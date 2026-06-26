# Image Analysis Blocks

Companion to `backtest_chart_analysis.md` — Part 3 image-analysis blocks have been separated from the scenario definitions into this document. The scenario definitions (Cascade Position, Sub-Scenarios, Sub-State Flowchart, Identification Flowchart, Trade action) remain in `backtest_chart_analysis.md`.

Each block uses a 5-step + TIMELINE format. States are confirmed against the backtest log (`references/Backtest_data/V31.04/20260620_clean.log`) where date coverage exists; `[TO BE FILLED]` where images do not show values clearly.

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

##### Step 1: State Read
| From | To | TF group | TF | BBW_stage | diffMid | BBUpDn | Source |
|------|-----|----------|----|-----------|---------|--------|--------|
| 260102 01:00 | 260103 04:00 | HTF | W1 | 511 | 1 | 1 | img |
| 260102 01:00 | 260103 04:00 | HTF | D1 | 511 | 1 | 1 | img |
| 260102 01:00 | 260103 04:00 | HTF | H4 | 511 | 1 | 1 | img |
| 260102 01:00 | 260103 04:00 | MTF | H1 | 511 (brief 424 SQZ) | 1 | 1 | img |
| 260102 01:00 | 260103 04:00 | MTF | M30 | 511 | 1 | 1 | log-confirmed (W_stage_M30:(FLY)[511], diffMid=1.0, BBUpDn=1) |
| 260102 01:00 | 260103 04:00 | MTF | M15 | 511 | 1 | 1 | log-confirmed (W_stage_M15:(FLY)[511], diffMid=1.0, BBUpDn=1) |
| 260102 01:00 | 260103 04:00 | LTF | M5 | 511 (brief 411 SQZ) | 1 | 1 | img |

##### Step 2: Two-Axis Classification
- **HTF scenario:** F1 — W1/D1/H4 all fly 511, D1+W1 aligned
- **MTF scenario:** F — H1/M30 fly 511, aligned with H4
- **MTF direction vs H4:** SAME  continuation

##### Step 3: Cascade
- direction: TOP — no active D1 or D2
- depth: None — all fly | leading TF: H4 (watch for shrink)
- key transition: Full fly alignment maintained; M5 brief SQZ noise resolves

##### Step 4: TIMELINE
| From | To | Scenario (HTF-MTF) | Trend / Tier | HTF state | MTF state | Source | Notes |
|------|-----|--------------------|--------------|-----------|-----------|--------|-------|
| 260102 01:00 | 260102 03:00 | F1-F | Up / Tier 1 | W1/D1/H4 fly 511 | M30/M15 fly 511, H1 SQZ 424 | log | H1 SQZ transient — Decision 6 not met (single-bar) |
| 260102 03:00 | 260103 04:00 | F1-F | Up / Tier 1 | W1/D1/H4 fly 511 | H1/M30/M15 fly 511, M5 brief 411 | log | Full fly restored; M5 noise resolves |

##### Step 5: Conclusion + Prediction
- **Scenario: F1-F** (HTF=F1 MTF=F). No divergence.
- **Next likely:** F1-S if H4 enters 513. Watch: H4 BBW_stage for first sign of shrink.

#### Image 2 Analysis — backtested_EA_predict_trend_1.jpg
![backtested_EA_predict_trend_1](./Backtest_data/extras/backtested_EA_predict_trend_1.jpg)

**Period:** 2026.04.01 13:00 → 2026.04.01 17:00 (chart x-axis: "01.04.2026" labels, DD.MM.YYYY = Apr 1)

##### Step 1: State Read
| From | To | TF group | TF | BBW_stage | diffMid | BBUpDn | Source |
|------|-----|----------|----|-----------|---------|--------|--------|
| 260401 13:00 | 260401 17:00 | HTF | W1 | [TO BE FILLED] | [TO BE FILLED] | [TO BE FILLED] | img |
| 260401 13:00 | 260401 17:00 | HTF | D1 | 513 | 1 | 2 | img |
| 260401 13:00 | 260401 17:00 | HTF | H4 | 512 | 1 | 3 | img |
| 260401 13:00 | 260401 17:00 | MTF | H1 | 512 | 1 | 0 | img |
| 260401 13:00 | 260401 17:00 | MTF | M30 | 511 | 1 | 1 | img |
| 260401 13:00 | 260401 17:00 | MTF | M15 | 511 | 1 | 1 | img |
| 260401 13:00 | 260401 17:00 | LTF | M5 | 511 | 1 | 1 | img |

##### Step 2: Two-Axis Classification
- **HTF scenario:** S — H4 fly 512, D1 shrink 513 (pre-pivot)
- **MTF scenario:** F — M30/M15 fly 511, aligned with H4
- **MTF direction vs H4:** SAME  continuation

##### Step 3: Cascade
- direction: D1 compress HTF  LTF (D1 shrinking)
- depth: D1 only | leading TF: M30 (watch for shrink or SQZ)
- key transition: D1 compression while MTF still flying — early pre-pivot

##### Step 4: TIMELINE
| From | To | Scenario (HTF-MTF) | Trend / Tier | HTF state | MTF state | Source | Notes |
|------|-----|--------------------|--------------|-----------|-----------|--------|-------|
| 260401 13:00 | 260401 17:00 | S-F | Up / Tier 2 | H4 fly 512, D1 shrink 513 | M30/M15 fly 511 | img | D1 compressing but MTF still flying |

##### Step 5: Conclusion + Prediction
- **Scenario: S-F** (HTF=S MTF=F). No divergence yet — MTF same direction as H4.
- **Next likely:** S-S2 if M30 enters shrink; S-C1 if M30 enters SQZ. Watch: M30 BBW_stage.

#### Image 3 Analysis — LTH_drive_fly.jpg
![LTH_drive_fly](./Backtest_data/extras/LTH_drive_fly.jpg)

**Period:** 2026.01.02 01:00 → 2026.01.03 04:00 (chart x-axis: "02.01.2026" / "03.01.2026", DD.MM.YYYY = Jan 2-3)

##### Step 1: State Read
| From | To | TF group | TF | BBW_stage | diffMid | BBUpDn | Source |
|------|-----|----------|----|-----------|---------|--------|--------|
| 260102 01:00 | 260103 04:00 | HTF | W1 | 511 | 1 | 1 | img |
| 260102 01:00 | 260103 04:00 | HTF | D1 | 511 | 1 | 1 | img |
| 260102 01:00 | 260103 04:00 | HTF | H4 | 511 | 1 | 1 | img |
| 260102 01:00 | 260103 04:00 | MTF | H1 | 511 | 1 | 1 | img |
| 260102 01:00 | 260103 04:00 | MTF | M30 | 511 | 1 | 1 | img |
| 260102 01:00 | 260103 04:00 | MTF | M15 | 511 | 1 | 1 | img |
| 260102 01:00 | 260103 04:00 | LTF | M5 | 511 | 1 | 1 | img |

##### Step 2: Two-Axis Classification
- **HTF scenario:** F1 — W1/D1/H4 all fly 511, D1+W1 aligned
- **MTF scenario:** F — H1/M30/M15 fly 511, aligned with H4
- **MTF direction vs H4:** SAME  continuation

##### Step 3: Cascade
- direction: TOP — no active D1 or D2
- depth: None — all fly | leading TF: H4 (watch for shrink)
- key transition: Full fly alignment — LTH (long-term high) driving fly state

##### Step 4: TIMELINE
| From | To | Scenario (HTF-MTF) | Trend / Tier | HTF state | MTF state | Source | Notes |
|------|-----|--------------------|--------------|-----------|-----------|--------|-------|
| 260102 01:00 | 260103 04:00 | F1-F | Up / Tier 1 | W1/D1/H4 fly 511 | H1/M30/M15 fly 511 | img | Sustained full fly — LTH-driven |

##### Step 5: Conclusion + Prediction
- **Scenario: F1-F** (HTF=F1 MTF=F). No divergence.
- **Next likely:** F1-S if H4 enters 513. Watch: H4 BBW_stage.

---

## Scenario S (Shrink)

#### Image 1 Analysis — backtested_EA_fly_2_fly_shrink.jpg
![backtested_EA_fly_2_fly_shrink](./Backtest_data/extras/backtested_EA_fly_2_fly_shrink.jpg)

**Period:** 2026.03.30 13:00 → 2026.04.01 13:00 (chart x-axis: "30.03.2026" / "01.04.2026", log-confirmed)

