#!/usr/bin/env python3
"""Revert Split — classify 152 M15_REVERT exits by the M15 state they reverted TO.

For each M15_REVERT exit:
  - UP trade (trigger F): reverted-to-R = TRUE REVERSAL; to-S/C = PAUSE-CUT.
  - DOWN trade (trigger R): reverted-to-F = TRUE REVERSAL; to-S/C = PAUSE-CUT.

Reports per class: n, total $, mean $, win-rate, PF.
Appends section to V36_13_DISSECTION.md.
"""

import json
import re
from datetime import datetime

JSON_PATH = "references/Backtest_data/V36.13/report_tables_clean.json"
LOG_PATH = "references/Backtest_data/V36.13/20260705_clean.log"
REPORT_PATH = "references/V36_13_DISSECTION.md"

# ── regexes ──────────────────────────────────────────────────────
ENTRY_RE = re.compile(
    r"\[TRADE\] evt:ENTRY dir:(UP|DOWN) dt:(\S+\s+\S+) "
    r"entry:(\S+) sl:(\S+) sldist:(\S+) tp:(\S+) tpdist:(\S+) rr:(\S+) "
    r"m30bbloc:(\d+) m15:(\S+) m30:(\S+) h1bbloc:(\d+) h4bbloc:(\d+)"
)
EXIT_RE = re.compile(
    r"\[TRADE\] evt:EXIT reason:(\S+) dt:(\S+\s+\S+) "
    r"exit:(\S+) bars_held:(\d+) m30_followed:(Y|N)"
)

# DUALTF regex that captures m15_state (field after m15:state:)
DUALTF_M15_RE = re.compile(
    r"\[DUALTF\].*?dt:(\S+\s+\S+).*?"
    r"m15:state:(\S+)"
)

# ── 1. Load deals ───────────────────────────────────────────────
with open(JSON_PATH) as f:
    data = json.load(f)

trade_deals = [d for d in data["table_deals"]
               if d["Type"] != "balance" and d["Direction"] in ("in", "out")]
in_deals = [d for d in trade_deals if d["Direction"] == "in"]
out_deals = [d for d in trade_deals if d["Direction"] == "out"]

per_trade = []
for i, (ind, outd) in enumerate(zip(in_deals, out_deals)):
    profit = float(outd["Profit"].replace(" ", ""))
    ind_time = datetime.strptime(ind["Time"], "%Y.%m.%d %H:%M:%S")
    outd_time = datetime.strptime(outd["Time"], "%Y.%m.%d %H:%M:%S")
    per_trade.append({
        "idx": i,
        "entry_time": ind_time,
        "exit_time": outd_time,
        "profit": profit,
    })

# ── 2. Parse log ENTRY / EXIT lines ─────────────────────────────
entry_log = []
exit_log = []
with open(LOG_PATH) as f:
    for line in f:
        m = ENTRY_RE.search(line)
        if m:
            entry_log.append({
                "dir": m.group(1),
                "dt": datetime.strptime(m.group(2), "%Y.%m.%d %H:%M:%S"),
            })
        m = EXIT_RE.search(line)
        if m:
            exit_log.append({
                "reason": m.group(1),
                "dt": datetime.strptime(m.group(2), "%Y.%m.%d %H:%M:%S"),
            })

# ── 3. Parse DUALTF for m15_state by timestamp ──────────────────
dt_to_m15 = {}
with open(LOG_PATH) as f:
    for line in f:
        m = DUALTF_M15_RE.search(line)
        if m:
            dt = datetime.strptime(m.group(1), "%Y.%m.%d %H:%M:%S")
            dt_to_m15[dt] = m.group(2)

# ── 4. Match trades to log lines ────────────────────────────────
used_entries = set()
for t in per_trade:
    best_ei = None
    best_ei_diff = None
    for ei, e in enumerate(entry_log):
        if ei in used_entries:
            continue
        diff = abs((t["entry_time"] - e["dt"]).total_seconds())
        if best_ei_diff is None or diff < best_ei_diff:
            best_ei = ei
            best_ei_diff = diff
    if best_ei is not None and best_ei_diff <= 600:
        t["entry_log"] = entry_log[best_ei]
        used_entries.add(best_ei)

for i, t in enumerate(per_trade):
    if i < len(exit_log):
        t["exit_log"] = exit_log[i]

