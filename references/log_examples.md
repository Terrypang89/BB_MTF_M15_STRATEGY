# Log Examples Reference
## Annotated EA Log Samples — How to Decode Each Line

---

## Log Line Format Reference

```
[ORDERINFO]   → open position summary (profit, lots, ticket numbers)
[ATRSL1buf]   → ATR stop loss state (dir, levels, mid, ATR value)
[M15]         → M15 Bollinger Band state
[M30]         → M30 Bollinger Band state
[H1]          → H1 Bollinger Band state (first_stage flag if uninitialized)
[TRADEINFO]   → H2L/L2H chain detection results + Trade_act decision
[AllTF]       → Cross-TF relationship flags
```

---

## Example 1: Indecision / Sideway State
**Source: 2025.03.03 06:00–06:15**

```
[ORDERINFO] BUY_PROFIT:-6.42, BUY_LOTS:0.01, BUY_TICKET_NUM:2, BUYS:1
```
**Reading:** One open BUY losing $6.42. Only 1 active order.

```
[ATRSL1buf] dir:0, Trend:[2.0,2.0,1.0,1.0,]
            LV:[2861.85,2861.85,2865.52,2865.52,]
            Upper:[2868.54,2869.29,2865.52,2865.52,]
            ATRSLMid:[2864.84,2864.89,2865.36,2864.71,]
```
**Reading:**
- `dir:0` → ATRSL not trailing yet, static stop mode
- `Trend:[2,2,1,1]` → ATRSL itself trending down on recent bars, up on older bars (mixed)
- `LV:2861.85` → static lower stop at 2861.85 (BUY stop level)
- ATRSL is FLAT → no clear directional commitment from stop system

```
[M15] W_stage_M15:[522,522,522](FLY), diffMid_Trend_M15:[2.0,4.0,2.0]
     diffBBW_M15:[-2.96,-1.94,-0.93]
```
**Reading:**
- Stage 522 all 3 bars = parallel down (all bands falling)
- Midtrend [2,4,2] = downtrend, side-dn, downtrend = **bearish M5**
- diffBBW negative = BB is contracting (narrowing) = losing momentum
- **M5 is bearish but weakening — fly losing strength**

```
[M15] W_stage_M15:[423,513,513](SQZ), diffMid_Trend_M15:[3.0,5.0,5.0]
```
**Reading:**
- Stage sequence [423→513→513]: M15 was in SQZ (423) and is transitioning to shrink (513)
- diffMidtrend [3,5,5] = flat, side-up, side-up = **M15 trying to turn bullish but not confirmed**
- SQZ deepening (423 > 423 in prev session) = compression building

```
[M30] W_stage_M30:[512,512,512](FLY), diffMid_Trend_M30:[1.0,1.0,1.0]
```
**Reading:**
- Stage 512 = parallel up (all bands rising)
- Midtrend all 1 = **M30 clearly bullish** — this is the macro supporting direction for the open BUY

```
[H1] first_stage_H1:[true], W_stage_H1:()[0,0,0], diffMid_Trend_H1:[3.0,3.0,3.0]
```
**Reading:**
- `first_stage_H1:true` = H1 not yet initialized — insufficient bars
- Stage 0, midtrend 3 = **H1 undefined/neutral**
- Cannot use H1 as macro filter yet

```
[TRADEINFO] L2H_sideway:1, H2L_flyUP:-1, H2L_flyDN:-1, L2H_flyUP:-1, L2H_flyDN:-1
```
**Reading:**
- Only `L2H_sideway:1` fired = sideway chain detected bottom-up
- All fly signals = -1 (no consecutive fly chain in either direction)
- **No valid fly entry — EA correctly not opening new orders**

```
[AllTF] HTF_Drive_LTF_Sideway:[M5_1, M15_1]
        LTF_Drive_HTF_Fly:[M15_1, H1_1]
```
**Reading:**
- `HTF_Drive_LTF_Sideway_M5=1, M15=1` → Higher TFs are suppressing M5 and M15 into sideways
- `LTF_Drive_HTF_Fly_M15=1, H1=1` → M15 and H1 showing fly energy (LTF pushing back)
- **Conflict state: HTF suppressing LTF but LTF trying to break out**
- This maps to `sizeMultiplier = 0.5` in the sizing logic

