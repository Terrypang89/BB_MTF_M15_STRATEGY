#!/usr/bin/env python3
"""GATE 2: Verify MQL5 IdentifyScenario port matches Python harness.

Simulates the MQL5 IdentifyScenario logic in Python using the same
thresholds and cascade order as the MQL5 code. Compares against the
original Python harness on the 78 March fixture rows.

Agreement % = MQL5-sim matches Python-harness / 78 rows.
Target: near-100% (port, not redesign). Any divergence = a port bug.
"""

import csv
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
LOG_PATH = BASE / "references" / "Backtest_data" / "V30.02" / "20260606_clean.log"
EXPECTED_CSV = BASE / "references" / "fixtures" / "march2026_expected.csv"

START_DATE = "2026.03.02"
END_DATE = "2026.03.20"
END_TIME = "09:00"

TF_INDEX = {"M5": 0, "M15": 1, "M30": 2, "H1": 3, "H4": 4, "D1": 5, "W1": 6}
CASCADE_TFS = ["M15", "M30", "H1", "H4", "D1"]

PARENT_MAP = {
    "A1": "A", "A2": "A", "A3": "A",
    "B1": "B", "B2": "B", "B3": "B",
    "E1": "E", "E2": "E", "E3": "E", "E4": "E",
    "G1": "H", "G2": "H", "G3": "H", "G4": "H",
    "D1": "D", "D2": "D", "D3": "D",
    "F1": "F", "F2": "F", "F3": "F",
    "C1": "C", "C2": "C", "C3": "C",
}

# ── Parsers ─────────────────────────────────────────────────────────

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

# ── Helpers ─────────────────────────────────────────────────────────

def is_sqz(stg): return 400 <= stg <= 499 if stg else False
def is_fly(stg): return stg in (511, 512, 521, 522) if stg else False
def is_shrink(stg): return stg in (513, 523) if stg else False

def d1_dir_str(tf):
    m = tf.get('D1', {}).get('mid', 0) or 0
    if m in (1, 5): return "bullish"
    if m in (2, 4): return "bearish"
    stg = tf.get('D1', {}).get('stage', 0) or 0
    if stg in (511, 512): return "bullish"
    if stg in (521, 522): return "bearish"
    return "neutral"

# ── MQL5-sim state (mutable dict, no global keyword needed) ─────────
G = {
    'ring': [], 'ring_n': 0,
    'prevH1Sqz': False,
    'hist': [], 'hist_n': 0,
}

def ring_push(v):
    G['ring'].insert(0, v)
    if len(G['ring']) > 12: G['ring'].pop()
    if G['ring_n'] < 12: G['ring_n'] += 1

def hist_push(v):
    G['hist'].insert(0, v)
    if len(G['hist']) > 2: G['hist'].pop()
    if G['hist_n'] < 2: G['hist_n'] += 1

# ── ClassifyPhase (MQL5 port, absolute thresholds) ─────────────────

def classify_phase(tf):
    if G['ring_n'] < 2: return "PH_NONE"
    cur, prev = G['ring'][0], G['ring'][1]
    h4mid = tf.get('H4', {}).get('mid', 0) or 0
    h4stg = tf.get('H4', {}).get('stage', 0) or 0
    h4ud = tf.get('H4', {}).get('bbupdn', 0) or 0

    if G['ring_n'] >= 3 and h4stg >= 500 and all(G['ring'][i] > 0 for i in range(3)):
        return "PH_1"
    if is_sqz(h4stg): return "PH_4"
    if abs(prev) < 5 and cur > 15 and h4ud == 1: return "PH_5"
    if prev < 0 and cur > 20 and h4ud == 1: return "PH_5"
    if G['ring_n'] >= 4:
        alts = sum(1 for i in range(3) if i+1 < G['ring_n']
                   and (G['ring'][i] > 0) != (G['ring'][i+1] > 0))
        if alts >= 3: return "PH_6"
    if cur < -5:
        return "PH_3A" if h4mid == 3 else "PH_3B_INTO"
    if -5 <= cur <= 5 and h4ud in (1, 3) and prev < -10:
        return "PH_3B_OUT"
    if cur > 0 and cur < 15 and h4stg >= 500: return "PH_2"
    if h4mid == 3 and h4stg >= 500: return "PH_3A"
    return "PH_2" if cur > 0 else "PH_1"

