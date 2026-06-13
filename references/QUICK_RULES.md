# QUICK_RULES — derived from backtest_chart_analysis.md
# ⚠ THIS FILE IS DERIVED. NEVER EDIT DIRECTLY.
# Every edit to a normative table in backtest_chart_analysis.md MUST
# regenerate the corresponding section here IN THE SAME COMMIT.
# Master version: 076c0c0

## 1. Variables  [master: Part 1 §2-§4b, §12]

### BBW_stage

| Code | Name | What you see | Trade Bias |
|------|------|-------------|------------|
| 511 | FLY++ bullish expand | Bands fanning out upward, all 3 rising | BUY |
| 512 | FLY+- parallel up | All bands rising together in parallel | BUY |
| 521 | FLY++ bearish expand | Bands fanning out downward | SELL |
| 522 | FLY-+ parallel down | All bands falling in parallel | SELL |
| 513 | FLY-- bullish shrink | Upper band curling down, lower band still rising | WATCH → use M5 |
| 523 | FLY-- bearish shrink | Upper still rising, lower curling down | WATCH → use M5 |
| 400–499 | SQZ | Bands extremely tight and flat | WAIT |

### diffMid_Trend

| Value | Name | Visual | Label shown? |
|-------|------|--------|-------------|
| 1 | Uptrend | Midband rising | No |
| 2 | Downtrend | Midband falling | No |
| 3 | Sideways | Midband flat | Yes |
| 4 | Sideway downtrend | Midband flat, slight downward bias | Yes |
| 5 | Sideway uptrend | Midband flat, slight upward bias | Yes |

- `REVUP` = midtrend just flipped from 2 → uptrend reversal this bar
- `REVDN` = midtrend just flipped from 1 → downtrend reversal this bar

### BBUpDn_state

**BBUpDn_state measures band movement direction — NOT price location:**
- 0 = no_state (SQZ or transitional)
- 1 = expanding (upper rising AND lower falling — confirmed 2 bars)
- 2 = shrinking (upper falling AND lower rising — confirmed 2 bars)
- 3 = up (both bands moving upward together)
- 4 = dn (both bands moving downward together)

### PriceLoc

above_upper / at_upper / inside / at_mid / at_lower / below_lower

### diffBBW

| diffBBW value | Meaning | BBW_stage relationship |
|---------------|---------|----------------------|
| Positive and increasing | Band actively expanding — fly has momentum | Consistent with 511/521 (FLY++) |
| Positive and decreasing | Fly expanding but slowing — watch for shrink | Transitioning 511→512 or 511→513 |
| Near zero | Band width stable — parallel fly or SQZ | Consistent with 512/522 or 400-499 |
| Negative and decreasing | Band actively shrinking — compression accelerating | Consistent with 513/523 (FLY--) |
| Negative and increasing | Shrinking slowing — about to stabilize or reverse | Transitioning 513→512 or 513→511 |

Visible in EA logs as `diffBBW_M15`, `diffBBW_M30` etc.

### Priority Rule

When BBW_stage conflicts with diffMid_Trend or diffBBW, the scenario MUST be
identified from diffBBW + diffMid_Trend. BBW_stage is a 3-bar lagging label and
is confirmation only — never the primary input.

Priority: diffBBW (fastest) > diffMid_Trend > BBW_stage (slowest).

This applies to every scenario table in Part 3 and every gate/condition in Part 5.

## 2. Log Decoders  [master: §12b, §12c, §12d]

### TRADEINFO Flag Table

| Flag | Active (≥0) meaning | Cascade mapping | When you see it |
|------|--------------------|-----------------|-----------------|
| H2L_flyUP | HTF→LTF fly uptrend chain confirmed | Expansion confirmed top-down — all TFs aligned UP | Scenario A (full fly up) |
| H2L_flyDN | HTF→LTF fly downtrend chain confirmed | Expansion confirmed top-down — all TFs aligned DN | Scenario A (full fly dn) |
| H2L_flyStrink | HTF→LTF shrink chain active | Shrink propagating — compression cascade in progress | Scenario B/E (compression) |
| H2L_sideway | HTF→LTF sideway/SQZ chain | All TFs suppressed — compression complete | Scenario E4/H (BOTTOM) |
| L2H_flyUP | LTF→HTF fly uptrend chain (bottom-up) | LTF leading expansion upward — D2 initiated | Scenario D/F (expansion up) |
| L2H_flyDN | LTF→HTF fly downtrend chain (bottom-up) | LTF leading expansion downward — D2 initiated | Scenario D/F (expansion dn) |
| L2H_sideway | LTF→HTF sideway chain | LTF being suppressed by HTF — D1 active | Scenario B/E (LTF confined) |
| All = -1 | No chains detected | Mixed/neutral — transitional state | Scenario H (direction pivot) |

### TF Index Reference

| Index | Timeframe |
|-------|-----------|
| 0 | M5 |
| 1 | M15 |
| 2 | M30 |
| 3 | H1 |
| 4 | H4 |
| 5 | D1 |

### TRADEINFO Scenario Identification

