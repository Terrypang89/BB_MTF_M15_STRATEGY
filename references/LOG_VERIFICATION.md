# Log Verification

Companion to `backtest_chart_analysis.md` — Part 6 Steps 7-8 (log verification) have been separated from the chart analysis workflow into this document. The chart analysis workflow (Steps 1-6: Read → CHECK HTF → Container → Identify Scenario → Phase → Predict → Act) remains in `backtest_chart_analysis.md`.

---

## Verify Against EA Log

After completing Steps 1–6 visually, verify by extracting EA journal log data.
If your visual analysis disagrees with the log, **the log is ground truth**.

### Log File Location

```
.\Backtest_data\(version)\(YYYYMMDD)_clean.log
```

Where:
- `(version)` = the EA version folder (e.g., `v22.17`, `V30.02`)
- `(YYYYMMDD)` = the backtest date in year-month-day format

**Log format reference:** See `.\log_examples.md` for complete documentation of:
- Journal log output format and field ordering
- AllTF decoder (line_seq_touch, Midline_cross, BBW_stage arrays)
- TRADEINFO field semantics and enum values
- BBTFImpact flag format and index reference
- ATRSL1buf struct fields (dir, Trend, LV, Upper, Lower, ATRSLMid, Val)
- Cascade state decoder (cas_shrinkTF, cas_sqzCount)
- Example log entries with annotated field breakdowns

When grep output is unclear, check `log_examples.md` for the exact field
format before interpreting values.

Example:
```
.\Backtest_data\V30.02\20260606_clean.log
```

### Extraction Commands

#### HTF State (confirms Step 2)

```bash
# D1 state — confirm D1 direction and regime
grep -r "\[D1\]" .\Backtest_data\(version)\(YYYYMMDD)_clean.log | tail -20

# H4 state — confirm H4 direction and regime
grep -r "\[H4\]" .\Backtest_data\(version)\(YYYYMMDD)_clean.log | tail -20

# BBW_stage per TF — confirm regime at each level
grep -r "BBW_stage" .\Backtest_data\(version)\(YYYYMMDD)_clean.log | tail -10

# diffMid_Trend per TF — confirm direction at each level
grep -r "diffMid" .\Backtest_data\(version)\(YYYYMMDD)_clean.log | tail -10

# BBUpDn_state per TF — confirm band movement direction
grep -r "BBUpDn" .\Backtest_data\(version)\(YYYYMMDD)_clean.log | tail -10
```

#### Scenario Identification (confirms Step 3)

```bash
# TRADEINFO chain flags — confirm cascade direction
grep -r "\[TRADEINFO\]" .\Backtest_data\(version)\(YYYYMMDD)_clean.log | tail -10
# Expected match:
#   H2L_flyStrink active    = Scenario B/E (compression)
#   L2H_flyUP/DN active     = Scenario D/F (expansion)
#   H2L_sideway active      = Scenario E4/G (all suppressed)
#   All flags = -1           = Scenario G (direction pivot, transitional)

# BBTFImpact — confirm compression depth = sub-scenario
grep -r "\[BBTFImpact\]" .\Backtest_data\(version)\(YYYYMMDD)_clean.log | tail -10
# Expected match:
#   HTF_Drive_LTF_Sideway:[M15_1]              = B1
#   HTF_Drive_LTF_Sideway:[M15_1, M30_1]       = B2
#   HTF_Drive_LTF_Sideway:[M15_1, M30_1, H1_1] = B3
#   + LTF_Drive_HTF_Fly appearing              = E3 loading / transition to F

# Cascade state values — confirm sub-scenario directly
grep -r "cas_shrinkTF" .\Backtest_data\(version)\(YYYYMMDD)_clean.log | tail -5
grep -r "cas_sqzCount" .\Backtest_data\(version)\(YYYYMMDD)_clean.log | tail -5
# Expected match:
#   cas_shrinkTF=1 → B1    =2 → B2    =3 → B3    =-1 → not in B
#   cas_sqzCount=0 → B     =1 → E1    =2 → E2 (pink)   =3+ → E4/G
```

#### Phase Identification (confirms Step 4)

