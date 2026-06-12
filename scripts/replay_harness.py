#!/usr/bin/env python3
"""Replay harness — executable spec for TofyTrade5.

Parses V30.02 clean log, implements identify_scenario() as reference
implementation of Layer 1 (Part 3 + 12d), scores against March 2026 fixtures.

When MQL5 and Python disagree, Python (validated against fixtures) is truth.
"""

import csv
import re
import sys
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────
BASE = Path(__file__).resolve().parent.parent
LOG_PATH = BASE / "references" / "Backtest_data" / "V30.02" / "20260606_clean.log"
TRUTH_CSV = BASE / "references" / "fixtures" / "march2026_truth.csv"
EXPECTED_CSV = BASE / "references" / "fixtures" / "march2026_expected.csv"
BENCHMARK_MD = BASE / "references" / "fixtures" / "march2026_benchmark.md"

START_DATE = "2026.03.02"
END_DATE = "2026.03.20"
END_TIME = "09:00"

# ── TF index convention (from TofyTrade4.mqh) ─────────────────────────
# BB_datas[0]=M5, [1]=M15, [2]=M30, [3]=H1, [4]=H4, [5]=D1, [6]=W1
TF_INDEX = {"M5": 0, "M15": 1, "M30": 2, "H1": 3, "H4": 4, "D1": 5, "W1": 6}
CASCADE_TFS = ["M15", "M30", "H1", "H4", "D1"]  # for cas_shrinkTF

# ── Scenario / Phase enums (matching MQL5) ────────────────────────────
SCENARIOS = {
    "A1": "A", "A2": "A", "A3": "A",
    "B1": "B", "B2": "B", "B3": "B",
    "E1": "E", "E2": "E", "E3": "E", "E4": "E",
    "G1": "H", "G2": "H", "G3": "H", "G4": "H",  # Direction pivot (scaffold SC_G1-SC_G4)
    "D1": "D", "D2": "D", "D3": "D",
    "F1": "F", "F2": "F", "F3": "F",
    "C1": "C", "C2": "C", "C3": "C",
}
PARENT_SCENARIO = {k: v for k, v in SCENARIOS.items()}

# Scenario labels used in expected CSV
SCENARIO_LABELS = [
    "A1", "A2", "A3",
    "B1", "B2", "B3",
    "E1", "E2", "E3", "E4",
    "G1", "G2", "G3", "G4",
    "D1", "D2", "D3",
    "F1", "F2", "F3",
    "C1", "C2", "C3",
]

PHASES = ["PH_1", "PH_2", "PH_3A", "PH_3B_INTO", "PH_3B_OUT", "PH_4", "PH_5", "PH_6"]

# ── Parsers (reusing extract_log_data.py patterns) ────────────────────

def parse_array_first(raw):
    """Extract first value from '[1.0, 2.0, 3.0]' -> 1.0"""
    m = re.search(r'\[([-\d.]+)', raw)
    return float(m.group(1)) if m else None

def parse_int_array_first(raw):
    """Extract first int from '[2, 0, 1]' -> 2"""
    m = re.search(r'\[(\d+)', raw)
    return int(m.group(1)) if m else None

