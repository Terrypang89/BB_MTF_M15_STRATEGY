#!/usr/bin/env python3
"""Scan V30.02 log for H4-SQZ episodes outside March 2026.

An H4-SQZ episode:
  1. H4 enters SQZ (stage 400-499) — onset
  2. H4 remains in SQZ or briefly exits to adjacent fly/shrink
  3. H4 resolves — G (direction pivot) or F (expansion continuation)

We scan at H4 boundaries (00:00, 04:00, 08:00, 12:00, 16:00, 20:00).
Episode = contiguous SQZ blocks (separated by <= 2 non-SQZ bars).
"""

import re
import json
from pathlib import Path

LOG_PATH = Path(__file__).parent.parent / "references" / "Backtest_data" / "V30.02" / "20260606_clean.log"
MARCH_START = "2026.03.02"
MARCH_END = "2026.03.20"

H4_HOURS = {"00", "04", "08", "12", "16", "20"}

def parse_tf_line(line, tf_name):
    r = {}
    m = re.search(rf'W_stage_{tf_name}:\((\w+)\)\[([^\]]+)\]', line)
    if m:
        vals = [int(x.strip()) for x in m.group(2).split(',') if x.strip()]
        r['stage'] = vals[0] if vals else None
    m = re.search(rf'diffMid_Trend_{tf_name}:\[([^\]]+)\]', line)
    if m:
        vals = [float(x.strip()) for x in m.group(1).split(',') if x.strip()]
        r['mid'] = int(vals[0]) if vals else None
    m = re.search(rf'BBUpDn_{tf_name}:\[([^\]]+)\]', line)
    if m:
        vals = [int(x.strip()) for x in m.group(1).split(',') if x.strip()]
        r['bbupdn'] = vals[0] if vals else None
    m = re.search(rf'diffBBW_{tf_name}:\[([^\]]+)\]', line)
    if m:
        vals = [float(x.strip()) for x in m.group(1).split(',') if x.strip()]
        r['diffBBW'] = vals[0] if vals else None
    return r

def is_sqz(stage):
    return 400 <= stage <= 499 if stage else False

def is_fly(stage):
    return stage in (511, 512, 521, 522) if stage else False

def is_shrink(stage):
    return stage in (513, 523) if stage else False

def classify_resolution(last_sqz_stage, first_out_stage, first_out_dbbw, first_out_mid, first_out_bbupdn):
    """Classify how a SQZ episode resolved."""
    if first_out_dbbw is not None and first_out_dbbw > 15 and first_out_bbupdn == 1:
        return 'F'  # explosive expansion — F-tier
    if is_fly(first_out_stage):
        if first_out_dbbw is not None and first_out_dbbw > 5:
            return 'F'  # fly with positive diffBBW — expansion
        return 'G'  # fly from SQZ — direction pivot
    if is_shrink(first_out_stage):
        return 'G'  # shrink from SQZ — compression pivot
    return 'U'  # unknown