```bash
# diffBBW — confirm compression/expansion rate = phase
grep -r "diffBBW" .\Backtest_data\(version)\(YYYYMMDD)_clean.log | tail -10
# Expected match:
#   Negative values            = Phase 3 (shrink deepening)
#   Near zero at minimum       = Phase 4 (SQZ floor)
#   Sharply positive           = Phase 5 (expansion)
#   Alternating pos↔neg        = Phase 6 (post-SQZ oscillation)

# SQZ loading and break labels — confirm Phase 4→5 transition
grep -r "MIDLINE_SQZ" .\Backtest_data\(version)\(YYYYMMDD)_clean.log | tail -5
grep -r "SQZ_BREAK" .\Backtest_data\(version)\(YYYYMMDD)_clean.log | tail -5
# Expected match:
#   MIDLINE_SQZ_LOADING    = E3 / Phase 4 (loading state)
#   MIDLINE_SQZ_ENTRY      = Phase 4→5 transition (entry fires)
#   SQZ_BREAK_UP           = Phase 5 BUY direction
#   SQZ_BREAK_DN           = Phase 5 SELL direction

# Cascade touch and pink zone events — confirm Phase boundary hits
grep -r "CASCADE_TOUCH" .\Backtest_data\(version)\(YYYYMMDD)_clean.log | tail -5
grep -r "CASCADE_PINK" .\Backtest_data\(version)\(YYYYMMDD)_clean.log | tail -5
# Expected match:
#   CASCADE_TOUCH(TF:n upper_band) = confinement boundary hit (E3 entry check)
#   CASCADE_TOUCH(TF:n lower_band) = confinement boundary hit
#   CASCADE_PINK_ZONE              = Phase 4 / E2 pink zone (exit all)
```

#### Trade Action (confirms Step 6)

```bash
# Entry gate fires — confirm entry conditions E1-E6
# v31 labels:
grep -r "E3:\|E4-ARM\|ORD:BUY\|ORD:SELL" .\Backtest_data\(version)\(YYYYMMDD)_clean.log | tail -10
# E3: boundary fade entry; E4-ARM: loading; ORD:BUY/SELL: order placed
# legacy labels (pre-v31):
grep -r "G6-BUY\|G6-SELL\|G6-LOAD" .\Backtest_data\(version)\(YYYYMMDD)_clean.log | tail -10
# G6-BUY/SELL maps to: E1/E2/E5; G6-LOAD maps to: E4

# Exit gate fires — confirm exit conditions X1-X4
# v31 labels:
grep -r "X1:\|X2:" .\Backtest_data\(version)\(YYYYMMDD)_clean.log | tail -5
# X1: target reached; X2: qualified fade (carries reason string)
# legacy labels (pre-v31):
grep -r "G8-BNDTGT" .\Backtest_data\(version)\(YYYYMMDD)_clean.log | tail -5
grep -r "G5-FADE" .\Backtest_data\(version)\(YYYYMMDD)_clean.log | tail -5
grep -r "G5-WEAK" .\Backtest_data\(version)\(YYYYMMDD)_clean.log | tail -5

# Block gate fires — confirm block conditions B1-B4
# v31 labels:
grep -r "X4-PINK\|VETO-AT-TARGET\|EMERGENCY\|ASSERT" .\Backtest_data\(version)\(YYYYMMDD)_clean.log | tail -5
# X4-PINK: pink zone; VETO-AT-TARGET: entry veto; EMERGENCY: max loss
# ASSERT-B1..B4: consistency failures (should be zero)
# legacy labels (pre-v31):
grep -r "G0b-PINK\|PINK_ZONE" .\Backtest_data\(version)\(YYYYMMDD)_clean.log | tail -5
grep -r "G0c-SQZLOCK\|SQZLOCK" .\Backtest_data\(version)\(YYYYMMDD)_clean.log | tail -5

# ATRSL stop levels — confirm stop placement
grep -r "ATRSL" .\Backtest_data\(version)\(YYYYMMDD)_clean.log | tail -5
# dir:0 = tracking upward (BUY trailing stop)
# dir:1 = tracking downward (SELL trailing stop)
```

### Verification Checklist

Match log values against expected values for your identified scenario:

