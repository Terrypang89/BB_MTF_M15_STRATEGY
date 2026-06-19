# Architecture — TofyTrade5 Three-Layer System

System design and UML for TofyTrade5's three-layer architecture. For scenario/rule MEANINGS see `backtest_chart_analysis.md`; for the validation record see `references/fixtures/validation_status.md`.

## Three-Layer Overview

```mermaid
flowchart LR
    L1["**Layer 1**\nIdentifyScenario\nWHERE am I?"] --> L2["**Layer 2**\nPredictNext\nWHAT's next?"]
    L2 --> L3["**Layer 3**\nDecideAction\nWHAT to do?"]

    L1 -.->|ScenarioState| L2
    L2 -.->|Prediction| L3
```

- **Layer 1 — IdentifyScenario**: Given current BB state across all TFs, classify the market into a scenario + phase. **Built & validated** against March 2026 in-sample + Jan-Apr OOS data.
- **Layer 2 — PredictNext**: Given ScenarioState, score direction, confidence, target TF, timeline, and next scenario. Built but diffBBW damping thresholds need correction (see integration note 6 in `.mqh`).
- **Layer 3 — DecideAction**: Given ScenarioState + Prediction, select entry/exit condition from firing matrix. Built and enforced.

## TF Roles (cross-cut all layers)

These responsibilities are invariant across all three layers — they define what each TF contributes to the system.

| TF | Role | Layers that consume |
|----|------|---------------------|
| W1 | Macro bias — highest container candidate, sets directional a priori | L1 (container), L2 (direction score), L3 (X2 container-crack) |
| D1 | Macro bias — alignment check for A1, G-tier sub-state discriminator | L1 (A1/G1-G2), L2 (direction score), L3 (VETO via veto_priceloc in .py) |
| H4 | Trend / context — primary classifier (fly/shrink/sqz), phase driver | L1 (CHECK-HTF, phase), L2 (direction score), L3 (E3 chk1, X2) |
| M30 | Primary trend DRIVER — the leg ridden, E3 confinement check | L1 (compression routing), L2 (direction score), L3 (E3 chk4, X2) |
| M15 | Entry TRIGGER — flip detection, B-tier depth | L1 (B-tier, E-tier, flip detection), L2 (direction score), L3 (X2 fade) |
| M5 | Noise / unused for entry — SQZ count contributor only | L1 (cas_sqzCount, E3 chk3), L2 (not scored — index 0 excluded) |

---

## Part 3 — Layer 1: IdentifyScenario (BUILT & VALIDATED)

### 3.1 Interface — Class/Struct Diagram

This diagram shows the actual data structures: what IdentifyScenario reads (input per-TF BB data) and what it returns (ScenarioState). Fields marked with `[L2]` / `[L3]` indicate the output contract consumed by downstream layers.

```mermaid
classDiagram
    class BB_TF_Data {
        <<per-TF input>>
        int BBW_stage
        int BB_diffMid_Trend
        int BBUpDn_state
        double diffBBW*
        double BBUppLV
        double BBLowLV
        double BB_Mid
    }

    class BB_datas {
        <<array input>>
        BB_TF_Data[0]   *M5*
        BB_TF_Data[1]   *M15*
        BB_TF_Data[2]   *M30*
        BB_TF_Data[3]   *H1*
        BB_TF_Data[4]   *H4*
        BB_TF_Data[5]   *D1*
        BB_TF_Data[6]   *W1*
    }

    class ScenarioState {
        SCENARIO scenario*[L2,L3]
        PHASE phase*[L2,L3]
        int cas_shrinkTF*[L3]
        int cas_sqzCount*[L3]
        bool b1_block*[L3]
        bool b2_pink*[L2,L3]
        int container_tf*[L2,L3]
        int container_dir*[L3]
        double container_diffbbw*[L3]
        int priceloc*[L3]
        int pivot_substate
        string info
    }

    class IdentifyScenario {
        +ScenarioState IdentifyScenario(BB_datas[], close_prices[])
    }

    BB_datas --> IdentifyScenario : feeds
    IdentifyScenario --> ScenarioState : returns
```

**Field meanings (ScenarioState):**

| Field | Type | Meaning | Consumed by |
|-------|------|---------|-------------|
| `scenario` | SCENARIO | Identified scenario (A1..C3) | L2, L3 |
| `phase` | PHASE | Phase classification (PH_1..PH_6) | L2, L3 |
| `cas_shrinkTF` | int | Highest TF in shrink (1=M15..5=D1, -1=none), per §12d | L3 |
| `cas_sqzCount` | int | Count of M5..H1 TFs in SQZ (400-499), per §12d | L3 |
| `b1_block` | bool | M15 diffMid >= 3 (blocks flip-entries) | L3 (read from struct by DecideAction line 809; Python harness recomputes from raw BB data — no ScenarioState struct) |
| `b2_pink` | bool | M15 AND M30 both BBW 400-499 (forces flat) | L3 (read from struct by X4 invariant line 1040 + ASSERT line 784; L2 uses `scenario==E2` as proxy, not b2_pink directly; Python harness recomputes) |
| `container_tf` | int | Highest TF with committed fly, -1 if none | L2, L3 |
| `container_dir` | int | Container's diffMid (1=UP, 2=DN, 0=none) | L3 |
| `container_diffbbw` | double | Container health: >0 room, <=0 aging | L3 |
| `priceloc` | int | Price vs container bands: -2..+2 | L3 |
| `pivot_substate` | int | G-tier: 0=N/A, 1=PIVOT-PENDING, 2=G-REVERSAL | display only |
| `info` | string | Human-readable reason string | logging |

> **Note:** `dbbwH4` is NOT a ScenarioState field — it is computed internally and pushed to ring buffers (`g_dbbw_ring`, `s_dbbwH4_hist`) used by `ClassifyPhase()` and early F-tier detection. The value is available to callers via `ADiffBBW(bb, 4)` but is not part of the output contract.

**MQL5 vs Python consumption:** MQL5 L3 reads `b1_block`, `b2_pink`, and `cas_sqzCount` directly from the ScenarioState struct. The Python harness has no ScenarioState struct — it recomputes these from raw BB data in the simulation loop. This is a harness architecture difference, not a behavioral one, except for `veto_priceloc` (Python adds D1 as veto source — see known divergence in `validation_status.md`).

**Output contract summary:**
- Layer 2 consumes: `scenario`, `phase`, `container_tf`, `container_dir`, `b2_pink`
- Layer 3 consumes: all fields except `pivot_substate` (display-only) and `info` (logging)

### 3.2 Control Flow — Activity Diagram

This flowchart shows the **as-built** evaluation order of `IdentifyScenario`, matching the validated Decisions 1-6. Note: the early F-tier check fires **before** G-tier (Step 3 in code), not after compression routing — this is the Cluster 1 fix that prevents misclassifying H4-exiting-compression as G when it should be F.

