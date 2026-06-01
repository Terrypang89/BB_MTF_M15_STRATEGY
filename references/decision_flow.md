# Full Decision Flow
## BB Multi-Timeframe Trade Strategy — Complete Gate-by-Gate Logic

> Execute every gate in order on each new M15 bar close (V30.02+).
> A gate that fails **stops the flow** — no entry is made until all gates pass.

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│  TIMEFRAME ROLES                                                │
├──────────┬──────────────────────────────────────────────────────┤
│  W1      │  Ultra-macro direction — multi-week wind             │
│  D1      │  Daily macro — final price target ceiling/floor      │
│  H4      │  Macro bias — sets M30 target; controls gate filters │
│  H1      │  Chain anchor + G0 sideway confirm                   │
│  M30     │  Mid TF Primary — trend driver                       │
│  M15     │  Entry trigger (BBdiffMidTrend transition) V30.02+   │
│  ATRSL   │  Dynamic stop — dir=0=uptrend / dir=1=downtrend      │
└──────────┴──────────────────────────────────────────────────────┘
```

---

## Quick Reference — BBW_Stage Codes

| Code | Name | Bands | Bias |
|------|------|-------|------|
| 511 | FLY++ mid up | Upper↑ Lower↑ Mid↑ | BUY |
| 512 | FLY+- parallel up | All rising together | BUY |
| 513 | FLY-- bullish shrink | Upper↓ Lower↑ Mid↑ | WATCH |
| 521 | FLY++ mid dn | Upper↑ Lower↑ Mid↓ | SELL |
| 522 | FLY-+ parallel dn | All falling | SELL |
| 523 | FLY-- bearish shrink | Upper↑ Lower↓ Mid↓ | WATCH |
| 400-499 | SQZ | Bands flat/compressed | WAIT |

## Quick Reference — BB_diffMid_Trend Values

| Value | Name | Meaning |
|-------|------|---------|
| 1 | Uptrend | Price above midline, midline rising |
| 2 | Downtrend | Price below midline, midline falling |
| 3 | Sideways | Midline flat |
| 4 | Sideway downtrend | Flat with downward bias |
| 5 | Sideway uptrend | Flat with upward bias |

---

## Gate-by-Gate Flow

Every M15 bar close, gates execute in this exact order. Any gate that fires `act=7` or `act=0` stops the chain.

```
Bar close (M15)
│
├─ [G0]  M30+M15+H1 all mid≥3 → act=7 EXIT ALL
├─ [G0-HOLD] M30+M15 mid≥3, H1 mid<3 → act=0 NO NEW ENTRY
│
├─ SHRINK PATH (if H4/H1/M30/M15 stage=513/523 AND M15 mid≥3)
│  ├─ [G4-BLOCK]       M30 up + M15 clearly dn (or vice versa) → act=0
│  ├─ [G4b-H1OPP]      H1 committed opposing fly → act=0
│  ├─ [G6-LOAD]        M15 SQZ + M30 shrink + M30 sideway → log loading state
│  ├─ Adaptive trigger: M15 default; escalate to M30 if M15 noisy
│  ├─ [G4k-M15SHRKopp] M30 trigger + M15 opposing shrink → act=0
│  ├─ [G4k-TRIGDIR]    Trigger TF stage contradicts direction → act=0
│  ├─ [G5-WEAK]        Transition quality 45-59 → act=0
│  ├─ [G5-FADE]        M15 UP→FLAT or DN→FLAT → act=7 EXIT
│  ├─ [G4c-M15OPP]     M15 opposing fly/shrink/SQZ → act=0
│  ├─ [G4d-M30SID]     M30 flat + M15 opposing → act=0
│  ├─ [G4e-H4OPP]      H4 committed opposing fly → act=0
│  ├─ [G4j-D1OPP]      H4 SQZ + D1 opposing fly → act=0
│  ├─ [G4f-M30OPP]     M30 opposing fly/shrink/SQZ → act=0
│  └─ [G6-BUY/SELL]    Transition quality ≥60 → act=1/2 ENTRY
│
└─ FLY/BREAKOUT PATH (H2L+L2H chain detection)
   ├─ [G7-H1OPP]       Cases 3/4 with H1 clearly opposing → act=0
   ├─ [H4-OPPOSE]      H4 committed opposing fly → act=0, direction=0
   ├─ [H4-SQZ]         H4 SQZ, M15 mid doesn't confirm → act=0
   ├─ [G4g-H1H4SQZ]    H4 SQZ + H1 SQZ double-compressed → act=0
   ├─ [G4h-H4M30SQZ]   H4 SQZ + M30 SQZ → act=0
   ├─ [G4i-H4M30FLY]   H4 SQZ + M30 opposing fly → act=0
   ├─ [G4j-D1OPP]      H4 SQZ + D1 opposing fly → act=0
   ├─ [G1-FAIL]        Neither M30 nor M15 confirms direction → act=0
   ├─ [G1-OK]          M30 or M15 confirms → continue
   ├─ [G4-BLOCK]       M15 hard opposing mid → act=0
   ├─ M15 transition check (DetectM5Transition, triggerTF=1)
   ├─ [G5-FADE]        M15 UP→FLAT or DN→FLAT → act=7 EXIT
   └─ [FLY-BUY/SELL]   trans.direction == chain direction, quality ≥60 → act=1/2
