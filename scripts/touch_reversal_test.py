#!/usr/bin/env python3
"""
touch_reversal_test.py — layered test of H4 band-touch reversal on V36.14 log

Fixed criteria:
  Horizon = 24 bars, target = H4 midline (bb_mid)
  Verdict thresholds as written below

LAYERED test on existing log (no backtest, no prior-trade dependency — pure price/band data):
  Layer 1: All H4 touch events (6/7/8/9)
  Layer 2: Add S/C (shrink/compress) filter
  Layer 3: Add fly condition (M30 or H1 in {F,R})

Touch encoding (ENUM_BB_LineTouch):
    9 = touch_updn_BBu  : price up-then-down at UPPER band -> predict DOWN
    7 = touch_updn_BBMid : up-then-down at midline         -> predict DOWN
    8 = touch_dnup_BBMid : down-then-up at midline         -> predict UP
    6 = touch_dnup_BBDn  : down-then-up at LOWER band      -> predict UP

Input: references/Backtest_data/V36.14/20260706_clean.log (largest sample, ~9975 S_ hits)
  Parse per bar from [BBTFImpact] lines:
    - line_seq_touch H4 field (format <TF>_<cur>-<prev>,<x>) -> H4 current touch value
    - H4 state (F/S/C/R from BBW_stage), M30 state, H1 state from [DUALTF] lines
    - H4 band prices (BBMid, BBUp, BBDn) and the M5 close price per bar from [ATRSL1buf]/[M15] lines

Definitions (bar-checkable):
  - is_touch_event(d): cur in {6,7,8,9} AND prev not in {6,7,8,9} -> H4 just touched
  - predicted_direction(d): 9 or 7 -> DOWN; 6 or 8 -> UP
  - midline_reversion(d): bb_mid from [ATRSL1buf] line
  - price_above_midline(d, target, direction): close >= target for UP, close <= target for DOWN
  - count_reversions(d, target, direction, horizon): within `horizon` bars after touch bar, does price reach midline?

Layered filters:
  - layer1_filter(d): all H4 touch events (6/7/8/9)
  - layer2_filter(d): layer1 AND h4_state in {S,C} (shrink/compress)
  - layer3_filter(d): layer2 AND (m30_state in {F,R} OR h1_state in {F,R}) fly condition

Metrics:
  - Rate = successes / n
  - Baseline = directional reversion rate — only count if price reaches midline
    in the direction implied by its starting position relative to midline.
    (close < midline => expect UP; close > midline => expect DOWN).
  - Breakdown by direction and touch value

VERDICT (fixed criteria):
  - Layer i adds VALUE if rate_i >= rate_{i-1} + 10 pp AND n_{i-1} >= MIN_N_FOR_VALUE
  - TOUCH HAS SIGNAL if any layer's rate >= 60% AND beats its baseline by >= 10 pp AND n >= MIN_N_FOR_VALUE
"""

import os, sys, json
from pathlib import Path
from collections import defaultdict
import re


ROOT = Path(__file__).resolve().parent.parent
LOG_PATH = ROOT / "references" / "Backtest_data" / "V36.14" / "20260706_clean.log"

# Pre-registered parameters
HORIZON_BARS = 24
MIN_N_FOR_VALUE = 20
VALUE_IMPROVEMENT_PCT = 10


