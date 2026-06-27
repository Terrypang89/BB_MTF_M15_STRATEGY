#!/usr/bin/env python3
"""Rebuild IMAGE_ANALYSIS.md with event-driven state tables from V31.04 log.

Reads the log, extracts state data for each user-defined period,
and generates the new markdown with event-driven tables.
"""

import re
from pathlib import Path
from collections import defaultdict

BASE = Path(__file__).resolve().parent.parent
LOG_PATH = BASE / "references" / "Backtest_data" / "V31.04" / "20260620_clean.log"
MD_PATH = BASE / "references" / "IMAGE_ANALYSIS.md"

TF_NAMES = ["M15", "M30", "H1", "H4", "D1", "W1"]

# Block definitions: (scenario_heading, image_num, filename, period_start, period_end)
BLOCKS = [
    ("Scenario F (Full Fly)", 1, "backtested_EA_fly_scenario.jpg",
     "2026.01.02 01:00", "2026.01.03 04:00"),
    ("Scenario F (Full Fly)", 2, "backtested_EA_predict_trend_1.jpg",
     "2026.04.01 13:00", "2026.04.01 17:00"),
    ("Scenario F (Full Fly)", 3, "LTH_drive_fly.jpg",
     "2026.01.02 01:00", "2026.01.03 04:00"),
    ("Scenario S (Shrink)", 1, "backtested_EA_fly_2_fly_shrink.jpg",
     "2026.03.30 13:00", "2026.04.01 13:00"),
    ("Scenario S (Shrink)", 2, "backtested_EA_fly_2_fly_shrink_zoomin.jpg",
     "2026.03.30 14:30", "2026.04.01 09:00"),
    ("Scenario S (Shrink)", 3, "backtested_EA_b_to_e_to_g_progression.jpg",
     "2026.03.30 13:00", "2026.04.01 17:00"),
    ("Scenario P (Rest Recovery / Pause)", 1, "backtested_EA_fly_2_shrink_2_fly.jpg",
     "2026.04.03 03:00", "2026.04.05 00:00"),
    ("Scenario P (Rest Recovery / Pause)", 2, "backtested_EA_fly_2_shrink_2_fly_zoomin.jpg",
     "2026.04.04 15:00", "2026.04.05 00:00"),
    ("Scenario R (Reversal)", 1, "backtested_EA_trend_reversal.jpg",
     "2026.04.01 14:30", "2026.04.02 05:00"),
    ("Scenario R (Reversal)", 2, "backtested_EA_test_phase_April_01.jpg",
     "2026.04.01 14:30", "2026.04.02 09:00"),
    ("Scenario B (Compression Release / Breakout)", 1, "backtested_EA_sideway_2_fly.jpg",
     "2026.02.06 01:00", "2026.02.07 21:00"),
    ("Scenario B (Compression Release / Breakout)", 2, "backtested_EA_sideway_2_fly_zoomin.jpg",
     "2026.02.06 13:00", "2026.02.07 09:00"),
    ("Scenario B (Compression Release / Breakout)", 3, "backtest_EA_sideway_2_fly2_zoomin.jpg",
     "2026.02.06 13:00", "2026.02.07 09:00"),
    ("Scenario V (Direction Pivot)", 1, "backtested_EA_fly_shrink_2_sideway2.jpg",
     "2026.04.02 05:00", "2026.04.03 03:00"),
    ("Scenario C (Deep Compression)", 1, "backtested_EA_fly_shrink_2_sideway.jpg",
     "2026.04.01 13:00", "2026.04.02 17:00"),
    ("Scenario C (Deep Compression)", 2, "backtested_EA_fly_shrink_2_sideway_zoomin.jpg",
     "2026.04.02 09:00", "2026.04.02 17:00"),
    ("Scenario C (Deep Compression)", 3, "backtested_EA_phase_3a_symmetric.jpg",
     "2026.04.01 17:00", "2026.04.02 05:00"),
    ("Scenario C (Deep Compression)", 4, "backtested_EA_phase_3a_to_3b.jpg",
     "2026.04.02 05:00", "2026.04.02 17:00"),
    ("Scenario C (Deep Compression)", 5, "backtested_EA_phase_3b_asymmetric.jpg",
     "2026.04.02 10:00", "2026.04.02 17:00"),
    ("Scenario C (Deep Compression)", 6, "backtested_EA_phase_3b_out_recovery.jpg",
     "2026.04.02 17:00", "2026.04.03 03:00"),
    ("Scenario C (Deep Compression)", 7, "backtested_EA_phase_6_post_sqz_oscillation.jpg",
     "2026.04.03 03:00", "2026.04.03 17:00"),
]

