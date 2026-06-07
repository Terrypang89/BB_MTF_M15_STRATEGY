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
[M15] → [M30] → [H1] → [H4] → [D1] → [W1] → [TRADEINFO] → [BBTFImpact] → [ATRSL1buf] → [ORDERINFO]
```

**HTF tag availability — lookback rule:**

Not every tick emits all tags. A tag only appears when that TF's bar has updated
on the current tick's datetime. If `[M30]`, `[H1]`, `[H4]`, `[D1]`, or `[W1]`
is absent from a tick, their state is unchanged from the last tick that emitted them.

```
To find the current state of a missing TF tag:
  → search backward in the log for the most recent datetime that contains [M30],
    [H1], [H4], [D1], or [W1] respectively
  → those field values remain valid until the next time that tag appears

Example: tick at 04:07 only shows [M15] and [TRADEINFO]
  → [M30] last seen at 04:00 → use those M30 values
  → [H1]  last seen at 04:00 → use those H1 values
  → [H4]  last seen at 02:00 → use those H4 values
  → [D1]  last seen at 00:00 → use those D1 values
  → [W1]  last seen at Monday 00:00 → use those W1 values

Approximate update frequency (EA runs on M5):
  [M30] → every 6   M5 bars  (30 min)
  [H1]  → every 12  M5 bars  (1 hr)
  [H4]  → every 48  M5 bars  (4 hr)
  [D1]  → every 288 M5 bars  (1 day)
  [W1]  → every 1440 M5 bars (1 week)
```

> **Float precision note:** The EA emits raw MQL5 doubles. Some values will appear as
> e.g. `1.6099999999999999` or `3.7199999999999998` — this is normal IEEE 754 output,
> not a bug. Do not round these when comparing logs.

---

## Tag Field Reference

```
[M15] / [M30] / [H1] / [H4] / [D1] / [W1]
  W_stage_TF:(REGIME)[cur, prev, prev2]        → BBW stage + regime label
  diffMid_Trend_TF:[cur, prev, prev2]           → midline trend (ENUM_BBMID_trend)
                                                   0=no_midtrend 1=uptrend 2=dntrend
                                                   3=sidewaytrend 4=sidewaydntrend 5=sidewayuptrend
  BBUpDn_TF:[cur, prev, prev2]                  → band movement state (2-bar confirmed):
                                                   0=neutral/mixed (no clean confirmation)
                                                   1=expanding  Upper↑ AND Lower↓ for 2 bars
                                                   2=shrinking  Upper↓ AND Lower↑ for 2 bars
                                                   3=up         Upper↑ AND Lower↑ for 2 bars (parallel up)
                                                   4=dn         Upper↓ AND Lower↓ for 2 bars (parallel down)
  trend_TF:[cur, prev, prev2, ]                 → BB midline trend (ENUM_BB_trend) per bar (trailing comma)
                                                   0=no_trend  1=up_trend  2=dn_trend  3=sideway_trend
                                                   4=sideway_dntrend  5=sideway_uptrend
                                                   7=rev_uptrend (REVUP on chart)  8=rev_dntrend (REVDN on chart)
                                                   note: shares values 0–5 with diffMid_Trend; adds 7/8 for reversals
  prev_trend_TF:N                               → ENUM_BB_trend value of the bar before cur
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
  close_TF / high_TF / low_TF                   → M5 candlestick close/high/low price
                                                   logged in [M15] block only; values are M5 bar OHLC
                                                   (EA runs on M5 period — these are the current M5 candle prices)

[TRADEINFO]
  Gate:[Gx-LABEL] TradeAct:N cnt:N pen:N.NN| ...flags...|act:N atrsl:N
  Minimal format (no gate fired): |act:N atrsl:N
  TradeAct: 0=NEUTRAL  1=BUY  2=SELL
  act:      0=no action  4=open trade
  atrsl:    0=ATRSL not used as SL  1=ATRSL used as SL
  pen:      size penalty multiplier (1.0=none, <1.0=reduced size)
  cnt:      number of TFs in aligned chain
  (gate labels subject to redesign — not documented here)

