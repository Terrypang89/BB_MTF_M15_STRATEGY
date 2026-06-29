#!/usr/bin/env python3
"""
Analyze BBLoc trajectory as a predictor of MTF scenario transitions.

Parses V36.03 backtest log, filters no-data rows, identifies MTF transitions,
and tests whether the 6-bar BBLoc slope precedes transition direction.

Usage:
    python scripts/analyze_bbloc_transitions.py
"""

import re
import json
from collections import defaultdict
from pathlib import Path

LOG_PATH = Path("references/Backtest_data/V36.03/20260630_clean.log")
REPORT_PATH = Path("references/BBLOC_TRANSITION_ANALYSIS.md")
PRE_TRANSITION_BARS = 6

# --- Scenario direction mapping for the predictor ---
# Up/continuation scenarios (bullish)
UP_SCENARIOS = {"FF", "FS", "CF", "CS"}
# Down/reversal scenarios (bearish)
DOWN_SCENARIOS = {"RF", "RS", "CR", "RR"}
# Neutral
NEUTRAL_SCENARIOS = {"SF", "SS", "SR"}

# For transition direction: classify a FROM->TO transition
# as "up" if TO is more bullish than FROM, "down" if more bearish
SCENARIO_ORDER = {"RR": 0, "CR": 1, "SR": 2, "FR": 3,
                  "RS": 4, "CS": 5, "SS": 6, "FS": 7, "RF": 8,
                  "CF": 9, "SF": 10, "FF": 11, "RF": 8, "RR": 0}

# --- STEP 1: Parse and filter ---

def parse_line(line):
    """Parse a DUALTF log line into a dict of fields."""
    line = line.strip()
    if "[DUALTF]" not in line:
        return None

    rec = {}

    # Timestamp
    m = re.match(r"(\d{4}\.\d{2}\.\d{2}\s+\d{2}:\d{2}:\d{2})", line)
    if m:
        rec["timestamp"] = m.group(1)

    # Key-value pairs like htf:SF htfbbloc:9 mtf:FF mtfbbloc:10
    for kv in re.finditer(r"(\w+):([\S]+)", line):
        key, val = kv.group(1), kv.group(2)
        rec[key] = val

    # Parse numeric fields
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
    # HTF: contains X
    if "X" in htf:
        return True
    # HTF bbloc == -1
    if rec.get("htfbbloc", -1) == -1:
        return True
    # MTF: contains X
    if "X" in mtf:
        return True
    # MTF bbloc == -1
    if rec.get("mtfbbloc", -1) == -1:
        return True
    return False

