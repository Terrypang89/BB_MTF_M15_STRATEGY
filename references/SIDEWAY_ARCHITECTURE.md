# TofySideway — Sideways-Classification Subsystem (DETECTOR)

This document describes the TofySideway sideways-classification subsystem, which classifies each bar's sideways condition into a code (11/12/13/21/22/23/24/31/32/41/51, or 0=none), using midline clustering across TFs + per-TF sideways scores.

---

## Overview

TofySideway classifies each bar's sideways condition into a code using two functions:

- **BBDatas_Midline_Cluster** — computes midline-distance between TF pairs (M5-M15, M15-M30, M15-H1) and stores results in `BBTFImpact.BB_midline_Cluster[3][LA]`.
- **BBDatas_Midline_Sideway** — scores each TF with `sideway_val` and classifies into a code stored in `BBTFImpact.sideway_selected[0]`.

State: TofySideway is a DETECTOR — it flags sideways conditions, it does NOT yet make trade decisions (untested for trading).

---

## Inputs and scoring

### BB_midline_Cluster values

| Index | TF pair | Stored in |
|-------|---------|-----------|
| 0 | M5 vs M15 | `BBTFImpact.BB_midline_Cluster[0][LA]` |
| 1 | M15 vs M30 | `BBTFImpact.BB_midline_Cluster[1][LA]` |
| 2 | M15 vs H1 | `BBTFImpact.BB_midline_Cluster[2][LA]` |

### sideway_val per TF — scoring rules

Each TF contributes a sum of points (max 7):

| Condition | Points | Source line |
|-----------|--------|-------------|
| `BB_diffMid_Trend >= 3` (sideways trend) | +4 | line 51-53 |
| `BBW_stage < 500` (not flying) | +2 | line 55-57 |
| `BBW_stage == 513 / 523` (fly-shrink) | +1 | line 59-61 |

### Log format

When a code fires, the log line includes:

```
Sideway_val:[H4 H1 M30 M15 M5]-S_<code>
```

where `<code>` is the selected sideways code (e.g. `11`, `23`, `41`). The `S_` prefix marks the sideways selection event.

---

## Classification logic

### DIAGRAM 1 — Full decision cascade

```mermaid
flowchart TD
    Start["BBDatas_Midline_Sideway()"] --> Reset["sideway_selected[0] = 0; sideway_val[] = 0"]

    Reset --> T1{"M5+M15 cluster <=6 AND M15+M30 cluster <=10<br/>OR M5+M15 cluster <=6 AND M15+H1 cluster <=10"}

    T1 -- YES --> C11{"sideway_val[0]>=1 AND sideway_val[1]>=4 AND (sideway_val[3]>=2 OR sideway_val[2]>=4)"}
    T1 -- NO --> T2{"M5+M15 cluster <=6 for 2 bars<br/>AND sideway_selected[0] == 0"}

    C11 -- YES --> CODE_11["code 11"]
    C11 -- NO --> C12{"sideway_val[0]>=4 AND sideway_val[1]>=1 AND (sideway_val[3]>=2 OR sideway_val[2]>=4)"}
    C12 -- YES --> CODE_12["code 12"]
    C12 -- NO --> C13{"sideway_val[0]>=4 AND sideway_val[1]>=2"}
    C13 -- YES --> CODE_13["code 13"]
    C13 -- NO --> T3

    T2 -- YES --> C21{"sideway_val[0]>=6"}
    T2 -- NO --> T4{"M5+M15 cluster <=10 AND M15+M30 cluster <=15<br/>AND sideway_selected[0] == 0"}

    C21 -- YES --> CODE_21["code 21"]
    C21 -- NO --> C22{"sideway_val[0]>=4 AND sideway_val[1]>=2"}
    C22 -- YES --> CODE_22["code 22"]
    C22 -- NO --> C23{"sideway_val[1]>=2 AND sideway_val[3]>=5"}
    C23 -- YES --> CODE_23["code 23"]
    C23 -- NO --> C24{"sideway_val[0]>=5 AND sideway_val[1]>=1"}
    C24 -- YES --> CODE_24["code 24"]
    C24 -- NO --> T4

    T4 -- YES --> C31{"sideway_val[0]>=4 AND sideway_val[1]>=2"}
    T4 -- NO --> T5{"prev bar sideways AND M5+M15 cluster <=6 AND M15+M30 cluster <=6 AND M15+H1 cluster <=10<br/>AND sideway_selected[1] != 0"}

    C31 -- YES --> CODE_31["code 31"]
    C31 -- NO --> C32{"sideway_val[1]>=2 AND sideway_val[3]>=5"}
    C32 -- YES --> CODE_32["code 32"]
    C32 -- NO --> T5

    T5 -- YES --> C41{"sideway_val[0]>=1 OR sideway_val[1]>=1 AND sideway_val[2]>=2 AND sideway_val[3]>=2 AND sideway_val[4]>=2"}
    T5 -- NO --> T6{"prev bar sideways AND (M5+M15 cluster <=3 OR M15+M30 cluster <=3)<br/>AND cluster tightening<br/>AND sideway_selected[1] != 0"}

    C41 -- YES --> CODE_41["code 41"]
    C41 -- NO --> C51{"sideway_val[1]>=6"}

    C51 -- YES --> CODE_51["code 51"]
    C51 -- NO --> End["sideway_selected[0] remains 0"]

    classDef code fill:#e8f5e9,stroke:#2e7d32
    class CODE_11,CODE_12,CODE_13,CODE_21,CODE_22,CODE_23,CODE_24,CODE_31,CODE_32,CODE_41,CODE_51 code
```