| Your visual observation (Steps 1-4) | Log field to verify | Expected log value if correct |
|---|---|---|
| D1 sideway on chart | D1 diffMid_Trend | 3, 4, or 5 |
| D1 fly up on chart | D1 diffMid_Trend | 1 |
| D1 fly down on chart | D1 diffMid_Trend | 2 |
| H4 fly on chart | H4 BBW_stage | 511 or 512 |
| H4 shrinking on chart | H4 BBUpDn_state | 2 (shrinking) |
| H4 SQZ on chart | H4 BBW_stage | 400-499 |
| M15 sideways (blocking entry) | M15 diffMid_Trend | ≥ 3 |
| M30 SQZ but still in trade | M30 BBW_stage | 400-499 (NOT a block alone) |
| Pink zone — exit all | CASCADE_PINK_ZONE | Present in log |
| Phase 3 (legs shortening) | diffBBW_H4 | Negative values |
| Phase 4 (noise oscillation) | diffBBW_H4 | Near zero |
| Phase 5 (explosive breakout) | SQZ_BREAK_UP or SQZ_BREAK_DN | Present in log |
| Phase 6 (equal legs post-SQZ) | diffBBW_H4 | Alternating positive and negative |
| Scenario B1 | cas_shrinkTF | 1 |
| Scenario B2 | cas_shrinkTF | 2 |
| Scenario B3 | cas_shrinkTF | 3 |
| Scenario E2 (pink zone) | cas_sqzCount | ≥ 2 |
| Scenario G (all SQZ) | TRADEINFO all flags | -1 |
| Entry fired | G6-BUY or G6-SELL | Present in log at expected bar |
| Target exit | G8-BNDTGT | Present in log at target level |
| Forced exit (pink) | G0b-PINK | Present in log |

### When Log Disagrees With Chart

| Situation | Likely cause | Action |
|---|---|---|
| Chart shows H4 fly but log shows H4 BBUpDn=2 | H4 just entered shrink — visual lags behind computation | Trust log — reassess as Scenario B |
| Chart shows SQZ but log shows BBW_stage=513 | Not yet full SQZ — still in late shrink | Wait — not Phase 4 yet, still Phase 3 |
| Chart shows breakout but no SQZ_BREAK label | M5 broke but M15 hasn't confirmed yet | Wait — still E3/F1, not Phase 5 |
| Log shows G6-BUY fired but chart looks sideways | Entry valid by computed values — visual is deceptive | Trust entry condition — use small size, tight stop |
| Log shows pink zone but chart looks tradeable | M15+M30 both hit BBW 400-499 — hard block | Trust log — EXIT ALL, do not override pink zone |
| cas_shrinkTF=3 but chart shows H1 still fly | H1 just entered shrink — band hasn't visually changed yet | Trust log — H1 shrink confirmed, reduce to 0.25× |
| TRADEINFO all=-1 but chart shows M30 fly | Chain detection couldn't confirm sustained chain | Likely Phase 6 or H4 transition — treat with caution |

### Multi-Day Verification Example

For verifying D1 sideway over multiple days:

```bash
# Extract past 5 days of D1 state from multiple log files
grep -r "\[D1\]" .\Backtest_data\V30.02\20260606_clean.log | tail -5
grep -r "\[D1\]" .\Backtest_data\V30.02\20260606_clean.log | tail -5
grep -r "\[D1\]" .\Backtest_data\V30.02\20260606_clean.log | tail -5
grep -r "\[D1\]" .\Backtest_data\V30.02\20260606_clean.log | tail -5
grep -r "\[D1\]" .\Backtest_data\V30.02\20260606_clean.log | tail -5

# Or use wildcard for date range
grep -r "\[D1\]" .\Backtest_data\V30.02\20260606_clean.log | tail -25
```

Confirm D1 diffMid_Trend = 3/4/5 across all extracted lines = D1 sideway confirmed.
If D1 diffMid_Trend = 1 or 2 appears in any line = D1 still has direction, NOT sideway.

### Full Verification Workflow Example

```
1. Chart shows: H4-fly-- labels, M30 oscillating, legs shortening
   Visual assessment: Scenario B3, Phase 3a

2. Extract log:
   grep -r "cas_shrinkTF" (log) → cas_shrinkTF=3 ✅ matches B3
   grep -r "diffBBW_H4" (log) → negative values ✅ matches Phase 3
   grep -r "\[BBTFImpact\]" (log) → HTF_Drive_LTF_Sideway:[M15_1,M30_1,H1_1] ✅ matches B3
   grep -r "\[TRADEINFO\]" (log) → H2L_flyStrink:3 ✅ matches compression

3. All match → visual assessment confirmed
   Proceed to Part 4 prediction with HIGH confidence in scenario identification

4. If mismatch found:
   grep shows cas_shrinkTF=2 (not 3) → actually B2, not B3
   → Reassess: H1 hasn't entered shrink yet — adjust size from 0.25× to 0.50×
```