# ── 5. Filter to M15_REVERT exits and classify ──────────────────
revert_trades = [
    t for t in per_trade
    if t.get("exit_log") and t["exit_log"]["reason"] == "M15_REVERT"
       and t.get("entry_log")
]

print(f"M15_REVERT exits found: {len(revert_trades)}")

classes = {"TRUE_REVERSAL": [], "PAUSE_CUT_S": [], "PAUSE_CUT_C": [], "STATE_UNCHANGED": [], "UNKNOWN": []}

for t in revert_trades:
    direction = t["entry_log"]["dir"]
    exit_dt = t["exit_log"]["dt"]

    # Find m15_state at the exit bar
    m15_state = dt_to_m15.get(exit_dt, None)

    if m15_state is None:
        # Fallback: search nearby bars (same minute, +/-15s)
        for delta in [-15, 15, -30, 30]:
            check_min = max(0, min(59, exit_dt.minute + delta))
            check_dt = exit_dt.replace(minute=check_min)
            m15_state = dt_to_m15.get(check_dt, None)
            if m15_state:
                break

    if m15_state is None:
        t["revert_class"] = "UNKNOWN"
        t["m15_exit_state"] = "MISSING"
        continue

    t["m15_exit_state"] = m15_state

    # Classify based on direction and reverted-to state
    if direction == "UP":
        # UP trade triggered by F; reverted to R = true reversal, to S/C = pause-cut,
        # to F = state unchanged (edge: exit fired but state same as entry)
        if m15_state == "R":
            t["revert_class"] = "TRUE_REVERSAL"
        elif m15_state == "S":
            t["revert_class"] = "PAUSE_CUT_S"
        elif m15_state == "C":
            t["revert_class"] = "PAUSE_CUT_C"
        elif m15_state == "F":
            t["revert_class"] = "STATE_UNCHANGED"
        else:
            t["revert_class"] = "UNKNOWN"
    else:
        # DOWN trade triggered by R; reverted to F = true reversal, to S/C = pause-cut,
        # to R = state unchanged (edge: exit fired but state same as entry)
        if m15_state == "F":
            t["revert_class"] = "TRUE_REVERSAL"
        elif m15_state == "S":
            t["revert_class"] = "PAUSE_CUT_S"
        elif m15_state == "C":
            t["revert_class"] = "PAUSE_CUT_C"
        elif m15_state == "R":
            t["revert_class"] = "STATE_UNCHANGED"
        else:
            t["revert_class"] = "UNKNOWN"

    classes[t["revert_class"]].append(t)

# ── 6. Compute stats per class ──────────────────────────────────
def class_stats(trades):
    n = len(trades)
    if n == 0:
        return {"n": 0, "total": 0.0, "mean": 0.0, "win_rate": 0.0, "pf": 0.0,
                "wins": 0, "losses": 0, "gp": 0.0, "gl": 0.0}
    gp = sum(t["profit"] for t in trades if t["profit"] > 0)
    gl = sum(abs(t["profit"]) for t in trades if t["profit"] < 0)
    wins = sum(1 for t in trades if t["profit"] > 0)
    losses = sum(1 for t in trades if t["profit"] < 0)
    pf = round(gp / gl, 2) if gl > 0 else ("inf" if gp > 0 else 0.0)
    wr = round(wins / n * 100, 1)
    total = round(gp - gl, 2)
    mean = round(total / n, 2)
    return {
        "n": n, "total": total, "mean": mean,
        "win_rate": wr, "pf": pf,
        "wins": wins, "losses": losses, "gp": gp, "gl": gl
    }

stats = {}
for cls_name, trades in classes.items():
    stats[cls_name] = class_stats(trades)

# Pause-cut totals
pause_cut_s_c = stats["PAUSE_CUT_S"]["n"] + stats["PAUSE_CUT_C"]["n"]
pause_cut_total = (stats["PAUSE_CUT_S"]["total"] + stats["PAUSE_CUT_C"]["total"])

# Percentage of M15_REVERT net loss by class
m15_revert_net_loss = sum(abs(t["profit"]) for t in revert_trades if t["profit"] < 0)
true_rev_loss_pct = round(stats["TRUE_REVERSAL"]["gl"] / m15_revert_net_loss * 100, 1) if m15_revert_net_loss > 0 else 0.0
pause_cut_loss_pct = round(
    (stats["PAUSE_CUT_S"]["gl"] + stats["PAUSE_CUT_C"]["gl"]) / m15_revert_net_loss * 100, 1
) if m15_revert_net_loss > 0 else 0.0

