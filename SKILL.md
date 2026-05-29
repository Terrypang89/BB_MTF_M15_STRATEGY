---
name: BB_MTF_M15_STRATEGY
description: >
  Multi-Timeframe Bollinger Band trade strategy skill for XAUUSD EA development
  on MetaTrader 4/5 (MQL4/MQL5). Use this skill whenever the user asks about:
  trade strategy logic, scenario decisions, BBW_Stage codes, BB_diffMid_Trend values,
  Trade_Strategy() function, H2L/L2H chain detection, fly_shrink handling,
  M15 midtrend transitions, position sizing, ATRSL stop placement, ORDER_SEND
  with SL, scenario table interpretation, or any question involving 511/512/521/522/
  513/523/400 stage codes. Also trigger when the user pastes EA log lines containing
  [M15], [M30], [H1], [ATRSL1buf], [TRADEINFO], or [AllTF] tags. Also trigger
  when the user asks about backtest analysis, version comparison, root cause analysis,
  loss deal investigation, or mentions "new backtest data" — read references/Task_force.md
  for the standard workflow. When invoked with a path argument like
  `@references/Backtest_data/`, execute the full 9-step analysis workflow
  defined in section 15 of this skill. This skill contains the full authoritative definition
  of all regime codes, decision gates, scenario conditions, MQL4 code patterns, and the
  backtest analysis procedure — always consult it before answering any strategy, code,
  or backtest question for this EA.
---

# BB Multi-Timeframe Trade Strategy

Full reference for the XAUUSD multi-timeframe Bollinger Band EA.
Covers all regime codes, decision logic, scenario conditions, MQL4 patterns,
and position sizing rules.

---

### 1. System Architecture

```
Timeframe   Role                          Index in BB_datas[]
─────────── ───────────────────────────── ──────────────────
W1          Ultra-macro context           6
D1          Daily macro context           5
H4          Macro bias filter (v22.12+)   4
H1          Chain anchor + G0 sideway     3
M30         Mid TF — primary trend        2
M15         Mid TF — entry alignment      1   ← full stage+mid check
M15         Entry trigger (transition)    1
ATRSL       Dynamic stop (dir 0/1/2)      separate struct
```

**Key rule:** M15 is a full mid-timeframe, not just a confirmation flag.
Both M30 AND M15 stage+midtrend must be checked and must agree before entry.

---

### 2. BBW_Stage Codes

```
Code    Name                  BB Bands Behaviour         Trade Bias
──────  ────────────────────  ────────────────────────   ──────────
511     FLY++ mid uptrend     Upper↑ Lower↑ Mid↑         BUY
512     FLY +- parallel up    All bands rising together  BUY
521     FLY++ mid downtrend   Upper↑ Lower↑ Mid↓         SELL
522     FLY -+ parallel dn    All bands falling          SELL
513     FLY-- bullish shrink  Upper↓ Lower↑ Mid↑         WATCH → use M5
523     FLY-- bearish shrink  Upper↑ Lower↓ Mid↓         WATCH → use M5
400-499 SQZ                   Midband flat, compressed   WAIT → breakout
200     FLY parallel          Price-act specific         Reduce size
300     FLY shrink            Price-act specific         Reduce size
0       First bar / unset     Not ready                  Stand aside
```

---

## 3. BBDiffMidTrend Values

```
Value   Name                Description
──────  ──────────────────  ─────────────────────────────────────────
1       Uptrend             Price above midline, midline rising
2       Downtrend           Price below midline, midline falling
3       Sideways            Midline flat — no direction
4       Sideway downtrend   Sideways with downward bias
5       Sideway uptrend     Sideways with upward bias
```

---

## 4. M5 Midtrend Transition — Entry Trigger

The precise entry signal is a **BBMidTrend transition on M5**.
Read across `LA` (current), `LA_1` (prev), `LA_2` (prev-2).

```
Transition          Condition                 Base Quality  Action
─────────────────── ─────────────────────── ─────────────  ──────────────────
FLAT → UP           (prev==3||prev2==3)&&cur==1   70       Enter BUY
FLAT → DN           (prev==3||prev2==3)&&cur==2   70       Enter SELL
UP → DN direct      prev==1 && cur==2             75       Exit BUY → SELL  ← raised from 60 (v22.13 Fix B)
DN → UP direct      prev==2 && cur==1             75       Exit SELL → BUY  ← raised from 60 (v22.13 Fix B)
FLAT → SIDEUP       prev==3 && cur==5             45       Early BUY (M15 SQZ only)
FLAT → SIDEDN       prev==3 && cur==4             45       Early SELL (M15 SQZ only)
UP → FLAT fading    prev==1 && cur==3              0       REDUCE longs 50%
DN → FLAT fading    prev==2 && cur==3              0       REDUCE shorts 50%
```

**Quality boosters (+10 each) — M15 requires BOTH stage AND midtrend:**
```
+10  M5 midband rising (BUY) or falling (SELL)
+10  M5 close above midband (BUY) or below midband (SELL)

FLAT→UP  BUY  boost: M15_stage==511 AND M15_mid==1   (+10)
FLAT→DN  SELL boost: M15_stage==521 AND M15_mid==2   (+10)
FLAT→SIDEUP  BUY  boost: M15_stage==511 AND M15_mid==1  (+20)
FLAT→SIDEDN  SELL boost: M15_stage==521 AND M15_mid==2  (+20)
UP→DN  SELL confirm: M15_stage∈{521,522} AND M15_mid==2 (+15)
DN→UP  BUY  confirm: M15_stage∈{511,512} AND M15_mid==1 (+15)

Rationale: midtrend alone is insufficient — M15 must also be in
active fly expand (511/521) to confirm the M5 transition signal.
```

