# Validation Status — Decision 8 Freeze (Corrected)

> Generated: 2026-06-14 | Corrected: 2026-06-14
> In-sample period: March 2-20, 2026 (78 snapshots) — 83.3% parent-level match
> OOS period: Jan 1 - Feb 27 + Apr 1 - Apr 29, 2026 (349 snapshots)

## Terminology Clarification

| Term | Meaning |
|------|---------|
| G-tier on SQZ bars | "Compression detected, pivot pending" — NOT "this will resolve as G reversal" |
| G-vs-F discrimination | Predicting whether compression resolves as G (reversal) or F (continuation) |
| G reversal resolution | H4-SQZ resolves with directional pivot opposite to prior trend |
| F continuation resolution | H4-SQZ resolves with explosive expansion in same direction |

The 36/36 "G-tier detection" in OOS = **compression-state detection**, not G-vs-F discrimination.
Every H4-SQZ bar was correctly flagged as G2/G3 (pivot-pending). But none of the 7 OOS episodes
actually reversed — all 7 continued in F direction. The G-vs-F discriminator was never tested.

---

## OOS-VALIDATED Rules (snapshot + prior-bar)

These rules have been tested on both in-sample (March) and out-of-sample (Jan-Feb+Apr) data.

| Rule | Description | In-Sample | OOS |
|------|-------------|-----------|-----|
| A-tier | H4-fly, no compression, D1-aligned → A1; D1-not-aligned → A2 | Multiple episodes | 74/349 snapshots (21.2%) |
| B-tier | LTF shrink keyed by max(shrink, sqz) depth → B1/B2/B3 | Multiple episodes | 81/349 snapshots (23.2%) |
| E-tier | cas_sqzCount>=2 → E1/E2; H4-shrink → E4 | Multiple episodes | 153/349 snapshots (43.8%) |
| G-tier compression entry | H4-SQZ detected → G2/G3 (pivot-pending state) | 03.09-03.10 | 36/36 SQZ bars (100%) |
| F continuation resolution | H4-SQZ resolves with explosive expansion | 03.10-03.18 | 7/7 episodes (100%) |
| Onset/Established | H1-SQZ first bar → B3; H1-SQZ 2+ bars → E1 | Decision 5 cascade | Consistent on OOS |
| D1-D6 | Decision cascade (priority routing, transient exemption, B-depth, B-decoder, H1-SQZ tracking, D2-vs-D5 resolution) | Full March replay | Full OOS replay |
| VETO-AT-TARGET | BUY-at-upper-band / SELL-at-lower-band veto | 03.03 07:45 — item 5 PASS | Architecture-enforced |
| Matrix ceilings | Scenario → ceiling mapping | Enforced | Enforced |
| Decoder size | cas_sqzCount + cas_shrinkTF → size multiplier | Enforced | Enforced |
| ASSERT-B1/B3/B4 | Invariant checks on flip-entries | 2 ASSERT-B3 in March | Architecture-enforced |

## STILL HYPOTHESIS — G Reversal Branch

The G reversal branch has never fired on OOS data.

| Rule | Description | Why Untested | Risk |
|------|-------------|--------------|------|
| G reversal resolution | H4-SQZ resolves with directional pivot opposite to prior trend | 0 of 7 OOS episodes resolved G — the reversal branch never executed | If G episodes are rare (<1 per quarter), this branch may remain unvalidated for months |
| G-vs-F discriminator | Predicting G (reversal) vs F (continuation) during PIVOT-PENDING | Requires episodes that resolve both ways — not available in current data | The discriminator may be correct or wrong; there's no way to tell without a G-resolving episode |
| 2-bar interlude threshold | "2 consecutive bars" for H1-SQZ established vs onset at G/F boundary | Never stressed during G→F transitions in OOS (no G→F transitions existed) | Threshold may be too short (noise) or too long (misses entries) |

**This is INSUFFICIENT-DATA, not a rule failure.** The G reversal branch is structurally
defined in the code but has no OOS evidence.

### Data Finding: Jan-Apr 2026 Resolution Mix

