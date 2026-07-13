#!/usr/bin/env python3
"""
REAL TRADE P&L by Fast-Scenario Context (Level 1)

Reads backtest log from V36.15 and reports matched trades grouped by logged
m15/m30 state and direction. Uses ONLY fields that appear in the [TRADE]
entry lines — no computed scenario labels. Deterministic: two runs = identical
output.
"""

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
    # Fall back to any [TRADE] lines that contain a date
    trade_date = re.compile(r"\[TRADE\].*dt:(\d{4}\.\d{2}\.\d{2})")
    for line in LOG_FILE.read_text().splitlines():
        m = trade_date.search(line)
        if m:
            dates.add(m.group(1))
            break

print(f"Input file parsed: {LOG_FILE}")
print(f"Date range: min={min(dates)} max={max(dates)}")


# =============================================================================
# Step 1 — Extract real trades (entry + outcome)
# =============================================================================

# Pattern for [TRADE] ENTRY lines — captures essential fields
# Note: timestamp prefix may appear before [TRADE], so match anywhere on line
ENTRY_RE = re.compile(
    r"\[TRADE\]\s+evt:ENTRY\s+"
    r"(dir:UP|dir:DN)\s+"
    r"dt:\d{4}\.\d{2}\.\d{2}[\d :]+\s*"  # date/time with possible colons/spaces
    r"entry:(\d+(?:\.\d+)?)\s+"
    r"sl:([\d.]+)\s+"
    r"sldist:\d+(?:\.\d+)?\s+"
    r"tp:([\d.]+)\s+"
    r"tpdist:\d+(?:\.\d+)?\s+"
    r"rr:([\d.]+)\s+"
    r"(m30bbloc:\d+)\s+"
    r"(m15:([FSCV-]+))\s+"
    r"(m30:([FSCV-]+))\s+"
    r"h1bbloc:(\d+)"  # capture h1bbloc value
)

# Pattern for [NEW_ORDER_OPEN] — captures the ticket number
# Note: timestamp prefix may appear, match anywhere on line
OPEN_RE = re.compile(
    r"\[NEW_ORDER_OPEN\].*OPEN_TICKET:(\d+).*"
)

# Pattern for [NEW_ORDER_CLOSE] — captures profit and ticket
CLOSE_RE = re.compile(
    r"\[NEW_ORDER_CLOSE\].*TOTAL_PROFIT:([+-]?\d+\.?\d*)"
)

# Also capture ORDERINFO (used when close line is missing)
ORDERINFO_RE = re.compile(
    r"\[ORDERINFO\].*PROFIT:([+-]?\d+\.?\d*)"
)

# Read all lines — handle CRLF properly with readlines()
lines = LOG_FILE.read_text().splitlines()

# Build a map: ticket -> close profit
ticket_close_map: dict[int, float] = {}
for line in lines:
    m = OPEN_RE.search(line)
    if m:
        ticket = int(m.group(1))
        # Skip orders that never close (no matching close found below)
        continue

    m = CLOSE_RE.search(line)
    if m:
        profit = float(m.group(1))
        # Extract ticket from the same line (CLOSE line includes OPEN_TICKET)
        tk_m = re.search(r"OPEN_TICKET:(\d+)", line)
        if tk_m:
            ticket = int(tk_m.group(1))
            ticket_close_map[ticket] = profit

# Build list of entries with their matched outcome
trades: list[dict] = []
entry_seen: dict[int, dict] = {}

for line in lines:
    m = ENTRY_RE.search(line)
    if not m:
        continue

    # Extract values from match groups
    # Groups: 1=dir, 2=entry, 3=sl, 4=tp, 5=rr, 6=m30bbloc(outer), 7=m15(outer), 8=m15 inner,
    #         9=m30(outer), 10=m30 inner
    dir_str = m.group(1)  # "UP" or "DN"
    entry_px = float(m.group(2))  # entry price
    sl_px = float(m.group(3))     # sl value
    tp_px = float(m.group(4))     # tp value
    rr = float(m.group(5))        # rr

    m30bbloc_val = m.group(6)      # e.g. "m30bbloc:7"
    m15_state = m.group(7)         # full "m15:F" or just "F"
    m30_state = m.group(9)         # full "m30:F" or just "F"
    h1bbloc = int(m.group(11))     # h1bbloc value

    ticket = int(re.search(r"OPEN_TICKET:(\d+)", line).group(1))

    # Look up profit from close
    if ticket in ticket_close_map:
        profit = ticket_close_map[ticket]
        outcome = "WIN" if profit > 0 else ("LOSS" if profit < 0 else "NEUTRAL")
    else:
        profit = None
        outcome = "UNMATCHED"

    trade_rec = {
        "datetime": dt,
        "dir": dir_str,
        "entry_px": entry_px,
        "sl": sl_px,
        "tp": tp_px,
        "rr": rr,
        "m30bbloc": m30bbloc,
        "m15_state": m15_state,
        "m30_state": m30_state,
        "h1bbloc": h1bbloc,
        "h4bbloc": h4bbloc,
        "ticket": ticket,
        "profit": profit,
        "outcome": outcome,
    }

    # Track entries we've seen (for duplicate detection)
    entry_seen[ticket] = trade_rec
    trades.append(trade_rec)


