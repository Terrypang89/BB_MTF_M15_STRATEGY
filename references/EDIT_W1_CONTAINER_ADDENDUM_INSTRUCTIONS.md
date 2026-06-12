# EDIT_W1_CONTAINER_ADDENDUM_INSTRUCTIONS.md
# Two parts: (A) document edits to backtest_chart_analysis.md — apply FIRST
#            (B) addendum to EDIT_TOFYTRADE5_SCAFFOLD_INSTRUCTIONS.md phases
# Branch: tofy5
# Source: Step 0.5 container discussion + 03.03 entry-at-target failure
#         (BUY @5343.82 with price AT D1 upper band 5336 — X1 target = entry price)

---

## PART A — DOCUMENT EDITS (backtest_chart_analysis.md)

### EDIT W1a — Add Step 2b (MTF Container Check) to Part 6 workflow

Locate Part 6 "Step 2 — CHECK HTF". Read it, then INSERT a new step
immediately AFTER it, renumbering nothing (use "Step 2b"):

```
## Step 2b — MTF Container Check (H1, M30)

Step 2 selects the playbook (strategic). Step 2b identifies the tactical
container for the current leg — required BEFORE depth or entry reads.

| Read | How | Why |
|---|---|---|
| Container TF | Highest TF currently in committed fly (diffMid=1/2 AND diffBBW not negative) | Its outer bands are the X1 target and the leg's hard boundaries |
| Container direction | Container TF diffMid | The leg's direction — M15 entries trade WITH or fade AT its boundaries |
| Container health | Container TF diffBBW | Positive = room left in the leg; ≤ 0 = leg aging, boundary rejection likely |
| PriceLoc vs container | Price vs container TF upper/mid/lower bands | Mid-band = room to trade; AT boundary = target zone — see veto below |

**Depth (Step 1/cas_shrinkTF) and container are independent reads:** depth can be
zero (no compression) while price sits at the container boundary — the leg is
finished even though nothing is compressed. The 2026.03.03 entry failed on
exactly this: shallow depth, but price AT the D1 upper band.
```

### EDIT W1b — Add the entry-at-target veto to Part 5 Entry Conditions

Locate the Part 5 "Entry path priority by phase" block (added by EDIT V2).
Read it, then INSERT immediately AFTER it:

```
**Entry-at-target veto (applies to ALL entry conditions E1–E6):**

No entry in the direction of a container/target boundary that price is
already touching. If PriceLoc is at/above the container TF upper band, BUY
is forbidden (the X1 target equals the entry price — the trade has no room);
mirror for SELL at the lower band. At a boundary the only valid setups are
the E3 fade (opposite direction, with lean + 6 checks) or WAIT.

Failure this prevents (March 2026 verification): 03.03 07:45 BUY @5343.82
with price AT the D1 upper band (5336) — entered exactly at its own target,
then held −191.29 for 9 days.
```

### EDIT W1c — Strengthen the X2 qualifier in the EDIT V3 exit-priority block

Locate the "Exit priority by phase" block (added by EDIT V3). In the
Phase 2/3a/3b/6 row, the X2 condition currently reads (approximately):
"Ignore M15 mid=3 wobble unless price has stalled ≥3 bars short of target
OR target TF band invalidated".

REPLACE that qualifier text with:

```
Ignore M15 mid=3 wobble unless ANY of: (a) the rung above is cracking —
container TF diffBBW ≤ 0 or its mid drifting to 5/4/3; (b) price stalled
≥3 bars short of the X1 target; (c) the target TF band is invalidated.
An M15 reversal with the container still committed (diffBBW > 0, mid=1/2,
price mid-band) is a pullback (D-rest), not an exit signal.
```

### Commit A: 
```
git add references/backtest_chart_analysis.md
git commit -m "Add Step 2b MTF container check, entry-at-target veto, container-cracking X2 qualifier (03.03 failure class)"
git push origin tofy5
```

---

## PART B — SCAFFOLD ADDENDUM (apply with EDIT_TOFYTRADE5_SCAFFOLD_INSTRUCTIONS.md)

### B1 — Phase 2 addition: extend ScenarioState

Add to the ScenarioState struct and compute in IdentifyScenario:

```cpp
  int    container_tf;      // highest TF in committed fly: diffMid 1/2 AND diffBBW>=0  // Part 6 Step 2b
  int    container_dir;     // that TF's diffMid (1/2), 0 if none
  double container_diffbbw; // health: >0 room, <=0 aging                               // Part 6 Step 2b
  int    priceloc_container;// -2 below_lower,-1 at_lower,0 inside,+1 at_upper,+2 above // vs container bands
```

