# Log Examples Reference

## Annotated EA Log Samples — How to Decode Each Line

---

## Log Line Format Reference

Each EA log line in the Journal tab:

```
YYYY.MM.DD HH:MM:SS  [TAG] field:value, field:value, ...
```

No EA-name or timestamp prefix in the Journal tab output — just date/time + tag block.

**Tag emit order per tick:**

```
[M15] → [M30] → [H1] → [H4] → [TRADEINFO] → [BBTFImpact] → [ATRSL1buf] → [ORDERINFO]
```

> **Float precision note:** The EA emits raw MQL5 doubles. Some values will appear as
> e.g. `1.6099999999999999` or `3.7199999999999998` — this is normal IEEE 754 output,
> not a bug. Do not round these when comparing logs.

---

## Tag Field Reference

```
[M15] / [M30] / [H1] / [H4]
  W_stage_TF:(REGIME)[cur, prev, prev2]        → BBW stage + regime label
  diffMid_Trend_TF:[cur, prev, prev2]           → midline trend  1=up 2=dn 3=flat 4=side-dn 5=side-up
  BBUpDn_TF:[cur, prev, prev2]                  → band movement state (2-bar confirmed):
                                                   0=neutral/mixed (no clean confirmation)
                                                   1=expanding  Upper↑ AND Lower↓ for 2 bars
                                                   2=shrinking  Upper↓ AND Lower↑ for 2 bars
                                                   3=up         Upper↑ AND Lower↑ for 2 bars (parallel up)
                                                   4=dn         Upper↓ AND Lower↓ for 2 bars (parallel down)
  trend_TF:[cur, prev, prev2, ]                 → BB midline trend enum per bar (trailing comma)
                                                   0=no_trend  1=up  2=dn  3=sideway
                                                   4=sideway_dn  5=sideway_up
                                                   7=rev_up (REVUP on chart)  8=rev_dn (REVDN on chart)
  prev_trend_TF:N                               → trend enum of the bar before cur (same enum as above)
  diffMid_TF:[cur, prev, prev2]                 → midline delta: [n] = MidLV[n] - MidLV[n+1]
                                                   each step = one TF bar apart (EA runs on M5, HTF sampled at M5 resolution)
  diffBBW_TF:[cur, prev, prev2]                 → BB-width delta: [n] = (WLV[n] - WLV[n+1]) * 100
                                                   positive = expanding, negative = contracting
                                                   scaled ×100; uses full-precision internal BBWLV not printed WLV
                                                   step size varies by TF: M15=15min, M30=30min, H1=1hr, H4=4hr
  WLV_TF:[cur, prev, prev2]                     → BB width level; prev = one TF bar ago
                                                   M5=5min, M15=15min, M30=30min, H1=1hr, H4=4hr between samples
  MidLV_TF:[cur, prev, prev2]                   → midline price (sampled at M5 resolution)
                                                   prev = one TF bar ago: M15=15min, M30=30min, H1=1hr, H4=4hr
  UppLV_TF:[cur, prev, prev2]                   → upper band price (same sampling as MidLV)
  LowLV_TF:[cur, prev, prev2]                   → lower band price (same sampling as MidLV)
  close_TF / high_TF / low_TF                   → OHLC (M15 only; omitted on M30/H1/H4)

[TRADEINFO]
  Gate:[Gx-LABEL] TradeAct:N cnt:N pen:N.NN| Gate:[Gy-LABEL] ...flags...|act:N atrsl:N

[BBTFImpact]
  Sideway_val:[NNNNN-...]                        → 5-digit concatenation of per-TF sideway scores [H4][H1][M30][M15][M5]
                                                   each digit 0–6:  +4 if diffMid_Trend>=3 (flat/side)
                                                                    +2 if stage<500 (SQZ/SW/STR)
                                                                    +1 if stage==513 or 523 (shrink)
                                                                     0 if clean fly (stage>=500, not 513/523)
                                                   [NNNNN]        = sideway not confirmed
                                                   [NNNNN-S_XX]   = sideway CONFIRMED (combined detection triggered)
  HTF_Drive_LTF_Sideway:[TF_N, ...]
  LTF_Drive_HTF_Fly:[TF_N, ...]
  midline_Cluster:[N, N, N]                      → midline price spread vs M15: [|M15-M5|, |M15-M30|, |M15-H1|]
  line_seq_touch:[TF_cur-recent,prev, ...]       → touch sequence per TF [cur state - recent touch, prev touch]
                                                   ENUM_BB_LineTouch: 0=none 6=dnup_Dn 7=updn_Mid
                                                   8=dnup_Mid 9=updn_Up 16=untouch_dnup_Dn
                                                   17=untouch_updn_Mid 18=untouch_dnup_Mid 19=untouch_updn_Up
  line_seq_cross:[TF_cur-recent,prev, ...]       → cross sequence per TF [cur state - recent cross, prev cross]
                                                   ENUM_BB_LineCross: 0=none 10=BB_LOW 15=CrossUp_LOW
                                                   16=CrossDn_LOW 20=BB_DN 26=CrossDn_DN 30=BB_UP
                                                   35=CrossUp_UP 40=BB_HIGH 45=CrossUp_HIGH 46=CrossDn_HIGH
  untouch_val:[TF_N-N, ...]                      → bars since last band touch
  Midline_cross:[TF_cur-prev, ...]               → midline cross per TF [cur bar state - prev bar state]
                                                   same ENUM_BB_LineCross values as line_seq_cross

[ATRSL1buf]
  dir:N                                         → 0=uptrend (LV=Lower, stop below price)
                                                   1=downtrend (LV=Upper, stop above price)
  Trend:[cur,prev,prev2,prev3,prev4,prev5,]     → buffer direction per bar [cur→prev5] (trailing comma)
                                                   2=uptrend  1=downtrend
  LV:[cur,prev,prev2,prev3,prev4,prev5,]        → active buffer value = Lower when dir:0, Upper when dir:1
  Upper:[cur,prev,prev2,prev3,prev4,prev5,]     → upper band of ATR channel (SELL stop reference)
  Lower:[cur,prev,prev2,prev3,prev4,prev5,]     → lower band of ATR channel (BUY stop reference)
  SLMid:[cur,prev,prev2,prev3,prev4,prev5,]     → midpoint of ATR channel
  Val:[cur,prev,prev2,prev3,prev4,prev5,]       → raw ATR value per bar (trailing comma)

[ORDERINFO]
  BUY_PROFIT:N, BUY_LOTS:N, BUY_TICKET_NUM:N, BUYS:N,
  SELL_PROFIT:N, SELL_LOTS:N, SELL_TICKET_NUM:N, SELLS:N, TOTALORDERS:N
```

