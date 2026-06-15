#!/usr/bin/env python3
"""Run the locked harness against OOS data (Jan-Feb + April 2026).

This script:
1. Extracts snapshots from V30.02 log for OOS periods (excluding March 2-20)
2. Runs the same identify_scenario() from the locked harness
3. Evaluates G/F macro design on H4-compression episodes
4. Reports overall match % and G/F-specific performance

NO TUNING — this is a pure test.
"""

import sys
from pathlib import Path

# Import the locked harness functions
sys.path.insert(0, str(Path(__file__).parent))
from replay_harness import (
    parse_tf_line, identify_scenario, identify_phase,
    derive_cascade, is_sqz, is_fly, is_shrink, TF_INDEX, CASCADE_TFS,
    LOG_PATH,
)

import re
# ── OOS date ranges ────────────────────────────────────────────────────
# Jan 1 - Feb 27 (before March fixture) + April 1 - April 29 (after March fixture)
OOS_RANGES = [
    ("2026.01.01", "2026.02.27"),
    ("2026.04.01", "2026.04.29"),
]

H4_HOURS = {"00", "04", "08", "12", "16", "20"}

def oos_parse_log():
    """Parse the clean log for OOS periods only."""
    tf_states = {tf: {} for tf in ['M5', 'M15', 'M30', 'H1', 'H4', 'D1', 'W1']}
    snapshots = []
    diffbbw_h4_history = []
    prev_h1_sqz = False
    captured_h4 = set()
    trade_events = []

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

        # Check if this date falls in an OOS range
        in_oos = False
        for start, end in OOS_RANGES:
            if start <= date_str <= end:
                in_oos = True
                break
        if not in_oos:
            # Still need to parse TF states for continuity? No —
            # each snapshot is self-contained with its own diffbbw history
            # But we need to reset state at range boundaries
            continue

        current_time = f"{date_str} {time_str}"

        # Parse TF blocks
        for tf in ['M5', 'M15', 'M30', 'H1', 'H4', 'D1', 'W1']:
            if f'[{tf}]' in line:
                tf_states[tf] = parse_tf_line(line, tf)

        # Track trade events
        if '[NEW_ORDER_OPEN]' in line or '[NEW_ORDER_CLOSE]' in line:
            trade_events.append({'time': current_time, 'line': line})

        # Capture at H4 boundaries
        if '[ORDERINFO]' in line and hour in H4_HOURS and minute == "00":
            boundary_key = f"{date_str}_{hour}"
            if boundary_key not in captured_h4:
                captured_h4.add(boundary_key)

                h4_dbbw = tf_states.get('H4', {}).get('diffBBW')
                if h4_dbbw is not None:
                    diffbbw_h4_history.append(h4_dbbw)

                snap = {
                    'time': current_time,
                    'tf_states': {tf: dict(tf_states[tf]) for tf in ['M5'] + CASCADE_TFS + ['W1']},
                    'diffbbw_h4_history': list(diffbbw_h4_history),
                    'trade_event': '',
                    'prev_h1_sqz': prev_h1_sqz,
                }
                snapshots.append(snap)

                h1_stg = tf_states.get('H1', {}).get('stage', 0)
                prev_h1_sqz = (400 <= h1_stg <= 499) if h1_stg else False

        # Capture at trade events
        if '[NEW_ORDER_OPEN]' in line or '[NEW_ORDER_CLOSE]' in line:
            h4_dbbw = tf_states.get('H4', {}).get('diffBBW')
            if h4_dbbw is not None:
                diffbbw_h4_history.append(h4_dbbw)

            te = ''
            if 'NEW_ORDER_CLOSE' in line:
                profit_m = re.search(r'PROFIT:([-\d.]+)', line)
                type_m = re.search(r'OPEN_Type:(\w+)', line)
                te = f"CLOSE {type_m.group(1)}" + (f" P&L:{profit_m.group(1)}" if profit_m else '')
            if 'NEW_ORDER_OPEN' in line:
                type_m = re.search(r'OPEN_TYPE:(\w+)', line)
                te = f"OPEN {type_m.group(1)}" if type_m else 'OPEN'

            snap = {
                'time': current_time,
                'tf_states': {tf: dict(tf_states[tf]) for tf in ['M5'] + CASCADE_TFS + ['W1']},
                'diffbbw_h4_history': list(diffbbw_h4_history),
                'trade_event': te,
                'prev_h1_sqz': prev_h1_sqz,
            }
            snapshots.append(snap)

    snapshots.sort(key=lambda x: x['time'])
    return snapshots