##### Step 1: State Read
| From | To | TF group | TF | BBW_stage | diffMid | BBUpDn | Source |
|------|-----|----------|----|-----------|---------|--------|--------|
| 260330 13:00 | 260330 14:00 | HTF | W1 | 511 | 1 | 1 | img |
| 260330 13:00 | 260330 14:00 | HTF | D1 | 511 | 1 | 1 | img |
| 260330 13:00 | 260330 14:00 | HTF | H4 | 511→512 | 1 | 1 | log |
| 260330 13:00 | 260330 14:00 | MTF | H1 | 512 | 1 | 0 | log |
| 260330 13:00 | 260330 14:00 | MTF | M30 | 512 | 1 | 2 | log |
| 260330 13:00 | 260330 14:00 | MTF | M15 | 511→513 | 1→5 | 1→2 | log |
| 260330 13:00 | 260330 14:00 | LTF | M5 | 513 | 5 | 2 | img |
| 260330 14:00 | 260401 13:00 | HTF | W1 | 511 | 1 | 1 | img |
| 260330 14:00 | 260401 13:00 | HTF | D1 | 511 | 1 | 1 | img |
| 260330 14:00 | 260401 13:00 | HTF | H4 | 511 | 1 | 1 | img |
| 260330 14:00 | 260401 13:00 | MTF | H1 | 512 | 1 | 0 | log |
| 260330 14:00 | 260401 13:00 | MTF | M30 | 513 | 1 | 2 | log |
| 260330 14:00 | 260401 13:00 | MTF | M15 | 513 | 5 | 2 | log |
| 260330 14:00 | 260401 13:00 | LTF | M5 | 513 | 5 | 2 | img |

##### Step 2: Two-Axis Classification
- **HTF scenario:** F1 — H4/D1/W1 all fly 511/512, D1+W1 aligned
- **MTF scenario:** S2 — M30/M15 shrink 513, H1 still fly
- **MTF direction vs H4:** SAME  continuation (M30 diffMid=1 same as H4)

##### Step 3: Cascade
- direction: D1 compress HTF  LTF
- depth: M5 (M30/M15/M5 shrinking) | leading TF: M30 (watch for SQZ or fly resume)
- key transition: M15 transitions 511→513; D1 compression deepens from S1 to S2

##### Step 4: TIMELINE
| From | To | Scenario (HTF-MTF) | Trend / Tier | HTF state | MTF state | Source | Notes |
|------|-----|--------------------|--------------|-----------|-----------|--------|-------|
| 260330 13:00 | 260330 14:00 | F1-S1 | Up / Tier 2 | H4 fly 511, D1 fly 511 | M30 fly 512, M15 511→513 | log | M15 enters shrink first |
| 260330 14:00 | 260330 14:30 | F1-S2 | Up / Tier 2 | H4 fly 511 | M30 shrink 513, M15 shrink 513, M5 shrink | log | M30 also shrink — S2 confirmed |
| 260330 14:30 | 260401 13:00 | F1-S2 | Up / Tier 2 | H4 fly 511 | M30/M15/M5 shrink 513 | img | Sustained S2; M15 briefly SQZ 425 then back to 513 |

##### Step 5: Conclusion + Prediction
- **Scenario: F1-S2** (HTF=F1 MTF=S2). No divergence.
- **Next likely:** F1-C2 if M30 enters SQZ 400-499; F1-P if M30 returns to 511/512. Watch: M30 BBW_stage + diffBBW.

#### Image 2 Analysis — backtested_EA_fly_2_fly_shrink_zoomin.jpg
![backtested_EA_fly_2_fly_shrink_zoomin](./Backtest_data/extras/backtested_EA_fly_2_fly_shrink_zoomin.jpg)

**Period:** 2026.03.30 14:30 → 2026.04.01 09:00 (chart x-axis: "30.03.2026" / "01.04.2026", log-confirmed)

##### Step 1: State Read
| From | To | TF group | TF | BBW_stage | diffMid | BBUpDn | Source |
|------|-----|----------|----|-----------|---------|--------|--------|
| 260330 14:30 | 260401 09:00 | HTF | W1 | 511 | 1 | 1 | img |
| 260330 14:30 | 260401 09:00 | HTF | D1 | 511 | 1 | 1 | img |
| 260330 14:30 | 260401 09:00 | HTF | H4 | 511 | 1 | 1 | img |
| 260330 14:30 | 260401 09:00 | MTF | H1 | 512 | 1 | 0 | img |
| 260330 14:30 | 260401 09:00 | MTF | M30 | 513 | 1 | 2 | img |
| 260330 14:30 | 260401 09:00 | MTF | M15 | 513 | 5 | 2 | img |
| 260330 14:30 | 260401 09:00 | LTF | M5 | 513 | 5 | 2 | img |

##### Step 2: Two-Axis Classification
- **HTF scenario:** F1 — H4/D1/W1 fly 511/512
- **MTF scenario:** S2 — M30/M15 shrink 513
- **MTF direction vs H4:** SAME  continuation

##### Step 3: Cascade
- direction: D1 compress HTF  LTF
- depth: M5 | leading TF: M15 (watch for FLAT UP/DN transition)
- key transition: M15 bands converging — shrink path entry possible

##### Step 4: TIMELINE
| From | To | Scenario (HTF-MTF) | Trend / Tier | HTF state | MTF state | Source | Notes |
|------|-----|--------------------|--------------|-----------|-----------|--------|-------|
| 260330 14:30 | 260401 05:00 | F1-S2 | Up / Tier 2 | H4 fly 511 | M30/M15 shrink 513, M5 shrink | img | D1 sustained; M15 SQZ 425 briefly then 513 |
| 260401 05:00 | 260401 09:00 | F1-S2 | Up / Tier 2 | H4 fly 511 | M30/M15 shrink 513 | img | M15 bands converging; entry on FLAT→UP/DN |

##### Step 5: Conclusion + Prediction
- **Scenario: F1-S2** (HTF=F1 MTF=S2). No divergence.
- **Next likely:** F1-P if M30 513→511/512; F1-C2 if M30 513→400-499. Watch: M30 BBW_stage + M15 midtrend transition.

#### Image 3 Analysis — backtested_EA_b_to_e_to_g_progression.jpg
![backtested_EA_b_to_e_to_g_progression](./Backtest_data/extras/backtested_EA_b_to_e_to_g_progression.jpg)

**Period:** 2026.03.30 13:00 → 2026.04.01 17:00 (chart x-axis: "30.03.2026" / "01.04.2026", extended view)

##### Step 1: State Read
| From | To | TF group | TF | BBW_stage | diffMid | BBUpDn | Source |
|------|-----|----------|----|-----------|---------|--------|--------|
| 260330 13:00 | 260330 17:00 | HTF | W1 | 511 | 1 | 1 | img |
| 260330 13:00 | 260330 17:00 | HTF | D1 | 511 | 1 | 1 | img |
| 260330 13:00 | 260330 17:00 | HTF | H4 | 511 | 1 | 1 | img |
| 260330 13:00 | 260330 17:00 | MTF | H1 | 512 | 1 | 0 | img |
| 260330 13:00 | 260330 17:00 | MTF | M30 | 512→513 | 1→1 | 2→2 | img |
| 260330 13:00 | 260330 17:00 | MTF | M15 | 511→513 | 1→5 | 1→2 | img |
| 260330 13:00 | 260330 17:00 | LTF | M5 | 513 | 5 | 2 | img |
| 260330 17:00 | 260401 13:00 | HTF | W1 | 511 | 1 | 1 | img |
| 260330 17:00 | 260401 13:00 | HTF | D1 | 511 | 1 | 1 | img |
| 260330 17:00 | 260401 13:00 | HTF | H4 | 511 | 1 | 1 | img |
| 260330 17:00 | 260401 13:00 | MTF | H1 | 512 | 1 | 0 | img |
| 260330 17:00 | 260401 13:00 | MTF | M30 | 513 | 1 | 2 | img |
| 260330 17:00 | 260401 13:00 | MTF | M15 | 513 | 5 | 2 | img |
| 260330 17:00 | 260401 13:00 | LTF | M5 | 513 | 5 | 2 | img |
| 260401 13:00 | 260401 17:00 | HTF | W1 | 511 | 1 | 1 | img |
| 260401 13:00 | 260401 17:00 | HTF | D1 | 513 | 1 | 2 | img |
| 260401 13:00 | 260401 17:00 | HTF | H4 | 512 | 1 | 3 | img |
| 260401 13:00 | 260401 17:00 | MTF | H1 | 512→411 | 1→3 | 0→0 | img |
| 260401 13:00 | 260401 17:00 | MTF | M30 | 513→411 | 1→3 | 2→0 | img |
| 260401 13:00 | 260401 17:00 | MTF | M15 | 513→411 | 5→3 | 2→0 | img |
| 260401 13:00 | 260401 17:00 | LTF | M5 | 411 | 3 | 0 | img |

