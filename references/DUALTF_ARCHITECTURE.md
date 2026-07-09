# DualTF Architecture — EA Implementation Design (MEASURED SPEC)

> **STATUS NOTE:** DualTF band-state ENTRY is CLOSED (see V36.14 section).
> Part 3 IDENTIFICATION remains validated and reusable for any future premise.
>
> **A three-layer EA design implementing the DualTF Stack model**
> (DUALTF_IMAGE_ANALYSIS.md): Identify → Detect → Act.
> Part 3 **BUILT & BACKTESTED** (TofyTrade6.mqh V36.10, backtests V36.01–V36.10,
> 7,608-row verified logs); Part 4 **redesigned as TransitionDetector**
> (measured-viable, not yet implemented as detector); Part 5 **DESIGN**
> (measured rules, unimplemented).

---

## Architecture overview — four-layer model

> **STATUS NOTE (2026-07-04):** Layer 3 exit lifecycle reflects V36.13 (exit-retry fix) which is **IN-FLIGHT** — backtest not yet verified. Re-verify this section and all IN-FLIGHT-tagged diagrams after the V36.13 backtest.

### Layer ↔ Part Mapping

| Layer | Part | Description | Status |
|-------|------|-------------|--------|
| Layer 1 | Part 3 | Identification — per-TF states + BBLoc | **BUILT V36.10** |
| Layer 2 | Part 4 | TransitionDetector — M15 flip detection | **BUILT V36.11** |
| Layer 3 | Part 5 | Trade ruleset — gate, entry, TP, SL, exit | **BUILT V36.11 + V36.13 IN-FLIGHT** |
| Layer 4 | Open Questions + Evidence Index | Measurement gate — nothing enters Layers 2-3 without committed analysis passing pre-fixed criteria | **ONGOING** |

### Four-Layer Overview Diagram

```mermaid
flowchart TD
    classDef built fill:#E1F5EE,stroke:#0F6E56
    classDef inflight fill:#FAEEDA,stroke:#854F0B
    classDef gated fill:#F1EFE8,stroke:#5F5E5A

    subgraph L1sub ["Layer 1 — Identification"]
        L1id["per-TF states + BBLoc<br/>V36.10"]
    end

    subgraph L2sub ["Layer 2 — TransitionDetector"]
        L2det["fires on M15 flip to F or R"]
    end

    subgraph L3sub ["Layer 3 — Trade Ruleset"]
        L3gate["m30bbloc NEAR or MID"]
        L3entry["0.01 lots<br/>SL M15 band, TP M30 band"]
        L3mgmt["manage exit"]
        L3act["act 1 / 2 / 7"]
        L3skip["at-band, FAR, concurrent"]
        L3retry["V36.13: retry close<br/>until confirmed flat"]
    end

    subgraph L4sub ["Layer 4 — Measurement Gate"]
        L4knobs["staged knobs<br/>min-rr gate V36.14, revert loosen V36.15"]
        L4queue["measurement queue<br/>H4 volatility lead, revert vs HTF trend,<br/>at-band trend-ride, M30/H1 trend at trigger"]
    end

    M15["M15"] --> L1id
    M30["M30"] --> L1id
    H1n["H1"] --> L1id
    H4n["H4"] --> L1id
    D1n["D1"] --> L1id

    L1id --> L2det
    L2det --> L3gate
    L3gate -->|"pass"| L3entry
    L3gate -->|"skip"| L3skip
    L3entry --> L3mgmt
    L3mgmt --> L3act
    L3mgmt --> L3retry
    L4queue -.->|"criteria PASS promotes"| L3sub
    L4knobs -.->|"criteria PASS promotes"| L3sub

    class L1id,L2det,L3gate,L3entry,L3mgmt,L3act,L3skip built
    class L3retry inflight
    class L4knobs,L4queue gated
```

*Legend: teal = built, amber = in-flight, gray = gated (measurement required before promotion).*

### TF Roles (measured inventory)

| TF | Role | Notes |
|----|------|-------|
| M15 | Trigger + SL price + revert exit | Leading-edge signal for detection and timing |
| M30 | Gate location + TP price + timeout disarm | Never used for trend — gate and target only |
| H1 | Layer 1 logging only | Zero decision role |
| H4 | Layer 1 logging only | Zero decision role |
| D1 | Layer 1 logging only | Zero decision role |

**Dead roles (killed by measurement):**

| Dead Role | Kill Numbers | Source |
|-----------|-------------|--------|
| HTF entry filter (agreeing vs disagreeing) | 33.0% vs 35.9% — no effect | CASCADE_LEAD_ANALYSIS.md |
| H4-band TP target | 24.4% reach from MID+FAR | TARGET_REACH_ANALYSIS.md |
| Tier-2 H1 cascade TP | 0.99x lift — below 1.0 | TIER2_REACH_ANALYSIS.md |
| MTF prediction | 1.2% coarse, 43.9% fine (invalidated), multi-input worse | MULTIINPUT_PREDICTION_ANALYSIS.md |

---

## Three-Layer Overview

```mermaid
flowchart LR
    L1["**Layer 1**<br/>Identify DualTF Scenario<br/>WHERE am I?<br/>(F/S/C/R per axis)"] --> L2["**Layer 2**<br/>TransitionDetector<br/>M15 flip F/R?<br/>(detection)"]
    L2 --> L3["**Layer 3**<br/>Trade Ruleset<br/>WHAT to do?<br/>(entry/exit/gate)"]

    L1 -.->|"DualTF Scenario + BBLoc"| L2
    L2 -.->|"trigger: direction, validity"| L3
```