# ── Episode tracking ───────────────────────────────────────────────────

def identify_h4_sqz_episodes(snapshots):
    """Identify H4-SQZ episodes in the snapshot stream."""
    episodes = []
    in_episode = False
    episode = None
    gap_count = 0

    for snap in snapshots:
        h4_stg = snap['tf_states'].get('H4', {}).get('stage', 0)
        sqz = is_sqz(h4_stg)

        if sqz:
            if not in_episode:
                episode = {
                    'onset_time': snap['time'],
                    'onset_stage': h4_stg,
                    'snapshots': [],
                    'sqz_count': 0,
                }
                in_episode = True
                gap_count = 0
            episode['snapshots'].append(snap)
            episode['sqz_count'] += 1
            gap_count = 0
        else:
            if in_episode:
                gap_count += 1
                episode['snapshots'].append(snap)
                if gap_count >= 3:
                    episode['end_time'] = snap['time']
                    episode['end_stage'] = h4_stg
                    episodes.append(episode)
                    in_episode = False
                    episode = None
                    gap_count = 0

    if in_episode and episode:
        episode['end_time'] = episode['snapshots'][-1]['time']
        episode['end_stage'] = episode['snapshots'][-1]['tf_states'].get('H4', {}).get('stage', 0)
        episodes.append(episode)

    return episodes

def classify_episode_resolution(episode):
    """Classify G vs F resolution for an episode."""
    # Look at the exit from SQZ — first non-SQZ bar after SQZ
    last_sqz_snap = None
    first_out_snap = None
    for snap in episode['snapshots']:
        h4_stg = snap['tf_states'].get('H4', {}).get('stage', 0)
        if is_sqz(h4_stg):
            last_sqz_snap = snap
        elif first_out_snap is None and not is_sqz(h4_stg):
            first_out_snap = snap

    if not first_out_snap:
        return 'OPEN', ''

    out_stg = first_out_snap['tf_states'].get('H4', {}).get('stage', 0)
    out_dbbw = first_out_snap['tf_states'].get('H4', {}).get('diffBBW', 0)
    out_bbupdn = first_out_snap['tf_states'].get('H4', {}).get('bbupdn', 0)

    if out_dbbw is not None and out_dbbw > 15 and out_bbupdn == 1:
        return 'F', 'explosive expansion'
    if is_fly(out_stg):
        if out_dbbw is not None and out_dbbw > 5:
            return 'F', 'fly with positive diffBBW'
        return 'G', 'fly from SQZ — direction pivot'
    if is_shrink(out_stg):
        return 'G', 'shrink from SQZ — compression pivot'
    return 'U', 'unknown resolution'

# ── Main ───────────────────────────────────────────────────────────────

