# Script / Command (`python scripts/label_base_rate.py`) / Input log / Generated (UTC)
# X=10.0, N=8 M15 bars (120 min), first-touch barrier, labels from [M15], outcome from close_M5, NO trades read.

## Verification: tag filter
The script only parses lines containing `[M15]` or `[M5]` tags. All other tags (`[TRADE]`, `[TRADEINFO]`, `[ORDERINFO]`, `[DUALTF]`, `[ATRSL1buf]`, `[NEW_ORDER_*]`, `[BBTFImpact]`) are ignored.

## Results

**Parsed data:**
- M15 lines: 7610 (date range: 2026-01-02 01:00:02 to 2026-04-29 23:45:02)
- M5 lines: 22821

## Label distribution
M5 lines parsed: 22821

Label distribution:
  SIDEWAYS: n=7, WIN=0, LOSS=7, NEUTRAL=0
  FLY_UP: n=2485, WIN=2313, LOSS=172, NEUTRAL=0
  SHRINK: n=1801, WIN=0, LOSS=0, NEUTRAL=1801
  SQZ: n=1113, WIN=0, LOSS=0, NEUTRAL=1113
  FLY_DOWN: n=2204, WIN=2178, LOSS=26, NEUTRAL=0

Hit rate per label (WIN/(WIN+LOSS), excluding NEUTRAL):
  FLY_DOWN: 0.9882 (2178/2204)
  FLY_UP: 0.9308 (2313/2485)
  SHRINK: n/a (no directional outcomes)
  SIDEWAYS: 0.0000 (0/7)
  SQZ: n/a (no directional outcomes)
  SHRINK: UP=1801, DOWN=1801, NEUTRAL=1801
  SQZ: UP=1113, DOWN=1113, NEUTRAL=1113

AMBIGUOUS: 0

Worked examples (5 bars):
  [2026-01-02] label=SIDEWAYS, outcome=LOSS
  [2026-01-02] label=FLY_UP, outcome=WIN
  [2026-01-02] label=SHRINK, outcome=NEUTRAL
  [2026-01-02] label=SQZ, outcome=NEUTRAL
  [2026-01-02] label=FLY_DOWN, outcome=WIN
