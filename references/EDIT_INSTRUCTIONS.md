# EDIT_INSTRUCTIONS.md
# Target file: references/backtest_chart_analysis.md
# Current state: 2218 lines / 94.2 KB
# Branch: tofy5

---

## CRITICAL RULES — READ BEFORE ANY EDIT

1. Execute edits ONE AT A TIME using str_replace_based_edit
2. After EVERY edit, run: `wc -l references/backtest_chart_analysis.md`
   and confirm line count increased before proceeding
3. NEVER remove existing content unless the instruction says REPLACE
4. NEVER invent BBW_stage, diffMid_Trend, or BBUpDn_state values
5. Use [TO BE FILLED: describe what is needed] for image-dependent content
6. Valid BBW_stage values ONLY: 511 512 521 522 513 523 400-499
7. Valid diffMid_Trend values ONLY: 1 2 3 4 5
8. Valid BBUpDn_state values ONLY: 0 1 2
9. Valid Touch Type values ONLY: Type 1 Type 2 Type 3
10. After ALL edits complete: git add references/backtest_chart_analysis.md
    then git commit -m "message" then git push origin tofy5
    then report the commit hash

---

## EDIT 1 — Replace PART 3 heading and add Tier structure

### Find this EXACT string (unique in file):
```
# PART 3 — MIDDLE AND LOWER TIMEFRAME SCENARIO ANALYSIS

Apply after HTF context is established. Each scenario: **What you see → What it means → Trade action**
```

### Replace with EXACTLY:
```
# PART 3 — MIDDLE AND LOWER TIMEFRAME SCENARIO ANALYSIS

Apply after HTF context is established.
Read Part 2 HTF context first — every scenario below only makes sense
when you know what H4 + D1 are doing.

Scenarios are organised by **cascade position** — where in the D1→D2
cycle the market currently sits. Two cascade directions drive every cycle:

- **D1 — Compression cascade (HTF → LTF):** HTF tightens → confines TF below → cascades down. HTF is the driver.
- **D2 — Expansion cascade (LTF → HTF):** LTF breaks SQZ first → signal travels upward → HTF confirms last. LTF is the leading indicator.

**Cycle sequence:**
```
TOP (A) → D1 begins (B) → D1 deepens (E) → BOTTOM (G or E2)
→ D2 initiates (D or F) → D2 confirms (C or back to A)
```

---

## TIER 1 — EXPANSION COMPLETE (TOP)

> D2 cascade fully confirmed. All TFs expanding same direction.
> HTF fly intact. Highest entry quality. D1 has not yet begun.

**Scenarios in this tier:** A

---

## TIER 2 — COMPRESSION IN PROGRESS (D1)

> HTF compressing downward toward LTF. Trades shorter and
> size reduces as compression depth increases.
> D1 cascade is the cause — HTF state confines every TF below it.

**Scenarios in this tier:** B (shallow) → E (deep, HTF fly) → G (HTF also compressing)

---

## TIER 3 — EXPANSION IN PROGRESS (D2)

> LTF breaking out, signal travelling upward toward HTF.
> Entry quality increases as each TF confirms upward.
> Direction may be same as previous trend (D, F) or opposite (C).

**Scenarios in this tier:** D (same direction) → F (breakout from deep) → C (full reversal)

---

```

### Verify: line count should increase by ~40 lines

---

## EDIT 2 — Add Tier label and sub-scenarios to Scenario A

### Find this EXACT string (unique in file):
```
**HTF context:** W1 fly + D1 fly + H4 fly — all in same direction. Full macro tailwind.
```

### Insert BEFORE it EXACTLY:
```
> **Tier:** TIER 1 — EXPANSION COMPLETE (TOP)
> **Cascade position:** D2 fully confirmed — all TFs aligned
> **Cascade direction:** TOP — no active D1 or D2, fully expanded
> **Leading TF:** M15 (entry trigger)
> **Next scenario:** → B when M15 first enters 513/523 (D1 begins at M15 depth)

### Sub-Scenarios

| Sub | Name | HTF State | MTF State | LTF State | Trade Mode | Size |
|-----|------|-----------|-----------|-----------|------------|------|
| A1 | Strong Fly | W1+D1+H4 all 511/512 | H1+M30 511/512 | M15+M5 511/512 | Full trend entry — hold toward D1 outer band | 1.0× |
| A2 | Partial Fly | H4 511/512 fly but W1 or D1 counter-trend | H1+M30 511/512 | M15+M5 511/512 | Trend entry, shorter hold — exit at H4 outer band | 0.75× |
| A3 | Noise Squeeze | H4+D1+W1 all 511/512 | H1+M30 511/512 | M15 513/523 briefly OR M5 400-499 briefly | HOLD through — Type 1 compression noise | 1.0× |

**Discriminator A1 vs A2:** Check W1 and D1 BBW_stage — both 511/512 = A1, either opposing = A2
**Discriminator A2 vs A3:** A3 is a sub-state within A1 or A2 — M5/M15 brief squeeze only, M30 still 511/512

```