def main():
    print("=" * 80)
    print("OOS VALIDATION — Locked Harness on Jan-Feb + April 2026")
    print("NO TUNING — pure test")
    print("=" * 80)

    # Parse OOS snapshots
    print("\nParsing OOS log...")
    snapshots = oos_parse_log()
    print(f"  Captured {len(snapshots)} snapshots")

    if not snapshots:
        print("  ERROR: No OOS snapshots — date range issue")
        return

    print(f"  First: {snapshots[0]['time']}")
    print(f"  Last:  {snapshots[-1]['time']}")

    # Run identify_scenario on all snapshots
    print("\nRunning identify_scenario on all snapshots...")
    results = []
    for snap in snapshots:
        tf_st = snap['tf_states']
        dbbw_hist = snap['diffbbw_h4_history']
        prev_h1 = snap.get('prev_h1_sqz', False)
        scenario, info, cas_shrink, cas_sqz = identify_scenario(
            tf_st, dbbw_hist, prev_h1)
        phase = identify_phase(tf_st.get('H4', {}), dbbw_hist)

        h4_stg = tf_st.get('H4', {}).get('stage', 0)
        h4_dbbw = tf_st.get('H4', {}).get('diffBBW', 0)
        h4_mid = tf_st.get('H4', {}).get('mid', 0)
        h4_bbupdn = tf_st.get('H4', {}).get('bbupdn', 0)

        short_ts = snap['time'][5:7] + '.' + snap['time'][8:10] + ' ' + snap['time'][11:16]

        results.append({
            'time': short_ts,
            'scenario': scenario,
            'phase': phase,
            'info': info,
            'cas_shrinkTF': cas_shrink,
            'cas_sqzCount': cas_sqz,
            'h4_stage': h4_stg,
            'h4_diffBBW': h4_dbbw,
            'h4_mid': h4_mid,
            'h4_bbupdn': h4_bbupdn,
            'trade_event': snap.get('trade_event', ''),
            'h4_sqz': is_sqz(h4_stg),
            'h4_fly': is_fly(h4_stg),
            'h4_shrink': is_shrink(h4_stg),
        })

    # Scenario distribution
    from collections import Counter
    scenario_counts = Counter(r['scenario'] for r in results)
    print(f"\n  Scenario distribution ({len(results)} snapshots):")
    for sc, cnt in sorted(scenario_counts.items()):
        pct = cnt / len(results) * 100
        print(f"    {sc}: {cnt} ({pct:.1f}%)")

    # ── G/F-specific analysis ────────────────────────────────────────
    print("\n" + "=" * 80)
    print("G/F MACRO DESIGN — OOS Episode Analysis")
    print("=" * 80)

    episodes = identify_h4_sqz_episodes(snapshots)
    print(f"\n  H4-SQZ episodes in OOS: {len(episodes)}")

    for i, ep in enumerate(episodes):
        res, res_reason = classify_episode_resolution(ep)
        print(f"\n  Episode {i+1}:")
        print(f"    Onset: {ep['onset_time']} (H4 stage={ep['onset_stage']})")
        print(f"    SQZ bars: {ep['sqz_count']}")
        print(f"    Resolution: {res} — {res_reason}")
        print(f"    End: {ep['end_time']} (H4 stage={ep.get('end_stage', '?')})")

        # Show scenarios identified during this episode
        ep_scenarios = []
        for snap in ep['snapshots']:
            short_ts = snap['time'][5:7] + '.' + snap['time'][8:10] + ' ' + snap['time'][11:16]
            for r in results:
                if r['time'] == short_ts:
                    ep_scenarios.append((short_ts, r['scenario'], r['h4_stage'], r['h4_sqz']))
                    break

        print(f"    Scenarios during episode:")
        g_f_during = 0
        for ts, sc, stg, sqz in ep_scenarios:
            marker = ' *' if sqz else ''
            if sc.startswith('G') or sc.startswith('F'):
                g_f_during += 1
                print(f"      {ts}: {sc} (H4={stg}, sqz={sqz}){marker}")
            elif len(ep_scenarios) <= 10:
                print(f"      {ts}: {sc} (H4={stg}, sqz={sqz}){marker}")
            else:
                if sqz or sc.startswith('G') or sc.startswith('F'):
                    print(f"      {ts}: {sc} (H4={stg}, sqz={sqz}){marker}")

        # Count G/F identification during SQZ bars
        sqz_bars_g_f = sum(1 for ts, sc, stg, sqz in ep_scenarios
                          if sqz and (sc.startswith('G') or sc.startswith('F')))
        sqz_bars_total = sum(1 for ts, sc, stg, sqz in ep_scenarios if sqz)
        if sqz_bars_total > 0:
            print(f"    G/F identified on SQZ bars: {sqz_bars_g_f}/{sqz_bars_total} "
                  f"({sqz_bars_g_f/sqz_bars_total*100:.0f}%)")

    # Overall G/F resolution mix
    g_count = sum(1 for ep in episodes if classify_episode_resolution(ep)[0] == 'G')
    f_count = sum(1 for ep in episodes if classify_episode_resolution(ep)[0] == 'F')
    print(f"\n  G/F Resolution Mix:")
    print(f"    G (direction pivot): {g_count}")
    print(f"    F (expansion continuation): {f_count}")
    if g_count > 0 and f_count > 0:
        print(f"    => Mixed resolution — OOS CAN validate G/F")
    else:
        print(f"    => Single-direction resolution — OOS cannot fully validate G/F")

    # ── G/F identification rate ──────────────────────────────────────
    print("\n" + "=" * 80)
    print("G/F IDENTIFICATION RATE — Does the harness see G/F when it should?")
    print("=" * 80)

    # During H4-SQZ bars, what scenarios does the harness produce?
    sqz_snapshots = [r for r in results if r['h4_sqz']]
    if sqz_snapshots:
        sqz_scenario_counts = Counter(r['scenario'] for r in sqz_snapshots)
        print(f"\n  During H4-SQZ bars ({len(sqz_snapshots)} snapshots):")
        for sc, cnt in sorted(sqz_scenario_counts.items()):
            pct = cnt / len(sqz_snapshots) * 100
            print(f"    {sc}: {cnt} ({pct:.1f}%)")

        g_f_on_sqz = sum(1 for r in sqz_snapshots
                        if r['scenario'].startswith('G') or r['scenario'].startswith('F'))
        print(f"\n  G/F scenarios during H4-SQZ: {g_f_on_sqz}/{len(sqz_snapshots)} "
              f"({g_f_on_sqz/len(sqz_snapshots)*100:.1f}%)")
    else:
        print("\n  No H4-SQZ snapshots in OOS data")

    # ── Full results table ───────────────────────────────────────────
    print("\n" + "=" * 80)
    print("FULL OOS RESULTS")
    print("=" * 80)

    print(f"\n{'Time':<12} {'Scenario':<8} {'Phase':<12} {'H4 Stg':<8} {'H4 dBBW':<10} {'H4 SQZ':<8} {'Info'}")
    print("-" * 100)

    for r in results:
        ev = f" ***{r['trade_event']}" if r['trade_event'] else ""
        dbbw = r['h4_diffBBW']
        dbbw_str = f"{dbbw:+.1f}" if dbbw is not None else '?'
        print(f"{r['time']:<12} {r['scenario']:<8} {r['phase']:<12} "
              f"{str(r['h4_stage']):<8} {dbbw_str:<10} {str(r['h4_sqz']):<8} "
              f"{r['info']}{ev}")

    # ── Save results ─────────────────────────────────────────────────
    import json
    out_path = Path(__file__).parent.parent / "references" / "fixtures" / "oos_results.json"
    serializable = []
    for r in results:
        entry = dict(r)
        entry['time'] = entry['time']  # already string
        serializable.append(entry)
    with open(out_path, 'w') as f:
        json.dump(serializable, f, indent=2)
    print(f"\nFull results written to {out_path}")

    # Also save as CSV for easy review
    csv_path = Path(__file__).parent.parent / "references" / "fixtures" / "oos_results.csv"
    with open(csv_path, 'w', newline='') as f:
        if results:
            import csv as csv_mod
            writer = csv_mod.DictWriter(f, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)
    print(f"CSV written to {csv_path}")

if __name__ == '__main__':
    main()