**Quality → size:**
```
≥ 90  → 1.0×    ≥ 75 → 0.75×    ≥ 60 → 0.5×    ≥ 45 → 0.25×    < 45 → 0×
```

---

## 5. Trade_Act Quick Map

**v22.x production values (only these 4 are set by Trade_Strategy()):**

```
act  Name                    Condition
───  ──────────────────────  ──────────────────────────────────────
0    WAIT / hold             Gate blocked / neutral / hold existing
1    exit_sell + open BUY    BUY direction (all BUY paths → always act=1)
2    exit_buy  + open SELL   SELL direction (all SELL paths → always act=2)
7    exit_all, no new trade  G0/G0b-PINK/G5-FADE/G6-REV + Phase 1 intercept
```

Values 3, 4, 5, 6, 11, 12 exist in the enum but are **not set** by Trade_Strategy().

> Version changelog (v22.11–v22.38): see `CLAUDE.md` and `references/fix.md`.

**Gate Labels (current):**
```
[G0d-COOL] N       Post-exit cooldown N bars remaining      → act=0  (DimGray)
[PHASE2-BUY]       Pending reversal confirmed BUY           → act=1  (Lime)
[PHASE2-SELL]      Pending reversal confirmed SELL          → act=2  (OrangeRed)
[PHASE2-WAIT]      Pending, MIN_HOLD_BARS not elapsed       → act=0  (Yellow)
[PHASE2-CANCEL]    Pending cancelled (G0/G0c would fire)    → act=0  (DimGray)
[G0]               M30+M15+H1 all sideways                  → act=7  (Crimson)
[G0-HOLD]          M30+M15 sideways, H1 trending            → act=0  (DimGray)
[G0b-PINK]         M15+M30 both SQZ (cascade pink zone)     → act=7  (Magenta)
[G0b-ATRSL]        Cascade: ATRSL opposes band-touch dir    → act=0  (DimGray)
[G0b-M15OPP]       Cascade: M15 opposing fly/shrink/SQZ     → act=0  (DimGray)
[G0b-H4OPP]        Cascade: H4 opposing fly/shrink          → act=0  (DarkOrange)
[G0b-M30OPP]       Cascade: M30 opposing fly/shrink (incl. 523 flat mid v22.29) → act=0 (DimGray)
[G0b-SQZLOCK]      Cascade: H1+M30 both SQZ, both mid==3   → act=0  (Magenta)
[G0b-TOUCH]        Cascade band touch entry                 → act=1/2 (Lime/OrangeRed)
[G0b-WAIT]         Cascade active, no touch yet             → act=0  (Yellow)
[G0c-SQZLOCK]      H1_SQZ + M30_cmp or M15_SQZ             → act=0  (Magenta)
[H4-OPPOSE]        H4 opposing trade direction              → act=0  (DarkOrange)
[H4-SQZ]           H4 SQZ: blocks fly if M5mid not confirming (v22.23) → act=0/cont (DarkOrange)
[G1-OK]            M30 or M15 midtrend confirms             → cont.
[G1-FAIL]          Neither M30 nor M15 confirms             → act=0  (DimGray)
[G4-BLOCK]         M15 hard conflict (clear mid==1/2 only)  → act=0  (Red)
[G4b-H1OPP]        Shrink: H1 full-fly opposing M30 dir     → act=0  (DimGray)
[G4c-M15OPP]       Shrink: M15 opposing fly/shrink (523/513 v22.24) → act=0 (DimGray)
[G4d-M30SID]       Shrink: M30 flat + M15 opposing (v22.22) → act=0 (DimGray)
[G4e-H4OPP]        Shrink: H4 macro opposing fly/shrink     → act=0  (DimGray)
[G4f-M30OPP]       Shrink: M30 fly/shrink/SQZ opposing (v22.26, SQZ v22.27) → act=0 (DimGray)
[G4g-H1H4SQZ]     Fly H4-SQZ: H4+H1 both SQZ double-compressed → act=0 (DimGray)
[G4h-H4M30SQZ]    Fly H4-SQZ: H4+M30 both SQZ macro+mid compressed → act=0 (DimGray)
[G4i-H4M30FLY]    Fly H4-SQZ: M30 opposing committed fly → act=0  (DimGray)
[G4j-D1OPP]       H4-SQZ contexts: D1 opposing committed fly → act=0 (DimGray)
[G0b-H1SQZDN]     Cascade: H1-SQZ + opposing mid (4 vs BUY, 5 vs SELL, mid=2 v22.38) → act=0 (DimGray)
[G0e-MAXLOSS]      Emergency exit: float profit < -$50    → act=7  (Crimson)
[G8-BNDTGT]        Cascade band target: lowest fly TF outer band touch → act=7 (Crimson)
[G5-FADE]          M5 UP/DN→FLAT fading                    → act=7  (Crimson)
[G6-LOAD]          Midline SQZ loading, wait M5 break      → act=0  (Gold)
[G6-ENTRY]         Midline SQZ entry fires                  → act=1/2 (Gold)
[G6-BUY]           Shrink BUY entry                        → act=1  (Lime)
[G6-SELL]          Shrink SELL entry                       → act=2  (OrangeRed)
[G6-REV]           Shrink reversal                         → act=7  (Crimson)
[PHASE1-BUY]       Reversal to BUY intercepted (close only) → act=7  (Yellow)
[PHASE1-SELL]      Reversal to SELL intercepted (close only)→ act=7  (Yellow)
[G7-H1OPP]         Cases 3/4 breakout blocked by H1 opposing fly → act=0 (DimGray)
[G7-NEUTRAL]       Fell through all gates                   → act=0  (DimGray)
[G7-NOCHAIN]       M5-only chain in breakout/sideway context → act=0 (DimGray)
[G7-SUPPRESSED]    Lots below SYMBOL_VOLUME_MIN             → act=0  (DimGray)
[G7-TOOSOON]       Within MIN_HOLD_BARS of last entry       → act=0  (DimGray)
```