```

---

## H2L / L2H Chain Cases

```
Case 1: ltfUP + htfDN  → direction=1 BUY  (HTF bearish, LTF reversing up)
Case 2: ltfDN + htfUP  → direction=2 SELL (HTF bullish, LTF reversing down)
Case 3: ltfUP + htfShrk/htfSide + L2H_flyUP_TF≥1 → direction=1 BUY breakout
Case 4: ltfDN + htfShrk/htfSide + L2H_flyDN_TF≥1 → direction=2 SELL breakout
```

H1 guard: Cases 3/4 block if H1 mid clearly opposes direction (→ `[G7-H1OPP]`).

---

## Shrink Path — Adaptive Trigger Logic

```
M15 clean (fly 511/512/521/522) → triggerTF = 1 (M15)  [default]
M15 noisy (SQZ/shrink) + M30 flying → triggerTF = 2 (M30)

Entry fires when: DetectM5Transition(BB_datas, close_prices, triggerTF).quality ≥ 60
Exit fires when:  transition == UP_TO_FLAT or DN_TO_FLAT  → [G5-FADE] act=7
```

---

## M15 Transition Quality Table

| Transition | Condition | Base Quality | Boost |
|------------|-----------|-------------|-------|
| FLAT→UP | (prev==3\|\|prev2==3) && cur==1 | 80 (M15) | +10 mid rising, +10 price above mid, +10 M30 cok |
| FLAT→DN | (prev==3\|\|prev2==3) && cur==2 | 80 (M15) | +10 mid falling, +10 price below mid, +10 M30 cok |
| UP→DN | prev==1 && cur==2 | 80 (M15) | +15 M30 bearish confirm |
| DN→UP | prev==2 && cur==1 | 80 (M15) | +15 M30 bullish confirm |
| FLAT→SIDEUP | prev==3 && cur==5 | 45 | +20 M30 cok |
| FLAT→SIDEDN | prev==3 && cur==4 | 45 | +20 M30 cok |
| UP→FLAT | prev==1 && cur==3 | — | → G5-FADE (exit) |
| DN→FLAT | prev==2 && cur==3 | — | → G5-FADE (exit) |

**M30 confirm** (`cok`): M30 stage=511/512 + M30 mid=1 for BUY; stage=521/522 + mid=2 for SELL.
**Quality floor**: FLAT→UP/DN without M30 confirm → quality capped at 59 → blocked by G5-WEAK.
**Quality → size**: ≥90 → 1.0× | ≥75 → 0.75× | ≥60 → 0.5× | ≥45 → 0.25× | <45 → 0×

---

## Trend Prediction — `PredictNextTrend()`

Predicts the directional bias for the **next bar** based on the current and previous BBW_stage and BB_diffMid_Trend across all six timeframes (M15, M30, H1, H4, D1, W1).

Called each bar for situational awareness. **Not a gate** — does not block or trigger trades directly. Use alongside the gate pipeline for context.

### Per-TF Directional Score

Each TF produces a score in **[-8, +8]** from four components:

```
score = stage_bias + mid_bias + stage_transition + mid_transition
```

#### Stage Structural Bias

| BBW_Stage | Score | Rationale |
|-----------|-------|-----------|
| 511 | +3 | Full bullish fly — strongest directional state |
| 512 | +2 | Parallel bullish |
| 513 | +1 | Bullish shrink — directional but weakening |
| 400-499 | 0 | SQZ — neutral, wait for breakout |
| 523 | -1 | Bearish shrink — directional but weakening |
| 521 | -3 | Full bearish fly |
| 522 | -2 | Parallel bearish |
| other | 0 | Undefined/parallel |

#### Mid Trend Bias

| BB_diffMid_Trend | Score | Rationale |
|-----------------|-------|-----------|
| 1 (uptrend) | +2 | Confirmed directional up |
| 5 (sideway-up) | +1 | Weak bullish bias |
| 3 (sideway) | 0 | Neutral |
| 4 (sideway-dn) | -1 | Weak bearish bias |
| 2 (downtrend) | -2 | Confirmed directional down |

#### Stage Transition Bonus (prev_bar → cur_bar)

| Transition | Bonus | Signal Meaning |
|------------|-------|----------------|
| SQZ → fly BUY (511/512) | +3 | Breakout upward — strongest buy signal |
| SQZ → fly SELL (521/522) | -3 | Breakout downward |
| fly SELL → fly BUY | +3 | Direct upward reversal |
| fly BUY → fly SELL | -3 | Direct downward reversal |
| fly BUY → shrink (513) | -1 | Weakening — watch for reversal |
| fly SELL → shrink (523) | +1 | Weakening |
| shrink (513) → fly BUY | +2 | Shrink resolved, trend resuming up |
| shrink (523) → fly SELL | -2 | Shrink resolved, trend resuming down |
| other | 0 | No significant structural change |

#### Mid Transition Bonus (prev_bar → cur_bar)

| Transition | Bonus | Signal Meaning |
|------------|-------|----------------|
| 2 → 1 (dn→up reversal) | +3 | Strong: downtrend just reversed upward |
| 1 → 2 (up→dn reversal) | -3 | Strong: uptrend just reversed downward |
| 3 → 1 (flat→up) | +2 | Emerging uptrend from neutral |
| 3 → 2 (flat→dn) | -2 | Emerging downtrend from neutral |
| 3 → 5 (flat→side-up) | +1 | Weak bullish bias forming |
| 3 → 4 (flat→side-dn) | -1 | Weak bearish bias forming |
| 2 → 3 (dn fading) | +1 | Downtrend losing momentum |
| 1 → 3 (up fading) | -1 | Uptrend losing momentum |
| other | 0 | No transition this bar |

### TF Weights

| TF | Index | Weight | Role |
|----|-------|--------|------|
| M15 | 1 | 1 | Entry trigger — most recent but noisiest |
| M30 | 2 | 2 | Primary trend driver |
| H1 | 3 | 2 | Chain anchor |
| H4 | 4 | **3** | Dominant macro bias — highest weight |
| D1 | 5 | 2 | Daily macro context |
| W1 | 6 | 1 | Ultra-macro — slowest, structural only |

### Aggregation and Output

```
LTF total = M15_score × 1               (max ±8)
MTF total = M30_score × 2 + H1_score × 2  (max ±32)
HTF total = H4_score × 3 + D1_score × 2 + W1_score × 1  (max ±48)

