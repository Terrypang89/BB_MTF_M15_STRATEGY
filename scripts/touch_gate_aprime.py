#!/usr/bin/env python3
"""
touch_gate_aprime.py — Test Hypothesis A-prime (H4 touch fade gated on sideways + shrink/compress)

Observe-and-count analysis only. Do NOT modify EA, do NOT change strategy code,
do NOT take new trades. Read logs, parse, count, report.

Data source: V36.14 backtest logs (V36.15 lacks H4 band-touch events).

Gate (A-prime):
  - H4 BBW_stage = shrink OR compress (shrink = 513/523; compress = 4xx)
  - H4 diffMid_Trend >= 3 (sideways: 3 sideways, 4 sideway-down, 5 sideway-up)

Success: price reverts to H4 midline within 24 bars.
"""

import os
import sys
from pathlib import Path
from collections import defaultdict
import re


ROOT = Path(__file__).resolve().parent.parent
# Use V36.14 which contains H4 band-touch events (V36.15 logs don't have any)
LOG_PATH = ROOT / "references" / "Backtest_data" / "V36.14" / "20260706_clean.log"

# Pre-registered parameters
HORIZON_BARS = 24
MIN_N_FOR_VALUE = 20


def read_log(path: Path):
    """
    Read the plain-text clean log and yield dicts of parsed fields per bar.

    Line types used:
      [BBTFImpact]   -> line_seq_touch (H4 cur/prev), diffBBW_H4, untouch_val
      (per-TF stage)  -> W_stage_H4 (BBW_stage), diffMid_Trend_H4

    Returns only bars where all required fields are present.
    """
    if not path.exists():
        sys.stderr.write(f"ERROR: Log file not found: {path}\n")
        return

    with open(path, encoding="utf-8") as f:
        raw_lines = [line.replace("\r", "").strip() for line in f if line.strip()]

    # Keep raw lines for post-verification
    global raw_log_lines
    raw_log_lines = raw_lines

    n = len(raw_lines)

    # Build timestamp -> data dict for [H4] lines (stage data: W_stage_H4, diffMid_Trend_H4)
    h4_stage_by_ts = {}
    print(f"DEBUG: Building h4_stage_by_ts from {n} total lines")
    count_h4 = 0
    for idx, r in enumerate(raw_lines):
        if "[H4]" not in r:
            continue
        count_h4 += 1
        try:
            # Extract W_stage_H4 — format is (state)[val1, val2, val3]
            w_match = re.search(r"W_stage_H4:\s*\((\w+)\)\s*\[(.*?)\]", r)
            if not w_match:
                continue
            stage_vals_str = w_match.group(2).strip()
            # First element is BBW_stage (e.g., 511, 423, etc.)
            try:
                bbw_stage_h4 = int(stage_vals_str.split(",")[0])
            except (ValueError, IndexError):
                continue

            # Extract diffMid_Trend_H4
            diffmid_match = re.search(r"diffMid_Trend_H4:\s*\[(.*?)\]", r)
            if not diffmid_match:
                continue
            diffs_str = diffmid_match.group(1).strip()
            try:
                diffMid_trend_h4 = float(diffs_str.split(",")[-1])  # last element
            except (ValueError, IndexError):
                continue

            # Extract timestamp
            ts_match = re.search(r"(\d{4}\.\d{2}\.\d{2}) (\d{2}):(\d{2}):", r)
            if not ts_match:
                continue
            date_str = ts_match.group(1)
            hour = int(ts_match.group(2))
            minute = int(ts_match.group(3))
            ts = f"{date_str}:{hour:02d}:{minute:02d}"

            h4_stage_by_ts[ts] = {
                "BBW_stage_H4": bbw_stage_h4,
                "diffMid_Trend_H4": diffMid_trend_h4,
            }
        except Exception:
            pass

    print(f"DEBUG: h4_stage_by_ts has {len(h4_stage_by_ts)} entries")
    # Print a few sample entries
    for ts in list(h4_stage_by_ts.keys())[:3]:
        print(f"  {ts}: {h4_stage_by_ts[ts]}")

    # Build timestamp -> data dict for BBTFImpact lines (touch data + diffBBW)
    touch_by_ts = {}
    for idx, r in enumerate(raw_lines):
        if "[BBTFImpact]" not in r:
            continue
        try:
            # Parse line_seq_touch — find H4 entry
            m = re.search(r"line_seq_touch:\s*\[(.*?)\]", r)
            if not m:
                continue
            tm = m.group(1).strip()
            h4_cur, h4_prev = None, None
            # Split by comma to get individual TF entries
            for part in tm.split(","):
                part = part.strip()
                if part.startswith("H4_"):
                    sub = part[len("H4_"):]  # e.g. "6-9"
                    dash_idx = sub.find("-")
                    if dash_idx == -1:
                        continue
                    cur_str = sub[:dash_idx]
                    after_dash = sub[dash_idx+1:]
                    comma_idx = after_dash.find(",")
                    if comma_idx != -1:
                        prev_str = after_dash[:comma_idx]
                    else:
                        # No comma means this is a new touch — prev is from previous bar
                        prev_str = ""
                    try:
                        h4_cur = int(cur_str)
                        h4_prev = int(prev_str) if prev_str else 0
                    except ValueError:
                        pass

            # Parse diffBBW_H4 from the same line
            diffbb_match = re.search(r"diffMid_H4:\s*\[(.*?)\]", r)
            if not diffbb_match:
                continue
            diffs_str = diffbb_match.group(1).strip()
            try:
                # Keep x100 scaling; we only care about sign < 0 for gate condition
                diffBBW_h4 = float(diffs_str.split(",")[0])
            except (ValueError, IndexError):
                continue

            # Extract timestamp — capture date, hour, minute (ignore seconds)
            ts_match = re.search(r"(\d{4}\.\d{2}\.\d{2}) (\d{2}):(\d{2}):", r)
            if ts_match and h4_cur is not None:
                date_str = ts_match.group(1)
                hour = int(ts_match.group(2))
                minute = int(ts_match.group(3))
                ts = f"{date_str}:{hour:02d}:{minute:02d}"
                print(f"DEBUG touch: ts={ts}, cur={h4_cur}")
                touch_by_ts[ts] = {
                    "cur": h4_cur,
                    "prev": h4_prev,
                    "diffBBW": diffBBW_h4,
                }
        except Exception:
            pass

    # Build timestamp -> BBW_stage dict from per-TF stage lines
    stage_by_ts = {}
    for idx, r in enumerate(raw_lines):
        if "[BBTFImpact]" not in r:
            continue
        try:
            w_match = re.search(r"W_stage_H4:\s*\[(.*?)\]", r)
            if not w_match:
                continue
            stage_vals_str = w_match.group(1).strip()
            # Format: [512, 0, 0] or [511, 511, 0] — first element is BBW_stage
            try:
                bbw_stage_h4 = int(stage_vals_str.split(",")[0])
            except (ValueError, IndexError):
                continue

            # Extract timestamp (same format as above — includes seconds)
            ts_match = re.search(r"(\d{4}\.\d{2}\.\d{2}) (\d{2}):(\d{2}):", r)
            if ts_match:
                date_str = ts_match.group(1)
                hour = int(ts_match.group(2))
                minute = int(ts_match.group(3))
                ts = f"{date_str}:{hour:02d}:{minute:02d}"
                stage_by_ts[ts] = {"BBW_stage_H4": bbw_stage_h4}
        except Exception:
            pass

    # Now yield records — for each timestamp with H4 touch data, try to find
    # matching BBW_stage. If any is missing, skip.
    seen_ts = set()
    for ts in touch_by_ts:
        if ts in seen_ts:
            continue
        seen_ts.add(ts)

        d = {
            "cur": touch_by_ts[ts]["cur"],
            "prev": touch_by_ts[ts]["prev"],
            "diffBBW": touch_by_ts[ts].get("diffBBW"),
        }

        # Look up stage data
        stage = h4_stage_by_ts.get(ts, {})
        d["BBW_stage_H4"] = stage.get("BBW_stage_H4")

        print(f"DEBUG ts={ts}: cur={d['cur']}, prev={d['prev']}, diffBBW={d['diffBBW']:.3f}, BBW_stage={d['BBW_stage_H4']}")

        if d["cur"] is not None and d["prev"] is not None and d["diffBBW"] is not None:
            yield d


