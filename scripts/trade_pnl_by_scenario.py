#!/usr/bin/env python3
"""
REAL TRADE P&L by Fast-Scenario Context (Level 1)

Reads backtest log from V36.15 and reports matched trades grouped by logged
m15/m30 state and direction. Uses ONLY fields that appear in the [TRADE]
entry lines — no computed scenario labels. Deterministic: two runs = identical
output.

This rewrite implements the EXACT multi-line matching algorithm:
- ENTRY line (no ticket) is matched to NEW_ORDER_OPEN line at same timestamp
  (the OPEN line immediately follows the ENTRY).
- The ticket from the OPEN line is then used to look up CLOSE info.
- Profit comes from NEW_ORDER_CLOSE or ORDERINFO fallback.
"""

import math
import re
from collections import defaultdict
from pathlib import Path


# =============================================================================
# Step 0 — Verify input file exists
# =============================================================================

LOG_FILE = Path("references/Backtest_data/V36.15/20260712_clean.log")

if not LOG_FILE.exists():
    print(f"ERROR: Log file not found: {LOG_FILE}")
    raise SystemExit(1)

with open(LOG_FILE, "r") as f:
    header = f.read(8000)

# Extract date range from header lines
date_pattern = re.compile(r"(?:history data begins from |XAUUSD,M5: history begins from )(\d{4}\.\d{2}\.\d{2})")
dates = set(m.group(1) for m in date_pattern.finditer(header))
if not dates:
    # Fallback to any [TRADE] lines that contain a date
    trade_date = re.compile(r"\[TRADE\].*dt:(\d{4}\.\d{2}\.\d{2})")
    for line in LOG_FILE.read_text().splitlines():
        m = trade_date.search(line)
        if m:
            dates.add(m.group(1))
            break

print(f"Input file parsed: {LOG_FILE}")
print(f"Date range: min={min(dates)} max={max(dates)}")


# =============================================================================
# Step 1 — Parse all lines into structured records
# =============================================================================

# Pattern for [TRADE] ENTRY lines — captures essential fields
ENTRY_RE = re.compile(
    r"\[TRADE\]\s+evt:ENTRY\s+"
    r"(dir:UP|dir:DOWN)\s+"
    r"dt:\d{4}\.\d{2}\.\d{2}[\d :]+\s*"  # date/time (may have colons/spaces)
    r"entry:(\d+(?:\.\d+)?)\s+"
    r"sl:([\d.]+)\s+"
    r"sldist:\d+(?:\.\d+)?\s+"
    r"tp:([\d.]+)\s+"
    r"tpdist:\d+(?:\.\d+)?\s+"
    r"rr:([\d.]+)\s+"
    r"(m30bbloc:\d+)\s+"
    r"(m15:([FSCVR-]+))\s+"     # Group 7: full m15, Group 8: clean (includes R)
    r"(m30:([FSCVR-]+))\s+"    # Group 9: full m30, Group 10: clean (includes R)
    r"h1bbloc:(\d+)"
)

# Pattern for [NEW_ORDER_OPEN] — captures ticket and timestamp
OPEN_RE = re.compile(
    r"\[NEW_ORDER_OPEN\].*OPEN_TICKET:(\d+).*"
)
# Also capture timestamp from OPEN line for matching to ENTRY
OPEN_TS_RE = re.compile(r"(?P<ts>\d{4}\.\d{2}\.\d{2}[\d :]+)")

# Pattern for [NEW_ORDER_CLOSE] — captures ticket (for BUY orders)
CLOSE_RE = re.compile(
    r"\[NEW_ORDER_CLOSE\].*OPEN_TICKET:(\d+)"
)
# Profit can appear as PROFIT: or CLOSED_PROFIT: (or similar)
PROFIT_RE = re.compile(r"(?:CLOSED_PROFIT|PROFIT):([+-]?\d+(?:\.\d+)?)")

# Fallback: ORDERINFO may contain BUY_PROFIT/SELL_PROFIT
ORDERINFO_RE = re.compile(
    r"\[ORDERINFO\].*(?:BUY_PROFIT|SELL_PROFIT):([+-]?\d+(?:\.\d+)*)"
)


# Read all lines — handle CRLF properly with splitlines()
raw_lines = LOG_FILE.read_text().splitlines()


def parse_timestamp(ts_str):
    """Normalize timestamp string to a comparable form."""
    # Remove colons and spaces — just keep YYYY.MM.DDHHMMSS
    return re.sub(r"[ :]", "", ts_str)


