# CLAUDE.md — BB MTF Strategy Repository

## Source of Truth Hierarchy
- `references/backtest_chart_analysis.md` = PRIMARY reference for scenario/rule MEANINGS and the model. Always consult first for "what does X mean."
- The CODE (`scripts/TofyTrade5.mqh` and `scripts/replay_harness.py`) = FINAL AUTHORITY on what's implemented. Doc and code disagree → code wins, doc is stale (e.g. Scenario C/H had old gate names / unimplemented logic).
- `references/fixtures/validation_status.md` = what's VALIDATED vs hypothesis. A documented rule is not necessarily validated.
- `references/ARCHITECTURE.md` = system DESIGN (how layers connect). Don't confuse with the rules doc.
- `AGENTS.md` = repository-wide dev guidance (build/validation commands, coding style, commit conventions) and the FINAL AUTHORITY for the sideway-ladder/state-machine subsystem: `scripts/TofySidewayLadder.mqh`, its rectangle rules, sideway state machine, and trade rules. That subsystem is the actively developed track (commits through 2026-08-30); consult AGENTS.md first for anything touching `SL_*` settings, `Trade_Strategy` in that file, or `SL_ExitMode`.

## Architecture
- Scenario track (dormant since 2026-06-24, see Current Status below): 3 layers — L1 IdentifyScenario (VALIDATED/built) → L2 PredictNext (Phase 3, not built) → L3 DecideAction (Phase 4, not built).
- Sideway-ladder track (active): a ladder of per-timeframe evidence gates (M15→M30→H1→H4) feeds a sideway state machine (`sl_sw_state` in `TofySidewayLadder.mqh`) that drives `Trade_Strategy` when `SL_ExitMode == 5`. See AGENTS.md for the rectangle rules, state-machine transitions, and trade rules.

## Sideway State Machine — Current Design

Per M15 bar, `TofySidewayLadder.mqh`'s `SL_Update` picks one of two branches via `ladder_branch = (dmt2 == dmt3 && dmt2 < 3)` (M30 and H1 diffMid_Trend agree and are both flying), each driving `sl_sw_state` (0/1/2) — the value `SL_ExitMode == 5` reads as `sw = (sl_sw_state >= 1)`.

**Ladder branch** — `dmt2 == dmt3 && dmt2 < 3` (M30 && H1 fly):
- L1 entry: `L1(SWD) || L1(MW)` (early detect) → once L1 sideway is active, continue only on `L1S || L1C || L1D || L1M` → fill the L1 rectangle.
- L2 promotion: if `prev == L1 sideway` and `L2M || L2S || L2C || L2D` → L2 sideway, fill the L2 rectangle.
- Breakout: if (`prev` was L1 or L2 sideway) and `raw30` → unfill L1 and L2 rectangles, close the run.
- Latch: if `prev == L2 sideway` → extend the L2 rectangle.

**Non-ladder branch** — `!(dmt2 == dmt3 && dmt2 < 3)`:
- Gate: `(L2M||L2S||L2C||L2D) && (L3M||L3S||L3C||L3D)` must hold before L1 can start.
- L1 entry: same `L1(SWD) || L1(MW)` trigger, once the gate holds → fill the L1 rectangle.
- L2 promotion: if `prev == L1 sideway` and `(L2M||L2S||L2C||L2D) && (L3M||L3S||L3C||L3D)` → L2 sideway, fill the L2 rectangle.
- Breakout / latch: same rules as the ladder branch.

**Trade rules** (only when no breakout is active), from `dmt0`: buy on `dmt0 == 1 || dmt0 == 5`, sell on `dmt0 == 2 || dmt0 == 4`, exit all on `dmt0 == 3`. (Also in AGENTS.md "Trade Rules" — kept here too since this is the section actively being debugged.)

Maps to code at `SL_Update`'s state-machine block (~`TofySidewayLadder.mqh:1713` onward): `SL_SwL1EntryA="SWD"`, `SL_SwL1EntryB="MW"`, `SL_SwL1Cont="SCDM"`, `SL_SwL2Any="MSCD"`, `SL_SwL3Any="MSCD"`, `SL_SwPairLo=2` (dmt2), `SL_SwPairHi=3` (dmt3), `SL_SwPairMax=3.0`.