def step1_parse_and_filter():
    """Parse log, filter no-data rows, return all rows and kept rows."""
    all_rows = []
    with open(LOG_PATH, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            rec = parse_line(line)
            if rec:
                all_rows.append(rec)

    total = len(all_rows)
    kept = [r for r in all_rows if not is_no_data(r)]
    dropped = total - len(kept)

    print(f"=== STEP 1: Parse & Filter ===")
    print(f"  Total DUALTF rows : {total}")
    print(f"  Rows kept (data)  : {len(kept)}")
    print(f"  Rows dropped (no-data): {dropped}")

    return all_rows, kept

# --- STEP 2: Identify transitions ---

def step2_identify_transitions(kept):
    """Walk kept rows in time order; identify MTF scenario transitions."""
    transitions = []
    for i in range(1, len(kept)):
        prev_mtf = kept[i - 1].get("mtf", "")
        curr_mtf = kept[i].get("mtf", "")
        if prev_mtf and curr_mtf and prev_mtf != curr_mtf:
            trans_type = f"{prev_mtf}->{curr_mtf}"

            # Pre-transition BBLoc trajectory (6 bars before transition)
            pre_start = max(0, i - PRE_TRANSITION_BARS)
            pre_bbloc = [kept[j].get("mtfbbloc", -1) for j in range(pre_start, i)]

            # HTF context at transition
            htf_at_trans = kept[i].get("htf", "?")
            htf_bbloc_at_trans = kept[i].get("htfbbloc", -1)

            transitions.append({
                "index": i,
                "timestamp": kept[i].get("timestamp", ""),
                "from": prev_mtf,
                "to": curr_mtf,
                "type": trans_type,
                "pre_bbloc": pre_bbloc,
                "htf_at_trans": htf_at_trans,
                "htf_bbloc_at_trans": htf_bbloc_at_trans,
            })

    persistence = len(kept) - 1 - len(transitions)

    print(f"\n=== STEP 2: Identify Transitions ===")
    print(f"  MTF transitions     : {len(transitions)}")
    print(f"  Persistence rows    : {persistence}")
    print(f"  Persistence base rate: {persistence / (len(kept) - 1) * 100:.1f}%")

    return transitions, persistence

# --- STEP 3: Analyze ---

def bbloc_slope(bbloc_list):
    """Compute the slope of BBLoc over the pre-transition bars.
    Simple linear regression: slope = sum((x - x_mean)(y - y_mean)) / sum((x - x_mean)^2)
    Returns slope value. If not enough data, returns 0.0."""
    if len(bbloc_list) < 2:
        return 0.0
    n = len(bbloc_list)
    x = list(range(n))
    x_mean = (n - 1) / 2.0
    y_mean = sum(bbloc_list) / n
    num = sum((x[i] - x_mean) * (bbloc_list[i] - y_mean) for i in range(n))
    den = sum((x[i] - x_mean) ** 2 for i in range(n))
    if den == 0:
        return 0.0
    return num / den

def classify_transition_direction(trans):
    """Classify a transition as 'up', 'down', or 'neutral'.
    Uses the second letter of the scenario as primary signal:
    F=flow (neutral-positive), S=squeeze (neutral),
    C=continuation (positive), R=reversal (negative).
    Also considers the first letter change.
    Simplified: second letter change direction.
    F->S = tightening, F->R = reversal (down), F->C = continuation (up)
    S->F = release, S->R = reversal (down), S->C = continuation (up)
    R->F = recovery (up), R->S = squeeze (neutral), R->C = continuation (up)
    C->F = release, C->S = tightening, C->R = reversal (down)
    """
    to_second = trans["to"][1] if len(trans["to"]) >= 2 else "?"
    from_second = trans["from"][1] if len(trans["from"]) >= 2 else "?"

    # Direction based on second letter movement
    # R < S < F < C  (reversal worst, continuation best)
    order = {"R": 0, "S": 1, "F": 2, "C": 3}
    from_val = order.get(from_second, 1)
    to_val = order.get(to_second, 1)

    if to_val > from_val:
        return "up"
    elif to_val < from_val:
        return "down"
    else:
        return "neutral"

def step3_analyze(kept, transitions, persistence):
    """Analyze BBLoc trajectory as predictor of transitions."""

    # --- A. Transition frequency ---
    total_pairs = len(kept) - 1
    persist_rate = persistence / total_pairs * 100

    print(f"\n=== STEP 3: Analysis ===")
    print(f"  A. Transition Frequency:")
    print(f"     Total consecutive pairs : {total_pairs}")
    print(f"     Transitions             : {len(transitions)}")
    print(f"     Persistence rows        : {persistence}")
    print(f"     Persistence base rate   : {persist_rate:.1f}%")

    # --- B. Pre-transition BBLoc pattern per type ---
    type_data = defaultdict(lambda: {"count": 0, "slopes": [], "directions": [],
                                      "consistent_up": 0, "consistent_down": 0,
                                      "consistent_flat": 0, "directions_seen": []})

    for t in transitions:
        tt = t["type"]
        slope = bbloc_slope(t["pre_bbloc"])
        direction = classify_transition_direction(t)

        type_data[tt]["count"] += 1
        type_data[tt]["slopes"].append(slope)
        type_data[tt]["directions"].append(direction)
        type_data[tt]["directions_seen"].append(direction)

        # Consistency: rising slope -> up, falling slope -> down, flat -> neutral
        if slope > 0.3 and direction == "up":
            type_data[tt]["consistent_up"] += 1
        elif slope < -0.3 and direction == "down":
            type_data[tt]["consistent_down"] += 1
        elif abs(slope) <= 0.3 and direction == "neutral":
            type_data[tt]["consistent_flat"] += 1

    print(f"\n  B. Pre-Transition BBLoc Pattern (per type):")
    print(f"  {'Type':<12} {'Count':>6} {'Avg Slope':>10} {'% Consistent':>13}")
    print(f"  {'-'*43}")

    type_summary = {}
    for tt in sorted(type_data.keys()):
        d = type_data[tt]
        avg_slope = sum(d["slopes"]) / len(d["slopes"]) if d["slopes"] else 0
        consistent = d["consistent_up"] + d["consistent_down"] + d["consistent_flat"]
        pct_consistent = consistent / d["count"] * 100 if d["count"] else 0
        print(f"  {tt:<12} {d['count']:>6} {avg_slope:>10.3f} {pct_consistent:>12.1f}%")
        type_summary[tt] = {
            "count": d["count"],
            "avg_slope": avg_slope,
            "pct_consistent": pct_consistent,
        }

    # --- C. Predictiveness test ---
    # Predictor: rising slope -> predict up, falling slope -> predict down, flat -> predict persist
    # On transition rows: how often does bbloc-slope get direction right?

    correct = 0
    total_transition_predictions = 0
    direction_counts = {"up": 0, "down": 0, "neutral": 0}

    for t in transitions:
        slope = bbloc_slope(t["pre_bbloc"])
        actual = classify_transition_direction(t)
        direction_counts[actual] += 1

        # Prediction
        if slope > 0.3:
            predicted = "up"
        elif slope < -0.3:
            predicted = "down"
        else:
            predicted = "neutral"

        if predicted == actual:
            correct += 1
        total_transition_predictions += 1

    transition_accuracy = correct / total_transition_predictions * 100 if total_transition_predictions else 0

    # Baseline 1: always-persist (predict no change = neutral)
    # On transition rows, always-persist is wrong (it's a transition, not persist)
    # But for the direction prediction on transitions: predict the most common direction
    most_common_dir = max(direction_counts, key=direction_counts.get)
    always_majority_correct = direction_counts[most_common_dir]
    always_majority_accuracy = always_majority_correct / total_transition_predictions * 100

    # Baseline 2: random (3 classes: up, down, neutral)
    random_accuracy = 100 / 3  # ~33.3%

    # Overall accuracy on ALL pairs (including persist)
    # BBLoc predictor on persist rows: slope is usually flat -> predict neutral (persist) -> correct
    # But we need to check this properly
    persist_predictions_correct = 0
    persist_predictions_total = 0

    for i in range(1, len(kept)):
        prev_mtf = kept[i - 1].get("mtf", "")
        curr_mtf = kept[i].get("mtf", "")

        # Get 6-bar pre-bbloc
        pre_start = max(0, i - PRE_TRANSITION_BARS)
        pre_bbloc = [kept[j].get("mtfbbloc", -1) for j in range(pre_start, i)]
        slope = bbloc_slope(pre_bbloc)

        # Prediction
        if slope > 0.3:
            predicted = "up"
        elif slope < -0.3:
            predicted = "down"
        else:
            predicted = "neutral"

        # Actual
        if prev_mtf == curr_mtf:
            actual = "neutral"  # persist
        else:
            actual = classify_transition_direction({
                "from": prev_mtf, "to": curr_mtf
            })

        if predicted == actual:
            persist_predictions_correct += 1
        persist_predictions_total += 1

    overall_accuracy = persist_predictions_correct / persist_predictions_total * 100

    # Always-persist baseline on all pairs
    always_persist_correct = persistence  # correct on persist rows only
    always_persist_overall = always_persist_correct / persist_predictions_total * 100

    # Distribution of slopes
    all_slopes = [bbloc_slope([kept[j].get("mtfbbloc", -1)
                               for j in range(max(0, i - PRE_TRANSITION_BARS), i)])
                  for i in range(1, len(kept))]

    rising = sum(1 for s in all_slopes if s > 0.3)
    falling = sum(1 for s in all_slopes if s < -0.3)
    flat = sum(1 for s in all_slopes if abs(s) <= 0.3)

    print(f"\n  C. Predictiveness Test:")
    print(f"     Slope distribution (all {len(all_slopes)} pairs):")
    print(f"       Rising (>0.3)  : {rising} ({rising/len(all_slopes)*100:.1f}%)")
    print(f"       Falling (<-0.3): {falling} ({falling/len(all_slopes)*100:.1f}%)")
    print(f"       Flat (<=0.3)   : {flat} ({flat/len(all_slopes)*100:.1f}%)")
    print(f"     Transition direction distribution:")
    for d in ["up", "down", "neutral"]:
        print(f"       {d:>8}: {direction_counts[d]} ({direction_counts[d]/total_transition_predictions*100:.1f}%)")
    print(f"     Transition accuracy (bbloc slope predictor): {transition_accuracy:.1f}%")
    print(f"     Baseline - always predict majority ({most_common_dir}): {always_majority_accuracy:.1f}%")
    print(f"     Baseline - random (3 classes): {random_accuracy:.1f}%")
    print(f"     Overall accuracy (all pairs, bbloc slope): {overall_accuracy:.1f}%")
    print(f"     Overall accuracy (all pairs, always-persist): {always_persist_overall:.1f}%")

    # --- D. Honest verdict ---
    beats_majority = transition_accuracy > always_majority_accuracy + 5  # 5% margin
    beats_random = transition_accuracy > random_accuracy + 5

    print(f"\n  D. Honest Verdict:")
    if beats_majority and beats_random:
        print(f"     BBLoc slope DOES beat baselines on transitions ({transition_accuracy:.1f}% vs {always_majority_accuracy:.1f}% majority, {random_accuracy:.1f}% random)")
        verdict = "BEATS_BASELINE"
    elif beats_random and not beats_majority:
        print(f"     BBLoc slope beats random ({transition_accuracy:.1f}% vs {random_accuracy:.1f}%) but NOT majority baseline ({always_majority_accuracy:.1f}%)")
        verdict = "MARGINAL"
    else:
        print(f"     BBLoc slope does NOT meaningfully beat baselines on transitions")
        verdict = "NO_SIGNAL"

    return {
        "total_pairs": total_pairs,
        "transitions": len(transitions),
        "persistence": persistence,
        "persist_rate": persist_rate,
        "type_summary": type_summary,
        "transition_accuracy": transition_accuracy,
        "always_majority_accuracy": always_majority_accuracy,
        "random_accuracy": random_accuracy,
        "overall_accuracy": overall_accuracy,
        "always_persist_overall": always_persist_overall,
        "verdict": verdict,
        "slope_dist": {"rising": rising, "falling": falling, "flat": flat},
        "direction_counts": direction_counts,
        "most_common_dir": most_common_dir,
    }

# --- STEP 4: Write report ---

def step4_write_report(total_rows, kept_rows, dropped_rows,
                       analysis, type_summary, transitions):
    """Write the analysis report to references/BBLOC_TRANSITION_ANALYSIS.md."""

    # Build per-type table
    type_table_rows = ""
    for tt in sorted(type_summary.keys()):
        d = type_summary[tt]
        type_table_rows += (f"| {tt} | {d['count']} | {d['avg_slope']:.3f} | {d['pct_consistent']:.1f}% |\n")

    # Top 10 transitions by count
    trans_by_type = defaultdict(int)
    for t in transitions:
        trans_by_type[t["type"]] += 1
    top_transitions = sorted(trans_by_type.items(), key=lambda x: -x[1])[:15]
    top_trans_rows = ""
    for tt, cnt in top_transitions:
        top_trans_rows += f"| {tt} | {cnt} |\n"

    report = f"""# BBLoc Transition Analysis — V36.03

## 1. Data Summary

- **Total DUALTF rows**: {total_rows}
- **Rows kept (real HTF+MTF data)**: {kept_rows}
- **Rows dropped (no-data)**: {dropped_rows}
- **Filter criteria**: dropped rows where htf_scenario contains "X" OR htfbbloc==-1 OR mtf contains "X" OR mtfbbloc==-1

## 2. Transition Frequency

- **Consecutive row pairs**: {analysis['total_pairs']}
- **MTF transitions** (scenario changed): {analysis['transitions']}
- **Persistence rows** (scenario same): {analysis['persistence']}
- **Persistence base rate**: {analysis['persist_rate']:.1f}%

> This is the bar to beat — a predictor that always guesses "persist" gets {analysis['persist_rate']:.1f}% overall accuracy trivially. The TRANSITION accuracy is what matters.

## 3. Pre-Transition BBLoc Pattern (per transition type)

| Type | Count | Avg Pre-BBLoc Slope | % Consistent |
|------|-------|-------------------|-------------|
{type_table_rows}

**Slope consistency** = % of transitions where BBLoc slope direction matched the transition direction (rising->up, falling->down, flat->neutral).

## 4. BBLoc Slope Predictor — Transition Accuracy (The Key Number)

**Predictor logic**: Rising BBLoc slope (>0.3) over last 6 bars → predict up-continuation; falling slope (<-0.3) → predict down-reversal; flat → predict persist.

| Metric | Accuracy |
|--------|----------|
| **BBLoc slope predictor (transitions only)** | **{analysis['transition_accuracy']:.1f}%** |
| Baseline — always predict majority direction ({analysis['most_common_dir']}) | {analysis['always_majority_accuracy']:.1f}% |
| Baseline — random (3 classes) | {analysis['random_accuracy']:.1f}% |

### Overall Accuracy (all pairs, including persistence)

| Metric | Accuracy |
|--------|----------|
| BBLoc slope predictor (all pairs) | {analysis['overall_accuracy']:.1f}% |
| Baseline — always predict persist | {analysis['always_persist_overall']:.1f}% |

### Slope Distribution (all {analysis['total_pairs']} pairs)

| Direction | Count | % |
|-----------|-------|---|
| Rising (>0.3) | {analysis['slope_dist']['rising']} | {analysis['slope_dist']['rising']/analysis['total_pairs']*100:.1f}% |
| Falling (<-0.3) | {analysis['slope_dist']['falling']} | {analysis['slope_dist']['falling']/analysis['total_pairs']*100:.1f}% |
| Flat (<=0.3) | {analysis['slope_dist']['flat']} | {analysis['slope_dist']['flat']/analysis['total_pairs']*100:.1f}% |

### Transition Direction Distribution

| Direction | Count | % |
|-----------|-------|---|
| Up | {analysis['direction_counts']['up']} | {analysis['direction_counts']['up']/analysis['transitions']*100:.1f}% |
| Down | {analysis['direction_counts']['down']} | {analysis['direction_counts']['down']/analysis['transitions']*100:.1f}% |
| Neutral | {analysis['direction_counts']['neutral']} | {analysis['direction_counts']['neutral']/analysis['transitions']*100:.1f}% |

## 5. Top Transition Types

| Type | Count |
|------|-------|
{top_trans_rows}

## 6. Honest Verdict

**Verdict: {analysis['verdict']}**

"""

    if analysis['verdict'] == "BEATS_BASELINE":
        report += f"""The BBLoc slope predictor achieves **{analysis['transition_accuracy']:.1f}% accuracy on transitions** — meaningfully better than the majority baseline ({analysis['always_majority_accuracy']:.1f}%) and random ({analysis['random_accuracy']:.1f}%).

This suggests BBLoc trajectory DOES carry predictive signal for MTF scenario transitions. Part 4 (prediction layer) could be designed around this signal, particularly for transition types with high % consistency.
"""
    elif analysis['verdict'] == "MARGINAL":
        report += f"""The BBLoc slope predictor achieves **{analysis['transition_accuracy']:.1f}% accuracy on transitions** — better than random ({analysis['random_accuracy']:.1f}%) but not meaningfully better than always predicting the majority direction ({analysis['always_majority_accuracy']:.1f}%).

This is marginal signal. Fine BBLoc data provides some information but not enough to be a reliable predictor on its own.
"""
    else:
        report += f"""The BBLoc slope predictor achieves **{analysis['transition_accuracy']:.1f}% accuracy on transitions** — this is **not meaningfully better** than the majority baseline ({analysis['always_majority_accuracy']:.1f}%) or random ({analysis['random_accuracy']:.1f}%).

**Fine BBLoc data does not fix the prediction problem.** Just as coarse BBLoc (the 1.2% lesson) showed that overall accuracy is dominated by persistence, fine-grained BBLoc slope on the analysis set (real HTF+MTF data only) still fails to predict transition direction better than chance.

**Recommendation**: Use DualTF for identification and decision-making, not prediction. BBLoc trajectory alone is not a sufficient predictor of MTF scenario transitions.
"""

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\n=== STEP 4: Report Written ===")
    print(f"  {REPORT_PATH}")

# --- Main ---

def main():
    print("=" * 60)
    print("BBLoc Transition Analysis — V36.03")
    print("=" * 60)

    # Step 1
    all_rows, kept = step1_parse_and_filter()

    # Step 2
    transitions, persistence = step2_identify_transitions(kept)

    # Step 3
    analysis = step3_analyze(kept, transitions, persistence)

    # Step 4
    step4_write_report(
        total_rows=len(all_rows),
        kept_rows=len(kept),
        dropped_rows=len(all_rows) - len(kept),
        analysis=analysis,
        type_summary=analysis["type_summary"],
        transitions=transitions,
    )

    print("\n" + "=" * 60)
    print("Analysis complete.")
    print("=" * 60)

if __name__ == "__main__":
    main()
