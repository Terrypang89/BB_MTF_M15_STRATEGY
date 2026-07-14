#!/usr/bin/env python3
"""
TRADE P&L ENGINE — reusable with pluggable designs.

Two designs:
  • ea_labels   — uses EA-logged m15/m30 state and dir (reproduces current report)
  • fast_subscenario — computes STATE and DIRECTION from RAW log fields at the entry bar.

Usage:
  python scripts/trade_pnl.py --design ea_labels           → TRADE_PNL_BY_SCENARIO.md
  python scripts/trade_pnl.py --design fast_subscenario   → TRADE_PNL_FAST_SUBSCENARIO.md
"""

import argparse
import math
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path


# =============================================================================
# ENGINE — shared parsing and stats (no design-specific logic)
# =============================================================================

LOG_FILE = Path("references/Backtest_data/V36.15/20260712_clean.log")

if not LOG_FILE.exists():
    print(f"ERROR: Log file not found: {LOG_FILE}")
    raise SystemExit(1)


def parse_timestamp(ts_str):
    """Normalize timestamp string to a comparable form (YYYYMMDDHHMMSS)."""
    return re.sub(r"[ :]", "", ts_str)


# [TRADE] ENTRY line pattern — captures dir, dt, entry_px, sl, tp, rr, m15/m30 states
ENTRY_RE = re.compile(
    r"\[TRADE\]\s+evt:ENTRY\s+"
    r"(dir:UP|dir:DOWN|dir:DN)\s+"
    r"dt:\d{4}\.\d{2}\.\d{2}[\d :.]+\s*"
    r"entry:(\d+(?:\.\d+)?)\s+"
    r"sl:([\d.]+)\s+"
    r"sldist:\d+(?:\.\d+)?\s+"
    r"tp:([\d.]+)\s+"
    r"tpdist:\d+(?:\.\d+)?\s+"
    r"rr:([\d.]+)\s+"
    r"(m30bbloc:\d+)\s+"
    r"(m15:([FSCVR-]+))\s+"
    r"(m30:([FSCVR-]+))\s+"
    r"h1bbloc:(\d+)"
)

# [NEW_ORDER_OPEN] — ticket and timestamp
OPEN_RE = re.compile(r"\[NEW_ORDER_OPEN\].*OPEN_TICKET:(\d+)")
OPEN_TS_RE = re.compile(r"(?P<ts>\d{4}\.\d{2}\.\d{2}[\d :]+)")

# [NEW_ORDER_CLOSE] — ticket
CLOSE_RE = re.compile(r"\[NEW_ORDER_CLOSE\].*OPEN_TICKET:(\d+)")

# Profit from CLOSE or ORDERINFO
PROFIT_RE = re.compile(r"(?:CLOSED_PROFIT|PROFIT):([+-]?\d+(?:\.\d+)?)")
ORDERINFO_RE = re.compile(r"\[ORDERINFO\].*(?:BUY_PROFIT|SELL_PROFIT):([+-]?\d+(?:\.\d+)*)")