**Pending Fix D:**
```
Fix D: Profit lock before reversal — if open profit >= PROFIT_LOCK_PIPS (15 pts)
       and reversal fires → close only (act=7), no forced counter-trade.
```

---

## 6. Decision Gates (top-down on each new bar)

### ⚠️ Gate 0 — M30 + M15 Dual Sideway EXIT (HIGHEST PRIORITY)
```
IF M30 BBMidTrend >= 3 AND M15 BBMidTrend >= 3
→ Trade_act = 7  (exit_all)
→ EXIT ALL OPEN TRADES IMMEDIATELY
→ BLOCK all new entries
→ Return — skip all other gates
```
Rationale: both mid TFs lost directional conviction. No trend = no position.
Check at very top of Trade_Strategy() before any other logic.

### Gate 1 — ATRSL Direction Block (Shrink/Cascade only — NOT during normal fly)
> **v22.07:** During normal fly (H1/M30 in 511/512/521/522), ATRSL is used for
> **stop placement only**. M5 may briefly squeeze (noise) and ATRSL lags.
> Use M30 + M15 midtrend as trend reference instead.
> Gate 1 ATRSL block still applies in cascade band touch path.
```
APPLIES only when M5 BBW_stage ∈ {511, 512, 521, 522}  (fly expanding)
SKIPPED when M5 BBW_stage ∈ {513, 523}                 (shrink)
SKIPPED when M5 BBW_stage ∈ {400–499}                  (SQZ)
SKIPPED when M5 BBW_stage ∈ {200, 300, 0}              (other)

When active:
  ATRSL dir==1 (downtrend) AND intending BUY  → Trade_act=0 (block — old trail, no reversal yet)
  ATRSL dir==0 (uptrend) AND intending SELL → Trade_act=0 (block — old trail, no reversal yet)

Rationale:
  During shrink/SQZ the ATRSL stop is still trailing from a prior fly.
  Blocking new entries against it would kill valid breakout and transition signals.
  Only enforce the block when M5 is actively expanding in the opposite direction
  — that is a genuine trend conflict, not just a lagging stop level.
```

### Gate 2 — H1 Classification
```
511/512 mid=1  → BUY bias  → proceed
521/522 mid=2  → SELL bias → proceed
513/523        → Shrink path (see Section 7)
400-499        → SQZ/Breakout path (see Section 8)
200/300/0      → Stand aside
```

### Gate 3 — M30 Stage vs H1 Alignment
```
H1 BUY + M30=511/512  → Full alignment, size×1.0
H1 BUY + M30=513/523  → M30 shrinking, size×0.75
H1 BUY + M30=400-499  → M30 in SQZ, size×0.5
H1 BUY + M30 SELL     → Conflict → WAIT
H1 SELL mirror rules apply symmetrically
```

### Gate 4 — M15 Stage Check (full mid-TF)
```
M15=511/512 mid=1/5  → BUY aligned  → size maintained
M15=521/522 mid=2/4  → SELL aligned → size maintained
M15=513/523 mid=1    → Shrinking but uptrend → size×0.75
M15=513/523 mid=2    → Shrinking but downtrend → size×0.75
M15=513/523 mid=3    → Shrinking + flat → size×0.5
M15=400-499          → SQZ, pioneer signal possible → size×0.75
M15 opposes M30      → Conflict → WAIT (hard block)
```

### Gate 5 — M5 Midtrend Transition
```
See Section 4. Must detect FLAT→1 or FLAT→2 (or direct reversal) to enter.
M5 flat (cur==3) → no new entry regardless of higher TFs.
```

### Gate 6 — Shrink Depth Penalty
```
No shrink               → size × 1.0
M15 only shrink         → size × 0.75
M30 only shrink         → size × 0.75
H1 only shrink          → size × 0.75
M30 + H1 double shrink  → size × 0.50
All 3 shrink            → size × 0.25
HTF driving LTF sideway → additional × 0.5
```

### Gate 7 — Final Size & Suppression
```
Final lots = baseLot × qualityMulti × shrinkPenalty
Round to SYMBOL_VOLUME_STEP
If final lots < SYMBOL_VOLUME_MIN → suppress (act = 0)
```

---

## 6. H4 Fly Scenarios (quick lookup)

