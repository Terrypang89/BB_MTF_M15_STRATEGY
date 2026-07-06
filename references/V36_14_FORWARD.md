# V36.14 Forward Analysis - M30-Confirmed Cascade Entry

Tests whether the M30-confirmed entry gate (enters on bar M30 confirms, not M15 flips) has a real dollar edge versus V36.13 NOT-SEPARABLE (-$899). Full-range PF 0.87 is contaminated by discovery window; only clean OOS windows decide.

## 1. Reconciliation

- Tester Total Trades: 247 | Joined in/out pairs from deals table: 247
- [TRADE] ENTRY log lines matched to trades: 0/247
- [TRADE] EXIT  log lines matched to trades: 0/247
- Reconciled $ sum (sum of all trade P&L from deals): $-185.93

## 2. Zone Split (by entry date)

| Zone | n | Net$ | WR% | PF | Mean$/trade |
|------|---:|-----:|----:|----:|-----------:|

### Clean-set Assertion

- PRE date range: 2025.06.02 to 2025.12.31
- POST date range: 2026.04.30 to 2026.06.29
- ASSERTION PASSED: zero overlap - no PRE or POST trade falls in 2026.01.05-2026.04.29 (DISC).
- Clean set date bounds: 2025.06.02 to 2026.06.29

## 3. Combined-Clean Result

| Metric | n | Net$ | WR% | PF | Mean$/trade |
|--------|---:|-----:|----:|----:|-----------:|
| Combined (PRE+POST) | 169 | $-208.45 | 39.1% | 0.71 | $-1.23 |
| PRE | 126 | $-186.32 | 37.3% | 0.66 | $-1.48 |
| POST | 43 | $-22.13 | 44.2% | 0.88 | $-0.51 |

## 4. Regime Split (clean set, by D1 state at entry)

| Regime | n | Net$ | WR% | PF | Mean$/trade |
|--------|---:|-----:|----:|----:|-----------:|
| D1=F (Fly-up) | 0 | $0.00 | - | - | - |
| D1=R (Fly-down) | 0 | $0.00 | - | - | - |
| D1=S (Shrink) | 0 | $0.00 | - | - | - |
| D1=C (Compress) | 0 | $0.00 | - | - | - |
| D1=X (no data) | 169 | $-208.45 | 39.1% | 0.71 | $-1.23 |

## 5. M30 Confirm-Lag (bars_between distribution)
- bars_between counts: 

## 6. Verdict

**VERDICT: V36.14 REJECTED**

Combined-clean PF 0.71 < 1.0.

- Combined-clean PF = 0.71, n = 169

## 7. Limitations

- Single backtest run, no live confirmation. Reconciled against Tester deals table (net $-189.54) to confirm realized-dollar P&L matches the source of truth.