Grand total = LTF + MTF + HTF           (max ±88)

direction:
  total ≥  +22 → BUY   (~25% of max)
  total ≤  -22 → SELL
  else         → NEUTRAL

confidence:
  |total| ≥ 66 → 95   (≥75% of max — all TFs broadly aligned)
  |total| ≥ 44 → 80   (≥50% of max — clear majority)
  |total| ≥ 22 → 60   (≥25% of max — directional but not unanimous)
  else         → 25   (below threshold — ambiguous)

reversal flag:
  HTF total ≥ +18 AND LTF+MTF ≤ -12 → reversal=true (BUY counter-trend)
  HTF total ≤ -18 AND LTF+MTF ≥ +12 → reversal=true (SELL counter-trend)
  confidence capped at 65 when reversal=true
```

### Log Format

```
[PRED] BUY conf:80 htf:24 mtf:16 ltf:3 tot:43
[PRED] SELL conf:60 htf:-18 mtf:-12 ltf:-2 tot:-32
[PRED] NEUTRAL conf:25 htf:6 mtf:-4 ltf:1 tot:3
[PRED] BUY conf:65 htf:-20 mtf:14 ltf:8 tot:2 REV    ← reversal setup
```

### Interpretation Rules

| Pattern | HTF | MTF | LTF | Meaning |
|---------|-----|-----|-----|---------|
| Strong trend BUY | +high | +mid | +any | All layers aligned bullish — ideal continuation entry |
| Breakout BUY | low | +any | +high (SQZ→fly bonus) | LTF breaking out before HTF confirms — pioneer entry |
| Weakening BUY | +high | +low | 0 or - | HTF bullish but momentum fading — reduce size or wait |
| Reversal BUY | -high | +high | +high | HTF bearish, LTF+MTF turning bullish — counter-trend entry |
| Neutral | mixed | mixed | mixed | No dominant direction — stand aside |
| Mirror rules apply for SELL |

### Continuation vs Reversal vs Neutral Decision

```
             HTF ≥ +18  HTF flat  HTF ≤ -18
