#!/usr/bin/env python3
"""Scenario-Cell Dissection — split 214 V36.13 trades into H4×H1 scenario cells.

Pre-registered bar: PF >= 1.2 at n >= 20. Reads existing data only.
Reuses the join logic from dissect_v36_13.py verbatim.
"""

import json
import re
from datetime import datetime
from collections import defaultdict

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

# DUALTF: captures dt, h4_state, h1_state
DUALTF_RE = re.compile(
    r"\[DUALTF\].*?dt:(\S+\s+\S+).*?"
    r"h4:state:(\S+).*?"
    r"h1:state:(\S+)"
)

# ── 1. Reconcile: join in-deal <-> out-deal (from dissect_v36_13.py) ──
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

total_profit = sum(t["profit"] for t in per_trade)

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

# ── 3. Parse DUALTF for h4_state, h1_state by timestamp ─────────
dt_to_h4h1 = {}
with open(LOG_PATH) as f:
    for line in f:
        m = DUALTF_RE.search(line)
        if m:
            dt = datetime.strptime(m.group(1), "%Y.%m.%d %H:%M:%S")
            dt_to_h4h1[dt] = (m.group(2), m.group(3))

# ── 4. Match per-trade to log lines (from dissect_v36_13.py) ─────
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

# Sequential exit matching
for i, t in enumerate(per_trade):
    if i < len(exit_log):
        t["exit_log"] = exit_log[i]

# ── 5. Lookup h4_state and h1_state at entry bar ────────────────
# Same M15-bar rounding fix as dissect_v36_13.py Split E
for t in per_trade:
    if not t.get("entry_log"):
        continue
    entry_dt = t["entry_log"]["dt"]
    # Round to nearest M15 bar
    rounded_dt = entry_dt.replace(second=0, microsecond=0)
    h4h1 = dt_to_h4h1.get(rounded_dt, None)
    if h4h1 is None:
        for delta in [-15, 15, -30, 30]:
            check_min = max(0, min(59, rounded_dt.minute + delta))
            check_dt = rounded_dt.replace(minute=check_min)
            h4h1 = dt_to_h4h1.get(check_dt, None)
            if h4h1:
                break
    if h4h1:
        t["h4_state"] = h4h1[0]
        t["h1_state"] = h4h1[1]
    else:
        t["h4_state"] = "X"
        t["h1_state"] = "X"

# ── 6. Assign to scenario cells ─────────────────────────────────
states = ["F", "S", "C", "R", "X"]
cells = {}
for h4 in states:
    for h1 in states:
        key = f"{h4}-{h1}"
        cells[key] = {"h4": h4, "h1": h1, "trades": []}

for t in per_trade:
    h4 = t.get("h4_state", "X")
    h1 = t.get("h1_state", "X")
    key = f"{h4}-{h1}"
    if key not in cells:
        cells[key] = {"h4": h4, "h1": h1, "trades": []}
    cells[key]["trades"].append(t)

# ── 7. Compute stats per cell ───────────────────────────────────
def cell_stats(trades):
    n = len(trades)
    if n == 0:
        return {"n": 0, "total": 0.0, "mean": 0.0, "win_rate": 0.0,
                "pf": 0.0, "wins": 0, "losses": 0, "gp": 0.0, "gl": 0.0}
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

cell_results = {}
for key, c in cells.items():
    cell_results[key] = cell_stats(c["trades"])

# ── 8. Sanity checks ────────────────────────────────────────────
sum_n = sum(v["n"] for v in cell_results.values())
sum_dollars = round(sum(v["total"] for v in cell_results.values()), 2)
sum_dollar_check = round(sum(v["gp"] - v["gl"] for v in cell_results.values()), 2)

print(f"Cell n sum: {sum_n} (expected 214)")
print(f"Cell $ sum: {sum_dollars} (expected {total_profit:.2f})")
print(f"Cell $ sum (via gp-gl): {sum_dollar_check} (expected {total_profit:.2f})")

if sum_n != 214:
    print(f"STOP: cell n sum {sum_n} != 214")
    exit(1)

delta = abs(sum_dollars - total_profit)
print(f"Reconciliation delta: {delta:.2f}")