```mermaid
flowchart TD
    Start["Start: BB_datas[0..6] + close_prices"] --> Init["Initialize ScenarioState defaults<br/>scenario=SC_NONE phase=PH_NONE"]

    Init --> Cascade["§12d: Compute cascade decoders<br/>cas_shrinkTF = highest shrink TF M15..D1<br/>cas_sqzCount = SQZ count M5..H1"]

    Cascade --> Derived["Compute derived states<br/>b1_block, b2_pink, ltf_shrinkTF,<br/>container_tf/dir/diffbbw, priceloc"]

    Derived --> Phase["§13: ClassifyPhase via diffBBW_H4 ring"]

    Phase --> H4Class["§12: Classify H4 state<br/>h4_fly, h4_shrink, h4_sqz<br/>+ D1 direction + D1 fly"]

    H4Class --> EarlyF{"Early F-tier?<br/>H4 exiting compression<br/>diffBBW recovering"}
    EarlyF -->|yes| FSub["Route to F1/F2/F3<br/>based on D1+M30 confirm"]
    FSub --> Return([return ScenarioState])

    EarlyF -->|no| H4Sqz{"h4_sqz?"}
    H4Sqz -->|yes| GTier["G-tier: Direction pivot<br/>G1 = M5 break same as D1<br/>G2 = M5 break opposite D1<br/>G3 = no M5 break / D1 not flying<br/>G4 = phase PH_6<br/>pivot_substate = 1 or 2"]
    GTier --> Return

    H4Sqz -->|no| H4Shrink{"h4_shrink?"}
    H4Shrink -->|yes| E4["E4 — HTF compressing"]
    E4 --> Return

    H4Shrink -->|no| ConfComp{"confirmed_compression?<br/>cas_sqzCount >= 1<br/>OR ltf_shrinkTF >= 1 + diffBBW < 30"}

    ConfComp -->|yes| D5{"Decision 5:<br/>H1-SQZ this bar<br/>AND prior-bar?"}

    D5 -->|"established<br/>(2+ bars H1-SQZ)"| D5Sub{"M15+M30 both SQZ?"}
    D5Sub -->|yes| E2a["E2 — H1-SQZ established,<br/>M15+M30 SQZ"]
    D5Sub -->|no| E1a["E1 — H1-SQZ established"]
    E2a --> Return
    E1a --> Return

    D5 -->|"recovery<br/>(H1 exited SQZ,<br/>compression persists)"| E1b["E1 — H1-SQZ recovery"]
    E1b --> Return

    D5 -->|"onset<br/>(first bar H1-SQZ)"| B3onset["B3 — H1-SQZ onset"]
    B3onset --> Return

    D5 -->|none of above| D2{"Decision 2:<br/>h4_fly + diffBBW > 5<br/>+ no ltf_shrink + no prev H1-SQZ<br/>+ cas_sqzCount==1"}
    D2 -->|"D1 aligned<br/>(D1 fly + same dir as H4)?"| D2Sub{"D1 aligned<br/>(D1 fly + same dir as H4)?"}
    D2Sub -->|yes| A1c["A1 — transient SQZ,<br/>D1 aligned"]
    D2Sub -->|no| A2c["A2 — transient SQZ,<br/>D1 not aligned"]
    A1c --> Return
    A2c --> Return

    D2 -->|no| Ecomp{"cas_sqzCount >= 2?"}
    Ecomp -->|yes| EcompSub{"b2_pink?"}
    EcompSub -->|yes| E2b["E2 — M15+M30 both SQZ"]
    EcompSub -->|no| E1b2["E1 — LTF SQZ"]
    E2b --> Return
    E1b2 --> Return

    Ecomp -->|no| Bcomp{"ltf_shrinkTF >= 1?"}
    Bcomp -->|yes| BDecode["B-tier decoder:<br/>max(shrink_depth, sqz_depth)<br/>+ cas_sqzCount → B1/B2/B3"]
    BDecode --> Return

    Bcomp -->|no| A2safe["A2 — SQZ without LTF shrink<br/>(safety net)"]
    A2safe --> Return

    ConfComp -->|no| H4Fly{"h4_fly?"}
    H4Fly -->|yes| A1Sub{"D1 aligned<br/>(D1 fly + same dir as H4)?"}
    A1Sub -->|yes| A1a["A1 — H4+D1 fly aligned"]
    A1Sub -->|no| A2a["A2 — H4 fly, D1 not aligned"]
    A1a --> Return
    A2a --> Return

    H4Fly -->|no| Default["Default: A2 — conservative"]
    Default --> UpdatePrev["Update s_prevH1Sqz = H1 in SQZ"]
    UpdatePrev --> Return
```

**Contract established:** IdentifyScenario returns a fully populated ScenarioState. The evaluation order is: cascade decoders → phase → CHECK-HTF (h4_sqz/h4_shrink) → compression routing → h4_fly → default. This implements the Part 2 HTF-first principle: H4 state is checked before LTF compression, and D1 direction gates G-tier sub-states (G1 vs G2).

### 3.3 Scenario State Machine — State Diagram

This diagram shows the scenario lifecycle: how the system transitions between tiers as market conditions evolve. Transition conditions are derived from the code's branch logic, not assumed.

```mermaid
stateDiagram-v2
    [*] --> A

    A --> B: "LTF shrink appears<br/>(cas_sqzCount >= 1<br/>or ltf_shrinkTF >= 1)"
    B --> E: "H1-SQZ established<br/>(2+ bars, Decision 5)"
    E --> G: "H4 enters SQZ<br/>(h4_sqz = true)"

    G --> F: "H4 exits SQZ with expansion<br/>(diffBBW recovering, early F-tier)"
    G --> C: "G-reversal resolves<br/>(M5 break confirmed,<br/>pivot_substate = 2)"

    F --> A: "Expansion completes<br/>(F3 → new trend phase)"
    C --> A: "Reversal completes<br/>(C2 → new A-tier)"

    note right of G
        OOS-UNVALIDATED:<br/>
        G→C transition never fired<br/>
        on Jan-Apr OOS data.<br/>
        0 of 7 H4-SQZ episodes<br/>
        resolved as reversal.<br/>
        See validation_status.md.
    end note

    note right of C
        UNIMPLEMENTED:<br/>
        G2→C1→C2/C3 forward<br/>
        transitions not in harness.<br/>
        C-tier states are<br/>
        doc-only in identify_scenario.<br/>
        See validation_status.md.
    end note

    state G {
        [*] --> PIVOT_PENDING: "M5 break not confirmed<br/>(pivot_substate = 1)"
        PIVOT_PENDING --> G_REVERSAL: "M5 break confirmed<br/>(pivot_substate = 2)"
        PIVOT_PENDING --> [*]: Resolved to F-tier
    }
```

**Contract established:** The scenario machine is a left-side (A→B→E→G) then right-side (F continuation or C reversal) cycle. The G→F edge is OOS-validated (7/7 episodes). The G→C edge is structurally defined but unvalidated — both the discriminator and the C-tier state transitions are unimplemented in the harness.

### 3.4 Validation Status

