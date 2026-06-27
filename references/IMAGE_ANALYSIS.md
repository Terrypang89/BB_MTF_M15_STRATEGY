# Image Analysis Blocks

Companion to `backtest_chart_analysis.md` — Part 3 image-analysis blocks have been separated from the scenario definitions into this document. The scenario definitions (Cascade Position, Sub-Scenarios, Sub-State Flowchart, Identification Flowchart, Trade action) remain in `backtest_chart_analysis.md`.

Each block contains an event-driven state table derived from the backtest log (`references/Backtest_data/V31.04/20260620_clean.log`). States are `[TO BE FILLED]` where the log has no data for that TF at the given time.

---

## HTF / MTF Two-Axis Reading — DESIGN REFERENCE

> **STATUS: DESIGN — UNBUILT, UNVALIDATED.** This is a proposed framework for
> reading each chart into two state axes (HTF + MTF). It is NOT implemented in
> identify_scenario and NOT validated against backtest data. It is a reference
> for the manual image analysis below, not a code spec. Depends on the EA
> baseline (V31.06) blocker before any of it can be built. Rows marked below are
> inferred — verify against backtest_chart_analysis.md before relying on them.

**The two axes:**
- **HTF-state** (H4/D1/W1): slow macro context (changes over days).
- **MTF-state** (M15/M30/H1): fast cascade (changes bar-to-bar).
- A scenario = (HTF-state × MTF-state). Existing labels are shorthand for
  combinations.
- **KEY: the MTF-state's most important attribute is DIRECTION-vs-H4.** "MTF
  flying SAME as H4" = continuation (F); "MTF flying/reversed OPPOSITE to H4"
  = reversal beginning (R1). Both look like "MTF active" — only direction-vs-H4
  separates them. (This is the discriminator current code is blind to.)

**Scenario → axis classification** (defs from backtest_chart_analysis.md):

| Scenario | Sub-state meaning | MTF/HTF driven | Why |
|----------|-------------------|----------------|-----|
| F1/F2/F3 | D1/W1 alignment levels (macro/partial/weak) | HTF | sub-split is D1/W1 |
| S1/S2/S3 | shrink @ M15 / M30 / H1 | MTF | which TF shrinks |
| R1 | M30 reversed, H4 still flying (pre-pivot) | Both | genuinely 2-axis |
| R2 | H4 flipped + D1 reversed (full) | HTF | D1 fork |
| R3 | H4 flipped, D1 original (counter-trend) | HTF | D1 fork |
| C1 | LTF partial SQZ (M15 peak, M30 noise) | MTF | SQZ progression |
| C2 | LTF full SQZ (all LTF, G0b-PINK) | MTF | SQZ progression |
| C3 | M5 loading (breaking SQZ, G6-LOAD) | MTF | SQZ progression |
| C4 | H4 also compressing ( V) | HTF | H4 state change |
| B1 | release, LTF only (unconfirmed) | MTF | MTF leads |
| B2 | release, MTF confirmed | Both | propagation |
| B3 | release, HTF confirmed ( F) | HTF | H4 confirms |
| V1 | H4 breaks same as D1 (continuation  B) | HTF | H4 SQZ resolution |
| V2 | H4 breaks opposite D1 (reversal  R2/R3) | HTF | H4 SQZ resolution |
| V3 | false breakout (reverts 3 bars  C/V) | HTF | H4 SQZ resolution |
| V4 | whipsaw (alternating, no resolution) | HTF | H4 SQZ resolution |
| P1 | M5 break (G6-LOAD, arm) | MTF | re-expansion |
| P2 | M15 confirm (entry trigger, 0.75) | MTF | re-expansion |
| P3 | MTF re-align ( F, 1.0) | MTF | re-expansion |

**Pattern:** HTF-driven = F, R2/R3, C4, V (all), B3 (D1/W1/H4-state is the
discriminator). MTF-driven = S, C1-C3, P, B1 (which-TF/depth/stage). Genuinely
2-axis = R1, B2.

**Sideways cascade:** "sideways" (diffMid=3) propagates up the TFs —
LTF-sideways (M5/M15 flat, earliest/ambiguous)  MTF-sideways (M30/H1 flat,
committed)  HTF-sideways (H4 flat = pivot/V). Propagating states (shrink,
sideways, breakout) are TF-indexable; simultaneous states (fly) are not.

**Split recommendation (when built):** expose HTF-state + MTF-state as two
fields (additive), KEEP existing labels, share HTF-state with Part 4. Do NOT
do a uniform 2-digit rename — most scenarios are single-axis (one field empty);
only R1/B2 are genuinely 2-axis.

---

## Scenario F (Full Fly)

#### Image 1 Analysis — backtested_EA_fly_scenario.jpg
![backtested_EA_fly_scenario](./Backtest_data/extras/backtested_EA_fly_scenario.jpg)

**Period:** 2026.01.02 01:00 → 2026.01.03 04:00 (log-ground-truth: Jan 2-3 log shows M30=511 FLY matching chart; Feb 1-3 log shows M30=522 FLY DN — opposite state. Chart x-axis too small to read definitively; log is unambiguous.)

> **Cell = BBW_stage-diffMid-BBUpDn** (e.g. 511-1-1). BBW: 511/512=up-fly,
> 521/522=down-fly, 513/523=shrink, 4xx=SQZ. diffMid: 1=up, 2=down,
> 3=sideways, 5=deep-sideways. BBUpDn: 0=between, 1=upper, 2=lower,
> 3=sideways. A new row is added only when M15 BBW_stage or diffMid changes.
> All rows fall within the user-defined period.

| datetime | M15 | M30 | H1 | H4 | D1 | W1 | Scenario (HTF-MTF) | Trend / Tier |
|----------|-----|-----|----|----|----|----|--------------------|------------|
| 2026.01.02 01:45 | 511-1-1 | [TO BE FILLED] | [TO BE FILLED] | [TO BE FILLED] | [TO BE FILLED] | [TO BE FILLED] | F-F | Sideways / Tier 3 |
| 2026.01.02 03:30 | 512-1-3 | 511-5-1 | 424-4-0 | [TO BE FILLED] | [TO BE FILLED] | [TO BE FILLED] | F-F | Sideways / Tier 3 |
| 2026.01.02 09:00 | 513-1-2 | 512-1-3 | 511-1-0 | [TO BE FILLED] | [TO BE FILLED] | [TO BE FILLED] | F-S1 | Sideways / Tier 3 |
| 2026.01.02 10:15 | 421-1-3 | 512-1-0 | 512-1-3 | [TO BE FILLED] | [TO BE FILLED] | [TO BE FILLED] | F-C1 | Sideways / Tier 3 |
| 2026.01.02 10:30 | 511-1-3 | 513-1-2 | 512-1-3 | [TO BE FILLED] | [TO BE FILLED] | [TO BE FILLED] | F-F | Sideways / Tier 3 |
| 2026.01.02 11:30 | 512-1-3 | 512-1-3 | 512-1-3 | [TO BE FILLED] | [TO BE FILLED] | [TO BE FILLED] | F-F | Sideways / Tier 3 |
| 2026.01.02 12:00 | 512-5-3 | 512-1-3 | 512-1-3 | [TO BE FILLED] | [TO BE FILLED] | [TO BE FILLED] | F-F | Sideways / Tier 3 |
| 2026.01.02 12:15 | 512-1-3 | 512-1-3 | 512-1-3 | [TO BE FILLED] | [TO BE FILLED] | [TO BE FILLED] | F-F | Sideways / Tier 3 |
| 2026.01.02 12:30 | 512-5-3 | 512-1-3 | 512-1-3 | [TO BE FILLED] | [TO BE FILLED] | [TO BE FILLED] | F-F | Sideways / Tier 3 |
| 2026.01.02 12:45 | 512-1-0 | 512-1-3 | 512-1-3 | [TO BE FILLED] | [TO BE FILLED] | [TO BE FILLED] | F-F | Sideways / Tier 3 |
| 2026.01.02 14:30 | 513-1-2 | 513-1-2 | 512-1-0 | [TO BE FILLED] | [TO BE FILLED] | [TO BE FILLED] | F-S2 | Sideways / Tier 3 |
| 2026.01.02 14:45 | 513-5-2 | 513-1-2 | 512-1-0 | [TO BE FILLED] | [TO BE FILLED] | [TO BE FILLED] | F-S2 | Sideways / Tier 3 |
| 2026.01.02 15:00 | 513-1-0 | 513-1-0 | 512-1-3 | [TO BE FILLED] | [TO BE FILLED] | [TO BE FILLED] | F-S2 | Sideways / Tier 3 |
| 2026.01.02 15:15 | 421-1-3 | 513-1-0 | 512-1-3 | [TO BE FILLED] | [TO BE FILLED] | [TO BE FILLED] | F-C1 | Sideways / Tier 3 |
| 2026.01.02 15:30 | 421-3-0 | 513-3-2 | 512-1-3 | [TO BE FILLED] | [TO BE FILLED] | [TO BE FILLED] | F-C1 | Sideways / Tier 3 |
| 2026.01.02 15:45 | 521-2-1 | 513-3-2 | 512-1-3 | [TO BE FILLED] | [TO BE FILLED] | [TO BE FILLED] | F-F | Sideways / Tier 3 |
| 2026.01.02 18:00 | 522-2-4 | 521-2-1 | 513-1-2 | [TO BE FILLED] | [TO BE FILLED] | [TO BE FILLED] | F-F | Sideways / Tier 3 |
| 2026.01.02 21:15 | 523-2-2 | 522-2-4 | 412-2-0 | [TO BE FILLED] | [TO BE FILLED] | [TO BE FILLED] | F-F | Sideways / Tier 3 |
| 2026.01.02 23:00 | 423-3-0 | 522-2-0 | 521-2-1 | [TO BE FILLED] | [TO BE FILLED] | [TO BE FILLED] | F-C1 | Sideways / Tier 3 |
| 2026.01.02 23:15 | 511-5-0 | 522-2-0 | 521-2-1 | [TO BE FILLED] | [TO BE FILLED] | [TO BE FILLED] | F-F | Sideways / Tier 3 |
| 2026.01.02 23:30 | 512-5-3 | 523-2-2 | 521-2-1 | [TO BE FILLED] | [TO BE FILLED] | [TO BE FILLED] | F-F | Sideways / Tier 3 |

**Coverage:** 2026.01.02 01:45 → 2026.01.02 23:30 | Period: 2026.01.02 01:00 → 2026.01.03 04:00 | **INCOMPLETE — period ends on non-trading day (2026.01.03)**

#### Image 2 Analysis — backtested_EA_predict_trend_1.jpg
![backtested_EA_predict_trend_1](./Backtest_data/extras/backtested_EA_predict_trend_1.jpg)

**Period:** 2026.04.01 13:00 → 2026.04.01 17:00 (chart x-axis: "01.04.2026" labels, DD.MM.YYYY = Apr 1)

> **Cell = BBW_stage-diffMid-BBUpDn** (e.g. 511-1-1). BBW: 511/512=up-fly,
> 521/522=down-fly, 513/523=shrink, 4xx=SQZ. diffMid: 1=up, 2=down,
> 3=sideways, 5=deep-sideways. BBUpDn: 0=between, 1=upper, 2=lower,
> 3=sideways. A new row is added only when M15 BBW_stage or diffMid changes.
> All rows fall within the user-defined period.

| datetime | M15 | M30 | H1 | H4 | D1 | W1 | Scenario (HTF-MTF) | Trend / Tier |
|----------|-----|-----|----|----|----|----|--------------------|------------|
| 2026.04.01 13:00 | 513-1-2 | 512-1-0 | 512-1-0 | 512-1-3 | 522-2-4 | 513-1-2 | F2-S1 | Up (div) / Tier 1 |
| 2026.04.01 14:30 | 512-1-3 | 511-1-1 | 512-1-0 | 512-1-3 | 522-2-4 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.04.01 14:45 | 511-1-1 | 511-1-1 | 512-1-0 | 512-1-3 | 522-2-4 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.04.01 15:15 | 512-1-3 | 511-1-0 | 512-1-3 | 512-1-3 | 522-2-4 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.04.01 15:30 | 512-3-3 | 512-1-3 | 512-1-3 | 512-1-3 | 522-2-4 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.04.01 16:15 | 512-5-0 | 512-1-3 | 513-1-2 | 512-1-3 | 522-2-4 | 513-1-2 | F2-F | Up (div) / Tier 1 |

**Coverage:** 2026.04.01 13:00 → 2026.04.01 16:15 | Period: 2026.04.01 13:00 → 2026.04.01 17:00 | **COMPLETE**

#### Image 3 Analysis — LTH_drive_fly.jpg
![LTH_drive_fly](./Backtest_data/extras/LTH_drive_fly.jpg)

**Period:** 2026.01.02 01:00 → 2026.01.03 04:00 (chart x-axis: "02.01.2026" / "03.01.2026", DD.MM.YYYY = Jan 2-3)

> **Cell = BBW_stage-diffMid-BBUpDn** (e.g. 511-1-1). BBW: 511/512=up-fly,
> 521/522=down-fly, 513/523=shrink, 4xx=SQZ. diffMid: 1=up, 2=down,
> 3=sideways, 5=deep-sideways. BBUpDn: 0=between, 1=upper, 2=lower,
> 3=sideways. A new row is added only when M15 BBW_stage or diffMid changes.
> All rows fall within the user-defined period.