# Group blocks by scenario
SCENARIOS_ORDER = []
SCENARIO_BLOCKS = defaultdict(list)
for block in BLOCKS:
    scenario = block[0]
    if scenario not in SCENARIO_BLOCKS:
        SCENARIOS_ORDER.append(scenario)
    SCENARIO_BLOCKS[scenario].append(block)

def parse_log(log_path):
    """Parse log into dict: { tf: { datetime_str: {stage, diffMid, BBUpDn} } }"""
    data = {tf: {} for tf in TF_NAMES}
    with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
        for line in f:
            for tf in TF_NAMES:
                if f'[{tf}]' not in line:
                    continue
                m_ts = re.match(r'(2026\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2})', line)
                if not m_ts:
                    continue
                ts = m_ts.group(1)
                m_st = re.search(rf'W_stage_{tf}:\((\w+)\)\[([^\]]+)\]', line)
                if not m_st:
                    continue
                stage = int(m_st.group(2).split(',')[0].strip())
                m_dm = re.search(rf'diffMid_Trend_{tf}:\[([^\]]+)\]', line)
                diffMid = None
                if m_dm:
                    diffMid = float(m_dm.group(1).split(',')[0].strip())
                m_bu = re.search(rf'BBUpDn_{tf}:\[([^\]]+)\]', line)
                bbupdn = None
                if m_bu:
                    bbupdn = int(m_bu.group(1).split(',')[0].strip())
                data[tf][ts] = {'stage': stage, 'diffMid': diffMid, 'BBUpDn': bbupdn}
    return data

def ts_in_range(ts, start, end):
    ts_dt = ts[:16]
    start_dt = start[:16]
    end_dt = end[:16]
    return start_dt <= ts_dt <= end_dt

def round_down_to_m15(ts):
    return ts[:16]

def get_state_at_tf(data, tf, ts):
    ts_target = ts
    best = None
    for log_ts, state in data[tf].items():
        log_ts_rounded = round_down_to_m15(log_ts)
        if log_ts_rounded <= ts_target:
            if best is None or log_ts_rounded > best[0]:
                best = (log_ts_rounded, state)
        else:
            break
    return best[1] if best else None

def abs_minutes(ts1, ts2):
    """Absolute minutes between two 'YYYY.MM.DD HH:MM' strings."""
    from datetime import datetime
    fmt = "%Y.%m.%d %H:%M"
    dt1 = datetime.strptime(ts1, fmt)
    dt2 = datetime.strptime(ts2, fmt)
    return abs((dt2 - dt1).total_seconds()) / 60

def get_m15_timestamps_in_period(data, start, end):
    m15_ts = set()
    for ts in data["M15"].keys():
        if ts_in_range(ts, start, end):
            m15_ts.add(round_down_to_m15(ts))
    return sorted(m15_ts)

def cell_format(stage, diffmid, bbupdn):
    if stage is None:
        return "[TO BE FILLED]"
    dm = int(diffmid) if diffmid is not None else "?"
    bu = bbupdn if bbupdn is not None else "?"
    return f"{stage}-{dm}-{bu}"

def safe_get(s, key, default=0):
    if s is None:
        return default
    return s.get(key, default)

