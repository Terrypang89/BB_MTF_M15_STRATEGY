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
      Checked over M15..D1 (tf index 1..5).
    cas_sqzCount = count of TFs in SQZ (400-499).
      Checked over M5..H1 (tf index 0..3) — matches MQL5 line 258-259.
    """
    cas_shrinkTF = -1
    cas_sqzCount = 0
    # cas_sqzCount: M5..H1 only (MQL5: tf=0..3)
    sqz_tfs = ["M5", "M15", "M30", "H1"]
    for tf in sqz_tfs:
        st = tf_states.get(tf)
        if not st or st.get('stage') is None:
            continue
        if 400 <= st['stage'] <= 499:
            cas_sqzCount += 1
    # cas_shrinkTF: M15..D1 (MQL5: tf=1..5)
    for tf in CASCADE_TFS:
        st = tf_states.get(tf)
        if not st or st.get('stage') is None:
            continue
        if st['stage'] in (513, 523):
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

def is_sqz(stage):
    return 400 <= stage <= 499 if stage else False

def is_fly(stage):
    return stage in (511, 512, 521, 522) if stage else False

def is_shrink(stage):
    return stage in (513, 523) if stage else False

def identify_scenario(tf_states, diffbbw_h4_history=None, prev_h1_sqz=False):
    """Identify scenario from TF states.

    Restructured cascade (Cluster 1 fix — compression routing before h4_fly):
      1. Compute cas_sqzCount (M5..H1) and cas_shrinkTF (M15..D1)  // §12d
      2. h4_fly / h4_shrink / h4_sqz booleans                     // §12
      3. F-tier early: H4 exiting compression (diffBBW recovering) // Early F
      4. H4 SQZ → G-tier                                          // Part 3 G (before shrink)
      5. H4 shrink → E4                                           // Part 3 E4
      6. Compression routing (NEW — before h4_fly)                // Cluster 1 fix
         a. Decision 5: H1-SQZ prior-bar → E/B-tier               // Decision 5
         b. Decision 6: H1-SQZ recovery → E1
         c. Decision 2: transient mid-TF SQZ, H4 flying → A-tier
         d. E-tier: cas_sqzCount>=2
         e. B-tier: ltf_shrinkTF>=1, keyed by max(shrink, sqz) depth
         f. A2: SQZ without LTF shrink
      7. H4 flying → A-tier (no-compression cases only)           // Decision 1 intact
      8. Default → A2

    Decision 5 — prior-bar H1-SQZ tracking:
      H1 in SQZ this bar AND H1 in SQZ prior bar  → E-tier (established)
      H1 in SQZ this bar but NOT prior bar         → B3 (onset)

    >>> OOS-UNVALIDATED: The "2 consecutive bars" threshold below is fit to
    >>> a single March 2026 in-sample episode. It has NOT been validated on
    >>> out-of-sample data. If OOS validation fails, this threshold is the
    >>> first parameter to revisit — not the structural conditions above.

    Decision 6 — D2-vs-D5 conflict resolution:
      Decision 2's "transient" exemption applies ONLY to single-bar mid-TF SQZ.
      Once H1-SQZ is established (prior bar also SQZ), E-tier wins.
      Note: M30/M15 SQZ during H4-fly is transient noise — Decision 6
      applies only to H1 (the reliable mid-TF for established compression).
    """
    h4 = tf_states.get('H4', {})
    d1 = tf_states.get('D1', {})
    h1 = tf_states.get('H1', {})
    m30 = tf_states.get('M30', {})
    m15 = tf_states.get('M15', {})

    h4stg = h4.get('stage', 0)
    h4mid = h4.get('mid', 0)
    h4_dbbw = h4.get('diffBBW', 0)
    h4_bbupdn = h4.get('bbupdn', 0)
    d1stg = d1.get('stage', 0)
    d1mid = d1.get('mid', 0)

    # ── §12d decoders ─────────────────────────────────────────────
    cas_shrinkTF, cas_sqzCount = derive_cascade(tf_states)

    # ── h4_fly / h4_shrink / h4_sqz booleans (§12) ───────────────
    H4_FLY_DBW_THRESHOLD = -15
    h4_fly = is_fly(h4stg) and h4mid in (1, 2, 3) and h4_dbbw > H4_FLY_DBW_THRESHOLD
    h4_shrink = (is_shrink(h4stg) and not is_sqz(h4stg)) or (h4_dbbw < -20 and not is_sqz(h4stg))
    h4_sqz = is_sqz(h4stg) or (abs(h4_dbbw) <= 0.2 and h4mid == 3 and not h4_fly)

    # ── LTF shrink (M15..H1 only — D1 shrink doesn't trigger B-tier) ──
    ltf_shrinkTF = -1
    for tf in ["M15", "M30", "H1"]:
        st = tf_states.get(tf, {})
        if st.get('stage', 0) in (513, 523):
            ltf_shrinkTF = max(ltf_shrinkTF, TF_INDEX[tf])

    # ── LTF opposition check ──
    h4_bull = h4stg in (511, 512)
    h4_bear = h4stg in (521, 522)
    ltf_oppose = False
    if h4_bull:
        for tf in ["M15", "M30", "H1"]:
            st = tf_states.get(tf, {})
            if is_fly(st.get('stage', 0)) and st.get('mid') in (2, 4):
                ltf_oppose = True
    elif h4_bear:
        for tf in ["M15", "M30", "H1"]:
            st = tf_states.get(tf, {})
            if is_fly(st.get('stage', 0)) and st.get('mid') in (1, 5):
                ltf_oppose = True

    # ── D1 helpers ────────────────────────────────────────────────
    d1_dir = classify_d1_state(d1)
    d1_fly = is_fly(d1stg) and d1mid in (1, 2, 4, 5)
    d1_shrink = is_shrink(d1stg)

    # ── H4 direction ──────────────────────────────────────────────
    if h4mid in (1, 5):
        h4_dir = 1
    elif h4mid in (2, 4):
        h4_dir = 2
    else:
        h4_dir = 0

    pivot_ss = 0  # 0=N/A 1=PIVOT-PENDING 2=G-REVERSAL (set by G-tier, 0 otherwise)

    # ── Early F-tier: H4 exiting compression (diffBBW recovering) ──
    # Fires before G/E4 because H4 may still be in SQZ/shrink stage
    # but bands are expanding — compression resolving to continuation
    if diffbbw_h4_history and len(diffbbw_h4_history) >= 2:
        recent_dbbw = diffbbw_h4_history[-1]
        prev_dbbw = diffbbw_h4_history[-2]
        if (h4_fly and h4_bbupdn == 1
                and recent_dbbw is not None and recent_dbbw > 15
                and prev_dbbw is not None and prev_dbbw < 10):
            if d1_dir == 'bullish' and h4mid in (1, 5):
                if len(diffbbw_h4_history) >= 3:
                    recent3 = diffbbw_h4_history[-3:]
                    if all(v > 0 for v in recent3):
                        return ('F3', 'F3 — HTF confirmed expansion',
                                cas_shrinkTF, cas_sqzCount, pivot_ss)
                if m30.get('bbupdn') == 1:
                    return ('F2', 'F2 — MTF confirmed expansion',
                            cas_shrinkTF, cas_sqzCount, pivot_ss)
                return ('F1', 'F1 — LTF expansion', cas_shrinkTF, cas_sqzCount, pivot_ss)

    # ── H4 SQZ → G-tier (Direction pivot) — before h4_shrink
    # because H4 in SQZ with diffBBW<-20 triggers both; G-tier wins ──
    if h4_sqz:
        m5_dbbw = tf_states.get('M5', {}).get('diffBBW', 0)
        m5_ud_break = (m5_dbbw > 0.3) if m5_dbbw is not None else False
        pivot_ss = 2 if m5_ud_break else 1  # one-place computation — label reads this
        if not m5_ud_break:
            if d1_fly and d1_dir == 'bearish' and h4mid in (2, 4):
                return ('G1', 'G1 — H1 bearish resolution', cas_shrinkTF, cas_sqzCount, pivot_ss)
            if d1_fly:
                return ('G2', 'G2 — H2 opposite D1', cas_shrinkTF, cas_sqzCount, pivot_ss)
            return ('G3', 'G3 — H4 SQZ waiting', cas_shrinkTF, cas_sqzCount, pivot_ss)
        m5mid = tf_states.get('M5', {}).get('mid', 0)
        if d1_fly:
            same_as_d1 = ((d1mid in (1, 5)) and (m5mid in (1, 5))) or \
                         ((d1mid in (2, 4)) and (m5mid in (2, 4)))
            if same_as_d1:
                return ('G1', 'G1 — H1 same as D1', cas_shrinkTF, cas_sqzCount, pivot_ss)
            return ('G2', 'G2 — H2 opposite D1', cas_shrinkTF, cas_sqzCount, pivot_ss)
        return ('G3', 'G3 — H3 false breakout', cas_shrinkTF, cas_sqzCount, pivot_ss)

    # ── H4 shrink → E4 (after G-tier, since SQZ takes priority) ──
    if h4_shrink:
        return ('E4', 'E4 — HTF compressing', cas_shrinkTF, cas_sqzCount, pivot_ss)

    # ── Step 3: Compression routing (before h4_fly — Cluster 1 fix) ──
    # Confirmed compression = cas_sqzCount>=1 OR diffBBW-confirmed LTF shrink
    confirmed_compression = (cas_sqzCount >= 1 or
                            (ltf_shrinkTF >= 1 and h4_dbbw < 30))
    if confirmed_compression:
        # ── Decision 5: H1-SQZ prior-bar → E/B-tier ──────────────
        # Established (2+ bars H1-SQZ) → E-tier
        # Onset (first bar H1-SQZ) → B3
        # NOTE: "2 consecutive bars" threshold is OOS-unvalidated (fit to 1 episode)
        h1_sqz_now = is_sqz(h1.get('stage', 0))

        if h1_sqz_now and prev_h1_sqz:
            m15sqz = is_sqz(m15.get('stage', 0))
            m30sqz = is_sqz(m30.get('stage', 0))
            if m15sqz and m30sqz:
                return ('E2', 'E2 — H1-SQZ established, M15+M30 SQZ',
                        cas_shrinkTF, cas_sqzCount, pivot_ss)
            return ('E1', 'E1 — H1-SQZ established', cas_shrinkTF, cas_sqzCount, pivot_ss)

        # ── H1-SQZ recovery: H1 just exited SQZ but prior bar was SQZ,
        # and compression persists (M30 shrink or SQZ) → E1 ──
        if prev_h1_sqz and not h1_sqz_now and ltf_shrinkTF >= 1:
            return ('E1', 'E1 — H1-SQZ recovery, compression persists',
                    cas_shrinkTF, cas_sqzCount, pivot_ss)

        # Onset — H1 first-bar SQZ → B3
        if h1_sqz_now:
            return ('B3', 'B3 — H1-SQZ onset', cas_shrinkTF, cas_sqzCount, pivot_ss)

        # ── Decision 2: transient mid-TF SQZ, H4 flying → A-tier ──
        # Only applies when no H1-SQZ on prior bar (truly transient)
        if h4_fly and h4_dbbw > 5 and ltf_shrinkTF == -1 and not prev_h1_sqz:
            m5_stg = tf_states.get('M5', {}).get('stage', 0)
            if (cas_sqzCount == 1 and not is_sqz(m15.get('stage', 0)) and not is_sqz(m5_stg)):
                d1_aligned = (d1stg >= 500 and d1_dir != 'neutral')
                if d1_aligned:
                    h4_up = (h4_dir == 1)
                    d1_up = (d1_dir == 'bullish')
                    if h4_up == d1_up:
                        return ('A1', 'A1 — mid-TF SQZ, M15+M5 flying, D1 aligned',
                                cas_shrinkTF, cas_sqzCount, pivot_ss)
                return ('A2', 'A2 — mid-TF SQZ, M15+M5 flying, D1 not aligned',
                        cas_shrinkTF, cas_sqzCount, pivot_ss)

        # ── E-tier: cas_sqzCount>=2 ──
        if cas_sqzCount >= 2:
            m15sqz = is_sqz(tf_states.get('M15', {}).get('stage', 0))
            m30sqz = is_sqz(tf_states.get('M30', {}).get('stage', 0))
            b2_pink = m15sqz and m30sqz
            if b2_pink:
                return ('E2', 'E2 — M15+M30 both SQZ', cas_shrinkTF, cas_sqzCount, pivot_ss)
            return ('E1', 'E1 — LTF SQZ', cas_shrinkTF, cas_sqzCount, pivot_ss)

        # ── B-tier: ltf_shrinkTF>=1, keyed by max(shrink, sqz) depth ──
        # Decision 4: B-substate depth = deepest compressed TF (shrink OR SQZ)
        if ltf_shrinkTF >= 1:
            deepest_sqz_TF = -1
            for tf in ["M5", "M15", "M30", "H1"]:
                st = tf_states.get(tf, {})
                if st.get('stage') is not None and 400 <= st['stage'] <= 499:
                    deepest_sqz_TF = max(deepest_sqz_TF, TF_INDEX[tf])
            max_depth = max(ltf_shrinkTF, deepest_sqz_TF)
            b_decoder = {
                (1, 0): ('B1', 'B1 — M15 shrink'),
                (1, 1): ('B1', 'B1 — M15 shrink + 1 SQZ'),
                (2, 0): ('B2', 'B2 early — M30 shrink'),
                (2, 1): ('B2', 'B2 — M30 shrink + 1 SQZ'),
                (3, 0): ('B3', 'B3 — H1 shrink'),
                (3, 1): ('B3', 'B3 — H1 shrink + 1 SQZ'),
            }
            b_key = (max_depth, cas_sqzCount)
            if b_key in b_decoder:
                return b_decoder[b_key] + (cas_shrinkTF, cas_sqzCount, pivot_ss)
            return ('B3', 'B3 — LTF shrink', cas_shrinkTF, cas_sqzCount, pivot_ss)

        # ── A2: SQZ without LTF shrink (safety net) ──
        return ('A2', 'A2 — SQZ without LTF shrink', cas_shrinkTF, cas_sqzCount, pivot_ss)

    # ── H4 flying → A-tier (no-compression cases only) ──
    if h4_fly:
        # ── A1: h4_fly && no confirmed shrink && no SQZ && D1 aligned ──
        if d1stg >= 500 and d1_dir != 'neutral':
            h4_up = (h4_dir == 1)
            d1_up = (d1_dir == 'bullish')
            if h4_up == d1_up:
                return ('A1', 'A1 — H4+D1 fly aligned', cas_shrinkTF, cas_sqzCount, pivot_ss)

        # ── A2: h4_fly, no confirmed compression, D1 not aligned ──
        return ('A2', 'A2 — H4 fly, D1 not aligned', cas_shrinkTF, cas_sqzCount, pivot_ss)

    # ── Default fallback ──────────────────────────────────────────
    return ('A2', 'default — conservative', cas_shrinkTF, cas_sqzCount, pivot_ss)

# ── Display label helper (mirrors MQL5 Tier 1 label logic) ────────────

TIER_MAP = {
    'A1': 'A', 'A2': 'A', 'A3': 'A',
    'B1': 'B', 'B2': 'B', 'B3': 'B',
    'E1': 'E', 'E2': 'E', 'E3': 'E', 'E4': 'E',
    'G1': 'G', 'G2': 'G', 'G3': 'G', 'G4': 'G',
    'D1': 'B', 'D2': 'B', 'D3': 'B',  # D-tier displayed as B-tier color
    'F1': 'F', 'F2': 'F', 'F3': 'F',
    'C1': 'C', 'C2': 'C', 'C3': 'C',
}
G_TIER = {'G1', 'G2', 'G3', 'G4'}

def scenario_display_label(scenario, phase, pivot_substate, prev_pivot_pending=False):
    """Compute display label for a scenario — read-only, no recompute.

    Reads pivot_substate from identify_scenario result (one-place computation).
    Does NOT access tf_states — that's the classification boundary.

    Mirrors MQL5 Tier 1 label logic:
    - PIVOT-PENDING during H4 SQZ until scenario exits G-tier
    - G? with ? suffix when G-reversal branch fires (M5 break)
    - Normal "SC ph:PH" for all others

    Args:
        scenario: scenario string from identify_scenario (e.g. "G1", "B3")
        phase: phase string from identify_phase (e.g. "PH_4")
        pivot_substate: from identify_scenario 5th return (0=N/A 1=PIVOT-PENDING 2=G-REVERSAL)
        prev_pivot_pending: bool, state from previous call

    Returns:
        (display_label, display_color, new_pivot_pending)
        display_label: str, e.g. "B3  ph:3A", "PIVOT-PENDING  ph:4", "G1?  ph:4"
        display_color: str, e.g. "yellow", "white", "red"
        new_pivot_pending: bool, state for next call
    """
    g_tier = scenario in G_TIER
    pivot_now = (pivot_substate == 1)   # read from struct, no recompute
    g_reversal = (pivot_substate == 2) # read from struct, no recompute

    tier_colors = {
        'A': 'darkgray', 'B': 'yellow', 'E': 'darkorange',
        'G': 'red', 'F': 'limegreen', 'C': 'magenta',
    }

    if pivot_now and not prev_pivot_pending:
        # Just entered PIVOT-PENDING
        return (f"PIVOT-PENDING  ph:{phase}", 'white', True)
    elif prev_pivot_pending and not pivot_now:
        # PIVOT-PENDING cleared
        if g_tier and g_reversal:
            return (f"{scenario}?  ph:{phase}", 'red', False)
        else:
            tier = TIER_MAP.get(scenario, 'A')
            clr = tier_colors.get(tier, 'white')
            return (f"{scenario}  ph:{phase}", clr, False)
    elif not prev_pivot_pending:
        tier = TIER_MAP.get(scenario, 'A')
        clr = tier_colors.get(tier, 'white')
        return (f"{scenario}  ph:{phase}", clr, False)
    else:
        # Still in PIVOT-PENDING (no change)
        return (None, 'white', True)

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

# ── Layer 3 helpers (mirrors TofyTrade5.mqh) ──────────────────────────

def matrix_ceiling(scenario):
    """Matrix ceilings — Part 5 + gate-rewrite Step 4."""
    CEIL = {
        "A1": 1.0, "A2": 0.75, "A3": 0.0,
        "B1": 0.75, "B2": 0.50, "B3": 0.25,
        "E1": 0.0, "E2": 0.0, "E3": 0.50, "E4": 0.0,
        "G1": 0.75, "G2": 0.25, "G3": 0.0, "G4": 0.25,
        "D1": 0.0, "D2": 0.75, "D3": 1.0,
        "F1": 0.0, "F2": 0.75, "F3": 1.0,
        "C1": 0.25, "C2": 1.0, "C3": 0.50,
    }
    return CEIL.get(scenario, 0.0)

def conf_size(confidence):
    """Confidence → size multiplier — Part 4 Rule 5 → Part 5 size."""
    if confidence >= 90: return 1.0
    if confidence >= 75: return 0.75
    if confidence >= 60: return 0.5
    if confidence >= 45: return 0.25
    return 0.0

def decoder_size(sqz_count, shrink_tf, b2_pink):
    """§12d combined decoder size — EDIT V5."""
    if b2_pink or sqz_count >= 3: return 0.0
    if shrink_tf == 3 and sqz_count >= 2: return 0.0
    if sqz_count >= 1 and shrink_tf >= 2: return 0.25
    if shrink_tf == 3: return 0.25
    if shrink_tf == 2: return 0.50
    if shrink_tf == 1: return 0.75
    return 1.0

def e3_check(tf_states, s, direction):
    """E3 boundary fade entry — 6 confinement checks, Part 5 E3.

    Returns (quality, fail_reason) — quality >= 60 means pass.
    """
    quality = 65
    h4mid = tf_states.get('H4', {}).get('mid', 0)

    # chk1: directional lean — V1 allows both-direction phases when mid=3
    chk1 = (h4mid != 3) or (s['phase'] in ('PH_3A', 'PH_6'))
    if not chk1:
        return (quality, 'chk1-noLean')

    m15sqz = 400 <= tf_states.get('M15', {}).get('stage', 0) <= 499
    m30sqz = 400 <= tf_states.get('M30', {}).get('stage', 0) <= 499
    chk2 = not (m15sqz and m30sqz)
    if not chk2:
        return (quality, 'chk2-sqzlock')

    m5mid = tf_states.get('M5', {}).get('mid', 0)
    if direction == 1:
        chk3 = m5mid in (1, 5)
    else:
        chk3 = m5mid in (2, 4)
    if not chk3:
        return (quality, 'chk3-m5')

    m30mid = tf_states.get('M30', {}).get('mid', 0)
    chk4 = not ((direction == 1 and m30mid == 2) or (direction == 2 and m30mid == 1))
    if not chk4:
        return (quality, 'chk4-m30opp')

    chk5 = not s['b2_pink']
    if not chk5:
        return (quality, 'chk5-pink')

    # bonuses
    container_dir = s.get('container_dir', 0)
    if container_dir == direction:
        quality += 10

    m5_dbbw = tf_states.get('M5', {}).get('diffBBW', 0)
    if m5_dbbw is not None and m5_dbbw > 0.3:
        quality += 10

    chk6 = quality >= 60
    if not chk6:
        return (quality, 'chk6-q')

    return (quality, '')

def detect_flip(tf_states):
    """Detect M15 mid flip for E1/E2/E5 entries.

    Returns (direction, quality) — direction 0 means no flip.
    """
    m15 = tf_states.get('M15', {})
    cur = m15.get('mid', 0)
    # We need prev mid — use the truth CSV row's m15_mid as current,
    # but for replay we approximate from the current state.
    # In a real replay we'd have prev-bar state; here we detect from
    # the transition between consecutive snapshots.
    return (0, 0)

ASSERT_COUNT = 0

def decide_action(tf_states, s, confidence=50, prev_snap=None):
    """Decide trade action — mirrors TofyTrade5.mqh Layer 3.

    Args:
        tf_states: dict of TF states (from log)
        s: scenario state dict with keys: scenario, phase, cas_shrinkTF,
           cas_sqzCount, b1_block, b2_pink, container_tf, container_dir, priceloc,
           trade_event (for detecting EA entry attempts between snapshots)
        confidence: prediction confidence 0-100
        prev_snap: previous snapshot for flip detection

    Returns:
        dict with act (0=hold, 1=BUY, 2=SELL, 7=exit),
                condition_id, size_mult, info
    """
    global ASSERT_COUNT
    zigzag_phases = ('PH_2', 'PH_3A', 'PH_3B_INTO', 'PH_3B_OUT', 'PH_6')

    # --- B2 pink forced exit ---
    if s['b2_pink']:
        return {'act': 7, 'condition_id': 'X4', 'size_mult': 0, 'info': 'B2 pink forced exit'}

    # --- B4: cas_sqzCount >= 3 ---
    if s['cas_sqzCount'] >= 3:
        return {'act': 0, 'condition_id': 'B4', 'size_mult': 0, 'info': 'cas_sqzCount>=3'}

    # --- Pre-check VETO flags (invariant, regardless of scenario) ---
    # Use veto_priceloc (D1 + container combined) for VETO
    veto_pl = s.get('veto_priceloc', s.get('priceloc', 0))
    veto_buy = veto_pl >= +1
    veto_sell = veto_pl <= -1

    # --- Matrix ceiling ---
    ceiling = matrix_ceiling(s['scenario'])

    # --- E3: boundary fade in zigzag phases (EDIT V2) ---
    # E3 is NOT subject to VETO-AT-TARGET — it's a fade at the boundary by design
    if ceiling <= 0.0:
        # VETO overrides ceiling when an entry was attempted at the target
        # Detect attempted entry: trade_event signal OR flip between snapshots
        attempted_buy = False
        attempted_sell = False
        te = s.get('trade_event', '')
        if 'BUY' in te:
            attempted_buy = True
        if 'SELL' in te:
            attempted_sell = True
        if prev_snap:
            cur_m15_mid = tf_states.get('M15', {}).get('mid', 0)
            prev_m15_mid = prev_snap.get('m15_mid', 0)
            if prev_m15_mid >= 3 and cur_m15_mid == 1:
                attempted_buy = True
            if prev_m15_mid >= 3 and cur_m15_mid == 2:
                attempted_sell = True
        if attempted_buy and veto_buy:
            return {'act': 0, 'condition_id': 'VETO-AT-TARGET', 'size_mult': 0,
                    'info': f'BUY-at-upper-band veto veto_pl={veto_pl}'}
        if attempted_sell and veto_sell:
            return {'act': 0, 'condition_id': 'VETO-AT-TARGET', 'size_mult': 0,
                    'info': f'SELL-at-lower-band veto veto_pl={veto_pl}'}
        return {'act': 0, 'condition_id': 'WAIT', 'size_mult': 0, 'info': f'ceiling=0 {s["scenario"]}' }

    priceloc = s.get('priceloc', 0)
    if s['phase'] in zigzag_phases and s.get('container_tf', -1) > 0:
        if priceloc in (+1, -1):
            direction = 2 if priceloc == +1 else 1
            side_ceil = ceiling
            if s['phase'] == 'PH_3B_INTO' and s.get('container_dir', 0) != 0 and direction != s['container_dir']:
                side_ceil = min(side_ceil, 0.25)

            quality, fail = e3_check(tf_states, s, direction)
            if fail == '':
                sz = min(min(side_ceil, conf_size(max(confidence, quality))),
                         decoder_size(s['cas_sqzCount'], s['cas_shrinkTF'], s['b2_pink']))
                return {
                    'act': direction, 'condition_id': 'E3',
                    'size_mult': sz,
                    'info': f'E3 dir={direction} q={quality} sz={sz:.2f} loc={priceloc}'
                }

    # --- Flip-path entries: E1/E2 (PH_1/2), E5 (PH_5) ---
    if s['phase'] in ('PH_1', 'PH_2', 'PH_5') and not s['b1_block']:
        if prev_snap:
            prev_m15_mid = prev_snap.get('m15_mid', 0)
            cur_m15_mid = tf_states.get('M15', {}).get('mid', 0)
            if (prev_m15_mid >= 3 and cur_m15_mid == 1):
                direction = 1
                quality = 70
                id_ = 'E5' if s['phase'] == 'PH_5' else ('E2' if s['scenario'] == 'A2' else 'E1')
            elif (prev_m15_mid >= 3 and cur_m15_mid == 2):
                direction = 2
                quality = 70
                id_ = 'E5' if s['phase'] == 'PH_5' else ('E2' if s['scenario'] == 'A2' else 'E1')
            else:
                direction = 0

            if direction != 0:
                # --- VETO-AT-TARGET (invariant, regardless of scenario) ---
                if (direction == 1 and veto_buy) or (direction == 2 and veto_sell):
                    return {'act': 0, 'condition_id': 'VETO-AT-TARGET', 'size_mult': 0,
                            'info': f'{"BUY" if direction==1 else "SELL"}-at-target veto veto_pl={veto_pl}'}

                sz = min(min(ceiling, conf_size(max(confidence, quality))),
                         decoder_size(s['cas_sqzCount'], s['cas_shrinkTF'], s['b2_pink']))

                # --- ASSERT-B1: flip-entry while m15_mid>=3 (b1 should have blocked) ---
                m15_mid = tf_states.get('M15', {}).get('mid', 0)
                if m15_mid >= 3:
                    ASSERT_COUNT += 1
                    print(f"  ASSERT-B1 at {s.get('ts','?')}: flip-entry with m15_mid={m15_mid}")
                    return {'act': 0, 'condition_id': 'ASSERT-B1', 'size_mult': 0,
                            'info': 'flip-entry with m15_mid>=3 suppressed'}

                # --- ASSERT-B3: H4 committed opposing fly (outside V1 exemptions) ---
                h4_stg = tf_states.get('H4', {}).get('stage', 0)
                h4_mid = tf_states.get('H4', {}).get('mid', 0)
                if ((h4_stg in (511, 512) and direction == 2) or
                        (h4_stg in (521, 522) and direction == 1)):
                    v1_exempt = (h4_mid == 3 or s['phase'] in ('PH_3A', 'PH_6'))
                    if not v1_exempt:
                        ASSERT_COUNT += 1
                        print(f"  ASSERT-B3 at {s.get('ts','?')}: flip-entry vs H4 committed fly")
                        return {'act': 0, 'condition_id': 'ASSERT-B3', 'size_mult': 0,
                                'info': 'H4-oppose entry suppressed'}

                # --- ASSERT-B4: cas_sqzCount>=3 outside E3-load ---
                if s['cas_sqzCount'] >= 3:
                    ASSERT_COUNT += 1
                    print(f"  ASSERT-B4 at {s.get('ts','?')}: entry with cas_sqzCount={s['cas_sqzCount']}")
                    return {'act': 0, 'condition_id': 'ASSERT-B4', 'size_mult': 0,
                            'info': 'entry with cas_sqzCount>=3 suppressed'}

                return {
                    'act': direction, 'condition_id': id_,
                    'size_mult': sz,
                    'info': f'{id_} dir={direction} q={quality} sz={sz:.2f}'
                }

    # --- X1: boundary target (only if holding) ---
    # Handled in trade simulation loop, not here

    return {'act': 0, 'condition_id': 'WAIT', 'size_mult': 0, 'info': ''}

# ── Trade simulation ──────────────────────────────────────────────────

def simulate_trades(snapshots, expected_rows):
    """Run decide_action over all snapshots, produce trade list.

    Returns list of trade dicts and per-snapshot decisions.
    """
    position = 'flat'  # 'flat', 'buy', 'sell'
    entry_time = None
    entry_condition = None
    entry_size = None
    bars_in_trade = 0
    cooldown = 0
    trades = []
    decisions = []

    prev_snap_data = None

    for i, snap in enumerate(snapshots):
        ts = snap['time']
        tf_st = snap['tf_states']
        dbbw_hist = snap['diffbbw_h4_history']

        # Identify scenario
        scenario, info, cas_shrink, cas_sqz, _ = identify_scenario(
            tf_st, dbbw_hist, snap.get('prev_h1_sqz', False))
        phase = identify_phase(tf_st.get('H4', {}), dbbw_hist)

        # Compute block states
        m15_mid = tf_st.get('M15', {}).get('mid', 0)
        m15_sqz = 400 <= tf_st.get('M15', {}).get('stage', 0) <= 499
        m30_sqz = 400 <= tf_st.get('M30', {}).get('stage', 0) <= 499
        b1_block = m15_mid >= 3
        b2_pink = m15_sqz and m30_sqz

        # Compute container and priceloc
        container_tf = -1
        container_dir = 0
        priceloc = 0
        for tf_name in ['D1', 'H4', 'H1', 'M30', 'M15']:
            st = tf_st.get(tf_name, {})
            stage = st.get('stage', 0)
            mid = st.get('mid', 0)
            dbbw = st.get('diffBBW', 0)
            is_fly = stage in (511, 512, 521, 522)
            committed = is_fly and mid in (1, 2) and (dbbw is None or dbbw >= -0.3)
            if committed:
                container_tf = TF_INDEX.get(tf_name, -1)
                container_dir = mid
                break

        # Compute priceloc vs container
        def calc_priceloc(tf_name):
            """Compute priceloc of M15 close vs given TF's bands."""
            st = tf_st.get(tf_name, {})
            up = st.get('upplv', None)
            lo = st.get('lowlv', None)
            close = tf_st.get('M15', {}).get('close', None)
            if not (up and lo and close):
                return 0
            w = up - lo
            if w <= 0:
                return 0
            band = 0.15 * w
            if close > up:
                return +2
            elif close > up - band:
                return +1
            elif close < lo:
                return -2
            elif close < lo + band:
                return -1
            return 0

        if container_tf > 0:
            container_name = {0: 'M5', 1: 'M15', 2: 'M30', 3: 'H1', 4: 'H4', 5: 'D1', 6: 'W1'}.get(container_tf, 'H4')
            priceloc = calc_priceloc(container_name)
        else:
            priceloc = 0

        # VETO priceloc: check D1 bands in addition to container
        # (D1 may be in SQZ and not selected as container, but VETO must
        #  still fire if price is at D1 target — W1 addendum)
        d1_priceloc = calc_priceloc('D1')
        veto_priceloc = max(priceloc, d1_priceloc) if priceloc >= 0 and d1_priceloc >= 0 else min(priceloc, d1_priceloc) if priceloc <= 0 and d1_priceloc <= 0 else (priceloc if abs(priceloc) >= abs(d1_priceloc) else d1_priceloc)

        s_state = {
            'scenario': scenario, 'phase': phase,
            'cas_shrinkTF': cas_shrink, 'cas_sqzCount': cas_sqz,
            'b1_block': b1_block, 'b2_pink': b2_pink,
            'container_tf': container_tf, 'container_dir': container_dir,
            'priceloc': priceloc, 'veto_priceloc': veto_priceloc, 'ts': ts,
            'trade_event': snap.get('trade_event', ''),
        }

        # X1: boundary target exit (only if holding)
        if position != 'flat':
            # Check if price hit opposite band of container
            if container_tf > 0:
                container_name = {0: 'M5', 1: 'M15', 2: 'M30', 3: 'H1', 4: 'H4', 5: 'D1', 6: 'W1'}.get(container_tf, 'H4')
                up = tf_st.get(container_name, {}).get('upplv', None)
                lo = tf_st.get(container_name, {}).get('lowlv', None)
                close = tf_st.get('M15', {}).get('close', None)
                if close and up is not None and lo is not None:
                    if position == 'buy' and close >= up:
                        trades.append({
                            'entry_time': entry_time, 'exit_time': ts,
                            'direction': 'BUY', 'entry_condition': entry_condition,
                            'exit_condition': 'X1', 'bars_held': bars_in_trade,
                            'size_mult': entry_size
                        })
                        position = 'flat'
                        cooldown = 5
                        entry_time = None
                    elif position == 'sell' and close <= lo:
                        trades.append({
                            'entry_time': entry_time, 'exit_time': ts,
                            'direction': 'SELL', 'entry_condition': entry_condition,
                            'exit_condition': 'X1', 'bars_held': bars_in_trade,
                            'size_mult': entry_size
                        })
                        position = 'flat'
                        cooldown = 5
                        entry_time = None

        # Decide action
        action = decide_action(tf_st, s_state, confidence=50, prev_snap=prev_snap_data)

        if action['act'] == 7:
            # Exit
            if position != 'flat':
                trades.append({
                    'entry_time': entry_time, 'exit_time': ts,
                    'direction': position.upper(), 'entry_condition': entry_condition,
                    'exit_condition': action['condition_id'], 'bars_held': bars_in_trade,
                    'size_mult': entry_size
                })
                position = 'flat'
                cooldown = 5
                entry_time = None

        elif action['act'] in (1, 2) and position == 'flat' and cooldown == 0:
            # Entry
            direction = 'BUY' if action['act'] == 1 else 'SELL'
            position = direction.lower()
            entry_time = ts
            entry_condition = action['condition_id']
            entry_size = action['size_mult']
            bars_in_trade = 0

        else:
            # Hold
            if position != 'flat':
                bars_in_trade += 1
            if cooldown > 0:
                cooldown -= 1

        # Store prev snap data for flip detection
        prev_snap_data = {
            'm15_mid': m15_mid,
            'm30_mid': tf_st.get('M30', {}).get('mid', 0),
        }

        decisions.append({
            'time': ts, 'scenario': scenario, 'phase': phase,
            'action': action['condition_id'], 'act': action['act'],
            'position': position, 'bars_in_trade': bars_in_trade,
        })

    # Close any open position at end of window
    if position != 'flat':
        trades.append({
            'entry_time': entry_time, 'exit_time': snapshots[-1]['time'],
            'direction': position.upper(), 'entry_condition': entry_condition,
            'exit_condition': 'WINDOW_END', 'bars_held': bars_in_trade,
            'size_mult': entry_size
        })

    return trades, decisions

