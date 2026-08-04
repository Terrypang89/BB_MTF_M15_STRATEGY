# TofySidewayLadder — design, measurements, and open questions

Companion doc for `scripts/TofySidewayLadder.mqh` and `scripts/ladder_ranges.py`.

**Status: diagnostic only.** The module computes a sideway "ladder" state and draws a
label per M15 bar. It does **not** trade and does **not** write `sideway_selected`, so
the existing detector and DMONLY are unaffected.

> **Major update:** scoring now runs against **hand-labelled February ranges**
> (`references/SIDEWAY_LABELS_FEB.md`, 27 ranges / 1,830 bars) rather than the earlier
> QUIET proxy. The two targets **disagree** on some settings, and the labels are the
> better target — see §9. Conclusions drawn from the proxy alone are marked as superseded.

---

## 1. What problem this is trying to solve

The existing `TofySideway` detector misses most rangebound periods. The original example
was **2026.02.03 12:40 → 02.04 02:05** (50 M15 bars):

| | value |
|---|---|
| start → end | 4916.88 → 4957.30 (**net 40.42**) |
| high / low | 4993.42 / 4881.51 (**range 111.91**) |
| path travelled | 1,163.18 |
| **efficiency ratio** | **0.035** |

Price walked 1,163 points to finish 40 from where it started — bottom decile of the
dataset. **This is chop, not quiet.** The current detector covered 6 of 50 bars (12%).

---

## 2. Why the existing detector misses it

`TofySideway` is a **quiet** detector, not a **chop** detector:

| class | definition | baseline | TofySideway flags | lift |
|---|---|---|---|---|
| QUIET | net < 10 and range < 15 | 37.8% | 53.8% | **+16.0** |
| CHOPPY | net < 10 and range ≥ 15 | 15.6% | 10.8% | **−4.8** |
| TREND | net ≥ 10 | 46.6% | 35.4% | −11.2 |

The mechanism is the midline-cluster gate. In a *quiet* market the M5/M15/M30 midlines
converge, so `cluster < 10` passes. In a *choppy* range price swings ±50 points, which
keeps the midlines apart — **the condition used as evidence of sideways is destroyed by
the kind of sideways being looked for.**

This tension recurs throughout everything below and is never fully resolved.

---

## 3. The ladder design

Sequential escalation. `＜` means "less than".
`clus0` = |M15−M5 mid|, `clus1` = |M15−M30 mid|, `clus2` = |M15−H1 mid|.
`LA` = current bar, `LA_1` = one back, `LA_2` = two back.

### Predicates (each scored alone in §4)

| name | condition |
|---|---|
| **A15** | `(clus0[LA] ＜ clus0[LA_1] ＜ clus0[LA_2])` OR `(clus0[LA] ＜ CL_NEAR AND clus0[LA_1] ＜ CL_NEAR)` |
| **S15** | `stage[1][LA]` is 512, 523, or 400-499 |
| **C15** | `\|dm1[LA]\| ＜ 3` AND `\|dm1[LA_1]\| ＜ 3` |
| **W15** | `dbbw1[LA] ＜ 1` AND `dbbw1[LA_1] ＜ 1` |
| **A30** | same shape as A15, on `clus1` |
| **S30** | `stage[2][LA]` is 512, 523, or 400-499 |
| **C30** | `\|dm2[LA]\| ＜ 1.5` AND `\|dm2[LA_1]\| ＜ 1.5` |
| **W30** | `dbbw2[LA] ＜ 1` AND `dbbw2[LA_1] ＜ 1` |
| ~~B15~~ | ~~`dm1[LA] ＜ dm1[LA_1] ＜ dm1[LA_2]`~~ **REMOVED** |
| ~~B30~~ | ~~same on dm2~~ **REMOVED** |

### Level gates (selectable)

