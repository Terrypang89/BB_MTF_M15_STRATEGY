#!/usr/bin/env python3
"""
Multi-Input Transition Prediction Analysis — V36.03

Tests whether combining inputs (bbloc_slope, htf_direction, m15_cascade,
duration, per-TF states) beats bbloc-slope-only (40.9%) on MTF transition
prediction. Uses TRAIN/TEST split to protect against overfitting.

Usage:
    python scripts/analyze_multiinput_prediction.py
"""

import re
import json
from collections import defaultdict
from pathlib import Path

LOG_PATH = Path("references/Backtest_data/V36.03/20260630_clean.log")
REPORT_PATH = Path("references/MULTIINPUT_PREDICTION_ANALYSIS.md")
PRE_TRANSITION_BARS = 6
TRAIN_FRACTION = 0.7

# Direction mapping
UP_SCENARIOS = {"FF", "FS", "CF", "CS"}
DOWN_SCENARIOS = {"RF", "RS", "CR", "RR"}

# ============================================================
# STEP 0: Parse, filter, train/test split
# ============================================================

def parse_line(line):
    """Parse a DUALTF log line into a dict of fields."""
    line = line.strip()
    if "[DUALTF]" not in line:
        return None
    rec = {}
    m = re.match(r"(\d{4}\.\d{2}\.\d{2}\s+\d{2}:\d{2}:\d{2})", line)
    if m:
        rec["timestamp"] = m.group(1)
    for kv in re.finditer(r"(\w+):([\S]+)", line):
        key, val = kv.group(1), kv.group(2)
        rec[key] = val
    if "htfbbloc" in rec:
        try:
            rec["htfbbloc"] = int(rec["htfbbloc"])
        except ValueError:
            rec["htfbbloc"] = -1
    if "mtfbbloc" in rec:
        try:
            rec["mtfbbloc"] = int(rec["mtfbbloc"])
        except ValueError:
            rec["mtfbbloc"] = -1
    return rec

def is_no_data(rec):
    """Check if a row has no real HTF or MTF data."""
    htf = rec.get("htf", "XX")
    mtf = rec.get("mtf", "XX")
    if "X" in htf:
        return True
    if rec.get("htfbbloc", -1) == -1:
        return True
    if "X" in mtf:
        return True
    if rec.get("mtfbbloc", -1) == -1:
        return True
    return False

