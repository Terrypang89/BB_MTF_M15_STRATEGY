#!/usr/bin/env python3
"""Extract event-driven state tables from V31.04 log for IMAGE_ANALYSIS.md rebuild.

For each user-defined period, extracts M15/M30/H1/H4/D1/W1 state at each M15-bar
timestamp, then produces event-driven rows (new row only on M15 BBW_stage/diffMid change).
"""

import re
from pathlib import Path
from collections import defaultdict

BASE = Path(__file__).resolve().parent.parent
LOG_PATH = BASE / "references" / "Backtest_data" / "V31.04" / "20260620_clean.log"

TF_NAMES = ["M15", "M30", "H1", "H4", "D1", "W1"]

# User-defined periods per image block (in order of appearance in IMAGE_ANALYSIS.md)
PERIODS = [
    # Scenario F
    ("F_img1", "2026.01.02 01:00", "2026.01.03 04:00"),
    ("F_img2", "2026.04.01 13:00", "2026.04.01 17:00"),
    ("F_img3", "2026.01.02 01:00", "2026.01.03 04:00"),
    # Scenario S
    ("S_img1", "2026.03.30 13:00", "2026.04.01 13:00"),
    ("S_img2", "2026.03.30 14:30", "2026.04.01 09:00"),
    ("S_img3", "2026.03.30 13:00", "2026.04.01 17:00"),
    # Scenario P
    ("P_img1", "2026.04.03 03:00", "2026.04.05 00:00"),
    ("P_img2", "2026.04.04 15:00", "2026.04.05 00:00"),
    # Scenario R
    ("R_img1", "2026.04.01 14:30", "2026.04.02 05:00"),
    ("R_img2", "2026.04.01 14:30", "2026.04.02 09:00"),
    # Scenario B
    ("B_img1", "2026.02.06 01:00", "2026.02.07 21:00"),
    ("B_img2", "2026.02.06 13:00", "2026.02.07 09:00"),
    ("B_img3", "2026.02.06 13:00", "2026.02.07 09:00"),
    # Scenario V
    ("V_img1", "2026.04.02 05:00", "2026.04.03 03:00"),
    # Scenario C
    ("C_img1", "2026.04.01 13:00", "2026.04.02 17:00"),
    ("C_img2", "2026.04.02 09:00", "2026.04.02 17:00"),
    ("C_img3", "2026.04.01 17:00", "2026.04.02 05:00"),
    ("C_img4", "2026.04.02 05:00", "2026.04.02 17:00"),
    ("C_img5", "2026.04.02 10:00", "2026.04.02 17:00"),
    ("C_img6", "2026.04.02 17:00", "2026.04.03 03:00"),
    ("C_img7", "2026.04.03 03:00", "2026.04.03 17:00"),
]

def parse_log(log_path):
    """Parse log into dict: { tf: { datetime_str: {stage, diffMid, BBUpDn} } }"""
    data = {tf: {} for tf in TF_NAMES}

    with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
        for line in f:
            for tf in TF_NAMES:
                if f'[{tf}]' not in line:
                    continue
                # Timestamp
                m_ts = re.match(r'(2026\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2})', line)
                if not m_ts:
                    continue
                ts = m_ts.group(1)
                # Stage
                m_st = re.search(rf'W_stage_{tf}:\((\w+)\)\[([^\]]+)\]', line)
                if not m_st:
                    continue
                stage = int(m_st.group(2).split(',')[0].strip())
                # diffMid_Trend
                m_dm = re.search(rf'diffMid_Trend_{tf}:\[([^\]]+)\]', line)
                diffMid = None
                if m_dm:
                    diffMid = float(m_dm.group(1).split(',')[0].strip())
                # BBUpDn
                m_bu = re.search(rf'BBUpDn_{tf}:\[([^\]]+)\]', line)
                bbupdn = None
                if m_bu:
                    bbupdn = int(m_bu.group(1).split(',')[0].strip())

                data[tf][ts] = {
                    'stage': stage,
                    'diffMid': diffMid,
                    'BBUpDn': bbupdn,
                }
    return data

def ts_in_range(ts, start, end):
    """Check if timestamp is in [start, end] range."""
    # Remove seconds for comparison: "2026.01.02 01:15:02" -> "2026.01.02 01:15"
    ts_dt = ts[:16]  # "2026.01.02 01:15"
    start_dt = start[:16]
    end_dt = end[:16]
    return start_dt <= ts_dt <= end_dt

def round_down_to_m15(ts):
    """Round timestamp down to nearest M15 bar."""
    # "2026.01.02 01:15:02" -> "2026.01.02 01:15"
    return ts[:16]

def get_m15_timestamps_in_period(data, start, end):
    """Get unique M15 bar timestamps within period."""
    m15_ts = set()
    for ts in data["M15"].keys():
        if ts_in_range(ts, start, end):
            m15_ts.add(round_down_to_m15(ts))
    return sorted(m15_ts)

