# Backtest Chart Analysis — BB MTF Strategy

Visual interpretation guide for Tofu EA backtest chart screenshots.
**Always analyze top-down: W1 → D1 → H4 → M30 -> M15.**
Higher TFs determine where lower TF trades travel to, and why lower TFs go sideway.

Work through: **Part 1** (read the chart) → **Part 2** (HTF context) → **Part 3** (MTF/LTF scenario) → **Part 4** (trade decision).

---

## How to Trade — Summary

### Step 1: Read HTF (W1 → D1 → H4) first
- **W1 fly BUY + D1 fly BUY + H4 fly BUY** → full tailwind. M30 BUY trades ride toward H4 outer band then D1 outer band. Hold through brief M5/M15 squeezes.
- **H4 shrink (513/523)** → M30 is ranging inside H4's band. Take short trades only. Exit when price touches H4 outer band (G8-BNDTGT fires automatically).
- **H4 SQZ (400-499)** → no macro target. Only cascade band-touch entries (G0b path) are valid. M5 must confirm direction.
- **H4 opposing direction** → G4e-H4OPP or H4-OPPOSE blocks entry. Do not fight H4.

### Step 2: Identify your scenario
| MTF state | Action |
|-----------|--------|
| M30+M15 both fly, same direction | Enter on M5 FLAT→UP or FLAT→DN transition |
| M30 fly, M15/M5 shrinking | Shrink path entry — M5 transition still the trigger |
| Only M5 shrinking | **Wait** — M5 alone is noise; M15 must also compress |
| H1/M30 SQZ, price at outer band | Cascade entry (G0b-TOUCH) if all filters pass |
| M15+M30 both SQZ | **No entry** — G0b-PINK exits all open positions |
| M30 mid≥3 AND M15 mid≥3 | **No new entries** — G0 or G0-HOLD depending on H1 |

### Step 3: Entry trigger — always M5 transition
The entry signal is **always a BBMidTrend change on M5**:
- `FLAT(3) → UP(1)` or `FLAT(3) → DN(2)` → base quality 70
- `UP(1) → DN(2)` or `DN(2) → UP(1)` (reversal) → base quality 75
- M15 confirming fly stage → +10 to +15 quality boost
- Quality ≥ 90 → 1.0× size | ≥ 75 → 0.75× | ≥ 60 → 0.5× | ≥ 45 → 0.25× | < 45 → skip

### Step 4: Know your price target before entering
| HTF state | Target for M30 trade | Exit signal |
|-----------|----------------------|-------------|
| H4 fly | H4 outer band | G8-BNDTGT or G5-FADE |
| H4 shrink | H4 outer band boundary (range reversal) | G8-BNDTGT |
| D1 fly + H4 fly | D1 outer band (long hold) | D1 starts shrinking |
| H4 SQZ | Within H4 band range only | G0b-PINK or G0 |

### Step 5: Know what blocks entry
Block gates fire **before** the entry. If you see a DimGray or DarkOrange label, that bar was blocked:
- **G4e-H4OPP / H4-OPPOSE** — H4 opposing the trade direction
- **G4c-M15OPP / G0b-M15OPP** — M15 opposing fly/shrink/SQZ
- **G4f-M30OPP / G0b-M30OPP** — M30 opposing fly/shrink/SQZ
- **G0b-M5FLY / G0b-M5OPP** — M5 itself contradicting the cascade direction
- **G1-FAIL** — neither M30 nor M15 midtrend confirms direction
- **G4-BLOCK** — M15 hard conflict (clear mid=1 vs SELL or mid=2 vs BUY)

### Step 6: Exit rules
| Trigger | Gate | Act |
|---------|------|-----|
| M5 UP→FLAT or DN→FLAT | G5-FADE | 7 — exit all |
| M30+M15+H1 all mid≥3 | G0 | 7 — exit all |
| M15+M30 both SQZ | G0b-PINK | 7 — exit all |
| Price hits outer band (cascade context) | G8-BNDTGT | 7 — exit all |
| Float loss < −$50 | G0e-MAXLOSS | 7 — exit all |
| ATRSL trailing stop hit | ATRSL | Broker closes |

---

## Auto-Load Reference Images

**When this file is read for chart analysis: immediately read the following image files using the Read tool before applying any analysis.**

**When user asks to analyze a specific backtest version chart:**
- Read `references/Backtest_data/extras/backtested_chart.jpg` as the baseline visual reference
- Read `references/Backtest_data/extras/HTF/backtest_EA_HTF_Fly_2_Shrink_part1.jpg` and `part2.jpg` as HTF reference
- Then read any user-specified image path (e.g. `references/Backtest_data/V22.XX/chart.jpg`)

### Main Dashboard

![Main dashboard](./Backtest_data/extras/backtested_chart.jpg)

