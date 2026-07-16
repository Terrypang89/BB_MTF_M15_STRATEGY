# Script / Command (`python scripts/label_base_rate.py`) / Input log / Generated (UTC)
# X=10.0, N=8 M15 bars (120 min), first-touch barrier, labels from [M15], outcome from close_M5, NO trades read.

## Results

**Parsed data:**
- M15 lines: 7610 (date range: 2026-01-02 01:00:02 to 2026-04-29 23:45:02)
- M5 lines: 22821

## Verification: tag filter

The script only parses lines containing `[M15]` or `[M5]` tags. All other tags (`[TRADE]`, `[TRADEINFO]`, `[ORDERINFO]`, `[DUALTF]`, `[ATRSL1buf]`, `[NEW_ORDER_*]`, `[BBTFImpact]`) are ignored.

**Parsed counts:**
- M15: 7610 lines
- M5: 22821 lines

## Label distribution

| Label | n | WIN | LOSS | NEUTRAL | Hit rate |
|-------|---|-----|------|---------|----------|
| UNLABELED | 26 | 0 | 0 | 26 | — |
| FLY_UP | 1934 | 850 | 833 | 251 | 0.5051 (850/1683) |
| SHRINK | 1254 | 0 | 0 | 1254 | n/a (direction-blind) |
| SQZ | 376 | 0 | 0 | 376 | n/a (direction-blind) |
| SIDEWAYS | 2279 | 475 | 1804 | 0 | 0.2084 (475/2279) |
| FLY_DOWN | 1741 | 746 | 829 | 166 | 0.4737 (746/1575) |

## Hit rate per label (WIN/(WIN+LOSS), excluding NEUTRAL)

| Label | WIN / (WIN+LOSS) |
|-------|------------------|
| FLY_DOWN | **47.37%** (746/1575) |
| FLY_UP | **50.51%** (850/1683) |
| SIDEWAYS | **20.84%** (475/2279) |
| SHRINK | n/a (direction-blind) |
| SQZ | n/a (direction-blind) |
| UNLABELED | n/a (no directional outcomes) |

## Direction-blind labels (SHRINK, SQZ)

| Label | UP | DOWN | NEUTRAL |
|-------|----|------|---------|
| SHRINK | 1254 | 1254 | 1254 |
| SQZ | 376 | 376 | 376 |

## AMBIGUOUS

0 bars were ambiguous (both barriers touched in the same bar).

## Worked examples (5 bars)
  [2026-01-02] label=UNLABELED, outcome=NEUTRAL
  [2026-01-02] label=FLY_UP, outcome=NEUTRAL
  [2026-01-02] label=FLY_UP, outcome=WIN
  [2026-01-02] label=SHRINK, outcome=NEUTRAL
  [2026-01-02] label=SQZ, outcome=NEUTRAL