| Component | Status | Detail |
|-----------|--------|--------|
| A-tier routing (A1/A2) | OOS-VALIDATED | 103/349 snapshots, D1 alignment working |
| B-tier routing (B1/B2/B3) | OOS-VALIDATED | 81/349 snapshots, depth decoder working |
| E-tier routing (E1/E2/E4) | OOS-VALIDATED | 153/349 snapshots |
| G-tier compression entry | OOS-VALIDATED | 36/36 H4-SQZ bars detected correctly |
| F continuation resolution | OOS-VALIDATED | 7/7 episodes resolved as F |
| Decision 5 (onset/established) | OOS-VALIDATED | H1-SQZ tracking consistent |
| Early F-tier detection | OOS-VALIDATED | Fires before G-tier, prevents misclassification |
| **G reversal branch (G→C)** | **HYPOTHESIS** | Never fired on OOS data — 0/7 episodes |
| **G-vs-F discriminator** | **HYPOTHESIS** | Requires reversal episodes — none in current data |
| **G2→C1→C2/C3 transitions** | **UNIMPLEMENTED** | Not in identify_scenario, doc-only |
| VETO-AT-TARGET | OOS-VALIDATED | Architecture-enforced, item 5 PASS |
| veto_priceloc (L3) | **KNOWN DIVERGENCE** | Python stricter than MQL5 — D1 veto when not container |

For the full validation record with episode detail, see [`references/fixtures/validation_status.md`](fixtures/validation_status.md).

---

## Part 4 — Layer 2: PredictNext (DESIGN — built Phase 3)

Consumes Layer 1 ScenarioState + per-TF BB data → outputs Prediction for Layer 3. D1/W1 do their heaviest work here — resolving the H4 pivot that Part 3 left pending. For prediction rule MEANINGS see `backtest_chart_analysis.md` Part 4 (Rules 1-4); this section designs the layer structure, not rule values.

### 4.0 Link from Layer 1 — what Part 4 consumes from Part 3

**ScenarioState consumption table** — every Part 3 field mapped to Part 4 use:

| ScenarioState field (from Part 3 §3.1) | How PredictNext uses it |
|---|---|
| `scenario` | Selects which prediction rule applies; scenario-gates confidence and next-scenario edges |
| `phase` | Scenario-gates confidence (PH_4 → None, PH_5 → explosive); drives timeline estimate |
| `b2_pink` | Gating — forces confidence=0 (no prediction possible, M15+M30 locked in SQZ) |
| `container_tf` | The target the prediction aims at (Rule 2: next confinement boundary) |
| `pivot_substate` | G-tier: 0=N/A, 1=PIVOT-PENDING (direction unresolved — D1/W1 bias predicts G→F vs G→C), 2=G-REVERSAL (reversal_flag=True) |
| `cas_shrinkTF` | Not used directly by Layer 2 — consumed by Layer 3 (decoder size) |
| `cas_sqzCount` | Not used directly by Layer 2 — consumed by Layer 3 (decoder size). Provides compression depth context for timeline estimate. |
| `b1_block` | Not used by Layer 2 — consumed by Layer 3 (entry gating) |
| `container_dir` | Not used directly — direction is scored from per-TF BB data (see gap below) |
| `container_diffbbw` | Not used directly — container health scored from per-TF BB data via ADiffBBW |
| `priceloc` | Not used by Layer 2 — consumed by Layer 3 (E3, VETO, X1) |
| `info` | Not used — logging field from Part 3 |

**GAP — per-TF BB data**: PredictNext needs per-TF BB data (stage, mid, diffBBW, BBUpDn) to score direction across TFs. ScenarioState does NOT expose this — it exposes `container_tf`, `container_dir`, and `container_diffbbw` for the container only. Therefore Part 4 receives **both** ScenarioState (for scenario/phase gating) **and** the raw `BB_datas[]` array (for per-TF direction scoring). This matches the MQL5 signature: `PredictNext(ScenarioState &s, BB_MTF_Data_struct &bb[])`.

**GAP — D1/W1 prior-bar state**: Direction scoring needs `stage[LA_1]` and `mid[LA_1]` (prior-bar) for transition detection (sqz→fly, fly→shrink). ScenarioState doesn't store prior-bar per-TF state. Part 4 reads this directly from `BB_datas[tf].BBW_stage[LA_1]` — the same raw array it already receives. No additional Part 3 change needed.

**Impact — how Part 3 constrains Part 4:**

1. **Can only predict from what ScenarioState exposes.** Part 4 can gate on scenario, phase, and b2_pink. Everything else (per-TF direction scoring, diffBBW damping) requires raw BB data. If a prediction needed per-TF diffBBW and Part 3 didn't pass BB_datas, that would be an unresolvable gap — but the dual-input design avoids this.
2. **G-pivot handoff.** Part 3 marks G-tier as "pivot-pending" (pivot_substate=1) and sets direction=UNKNOWN — it does NOT resolve the pivot. Part 4 INHERITS this unresolved pivot as its primary job: D1/W1 bias predicts whether G resolves as F (continuation) or C (reversal). This is the most important Part 3 → Part 4 handoff.
3. **OOS-unvalidated propagation.** Part 3 flags G→C transition as OOS-UNVALIDATED (0 of 7 OOS episodes resolved as reversal) and G2→C1→C2/C3 as UNIMPLEMENTED. Any Part 4 prediction that depends on G→C resolution inherits these flags — it is also OOS-UNVALIDATED.
4. **Fields Part 3 computes but Part 4 ignores.** cas_shrinkTF, cas_sqzCount, b1_block, priceloc are Layer 3 fields. Part 4 doesn't consume them — they flow ScenarioState → Layer 3 directly.

### 4.0a Part 3 → Part 4 Link (visual)

Three diagrams showing how Layer 1 connects to and constrains Layer 2 — the handoff made visible, not just the table above.

#### Diagram 1 — Cross-Layer Data-Flow (field → function wiring)

Which ScenarioState field wires to which Layer 2 sub-function. Shows the dual-input: ScenarioState (gating) vs raw BB_datas (scoring).

```mermaid
flowchart LR
    subgraph L1["Layer 1 — IdentifyScenario"]
        ID["IdentifyScenario"]
    end

    subgraph SS["ScenarioState s (struct)"]
        sc["scenario"]
        ph["phase"]
        b2["b2_pink"]
        piv["pivot_substate"]
        ct["container_tf"]
    end

    subgraph BB["BB_datas[] (raw per-TF)"]
        raw["raw per-TF data<br/>BBW_stage / BB_diffMid_Trend"]
        d1w1["D1/W1 per-TF data"]
    end

    subgraph L2["Layer 2 — PredictNext"]
        SG["ScenarioGate"]
        DS["DirectionScore"]
        GTR["GTierResolve"]
        ASM["Assemble"]
        PNX["PredictNext"]
    end

    subgraph OUT["Output"]
        PRED["Prediction p"]
        L3["Layer 3 (Part 5)"]
    end

    ID --> SS
    ID -->|"raw BB_datas[]"| BB
    sc --> SG
    ph --> SG
    b2 --> SG
    piv --> GTR
    ct --> ASM
    raw -->|"NOT from ScenarioState"| DS
    d1w1 --> GTR
    piv -->|"pivot_substate"| GTR
    SG --> ASM
    DS --> ASM
    GTR --> ASM
    ASM --> PRED
    PRED --> L3
```

*Review criterion: I can trace any ScenarioState field to the exact sub-function that consumes it.*