[BBTFImpact]
  Sideway_val:[NNNNN-...]                        → 5-digit concatenation of per-TF sideway scores [H4][H1][M30][M15][M5]
                                                   each digit 0–6:  +4 if diffMid_Trend>=3 (flat/side)
                                                                    +2 if stage<500 (SQZ/SW/STR)
                                                                    +1 if stage==513 or 523 (shrink)
                                                                     0 if clean fly (stage>=500, not 513/523)
                                                   [NNNNN]        = sideway not confirmed
                                                   [NNNNN-S_XX]   = sideway CONFIRMED (combined detection triggered)
  HTF_Drive_LTF_Sideway:[TF_N, ...]              → HTF driving LTF into sideway; TF label = target being driven
                                                   M5_1=M15 drives M5 sideways; M15_1=M30 drives M15 sideways
  LTF_Drive_HTF_Fly:[TF_N, ...]                  → LTF driving HTF into fly; TF label = target being driven
                                                   M15_1=M5 drives M15 to fly; M30_1=M15 drives M30 to fly
  midline_Cluster:[N, N, N]                      → midline price spread vs M15: [|M15-M5|, |M15-M30|, |M15-H1|]
  line_seq_touch:[TF_cur-recent,prev, ...]       → touch sequence per TF [cur state - recent touch, prev touch]
                                                   ENUM_BB_LineTouch: 0=none 6=dnup_Dn 7=updn_Mid
                                                   8=dnup_Mid 9=updn_Up 16=untouch_dnup_Dn
                                                   17=untouch_updn_Mid 18=untouch_dnup_Mid 19=untouch_updn_Up
  line_seq_cross:[TF_cur-recent,prev, ...]       → cross sequence per TF [cur state - recent cross, prev cross]
                                                   ENUM_BB_LineCross: 0=none 10=BB_LOW 15=CrossUp_LOW
                                                   16=CrossDn_LOW 20=BB_DN 26=CrossDn_DN 30=BB_UP
                                                   35=CrossUp_UP 40=BB_HIGH 45=CrossUp_HIGH 46=CrossDn_HIGH
  untouch_val:[TF_cur-prev, ...]                 → price proximity to BB lines per TF [cur state - prev state]
                                                   0=none 26=near_lower 27=near_mid_above
                                                   28=near_mid_below 29=near_upper
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

`diffMid_Trend` uses `ENUM_BBMID_trend` — the midline direction classification:

```
0 = no_midtrend   no direction established
1 = uptrend       mid rising cleanly
2 = dntrend       mid falling cleanly
3 = sidewaytrend  mid stationary
4 = sidewaydntrend mid drifting lower
5 = sidewayuptrend mid drifting higher
```

**Distinction from `trend_TF`:**

```
diffMid_Trend  → ENUM_BBMID_trend  values 0–5 only, no reversal states
trend_TF       → ENUM_BB_trend     values 0–5 plus 7=rev_up, 8=rev_dn
```

Both share values 0–5 with the same meaning. `trend_TF` adds reversal detection
(7/8) that `diffMid_Trend` does not have. `diffMid_Trend>=3` is the sideway
threshold used in `Sideway_val` scoring and gate logic.

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
HTF_Drive_LTF_Sideway       Higher TF driving lower TF into sideway compression.
                            TF label = the TF being driven (target); driver = next higher TF
                            e.g. M5_1  → M15 is driving M5 into sideway
                                 M15_1 → M30 is driving M15 into sideway
                            [] = none active
LTF_Drive_HTF_Fly           Lower TF driving higher TF into fly.
                            TF label = the TF being driven (target); driver = next lower TF
                            e.g. M15_1 → M5 is driving M15 into fly
                                 M30_1 → M15 is driving M30 into fly
                            Both fields active simultaneously = conflict/volatile transition state
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
                              (values 26–29 near_ variants used by untouch_val only, not here)
