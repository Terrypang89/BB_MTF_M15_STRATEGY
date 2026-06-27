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

    Classification order (per disambiguation rules):
    1. HTF: H4 in SQZ (4xx) → V-family. H4 shrink (513/523) → C4.
       H4 fly → F-family (R2/R3 requires prior state to detect "flip" —
       without it, H4-vs-D1-opposite = F2, not R3).
    2. MTF: reversed opposite H4 → R1. Breaking from SQZ → B1/B2/B3
       (B1/B2 only when H4 also compressed; H4-fly + MTF-compressed = F-tier
       per Decision 6). In SQZ → C1/C2/C3. Shrinking → S1/S2/S3.
       P1/P2/P3 requires prior state (APPROX, not detected from snapshot).
       Else flying → F.
    3. Combine into (HTF-MTF) pair.
    """
    def safe_get(d, key, default=0):
        """Safe dict access for potentially None states."""
        if d is None:
            return default
        return d.get(key, default)

    def is_fly(s):
        return s in (511, 512, 521, 522)

    def is_shrink(s):
        return s in (513, 523)

    def is_sqz(s):
        return 400 <= s <= 499

    def fly_dir(s):
        """1=up-fly, 2=down-fly, 0=not fly."""
        if s in (511, 512):
            return 1
        elif s in (521, 522):
            return 2
        return 0

    # --- Gather MTF states ---
    m15_s = safe_get(mtf_cells.get('M15'), 'stage', 0)
    m30_s = safe_get(mtf_cells.get('M30'), 'stage', 0)
    h1_s = safe_get(mtf_cells.get('H1'), 'stage', 0)
    m15_dm = safe_get(mtf_cells.get('M15'), 'diffMid', 0) or 0
    m30_dm = safe_get(mtf_cells.get('M30'), 'diffMid', 0) or 0
    h1_dm = safe_get(mtf_cells.get('H1'), 'diffMid', 0) or 0
    m15_bu = safe_get(mtf_cells.get('M15'), 'BBUpDn', 0) or 0

    # --- Gather HTF states ---
    h4_s = safe_get(htf_cells.get('H4'), 'stage', 0)
    h4_dm = safe_get(htf_cells.get('H4'), 'diffMid', 0) or 0
    h4_bu = safe_get(htf_cells.get('H4'), 'BBUpDn', 0) or 0
    d1_s = safe_get(htf_cells.get('D1'), 'stage', 0)
    d1_dm = safe_get(htf_cells.get('D1'), 'diffMid', 0) or 0
    w1_s = safe_get(htf_cells.get('W1'), 'stage', 0)
    w1_dm = safe_get(htf_cells.get('W1'), 'diffMid', 0) or 0

    # ================================================================
    # MTF Scenario Classification
    # ================================================================
    mtf_scenario = "F"  # default: flying same as H4

    # --- R1: MTF reversed opposite H4 (H4 still flying) ---
    # Per backtest_chart_analysis.md p.3022: H4 flying dir X, M30 flying dir NOT-X
    if is_fly(h4_s) and is_fly(m30_s) and fly_dir(h4_s) != fly_dir(m30_s):
        mtf_scenario = "R1"

    # --- B1/B2/B3: Breakout from compression ---
    # B1: M15 fly, M30 still compressed (SQZ or shrink), H1 fly — LTF only
    # B2: M15+M30 fly, H1 compressed — MTF confirmed
    # B3: M15+M30+H1 all fly — HTF confirmed (indistinguishable from F without
    #     prior state, but if H4 was SQZ/shrink, it's B3 → V1/B3)
    # CRITICAL: B1/B2 only when H4 is also compressed (SQZ or shrink).
    # If H4 is flying, MTF compression is transient noise (F-tier, Decision 6).
    elif is_fly(m15_s) and (is_sqz(h4_s) or is_shrink(h4_s)):
        if is_fly(m30_s):
            if is_sqz(h1_s) or is_shrink(h1_s):
                mtf_scenario = "B2"
            # else: all MTF fly → F (or B3, but B3=F when all fly)
        elif is_sqz(m30_s) or is_shrink(m30_s):
            if is_fly(h1_s):
                mtf_scenario = "B1"
            else:
                # M15 fly but M30+H1 compressed — unusual, treat as B1
                mtf_scenario = "B1"
        # else M30 fly, H1 fly → F

    # --- C1/C2/C3: MTF in SQZ ---
    elif any(is_sqz(s) for s in [m15_s, m30_s, h1_s] if s):
        if all(is_sqz(s) for s in [m15_s, m30_s] if s):
            # Both M15 and M30 in SQZ → C2 (full LTF compression)
            # C3: M5 loading — BBUpDn 0→1 pattern. Without M5 data, we can't
            # distinguish C2 from C3 directly. APPROX: if M15 BBUpDn=1 (upper),
            # it suggests loading upward → C3.
            if m15_bu in (1, 3):
                mtf_scenario = "C3"  # APPROX — verify against doc
            else:
                mtf_scenario = "C2"
        elif is_sqz(m15_s):
            mtf_scenario = "C1"

    # --- S1/S2/S3: MTF shrinking ---
    elif any(is_shrink(s) for s in [m15_s, m30_s, h1_s]):
        if is_shrink(m15_s) and is_shrink(m30_s) and is_shrink(h1_s):
            mtf_scenario = "S3"
        elif is_shrink(m15_s) and is_shrink(m30_s):
            mtf_scenario = "S2"
        elif is_shrink(m15_s):
            mtf_scenario = "S1"

    # --- P1/P2/P3: Rest recovery — APPROX without prior state ---
    # P1: M5 break after pause, M15 still compressed, M30+H1 fly
    # P2: M15 mid flip after pause, M30+H1 fly
    # P3: MTF re-aligns to fly (indistinguishable from F)
    # Without prior state, P1/P2 look like S1 (M15 shrink, M30+H1 fly).
    # Heuristic: if M15 shrink but M30+H1 fly AND H4 fly same direction →
    # could be S1 or P1/P2. We default to S1 (safer).
    # P1/P2 detection requires prior-state; marked APPROX.

    # ================================================================
    # HTF Scenario Classification
    # ================================================================
    htf_scenario = "F"  # default

    if h4_s:
        # --- V-family: H4 in SQZ ---
        if is_sqz(h4_s):
            # V1: H4 breaks same dir as D1
            # V2: H4 breaks opposite D1
            # V3: false breakout (reverts within 3 bars — need prior state)
            # V4: whipsaw (alternating — need prior state)
            # Without prior state, H4 in SQZ = V1 (default pivot state).
            # APPROX: if H4 BBUpDn=1 and D1 fly same dir → V1
            #         if H4 BBUpDn=4 and D1 fly opposite → V2
            #         else → V1 (default, H4 SQZ)
            if is_fly(d1_s) and h4_bu in (4, 2):
                # H4 breaking downward while D1 flying upward → opposite = V2
                if d1_dm == 1.0:
                    htf_scenario = "V2"
                # H4 breaking downward, D1 flying downward → same = V1
                elif d1_dm == 2.0:
                    htf_scenario = "V1"
                else:
                    htf_scenario = "V1"
            elif h4_bu in (1, 3):
                # H4 breaking upward
                if is_fly(d1_s) and d1_dm == 2.0:
                    # D1 flying down, H4 breaks up → opposite = V2
                    htf_scenario = "V2"
                else:
                    htf_scenario = "V1"
            else:
                htf_scenario = "V1"  # H4 SQZ, no breakout yet

        # --- C4: H4 shrinking ---
        elif is_shrink(h4_s):
            htf_scenario = "C4"

        # --- F-family: H4 flying ---
        # R2/R3 requires prior state to detect "H4 flipped vs original trend".
        # Without it, H4-fly + D1-fly-opposite = F2 (partial fly, not R3).
        # APPROX — verify against doc: R2/R3 detection unavailable from
        # snapshot alone; requires tracking H4 direction change.
        elif is_fly(h4_s):
            if d1_s == 0 or w1_s == 0:
                htf_scenario = "F"  # can't determine
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

        # Coverage check — compare last DATA timestamp, not last ROW timestamp
        # (last row can be earlier if no state change after it)
        from datetime import datetime
        _fmt = "%Y.%m.%d %H:%M"
        _dt_start = datetime.strptime(start[:16], _fmt)
        _dt_end = datetime.strptime(end[:16], _fmt)
        _dt_last_data = datetime.strptime(m15_ts_list[-1], _fmt)
        _gap_min = (_dt_end - _dt_last_data).total_seconds() / 60

        first_ts = rows[0]['datetime'] if rows else "N/A"
        last_row_ts = rows[-1]['datetime'] if rows else "N/A"
        print(f"  Coverage: {first_ts} -> {last_row_ts} (period: {start[:16]} -> {end[:16]})")

        # Known non-trading days in 2026 (weekends + holidays)
        _nontrading = {
            "2026.01.03", "2026.01.04",  # Sat/Sun
            "2026.02.07", "2026.02.08",  # Sat/Sun
            "2026.04.03", "2026.04.04", "2026.04.05", "2026.04.06",  # Good Fri + Easter
        }
        _end_date = end[:10]
        _is_nontrading = _end_date in _nontrading

        if _gap_min <= 15:
            print(f"  Coverage: COMPLETE (last data {m15_ts_list[-1]}, {int(_gap_min)}min before period end)")
        elif _is_nontrading:
            print(f"  Coverage: INCOMPLETE — period ends on non-trading day ({_end_date}), last data {m15_ts_list[-1]}")
        else:
            print(f"  Coverage: INCOMPLETE — no data after {m15_ts_list[-1]} ({int(_gap_min)}min before period end)")

if __name__ == "__main__":
    main()