---

## BBW Stage Code Reference

Stage codes are 3-digit: each digit encodes Upper/Lower/Mid band direction.
The chart label is derived from `BBW_stage` + `BB_diffBBW[LA]` at the current bar.

```
Stage   Chart Label   Condition                        Meaning
──────  ────────────  ───────────────────────────────  ──────────────────────────────────────
511     fly++         stage=511 (default ≥500)         All bands rising — strong bull fly
512     fly+-         stage=512 AND diffBBW > 0        Parallel up, BB expanding
512     fly-+         stage=512 AND diffBBW < 0        Parallel up, BB contracting
512     fly++         stage=512 AND diffBBW = 0        Parallel up, width unchanged
513     fly--         stage=513                        Shrink-up (bands converging, mid rising)
521     fly++         stage=521 (default ≥500)         All bands falling — strong bear fly
522     fly+-         stage=522 AND diffBBW > 0        Parallel down, BB expanding
522     fly-+         stage=522 AND diffBBW < 0        Parallel down, BB contracting
522     fly++         stage=522 AND diffBBW = 0        Parallel down, width unchanged
523     fly--         stage=523                        Shrink-dn (bands converging, mid falling)
400–499 SQZ           stage 400–499                   Squeeze — bands compressed
400–499 SQZ-@@@       stage 400–499 AND               Deep/confirmed squeeze
                      BBW_updated_stage >= 1000
300–399 SW            stage 300–399                   Sideways
200–299 STR           stage 200–299                   Strong trend
```