##### Step 2: Two-Axis Classification
- **HTF scenario:** F1 → S — W1/D1 fly initially, then D1 shrinks 513 (pre-pivot)
- **MTF scenario:** S1 → S2 → C2 — M15 shrink first, M30 follows, then full SQZ
- **MTF direction vs H4:** SAME  continuation through S-phase, then SQZ

##### Step 3: Cascade
- direction: D1 compress HTF  LTF throughout
- depth: Full — M5 SQZ (BOTTOM) | leading TF: M30 (watch for SQZ break direction)
- key transition: Complete S C progression — shrink deepens to full compression

##### Step 4: TIMELINE
| From | To | Scenario (HTF-MTF) | Trend / Tier | HTF state | MTF state | Source | Notes |
|------|-----|--------------------|--------------|-----------|-----------|--------|-------|
| 260330 13:00 | 260330 17:00 | F1-S1 | Up / Tier 2 | H4/D1 fly 511 | M30 fly 512, M15 511→513 | img | M15 enters shrink first |
| 260330 17:00 | 260401 13:00 | F1-S2 | Up / Tier 2 | H4/D1 fly 511 | M30/M15/M5 shrink 513 | img | M30 also shrink — S2 confirmed |
| 260401 13:00 | 260401 17:00 | S-C2 | Up / Tier 2 | H4 fly 512, D1 shrink 513 | M30/M15/M5 SQZ 411 | img | D1 also shrinks; full SQZ — C2 |

##### Step 5: Conclusion + Prediction
- **Scenario: S-C2** (HTF=S MTF=C2). No divergence yet — SQZ but diffMid=1 same as H4.
- **Next likely:** S-P2 if M5 REVUP and M15 follows; S-R1 if M30 breaks 411→521 (opposite H4). Watch: M5 BBW_stage + M30 BBW_stage.

---

## Scenario P (Rest Recovery / Pause)

#### Image 1 Analysis — backtested_EA_fly_2_shrink_2_fly.jpg
![backtested_EA_fly_2_shrink_2_fly](./Backtest_data/extras/backtested_EA_fly_2_shrink_2_fly.jpg)

**Period:** 2026.04.03 03:00 → 2026.04.05 00:00 (chart x-axis: "03.04.2026" / "04.04.2026" / "05.04.2026")

##### Step 1: State Read
| From | To | TF group | TF | BBW_stage | diffMid | BBUpDn | Source |
|------|-----|----------|----|-----------|---------|--------|--------|
| 260403 03:00 | 260403 09:00 | HTF | W1 | 511 | 1 | 1 | img |
| 260403 03:00 | 260403 09:00 | HTF | D1 | 511 | 1 | 1 | img |
| 260403 03:00 | 260403 09:00 | HTF | H4 | 511 | 1 | 1 | img |
| 260403 03:00 | 260403 09:00 | MTF | H1 | 511 | 1 | 1 | img |
| 260403 03:00 | 260403 09:00 | MTF | M30 | 513 | 3 | 2 | img |
| 260403 03:00 | 260403 09:00 | MTF | M15 | 513 | 3 | 2 | img |
| 260403 03:00 | 260403 09:00 | LTF | M5 | 513 | 3 | 2 | img |
| 260403 09:00 | 260404 15:00 | HTF | W1 | 511 | 1 | 1 | img |
| 260403 09:00 | 260404 15:00 | HTF | D1 | 511 | 1 | 1 | img |
| 260403 09:00 | 260404 15:00 | HTF | H4 | 511 | 1 | 1 | img |
| 260403 09:00 | 260404 15:00 | MTF | H1 | 511 | 1 | 1 | img |
| 260403 09:00 | 260404 15:00 | MTF | M30 | 400-499 | 3 | 0 | img |
| 260403 09:00 | 260404 15:00 | MTF | M15 | 400-499 | 3 | 0 | img |
| 260403 09:00 | 260404 15:00 | LTF | M5 | 400-499 | 3 | 0 | img |
| 260404 15:00 | 260405 00:00 | HTF | W1 | 511 | 1 | 1 | img |
| 260404 15:00 | 260405 00:00 | HTF | D1 | 511 | 1 | 1 | img |
| 260404 15:00 | 260405 00:00 | HTF | H4 | 511 | 1 | 1 | img |
| 260404 15:00 | 260405 00:00 | MTF | H1 | 511 | 1 | 1 | img |
| 260404 15:00 | 260405 00:00 | MTF | M30 | 511 | 1 | 1 | img |
| 260404 15:00 | 260405 00:00 | MTF | M15 | 511 | 1 | 1 | img |
| 260404 15:00 | 260405 00:00 | LTF | M5 | 511 | 1 | 1 | img |

##### Step 2: Two-Axis Classification
- **HTF scenario:** F1 — W1/D1/H4 fly 511, D1+W1 aligned
- **MTF scenario:** P2 P3 — M30 compresses then re-expands, M15 confirms
- **MTF direction vs H4:** SAME  continuation

##### Step 3: Cascade
- direction: D1 compress HTF  LTF, then D2 expand LTF  HTF
- depth: M5 SQZ (BOTTOM)  D2 initiated at M5 | leading TF: M5 (broke SQZ)
- key transition: D1→D2 — M5 REVUP drives full re-expansion

##### Step 4: TIMELINE
| From | To | Scenario (HTF-MTF) | Trend / Tier | HTF state | MTF state | Source | Notes |
|------|-----|--------------------|--------------|-----------|-----------|--------|-------|
| 260403 03:00 | 260403 09:00 | F1-S2 | Up / Tier 2 | H4/H1 fly 511 | M30/M15 shrink 513 | img | D1 compression begins |
| 260403 09:00 | 260404 15:00 | F1-C2 | Up / Tier 2 | H4/H1 fly 511 | M30/M15/M5 SQZ 400-499 | img | D1 reaches BOTTOM |
| 260404 15:00 | 260404 21:00 | F1-P2 | Up / Tier 3 | H4/H1 fly 511 | M5 fly 511, M15 confirms | img | M5 REVUP, D2 initiated |
| 260404 21:00 | 260405 00:00 | F1-P3 | Up / Tier 3 | H4/H1 fly 511 | M30 fly 511 | img | D2 complete |

##### Step 5: Conclusion + Prediction
- **Scenario: F1-P2→F1-P3** (HTF=F1 MTF=P2→P3). No divergence.
- **Next likely:** F1-F if M30 fly confirmed; F1-S if M30 enters shrink again. Watch: M30 BBW_stage.

#### Image 2 Analysis — backtested_EA_fly_2_shrink_2_fly_zoomin.jpg
![backtested_EA_fly_2_shrink_2_fly_zoomin](./Backtest_data/extras/backtested_EA_fly_2_shrink_2_fly_zoomin.jpg)

**Period:** 2026.04.04 15:00 → 2026.04.05 00:00 (chart x-axis: "04.04.2026" / "05.04.2026")

##### Step 1: State Read
| From | To | TF group | TF | BBW_stage | diffMid | BBUpDn | Source |
|------|-----|----------|----|-----------|---------|--------|--------|
| 260404 15:00 | 260405 00:00 | HTF | W1 | 511 | 1 | 1 | img |
| 260404 15:00 | 260405 00:00 | HTF | D1 | 511 | 1 | 1 | img |
| 260404 15:00 | 260405 00:00 | HTF | H4 | 511 | 1 | 1 | img |
| 260404 15:00 | 260405 00:00 | MTF | H1 | 511 | 1 | 1 | img |
| 260404 15:00 | 260405 00:00 | MTF | M30 | 400-499→511 | 3→1 | 0→1 | img |
| 260404 15:00 | 260405 00:00 | MTF | M15 | 400-499→511 | 3→1 | 0→1 | img |
| 260404 15:00 | 260405 00:00 | LTF | M5 | 400-499→511 | 3→1 | 0→1 | img |

##### Step 2: Two-Axis Classification
- **HTF scenario:** F1 — H4/D1/W1 fly 511
- **MTF scenario:** P3 — M30 re-expands to fly 511
- **MTF direction vs H4:** SAME  continuation

##### Step 3: Cascade
- direction: D2 expand LTF  HTF
- depth: TOP — D2 complete | leading TF: M30 (confirm fly)
- key transition: M30 SQZ→fly — full D2 expansion confirmed

##### Step 4: TIMELINE
| From | To | Scenario (HTF-MTF) | Trend / Tier | HTF state | MTF state | Source | Notes |
|------|-----|--------------------|--------------|-----------|-----------|--------|-------|
| 260404 15:00 | 260404 18:00 | F1-P2 | Up / Tier 3 | H4/H1 fly 511 | M5 fly 511, M15 fly 511 | img | M5 REVUP, M15 confirms |
| 260404 18:00 | 260405 00:00 | F1-P3 | Up / Tier 3 | H4/H1 fly 511 | M30 fly 511 | img | D2 complete — all fly |