| H1      | M30     | M15     | M15 midtrend | Action | Size   |
|---------|---------|---------|-------------|--------|--------|
| 511/512 | 511/512 | 511/512 | 1 (up)      | BUY    | 1.0×   |
| 511/512 | 511/512 | 511/512 | 5 (side-up) | BUY    | 1.0×   |
| 511/512 | 511/512 | 511/512 | 3 (flat)    | WAIT   | 0×     |
| 511/512 | 511/512 | 513/523 | FLAT→1      | BUY    | 0.75×  |
| 511/512 | 511/512 | 400-499 | FLAT→1      | BUY    | 0.75×  |
| 513/523 | 
| 511/512 | 511/512 | 521/522 | any         | WAIT   | 0×     |
| 521/522 | 521/522 | 521/522 | 2 (down)    | SELL   | 1.0×   |
| 521/522 | 521/522 | 521/522 | 4 (side-dn) | SELL   | 1.0×   |
| 521/522 | 521/522 | 521/522 | 3 (flat)    | WAIT   | 0×     |
| 521/522 | 521/522 | 513/523 | FLAT→2      | SELL   | 0.75×  |

> For full 79-scenario table → see `references/scenarios.md`

---

## 7. Fly Shrink Handling

When M5, H1, M30, or M15 = 513/523:
- That TF's BB is contracting — midband signal unreliable for that TF
- **M5 midtrend is the primary directional proxy** during any shrink
- Entry only on M5 transition event (FLAT→UP or FLAT→DN)
- Apply shrink depth penalty from Gate 6

**M5-only shrink (M5=523, M15 still flying):**
- M15 provides fly direction, M5 midtrend is the trigger
- Penalty = 0.90× (lightest — M15+ still flying cleanly)
- Previously returned NEUTRAL incorrectly — now caught by shrink path

**During shrink, do NOT:**
- Enter based on H1/M30 stage alone
- Enter when M5 midtrend = 3 (flat)
- Add to position when M5 is UP→FLAT (fading)

**During shrink, DO:**
- Exit longs when M5 flips to 2 (down) during bullish shrink
- Exit shorts when M5 flips to 1 (up) during bearish shrink
- Reduce 50% when M5 goes UP→FLAT or DN→FLAT

**Midline SQZ continuation (new):**
- M30 shrink + M15 sideway + M5 in SQZ → `MIDLINE_SQZ_LOADING` logged
- When M5 SQZ breaks (stage 400-499 → 521/522) → `SQZ_BREAK_DN` quality=75 → SELL
- When M5 SQZ breaks (stage 400-499 → 511/512) → `SQZ_BREAK_UP` quality=75 → BUY

**Cascade band touch (new):**
- Separate pattern — checks BEFORE shrink path, after Gate 0
- M15→M30→H1 cascade: each TF enters fly_shrink then SQZ
- Trade at BB upper/lower band touch of highest active shrink TF
- Pink zone (M15+M30 both SQZ) → NO TRADE, return immediately

---

## 8. SQZ / Breakout Handling

**Loading phase (stage 400-499):** Stand aside completely.
Watch for: BBW expanding + BBMidTrend flip + ATRSL dir flip.

**M15 pioneer signal:** M15 breaks from SQZ before M30.
```
M30=400-499, M15=511/512, M5=1 → BUY 0.75× (pioneer)
M30=400-499, M15=521/522, M5=2 → SELL 0.75× (pioneer)
```

**Full breakout (M30+M15 both confirm):**
```
M30=511/512, M15=511/512, M15=1 → BUY 1.0× (best setup)
M30=521/522, M15=521/522, M15=2 → SELL 1.0× (best setup)
Enter at CLOSE of first confirmed bar after BBMidTrend flip
SL = ATRSL LV/Upper at the breakout candle
```

---

## 9. ATRSL Stop Placement

```
ATRSL1BUF.dir   Trade   SL field
─────────────   ──────  ─────────────────────────────────────────────
0 (uptrend)     BUY     ATRSL1BUF.ATRSLLower[LA]   (ATRSL agrees → correct stop)
1 (downtrend)   SELL    ATRSL1BUF.ATRSLUpper[LA]   (ATRSL agrees → correct stop)
1 (downtrend)   BUY     ATRSL1BUF.ATRSLMid[LA]     (ATRSL opposes BUY → emergency)
0 (uptrend)     SELL    ATRSL1BUF.ATRSLMid[LA]     (ATRSL opposes SELL → emergency)
```

SQZ breakout: use `ATRSLLower[LA]` / `ATRSLUpper[LA]` at the breakout bar index.

**ATRSLBUF_struct full fields:**
```
.dir              int     0=uptrend  1=downtrend  (no dir=2)
.ATRLV[]          double  raw ATR LV buffer
.ATRTrend[]       double  ATR trend per bar
.ATRSLUpper[LA]   double  upper stop  ← SELL stop / BUY emergency
.ATRSLLower[LA]   double  lower stop  ← BUY stop  / SELL emergency
.ATRSLMid[LA]     double  midline (emergency stop)
.BufferTMP[]      double  temp buffer
.ATRVal[LA]       double  ATR value
```
Array size: `[TF_ANUM+1]` = 6 slots. Index [LA]=0=current bar.

**SQZ breakout:** SL goes at ATRSL level of the *breakout bar*, not current bar.

---

## 10. Cascading Sideway Price Target Logic

When TFs compress from fly into shrink/sideway sequentially (M5 first, then M15, M30, H1, H4), price consistently gravitates toward the **outer band of the lowest TF that is still in fly**. This is the visual price target framework derived from observed chart behavior.