**Mid-band chart labels** (drawn at midline, separate from stage label):

```
diffMid_Trend >= 3   → prints the numeric value (3=flat, 4=side-dn, 5=side-up)
trend == 7           → REVUP  (reversal upward detected)
trend == 8           → REVDN  (reversal downward detected)
```

**Note:** The `(REGIME)` string in `W_stage_TF:(REGIME)[...]` in the log prints only `FLY` or `SQZ`.
The full `fly++/fly+-/fly-+/fly--` label is the chart annotation only, derived at draw time from
`BBW_stage` + `diffBBW[LA]` as shown above.

**BBW Stage Progression Patterns:**

```
Normal bull run:   400 → 512 → 511 → 513 → 400 → 512
                   SQZ   fly    fly  shrink  SQZ   fly

Healthy trend:     511 → 511 → 511 → 513 → 511
                   hold  hold  hold  pause  resume

Reversal pattern:  511 → 513 → 400 → 521 → 522
                   up   shrink  SQZ  turn   down

Bear trend:        522 → 522 → 522 → 523 → 400 → 512
                   dn    dn    dn   shrink  SQZ  reversal
```

Key: `513/523 → 400` = shrink-to-SQZ. When M30 hits this, watch for direction change in next 3–10 bars.

---

## diffMid_Trend Value Reference

```
1 = Uptrend       mid rising cleanly
2 = Downtrend     mid falling cleanly
3 = Flat          mid stationary
4 = Side-down     mid drifting lower
5 = Side-up       mid drifting higher
```

---

## BBUpDn Value Reference

`BBUpDn_TF` reflects `BBUpDn_state` — band movement confirmed over 2 consecutive bars.
Both current and previous bar must show the same pattern before a state fires; otherwise `0`.

```
Value  Meaning
─────  ──────────────────────────────────────────────────────────────────
0      Neutral / mixed  — no clean 2-bar confirmation
1      Expanding        — Upper↑ AND Lower↓ on bar[cur] and bar[prev]
2      Shrinking        — Upper↓ AND Lower↑ on bar[cur] and bar[prev]
3      Up               — Upper↑ AND Lower↑ on bar[cur] and bar[prev] (parallel up)
4      Down             — Upper↓ AND Lower↓ on bar[cur] and bar[prev] (parallel down)
```

---

## TRADEINFO Gate Reference

```
Gate       Meaning
─────────  ─────────────────────────────────────────────────────
G0         Initial regime filter (M5 check)
G1         ATRSL direction gate
G2         HTF anchor (D1+H4 agreement)
G3-CHAIN   Minimum TF chain length — cnt = number of TFs aligned
G4a        M30/H1 alignment (same direction)
G4b-H1OPP H1 opposing direction block
G5         SQZ block (no entry during squeeze)
G6-SHRINK  Shrink path gate — pen = size penalty (0.75–1.0)
G7         Final entry confirmation

TradeAct:  0=NEUTRAL  1=BUY  2=SELL
act:       0=no action  4=open trade
atrsl:     0=ATRSL not used as SL  1=ATRSL used as SL
```

**TRADEINFO pipe format:**

```
Gate:[Gx-LABEL] TradeAct:N cnt:N pen:N.NN| Gate:[Gy-LABEL] flag:N|act:N atrsl:N
│                            │       │       │                        │
│                            │       │       └─ subsequent gate check └─ final action
│                            │       └─ penalty multiplier (1.0=none)
│                            └─ TF chain count
└─ primary gate fired
```

---

## BBTFImpact Field Reference