| TRADEINFO state | Scenario | Trade implication |
|----------------|----------|-------------------|
| `H2L_flyUP:0` + `L2H_flyUP:3` | A — Full fly alignment (up) | Full size trend entry BUY |
| `H2L_flyDN:0` + `L2H_flyDN:3` | A — Full fly alignment (dn) | Full size trend entry SELL |
| `H2L_flyStrink:1` + `L2H_sideway:1` | B1 — M15 shrink only | Reduce to 0.75×, watch depth |
| `H2L_flyStrink:2` + `L2H_sideway:2` | B2 — M30 shrink | Reduce to 0.50×, watch H1 |
| `H2L_flyStrink:3` + `L2H_sideway:3` | B3 — H1 shrink | Reduce to 0.25×, watch H4 |
| `H2L_sideway:1` + `L2H_sideway:1` | E1/E2 — Deep compression | No entry — G0b-PINK may fire |
| `H2L_sideway:3` + all L2H = -1 | E4/H — BOTTOM | No entry — wait M5 BBUpDn 0→1 |
| All flags = -1 | H — Direction pivot (transitional) | No entry — direction unknown |
| `L2H_flyUP:1` + `H2L_flyStrink:3` | D1/F1 — LTF leading, HTF not confirmed | ARM — wait M30 confirm |
| `L2H_flyUP:2` + `H2L_flyStrink:3` or clearing | D2/F2 — MTF confirmed | ENTER — 0.75× |
| `L2H_flyUP:3` + `H2L_flyUP:0` | D3/F3 — Full chain restored | → Scenario A, full size |
| `L2H_flyDN:1` + `H2L_flyUP:3` (opposing) | C1 — MTF reversal only | Small entry 0.25× — wait H4 |
| `L2H_flyDN:3` + `H2L_flyDN:0` | C2 — H4 confirmed reversal | → New Scenario A opposite dir |

### BBTFImpact Flags

| Flag | Format | Active (=1) meaning | Cascade mapping |
|------|--------|--------------------|--------------------|
| HTF_Drive_LTF_Sideway | [TF_name_index] | TF at that index being pushed into sideways by higher TFs | Shrink/confinement active at this TF level |
| LTF_Drive_HTF_Fly | [TF_name_index] | TF at that index showing fly energy despite HTF pressure | Expansion energy building at this TF level |

### B Sub-Scenario Mapping

| BBTFImpact pattern | Scenario | Size multiplier |
|-------------------|----------|----------------|
| `HTF_Drive_LTF_Sideway:[M15_1]` only | B1 — M15 shrink only | 0.75× |
| `HTF_Drive_LTF_Sideway:[M15_1, M30_1]` | B2 — M30 shrink | 0.50× |
| `HTF_Drive_LTF_Sideway:[M15_1, M30_1, H1_1]` | B3 — H1 shrink | 0.25× |
| `HTF_Drive_LTF_Sideway:[M15_1, M30_1, H1_1, H4_1]` | E4 — H4 also compressing | No entry |

**Conflict state:** Both `HTF_Drive_LTF_Sideway` and `LTF_Drive_HTF_Fly` active simultaneously at a TF = volatile transition (E3 or H). sizeMultiplier = 0.5. Watch M5 BBUpDn_state: 0→1 resolves the conflict in favour of expansion.

### cas_shrinkTF

| cas_shrinkTF | Meaning | Scenario sub-state | Reversal probability |
|-------------|---------|-------------------|---------------------|
| 1 | M15 is highest active shrink TF | B1 — Shallow compression | Low |
| 2 | M30 is highest shrink TF | B2 — Moderate compression | Low-Medium |
| 3 | H1 is highest shrink TF | B3 — Deep compression | Medium |
| 4 | H4 is highest shrink TF | E4 — HTF also compressing | High |
| 5 | D1 is highest shrink TF | Scenario I — Macro sideways | Very high |
| -1 | No TF in fly_shrink | Not in B — check E/H or A | Depends on other flags |

### cas_sqzCount

| cas_sqzCount | Meaning | Scenario sub-state | Gate status |
|-------------|---------|-------------------|------------|
| 0 | No TFs in SQZ | B (shallow compression) — shrink only | Normal gates |
| 1 | One TF squeezed (typically M5 first) | E1 — LTF partial SQZ | G0c-SQZLOCK may activate |
| 2 | Two TFs squeezed (M5+M15) | E2 — LTF full SQZ | G0b-PINK fires — EXIT all |
| 3 | Three TFs squeezed (M5+M15+M30) | E3/E4 — Deep cascade | G0b-PINK + G0c-SQZLOCK |
| 4+ | Four or more TFs squeezed | E4/H — BOTTOM | All gates locked — wait |

### Combined cas_shrinkTF × cas_sqzCount

| cas_shrinkTF | cas_sqzCount | Full state | Scenario | Action |
|-------------|-------------|-----------|----------|--------|
| 1 | 0 | M15 shrink, nothing squeezed | B1 | Trade at 0.75× |
| 2 | 0 | M30 shrink, nothing squeezed | B2 early | Trade at 0.50× |
| 2 | 1 | M30 shrink, M5 squeezed | B2 late → E1 | Reduce to 0.25× |
| 3 | 1 | H1 shrink, M5 squeezed | B3 → E1 | Reduce to 0.25× |
| 3 | 2 | H1 shrink, M5+M15 squeezed | E2 | EXIT — G0b-PINK |
| -1 | 2 | No shrink but 2 TFs squeezed | E2/E3 transition | Wait — G6-LOAD may fire |
| -1 | 3+ | No shrink, 3+ TFs squeezed | E4/H — BOTTOM | No entry — wait M5 expand |
| -1 | 0 | No shrink, no squeeze | A (fly) or transition | Check TRADEINFO for direction |

