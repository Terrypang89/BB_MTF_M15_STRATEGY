#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Barrier-based first-touch test for TofySideway flag — simplified version.

Uses the same log file as label_base_rate.py:
    references/Backtest_data/V36.15/20260712_clean.log

Pre-registered barrier parameters:
    X = 10.0 (price offset)
    N = 8 M15 bars = 120 minutes
    First-touch on close_M5

For every M15 bar, split by the EA-logged flag from [BBTFImpact]:
    GROUP A: Sideway_val contains an S_n sub-type (flag present) ~1684 bars
    GROUP B: no S_ sub-type in Sideway_val                 ~5926 bars

Outcome per group:
    UP      = M5 close >= start_price + X first
    DOWN    = M5 close <= start_price - X first
    NEUTRAL = neither barrier touched (price stayed within +/- X)

Also report NEUTRAL% per S_ sub-type.
"""

import re
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

# Constants — DO NOT change
X = 10.0
N = 8

# Paths
repo_root = Path(__file__).resolve().parent.parent
log_path = repo_root / "references" / "Backtest_data" / "V36.15" / "20260712_clean.log"

# Regexes
M15_LINE_RE = re.compile(
    r"^(\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2})"       # timestamp
    r".*W_stage_M15:.*\[\s*(\d+)"                       # W_stage list, first value (may be empty)
    r".*diffMid_Trend_M15:\s*\[\s*(\d+\.?)"            # diffMid_Trend cur value
)

M5_LINE_RE = re.compile(
    r"^(\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2})"
    r".*close_M5:\s*\[\s*([\d.]+)"
)

BBTFIMPACT_RE = re.compile(r"Sideway_val:\s*\[(\d+)-S_(\d+)\]")


def parse_log():
    m15_data = []
    m5_data = []
    bbfimpacts = {}

    with log_path.open("r", encoding="utf-8") as f:
        for raw in f:
            raw = raw.rstrip("\r\n")
            m15_match = M15_LINE_RE.search(raw)
            if m15_match:
                ts, w_stage, dm = m15_match.groups()
                # Handle empty W_stage (e.g., "0") as 0, and full stage names like "FLY" aren't valid here
                # The first value in the list is what we capture — for empty lists it's still a digit 0
                w_stage_int = int(w_stage) if w_stage else 0
                m15_data.append((ts, w_stage_int, float(dm)))

            m5_match = M5_LINE_RE.search(raw)
            if m5_match:
                ts, close = m5_match.groups()
                m5_data.append((ts, float(close)))

            bbf_match = BBTFIMPACT_RE.search(raw)
            if bbf_match:
                bar_idx, subtype = bbf_match.groups()
                bbfimpacts[int(bar_idx)] = subtype

    # Sort by timestamp
    m15_data.sort(key=lambda x: x[0])
    m5_data.sort(key=lambda x: x[0])

    return m15_data, m5_data, bbfimpacts


def parse_ts(s):
    """Convert YYYY.MM.DD HH:MM:SS to datetime."""
    s_dash = s.replace(".", "-")
    return datetime.strptime(s_dash, "%Y-%m-%d %H:%M:%S")


def evaluate_barrier(start_price, m5_lookup, start_dt, end_dt):
    """
    Walk forward from start_dt through [M5] lines up to end_dt.
    Return outcome: "UP", "DOWN", or "NEUTRAL".
    If no M5 data in window -> NEUTRAL.
    """
    first_touch = "NEUTRAL"
    found_any = False

    for ts, price in m5_lookup:
        ts_dt = parse_ts(ts)
        if ts_dt < start_dt:
            continue
        if ts_dt > end_dt:
            break

        found_any = True
        up = price >= start_price + X
        down = price <= start_price - X

        if up and down:
            return "AMBIGUOUS"
        if up:
            first_touch = "UP"
            break
        if down:
            first_touch = "DOWN"
            break

    # No M5 data in window -> NEUTRAL
    return first_touch


def main():
    m15_data, m5_data, bbfimpacts = parse_log()
    print(f"[MAIN] Parsed: {len(m15_data)} M15, {len(m5_data)} M5")

    # Build M5 lookup (already sorted)
    m5_lookup = m5_data

    # Initialize counters
    group_a_n = 0
    group_a_up = 0
    group_a_down = 0
    group_a_neutral = 0

    group_b_n = 0
    group_b_up = 0
    group_b_down = 0
    group_b_neutral = 0

    subtype_counts = defaultdict(lambda: {"n": 0, "up": 0, "down": 0, "neutral": 0})

    # Iterate through M15 bars in order
    for i, (m15_ts, w_stage, dm) in enumerate(m15_data):
        m15_dt = parse_ts(m15_ts)
        end_dt = m15_dt + timedelta(minutes=120)

        # Get S_ subtype from BBTFImpact if present for this bar index
        s_subtype = bbfimpacts.get(i)

        # Determine the M5 start price: nearest [M5] at or before this M15 timestamp
        start_price = None
        for ts, price in m5_lookup:
            ts_dt = parse_ts(ts)
            if ts_dt <= m15_dt:
                start_price = price

        # If no prior M5 price, skip this bar (cannot evaluate)
        if start_price is None:
            group_b_n += 1
            continue

        # Evaluate barrier outcome
        outcome = evaluate_barrier(start_price, m5_lookup, m15_dt, end_dt)

        # GROUP A vs GROUP B
        if s_subtype is not None:
            group_a_n += 1
            if outcome == "UP":
                group_a_up += 1
            elif outcome == "DOWN":
                group_a_down += 1
            else:
                group_a_neutral += 1

            subtype_key = f"S_{s_subtype}"
            subtype_counts[subtype_key]["n"] += 1
            if outcome == "UP":
                subtype_counts[subtype_key]["up"] += 1
            elif outcome == "DOWN":
                subtype_counts[subtype_key]["down"] += 1
            else:
                subtype_counts[subtype_key]["neutral"] += 1
        else:
            group_b_n += 1
            if outcome == "UP":
                group_b_up += 1
            elif outcome == "DOWN":
                group_b_down += 1
            else:
                group_b_neutral += 1

    # Compute NEUTRAL percentages
    a_neutral_pct = (group_a_neutral / group_a_n * 100) if group_a_n > 0 else 0.0
    b_neutral_pct = (group_b_neutral / group_b_n * 100) if group_b_n > 0 else 0.0

    # Build sub-type report list
    subtype_report = []
    for key in sorted(subtype_counts.keys()):
        counts = subtype_counts[key]
        n = counts["n"]
        up = counts["up"]
        down = counts["down"]
        neutral = counts["neutral"]
        neutral_pct = (neutral / n * 100) if n > 0 else 0.0
        subtype_report.append((key, n, up, down, neutral, neutral_pct))

    # Verify: group totals must sum to total M15 bars parsed
    total_m15 = len(m15_data)
    assert group_a_n + group_b_n == total_m15, \
        f"Group totals ({group_a_n} + {group_b_n}) != total M15 ({total_m15})"

    # Write report
    report_path = repo_root / "references" / "VERIFY_SIDEWAY_FLAG.md"
    with report_path.open("w", encoding="utf-8") as f:
        f.write("# VERIFY_SIDEWAY_FLAG — TofySideway S_ flag test\n\n")
        f.write(f"**Data source**: {log_path}\n")
        f.write(f"**Barrier parameters**: X = {X}, N = {N} M15 bars (120 min)\n")
        f.write(f"**Parsed totals**: {total_m15} M15 lines, {len(m5_data)} M5 lines\n\n")

        # Two-group summary
        f.write("## Two-Group Summary\n\n")
        f.write("| Group | n  | UP | DOWN | NEUTRAL | NEUTRAL% |\n")
        f.write("|-------|----|----|------|---------|----------|\n")
        f.write(f"| A (S_ flag present) | {group_a_n:4d} | {group_a_up:3d} | {group_a_down:3d} | {group_a_neutral:5d} | {a_neutral_pct:7.2f}% |\n")
        f.write(f"| B (no S_ flag)      | {group_b_n:4d} | {group_b_up:3d} | {group_b_down:3d} | {group_b_neutral:5d} | {b_neutral_pct:7.2f}% |\n")

        # Verification statements
        f.write("\n## Verification\n\n")
        f.write(f"1. Group A n + Group B n = {group_a_n} + {group_b_n} = **{total_m15}** M15 bars parsed.\n")
        f.write(f"2. NEUTRAL% for Group A: **{a_neutral_pct:.2f}%**\n")
        f.write(f"3. NEUTRAL% for Group B: **{b_neutral_pct:.2f}%**\n")

        delta = a_neutral_pct - b_neutral_pct
        if delta > 0:
            f.write(f"\n4. **A_neutral% is higher** than B_neutral% by **{delta:.1f} percentage points**.\n")
            f.write("   This suggests the TofySideway flag *may* correctly identify sideways price.\n")
        elif delta < 0:
            f.write(f"\n4. **A_neutral% is lower** than B_neutral% by **{-delta:.1f} percentage points**.\n")
            f.write("   The flag does not carry the expected information about sideways price.\n")
        else:
            f.write("\n4. NEUTRAL percentages are equal — flag carries no information.\n")

        # Per-sub-type breakdown
        f.write("\n## Per-Sub-Type Breakdown\n\n")
        f.write("| Sub-type | n  | UP | DOWN | NEUTRAL | NEUTRAL% |\n")
        f.write("|----------|----|----|------|---------|----------|\n")

        for key, n, up, down, neutral, neutral_pct in subtype_report:
            if n >= 50:
                f.write(f"| {key} | {n:3d} | {up:3d} | {down:3d} | {neutral:5d} | {neutral_pct:7.2f}% |\n")
            else:
                f.write(f"| {key} | {n:3d} | {up:3d} | {down:3d} | {neutral:5d} | {neutral_pct:7.2f}% (low confidence) |\n")

    print("Report written to:", report_path)


if __name__ == "__main__":
    main()