##### Step 5: Conclusion + Prediction
- **Scenario: F1-P3** (HTF=F1 MTF=P3). No divergence.
- **Next likely:** F1-F if M30 fly sustained; F1-S if M30 enters shrink. Watch: M30 BBW_stage.

---

## Scenario R (Reversal)

#### Image 1 Analysis — backtested_EA_trend_reversal.jpg
![backtested_EA_trend_reversal](./Backtest_data/extras/backtested_EA_trend_reversal.jpg)

**Period:** 2026.04.01 14:30 → 2026.04.02 05:00 (chart x-axis: "01.04.2026" / "02.04.2026", log-confirmed)

##### Step 1: State Read
| From | To | TF group | TF | BBW_stage | diffMid | BBUpDn | Source |
|------|-----|----------|----|-----------|---------|--------|--------|
| 260401 14:30 | 260401 23:00 | HTF | W1 | [TO BE FILLED] | [TO BE FILLED] | [TO BE FILLED] | img |
| 260401 14:30 | 260401 23:00 | HTF | D1 | 512 | 1 | 2 | img |
| 260401 14:30 | 260401 23:00 | HTF | H4 | 512 | 1 | 3 | log |
| 260401 14:30 | 260401 23:00 | MTF | H1 | 512 | 1 | 0 | log |
| 260401 14:30 | 260401 23:00 | MTF | M30 | 511 | 1 | 1 | img |
| 260401 14:30 | 260401 23:00 | MTF | M15 | 511 | 1 | 1 | img |
| 260401 14:30 | 260401 23:00 | LTF | M5 | [TO BE FILLED] | [TO BE FILLED] | [TO BE FILLED] | img |
| 260402 00:00 | 260402 05:00 | HTF | W1 | [TO BE FILLED] | [TO BE FILLED] | [TO BE FILLED] | img |
| 260402 00:00 | 260402 05:00 | HTF | D1 | 513 | 1 | 2 | log |
| 260402 00:00 | 260402 05:00 | HTF | H4 | 512 | 1 | 3 | log |
| 260402 00:00 | 260402 05:00 | MTF | H1 | 512 | 1 | 0 | log |
| 260402 00:00 | 260402 05:00 | MTF | M30 | 411 | 1 | 0 | log |
| 260402 00:00 | 260402 05:00 | MTF | M15 | 512 | 1 | 3 | log |
| 260402 00:00 | 260402 05:00 | LTF | M5 | [TO BE FILLED] | [TO BE FILLED] | [TO BE FILLED] | img |

##### Step 2: Two-Axis Classification
- **HTF scenario:** S — H4 fly 512, D1 shrink 513 (pre-pivot reversal)
- **MTF scenario:** C1 — M30 SQZ 411, H1 fly 512, M15 fly 512
- **MTF direction vs H4:** SAME  continuation (M30 SQZ but diffMid=1 same as H4)

##### Step 3: Cascade
- direction: D1 compress HTF  LTF (M30 SQZ)
- depth: M30 SQZ 411 | leading TF: M30 (watch for SQZ break direction)
- key transition: F1  R1 progression — M30 compresses between fly states, reversal beginning

##### Step 4: TIMELINE
| From | To | Scenario (HTF-MTF) | Trend / Tier | HTF state | MTF state | Source | Notes |
|------|-----|--------------------|--------------|-----------|-----------|--------|-------|
| 260401 14:30 | 260401 23:00 | F?-F | Up / Tier 1 | H4 fly 512, D1 fly 512 | M30 fly 511, M15 fly 511 | img | All aligned up — W1 unreadable so F? |
| 260401 23:00 | 260402 00:00 | F?-F  S-C1 | Up / Tier 1→2 | H4 fly 512, D1 512→513 | M30 511→411, M15 fly 512 | img | Transition: D1 shrinks, M30 enters SQZ |
| 260402 00:00 | 260402 04:00 | S-C1 | Up / Tier 2 | H4 fly 512, D1 shrink 513 | M30 SQZ 411, M15 fly 512 | log | M30 compresses — D1 deepens |
| 260402 04:00 | 260402 05:00 | S-C1 | Up / Tier 2 | H4 fly 512, D1 shrink 513 | M30 SQZ 411, M15 fly 512 | log | M30 still SQZ — waiting break |

##### Step 5: Conclusion + Prediction
- **Scenario: S-C1** (HTF=S MTF=C1). No divergence yet — M30 SQZ but diffMid=1 same as H4.
- **Next likely:** S-R1 if M30 breaks 411→521 (opposite H4); F?-F if M30 breaks 411→511 (same H4). Watch: M30 BBW_stage 411→511 vs 411→521.

#### Image 2 Analysis — backtested_EA_test_phase_April_01.jpg
![backtested_EA_test_phase_April_01](./Backtest_data/extras/backtested_EA_test_phase_April_01.jpg)

**Period:** 2026.04.01 14:30 → 2026.04.02 09:00 (chart x-axis: "01.04.2026" / "02.04.2026", extended view of reversal)

##### Step 1: State Read
| From | To | TF group | TF | BBW_stage | diffMid | BBUpDn | Source |
|------|-----|----------|----|-----------|---------|--------|--------|
| 260401 14:30 | 260401 23:00 | HTF | W1 | [TO BE FILLED] | [TO BE FILLED] | [TO BE FILLED] | img |
| 260401 14:30 | 260401 23:00 | HTF | D1 | 512 | 1 | 2 | img |
| 260401 14:30 | 260401 23:00 | HTF | H4 | 512 | 1 | 3 | img |
| 260401 14:30 | 260401 23:00 | MTF | H1 | 512 | 1 | 0 | img |
| 260401 14:30 | 260401 23:00 | MTF | M30 | 511→411 | 1→3 | 1→0 | img |
| 260401 14:30 | 260401 23:00 | MTF | M15 | 511→512 | 1→1 | 1→3 | img |
| 260401 14:30 | 260401 23:00 | LTF | M5 | 511 | 1 | 1 | img |
| 260402 00:00 | 260402 05:00 | HTF | W1 | [TO BE FILLED] | [TO BE FILLED] | [TO BE FILLED] | img |
| 260402 00:00 | 260402 05:00 | HTF | D1 | 513 | 1 | 2 | img |
| 260402 00:00 | 260402 05:00 | HTF | H4 | 512 | 1 | 3 | img |
| 260402 00:00 | 260402 05:00 | MTF | H1 | 512 | 1 | 0 | img |
| 260402 00:00 | 260402 05:00 | MTF | M30 | 411 | 1 | 0 | img |
| 260402 00:00 | 260402 05:00 | MTF | M15 | 512 | 1 | 3 | img |
| 260402 00:00 | 260402 05:00 | LTF | M5 | 512 | 1 | 3 | img |
| 260402 05:00 | 260402 09:00 | HTF | W1 | [TO BE FILLED] | [TO BE FILLED] | [TO BE FILLED] | img |
| 260402 05:00 | 260402 09:00 | HTF | D1 | 513 | 1 | 2 | img |
| 260402 05:00 | 260402 09:00 | HTF | H4 | 512 | 1 | 3 | img |
| 260402 05:00 | 260402 09:00 | MTF | H1 | 521 | 2 | 1 | img |
| 260402 05:00 | 260402 09:00 | MTF | M30 | 411→521 | 1→2 | 0→1 | img |
| 260402 05:00 | 260402 09:00 | MTF | M15 | 522 | 2 | 4 | img |
| 260402 05:00 | 260402 09:00 | LTF | M5 | 521 | 2 | 1 | img |

##### Step 2: Two-Axis Classification
- **HTF scenario:** S — H4 fly 512, D1 shrink 513 (reversal in progress)
- **MTF scenario:** R1 — M30 reversed 521, H4 still flying 512 (pre-pivot)
- **MTF direction vs H4:** OPPOSITE  R1 divergence (M30 diffMid=2, H4 diffMid=1)

##### Step 3: Cascade
- direction: D1 compress HTF  LTF, then D2 expand LTF  HTF (reversal)
- depth: Full — M5 SQZ break  M30 reversal | leading TF: M30 (reversed)
- key transition: Complete reversal sequence — fly  SQZ  reverse

##### Step 4: TIMELINE
| From | To | Scenario (HTF-MTF) | Trend / Tier | HTF state | MTF state | Source | Notes |
|------|-----|--------------------|--------------|-----------|-----------|--------|-------|
| 260401 14:30 | 260401 23:00 | F?-F | Up / Tier 1 | H4 fly 512, D1 fly 512 | M30 fly 511, M15 fly 511 | img | All aligned up — W1 unreadable |
| 260401 23:00 | 260402 00:00 | F?-C1  S-C1 | Up / Tier 1→2 | H4 fly 512, D1 512→513 | M30 511→411, M15 fly 512 | img | D1 shrinks, M30 enters SQZ |
| 260402 00:00 | 260402 05:00 | S-C1 | Up / Tier 2 | H4 fly 512, D1 shrink 513 | M30 SQZ 411, M15 fly 512 | img | M30 SQZ — waiting break |
| 260402 05:00 | 260402 09:00 | S-R1 | Down / Tier 3 | H4 fly 512, D1 shrink 513 | M30 fly 521, M15 fly 522 | img | M30 breaks SQZ 521 — R1 reversal |