#### Diagram 2 — Impact / Constraint (how Part 3 shapes Part 4)

Three ways Layer 1's design constrains Layer 2 — the unresolved pivot, the OOS flag, the dual-input gap.

```mermaid
flowchart TD
    subgraph A["(a) G-PIVOT HANDOFF — core handoff"]
        L1a["Layer 1: H4 SQZ → G-tier<br/>sets pivot_substate<br/>direction = UNKNOWN<br/>(pivot unresolved)"]
        L2a["Layer 2 GTierResolve INHERITS:<br/>D1/W1 bias predicts<br/>G→F continuation vs G→C reversal"]
        L1a -->|"Part 3 stops at pivot-pending;<br/>resolving it IS Part 4 primary job"| L2a
    end

    subgraph B["(b) OOS-UNVALIDATED PROPAGATION"]
        L1b["Layer 1: G→C flagged<br/>OOS-UNVALIDATED<br/>0 of 7 OOS episodes"]
        L2b["Layer 2: any G→C prediction<br/>INHERITS OOS-UNVALIDATED"]
        L1b -.->|"flag propagates"| L2b
    end

    subgraph C["(c) DUAL-INPUT GAP"]
        L1c["ScenarioState exposes<br/>container only<br/>NOT per-TF detail"]
        L2c1["ScenarioState<br/>(gating)"]
        L2c2["BB_datas[]<br/>(per-TF scoring)"]
        L1c -->|"so PredictNext takes BOTH"| L2c1
        L1c -->|"so PredictNext takes BOTH"| L2c2
    end
```

*Review criterion: I see WHY Part 4 is shaped the way it is — the unresolved pivot it inherits, the flag it carries, the raw data it needs.*

#### Diagram 3 — Detailed Cross-Layer Sequence (runtime call order)

Per-bar call sequence at the skeleton-function level — the exact functions the skeleton implements.

```mermaid
sequenceDiagram
    participant Caller as "Caller<br/>(OnBar)"
    participant Ident as "IdentifyScenario"
    participant SS as "ScenarioState s"
    participant PNX as "PredictNext"
    participant SG as "ScenarioGate"
    participant DS as "DirectionScore"
    participant GTR as "GTierResolve"
    participant ASM as "Assemble"
    participant DecAct as "DecideAction"

    Caller->>Ident: "IdentifyScenario(bb)"
    Ident->>Ident: "decoders → ClassifyPhase →<br/>H4 classify → set<br/>scenario/phase/pivot_substate/container"
    Ident-->>Caller: "ScenarioState s"
    Note over Caller,SS: "HANDOFF: s leaves L1, enters L2"

    Caller->>PNX: "PredictNext(s, bb)"
    PNX->>SG: "ScenarioGate(s) — reads<br/>scenario/phase/b2_pink"
    SG-->>PNX: "suppress flag [TBD-GATE-3 stub]"

    PNX->>DS: "DirectionScore(bb) — reads<br/>RAW bb (dual-input gap)"
    DS-->>PNX: "score [TBD-GATE-3 stub]"

    alt "s.pivot_substate > 0 (G-tier)"
        PNX->>GTR: "GTierResolve(s, bb) —<br/>pivot_substate + D1/W1"
        note over GTR : "OOS-UNVALIDATED"
        GTR-->>PNX: "reversal flag [TBD-GATE-3 stub]"
    end

    PNX->>ASM: "Assemble(s, score, reversal)"
    ASM-->>PNX: "Prediction p"
    PNX-->>Caller: "Prediction p"

    Caller->>DecAct: "DecideAction(s, p, bb)<br/>[Part 5, stubbed]"
```

*Review criterion: this reads as the exact call sequence the skeleton implements — diagram and code are two views of one structure.*

### 4.0b Cross-Layer Sequence — Per-Bar Call Flow (L1 → L2 → L3)

This diagram shows the function-level call sequence at runtime. Every L2 sub-function is a TBD-GATE-3 stub — structure built, logic deferred.

```mermaid
sequenceDiagram
    participant Caller as "Caller<br/>(OnBar / main handler)"
    participant IdentScen as "IdentifyScenario<br/>(bb, close)"
    participant L1internal as "L1 Internal<br/>(cascade, ClassifyPhase,<br/>H4 classify, container)"
    participant SS as "ScenarioState<br/>s"
    participant PredNext as "PredictNext<br/>(s, bb)"
    participant SG as "ScenarioGate(s)"
    participant DS as "DirectionScore(bb)"
    participant GTR as "GTierResolve(s, bb)"
    participant ASM as "Assemble(s, total,<br/>reversal, p)"
    participant DecAct as "DecideAction<br/>(s, p, bb)"

    rect rgb(240, 248, 255)
    Note over Caller,SS: "LAYER 1 — IdentifyScenario (VALIDATED)"
    Caller->>IdentScen: "BB_datas[] bb + close[]<br/>IdentifyScenario(bb, close)"
    activate IdentScen
    IdentScen->>L1internal: "Cascade decoders (cas_shrinkTF,<br/>cas_sqzCount)"
    IdentScen->>L1internal: "ClassifyPhase(bb)"
    IdentScen->>L1internal: "H4 classify (stage/mid/diffBBW)"
    IdentScen->>L1internal: "Set scenario / phase / pivot_substate<br/>Set container_tf / container_dir"
    IdentScen->>L1internal: "Set b2_pink / b1_block"
    IdentScen-->>SS: "ScenarioState s"
    deactivate IdentScen
    end

    rect rgb(255, 248, 240)
    Note over Caller,DecAct: "LAYER 2 — PredictNext (SKELETON — TBD-GATE-3)"
    Caller->>PredNext: "ScenarioState s + BB_datas[] bb<br/>PredictNext(s, bb)"
    activate PredNext

    PredNext->>PredNext: "Initialize Prediction defaults<br/>direction=0, target_tf=-1, ..."

    Note over PredNext,SG: "HANDOFF: s.scenario, s.phase, s.b2_pink"
    PredNext->>SG: "ScenarioState s"
    activate SG
    SG-->>PredNext: "suppress (bool)"
    deactivate SG
    Note over SG: "TBD-GATE-3 stub:<br/>returns true (always suppress)"

    alt suppress == true
        PredNext->>PredNext: "p.confidence=0, p.direction=0"
    end

    Note over PredNext,DS: "DUAL INPUT: raw bb[] (NOT s)"
    PredNext->>DS: "BB_datas[] bb"
    activate DS
    DS-->>PredNext: "total (int)"
    deactivate DS
    Note over DS: "TBD-GATE-3 stub:<br/>reads per-TF stage/mid from bb<br/>returns 0"

    alt s.pivot_substate > 0 (G-tier)
        Note over PredNext,GTR: "G-TIER BRANCH: OOS-UNVALIDATED"
        PredNext->>GTR: "ScenarioState s + BB_datas[] bb"
        activate GTR
        GTR-->>PredNext: "reversal (bool)"
        deactivate GTR
        Note over GTR: "OOS-UNVALIDATED:<br/>0 reversal episodes in OOS<br/>TBD-GATE-3 stub:<br/>returns false"
    else s.pivot_substate == 0
        PredNext->>PredNext: "reversal = false (default)"
    end

    PredNext->>ASM: "s, total, reversal, Prediction &p"
    activate ASM
    ASM-->>PredNext: "Prediction p (filled)"
    deactivate ASM
    Note over ASM: "TBD-GATE-3 stub:<br/>safe defaults"

    PredNext-->>Caller: "Prediction p"
    deactivate PredNext
    end

    rect rgb(250, 250, 250)
    Note over Caller,DecAct: "LAYER 3 — DecideAction (PHASE 4 — NOT WIRED YET)"
    Caller->>DecAct: "s, p, bb, ATRSL1BUF, close, BUYS, SELLS"
    Note over DecAct: "Stubbed — Prediction not yet<br/>consumed. Phase 4 work."
    end
```

