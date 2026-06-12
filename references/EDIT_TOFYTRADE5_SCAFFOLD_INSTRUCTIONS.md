# EDIT_TOFYTRADE5_SCAFFOLD_INSTRUCTIONS.md
# Target: new files scripts/TofyTrade5.mqh, scripts/replay_harness.py, references/fixtures/
# Branch: tofy5
# Goal: restructure EA into 3 layers mapping 1:1 to backtest_chart_analysis.md Parts 3/4/5,
#       validated by log replay BEFORE any MT5 backtest.
#
# Source documents (read ALL before starting):
# - references/backtest_chart_analysis.md  (Parts 3,4,5 + §12/12b/12c/12d + Section 13 phases)
# - references/log_verification/20260302_0400-20260320_0900_analysis_part2.md  (verified truth data)
# - references/log_examples.md  (log field formats)
# - scripts/TofyTrade4.mqh  (current code — source of structs, helpers, and RC incident comments)
# - references/Backtest_data/V30.02/20260606_clean.log  (replay data source)

---

## CRITICAL RULES

1. Execute PHASES IN ORDER. Each phase ends with a verification gate.
   DO NOT proceed to the next phase if the gate fails — report and stop.
2. NEVER invent struct field names. Read TofyIncludeSimple.mqh first and use the
   real field names for: BBW_stage, BB_diffMid_Trend, BB_Mid, diffBBW (the band
   width velocity — find its actual field name), and BBUpDn state (find its
   actual field name). If a field does not exist in the struct, report it —
   do not fabricate access to it.
3. TF index convention from TofyTrade4.mqh: BB_datas[0]=M5, [1]=M15, [2]=M30,
   [3]=H1, [4]=H4, [5]=D1, [6]=W1. Bar indexing: LA=current, LA_1=prev, LA_2=prev2.
4. Every decision rule in TofyTrade5 MUST carry a comment citing its document
   section (e.g. "// Part 5 B3 scope limits" or "// §12d decoder row cas=2/sqz=1").
   Logic without a doc citation is forbidden.
5. Commit at the end of each phase with the message given. Report each commit hash.
6. NO MT5 backtest in this task. Replay only.

---

## PHASE 0 — Extract Truth Fixtures from the Verified March Analysis

### 0.1 Create references/fixtures/march2026_truth.csv

Parse the Section 1 table of
references/log_verification/20260302_0400-20260320_0900_analysis_part2.md
(78 rows) into CSV with columns:

```
row,timestamp,h4_bbw,h4_mid,h4_ud,h1_bbw,h1_mid,h1_ud,m30_bbw,m30_mid,m30_ud,m15_bbw,m15_mid,m15_ud,d1_bbw,d1_mid,diffbbw_h4,cas_shrinktf,cas_sqzcount,trade_event
```

### 0.2 Create references/fixtures/march2026_expected.csv

For each of the 78 rows, derive the EXPECTED scenario+phase from the
Section 3 period analysis in the same file (Periods 1–onward assign scenario/phase
to time ranges). Columns:

```
row,timestamp,expected_scenario,expected_substate,expected_phase,expected_b1_block,expected_b2_pink,notes
```

Rules for derivation:
- expected_scenario/substate/phase come from the Period that contains the timestamp
- expected_b1_block = TRUE where M15 mid >= 3 (per Part 5 B1)
- expected_b2_pink = TRUE only where M15 BBW in 400-499 AND M30 BBW in 400-499
  simultaneously (per Part 5 B2 — NOT cas_sqzCount alone)

### 0.3 Create references/fixtures/march2026_benchmark.md

Write the acceptance benchmark for this window:

```
REPLAY BENCHMARK — 2026.03.02 04:00 to 2026.03.20 09:00
1. IdentifyScenario must match expected_scenario on >= 95% of the 78 rows
   (substate mismatches within same parent scenario count as half-miss)
2. DecideAction over the window must produce >= 6 leg-capture entries
   matching these verified arrow legs:
   - 03.03 ~08:00-20:00 SELL leg (crash) — entry valid once M30+M15 mid=2
     and B3 disabled (H4 mid=3 by 16:00 / diffBBW contradicts 512 label)
   - 03.04 ~04:00-16:00 BUY leg (H4 mid=3 → B3 off)
   - 03.04 20:00 SELL leg (H4 mid=2 aligned)
   - 03.05 04:00-08:00 BUY leg (short)
   - 03.05 12:00-22:00 SELL leg (full alignment — cleanest of window)
   - 03.06 04:00-08:00 BUY recovery leg
   - 03.10 04:45+ BUY leg (the one TofyTrade4 actually caught)
   - 03.17-03.19 SELL run (must be held, not churned: no exit within
     3 bars of entry on a mid=3 wobble; X1/boundary or trailing stop only)
3. Max single-trade adverse excursion <= M30-band stop distance at entry
   (the -191.29 nine-day hold must be IMPOSSIBLE: stop set at entry,
    emergency $50 exit unconditional)
4. Zero positions held > 3 days
```