# Percentage by trade count
pause_cut_count_pct = round(pause_cut_s_c / len(revert_trades) * 100, 1) if len(revert_trades) > 0 else 0.0
true_rev_count_pct = round(stats["TRUE_REVERSAL"]["n"] / len(revert_trades) * 100, 1) if len(revert_trades) > 0 else 0.0

# ── 7. Verdict ──────────────────────────────────────────────────
# PAUSE-CUT DOMINANT if PAUSE_CUT (S+C) trades account for >= 60% of the M15_REVERT net loss
if pause_cut_loss_pct >= 60.0:
    verdict = "PAUSE-CUT DOMINANT"
    verdict_detail = (f"PAUSE_CUT (S+C) accounts for {pause_cut_loss_pct:.1f}% of M15_REVERT "
                      f"gross loss ({pause_cut_s_c} of {len(revert_trades)} trades, "
                      f"{pause_cut_count_pct:.1f}%)")
elif true_rev_loss_pct >= 60.0:
    verdict = "REVERSAL-JUSTIFIED"
    verdict_detail = (f"TRUE_REVERSAL accounts for {true_rev_loss_pct:.1f}% of M15_REVERT "
                      f"gross loss ({stats['TRUE_REVERSAL']['n']} of {len(revert_trades)} trades, "
                      f"{true_rev_count_pct:.1f}%)")
else:
    verdict = "MIXED"
    verdict_detail = (f"TRUE_REVERSAL: {true_rev_loss_pct:.1f}% of loss ({stats['TRUE_REVERSAL']['n']} trades), "
                      f"PAUSE_CUT: {pause_cut_loss_pct:.1f}% of loss ({pause_cut_s_c} trades), "
                      f"STATE_UNCHANGED: {stats['STATE_UNCHANGED']['n']} trades")

# ── 8. Print summary ────────────────────────────────────────────
print(f"\n{'='*60}")
print(f"M15_REVERT Revert-Split Analysis")
print(f"{'='*60}")
print(f"Total M15_REVERT exits: {len(revert_trades)}")
print(f"\nClass breakdown:")
for cls_name in ["TRUE_REVERSAL", "PAUSE_CUT_S", "PAUSE_CUT_C", "STATE_UNCHANGED", "UNKNOWN"]:
    s = stats[cls_name]
    pf_str = "inf" if s["pf"] == "inf" else f"{s['pf']:.2f}"
    print(f"  {cls_name}: n={s['n']}, total={s['total']:+.2f}, mean={s['mean']:+.2f}, "
          f"wr={s['win_rate']:.1f}%, PF={pf_str}")

print(f"\nPause-cut (S+C) count: {pause_cut_s_c} ({pause_cut_count_pct:.1f}%)")
print(f"True-reversal count: {stats['TRUE_REVERSAL']['n']} ({true_rev_count_pct:.1f}%)")
print(f"\nLoss concentration:")
print(f"  TRUE_REVERSAL: {true_rev_loss_pct:.1f}% of M15_REVERT gross loss")
print(f"  PAUSE_CUT:     {pause_cut_loss_pct:.1f}% of M15_REVERT gross loss")

print(f"\nVerdict: {verdict}")
print(f"  {verdict_detail}")

# ── 9. Append section to report ─────────────────────────────────
# Check if section already exists
with open(REPORT_PATH, "r", encoding="utf-8") as f:
    existing = f.read()

if "## M15_REVERT by reverted-to-state" in existing:
    print(f"\nSection already exists in {REPORT_PATH} — skipping append.")
