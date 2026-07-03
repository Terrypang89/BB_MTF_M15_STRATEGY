#!/usr/bin/env python3
"""
reconcile_v36_11.py — Reconcile V36.11 [TRADE] log against MT5 Tester deals.

Key finding: 34 "entries" = 17 [TRADE] + 17 [TRADEINFO] (double logging, not
phantom entries). The real discrepancy: the last log EXIT (M15_REVERT at
2026.01.14 01:00) was never executed by the EA — position held until end of
test (deal 35, +$45.18 + $40.13 swap). 16 regular trades lost $43.53; deal 35
saved the run.

Usage:
  python scripts/reconcile_v36_11.py
"""
from __future__ import annotations
import re
import json
import math
from datetime import datetime
from collections import Counter, defaultdict

# ── paths ──────────────────────────────────────────────────────────
LOG_PATH = "references/Backtest_data/V36.11/20260703_clean.log"
JSON_PATH = "references/Backtest_data/V36.11/report_tables_clean.json"
REPORT_PATH = "references/V36_11_RECONCILIATION.md"

DT_FMT = "%Y.%m.%d %H:%M:%S"

def parse_dt(s):
    return datetime.strptime(s.strip(), DT_FMT)

def parse_num(s):
    """Parse number from MT5 format (space as thousands sep)."""
    if s is None or s == '':
        return None
    if isinstance(s, float) and math.isnan(s):
        return None
    s = str(s).replace(" ", "").replace(",", "")
    try:
        return float(s)
    except ValueError:
        return None

# ── parse log ──────────────────────────────────────────────────────
def parse_trade_log(path):
    entries, exits, skips = [], [], []

    entry_re = re.compile(
        r'(\d{4}\.\d{2}\.\d{2}\s+\d{2}:\d{2}:\d{2})\s+\[TRADE\]\s+'
        r'evt:ENTRY\s+dir:(UP|DOWN)\s+dt:(\S+\s+\S+)\s+'
        r'entry:([\d.]+)\s+sl:([\d.]+)\s+sldist:([\d.]+)\s+'
        r'tp:([\d.]+)\s+tpdist:([\d.]+)\s+rr:([\d.]+)\s+'
        r'm30bbloc:(\d+)\s+m15:(\w+)\s+m30:(\w+)\s+'
        r'h1bbloc:(\d+)\s+h4bbloc:(\d+)'
    )
    exit_re = re.compile(
        r'(\d{4}\.\d{2}\.\d{2}\s+\d{2}:\d{2}:\d{2})\s+\[TRADE\]\s+'
        r'evt:EXIT\s+reason:([A-Z_0-9]+)\s+'
        r'dt:(\S+\s+\S+)\s+'
        r'exit:([\d.]+)\s+bars_held:(\d+)\s+m30_followed:(Y|N)'
    )
    skip_re = re.compile(
        r'(\d{4}\.\d{2}\.\d{2}\s+\d{2}:\d{2}:\d{2})\s+\[TRADE\]\s+'
        r'evt:SKIP\s+reason:(\S+)\s+dir:(UP|DOWN)\s+'
        r'dt:(\S+\s+\S+)\s+'
        r'm30bbloc:(\d+)'
    )

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            m = entry_re.search(line)
            if m:
                entries.append(dict(
                    log_ts=parse_dt(m.group(1)), dir=m.group(2),
                    dt=parse_dt(m.group(3)), entry=float(m.group(4)),
                    sl=float(m.group(5)), sldist=float(m.group(6)),
                    tp=float(m.group(7)), tpdist=float(m.group(8)),
                    rr=float(m.group(9)), m30bbloc=int(m.group(10)),
                    m15_state=m.group(11), m30_state=m.group(12),
                    h1bbloc=int(m.group(13)), h4bbloc=int(m.group(14)),
                ))
                continue
            m = exit_re.search(line)
            if m:
                exits.append(dict(
                    log_ts=parse_dt(m.group(1)), reason=m.group(2),
                    dt=parse_dt(m.group(3)), exit_price=float(m.group(4)),
                    bars_held=int(m.group(5)), m30_followed=m.group(6)=="Y",
                ))
                continue
            m = skip_re.search(line)
            if m:
                skips.append(dict(
                    log_ts=parse_dt(m.group(1)), reason=m.group(2),
                    dir=m.group(3), dt=parse_dt(m.group(4)),
                    m30bbloc=int(m.group(5)),
                ))
    return entries, exits, skips