### Verify: line count should increase by ~18 lines

---

## EDIT 3 — Add Tier label and sub-scenarios to Scenario B

### Find this EXACT string (unique in file):
```
**HTF context:** H4 is still in fly, but M30 or M15 starting to shrink. H4 provides the direction and target; M30/M15 are resting before continuing.
```

### Insert BEFORE it EXACTLY:
```
> **Tier:** TIER 2 — COMPRESSION IN PROGRESS (D1 Shallow)
> **Cascade position:** D1 initiated — H4 fly intact, LTF/MTF compressing
> **Cascade direction:** D1 flowing downward — H4 confinement driving MTF/LTF shrink
> **Leading TF:** Lowest TF currently showing 513/523 (frontier of D1)
> **Next scenario:** → E if depth reaches M30+M15 SQZ simultaneously
>                   → D if M5 breaks SQZ in same direction as H4
>                   → C if M5 breaks SQZ in opposite direction to H4

### Sub-Scenarios

| Sub | Name | D1 Depth | H4 | H1 | M30 | M15 | Size | Valid Touch Signal |
|-----|------|----------|----|----|-----|-----|------|--------------------|
| B1 | M15 shrink only | M15 entering 513/523 | 511/512 | 511/512 | 511/512 | 513/523 | 0.75× | M30 outer band BBUpDn=1/2 with mid=4/5 — Type 2 |
| B2 | M30 shrink | M30 also 513/523 | 511/512 | 511/512 | 513/523 | 513/523 | 0.50× | H1 outer band BBUpDn=1/2 with mid=4/5 — Type 2 |
| B3 | H1 shrink | H1 also 513/523 | 511/512 | 513/523 | 513/523 | 513/523 | 0.25× | H4 outer band BBUpDn=1/2 only — Type 2 |

**Touch discrimination during B:** LTF/MTF outer band touches during B are mostly Type 1
(compression geometry — band moved to price, mid=3). Valid signal ONLY when:
BBUpDn_state=1/2 at the HIGHEST still-flying TF AND that TF mid=4 or 5 (directional lean).

**Discriminator B1→B2:** Watch M30 BBW_stage — when M30 enters 513/523, depth increases to B2
**Discriminator B2→B3:** Watch H1 BBW_stage — when H1 enters 513/523, depth increases to B3
**Discriminator B→E:** When M15+M30 both show 400-499 (SQZ) simultaneously → E2

```

### Verify: line count should increase by ~22 lines

---

## EDIT 4 — Rename Scenario C and add Tier label + sub-scenarios

### Find this EXACT string (unique in file):
```
## Scenario C — Cascade Band Touch (G0b context)
```

### Replace with EXACTLY:
```
## Scenario C — Full Reversal (D2 Opposite Direction)
```

Then find this EXACT string (unique in file — first line of Scenario C content after flowchart):
```
### Scenario C Identification Flowchart
```

### Insert BEFORE it EXACTLY:
```
> **Tier:** TIER 3 — EXPANSION IN PROGRESS (D2 Opposite)
> **Cascade position:** D2 confirmed in opposite direction to previous trend
> **Cascade direction:** D2 flowing upward in new direction — LTF led, HTF confirming last
> **Leading TF:** H4 (last to confirm — once H4 flips, C2 confirmed → treat as new A)
> **Previous scenario:** Came from E2/E3 or G2/G3 — deep compression exhausted
> **Next scenario:** → New A in opposite direction once H4 confirms (C2)

### Sub-Scenarios

| Sub | Name | H4 State | H1 State | M30 State | M15 State | Entry | Size |
|-----|------|----------|----------|-----------|-----------|-------|------|
| C1 | MTF reversal only | 511/512 or 513 (original direction) | Reversed 521/522 | Reversed 521/522 | Reversed 521/522 | Wait — H4 not confirmed, counter-trend risk | 0.25× |
| C2 | H4 confirmed | H4 flipped to new direction 511/512 | New direction | New direction | New direction | ENTER — treat as new Scenario A1/A2 | 1.0× or 0.75× |
| C3 | Counter-trend | H4 reversed BUT W1/D1 still original direction | New direction | New direction | New direction | SHORT hold — W1/D1 will eventually pull back | 0.50× |

**Discriminator C1→C2:** H4 BBW_stage flips from original direction fly to new direction fly
**Discriminator C2 vs C3:** Check W1+D1 — if both also reversed = C2 full (→ A1). If W1/D1 still original = C3 counter-trend
**Key rule:** Do NOT enter at C1. Wait for H4 confirmation (C2) unless deliberately taking
counter-trend with tight stop and 0.25× size.

```