# ── 9. Marginals ────────────────────────────────────────────────
marginal_h4 = defaultdict(list)
marginal_h1 = defaultdict(list)
for key, c in cells.items():
    marginal_h4[c["h4"]].extend(c["trades"])
    marginal_h1[c["h1"]].extend(c["trades"])

marginal_h4_stats = {h4: cell_stats(trades) for h4, trades in marginal_h4.items()}
marginal_h1_stats = {h1: cell_stats(trades) for h1, trades in marginal_h1.items()}

# ── 10. n-distribution ──────────────────────────────────────────
n_ge_20 = sum(1 for v in cell_results.values() if v["n"] >= 20)
n_10_19 = sum(1 for v in cell_results.values() if 10 <= v["n"] < 20)
n_lt_10 = sum(1 for v in cell_results.values() if 0 < v["n"] < 10)
n_zero = sum(1 for v in cell_results.values() if v["n"] == 0)

print(f"\nn-distribution: >=20: {n_ge_20}, 10-19: {n_10_19}, <10: {n_lt_10}, empty: {n_zero}")

# ── 11. Verdict ─────────────────────────────────────────────────
survivors = []
below_threshold = []
for key, st in cell_results.items():
    if st["n"] == 0:
        continue
    pf_ok = isinstance(st["pf"], (int, float)) and st["pf"] >= 1.2
    if pf_ok and st["n"] >= 20:
        survivors.append((key, st))
    elif pf_ok and st["n"] < 20:
        below_threshold.append((key, st))

if survivors:
    verdict = "SURVIVOR"
    verdict_detail = []
    for key, st in survivors:
        pf_str = "inf" if st["pf"] == "inf" else f"{st['pf']:.2f}"
        verdict_detail.append(
            f"Cell {key}: n={st['n']}, PF={pf_str}, total={st['total']:+.2f}, "
            f"WR={st['win_rate']:.1f}%"
        )
    verdict_detail.append(
        "in-sample, post-hoc, one of 16+ comparisons — a HYPOTHESIS "
        "requiring a forward test on a fresh data window before any rule "
        "is built on it."
    )
else:
    verdict = "NO-SURVIVOR"
    verdict_detail = [
        "Joint H4xH1 scenario cells do not rescue the M15 trigger. "
        "The scenario-specific claim is not supported at any viable sample size."
    ]

# ── 12. Print summary ───────────────────────────────────────────
print(f"\n{'='*60}")
print(f"Scenario-Cell Dissection — V36.13")
print(f"{'='*60}")
print(f"\nCell grid:")
for h4 in states:
    for h1 in states:
        key = f"{h4}-{h1}"
        st = cell_results[key]
        if st["n"] == 0:
            continue
        pf_str = "inf" if st["pf"] == "inf" else f"{st['pf']:.2f}"
        print(f"  {key}: n={st['n']}, total={st['total']:+.2f}, WR={st['win_rate']:.1f}%, PF={pf_str}")

print(f"\nVerdict: {verdict}")
for line in verdict_detail:
    print(f"  {line}")

if below_threshold:
    print(f"\nBelow-threshold (PF>=1.2 but n<20):")
    for key, st in below_threshold:
        pf_str = "inf" if st["pf"] == "inf" else f"{st['pf']:.2f}"
        print(f"  {key}: n={st['n']}, PF={pf_str}, total={st['total']:+.2f}")

# ── 13. Append section to report ────────────────────────────────
with open(REPORT_PATH, "r", encoding="utf-8") as f:
    existing = f.read()

if "## Scenario-cell dissection" in existing:
    print(f"\nSection already exists in {REPORT_PATH} — skipping append.")
