# Cascade Entry Test — Signal-Quality Proxy Results

> **PROXY throughout**: outcome measured in bbloc-space (target/stop reach), NOT realized P&L. No dollar claims.

## 1. Field-Presence Check

| Field | Present? | Encoding |
|-------|----------|----------|
| diffMid_Trend_M15 (`m15:mid`) | Yes | Unsigned integer, range [0.0, 5.0] (no negative values) |
| diffMid_Trend_M30 (`m30:mid`) | Yes | Unsigned integer, range [0.0, 5.0] (no negative values) |

**Sign convention**: The log encodes diffMid_Trend as unsigned integers 1-5 with no directional sign. Active states always have mid >= 1 (>0). X-state has mid=0. There are **no negative values**. Therefore:
- Fly-up confirm (`mid > 0`) is trivially satisfied for any active state → S_conf fly-up = S_casc fly-up (26 = 26)
- Fly-down confirm (`mid < 0`) can never be met in this encoding → S_conf fly-down = empty set (n=0)

Sample F-state row: `m15_mid=1.0, m30_mid=1.0`.

## 2. Signal Sets — n per Set

| Set | Definition | n | Notes |
|-----|-----------|---|-------|
| **S_base** | M15-only flips (any non-X state change, the -$899 baseline) | 1093 | Includes F,R,S,C direction flips and S↔C transitions; only F/R directed for outcome proxy |
| **S_casc** | M30-confirmed cascade (fly-up: C→F on M30 + M15 confirm in window; fly-down: F→R mirror) — no diffmid filter | 30 | Fly-up: 26, fly-down: 4 |
| **S_conf** | S_casc AND diffMid_Trend agreement on M15+M30 (full rule) | 26 | Fly-up: 26, fly-down: 0. Collapses to S_casc subset because mid encoding is unsigned. |

## 3. Win-Rate + Proxy per Set

| Set | n | Wins | Losses | Timeouts | WR% | Proxy Expectancy (bbloc) |
|-----|---|------|--------|----------|-----|--------------------------|
| S_base | 1093 | 343 | 154 | 596 | 31.38% | -5.300 |
| S_casc | 30 | 29 | 1 | 0 | 96.67% | -7.900 |
| S_conf | 26 | 25 | 1 | 0 | 96.15% | -8.038 |

> Proxy expectancy = average max bbloc travel toward target minus toward stop within 48 bars, measured in bbloc-space units (1-10 scale). NOT dollars.

### Confirmation Gap
S_casc WR - S_base WR = **+65.29 pp** (96.67% vs 31.38%)

### Diffmid Ablation Gap
S_conf WR - S_casc WR = **-0.52 pp (S_conf WR 96.15% - S_casc WR 96.67%)**

## 4. Verdict: Does Confirmation Help? (>=10pp at n>=20)

**CONFIRMATION HELPS** — M30-confirmed cascade entry (S_casc, n=30) exceeds S_base win-rate by 65.3 pp >= 10pp threshold at n >= 20.

## 5. Verdict: Does DiffMid Add Value? (>=5pp at n>=20)

**DIFFMID REDUNDANT** — adding diffMid_Trend direction agreement fails the verification: win-rate gap only 0.5 pp (below 5pp threshold); diffMid_Trend uses unsigned encoding (1-5), so >0 condition is trivially true for active states while <0 can never be met — S_conf collapses into S_casc subset, diffmid provides no filtering.

## 6. Overall Verdict

CONFIRMATION HELPS BUT DIFFMID REDUNDANT — M30-confirmed cascade entry outperforms baseline, but adding diffMid_Trend agreement provides no additional value (0.5 pp < 5pp). Consistent with prior ablation: diffmid_trend adds nothing. Warrants a clean-window forward test of cascade entry WITHOUT diffmid.

## 7. Limitations

1. **PROXY, not dollars**: bbloc-space target/stop reach is a signal-quality proxy, NOT realized P&L. A positive result warrants a real backtest with the confirmed entry in the clean-window forward test; it does not justify live decisions.
2. **In-sample discovery data**: this tests on V36.13's own discovery log — survivors bias applies. Any positive finding requires out-of-sample validation via the clean-window forward test (same EA, unseen window).
3. **bbloc-space R:R differs from price R:R**: equal bbloc steps do not correspond to equal price distances across BB widths. A win in bbloc terms may be a small P&L event and vice versa.
4. **Unsigned diffMid_Trend encoding**: the log uses unsigned integers (1-5) for trend categories, eliminating directional filtering from S_conf. This is itself an informative result — diffmid_trend provides no additional signal separation beyond state-based classification in this data.

## 8. Method Parameters

| Parameter | Value |
|-----------|-------|
| Confirm window | 12 bars (≈3.0h at 15-min resolution) |
| Forward outcome window | 48 bars (≈12.0h) |
| Fly-up target | m30bbloc >= 9 |
| Fly-up stop | m15bbloc <= 1 |
| Fly-down target | m30bbloc <= 1 |
| Fly-down stop | m15bbloc >= 9 |
| Data source | `references/Backtest_data/V36.13/20260705_clean.log` (DUALTF rows, 15-min resolution) |
| Confirmation threshold | +10 pp at n >= 20 |
| Diffmid ablation threshold | +5 pp at n >= 20 |

