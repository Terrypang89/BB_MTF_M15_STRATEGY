# REAL TRADE P&L by Fast-Scenario Context (Level 1)

**Source:** Real backtest trades from `20260712_clean.log`

**Date range:** 2022.12.29 — 2025.01.02

## Summary

1. **Total [TRADE] entries found:** 80
   - Matched to close: **78**
   - Unmatched: **2** (no matching OPEN or CLOSE)

2. **Overall statistics:**
   - Win-rate: 30.8% (24 wins / 78 total)
   - Total profit: +69.37
   - PF (gross profit / gross loss): +671.16 / +601.79 = 1.12

## 1. Grouped by M15 State

| M15 | Count | Win-Rate | Total Profit | PF |
|-----|-------|----------|---------------|-----|
| F | 39 | 25.6% | -115.12 | 0.63 |
| R | 39 | 35.9% | +184.49 | 1.64 |

## 2. Grouped by M30 State

| M30 | Count | Win-Rate | Total Profit | PF |
|-----|-------|----------|---------------|-----|
| F | 39 | 25.6% | -115.12 | 0.63 |
| R | 39 | 35.9% | +184.49 | 1.64 |

## 3. Grouped by Direction

| Dir | Count | Win-Rate | Total Profit | PF |
|-----|-------|----------|---------------|-----|
| UP | 39 | 25.6% | -115.12 | 0.63 |
| DOWN | 39 | 35.9% | +184.49 | 1.64 |

## 4. Grouped by (M15 × Direction)

| M15 | Dir | Count | Win-Rate | Total Profit | PF |
|-----|------|-------|----------|---------------|-----|
| F | UP | 39 | 25.6% | -115.12 | 0.63 |
| R | DOWN | 39 | 35.9% | +184.49 | 1.64 |

## 5. Grouped by (M30 × Direction)

| M30 | Dir | Count | Win-Rate | Total Profit | PF |
|-----|------|-------|----------|---------------|-----|
| F | UP | 39 | 25.6% | -115.12 | 0.63 |
| R | DOWN | 39 | 35.9% | +184.49 | 1.64 |

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
