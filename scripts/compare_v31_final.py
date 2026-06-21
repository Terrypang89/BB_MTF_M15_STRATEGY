#!/usr/bin/env python3
"""
Compare V31 EA output against Python baseline on 78 March fixture bars.
Fixed timestamp parsing: day index [2:4] not [3:5].
Uses DECISION events for scenario/phase/diffBBW, SC events for pivot/cascade.
Pure comparison — no tuning, no forcing agreement.
Usage: python compare_v31_final.py <V31_log_path> <label>
"""
import csv, re, sys

log_path = sys.argv[1]
label = sys.argv[2]  # "V31.02" or "V31.04"

fixture_path = r"C:\Users\Tofy5\Project\BB_MTF_M15_STRATEGY\references\fixtures\march2026_truth.csv"
expected_path = r"C:\Users\Tofy5\Project\BB_MTF_M15_STRATEGY\references\fixtures\march2026_expected.csv"
python_baseline_path = r"C:\Users\Tofy5\Project\BB_MTF_M15_STRATEGY\references\fixtures\replay_march_final.txt"

fixtures = list(csv.DictReader(open(fixture_path)))
expected_scenarios = {row['timestamp']: row for row in csv.DictReader(open(expected_path))}

# DECISION events
dec_pattern = re.compile(
    r'(\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2}).*?evt:DECISION\s+'
    r'sc:(\S+)\s+ph:(\S+)\s+id:(\S+)\s+act:(\d+)\s+'
    r'sz:([+-]?\d+\.?\d*)\s+conf:(\d+)\s+dir:(\d+)\s+'
    r'dbbwH4:([+-]?\d+\.?\d*)'
)
dec_timeline = []
with open(log_path) as f:
    for line in f:
        m = dec_pattern.search(line)
        if m:
            ts_raw = m.group(1)
            dec_timeline.append({
                'ts_key': f"{ts_raw[5:10]} {ts_raw[11:13]}:{ts_raw[14:16]}",
                'scenario': m.group(2),
                'phase': m.group(3),
                'dbbwH4': float(m.group(9)),
            })

# SC events for pivot/cascade
sc_pattern = re.compile(
    r'(\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2}).*?evt:SC\s+'
    r'sc:(\S+)\s+ph:(\S+)\s+pivot:(\d+)\s+'
    r'casShr:(-?\d+)\s+casSqz:(-?\d+)\s+'
    r'cont:(\S+)\s+loc:(-?\d+)\s+dbbwH4:([+-]?\d+\.?\d*)'
)
sc_timeline = []
with open(log_path) as f:
    for line in f:
        m = sc_pattern.search(line)
        if m:
            ts_raw = m.group(1)
            sc_timeline.append({
                'ts_key': f"{ts_raw[5:10]} {ts_raw[11:13]}:{ts_raw[14:16]}",
                'scenario': m.group(2),
                'phase': m.group(3),
                'pivot': int(m.group(4)),
                'casShr': int(m.group(5)),
                'casSqz': int(m.group(6)),
            })

# FIXED timestamp parsing: day = parts[0][2:4], not [3:5]
def ts_comp(ts_str):
    parts = ts_str.replace('.', '').split()
    return (int(parts[0][0:2]), int(parts[0][2:4]), int(parts[1][0:2]), int(parts[1][3:5]))

dec_timeline.sort(key=lambda x: ts_comp(x['ts_key']))
sc_timeline.sort(key=lambda x: ts_comp(x['ts_key']))

def find_at(timeline, fixture_ts):
    comp = ts_comp(fixture_ts)
    active = None
    for evt in timeline:
        if ts_comp(evt['ts_key']) <= comp:
            active = evt
        else:
            break
    return active

# Python baseline
python_results = {}
with open(python_baseline_path, 'r', encoding='utf-8', errors='replace') as f:
    for line in f:
        m = re.compile(
            r'(\d{2}\.\d{2} \d{2}:\d{2})\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(.*)'
        ).search(line)
        if m:
            python_results[m.group(1)] = {
                'got_scenario': m.group(2), 'got_phase': m.group(4),
                'status': m.group(6), 'reason': m.group(7),
            }

# Phase name mapping (V31 numeric → Python PH_ naming)
phase_map = {'1': 'PH_1', '2': 'PH_2', '3A': 'PH_3A', '3BI': 'PH_3B_INTO', '4': 'PH_4'}

# Compare
def parent_tier(sc):
    return sc[0]

scenario_exact = scenario_parent = phase_exact = 0
phase_mm = cas_mm = dbbw_mm = no_dec = 0
mismatches = []