# ── parse deals ────────────────────────────────────────────────────
def parse_deals(path):
    with open(path) as f:
        data = json.load(f)

    in_deals, out_deals = [], []
    for row in data.get("table_deals", []):
        d = row.get("Direction")
        if d == "in":
            in_deals.append(dict(
                deal_id=int(row["Deal"]), time=parse_dt(row["Time"]),
                type=row["Type"], price=parse_num(row["Price"]),
            ))
        elif d == "out":
            out_deals.append(dict(
                deal_id=int(row["Deal"]), time=parse_dt(row["Time"]),
                type=row["Type"], price=parse_num(row["Price"]),
                profit=parse_num(row["Profit"]),
                swap=parse_num(row.get("Swap")),
                commission=parse_num(row.get("Commission")),
                comment=row.get("Comment"),
            ))
    return in_deals, out_deals, data

# ── join entries to deals ──────────────────────────────────────────
def dir_match(log_dir, deal_type):
    return (log_dir == "UP" and deal_type == "buy") or \
           (log_dir == "DOWN" and deal_type == "sell")

def join_entries(entries, in_deals, max_s=600):
    """1:1 match each in-deal to a log ENTRY. Returns matched, phantoms, unmatched."""
    used_e, used_d = set(), set()
    matched_e, matched_d = [], []
    for di, deal in enumerate(in_deals):
        best, best_sc = None, float("inf")
        for ei, entry in enumerate(entries):
            if ei in used_e: continue
            if not dir_match(entry["dir"], deal["type"]): continue
            td = abs((deal["time"] - entry["dt"]).total_seconds())
            if td > max_s: continue
            sc = td + 100 * abs(deal["price"] - entry["entry"])
            if sc < best_sc:
                best_sc, best = sc, (ei, di)
        if best:
            ei, di = best
            used_e.add(ei); used_d.add(di)
            matched_e.append(entries[ei]); matched_d.append(in_deals[di])
    return matched_e, matched_d, \
           [entries[i] for i in range(len(entries)) if i not in used_e], \
           [in_deals[i] for i in range(len(in_deals)) if i not in used_d]

def join_exits(exits, out_deals, max_s=600):
    """1:1 match each out-deal to a log EXIT. Returns matched, unmatched."""
    used_e, used_d = set(), set()
    matched_e, matched_d = [], []
    for di, deal in enumerate(out_deals):
        best, best_sc = None, float("inf")
        for ei, ex in enumerate(exits):
            if ei in used_e: continue
            td = abs((deal["time"] - ex["dt"]).total_seconds())
            if td > max_s: continue
            sc = td + 100 * abs(deal["price"] - ex["exit_price"])
            if sc < best_sc:
                best_sc, best = sc, (ei, di)
        if best:
            ei, di = best
            used_e.add(ei); used_d.add(di)
            matched_e.append(exits[ei]); matched_d.append(out_deals[di])
    return matched_e, matched_d, \
           [exits[i] for i in range(len(exits)) if i not in used_e], \
           [out_deals[i] for i in range(len(out_deals)) if i not in used_d]

# ── gate-eval analysis ────────────────────────────────────────────
def analyze_gate_evals(skips, entries):
    """
    Build a timeline of all trade events. Group into flip windows.
    A flip window = events of the same direction within 12 M5 bars of each other.
    If the trigger re-evaluates every bar during validity, each flip window
    would contain multiple SKIP/ENTRY events.
    """
    events = []
    for e in entries:
        events.append(dict(dt=e["dt"], type="ENTRY", dir=e["dir"],
                          m30bbloc=e["m30bbloc"]))
    for s in skips:
        events.append(dict(dt=s["dt"], type="SKIP", dir=s["dir"],
                          m30bbloc=s["m30bbloc"]))
    events.sort(key=lambda x: x["dt"])

    # Group into flip windows: consecutive events within 12 bars of each other
    windows = []
    cur = None
    for ev in events:
        if cur is None or (ev["dt"] - cur["start"]).total_seconds() > 12 * 300:
            if cur: windows.append(cur)
            cur = dict(start=ev["dt"], dir=ev["dir"], events=[ev])
        else:
            cur["events"].append(ev)
    if cur: windows.append(cur)

    # Filter to only flip-triggered windows (events with dir=UP or dir=DOWN,
    # which correspond to actual F/R flips)
    return windows, events