##### Step 5: Conclusion + Prediction
- **Scenario: S-R1** (HTF=S MTF=R1). DIVERGENCE: MTF down (diffMid=2) vs H4 up (diffMid=1).
- **Next likely:** S-R2 if H4 flips to 521; S-C1 if M30 re-enters SQZ. Watch: H4 BBW_stage for flip.

---

## Scenario B (Compression Release / Breakout)

#### Image 1 Analysis — backtested_EA_sideway_2_fly.jpg
![backtested_EA_sideway_2_fly](./Backtest_data/extras/backtested_EA_sideway_2_fly.jpg)

**Period:** 2026.02.06 01:00 → 2026.02.07 21:00 (chart x-axis: "06.02.2026" / "07.02.2026", log-confirmed)

##### Step 1: State Read
| From | To | TF group | TF | BBW_stage | diffMid | BBUpDn | Source |
|------|-----|----------|----|-----------|---------|--------|--------|
| 260206 01:00 | 260206 09:00 | HTF | W1 | [TO BE FILLED] | [TO BE FILLED] | [TO BE FILLED] | img |
| 260206 01:00 | 260206 09:00 | HTF | D1 | 513 | 1 | 2 | log |
| 260206 01:00 | 260206 09:00 | HTF | H4 | 513 | 1 | 2 | log |
| 260206 01:00 | 260206 09:00 | MTF | H1 | 402 | 2 | 0 | log |
| 260206 01:00 | 260206 09:00 | MTF | M30 | 521 | 2 | 1 | log |
| 260206 01:00 | 260206 09:00 | MTF | M15 | 522 | 2 | 4 | log |
| 260206 01:00 | 260206 09:00 | LTF | M5 | 400-499→521 | 3→2 | 0→1 | img |
| 260206 09:00 | 260207 21:00 | HTF | W1 | [TO BE FILLED] | [TO BE FILLED] | [TO BE FILLED] | img |
| 260206 09:00 | 260207 21:00 | HTF | D1 | 513 | 1 | 2 | img |
| 260206 09:00 | 260207 21:00 | HTF | H4 | 513 | 1 | 2 | img |
| 260206 09:00 | 260207 21:00 | MTF | H1 | 513→521 | 2→2 | 2→1 | img |
| 260206 09:00 | 260207 21:00 | MTF | M30 | 521 | 2 | 1 | img |
| 260206 09:00 | 260207 21:00 | MTF | M15 | 522 | 2 | 4 | img |
| 260206 09:00 | 260207 21:00 | LTF | M5 | 521 | 2 | 1 | img |

##### Step 2: Two-Axis Classification
- **HTF scenario:** S — H4 shrink 513, D1 shrink 513
- **MTF scenario:** B1 → B2 — M5/M15 fly 521/522, M30 fly 521, H1 SQZ then decompress
- **MTF direction vs H4:** OPPOSITE  R1 divergence (M30 diffMid=2, H4 diffMid=1)

##### Step 3: Cascade
- direction: D2 expand LTF  HTF
- depth: M5 broke SQZ first | leading TF: M5 (broke SQZ)
- key transition: All TF SQZ  M5 breaks SQZ  D2 expansion

##### Step 4: TIMELINE
| From | To | Scenario (HTF-MTF) | Trend / Tier | HTF state | MTF state | Source | Notes |
|------|-----|--------------------|--------------|-----------|-----------|--------|-------|
| 260206 01:00 | 260206 09:00 | S-C4 | Down / Tier 2 | H4 shrink 513, D1 shrink 513 | H1 SQZ 402, M30 fly 521, M15 fly 522 | log | H1 SQZ blocks; M30/M15 already fly down |
| 260206 09:00 | 260207 21:00 | S-B2 | Down / Tier 3 | H4 shrink 513 | M30 fly 521, M15 fly 522, H1 decompressing | img | D2 confirmed — M30 fly down |

##### Step 5: Conclusion + Prediction
- **Scenario: S-B2** (HTF=S MTF=B2).  DIVERGENCE: MTF direction (down) vs H4 direction (up).
- **Next likely:** S-B3 if H4 breaks to fly 521/522; S-C4 if H4 remains 513. Watch: H4 BBW_stage.

#### Image 2 Analysis — backtested_EA_sideway_2_fly_zoomin.jpg
![backtested_EA_sideway_2_fly_zoomin](./Backtest_data/extras/backtested_EA_sideway_2_fly_zoomin.jpg)

**Period:** 2026.02.06 13:00 → 2026.02.07 09:00 (chart x-axis: "06.02.2026" / "07.02.2026")

##### Step 1: State Read
| From | To | TF group | TF | BBW_stage | diffMid | BBUpDn | Source |
|------|-----|----------|----|-----------|---------|--------|--------|
| 260206 13:00 | 260207 09:00 | HTF | W1 | [TO BE FILLED] | [TO BE FILLED] | [TO BE FILLED] | img |
| 260206 13:00 | 260207 09:00 | HTF | D1 | 513 | 1 | 2 | img |
| 260206 13:00 | 260207 09:00 | HTF | H4 | 513 | 1 | 2 | img |
| 260206 13:00 | 260207 09:00 | MTF | H1 | 513 | 2 | 2 | img |
| 260206 13:00 | 260207 09:00 | MTF | M30 | 521 | 2 | 1 | img |
| 260206 13:00 | 260207 09:00 | MTF | M15 | 521 | 2 | 1 | img |
| 260206 13:00 | 260207 09:00 | LTF | M5 | 521 | 2 | 1 | img |

##### Step 2: Two-Axis Classification
- **HTF scenario:** S — H4/D1 shrink 513
- **MTF scenario:** B2 — M30/M15 fly 521, H1 shrink 513
- **MTF direction vs H4:** OPPOSITE  R1 divergence

##### Step 3: Cascade
- direction: D2 expand LTF  HTF
- depth: D2 advancing | leading TF: M30 (confirm fly)
- key transition: M5/M15/M30 fly 521 — D2 confirmed in down direction

##### Step 4: TIMELINE
| From | To | Scenario (HTF-MTF) | Trend / Tier | HTF state | MTF state | Source | Notes |
|------|-----|--------------------|--------------|-----------|-----------|--------|-------|
| 260206 13:00 | 260207 01:00 | S-B2 | Down / Tier 3 | H4 shrink 513 | M30/M15 fly 521, H1 shrink 513 | img | D2 expanding down |
| 260207 01:00 | 260207 09:00 | S-B2 | Down / Tier 3 | H4 shrink 513 | M30/M15 fly 521 | img | H4 still shrink — B2, not B3 |

##### Step 5: Conclusion + Prediction
- **Scenario: S-B2** (HTF=S MTF=B2).  DIVERGENCE: MTF down vs H4 up.
- **Next likely:** S-B3 if H4 513→521/522; S-S if H4 remains 513. Watch: H4 BBW_stage.

#### Image 3 Analysis — backtest_EA_sideway_2_fly2_zoomin.jpg
![backtest_EA_sideway_2_fly2_zoomin](./Backtest_data/extras/backtest_EA_sideway_2_fly2_zoomin.jpg)

**Period:** 2026.02.06 13:00 → 2026.02.07 09:00 (chart x-axis: "06.02.2026" / "07.02.2026")

##### Step 1: State Read
| From | To | TF group | TF | BBW_stage | diffMid | BBUpDn | Source |
|------|-----|----------|----|-----------|---------|--------|--------|
| 260206 13:00 | 260207 09:00 | HTF | W1 | [TO BE FILLED] | [TO BE FILLED] | [TO BE FILLED] | img |
| 260206 13:00 | 260207 09:00 | HTF | D1 | 513 | 1 | 2 | img |
| 260206 13:00 | 260207 09:00 | HTF | H4 | 513 | 1 | 2 | img |
| 260206 13:00 | 260207 09:00 | MTF | H1 | 513 | 2 | 2 | img |
| 260206 13:00 | 260207 09:00 | MTF | M30 | 521 | 2 | 1 | img |
| 260206 13:00 | 260207 09:00 | MTF | M15 | 521 | 2 | 1 | img |
| 260206 13:00 | 260207 09:00 | LTF | M5 | 521 | 2 | 1 | img |

