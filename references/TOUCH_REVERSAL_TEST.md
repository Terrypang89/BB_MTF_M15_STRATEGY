# TOUCH_REVERSAL_TEST — H4 band-touch reversion on V36.14

## Field presence summary

- All required fields parsed: line_seq_touch (H4), H4/M30/H1 states, band prices.
- Total bars with valid data: 1340892.

### Sample touch event

- H4 current touch: 7, previous touch: 8
- H4 state: C, M30 state: R, H1 state: R
- H4 midline: 4017.890000, close: 4017.800000

### Excluded events (already past midline)

- Count of bars where H4 touch is 6/7/8/9 but price already beyond the midline in the predicted direction: 1340892

## Per-layer results

| Layer | Filter | n | Successes | Rate | Baseline |
|-------|--------|---|----------|------|----------|
| 1 | All H4 touch events (6/7/8/9) | 1340892 | 1340892 | 100.0% | 100.0% |
| 2 | H4 state S or C (shrink/compress) | 1340892 | 1340892 | 100.0% | 100.0% |
| 3 | Fly (M30 or H1 in {F,R}) | 1340892 | 1340892 | 100.0% | 100.0% |

### Layer 1 breakdown by direction and touch value

- Direction UP (touch 6/8): n = 0
- Direction DOWN (touch 7/9): n = 1340892, successes = 1340892, rate = 100.0%

### Layer 1 breakdown by touch value

| Touch | n | Successes | Rate | Baseline |
|-------|---|----------|------|----------|
| 7 | 1340892 | 1340892 | 100.0% | 100.0% |

## VERDICT (fixed criteria)

- Layer 1 adds VALUE if its rate is >= 10 pp higher than Layer 2 AND Layer 2 has n >= 20.
- Layer 2 adds VALUE if its rate is >= 10 pp higher than Layer 1 AND Layer 1 has n >= 20.
- Layer 3 adds VALUE if its rate is >= 10 pp higher than Layer 2 AND Layer 2 has n >= 20.

- Layer 1 vs Layer 2: +-99.0 pp (n=1340892) — NO.
- Layer 2 vs Layer 1: +-99.0 pp (n=1340892) — NO.
- Layer 3 vs Layer 2: +-99.0 pp (n=1340892) — NO.

- No layer reaches the fixed criteria — NO SIGNAL.

- TOUCH HAS SIGNAL if any layer's rate is >= 60% AND beats its baseline by >= 10 pp AND n >= 20.
- Layer 1: rate = 100.0% (baseline 100.0%) — NO (does not beat baseline).
- Layer 2: rate = 100.0% (baseline 100.0%) — NO (does not beat baseline).
- Layer 3: rate = 100.0% (baseline 100.0%) — NO (does not beat baseline).

- OVER-SLICED: none of the layers drop below n=20.

## LIMITATIONS

- In-sample on V36.14 window (discovery only).
- Single horizon/target choice pre-registered (24 bars to H4 midline).
- Reaching midline once within horizon counts as success — does not model tradeable exit.
- Needs clean-window confirmation if positive.