def extract_trades():
    """
    Parse log, match each ENTRY to its NEW_ORDER_OPEN (nearest following line -> ticket),
    then look up CLOSE for that ticket. Returns list of trade dicts with all fields
    needed by both designs: raw_m15, raw_m30, raw_dir (from EA) AND the per-TF lines at entry.
    """
    raw_lines = LOG_FILE.read_text().splitlines()

    # Build OPEN records indexed by line number
    open_records = []
    for i, line in enumerate(raw_lines):
        m = OPEN_RE.search(line)
        if not m:
            continue
        ticket = int(m.group(1))
        ts_match = OPEN_TS_RE.search(line)
        ts_str = ts_match.group("ts") if ts_match else ""
        open_records.append({"ticket": ticket, "ts_str": ts_str, "line_idx": i})

    # Build CLOSE records (ticket + profit)
    close_records = []
    for i, line in enumerate(raw_lines):
        # First try [NEW_ORDER_CLOSE] (BUY orders)
        m = CLOSE_RE.search(line)
        if m:
            ticket = int(m.group(1))
            profit = None
            pm = PROFIT_RE.search(line)
            if pm:
                profit = float(pm.group(1))
            else:
                # Check following ORDERINFO lines (up to 30 ahead for SELL orders)
                for j in range(i + 1, min(i + 31, len(raw_lines))):
                    oi_m = ORDERINFO_RE.search(raw_lines[j])
                    if oi_m:
                        profit = float(oi_m.group(1))
                        break

            exit_price_match = re.search(r"CLOSED_PRICE:([+-]?\d+(?:\.\d+)?)", line)
            exit_price_str = exit_price_match.group(1) if exit_price_match else None
            open_time_match = re.search(r"OPEN_TIME:(\d{4}\.\d{2}\.\d{2}[\d :]+)", line)
            open_time_str = open_time_match.group(1) if open_time_match else ""

            close_records.append({
                "ticket": ticket,
                "profit": profit,
                "exit_price": float(exit_price_str) if exit_price_str is not None else None,
                "open_time": parse_timestamp(open_time_str),
                "line_idx": i,
            })
            continue

        # For SELL orders: look for ORDERINFO with BUY_PROFIT/SELL_PROFIT
        oi_m = ORDERINFO_RE.search(line)
        if oi_m:
            profit_val = float(oi_m.group(1))
            buy_match = re.search(r"BUY_PROFIT", line)
            sell_match = re.search(r"SELL_PROFIT", line)
            if sell_match and not buy_match:
                ticket = None
                for k in range(max(0, i - 100), i):
                    open_m = re.search(r"\[NEW_ORDER_OPEN\].*OPEN_TICKET:(\d+)", raw_lines[k])
                    if open_m and int(open_m.group(1)) == oi_m.group("SELL_TICKET_NUM"):
                        ticket = int(open_m.group(1))
                        break
                if ticket:
                    close_records.append({
                        "ticket": ticket,
                        "profit": profit_val,
                        "exit_price": None,
                        "open_time": "",
                        "line_idx": i,
                    })

    # Map ticket -> close record (keep earliest line)
    close_by_ticket = {}
    for cr in close_records:
        if cr["ticket"] not in close_by_ticket:
            close_by_ticket[cr["ticket"]] = cr
        elif cr["line_idx"] < close_by_ticket[cr["ticket"]]["line_idx"]:
            close_by_ticket[cr["ticket"]] = cr

    # Match ENTRY to OPEN (nearest following line)
    trades = []
    unmatched_entries = []

    for i, line in enumerate(raw_lines):
        m = ENTRY_RE.search(line)
        if not m:
            continue

        entry_line_idx = i
        dir_str = re.sub(r"^dir:", "", m.group(1))  # "UP" or "DOWN"
        entry_px = float(m.group(2))
        sl_px = float(m.group(3))
        tp_px = float(m.group(4))
        rr = float(m.group(5))
        m30bbloc_val = m.group(6)
        raw_m15_state = m.group(7)      # e.g. "m15:F" or just "F"
        raw_m30_state = m.group(9)      # same
        h1bbloc = int(m.group(11))

        ts_match = OPEN_TS_RE.search(line)
        entry_ts_str = ts_match.group("ts") if ts_match else ""
        entry_ts_key = parse_timestamp(entry_ts_str)

        # ---- DEBUG: print what we're looking at ----
        # print(f"DEBUG ENTRY line {i}: {line[:60]}...")

        # Look for nearest OPEN after this ENTRY
        matched_open = None
        ticket = None
        for j in range(i + 1, min(i + 30, len(raw_lines))):
            if "OPEN_TICKET:" in raw_lines[j]:
                tk = re.search(r"OPEN_TICKET:(\d+)", raw_lines[j])
                if tk:
                    ticket = int(tk.group(1))
                    matched_open = {"ticket": ticket, "line_idx": j}
                    break

        if matched_open is None:
            unmatched_entries.append({
                "datetime": entry_ts_str,
                "line": line,
                "ticket": None,
                "reason": "No NEW_ORDER_OPEN found after ENTRY",
            })
            continue

        ticket = matched_open["ticket"]
        close_info = close_by_ticket.get(ticket)
        if close_info is None:
            unmatched_entries.append({
                "datetime": entry_ts_str,
                "line": line,
                "ticket": ticket,
                "reason": "No NEW_ORDER_CLOSE found",
            })
            continue

        profit = close_info["profit"]
        exit_price = close_info.get("exit_price")
        if profit is None:
            pm = PROFIT_RE.search(line)
            if pm:
                profit = float(pm.group(1))
            else:
                unmatched_entries.append({
                    "datetime": entry_ts_str,
                    "line": line,
                    "ticket": ticket,
                    "reason": "No profit field",
                })
                continue

        outcome = "WIN" if profit > 0 else ("LOSS" if profit < 0 else "NEUTRAL")

        # Clean raw state strings (strip prefix)
        m15_clean = re.sub(r"^m15:", "", raw_m15_state)
        m30_clean = re.sub(r"^m30:", "", raw_m30_state)

        # ---- Capture the per-TF log lines at this bar for DESIGN B ----
        # Find the [M5]/[M15]/[M30]/[H1]/[H4] lines that appear at/just before the entry minute.
        # We'll look a small window backwards from the OPEN line (which is right after ENTRY).
        tf_lines = {}
        # Look back up to ~80 lines (to catch M5 line at 08:15:01 which is before ENTRY at 08:15:02)
        for j in range(max(0, entry_line_idx - 80), min(entry_line_idx + 60, len(raw_lines))):
            ln = raw_lines[j]
            # Look for any line containing a W_stage pattern for our TFs
            if not any(re.search(rf"W_stage_{tf}:", ln) for tf in ("M5", "M15", "M30", "H1", "H4")):
                # print(f"DEBUG: skipping line {j}: {ln[:60]}")
                continue
            # Extract TF name from "W_stage_M15:" etc.
            # Format: W_stage_<tf>:(STAGE)[cur, prev1] — capture cur and prev1 from the second bracketed group.
            for tf in ("M5", "M15", "M30", "H1", "H4"):
                w_match = re.search(rf"W_stage_{tf}:\s*\([^)]*\)\[([0-9]+),\s*([0-9]+)", ln)
                if w_match:
                    cur = int(w_match.group(1))
                    prev1 = int(w_match.group(2))
                    # Also capture diffMid_Trend for M15/M30 (used for direction: 1=up, 2=down, >=3=sideways)
                    if tf in ("M15", "M30"):
                        mid_match = re.search(rf"diffMid_Trend_{tf}:\s*\[\s*([0-9.]+)", ln)
                        if mid_match:
                            # Use the first value (cur) for diffMid_Trend direction
                            dmt_val = int(float(mid_match.group(1)))  # Convert float to int
                    else:
                        dmt_val = None

                    # Capture BBUpDn (state 1=up, 2=down) for direction fallback — 3 values
                    bb_match = re.search(rf"BBUpDn_{tf}:\s*\[\s*([0-9]+)", ln)
                    if bb_match:
                        bb_val = int(bb_match.group(1))
                    else:
                        bb_val = None

                    tf_lines[tf] = {"cur": cur, "prev1": prev1, "diffMid_Trend": dmt_val, "BBUpDn": bb_val}

        # Store raw_dir from EA (used by Design A)
        trade_rec = {
            "datetime": entry_ts_str,
            "dir": dir_str,
            "raw_dir": dir_str,  # DESIGN A: EA-logged direction
            "m15_raw": m15_clean,
            "m30_raw": m30_clean,
            "entry_px": entry_px,
            "exit_px": exit_price,
            "profit": profit,
            "sl": sl_px,
            "tp": tp_px,
            "rr": rr,
            "outcome": outcome,
            "ticket": ticket,
            # DESIGN B fields (computed from raw log lines)
            "tf_lines": tf_lines,
        }
        trades.append(trade_rec)

    return trades, unmatched_entries


