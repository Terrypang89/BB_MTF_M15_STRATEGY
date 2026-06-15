# Validation Status — Decision 8 Freeze (Corrected)

> Generated: 2026-06-14 | Corrected: 2026-06-14
> In-sample period: March 2-20, 2026 (78 snapshots) — 83.3% parent-level match
> OOS period: Jan 1 - Feb 27 + Apr 1 - Apr 29, 2026 (349 snapshots)

## Terminology Clarification

| Term | Meaning |
|------|---------|
| G-tier on SQZ bars | "Compression detected, pivot pending" — NOT "this will resolve as G reversal" |
| G-vs-F discrimination | Predicting whether compression resolves as G (reversal) or F (continuation) |
| G reversal resolution | H4-SQZ resolves with directional pivot opposite to prior trend |
| F continuation resolution | H4-SQZ resolves with explosive expansion in same direction |

The 36/36 "G-tier detection" in OOS = **compression-state detection**, not G-vs-F discrimination.
Every H4-SQZ bar was correctly flagged as G2/G3 (pivot-pending). But none of the 7 OOS episodes
actually reversed — all 7 continued in F direction. The G-vs-F discriminator was never tested.

---

## OOS-VALIDATED Rules (snapshot + prior-bar)

These rules have been tested on both in-sample (March) and out-of-sample (Jan-Feb+Apr) data.

| Rule | Description | In-Sample | OOS |
|------|-------------|-----------|-----|
| A-tier | H4-fly, no compression, D1-aligned → A1; D1-not-aligned → A2 | Multiple episodes | 74/349 snapshots (21.2%) |
| B-tier | LTF shrink keyed by max(shrink, sqz) depth → B1/B2/B3 | Multiple episodes | 81/349 snapshots (23.2%) |
| E-tier | cas_sqzCount>=2 → E1/E2; H4-shrink → E4 | Multiple episodes | 153/349 snapshots (43.8%) |
| G-tier compression entry | H4-SQZ detected → G2/G3 (pivot-pending state) | 03.09-03.10 | 36/36 SQZ bars (100%) |
| F continuation resolution | H4-SQZ resolves with explosive expansion | 03.10-03.18 | 7/7 episodes (100%) |
| Onset/Established | H1-SQZ first bar → B3; H1-SQZ 2+ bars → E1 | Decision 5 cascade | Consistent on OOS |
| D1-D6 | Decision cascade (priority routing, transient exemption, B-depth, B-decoder, H1-SQZ tracking, D2-vs-D5 resolution) | Full March replay | Full OOS replay |
| VETO-AT-TARGET | BUY-at-upper-band / SELL-at-lower-band veto | 03.03 07:45 — item 5 PASS | Architecture-enforced |
| Matrix ceilings | Scenario → ceiling mapping | Enforced | Enforced |
| Decoder size | cas_sqzCount + cas_shrinkTF → size multiplier | Enforced | Enforced |
| ASSERT-B1/B3/B4 | Invariant checks on flip-entries | 2 ASSERT-B3 in March | Architecture-enforced |

## STILL HYPOTHESIS — G Reversal Branch

The G reversal branch has never fired on OOS data.

| Rule | Description | Why Untested | Risk |
|------|-------------|--------------|------|
| G reversal resolution | H4-SQZ resolves with directional pivot opposite to prior trend | 0 of 7 OOS episodes resolved G — the reversal branch never executed | If G episodes are rare (<1 per quarter), this branch may remain unvalidated for months |
| G-vs-F discriminator | Predicting G (reversal) vs F (continuation) during PIVOT-PENDING | Requires episodes that resolve both ways — not available in current data | The discriminator may be correct or wrong; there's no way to tell without a G-resolving episode |
| 2-bar interlude threshold | "2 consecutive bars" for H1-SQZ established vs onset at G/F boundary | Never stressed during G→F transitions in OOS (no G→F transitions existed) | Threshold may be too short (noise) or too long (misses entries) |

**This is INSUFFICIENT-DATA, not a rule failure.** The G reversal branch is structurally
defined in the code but has no OOS evidence.

### Data Finding: Jan-Apr 2026 Resolution Mix

| Resolution | Count | Episodes |
|------------|-------|----------|
| F (continuation) | 7 | Ep1 (Jan 5), Ep2 (Jan 8-12), Ep3 (Jan 15-19), Ep4 (Jan 30-Feb 2), Ep5 (Feb 19-20), Ep6 (Apr 13-14), Ep7 (Apr 20-22) |
| G (reversal) | 0 | — |

**G (reversal) is the rare case.** Jan-Apr 2026 contained 7 H4-SQZ episodes and all resolved
as F (expansion continuation). No reversal occurred.

### Candidate Periods for G-Reversal Validation

To validate the G reversal branch, a data period is needed containing at least 1 H4-SQZ episode
that resolves as a directional pivot (G).

| Candidate | Rationale | Status |
|-----------|-----------|--------|
| 2025 data | Full year — likely contains multiple G and F episodes | Need to check if logs exist |
| Sep-Dec 2026 | Future period — may contain reversal episodes | Not yet available |
| May-Jun 2026 | Immediate next quarter | May contain reversal episodes |
| V30.01 log (Jan 2026 only) | Already in repo but subset of V30.02 | Won't help — Ep1-Ep4 are already in OOS |

### OOS Episode Detail (2 Examples)

**Episode 2 — Jan 8-12, 2026**
```
01.08 16:00  G2  H4=423  SQZ *   ← entry: H4 enters compression
01.08 20:00  G2  H4=423  SQZ *   ← pivot-pending
01.09 04:00  G2  H4=423  SQZ *   ← pivot-pending
01.09 08:00  G2  H4=423  SQZ *   ← pivot-pending
01.09 12:00  G2  H4=423  SQZ *   ← pivot-pending
01.09 16:00  G2  H4=423  SQZ *   ← pivot-pending (8 bars total)
01.12 04:00  F3  H4=511  diffBBW=+67.8  ← resolution: F continuation
```

**Episode 5 — Feb 19-20, 2026**
```
02.19 16:00  G3  H4=423  SQZ *   ← entry: H4 enters compression
02.19 20:00  G3  H4=423  SQZ *   ← pivot-pending
02.20 04:00  G2  H4=423  SQZ *   ← pivot-pending
02.20 08:00  G2  H4=423  SQZ *   ← pivot-pending (8 bars total)
02.20 20:00  A2  H4=512  ← resolution: F continuation (F-tier missed)
```

### Scenario Distribution (OOS — 349 snapshots)

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
| B1 | 4 | 1.1% |
| E2 | 3 | 0.9% |
| F3 | 2 | 0.6% |
| F1 | 1 | 0.3% |
| F2 | 1 | 0.3% |