### Journal Log Labels

| Log label | Meaning | Scenario sub-state | Action |
|-----------|---------|-------------------|--------|
| `MIDLINE_SQZ_LOADING` | M5 in SQZ, M30 shrinking — loading state | E3 — Loading | Wait — G6-LOAD about to fire |
| `MIDLINE_SQZ_ENTRY` | Loading complete — entry condition met | E3→D/F transition | ENTER on next bar |
| `SQZ_BREAK_UP` | M5 broke SQZ bullish — expansion initiated upward | D1 or F1 initiating BUY | ARM — wait M15 confirm |
| `SQZ_BREAK_DN` | M5 broke SQZ bearish — expansion initiated downward | D1 or F1 initiating SELL | ARM — wait M15 confirm |
| `CASCADE_TOUCH(TF:n upper_band)` | G0b-TOUCH fired at TF index n, upper band | Confinement boundary reached | Check G0b 6 filters |
| `CASCADE_TOUCH(TF:n lower_band)` | G0b-TOUCH fired at TF index n, lower band | Confinement boundary reached | Check G0b 6 filters |
| `CASCADE_PINK_ZONE` | G0b-PINK fired — M15+M30 both SQZ | E2 — Pink zone active | EXIT all — no entries |

**Pink zone condition:** cas_sqzCount ≥ 2 AND M15+M30 both SQZ simultaneously → G0b-PINK fires → EXIT all. This maps to E2 (LTF full SQZ) or deeper.
**Pink Pair Rule:** pink = M15 BBW 400-499 AND M30 BBW 400-499 simultaneously — NEVER cas_sqzCount alone (sqzCount=2 can be H1+M30).

## 3. CHECK HTF FIRST  [master: §12 Compression — Check HTF First]

### H4 × D1 State Matrix

| H4 state | D1 state | LTF shrink meaning | Scenario path | Reversal probability |
|----------|----------|-------------------|---------------|---------------------|
| Fly (511/512) | Fly (511/512) | REST — internal LTF pullback, HTF intact | B→D (rest recovery) | Low |
| Shrink (513) | Fly (511/512) | CONFINED — H4 caused LTF compression, D1 may rescue | B→E (deep compression) | Medium |
| Shrink (513) | Shrink (513) | REVERSAL WARNING — both HTF losing direction | B→E→E4 (HTF reversal) | High |
| SQZ (400-499) | Fly (511/512) | BOTTOM with D1 bias — old H4 trend exhausted | E4→H (direction pivot, D1 gives bias) | High for H4, low for macro |
| SQZ (400-499) | Shrink/SQZ | DEEP BOTTOM — no macro bias exists | E4→H (direction pivot, no bias) | Very high — full reversal |

### Reversal Probability Ladder

| Depth reached | Reversal probability | Scenario |
|---------------|---------------------|----------|
| M15 only (H4 still fly) | Low — likely rest/continuation | B1 |
| M30 added (H4 still fly) | Low-Medium — watch H1 | B2 |
| H1 added (H4 still fly) | Medium — H4 likely to follow | B3 |
| H4 enters shrink (D1 still fly) | High — HTF reversal warning | E/E4 |
| H4 SQZ + D1 still fly | High for H4, D1 gives bias | H (D1 bias) |
| H4 SQZ + D1 shrink/SQZ | Very high — full macro reversal | H (no bias) |

### HTF vs LTF First Discriminator

- If H4 entered shrink BEFORE M15 → H4 is the cause → confinement (check D1 for rescue)
- If M15 entered shrink BEFORE H4 → LTF is warning → watch if H4 follows (reversal ladder)
- If both entered shrink simultaneously → strong reversal signal

## 4. Scenario Identification  [master: Part 3]