LTF+MTF ≥ +12  CONTINUATION BUY  BREAKOUT BUY  REVERSAL BUY
LTF+MTF flat   WEAK BUY BIAS      NEUTRAL       WEAK SELL BIAS
LTF+MTF ≤ -12  REVERSAL SELL     BREAKOUT SELL  CONTINUATION SELL
```

**Continuation** (HTF and LTF+MTF agree): highest confidence, ride the trend.
**Breakout** (HTF flat/SQZ, LTF+MTF building): pioneer entry, smaller size.
**Reversal** (HTF and LTF+MTF oppose): counter-trend trade, confidence capped at 65, tighter stop.
**Weak bias**: HTF points one way but LTF+MTF are flat — wait for LTF to confirm before entering.

### Example: HTF Bearish + M30/M15 Turning Bullish

```
W1:  stage=522 mid=2 → score=-3-2=-5 → ×1 = -5
D1:  stage=523 mid=2 → score=-1-2=-3 → ×2 = -6
H4:  stage=523 mid=3 → score=-1+0=-1 → ×3 = -3   (shrink fading)
H1:  stage=512 mid=1  → score=+2+2=+4, transition 523→512 stg_t=+2, mid 2→1 mid_t=+3 → total=+9 → ×2 = +18
M30: stage=511 mid=1  → score=+3+2=+5, mid 3→1 mid_t=+2 → total=+7 → ×2 = +14
M15: stage=511 mid=1  → score=+3+2=+5, SQZ→511 stg_t=+3 → total=+8 → ×1 = +8

HTF total = -5 + -6 + -3 = -14
MTF total = +18 + +14     = +32
LTF total = +8
Grand total = -14 + 32 + 8 = +26 → BUY direction
Confidence = 60 (|26| ≥ 22)
Reversal check: HTF=-14 (< -18 threshold not met), no reversal flag
→ [PRED] BUY conf:60 htf:-14 mtf:32 ltf:8 tot:26
```

This predicts BUY at moderate confidence: LTF+MTF are strongly bullish from recent SQZ breakout, overcoming W1/D1 bear bias. H4 has already neutralised (shrink+flat mid). Entry would be at next M15 FLAT→UP transition with M30 confirmation.

---

## Entry Gate Invariants (V30.02)

```
Block BUY  when M15/M30/H4 mid ∈ {2, 4}  (downtrend or sideway-dn)
Block SELL when M15/M30/H4 mid ∈ {1, 5}  (uptrend  or sideway-up)
mid = 3 (flat sideway) = NEUTRAL — do NOT block on mid=3 alone
```