Full backtest period for XAUUSD — 3 macro phases visible:
- **Left:** All TFs aligned bullish (511/512) — W1/D1 fly driving H4 fly driving M30/M15/M5 fly
- **Center:** Peak — price reached D1 outer band → D1/H4 start shrinking → M30/M15 reverse
- **Right:** Recovery — lower TFs cycle through shrink→SQZ→breakout while D1/H4 macro steps continue

### ATRSL1buf Indicator

![ATRSL1buf](./Backtest_data/extras/backtested_EA_atrsl1buf.jpg)

- **dir=0 (uptrend):** orange below price, yellow buffer below orange — stop trails up
- **dir=1 (downtrend):** orange above price, yellow buffer above orange — stop trails down
- ATRSL lags during brief M5/M15 squeezes — do not use as primary signal during fly expand

---

---

# PART 1 — CHART BASICS

## 1. Chart Layers

| Layer | What you see |
|-------|-------------|
| Candlesticks | OHLC price bars |
| Bollinger Bands | Multiple sets of 3 bands (upper/mid/lower) — one per timeframe in a distinct color |
| Upper band labels | `TF-BBW_stage` printed at top of each upper band every bar |
| Middle band labels | `BB_diffMid_Trend` printed at middle band — only when value is 3, 4, or 5 |
| ATRSL1buf | Orange trailing stop with yellow buffer band |
| Gate labels | Short colored text tags (e.g. `[G0b-TOUCH]`, `[G6-BUY]`) — mark where gates fired |
| Trade arrows | Entry/exit markers on candles (up arrow = buy, down arrow = sell) |

---

## 2. Bollinger Band Color Reference

| Timeframe | Color | BB_datas[] | Role |
|-----------|-------|------------|------|
| M5 | Aqua / Cyan | [0] | Entry trigger — fastest |
| M15 | Goldenrod | [1] | Entry alignment |
| M30 | GreenYellow | [2] | Primary trend driver |
| H1 | Red | [3] | Chain anchor |
| H4 | Yellow | [4] | Macro bias filter |
| D1 | Magenta | [5] | Daily macro — price target boundary |
| W1 | LightCyan | [6] | Ultra-macro — outermost band |
| ATRSL1buf | Orange | — | Trailing stop |

> **H4 vs W1:** H4 is saturated yellow and narrower; W1 is pale near-white cyan and the widest band set on the chart.

---

## 3. Upper Band Labels — BBW_Stage Codes

Format: `{TF}-{BBW_stage}` or `{TF}-{debug}-{BBW_stage}` (SQZ includes BBW ratio)

| Code | Name | What you see | Trade Bias |
|------|------|-------------|------------|
| 511 | FLY++ bullish expand | Bands fanning out upward, all 3 rising | BUY |
| 512 | FLY+- parallel up | All bands rising together in parallel | BUY |
| 521 | FLY++ bearish expand | Bands fanning out downward | SELL |
| 522 | FLY-+ parallel down | All bands falling in parallel | SELL |
| 513 | FLY-- bullish shrink | Upper band curling down, lower band still rising | WATCH → use M5 |
| 523 | FLY-- bearish shrink | Upper band still rising, lower band curling down | WATCH → use M5 |
| 400–499 | SQZ | Bands extremely tight and flat | WAIT |

---

## 4. Middle Band Labels — BB_diffMid_Trend

Format: `{value}` or `{value}-REVUP/REVDN`. Values 1 and 2 are **not shown** on chart.

| Value | Name | Visual | Label shown? |
|-------|------|--------|-------------|
| 1 | Uptrend | Midband rising | No |
| 2 | Downtrend | Midband falling | No |
| 3 | Sideways | Midband flat | Yes |
| 4 | Sideway downtrend | Midband flat, slight downward bias | Yes |
| 5 | Sideway uptrend | Midband flat, slight upward bias | Yes |

- `REVUP` = midtrend just flipped from 2 → uptrend reversal this bar
- `REVDN` = midtrend just flipped from 1 → downtrend reversal this bar
- **Reading combo:** Upper label = structure (expanding/contracting/compressed); middle label = direction. Together they define the full regime.

---

## 5. ATRSL State

| State | Visual | Meaning |
|-------|--------|---------|
| dir=0 (uptrend) | Orange below price, rising | BUY stop — trailing up |
| dir=1 (downtrend) | Orange above price, falling | SELL stop — trailing down |
| Yellow buffer | Below orange (BUY) or above orange (SELL) | Visual cushion — 1 ATR offset from stop |

---

## 6. Gate Label Colors

| Color | Gate labels | Meaning |
|-------|-------------|---------|

---

---

# PART 2 — HIGHER TIMEFRAME ANALYSIS (W1 → D1 → H4)