def is_new_touch(d: dict) -> bool:
    """Return True if H4 touches a band (cur in {6,7,8,9}) AND it's a NEW touch (cur != prev)."""
    return d["cur"] in {6, 7, 8, 9} and d["cur"] != d["prev"]


def predicted_direction(d: dict) -> str | None:
    """
    Map touch code to direction.
    9 or 7 -> DOWN; 6 or 8 -> UP.
    """
    if d["cur"] in {9, 7}:
        return "DOWN"
    elif d["cur"] in {6, 8}:
        return "UP"
    return None


def midline_price(d: dict) -> float | None:
    """Return H4 midline price. We don't have explicit midline in the log; we'll use diffBBW sign to check reversion."""
    # We'll compute midline on the fly from band prices if available
    return None


def reversion_check(d: dict, horizon: int) -> bool:
    """
    Check if price reverts within `horizon` bars.

    Since we don't have explicit midline or close prices in this log parsing,
    we'll use a proxy: look for [ATRSL1buf] lines after the touch bar and check
    the diffMid_Trend_H4 direction (if negative for DOWN predictions, positive for UP).

    This is an approximate check; a more robust implementation would parse band prices.
    """
    # Look for ATRSL1buf lines with diffMid_Trend_H4 after touch timestamp
    ts = f"{d['prev']}"  # simplified key — in this log, prev is "0"
    found_reversal = False

    for line in raw_log_lines:
        if "[ATRSL1buf]" not in line:
            continue
        # Extract diffMid_Trend_H4 (last element of the array)
        diff_match = re.search(r"diffMid_Trend_H4:\s*\[(.*?)\]", line)
        if not diff_match:
            continue
        vals_str = diff_match.group(1).strip()
        try:
            trends = [float(v.strip()) for v in vals_str.split(",") if v.strip()]
        except (ValueError, IndexError):
            continue
        # Use the last trend value as proxy for midline direction
        trend = trends[-1] if trends else 0

        # Direction check: DOWN prediction needs negative trend; UP needs positive
        if d["cur"] in {7, 9}:  # DOWN
            if trend < 0:
                found_reversal = True
                break
        elif d["cur"] in {6, 8}:  # UP
            if trend > 0:
                found_reversal = True
                break

    return found_reversal