**Overall diagnosis:**
> Market is in a **compression/indecision phase**. M30 is bullish (512) but M5 is bearish (522) and M15 is squeezing (423→513). The open BUY was entered prematurely before SQZ resolved. Hold with tight stop at ATRSL LV=2861.85. Wait for M15 SQZ to break upward before adding. Exit if price closes below 2861.85.

---

## Example 2: Normal Fly State (High Conviction)

```
[M5]  W_stage_M5:(FLY)[511,511,512], diffMid_Trend_M5:[1.0,1.0,1.0]
      diffBBW_M5:[+2.14,+3.21,+1.98]
[M15] W_stage_M15:[511,511,511](FLY), diffMid_Trend_M15:[1.0,1.0,1.0]
[M30] W_stage_M30:[512,512,511](FLY), diffMid_Trend_M30:[1.0,1.0,1.0]
[H1]  W_stage_H1:[511,511,512](FLY), diffMid_Trend_H1:[1.0,1.0,1.0]
[ATRSL1buf] dir:1
[TRADEINFO] L2H_flyUP:3, H2L_flyUP:0
```
**Reading:**
- All TFs 511/512 midtrend=1 = **full bullish alignment**
- diffBBW positive = BB expanding = fly has momentum
- ATRSL dir=1 = trailing stop moving up = confirms long trend
- `L2H_flyUP:3` = fly chain detected from M5(0) through H1(3) bottom-up
- `H2L_flyUP:0` = fly chain from H1 down to M5

**Trade decision:** BUY 1.0× quality=High. SL = ATRSL LV[0]. Enter on M5 bar close.

---

## Example 3: Double Shrink with M5 Transition

```
[M5]  W_stage_M5:(FLY)[522,522,512], diffMid_Trend_M5:[1.0,2.0,2.0]
      ← cur=1, prev=2 → DN→UP reversal transition!
[M15] W_stage_M15:(FLY)[513,513,522], diffMid_Trend_M15:[1.0,2.0,2.0]
      ← M15 shrinking (513), midtrend was 2 now 1 (turning up)
[M30] W_stage_M30:(FLY)[513,513,513], diffMid_Trend_M30:[1.0,1.0,2.0]
      ← M30 shrinking (513), midtrend turning up
[H1]  W_stage_H1:(FLY)[511,511,512], diffMid_Trend_H1:[1.0,1.0,1.0]
[ATRSL1buf] dir:1
```
**Reading:**
- H1 still flying up ✓
- M30 shrinking (513) but midtrend turning to 1 (bullish) ← positive sign
- M15 shrinking (513) but midtrend turning to 1 ← double shrink with bullish lean
- M5 midtrend: cur=1, prev=2 → **DN→UP direct reversal, quality=60**
- ATRSL dir=1 (trailing up) → confirms long bias

**Shrink depth:** M30+M15 both shrink = 2 TFs → penalty × 0.5
**M5 quality:** 60 → base size 0.5× → final: 0.5 × 0.5 = **0.25×**
**Trade decision:** BUY 0.25× (low size, double shrink). SL = ATRSL LV[0].

---

## Example 4: SQZ Breakout Detection

```
[M5]  W_stage_M5:(FLY)[511,400,400], diffMid_Trend_M5:[1.0,3.0,3.0]
      ← M5 just broke from SQZ(400) to fly(511), midtrend flipped 3→1
[M15] W_stage_M15:(FLY)[511,400,400], diffMid_Trend_M15:[1.0,3.0,3.0]
      ← M15 also broke from SQZ, midtrend 3→1 = FLAT→UP transition!
[M30] W_stage_M30:(FLY)[511,400,400], diffMid_Trend_M30:[1.0,3.0,3.0]
      ← M30 also broke from SQZ = full breakout
[H1]  W_stage_H1:()[400,400,400], diffMid_Trend_H1:[3.0,3.0,3.0]
      ← H1 still in SQZ
[ATRSL1buf] dir:0→1 (just flipped)
```
**Reading:**
- M30+M15+M5 all broke from SQZ upward simultaneously
- ATRSL just flipped from dir=0 to dir=1 (breakout confirmed by stop system)
- H1 still in SQZ — this is a M30+M15 pioneer breakout
- M15 midtrend: prev=3, cur=1 = **FLAT→UP transition, quality=70**