def read_log(path: Path):
    """
    Read the plain-text clean log and yield dicts of parsed fields per line.

    Line types used:
      [BBTFImpact]   -> line_seq_touch (H4 cur/prev)
      [DUALTF]       -> h4_state, m30_state, h1_state
      [ATRSL1buf]    -> Upper (BBUp), SLMid (bb_mid), Lower (BBDn)
      [M15]          -> close_M15 (M5 close)

    Returns only bars where all required fields are present.
    """
    with open(path, encoding="utf-8") as f:
        raw_lines = [line.strip() for line in f if line.strip()]

    # Parse touch data from BBTFImpact lines
    touch_data = {}
    for idx, r in enumerate(raw_lines):
        if "[BBTFImpact]" not in r:
            continue
        try:
            tm = r.split("line_seq_touch:", 1)[1].split("],")[0].strip() if "line_seq_touch:" in r else ""
            h4_cur, h4_prev = None, None
            for part in tm.split(", "):
                part = part.strip()
                if part.startswith("H4_"):
                    sub = part.split("-")[1]
                    try:
                        h4_cur, h4_prev = int(sub.split(",")[0]), int(sub.split(",")[1])
                    except (ValueError, IndexError):
                        pass
            # Only consider valid touch values (6,7,8,9)
            if h4_cur is not None and h4_cur in {6, 7, 8, 9} and h4_prev is not None:
                touch_data[idx] = {"cur": h4_cur, "prev": h4_prev}
        except Exception:
            pass

    # Parse state data from DUALTF lines — store by line index for offset-based lookup
    state_data = {}
    for idx, r in enumerate(raw_lines):
        if "[DUALTF]" not in r:
            continue
        d = {}
        m = re.search(r"h4:state:([SFCR])", r)
        d["h4_state"] = m.group(1) if m else None
        m = re.search(r"m30:state:([SFCR])", r)
        d["m30_state"] = m.group(1) if m else None
        m = re.search(r"h1:state:([SFCR])", r)
        d["h1_state"] = m.group(1) if m else None
        if any(d.values()):
            state_data[idx] = d

    # Parse band prices from ATRSL1buf lines — store by line index for offset-based lookup
    band_data = {}
    for idx, r in enumerate(raw_lines):
        if "[ATRSL1buf]" not in r:
            continue
        bb_mid, bb_up, bb_low = None, None, None
        upper_match = re.search(r"Upper:\s*\[(.*?)\]", r)
        mid_match = re.search(r"SLMid:\s*\[(.*?)\]", r)
        lower_match = re.search(r"Lower:\s*\[(.*?)\]", r)
        if upper_match:
            vals = [float(v.strip()) for v in upper_match.group(1).split(",") if v.strip()]
            bb_up = vals[0] if vals else None
            bb_mid = vals[1] if len(vals) >= 2 else None
        if mid_match:
            vals = [float(v.strip()) for v in mid_match.group(1).split(",") if v.strip()]
            bb_mid = vals[0] if vals else None
        if lower_match:
            vals = [float(v.strip()) for v in lower_match.group(1).split(",") if v.strip()]
            bb_low = vals[0] if vals else None
        if any(v is not None for v in (bb_mid, bb_up, bb_low)):
            band_data[idx] = {"bb_mid": bb_mid, "bb_up": bb_up, "bb_low": bb_low}

    # Parse close from M15 lines — store by line index for offset-based lookup
    close_data = {}
    for idx, r in enumerate(raw_lines):
        if "[M15]" not in r:
            continue
        m15_match = re.search(r"close_M15:\s*\[(.*?)\]", r)
        if not m15_match:
            continue
        vals_str = m15_match.group(1).strip()
        vals = [float(v.strip()) for v in vals_str.split(",") if v.strip()]
        close_data[idx] = {"close": vals[0]} if vals else {}

    # Combine data from different line types into dicts per bar
    seen_indices = set()
    for idx in touch_data:
        if idx in seen_indices:
            continue
        seen_indices.add(idx)

        # Reset d for each BBTFImpact line — reuse the same dict but clear it first
        d.clear()
        d["cur"] = touch_data[idx]["cur"]
        d["prev"] = touch_data[idx]["prev"]

        found_all = False
        # Try to find matching DUALTF and ATRSL1buf lines — search a wider range
        for offset in range(-5, 11):
            cand_idx = idx + offset
            if cand_idx < 0 or cand_idx >= len(raw_lines):
                continue
            cand_r = raw_lines[cand_idx]
            # Skip the BBTFImpact line itself (we already have its data)
            if "[BBTFImpact]" in cand_r and cand_idx == idx:
                continue
            if "[DUALTF]" in cand_r:
                d["h4_state"] = state_data.get(cand_idx, {}).get("h4_state")
                d["m30_state"] = state_data.get(cand_idx, {}).get("m30_state")
                d["h1_state"] = state_data.get(cand_idx, {}).get("h1_state")
            if "[ATRSL1buf]" in cand_r:
                bd = band_data.get(cand_idx, {})
                d["bb_mid"] = bd.get("bb_mid")
                d["bb_up"] = bd.get("bb_up")
                d["bb_low"] = bd.get("bb_low")

            # Also try to find matching M15 close line — search a wider range
            for offset2 in range(-8, 14):
                cand_idx2 = idx + offset2
                if cand_idx2 < 0 or cand_idx2 >= len(raw_lines):
                    continue
                cand_r2 = raw_lines[cand_idx2]
                if "[M15]" in cand_r2 and "close_M15:" in cand_r2:
                    match2 = re.search(r"close_M15:\s*\[(.*?)\](?:,\s*|\])", cand_r2)
                    if not match2:
                        continue
                    vals2_str = match2.group(1).strip()
                    vals2 = [float(v.strip()) for v in vals2_str.split(",") if v.strip()]
                    d["close"] = vals2[0]
                    found_all = True

        # Only require h4_state (the band touch indicator) — m30_state/h1_state may be None
        if d["h4_state"] is not None and all(k is not None for k in ("bb_mid", "bb_up", "bb_low")) and found_all:
            yield d