**IMPORTANT:** Always read HTF before analyzing MTF/LTF. HTF determines:
1. **Direction** — which way the wind blows for all lower TFs
2. **Target** — where lower TF trades travel to before stopping
3. **Why sideway** — lower TF goes sideway because HTF is compressing or ranging
4. **MTF Predict** — if H4 is sideway and D1 is shrinking, in the same time M30 & H1 in fly in direction, able to predict the fly will end at H4 upper band or H1 will drive H4 to fly. 

The cascade is top-down: **W1 sets D1's range → D1 sets H4's range → H4 sets H1's range -> H1 sets M30's range → M30 sets M15's range**.

---

## HTF Reference Charts

![HTF Fly to Sideway part 1](./Backtest_data/extras/HTF/backtest_EA_HTF_Fly_2_Shrink_part1.jpg)

**Part 1 — Full macro cycle (Jan–Feb 2026):**
- **Left:** W1 (lightcyan/white) and D1 (magenta) bands stepping upward — both in fly. H4 (yellow) flies in the same direction. All TFs aligned: M30/M15/M5 all ride this macro momentum upward
- **Yellow circles (left):** H4 shrink and squeezed then continue fly — each step up is where H4 upper band previously sat; these become support on the way up
- **Peak (center, ~5400):** Price reached D1 upper band → D1 starts shrinking (top of D1 fly). H4 follows, entering shrink. M30/M15 lose macro tailwind and reverse
- **White rectangles (right):** After D1/H4 enter shrink, M30/M15 are forced to range within the H4 band envelope — oscillating between H4 upper and H4 lower. This is the "M30 sideway caused by H4 shrink" pattern
- **Blue circles:** Cascade band-touch entries (G0b-TOUCH) firing at H4 band boundaries during H4 shrink phase — price touches H4 outer band edge, G0b-TOUCH fires

![HTF Fly to Sideway part 2](./Backtest_data/extras/HTF/backtest_EA_HTF_Fly_2_Shrink_part2.jpg)

**Part 2 — H4 shrink zones (Feb–Apr 2026):**
- **H4 stage labels "H4-Fly--" visible on bands** — H4 is in shrink (513 or 523) throughout most of this period
- **D1 (magenta) still stepping at bottom** — D1 remains in fly, providing macro direction bias even while H4 shrinks. D1 fly direction = the "eventual" direction price returns to after H4 shrink resolves
- **Large pink rectangles:** H4 shrink zones where M30/M15 are confined. Inside each rectangle: M30/M15 oscillate within the H4 upper/lower band range — they cannot break out until H4 exits shrink
- **Purple circles:** M30/M15 pivot points at H4 band boundaries — these are the "outer band touch" exit signals (G8-BNDTGT fires here). Sell when M30 touches H4 upper band; buy when M30 touches H4 lower band
- **After each pink rectangle:** When H4 exits shrink back to fly (either resuming D1 direction or reversing), M30/M15/M5 resume trending

---

## W1 — Ultra-Macro Context

W1 is the slowest band (lightcyan, widest). It changes direction rarely but determines the multi-month trajectory.

| W1 Stage | diffmid Trend | What it means | MTF implication |
|----------|---------------|----------------|----------------|
| 511/512 (BUY) | | Multi-week uptrend — macro wind is bullish | All lower TF dips are buying opportunities; BUY trades last longer; SELL trades are counter-trend (smaller size, faster exit) |
| 521/522 (SELL) | | Multi-week downtrend — macro wind is bearish | All lower TF rallies are selling opportunities; SELL trades last longer; BUY trades are counter-trend |
| 513 (BUY shrink) | | Macro uptrend slowing — D1/H4 will start to compress | Expect H4 shrink soon → M30 ranges will get tighter; new BUY entries are shorter-duration |
| 523 (SELL shrink) | | Macro downtrend slowing | Expect H4 shrink soon → SELL entries shorter-duration |
| 400–499 (SQZ) | | Multi-week range — no macro conviction | No sustained directional moves at any TF; range-trade only; avoid large positions |

**W1 price target:** When W1 is in fly, the D1 outer band is where price gravitates before W1 itself turns. When price is far below W1 upper band (BUY), the W1 band acts as a long-distance magnet.

---

## D1 — Daily Macro

D1 is the magenta band. It steps in large increments and updates slowly.

| D1 Stage | diffmid Trend | What it means | MTF implication |
|----------|---------------|-------------------|-------------------|
| 511/512 (BUY) + W1 fly | | Strong macro alignment — daily uptrend | H4 BUY entries are high-quality; hold through H4 brief SQZ; target = D1 outer band |
| 521/522 (SELL) + W1 fly | | D1 SELL vs W1 BUY — D1 is counter-trend pullback | H4 SELL entries are shorter-duration; expect D1 BUY to resume once pullback exhausts |
| 521/522 (SELL) + W1 SELL | | Full alignment bearish | H4 SELL entries ride toward D1 lower band; BUY is counter-trend |
| 513/523 (shrink) | | D1 losing directional conviction | H4 is about to lose macro backing; H4 trades become range-bound |
| 400–499 (SQZ) | | D1 flat — no daily directional bias | H4 fly entries get no macro tailwind; H4 trades chop within D1 band range |

