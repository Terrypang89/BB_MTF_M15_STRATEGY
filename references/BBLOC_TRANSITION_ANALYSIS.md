# BBLoc Transition Analysis — V36.03

## 1. Data Summary

- **Total DUALTF rows**: 7608
- **Rows kept (real HTF+MTF data)**: 7333
- **Rows dropped (no-data)**: 275
- **Filter criteria**: dropped rows where htf_scenario contains "X" OR htfbbloc==-1 OR mtf contains "X" OR mtfbbloc==-1

## 2. Transition Frequency

- **Consecutive row pairs**: 7332
- **MTF transitions** (scenario changed): 706
- **Persistence rows** (scenario same): 6626
- **Persistence base rate**: 90.4%

> This is the bar to beat — a predictor that always guesses "persist" gets 90.4% overall accuracy trivially. The TRANSITION accuracy is what matters.

## 3. Pre-Transition BBLoc Pattern (per transition type)

| Type | Count | Avg Pre-BBLoc Slope | % Consistent |
|------|-------|-------------------|-------------|
| CC->CF | 12 | 0.402 | 8.3% |
| CC->CR | 14 | -0.308 | 35.7% |
| CC->FF | 4 | 0.243 | 0.0% |
| CC->RR | 5 | -0.554 | 60.0% |
| CF->CR | 6 | -0.381 | 83.3% |
| CF->CS | 9 | -0.368 | 44.4% |
| CF->FF | 23 | 0.190 | 69.6% |
| CF->RF | 2 | -0.700 | 0.0% |
| CR->CF | 4 | 1.000 | 75.0% |
| CR->CS | 12 | 0.174 | 33.3% |
| CR->FR | 2 | -0.543 | 50.0% |
| CR->RR | 25 | -0.275 | 60.0% |
| CS->CC | 23 | 0.007 | 26.1% |
| CS->CF | 3 | 0.362 | 66.7% |
| CS->CR | 4 | -0.350 | 50.0% |
| CS->RR | 1 | -0.429 | 100.0% |
| FC->FF | 16 | 0.246 | 0.0% |
| FC->FR | 12 | -0.538 | 58.3% |
| FC->RR | 1 | -0.686 | 100.0% |
| FC->SC | 14 | -0.184 | 78.6% |
| FC->SR | 1 | -0.457 | 100.0% |
| FF->FR | 4 | -0.529 | 100.0% |
| FF->FS | 58 | -0.194 | 32.8% |
| FF->RF | 1 | -0.229 | 100.0% |
| FF->SF | 11 | -0.252 | 63.6% |
| FF->SR | 1 | -0.457 | 100.0% |
| FR->FF | 1 | 0.800 | 100.0% |
| FR->FS | 1 | 0.286 | 0.0% |
| FR->RR | 5 | 0.000 | 80.0% |
| FR->SF | 1 | 0.800 | 100.0% |
| FR->SR | 14 | -0.057 | 57.1% |
| FS->FC | 39 | -0.199 | 5.1% |
| FS->FF | 16 | 0.216 | 25.0% |
| FS->FR | 2 | -0.343 | 50.0% |
| FS->RC | 1 | -0.429 | 0.0% |
| FS->RS | 1 | 0.000 | 100.0% |
| FS->SS | 5 | -0.046 | 60.0% |
| RC->FC | 1 | 0.514 | 0.0% |
| RC->RF | 4 | 0.571 | 0.0% |
| RC->RR | 11 | -0.340 | 63.6% |
| RC->SC | 10 | 0.040 | 90.0% |
| RC->SF | 1 | 0.457 | 0.0% |
| RF->FF | 4 | 0.107 | 75.0% |
| RF->RR | 1 | -0.457 | 100.0% |
| RF->RS | 2 | -0.571 | 100.0% |
| RF->SF | 3 | 0.714 | 33.3% |
| RR->FR | 1 | 0.571 | 0.0% |
| RR->RF | 1 | 1.514 | 100.0% |
| RR->RS | 57 | 0.261 | 40.4% |
| RR->SR | 5 | -0.057 | 100.0% |
| RS->FC | 1 | -0.114 | 0.0% |
| RS->FS | 2 | -0.057 | 100.0% |
| RS->RC | 24 | 0.014 | 33.3% |
| RS->RF | 1 | 1.429 | 100.0% |
| RS->RR | 13 | -0.163 | 23.1% |
| RS->SC | 8 | 0.164 | 25.0% |
| RS->SS | 12 | 0.176 | 75.0% |
| SC->CC | 11 | -0.016 | 81.8% |
| SC->CF | 4 | 0.779 | 0.0% |
| SC->CR | 3 | -0.210 | 33.3% |
| SC->FC | 3 | 0.467 | 33.3% |
| SC->RC | 2 | 0.000 | 0.0% |
| SC->SF | 26 | 0.398 | 7.7% |
| SC->SR | 9 | -0.140 | 22.2% |
| SF->CF | 17 | 0.187 | 52.9% |
| SF->CS | 2 | 0.143 | 0.0% |
| SF->FF | 9 | 0.314 | 55.6% |
| SF->RF | 1 | -0.800 | 0.0% |
| SF->RR | 1 | -1.257 | 100.0% |
| SF->SR | 5 | -0.560 | 80.0% |
| SF->SS | 16 | -0.195 | 25.0% |
| SR->CR | 15 | -0.417 | 33.3% |
| SR->FR | 1 | -0.143 | 100.0% |
| SR->FS | 1 | 0.286 | 0.0% |
| SR->RR | 1 | -0.743 | 0.0% |
| SR->SF | 6 | 0.467 | 66.7% |
| SR->SS | 12 | 0.138 | 16.7% |
| SS->CC | 1 | 0.457 | 100.0% |
| SS->CR | 1 | -1.257 | 100.0% |
| SS->CS | 8 | 0.046 | 87.5% |
| SS->FF | 1 | 0.000 | 0.0% |
| SS->FS | 2 | -0.057 | 0.0% |
| SS->RS | 2 | -0.686 | 0.0% |
| SS->SC | 26 | 0.110 | 26.9% |
| SS->SF | 3 | 0.238 | 33.3% |
| SS->SR | 1 | -0.171 | 0.0% |