**Trade decision:** BUY 1.0× quality=High (M30+M15 both confirmed).
SL = ATRSL LV at the breakout bar (not current bar).

---

## TRADEINFO Flag Decoder

```
H2L_flyUP_TF  ≥ 0  →  HTF fly-up chain detected starting from TF index
H2L_flyDN_TF  ≥ 0  →  HTF fly-down chain detected
H2L_flyStrink_TF ≥ 0 → HTF shrink chain detected
H2L_sideway_TF ≥ 0 → HTF sideway/SQZ chain detected
L2H_flyUP_TF  ≥ 0  →  LTF fly-up chain detected (bottom-up)
L2H_flyDN_TF  ≥ 0  →  LTF fly-down chain detected
L2H_flyStrink_TF ≥ 0 → LTF shrink chain
L2H_sideway_TF ≥ 0 → LTF sideway chain

All = -1  →  no chains detected, market in mixed/neutral state

Trade_act:
  0 → NEUTRAL / no trade
  1 → BUY signal
  2 → SELL signal
```

---

## AllTF Flag Decoder

```
HTF_Drive_LTF_Sideway:[M5_1, M15_1]
  → M5 and M15 both being pushed into sideways by higher TFs
  → sizeMultiplier = 0.25 in Trade_Strategy

LTF_Drive_HTF_Fly:[M15_1, H1_1]
  → M15 and H1 showing fly momentum (LTF driving)
  → sizeMultiplier restores to 1.0

line_seq_touch:[M5_17-6,9, M15_0-9,0 ...]
  → Price touch sequence count on BB lines per TF

Midline_cross:[M5_20-20, M15_20-20 ...]
  → Count of midline crossings (20=moderate activity)
```

---

## BBW_stage Progression Patterns

```
Normal bull run:      400 → 512 → 511 → 513 → 400 → 512 ...
                      SQZ   fly    fly   shrink  SQZ   fly

Healthy trend:        511 → 511 → 511 → 513 → 511
                      hold  hold  hold  pause  resume

Reversal pattern:     511 → 513 → 400 → 521 → 522
                      up    shrink SQZ  turn  down

Bear trend:           522 → 522 → 522 → 523 → 400 → 512
                      dn    dn    dn    shrink SQZ   reversal
```

**Key pattern to watch:** 513/523 → 400 → direction change
This is the classic shrink-to-SQZ-to-reversal sequence. If you see M30 go 513→400, prepare for a potential direction change in the next 3-10 bars.

---

## Example 5: M5 Shrink + M15 Fly — Previously NEUTRAL, Now SELL
**Source: 2026.01.07 09:15:00 (real EA log)**

```
[ORDERINFO] SELL_PROFIT:6.22, SELL_LOTS:0.01, SELL_TICKET_NUM:2, SELLS:1
```
**Reading:** One open SELL, currently up $6.22.

```
[ATRSL1buf] dir:0
            Trend:[2.0,2.0,2.0,2.0,2.0,2.0,]
            LV:[4441.29,4440.09,4439.78,...]
            Upper:[4453.97,4453.97,4453.97,...]
            Lower:[4441.29,4440.09,4439.78,...]
            SLMid:[4450.56,4449.85,4448.25,...]
            Val:[4.64,4.83,4.89,...]
```
**Reading:**
- `dir:0` → ATRSL static, not yet trailing
- `Trend:[2,2,2,...]` → ATRTrend consistently bearish
- `Lower:[4441.29,...]` → ATRSLLower = BUY stop level
- `Upper:[4453.97,...]` → ATRSLUpper = SELL stop level (current SELL SL)
- Gate 1 skipped: M5 stage=523 (shrink) → ATRSL dir=0 never blocks anyway

```
[M5]  W_stage_M5:(FLY)[523,523,523]  diffMid_Trend_M5:[4.0,2.0,2.0]
      diffBBW_M5:[-0.54,-4.53,-10.62]
```
**Reading:**
- Stage 523 all 3 bars = bearish shrink (Upper↑ Lower↓ Mid↓)
- Midtrend [4,2,2] = side-dn, down, down → **M5 bearish** but contracting
- diffBBW negative and increasing = BB actively narrowing
- **M5 is in bearish shrink** → triggers shrink path (was missing before fix)