```
SL_L1Mode   0  A15 && (S15 || C15)
            1  A15 && C15                <- default
            2  A15 && S15
            3  A15 && S15 && C15

SL_L2Mode   0  S30 || C30 || W30         <- default
            1  S30 || C30
            2  C30

state 1 = lvl1
state 2 = prev >= 1  AND  A30  AND  ev30
```

### Breakout cancel

```
SL_BreakoutMode  0  off
                 1  raw                    close outside the M15 band
                 2  raw && raw1            breakout persisted 2 bars
                 3  raw && !C15
                 4  raw && !C15 && !W15    IDENTICAL to 3 in practice
```

---

## 4. Each predicate scored alone

7,603 M15 bars, QUIET baseline 37.8%. "window" = the 50-bar Feb 3-4 range.

| predicate | fires on | lift | window | enrichment |
|---|---|---|---|---|
| A15 cluster | 76% | +4.5 | 35/50 | 0.93× |
| S15 stage | 47% | +3.3 | 26/50 | 1.12× |
| **B15 dm falling** | 25% | **+2.3** | 7/50 | **0.56×** ← removed |
| C15 \|dm\| ＜ 3 | 82% | +5.3 | 44/50 | 1.07× |
| W15 dbbw ＜ 1 | 52% | +4.8 | 30/50 | 1.15× |
| A30 cluster | 62% | +5.4 | 33/50 | 1.07× |
| S30 stage | 49% | +4.1 | 34/50 | **1.40×** |
| **B30 dm falling** | 25% | **+1.2** | 17/50 | 1.37× ← removed |
| **C30 \|dm\| ＜ 1.5** | 41% | **+10.9** | 11/50 | 0.54× |
| W30 dbbw ＜ 1 | 49% | +4.4 | 31/50 | 1.26× |

**Three structural facts:**

1. **`C30` alone scores +10.9** — more than the entire original ladder. Most of the
   module's value comes from one condition: *is the M30 midline barely moving?*
2. **`B15` and `B30` are dead.** +2.3 and +1.2, and B15 fires *less* inside the target
   range than chance. Removing both changed lift by +0.1.
3. **The M15 side is saturated.** A15 fires on 76%, C15 on 82%. Any additional OR-branch
   on level 1 cannot bite — confirmed three separate times (B15, a diffBBW branch, and
   W15, which changed **2 bars out of 7,603**).

---

## 5. Fixes that worked

### `prev >= 1` instead of `prev == 1`

Under `prev == 1`, a bar already at level 2 could never re-qualify, so the state
collapsed every bar.

| | state≥2 n | lift | window |
|---|---|---|---|
| `prev == 1` | 1,019 | +8.6 | 6/50 |
| **`prev >= 1`** | **2,648** | **+9.0** | **14/50** |

2.6× coverage *and* slightly better lift — unusual, because it fixed a structural flaw
rather than loosening a threshold.

### `CL_NEAR` 10.0 → 10.5

A bar at `clus1 = 10.1` was rejected by 0.1 and broke the ladder chain behind it.

| CL_NEAR | state≥2 n | lift | window |
|---|---|---|---|
| 10.0 | 3,667 | +8.4 | 16/50 |
| **10.5** | **3,756** | +8.4 | **27/50** |
| 15.0 | 3,268 | +8.4 | 29/50 |
| 40.0 | 4,223 | +4.8 | 29/50 |

+89 bars for +11 window bars. Coverage plateaus at 15 — past that the cluster gate is no
longer the binding constraint.

### Removing B15 / B30

Free: lift +11.2 → +11.5, identical window coverage.

---

## 6. Things measured and rejected

| change | result |
|---|---|
| **H1 level (state 3)** | +3.2 as ladder step 3, +3.4 standalone. Cuts sample 948 → 229. **`SL_UseH1 = false`** |
| **`diffMid` threshold branch** | adds up to 1,400 detections, costs lift in every variant, **window coverage does not move at all** |
| **`diffBBW` on M15** | changed 2 bars out of 7,603 — B15 is saturated |
| **`W15` added to level 1** | changed 4 bars — same reason |
| **ladder as a replacement for TofySideway** | would add 883 near-baseline bars while discarding 892 good ones |