# ── IdentifyScenario (MQL5 port — faithful to TofyTrade5.mqh) ───────

def identify_scenario_mql5(tf):
    dbbw_h4 = tf.get('H4', {}).get('diffBBW', 0) or 0
    ring_push(dbbw_h4)
    hist_push(dbbw_h4)

    # §12d
    cas_shrinkTF = -1
    for tfn in CASCADE_TFS:
        stg = tf.get(tfn, {}).get('stage', 0) or 0
        if is_shrink(stg): cas_shrinkTF = TF_INDEX[tfn]
    cas_sqzCount = sum(1 for t in ["M5","M15","M30","H1"]
                      if is_sqz(tf.get(t, {}).get('stage', 0) or 0))

    m15sqz = is_sqz(tf.get('M15', {}).get('stage', 0) or 0)
    m30sqz = is_sqz(tf.get('M30', {}).get('stage', 0) or 0)

    # LTF shrink
    ltf_shrinkTF = -1
    for tfn in ["M15","M30","H1"]:
        stg = tf.get(tfn, {}).get('stage', 0) or 0
        if is_shrink(stg): ltf_shrinkTF = TF_INDEX[tfn]

    # H4 state (§12, absolute thresholds)
    h4stg = tf.get('H4', {}).get('stage', 0) or 0
    h4mid = tf.get('H4', {}).get('mid', 0) or 0
    h4ud = tf.get('H4', {}).get('bbupdn', 0) or 0
    d1stg = tf.get('D1', {}).get('stage', 0) or 0
    d1mid = tf.get('D1', {}).get('mid', 0) or 0
    d1dir = d1_dir_str(tf)

    h4_dir = 1 if h4mid in (1,5) else (2 if h4mid in (2,4) else 0)

    h4_fly = (is_fly(h4stg) and h4mid in (1,2,3) and dbbw_h4 > -15)
    h4_shrink = ((is_shrink(h4stg) and not is_sqz(h4stg))
                 or (dbbw_h4 < -20 and not is_sqz(h4stg)))
    h4_sqz = (is_sqz(h4stg)
              or (abs(dbbw_h4) <= 0.2 and h4mid == 3 and not h4_fly))
    d1_fly = is_fly(d1stg) and d1mid in (1,2,4,5)

    phase = classify_phase(tf)

    # Early F-tier
    if G['hist_n'] >= 2:
        recent, prev_h = G['hist'][0], G['hist'][1]
        if (h4_fly and h4ud == 1 and recent > 15 and prev_h < 10
                and d1dir == "bullish" and h4mid in (1,5)):
            if G['ring_n'] >= 3 and all(G['ring'][i] > 0 for i in range(3)):
                return "F3", phase, cas_shrinkTF, cas_sqzCount
            if (tf.get('M30', {}).get('bbupdn', 0) or 0) == 1:
                return "F2", phase, cas_shrinkTF, cas_sqzCount
            return "F1", phase, cas_shrinkTF, cas_sqzCount

    # G-tier (OOS-UNVALIDATED)
    if h4_sqz:
        m5db = tf.get('M5', {}).get('diffBBW', 0) or 0
        m5_break = m5db > 0.3
        if not m5_break:
            if d1_fly and d1dir == "bearish" and h4mid in (2,4):
                return "G1", phase, cas_shrinkTF, cas_sqzCount
            if d1_fly:
                return "G2", phase, cas_shrinkTF, cas_sqzCount
            return "G3", phase, cas_shrinkTF, cas_sqzCount
        m5mid = tf.get('M5', {}).get('mid', 0) or 0
        sameD1 = ((d1mid in (1,5)) and (m5mid in (1,5))) or \
                 ((d1mid in (2,4)) and (m5mid in (2,4)))
        if d1_fly:
            return ("G1" if sameD1 else "G2"), phase, cas_shrinkTF, cas_sqzCount
        return "G3", phase, cas_shrinkTF, cas_sqzCount

    # E4
    if h4_shrink:
        return "E4", phase, cas_shrinkTF, cas_sqzCount

    # Compression routing
    confirmed = (cas_sqzCount >= 1 or (ltf_shrinkTF >= 1 and dbbw_h4 < 30))
    if confirmed:
        h1_sqz = is_sqz(tf.get('H1', {}).get('stage', 0) or 0)

        if h1_sqz and G['prevH1Sqz']:
            if m15sqz and m30sqz:
                return "E2", phase, cas_shrinkTF, cas_sqzCount
            return "E1", phase, cas_shrinkTF, cas_sqzCount

        if G['prevH1Sqz'] and not h1_sqz and ltf_shrinkTF >= 1:
            return "E1", phase, cas_shrinkTF, cas_sqzCount

        if h1_sqz:
            return "B3", phase, cas_shrinkTF, cas_sqzCount

        if h4_fly and dbbw_h4 > 5 and ltf_shrinkTF == -1 and not G['prevH1Sqz']:
            m5stg = tf.get('M5', {}).get('stage', 0) or 0
            if cas_sqzCount == 1 and not m15sqz and not is_sqz(m5stg):
                d1_ok = d1stg >= 500 and d1dir != "neutral"
                if d1_ok and (h4_dir == 1) == (d1dir == "bullish"):
                    return "A1", phase, cas_shrinkTF, cas_sqzCount
                return "A2", phase, cas_shrinkTF, cas_sqzCount

        if cas_sqzCount >= 2:
            if m15sqz and m30sqz:
                return "E2", phase, cas_shrinkTF, cas_sqzCount
            return "E1", phase, cas_shrinkTF, cas_sqzCount

        if ltf_shrinkTF >= 1:
            d_sqz = max((TF_INDEX[t] for t in ["M5","M15","M30","H1"]
                        if is_sqz(tf.get(t, {}).get('stage', 0) or 0)), default=-1)
            md = max(ltf_shrinkTF, d_sqz)
            if md == 1 and cas_sqzCount <= 1: return "B1", phase, cas_shrinkTF, cas_sqzCount
            if md == 2 and cas_sqzCount <= 1: return "B2", phase, cas_shrinkTF, cas_sqzCount
            return "B3", phase, cas_shrinkTF, cas_sqzCount

        return "A2", phase, cas_shrinkTF, cas_sqzCount

    # A-tier no-compression
    if h4_fly:
        if d1stg >= 500 and d1dir != "neutral":
            if (h4_dir == 1) == (d1dir == "bullish"):
                return "A1", phase, cas_shrinkTF, cas_sqzCount
        return "A2", phase, cas_shrinkTF, cas_sqzCount

    # Default
    return "A2", phase, cas_shrinkTF, cas_sqzCount