| datetime | M15 | M30 | H1 | H4 | D1 | W1 | Scenario (HTF-MTF) | Trend / Tier |
|----------|-----|-----|----|----|----|----|--------------------|------------|
| 2026.01.02 01:45 | 511-1-1 | [TO BE FILLED] | [TO BE FILLED] | [TO BE FILLED] | [TO BE FILLED] | [TO BE FILLED] | F-F | Sideways / Tier 3 |
| 2026.01.02 03:30 | 512-1-3 | 511-5-1 | 424-4-0 | [TO BE FILLED] | [TO BE FILLED] | [TO BE FILLED] | F-F | Sideways / Tier 3 |
| 2026.01.02 09:00 | 513-1-2 | 512-1-3 | 511-1-0 | [TO BE FILLED] | [TO BE FILLED] | [TO BE FILLED] | F-S1 | Sideways / Tier 3 |
| 2026.01.02 10:15 | 421-1-3 | 512-1-0 | 512-1-3 | [TO BE FILLED] | [TO BE FILLED] | [TO BE FILLED] | F-C1 | Sideways / Tier 3 |
| 2026.01.02 10:30 | 511-1-3 | 513-1-2 | 512-1-3 | [TO BE FILLED] | [TO BE FILLED] | [TO BE FILLED] | F-F | Sideways / Tier 3 |
| 2026.01.02 11:30 | 512-1-3 | 512-1-3 | 512-1-3 | [TO BE FILLED] | [TO BE FILLED] | [TO BE FILLED] | F-F | Sideways / Tier 3 |
| 2026.01.02 12:00 | 512-5-3 | 512-1-3 | 512-1-3 | [TO BE FILLED] | [TO BE FILLED] | [TO BE FILLED] | F-F | Sideways / Tier 3 |
| 2026.01.02 12:15 | 512-1-3 | 512-1-3 | 512-1-3 | [TO BE FILLED] | [TO BE FILLED] | [TO BE FILLED] | F-F | Sideways / Tier 3 |
| 2026.01.02 12:30 | 512-5-3 | 512-1-3 | 512-1-3 | [TO BE FILLED] | [TO BE FILLED] | [TO BE FILLED] | F-F | Sideways / Tier 3 |
| 2026.01.02 12:45 | 512-1-0 | 512-1-3 | 512-1-3 | [TO BE FILLED] | [TO BE FILLED] | [TO BE FILLED] | F-F | Sideways / Tier 3 |
| 2026.01.02 14:30 | 513-1-2 | 513-1-2 | 512-1-0 | [TO BE FILLED] | [TO BE FILLED] | [TO BE FILLED] | F-S2 | Sideways / Tier 3 |
| 2026.01.02 14:45 | 513-5-2 | 513-1-2 | 512-1-0 | [TO BE FILLED] | [TO BE FILLED] | [TO BE FILLED] | F-S2 | Sideways / Tier 3 |
| 2026.01.02 15:00 | 513-1-0 | 513-1-0 | 512-1-3 | [TO BE FILLED] | [TO BE FILLED] | [TO BE FILLED] | F-S2 | Sideways / Tier 3 |
| 2026.01.02 15:15 | 421-1-3 | 513-1-0 | 512-1-3 | [TO BE FILLED] | [TO BE FILLED] | [TO BE FILLED] | F-C1 | Sideways / Tier 3 |
| 2026.01.02 15:30 | 421-3-0 | 513-3-2 | 512-1-3 | [TO BE FILLED] | [TO BE FILLED] | [TO BE FILLED] | F-C1 | Sideways / Tier 3 |
| 2026.01.02 15:45 | 521-2-1 | 513-3-2 | 512-1-3 | [TO BE FILLED] | [TO BE FILLED] | [TO BE FILLED] | F-F | Sideways / Tier 3 |
| 2026.01.02 18:00 | 522-2-4 | 521-2-1 | 513-1-2 | [TO BE FILLED] | [TO BE FILLED] | [TO BE FILLED] | F-F | Sideways / Tier 3 |
| 2026.01.02 21:15 | 523-2-2 | 522-2-4 | 412-2-0 | [TO BE FILLED] | [TO BE FILLED] | [TO BE FILLED] | F-F | Sideways / Tier 3 |
| 2026.01.02 23:00 | 423-3-0 | 522-2-0 | 521-2-1 | [TO BE FILLED] | [TO BE FILLED] | [TO BE FILLED] | F-C1 | Sideways / Tier 3 |
| 2026.01.02 23:15 | 511-5-0 | 522-2-0 | 521-2-1 | [TO BE FILLED] | [TO BE FILLED] | [TO BE FILLED] | F-F | Sideways / Tier 3 |
| 2026.01.02 23:30 | 512-5-3 | 523-2-2 | 521-2-1 | [TO BE FILLED] | [TO BE FILLED] | [TO BE FILLED] | F-F | Sideways / Tier 3 |

**Coverage:** 2026.01.02 01:45 → 2026.01.02 23:30 | Period: 2026.01.02 01:00 → 2026.01.03 04:00 | **INCOMPLETE — period ends on non-trading day (2026.01.03)**

---

## Scenario S (Shrink)

#### Image 1 Analysis — backtested_EA_fly_2_fly_shrink.jpg
![backtested_EA_fly_2_fly_shrink](./Backtest_data/extras/backtested_EA_fly_2_fly_shrink.jpg)

**Period:** 2026.03.30 13:00 → 2026.04.01 13:00 (chart x-axis: "30.03.2026" / "01.04.2026", log-confirmed)

> **Cell = BBW_stage-diffMid-BBUpDn** (e.g. 511-1-1). BBW: 511/512=up-fly,
> 521/522=down-fly, 513/523=shrink, 4xx=SQZ. diffMid: 1=up, 2=down,
> 3=sideways, 5=deep-sideways. BBUpDn: 0=between, 1=upper, 2=lower,
> 3=sideways. A new row is added only when M15 BBW_stage or diffMid changes.
> All rows fall within the user-defined period.

| datetime | M15 | M30 | H1 | H4 | D1 | W1 | Scenario (HTF-MTF) | Trend / Tier |
|----------|-----|-----|----|----|----|----|--------------------|------------|
| 2026.03.30 13:00 | 513-1-2 | 512-1-3 | 512-1-0 | 513-4-0 | 522-2-4 | 513-1-2 | C4-S1 | Sideways / Tier 2 |
| 2026.03.30 14:00 | 513-5-2 | 513-1-2 | 512-1-0 | 513-4-0 | 522-2-4 | 513-1-2 | C4-S2 | Sideways / Tier 2 |
| 2026.03.30 14:15 | 425-5-0 | 513-1-2 | 512-1-0 | 513-4-0 | 522-2-4 | 513-1-2 | C4-C1 | Sideways / Tier 2 |
| 2026.03.30 14:30 | 511-5-1 | 513-1-2 | 512-1-0 | 513-4-0 | 522-2-4 | 513-1-2 | C4-B1 | Sideways / Tier 2 |
| 2026.03.30 14:45 | 511-1-1 | 513-1-2 | 512-1-0 | 513-4-0 | 522-2-4 | 513-1-2 | C4-B1 | Sideways / Tier 2 |
| 2026.03.30 16:00 | 512-1-3 | 512-1-3 | 511-1-1 | 513-3-0 | 522-2-4 | 513-1-2 | C4-F | Sideways / Tier 2 |
| 2026.03.30 16:45 | 512-5-3 | 512-1-3 | 511-1-1 | 513-3-0 | 522-2-4 | 513-1-2 | C4-F | Sideways / Tier 2 |
| 2026.03.30 17:00 | 511-5-1 | 512-1-0 | 511-1-0 | 513-3-0 | 522-2-4 | 513-1-2 | C4-F | Sideways / Tier 2 |
| 2026.03.30 17:30 | 521-2-1 | 513-1-2 | 511-1-0 | 513-3-0 | 522-2-4 | 513-1-2 | C4-B1 | Sideways / Tier 2 |
| 2026.03.30 18:00 | 521-3-0 | 513-1-2 | 512-1-3 | 513-3-0 | 522-2-4 | 513-1-2 | C4-B1 | Sideways / Tier 2 |
| 2026.03.30 19:00 | 512-1-3 | 513-1-0 | 512-1-0 | 513-3-0 | 522-2-4 | 513-1-2 | C4-B1 | Sideways / Tier 2 |
| 2026.03.30 19:15 | 512-5-0 | 513-1-0 | 512-1-0 | 513-3-0 | 522-2-4 | 513-1-2 | C4-B1 | Sideways / Tier 2 |
| 2026.03.30 19:45 | 512-2-0 | 513-3-0 | 512-1-0 | 513-3-0 | 522-2-4 | 513-1-2 | C4-B1 | Sideways / Tier 2 |
| 2026.03.30 20:15 | 522-2-4 | 513-3-3 | 512-1-3 | 513-3-2 | 522-2-4 | 513-1-2 | C4-B1 | Sideways / Tier 2 |
| 2026.03.30 21:15 | 523-2-2 | 521-2-1 | 512-1-3 | 513-3-2 | 522-2-4 | 513-1-2 | C4-S1 | Sideways / Tier 2 |
| 2026.03.30 21:45 | 412-2-0 | 521-2-1 | 512-1-3 | 513-3-2 | 522-2-4 | 513-1-2 | C4-C1 | Sideways / Tier 2 |
| 2026.03.30 22:00 | 521-2-1 | 521-2-1 | 512-1-0 | 513-3-2 | 522-2-4 | 513-1-2 | C4-F | Sideways / Tier 2 |
| 2026.03.30 23:00 | 522-2-4 | 521-2-1 | 513-1-2 | 513-3-2 | 522-2-4 | 513-1-2 | C4-B2 | Sideways / Tier 2 |
| 2026.03.31 01:00 | 523-2-2 | 521-2-0 | 513-1-2 | 513-4-2 | 522-2-4 | 513-1-2 | C4-S1 | Sideways / Tier 2 |
| 2026.03.31 02:45 | 523-3-2 | 522-2-0 | 513-1-2 | 513-4-2 | 522-2-4 | 513-1-2 | C4-S1 | Sideways / Tier 2 |
| 2026.03.31 03:00 | 523-4-2 | 523-2-2 | 513-1-2 | 513-4-2 | 522-2-4 | 513-1-2 | C4-S3 | Sideways / Tier 2 |
| 2026.03.31 03:15 | 423-3-1 | 523-2-2 | 513-1-2 | 513-4-2 | 522-2-4 | 513-1-2 | C4-C1 | Sideways / Tier 2 |
| 2026.03.31 03:30 | 423-4-0 | 523-2-2 | 513-1-2 | 513-4-2 | 522-2-4 | 513-1-2 | C4-C1 | Sideways / Tier 2 |
| 2026.03.31 03:45 | 521-4-1 | 523-2-2 | 513-1-2 | 513-4-2 | 522-2-4 | 513-1-2 | C4-B1 | Sideways / Tier 2 |
| 2026.03.31 04:00 | 511-1-1 | 413-3-0 | 513-1-0 | 513-3-0 | 522-2-4 | 513-1-2 | C4-B1 | Sideways / Tier 2 |
| 2026.03.31 05:30 | 512-1-3 | 511-1-1 | 411-1-0 | 513-3-0 | 522-2-4 | 513-1-2 | C4-B2 | Sideways / Tier 2 |
| 2026.03.31 07:15 | 513-1-2 | 511-1-0 | 511-1-0 | 513-3-0 | 522-2-4 | 513-1-2 | C4-S1 | Sideways / Tier 2 |
| 2026.03.31 09:15 | 513-3-0 | 512-1-3 | 512-1-3 | 511-1-1 | 522-2-4 | 513-1-2 | F2-S1 | Up (div) / Tier 1 |
| 2026.03.31 09:45 | 513-2-2 | 512-1-3 | 512-1-3 | 511-1-1 | 522-2-4 | 513-1-2 | F2-S1 [divergence] | Up (div) / Tier 1 |
| 2026.03.31 11:00 | 513-4-2 | 513-1-2 | 512-5-0 | 511-1-1 | 522-2-4 | 513-1-2 | F2-S2 | Up (div) / Tier 1 |
| 2026.03.31 11:15 | 424-4-0 | 513-1-2 | 512-5-0 | 511-1-1 | 522-2-4 | 513-1-2 | F2-C1 | Up (div) / Tier 1 |
| 2026.03.31 11:30 | 521-4-1 | 512-1-3 | 512-5-0 | 511-1-1 | 522-2-4 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.03.31 11:45 | 521-1-0 | 512-1-3 | 512-5-0 | 511-1-1 | 522-2-4 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.03.31 12:00 | 512-1-3 | 512-1-0 | 512-3-1 | 511-5-1 | 522-2-4 | 513-1-2 | F3-F | Sideways / Tier 1 |
| 2026.03.31 12:15 | 512-5-3 | 512-1-0 | 512-3-1 | 511-5-1 | 522-2-4 | 513-1-2 | F3-F | Sideways / Tier 1 |
| 2026.03.31 12:30 | 512-3-0 | 513-1-2 | 512-3-1 | 511-5-1 | 522-2-4 | 513-1-2 | F3-F | Sideways / Tier 1 |
| 2026.03.31 12:45 | 512-4-0 | 513-1-2 | 512-3-1 | 511-5-1 | 522-2-4 | 513-1-2 | F3-F | Sideways / Tier 1 |
| 2026.03.31 13:15 | 521-4-1 | 513-1-2 | 512-3-0 | 511-5-1 | 522-2-4 | 513-1-2 | F3-F | Sideways / Tier 1 |
| 2026.03.31 13:45 | 521-2-0 | 513-1-2 | 512-3-0 | 511-5-1 | 522-2-4 | 513-1-2 | F3-F | Sideways / Tier 1 |
| 2026.03.31 14:15 | 521-4-0 | 413-3-0 | 512-1-0 | 511-5-1 | 522-2-4 | 513-1-2 | F3-F | Sideways / Tier 1 |
| 2026.03.31 14:45 | 511-1-1 | 413-2-0 | 512-1-0 | 511-5-1 | 522-2-4 | 513-1-2 | F3-F | Sideways / Tier 1 |
| 2026.03.31 15:30 | 512-1-3 | 413-3-0 | 512-1-0 | 511-5-1 | 522-2-4 | 513-1-2 | F3-F | Sideways / Tier 1 |
| 2026.03.31 16:00 | 512-5-3 | 511-5-1 | 512-1-0 | 511-1-1 | 522-2-4 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.03.31 16:15 | 512-1-0 | 511-5-1 | 512-1-0 | 511-1-1 | 522-2-4 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.03.31 16:45 | 511-1-1 | 511-1-0 | 512-1-0 | 511-1-1 | 522-2-4 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.03.31 18:00 | 512-1-3 | 511-1-0 | 511-1-0 | 511-1-1 | 522-2-4 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.03.31 23:45 | 513-1-2 | 512-1-3 | 512-1-3 | 511-1-1 | 522-2-4 | 513-1-2 | F2-S1 | Up (div) / Tier 1 |
| 2026.04.01 02:45 | 512-1-3 | 512-1-3 | 511-1-1 | 511-1-0 | 522-2-4 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.04.01 03:30 | 511-1-1 | 512-1-3 | 511-1-0 | 511-1-0 | 522-2-4 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.04.01 04:00 | 512-1-3 | 512-1-3 | 511-1-0 | 511-1-0 | 522-2-4 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.04.01 05:30 | 512-5-3 | 512-1-0 | 512-1-3 | 511-1-0 | 522-2-4 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.04.01 05:45 | 512-3-0 | 512-1-0 | 512-1-3 | 511-1-0 | 522-2-4 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.04.01 06:00 | 513-5-2 | 513-1-2 | 512-1-3 | 511-1-0 | 522-2-4 | 513-1-2 | F2-S2 | Up (div) / Tier 1 |
| 2026.04.01 06:30 | 513-1-2 | 513-1-2 | 512-1-3 | 511-1-0 | 522-2-4 | 513-1-2 | F2-S2 | Up (div) / Tier 1 |
| 2026.04.01 07:00 | 513-5-2 | 513-1-2 | 512-1-3 | 511-1-0 | 522-2-4 | 513-1-2 | F2-S2 | Up (div) / Tier 1 |
| 2026.04.01 07:15 | 415-5-1 | 513-1-2 | 512-1-3 | 511-1-0 | 522-2-4 | 513-1-2 | F2-C1 | Up (div) / Tier 1 |
| 2026.04.01 07:30 | 422-2-1 | 513-1-2 | 512-1-3 | 511-1-0 | 522-2-4 | 513-1-2 | F2-C1 [divergence] | Up (div) / Tier 1 |
| 2026.04.01 07:45 | 521-2-1 | 513-1-2 | 512-1-3 | 511-1-0 | 522-2-4 | 513-1-2 | F2-F [divergence] | Up (div) / Tier 1 |
| 2026.04.01 08:38 | 523-2-2 | 513-1-0 | 512-1-3 | 512-1-3 | 522-2-4 | 513-1-2 | F2-S2 [divergence] | Up (div) / Tier 1 |
| 2026.04.01 08:45 | 523-4-2 | 513-1-0 | 512-1-3 | 512-1-3 | 522-2-4 | 513-1-2 | F2-S2 | Up (div) / Tier 1 |
| 2026.04.01 09:00 | 523-2-2 | 513-1-2 | 512-1-3 | 512-1-3 | 522-2-4 | 513-1-2 | F2-S2 [divergence] | Up (div) / Tier 1 |
| 2026.04.01 09:30 | 413-3-1 | 411-1-3 | 512-1-3 | 512-1-3 | 522-2-4 | 513-1-2 | F2-C3 | Up (div) / Tier 1 |
| 2026.04.01 09:45 | 421-1-1 | 411-1-3 | 512-1-3 | 512-1-3 | 522-2-4 | 513-1-2 | F2-C3 | Up (div) / Tier 1 |
| 2026.04.01 10:00 | 511-1-1 | 511-1-1 | 512-1-3 | 512-1-3 | 522-2-4 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.04.01 11:00 | 512-1-3 | 511-1-0 | 512-1-0 | 512-1-3 | 522-2-4 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.04.01 12:30 | 513-1-2 | 512-1-3 | 512-1-3 | 512-1-3 | 522-2-4 | 513-1-2 | F2-S1 | Up (div) / Tier 1 |

