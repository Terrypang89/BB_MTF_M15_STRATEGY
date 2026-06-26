# Image Analysis Blocks

Companion to `backtest_chart_analysis.md` — Part 3 image-analysis blocks have been separated from the scenario definitions into this document. The scenario definitions (Cascade Position, Sub-Scenarios, Sub-State Flowchart, Identification Flowchart, Trade action) remain in `backtest_chart_analysis.md`.

Each block uses a 5-step + TIMELINE format. States are confirmed against the backtest log (`references/Backtest_data/V31.04/20260620_clean.log`) where date coverage exists; W1 states remain `[TO BE FILLED]` where images do not show W1 clearly.

---

## Scenario F

#### Image Analysis — backtested_EA_fly_scenario.jpg
**Period:** 2026.01.02 01:00 → 2026.01.03 04:00

##### Step 1: State Read (evidence first — one table, all 7 TFs)
| TF group | TF | BBW_stage | diffMid | BBUpDn | Source (img/log) |
|----------|----|-----------|---------|--------|------------------|
| HTF | W1 | 511 | 1 | 1 | img |
| HTF | D1 | 511 | 1 | 1 | img |
| HTF | H4 | 511 | 1 | 1 | img |
| MTF | H1 | 511 | 1 | 1 | img (log at 03:00 shows H1 SQZ 424 — image depicts later recovery to fly) |
| MTF | M30 | 511 | 1 | 1 | log-confirmed (W_stage_M30:(FLY)[511], diffMid=1.0, BBUpDn=1) |
| MTF | M15 | 511 | 1 | 1 | log-confirmed (W_stage_M15:(FLY)[511], diffMid=1.0, BBUpDn=1) |
| LTF | M5 | 511 (brief 411 SQZ noise) | 1 | 1 | img |

##### Step 2: Two-Axis Classification
- **HTF scenario:** F — W1/D1/H4 all fly 511, same direction
- **MTF scenario:** F — H1/M30 fly 511, aligned with H4
- **MTF direction vs H4:** SAME → continuation

##### Step 3: Cascade
- direction: TOP — no active D1 or D2
- depth: None — all fly | leading TF: H4 (watch for shrink)
- key transition: Full fly alignment maintained; M5 brief SQZ noise resolves

##### Step 4: TIMELINE
| From | To | Scenario | Trend / Tier | HTF state | MTF state | Source | Notes |
|------|-----|----------|--------------|-----------|-----------|--------|-------|
| 260102 01:00 | 260102 03:00 | F1 | Up / Tier 1 | W1/D1/H4 fly 511 | M30/M15 fly 511, H1 SQZ 424 | log | H1 SQZ transient — Decision 6 not met (single-bar) |
| 260102 03:00 | 260103 04:00 | F1 | Up / Tier 1 | W1/D1/H4 fly 511 | H1/M30/M15 fly 511, M5 brief 411 | img/log | Full fly restored; M5 noise resolves |

##### Step 5: Conclusion + Prediction
- **Scenario: F1** (HTF=F × MTF=F). No divergence.
- **Next likely:** S if H4 enters 513. Watch: H4 BBW_stage for first sign of shrink.

---

## Scenario S

#### Image 1 Analysis — backtested_EA_fly_2_fly_shrink.jpg
**Period:** 2026.03.30 13:00 → 2026.04.01 13:00

##### Step 1: State Read (evidence first — one table, all 7 TFs)
| TF group | TF | BBW_stage | diffMid | BBUpDn | Source (img/log) |
|----------|----|-----------|---------|--------|------------------|
| HTF | W1 | 511 | 1 | 1 | img |
| HTF | D1 | 511 | 1 | 1 | img |
| HTF | H4 | 511 | 1 | 1 | img/log (W_stage_H4:(FLY)[512], diffMid=1.0) |
| MTF | H1 | 512 | 1 | 0 | log (W_stage_H1:(FLY)[512], diffMid=1.0, BBUpDn=0) |
| MTF | M30 | 513 | 1 | 2 | log (W_stage_M30:(FLY)[513], diffMid=1.0, BBUpDn=2) |
| MTF | M15 | 513 | 5 | 2 | log (W_stage_M15:(FLY)[513], diffMid=5.0, BBUpDn=2) |
| LTF | M5 | 513 | 5 | 2 | img |