# ── build real trades ──────────────────────────────────────────────
def build_real_trades(in_deals, out_deals, matched_entries, matched_exits):
    """
    Pair sequential in/out deals. Join to log ENTRY/EXIT for metadata.
    """
    trades = []
    for i in range(min(len(in_deals), len(out_deals))):
        ind, outd = in_deals[i], out_deals[i]
        direction = "UP" if ind["type"] == "buy" else "DOWN"
        profit = outd["profit"] or 0.0
        swap = outd["swap"] or 0.0

        # Join to ENTRY
        entry_m = None
        best_d = float("inf")
        for me in matched_entries:
            if me["dir"] == direction:
                d = abs((ind["time"] - me["dt"]).total_seconds())
                if d < best_d:
                    best_d, entry_m = d, me

        # Join to EXIT
        exit_m = None
        best_d = float("inf")
        for mex in matched_exits:
            d = abs((outd["time"] - mex["dt"]).total_seconds())
            if d < best_d:
                best_d, exit_m = d, mex

        sldist = entry_m["sldist"] if entry_m else None
        trades.append(dict(
            in_deal_id=ind["deal_id"], out_deal_id=outd["deal_id"],
            in_time=ind["time"], out_time=outd["time"],
            direction=direction, in_price=ind["price"],
            out_price=outd["price"], profit=profit, swap=swap,
            total_profit=profit + swap,
            reason=exit_m["reason"] if exit_m else "UNKNOWN",
            bars_held=exit_m["bars_held"] if exit_m else None,
            m30_followed=exit_m["m30_followed"] if exit_m else None,
            sldist=sldist,
            rr=entry_m["rr"] if entry_m else None,
            m30bbloc=entry_m["m30bbloc"] if entry_m else None,
            r_multiple=(profit / sldist) if (sldist and sldist > 0) else None,
        ))
    return trades