| Sub | Tier | Identification condition (TF states) | Next |
|-----|------|-------------------------------------|------|
| A1 | 1 | W1+D1+H4 all 511/512, H1+M30 511/512, M15+M5 511/512 | → B when M15 enters 513 |
| A2 | 1 | H4 511/512 fly but W1 or D1 counter-trend, H1+M30 511/512, M15+M5 511/512 | → B when M15 enters 513 |
| A3 | 1 | H4+D1+W1 all 511/512, H1+M30 511/512, M15 513/523 briefly or M5 400-499 briefly | → B if M15 513 sustains |
| B1 | 2 | D1+H4+H1+M30 all 511/512, M15 513/523, M5 511/512 | → E if M30 also 513, → D if M5 breaks SQZ same dir |
| B2 | 2 | D1+H4+H1 all 511/512, M30 513/523, M15 513/523, M5 511/512 | → E if H1 also 513, → D if M5 breaks SQZ same dir |
| B3 | 2 | D1+H4 511/512, H1 513/523, M30+M15 513/523, M5 511/512 | → E if H4 also 513, → D if M5 breaks SQZ same dir |
| E1 | 2 | H4 511/512, H1 511/512 or 513, M30 513/523 (BBUpDn=2), M15 400-499, M5 400-499 | → E2 if M30 SQZ, → E3 if M5 BBUpDn 0→1 |
| E2 | 2 | H4 511/512, H1 511/512 or 513, M30 400-499 (BBUpDn=0), M15 400-499, M5 400-499 | → E3 if M5 BBUpDn 0→1, → E4 if H4 400-499 |
| E3 | 2 | H4 511/512, H1 511/512, M30 513/523 (BBUpDn 2→1), M15 513, M5 breaking SQZ | → D/F if M15 mid confirms, → E4 if H4 compresses |
| E4 | 2 | H4 513/523 or 400-499, H1 400-499, M30 400-499, M15 400-499, M5 400-499 | → H (direction pivot) |
| H1 | 2 | D1 511/512, H4 breaking SQZ (BBUpDn 0→1 same dir as D1 mid) | → F (compression release) |
| H2 | 2 | D1 511/512, H4 breaking SQZ (BBUpDn 0→4 opposite D1 mid) | → C (trend reversal) |
| H3 | 2 | H4 BBUpDn 1→0 reverts within 3 bars | → back to E/H |
| H4 | 2 | H4 SQZ, BBUpDn alternating 1 and 4 | → Phase 6 if persists |
| D1 | 3 | H4 511/512, H1 511/512, M30/M15 513/523 or 400-499, M5 breaking SQZ | → D2 if M15 mid confirms |
| D2 | 3 | H4 511/512, H1 511/512, M30 511/512 or 513, M15 FLAT→UP/DN, M5 511/512 | → D3 if M30 511/512 |
| D3 | 3 | H4+H1+M30+M15+M5 all 511/512 | → A (full fly) |
| F1 | 3 | H4 400-499 or 513, H1 513 or 400-499, M30 513 or 400-499, M15 511/512, M5 511/512 | → F2 if M30 511/512, WAIT (quality capped) |
| F2 | 3 | H4 400-499 or 513, H1 511/512, M30 511/512, M15 511/512, M5 511/512 | → F3 if H4 511/512 |
| F3 | 3 | H4+H1+M30+M15+M5 all 511/512 (new direction) | → A (full fly) |
| C1 | 3 | H4 511/512 or 513 (original dir), H1+M30+M15 reversed 521/522 | → C2 if H4 flips new dir, WAIT |
| C2 | 3 | H4 flipped new direction 511/512, all TFs new direction | → new A (full fly) |
| C3 | 3 | H4 reversed but W1/D1 still original direction | → C2 if D1 also reverses |

**Cycle sequence:**
```
A → B → E → E4 → H → F → A       (continuation — same direction)
A → B → E → E4 → H → C → A       (reversal — new direction)
A → B → D → A                     (rest — short cycle, shallow D1 only)
H3 false breakout → back to H/E   (failed breakout)
```

## 5. Phase Identification  [master: §13]

### Zigzag Amplitude Decay = diffBBW Made Visual

| Amplitude behavior | diffBBW | Shrink type | Phase | Scenario path |
|-------------------|---------|-------------|-------|---------------|
| No zigzag — directional trend | Positive | No shrink | Phase 1 | A — hold until M15 enters 513 |
| Equal-height legs (no decay) — before SQZ | ≈ zero | Parallel fly, no narrowing | Phase 2 onset | A2 or I (macro sideways) |
| Symmetric decay — both sides equal | Negative | H4 mid=3 sideways shrink | Phase 3a | B→E — trade both directions equally |
| Asymmetric decay — one side drops first (INTO) | Negative | H4 mid≠3 trending shrink | Phase 3b-INTO | B→E — favour trending side |
| Asymmetric gain — one side rises (OUT) | Near zero→positive | H4 recovering from SQZ | Phase 3b-OUT | Counter-trend recovery — 0.50× max |
| Collapsed to noise (no legs) | ≈ zero at minimum | SQZ confirmed | Phase 4 | E2/E3→H — wait for direction |
| Explosive one-direction breakout | Positive sharply | SQZ break — committed | Phase 5 | H→F or C — enter on M15 confirm |
| Equal-height legs (no decay) — AFTER SQZ | Alternating pos↔neg | H4 cycling fly→SQZ→fly | Phase 6 | H4 whipsaw — 0.25× at H4 boundaries |

### 3a vs 3b Discriminator

| H4 diffMid_Trend | Phase | Pattern | Oscillation center |
|-------------------|-------|---------|-------------------|
| 3 (sideways, no lean) | 3a — Symmetric Tightening | Both ceiling and floor close in equally | Centered around H4 mid |
| 1 or 5 (uptrend / sideway-up) | 3b — Asymmetric Cascade (BUY) | UP targets drop progressively, DN targets hold at H4 mid then break | Biased above H4 mid initially |
| 2 or 4 (downtrend / sideway-dn) | 3b — Asymmetric Cascade (SELL) | DN targets rise progressively, UP targets hold at H4 mid then break | Biased below H4 mid initially |

### Phase 6 vs Phase 2 Discriminator

