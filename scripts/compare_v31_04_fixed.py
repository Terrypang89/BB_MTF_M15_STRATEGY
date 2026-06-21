#!/usr/bin/env python3
"""
Compare V31.04 MT5 compiled EA output against Python baseline on the 78 March fixture bars.
FIXED: timestamp parsing bug — day index was [3:5] (off by 1), now [2:4].
Pure comparison — no tuning, no forcing agreement.
"""
import csv
import re

fixture_path = r"C:\Users\Tofy5\Project\BB_MTF_M15_STRATEGY\references\fixtures\march2026_truth.csv"
expected_path = r"C:\Users\Tofy5\Project\BB_MTF_M15_STRATEGY\references\fixtures\march2026_expected.csv"
v31_log_path = r"C:\Users\Tofy5\Project\BB_MTF_M15_STRATEGY\references\Backtest_data\V31.04\20260620_clean.log"
python_baseline_path = r"C:\Users\Tofy5\Project\BB_MTF_M15_STRATEGY\references\fixtures\replay_march_final.txt"

fixtures = []
with open(fixture_path, 'r') as f:
    for row in csv.DictReader(f):
        fixtures.append(row)

expected_scenarios = {}
with open(expected_path, 'r') as f:
    for row in csv.DictReader(f):
        expected_scenarios[row['timestamp']] = {
            'scenario': row['expected_scenario'],
            'phase': row['expected_phase'],
        }

# DECISION events
dec_pattern = re.compile(
    r'(\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2}).*?evt:DECISION\s+'
    r'sc:(\S+)\s+ph:(\S+)\s+id:(\S+)\s+act:(\d+)\s+'
    r'sz:([+-]?\d+\.?\d*)\s+conf:(\d+)\s+dir:(\d+)\s+'
    r'dbbwH4:([+-]?\d+\.?\d*)'
)

