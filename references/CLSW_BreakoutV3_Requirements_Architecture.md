# CLSW breakout V3

Nov 3, 2026 · @terry pang

## At a glance

V3 marks when a midline-cluster sideway is ready to break (Ready), what kind it is (type T1–T4) and how tight the squeeze is (strong 1–4, numbered by the timeframe hi: 1 M15, 2 M30, 3 H1, 4 H4). It is `SL_MidCluster_Breakout_V3.mqh`; there are no breakout stages yet.

| Part | Answers | February replay (V38.35.16\_2, your 37 breakouts) |
| --- | --- | --- |
| Ready | when is it squeezed enough to break? | Ready before 33 / 37; 76 % of Ready bars inside your sideways |
| Type | what kind of sideway? | your type on 31 / 33 |
| Strong (rule C) | how tight, at which timeframe? | 290 strong bars, 84 % inside your sideways, a strong within 6 h before 24 / 37 |

**What V3 changes from V2** (all behind inputs, all on by default):

| Change | Input | Why (your chart) |
| --- | --- | --- |
| Strong 1 is a sequence: M15 band shrank → M5–M15 very close → M5 sideway 2+ bars with a quiet slope + M30 band shrinking, not while M30 still closes in | `CLSW_S1Seq`, `CLSW_S1Close`, `CLSW_S1M5Run`, `CLSW_S1M5Quiet` | 6 Feb 23:15–23:45; not 9 Feb 04:30, not 3 Feb 23:20 |
| Strong 2 also by a sequence: M15 sideway-ish + M5 sideway 2+ bars, quiet + M30 band shrinking | `CLSW_S2Seq` | 11 Feb 11:25–11:40 |
| Strong is checked at every timeframe M15 is clustered with, not only the highest | — | 13 Feb 11:20 (M15 on M30 and H1) |
| Each grade needs M15 or M5 sideway on that bar: strong 1, 4 M15; strong 2, 3 M5 run or M15 | `CLSW_StrongNeedM15` | 26 Feb 07:00 / 16:55 removed; 23 Feb 15:20 kept |
| Strong without a Ready (tested, off) | `CLSW_StrongNoReady` = 0 | strong 1 already needs M5 sideway, which is a Ready |

## Each M5 bar

`SL_MidCluster_Breakout` runs once per new M5 bar and calls the steps below in this order. Every rule reads either a state on this bar or evidence seen since the reset (the bar the gate opened); nothing uses a clock.

| # | Function | Does |
| --- | --- | --- |
| 1 | `SL_CLUpdateGaps` | V3's own midline gaps `g_clsw_cl[lo][hi][k]` from BBMidLV, refreshed like `BBDatas_Midline_Cluster` (does not read `ctx.cl`, whose H4 slots read 0) |
| 2 | `SL_CLUpdateHist` | touch times, M5 sideway run, M5 diffMid reversal, last 3 different values of each neighbour gap ("closing") |
| 3 | `SL_CLSW_Type` | gate + reset, ladder, strong-1 memory, type inputs |
| 4 | `SL_CLSW_Ready` | Ready A / B / T4, type and level; on Ready A or B calls `SL_CLSetStrong` |
| 5 | `SL_CLLog`, `SL_CLDebugMem` | `[CLSW2]`, `[CLCHK]`, `[CLMEM]` lines |
| 6 | `SL_CLDraw`, `SL_CLDrawABC` | Ready circle + type number; A / B / C strong labels |

```mermaid
sequenceDiagram
    autonumber
    participant MCB as SL_MidCluster_Breakout (V3)
    participant GAP as SL_CLUpdateGaps
    participant MEM as SL_CLUpdateHist
    participant TYP as SL_CLSW_Type
    participant RDY as SL_CLSW_Ready
    participant STR as SL_CLSetStrong
    participant G as g_clsw (state)
    participant OUT as SL_CLLog and SL_CLDraw

    MCB->>MCB: new M5 bar? no - return
    MCB->>GAP: own midline gaps g_clsw_cl (M5 pairs every bar, M15 / M30 / H1 pairs on their new bar)
    MCB->>MEM: touch times, M5 sideway run, M5 diffMid reversal, last 3 values of each neighbour gap
    MCB->>TYP: SL_CLGateOpen, SL_CLLadder, SL_CLS1Track, SL_CLFindCandidates
    TYP->>G: gate, step (ladder), strong-1 memory, cand, m30_dir, fly_dir, fly_lo
    opt gate closed
        TYP-->>MCB: nothing else runs this bar
    end
    MCB->>RDY: SL_CLSW_Ready
    RDY->>G: ready, ready_now, ready_type, ready_lvl (log RA / RB / R4)
    opt Ready A or B
        RDY->>STR: strong at the Ready level and every TF M15 is clustered with above it
        STR->>G: strong_a, strong_b, strong_c, ready_strong 1-4 (log S1-S4)
    end
    MCB->>OUT: CLSW2 and CLCHK lines, Ready circle and type number, A / B / C strong labels
```

## Gate, ladder and type inputs

The gate decides whether a sideway exists; the ladder and the type inputs are kept from the gate opening (the reset) until it closes.

| Step | Rule | Function |
| --- | --- | --- |
| Gate | opens when the ladder `sw_sl_state ≥ 0` (or a midline cluster with `CLSW_GateCluster`); closes after 2 bars without; opening = the reset, which clears Ready, type, strong, ladder and strong-1 memory | `SL_CLGateOpen`, `SL_CLSW_Clear` |
| Ladder | since the reset each TF goes sideway-ish after the one below: M5 → M15 → M30 → H1; `step` = highest reached (−1 none), several on one bar allowed, never goes down | `SL_CLLadder` |
| Sideway-ish | midtrend sideway (`dmtsw ≥ 3`), weak midtrend 4 / 5, or flat by diffMid (`CLSW_FlatDiffMid`): \|diffMid\| ≤ M5 0.33 / M15 0.6 / M30 0.7 / H1 0.8 / H4 0.9, or ≤ ½ of the bigger of the 2 bars before, or diffMid changed sign | `SL_CLSideIsh`, `SL_CLFlat` |
| Strong-1 memory | since the reset: the M15 band shrank (`m15shr`), then M5–M15 came within 2.25 (`close`) | `SL_CLS1Track` |
| Type inputs | T3: H1 and H4 sideway now, no fly · T1r: M5–M15 ≤ 5 since the reset and M30 trending now (`m30_dir`) · T2: a fly now, H1H4 else M30H1 (`fly_dir`, `fly_lo`) · T1l: M5–M15 touched since the reset and ladder reached M15 · T4: M5 sideway since the reset | `SL_CLFindCandidates` |