- Preceded by Phase 1 (directional trend) → Phase 2 (pre-compression zigzag beginning)
- Preceded by Phase 4/5 (SQZ/breakout) → Phase 6 (post-compression oscillation)
- Phase 2: H4 BBW_stage = stable 511/512 (sustained fly) → Phase 2
- Phase 6: H4 BBW_stage = cycling 511→513→400-499→511 → Phase 6

### 3b-INTO vs 3b-OUT Discriminator

- H4 entering shrink (BBUpDn 1→2) + legs LOSING reach = Phase 3b-INTO (normal)
- H4 exiting SQZ (BBUpDn 0→1) + legs GAINING reach = Phase 3b-OUT (recovery)

## 6. Prediction  [master: Part 4 Rules 1-5]

### Rule 1 — Direction by Phase

| Current phase | CHECK HTF result | Predicted direction | Confidence |
|---|---|---|---|
| Phase 1 (directional trend) | H4 fly + D1 fly same direction | Continue same direction | High |
| Phase 2 (zigzag onset) | H4 fly + D1 fly same direction | Each leg: M30 fly direction. Overall bias: H4 direction | Medium per leg |
| Phase 3a (symmetric decay) | H4 shrink + H4 mid=3 | Next leg: opposite to current leg. Overall: UNKNOWN | Low |
| Phase 3b-INTO (trending shrink) | H4 shrink + H4 mid=1/5 or 2/4 | Next leg: opposite. Overall: trending side favoured while H4 mid ≠ 3 | Medium for trending side |
| Phase 3b-OUT (recovery) | H4 exiting SQZ + D1 opposing | Recovery direction — until D1 confinement boundary reached | Medium |
| Phase 4 (compressed oscillation) | H4 SQZ | UNKNOWN — direction not determinable. Wait for M5 BBUpDn 0→1 | None — do not predict |
| Phase 5 (explosive breakout) | H4 breaking SQZ | Direction of M5 expansion. CHECK D1 for alignment | Medium → High as TFs confirm |
| Phase 6 (post-SQZ oscillation) | H4 cycling fly→SQZ→fly | Next leg: opposite to current. Overall: D1 direction eventually | Low per leg, Medium overall |

### Rule 2 — Target by Scenario

| Scenario | UP target | DN target | Target TF (confinement) |
|---|---|---|---|
| A (full fly) | D1 outer band (furthest target) | Brief pullback to M30 mid then resume | D1 — highest confinement |
| B1 (M15 shrink) | M30 outer band | M30 mid or M30 lower | M30 — highest still-flying MTF |
| B2 (M30 shrink) | H1 outer band | H1 mid or H1 lower | H1 — highest still-flying MTF |
| B3 (H1 shrink) | H4 outer band | H4 mid or H4 lower | H4 — confinement ceiling |
| E1-E3 (deep compression) | H4 outer band (confined) | H4 lower band | H4 — hard ceiling/floor |
| E4 (H4 compressing) | D1 mid or D1 outer band | D1 lower band | D1 — next level up |
| H (direction pivot) | Unknown until M5 breaks SQZ | Unknown until M5 breaks SQZ | Wait — no target yet |
| D1 (M5 break) | M30 outer band (arm — not confirmed) | M30 mid | M30 — wait for confirm |
| D2 (M15 confirm) | H1 outer band → H4 outer band | M30 mid (brief pullback) | Escalates as TFs confirm |
| D3 (MTF re-align) | H4 outer band → D1 outer band | M30 mid | → Scenario A target |
| F1 (LTF only) | M30 outer band (weak — wait) | M15 mid | M30 — not confirmed yet |
| F2 (MTF confirmed) | H4 outer band | M30 mid | H4 — MTF backing the move |
| F3 (HTF confirmed) | D1 outer band (→ Scenario A) | H1 mid | D1 — full fly restored |
| C1 (MTF reversal) | Previous H4 lower (now ceiling) | New H4 outer band (new direction) | H4 — transitioning |
| C2 (H4 confirmed) | New D1 outer band (new direction) | New H4 mid (pullback) | D1 — new trend confirmed |
| C3 (counter-trend) | H4 outer band (limited by W1/D1) | H4 mid | H4 — W1/D1 still opposing |

### Rule 3 — Timeline

| Phase | Leg duration | Full cycle to next phase | diffBBW signal |
|---|---|---|---|
| Phase 1 | Sustained — days to weeks | Until M15 BBW enters 513 (shrink) | diffBBW positive → no end imminent |
| Phase 2 | 4–12 hours per leg | 2–5 days until Phase 3 | diffBBW transitioning positive → near zero |
| Phase 3a | 3–8 hours per leg (shortening) | 1–3 days until Phase 4 | diffBBW negative → more negative = faster compression |
| Phase 3b-INTO | 3–8 hours per leg (shortening) | 1–3 days until Phase 4 | diffBBW negative |
| Phase 3b-OUT | 4–12 hours per leg (lengthening) | 1–5 days until D1 boundary reached | diffBBW near zero → positive (recovering) |
| Phase 4 | No legs — noise oscillation | Hours to 1 day until M5 breaks | diffBBW ≈ zero at minimum (SQZ floor) |
| Phase 5 | Single explosive move — hours | Immediate — one move | diffBBW sharply positive (band expanding fast) |
| Phase 6 | 12–24 hours per leg | Days to weeks until commitment | diffBBW alternating positive ↔ negative each cycle |