untouch_val                 Price proximity to BB lines — [TF_cur-prev] per TF
                            cur/prev = proximity state each bar, same values:
                              0  = none         price not near any band
                              26 = near_dnup_BBDn   price within threshold of lower band
                              27 = near_updn_BBMid  price within threshold above midline
                              28 = near_dnup_BBMid  price within threshold below midline
                              29 = near_updn_BBUp   price within threshold of upper band
                            Uses close price AND prev bar high/low vs BBW_untouch_dist threshold
                            Priority (first match wins): lower → upper → mid-dn → mid-up
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
HTF_Drive_LTF_Sideway on M5+M15       → M15+M30 driving M5+M15 sideways → sizeMultiplier = 0.25
HTF_Drive_LTF_Sideway on M5 only      → M15 driving M5 sideways only    → sizeMultiplier = 0.50
LTF_Drive_HTF_Fly active, no suppress → LTFs pushing HTFs to fly         → sizeMultiplier = 1.00
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

## Example 2: Full TF Bull Fly — No Trade (No Gate Fired)

**Source: 2026.02.23 01:00**

```
2026.02.23 01:00:02   [M15], W_stage_M15:(FLY)[511, 512, 511], diffMid_Trend_M15:[1.0, 1.0, 1.0],
  BBUpDn_M15:[1, 3, 3], trend_M15:[1, 1, 1, ], prev_trend_M15:1,
  diffMid_M15:[2.04, 1.78, 1.85], diffBBW_M15:[12.48, 5.72, 5.97],
  WLV_M15:[1.1, 0.97, 0.89],
  MidLV_M15:[5080.1, 5078.06, 5076.09], UppLV_M15:[5108.0, 5102.78, 5098.62],
  LowLV_M15:[5052.2, 5053.35, 5053.57],
  close_M15:[5109.5, 5107.8, 5103.64], high_M15:[5109.5, 5107.96, 5107.07],
  low_M15:[5109.5, 5102.94, 5101.88],

2026.02.23 01:00:03   [M30], W_stage_M30:(FLY)[512, 511, 511], diffMid_Trend_M30:[1.0, 1.0, 1.0],
  BBUpDn_M30:[3, 0, 1], trend_M30:[1, 1, 1, ], prev_trend_M30:1,
  diffMid_M30:[4.6, 3.68, 3.34], diffBBW_M30:[6.31, 7.64, 14.19],
  WLV_M30:[2.04, 1.97, 1.87],
  MidLV_M30:[5061.6, 5057.0, 5053.09], UppLV_M30:[5113.17, 5106.92, 5100.23],
  LowLV_M30:[5010.03, 5007.07, 5005.94],

2026.02.23 01:00:04   [H1], W_stage_H1:(FLY)[511, 511, 512], diffMid_Trend_H1:[1.0, 1.0, 1.0],
  BBUpDn_H1:[1, 1, 3], trend_H1:[1, 1, 1, ], prev_trend_H1:1,
  diffMid_H1:[5.49, 4.61, 4.17], diffBBW_H1:[23.13, 23.53, 12.57],
  WLV_H1:[2.61, 2.38, 2.12],
  MidLV_H1:[5040.95, 5035.46, 5030.72], UppLV_H1:[5106.68, 5095.3, 5084.07],
  LowLV_H1:[4975.21, 4975.62, 4977.37],

2026.02.23 01:00:05   [H4], W_stage_H4:(FLY)[512, 512, 512], diffMid_Trend_H4:[1.0, 1.0, 1.0],
  BBUpDn_H4:[3, 3, 3], trend_H4:[1, 1, 1, ], prev_trend_H4:1,
  diffMid_H4:[11.77, 8.29, 6.71], diffBBW_H4:[20.36, 26.27, 14.87],
  WLV_H4:[4.5600000000000005, 4.35, 4.03],
  MidLV_H4:[4985.72, 4973.96, 4965.26], UppLV_H4:[5099.28, 5082.18, 5065.24],
  LowLV_H4:[4872.17, 4865.73, 4865.29],

2026.02.23 01:00:06   [D1], W_stage_D1:(FLY)[512, 512, 513], diffMid_Trend_D1:[5.0, 5.0, 1.0],
  BBUpDn_D1:[0, 3, 0], trend_D1:[0, 0, 0, ], prev_trend_D1:1,
  diffMid_D1:[2.98, 2.66, 5.9399999999999995], diffBBW_D1:[11.81, -4.17, -25.05],
  WLV_D1:[12.1, 11.98, 12.0],
  MidLV_D1:[5002.66, 4999.68, 4994.67], UppLV_D1:[5305.21, 5299.1, 5294.25],
  LowLV_D1:[4700.12, 4700.27, 4695.09],

2026.02.23 01:00:07   [W1], W_stage_W1:(FLY)[511, 401, 401], diffMid_Trend_W1:[1.0, 1.0, 1.0],
  BBUpDn_W1:[3, 3, 3], trend_W1:[0, 0, 0, ], prev_trend_W1:1,
  diffMid_W1:[56.92, 60.83, 62.31], diffBBW_W1:[119.21, 54.09, 40.1],
  WLV_W1:[33.27, 32.08, 32.04],
  MidLV_W1:[4456.01, 4399.09, 4341.67], UppLV_W1:[5197.22, 5104.61, 5037.2],
  LowLV_W1:[3714.8, 3693.57, 3646.14],

2026.02.23 01:00:07   [TRADEINFO] |act:0 atrsl:0

2026.02.23 01:00:07   [BBTFImpact] Sideway_val:[00000]
  HTF_Drive_LTF_Sideway:[H4_1, D1_1],
  LTF_Drive_HTF_Fly:[M15_1, M30_1, H1_1, H4_1, D1_1, W1_1],
  midline_Cluster:[14.45, 18.5, 39.15],
  line_seq_touch:[M5_0-9,9, M15_19-9,9, M30_0-9,9, H1_0-9,9, H4_0-9,19, D1_0-8,7, W1_0-9,9],
  line_seq_cross:[M5_40-30,40, M15_0-40,30, M30_0-30,40, H1_0-40,30, H4_0-40,30, D1_0-30,20, W1_0-30,40],
  untouch_val:[M5_0-0, M15_19-0, M30_0-0, H1_0-0, H4_0-0, D1_0-0, W1_0-0],
  Midline_cross:[M5_40-30, M15_40-40, M30_46-46, H1_40-40, ...]

2026.02.23 01:00:07   [ATRSL1buf] dir:0,
  Trend:[2.0,2.0,2.0,2.0,2.0,2.0,],
  LV:[5101.09,5095.84,5095.84,5091.95,5091.95,5090.24,],
  Upper:[5112.35,5112.35,5112.35,5101.8,5101.8,5101.8,],
  Lower:[5101.09,5095.84,5095.84,5091.95,5091.95,5090.24,],
  SLMid:[5110.06,5106.26,5104.21,5102.25,5099.32,5099.43,],
  Val:[4.48,4.63,4.49,4.39,4.13,4.28,]

2026.02.23 01:00:07   [ORDERINFO], BUY_PROFIT:0.0, BUY_LOTS:0.0, BUY_TICKET_NUM:0, BUYS:0,
  SELL_PROFIT:0.0, SELL_LOTS:0.0, SELL_TICKET_NUM:0, SELLS:0, TOTALORDERS:0
```

