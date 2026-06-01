# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Repo Is

Development workspace for **Tofu EA** — a XAUUSD Expert Advisor for MetaTrader 5 using a multi-timeframe Bollinger Band strategy. The EA is implemented in MQL5 (`scripts/TofyTrade4.mqh`). This repo holds the strategy source, backtest data, analysis scripts, and reference documentation — not the full MT5 terminal project.

Current production version: **v22.49** (in `#property version` at top of `TofyTrade4.mqh`).

## Key Commands

```bash
# Regenerate version_profit.md from all V30.XX backtest JSON folders
python scripts/gen_version_profit.py

# Run from repo root — output written to references/version_profit.md
```

There is no build step here. Compilation happens inside MetaTrader 5. The backtest is run via MetaTrader Strategy Tester using `scripts/tester.ini` (Expert: `Tofu_EA_Simple_V4.ex5`, Symbol: XAUUSD, Period: M5, 2026-01-01 to 2026-04-30).

## Architecture Overview

### Timeframe Stack

```
BB_datas[6] = W1   — ultra-macro context (reference only)
BB_datas[5] = D1   — daily macro context
BB_datas[4] = H4   — macro bias filter (MAX_TF)
BB_datas[3] = H1   — chain anchor + G0 sideway confirm
BB_datas[2] = M30  — primary trend driver + confirmation for M15 trigger quality
BB_datas[1] = M15  — entry trigger (BBdiffMidTrend transition) V30.02+
BB_datas[0] = M5   — data only; no longer the entry trigger (too noisy)
```

The **M15 transition** is the entry signal (V30.02+). The EA runs on M5 chart period but only fires entries on M15 bar closes. M30 stage+midtrend must agree with direction before entry is allowed. Each gate in `Trade_Strategy()` is evaluated in cascade order — any failing gate stops the flow for that bar.

### Core Data Types per TF

- `BBW_stage[LA]` — regime code (511/512/513/521/522/523/400-499/200/300/0)
- `BB_diffMid_Trend[LA]` — midtrend direction (1=up 2=dn 3=flat 4=side-dn 5=side-up)

### BBW_Stage Codes

| Code | Name | Bias |
|------|------|------|
| 511 | FLY++ mid up | BUY |
| 512 | FLY+- parallel up | BUY |
| 521 | FLY++ mid dn | SELL |
| 522 | FLY-+ parallel dn | SELL |
| 513 | FLY-- bullish shrink | WATCH |
| 523 | FLY-- bearish shrink | WATCH |
| 400–499 | SQZ (squeeze) | WAIT |

### Entry Gate Rule (key invariant)

- Block BUY when M15/M30/H4 mid=2 (dn) or mid=4 (side-dn)
- Block SELL when M15/M30/H4 mid=1 (up) or mid=5 (side-up)
- mid=3 (flat) = neutral — do NOT block

### Position Sizing

```mql5
// TF agreement count → lot multiplier
≥3 TFs agree → 1.0× baseLot
2 TFs        → 0.75×
1 TF         → 0.5×
```

M5 transition quality score also scales size: ≥90→1.0×, ≥75→0.75×, ≥60→0.5×, ≥45→0.25×.

## Source Files

| File | Purpose |
|------|---------|
| `scripts/TofyTrade4.mqh` | Main EA strategy library — all gate logic, position sizing, ATRSL stop placement |
| `scripts/tester.ini` | MT5 Strategy Tester config for V4 EA |
| `scripts/gen_version_profit.py` | Generates `references/version_profit.md` from all `V30.XX` backtest folders |

## Reference Files

| File | Purpose |
|------|---------|
| `SKILL.md` | Full authoritative strategy reference — all gate codes, decision tables, log parsing recipes |
| `references/Task_force.md` | **9-step backtest analysis SOP** — start here for every new backtest version |
| `references/fix.md` | Chronological fix history with code diffs |
| `references/decision_flow.md` | Gate-by-gate logic walkthrough with text diagrams |
| `references/log_matrix.md` | Log format spec — TRADEINFO line structure, gate attribute keys |
| `references/log_examples.md` | Annotated real log samples |
| `references/backtest_chart_analysis.md` | Visual guide for chart screenshots — BBW_stage decode, gate label colors |

## Backtest Data Layout

Each backtest version lives in `references/Backtest_data/V30.XX/`:

```
report_tables_clean.json   ← net profit + deal table (Steps 1 & 2)
log_matrix.csv             ← per-bar TF state (Steps 4 & 6 gate tracing)
YYYYMMDD_clean.log         ← full TRADEINFO log (Step 4 entry search)
filtered_log_json.json     ← structured log (entry search)
metadata.json              ← test period + EA version
```

Multi-period variants: `V30.XX_M15/` and `V30.XX_M30/` (when present) — used for M5-ONLY loss isolation.

## Backtest Analysis Workflow (9 steps)

When new backtest data arrives in `references/Backtest_data/V30.XX/`, follow `references/Task_force.md` exactly:

1. Net profit comparison vs all same-period versions → update `references/version_profit.md`
2. Deal loss comparison (profit < −10) vs previous version
3. Rank fix list: NEW losses first, then SAME losses by absolute size
4. Root cause per priority deal — trace entry gate + TF context in log_matrix.csv
5. Code fix in `scripts/TofyTrade4.mqh` + bump `#property version`
6. Verify fix eliminates/reduces the confirmed loss deal
7. Update `Task_force.md` (cascade gate order, RC tree, versions dict)
8. Update `fix.md`, `decision_flow.md`, `log_matrix.md`, CLAUDE.md
9. Git commit with message format: `vXX.XX: [gate name] [description] (RCN)`

## Version Naming

- EA code version: `22.XX` in `#property version` and `ORDERS_COMMENT` in tester.ini
- Backtest folder: `V30.XX` (backtest data versioning is independent of EA code version)
- Same test period (Jan–Apr 2026) required for meaningful net profit comparison across versions

## Commit Convention

```
v22.29: G0b-M30OPP extended to bearish shrink flat mid (RC14)
v22.28: G0b-SQZLOCK narrowed to both-mid==3 (RC13 over-filtering fix)
```

Format: `vXX.XX: [gate name(s)] [brief description] ([RC refs])`