def stats_for(trades):
    """Count, win-rate, gross_profit, gross_loss, PF."""
    if not trades:
        return {"count": 0, "win_rate": None, "total_profit": 0.0,
                "gross_profit": 0.0, "gross_loss": 0.0, "pf": None}

    wins = sum(1 for t in trades if t["outcome"] == "WIN")
    losses = sum(1 for t in trades if t["outcome"] == "LOSS")
    total_profit = sum(t["profit"] for t in trades)
    gross_profit = sum(t["profit"] for t in trades if t["profit"] > 0)
    gross_loss = abs(sum(t["profit"] for t in trades if t["profit"] < 0))

    win_rate = wins / len(trades) if trades else None
    pf = gross_profit / gross_loss if gross_loss != 0 else (math.inf if gross_profit != 0 else None)

    return {
        "count": len(trades),
        "win_rate": win_rate,
        "total_profit": total_profit,
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        "pf": pf,
    }


# =============================================================================
# DESIGN A — ea_labels (reproduces current behavior)
# =============================================================================

def label_ea(trade):
    """Return (state, dir) using EA-logged fields."""
    # state: m15_raw (or m30_raw as fallback if missing)
    state = trade["m15_raw"] or trade["m30_raw"] or "UNKNOWN"
    # dir: raw_dir from EA
    direction = trade["raw_dir"]
    return state, direction