- **Layer 1 — Identify DualTF Scenario**: Given current BB state across all TFs, derive 4-state (F/S/C/R) per TF, then pair into HTF (D1×H4) and MTF (H1×M30) scenarios with per-TF BBLoc. Replaces the 7-scenario IdentifyScenario with the DualTF 4×4 derivation.
- **Layer 2 — TransitionDetector**: Detects M15 state flips to F (up) or R (down). No prediction — detection of real events. Fires trigger with 12-row validity window.
- **Layer 3 — Trade Ruleset**: Given trigger + m30bbloc zone, applies gate (NEAR/MID only) → entry → M30-band TP → stop → invalidation.

---

## TF Roles (cross-cut all layers)

These responsibilities are invariant across all three layers — they define what each TF contributes to the DualTF system.

| TF | Role | Layers that consume |
|----|------|---------------------|
| D1 | HTF axis (with H4) — sets macro direction, fork-decider for compression breakout | L1 (HTF scenario), L3 (directional a priori) |
| H4 | HTF axis (with D1) — primary HTF classifier, phase context | L1 (HTF scenario), L3 (confinement check) |
| H1 | MTF axis (with M30) — the leg ridden, primary trend driver | L1 (MTF scenario), L3 (confinement) |
| M30 | MTF axis (with H1) — MTF confinement check | L1 (MTF scenario), L3 (confinement) |
| M15 | Leading-edge — feeds Part 4 TransitionDetector AND Part 5 entry/exit timing | L2 (leading-edge signal), L3 (entry/exit trigger) |
| M5 | Optional within-M15-bar refinement — NOT a standalone trigger | L3 (tick refinement only, after M15 confirms) |

**Key difference from 7-scenario system:** M15 is no longer just an entry trigger — it is the PRIMARY detection signal (Part 4) and the PRIMARY entry/exit timing trigger. M5 is NOT a standalone trigger — optional within-M15-bar refinement only after M15 confirms. The HTF axis (D1×H4) provides context but has no filter role (HTF filter killed by measurement).

---

## Evolution + Falsification UML

```mermaid
flowchart TD
    subgraph PART3["PART 3 — IDENTIFICATION (VALIDATED, REUSABLE)"]
        P3["IdentifyDualTF<br/>(per-TF states + BBLoc)"]
    end

    subgraph PREMISE["ENTRY PREMISE — band-state flip predicts direction"]
        PR["Band-state flip = directional signal<br/>M15 flip alone → F/R"]
    end

    subgraph V36_13["V36.13 — M15-alone entry gate"]
        V3_13["ENTRY: M15 flips to F or R<br/>No HTF filter, no M30 confirm"]
    end

    subgraph V36_14["V36.14 — M30-confirmed entry gate"]
        V3_14["ENTRY: M15 flip + M30 confirms within 12 bars<br/>Same exits/SL/TP/sizing"]
    end

    subgraph V36_14_H4["V36.14 — H4×H1 filter (S-F)"]
        V3_14_H4["ENTRY: M15 flip + M30 confirms + H4/H1 agree<br/>OOS-fail PF 3.62→0.13"]
    end

    PART3 --> PREMISE
    PREMISE --> V36_13
    PREMISE --> V36_14
    PREMISE --> V36_14_H4

    classDef validated fill:#e8f5e9,stroke:#0F6E56
    classDef dead fill:#f1f1f1,stroke:#666,color:#666
    classDef entry fill:#fff3e0,stroke:#ff9800

    class P3 validated
    class V3_13,PREMISE,V36_13 dead
    class V3_14,V36_14 entry
    class V3_14_H4 dead
```

**The diagram shows:** Part 3 identification (VALIDATED, reusable) feeding the entry premise, then the premise branching into the three tested variants — M15-alone (V36.13), M30-confirmed (V36.14), and H4×H1 filter (V36.14 S-F). All three terminate in their OOS verdict nodes (all REJECTED/DEAD). Part 3 alone survives; the shared dead core is the band-state flip premise.

---

## Part 3 — Layer 1: Identify DualTF Scenario (BUILT & BACKTESTED)

### 3.1 Interface — Class/Struct Diagram

This diagram shows the DualTF data structures: what Layer 1 reads (per-TF BB data) and what it returns (DualTFScenarioState). This replaces the ScenarioState struct from the 7-scenario system.

```mermaid
classDiagram
    class BB_TF_Data {
        <<per-TF input — same as 7-scenario>>
        int BBW_stage
        int BB_diffMid_Trend
        int BBUpDn_state
        double diffBBW
        double BBUppLV
        double BBLowLV
        double BB_Mid
    }

    class BB_datas {
        <<array input>>
        BB_TF_Data tf_m5
        BB_TF_Data tf_m15
        BB_TF_Data tf_m30
        BB_TF_Data tf_h1
        BB_TF_Data tf_h4
        BB_TF_Data tf_d1
    }

    class DualTFScenarioState {
        string htf_scenario
        string mtf_scenario
        int htf_bbloc
        int mtf_bbloc
        int d1_bbloc
        int h4_bbloc
        int h1_bbloc
        int m30_bbloc
        int m15_bbloc
        string htf_combo
        string mtf_combo
        string ltf_combo
        string htf_d1_state
        string htf_h4_state
        string mtf_h1_state
        string mtf_m30_state
        string m15_state
        string info
    }

    class IdentifyDualTF {
        +DualTFScenarioState IdentifyDualTF(BB_datas[], close_prices[])
    }

    BB_datas --> IdentifyDualTF : feeds
    IdentifyDualTF --> DualTFScenarioState : returns
```

```mermaid
classDiagram
    class PositionState {
        bool open
        int direction
        double entry_price
        datetime entry_time
        double tp_price
        double sl_price
        bool m30_followed
        int bars_since_entry
        string trigger_state
        int trigger_dir
    }
```