def parse_tf_line(line, tf_name):
    """Parse a TF block line and return dict of fields."""
    r = {}
    # Stage
    m = re.search(rf'W_stage_{tf_name}:\((\w+)\)\[([^\]]+)\]', line)
    if m:
        vals = [int(x.strip()) for x in m.group(2).split(',') if x.strip()]
        r['stage'] = vals[0] if vals else None
        r['regime'] = m.group(1)
    # diffMid_Trend
    m = re.search(rf'diffMid_Trend_{tf_name}:\[([^\]]+)\]', line)
    if m:
        vals = [float(x.strip()) for x in m.group(1).split(',') if x.strip()]
        r['mid'] = int(vals[0]) if vals else None
    # BBUpDn
    m = re.search(rf'BBUpDn_{tf_name}:\[([^\]]+)\]', line)
    if m:
        vals = [int(x.strip()) for x in m.group(1).split(',') if x.strip()]
        r['bbupdn'] = vals[0] if vals else None
    # diffBBW
    m = re.search(rf'diffBBW_{tf_name}:\[([^\]]+)\]', line)
    if m:
        vals = [float(x.strip()) for x in m.group(1).split(',') if x.strip()]
        r['diffBBW'] = vals[0] if vals else None
    # trend
    m = re.search(rf'trend_{tf_name}:\[([^\]]+)\]', line)
    if m:
        vals_str = m.group(1).replace(' ', '').rstrip(',').split(',')
        vals = [int(float(x)) for x in vals_str if x]
        r['trend'] = vals[0] if vals else None
    # Price levels
    for fld in ('MidLV', 'UppLV', 'LowLV', 'WLV'):
        m = re.search(rf'{fld}_{tf_name}:\[([^\]]+)\]', line)
        if m:
            vals = [float(x.strip()) for x in m.group(1).split(',') if x.strip()]
            r[fld.lower()] = vals[0] if vals else None
    # close (M15 block only)
    m = re.search(rf'close_{tf_name}:\[([^\]]+)\]', line)
    if m:
        vals = [float(x.strip()) for x in m.group(1).split(',') if x.strip()]
        r['close'] = vals[0] if vals else None
    return r

# ── Cascade state derivation (§12d) ───────────────────────────────────

def derive_cascade(tf_states):
    """Derive cas_shrinkTF and cas_sqzCount from TF states.

    cas_shrinkTF = highest TF index in shrink (513/523), -1 if none.
    cas_sqzCount = count of TFs in SQZ (400-499).
    """
    cas_shrinkTF = -1
    cas_sqzCount = 0
    for tf in CASCADE_TFS:
        st = tf_states.get(tf)
        if not st or st.get('stage') is None:
            continue
        stage = st['stage']
        if 400 <= stage <= 499:
            cas_sqzCount += 1
        elif stage in (513, 523):
            idx = TF_INDEX[tf]
            if idx > cas_shrinkTF:
                cas_shrinkTF = idx
    return cas_shrinkTF, cas_sqzCount

# ── H4 x D1 CHECK-HTF classification (§12) ───────────────────────────

def classify_h4_state(h4):
    """Classify H4 state using diffMid + diffBBW as PRIMARY (§12 EDIT V4 normative rule).

    Returns (state_label, direction):
      state_label: 'fly', 'shrink', 'sqz'
      direction: 1=UP, 2=DN, 0=NONE
    """
    stage = h4.get('stage')
    mid = h4.get('mid')
    dbbw = h4.get('diffBBW')
    ud = h4.get('bbupdn')

    if stage is None:
        return ('unknown', 0)

    # diffBBW is PRIMARY — trust it over stage label (§12 lag rule)
    # Strongly negative diffBBW means H4 is shrinking regardless of stage
    if dbbw is not None and dbbw < -20:
        direction = 1 if mid in (1, 5) else (2 if mid in (2, 4) else 0)
        return ('shrink', direction)

    # SQZ — if H4 in SQZ stage
    if 400 <= stage <= 499:
        # But check diffBBW: if strongly positive + BBUpDn=1, H4 may be exiting SQZ
        if dbbw is not None and dbbw > 10 and ud == 1:
            # H4 exiting SQZ — treat as early fly
            direction = 1 if mid in (1, 5) else (2 if mid in (2, 4) else 0)
            return ('fly', direction)
        return ('sqz', 0)

    # Shrink stage
    if stage in (513, 523):
        # Check if diffBBW contradicts: positive + BBUpDn=1 means exiting shrink
        if dbbw is not None and dbbw > 5 and ud == 1:
            direction = 1 if mid in (1, 5) else (2 if mid in (2, 4) else 0)
            return ('fly', direction)
        direction = 1 if (stage == 513 or mid in (1, 5)) else (2 if (stage == 523 or mid in (2, 4)) else 0)
        return ('shrink', direction)

    # Fly (511/512/521/522)
    # Check if diffBBW contradicts: negative + mid>=3 means transitioning away from fly
    if stage in (511, 512, 521, 522):
        if dbbw is not None and dbbw < -5 and mid is not None and mid >= 3:
            # H4 shrinking, stage label lags
            return ('shrink', 0)
        direction = 1 if stage in (511, 512) or mid in (1, 5) else (2 if stage in (521, 522) or mid in (2, 4) else 0)
        return ('fly', direction)

    return ('unknown', 0)