### GATE 0: show me the 3 fixture files (head -20 of each) before continuing.

### Commit: "Phase 0: extract March 2026 truth fixtures and replay benchmark"

---

## PHASE 1 — Replay Harness (Python, before any MQL5)

### 1.1 Create scripts/replay_harness.py

A Python script that:
1. Parses references/Backtest_data/V30.02/20260606_clean.log into per-bar records
   (reuse/extend scripts/extract_log_data.py which already exists and parsed
   this log for the part2 analysis)
2. Implements identify_scenario(record) in Python as the REFERENCE
   implementation of Layer 1 (rules below in Phase 2 — implement them here first)
3. Runs it over the March window, joins against march2026_expected.csv,
   prints: match %, per-row mismatches with reason
4. Implements decide_action() the same way (rules in Phase 4) and replays the
   window producing a trade list: entries/exits with timestamp, direction,
   condition ID (E1-E6/X1-X4/B1-B4), size
5. Scores the trade list against march2026_benchmark.md and prints PASS/FAIL
   per benchmark item

The Python harness is the executable spec. The MQL5 code in later phases is a
PORT of this harness — when they disagree, the harness (validated against
fixtures) is the truth.

### GATE 1: run the harness with identify_scenario only.
Report match % against expected. Iterate the rules until >= 95%.
DO NOT tune by hardcoding timestamps — only by improving the general rules.
If a fixture row appears wrongly labeled (the expected value itself is wrong),
flag it to me with evidence instead of forcing a match.

### Commit: "Phase 1: replay harness with scenario identification >= 95% on March fixtures"

---

## PHASE 2 — TofyTrade5.mqh Layer 1: IdentifyScenario (Part 3 + §12d)

### 2.1 Create scripts/TofyTrade5.mqh with header

```cpp
#property version   "31.00"
// TofyTrade5 — three-layer architecture mapping 1:1 to backtest_chart_analysis.md
// Layer 1 IdentifyScenario  = Part 3  (+ §12 CHECK-HTF, §12d decoder, Section 13 phases)
// Layer 2 PredictNext       = Part 4  (Rules 1-5)
// Layer 3 DecideAction      = Part 5  (E1-E6 / X1-X4 / B1-B4, size, stops)
// RULE: every branch cites its document section. No uncited logic.
#include <TofyIncludeSimple.mqh>
#define MIN_HOLD_BARS 3
#define POST_EXIT_COOLDOWN 5
#define MAX_FLOATING_LOSS_USD 50.0   // checked UNCONDITIONALLY every tick — no gate may suppress
```

### 2.2 Enums and state struct

```cpp
enum SCENARIO { SC_NONE,
  SC_A1, SC_A2, SC_A3,
  SC_B1, SC_B2, SC_B3,
  SC_E1, SC_E2, SC_E3, SC_E4,
  SC_G1, SC_G2, SC_G3, SC_G4,      // Direction pivot (doc Scenario G/H naming)
  SC_D1s, SC_D2s, SC_D3s,          // suffix s to avoid clash with TF names
  SC_F1, SC_F2, SC_F3,
  SC_C1, SC_C2, SC_C3 };

enum PHASE { PH_NONE, PH_1, PH_2, PH_3A, PH_3B_INTO, PH_3B_OUT, PH_4, PH_5, PH_6 };

struct ScenarioState {
  SCENARIO scenario;
  PHASE    phase;
  int      cas_shrinkTF;   // §12d
  int      cas_sqzCount;   // §12d
  bool     b1_block;       // M15 mid >= 3            // Part 5 B1
  bool     b2_pink;        // M15 BBW 400-499 AND M30 BBW 400-499  // Part 5 B2
  string   info;
};
```