### The Cascade Direction

TFs compress bottom-up: M5 → M15 → M30 → H1 → H4. At each stage the price target is the outer band of the next higher still-flying TF.

| Active TF State | Expected Price Behavior | Trade Rule |
|---|---|---|
| All TFs in fly | Price rides outer band in trend direction | Hold position; follow M5 transitions |
| **M5 sideway** + M15/M30/H1 fly | M5 oscillates; no clear price target | **Wait** — do not enter until M15 also shrinks |
| **M15 sideway** + M30/H1/H4 fly | Price touches M15 outer band repeatedly, then ranges | Follow M5; target = M15 outer band; exit on touch |
| **M30 sideway** + H1/H4 fly | Price touches M30 upper band (BUY); ranges between M30 upper and midband | Follow M5; exit when price reaches M30 outer band |
| **H1 sideway** + H4 fly | Price touches H1 outer band; ranges between H1 upper and midband | Follow M5; target = H4 midband first, then H4 outer band |
| **H4 sideway** + H1/M30 sideway | Price oscillates between H1 upper and H1 lower bands | Sell at H1 upper touch; Buy at H1 lower touch |
| **All major TFs sideway** | No directional conviction | Exit all immediately — G0 fires (act=7) |

### Exit Triggers by Level

| Compressed TF | Visual Price Target | Gate that fires |
|---|---|---|
| M15 sideway | M15 outer band | G5-FADE when M5 goes flat |
| M30 sideway | M30 outer band | G5-FADE or G0-HOLD |
| H1 sideway | H4 middle band | G0-HOLD (H1 starts trending again) |
| H4 sideway | M15+M5 both sideway (pink zone) | G0b-PINK or G0 |
| All sideway | All mid labels ≥ 3 | G0 → act=7, exit all |

### Key Rules

1. **Only M5 sideway** → do not enter. Wait for M15 to also start shrinking before using M5 as trigger
2. **Outer band target** = the outer band of the LOWEST TF still in fly (upper band for BUY, lower for SELL)
3. **Ranging channel** = while HTF is sideway, price bounces between that HTF's upper and lower bands
4. **Exit** = when price touches/approaches the target HTF outer band — not a fixed pip target
5. **Pink zone** (M15+M5 both sideway while H1+M30 in SQZ/sideway) = exit all, no new entry
6. **Fly→Shrink→Fly (rest pattern)**: H4+H1 maintain fly direction throughout; only M30 and below briefly compress. Entry signal = M5 SQZ breakout within the shrink phase. Target = resume of fly toward H1 outer band

### Visual Reference

See `references/backtest_chart_analysis.md` Section 10 for the full cascade table, exit triggers, and annotated chart examples showing each cascade stage.

---

## 11. MQL4 Code Patterns

### Trade_Strategy() signature
```cpp
void Trade_Strategy(
   BB_MTF_Data_struct  &BB_datas[],   // TF data array [0]=M5 [1]=M15 [2]=M30 [3]=H1
   ATRSLBUF_struct   &ATRSL1BUF,        // ATRSL struct
   BB_MTF_Impact_struct   &allTF,        // HTF_Drive_LTF flags
   ENUM_Trade_Act      &Trade_act,    // OUT: 0=none 1=buy 2=sell
   string              &Trade_info,   // OUT: debug string
   double              &Trade_lots,   // OUT: calculated lot size
   double              &Trade_sl,     // OUT: stop loss price
   double               baseLot=0.01
)
```

### H2L/L2H chain detection
```cpp
// Pass 1: HTF→LTF (H2L) — scan from MAX_TF=3 down to MIN_TF=0
// Chain RESETS if broken (critical bug fix — must include else reset)
if((stage==511||stage==512) && trend==1) {
   if(i==MAX_TF || H2L_flyUP_TF==i+1) H2L_flyUP_TF=i;
   else H2L_flyUP_TF=-1;  // ← chain break reset — do not omit
}

// Pass 2: LTF→HTF (L2H) — scan from MIN_TF=0 up to MAX_TF
// MIN_TF must be 0 (not 1) to include M5
// Loop bound must be i<=MAX_TF (not i<6) to avoid out-of-bounds
```

### Decision cases (with conflict guard)
```cpp
bool htfDN=(H2L_flyDN_TF!=-1), htfUP=(H2L_flyUP_TF!=-1);
bool ltfUP=(L2H_flyUP_TF!=-1), ltfDN=(L2H_flyDN_TF!=-1);

// Case 1: HTF bearish + LTF turning bullish → BUY reversal
if(ltfUP && htfDN && !htfUP) { Trade_act=1; }
// Case 2: HTF bullish + LTF turning bearish → SELL reversal
else if(ltfDN && htfUP && !htfDN) { Trade_act=2; }
// Case 3: HTF shrink/SQZ + LTF breaking UP → BUY breakout (v22.14: M15+ required)
else if(ltfUP && L2H_flyUP_TF>=1 && (htfShrk||htfSide) && !htfDN) { direction=1; }
// Case 4: HTF shrink/SQZ + LTF breaking DN → SELL breakout (v22.14: M15+ required)
else if(ltfDN && L2H_flyDN_TF>=1 && (htfShrk||htfSide) && !htfUP) { direction=2; }
// M5-only in cases 3/4 context → nochain=true → [G7-NOCHAIN] ltf_M5only
else if((ltfUP||ltfDN) && (htfShrk||htfSide))                      { nochain=true; }
```

