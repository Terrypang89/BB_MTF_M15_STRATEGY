# EDIT_GATE_REWRITE_INSTRUCTIONS.md
# Target: scripts/TofyTrade5.mqh signal layer + references/backtest_chart_analysis.md Gate Decoder
# Branch: tofy5
# Purpose: replace the entire TofyTrade4 gate set with a condition/signal system
#          organized by scenario and phase. Gates as control flow are abolished;
#          what remains are SIGNALS (log labels), 3 INVARIANTS, and ASSERTIONS.
# Companion files: EDIT_TOFYTRADE5_SCAFFOLD_INSTRUCTIONS.md (Phases 0-5),
#                  EDIT_W1_CONTAINER_ADDENDUM_INSTRUCTIONS.md

---

## STEP 1 — Complete Gate Inventory (do this FIRST)

The disposition table below was built from a partial read of TofyTrade4.mqh.
Before applying anything:

```
grep -n "G[0-9]" scripts/TofyTrade4.mqh   (and grep -n "Gate:" )
```

List EVERY distinct gate label found. Any label NOT in the disposition table
below → STOP and report it to me with its code context. Do not silently drop
or silently keep it.

---

## STEP 2 — Disposition Table (old gate → fate)

### DELETED — intent absorbed by Layer 1 (scenario) or Layer 2 (confidence)

| Old gate | Original intent | Where the intent now lives |
|---|---|---|
| G4-BLOCK | M30/M15 mid conflict | Conflicting mids = different scenario (Layer 1); low score (Layer 2) |
| G4b-H1OPP | H1 committed fly opposes | H1 weighted ×2 in direction score → drags total below threshold |
| G4c-M15OPP | M15 fly/shrink/SQZ opposes | M15 state is part of scenario ID; opposing M15 = C1/noise scenario |
| G4d-M30SID | M30 flat + M15 opposing | Same — scenario, not veto |
| G4e-H4OPP / H4-OPPOSE | H4 committed fly opposes | H4 ×3 in score + EDIT V1 scope limits; ASSERT-B3 only |
| G4j-D1OPP | D1 opposes while H4 SQZ | D1 ×2 in score; G2 scenario = counter-D1 at 0.25× (allowed, sized) |
| G4k-M15SHRKopp | M15 opposing shrink w/ M30 trigger | Scenario ID covers it |
| G4k-TRIGDIR | Trigger TF stage contradicts direction | Cross-check rule (diffBBW/diffMid primary) makes this unreachable |
| G5-WEAK | Quality < 60 floor | Confidence band "None" → size 0; log reason in info, no gate |
| G5-NONE | No transition | No signal = no label needed |
| G0 / G0-HOLD | All-TF mid≥3 exit/hold | THE 03.17 winner-killer. Replaced by qualified X2 (W1c) — delete outright |
| G0b-WAIT | Cascade waiting | State [SC:*|PH:*] tag conveys this |
| G7-NEUTRAL | Prediction neutral | [PRED] label already carries direction=NEUTRAL |
| G1-FAIL / G1-OK | (verify purpose via grep) | Expected: info-only → fold into state tag; CONFIRM before deleting |

### RENAMED — same trigger, new condition-ID label (doc Part 5 names)

| Old gate | New signal | Doc section |
|---|---|---|
| G5-ENTRY (flip path) | E1 / E2 / E5 (by scenario+phase, see matrix) | Part 5 Entry |
| G6-ENTRY (sqz_brk path) | E5 | Part 5 Entry |
| G6-LOAD | E4-ARM | Part 5 Entry (arm only) |
| G6-BUY / G6-SELL | ORD:BUY / ORD:SELL (order execution label, carries condition_id) | Part 5 |
| G0b-TOUCH | E3 (boundary fade entry) | Part 5 E3 |
| G0b-M15OPP / G0b-M30OPP / G0b-H4OPP / G0b-SQZLOCK | E3-CHK:n fail reasons (the 6 confinement checks, n=1..6) | Part 5 E3 checks |
| G8-BNDTGT | X1 (target reached) | Part 5 Exit |
| G5-FADE | X2 (QUALIFIED per W1c — container cracking / stall / invalidated) | Part 5 Exit + W1c |
| G6-REV | X2 + immediate new E-eval (reversal = exit then entry, two signals) | Part 5 |
| G0b-PINK | X4-PINK (forced exit invariant) | Part 5 B2/X4 |
| G0e-MAXLOSS | EMERGENCY (invariant) | unconditional |
| G0c-SQZLOCK | ASSERT-B4 (consistency check, not control flow) | Part 5 B4 |

