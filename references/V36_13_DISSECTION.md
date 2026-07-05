# V36.13 Dissection — Where the -$899 concentrates

## Reconciliation

- 214 in-deals matched to 214 out-deals. All 214 trades joined.
- 217 [TRADE] ENTRY lines in log; 0 unmatched (in-deal with no ENTRY log), 3 rejected (ENTRY log with no in-deal).
- 214 [TRADE] EXIT lines in log; 0 extra (exit-retry duplicates). Joined by sequential index (one position at a time).
- Per-trade profit sum: **-896.62**
- Report Total Net Profit: **-899.06**
- Delta: **2.44** (explained by swap: **-2.44**)

## Splits

### A. By Exit Reason

| Group | n | Total $ | Mean $ | Win-Rate | PF |
|-------|---|---------|--------|----------|-----|
| TP_HIT | 45 | +1138.70 | +25.30 | 100.0% | inf |
| M15_REVERT | 152 | -1801.49 | -11.85 | 16.4% | 0.1 |
| TIMEOUT | 8 | +48.55 | +6.07 | 87.5% | 35.43 |
| SL_HIT | 9 | -282.38 | -31.38 | 0.0% | 0.0 |

**M15_REVERT:** n=152, net **-1801.49**, PF=0.1

### B. By Entry m30bbloc Zone

| Group | n | Total $ | Mean $ | Win-Rate | PF |
|-------|---|---------|--------|----------|-----|
| NEAR/MID | 214 | -896.62 | -4.19 | 36.0% | 0.61 |

### C. By rr Bucket at Entry

| Group | n | Total $ | Mean $ | Win-Rate | PF |
|-------|---|---------|--------|----------|-----|
| rr<1.0 | 134 | -593.15 | -4.43 | 37.3% | 0.58 |
| 1.0-1.5 | 37 | -240.04 | -6.49 | 32.4% | 0.57 |
| 1.5-2.0 | 17 | +78.56 | +4.62 | 47.1% | 1.74 |
| >=2.0 | 26 | -141.99 | -5.46 | 26.9% | 0.36 |

### D. By Direction

| Group | n | Total $ | Mean $ | Win-Rate | PF |
|-------|---|---------|--------|----------|-----|
| BUY | 113 | -476.99 | -4.22 | 36.3% | 0.61 |
| SELL | 101 | -419.63 | -4.15 | 35.6% | 0.61 |

### E. By HTF Context (H4 vs Trigger Dir)

| Group | n | Total $ | Mean $ | Win-Rate | PF |
|-------|---|---------|--------|----------|-----|
| AGREE | 92 | -405.98 | -4.41 | 37.0% | 0.6 |
| DISAGREE | 68 | -233.46 | -3.43 | 32.4% | 0.67 |
| NEUTRAL | 54 | -257.18 | -4.76 | 38.9% | 0.55 |

### F. By Session/Hour Bucket

| Group | n | Total $ | Mean $ | Win-Rate | PF |
|-------|---|---------|--------|----------|-----|
| 00-04 | 29 | -55.43 | -1.91 | 44.8% | 0.8 |
| 04-08 | 34 | +6.68 | +0.20 | 44.1% | 1.03 |
| 08-12 | 46 | -101.49 | -2.21 | 32.6% | 0.68 |
| 12-16 | 34 | -342.14 | -10.06 | 26.5% | 0.24 |
| 16-20 | 34 | -464.13 | -13.65 | 26.5% | 0.35 |
| 20-00 | 37 | +59.89 | +1.62 | 43.2% | 1.21 |

## Verdict

**SALVAGEABLE-BY-GATE**

Split F subset '20-00' has PF 1.21 with n=37 (>=30). This subset is a profitable core big enough to trade.

### Subsets with PF >= 1.0 but n < 30 (not promoted)

- Split C '1.5-2.0': n=17, PF=1.74, total=+78.56 — too small to trade

## Limitations

- **Counterfactual unknowable:** The EXIT-DRIVEN counterfactual (removing a bucket) is realized-only — we cannot know whether those lost trades would have been wins had they exited differently.
- **Post-hoc subsets are hypotheses, not validation:** Any promising subset identified here needs a FORWARD test on a fresh data window before trusting it. This analysis is descriptive, not prescriptive.
- **No new design recommendations:** The three fixed verdict categories (salvageable-by-gate / exit-driven / fundamentally-negative) are the only conclusions drawn. No gate, exit, or parameter tuning is proposed.