def main():
    h4_state = {}
    boundaries = []

    with open(LOG_PATH, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    for line in lines:
        line = line.strip()
        if not line:
            continue
        m = re.match(r'(\d{4}\.\d{2}\.\d{2}) (\d{2}:\d{2}:\d{2})', line)
        if not m:
            continue

        date_str = m.group(1)
        time_str = m.group(2)
        hour = time_str[:2]
        minute = time_str[3:5]

        if MARCH_START <= date_str <= MARCH_END:
            continue

        if '[H4]' in line:
            h4_state = parse_tf_line(line, 'H4')

        if '[ORDERINFO]' in line and hour in H4_HOURS and minute == "00":
            boundaries.append({
                'time': f"{date_str} {time_str}",
                'stage': h4_state.get('stage'),
                'mid': h4_state.get('mid'),
                'diffBBW': h4_state.get('diffBBW'),
                'bbupdn': h4_state.get('bbupdn'),
            })

    # Identify SQZ episodes — contiguous blocks of SQZ bars
    # (allowing brief gaps of <= 2 non-SQZ bars within the episode)
    episodes = []
    current_episode = None
    gap_count = 0

    for i, b in enumerate(boundaries):
        sqz = is_sqz(b['stage'])

        if sqz:
            if current_episode is None:
                # New episode starts
                current_episode = {
                    'onset_time': b['time'],
                    'onset_stage': b['stage'],
                    'onset_mid': b['mid'],
                    'onset_diffBBW': b['diffBBW'],
                    'sqz_bars': 1,
                    'total_bars': 1,
                    'gap_bars': 0,
                    'boundaries': [b],
                    'resolution': None,
                    'resolution_time': None,
                }
            else:
                current_episode['sqz_bars'] += 1
                current_episode['total_bars'] += 1
                current_episode['boundaries'].append(b)
                gap_count = 0  # reset gap
        else:
            if current_episode is not None:
                gap_count += 1
                current_episode['total_bars'] += 1
                current_episode['gap_bars'] = gap_count
                current_episode['boundaries'].append(b)

                if gap_count >= 3:
                    # Episode ended — too many non-SQZ bars
                    # Resolution = this bar (first bar after gap)
                    last_sqz_boundary = None
                    for j in range(len(current_episode['boundaries']) - 1, -1, -1):
                        if is_sqz(current_episode['boundaries'][j]['stage']):
                            last_sqz_boundary = current_episode['boundaries'][j]
                            break
                    current_episode['resolution'] = classify_resolution(
                        last_sqz_boundary['stage'] if last_sqz_boundary else None,
                        b['stage'], b['diffBBW'], b['mid'], b['bbupdn']
                    )
                    current_episode['resolution_time'] = b['time']
                    current_episode['resolution_stage'] = b['stage']
                    current_episode['resolution_diffBBW'] = b['diffBBW']
                    episodes.append(current_episode)
                    current_episode = None
                    gap_count = 0

    # Handle open episode at end of data
    if current_episode is not None:
        current_episode['resolution'] = 'OPEN'
        current_episode['resolution_time'] = current_episode['boundaries'][-1]['time']
        episodes.append(current_episode)

    # ── Report ──────────────────────────────────────────────────────
    print(f"{'='*80}")
    print(f"OOS H4-SQZ EPISODE SCAN")
    print(f"Data: V30.02 log, excluding March 2-20")
    print(f"Total H4 boundaries scanned: {len(boundaries)}")
    print(f"Episode definition: contiguous SQZ blocks (gaps <= 2 bars)")
    print(f"{'='*80}")

    print(f"\n{'#':<4} {'Onset Time':<18} {'SQZ Bars':<10} {'Total Bars':<12} {'Resolution':<12} {'Resolve Time':<18} {'Resolve Stg':<10} {'Resolve dBBW':<12}")
    print('-' * 110)

    for i, ep in enumerate(episodes):
        res = ep['resolution'] or '?'
        res_time = ep.get('resolution_time', 'N/A') or 'N/A'
        res_stg = ep.get('resolution_stage', '?') or '?'
        res_dbbw = ep.get('resolution_diffBBW', '?')
        if res_dbbw is not None and isinstance(res_dbbw, (int, float)):
            res_dbbw = f"{res_dbbw:+.1f}"
        else:
            res_dbbw = '?'
        print(f"{i+1:<4} {ep['onset_time']:<18} {ep['sqz_bars']:<10} "
              f"{ep['total_bars']:<12} {res:<12} {res_time:<18} "
              f"{res_stg:<10} {res_dbbw:<12}")

    print(f"\n--- Summary ---")
    g_count = sum(1 for ep in episodes if ep['resolution'] == 'G')
    f_count = sum(1 for ep in episodes if ep['resolution'] == 'F')
    u_count = sum(1 for ep in episodes if ep['resolution'] in ('U', 'OPEN'))
    print(f"  Total episodes: {len(episodes)}")
    print(f"  G (direction pivot): {g_count}")
    print(f"  F (expansion continuation): {f_count}")
    print(f"  Unknown/Open: {u_count}")

    if g_count > 0 and f_count > 0:
        print(f"\n  VERDICT: Mixed G/F resolution — OOS CAN validate G/F macro design")
    elif g_count + f_count >= 3:
        print(f"\n  VERDICT: {g_count+f_count} resolved episodes but single-direction resolution")
        print(f"  OOS will only test one side of G/F — partial validation at best")
    elif g_count + f_count < 3:
        print(f"\n  VERDICT: Too few resolved G/F episodes ({g_count+f_count}) — OOS CANNOT validate G/F")
        print(f"  Need a different period or cascade-model redesign")

    # ── Detail: SQZ bar timeline ────────────────────────────────────
    print(f"\n{'='*80}")
    print(f"H4 STAGE TIMELINE (SQZ bars marked *)")
    print(f"{'='*80}")

    print(f"\n{'Time':<20} {'Stage':<8} {'Mid':<6} {'BBUpDn':<8} {'diffBBW':<12} {'State':<8}")
    print('-' * 70)

    for b in boundaries:
        stg = b['stage'] or '?'
        mid = b['mid'] or '?'
        bbupdn = b['bbupdn'] or '?'
        dbbw = b['diffBBW']
        if dbbw is not None:
            dbbw_str = f"{dbbw:+.1f}"
        else:
            dbbw_str = '?'

        stg_num = stg if isinstance(stg, int) else None
        if is_sqz(stg_num):
            state = 'SQZ*'
        elif is_fly(stg_num):
            state = 'FLY'
        elif is_shrink(stg_num):
            state = 'SHR'
        else:
            state = 'UNK'

        print(f"{b['time']:<20} {str(stg):<8} {str(mid):<6} {str(bbupdn):<8} {dbbw_str:<12} {state:<8}")

    # Write episode data to file
    out_path = Path(__file__).parent.parent / "references" / "fixtures" / "oos_episodes.json"
    serializable = []
    for ep in episodes:
        entry = {
            'onset_time': ep['onset_time'],
            'onset_stage': ep['onset_stage'],
            'onset_mid': ep['onset_mid'],
            'onset_diffBBW': ep['onset_diffBBW'],
            'sqz_bars': ep['sqz_bars'],
            'total_bars': ep['total_bars'],
            'gap_bars': ep['gap_bars'],
            'resolution': ep['resolution'],
            'resolution_time': ep.get('resolution_time'),
            'resolution_stage': ep.get('resolution_stage'),
            'resolution_diffBBW': ep.get('resolution_diffBBW'),
        }
        serializable.append(entry)
    with open(out_path, 'w') as f:
        json.dump(serializable, f, indent=2)
    print(f"\nEpisode data written to {out_path}")

if __name__ == '__main__':
    main()