### Verify: line count should increase by ~24 lines

---

## EDIT 5 — Add Tier label and sub-scenarios to Scenario D

### Find the SCENARIO D heading. The exact string is:
```
## Scenario D —
```

NOTE: Get the full exact heading text first by reading the file around that section,
then find the first line of Scenario D content (the HTF context line) and insert before it.

The HTF context line for Scenario D contains "rest" or "shrink → fly" — find it and insert:

```
> **Tier:** TIER 3 — EXPANSION IN PROGRESS (D2 Same Direction)
> **Cascade position:** D2 initiated in same direction as previous trend — rest re-entry
> **Cascade direction:** D2 flowing upward — M5 led, MTF confirming
> **Leading TF:** M5 (first to break SQZ), then M15 (entry trigger)
> **Previous scenario:** Came from B (shallow D1) — H4 fly maintained throughout
> **Next scenario:** → A when MTF re-aligns fully (D3 complete)

### Sub-Scenarios

| Sub | Name | Gate | H4 | H1 | M30 | M15 | M5 | Entry | Size |
|-----|------|------|----|----|-----|-----|----|-------|------|
| D1 | M5 break | G6-LOAD fires | 511/512 | 511/512 | 513/523 or 400-499 | 513/523 or 400-499 | Breaking SQZ — REVUP/REVDN | WAIT — arm only, M15 not confirmed | — |
| D2 | M15 confirm | G6-BUY/SELL fires | 511/512 | 511/512 | 511/512 or 513 | FLAT→UP/DN transition | 511/512 | ENTER — M15 mid flip is the trigger | 0.75× |
| D3 | MTF re-align | — | 511/512 | 511/512 | 511/512 | 511/512 | 511/512 | Hold existing / add if quality ≥ 90 | → 1.0× |

**D1 sub-state BBUpDn sequence:** M5 BBUpDn_state 2→1 (for BUY REVUP) = D2 signal initiated
**D2 trigger:** M15 mid=3 → mid=1 (REVUP) or mid=3 → mid=2 (REVDN) = G6-BUY/SELL fires
**D3 confirmation:** M30 BBW_stage reaches 511/512 = D2 fully confirmed → back toward A

```

### Verify: line count should increase by ~20 lines

---

## EDIT 6 — Add Tier label and sub-scenarios to Scenario E

### Find the first line of Scenario E content (HTF context line).
It will contain text about "H4 fly" and "confined compression" or similar.
Insert BEFORE the HTF context line of Scenario E EXACTLY:

```
> **Tier:** TIER 2 — COMPRESSION IN PROGRESS (D1 Deep)
> **Cascade position:** D1 deep — LTF fully SQZ, HTF fly maintained
> **Cascade direction:** D1 complete at LTF level — BOTTOM approaching
> **Leading TF:** M5 (watch for REVUP/REVDN — this is the D2 initiation signal)
> **Previous scenario:** Came from B3 (H1 also shrinking) → E1
> **Next scenario:** → F when M5 breaks SQZ and M15 confirms (D2 begins)
>                   → G if H4 also starts compressing (D1 deepens further)

### Sub-Scenarios

| Sub | Name | H4 | H1 | M30 | M15 | M5 | Touch Type | Gate | Trade |
|-----|------|----|----|-----|-----|----|------------|------|-------|
| E1 | LTF partial SQZ | 511/512 | 511/512 or 513 | 513/523 | 400-499 | 400-499 | Type 1 at M30, Type 3 at M15/M5 | G0c-SQZLOCK active | No new entries — wait |
| E2 | LTF full SQZ | 511/512 | 511/512 or 513 | 400-499 | 400-499 | 400-499 | Type 3 — all bands alternating BBUpDn 1/2 | G0b-PINK fires | EXIT all — pink zone |
| E3 | Loading | 511/512 | 511/512 | 513/523 or breaking | 513/523 or breaking | Breaking SQZ — REVUP/REVDN | Type 2 at M5 (BBUpDn 2→1) | G6-LOAD fires | ARM for entry — wait M15 confirm |

**E2 BBUpDn sequence:** M5 BBUpDn alternates 1 and 2 on consecutive bars = SQZ peak = G0b-PINK
**E3 BBUpDn sequence:** M5 BBUpDn_state 2→1 (REVUP) = D2 initiated = G6-LOAD
**Touch rule in E:** During E1/E2 all LTF touches are Type 1 or Type 3 (noise/geometry).
Only M5 BBUpDn 2→1 transition (Type 2 at M5 level) is the valid signal.

```