def derive_scenario(htf_states, mtf_states):
    def sg(d, key, default=0):
        return safe_get(d, key, default)

    m15_s = sg(mtf_states.get('M15'), 'stage', 0)
    m30_s = sg(mtf_states.get('M30'), 'stage', 0)
    h1_s = sg(mtf_states.get('H1'), 'stage', 0)
    m15_dm = sg(mtf_states.get('M15'), 'diffMid', 0) or 0
    m30_dm = sg(mtf_states.get('M30'), 'diffMid', 0) or 0
    h1_dm = sg(mtf_states.get('H1'), 'diffMid', 0) or 0

    h4_s = sg(htf_states.get('H4'), 'stage', 0)
    h4_dm = sg(htf_states.get('H4'), 'diffMid', 0) or 0

    mtf_scenario = "F"
    if any(s in (513, 523) for s in [m15_s, m30_s, h1_s]):
        if m15_s in (513, 523) and m30_s in (513, 523) and h1_s in (513, 523):
            mtf_scenario = "S3"
        elif m15_s in (513, 523) and m30_s in (513, 523):
            mtf_scenario = "S2"
        elif m15_s in (513, 523):
            mtf_scenario = "S1"
    elif any(400 <= s <= 499 for s in [m15_s, m30_s, h1_s] if s):
        if all(400 <= s <= 499 for s in [m15_s, m30_s] if s):
            mtf_scenario = "C2"
        elif (400 <= m15_s <= 499):
            mtf_scenario = "C1"
    elif (h4_dm == 1.0 and any(dm == 2.0 for dm in [m15_dm, m30_dm, h1_dm])) or \
         (h4_dm == 2.0 and any(dm == 1.0 for dm in [m15_dm, m30_dm, h1_dm])):
        mtf_scenario = "R1"

    d1_s = sg(htf_states.get('D1'), 'stage', 0)
    d1_dm = sg(htf_states.get('D1'), 'diffMid', 0) or 0
    w1_s = sg(htf_states.get('W1'), 'stage', 0)
    w1_dm = sg(htf_states.get('W1'), 'diffMid', 0) or 0

    htf_scenario = "F"
    if h4_s and 400 <= h4_s <= 499:
        htf_scenario = "V1"
    elif h4_s and h4_s in (513, 523):
        htf_scenario = "C4"
    elif h4_s:
        if d1_s == 0 or w1_s == 0:
            htf_scenario = "F"
        elif h4_dm == d1_dm == w1_dm and h4_dm in (1.0, 2.0):
            htf_scenario = "F1"
        elif h4_dm == d1_dm or h4_dm == w1_dm:
            htf_scenario = "F2"
        else:
            htf_scenario = "F3"

    divergence = False
    if h4_dm in (1.0, 2.0):
        for tf_dm in [m15_dm, m30_dm, h1_dm]:
            if tf_dm == 3 - h4_dm:
                divergence = True
                break

    return htf_scenario, mtf_scenario, divergence

def derive_trend_tier(htf_states):
    h4_dm = (safe_get(htf_states.get('H4'), 'diffMid', 0) or 0)
    d1_dm = (safe_get(htf_states.get('D1'), 'diffMid', 0) or 0)
    h4_s = (safe_get(htf_states.get('H4'), 'stage', 0) or 0)

    if h4_dm == 1.0 and d1_dm == 1.0:
        trend = "Up"
    elif h4_dm == 2.0 and d1_dm == 2.0:
        trend = "Down"
    elif h4_dm == 1.0 and d1_dm == 2.0:
        trend = "Up (div)"
    elif h4_dm == 2.0 and d1_dm == 1.0:
        trend = "Down (div)"
    elif h4_dm in (3.0, 4.0, 5.0):
        trend = "Sideways"
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