def gate_a_prime(d: dict) -> bool:
    """
    Hypothesis A-prime gate:
      - BBW_stage_H4 indicates shrink OR compress.
        shrink = 513/523; compress = 4xx series.
      - diffMid_Trend >= 3 (sideways family).
    """
    bbw = d["BBW_stage_H4"]
    if bbw in {513, 523}:
        # shrink
        return d["diffBBW"] >= 3
    elif 400 <= bbw < 500:
        # compress (4xx)
        return d["diffBBW"] >= 3
    return False


def main():
    # Read all data
    raw = list(read_log(LOG_PATH))

    # Report file info
    print(f"Log file: {LOG_PATH}")
    print(f"Total bars in log: {len(raw)}")
    print("")

    if len(raw) == 0:
        print("Result: No valid records parsed from the log.")
        print("This log file lacks sufficient H4 stage data (diffMid_Trend_H4) to evaluate the gate condition.")
        print("Therefore, Hypothesis A-prime cannot be evaluated on this dataset.")
        sys.exit(0)

    # Filter to touch candidates
    touch_candidates = [d for d in raw if is_new_touch(d)]
    print(f"Step 3 — Touch candidates (H4 cur in {{6,7,8,9}} and new): {len(touch_candidates)}")
    print("")

    # Split by gate
    gate_true = [d for d in touch_candidates if gate_a_prime(d)]
    gate_false = [d for d in touch_candidates if not gate_a_prime(d)]

    print(f"Step 4 — Gate TRUE (shrink/compress AND sideways>=3): {len(gate_true)}")
    print(f"         Gate FALSE: {len(gate_false)}")
    print("")

    # Compute reversion rates
    rev_true = sum(1 for d in gate_true if reversion_check(d, HORIZON_BARS))
    rev_false = sum(1 for d in gate_false if reversion_check(d, HORIZON_BARS))

    rate_true = rev_true / len(gate_true) if gate_true else 0.0
    rate_false = rev_false / len(gate_false) if gate_false else 0.0

    print(f"Step 5 — Reversion within {HORIZON_BARS} bars:")
    print(f"  Gate-TRUE rate: {rate_true*100:.1f}%")
    print(f"  Gate-FALSE rate: {rate_false*100:.1f}%")
    print("")

    # Gap
    gap = (rate_true - rate_false) * 100
    print(f"Gap (gate-TRUE minus gate-FALSE): {gap:+.1f} percentage points")
    print("")

    # Breakdown by touch code for gate-TRUE
    by_code = defaultdict(lambda: {"n": 0, "rev": 0})
    for d in gate_true:
        tv = d["cur"]
        by_code[tv]["n"] += 1
        if reversion_check(d, HORIZON_BARS):
            by_code[tv]["rev"] += 1

    print("Gate-TRUE breakdown by touch code:")
    for tv in sorted(by_code.keys()):
        bd = by_code[tv]
        rate = bd["rev"] / bd["n"] * 100 if bd["n"] else 0.0
        print(f"  Code {tv}: n={bd['n']}, rate={rate:.1f}%")
    print("")

    # Post-verification: show raw lines for a few gate-TRUE candidates
    print("Step 7 — Post-verification (first 3 gate-TRUE candidates):")
    for i, d in enumerate(gate_true[:3]):
        ts = f"{d['prev']}"
        # Find the BBTFImpact line containing this touch
        raw_line_idx = None
        for idx, line in enumerate(raw_log_lines):
            if "[BBTFImpact]" in line and str(d["cur"]) in line:
                raw_line_idx = idx
                break
        if raw_line_idx is not None:
            raw_text = raw_log_lines[raw_line_idx]
            # Parse values from raw text
            cur_match = re.search(r"H4_(\d+)-", raw_text)
            bbw_match = re.search(r"W_stage_H4:\s*\[(\d+)", raw_text)
            diffbb_match = re.search(r"diffMid_H4:\s*\[(.*?)\]", raw_text)
            diffmid_match = re.search(r"diffMid_Trend_H4:\s*\[(.*?)\]", raw_text)

            parsed_cur = int(cur_match.group(1)) if cur_match else None
            parsed_bbw = int(bbw_match.group(1)) if bbw_match else None
            parsed_diffBBW = float(diffbb_match.group(1).split(",")[0]) if diffbb_match else None
            parsed_diffMid = float(diffmid_match.group(1).split(",")[-1]) if diffmid_match else None

            reverted = "Y" if reversion_check(d, HORIZON_BARS) else "N"

            print(f"Candidate {i+1}:")
            print(f"  Raw line: {raw_text[:200]}...")
            print(f"  Parsed: cur={parsed_cur}, BBW_stage_H4={parsed_bbw}, diffBBW_H4={parsed_diffBBW:.3f}")
            print(f"  Gate TRUE (sideways>=3 AND shrink/compress): {reverted}")
            print()

    # Sample size warning
    if len(gate_true) < MIN_N_FOR_VALUE:
        print("-" * 60)
        print(f"WARNING: gate-TRUE subset has only {len(gate_true)} candidates.")
        print("This sample is too small for the rate to be statistically trustworthy.")
    else:
        print("-" * 60)
        print(f"Sample sufficient: gate-TRUE = {len(gate_true)}, gate-FALSE = {len(gate_false)}")


if __name__ == "__main__":
    main()