### Rule 4 — Next Scenario Edges

| From | CHECK condition | Next |
|------|----------------|------|
| A | M15 enters 513 | B |
| A | M15 stays 511/512 | A continues |
| B | H4 still fly + D1 fly, M5 BBUpDn 0→1 same dir | D (rest recovery) |
| B | H4 entering shrink | E (deep compression) |
| B | H4 already SQZ | H (direction pivot) |
| B | H4 fly, M5 no signal | B continues |
| E | H4 enters SQZ (400-499) | E4 → H |
| E | M5 BBUpDn 0→1 | F1 (LTF breakout) |
| H | H4 BBUpDn=1 sustained 3+ bars, same dir as D1 | F (compression release) |
| H | H4 BBUpDn=1 sustained 3+ bars, opposite D1 | C (trend reversal) |
| H | H4 BBUpDn reverts to 0 within 3 bars | E/H (false breakout) |
| H | H4 BBUpDn alternates 1 and 4 | Phase 6 (whipsaw) |
| H | D1 also shrinking | Scenario I (macro sideways) |
| D | M30 BBUpDn=1 | A (D3 confirmed) |
| D | M15 mid flips back to 3 | B (D stalled) |
| F | H4 BBUpDn=1 sustained | A (F3) |
| F | H4 BBUpDn reverts | E/H (false breakout) |
| C | H4 BBUpDn=1 new direction | new A (C2) |
| C | W1/D1 still original | C3 (counter-trend) |

### Rule 5 — Confidence Matrix

| Confidence level | Conditions | Part 5 size multiplier |
|---|---|---|
| High | H4 fly + D1 fly + same direction + Phase 1 or 2 | 1.0× |
| Medium-High | H4 fly + D1 fly + Phase 3b trending side | 0.75× |
| Medium | M30 confirmed expansion + H4 not opposing | 0.75× |
| Medium-Low | LTF expansion only + H4 still SQZ or shrink | 0.50× |
| Low | Counter-trend to D1 + Phase 3b-OUT or C1 | 0.25× |
| None | Phase 4 (SQZ) or Phase 6 (H4 uncommitted) or H4 whipsaw | 0 (no entry) or 0.25× max |

**Confidence adjustments based on diffBBW:**
- diffBBW strongly positive → confidence +1 level (expansion has momentum)
- diffBBW near zero after negative → confidence +1 (SQZ floor, breakout imminent)
- diffBBW negative and getting more negative → confidence -1 (compression accelerating)
- diffBBW alternating → no adjustment (Phase 6 — direction uncertain)

## 7. Trade Conditions  [master: Part 5 + EDITs V1-V5, W1]

### Entry E1–E6

| ID | Condition name | What must be true | Trigger (what you watch for) | Scenario |
|---|---|---|---|---|
| E1 | Trend entry | H4 fly + D1 fly + M30 fly all same direction | M15 mid flips 3→1 (BUY) or 3→2 (SELL) | A1 |
| E2 | Partial trend entry | H4 fly + M30 fly same direction, W1 or D1 opposing | M15 mid flips 3→1 or 3→2 | A2 |
| E3 | Confinement boundary entry | Highest flying TF has directional lean (mid=4/5), PriceLoc at outer band | M15 mid flips to trade direction + 6 confinement checks pass (see below) | B, E range trade |
| E4 | Expansion arm | H4 fly intact, M30/M15 in SQZ or shrink | M5 BBUpDn transitions 0→1 (expansion begins) | D1, E3, F1 — ARM only, do not enter yet |
| E5 | Expansion entry | M5 BBUpDn=1 confirmed, M30 starting to confirm | M15 mid flips 3→1 or 3→2 (direction confirmed) | D2, F2 |
| E6 | Full confirmation entry | H4 BBUpDn=1 sustained 3+ bars, M30+H1 both expanding | M15 mid confirms same direction | F3, C2 → becomes Scenario A |

### Entry Path Priority by Phase

| Phase | Primary entry path | Secondary | Notes |
|---|---|---|---|
| Phase 1 (trend) | E1/E2 (M15 mid flip) | — | Trend-following entries correct here |
| Phase 2 (zigzag onset) | E3 (boundary touch + lean) | E1 at flip | Legs reverse AT boundaries — enter there |
| Phase 3a (symmetric) | E3 both directions | — | B3 disabled (no H4 direction exists) |
| Phase 3b-INTO | E3 favouring trending side | E5 | Counter-trend side 0.25× max |
| Phase 3b-OUT | E3 recovery side | — | Exit hard at D1 boundary |
| Phase 4 (SQZ) | NONE | — | B2/B4 — wait |
| Phase 5 (breakout) | E5/E6 (transition entries) | — | Transition window IS the signal here |
| Phase 6 (post-SQZ) | E3 at H4 boundary, 0.25× | — | Never hold through reversal |

### 6 Confinement Checks for E3