**Coverage:** 2026.03.30 13:00 → 2026.04.01 12:30 | Period: 2026.03.30 13:00 → 2026.04.01 13:00 | **COMPLETE**

#### Image 2 Analysis — backtested_EA_fly_2_fly_shrink_zoomin.jpg
![backtested_EA_fly_2_fly_shrink_zoomin](./Backtest_data/extras/backtested_EA_fly_2_fly_shrink_zoomin.jpg)

**Period:** 2026.03.30 14:30 → 2026.04.01 09:00 (chart x-axis: "30.03.2026" / "01.04.2026", log-confirmed)

> **Cell = BBW_stage-diffMid-BBUpDn** (e.g. 511-1-1). BBW: 511/512=up-fly,
> 521/522=down-fly, 513/523=shrink, 4xx=SQZ. diffMid: 1=up, 2=down,
> 3=sideways, 5=deep-sideways. BBUpDn: 0=between, 1=upper, 2=lower,
> 3=sideways. A new row is added only when M15 BBW_stage or diffMid changes.
> All rows fall within the user-defined period.

| datetime | M15 | M30 | H1 | H4 | D1 | W1 | Scenario (HTF-MTF) | Trend / Tier |
|----------|-----|-----|----|----|----|----|--------------------|------------|
| 2026.03.30 14:30 | 511-5-1 | 513-1-2 | 512-1-0 | 513-4-0 | 522-2-4 | 513-1-2 | C4-B1 | Sideways / Tier 2 |
| 2026.03.30 14:45 | 511-1-1 | 513-1-2 | 512-1-0 | 513-4-0 | 522-2-4 | 513-1-2 | C4-B1 | Sideways / Tier 2 |
| 2026.03.30 16:00 | 512-1-3 | 512-1-3 | 511-1-1 | 513-3-0 | 522-2-4 | 513-1-2 | C4-F | Sideways / Tier 2 |
| 2026.03.30 16:45 | 512-5-3 | 512-1-3 | 511-1-1 | 513-3-0 | 522-2-4 | 513-1-2 | C4-F | Sideways / Tier 2 |
| 2026.03.30 17:00 | 511-5-1 | 512-1-0 | 511-1-0 | 513-3-0 | 522-2-4 | 513-1-2 | C4-F | Sideways / Tier 2 |
| 2026.03.30 17:30 | 521-2-1 | 513-1-2 | 511-1-0 | 513-3-0 | 522-2-4 | 513-1-2 | C4-B1 | Sideways / Tier 2 |
| 2026.03.30 18:00 | 521-3-0 | 513-1-2 | 512-1-3 | 513-3-0 | 522-2-4 | 513-1-2 | C4-B1 | Sideways / Tier 2 |
| 2026.03.30 19:00 | 512-1-3 | 513-1-0 | 512-1-0 | 513-3-0 | 522-2-4 | 513-1-2 | C4-B1 | Sideways / Tier 2 |
| 2026.03.30 19:15 | 512-5-0 | 513-1-0 | 512-1-0 | 513-3-0 | 522-2-4 | 513-1-2 | C4-B1 | Sideways / Tier 2 |
| 2026.03.30 19:45 | 512-2-0 | 513-3-0 | 512-1-0 | 513-3-0 | 522-2-4 | 513-1-2 | C4-B1 | Sideways / Tier 2 |
| 2026.03.30 20:15 | 522-2-4 | 513-3-3 | 512-1-3 | 513-3-2 | 522-2-4 | 513-1-2 | C4-B1 | Sideways / Tier 2 |
| 2026.03.30 21:15 | 523-2-2 | 521-2-1 | 512-1-3 | 513-3-2 | 522-2-4 | 513-1-2 | C4-S1 | Sideways / Tier 2 |
| 2026.03.30 21:45 | 412-2-0 | 521-2-1 | 512-1-3 | 513-3-2 | 522-2-4 | 513-1-2 | C4-C1 | Sideways / Tier 2 |
| 2026.03.30 22:00 | 521-2-1 | 521-2-1 | 512-1-0 | 513-3-2 | 522-2-4 | 513-1-2 | C4-F | Sideways / Tier 2 |
| 2026.03.30 23:00 | 522-2-4 | 521-2-1 | 513-1-2 | 513-3-2 | 522-2-4 | 513-1-2 | C4-B2 | Sideways / Tier 2 |
| 2026.03.31 01:00 | 523-2-2 | 521-2-0 | 513-1-2 | 513-4-2 | 522-2-4 | 513-1-2 | C4-S1 | Sideways / Tier 2 |
| 2026.03.31 02:45 | 523-3-2 | 522-2-0 | 513-1-2 | 513-4-2 | 522-2-4 | 513-1-2 | C4-S1 | Sideways / Tier 2 |
| 2026.03.31 03:00 | 523-4-2 | 523-2-2 | 513-1-2 | 513-4-2 | 522-2-4 | 513-1-2 | C4-S3 | Sideways / Tier 2 |
| 2026.03.31 03:15 | 423-3-1 | 523-2-2 | 513-1-2 | 513-4-2 | 522-2-4 | 513-1-2 | C4-C1 | Sideways / Tier 2 |
| 2026.03.31 03:30 | 423-4-0 | 523-2-2 | 513-1-2 | 513-4-2 | 522-2-4 | 513-1-2 | C4-C1 | Sideways / Tier 2 |
| 2026.03.31 03:45 | 521-4-1 | 523-2-2 | 513-1-2 | 513-4-2 | 522-2-4 | 513-1-2 | C4-B1 | Sideways / Tier 2 |
| 2026.03.31 04:00 | 511-1-1 | 413-3-0 | 513-1-0 | 513-3-0 | 522-2-4 | 513-1-2 | C4-B1 | Sideways / Tier 2 |
| 2026.03.31 05:30 | 512-1-3 | 511-1-1 | 411-1-0 | 513-3-0 | 522-2-4 | 513-1-2 | C4-B2 | Sideways / Tier 2 |
| 2026.03.31 07:15 | 513-1-2 | 511-1-0 | 511-1-0 | 513-3-0 | 522-2-4 | 513-1-2 | C4-S1 | Sideways / Tier 2 |
| 2026.03.31 09:15 | 513-3-0 | 512-1-3 | 512-1-3 | 511-1-1 | 522-2-4 | 513-1-2 | F2-S1 | Up (div) / Tier 1 |
| 2026.03.31 09:45 | 513-2-2 | 512-1-3 | 512-1-3 | 511-1-1 | 522-2-4 | 513-1-2 | F2-S1 [divergence] | Up (div) / Tier 1 |
| 2026.03.31 11:00 | 513-4-2 | 513-1-2 | 512-5-0 | 511-1-1 | 522-2-4 | 513-1-2 | F2-S2 | Up (div) / Tier 1 |
| 2026.03.31 11:15 | 424-4-0 | 513-1-2 | 512-5-0 | 511-1-1 | 522-2-4 | 513-1-2 | F2-C1 | Up (div) / Tier 1 |
| 2026.03.31 11:30 | 521-4-1 | 512-1-3 | 512-5-0 | 511-1-1 | 522-2-4 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.03.31 11:45 | 521-1-0 | 512-1-3 | 512-5-0 | 511-1-1 | 522-2-4 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.03.31 12:00 | 512-1-3 | 512-1-0 | 512-3-1 | 511-5-1 | 522-2-4 | 513-1-2 | F3-F | Sideways / Tier 1 |
| 2026.03.31 12:15 | 512-5-3 | 512-1-0 | 512-3-1 | 511-5-1 | 522-2-4 | 513-1-2 | F3-F | Sideways / Tier 1 |
| 2026.03.31 12:30 | 512-3-0 | 513-1-2 | 512-3-1 | 511-5-1 | 522-2-4 | 513-1-2 | F3-F | Sideways / Tier 1 |
| 2026.03.31 12:45 | 512-4-0 | 513-1-2 | 512-3-1 | 511-5-1 | 522-2-4 | 513-1-2 | F3-F | Sideways / Tier 1 |
| 2026.03.31 13:15 | 521-4-1 | 513-1-2 | 512-3-0 | 511-5-1 | 522-2-4 | 513-1-2 | F3-F | Sideways / Tier 1 |
| 2026.03.31 13:45 | 521-2-0 | 513-1-2 | 512-3-0 | 511-5-1 | 522-2-4 | 513-1-2 | F3-F | Sideways / Tier 1 |
| 2026.03.31 14:15 | 521-4-0 | 413-3-0 | 512-1-0 | 511-5-1 | 522-2-4 | 513-1-2 | F3-F | Sideways / Tier 1 |
| 2026.03.31 14:45 | 511-1-1 | 413-2-0 | 512-1-0 | 511-5-1 | 522-2-4 | 513-1-2 | F3-F | Sideways / Tier 1 |
| 2026.03.31 15:30 | 512-1-3 | 413-3-0 | 512-1-0 | 511-5-1 | 522-2-4 | 513-1-2 | F3-F | Sideways / Tier 1 |
| 2026.03.31 16:00 | 512-5-3 | 511-5-1 | 512-1-0 | 511-1-1 | 522-2-4 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.03.31 16:15 | 512-1-0 | 511-5-1 | 512-1-0 | 511-1-1 | 522-2-4 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.03.31 16:45 | 511-1-1 | 511-1-0 | 512-1-0 | 511-1-1 | 522-2-4 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.03.31 18:00 | 512-1-3 | 511-1-0 | 511-1-0 | 511-1-1 | 522-2-4 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.03.31 23:45 | 513-1-2 | 512-1-3 | 512-1-3 | 511-1-1 | 522-2-4 | 513-1-2 | F2-S1 | Up (div) / Tier 1 |
| 2026.04.01 02:45 | 512-1-3 | 512-1-3 | 511-1-1 | 511-1-0 | 522-2-4 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.04.01 03:30 | 511-1-1 | 512-1-3 | 511-1-0 | 511-1-0 | 522-2-4 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.04.01 04:00 | 512-1-3 | 512-1-3 | 511-1-0 | 511-1-0 | 522-2-4 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.04.01 05:30 | 512-5-3 | 512-1-0 | 512-1-3 | 511-1-0 | 522-2-4 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.04.01 05:45 | 512-3-0 | 512-1-0 | 512-1-3 | 511-1-0 | 522-2-4 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.04.01 06:00 | 513-5-2 | 513-1-2 | 512-1-3 | 511-1-0 | 522-2-4 | 513-1-2 | F2-S2 | Up (div) / Tier 1 |
| 2026.04.01 06:30 | 513-1-2 | 513-1-2 | 512-1-3 | 511-1-0 | 522-2-4 | 513-1-2 | F2-S2 | Up (div) / Tier 1 |
| 2026.04.01 07:00 | 513-5-2 | 513-1-2 | 512-1-3 | 511-1-0 | 522-2-4 | 513-1-2 | F2-S2 | Up (div) / Tier 1 |
| 2026.04.01 07:15 | 415-5-1 | 513-1-2 | 512-1-3 | 511-1-0 | 522-2-4 | 513-1-2 | F2-C1 | Up (div) / Tier 1 |
| 2026.04.01 07:30 | 422-2-1 | 513-1-2 | 512-1-3 | 511-1-0 | 522-2-4 | 513-1-2 | F2-C1 [divergence] | Up (div) / Tier 1 |
| 2026.04.01 07:45 | 521-2-1 | 513-1-2 | 512-1-3 | 511-1-0 | 522-2-4 | 513-1-2 | F2-F [divergence] | Up (div) / Tier 1 |
| 2026.04.01 08:38 | 523-2-2 | 513-1-0 | 512-1-3 | 512-1-3 | 522-2-4 | 513-1-2 | F2-S2 [divergence] | Up (div) / Tier 1 |
| 2026.04.01 08:45 | 523-4-2 | 513-1-0 | 512-1-3 | 512-1-3 | 522-2-4 | 513-1-2 | F2-S2 | Up (div) / Tier 1 |
| 2026.04.01 09:00 | 523-2-2 | 513-1-2 | 512-1-3 | 512-1-3 | 522-2-4 | 513-1-2 | F2-S2 [divergence] | Up (div) / Tier 1 |

**Coverage:** 2026.03.30 14:30 → 2026.04.01 09:00 | Period: 2026.03.30 14:30 → 2026.04.01 09:00 | **COMPLETE**

#### Image 3 Analysis — backtested_EA_b_to_e_to_g_progression.jpg
![backtested_EA_b_to_e_to_g_progression](./Backtest_data/extras/backtested_EA_b_to_e_to_g_progression.jpg)