The tier order is critical — each code only fires if earlier conditions were false (see the `sideway_selected[0] == 0` guards). Terminal nodes are the final codes or the default `sideway_selected[0] = 0` when none match.

---

## Code catalog

| Code | Tier | Exact trigger condition (from source) | Plain-language description |
|------|------|--------------------------------------|----------------------------|
| 11 | 1 | `(midline_0<=6 && midline_1<=10 || midline_0<=6 && midline_2<=10) && sideway_val[0]>=1 && sideway_val[1]>=4 && (sideway_val[3]>=2 || sideway_val[2]>=4)` | M5+M15 tightly clustered with M15+M30 or M15+H1; M5 shows sideways trend, M15 strongly sideways; H4/M30 also sideways or not flying |
| 12 | 1 | `(midline_0<=6 && midline_1<=10 || midline_0<=6 && midline_2<=10) && sideway_val[0]>=4 && sideway_val[1]>=1 && (sideway_val[3]>=2 || sideway_val[2]>=4)` | Same cluster pattern but M5 sideways trend stronger (>=4); M15 still sideways or not flying |
| 13 | 1 | `(midline_0<=6 && midline_1<=10 || midline_0<=6 && midline_2<=10) && sideway_val[0]>=4 && sideway_val[1]>=2` | Cluster pattern; M5 sideways trend moderate (>=4); M15 moderate sideways (>=2); H4/M30 not flying |
| 21 | 2 | `(midline_0<=6 && midline_0_1<=6) && sideway_val[0]>=6` | M5+M15 cluster sustained for two bars; M5 strongly sideways (>=6) |
| 22 | 2 | `(midline_0<=6 && midline_0_1<=6) && sideway_val[0]>=4 && sideway_val[1]>=2` | Same cluster pattern; M5 moderate sideways (>=4); M15 sideways or not flying (>=2) |
| 23 | 2 | `(midline_0<=6 && midline_0_1<=6) && sideway_val[1]>=2 && sideway_val[3]>=5` | Same cluster pattern; M15 sideways or not flying (>=2); H4 strongly sideways (>=5) |
| 24 | 2 | `(midline_0<=6 && midline_0_1<=6) && sideway_val[0]>=5 && sideway_val[1]>=1` | Same cluster pattern; M5 moderate sideways (>=5); M15 not flying (>=1) |
| 31 | 3 | `(midline_0<=10 && midline_1<=15) && sideway_val[0]>=4 && sideway_val[1]>=2` | Wider cluster pattern; M5 sideways trend (>=4); M15 sideways or not flying (>=2) |
| 32 | 3 | `(midline_0<=10 && midline_1<=15) && sideway_val[1]>=2 && sideway_val[3]>=5` | Wider cluster pattern; M15 sideways or not flying (>=2); H4 strongly sideways (>=5) |
| 41 | 4 | `sideway_selected[1] != 0 && midline_0<=6 && midline_1<=6 && midline_2<=10 && (sideway_val[0]>=1 || sideway_val[1]>=1) && sideway_val[2]>=2 && sideway_val[3]>=2 && sideway_val[4]>=2` | Previous bar was sideways; all TFs now clustered tighter; H4/M30/M15 not flying, M5 at least mildly sideways |
| 51 | 5 | `sideway_selected[1] != 0 && (midline_0<=3 || midline_1<=3) && (midline_0<prev_midline_0 || midline_1<prev_midline_1) && sideway_val[1]>=6` | Previous bar was sideways; M5+M15 cluster further tightening (<=3 and shrinking); M15 strongly sideways (>=6) |