| Check | What it verifies | Pass condition | Fail = no entry |
|-------|-----------------|---------------|-----------------|
| 1. H4 directional lean | H4 has bias — not pure sideways | H4 diffMid = 4 or 5 (lean exists) | H4 diffMid = 3 → no lean, no entry |
| 2. No SQZ lock | M15 and M30 not both in SQZ | At most ONE of M15/M30 is BBW 400-499 | BOTH M15+M30 BBW 400-499 → SQZ lock |
| 3. M5 direction confirm | M5 agrees with trade direction | M5 diffMid = 1 (for BUY) or 2 (for SELL) | M5 diffMid opposing or 3 → no confirm |
| 4. M30 not opposing | M30 not actively opposing trade | M30 diffMid ≠ opposing direction | M30 diffMid directly opposing → no entry |
| 5. No pink zone | Not in M15+M30 simultaneous SQZ | M15+M30 not both SQZ at same time | Both SQZ simultaneously → exit all |
| 6. Quality threshold | Sufficient signal quality | Quality score ≥ 60 | Quality < 60 → too weak |

### Entry-at-Target Veto

No entry in the direction of a container/target boundary that price is
already touching. If PriceLoc is at/above the container TF upper band, BUY
is forbidden (the X1 target equals the entry price — the trade has no room);
mirror for SELL at the lower band. At a boundary the only valid setups are
the E3 fade (opposite direction, with lean + 6 checks) or WAIT.

### Exit X1–X4

| ID | Condition name | What triggers it | Variable to watch | Applies to |
|---|---|---|---|---|
| X1 | Target reached | Price hits the Part 4 predicted target band | PriceLoc = above_upper or below_lower at target TF | All scenarios |
| X2 | M15 trend fading | M15 loses direction — move exhausted | M15 diffMid flips 1→3 (BUY fading) or 2→3 (SELL fading) | All scenarios |
| X3 | Quality degraded | Signal quality dropped below threshold | Quality score < 60 | F1 (LTF only) |
| X4 | Pink zone — forced exit | M15+M30 both enter SQZ simultaneously | M15 BBW=400-499 AND M30 BBW=400-499 same time | E2, Phase 4 — EXIT ALL |

### Exit Priority by Phase

| Phase | Primary exit | X2 role | Rule |
|---|---|---|---|
| Phase 1 | X2 (trend fade) | Primary | Trend exits on genuine fade |
| Phase 2 / 3a / 3b / 6 | X1 (opposite boundary target) | Failsafe ONLY | Ignore M15 mid=3 wobble unless ANY of: (a) the rung above is cracking — container TF diffBBW ≤ 0 or its mid drifting to 5/4/3; (b) price stalled ≥3 bars short of the X1 target; (c) the target TF band is invalidated. An M15 reversal with the container still committed (diffBBW > 0, mid=1/2, price mid-band) is a pullback (D-rest), not an exit signal. |
| Phase 4 | X4 (pink zone) | — | Forced exit |
| Phase 5 | X1 at escalating targets | Secondary | Hold while diffBBW sharply positive |

### Block B1–B4

| ID | Condition name | What it checks | Variable check | Result | Scenario |
|---|---|---|---|---|---|
| B1 | M15 sideways | M15 has no direction — cannot trigger entry | M15 diffMid ≥ 3 | No NEW entries. Existing position HOLDS if H4/H1 still fly | B, E1, between Phase legs |
| B2 | Pink zone | M15+M30 both SQZ simultaneously | M15 BBW=400-499 AND M30 BBW=400-499 | EXIT ALL positions + no new entries | E2, Phase 4 |
| B3 | H4 opposing | H4 direction opposes trade direction | H4 diffMid = 1 when trying SELL, or 2 when trying BUY | No entry in that direction | C3 counter-trend |
| B4 | Full SQZ | All MTF/LTF in SQZ | cas_sqzCount ≥ 3 | No entries at all — wait for M5 expansion | E4, H |

### B3 Scope Limits

| Condition | Why B3 is invalid | Evidence rule |
|---|---|---|
| H4 diffMid = 3 (sideways) | There is no "opposing" direction — H4 has none. Phase 3a zigzag legs are tradeable BOTH directions | diffMid is primary over BBW_stage |
| H4 diffBBW contradicts H4 BBW_stage (e.g., BBW=521 bearish but diffBBW positive and mid=3) | BBW_stage is lagging — the labelled direction no longer exists | Section 12 priority: diffBBW > diffMid > BBW_stage |
| Phase = 3a, 6 (identified per Section 13) | These phases are defined as both-direction range phases | Phase rules override directional blocks |

### Critical Block Rule — M30 SQZ Alone Is Not a Block

M30 in SQZ (BBW 400-499) → existing trade STAYS OPEN. M30 is compressed but position is managed by M15 transitions. Size may reduce but position is maintained.

M15 diffMid ≥ 3 (sideways) → THIS blocks NEW entries. M15 is the entry trigger TF — no direction = no entry. Existing position: hold if H4/H1 still fly, otherwise exit.

M15 + M30 BOTH SQZ simultaneously → EXIT ALL (B2 pink zone). This is the ONLY condition that forces exit of existing positions.

### Stop Placement