def generate_table(scenario_label, image_num, filename, start, end, data):
    """Generate the event-driven table for a block."""
    m15_ts_list = get_m15_timestamps_in_period(data, start, end)

    if not m15_ts_list:
        return f"  > **No log data available for this period.**\n"

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

        if (m15['stage'] != prev_m15_stage or
            m15['diffMid'] != prev_m15_diffmid):
            cells = {}
            for tf in TF_NAMES:
                s = states[tf]
                cells[tf] = cell_format(
                    s['stage'] if s else None,
                    s['diffMid'] if s else None,
                    s['BBUpDn'] if s else None,
                )

            htf_states = {k: states.get(k) for k in ['H4', 'D1', 'W1']}
            mtf_states = {k: states.get(k) for k in ['M15', 'M30', 'H1']}
            htf_sc, mtf_sc, div = derive_scenario(htf_states, mtf_states)
            trend_tier = derive_trend_tier(htf_states)

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

    if not rows:
        return f"  > **No state transitions detected in this period.**\n"

    # Build markdown
    lines = []
    lines.append("> **Cell = BBW_stage-diffMid-BBUpDn** (e.g. 511-1-1). BBW: 511/512=up-fly,")
    lines.append("> 521/522=down-fly, 513/523=shrink, 4xx=SQZ. diffMid: 1=up, 2=down,")
    lines.append("> 3=sideways, 5=deep-sideways. BBUpDn: 0=between, 1=upper, 2=lower,")
    lines.append("> 3=sideways. A new row is added only when M15 BBW_stage or diffMid changes.")
    lines.append("> All rows fall within the user-defined period.")
    lines.append("")
    lines.append("| datetime | M15 | M30 | H1 | H4 | D1 | W1 | Scenario (HTF-MTF) | Trend / Tier |")
    lines.append("|----------|-----|-----|----|----|----|----|--------------------|------------|")
    for row in rows:
        c = row['cells']
        lines.append(f"| {row['datetime']} | {c['M15']} | {c['M30']} | {c['H1']} | {c['H4']} | {c['D1']} | {c['W1']} | {row['scenario']} | {row['trend_tier']} |")
    lines.append("")

    # Coverage check — table must reach period end (within 15 min tolerance)
    first_ts = rows[0]['datetime']
    last_ts = rows[-1]['datetime']
    end_dt = end[:16]
    # Allow 15-minute tolerance: last row within 15 min of period end
    coverage_ok = first_ts >= start[:16] and (last_ts >= end_dt or abs_minutes(last_ts, end_dt) <= 15)
    status = "COMPLETE" if coverage_ok else "INCOMPLETE"
    lines.append(f"**Coverage:** {first_ts} → {last_ts} | Period: {start} → {end} | **{status}**")
    lines.append("")

    return "\n".join(lines)