**D1 price target rule:** When D1 is in fly BUY, H4 trades travel toward the **D1 upper band** before D1 turns. The D1 upper band is the "ceiling" for H4 BUY trades on the macro timeframe.

---

## H4 — Macro Bias Filter

H4 is the yellow band. It directly controls M30/M15/M5 entry quality and duration.

| H4 Stage + Mid | diffmid Trend | What it means | MTF implication |
|----------------|---------------|-----------------|-------------------|
| 511/512 + mid=1 | | H4 BUY fly | M30 BUY trades fully backed — ride toward H4 upper band; hold through M5 brief squeezes |
| 521/522 + mid=2 | | H4 SELL fly | M30 SELL trades fully backed — ride toward H4 lower band |
| 513 + mid=1/5 | | H4 bullish shrink | H4 is contracting but still bullish — M30 BUY trades are shorter; exit when price reaches H4 outer band |
| 523 + mid=2/4 | | H4 bearish shrink | H4 contracting, still bearish — H1 SELL trades shorter |
| 513/523 + mid=3 | | H4 shrink with flat mid | H4 has no directional conviction — **G4e-H4OPP blocks this in shrink path** |
| 400–499 + mid=1/5 | | H4 SQZ, but midtrend bullish | Weak H4 — G0b-H4OPP passes (mid has some conviction); M5 must confirm direction |
| 400–499 + mid=3 | | H4 SQZ flat | No macro conviction at all |
| 400–499 + mid=2/4 | | H4 SQZ, bearish mid | H4 SQZ but leaning bearish — blocks BUY entries via G0b-H4OPP |

---

## The Core HTF → MTF Cascade Rule

**Always check H4**

**Why does H1 go sideway?** Because H4 is shrinking or in SQZ.

When H4 is in fly: H1 has a clear macro path → H1 trades travel toward H4 outer band.
When H4 enters shrink: H4's band range narrows → H1 is confined within that shrinking range → H1 oscillates and appears "sideway."
When H4 is in SQZ: H1 has no target beyond the SQZ boundaries → H1 chops flat.

```
H4 stage       → H1 behavior              → MTF trade duration
─────────────────────────────────────────────────────────────────
511/512 fly    → H1 trends with H4        → Long trades — hold until H4 outer band
513/523 shrink → H1 ranges within H4 band → Short trades — exit at H4 band boundary
400-499 SQZ    → H1 flat/ranging          → No new trades; wait for H4 breakout
```

**Price target derivation (top-down):**

| Trade entry | Target 1 | Target 2 | Exit signal |
|-------------|----------|----------|-------------|
| W1 fly BUY + D1 fly BUY | H4 outer band | D1 outer band | D1 starts shrinking (513) |
| D1 fly BUY + H4 fly BUY | H1 outer band → H1 outer band | H4 outer band | H4 starts shrinking |
| H4 fly BUY + H1 fly BUY | M15 outer band | H1 outer band | H1 goes sideway; H4 outer band reached |
| H4 shrink + H1 ranging | H4 upper band (BUY) or lower (SELL) | — | Price touches H4 outer band → G8-BNDTGT fires |
| All HTF SQZ | No target | — | Wait — no trade |

---

## HTF Analysis Step-by-Step

Before looking at any H1/M30/M15/M5 entry, answer these questions:

**1. What is W1 doing?**
- Fly BUY / Fly SELL / Shrink / SQZ?
- This sets the multi-week wind direction.
- Impact D1 sideway when W1 shrink

**2. What is D1 doing?**
- Fly same direction as W1 → full alignment, hold trades longer
- Fly opposite to W1 → counter-trend pullback; shorter trades
- Shrink → D1 losing conviction; H4 trades will become shorter
- SQZ → H4 has no D1 backing; only range trades

**3. What is H4 doing?**
- Fly BUY/SELL → H1 entries ride toward H4 outer band
- Shrink (513/523) → H1 is ranging within H4 band; short trades, target = H4 outer band boundary
- SQZ (400-499) → H1 entry requires G0b / H4-SQZ path with M5 confirmation

**4. What is the price target for H1?**
- H4 fly → H4 outer band is where H1 trades stop
- H4 shrink → H4 outer band is where the range reverses
- H4 SQZ → no clear target; wait for breakout

**4. What is the price target for H1?**
- H4 fly → H4 outer band is where H1 trades stop
- H4 shrink → H4 outer band is where the range reverses
- H4 SQZ → no clear target; wait for breakout