### Why the diffMid branch could not help

`diffMid` sits in **block B**. The undetected bars in the target window failed **block A**
— the cluster gate (`clus0` at 13-23 against a threshold of 10). Since the rule is
`A && B`, loosening B changes nothing when A is already false. **The wrong condition was
being relaxed.**

### `diffMid` is signed

47% of values are negative. `dm ＜ 1.0` is true for *every falling midline*, including one
dropping at −18. It measures "midline is falling", not "midline is flat". Use `MathAbs`.

---

## 7. The February labels — ground truth

`references/SIDEWAY_LABELS_FEB.md`: **27 hand-labelled ranges, 1,830 M15 bars,
858 labelled sideway (46.9%).** A random detector firing at any rate scores 46.9%
precision.

This replaces the 50-bar window as the scoring target. The window was too small to
distinguish enrichment 1.21× from 1.37×.

### Protocol (must be followed or the numbers mean nothing)

1. Label a month by eye, **without** looking at detector output.
2. Tune against those labels.
3. Label a **second** month **before** running the tuned detector on it.
4. Run once. That is the number that counts.

**February is now the tuning set.** Any change made to improve February numbers makes
February in-sample. March, labelled blind, is the test.

### Edge tolerance

Hand labels are not bar-precise. Two treatments, ±6 bars:

- **(a) widened** — extend each range ±6 bars. Treats uncertain edges as definitely sideway.
- **(b) edges excluded** — drop the ±6 bars around each boundary from scoring. Treats them
  as "don't know". **This is the honest reading** and is preferred.

Note (b) excludes **641 of 1,830 bars (35%)** — the ranges are short enough that edges are
a large fraction of the data.

---

## 8. Scored against the February labels

`L1=1, L2=0` throughout unless stated.

| detector | fires | precision | recall | F1 (strict) | F1 (widened) | F1 (edges excl) |
|---|---|---|---|---|---|---|
| **TofySideway S_** | 346 | **82.4%** | **33.2%** | 47.3 | 40.5 | 49.0 |
| ladder brk=0 | 947 | 63.1% | 69.7% | 66.3 | **72.0** | 71.4 |
| ladder brk=1 | 734 | 70.4% | 60.3% | **64.9** | **62.6** | **67.0** |
| **ladder brk=2** | 857 | 67.7% | 67.6% | **67.6** | 69.8 | **72.1** |
| ladder brk=3 | 927 | 64.1% | 69.2% | 66.6 | 71.4 | 71.4 |
| **ladder brk=4** | 927 | 64.1% | 69.2% | 66.6 | 71.4 | 71.4 |

**Findings:**

**TofySideway is high-precision, low-recall: ~83% / ~34%.** When it fires you can trust
it; it catches only a third of the ranges. The ladder is balanced (~70% / ~68%). They are
**complementary, not competing** — consistent with the earlier +18.4 lift where both agree.

**Breakout modes 0, 2, 3, 4 are within ~1.5 F1 of each other.** Only mode 1 is clearly
worse on the labels. An earlier "mode 2 wins" call was overconfident on a margin that
small.

**Mode 4 is byte-identical to mode 3** — same fires (927/927/570), same precision, same
recall, same 7 cancels, in all three treatments. The `!W15` term never changes an outcome.
If you want mode 4's behaviour, mode 3 gives it with one fewer term.

---

## 9. The proxy and the labels DISAGREE

| setting | QUIET-proxy lift | label F1 (strict) |
|---|---|---|
| breakout cancel ON (mode 1) | **+11.5** (best) | 64.9 (worst) |
| breakout cancel OFF | +7.8 (worst) | 66.3 |

Exactly opposite. The reason: **the labels include bars where price briefly pokes outside
the M15 band.** The QUIET test scores those as TREND (net ≥ 10 over the next hour) and
penalises flagging them; the labels treat them as still inside the range.

