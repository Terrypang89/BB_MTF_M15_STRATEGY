# Task Force — Backtest Analysis Workflow

Standard operating procedure when a new backtest version is released.  
Covers 9 steps: read SOP, net profit comparison, deal loss comparison, fix priority ranking, root cause analysis, code fix, fix verification, reference file updates, and git commit.

**Goal:** Each new version must achieve **higher net profit** than the previous same-period version. Every deal loss < −10 USD is a candidate for a gate fix — prioritize highest absolute loss first.

---

## Overview of the 9-Step Workflow

```
Step 0 → Read this file — load all Python scripts and RC patterns before starting
Step 1 → Net profit comparison vs all previous versions → update references/version_profit.md
Step 2 → Deal-by-deal loss comparison (profit < -10) vs all previous versions → update references/version_profit.md
Step 3 → Set fix priorities: rank NEW losses first, then SAME losses by size descending
Step 4 → Log analysis → root cause write-up in references/root-cause-analysis.md
Step 5 → Code fix in TofyTrade3.mqh → version bump
Step 6 → Verify fixes: trace how each fix eliminates/reduces confirmed loss deals in log_matrix.csv
Step 7 → Update this file (Task_force.md) with new gate, RC patterns, and registry entries
Step 8 → Update all related reference files (CLAUDE.md, fix.md, decision_flow.md, architecture diagrams, etc.)
Step 9 → Git commit all changes with version tag as commit message
```

Before starting, confirm which files exist in the new version folder:

```
references/Backtest_data/V30.XX/
  report_tables_clean.json   ← required for Steps 1 & 2
  log_matrix.csv             ← required for Steps 4 & 6 (gate pattern lookup)
  YYYYMMDD_clean.log         ← required for Step 4 (TRADEINFO line search) — single file V22.30+
  *_clean.log_part_N.txt     ← split format (older versions pre-V22.30, if present)
  metadata.json              ← optional (test period cross-check)
```

---

## Step 1 — Net Profit Comparison

### File formats by version

| Versions | Format | Location |
|----------|--------|----------|
| V30.XX+ | JSON `.json` | `report_tables_clean.json` |

### Python script — full net profit comparison

```python
import json, openpyxl, warnings
warnings.filterwarnings('ignore')

def load_xlsx_net(path):
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb.active
    for row in ws.iter_rows(values_only=True):
        for j, v in enumerate(row):
            if v and 'Total Net Profit' in str(v):
                for k in range(j+1, len(row)):
                    if row[k] is not None:
                        try: return float(row[k])
                        except: pass
    return None

def load_json_net(path):
    with open(path) as f: d = json.load(f)
    tr = d.get('table_results', {})
    if isinstance(tr, list):          # V22.22 format: list of {label, value}
        for item in tr:
            if 'Net Profit' in str(item.get('label','')):
                return float(str(item.get('value',0)).replace(' ','').replace(',',''))
    else:                             # V22.23+ format: dict
        v = tr.get('Total Net Profit', 0)
        return float(str(v).replace(' ','').replace(',',''))
    return None

def get_period(path):
    with open(path) as f: d = json.load(f)
    t0 = d.get('table_0', {})
    if isinstance(t0, list):
        for item in t0:
            if 'Period' in str(item.get('label','')): return item.get('value')
    else:
        return t0.get('Period','?')

versions = {
    'V22.18': ('xlsx', 'references/Backtest_data/V22.18/ReportTester-V30_00.xlsx'),
    # add new version here:
    # 'V22.XX': ('json', 'references/Backtest_data/V22.XX/report_tables_clean.json'),
}

for ver, (fmt, path) in versions.items():
    try:
        n = load_json_net(path) if fmt == 'json' else load_xlsx_net(path)
        period = get_period(path) if fmt == 'json' else 'see xlsx'
        print(f'  {ver}: {n:+.2f}  [{period}]')
    except Exception as e:
        print(f'  {ver}: ERROR {e}')
```

### Interpretation rules

- **Same test period required** for meaningful net profit comparison.
  - V22.22, V22.24, V22.25+: Jan–Apr 2026 (use these as same-period baseline)
  - V22.23: Jan only (Jan-only net profit cannot be compared directly to Jan-Apr versions)
- If periods differ, note it explicitly in root-cause-analysis.md version table.
- Target: new version net profit > previous version **of the same period**.

### Step 1a — Multi-Period Comparison (when _M15 / _M30 folders exist)