**Critical details visible in this diagram:**

- **HANDOFF POINT:** ScenarioState `s` flows from IdentifyScenario → PredictNext → ScenarioGate. This is the exact interface boundary between L1 and L2.
- **DUAL INPUT:** PredictNext receives both `s` (ScenarioGate reads it) and `bb` (DirectionScore reads it). The gap-resolution is visible: ScenarioGate reads `s.scenario`, `s.phase`, `s.b2_pink`; DirectionScore reads raw `bb[]` per-TF stage/mid.
- **G-TIER BRANCH:** GTierResolve fires only when `s.pivot_substate > 0`. Marked OOS-UNVALIDATED.
- **STUB MARKERS:** Every L2 sub-function is annotated as TBD-GATE-3. No rule values are present — structure only.
- **LAYER 3 NOT WIRED:** DecideAction receives Prediction `p` but does not consume it yet. Phase 4 work.

### 4.1 Interface — Class Diagram

```mermaid
classDiagram
    class ScenarioState {
        <<from Part 3>>
        SCENARIO scenario
        PHASE phase
        bool b2_pink
        int container_tf
        int pivot_substate
    }

    class BB_MTF_Data_struct {
        <<per-TF raw input>>
        int BBW_stage[LA, LA_1]
        int BB_diffMid_Trend[LA, LA_1]
        int BBUpDn_state[LA]
        double diffBBW[LA]
        double BBUppLV[LA]
        double BBLowLV[LA]
    }

    class Prediction {
        <<output contract for Part 5>>
        int direction     1=BUY / 2=SELL / 0=NEUTRAL
        int target_tf     container_tf or scenario fallback
        int timeline_bars coarse, in M5 bars
        SCENARIO next_scenario
        int confidence    0-100
        bool reversal     G→C reversal flag
        string info       logging
    }

    class PredictNext {
        +Prediction PredictNext(ScenarioState &s, BB_MTF_Data_struct &bb[])
    }

    ScenarioState --> PredictNext : gates
    BB_MTF_Data_struct --> PredictNext : scores
    PredictNext --> Prediction : returns
```

**Prediction field meanings:**

| Field | Type | Meaning | Rule | Consumed by Part 5 |
|---|---|---|---|---|
| `direction` | int | Predicted direction (1=BUY, 2=SELL, 0=NEUTRAL) | Rule 1 | Entry side |
| `target_tf` | int | Which TF band is the target (0=M5..5=D1, -1=none) | Rule 2 | Exit target |
| `timeline_bars` | int | Coarse estimate in M5 bars (TBD — GATE 3) | Rule 3 | Hold-duration check |
| `next_scenario` | SCENARIO | Predicted next scenario | Rule 4 | Scenario-transition gating |
| `confidence` | int | 0-100, drives Part 5 size | Rule 5 | Size multiplier |
| `reversal` | bool | True if HTF LTF diverge (reversal imminent) | Rule 1 | Exit-not-entry signal |
| `info` | string | Debug string (score components) | logging | — |

**Output contract:** Prediction is the structured output Part 5 consumes. direction → entry side; confidence → size; target_tf → exit target TF; reversal → exit-not-entry signal.

### 4.2 Sequence Diagram — per-bar flow

This diagram makes the consumption arrow explicit: Prediction is CONSUMED by Part 5, not decorative. (TofyTrade4 PredictNextTrend was drawn-and-discarded — its output was never consumed by the firing matrix.)

```mermaid
sequenceDiagram
    participant Tick as Tick (per bar)
    participant L1 as Layer 1<br/>IdentifyScenario
    participant L2 as Layer 2<br/>PredictNext
    participant L3 as Layer 3<br/>DecideAction

    Tick->>L1: "BB_datas[] + close[]"
    L1->>L1: Classify scenario, phase, cascade
    L1-->>Tick: ScenarioState s

    Tick->>L2: "ScenarioState s + BB_datas[]"
    L2->>L2: Scenario-gate (PH_4/G4→None)
    L2->>L2: Direction score (per-TF)
    L2->>L2: G-tier: D1/W1 predicts G→F vs G→C
    L2-->>Tick: Prediction p

    Tick->>L3: "ScenarioState s + Prediction p + BB_datas[]"
    L3->>L3: Firing matrix (scenario,phase row)
    L3->>L3: Entry/exit/size/stop decision
    L3-->>Tick: TradeAction
```

**Key difference from TofyTrade4:** In TofyTrade4, PredictNextTrend returned a TrendPrediction that was drawn on chart but NOT consumed by the entry/exit logic — the firing matrix operated independently. In TofyTrade5, Prediction flows into DecideAction: direction determines entry side, confidence determines size, target_tf determines exit boundary, reversal determines whether the signal is an exit or entry.

#### Detailed Internal Sequence — PredictNext sub-function calls

This diagram breaks PredictNext into its internal sub-function calls, showing data flow between steps. Each sub-function is a stub (TBD-GATE-3) — no rule values.

```mermaid
sequenceDiagram
    participant Caller as "DecideAction / Tick"
    participant PNX as "PredictNext(s, bb)"
    participant SG as "ScenarioGate(s)"
    participant DS as "DirectionScore(bb)"
    participant GTR as "GTierResolve(s, bb)"
    participant ASM as "Assemble(s, total, reversal, p)"

    Caller->>PNX: "ScenarioState s + BB_datas[] bb"
    activate PNX

    PNX->>PNX: "Initialize Prediction defaults<br/>direction=0, target_tf=-1, timeline_bars=0,<br/>next_scenario=SC_NONE, confidence=0,<br/>reversal=false, info=''"
    Note over PNX: "Safe defaults — no rule values"

    PNX->>SG: "ScenarioState s (scenario, phase, b2_pink)"
    activate SG
    SG-->>PNX: "suppress (bool)"
    deactivate SG
    Note over SG: "TBD-GATE-3:<br/>PH_4 / G4 / E2 suppression<br/>Returns true = suppress all"

    alt suppress == true
        PNX->>PNX: "Set p.confidence=0, p.direction=0<br/>Skip scoring (optional optimization)"
    end

    PNX->>DS: "BB_datas[] bb (per-TF raw data)"
    activate DS
    DS-->>PNX: "total (int) — aggregate score"
    deactivate DS
    Note over DS: "TBD-GATE-3:<br/>Per-TF TF_DirectionScore +<br/>diffBBW damping + aggregation<br/>diffBBW: re-derive absolute scale<br/>Returns 0 (safe default)"

    PNX->>PNX: "Check s.pivot_substate > 0"

    alt pivot_substate > 0
        PNX->>GTR: "ScenarioState s + BB_datas[] bb"
        activate GTR
        GTR-->>PNX: "reversal (bool)"
        deactivate GTR
        Note over GTR: "OOS-UNVALIDATED:<br/>D1/W1 bias → G→F vs G→C<br/>TBD-GATE-3:<br/>Returns false (safe default)"
    else pivot_substate == 0
        PNX->>PNX: "reversal = false (default)"
    end

    PNX->>ASM: "ScenarioState s, total, reversal, Prediction &p"
    activate ASM
    ASM-->>PNX: "Prediction p (filled)"
    deactivate ASM
    Note over ASM: "TBD-GATE-3:<br/>total → direction/confidence<br/>container_tf → target_tf<br/>phase → timeline_bars<br/>scenario → next_scenario<br/>Safe defaults: direction=0,<br/>confidence=0, target_tf=container_tf"

    PNX->>PNX: "p.info = KVi('tot', total)"

    PNX-->>Caller: "Prediction p"
    deactivate PNX
```