The type inputs are recomputed every bar (`CLSW_LatchCand` = false) and only read at a Ready bar to pick one type.

## Ready and type

Ready is checked every gate bar; the first of A, B, T4 that passes sets Ready, type and level, and the latest A or B Ready since the reset decides `ready_type` and `ready_lvl`.

| Ready | Passes when | Level | Type |
| --- | --- | --- | --- |
| A — M5 cluster | M5 event (M5 midtrend sideway, or M5 diffMid just reversed) **and** M5 within CL\_SW of a higher TF: M15 9, M30 3, H1 4, H4 3.1 | highest such TF | type table below |
| B — M15 cluster | no A; M5 **and** M15 midtrend sideway **and** M15 within CL\_SW of a higher TF: M30 5, H1 2, H4 1 | highest such TF | T3 if T3 input, T2 if a fly, else the table |
| T4 — nothing near | no A or B; M5 midtrend sideway 3 bars in a row (`CLSW_T4MinRun`) and every M5 / M15 gap above 2 × its CL\_SW | M5 | T4, only while no A or B Ready since the reset |
| none | near-misses, a short M5 flicker, or no M5 sideway | — | type and level kept |

**Type at Ready A** — first match wins; `dir` = sign of M5 diffMid on the Ready bar.

| Order | Type | When |
| --- | --- | --- |
| 1 | T3 | T3 input |
| 2 | T1 | T1r input and `dir` against M30 |
| 3 | T1 or T2 | T2 input and `dir` with the fly: T1 if M5’s cluster TF is one of the fly’s TFs, else T2 |
| 4 | T1 | T1l input |
| 5 | T2 | T2 input |
| 6 | T1 | T1r input |
| 7 | T4 | nothing above |

```mermaid
sequenceDiagram
    autonumber
    participant MCB as SL_MidCluster_Breakout
    participant RDY as SL_CLSW_Ready
    participant EV as SL_CLM5Event
    participant CL as SL_CLM5Cluster and SL_CLM15Cluster
    participant TY as SL_CLConfirmType and SL_CLConfirmTypeB
    participant NN as SL_CLNothingNear
    participant STR as SL_CLSetStrong
    participant G as g_clsw (state)

    MCB->>RDY: once per new M5 bar
    RDY->>G: ready_now = 0, strong_now = false
    opt gate = 0
        RDY-->>MCB: return, not Ready
    end
    RDY->>EV: M5 event? M5 midtrend sideway, or M5 diffMid just reversed
    RDY->>CL: lvl = highest TF within CL_SW of M5 (M15 9, M30 3, H1 4, H4 3.1)
    RDY->>CL: lvl15 = highest TF within CL_SW of M15 (M30 5, H1 2, H4 1)
    alt A - M5 event and lvl M15 or higher
        RDY->>TY: SL_CLConfirmType(cand, lvl), dir = sign of M5 diffMid
        RDY->>G: Ready, ready_type, ready_lvl = lvl (log RA)
        RDY->>STR: SL_CLSetStrong(lvl, lvl15)
    else B - M5 and M15 sideway and lvl15 M30 or higher
        RDY->>TY: SL_CLConfirmTypeB(cand) - T3, else T2 if a fly, else the table
        RDY->>G: Ready, ready_type, ready_lvl = lvl15 (log RB)
        RDY->>STR: SL_CLSetStrong(lvl15)
    else T4 - M5 sideway 3 bars in a row and nothing near
        RDY->>NN: every M5 and M15 gap above 2 x its CL_SW?
        RDY->>G: Ready, type T4 at M5 only if no A or B since the reset (log R4)
    else none
        RDY->>G: not Ready this bar, type, level and strong kept
    end
```

## Strong

Strong grades how tight the squeeze is on a Ready A or B bar; the number is hi, the timeframe being squeezed onto. It never changes Ready, type or level.

**When it is checked**

| # | Action | Debug |
| --- | --- | --- |
| 1 | No Ready A or B on this bar → no strong check (`CLSW_StrongNoReady` = 0) | — |
| 2 | Ready A: check at the Ready level (highest TF M5 is clustered with), plus every TF M15 is clustered with above it | `M15 on M30:` / `M15 on H1:` |
| 3 | Ready B: check at the Ready level (M15’s highest cluster) | — |
| 4 | Level M15 → strong 1, M30 → strong 2, H1 → strong 3, H4 → strong 4 (sections below) | `S1seq` / `S2seq` / `S2:M30` / `S3:H1` |
| 5 | Drop each grade that lacks its need (next table), per level | `NEED:` |
| 6 | Each rule (A, B, C) keeps its highest grade of the bar | — |
| 7 | Keep it until the next reset (last table) | `_S1` … `_S4` |

**What each grade needs on that bar** (`CLSW_StrongNeedM15`)

| Grade | hi | Needs | “Sideway-ish” / “run” |
| --- | --- | --- | --- |
| 1 | M15 | M15 sideway-ish | sideway-ish = midtrend sideway, weak 4 / 5, or flat by diffMid |
| 2 | M30 | M5 run **or** M15 sideway-ish | run = M5 midtrend sideway 2+ bars in a row (`CLSW_S1M5Run`) |
| 3 | H1 | M5 run **or** M15 sideway-ish |  |
| 4 | H4 | M15 sideway-ish |  |

**Keeping the grade**

| # | Action | Input |
| --- | --- | --- |
| 1 | Each rule keeps its own grade: `strong_a`, `strong_b`, `strong_c` (log `A/B/C:x/y/z`) | — |
| 2 | `ready_strong` follows rule C | `CLSW_StrongMode` = 2 |
| 3 | A new strong replaces the kept one: latest wins (0) or only a higher TF wins (1) | `CLSW_StrongKeep` = 0 |
| 4 | Kept until the gate reopens | — |
| 5 | An A / B / C label is drawn when a rule’s kept grade changes | `CLSW_DrawStrongABC` |

## Strong 1 (hi M15)

Strong 1 is a sequence since the gate opened: M15’s band shrinks, M5 comes onto M15, then M5 goes quietly sideway while M30 is still squeezing — and not while M30 is still closing in on M15 (6 Feb 23:15–23:45 → breakout 23:50). All three rules (A, B, C) give the same answer.

