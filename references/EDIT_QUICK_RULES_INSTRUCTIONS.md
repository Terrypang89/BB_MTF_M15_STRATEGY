# EDIT_QUICK_RULES_INSTRUCTIONS.md
# Target: create references/QUICK_RULES.md (derived rules-only file)
# Branch: tofy5
# Source: references/backtest_chart_analysis.md (MASTER — do not modify it in this task)
# Purpose: verification tasks read this ~350-line file instead of the 5,062-line master.
#          10× token reduction per verification run.

---

## CRITICAL RULES

1. Every table is COPIED VERBATIM from the master — no rewording, no summarizing,
   no "improving". If a master table is wrong, it gets fixed in the MASTER first
   (separate edit), then re-extracted here.
2. Every section carries its master citation in the heading, e.g.
   "## 4. Scenario Identification  [master: Part 3]" — so ambiguity resolution
   can grep the master heading instead of reading the whole file.
3. EXCLUDE: all images, ASCII diagrams, worked examples, March-2026 evidence
   narratives, candlestick prose, Part 1 teaching content, Part 2 reference charts,
   Part 6 tutorials. Tables and one-line rules ONLY.
4. Target length: 300–400 lines. If over 450, you copied prose — cut it.
5. After creating, run the SELF-TEST in Step 3 before committing.

---

## STEP 1 — Create references/QUICK_RULES.md with this exact skeleton

```markdown
# QUICK_RULES — derived from backtest_chart_analysis.md
# ⚠ THIS FILE IS DERIVED. NEVER EDIT DIRECTLY.
# Every edit to a normative table in backtest_chart_analysis.md MUST
# regenerate the corresponding section here IN THE SAME COMMIT.
# Master version: <git short-hash of backtest_chart_analysis.md at generation time>

## 1. Variables  [master: Part 1 §2-§4b, §12]
<copy verbatim:>
- BBW_stage value table (511/512/521/522/513/523/400-499)
- diffMid_Trend value table (1-5)
- BBUpDn_state value table (0-4) + the "measures band movement NOT price" note
- PriceLoc value table (above_upper..below_lower)
- diffBBW sign table from §4b (5 rows: pos-increasing..neg-decreasing) + log format line
- THE PRIORITY RULE (verbatim from Part 3 intro / EDIT V4):
  diffBBW > diffMid_Trend > BBW_stage; BBW_stage is lagging confirmation only

## 2. Log Decoders  [master: §12b, §12c, §12d]
<copy verbatim:>
- TRADEINFO flag table (8 rows H2L/L2H + all=-1) + TF index reference (0=M5..5=D1)
- TRADEINFO scenario-identification table (the 13-14 row mapping)
- BBTFImpact two-flag table + B-sub-scenario mapping (4 rows) + conflict-state rule
- cas_shrinkTF table (6 rows) ; cas_sqzCount table (5 rows)
- COMBINED cas_shrinkTF × cas_sqzCount table (8 rows — includes the
  "B2 late → E1 → 0.25×" row)
- Journal log label table (MIDLINE_SQZ_LOADING..CASCADE_PINK_ZONE, 7 rows)
- PINK PAIR RULE one-liner: pink = M15 BBW 400-499 AND M30 BBW 400-499
  simultaneously — NEVER cas_sqzCount alone (sqzCount=2 can be H1+M30)

## 3. CHECK HTF FIRST  [master: §12 Compression — Check HTF First]
<copy verbatim:>
- The H4 × D1 state matrix (5 rows: fly/fly .. SQZ/shrink → meaning/path/probability)
- Reversal probability ladder (6 rows: M15-only .. H4 SQZ+D1)
- The "did HTF shrink FIRST or LTF FIRST" discriminator (3 bullets)

## 4. Scenario Identification  [master: Part 3]
<build ONE compact table — this is the only section that is assembled rather
 than copied wholesale, but every cell value comes from the master sub-state tables:>
| Sub | Tier | Identification condition (TF states) | Next |
covering all of: A1 A2 A3 / B1 B2 B3 / E1 E2 E3 E4 / G1 G2 G3 G4 /
D1 D2 D3 / F1 F2 F3 / C1 C2 C3   (23 rows)
- plus the cycle sequence block (A→B→E→E4→G→F→A etc, verbatim)

## 5. Phase Identification  [master: §13]
<copy verbatim:>
- The "Zigzag Amplitude Decay = diffBBW Made Visual" 8-row summary table
  (it already encodes Phase 1/2/3a/3b-INTO/3b-OUT/4/5/6 with diffBBW signatures)
- 3a vs 3b discriminator table (3 rows by H4 mid)
- Phase 6 vs Phase 2 discriminator (history + BBW cycling, 2 bullets)
- 3b-INTO vs 3b-OUT discriminator (2 bullets)

## 6. Prediction  [master: Part 4 Rules 1-5]
<copy verbatim, tables only:>
- Rule 1 direction table (8 phases)
- Rule 2 target-by-scenario table (16 rows) — SKIP the target-by-phase table
  (redundant with §5 for verification purposes)
- Rule 3 timeline table (8 rows)
- Rule 4: compress the CHECK trees into one edge table:
  | From | CHECK condition | Next | (≈15 rows — every YES/NO branch becomes a row)
- Rule 5 confidence matrix (6 rows) + diffBBW adjustments (4 bullets)

## 7. Trade Conditions  [master: Part 5 + EDITs V1-V5, W1]
<copy verbatim:>
- Entry table E1-E6 (6 rows)
- Entry path priority by phase table (8 rows)  [EDIT V2]
- The 6 confinement checks table
- ENTRY-AT-TARGET VETO paragraph  [W1b]
- Exit table X1-X4 (4 rows)
- Exit priority by phase table (4 rows) WITH the 3-condition X2 qualifier  [V3+W1c]
- Block table B1-B4 (4 rows) + B3 scope-limits table (3 rows)  [V1]
- The "M30 SQZ alone is NOT a block" critical rule block
- Stop placement table (11 rows) + ATRSL dir note

## 8. Firing Matrix & Sizing  [master: Part 5 / gate-rewrite]
- The scenario×phase armed-conditions matrix (≈23 rows)
- final size = min(matrix ceiling, confidence size, §12d decoder size)  [V5]
- The 3 invariants in evaluation order: EMERGENCY → X4-PINK → VETO-AT-TARGET

## 9. Verification Constants  [master: Part 6]
- Log path: .\Backtest_data\(version)\(YYYYMMDD)_clean.log  (V uppercase)
- Output path: .\references\log_verification\
- March benchmark one-liners: ≥6 of 8 legs; max loss ≤ M30-band stop;
  no exit ≤3 bars on mid=3 wobble; zero holds >3 days;
  03.03 07:45 → VETO-AT-TARGET never BUY
```