```
[M15] W_stage_M15:(FLY)[521,521,521]  diffMid_Trend_M15:[2.0,2.0,2.0]
      diffBBW_M15:[3.02,9.85,9.46]
```
**Reading:**
- Stage 521 = FLY++ mid downtrend (all 3 bars)
- Midtrend all 2 = **M15 clearly bearish and expanding**
- diffBBW positive = M15 BB expanding = healthy fly momentum
- M15 provides the direction: SELL

```
[TRADEINFO] |NEUTRAL  H2L[UP:-1 DN:-1 Shrk:-1 Side:3]  L2H[UP:-1 DN:-1]
```
**Reading (OLD — before fix):**
- L2H chain starts at M5 (index 0): M5 stage=523 ≠ 521/522 → chain never starts
- L2H_flyDN stays -1 → no fly decision cases fire
- Shrink detection missed M5 → NEUTRAL incorrectly

**Reading (AFTER FIX):**
- M5 stage=523 → `M5_shrink=true` → enters shrink path
- GetShrinkDecision: shrinkCount=0 (H1/M30/M15 not shrinking), M5 shrink only
- depthPenalty = 0.90 (M5-only, lightest)
- M15_mid=2, M30_mid check → no M15/M30 conflict
- M5 midtrend cur=4 (side-dn), prev=2 → no FLAT→DN transition yet
  → If prev bar had mid=3: would fire FLAT→DN quality=70
  → With cur=4: fires FLAT→SIDEDN, quality=45 (early signal)
- M15 in SQZ? No (M15=521 fly) → early signal suppressed → WAIT

**Corrected diagnosis:**
> M5 is in bearish shrink (523) while M15 is flying down (521). No M5 midtrend
> transition has fired yet (cur=4, not FLAT→1/2). Correct action is WAIT until
> M5 midtrend shows FLAT→2 or direct DN→2. The open SELL from earlier is still
> valid — hold with SL at ATRSLUpper[LA]=4453.97.

```
[BBTFImpact] HTF_Drive_LTF_Sideway:[M30_1]  LTF_Drive_HTF_Fly:[M30_1,H1_1]
```
**Reading:**
- `BB_HTF_Drive_LTF_Sideway[2]=1` → M30 (index 2) being pushed into sideway
- `BB_LTF_Drive_HTF_Fly[2]=1, [3]=1` → M30 and H1 showing fly energy
- sizeMulti: M5 [0] and M15 [1] not suppressed → sizeMulti=1.0 (full)
- Conflict state: M30 sideways but M30+H1 also have fly energy
  → Volatile transition period, wait for M5 to confirm direction

---

## BBTFImpact Array Index Reference

```
Index  TF    BB_HTF_Drive_LTF_Sideway[n]         BB_LTF_Drive_HTF_Fly[n]
─────  ────  ────────────────────────────────     ──────────────────────────
1      M15   M15 being suppressed into sideway    M15 driving HTF into fly
2      M30   M30 being suppressed into sideway    M30 driving HTF into fly
3      H1    H1 being suppressed into sideway     H1 driving HTF into fly
4      H4    H4 being suppressed                  H4 driving
5      D1    D1 being suppressed                  D1 driving
```

**Log decode: `HTF_Drive_LTF_Sideway:[M30_1]`**
```
M30_1 → BB_HTF_Drive_LTF_Sideway[2] = 1
         (M30 is index 2, value 1 = active)
```

**Log decode: `LTF_Drive_HTF_Fly:[M30_1, H1_1]`**
```
M30_1 → BB_LTF_Drive_HTF_Fly[2] = 1
H1_1  → BB_LTF_Drive_HTF_Fly[3] = 1
```

---

## Example 6: Cascade Band Touch — SELL (upper band)

```
[M15] W_stage_M15:(SQZ)[432,423,400] diffMid_Trend_M15:[3.0,3.0,3.0] BBUpDn_M15:[1,0,0]
[M30] W_stage_M30:(FLY)[523,523,523] diffMid_Trend_M30:[2.0,2.0,2.0] BBUpDn_M30:[1,0,0]
[H1]  W_stage_H1:(FLY)[513,513,512]  diffMid_Trend_H1:[2.0,2.0,2.0]  BBUpDn_H1:[1,0,0]
```
**Reading:**
- H1=513 (shrink) mid=2 → `cas_shrinkTF=3` (H1 is highest shrink TF)
- M30=523 (shrink) → contributes to shrinkTF scan but H1 wins
- M15=SQZ (432→400) → `cas_sqzCount` includes M15
- M5=521→513 → M5 not in SQZ, contributes to count
- H1 BBUpDn=1 (upper band touch) → **SELL signal**
- M15+M30 both SQZ? M30=523 (NOT SQZ) → pink zone NOT triggered

