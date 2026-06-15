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

## OOS Validation Plan

- **OOS period**: Jan 1 - Feb 27, Apr 1 - Apr 29, 2026 (V30.02 log)
- **Key question**: How many H4-compression episodes exist?
  Do they resolve both G and F ways?
- **Pass criteria**: >= 3 episodes with mixed G/F resolution
- **Fail criteria**: < 3 episodes OR all same-direction resolution
  → G/F untestable, need different period or cascade-model redesign