##### Step 2: Two-Axis Classification
- **HTF scenario:** F — H4/D1/W1 all fly 511/512, same direction
- **MTF scenario:** S2 — M30/M15 shrink 513, H1 still fly
- **MTF direction vs H4:** SAME → continuation (M30 diffMid=1 same as H4)

##### Step 3: Cascade
- direction: D1 compress HTF→LTF
- depth: M5 (M30/M15/M5 shrinking) | leading TF: M30 (watch for SQZ or fly resume)
- key transition: M15 transitions 511→513; D1 compression deepens from S1 to S2

##### Step 4: TIMELINE
| From | To | Scenario | Trend / Tier | HTF state | MTF state | Source | Notes |
|------|-----|----------|--------------|-----------|-----------|--------|-------|
| 260330 13:00 | 260330 14:00 | S1 | Up / Tier 2 | H4 fly 511, D1 fly 511 | M30 fly 512, M15 fly 511→513 | log | M15 enters shrink first |
| 260330 14:00 | 260330 14:30 | S2 | Up / Tier 2 | H4 fly 511 | M30 shrink 513, M15 shrink 513, M5 shrink | log | M30 also shrink — S2 confirmed |
| 260330 14:30 | 260401 13:00 | S2 | Up / Tier 2 | H4 fly 511 | M30/M15/M5 shrink 513 | img | Sustained S2; M15 briefly SQZ 425 then back to 513 |

##### Step 5: Conclusion + Prediction
- **Scenario: S2** (HTF=F × MTF=S). No divergence.
- **Next likely:** C2 if M30 enters SQZ 400-499; P if M30 returns to 511/512. Watch: M30 BBW_stage + diffBBW.

#### Image 2 Analysis — backtested_EA_fly_2_fly_shrink_zoomin.jpg
**Period:** 2026.03.30 14:30 → 2026.04.01 09:00

##### Step 1: State Read (evidence first — one table, all 7 TFs)
| TF group | TF | BBW_stage | diffMid | BBUpDn | Source (img/log) |
|----------|----|-----------|---------|--------|------------------|
| HTF | W1 | 511 | 1 | 1 | img |
| HTF | D1 | 511 | 1 | 1 | img |
| HTF | H4 | 511 | 1 | 1 | img |
| MTF | H1 | 512 | 1 | 0 | img/log |
| MTF | M30 | 513 | 1 | 2 | img/log |
| MTF | M15 | 513 | 5 | 2 | img/log |
| LTF | M5 | 513 | 5 | 2 | img |

##### Step 2: Two-Axis Classification
- **HTF scenario:** F — H4/D1 fly 511/512
- **MTF scenario:** S2 — M30/M15 shrink 513
- **MTF direction vs H4:** SAME → continuation

##### Step 3: Cascade
- direction: D1 compress HTF→LTF
- depth: M5 | leading TF: M15 (watch for FLAT→UP/DN transition)
- key transition: M15 bands converging — shrink path entry possible

##### Step 4: TIMELINE
| From | To | Scenario | Trend / Tier | HTF state | MTF state | Source | Notes |
|------|-----|----------|--------------|-----------|-----------|--------|-------|
| 260330 14:30 | 260401 05:00 | S2 | Up / Tier 2 | H4 fly 511 | M30/M15 shrink 513, M5 shrink | img | D1 sustained; M15 SQZ 425 briefly then 513 |
| 260401 05:00 | 260401 09:00 | S2 | Up / Tier 2 | H4 fly 511 | M30/M15 shrink 513 | img | M15 bands converging; entry on FLAT→UP/DN |