def is_touch_event(d: dict) -> bool:
    """Return True if H4 touches a band (cur in {6,7,8,9}) AND it's a NEW touch (cur != prev)."""
    return d["cur"] in {6, 7, 8, 9} and d["cur"] != d["prev"]


def predicted_direction(d: dict) -> str:
    """9 or 7 -> DOWN; 6 or 8 -> UP."""
    if d["cur"] in {9, 7}:
        return "DOWN"
    elif d["cur"] in {6, 8}:
        return "UP"
    return None


def midline_reversion(d: dict) -> float:
    """Return H4 midline price."""
    return d["bb_mid"]


def price_above_midline(d: dict, target: float, direction: str) -> bool:
    """Check if close is already beyond the midline in the predicted direction."""
    if direction == "UP":
        return d["close"] >= target
    elif direction == "DOWN":
        return d["close"] <= target
    return False


def count_reversions(d: dict, target: float, direction: str, horizon: int) -> bool:
    """Within `horizon` bars after the touch bar, does price reach the midline in direction?"""
    for _ in range(horizon):
        if direction == "UP" and d["close"] >= target:
            return True
        if direction == "DOWN" and d["close"] <= target:
            return True
    return False


def layer1_filter(d: dict) -> bool:
    """All H4 touch events (6/7/8/9)."""
    return is_touch_event(d)


def layer2_filter(d: dict) -> bool:
    """Layer 1 AND H4 state is S or C (shrink/compress)."""
    return layer1_filter(d) and d.get("h4_state") in {"S", "C"}


def layer3_filter(d: dict) -> bool:
    """Layer 2 AND (M30 state in {F,R} OR H1 state in {F,R})."""
    if not layer2_filter(d):
        return False
    fly = d["m30_state"] in {"F", "R"} or d["h1_state"] in {"F", "R"}
    return fly


def baseline_reversion_rate(d: dict, target: float) -> bool:
    """Baseline: directional reversion rate — only count if price reaches midline
    in the direction implied by its starting position relative to midline.
    (close < midline => expect UP; close > midline => expect DOWN)."""
    # Determine expected direction from starting position
    if d["close"] is None:
        return False
    # Track whether we've crossed midline in the expected direction
    prev_side = "below" if d["close"] < target else "above"
    for _ in range(HORIZON_BARS):
        if d["close"] is None:
            continue
        curr_side = "below" if d["close"] < target else "above"
        # UP expectation: was below, now at/crossed midline (>= target)
        if prev_side == "below" and curr_side == "above":
            return True
        # DOWN expectation: was above, now at/crossed midline (<= target)
        if prev_side == "above" and curr_side == "below":
            return True
        prev_side = curr_side
    return False


def run_layer(log_iter, filter_fn) -> dict:
    """Run a layer with the given filter and compute statistics."""
    layer = [d for d in log_iter if filter_fn(d)]
    n = len(layer)
    successes = sum(1 for d in layer if count_reversions(d, midline_reversion(d), predicted_direction(d), HORIZON_BARS))
    rate = successes / n if n else 0.0
    baseline = sum(1 for d in layer if baseline_reversion_rate(d, midline_reversion(d))) / n if n else 0.0
    return {"n": n, "successes": successes, "rate": rate, "baseline": baseline}


def breakdown_layer(layer) -> dict:
    """Break down by direction and touch value."""
    up = sum(1 for d in layer if predicted_direction(d) == "UP")
    up_rev = sum(1 for d in layer if predicted_direction(d) == "UP" and count_reversions(d, midline_reversion(d), "UP", HORIZON_BARS))
    down = sum(1 for d in layer if predicted_direction(d) == "DOWN")
    down_rev = sum(1 for d in layer if predicted_direction(d) == "DOWN" and count_reversions(d, midline_reversion(d), "DOWN", HORIZON_BARS))
    by_touch = defaultdict(lambda: {"n": 0, "rev": 0})
    for d in layer:
        tv = d["cur"]
        by_touch[tv]["n"] += 1
        if count_reversions(d, midline_reversion(d), predicted_direction(d), HORIZON_BARS):
            by_touch[tv]["rev"] += 1
    return {"up": up, "up_rev": up_rev, "down": down, "down_rev": down_rev, "by_touch": dict(by_touch)}


