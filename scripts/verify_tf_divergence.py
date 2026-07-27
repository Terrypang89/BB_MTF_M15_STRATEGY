# -*- coding: utf-8 -*-
"""
<<<<<<< HEAD
Cross-timeframe divergence test — measure whether DIVERGENCE predicts sideways price.
=======
Cross-timeframe divergence test — measure whether DVERGENCE predicts sideways price.
>>>>>>> 1235d8b4f8df90d7c896d7c1162228fff8193091

Verification only — do NOT modify TofySideway.mqh, any labelbase_strategy*.py, or the EA.

Uses the same log as label_base_rate.py:
    references/Backtest_data/V36.15/20260712_clean.log

Parse [M15], [M30], [H1], [M5] and [BBTFImpact] lines.

<<<<<<< HEAD
Direction per timeframe (from diffMid_Trend cur):
=======
Direction per timeframe (from diffMid_Trend cur value):
>>>>>>> 1235d8b4f8df90d7c896d7c1162228fff8193091
    1 or 5 -> U (Up)
    2 or 4 -> D (Down)
    3      -> S (Sideways)
    0      -> W (Warmup — ignore for divergence)

Divergence is defined as: any two timeframes disagree on direction.
    e.g., M15=U while M30=D, or H1=S while M15=U, etc.

<<<<<<< HEAD
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
=======
From each bar's divergence state, measure the first-touch barrier outcome
over the next N M15 bars (120 min):
    UP      = price hit start + X first
    DOWN    = price hit start - X first
    NEUTRAL = neither barrier touched

X = 10.0, N = 8 M15 bars — same as the base-rate test for comparability.

Report per bar:
    - ts (M15 timestamp)
    - M15_dir, M30_dir, H1_dir (each: U/D/S/W)
    - diverged (boolean)
    - outcome (UP/DOWN/NEUTRAL)

Aggregate into two groups:
    GROUP A: bars with divergence present
    GROUP B: bars without divergence (all timeframes agree)

Then compute NEUTRAL% for each group and compare.
"""

import re
>>>>>>> 1235d8b4f8df90d7c896d7c1162228fff8193091
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Optional

LOG_PATH = Path(r"references/Backtest_data/V36.15/20260712_clean.log")

<<<<<<< HEAD
# Sideways threshold and window length
SIDWAYS_RANGE = 10.0
M5_BARS_PER_120_MIN = 24
=======
# Barrier parameters — same as base-rate test
X = 10.0
N = 8  # M15 bars ahead (120 min)
>>>>>>> 1235d8b4f8df90d7c896d7c1162228fff8193091


def _parse_ts(ts: str) -> datetime:
    """Convert dot-separated timestamp to datetime."""
    return datetime.strptime(ts.replace(".", "-"), "%Y-%m-%d %H:%M:%S")


# Regex patterns for each timeframe
<<<<<<< HEAD
=======
# M15: W_stage list, diffMid_Trend cur
>>>>>>> 1235d8b4f8df90d7c896d7c1162228fff8193091
M15_RE = re.compile(
    r"^(\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2})"
    r".*W_stage_M15:.*\[\s*(\d+)"
    r".*diffMid_Trend_M15:\s*\[\s*(-?[\d.]+)"
)

<<<<<<< HEAD
=======
# M30: diffMid_Trend_D30 cur (same timestamp as M15 line)
>>>>>>> 1235d8b4f8df90d7c896d7c1162228fff8193091
M30_RE = re.compile(
    r"^(\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2}).*diffMid_Trend_D30:\s*\[\s*(-?[\d.]+)"
)

<<<<<<< HEAD
=======
# H1: diffMid_Trend_H1 cur
>>>>>>> 1235d8b4f8df90d7c896d7c1162228fff8193091
H1_RE = re.compile(
    r"^(\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2}).*diffMid_Trend_H1:\s*\[\s*(-?[\d.]+)"
)

<<<<<<< HEAD
=======
# M5: close price list (first = cur)
>>>>>>> 1235d8b4f8df90d7c896d7c1162228fff8193091
M5_RE = re.compile(
    r"^(\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2})"
    r".*close_M5:\s*\[\s*(-)?[\d.]+"
)

