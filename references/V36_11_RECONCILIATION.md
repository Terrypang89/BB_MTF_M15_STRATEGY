# V36.11 Reconciliation Report

> Log: `references/Backtest_data/V36.11/20260703_clean.log`
> Deals: `references/Backtest_data/V36.11/report_tables_clean.json`
> Script: `scripts/reconcile_v36_11.py`
> Generated: 2026-07-03

---

## THE 2X DISCREPANCY — Named and Resolved

**34 "entries" = 17 [TRADE] + 17 [TRADEINFO]. Double logging, not phantom fills.**

Each event in V36.11 produces two log lines:

| Line | Source | Example |
|------|--------|---------|
| `[TRADE]` | V36.11 `LogTradeEntry()` | `evt:ENTRY dir:UP dt:2026.01.05 08:15:00 entry:4418.36 sl:4394.90 sldist:23.46 tp:4446.08 tpdist:27.72 rr:1.18` |
| `[TRADEINFO]` | EA's own `SigEvt()` | `evt:ENTRY dir:UP entry:4418.36 sl:4394.90 tp:4446.08 rr:1.18` |

Counting `grep "evt:ENTRY"` yields 34 lines. Counting `grep "\[TRADE\]" "evt:ENTRY"` yields 17.
The 17 [TRADE] lines match 17 in-deals 1:1. No phantom entries exist.

**Mechanism: DOUBLE LOGGING.** The EA's own SIG:SIG pipeline and the V36.11 [TRADE]
pipeline both fire on the same event. This is cosmetic — it inflates line counts but
does not affect trade logic.

---

## STEP 1 — Join Results

| | Log [TRADE] | Deals | Matched | Unmatched |
|--|------------|-------|---------|-----------|
| **Entries** | 17 | 17 in-deals | **17** | 0 phantoms, 0 unmatched deals |
| **Exits** | 17 | 17 out-deals | **16** | 1 unmatched exit line, 1 unmatched out-deal |

**in-deal count = 17** (matches Tester "Total Trades: 17").

### Unmatched Out-Deal

Deal 35: `2026.04.29 23:59:58` buy @4543.88, profit +$45.18, comment = "end of test".
This is the Tester's forced close of the last open position at test end.

### Unmatched Exit Line

`M15_REVERT at 2026.01.14 01:00:00` exit=4588.92, bars_held=6.
No out-deal within 600s. The EA did NOT close the position when the strategy
logged this EXIT. The position (deal 34, sell @4589.06) was held until
end of test (deal 35, +$45.18 + $40.13 swap).

---

## STEP 2 — The Failed Exit (the real discrepancy)

The last position's lifecycle:

| Time | Event | Detail |
|------|-------|--------|
| 2026.01.13 22:30 | ENTRY (log) + deal 34 (sell @4589.06) | DOWN trigger, m30bbloc=3 |
| 2026.01.14 01:00 | EXIT (log) | M15_REVERT, bars_held=6, exit=4588.92 |
| **No deal** | — | EA did not execute Trade_act=7 |
| 2026.04.29 23:59 | deal 35 (buy @4543.88) | End of test, profit +$45.18 |

**The strategy said EXIT at 01:00. The EA did nothing.**
The position survived 3.5 months on swap ($40.13 income) and closed at +$45.18 —
a lucky save that masks the strategy's actual performance.