**The labels are the better target** — they encode what the detector is actually wanted
for. `net < 10 && range < 15` was a guess at that.

Conclusions in §4-§6 that rest on the proxy alone should be re-checked against labels
before being acted on.

---

## 10. The fragmentation problem

`scripts/ladder_ranges.py` collapses `state >= 2` bars into ranges and compares them to
the labels.

| setting | ranges | bars | precision | recall | F1 |
|---|---|---|---|---|---|
| A `L1=1 L2=0 brk=0` | 48 | 947 | 63.1% | 69.7% | 66.3 |
| B `L1=1 L2=0 brk=2` | 57 | 857 | 67.7% | 67.6% | 67.6 |
| C `L1=1 L2=0 brk=4` | 48 | 927 | 64.1% | 69.2% | 66.6 |
| D `L1=0 L2=0 brk=2` | 59 | 869 | 67.3% | 68.2% | 67.7 |
| E `L1=3 L2=1 brk=2` | 45 | 626 | 67.6% | 49.3% | 57.0 |

**You labelled 27 ranges. The detector produces 45-59.** It cuts single ranges into pieces:

```
| 2 | 2026.02.03 14:45 | 2026.02.03 15:30 |  4 | 4/4 |
| 3 | 2026.02.03 16:45 | 2026.02.03 17:00 |  2 | 2/2 |
| 4 | 2026.02.03 17:45 | 2026.02.03 18:30 |  4 | 4/4 |
| 5 | 2026.02.03 20:45 | 2026.02.04 02:15 | 19 | 18/19 |
```

Four detections inside one 13:30→02:00 label, each with near-perfect overlap. **The
detector sees the range; it keeps dropping out and re-entering.** That is why recall sits
near 68% despite the pieces being accurate.

`--gap N` bridges dropouts, `--min-bars N` drops fragments. Worth testing `--gap 3`.

---

## 11. Metric definitions

For every M15 bar, look forward 12 M5 bars (60 min) from that bar's `close_M5`:

```
net   = |close[last] − close[first]|
range = max(closes) − min(closes)

TREND   if net >= 10
CHOPPY  if net < 10  AND  range >= 15
QUIET   if net < 10  AND  range <  15
```

| metric | formula |
|---|---|
| n | count of bars where `state >= 2` |
| %bars | `n / total_bars` |
| baseline | `QUIET_all / total_bars` = 2,877 / 7,603 = 37.8% |
| lift | `(QUIET_flagged / n) − baseline` |
| enrichment | `(window_hits / n) ÷ (window_bars / total_bars)` — **1.0× = chance** |
| precision | `flagged ∩ labelled / flagged` |
| recall | `flagged ∩ labelled / labelled` |
| F1 | `2·P·R / (P+R)` |

### Worked example — `L1=1, L2=0, brk=1`

```
T (scored bars)              = 7,603
QUIET bars overall           = 2,877
baseline    = 2877 / 7603    = 37.8%

n (state ≥ 2)                = 3,139
  of which QUIET             = 1,548
flagged QUIET% = 1548 / 3139 = 49.3%
LIFT        = 49.3 − 37.8    = +11.5

share of flags in window     = 25 / 3139   = 0.0080
share of all bars in window  = 50 / 7603   = 0.0066
ENRICHMENT                   = 0.0080 / 0.0066 = 1.21×
```

### What none of these measure

**Profitability.** Lift and F1 measure agreement with a definition or a label set. A
detector with perfect F1 could still lose money if the bars it flags are not the ones
where exiting beats holding. That question needs the ladder wired into a strategy and
compared against the DMONLY +$968 baseline — **still untested.**

---

## 12. Design (UML)

