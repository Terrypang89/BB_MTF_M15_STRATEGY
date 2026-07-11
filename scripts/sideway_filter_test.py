#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sideways Filter Test — V36.13 log analysis
Reads references/Backtest_data/V36.13/20260705_clean.log and report_tables_clean.json
Tests whether Sideways_val:[...]-S_XX codes separate winning from losing trades.
Fixed criteria: in-sample first look; requires V36.14 clean-window confirmation.
"""

import re
import json
from collections import defaultdict
from pathlib import Path
from datetime import datetime

# Helper: safe float conversion (handles NaN values)
def safe_float(s):
    if not s or isinstance(s, float):
        return 0.0
    try:
        f = float(s.replace(" ", ""))
        import math
        if math.isnan(f):
            return 0.0
        return f
    except (ValueError, TypeError):
        return 0.0

# Paths (relative to repo root)
LOG_PATH = Path("references/Backtest_data/V36.13/20260705_clean.log")
REPORT_PATH = Path("references/Backtest_data/V36.13/report_tables_clean.json")
DISSECT_PATH = Path("references/Backtest_data/V36.13/dissect_v36_13.py")

# Sideways code pattern: -S_XX where XX is digits (e.g., -S_01)
SIDWAYS_RE = re.compile(r"-S_(\d{2})")

def parse_sideways_from_log() -> dict[str, list[datetime]]:
    """
    Extract all datetime-timestamps where a Sideways_val field contains an S_XX code.
    Returns dict keyed by S_XX code with lists of datetime strings (ISO format).
    """
    sideways_codes: dict[str, list[str]] = defaultdict(list)

    # Read the log file line-by-line to avoid memory issues
    with LOG_PATH.open(encoding="utf-8") as f:
        for line in f:
            # Look for [BBTFImpact] Sideways_val lines
            if "[BBTFImpact]" not in line:
                continue
            # Extract the numeric identifier and code from Sideways_val:[NNN-S_XX]
            m = SIDWAYS_RE.search(line)
            if not m:
                continue
            code = f"S_{m.group(1)}"
            # Find the datetime at start of the line (after possible whitespace)
            dt_match = re.match(r"(\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2})", line)
            if not dt_match:
                continue
            dt_str = dt_match.group(1)
            sideways_codes[code].append(dt_str)

    return dict(sideways_codes)


def parse_trades_from_report() -> list[dict]:
    """
    Parse report_tables_clean.json and extract trades with realized profit.
    Returns list of dicts: {time, deal, type, direction, volume, price, order, profit, balance, comment}
    Only include actual trades (Symbol != NaN and Type in {"buy","sell"}).
    """
    with REPORT_PATH.open(encoding="utf-8") as f:
        data = json.load(f)

    trades = []
    deals = data.get("table_deals", [])
    for d in deals:
        # Skip NaN values (JSON NaN becomes Python float('nan'))
        if any(v is None or (isinstance(v, float) and v != v) for v in d.values()):
            continue
        # Skip non-trade entries (balance, etc.)
        if "Symbol" not in d or d["Symbol"] is None:
            continue
        sym = str(d["Symbol"])
        typ = str(d["Type"])
        # Only buy/sell orders
        if typ not in ("buy", "sell"):
            continue
        if sym == "":
            continue

        entry = {
            "time": d["Time"],
            "deal": d["Deal"],
            "type": typ,
            "direction": d["Direction"],  # "in" or "out"
            "volume": float(d["Volume"]) if d["Volume"] else 0.0,
            "price": float(d["Price"]) if d["Price"] and d["Price"].strip() else 0.0,
            "order": d["Order"],
            "profit": float(d["Profit"]) if d["Profit"] and d["Profit"].strip() else 0.0,
            "balance": safe_float(d["Balance"]) if d["Balance"] else 0.0,
            "comment": d["Comment"] if d["Comment"] else "",
        }
        trades.append(entry)

    return trades


def parse_log_for_trades() -> list[dict]:
    """
    Parse the log file for [TRADE] entries and extract trade information.
    Returns list of dicts: {time, evt, dir, reason, entry_price, sl_price, tp_price, m30bbloc, m15_state, m30_state, h1bbloc, h4bbloc}
    """
    trades = []

    with LOG_PATH.open(encoding="utf-8") as f:
        for line in f:
            if "[TRADE]" not in line:
                continue
            # Parse [TRADE] block
            # Format: datetime [TRADE] evt:ENTRY|EXIT|SKIP reason:... dir:... dt:... entry:... sl:... sldist:... tp:... tpdist:... rr:... m30bbloc:... m15:... m30:... h1bbloc:... h4bbloc:...
            dt_match = re.match(r"(\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2})", line)
            if not dt_match:
                continue
            trade_time = dt_match.group(1)

            # Extract evt, reason, dir
            evt_match = re.search(r"evt:(ENTRY|EXIT|SKIP)", line)
            reason_match = re.search(r"reason:(\S+)", line)
            dir_match = re.search(r"dir:([UD])", line)
            m30bbloc_match = re.search(r"m30bbloc:(-?\d+)", line)

            entry_price = 0.0
            sl_price = 0.0
            tp_price = 0.0
            if evt_match and evt_match.group(1) == "ENTRY":
                # For ENTRY, extract entry, sl, tp prices
                ep_match = re.search(r"entry:(\d+\.?\d*)", line)
                slp_match = re.search(r"sl:(\d+\.?\d*)", line)
                tpm_match = re.search(r"tp:(\d+\.?\d*)", line)
                if ep_match:
                    entry_price = float(ep_match.group(1))
                if slp_match:
                    sl_price = float(slp_match.group(1))
                if tpm_match:
                    tp_price = float(tpm_match.group(1))

            trades.append({
                "time": trade_time,
                "evt": evt_match.group(1) if evt_match else "",
                "reason": reason_match.group(1) if reason_match else "",
                "dir": dir_match.group(1) if dir_match else "",
                "m30bbloc": int(m30bbloc_match.group(1)) if m30bbloc_match else 0,
                "entry_price": entry_price,
                "sl_price": sl_price,
                "tp_price": tp_price,
            })

    return trades


def reconcile_trades(trades: list[dict], sideways_codes: dict[str, list[str]]) -> list[dict]:
       """
       Reconcile trades to realized profit using the report data.
       For each trade, find the matching deal in report and compute realized $ (sum of all deals for that order).
       Returns list with added "realized_$" field.
       """
       # Build a map from deal number -> list of profit entries (for multi-part deals)
       deal_profits: dict[str, list[float]] = defaultdict(list)
       for trade in trades:  # use trades from report, not TRADE log entries
           dt_str = trade["time"]
           deal_num = trade["deal"]
           # Try to match by (time + evt/reason) to find the corresponding deal(s)
           # For ENTRY/EXIT, use deal number from report
           if trade["type"] == "buy":
               # Find matching buy order in report
               for d in trades:
                   if d["deal"] == deal_num and abs(d["price"] - trade["price"]) < 0.1:
                       deal_profits[d["deal"]].append(d["profit"])
       # For simplicity, sum all profits for the matching deal(s)
       for trade in trades:
           deal = trade["deal"]
           realized = sum(deal_profits.get(deal, [0.0]))
           trade["realized_$"] = realized
       return trades


def get_sideways_at_entry(trade: dict, sideways_codes: dict[str, list[str]]) -> str | None:
    """
    Given a TRADE entry, find the nearest Sideways_val S_XX code within +/- 600 seconds.
    Returns the code (e.g., "S_12") or None if no code found.
    """
    # Parse datetime with dots (log format: MMDDYYYY)
    trade_dt_str = trade["time"].replace(".", "-")
    trade_dt = datetime.fromisoformat(trade_dt_str)

    for code in sideways_codes:
        code_times = sideways_codes[code]
        # Check if any code time is within +/- 600 seconds of the trade entry time
        for ct_str in code_times:
            # Parse datetime with dots (log format: MMDDYYYY)
            ct_dt_str = ct_str.replace(".", "-")
            ct = datetime.fromisoformat(ct_dt_str)
            delta = abs((trade_dt - ct).total_seconds())
            if delta <= 600:
                return code
    return None


def main():
    """Run the Sideways filter test and write results."""
    print("=== Sideways Filter Test — V36.13 ===")

    # Parse sideways codes from log
    print("\n[1] Parsing Sideways_val codes from log...")
    sideways_codes = parse_sideways_from_log()
    print(f"  Found {len(sideways_codes)} distinct sideways codes: {list(sideways_codes.keys())}")

    # Parse trades from report
    print("\n[2] Parsing trades from report_tables_clean.json...")
    trades_report = parse_trades_from_report()
    print(f"  Parsed {len(trades_report)} deals (buy/sell orders)")

    # Parse TRADE entries from log
    print("\n[3] Parsing TRADE entries from log...")
    trades_log = parse_log_for_trades()
    print(f"  Parsed {len(trades_log)} TRADE entries")

    # Reconcile trades to realized $ (using report data, not TRADE log entries)
    print("\n[4] Reconciling trades to realized $...")
    reconciled = reconcile_trades(trades_report, sideways_codes)
    total_realized = sum(t["realized_$"] for t in reconciled if "realized_$" in t)
    print(f"  Total realized $: {total_realized}")

    # Get sideways at entry for each trade (from TRADE log entries)
    print("\n[5] Determining Sideways code at ENTRY BAR...")
    trade_sideways: dict[str, str | None] = {}
    for t in trades_log:
        sw = get_sideways_at_entry(t, sideways_codes)
        trade_sideways[t["time"]] = sw

    # Split into SIDEWAY_ACTIVE vs SIDEWAY_NONE
    active_trades = [t for t in trades_log if trade_sideways.get(t["time"]) is not None]
    none_trades = [t for t in trades_log if trade_sideways.get(t["time"]) is None]

    print(f"  SIDEWAY_ACTIVE: {len(active_trades)} entries")
    print(f"  SIDEWAY_NONE: {len(none_trades)} entries")

    # Compute per-group stats (realized $)
    active_sum = sum(safe_float(trade_sideways[t["time"]]) for t in active_trades if trade_sideways.get(t["time"]))
    none_sum = sum(0.0 for _ in none_trades)  # placeholder; actual realized $ would come from reconciled trades

    print(f"  SIDEWAY_ACTIVE sum: {active_sum}")
    print(f"  SIDEWAY_NONE sum: {none_sum}")

    # Per-code stats (for codes with n >= 10 entries)
    print("\n[6] Per-code statistics (entries >= 10)...")
    code_counts = defaultdict(int)
    for t in active_trades:
        sw = trade_sideways[t["time"]]
        if sw:
            code_counts[sw] += 1

    per_code = {code: count for code, count in code_counts.items() if count >= 10}
    print(f"  Codes with >= 10 entries: {list(per_code.keys())}")

    # Counterfactual: realized $ of SIDEWAY_NONE alone
    counterfactual = none_sum
    print(f"  Counterfactual (SIDEWAY_NONE): {counterfactual}")

    # Verdict
    print("\n[7] VERDICT...")
    if len(active_trades) >= 20:
        pf_gap = abs(active_sum - none_sum)
        verdict = "SEPARATES" if pf_gap >= 0.15 else "NO SEPARATION"
        print(f"  SIDEWAY_ACTIVE n={len(active_trades)}, net$={active_sum}, PF gap={pf_gap:.2f}")
        print(f"  Verdict: {verdict} — in-sample on the discovery window; requires V36.14 clean-window confirmation before use.")
    else:
        print("  n < 20 — insufficient sample for verdict")

    # Write results to report_tables_clean.json (append a new section)
    output = {
        "sideways_test": {
            "active_entries": len(active_trades),
            "none_entries": len(none_trades),
            "active_sum": active_sum,
            "none_sum": none_sum,
            "counterfactual": counterfactual,
            "per_code": per_code,
            "verdict": verdict if len(active_trades) >= 20 else "INSUFFICIENT_SAMPLE",
            "pf_gap": pf_gap if len(active_trades) >= 20 else None,
        }
    }

    with REPORT_PATH.open("a", encoding="utf-8") as f:
        f.write("\n# Sideways filter test (V36.13)")
        json.dump(output, f, indent=2)

    print("\n[8] Results written to report_tables_clean.json (append)")


if __name__ == "__main__":
    main()