# =============================================================================
# DESIGN B — fast_subscenario (compute from RAW log fields)
# =============================================================================

def classify_state(cur):
    """Map stage value to high-level state."""
    if cur is None:
        return "NONE"
    # SQZ range
    if 400 <= cur < 500:
        return "SQZ"
    # FLY_PSHRINK: stage 512/522 with diffBBW < 0 (handled in onset_state)
    if 500 <= cur < 600:
        return "FLY"
    # otherwise negative → SHRINK
    return "SHRINK"


def classify_touch(cur, prev1):
    """Determine Touch Type from stage progression."""
    if cur is None:
        return "Type 3"
    if prev1 is not None and 400 <= prev1 < 500:
        return "Type 2"
    return "Type 1"


def compute_state_from_raw(tf_lines, tf_name):
    """
    Compute the in-state for a given TF using the raw log fields.
    We look at the line that contains W_stage_<tf>: and diffBBW_<tf>:
    (these are typically the same line). The classification follows the
    rules used in fast_subscenario_compute.py: FLY_PSHRINK is only
    reported when prev1 was 500-599 and cur is 512/522.

    Returns a dict: {"state": ..., "touch": ..., "used_field": ...}.
    """
    if tf_name not in tf_lines:
        return {"state": "UNKNOWN", "touch": "N/A", "used_field": "none"}

    cur = tf_lines[tf_name]["cur"]
    prev1 = tf_lines[tf_name].get("prev1")

    # Determine state
    if 400 <= prev1 < 500 and cur in (512, 522):
        state = "FLY_PSHRINK"
    elif prev1 is not None and 400 <= prev1 < 500:
        state = "SQZ"
    elif cur is not None and cur >= 0:
        state = "FLY"
    elif cur is not None:
        state = "SHRINK"
    else:
        state = "NONE"

    touch = classify_touch(cur, prev1)
    return {"state": state, "touch": touch, "used_field": f"W_stage_{tf_name}"}


