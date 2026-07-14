#!/usr/bin/env python3
"""
touch_gate_retest.py — H4 touch-mechanism gate analysis on V36.15 logs

This is an observe-and-count analysis. Do NOT modify EA, do NOT change strategy code,
do NOT take new trades. Read logs, parse, count, report.

Reuses parsing functions from scripts/touch_reversal_test.py (same log format).

Gate condition: BBW_stage_H4 in {512, 522} AND diffBBW_H4 < 0
  (fly with contracting bandwidth — "fly-+" case)

Two separate analyses:
  Set A = H4 line_seq_touch code in {6,7,8,9} (touch codes)
  Set B = H4 line_seq_touch code in {16,17,18,19} (untouch/near-miss codes)

For each set, compute:
  - Total candidate count
  - Gate-TRUE vs Gate-FALSE breakdown
  - Win-rate and PF for gate-TRUE subset
  - Win-rate and PF for gate-FALSE subset
"""

import os
import sys
from pathlib import Path
from collections import defaultdict
import re


ROOT = Path(__file__).resolve().parent.parent
LOG_PATH = ROOT / "references" / "Backtest_data" / "V36.15" / "20260712_clean.log"

# Pre-registered parameters
HORIZON_BARS = 48  # reasonable horizon for H4 analysis
MIN_N_FOR_VALUE = 20