<<<<<<< HEAD
# BBTFImpact — S_ sub-type (kept for reference only)
=======
# BBTFImpact: Sideway_val:[NUM-S_n] — capture S_ sub-type if present
>>>>>>> 1235d8b4f8df90d7c896d7c1162228fff8193091
BBTFIMPACT_RE = re.compile(
    r"Sideway_val:\s*\[(\d+)-S_(\d+)\]"
)


def _dir_from_dm(dm: float) -> str:
    """Convert diffMid_Trend value to direction string."""
    if dm == 0:
<<<<<<< HEAD
        return "W"
=======
        return "W"  # warmup — ignore for divergence
>>>>>>> 1235d8b4f8df90d7c896d7c1162228fff8193091
    elif dm in (1, 5):
        return "U"
    elif dm in (2, 4):
        return "D"
    elif dm == 3:
        return "S"
    else:
<<<<<<< HEAD
        return "?"


def parse_log() -> Tuple[Dict[str, Dict], Dict[str, float], Dict[str, float], List[Tuple[str, float]], List[Tuple[str, float]]]:
    """
    Parse the log file.

=======
        # Unknown / missing — treat as neutral
        return "?"


def parse_log() -> Tuple[Dict[str, Dict], Dict[str, float], Dict[str, float], List[Tuple[str, float]], Dict[str, str]]:
    """
    Parse the log file.

    M30 and H1 update less frequently than M15 — we collect them as they appear
    and forward-fill when needed (use the nearest prior value).

>>>>>>> 1235d8b4f8df90d7c896d7c1162228fff8193091
    Returns:
        m15_data: dict keyed by M15 timestamp string
        m30_by_minute: dict mapping minute -> diffMid_Trend_D30 cur value
        h1_by_minute: dict mapping minute -> diffMid_Trend_H1 cur value
<<<<<<< HEAD
        m5_data: list of (ts, price) tuples — sorted once at module level
        m5_lookahead: list of (ts, price) — same M5 data for end-of-window lookup
=======
        m5_data: list of (ts, price) tuples for barrier evaluation
        bbf_by_minute: dict mapping minute -> S_ sub-type
>>>>>>> 1235d8b4f8df90d7c896d7c1162228fff8193091
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
<<<<<<< HEAD
=======
                # Minute from M15 timestamp (YYYY-MM-DD HH:MM)
>>>>>>> 1235d8b4f8df90d7c896d7c1162228fff8193091
                minute = ts_str[:16]
                m15_data[ts_str] = {
                    "ts": ts_dt,
                    "minute": minute,
<<<<<<< HEAD
                    "dm": float(dm_m15),
                }

=======
                    "m30": m30_by_minute.get(minute),
                    "h1": h1_by_minute.get(minute),
                }

            # M30 line — capture diffMid_Trend_D30 cur
>>>>>>> 1235d8b4f8df90d7c896d7c1162228fff8193091
            m30_match = M30_RE.search(raw)
            if m30_match:
                ts_str, dm_m30 = m30_match.groups()
                minute = ts_str[:16]
                m30_by_minute[minute] = float(dm_m30)

<<<<<<< HEAD
=======
            # H1 line — capture diffMid_Trend_H1 cur
>>>>>>> 1235d8b4f8df90d7c896d7c1162228fff8193091
            h1_match = H1_RE.search(raw)
            if h1_match:
                ts_str, dm_h1 = h1_match.groups()
                minute = ts_str[:16]
                h1_by_minute[minute] = float(dm_h1)

<<<<<<< HEAD
=======
            # M5 close price
>>>>>>> 1235d8b4f8df90d7c896d7c1162228fff8193091
            m5_match = M5_RE.search(raw)
            if m5_match:
                ts_str, price = m5_match.groups()
                m5_data.append((ts_str, float(price)))

<<<<<<< HEAD
=======
            # BBTFImpact — store S_ sub-type by minute
>>>>>>> 1235d8b4f8df90d7c896d7c1162228fff8193091
            bbf_match = BBTFIMPACT_RE.search(raw)
            if bbf_match:
                impact_ts, _, subtype = bbf_match.groups()
                norm_ts = impact_ts.replace(".", "-")
                minute = norm_ts[:16]
                bbf_by_minute[minute] = subtype