```
Field                       Meaning
──────────────────────────  ──────────────────────────────────────────────────
Sideway_val:[NNNNN-...]     5-digit string [H4][H1][M30][M15][M5], each digit 0–6
                            +4 = diffMid_Trend>=3 (flat/side-dn/side-up)
                            +2 = stage<500 (SQZ/SW/STR)
                            +1 = stage==513 or 523 (shrink)
                             0 = clean fly
                            higher digits = more sideways/compressed on that TF
                            Format:
                              [NNNNN]        → sideway not confirmed
                              [NNNNN-S_XX]   → sideway CONFIRMED (combined Sideway_val
                                               + midline_Cluster detection triggered)
HTF_Drive_LTF_Sideway       HTFs suppressing LTFs into sideways compression
                            TF_1 = that TF is actively suppressed; [] = none
LTF_Drive_HTF_Fly           LTFs showing fly energy driving HTFs
                            Both active simultaneously = conflict/volatile state
midline_Cluster             Price spread between M15 midline and other TF midlines:
                            [0] = |M15mid - M5mid|
                            [1] = |M15mid - M30mid|
                            [2] = |M15mid - H1mid|
                            larger value = greater TF divergence from M15
line_seq_touch              Touch sequence per TF: [TF_cur-recent,prev]
                            cur    = current touch state
                            recent = most recent completed touch event
                            prev   = previous completed touch event
                            Values (ENUM_BB_LineTouch):
                              0  = touch_none
                              6  = touch_dnup_BBDn    crossed dn→up at lower band
                              7  = touch_updn_BBMid   crossed up→dn at mid band
                              8  = touch_dnup_BBMid   crossed dn→up at mid band
                              9  = touch_updn_BBUp    crossed up→dn at upper band
                              16 = untouch_dnup_BBDn  nearly dn→up at lower band
                              17 = untouch_updn_BBMid nearly up→dn at mid band
                              18 = untouch_dnup_BBMid nearly dn→up at mid band
                              19 = untouch_updn_BBUp  nearly up→dn at upper band
line_seq_cross              Cross sequence per TF: [TF_cur-recent,prev]
                            cur    = current cross state
                            recent = most recent completed cross event
                            prev   = previous completed cross event
                            Values (ENUM_BB_LineCross):
                              0  = none
                              10 = BB_LOW          price at lower band
                              15 = CrossUp_BB_LOW  crossed up through lower band
                              16 = CrossDn_BB_LOW  crossed down through lower band
                              20 = BB_DN           price below lower band
                              26 = CrossDn_BB_DN   crossed down below lower band
                              30 = BB_UP           price at upper band
                              35 = CrossUp_BB_UP   crossed up through upper band
                              40 = BB_HIGH         price above upper band
                              45 = CrossUp_BB_HIGH crossed up above upper band
                              46 = CrossDn_BB_HIGH crossed down from above upper band
untouch_val                 [TF_upper-lower] bars since last touch
Midline_cross               Midline cross state per TF: [TF_cur-prev]
                            cur  = current bar midline cross state
                            prev = previous bar midline cross state
                            Same ENUM_BB_LineCross values as line_seq_cross
```

**Sideway detection combines both Sideway_val and midline_Cluster:**

```
Sideway_val    → momentum dimension: are TF stages/trends losing direction?
midline_Cluster → spatial dimension: are TF midlines converging in price?

True sideway zone = BOTH conditions met:
  Sideway_val digits high  (stages in SQZ/shrink, diffMid_Trend flat/side)
  midline_Cluster low      (M5/M30/H1 midlines physically close to M15 midline)

On chart: BB midlines visually stack and cluster together in the sideways zone.
In a trending market: Sideway_val digits near 0, midline_Cluster values large
  (TF midlines spread apart as each TF trends at its own pace).
```

**TF index mapping (BBTFImpact):**

```
M5=0  M15=1  M30=2  H1=3  H4=4  D1=5  W1=6
```

**Size multiplier from BBTFImpact:**

```
HTF_Drive_LTF_Sideway on M5+M15       → sizeMultiplier = 0.25
HTF_Drive_LTF_Sideway on M5 only      → sizeMultiplier = 0.50
LTF_Drive_HTF_Fly active, no suppress → sizeMultiplier = 1.00
Both active at same time              → volatile transition, hold
```

