# Full Decision Flow
## BB Multi-Timeframe Trade Strategy — Complete Gate-by-Gate Logic

> Execute every gate in order on each new bar close (M30, M15, or H1).
> A gate that fails **stops the flow** — no entry is made until all gates pass.

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│  TIMEFRAME ROLES                                                │
├──────────┬──────────────────────────────────────────────────────┤
│  W1      │  Ultra-macro direction — multi-week wind             │
│  D1      │  Daily macro — final price target ceiling/floor      │
│  H4      │  Macro bias — sets M30 target; controls gate filters │
│  H1      │  Chain anchor + G0 sideway confirm                   │
│  M30     │  Mid TF Primary — trend driver                       │
│  M15     │  Mid TF Entry — full stage + midtrend alignment gate  │
│  ATRSL   │  Dynamic stop — dir=0=uptrend / dir=1=downtrend  (no dir=2)  │
└──────────┴──────────────────────────────────────────────────────┘
```