### ORDER_SEND with SL
```cpp
void ORDER_SEND(ENUM_ORDER_TYPE CMD, double LOTS, string COMMENT,
                int MAGIC, string TRADE_INFO="",
                double SL=0.0, double TP=0.0)
// SL must be normalized to SYMBOL_DIGITS
// Validate: |entry - SL| >= SYMBOL_TRADE_STOPS_LEVEL × SYMBOL_POINT
// Send with SL=0 first, then OrderModify() after fill
// Re-validate SL against actual fill price before modifying
```

### Shrink detection in MQL4
```cpp
bool M30_shrink=(BB_datas[2].BBW_stage[LA]==513||BB_datas[2].BBW_stage[LA]==523);
bool H1_shrink =(BB_datas[3].BBW_stage[LA]==513||BB_datas[3].BBW_stage[LA]==523);
bool M15_shrink=(BB_datas[1].BBW_stage[LA]==513||BB_datas[1].BBW_stage[LA]==523);
int  M15_cur    = BB_datas[1].BB_diffMid_Trend[LA];
int  M15_prev   = BB_datas[1].BB_diffMid_Trend[LA_1];
```

---

## 12. Common Bugs & Fixes

| Bug | Symptom | Fix |
|-----|---------|-----|
| `min_TF=1` | M5 excluded from L2H chain | Change to `min_TF=0` |
| L2H loop `i<6` | Out-of-bounds on BB_datas[] | Change to `i<=MAX_TF` |
| No chain reset in H2L | Non-consecutive TFs match | Add `else H2L_flyUP_TF=-1` |
| `-1 <= max_TF` always true | Case 1/2 fire with no signal | Guard with `!= -1` bool check |
| SL sent in OrderSend() | Broker rejects on some MT4 | Send SL=0 then OrderModify() |
| SL too close to price | MODIFY_ERROR logged | Validate against STOPS_LEVEL |
| Single M5 bar transition missed | Entry delayed 1+ bars | Check prev2 also: `LA_1==3||LA_2==3` |

---

## 13. Log Line Decoder

When the user pastes log lines, decode them as follows:

```
[M15]   W_stage_M15:(FLY)[522,522,522]  → last 3 bars all 522 (parallel dn)
       diffMid_Trend_M5:[2.0,4.0,2.0] → midtrend: down, side-dn, down
       diffBBW_M15:[-2.96,-1.94,-0.93] → BBW shrinking (negative = contracting)

[ATRSL1buf] dir:0                     → no trailing yet, static stop
            LV:[2861.85,...]           → lower stop level
            Upper:[2868.54,...]        → upper stop level

[AllTF] HTF_Drive_LTF_Sideway:[M5_1,M15_1]  → HTF suppressing LTF into sideway
        LTF_Drive_HTF_Fly:[M15_1,H1_1]       → LTF momentum building upward
```

### [TRADEINFO] Format (v22.22+)

Every line: `[TRADEINFO] Gate:[NAME] TradeAct:N key:val...| Gate:[NAME] key:val...|act:N atrsl:N`

- **First segment** always has `Gate:[NAME] TradeAct:N` + gate params
- **Subsequent segments** append as `| Gate:[NAME] params` (no `TradeAct`)
- **Final suffix** `|act:N atrsl:N` = resolved action + ATRSL direction

```
[TRADEINFO] Gate:[G0d-COOL] TradeAct:0 cd:4|act:0 atrsl:0
  → post-exit cooldown, 4 bars remaining, no action

[TRADEINFO] Gate:[G0] TradeAct:7 M30:3 M15:3 H1:3|act:7 atrsl:1
  → all three TFs sideways → exit all

[TRADEINFO] Gate:[G0b-TOUCH] TradeAct:0 TF:3 touch:lower_band sl:3250.50|act:1 atrsl:0
  → cascade band touch on H1 (TF index 3) at lower band → BUY

[TRADEINFO] Gate:[G1-OK] TradeAct:0 M30:1 M15:5| Gate:[FLY] dir:1 sl:3248.00 H2L:-1/-1 L2H:2/-1|act:1 atrsl:0
  → M30 up + M15 sideway-up confirm → fly BUY, SL at 3248

[TRADEINFO] Gate:[H4-SQZ] TradeAct:0| Gate:[G1-OK] M30:1 M15:1| Gate:[G4-BLOCK] M15:2|act:0 atrsl:1
  → H4 in SQZ (noted), G1 ok, but M15 hard-opposing → blocked

[TRADEINFO] Gate:[G6-SHRINK] TradeAct:0 cnt:2+M5 pen:0.75| Gate:[G5] c:1 p:3 p2:3 M15s:511 M15m:1 t:flat_up mid+ abv M15ok q:90 sz:1.0| Gate:[G6-BUY] sl:3250.50|act:1 atrsl:0
  → shrink path, M5 FLAT→UP transition (q=90 → full size 1.0×) → BUY
```

**Gate:[G5] t: field values:** `flat_up` `flat_dn` `up_dn` `dn_up` `weak_up` `weak_dn` `sqz_brk_up` `sqz_brk_dn`
**Quality boosters (appended if active):** `mid+` (midband aligned) `abv` (price above/below midband) `M15ok` (M15 confirms)
**Quality → size:** `≥90→1.0×` | `≥75→0.75×` | `≥60→0.5×` | `≥45→0.25×` | `<45→0×`