**Period:** 2026.03.30 13:00 → 2026.04.01 17:00 (chart x-axis: "30.03.2026" / "01.04.2026", extended view)

> **Cell = BBW_stage-diffMid-BBUpDn** (e.g. 511-1-1). BBW: 511/512=up-fly,
> 521/522=down-fly, 513/523=shrink, 4xx=SQZ. diffMid: 1=up, 2=down,
> 3=sideways, 5=deep-sideways. BBUpDn: 0=between, 1=upper, 2=lower,
> 3=sideways. A new row is added only when M15 BBW_stage or diffMid changes.
> All rows fall within the user-defined period.

| datetime | M15 | M30 | H1 | H4 | D1 | W1 | Scenario (HTF-MTF) | Trend / Tier |
|----------|-----|-----|----|----|----|----|--------------------|------------|
| 2026.03.30 13:00 | 513-1-2 | 512-1-3 | 512-1-0 | 513-4-0 | 522-2-4 | 513-1-2 | C4-S1 | Sideways / Tier 2 |
| 2026.03.30 14:00 | 513-5-2 | 513-1-2 | 512-1-0 | 513-4-0 | 522-2-4 | 513-1-2 | C4-S2 | Sideways / Tier 2 |
| 2026.03.30 14:15 | 425-5-0 | 513-1-2 | 512-1-0 | 513-4-0 | 522-2-4 | 513-1-2 | C4-C1 | Sideways / Tier 2 |
| 2026.03.30 14:30 | 511-5-1 | 513-1-2 | 512-1-0 | 513-4-0 | 522-2-4 | 513-1-2 | C4-B1 | Sideways / Tier 2 |
| 2026.03.30 14:45 | 511-1-1 | 513-1-2 | 512-1-0 | 513-4-0 | 522-2-4 | 513-1-2 | C4-B1 | Sideways / Tier 2 |
| 2026.03.30 16:00 | 512-1-3 | 512-1-3 | 511-1-1 | 513-3-0 | 522-2-4 | 513-1-2 | C4-F | Sideways / Tier 2 |
| 2026.03.30 16:45 | 512-5-3 | 512-1-3 | 511-1-1 | 513-3-0 | 522-2-4 | 513-1-2 | C4-F | Sideways / Tier 2 |
| 2026.03.30 17:00 | 511-5-1 | 512-1-0 | 511-1-0 | 513-3-0 | 522-2-4 | 513-1-2 | C4-F | Sideways / Tier 2 |
| 2026.03.30 17:30 | 521-2-1 | 513-1-2 | 511-1-0 | 513-3-0 | 522-2-4 | 513-1-2 | C4-B1 | Sideways / Tier 2 |
| 2026.03.30 18:00 | 521-3-0 | 513-1-2 | 512-1-3 | 513-3-0 | 522-2-4 | 513-1-2 | C4-B1 | Sideways / Tier 2 |
| 2026.03.30 19:00 | 512-1-3 | 513-1-0 | 512-1-0 | 513-3-0 | 522-2-4 | 513-1-2 | C4-B1 | Sideways / Tier 2 |
| 2026.03.30 19:15 | 512-5-0 | 513-1-0 | 512-1-0 | 513-3-0 | 522-2-4 | 513-1-2 | C4-B1 | Sideways / Tier 2 |
| 2026.03.30 19:45 | 512-2-0 | 513-3-0 | 512-1-0 | 513-3-0 | 522-2-4 | 513-1-2 | C4-B1 | Sideways / Tier 2 |
| 2026.03.30 20:15 | 522-2-4 | 513-3-3 | 512-1-3 | 513-3-2 | 522-2-4 | 513-1-2 | C4-B1 | Sideways / Tier 2 |
| 2026.03.30 21:15 | 523-2-2 | 521-2-1 | 512-1-3 | 513-3-2 | 522-2-4 | 513-1-2 | C4-S1 | Sideways / Tier 2 |
| 2026.03.30 21:45 | 412-2-0 | 521-2-1 | 512-1-3 | 513-3-2 | 522-2-4 | 513-1-2 | C4-C1 | Sideways / Tier 2 |
| 2026.03.30 22:00 | 521-2-1 | 521-2-1 | 512-1-0 | 513-3-2 | 522-2-4 | 513-1-2 | C4-F | Sideways / Tier 2 |
| 2026.03.30 23:00 | 522-2-4 | 521-2-1 | 513-1-2 | 513-3-2 | 522-2-4 | 513-1-2 | C4-B2 | Sideways / Tier 2 |
| 2026.03.31 01:00 | 523-2-2 | 521-2-0 | 513-1-2 | 513-4-2 | 522-2-4 | 513-1-2 | C4-S1 | Sideways / Tier 2 |
| 2026.03.31 02:45 | 523-3-2 | 522-2-0 | 513-1-2 | 513-4-2 | 522-2-4 | 513-1-2 | C4-S1 | Sideways / Tier 2 |
| 2026.03.31 03:00 | 523-4-2 | 523-2-2 | 513-1-2 | 513-4-2 | 522-2-4 | 513-1-2 | C4-S3 | Sideways / Tier 2 |
| 2026.03.31 03:15 | 423-3-1 | 523-2-2 | 513-1-2 | 513-4-2 | 522-2-4 | 513-1-2 | C4-C1 | Sideways / Tier 2 |
| 2026.03.31 03:30 | 423-4-0 | 523-2-2 | 513-1-2 | 513-4-2 | 522-2-4 | 513-1-2 | C4-C1 | Sideways / Tier 2 |
| 2026.03.31 03:45 | 521-4-1 | 523-2-2 | 513-1-2 | 513-4-2 | 522-2-4 | 513-1-2 | C4-B1 | Sideways / Tier 2 |
| 2026.03.31 04:00 | 511-1-1 | 413-3-0 | 513-1-0 | 513-3-0 | 522-2-4 | 513-1-2 | C4-B1 | Sideways / Tier 2 |
| 2026.03.31 05:30 | 512-1-3 | 511-1-1 | 411-1-0 | 513-3-0 | 522-2-4 | 513-1-2 | C4-B2 | Sideways / Tier 2 |
| 2026.03.31 07:15 | 513-1-2 | 511-1-0 | 511-1-0 | 513-3-0 | 522-2-4 | 513-1-2 | C4-S1 | Sideways / Tier 2 |
| 2026.03.31 09:15 | 513-3-0 | 512-1-3 | 512-1-3 | 511-1-1 | 522-2-4 | 513-1-2 | F2-S1 | Up (div) / Tier 1 |
| 2026.03.31 09:45 | 513-2-2 | 512-1-3 | 512-1-3 | 511-1-1 | 522-2-4 | 513-1-2 | F2-S1 [divergence] | Up (div) / Tier 1 |
| 2026.03.31 11:00 | 513-4-2 | 513-1-2 | 512-5-0 | 511-1-1 | 522-2-4 | 513-1-2 | F2-S2 | Up (div) / Tier 1 |
| 2026.03.31 11:15 | 424-4-0 | 513-1-2 | 512-5-0 | 511-1-1 | 522-2-4 | 513-1-2 | F2-C1 | Up (div) / Tier 1 |
| 2026.03.31 11:30 | 521-4-1 | 512-1-3 | 512-5-0 | 511-1-1 | 522-2-4 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.03.31 11:45 | 521-1-0 | 512-1-3 | 512-5-0 | 511-1-1 | 522-2-4 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.03.31 12:00 | 512-1-3 | 512-1-0 | 512-3-1 | 511-5-1 | 522-2-4 | 513-1-2 | F3-F | Sideways / Tier 1 |
| 2026.03.31 12:15 | 512-5-3 | 512-1-0 | 512-3-1 | 511-5-1 | 522-2-4 | 513-1-2 | F3-F | Sideways / Tier 1 |
| 2026.03.31 12:30 | 512-3-0 | 513-1-2 | 512-3-1 | 511-5-1 | 522-2-4 | 513-1-2 | F3-F | Sideways / Tier 1 |
| 2026.03.31 12:45 | 512-4-0 | 513-1-2 | 512-3-1 | 511-5-1 | 522-2-4 | 513-1-2 | F3-F | Sideways / Tier 1 |
| 2026.03.31 13:15 | 521-4-1 | 513-1-2 | 512-3-0 | 511-5-1 | 522-2-4 | 513-1-2 | F3-F | Sideways / Tier 1 |
| 2026.03.31 13:45 | 521-2-0 | 513-1-2 | 512-3-0 | 511-5-1 | 522-2-4 | 513-1-2 | F3-F | Sideways / Tier 1 |
| 2026.03.31 14:15 | 521-4-0 | 413-3-0 | 512-1-0 | 511-5-1 | 522-2-4 | 513-1-2 | F3-F | Sideways / Tier 1 |
| 2026.03.31 14:45 | 511-1-1 | 413-2-0 | 512-1-0 | 511-5-1 | 522-2-4 | 513-1-2 | F3-F | Sideways / Tier 1 |
| 2026.03.31 15:30 | 512-1-3 | 413-3-0 | 512-1-0 | 511-5-1 | 522-2-4 | 513-1-2 | F3-F | Sideways / Tier 1 |
| 2026.03.31 16:00 | 512-5-3 | 511-5-1 | 512-1-0 | 511-1-1 | 522-2-4 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.03.31 16:15 | 512-1-0 | 511-5-1 | 512-1-0 | 511-1-1 | 522-2-4 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.03.31 16:45 | 511-1-1 | 511-1-0 | 512-1-0 | 511-1-1 | 522-2-4 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.03.31 18:00 | 512-1-3 | 511-1-0 | 511-1-0 | 511-1-1 | 522-2-4 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.03.31 23:45 | 513-1-2 | 512-1-3 | 512-1-3 | 511-1-1 | 522-2-4 | 513-1-2 | F2-S1 | Up (div) / Tier 1 |
| 2026.04.01 02:45 | 512-1-3 | 512-1-3 | 511-1-1 | 511-1-0 | 522-2-4 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.04.01 03:30 | 511-1-1 | 512-1-3 | 511-1-0 | 511-1-0 | 522-2-4 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.04.01 04:00 | 512-1-3 | 512-1-3 | 511-1-0 | 511-1-0 | 522-2-4 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.04.01 05:30 | 512-5-3 | 512-1-0 | 512-1-3 | 511-1-0 | 522-2-4 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.04.01 05:45 | 512-3-0 | 512-1-0 | 512-1-3 | 511-1-0 | 522-2-4 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.04.01 06:00 | 513-5-2 | 513-1-2 | 512-1-3 | 511-1-0 | 522-2-4 | 513-1-2 | F2-S2 | Up (div) / Tier 1 |
| 2026.04.01 06:30 | 513-1-2 | 513-1-2 | 512-1-3 | 511-1-0 | 522-2-4 | 513-1-2 | F2-S2 | Up (div) / Tier 1 |
| 2026.04.01 07:00 | 513-5-2 | 513-1-2 | 512-1-3 | 511-1-0 | 522-2-4 | 513-1-2 | F2-S2 | Up (div) / Tier 1 |
| 2026.04.01 07:15 | 415-5-1 | 513-1-2 | 512-1-3 | 511-1-0 | 522-2-4 | 513-1-2 | F2-C1 | Up (div) / Tier 1 |
| 2026.04.01 07:30 | 422-2-1 | 513-1-2 | 512-1-3 | 511-1-0 | 522-2-4 | 513-1-2 | F2-C1 [divergence] | Up (div) / Tier 1 |
| 2026.04.01 07:45 | 521-2-1 | 513-1-2 | 512-1-3 | 511-1-0 | 522-2-4 | 513-1-2 | F2-F [divergence] | Up (div) / Tier 1 |
| 2026.04.01 08:38 | 523-2-2 | 513-1-0 | 512-1-3 | 512-1-3 | 522-2-4 | 513-1-2 | F2-S2 [divergence] | Up (div) / Tier 1 |
| 2026.04.01 08:45 | 523-4-2 | 513-1-0 | 512-1-3 | 512-1-3 | 522-2-4 | 513-1-2 | F2-S2 | Up (div) / Tier 1 |
| 2026.04.01 09:00 | 523-2-2 | 513-1-2 | 512-1-3 | 512-1-3 | 522-2-4 | 513-1-2 | F2-S2 [divergence] | Up (div) / Tier 1 |
| 2026.04.01 09:30 | 413-3-1 | 411-1-3 | 512-1-3 | 512-1-3 | 522-2-4 | 513-1-2 | F2-C3 | Up (div) / Tier 1 |
| 2026.04.01 09:45 | 421-1-1 | 411-1-3 | 512-1-3 | 512-1-3 | 522-2-4 | 513-1-2 | F2-C3 | Up (div) / Tier 1 |
| 2026.04.01 10:00 | 511-1-1 | 511-1-1 | 512-1-3 | 512-1-3 | 522-2-4 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.04.01 11:00 | 512-1-3 | 511-1-0 | 512-1-0 | 512-1-3 | 522-2-4 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.04.01 12:30 | 513-1-2 | 512-1-3 | 512-1-3 | 512-1-3 | 522-2-4 | 513-1-2 | F2-S1 | Up (div) / Tier 1 |
| 2026.04.01 14:30 | 512-1-3 | 511-1-1 | 512-1-0 | 512-1-3 | 522-2-4 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.04.01 14:45 | 511-1-1 | 511-1-1 | 512-1-0 | 512-1-3 | 522-2-4 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.04.01 15:15 | 512-1-3 | 511-1-0 | 512-1-3 | 512-1-3 | 522-2-4 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.04.01 15:30 | 512-3-3 | 512-1-3 | 512-1-3 | 512-1-3 | 522-2-4 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.04.01 16:15 | 512-5-0 | 512-1-3 | 513-1-2 | 512-1-3 | 522-2-4 | 513-1-2 | F2-F | Up (div) / Tier 1 |

**Coverage:** 2026.03.30 13:00 → 2026.04.01 16:15 | Period: 2026.03.30 13:00 → 2026.04.01 17:00 | **COMPLETE**

---

## Scenario P (Rest Recovery / Pause)

#### Image 1 Analysis — backtested_EA_fly_2_shrink_2_fly.jpg
![backtested_EA_fly_2_shrink_2_fly](./Backtest_data/extras/backtested_EA_fly_2_shrink_2_fly.jpg)

**Period:** 2026.04.03 03:00 → 2026.04.05 00:00 (chart x-axis: "03.04.2026" / "04.04.2026" / "05.04.2026")

  > **No log data available for this period.**

#### Image 2 Analysis — backtested_EA_fly_2_shrink_2_fly_zoomin.jpg
![backtested_EA_fly_2_shrink_2_fly_zoomin](./Backtest_data/extras/backtested_EA_fly_2_shrink_2_fly_zoomin.jpg)

