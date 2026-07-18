# -*- coding: utf-8 -*-
"""
Label-Based Strategy P&L Test (no X, no N)
Reads NO trades. Simulates a label-driven strategy on M15/M5 data and reports P&L in DOLLARS.
NO X barrier, NO N horizon — entry and exit are both label-driven; P&L is gross on close_M5, 1 unit, no costs.

Deterministic: two runs produce identical output.
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional

LOG_PATH = Path(r"references/Backtest_data/V36.15/20260712_clean.log")

# Tags we ALLOW: all timeframe tags
TAG_ALLOW = {"[M5]", "[M15]", "[M30]", "[H1]", "[H4]", "[D1]", "[W1]"}

# Tags we NEVER parse (informational, not data)
TAG_IGNORE = {"[TRADE]", "[TRADEINFO]", "[ORDERINFO]", "[DUALTF]",
              "[ATRSL1buf]", "[NEW_ORDER_OPEN]", "[NEW_ORDER_CLOSE]"}

# Regex for M15 line: W_stage, diffMid_Trend, BBUpDn — capture cur from each list
M15_LINE_RE = re.compile(
    r"^(\d{4}\.\d{2}\.\d{2}[-\s]\d{2}:\d{2}:\d{2})"
    r".*\[M15\]"
    r",.*W_stage_M15:\s*\(([^)]*)\)\[\s*([0-9]+)"
    r".*diffMid_Trend_M15:\s*\[\s*([-]?[\d.]+)"
    r",.*BBUpDn_M15:\s*\[\s*([0-9\-]+)"
)

# Regex for M5 line: close_M5 is a list; we take the first (cur = price)
M5_LINE_RE = re.compile(
    r"^(\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2})"
    r".*close_M5:\s*\[\s*([-]?[\d.]+)"
)


def _parse_ts(ts: str) -> datetime:
    """Convert dot-separated timestamp to datetime for arithmetic."""
    return datetime.strptime(ts.replace(".", "-"), "%Y-%m-%d %H:%M:%S")


def parse_log() -> Tuple[List, List]:
    """Parse the log file. Returns (m15_data, m5_data)."""
    m15_data = []
    m5_data = []

    with LOG_PATH.open("r", encoding="utf-8") as f:
        for raw in f:
            # Only consider allowed tags
            if not any(tag in raw for tag in TAG_ALLOW):
                continue
            # Skip ignored tags (safety check)
            if any(tgt in raw for tgt in TAG_IGNORE):
                continue

            m = M15_LINE_RE.search(raw)
            if m:
                ts, ws_stage_str, ws_cur, dm_cur, bbupdn_cur = m.groups()
                ts_dt = _parse_ts(ts)
                # For empty warmup (), ws_stage_str is empty and ws_cur is "0"
                ws_num = int(ws_cur) if ws_cur else 0
                m15_data.append({
                    "ts": ts_dt,
                    "ts_str": ts,
                    "ws": ws_num,  # W_stage cur (e.g., 511, 522)
                    "dm": float(dm_cur),  # diffMid_Trend cur
                    "dbw": 0.0,  # diffBBW not captured in this format — use 0
                    "bbupdn": int(bbupdn_cur) if bbupdn_cur else 0,  # BBUpDn cur
                })

            m = M5_LINE_RE.search(raw)
            if m:
                ts, price = m.groups()
                m5_data.append({
                    "ts_str": ts,
                    "price": float(price),
                })

    # Sort both by timestamp
    m15_data.sort(key=lambda x: x["ts"])
    m5_data.sort(key=lambda x: _parse_ts(x["ts_str"]))

    return m15_data, m5_data


def get_nearest_m5_at_or_before(m5_list: List[Dict], target_dt: datetime) -> Optional[float]:
    """
    Return the close_M5 price from the NEAREST M5 line AT OR BEFORE T.
    Scans forward and keeps updating; breaks ONLY when ts > target.
    (This is the LAST-match, not the FIRST-match.)
    """
    nearest_price = None
    # Convert target to dot format for comparison with stored ts_str
    target_str = target_dt.strftime("%Y.%m.%d %H:%M:%S")
    for entry in m5_list:
        if entry["ts_str"] <= target_str:
            nearest_price = entry["price"]
        else:
            break
    return nearest_price


# Exit reasons mapping
EXIT_REASON_NAMES = {
    "SIDEWAYS": "SIDEWAYS",
    "FLY_PSHRINK": "FLY_PSHRINK",
    "SHRINK": "SHRINK",
    "SQZ": "SQZ",
    "REVERSAL": "REVERSAL (BUY->SELL or SELL->BUY)",
}


def evaluate_bar(m15: Dict, m5_price: Optional[float], position: Optional[str]) -> Tuple[Optional[str], float]:
    """
    Evaluate ONE M15 bar. Returns (new_position, exit_reason).
    new_position is one of: "LONG", "SHORT", "FLAT" (or None if flat and no entry).
    exit_reason is one of the EXIT_REASON_NAMES values or None (no exit).
    """
    ws = m15["ws"]
    dm = m15["dm"]
    dbw = m15["dbw"]

    # Exit conditions (priority 1-4) — only when we have an active position
    if position != "FLAT":
        if dm >= 3:
            return "FLAT", EXIT_REASON_NAMES["SIDEWAYS"]
        if ws in {512, 522} and dbw < 0 and (m15.get("dbw_prev", 0) < 0):
            return "FLAT", EXIT_REASON_NAMES["FLY_PSHRINK"]
        if ws in {513, 523} and dm in {2, 4}:
            return "FLAT", EXIT_REASON_NAMES["SHRINK"]
        if (400 <= ws <= 499) or dm == 3:
            return "FLAT", EXIT_REASON_NAMES["SQZ"]

    # Entry conditions (priority 5-6) — only apply when flat and no entry pending
    if position == "FLAT" and m15.get("entry_pending") != True:
        if ws in {511, 512} and dm in {1, 5}:
            return "LONG", None
        if ws in {521, 522} and dm in {2, 4}:
            return "SHORT", None

    # Otherwise hold
    return position, None


def simulate(m15_data: List[Dict], m5_data: List[Dict]) -> List[Dict]:
    """
    Run the strategy over the data. Returns a list of trade records.
    Each record has: ts, entry_price, exit_reason, exit_price, pnl, cum_pnl, direction,
    entry_bar_index, exit_bar_index (for bars_held calculation).
    """
    trades = []
    position = "FLAT"  # Current position
    entry_price = None
    entry_bar_index = None  # Track the bar where we entered
    bars_in_trade = 0  # Count bars held while in position

    for m15_idx, m15 in enumerate(m15_data):
        # Get nearest M5 price at or before this M15 bar
        m5_price = get_nearest_m5_at_or_before(m5_data, m15["ts"])
        if m5_price is None:
            continue

        new_position, exit_reason = evaluate_bar(m15, m5_price, position)

        if exit_reason:
            # EXIT ALL — close any existing position
            if position != "FLAT":
                pnl = _compute_pnl(position, entry_price, m5_price)
                exit_bar_index = m15_idx
                bars_held = bars_in_trade
                assert bars_held >= 1, f"bars_held must be >= 1: {bars_held}"
                trades.append({
                    "ts": m15["ts_str"],
                    "entry_ts": m15_data[entry_bar_index]["ts_str"],
                    "dir": position,
                    "entry_px": entry_price,
                    "exit_reason": exit_reason,
                    "exit_px": m5_price,
                    "pnl": pnl,
                    "cum_pnl": sum(t["pnl"] for t in trades),
                    "entry_bar_index": entry_bar_index,
                    "exit_bar_index": exit_bar_index,
                })
            entry_price = None
            position = "FLAT"
            bars_in_trade = 0

        if new_position != position:
            # Position changed — this is an ENTRY
            if position == "FLAT" and new_position == "LONG":
                entry_price = m5_price
                position = "LONG"
                entry_bar_index = m15_idx
                bars_in_trade = 0
            elif position == "FLAT" and new_position == "SHORT":
                entry_price = m5_price
                position = "SHORT"
                entry_bar_index = m15_idx
                bars_in_trade = 0
            elif position != "FLAT" and new_position == "FLAT":
                # This shouldn't happen after we already exited; but handle it
                entry_price = None
                position = "FLAT"

        # Increment bars held while in position
        if position != "FLAT":
            bars_in_trade += 1

    # Forced close at end of data
    if position != "FLAT" and entry_price is not None:
        exit_bar_index = len(m15_data) - 1
        bars_held = bars_in_trade
        assert bars_held >= 1, f"bars_held must be >= 1: {bars_held}"
        pnl = _compute_pnl(position, entry_price, m5_data[-1]["price"])
        trades.append({
            "ts": m5_data[-1]["ts_str"],
            "entry_ts": m15_data[entry_bar_index]["ts_str"],
            "dir": position,
            "entry_px": entry_price,
            "exit_reason": EXIT_REASON_NAMES["REVERSAL"],
            "exit_px": m5_data[-1]["price"],
            "pnl": pnl,
            "cum_pnl": sum(t["pnl"] for t in trades),
            "entry_bar_index": entry_bar_index,
            "exit_bar_index": exit_bar_index,
        })

    return trades


def _compute_pnl(position: str, entry: float, exit_: float) -> float:
    """Compute P&L for 1 unit."""
    if position == "LONG":
        return exit_ - entry
    elif position == "SHORT":
        return entry - exit_
    else:
        return 0.0


def entry_price_dt_str(price: float) -> str:
    """Convert entry price back to timestamp string (approximate)."""
    # This is a rough approximation; we'll just use the M15 timestamp where entry occurred.
    # In practice, we store this in the trade record separately.
    return ""


def _bars_held(t: Dict) -> int:
    """Compute bars held using stored entry_bar_index and exit_bar_index."""
    # assert t.get("entry_bar_index") is not None, "Missing entry_bar_index"
    # assert t.get("exit_bar_index") is not None, "Missing exit_bar_index"
    return max(1, t["exit_bar_index"] - t["entry_bar_index"])


def generate_report(trades: List[Dict], m15_data: List[Dict], m5_data: List[Dict]) -> str:
    """Generate the markdown report."""
    total_trades = len(trades)
    long_count = sum(1 for t in trades if t["dir"] == "LONG")
    short_count = sum(1 for t in trades if t["dir"] == "SHORT")
    forced_close_count = sum(1 for t in trades if t["exit_reason"] == "REVERSAL")

    win_count = sum(1 for t in trades if t["pnl"] > 0)
    loss_count = sum(1 for t in trades if t["pnl"] < 0)
    gross_profit = sum(t["pnl"] for t in trades if t["pnl"] > 0)
    gross_loss = abs(sum(t["pnl"] for t in trades if t["pnl"] < 0))
    win_rate = win_count / total_trades if total_trades else 0.0
    pnl_freq = gross_profit / (gross_profit + gross_loss) if (gross_profit + gross_loss) else 0.0

    avg_bars = _avg_bars_held(trades)
    # For bars held, we need to estimate from timestamps — simplified
    median_bars = _median_bars_held(trades)
    short_2_bars = sum(1 for t in trades if _bars_held(t) < 2)

    # Breakdown by exit reason
    breakdown = {}
    for reason in EXIT_REASON_NAMES.values():
        breakdown[reason] = {"count": 0, "pnl": 0.0}
    for t in trades:
        break_reason = t["exit_reason"]
        if break_reason not in breakdown:
            breakdown[break_reason] = {"count": 0, "pnl": 0.0}
        breakdown[break_reason]["count"] += 1
        breakdown[break_reason]["pnl"] += t["pnl"]

    # Build ledger lines with entry reason (rule + fields at entry bar) and exit reason (rule + fields at exit bar)
    ledger_lines = []
    cum_pnl = 0.0
    for t in trades:
        cum_pnl += t["pnl"]

        # Get entry bar data to extract ws, dm, dbw, bbupdn for the entry reason
        entry_bar = m15_data[t["entry_bar_index"]]
        entry_ws = entry_bar["ws"]
        entry_dm = entry_bar["dm"]
        entry_dbw = entry_bar["dbw"]
        entry_bbupdn = entry_bar.get("bbupdn", 0)  # bbupdn not captured in original parse; use 0 as default

        # Determine entry reason name based on W_stage and dm (same logic as entry)
        if entry_ws in (511, 521):
            if entry_dm == 1.0:
                entry_reason_name = "FLY_UP"
            elif entry_dm == 5.0:
                entry_reason_name = "SHRK_UP"
            else:
                entry_reason_name = f"W{entry_ws}_UP"
        elif entry_ws in (512, 522):
            if entry_dm == 1.0:
                entry_reason_name = "SQZ_UP"
            elif entry_dm == 5.0:
                entry_reason_name = "SHRK_UP"
            else:
                entry_reason_name = f"W{entry_ws}_UP"
        else:
            entry_reason_name = f"W{entry_ws}_UP"

        # Build entry reason field string
        entry_re = f"{entry_reason_name} [M15]: ws={entry_ws} dm={entry_dm:.1f} dbw={entry_dbw:+.2f} bbupdn={entry_bbupdn}"
        entry_dt = t["entry_ts"] or "—"

        # Get exit bar data for the exit reason
        exit_bar = m15_data[t["exit_bar_index"]]
        exit_ws = exit_bar["ws"]
        exit_dm = exit_bar["dm"]
        exit_dbw = exit_bar["dbw"]
        exit_bbupdn = exit_bar.get("bbupdn", 0)  # bbupdn not captured in original parse; use 0 as default

        # Exit reason is just the rule name (no field values needed per requirements)
        exit_re = f"{t['exit_reason']} [M15]: ws={exit_ws} dm={exit_dm:.1f} dbw={exit_dbw:+.2f} bbupdn={exit_bbupdn}"
        exit_dt = t["ts"]

        ledger_lines.append(
            f"| {t['entry_bar_index'] + 1} | {t['entry_bar_index'] + 1} | {entry_dt} | {t['dir']} | "
            f"{entry_re} | {t['entry_px']:.2f} | {exit_dt} | {exit_re} | "
            f"{t['exit_px']:.2f} | {t['pnl']:+.2f} | {cum_pnl:+.2f} |"
        )

    report = (
        "# Label-Based Strategy P&L Report\n\n"
        "## Provenance\n"
        f"`python scripts/labelbase_strategy.py` / input log / generated UTC\n"
        "NO X barrier, NO N horizon — entry and exit are both label-driven; P&L is gross on close_M5, 1 unit, no costs.\n\n"

        "## Summary\n"
        f"- **Total trades**: {total_trades}\n"
        f"- **LONG**: {long_count} | **SHORT**: {short_count} | **Forced-close (reversal)**: {forced_close_count}\n"
        f"- **Win count**: {win_count} / {total_trades} = {win_rate:.1%}\n"
        f"- **Gross profit**: ${gross_profit:+.2f}\n"
        f"- **Gross loss**: ${gross_loss:-.2f}\n"
        f"- **PF (profit/loss frequency)**: {pnl_freq:.1%}\n"
        f"- **Total P&L**: **${cum_pnl:+.2f}**\n\n"

        "## Trade Statistics\n"
        f"- Average bars held: {avg_bars:.1f}\n"
        f"- Median bars held: {median_bars}\n"
        f"- Trades held < 2 M15 bars: {short_2_bars}\n\n"

        "## Exit Reasons\n"
    )

    for reason, data in sorted(breakdown.items()):
        report += f"- **{reason}**: {data['count']} trades, ${data['pnl']:+.2f} P&L\n"

    # --- Uncovered bars calculation (using evaluate_bar like the simulation) ---
    # A bar is "matched" if evaluate_bar triggers an entry or exit.
    # We must track running state (position) like simulate() does to avoid
    # counting consecutive identical bars multiple times.
    sim_position = "FLAT"
    matched_ts_set = set()
    for bar in m15_data:
        price = get_nearest_m5_at_or_before(m5_data, bar["ts"])
        new_pos, exit_reason = evaluate_bar(bar, price, sim_position)

        # Matched if we got an entry (new_pos != "FLAT") or an exit reason
        if new_pos != sim_position or exit_reason is not None:
            matched_ts_set.add(bar["ts_str"])
            sim_position = new_pos

    covered_count = len(matched_ts_set)
    uncovered_count = len(m15_data) - covered_count
    uncovered_pct = (uncovered_count / len(m15_data) * 100) if m15_data else 0.0

    # Group uncovered bars by (ws, dm) combo — skip any that would be entries/exits
    uncovered_by_combo: Dict[Tuple[int, float], List[Dict]] = {}
    for bar in m15_data:
        if bar["ts_str"] not in matched_ts_set:
            combo = (bar["ws"], bar["dm"])
            if combo not in uncovered_by_combo:
                uncovered_by_combo[combo] = []
            uncovered_by_combo[combo].append(bar)

    # Build summary rows for the uncovered table
    combo_summary = []
    for (ws, dm), bars in sorted(uncovered_by_combo.items(), key=lambda x: len(x[1]), reverse=True):
        n = len(bars)
        combo_summary.append({"ws": ws, "dm": dm, "n": n})

    report = (
        "# Label-Based Strategy P&L Report\n\n"
        "## Provenance\n"
        f"`python scripts/labelbase_strategy.py` / input log / generated UTC\n"
        "NO X barrier, NO N horizon — entry and exit are both label-driven; P&L is gross on close_M5, 1 unit, no costs.\n\n"

        "## Summary\n"
        f"- **Total trades**: {total_trades}\n"
        f"- **LONG**: {long_count} | **SHORT**: {short_count} | **Forced-close (reversal)**: {forced_close_count}\n"
        f"- **Win count**: {win_count} / {total_trades} = {win_rate:.1%}\n"
        f"- **Gross profit**: ${gross_profit:+.2f}\n"
        f"- **Gross loss**: ${gross_loss:-.2f}\n"
        f"- **PF (profit/loss frequency)**: {pnl_freq:.1%}\n"
        f"- **Total P&L**: **${cum_pnl:+.2f}**\n\n"

        "## Trade Statistics\n"
        f"- Average bars held: {avg_bars:.1f}\n"
        f"- Median bars held: {median_bars}\n"
        f"- Trades held < 2 M15 bars: {short_2_bars}\n\n"

        "## Exit Reasons\n"
    )

    for reason, data in sorted(breakdown.items()):
        report += f"- **{reason}**: {data['count']} trades, ${data['pnl']:+.2f} P&L\n"

    report += f"\n## Uncovered Bars — matched no rule ({uncovered_count} bars, {uncovered_pct:.1f}%)\n\n"
    if combo_summary:
        report += "### Summary by W_stage / diffMid_Trend\n\n"
        for cs in combo_summary:
            report += f"- **{cs['ws']} / {cs['dm']:.1f}**: {cs['n']} bars\n"

    report += "\n## Trade Ledger\n\n"
    report += "| # | trade number | entry dt | dir | entry reason | entry px | exit dt | exit reason | exit px | P&L | Cum P&L |\n"
    report += "|---|--------------|----------|-----|---------------|----------|---------|-------------|---------|------|-------|\n"
    report += "\n".join(ledger_lines)

    return report


def _avg_bars_held(trades: List[Dict]) -> float:
    """Compute average bars held from stored counters."""
    if not trades:
        return 0.0
    total = sum(t["exit_bar_index"] - t["entry_bar_index"] for t in trades)
    return total / len(trades)


def _median_bars_held(trades: List[Dict]) -> int:
    """Compute median bars held from actual counts."""
    if not trades:
        return 0
    bars_list = [t["exit_bar_index"] - t["entry_bar_index"] for t in trades]
    bars_list.sort()
    n = len(bars_list)
    if n % 2 == 1:
        return bars_list[n // 2]
    else:
        return (bars_list[n // 2 - 1] + bars_list[n // 2]) // 2


def main():
    m15_data, m5_data = parse_log()

 
    print(f"M15 lines parsed: {len(m15_data)} (date range: {m15_data[0]['ts_str'][:10]} to {m15_data[-1]['ts_str'][:10]})")
    print(f"M5 lines parsed: {len(m5_data)}")
    print()

    trades = simulate(m15_data, m5_data)

    report = generate_report(trades, m15_data, m5_data)
    print(report)


if __name__ == "__main__":
    main()