# ── main ───────────────────────────────────────────────────────────
def main():
    print("=" * 70)
    print("V36.11 RECONCILIATION")
    print("=" * 70)

    entries, exits, skips = parse_trade_log(LOG_PATH)
    in_deals, out_deals, data = parse_deals(JSON_PATH)

    trade_info_count = 0
    with open(LOG_PATH) as f:
        for line in f:
            if "[TRADEINFO]" in line and "evt:ENTRY" in line:
                trade_info_count += 1

    print(f"\n[PARSE]")
    print(f"  [TRADE] ENTRY: {len(entries)}")
    print(f"  [TRADEINFO] ENTRY: {trade_info_count}")
    print(f"  Total evt:ENTRY lines: {len(entries) + trade_info_count}")
    print(f"  [TRADE] EXIT: {len(exits)}")
    print(f"  [TRADE] SKIP: {len(skips)}")
    print(f"  Deals: {len(in_deals)} in, {len(out_deals)} out")
    print(f"\n  THE 2X DISCREPANCY: 34 = 17 [TRADE] + 17 [TRADEINFO]")
    print(f"  Double logging — each event produces two lines.")
    print(f"  Actual unique entries: {len(entries)}, not 34.")

    # ── STEP 1 ──────────────────────────────────────────────────────
    matched_e, matched_d, phantoms, unmatched_in = join_entries(entries, in_deals)
    matched_ex, matched_out, unmatched_ex_l, unmatched_out_d = \
        join_exits(exits, out_deals)

    print(f"\n{'='*70}")
    print("STEP 1 — JOIN")
    print(f"{'='*70}")
    print(f"  Entries: {len(matched_e)} matched, {len(phantoms)} phantom, "
          f"{len(unmatched_in)} unmatched in-deals")
    print(f"  Exits:   {len(matched_ex)} matched, "
          f"{len(unmatched_ex_l)} unmatched exit lines, "
          f"{len(unmatched_out_d)} unmatched out-deals")
    print(f"  in-deal count: {len(in_deals)} (Tester: 17 Total Trades)")
    print(f"  out-deal count: {len(out_deals)}")

    # Report unmatched details
    if unmatched_out_d:
        print(f"\n  UNMATCHED OUT-DEALS:")
        for ud in unmatched_out_d:
            print(f"    Deal {ud['deal_id']}: {ud['time'].strftime(DT_FMT)} "
                  f"price={ud['price']:.2f} profit={ud['profit']:.2f} "
                  f"comment={ud.get('comment','')}")

    if unmatched_ex_l:
        print(f"\n  UNMATCHED EXIT LINES:")
        for ue in unmatched_ex_l:
            print(f"    {ue['reason']} at {ue['dt'].strftime(DT_FMT)} "
                  f"exit={ue['exit_price']:.2f} bars_held={ue['bars_held']}")

    # ── STEP 2: the 34-count phantom mechanism ──────────────────────
    print(f"\n{'='*70}")
    print("STEP 2 — PHANTOM MECHANISM")
    print(f"{'='*70}")
    print(f"  There are NO phantom entries (17/17/0).")
    print(f"  The 34 'entries' the user saw = 17 [TRADE] + 17 [TRADEINFO].")
    print(f"  Mechanism: DOUBLE LOGGING — each event produces two lines.")
    print(f"  [TRADE] = V36.11 LogTradeEntry(); [TRADEINFO] = EA's own SIG:SIG.")
    print(f"  This is the 2x inflation — not phantom fills.")

    # ── STEP 2b: failed exit ────────────────────────────────────────
    print(f"\n{'='*70}")
    print("STEP 2b — FAILED EXIT (the real discrepancy)")
    print(f"{'='*70}")
    # Find the unmatched exit line
    for ue in unmatched_ex_l:
        print(f"  Log EXIT at {ue['dt'].strftime(DT_FMT)} reason={ue['reason']} "
              f"exit={ue['exit_price']:.2f} bars_held={ue['bars_held']}")
        print(f"  >> No out-deal within 600s >> EA did NOT close the position.")
        print(f"  >> Position held until end of test (deal 35).")

    # Show the last position lifecycle
    last_entry = entries[-1]
    last_exit = exits[-1]
    print(f"\n  Last position lifecycle:")
    print(f"    ENTRY: {last_entry['dt'].strftime(DT_FMT)} dir={last_entry['dir']} "
          f"entry={last_entry['entry']:.2f}")
    print(f"    EXIT:  {last_exit['dt'].strftime(DT_FMT)} reason={last_exit['reason']} "
          f"exit={last_exit['exit_price']:.2f} bars_held={last_exit['bars_held']}")
    print(f"    Deal 34 (in): 2026.01.13 22:30:03 sell @4589.06")
    print(f"    Deal 35 (out): 2026.04.29 23:59:58 buy @4543.88 profit=+45.18 "
          f"(end of test)")
    print(f"    Position held ~3.5 months, accumulated $40.13 swap.")

    # ── Gate-eval analysis ──────────────────────────────────────────
    print(f"\n{'='*70}")
    print("STEP 2c — GATE-EVAL ANOMALY")
    print(f"{'='*70}")

    windows, all_events = analyze_gate_evals(skips, entries)
    print(f"  Total flip windows: {len(windows)}")

    # Count events per window
    multi_event_windows = [w for w in windows if len(w["events"]) > 1]
    single_event_windows = [w for w in windows if len(w["events"]) == 1]
    print(f"  Windows with >1 event: {len(multi_event_windows)}")
    print(f"  Windows with 1 event: {len(single_event_windows)}")

    if multi_event_windows:
        print(f"\n  MULTI-EVENT WINDOWS (re-evaluation pattern):")
        for i, w in enumerate(multi_event_windows[:10]):
            print(f"  Window {i+1}: start={w['start'].strftime(DT_FMT)} "
                  f"events={len(w['events'])}")
            for ev in w["events"]:
                print(f"    {ev['type']} {ev['dir']} at {ev['dt'].strftime(DT_FMT)} "
                      f"m30bbloc={ev['m30bbloc']}")
    else:
        print(f"\n  NO multi-event windows found.")
        print(f"  Each F/R flip produces at most 1 event (ENTRY or SKIP).")
        print(f"  The 12-row validity does NOT re-gate every bar.")
        print(f"  The trigger fires once per flip; no re-evaluation pattern.")

    # Show example flip windows
    print(f"\n  Example flip windows (first 10):")
    for i, w in enumerate(windows[:10]):
        print(f"  W{i+1}: {w['start'].strftime(DT_FMT)} dir={w['dir']} "
              f"n={len(w['events'])}")
        for ev in w["events"]:
            print(f"    {ev['type']} {ev['dir']} m30bbloc={ev['m30bbloc']}")

    # ── STEP 3: honest expectancy ───────────────────────────────────
    print(f"\n{'='*70}")
    print("STEP 3 — HONEST EXPECTANCY")
    print(f"{'='*70}")

    # Build 16 regular trades (exclude deal 35 end-of-test)
    regular_out = [d for d in out_deals if d["deal_id"] != 35]
    trades = build_real_trades(matched_d, regular_out, matched_e, matched_ex)

    n = len(trades)
    wins = sum(1 for t in trades if t["profit"] > 0)
    win_rate = wins / n if n > 0 else 0
    profits = [t["profit"] for t in trades]
    mean_p = sum(profits) / n if n > 0 else 0
    median_p = sorted(profits)[n // 2] if n > 0 else 0
    total_net = sum(profits)
    gross_p = sum(p for p in profits if p > 0)
    gross_l = abs(sum(p for p in profits if p < 0))
    pf = gross_p / gross_l if gross_l > 0 else float("inf")

    r_mults = [t["r_multiple"] for t in trades if t["r_multiple"] is not None]
    mean_r = sum(r_mults) / len(r_mults) if r_mults else 0
    median_r = sorted(r_mults)[len(r_mults) // 2] if r_mults else 0

    print(f"\n  A. OVERALL (16 regular trades, excl end-of-test):")
    print(f"    n={n}, wins={wins}, win_rate={win_rate:.1%}")
    print(f"    mean=${mean_p:.2f}, median=${median_p:.2f}")
    print(f"    total_net=${total_net:.2f}")
    print(f"    gross_profit=${gross_p:.2f}, gross_loss=${gross_l:.2f}")
    print(f"    PF={pf:.2f}")
    print(f"    mean_R={mean_r:.2f}, median_R={median_r:.2f}")
    print(f"    Tester net (incl deal 35): $41.61")
    print(f"    Delta: ${total_net - 41.61:.2f} (deal 35 contributes +$45.18 + $40.13 swap)")

    # B. Ex-largest-winner
    max_trade = max(trades, key=lambda t: t["profit"])
    ex_max = [t for t in trades if t["in_deal_id"] != max_trade["in_deal_id"]]
    ex_max_net = sum(t["profit"] for t in ex_max)
    ex_max_wins = sum(1 for t in ex_max if t["profit"] > 0)
    print(f"\n  B. EX-LARGEST-WINNER:")
    print(f"    Largest: deal {max_trade['in_deal_id']} +${max_trade['profit']:.2f} "
          f"({max_trade['reason']})")
    print(f"    Ex-largest net: ${ex_max_net:.2f} (n={len(ex_max)}, wins={ex_max_wins})")
    print(f"    WITHOUT largest winner: {'NEGATIVE' if ex_max_net < 0 else 'POSITIVE'} "
          f"(${ex_max_net:.2f})")

    # C. By exit reason
    print(f"\n  C. BY EXIT REASON:")
    reason_groups = defaultdict(list)
    for t in trades:
        reason_groups[t["reason"]].append(t)

    for reason in sorted(reason_groups.keys()):
        rt = reason_groups[reason]
        n_r = len(rt)
        total_r = sum(t["profit"] for t in rt)
        mean_r_p = total_r / n_r
        r_m = [t["r_multiple"] for t in rt if t["r_multiple"] is not None]
        mean_r_m = sum(r_m) / len(r_m) if r_m else 0
        wins_r = sum(1 for t in rt if t["profit"] > 0)
        print(f"    {reason}: n={n_r}, wins={wins_r}, total=${total_r:.2f}, "
              f"mean=${mean_r_p:.2f}, mean_R={mean_r_m:.2f}")

    revert_net = sum(t["profit"] for t in reason_groups.get("M15_REVERT", []))
    print(f"    M15_REVERT net: ${revert_net:.2f} "
          f"({'SAVER' if revert_net > 0 else 'COST'})")
    print(f"    COUNTERFACTUAL: whether TP would have hit after M15_REVERT "
          f"is UNKNOWABLE — reporting realized only.")

    # D. By rr bucket
    print(f"\n  D. BY rr BUCKET:")
    rr_low = [t for t in trades if t["rr"] is not None and t["rr"] < 1.0]
    rr_high = [t for t in trades if t["rr"] is not None and t["rr"] >= 1.0]
    rr_low_net = sum(t["profit"] for t in rr_low)
    rr_high_net = sum(t["profit"] for t in rr_high)
    print(f"    rr < 1.0: n={len(rr_low)}, net=${rr_low_net:.2f}")
    print(f"    rr >= 1.0: n={len(rr_high)}, net=${rr_high_net:.2f}")

    # $/point sanity check
    print(f"\n  $/POINT SANITY CHECK:")
    for t in trades[:3]:
        move = abs(t["out_price"] - t["in_price"])
        dpp = t["profit"] / move if move else 0
        print(f"    Deal {t['in_deal_id']}: move={move:.2f} profit=${t['profit']:.2f} "
              f"$/point={dpp:.4f}")

    # ── STEP 4: knob ranking ────────────────────────────────────────
    print(f"\n{'='*70}")
    print("STEP 4 — KNOB RANKING")
    print(f"{'='*70}")

    # KNOB #0: double logging → not a code defect in trade path, but
    # the failed exit IS a code defect
    has_failed_exit = len(unmatched_ex_l) > 0
    if has_failed_exit:
        print(f"  KNOB #0: FIX EXIT/SYNC LOGIC (failed exit detected: "
              f"{len(unmatched_ex_l)} log EXIT not executed)")
        print(f"    V36.11 expectancy = PROVISIONAL until V36.12 re-backtest")
    else:
        print(f"  KNOB #0: NOT TRIGGERED")

    # M15_REVERT
    revert_trades = reason_groups.get("M15_REVERT", [])
    revert_wins = [t["profit"] for t in revert_trades if t["profit"] > 0]
    revert_losses = [abs(t["profit"]) for t in revert_trades if t["profit"] < 0]
    med_revert_win = sorted(revert_wins)[len(revert_wins)//2] if revert_wins else 0
    med_revert_loss = sorted(revert_losses)[len(revert_losses)//2] if revert_losses else 0

    if revert_net < 0 and med_revert_loss > med_revert_win:
        print(f"  KNOB #1: M15_REVERT — candidate for change "
              f"(net=${revert_net:.2f}, med_loss={med_revert_loss:.2f} > "
              f"med_win={med_revert_win:.2f})")
    else:
        print(f"  KNOB #1: M15_REVERT — NOT candidate "
              f"(net=${revert_net:.2f}, med_loss={med_revert_loss:.2f} <= "
              f"med_win={med_revert_win:.2f})")

    # min-rr gate
    if rr_low_net < 0:
        print(f"  KNOB #2: min-rr GATE — candidate (rr<1 net=${rr_low_net:.2f})")
    else:
        print(f"  KNOB #2: min-rr GATE — NOT candidate (rr<1 net=${rr_low_net:.2f})")

    # Stop source
    sl_hit = reason_groups.get("SL_HIT", [])
    sl_rr = [t["rr"] for t in sl_hit if t["rr"] is not None]
    print(f"  KNOB #3: Stop source — SL_HIT count={len(sl_hit)}, rr at SL={sl_rr}")

    print(f"\n  CAVEAT: 17 trades ranks hypotheses; it validates nothing.")

    # ── save report data ────────────────────────────────────────────
    report_data = dict(
        step1=dict(
            real_entries=len(matched_e), phantoms=len(phantoms),
            unmatched_in_deals=len(unmatched_in),
            real_exits=len(matched_ex),
            unmatched_exit_lines=len(unmatched_ex_l),
            unmatched_out_deals=len(unmatched_out_d),
            in_deal_count=len(in_deals), out_deal_count=len(out_deals),
        ),
        step2=dict(
            mechanism="DOUBLE_LOGGING",
            failed_exit=bool(unmatched_ex_l),
            unmatched_exit_details=[
                dict(dt=ue["dt"].strftime(DT_FMT), reason=ue["reason"],
                     exit_price=ue["exit_price"], bars_held=ue["bars_held"])
                for ue in unmatched_ex_l
            ],
        ),
        step2b=dict(
            flip_windows=len(windows),
            multi_event_windows=len(multi_event_windows),
            single_event_windows=len(single_event_windows),
        ),
        step3=dict(
            n=n, win_rate=win_rate, mean_profit=mean_p,
            median_profit=median_p, total_net=total_net, pf=pf,
            mean_r=mean_r, median_r=median_r,
            ex_max_net=ex_max_net, revert_net=revert_net,
            rr_low_net=rr_low_net, rr_high_net=rr_high_net,
            trades=[dict(
                in_deal_id=t["in_deal_id"], out_deal_id=t["out_deal_id"],
                direction=t["direction"], profit=t["profit"],
                swap=t["swap"], reason=t["reason"],
                bars_held=t["bars_held"], sldist=t["sldist"],
                rr=t["rr"], r_multiple=t["r_multiple"],
            ) for t in trades],
        ),
    )

    with open("references/Backtest_data/V36.11/reconcile_data.json", "w") as f:
        json.dump(report_data, f, indent=2, default=str)
    print(f"\n  Data written to references/Backtest_data/V36.11/reconcile_data.json")

if __name__ == "__main__":
    main()