**Log output:**
```
[TRADEINFO] |CASCADE_TOUCH(TF:3 upper_band(BBUpDn=1) sqzBelow:1) dir:2 act:4 lots:0.01 sl:4453.97 |ATRSL:0
```

---

## Example 7: Cascade Pink Zone — NO TRADE

```
[M15] W_stage_M15:(SQZ)[432,423,400] diffMid_Trend_M15:[3.0,3.0,3.0]
[M30] W_stage_M30:(SQZ)[443,432,423] diffMid_Trend_M30:[3.0,3.0,3.0]
[H1]  W_stage_H1:(FLY)[513,513,513]  diffMid_Trend_H1:[2.0,2.0,2.0]
```
**Reading:**
- H1=513 (shrink) → `cas_shrinkTF=3`
- M30=SQZ (443) → `cas_M30sqz=true`
- M15=SQZ (432) → `cas_M15sqz=true`
- **Pink zone condition: M15+M30 both SQZ → NO TRADE + return**

**Log output:**
```
[TRADEINFO] |CASCADE_PINK_ZONE(M15+M30_SQZ)→no_trade
```
This is the **pink rectangle** on the chart — fully compressed middle zone.

---

## Example 8: Midline SQZ Loading → Break → SELL

**Bar 1 (loading):**
```
[M15] W_stage_M15:(SQZ)[432,423,400] diffMid_Trend_M15:[4.0,3.0,3.0]
[M30] W_stage_M30:(FLY)[523,523,523] diffMid_Trend_M30:[2.0,2.0,2.0]
```
- M30_shrink=true, M5 in SQZ, M15 sideway
- M15_mid>=3 AND M5 in SQZ → `MIDLINE_SQZ_LOADING` logged
- No entry yet — M5 still in SQZ

**Log Bar 1:**
```
[TRADEINFO] |SHRINK_DEPTH:1 penalty:0.75 +M5_shrink |MIDLINE_SQZ_LOADING(SELL_setup→wait_M5_break)
            [M5_trans cur:3 prev:3 prev2:3 M15_stg:432 M15_mid:4] |NO_TRANS(stable:3) |NEUTRAL
```

**Bar 2 (M5 SQZ breaks bearish):**
```
[M5]  W_stage_M5:(FLY)[521,423,400]  diffMid_Trend_M5:[2.0,3.0,3.0]
      BBW_stage prev bar was 423 (SQZ), now 521 (fly bearish)
```
- M5_was_sqz=true (prev=423), M5_stg_now=521 → `SQZ_BREAK_DN`
- quality=75 → sizeMulti=0.75 × depthPenalty=0.75 = 0.56×

**Log Bar 2:**
```
[TRADEINFO] |SHRINK_DEPTH:1 penalty:0.75 [M5_trans cur:2 prev:3 M15_stg:432 M15_mid:4]
            |SQZ_BREAK_DN(midline_continuation) |quality:75 size:0.75 |MIDLINE_SQZ_ENTRY
            dir:2 act:4 lots:0.01 sl:4453.97
```

---

## Cascade State Decoder

```
cas_shrinkTF value  Meaning
──────────────────  ─────────────────────────────────────────────
3                   H1 is the highest active fly_shrink TF
2                   M30 is highest (H1 already in SQZ or flat)
1                   M15 is highest (M30+H1 in SQZ or flat)
-1                  No TF in fly_shrink — cascade not active

cas_sqzCount value  Meaning
──────────────────  ─────────────────────────────────────────────
0                   No TFs in SQZ yet — too early for cascade
1                   One TF squeezed (typically M5 first)
2                   Two TFs squeezed (M5+M15 or similar)
3+                  Deep cascade — multiple TFs compressed
```

**M15+M30 pink zone vs normal sideway:**
```
Gate 0 (M30_mid>=3 AND M15_mid>=3): fires when MIDTREND is sideways
Cascade pink zone (M15_sqz AND M30_sqz): fires when STAGE is SQZ (400-499)
These are different conditions — both may fire together, or independently.
```