**Period:** 2026.04.04 15:00 → 2026.04.05 00:00 (chart x-axis: "04.04.2026" / "05.04.2026")

  > **No log data available for this period.**

---

## Scenario R (Reversal)

#### Image 1 Analysis — backtested_EA_trend_reversal.jpg
![backtested_EA_trend_reversal](./Backtest_data/extras/backtested_EA_trend_reversal.jpg)

**Period:** 2026.04.01 14:30 → 2026.04.02 05:00 (chart x-axis: "01.04.2026" / "02.04.2026", log-confirmed)

> **Cell = BBW_stage-diffMid-BBUpDn** (e.g. 511-1-1). BBW: 511/512=up-fly,
> 521/522=down-fly, 513/523=shrink, 4xx=SQZ. diffMid: 1=up, 2=down,
> 3=sideways, 5=deep-sideways. BBUpDn: 0=between, 1=upper, 2=lower,
> 3=sideways. A new row is added only when M15 BBW_stage or diffMid changes.
> All rows fall within the user-defined period.

| datetime | M15 | M30 | H1 | H4 | D1 | W1 | Scenario (HTF-MTF) | Trend / Tier |
|----------|-----|-----|----|----|----|----|--------------------|------------|
| 2026.04.01 14:30 | 512-1-3 | 511-1-1 | 512-1-0 | 512-1-3 | 522-2-4 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.04.01 14:45 | 511-1-1 | 511-1-1 | 512-1-0 | 512-1-3 | 522-2-4 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.04.01 15:15 | 512-1-3 | 511-1-0 | 512-1-3 | 512-1-3 | 522-2-4 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.04.01 15:30 | 512-3-3 | 512-1-3 | 512-1-3 | 512-1-3 | 522-2-4 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.04.01 16:15 | 512-5-0 | 512-1-3 | 513-1-2 | 512-1-3 | 522-2-4 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.04.01 17:15 | 512-1-3 | 512-1-0 | 513-1-0 | 512-1-3 | 522-2-4 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.04.01 18:45 | 511-1-1 | 411-1-3 | 411-1-3 | 512-1-3 | 522-2-4 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.04.01 20:30 | 512-1-3 | 512-1-0 | 511-1-0 | 512-1-3 | 522-2-4 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.04.01 21:15 | 513-1-2 | 512-1-3 | 512-1-3 | 512-1-3 | 522-2-4 | 513-1-2 | F2-S1 | Up (div) / Tier 1 |
| 2026.04.01 22:45 | 513-5-2 | 513-1-2 | 512-1-3 | 512-1-3 | 522-2-4 | 513-1-2 | F2-S2 | Up (div) / Tier 1 |
| 2026.04.01 23:00 | 513-3-0 | 513-1-0 | 512-1-3 | 512-1-3 | 522-2-4 | 513-1-2 | F2-S2 | Up (div) / Tier 1 |
| 2026.04.01 23:30 | 513-2-4 | 513-1-2 | 512-1-3 | 512-1-3 | 522-2-4 | 513-1-2 | F2-S2 [divergence] | Up (div) / Tier 1 |
| 2026.04.01 23:45 | 523-2-4 | 513-1-2 | 512-1-3 | 512-1-3 | 522-2-4 | 513-1-2 | F2-S2 [divergence] | Up (div) / Tier 1 |
| 2026.04.02 01:00 | 522-2-4 | 513-1-2 | 512-1-3 | 512-1-3 | 523-2-0 | 513-1-2 | F2-F [divergence] | Up (div) / Tier 1 |
| 2026.04.02 01:30 | 522-4-0 | 411-1-0 | 512-1-3 | 512-1-3 | 523-2-0 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.04.02 01:45 | 523-4-2 | 411-1-0 | 512-1-3 | 512-1-3 | 523-2-0 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.04.02 02:00 | 523-2-2 | 411-1-3 | 512-1-3 | 512-1-3 | 523-2-0 | 513-1-2 | F2-F [divergence] | Up (div) / Tier 1 |
| 2026.04.02 02:15 | 523-3-0 | 411-1-3 | 512-1-3 | 512-1-3 | 523-2-0 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.04.02 02:45 | 511-1-1 | 411-1-3 | 512-1-3 | 512-1-3 | 523-2-0 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.04.02 03:45 | 512-1-3 | 411-1-0 | 512-1-3 | 512-1-3 | 523-2-0 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.04.02 04:15 | 512-3-1 | 411-1-0 | 512-1-0 | 512-1-3 | 523-2-0 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.04.02 04:30 | 521-2-1 | 413-3-1 | 512-1-0 | 512-1-3 | 523-2-0 | 513-1-2 | F2-F [divergence] | Up (div) / Tier 1 |

**Coverage:** 2026.04.01 14:30 → 2026.04.02 04:30 | Period: 2026.04.01 14:30 → 2026.04.02 05:00 | **COMPLETE**

#### Image 2 Analysis — backtested_EA_test_phase_April_01.jpg
![backtested_EA_test_phase_April_01](./Backtest_data/extras/backtested_EA_test_phase_April_01.jpg)

**Period:** 2026.04.01 14:30 → 2026.04.02 09:00 (chart x-axis: "01.04.2026" / "02.04.2026", extended view of reversal)

> **Cell = BBW_stage-diffMid-BBUpDn** (e.g. 511-1-1). BBW: 511/512=up-fly,
> 521/522=down-fly, 513/523=shrink, 4xx=SQZ. diffMid: 1=up, 2=down,
> 3=sideways, 5=deep-sideways. BBUpDn: 0=between, 1=upper, 2=lower,
> 3=sideways. A new row is added only when M15 BBW_stage or diffMid changes.
> All rows fall within the user-defined period.

| datetime | M15 | M30 | H1 | H4 | D1 | W1 | Scenario (HTF-MTF) | Trend / Tier |
|----------|-----|-----|----|----|----|----|--------------------|------------|
| 2026.04.01 14:30 | 512-1-3 | 511-1-1 | 512-1-0 | 512-1-3 | 522-2-4 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.04.01 14:45 | 511-1-1 | 511-1-1 | 512-1-0 | 512-1-3 | 522-2-4 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.04.01 15:15 | 512-1-3 | 511-1-0 | 512-1-3 | 512-1-3 | 522-2-4 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.04.01 15:30 | 512-3-3 | 512-1-3 | 512-1-3 | 512-1-3 | 522-2-4 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.04.01 16:15 | 512-5-0 | 512-1-3 | 513-1-2 | 512-1-3 | 522-2-4 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.04.01 17:15 | 512-1-3 | 512-1-0 | 513-1-0 | 512-1-3 | 522-2-4 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.04.01 18:45 | 511-1-1 | 411-1-3 | 411-1-3 | 512-1-3 | 522-2-4 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.04.01 20:30 | 512-1-3 | 512-1-0 | 511-1-0 | 512-1-3 | 522-2-4 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.04.01 21:15 | 513-1-2 | 512-1-3 | 512-1-3 | 512-1-3 | 522-2-4 | 513-1-2 | F2-S1 | Up (div) / Tier 1 |
| 2026.04.01 22:45 | 513-5-2 | 513-1-2 | 512-1-3 | 512-1-3 | 522-2-4 | 513-1-2 | F2-S2 | Up (div) / Tier 1 |
| 2026.04.01 23:00 | 513-3-0 | 513-1-0 | 512-1-3 | 512-1-3 | 522-2-4 | 513-1-2 | F2-S2 | Up (div) / Tier 1 |
| 2026.04.01 23:30 | 513-2-4 | 513-1-2 | 512-1-3 | 512-1-3 | 522-2-4 | 513-1-2 | F2-S2 [divergence] | Up (div) / Tier 1 |
| 2026.04.01 23:45 | 523-2-4 | 513-1-2 | 512-1-3 | 512-1-3 | 522-2-4 | 513-1-2 | F2-S2 [divergence] | Up (div) / Tier 1 |
| 2026.04.02 01:00 | 522-2-4 | 513-1-2 | 512-1-3 | 512-1-3 | 523-2-0 | 513-1-2 | F2-F [divergence] | Up (div) / Tier 1 |
| 2026.04.02 01:30 | 522-4-0 | 411-1-0 | 512-1-3 | 512-1-3 | 523-2-0 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.04.02 01:45 | 523-4-2 | 411-1-0 | 512-1-3 | 512-1-3 | 523-2-0 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.04.02 02:00 | 523-2-2 | 411-1-3 | 512-1-3 | 512-1-3 | 523-2-0 | 513-1-2 | F2-F [divergence] | Up (div) / Tier 1 |
| 2026.04.02 02:15 | 523-3-0 | 411-1-3 | 512-1-3 | 512-1-3 | 523-2-0 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.04.02 02:45 | 511-1-1 | 411-1-3 | 512-1-3 | 512-1-3 | 523-2-0 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.04.02 03:45 | 512-1-3 | 411-1-0 | 512-1-3 | 512-1-3 | 523-2-0 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.04.02 04:15 | 512-3-1 | 411-1-0 | 512-1-0 | 512-1-3 | 523-2-0 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.04.02 04:30 | 521-2-1 | 413-3-1 | 512-1-0 | 512-1-3 | 523-2-0 | 513-1-2 | F2-F [divergence] | Up (div) / Tier 1 |
| 2026.04.02 06:30 | 522-2-4 | 521-2-0 | 512-3-1 | 512-1-3 | 523-2-0 | 513-1-2 | F2-R1 [divergence] | Up (div) / Tier 1 |
| 2026.04.02 08:15 | 523-2-2 | 522-2-4 | 521-2-1 | 512-1-0 | 523-2-0 | 513-1-2 | F2-R1 [divergence] | Up (div) / Tier 1 |
| 2026.04.02 09:00 | 412-2-4 | 521-2-1 | 521-2-1 | 512-1-0 | 523-2-0 | 513-1-2 | F2-R1 [divergence] | Up (div) / Tier 1 |

**Coverage:** 2026.04.01 14:30 → 2026.04.02 09:00 | Period: 2026.04.01 14:30 → 2026.04.02 09:00 | **COMPLETE**

---

## Scenario B (Compression Release / Breakout)

#### Image 1 Analysis — backtested_EA_sideway_2_fly.jpg
![backtested_EA_sideway_2_fly](./Backtest_data/extras/backtested_EA_sideway_2_fly.jpg)

**Period:** 2026.02.06 01:00 → 2026.02.07 21:00 (chart x-axis: "06.02.2026" / "07.02.2026", log-confirmed)

> **Cell = BBW_stage-diffMid-BBUpDn** (e.g. 511-1-1). BBW: 511/512=up-fly,
> 521/522=down-fly, 513/523=shrink, 4xx=SQZ. diffMid: 1=up, 2=down,
> 3=sideways, 5=deep-sideways. BBUpDn: 0=between, 1=upper, 2=lower,
> 3=sideways. A new row is added only when M15 BBW_stage or diffMid changes.
> All rows fall within the user-defined period.

| datetime | M15 | M30 | H1 | H4 | D1 | W1 | Scenario (HTF-MTF) | Trend / Tier |
|----------|-----|-----|----|----|----|----|--------------------|------------|
| 2026.02.06 01:00 | 522-2-4 | 521-2-1 | 402-2-0 | 513-1-2 | 513-1-2 | 401-1-0 | C4-B2 [divergence] | Up / Tier 2 |
| 2026.02.06 02:15 | 521-2-1 | 521-2-1 | 521-2-1 | 513-1-2 | 513-1-2 | 401-1-0 | C4-F [divergence] | Up / Tier 2 |
| 2026.02.06 02:30 | 522-2-4 | 521-2-1 | 521-2-1 | 513-1-2 | 513-1-2 | 401-1-0 | C4-F [divergence] | Up / Tier 2 |
| 2026.02.06 04:00 | 523-2-2 | 522-2-4 | 521-2-0 | 513-1-2 | 513-1-2 | 401-1-0 | C4-S1 [divergence] | Up / Tier 2 |
| 2026.02.06 04:30 | 523-3-2 | 522-3-4 | 521-2-0 | 513-1-2 | 513-1-2 | 401-1-0 | C4-S1 [divergence] | Up / Tier 2 |
| 2026.02.06 04:45 | 403-3-1 | 522-3-4 | 521-2-0 | 513-1-2 | 513-1-2 | 401-1-0 | C4-C1 [divergence] | Up / Tier 2 |
| 2026.02.06 05:30 | 403-1-1 | 522-2-0 | 522-2-4 | 513-1-2 | 513-1-2 | 401-1-0 | C4-C1 [divergence] | Up / Tier 2 |
| 2026.02.06 07:45 | 511-1-3 | 523-2-2 | 523-2-2 | 513-1-2 | 513-1-2 | 401-1-0 | C4-B1 [divergence] | Up / Tier 2 |
| 2026.02.06 08:00 | 512-1-3 | 403-3-1 | 403-3-0 | 513-1-2 | 513-1-2 | 401-1-0 | C4-B1 | Up / Tier 2 |
| 2026.02.06 08:30 | 513-1-2 | 403-3-1 | 403-3-0 | 513-1-2 | 513-1-2 | 401-1-0 | C4-F | Up / Tier 2 |
| 2026.02.06 09:30 | 411-1-3 | 403-1-1 | 403-3-2 | 513-1-2 | 513-1-2 | 401-1-0 | C4-C3 | Up / Tier 2 |
| 2026.02.06 12:30 | 411-3-0 | 403-1-2 | 403-3-1 | 513-1-2 | 513-1-2 | 401-1-0 | C4-C2 | Up / Tier 2 |
| 2026.02.06 12:45 | 411-5-0 | 403-1-2 | 403-3-1 | 513-1-2 | 513-1-2 | 401-1-0 | C4-C2 | Up / Tier 2 |
| 2026.02.06 13:00 | 411-4-2 | 403-1-2 | 403-1-1 | 513-1-2 | 513-1-2 | 401-1-0 | C4-C2 | Up / Tier 2 |
| 2026.02.06 13:15 | 521-4-0 | 403-1-2 | 403-1-1 | 513-1-2 | 513-1-2 | 401-1-0 | C4-B1 | Up / Tier 2 |
| 2026.02.06 13:30 | 511-1-1 | 403-1-2 | 403-1-1 | 513-1-2 | 513-1-2 | 401-1-0 | C4-B1 | Up / Tier 2 |
| 2026.02.06 14:00 | 512-1-3 | 403-1-0 | 403-1-1 | 513-1-2 | 513-1-2 | 401-1-0 | C4-B1 | Up / Tier 2 |
| 2026.02.06 15:30 | 511-1-1 | 512-1-3 | 511-1-1 | 513-1-2 | 513-1-2 | 401-1-0 | C4-F | Up / Tier 2 |
| 2026.02.06 16:15 | 512-1-3 | 512-1-3 | 511-1-1 | 513-1-0 | 513-1-2 | 401-1-0 | C4-F | Up / Tier 2 |
| 2026.02.06 19:45 | 513-1-2 | 512-1-3 | 511-1-1 | 513-1-0 | 513-1-2 | 401-1-0 | C4-S1 | Up / Tier 2 |
| 2026.02.06 20:00 | 512-1-3 | 512-1-3 | 511-1-0 | 512-1-3 | 513-1-2 | 401-1-0 | F1-F | Up / Tier 1 |
| 2026.02.06 21:30 | 513-1-2 | 512-1-3 | 512-1-3 | 512-1-3 | 513-1-2 | 401-1-0 | F1-S1 | Up / Tier 1 |
| 2026.02.06 22:00 | 512-5-3 | 512-1-3 | 512-1-0 | 512-1-3 | 513-1-2 | 401-1-0 | F1-F | Up / Tier 1 |
| 2026.02.06 23:00 | 513-5-2 | 513-1-2 | 513-1-2 | 512-1-3 | 513-1-2 | 401-1-0 | F1-S3 | Up / Tier 1 |
| 2026.02.06 23:30 | 513-1-2 | 513-1-2 | 513-1-2 | 512-1-3 | 513-1-2 | 401-1-0 | F1-S3 | Up / Tier 1 |