**Root cause hypothesis:** The EA's order execution layer (Tofu_EA_Simple_V6) may
not be calling the V36.11 Trade_Strategy on the correct bar, or the Trade_act=7
signal was set but the EA's order logic failed to send OrderClose. This is a
**code defect** (KNOB #0) — the exit sync between V36.11 and the EA is broken.

---

## STEP 2c — Gate-Eval Anomaly

**Finding: NO per-bar re-evaluation. Each F/R flip produces exactly 1 event.**

- 422 flip windows total
- 349 with 1 event (each flip = 1 evaluation)
- 73 with 2+ events (rapid successive flips, e.g., DOWN flip then UP flip within 12 bars)

The multi-event windows show independent flips, not re-evaluation of the same trigger:

```
Window 5: 2026.01.12 16:30-17:15
  ENTRY DOWN @16:30 (m30bbloc=5) — flip to R
  SKIP UP   @17:15 (m30bbloc=10) — new flip to F, skipped (position open)
```

The 12-row validity window does NOT re-gate every bar. The trigger fires once per
M15 F/R flip. No per-bar re-evaluation pattern detected.

---

## STEP 3 — Honest Expectancy (16 regular trades, excl end-of-test)

### A. Overall

| Metric | Value |
|--------|-------|
| n | 16 |
| Wins | 5 |
| Win rate | 31.2% |
| Mean $ | -$2.72 |
| Median $ | -$3.10 |
| Total net | **-$43.53** |
| Gross profit | $56.44 |
| Gross loss | $99.97 |
| PF | 0.56 |
| Mean R | -0.11 |
| Median R | -0.09 |

**Tester net (incl deal 35): $41.61.** Delta: -$85.14 (deal 35 contributes +$45.18
profit + $40.13 swap). Without deal 35, the run is -$43.53.

**Recovery Factor 0.04** (from Tester) is unreliable: it includes deal 35's $45.18
and $40.13 swap against gross loss of $99.97. Without deal 35, RF = 56.44 / 99.97
= 0.56 — still bad, but the Tester's 0.04 is inflated by the end-of-test artifact.

### B. Ex-Largest-Winner

| Metric | Value |
|--------|-------|
| Largest winner | Deal 28: +$23.39 (TP_HIT) |
| Ex-largest net | **-$66.92** |
| Ex-largest n | 15, wins = 4 |

**WITHOUT the largest winner, the run is NEGATIVE (-$66.92).**
The strategy's performance is entirely dependent on one TP_HIT trade.

### C. By Exit Reason

| Reason | n | Wins | Total $ | Mean $ | Mean R |
|--------|---|------|---------|--------|--------|
| M15_REVERT | 11 | 2 | -$57.05 | -$5.19 | -0.06 |
| SL_HIT | 2 | 0 | -$38.98 | -$19.49 | -1.81 |
| TIMEOUT | 1 | 1 | +$8.71 | +$8.71 | +0.48 |
| TP_HIT | 2 | 2 | +$43.79 | +$21.89 | +1.01 |

**M15_REVERT net: -$57.05 (COST).** 11 of 16 trades (68.75%) exited via M15_REVERT,
and 9 of those 11 were losers.

**Counterfactual note:** Whether TP would have hit after M15_REVERT is UNKNOWABLE
from this data — reporting realized only.

### D. By rr Bucket

| Bucket | n | Net $ |
|--------|---|-------|
| rr < 1.0 | 12 | **-$48.78** |
| rr >= 1.0 | 4 | +$5.25 |

12 of 16 trades (75%) had rr < 1.0. The rr < 1.0 bucket accounts for 95% of losses
(-$48.78 vs -$43.53 total). The rr >= 1.0 bucket is marginally positive (+$5.25).

### $/Point Sanity Check

Confirmed: $1 per $1 per 0.01 lot XAUUSD. Example:
- Deal 2: BUY at 4418.47, out at 4418.10, move = -$0.37, profit = -$0.37, $/point = 1.00
- Deal 4: SELL at 4415.71, out at 4419.83, move = -$4.12, profit = -$4.12, $/point = 1.00

---

## STEP 4 — Knob Ranking

### KNOB #0: FIX EXIT/SYNC LOGIC — MANDATORY (triggered)

1 log EXIT (M15_REVERT at 2026.01.14 01:00) was not executed by the EA.
Position held 3.5 months until end of test. V36.11 expectancy numbers are
**PROVISIONAL** until V36.12 re-backtest with the fix.

**No parameter change is justified on this dataset.** The failed exit means
one trade (deal 34-35) was closed by end-of-test, not by strategy logic.
Its +$45.18 profit is an artifact, not a signal. Removing it flips the
entire run from +$41.61 to -$43.53.

### KNOB #1: M15_REVERT Rule — candidate for change

M15_REVERT: net = -$57.05, median loss = $5.17 > median win = $2.26.
11 of 16 trades (68.75%) exit via M15_REVERT; 9 of 11 are losers (81.8%
lose rate). The rule closes too early — price reverts to the trigger state
but the trade is already underwater.

**Hypothesis:** Delaying the M15_REVERT exit (e.g., require 2 consecutive
bars of non-trigger state) might let more trades reach TP. Unmeasured.

### KNOB #2: min-rr Gate — candidate for change

rr < 1.0: net = -$48.78 (12 trades). rr >= 1.0: net = +$5.25 (4 trades).
75% of trades have rr < 1.0 and account for 111% of losses.

**Hypothesis:** A min-rr gate (e.g., rr >= 1.0 required) would filter 12
trades (saving -$48.78) at the cost of 4 trades (losing +$5.25).
Net effect: +$43.53 - $48.78 = -$5.25. **Still negative** — the gate
saves the losers but the remaining 4 rr>=1 trades barely break even.
The issue is not just the rr distribution; the underlying edge is absent.

### KNOB #3: Stop Source — candidate for review

SL_HIT: 2 of 16 trades, both losers, rr at SL = [0.98, 0.38].
The r=0.38 trade (sldist=28.55, tpdist=12.46) shows the stop is too
wide relative to TP — the M15-band SL gives too much room for price
to hit SL before TP.

**Hypothesis:** Narrower stop (e.g., fixed ATR offset instead of
opposite M15 band) might improve rr distribution. Unmeasured.

### CAVEAT

**17 trades ranks hypotheses; it validates nothing.** Every "candidate"
here is a question mark on 16 data points. The KNOB #0 fix is the
only mandatory item — the rest are directional signals that need
their own backtest.

---

## Limitations

1. **16-trade sample (17 with end-of-test artifact).** Standard error on
   win-rate 31.2% is ~3.7 percentage points. Every conclusion is a
   hypothesis, not a finding.

2. **Counterfactual unknowable.** Whether TP would have hit after
   M15_REVERT exits is unknowable from this data. The realized
   -$57.05 M15_REVERT net may overstate the true cost of the rule.

3. **$/point assumption.** Confirmed at $1 per $1 per 0.01 lot XAUUSD
   via sanity check (all 16 trades show $/point = 1.00).

4. **Recovery Factor unreliable.** Tester reports RF = 0.04, inflated by
   deal 35's end-of-test profit. True RF (excl deal 35) = 56.44 / 99.97
   = 0.56 — still bad but not as bad as the Tester implies.

5. **Failed exit (deal 34-35).** The EA did not execute the EXIT signal
   at 2026.01.14 01:00. This means V36.11's actual exit logic may be
   correct, but the EA's order execution layer dropped the signal.
   All expectancy numbers are PROVISIONAL until this is fixed and
   re-backtested.

6. **Swap on deal 34-35.** The $40.13 swap income is a function of the
   failed exit, not strategy design. It should not be attributed to
   the strategy.