⚠ **Code-vs-design gap to verify** (candidate lead for the STATE-only over-firing in Current Blocker below): in code, `gate = ladder_branch ? true : (l2_ok && l3_ok)` is evaluated ONLY to permit L1 **starting** (`sl_sw_state==0 && gate && l1_entry`). The L2 **promotion** step (`sw_state_before==1 && l2_ok`) re-checks only `l2_ok` on the current bar — `l3_ok` is NOT re-checked at promotion time in either branch, even though the design above (and AGENTS.md's existing "Sideway State Machine" section) states L2 promotion outside the ladder branch needs both the M30 AND H1 tag sets. If L3's evidence drops after L1 starts but before L2 promotes, code still promotes to L2 where the design says it shouldn't — check this against the STATE-only bars found in `references/Backtest_data/V38.19/20260830.log` before assuming the gate logic itself needs retuning.

## Recurring Lessons
- **STORE-vs-RECOMPUTE**: MQL5 stores values on structs; Python recomputes. NOT auto-equivalent — verify bar-for-bar. (Hit on prev_h1_sqz, b1_block/b2_pink, veto_priceloc.)
- **VALIDATED ≠ committed**. V-reversal = HYPOTHESIS (0 OOS episodes); flag OOS-UNVALIDATED in code/doc/chart. Don't tune rules to fit test data.
- **GATES**: GATE 2 = port faithfulness (100% expected). GATE 3 = prediction hit-rate (NOT 100% — forecasting; report real accuracy, don't tune). GATE 4 = firing benchmark.

## Current Blocker

- **Active (sideway-ladder track) — THE task right now:** `SL_ExitMode == 5` (`sw = (sl_sw_state >= 1)` at `TofySidewayLadder.mqh:2068`) must match the VIRTUAL USER hand-labelled sideway signal bar-for-bar (27 ranges, 858/1830 Feb bars = 46.9%, the tradeable ceiling — gross +415.36 M15 / +1353.85 M5). Measured from `references/Backtest_data/V38.19/20260830.log` (the latest run — see "Reading the MT5 log" below): the state machine currently flags 1229/1830 bars = 67.2% in 55 ranges (USER: 858 bars, 27 ranges), 61.2% precision / 87.6% recall — 477 STATE-only bars (over-firing) vs. 106 USER-only bars (under-firing). Recall is close; precision is the gap. STATE-only bars cluster in long non-sideway stretches (e.g. `2026.02.02 10:00`–`13:00`, 12 consecutive bars, no USER range within 2h) — check `dmt1/dmt2/dmt3` there; that run is a trending period the ladder branch (`dmt2==dmt3 && dmt2<3`) or the L2/L3 gate is wrongly treating as sideway. **Next:** walk `[LADDER]` (`sw:`, `gate:`, `l2ok:`, `l3ok:`, `lbr:`, `why:`) against `[SWCMP]`/`[VIRTUAL]` (USER block) bar-by-bar over the STATE-only stretches first — find which gate/entry rule is failing to reject them — before touching trade rules. See AGENTS.md "Primary Validation Goal" for the general method and `references/SIDEWAY_LABELS_CEILING_FEB.md` for the reference timeline.

  **Reading the MT5 log:** these `.log` files under `references/Backtest_data/` are UTF-16 (MetaTester's native encoding) — `grep`/`Read` render them as garbled space-separated characters. In PowerShell: `Get-Content -Encoding Unicode <path> | Where-Object { $_ -match '\[LADDER\]' }` (or `[SWCMP]`/`[VIRTUAL]`). One `[LADDER]`, one `[SWCMP]`, and (if `SL_DrawVirtual` is on) one `[VIRTUAL]` line print per M15 bar, in that order, so the Nth line of each tag is the same bar — join by index, not by the log's own timestamp column (that's the M5 tick time the print happened on, not the M15 bar time; use `[SWCMP]`'s `bar:[...]` field for the true M15 bar time). `[SWCMP]`'s `user:[...]`/`ladder:[...]` fields are each only printed when the *other* source is sideway — don't rely on them for a full-coverage comparison; recompute USER sideway directly from `SL_LabelStart`/`SL_LabelEnd` instead.
- **Dormant (scenario track, since 2026-06-24):** s_prevH1Sqz timing bug fixed in repo (TofyTrade5.mqh v31.06 — capture-prior-then-update; was current-vs-prior collapse making Decision 6 recovery dead). Still **OPEN** if this track is picked back up: confirm whether the EA (local TofyIncludeSimple/Tofu_EA_Simple) `#includes` TofyTrade5.mqh (fix flows through) or has its own copy of IdentifyScenario (fix must be applied to EA separately — user-side, Claude Code does not touch EA source). diffBBW history (repo correct, EA diverged) suggests own-copy. See validation_status.md for the Bug 3 record.


### Rules Claude Code must follow for this file

1. NEVER remove existing flowcharts, trade action blocks,
   checklists, or image embed lines
2. NEVER invent BBW_stage, diffMid_Trend, or BBUpDn_state
   values — read them from image filenames and existing
   text analysis only. Use [TO BE FILLED] if uncertain.
3. BBW_stage valid values: 511 512 521 522 513 523 400-499
4. diffMid_Trend valid values: 1 2 3 4 5 only
5. BBUpDn_state valid values: 0 1 2 only
6. Touch Type valid values: Type 1 Type 2 Type 3 only
7. Insert at ### heading level — never promote to ## or #
8. Every Step 7 flowchart must use mermaid syntax
9. After every str_replace confirm the new line count
10. Process one scenario at a time — do not batch all scenarios
    in one tool call