> **Note:** PositionState fields match TofyTrade6.mqh V36.12 struct. An `exit_pending` field (bool) is part of V36.13 IN-FLIGHT — not yet present in the committed struct.

**Field meanings (DualTFScenarioState):**

| Field | Type | Meaning | Consumed by |
|-------|------|---------|-------------|
| `htf_scenario` | string | HTF 2-char code (D1-state)(H4-state), e.g. "FS" = D1 fly-up, H4 shrinking | L2, L3 |
| `mtf_scenario` | string | MTF 2-char code (H1-state)(M30-state), e.g. "FC" = H1 fly-up, M30 compress | L2, L3 |
| `htf_bbloc` | int | HTF band location 0-10 (legacy, kept for compat) | L3 |
| `mtf_bbloc` | int | MTF band location {0,1,3,5,7,9,10} (legacy, kept for compat) | L3 |
| `d1_bbloc` | int | D1 per-TF band location 0-10 (V36.05+) | L2, L3 |
| `h4_bbloc` | int | H4 per-TF band location 0-10 (V36.05+) | L2, L3 |
| `h1_bbloc` | int | H1 per-TF band location sparse (V36.05+) | L2, L3 |
| `m30_bbloc` | int | M30 per-TF band location sparse (V36.05+) | L2, L3 |
| `m15_bbloc` | int | M15 per-TF band location sparse (V36.05+) | L2, L3 |
| `htf_combo` | string | HTF paired combo string, e.g. "F3F5" (V36.05+) | L2, L3 |
| `mtf_combo` | string | MTF paired combo string, e.g. "F3F5" (V36.05+) | L2, L3 |
| `ltf_combo` | string | LTF combo string, e.g. "F3" (V36.05+) | L2, L3 |
| `htf_d1_state` | string | D1 raw 4-state: F/S/C/R | L2 (HTF fork-decider) |
| `htf_h4_state` | string | H4 raw 4-state: F/S/C/R | L2 (HTF fork-decider) |
| `mtf_h1_state` | string | H1 raw 4-state: F/S/C/R | L2, L3 |
| `mtf_m30_state` | string | M30 raw 4-state: F/S/C/R | L2, L3 |
| `m15_state` | string | M15 leading-edge state: F/S/C/R | L2 (leading-edge input), L3 (trigger) |
| `info` | string | Human-readable reason string | logging |

> **Note:** BBW_stage mapping to F/S/C/R: 511,512 → F; 521,522 → R; 513,523 → S; 400-499 → C. Same as DUALTF_IMAGE_ANALYSIS.md Part 1.

### 3.2 Control Flow — Activity Diagram

This flowchart shows the derivation order: per-TF BBW_stage → F/S/C/R state, then D1×H4 → HTF pair, H1×M30 → MTF pair, then BBLoc computation.

```mermaid
flowchart TD
    Start["Start: BB_datas[0..5] + close_prices + band_data"] --> Init["Initialize DualTFScenarioState defaults"]

    Init --> D1State["D1: BBW_stage → F/S/C/R"]
    D1State --> H4State["H4: BBW_stage → F/S/C/R"]
    H4State --> H1State["H1: BBW_stage → F/S/C/R"]
    H1State --> M30State["M30: BBW_stage → F/S/C/R"]
    M30State --> M15State["M15: BBW_stage → F/S/C/R"]

    M15State --> HTFPair["HTF scenario = (D1-state)(H4-state)<br/>Pair into 2-char code, e.g. 'FS'"]
    HTFPair --> MTFPair["MTF scenario = (H1-state)(M30-state)<br/>Pair into 2-char code, e.g. 'FC'"]

    MTFPair --> HTFBBLoc["Compute HTF BBLoc (0-10)<br/>From real price vs D1/H4 bands"]
    HTFBBLoc --> MTFBBLoc["Compute MTF BBLoc (0,1,3,5,7,9,10)<br/>From real price vs H1/M30 bands"]

    MTFBBLoc --> Info["Set info string"]
    Info --> Return([return DualTFScenarioState])
```

**Derivation order:** Per-TF states first (independent, parallel), then axis pairing (HTF from D1×H4, MTF from H1×M30), then BBLoc (real-time price-vs-band computation — EA advantage over analysis-side coarse BBUpDn mapping).

### 3.3 Scenario State Machine — State Diagram

The 4-state cycle: F → S → C → {F or R}, with persistence at each state.

```mermaid
stateDiagram-v2
    [*] --> F

    F --> S: "Expansion fades → bands contract"
    S --> C: "Deepen → SQZ (stage 4xx)"
    S --> F: "Re-expand before compression"
    C --> F: "Break out up (HTF aligned up)"
    C --> R: "Break out down (HTF aligned down)"

    F --> F: "Persist (duration ≥ 3)"
    S --> S: "Persist (duration ≥ 3)"
    C --> C: "Persist (duration ≥ 3)"

    R --> S: "Down-fly fades → bands contract"
    R --> R: "Persist (duration ≥ 3)"

    note right of C
        Fork-decider: HTF axis determines
        breakout direction.
        D1 up → F; D1 down → R.
    end note

    note right of F
        Persist triggered by
        duration ≥ 3 bars in same state.
        Fly states typically persist
        5-15+ bars.
    end note
```

**Contract established:** The 4-state machine flows F → S → C → {F or R}, with R symmetric to F (R → S → C → {R or F}). Each state can persist (duration ≥ 3 bars). The HTF axis determines the C → {F or R} fork: D1 up → F (continuation), D1 down → R (reversal). This replaces the 7-scenario state machine in ARCHITECTURE.md §3.3.

### 3.4 BBLoc Computation