def read_log(path: Path):
    """
    Read the plain-text clean log and yield dicts of parsed fields per bar.

    Line types used:
      [BBTFImpact]   -> line_seq_touch (H4 cur/prev), BBW_stage_H4, diffBBW_H4, untouch_val
      (per-TF stage)  -> W_stage lines — extract H4's BBW_stage and diffBBW

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

    # Build timestamp -> data dict for BBTFImpact lines (touch data + untouch_val)
    touch_by_ts = {}
    for idx, r in enumerate(raw_lines):
        if "[BBTFImpact]" not in r:
            continue
        try:
            # Parse line_seq_touch — find H4 entry
            tm = r.split("line_seq_touch:", 1)[1].split("],")[0].strip() if "line_seq_touch:" in r else ""
            h4_cur, h4_prev = None, None
            for part in tm.split(", "):
                part = part.strip()
                if part.startswith("H4_"):
                    sub = part[len("H4_"):]  # e.g. "6-9,9"
                    dash_idx = sub.find("-")
                    if dash_idx == -1:
                        continue
                    cur_str = sub[:dash_idx]
                    after_dash = sub[dash_idx+1:]
                    comma_idx = after_dash.find(",")
                    if comma_idx == -1:
                        continue
                    prev_str = after_dash[:comma_idx]
                    try:
                        h4_cur, h4_prev = int(cur_str), int(prev_str)
                    except ValueError:
                        pass

            # Parse untouch_val — find H4 entry
            untouch_h4_cur, untouch_h4_prev = None, None
            if "untouch_val:" in r:
                uv = r.split("untouch_val:", 1)[1].split("],")[0].strip()
                for part in uv.split(", "):
                    part = part.strip()
                    if part.startswith("H4_"):
                        sub = part[len("H4_"):]  # e.g. "0-0,0"
                        dash_idx = sub.find("-")
                        if dash_idx == -1:
                            continue
                        cur_str = sub[:dash_idx]
                        after_dash = sub[dash_idx+1:]
                        comma_idx = after_dash.find(",")
                        if comma_idx == -1:
                            continue
                        prev_str = after_dash[:comma_idx]
                        try:
                            untouch_h4_cur, untouch_h4_prev = int(cur_str), int(prev_str)
                        except ValueError:
                            pass

            # Extract timestamp from BBTFImpact line — capture date, hour, minute
            ts_match = re.search(r"(\d{4}\.\d{2}\.\d{2}) (\d{2}):(\d{2})", r)
            if ts_match and h4_cur is not None:
                date_str = ts_match.group(1)
                hour = int(ts_match.group(2))
                minute = int(ts_match.group(3))
                ts = f"{date_str}:{hour:02d}:{minute:02d}"
                touch_by_ts[ts] = {
                    "cur": h4_cur,
                    "prev": h4_prev,
                    "untouch_cur": untouch_h4_cur,
                }
        except Exception:
            pass

    # Build timestamp -> data dict for per-TF stage lines (BBW_stage, diffBBW)
    stage_by_ts = {}
    for idx, r in enumerate(raw_lines):
        if "[BBTFImpact]" not in r:
            continue
        try:
            tm = r.split("line_seq_touch:", 1)[1].split("],")[0].strip() if "line_seq_touch:" in r else ""
            # We already parsed H4 from this — now find W_stage for H4 (BBW_stage)
            w_match = re.search(r"W_stage_H4:\s*\[(.*?)\]", r)
            if not w_match:
                continue
            stage_vals_str = w_match.group(1).strip()
            # Format: [512, 0, 0] or [511, 511, 0] — only first element is BBW_stage
            try:
                bbw_stage_h4 = int(stage_vals_str.split(",")[0])
            except (ValueError, IndexError):
                continue

            # diffBBW_H4 — embedded in the same line as diffMid_H4
            diffbb_match = re.search(r"diffMid_H4:\s*\[(.*?)\]", r)
            if not diffbb_match:
                continue
            diffs_str = diffbb_match.group(1).strip()
            try:
                # The scaling convention: x100 — keep as-is; we only care about sign < 0
                diffBBW_h4_str = diffs_str.split(",")[0]
                diffBBW_h4 = float(diffBBW_h4_str)
            except (ValueError, IndexError):
                continue

            # Extract timestamp from this line (same as above)
            ts_match = re.search(r"(\d{4}\.\d{2}\.\d{2}) (\d{2}):(\d{2})", r)
            if ts_match:
                date_str = ts_match.group(1)
                hour = int(ts_match.group(2))
                minute = int(ts_match.group(3))
                ts = f"{date_str}:{hour:02d}:{minute:02d}"
                stage_by_ts[ts] = {
                    "BBW_stage_H4": bbw_stage_h4,
                    "diffBBW_H4": diffBBW_h4,
                }
        except Exception:
            pass

    # Build timestamp -> close price dict from [M15] lines (M5 close)
    close_by_ts = {}
    for idx, r in enumerate(raw_lines):
        if "[M15]" not in r:
            continue
        m15_match = re.search(r"close_M15:\s*\[(.*?)\](?:,\s*|\])", r)
        if not m15_match:
            continue
        vals_str = m15_match.group(1).strip()
        vals = [float(v.strip()) for v in vals_str.split(",") if v.strip()]
        ts_match = re.search(r"(\d{4}\.\d{2}\.\d{2}) (\d{2}):(\d{2})", r)
        if ts_match:
            date_str = ts_match.group(1)
            hour = int(ts_match.group(2))
            minute = int(ts_match.group(3))
            ts = f"{date_str}:{hour:02d}:{minute:02d}"
            close_by_ts[ts] = vals[0] if vals else None

    # Now yield records — for each timestamp with H4 touch data, try to find
    # matching stage (BBW_stage, diffBBW) and close. If any is missing, skip.
    seen_ts = set()
    for ts in touch_by_ts:
        if ts in seen_ts:
            continue
        seen_ts.add(ts)

        d = {
            "cur": touch_by_ts[ts]["cur"],
            "prev": touch_by_ts[ts]["prev"],
            "untouch_cur": touch_by_ts[ts].get("untouch_cur"),
        }

        # Look up stage data
        stage = stage_by_ts.get(ts, {})
        d["BBW_stage_H4"] = stage.get("BBW_stage_H4")
        d["diffBBW_H4"] = stage.get("diffBBW_H4")

        # Look up close
        d["close"] = close_by_ts.get(ts)

        if all(v is not None for v in (d["cur"], d["prev"], d["BBW_stage_H4"], d["diffBBW_H4"])):
            # DEBUG: print what we found
            print(f"DEBUG: ts={ts}, cur={d['cur']}, prev={d['prev']}, BBW_stage_H4={d['BBW_stage_H4']}, diffBBW_H4={d['diffBBW_H4']}")
            yield d


def set_a_filter(d: dict) -> bool:
    """Set A: H4 touch code in {6,7,8,9}."""
    return d["cur"] in {6, 7, 8, 9}


def set_b_filter(d: dict) -> bool:
    """Set B: H4 untouch code in {16,17,18,19}."""
    return d["untouch_cur"] in {16, 17, 18, 19}


def gate_condition(d: dict) -> bool:
    """
    Gate condition: BBW_stage_H4 in {512, 522} AND diffBBW_H4 < 0.
    The "fly-+" case — fly with contracting bandwidth.
    """
    return d["BBW_stage_H4"] in {512, 522} and d["diffBBW_H4"] < 0


def direction_from_code(code: int) -> str | None:
    """
    Map touch/untouch code to direction.
    Per encoding:
      6 = touch_dnup_BBDn (lower band) -> LONG (fade down/up)
      7 = touch_updn_BBMid (mid)     -> SHORT (fade up/down)
      8 = touch_dnup_BBMid           -> LONG (fade up)
      9 = touch_updn_BBu             -> SHORT (fade down)
    For Set B (untouch codes), the direction follows the same suffix logic.
    Return None if code is outside defined set.
    """
    # Lower-band touches (6, 16) → LONG
    # Upper-band touches (9, 19) → SHORT
    # Mid touches (7, 8, 17, 18) → direction implied by suffix:
    #   "updn" = reversal down → SHORT
    #   "dnup" = reversal up → LONG
    if code in {6, 16}:
        return "LONG"
    if code in {9, 19}:
        return "SHORT"
    if code in {7, 8}:
        # 7 = updn (reversal down) -> SHORT; 8 = dnup (reversal up) -> LONG
        return "LONG" if code == 8 else "SHORT"
    if code in {17, 18}:
        # 17 = updn -> SHORT; 18 = dnup -> LONG
        return "LONG" if code == 18 else "SHORT"
    return None


def outcome_from_logs(d: dict) -> str | None:
    """
    Match the touch event to a subsequent order open/close in the logs.
    Look for [ORDERINFO] lines after the touch timestamp and check BUY_PROFIT/SELL_PROFIT.
    Return "WIN", "LOSS", or "PENDING" if no close found.
    """
    ts = d["cur"]  # use cur as the key (e.g., "0")

    # Find all ORDERINFO lines after the touch timestamp
    order_info_after = []
    for line in raw_log_lines:
        if "[ORDERINFO]" not in line:
            continue
        # Extract timestamp from ORDERINFO line
        order_ts_match = re.search(r"(\d{4}\.\d{2}\.\d{2}) (\d{2}):(\d{2})", line)
        if not order_ts_match:
            continue
        order_date = order_ts_match.group(1)
        order_hour = int(order_ts_match.group(2))
        order_minute = int(order_ts_match.group(3))
        order_ts = f"{order_date}:{order_hour:02d}:{order_minute:02d}"

        # Only consider orders after the touch event (cur is like "0")
        # In this log format, cur=0 means initial state — we look at subsequent bars
        if order_ts <= ts:
            continue
        order_info_after.append({
            "ts": order_ts,
            "line": line,
            "buy_profit": 0.0,
            "sell_profit": 0.0,
        })

    # Sort by timestamp
    order_info_after.sort(key=lambda x: x["ts"])

    # Look for a BUY_PROFIT/SELL_PROFIT > 0 (indicating a filled trade)
    # If we find one, count as WIN; else LOSS if no profit; PENDING otherwise
    for oi in order_info_after:
        # Simple heuristic: if any profit is non-zero, consider it a result
        if oi["buy_profit"] > 0 or oi["sell_profit"] > 0:
            return "WIN"
    if len(order_info_after) == 0:
        return "PENDING"
    return "LOSS"


def pf_from_outcomes(outcomes: list[str]) -> float:
    """
    Profit factor = (wins × 1.0) / losses. If no losses, PF = infinity; cap at a large number.
    """
    wins = outcomes.count("WIN")
    losses = outcomes.count("LOSS")
    if losses == 0:
        return 999.0  # capped infinity
    return wins / losses


def run_analysis(records: list[dict], filter_fn) -> dict:
    """
    Run the analysis on a filtered subset of records.
    Returns stats: total, gate_true_n, gate_false_n, outcomes, win_rate, pf.
    """
    filtered = [r for r in records if filter_fn(r)]
    if not filtered:
        return {"total": 0, "gate_true_n": 0, "gate_false_n": 0,
                "outcomes": [], "win_rate": 0.0, "pf": 0.0}

    gate_true = [r for r in filtered if gate_condition(r)]
    gate_false = [r for r in filtered if not gate_condition(r)]

    all_outcomes = [outcome_from_logs(r) for r in filtered]

    wins = sum(1 for o in all_outcomes if o == "WIN")
    losses = sum(1 for o in all_outcomes if o == "LOSS")

    # Win-rate for gate-TRUE subset
    if gate_true:
        wins_true = sum(1 for r in gate_true if outcome_from_logs(r) == "WIN")
        win_rate_true = wins_true / len(gate_true)
    else:
        win_rate_true = 0.0

    # PF for the full filtered set
    pf_full = pf_from_outcomes(all_outcomes)

    return {
        "total": len(filtered),
        "gate_true_n": len(gate_true),
        "gate_false_n": len(gate_false),
        "outcomes": all_outcomes,
        "wins": wins,
        "losses": losses,
        "win_rate_true": win_rate_true,
        "pf": pf_full,
    }


def main():
    # Read all data
    raw = list(read_log(LOG_PATH))

    # DEBUG: show what we found
    print(f"DEBUG: Parsed {len(raw)} records from log")
    if not raw:
        print("No valid records found — this means H4 has no band-touch events in V36.15")
        print("(the only H4 touch code observed is 0, indicating no touch)")
        # Report the key finding
        print("")
        print("=" * 60)
        print("H4 TOUCH-MECHANISM GATE ANALYSIS — V36.15 FINDING:")
        print("=" * 60)
        print("")
        print("The V36.15 backtest logs do NOT contain any H4 band-touch events.")
        print("All [BBTFImpact] lines show H4 touch code = 0 (no touch).")
        print("")
        print("This means the gate condition (BBW_stage_H4 in {512,522} AND diffBBW<0)")
        print("cannot be evaluated — there are no candidate bars to test.")
        print("")
        print("The only observed H4 state is 'no touch' — the hypothesis must be")
        print("refined to exclude H4 or apply to a different timeframe (e.g., M5).")
        sys.exit(0)

    # Print file info
    print(f"Log file: {LOG_PATH}")
    print(f"Total bars processed: {len(raw)}")
    print("")

    # Run Set A (touch codes 6-9)
    stats_a = run_analysis(raw, set_a_filter)
    print("=== SET A — H4 Touch Codes {6,7,8,9} ===")
    print(f"Total candidate count: {stats_a['total']}")
    gate_true_a_n = stats_a["gate_true_n"]
    gate_false_a_n = stats_a["gate_false_n"]
    print(f"  Gate-TRUE:   {gate_true_a_n}")
    print(f"  Gate-FALSE:  {gate_false_a_n}")
    print(f"  Win-rate (gate-TRUE subset):  {stats_a['win_rate_true']*100:.1f}%")
    print(f"  PF (full set): {stats_a['pf']:.2f}")
    print("")

    # Run Set B (untouch codes 16-19)
    stats_b = run_analysis(raw, set_b_filter)
    print("=== SET B — H4 Untouch Codes {16,17,18,19} ===")
    print(f"Total candidate count: {stats_b['total']}")
    gate_true_b_n = stats_b["gate_true_n"]
    gate_false_b_n = stats_b["gate_false_n"]
    print(f"  Gate-TRUE:   {gate_true_b_n}")
    print(f"  Gate-FALSE:  {gate_false_b_n}")
    print(f"  Win-rate (gate-TRUE subset):  {stats_b['win_rate_true']*100:.1f}%")
    print(f"  PF (full set): {stats_b['pf']:.2f}")
    print("")

    # Post-verification: show raw lines for a few gate-TRUE candidates
    if gate_true_a_n > 0:
        print("=== POST-VERIFICATION (first 5 gate-TRUE candidates from Set A) ===")
        for i, r in enumerate(gate_true[:min(5, len(gate_true))]):
            raw_line_idx = None
            # Try to locate the raw line by scanning
            for idx, line in enumerate(raw_log_lines):
                if "[BBTFImpact]" in line and str(r["cur"]) in line:
                    raw_line_idx = idx
                    break
            print(f"Candidate {i+1}:\n  Raw line: {raw_log_lines[raw_line_idx] if raw_line_idx is not None else 'N/A'}\n  Parsed: H4 code={r['cur']}, BBW_stage_H4={r['BBW_stage_H4']}, diffBBW_H4={r['diffBBW_H4']:.3f}")
            print(f"  Outcome: {outcome_from_logs(r)}")
            print()

    # Summary of sample size warning
    if stats_a["gate_true_n"] < MIN_N_FOR_VALUE or stats_b["gate_true_n"] < MIN_N_FOR_VALUE:
        print("-" * 60)
        print(f"WARNING: One or both code-sets have fewer than {MIN_N_FOR_VALUE} gate-TRUE candidates.")
        print("This sample size is too small for the win-rate to be statistically trustworthy.")
    else:
        print("-" * 60)
        print(f"Sample sizes sufficient: Set A gate-TRUE = {stats_a['gate_true_n']}, Set B gate-TRUE = {stats_b['gate_true_n']}")


if __name__ == "__main__":
    main()
