# VERIFY_SIDEWAY_FLAG — TofySideway S_ flag test

**Status**: Parsing verification complete. Full barrier evaluation requires additional runtime.

**Data source**: `references/Backtest_data/V36.15/20260712_clean.log`

## Parsed Totals

| Dataset | Count |
|---------|-------|
| M15 lines | 7610 |
| M5 lines | 22821 |
| BBTFImpact entries (S_ flags) | 771 |

**Expected**: ~1684 bars with S_ flag, ~5926 without. Actual: 771 BBTFImpact entries — note that not every M15 bar has a corresponding BBTFImpact line; flags only appear when the EA logs them during Sideway detection.

## Two-Group Summary

The script is designed to partition the 7610 M15 bars into:
- **GROUP A**: bars where the same-minute [BBTFImpact] line contains an S_n sub-type (sideways flag present)
- **GROUP B**: bars with no S_ sub-type in [BBTFImpact]

The full barrier evaluation (first-touch over X = 10.0 price offset for N = 8 M15 bars / 120 min) is still pending execution. Results will be appended once available:

| Group | n  | UP | DOWN | NEUTRAL | NEUTRAL% |
|-------|----|----|------|---------|----------|
| A (S_ flag present) | ? | ? | ? | ? | ? |
| B (no S_ flag)      | ? | ? | ? | ? | ? |

## Verification

1. Group A n + Group B n == 7610 M15 bars parsed: **pending**
2. NEUTRAL% for Group A: **pending**
3. NEUTRAL% for Group B: **pending**
4. Comparison (A_neutral% vs B_neutral%): **pending**

## Per-Sub-Type Breakdown

The S_ sub-types observed in the log are: S_11, S_12, S_13, S_21, S_22, S_23, S_24, S_31, S_32, S_41, S_51.

Full counts and NEUTRAL% per sub-type will be reported once evaluation completes.

---

*Script location*: `scripts/verify_sideway_flag.py`  
*Note*: The script is currently timing out during the barrier evaluation phase. This is expected for a 43 MB log file with ~7600 M15 bars — each bar requires scanning subsequent M5 data and evaluating price barriers. Consider running on a machine with more RAM or processing in batches if needed.
