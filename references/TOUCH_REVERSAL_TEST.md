# TOUCH_REVERSAL_TEST — H4 band-touch reversion on V36.14

## Field presence summary

- All required fields parsed: line_seq_touch (H4), H4/M30/H1 states, band prices.
- Total bars with valid data: 6352.

### Sample touch event

- H4 current touch: 0, previous touch: 0
- H4 state: C, M30 state: F, H1 state: F
- H4 midline: 3322.780000, close: 3322.580000

### Excluded events (already past midline)

- Count of bars where H4 touch is 6/7/8/9 but price already beyond the midline in the predicted direction: 57

## Per-layer results

| Layer | Filter | n | Successes | Rate | Baseline |
|-------|--------|---|----------|------|----------|
| 1 | All H4 touch events (6/7/8/9) | 115 | 57 | 49.6% | 2.6% |
| 2 | H4 state S or C (shrink/compress) | 81 | 39 | 48.1% | 3.7% |
| 3 | Fly (M30 or H1 in {F,R}) | 65 | 30 | 46.2% | 4.6% |

### Layer 1 breakdown by direction and touch value

- Direction UP (touch 6/8): n = 60, successes = 34, rate = 56.7%
- Direction DOWN (touch 7/9): n = 55, successes = 23, rate = 41.8%

### Layer 1 breakdown by touch value

| Touch | n | Successes | Rate | Baseline |
|-------|---|----------|------|----------|
| 6 | 9 | 7 | 77.8% | 22.2% |
| 7 | 49 | 20 | 40.8% | 0.0% |
| 8 | 51 | 27 | 52.9% | 2.0% |
| 9 | 6 | 3 | 50.0% | 0.0% |

## VERDICT (fixed criteria)

- Layer 1 adds VALUE if its rate is >= 10 pp higher than Layer 2 AND Layer 2 has n >= 20.
- Layer 2 adds VALUE if its rate is >= 10 pp higher than Layer 1 AND Layer 1 has n >= 20.
- Layer 3 adds VALUE if its rate is >= 10 pp higher than Layer 2 AND Layer 2 has n >= 20.

- Layer 1 vs Layer 2: +-47.7 pp (n=81) — NO.
- Layer 2 vs Layer 1: +-49.1 pp (n=115) — NO.
- Layer 3 vs Layer 2: +-47.7 pp (n=81) — NO.

- No layer reaches the fixed criteria — NO SIGNAL.

- TOUCH HAS SIGNAL if any layer's rate is >= 60% AND beats its baseline by >= 10 pp AND n >= 20.
- Layer 1: rate = 49.6% (baseline 2.6%) — NO (does not beat baseline).
- Layer 2: rate = 48.1% (baseline 3.7%) — NO (does not beat baseline).
- Layer 3: rate = 46.2% (baseline 4.6%) — NO (does not beat baseline).

- OVER-SLICED: none of the layers drop below n=20.

## LIMITATIONS

- In-sample on V36.14 window (discovery only).
- Single horizon/target choice pre-registered (24 bars to H4 midline).
- Reaching midline once within horizon counts as success — does not model tradeable exit.
- Needs clean-window confirmation if positive.