def step0_parse_filter_split():
    """Parse log, filter no-data, split TRAIN/TEST chronologically."""
    all_rows = []
    with open(LOG_PATH, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            rec = parse_line(line)
            if rec:
                all_rows.append(rec)

    kept = [r for r in all_rows if not is_no_data(r)]
    total = len(all_rows)
    dropped = total - len(kept)

    # Chronological train/test split
    split_idx = int(len(kept) * TRAIN_FRACTION)
    train = kept[:split_idx]
    test = kept[split_idx:]

    print(f"=== STEP 0: Parse, Filter, Split ===")
    print(f"  Total DUALTF rows : {total}")
    print(f"  Rows kept (data)  : {len(kept)}")
    print(f"  Rows dropped      : {dropped}")
    print(f"  TRAIN rows        : {len(train)}")
    print(f"  TEST rows         : {len(test)}")

    return kept, train, test, total, dropped

# ============================================================
# STEP 1: Compute input signals per row
# ============================================================

def bbloc_slope(bbloc_list):
    """Linear regression slope over BBLoc values."""
    if len(bbloc_list) < 2:
        return 0.0
    n = len(bbloc_list)
    x_mean = (n - 1) / 2.0
    y_mean = sum(bbloc_list) / n
    num = sum((i - x_mean) * (bbloc_list[i] - y_mean) for i in range(n))
    den = sum((i - x_mean) ** 2 for i in range(n))
    if den == 0:
        return 0.0
    return num / den

def classify_transition_direction(trans_from, trans_to):
    """Classify a transition as 'up', 'down', or 'neutral'."""
    order = {"R": 0, "S": 1, "F": 2, "C": 3}
    from_second = trans_from[1] if len(trans_from) >= 2 else "?"
    to_second = trans_to[1] if len(trans_to) >= 2 else "?"
    from_val = order.get(from_second, 1)
    to_val = order.get(to_second, 1)
    if to_val > from_val:
        return "up"
    elif to_val < from_val:
        return "down"
    else:
        return "neutral"

def htf_direction_from_scenario(htf_str):
    """Derive HTF direction from the htf 2-char scenario string.
    First char = D1 state, second char = H4 state.
    F/C = up, R = down, S = neutral.
    Combines both: if either is clearly directional, use that.
    """
    if len(htf_str) < 2:
        return "neutral"
    d1_state = htf_str[0]
    h4_state = htf_str[1]

    d1_dir = {"F": "up", "C": "up", "R": "down", "S": "neutral"}.get(d1_state, "neutral")
    h4_dir = {"F": "up", "C": "up", "R": "down", "S": "neutral"}.get(h4_state, "neutral")

    if d1_dir == h4_dir:
        return d1_dir
    if d1_dir == "up" and h4_dir == "down":
        return "mixed"
    if d1_dir == "down" and h4_dir == "up":
        return "mixed"
    # One is neutral, use the directional one
    if d1_dir == "neutral":
        return h4_dir
    return d1_dir

def compute_duration(i, kept):
    """Count consecutive prior rows in the same MTF scenario as row i."""
    curr_mtf = kept[i].get("mtf", "")
    count = 0
    for j in range(i, -1, -1):
        if kept[j].get("mtf", "") == curr_mtf:
            count += 1
        else:
            break
    return count

def compute_signals(kept):
    """For each row in kept, compute all predictor input signals.
    Returns list of signal dicts keyed by row index.
    """
    signals = []
    for i in range(len(kept)):
        rec = kept[i]
        # BBLoc slope over last 6 rows
        pre_start = max(0, i - PRE_TRANSITION_BARS)
        pre_bbloc = [kept[j].get("mtfbbloc", -1) for j in range(pre_start, i + 1)]
        slope = bbloc_slope(pre_bbloc)

        # HTF direction
        htf_str = rec.get("htf", "XX")
        htf_dir = htf_direction_from_scenario(htf_str)

        # M15 cascade state — stored as "state:F" in rec["m15"]
        m15_raw = rec.get("m15", "X")
        m15_state = m15_raw.split(":")[-1] if ":" in m15_raw else m15_raw

        # H1 state — stored as "state:F" in rec["h1"]
        h1_raw = rec.get("h1", "X")
        h1_state = h1_raw.split(":")[-1] if ":" in h1_raw else h1_raw

        # M30 state — stored as "state:F" in rec["m30"]
        m30_raw = rec.get("m30", "X")
        m30_state = m30_raw.split(":")[-1] if ":" in m30_raw else m30_raw

        # Duration in current MTF scenario
        dur = compute_duration(i, kept)

        signals.append({
            "index": i,
            "bbloc_slope": slope,
            "htf_direction": htf_dir,
            "m15_cascade": m15_state,
            "h1_state": h1_state,
            "m30_state": m30_state,
            "duration": dur,
            "mtf": rec.get("mtf", ""),
            "mtfbbloc": rec.get("mtfbbloc", -1),
        })
    return signals

# ============================================================
# STEP 1b: Identify transitions within a subset
# ============================================================

def identify_transitions_in_range(kept, start_idx, end_idx):
    """Identify MTF transitions within kept[start_idx:end_idx].
    Returns list of transition dicts with indices relative to kept.
    """
    transitions = []
    for i in range(start_idx + 1, end_idx):
        prev_mtf = kept[i - 1].get("mtf", "")
        curr_mtf = kept[i].get("mtf", "")
        if prev_mtf and curr_mtf and prev_mtf != curr_mtf:
            pre_start = max(0, i - PRE_TRANSITION_BARS)
            pre_bbloc = [kept[j].get("mtfbbloc", -1) for j in range(pre_start, i)]
            direction = classify_transition_direction(prev_mtf, curr_mtf)
            transitions.append({
                "index": i,
                "from": prev_mtf,
                "to": curr_mtf,
                "type": f"{prev_mtf}->{curr_mtf}",
                "pre_bbloc": pre_bbloc,
                "direction": direction,
            })
    return transitions

# ============================================================
# Predictors A-E
# ============================================================

def predict_bbloc_only(slope, htf_dir=None, m15_state=None, duration=None):
    """A: BBLoc slope only predictor."""
    if slope > 0.3:
        return "up"
    elif slope < -0.3:
        return "down"
    else:
        return "neutral"

def predict_bbloc_plus_htf(slope, htf_dir, m15_state=None, duration=None):
    """B: BBLoc slope + HTF direction.
    HTF acts as fork-decider: when bbloc is flat, use HTF.
    When bbloc and HTF agree, confident. When they disagree,
    use bbloc (it's the direct MTF signal).
    """
    bbloc_pred = predict_bbloc_only(slope)
    if bbloc_pred != "neutral":
        return bbloc_pred
    # BBLoc flat -> use HTF as decider
    if htf_dir == "up":
        return "up"
    elif htf_dir == "down":
        return "down"
    else:
        return "neutral"

def state_to_direction(state):
    """Map a single TF state to a direction hint."""
    return {"F": "up", "C": "up", "R": "down", "S": "neutral", "X": "neutral"}.get(state, "neutral")

def predict_bbloc_plus_m15(slope, htf_dir=None, m15_state=None, duration=None):
    """C: BBLoc slope + M15 cascade.
    M15 is the leading edge — when M15 turns, M30 follows.
    When bbloc flat, use M15. When both agree, confident.
    When they disagree, M15 may be early signal — trust M15.
    """
    m15_dir = state_to_direction(m15_state)
    bbloc_pred = predict_bbloc_only(slope)
    if bbloc_pred != "neutral":
        return bbloc_pred
    # BBLoc flat -> use M15
    if m15_dir in ("up", "down"):
        return m15_dir
    return "neutral"

def predict_all_combined(slope, htf_dir, m15_state, duration):
    """D: All inputs combined — bbloc + HTF + M15 + duration.
    Voting system: each input casts a vote.
    Duration acts as confidence — longer duration = closer to transition.
    """
    votes = {"up": 0, "down": 0, "neutral": 0}

    # BBLoc vote
    bbloc_pred = predict_bbloc_only(slope)
    votes[bbloc_pred] += 1

    # HTF vote
    if htf_dir in ("up", "down"):
        votes[htf_dir] += 1
    else:
        votes["neutral"] += 1

    # M15 vote
    m15_dir = state_to_direction(m15_state)
    if m15_dir in ("up", "down"):
        votes[m15_dir] += 1
    else:
        votes["neutral"] += 1

    # Duration vote: long duration (>10 bars) biases toward transition
    # (not persist), so reduces neutral weight
    if duration > 10:
        # Remove neutral vote if present (transition likely)
        votes["neutral"] = max(0, votes["neutral"] - 1)

    # Winner
    max_votes = max(votes.values())
    winner = [k for k, v in votes.items() if v == max_votes]
    if len(winner) == 1:
        return winner[0]
    # Tie: prefer non-neutral if available
    non_neutral = [w for w in winner if w != "neutral"]
    if non_neutral:
        return non_neutral[0]
    return "neutral"

def predict_m15_alone(slope, htf_dir=None, m15_state=None, duration=None):
    """E: M15 cascade alone."""
    m15_dir = state_to_direction(m15_state)
    if m15_dir in ("up", "down"):
        return m15_dir
    return "neutral"

# ============================================================
# Evaluation
# ============================================================

def evaluate_predictor(transitions, signals, predict_fn):
    """Evaluate a predictor on a set of transitions.
    predict_fn takes (slope, htf_dir, m15_state, duration) and returns direction.
    Returns (correct, total, accuracy).
    """
    correct = 0
    total = 0
    details = []
    for t in transitions:
        sig = signals[t["index"]]
        predicted = predict_fn(
            sig["bbloc_slope"],
            sig["htf_direction"],
            sig["m15_cascade"],
            sig["duration"],
        )
        actual = t["direction"]
        is_correct = predicted == actual
        if is_correct:
            correct += 1
        total += 1
        details.append({
            "index": t["index"],
            "type": t["type"],
            "predicted": predicted,
            "actual": actual,
            "correct": is_correct,
        })
    accuracy = correct / total * 100 if total else 0.0
    return correct, total, accuracy, details

def majority_baseline_accuracy(transitions):
    """Accuracy if we always predict the most common direction."""
    dir_counts = defaultdict(int)
    for t in transitions:
        dir_counts[t["direction"]] += 1
    if not dir_counts:
        return 0.0, "neutral", dir_counts
    most_common = max(dir_counts, key=dir_counts.get)
    acc = dir_counts[most_common] / len(transitions) * 100
    return acc, most_common, dict(dir_counts)

# ============================================================
# STEP 3: Ablation
# ============================================================

def ablation_analysis(train_trans, test_trans, signals):
    """Test each input added to bbloc-slope alone, one at a time.
    Report TEST accuracy improvement.
    """
    results = {}

    # Base: bbloc only
    base_train, _, base_train_acc, _ = evaluate_predictor(
        train_trans, signals, predict_bbloc_only)
    base_test, _, base_test_acc, _ = evaluate_predictor(
        test_trans, signals, predict_bbloc_only)
    results["bbloc_only"] = {"train_acc": base_train_acc, "test_acc": base_test_acc,
                              "test_delta": 0.0}

    # + HTF
    htf_train, _, htf_train_acc, _ = evaluate_predictor(
        train_trans, signals, predict_bbloc_plus_htf)
    htf_test, _, htf_test_acc, _ = evaluate_predictor(
        test_trans, signals, predict_bbloc_plus_htf)
    results["bbloc+htf"] = {"train_acc": htf_train_acc, "test_acc": htf_test_acc,
                             "test_delta": htf_test_acc - base_test_acc}

    # + M15
    m15_train, _, m15_train_acc, _ = evaluate_predictor(
        train_trans, signals, predict_bbloc_plus_m15)
    m15_test, _, m15_test_acc, _ = evaluate_predictor(
        test_trans, signals, predict_bbloc_plus_m15)
    results["bbloc+m15"] = {"train_acc": m15_train_acc, "test_acc": m15_test_acc,
                             "test_delta": m15_test_acc - base_test_acc}

    # + HTF + M15 + duration (all combined)
    all_train, _, all_train_acc, _ = evaluate_predictor(
        train_trans, signals, predict_all_combined)
    all_test, _, all_test_acc, _ = evaluate_predictor(
        test_trans, signals, predict_all_combined)
    results["bbloc+htf+m15+dur"] = {
        "train_acc": all_train_acc, "test_acc": all_test_acc,
        "test_delta": all_test_acc - base_test_acc}

    # M15 alone (for comparison)
    m15a_train, _, m15a_train_acc, _ = evaluate_predictor(
        train_trans, signals, predict_m15_alone)
    m15a_test, _, m15a_test_acc, _ = evaluate_predictor(
        test_trans, signals, predict_m15_alone)
    results["m15_alone"] = {"train_acc": m15a_train_acc, "test_acc": m15a_test_acc,
                             "test_delta": m15a_test_acc - base_test_acc}

    return results

# ============================================================
# STEP 4: Targeted predictor (high-confidence only)
# ============================================================

def targeted_predict(slope, htf_dir, m15_state, duration):
    """Predict only when inputs strongly agree.
    Returns (prediction, confidence) where confidence is 'high', 'medium', or 'skip'.
    High confidence = at least 3 of 4 inputs agree on direction.
    """
    votes = []

    # BBLoc direction
    bb_pred = predict_bbloc_only(slope)
    if bb_pred in ("up", "down"):
        votes.append(bb_pred)

    # HTF direction
    if htf_dir in ("up", "down"):
        votes.append(htf_dir)

    # M15 direction
    m15_dir = state_to_direction(m15_state)
    if m15_dir in ("up", "down"):
        votes.append(m15_dir)

    # Duration: long duration supports transition (not persist)
    if duration > 10:
        # Doesn't vote direction but supports non-neutral
        pass

    if len(votes) < 2:
        return None, "skip"

    # Count agreement
    up_count = votes.count("up")
    down_count = votes.count("down")

    if up_count >= 3 or down_count >= 3:
        return "up" if up_count > down_count else "down", "high"
    elif up_count == 2 or down_count == 2:
        return "up" if up_count > down_count else "down", "medium"
    else:
        return None, "skip"

def evaluate_targeted(transitions, signals):
    """Evaluate the targeted (high-confidence-only) predictor."""
    high_correct = 0
    high_total = 0
    med_correct = 0
    med_total = 0
    all_correct = 0
    all_total = 0
    skipped = 0

    for t in transitions:
        sig = signals[t["index"]]
        pred, conf = targeted_predict(
            sig["bbloc_slope"],
            sig["htf_direction"],
            sig["m15_cascade"],
            sig["duration"],
        )
        actual = t["direction"]

        if pred is None:
            skipped += 1
            continue

        if pred == actual:
            all_correct += 1
        all_total += 1

        if conf == "high":
            if pred == actual:
                high_correct += 1
            high_total += 1
        elif conf == "medium":
            if pred == actual:
                med_correct += 1
            med_total += 1

    return {
        "high_correct": high_correct,
        "high_total": high_total,
        "high_accuracy": high_correct / high_total * 100 if high_total else 0.0,
        "med_correct": med_correct,
        "med_total": med_total,
        "med_accuracy": med_correct / med_total * 100 if med_total else 0.0,
        "all_correct": all_correct,
        "all_total": all_total,
        "all_accuracy": all_correct / all_total * 100 if all_total else 0.0,
        "skipped": skipped,
    }

# ============================================================
# STEP 5: Write report
# ============================================================

def write_report(results):
    """Write the full analysis report."""
    r = results

    report = f"""# Multi-Input Transition Prediction Analysis — V36.03

## 1. Data Summary & Train/Test Split

- **Total DUALTF rows**: {r['total_rows']}
- **Rows kept (real HTF+MTF data)**: {r['kept_rows']}
- **Rows dropped (no-data)**: {r['dropped_rows']}
- **TRAIN rows (first 70%)**: {r['train_rows']}
- **TEST rows (last 30%)**: {r['test_rows']}
- **TRAIN transitions**: {r['train_transitions']}
- **TEST transitions**: {r['test_transitions']}
- **TRAIN majority baseline**: {r['train_majority_acc']:.1f}% (always predict '{r['train_majority_dir']}')
- **TEST majority baseline**: {r['test_majority_acc']:.1f}% (always predict '{r['test_majority_dir']}')

> The TEST accuracy is the honest number — predictors are derived on TRAIN, measured on TEST.

## 2. Predictor Comparison

| Predictor | Inputs | TRAIN Accuracy | TEST Accuracy | vs TEST Baseline |
|-----------|--------|---------------|---------------|-----------------|
| A — BBLoc slope only | bbloc_slope | {r['predictors']['A']['train_acc']:.1f}% | {r['predictors']['A']['test_acc']:.1f}% | +{r['predictors']['A']['test_acc'] - r['test_majority_acc']:.1f}pp |
| B — BBLoc + HTF | bbloc_slope + htf_direction | {r['predictors']['B']['train_acc']:.1f}% | {r['predictors']['B']['test_acc']:.1f}% | +{r['predictors']['B']['test_acc'] - r['test_majority_acc']:.1f}pp |
| C — BBLoc + M15 | bbloc_slope + m15_cascade | {r['predictors']['C']['train_acc']:.1f}% | {r['predictors']['C']['test_acc']:.1f}% | +{r['predictors']['C']['test_acc'] - r['test_majority_acc']:.1f}pp |
| D — All combined | bbloc + htf + m15 + duration | {r['predictors']['D']['train_acc']:.1f}% | {r['predictors']['D']['test_acc']:.1f}% | +{r['predictors']['D']['test_acc'] - r['test_majority_acc']:.1f}pp |
| E — M15 alone | m15_cascade | {r['predictors']['E']['train_acc']:.1f}% | {r['predictors']['E']['test_acc']:.1f}% | +{r['predictors']['E']['test_acc'] - r['test_majority_acc']:.1f}pp |

**Baselines**: Random = 33.3% | Majority = {r['test_majority_acc']:.1f}% | BBLoc-only full-dataset benchmark = 40.9% (706 transitions)

> Note: BBLoc-only on TEST ({r['predictors']['A']['test_acc']:.1f}%) differs from the full-dataset benchmark (40.9%) because the TEST subset (221 transitions) is a different time period. The TEST number is the fair comparison for all predictors.

## 3. Ablation — Which Inputs Help?

| Configuration | TEST Accuracy | Delta vs BBLoc-only |
|---------------|-------------|-------------------|
| BBLoc slope only (baseline) | {r['ablation']['bbloc_only']['test_acc']:.1f}% | — |
| + HTF direction | {r['ablation']['bbloc+htf']['test_acc']:.1f}% | {r['ablation']['bbloc+htf']['test_delta']:+.1f}pp |
| + M15 cascade | {r['ablation']['bbloc+m15']['test_acc']:.1f}% | {r['ablation']['bbloc+m15']['test_delta']:+.1f}pp |
| + HTF + M15 + duration | {r['ablation']['bbloc+htf+m15+dur']['test_acc']:.1f}% | {r['ablation']['bbloc+htf+m15+dur']['test_delta']:+.1f}pp |
| M15 alone (for comparison) | {r['ablation']['m15_alone']['test_acc']:.1f}% | {r['ablation']['m15_alone']['test_delta']:+.1f}pp |

### Input Ranking (by TEST contribution):
"""

    # Rank inputs by test_delta
    ablation_ranked = sorted(
        [(k, v) for k, v in r["ablation"].items() if k != "bbloc_only"],
        key=lambda x: -x[1]["test_delta"],
    )
    for rank, (key, val) in enumerate(ablation_ranked, 1):
        report += f"- **{rank}. {key}**: {val['test_delta']:+.1f}pp on TEST\n"

    report += f"""
## 4. Targeted Predictor — High-Confidence Only

Instead of predicting every transition, predict only when inputs agree:

| Confidence Level | Predictions Made | Correct | Accuracy | Coverage |
|-----------------|-----------------|---------|----------|----------|
| High only | {r['targeted_test']['high_total']} | {r['targeted_test']['high_correct']} | {r['targeted_test']['high_accuracy']:.1f}% | {r['targeted_test']['high_total'] / r['test_transitions'] * 100:.1f}% |
| Medium only | {r['targeted_test']['med_total']} | {r['targeted_test']['med_correct']} | {r['targeted_test']['med_accuracy']:.1f}% | {r['targeted_test']['med_total'] / r['test_transitions'] * 100:.1f}% |
| All predictions made | {r['targeted_test']['all_total']} | {r['targeted_test']['all_correct']} | {r['targeted_test']['all_accuracy']:.1f}% | {r['targeted_test']['all_total'] / r['test_transitions'] * 100:.1f}% |
| Skipped | {r['targeted_test']['skipped']} | — | — | {r['targeted_test']['skipped'] / r['test_transitions'] * 100:.1f}% |

## 5. Overfitting Check

| Predictor | TRAIN Acc | TEST Acc | Gap | Flag |
|-----------|----------|----------|-----|------|
| A — BBLoc only | {r['predictors']['A']['train_acc']:.1f}% | {r['predictors']['A']['test_acc']:.1f}% | {r['predictors']['A']['train_acc'] - r['predictors']['A']['test_acc']:+.1f}pp | {'OVERFIT' if (r['predictors']['A']['train_acc'] - r['predictors']['A']['test_acc']) > 5 else 'OK'} |
| B — BBLoc + HTF | {r['predictors']['B']['train_acc']:.1f}% | {r['predictors']['B']['test_acc']:.1f}% | {r['predictors']['B']['train_acc'] - r['predictors']['B']['test_acc']:+.1f}pp | {'OVERFIT' if (r['predictors']['B']['train_acc'] - r['predictors']['B']['test_acc']) > 5 else 'OK'} |
| C — BBLoc + M15 | {r['predictors']['C']['train_acc']:.1f}% | {r['predictors']['C']['test_acc']:.1f}% | {r['predictors']['C']['train_acc'] - r['predictors']['C']['test_acc']:+.1f}pp | {'OVERFIT' if (r['predictors']['C']['train_acc'] - r['predictors']['C']['test_acc']) > 5 else 'OK'} |
| D — All combined | {r['predictors']['D']['train_acc']:.1f}% | {r['predictors']['D']['test_acc']:.1f}% | {r['predictors']['D']['train_acc'] - r['predictors']['D']['test_acc']:+.1f}pp | {'OVERFIT' if (r['predictors']['D']['train_acc'] - r['predictors']['D']['test_acc']) > 5 else 'OK'} |
| E — M15 alone | {r['predictors']['E']['train_acc']:.1f}% | {r['predictors']['E']['test_acc']:.1f}% | {r['predictors']['E']['train_acc'] - r['predictors']['E']['test_acc']:+.1f}pp | {'OVERFIT' if (r['predictors']['E']['train_acc'] - r['predictors']['E']['test_acc']) > 5 else 'OK'} |

## 6. Honest Verdict

"""

    # Determine verdict
    best_test_predictor = max(r["predictors"].items(), key=lambda x: x[1]["test_acc"])
    best_label, best_result = best_test_predictor
    best_test_acc = best_result["test_acc"]
    bbloc_only_test = r["predictors"]["A"]["test_acc"]

    beats_bbloc = best_test_acc > bbloc_only_test + 2  # 2pp margin
    viable = best_test_acc >= 50  # 50% threshold for viability

    if beats_bbloc:
        report += f"""**Multi-input DOES beat BBLoc-only on TEST.**

- Best TEST accuracy: **{best_test_acc:.1f}%** ({best_label}), vs BBLoc-only TEST = {bbloc_only_test:.1f}%
- Margin: **{best_test_acc - bbloc_only_test:.1f} percentage points**
- vs majority baseline ({r['test_majority_acc']:.1f}%): **+{best_test_acc - r['test_majority_acc']:.1f}pp**
"""
    else:
        report += f"""**Multi-input does NOT meaningfully beat BBLoc-only on TEST.**

- Best TEST accuracy: **{best_test_acc:.1f}%** ({best_label}), vs BBLoc-only TEST = {bbloc_only_test:.1f}%
- Margin: **{best_test_acc - bbloc_only_test:.1f} percentage points** (not meaningful)
- vs majority baseline ({r['test_majority_acc']:.1f}%): **+{best_test_acc - r['test_majority_acc']:.1f}pp**
"""

    if viable:
        report += f"""
**Prediction is VIABLE at {best_test_acc:.1f}% TEST accuracy.** This is a genuine signal — multi-input prediction can inform Part 4.
"""
    else:
        report += f"""
**Prediction is NOT VIABLE at {best_test_acc:.1f}% TEST accuracy.** Even the best multi-input predictor doesn't reach a level that justifies building Part 4 on prediction alone.
"""

    # Overfitting flags
    overfit_flags = []
    for label, pred in r["predictors"].items():
        gap = pred["train_acc"] - pred["test_acc"]
        if gap > 5:
            overfit_flags.append(f"{label}: TRAIN {pred['train_acc']:.1f}% >> TEST {pred['test_acc']:.1f}% (gap {gap:.1f}pp)")

    if overfit_flags:
        report += f"""
**OVERFITTING FLAGS:**
"""
        for flag in overfit_flags:
            report += f"- {flag}\n"
    else:
        report += f"""
**No overfitting detected** — no predictor has a TRAIN/TEST gap > 5pp.
"""

    # Targeted verdict
    tgt = r["targeted_test"]
    if tgt["high_accuracy"] > 60 and tgt["high_total"] > 0:
        report += f"""
**Targeted (high-confidence-only) approach**: {tgt['high_accuracy']:.1f}% accuracy on {tgt['high_total']} predictions ({tgt['high_total'] / r['test_transitions'] * 100:.1f}% coverage). This is more tradeable than a low-accuracy full-coverage predictor.
"""
    elif tgt["all_accuracy"] > r["test_majority_acc"] + 3:
        report += f"""
**Targeted approach**: {tgt['all_accuracy']:.1f}% on {tgt['all_total']} predictions ({tgt['all_total'] / r['test_transitions'] * 100:.1f}% coverage). Modest improvement over blind prediction, but limited coverage.
"""
    else:
        report += f"""
**Targeted approach not compelling** — high-confidence accuracy ({tgt['high_accuracy']:.1f}%) doesn't justify the reduced coverage ({tgt['high_total'] / r['test_transitions'] * 100:.1f}%).
"""

    report += f"""
**Recommendation**: {"Build Part 4 on multi-input prediction — genuine signal exists." if viable else "Use identification-based trading (Part 3), not prediction. The signal is too weak to build a prediction layer on top."}
"""

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\n=== STEP 5: Report Written ===")
    print(f"  {REPORT_PATH}")

# ============================================================
# Main
# ============================================================

def main():
    print("=" * 60)
    print("Multi-Input Transition Prediction Analysis — V36.03")
    print("=" * 60)

    # Step 0
    kept, train, test, total_rows, dropped_rows = step0_parse_filter_split()
    kept_rows = len(kept)

    # Compute signals for all kept rows
    signals = compute_signals(kept)

    # Identify transitions in each split
    train_trans = identify_transitions_in_range(kept, 0, len(train))
    test_trans = identify_transitions_in_range(kept, len(train) - 1, len(kept))

    print(f"\n=== Transitions ===")
    print(f"  TRAIN transitions : {len(train_trans)}")
    print(f"  TEST transitions  : {len(test_trans)}")

    # Baselines
    train_majority_acc, train_majority_dir, train_dir_counts = majority_baseline_accuracy(train_trans)
    test_majority_acc, test_majority_dir, test_dir_counts = majority_baseline_accuracy(test_trans)

    print(f"\n  TRAIN majority baseline: {train_majority_acc:.1f}% (always '{train_majority_dir}')")
    print(f"  TEST majority baseline : {test_majority_acc:.1f}% (always '{test_majority_dir}')")

    # Evaluate predictors A-E on both splits
    predictor_names = {
        "A": ("BBLoc slope only", predict_bbloc_only),
        "B": ("BBLoc + HTF", predict_bbloc_plus_htf),
        "C": ("BBLoc + M15", predict_bbloc_plus_m15),
        "D": ("All combined", predict_all_combined),
        "E": ("M15 alone", predict_m15_alone),
    }

    predictors = {}
    print(f"\n=== Predictor Results ===")
    print(f"{'Predictor':<25} {'TRAIN acc':>10} {'TEST acc':>10} {'vs baseline':>14}")
    print(f"{'-' * 60}")

    for label, (name, fn) in predictor_names.items():
        _, _, train_acc, _ = evaluate_predictor(train_trans, signals, fn)
        _, _, test_acc, _ = evaluate_predictor(test_trans, signals, fn)
        predictors[label] = {
            "name": name,
            "train_acc": train_acc,
            "test_acc": test_acc,
        }
        print(f"  {label} — {name:<22} {train_acc:>9.1f}% {test_acc:>9.1f}% {test_acc - test_majority_acc:>+13.1f}pp")

    # Ablation
    ablation = ablation_analysis(train_trans, test_trans, signals)

    # Targeted predictor on TEST
    targeted_test = evaluate_targeted(test_trans, signals)

    print(f"\n=== Targeted Predictor (TEST) ===")
    print(f"  High confidence : {targeted_test['high_accuracy']:.1f}% ({targeted_test['high_total']}/{targeted_test['high_total'] + targeted_test['med_total'] + targeted_test.get('skipped', 0)})")
    print(f"  Medium confidence: {targeted_test['med_accuracy']:.1f}%")
    print(f"  All made        : {targeted_test['all_accuracy']:.1f}% ({targeted_test['all_total']}/{len(test_trans)})")
    print(f"  Skipped         : {targeted_test['skipped']}")

    # Write report
    results = {
        "total_rows": total_rows,
        "kept_rows": kept_rows,
        "dropped_rows": dropped_rows,
        "train_rows": len(train),
        "test_rows": len(test),
        "train_transitions": len(train_trans),
        "test_transitions": len(test_trans),
        "train_majority_acc": train_majority_acc,
        "train_majority_dir": train_majority_dir,
        "test_majority_acc": test_majority_acc,
        "test_majority_dir": test_majority_dir,
        "predictors": predictors,
        "ablation": ablation,
        "targeted_test": targeted_test,
    }
    write_report(results)

    print("\n" + "=" * 60)
    print("Analysis complete.")
    print("=" * 60)

if __name__ == "__main__":
    main()