| # | Action | Checked | Input | Debug |
| --- | --- | --- | --- | --- |
| 1 | The M15 band shrinks (`BB_diffBBW` < 0) | any bar since the reset, remembered | — | `m15shr:Y` |
| 2 | Then the M5–M15 gap comes within 2.25 | any bar after step 1, remembered | `CLSW_S1Close` | `close:Y` |
| 3 | A Ready A with M5 on M15 (M5–M15 ≤ 9); Ready B and the M15 loop start at M30, so they never give strong 1 | this bar | — | `RA` / `RB` |
| 4 | M5 midtrend sideway 2+ bars in a row | this bar | `CLSW_S1M5Run` | `m5sw:Y(run 2)` |
| 5 | M5 slope quiet: \|M5 diffMid\| ≤ 0.33, or smaller than the bar before | this bar | `CLSW_S1M5Quiet`, `CLSW_S1M5Dmid` | `m5quiet:Y(0.14)` |
| 6 | The M30 band is shrinking | this bar | — | `m30shr:Y` |
| 7 | Wait: M15–M30 closing **and** M30 band shrinking → no strong 1 | this bar | `CLSW_StrongWait1` | `WAIT:M30 still closing in` |
| 8 | Need: M15 sideway-ish | this bar | `CLSW_StrongNeedM15` | `NEED:` |
| 9 | All pass → strong 1 | — | `CLSW_S1Seq` | `-> S1`, `_S1` |

```mermaid
sequenceDiagram
    participant HIST as SL_CLUpdateHist
    participant TYP as SL_CLSW_Type
    participant TRK as SL_CLS1Track
    participant RDY as SL_CLSW_Ready
    participant SET as SL_CLSetStrong
    participant AT as SL_CLStrongAt
    participant ABC as SL_CLStrongABC
    participant M1 as SL_CLStrongM15H1
    participant NEED as SL_CLStrongNeedOK

    HIST->>HIST: every bar - g_clsw_m5_run, last 3 values of each gap
    TYP->>TRK: gate open - after SL_CLLadder
    TRK->>TRK: step 1 - M15 diffBBW below 0 - g_clsw_s1_m15shr = true
    TRK->>TRK: step 2 - m15shr and M5-M15 ≤ 2.25 - g_clsw_s1_close = true
    RDY->>RDY: step 3 - SL_CLM5Event and SL_CLM5Cluster = M15 (M5-M15 ≤ 9)
    Note over RDY,SET: strong 1 only comes from a Ready A at M15 - Ready B and the M15 loop start at M30
    RDY->>SET: SL_CLSetStrong(1, lvl15)
    SET->>AT: SL_CLStrongAt(1)
    AT->>ABC: SL_CLStrongABC(1)
    ABC->>ABC: step 4 - SL_CLSw(M5) and m5_run ≥ 2
    ABC->>ABC: step 5 - abs M5 diffMid ≤ 0.33 or smaller than last bar
    ABC->>ABC: step 6 - SL_CLBandShrink(M30)
    ABC->>ABC: step 7 wait - SL_CLGapShrinking(M15-M30) and SL_CLBandShrink(M30)
    ABC-->>AT: steps 1-6 pass, no wait - 1, 1, 1 (log S1seq ... S1)
    AT->>M1: SL_CLStrongM15H1
    M1-->>AT: H1 flat and M15 on H1 - becomes 3, not 1
    AT-->>SET: sa, sb, sc
    SET->>NEED: step 8 via SL_CLStrongNeed - grade 1 needs SL_CLSideIsh(M15)
    NEED-->>SET: no - becomes 0 (log NEED)
    opt M15 also clustered with M30, H1 or H4 (lvl15)
        SET->>AT: SL_CLStrongAt(tf) - strong 2, 3 or 4 there beats 1
    end
    SET->>SET: step 9 - SL_CLKeep, grade by CLSW_StrongMode, ready_strong = 1 (log _S1)
```

Examples: 6 Feb 23:15 strong 1 (run 2, slope 0.14, M30 −20.7); 24 Feb 11:00–12:25 waits (M15–M30 13.6 → 3.7, M30 −21 → −55); 3 Feb 23:20 no (run 1); 9 Feb 04:30 no (M5 trending).

## Strong 2 (hi M30)

Strong 2 is checked when the Ready is at M30 or M15 sits on M30 (≤ 5), and passes by either route: your sequence (M15 sideway, M5 quietly sideway, M30 squeezing) or rules A / B / C at M30.

**Route 1 — sequence** (`CLSW_S2Seq`)

| # | Action | Debug |
| --- | --- | --- |
| 1 | A Ready at M30, or M15 within 5 of M30 | `RA:…M30` / `M15 on M30:` |
| 2 | M15 sideway-ish | `m15sw:Y` |
| 3 | M5 midtrend sideway 2+ bars in a row with a quiet slope (same test as strong 1, steps 4–5) | `m5quietSw:Y(run 3,0.02)` |
| 4 | The M30 band is shrinking | `m30shr:Y` |
| 5 | All pass → strong 2 for A, B and C | `-> S2` |

**Route 2 — rules A / B / C at M30** (below = M15, step = H1; see Rules A / B / C).

**Then for both routes**

| # | Action | Debug |
| --- | --- | --- |
| 6 | Need: M5 sideway 2+ bars **or** M15 sideway-ish | `NEED:` |
| 7 | Keep the highest grade of the bar per rule | `_S2` |

```mermaid
sequenceDiagram
    participant HIST as SL_CLUpdateHist
    participant RDY as SL_CLSW_Ready
    participant SET as SL_CLSetStrong
    participant AT as SL_CLStrongAt
    participant ABC as SL_CLStrongABC
    participant M5Q as SL_CLM5QuietSw
    participant M1 as SL_CLStrongM15H1
    participant NEED as SL_CLStrongNeedOK

    HIST->>HIST: every bar - g_clsw_m5_run, last 3 values of M15-M30 and M30-H1
    alt Ready A, M5's highest cluster M30 (≤ 3)
        RDY->>SET: SL_CLSetStrong(2, lvl15)
        SET->>AT: SL_CLStrongAt(2)
    else Ready A, M5 on M15 and M15 on M30 (≤ 5)
        RDY->>SET: SL_CLSetStrong(1, lvl15)
        SET->>AT: SL_CLTouch(M15, M30) yes - SL_CLStrongAt(2), log M15 on M30
    else Ready B, M15 on M30 (≤ 5)
        RDY->>SET: SL_CLSetStrong(2, -1)
        SET->>AT: SL_CLStrongAt(2)
    end
    AT->>ABC: SL_CLStrongABC(2) - below M15, hi M30, step H1
    ABC->>ABC: lad - g_clsw.step ≥ 2 (ladder reached M30)
    ABC->>ABC: pinch - SL_CLGapShrinking(M15-M30) and gap ≤ 2.5
    ABC->>ABC: bands - SL_CLBandShrink(M30) and SL_CLBandShrink(H1)
    ABC->>ABC: step_cl - SL_CLGapShrinking(M30-H1), step_band - SL_CLBandShrink(H1)
    ABC->>ABC: route 2 - rules A, B, C = 2 or 0
    ABC->>ABC: route 1 (CLSW_S2Seq) - SL_CLSideIsh(M15)?
    ABC->>M5Q: and M5 sideway 2+ bars with a quiet slope?
    M5Q-->>ABC: true / false
    ABC->>ABC: and SL_CLBandShrink(M30)? all yes - 2, 2, 2 (log S2seq ... S2)
    ABC-->>AT: sa, sb, sc
    AT->>M1: SL_CLStrongM15H1
    M1-->>AT: yes - becomes 3
    AT-->>SET: sa, sb, sc
    SET->>NEED: via SL_CLStrongNeed - grade 2 needs M5 run ≥ 2 OR SL_CLSideIsh(M15)
    NEED-->>SET: no - becomes 0 (log NEED)
    SET->>SET: highest per rule over levels, SL_CLKeep, ready_strong = 2 (log _S2)
```

