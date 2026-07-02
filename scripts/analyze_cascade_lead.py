#!/usr/bin/env python3
"""
Cascade Lead Analysis — Measure whether M15 state flips LEAD M30 state transitions.

This is the LAST live hypothesis. Prediction is dead (1.2% / 43.9% / multi-input worse).
If this fails, detection-based Part 4 dies too → identification-only Part 5.

Verdict criteria (FIXED, no post-hoc adjustment):
  1. RECALL >= 40% of M30 transitions LED (lead >= 1) by same-target M15 flip.
  2. PRECISION LIFT >= 1.5x unconditional base rate for F and R targets.
  3. LEAD median >= 2 rows (>= 10 minutes).
All three must hold at K=12 for viability.
"""

import re
import sys
from collections import defaultdict

LOG_PATH = r"references/Backtest_data/V36.10/20260703_clean.log"
REPORT_PATH = "references/CASCADE_LEAD_ANALYSIS.md"

K_PRIMARY = 12
K_SENSITIVITIES = [6, 24]

# Verdict criteria
RECALL_THRESHOLD = 0.40
LIFT_THRESHOLD = 1.5
MEDIAN_LEAD_THRESHOLD = 2  # rows (10 minutes)


def parse_log(path):
    """Parse DUALTF rows from the log file."""
    rows = []
    pattern = re.compile(
        r"dt:(\d{4}\.\d{2}\.\d{2}\s+\d{2}:\d{2}:\d{2})"
        r".*?d1:state:(\w+)"
        r".*?h4:state:(\w+)"
        r".*?h1:state:(\w+)"
        r".*?m30:state:(\w+)"
        r".*?m15:state:(\w+)"
    )
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if "[DUALTF]" not in line:
                continue
            m = pattern.search(line)
            if not m:
                continue
            dt_str, d1_st, h4_st, h1_st, m30_st, m15_st = m.groups()
            rows.append({
                "dt": dt_str,
                "d1_state": d1_st,
                "h4_state": h4_st,
                "h1_state": h1_st,
                "m30_state": m30_st,
                "m15_state": m15_st,
            })
    return rows


def filter_rows(rows):
    """Drop rows where m15_state or m30_state == 'X'."""
    total = len(rows)
    kept = [r for r in rows if r["m15_state"] != "X" and r["m30_state"] != "X"]
    dropped = total - len(kept)
    return kept, total, dropped


def find_m30_transitions(rows):
    """Find rows where m30_state changes from the previous row."""
    transitions = []
    for i in range(1, len(rows)):
        if rows[i]["m30_state"] != rows[i - 1]["m30_state"]:
            transitions.append({
                "index": i,
                "from_state": rows[i - 1]["m30_state"],
                "to_state": rows[i]["m30_state"],
            })
    return transitions


def find_m15_flips(rows):
    """Find rows where m15_state changes from the previous row."""
    flips = []
    for i in range(1, len(rows)):
        if rows[i]["m15_state"] != rows[i - 1]["m15_state"]:
            flips.append({
                "index": i,
                "from_state": rows[i - 1]["m15_state"],
                "to_state": rows[i]["m15_state"],
            })
    return flips


def h4_direction(row):
    """HTF direction proxy: h4_state → 'up' if F, 'down' if R, else 'neutral'."""
    if row["h4_state"] == "F":
        return "up"
    elif row["h4_state"] == "R":
        return "down"
    else:
        return "neutral"


# ─── MEASUREMENT A ──────────────────────────────────────────────

def measurement_a(rows, m30_transitions, m15_flips, K):
    """
    For each M30 transition to state B at row i:
    search rows [i-K, i] for the most recent M15 flip TO the same state B.
    Classify: LED (lead>=1), SIMULTANEOUS (lead=0), NO LEAD.
    """
    # Build lookup: for each row index, the most recent M15 flip to state B at or before that index
    # m15_flip_to_state[i] = list of (flip_index, to_state) for flips at or before i
    # More efficient: build a dict mapping (row_index) → list of (flip_index, to_state)
    # But we need the most recent flip to a SPECIFIC state B in the window [i-K, i].

    # Build: for each row index, list of (flip_index, to_state) of all M15 flips up to that point
    flip_events = []  # list of (index, to_state)
    for flip in m15_flips:
        flip_events.append((flip["index"], flip["to_state"]))

    results = []
    for trans in m30_transitions:
        i = trans["index"]
        B = trans["to_state"]
        # Search backwards from i for the most recent M15 flip to state B in [i-K, i]
        found = False
        for flip_idx, flip_state in reversed(flip_events):
            if flip_idx > i:
                continue
            if flip_idx < i - K:
                break
            if flip_state == B:
                lead = i - flip_idx
                if lead >= 1:
                    cls = "LED"
                else:
                    cls = "SIMULTANEOUS"
                results.append({"m30_index": i, "target": B, "class": cls, "lead": lead})
                found = True
                break
        if not found:
            results.append({"m30_index": i, "target": B, "class": "NO LEAD", "lead": None})

    return results