| Resolution | Count | Episodes |
|------------|-------|----------|
| F (continuation) | 7 | Ep1 (Jan 5), Ep2 (Jan 8-12), Ep3 (Jan 15-19), Ep4 (Jan 30-Feb 2), Ep5 (Feb 19-20), Ep6 (Apr 13-14), Ep7 (Apr 20-22) |
| G (reversal) | 0 | — |

**G (reversal) is the rare case.** Jan-Apr 2026 contained 7 H4-SQZ episodes and all resolved
as F (expansion continuation). No reversal occurred.

---

## Known False-Verification — ADiffBBW (Commit 21fad56)

Commit 21fad56 ("Phase 2: Port OOS-validated Layer 1 to MQL5 — diffBBW fix, GATE 2 100%")
claimed ADiffBBW was "verified against V30.02 log values." This claim was **CIRCULAR**:
the verification compared the COMMENT'S WLV example (4.66 vs 5.46) against the log,
but the CODE PATH read BBUppLV-BBLowLV (raw band width) instead of BBWLV (indicator WLV).

**What happened:**
- ADiffBBW computed `(BBUppLV[0]-BBLowLV[0] - (BBUppLV[1]-BBLowLV[1])) * 100`
- This produced values 10-100x larger than indicator diffBBW (e.g. 3081 vs 58.7)
- The indicator computes diffBBW as `(BBWLV[0]-BBWLV[1]) * 100` — using WLV, not raw band width
- The EA struct has BBWLV (populated via CopyBuffer from indicator buffer 8) and BB_diffBBW
  (populated by the indicator as `(BBWLV[LA]-BBWLV[LA_1])*100`) — both fields were available but unused by ADiffBBW

**Why GATE 2 wasn't exposed:**
- GATE 2 was a source-to-source desk-check (verify_mql5_port.py). Both the MQL5-sim and the
  Python harness read indicator diffBBW from the log. The EA's ADiffBBW code path was never
  exercised — it was dead code at GATE 2 time. The GATE 2 100% proved control-flow faithfulness,
  not data-input correctness.
- V31.02 was the first compiled EA run of the validated logic. It exposed the divergence:
  26.9% scenario match, 0% phase match, 0% diffBBW match on the 78 March bars.

**The real verification (never done until now):**
- WLV-based ADiffBBW vs indicator diffBBW at 132 March bars: 132/132 match (100%, within 1.0 tolerance)
- WLV-based ADiffBBW vs fixture diffBBW at 72 fixture bars: 72/72 match (100%)
- BBUppLV-based ADiffBBW at the same bars: 0/72 match — every bar off by 10-100x

**Fix applied:** ADiffBBW now reads `bb[tf].BBWLV[sh]` instead of `ABBUpper(bb,tf,sh)-ABBLower(bb,tf,sh)`.
One-line change. No indicator modification needed — BBWLV is already in the struct.

**V31.02 status:** V30.02 remains the frozen baseline. V31.02 is unverified — the compiled EA
hasn't been re-run with the fixed ADiffBBW to confirm scenario recovery to ~100%.

### Three Compiled-vs-Source Bugs Found (V31.02–V31.04)

All three bugs belong to the same family: **"a value/state not accessed or maintained
at the right point — logic correct, data plumbing wrong."** This is the class to watch
when the compiled EA diverges from the harness.

| Bug | What | Where | Root Cause | Fix |
|-----|------|-------|------------|-----|
| Bug 1 | ADiffBBW read `BBWLV[0]` (oldest bar) | `ADiffBBW(bb,tf,sh)` | `sh` parameter default 0 = slot [0] = oldest | Read `bb[tf].BB_diffBBW[LA]` directly |
| Bug 2 | Band-edge read `BBUppLV[0]` (oldest bar) | `ABBUpper/ABBLower(bb,tf,sh)` | Same `sh` pattern — default 0 = slot [0] | Inline `bb[tf].BBUppLV[LA]` at call sites |
| Bug 3 | `s_prevH1Sqz` timing — current-vs-prior | `IdentifyScenario` lines 313, 454, 465, 477 | Update-then-read with LA=current collapsed prior to current-bar value → Decision 6 (recovery) dead code | Capture-prior-then-update: `bool h1sqz_prior = s_prevH1Sqz;` before update, use `h1sqz_prior` in Decisions 5/6/2 |