def compute_direction_from_raw(tf_lines):
    """
    Direction is derived from diffMid_Trend_M15 (preferred) or BBUpDn_M15/trend_M15.
    We scan the same window used for tf_lines and look for any line that
    contains "diffMid_Trend_M15:". If found, use its first value:
      1 → UP, 2 → DOWN, >=3 → SIDEWAYS.
    If not found, fall back to BBUpDn_M15 / trend_M15.

    Returns {"dir": ..., "used_field": ...}.
    """
    # Try diffMid_Trend first (only M15 and M30 have this field)
    for tf in ("M15", "M30"):
        if tf not in tf_lines:
            continue
        dmt = tf_lines[tf].get("diffMid_Trend")  # our captured value
        if dmt is not None:
            if dmt == 1:
                return {"dir": "UP", "used_field": f"diffMid_Trend_{tf}"}
            elif dmt == 2:
                return {"dir": "DOWN", "used_field": f"diffMid_Trend_{tf}"}
            else:  # >=3 means sideways (sideways/sideway-down/sideway-up)
                return {"dir": "SIDEWAYS", "used_field": f"diffMid_Trend_{tf}"}

    # Fallback to BBUpDn (state 1=up, 2=down)
    for tf in ("M5", "M15", "M30", "H1", "H4"):
        if tf not in tf_lines:
            continue
        bb = tf_lines[tf].get("BBUpDn")
        if bb is not None:
            if bb == 1:
                return {"dir": "UP", "used_field": f"BBUpDn_{tf}"}
            elif bb == 2:
                return {"dir": "DOWN", "used_field": f"BBUpDn_{tf}"}
    # No usable field — mark as SIDEWAYS (should not happen with valid logs)
    return {"dir": "SIDEWAYS", "used_field": "none"}


def label_fast_subscenario(trade):
    """
    Compute STATE from M15 (primary) and DIRECTION from raw fields at the entry bar.
    Returns (state, direction) as strings for grouping.
    """
    # DESIGN B: use M15 state (as per task spec) — we also compute M30 but only report M15
    m15_state_info = compute_state_from_raw(trade["tf_lines"], "M15")
    dir_info = compute_direction_from_raw(trade["tf_lines"])

    return (m15_state_info["state"], dir_info["dir"])


# =============================================================================
# GROUPING AND REPORT WRITER (shared by both designs)
# =============================================================================