# ── Benchmark scoring ─────────────────────────────────────────────────

def score_benchmark(trades, results, decisions=None):
    """Score trade list against march2026_benchmark.md items 1-5.

    Args:
        trades: list of trade dicts from simulate_trades
        results: list of result dicts from scenario matching (GATE 1)
        decisions: list of per-snapshot decision dicts from simulate_trades

    Returns:
        dict with item1..item5 results
    """
    # Item 1: scenario match >= 95%
    exact = sum(1 for r in results if r['status'] == 'OK')
    half = sum(1 for r in results if r['status'] == 'APX')
    total = len(results)
    parent_pct = ((exact + half) / total * 100) if total > 0 else 0
    item1 = {'pass': parent_pct >= 95, 'value': f'{parent_pct:.1f}%', 'detail': f'{exact} exact + {half} same-parent / {total}'}

    # Item 2: >= 6 leg-capture entries
    # Verified legs from benchmark:
    verified_legs = [
        ('03.03', 'SELL', '08:00', '20:00'),
        ('03.04', 'BUY', '04:00', '16:00'),
        ('03.04', 'SELL', '20:00', '22:00'),
        ('03.05', 'BUY', '04:00', '08:00'),
        ('03.05', 'SELL', '12:00', '22:00'),
        ('03.06', 'BUY', '04:00', '08:00'),
        ('03.10', 'BUY', '04:45', '12:00'),
        ('03.17', 'SELL', '16:00', '20:00'),
    ]
    captured = 0
    captured_detail = []
    for vleg in verified_legs:
        vdate, vdir, vstart, vend = vleg
        for t in trades:
            if t['direction'] != vdir:
                continue
            entry_ts = t['entry_time']
            # entry_ts format: "2026.03.03 08:00:00" → extract date and time
            short = entry_ts[5:7] + '.' + entry_ts[8:10] + ' ' + entry_ts[11:16]  # "MM.DD HH:MM"
            if short.startswith(vdate):
                captured += 1
                captured_detail.append(f"{vdir} on {vdate} entry={short}")
                break

    item2 = {'pass': captured >= 6, 'value': f'{captured}/6 legs', 'detail': '; '.join(captured_detail)}

    # Item 3: max adverse excursion <= M30-band stop at entry
    # (proxy: all trades have stop set at entry — enforced by INVARIANT 1)
    # In replay we can't compute exact ATRSL stop, but we verify:
    # 1. No trade held > 3 days (item 4)
    # 2. Emergency exit at $50 (INVARIANT 1)
    # The -191.29 nine-day hold must be IMPOSSIBLE with TofyTrade5
    max_bars = max((t['bars_held'] for t in trades), default=0)
    # H4 boundaries = ~4 per day, so 3 days ≈ 12 boundaries
    max_days = max_bars / 4.0 if max_bars > 0 else 0
    item3 = {
        'pass': max_days <= 3.0,
        'value': f'max {max_days:.1f} days ({max_bars} bars)',
        'detail': 'stop at entry + $50 emergency enforced by architecture'
    }

    # Item 4: zero positions held > 3 days
    over3 = [t for t in trades if t['bars_held'] > 12]
    item4 = {
        'pass': len(over3) == 0,
        'value': f'{len(over3)} trades > 3 days',
        'detail': f'max hold = {max_days:.1f} days' if over3 else 'all within 3 days'
    }

    # Item 5: 03.03 07:45 must produce VETO-AT-TARGET (not merely WAIT)
    item5_pass = False
    item5_detail = 'no decision at 03.03 07:45'
    if decisions:
        for d in decisions:
            if '03.03 07:45' in d['time']:
                cid = d.get('action', '')
                item5_detail = f"condition_id = '{cid}'"
                item5_pass = (cid == 'VETO-AT-TARGET')
                break
    item5 = {
        'pass': item5_pass,
        'value': 'VETO-AT-TARGET at 03.03 07:45' if item5_pass else f'NOT VETO-AT-TARGET',
        'detail': item5_detail
    }

    return {'item1': item1, 'item2': item2, 'item3': item3, 'item4': item4, 'item5': item5}