Examples: 11 Feb 11:25–11:40 (route 1: M5 on M30 2.5, run 2–5, M30 shrinking); 13 Feb 11:20 (route 1 via M15 on M30 4.2); 4 Feb 01:10 and 23 Feb 15:15 (route 2); 23 Feb 15:20–15:55 kept by the M5 run while M15 trends up.

## Strong 3 (hi H1)

Strong 3 is checked when the Ready is at H1 or M15 sits on H1 (≤ 2), and passes by rules A / B / C at H1 or by M15 sitting on a flat H1 — the second route runs at every checked level and ignores the ladder.

**Route 1 — rules A / B / C at H1** (below = M30, step = H4; see Rules A / B / C).

**Route 2 — M15 on H1** (`CLSW_StrongM15H1`)

| # | Action | Debug |
| --- | --- | --- |
| 1 | H1 flat by diffMid: \|diffMid\| ≤ 0.8, or ≤ ½ of the bigger of the 2 bars before, or a sign change | `H1flat:Y` |
| 2 | M15 sideway-ish | `M15:Y` |
| 3 | M15–H1 gap between 0 and 1 (½ of CL\_SW 2) | `gap:0.0` |
| 4 | All pass → strong 3 for A, B and C, over any lower grade | `S3m15h1` |

**Then for both routes**

| # | Action | Debug |
| --- | --- | --- |
| 5 | Need: M5 sideway 2+ bars **or** M15 sideway-ish | `NEED:` |
| 6 | Keep the highest grade of the bar per rule | `_S3` |

```mermaid
sequenceDiagram
    participant RDY as SL_CLSW_Ready
    participant SET as SL_CLSetStrong
    participant AT as SL_CLStrongAt
    participant ABC as SL_CLStrongABC
    participant M1 as SL_CLStrongM15H1
    participant NEED as SL_CLStrongNeedOK

    alt Ready A, M5's highest cluster H1 (≤ 4)
        RDY->>SET: SL_CLSetStrong(3, lvl15)
    else Ready A, M15 on H1 (≤ 2) above M5's level
        RDY->>SET: SL_CLSetStrong(lvl, lvl15) - the loop reaches H1
    else Ready B, M15 on H1 (≤ 2)
        RDY->>SET: SL_CLSetStrong(3, -1)
    end
    SET->>AT: SL_CLStrongAt(3)
    AT->>ABC: route 1 - SL_CLStrongABC(3) - below M30, hi H1, step H4
    ABC->>ABC: lad - g_clsw.step ≥ 3 (ladder reached H1)
    ABC->>ABC: pinch - SL_CLGapShrinking(M30-H1) and gap ≤ 2
    ABC->>ABC: bands - SL_CLBandShrink(H1) and SL_CLBandShrink(H4)
    ABC->>ABC: step_cl - SL_CLGapShrinking(H1-H4), step_band - SL_CLBandShrink(H4)
    ABC-->>AT: rules A, B, C = 3 or 0 (log S3:H1)
    Note over AT,M1: route 2 runs inside SL_CLStrongAt at EVERY level, so a Ready at M15 or M30 can also give strong 3
    AT->>M1: route 2 - SL_CLStrongM15H1
    M1->>M1: SL_CLFlat(H1), M15 SL_CLSw or SL_CLFlat or SL_CLSideIsh, gap M15-H1 ≤ 1
    M1-->>AT: all yes - 3, 3, 3 (log S3m15h1)
    AT-->>SET: sa, sb, sc
    SET->>NEED: via SL_CLStrongNeed - grade 3 needs M5 run ≥ 2 OR SL_CLSideIsh(M15)
    NEED-->>SET: no - becomes 0 (log NEED)
    SET->>SET: highest per rule over levels, SL_CLKeep, ready_strong = 3 (log _S3)
```

Examples: 2 Feb 23:20 (route 2: H1 diffMid −1.53 after −6.36, M15–H1 0.0, M30 still 29 away); 3 Feb 01:15 keeps it. Strong 3 is the second-noisiest grade (68 % inside your sideways).

## Strong 4 (hi H4)

Strong 4 is a Ready at H4 judged by the squeeze under it: H1–H4 has no CL\_SW, so the H1 checks run and any pass is relabelled 4 (`CLSW_StrongH4Fall`).

| # | Action | Debug |
| --- | --- | --- |
| 1 | A Ready at H4: M5–H4 ≤ 3.1, or M15–H4 ≤ 1 | `_CH4` / `_C15H4` |
| 2 | Run the strong 3 checks at H1 (both routes) | `[hi H4 -> H1 checks]` |
| 3 | Any rule passes → its grade becomes 4 | — |
| 4 | Need: M15 sideway-ish | `NEED:` |
| 5 | Keep it | `_S4` |