# Remove duplicates: keep only the first occurrence per ticket
trades = [t for t in trades if not any(e["ticket"] == t["ticket"] and e is not t for e in trades)]

matched = sum(1 for t in trades if t["profit"] is not None)
unmatched = len(trades) - matched

print(f"\nTotal [TRADE] entries found: {len(trades)}")
print(f"Matched to close: {matched}")
print(f"Unmatched (no close): {unmatched}")


# =============================================================================
# Step 2 — LEVEL 1 grouping (use ONLY logged fields)
# =============================================================================

# Group by m15 state
group_m15: dict[str, list[dict]] = defaultdict(list)
# Group by m30 state
group_m30: dict[str, list[dict]] = defaultdict(list)
# Group by dir
group_dir: dict[str, list[dict]] = defaultdict(list)
# Group by (m15_state, dir)
group_m15_dir: dict[tuple, list[dict]] = defaultdict(list)
# Group by (m30_state, dir)
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

    gp = total_profit - losses  # gross profit (wins only)
    gl = -(total_profit - wins)  # gross loss (absolute value of losses)

    win_rate = wins / len(trade_list) if len(trade_list) > 0 else None
    pf = gp / gl if gl != 0 else None

    return {
        "count": len(trade_list),
        "win_rate": win_rate,
        "total_profit": total_profit,
        "gross_profit": gp,
        "gross_loss": abs(gl),
        "pf": pf,
    }


# =============================================================================
# Step 3 — Report output to markdown file
# =============================================================================

REPORT = LOG_FILE.parent / "TRADE_PNL_BY_SCENARIO.md"