**Reading:**

**[M15]** Stage `[511,512,511]` = fly++ cur, fly+- prev (was expanding), fly++ prev2. `diffMid_Trend=[1,1,1]` = clean uptrend all bars. `BBUpDn=[1,3,3]` = expanding cur (Upper↑ AND Lower↓), parallel-up prev2 bars. `diffBBW=[12.48,5.72,5.97]` all positive = BB actively widening. M15 strongly bullish. `close_M15=5109.5` = M5 candle closed above upper band (`UppLV_M15=5108.0`) — price breaking out above M15 upper band.

**[M30]** Stage `[512,511,511]` = fly+- cur (parallel-up expanding), fly++ prior. `BBUpDn=[3,0,1]` = parallel-up cur, neutral prev, expanding prev2 — transition into parallel-up. `diffBBW` all positive = expanding. M30 bullish and widening.

**[H1]** Stage 511 all 3 bars = fly++, `diffMid_Trend=[1,1,1]` = clean uptrend. `BBUpDn=[1,1,3]` = expanding cur and prev (Upper↑ Lower↓), parallel-up prev2. `diffBBW` large and positive = strong expansion. H1 confirming bull fly.

**[H4]** Stage 512 all 3 bars = fly+-, `BBUpDn=[3,3,3]` = parallel-up confirmed all 3 bars. `diffMid_H4=[11.77,8.29,6.71]` = mid rising 11+ points per H4 sample = strong bull trend. H4 parallel-up with consistent momentum.