# ─── MEASUREMENT B ──────────────────────────────────────────────

def measurement_b(rows, m15_flips, K):
    """
    For each M15 flip to state B at row j:
    search rows [j, j+K] for an M30 transition TO the same state B.
    Classify: FOLLOWED, NOT FOLLOWED.
    """
    results = []
    for flip in m15_flips:
        j = flip["index"]
        B = flip["to_state"]
        # Search forward from j for M30 transition to state B in [j, j+K]
        found = False
        for fwd in range(j, min(j + K + 1, len(rows))):
            if fwd < 1:
                continue
            if rows[fwd]["m30_state"] != rows[fwd - 1]["m30_state"]:
                if rows[fwd]["m30_state"] == B:
                    delay = fwd - j
                    results.append({"m15_index": j, "target": B, "followed": True, "delay": delay})
                    found = True
                    break
        if not found:
            results.append({"m15_index": j, "target": B, "followed": False, "delay": None})

    return results


def base_rate(rows, K):
    """
    Unconditional P(M30 transitions to state B within K rows) per target state.
    For each row i, check if M30 transitions to B in [i, i+K].
    Returns dict: state → probability.
    """
    states = ["F", "R", "S", "C"]
    rates = {}
    for B in states:
        count = 0
        total = 0
        for i in range(len(rows)):
            total += 1
            for fwd in range(i, min(i + K + 1, len(rows))):
                if fwd < 1:
                    continue
                if rows[fwd]["m30_state"] != rows[fwd - 1]["m30_state"]:
                    if rows[fwd]["m30_state"] == B:
                        count += 1
                        break
        rates[B] = count / total if total > 0 else 0.0
    return rates


# ─── MEASUREMENT C ──────────────────────────────────────────────

def measurement_c(meas_b_results, rows, K):
    """
    Repeat Measurement B precision, split by HTF filter for directional targets (F, R).
    AGREEING: M15→F with h4='up', or M15→R with h4='down'
    DISAGREEING: M15→F with h4='down', or M15→R with h4='up'
    NEUTRAL: h4 in {S, C, X}
    """
    buckets = {"AGREEING": {"followed": 0, "total": 0},
               "DISAGREEING": {"followed": 0, "total": 0},
               "NEUTRAL": {"followed": 0, "total": 0}}

    for res in meas_b_results:
        if res["target"] not in ("F", "R"):
            continue
        j = res["m15_index"]
        h4_dir = h4_direction(rows[j])

        if res["target"] == "F" and h4_dir == "up":
            bucket = "AGREEING"
        elif res["target"] == "R" and h4_dir == "down":
            bucket = "AGREEING"
        elif res["target"] == "F" and h4_dir == "down":
            bucket = "DISAGREEING"
        elif res["target"] == "R" and h4_dir == "up":
            bucket = "DISAGREEING"
        else:
            bucket = "NEUTRAL"

        buckets[bucket]["total"] += 1
        if res["followed"]:
            buckets[bucket]["followed"] += 1

    return buckets


# ─── REPORTING ──────────────────────────────────────────────────

def lead_histogram(led_results):
    """Histogram of lead values for LED class."""
    hist = defaultdict(int)
    for r in led_results:
        if r["class"] == "LED":
            hist[r["lead"]] += 1
    return dict(sorted(hist.items()))