**EA advantage over analysis side:** The EA computes real band position from price vs band data. The analysis side uses coarse BBUpDn mapping (only {1,2,3,5} reachable). The EA has access to `BBUppLV`, `BBLowLV`, and `BB_Mid` per TF — it can compute exact position.

**HTF BBLoc (0-10, continuous scale):**

```
htf_bbloc = (price - band_low) / (band_up - band_low) * 10
```

Anchors: 0 = below lower band, 5 = at mid, 10 = above upper band.
Shared anchors with MTF: 1 = lower band, 5 = mid, 9 = upper band.

**MTF BBLoc (sparse scale: 0, 1, 3, 5, 7, 9, 10):**

Same formula, but the scale is sparse — mirroring the BBUpDn reachability gap.
Anchors: 0 = below lower, 1 = lower band, 3 = lower-mid, 5 = mid, 7 = upper-mid, 9 = upper band, 10 = above upper.
Gaps at 2, 4, 6 reflect the same coarse-data limit as the analysis side — the EA inherits the gap from the BBUpDn mapping that defines the state boundaries.

**Key advantage:** The EA's BBLoc is real (from price/band computation), not inferred from BBUpDn. This means levels 0, 2, 4, 6, 8 are reachable — the trajectory is continuous, not gapped. The MTF sparse scale is a design choice (matching the analysis side for consistency), not a data limitation.

**Band-position ladder:**

```
HTF BBLoc (0-10) — price position in the Bollinger bands:

   10  ── over BB Upper
──────── 9   BB Upper band
    8   ── between Upper and Upper-Mid
──────── 7   BB Upper-Mid
    6   ── between Upper-Mid and Mid
──────── 5   BB Mid band
    4   ── between Mid and Lower-Mid
──────── 3   BB Lower-Mid
    2   ── between Lower-Mid and Lower
──────── 1   BB Lower band
    0   ── below BB Lower

MTF BBLoc (sparse 0,1,3,5,7,9,10) — same anchors, coarser:
   1=Lower, 3=Lower-Mid, 5=Mid, 7=Upper-Mid, 9=Upper, 0=below, 10=above
```

**Computation flowchart:**

```mermaid
flowchart TD
    A["Read price + band values<br/>BBUppLV BBLowLV BB_Mid"] --> B["Compute ratio<br/>r = (price - BBLowLV) / (BBUppLV - BBLowLV)"]
    B --> C["Scale to 0-10<br/>bbloc_raw = r * 10"]
    C --> D{"Which axis?"}
    D -->|"HTF: D1 or H4"| E["Round to 0-10 full resolution"]
    D -->|"MTF: H1 or M30"| F["Snap to nearest of 0,1,3,5,7,9,10"]
    E --> G["htf_bbloc"]
    F --> H["mtf_bbloc"]
```

### 3.4a Per-Bar Runtime Sequence — TofyTrade6.mqh (V36.10)

This sequenceDiagram traces the actual function call flow in TofyTrade6.mqh per bar.
Each participant is a real function; each message is a real call.

```mermaid
sequenceDiagram
    participant EA as "EA OnTick"
    participant TS as "Trade_Strategy()"
    participant ID as "IdentifyDualTF()"
    participant B2D as "BBStageToDualState()"
    participant HBF as "ComputeHTFBBLoc()"
    participant MBF as "ComputeMTFBBLoc()"
    participant L as "LogDualTFBar()"
    participant DL as "DrawGateLabel()"

    Note over EA,TS: "Part 3 is the WORKING, validated layer — V36.10 runtime"

    EA->>TS: "BB_datas[] ATRSL1BUF BBTFImpact Trade_act close_prices[]"
    TS->>TS: "Once-per-bar guard (iTime M5)"
    TS-->>TS: "return if same bar (Trade_act=0)"

    TS->>ID: "BB_datas[] close_prices[]"
    Note over ID,B2D: "Per-TF state derivation (5 TFs)"
    ID->>B2D: "bb[5].BBW_stage → D1 state"
    B2D-->>ID: "DUAL_STATE (F/S/C/R/X)"
    ID->>B2D: "bb[4].BBW_stage → H4 state"
    B2D-->>ID: "DUAL_STATE"
    ID->>B2D: "bb[3].BBW_stage → H1 state"
    B2D-->>ID: "DUAL_STATE"
    ID->>B2D: "bb[2].BBW_stage → M30 state"
    B2D-->>ID: "DUAL_STATE"
    ID->>B2D: "bb[1].BBW_stage → M15 state"
    B2D-->>ID: "DUAL_STATE"

    ID->>ID: "Pair: HTF=D1+H4 MTF=H1+M30"

    ID->>HBF: "price bb[5].BBLowLV bb[5].BBUppLV"
    HBF-->>ID: "htf_bbloc (0-10 rounded)"

    ID->>MBF: "price bb[3].BBLowLV bb[3].BBUppLV"
    MBF-->>ID: "mtf_bbloc (0,1,3,5,7,9,10 snapped)"

    Note over ID: "No-data gate: state X → bbloc=-1"

    ID->>ID: "Build info string"
    ID-->>TS: "DualTFScenarioState s"

    TS->>L: "BB_datas[] s"
    L-->>TS: "DUALTF log line written"

    TS->>TS: "Scenario change? (curKey vs prev)"
    alt scenario changed
        TS->>DL: "tag price BB_datas clrWhite 1"
        DL-->>TS: "Chart label drawn"
    else no change
        TS->>TS: "skip DrawGateLabel"
    end

    TS->>TS: "Trade_info = s.info"
    TS-->>EA: "Trade_act=0 (HOLD — no trades)"
```