### KEPT AS-IS

| Item | Why |
|---|---|
| [PRED] label + drawing | Part 6 log verification uses it; now also consumed by Layer 3 |
| GATE_CLR_* color scheme | Reuse for new labels (same semantic colors) |

---

## STEP 3 — New Signal Taxonomy (log label grammar)

Every bar where state changes, and every action, emits ONE of:

```
[SC:B2|PH:3A]                          state tag (on change only, not every bar)
[E3:SELL q:72 sz:0.50 chk:6/6]         entry signal with quality, size, checks passed
[E3-CHK:4 FAIL M30opp]                 E3 attempted, check 4 failed (replaces G0b-M30OPP)
[E4-ARM:BUY]                           loading state armed
[ORD:BUY id:E5 lot:0.01 sl:5102.3]     order actually placed
[X1:SELL tgt:H1up hit:5231.4]          target exit
[X2:SELL reason:container-crack]       qualified fade exit (reason mandatory:
                                        container-crack | stall3 | invalidated)
[X4-PINK]                              forced flat — M15+M30 both SQZ
[VETO-AT-TARGET dir:BUY loc:+2]        entry veto fired (W1 addendum)
[EMERGENCY loss:-51.2]                 unconditional loss exit
[ASSERT-B1] [ASSERT-B2] [ASSERT-B3] [ASSERT-B4]
                                        consistency failures: decision table tried
                                        an entry in a state that forbids it.
                                        Log + suppress the order + count it.
[PRED ...]                             unchanged format from TofyTrade4
```

Rules:
- X2 without a reason string is a compile-discipline violation — the reason
  parameter is non-optional in the function signature.
- ASSERT-* in a replay run = test failure. The benchmark requires zero.

---

## STEP 4 — Firing Matrix: which conditions are ARMED per scenario × phase

This is the core deliverable. Implement as a single static table
(scenario, phase) → {armed entries, armed exits, size ceiling} consulted by
DecideAction. Anything not armed cannot fire — no veto needed.

### Always armed, every state (the 3 invariants, evaluated in this order):
```
1. EMERGENCY          (MAX_FLOATING_LOSS_USD)
2. X4-PINK            (M15+M30 both BBW 400-499)
3. VETO-AT-TARGET     (screens any entry the matrix produces)
```

### Matrix