```mermaid
sequenceDiagram
    participant RDY as SL_CLSW_Ready
    participant SET as SL_CLSetStrong
    participant AT as SL_CLStrongAt
    participant ABC as SL_CLStrongABC
    participant M1 as SL_CLStrongM15H1
    participant NEED as SL_CLStrongNeedOK

    alt Ready A, M5 on H4 (≤ 3.1)
        RDY->>SET: SL_CLSetStrong(4, lvl15)
    else Ready A, M15 on H4 (≤ 1) above M5's level
        RDY->>SET: SL_CLSetStrong(lvl, 4) - the loop reaches H4
    else Ready B, M15 on H4 (≤ 1)
        RDY->>SET: SL_CLSetStrong(4, -1)
    end
    SET->>AT: SL_CLStrongAt(4)
    alt CLSW_StrongH4Fall off
        AT-->>SET: 0, 0, 0 - no strong 4
    end
    AT->>AT: lvl = 3 (log hi H4 to H1 checks)
    AT->>ABC: SL_CLStrongABC(3) - same checks as strong 3 route 1
    ABC-->>AT: 3 or 0 per rule
    AT->>M1: SL_CLStrongM15H1 - same as strong 3 route 2
    M1-->>AT: yes - 3, 3, 3
    AT->>AT: every non-zero grade becomes 4
    AT-->>SET: sa, sb, sc
    SET->>NEED: via SL_CLStrongNeed - grade 4 needs SL_CLSideIsh(M15)
    NEED-->>SET: no - becomes 0 (log NEED)
    SET->>SET: highest per rule over levels, SL_CLKeep, ready_strong = 4 (log _S4)
```

Example: 27 Feb from 13:50 (M5 on H4, M30–H1 1.1 and closing, H1 and H4 bands shrinking, M15 sideway-ish from 13:50) → breakout 14:45. Strong 4 is the weakest grade: 17 bars, mostly 26 Feb, outside your sideways.

## Rules A / B / C and SL\_CLSetStrong

Rules A / B / C are route 2 of strong 2 and route 1 of strong 3 (and so of strong 4). For hi = M30 or H1: below = the TF under hi, step = the TF above.

| # | Check | Debug |
| --- | --- | --- |
| 1 | Ladder reached hi | `lad:Y` |
| 2 | Pinch: gap (below, hi) closing — its last 3 different values each smaller — and ≤ ½ CL\_SW | `pinch:Y` |
| 3 | Bands: the hi band and the step band both shrinking (stage 513 / 523 or diffBBW < 0) | `bands:Y` |
| 4 | Step closing: gap (hi, step) closing | `step<:Y` |
| 5 | Step band: the step band shrinking | `stepBand:Y` |
| → | **A** = 1 + 2 + 3 · **B** = A, or 1 + 4 · **C** = A, or 1 + 4 + 5 | `-> A? B? C?` |

`SL_CLSetStrong` puts the levels, the needs and the keeping together:

```mermaid
sequenceDiagram
    autonumber
    participant RDY as SL_CLSW_Ready
    participant SET as SL_CLSetStrong
    participant AT as SL_CLStrongAt
    participant NEED as SL_CLStrongNeed
    participant KP as SL_CLKeep
    participant G as g_clsw
    participant DR as SL_CLDrawABC

    RDY->>SET: SL_CLSetStrong(lvl, lvl2) on a Ready A or B
    SET->>AT: grades at lvl (the Ready level)
    AT-->>SET: A, B, C
    SET->>NEED: drop any grade that lacks its M15 / M5 need
    loop every TF from lvl+1 to lvl2 that M15 is clustered with
        SET->>AT: grades at that TF (log M15 on TF)
        SET->>NEED: drop any grade that lacks its need
        SET->>SET: each rule keeps its higher grade
    end
    SET->>KP: strong_a, strong_b, strong_c = SL_CLKeep(old, new)
    KP-->>SET: latest non-zero (CLSW_StrongKeep 0) or the higher TF (1)
    SET->>SET: grade = rule C (CLSW_StrongMode 2)
    alt grade 0
        SET-->>RDY: ready_strong kept
    else grade 1 to 4
        SET->>G: ready_strong, ready_strong_t (log _S grade)
    end
    DR->>G: after the log - a rule's kept grade changed?
    DR->>DR: draw A n, B n, C n labels above the M5 band
```

## Strong call chain

How the strong functions call each other on one M5 bar. The first diagram is the whole chain; the next six open one function each. A solid arrow is a call or a check, a dashed arrow is what comes back.

| Function | Called by | Calls | Returns |
| --- | --- | --- | --- |
| SL\_CLSetStrong | SL\_CLSW\_Ready (Ready A / B) | SL\_CLStrongAt, SL\_CLStrongNeed, SL\_CLTouch, SL\_CLKeep | nothing; writes strong\_a / b / c, ready\_strong, g\_clsw\_strong\_now |
| SL\_CLStrongAt | SL\_CLSetStrong | SL\_CLStrongABC, SL\_CLStrongM15H1 | sa, sb, sc at one level (H4 → H1 checks, relabelled 4) |
| SL\_CLStrongABC | SL\_CLStrongAt | SL\_CLGapShrinking, SL\_CLBandShrink, SL\_CLSw, SL\_CLSideIsh, SL\_CLM5QuietSw | sa, sb, sc = 0 or the grade (S1 sequence, rules A / B / C, S2 sequence) |
| SL\_CLStrongM15H1 | SL\_CLStrongAt (every level) | SL\_CLFlat, SL\_CLSw, SL\_CLSideIsh | true → all three rules = 3 |
| SL\_CLStrongNeed / SL\_CLStrongNeedOK | SL\_CLSetStrong (per level) | SL\_CLSideIsh (→ SL\_CLFlat, SL\_CLSw), SL\_CLSw | grades that lack their need set to 0 |
| SL\_CLM5QuietSw | SL\_CLStrongABC (strong 2 sequence) | SL\_CLSw; reads g\_clsw\_m5\_run from SL\_CLUpdateHist | true when M5 is sideway 2+ bars with a quiet slope, plus d0 |

### Whole chain