##### Step 5: Conclusion + Prediction
- **Scenario: S2** (HTF=F × MTF=S). No divergence.
- **Next likely:** P if M30 513→511/512; C2 if M30 513→400-499. Watch: M30 BBW_stage + M15 midtrend transition.

---

## Scenario P

#### Image 1 Analysis — backtested_EA_fly_2_shrink_2_fly.jpg
**Period:** 2026.04.03 03:00 → 2026.04.05 00:00

##### Step 1: State Read (evidence first — one table, all 7 TFs)
| TF group | TF | BBW_stage | diffMid | BBUpDn | Source (img/log) |
|----------|----|-----------|---------|--------|------------------|
| HTF | W1 | 511 | 1 | 1 | img |
| HTF | D1 | 511 | 1 | 1 | img |
| HTF | H4 | 511 | 1 | 1 | img |
| MTF | H1 | 511 | 1 | 1 | img |
| MTF | M30 | 513→400-499→511 | 3→1 | 2→1 | img |
| MTF | M15 | 513→400-499→511 | 3→1 | 2→1 | img |
| LTF | M5 | 513→400-499→511 | 3→1 | 2→1 | img |

##### Step 2: Two-Axis Classification
- **HTF scenario:** F — W1/D1/H4 fly 511, same direction
- **MTF scenario:** P2 → P3 — M30 compresses then re-expands, M15 confirms
- **MTF direction vs H4:** SAME → continuation

##### Step 3: Cascade
- direction: D1 compress HTF→LTF, then D2 expand LTF→HTF
- depth: M5 SQZ (BOTTOM) → D2 initiated at M5 | leading TF: M5 (broke SQZ)
- key transition: D1→D2 — M5 REVUP drives full re-expansion

##### Step 4: TIMELINE
| From | To | Scenario | Trend / Tier | HTF state | MTF state | Source | Notes |
|------|-----|----------|--------------|-----------|-----------|--------|-------|
| 260403 03:00 | 260403 09:00 | S2 | Up / Tier 2 | H4/H1 fly 511 | M30/M15 shrink 513 | img | D1 compression begins |
| 260403 09:00 | 260404 15:00 | C2 | Up / Tier 2 | H4/H1 fly 511 | M30/M15/M5 SQZ 400-499 | img | D1 reaches BOTTOM |
| 260404 15:00 | 260404 21:00 | P2 | Up / Tier 3 | H4/H1 fly 511 | M5 fly 511, M15 confirms | img | M5 REVUP, D2 initiated |
| 260404 21:00 | 260405 00:00 | P3 | Up / Tier 3 | H4/H1 fly 511 | M30 fly 511 | img | D2 complete |

##### Step 5: Conclusion + Prediction
- **Scenario: P2→P3** (HTF=F × MTF=P). No divergence.
- **Next likely:** F if M30 fly confirmed; S if M30 enters shrink again. Watch: M30 BBW_stage.

#### Image 2 Analysis — backtested_EA_fly_2_shrink_2_fly_zoomin.jpg
**Period:** 2026.04.04 15:00 → 2026.04.05 00:00

##### Step 1: State Read (evidence first — one table, all 7 TFs)
| TF group | TF | BBW_stage | diffMid | BBUpDn | Source (img/log) |
|----------|----|-----------|---------|--------|------------------|
| HTF | W1 | 511 | 1 | 1 | img |
| HTF | D1 | 511 | 1 | 1 | img |
| HTF | H4 | 511 | 1 | 1 | img |
| MTF | H1 | 511 | 1 | 1 | img |
| MTF | M30 | 400-499→511 | 3→1 | 0→1 | img |
| MTF | M15 | 400-499→511 | 3→1 | 0→1 | img |
| LTF | M5 | 400-499→511 | 3→1 | 0→1 | img |

##### Step 2: Two-Axis Classification
- **HTF scenario:** F — H4/D1 fly 511
- **MTF scenario:** P3 — M30 re-expands to fly 511
- **MTF direction vs H4:** SAME → continuation