##### Step 2: Two-Axis Classification
- **HTF scenario:** S — H4/D1 shrink 513
- **MTF scenario:** B2 — M30/M15 fly 521, H1 shrink 513
- **MTF direction vs H4:** OPPOSITE  R1 divergence

##### Step 3: Cascade
- direction: D2 expand LTF  HTF
- depth: D2 advancing | leading TF: M30 (confirm fly)
- key transition: M5/M15/M30 fly 521 — D2 confirmed in down direction

##### Step 4: TIMELINE
| From | To | Scenario (HTF-MTF) | Trend / Tier | HTF state | MTF state | Source | Notes |
|------|-----|--------------------|--------------|-----------|-----------|--------|-------|
| 260206 13:00 | 260207 01:00 | S-B2 | Down / Tier 3 | H4 shrink 513 | M30/M15 fly 521, H1 shrink 513 | img | D2 expanding down |
| 260207 01:00 | 260207 09:00 | S-B2 | Down / Tier 3 | H4 shrink 513 | M30/M15 fly 521 | img | H4 still shrink — B2, not B3 |

##### Step 5: Conclusion + Prediction
- **Scenario: S-B2** (HTF=S MTF=B2).  DIVERGENCE: MTF down vs H4 up.
- **Next likely:** S-B3 if H4 513→521/522; S-S if H4 remains 513. Watch: H4 BBW_stage.

---

## Scenario V (Direction Pivot)

#### Image 1 Analysis — backtested_EA_fly_shrink_2_sideway2.jpg
![backtested_EA_fly_shrink_2_sideway2](./Backtest_data/extras/backtested_EA_fly_shrink_2_sideway2.jpg)

**Period:** 2026.04.02 05:00 → 2026.04.03 03:00 (chart x-axis: "02.04.2026" / "03.04.2026")

##### Step 1: State Read
| From | To | TF group | TF | BBW_stage | diffMid | BBUpDn | Source |
|------|-----|----------|----|-----------|---------|--------|--------|
| 260402 05:00 | 260402 17:00 | HTF | W1 | [TO BE FILLED] | [TO BE FILLED] | [TO BE FILLED] | img |
| 260402 05:00 | 260402 17:00 | HTF | D1 | 513 | 1 | 2 | img |
| 260402 05:00 | 260402 17:00 | HTF | H4 | 512 | 1 | 3 | img |
| 260402 05:00 | 260402 17:00 | MTF | H1 | 512 | 1 | 0 | img |
| 260402 05:00 | 260402 17:00 | MTF | M30 | 513 | 1 | 2 | img |
| 260402 05:00 | 260402 17:00 | MTF | M15 | 513 | 5 | 2 | img |
| 260402 05:00 | 260402 17:00 | LTF | M5 | 513 | 5 | 2 | img |
| 260402 17:00 | 260403 03:00 | HTF | W1 | [TO BE FILLED] | [TO BE FILLED] | [TO BE FILLED] | img |
| 260402 17:00 | 260403 03:00 | HTF | D1 | 513 | 1 | 2 | img |
| 260402 17:00 | 260403 03:00 | HTF | H4 | 512 | 1 | 3 | img |
| 260402 17:00 | 260403 03:00 | MTF | H1 | 512 | 1 | 0 | img |
| 260402 17:00 | 260403 03:00 | MTF | M30 | 411 | 1 | 0 | img |
| 260402 17:00 | 260403 03:00 | MTF | M15 | 513 | 5 | 2 | img |
| 260402 17:00 | 260403 03:00 | LTF | M5 | 513 | 5 | 2 | img |

##### Step 2: Two-Axis Classification
- **HTF scenario:** S — H4 fly 512, D1 shrink 513
- **MTF scenario:** C2 — M30 SQZ 411, M15 shrink 513
- **MTF direction vs H4:** SAME  continuation

##### Step 3: Cascade
- direction: D1 compress HTF  LTF
- depth: M30 SQZ 411 | leading TF: M30 (watch for SQZ break)
- key transition: M30 513→411 — D1 deepens to C2

##### Step 4: TIMELINE
| From | To | Scenario (HTF-MTF) | Trend / Tier | HTF state | MTF state | Source | Notes |
|------|-----|--------------------|--------------|-----------|-----------|--------|-------|
| 260402 05:00 | 260402 17:00 | S-S2 | Up / Tier 2 | H4 fly 512 | M30 shrink 513, M15 shrink 513 | img | D1 compression |
| 260402 17:00 | 260403 03:00 | S-C2 | Up / Tier 2 | H4 fly 512 | M30 SQZ 411, M15 shrink 513 | img | M30 enters SQZ — C2 |

##### Step 5: Conclusion + Prediction
- **Scenario: S-C2** (HTF=S MTF=C2). No divergence.
- **Next likely:** S-P2 if M30 411→511 (same dir as H4); S-R1 if M30 411→521 (opposite). Watch: M30 BBW_stage.

---

## Scenario C (Deep Compression)

#### Image 1 Analysis — backtested_EA_fly_shrink_2_sideway.jpg
![backtested_EA_fly_shrink_2_sideway](./Backtest_data/extras/backtested_EA_fly_shrink_2_sideway.jpg)

**Period:** 2026.04.01 13:00 → 2026.04.02 17:00 (chart x-axis: "01.04.2026" / "02.04.2026", log-confirmed)

##### Step 1: State Read
| From | To | TF group | TF | BBW_stage | diffMid | BBUpDn | Source |
|------|-----|----------|----|-----------|---------|--------|--------|
| 260401 13:00 | 260401 17:00 | HTF | W1 | [TO BE FILLED] | [TO BE FILLED] | [TO BE FILLED] | img |
| 260401 13:00 | 260401 17:00 | HTF | D1 | 513 | 1 | 2 | log |
| 260401 13:00 | 260401 17:00 | HTF | H4 | 512 | 1 | 3 | log |
| 260401 13:00 | 260401 17:00 | MTF | H1 | 512 | 1 | 0 | log |
| 260401 13:00 | 260401 17:00 | MTF | M30 | 513 | 1 | 2 | img |
| 260401 13:00 | 260401 17:00 | MTF | M15 | 513 | 5 | 2 | img |
| 260401 13:00 | 260401 17:00 | LTF | M5 | 513 | 5 | 2 | img |
| 260401 17:00 | 260402 17:00 | HTF | W1 | [TO BE FILLED] | [TO BE FILLED] | [TO BE FILLED] | img |
| 260401 17:00 | 260402 17:00 | HTF | D1 | 513 | 1 | 2 | img |
| 260401 17:00 | 260402 17:00 | HTF | H4 | 512 | 1 | 3 | img |
| 260401 17:00 | 260402 17:00 | MTF | H1 | 512 | 1 | 0 | img |
| 260401 17:00 | 260402 17:00 | MTF | M30 | 411 | 1 | 0 | img |
| 260401 17:00 | 260402 17:00 | MTF | M15 | 400-499→512 | 3→1 | 0→3 | img |
| 260401 17:00 | 260402 17:00 | LTF | M5 | 400-499 | 3 | 0 | img |

##### Step 2: Two-Axis Classification
- **HTF scenario:** S — H4 fly 512, D1 shrink 513
- **MTF scenario:** C2 — M30/M15/M5 SQZ 400-499
- **MTF direction vs H4:** SAME  continuation (M30 diffMid=1 same as H4)

##### Step 3: Cascade
- direction: D1 compress HTF  LTF
- depth: M5 (full SQZ) | leading TF: M5 (watch for REVUP/REVDN)
- key transition: Sequential compression — M5 first, M15 second, M30 third; G0c-SQZLOCK active

##### Step 4: TIMELINE
| From | To | Scenario (HTF-MTF) | Trend / Tier | HTF state | MTF state | Source | Notes |
|------|-----|--------------------|--------------|-----------|-----------|--------|-------|
| 260401 13:00 | 260401 17:00 | S-S2 | Up / Tier 2 | H4 fly 512 | M30 shrink 513, M15 shrink 513 | img | D1 compression begins |
| 260401 17:00 | 260402 01:00 | S-C2 | Up / Tier 2 | H4 fly 512 | M30/M15/M5 SQZ 400-499 | img | D1 reaches BOTTOM; G0c-SQZLOCK |
| 260402 01:00 | 260402 04:00 | S-C2 | Up / Tier 2 | H4 fly 512 | M30 SQZ 411, M15 fly 512 | img | M30 SQZ 411 confirmed; M15 fly 512 |
| 260402 04:00 | 260402 17:00 | S-C2 | Up / Tier 2 | H4 fly 512 | M30 SQZ 411, M15 fly 512 | img | Sustained C2; M30 still SQZ |

