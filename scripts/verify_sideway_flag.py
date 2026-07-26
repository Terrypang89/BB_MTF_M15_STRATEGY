#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Barrier-based first-touch test for TofySideway flag.

Reuses the barrier method from scripts/label_base_rate.py:
    X = 10.0 (price offset)
    N = 8 M15 bars = 120 minutes
    First-touch on close_M5

For every M15 bar, split by EA-logged flag from [BBTFImpact]:
    GROUP A: sideway_flag present  (S_n)
    GROUP B: no sideway_flag

Outcome per group:
    UP      = price hit start + X first
    DOWN    = price hit start - X first
    NEUTRAL = neither barrier touched

Also report NEUTRAL% per S_ sub-type.
"""

import json
from pathlib import Path
from collections import defaultdict

# Pre-registered barrier parameters — DO NOT change
X = 10.0
N = 8  # M15 bars, first-touch on close_M5

# Paths
repo_root = Path(__file__).parent.parent
ea_log_path = repo_root / "logs" / "TofyTrade5_clean.json"

# Read EA log
with ea_log_path.open("r", encoding="utf-8") as f:
    data = json.load(f)

# Build a map of (bar_idx, tf) -> fields
records_by_bar = defaultdict(dict)
for entry in data:
    bar_idx = entry["bar_idx"]
    tf = entry["tf"]
    records_by_bar[(bar_idx, tf)][entry["field"]] = entry

def extract_fields(bar_idx, tf):
    """Extract flag and close price from BBTFImpact at M5."""
    rec = records_by_bar.get((bar_idx, tf), {})
    flag = rec.get("sideway_flag")
    close = rec.get("close")
    return flag, float(close) if close is not None else None

# Parse M15 bars (tf == "M15")
m15_bars = [b for b in range(len(data)) if records_by_bar.get((b, "M15"), {}).get("tf") == "M15"]
total_m15 = len(m15_bars)

# Group A: sideway_flag present
group_a_n = 0
group_a_up = 0
group_a_down = 0
group_a_neutral = 0

# Group B: no flag (None)
group_b_n = 0
group_b_up = 0
group_b_down = 0
group_b_neutral = 0

# Sub-type counts
subtype_counts = defaultdict(lambda: {"n": 0, "up": 0, "down": 0, "neutral": 0})

for bar in m15_bars:
    flag, close = extract_fields(bar, "M15")
    if flag is None:
        # GROUP B — no flag logged at this M15 bar
        group_b_n += 1
        continue

    # Flag logged — now evaluate the barrier outcome over the next N M15 bars
    up = False
    down = False

    for offset in range(1, N + 1):
        next_bar = bar + offset
        if next_bar >= total_m15:
            break
        flag_next, _ = extract_fields(next_bar, "M15")
        if flag_next is not None:
            # A subsequent sideway_flag means price stayed in the middle;
            # treat as NEUTRAL. We do NOT count this as a barrier hit.
            up = True
            down = True
            break

    if close is not None:
        up_bar = records_by_bar.get((bar, "M15"), {}).get("close") or 0
        down_bar = records_by_bar.get((bar, "M15"), {}).get("close") or 0
        if close >= up_bar + X:
            up = True
        elif close <= down_bar - X:
            down = True

    # Determine outcome for this bar
    if not up and not down:
        outcome = "NEUTRAL"
    elif up and not down:
        outcome = "UP"
    else:
        outcome = "DOWN"

    # Group A totals
    group_a_n += 1
    if outcome == "UP":
        group_a_up += 1
    elif outcome == "DOWN":
        group_a_down += 1
    else:
        group_a_neutral += 1

    # Sub-type totals
    subtype_key = f"S_{flag}"
    subtype_counts[subtype_key]["n"] += 1
    if outcome == "UP":
        subtype_counts[subtype_key]["up"] += 1
    elif outcome == "DOWN":
        subtype_counts[subtype_key]["down"] += 1
    else:
        subtype_counts[subtype_key]["neutral"] += 1

# Compute NEUTRAL percentages
a_neutral_pct = (group_a_neutral / group_a_n * 100) if group_a_n > 0 else 0.0
b_neutral_pct = (group_b_neutral / group_b_n * 100) if group_b_n > 0 else 0.0

# Build sub-type report
subtype_report = []
for key in sorted(subtype_counts.keys()):
    counts = subtype_counts[key]
    n = counts["n"]
    up = counts["up"]
    down = counts["down"]
    neutral = counts["neutral"]
    neutral_pct = (neutral / n * 100) if n > 0 else 0.0
    subtype_report.append((key, n, up, down, neutral, neutral_pct))

# Safety: group totals must sum to total M15
assert group_a_n + group_b_n == total_m15, "Group totals do not match parsed M15 bars"

# Write report
report_path = repo_root / "references" / "VERIFY_SIDEWAY_FLAG.md"
with report_path.open("w", encoding="utf-8") as f:
    f.write("# VERIFY_SIDEWAY_FLAG — TofySideway S_ flag test\n\n")
    f.write(f"**Barrier parameters**: X = {X}, N = {N} M15 bars (first-touch on close_M5)\n\n")

    # Group summary
    f.write("## Two-Group Summary\n\n")
    f.write("| Group | n  | UP | DOWN | NEUTRAL | NEUTRAL% |\n")
    f.write("|-------|----|----|------|---------|----------|\n")
    f.write(f"| A (flag present) | {group_a_n:4d} | {group_a_up:3d} | {group_a_down:3d} | {group_a_neutral:5d} | {a_neutral_pct:7.2f}% |\n")
    f.write(f"| B (no flag)      | {group_b_n:4d} | {group_b_up:3d} | {group_b_down:3d} | {group_b_neutral:5d} | {b_neutral_pct:7.2f}% |\n")

    # Verification
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

    # Sub-type breakdown
    f.write("\n## Per-Sub-Type Breakdown\n\n")
    f.write("| Sub-type | n  | UP | DOWN | NEUTRAL | NEUTRAL% |\n")
    f.write("|----------|----|----|------|---------|----------|\n")

    for key, n, up, down, neutral, neutral_pct in subtype_report:
        if n >= 50:
            f.write(f"| {key} | {n:3d} | {up:3d} | {down:3d} | {neutral:5d} | {neutral_pct:7.2f}% |\n")
        else:
            f.write(f"| {key} | {n:3d} | {up:3d} | {down:3d} | {neutral:5d} | {neutral_pct:7.2f}% (low confidence) |\n")

# Done — output to stdout as well
print("Report written to:", report_path)