##### Step 3: Cascade
- direction: D2 expand LTF→HTF
- depth: TOP — D2 complete | leading TF: M30 (confirm fly)
- key transition: M30 SQZ→fly — full D2 expansion confirmed

##### Step 4: TIMELINE
| From | To | Scenario | Trend / Tier | HTF state | MTF state | Source | Notes |
|------|-----|----------|--------------|-----------|-----------|--------|-------|
| 260404 15:00 | 260404 18:00 | P2 | Up / Tier 3 | H4/H1 fly 511 | M5 fly 511, M15 fly 511 | img | M5 REVUP, M15 confirms |
| 260404 18:00 | 260405 00:00 | P3 | Up / Tier 3 | H4/H1 fly 511 | M30 fly 511 | img | D2 complete — all fly |

##### Step 5: Conclusion + Prediction
- **Scenario: P3** (HTF=F × MTF=P3). No divergence.
- **Next likely:** F if M30 fly sustained; S if M30 enters shrink. Watch: M30 BBW_stage.

---

## Scenario B

#### Image 1 Analysis — backtested_EA_sideway_2_fly.jpg
**Period:** 2026.02.06 01:00 → 2026.02.07 21:00

##### Step 1: State Read (evidence first — one table, all 7 TFs)
| TF group | TF | BBW_stage | diffMid | BBUpDn | Source (img/log) |
|----------|----|-----------|---------|--------|------------------|
| HTF | W1 | [TO BE FILLED] | [TO BE FILLED] | [TO BE FILLED] | img |
| HTF | D1 | 513 | 1 | 2 | log (W_stage_D1:(FLY)[513], diffMid=1.0, BBUpDn=2) |
| HTF | H4 | 513 | 1 | 2 | log (W_stage_H4:(FLY)[513], diffMid=1.0, BBUpDn=2) |
| MTF | H1 | 402 | 2 | 0 | log (W_stage_H1:(SQZ)[402], diffMid=2.0, BBUpDn=0) |
| MTF | M30 | 521 | 2 | 1 | log (W_stage_M30:(FLY)[521], diffMid=2.0, BBUpDn=1) |
| MTF | M15 | 522 | 2 | 4 | log (W_stage_M15:(FLY)[522], diffMid=2.0, BBUpDn=4) |
| LTF | M5 | 400-499→521 | 3→2 | 0→1 | img |

##### Step 2: Two-Axis Classification
- **HTF scenario:** S — H4 shrink 513, D1 shrink 513
- **MTF scenario:** B1 → B2 — M5/M15 fly 521/522, M30 fly 521, H1 SQZ 402
- **MTF direction vs H4:** OPPOSITE → R1 divergence (M30 diffMid=2, H4 diffMid=1)

##### Step 3: Cascade
- direction: D2 expand LTF→HTF
- depth: M5 broke SQZ first | leading TF: M5 (broke SQZ)
- key transition: All TF SQZ → M5 breaks SQZ → D2 expansion

##### Step 4: TIMELINE
| From | To | Scenario | Trend / Tier | HTF state | MTF state | Source | Notes |
|------|-----|----------|--------------|-----------|-----------|--------|-------|
| 260206 01:00 | 260206 09:00 | C4 | Down / Tier 2 | H4 shrink 513, D1 shrink 513 | H1 SQZ 402, M30 fly 521, M15 fly 522 | log | H1 SQZ blocks; M30/M15 already fly down |
| 260206 09:00 | 260207 21:00 | B2 | Down / Tier 3 | H4 shrink 513 | M30 fly 521, M15 fly 522, H1 decompressing | img | D2 confirmed — M30 fly down |

##### Step 5: Conclusion + Prediction
- **Scenario: B2** (HTF=S × MTF=B2). Divergence: MTF direction (down) vs H4 direction (up).
- **Next likely:** B3 if H4 breaks to fly 521/522; C4 if H4 remains 513. Watch: H4 BBW_stage.

#### Image 2 Analysis — backtested_EA_sideway_2_fly_zoomin.jpg
**Period:** 2026.02.06 13:00 → 2026.02.07 09:00

