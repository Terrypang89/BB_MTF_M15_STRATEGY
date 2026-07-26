# -*- coding: utf-8 -*-
"""
Cross-timeframe divergence test — measure whether DIVERGENCE predicts sideways price.

Verification only — do NOT modify TofySideway.mqh, any labelbase_strategy*.py, or the EA.

Uses the same log as label_base_rate.py:
    references/Backtest_data/V36.15/20260712_clean.log

Parse [M15], [M30], [H1], [M5] and [BBTFImpact] lines.

Direction per timeframe (from diffMid_Trend cur):
    1 or 5 -> U (Up)
    2 or 4 -> D (Down)
    3      -> S (Sideways)
    0      -> W (Warmup — ignore for divergence)

Divergence is defined as: any two timeframes disagree on direction.
    e.g., M15=U while M30=D, or H1=S while M15=U, etc.

Sideways = abs(end_price - start_price) < 10.0 over the 120-minute window.
start_price = nearest M5 close at or before this bar's timestamp
end_price   = M5 close 24 bars later (120 min)

Group columns:
    ALL_BARS       — every bar in the dataset
    DIV_5_15       — divergence between M5 and M15
    DIV_15_30      — divergence between M15 and M30
    DIV_15_H1      — divergence between M15 and H1
    DIV_BOTH_5_30  — divergence between M5 and M30 (both timeframes)
    AGREE          — no divergence across all non-W timeframes

Report per group:
    n     = number of bars with a valid end price (24 M5 bars ahead)
    sideways_pct = (count where |end-start| < 10.0) / n * 100

Efficiency ratio (unthresholded, printed for debugging):
    eff = abs(end - start) / sum(|bar-to-bar moves|)
"""

import re
import json
import math
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Optional

LOG_PATH = Path(r"references/Backtest_data/V36.15/20260712_clean.log")

# Sideways threshold and window length
SIDWAYS_RANGE = 10.0
M5_BARS_PER_120_MIN = 24


def _parse_ts(ts: str) -> datetime:
    """Convert dot-separated timestamp to datetime."""
    return datetime.strptime(ts.replace(".", "-"), "%Y-%m-%d %H:%M:%S")


# Regex patterns for each timeframe
M15_RE = re.compile(
    r"^(\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2})"
    r".*W_stage_M15:.*\[\s*(\d+)"
    r".*diffMid_Trend_M15:\s*\[\s*(-?[\d.]+)"
)

M30_RE = re.compile(
    r"^(\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2}).*diffMid_Trend_D30:\s*\[\s*(-?[\d.]+)"
)

H1_RE = re.compile(
    r"^(\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2}).*diffMid_Trend_H1:\s*\[\s*(-?[\d.]+)"
)

M5_RE = re.compile(
    r"^(\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2})"
    r".*close_M5:\s*\[\s*(-)?[\d.]+"
)

# BBTFImpact — S_ sub-type (kept for reference only)
BBTFIMPACT_RE = re.compile(
    r"Sideway_val:\s*\[(\d+)-S_(\d+)\]"
)


def _dir_from_dm(dm: float) -> str:
    """Convert diffMid_Trend value to direction string."""
    if dm == 0:
        return "W"
    elif dm in (1, 5):
        return "U"
    elif dm in (2, 4):
        return "D"
    elif dm == 3:
        return "S"
    else:
        return "?"


def parse_log() -> Tuple[Dict[str, Dict], Dict[str, float], Dict[str, float], List[Tuple[str, float]], List[Tuple[str, float]]]:
    """
    Parse the log file.

    Returns:
        m15_data: dict keyed by M15 timestamp string
        m30_by_minute: dict mapping minute -> diffMid_Trend_D30 cur value
        h1_by_minute: dict mapping minute -> diffMid_Trend_H1 cur value
        m5_data: list of (ts, price) tuples — sorted once at module level
        m5_lookahead: list of (ts, price) — same M5 data for end-of-window lookup
    """
    m15_data: Dict[str, Dict] = {}
    m30_by_minute: Dict[str, float] = {}
    h1_by_minute: Dict[str, float] = {}
    m5_data: List[Tuple[str, float]] = []
    bbf_by_minute: Dict[str, str] = {}

    with LOG_PATH.open("r", encoding="utf-8") as f:
        for raw in f:
            ts_match = M15_RE.search(raw)
            if ts_match:
                ts_str, ws, dm_m15 = ts_match.groups()
                ts_dt = _parse_ts(ts_str)
                minute = ts_str[:16]
                m15_data[ts_str] = {
                    "ts": ts_dt,
                    "minute": minute,
                    "dm": float(dm_m15),
                }

            m30_match = M30_RE.search(raw)
            if m30_match:
                ts_str, dm_m30 = m30_match.groups()
                minute = ts_str[:16]
                m30_by_minute[minute] = float(dm_m30)

            h1_match = H1_RE.search(raw)
            if h1_match:
                ts_str, dm_h1 = h1_match.groups()
                minute = ts_str[:16]
                h1_by_minute[minute] = float(dm_h1)

            m5_match = M5_RE.search(raw)
            if m5_match:
                ts_str, price = m5_match.groups()
                m5_data.append((ts_str, float(price)))

            bbf_match = BBTFIMPACT_RE.search(raw)
            if bbf_match:
                impact_ts, _, subtype = bbf_match.groups()
                norm_ts = impact_ts.replace(".", "-")
                minute = norm_ts[:16]
                bbf_by_minute[minute] = subtype

    # Sort M5 data once — use for both start and end lookups
    m5_data.sort(key=lambda x: _parse_ts(x[0]))

    return m15_data, m30_by_minute, h1_by_minute, m5_data, m5_data