---

## ATRSL1buf Field Reference

```
Field   Meaning
──────  ──────────────────────────────────────────────────────────
dir     0 = uptrend   → LV = Lower band (stop below price, BUY mode)
        1 = downtrend → LV = Upper band (stop above price, SELL mode)
Trend   [cur,prev,prev2,prev3,prev4,prev5,]  buffer direction per bar
        2=uptrend  1=downtrend
LV      [cur,prev,prev2,prev3,prev4,prev5,]  active buffer value
        equals Lower[n] when dir=0, Upper[n] when dir=1
Upper   [cur,prev,prev2,prev3,prev4,prev5,]  top orange band — SELL stop reference
Lower   [cur,prev,prev2,prev3,prev4,prev5,]  bottom orange band — BUY stop reference
SLMid   [cur,prev,prev2,prev3,prev4,prev5,]  midpoint of ATR channel (yellow line)
Val     [cur,prev,prev2,prev3,prev4,prev5,]  raw ATR value per bar
```

**Stop selection:**

```
dir:0 (uptrend)   → SL for open BUY  = LV[cur] = Lower[cur]
dir:1 (downtrend) → SL for open SELL = LV[cur] = Upper[cur]

Trend history examples:
  [2,2,2,2,1,1,] → uptrend now (2), flipped from downtrend (1) at prev3
  [1,1,1,1,2,2,] → downtrend now (1), flipped from uptrend (2) at prev3
```

---

## Example 1: Multi-TF Compression — No Trade

**Source: 2026.02.19 04:00**