### 2.3 IdentifyScenario rules (port from the validated Python harness)

Implementation order inside the function — cite each:

1. Compute cas_sqzCount and cas_shrinkTF from per-TF BBW_stage  // §12d tables
2. Compute b2_pink: M15 AND M30 both in 400-499                 // Part 5 B2
3. Compute b1_block: M15 diffMid >= 3                            // Part 5 B1
4. CHECK HTF FIRST: classify the H4 x D1 state cell              // §12 CHECK-HTF table
   using diffMid + diffBBW as PRIMARY, BBW_stage as confirmation // EDIT V4 normative rule
   - if H4 BBW_stage label contradicts (sign of diffBBW + mid),
     override the label                                           // §12 lag rule, 7 March conflicts
5. Map to scenario per Part 3 tier tables + §12d sub-state rows
6. Phase from diffBBW trajectory (needs last N values — maintain a
   small ring buffer of diffBBW_H4):                              // Section 13 phase table
   sustained positive=PH_1/2; sustained negative=PH_3*; near-zero
   minimum=PH_4; zero-cross to sharply positive=PH_5;
   alternating sign over lookback=PH_6
   3A vs 3B-INTO vs 3B-OUT discriminated by H4 mid (=3 → 3A) and
   by whether H4 BBUpDn is exiting SQZ (0→1) with legs gaining → 3B-OUT

### GATE 2: cross-check — run the same 78 fixture rows through a quick
MQL5-side test (or desk-check 10 representative rows by hand against the
Python harness output). The two implementations must agree on all checked rows.

### Commit: "Phase 2: TofyTrade5 Layer 1 IdentifyScenario ported from validated harness"

---

## PHASE 3 — Layer 2: PredictNext (Part 4) — salvage PredictNextTrend

### 3.1 Port from TofyTrade4.mqh, KEEP:
- TF_DirectionScore() scoring skeleton (stage+mid+transitions)
- PredictTFNextStage() labels
- TF_BandTouchSummary()

### 3.2 CHANGE:
- Add diffBBW term to TF_DirectionScore (positive expanding reinforces the
  directional score; negative damps it)                          // Part 4 Rule 5 diffBBW adjust
- Output struct extended:

```cpp
struct Prediction {
  int direction;        // 1 BUY / 2 SELL / 0 NEUTRAL            // Part 4 Rule 1
  int target_tf;        // TF index whose outer band is target   // Part 4 Rule 2 table
  int timeline_bars;    // expected bars to target                // Part 4 Rule 3 table
  SCENARIO next_scenario;                                        // Part 4 Rule 4 CHECK trees
  int confidence;       // 0-100                                  // Part 4 Rule 5 matrix
  bool reversal;
  string info;
};
Prediction PredictNext(ScenarioState &s, BB_MTF_Data_struct &bb[]);
```

- Confidence is GATED BY SCENARIO: PH_4 or SC_G4 (whipsaw) forces
  confidence band "None" regardless of score                    // Part 4 Rule 5
- The chart label drawing stays (useful for Part 6 log verification),
  but the Prediction return value is now CONSUMED by Layer 3.

### Commit: "Phase 3: Layer 2 PredictNext — rewired PredictNextTrend, scenario-gated confidence"

---

## PHASE 4 — Layer 3: DecideAction (Part 5) — gates deleted, conditions in

### 4.1 The G4x chain is NOT ported. Delete-list (do not carry over):
G4-BLOCK, G4b-H1OPP, G4c-M15OPP, G4d-M30SID, G4e-H4OPP, G4j-D1OPP,
G4k-M15SHRKopp, G4k-TRIGDIR, G5-WEAK quality patchwork, adaptive-trigger
special cases. Their intents live in Layers 1-2 (an opposing-TF
configuration IS a different scenario / lower confidence, not a veto).

### 4.2 Structure

```cpp
struct TradeAction {
  int    act;          // 0 none / 1 open BUY / 2 open SELL / 7 exit
  string condition_id; // "E1".."E6","X1".."X4","B1".."B4","WAIT"
  double size_mult;    // min(confidence size, §12d decoder size)   // EDIT V5
  double stop_price;   // M30-band stop AT ENTRY per Part 5 table
  string info;
};
TradeAction DecideAction(ScenarioState &s, Prediction &p,
                         BB_MTF_Data_struct &bb[], double &close[],
                         PositionInfo &pos);
```

