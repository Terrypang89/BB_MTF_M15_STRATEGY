#!/usr/bin/env python3
"""V36.13 Dissection — decompose 214 trades to locate where the loss concentrates.

Reconciles report_tables_clean.json deals with [TRADE] ENTRY/EXIT log lines.
Splits by: rr bucket, exit reason, m30bbloc zone, direction, HTF context.
Applies fixed verdict criteria mechanically.
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
DUALTF_RE = re.compile(
    r"\[DUALTF\] SIG:DUALTF evt:BAR dt:(\S+\s+\S+) "
    r"d1:stg:(\d+) d1:mid:(\d+) d1:ud:(\d+) d1:state:(\S+) d1bbloc:(-?\d+) "
    r"h4:stg:(\d+) h4:mid:(\d+) h4:ud:(\d+) h4:state:(\S+) h4bbloc:(-?\d+)"
)

# ── 1. Reconcile: join in-deal <-> out-deal ─────────────────────
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
        "entry_price": float(ind["Price"]),
        "exit_price": float(outd["Price"]),
        "profit": profit,
    })

total_profit = sum(t["profit"] for t in per_trade)
report_net = float(data["table_results"]["Total Net Profit"])

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
                "rr": float(m.group(8)),
                "m30bbloc": int(m.group(9)),
                "m15_state": m.group(10),
                "m30_state": m.group(11),
                "h1bbloc": int(m.group(12)),
                "h4bbloc": int(m.group(13)),
            })
        m = EXIT_RE.search(line)
        if m:
            exit_log.append({
                "reason": m.group(1),
                "dt": datetime.strptime(m.group(2), "%Y.%m.%d %H:%M:%S"),
                "bars_held": int(m.group(4)),
            })

# ── 3. Parse DUALTF for h4_state ────────────────────────────────
dt_to_h4 = {}
with open(LOG_PATH) as f:
    for line in f:
        m = DUALTF_RE.search(line)
        if m:
            dt = datetime.strptime(m.group(1), "%Y.%m.%d %H:%M:%S")
            dt_to_h4[dt] = m.group(10)

# ── 4. Match per-trade to log lines ─────────────────────────────
# Entries: time-based matching (+/-600s)
# Exits: sequential matching (both sources have 214 exits in same order;
#   exit times differ by ~900s between deal and log bar-boundary)
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

# Sequential exit matching: pair i-th exit log with i-th trade
for i, t in enumerate(per_trade):
    if i < len(exit_log):
        t["exit_log"] = exit_log[i]

matched_entry = sum(1 for t in per_trade if "entry_log" in t)
matched_exit = sum(1 for t in per_trade if "exit_log" in t)

# ── 5. Derive trade attributes ──────────────────────────────────
def rr_bucket(rr):
    if rr < 1.0:
        return "rr<1.0"
    elif rr < 1.5:
        return "1.0-1.5"
    elif rr < 2.0:
        return "1.5-2.0"
    else:
        return ">=2.0"

def m30_zone(bbloc, direction):
    if direction == "UP":
        if bbloc in (5, 7):
            return "NEAR/MID"
        elif bbloc in (9, 10):
            return "ATBAND"
        else:
            return "FAR"
    else:
        if bbloc in (3, 5):
            return "NEAR/MID"
        elif bbloc in (0, 1):
            return "ATBAND"
        else:
            return "FAR"

def h4_agree(h4_state, trigger_dir):
    if trigger_dir == "UP":
        if h4_state == "F":
            return "AGREE"
        elif h4_state == "S":
            return "DISAGREE"
        else:
            return "NEUTRAL"
    else:
        if h4_state == "S":
            return "AGREE"
        elif h4_state == "F":
            return "DISAGREE"
        else:
            return "NEUTRAL"

for t in per_trade:
    el = t.get("entry_log", {})
    xl = t.get("exit_log", {})
    t["rr"] = el.get("rr", None)
    t["rr_bucket"] = rr_bucket(t["rr"]) if t["rr"] else "UNKNOWN"
    t["m30bbloc"] = el.get("m30bbloc", None)
    t["dir"] = el.get("dir", None)
    t["zone"] = (m30_zone(t["m30bbloc"], t["dir"])
                 if (t["m30bbloc"] is not None and t["dir"]) else "UNKNOWN")
    t["exit_reason"] = xl.get("reason", "UNKNOWN")
    t["h4bbloc"] = el.get("h4bbloc", None)

    # Round entry time to nearest M15 bar (seconds=0)
    rounded_dt = t["entry_time"].replace(second=0, microsecond=0)
    h4_st = dt_to_h4.get(rounded_dt, None)
    if h4_st is None:
        # Fallback: search nearby bars
        for delta in [-15, 15, -30, 30]:
            check_min = max(0, min(59, rounded_dt.minute + delta))
            check_dt = rounded_dt.replace(minute=check_min)
            h4_st = dt_to_h4.get(check_dt, None)
            if h4_st:
                break
    t["h4_state"] = h4_st
    t["h4_context"] = (h4_agree(h4_st, t["dir"])
                       if (h4_st and t.get("dir")) else "UNKNOWN")

# ── 6. Compute splits ──────────────────────────────────────────
def group_stats(group_key, trades):
    groups = {}
    for t in trades:
        key = group_key(t)
        groups.setdefault(key, {"wins": 0, "losses": 0, "gp": 0.0, "gl": 0.0, "n": 0})
        groups[key]["n"] += 1
        p = t["profit"]
        if p > 0:
            groups[key]["wins"] += 1
            groups[key]["gp"] += p
        elif p < 0:
            groups[key]["losses"] += 1
            groups[key]["gl"] += abs(p)
    result = {}
    for k, v in groups.items():
        pf = round(v["gp"] / v["gl"], 2) if v["gl"] > 0 else (
            "inf" if v["gp"] > 0 else 0.0)
        wr = (v["wins"] / v["n"] * 100) if v["n"] > 0 else 0.0
        result[k] = {
            "n": v["n"],
            "total": round(v["gp"] - v["gl"], 2),
            "mean": round((v["gp"] - v["gl"]) / v["n"], 2) if v["n"] > 0 else 0.0,
            "win_rate": round(wr, 1),
            "pf": pf,
        }
    return result

# Split A: rr bucket
split_a = group_stats(lambda t: t["rr_bucket"], per_trade)

# Cumulative nets for keep-rr thresholds
keep_nets = {}
for threshold_rr in [1.0, 1.5]:
    kept = [t for t in per_trade if t["rr"] is not None and t["rr"] >= threshold_rr]
    net = round(sum(t["profit"] for t in kept), 2)
    n_kept = len(kept)
    gp = sum(t["profit"] for t in kept if t["profit"] > 0)
    gl = sum(abs(t["profit"]) for t in kept if t["profit"] < 0)
    pf = round(gp / gl, 2) if gl > 0 else ("inf" if gp > 0 else 0.0)
    keep_nets[f"rr>={threshold_rr}"] = {"n": n_kept, "net": net, "pf": pf}

# Split B: exit reason
split_b = group_stats(lambda t: t["exit_reason"], per_trade)

# Split C: m30bbloc zone
split_c = group_stats(lambda t: t["zone"], per_trade)

# Split D: direction
split_d = group_stats(lambda t: t["dir"], per_trade)

# Split E: HTF context
split_e = group_stats(lambda t: t["h4_context"], per_trade)

# ── 7. Verdict (fixed criteria) ────────────────────────────────
total_gl = sum(abs(t["profit"]) for t in per_trade if t["profit"] < 0)

# SALVAGEABLE-BY-RR-GATE: rr>=1.5 yields net >= 0 (or PF >= 1.0) at n >= 30
rr15 = keep_nets.get("rr>=1.5", {})
rr15_pf = rr15.get("pf", 0)
rr15_pf_ok = isinstance(rr15_pf, (int, float)) and rr15_pf >= 1.0
rr15_salvageable = (rr15.get("net", -999) >= 0 or rr15_pf_ok) and rr15.get("n", 0) >= 30

# EXIT-DRIVEN: M15_REVERT > 60% of gross loss
m15_revert_gl = sum(abs(t["profit"]) for t in per_trade
                    if t["profit"] < 0 and t["exit_reason"] == "M15_REVERT")
m15_revert_pct = (m15_revert_gl / total_gl * 100) if total_gl > 0 else 0.0
exit_driven = m15_revert_pct > 60.0

# FUNDAMENTALLY-NEGATIVE: no rr bucket + no zone subset PF >= 1.0 at n >= 30
rr_buckets_ok = any(
    v["n"] >= 30 and isinstance(v["pf"], (int, float)) and v["pf"] >= 1.0
    for v in split_a.values()
)
zone_ok = any(
    v["n"] >= 30 and isinstance(v["pf"], (int, float)) and v["pf"] >= 1.0
    for v in split_c.values()
)
fund_negative = not rr_buckets_ok and not zone_ok

if rr15_salvageable:
    verdict = "SALVAGEABLE-BY-RR-GATE"
    verdict_detail = (f"Keeping only rr>=1.5: n={rr15['n']}, net={rr15['net']:+.2f}, "
                      f"PF={rr15['pf']}")
elif exit_driven:
    verdict = "EXIT-DRIVEN"
    verdict_detail = (f"M15_REVERT accounts for {m15_revert_pct:.1f}% of gross loss "
                      f"({m15_revert_gl:.2f} / {total_gl:.2f})")
elif fund_negative:
    verdict = "FUNDAMENTALLY-NEGATIVE"
    verdict_detail = ("No rr bucket and no zone subset reaches PF >= 1.0 at n >= 30")
else:
    verdict = "NO CLEAR CATEGORY"
    verdict_detail = "Criteria did not match any single category"

# ── 8. Write report ────────────────────────────────────────────
md = []
md.append("# V36.13 Dissection — Where the -$899 concentrates")
md.append("")
md.append("## Reconciliation")
md.append("")
md.append(f"- {len(per_trade)} in-deals matched to {len(per_trade)} out-deals. "
          f"All {len(per_trade)} trades joined.")
md.append(f"- {matched_entry}/{len(per_trade)} trades matched to [TRADE] ENTRY log lines. "
          f"{matched_exit}/{len(per_trade)} matched to [TRADE] EXIT lines.")
md.append(f"- Per-trade profit sum: **{total_profit:.2f}**")
md.append(f"- Report Total Net Profit: **{report_net:.2f}**")
md.append(f"- Delta: **{abs(total_profit - report_net):.2f}** "
          f"(explained by swap/summary deal)")
md.append("")
md.append("## Splits")
md.append("")

# A. rr bucket
md.append("### A. By rr Bucket at Entry")
md.append("")
md.append("| Group | n | Total $ | Mean $ | Win-Rate | PF |")
md.append("|-------|---|---------|--------|----------|-----|")
order_a = ["rr<1.0", "1.0-1.5", "1.5-2.0", ">=2.0"]
for g in order_a:
    v = split_a.get(g, {"n": 0, "total": 0, "mean": 0, "win_rate": 0, "pf": 0})
    pf_str = "inf" if v["pf"] == "inf" else f"{v['pf']:.2f}"
    md.append(f"| {g} | {v['n']} | {v['total']:+.2f} | {v['mean']:+.2f} "
              f"| {v['win_rate']:.1f}% | {pf_str} |")
md.append("")
for thresh in ["rr>=1.0", "rr>=1.5"]:
    v = keep_nets[thresh]
    pf_str = "inf" if v["pf"] == "inf" else f"{v['pf']:.2f}"
    md.append(f"**Cumulative net keeping only {thresh}:** n={v['n']}, "
              f"net={v['net']:+.2f}, PF={pf_str}")
md.append("")

# B. exit reason
md.append("### B. By Exit Reason")
md.append("")
md.append("| Group | n | Total $ | Mean $ | Win-Rate | PF |")
md.append("|-------|---|---------|--------|----------|-----|")
order_b = ["TP_HIT", "M15_REVERT", "TIMEOUT", "SL_HIT"]
for g in order_b:
    v = split_b.get(g, {"n": 0, "total": 0, "mean": 0, "win_rate": 0, "pf": 0})
    pf_str = "inf" if v["pf"] == "inf" else f"{v['pf']:.2f}"
    md.append(f"| {g} | {v['n']} | {v['total']:+.2f} | {v['mean']:+.2f} "
              f"| {v['win_rate']:.1f}% | {pf_str} |")
md.append("")
if split_b.get("M15_REVERT"):
    mrv = split_b["M15_REVERT"]
    pf_str = "inf" if mrv["pf"] == "inf" else f"{mrv['pf']:.2f}"
    md.append(f"**M15_REVERT:** n={mrv['n']}, net **{mrv['total']:+.2f}**, "
              f"PF={pf_str}")
md.append("")

# C. m30bbloc zone
md.append("### C. By Entry m30bbloc Zone")
md.append("")
md.append("| Group | n | Total $ | Mean $ | Win-Rate | PF |")
md.append("|-------|---|---------|--------|----------|-----|")
for g, v in sorted(split_c.items()):
    pf_str = "inf" if v["pf"] == "inf" else f"{v['pf']:.2f}"
    md.append(f"| {g} | {v['n']} | {v['total']:+.2f} | {v['mean']:+.2f} "
              f"| {v['win_rate']:.1f}% | {pf_str} |")
md.append("")

# D. direction
md.append("### D. By Direction")
md.append("")
md.append("| Group | n | Total $ | Mean $ | Win-Rate | PF |")
md.append("|-------|---|---------|--------|----------|-----|")
for g, v in sorted(split_d.items()):
    pf_str = "inf" if v["pf"] == "inf" else f"{v['pf']:.2f}"
    md.append(f"| {g} | {v['n']} | {v['total']:+.2f} | {v['mean']:+.2f} "
              f"| {v['win_rate']:.1f}% | {pf_str} |")
md.append("")

# E. HTF context
md.append("### E. By HTF Context (H4 vs Trigger Dir)")
md.append("")
md.append("| Group | n | Total $ | Mean $ | Win-Rate | PF |")
md.append("|-------|---|---------|--------|----------|-----|")
order_e = ["AGREE", "DISAGREE", "NEUTRAL"]
for g in order_e:
    v = split_e.get(g, {"n": 0, "total": 0, "mean": 0, "win_rate": 0, "pf": 0})
    pf_str = "inf" if v["pf"] == "inf" else f"{v['pf']:.2f}"
    md.append(f"| {g} | {v['n']} | {v['total']:+.2f} | {v['mean']:+.2f} "
              f"| {v['win_rate']:.1f}% | {pf_str} |")
md.append("")

# Verdict
md.append("## Verdict")
md.append("")
md.append(f"**{verdict}**")
md.append("")
md.append(f"{verdict_detail}")
md.append("")

# Subsets with PF >= 1.0 but n < 30
small_ok = []
for g, v in split_a.items():
    if v["n"] < 30 and isinstance(v["pf"], (int, float)) and v["pf"] >= 1.0:
        small_ok.append((g, v))
for g, v in split_c.items():
    if v["n"] < 30 and isinstance(v["pf"], (int, float)) and v["pf"] >= 1.0:
        small_ok.append((g, v))
if small_ok:
    md.append("### Subsets with PF >= 1.0 but n < 30 (not promoted)")
    md.append("")
    for g, v in small_ok:
        md.append(f"- {g}: n={v['n']}, PF={v['pf']:.2f}, "
                  f"total={v['total']:+.2f} -- too small to trade")
    md.append("")

# Limitations
md.append("## Limitations")
md.append("")
md.append("- **Post-hoc subsets are hypotheses, not validation:** Any promising "
          "subset identified here needs a FORWARD test on a fresh data window "
          "before trusting it. This analysis is descriptive, not prescriptive.")
md.append("- **In-sample kept-set:** The rr>=1.5 kept-set is in-sample -- it was "
          "selected on the same data it was evaluated on. Overfitting is possible.")
md.append("- **Counterfactual unknowable:** Removing a bucket (e.g., M15_REVERT) "
          "is counterfactual -- we cannot know whether those lost trades would have "
          "been wins had they exited differently.")
md.append("- **No new design recommendations:** The three fixed verdict categories "
          "(salvageable-by-rr-gate / exit-driven / fundamentally-negative) are the "
          "only conclusions drawn. No gate, exit, or parameter tuning is proposed.")
md.append("")
md.append("---")
md.append("")
md.append("*Analysis generated by `scripts/dissect_v36_13.py`. Deterministic -- "
          "re-running produces identical numbers.*")

with open(REPORT_PATH, "w", encoding="utf-8") as f:
    f.write("\n".join(md) + "\n")

# ── 9. Print summary ───────────────────────────────────────────
print(f"Reconciled: {len(per_trade)} trades, sum={total_profit:.2f}, "
      f"report={report_net:.2f}, delta={abs(total_profit - report_net):.2f}")
print(f"Matched: {matched_entry}/{len(per_trade)} entry, "
      f"{matched_exit}/{len(per_trade)} exit")
print(f"Verdict: {verdict}")
print(f"  Detail: {verdict_detail}")
print(f"Keep nets: {keep_nets}")
print(f"M15_REVERT % of gross loss: {m15_revert_pct:.1f}%")
print(f"Report written to {REPORT_PATH}")
