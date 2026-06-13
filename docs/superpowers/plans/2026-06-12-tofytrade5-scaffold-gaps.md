# TofyTrade5 Scaffold Gaps Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the missing pieces of EDIT PART 11 — decide_action in replay harness, benchmark scoring, RC regression suite, and phase commits.

**Architecture:** Python replay harness mirrors TofyTrade5.mqh Layer 3 (DecideAction) logic. RC regression suite derives expected behavior from document rules, not hardcoded timestamps.

**Tech Stack:** Python 3, CSV, MQL5 (existing TofyTrade5.mqh)

---

### Task 1: Implement decide_action() in replay_harness.py

**Files:**
- Modify: `scripts/replay_harness.py`

Context from TofyTrade5.mqh (Layer 3):
- Entry conditions: E1/E2 (flip-path, PH_1/2), E3 (zigzag boundary fade, PH_2/3A/3B/6), E5 (PH_5), E6 (F3/C2)
- Exit conditions: X1 (boundary target), X2 (M15 fade with W1c qualifiers), X4 (B2 pink forced exit)
- Block rules: B1 (M15 mid>=3), B2 (M15+M30 both SQZ), B3 (H4 committed opposing fly — disabled when H4 mid=3, diffBBW contradicts, PH_3A/6), B4 (cas_sqzCount>=3)
- Sizing: size_mult = min(matrix_ceiling, conf_size, decoder_size)
- Invariants: MAX_FLOATING_LOSS_USD=$50, MIN_HOLD_BARS=3, POST_EXIT_COOLDOWN=5

- [ ] **Step 1: Add decide_action() function**

Implement Python version of DecideAction mirroring TofyTrade5.mqh:

```python
def decide_action(tf_states, diffbbw_h4_history, close_m15, s):
    """Decide trade action from TF states, scenario state, and price.

    Mirrors TofyTrade5.mqh Layer 3 DecideAction.
    Returns dict with: act (0=hold, 1=BUY, 2=SELL, 7=exit),
                      condition_id (E1-E6/X1-X4/WAIT),
                      size_mult, info
    """
    # --- Block checks ---
    if s['b2_pink']:
        return {'act': 7, 'condition_id': 'X4', 'size_mult': 0, 'info': 'B2 pink forced exit'}
    if s['cas_sqzCount'] >= 3:
        return {'act': 0, 'condition_id': 'B4', 'size_mult': 0, 'info': 'cas_sqzCount>=3'}

    # --- Matrix ceiling ---
    ceiling = matrix_ceiling(s['scenario'])
    if ceiling <= 0:
        return {'act': 0, 'condition_id': 'WAIT', 'size_mult': 0, 'info': 'ceiling=0'}

    # --- E3: zigzag boundary entry ---
    zigzag = s['phase'] in ('PH_2','PH_3A','PH_3B_INTO','PH_3B_OUT','PH_6')
    if zigzag and s['container_tf'] > 0:
        # compute priceloc vs container band
        # if E3Check passes, return E3 entry

    # --- Flip-path entries (E1/E2/E5) ---
    if s['phase'] in ('PH_1','PH_2','PH_5') and not s['b1_block']:
        # detect M15 mid flip, return E1/E2/E5

    return {'act': 0, 'condition_id': 'WAIT', 'size_mult': 0, 'info': ''}
```

- [ ] **Step 2: Add helper functions**

Add `matrix_ceiling(scenario)`, `conf_size(confidence)`, `decoder_size(cas_sqzCount, cas_shrinkTF, b2_pink)`, `e3_check(tf_states, s, direction)`, `detect_flip(tf_states)` mirroring the MQL5 functions.

- [ ] **Step 3: Add trade simulation loop**

Extend main() to run decide_action over all snapshots, maintaining position state (flat/buy/sell), tracking entries/exits with timestamps and condition IDs.

- [ ] **Step 4: Commit**

```bash
git add scripts/replay_harness.py
git commit -m "Phase 1: add decide_action and trade simulation to replay harness"
```