**5. Why is H1 sideway right now?**
- Check H4: if H4 is shrinking or SQZ → that is why H1 is flat
- Once H4 exits shrink back to fly → H1 will resume trending

---

---

# PART 3 — MIDDLE AND LOWER TIMEFRAME SCENARIO ANALYSIS

Apply after HTF context is established. Each scenario: **What you see → What it means → Trade action**

---

## Scenario A — Normal Fly (All TFs Aligned)

![Normal fly scenario](./Backtest_data/extras/backtested_EA_fly_scenario.jpg)

**HTF context:** W1 fly + D1 fly + H4 fly — all in same direction. Full macro tailwind.

**What you see:**
- H1 (red) and M30 (greenyellow) bands stepping in fly (511/512 or 521/522)
- All bands fanning outward in the same direction
- M5 (aqua) may show 2–3 brief tight bundles mid-fly — noise squeezes
- No mid-band labels visible (mid=1 or 2 — suppressed)
- H4 (yellow) stepping in same direction — macro confirmed

**What it means:**
- Full alignment — strongest possible trend
- Brief M5/M15 compressions are noise — M30 midtrend is the reference
- H4 fly is why brief squeezes resolve back to fly instead of deeper compression
- Price target: H4 outer band → then D1 outer band if D1 is also fly

**Trade action:**
```
BUY:  H1+M30 511/512 + mid=1  →  enter on M5 FLAT→UP transition
SELL: H1+M30 521/522 + mid=2  →  enter on M5 FLAT→DN transition
HOLD: through all brief M5/M15 noise squeezes (< 3 bars)
EXIT: M5 UP→FLAT (G5-FADE) | M30+M15 both sideway (G0) | ATRSL stop hit | H4 outer band reached (G8-BNDTGT)
SIZE: 1.0× (full — highest quality when W1+D1+H4 all aligned)
```

---

## Scenario B — Fly → Shrink (Inner TFs Contracting)

![Fly to shrink](./Backtest_data/extras/backtested_EA_fly_2_fly_shrink.jpg)
![Fly to shrink zoom](./Backtest_data/extras/backtested_EA_fly_2_fly_shrink_zoomin.jpg)

**HTF context:** H4 is still in fly, but M30 or M15 starting to shrink. H4 provides the direction and target; M30/M15 are resting before continuing.

**What you see:**
- H1 (red) and H4 (yellow) still in fly (bands stepping)
- M30 or M15 bands beginning to converge (513/523)
- M5 (aqua) tightening; midtrend labels (3, 4, 5) appear at midband
- Bands that were fanning out are now closing in from one side

**What it means:**
- M30/M15 losing momentum temporarily; H4 macro structure intact
- Price is "resting" inside H4's band before continuing toward H4 outer band
- M5 midtrend transitions are the only valid entry triggers now

**Cascade shrink sequence (why each TF goes sideway):**
- **Only M5 shrink:** M5 resting, M15/M30 still fly → wait — M5 noise within M30 fly
- **M15 shrink** + M30/H1/H4 fly → M15 confined within M30 band; price touches M15 outer band
- **M30 shrink** + H1/H4 fly → M30 confined within H1 band; price touches M30 outer band
- **H1 shrink** + H4 fly → H1 confined within H4 band; price touches H1 outer band

**Trade action:**
```
ENTRY: M5 FLAT→UP (BUY) or FLAT→DN (SELL) transition
WAIT if: only M5 shrinking, M15 still fly — M5 alone is noise
BLOCK: H4 opposing (G4e-H4OPP) | M15 opposing (G4c-M15OPP) | M30 opposing (G4f-M30OPP)
TARGET: outer band of lowest TF still in fly (= where price stops this leg)
EXIT: M5 UP→FLAT (G5-FADE) | cascade into SQZ | outer band touched (G8-BNDTGT)
SIZE: 0.75× (M15 or M30 shrink alone) → 0.50× (M30+H1 both) → 0.25× (all 3 shrink)
```

---

## Scenario C — Cascade Band Touch (G0b context)

**HTF context:** H4 is in SQZ or shrink. M30 is also SQZ. M15/M5 in shrink. Price approaching the outer band of the highest active shrink TF. This is the "HTF compressing → range bounce" pattern.

**What you see:**
- H1/M30 in SQZ (400-499) — bands extremely flat
- M15/M5 in shrink (513/523) — bands converging
- Price approaching the outer edge of the highest shrink TF's band
- Gate labels: `[G0b-TOUCH]` (lime/orange) or `[G0b-WAIT]` (yellow)

**Pink zone — exit immediately:**
- M15 SQZ + M30 SQZ simultaneously → `[G0b-PINK]` → exit all, no entries

**Cascade entry filters (all must pass before touch fires):**