with open(REPORT, "w") as out:
    # Header
    out.write("# REAL TRADE P&L by Fast-Scenario Context (Level 1)\n\n")
    out.write(f"**Source:** Real backtest trades from `{LOG_FILE.name}`\n\n")
    out.write(f"**Date range:** {min(dates)} — {max(dates)}\n\n")

    # Summary
    out.write("## Summary\n\n")
    total = len(trades)
    out.write(f"1. **Total trades:** {total}\n")
    out.write(f"   - Matched (close found): **{matched}**\n")
    out.write(f"   - Unmatched (no close line): **{unmatched}**\n\n")

    overall = stats_for(trades)
    out.write(f"2. **Overall statistics:**\n")
    out.write(f"   - Win-rate: {overall['win_rate']:.1%} ({overall['count']} wins / {overall['count']} total)\n")
    out.write(f"   - Total profit: {overall['total_profit']:+.2f}\n")
    if overall['pf'] is not None and overall['pf'] != 0:
        out.write(f"   - Profit/Factor (PF): {overall['gross_profit']:+.2f} / {overall['gross_loss']:+.2f} = {overall['pf']:.2f}\n")
    else:
        out.write("   - PF: 0 (either no losses or no wins — see notes)\n")
    out.write("\n---\n\n")

    # Level 1 tables
    # By m15 state
    out.write("## 1. Grouped by M15 State\n\n")
    out.write("| M15 State | Count | Win-Rate | Total Profit | PF |")
    out.write("\n|-----------|-------|----------|---------------|-----|")
    for key in sorted(group_m15.keys()):
        s = stats_for(group_m15[key])
        pf_str = f"{s['pf']:.2f}" if s['pf'] is not None else "—"
        out.write(f"\n| {key} | {s['count']} | {s['win_rate']:.1%} | {s['total_profit']:+.2f} | {pf_str} |")
    out.write("\n\n")

    # By m30 state
    out.write("## 2. Grouped by M30 State\n\n")
    out.write("| M30 State | Count | Win-Rate | Total Profit | PF |")
    out.write("\n|-----------|-------|----------|---------------|-----|")
    for key in sorted(group_m30.keys()):
        s = stats_for(group_m30[key])
        pf_str = f"{s['pf']:.2f}" if s['pf'] is not None else "—"
        out.write(f"\n| {key} | {s['count']} | {s['win_rate']:.1%} | {s['total_profit']:+.2f} | {pf_str} |")
    out.write("\n\n")

    # By direction
    out.write("## 3. Grouped by Direction\n\n")
    out.write("| Dir | Count | Win-Rate | Total Profit | PF |")
    out.write("\n|-----|-------|----------|---------------|-----|")
    for d in ("UP", "DN"):
        s = stats_for(group_dir[d])
        pf_str = f"{s['pf']:.2f}" if s['pf'] is not None else "—"
        out.write(f"\n| {d} | {s['count']} | {s['win_rate']:.1%} | {s['total_profit']:+.2f} | {pf_str} |")
    out.write("\n\n")

    # By (M15 state × Dir)
    out.write("## 4. Grouped by (M15 State × Direction)\n\n")
    out.write("| M15 | Dir | Count | Win-Rate | Total Profit | PF |")
    out.write("\n|-----|------|-------|----------|---------------|-----|")
    for (m15, d) in sorted(group_m15_dir.keys()):
        s = stats_for(group_m15_dir[(m15, d)])
        pf_str = f"{s['pf']:.2f}" if s['pf'] is not None else "—"
        out.write(f"\n| {m15} | {d} | {s['count']} | {s['win_rate']:.1%} | {s['total_profit']:+.2f} | {pf_str} |")
    out.write("\n\n")

    # By (M30 state × Dir)
    out.write("## 5. Grouped by (M30 State × Direction)\n\n")
    out.write("| M30 | Dir | Count | Win-Rate | Total Profit | PF |")
    out.write("\n|-----|------|-------|----------|---------------|-----|")
    for (m30, d) in sorted(group_m30_dir.keys()):
        s = stats_for(group_m30_dir[(m30, d)])
        pf_str = f"{s['pf']:.2f}" if s['pf'] is not None else "—"
        out.write(f"\n| {m30} | {d} | {s['count']} | {s['win_rate']:.1%} | {s['total_profit']:+.2f} | {pf_str} |")
    out.write("\n\n")

    # Low-confidence note
    low_conf = [(k, stats_for(group_m15[k])) for k in group_m15 if group_m15[k][0]['count'] < 20]
    if low_conf:
        out.write("## Notes\n\n- **Low-confidence groups** (< 20 trades):")
        for (k, s) in low_conf:
            out.write(f"\n  - `{k}`: {s['count']} trades — win-rate may be unstable")
        out.write("\n\n")

    # Placeholder for Level 2 (structure only)
    out.write("---\n\n")
    out.write("### LEVEL 2 Hook (not implemented yet)\n\n")
    out.write("```python\n")
    out.write("def compute_subscenario(trade):\n")
    out.write("    \"\"\"\n")
    out.write("    TODO Level 2: compute S1/S2/B2/P2 from raw stage/diffBBW/diffMid fields per the\n")
    out.write("    Part 3 sub-state rules, once validated. Not implemented - Level 1 uses logged m15/m30\n")
    out.write("    state only.\n")
    out.write("    \"\"\"\n")
    out.write("    pass\n\n\n")
    out.write("# Usage (after validation of the sub-scenario rules):\n")
    out.write("# for t in trades:\n")
    out.write("#     if t['m15_state'] == 'F':\n")
    out.write("#         ss = compute_subscenario(t)  # would return S1/S2/etc.\n")
    out.write("```\n")

print(f"\nReport written to: {REPORT}")


# =============================================================================
# Step 4 — Print 5 hand-verified sample trades
# =============================================================================

print("\n=== Sample TRADE entries (first 5 matched) ===\n")
for t in trades[:5]:
    if t["outcome"] == "UNMATCHED":
        continue
    print(f"Matched trade: {t['datetime']} | dir={t['dir']} | m15={t['m15_state']} | "
          f"m30={t['m30_state']} | entry={t['entry_px']:.2f} | profit={t['profit']:+.2f} | {t['outcome']}")


# =============================================================================
# End of script
# =============================================================================
