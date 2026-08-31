#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ladder_breakout_variant_test.py

What-if test for the SIDEWAY STATE MACHINE breakout rule in
scripts/TofySidewayLadder.mqh (the `sl_sw_state` machine that
SL_ExitMode == 5 reads as sw = (sl_sw_state >= 1)).

Separate file from labelbase_strategy_dmonly_stop.py on purpose: that
script tests the OLD TofySideway `S_` flag + a stop-loss variant (a
different, already-validated experiment with its own regression
baseline) and its own docstring establishes "one script per variant,
don't modify the original" — this is a different signal entirely
(the ladder's sl_sw_state, not S_), so it gets its own file.

QUESTION THIS ANSWERS: does ANDing an extra condition onto the
state-machine breakout —

    CURRENT   sw_brk = raw30                                  (SL_SwReleaseMode == 2, the default)
    PROPOSED  sw_brk = raw30 and (dmt1 < 3 or stage15 is FLY)

— improve the DMONLY-style virtual trade P&L. This makes breakout
HARDER to trigger (an AND, not an OR), so sideway runs persist
LONGER. Reasoning alone says that should worsen the state machine's
existing over-coverage (67.2% of bars vs USER's 46.9% — see
CLAUDE.md "Current Blocker"); this script measures it instead of
assuming it.

METHOD — no MQL5 recompile, no MT5 Tester run needed:
  scripts/TofySidewayLadder.mqh's SL_Update() already prints, once
  per M15 bar, everything needed to REPLAY the state machine's
  control flow without re-deriving any threshold/tag logic:
    [LADDER]  L1tags/L2tags (strings), gate, l2_ok, l3_ok (l3ok is
              informational only - not consumed by the promotion
              step in the real code, see CLAUDE.md's flagged gap),
              ladder_branch (lbr), the REAL sl_sw_state (sw) and
              sl_brk (brk) for that bar.
    [M15]     diffMid_Trend_M15[LA] (dmt1), BBW_stage_M15[LA] (stage15)
    [M30]     BBUppLV_M30[LA], BBLowLV_M30[LA]  (the M30 band -> raw30)
    [M5]      close_M5[LA] (trade/breakout price), diffMid_Trend_M5[LA] (dmt0, entries)
  This script only supplies an alternative breakout PREDICATE and
  replays the same L1/L2 transition control flow SL_Update uses,
  using the ALREADY-COMPUTED tags/gate/l2_ok from the log as ground
  truth (so no BBW_stage/diffMid threshold logic is reimplemented —
  avoids the STORE-vs-RECOMPUTE trap in CLAUDE.md "Recurring Lessons").

REGRESSION CHECK (mandatory, run first): replaying with the CURRENT
breakout rule must reproduce the log's actual sw:[N] trajectory bar
for bar. If it doesn't, this script's parsing/replay has a bug and
the PROPOSED-rule numbers below must not be trusted until it's fixed.

KNOWN LIMITATION (already measured on V38.19/20260830.log - expect
~4-5% mismatch, not 0): the [M15]/[M30]/[M5] diagnostic prints this
script reads close_M5/UppLV_M30/LowLV_M30 from do NOT fire on every
tick - on some M15-bar-boundary ticks [LADDER] prints with no fresh
[M5] line ahead of it, so the close price used here is up to one M5
bar (5 min) stale relative to what SL_Update actually read via
iClose(_Symbol, PERIOD_M5, 0). This is a data-availability gap in
the log, not a logic bug in the replay - the mismatches are sporadic
(near-threshold band crossings), not systematic, and they affect the
CURRENT and PROPOSED trajectories roughly equally (both key off the
same close_M5/band reconstruction), so the relative comparison
between them is more trustworthy than either trajectory's exact
match to the log. Treat results as directional, not to-the-dollar;
for a precise number, this needs the real M5 close either sourced
from a tick/bar CSV export or from an MT5 Tester re-run.

Log encoding: MetaTester logs are UTF-16 (with BOM). Open with
encoding="utf-16" - plain utf-8/ascii open() will garble every line.

Usage:
  python scripts/ladder_breakout_variant_test.py references/Backtest_data/V38.19/20260830.log
"""
import re
import sys

RE_LADDER = re.compile(
    r"\[LADDER\] L1tags:\[([^\]]*)\] L2tags:\[([^\]]*)\] L3tags:\[([^\]]*)\] L4tags:\[[^\]]*\] "
    r"state:\[(-?\d+)\] prev:\[(-?\d+)\] r1:\[\w+\] r2:\[\w+\] r3:\[\w+\] r4:\[\w+\] "
    r"brk:\[(true|false)\] sw:\[(-?\d+)\] gate:\[([01])\] l2ok:\[([1-])\] l3ok:\[([1-])\] lbr:\[([1-])\]"
)
RE_SWCMP_BAR = re.compile(r"\[SWCMP\] bar:\[([\d.]+ [\d:]+)\]")
RE_M15_DMT = re.compile(r"\[M15\],.*diffMid_Trend_M15:\[\s*(-?[\d.]+)")
RE_M15_STAGE = re.compile(r"\[M15\],.*W_stage_M15:\([^)]*\)\[\s*(-?[\d.]+)")
RE_M30_UPP = re.compile(r"\[M30\],.*UppLV_M30:\[\s*(-?[\d.]+)")
RE_M30_LOW = re.compile(r"\[M30\],.*LowLV_M30:\[\s*(-?[\d.]+)")
RE_M5_CLOSE = re.compile(r"\[M5\],.*close_M5:\[\s*(-?[\d.]+)")
RE_M5_DMT = re.compile(r"\[M5\],.*diffMid_Trend_M5:\[\s*(-?[\d.]+)")

FLY_STAGES = {511, 512, 521, 522}


def parse_log(path):
    """Single pass: track latest M15/M30/M5 raw values, snapshot them
    into a record on every [LADDER] line, fill in the bar timestamp
    from the [SWCMP] line that follows it (SL_Update prints LADDER,
    then VIRTUAL, then SWCMP, in that order, once per M15 bar)."""
    records = []
    dmt1 = stage15 = m30_upp = m30_low = m5_close = dmt0 = None
    pending = None

    with open(path, encoding="utf-16", errors="ignore") as f:
        for line in f:
            if "[M15]," in line:
                m = RE_M15_DMT.search(line)
                if m: dmt1 = float(m.group(1))
                m = RE_M15_STAGE.search(line)
                if m: stage15 = int(float(m.group(1)))
                continue
            if "[M30]," in line:
                m = RE_M30_UPP.search(line)
                if m: m30_upp = float(m.group(1))
                m = RE_M30_LOW.search(line)
                if m: m30_low = float(m.group(1))
                continue
            if "[M5]," in line:
                m = RE_M5_CLOSE.search(line)
                if m: m5_close = float(m.group(1))
                m = RE_M5_DMT.search(line)
                if m: dmt0 = float(m.group(1))
                continue

            m = RE_LADDER.search(line)
            if m:
                l1tags, l2tags, l3tags, state, prev, brk, sw, gate, l2ok, l3ok, lbr = m.groups()
                pending = dict(
                    l1tags=l1tags, l2tags=l2tags, l3tags=l3tags,
                    sw_real=int(sw), brk=(brk == "true"),
                    gate=(gate == "1"), l2_ok=(l2ok == "1"), l3_ok=(l3ok == "1"),
                    ladder_branch=(lbr == "1"),
                    dmt1=dmt1, stage15=stage15,
                    m30_upp=m30_upp, m30_low=m30_low,
                    m5_close=m5_close, dmt0=dmt0,
                )
                continue

            m = RE_SWCMP_BAR.search(line)
            if m and pending is not None:
                pending["bar"] = m.group(1)
                records.append(pending)
                pending = None

    return records


def l1_entry(tags):
    return (all(c in tags for c in "SWD")) or (all(c in tags for c in "MW"))


def l1_cont(tags):
    return any(c in tags for c in "SCDM")


def raw30(r):
    if r["m5_close"] is None or r["m30_upp"] is None or r["m30_low"] is None:
        return False
    return r["m5_close"] > r["m30_upp"] or r["m5_close"] < r["m30_low"]


def breakout_current(r):
    """SL_SwReleaseMode == 2 (the repo default): M30 band, always."""
    return raw30(r)


def breakout_proposed(r):
    """User's candidate: raw30 AND (dmt1 < 3 OR M15 stage is FLY)."""
    if r["dmt1"] is None or r["stage15"] is None:
        return raw30(r)  # missing data this bar: fall back, don't fabricate
    fly = r["stage15"] in FLY_STAGES
    return raw30(r) and (r["dmt1"] < 3 or fly)


def replay_state_machine(records, breakout_fn):
    """Reproduces SL_Update's L1/L2/breakout/latch control flow using
    the log's own gate/l2_ok/tags — see module docstring METHOD."""
    sl_sw_state = 0
    trajectory = []
    for r in records:
        sw_state_before = sl_sw_state
        sw_brk = breakout_fn(r)

        if sl_sw_state >= 1 and sw_brk:
            sl_sw_state = 0
        else:
            if sl_sw_state == 0 and r["gate"] and l1_entry(r["l1tags"]):
                sl_sw_state = 1
            if sl_sw_state == 1:
                if l1_cont(r["l1tags"]):
                    if sw_state_before == 1 and r["l2_ok"]:
                        sl_sw_state = 2
                else:
                    sl_sw_state = 0
            # sl_sw_state == 2: latch, no change here
        trajectory.append(sl_sw_state)
    return trajectory


def simulate_virtual_trades(records, trajectory):
    """Ports SL_VirtualStep: DMONLY entries/reversals on dmt0, sideway
    (sw>=1) exits all and blocks entry, dm==3 exit-all when !sl_brk."""
    pos = None  # None=FLAT, 'LONG', 'SHORT'
    entry_px = 0.0
    trades = []
    for r, sw_state in zip(records, trajectory):
        sw = sw_state >= 1
        dmt0 = r["dmt0"]
        px = r["m5_close"]
        if dmt0 is None or px is None:
            continue
        act = 0
        if sw:
            if pos is not None: act = 7
        elif not r["brk"] and pos is not None and dmt0 == 3.0:
            act = 7
        elif pos == "LONG" and dmt0 in (2.0, 4.0):
            act = 5
        elif pos == "SHORT" and dmt0 in (1.0, 5.0):
            act = 6
        elif pos is None:
            if dmt0 in (1.0, 5.0): act = 3
            elif dmt0 in (2.0, 4.0): act = 4

        if act in (5, 6, 7):
            pnl = (px - entry_px) if pos == "LONG" else (entry_px - px)
            trades.append(pnl)
            pos = None
            continue
        if act in (3, 4):
            pos = "LONG" if act == 3 else "SHORT"
            entry_px = px

    total = sum(trades)
    wins = sum(1 for p in trades if p > 0)
    return dict(trade_count=len(trades), win_count=wins,
                win_rate=(wins / len(trades) * 100 if trades else 0.0),
                total_pnl=total)


def main():
    if len(sys.argv) != 2:
        print("usage: python ladder_breakout_variant_test.py <path-to-MT5-log>")
        sys.exit(1)
    path = sys.argv[1]

    records = parse_log(path)
    print(f"parsed {len(records)} M15 bars from {path}")
    if not records:
        print("no [LADDER]/[SWCMP] pairs found - wrong log or wrong encoding")
        sys.exit(1)

    # --- mandatory regression: current-rule replay must match the log ---
    traj_current = replay_state_machine(records, breakout_current)
    mismatches = [(i, r["bar"], r["sw_real"], s)
                  for i, (r, s) in enumerate(zip(records, traj_current))
                  if r["sw_real"] != s]
    print()
    print("=== REGRESSION: replay(current rule) vs logged sw:[N] ===")
    if not mismatches:
        print(f"MATCH: all {len(records)} bars reproduce the logged trajectory exactly.")
    else:
        print(f"MISMATCH at {len(mismatches)}/{len(records)} bars - "
              "DO NOT TRUST the proposed-rule numbers below until this is fixed.")
        for i, bar, real, replayed in mismatches[:10]:
            print(f"  bar {bar}: logged sw={real} replayed sw={replayed}")

    # --- current vs proposed breakout, same virtual-trade sim ---
    traj_proposed = replay_state_machine(records, breakout_proposed)

    def coverage(traj):
        bars = sum(1 for s in traj if s >= 1)
        ranges = 0
        prev = False
        for s in traj:
            on = s >= 1
            if on and not prev: ranges += 1
            prev = on
        return bars, ranges

    print()
    print("=== Sideway coverage: current vs proposed breakout ===")
    for name, traj in (("current  (raw30)", traj_current),
                        ("proposed (raw30 & (dmt1<3|fly))", traj_proposed)):
        bars, ranges = coverage(traj)
        print(f"{name:36s} bars={bars:4d} ({100*bars/len(traj):.1f}%)  ranges={ranges}")

    print()
    print("=== Virtual DMONLY trade P&L: current vs proposed breakout ===")
    for name, traj in (("current  (raw30)", traj_current),
                        ("proposed (raw30 & (dmt1<3|fly))", traj_proposed)):
        res = simulate_virtual_trades(records, traj)
        print(f"{name:36s} trades={res['trade_count']:4d}  win={res['win_rate']:5.1f}%  "
              f"total P&L={res['total_pnl']:+.2f}")

    print()
    print("Reference (from this log's own [SWCMP_SUMMARY], if present): "
          "grep it directly - USER hindsight-ceiling trades/win_rate/pnl "
          "are printed once at the end of the run.")


if __name__ == "__main__":
    main()