### Verify: line count should increase by ~22 lines

---

## EDIT 7 — Add Tier label and sub-scenarios to Scenario F

### Find the Scenario F heading. It will be:
```
## Scenario F —
```

Get the exact heading text, then find the first content line of Scenario F
and insert BEFORE it EXACTLY:

```
> **Tier:** TIER 3 — EXPANSION IN PROGRESS (D2 from Deep Compression)
> **Cascade position:** D2 initiated after E or G depth — HTF not yet confirmed
> **Cascade direction:** D2 flowing upward — came from deep BOTTOM
> **Leading TF:** M30 (MTF confirmation is the key gate — F1 waits for this)
> **Previous scenario:** Came from E3 (M5 broke SQZ) or G2 (D1 gives bias)
> **Next scenario:** → A when H4 confirms new fly direction (F3 → A)
>                   → Back to E/G if HTF rejects breakout

### Sub-Scenarios

| Sub | Name | H4 | H1 | M30 | M15 | M5 | Entry | Size |
|-----|------|----|----|-----|-----|----|-------|------|
| F1 | LTF only | 400-499 or 513 | 513 or 400-499 | 513 or 400-499 | 511/512 | 511/512 | WAIT — quality capped at 59, G5-WEAK blocks | — |
| F2 | MTF confirmed | 400-499 or 513 | 511/512 | 511/512 | 511/512 | 511/512 | ENTER on M15 FLAT→UP/DN, M30 confirming | 0.75× |
| F3 | HTF confirmed | 511/512 (new direction) | 511/512 | 511/512 | 511/512 | 511/512 | ENTER — treat as Scenario A | 1.0× |

**F1→F2 discriminator:** M30 BBW_stage exits 400-499/513 and reaches 511/512 = F2 confirmed
**F2→F3 discriminator:** H4 BBW_stage exits 400-499/513 and reaches 511/512 new direction = F3
**False breakout rule:** If M15 fly expands but reverses within 3-5 bars back to 513/400-499
→ invalidated → return to E3/G2, wait for re-SQZ and re-expand

### Trade action:
```
F1: WAIT — M30 not confirmed, quality ≤ 59, G5-WEAK blocks entry
F2: ENTER on M15 FLAT→UP/DN transition
    TARGET: H4 outer band (if H4 still 513) or H4 fly target (if H4 breaking out)
    EXIT: M15 UP→FLAT (G5-FADE) | H4 rejects → return to E | G8-BNDTGT
    SIZE: 0.75×
F3: ENTER → treat as Scenario A1 or A2 depending on W1/D1 alignment
    SIZE: 1.0× (A1) or 0.75× (A2)
```

```

### Verify: line count should increase by ~30 lines

---

## EDIT 8 — Add Tier label and sub-scenarios to Scenario G

### Find the Scenario G heading. It will be:
```
## Scenario G —
```

Get the exact heading text, then find the first content line of Scenario G
and insert BEFORE it EXACTLY:

```
> **Tier:** TIER 2 — COMPRESSION IN PROGRESS (D1 Reached HTF)
> **Cascade position:** D1 deep — H4 also compressing. No macro tailwind at any TF.
> **Cascade direction:** D1 complete — BOTTOM-DEEP. D2 direction unknown until D1 fly breaks.
> **Leading TF:** D1 (sets eventual D2 direction — watch D1 mid for bias)
> **Previous scenario:** Came from E (H4 started compressing while LTF already SQZ)
> **Next scenario:** → F when M5 breaks SQZ and M30 confirms (D2 begins from deep)
>                   → G3 if D1 also enters SQZ (full flat — no trade)

### Sub-Scenarios

| Sub | Name | D1 | H4 | H1+M30+M15 | M5 | Trade Mode | Size |
|-----|------|----|----|------------|-----|------------|------|
| G1 | H4 shrink + LTF SQZ | 511/512 fly | 513/523 | 400-499 SQZ | 400-499 SQZ | Range fade at H4 outer bands — G0b-TOUCH path | 0.25× |
| G2 | H4 SQZ + D1 fly | 511/512 fly | 400-499 SQZ | 400-499 SQZ | 400-499 SQZ | Range fade — D1 mid gives directional bias | 0.25× |
| G3 | Full flat | 400-499 SQZ | 400-499 SQZ | 400-499 SQZ | 400-499 SQZ | NO TRADE — G0b-SQZLOCK | — |

**G1 touch rule:** H4 outer band BBUpDn=1/2 = valid G0b-TOUCH range fade entry
               H4 mid=1/5 (lean) = bias toward that direction — favour that side
               Target = H4 midline (not outer band — range trade only)
**G2 touch rule:** Same as G1 but use D1 mid direction as bias for which side to favour
**G3 rule:** G0b-SQZLOCK active — no entry. Wait for M5 REVUP/REVDN signal.
**D2 direction prediction from G:** The TF that is still in fly (usually D1 in G1/G2)
sets the eventual D2 direction. Watch D1 mid — mid=1/5 = D2 likely upward, mid=2/4 = downward.

### Trade action:
```
G1: SELL at H4 upper band touch (BBUpDn=1) | BUY at H4 lower band touch (BBUpDn=2)
    FILTER: H4 mid must have lean (4 or 5) not pure 3 — if mid=3, G0b-SQZLOCK may block
    TARGET: H4 midline
    EXIT: G8-BNDTGT (midline reached) | G0b-PINK (M15+M30 both SQZ)
    SIZE: 0.25×