```mermaid
sequenceDiagram
    autonumber
    participant TYP as SL_CLSW_Type
    participant RDY as SL_CLSW_Ready
    participant SET as SL_CLSetStrong
    participant AT as SL_CLStrongAt
    participant ABC as SL_CLStrongABC
    participant M5Q as SL_CLM5QuietSw
    participant M1 as SL_CLStrongM15H1
    participant NEED as SL_CLStrongNeed
    participant OK as SL_CLStrongNeedOK
    participant KP as SL_CLKeep

    Note over TYP: earlier on the same bar, gate open
    TYP->>TYP: SL_CLLadder - g_clsw.step
    TYP->>TYP: SL_CLS1Track - g_clsw_s1_m15shr, g_clsw_s1_close
    RDY->>RDY: SL_CLM5Cluster - lvl, SL_CLM15Cluster - lvl15
    alt Ready A
        RDY->>SET: SL_CLSetStrong(lvl, lvl15)
    else Ready B
        RDY->>SET: SL_CLSetStrong(lvl15, -1)
    end
    SET->>AT: SL_CLStrongAt(lvl)
    AT->>ABC: SL_CLStrongABC(lvl, or 3 when lvl is H4)
    opt lvl = 2 (M30), strong 2 sequence
        ABC->>M5Q: M5 quiet sideway?
        M5Q-->>ABC: true / false
    end
    ABC-->>AT: sa, sb, sc
    AT->>M1: SL_CLStrongM15H1 (at every level)
    M1-->>AT: true - all three = 3
    AT-->>SET: sa, sb, sc (non-zero becomes 4 when lvl is H4)
    SET->>NEED: SL_CLStrongNeed(sa, sb, sc)
    loop each non-zero grade
        NEED->>OK: SL_CLStrongNeedOK(grade)
        OK-->>NEED: true keeps it, false sets it to 0
    end
    loop every TF from lvl+1 to lvl2 that M15 touches
        SET->>AT: SL_CLStrongAt(tf) - same path as above
        SET->>NEED: SL_CLStrongNeed - same as above
        SET->>SET: each rule keeps the higher grade
    end
    SET->>KP: SL_CLKeep for strong_a, strong_b, strong_c, ready_strong
    KP-->>SET: kept grade
```

### SL\_CLSetStrong

The top of the chain. It grades the Ready level, then every higher TF that M15 is clustered with, keeps the highest grade per rule, and writes the kept grades.

```mermaid
sequenceDiagram
    autonumber
    participant RDY as SL_CLSW_Ready
    participant SET as SL_CLSetStrong
    participant AT as SL_CLStrongAt
    participant NEED as SL_CLStrongNeed
    participant TCH as SL_CLTouch
    participant KP as SL_CLKeep
    participant G as g_clsw

    RDY->>SET: (lvl, lvl2, only1 = false)
    SET->>AT: SL_CLStrongAt(lvl)
    AT-->>SET: sa, sb, sc
    SET->>NEED: SL_CLStrongNeed(sa, sb, sc)
    NEED-->>SET: a grade that lacks its need becomes 0
    opt lvl2 above lvl (Ready A only)
        loop tf = lvl+1 to lvl2
            SET->>TCH: gap M15-tf within CL_SW? (M30 5, H1 2, H4 1)
            alt no
                TCH-->>SET: skip this tf
            else yes
                SET->>AT: SL_CLStrongAt(tf) - log M15 on tf
                AT-->>SET: ta, tb, tc
                SET->>NEED: SL_CLStrongNeed(ta, tb, tc)
                SET->>SET: sa = max(sa, ta), sb = max(sb, tb), sc = max(sc, tc)
            end
        end
    end
    opt only1 (no-Ready bars, CLSW_StrongNoReady 1)
        SET->>SET: any grade other than 1 becomes 0
    end
    SET->>G: any grade non-zero - g_clsw_strong_now = true
    SET->>KP: strong_a, strong_b, strong_c = SL_CLKeep(old, new)
    SET->>SET: grade = sa, sb or sc by CLSW_StrongMode (0 A, 1 B, 2 C)
    alt grade 0
        SET-->>RDY: return, ready_strong kept
    else grade 1 to 4
        SET->>KP: SL_CLKeep(ready_strong, grade)
        KP-->>SET: latest (CLSW_StrongKeep 0) or higher TF (1)
        SET->>G: ready_strong, ready_strong_t (log _S grade)
    end
```

### SL\_CLStrongAt

Grades one level. H4 has no level above it to squeeze into, so it borrows the H1 checks and relabels the result 4. The M15-on-H1 route runs after rules A / B / C at every level, and wins.

```mermaid
sequenceDiagram
    autonumber
    participant SET as SL_CLSetStrong
    participant AT as SL_CLStrongAt
    participant ABC as SL_CLStrongABC
    participant M1 as SL_CLStrongM15H1

    SET->>AT: (lvl)
    AT->>AT: sa = sb = sc = 0
    alt lvl = 4 (H4) and CLSW_StrongH4Fall off
        AT-->>SET: return 0, 0, 0
    else lvl = 4 and CLSW_StrongH4Fall on
        AT->>AT: lvl = 3 (log hi H4 to H1 checks)
    end
    AT->>ABC: SL_CLStrongABC(lvl)
    ABC-->>AT: sa, sb, sc (each 0 or lvl)
    AT->>M1: SL_CLStrongM15H1()
    M1-->>AT: true - sa = sb = sc = 3 (wins over 1 or 2)
    opt lvl was 4
        AT->>AT: each non-zero grade becomes 4
    end
    AT-->>SET: sa, sb, sc
```

### SL\_CLStrongABC

Works out the shared parts (lad, pinch, bands, step\_cl, step\_band, wait), then takes one of two paths: the strong 1 sequence at M15, or rules A / B / C at M30 and H1 with the strong 2 sequence added at M30. The strong 1 path checks M5's quiet slope inline; it does not call SL\_CLM5QuietSw.

```mermaid
sequenceDiagram
    autonumber
    participant AT as SL_CLStrongAt
    participant ABC as SL_CLStrongABC
    participant GS as SL_CLGapShrinking
    participant BS as SL_CLBandShrink
    participant M5Q as SL_CLM5QuietSw
    participant SI as SL_CLSideIsh

    AT->>ABC: (lvl) - hi = lvl, below = lvl-1, step = lvl+1
    alt lvl not 1 to 3
        ABC-->>AT: 0, 0, 0
    end
    ABC->>ABC: lad = g_clsw.step ≥ lvl
    ABC->>GS: gap (below, hi) closing?
    ABC->>ABC: pinch = closing and gap (below, hi) ≤ half CL_SW
    ABC->>BS: hi band shrinking? step band shrinking?
    ABC->>ABC: bands = both shrinking
    ABC->>GS: gap (hi, step) closing? - step_cl
    ABC->>BS: step band shrinking? - step_band
    ABC->>ABC: wait = CLSW_StrongWait1 and lvl 1 and step_cl and step_band
    alt lvl 1 and CLSW_S1Seq on
        ABC->>ABC: m5sw = SL_CLSw(M5) and g_clsw_m5_run ≥ 2
        ABC->>ABC: m5q = abs M5 diffMid ≤ 0.33 or smaller than last bar
        ABC->>BS: M30 band shrinking? - m30shr
        ABC->>ABC: ok = m15shr and close and m5sw and m5q and m30shr and not wait
        ABC-->>AT: ok - 1, 1, 1, else 0, 0, 0 (log S1seq) and return
    else lvl 2 or 3 (or lvl 1 with CLSW_S1Seq off)
        ABC->>ABC: A = lad and pinch and bands
        ABC->>ABC: unless wait - sa = A, sb = A or (lad and step_cl), sc = A or (lad and step_cl and step_band)
        opt lvl 2 and CLSW_S2Seq on
            ABC->>SI: M15 sideway-ish?
            ABC->>M5Q: M5 quiet sideway?
            ABC->>BS: M30 band shrinking?
            ABC->>ABC: all three - sa = sb = sc = 2 (log S2seq)
        end
        ABC-->>AT: sa, sb, sc (log lad pinch bands step stepBand)
    end
```