dec_timeline = []
with open(v31_log_path, 'r') as f:
    for line in f:
        m = dec_pattern.search(line)
        if m:
            ts_raw = m.group(1)
            date_part = ts_raw[5:10]
            hour_part = ts_raw[11:13]
            minute_part = ts_raw[14:16]
            dec_timeline.append({
                'ts_key': f"{date_part} {hour_part}:{minute_part}",
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
with open(v31_log_path, 'r') as f:
    for line in f:
        m = sc_pattern.search(line)
        if m:
            ts_raw = m.group(1)
            date_part = ts_raw[5:10]
            hour_part = ts_raw[11:13]
            minute_part = ts_raw[14:16]
            sc_timeline.append({
                'ts_key': f"{date_part} {hour_part}:{minute_part}",
                'scenario': m.group(2),
                'phase': m.group(3),
                'pivot': int(m.group(4)),
                'casShr': int(m.group(5)),
                'casSqz': int(m.group(6)),
                'cont': m.group(7),
                'loc': int(m.group(8)),
                'dbbwH4': float(m.group(9)),
            })

# FIX: day index [2:4] not [3:5]
def ts_to_comparable(ts_str):
    parts = ts_str.replace('.', '').split()
    month = int(parts[0][0:2])
    day = int(parts[0][2:4])  # FIXED
    hour, minute = int(parts[1][0:2]), int(parts[1][3:5])
    return (month, day, hour, minute)

dec_timeline.sort(key=lambda x: ts_to_comparable(x['ts_key']))
sc_timeline.sort(key=lambda x: ts_to_comparable(x['ts_key']))

def find_at_timestamp(timeline, fixture_ts):
    comp = ts_to_comparable(fixture_ts)
    active = None
    for evt in timeline:
        if ts_to_comparable(evt['ts_key']) <= comp:
            active = evt
        else:
            break
    return active

# Python baseline
python_results = {}
with open(python_baseline_path, 'r', encoding='utf-8', errors='replace') as f:
    for line in f:
        m = re.compile(
            r'(\d{2}\.\d{2} \d{2}:\d{2})\s+'
            r'(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(.*)'
        ).search(line)
        if m:
            python_results[m.group(1)] = {
                'got_scenario': m.group(2),
                'exp_scenario': m.group(3),
                'got_phase': m.group(4),
                'exp_phase': m.group(5),
                'status': m.group(6),
                'reason': m.group(7),
            }

# Compare
def parent_tier(sc):
    return sc[0]

scenario_exact = scenario_parent = phase_exact = 0
phase_mm = cas_mm = dbbw_mm = no_dec = 0
mismatches = []

for row in fixtures:
    ts = row['timestamp']
    v31 = find_at_timestamp(dec_timeline, ts)
    v31_sc = find_at_timestamp(sc_timeline, ts)
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
        mismatches.append({'ts': ts, 'field': 'NO_DEC', 'v31': 'none', 'python': py_sc, 'expected': expected_scenarios.get(ts, {}).get('scenario', '??')})
        continue

    if v31_sc_val == py_sc:
        scenario_exact += 1
    elif parent_tier(v31_sc_val) == parent_tier(py_sc):
        scenario_parent += 1
    else:
        mismatches.append({'ts': ts, 'field': 'scenario', 'v31': v31_sc_val, 'python': py_sc, 'expected': expected_scenarios.get(ts, {}).get('scenario', '??')})

    if v31_ph == py_ph:
        phase_exact += 1
    else:
        phase_mm += 1
        mismatches.append({'ts': ts, 'field': 'phase', 'v31': v31_ph, 'python': py_ph, 'expected': expected_scenarios.get(ts, {}).get('phase', '??')})

    fx_casShr = int(row['cas_shrinktf'])
    fx_casSqz = int(row['cas_sqzcount'])
    if v31_casShr == fx_casShr and v31_casSqz == fx_casSqz:
        pass
    else:
        cas_mm += 1
        mismatches.append({'ts': ts, 'field': 'cascade', 'v31': f"Shr={v31_casShr} Sqz={v31_casSqz}", 'python': f"Shr={fx_casShr} Sqz={fx_casSqz}", 'expected': f"Shr={fx_casShr} Sqz={fx_casSqz}"})

    fx_db = float(row['diffbbw_h4'].replace('+', ''))
    if abs(v31_db - fx_db) < 1.0:
        pass
    else:
        dbbw_mm += 1
        mismatches.append({'ts': ts, 'field': 'diffBBW_H4', 'v31': f"{v31_db:.1f}", 'python': f"{fx_db:.1f}", 'expected': f"{fx_db:.1f}"})

total = len(fixtures)
print(f"--- SCENARIO ---")
print(f"Exact match:       {scenario_exact}/{total} ({100*scenario_exact/total:.1f}%)")
print(f"Same parent tier:  {scenario_parent}/{total} ({100*scenario_parent/total:.1f}%)")
print(f"Parent-tier match: {(scenario_exact+scenario_parent)}/{total} ({100*(scenario_exact+scenario_parent)/total:.1f}%)")
print(f"Mismatch:          {total-scenario_exact-scenario_parent}/{total} ({100*(total-scenario_exact-scenario_parent)/total:.1f}%)")

print(f"\n--- PHASE ---")
print(f"Exact match:       {phase_exact}/{total} ({100*phase_exact/total:.1f}%)")
print(f"Mismatch:          {phase_mm}/{total} ({100*phase_mm/total:.1f}%)")

print(f"\n--- CASCADE ---")
cas_ok = total - cas_mm
print(f"Match:             {cas_ok}/{total} ({100*cas_ok/total:.1f}%)")
print(f"Mismatch:          {cas_mm}/{total} ({100*cas_mm/total:.1f}%)")

print(f"\n--- diffBBW_H4 ---")
dbbw_ok = total - dbbw_mm
print(f"Match:             {dbbw_ok}/{total} ({100*dbbw_ok/total:.1f}%)")
print(f"Mismatch:          {dbbw_mm}/{total} ({100*dbbw_mm/total:.1f}%)")

if no_dec > 0:
    print(f"\n--- NO DECISION EVENT ---")
    print(f"Bars with no DECISION event: {no_dec}")

print(f"\n{'='*120}")
print(f"ALL MISMATCHES ({len(mismatches)} total)")
print(f"{'='*120}")
for i, mm in enumerate(mismatches):
    print(f"\n[{i+1}] {mm['ts']} — {mm['field']}")
    print(f"    V31.04:   {mm['v31']}")
    print(f"    Python:  {mm['python']}")
    print(f"    Expected: {mm['expected']}")