```
2026.02.19 04:00:02   [M15], W_stage_M15:(FLY)[522, 522, 522], diffMid_Trend_M15:[4.0, 2.0, 2.0],
  BBUpDn_M15:[4, 4, 0], trend_M15:[2, 2, 2, ], prev_trend_M15:2,
  diffMid_M15:[-0.34, -0.55, -0.73], diffBBW_M15:[-0.82, -0.66, 3.29],
  WLV_M15:[0.56, 0.57, 0.58],
  MidLV_M15:[4974.42, 4974.76, 4975.21], UppLV_M15:[4988.28, 4988.82, 4989.53],
  LowLV_M15:[4960.56, 4960.69, 4960.88],
  close_M15:[4973.23, 4973.32, 4973.97], high_M15:[4973.23, 4975.7, 4975.33],
  low_M15:[4973.23, 4972.62, 4970.78],

2026.02.19 04:00:03   [M30], W_stage_M30:(SQZ)[412, 412, 513], diffMid_Trend_M30:[2.0, 2.0, 3.0],
  BBUpDn_M30:[0, 0, 2], trend_M30:[2, 8, 1, ], prev_trend_M30:2,
  diffMid_M30:[-1.35, -0.54, 0.18], diffBBW_M30:[-2.84, 5.3, -2.93],
  WLV_M30:[0.94, 0.97, 0.95],
  MidLV_M30:[4983.0, 4984.35, 4984.65], UppLV_M30:[5006.52, 5008.58, 5008.25],
  LowLV_M30:[4959.48, 4960.11, 4961.05],

2026.02.19 04:00:04   [H1], W_stage_H1:(FLY)[512, 512, 512], diffMid_Trend_H1:[1.0, 1.0, 1.0],
  BBUpDn_H1:[3, 3, 0], trend_H1:[1, 1, 1, ], prev_trend_H1:1,
  diffMid_H1:[1.92, 1.6099999999999999, 3.14], diffBBW_H1:[-3.15, -5.4, -9.28],
  WLV_H1:[2.38, 2.42, 2.46],
  MidLV_H1:[4961.0, 4959.08, 4957.13], UppLV_H1:[5020.14, 5018.98, 5018.21],
  LowLV_H1:[4901.85, 4899.18, 4896.05],

2026.02.19 04:00:05   [H4], W_stage_H4:(FLY)[523, 521, 521], diffMid_Trend_H4:[2.0, 5.0, 4.0],
  BBUpDn_H4:[2, 0, 0], trend_H4:[2, 2, 2, ], prev_trend_H4:2,
  diffMid_H4:[-2.87, -1.21, 1.63], diffBBW_H4:[-23.71, -6.23, 7.14],
  WLV_H4:[3.7199999999999998, 3.96, 4.02],
  MidLV_H4:[4951.58, 4954.45, 4955.69], UppLV_H4:[5043.76, 5052.56, 5055.38],
  LowLV_H4:[4859.41, 4856.35, 4855.99],

2026.02.19 04:00:05   [TRADEINFO] Gate:[G6-SHRINK] TradeAct:0 cnt:1 pen:0.75|
  Gate:[G4b-H1OPP] M30dn+H1up:1|act:0 atrsl:0

2026.02.19 04:00:05   [BBTFImpact] Sideway_val:[10244-S_31]
  HTF_Drive_LTF_Sideway:[M5_1, M15_1, M30_1, H4_1, D1_1],
  LTF_Drive_HTF_Fly:[M15_1, M30_1, H4_1],
  midline_Cluster:[7.42, 8.58, 13.42],
  line_seq_touch:[M5_9-9,6, M15_0-6,6, M30_0-7,8, H1_0-9,9, H4_0-18,8, D1_0-17,7, W1_0-9,9],
  line_seq_cross:[M5_30-40,30, M15_0-20,10, M30_0-20,30, H1_0-30,40, H4_0-30,20, D1_0-20,30, W1_0-30,40],
  untouch_val:[M5_0-0, M15_0-0, M30_0-0, H1_0-0, H4_0-0, D1_0-0, W1_0-0],
  Midline_cross:[M5_46-40, M15_20-20, M30_20-20, H1_30-30, H4_30-30, D1_20-20, W1_30-30]

2026.02.19 04:00:05   [ATRSL1buf] dir:0,
  Trend:[2.0,2.0,2.0,2.0,1.0,1.0,],
  LV:[4967.04,4967.04,4964.64,4963.2,4970.05,4970.05,],
  Upper:[4978.14,4978.14,4978.14,4978.14,4970.05,4970.05,],
  Lower:[4967.04,4967.04,4964.64,4963.2,4960.42,4959.59,],
  SLMid:[4973.73,4974.13,4973.35,4971.09,4969.54,4967.9,],
  Val:[3.57,3.79,3.79,3.92,4.32,4.45,]

2026.02.19 04:00:05   [ORDERINFO], BUY_PROFIT:0.0, BUY_LOTS:0.0, BUY_TICKET_NUM:0, BUYS:0,
  SELL_PROFIT:0.0, SELL_LOTS:0.0, SELL_TICKET_NUM:0, SELLS:0, TOTALORDERS:0
```

**Reading:**

**[M15]** Stage 522 all 3 bars = bearish fly (all bands falling). `diffMid_Trend=[4,2,2]` = side-dn cur, dn prev bars — bearish but not accelerating. `BBUpDn=[4,4,0]` = parallel-down confirmed (Upper↓ AND Lower↓) on cur and prev bars, neutral at prev2. `diffBBW` going from negative (contracting) to +3.29 = BB re-expanding this bar.

**[M30]** Stage sequence `[412, 412, 513]` = was shrinking (513 two bars ago), now in SQZ (412) for two bars. `diffMid_Trend=[2,2,3]` = dn → dn → flat. `BBUpDn=[0,0,2]` = neutral now (no 2-bar confirmation), was shrinking at prev2. M30 compressing into squeeze with mid flattening.

**[H1]** Stage 512 all 3 bars = bullish fly, `diffMid_Trend=[1,1,1]` = clean uptrend all bars. `BBUpDn=[3,3,0]` = parallel-up confirmed (Upper↑ AND Lower↑) on cur and prev bars, neutral at prev2. `diffBBW` consistently negative = H1 BB width narrowing despite parallel-up movement.

