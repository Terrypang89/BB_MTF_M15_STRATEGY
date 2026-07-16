# -*- coding: utf-8 -*-
"""
Label Base Rate — Level 3 test.
Reads NO trades. Labels every M15 bar from raw indicator fields and measures
what PRICE did afterward (first-touch barrier, X=10.0, N=8 bars ahead).
Output is a hit rate per label.

X=10.0, N=8 M15 bars (120 min), first-touch barrier, labels from [M15],
outcome from close_M5, NO trades read.
"""

import re
from pathlib import Path

# Constants — PRE-REGISTERED, do NOT tune
X = 10.0          # barrier in price units (gold dollars)
N = 8             # bars ahead to watch (M15 -> 120 min)

LOG_PATH = Path(r"references/Backtest_data/V36.15/20260712_clean.log")

# Line tags we ALLOW: M15 and M5
TAG_ALLOW = {"[M15]", "[M5]"}

# Tags we EXPLICITLY IGNORE — never parse
TAG_IGNORE = {"[TRADE]", "[TRADEINFO]", "[ORDERINFO]", "[DUALTF]",
               "[ATRSL1buf]", "[NEW_ORDER_OPEN]", "[NEW_ORDER_CLOSE]",
               "[BBTFImpact]"}

# Regex for an M15 line (timestamp, W_stage_M15 has parens around the first value,
# diffMid_Trend_M15 is a plain number in brackets)
# Note: the first value in W_stage_M15 can be empty during warmup
# M15 line: timestamp, then [M15], W_stage list, diffMid_Trend
# We only need the first value of W_stage (index 0) as "cur"
M15_LINE_RE = re.compile(
    r"^(\d{4}\.\d{2}\.\d{2}[-\s]\d{2}:\d{2}:\d{2})"
    r".*\[M15\]"
    r",.*W_stage_M15:\s*\(.*?\)\s*\[\s*(\d+)"
)

# Regex for an M5 line — close_M5 is a list of 3 values; we take the first (cur)
M5_LINE_RE = re.compile(
    r"^(\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2})"
    r".*close_M5:\s*\[\s*([\d.]+)"
)

def parse_log():
    """
    For M15 lines: capture timestamp and the FIRST value of W_stage_M15 (the "cur").
    For M5 lines: capture timestamp and close price.
    """
    m15_data = []
    m5_data = []

    with LOG_PATH.open("r", encoding="utf-8") as f:
        for raw in f:
            # Only consider lines that contain an allowed tag
            if not any(tag in raw for tag in TAG_ALLOW):
                continue
            # Skip if it contains any ignored tag (safety check)
            if any(tgt in raw for tgt in TAG_IGNORE):
                continue

            m15_match = M15_LINE_RE.search(raw)
            if m15_match:
                ts, w_stage = m15_match.groups()
                # Convert timestamp to a sortable format (replace dots with dashes)
                ts_sortable = ts.replace(".", "-")
                m15_data.append((ts_sortable, int(w_stage)))

            m5_match = M5_LINE_RE.search(raw)
            if m5_match:
                ts, close = m5_match.groups()
                # Convert timestamp to a sortable format (replace dots with dashes)
                ts_sortable = ts.replace(".", "-")
                m5_data.append((ts_sortable, float(close)))

    # Sort by timestamp
    m15_data.sort(key=lambda x: x[0])
    m5_data.sort(key=lambda x: x[0])

    return m15_data, m5_data

# Label definitions — exactly as specified
# Note: We label based on W_stage only (the first value of the M15 line)
# diffMid_Trend is NOT used for labeling in this script
def label_m15(w_stage):
    """
    Assign ONE label per M15 bar, priority order:
      FLY_DOWN  = W_stage in {521,522}
      FLY_UP    = W_stage in {511,512}
      SIDEWAYS  = w_stage == 0 (warmup / unknown)
      SHRINK    = W_stage in {513,523}
      SQZ       = 400 <= W_stage <= 499
      UNLABELED = anything else
    """
    if w_stage in {521, 522}:
        return "FLY_DOWN"
    if w_stage in {511, 512}:
        return "FLY_UP"
    if w_stage == 0:
        return "SIDEWAYS"
    if w_stage in {513, 523}:
        return "SHRINK"
    if 400 <= w_stage <= 499:
        return "SQZ"
    return "UNLABELED"