---

## Practical Log Verification Tutorial

This section shows how to extract a specific period from the log,
read each field, identify the scenario and phase, and explain
what the EA should do next.

**Log format reference:** See `.\references\log_examples.md` for complete
field documentation, enum values, and annotated examples.

---

### How to Extract a Specific Period

Identify the date range and timeframes you want to verify from your chart.
Then extract using these patterns:

```bash
# Get all entries for a specific date
type .\Backtest_data\V30.02\20260306_clean.log

# Get entries for a specific time window (e.g., 08:00-12:00)
findstr "08:\|09:\|10:\|11:" .\Backtest_data\V30.02\20260306_clean.log

# Get only the AllTF summary lines (contains all TF states in one line)
findstr "AllTF" .\Backtest_data\V30.02\20260306_clean.log

# Get H4 state changes only
findstr "\[H4\]" .\Backtest_data\V30.02\20260306_clean.log

# Get trade entry/exit events
findstr "G6-BUY\|G6-SELL\|G8-BNDTGT\|G5-FADE\|PINK" .\Backtest_data\V30.02\20260306_clean.log

# Get cascade state across multiple days
findstr "cas_shrinkTF\|cas_sqzCount" .\Backtest_data\V30.02\2026030*_clean.log
```

**PowerShell alternative (if findstr not available):**

```powershell
# Get all entries for specific date
Get-Content .\Backtest_data\V30.02\20260306_clean.log

# Filter by time window
Select-String -Path .\Backtest_data\V30.02\20260306_clean.log -Pattern "08:|09:|10:|11:"

# Filter by field
Select-String -Path .\Backtest_data\V30.02\20260306_clean.log -Pattern "AllTF"

# Multi-day D1 state
Select-String -Path .\Backtest_data\V30.02\2026030*_clean.log -Pattern "\[D1\]"
```

---

### How to Read Extracted Log Data

When you extract a log line, read these fields in order:

```
Step 1: Read TIMESTAMP — what bar is this?
Step 2: Read BBW_stage per TF — what regime LABEL is each TF in?
Step 3: Read diffMid_Trend per TF — what direction is each TF?
Step 4: Read diffBBW per TF — is band expanding or contracting?
Step 5: CROSS-CHECK Steps 2+3+4 — does the regime label match reality?
Step 6: Read BBUpDn_state per TF — what are bands doing?
Step 7: Read TRADEINFO — what cascade chains are active?
Step 8: Read BBTFImpact — what's being suppressed/driving?
Step 9: Read any gate fires — did entry/exit/block trigger?
```

**Field value quick reference (while reading log):**

| Field | Values | Quick meaning |
|---|---|---|
| BBW_stage | 511/512 | FLY (expanding/parallel) |
| BBW_stage | 513/523 | SHRINK |
| BBW_stage | 400-499 | SQZ |
| diffMid_Trend | 1 | Uptrend |
| diffMid_Trend | 2 | Downtrend |
| diffMid_Trend | 3/4/5 | Sideways / flat |
| BBUpDn_state | 0 | no_state (SQZ or transition) |
| BBUpDn_state | 1 | expanding (upper↑ lower↓) |
| BBUpDn_state | 2 | shrinking (upper↓ lower↑) |
| BBUpDn_state | 3 | up (both bands rising) |
| BBUpDn_state | 4 | dn (both bands falling) |
| diffBBW | positive | Band expanding — fly has momentum |
| diffBBW | negative | Band contracting — shrink active |
| diffBBW | near zero | SQZ floor or parallel fly |
| cas_shrinkTF | 1/2/3 | M15/M30/H1 is highest shrink TF |
| cas_sqzCount | 0/1/2/3+ | Number of TFs in SQZ |

### BBW_stage Cross-Check Rule

BBW_stage is a LAGGING label — it classifies the regime AFTER the transition
has already started. diffMid_Trend and diffBBW move FIRST and are more accurate
for real-time scenario identification.

**Always cross-check BBW_stage against diffMid_Trend + diffBBW:**