**Data consumption notes:**
- `ScenarioGate` consumes only `ScenarioState` fields: `scenario`, `phase`, `b2_pink`
- `DirectionScore` consumes only raw `BB_datas[]` — reads per-TF `BBW_stage`, `BB_diffMid_Trend` (current + prior bar via `LA`/`LA_1`)
- `GTierResolve` consumes both: `ScenarioState.pivot_substate` + raw `BB_datas[]` for D1/W1 bias
- `Assemble` consumes `ScenarioState` fields: `scenario`, `phase`, `container_tf` + score from DirectionScore + reversal from GTierResolve

**Store-vs-recompute note:** MQL5 reads `BBW_stage[LA_1]` and `BB_diffMid_Trend[LA_1]` (prior-bar state) directly from the `BB_datas[]` struct. Python harness recomputes these from consecutive log snapshots. Must match bar-for-bar (per `validation_status.md` Phase 4 item).

### 4.3 Activity Diagram — internal flow

Flow only — no weights, thresholds, or formulas. All values TBD — GATE 3.

```mermaid
flowchart TD
    Start["Start: ScenarioState s + BB_datas[]"] --> Init["Initialize Prediction defaults<br/>direction=0, confidence=0, target_tf=-1"]

    Init --> Gate["Scenario-gate<br/>PH_4 or G4 or E2 → confidence=0, direction=0"]

    Gate --> Score["Direction scoring per-TF<br/>For each TF M15..W1:<br/>  TF_DirectionScore(stage, mid, prev_stage, prev_mid)<br/>  diffBBW damping<br/>  Weight by TF hierarchy"]

    Score --> Aggregate["Aggregate scores<br/>LTF + MTF + HTF totals → direction<br/>Magnitude → confidence"]

    Aggregate --> GTier{"G-tier?<br/>pivot_substate > 0"}
    GTier -->|yes| GPredict["D1/W1 bias predicts G→F vs G→C<br/>D1 same direction as H4 → F (continuation)<br/>D1 opposite → C (reversal)<br/>Set reversal flag if D1 opposes H4<br/>OOS-UNVALIDATED — 0 reversal episodes"]
    GTier -->|no| Target["Target TF (Rule 2)<br/>container_tf if > 0 else scenario fallback"]

    GPredict --> Target

    Target --> Timeline["Timeline estimate (Rule 3)<br/>Phase → coarse bar estimate TBD-GATE-3<br/>diffBBW as accelerator/decelerator TBD-GATE-3"]

    Timeline --> NextSc["Next scenario (Rule 4)<br/>Scenario → principal edge TBD-GATE-3"]

    NextSc --> Assemble["Assemble Prediction struct"]
    Assemble --> Return([Return Prediction])
```

**TBD — GATE 3 markers:**
- Direction scoring weights per TF (LTF/MTF/HTF hierarchy weights)
- diffBBW damping thresholds (current values -0.5, 1.0 are WRONG with absolute formula — see integration note 6 in TofyTrade5.mqh)
- Confidence thresholds (magnitude → confidence mapping)
- Timeline bar estimates per phase
- Next-scenario edge transitions
- G→F vs G→C discrimination thresholds

### 4.4 Consumption note — link forward to Part 5

Prediction is the structured input Part 5 receives. How each field is consumed:

| Prediction field | How Part 5 uses it |
|---|---|
| `direction` | Entry side — 1=BUY, 2=SELL, 0=NEUTRAL (no entry) |
| `confidence` | Size multiplier — confidence → size mapping (Rule 5) |
| `target_tf` | Exit target — which TF band boundary triggers X1 |
| `timeline_bars` | Hold-duration sanity — if price hasn't moved in N bars, re-evaluate |
| `next_scenario` | Scenario-transition gating — if L1 transitions to next_scenario, re-evaluate position |
| `reversal` | Exit-not-entry signal — if reversal=True, the firing matrix prioritizes exit conditions over entry |

**Existing code status:** The MQL5 PredictNext stub (lines 590-648 of TofyTrade5.mqh) is functional but suppressed — `ShowPredLabels=false` and Prediction fields are not wired into DecideAction. The Python harness has no PredictNext equivalent. Both are Phase 3 work.

**Staleness report:**
- `TF_DirectionScore` — salvaged verbatim from TofyTrade4. Core scoring logic (stage→stg, mid→mid_b, transition→stg_t, mid_transition→mid_t) is intact. **NOT stale** — the scoring formula is unchanged from TofyTrade4.
- `PredictNext` — uses TF_DirectionScore + diffBBW damping + scenario-gating. **PARTIALLY STALE**: diffBBW damping thresholds (-0.5, 1.0) are WRONG with the absolute formula (flagged in integration note 6, line 1132). Confidence thresholds and next-scenario edges are hardcoded from doc rules but unvalidated — no GATE 3 run.
- TofyTrade4 `PredictNextTrend` — **STALE**: drawn-and-discarded, output not consumed by firing matrix. TofyTrade5 PredictNext fixes this by flowing Prediction into DecideAction.

---

## Part 5 — Layer 3: DecideAction (DESIGN — built Phase 4)

Consumes ScenarioState (Part 3) + Prediction (Part 4) + raw BB_datas → outputs a TradeAction (entry/exit/size/stop). This is where trades actually fire — the layer GATE 4 tests against the March 2026 benchmark. Core principle: **NOTHING FIRES UNLESS ARMED** — opposite of TofyTrade4's fire-unless-blocked model. For entry/exit/block/size/stop rule MEANINGS see `backtest_chart_analysis.md` Part 5; this section designs the layer structure, not rule values.

### 5.0 Link from Layers 1 & 2 — what Part 5 consumes

**Table A — ScenarioState (Part 3) consumption:**