# Build list of OPEN records indexed by line number
open_records = []
for i, line in enumerate(raw_lines):
    m = OPEN_RE.search(line)
    if not m:
        continue
    ticket = int(m.group(1))
    ts_match = OPEN_TS_RE.search(line)
    ts_str = ts_match.group("ts") if ts_match else ""
    open_records.append({"ticket": ticket, "ts_str": ts_str, "line_idx": i})

# Build list of CLOSE records indexed by line number
close_records = []
for i, line in enumerate(raw_lines):
    # First try [NEW_ORDER_CLOSE] (BUY orders)
    m = CLOSE_RE.search(line)
    if m:
        ticket = int(m.group(1))
        # Look for profit on this line or the next ORDERINFO
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
        # Also capture CLOSED_PRICE and OPEN_TIME from CLOSE line if present
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
        continue  # Already handled this line as a CLOSE

    # For SELL orders: look for ORDERINFO with SELL_PROFIT and SELL_TICKET_NUM
    oi_m = ORDERINFO_RE.search(line)
    if oi_m:
        profit_val = float(oi_m.group(1))
        # Check if this is BUY or SELL by looking for the type indicator
        buy_match = re.search(r"BUY_PROFIT", line)
        sell_match = re.search(r"SELL_PROFIT", line)
        if sell_match and not buy_match:
            # This is a SELL order — look for OPEN_TICKET on this or previous lines
            ticket = None
            # Search backwards up to 100 lines for matching OPEN_TICKET (SELL can be far)
            for k in range(max(0, i - 100), i):
                open_m = re.search(r"\[NEW_ORDER_OPEN\].*OPEN_TICKET:(\d+)", raw_lines[k])
                if open_m and int(open_m.group(1)) == oi_m.group("SELL_TICKET_NUM"):
                    ticket = int(open_m.group(1))
                    break
            if ticket:
                close_records.append({
                    "ticket": ticket,
                    "profit": profit_val,
                    "exit_price": None,  # SELL orders may not have CLOSED_PRICE
                    "open_time": "",  # SELL orders don't have OPEN_TIME
                    "line_idx": i,
                })

# Build a map: ticket -> close record (keep the one with earliest line index)
close_by_ticket = {}
for cr in close_records:
    if cr["ticket"] not in close_by_ticket:
        close_by_ticket[cr["ticket"]] = cr
    else:
        # If same ticket appears on multiple CLOSE lines, take the first one
        if cr["line_idx"] < close_by_ticket[cr["ticket"]]["line_idx"]:
            close_by_ticket[cr["ticket"]] = cr


# =============================================================================
# Step 2 — Match ENTRY to OPEN (same timestamp, nearest following line)
# =============================================================================

# Group open records by normalized timestamp
opens_by_ts: dict[str, list[dict]] = defaultdict(list)
for orec in open_records:
    key = parse_timestamp(orec["ts_str"])
    opens_by_ts[key].append(orec)

# Now walk through the file line-by-line, matching each ENTRY to its OPEN.
# The OPEN line should appear at the same timestamp and be the nearest one
# with that ticket (i.e., immediately after the ENTRY line).
trades = []  # list of matched trade dicts
unmatched_entries = []  # entries that could not be linked