| BBW_stage says | diffMid says | diffBBW says | Actual state | Trust |
|---|---|---|---|---|
| 511 (fly) | 1 (uptrend) | Positive (expanding) | Fly confirmed ✅ | All agree |
| 511 (fly) | 3 (sideways) | Near zero | Fly ENDING — about to shrink | Trust diffMid+diffBBW |
| 511 (fly) | 3 (sideways) | Negative | Already shrinking — BBW_stage hasn't updated | Trust diffBBW — actually 513 |
| 513 (shrink) | 2 (downtrend) | Negative | Shrink confirmed ✅ | All agree |
| 513 (shrink) | 3 (sideways) | Near zero | Approaching SQZ — shrink ending | Trust diffBBW — nearing 400-499 |
| 513 (shrink) | 1 (uptrend) | Positive | Already expanding — BBW_stage hasn't updated | Trust diffMid+diffBBW — actually 511 |
| 400-499 (SQZ) | 3 (sideways) | Near zero | SQZ confirmed ✅ | All agree |
| 400-499 (SQZ) | 1 or 2 | Positive | SQZ breaking — BBW_stage hasn't updated | Trust diffMid+diffBBW — breakout started |

**Priority order when values conflict:**
1. diffBBW — fastest signal (band width velocity changes first)
2. diffMid_Trend — second signal (midline direction shifts)
3. BBW_stage — slowest (regime label updates last)

**Practical rule:** If diffBBW and diffMid_Trend both contradict BBW_stage,
ignore BBW_stage — the regime has already changed, the label just hasn't caught up.
This is especially critical at Phase 3→4 and Phase 4→5 transitions where
BBW_stage may still show 513 while diffBBW has already turned positive (expansion started).

---

### Worked Example — Identifying Scenario B2 from Log

**Chart observation:** H4-fly-- labels visible, M30 bands tightening,
M15 oscillating with shortening legs. Visually assessed as Scenario B2, Phase 3a.

**Step 1: Extract the relevant period**

```bash
findstr "AllTF" .\Backtest_data\V30.02\20260306_clean.log | findstr "10:00\|10:15\|10:30"
```

**Step 2: Read the extracted fields**

```
Example output (simplified):
  10:00 BBW_stage: [H4:512, H1:512, M30:513, M15:513, M5:400]
        diffMid:   [H4:1,   H1:1,   M30:2,   M15:3,   M5:3]
        BBUpDn:    [H4:3,   H1:1,   M30:2,   M15:2,   M5:0]
        diffBBW:   [H4:-1.2, H1:-0.8, M30:-2.1, M15:-1.5, M5:-0.3]
```

**Step 3: Map each TF to the variable definitions**

| TF | BBW_stage | diffMid | diffBBW | Cross-check | BBUpDn | Meaning |
|---|---|---|---|---|---|---|
| H4 | 512 (FLY parallel) | 1 (uptrend) | -1.2 (contracting) | ⚠️ BBW says fly but diffBBW negative — fly WEAKENING, approaching shrink | 3 (up) | Both bands moving up |
| H1 | 512 (FLY parallel) | 1 (uptrend) | -0.8 (contracting) | ⚠️ Same — fly label but contracting — H1 will enter shrink soon | 1 (expanding) | Expanding |
| M30 | 513 (SHRINK) | 2 (downtrend) | -2.1 (contracting) | ✅ All agree — shrink confirmed and accelerating | 2 (shrinking) | Shrinking |
| M15 | 513 (SHRINK) | 3 (sideways) | -1.5 (contracting) | ✅ Shrink + sideways = B1 block active (M15 no direction) | 2 (shrinking) | Shrinking |
| M5 | 400 (SQZ) | 3 (sideways) | -0.3 (barely contracting) | ✅ SQZ confirmed — diffBBW near zero = SQZ floor | 0 (no_state) | SQZ |

**Step 4: Identify scenario from log values**

```
CHECK HTF:
  H4 = 512 (fly) + mid=1 (uptrend) + BBUpDn=3 (up) → H4 fly intact ✅
  D1 = (extract separately) → need to check

CHECK compression depth:
  M30 = 513 (shrink) → M30 has entered shrink
  M15 = 513 (shrink) → M15 also shrinking
  H1 = 512 (still fly) → H1 NOT shrinking yet

  cas_shrinkTF would = 2 (M30 is highest shrink TF) → Scenario B2 ✅

CHECK phase:
  diffBBW_H4 = -1.2 (negative) → compression active → Phase 3
  H4 mid = 1 (uptrend lean) → Phase 3b-INTO (not 3a — H4 has lean)
  → BUT M15 diffMid = 3 (sideways) → B1 block active for new entries
```