Full gate attribute reference: `references/log_matrix.md`

---

## 14. Reference Files

Read these when you need full detail beyond this overview:

| File | Contents | When to read |
|------|----------|--------------|
| `scripts/TofyTrade4.mqh` | Full EA include file v22.38 — latest production code | When writing or reviewing MQL4/5 code |
| `references/backtest_chart_analysis.md` | Visual interpretation guide for backtest chart screenshots — BB color mapping, BBW_stage visual decode, ATRSL reading, gate label colors, 9 annotated reference images with analysis | When analyzing an attached chart image or explaining what EA chart elements look like visually |

---

## 15. Backtest Analysis Workflow — `/bb-mtf-strategy @path/to/version`

**Trigger:** User runs `/bb-mtf-strategy @references/Backtest_data/V22.XX` or pastes backtest data and says "run analysis".

Auto-detect `VER` from path (e.g., `V22.38`). Auto-detect `PREV_VER` as the immediately preceding version with same test period from `references/version_profit.md`.

**Goal:** Each new version must achieve **higher net profit** than PREV_VER. Every deal loss < −10 USD is a fix candidate — prioritize by highest absolute loss first.

---

### 9-Step Execution Checklist

```
Step 0  Read Task_force.md                 (scripts, RC patterns, gate templates)
Step 1  Net profit comparison              → update version_profit.md + root-cause-analysis.md
Step 2  Deal loss comparison               → update version_profit.md
Step 3  Set fix priorities                 (ranked list, confirm net profit goal)
Step 4  Root cause analysis                → update root-cause-analysis.md
Step 5  Code fix                           → edit TofyTrade3.mqh + bump version
Step 6  Fix verification                   (confirm gate fires, check over-filtering)
Step 7  Update Task_force.md              (targeted additions only)
Step 8  Update all related reference files (table in Step 8 below)
Step 9  Git commit
```

---

### Step 0 — Read Task_force.md

> **Read: `references/Task_force.md`**

Must read before any other step. Contains:
- Python scripts for Steps 1–6 (net profit, deal comparison, log search, TF context, verification)
- Cascade gate insertion order — reference for Step 5 code placement
- Root Cause Decision Tree — maps entry gate + TF pattern → RC number
- GATE_CLR registries — correct color constants for new gate labels
- Replacement Entry Phenomenon explanation

Do not guess script syntax — copy from `Task_force.md` exactly.

---

### Step 1 — Net Profit Comparison

> **Read: `references/version_profit.md`**  
> **Update: `references/version_profit.md`** (regenerate), **`references/root-cause-analysis.md`** (add VER row to version table)

Run `python scripts/gen_version_profit.py` to regenerate `version_profit.md` for all versions in the same test-period group. Confirm:
- Same test period as PREV_VER? (Jan–Apr vs Jan-only are not comparable — note explicitly)
- VER net profit > PREV_VER net? → mark **IMPROVED** or **REGRESSION**

Add VER row to the version comparison table at the top of `root-cause-analysis.md` (net, PF, total deals, delta vs PREV_VER).

> If `gen_version_profit.py` is missing or outdated, use the Part 1 script in `Task_force.md` and append results manually.

---

### Step 2 — Deal Loss Comparison

> **Read: `references/Task_force.md`** (Part 2 Python script)  
> **Update: `references/version_profit.md`** (append new `## VER vs PREV_VER Deal Loss Comparison` section)

Run Part 2 script (prev=PREV_VER path, curr=VER path). Append table with columns: Time | PREV | CURR | Delta | Status.

| Status | Meaning |
|--------|---------|
| ELIMINATED | Fix worked — confirm blocking gate in Step 4 |
| NEW | Regression from current fix — highest investigation priority |
| WORSE | Same deal, larger loss — often a replacement entry, investigate before fixing |
| BETTER | Same deal, smaller loss — partial improvement |
| SAME | Persistent unresolved loss — add to `root-cause-analysis.md` if not already there |

---

### Step 3 — Set Fix Priorities

> **Read: `references/version_profit.md`** (Step 2 output)

Build a ranked fix list from the Step 2 output:
1. **NEW losses** first — regressions from this version's changes
2. **SAME losses** by absolute value, largest first
3. **WORSE losses** — investigate replacement entry phenomenon before adding a new fix

Confirm: expected gain (losses blocked − wins blocked) must be positive before implementing.

---

### Step 4 — Root Cause Analysis

> **Read: `references/Task_force.md`** (Part 3a log search, Part 3b TF context, Root Cause Decision Tree)  
> **Read: `references/root-cause-analysis.md`** (check if RC pattern already known)  
> **Read: `references/log_examples.md`** (if decoding unfamiliar log output)  
> **Update: `references/root-cause-analysis.md`**

For each deal on the Step 3 priority list:

**4a — Find entry gate** (Part 3a script from `Task_force.md`):  
Search `VER/YYYYMMDD_clean.log` for exit timestamp → find `ORDERINFO` → scan back ≤800 lines for `|act:1` or `|act:2` TRADEINFO line. Record gate name, direction, TF index.

**4b — Get TF context** (Part 3b script from `Task_force.md`):  
Read `[M15]`, `[M30]`, `[H4]`, `[D1]` lines within ±30 lines of the entry bar. Record `BBW_stage` and `BB_diffMid_Trend` for each TF.