NOTE on Section 8: if the firing matrix does not yet exist in the master
(it was specified in EDIT_GATE_REWRITE_INSTRUCTIONS.md Step 4), copy it from
that file and add citation "[source: EDIT_GATE_REWRITE Step 4 — pending master
integration]". Flag this to the user in your completion report.

## STEP 2 — Header hash

Set the "Master version:" line to the current commit short-hash:
git log -1 --format=%h -- references/backtest_chart_analysis.md

## STEP 3 — SELF-TEST before committing

Answer these 8 questions using ONLY QUICK_RULES.md (do not open the master).
If any answer requires the master, the extraction is incomplete — fix first:

1. cas_shrinkTF=2 + cas_sqzCount=1 → scenario? size?        (expect: B2-late→E1, 0.25×)
2. M30 BBW=415, M15 mid=2 → is pink active? is B1 active?   (expect: no pink; no B1)
3. H4 BBW=512 but diffBBW_H4=-1.2, mid=3 → trust which? state? (expect: diffBBW; shrinking)
4. Phase 3a, price at H4 upper band, H4 mid=3 → which entry armed, which direction?
   (expect: E3 fade SELL — B3 disabled per V1)
5. Holding SELL in PH_2, M15 mid flips 2→3, container diffBBW=+0.8, mid=2,
   price mid-band → exit? (expect: NO — unqualified fade, hold)
6. PriceLoc=+2 vs D1 container, flip BUY signal fires → action? (expect: VETO-AT-TARGET)
7. Scenario G2 → next scenario and max size? (expect: C1; 0.25×)
8. All TRADEINFO flags = -1 → scenario? (expect: G direction pivot / transitional)

## STEP 4 — Commit + sync rule propagation

1. git add references/QUICK_RULES.md
   git commit -m "Add QUICK_RULES.md: derived rules-only extract (~350 lines) for token-efficient verification; master hash pinned"
   git push origin tofy5
2. Append to the CRITICAL RULES section of EDIT_INSTRUCTIONS.md (the local
   workflow file, if present in repo):
   "N. Any edit touching a normative table MUST regenerate the corresponding
    QUICK_RULES.md section in the same commit. Post-edit checklist:
    [ ] QUICK_RULES.md synced + master hash updated."
3. Report: final line count, self-test 8/8 result, commit hash, and whether
   Section 8 came from master or from EDIT_GATE_REWRITE (pending flag).

---

## POST-EDIT VERIFICATION

- [ ] File exists at references/QUICK_RULES.md, 300-450 lines
- [ ] DERIVED warning + master hash in header
- [ ] All 9 sections present with [master: ...] citations
- [ ] Zero images, zero ASCII diagrams, zero worked examples
- [ ] Pink-pair rule present (M15+M30 BBW, not cas_sqzCount)
- [ ] Priority rule present (diffBBW > diffMid > BBW_stage)
- [ ] V1 B3 scope limits, V2 entry priority, V3+W1c exit qualifier,
      W1b veto, V5 min() sizing all present
- [ ] Self-test 8/8 answered from QUICK_RULES alone
- [ ] Sync rule added to workflow critical rules