def get_state_at_tf(data, tf, ts):
    """Get the nearest state for a TF at or before the given M15 timestamp."""
    # Find the latest entry at or before ts
    ts_target = ts  # "2026.01.02 01:15"
    best = None
    for log_ts, state in data[tf].items():
        log_ts_rounded = round_down_to_m15(log_ts)
        if log_ts_rounded <= ts_target:
            if best is None or log_ts_rounded > best[0]:
                best = (log_ts_rounded, state)
        else:
            break  # sorted, so we can stop
    return best[1] if best else None

def stage_label(stage):
    """Convert stage code to label."""
    if stage in (511, 512):
        return "up-fly"
    elif stage in (521, 522):
        return "down-fly"
    elif stage in (513, 523):
        return "shrink"
    elif 400 <= stage <= 499:
        return "SQZ"
    return str(stage)

def diffmid_label(dm):
    """Convert diffMid value to label."""
    if dm == 1.0:
        return "up"
    elif dm == 2.0:
        return "down"
    elif dm == 3.0:
        return "sideways"
    elif dm == 4.0:
        return "deep-sideways"
    elif dm == 5.0:
        return "deep-sideways"
    return str(int(dm)) if dm else "?"

def cell_format(stage, diffmid, bbupdn):
    """Format as BBW_stage-diffMid-BBUpDn."""
    if stage is None:
        return "[TO BE FILLED]"
    dm = int(diffmid) if diffmid is not None else "?"
    bu = bbupdn if bbupdn is not None else "?"
    return f"{stage}-{dm}-{bu}"

def derive_scenario(htf_cells, mtf_cells):
    """Derive HTF-MTF scenario pair from cell data.

    Args:
        htf_cells: dict of H4, D1, W1 states
        mtf_cells: dict of M15, M30, H1 states
    Returns:
        (htf_scenario, mtf_scenario, divergence_flag)
    """
    def safe_get(d, key, default=0):
        """Safe dict access for potentially None states."""
        if d is None:
            return default
        return d.get(key, default)

    # --- MTF scenario ---
    m15_s = safe_get(mtf_cells.get('M15'), 'stage', 0)
    m30_s = safe_get(mtf_cells.get('M30'), 'stage', 0)
    h1_s = safe_get(mtf_cells.get('H1'), 'stage', 0)
    m15_dm = safe_get(mtf_cells.get('M15'), 'diffMid', 0) or 0
    m30_dm = safe_get(mtf_cells.get('M30'), 'diffMid', 0) or 0
    h1_dm = safe_get(mtf_cells.get('H1'), 'diffMid', 0) or 0

    h4_s = safe_get(htf_cells.get('H4'), 'stage', 0)
    h4_dm = safe_get(htf_cells.get('H4'), 'diffMid', 0) or 0

    mtf_scenario = "F"  # default: flying same as H4
    # Check shrink
    if any(s in (513, 523) for s in [m15_s, m30_s, h1_s]):
        # deepest shrink TF
        if m15_s in (513, 523) and m30_s in (513, 523) and h1_s in (513, 523):
            mtf_scenario = "S3"
        elif m15_s in (513, 523) and m30_s in (513, 523):
            mtf_scenario = "S2"
        elif m15_s in (513, 523):
            mtf_scenario = "S1"
    # Check SQZ
    elif any(400 <= s <= 499 for s in [m15_s, m30_s, h1_s] if s):
        if all(400 <= s <= 499 for s in [m15_s, m30_s] if s):
            mtf_scenario = "C2"
        elif (400 <= m15_s <= 499):
            mtf_scenario = "C1"
    # Check reversal (opposite to H4)
    elif (h4_dm == 1.0 and any(dm == 2.0 for dm in [m15_dm, m30_dm, h1_dm])) or \
         (h4_dm == 2.0 and any(dm == 1.0 for dm in [m15_dm, m30_dm, h1_dm])):
        mtf_scenario = "R1"

    # --- HTF scenario ---
    d1_s = safe_get(htf_cells.get('D1'), 'stage', 0)
    d1_dm = safe_get(htf_cells.get('D1'), 'diffMid', 0) or 0
    w1_s = safe_get(htf_cells.get('W1'), 'stage', 0)
    w1_dm = safe_get(htf_cells.get('W1'), 'diffMid', 0) or 0

    htf_scenario = "F"  # default
    if h4_s and 400 <= h4_s <= 499:
        htf_scenario = "V1"  # H4 in SQZ
    elif h4_s and h4_s in (513, 523):
        htf_scenario = "C4"
    elif h4_s:  # H4 flying
        # Check D1/W1 alignment
        if d1_s == 0 or w1_s == 0:
            htf_scenario = "F"  # can't determine (missing D1/W1 data)
        elif h4_dm == d1_dm == w1_dm and h4_dm in (1.0, 2.0):
            htf_scenario = "F1"
        elif h4_dm == d1_dm or h4_dm == w1_dm:
            htf_scenario = "F2"
        else:
            htf_scenario = "F3"

    # Divergence check
    divergence = False
    if h4_dm in (1.0, 2.0):
        for tf_dm in [m15_dm, m30_dm, h1_dm]:
            if tf_dm == 3 - h4_dm:  # opposite
                divergence = True
                break

    return htf_scenario, mtf_scenario, divergence