**4c — Match RC pattern** (Root Cause Decision Tree in `Task_force.md`):  
Cross-reference entry gate + TF context. Assign existing RC number if matched, or new RCN if novel.

**4d — Analyze neighboring TFs**:  
Is the opposing TF's stage/mid stable for 3+ bars before entry? Does any higher TF agree with direction? If no higher TF agrees — that is the missing filter.

**4e — Write RC entry to `root-cause-analysis.md`**:
```markdown
### RCN — [short description]

**Status:** NEW  
**Deals affected:** N deals, total -XXX.XX  

| Time | Loss | Dir | Context | Status |
|------|------|-----|---------|--------|
| 2026.XX.XX HH:MM | -XX.XX | BUY | M30stg=523 M30mid=2 H4stg=423 | NEW |

**Root cause:**  
[Why the gate fired and what TF guard was missing]

**Fix:**
// Proposed condition (old → new)
```

Update Summary of Fixes table: new RCN=OPEN; previously fixed RCs=FIXED.

---

### Step 5 — Code Fix

> **Read: `scripts/TofyTrade3.mqh`** (locate insertion point)  
> **Read: `references/Task_force.md`** (Part 4 gate templates + cascade gate order)  
> **Read: `references/code_patterns.md`** (MQL4 patterns if writing a new gate type)  
> **Edit: `scripts/TofyTrade3.mqh`**

1. Copy the matching gate template from `Task_force.md` Part 4
2. Insert at the correct position (cascade / shrink / fly sub-path — use cascade gate order from `Task_force.md`):
   - **Cascade (G0b)**: before `G0b-TOUCH`, after last existing filter
   - **Shrink (GetShrinkDecision)**: after `G4e-H4OPP` / `G4j-D1OPP`, before `return result`
   - **Fly H4-SQZ sub-path**: inside `else if(H4_in_sqz)`, after last G4X gate
3. Key invariants: block BUY when opposing mid ∈ {2,4}; block SELL when opposing mid ∈ {1,5}; never block on mid=3 alone unless both TFs are flat (G0b-SQZLOCK pattern)
4. Bump `#property version "22.XX"` → next version
5. Add new gate label to the `GATE_CLR_*` comment line

> Fix only the highest-priority RC per cycle. Verify net improvement (Step 6) before committing.

---

### Step 6 — Fix Verification

> **Read: `references/Task_force.md`** (Part 5 verification script)  
> **Read:** CSV or log files in `references/Backtest_data/VER/`

1. Run Part 5 script (target_entry = deal datetime)
2. Read TF stage and mid at that bar; confirm new condition evaluates TRUE → gate fires
3. Over-filtering check: count all entries with same gate pattern — (losses × avg_loss) − (wins × avg_win) must be positive
4. If net negative → do not implement; document as "net negative, deferred"

---

### Step 7 — Update Task_force.md

> **Update: `references/Task_force.md`** (targeted additions only — do not rewrite existing sections)

1. **Cascade gate order block**: add new gate line at correct position with `← added vNEW.XX`
2. **Root Cause Decision Tree**: add new RC leaf node under the correct entry gate branch
3. **GATE_CLR registries**: add new gate name to the correct color group list
4. **Persistent Unresolved RC table**: add new RCN row; mark prior RCs FIXED; append vNEW.XX note paragraph
5. **Part 1 `versions` dict**: add `'VER': ('json', 'references/Backtest_data/VER/report_tables_clean.json')`

---

### Step 8 — Update Related Reference Files

> **Update:** all files in the table below

| File | What to update |
|------|----------------|
| `references/fix.md` | Add `## vNEW.XX — [gate name] (RCNN)` section before previous version section; include root cause, code diff, expected result |
| `references/root-cause-analysis.md` | Mark new RCs FIXED; update version comparison table; add vNEW.XX note to RC detail section |
| `CLAUDE.md` | Bump source files version; add `## vNEW.XX Changes` section; update GATE_CLR line |
| `SKILL.md` (this file) | Section 13: bump `TofyTrade3.mqh` version line; Section 14: update only if SOP changes |
| `references/decision_flow.md` | Add new gate to the gate-by-gate logic section for its path (cascade / shrink / fly) |
| `references/scenarios.md` | Update if new gate changes any of the 79 scenario outcomes |
| `references/log_matrix.md` | Add new gate row with its TRADEINFO key attributes |
| `references/architecture_flow.html` | Add new gate diamond node + arrow in correct subgraph; apply matching `classDef` color |
| `references/architecture_flow.puml` | Add new gate `if` block in correct swimlane with matching `#color`; same logical position as HTML |

For architecture diagrams: insert at the same logical position as in the code. Match node color to `GATE_CLR_*` palette.

---

### Step 9 — Git Commit

> **No reads or updates — commit all staged changes**

```bash
git add scripts/TofyTrade3.mqh CLAUDE.md SKILL.md \
        references/fix.md references/root-cause-analysis.md \
        references/Task_force.md references/version_profit.md \
        references/decision_flow.md references/log_matrix.md \
        references/architecture_flow.html references/architecture_flow.puml \
        scripts/gen_version_profit.py

git commit -m "vNEW.XX: [gate name(s)] [brief description] (RCNN)"
```

Commit format: `v22.39: G0b-EXAMPLE extended to mid=N (RC27)`

After commit: next backtest run uses the newly committed version as its baseline.