**[H4]** Stage `[523, 521, 521]` = bearish shrink cur bar, bearish fly prior 2 bars. `diffMid_Trend=[2,5,4]` = dn → side-up → side-dn = H4 losing momentum. `BBUpDn=[2,0,0]` = shrinking confirmed only on cur bar (Upper↓ AND Lower↑), neutral prior — shrink just started. `WLV=3.72` (raw double `3.7199999999999998`) = widest BB across TFs.

**[TRADEINFO]** G6-SHRINK fired: H4 cur=523 (bearish shrink), `cnt:1` = one shrink TF, `pen:0.75` = 25% size penalty. But then G4b-H1OPP blocks: `M30dn+H1up:1` = M30 is bearish (mid=2) while H1 is bullish (mid=1) → opposing. `TradeAct:0` = NEUTRAL, `act:0` = no trade.

**[BBTFImpact]** `Sideway_val=10244` decodes as `[H4=1][H1=0][M30=2][M15=4][M5=4]` — H4 shrinking (+1), H1 clean fly (0), M30 in SQZ (+2), M15 flat/side-dn (+4), M5 flat/side (+4). High scores on M15/M5 confirm deep LTF compression. `HTF_Drive_LTF_Sideway` active on M5/M15/M30/H4/D1 = virtually all TFs suppressed. `LTF_Drive_HTF_Fly` on M15/M30/H4 = those TFs still have residual fly energy despite suppression → conflict state, `sizeMultiplier` reduced. `midline_Cluster=[7.42, 8.58, 13.42]` = midlines spread widely across TFs → no price convergence.

**[ATRSL1buf]** `dir:0` = uptrend mode, LV tracking Lower band. `Trend=[2,2,2,2,1,1]` = currently uptrend (2) for 4 bars, prior 2 bars were downtrend (1) — buffer recently flipped to uptrend. `LV[0]=4967.04 = Lower[0]=4967.04` ✓ confirms dir:0. `Upper=4978.14` = SELL stop reference if a short were open.

**[ORDERINFO]** No open positions.

**Overall diagnosis:**
> Deep multi-TF compression. M30 has entered SQZ (412) while H1 is bullishly flying (512) and H4 is starting to shrink (523→). G4b-H1OPP correctly blocks any short entry — H1 direction directly opposes M30. The enormous `Sideway_val` (10244) confirms no tradeable state. Wait for M30 SQZ to resolve AND H1/M30 to align before any entry.

---

## Example 2: Normal Fly State (High Conviction BUY)

```
2026.XX.XX XX:XX:XX   [M15], W_stage_M15:(FLY)[511, 511, 512], diffMid_Trend_M15:[1.0, 1.0, 1.0],
  BBUpDn_M15:[1, 0, 0], trend_M15:[1, 1, 1, ], prev_trend_M15:1,
  diffMid_M15:[0.42, 0.38, 0.51], diffBBW_M15:[2.14, 3.21, 1.98],
  WLV_M15:[0.61, 0.59, 0.57], ...

2026.XX.XX XX:XX:XX   [M30], W_stage_M30:(FLY)[512, 512, 511], diffMid_Trend_M30:[1.0, 1.0, 1.0], ...
2026.XX.XX XX:XX:XX   [H1],  W_stage_H1:(FLY)[511, 511, 512],  diffMid_Trend_H1:[1.0, 1.0, 1.0], ...
2026.XX.XX XX:XX:XX   [H4],  W_stage_H4:(FLY)[511, 511, 511],  diffMid_Trend_H4:[1.0, 1.0, 1.0], ...

2026.XX.XX XX:XX:XX   [TRADEINFO] Gate:[G3-CHAIN] TradeAct:1 cnt:4 pen:1.0|act:4 atrsl:1

2026.XX.XX XX:XX:XX   [ATRSL1buf] dir:1, Trend:[1.0,1.0,1.0,1.0,1.0,1.0,], ...
2026.XX.XX XX:XX:XX   [ORDERINFO], BUY_PROFIT:0.0, ..., TOTALORDERS:0
```

**Reading:**