**Directory naming convention:**
```
references/Backtest_data/V22.XX/        ← M5 chart period (standard, production)
```

`gen_version_profit.py` auto-detects `_M15` and `_M30` suffixed directories and writes Part 4 of `version_profit.md` with net profit comparison and M5-ONLY loss breakdown table.

**Interpretation:**
- If M30 >> M15 >> M5 in net profit, the M5 trigger is the bottleneck — gate fix approach is correct
- ALL losses in M5 that are absent in M15 and M30 are **M5-ONLY** — direct gate fix candidates
- Shared losses (appear in all periods) are macro/structural — accept or study parameter changes
- The "M5-ONLY %" guides priority: if 100% of M15 losses are M15-ONLY, gate fixes are the primary lever

---

## Step 2 — Deal Loss Comparison (profit < -10)

### Python script — full deal comparison

```python
import json, openpyxl, warnings
warnings.filterwarnings('ignore')

def load_json_deals(path):
    with open(path) as f: d = json.load(f)
    deals = d.get('table_deals', [])
    result = {}
    for deal in deals:
        try:
            t = str(deal.get('Time',''))
            p = float(str(deal.get('Profit',0)).replace(' ','').replace(',',''))
            if t not in ('','nan') and p < -10:
                result[t] = p
        except: pass
    return result

def load_xlsx_deals(path):
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb.active
    time_col = profit_col = None
    header_row = None
    for i, row in enumerate(ws.iter_rows(values_only=True), 1):
        if row and 'Time' in str(row) and 'Profit' in str(row):
            header_row = i
            for j, v in enumerate(row):
                if str(v) == 'Time': time_col = j
                if str(v) == 'Profit': profit_col = j
            break
    result = {}
    if header_row and time_col is not None and profit_col is not None:
        for row in ws.iter_rows(min_row=header_row+1, values_only=True):
            try:
                t = str(row[time_col])
                p = float(str(row[profit_col]).replace(' ','').replace(',',''))
                if t not in ('','None','nan') and p < -10:
                    result[t] = p
            except: pass
    return result

# Compare NEW version (e.g. V22.25) against most recent same-period baseline
prev = load_json_deals('references/Backtest_data/V22.24/report_tables_clean.json')  # ← change
curr = load_json_deals('references/Backtest_data/V22.XX/report_tables_clean.json')   # ← change

all_times = sorted(set(list(prev.keys()) + list(curr.keys())))
eliminated = new_losses = same = better = worse = 0
elim_sum = new_sum = 0

print(f'{"Time":<22} {"PREV":>10} {"CURR":>10} {"Delta":>10} {"Status":<12}')
print('-'*70)

for t in all_times:
    pp = prev.get(t)
    pc = curr.get(t)
    if pp is not None and pc is None:
        eliminated += 1; elim_sum += pp
        print(f'{t:<22} {pp:>10.2f} {"(gone)":>10} {-pp:>+10.2f} ELIMINATED')
    elif pp is None and pc is not None:
        new_losses += 1; new_sum += pc
        print(f'{t:<22} {"(new)":>10} {pc:>10.2f} {pc:>+10.2f} NEW')
    else:
        delta = pc - pp
        status = 'SAME' if abs(delta)<0.5 else ('WORSE' if delta<0 else 'BETTER')
        if status != 'SAME': print(f'{t:<22} {pp:>10.2f} {pc:>10.2f} {delta:>+10.2f} {status}')
        if status == 'SAME': same += 1
        elif status == 'BETTER': better += 1
        else: worse += 1

print()
print(f'Eliminated: {eliminated}  (recovered: {-elim_sum:.2f})')
print(f'NEW losses: {new_losses}  (total: {new_sum:.2f})')
print(f'SAME: {same}  BETTER: {better}  WORSE: {worse}')
```

### Categorizing results

| Status | Meaning | Action |
|--------|---------|--------|
| ELIMINATED | Fix worked — old deal no longer occurs | Confirm which gate blocked it |
| SAME | Persistent unresolved loss | Add to root-cause-analysis.md if not already there |
| NEW | Regression introduced by fix | Highest priority — trace entry in log |
| WORSE | Same deal but larger loss | Check if SL/exit changed |
| BETTER | Same deal, smaller loss | Note as partial improvement |

---

## Step 3 — Set Fix Priorities

After Step 2, build a ranked fix list before writing any code:

1. **NEW losses first** (regressions from current version's changes — must be traced and fixed)
2. **SAME losses** ordered by absolute value, largest first — work top-to-bottom through the list
3. **WORSE losses** — investigate replacement entry phenomenon before adding a new gate

For each candidate deal, pre-check viability:
- Estimate losses blocked vs wins blocked (net improvement must be positive)
- Check the Root Cause Decision Tree below — has this pattern been seen and deferred before?
- If net improvement < 0 → mark as "deferred, net negative" and skip to the next deal

**Net profit goal:** new fix version net > VER net. If the top-priority fix is insufficient, stack the next-largest deal on top — but only if both fixes are independently safe (no gate interaction).

---

## Step 4 — Root Cause Analysis

### Step 4a — Find entry gate for each NEW or large SAME loss

**Method 1 — Search log part files:**

```python
import os

# Load all log part files into memory
parts = sorted([f for f in os.listdir('references/Backtest_data/V22.XX')
                if f.endswith('.txt')])
all_lines = []
for part in parts:
    with open(f'references/Backtest_data/V22.XX/{part}',
              encoding='utf-8', errors='replace') as f:
        all_lines.extend(f.readlines())

# For each loss deal: find exit ORDERINFO, then scan backward for entry TRADEINFO
def find_entry(all_lines, exit_ts, max_lookback=800):
    exit_idx = None
    for i, l in enumerate(all_lines):
        if exit_ts in l and 'ORDERINFO' in l:
            exit_idx = i; break
    if not exit_idx: return None, None
    for j in range(exit_idx, max(0, exit_idx - max_lookback), -1):
        if 'TRADEINFO' in all_lines[j] and ('|act:1' in all_lines[j] or '|act:2' in all_lines[j]):
            return j, all_lines[j].rstrip()
    return None, None

# For each loss:
for ts, loss in [('2026.01.08 14:10', -14.74), ...]:
    idx, entry = find_entry(all_lines, ts)
    print(f'{ts} ({loss:.2f}): {entry}')
```

**Method 2 — Search log_matrix.csv for gate pattern:**

The `log_matrix.csv` uses compound headers. The gate column is `headers[2]` which contains `TRADEINFO0-Gate/TRADEINFO1-Gate/...`.

```python
import pandas as pd
df = pd.read_csv('references/Backtest_data/V22.XX/log_matrix.csv', header=[0,1,2], low_memory=False)
# Gate info is in level-2 header containing 'TRADEINFO'
# Use ~timestamp for repeated rows, full timestamp on first row of each bar
```

### Step 4b — Get TF context (M15/M30/H4) at entry bar

```python
import re

def get_tf_context(all_lines, entry_idx):
    entry_date = all_lines[entry_idx][:10]
    ctx = {'M15stg':'?','M15mid':'?','M30stg':'?','M30mid':'?','H4stg':'?','H4mid':'?'}
    for j in range(max(0, entry_idx-30), min(len(all_lines), entry_idx+2)):
        line = all_lines[j]
        if entry_date not in line: continue
        for tf, key in [('[M15]','M15'), ('[M30]','M30'), ('[H4]','H4')]:
            if tf in line:
                s = re.search(rf'W_stage_{key[1:]}:\[(\d+),', line)
                m = re.search(rf'diffMid_Trend_{key[1:]}:\[(\d+),', line)
                if s: ctx[f'{key}stg'] = s.group(1)
                if m: ctx[f'{key}mid'] = m.group(1)
    return ctx
```

### Step 4c — Identify root cause pattern

**Gate → Root Cause mapping:**

| Entry Gate | Exit Gate | Root Cause Category |
|------------|-----------|---------------------|

### Step 4d — Write to root-cause-analysis.md

Location: `references/root-cause-analysis.md`

**Update the version comparison table** at the top — add new row.  
Note any period mismatch (e.g., "Jan only" vs "Jan–Apr").

**Add RC section** for each new root cause:

```markdown
### RCN — [short description]

**Status:** NEW / FIXED in vXX.XX / Persistent  
**Deals affected:** N deals, total -XXX.XX

| Time | Loss | Dir | Context | Status |
|------|------|-----|---------|--------|
| 2026.XX.XX HH:MM | -XX.XX | BUY/SELL | M30stg=523 M30mid=2 | NEW |

**Root cause:**  
[1-2 sentences explaining WHY the gate fired and what was missing]

**Fix:**
```cpp
// Show old vs new condition
```

**Update the Summary table** at the bottom.

---

## Step 5 — Code Fix in TofyTrade3.mqh


### Fix pattern — extending an existing fly/shrink condition to SQZ

```cpp
// Before (covers fly + shrink):
bool m15_fly_dn_gb=(m15_stg_gb==521)||(m15_stg_gb==522&&m15_mid_gb!=5)
                  ||(m15_stg_gb==523&&(m15_mid_gb==2||m15_mid_gb==4));

// After (also covers SQZ with opposing midtrend):
bool m15_fly_dn_gb=(m15_stg_gb==521)||(m15_stg_gb==522&&m15_mid_gb!=5)
                  ||(m15_stg_gb==523&&(m15_mid_gb==2||m15_mid_gb==4))
                  ||((m15_stg_gb>=400&&m15_stg_gb<500)&&(m15_mid_gb==2||m15_mid_gb==4));
```

**Key invariants:**
- Block BUY when M15/M30/H4 mid=2 (downtrend) or mid=4 (sideway-dn)
- Block SELL when M15/M30/H4 mid=1 (uptrend) or mid=5 (sideway-up)
- mid=3 (flat sideway) = neutral — do NOT block (let the trade through)
- For fly: always block 511/521 (full fly). For 512/522: exclude neutral mid (522 mid=5 = recovering).
- For shrink (513/523): only block when mid confirms direction (523 mid=2 or 4).
- For SQZ (400-499): only block when mid is committed opposing (not mid=3).

### Fix checklist after code edit

1. **Bump version** `#property version "22.XX"` (line 3)
2. **Update CLAUDE.md**:
   - Source files table version: `latest production code (vXX.XX)`
   - Add `## vXX.XX Changes` section before previous version section
   - Add new gate to `GATE_CLR_NOISE` color line (if using `GATE_CLR_NOISE`)
3. **Update references/fix.md**: add `## vXX.XX — [title]` section with root cause + fix snippet
4. **Update root-cause-analysis.md**: update RC status to FIXED, note version

## BB_datas Array Index Reference

```
BB_datas[1] = M15  ← entry quality filter && entry trigger
BB_datas[2] = M30  ← primary trend driver
BB_datas[3] = H1   ← chain anchor
BB_datas[4] = H4   ← macro bias (MAX_TF)
BB_datas[5] = D1   ← daily macro context (populated, not in chain scan — used in G4j-D1OPP v22.37)
BB_datas[6] = W1   ← weekly (populated, reference only)
```

Fields used in analysis:
- `BBW_stage[LA]` — current bar stage (511/512/513/521/522/523/400-499)
- `BB_diffMid_Trend[LA]` — midtrend direction (1=up 2=dn 3=flat 4=side-dn 5=side-up)

---

## TRADEINFO Log Line Format (v22.22+)

```
[TRADEINFO] Gate:[G0b-TOUCH] TradeAct:1 TF:4 touch:lower_band sl:4426.81|act:1 atrsl:0
[TRADEINFO] Gate:[G6-SHRINK] TradeAct:0 cnt:2+M5 pen:0.75| Gate:[G5] c:1 p:3 p2:3 M15s:523 M15m:2 t:flat_up q:90 sz:1.00| Gate:[G6-BUY] sl:3250.50|act:1 atrsl:0
```

- `|act:1` = BUY entry, `|act:2` = SELL entry, `|act:7` = exit all
- `M15s:NNN` = M15 BBW_stage at that bar
- `M15m:N` = M15 diffMid_Trend at that bar
- `q:NN` = M5 transition quality (≥90=1.0× size, ≥75=0.75×, ≥60=0.5×, ≥45=0.25×)
- `TF:N` in G0b-TOUCH = the timeframe index that triggered (0=M5 1=M15 2=M30 3=H1 4=H4)

---

## Typical Root Cause Decision Tree

```
New loss deal found (profit < -10, not in previous version)
```

---

## Persistent Unresolved Root Causes

| RC | Description | Status |
|----|-------------|--------|

### Replacement Entry Phenomenon

When a filter blocks an entry and M30/M15 temporarily recovers its stage+mid before continuing the original move, a replacement entry fires at a **worse price** with the same eventual stop. This is a structural risk of precision filtering.

**Detection pattern in deal comparison (Part 2):**
- WORSE deal at same close time as a V22.28 entry that was blocked/eliminated
- Close timestamp identical → same market event, different open price
- Delta = (new open − old open) × lots × (direction: −1 for BUY worse when open is higher)

**How to investigate:**
1. Find the original blocked entry: search log_matrix.csv around 2–4 hours before the WORSE deal's open time for G0b-M30OPP / G0b-M15OPP / other filter gate
2. Check if M30/M15 stage+mid changed between blocked time and actual entry time
3. If yes → replacement entry. This is not a new root cause — it is the RC14 fix working correctly but the market providing a worse second entry.

**No fix recommended** unless a 2nd+ data point confirms a systematic blocker-then-replacement pattern.

---

## Step 6 — Fix Verification Analysis

After implementing fixes, verify each fix would have blocked the confirmed loss deal using log_matrix.csv.

### Verification method

For each fixed deal, confirm the NEW gate condition is satisfied at the entry bar:

```python
import csv

log_path = 'references/Backtest_data/V22.XX/log_matrix.csv'
with open(log_path,'r',encoding='utf-8') as f:
    reader = csv.reader(f)
    headers = next(reader)
    rows = list(reader)

def resolve_time(i):
    for j in range(i,-1,-1):
        if rows[j][0] and rows[j][0]!='~': return rows[j][0]
    return ''

# For a specific NEW_ORDER_OPEN (entry), read TF stages in surrounding block:
target_entry = '2026.02.06 08:00'  # ← change per deal
for i, row in enumerate(rows):
    if row[0] == target_entry:
        for j in range(i, min(len(rows), i+20)):
            print(' | '.join(rows[j][:8]))
        break
```
### Expected improvement per fix

Document for each fix:
- Deal datetime and profit (e.g., 2026.02.06 -42.99)
- Gate condition that would have fired (e.g., "H1=403 SQZ + M30=403 SQZ → G0b-SQZLOCK")
- Whether the fix would eliminate (loss gone) or reduce (loss smaller)
- Risk of over-filtering: check how many total G0b-TOUCH entries with the new block condition exist, and verify win/loss balance

---

## Step 7 — Update Task_force.md

Minimal targeted updates — do not rewrite existing sections:

1. **Cascade gate order block** (Step 5 section): add new gate line in correct position with `← added vNEW.XX` annotation
2. **Root Cause Decision Tree**: add new RC leaf node under the correct entry gate branch
3. **GATE_CLR_NOISE / GATE_CLR_PINK registries**: add new gate name to the correct list
4. **Persistent Unresolved RC table**: add new RCN row (status=OPEN or FIXED); update prior RCs to FIXED; append vNEW.XX note paragraph
5. **Step 1 `versions` dict** in the Python script: add `'VER': ('json', 'references/Backtest_data/VER/report_tables_clean.json')`

---

## Step 8 — Update Related Reference Files

| File | What to update |
|------|----------------|
| `references/fix.md` | Add `## vNEW.XX — [gate name] (RCNN)` section before previous version; include root cause, code diff, expected result |
| `references/root-cause-analysis.md` | Mark new RCs FIXED; update version comparison table row; add vNEW.XX note to RC detail sections |
| `CLAUDE.md` | Bump source files version; add `## vNEW.XX Changes` section before previous; update GATE_CLR line |
| `SKILL.md` | Section 13: bump `scripts/TofyTrade3.mqh` version line |
| `references/decision_flow.md` | Add new gate to the gate-by-gate logic for its path (cascade / shrink / fly) |
| `references/scenarios.md` | Update if new gate changes any of the 79 H1+M30+M15 scenario outcomes |
| `references/log_matrix.md` | Add new gate row to the Gate Reference table with its TRADEINFO key attributes |
| `references/architecture_flow.html` | Add new gate diamond node + arrow in correct cascade/shrink/fly subgraph; apply matching `classDef` color |
| `references/architecture_flow.puml` | Add new gate `if` block in correct swimlane at same logical position; match `#color` to `GATE_CLR_*` palette |
| `references/version_profit.md` | Ensure Step 1 and Step 2 tables are current; regenerate with `scripts/gen_version_profit.py` if needed |

> For `architecture_flow.html` and `architecture_flow.puml`: insert the new gate node at the same logical position as it appears in the source code (cascade filter order, shrink filter chain, or fly sub-path). The node color must match the `GATE_CLR_*` definition used in `TofyTrade3.mqh`.

### Full update checklist (copy and use per version)

```
[ ] Step 1: run net profit comparison — note period, note if regression vs same-period baseline
[ ] Step 2: run deal comparison vs previous same-period version — tabulate ELIMINATED/NEW/SAME/WORSE
[ ] Step 3: rank fix list — NEW losses first, then SAME by size descending
[ ] Step 4: for each priority deal — trace entry gate + TF context + write RC section
[ ] Step 4: update version comparison table in root-cause-analysis.md
[ ] Step 5: implement fix in scripts/TofyTrade4.mqh
[ ] Step 5: bump #property version to vXX.XX
[ ] Step 5: update GATE_CLR_NOISE/GATE_CLR_PINK comment in TofyTrade3.mqh if new gate added
[ ] Step 6: verify each fix by tracing entry bar TF state in log_matrix.csv
[ ] Step 6: document expected improvement (deals eliminated + total recovery)
[ ] Step 7: update Task_force.md — cascade gate order, RC decision tree, GATE_CLR registries, versions dict
[ ] Step 8: add ## vXX.XX Changes section in CLAUDE.md + update GATE_CLR line
[ ] Step 8: add ## vXX.XX section in references/fix.md
[ ] Step 8: update RC status to FIXED in root-cause-analysis.md Summary table
[ ] Step 8: update references/decision_flow.md (new gate in its path)
[ ] Step 8: update references/log_matrix.md (new gate attributes)
[ ] Step 8: update references/architecture_flow.html (new gate node + color)
[ ] Step 8: update references/architecture_flow.puml (new gate if-block + color)
[ ] Step 9: git commit all changed files with version tag
```

---

## Step 9 — Git Commit

Commit all changed files after each version analysis cycle is complete.

### Files to stage (typical per version)

```
scripts/TofyTrade4.mqh                    ← code fix + version bump
CLAUDE.md                                 ← vXX.XX Changes section + gate color table
SKILL.md                                  ← version line bump
references/fix.md                         ← vXX.XX fix history entry
references/root-cause-analysis.md         ← version row + new RC sections
references/Task_force.md                  ← SOP updates
references/version_profit.md             ← updated net profit + deal loss tables
references/decision_flow.md              ← new gate in gate-by-gate logic
references/log_matrix.md                 ← new gate TRADEINFO attributes
references/architecture_flow.html        ← new gate node in Mermaid diagram
references/architecture_flow.puml        ← new gate node in PlantUML diagram
scripts/gen_version_profit.py            ← if updated
```

### Commit command template

```bash
git add scripts/TofyTrade3.mqh CLAUDE.md SKILL.md \
        references/fix.md references/root-cause-analysis.md \
        references/Task_force.md references/version_profit.md \
        references/decision_flow.md references/log_matrix.md \
        references/architecture_flow.html references/architecture_flow.puml \
        scripts/gen_version_profit.py

git commit -m "vXX.XX: [one-line summary of fix]"
```

### Commit message convention

```
v22.29: G0b-M30OPP extended to bearish shrink flat mid (RC14)
v22.28: G0b-SQZLOCK narrowed to both-mid==3 (RC13 over-filtering fix)
v22.27: G0b-SQZLOCK + G4f-M30OPP SQZ extension (RC11 + RC12)
v22.26: G4f-M30OPP shrink path M30 opposing filter (RC8)
v22.25: G0b-M30OPP new gate + G0b-M15OPP SQZ extension (RC6 + RC7)
v22.24: G4c-M15OPP + G0b-M15OPP extended to M15 shrink 523/513 (RC1)
```

Format: `vXX.XX: [gate name(s)] [brief description] ([RC refs])`

### After commit

After committing, note the commit hash in any relevant analysis files if needed.
The next backtest run should use the committed version as the source.

---

## Reference Files

| File | Purpose |
|------|---------|
| `references/root-cause-analysis.md` | Cumulative RC log — always update here |
| `references/log_matrix.md` | Log format reference — gate attribute definitions |
| `references/log_examples.md` | Annotated real log samples |
| `CLAUDE.md` | Gate architecture, fix history — source of truth for gate logic |
| `references/fix.md` | Chronological fix history with code diffs |
| `references/decision_flow.md` | Full gate-by-gate logic with text diagrams — update when gate logic changes |
| `references/architecture_flow.html` | Interactive Mermaid swimlane of Trade_Strategy() — update when a new gate is added |
| `references/architecture_flow.puml` | PlantUML swimlane of Trade_Strategy() — update in sync with HTML version |
| `references/version_profit.md` | Cross-version net profit + deal loss matrix — regenerate with gen_version_profit.py |
| `references/backtest_chart_analysis.md` | Visual interpretation guide for chart screenshots — BB color mapping, BBW_stage decode, gate label colors, 11 annotated reference images with full analysis, cascading sideway price target rules (Section 10) |