| Scenario | Phase(s) | Armed entries | Armed exits | Size ceiling | Notes (doc cite) |
|---|---|---|---|---|---|
| A1 | PH_1 | E1 | X2 primary, X1(D1 band) | 1.00 | Part 5 Tier 1 |
| A2 | PH_1 | E2 | X2, X1(H4 band) | 0.75 | Part 5 Tier 1 |
| A3 | PH_1 | none (HOLD) | none (ride noise SQZ) | hold | Part 5 A3 |
| B1 | PH_2 | E3 both dir, E1 re-entry | X1(M30 band) primary, X2 qualified | 0.75 | Part 5 Tier 2 + V2 |
| B2 | PH_2/3A | E3 both dir | X1(H1 band) primary, X2 qualified | 0.50 | Part 5 + V2/V3 |
| B3 | PH_3A | E3 both dir | X1(H4 band) primary, X2 qualified | 0.25 | Part 5 + V1 (B3 gate off) |
| B1-B3 | PH_3B_INTO | E3 trend-side at ceiling/floor; counter-side 0.25 | X1 (dropping targets) | 0.50 | §13 Phase 3b |
| B* | PH_3B_OUT | E3 recovery-side | X1 = D1 boundary HARD | 0.50 | §13 3b-OUT |
| E1 | PH_3A/4 | none (WAIT) | existing rides: X1, X2 qualified | — | M30 SQZ ≠ exit |
| E2 | PH_4 | none | X4 forced | 0 | ASSERT-B2 backs it |
| E3(load) | PH_4→5 | E4-ARM → E5 on M15 confirm | — | 0.50 | Part 5 E3 loading |
| E4 | PH_4 | none (WAIT) | — | 0 | ASSERT-B4 backs it |
| G1 | PH_5 | E5 (with-D1 break) | X1, X2 | 0.75 | Part 4 Rule 4 |
| G2 | PH_5 | E5 (counter-D1) | X1, X2, tight stop | 0.25 | counter-trend sizing |
| G3 | PH_5 fail | none — exit any position | X2 immediate | 0 | false breakout |
| G4 | PH_6 | E3 at H4 bounds, both dir | X1 opposite H4 bound ONLY — never hold through | 0.25 | §13 Phase 6 |
| D1s | PH_5 | E4-ARM | — | — | arm only |
| D2s | PH_5 | E5 | X1(H4 band), X2 qualified | 0.75 | |
| D3s | PH_1 | add-on if conf≥90 | X1(D1 band), X2 | 1.00 | → A |
| F1 | PH_5 | none (WAIT — conf floor) | — | 0 | LTF only |
| F2 | PH_5 | E5 | X1(H4 band) | 0.75 | |
| F3 | PH_5→1 | E6 | X1(D1 band), X2 | 1.00 | → A |
| C1 | PH_5 | E5 | X1(H4 band new dir), tight | 0.25 | until H4 confirms |
| C2 | PH_5→1 | E6 | X1(D1 band new dir), X2 | 1.00 | → new A |
| C3 | any | E5 | X1(H4 band), tight | 0.50 | W1/D1 still opposing |

Final size for any entry = MathMin(matrix ceiling, confidence size, §12d decoder size)  // EDIT V5

### Assertions (logged, order suppressed, never control flow beyond suppression):
```
ASSERT-B1: matrix produced E1/E5 while M15 mid>=3        (flip entries need a flip — unreachable if Layer 1 correct)
ASSERT-B2: matrix produced any entry while pink           (E2 row is empty — unreachable)
ASSERT-B3: entry against H4 committed fly outside V1 exemptions
ASSERT-B4: entry while cas_sqzCount>=3 outside E3(load)
```

---

## STEP 5 — Document Update (backtest_chart_analysis.md Gate Decoder)

Locate the "Gate Decoder — EA Implementation Reference" section at the end of
Part 5. Read it, then REPLACE its mapping table with the STEP 2 disposition
tables above (Deleted / Renamed / Kept), prefaced by:

```
As of TofyTrade5 (v31), gates no longer exist as control flow. This decoder
maps legacy TofyTrade4 gate names (still present in pre-v31 logs) to the
v31 signal taxonomy, for cross-version log verification.
```

Also update Part 6 Step 7d grep commands: add the new labels
(E3, X1, X2, X4-PINK, VETO-AT-TARGET, EMERGENCY, ASSERT-, ORD:) alongside the
legacy ones (keep legacy greps — old logs remain greppable).

Commit: "Gate system rewrite: disposition table, signal taxonomy, scenario×phase firing matrix; Gate Decoder updated for v31"

---

## STEP 6 — Verification

1. Inventory completeness: grep output from STEP 1 vs disposition table —
   zero unlisted labels (G1-FAIL/G1-OK purpose confirmed and reported)
2. Replay the March window with the matrix implementation:
   - march2026_benchmark items 1-5 all PASS
   - zero ASSERT-* lines in the replay log
   - every X2 line carries a reason string
   - the 03.17-03.19 run shows X1 or trailing-stop exit, no X2:stall before
     3 bars, and NO label resembling the old G0 all-mid exit
3. RC regression suite (scaffold Phase 5) re-run: report N/M covered —
   each covered incident must now log either a state with no armed entry,
   a failed E3-CHK, confidence size 0, or VETO-AT-TARGET — never a bespoke gate
4. Doc check: Gate Decoder section contains the three disposition tables and
   the v31 preface; Step 7d has both legacy and v31 grep lines