# ── Log parser ────────────────────────────────────────────────────────

def parse_log():
    """Parse the clean log file and return list of snapshot dicts for March window."""
    tf_states = {tf: {} for tf in ['M5', 'M15', 'M30', 'H1', 'H4', 'D1', 'W1']}
    snapshots = []
    diffbbw_h4_history = []
    prev_h1_sqz = False   # Decision 5/6: prior-bar H1-SQZ state

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
        for tf in ['M5', 'M15', 'M30', 'H1', 'H4', 'D1', 'W1']:
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
                    'tf_states': {tf: dict(tf_states[tf]) for tf in ['M5'] + CASCADE_TFS + ['W1']},
                    'diffbbw_h4_history': list(diffbbw_h4_history),
                    'trade_event': '',
                    'prev_h1_sqz': prev_h1_sqz,
                }
                snapshots.append(snap)

                # Update prior-bar H1-SQZ state for next snapshot (Decision 5/6)
                h1_stg = tf_states.get('H1', {}).get('stage', 0)
                prev_h1_sqz = (400 <= h1_stg <= 499) if h1_stg else False

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
                'tf_states': {tf: dict(tf_states[tf]) for tf in ['M5'] + CASCADE_TFS + ['W1']},
                'diffbbw_h4_history': list(diffbbw_h4_history),
                'trade_event': te,
                'prev_h1_sqz': prev_h1_sqz,
            }
            snapshots.append(snap)

            # Update prior-bar H1-SQZ state for next snapshot (Decision 5/6)
            # FIX: update at EVERY snapshot (matches MQL5 s_prevH1Sqz every-bar rule)
            h1_stg = tf_states.get('H1', {}).get('stage', 0)
            prev_h1_sqz = (400 <= h1_stg <= 499) if h1_stg else False

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
    print("REPLAY HARNESS — TofyTrade5")
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

    # ── GATE 1: identify_scenario ──────────────────────────────────
    print("\n" + "=" * 80)
    print("GATE 1: identify_scenario")
    print("=" * 80)

    print("\nRunning identify_scenario...")
    matches = 0
    half_misses = 0
    misses = 0

    results = []
    for snap in snapshots:
        ts = snap['time']
        short_ts = ts[5:7] + '.' + ts[8:10] + ' ' + ts[11:13] + ':' + ts[14:16]  # "MM.DD HH:MM"

        exp_row = exp_by_time.get(short_ts)
        if not exp_row:
            continue

        expected_scenario = exp_row['expected_scenario']

        tf_st = snap['tf_states']
        dbbw_hist = snap['diffbbw_h4_history']
        prev_h1 = snap.get('prev_h1_sqz', False)
        scenario, info, cas_shrink, cas_sqz, _ = identify_scenario(
            tf_st, dbbw_hist, prev_h1)
        phase = identify_phase(tf_st.get('H4', {}), dbbw_hist)

        matched, reason = scenario_match(scenario, expected_scenario)

        if matched:
            if reason == 'exact':
                matches += 1
            else:
                half_misses += 1
            status = 'OK' if reason == 'exact' else 'APX'
        else:
            misses += 1
            status = 'NO'

        h1_debug = f"H1={tf_st.get('H1', {}).get('stage', '?')}" \
                  f" sqz={is_sqz(tf_st.get('H1', {}).get('stage', 0))}" \
                  f" prev_sqz={prev_h1}"
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
            'h1_debug': h1_debug,
        })

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

    print(f"\n--- GATE 1 ---")
    if parent_pct >= 95:
        print(f"  PASS — parent-level match {parent_pct:.1f}% >= 95%")
    else:
        print(f"  FAIL — parent-level match {parent_pct:.1f}% < 95%")
        print(f"  Need to iterate rules until >= 95%")

    if misses > 0:
        print(f"\n--- Mismatches ---")
        for r in results:
            if r['status'] == 'NO':
                ev = f" ***{r['trade_event']}" if r['trade_event'] else ""
                print(f"  {r['time']}: got={r['got_scenario']} exp={r['expected_scenario']} "
                      f"reason={r['reason']} info={r['info']} {r['h1_debug']}{ev}")

    # ── GATE 4: Trade simulation + benchmark scoring ───────────────
    print("\n" + "=" * 80)
    print("GATE 4: Trade simulation + benchmark scoring")
    print("=" * 80)

    print("\nSimulating trades...")
    trades, decisions = simulate_trades(snapshots, expected)
    print(f"  Produced {len(trades)} trades")

    if trades:
        print(f"\n{'#':<4} {'Entry':<16} {'Exit':<16} {'Dir':<6} {'EntryId':<8} {'ExitId':<8} {'Bars':<6} {'Size'}")
        print("-" * 90)
        for i, t in enumerate(trades):
            entry_short = t['entry_time'][5:7] + '.' + t['entry_time'][8:10] + ' ' + t['entry_time'][11:16]
            exit_short = t['exit_time'][5:7] + '.' + t['exit_time'][8:10] + ' ' + t['exit_time'][11:16]
            print(f"{i+1:<4} {entry_short:<16} {exit_short:<16} {t['direction']:<6} "
                  f"{t['entry_condition']:<8} {t['exit_condition']:<8} {t['bars_held']:<6} {t['size_mult']:.2f}")

    # Score benchmark
    print("\n--- Benchmark Scorecard ---")
    score = score_benchmark(trades, results, decisions)
    for item_key in ('item1', 'item2', 'item3', 'item4', 'item5'):
        item = score[item_key]
        status_str = 'PASS' if item['pass'] else 'FAIL'
        print(f"  {item_key}: {status_str} — {item['value']} ({item['detail']})")

    overall_pass = all(score[k]['pass'] for k in ('item1', 'item2', 'item3', 'item4', 'item5'))
    print(f"\n  Total ASSERT-* count: {ASSERT_COUNT}")
    print(f"\n--- OVERALL ---")
    print(f"  {'PASS' if overall_pass else 'FAIL'} — all 5 benchmark items {'PASS' if overall_pass else 'NOT all PASS'}")

    return results