##### Step 5: Conclusion + Prediction
- **Scenario: S-C2** (HTF=S MTF=C2). No divergence.
- **Next likely:** S-P2 if M5 REVUP and M15 follows; S-R1 if M30 411→521 (opposite H4). Watch: M5 BBW_stage + M30 BBW_stage.

#### Image 2 Analysis — backtested_EA_fly_shrink_2_sideway_zoomin.jpg
![backtested_EA_fly_shrink_2_sideway_zoomin](./Backtest_data/extras/backtested_EA_fly_shrink_2_sideway_zoomin.jpg)

**Period:** 2026.04.02 09:00 → 2026.04.02 17:00 (chart x-axis: "02.04.2026")

##### Step 1: State Read
| From | To | TF group | TF | BBW_stage | diffMid | BBUpDn | Source |
|------|-----|----------|----|-----------|---------|--------|--------|
| 260402 09:00 | 260402 17:00 | HTF | W1 | [TO BE FILLED] | [TO BE FILLED] | [TO BE FILLED] | img |
| 260402 09:00 | 260402 17:00 | HTF | D1 | 513 | 1 | 2 | img |
| 260402 09:00 | 260402 17:00 | HTF | H4 | 512 | 1 | 3 | img |
| 260402 09:00 | 260402 17:00 | MTF | H1 | 521 | 2 | 1 | log |
| 260402 09:00 | 260402 17:00 | MTF | M30 | 411→521 | 1→2 | 0→1 | log |
| 260402 09:00 | 260402 17:00 | MTF | M15 | 522 | 2 | 4 | log |
| 260402 09:00 | 260402 17:00 | LTF | M5 | 411→521 | 1→2 | 0→1 | img |

##### Step 2: Two-Axis Classification
- **HTF scenario:** S — H4 fly 512, D1 shrink 513
- **MTF scenario:** P2 → P3 — M30 breaks SQZ 411→521, M15 fly 522
- **MTF direction vs H4:** OPPOSITE  R1 divergence (M30 diffMid=2, H4 diffMid=1)

##### Step 3: Cascade
- direction: D2 expand LTF  HTF
- depth: M5 broke SQZ first | leading TF: M5 (broke SQZ)
- key transition: M5 SQZ break  M15 follows  M30 breaks SQZ 411→521

##### Step 4: TIMELINE
| From | To | Scenario (HTF-MTF) | Trend / Tier | HTF state | MTF state | Source | Notes |
|------|-----|--------------------|--------------|-----------|-----------|--------|-------|
| 260402 09:00 | 260402 10:00 | S-P2 | Down / Tier 3 | H4 fly 512 | M5 fly 521, M15 fly 522, M30 SQZ 411 | img | M5 broke SQZ; M30 still SQZ |
| 260402 10:00 | 260402 17:00 | S-P3 | Down / Tier 3 | H4 fly 512 | M30 fly 521, M15 fly 522 | img | M30 breaks SQZ 411→521; D2 confirmed |

##### Step 5: Conclusion + Prediction
- **Scenario: S-P3** (HTF=S MTF=P3).  DIVERGENCE: MTF down (diffMid=2) vs H4 up (diffMid=1).
- **Next likely:** S-B2 if M30 fly 521 sustained; S-S if M30 re-enters shrink. Watch: M30 BBW_stage.

#### Image 3 Analysis — backtested_EA_phase_3a_symmetric.jpg
![backtested_EA_phase_3a_symmetric](./Backtest_data/extras/backtested_EA_phase_3a_symmetric.jpg)

**Period:** 2026.04.01 17:00 → 2026.04.02 05:00 (chart x-axis: "01.04.2026" / "02.04.2026", symmetric SQZ phase)

##### Step 1: State Read
| From | To | TF group | TF | BBW_stage | diffMid | BBUpDn | Source |
|------|-----|----------|----|-----------|---------|--------|--------|
| 260401 17:00 | 260402 05:00 | HTF | W1 | [TO BE FILLED] | [TO BE FILLED] | [TO BE FILLED] | img |
| 260401 17:00 | 260402 05:00 | HTF | D1 | 513 | 1 | 2 | img |
| 260401 17:00 | 260402 05:00 | HTF | H4 | 512 | 1 | 3 | img |
| 260401 17:00 | 260402 05:00 | MTF | H1 | 512 | 1 | 0 | img |
| 260401 17:00 | 260402 05:00 | MTF | M30 | 411 | 1 | 0 | img |
| 260401 17:00 | 260402 05:00 | MTF | M15 | 411 | 1 | 0 | img |
| 260401 17:00 | 260402 05:00 | LTF | M5 | 411 | 1 | 0 | img |

##### Step 2: Two-Axis Classification
- **HTF scenario:** S — H4 fly 512, D1 shrink 513
- **MTF scenario:** C2 — M30/M15/M5 all SQZ 411 (symmetric compression)
- **MTF direction vs H4:** SAME  continuation (SQZ but diffMid=1)

##### Step 3: Cascade
- direction: D1 compress HTF  LTF (BOTTOM)
- depth: M5 (full SQZ) | leading TF: M5 (watch for REVUP/REVDN)
- key transition: Symmetric SQZ — all LTF compressed equally, G0c-SQZLOCK

##### Step 4: TIMELINE
| From | To | Scenario (HTF-MTF) | Trend / Tier | HTF state | MTF state | Source | Notes |
|------|-----|--------------------|--------------|-----------|-----------|--------|-------|
| 260401 17:00 | 260402 05:00 | S-C2 | Up / Tier 2 | H4 fly 512 | M30/M15/M5 SQZ 411 | img | Symmetric SQZ — all LTF compressed |

##### Step 5: Conclusion + Prediction
- **Scenario: S-C2** (HTF=S MTF=C2). No divergence.
- **Next likely:** S-P2 if M5 REVUP; S-R1 if M30 411→521 (opposite H4). Watch: M5 BBW_stage.

#### Image 4 Analysis — backtested_EA_phase_3a_to_3b.jpg
![backtested_EA_phase_3a_to_3b](./Backtest_data/extras/backtested_EA_phase_3a_to_3b.jpg)

**Period:** 2026.04.02 05:00 → 2026.04.02 17:00 (chart x-axis: "02.04.2026", transition from symmetric to asymmetric SQZ)

##### Step 1: State Read
| From | To | TF group | TF | BBW_stage | diffMid | BBUpDn | Source |
|------|-----|----------|----|-----------|---------|--------|--------|
| 260402 05:00 | 260402 10:00 | HTF | W1 | [TO BE FILLED] | [TO BE FILLED] | [TO BE FILLED] | img |
| 260402 05:00 | 260402 10:00 | HTF | D1 | 513 | 1 | 2 | img |
| 260402 05:00 | 260402 10:00 | HTF | H4 | 512 | 1 | 3 | img |
| 260402 05:00 | 260402 10:00 | MTF | H1 | 512 | 1 | 0 | img |
| 260402 05:00 | 260402 10:00 | MTF | M30 | 411 | 1 | 0 | img |
| 260402 05:00 | 260402 10:00 | MTF | M15 | 411 | 1 | 0 | img |
| 260402 05:00 | 260402 10:00 | LTF | M5 | 411→521 | 1→2 | 0→1 | img |
| 260402 10:00 | 260402 17:00 | HTF | W1 | [TO BE FILLED] | [TO BE FILLED] | [TO BE FILLED] | img |
| 260402 10:00 | 260402 17:00 | HTF | D1 | 513 | 1 | 2 | img |
| 260402 10:00 | 260402 17:00 | HTF | H4 | 512 | 1 | 3 | img |
| 260402 10:00 | 260402 17:00 | MTF | H1 | 512 | 1 | 0 | img |
| 260402 10:00 | 260402 17:00 | MTF | M30 | 411 | 1 | 0 | img |
| 260402 10:00 | 260402 17:00 | MTF | M15 | 522 | 2 | 4 | img |
| 260402 10:00 | 260402 17:00 | LTF | M5 | 521 | 2 | 1 | img |

##### Step 2: Two-Axis Classification
- **HTF scenario:** S — H4 fly 512, D1 shrink 513
- **MTF scenario:** P2 — M5 breaks SQZ, M15 confirms, M30 still SQZ
- **MTF direction vs H4:** OPPOSITE  R1 divergence (M5/M15 diffMid=2, H4 diffMid=1)

##### Step 3: Cascade
- direction: D2 expand LTF  HTF (asymmetric — M5/M15 break, M30 still SQZ)
- depth: M5 broke SQZ first | leading TF: M30 (watch for SQZ break)
- key transition: Asymmetric break — M5/M15 out of SQZ but M30 remains compressed