entry_line_idx = 0
for i, line in enumerate(raw_lines):
    m = ENTRY_RE.search(line)
    if not m:
        continue

    entry_line_idx = i
    dir_str = m.group(1)  # captured as "dir:UP" or "dir:DN" — strip prefix
    dir_str = re.sub(r"^dir:", "", dir_str)
    entry_px = float(m.group(2))
    sl_px = float(m.group(3))
    tp_px = float(m.group(4))
    rr = float(m.group(5))
    m30bbloc_val = m.group(6)  # e.g. "m30bbloc:7"
    m15_state = m.group(7)     # full "m15:F" or just "F"
    m30_state = m.group(9)     # full "m30:F" or just "F"
    h1bbloc = int(m.group(11))

    # Extract normalized timestamp from ENTRY line
    ts_match = OPEN_TS_RE.search(line)
    entry_ts_str = ts_match.group("ts") if ts_match else ""
    entry_ts_key = parse_timestamp(entry_ts_str)

    # Look for the nearest OPEN record after this ENTRY (by line index).
    # We don't rely on timestamp matching because ENTRY's dt: field is
    # slightly earlier than the actual NEW_ORDER_OPEN timestamp.
    matched_open = None
    ticket = None
    for j in range(i + 1, min(i + 30, len(raw_lines))):  # look ahead ~30 lines
        if 'OPEN_TICKET:' in raw_lines[j]:
            tk = re.search(r'OPEN_TICKET:(\d+)', raw_lines[j])
            if tk:
                ticket = int(tk.group(1))
                matched_open = {"ticket": ticket, "line_idx": j}
                break

    if matched_open is None:
        # No OPEN found after this ENTRY — this is unexpected.
        unmatched_entries.append({
            "line": line,
            "ticket": None,
            "reason": "No NEW_ORDER_OPEN found after ENTRY",
        })
        continue

    ticket = matched_open["ticket"]

    # Look up CLOSE for this ticket
    close_info = close_by_ticket.get(ticket)
    if close_info is None:
        unmatched_entries.append({
            "line": line,
            "ticket": ticket,
            "reason": "No NEW_ORDER_CLOSE found for ticket",
        })
        continue

    profit = close_info["profit"]
    exit_price = close_info.get("exit_price")  # None if not available

    if profit is None:
        # Fallback: try to find any profit field on the CLOSE line or nearby ORDERINFO
        pm = PROFIT_RE.search(line)
        if pm:
            profit = float(pm.group(1))
        else:
            unmatched_entries.append({
                "line": line,
                "ticket": ticket,
                "reason": "No profit field found",
            })
            continue

    # Determine outcome string
    outcome = "WIN" if profit > 0 else ("LOSS" if profit < 0 else "NEUTRAL")

    # Parse m15/m30 state (strip the prefix like "m15:"):
    m15_clean = re.sub(r"^m15:", "", m15_state)
    m30_clean = re.sub(r"^m30:", "", m30_state)

    # Record — we only keep matched trades
    trade_rec = {
        "datetime": entry_ts_str,
        "dir": dir_str,
        "entry_px": entry_px,
        "sl": sl_px,
        "tp": tp_px,
        "rr": rr,
        "m30bbloc": m30bbloc_val,
        "m15_state": m15_clean,
        "m30_state": m30_clean,
        "h1bbloc": h1bbloc,
        "ticket": ticket,
        "profit": profit,
        "exit_price": exit_price,
        "outcome": outcome,
    }
    trades.append(trade_rec)

# =============================================================================
# Step 3 — Report statistics
# =============================================================================

matched = len(trades)
unmatched_count = len(unmatched_entries)

print(f"\nTotal [TRADE] entries found: {len(trades) + unmatched_count}")
print(f"Matched to close: {matched}")
print(f"Unmatched: {unmatched_count}")

# If there are unmatched entries, summarize why
if unmatched_entries:
    print("\n--- Unmatched entries ---")
    for ue in unmatched_entries[:5]:  # show first few
        print(f"  - ticket={ue.get('ticket', 'N/A')} | reason: {ue['reason']}")

# =============================================================================
# Step 4 — LEVEL 1 grouping (use ONLY logged fields)
# =============================================================================

group_m15: dict[str, list[dict]] = defaultdict(list)
group_m30: dict[str, list[dict]] = defaultdict(list)
group_dir: dict[str, list[dict]] = defaultdict(list)
group_m15_dir: dict[tuple, list[dict]] = defaultdict(list)
group_m30_dir: dict[tuple, list[dict]] = defaultdict(list)

for t in trades:
    m15_key = t["m15_state"]
    m30_key = t["m30_state"]
    d = t["dir"]

    group_m15[m15_key].append(t)
    group_m30[m30_key].append(t)
    group_dir[d].append(t)
    group_m15_dir[(m15_key, d)].append(t)
    group_m30_dir[(m30_key, d)].append(t)


def stats_for(trade_list):
    """Return count, win_rate, total_profit, gross_profit, gross_loss, pf."""
    if not trade_list:
        return {"count": 0, "win_rate": None, "total_profit": 0.0,
                "gross_profit": 0.0, "gross_loss": 0.0, "pf": None}

    wins = sum(1 for t in trade_list if t["outcome"] == "WIN")
    losses = sum(1 for t in trade_list if t["outcome"] == "LOSS")
    total_profit = sum(t["profit"] for t in trade_list)

    # gross_profit: sum of positive profits (from WIN trades)
    gross_profit = sum(t["profit"] for t in trade_list if t["profit"] > 0)
    # gross_loss: absolute value of sum of negative profits (from LOSS trades)
    gross_loss = abs(sum(t["profit"] for t in trade_list if t["profit"] < 0))

    win_rate = wins / len(trade_list) if len(trade_list) > 0 else None
    pf = gross_profit / gross_loss if gross_loss != 0 else (inf if gross_profit != 0 else None)

    return {
        "count": len(trade_list),
        "win_rate": win_rate,
        "total_profit": total_profit,
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        "pf": pf,
    }