**Bug 3 = the MQL5 never received the harness's prev_h1_sqz fix — and the
move-to-top was a partial fix that traded one bug for another.** The harness
(replay_harness.py:1383-1385, 1412-1415) updates `prev_h1_sqz` on every bar
AFTER reading it (read-then-update = current-vs-prior). The MQL5 code had
the update at the bottom of IdentifyScenario where it was unreachable — every
scenario path (B3, E1, E2, G-tier, etc.) returns before reaching it. The
move-to-top fix (V31.03) made the update reachable but introduced a new bug:
update-then-read with LA=current means both the update and the read access the
same bar → current-vs-current. The prior-bar check collapses to a tautology.
Decision 6 (recovery: `h1sqz_prior && !h1_sqz_now`) was dead code — can't be
SQZ and not-SQZ on the same bar.

**Impact:** Bug 3 caused B3 (H1-SQZ onset) to fire on every bar where H1 was
in SQZ, instead of E1 (H1-SQZ established) after the first bar. Decision 6
(recovery) never fired — H1 exiting SQZ with compression persisting could not
route to E1. This explains 6 of 10 V31.04 scenario mismatches (84.6% →
expected ~94.9% after fix).

**Lesson (committed → fixed):** Moving a state update to the top of a function
makes it reachable but doesn't guarantee correct timing. If the update and
reads share the same bar (LA=current), the prior-bar semantics collapse.
The fix is capture-prior-then-update: capture the prior value in a local
variable BEFORE updating the static, then use the captured value in reads.
The `sh` parameter pattern (Bugs 1+2) is misleading — default `sh=0`
reads slot [0] which is the OLDEST bar, not the current one. All helpers with
this pattern should be inlined with explicit `[LA]` indices.

### Candidate Periods for G-Reversal Validation

To validate the G reversal branch, a data period is needed containing at least 1 H4-SQZ episode
that resolves as a directional pivot (G).

| Candidate | Rationale | Status |
|-----------|-----------|--------|
| 2025 data | Full year — likely contains multiple G and F episodes | Need to check if logs exist |
| Sep-Dec 2026 | Future period — may contain reversal episodes | Not yet available |
| May-Jun 2026 | Immediate next quarter | May contain reversal episodes |
| V30.01 log (Jan 2026 only) | Already in repo but subset of V30.02 | Won't help — Ep1-Ep4 are already in OOS |

### OOS Episode Detail (2 Examples)

**Episode 2 — Jan 8-12, 2026**
```
01.08 16:00  G2  H4=423  SQZ *   ← entry: H4 enters compression
01.08 20:00  G2  H4=423  SQZ *   ← pivot-pending
01.09 04:00  G2  H4=423  SQZ *   ← pivot-pending
01.09 08:00  G2  H4=423  SQZ *   ← pivot-pending
01.09 12:00  G2  H4=423  SQZ *   ← pivot-pending
01.09 16:00  G2  H4=423  SQZ *   ← pivot-pending (8 bars total)
01.12 04:00  F3  H4=511  diffBBW=+67.8  ← resolution: F continuation
```

**Episode 5 — Feb 19-20, 2026**
```
02.19 16:00  G3  H4=423  SQZ *   ← entry: H4 enters compression
02.19 20:00  G3  H4=423  SQZ *   ← pivot-pending
02.20 04:00  G2  H4=423  SQZ *   ← pivot-pending
02.20 08:00  G2  H4=423  SQZ *   ← pivot-pending (8 bars total)
02.20 20:00  A2  H4=512  ← resolution: F continuation (F-tier missed)
```

### Harness Gap: G2→C1→C2/C3 forward transition not implemented

