# -*- coding: utf-8 -*-
"""
dm-only Label-Based Strategy (TofySideway + reversal)
Entry/exit keys ONLY on diffMid_Trend (dm). W_stage is NOT used for entry.
FLY_PSHRINK, SHRINK, SQZ exits are REMOVED. Only exits: S_ sideway flag and opposite-dm reversal.

Based on scripts/labelbase_strategy_tofysideway.py
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional

LOG_PATH = Path(r"references/Backtest_data/V36.15/20260712_clean.log")

# Tags we ALLOW: M15, M5, D1, and BBTFImpact (for sideway flag)
TAG_ALLOW = {"[M15]", "[M5]", "[D1]", "[BBTFImpact]"}

# Tags we NEVER parse (BBTFImpact now allowed in TAG_ALLOW)
TAG_IGNORE = {"[TRADE]", "[TRADEINFO]", "[ORDERINFO]", "[DUALTF]",
              "[ATRSL1buf]", "[NEW_ORDER_OPEN]", "[NEW_ORDER_CLOSE]"}

# Regex for M15 line: W_stage, diffMid_Trend, diffBBW — capture cur and prev1 from each list
M15_LINE_RE = re.compile(
    r"^(\d{4}\.\d{2}\.\d{2}[-\s]\d{2}:\d{2}:\d{2})"
    r".*\[M15\]"
    r",.*W_stage_M15:\s*\(([^)]*)\)\[\s*([0-9]+)"
    r".*diffMid_Trend_M15:\s*\[\s*([-]?[\d.]+)"
    r".*diffBBW_M15:\s*\[\s*([-]?[\d.]+),\s*([-]?[\d.]+)"
)

# Regex for M5 line: close_M5 is a list; we take the first (cur = price)
M5_LINE_RE = re.compile(
    r"^(\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2})"
    r".*close_M5:\s*\[\s*([-)?[\d.]+)"
)

# Regex for [BBTFImpact] line: timestamp, then extract Sideway_val
# Format: Sideway_val:[NUM-S_n] where n is the sub-type (e.g., 12)
BBTFIMPACT_LINE_RE = re.compile(
    r"^(\d{4}\.\d{2}\.\d{2}[-\s]\d{2}:\d{2}:\d{2}).*Sideway_val:\s*\[\s*([0-9]+)(?:-S_([0-9]+))?"
)

# Regex for D1 line: timestamp, diffMid_Trend_D1 (first = current value)
# Format: ...[D1], first_stage_D1:[...], W_stage_D1:()[...], diffMid_Trend_D1:[cur, prev1, prev2], ...
# We only care about the FIRST value (current) of diffMid_Trend_D1
D1_LINE_RE = re.compile(
    r"^(\d{4}\.\d{2}\.\d{2}[-\s]\d{2}:\d{2}:\d{2}).*diffMid_Trend_D1:\s*\[\s*([-]?[\d.]+)"
)


def _parse_ts(ts: str) -> datetime:
    """Convert dot-separated timestamp to datetime for arithmetic."""
    return datetime.strptime(ts.replace(".", "-"), "%Y-%m-%d %H:%M:%S")


def parse_log() -> Tuple[List, List, List]:
    """Parse the log file. Returns (m15_data, m5_data, d1_data)."""
    m15_data = []
    m5_data = []
    d1_data = []

    # First pass: collect BBTFImpact data by minute
    sideway_by_minute = {}

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
                ts, ws_stage_str, ws_cur, dm_cur, dbw_cur, dbw_prev1 = m.groups()
                ts_dt = _parse_ts(ts)
                # For empty warmup (), ws_stage_str is empty and ws_cur is "0"
                ws_num = int(ws_cur) if ws_cur else 0
                m15_data.append({
                    "ts": ts_dt,
                    "ts_str": ts,
                    "ws": ws_num,  # W_stage cur (e.g., 511, 522)
                    "dm": float(dm_cur),  # diffMid_Trend cur
                    "dbw": float(dbw_cur),  # diffBBW cur
                    "dbw_prev": float(dbw_prev1),  # diffBBW prev1 (for FLY_PSHRINK rule)
                    "sideway_flag": None,  # will be set from BBTFImpact by minute
                })

            m = M5_LINE_RE.search(raw)
            if m:
                ts, price = m.groups()
                m5_data.append({
                    "ts_str": ts,
                    "price": float(price),
                })

            # Also parse D1 lines (same timestamp as M15 bar)
            d = D1_LINE_RE.search(raw)
            if d:
                ts, dm_d1_cur = d.groups()
                ts_dt = _parse_ts(ts)
                d1_data.append({
                    "ts": ts_dt,
                    "ts_str": ts,
                    "dm": float(dm_d1_cur),  # diffMid_Trend_D1 current value
                })

            # Also parse BBTFImpact lines (same minute as M15 bar)
            b = BBTFIMPACT_LINE_RE.search(raw)
            if b:
                impact_ts_str, impact_val, sideway_sub = b.groups()
                # Normalize timestamp to use hyphens (same format as M15 entries)
                normalized = impact_ts_str.replace(".", "-")
                ts_minute = normalized[:16]  # "YYYY-MM-DD HH:MM"

                # Only keep the S_ flag (sub-type), not the numeric value
                if sideway_sub is not None:
                    sideway_by_minute[ts_minute] = sideway_sub

    # Sort all by timestamp
    m15_data.sort(key=lambda x: x["ts"])
    d1_data.sort(key=lambda x: x["ts"])
    m5_data.sort(key=lambda x: _parse_ts(x["ts_str"]))

    # Fill in sideway flags by matching on minute
    for entry in m15_data:
        ts_minute = entry["ts"].strftime("%Y-%m-%d %H:%M")
        flag = sideway_by_minute.get(ts_minute)
        entry["sideway_flag"] = flag

    return m15_data, m5_data, d1_data


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


# Exit reasons mapping — dm-only: sideway flag and opposite-dm reversal
EXIT_REASON_NAMES = {
    "SIDEWAYS": "SIDEWAYS",
    "REVERSAL_UP": "REVERSAL_UP",
    "REVERSAL_DN": "REVERSAL_DN",
    "FORCED_CLOSE": "FORCED_CLOSE (end of data)",
}


def evaluate_bar(m15: Dict, m5_price: Optional[float], position: Optional[str]) -> Tuple[Optional[str], float]:
    """
    Evaluate ONE M15 bar. Returns (new_position, exit_reason).
    dm-only: entry/exit on diffMid_Trend only; sideway flag closes position;
    reversal closes when dm flips opposite to current direction.
    """
    dm = m15["dm"]

    # RULE 1 — Sideways exit (EA S_ flag), highest priority, only if in a position
    if position != "FLAT":
        if m15.get("sideway_flag") is not None:
            return "FLAT", EXIT_REASON_NAMES["SIDEWAYS"]
        # RULE 2/3 — REVERSAL: opposite dm closes the position
        if position == "LONG" and dm in {2, 4}:  # was long, dm turned down
            return "FLAT", EXIT_REASON_NAMES["REVERSAL_DN"]
        if position == "SHORT" and dm in {1, 5}:  # was short, dm turned up
            return "FLAT", EXIT_REASON_NAMES["REVERSAL_UP"]
        # otherwise hold the position
        return position, None

    # position == FLAT — ENTRIES (RULE 2/3)
    if dm in {1, 5}:
        return "LONG", None
    if dm in {2, 4}:
        return "SHORT", None

    # dm == 3 or 0 -> stay flat
    return position, None


def _format_ledger_row(t, cum_pnl):
    """Format one trade dict into an 8-column ledger row."""
    entry_ts = t["entry_ts"] if t["entry_ts"] else ""
    return f"| {t['ts']} | {entry_ts} | {t['dir']} | {t['entry_px']:.2f} | "            f"{t['ts']} | {t['exit_reason']} | {t['exit_px']:.2f} | {t['pnl']:+.2f} | {cum_pnl:+.2f} |"


def simulate(m15_data: List[Dict], m5_data: List[Dict], d1_data: List[Dict]) -> Tuple[List[Dict], Dict]:
    """
    Run the strategy over the data. Returns (trades, d1_regime_timeline).
    Each trade record has: ts, entry_ts, dir, entry_px, exit_reason, exit_px, pnl, cum_pnl,
    entry_bar_index, exit_bar_index, and now also "entry_d1_regime".
    """
    # Build D1 regime timeline — map from timestamp to regime name
    # dm == 1 -> D1_UP, dm == 2 -> D1_DOWN, dm >= 3 -> D1_SIDEWAYS, dm == 0 -> D1_WARMUP
    d1_regime_timeline: Dict[datetime, str] = {}
    for d in d1_data:
        # A D1 regime starts at d["ts"] and continues until the next D1 line
        dm = d["dm"]
        if dm == 1:
            regime = "D1_UP"
        elif dm == 2:
            regime = "D1_DOWN"
        elif dm >= 3:
            regime = "D1_SIDEWAYS"
        else:  # dm == 0
            regime = "D1_WARMUP"
        d1_regime_timeline[d["ts"]] = regime

    trades = []
    position = "FLAT"
    entry_price = None
    entry_bar_index = None
    bars_in_trade = 0

    for m15_idx, m15 in enumerate(m15_data):
        m5_price = get_nearest_m5_at_or_before(m5_data, m15["ts"])
        if m5_price is None:
            continue

        new_position, exit_reason = evaluate_bar(m15, m5_price, position)

        if exit_reason:
            if position != "FLAT":
                pnl = _compute_pnl(position, entry_price, m5_price)
                exit_bar_index = m15_idx
                bars_held = bars_in_trade
                assert bars_held >= 1, f"bars_held must be >= 1: {bars_held}"
                # Determine D1 regime at entry time — forward-fill from last D1 line
                entry_ts_dt = m15_data[entry_bar_index]["ts"]
                # Find latest D1 timestamp <= entry_ts_dt
                matching_dts = None
                for dts, _ in d1_regime_timeline.items():
                    if dts <= entry_ts_dt:
                        matching_dts = dts
                    else:
                        break
                if matching_dts is not None:
                    entry_regime = d1_regime_timeline[matching_dts]
                else:
                    # No D1 line before this — use the first one (which is WARMUP)
                    entry_regime = d1_regime_timeline[next(iter(d1_regime_timeline))]
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
                    "entry_d1_regime": entry_regime,
                })
            entry_price = None
            position = "FLAT"
            bars_in_trade = 0

        if new_position != position:
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
                entry_price = None
                position = "FLAT"

        if position != "FLAT":
            bars_in_trade += 1

    # Forced close at end of data
    if position != "FLAT" and entry_price is not None:
        exit_bar_index = len(m15_data) - 1
        bars_held = bars_in_trade
        assert bars_held >= 1, f"bars_held must be >= 1: {bars_held}"
        pnl = _compute_pnl(position, entry_price, m5_data[-1]["price"])
        entry_ts_dt = m15_data[entry_bar_index]["ts"]
        # Forward-fill: find latest D1 timestamp <= entry_ts_dt
        matching_dts = None
        for dts, _ in d1_regime_timeline.items():
            if dts <= entry_ts_dt:
                matching_dts = dts
            else:
                break
        if matching_dts is not None:
            entry_regime = d1_regime_timeline[matching_dts]
        else:
            # No D1 line before this — use the first one (which is WARMUP)
            entry_regime = d1_regime_timeline[next(iter(d1_regime_timeline))]
        trades.append({
            "ts": m5_data[-1]["ts_str"],
            "entry_ts": m15_data[entry_bar_index]["ts_str"],
            "dir": position,
            "entry_px": entry_price,
            "exit_reason": EXIT_REASON_NAMES["FORCED_CLOSE"],
            "exit_px": m5_data[-1]["price"],
            "pnl": pnl,
            "cum_pnl": sum(t["pnl"] for t in trades),
            "entry_bar_index": entry_bar_index,
            "exit_bar_index": exit_bar_index,
            "entry_d1_regime": entry_regime,
        })

    return trades, d1_regime_timeline


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


def generate_report(trades: List[Dict], churn_data: Optional[Dict] = None) -> str:
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

    # Build ledger lines
    ledger_lines = []
    cum_pnl = 0.0
    for t in trades:
        cum_pnl += t["pnl"]
        ledger_lines.append(
            f"| {t['ts']} | {t['entry_ts'] or '—'} | {t['dir']} | {t['entry_px']:.2f} | "
            f"{t['ts']} | {t['exit_reason']} | {t['exit_px']:.2f} | {t['pnl']:+.2f} | {cum_pnl:+.2f} |"
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

    for reason, data in sorted(breakdown.items()):
        report += f"- **{reason}**: {data['count']} trades, ${data['pnl']:+.2f} P&L\n"

    report += "\n## Trade Ledger\n\n" + "\n".join(ledger_lines)

    # Append churn analysis if provided
    if churn_data:
        report += "\n\n" + _churn_analysis_markdown(churn_data)

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


def churn_analysis(trades: List[Dict], m15_data: List[Dict]) -> Dict:
    """
    Compute churn metrics for DMONLY report.
    Returns a dict with keys: 'reentry_by_side', 'short_hold_buckets', 'exit_pnl'
    """
    # Build a timeline of M15 bars (ts_str -> ts_dt) for re-entry measurements
    m15_ts_to_idx = {t["ts_str"]: i for i, t in enumerate(m15_data)}

    # Get all exit timestamps and next entry timestamps from SIDEWAYS exits
    sideways_exit_times: List[datetime] = []
    next_entry_times: List[datetime] = []

    for t in trades:
        if t["exit_reason"] == "SIDEWAYS":
            sideways_exit_times.append(_parse_ts(t["ts"]))
        elif t["dir"] != "FLAT" and t["entry_ts"]:
            # This is an entry (not forced close)
            next_entry_times.append(_parse_ts(t["entry_ts"]))

    # Compute re-entry delays in M15 bars
    reentry_counts: Dict[str, int] = {"1": 0, "2": 0, "3-5": 0, "6+": 0}
    reentry_pnl_1bar: float = 0.0
    reentry_pnl_3plus: float = 0.0

    for exit_dt in sideways_exit_times:
        # Find next entry after this exit
        matching_idx = None
        for e in next_entry_times:
            if e > exit_dt:
                matching_idx = e
                break
        if matching_idx is None:
            continue

        delay_bars = 0
        for i in range(1, len(m15_data)):
            bar_ts = m15_data[i]["ts_str"]
            if _parse_ts(bar_ts) > exit_dt:
                delay_bars = i - m15_ts_to_idx[bar_ts]
                break

        key = "1" if delay_bars == 1 else ("2" if delay_bars == 2 else ("3-5" if 3 <= delay_bars <= 5 else "6+"))
        reentry_counts[key] += 1

    # Compute P&L for trades that entered within 1 bar of a SIDEWAYS exit
    # Need to match each sideways exit with its corresponding entry
    for exit_dt in sideways_exit_times:
        # Find the matching entry (same delay logic)
        matching_idx = None
        for e in next_entry_times:
            if e > exit_dt:
                matching_idx = e
                break
        if matching_idx is None:
            continue

        delay_bars = 0
        for i in range(1, len(m15_data)):
            bar_ts = m15_data[i]["ts_str"]
            if _parse_ts(bar_ts) > exit_dt:
                delay_bars = i - m15_ts_to_idx[bar_ts]
                break

        # Find the trade that entered at matching_idx
        for t in trades:
            if t["entry_bar_index"] == matching_idx and t["exit_reason"] != "SIDEWAYS":
                if delay_bars == 1:
                    reentry_pnl_1bar += t["pnl"]
                elif delay_bars >= 3:
                    reentry_pnl_3plus += t["pnl"]
                break

    # B: Short-hold buckets by bars_held
    short_hold_buckets: Dict[str, Dict] = {
        "1": {"count": 0, "wins": 0, "pnl": 0.0},
        "2": {"count": 0, "wins": 0, "pnl": 0.0},
        "3-5": {"count": 0, "wins": 0, "pnl": 0.0},
        "6+": {"count": 0, "wins": 0, "pnl": 0.0},
    }

    for t in trades:
        bars_held = _bars_held(t)
        bucket = "1" if bars_held == 1 else ("2" if bars_held == 2 else ("3-5" if 3 <= bars_held <= 5 else "6+"))
        short_hold_buckets[bucket]["count"] += 1
        short_hold_buckets[bucket]["pnl"] += t["pnl"]
        if t["pnl"] > 0:
            short_hold_buckets[bucket]["wins"] += 1

    # C: Exit reason breakdown (same as in generate_report)
    exit_pnl = {}
    for reason in EXIT_REASON_NAMES.values():
        exit_pnl[reason] = {"count": 0, "wins": 0, "gross_profit": 0.0, "gross_loss": 0.0, "pnl": 0.0}
    for t in trades:
        reason = t["exit_reason"]
        if reason not in exit_pnl:
            # Handle any other reasons that might appear
            exit_pnl[reason] = {"count": 0, "wins": 0, "gross_profit": 0.0, "gross_loss": 0.0, "pnl": 0.0}
        exit_pnl[reason]["count"] += 1
        if t["pnl"] > 0:
            exit_pnl[reason]["wins"] += 1
            exit_pnl[reason]["gross_profit"] += t["pnl"]
        else:
            exit_pnl[reason]["gross_loss"] += abs(t["pnl"])
        exit_pnl[reason]["pnl"] += t["pnl"]

    return {
        "reentry_by_side": reentry_counts,
        "reentry_pnl_1bar": reentry_pnl_1bar,
        "reentry_pnl_3plus": reentry_pnl_3plus,
        "short_hold_buckets": short_hold_buckets,
        "exit_pnl": exit_pnl,
    }


def _churn_analysis_markdown(data: Dict) -> str:
    """Render churn analysis as markdown tables."""
    lines = []

    # Main section header
    lines.append("## Churn Analysis\n")

    # A: Re-entry after SIDEWAYS exits
    lines.append("| Delay (M15 bars) | count |")
    lines.append("|---|---|")
    for key, cnt in data["reentry_by_side"].items():
        lines.append(f"| {key} | {cnt} |")

    lines.append("")
    lines.append("P&L of trades opened after SIDEWAYS exit:\n")
    pnl_1 = data["reentry_pnl_1bar"]
    pnl_3plus = data["reentry_pnl_3plus"]
    total_reentry = pnl_1 + pnl_3plus
    lines.append(f"- Within 1 bar: ${pnl_1:+.2f}")
    lines.append(f"- 3+ bars later: ${pnl_3plus:+.2f}")
    if total_reentry != 0:
        pct = pnl_3plus / abs(total_reentry) * 100
        lines.append(f"  (3+ bars accounts for {pct:.1f}% of total re-entry P&L)")

    # B: Short-hold buckets
    lines.append("\n\n### Short-Hold Trades (by bars held)\n")
    lines.append("| Bars Held | trades | win rate | total P&L | P&L per trade |")
    lines.append("|---|---|---|---|---|")
    for bucket in ["1", "2", "3-5", "6+"]:
        s = data["short_hold_buckets"][bucket]
        pct = s["wins"] / s["count"] if s["count"] else 0.0
        per_trade = s["pnl"] / s["count"] if s["count"] else 0.0
        lines.append(f"| {bucket} | {s['count']} | {pct:.1%} | ${s['pnl']:+.2f} | ${per_trade:+.2f} |")

    # C: Exit reason breakdown
    lines.append("\n\n### P&L by Exit Reason\n")
    lines.append("| Exit Reason | trades | win rate | gross profit | gross loss | total P&L |")
    lines.append("|---|---|---|---|---|---|")
    for reason in sorted(data["exit_pnl"].keys()):
        e = data["exit_pnl"][reason]
        pct = e["wins"] / e["count"] if e["count"] else 0.0
        per_trade = e["pnl"] / e["count"] if e["count"] else 0.0
        lines.append(f"| {reason} | {e['count']} | {pct:.1%} | ${e['gross_profit']:+.2f} | ${e['gross_loss']:+.2f} | ${e['pnl']:+.2f} |")

    return "\n".join(lines)


def main():
    m15_data, m5_data, d1_data = parse_log()

    print(f"M15 lines parsed: {len(m15_data)} (date range: {m15_data[0]['ts_str'][:10]} to {m15_data[-1]['ts_str'][:10]})")
    print(f"M5 lines parsed: {len(m5_data)}")
    print(f"D1 lines parsed: {len(d1_data)} (date range: {d1_data[0]['ts_str'][:10]} to {d1_data[-1]['ts_str'][:10]})")
    print()

    trades, d1_regime_timeline = simulate(m15_data, m5_data, d1_data)

    # Compute churn analysis
    churn_data = churn_analysis(trades, m15_data)

    # Build regime counts and per-regime P&L stats
    regime_counts: Dict[str, int] = {"D1_UP": 0, "D1_DOWN": 0, "D1_SIDEWAYS": 0, "D1_WARMUP": 0}
    regime_trades: Dict[str, List[Dict]] = {r: [] for r in regime_counts.keys()}

    for t in trades:
        regime = t.get("entry_d1_regime", "D1_WARMUP")
        regime_counts[regime] += 1
        regime_trades[regime].append(t)

    # Compute per-regime stats — initialize with defaults for empty regimes
    regime_stats: Dict[str, Dict] = {
        r: {"trades": 0, "wins": 0, "losses": 0, "win_rate": 0.0, "gross_profit": 0.0, "gross_loss": 0.0, "total_pnl": 0.0, "avg_bars_held": 0.0}
        for r in regime_counts
    }
    for r in regime_counts:
        trds = regime_trades[r]
        if trds:
            wins = sum(1 for t in trds if t["pnl"] > 0)
            losses = len(trds) - wins
            gross_p = sum(t["pnl"] for t in trds if t["pnl"] > 0)
            gross_l = abs(sum(t["pnl"] for t in trds if t["pnl"] < 0))
            avg_bars = sum(t.get("bars_held", 1) for t in trds) / len(trds)
            regime_stats[r] = {
                "trades": len(trds),
                "wins": wins,
                "losses": losses,
                "win_rate": wins / len(trds),
                "gross_profit": gross_p,
                "gross_loss": gross_l,
                "total_pnl": gross_p - gross_l,
                "avg_bars_held": avg_bars,
            }

    # Generate the report with churn analysis
    report = generate_report(trades, churn_data)

    # Build the new section
    lines = [
        "\n## P&L by D1 Regime\n",
        "| D1 Regime | trades | win rate | gross profit | gross loss | total P&L | avg bars held |\n",
        "|---|---|---|---|---|---|---|\n",
    ]

    # Order: UP, DOWN, SIDEWAYS, WARMUP, then TOTAL
    ordered = ["D1_UP", "D1_DOWN", "D1_SIDEWAYS", "D1_WARMUP"]
    for r in ordered:
        s = regime_stats.get(r, {})
        lines.append(
            f"| {r} | {s['trades']} | {s['win_rate']:.1%} | ${s['gross_profit']:+.2f} | ${s['gross_loss']:+.2f} | ${s['total_pnl']:+.2f} | {s['avg_bars_held']:.1f} |\n"
        )

    # TOTAL row
    total_trades = len(trades)
    total_wins = sum(s["wins"] for s in regime_stats.values())
    total_gross_p = sum(s["gross_profit"] for s in regime_stats.values())
    total_gross_l = sum(s["gross_loss"] for s in regime_stats.values())
    total_pnl = sum(s["total_pnl"] for s in regime_stats.values())
    lines.append(f"| TOTAL | {total_trades} | — | ${total_gross_p:+.2f} | ${total_gross_l:+.2f} | ${total_pnl:+.2f} | — |\n")

    d1_bar_counts = regime_counts
    largest_regime = max(regime_stats.items(), key=lambda x: abs(x[1]["total_pnl"])) if regime_stats else ("D1_WARMUP", {})
    pct_of_total = (largest_regime[1]["total_pnl"] / total_pnl * 100) if total_pnl and largest_regime[1] else 0.0

    lines.append(f"D1 bars: {d1_bar_counts['D1_UP']} UP | {d1_bar_counts['D1_DOWN']} DOWN | {d1_bar_counts['D1_SIDEWAYS']} SIDEWAYS | {d1_bar_counts['D1_WARMUP']} WARMUP\n")
    lines.append(f"Largest regime P&L: {largest_regime[0]} = ${largest_regime[1]['total_pnl']:+.2f} ({pct_of_total:.1f}% of total)\n")

    report = report.rstrip("\n") + "\n" + "".join(lines)

    print(report)


if __name__ == "__main__":
    main()