else:
    md = []
    md.append("")
    md.append("## M15_REVERT by reverted-to-state")
    md.append("")
    md.append(
        "The 152 M15_REVERT exits classified by the M15 state at the exit bar.\n"
        "For an UP trade (trigger F): reverted-to-R = TRUE REVERSAL; to-S/C = PAUSE-CUT; to-F = STATE_UNCHANGED.\n"
        "For a DOWN trade (trigger R): reverted-to-F = TRUE REVERSAL; to-S/C = PAUSE-CUT; to-R = STATE_UNCHANGED.\n"
        "STATE_UNCHANGED: exit fired but m15_state at exit bar equals entry state — edge case, not reversal nor pause."
    )
    md.append("")
    md.append("### Class Table")
    md.append("")
    md.append("| Class | n | Total $ | Mean $ | Win-Rate | PF |")
    md.append("|-------|---|---------|--------|----------|-----|")

    for cls_name in ["TRUE_REVERSAL", "PAUSE_CUT_S", "PAUSE_CUT_C", "STATE_UNCHANGED"]:
        s = stats[cls_name]
        pf_str = "inf" if s["pf"] == "inf" else f"{s['pf']:.2f}"
        md.append(
            f"| {cls_name} | {s['n']} | {s['total']:+.2f} | {s['mean']:+.2f} "
            f"| {s['win_rate']:.1f}% | {pf_str} |"
        )

    if stats["UNKNOWN"]["n"] > 0:
        md.append(
            f"| UNKNOWN | {stats['UNKNOWN']['n']} | {stats['UNKNOWN']['total']:+.2f} "
            f"| {stats['UNKNOWN']['mean']:+.2f} | {stats['UNKNOWN']['win_rate']:.1f}% "
            f"| {stats['UNKNOWN']['pf']} |"
        )

    md.append("")
    md.append(f"**Total:** {len(revert_trades)} M15_REVERT exits classified.")
    md.append("")

    md.append("### Loss Concentration")
    md.append("")
    md.append(f"- TRUE_REVERSAL gross loss: **${stats['TRUE_REVERSAL']['gl']:.2f}** "
              f"({true_rev_loss_pct:.1f}% of M15_REVERT gross loss)")
    md.append(f"- PAUSE_CUT_S gross loss: **${stats['PAUSE_CUT_S']['gl']:.2f}**")
    md.append(f"- PAUSE_CUT_C gross loss: **${stats['PAUSE_CUT_C']['gl']:.2f}**")
    md.append(f"- PAUSE_CUT (S+C) combined gross loss: **${stats['PAUSE_CUT_S']['gl'] + stats['PAUSE_CUT_C']['gl']:.2f}** "
              f"({pause_cut_loss_pct:.1f}% of M15_REVERT gross loss)")
    if stats["STATE_UNCHANGED"]["n"] > 0:
        st_pct = round(stats["STATE_UNCHANGED"]["gl"] / m15_revert_net_loss * 100, 1) if m15_revert_net_loss > 0 else 0.0
        md.append(f"- STATE_UNCHANGED gross loss: **${stats['STATE_UNCHANGED']['gl']:.2f}** "
                  f"({st_pct:.1f}% of M15_REVERT gross loss, {stats['STATE_UNCHANGED']['n']} trades)")
    md.append("")

    # Find which class owns the most loss
    class_gl = {
        "TRUE_REVERSAL": stats["TRUE_REVERSAL"]["gl"],
        "PAUSE_CUT_S": stats["PAUSE_CUT_S"]["gl"],
        "PAUSE_CUT_C": stats["PAUSE_CUT_C"]["gl"],
        "PAUSE_CUT (S+C)": stats["PAUSE_CUT_S"]["gl"] + stats["PAUSE_CUT_C"]["gl"],
    }
    max_class = max(class_gl, key=lambda k: class_gl[k])
    max_pct = round(class_gl[max_class] / m15_revert_net_loss * 100, 1)
    md.append(f"**{max_class}** owns the most loss: ${class_gl[max_class]:.2f} ({max_pct:.1f}%).")
    md.append("")

    md.append("### Verdict")
    md.append("")
    md.append(f"**{verdict}**")
    md.append("")
    md.append(f"{verdict_detail}")
    md.append("")

    md.append("### Caveat — Counterfactual Unknowable, Realized-Only")
    md.append("")
    md.append(
        "- **Counterfactual unknowable:** Whether PAUSE-CUT trades would have recovered "
        "had the exit been held is unknowable from this data. The exit fired at the M15 "
        "state change; without the exit rule, price may have continued against the trade "
        "or recovered. We cannot simulate counterfactual outcomes here."
    )
    md.append(
        "- **Realized-only:** All figures below are realized profits/losses per the "
        "actual exit. The concentration of realized loss by class is informative — "
        "if PAUSE-CUT trades carry the bulk of the loss, loosening the exit (exit only "
        "on TRUE_REVERSAL) targets those trades. However, whether they would recover "
        "requires a backtest with the modified exit rule."
    )
    md.append("")

    with open(REPORT_PATH, "a", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")

    print(f"\nSection appended to {REPORT_PATH}")