##### Step 1: State Read (evidence first — one table, all 7 TFs)
| TF group | TF | BBW_stage | diffMid | BBUpDn | Source (img/log) |
|----------|----|-----------|---------|--------|------------------|
| HTF | W1 | [TO BE FILLED] | [TO BE FILLED] | [TO BE FILLED] | img |
| HTF | D1 | 513 | 1 | 2 | img |
| HTF | H4 | 513 | 1 | 2 | img |
| MTF | H1 | 513 | 2 | 2 | img |
| MTF | M30 | 521 | 2 | 1 | img |
| MTF | M15 | 521 | 2 | 1 | img |
| LTF | M5 | 521 | 2 | 1 | img |

##### Step 2: Two-Axis Classification
- **HTF scenario:** S — H4/D1 shrink 513
- **MTF scenario:** B2 — M30/M15 fly 521, H1 shrink 513
- **MTF direction vs H4:** OPPOSITE → R1 divergence

##### Step 3: Cascade
- direction: D2 expand LTF→HTF
- depth: D2 advancing | leading TF: M30 (confirm fly)
- key transition: M5/M15/M30 fly 521 — D2 confirmed in down direction

##### Step 4: TIMELINE
| From | To | Scenario | Trend / Tier | HTF state | MTF state | Source | Notes |
|------|-----|----------|--------------|-----------|-----------|--------|-------|
| 260206 13:00 | 260207 01:00 | B2 | Down / Tier 3 | H4 shrink 513 | M30/M15 fly 521, H1 shrink 513 | img | D2 expanding down |
| 260207 01:00 | 260207 09:00 | B2 | Down / Tier 3 | H4 shrink 513 | M30/M15 fly 521 | img | H4 still shrink — B2, not B3 |

##### Step 5: Conclusion + Prediction
- **Scenario: B2** (HTF=S × MTF=B2). Divergence: MTF down vs H4 up.
- **Next likely:** B3 if H4 513→521/522; S if H4 remains 513. Watch: H4 BBW_stage.

---

## Scenario V

#### Image 1 Analysis — backtested_EA_trend_reversal.jpg
**Period:** 2026.04.01 14:30 → 2026.04.02 05:00

##### Step 1: State Read (evidence first — one table, all 7 TFs)
| TF group | TF | BBW_stage | diffMid | BBUpDn | Source (img/log) |
|----------|----|-----------|---------|--------|------------------|
| HTF | W1 | [TO BE FILLED] | [TO BE FILLED] | [TO BE FILLED] | img |
| HTF | D1 | 513 | 1 | 2 | log (W_stage_D1:(FLY)[513], diffMid=1.0, BBUpDn=2) |
| HTF | H4 | 512 | 1 | 3 | log (W_stage_H4:(FLY)[512], diffMid=1.0, BBUpDn=3) |
| MTF | H1 | 512 | 1 | 0 | log (W_stage_H1:(FLY)[512], diffMid=1.0, BBUpDn=0) |
| MTF | M30 | 411 | 1 | 0 | log (W_stage_M30:(SQZ)[411], diffMid=1.0, BBUpDn=0) |
| MTF | M15 | 512 | 1 | 3 | log (W_stage_M15:(FLY)[512], diffMid=1.0, BBUpDn=3) |
| LTF | M5 | [TO BE FILLED] | [TO BE FILLED] | [TO BE FILLED] | img |

##### Step 2: Two-Axis Classification
- **HTF scenario:** S — H4 fly 512, D1 shrink 513
- **MTF scenario:** C1 — M30 SQZ 411, H1 fly 512, M15 fly 512
- **MTF direction vs H4:** SAME → continuation (M30 SQZ but diffMid=1 same as H4)

##### Step 3: Cascade
- direction: D1 compress HTF→LTF (M30 SQZ)
- depth: M30 SQZ 411 | leading TF: M30 (watch for SQZ break direction)
- key transition: F2 → R1 progression — M30 compresses between fly states