### 4.3 Entry rules (cite Part 5 Entry Conditions + EDIT V2 priority-by-phase):
- PH_2/PH_3A/PH_3B*/PH_6 → E3 boundary entry is PRIMARY:
  PriceLoc at highest-flying-TF outer band (compute from close vs that TF's
  band buffers) + directional lean + the 6 confinement checks   // Part 5 E3
  Both directions allowed in PH_3A/PH_6 (B3 disabled there)     // EDIT V1
- PH_1 → E1/E2 on M15 mid flip (keep DetectM5Transition for THIS path only,
  stripped of its embedded G4 blocks)                            // Part 5 E1/E2
- PH_5 → E5/E6 transition entries                                // Part 5 E5/E6
- SC_E3 → E4 arm only (no order until M15 confirms → E5)

### 4.4 Block rules — exactly four:
- B1: M15 diffMid >= 3 blocks NEW entries only; existing position holds
- B2: M15+M30 both BBW 400-499 → exit all + no entries
- B3: H4 committed opposing fly — WITH the V1 scope limits:
  disabled when H4 mid==3, when diffBBW contradicts the H4 label,
  and in PH_3A/PH_6                                              // EDIT V1
- B4: cas_sqzCount >= 3 → no entries

### 4.5 Exit rules (EDIT V3 hierarchy):
- PH_2/3A/3B/6: X1 boundary-target PRIMARY (opposite band of the leg's
  confinement TF). X2 (M15 fade) only if price stalled >= 3 bars short of
  target or the target TF band is invalidated. NO exit within 3 bars of
  entry on a mid=3 wobble.
- PH_1: X2 primary.
- X4 = B2 pink forced exit.
- ALWAYS: stop_price set at entry (GetATRSLStop kept from TofyTrade4) and
  MAX_FLOATING_LOSS_USD checked unconditionally before anything else.

### 4.6 Sizing:
size_mult = MathMin(confidence_size(p.confidence), decoder_size(s))  // EDIT V5
and it MUST be applied to the actual lot calculation (CalcLotSize kept) —
no "unused; lots always baseLot".

### GATE 4: port decide_action back into replay_harness.py (or run the
fixtures through it) and score against march2026_benchmark.md.
Report each benchmark item PASS/FAIL with the produced trade list.
Iterate rules (general rules only, no timestamp hardcoding) until items
1, 3, 4 PASS and item 2 reaches >= 6 captured legs.

### Commit: "Phase 4: Layer 3 DecideAction — E/X/B conditions, G4x chain removed, benchmark PASS"

---

## PHASE 5 — RC Incident Regression Suite

Every RC comment in TofyTrade4.mqh cites a dated losing trade
(e.g. "RC16: Mar-02 ... -62.63", "RC24: Jan-16 19:55 ... -97.03",
"RC31: Apr-24 ...", "RC35: Apr-27 03:10 ... -32.41", "RC39", "RC18: Feb-09 /
Feb-27 / Apr-20 ..."). 

1. Grep TofyTrade4.mqh for all "RC" comments; list each with its date,
   direction, TF states, and loss.
2. For each incident whose date exists in available logs, add a row to
   references/fixtures/rc_regressions.csv:
   timestamp, tf_states, old_failure, expected_new_behavior
   (expected behavior derived from the document: most are "no entry —
   scenario X / confidence below floor" or "entry allowed but stop limits
   loss to Y").
3. Run the replay harness over each incident timestamp and report whether
   TofyTrade5 rules avoid the original loss WITHOUT a dedicated veto.
4. Any incident the new architecture does NOT handle → report it to me
   with the scenario readout. Do not add a patch gate. We fix the document
   rule first.

### Commit: "Phase 5: RC incident regression suite — N/M incidents covered by architecture"

---

## FINAL REPORT (paste back to me)

1. Fixture extraction stats (rows, scenarios covered)
2. Layer 1 match % + list of remaining mismatches with reasons
3. Benchmark scorecard (items 1-4, PASS/FAIL, trade list for the window)
4. RC regression coverage (N of M, list of uncovered)
5. All commit hashes
6. Any struct fields that did not exist (diffBBW / BBUpDn field names found)
7. Open questions where the document is ambiguous — listed, NOT silently resolved