**Slope consistency** = % of transitions where BBLoc slope direction matched the transition direction (rising->up, falling->down, flat->neutral).

## 4. BBLoc Slope Predictor — Transition Accuracy (The Key Number)

**Predictor logic**: Rising BBLoc slope (>0.3) over last 6 bars → predict up-continuation; falling slope (<-0.3) → predict down-reversal; flat → predict persist.

| Metric | Accuracy |
|--------|----------|
| **BBLoc slope predictor (transitions only)** | **40.9%** |
| Baseline — always predict majority direction (down) | 35.4% |
| Baseline — random (3 classes) | 33.3% |

### Overall Accuracy (all pairs, including persistence)

| Metric | Accuracy |
|--------|----------|
| BBLoc slope predictor (all pairs) | 67.4% |
| Baseline — always predict persist | 90.4% |

### Slope Distribution (all 7332 pairs)

| Direction | Count | % |
|-----------|-------|---|
| Rising (>0.3) | 1154 | 15.7% |
| Falling (<-0.3) | 1129 | 15.4% |
| Flat (<=0.3) | 5049 | 68.9% |

### Transition Direction Distribution

| Direction | Count | % |
|-----------|-------|---|
| Up | 243 | 34.4% |
| Down | 250 | 35.4% |
| Neutral | 213 | 30.2% |

## 5. Top Transition Types

| Type | Count |
|------|-------|
| FF->FS | 58 |
| RR->RS | 57 |
| FS->FC | 39 |
| SC->SF | 26 |
| SS->SC | 26 |
| CR->RR | 25 |
| RS->RC | 24 |
| CS->CC | 23 |
| CF->FF | 23 |
| SF->CF | 17 |
| FS->FF | 16 |
| FC->FF | 16 |
| SF->SS | 16 |
| SR->CR | 15 |
| CC->CR | 14 |


## 6. Honest Verdict

**Verdict: MODEST SIGNAL — BEATS BASELINE BUT WEAKLY**

The BBLoc slope predictor achieves **40.9% accuracy on transitions** — better than the majority baseline (35.4%) and random (33.3%), but the margin is only **5.5 percentage points** over majority.

Key context:
- **68.9% of BBLoc slopes are flat** (within 0.3), meaning the predictor defaults to "neutral/persist" most of the time — which is wrong on transition rows by definition. This structural limitation caps accuracy.
- The 5.5% margin (39 more correct predictions out of 706 transitions) is real but modest.
- Some transition types show high consistency (e.g., CF->CR, FC->SC, SC->CC, RC->SC) but these are low-frequency types (n < 15).
- The most common transitions (FF->FS, RR->RS, FS->FC) show low-to-moderate consistency, suggesting BBLoc slope is not predictive for the dominant transition patterns.

**What this means**: BBLoc trajectory carries some signal for MTF transitions, but it's not strong enough to be a standalone predictor. It may be useful as one factor among many (e.g., combined with HTF context, BBUpDn state, or price location). Part 4 could use BBLoc slope as a directional bias, but should not rely on it as the sole predictor.

**For high-consistency transition types**, BBLoc slope is a more reliable signal — these could be candidates for targeted prediction rules.
