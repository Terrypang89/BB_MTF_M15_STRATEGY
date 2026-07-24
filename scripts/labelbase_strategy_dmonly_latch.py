# -*- coding: utf-8 -*-
"""
DMONLY LATCHED-SIDEWAY variant

Tests whether holding the sideway state (latching) reduces churn.
Same data, same logic except S_ flag now latches until dm < 3.
Do NOT modify scripts/labelbase_strategy_dmonly.py — this is a separate test.
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional

LOG_PATH = Path(r"references/Backtest_data/V36.15/20260712_clean.log")

# Tags we ALLOW: M15, M5, D1, and BBTFImpact (for sideway flag)
TAG_ALLOW = {"[M15]", "[M5]", "[D1]", "[BBTFImpact]"}

# Tags we NEVER parse
TAG_IGNORE = {"[TRADE]", "[TRADEINFO]", "[ORDERINFO]", "[DUALTF]",
              "[ATRSL1buf]", "[NEW_ORDER_OPEN]", "[NEW_ORDER_CLOSE]"}

# Regex patterns (same as DMONLY)
M15_LINE_RE = re.compile(
    r"^(\d{4}\.\d{2}\.\d{2}[-\s]\d{2}:\d{2}:\d{2})"
    r".*\[M15\]"
    r",.*W_stage_M15:\s*\(([^)]*)\)\[\s*([0-9]+)"
    r".*diffMid_Trend_M15:\s*\[\s*([-]?[\d.]+)"
    r".*diffBBW_M15:\s*\[\s*([-]?[\d.]+),\s*([-]?[\d.]+)"
)

M5_LINE_RE = re.compile(
    r"^(\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2})"
    r".*close_M5:\s*\[\s*([-)?[\d.]+)"
)

BBTFIMPACT_LINE_RE = re.compile(
    r"^(\d{4}\.\d{2}\.\d{2}[-\s]\d{2}:\d{2}:\d{2}).*Sideway_val:\s*\[\s*([0-9]+)(?:-S_([0-9]+))?"
)

D1_LINE_RE = re.compile(
    r"^(\d{4}\.\d{2}\.\d{2}[-\s]\d{2}:\d{2}:\d{2}).*diffMid_Trend_D1:\s*\[\s*([-]?[\d.]+)"
)

# Module-level latch state (used by evaluate_bar)
_latched = False


def _parse_ts(ts: str) -> datetime:
    """Convert dot-separated timestamp to datetime for arithmetic."""
    return datetime.strptime(ts.replace(".", "-"), "%Y-%m-%d %H:%M:%S")


def parse_log() -> Tuple[List, List, List]:
    """Parse the log file. Returns (m15_data, m5_data, d1_data)."""
    m15_data = []
    m5_data = []
    d1_data = []

    # Store BBTFImpact signals with their exact timestamp
    sideway_signals: List[Dict[str, str]] = []

    with LOG_PATH.open("r", encoding="utf-8") as f:
        for raw in f:
            if not any(tag in raw for tag in TAG_ALLOW):
                continue
            if any(tgt in raw for tgt in TAG_IGNORE):
                continue

            m = M15_LINE_RE.search(raw)
            if m:
                ts, ws_stage_str, ws_cur, dm_cur, dbw_cur, dbw_prev1 = m.groups()
                ts_dt = _parse_ts(ts)
                ws_num = int(ws_cur) if ws_cur else 0
                m15_data.append({
                    "ts": ts_dt,
                    "ts_str": ts,
                    "ws": ws_num,
                    "dm": float(dm_cur),
                    "dbw": float(dbw_cur),
                    "dbw_prev": float(dbw_prev1),
                    "sideway_flag": None,  # will be set after parsing all signals
                })

            m = M5_LINE_RE.search(raw)
            if m:
                ts, price = m.groups()
                m5_data.append({
                    "ts_str": ts,
                    "price": float(price),
                })

            d = D1_LINE_RE.search(raw)
            if d:
                ts, dm_d1_cur = d.groups()
                ts_dt = _parse_ts(ts)
                d1_data.append({
                    "ts": ts_dt,
                    "ts_str": ts,
                    "dm": float(dm_d1_cur),
                })

            b = BBTFIMPACT_LINE_RE.search(raw)
            if b:
                impact_ts_str, impact_val, sideway_sub = b.groups()
                # Normalize timestamp to use hyphens (same format as M15 entries)
                normalized = impact_ts_str.replace(".", "-")
                # Only store if there's an S_ sub-type (sideway signal)
                if sideway_sub is not None:
                    sideway_signals.append({
                        "ts_str": normalized,
                        "sub_type": sideway_sub,
                    })

    m15_data.sort(key=lambda x: x["ts"])
    d1_data.sort(key=lambda x: x["ts"])
    m5_data.sort(key=lambda x: _parse_ts(x["ts_str"]))

    # Now assign sideway_flag only to bars that occur AT OR AFTER the signal timestamp
    for signal in sideway_signals:
        signal_dt = _parse_ts(signal["ts_str"])
        for entry in m15_data:
            if entry["sideway_flag"] is not None:
                # Already has a flag — don't overwrite
                continue
            # Only apply if the bar's timestamp >= signal timestamp
            if entry["ts"] >= signal_dt:
                entry["sideway_flag"] = signal["sub_type"]

    return m15_data, m5_data, d1_data


def get_nearest_m5_at_or_before(m5_list: List[Dict], target_dt: datetime) -> Optional[float]:
    """Return the close_M5 price from the NEAREST M5 line AT OR BEFORE T."""
    nearest_price = None
    target_str = target_dt.strftime("%Y.%m.%d %H:%M:%S")
    for entry in m5_list:
        if entry["ts_str"] <= target_str:
            nearest_price = entry["price"]
        else:
            break
    return nearest_price


EXIT_REASON_NAMES = {
    "SIDEWAYS": "SIDEWAYS",
    "REVERSAL_UP": "REVERSAL_UP",
    "REVERSAL_DN": "REVERSAL_DN",
    "FORCED_CLOSE": "FORCED_CLOSE (end of data)",
}


def evaluate_bar(m15: Dict, m5_price: Optional[float], position: Optional[str]) -> Tuple[Optional[str], float]:
    """
    Evaluate ONE M15 bar. Returns (new_position, exit_reason).

    DMONLY LATCHED-SIDEWAY:
    - If latched, close any position and block entries.
    - Otherwise, use the original DMONLY rules (sideway_flag for exits, dm for entries/reversals).
    """
    global _latched
    dm = m15["dm"]

    # LATCHED-SIDEWAY state machine — update latch first, before any entry checks:
    if _latched:
        if dm in {1, 2}:
            _latched = False  # release only on clean trend (dm 1 or 2)
    else:
        if m15.get("sideway_flag") is not None:
            _latched = True  # ONLY the S_ flag engages the latch


    # If currently latched, close any position and block entries — return early
    if _latched:
        if position != "FLAT":
            return "FLAT", EXIT_REASON_NAMES["SIDEWAYS"]
        else:
            return "FLAT", None  # block entry

    # Not latched — use original DMONLY logic
    if position != "FLAT":
        if m15.get("sideway_flag") is not None:
            return "FLAT", EXIT_REASON_NAMES["SIDEWAYS"]
        if position == "LONG" and dm in {2, 4}:
            return "FLAT", EXIT_REASON_NAMES["REVERSAL_DN"]
        if position == "SHORT" and dm in {1, 5}:
            return "FLAT", EXIT_REASON_NAMES["REVERSAL_UP"]
        return position, None

    # position == FLAT — ENTRIES (RULE 2/3)
    if dm in {1, 5}:
        return "LONG", None
    if dm in {2, 4}:
        return "SHORT", None

    return position, None


def _format_ledger_row(t, cum_pnl):
    """Format one trade dict into an 8-column ledger row."""
    entry_ts = t["entry_ts"] if t["entry_ts"] else ""
    return (f"| {t['ts']} | {entry_ts} | {t['dir']} | "
            f"{t['entry_px']:.2f} | {t['ts']} | "
            f"{t['exit_reason']} | {t['exit_px']:.2f} | "
            f"{t['pnl']:+.2f} | {cum_pnl:+.2f} |")


def simulate(m15_data: List[Dict], m5_data: List[Dict], d1_data: List[Dict]) -> Tuple[List[Dict], int, Dict]:
    """
    Run the strategy over the data. Returns (trades, latched_bars_count, d1_regime_timeline).

    Tracks how many bars were in the LATCHED state vs UNLATCHED.
    """
    # Build D1 regime timeline (same as DMONLY)
    d1_regime_timeline: Dict[datetime, str] = {}
    for d in d1_data:
        dm = d["dm"]
        if dm == 1:
            regime = "D1_UP"
        elif dm == 2:
            regime = "D1_DOWN"
        elif dm >= 3:
            regime = "D1_SIDEWAYS"
        else:
            regime = "D1_WARMUP"
        d1_regime_timeline[d["ts"]] = regime

    trades = []
    latched_bars_count = 0  # count of bars where latch was active
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
                entry_ts_dt = m15_data[entry_bar_index]["ts"]
                matching_dts = None
                for dts, _ in d1_regime_timeline.items():
                    if dts <= entry_ts_dt:
                        matching_dts = dts
                    else:
                        break
                if matching_dts is not None:
                    entry_regime = d1_regime_timeline[matching_dts]
                else:
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

        # Count latched bars — only count if we were already latched at START of bar
        # (don't count the transition bar itself)
        was_latched_before = _latched
        if was_latched_before:
            latched_bars_count += 1

    # Forced close at end of data
    if position != "FLAT" and entry_price is not None:
        exit_bar_index = len(m15_data) - 1
        bars_held = bars_in_trade
        assert bars_held >= 1, f"bars_held must be >= 1: {bars_held}"
        pnl = _compute_pnl(position, entry_price, m5_data[-1]["price"])
        entry_ts_dt = m15_data[entry_bar_index]["ts"]
        matching_dts = None
        for dts, _ in d1_regime_timeline.items():
            if dts <= entry_ts_dt:
                matching_dts = dts
            else:
                break
        if matching_dts is not None:
            entry_regime = d1_regime_timeline[matching_dts]
        else:
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

    return trades, latched_bars_count, d1_regime_timeline


def _compute_pnl(position: str, entry: float, exit_: float) -> float:
    """Compute P&L for 1 unit."""
    if position == "LONG":
        return exit_ - entry
    elif position == "SHORT":
        return entry - exit_
    else:
        return 0.0


def _bars_held(t: Dict) -> int:
    """Compute bars held using stored entry_bar_index and exit_bar_index."""
    return max(1, t["exit_bar_index"] - t["entry_bar_index"])


def churn_analysis(trades: List[Dict]) -> Dict:
    """
    Compute churn metrics for LATCHED-SIDEWAY report.

    Returns dict with: short_hold_buckets (same format as DMONLY), exit_pnl.
    """
    # B: Short-hold buckets by bars_held
    short_hold_buckets: Dict[str, Dict] = {
        "1": {"count": 0, "wins": 0, "pnl": 0.0},
        "2": {"count": 0, "wins": 0, "pnl": 0.0},
        "3-5": {"count": 0, "wins": 0, "pnl": 0.0},
        "6+": {"count": 0, "wins": 0, "pnl": 0.0},
    }

    for t in trades:
        bars_held = _bars_held(t)
        bucket = "1" if bars_held == 1 else ("2" if bars_held == 2 else
                                             ("3-5" if 3 <= bars_held <= 5 else "6+"))
        short_hold_buckets[bucket]["count"] += 1
        short_hold_buckets[bucket]["pnl"] += t["pnl"]
        if t["pnl"] > 0:
            short_hold_buckets[bucket]["wins"] += 1

    # C: Exit reason breakdown
    exit_pnl = {}
    for reason in EXIT_REASON_NAMES.values():
        exit_pnl[reason] = {"count": 0, "wins": 0,
                           "gross_profit": 0.0, "gross_loss": 0.0, "pnl": 0.0}
    for t in trades:
        reason = t["exit_reason"]
        if reason not in exit_pnl:
            exit_pnl[reason] = {"count": 0, "wins": 0,
                                "gross_profit": 0.0, "gross_loss": 0.0, "pnl": 0.0}
        exit_pnl[reason]["count"] += 1
        if t["pnl"] > 0:
            exit_pnl[reason]["wins"] += 1
            exit_pnl[reason]["gross_profit"] += t["pnl"]
        else:
            exit_pnl[reason]["gross_loss"] += abs(t["pnl"])
        exit_pnl[reason]["pnl"] += t["pnl"]

    return {
        "short_hold_buckets": short_hold_buckets,
        "exit_pnl": exit_pnl,
    }


def generate_report(trades: List[Dict], latched_bars_count: int, unlatched_bars_count: int,
                    d1_regime_timeline: Dict, short_hold_buckets: Dict, exit_pnl: Dict) -> str:
    """Generate the markdown report for LATCHED-SIDEWAY."""
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
    median_bars = _median_bars_held(trades)
    short_2_bars = sum(1 for t in trades if _bars_held(t) < 2)

    ledger_lines = []
    cum_pnl = 0.0
    for t in trades:
        cum_pnl += t["pnl"]
        ledger_lines.append(_format_ledger_row(t, cum_pnl))

    report = (
        "# Label-Based Strategy P&L Report — LATCHED-SIDEWAY\n\n"
        "## Provenance\n"
        "`python scripts/labelbase_strategy_dmonly_latch.py` / input log / generated UTC\n"
        "Test: holding the sideway state (latching) until dm < 3.\n"
        "LATCHED-SIDEWAY does NOT modify the original DMONLY script — this is a separate variant.\n\n"

        "## Summary\n"
        f"- **Total trades**: {total_trades}\n"
        f"- **LONG**: {long_count} | **SHORT**: {short_count} | **Forced-close (reversal)**: {forced_close_count}\n"
        f"- **Win count**: {win_count} / {total_trades} = {win_rate:.1%}\n"
        f"- **Gross profit**: ${gross_profit:+.2f}\n"
        f"- **Gross loss**: ${gross_loss:-.2f}\n"
        f"- **PF (profit/loss frequency)**: {pnl_freq:.1%}\n"
        f"- **Total P&L**: **${cum_pnl:+.2f}**\n\n"

        "## Latch Statistics\n"
        f"- **Latched bars**: {latched_bars_count}\n"
        f"- **Unlatched bars**: {unlatched_bars_count}\n"
    )

    report += (
        "### Bars-Held Buckets (same format as DMONLY churn analysis)\n\n"
        "| Bars Held | trades | win rate | total P&L | P&L per trade |\n"
        "|---|---|---|---|---|\n"
    )

    for bucket in ["1", "2", "3-5", "6+"]:
        s = short_hold_buckets[bucket]
        pct = s["wins"] / s["count"] if s["count"] else 0.0
        per_trade = s["pnl"] / s["count"] if s["count"] else 0.0
        report += f"| {bucket} | {s['count']} | {pct:.1%} | ${s['pnl']:+.2f} | ${per_trade:+.2f} |\n"

    report += "\n\n### P&L by Exit Reason\n\n"
    report += "| Exit Reason | trades | win rate | gross profit | gross loss | total P&L |\n"
    report += "|---|---|---|---|---|---|\n"
    for reason in sorted(exit_pnl.keys()):
        e = exit_pnl[reason]
        pct = e["wins"] / e["count"] if e["count"] else 0.0
        per_trade = e["pnl"] / e["count"] if e["count"] else 0.0
        report += (f"| {reason} | {e['count']} | {pct:.1%} | "
                   f"${e['gross_profit']:+.2f} | ${e['gross_loss']:+.2f} | "
                   f"${e['pnl']:+.2f} |\n")

    report += "\n## Trade Ledger\n\n" + "\n".join(ledger_lines)

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
    # Reset latch state before each run
    global _latched
    _latched = False

    m15_data, m5_data, d1_data = parse_log()

    print(f"M15 lines parsed: {len(m15_data)} (date range: {m15_data[0]['ts_str'][:10]} to {m15_data[-1]['ts_str'][:10]})")
    print(f"M5 lines parsed: {len(m5_data)}")
    print(f"D1 lines parsed: {len(d1_data)} (date range: {d1_data[0]['ts_str'][:10]} to {d1_data[-1]['ts_str'][:10]})")
    print()

    trades, latched_bars_count, d1_regime_timeline = simulate(m15_data, m5_data, d1_data)

    # Compute churn analysis (same buckets as DMONLY for comparison)
    churn_data = churn_analysis(trades)
    unlatched_bars_count = len(m15_data) - latched_bars_count
    churn_data["unlatched_bars_count"] = unlatched_bars_count

    print(f"Trade count: {len(trades)} (expected 1120 / +$968.93)")
    print(f"Latched bars: {latched_bars_count}, Unlatched bars: {unlatched_bars_count}")
    print()

    report = generate_report(trades, latched_bars_count, unlatched_bars_count,
                             d1_regime_timeline, churn_data["short_hold_buckets"], churn_data["exit_pnl"])
    print(report)


if __name__ == "__main__":
    main()