# ── Parse log (same as replay_harness.py) ───────────────────────────

def parse_log():
    tf_states = {t: {} for t in ['M5','M15','M30','H1','H4','D1','W1']}
    snapshots = []
    dbbw_hist = []
    prev_h1_sqz = False
    H4_HOURS = {"00","04","08","12","16","20"}
    captured = set()
    trade_events = []

    with open(LOG_PATH, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    for line in lines:
        line = line.strip()
        if not line: continue
        m = re.match(r'(\d{4}\.\d{2}\.\d{2}) (\d{2}:\d{2}:\d{2})', line)
        if not m: continue
        dt, tm = m.group(1), m.group(2)
        if dt < START_DATE: continue
        if dt > END_DATE or (dt == END_DATE and tm > END_TIME+":59"): continue
        hr, mn = tm[:2], tm[3:5]
        for t in ['M5','M15','M30','H1','H4','D1','W1']:
            if f'[{t}]' in line:
                tf_states[t] = parse_tf_line(line, t)
        if '[NEW_ORDER_OPEN]' in line or '[NEW_ORDER_CLOSE]' in line:
            trade_events.append({'time': f"{dt} {tm}", 'line': line})
        if '[ORDERINFO]' in line and hr in H4_HOURS and mn == "00":
            key = f"{dt}_{hr}"
            if key not in captured:
                captured.add(key)
                h4d = tf_states.get('H4', {}).get('diffBBW')
                if h4d is not None: dbbw_hist.append(h4d)
                snapshots.append({
                    'time': f"{dt} {tm}",
                    'tf': {t: dict(tf_states[t]) for t in ['M5']+CASCADE_TFS+['W1']},
                    'dbbw_hist': list(dbbw_hist),
                    'prev_h1_sqz': prev_h1_sqz,
                })
                h1s = tf_states.get('H1', {}).get('stage', 0)
                prev_h1_sqz = (400 <= h1s <= 499) if h1s else False
        if '[NEW_ORDER_OPEN]' in line or '[NEW_ORDER_CLOSE]' in line:
            h4d = tf_states.get('H4', {}).get('diffBBW')
            if h4d is not None: dbbw_hist.append(h4d)
            snapshots.append({
                'time': f"{dt} {tm}",
                'tf': {t: dict(tf_states[t]) for t in ['M5']+CASCADE_TFS+['W1']},
                'dbbw_hist': list(dbbw_hist),
                'prev_h1_sqz': prev_h1_sqz,
            })

    snapshots.sort(key=lambda x: x['time'])
    return snapshots

# ── Import Python harness for comparison ────────────────────────────

import importlib.util
spec = importlib.util.spec_from_file_location("rh", "scripts/replay_harness.py")
rh = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rh)