| Scenario | BUY stop placement | SELL stop placement | ATR TF |
|---|---|---|---|
| A (full fly) | Below M30 lower band | Above M30 upper band | M30 ATR |
| B1 (M15 shrink) | Below M30 lower band | Above M30 upper band | M30 ATR |
| B2 (M30 shrink) | Below H1 lower band | Above H1 upper band | H1 ATR |
| B3 (H1 shrink) | Below H4 lower band | Above H4 upper band | H4 ATR |
| E (range trade) | Beyond H4 outer band | Beyond H4 outer band | H4 ATR |
| D (rest recovery) | Below M30 lower band | Above M30 upper band | M30 ATR |
| F1/F2 (compression release) | Below H1 lower band | Above H1 upper band | H1 ATR |
| F3 (HTF confirmed) | Below M30 lower band (→ Scenario A) | Above M30 upper band | M30 ATR |
| C1 (MTF reversal) | Beyond H4 outer band (tight — counter-trend) | Beyond H4 outer band | H4 ATR |
| C2 (H4 confirmed) | Below M30 lower band (→ new A) | Above M30 upper band | M30 ATR |
| Phase 6 (legs) | Beyond H4 boundary that was just touched (tight) | Same — tight to boundary | H4 ATR |

**ATRSL reference:** Stop levels use `ATRSL1buf` values from EA. `dir:0` = tracking upward (BUY trailing stop). `dir:1` = tracking downward (SELL trailing stop).

## 8. Firing Matrix & Sizing  [master: Part 5 / gate-rewrite]

| Scenario | Phase(s) | Armed entries | Armed exits | Size ceiling | Notes |
|---|---|---|---|---|---|
| A1 | PH_1 | E1 | X2 primary, X1(D1 band) | 1.00 | Part 5 Tier 1 |
| A2 | PH_1 | E2 | X2, X1(H4 band) | 0.75 | Part 5 Tier 1 |
| A3 | PH_1 | none (HOLD) | none (ride noise SQZ) | hold | Part 5 A3 |
| B1 | PH_2 | E3 both dir, E1 re-entry | X1(M30 band) primary, X2 qualified | 0.75 | Part 5 + V2 |
| B2 | PH_2/3A | E3 both dir | X1(H1 band) primary, X2 qualified | 0.50 | Part 5 + V2/V3 |
| B3 | PH_3A | E3 both dir | X1(H4 band) primary, X2 qualified | 0.25 | Part 5 + V1 |
| B1-B3 | PH_3B_INTO | E3 trend-side; counter-side 0.25 | X1 (dropping targets) | 0.50 | §13 Phase 3b |
| B* | PH_3B_OUT | E3 recovery-side | X1 = D1 boundary HARD | 0.50 | §13 3b-OUT |
| E1 | PH_3A/4 | none (WAIT) | existing rides: X1, X2 qualified | — | M30 SQZ ≠ exit |
| E2 | PH_4 | none | X4 forced | 0 | ASSERT-B2 |
| E3(load) | PH_4→5 | E4-ARM → E5 on M15 confirm | — | 0.50 | Part 5 E3 loading |
| E4 | PH_4 | none (WAIT) | — | 0 | ASSERT-B4 |
| H1 | PH_5 | E5 (with-D1 break) | X1, X2 | 0.75 | Part 4 Rule 4 |
| H2 | PH_5 | E5 (counter-D1) | X1, X2, tight stop | 0.25 | counter-trend |
| H3 | PH_5 fail | none | X2 immediate | 0 | false breakout |
| H4 | PH_6 | E3 at H4 bounds, both dir | X1 opposite H4 bound ONLY | 0.25 | §13 Phase 6 |
| D1s | PH_5 | E4-ARM | — | — | arm only |
| D2s | PH_5 | E5 | X1(H4 band), X2 qualified | 0.75 | |
| D3s | PH_1 | add-on if conf≥90 | X1(D1 band), X2 | 1.00 | → A |
| F1 | PH_5 | none (WAIT) | — | 0 | LTF only |
| F2 | PH_5 | E5 | X1(H4 band) | 0.75 | |
| F3 | PH_5→1 | E6 | X1(D1 band), X2 | 1.00 | → A |
| C1 | PH_5 | E5 | X1(H4 band new dir), tight | 0.25 | until H4 confirms |
| C2 | PH_5→1 | E6 | X1(D1 band new dir), X2 | 1.00 | → new A |
| C3 | any | E5 | X1(H4 band), tight | 0.50 | W1/D1 opposing |

Final size = MathMin(matrix ceiling, confidence size, §12d decoder size)  // EDIT V5

Always armed (3 invariants, evaluated in order):
1. EMERGENCY (MAX_FLOATING_LOSS_USD)
2. X4-PINK (M15+M30 both BBW 400-499)
3. VETO-AT-TARGET (screens any entry the matrix produces)

## 9. Verification Constants  [master: Part 6]

- Log path: `.\Backtest_data\(version)\(YYYYMMDD)_clean.log` (V uppercase)
- Output path: `.\references\log_verification\`
- March benchmark: ≥6 of 8 legs; max loss ≤ M30-band stop; no exit ≤3 bars on mid=3 wobble; zero holds >3 days; 03.03 07:45 → VETO-AT-TARGET never BUY