| Filter | Block condition |
|--------|----------------|
| G0b-H4OPP | H4 fly/shrink opposing entry direction |
| G0b-M30OPP | M30 fly/shrink/SQZ with opposing mid |
| G0b-SQZLOCK | H1+M30 both SQZ, both mid==3 (no conviction) |
| G0b-H1SQZDN | H1-SQZ with mid=2/4 vs BUY, or mid=5 vs SELL |
| G0b-M5OPP | M5 sole trigger + M5 shrink with opposing mid |
| G0b-M5FLY | M5 in committed opposing fly when higher TF triggers |

**Trade action:**
```
WAIT: no touch yet → [G0b-WAIT]
BUY:  lower band touch, all filters pass → [G0b-TOUCH] act=1
SELL: upper band touch, all filters pass → [G0b-TOUCH] act=2
EXIT ALL: M15+M30 both SQZ → [G0b-PINK] act=7 + cooldown
SIZE: quality score from M5 transition
```

---

## Scenario D — Fly → Shrink → Fly (Rest Pattern)

![Fly to Shrink to Fly](./Backtest_data/extras/backtested_EA_fly_2_shrink_2_fly.jpg)
![Fly to Shrink to Fly zoom](./Backtest_data/extras/backtested_EA_fly_2_shrink_2_fly_zoomin.jpg)

**HTF context:** W1/D1 remain in fly throughout. H4 also stays in fly. Only M30/M15/M5 briefly compress. The macro tailwind (H4 fly) guarantees fly resumes.

**What you see:**
- H1 (red) and H4 (yellow) never reverse their stepping structure
- White rectangles: M30/M15/M5 briefly compress then re-expand in the same direction
- After each rectangle: full fly resumes, all bands fan back out

**Key test — rest vs reversal:** H1 (red) maintains its step direction throughout. If H1 never breaks, this is a rest pattern. If H1 reverses direction, it is a true reversal.

**Zones in the zoom:**
- Yellow (left): initial fly — all bands expanding
- Red (center): M30/M15 shrink; H4 step unchanged
- Purple/magenta: brief SQZ — `[G6-LOAD]` logging; wait for M5 break
- White (right): fly resumes — M5 SQZ break → `[G6-BUY]` → M15/M30 follow

**Trade action:**
```
DURING shrink: enter on M5 FLAT→UP/DN via shrink path (G6-BUY/SELL)
DO NOT wait for all TFs to re-align — M5 SQZ break IS the entry
TARGET: resume toward H4 outer band (H4 fly context)
EXIT: ATRSL stop | M5 UP→FLAT (G5-FADE) | M30+M15 go sideway
```

---

## Scenario E — Shrink → SQZ (All TFs Compressing)

![Shrink to sideway](./Backtest_data/extras/backtested_EA_fly_shrink_2_sideway.jpg)
![Shrink to sideway zoom](./Backtest_data/extras/backtested_EA_fly_shrink_2_sideway_zoomin.jpg)

**HTF context:** H4 is shrinking or in SQZ. D1 is also slowing. The macro is losing conviction — this is WHY all lower TFs are going flat. Price is ranging because H4 cannot provide a clear outer band target.

**What you see:**
- M5/M15/M30 bands collapsed to near-flat horizontal lines — barely any gap between upper and lower
- Mid-band labels (3, 4, 5) appear on multiple TFs at once
- H1/H4 also flat or slowly stepping
- Gate labels: `[G0c-SQZLOCK]` (magenta), `[G0b-SQZLOCK]` (magenta), `[G6-LOAD]` (gold)

**Why each zone is ranging (from zoom, Jan 13–15):**
- **H1 sideway** (Jan 13): H4 is still fly → price tries H4 midband; trade follows M5 up toward H4 midband
- **M30/M15 fly down + H1 shrink** (Jan 14 12:20): H1 compressing → M30 range widens to H1 band boundaries
- **Touch H1 lower** (Jan 14 15:30): Price reaches H1 lower band → bounces up toward H1 upper (range trade within H1 band)
- **H1 fly down → H4 shrink** (Jan 14 20:50–Jan 15 05:50): H4 starts shrinking → H1 range confined within H4 band
- **H4 sideway** (Jan 15 11:10): H4 SQZ → range trade between H1 upper and H1 lower
- **Pink zone** (Jan 15 19:10): M15+M5 both sideway → exit all

**Trade action:**
```
WAIT:     M30+M15 both SQZ → G0c-SQZLOCK → no entry
WAIT:     H1+M30 both SQZ, both mid==3 → G0b-SQZLOCK → no entry
RANGE:    H4 sideway → sell at H1 upper touch, buy at H1 lower touch
EXIT ALL: M15+M5 both sideway → G0b-PINK → act=7
EXIT ALL: M30+M15+H1 all mid≥3 → G0 → act=7
```

---

## Scenario F — SQZ → Fly (Breakout)

