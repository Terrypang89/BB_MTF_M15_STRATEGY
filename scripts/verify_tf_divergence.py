# -*- coding: utf-8 -*-
"""
Cross-timeframe divergence test — measure whether DVERGENCE predicts sideways price.

Verification only — do NOT modify TofySideway.mqh, any labelbase_strategy*.py, or the EA.

Uses the same log as label_base_rate.py:
    references/Backtest_data/V36.15/20260712_clean.log

Parse [M15], [M30], [H1], [M5] and [BBTFImpact] lines.

Direction per timeframe (from diffMid_Trend cur value):
    1 or 5 -> U (Up)
    2 or 4 -> D (Down)
    3      -> S (Sideways)
    0      -> W (Warmup — ignore for divergence)

Divergence is defined as: any two timeframes disagree on direction.
    e.g., M15=U while M30=D, or H1=S while M15=U, etc.

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
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Optional

LOG_PATH = Path(r"references/Backtest_data/V36.15/20260712_clean.log")

# Barrier parameters — same as base-rate test
X = 10.0
N = 8  # M15 bars ahead (120 min)


def _parse_ts(ts: str) -> datetime:
    """Convert dot-separated timestamp to datetime."""
    return datetime.strptime(ts.replace(".", "-"), "%Y-%m-%d %H:%M:%S")


# Regex patterns for each timeframe
# M15: W_stage list, diffMid_Trend cur
M15_RE = re.compile(
    r"^(\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2})"
    r".*W_stage_M15:.*\[\s*(\d+)"
    r".*diffMid_Trend_M15:\s*\[\s*(-?[\d.]+)"
)

# M30: diffMid_Trend_D30 cur (same timestamp as M15 line)
M30_RE = re.compile(
    r"^(\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2}).*diffMid_Trend_D30:\s*\[\s*(-?[\d.]+)"
)

# H1: diffMid_Trend_H1 cur
H1_RE = re.compile(
    r"^(\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2}).*diffMid_Trend_H1:\s*\[\s*(-?[\d.]+)"
)

# M5: close price list (first = cur)
M5_RE = re.compile(
    r"^(\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2})"
    r".*close_M5:\s*\[\s*(-)?[\d.]+"
)

# BBTFImpact: Sideway_val:[NUM-S_n] — capture S_ sub-type if present
BBTFIMPACT_RE = re.compile(
    r"Sideway_val:\s*\[(\d+)-S_(\d+)\]"
)


def _dir_from_dm(dm: float) -> str:
    """Convert diffMid_Trend value to direction string."""
    if dm == 0:
        return "W"  # warmup — ignore for divergence
    elif dm in (1, 5):
        return "U"
    elif dm in (2, 4):
        return "D"
    elif dm == 3:
        return "S"
    else:
        # Unknown / missing — treat as neutral
        return "?"


def parse_log() -> Tuple[Dict[str, Dict], Dict[str, float], Dict[str, float], List[Tuple[str, float]], Dict[str, str]]:
    """
    Parse the log file.

    M30 and H1 update less frequently than M15 — we collect them as they appear
    and forward-fill when needed (use the nearest prior value).

    Returns:
        m15_data: dict keyed by M15 timestamp string
        m30_by_minute: dict mapping minute -> diffMid_Trend_D30 cur value
        h1_by_minute: dict mapping minute -> diffMid_Trend_H1 cur value
        m5_data: list of (ts, price) tuples for barrier evaluation
        bbf_by_minute: dict mapping minute -> S_ sub-type
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
                # Minute from M15 timestamp (YYYY-MM-DD HH:MM)
                minute = ts_str[:16]
                m15_data[ts_str] = {
                    "ts": ts_dt,
                    "minute": minute,
                    "m30": m30_by_minute.get(minute),
                    "h1": h1_by_minute.get(minute),
                }

            # M30 line — capture diffMid_Trend_D30 cur
            m30_match = M30_RE.search(raw)
            if m30_match:
                ts_str, dm_m30 = m30_match.groups()
                minute = ts_str[:16]
                m30_by_minute[minute] = float(dm_m30)

            # H1 line — capture diffMid_Trend_H1 cur
            h1_match = H1_RE.search(raw)
            if h1_match:
                ts_str, dm_h1 = h1_match.groups()
                minute = ts_str[:16]
                h1_by_minute[minute] = float(dm_h1)

            # M5 close price
            m5_match = M5_RE.search(raw)
            if m5_match:
                ts_str, price = m5_match.groups()
                m5_data.append((ts_str, float(price)))

            # BBTFImpact — store S_ sub-type by minute
            bbf_match = BBTFIMPACT_RE.search(raw)
            if bbf_match:
                impact_ts, _, subtype = bbf_match.groups()
                norm_ts = impact_ts.replace(".", "-")
                minute = norm_ts[:16]
                bbf_by_minute[minute] = subtype

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


def main() -> None:
    print("Parsing log...")
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

        results.append({
            "ts": ts_str,
            "m15_dir": m15_dir,
            "m30_dir": m30_dir,
            "h1_dir": h1_dir,
            "diverged": diverged,
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


if __name__ == "__main__":
    main()