G2: Same as G1 — use D1 mid direction to favour long or short side
    SIZE: 0.25×
G3: NO ENTRY — wait for M5 REVUP/REVDN → signals transition to F1
```

```

### Verify: line count should increase by ~32 lines

---

## EDIT 9 — Add Section 13 to Part 1

### Find this EXACT string (unique in file):
```
## 12. Risk Management Guidelines
```

### Insert BEFORE it EXACTLY:
```
## 13. Cascade Direction Model

Two cascade directions drive every market cycle in this strategy.

### D1 — Compression Cascade (HTF → LTF)

HTF tightens → confines TF below → cascades downward until LTF reaches SQZ.
HTF is the driver. Observable as BBW_stage dropping TF by TF from top down.

```
H4 shrinks (513/523)
  → H1 confined within H4 band → H1 ranges within H4 upper/lower
    → M30 confined within H1 band → M30 shrinks
      → M15 confined within M30 band → M15 shrinks
        → M5 reaches SQZ (400-499) — deepest confinement point
```

### D2 — Expansion Cascade (LTF → HTF)

LTF breaks SQZ first → signal travels upward → HTF confirms last.
LTF is the leading indicator. Observable as REVUP/REVDN at M5, then M15 fly, then M30, H1, H4.

```
M5 breaks SQZ (REVUP/REVDN) — G6-LOAD fires
  → M15 follows in 2-5 bars (FLAT→UP/DN) — G6-BUY/SELL fires — ENTRY
    → M30 confirms (511/512) — quality boost +10 to +15
      → H1 confirms — hold signal sustained
        → H4 confirms — full fly → Scenario A
```

### Cycle Sequence

```
TOP (A) → D1 begins (B) → D1 deepens (E) → BOTTOM (G or E2)
→ D2 initiates (D or F) → D2 confirms (C or back to A)
```

### Touch Type Classification

During D1, bands move toward price — candle wicks touch multiple TF bands simultaneously.
Three touch types must be distinguished:

| Type | BBW_stage | diffMid_Trend | BBUpDn_state | Meaning | Action |
|------|-----------|---------------|--------------|---------|--------|
| Type 1 | Shrinking 513/523 | 3/4/5 — flat or weak | 0→1 or 0→2 (band caught wick) | Band moved to price — compression geometry noise | IGNORE — not a signal |
| Type 2 | Highest still-flying TF at outer band | 4 or 5 — directional lean | 1 or 2 at HTF level | Price reached confinement boundary — real signal | Check G0b filters — valid entry |
| Type 3 | Multiple TFs SQZ 400-499 | 3 all TFs | Alternating 1 and 2 same bar/adjacent bars | SQZ peak — band width < candle range, geometric overlap | G0b-PINK zone — EXIT all, wait |

**Key rule:** The signal always comes from the HIGHEST TF that is currently at its outer band.
Lower TF outer band touches during HTF shrink = Type 1 noise.
Only the HTF confinement boundary touch = Type 2 valid signal.

---

```

### Verify: line count should increase by ~55 lines

---

## EDIT 10 — Fix Quick Navigation table

### Find this EXACT string (unique in file):
```
| Scenario details                       | Part 3 — Scenarios A through G             |
```

### Replace with EXACTLY:
```
| Scenario details                       | Part 3 — Tier 1 (A) / Tier 2 (B, E, G) / Tier 3 (D, F, C) |
```