def find_m5_close_at_or_before(m5_list: List[Tuple[str, float]], target_dt: datetime) -> Optional[float]:
    """Binary search for the nearest M5 close <= target_dt."""
    from bisect import bisect_right

    def make_comparable(dt: datetime) -> str:
        return dt.strftime("%Y.%m.%d %H:%M:%S")

    idx = bisect_right([make_comparable(ts) for ts, _ in m5_list], make_comparable(target_dt))
    if idx == 0:
        return None
    ts, price = m5_list[idx - 1]
    return price


def main() -> None:
    print("Parsing log...")
    m15_data, m30_by_minute, h1_by_minute, m5_data, _ = parse_log()

    print(f"Parsed {len(m15_data)} M15 bars, {len(m5_data)} M5 bars")

    # Build minute-indexed lookups for forward-fill
    minute_to_idx: Dict[str, int] = {
        ts[:16]: i for i, (ts, _) in enumerate(m5_data)
    }

    results: List[Dict] = []

    for ts_str, entry in sorted(m15_data.items(), key=lambda x: _parse_ts(x[0])):
        minute = entry["minute"]
        idx = minute_to_idx.get(minute)
        if idx is None:
            continue

        start_price = m5_data[idx][1]
        # End of window: 24 M5 bars later
        end_idx = idx + M5_BARS_PER_120_MIN
        if end_idx >= len(m5_data):
            # Not enough lookahead — skip this bar
            continue
        end_price = m5_data[end_idx][1]

        start_dt = entry["ts"]
        end_dt = start_dt + timedelta(minutes=120)

        dm15 = entry["dm"]
        m30_dm = m30_by_minute.get(minute)
        h1_dm = h1_by_minute.get(minute)

        m15_dir = _dir_from_dm(dm15) if dm15 is not None else "W"
        m30_dir = _dir_from_dm(m30_dm) if m30_dm is not None else "W"
        h1_dir = _dir_from_dm(h1_dm) if h1_dm is not None else "W"

        # Divergence: any pair disagrees (ignore W)
        dirs = [d for d in (m15_dir, m30_dir, h1_dir) if d != "W"]
        diverged = len(dirs) < 2 or dirs[0] != dirs[1]

        # Sideways verdict
        net = end_price - start_price
        is_sideways = abs(net) < SIDWAYS_RANGE

        # Efficiency ratio (unthresholded)
        moves = [abs(end_price - start_price)]
        for i in range(idx + 1, end_idx):
            mid_price = m5_data[i][1]
            moves.append(abs(mid_price - m5_data[i - 1][1]))
        eff = sum(moves) if moves else 0.0
        if eff > 0:
            eff = abs(net) / eff
        else:
            eff = 0.0

        results.append({
            "ts": ts_str,
            "m15_dir": m15_dir,
            "m30_dir": m30_dir,
            "h1_dir": h1_dir,
            "diverged": diverged,
            "start_price": start_price,
            "end_price": end_price,
            "net": net,
            "is_sideways": is_sideways,
            "efficiency": eff,
        })

    # Group counts
    group_all = results
    group_div_5_15 = [r for r in results if r["diverged"] and any(r["m15_dir"] != d for d in (r["m30_dir"], r["h1_dir"]))]
    group_div_15_30 = [r for r in results if r["diverged"] and r["m15_dir"] != r["m30_dir"]]
    group_div_15_h1 = [r for r in results if r["diverged"] and r["m15_dir"] != r["h1_dir"]]
    group_div_both_5_30 = [r for r in results if r["diverged"] and r["m30_dir"] != r["h1_dir"]]
    group_agree = [r for r in results if not diverged]

    def sideways_pct(group: List[Dict]) -> float:
        n = len(group)
        if n == 0:
            return 0.0
        return sum(1 for r in group if r["is_sideways"]) / n * 100

    print(f"\nALL_BARS       n={len(group_all):4d}  sideways {sideways_pct(group_all):.1f}%")
    print(f"DIV_5_15       n={len(group_div_5_15):4d}  sideways {sideways_pct(group_div_5_15):.1f}%")
    print(f"DIV_15_30      n={len(group_div_15_30):4d}  sideways {sideways_pct(group_div_15_30):.1f}%")
    print(f"DIV_15_H1      n={len(group_div_15_h1):4d}  sideways {sideways_pct(group_div_15_h1):.1f}%")
    print(f"DIV_BOTH_5_30  n={len(group_div_both_5_30):4d}  sideways {sideways_pct(group_div_both_5_30):.1f}%")
    print(f"AGREE          n={len(group_agree):4d}  sideways {sideways_pct(group_agree):.1f}%")


if __name__ == "__main__":
    main()