def median(values):
    """Compute median of a list of numbers."""
    if not values:
        return 0
    s = sorted(values)
    n = len(s)
    if n % 2 == 1:
        return s[n // 2]
    else:
        return (s[n // 2 - 1] + s[n // 2]) / 2


def mean(values):
    """Compute mean of a list of numbers."""
    if not values:
        return 0
    return sum(values) / len(values)


def write_report(rows, total, kept_count, dropped, m30_transitions, m15_flips,
                 meas_a_results, meas_b_results, base_rates, meas_c_buckets,
                 k_sensitivity_results):
    """Write the CASCADE_LEAD_ANALYSIS.md report."""

    m30_count = len(m30_transitions)
    m15_count = len(m15_flips)

    # Measurement A stats
    led_count = sum(1 for r in meas_a_results if r["class"] == "LED")
    sim_count = sum(1 for r in meas_a_results if r["class"] == "SIMULTANEOUS")
    no_lead_count = sum(1 for r in meas_a_results if r["class"] == "NO LEAD")
    led_leads = [r["lead"] for r in meas_a_results if r["class"] == "LED"]
    led_hist = lead_histogram(meas_a_results)

    # Per-target split for Measurement A
    a_per_target = defaultdict(lambda: {"LED": 0, "SIMULTANEOUS": 0, "NO LEAD": 0, "leads": []})
    for r in meas_a_results:
        t = r["target"]
        a_per_target[t][r["class"]] += 1
        if r["class"] == "LED":
            a_per_target[t]["leads"].append(r["lead"])

    # Measurement B stats
    followed_count = sum(1 for r in meas_b_results if r["followed"])
    not_followed_count = m15_count - followed_count
    delays = [r["delay"] for r in meas_b_results if r["followed"]]

    # Per-target split for Measurement B
    b_per_target = defaultdict(lambda: {"followed": 0, "total": 0, "delays": []})
    for r in meas_b_results:
        t = r["target"]
        b_per_target[t]["total"] += 1
        if r["followed"]:
            b_per_target[t]["followed"] += 1
            b_per_target[t]["delays"].append(r["delay"])

    # Measurement C precision
    c_precision = {}
    for bucket, counts in meas_c_buckets.items():
        c_precision[bucket] = counts["followed"] / counts["total"] if counts["total"] > 0 else 0.0

    # ─── VERDICT ─────────────────────────────────────────────
    recall_pct = led_count / m30_count if m30_count > 0 else 0.0
    median_lead = median(led_leads) if led_leads else 0

    # Precision lift for F and R
    f_precision = b_per_target["F"]["followed"] / b_per_target["F"]["total"] if b_per_target["F"]["total"] > 0 else 0.0
    r_precision = b_per_target["R"]["followed"] / b_per_target["R"]["total"] if b_per_target["R"]["total"] > 0 else 0.0
    f_lift = f_precision / base_rates["F"] if base_rates["F"] > 0 else 0.0
    r_lift = r_precision / base_rates["R"] if base_rates["R"] > 0 else 0.0

    criterion1 = recall_pct >= RECALL_THRESHOLD
    criterion2 = f_lift >= LIFT_THRESHOLD and r_lift >= LIFT_THRESHOLD
    criterion3 = median_lead >= MEDIAN_LEAD_THRESHOLD

    viable = criterion1 and criterion2 and criterion3

    # ─── BUILD REPORT ────────────────────────────────────────
    lines = []
    lines.append("# Cascade Lead Analysis")
    lines.append("")
    lines.append(
        "> This is the LAST live hypothesis. Prediction is dead (1.2% / 43.9% / multi-input worse)."
    )
    lines.append(
        "> If this fails, detection-based Part 4 dies → identification-only Part 5."
    )
    lines.append("")

    lines.append("## Data Summary")
    lines.append("")
    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Total DUALTF rows | {total} |")
    lines.append(f"| Kept (m15 & m30 non-X) | {kept_count} |")
    lines.append(f"| Dropped (m15 or m30 = X) | {dropped} |")
    lines.append(f"| M30 transitions | {m30_count} |")
    lines.append(f"| M15 flips | {m15_count} |")
    lines.append("")

    # ─── MEASUREMENT A ───────────────────────────────────────
    lines.append("## Measurement A — Recall + Lead")
    lines.append("")
    lines.append(
        "**Question:** Did M15 warn before M30 moved? (backward: for each M30 transition, "
        "was there a same-target M15 flip in the window before?)"
    )
    lines.append("")
    lines.append(f"Window K={K_PRIMARY} rows ({K_PRIMARY * 5} minutes)")
    lines.append("")
    lines.append("| Class | Count | % of M30 transitions |")
    lines.append("|-------|-------|---------------------|")
    lines.append(f"| LED (lead >= 1) | {led_count} | {led_count / m30_count * 100:.1f}% |")
    lines.append(f"| SIMULTANEOUS (lead = 0) | {sim_count} | {sim_count / m30_count * 100:.1f}% |")
    lines.append(f"| NO LEAD | {no_lead_count} | {no_lead_count / m30_count * 100:.1f}% |")
    lines.append("")

    if led_leads:
        lines.append(f"**LED Lead Distribution:** median = {median(led_leads):.1f} rows ({median(led_leads) * 5:.0f} min), "
                      f"mean = {mean(led_leads):.1f} rows ({mean(led_leads) * 5:.0f} min)")
        lines.append("")
        lines.append("| Lead (rows) | Lead (min) | Count |")
        lines.append("|-------------|-----------|-------|")
        for lead_val, cnt in led_hist.items():
            lines.append(f"| {lead_val} | {lead_val * 5} | {cnt} |")
        lines.append("")

    lines.append("**Per-Target Breakdown:**")
    lines.append("")
    lines.append("| Target | LED | SIMULTANEOUS | NO LEAD | Total | LED % | Median Lead |")
    lines.append("|--------|-----|------------|---------|-------|-------|-------------|")
    for target in ["F", "R", "S", "C"]:
        d = a_per_target[target]
        t_total = d["LED"] + d["SIMULTANEOUS"] + d["NO LEAD"]
        led_pct = d["LED"] / t_total * 100 if t_total > 0 else 0.0
        med_lead = median(d["leads"]) if d["leads"] else "N/A"
        lines.append(f"| →{target} | {d['LED']} | {d['SIMULTANEOUS']} | {d['NO LEAD']} | {t_total} | {led_pct:.1f}% | {med_lead} |")
    lines.append("")

    # ─── MEASUREMENT B ───────────────────────────────────────
    lines.append("## Measurement B — Precision + Delay")
    lines.append("")
    lines.append(
        "**Question:** If I act on an M15 flip, does M30 follow? (forward: for each M15 flip, "
        "does M30 reach the same target state within the window?)"
    )
    lines.append("")
    lines.append(f"Window K={K_PRIMARY} rows ({K_PRIMARY * 5} minutes)")
    lines.append("")
    lines.append(f"**Overall Precision:** {followed_count}/{m15_count} = {followed_count / m15_count * 100:.1f}%")
    lines.append(f"**False Signals (NOT FOLLOWED):** {not_followed_count}/{m15_count} = {not_followed_count / m15_count * 100:.1f}%")
    lines.append("")

    if delays:
        lines.append(f"**Delay Distribution:** median = {median(delays):.1f} rows ({median(delays) * 5:.0f} min), "
                      f"mean = {mean(delays):.1f} rows ({mean(delays) * 5:.0f} min)")
        lines.append("")

    lines.append("**Per-Target Precision + Base Rate + Lift:**")
    lines.append("")
    lines.append(
        "> **Honesty anchor:** precision without base-rate comparison is meaningless. "
        "Lift = precision / base rate. Lift > 1 means M15 flip adds information over random."
    )
    lines.append("")
    lines.append("| Target | M15 Flip Precision | Base Rate | Lift | Followed / Total | Median Delay (rows) | Median Delay (min) |")
    lines.append("|--------|-------------------|-----------|------|------------------|---------------------|-------------------|")
    for target in ["F", "R", "S", "C"]:
        d = b_per_target[target]
        prec = d["followed"] / d["total"] if d["total"] > 0 else 0.0
        br = base_rates[target]
        lift = prec / br if br > 0 else 0.0
        med_delay = median(d["delays"]) if d["delays"] else "N/A"
        lines.append(
            f"| →{target} | {prec * 100:.1f}% | {br * 100:.1f}% | {lift:.2f}x | "
            f"{d['followed']}/{d['total']} | {med_delay} | {median(d['delays']) * 5:.0f}" if d["delays"] else f"| →{target} | {prec * 100:.1f}% | {br * 100:.1f}% | {lift:.2f}x | {d['followed']}/{d['total']} | N/A | N/A |"
        )
    lines.append("")

    # ─── MEASUREMENT C ───────────────────────────────────────
    lines.append("## Measurement C — HTF Filter Split")
    lines.append("")
    lines.append(
        "**Question:** Does the proposed HTF filter help? "
        "(for directional targets F/R, does agreeing HTF improve precision?)"
    )
    lines.append("")
    lines.append("| Bucket | Precision | Followed / Total |")
    lines.append("|--------|-----------|-----------------|")
    for bucket in ["AGREEING", "DISAGREEING", "NEUTRAL"]:
        counts = meas_c_buckets[bucket]
        prec = c_precision[bucket]
        lines.append(f"| {bucket} | {prec * 100:.1f}% | {counts['followed']}/{counts['total']} |")
    lines.append("")

    agreeing_prec = c_precision["AGREEING"]
    disagreeing_prec = c_precision["DISAGREEING"]
    if agreeing_prec > disagreeing_prec * 1.2:
        lines.append(
            f"**Filter helps:** AGREEING precision ({agreeing_prec * 100:.1f}%) > "
            f"DISAGREEING precision ({disagreeing_prec * 100:.1f}%) by {((agreeing_prec - disagreeing_prec) * 100):.1f}pp."
        )
    elif agreeing_prec < disagreeing_prec * 0.8:
        lines.append(
            f"**Filter hurts:** AGREEING precision ({agreeing_prec * 100:.1f}%) < "
            f"DISAGREEING precision ({disagreeing_prec * 100:.1f}%) — the filter would make things worse."
        )
    else:
        lines.append(
            f"**No filter effect:** AGREEING ({agreeing_prec * 100:.1f}%) ≈ "
            f"DISAGREEING ({disagreeing_prec * 100:.1f}%) — difference of only "
            f"{abs(agreeing_prec - disagreeing_prec) * 100:.1f}pp. The HTF filter idea is not validated."
        )
    lines.append("")

    # ─── SENSITIVITY ─────────────────────────────────────────
    lines.append("## Sensitivity — K=6 and K=24")
    lines.append("")
    lines.append("| K | Recall (LED%) | Precision | F Lift | R Lift | Median Lead | Criterion 1 | Criterion 2 | Criterion 3 |")
    lines.append("|---|-------------|-----------|--------|--------|-------------|-------------|-------------|-------------|")
    for k, sr in k_sensitivity_results.items():
        c1 = "PASS" if sr["recall_pct"] >= RECALL_THRESHOLD else "FAIL"
        c2 = "PASS" if sr["f_lift"] >= LIFT_THRESHOLD and sr["r_lift"] >= LIFT_THRESHOLD else "FAIL"
        c3 = "PASS" if sr["median_lead"] >= MEDIAN_LEAD_THRESHOLD else "FAIL"
        lines.append(
            f"| {k} | {sr['recall_pct'] * 100:.1f}% | {sr['precision'] * 100:.1f}% | "
            f"{sr['f_lift']:.2f}x | {sr['r_lift']:.2f}x | {sr['median_lead']:.1f} | {c1} | {c2} | {c3} |"
        )
    lines.append("")

    # ─── VERDICT ─────────────────────────────────────────────
    lines.append("## VERDICT")
    lines.append("")
    lines.append(
        f"**Criteria applied mechanically at K={K_PRIMARY} — no post-hoc adjustment.**"
    )
    lines.append("")
    lines.append(
        f"| Criterion | Threshold | Actual | Result |"
    )
    lines.append(f"|-----------|-----------|--------|--------|")
    lines.append(
        f"| 1. RECALL >= {RECALL_THRESHOLD * 100:.0f}% | >= {RECALL_THRESHOLD * 100:.0f}% | "
        f"{recall_pct * 100:.1f}% | {'PASS' if criterion1 else 'FAIL'} |"
    )
    lines.append(
        f"| 2. PRECISION LIFT >= {LIFT_THRESHOLD}x (F & R) | >= {LIFT_THRESHOLD}x | "
        f"F: {f_lift:.2f}x, R: {r_lift:.2f}x | {'PASS' if criterion2 else 'FAIL'} |"
    )
    lines.append(
        f"| 3. MEDIAN LEAD >= {MEDIAN_LEAD_THRESHOLD} rows | >= {MEDIAN_LEAD_THRESHOLD} | "
        f"{median_lead:.1f} | {'PASS' if criterion3 else 'FAIL'} |"
    )
    lines.append("")

    if viable:
        lines.append(
            "**CONCLUSION: VIABLE.** All three criteria met. "
            "The TransitionDetector redesign for Part 4 is grounded in data. "
            "A detection-based approach (act on M15 flips as M30 forecast) has empirical support."
        )
    else:
        failed = []
        if not criterion1:
            failed.append(f"RECALL ({recall_pct * 100:.1f}% < {RECALL_THRESHOLD * 100:.0f}%)")
        if not criterion2:
            failed.append(f"PRECISION LIFT (F: {f_lift:.2f}x, R: {r_lift:.2f}x < {LIFT_THRESHOLD}x)")
        if not criterion3:
            failed.append(f"MEDIAN LEAD ({median_lead:.1f} < {MEDIAN_LEAD_THRESHOLD} rows)")
        lines.append(
            f"**CONCLUSION: NOT VIABLE.** Criterion(s) failed: {', '.join(failed)}. "
            "The detection-based Part 4 (TransitionDetector) is NOT viable as designed. "
            "Recommendation: default to identification-only Part 5."
        )
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(
        f"*Analysis generated by `scripts/analyze_cascade_lead.py`. "
        f"Deterministic — re-running produces identical numbers.*"
    )

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    return viable, criterion1, criterion2, criterion3, recall_pct, f_lift, r_lift, median_lead


def run_sensitivity(rows, m30_transitions, m15_flips, K_values):
    """Run compact sensitivity for K=6 and K=24."""
    results = {}
    for K in K_values:
        ma = measurement_a(rows, m30_transitions, m15_flips, K)
        mb = measurement_b(rows, m15_flips, K)
        br = base_rate(rows, K)

        led_count = sum(1 for r in ma if r["class"] == "LED")
        led_leads = [r["lead"] for r in ma if r["class"] == "LED"]
        followed = sum(1 for r in mb if r["followed"])

        b_per_t = defaultdict(lambda: {"followed": 0, "total": 0})
        for r in mb:
            b_per_t[r["target"]]["total"] += 1
            if r["followed"]:
                b_per_t[r["target"]]["followed"] += 1

        f_prec = b_per_t["F"]["followed"] / b_per_t["F"]["total"] if b_per_t["F"]["total"] > 0 else 0
        r_prec = b_per_t["R"]["followed"] / b_per_t["R"]["total"] if b_per_t["R"]["total"] > 0 else 0
        f_l = f_prec / br["F"] if br["F"] > 0 else 0
        r_l = r_prec / br["R"] if br["R"] > 0 else 0

        results[K] = {
            "recall_pct": led_count / len(m30_transitions) if m30_transitions else 0,
            "precision": followed / len(m15_flips) if m15_flips else 0,
            "f_lift": f_l,
            "r_lift": r_l,
            "median_lead": median(led_leads) if led_leads else 0,
        }
    return results


def main():
    print("Parsing log file...")
    rows = parse_log(LOG_PATH)
    print(f"  Parsed {len(rows)} DUALTF rows.")

    print("Filtering rows (dropping m15 or m30 = X)...")
    kept, total, dropped = filter_rows(rows)
    print(f"  Kept {len(kept)}, dropped {dropped}.")

    print("Finding M30 transitions...")
    m30_transitions = find_m30_transitions(kept)
    print(f"  Found {len(m30_transitions)} M30 transitions.")

    print("Finding M15 flips...")
    m15_flips = find_m15_flips(kept)
    print(f"  Found {len(m15_flips)} M15 flips.")

    print(f"\n--- Measurement A (K={K_PRIMARY}) ---")
    meas_a = measurement_a(kept, m30_transitions, m15_flips, K_PRIMARY)
    led = sum(1 for r in meas_a if r["class"] == "LED")
    sim = sum(1 for r in meas_a if r["class"] == "SIMULTANEOUS")
    no_l = sum(1 for r in meas_a if r["class"] == "NO LEAD")
    led_leads = [r["lead"] for r in meas_a if r["class"] == "LED"]
    print(f"  LED: {led} ({led / len(meas_a) * 100:.1f}%), "
          f"SIMULTANEOUS: {sim} ({sim / len(meas_a) * 100:.1f}%), "
          f"NO LEAD: {no_l} ({no_l / len(meas_a) * 100:.1f}%)")
    if led_leads:
        print(f"  Median lead: {median(led_leads):.1f} rows ({median(led_leads) * 5:.0f} min)")

    print(f"\n--- Measurement B (K={K_PRIMARY}) ---")
    meas_b = measurement_b(kept, m15_flips, K_PRIMARY)
    followed = sum(1 for r in meas_b if r["followed"])
    print(f"  Followed: {followed}/{len(meas_b)} = {followed / len(meas_b) * 100:.1f}%")

    print("  Base rates...")
    base_r = base_rate(kept, K_PRIMARY)
    for st, br in base_r.items():
        print(f"    P(M30->'{st}' within {K_PRIMARY} rows) = {br * 100:.1f}%")

    b_per_t = defaultdict(lambda: {"followed": 0, "total": 0})
    for r in meas_b:
        b_per_t[r["target"]]["total"] += 1
        if r["followed"]:
            b_per_t[r["target"]]["followed"] += 1

    print("  Precision + Lift per target:")
    for t in ["F", "R", "S", "C"]:
        prec = b_per_t[t]["followed"] / b_per_t[t]["total"] if b_per_t[t]["total"] > 0 else 0
        lift = prec / base_r[t] if base_r[t] > 0 else 0
        print(f"    ->'{t}': precision={prec * 100:.1f}%, base_rate={base_r[t] * 100:.1f}%, lift={lift:.2f}x")

    print(f"\n--- Measurement C (K={K_PRIMARY}) ---")
    meas_c = measurement_c(meas_b, kept, K_PRIMARY)
    for bucket in ["AGREEING", "DISAGREEING", "NEUTRAL"]:
        c = meas_c[bucket]
        prec = c["followed"] / c["total"] if c["total"] > 0 else 0
        print(f"  {bucket}: {c['followed']}/{c['total']} = {prec * 100:.1f}%")

    print(f"\n--- Sensitivity ---")
    k_results = run_sensitivity(kept, m30_transitions, m15_flips, K_SENSITIVITIES)
    for k, sr in k_results.items():
        print(f"  K={k}: recall={sr['recall_pct'] * 100:.1f}%, "
              f"precision={sr['precision'] * 100:.1f}%, "
              f"F_lift={sr['f_lift']:.2f}x, R_lift={sr['r_lift']:.2f}x, "
              f"median_lead={sr['median_lead']:.1f}")

    # ─── VERDICT ─────────────────────────────────────────────
    recall_pct = led / len(m30_transitions) if m30_transitions else 0
    f_prec = b_per_t["F"]["followed"] / b_per_t["F"]["total"] if b_per_t["F"]["total"] > 0 else 0
    r_prec = b_per_t["R"]["followed"] / b_per_t["R"]["total"] if b_per_t["R"]["total"] > 0 else 0
    f_lift = f_prec / base_r["F"] if base_r["F"] > 0 else 0
    r_lift = r_prec / base_r["R"] if base_r["R"] > 0 else 0
    med_lead = median(led_leads) if led_leads else 0

    c1 = recall_pct >= RECALL_THRESHOLD
    c2 = f_lift >= LIFT_THRESHOLD and r_lift >= LIFT_THRESHOLD
    c3 = med_lead >= MEDIAN_LEAD_THRESHOLD

    print(f"\n--- VERDICT (K={K_PRIMARY}) ---")
    print(f"  Criterion 1 (RECALL >= {RECALL_THRESHOLD * 100:.0f}%): "
          f"{recall_pct * 100:.1f}% -> {'PASS' if c1 else 'FAIL'}")
    print(f"  Criterion 2 (LIFT >= {LIFT_THRESHOLD}x for F & R): "
          f"F={f_lift:.2f}x, R={r_lift:.2f}x -> {'PASS' if c2 else 'FAIL'}")
    print(f"  Criterion 3 (MEDIAN LEAD >= {MEDIAN_LEAD_THRESHOLD}): "
          f"{med_lead:.1f} -> {'PASS' if c3 else 'FAIL'}")

    viable = c1 and c2 and c3
    if viable:
        print("  ** VIABLE ** — TransitionDetector is grounded.")
    else:
        failed = []
        if not c1:
            failed.append(f"RECALL ({recall_pct * 100:.1f}%)")
        if not c2:
            failed.append(f"LIFT (F={f_lift:.2f}x, R={r_lift:.2f}x)")
        if not c3:
            failed.append(f"MEDIAN LEAD ({med_lead:.1f})")
        print(f"  ** NOT VIABLE ** — Failed: {', '.join(failed)}")

    # ─── WRITE REPORT ────────────────────────────────────────
    print(f"\nWriting report to {REPORT_PATH}...")
    write_report(kept, total, len(kept), dropped, m30_transitions, m15_flips,
                 meas_a, meas_b, base_r, meas_c, k_results)
    print("Done.")


if __name__ == "__main__":
    main()