**Coverage:** 2026.02.06 01:00 → 2026.02.06 23:30 | Period: 2026.02.06 01:00 → 2026.02.07 21:00 | **INCOMPLETE — period ends on non-trading day (2026.02.07)**

#### Image 2 Analysis — backtested_EA_sideway_2_fly_zoomin.jpg
![backtested_EA_sideway_2_fly_zoomin](./Backtest_data/extras/backtested_EA_sideway_2_fly_zoomin.jpg)

**Period:** 2026.02.06 13:00 → 2026.02.07 09:00 (chart x-axis: "06.02.2026" / "07.02.2026")

> **Cell = BBW_stage-diffMid-BBUpDn** (e.g. 511-1-1). BBW: 511/512=up-fly,
> 521/522=down-fly, 513/523=shrink, 4xx=SQZ. diffMid: 1=up, 2=down,
> 3=sideways, 5=deep-sideways. BBUpDn: 0=between, 1=upper, 2=lower,
> 3=sideways. A new row is added only when M15 BBW_stage or diffMid changes.
> All rows fall within the user-defined period.

| datetime | M15 | M30 | H1 | H4 | D1 | W1 | Scenario (HTF-MTF) | Trend / Tier |
|----------|-----|-----|----|----|----|----|--------------------|------------|
| 2026.02.06 13:00 | 411-4-2 | 403-1-2 | 403-1-1 | 513-1-2 | 513-1-2 | 401-1-0 | C4-C2 | Up / Tier 2 |
| 2026.02.06 13:15 | 521-4-0 | 403-1-2 | 403-1-1 | 513-1-2 | 513-1-2 | 401-1-0 | C4-B1 | Up / Tier 2 |
| 2026.02.06 13:30 | 511-1-1 | 403-1-2 | 403-1-1 | 513-1-2 | 513-1-2 | 401-1-0 | C4-B1 | Up / Tier 2 |
| 2026.02.06 14:00 | 512-1-3 | 403-1-0 | 403-1-1 | 513-1-2 | 513-1-2 | 401-1-0 | C4-B1 | Up / Tier 2 |
| 2026.02.06 15:30 | 511-1-1 | 512-1-3 | 511-1-1 | 513-1-2 | 513-1-2 | 401-1-0 | C4-F | Up / Tier 2 |
| 2026.02.06 16:15 | 512-1-3 | 512-1-3 | 511-1-1 | 513-1-0 | 513-1-2 | 401-1-0 | C4-F | Up / Tier 2 |
| 2026.02.06 19:45 | 513-1-2 | 512-1-3 | 511-1-1 | 513-1-0 | 513-1-2 | 401-1-0 | C4-S1 | Up / Tier 2 |
| 2026.02.06 20:00 | 512-1-3 | 512-1-3 | 511-1-0 | 512-1-3 | 513-1-2 | 401-1-0 | F1-F | Up / Tier 1 |
| 2026.02.06 21:30 | 513-1-2 | 512-1-3 | 512-1-3 | 512-1-3 | 513-1-2 | 401-1-0 | F1-S1 | Up / Tier 1 |
| 2026.02.06 22:00 | 512-5-3 | 512-1-3 | 512-1-0 | 512-1-3 | 513-1-2 | 401-1-0 | F1-F | Up / Tier 1 |
| 2026.02.06 23:00 | 513-5-2 | 513-1-2 | 513-1-2 | 512-1-3 | 513-1-2 | 401-1-0 | F1-S3 | Up / Tier 1 |
| 2026.02.06 23:30 | 513-1-2 | 513-1-2 | 513-1-2 | 512-1-3 | 513-1-2 | 401-1-0 | F1-S3 | Up / Tier 1 |

**Coverage:** 2026.02.06 13:00 → 2026.02.06 23:30 | Period: 2026.02.06 13:00 → 2026.02.07 09:00 | **INCOMPLETE — period ends on non-trading day (2026.02.07)**

#### Image 3 Analysis — backtest_EA_sideway_2_fly2_zoomin.jpg
![backtest_EA_sideway_2_fly2_zoomin](./Backtest_data/extras/backtest_EA_sideway_2_fly2_zoomin.jpg)

**Period:** 2026.02.06 13:00 → 2026.02.07 09:00 (chart x-axis: "06.02.2026" / "07.02.2026")

> **Cell = BBW_stage-diffMid-BBUpDn** (e.g. 511-1-1). BBW: 511/512=up-fly,
> 521/522=down-fly, 513/523=shrink, 4xx=SQZ. diffMid: 1=up, 2=down,
> 3=sideways, 5=deep-sideways. BBUpDn: 0=between, 1=upper, 2=lower,
> 3=sideways. A new row is added only when M15 BBW_stage or diffMid changes.
> All rows fall within the user-defined period.

| datetime | M15 | M30 | H1 | H4 | D1 | W1 | Scenario (HTF-MTF) | Trend / Tier |
|----------|-----|-----|----|----|----|----|--------------------|------------|
| 2026.02.06 13:00 | 411-4-2 | 403-1-2 | 403-1-1 | 513-1-2 | 513-1-2 | 401-1-0 | C4-C2 | Up / Tier 2 |
| 2026.02.06 13:15 | 521-4-0 | 403-1-2 | 403-1-1 | 513-1-2 | 513-1-2 | 401-1-0 | C4-B1 | Up / Tier 2 |
| 2026.02.06 13:30 | 511-1-1 | 403-1-2 | 403-1-1 | 513-1-2 | 513-1-2 | 401-1-0 | C4-B1 | Up / Tier 2 |
| 2026.02.06 14:00 | 512-1-3 | 403-1-0 | 403-1-1 | 513-1-2 | 513-1-2 | 401-1-0 | C4-B1 | Up / Tier 2 |
| 2026.02.06 15:30 | 511-1-1 | 512-1-3 | 511-1-1 | 513-1-2 | 513-1-2 | 401-1-0 | C4-F | Up / Tier 2 |
| 2026.02.06 16:15 | 512-1-3 | 512-1-3 | 511-1-1 | 513-1-0 | 513-1-2 | 401-1-0 | C4-F | Up / Tier 2 |
| 2026.02.06 19:45 | 513-1-2 | 512-1-3 | 511-1-1 | 513-1-0 | 513-1-2 | 401-1-0 | C4-S1 | Up / Tier 2 |
| 2026.02.06 20:00 | 512-1-3 | 512-1-3 | 511-1-0 | 512-1-3 | 513-1-2 | 401-1-0 | F1-F | Up / Tier 1 |
| 2026.02.06 21:30 | 513-1-2 | 512-1-3 | 512-1-3 | 512-1-3 | 513-1-2 | 401-1-0 | F1-S1 | Up / Tier 1 |
| 2026.02.06 22:00 | 512-5-3 | 512-1-3 | 512-1-0 | 512-1-3 | 513-1-2 | 401-1-0 | F1-F | Up / Tier 1 |
| 2026.02.06 23:00 | 513-5-2 | 513-1-2 | 513-1-2 | 512-1-3 | 513-1-2 | 401-1-0 | F1-S3 | Up / Tier 1 |
| 2026.02.06 23:30 | 513-1-2 | 513-1-2 | 513-1-2 | 512-1-3 | 513-1-2 | 401-1-0 | F1-S3 | Up / Tier 1 |

**Coverage:** 2026.02.06 13:00 → 2026.02.06 23:30 | Period: 2026.02.06 13:00 → 2026.02.07 09:00 | **INCOMPLETE — period ends on non-trading day (2026.02.07)**

---

## Scenario V (Direction Pivot)

#### Image 1 Analysis — backtested_EA_fly_shrink_2_sideway2.jpg
![backtested_EA_fly_shrink_2_sideway2](./Backtest_data/extras/backtested_EA_fly_shrink_2_sideway2.jpg)

**Period:** 2026.04.02 05:00 → 2026.04.03 03:00 (chart x-axis: "02.04.2026" / "03.04.2026")

> **Cell = BBW_stage-diffMid-BBUpDn** (e.g. 511-1-1). BBW: 511/512=up-fly,
> 521/522=down-fly, 513/523=shrink, 4xx=SQZ. diffMid: 1=up, 2=down,
> 3=sideways, 5=deep-sideways. BBUpDn: 0=between, 1=upper, 2=lower,
> 3=sideways. A new row is added only when M15 BBW_stage or diffMid changes.
> All rows fall within the user-defined period.

| datetime | M15 | M30 | H1 | H4 | D1 | W1 | Scenario (HTF-MTF) | Trend / Tier |
|----------|-----|-----|----|----|----|----|--------------------|------------|
| 2026.04.02 05:00 | 521-2-1 | 422-2-1 | 512-3-2 | 512-1-3 | 523-2-0 | 513-1-2 | F2-F [divergence] | Up (div) / Tier 1 |
| 2026.04.02 06:30 | 522-2-4 | 521-2-0 | 512-3-1 | 512-1-3 | 523-2-0 | 513-1-2 | F2-R1 [divergence] | Up (div) / Tier 1 |
| 2026.04.02 08:15 | 523-2-2 | 522-2-4 | 521-2-1 | 512-1-0 | 523-2-0 | 513-1-2 | F2-R1 [divergence] | Up (div) / Tier 1 |
| 2026.04.02 09:00 | 412-2-4 | 521-2-1 | 521-2-1 | 512-1-0 | 523-2-0 | 513-1-2 | F2-R1 [divergence] | Up (div) / Tier 1 |
| 2026.04.02 09:15 | 521-2-0 | 521-2-1 | 521-2-1 | 512-1-0 | 523-2-0 | 513-1-2 | F2-R1 [divergence] | Up (div) / Tier 1 |
| 2026.04.02 10:00 | 522-2-4 | 521-2-0 | 521-2-1 | 512-1-0 | 523-2-0 | 513-1-2 | F2-R1 [divergence] | Up (div) / Tier 1 |
| 2026.04.02 11:15 | 523-2-2 | 522-2-4 | 521-2-0 | 512-1-0 | 523-2-0 | 513-1-2 | F2-R1 [divergence] | Up (div) / Tier 1 |
| 2026.04.02 13:45 | 523-3-0 | 523-2-2 | 521-2-1 | 513-1-2 | 523-2-0 | 513-1-2 | C4-S2 [divergence] | Up (div) / Tier 2 |
| 2026.04.02 14:00 | 523-1-0 | 523-2-2 | 521-2-0 | 513-1-2 | 523-2-0 | 513-1-2 | C4-S2 [divergence] | Up (div) / Tier 2 |
| 2026.04.02 14:45 | 523-5-2 | 523-2-0 | 521-2-0 | 513-1-2 | 523-2-0 | 513-1-2 | C4-S2 [divergence] | Up (div) / Tier 2 |
| 2026.04.02 15:00 | 415-5-0 | 522-2-4 | 522-2-4 | 513-1-2 | 523-2-0 | 513-1-2 | C4-C1 [divergence] | Up (div) / Tier 2 |
| 2026.04.02 15:15 | 521-4-1 | 522-2-4 | 522-2-4 | 513-1-2 | 523-2-0 | 513-1-2 | C4-F [divergence] | Up (div) / Tier 2 |
| 2026.04.02 15:30 | 522-4-4 | 522-2-0 | 522-2-4 | 513-1-2 | 523-2-0 | 513-1-2 | C4-F [divergence] | Up (div) / Tier 2 |
| 2026.04.02 15:45 | 522-2-0 | 522-2-0 | 522-2-4 | 513-1-2 | 523-2-0 | 513-1-2 | C4-F [divergence] | Up (div) / Tier 2 |
| 2026.04.02 17:00 | 522-3-0 | 523-2-2 | 522-2-4 | 513-1-2 | 523-2-0 | 513-1-2 | C4-B1 [divergence] | Up (div) / Tier 2 |
| 2026.04.02 17:15 | 511-1-1 | 523-2-2 | 522-2-4 | 513-1-2 | 523-2-0 | 513-1-2 | C4-B1 [divergence] | Up (div) / Tier 2 |
| 2026.04.02 19:00 | 512-1-3 | 511-1-0 | 523-2-2 | 513-1-2 | 523-2-0 | 513-1-2 | C4-B2 [divergence] | Up (div) / Tier 2 |
| 2026.04.02 21:00 | 513-1-2 | 512-1-3 | 523-2-2 | 513-1-0 | 523-2-0 | 513-1-2 | C4-S1 [divergence] | Up (div) / Tier 2 |
| 2026.04.02 22:15 | 411-1-3 | 512-1-3 | 523-2-2 | 513-1-0 | 523-2-0 | 513-1-2 | C4-C1 [divergence] | Up (div) / Tier 2 |
| 2026.04.02 22:30 | 411-3-0 | 512-1-3 | 523-2-2 | 513-1-0 | 523-2-0 | 513-1-2 | C4-C1 [divergence] | Up (div) / Tier 2 |
| 2026.04.02 22:45 | 411-2-2 | 512-1-3 | 523-2-2 | 513-1-0 | 523-2-0 | 513-1-2 | C4-C1 [divergence] | Up (div) / Tier 2 |
| 2026.04.02 23:15 | 413-3-0 | 512-1-3 | 523-2-2 | 513-1-0 | 523-2-0 | 513-1-2 | C4-C1 [divergence] | Up (div) / Tier 2 |
| 2026.04.02 23:45 | 413-5-0 | 512-1-3 | 523-2-2 | 513-1-0 | 523-2-0 | 513-1-2 | C4-C1 [divergence] | Up (div) / Tier 2 |