| ScenarioState field (from Part 3 §3.1) | How DecideAction uses it |
|---|---|
| `scenario` | Firing-matrix ROW key — selects which row of the matrix arms triggers |
| `phase` | Firing-matrix ROW key (combined with scenario); gates entry path (E3 in zigzag vs E1/E2 in trend) |
| `b1_block` | Entry gating — M15 sideways block (M15 mid ≥ 3 → no flip-entries) |
| `b2_pink` | X4-PINK exit trigger — M15+M30 both SQZ → forced exit all |
| `priceloc` | E3 boundary entry (at container band), VETO-at-target (no entry at target), X1 (price at target_tf band) |
| `container_tf` | Exit target boundary — which TF band triggers X1 |
| `container_dir` | E3 counter-trend sizing (3B-INTO: counter side 0.25× max) |
| `container_diffbbw` | X2 qualification — container cracking (diffBBW ≤ 0 → qualified exit) |
| `cas_shrinkTF` | Decoder size — compression depth → size multiplier |
| `cas_sqzCount` | Decoder size — B4 block (≥3 → no entries), combined with cas_shrinkTF |
| `pivot_substate` | G-tier routing — 1=PIVOT-PENDING (arm cautiously, exit-only on reversal), 2=G-REVERSAL (reversal_flag → EXIT branch) |
| `info` | Not used — logging field from Part 3 |

**Table B — Prediction (Part 4) consumption:**

| Prediction field (from Part 4 §4.1) | How DecideAction uses it |
|---|---|
| `direction` | Entry side — 1=BUY, 2=SELL, 0=NEUTRAL (no entry); flip-entries require dir==p.direction |
| `confidence` | Size multiplier — confidence → size mapping (ConfSize, Rule 5) |
| `target_tf` | Exit target — which TF band boundary triggers X1 |
| `reversal` | EXIT-not-entry routing — reversal=True → counter-H4 M15 signal closes longs, doesn't open counter-shorts |
| `timeline_bars` | Hold-duration sanity — if price hasn't moved in N bars, re-evaluate |
| `next_scenario` | Re-evaluate on transition — if L1 transitions to next_scenario, re-evaluate position |

**Impact — how the two upstream layers constrain Part 5:**