### SL\_CLStrongM15H1

Strong 3 through M15: H1 has gone flat and M15 sits on the H1 midline, even while M30 is still trending away.

```mermaid
sequenceDiagram
    autonumber
    participant AT as SL_CLStrongAt
    participant M1 as SL_CLStrongM15H1
    participant FL as SL_CLFlat
    participant SW as SL_CLSw
    participant SI as SL_CLSideIsh

    AT->>M1: ()
    alt CLSW_StrongM15H1 off
        M1-->>AT: false
    end
    M1->>FL: H1 flat by diffMid? - h1f
    M1->>SW: M15 midtrend sideway (dmtsw ≥ 3)?
    M1->>FL: or M15 flat by diffMid?
    M1->>SI: or M15 sideway-ish? - m15s
    M1->>M1: near = gap M15-H1 between 0 and 1 (half of CL_SW 2)
    M1->>M1: log S3m15h1 H1flat, M15, gap
    M1-->>AT: h1f and m15s and near
```

### SL\_CLStrongNeed and SL\_CLStrongNeedOK

The per-grade need, applied to each level before the levels are combined. SL\_CLStrongNeed loops over the three rules; SL\_CLStrongNeedOK answers for one grade.

```mermaid
sequenceDiagram
    autonumber
    participant SET as SL_CLSetStrong
    participant NEED as SL_CLStrongNeed
    participant OK as SL_CLStrongNeedOK
    participant SI as SL_CLSideIsh
    participant FL as SL_CLFlat
    participant SW as SL_CLSw

    SET->>NEED: (a, b, c)
    loop each of a, b, c above 0
        NEED->>OK: (grade g)
        alt CLSW_StrongNeedM15 off
            OK-->>NEED: true
        end
        OK->>SI: M15 sideway-ish?
        SI->>FL: M15 flat by diffMid? (CLSW_FlatDiffMid)
        SI->>SW: or M15 dmtsw ≥ 3, or M15 dmt 4 / 5
        SI-->>OK: m15
        OK->>SW: M5 dmtsw ≥ 3 and g_clsw_m5_run ≥ 2? - m5
        alt g = 1 or 4
            OK-->>NEED: m15
        else g = 2 or 3
            OK-->>NEED: m5 or m15
        end
        NEED->>NEED: false - that grade becomes 0
    end
    NEED-->>SET: a, b, c (log NEED ... dropped if any became 0)
```

### SL\_CLM5QuietSw

M5 sideway for 2+ bars in a row with its slope going quiet. Only the strong 2 sequence calls it; the strong 1 path runs the same test inline.

```mermaid
sequenceDiagram
    autonumber
    participant HIST as SL_CLUpdateHist
    participant ABC as SL_CLStrongABC
    participant M5Q as SL_CLM5QuietSw
    participant SW as SL_CLSw

    HIST->>HIST: earlier on the bar - g_clsw_m5_run = M5 sideway bars in a row
    ABC->>M5Q: (d0 by reference) - strong 2 sequence
    M5Q->>M5Q: d0 = abs M5 diffMid this bar, d1 = last bar
    M5Q->>SW: M5 dmtsw ≥ 3?
    M5Q->>M5Q: sw = that and g_clsw_m5_run ≥ CLSW_S1M5Run (2)
    M5Q->>M5Q: q = CLSW_S1M5Quiet off, or d0 ≤ 0.33, or d0 smaller than d1
    M5Q-->>ABC: sw and q, plus d0 for the log
```

## February replay

With all V3 defaults (rule C), strong fires on 290 Ready bars, 84 % of them inside your sideways, with a strong in the 6 h before 24 of your 37 breakouts; strong 2 carries most of it and strong 4 is mostly noise.

| Strong | Bars | Inside your sideways | Your breakouts within 6 h after |
| --- | --- | --- | --- |
| 1 (M15) | 64 | 95 % | 12 |
| 2 (M30) | 137 | 96 % | 15 |
| 3 (H1) | 72 | 68 % | 5 |
| 4 (H4) | 17 | 12 % | 1 |
| all | 290 | 84 % | 24 / 37 (11 strong episodes outside your sideways) |

**Your dates** (strong kept on that bar, rule C, keep latest):

| Time | Strong | Why |
| --- | --- | --- |
| 02.02 23:20 → 23:55 | 3 | M15 on a flat H1 |
| 02.03 01:15 breakout | 3 | kept from 02.02 |
| 02.04 01:10 → 01:50 | 2 | Ready B at M30, rules A / B / C |
| 02.06 23:15 → 23:45 | 1 | strong 1 sequence |
| 02.09 15:30 → 16:25 | 2 | rules B / C (M30–H1 closing) |
| 02.11 11:25 → 11:40 | 2 | strong 2 sequence |
| 02.13 11:20 → 14:15 | 2 | strong 2 sequence via M15 on M30 |
| 02.23 15:15 → 16:25 | 2 | M15 on M30, kept through 15:20–15:55 by the M5 run |
| 02.24 11:00 → 12:25 | none | strong 1 waits for M30 |
| 02.24 13:15 → 13:55 | 2 | M30 shrink nearly done, M15–M30 0.3–0.8 |
| 02.27 13:50 → 14:40 | 4 | Ready at H4, H1 checks pass |

Known leftovers: 26 Feb 07:05 comes back as strong 3 (M5 sideway, outside your sideways); 26 Feb 14:35–16:05 strong 4 (outside). Replay limits: values come from your log lines (completed bars for M15 and above), so the EA can move by a bar.

## Code map

`SL_MidCluster_Breakout_V3.mqh` has the same entry call as V1 / V2 (`SL_CLSW_Reset()` in OnInit, `SL_MidCluster_Breakout(BB_datas, g_tradectx)` on tick); include only one of V1, V2, V3.

