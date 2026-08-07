# Ceiling and floor — what perfect sideway detection is worth

Input: `references/Backtest_data/V36.15/20260712_clean.log`   bars: 1830   month filter: 2026.02

Ranges are consecutive `state >= 2` bars, gaps of <= 1 bar(s) bridged, ranges shorter than 2 bars dropped.


### P  PERFECT - the labels themselves

`l1=1  l2=0  bm=2`   -   0 ranges, 0 bars flagged (0.0%)

**P&L (gross):** 114 trades, 26.3% win rate, **-636.37**


### N  NO sideway exit at all

`l1=1  l2=0  bm=2`   -   0 ranges, 0 bars flagged (0.0%)

**P&L (gross):** 114 trades, 26.3% win rate, **-636.37**

