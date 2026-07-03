# Tier 2 Reach Analysis

> For detector triggers with M30 already at/beyond its band (~68% of followed triggers), does the H1 band get reached? Decides cascade-vs-skip for the at-band majority.

## Data Summary

| Metric | Value |
|--------|-------|
| Total DUALTF rows | 7608 |
| Total triggers | 497 |
| At-band triggers (M30 at/beyond) | 222 |
| At-band UP | 111 |
| At-band DOWN | 111 |
| At-band UP followed | 63 |
| At-band DOWN followed | 53 |

### Match-Check Against TARGET_REACH_ANALYSIS

| Check | Expected | Actual | Match |
|-------|----------|--------|-------|
| At-band ALL UP | 111 | 111 | YES |
| At-band ALL DOWN | 111 | 111 | YES |
| At-band FOLLOWED UP | 63 | 63 | YES |
| At-band FOLLOWED DOWN | 53 | 53 | YES |

### H1 Zone Distribution of At-Band Triggers

| Zone | Count | % |
|------|-------|---|
| FAR | 4 | 1.8% |
| MID | 34 | 15.3% |
| NEAR | 41 | 18.5% |
| AT/BEYOND | 143 | 64.4% |

## Measurement A — Tier-2 Reach

For at-band triggers: H1-band reach % per h1-zone x direction x window. ALL and FOLLOWED subsets.

**Window N=12 rows (60 minutes)**

| Zone | Direction | ALL Reach % (n) | FOLLOWED Reach % (n) |
|------|-----------|-----------------|---------------------|
| FAR | UP | 0% (n=0) * | 0% (n=0) * |
| FAR | DOWN | 25% (n=4) * | 33% (n=3) * |
| MID | UP | 8% (n=12) * | 14% (n=7) * |
| MID | DOWN | 23% (n=22) | 9% (n=11) * |
| NEAR | UP | 64% (n=28) | 70% (n=20) |
| NEAR | DOWN | 46% (n=13) * | 67% (n=6) * |
| AT/BEYOND | UP | 97% (n=71) | 100% (n=36) |
| AT/BEYOND | DOWN | 99% (n=72) | 100% (n=33) |

**Window N=24 rows (120 minutes)**

| Zone | Direction | ALL Reach % (n) | FOLLOWED Reach % (n) |
|------|-----------|-----------------|---------------------|
| FAR | UP | 0% (n=0) * | 0% (n=0) * |
| FAR | DOWN | 50% (n=4) * | 67% (n=3) * |
| MID | UP | 17% (n=12) * | 14% (n=7) * |
| MID | DOWN | 50% (n=22) | 45% (n=11) * |
| NEAR | UP | 79% (n=28) | 80% (n=20) |
| NEAR | DOWN | 54% (n=13) * | 67% (n=6) * |
| AT/BEYOND | UP | 99% (n=71) | 100% (n=36) |
| AT/BEYOND | DOWN | 99% (n=72) | 100% (n=33) |

**Window N=48 rows (240 minutes)**

| Zone | Direction | ALL Reach % (n) | FOLLOWED Reach % (n) |
|------|-----------|-----------------|---------------------|
| FAR | UP | 0% (n=0) * | 0% (n=0) * |
| FAR | DOWN | 75% (n=4) * | 67% (n=3) * |
| MID | UP | 75% (n=12) * | 71% (n=7) * |
| MID | DOWN | 73% (n=22) | 82% (n=11) * |
| NEAR | UP | 82% (n=28) | 85% (n=20) |
| NEAR | DOWN | 62% (n=13) * | 67% (n=6) * |
| AT/BEYOND | UP | 99% (n=71) | 100% (n=36) |
| AT/BEYOND | DOWN | 99% (n=72) | 100% (n=33) |

**Window N=96 rows (480 minutes)**

| Zone | Direction | ALL Reach % (n) | FOLLOWED Reach % (n) |
|------|-----------|-----------------|---------------------|
| FAR | UP | 0% (n=0) * | 0% (n=0) * |
| FAR | DOWN | 75% (n=4) * | 67% (n=3) * |
| MID | UP | 75% (n=12) * | 71% (n=7) * |
| MID | DOWN | 77% (n=22) | 91% (n=11) * |
| NEAR | UP | 89% (n=28) | 90% (n=20) |
| NEAR | DOWN | 62% (n=13) * | 67% (n=6) * |
| AT/BEYOND | UP | 100% (n=71) | 100% (n=36) |
| AT/BEYOND | DOWN | 99% (n=72) | 100% (n=33) |

* = low sample (n < 15)

## Measurement B — Base-Rate Lift

Unconditional: from ALL rows (no trigger) where m30bbloc is at/beyond AND h1bbloc is in the given zone, how often is H1 band reached within N=48? Lift = trigger-conditioned reach / unconditional reach.

**Pooling:** trigger-conditioned uses ALL triggers (NEAR+MID pooled, both directions). Base rate uses NEAR+MID pooled, both directions.

| Zone | Trigger Reach % (n) | Base Rate % (n) | Lift |
|------|---------------------|-----------------|------|
| FAR | 75% (n=4) | 75% (n=16) | 1.00x |
| MID | 74% (n=34) | 70% (n=279) | 1.06x |
| NEAR | 76% (n=41) | 79% (n=420) | 0.96x |
| AT/BEYOND | 99% (n=143) | 99% (n=2060) | 0.99x |

**Pooled (NEAR+MID, both directions):**

| | Trigger Reach % | Base Rate % | Lift |
|---|-----------------|-------------|------|
| NEAR+MID | 74.7% (n=44) | 75.3% | 0.99x |

## Measurement C — Tier-3 (Informational)

At-band triggers where H1 is ALSO at/beyond. H4-band reach at N=48.

| Metric | Value |
|--------|-------|
| Tier-3 trigger count | 143 |
| % of at-band triggers | 64.4% |
| H4 reach (ALL) | 97/143 = 68% |
| H4 reach (FOLLOWED) | 43/68 = 63% |

> Tier-3 sample adequate (n=68). H4 reach from tier-3: 63%.

## VERDICT

**Criteria applied mechanically at N=48, FOLLOWED subset, NEAR+MID pooled, both directions — no post-hoc adjustment.**

| Criterion | Threshold | Actual | Result |
|-----------|-----------|--------|--------|
| T2-1: H1 reach >= 50% | >= 50% | 79.5% (n=44) | PASS |
| T2-2: Lift >= 1.3x | >= 1.3x | 0.99x | FAIL |

**CONCLUSION: TIER 2 DEAD.** At-band triggers are SKIPPED. Failed: T2-2: lift 0.99x < 1.3x. Part 5 trades only the NEAR/MID minority (where M30 is not yet at the band) with the M30-band TP. No cascade for the at-band majority.

## LIMITATIONS

1. **Reach is not profit.** Price can stop you out on the way, then reach the band. No stops, no path analysis — only endpoint reach.
2. **bbloc-distance is not price-RR.** Band prices not logged. Real risk-reward waits for V36.11 backtest.
3. **Small cells.** Some zone/direction combos have n < 15. Flagged with *. Do not over-interpret individual cells.
4. **Weekend row-index caveat.** Rows are M5 bar index, not wall-clock. 48 rows may cover > 4 hours on Friday or < 4 hours mid-session.
5. **Tier-2 delay is not fill quality.** A trigger that reaches H1 band at row j+47 is technically 'reached' but the price move may have been too late to capture meaningful profit after the M30 band was already exhausted.

---

*Analysis generated by `scripts/analyze_tier2_reach.py`. Deterministic — re-running produces identical numbers.*