<<<<<<< HEAD
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
=======
    # Sort M5 data by timestamp
    m5_data.sort(key=lambda x: _parse_ts(x[0]))

    return m15_data, m30_by_minute, h1_by_minute, m5_data, bbf_by_minute


def get_nearest_m5_at_or_before(m5_list: List[Tuple[str, float]], target_dt: datetime) -> Optional[float]:
    """Return the nearest M5 close at or before target_dt (same as labelbase_strategy_dmonly)."""
    nearest = None
    target_str = target_dt.strftime("%Y.%m.%d %H:%M:%S")
    for ts, price in m5_list:
        if ts <= target_str:
            nearest = price
        else:
            break
    return nearest


def evaluate_barrier(start_price: float, m5_lookup: List[Tuple[str, float]],
                     start_dt: datetime, end_dt: datetime) -> str:
    """
    First-touch barrier over [start_dt, end_dt].
    UP  = close >= start + X
    DOWN = close <= start - X
    NEUTRAL = neither touched.
    """
    first_touch = "NEUTRAL"
    for ts, price in m5_lookup:
        ts_dt = _parse_ts(ts)
        if ts_dt < start_dt:
            continue
        if ts_dt > end_dt:
            break
        up = price >= start_price + X
        down = price <= start_price - X
        if up and down:
            return "AMBIGUOUS"  # should not happen with clean data
        if up:
            first_touch = "UP"
            break
        if down:
            first_touch = "DOWN"
            break
    return first_touch
>>>>>>> 1235d8b4f8df90d7c896d7c1162228fff8193091


def main() -> None:
    print("Parsing log...")
<<<<<<< HEAD
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
=======
    m15_data, m30_by_minute, h1_by_minute, m5_data, bbf_by_minute = parse_log()

    print(f"Parsed {len(m15_data)} M15 bars, {len(m5_data)} M5 bars")
    print(f"BBTFImpact entries: {sum(1 for _ in bbf_by_minute.values())}")

    results: List[Dict] = []

    # Helper: forward-fill — given a minute and value dict, return nearest prior value
    def forward_fill(minute: str, value_dict: Dict[str, float], default: Optional[float]) -> Optional[float]:
        # Find the latest minute <= current that has a value
        for m in sorted(value_dict.keys()):
            if m <= minute:
                return value_dict[m]
        return default

    # Iterate through M15 bars (sorted by timestamp)
    for ts_str, entry in sorted(m15_data.items(), key=lambda x: _parse_ts(x[0])):
        minute = entry["minute"]

        # Forward-fill M30 and H1 if not yet present
        m30_val = forward_fill(minute, m30_by_minute, None)
        h1_val = forward_fill(minute, h1_by_minute, None)

        m15_dm = entry["dm"]
        m30_dm = m30_val
        h1_dm = h1_val

        m15_dir = _dir_from_dm(m15_dm)
        m30_dir = _dir_from_dm(m30_dm)
        h1_dir = _dir_from_dm(h1_dm)

        # Determine divergence: any two timeframes disagree, or one is S while others differ
        def diverge(d1: str, d2: str, d3: str) -> bool:
            # All three agree
            if d1 == d2 == d3:
                return False
            # One is warmup (W) — ignore it; divergence only if the remaining two disagree
            non_warmups = [d for d in (d1, d2, d3) if d != "W"]
            if len(non_warmups) == 0:
                return False  # all W
            if len(non_warmups) == 1:
                return False  # only one non-warmup — no divergence to compare against
            # Two non-warmups must also disagree for divergence
            return non_warmups[0] != non_warmups[1]

        diverged = diverge(m15_dir, m30_dir, h1_dir)

        # Get start price from M5 (nearest at or before this M15 bar)
        start_price = get_nearest_m5_at_or_before(m5_data, entry["ts"])
        if start_price is None:
            # No prior M5 — cannot evaluate barrier
            results.append({
                "ts": ts_str,
                "m15_dir": m15_dir,
                "m30_dir": m30_dir,
                "h1_dir": h1_dir,
                "diverged": False,
                "outcome": "NEUTRAL",
            })
            continue

        # Compute end of window (start + N M15 bars = 120 min)
        end_dt = entry["ts"] + timedelta(minutes=120)

        outcome = evaluate_barrier(start_price, m5_data, entry["ts"], end_dt)