for row in fixtures:
    ts = row['timestamp']
    v31 = find_at(dec_timeline, ts)
    v31_sc = find_at(sc_timeline, ts)
    py = python_results.get(ts)

    v31_sc_val = v31['scenario'] if v31 else 'NO_DEC'
    v31_ph = v31['phase'] if v31 else '??'
    v31_db = v31['dbbwH4'] if v31 else 0.0
    v31_casShr = v31_sc['casShr'] if v31_sc else -99
    v31_casSqz = v31_sc['casSqz'] if v31_sc else -99
    py_sc = py['got_scenario'] if py else '??'
    py_ph = py['got_phase'] if py else '??'

    if not v31:
        no_dec += 1
        mismatches.append({'ts': ts, 'field': 'NO_DEC', 'v31': 'none', 'python': py_sc, 'expected': expected_scenarios.get(ts, {}).get('expected_scenario', '??')})
        continue

    if v31_sc_val == py_sc:
        scenario_exact += 1
    elif parent_tier(v31_sc_val) == parent_tier(py_sc):
        scenario_parent += 1
    else:
        mismatches.append({'ts': ts, 'field': 'scenario', 'v31': v31_sc_val, 'python': py_sc, 'expected': expected_scenarios.get(ts, {}).get('expected_scenario', '??')})

    # Phase: map V31 names to Python names before comparing
    v31_ph_mapped = phase_map.get(v31_ph, v31_ph)
    if v31_ph_mapped == py_ph:
        phase_exact += 1
    else:
        phase_mm += 1
        mismatches.append({'ts': ts, 'field': 'phase', 'v31': v31_ph, 'v31_mapped': v31_ph_mapped, 'python': py_ph, 'expected': expected_scenarios.get(ts, {}).get('expected_phase', '??')})

    fx_casShr = int(row['cas_shrinktf'])
    fx_casSqz = int(row['cas_sqzcount'])
    if v31_casShr == fx_casShr and v31_casSqz == fx_casSqz:
        pass
    else:
        cas_mm += 1
        mismatches.append({'ts': ts, 'field': 'cascade', 'v31': f"Shr={v31_casShr} Sqz={v31_casSqz}", 'expected': f"Shr={fx_casShr} Sqz={fx_casSqz}"})

    fx_db = float(row['diffbbw_h4'].replace('+', ''))
    if abs(v31_db - fx_db) < 1.0:
        pass
    else:
        dbbw_mm += 1
        mismatches.append({'ts': ts, 'field': 'diffBBW_H4', 'v31': f"{v31_db:.1f}", 'expected': f"{fx_db:.1f}"})

total = len(fixtures)
print(f"\n=== {label} vs PYTHON (fixed script, phase mapped) ===")
print(f"--- SCENARIO ---")
print(f"Exact match:       {scenario_exact}/{total} ({100*scenario_exact/total:.1f}%)")
print(f"Same parent tier:  {scenario_parent}/{total} ({100*scenario_parent/total:.1f}%)")
print(f"Parent-tier match: {(scenario_exact+scenario_parent)}/{total} ({100*(scenario_exact+scenario_parent)/total:.1f}%)")
print(f"Mismatch:          {total-scenario_exact-scenario_parent}/{total} ({100*(total-scenario_exact-scenario_parent)/total:.1f}%)")

print(f"\n--- PHASE (mapped) ---")
print(f"Exact match:       {phase_exact}/{total} ({100*phase_exact/total:.1f}%)")
print(f"Mismatch:          {phase_mm}/{total} ({100*phase_mm/total:.1f}%)")

print(f"\n--- CASCADE ---")
print(f"Match:             {total-cas_mm}/{total} ({100*(total-cas_mm)/total:.1f}%)")
print(f"Mismatch:          {cas_mm}/{total} ({100*cas_mm/total:.1f}%)")

print(f"\n--- diffBBW_H4 ---")
print(f"Match:             {total-dbbw_mm}/{total} ({100*(total-dbbw_mm)/total:.1f}%)")
print(f"Mismatch:          {dbbw_mm}/{total} ({100*dbbw_mm/total:.1f}%)")

if no_dec > 0:
    print(f"\n--- NO DECISION EVENT: {no_dec} ---")

# Print scenario mismatches detail
scenario_mismatches = [m for m in mismatches if m['field'] == 'scenario']
if scenario_mismatches:
    print(f"\n--- SCENARIO MISMATCHES ({len(scenario_mismatches)}) ---")
    for m in scenario_mismatches:
        print(f"  {m['ts']}: {label}={m['v31']}  Python={m['python']}  Expected={m['expected']}")

phase_mismatches = [m for m in mismatches if m['field'] == 'phase']
if phase_mismatches:
    print(f"\n--- PHASE MISMATCHES ({len(phase_mismatches)}) ---")
    for m in phase_mismatches:
        print(f"  {m['ts']}: {label}={m['v31']}({m['v31_mapped']})  Python={m['python']}  Expected={m['expected']}")
