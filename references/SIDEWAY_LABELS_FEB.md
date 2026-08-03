# Sideway labels - February 2026

Human-labelled ground truth. Detectors are scored AGAINST this file; this file is never
derived from detector output.

## Protocol
1. Label February by eye, from the chart, WITHOUT looking at any detector output.
2. Tune the detector against February labels.
3. Label a SECOND month (March) BEFORE running the tuned detector on it.
4. Run once on March. That is the number that counts.

Labelling after seeing detector output, or scoring on the same month used for tuning,
produces a meaningless result - it is the same failure mode as the S-F cell
(PF 1.55 in-sample -> 0.13 out-of-sample).

## How to label
- Record the START and END of each range you judge to be sideway.
- Use M15 bar times, format `2026.02.03 12:40`.
- LABEL THE EDGES CAREFULLY. Where a range begins and ends is where detectors fail and
  where exit decisions actually matter. A range labelled only in its obvious middle
  lets a lazy detector score well.
- Mark confidence: `definite` if you would bet on it, `arguable` if it is a judgement
  call. These are scored separately - a detector that gets the definite ones right and
  the arguable ones wrong is fine; one that is random on the definite ones is broken.
- Kind: `quiet` (price barely moves) or `choppy` (price swings a lot but returns).
  These are different conditions and detectors behave differently on them.
- Leave the table empty where you see no sideway. Absence is a label too.

## Labels

| # | start | end | confidence | kind | notes |
|---|-------|-----|------------|------|-------|
| 1 | 2026.02.02 15:00 | 2026.02.03 01:00 | - | - | - |
| 2 | 2026.02.03 13:30 | 2026.02.04 02:00 | - | - | - |
| 3 | 2026.02.04 08:30 | 2026.02.04 16:15 | - | - | - |
| 4 | 2026.02.05 08:30 | 2026.02.05 21:15 | - | - | - |
| 5 | 2026.02.06 09:40 | 2026.02.06 13:00 | - | - | - |
| 6 | 2026.02.06 20:30 | 2026.02.06 23:45 | - | - | - |
| 7 | 2026.02.09 06:15 | 2026.02.09 16:30 | - | - | - |
| 8 | 2026.02.10 03:45 | 2026.02.11 01:15 | - | - | - |
| 9 | 2026.02.11 07:30 | 2026.02.11 11:30 | - | - | - |
| 10 | 2026.02.11 20:45 | 2026.02.11 23:45 | - | - | - |
| 11 | 2026.02.12 03:45 | 2026.02.12 18:00 | - | - | - |
| 12 | 2026.02.12 21:45 | 2026.02.13 03:00 | - | - | - |
| 13 | 2026.02.13 06:45 | 2026.02.13 15:45 | - | - | - |
| 14 | 2026.02.13 23:45 | 2026.02.16 04:15 | - | - | - |
| 15 | 2026.02.16 13:15 | 2026.02.17 01:45 | - | - | - |
| 16 | 2026.02.17 10:45 | 2026.02.17 15:30 | - | - | - |
| 17 | 2026.02.17 19:25 | 2026.02.18 03:45 | - | - | - |
| 18 | 2026.02.18 08:45 | 2026.02.18 14:45 | - | - | - |
| 19 | 2026.02.19 01:45 | 2026.02.19 07:15 | - | - | - |
| 20 | 2026.02.19 14:45 | 2026.02.19 16:45 | - | - | - |
| 21 | 2026.02.19 21:30 | 2026.02.20 07:45 | - | - | - |
| 22 | 2026.02.20 12:45 | 2026.02.20 14:45 | - | - | - |
| 23 | 2026.02.23 06:45 | 2026.02.23 16:15 | - | - | - |
| 24 | 2026.02.24 07:00 | 2026.02.24 14:15 | - | - | - |
| 25 | 2026.02.24 21:30 | 2026.02.25 02:45 | - | - | - |
| 26 | 2026.02.25 06:15 | 2026.02.25 17:45 | - | - | - |
| 27 | 2026.02.27 01:45 | 2026.02.27 15:00 | - | - | - |

## Per-day reference (computed from the log - NOT labels)

| date | bars | open | close | net | range | path | ER |
|---|---|---|---|---|---|---|---|
| 2026.02.02 | 92 | 4809.72 | 4669.60 | 140.12 | 394.28 | 2267.22 | 0.062 |
| 2026.02.03 | 92 | 4671.46 | 4940.44 | 268.98 | 309.81 | 1281.24 | 0.210 |
| 2026.02.04 | 92 | 4944.76 | 4961.64 | 16.88 | 192.94 | 1020.78 | 0.017 |
| 2026.02.05 | 92 | 4968.94 | 4763.60 | 205.34 | 258.99 | 1382.32 | 0.149 |
| 2026.02.06 | 92 | 4792.68 | 4960.18 | 167.50 | 283.41 | 1034.36 | 0.162 |
| 2026.02.09 | 92 | 4983.69 | 5061.62 | 77.93 | 100.16 | 649.17 | 0.120 |
| 2026.02.10 | 92 | 5058.83 | 5024.32 | 34.51 | 61.61 | 632.67 | 0.055 |
| 2026.02.11 | 92 | 5025.85 | 5079.88 | 54.03 | 86.07 | 583.67 | 0.093 |
| 2026.02.12 | 92 | 5090.28 | 4918.20 | 172.08 | 193.10 | 702.24 | 0.245 |
| 2026.02.13 | 92 | 4926.44 | 5038.62 | 112.18 | 130.54 | 634.28 | 0.177 |
| 2026.02.16 | 82 | 5037.76 | 4991.18 | 46.58 | 61.57 | 307.20 | 0.152 |
| 2026.02.17 | 92 | 4996.25 | 4879.31 | 116.94 | 140.91 | 652.88 | 0.179 |
| 2026.02.18 | 92 | 4879.22 | 4980.00 | 100.78 | 146.48 | 383.16 | 0.263 |
| 2026.02.19 | 92 | 4975.45 | 4998.64 | 23.19 | 58.54 | 407.49 | 0.057 |
| 2026.02.20 | 92 | 4999.31 | 5099.48 | 100.17 | 112.09 | 440.15 | 0.228 |
| 2026.02.23 | 92 | 5109.50 | 5228.56 | 119.06 | 127.00 | 522.70 | 0.228 |
| 2026.02.24 | 92 | 5230.39 | 5150.54 | 79.85 | 139.62 | 543.05 | 0.147 |
| 2026.02.25 | 92 | 5143.77 | 5170.12 | 26.35 | 84.16 | 449.09 | 0.059 |
| 2026.02.26 | 92 | 5168.56 | 5190.08 | 21.52 | 58.85 | 422.88 | 0.051 |
| 2026.02.27 | 92 | 5187.91 | 5274.44 | 86.53 | 100.96 | 397.93 | 0.217 |