def classify_d1_state(d1):
    """Classify D1 direction for H-resolution."""
    mid = d1.get('mid')
    stage = d1.get('stage')
    if mid in (1, 5):
        return 'bullish'
    elif mid in (2, 4):
        return 'bearish'
    elif mid is not None and mid >= 3:
        return 'neutral'
    # fallback to stage
    if stage in (511, 512):
        return 'bullish'
    elif stage in (521, 522):
        return 'bearish'
    return 'neutral'

# ── IdentifyScenario (Part 3 + §12d) ─────────────────────────────────

def identify_scenario(tf_states, diffbbw_h4_history=None):
    """Identify scenario from TF states.

    Implements Part 3 tier tables + §12d decoder + §12 CHECK-HTF.
    Every branch cites its document section.

    Args:
        tf_states: dict {TF_name: {stage, mid, bbupdn, diffBBW, trend, ...}}
        diffbbw_h4_history: list of recent diffBBW_H4 values for phase detection

    Returns:
        (scenario, phase, info_string)
    """
    h4 = tf_states.get('H4', {})
    d1 = tf_states.get('D1', {})
    h1 = tf_states.get('H1', {})
    m30 = tf_states.get('M30', {})
    m15 = tf_states.get('M15', {})

    # 1. Compute cas_sqzCount and cas_shrinkTF (§12d)
    cas_shrinkTF, cas_sqzCount = derive_cascade(tf_states)

    # 2. CHECK HTF FIRST (§12 CHECK-HTF table)
    h4_state, h4_dir = classify_h4_state(h4)
    d1_dir = classify_d1_state(d1)

    # 3. Determine scenario per Part 3 tier tables + §12d decoder

    # ── H4 in SQZ → H-scenario (Direction pivot, Part 3 Tier 2) ──
    if h4_state == 'sqz':
        h4_bbupdn = h4.get('bbupdn', 0)
        h4_dbbw = h4.get('diffBBW', 0)
        h4_mid = h4.get('mid', 0)

        # H1: H4 breaking out of SQZ, same direction as D1
        if h4_bbupdn == 1 and h4_dbbw is not None and h4_dbbw > 0:
            if d1_dir == 'bullish' and h4_mid in (1, 5):
                return ('G1', 'G1 — H1 bullish resolution', cas_shrinkTF, cas_sqzCount)
            elif d1_dir == 'bearish' and h4_mid in (2, 4):
                return ('G1', 'G1 — H1 bearish resolution', cas_shrinkTF, cas_sqzCount)
            else:
                # Breakout opposite to D1 = H2 (counter-D1)
                return ('G2', 'G2 — H2 opposite D1', cas_shrinkTF, cas_sqzCount)

        # H4 whipsaw (§12d: alternating diffBBW)
        if diffbbw_h4_history and len(diffbbw_h4_history) >= 3:
            signs = [1 if v > 0 else -1 for v in diffbbw_h4_history[-3:]]
            if signs[0] != signs[1] and signs[1] != signs[2]:
                return ('G4', 'G4 — H4 whipsaw', cas_shrinkTF, cas_sqzCount)

        # H3: false breakout — H4 briefly in fly but BBUpDn not clean expanding
        h4_stage = h4.get('stage', 0)
        if h4_bbupdn in (3, 4) and h4_dbbw is not None and 0 < h4_dbbw < 20:
            return ('G3', 'G3 — H3 false breakout', cas_shrinkTF, cas_sqzCount)

        # Deep SQZ with many TFs squeezed → H4
        if cas_sqzCount >= 4:
            return ('G4', 'G4 — deep SQZ all gates locked', cas_shrinkTF, cas_sqzCount)

        # Default: H4 in SQZ = H3 (false breakout / waiting)
        return ('G3', 'G3 — H4 in SQZ waiting', cas_shrinkTF, cas_sqzCount)

    # ── H4 in shrink → E4 (§12d: cas_shrinkTF=4) ──
    if h4_state == 'shrink':
        return ('E4', 'E4 — HTF compressing', cas_shrinkTF, cas_sqzCount)

    # ── F scenarios: H4 exiting shrink/SQZ, expanding (Part 3 Tier 3) ──
    # Check BEFORE fly scenarios — H4 just exited compression
    if diffbbw_h4_history and len(diffbbw_h4_history) >= 2:
        recent_dbbw = diffbbw_h4_history[-1]
        prev_dbbw = diffbbw_h4_history[-2]
        h4_stage = h4.get('stage', 0)
        h4_bbupdn = h4.get('bbupdn', 0)
        # H4 stage is fly but was recently in shrink/SQZ (prev diffBBW <= 0 or small)
        if (h4_state == 'fly' and h4_bbupdn == 1
                and recent_dbbw is not None and recent_dbbw > 15
                and prev_dbbw is not None and prev_dbbw < 10):
            # H4 just broke out of compression
            if d1_dir == 'bullish' and h4.get('mid') in (1, 5):
                # F3 if sustained positive diffBBW
                if len(diffbbw_h4_history) >= 3:
                    recent3 = diffbbw_h4_history[-3:]
                    if all(v > 0 for v in recent3):
                        return ('F3', 'F3 — HTF confirmed expansion', cas_shrinkTF, cas_sqzCount)
                # F2 if M30 confirms
                if m30.get('bbupdn') == 1:
                    return ('F2', 'F2 — MTF confirmed expansion', cas_shrinkTF, cas_sqzCount)
                return ('F1', 'F1 — LTF expansion', cas_shrinkTF, cas_sqzCount)

    # ── H4 flying → A / B / E scenarios (Part 3 Tier 1/2/3) ──
    if h4_state == 'fly':
        h4_mid = h4.get('mid', 0)
        h4_dbbw = h4.get('diffBBW', 0)
        d1_stage = d1.get('stage', 0)

        # Compute lower-TF shrink excluding D1 (D1 shrink doesn't override H4 fly)
        ltf_shrinkTF = -1
        for tf in ["M15", "M30", "H1"]:
            st = tf_states.get(tf)
            if st and st.get('stage') in (513, 523):
                ltf_shrinkTF = max(ltf_shrinkTF, TF_INDEX[tf])

        # ── A1: H4+D1 both flying same direction (Part 3 Tier 1) ──
        if h4_dir != 0 and d1_dir != 'neutral' and d1_stage >= 500:
            # Check H4 and D1 direction alignment
            h4_up = (h4_dir == 1)
            d1_up = (d1_dir == 'bullish')
            if h4_up == d1_up:
                return ('A1', 'A1 — H4+D1 fly aligned', cas_shrinkTF, cas_sqzCount)

        # ── B-scenario FIRST: LTF shrink (Part 3 Tier 2) ──
        if ltf_shrinkTF > -1:
            b_key = (ltf_shrinkTF, cas_sqzCount)
            b_decoder = {
                (1, 0): ('B1', 'B1 — M15 shrink'),
                (1, 1): ('E1', 'B1 late → E1'),
                (2, 0): ('B2', 'B2 early — M30 shrink'),
                (2, 1): ('E1', 'B2 late → E1'),
                (3, 0): ('B3', 'B3 — H1 shrink'),
                (3, 1): ('E1', 'B3 → E1'),
                (3, 2): ('E2', 'E2 — H1 shrink + SQZ'),
            }
            if b_key in b_decoder:
                return b_decoder[b_key] + (cas_shrinkTF, cas_sqzCount)
            return (f'B{ltf_shrinkTF}', f'B{ltf_shrinkTF}', cas_shrinkTF, cas_sqzCount)

        # ── E-scenario: LTF SQZ without shrink (Part 3 Tier 2) ──
        if cas_sqzCount >= 1:
            if cas_sqzCount == 1:
                return ('E1', 'E1 — LTF partial SQZ', cas_shrinkTF, cas_sqzCount)
            elif cas_sqzCount == 2:
                return ('E2', 'E2 — LTF full SQZ', cas_shrinkTF, cas_sqzCount)
            else:
                return ('E3', 'E3 — deep cascade', cas_shrinkTF, cas_sqzCount)

        # ── A2: only when NO LTF compression (B/E) and NOT A1 ──
        # A2 requires H4 fly with directional conviction and D1 not opposing
        d1_compressing = (d1_stage in (513, 523)) or (400 <= d1_stage <= 499) or (300 <= d1_stage <= 399)
        if h4_mid in (1, 2) and d1_compressing:
            return ('A2', 'A2 — H4 fly, D1 compressing', cas_shrinkTF, cas_sqzCount)
        # A2 when H4 mid sideway but no LTF compression
        if h4_mid >= 3 and h4_dbbw is not None and h4_dbbw > 10:
            return ('A2', 'A2 — H4 fly mid sideway', cas_shrinkTF, cas_sqzCount)
        # A2 when D1 opposes but no LTF compression
        if d1_dir != h4_dir and h4_dir != 0:
            return ('A2', 'A2 — D1 opposes H4', cas_shrinkTF, cas_sqzCount)

    # ── Default fallback — compression likely ──
    return ('E1', 'default — LTF compression', cas_shrinkTF, cas_sqzCount)