def derive_trend_tier(htf_cells):
    """Derive trend and tier from H4/D1."""
    h4_s_obj = htf_cells.get('H4')
    d1_s_obj = htf_cells.get('D1')
    h4_dm = (h4_s_obj.get('diffMid', 0) if h4_s_obj else 0) or 0
    d1_dm = (d1_s_obj.get('diffMid', 0) if d1_s_obj else 0) or 0
    h4_s = (h4_s_obj.get('stage', 0) if h4_s_obj else 0) or 0

    if h4_dm == 1.0 and d1_dm == 1.0:
        trend = "Up"
    elif h4_dm == 2.0 and d1_dm == 2.0:
        trend = "Down"
    elif h4_dm == 1.0 and d1_dm == 2.0:
        trend = "Up (div)"
    elif h4_dm == 2.0 and d1_dm == 1.0:
        trend = "Down (div)"
    else:
        trend = "Sideways"

    if h4_s in (511, 512, 521, 522):
        tier = 1
    elif h4_s in (513, 523):
        tier = 2
    elif 400 <= h4_s <= 499:
        tier = 2
    else:
        tier = 3

    return f"{trend} / Tier {tier}"

def main():
    print(f"Parsing log: {LOG_PATH}")
    data = parse_log(LOG_PATH)

    for tf in TF_NAMES:
        print(f"  {tf}: {len(data[tf])} entries, range: {min(data[tf].keys())[:16]} to {max(data[tf].keys())[:16]}")

    for name, start, end in PERIODS:
        print(f"\n{'='*80}")
        print(f"Block: {name}  Period: {start} -> {end}")
        print(f"{'='*80}")

        m15_ts_list = get_m15_timestamps_in_period(data, start, end)
        print(f"  M15 bars in period: {len(m15_ts_list)}")

        if not m15_ts_list:
            print(f"  WARNING: No M15 data found for period {start} -> {end}")
            continue

        # Build rows - new row only on M15 BBW_stage/diffMid change
        rows = []
        prev_m15_stage = None
        prev_m15_diffmid = None

        for ts in m15_ts_list:
            states = {}
            for tf in TF_NAMES:
                states[tf] = get_state_at_tf(data, tf, ts)

            m15 = states['M15']
            if m15 is None:
                continue

            # Check if M15 stage or diffMid changed
            if (m15['stage'] != prev_m15_stage or
                m15['diffMid'] != prev_m15_diffmid):
                # Build cells (None TFs become [TO BE FILLED])
                cells = {}
                for tf in TF_NAMES:
                    s = states[tf]
                    cells[tf] = cell_format(
                        s['stage'] if s else None,
                        s['diffMid'] if s else None,
                        s['BBUpDn'] if s else None,
                    )

                # Derive scenario — pass None-safe states
                htf_cells = {k: states.get(k) for k in ['H4', 'D1', 'W1']}
                mtf_cells = {k: states.get(k) for k in ['M15', 'M30', 'H1']}
                htf_sc, mtf_sc, div = derive_scenario(htf_cells, mtf_cells)
                trend_tier = derive_trend_tier(htf_cells)

                scenario_str = f"{htf_sc}-{mtf_sc}"
                if div:
                    scenario_str += " [divergence]"

                rows.append({
                    'datetime': ts,
                    'cells': cells,
                    'scenario': scenario_str,
                    'trend_tier': trend_tier,
                })

                prev_m15_stage = m15['stage']
                prev_m15_diffmid = m15['diffMid']

        # Print the table
        print(f"  Event-driven rows: {len(rows)}")
        print(f"  | datetime | M15 | M30 | H1 | H4 | D1 | W1 | Scenario (HTF-MTF) | Trend / Tier |")
        print(f"  |----------|-----|-----|----|----|----|----|--------------------|------------|")
        for row in rows:
            print(f"  | {row['datetime']} | {row['cells']['M15']} | {row['cells']['M30']} | {row['cells']['H1']} | {row['cells']['H4']} | {row['cells']['D1']} | {row['cells']['W1']} | {row['scenario']} | {row['trend_tier']} |")

        # Coverage check
        first_ts = rows[0]['datetime'] if rows else "N/A"
        last_ts = rows[-1]['datetime'] if rows else "N/A"
        print(f"  Coverage: {first_ts} -> {last_ts} (period: {start[:16]} -> {end[:16]})")
        if first_ts >= start[:16] and last_ts <= end[:16]:
            print(f"  Coverage: COMPLETE")
        else:
            print(f"  Coverage: INCOMPLETE")

if __name__ == "__main__":
    main()