##### Step 4: TIMELINE
| From | To | Scenario | Trend / Tier | HTF state | MTF state | Source | Notes |
|------|-----|----------|--------------|-----------|-----------|--------|-------|
| 260401 14:30 | 260401 23:00 | F2 | Up / Tier 1 | H4 fly 512, D1 fly 512 | M30 fly 511, M15 fly 511 | img | All aligned up |
| 260402 00:00 | 260402 04:00 | C1 | Up / Tier 2 | H4 fly 512 | M30 SQZ 411, M15 fly 512 | log | M30 compresses — D1 deepens |
| 260402 04:00 | 260402 05:00 | C1 | Up / Tier 2 | H4 fly 512 | M30 SQZ 411, M15 fly 512 | log | M30 still SQZ — waiting break |

##### Step 5: Conclusion + Prediction
- **Scenario: C1** (HTF=S × MTF=C1). No divergence yet — M30 SQZ but diffMid=1 same as H4.
- **Next likely:** R1 if M30 breaks 411→521 (opposite H4); F if M30 breaks 411→511 (same H4). Watch: M30 BBW_stage 411→511 vs 411→521.

#### Image 2 Analysis — backtested_EA_fly_shrink_2_sideway2.jpg
**Period:** 2026.04.02 05:00 → 2026.04.03 03:00

##### Step 1: State Read (evidence first — one table, all 7 TFs)
| TF group | TF | BBW_stage | diffMid | BBUpDn | Source (img/log) |
|----------|----|-----------|---------|--------|------------------|
| HTF | W1 | [TO BE FILLED] | [TO BE FILLED] | [TO BE FILLED] | img |
| HTF | D1 | 513 | 1 | 2 | img |
| HTF | H4 | 512 | 1 | 3 | img |
| MTF | H1 | 512 | 1 | 0 | img |
| MTF | M30 | 513→411 | 1→3 | 2→0 | img |
| MTF | M15 | 513 | 5 | 2 | img |
| LTF | M5 | 513 | 5 | 2 | img |

##### Step 2: Two-Axis Classification
- **HTF scenario:** S — H4 fly 512, D1 shrink 513
- **MTF scenario:** C2 — M30 SQZ 411, M15 shrink 513
- **MTF direction vs H4:** SAME → continuation

##### Step 3: Cascade
- direction: D1 compress HTF→LTF
- depth: M30 SQZ 411 | leading TF: M30 (watch for SQZ break)
- key transition: M30 513→411 — D1 deepens to C2

##### Step 4: TIMELINE
| From | To | Scenario | Trend / Tier | HTF state | MTF state | Source | Notes |
|------|-----|----------|--------------|-----------|-----------|--------|-------|
| 260402 05:00 | 260402 17:00 | S2 | Up / Tier 2 | H4 fly 512 | M30 shrink 513, M15 shrink 513 | img | D1 compression |
| 260402 17:00 | 260403 03:00 | C2 | Up / Tier 2 | H4 fly 512 | M30 SQZ 411, M15 shrink 513 | img | M30 enters SQZ — C2 |

##### Step 5: Conclusion + Prediction
- **Scenario: C2** (HTF=S × MTF=C2). No divergence.
- **Next likely:** P2 if M30 411→511 (same dir as H4); R1 if M30 411→521 (opposite). Watch: M30 BBW_stage.

---

## Scenario C

#### Image 1 Analysis — backtested_EA_fly_shrink_2_sideway.jpg
**Period:** 2026.04.01 13:00 → 2026.04.02 17:00