### Verify: line count unchanged (same number of lines, content replaced)

---

## FINAL STEP — Commit and push

After all 10 edits are complete and each line count increase is confirmed:

```bash
git add references/backtest_chart_analysis.md
git commit -m "Restructure Part 3: add Tier 1/2/3 grouping, sub-scenarios A1-C3, Section 13 cascade model, touch type classification"
git push origin tofy5
```

Report the full commit hash.

Expected final line count: approximately 2218 + 40 + 18 + 22 + 24 + 20 + 22 + 30 + 32 + 55 + 0 = ~2481 lines

---

## VERIFICATION CHECKLIST

After push, confirm each item exists in the file:

- [ ] `## TIER 1 — EXPANSION COMPLETE (TOP)` heading present in Part 3
- [ ] `## TIER 2 — COMPRESSION IN PROGRESS (D1)` heading present in Part 3
- [ ] `## TIER 3 — EXPANSION IN PROGRESS (D2)` heading present in Part 3
- [ ] Scenario A has sub-scenario table with A1 / A2 / A3 rows
- [ ] Scenario B has sub-scenario table with B1 / B2 / B3 rows
- [ ] Scenario C heading reads "Full Reversal (D2 Opposite Direction)"
- [ ] Scenario C has sub-scenario table with C1 / C2 / C3 rows
- [ ] Scenario D has sub-scenario table with D1 / D2 / D3 rows
- [ ] Scenario E has sub-scenario table with E1 / E2 / E3 rows
- [ ] Scenario F has sub-scenario table with F1 / F2 / F3 rows
- [ ] Scenario G has sub-scenario table with G1 / G2 / G3 rows
- [ ] `## 13. Cascade Direction Model` section present in Part 1
- [ ] Touch Type table with Type 1 / Type 2 / Type 3 present in Section 13
- [ ] Quick Navigation table updated to reference Tier structure
- [ ] No existing content removed (flowcharts, trade action blocks, image embeds all intact)
- [ ] Final line count ≥ 2450

---

# CLEANUP EDITS — Remove redundant, duplicate, and misplaced content

---

## CLEANUP 1 — Remove duplicate "HTF Compression Cascade Dynamics" block from Part 1

### Problem:
Part 1 ends with Section 12 Risk Management, then has an UNLABELLED section
"HTF Compression Cascade Dynamics" with no section number. This exact content
is already covered in Part 2 (The Core HTF → MTF Cascade Rule, Price target
derivation table). It is a duplicate placed in the wrong part.

### Find this EXACT string (unique — starts after the --- separator after Section 12):
```
## HTF Compression Cascade Dynamics
```

### Find the full block to delete. It runs from that heading to the --- separator
before "# PART 2". Delete everything from the heading through the final --- :

Delete from:
```
## HTF Compression Cascade Dynamics
```
Through and including:
```
- When D1 starts shrinking (513), exit all H4 BUY positions

---
```

### Verify: line count should DECREASE by ~20 lines

---

## CLEANUP 2 — Remove duplicate "Compression depth measurement" block in Section 9

### Problem:
Section 9 (Compression Resolution) already has a "Compression Depth vs Outcome"
table. Then at the very END of Section 9, after the Visual Signals tables,
there is a standalone code block with band width ratios labelled
"Compression depth measurement". This same band width ratio formula
also appears in Scenario B's "Shrink depth measurement" block.
It appears TWICE and belongs in Section 8, not floating at the end of Section 9.

### Find this EXACT string (unique in file — the floating code block after Visual Signals of Reversal):
```
**Compression depth measurement:**

```
Band width ratio = (Upper band - Lower band) / Midband
  ≥ 0.005 = Wide (fly expanding)
  0.003-0.005 = Normal (parallel fly)
  0.001-0.003 = Narrow (shrinking)
  ≤ 0.001 = Very narrow (squeeze)

```

---
```

### Delete that entire block including the trailing ---

### Verify: line count should DECREASE by ~12 lines

---

## CLEANUP 3 — Remove duplicate visual checklist in Scenario A

### Problem:
Scenario A has TWO visual confirmation checklists back to back.
The first is a markdown TABLE checklist with [ ] checkboxes.
The second is a code block checklist with [✓] marks.
They contain identical items. The table version is better — keep it, delete the code block.

### Find this EXACT string (unique — the code block checklist in Scenario A):
```
**Visual identification checklist:**

```
[✓] All bands fanning outward in same direction
[✓] No mid-band labels (mid=1 or 2 suppressed)
[✓] H4 stepping in same direction
[✓] Stage labels: 511/512 (BUY) or 521/522 (SELL)
[✓] [G6-BUY] or [G6-SELL] gate labels visible (lime/orange)