**What this shows:** Per tick, the EA calls `Trade_Strategy()` which gates on once-per-bar. Inside: `IdentifyDualTF()` derives per-TF states via `BBStageToDualState()` (5 calls: D1/H4/H1/M30/M15), pairs HTF/MTF scenarios, computes real BBLoc via `ComputeHTFBBLoc()`/`ComputeMTFBBLoc()`, applies the no-data gate (state X → bbloc=-1), and returns `DualTFScenarioState`. The caller logs via `LogDualTFBar()`, draws a chart label only on scenario change via `DrawGateLabel()`, then returns `Trade_act=0` — no trades. This is the live V36.10 flow.

### 3.5 Build Status

| Component | Status | Detail |
|-----------|--------|--------|
| 4-state derivation (BBW_stage → F/S/C/R) | **BUILT** | BBStageToDualState(), V36.10 |
| HTF pairing (D1×H4) | **BUILT** | htf_combo (e.g. "F3F5"), V36.10 |
| MTF pairing (H1×M30) | **BUILT** | mtf_combo, V36.10 |
| BBLoc computation | **BUILT** | ComputeHTFBBLoc/ComputeMTFBBLoc, per-TF (d1_bbloc/h4_bbloc/h1_bbloc/m30_bbloc/m15_bbloc), V36.10 |
| M15 leading-edge state | **BUILT** | Same derivation as other TFs, V36.10 |

> **BUILT & BACKTESTED.** TofyTrade6.mqh V36.10, backtests V36.01–V36.10, 7,608 DUALTF log rows verified.

---

## Part 4 — Layer 2: TransitionDetector (MEASURED-VIABLE)

> **STATUS: MEASURED-VIABLE (tested).** Detection-based approach grounded in data.
> TransitionDetector fires on actual M15 state flips to F (up) or R (down) —
> not a forecast, a detection. Grounding citation: CASCADE_LEAD_ANALYSIS.md.

### SUPERSEDED — Prediction (retained as evidence trail)

> **PREDICTION IS DEAD.** Coarse data: 1.2% transition accuracy. Fine BBLoc:
> 43.9% OOS (BBLoc-only, best predictor — and that number was later invalidated:
> it was measured on H1-predicts/M30-verifies inconsistent logic, fixed in V36.06,
> consistent version never re-measured). Multi-input WORSE + overfit (40.8%→35.3%).
> See MULTIINPUT_PREDICTION_ANALYSIS.md for the full failure anatomy.
> The design below (4.1–4.2a, 4.2c–4.2d) is retained as historical record.

### 4.1 TransitionDetector — Definition

**Detection, not prediction.** The TransitionDetector fires on actual M15 state
flips — real events, not forecasts.

- **FIRES** on M15 state flip to F (up trigger) or R (down trigger) ONLY.
  S/C flips excluded — lift 1.26x/1.07x, no edge.
- **NO HTF filter** — killed by measurement (agreeing 33.0% vs disagreeing 35.9%).
- **Measured stats** (K=12, CASCADE_LEAD_ANALYSIS.md):
  - Recall: 57.2% (294/514 M30 transitions preceded by same-target M15 flip)
  - Precision: F 38.0% (93/245), R 32.9% (83/252)
  - Lift: F 2.03x, R 2.01x (over unconditional base rate)
  - Median lead: 5 rows (25 minutes)
  - Validity window: 12 rows (60 minutes)
- **Output:** trigger {direction, fire-time, 12-row validity window} → Part 5.
- **Existing prediction fields** (pred_direction, predmtf, slope, predhit)
  remain **LOG-DIAGNOSTIC ONLY** — never trade inputs.

### 4.2 TransitionDetector Flowchart

```mermaid
flowchart TD
    A["M15 state flip detected"]
    A --> B{"Flip to F or R?"}
    B -->|F| C["UP TRIGGER<br/>direction: UP, fire-time: now,<br/>validity: 12 rows"]
    B -->|R| D["DOWN TRIGGER<br/>direction: DOWN, fire-time: now,<br/>validity: 12 rows"]
    B -->|S or C| E["NO TRIGGER<br/>S/C excluded (no lift)"]

    C --> F["Part 5: Tradeability Gate<br/>+ Target Rule"]
    D --> F

    classDef trigger fill:#e8f5e9,stroke:#4CAF50
    classDef skip fill:#ffebee,stroke:#f44336
    classDef pass fill:#e8f4fd,stroke:#2196F3

    class C,D trigger
    class E skip
    class F pass
```

**What this shows:** The TransitionDetector detects real M15 flips — no forecast, no
rolling buffer, no prediction. It fires on F/R flips only (S/C excluded by lift
measurement). The trigger carries direction, fire-time, and a 12-row validity window.
Existing prediction fields (slope, pred_direction, predhit) are log-diagnostics only.

### 4.3 Build Status

| Component | Status | Detail |
|-----------|--------|--------|
| TransitionDetector (M15 F/R flip detection) | **MEASURED-VIABLE** | 57.2% recall, 2.03x/2.01x lift, CASCADE_LEAD_ANALYSIS.md |
| HTF filter | **KILLED** | Agreeing 33.0% vs disagreeing 35.9% — no effect |
| S/C flip detection | **KILLED** | Lift 1.26x/1.07x — no edge |
| Prediction fields (slope, pred_direction, predhit) | **LOG-DIAGNOSTIC** | Never trade inputs |

> **Measured-viable, not yet implemented as detector.** The cascade lead measurement
> grounds the TransitionDetector design (CASCADE_LEAD_ANALYSIS.md, commit 623f38d).
> Existing prediction stubs in TofyTrade6.mqh return persist with confidence=0.

---

## Part 5 — Layer 3: Measured v1 Trade Ruleset (DESIGN)

### 5.1 Trade Rules — Measured

**ENTRY:** On TransitionDetector trigger, enter in the flip direction (UP = BUY, DOWN = SELL).