def group_and_report(trades, labeler, out_path, title):
    """
    Apply labeler to each trade to get (state, dir), then write the same tables
    and per-trade ledger as the original report. Skips groups < 20.
    """
    # Group by (state, dir) for cross-tab; also keep single-groupings
    groups = defaultdict(list)
    for t in trades:
        s, d = labeler(t)
        groups[(s, d)].append(t)

    # Single groupings
    group_m15 = defaultdict(list)
    group_dir = defaultdict(list)
    group_all = defaultdict(list)  # (state, dir) -> list

    for t in trades:
        s, d = labeler(t)
        group_m15[s].append(t)
        group_dir[d].append(t)
        group_all[(s, d)].append(t)

    matched = len(trades)
    unmatched = len(trades) - matched  # all trades are matched here

    def write_table(header, groups_dict):
        # Handle both single and double-column headers
        if isinstance(header, tuple) and len(header) == 2:
            header1, header2 = header
            header_line = f"| {header1} | {header2} | Count | Win-Rate | Total Profit | PF |"
            sep_line = "|-----|------|-------|----------|---------------|-----|"
        else:
            header1 = header[0] if header else "State"
            header2 = "Dir"  # default for single-column state table
            header_line = f"| {header1} | {header2} | Count | Win-Rate | Total Profit | PF |"
            sep_line = "|-----|------|-------|----------|---------------|-----|"
        lines = [header_line]
        lines.append(sep_line)
        # Handle both single-key and tuple-key groupings
        for key, lst in sorted(groups_dict.items()):
            if isinstance(key, tuple):
                k1, k2 = key
            else:
                k1 = key
                k2 = ""
            s = stats_for(lst)
            if s["count"] < 20:
                continue
            pf_str = f"{s['pf']:.2f}" if s["pf"] is not None else "—"
            lines.append(
                f"| {k1} | {k2} | {s['count']} | {s['win_rate']:.1%} | {s['total_profit']:+.2f} | {pf_str} |"
            )
        return "\n".join(lines)

    lines = []

    # Header
    lines.append(f"# TRADE P&L by Scenario — Design: {title}\n")
    lines.append(f"**Labels:** {title}")
    if "ea_labels" in title:
        lines.append("Source: EA-logged fields (raw_m15, raw_dir).")
    else:
        lines.append("Source: Raw log fields at entry bar (W_stage_M15 / diffMid_Trend_M15 or BBUpDn).")

    # Summary
    overall = stats_for(trades)
    win_count = sum(1 for t in trades if t["outcome"] == "WIN")
    lines.append(f"\n## Summary\n")
    lines.append(f"1. **Total [TRADE] entries found:** {len(trades) + unmatched}")
    lines.append(f"   - Matched: **{matched}**")
    lines.append(f"   - Unmatched: **{unmatched}**\n")
    lines.append(f"2. **Overall statistics:**\n")
    lines.append(f"   - Win-rate: {overall['win_rate']:.1%} ({win_count} wins / {len(trades)} total)")
    lines.append(f"   - Total profit: {overall['total_profit']:+.2f}")
    if overall["pf"] is not None and overall["pf"] != 0:
        lines.append(f"   - PF: {overall['gross_profit']:+.2f} / {overall['gross_loss']:+.2f} = {overall['pf']:.2f}")
    else:
        lines.append("   - PF: 0 (no losses or no wins)")

    # By state
    lines.append("\n## By State\n")
    lines.append(write_table(("State",), group_m15))

    # By direction
    lines.append("\n## By Direction\n")
    lines.append(write_table(("Dir",), group_dir))

    # Cross-tab
    lines.append("\n## By (State × Direction)\n")
    lines.append(write_table(("",), group_all))

    # Per-trade ledger
    lines.append("\n## Per-Trade Ledger\n")
    lines.append("| # | Entry datetime | Dir | State | Exit px | Profit | Cum P&L | W/L |\n")
    lines.append("|---|----------------|-----|-------|---------|--------|---------|-----|\n")

    cum_pnl = 0.0
    for idx, t in enumerate(sorted(trades, key=lambda x: x["datetime"]), 1):
        dt = t["datetime"].rstrip("0").rstrip(".")
        exit_px_str = f"{t['exit_px']:.2f}" if t["exit_px"] is not None else "-"
        cum_pnl += t["profit"]
        lines.append(
            f"| {idx} | {dt} | {t['dir']} | {t['m15_raw']} | "
            f"{exit_px_str} | {t['profit']:+.2f} | {cum_pnl:+.2f} | {t['outcome']} |\n"
        )

    lines.append(f"\n**Total:** {matched} trades | — | — | — | — | — | **{overall['total_profit']:+.2f}** | — |\n")

    if unmatched:
        lines.append("\n### Unmatched entries\n")
        for ue in sorted(trades, key=lambda x: x["datetime"])[:unmatched]:
            lines.append(f"- **Unmatched:** {ue['datetime']} — {ue.get('reason', 'N/A')}\n")

    # Write
    Path(out_path).write_text("\n".join(lines), encoding="utf-8")


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="TRADE P&L Engine — compute stats by design.")
    parser.add_argument(
        "--design",
        choices=["ea_labels", "fast_subscenario"],
        default="ea_labels",
        help="Design to use (default: ea_labels)"
    )
    args = parser.parse_args()

    trades, unmatched = extract_trades()

    title_map = {"ea_labels": "EA-Logged", "fast_subscenario": "Raw-Computed"}
    labeler_map = {"ea_labels": label_ea, "fast_subscenario": label_fast_subscenario}

    out_path = f"references/TRADE_PNL_{args.design.upper().replace('-', '_')}.md"
    group_and_report(trades, labeler_map[args.design], out_path, title_map[args.design])

    print(f"\nDesign: {args.design}")
    print(f"Matched trades: {len(trades)}")
    print(f"Overall total profit: {stats_for(trades)['total_profit']:+.2f}")
    print(f"Report written to: {out_path}\n")


if __name__ == "__main__":
    main()