- All TFs 511/512, `diffMid_Trend=1` everywhere = full bullish alignment.
- `diffBBW` positive on all TFs = BB expanding = fly has momentum.
- `ATRSL1buf dir:1` = trailing stop moving up = stop system confirms long trend.
- G3-CHAIN fires: `cnt:4` = all 4 TFs in aligned chain, `pen:1.0` = no penalty, `TradeAct:1` = BUY, `act:4` = execute, `atrsl:1` = use ATRSL as SL.
- `HTF_Drive_LTF_Sideway:[]` empty = no suppression. Low `Sideway_val` = clean trend.

**Trade decision:** BUY 1.0× (full size, 4-TF chain, no penalty). SL = `ATRSL1buf Lower[0]`.

---

## Example 3: SQZ Breakout — BUY

```
2026.XX.XX XX:XX:XX   [M15], W_stage_M15:(FLY)[511, 400, 400], diffMid_Trend_M15:[1.0, 3.0, 3.0],
  BBUpDn_M15:[0, 3, 0], ...
2026.XX.XX XX:XX:XX   [M30], W_stage_M30:(FLY)[511, 400, 400], diffMid_Trend_M30:[1.0, 3.0, 3.0], ...
2026.XX.XX XX:XX:XX   [H1],  W_stage_H1:(SQZ)[400, 400, 400],  diffMid_Trend_H1:[3.0, 3.0, 3.0], ...
2026.XX.XX XX:XX:XX   [H4],  W_stage_H4:(FLY)[511, 511, 512],  diffMid_Trend_H4:[1.0, 1.0, 1.0], ...

2026.XX.XX XX:XX:XX   [TRADEINFO] Gate:[G3-CHAIN] TradeAct:1 cnt:2 pen:0.90|act:4 atrsl:1
```

**Reading:**

- M15 and M30 both broke from SQZ (400) to bullish fly (511) on current bar. `diffMid_Trend` flipped 3→1 (flat→up).
- H1 still in SQZ (400). H4 confirming bull fly (511, mid=1).
- G3-CHAIN fires: `cnt:2` = M15+M30 confirmed, `pen:0.90` = light penalty (H1 not yet confirming), `TradeAct:1` = BUY, `act:4` = execute.

**Trade decision:** BUY 0.90× (M15+M30 pioneer breakout). SL = `ATRSL1buf Lower[0]` at breakout bar.

---

## Example 4: Bearish Shrink — Blocked by H1 Opposition

```
2026.XX.XX XX:XX:XX   [M15], W_stage_M15:(FLY)[522, 522, 522], diffMid_Trend_M15:[2.0, 2.0, 2.0], ...
2026.XX.XX XX:XX:XX   [M30], W_stage_M30:(FLY)[523, 523, 522], diffMid_Trend_M30:[2.0, 2.0, 2.0], ...
2026.XX.XX XX:XX:XX   [H1],  W_stage_H1:(FLY)[512, 512, 512],  diffMid_Trend_H1:[1.0, 1.0, 1.0], ...
2026.XX.XX XX:XX:XX   [H4],  W_stage_H4:(FLY)[521, 521, 521],  diffMid_Trend_H4:[2.0, 2.0, 2.0], ...

2026.XX.XX XX:XX:XX   [TRADEINFO] Gate:[G6-SHRINK] TradeAct:0 cnt:1 pen:0.75|
  Gate:[G4b-H1OPP] M30dn+H1up:1|act:0 atrsl:0
```

**Reading:**

- M15 bearish fly (522), M30 bearish shrink (523), H4 bearish fly (521) = SELL candidate chain.
- H1 bullish fly (512, mid=1) = directly opposes M30 direction.
- G6-SHRINK fires (M30=523, `pen:0.75`) but G4b-H1OPP then blocks: `M30dn+H1up:1` = M30 bearish vs H1 bullish → `TradeAct:0`.

**Trade decision:** WAIT. Hold any existing SELL with SL at `ATRSL1buf Upper[0]`. Re-enter when H1 turns to `diffMid_Trend=2` or M30 exits shrink.