def main():
    print(f"Parsing log: {LOG_PATH}")
    data = parse_log(LOG_PATH)
    for tf in TF_NAMES:
        print(f"  {tf}: {len(data[tf])} entries")

    # Read existing file to get the DESIGN REFERENCE section
    with open(MD_PATH, 'r', encoding='utf-8') as f:
        existing = f.read()

    # Extract original Period lines (preserve them exactly)
    period_lines = re.findall(r'\*\*Period:\*\*.*', existing)

    # Extract DESIGN REFERENCE section (everything from ## HTF to the first ## Scenario)
    design_match = re.search(
        r'(## HTF / MTF Two-Axis Reading.*?)(?=## Scenario |\n---\n\n## Scenario )',
        existing, re.DOTALL
    )
    design_section = design_match.group(1).strip() if design_match else ""

    # Extract illustrative images section
    illustrative_match = re.search(
        r'(## Illustrative Images.*?)(?=\n---\n## |\n## Scenario Coverage|$)',
        existing, re.DOTALL
    )
    illustrative_section = illustrative_match.group(1).strip() if illustrative_match else ""
    # Strip trailing --- and blank lines
    while illustrative_section and (illustrative_section.rstrip().endswith('---') or
                                    illustrative_section.rstrip().endswith('\n')):
        illustrative_section = illustrative_section.rstrip()
        if illustrative_section.endswith('---'):
            illustrative_section = illustrative_section[:-3].rstrip()

    # Build the new content
    output_lines = []
    output_lines.append("# Image Analysis Blocks")
    output_lines.append("")
    output_lines.append("Companion to `backtest_chart_analysis.md` — Part 3 image-analysis blocks have been separated from the scenario definitions into this document. The scenario definitions (Cascade Position, Sub-Scenarios, Sub-State Flowchart, Identification Flowchart, Trade action) remain in `backtest_chart_analysis.md`.")
    output_lines.append("")
    output_lines.append("Each block contains an event-driven state table derived from the backtest log (`references/Backtest_data/V31.04/20260620_clean.log`). States are `[TO BE FILLED]` where the log has no data for that TF at the given time.")
    output_lines.append("")
    output_lines.append("---")
    output_lines.append("")

    # DESIGN REFERENCE section
    output_lines.append(design_section)
    output_lines.append("")
    output_lines.append("---")
    output_lines.append("")

    # Track scenarios for coverage matrix
    all_scenarios = set()

    # Generate blocks by scenario
    period_idx = 0  # Track which Period line to use
    for scenario in SCENARIOS_ORDER:
        output_lines.append(f"## {scenario}")
        output_lines.append("")

        for block in SCENARIO_BLOCKS[scenario]:
            scenario_label, image_num, filename, start, end = block
            image_tag = filename.replace('.jpg', '')

            output_lines.append(f"#### Image {image_num} Analysis — {filename}")
            output_lines.append(f"![{image_tag}](./Backtest_data/extras/{filename})")
            output_lines.append("")
            # Use original Period line if available
            if period_idx < len(period_lines):
                output_lines.append(period_lines[period_idx])
                period_idx += 1
            else:
                output_lines.append(f"**Period:** {start[:10]} {start[11:]} → {end[:10]} {end[11:]}")
            output_lines.append("")

            table_md = generate_table(scenario_label, image_num, filename, start, end, data)
            output_lines.append(table_md)

            # Track scenarios from table
            if table_md:
                for line in table_md.split('\n'):
                    if '| ' in line and 'Scenario' not in line:
                        parts = line.split('|')
                        if len(parts) >= 9:
                            sc = parts[8].strip().rstrip(' |')
                            # Extract base scenario (without [divergence])
                            sc_clean = sc.replace(' [divergence]', '').strip()
                            if '-' in sc_clean and sc_clean != '---':
                                all_scenarios.add(sc_clean)

        output_lines.append("---")
        output_lines.append("")

    # Illustrative images
    if illustrative_section:
        output_lines.append(illustrative_section)
        output_lines.append("")

    # Build coverage matrix
    output_lines.append("## Scenario Coverage")
    output_lines.append("")
    output_lines.append("| Scenario | Sub-states | Present? | Image(s) | Missing sub-states |")
    output_lines.append("|----------|-----------|----------|----------|--------------------|")

    # Check each sub-state
    SUBSTATES = {
        "F (Fly)": ["F1", "F2", "F3"],
        "S (Shrink)": ["S1", "S2", "S3"],
        "C (Compress)": ["C1", "C2", "C3", "C4"],
        "P (Pause)": ["P1", "P2", "P3"],
        "B (Breakout)": ["B1", "B2", "B3"],
        "R (Reversal)": ["R1", "R2", "R3"],
        "V (Pivot)": ["V1", "V2", "V3", "V4"],
    }

    missing_all = []
    for scenario_name, subs in SUBSTATES.items():
        present = []
        missing = []
        for sub in subs:
            # Check if sub appears in any HTF or MTF position
            found = False
            for sc in all_scenarios:
                parts = sc.split('-')
                if len(parts) == 2 and parts[0] == sub:
                    found = True
                    break
                if len(parts) == 2 and parts[1] == sub:
                    found = True
                    break
            if found:
                present.append(sub)
            else:
                missing.append(sub)

        present_str = "Yes" if present else "No"
        images_str = ", ".join(present) if present else "—"
        missing_str = ", ".join(missing) if missing else "—"
        output_lines.append(f"| {scenario_name} | {', '.join(subs)} | {present_str} | {images_str} | {missing_str} |")

        for m in missing:
            missing_all.append(m)

    output_lines.append("")
    if missing_all:
        output_lines.append(f"**Gap summary:** Missing sub-states with no chart example: {', '.join(missing_all)}.")
    else:
        output_lines.append("**Gap summary:** All sub-states are represented by at least one chart.")
    output_lines.append("")

    # Write output
    output = "\n".join(output_lines)
    with open(MD_PATH, 'w', encoding='utf-8') as f:
        f.write(output)

    print(f"\nWritten {len(output_lines)} lines to {MD_PATH}")
    print(f"Total scenarios observed: {sorted(all_scenarios)}")

if __name__ == "__main__":
    main()