**Coverage:** 2026.04.02 05:00 → 2026.04.02 23:45 | Period: 2026.04.02 05:00 → 2026.04.03 03:00 | **INCOMPLETE — period ends on non-trading day (2026.04.03)**

---

## Scenario C (Deep Compression)

#### Image 1 Analysis — backtested_EA_fly_shrink_2_sideway.jpg
![backtested_EA_fly_shrink_2_sideway](./Backtest_data/extras/backtested_EA_fly_shrink_2_sideway.jpg)

**Period:** 2026.04.01 13:00 → 2026.04.02 17:00 (chart x-axis: "01.04.2026" / "02.04.2026", log-confirmed)

> **Cell = BBW_stage-diffMid-BBUpDn** (e.g. 511-1-1). BBW: 511/512=up-fly,
> 521/522=down-fly, 513/523=shrink, 4xx=SQZ. diffMid: 1=up, 2=down,
> 3=sideways, 5=deep-sideways. BBUpDn: 0=between, 1=upper, 2=lower,
> 3=sideways. A new row is added only when M15 BBW_stage or diffMid changes.
> All rows fall within the user-defined period.

| datetime | M15 | M30 | H1 | H4 | D1 | W1 | Scenario (HTF-MTF) | Trend / Tier |
|----------|-----|-----|----|----|----|----|--------------------|------------|
| 2026.04.01 13:00 | 513-1-2 | 512-1-0 | 512-1-0 | 512-1-3 | 522-2-4 | 513-1-2 | F2-S1 | Up (div) / Tier 1 |
| 2026.04.01 14:30 | 512-1-3 | 511-1-1 | 512-1-0 | 512-1-3 | 522-2-4 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.04.01 14:45 | 511-1-1 | 511-1-1 | 512-1-0 | 512-1-3 | 522-2-4 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.04.01 15:15 | 512-1-3 | 511-1-0 | 512-1-3 | 512-1-3 | 522-2-4 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.04.01 15:30 | 512-3-3 | 512-1-3 | 512-1-3 | 512-1-3 | 522-2-4 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.04.01 16:15 | 512-5-0 | 512-1-3 | 513-1-2 | 512-1-3 | 522-2-4 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.04.01 17:15 | 512-1-3 | 512-1-0 | 513-1-0 | 512-1-3 | 522-2-4 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.04.01 18:45 | 511-1-1 | 411-1-3 | 411-1-3 | 512-1-3 | 522-2-4 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.04.01 20:30 | 512-1-3 | 512-1-0 | 511-1-0 | 512-1-3 | 522-2-4 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.04.01 21:15 | 513-1-2 | 512-1-3 | 512-1-3 | 512-1-3 | 522-2-4 | 513-1-2 | F2-S1 | Up (div) / Tier 1 |
| 2026.04.01 22:45 | 513-5-2 | 513-1-2 | 512-1-3 | 512-1-3 | 522-2-4 | 513-1-2 | F2-S2 | Up (div) / Tier 1 |
| 2026.04.01 23:00 | 513-3-0 | 513-1-0 | 512-1-3 | 512-1-3 | 522-2-4 | 513-1-2 | F2-S2 | Up (div) / Tier 1 |
| 2026.04.01 23:30 | 513-2-4 | 513-1-2 | 512-1-3 | 512-1-3 | 522-2-4 | 513-1-2 | F2-S2 [divergence] | Up (div) / Tier 1 |
| 2026.04.01 23:45 | 523-2-4 | 513-1-2 | 512-1-3 | 512-1-3 | 522-2-4 | 513-1-2 | F2-S2 [divergence] | Up (div) / Tier 1 |
| 2026.04.02 01:00 | 522-2-4 | 513-1-2 | 512-1-3 | 512-1-3 | 523-2-0 | 513-1-2 | F2-F [divergence] | Up (div) / Tier 1 |
| 2026.04.02 01:30 | 522-4-0 | 411-1-0 | 512-1-3 | 512-1-3 | 523-2-0 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.04.02 01:45 | 523-4-2 | 411-1-0 | 512-1-3 | 512-1-3 | 523-2-0 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.04.02 02:00 | 523-2-2 | 411-1-3 | 512-1-3 | 512-1-3 | 523-2-0 | 513-1-2 | F2-F [divergence] | Up (div) / Tier 1 |
| 2026.04.02 02:15 | 523-3-0 | 411-1-3 | 512-1-3 | 512-1-3 | 523-2-0 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.04.02 02:45 | 511-1-1 | 411-1-3 | 512-1-3 | 512-1-3 | 523-2-0 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.04.02 03:45 | 512-1-3 | 411-1-0 | 512-1-3 | 512-1-3 | 523-2-0 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.04.02 04:15 | 512-3-1 | 411-1-0 | 512-1-0 | 512-1-3 | 523-2-0 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.04.02 04:30 | 521-2-1 | 413-3-1 | 512-1-0 | 512-1-3 | 523-2-0 | 513-1-2 | F2-F [divergence] | Up (div) / Tier 1 |
| 2026.04.02 06:30 | 522-2-4 | 521-2-0 | 512-3-1 | 512-1-3 | 523-2-0 | 513-1-2 | F2-R1 [divergence] | Up (div) / Tier 1 |
| 2026.04.02 08:15 | 523-2-2 | 522-2-4 | 521-2-1 | 512-1-0 | 523-2-0 | 513-1-2 | F2-R1 [divergence] | Up (div) / Tier 1 |
| 2026.04.02 09:00 | 412-2-4 | 521-2-1 | 521-2-1 | 512-1-0 | 523-2-0 | 513-1-2 | F2-R1 [divergence] | Up (div) / Tier 1 |
| 2026.04.02 09:15 | 521-2-0 | 521-2-1 | 521-2-1 | 512-1-0 | 523-2-0 | 513-1-2 | F2-R1 [divergence] | Up (div) / Tier 1 |
| 2026.04.02 10:00 | 522-2-4 | 521-2-0 | 521-2-1 | 512-1-0 | 523-2-0 | 513-1-2 | F2-R1 [divergence] | Up (div) / Tier 1 |
| 2026.04.02 11:15 | 523-2-2 | 522-2-4 | 521-2-0 | 512-1-0 | 523-2-0 | 513-1-2 | F2-R1 [divergence] | Up (div) / Tier 1 |
| 2026.04.02 13:45 | 523-3-0 | 523-2-2 | 521-2-1 | 513-1-2 | 523-2-0 | 513-1-2 | C4-S2 [divergence] | Up (div) / Tier 2 |
| 2026.04.02 14:00 | 523-1-0 | 523-2-2 | 521-2-0 | 513-1-2 | 523-2-0 | 513-1-2 | C4-S2 [divergence] | Up (div) / Tier 2 |
| 2026.04.02 14:45 | 523-5-2 | 523-2-0 | 521-2-0 | 513-1-2 | 523-2-0 | 513-1-2 | C4-S2 [divergence] | Up (div) / Tier 2 |
| 2026.04.02 15:00 | 415-5-0 | 522-2-4 | 522-2-4 | 513-1-2 | 523-2-0 | 513-1-2 | C4-C1 [divergence] | Up (div) / Tier 2 |
| 2026.04.02 15:15 | 521-4-1 | 522-2-4 | 522-2-4 | 513-1-2 | 523-2-0 | 513-1-2 | C4-F [divergence] | Up (div) / Tier 2 |
| 2026.04.02 15:30 | 522-4-4 | 522-2-0 | 522-2-4 | 513-1-2 | 523-2-0 | 513-1-2 | C4-F [divergence] | Up (div) / Tier 2 |
| 2026.04.02 15:45 | 522-2-0 | 522-2-0 | 522-2-4 | 513-1-2 | 523-2-0 | 513-1-2 | C4-F [divergence] | Up (div) / Tier 2 |
| 2026.04.02 17:00 | 522-3-0 | 523-2-2 | 522-2-4 | 513-1-2 | 523-2-0 | 513-1-2 | C4-B1 [divergence] | Up (div) / Tier 2 |

**Coverage:** 2026.04.01 13:00 → 2026.04.02 17:00 | Period: 2026.04.01 13:00 → 2026.04.02 17:00 | **COMPLETE**

#### Image 2 Analysis — backtested_EA_fly_shrink_2_sideway_zoomin.jpg
![backtested_EA_fly_shrink_2_sideway_zoomin](./Backtest_data/extras/backtested_EA_fly_shrink_2_sideway_zoomin.jpg)

**Period:** 2026.04.02 09:00 → 2026.04.02 17:00 (chart x-axis: "02.04.2026")

> **Cell = BBW_stage-diffMid-BBUpDn** (e.g. 511-1-1). BBW: 511/512=up-fly,
> 521/522=down-fly, 513/523=shrink, 4xx=SQZ. diffMid: 1=up, 2=down,
> 3=sideways, 5=deep-sideways. BBUpDn: 0=between, 1=upper, 2=lower,
> 3=sideways. A new row is added only when M15 BBW_stage or diffMid changes.
> All rows fall within the user-defined period.

| datetime | M15 | M30 | H1 | H4 | D1 | W1 | Scenario (HTF-MTF) | Trend / Tier |
|----------|-----|-----|----|----|----|----|--------------------|------------|
| 2026.04.02 09:00 | 412-2-4 | 521-2-1 | 521-2-1 | 512-1-0 | 523-2-0 | 513-1-2 | F2-R1 [divergence] | Up (div) / Tier 1 |
| 2026.04.02 09:15 | 521-2-0 | 521-2-1 | 521-2-1 | 512-1-0 | 523-2-0 | 513-1-2 | F2-R1 [divergence] | Up (div) / Tier 1 |
| 2026.04.02 10:00 | 522-2-4 | 521-2-0 | 521-2-1 | 512-1-0 | 523-2-0 | 513-1-2 | F2-R1 [divergence] | Up (div) / Tier 1 |
| 2026.04.02 11:15 | 523-2-2 | 522-2-4 | 521-2-0 | 512-1-0 | 523-2-0 | 513-1-2 | F2-R1 [divergence] | Up (div) / Tier 1 |
| 2026.04.02 13:45 | 523-3-0 | 523-2-2 | 521-2-1 | 513-1-2 | 523-2-0 | 513-1-2 | C4-S2 [divergence] | Up (div) / Tier 2 |
| 2026.04.02 14:00 | 523-1-0 | 523-2-2 | 521-2-0 | 513-1-2 | 523-2-0 | 513-1-2 | C4-S2 [divergence] | Up (div) / Tier 2 |
| 2026.04.02 14:45 | 523-5-2 | 523-2-0 | 521-2-0 | 513-1-2 | 523-2-0 | 513-1-2 | C4-S2 [divergence] | Up (div) / Tier 2 |
| 2026.04.02 15:00 | 415-5-0 | 522-2-4 | 522-2-4 | 513-1-2 | 523-2-0 | 513-1-2 | C4-C1 [divergence] | Up (div) / Tier 2 |
| 2026.04.02 15:15 | 521-4-1 | 522-2-4 | 522-2-4 | 513-1-2 | 523-2-0 | 513-1-2 | C4-F [divergence] | Up (div) / Tier 2 |
| 2026.04.02 15:30 | 522-4-4 | 522-2-0 | 522-2-4 | 513-1-2 | 523-2-0 | 513-1-2 | C4-F [divergence] | Up (div) / Tier 2 |
| 2026.04.02 15:45 | 522-2-0 | 522-2-0 | 522-2-4 | 513-1-2 | 523-2-0 | 513-1-2 | C4-F [divergence] | Up (div) / Tier 2 |
| 2026.04.02 17:00 | 522-3-0 | 523-2-2 | 522-2-4 | 513-1-2 | 523-2-0 | 513-1-2 | C4-B1 [divergence] | Up (div) / Tier 2 |

**Coverage:** 2026.04.02 09:00 → 2026.04.02 17:00 | Period: 2026.04.02 09:00 → 2026.04.02 17:00 | **COMPLETE**

#### Image 3 Analysis — backtested_EA_phase_3a_symmetric.jpg
![backtested_EA_phase_3a_symmetric](./Backtest_data/extras/backtested_EA_phase_3a_symmetric.jpg)

**Period:** 2026.04.01 17:00 → 2026.04.02 05:00 (chart x-axis: "01.04.2026" / "02.04.2026", symmetric SQZ phase)

> **Cell = BBW_stage-diffMid-BBUpDn** (e.g. 511-1-1). BBW: 511/512=up-fly,
> 521/522=down-fly, 513/523=shrink, 4xx=SQZ. diffMid: 1=up, 2=down,
> 3=sideways, 5=deep-sideways. BBUpDn: 0=between, 1=upper, 2=lower,
> 3=sideways. A new row is added only when M15 BBW_stage or diffMid changes.
> All rows fall within the user-defined period.

| datetime | M15 | M30 | H1 | H4 | D1 | W1 | Scenario (HTF-MTF) | Trend / Tier |
|----------|-----|-----|----|----|----|----|--------------------|------------|
| 2026.04.01 17:00 | 512-5-0 | 512-1-0 | 513-1-0 | 512-1-3 | 522-2-4 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.04.01 17:15 | 512-1-3 | 512-1-0 | 513-1-0 | 512-1-3 | 522-2-4 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.04.01 18:45 | 511-1-1 | 411-1-3 | 411-1-3 | 512-1-3 | 522-2-4 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.04.01 20:30 | 512-1-3 | 512-1-0 | 511-1-0 | 512-1-3 | 522-2-4 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.04.01 21:15 | 513-1-2 | 512-1-3 | 512-1-3 | 512-1-3 | 522-2-4 | 513-1-2 | F2-S1 | Up (div) / Tier 1 |
| 2026.04.01 22:45 | 513-5-2 | 513-1-2 | 512-1-3 | 512-1-3 | 522-2-4 | 513-1-2 | F2-S2 | Up (div) / Tier 1 |
| 2026.04.01 23:00 | 513-3-0 | 513-1-0 | 512-1-3 | 512-1-3 | 522-2-4 | 513-1-2 | F2-S2 | Up (div) / Tier 1 |
| 2026.04.01 23:30 | 513-2-4 | 513-1-2 | 512-1-3 | 512-1-3 | 522-2-4 | 513-1-2 | F2-S2 [divergence] | Up (div) / Tier 1 |
| 2026.04.01 23:45 | 523-2-4 | 513-1-2 | 512-1-3 | 512-1-3 | 522-2-4 | 513-1-2 | F2-S2 [divergence] | Up (div) / Tier 1 |
| 2026.04.02 01:00 | 522-2-4 | 513-1-2 | 512-1-3 | 512-1-3 | 523-2-0 | 513-1-2 | F2-F [divergence] | Up (div) / Tier 1 |
| 2026.04.02 01:30 | 522-4-0 | 411-1-0 | 512-1-3 | 512-1-3 | 523-2-0 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.04.02 01:45 | 523-4-2 | 411-1-0 | 512-1-3 | 512-1-3 | 523-2-0 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.04.02 02:00 | 523-2-2 | 411-1-3 | 512-1-3 | 512-1-3 | 523-2-0 | 513-1-2 | F2-F [divergence] | Up (div) / Tier 1 |
| 2026.04.02 02:15 | 523-3-0 | 411-1-3 | 512-1-3 | 512-1-3 | 523-2-0 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.04.02 02:45 | 511-1-1 | 411-1-3 | 512-1-3 | 512-1-3 | 523-2-0 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.04.02 03:45 | 512-1-3 | 411-1-0 | 512-1-3 | 512-1-3 | 523-2-0 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.04.02 04:15 | 512-3-1 | 411-1-0 | 512-1-0 | 512-1-3 | 523-2-0 | 513-1-2 | F2-F | Up (div) / Tier 1 |
| 2026.04.02 04:30 | 521-2-1 | 413-3-1 | 512-1-0 | 512-1-3 | 523-2-0 | 513-1-2 | F2-F [divergence] | Up (div) / Tier 1 |