| Function | Does |
| --- | --- |
| `SL_CLUpdateGaps`, `SL_CLGapSet` | own midline gaps `g_clsw_cl` |
| `SL_CLUpdateHist` | touch times, M5 run, M5 reversal, gap history (`g_clsw_gh`, `g_clsw_ghn`) |
| `SL_CLSW_Type`, `SL_CLGateOpen`, `SL_CLSW_Clear` | gate and reset |
| `SL_CLLadder`, `SL_CLSideIsh`, `SL_CLFlat` | ladder and sideway-ish |
| `SL_CLS1Track` | strong-1 memory (M15 shrank, then M5–M15 close) |
| `SL_CLFindCandidates` | type inputs |
| `SL_CLSW_Ready`, `SL_CLM5Event`, `SL_CLM5Cluster`, `SL_CLM15Cluster`, `SL_CLNothingNear` | Ready A / B / T4 |
| `SL_CLConfirmType`, `SL_CLConfirmTypeB` | type at Ready |
| `SL_CLSetStrong`, `SL_CLStrongAt`, `SL_CLStrongABC`, `SL_CLStrongM15H1` | strong grades |
| `SL_CLM5QuietSw`, `SL_CLGapShrinking`, `SL_CLBandShrink` | M5 run + quiet slope, gap closing, band shrinking |
| `SL_CLStrongNeed`, `SL_CLStrongNeedOK`, `SL_CLKeep` | per-grade need, keeping |
| `SL_CLLog`, `SL_CLDebugMem`, `SL_CLDraw`, `SL_CLDrawABC` | logs and chart marks |

**Inputs**

| Input | Default | Meaning |
| --- | --- | --- |
| `CLSW_GateCluster` | false | also open the gate on midline clusters |
| `CLSW_LatchCand` | false | type inputs recomputed every bar |
| `CLSW_T4MinRun` | 3 | Ready T4: M5 sideway bars in a row |
| `CLSW_StrongMode` | 2 | rule behind `ready_strong`: 0 A, 1 B, 2 C |
| `CLSW_StrongKeep` | 0 | 0 latest strong, 1 highest TF |
| `CLSW_FlatDiffMid` | true | flat diffMid counts as sideway-ish |
| `CLSW_StrongWait1` | true | strong 1 waits while M30 closes in and shrinks |
| `CLSW_S1Seq` | true | strong 1 = the sequence |
| `CLSW_S1Close` | 2.25 | strong 1 “very close” M5–M15 |
| `CLSW_S1M5Run` | 2 | M5 sideway bars in a row (strong 1, strong 2 sequence, need) |
| `CLSW_S1M5Quiet`, `CLSW_S1M5Dmid` | true, 0.33 | M5 slope quiet |
| `CLSW_S2Seq` | true | strong 2 also by the sequence |
| `CLSW_StrongM15H1` | true | strong 3 route 2 |
| `CLSW_StrongH4Fall` | true | strong 4 |
| `CLSW_StrongNeedM15` | true | per-grade need |
| `CLSW_StrongNoReady` | 0 | strong without a Ready: 0 off, 1 strong 1 only, 2 any |
| `CLSW_Log`, `CLSW_DrawReady`, `CLSW_DrawStrongABC` | true | logs and drawing |
| `CLSW_DebugMem`, `CLSW_DebugFrom`, `CLSW_DebugTo` | false, all time | `[CLMEM]` window |

**Outputs in `g_clsw`:** `gate`, `step` (ladder −1–3), `cand`, `ready` (Ready since the reset), `ready_now` (this bar), `ready_type` 1–4, `ready_lvl` 0–4, `ready_t`, `ready_strong` 0–4, `ready_strong_t`, `strong_a / strong_b / strong_c`.

## Logs and debugging

One `[CLSW2]` line per M5 bar carries every decision; `evt{}` has three parts: gate + type inputs | Ready | strong checks.

| Field | Meaning |
| --- | --- |
| `gate`, `cand`, `step` | gate (0 / 1 / 2), type inputs, ladder step |
| `rdy`, `now`, `type`, `lvl` | Ready since the reset, Ready this bar, kept type and level |
| `strong`, `A/B/C` | `ready_strong`, and each rule’s kept grade (since the reset, not this bar) |
| `ladder`, `m5run` | ladder TF, M5 sideway run |
| `evt{…\|…\|…}` | part 2: `m5sw` / `m5rev`, `_C<TF>`, `_C15<TF>`, `_RA:T<n><TF>`, `_RB:…`, `_R4`, `_S<n>`; part 3: the strong check lines below |

| Strong debug | Meaning |
| --- | --- |
| `S1seq m15shr:Y close:Y m5sw:Y(run 2) m5quiet:Y(0.14) m30shr:Y -> S1` | strong 1 sequence; `WAIT:M30 still closing in` when blocked |
| `S2seq m15sw:Y m5quietSw:Y(run 3,0.02) m30shr:Y -> S2` | strong 2 sequence |
| `S2:M30 lad:Y pinch:N bands:N step<:Y stepBand:N -> A0 B2 C0` | rules A / B / C at that level, **this bar only** |
| `S3m15h1 H1flat:Y M15:Y gap:0.0` | strong 3 route 2 |
| `[hi H4 -> H1 checks]` | strong 4 |
| `\| M15 on M30:` | the extra level from M15’s clusters |
| `NEED:M15 not sideway-ish M5run 1 -> dropped` | per-grade need removed a grade |

| Line | When | Shows |
| --- | --- | --- |
| `[CLCHK]` | every bar (temporary) | own gaps next to `ctx.cl` H4 slots |
| `[CLMEM]` | `CLSW_DebugMem` + window | reset, M5 run, ladder, `gaps m15m30[3]:6.8>10.3>10.5 close:Y` (`[n]` = values stored), touch times |

## Open items

- [ ] `CLSW_StrongKeep`: keep the latest strong (0) or the highest TF (1) — decides which grade shows when several fire in one sideway (e.g. 27 Feb: strong 2 earlier, strong 4 at 13:50).
- [ ] Strong 3 need: “M5 run or M15” (5 breakouts, brings back 26 Feb 07:05) or “M15 only” (74 % inside, 3 breakouts).
- [ ] Strong 4 stays weak (12 % inside): add a condition such as the H4 band shrinking for N bars, or keep as information.
- [ ] Replace the word “candidate”: fold the type inputs into the type decision at the Ready bar (same results, `why:` tag).
- [ ] `SL_init` copies the midline pairs into `ctx.cl` without the H4 slots; V3 works around it with its own gaps.
- [ ] Breakout stages (trigger, price confirm, end) are not in V3 yet.
- [ ] Fitted on February only: replay a month you label blind before trusting the numbers.