# ── Phase identification (Section 13) ────────────────────────────────

def identify_phase(h4, diffbbw_h4_history):
    """Identify phase from H4 state + diffBBW trajectory (Section 13).

    Args:
        h4: H4 TF state dict
        diffbbw_h4_history: list of recent diffBBW_H4 values

    Returns:
        phase string (PH_1, PH_2, PH_3A, PH_3B_INTO, PH_3B_OUT, PH_4, PH_5, PH_6)
    """
    h4_mid = h4.get('mid', 0)
    h4_stage = h4.get('stage', 0)
    h4_bbupdn = h4.get('bbupdn', 0)

    if not diffbbw_h4_history or len(diffbbw_h4_history) < 2:
        return 'PH_1'  # default

    dbbw = diffbbw_h4_history[-1]
    prev_dbbw = diffbbw_h4_history[-2]

    # Phase 1: directional trend — diffBBW sustained positive (§13)
    if len(diffbbw_h4_history) >= 3:
        recent = diffbbw_h4_history[-3:]
        if all(v > 0 for v in recent) and h4_stage >= 500:
            return 'PH_1'

    # H4 in SQZ → Phase 4
    if 400 <= h4_stage <= 499:
        return 'PH_4'

    # Phase 5: explosive breakout — diffBBW sharply positive after near-zero
    if prev_dbbw is not None and dbbw is not None:
        if abs(prev_dbbw) < 5 and dbbw > 15 and h4_bbupdn == 1:
            return 'PH_5'
        # zero-cross to sharply positive
        if prev_dbbw < 0 and dbbw > 20 and h4_bbupdn == 1:
            return 'PH_5'

    # Phase 6: alternating diffBBW over lookback (§13)
    if len(diffbbw_h4_history) >= 4:
        recent = diffbbw_h4_history[-4:]
        signs = [1 if v > 0 else -1 for v in recent]
        alternations = sum(1 for i in range(len(signs)-1) if signs[i] != signs[i+1])
        if alternations >= 3:
            return 'PH_6'

    # Phase 3: negative diffBBW (compression)
    if dbbw is not None and dbbw < -5:
        # 3a vs 3b-INTO vs 3b-OUT
        if h4_mid == 3:
            return 'PH_3A'  # symmetric tightening (§13: H4 mid=3 → 3a)
        elif h4_mid in (1, 2, 4, 5):
            return 'PH_3B_INTO'  # asymmetric — trending INTO compression
        else:
            return 'PH_3B_INTO'  # default

    # Phase 3b-OUT: diffBBW near zero → positive, H4 exiting shrink
    if dbbw is not None and -5 <= dbbw <= 5 and h4_bbupdn in (1, 3):
        if prev_dbbw is not None and prev_dbbw < -10:
            return 'PH_3B_OUT'  # recovering from shrink

    # Phase 2: diffBBW transitioning pos→zero (pre-SQZ zigzag)
    if dbbw is not None and 0 < dbbw < 15 and h4_stage >= 500:
        return 'PH_2'

    # Phase 3a default: H4 mid=3 with fly stage
    if h4_mid == 3 and h4_stage >= 500:
        return 'PH_3A'

    # Fallback
    if dbbw is not None and dbbw > 0:
        return 'PH_2'
    return 'PH_1'

