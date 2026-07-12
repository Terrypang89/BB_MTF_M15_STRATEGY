# TOUCH_REVERSAL_TEST — H4 band-touch reversion on V36.14

## Field presence summary

- All required fields parsed: line_seq_touch (H4), H4/M30/H1 states, band prices.
- Total bars with valid data: 23247.

### Sample touch event

- H4 current touch: 7, previous touch: 8
- H4 state: None, M30 state: None, H1 state: None
- H4 midline: 4015.450000, close: 4015.640000

### Excluded events (already past midline)

- Count of bars where H4 touch is 6/7/8/9 but price already beyond the midline in the predicted direction: 0

## Per-layer results

| Layer | Filter | n | Successes | Rate | Baseline |
|-------|--------|---|----------|------|----------|
| 1 | All H4 touch events (6/7/8/9) | 23247 | 0 | 0.0% | 0.0% |
| 2 | H4 state S or C (shrink/compress) | 0 | 0 | 0.0% | 0.0% |
| 3 | Fly (M30 or H1 in {F,R}) | 0 | 0 | 0.0% | 0.0% |

### Layer 1 breakdown by direction and touch value

- Direction UP (touch 6/8): n = 0
- Direction DOWN (touch 7/9): n = 23247, successes = 0, rate = 0.0%

### Layer 1 breakdown by touch value

| Touch | n | Successes | Rate | Baseline |
|-------|---|----------|------|----------|
| 7 | 23247 | 0 | 0.0% | 0.0% |

## VERDICT (fixed criteria)

- Layer 1 adds VALUE if its rate is >= 10 pp higher than Layer 2 AND Layer 2 has n >= 20.
- Layer 2 adds VALUE if its rate is >= 10 pp higher than Layer 1 AND Layer 1 has n >= 20.
- Layer 3 adds VALUE if its rate is >= 10 pp higher than Layer 2 AND Layer 2 has n >= 20.

- Layer 1 vs Layer 2: +0.0 pp (n=0) — NO.
- Layer 2 vs Layer 1: +0.0 pp (n=23247) — NO.
- Layer 3 vs Layer 2: +0.0 pp (n=0) — NO.

- No layer reaches the fixed criteria — NO SIGNAL.

- TOUCH HAS SIGNAL if any layer's rate is >= 60% AND beats its baseline by >= 10 pp AND n >= 20.
- Layer 1: rate = 0.0% (baseline 0.0%) — NO (does not beat baseline).
- Layer 2: rate = 0.0% (baseline 0.0%) — NO (does not beat baseline).
- Layer 3: rate = 0.0% (baseline 0.0%) — NO (does not beat baseline).

- OVER-SLICED: Layer 2 drops to n=0 < 20 — this condition over-slices the data; cannot conclude.

## LIMITATIONS

- In-sample on V36.14 window (discovery only).
- Single horizon/target choice pre-registered (24 bars to H4 midline).
- Reaching midline once within horizon counts as success — does not model tradeable exit.
- Needs clean-window confirmation if positive.