![Sideway to fly](./Backtest_data/extras/backtested_EA_sideway_2_fly.jpg)
![Sideway to fly zoom](./Backtest_data/extras/backtested_EA_sideway_2_fly_zoomin.jpg)

**HTF context:** D1 and H4 are about to exit SQZ — the HTF breakout pulls M30/M15/M5 along. Watch the D1 direction (magenta) for the breakout direction.

**What you see:**
- All TF bands collapsed to a tight bundle — pure SQZ state
- M5 stage labels showing 400–499; no directional labels
- Gate labels: `[G6-LOAD]` (gold) or `[G0c-SQZLOCK]` (magenta)
- **Transition:** M5 (aqua) bands begin spreading first → `REVUP` or `REVDN` label fires
- M15 follows M5 with ~2–5 bar lag; then M30, then H1

**What it means:**
- SQZ loading phase complete; momentum building from fastest TF up
- L2H chain building: M5 fly → M15 fly → M30 fly
- D1 fly direction = which way the breakout will sustain

**Trade action:**
```
DURING SQZ: no entry — [G6-LOAD] confirms wait state
ENTRY: M5 SQZ break (400-499 → 511/512 or 521/522) + REVUP/REVDN → quality=75
M15 pioneer: M30 still SQZ, M15 breaks → pioneer entry 0.75×
FULL ENTRY: M30+M15 both confirm fly → 1.0×
EXIT: ATRSL trailing stop | M5 UP→FLAT (G5-FADE)
TARGET: H4 outer band (if H4 also breaking) → D1 outer band
```

---

## Scenario G — All TFs Sideway (G0 Exit)

**HTF context:** H4 SQZ or flat, D1 flat — no macro direction. Any open position must close immediately.

**What you see:**
- Mid-band labels (3, 4, 5) visible on M30 AND M15 at the same time
- All bands flat — no directional expansion
- Gate label `[G0]` (crimson) or `[G0-HOLD]` (dimgray)

**Trade action:**
```
M30 mid≥3 AND M15 mid≥3 AND H1 mid≥3  →  [G0]      act=7  exit all immediately
M30 mid≥3 AND M15 mid≥3, H1 mid<3     →  [G0-HOLD] act=0  hold existing, no new entry
Recovery: wait until M30 or M15 shows mid=1 or mid=2 again
```

---

---

# PART 4 — TRADE DECISION QUICK REFERENCE

First establish HTF context (Part 2), then apply this table:

## HTF Context → MTF Trade Quality

| W1 | D1 | H4 | MTF Trade Quality | MTF Target |
|----|----|----|-------------------|------------|
| 511/512 BUY | 511/512 BUY | 511/512 BUY | Full quality 1.0× — hold longs | H4 outer → D1 outer |
| 511/512 BUY | 511/512 BUY | 513 shrink | Reduced quality 0.75× — shorter BUY | H4 outer band boundary |
| 511/512 BUY | 511/512 BUY | 400-499 SQZ | Weak — G0b cascade only; require M5 confirm | H4 band range |
| 511/512 BUY | 521/522 SELL | Any | Counter-trend — smaller size, fast exit | D1 pullback target |
| Any | Any | 521/522 SELL | SELL backed by H4 | H4 lower band |
| 400-499 | 400-499 | 400-499 | No trade — full macro SQZ | Wait for breakout |

## Scenario → Action Table

| What you see | Scenario | Action | Gate |
|---|---|---|---|
| H1+M30+M15 all 511/512, mid=1 | Normal fly BUY | Enter on M5 FLAT→UP | G6-BUY |
| H1+M30+M15 all 521/522, mid=2 | Normal fly SELL | Enter on M5 FLAT→DN | G6-SELL |
| H1/M30 in fly, M15/M5 shrinking | Fly→Shrink BUY/SELL | Enter on M5 FLAT→UP/DN | G6-BUY/SELL |
| Only M5 shrinking, M15 still fly | M5 noise | **Wait** — not yet | — |
| H1+M30 SQZ, M15/M5 shrink, band touch | Cascade | Enter at outer band touch | G0b-TOUCH |
| M15+M30 both SQZ | Pink zone | **Exit all** | G0b-PINK |
| M5 fading (UP→FLAT or DN→FLAT) | Fade | Exit open position | G5-FADE |
| All TFs SQZ | Full lock | **Wait** for breakout | G0c/G6-LOAD |
| M5 breaks SQZ → REVUP/REVDN | Breakout | Enter quality=75 | G6-ENTRY |
| M30 mid≥3 AND M15 mid≥3, H1 trending | Near-G0 | Hold, no new entry | G0-HOLD |
| M30 mid≥3 AND M15 mid≥3, H1 sideway | G0 | **Exit all** | G0 |
| H4 fly opposing direction | H4 filter | Block | H4-OPPOSE |
| Float loss < −$50 | Emergency | Exit immediately | G0e-MAXLOSS |
| Price touches outer band of lowest fly TF (all below compressed) | Cascade target hit | Exit (auto) | G8-BNDTGT |