# ── Log parser ────────────────────────────────────────────────────────

def parse_log():
    """Parse the clean log file and return list of snapshot dicts for March window."""
    tf_states = {tf: {} for tf in ['M15', 'M30', 'H1', 'H4', 'D1', 'W1']}
    snapshots = []
    diffbbw_h4_history = []

    H4_HOURS = {"00", "04", "08", "12", "16", "20"}
    captured_h4 = set()
    trade_events = []

    with open(LOG_PATH, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue

        m = re.match(r'(\d{4}\.\d{2}\.\d{2}) (\d{2}:\d{2}:\d{2})', line)
        if not m:
            continue

        date_str = m.group(1)
        time_str = m.group(2)

        if date_str < START_DATE:
            continue
        if date_str > END_DATE or (date_str == END_DATE and time_str > END_TIME + ":59"):
            continue

        current_time = f"{date_str} {time_str}"
        hour = time_str[:2]
        minute = time_str[3:5]

        # Parse TF blocks
        for tf in ['M15', 'M30', 'H1', 'H4', 'D1', 'W1']:
            if f'[{tf}]' in line:
                tf_states[tf] = parse_tf_line(line, tf)

        # Track trade events
        if '[NEW_ORDER_OPEN]' in line or '[NEW_ORDER_CLOSE]' in line:
            trade_events.append({'time': current_time, 'line': line})

        # Capture at H4 boundaries (ORDERINFO = end of tick)
        if '[ORDERINFO]' in line and hour in H4_HOURS and minute == "00":
            boundary_key = f"{date_str}_{hour}"
            if boundary_key not in captured_h4:
                captured_h4.add(boundary_key)

                # Update diffBBW history
                h4_dbbw = tf_states.get('H4', {}).get('diffBBW')
                if h4_dbbw is not None:
                    diffbbw_h4_history.append(h4_dbbw)

                snap = {
                    'time': current_time,
                    'tf_states': {tf: dict(tf_states[tf]) for tf in CASCADE_TFS + ['W1']},
                    'diffbbw_h4_history': list(diffbbw_h4_history),
                    'trade_event': '',
                }
                snapshots.append(snap)

        # Capture at trade events
        if '[NEW_ORDER_OPEN]' in line or '[NEW_ORDER_CLOSE]' in line:
            h4_dbbw = tf_states.get('H4', {}).get('diffBBW')
            if h4_dbbw is not None:
                diffbbw_h4_history.append(h4_dbbw)

            # Determine trade event label
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
                'tf_states': {tf: dict(tf_states[tf]) for tf in CASCADE_TFS + ['W1']},
                'diffbbw_h4_history': list(diffbbw_h4_history),
                'trade_event': te,
            }
            snapshots.append(snap)

    snapshots.sort(key=lambda x: x['time'])
    return snapshots