##### Step 4: TIMELINE
| From | To | Scenario (HTF-MTF) | Trend / Tier | HTF state | MTF state | Source | Notes |
|------|-----|--------------------|--------------|-----------|-----------|--------|-------|
| 260402 05:00 | 260402 10:00 | S-C2  S-P2 | Down / Tier 2→3 | H4 fly 512 | M5 411→521, M15 411→522, M30 SQZ 411 | img | M5 breaks SQZ first |
| 260402 10:00 | 260402 17:00 | S-P2 | Down / Tier 3 | H4 fly 512 | M5 fly 521, M15 fly 522, M30 SQZ 411 | img | Asymmetric — M30 still SQZ |

##### Step 5: Conclusion + Prediction
- **Scenario: S-P2** (HTF=S MTF=P2).  DIVERGENCE: MTF down (diffMid=2) vs H4 up (diffMid=1).
- **Next likely:** S-P3 if M30 411→521; S-C2 if M30 remains SQZ. Watch: M30 BBW_stage.

#### Image 5 Analysis — backtested_EA_phase_3b_asymmetric.jpg
![backtested_EA_phase_3b_asymmetric](./Backtest_data/extras/backtested_EA_phase_3b_asymmetric.jpg)

**Period:** 2026.04.02 10:00 → 2026.04.02 17:00 (chart x-axis: "02.04.2026", asymmetric SQZ — M5/M15 out, M30 still in)

##### Step 1: State Read
| From | To | TF group | TF | BBW_stage | diffMid | BBUpDn | Source |
|------|-----|----------|----|-----------|---------|--------|--------|
| 260402 10:00 | 260402 17:00 | HTF | W1 | [TO BE FILLED] | [TO BE FILLED] | [TO BE FILLED] | img |
| 260402 10:00 | 260402 17:00 | HTF | D1 | 513 | 1 | 2 | img |
| 260402 10:00 | 260402 17:00 | HTF | H4 | 512 | 1 | 3 | img |
| 260402 10:00 | 260402 17:00 | MTF | H1 | 512 | 1 | 0 | img |
| 260402 10:00 | 260402 17:00 | MTF | M30 | 411 | 1 | 0 | img |
| 260402 10:00 | 260402 17:00 | MTF | M15 | 522 | 2 | 4 | img |
| 260402 10:00 | 260402 17:00 | LTF | M5 | 521 | 2 | 1 | img |

##### Step 2: Two-Axis Classification
- **HTF scenario:** S — H4 fly 512, D1 shrink 513
- **MTF scenario:** P2 — M5 fly 521, M15 fly 522, M30 still SQZ 411
- **MTF direction vs H4:** OPPOSITE  R1 divergence

##### Step 3: Cascade
- direction: D2 expand LTF  HTF (partial — M30 still compressed)
- depth: M5/M15 broke SQZ | leading TF: M30 (watch for SQZ break)
- key transition: Asymmetric D2 — M5/M15 expanded but M30 remains in SQZ

##### Step 4: TIMELINE
| From | To | Scenario (HTF-MTF) | Trend / Tier | HTF state | MTF state | Source | Notes |
|------|-----|--------------------|--------------|-----------|-----------|--------|-------|
| 260402 10:00 | 260402 17:00 | S-P2 | Down / Tier 3 | H4 fly 512 | M5 fly 521, M15 fly 522, M30 SQZ 411 | img | Asymmetric D2 — M30 still SQZ |

##### Step 5: Conclusion + Prediction
- **Scenario: S-P2** (HTF=S MTF=P2).  DIVERGENCE: MTF down vs H4 up.
- **Next likely:** S-P3 if M30 411→521; S-C2 if M30 remains SQZ. Watch: M30 BBW_stage.

#### Image 6 Analysis — backtested_EA_phase_3b_out_recovery.jpg
![backtested_EA_phase_3b_out_recovery](./Backtest_data/extras/backtested_EA_phase_3b_out_recovery.jpg)

**Period:** 2026.04.02 17:00 → 2026.04.03 03:00 (chart x-axis: "02.04.2026" / "03.04.2026", recovery from asymmetric SQZ)

##### Step 1: State Read
| From | To | TF group | TF | BBW_stage | diffMid | BBUpDn | Source |
|------|-----|----------|----|-----------|---------|--------|--------|
| 260402 17:00 | 260403 03:00 | HTF | W1 | [TO BE FILLED] | [TO BE FILLED] | [TO BE FILLED] | img |
| 260402 17:00 | 260403 03:00 | HTF | D1 | 513 | 1 | 2 | img |
| 260402 17:00 | 260403 03:00 | HTF | H4 | 512 | 1 | 3 | img |
| 260402 17:00 | 260403 03:00 | MTF | H1 | 521 | 2 | 1 | img |
| 260402 17:00 | 260403 03:00 | MTF | M30 | 521 | 2 | 1 | img |
| 260402 17:00 | 260403 03:00 | MTF | M15 | 522 | 2 | 4 | img |
| 260402 17:00 | 260403 03:00 | LTF | M5 | 521 | 2 | 1 | img |

##### Step 2: Two-Axis Classification
- **HTF scenario:** S — H4 fly 512, D1 shrink 513
- **MTF scenario:** P3 — M30 fly 521, M15 fly 522, full MTF re-alignment
- **MTF direction vs H4:** OPPOSITE  R1 divergence (M30 diffMid=2, H4 diffMid=1)

##### Step 3: Cascade
- direction: D2 expand LTF  HTF (complete — M30 confirms)
- depth: TOP — D2 complete | leading TF: M30 (confirm fly)
- key transition: M30 breaks SQZ 411→521 — full D2 expansion confirmed

##### Step 4: TIMELINE
| From | To | Scenario (HTF-MTF) | Trend / Tier | HTF state | MTF state | Source | Notes |
|------|-----|--------------------|--------------|-----------|-----------|--------|-------|
| 260402 17:00 | 260403 03:00 | S-P3 | Down / Tier 3 | H4 fly 512 | M30 fly 521, M15 fly 522 | img | D2 complete — M30 confirms |

##### Step 5: Conclusion + Prediction
- **Scenario: S-P3** (HTF=S MTF=P3).  DIVERGENCE: MTF down vs H4 up.
- **Next likely:** S-B2 if M30 fly 521 sustained; S-S if M30 re-enters shrink. Watch: M30 BBW_stage.

#### Image 7 Analysis — backtested_EA_phase_6_post_sqz_oscillation.jpg
![backtested_EA_phase_6_post_sqz_oscillation](./Backtest_data/extras/backtested_EA_phase_6_post_sqz_oscillation.jpg)

**Period:** 2026.04.03 03:00 → 2026.04.03 17:00 (chart x-axis: "03.04.2026", post-SQZ oscillation)

##### Step 1: State Read
| From | To | TF group | TF | BBW_stage | diffMid | BBUpDn | Source |
|------|-----|----------|----|-----------|---------|--------|--------|
| 260403 03:00 | 260403 17:00 | HTF | W1 | [TO BE FILLED] | [TO BE FILLED] | [TO BE FILLED] | img |
| 260403 03:00 | 260403 17:00 | HTF | D1 | 513 | 1 | 2 | img |
| 260403 03:00 | 260403 17:00 | HTF | H4 | 512 | 1 | 3 | img |
| 260403 03:00 | 260403 17:00 | MTF | H1 | 521 | 2 | 1 | img |
| 260403 03:00 | 260403 17:00 | MTF | M30 | 521 | 2 | 1 | img |
| 260403 03:00 | 260403 17:00 | MTF | M15 | 522 | 2 | 4 | img |
| 260403 03:00 | 260403 17:00 | LTF | M5 | 521 | 2 | 1 | img |

##### Step 2: Two-Axis Classification
- **HTF scenario:** S — H4 fly 512, D1 shrink 513
- **MTF scenario:** P3 — M30 fly 521, M15 fly 522 (post-SQZ oscillation, MTF re-aligned)
- **MTF direction vs H4:** OPPOSITE  R1 divergence

##### Step 3: Cascade
- direction: D2 complete — post-SQZ oscillation phase
- depth: TOP — all MTF expanded | leading TF: H4 (watch for flip)
- key transition: Post-SQZ — MTF fully re-expanded in down direction, waiting H4 response

##### Step 4: TIMELINE
| From | To | Scenario (HTF-MTF) | Trend / Tier | HTF state | MTF state | Source | Notes |
|------|-----|--------------------|--------------|-----------|-----------|--------|-------|
| 260403 03:00 | 260403 17:00 | S-P3 | Down / Tier 3 | H4 fly 512 | M30 fly 521, M15 fly 522 | img | Post-SQZ oscillation — D2 complete |

##### Step 5: Conclusion + Prediction
- **Scenario: S-P3** (HTF=S MTF=P3).  DIVERGENCE: MTF down vs H4 up.
- **Next likely:** S-R2 if H4 flips to 521; S-S if M30 re-enters shrink. Watch: H4 BBW_stage for flip.

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