```
```

### Delete that entire block (6 lines including the heading and blank lines around it)

### Verify: line count should DECREASE by ~8 lines

---

## CLEANUP 4 — Remove duplicate "Shrink depth measurement" from Scenario B

### Problem:
The band width ratio formula appears in Section 9 (being deleted by CLEANUP 2)
AND again in Scenario B as "Shrink depth measurement". Now that CLEANUP 2
removes the Section 9 copy, the Scenario B copy becomes the only instance —
BUT it should be moved to Section 8 where it belongs, not left in Scenario B.
The formula is a Part 1 reference tool, not scenario-specific content.

### Find this EXACT string (unique in file — in Scenario B):
```
**Shrink depth measurement:**

```
Band width ratio = (Upper band - Lower band) / Midband
  ≥ 0.005 = Wide (fly expanding)
  0.003-0.005 = Normal (parallel fly)
  0.001-0.003 = Narrow (shrinking)
  ≤ 0.001 = Very narrow (squeeze)

```
```

### Replace with exactly:
```
> **Band width reference:** See Part 1 Section 8 — Compression Zone Identification
```

### Then add the formula to Section 8. Find this EXACT string (end of Section 8):
```
- Gate labels shift to [G6-BUY] or [G6-SELL]

---
```

### Replace with:
```
- Gate labels shift to [G6-BUY] or [G6-SELL]

**Band width ratio reference:**
```
(Upper band - Lower band) / Midband
  ≥ 0.005 = Wide (fly expanding)
  0.003–0.005 = Normal (parallel fly)
  0.001–0.003 = Narrow (shrinking)
  ≤ 0.001 = Very narrow (SQZ)
```

---
```

### Verify: net line count change approximately zero (moved not deleted)

---

## CLEANUP 5 — Fix the duplicate "---" separator before PART 1

### Problem:
There are TWO consecutive "---" horizontal rules before "# PART 1 — CHART BASICS".
One is left over from the ATRSL1buf section, one is a section separator.

### Find this EXACT string (unique — the double --- before PART 1):
```
---

---


# PART 1 — CHART BASICS
```

### Replace with exactly:
```
---

# PART 1 — CHART BASICS
```

### Verify: line count should DECREASE by ~2 lines

---

## CLEANUP 6 — Remove "HTF Compression Zone Analysis" from Part 2

### Problem:
Part 2 ends with a section "HTF Compression Zone Analysis" containing
a compression phase table and compression duration guidelines table.
This content belongs in Part 1 Section 8 (Compression Zone Identification)
not in Part 2 (HTF Reference Charts). Part 2 should be HTF TF analysis only.
The duration guidelines table is new information — move it to Section 8,
then remove the Part 2 copy.

### Step A: Add duration table to Section 8.
Find this EXACT string (after the band width ratio block added in CLEANUP 4):
```
  ≤ 0.001 = Very narrow (SQZ)
```
```

---
```

### Replace with:
```
  ≤ 0.001 = Very narrow (SQZ)
```

**Compression duration guidelines:**

| Timeframe | Typical Duration |
|-----------|-----------------|
| M5 compression | 5–15 minutes |
| M15 compression | 30 min – 2 hours |
| M30 compression | 1–4 hours |
| H1 compression | 2–8 hours |
| H4 compression | 4–24 hours |

---
```

### Step B: Delete the entire "HTF Compression Zone Analysis" section from Part 2.
Find this EXACT string (unique — the HTF Compression Zone Analysis heading in Part 2):
```
## HTF Compression Zone Analysis
```

Delete from that heading through and including the final content of that section,
ending at the --- separator before "# PART 3":
```
- M (mid) touch counts high → oscillation, wait for direction

