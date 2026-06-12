# EDIT_VERIFICATION_FIXES_INSTRUCTIONS.md
# Target file: references/backtest_chart_analysis.md
# Branch: tofy5
# Source: findings from references/log_verification/20260302_0900-20260320_0900_analysis.md
#         (4 entries vs ~10 arrow legs, 25 EXIT churn, 7 BBW_stage lag conflicts,
#          H4-OPPOSE blocking zigzag legs, E3 boundary entries never firing,
#          0.75x sizing vs 0.25x decoder prescription)

---

## CRITICAL RULES — READ BEFORE ANY EDIT

1. Execute edits ONE AT A TIME using str_replace_based_edit
2. Before each edit, READ the target section first to get the exact current text.
   The anchor strings below are headings/fragments — locate them, read the
   surrounding lines, then build the exact old_string from the real file content.
3. After EVERY edit run: wc -l references/backtest_chart_analysis.md
4. NEVER remove existing content unless the instruction says REPLACE or DELETE
5. After ALL edits: git add, git commit, git push origin tofy5, report hash

---

## EDIT V1 — Re-scope Block Condition B3 (H4 opposing) in Part 5

### Locate: Part 5 Block Conditions table, the B3 row:
```
| B3 | H4 opposing |
```

### Read the full Block Conditions table, then ADD immediately AFTER the table
(before the "Critical block rule — M30 SQZ alone is NOT a block" block) EXACTLY:

```
**B3 scope limits — when H4-OPPOSE must NOT block:**

B3 is only valid when H4 has a REAL committed direction. It must be DISABLED when:

| Condition | Why B3 is invalid | Evidence rule |
|---|---|---|
| H4 diffMid = 3 (sideways) | There is no "opposing" direction — H4 has none. Phase 3a zigzag legs are tradeable BOTH directions | diffMid is primary over BBW_stage |
| H4 diffBBW contradicts H4 BBW_stage (e.g., BBW=521 bearish but diffBBW positive and mid=3) | BBW_stage is lagging — the labelled direction no longer exists | Section 12 priority: diffBBW > diffMid > BBW_stage |
| Phase = 3a, 6 (identified per Section 13) | These phases are defined as both-direction range phases | Phase rules override directional blocks |

**Failure mode this prevents (March 2026 verification):** H4-OPPOSE keyed off lagging
H4 BBW_stage blocked the entire counter-H4 half of zigzag legs (03.04–03.05 up-legs
blocked by stale 521/522 label while H4 mid=3), and blocked the 03.03 crash SELL leg
because H4 label was still 512 fly-up after the down-move had begun.
```

---

## EDIT V2 — Entry path priority by phase (E3 must be active in zigzag phases)

### Locate: Part 5 Entry Conditions table (rows E1–E6).

### Read the section, then ADD immediately AFTER the "6 Confinement Checks" block EXACTLY:

```
**Entry path priority by phase:**

The M15-mid-flip entries (E1/E2/E5) are a 1–2 bar transition window. If that single
bar is blocked, the leg is missed permanently — there is no mid-leg entry. Therefore
the boundary entry E3 is the PRIMARY path in zigzag phases:

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

**Failure mode this prevents (March 2026 verification):** zero E3 boundary entries
fired in the entire 03.02–03.20 window; only 4 G6 transition entries occurred against
~10 tradeable boundary-reversal legs. The transition window was repeatedly blocked at
the exact flip bar, leaving legs permanently missed (e.g., 03.05: M15 mid already 2
all day — no fresh flip, no entry, full SELL leg missed).
```

---

## EDIT V3 — Exit hierarchy by phase in Part 5

### Locate: Part 5 Exit Conditions table (rows X1–X4).

### Read the section, then ADD immediately AFTER the Exit Conditions table EXACTLY:

```
**Exit priority by phase — X1 before X2 in zigzag phases:**

X2 (M15 mid fades to 3) fires on every M15 wobble. In zigzag phases M15 passes
through 3 constantly MID-LEG, producing exit churn and — combined with the
transition-window entry problem — permanent loss of the leg.

| Phase | Primary exit | X2 role | Rule |
|---|---|---|---|
| Phase 1 | X2 (trend fade) | Primary | Trend exits on genuine fade |
| Phase 2 / 3a / 3b / 6 | X1 (opposite boundary target) | Failsafe ONLY | Ignore M15 mid=3 wobble unless price has stalled ≥3 bars short of target OR target TF band invalidated |
| Phase 4 | X4 (pink zone) | — | Forced exit |
| Phase 5 | X1 at escalating targets | Secondary | Hold while diffBBW sharply positive |

**Failure mode this prevents (March 2026 verification):** 25 EXIT events against
4 entries; 12+ exits clustered 03.17–03.18 at M30/M15 mid readings of 3/4/5 during
a sustained bearish run that should have been held as one or two legs to the
boundary target.
```

---

## EDIT V4 — Scenario identification priority rule in Part 3 intro

### Locate: Part 3 intro, the cycle sequence block (after "Cycle sequence:").

### Read the intro, then ADD immediately AFTER the cycle sequence code block EXACTLY:

```
**Scenario identification variable priority (normative):**

When BBW_stage conflicts with diffMid_Trend or diffBBW, the scenario MUST be
identified from diffBBW + diffMid_Trend. BBW_stage is a 3-bar lagging label and
is confirmation only — never the primary input.

Priority: diffBBW (fastest) > diffMid_Trend > BBW_stage (slowest).

This applies to every scenario table in Part 3 and every gate/condition in Part 5.
March 2026 verification found 7 lag conflicts, all clustered at scenario transition
timestamps — exactly the moments where acting on the stale label produces wrong
blocks and wrong scenario reads (e.g., 03.09 04:00: BBW=422 SQZ label while
diffBBW=+41.34 — breakout already underway).
```

---

## EDIT V5 — Size decoder enforcement note in Part 5 Size Matrix

### Locate: Part 5 Size Matrix table.

### Read the section, then ADD immediately AFTER the Size Matrix (before
"Size adjustments by diffBBW") EXACTLY:

```
**§12d combined decoder OVERRIDES the confidence matrix when stricter:**

When Section 12d's combined cas_shrinkTF + cas_sqzCount reading prescribes a
smaller size than the confidence matrix, the decoder wins. Example from March 2026
verification: 03.03 07:45 BUY — confidence matrix allowed 0.75×, but decoder state
(cas_shrinkTF=2 + cas_sqzCount=1 = "B2 late → E1") prescribes 0.25×. The EA sized
0.75×. Rule: final size = min(confidence size, decoder size).
```

---

## FINAL COMMIT

```bash
git add references/backtest_chart_analysis.md
git commit -m "Encode March 2026 verification findings: B3 H4-OPPOSE scope limits, E3 primary entry in zigzag phases, X1-before-X2 exit hierarchy, diffBBW-primary scenario ID, decoder size override"
git push origin tofy5
```

Report the commit hash and new line count.

---

## POST-EDIT VERIFICATION CHECKLIST

- [ ] "B3 scope limits" block exists after Block Conditions table (3-row table)
- [ ] "Entry path priority by phase" table exists (8 phase rows) after 6 Confinement Checks
- [ ] "Exit priority by phase" table exists (4 rows) after Exit Conditions table
- [ ] "Scenario identification variable priority (normative)" exists in Part 3 intro
- [ ] "§12d combined decoder OVERRIDES" note exists after Size Matrix
- [ ] Each block cites the March 2026 verification failure mode
- [ ] No existing E/X/B condition rows removed or altered
- [ ] No gate names introduced outside the Gate Decoder section