```mermaid
classDiagram
    class TofySidewayLadder {
        +int SL_L1Mode = 1
        +int SL_L2Mode = 0
        +int SL_BreakoutMode
        +bool SL_UseH1 = false
        +double CL_NEAR = 10.5
        +double SL_diffmid_m15 = 3.0
        +double SL_diffmid_m30 = 1.5
        -int SL_state[5]
        +SL_Update(BBTFImpact, BB_datas) void
        -SL_StageOK(stage) bool
    }
    class Predicates {
        +A15 S15 C15 W15
        +A30 S30 C30 W30
        NOTE B15 and B30 removed - measured dead
    }
    class ExistingDetector {
        +sideway_selected[LA]
        NOTE precision 82.4 pct recall 33.2 pct
    }
    class GroundTruth {
        +SIDEWAY_LABELS_FEB.md
        +27 ranges 858 bars
    }

    Predicates --> TofySidewayLadder : evaluated per M15 bar
    TofySidewayLadder --> ChartAndLog : labels + LADDER lines
    TofySidewayLadder ..> ExistingDetector : NEVER writes it
    GroundTruth --> TofySidewayLadder : scoring target
    ExistingDetector --> DMONLY : unchanged exit trigger
```

---

## 13. State machine

```mermaid
stateDiagram-v2
    [*] --> S0
    S0 : state 0 - not sideway
    S1 : state 1 - M15 settled
    S2 : state 2 - M30 confirms
    S3 : state 3 - H1 (disabled)

    S0 --> S1 : lvl1 gate
    S1 --> S2 : prev>=1 AND A30 AND ev30
    S2 --> S2 : persists (prev>=1)
    S2 --> S0 : breakout cancel
    S1 --> S0 : gate fails
    S2 --> S3 : SL_UseH1 (off)

    note right of S2
        the useful level
    end note
    note right of S3
        +3.2 vs +10.2 - disabled
    end note
```

The `S2 --> S2` self-transition is what `prev >= 1` enabled. Under `prev == 1` that edge
did not exist.

---

## 14. Chart labels

| label | colour | meaning |
|---|---|---|
| `L2` | 🟢 lime | M30 confirmed |
| `L1` | 🟡 yellow | M15 only |
| `L0-brk` | ⚪ gray | cancelled by breakout |
| `L0-A15` | ⚪ gray | cluster gate failed |
| `L0-ev15` | ⚪ gray | level-1 evidence gate failed |
| `L1-prev` | 🟡 yellow | chain not running yet |
| `L1-A30` / `L1-ev30` | 🟡 yellow | level-2 gate failed |

`SL_ShowFails = false` hides the gray labels. Keep it **true** while diagnosing.

---

## 15. Where this stands

**Confirmed**

| change | effect |
|---|---|
| `prev >= 1` | 2.6× coverage, lift up. Keep. |
| `CL_NEAR = 10.5` | +89 bars, window 16/50 → 27/50. Keep. |
| remove B15 / B30 | free: +0.3 lift, same coverage. Keep. |
| `SL_UseH1 = false` | H1 measured +3.2 vs +10.2. Keep off. |

**Rejected**

diffMid threshold branch · diffBBW on M15 · W15 on level 1 · ladder as a replacement for
TofySideway · breakout mode 4 as distinct from mode 3

**Open**

| question | status |
|---|---|
| fragmentation — 27 labels vs 45-59 detected ranges | `--gap` untested |
| ladder as a **confirmation tier** on TofySideway | +18.4 where both agree — strongest number seen, untested in a strategy |
| **does better detection improve P&L?** | **untested** — the one that matters |
| does anything here survive March? | untested; labels not yet made |

**Honest summary.** The ladder is a balanced detector (~70% precision, ~68% recall against
your labels) where TofySideway is precise but narrow (~83% / ~34%). It covers the choppy
ranges the incumbent misses, at the cost of firing 2-3× as often.

Every gain came from **fixing something wrong** — `prev >= 1`, the 0.1 threshold
rejection, removing dead predicates. Every attempt to gain by **loosening a threshold**
cost precision without improving coverage of the target.

None of this has been shown to improve trading. That test — DMONLY with the ladder as its
exit, once, against +$968 — remains the outstanding item, and no amount of detector
tuning substitutes for it.
