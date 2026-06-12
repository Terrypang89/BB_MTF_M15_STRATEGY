REPLAY BENCHMARK — 2026.03.02 04:00 to 2026.03.20 09:00

1. IdentifyScenario must match expected_scenario on >= 95% of the 78 rows
   (substate mismatches within same parent scenario count as half-miss)

2. DecideAction over the window must produce >= 6 leg-capture entries
   matching these verified arrow legs:
   - 03.03 ~08:00-20:00 SELL leg (crash) — entry valid once M30+M15 mid=2
     and B3 disabled (H4 mid=3 by 16:00 / diffBBW contradicts 512 label)
   - 03.04 ~04:00-16:00 BUY leg (H4 mid=3 → B3 off)
   - 03.04 20:00 SELL leg (H4 mid=2 aligned)
   - 03.05 04:00-08:00 BUY leg (short)
   - 03.05 12:00-22:00 SELL leg (full alignment — cleanest of window)
   - 03.06 04:00-08:00 BUY recovery leg
   - 03.10 04:45+ BUY leg (the one TofyTrade4 actually caught)
   - 03.17-03.19 SELL run (must be held, not churned: no exit within
     3 bars of entry on a mid=3 wobble; X1/boundary or trailing stop only)

3. Max single-trade adverse excursion <= M30-band stop distance at entry
   (the -191.29 nine-day hold must be IMPOSSIBLE: stop set at entry,
    emergency $50 exit unconditional)

4. Zero positions held > 3 days