**Step 5: Determine expected behavior**

```
Scenario: B2 (M30 shrink, H4 fly intact)
Phase: 3b-INTO (BUY trending — H4 mid=1)
Block: B1 active (M15 diffMid=3 — no new entry until M15 restores direction)

Expected EA behavior:
  ✗ No new entry — M15 sideways blocks entry (B1)
  ✓ Existing BUY position HOLDS — H4 still fly up
  ✓ Size should be at 0.50× (B2 depth)
  ✓ diffBBW negative = legs shortening on chart (Phase 3 confirmed)

What happens next (Part 4 prediction):
  Direction: BUY legs favoured (H4 mid=1) but shortening
  Target: H1 outer band per leg (H1 is highest still-flying MTF)
  Timeline: 3-8 hours per leg, compression continues
  Next: If M5 BBUpDn 0→1 same dir as H4 → Scenario D (rest)
        If H1 also enters 513 → B3 (depth increases, size → 0.25×)

Verify prediction by checking next few bars:
  findstr "10:45\|11:00\|11:15" (log) → does M15 mid flip to 1 or 2?
  If yes → B1 clears, new BUY entry valid (E5)
  If stays 3 → still blocked, wait
```

---

### Worked Example — Identifying Scenario E2 (Pink Zone) from Log

**Chart observation:** Price chopping sideways, bands extremely tight,
no impulse legs visible. Visually assessed as Phase 4.

**Step 1: Extract**

```bash
findstr "cas_sqzCount\|PINK" .\Backtest_data\V30.02\20260307_clean.log | findstr "14:00\|14:15\|14:30"
```

**Step 2: Read**

```
Example output:
  14:00 cas_sqzCount=2
  14:15 CASCADE_PINK_ZONE
  14:15 cas_sqzCount=2
```

**Step 3: Map**

```
cas_sqzCount = 2 → two TFs in SQZ (M15+M30 both 400-499) → Scenario E2
CASCADE_PINK_ZONE appeared → B2 block active → EXIT ALL
```

**Step 4: Identify**

```
Scenario: E2 (LTF full SQZ)
Phase: Phase 4 (compressed oscillation)
Block: B2 active (pink zone — M15+M30 both SQZ)
Action: EXIT ALL positions — no exceptions
```

**Step 5: Expected behavior**

```
Expected EA behavior:
  ✗ All positions CLOSED when CASCADE_PINK_ZONE fired
  ✗ No new entries allowed — B2 hard block
  ✓ Wait for M5 BBUpDn 0→1 (E3 loading → Phase 5 breakout)

What to watch next:
  findstr "SQZ_BREAK\|G6-LOAD" (log) → M5 expansion signal
  If SQZ_BREAK_UP appears → Phase 5 BUY direction → arm entry (E4)
  If SQZ_BREAK_DN appears → Phase 5 SELL direction → arm entry (E4)
  Neither → still Phase 4, wait

Verify by extracting next hour:
  findstr "15:00\|15:15\|15:30" (log)
  → check if cas_sqzCount drops below 2 (SQZ releasing)
  → check if diffBBW turns positive (expansion beginning)
```

---

### Worked Example — Identifying Phase 6 (Post-SQZ Oscillation) from Log

**Chart observation:** After SQZ breakout, H4 keeps cycling between
fly and SQZ. Equal-height legs, no decay. Visually assessed as Phase 6.

**Step 1: Extract multiple days**

```bash
findstr "BBUpDn.*H4\|TRADEINFO" .\Backtest_data\V30.02\2026031*_clean.log
```

**Step 2: Read H4 BBUpDn pattern over days**

```
Example output:
  Mar 10 09:00  H4 BBUpDn=1 (expanding)
  Mar 10 13:00  H4 BBUpDn=2 (shrinking)
  Mar 10 17:00  H4 BBUpDn=0 (SQZ)
  Mar 10 21:00  H4 BBUpDn=1 (expanding again)
  Mar 11 01:00  H4 BBUpDn=2 (shrinking again)
  Mar 11 05:00  H4 BBUpDn=0 (SQZ again)
  Mar 11 09:00  H4 BBUpDn=1 (expanding again)
  ...pattern repeats
```