##### Step 1: State Read (evidence first — one table, all 7 TFs)
| TF group | TF | BBW_stage | diffMid | BBUpDn | Source (img/log) |
|----------|----|-----------|---------|--------|------------------|
| HTF | W1 | [TO BE FILLED] | [TO BE FILLED] | [TO BE FILLED] | img |
| HTF | D1 | 513 | 1 | 2 | log (W_stage_D1:(FLY)[513], diffMid=1.0, BBUpDn=2) |
| HTF | H4 | 512 | 1 | 3 | log (W_stage_H4:(FLY)[512], diffMid=1.0, BBUpDn=3) |
| MTF | H1 | 512 | 1 | 0 | log (W_stage_H1:(FLY)[512], diffMid=1.0, BBUpDn=0) |
| MTF | M30 | 511→513→411 | 1→3→3 | 1→2→0 | img/log |
| MTF | M15 | 511→513→400-499 | 1→3→3 | 1→2→0 | img/log |
| LTF | M5 | 511→513→400-499 | 1→3→3 | 1→2→0 | img |

##### Step 2: Two-Axis Classification
- **HTF scenario:** S — H4 fly 512, D1 shrink 513
- **MTF scenario:** C2 — M30/M15/M5 SQZ 400-499
- **MTF direction vs H4:** SAME → continuation (M30 diffMid=1 same as H4)

##### Step 3: Cascade
- direction: D1 compress HTF→LTF
- depth: M5 (full SQZ) | leading TF: M5 (watch for REVUP/REVDN)
- key transition: Sequential compression — M5 first, M15 second, M30 third; G0c-SQZLOCK active

##### Step 4: TIMELINE
| From | To | Scenario | Trend / Tier | HTF state | MTF state | Source | Notes |
|------|-----|----------|--------------|-----------|-----------|--------|-------|
| 260401 13:00 | 260401 17:00 | S2 | Up / Tier 2 | H4 fly 512 | M30 shrink 513, M15 shrink 513 | img | D1 compression begins |
| 260401 17:00 | 260402 01:00 | C2 | Up / Tier 2 | H4 fly 512 | M30/M15/M5 SQZ 400-499 | img | D1 reaches BOTTOM; G0c-SQZLOCK |
| 260402 01:00 | 260402 04:00 | C2 | Up / Tier 2 | H4 fly 512 | M30 SQZ 411, M15 fly 512 | log | M30 SQZ 411 confirmed; M15 fly 512 |
| 260402 04:00 | 260402 17:00 | C2 | Up / Tier 2 | H4 fly 512 | M30 SQZ 411, M15 fly 512 | log | Sustained C2; M30 still SQZ |

##### Step 5: Conclusion + Prediction
- **Scenario: C2** (HTF=S × MTF=C2). No divergence.
- **Next likely:** P2 if M5 REVUP and M15 follows; R1 if M30 411→521 (opposite H4). Watch: M5 BBW_stage + M30 BBW_stage.

#### Image 2 Analysis — backtested_EA_fly_shrink_2_sideway_zoomin.jpg
**Period:** 2026.04.02 09:00 → 2026.04.02 17:00

##### Step 1: State Read (evidence first — one table, all 7 TFs)
| TF group | TF | BBW_stage | diffMid | BBUpDn | Source (img/log) |
|----------|----|-----------|---------|--------|------------------|
| HTF | W1 | [TO BE FILLED] | [TO BE FILLED] | [TO BE FILLED] | img |
| HTF | D1 | 513 | 1 | 2 | img |
| HTF | H4 | 512 | 1 | 3 | img |
| MTF | H1 | 521 | 2 | 1 | log (W_stage_H1:(FLY)[521], diffMid=2.0, BBUpDn=1) |
| MTF | M30 | 411→521 | 1→2 | 0→1 | log (SQZ[411]→FLY[521]) |
| MTF | M15 | 522 | 2 | 4 | log (W_stage_M15:(FLY)[522], diffMid=2.0) |
| LTF | M5 | 411→521 | 1→2 | 0→1 | img |

##### Step 2: Two-Axis Classification
- **HTF scenario:** S — H4 fly 512, D1 shrink 513
- **MTF scenario:** P2 → P3 — M30 breaks SQZ 411→521, M15 fly 522
- **MTF direction vs H4:** OPPOSITE → R1 divergence (M30 diffMid=2, H4 diffMid=1)