**Coverage:** 2026.04.01 17:00 → 2026.04.02 04:30 | Period: 2026.04.01 17:00 → 2026.04.02 05:00 | **COMPLETE**

#### Image 4 Analysis — backtested_EA_phase_3a_to_3b.jpg
![backtested_EA_phase_3a_to_3b](./Backtest_data/extras/backtested_EA_phase_3a_to_3b.jpg)

**Period:** 2026.04.02 05:00 → 2026.04.02 17:00 (chart x-axis: "02.04.2026", transition from symmetric to asymmetric SQZ)

> **Cell = BBW_stage-diffMid-BBUpDn** (e.g. 511-1-1). BBW: 511/512=up-fly,
> 521/522=down-fly, 513/523=shrink, 4xx=SQZ. diffMid: 1=up, 2=down,
> 3=sideways, 5=deep-sideways. BBUpDn: 0=between, 1=upper, 2=lower,
> 3=sideways. A new row is added only when M15 BBW_stage or diffMid changes.
> All rows fall within the user-defined period.

| datetime | M15 | M30 | H1 | H4 | D1 | W1 | Scenario (HTF-MTF) | Trend / Tier |
|----------|-----|-----|----|----|----|----|--------------------|------------|
| 2026.04.02 05:00 | 521-2-1 | 422-2-1 | 512-3-2 | 512-1-3 | 523-2-0 | 513-1-2 | F2-F [divergence] | Up (div) / Tier 1 |
| 2026.04.02 06:30 | 522-2-4 | 521-2-0 | 512-3-1 | 512-1-3 | 523-2-0 | 513-1-2 | F2-R1 [divergence] | Up (div) / Tier 1 |
| 2026.04.02 08:15 | 523-2-2 | 522-2-4 | 521-2-1 | 512-1-0 | 523-2-0 | 513-1-2 | F2-R1 [divergence] | Up (div) / Tier 1 |
| 2026.04.02 09:00 | 412-2-4 | 521-2-1 | 521-2-1 | 512-1-0 | 523-2-0 | 513-1-2 | F2-R1 [divergence] | Up (div) / Tier 1 |
| 2026.04.02 09:15 | 521-2-0 | 521-2-1 | 521-2-1 | 512-1-0 | 523-2-0 | 513-1-2 | F2-R1 [divergence] | Up (div) / Tier 1 |
| 2026.04.02 10:00 | 522-2-4 | 521-2-0 | 521-2-1 | 512-1-0 | 523-2-0 | 513-1-2 | F2-R1 [divergence] | Up (div) / Tier 1 |
| 2026.04.02 11:15 | 523-2-2 | 522-2-4 | 521-2-0 | 512-1-0 | 523-2-0 | 513-1-2 | F2-R1 [divergence] | Up (div) / Tier 1 |
| 2026.04.02 13:45 | 523-3-0 | 523-2-2 | 521-2-1 | 513-1-2 | 523-2-0 | 513-1-2 | C4-S2 [divergence] | Up (div) / Tier 2 |
| 2026.04.02 14:00 | 523-1-0 | 523-2-2 | 521-2-0 | 513-1-2 | 523-2-0 | 513-1-2 | C4-S2 [divergence] | Up (div) / Tier 2 |
| 2026.04.02 14:45 | 523-5-2 | 523-2-0 | 521-2-0 | 513-1-2 | 523-2-0 | 513-1-2 | C4-S2 [divergence] | Up (div) / Tier 2 |
| 2026.04.02 15:00 | 415-5-0 | 522-2-4 | 522-2-4 | 513-1-2 | 523-2-0 | 513-1-2 | C4-C1 [divergence] | Up (div) / Tier 2 |
| 2026.04.02 15:15 | 521-4-1 | 522-2-4 | 522-2-4 | 513-1-2 | 523-2-0 | 513-1-2 | C4-F [divergence] | Up (div) / Tier 2 |
| 2026.04.02 15:30 | 522-4-4 | 522-2-0 | 522-2-4 | 513-1-2 | 523-2-0 | 513-1-2 | C4-F [divergence] | Up (div) / Tier 2 |
| 2026.04.02 15:45 | 522-2-0 | 522-2-0 | 522-2-4 | 513-1-2 | 523-2-0 | 513-1-2 | C4-F [divergence] | Up (div) / Tier 2 |
| 2026.04.02 17:00 | 522-3-0 | 523-2-2 | 522-2-4 | 513-1-2 | 523-2-0 | 513-1-2 | C4-B1 [divergence] | Up (div) / Tier 2 |

**Coverage:** 2026.04.02 05:00 → 2026.04.02 17:00 | Period: 2026.04.02 05:00 → 2026.04.02 17:00 | **COMPLETE**

#### Image 5 Analysis — backtested_EA_phase_3b_asymmetric.jpg
![backtested_EA_phase_3b_asymmetric](./Backtest_data/extras/backtested_EA_phase_3b_asymmetric.jpg)

**Period:** 2026.04.02 10:00 → 2026.04.02 17:00 (chart x-axis: "02.04.2026", asymmetric SQZ — M5/M15 out, M30 still in)

> **Cell = BBW_stage-diffMid-BBUpDn** (e.g. 511-1-1). BBW: 511/512=up-fly,
> 521/522=down-fly, 513/523=shrink, 4xx=SQZ. diffMid: 1=up, 2=down,
> 3=sideways, 5=deep-sideways. BBUpDn: 0=between, 1=upper, 2=lower,
> 3=sideways. A new row is added only when M15 BBW_stage or diffMid changes.
> All rows fall within the user-defined period.

| datetime | M15 | M30 | H1 | H4 | D1 | W1 | Scenario (HTF-MTF) | Trend / Tier |
|----------|-----|-----|----|----|----|----|--------------------|------------|
| 2026.04.02 10:00 | 522-2-4 | 521-2-0 | 521-2-1 | 512-1-0 | 523-2-0 | 513-1-2 | F2-R1 [divergence] | Up (div) / Tier 1 |
| 2026.04.02 11:15 | 523-2-2 | 522-2-4 | 521-2-0 | 512-1-0 | 523-2-0 | 513-1-2 | F2-R1 [divergence] | Up (div) / Tier 1 |
| 2026.04.02 13:45 | 523-3-0 | 523-2-2 | 521-2-1 | 513-1-2 | 523-2-0 | 513-1-2 | C4-S2 [divergence] | Up (div) / Tier 2 |
| 2026.04.02 14:00 | 523-1-0 | 523-2-2 | 521-2-0 | 513-1-2 | 523-2-0 | 513-1-2 | C4-S2 [divergence] | Up (div) / Tier 2 |
| 2026.04.02 14:45 | 523-5-2 | 523-2-0 | 521-2-0 | 513-1-2 | 523-2-0 | 513-1-2 | C4-S2 [divergence] | Up (div) / Tier 2 |
| 2026.04.02 15:00 | 415-5-0 | 522-2-4 | 522-2-4 | 513-1-2 | 523-2-0 | 513-1-2 | C4-C1 [divergence] | Up (div) / Tier 2 |
| 2026.04.02 15:15 | 521-4-1 | 522-2-4 | 522-2-4 | 513-1-2 | 523-2-0 | 513-1-2 | C4-F [divergence] | Up (div) / Tier 2 |
| 2026.04.02 15:30 | 522-4-4 | 522-2-0 | 522-2-4 | 513-1-2 | 523-2-0 | 513-1-2 | C4-F [divergence] | Up (div) / Tier 2 |
| 2026.04.02 15:45 | 522-2-0 | 522-2-0 | 522-2-4 | 513-1-2 | 523-2-0 | 513-1-2 | C4-F [divergence] | Up (div) / Tier 2 |
| 2026.04.02 17:00 | 522-3-0 | 523-2-2 | 522-2-4 | 513-1-2 | 523-2-0 | 513-1-2 | C4-B1 [divergence] | Up (div) / Tier 2 |

**Coverage:** 2026.04.02 10:00 → 2026.04.02 17:00 | Period: 2026.04.02 10:00 → 2026.04.02 17:00 | **COMPLETE**

#### Image 6 Analysis — backtested_EA_phase_3b_out_recovery.jpg
![backtested_EA_phase_3b_out_recovery](./Backtest_data/extras/backtested_EA_phase_3b_out_recovery.jpg)

**Period:** 2026.04.02 17:00 → 2026.04.03 03:00 (chart x-axis: "02.04.2026" / "03.04.2026", recovery from asymmetric SQZ)

> **Cell = BBW_stage-diffMid-BBUpDn** (e.g. 511-1-1). BBW: 511/512=up-fly,
> 521/522=down-fly, 513/523=shrink, 4xx=SQZ. diffMid: 1=up, 2=down,
> 3=sideways, 5=deep-sideways. BBUpDn: 0=between, 1=upper, 2=lower,
> 3=sideways. A new row is added only when M15 BBW_stage or diffMid changes.
> All rows fall within the user-defined period.

| datetime | M15 | M30 | H1 | H4 | D1 | W1 | Scenario (HTF-MTF) | Trend / Tier |
|----------|-----|-----|----|----|----|----|--------------------|------------|
| 2026.04.02 17:00 | 522-3-0 | 523-2-2 | 522-2-4 | 513-1-2 | 523-2-0 | 513-1-2 | C4-B1 [divergence] | Up (div) / Tier 2 |
| 2026.04.02 17:15 | 511-1-1 | 523-2-2 | 522-2-4 | 513-1-2 | 523-2-0 | 513-1-2 | C4-B1 [divergence] | Up (div) / Tier 2 |
| 2026.04.02 19:00 | 512-1-3 | 511-1-0 | 523-2-2 | 513-1-2 | 523-2-0 | 513-1-2 | C4-B2 [divergence] | Up (div) / Tier 2 |
| 2026.04.02 21:00 | 513-1-2 | 512-1-3 | 523-2-2 | 513-1-0 | 523-2-0 | 513-1-2 | C4-S1 [divergence] | Up (div) / Tier 2 |
| 2026.04.02 22:15 | 411-1-3 | 512-1-3 | 523-2-2 | 513-1-0 | 523-2-0 | 513-1-2 | C4-C1 [divergence] | Up (div) / Tier 2 |
| 2026.04.02 22:30 | 411-3-0 | 512-1-3 | 523-2-2 | 513-1-0 | 523-2-0 | 513-1-2 | C4-C1 [divergence] | Up (div) / Tier 2 |
| 2026.04.02 22:45 | 411-2-2 | 512-1-3 | 523-2-2 | 513-1-0 | 523-2-0 | 513-1-2 | C4-C1 [divergence] | Up (div) / Tier 2 |
| 2026.04.02 23:15 | 413-3-0 | 512-1-3 | 523-2-2 | 513-1-0 | 523-2-0 | 513-1-2 | C4-C1 [divergence] | Up (div) / Tier 2 |
| 2026.04.02 23:45 | 413-5-0 | 512-1-3 | 523-2-2 | 513-1-0 | 523-2-0 | 513-1-2 | C4-C1 [divergence] | Up (div) / Tier 2 |

**Coverage:** 2026.04.02 17:00 → 2026.04.02 23:45 | Period: 2026.04.02 17:00 → 2026.04.03 03:00 | **INCOMPLETE — period ends on non-trading day (2026.04.03)**

#### Image 7 Analysis — backtested_EA_phase_6_post_sqz_oscillation.jpg
![backtested_EA_phase_6_post_sqz_oscillation](./Backtest_data/extras/backtested_EA_phase_6_post_sqz_oscillation.jpg)

**Period:** 2026.04.03 03:00 → 2026.04.03 17:00 (chart x-axis: "03.04.2026", post-SQZ oscillation)

  > **No log data available for this period.**

---

## Illustrative Images (do not fit a specific scenario)

#### backtested_EA_atrsl1buf.jpg
![backtested_EA_atrsl1buf](./Backtest_data/extras/backtested_EA_atrsl1buf.jpg)

**Illustrative:** ATR-based stop-loss / buffer visualization. Shows price action with ATR-derived levels. Does not map to a specific scenario — demonstrates the ATRSL1 buffer mechanism.

#### backtested-tofu-ea2.jpg
![backtested-tofu-ea2](./Backtest_data/extras/backtested-tofu-ea2.jpg)

**Illustrative:** EA performance chart — equity curve with trade markers. Shows overall EA results (green=profit trades, red=loss trades). Does not map to a specific BBW scenario.

#### backtested_chart.jpg
![backtested_chart](./Backtest_data/extras/backtested_chart.jpg)

**Illustrative:** General backtest overview chart. Multi-period view with trade markers and equity curve. Does not map to a single scenario — composite of multiple state transitions.

## Scenario Coverage

| Scenario | Sub-states | Present? | Image(s) | Missing sub-states |
|----------|-----------|----------|----------|--------------------|
| F (Fly) | F1, F2, F3 | Yes | F1, F2, F3 | — |
| S (Shrink) | S1, S2, S3 | Yes | S1, S2, S3 | — |
| C (Compress) | C1, C2, C3, C4 | Yes | C1, C2, C3, C4 | — |
| P (Pause) | P1, P2, P3 | No | — | P1, P2, P3 |
| B (Breakout) | B1, B2, B3 | Yes | B1, B2 | B3 |
| R (Reversal) | R1, R2, R3 | Yes | R1 | R2, R3 |
| V (Pivot) | V1, V2, V3, V4 | No | — | V1, V2, V3, V4 |

**Gap summary:** Missing sub-states with no chart example: P1, P2, P3, B3, R2, R3, V1, V2, V3, V4.