The G-tier returns G2 (reversal signal, pivot_substate=2) but does NOT
implement the G2→C1→C2/C3 forward transition. The reversal-confirmed states
(C1 = MTF reversal only, C2 = H4 confirmed new direction, C3 = H4 flipped
but W1/D1 still original) are doc-only, unimplemented in identify_scenario.
Must be built before the G-reversal branch can be validated on
reversal-containing data.

- **Affected tier:** G (Direction Pivot)
- **Affected sub-states:** G2, C1, C2, C3
- **Doc location:** Scenario G → Post-G2 Reversal Resolution Progression
- **Status:** OOS-UNVALIDATED — cannot validate until harness supports
  the G2→C1→C2/C3 state transitions

### Known Divergence: veto_priceloc (MQL5 vs Python, Layer 3 only)

MQL5 VETO (line 1087) uses `s.priceloc` — computed vs container TF only.
Python `decide_action()` (line 734) uses `veto_priceloc` — combines
container priceloc AND D1 priceloc (more-extreme-of-same-sign rule,
line 933). This means D1 can veto when in SQZ-but-not-container,
making Python stricter than MQL5.

- **Concrete divergence:** D1 in SQZ (not selected as container) + price
  at D1's upper band → MQL5: no VETO; Python: VETO fires.
- **Affected layer:** L3 only — does NOT feed back into L1 classification.
- **Resolution:** Phase 4. Python harness must match MQL5 for replay
  accuracy. Whether MQL5 should also check D1 (more defensive) is a
  design decision — D1 is the natural target for most trades.
- **Status:** UNRESOLVED — Python is strictly more defensive but
  behaviorally different.

### Phase 3 Fix Item: diffBBW Damping Thresholds

MQL5 PredictNext (TofyTrade5.mqh lines 600-603) applies diffBBW damping
with thresholds -0.5 (contracting) and 1.0 (expanding). These were
written for the percentage-era diffBBW formula — they are WRONG with
the absolute formula (flagged in integration note 6, line 1132).

- **Phase 3 fix:** re-derive thresholds for absolute diffBBW scale.
  Don't port the stale percentage-era values.
- **Affected:** PredictNext confidence scores — all confidence values
  are unreliable until thresholds are corrected.
- **Status:** STALE — must be fixed before GATE 3 validation.

### Phase 4 Verification Item: Store-vs-Recompute Equivalence

MQL5 STORES b1_block, b2_pink, and priceloc on the ScenarioState struct
(computed once per bar in IdentifyScenario). Python RECOMPUTES these
from raw BB data in the simulation loop. They are equivalent ONLY IF
Python's recompute uses identical inputs and timing to MQL5's stored
value — which is the SAME store-vs-recompute pattern that caused the
prev_h1_sqz divergence (assumed equivalent until timing differed).

- **Phase 4 check:** confirm Python's recomputation of b1_block,
  b2_pink (and veto_priceloc) matches MQL5's stored struct values
  bar-for-bar when DecideAction is built. Store-vs-recompute
  equivalence is assumed, not yet verified — same pattern as prev_h1_sqz.
- **Blocks:** Nothing now (L1 unaffected). Must be verified when L3
  is built, not silently trusted.
- **PredictNext prior-bar state:** MQL5 reads BB_datas[tf][LA_1]
  (prior-bar stage + mid) directly for TF_DirectionScore transitions.
  Python port must match MQL5 bar-for-bar — same class as prev_h1_sqz
  (store-vs-recompute with timing dependency). Must be verified when
  L2 is built, not silently trusted.

### Scenario Distribution (OOS — 349 snapshots)

| Scenario | Count | Pct |
|----------|-------|-----|
| E4 | 140 | 40.1% |
| B3 | 55 | 15.8% |
| A2 | 45 | 12.9% |
| A1 | 29 | 8.3% |
| G2 | 22 | 6.3% |
| B2 | 22 | 6.3% |
| G3 | 15 | 4.3% |
| E1 | 10 | 2.9% |
| B1 | 4 | 1.1% |
| E2 | 3 | 0.9% |
| F3 | 2 | 0.6% |
| F1 | 1 | 0.3% |
| F2 | 1 | 0.3% |