##### Step 3: Cascade
- direction: D2 expand LTF→HTF
- depth: M5 broke SQZ first | leading TF: M5 (broke SQZ)
- key transition: M5 SQZ break → M15 follows → M30 breaks SQZ 411→521

##### Step 4: TIMELINE
| From | To | Scenario | Trend / Tier | HTF state | MTF state | Source | Notes |
|------|-----|----------|--------------|-----------|-----------|--------|-------|
| 260402 09:00 | 260402 10:00 | P2 | Down / Tier 3 | H4 fly 512 | M5 fly 521, M15 fly 522, M30 SQZ 411 | img/log | M5 broke SQZ; M30 still SQZ |
| 260402 10:00 | 260402 17:00 | P3 | Down / Tier 3 | H4 fly 512 | M30 fly 521, M15 fly 522 | log | M30 breaks SQZ 411→521; D2 confirmed |

##### Step 5: Conclusion + Prediction
- **Scenario: P3** (HTF=S × MTF=P3). Divergence: MTF down (diffMid=2) vs H4 up (diffMid=1).
- **Next likely:** B2 if M30 fly 521 sustained; S if M30 re-enters shrink. Watch: M30 BBW_stage.

#### Image 3 Analysis — backtested_EA_fly_shrink_2_sideway2.jpg
**Period:** 2026.04.02 05:00 → 2026.04.03 03:00

##### Step 1: State Read (evidence first — one table, all 7 TFs)
| TF group | TF | BBW_stage | diffMid | BBUpDn | Source (img/log) |
|----------|----|-----------|---------|--------|------------------|
| HTF | W1 | [TO BE FILLED] | [TO BE FILLED] | [TO BE FILLED] | img |
| HTF | D1 | 513 | 1 | 2 | img |
| HTF | H4 | 512 | 1 | 3 | img |
| MTF | H1 | 512→521 | 1→2 | 0→1 | img/log |
| MTF | M30 | 513→411→521 | 1→3→2 | 2→0→1 | img/log |
| MTF | M15 | 513→411→521 | 1→3→2 | 2→0→1 | img/log |
| LTF | M5 | 513→411→521 | 1→3→2 | 2→0→1 | img |

##### Step 2: Two-Axis Classification
- **HTF scenario:** S — H4 fly 512, D1 shrink 513
- **MTF scenario:** C1→C2→P2 — full D1 cycle: shrink→SQZ→break
- **MTF direction vs H4:** OPPOSITE → R1 divergence (M30 diffMid=2, H4 diffMid=1)

##### Step 3: Cascade
- direction: D1 compress HTF→LTF, then D2 expand LTF→HTF
- depth: Full cycle — M5 SQZ (BOTTOM) → D2 initiated at M5 | leading TF: M5
- key transition: 6-zone D1 cycle — fly(1)→shrink(2)→SQZ(3-5)→release(6)

##### Step 4: TIMELINE
| From | To | Scenario | Trend / Tier | HTF state | MTF state | Source | Notes |
|------|-----|----------|--------------|-----------|-----------|--------|-------|
| 260402 05:00 | 260402 09:00 | S2 | Up / Tier 2 | H4 fly 512 | M30/M15 shrink 513 | img | Zone 2 — D1 compression |
| 260402 09:00 | 260402 15:00 | C2 | Up / Tier 2 | H4 fly 512 | M30/M15/M5 SQZ 411 | img | Zones 3-5 — SQZ peak |
| 260402 15:00 | 260402 21:00 | P2 | Down / Tier 3 | H4 fly 512 | M5 fly 521, M15 fly 522 | img | Zone 6 — M5 breaks SQZ |
| 260402 21:00 | 260403 03:00 | P3 | Down / Tier 3 | H4 fly 512 | M30 fly 521 | img | Zone 6 — M30 confirms |

##### Step 5: Conclusion + Prediction
- **Scenario: P3** (HTF=S × MTF=P3). Divergence: MTF down vs H4 up.
- **Next likely:** B2 if M30 fly 521 sustained; S if M30 re-enters shrink. Watch: M30 BBW_stage + M15 midtrend.
