#!/usr/bin/env python3
"""
Compare V31.04 MT5 compiled EA output against Python baseline on the 78 March fixture bars.
Uses DECISION events (fire every 15 min) instead of SC events (stale "most recent before" logic).
Pure comparison — no tuning, no forcing agreement.
"""
import csv
import re
import sys

# ============================================================
# 1. Load the 78 March fixture timestamps
# ============================================================
fixture_path = r"C:\Users\Tofy5\Project\BB_MTF_M15_STRATEGY\references\fixtures\march2026_truth.csv"
expected_path = r"C:\Users\Tofy5\Project\BB_MTF_M15_STRATEGY\references\fixtures\march2026_expected.csv"
v31_log_path = r"C:\Users\Tofy5\Project\BB_MTF_M15_STRATEGY\references\Backtest_data\V31.04\20260620_clean.log"
python_baseline_path = r"C:\Users\Tofy5\Project\BB_MTF_M15_STRATEGY\references\fixtures\replay_march_final.txt"

fixtures = []
with open(fixture_path, 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        fixtures.append(row)

print(f"Loaded {len(fixtures)} fixture bars from march2026_truth.csv")

# ============================================================
# 2. Load expected scenarios from expected.csv
# ============================================================
expected_scenarios = {}
with open(expected_path, 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        ts = row['timestamp']
        expected_scenarios[ts] = {
            'scenario': row['expected_scenario'],
            'phase': row['expected_phase'],
        }

print(f"Loaded {len(expected_scenarios)} expected scenarios from march2026_expected.csv")

# ============================================================
# 3. Extract DECISION events from V31.04 log
#    Format: evt:DECISION sc:A2 ph:1 id:WAIT act:0 sz:0.00 conf:0 dir:0 dbbwH4:58.7
# ============================================================
dec_pattern = re.compile(
    r'(\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2}).*?evt:DECISION\s+'
    r'sc:(\S+)\s+ph:(\S+)\s+id:(\S+)\s+act:(\d+)\s+'
    r'sz:([+-]?\d+\.?\d*)\s+conf:(\d+)\s+dir:(\d+)\s+'
    r'dbbwH4:([+-]?\d+\.?\d*)'
)

dec_events_by_ts = {}  # ts_key -> most recent DECISION event at or before that ts
dec_timeline = []

with open(v31_log_path, 'r') as f:
    for line in f:
        m = dec_pattern.search(line)
        if m:
            ts_raw = m.group(1)
            date_part = ts_raw[5:10]    # "03.02"
            hour_part = ts_raw[11:13]   # "04"
            minute_part = ts_raw[14:16] # "00"
            ts_key = f"{date_part} {hour_part}:{minute_part}"  # "03.02 04:00"
            evt = {
                'ts_key': ts_key,
                'scenario': m.group(2),
                'phase': m.group(3),
                'id': m.group(4),
                'act': int(m.group(5)),
                'dbbwH4': float(m.group(9)),
            }
            dec_timeline.append(evt)

print(f"Extracted {len(dec_timeline)} DECISION events from V31.04 log")

# ============================================================
# 4. Also extract SC events for pivot/cascade fields
#    Format: evt:SC sc:A2 ph:1 pivot:0 casShr:5 casSqz:0 cont:H4 loc:2 dbbwH4:58.7
# ============================================================
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
            ts_key = f"{date_part} {hour_part}:{minute_part}"
            sc_timeline.append({
                'ts_key': ts_key,
                'scenario': m.group(2),
                'phase': m.group(3),
                'pivot': int(m.group(4)),
                'casShr': int(m.group(5)),
                'casSqz': int(m.group(6)),
                'cont': m.group(7),
                'loc': int(m.group(8)),
                'dbbwH4': float(m.group(9)),
            })

print(f"Extracted {len(sc_timeline)} SC events from V31.04 log")

# ============================================================
# 5. Timestamp comparison helpers
# ============================================================
def ts_to_comparable(ts_str):
    """Convert '03.02 04:00' to comparable tuple (month, day, hour, minute)"""
    parts = ts_str.replace('.', '').split()
    month, day = int(parts[0][0:2]), int(parts[0][3:5])
    hour, minute = int(parts[1][0:2]), int(parts[1][3:5])
    return (month, day, hour, minute)

# Sort timelines
dec_timeline.sort(key=lambda x: ts_to_comparable(x['ts_key']))
sc_timeline.sort(key=lambda x: ts_to_comparable(x['ts_key']))

def find_dec_at_timestamp(fixture_ts):
    """Find the DECISION event at or just before the fixture timestamp."""
    comp = ts_to_comparable(fixture_ts)
    active = None
    for evt in dec_timeline:
        if ts_to_comparable(evt['ts_key']) <= comp:
            active = evt
        else:
            break
    return active

def find_sc_at_timestamp(fixture_ts):
    """Find the SC event at or just before the fixture timestamp (for pivot/cascade)."""
    comp = ts_to_comparable(fixture_ts)
    active = None
    for evt in sc_timeline:
        if ts_to_comparable(evt['ts_key']) <= comp:
            active = evt
        else:
            break
    return active

# ============================================================
# 6. Extract Python baseline results from replay_march_final.txt
# ============================================================
python_results = {}
with open(python_baseline_path, 'r', encoding='utf-8', errors='replace') as f:
    lines = f.readlines()

python_parse_pattern = re.compile(
    r'(\d{2}\.\d{2} \d{2}:\d{2})\s+'
    r'(\S+)\s+'       # Got scenario
    r'(\S+)\s+'       # Exp scenario
    r'(\S+)\s+'       # Phase (Got)
    r'(\S+)\s+'       # ExpPh
    r'(\S+)\s+'       # Status
    r'(.*)'           # Reason
)

for line in lines:
    m = python_parse_pattern.search(line)
    if m:
        ts = m.group(1)
        python_results[ts] = {
            'got_scenario': m.group(2),
            'exp_scenario': m.group(3),
            'got_phase': m.group(4),
            'exp_phase': m.group(5),
            'status': m.group(6),
            'reason': m.group(7),
        }

print(f"Extracted {len(python_results)} Python baseline results from replay_march_final.txt")

# ============================================================
# 7. Compare: V31.04 vs Python on each fixture bar
# ============================================================
print("\n" + "="*120)
print("V31.04 vs PYTHON COMPARISON — 78 March fixture bars (DECISION events)")
print("="*120)

def parent_tier(scenario):
    """Extract parent tier from scenario code."""
    return scenario[0]  # A, B, E, G, C, F

scenario_exact = 0
scenario_parent = 0
phase_exact = 0
phase_mismatches = 0
cas_matches = 0
cas_mismatches = 0
dbbw_matches = 0
dbbw_mismatches = 0
no_dec_event_count = 0

mismatches = []

for row in fixtures:
    ts = row['timestamp']
    exp_sc = expected_scenarios.get(ts, {}).get('scenario', '??')
    exp_ph = expected_scenarios.get(ts, {}).get('phase', '??')

    v31_evt = find_dec_at_timestamp(ts)
    v31_sc_evt = find_sc_at_timestamp(ts)
    py_result = python_results.get(ts)

    v31_sc = v31_evt['scenario'] if v31_evt else 'NO_DEC_EVENT'
    v31_ph = v31_evt['phase'] if v31_evt else '??'
    v31_dbbwH4 = v31_evt['dbbwH4'] if v31_evt else 0.0

    # Pivot/cascade from SC event
    v31_pivot = v31_sc_evt['pivot'] if v31_sc_evt else -1
    v31_casShr = v31_sc_evt['casShr'] if v31_sc_evt else -99
    v31_casSqz = v31_sc_evt['casSqz'] if v31_sc_evt else -99

    py_sc = py_result['got_scenario'] if py_result else '??'
    py_ph = py_result['got_phase'] if py_result else '??'

    if not v31_evt:
        no_dec_event_count += 1
        mismatches.append({
            'ts': ts,
            'field': 'NO_DEC_EVENT',
            'v31': 'no DECISION event',
            'python': py_sc,
            'expected': exp_sc,
        })
        continue

    # Scenario comparison
    if v31_sc == py_sc:
        scenario_exact += 1
    elif parent_tier(v31_sc) == parent_tier(py_sc):
        scenario_parent += 1
    else:
        mismatches.append({
            'ts': ts,
            'field': 'scenario',
            'v31': v31_sc,
            'python': py_sc,
            'expected': exp_sc,
        })

    # Phase comparison
    if v31_ph == py_ph:
        phase_exact += 1
    else:
        phase_mismatches += 1
        mismatches.append({
            'ts': ts,
            'field': 'phase',
            'v31': v31_ph,
            'python': py_ph,
            'expected': exp_ph,
        })

    # Cascade comparison — from fixture
    fixture_casShr = int(row['cas_shrinktf'])
    fixture_casSqz = int(row['cas_sqzcount'])
    if v31_casShr == fixture_casShr and v31_casSqz == fixture_casSqz:
        cas_matches += 1
    else:
        cas_mismatches += 1
        mismatches.append({
            'ts': ts,
            'field': 'cascade',
            'v31': f"Shr={v31_casShr} Sqz={v31_casSqz}",
            'python': f"Shr={fixture_casShr} Sqz={fixture_casSqz}",
            'expected': f"Shr={fixture_casShr} Sqz={fixture_casSqz}",
        })

    # diffBBW comparison — from fixture
    fixture_dbbw = float(row['diffbbw_h4'].replace('+', ''))
    if abs(v31_dbbwH4 - fixture_dbbw) < 1.0:  # Allow 1.0 rounding tolerance
        dbbw_matches += 1
    else:
        dbbw_mismatches += 1
        mismatches.append({
            'ts': ts,
            'field': 'diffBBW_H4',
            'v31': f"{v31_dbbwH4:.1f}",
            'python': f"{fixture_dbbw:.1f}",
            'expected': f"{fixture_dbbw:.1f}",
        })

# ============================================================
# 8. Print results
# ============================================================
total = len(fixtures)
print(f"\n--- SCENARIO ---")
print(f"Exact match:       {scenario_exact}/{total} ({100*scenario_exact/total:.1f}%)")
print(f"Same parent tier:  {scenario_parent}/{total} ({100*scenario_parent/total:.1f}%)")
print(f"Parent-tier match: {(scenario_exact+scenario_parent)}/{total} ({100*(scenario_exact+scenario_parent)/total:.1f}%)")
print(f"Mismatch:          {total - scenario_exact - scenario_parent}/{total} ({100*(total-scenario_exact-scenario_parent)/total:.1f}%)")

print(f"\n--- PHASE ---")
print(f"Exact match:       {phase_exact}/{total} ({100*phase_exact/total:.1f}%)")
print(f"Mismatch:          {phase_mismatches}/{total} ({100*phase_mismatches/total:.1f}%)")

print(f"\n--- CASCADE (cas_shrinkTF + cas_sqzCount) ---")
print(f"Match:             {cas_matches}/{total} ({100*cas_matches/total:.1f}%)")
print(f"Mismatch:          {cas_mismatches}/{total} ({100*cas_mismatches/total:.1f}%)")

print(f"\n--- diffBBW_H4 ---")
print(f"Match:             {dbbw_matches}/{total} ({100*dbbw_matches/total:.1f}%)")
print(f"Mismatch:          {dbbw_mismatches}/{total} ({100*dbbw_mismatches/total:.1f}%)")

if no_dec_event_count > 0:
    print(f"\n--- NO DECISION EVENT ---")
    print(f"Bars with no DECISION event at or before fixture timestamp: {no_dec_event_count}")

# ============================================================
# 9. Print all mismatches
# ============================================================
print(f"\n{'='*120}")
print(f"ALL MISMATCHES ({len(mismatches)} total)")
print(f"{'='*120}")

for i, mm in enumerate(mismatches):
    print(f"\n[{i+1}] {mm['ts']} — {mm['field']}")
    print(f"    V31.04:   {mm['v31']}")
    print(f"    Python:  {mm['python']}")
    print(f"    Expected: {mm['expected']}")

# ============================================================
# 10. Print pivot_substate values from V31.04 (for inspection)
# ============================================================
print(f"\n{'='*120}")
print(f"PIVOT_SUBSTATE VALUES from V31.04 (per fixture bar)")
print(f"{'='*120}")
for row in fixtures:
    ts = row['timestamp']
    v31_sc_evt = find_sc_at_timestamp(ts)
    if v31_sc_evt:
        pivot = v31_sc_evt['pivot']
        if pivot != 0:
            print(f"  {ts}: pivot={pivot} (scenario={v31_sc_evt['scenario']})")

pivot_nonzero = 0
for row in fixtures:
    v31_sc_evt = find_sc_at_timestamp(row['timestamp'])
    if v31_sc_evt and v31_sc_evt['pivot'] != 0:
        pivot_nonzero += 1
print(f"\nPivot non-zero count: {pivot_nonzero}/{total}")