else:
    md = []
    md.append("")
    md.append("## Scenario-cell dissection (H4 x H1 at entry)")
    md.append("")
    md.append(
        "The 214 reconciled trades split into joint scenario cells by "
        "H4 state x H1 state at the entry bar. Pre-registered bar: PF >= 1.2 at n >= 20."
    )
    md.append("")

    # Sanity
    md.append("### Sanity Reconciliation")
    md.append("")
    md.append(f"- Sum of cell n: **{sum_n}** (expected 214) — {'PASS' if sum_n == 214 else 'FAIL'}")
    md.append(f"- Sum of cell $: **{sum_dollars:+.2f}** (per-trade profit sum: {total_profit:+.2f}, delta: {delta:+.2f}) — "
              f"{'PASS' if delta < 1.0 else 'FAIL'}")
    md.append("")

    # n-distribution
    md.append("### n-Distribution Across Cells")
    md.append("")
    md.append(f"- n >= 20: **{n_ge_20}** cells")
    md.append(f"- n 10-19: **{n_10_19}** cells")
    md.append(f"- n < 10: **{n_lt_10}** cells")
    md.append(f"- empty: **{n_zero}** cells")
    md.append("")

    # Cell grid
    md.append("### Cell Grid (H4 x H1)")
    md.append("")
    md.append("| Cell | n | Total $ | Mean $ | Win-Rate | PF |")
    md.append("|------|---|---------|--------|----------|-----|")
    for h4 in states:
        for h1 in states:
            key = f"{h4}-{h1}"
            st = cell_results[key]
            if st["n"] == 0:
                continue
            pf_str = "inf" if st["pf"] == "inf" else f"{st['pf']:.2f}"
            md.append(
                f"| {key} | {st['n']} | {st['total']:+.2f} | {st['mean']:+.2f} "
                f"| {st['win_rate']:.1f}% | {pf_str} |"
            )
    md.append("")

    # Marginals
    md.append("### Marginals")
    md.append("")
    md.append("| H4 State | n | Total $ | Mean $ | Win-Rate | PF |")
    md.append("|----------|---|---------|--------|----------|-----|")
    for h4 in states:
        st = marginal_h4_stats.get(h4)
        if not st or st["n"] == 0:
            continue
        pf_str = "inf" if st["pf"] == "inf" else f"{st['pf']:.2f}"
        md.append(
            f"| {h4} | {st['n']} | {st['total']:+.2f} | {st['mean']:+.2f} "
            f"| {st['win_rate']:.1f}% | {pf_str} |"
        )
    md.append("")
    md.append("| H1 State | n | Total $ | Mean $ | Win-Rate | PF |")
    md.append("|----------|---|---------|--------|----------|-----|")
    for h1 in states:
        st = marginal_h1_stats.get(h1)
        if not st or st["n"] == 0:
            continue
        pf_str = "inf" if st["pf"] == "inf" else f"{st['pf']:.2f}"
        md.append(
            f"| {h1} | {st['n']} | {st['total']:+.2f} | {st['mean']:+.2f} "
            f"| {st['win_rate']:.1f}% | {pf_str} |"
        )
    md.append("")

    # Verdict
    md.append("### Verdict")
    md.append("")
    md.append(f"**{verdict}**")
    md.append("")
    for line in verdict_detail:
        md.append(line)
    md.append("")

    # Below-threshold
    if below_threshold:
        md.append("### Below-Threshold (PF >= 1.2 but n < 20 — not promoted)")
        md.append("")
        for key, st in below_threshold:
            pf_str = "inf" if st["pf"] == "inf" else f"{st['pf']:.2f}"
            md.append(f"- Cell {key}: n={st['n']}, PF={pf_str}, total={st['total']:+.2f} — too small to trade")
        md.append("")

    # Multiple comparisons note
    md.append("### Multiple-Comparisons Note")
    md.append("")
    md.append(
        "With 16+ cells and a 21% base win-rate, 1-2 cells are EXPECTED to look profitable by chance alone. "
        "Only the pre-registered bar (PF >= 1.2 at n >= 20) counts, and even a survivor is a hypothesis, "
        "not a validated edge."
    )
    md.append("")

    # Limitations
    md.append("### Limitations")
    md.append("")
    md.append("- **In-sample, post-hoc:** The cell with the best PF was selected from the same data it was evaluated on. Overfitting is possible. A forward test on a fresh data window is required before building any rule on a survivor cell.")
    md.append("- **X-cell handling:** X states (no real TF data at entry) form their own row/column in the grid. They are reported, not silently dropped, but carry no signal — they are no-data rows.")
    md.append("- **No new design recommendations:** The fixed verdict categories (SURVIVOR / NO-SURVIVOR) are the only conclusions drawn. No scenario-specific entry filter is proposed without a forward test.")
    md.append("")

    with open(REPORT_PATH, "a", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")

    print(f"\nSection appended to {REPORT_PATH}")