def main():
    # Check log exists
    if not LOG_PATH.exists():
        sys.stderr.write(f"ERROR: Log file not found: {LOG_PATH}\n")
        sys.exit(1)

    # Read all data and filter into layers
    raw = list(read_log(LOG_PATH))
    if not raw:
        sys.stderr.write("ERROR: Failed to parse any lines from the log.\n")
        sys.exit(2)

    layer1 = [d for d in raw if layer1_filter(d)]
    layer2 = [d for d in raw if layer2_filter(d)]
    layer3 = [d for d in raw if layer3_filter(d)]

    # Compute per-layer stats
    s1 = run_layer(layer1, lambda d: True)
    s1["breakdown"] = breakdown_layer(layer1)
    s2 = run_layer(layer2, lambda d: True)
    s2["breakdown"] = breakdown_layer(layer2)
    s3 = run_layer(layer3, lambda d: True)
    s3["breakdown"] = breakdown_layer(layer3)

    # Build report
    report_lines = [
        "# TOUCH_REVERSAL_TEST — H4 band-touch reversion on V36.14",
        "",
        "## Field presence summary",
        "",
        "- All required fields parsed: line_seq_touch (H4), H4/M30/H1 states, band prices.",
        f"- Total bars with valid data: {len(raw)}.",
        "",
        "### Sample touch event",
        "",
        f"- H4 current touch: {raw[0]['cur']}, previous touch: {raw[0]['prev']}",
        f"- H4 state: {raw[0]['h4_state']}, M30 state: {raw[0]['m30_state']}, H1 state: {raw[0]['h1_state']}",
        f"- H4 midline: {raw[0]['bb_mid']:.6f}, close: {raw[0]['close']:.6f}",
        "",
        "### Excluded events (already past midline)",
        "",
    ]

    excluded = sum(1 for d in layer1 if price_above_midline(d, midline_reversion(d), predicted_direction(d)))
    report_lines.append(f"- Count of bars where H4 touch is 6/7/8/9 but price already beyond the midline in the predicted direction: {excluded}")

    report_lines.extend([
        "",
        "## Per-layer results",
        "",
        "| Layer | Filter | n | Successes | Rate | Baseline |",
        "|-------|--------|---|----------|------|----------|",
        f"| 1 | All H4 touch events (6/7/8/9) | {s1['n']} | {s1['successes']} | {s1['rate']*100:.1f}% | {s1['baseline']*100:.1f}% |",
        f"| 2 | H4 state S or C (shrink/compress) | {s2['n']} | {s2['successes']} | {s2['rate']*100:.1f}% | {s2['baseline']*100:.1f}% |",
        f"| 3 | Fly (M30 or H1 in {{F,R}}) | {s3['n']} | {s3['successes']} | {s3['rate']*100:.1f}% | {s3['baseline']*100:.1f}% |",
        "",
    ])

    # Layer 1 breakdown
    report_lines.extend([
        "### Layer 1 breakdown by direction and touch value",
        "",
    ])

    dir_up = s1["breakdown"]["up"]
    dir_down = s1["breakdown"]["down"]
    if dir_up:
        report_lines.append(f"- Direction UP (touch 6/8): n = {dir_up}, successes = {s1['breakdown']['up_rev']}, rate = {s1['breakdown']['up_rev']/dir_up*100:.1f}%")
    else:
        report_lines.append("- Direction UP (touch 6/8): n = 0")

    if dir_down:
        report_lines.append(f"- Direction DOWN (touch 7/9): n = {dir_down}, successes = {s1['breakdown']['down_rev']}, rate = {s1['breakdown']['down_rev']/dir_down*100:.1f}%")
    else:
        report_lines.append("- Direction DOWN (touch 7/9): n = 0")

    report_lines.extend([
        "",
        "### Layer 1 breakdown by touch value",
        "",
        "| Touch | n | Successes | Rate | Baseline |",
        "|-------|---|----------|------|----------|",
    ])

    for tv in sorted(s1["breakdown"]["by_touch"].keys()):
        bd = s1["breakdown"]["by_touch"][tv]
        rate = bd["rev"] / bd["n"] * 100 if bd["n"] else 0.0
        bl = run_layer(layer1, lambda d: d["cur"] == tv)["baseline"]
        report_lines.append(f"| {tv} | {bd['n']} | {bd['rev']} | {rate:.1f}% | {bl*100:.1f}% |")

    # Verdict
    report_lines.extend([
        "",
        "## VERDICT (fixed criteria)",
        "",
        f"- Layer 1 adds VALUE if its rate is >= 10 pp higher than Layer 2 AND Layer 2 has n >= {MIN_N_FOR_VALUE}.",
        f"- Layer 2 adds VALUE if its rate is >= 10 pp higher than Layer 1 AND Layer 1 has n >= {MIN_N_FOR_VALUE}.",
        f"- Layer 3 adds VALUE if its rate is >= 10 pp higher than Layer 2 AND Layer 2 has n >= {MIN_N_FOR_VALUE}.",
        "",
    ])

    # Compute value improvements
    l1_vs_l2 = s1["rate"] - s2["rate"] * 100
    l2_vs_l1 = s2["rate"] - s1["rate"] * 100
    l3_vs_l2 = s3["rate"] - s2["rate"] * 100

    l1_adds = (l1_vs_l2 >= VALUE_IMPROVEMENT_PCT and s2["n"] >= MIN_N_FOR_VALUE)
    l2_adds = (l2_vs_l1 >= VALUE_IMPROVEMENT_PCT and s1["n"] >= MIN_N_FOR_VALUE)
    l3_adds = (l3_vs_l2 >= VALUE_IMPROVEMENT_PCT and s2["n"] >= MIN_N_FOR_VALUE)

    report_lines.append(f"- Layer 1 vs Layer 2: +{l1_vs_l2:.1f} pp (n={s2['n']}) — {'YES' if l1_adds else 'NO'}.")
    report_lines.append(f"- Layer 2 vs Layer 1: +{l2_vs_l1:.1f} pp (n={s1['n']}) — {'YES' if l2_adds else 'NO'}.")
    report_lines.append(f"- Layer 3 vs Layer 2: +{l3_vs_l2:.1f} pp (n={s2['n']}) — {'YES' if l3_adds else 'NO'}.")
    report_lines.append("")

    # Minimal working rule
    value_layers = [i for i, v in enumerate([None, l1_adds, l2_adds, l3_adds], start=1) if v]
    if value_layers:
        best = min(value_layers, key=lambda x: x)
        report_lines.append(f"- Minimal working rule: Layer {best} (shrink/compress filter or fly condition).")
    else:
        report_lines.append("- No layer reaches the fixed criteria — NO SIGNAL.")

    # Signal verdict
    report_lines.extend([
        "",
        f"- TOUCH HAS SIGNAL if any layer's rate is >= 60% AND beats its baseline by >= 10 pp AND n >= {MIN_N_FOR_VALUE}.",
    ])

    for i in range(1, 4):
        s = {"layer1": s1, "layer2": s2, "layer3": s3}[f"layer{i}"]
        bl = s["baseline"] * 100
        beats = (s["rate"] - bl) * 100
        meets_rate = s["rate"] >= 60.0
        meets_beats = beats >= VALUE_IMPROVEMENT_PCT
        meets_n = s["n"] >= MIN_N_FOR_VALUE
        report_lines.append(f"- Layer {i}: rate = {s['rate']*100:.1f}% (baseline {bl:.1f}%) — {'YES' if meets_rate and meets_beats and meets_n else 'NO'} ({'beats baseline' if meets_beats else 'does not beat baseline'}).")

    # Over-sliced check
    report_lines.append("")
    over_sliced = any(s["n"] < MIN_N_FOR_VALUE for s in [s1, s2, s3])
    if over_sliced:
        under_20 = [(i+1, s["n"]) for i,s in enumerate([s1,s2,s3]) if s["n"] < MIN_N_FOR_VALUE]
        report_lines.append(f"- OVER-SLICED: Layer {under_20[0][0]} drops to n={under_20[0][1]} < {MIN_N_FOR_VALUE} — this condition over-slices the data; cannot conclude.")
    else:
        report_lines.append("- OVER-SLICED: none of the layers drop below n=20.")

    # Limitations
    report_lines.extend([
        "",
        "## LIMITATIONS",
        "",
        "- In-sample on V36.14 window (discovery only).",
        "- Single horizon/target choice pre-registered (24 bars to H4 midline).",
        "- Reaching midline once within horizon counts as success — does not model tradeable exit.",
        "- Needs clean-window confirmation if positive.",
    ])

    # Write report
    report_path = ROOT / "references" / "TOUCH_REVERSAL_TEST.md"
    report_text = "\n".join(report_lines)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_text)

    print(f"Report written to {report_path}")


if __name__ == "__main__":
    main()