1. **Nothing fires unless armed.** Both ScenarioState (scenario+phase row) AND Prediction (direction+confidence) must arm the trigger. An M15 flip with ceiling=0 (E1/E2/E4) → WAIT. A prediction with direction=0 → no entry. This is the inversion of TofyTrade4 (which fired unless a gate blocked).
2. **Counter-H4 reversal routing.** A counter-H4 M15 trigger + reversal=True → EXIT route (close existing longs), NOT a new entry (don't open counter-shorts). This branch is explicit in the activity diagram.
3. **OOS-UNVALIDATED propagation.** G→C transition is OOS-UNVALIDATED (Part 3) and G-reversal prediction is OOS-UNVALIDATED (Part 4). Any Part 5 action depending on G-reversal resolution inherits the flag — pivot_substate=2 → exit-only, arm cautiously.
4. **Store-vs-recompute.** b1_block, b2_pink come from ScenarioState (MQL5 stores these on the struct). Python harness recomputes from raw BB data — must match bar-for-bar (per CLAUDE.md and validation_status.md Phase 4 verification item).
5. **Fields consumed but not by Part 5.** Part 3's info field is logging-only; Part 4's timeline_bars and next_scenario are advisory (re-evaluate triggers, not firing conditions).

### 5.1 Interface — Class Diagram

```mermaid
classDiagram
    class ScenarioState {
        <<from Part 3>>
        SCENARIO scenario
        PHASE phase
        bool b1_block
        bool b2_pink
        int container_tf
        int container_dir
        double container_diffbbw
        int priceloc
        int cas_shrinkTF
        int cas_sqzCount
        int pivot_substate
    }

    class Prediction {
        <<from Part 4>>
        int direction
        int confidence
        int target_tf
        bool reversal
        int timeline_bars
        SCENARIO next_scenario
    }

    class BB_MTF_Data_struct {
        <<per-TF raw input>>
        int BBW_stage[LA, LA_1]
        int BB_diffMid_Trend[LA, LA_1]
        int BBUpDn_state[LA]
        double diffBBW[LA]
        double BBUppLV[LA]
        double BBLowLV[LA]
    }

    class TradeAction {
        <<final EA output — drives OrderSend/OrderClose>>
        int act           0=hold / 1=BUY / 2=SELL / 7=exit_all
        string condition_id  E1-E6 / X1-X4 / VETO / WAIT
        double size_mult    0.0-1.0
        double stop_price   ATRSL-based
        string info         logging
    }

    class DecideAction {
        +TradeAction DecideAction(ScenarioState &s, Prediction &p, BB_MTF_Data_struct &bb[], ...)
    }

    ScenarioState --> DecideAction : arms
    Prediction --> DecideAction : directs
    BB_MTF_Data_struct --> DecideAction : boundaries
    DecideAction --> TradeAction : outputs
```

**TradeAction field meanings:**

| Field | Type | Meaning | Consumed by |
|---|---|---|---|
| `act` | int | 0=hold, 1=BUY, 2=SELL, 7=exit_all | OrderSend / OrderClose |
| `condition_id` | string | E1-E6 (entry), X1-X4 (exit), VETO, WAIT | Logging, benchmark verification |
| `size_mult` | double | 0.0–1.0, final = min(ceiling, conf_size, decoder_size) | Lot size |
| `stop_price` | double | ATRSL stop at entry | OrderSend SL |
| `info` | string | Debug string | Logging |

**Output contract:** TradeAction is the final EA output — it drives OrderSend (act=1/2), OrderClose (act=7), or holds (act=0). size_mult is the product of three independent constraints: matrix ceiling (scenario-based), confidence size (Prediction), and decoder size (cascade state). stop_price is set at entry — INVARIANT 1: no trade without a stop.

### 5.2 Activity Diagram — control-flow order

This is the evaluation order. The order IS the design. Cell values are TBD — GATE 4. The "nothing fires unless armed" principle is visible: an unarmed trigger has no path to act=1/2.

```mermaid
flowchart TD
    Start["Start: ScenarioState s + Prediction p + BB_datas[]"] --> Invariants["INVARIANTS (always first, unconditional)"]

    Invariants --> Inv1{"EMERGENCY?<br/>Float loss < -$50"}
    Inv1 -->|yes| Emerg["act=7 EMERGENCY exit"]
    Inv1 -->|no| Inv2{"b2_pink?<br/>X4-PINK"}
    Inv2 -->|yes| Pink["act=7 X4-PINK forced exit"]
    Inv2 -->|no| Inv3{"VETO-AT-TARGET?<br/>BUY-at-upper or SELL-at-lower<br/>and entry was attempted"}
    Inv3 -->|yes| Veto["act=0 VETO-AT-TARGET"]
    Inv3 -->|no| Blocks

    subgraph BLOCKS["BLOCKS (no new entries)"]
        B1["B1: b1_block → no flip-entries"]
        B3["B3: H4-OPPOSE (H4 committed opposing fly)"]
        B4["B4: cas_sqzCount>=3 → no entries"]
    end

    Inv3 --> B1
    B1 --> B3
    B3 --> B4
    B4 --> Exits

    subgraph EXITS["EXIT checks (position open only)"]
        X1{"X1: price at<br/>target_tf band?"}
        X2{"X2: M15 fade +<br/>qualified?"}
        X2a{"Zigzag phase?"}
        X2b{"Container cracking?<br/>or invalidated or stall?"}
    end

    Exits --> X1
    X1 -->|yes| Exit1["act=7 X1 target exit"]
    X1 -->|no| X2
    X2 -->|no fade| Hold1["act=0 hold"]
    X2 -->|fade yes| X2a
    X2a -->|"no (PH_1)"| Exit2["act=7 X2 trend-fade exit"]
    X2a -->|"yes (zigzag)"| X2b
    X2b -->|"yes (qualified)"| Exit2
    X2b -->|"no (unqualified)"| Hold1

    Hold1 --> Ceiling["MATRIX CEILING<br/>ceiling = MatrixCeiling(scenario, phase)"]

    Ceiling --> Ceil0{"ceiling <= 0?"}
    Ceil0 -->|yes| Wait1["act=0 WAIT — ceiling blocks"]
    Ceil0 -->|no| Arming

    subgraph ARMING["ENTRY ARMING (scenario,phase row + Prediction)"]
        EntryPath["Which entry path?<br/>Zigzag → E3 boundary<br/>PH_1/2/5 → flip-path E1/E2/E5"]

        E3{"E3: priceloc at band?<br/>+ 6 confinement checks"}
        E3pass["E3 entry fired<br/>size = min(ceiling, conf_size, decoder_size)"]
        E3fail["E3 check failed → WAIT"]

        Flip{"Flip: DetectFlip +<br/>dir == p.direction"}
        FlipYes["Flip entry E1/E2/E5<br/>size = min(ceiling, conf_size, decoder_size)"]
        FlipNo["No flip → WAIT"]

        ReversalCheck{"reversal=True?<br/>+ counter-H4 signal"}
        ReversalExit["EXIT route — close longs<br/>don't open counter-shorts"]
    end

    Arming --> EntryPath
    EntryPath --> E3
    E3 -->|pass| E3pass
    E3 -->|fail| E3fail
    E3pass --> Sizing
    E3fail --> Flip
    Flip -->|yes| ReversalCheck
    ReversalCheck -->|yes| ReversalExit
    ReversalCheck -->|no| FlipYes
    FlipYes --> Sizing
    Flip -->|no| FlipNo
    FlipNo --> Wait2["act=0 WAIT — no trigger armed"]

    Sizing["SIZE = min(ceiling, ConfSize(confidence), DecoderSize(cascade))<br/>STOP = ATRSL at entry (INVARIANT 1)"]
    Sizing --> Return([Return TradeAction])
    Emerg --> Return
    Pink --> Return
    Veto --> Return
    Exit1 --> Return
    Exit2 --> Return
    Wait1 --> Return
    ReversalExit --> Return
    Wait2 --> Return
```

**Contract established:** The evaluation order is INVARIANTS → BLOCKS → EXITS → ARMING → SIZE. Invariants fire unconditionally (EMERGENCY, X4-PINK, VETO). Blocks prevent new entries but don't close existing positions. Exits check only when a position is open. Arming requires BOTH scenario/phase row AND Prediction direction — unarmored triggers have no path to fire. Stop is set at entry (INVARIANT 1).

### 5.3 Firing Matrix — Structure (the shape, not the cells)

The matrix defines which triggers are armed per (scenario, phase) row. Cell VALUES are TBD — GATE 4. This section designs the table structure.

```mermaid
flowchart LR
    subgraph MATRIX["FIRING MATRIX — structure only"]
        Rows["ROWS: scenario × phase<br/>(e.g. A1/PH_1, B2/PH_3A, G3/PH_4)"]
        C1["COL 1: armed triggers<br/>E1/E2/E3/E4/E5/E6"]
        C2["COL 2: size ceiling<br/>(0.0–1.0, scenario-based)"]
        C3["COL 3: target_tf<br/>(which TF band for X1)"]
        C4["COL 4: allowed entry conditions<br/>(which E-conditions fire)"]
        C5["COL 5: entry mode<br/>(entry / exit-only / blocked)"]
    end

    Rows --> C1
    Rows --> C2
    Rows --> C3
    Rows --> C4
    Rows --> C5
```

**Structure rules (design-time, not GATE-4-validated):**
- Each row is a unique (scenario, phase) combination
- Ceiling = 0.0 → exit-only or blocked (no entries possible)
- Ceiling > 0.0 → entries possible if triggers armed
- PH_4 rows → exit-only (X4-PINK or WAIT, no entries)
- PH_5 rows → E5/E6 only (expansion entries)
- G-tier rows (G1-G4) → arm cautiously; pivot_substate=2 → exit-only
- C-tier rows → OOS-UNVALIDATED — cells TBD — no OOS episodes to validate
- Cell values (which specific triggers fire per row) = TBD — GATE 4

**Existing code status:** The MQL5 DecideAction (lines 731-828 of TofyTrade5.mqh) is implemented with the control flow matching the activity diagram: invariants (b2_pink, VETO), exits (X1, X2 qualified), ceiling check, E3 in zigzag, flip-path E1/E2/E5. The replay_harness.py `decide_action()` mirrors this (lines 706-847). Matrix ceiling values are hardcoded from backtest_chart_analysis.md Part 5 — not yet GATE-4-validated.

**Staleness report:**
- TofyTrade5 DecideAction — **CURRENT**: implements the three-layer design with firing matrix. Condition IDs (E1-E6, X1-X4, VETO, WAIT) match the v31 signal taxonomy. No old G0b/G4x gate names in control flow — those are in the gate decoder table only (for log parsing).
- TofyTrade4 gate-based model — **STALE**: fire-unless-blocked model replaced by nothing-fires-unless-armed. Old gate names (G0b-TOUCH → E3, G8-BNDTGT → X1, G5-FADE → X2, G0b-PINK → X4) documented in gate decoder table.
- Matrix ceiling values — **UNVALIDATED**: hardcoded from doc rules, no GATE 4 run against benchmark.

### 5.4 GATE 4 — what validates this layer

GATE 4 is the firing benchmark. Part 5 must produce results matching the March 2026 benchmark (`references/fixtures/march2026_benchmark.md`):

1. **≥ 6 leg-capture entries** — matching the 8 verified arrow legs (03.03 SELL crash, 03.04 BUY, 03.04 SELL, 03.05 BUY, 03.05 SELL, 03.06 BUY, 03.10 BUY, 03.17 SELL run)
2. **03.03 07:45 → VETO-AT-TARGET** — not BUY (price at D1 upper band — the -191.29 nine-day hold must be impossible)
3. **No exit within 3 bars on mid=3 wobble** — 03.17-03.19 SELL run held through M15 wobble (X2 qualified only)
4. **Zero positions held > 3 days** — stop at entry (INVARIANT 1) + emergency $50 exit
5. **Counter-H4 M15 sell = EXIT not new short** — reversal routing (reversal=True → exit branch)

The replay harness `simulate_trades()` + `score_benchmark()` (replay_harness.py lines 851-1117) runs this validation.

---
