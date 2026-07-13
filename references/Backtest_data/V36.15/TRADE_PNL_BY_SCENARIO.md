# REAL TRADE P&L by Fast-Scenario Context (Level 1)

**Source:** Real backtest trades from `20260712_clean.log`

**Date range:** 2022.12.29 — 2025.01.02

## Summary

1. **Total [TRADE] entries found:** 41
   - Matched to close: **39**
   - Unmatched: **2** (no matching OPEN or CLOSE)

2. **Overall statistics:**
   - Win-rate: 25.6% (39 wins / 39 total)
   - Total profit: -115.12
   - PF (gross profit / gross loss): -135.12 / +125.12 = -1.08

---

### LEVEL 2 Hook (not implemented yet)

```python
def compute_subscenario(bar_fields):
    """
    TODO Level 2: compute S1/S2/B2/P2 from raw stage/diffBBW/diffMid fields per the
    Part 3 sub-state rules, once validated. Not implemented - Level 1 uses logged m15/m30
    state only.
    """
    pass


# Usage (after validation of the sub-scenario rules):
# for t in trades:
#     if t['m15_state'] == 'F':
#         ss = compute_subscenario(t)  # would return S1/S2/etc.
```