---

## Classification dispatch (sequence view)

**TofySideway is a CLASSIFIER, not a trading strategy. The terminal outputs are sideways CODES (S_11..S_51, or none), NOT trade actions.** This diagram shows the DISPATCH ORDER of the tier cascade — each tier only fires if all earlier tiers were false (mutual exclusion via `sideway_selected[0] == 0` guards).

```mermaid
sequenceDiagram
    participant IN as Inputs per M5 bar
    participant CL as Cluster distances
    participant CLS as Classifier tier cascade
    participant CODE as Output code
    Note over IN,CODE: DETECTOR — outputs a code, never a trade
    IN->>CL: compute midline distances M5-M15, M15-M30, M15-H1
    IN->>CLS: score sideway_val per TF (plus4 diffmid, plus2 BBWunder500, plus1 flyshrink)
    CL->>CLS: pass cluster distances
    CLS->>CODE: TIER1 (cluster M5M15 max6 and M15M30 max10 or M15H1 max10) then S_11 or S_12 or S_13
    CLS->>CODE: TIER2 (M5M15 max6 two bars, no prior code) then S_21 or S_22 or S_23 or S_24
    CLS->>CODE: TIER3 (M5M15 max10 and M15M30 max15, no prior code) then S_31 or S_32
    CLS->>CODE: TIER4 (prev sideways, tight cluster) then S_41
    CLS->>CODE: TIER5 (prev sideways, cluster shrinking) then S_51
    CLS->>CODE: else code 0 (no sideways)
    Note over CLS,CODE: tiers checked top to bottom, first match wins, mutually exclusive
```

**Figure: TofySideway classification sequence.** The dispatcher tier cascade — tier 1 fires first, and only if it fails does tier 2 get checked, and so on. Each terminal node is a sideways CODE (S_11..S_51, or none), never a trade operation.
![TofySideway sequence](Backtest_data/extras/DRAWIO/TofySideway_sequence.svg)

The sequence mirrors the flowchart tier cascade: tier 1 fires first, and only if it fails does tier 2 get checked, and so on. Each terminal node is a sideways CODE, never a trade operation. This view emphasizes the DISPATCH ORDER — the mutual exclusion enforced by `sideway_selected[0] == 0` guards at each tier boundary.

---

## Cross-reference

See `DUALTF_ARCHITECTURE.md` for the DualTF Architecture overview. TofySideway is a candidate FILTER for the (now-closed) DualTF entry or any future premise, and its trading value is UNTESTED.

---

## Improvement opportunities

Observations on the logic AS WRITTEN — not prescriptive rewrites:

- **Tier-4/5 coupling:** Codes 41 and 51 require `sideway_selected[1] != 0`, meaning they only fire after a tier-1/2/3 code fired on the previous bar. This persistence dependence is built into the design; earlier tiers must establish a sideways state before later tiers can tighten it.
- **Threshold progression:** The cluster thresholds move from <=6 (tiers 1-2) to <=10 (tier 3) to <=3 with shrinking (tier 5). The progression from 6→10→3 suggests tier-5 is meant for a further-tightening case, but the jump back to <=3 seems asymmetric compared to the earlier steps.
- **M5 dependence:** M5 (`sideway_val[0]`) is used in almost every code (11/12/13/21/22/24/31/41/51). Since M5 is the noisiest TF, several codes lean on it for the sideways signal — this may make the detector sensitive to M5 noise.
- **sideway_val weighting:** The +4/+2/+1 scheme assigns most weight to `BB_diffMid_Trend >= 3`. Whether this has a rationale or is ad-hoc needs investigation — for instance, whether the +4 points correlate with higher win-rate than the +2 points from `BBW_stage < 500`.

---