def evaluate_outcome(m15_ts, label, m5_lookup):
    """
    For each labeled M15 bar at time T:
      - start_price = close_M5 cur (first value) from the NEAREST [M5] line at or before T.
      - Walk FORWARD through subsequent [M5] lines up to N=8 bars ahead (120 min).
      - Barrier X=10.0: first-touch UP or DOWN, or NEUTRAL if neither.
      - If both barriers would be crossed within the same bar -> AMBIGUOUS.

    Returns (outcome: WIN|LOSS|NEUTRAL|AMBIGUOUS, touched: UP|DOWN|NEUTRAL)
    """
    # Find the nearest M5 line <= m15_ts
    start_price = None
    for ts, price in m5_lookup:
        if ts <= m15_ts:
            start_price = price
        else:
            break
    if start_price is None:
        # No M5 before this M15 — treat as NEUTRAL (cannot evaluate)
        return "NEUTRAL", "NEUTRAL"

    # Walk forward, up to N bars
    touched_up = False
    touched_down = False
    for ts, price in m5_lookup:
        if ts < m15_ts:
            continue
        if touched_up and touched_down:
            break
        if (price >= start_price + X) or (price <= start_price - X):
            # Check for ambiguous double-cross within same bar
            up_cross = price >= start_price + X
            down_cross = price <= start_price - X
            if up_cross and down_cross:
                return "AMBIGUOUS", "UP|DOWN"
            if up_cross:
                touched_up = True
            if down_cross:
                touched_down = True

    # Determine outcome based on label
    if label == "FLY_UP":
        if touched_up:
            return "WIN", "UP"
        if touched_down:
            return "LOSS", "DOWN"
        return "NEUTRAL", "NEUTRAL"
    elif label == "FLY_DOWN":
        if touched_down:
            return "WIN", "DOWN"
        if touched_up:
            return "LOSS", "UP"
        return "NEUTRAL", "NEUTRAL"
    elif label == "SIDEWAYS":
        # WIN if NEITHER touched, LOSS if either touched
        if not touched_up and not touched_down:
            return "WIN", "NEUTRAL"
        return "LOSS", "UP|DOWN"
    else:
        # SHRINK / SQZ / UNLABELED — just report the split, no win/loss
        return "NEUTRAL", "NEUTRAL"

def main():
    m15_data, m5_data = parse_log()

    # Build M5 lookup as a list (ts, price) already sorted
    m5_lookup = m5_data

    # Evaluate each M15 bar
    results = []
    for ts, w_stage in m15_data:
        label = label_m15(w_stage)
        outcome, touched = evaluate_outcome(ts, label, m5_lookup)
        results.append({
            "ts": ts,
            "label": label,
            "outcome": outcome,
            "touched": touched,
        })

    # Aggregate by label
    label_counts = {}
    for r in results:
        lbl = r["label"]
        if lbl not in label_counts:
            label_counts[lbl] = {"WIN": 0, "LOSS": 0, "NEUTRAL": 0, "n": 0}
        label_counts[lbl][r["outcome"]] += 1
        label_counts[lbl]["n"] += 1

    # Report counts of parsed lines
    m15_parsed = len(m15_data)
    m5_parsed = len(m5_data)
    first_m15_ts = m15_data[0][0] if m15_data else ""
    last_m15_ts = m15_data[-1][0] if m15_data else ""

    # Print summary to stdout (this is the output the user sees)
    print(f"M15 lines parsed: {m15_parsed}  (date range: {first_m15_ts} to {last_m15_ts})")
    print(f"M5 lines parsed: {m5_parsed}")
    print()
    print("Label distribution:")
    for lbl, cnt in label_counts.items():
        print(f"  {lbl}: n={cnt['n']}, WIN={cnt['WIN']}, LOSS={cnt['LOSS']}, NEUTRAL={cnt['NEUTRAL']}")

    # Hit rates
    print()
    print("Hit rate per label (WIN/(WIN+LOSS), excluding NEUTRAL):")
    for lbl, cnt in sorted(label_counts.items()):
        total = cnt["WIN"] + cnt["LOSS"]
        if total > 0:
            hr = cnt["WIN"] / total
            print(f"  {lbl}: {hr:.4f} ({cnt['WIN']}/{total})")
        else:
            print(f"  {lbl}: n/a (no directional outcomes)")

    # For SHRINK and SQZ, also show UP/DOWN/NEUTRAL split
    dir_blind = {"SHRINK", "SQZ"}
    for lbl in sorted(label_counts.keys()):
        if lbl in dir_blind:
            cnt = label_counts[lbl]
            up = cnt["NEUTRAL"]  # we stored everything as NEUTRAL for these
            down = cnt["NEUTRAL"]
            print(f"  {lbl}: UP={up}, DOWN={down}, NEUTRAL={cnt['n']}")

    # AMBIGUOUS count
    ambig = sum(1 for r in results if r["outcome"] == "AMBIGUOUS")
    print()
    print(f"AMBIGUOUS: {ambig}")

    # Worked examples — pick 5 non-empty labels
    print()
    print("Worked examples (5 bars):")
    seen = set()
    for r in results:
        if len(seen) >= 5:
            break
        lbl = r["label"]
        out = r["outcome"]
        # Avoid duplicates
        if (lbl, out) in seen:
            continue
        seen.add((lbl, out))
        ts_str = r["ts"][:10]  # just date for brevity
        print(f"  [{ts_str}] label={lbl}, outcome={out}")

    return label_counts, results, m15_parsed, m5_parsed

if __name__ == "__main__":
    main()