# ── Main ────────────────────────────────────────────────────────────

def main():
    print("=" * 80)
    print("GATE 2: MQL5 Port Verification — IdentifyScenario")
    print("=" * 80)
    print()
    print("Python harness vs MQL5-simulated IdentifyScenario")
    print("on 78 March fixture rows.\n")

    snaps = parse_log()
    print(f"Parsed {len(snaps)} snapshots\n")

    # Load expected
    expected = list(csv.DictReader(open(EXPECTED_CSV)))
    exp_map = {r['timestamp']: r for r in expected}

    exact = parent_ok = mismatch = 0
    rows = []

    for snap in snaps:
        ts = snap['time']
        short = ts[5:7]+'.'+ts[8:10]+' '+ts[11:13]+':'+ts[14:16]
        tf = snap['tf']
        hist = snap['dbbw_hist']
        prev_h1 = snap['prev_h1_sqz']

        # Python harness
        py_sc, _, _, _ = rh.identify_scenario(tf, hist, prev_h1)

        # MQL5-sim
        m5_sc, m5_ph, _, _ = identify_scenario_mql5(tf)
        G['prevH1Sqz'] = is_sqz(tf.get('H1', {}).get('stage', 0) or 0)

        py_p, m5_p = PARENT_MAP.get(py_sc, py_sc), PARENT_MAP.get(m5_sc, m5_sc)
        if py_sc == m5_sc:
            st, exact = "OK", exact + 1
            parent_ok += 1
        elif py_p == m5_p:
            st, parent_ok = "APX", parent_ok + 1
        else:
            st, mismatch = "NO", mismatch + 1

        exp_sc = exp_map.get(short, {}).get('expected_scenario', '?')
        rows.append((short, py_sc, m5_sc, py_p, m5_p, st, exp_sc))

    total = len(rows)
    print(f"{'Time':<12} {'Python':<7} {'MQL5-sim':<8} {'PyP':<4} {'M5P':<4} {'St':<4} {'Exp':<6}")
    print("-" * 55)
    for r in rows:
        print(f"{r[0]:<12} {r[1]:<7} {r[2]:<8} {r[3]:<4} {r[4]:<4} {r[5]:<4} {r[6]:<6}")

    print(f"\n--- GATE 2 Results ---")
    print(f"  Exact match:       {exact}/{total} ({exact/total*100:.1f}%)")
    print(f"  Parent-level match:{parent_ok}/{total} ({parent_ok/total*100:.1f}%)")
    print(f"  Mismatches:        {mismatch}/{total} ({mismatch/total*100:.1f}%)")

    if mismatch > 0:
        print(f"\n--- Divergences (Python ≠ MQL5-sim, different parent) ---")
        for r in rows:
            if r[5] == "NO":
                print(f"  {r[0]}: Python={r[1]}({r[3]}) MQL5={r[2]}({r[4]}) Exp={r[6]}")

    # Full 3-way comparison
    print(f"\n--- 3-Way: Python | MQL5-sim | Expected ---")
    print(f"{'Time':<12} {'Py':<5} {'M5':<5} {'Exp':<5} {'Py=M5':<6} {'Py=Exp':<7} {'M5=Exp'}")
    print("-" * 55)
    for r in rows:
        eq_pm = "Y" if r[1]==r[2] else "N"
        eq_pe = "Y" if r[1]==r[6] else "N"
        eq_me = "Y" if r[2]==r[6] else "N"
        print(f"{r[0]:<12} {r[1]:<5} {r[2]:<5} {r[6]:<5} {eq_pm:<6} {eq_pe:<7} {eq_me}")

if __name__ == '__main__':
    main()