# ── Fixture loading ───────────────────────────────────────────────────

def load_truth(path):
    """Load march2026_truth.csv."""
    rows = []
    with open(path, 'r', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows

def load_expected(path):
    """Load march2026_expected.csv."""
    rows = []
    with open(path, 'r', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows

# ── Scenario matching ─────────────────────────────────────────────────

def scenario_match(got, expected):
    """Check if got scenario matches expected.

    Returns (match: bool, reason: str)
    Same parent scenario = full match.
    Different parent scenario = miss.
    """
    got_parent = PARENT_SCENARIO.get(got, got)
    exp_parent = PARENT_SCENARIO.get(expected, expected)

    if got == expected:
        return (True, 'exact')
    if got_parent == exp_parent:
        return (True, f'same parent {got_parent}')
    return (False, f'{got} vs {expected} (parents {got_parent} vs {exp_parent})')

# ── Main ──────────────────────────────────────────────────────────────

def main():
    print("=" * 80)
    print("REPLAY HARNESS — Phase 1: identify_scenario")
    print("=" * 80)

    # Parse log
    print("\nParsing log...")
    snapshots = parse_log()
    print(f"  Captured {len(snapshots)} snapshots")

    # Load fixtures
    truth = load_truth(TRUTH_CSV)
    expected = load_expected(EXPECTED_CSV)

    # Build lookup: timestamp → expected scenario
    exp_by_time = {}
    for row in expected:
        exp_by_time[row['timestamp']] = row

    # Run identify_scenario on each snapshot
    print("\nRunning identify_scenario...")
    matches = 0
    half_misses = 0
    misses = 0
    mismatches = []

    results = []
    for snap in snapshots:
        ts = snap['time']
        # Format timestamp to match fixture format (e.g., "03.02 04:00")
        # ts = "2026.03.02 04:00:00" → "03.02 04:00"
        short_ts = ts[5:7] + '.' + ts[8:10] + ' ' + ts[11:13] + ':' + ts[14:16]  # "MM.DD HH:MM"

        # Find matching expected row
        exp_row = exp_by_time.get(short_ts)

        if not exp_row:
            continue

        expected_scenario = exp_row['expected_scenario']

        # Run identify_scenario
        tf_st = snap['tf_states']
        dbbw_hist = snap['diffbbw_h4_history']
        scenario, info, cas_shrink, cas_sqz = identify_scenario(tf_st, dbbw_hist)

        # Run phase identification
        phase = identify_phase(tf_st.get('H4', {}), dbbw_hist)

        matched, reason = scenario_match(scenario, expected_scenario)

        if matched:
            if reason == 'exact':
                matches += 1
            else:
                half_misses += 1  # same parent, different sub-state
            status = 'OK' if reason == 'exact' else 'APX'
        else:
            misses += 1
            status = 'NO'

        results.append({
            'time': short_ts,
            'got_scenario': scenario,
            'expected_scenario': expected_scenario,
            'got_phase': phase,
            'expected_phase': exp_row.get('expected_phase', ''),
            'status': status,
            'reason': reason,
            'info': info,
            'trade_event': snap.get('trade_event', ''),
        })

    # Print results
    total = matches + half_misses + misses
    exact_pct = (matches / total * 100) if total > 0 else 0
    half_pct = (half_misses / total * 100) if total > 0 else 0
    miss_pct = (misses / total * 100) if total > 0 else 0
    parent_pct = ((matches + half_misses) / total * 100) if total > 0 else 0

    print(f"\n{'Time':<12} {'Got':<6} {'Exp':<6} {'Phase':<6} {'ExpPh':<8} {'Status':<6} {'Reason'}")
    print("-" * 100)
    for r in results:
        ev = f" ***{r['trade_event']}" if r['trade_event'] else ""
        print(f"{r['time']:<12} {r['got_scenario']:<6} {r['expected_scenario']:<6} "
              f"{r['got_phase']:<6} {r['expected_phase']:<8} {r['status']:<6} "
              f"{r['reason']}{ev}")

    print(f"\n--- Match Summary ---")
    print(f"  Exact matches:    {matches}/{total} ({exact_pct:.1f}%)")
    print(f"  Same parent:      {half_misses}/{total} ({half_pct:.1f}%)")
    print(f"  Misses:           {misses}/{total} ({miss_pct:.1f}%)")
    print(f"  Parent-level match: {matches+half_misses}/{total} ({parent_pct:.1f}%)")

    # GATE 1 check
    print(f"\n--- GATE 1 ---")
    if parent_pct >= 95:
        print(f"  PASS — parent-level match {parent_pct:.1f}% >= 95%")
    else:
        print(f"  FAIL — parent-level match {parent_pct:.1f}% < 95%")
        print(f"  Need to iterate rules until >= 95%")

    # Print mismatches for debugging
    if misses > 0:
        print(f"\n--- Mismatches ---")
        for r in results:
            if r['status'] == '✗':
                ev = f" ***{r['trade_event']}" if r['trade_event'] else ""
                print(f"  {r['time']}: got={r['got_scenario']} exp={r['expected_scenario']} "
                      f"reason={r['reason']} info={r['info']}{ev}")

    return results

if __name__ == '__main__':
    main()