**TRADEABILITY GATE:** m30bbloc at trigger row must be NEAR or MID —
UP: {5, 7}; DOWN: {3, 5} on the sparse scale.
**SKIP** AT/BEYOND (M30-band TP incoherent there; tier-2 H1 cascade DEAD — lift 0.99x;
TIER2_REACH_ANALYSIS.md) and **SKIP** FAR (6/45 = 13% follow).

**TAKE-PROFIT:** M30 band — 98.1% reach from NEAR+MID on the FOLLOWED subset,
61–72% reach on ALL triggers at N=12 (TARGET_REACH_ANALYSIS.md).
H4 target DEAD: C1 FAIL 24.4% reach from MID+FAR.

**STOP (v1 DEFAULT — LEAST-GROUNDED parameter, unmeasured):**
Opposite-side M15 band at entry.
Alternatives: opposite M30 band, fixed price offset.
**REQUIREMENT:** V36.11 must log per-trade stop and TP distances in PRICE
so the Tester adjudicates.

**INVALIDATION/EXIT:** M15 state reverts to non-trigger state,
OR 12 rows elapse without M30 reaching the trigger state → close.

**SIZING:** Fixed 0.01 lots (v1).

**FREQUENCY:** ~230 qualifying triggers / 4 months ≈ 2.7 per trading day.

**EXPECTANCY WARNING:** Follow-rate is not win-rate. The kept NEAR/MID population
follows at only 23% (54/230) vs 52% for the skipped at-band majority.
Reach is not profit — no stops or path analysis in any reach analysis.
Profitability is decided ONLY by the V36.11 Tester report.
RR must clear ~2:1 for the geometry to work.

### 5.2 Control Flow — Activity Diagram

```mermaid
flowchart TD
    A["TransitionDetector trigger<br/>UP or DOWN"]
    A --> B{"TRADEABILITY GATE<br/>m30bbloc zone?"}

    B -->|"NEAR or MID"| C["ENTER<br/>BUY if UP, SELL if DOWN<br/>Size: 0.01 lots"]
    B -->|"AT/BEYOND"| D["SKIP<br/>M30 TP incoherent;<br/>tier-2 cascade dead"]
    B -->|"FAR"| E["SKIP<br/>Only 13% follow"]

    C --> F["TAKE-PROFIT<br/>M30 band"]
    F --> G["STOP<br/>Opposite M15 band<br/>(least-grounded param)"]

    G --> H{"EXIT PRIORITY 1:<br/>TP hit?"}
    H -->|"yes"| I["CLOSE"]
    H -->|"no"| M{"EXIT PRIORITY 2:<br/>M15 reverts?"}
    M -->|"yes"| I
    M -->|"no"| T{"EXIT PRIORITY 3:<br/>timeout?"}
    T -->|"m30_followed = false<br/>and 12 bars elapsed"| I
    T -->|"m30_followed = true<br/>timeout disarmed"| SL{"EXIT PRIORITY 4:<br/>SL hit?"}
    T -->|"neither"| K["HOLD"]
    SL -->|"yes"| I
    SL -->|"no"| K

    K --> RETRY{"close confirmed flat?<br/>(V36.13 IN-FLIGHT)"}
    RETRY -->|"no"| K
    RETRY -->|"yes"| FLAT["FLAT"]

    classDef enter fill:#e8f5e9,stroke:#4CAF50
    classDef skip fill:#ffebee,stroke:#f44336
    classDef close fill:#fff3e0,stroke:#FF9800
    classDef hold fill:#e8f4fd,stroke:#2196F3
    classDef retry fill:#FAEEDA,stroke:#854F0B

    class C enter
    class D,E skip
    class I close
    class K hold
    class RETRY retry
```

**What this shows:** Trigger → gate (zone check) → entry + TP + stop → invalidation paths.
Two skip paths (AT/BEYOND and FAR) handle the majority of triggers.
The gate keeps only the NEAR/MID minority where the M30-band TP is coherent.

### 5.2a Position Lifecycle — State Diagram (V36.13 IN-FLIGHT)

```mermaid
stateDiagram-v2
    [*] --> FLAT
    FLAT --> TRIGGERED : "M15 flips to F or R"
    TRIGGERED --> FLAT : "gate skip - atband, FAR, concurrent, nodata"
    TRIGGERED --> OPEN : "gate pass - act 1 or 2, SL and TP set"
    OPEN --> EXIT_PENDING : "TP hit, M15 revert, or timeout - act 7 issued"
    EXIT_PENDING --> EXIT_PENDING : "close rejected - re-issue act 7 next bar"
    EXIT_PENDING --> FLAT : "live counts confirm flat"
    OPEN --> FLAT : "broker SL filled - counts reach zero, sync"
```

> **Note:** EXIT_PENDING retry loop is V36.13 IN-FLIGHT. Entries are blocked while OPEN or EXIT_PENDING (one position at a time). Pre-V36.13 the EXIT_PENDING state did not exist — a rejected close orphaned the position (the 2026.01.14 ERROR 4756 case).

### 5.2b Per-Bar End-to-End Flow — Sequence Diagram

```mermaid
sequenceDiagram
    participant EA as Tofu_EA_Simple_V6
    participant TS as Trade_Strategy_TofyTrade6
    participant Broker as tester_broker

    EA->>TS: OnTick - bb data, live BUYS SELLS
    TS->>TS: identify states and BBLoc
    TS->>TS: detect M15 flip
    TS->>TS: gate m30bbloc zone
    TS->>TS: manage position - TP, revert, timeout, retry
    TS-->>EA: Trade_act, Trade_sl, Trade_info
    EA->>Broker: ORDER_SEND or ORDERS_CLOSE per act
    alt close rejected - e.g. market closed, error 4756
        Broker-->>EA: fail retcode
        Note over TS: exit_pending stays true - act 7 re-issued next bar (V36.13 IN-FLIGHT)
    else close filled
        Broker-->>EA: out deal
        Note over TS: next bar counts show flat - state resets
    end
```