## Cascading Price Targets

When TFs compress bottom-up, price gravitates to the outer band of the **lowest TF still in fly**.

| Lowest TF still in fly | WHY it is lowest | Price target | Exit |
|---|---|---|---|
| H4 (M30/M15/M5/H1 all below) | D1 fly still providing H4 target | D1 outer band | D1 starts shrinking |
| H1 (M30/M15/M5 compressed) | H4 shrink forcing H1 range | H4 outer band | G0-HOLD or G8-BNDTGT |
| M30 (M15+M5 compressed) | H1 shrink forcing M30 range | H1 outer band | G8-BNDTGT |
| M15 (M5 compressed) | M30 shrink forcing M15 range | M30 outer band | G8-BNDTGT |
| M5 only fly | M15+ still fly — M5 is noise | Not applicable | Wait for M15 to confirm |
| All sideway | H4 SQZ — no macro target | None | G0 → exit all |

**Rules:**
1. Only M5 sideway → wait; M5 alone is noise within M30/H1 fly
2. Target = outer band of lowest still-flying TF (upper for BUY, lower for SELL)
3. HTF is why lower TF goes sideway: H4 SQZ → M30 flat; H4 shrink → M30 ranges within H4 band
4. G8-BNDTGT fires automatically at target band touch when all lower TFs are compressed

---

---

# PART 5 — ANALYSIS WORKFLOW

Apply these steps in order for any attached chart image.

**Step 1 — HTF first: W1 → D1 → H4**
- W1 direction? (fly BUY/SELL / shrink / SQZ)
- D1 direction? Same as W1 = aligned; opposite = counter-trend
- H4 stage? → determines M30 trade target and duration
- What is the current HTF price target for M30 trades?

**Step 2 — Identify each band**
Map colors to TFs (Section 2). Which bands are wide (fly) vs narrow (shrink/SQZ)?

**Step 3 — Build regime table**
```
W1: ___ | D1: ___ | H4: ___ | H1: ___ | M30: ___ | M15: ___ | M5: ___
```

**Step 4 — Read middle band labels**
Note values 3/4/5 and REVUP/REVDN flags. Flat labels = that TF is ranging. Ask: which HTF is causing this lower TF to be flat?

**Step 5 — Read ATRSL state**
dir=0 (orange below price) = uptrend stop. dir=1 (orange above) = downtrend stop.

**Step 6 — Read gate labels**
List visible tags with bar position. Match color to meaning (Part 1 Section 6).

**Step 7 — Match scenario**
Using regime table from Step 3:
- All mid TFs fly same direction → Scenario A
- HTF fly, inner TFs shrinking → Scenario B
- HTF SQZ, inner TFs shrinking, band touch → Scenario C
- HTF fly, inner TFs rest then resume → Scenario D
- All TFs compressing / ranging → Scenario E
- All TFs SQZ, about to break → Scenario F
- M30+M15 mid both ≥ 3 → Scenario G

**Step 8 — Apply trade decision**
Use Part 4 tables. State: current regime, price target, which gate fires next, open position status.

---

---

# PART 6 — COMMON MISREADS

| Misread | Correct interpretation |
|---------|----------------------|
| "M30 is sideway for no reason" | Check H4 — if H4 is SQZ/shrink, that is WHY M30 is flat. M30 range = H4 band range |
| "Trade stopped at random level" | Check if that level is H4 outer band or D1 outer band — it is a cascade price target |
| Brief M5 SQZ during H1 fly | Noise — M30 midtrend is still primary; do not exit |
| Both H4 and W1 look yellow | H4 is saturated yellow and narrower; W1 is pale near-white cyan and the widest band |
| No mid label visible | BB_diffMid_Trend is 1 or 2 (trending) — labels suppressed; check upper label direction |
| REVUP/REVDN label | Midtrend flipped THIS bar — transition event, not stable state yet |
| DimGray gate label near trade | Block gate fired — trade was NOT taken at this bar |
| DarkOrange gate label | H4 macro filter blocked (H4-OPPOSE/H4-SQZ/G0b-H4OPP) |
| Fly→Shrink vs Fly→Reversal | Check H1/H4: maintain step direction → rest pattern (D); break step → reversal |
| M5 sideway during HTF fly | M5 noise — wait for M15 to also shrink before entering |
| Cascade BUY with M5 in 521/522 | G0b-M5FLY blocks this — M5 committed opposing fly contradicts cascade direction |
| "Why did BUY stop here?" | Price hit H4 outer band during H4 shrink — G8-BNDTGT fired as expected cascade target |