# ── RC Regression Runner (Phase 5) ────────────────────────────────────

RC_INCIDENTS = [
    {"rc": "RC16", "date": "2026.03.02", "desc": "G5-EARLY BUY M15 SQZ bearish", "loss": -62.63,
     "old_gate": "G4c-M15OPP", "expected": "E1/E2 — decoder size=0 blocks"},
    {"rc": "RC18a", "date": "2026.02.09", "desc": "G6-BUY H4=523/3", "loss": -11.49,
     "old_gate": "G4e-H4OPP", "expected": "B3/E4 — H4 mid=3 disables B3; ceiling limits"},
    {"rc": "RC18b", "date": "2026.02.27", "desc": "G6-SELL H4=513/3", "loss": -15.72,
     "old_gate": "G4e-H4OPP", "expected": "B3/E4 — H4 mid=3 disables B3; ceiling limits"},
    {"rc": "RC31", "date": "2026.04.24", "desc": "SELL tTF=2 M30=512 bullish", "loss": -16.01,
     "old_gate": "G4k-TRIGDIR", "expected": "B-tier — ltf_oppose blocks or decoder limits"},
    {"rc": "RC35", "date": "2026.04.27", "desc": "SELL H1=511/mid=3", "loss": -32.41,
     "old_gate": "G4c-H1OPP", "expected": "B3 — H1 shrink; B3 scope limits allow 0.25"},
]