priceloc thresholds: "at" band = within 0.15 × container band width of the
band level (tune in replay; cite the chosen value in a comment).

### B2 — Phase 3 addition: PredictNext target from container

target_tf = container_tf (not a fixed mapping). If no container exists
(all TFs compressed), target falls back to the Part 4 Rule 2 scenario table.

### B3 — Phase 4 additions to DecideAction:

1. ENTRY VETO (checked before every E1–E6, after the unconditional
   loss check):
```cpp
   // Part 5 entry-at-target veto — 03.03 failure class
   if(dir==1 && s.priceloc_container >= +1) return WAIT_or_E3_fade;
   if(dir==2 && s.priceloc_container <= -1) return WAIT_or_E3_fade;
```
2. X2 qualifier per EDIT W1c: an M15 fade triggers X2 in zigzag phases only if
   container cracking (container_diffbbw <= 0 || container mid in {3,4,5})
   || stalled ≥3 bars short of target || target band invalidated.

### B4 — Phase 0 fixture addition

Add columns to march2026_expected.csv: expected_container_tf,
expected_priceloc_container — derivable for at least the trade-event rows
(03.03 07:45 row must show priceloc=+1/+2 vs D1 → veto fires → expected
action changes from the historical BUY to WAIT/E3-fade). Add a benchmark
item 5 to march2026_benchmark.md:

```
5. The 03.03 07:45 BUY must be VETOED by the entry-at-target check
   (priceloc at D1 upper). Replay must show condition_id="VETO-AT-TARGET"
   or an E3 SELL fade at that bar — never a BUY.
```

### Commit B (with the scaffold phases as they execute):
include in the Phase 2/3/4 commit messages: "+ container check (Step 2b)"

---

## POST-EDIT VERIFICATION

### Part A — Document (run after Commit A)

Ask Claude Code:
```
Read references/backtest_chart_analysis.md and confirm:
1. Does "## Step 2b — MTF Container Check" exist in Part 6? What line?
2. Does its table have 4 rows (Container TF / direction / health / PriceLoc)?
3. Does Step 2b cite the 2026.03.03 shallow-depth-at-boundary failure?
4. Does "Entry-at-target veto" exist in Part 5 after the
   "Entry path priority by phase" block? What line?
5. Does the veto cite 03.03 07:45 BUY @5343.82 / D1 upper 5336 / -191.29?
6. In the "Exit priority by phase" block, does the X2 qualifier now list
   the three conditions (a) container cracking (diffBBW ≤ 0 or mid 5/4/3),
   (b) stalled ≥3 bars short of target, (c) target band invalidated?
7. Does the old qualifier text ("unless price has stalled" without the
   container-cracking clause) still appear anywhere? (must be NO)
8. Confirm no other Part 5/6 content was removed (E/X/B tables intact,
   Steps 1-8 intact).
```

- [ ] Step 2b present in Part 6 between Step 2 and Step 3
- [ ] 4-row container read table present
- [ ] Entry-at-target veto present with 03.03 evidence
- [ ] X2 qualifier upgraded to 3-condition form, old text gone
- [ ] No existing content removed
- [ ] Commit hash reported

### Part B — Scaffold/code (verify during the corresponding phases)

- [ ] Phase 0: march2026_expected.csv has expected_container_tf and
      expected_priceloc_container columns; the 03.03 07:45 row shows
      priceloc +1/+2 vs D1
- [ ] Phase 0: march2026_benchmark.md contains item 5 (VETO-AT-TARGET assertion)
- [ ] Phase 2: ScenarioState has container_tf / container_dir /
      container_diffbbw / priceloc_container, each line carrying a
      "// Part 6 Step 2b" citation
- [ ] Phase 2: the "at band" threshold value is explicit in a comment
      (0.15 × band width or the replay-tuned value)
- [ ] Phase 3: target_tf sourced from container_tf with documented fallback
      to Part 4 Rule 2 table
- [ ] Phase 4: entry veto sits AFTER the unconditional MAX_FLOATING_LOSS
      check and BEFORE all E1-E6 evaluation
- [ ] Phase 4: X2 in zigzag phases requires container-cracking OR stall OR
      target-invalidated — verified by a fixture row where M15 wobbles to 3
      mid-leg with container healthy and replay shows HOLD (e.g. a
      03.17-03.19 row)
- [ ] GATE 4 report: benchmark item 5 PASS — 03.03 07:45 bar yields
      VETO-AT-TARGET or E3 SELL fade, never BUY
- [ ] Replay rerun: items 1-4 still PASS after veto added (the veto must
      not block legitimate mid-band entries — entry count for the window
      remains >= 6)
