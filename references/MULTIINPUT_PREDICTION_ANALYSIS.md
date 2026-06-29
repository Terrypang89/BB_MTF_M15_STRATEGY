# Multi-Input Transition Prediction Analysis — V36.03

## 1. Data Summary & Train/Test Split

- **Total DUALTF rows**: 7608
- **Rows kept (real HTF+MTF data)**: 7333
- **Rows dropped (no-data)**: 275
- **TRAIN rows (first 70%)**: 5133
- **TEST rows (last 30%)**: 2200
- **TRAIN transitions**: 485
- **TEST transitions**: 221
- **TRAIN majority baseline**: 35.5% (always predict 'down')
- **TEST majority baseline**: 35.3% (always predict 'down')

> The TEST accuracy is the honest number — predictors are derived on TRAIN, measured on TEST.

## 2. Predictor Comparison

| Predictor | Inputs | TRAIN Accuracy | TEST Accuracy | vs TEST Baseline |
|-----------|--------|---------------|---------------|-----------------|
| A — BBLoc slope only | bbloc_slope | 39.4% | 43.9% | +8.6pp |
| B — BBLoc + HTF | bbloc_slope + htf_direction | 40.6% | 41.2% | +5.9pp |
| C — BBLoc + M15 | bbloc_slope + m15_cascade | 43.7% | 43.0% | +7.7pp |
| D — All combined | bbloc + htf + m15 + duration | 40.8% | 35.3% | +0.0pp |
| E — M15 alone | m15_cascade | 39.4% | 35.7% | +0.5pp |

**Baselines**: Random = 33.3% | Majority = 35.3% | BBLoc-only full-dataset benchmark = 40.9% (706 transitions)

> Note: BBLoc-only on TEST (43.9%) differs from the full-dataset benchmark (40.9%) because the TEST subset (221 transitions) is a different time period. The TEST number is the fair comparison for all predictors.

## 3. Ablation — Which Inputs Help?

| Configuration | TEST Accuracy | Delta vs BBLoc-only |
|---------------|-------------|-------------------|
| BBLoc slope only (baseline) | 43.9% | — |
| + HTF direction | 41.2% | -2.7pp |
| + M15 cascade | 43.0% | -0.9pp |
| + HTF + M15 + duration | 35.3% | -8.6pp |
| M15 alone (for comparison) | 35.7% | -8.1pp |

### Input Ranking (by TEST contribution):
- **1. bbloc+m15**: -0.9pp on TEST
- **2. bbloc+htf**: -2.7pp on TEST
- **3. m15_alone**: -8.1pp on TEST
- **4. bbloc+htf+m15+dur**: -8.6pp on TEST

## 4. Targeted Predictor — High-Confidence Only

Instead of predicting every transition, predict only when inputs agree:

| Confidence Level | Predictions Made | Correct | Accuracy | Coverage |
|-----------------|-----------------|---------|----------|----------|
| High only | 18 | 9 | 50.0% | 8.1% |
| Medium only | 103 | 44 | 42.7% | 46.6% |
| All predictions made | 121 | 53 | 43.8% | 54.8% |
| Skipped | 100 | — | — | 45.2% |

## 5. Overfitting Check

| Predictor | TRAIN Acc | TEST Acc | Gap | Flag |
|-----------|----------|----------|-----|------|
| A — BBLoc only | 39.4% | 43.9% | -4.5pp | OK |
| B — BBLoc + HTF | 40.6% | 41.2% | -0.6pp | OK |
| C — BBLoc + M15 | 43.7% | 43.0% | +0.7pp | OK |
| D — All combined | 40.8% | 35.3% | +5.5pp | OVERFIT |
| E — M15 alone | 39.4% | 35.7% | +3.6pp | OK |

## 6. Honest Verdict

**Multi-input does NOT meaningfully beat BBLoc-only on TEST.**

- Best TEST accuracy: **43.9%** (A), vs BBLoc-only TEST = 43.9%
- Margin: **0.0 percentage points** (not meaningful)
- vs majority baseline (35.3%): **+8.6pp**

**Prediction is NOT VIABLE at 43.9% TEST accuracy.** Even the best multi-input predictor doesn't reach a level that justifies building Part 4 on prediction alone.

**OVERFITTING FLAGS:**
- D: TRAIN 40.8% >> TEST 35.3% (gap 5.5pp)

**Targeted approach**: 43.8% on 121 predictions (54.8% coverage). Modest improvement over blind prediction, but limited coverage.

**Recommendation**: Use identification-based trading (Part 3), not prediction. The signal is too weak to build a prediction layer on top.