### 5.3 Build Status

| Component | Status | Detail |
|-----------|--------|--------|
| Tradeability gate (NEAR/MID only) | **DESIGN** | Measured: 230 qualifying triggers / 4 months |
| Take-profit (M30 band) | **DESIGN** | 98.1% reach NEAR+MID FOLLOWED; 61-72% ALL at N=12 |
| Stop (opposite M15 band) | **DESIGN** | Least-grounded parameter — unmeasured |
| Invalidation (M15 revert or 12 rows) | **DESIGN** | From cascade validity window |
| Sizing (0.01 lots) | **DESIGN** | Fixed v1 |

> **DESIGN — measured rules, unimplemented.** The rules are grounded in four
> committed analyses (CASCADE_LEAD, TARGET_REACH, TIER2_REACH, MULTIINPUT_PREDICTION).
> The stop parameter is the least-grounded — V36.11 price logs decide.

---

## Cross-Layer Data Flow — Sequence Diagram

Per-bar L1→L2→L3: Identify → Detect → Act, showing what each layer passes to the next.

```mermaid
sequenceDiagram
    participant Tick as "Tick<br/>(per M15 bar)"
    participant L1 as "Layer 1<br/>IdentifyDualTF"
    participant L1Out as "DualTFScenarioState<br/>s"
    participant L2 as "Layer 2<br/>TransitionDetector"
    participant L2Out as "Trigger<br/>(direction, validity)"
    participant L3 as "Layer 3<br/>Trade Ruleset"
    participant L3Out as "TradeAction"

    rect rgb(240, 248, 255)
    Note over Tick,L1Out: "LAYER 1 — Identify DualTF Scenario"
    Tick->>L1: "BB_datas[] + close_prices + band_data"
    L1->>L1: "BBW_stage → F/S/C/R per TF"
    L1->>L1: "D1×H4 → HTF pair, H1×M30 → MTF pair"
    L1->>L1: "BBLoc: real price-vs-band"
    L1-->>Tick: "DualTFScenarioState s<br/>(per-TF states, per-TF bbloc,<br/>combo strings, m15_state)"
    end

    rect rgb(255, 248, 240)
    Note over Tick,L2Out: "LAYER 2 — TransitionDetector"
    Tick->>L2: "DualTFScenarioState s"
    L2->>L2: "M15 flip to F or R?"
    L2-->>Tick: "Trigger: direction, fire-time,<br/>12-row validity"
    end

    rect rgb(250, 250, 250)
    Note over Tick,L3Out: "LAYER 3 — Trade Ruleset"
    Tick->>L3: "Trigger + DualTFScenarioState s"
    L3->>L3: "Gate (zone check) → Entry → TP → Stop"
    L3->>L3: "Invalidation: M15 revert or 12 rows"
    L3-->>Tick: "TradeAction<br/>(act, stop_price, info)"
    end
```

**Data flow summary:**
- **L1 → L2:** DualTFScenarioState (per-TF states, per-TF bbloc, combo strings, m15_state)
- **L2 → L3:** Trigger (direction, fire-time, 12-row validity window)
- **L3 output:** TradeAction (act, stop_price, info) — drives OrderSend/OrderClose

---

## Analysis-side vs EA-side — Comparison

| Capability | Analysis side | EA side |
|------------|--------------|---------|
| BBLoc | Coarse {1,2,3,5} from BBUpDn mapping | Real 0-10 from price/band computation |
| Prior-state scenarios (R2/R3, P, V3/V4, B3) | Undetectable (single snapshot, no history) | Detectable (rolling buffer tracks full trajectory) |
| Detector trigger | M15 flip from log (post-hoc) | Real-time M15 flip detection |
| Validation | CASCADE_LEAD_ANALYSIS (7,608 rows) | Live forward-test on transitions |
| Per-TF BBLoc | Not available (V36.02 and earlier) | Per-TF bbloc (V36.05+) — d1_bbloc, h4_bbloc, h1_bbloc, m30_bbloc, m15_bbloc |
| M15 leading-edge | Coarse BBUpDn mapping only | Real BBLoc + state from price/band |

> **The EA is the REAL test of the DualTF detector.** The analysis side operates on coarse, static data (BBUpDn mapping, single snapshot). The EA has real-time, continuous data (price-vs-band, per-TF bbloc). The CASCADE_LEAD_ANALYSIS (7,608 rows) grounds the TransitionDetector — the EA's forward-test on live data is the true measure.

---

## Blocker Integration & Build Phases

The s_prevH1Sqz timing bug fix + scenario rename + V31.06 backtest promotion baseline
was claimed as a blocker for DualTF — **FALSIFIED**. DualTF was built and backtested
independently (V36.01–V36.10) without that baseline. That baseline gates promotion of
the OLD 7-scenario system only; DualTF is independent.

```mermaid
flowchart TD
    subgraph BLOCKERS["BLOCKERS — old 7-scenario system only"]
        B1["s_prevH1Sqz timing bug fix<br/>(V31.06: capture-prior-then-update)"]
        B2["Scenario rename A→F...<br/>(align with 4-state nomenclature)"]
        B3["V31.06 backtest promotion<br/>(baseline validation)"]
    end

    subgraph LAYER1["LAYER 1 — IdentifyDualTF"]
        P3["IdentifyDualTF<br/>(BUILT & BACKTESTED V36.10)"]
    end

    subgraph LAYER2["LAYER 2 — TransitionDetector"]
        P4["TransitionDetector<br/>(MEASURED-VIABLE, not yet implemented)"]
    end

    subgraph LAYER3["LAYER 3 — DecideTradeAction"]
        P5["Measured v1 Trade Ruleset<br/>(DESIGN — measured rules, unimplemented)"]
    end

    B1 --> B2 --> B3
    P3 --> P4 --> P5
```

