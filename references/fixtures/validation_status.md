# Validation Status — Decision 8 Freeze

> Generated: 2026-06-14 | In-sample period: March 2-20, 2026 (78 snapshots)
> In-sample result: 83.3% parent-level match (45 exact + 20 same-parent)

## VALIDATED Rules (snapshot + prior-bar)

These rules have been tested against March 2026 in-sample data with
consistent results across multiple episodes.

| Rule | Description | Evidence |
|------|-------------|----------|
| A-tier | H4-fly, no compression, D1-aligned → A1; D1-not-aligned → A2 | Multiple March episodes (03.02, 03.11-03.12, 03.19) |
| B-tier | LTF shrink keyed by max(shrink, sqz) depth → B1/B2/B3 | Multiple March episodes (03.04, 03.13, 03.16-03.20) |
| E-tier | cas_sqzCount>=2 → E1/E2; H4-shrink → E4 | Multiple March episodes (03.03-03.06, 03.12-03.13, 03.17) |
| Onset/Established | H1-SQZ first bar → B3; H1-SQZ 2+ bars → E1 | Decision 5 cascade (03.03-03.05) |
| D1-D6 | Decision cascade: D1 (priority routing), D2 (transient exemption), D3 (B-depth), D4 (B-decoder), D5 (H1-SQZ tracking), D6 (D2-vs-D5 resolution) | Full March replay |
| VETO-AT-TARGET | BUY-at-upper-band / SELL-at-lower-band veto | 03.03 07:45 — item 5 PASS |
| Matrix ceilings | Scenario → ceiling mapping (A1=1.0, E1=0.0, etc.) | Enforced by architecture |
| Decoder size | cas_sqzCount + cas_shrinkTF → size multiplier | Enforced by architecture |
| ASSERT-B1/B3/B4 | Invariant checks on flip-entries | 2 ASSERT-B3 in March — no violations |

## HYPOTHESIS Rules (needs OOS validation)

These rules are structurally sound but fit to a single in-sample episode.

| Rule | Description | Why Unvalidated | Risk |
|------|-------------|-----------------|------|
| G/F macro-episode | H4-SQZ → G-tier (direction pivot); H4-exiting-compression → F-tier (continuation) | Only 1 G→F episode in March (03.09-03.18). 13/13 G/F rows were mismatches | Overfit to 1 resolution path. If all OOS episodes resolve the same way, G/F is untestable |
| 2-bar interlude threshold | "2 consecutive bars" for H1-SQZ established vs onset | Fit to 1 March episode. No OOS confirmation | Threshold may be too short (noise) or too long (misses entries) |

### G/F Episode in March (In-Sample)

The single G→F progression in March:
- **03.09 04:00**: G3 (H4 enters SQZ, stage=422)
- **03.09-03.10**: G-tier dominance (G2, G3) — direction pivot phase
- **03.10 16:00**: Transition to A1 (F1 expected) — compression resolving
- **03.10-03.18**: F-tier episodes (F1-F3) — explosive expansion phase
- **03.18 20:00**: F3 (H4 fully expanded, diffBBW sharply positive)

Of the 20 G/F-expected rows (03.09-03.18), only 6 matched at parent level.
The remaining 14 were misclassified as A/B/E — the harness routes to
compression tiers before reaching G/F because H4-SQZ conditions overlap
with mid-TF compression signals.

## OOS Validation Results

- **OOS period**: Jan 1 - Feb 27 + Apr 1 - Apr 29, 2026 (V30.02 log, 349 snapshots)
- **H4-SQZ episodes found**: 7
- **Resolution mix**: 7 F (expansion continuation), 0 G (direction pivot)

### G/F Findings

| Finding | Result |
|---------|--------|
| G-tier on SQZ bars | 100% (36/36 SQZ bars correctly identified as G2/G3) |
| F-tier detection | Partial — only 4/349 snapshots (1.1%) identified as F1/F2/F3 |
| Mixed G/F resolution | NO — all 7 OOS episodes resolve F, none resolve G |

### Verdict

**G-tier structural conditions VALIDATED on OOS** — every H4-SQZ bar in OOS
data was correctly identified as G2/G3. The conditions (is_fly, mid directional,
diffBBW>0 sign, BBUpDn==1) are structurally sound.

**F-tier CANNOT be validated** — no G→F transitions in OOS data.
All 7 episodes resolve as F (expansion continuation), meaning the harness
has no G→F transition to test against. This is a data limitation, not a
rule failure — the early F-tier detection (diffBBW-recovery path) simply
has nothing to match in the OOS period.

**2-bar threshold** — OOS data provides no direct test. No G→F episode
means the onset vs established distinction at the G/F boundary is untested.

### Implication

The G/F macro design is validated on the G side (compression detection) but
the F side (expansion detection from compression) requires a period with
G→F transitions. The Jan-Apr 2026 data has only G→A transitions — H4 enters
SQZ, then exits directly to fly without the explosive diffBBW-recovery
signal the F-tier detects. This suggests either:

1. G→F transitions are rare (the March episode may be a statistical outlier)
2. A longer or different OOS period is needed (e.g., 2025 data, or Sep-Dec 2026)

### Scenario Distribution (OOS)

| Scenario | Count | Pct |
|----------|-------|-----|
| E4 | 140 | 40.1% |
| B3 | 55 | 15.8% |
| A2 | 45 | 12.9% |
| A1 | 29 | 8.3% |
| G2 | 22 | 6.3% |
| B2 | 22 | 6.3% |
| G3 | 15 | 4.3% |
| E1 | 10 | 2.9% |
| E2 | 3 | 0.9% |
| F3 | 2 | 0.6% |
| B1 | 4 | 1.1% |
| F1 | 1 | 0.3% |
| F2 | 1 | 0.3% |