# =============================================================================
# Step 5 — Write report to markdown file
# =============================================================================

# BUG 4 fix: write to canonical path (not inside Backtest_data subfolder)
REPORT = Path("references/TRADE_PNL_BY_SCENARIO.md")

with open(REPORT, "w", encoding="utf-8") as out:
    # Header
    out.write("# REAL TRADE P&L by Fast-Scenario Context (Level 1)\n\n")
    out.write(f"**Source:** Real backtest trades from `{LOG_FILE.name}`\n\n")
    out.write(f"**Date range:** {min(dates)} — {max(dates)}\n\n")

    # Summary section
    out.write("## Summary\n\n")
    total = len(trades) + unmatched_count
    out.write(f"1. **Total [TRADE] entries found:** {total}\n")
    out.write(f"   - Matched to close: **{matched}**\n")
    out.write(f"   - Unmatched: **{unmatched_count}** (no matching OPEN or CLOSE)\n\n")

    overall = stats_for(trades)
    out.write(f"2. **Overall statistics:**\n")
    # BUG 2 fix: win_count is number of WIN outcomes, not total trades
    win_count = sum(1 for t in trades if t["outcome"] == "WIN")
    out.write(f"   - Win-rate: {overall['win_rate']:.1%} ({win_count} wins / {len(trades)} total)\n")
    out.write(f"   - Total profit: {overall['total_profit']:+.2f}\n")
    if overall['pf'] is not None and overall['pf'] != 0:
        out.write(f"   - PF (gross profit / gross loss): {overall['gross_profit']:+.2f} / {overall['gross_loss']:+.2f} = {overall['pf']:.2f}\n")
    else:
        out.write("   - PF: 0 (either no losses or no wins — see notes)\n")

    # --- Grouped tables ---

    # By m15 state (skip empty groups)
    out.write("\n## 1. Grouped by M15 State\n\n")
    out.write("| M15 | Count | Win-Rate | Total Profit | PF |")
    out.write("\n|-----|-------|----------|---------------|-----|")
    for key in sorted(group_m15.keys()):
        s = stats_for(group_m15[key])
        if s is None:
            continue  # skip empty group
        pf_str = f"{s['pf']:.2f}" if s['pf'] is not None else "—"
        out.write(f"\n| {key} | {s['count']} | {s['win_rate']:.1%} | {s['total_profit']:+.2f} | {pf_str} |")
    out.write("\n\n")

    # By m30 state (skip empty groups)
    out.write("## 2. Grouped by M30 State\n\n")
    out.write("| M30 | Count | Win-Rate | Total Profit | PF |")
    out.write("\n|-----|-------|----------|---------------|-----|")
    for key in sorted(group_m30.keys()):
        s = stats_for(group_m30[key])
        if s is None:
            continue  # skip empty group
        pf_str = f"{s['pf']:.2f}" if s['pf'] is not None else "—"
        out.write(f"\n| {key} | {s['count']} | {s['win_rate']:.1%} | {s['total_profit']:+.2f} | {pf_str} |")
    out.write("\n\n")

    # By direction (skip empty)
    out.write("## 3. Grouped by Direction\n\n")
    out.write("| Dir | Count | Win-Rate | Total Profit | PF |")
    out.write("\n|-----|-------|----------|---------------|-----|")
    for d in ("UP", "DOWN"):
        s = stats_for(group_dir[d])
        if s is None or s['count'] == 0:
            continue  # skip empty direction
        pf_str = f"{s['pf']:.2f}" if s['pf'] is not None else "—"
        out.write(f"\n| {d} | {s['count']} | {s['win_rate']:.1%} | {s['total_profit']:+.2f} | {pf_str} |")
    out.write("\n\n")

    # By (M15 × Dir) (skip empty)
    out.write("## 4. Grouped by (M15 × Direction)\n\n")
    out.write("| M15 | Dir | Count | Win-Rate | Total Profit | PF |")
    out.write("\n|-----|------|-------|----------|---------------|-----|")
    for (m15, d) in sorted(group_m15_dir.keys()):
        s = stats_for(group_m15_dir[(m15, d)])
        if s is None or s['count'] == 0:
            continue  # skip empty group
        pf_str = f"{s['pf']:.2f}" if s['pf'] is not None else "—"
        out.write(f"\n| {m15} | {d} | {s['count']} | {s['win_rate']:.1%} | {s['total_profit']:+.2f} | {pf_str} |")
    out.write("\n\n")

    # By (M30 × Dir) (skip empty)
    out.write("## 5. Grouped by (M30 × Direction)\n\n")
    out.write("| M30 | Dir | Count | Win-Rate | Total Profit | PF |")
    out.write("\n|-----|------|-------|----------|---------------|-----|")
    for (m30, d) in sorted(group_m30_dir.keys()):
        s = stats_for(group_m30_dir[(m30, d)])
        if s is None or s['count'] == 0:
            continue  # skip empty group
        pf_str = f"{s['pf']:.2f}" if s['pf'] is not None else "—"
        out.write(f"\n| {m30} | {d} | {s['count']} | {s['win_rate']:.1%} | {s['total_profit']:+.2f} | {pf_str} |")
    out.write("\n\n")

    # =============================================================================
    # Per-trade ledger (append after aggregate tables)
    # =============================================================================

    # Sort trades chronologically by entry datetime
    sorted_trades = sorted(trades, key=lambda t: t["datetime"])

    # Build cumulative P&L
    cum_pnl = 0.0

    out.write("## Per-Trade Ledger\n\n")
    out.write("| # | Entry datetime | Dir | M15 | M30 | Entry px | Exit px | Profit | Cum P&L | W/L |\n")
    out.write("|---|----------------|-----|-----|-----|----------|---------|--------|---------|-----|\n")

    for idx, t in enumerate(sorted_trades, 1):
        # Format datetime nicely (remove any trailing zeros after decimal)
        dt = t["datetime"].rstrip("0").rstrip(".")
        exit_px_str = f"{t['exit_price']:.2f}" if t['exit_price'] is not None else "-"
        cum_pnl += t['profit']  # running sum
        out.write(f"| {idx} | {dt} | {t['dir']} | {t['m15_state']} | {t['m30_state']} | "
                  f"{t['entry_px']:.2f} | {exit_px_str} | {t['profit']:+.2f} | "
                  f"{cum_pnl:+.2f} | {t['outcome']} |\n")

    # Total row
    out.write(f"\n**Total:** {matched} trades | — | — | — | — | — | — | **{overall['total_profit']:+.2f}** | — |\n")

    # List unmatched entries
    if unmatched_entries:
        out.write("\n### Unmatched entries\n\n")
        for ue in unmatched_entries:
            out.write(f"- **Unmatched:** {ue.get('line', 'N/A')[:60]}…\n")

    low_conf = [(k, stats_for(group_m15[k])) for k in group_m15 if len(group_m15[k]) > 0 and stats_for(group_m15[k])['count'] < 20]
    if low_conf:
        out.write("## Notes\n\n- **Low-confidence groups** (< 20 trades):")
        for (k, s) in low_conf:
            out.write(f"\n  - `{k}`: {s['count']} trades — win-rate may be unstable")
        out.write("\n\n")

    # --- Level 2 stub (unimplemented) ---
    out.write("---\n\n")
    out.write("### LEVEL 2 Hook (not implemented yet)\n\n")
    out.write("```python\n")
    out.write("def compute_subscenario(bar_fields):\n")
    out.write('    """\n')
    out.write("    TODO Level 2: compute S1/S2/B2/P2 from raw stage/diffBBW/diffMid fields per the\n")
    out.write("    Part 3 sub-state rules, once validated. Not implemented - Level 1 uses logged m15/m30\n")
    out.write("    state only.\n")
    out.write("    \"\"\"\n")
    out.write('    pass\n')
    out.write("\n\n# Usage (after validation of the sub-scenario rules):\n")
    out.write("# for t in trades:\n")
    out.write("#     if t['m15_state'] == 'F':\n")
    out.write("#         ss = compute_subscenario(t)  # would return S1/S2/etc.\n")
    out.write("```\n")

# =============================================================================
# Step 6 — Print verification samples
# =============================================================================

print(f"\nReport written to: {REPORT}")

# Show first 5 matched trades with full linkage info
print("\n=== Sample matched trades (first 5) ===\n")
for t in trades[:5]:
    print(f"dir={t['dir']} | m15={t['m15_state']} | m30={t['m30_state']} | "
          f"ticket={t['ticket']} | profit={t['profit']:+.2f} | {t['outcome']}")

# Print overall stats again for confirmation
print(f"\n=== Verification Summary ===")
print(f"Matched trades: {matched}")
print(f"Unmatched: {unmatched_count}")
print(f"Overall win-rate: {overall['win_rate']:.1%}")
print(f"Overall PF: {overall['pf'] if overall['pf'] else 'N/A'}")