### Task 2: Benchmark scoring

**Files:**
- Modify: `scripts/replay_harness.py`

- [ ] **Step 1: Add benchmark scoring function**

```python
def score_benchmark(trades, benchmark_md):
    """Score trade list against march2026_benchmark.md items 1-4."""
    # Item 1: scenario match >= 95% (already done in GATE 1)
    # Item 2: >= 6 leg-capture entries from verified arrow legs
    # Item 3: max adverse excursion <= M30-band stop at entry
    # Item 4: zero positions held > 3 days
    return {'item1': pass_fail, 'item2': n_legs, 'item3': max_excursion, 'item4': max_holds}
```

- [ ] **Step 2: Integrate into main()**

Print PASS/FAIL for each benchmark item after the trade simulation.

- [ ] **Step 3: Commit**

```bash
git add scripts/replay_harness.py
git commit -m "Phase 1: benchmark scoring against march2026_benchmark.md items 1-4"
```

### Task 3: RC Regression Suite

**Files:**
- Create: `references/fixtures/rc_regressions.csv`
- Modify: `scripts/replay_harness.py`

RC incidents from TofyTrade4.mqh:
| RC | Date | Gate | Loss | Description |
|----|------|------|------|-------------|
| RC16 | Mar-02 | G4c-M15OPP | -62.63 | G5-EARLY BUY with M15 SQZ bearish |
| RC18 | Feb-09/Feb-27/Apr-20 | G4e-H4OPP | -11.49/-15.72/-20.19 | H4 shrink mid=3 opposing |
| RC24 | (in log) | G4j-D1OPP | ? | D1 opposing in H4-SQZ path |
| RC31 | Apr-24 | G4k-TRIGDIR | -16.01 | M30 bullish fly, midtrend fires SELL |
| RC35 | Apr-27 | G4c-H1OPP | -32.41 | H1 fly mid=3 opposing |
| RC39 | (in log) | G4k-confirmTF | ? | confirmTF flat mid=3 |
| RC17 | (in log) | G4g-H1H4SQZ | ? | H4+H1 both SQZ |
| RC20b | (in log) | G4h-H4M30SQZ | ? | H4+M30 both SQZ |
| RC21 | (in log) | G4i-H4M30FLY | ? | H4 SQZ + M30 opposing fly |

- [ ] **Step 1: Create rc_regressions.csv**

For each RC incident with a date in the log, derive expected_new_behavior from the TofyTrade5 architecture:
- Most should be "no entry — scenario X / confidence below floor" or "entry allowed but stop limits loss"
- The new architecture handles these via scenario classification, not dedicated veto gates

- [ ] **Step 2: Add RC regression runner to replay_harness.py**

For each row in rc_regressions.csv, find the snapshot at that timestamp, run identify_scenario + decide_action, and report whether the original loss would have been avoided.

- [ ] **Step 3: Commit**

```bash
git add references/fixtures/rc_regressions.csv scripts/replay_harness.py
git commit -m "Phase 5: RC incident regression suite — N/M incidents covered by architecture"
```

### Task 4: Phase commits for TofyTrade5.mqh (Phases 2-4)

Since TofyTrade5.mqh was already written but not committed per phase, create the phase commits.

- [ ] **Step 1: Commit Phase 2** — IdentifyScenario
- [ ] **Step 2: Commit Phase 3** — PredictNext
- [ ] **Step 3: Commit Phase 4** — DecideAction

### Task 5: Final commit and report

- [ ] **Step 1: Run final commit sequence from EDIT PART 11**

```bash
git add references/backtest_chart_analysis.md
git commit -m "Encode March 2026 verification findings: B3 H4-OPPOSE scope limits, E3 primary entry in zigzag phases, X1-before-X2 exit hierarchy, diffBBW-primary scenario ID, decoder size override"
```

- [ ] **Step 2: Generate final report** — fixture stats, match %, benchmark scorecard, RC coverage, commit hashes