**Step 3: Identify the cycling pattern**

```
H4 BBUpDn: 1 → 2 → 0 → 1 → 2 → 0 → 1 → ...
           (expanding → shrinking → SQZ → expanding → ...)

This is NOT sustained expansion (would be 1,1,1,1...)
This is NOT sustained shrink (would be 2,2,2,2...)
This is CYCLING — H4 cannot commit to a direction

TRADEINFO: all flags frequently = -1 (no sustained chain)
→ Phase 6 confirmed (post-SQZ oscillation, H4 uncommitted)
```

**Step 4: Check D1 for resolution bias**

```bash
findstr "\[D1\]" .\Backtest_data\V30.02\2026031*_clean.log
```

```
D1 diffMid = 1 across all days → D1 still fly uptrend
→ D1 gives upward bias → H4 will EVENTUALLY commit upward
→ But not yet — Phase 6 continues until H4 BBUpDn sustains 1 for 3+ bars

D1 diffMid = 3 across recent days → D1 losing direction too
→ Scenario I territory (macro sideways) → may persist weeks
```

**Step 5: Expected behavior**

```
Scenario: Extended G4 whipsaw (Scenario G4 sub-state)
Phase: Phase 6 (post-SQZ oscillation)
D1 bias: uptrend (D1 mid=1)

Expected EA behavior:
  ✓ Each H4 cycle IS tradeable but at 0.25× max
  ✓ Entry at H4 boundary (E3 confinement entry) each cycle
  ✓ Exit at OPPOSITE H4 boundary (X1) — do not hold through reversal
  ✓ Slightly favour BUY legs (D1 bias = uptrend)

Resolution watch:
  Monitor H4 BBUpDn — when it sustains 1 for 3+ consecutive H4 bars:
  → Phase 6 ends → Phase 5 (committed breakout) → Scenario F
  findstr "BBUpDn.*H4" (log) → look for three consecutive "1" values
```

---

### Verification Summary — What to Extract for Each Scenario

Quick reference for which log fields to extract depending on
what you're trying to verify:

| What you're verifying | Extract these fields | Expected pattern |
|---|---|---|
| Scenario A (all fly) | BBW_stage all TFs, TRADEINFO | All 511/512, H2L_flyUP/DN active |
| Scenario B depth | cas_shrinkTF, BBTFImpact | cas_shrinkTF = 1/2/3, HTF_Drive count |
| Scenario E depth | cas_sqzCount, CASCADE_PINK | cas_sqzCount ≥ 2, PINK if E2 |
| Scenario G (direction pivot) | H4 BBUpDn over 3+ bars, TRADEINFO | H4 BBUpDn sustains 1 or 4, all TRADEINFO = -1 before |
| Scenario D (rest) | M5 BBUpDn, M15 diffMid, H4 BBW | M5 BBUpDn 0→1, M15 mid flips, H4 still 511/512 |
| Scenario F (release) | M30 BBUpDn, H4 BBUpDn | M30 BBUpDn=1, H4 BBUpDn 0→? |
| G reversal C1→E4→G2→C2/C3 | H4 BBUpDn direction, D1 diffMid | H4 BBUpDn=1 opposite to previous, D1 may be flipping |
| Phase 3 (legs shortening) | diffBBW_H4 over time | Negative values, getting more negative |
| Phase 4 (SQZ noise) | diffBBW_H4, cas_sqzCount | Near zero, sqzCount ≥ 2 |
| Phase 5 (breakout) | SQZ_BREAK label, diffBBW_H4 | SQZ_BREAK_UP/DN present, diffBBW sharply positive |
| Phase 6 (cycling) | H4 BBUpDn over days | Pattern: 1→2→0→1→2→0 repeating |
| M15 block (B1) | M15 diffMid_Trend | ≥ 3 (sideways — blocking new entries) |
| Pink zone (B2) | CASCADE_PINK_ZONE | Present in log — EXIT ALL |
| Entry fired | G6-BUY/SELL/LOAD | Present at expected timestamp |
| Target exit | G8-BNDTGT | Present at expected price level |