---
```

Delete that entire block.

### Verify: line count should DECREASE by ~25 lines, net ~+10 from Step A addition

---

## CLEANUP 7 — Fix Quick Navigation — remove reference to non-existent Part 7

### Problem:
Quick Navigation table has this row:
"Compression analysis | Part 7 — HTF Compression Zone Analysis"
There is no Part 7 in the document. This content is now in Part 1 Section 8
after the cleanup moves above.

### Find this EXACT string (unique):
```
| Compression analysis                   | Part 7 — HTF Compression Zone Analysis     |
```

### Replace with:
```
| Compression analysis                   | Part 1 Section 8 — Compression Zone Identification |
| Cascade direction model                | Part 1 Section 13 — Cascade Direction Model        |
```

### Verify: line count should INCREASE by ~1 line

---

## CLEANUP 8 — Fix Scenario Identification Flowchart in Part 2

### Problem:
The Part 2 flowchart routes to old scenario names.
"SCENARIO C\nCascade" should route to "SCENARIO G" (sideway)
and "SCENARIO F\nSQZ → Fly" should be separate from the continuation/reversal split.
After the rename of C to "Full Reversal" in EDIT 4, the flowchart still uses old names.

### Find this EXACT string (unique — inside the Part 2 scenario flowchart):
```
    F -->|Yes| G["SCENARIO C\nCascade"]
    F -->|No| H["SCENARIO D\nRest Pattern"]
    A -->|No| I["H4 in shrink?"]
    I -->|Yes| J["M30/M15 compressing?"]
    J -->|Yes| K["SCENARIO E\nFly expand + confined compression"]
    J -->|No| L["SCENARIO D\nRest Pattern"]
    I -->|No — H4 in SQZ| M["All TFs in SQZ?"]
    M -->|Yes| N["SCENARIO F\nSQZ → Fly (Breakout)"]
    N --> O["H1 maintaining original step?"]
    O -->|Yes| P["CONTINUATION\n(rest pattern)"]
    O -->|No| Q["REVERSAL\n(direction flip)"]
    M -->|No| R["M30+M15 both mid≥3?"]
    R -->|Yes| S["SCENARIO G\nAll TFs Sideway"]
```

### Replace with:
```
    F -->|Yes| G["SCENARIO D\nRest Re-entry (D2 same)"]
    F -->|No| H["SCENARIO B\nFly → Shrink deeper"]
    A -->|No| I["H4 in shrink?"]
    I -->|Yes| J["LTF in SQZ?"]
    J -->|Yes| K["SCENARIO E\nDeep Compression (LTF SQZ, HTF fly)"]
    J -->|No| L["SCENARIO B\nFly → Shrink"]
    I -->|No — H4 in SQZ| M["D1 still fly?"]
    M -->|Yes| N["SCENARIO G\nHTF Compression (D1 fly bias exists)"]
    M -->|No| O["SCENARIO G3\nFull Flat — no trade"]
    N --> P{"LTF breaking SQZ?"}
    P -->|Yes, same direction| Q["SCENARIO F\nBreakout Expansion (D2)"]
    P -->|Yes, opposite direction| R["SCENARIO C\nFull Reversal (D2 opposite)"]
    P -->|No| S["SCENARIO G\nWait at outerband"]
```

### Verify: line count approximately unchanged

---

## FINAL CLEANUP COMMIT

After all cleanup edits are complete:

```bash
git add references/backtest_chart_analysis.md
git commit -m "Cleanup: remove duplicates, fix misplaced sections, update flowchart labels, consolidate Part 1"
git push origin tofy5
```

Report the commit hash.

---

## COMPLETE EDIT SEQUENCE SUMMARY

Run in this exact order:

| # | Type | Description | Expected line change |
|---|------|-------------|---------------------|
| EDIT 1 | ADD | Part 3 Tier structure header | +40 |
| EDIT 2 | ADD | Scenario A sub-scenarios + tier label | +18 |
| EDIT 3 | ADD | Scenario B sub-scenarios + tier label | +22 |
| EDIT 4 | RENAME+ADD | Scenario C rename + sub-scenarios | +24 |
| EDIT 5 | ADD | Scenario D sub-scenarios + tier label | +20 |
| EDIT 6 | ADD | Scenario E sub-scenarios + tier label | +22 |
| EDIT 7 | ADD | Scenario F sub-scenarios + trade action | +30 |
| EDIT 8 | ADD | Scenario G sub-scenarios + trade action | +32 |
| EDIT 9 | ADD | Section 13 Cascade Direction Model | +55 |
| EDIT 10 | REPLACE | Quick Navigation update | 0 |
| CLEANUP 1 | DELETE | Remove duplicate HTF Cascade Dynamics from Part 1 | -20 |
| CLEANUP 2 | DELETE | Remove floating compression formula from Section 9 | -12 |
| CLEANUP 3 | DELETE | Remove duplicate checklist in Scenario A | -8 |
| CLEANUP 4 | MOVE | Move shrink formula to Section 8 | ~0 |
| CLEANUP 5 | DELETE | Remove double --- separator | -2 |
| CLEANUP 6 | MOVE+DELETE | Move duration table to Section 8, remove from Part 2 | -15 |
| CLEANUP 7 | REPLACE | Fix Quick Navigation Part 7 reference | +1 |
| CLEANUP 8 | REPLACE | Fix Part 2 flowchart scenario labels | ~0 |

**Expected final line count:** 2218 + 263 - 57 = approximately **2424 lines**