**Phase list:**

| Phase | Task | Status |
|-------|------|--------|
| 0 | s_prevH1Sqz fix (V31.06) + scenario rename + backtest promotion | **OLD SYSTEM ONLY** — DualTF independent |
| 1 | Build IdentifyDualTF (per-TF derivation, HTF/MTF pairing, BBLoc) | **BUILT** — V36.10 |
| 2 | Build TransitionDetector (M15 flip detection, F/R only) | MEASURED-VIABLE |
| 3 | Build DecideTradeAction (measured rules: gate, TP, stop, invalidation) | DESIGN |

---

## Open Questions / v2 Hypotheses

These are explicitly unmeasured — they follow from the analysis but need their own
measurement before design work.

### TofySideway filter (untested)

See SIDEWAY_ARCHITECTURE.md for the sideways-classification detector. TofySideway
is a candidate FILTER for the (now-closed) DualTF entry or any future premise, and
its trading value is UNTESTED.

### AT-Band Trend-Ride (v2 candidate — highest priority)

The skip rule discards the HIGHEST-following triggers: the at-band majority follows
at 52% (116/222) vs 23% (54/230) for the kept NEAR/MID minority. A different trade
type may exist here — momentum entry, exhaustion exit. The H4-at-band hold rate is
65% (TARGET_REACH_ANALYSIS.md), and tier-3 H4 reach from the at-band population is
63–68% (TIER2_REACH_ANALYSIS.md). v2 needs its own target/exit measurement first.

### Stop-Source Comparison

Opposite M15 band vs opposite M30 band vs fixed price offset. Unmeasured — the
stop parameter is the LEAST-GROUNDED in the v1 ruleset. V36.11 price logs decide.

### M30→H1 Cascade for Trade Management

The tier-2 cascade died as a TP rule (lift 0.99x, T2-2 FAIL). But H1 reach as a
hold/scale signal — "ride through the M30 band toward H1" — is unmeasured.

### D1 as Persistence/Exhaustion Context

D1 as a macro context for trade duration (e.g., D1 fly-up = longer hold window)
is unmeasured. D1 is never a target — its role is confinement/exhaustion context.

### Sparse-BBLoc Quantization

The sparse bbloc scale (0,1,3,5,7,9,10) may overstate the 68.9%-flat-slope finding
from the prediction analysis. Noted, NOT a license to reopen prediction.

---

## V36.14 — M30-confirmed cascade entry (CLOSED)

> **STATUS: REJECTED.** Combined-clean OOS PF 0.71 (n=169); PRE 0.66, POST 0.88.
> The DualTF band-state entry is CLOSED at all confirmation levels.

### What changed vs V36.13

- Entry gate now requires M30 to flip to the trigger direction within 12 bars of the M15 flip (confirmation), instead of M15-alone. Exits/SL/TP/sizing unchanged.

### Measured result table

| Confirmation level | Source report | OOS PF (n) | Verdict |
|--------------------|----------------|------------|---------|
| M15-alone (V36.13) | V36_13_DISSECTION.md | -0.5 pp, NOT-SEPARABLE | REJECTED |
| H4xH1 filter (S-F) | SF_FORWARD_TEST.md | PF 0.13 (n=26) | REJECTED |
| M30-confirmed (V36.14) | V36_14_FORWARD.md | PF 0.71 (n=169) | REJECTED |

One row per confirmation level, each with its verdict. The failure is the PREMISE (band-state flip predicts direction), not the timing. No further DualTF entry variant is pursued.

---

## Evidence Index

| Hypothesis / Finding | Analysis File | Commit | Verdict |
|---------------------|---------------|--------|---------|
| Cascade lead (M15 flip → M30 transition) | CASCADE_LEAD_ANALYSIS.md | 623f38d | **VIABLE** — 57.2% recall, 2.03x/2.01x lift, median 5 rows |
| M30-band TP (NEAR+MID) | TARGET_REACH_ANALYSIS.md | 3a0ea21 | **VIABLE** — 98.1% reach NEAR+MID FOLLOWED |
| H4-band TP (MID+FAR) | TARGET_REACH_ANALYSIS.md | 3a0ea21 | **DEAD** — C1 FAIL 24.4% |
| Tier-2 H1 cascade | TIER2_REACH_ANALYSIS.md | 53cb2eb | **DEAD** — T2-2 FAIL 0.99x lift |
| HTF filter (agreeing vs disagreeing) | CASCADE_LEAD_ANALYSIS.md | 623f38d | **DEAD** — 33.0% vs 35.9%, no effect |
| Multi-input prediction | MULTIINPUT_PREDICTION_ANALYSIS.md | 623f38d | **DEAD** — 43.9% OOS, overfit 40.8%→35.3% |
| Zone gate (FAR skip) | TARGET_REACH_ANALYSIS.md | 3a0ea21 | **VIABLE** — FAR follow 13% (6/45) |
| AT-band hold rate (H4) | TARGET_REACH_ANALYSIS.md | 3a0ea21 | **VIABLE** — 65% ride rate |
| V36.14 M30-confirmed entry | V36_14_FORWARD.md | b194c56 | **REJECTED** PF 0.71 OOS |

DualTF-entry line: **CLOSED** — all three entry-timing variants (M15-alone, HTF-filtered, M30-confirmed) failed out-of-sample. The failure is the PREMISE (band-state flip predicts direction), not the timing. Part 3 IDENTIFICATION survives as reusable.