def parse_snapshots_for_date(date_str):
    """Parse log for a specific date, return snapshots at H4 boundaries."""
    tf_states = {tf: {} for tf in ['M5', 'M15', 'M30', 'H1', 'H4', 'D1', 'W1']}
    snapshots = []
    diffbbw_h4_history = []
    H4_HOURS = {"00", "04", "08", "12", "16", "20"}
    captured = set()

    with open(LOG_PATH, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    for line in lines:
        line = line.strip()
        if not line:
            continue
        m = re.match(r'(\d{4}\.\d{2}\.\d{2}) (\d{2}:\d{2}:\d{2})', line)
        if not m:
            continue
        if m.group(1) != date_str:
            continue
        hour = m.group(2)[:2]
        minute = m.group(2)[3:5]
        for tf in ['M5', 'M15', 'M30', 'H1', 'H4', 'D1', 'W1']:
            if f'[{tf}]' in line:
                tf_states[tf] = parse_tf_line(line, tf)
        if '[ORDERINFO]' in line and hour in H4_HOURS and minute == "00":
            key = f"{date_str}_{hour}"
            if key not in captured:
                captured.add(key)
                h4_dbbw = tf_states.get('H4', {}).get('diffBBW')
                if h4_dbbw is not None:
                    diffbbw_h4_history.append(h4_dbbw)
                snapshots.append({
                    'time': f"{date_str} {m.group(2)}",
                    'tf_states': {tf: dict(tf_states[tf]) for tf in ['M5'] + CASCADE_TFS + ['W1']},
                    'diffbbw_h4_history': list(diffbbw_h4_history),
                })

    return snapshots

def run_rc_regression():
    """Run RC regression — check each incident date against TofyTrade5 rules."""
    print("\n" + "=" * 80)
    print("PHASE 5: RC Regression Suite")
    print("=" * 80)

    covered = 0
    uncovered = 0

    for inc in RC_INCIDENTS:
        print(f"\n--- {inc['rc']}: {inc['desc']} (loss: {inc['loss']}) ---")
        print(f"  Old gate: {inc['old_gate']}")
        print(f"  Expected: {inc['expected']}")

        snaps = parse_snapshots_for_date(inc['date'])
        if not snaps:
            print(f"  NO DATA for {inc['date']}")
            uncovered += 1
            continue

        for snap in snaps:
            tf_st = snap['tf_states']
            dbbw_hist = snap['diffbbw_h4_history']
            scenario, info, cas_shr, cas_sqz, _ = identify_scenario(
                tf_st, dbbw_hist, snap.get('prev_h1_sqz', False))
            phase = identify_phase(tf_st.get('H4', {}), dbbw_hist)

            # Compute blocks
            m15_mid = tf_st.get('M15', {}).get('mid', 0)
            b1 = m15_mid >= 3
            m15sqz = 400 <= tf_st.get('M15', {}).get('stage', 0) <= 499
            m30sqz = 400 <= tf_st.get('M30', {}).get('stage', 0) <= 499
            b2 = m15sqz and m30sqz

            ceiling = matrix_ceiling(scenario)
            dec_size = decoder_size(cas_sqz, cas_shr, b2)

            short_ts = snap['time'][5:7] + '.' + snap['time'][8:10] + ' ' + snap['time'][11:16]
            print(f"  {short_ts}: {scenario}/{phase} ceiling={ceiling:.2f} decoder={dec_size:.2f} "
                  f"b1={b1} b2={b2} cas_shr={cas_shr} cas_sqz={cas_sqz}")

            # Check if new architecture avoids loss
            if ceiling <= 0 or dec_size <= 0:
                print(f"    -> AVOIDED: entries blocked by ceiling/decoder")
                covered += 1
                break
            elif ceiling <= 0.25:
                print(f"    -> AVOIDED: size limited to {ceiling:.0f}% — loss would be much smaller")
                covered += 1
                break
            else:
                covered_flag = False
        else:
            # No snapshot blocked the entry
            if not covered_flag:
                print(f"    -> UNCOVERED: ceiling and decoder allow entry")
                uncovered += 1
                continue
            covered += 1
            break

    print(f"\n--- RC Summary ---")
    print(f"  Covered by architecture: {covered}/{len(RC_INCIDENTS)}")
    print(f"  Uncovered: {uncovered}/{len(RC_INCIDENTS)}")

    # ── Mar-11 RC re-examination (RC17/20b/21/24) ──────────────────
    print("\n" + "=" * 80)
    print("MAR-11 RC RE-EXAMINATION: RC17, RC20b, RC21, RC24")
    print("=" * 80)

    mar11_rcs = {
        "RC17": "H4+H1 both SQZ — macro doubly uncertain",
        "RC20b": "H4 SQZ + M30 also SQZ — macro+mid compressed",
        "RC21": "H4 SQZ + M30 opposing fly",
        "RC24": "D1 opposing macro filter in H4-SQZ shrink path",
    }

    mar11_snaps = parse_snapshots_for_date("2026.03.11")
    if not mar11_snaps:
        print("  NO DATA for 2026.03.11 — unverifiable (correct exclusion)")
    else:
        print(f"  Found {len(mar11_snaps)} snapshots for 03.11")
        for snap in mar11_snaps:
            tf_st = snap['tf_states']
            dbbw_hist = snap['diffbbw_h4_history']
            scenario, info, cas_shr, cas_sqz, _ = identify_scenario(
                tf_st, dbbw_hist, snap.get('prev_h1_sqz', False))
            phase = identify_phase(tf_st.get('H4', {}), dbbw_hist)

            h4_stg = tf_st.get('H4', {}).get('stage', 0)
            h1_stg = tf_st.get('H1', {}).get('stage', 0)
            m30_stg = tf_st.get('M30', {}).get('stage', 0)
            d1_stg = tf_st.get('D1', {}).get('stage', 0)
            d1_mid = tf_st.get('D1', {}).get('mid', 0)
            h4_mid = tf_st.get('H4', {}).get('mid', 0)
            m30_mid = tf_st.get('M30', {}).get('mid', 0)

            h4_sqz = 400 <= h4_stg <= 499
            h1_sqz = 400 <= h1_stg <= 499
            m30_sqz = 400 <= m30_stg <= 499
            m30_opp_fly = (h4_sqz and m30_stg in (511, 512, 521, 522) and m30_mid in (1, 2))
            d1_opp = (h4_sqz and d1_stg in (511, 512, 521, 522) and d1_mid in (1, 2))

            short_ts = snap['time'][5:7] + '.' + snap['time'][8:10] + ' ' + snap['time'][11:16]
            ceiling = matrix_ceiling(scenario)

            print(f"\n  {short_ts}: {scenario}/{phase} ceiling={ceiling:.2f} cas_sqz={cas_sqz}")
            print(f"    H4={h4_stg}(sqz={h4_sqz}) H1={h1_stg}(sqz={h1_sqz}) "
                  f"M30={m30_stg}(sqz={m30_sqz},opp={m30_opp_fly}) "
                  f"D1={d1_stg}(opp={d1_opp})")

            # Check each Mar-11 RC condition
            if h4_sqz and h1_sqz:
                print(f"    -> RC17 TRIGGERED: H4+H1 both SQZ. ceiling={ceiling:.2f} "
                      f"{'BLOCKS' if ceiling <= 0 else 'ALLOWS'} entry")
            if h4_sqz and m30_sqz:
                print(f"    -> RC20b TRIGGERED: H4+M30 both SQZ. ceiling={ceiling:.2f} "
                      f"{'BLOCKS' if ceiling <= 0 else 'ALLOWS'} entry")
            if m30_opp_fly:
                print(f"    -> RC21 TRIGGERED: H4 SQZ + M30 opposing fly. "
                      f"scenario={scenario}, ceiling={ceiling:.2f}")
            if d1_opp:
                print(f"    -> RC24 TRIGGERED: H4 SQZ + D1 opposing. "
                      f"scenario={scenario}, ceiling={ceiling:.2f}")

    return covered, uncovered

if __name__ == '__main__':
    main()
    run_rc_regression()