**[D1]** Stage `[512,512,513]` = fly+- cur/prev, shrinking prev2. `diffMid_Trend=[5,5,1]` = side-up cur/prev, uptrend prev2 = D1 mid slowing but still rising. `trend_D1=[0,0,0]` = no_trend on all bars (D1 trend enum not established yet). `BBUpDn=[0,3,0]` = neutral cur, parallel-up prev. D1 transitioning — was shrinking, now expanding again but mid going sideways.

**[W1]** Stage `[511,401,401]` = fly++ cur, SQZ prev2 bars. `BBUpDn=[3,3,3]` = parallel-up all 3 bars. `diffMid_W1=[56.92,60.83,62.31]` = mid rising 57–62 points per W1 sample = massive weekly bull move. `trend_W1=[0,0,0]` = no_trend (W1 trend enum not established). W1 broke from SQZ (401) to fly++ = major weekly breakout.

**[TRADEINFO]** `|act:0 atrsl:0` — minimal format, no gate fired, no trade. Despite strong bullish alignment across all TFs, no entry condition was met at this tick.

**[BBTFImpact]** `Sideway_val:[00000]` = all 5 digits zero = every TF (M5–H4) is clean fly, no sideway pressure at all. `HTF_Drive_LTF_Sideway:[H4_1, D1_1]` = D1 driving H4 sideways, H4(?) driving D1 — some HTF suppression at higher TFs. `LTF_Drive_HTF_Fly:[M15_1,M30_1,H1_1,H4_1,D1_1,W1_1]` = full cascade of LTF→HTF fly energy, M5 driving everything up through W1. `midline_Cluster=[14.45,18.5,39.15]` = midlines spread far apart (H1 39 points from M15) — TFs at different price levels = strong trend, not compression. `untouch_val:[M15_19-0]` = M15 cur=19 (price nearly touched upper band from above = `untouch_updn_BBUp`), prev=0 — M15 price approaching upper band proximity zone this bar.

**[ATRSL1buf]** `dir:0` = uptrend mode, LV=Lower. `Trend=[2,2,2,2,2,2]` = all 6 bars downtrend (2) — note: `dir:0` means uptrend but `Trend=2` means the buffer itself is moving down. This is a contradiction worth noting: LV/Lower values are rising (`5090→5102`) while Trend shows 2. Likely `Trend` reflects the ATR band direction independently of `dir`.

**Overall diagnosis:**
> Full multi-TF bull fly from M15 through W1 with W1 breaking out of SQZ. `Sideway_val=00000` = cleanest possible trend state. M5 candle closed above M15 upper band (5109.5 > 5108.0). No trade fired this tick despite ideal conditions — gate logic not satisfied at this specific bar. Strong candidate for BUY entry on next bar if gates align.

---

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