>>>>>>> 1235d8b4f8df90d7c896d7c1162228fff8193091

        results.append({
            "ts": ts_str,
            "m15_dir": m15_dir,
            "m30_dir": m30_dir,
            "h1_dir": h1_dir,
            "diverged": diverged,
<<<<<<< HEAD
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
=======
            "outcome": outcome,
        })

    # Group each M15 bar into categories:
    # - DV_15_30: M15 and M30 directions are opposite (one U, one D)
    # - DV_15_H1: M15 and H1 directions are opposite
    # - AREE: M15 and M30 same direction (both U or both D)
    # - SLAG: the existing TofySideway S flag is present (bbf_by_minute has S_)
    # - DV_ANY: any divergence between non-W warmup readings (already computed via diverged flag)

    group_dv_15_30 = 0   # M15 opposite M30
    group_dv_15_h1 = 0   # M15 opposite H1
    group_aree = 0       # M15 same as M30
    group_slag = 0       # S flag present

    for r in results:
        m15_dir = r["m15_dir"]
        m30_dir = r["m30_dir"]
        h1_dir = r["h1_dir"]
        minute = r["ts"][:16]  # "YYYY-MM-DD HH:MM"

        # DV_15_30: M15 and M30 opposite (one U, one D)
        if m15_dir in ("U", "D") and m30_dir in ("U", "D") and m15_dir != m30_dir:
            group_dv_15_30 += 1

        # DV_15_H1: M15 and H1 opposite
        if m15_dir in ("U", "D") and h1_dir in ("U", "D") and m15_dir != h1_dir:
            group_dv_15_h1 += 1

        # AREE: M15 same as M30 (both U or both D)
        if m15_dir in ("U", "D") and m30_dir in ("U", "D") and m15_dir == m30_dir:
            group_aree += 1

        # SLAG: existing TofySideway S flag present
        if bbf_by_minute.get(minute):
            group_slag += 1

    print(f"\nGroup counts:")
    print(f"  DV_15_30 (M15 vs M30 opposite): {group_dv_15_30}")
    print(f"  DV_15_H1 (M15 vs H1 opposite):   {group_dv_15_h1}")
    print(f"  AREE (M15 same as M30):          {group_aree}")
    print(f"  SLAG (S flag present):           {group_slag}")

    # Compute NEUTRAL counts and percentages
    def count_outcomes(rlist: List[Dict]) -> Dict[str, int]:
        return {
            "UP": sum(1 for r in rlist if r["outcome"] == "UP"),
            "DOWN": sum(1 for r in rlist if r["outcome"] == "DOWN"),
            "NEUTRAL": sum(1 for r in rlist if r["outcome"] == "NEUTRAL"),
        }

    out_a = count_outcomes(group_a)
    out_b = count_outcomes(group_b)

    a_neutral_pct = (out_a["NEUTRAL"] / len(group_a) * 100) if group_a else 0.0
    b_neutral_pct = (out_b["NEUTRAL"] / len(group_b) * 100) if group_b else 0.0

    print("\nGROUP A outcomes:")
    for k, v in out_a.items():
        print(f"  {k}: {v}")
    print(f"\nGROUP B outcomes:")
    for k, v in out_b.items():
        print(f"  {k}: {v}")

    delta = a_neutral_pct - b_neutral_pct
    print(f"\nA_neutral% = {a_neutral_pct:.2f}%, B_neutral% = {b_neutral_pct:.2f}%")
    print(f"Difference: {delta:+.1f} percentage points")

    if delta > 0:
        print("Conclusion: Divergence is associated with higher NEUTRAL rate — supports the claim.")
    elif delta < 0:
        print("Conclusion: Divergence is associated with lower NEUTRAL rate — does not support the claim.")
    else:
        print("Conclusion: NEUTRAL rates are equal — no detectable difference.")

    # Save results to a JSON file for inspection
    results_path = LOG_PATH.parent / "verify_tf_divergence_results.json"
    with results_path.open("w", encoding="utf-8") as f:
        import json
        json.dump(results, f, indent=2)

    print(f"\nResults saved to: {results_path}")
>>>>>>> 1235d8b4f8df90d7c896d7c1162228fff8193091


if __name__ == "__main__":
    main()
