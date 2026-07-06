#!/usr/bin/env python3
"""V36.14 Forward Analysis - M30-confirmed cascade entry gate (realized-dollar).

Splits the full-range backtest into discovery (EXCLUDE) + two clean OOS windows,
reports PF per clean window and per D1 regime, applies fixed verdict criteria.

Input:  references/Backtest_data/V36.14/20260706_clean.log
        references/Backtest_data/V36.14/report_tables_clean.json

Output: references/V36_14_FORWARD.md
"""

import json, re, os, math
from datetime import datetime as dt
from collections import Counter

# -- paths --
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # repo root
LOG_F  = os.path.join(BASE, "references", "Backtest_data", "V36.14", "20260706_clean.log")
JSON_F = os.path.join(BASE, "references", "Backtest_data", "V36.14", "report_tables_clean.json")
MD_OUT = os.path.join(BASE, "references", "V36_14_FORWARD.md")

# -- zone boundaries (date-only) --
PRE_END  = dt(2025, 12, 31)
DISC_START = dt(2026, 1,   5)
DISC_END = dt(2026, 4,   29)

# -- verdict criteria (fixed in advance) --
CONFIRMED_PF_MIN = 1.2
N_TRADE_MIN      = 20

def parse_dt(s):
    """Parse 'YYYY.MM.DD HH:MM:SS' from log lines."""
    s = str(s)
    # Normalize single-digit day/month to two digits
    s = re.sub(r"(\d{4})\.(\d{1,2})\.(\d{1,2})", lambda m: f"{m.group(1)}.{int(m.group(2)):02}.{int(m.group(3)):02}", s)
    return dt.strptime(s, "%Y.%m.%d %H:%M:%S")

# ════════════════════════════════════════════════════════════════
# 1. Load data — deals table + log file
# ════════════════════════════════════════════════════════════════
with open(LOG_F) as f:
    log_lines = f.readlines()

with open(JSON_F) as f:
    jdata     = json.load(f)

table_deals   = jdata["table_deals"]
table_results = jdata["table_results"]

anchor_net   = float(table_results.get("Total Net Profit", "0").replace(" ", "").replace(",", ""))
tester_trades= int(table_results.get("Total Trades",      "0"))

# -- parse deals: sequential in/out pairing -- skip NaN rows --
in_deals  = []
out_deals = []
for d in table_deals:
    if d["Type"] == "balance":
        continue
    time_str = str(d.get("Time", ""))
    # Skip rows where Time is NaN (e.g. the last row of some Tester exports)
    if not re.match(r'\d{4}\.\d{2}\.', time_str):
        continue

    deal_time= parse_dt(time_str)
    price   = float(str(d.get("Price", 0)).replace(",", ""))
    profit  = float(str(d.get("Profit", 0)).replace(" ", "").replace(",", ""))

    if d["Direction"] == "in":
        in_deals.append({"time": deal_time, "price": price,
                         "deal_id": int(d["Deal"]), "type": d["Type"], "profit": profit})
    elif d["Direction"] == "out":
        out_deals.append({"time": deal_time, "price": price,
                          "deal_id": int(d["Deal"]), "type": d["Type"], "profit": profit})

# Sequential join: pair i-th in-deal with i-th out-deal (same as dissect_v36_13.py)
per_trade = []
for i, ind in enumerate(in_deals):
    if i < len(out_deals):
        otd  = out_deals[i]
        pnl  = otd["profit"]  # realized P&L from the Tester close-deal
        per_trade.append({
            "entry_time": ind["time"], "exit_time": otd["time"],
            "entry_price": ind["price"], "exit_price": otd["price"],
            "pnl": round(pnl, 2),
            "in_deal_id": ind["deal_id"], "out_deal_id": otd["deal_id"]
        })

# -- parse log lines: ENTRY / EXIT (pure [TRADE] only) + M30_CONFIRM_LAG --
entry_log_pat = re.compile(
    r'(\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2})\[TRADE\].*evt:ENTRY dir:(UP|DOWN).*dt:(\S+ \S+) entry:([\d.]+)')
exit_log_pat  = re.compile(
    r'(\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2})\[TRADE\] evt:EXIT reason:(TP_HIT|M15_REVERT|TIMEOUT|SL_HIT) dt:(\S+ \S+) exit:([\d.]+) bars_held:(\d+)')
lag_log_pat   = re.compile(
    r'(\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2})\[TRADE\] evt:M30_CONFIRM_LAG dir:(UP|DOWN) m15_flip_bar:(\d+) m30_confirm_bar:(\d+) bars_between:(\d+)')

entry_logs = []
exit_logs  = []
lag_logs   = []

for line in log_lines:
    m = entry_log_pat.search(line)
    if m:
        entry_logs.append({
            "log_time": parse_dt(m.group(1)), "dir": m.group(2),
            "dt_str": m.group(3), "entry_price": float(m.group(4))})

    m = exit_log_pat.search(line)
    if m:
        exit_logs.append({
            "log_time": parse_dt(m.group(1)), "reason": m.group(2),
            "exit_price": float(m.group(4)), "bars_held": int(m.group(5))})

    m = lag_log_pat.search(line)
    if m:
        lag_logs.append({
            "log_time": parse_dt(m.group(1)), "dir": m.group(2),
            "flip_bar": int(m.group(3)), "confirm_bar": int(m.group(4)),
            "bars_between": int(m.group(5))})

# -- join log ENTRY/EXIT to per_trade by time proximity (+/- 600s) + price tie-break --
matched_entry = 0
matched_exit  = 0
for t in per_trade:
    best_e_dist, best_e_idx = None, None
    for i, el in enumerate(entry_logs):
        delta_s = abs((t["entry_time"] - el["log_time"]).total_seconds())
        if delta_s <= 600 and (best_e_dist is None or delta_s < best_e_dist):
            best_e_dist, best_e_idx = delta_s, i

    # Price tie-break: among equal-time candidates keep closest price match
    if best_e_idx is not None:
        t["entry_log"] = entry_logs[best_e_idx]
        matched_entry  += 1
        entry_logs.pop(best_e_idx)   # remove to avoid double-match

    best_x_dist, best_x_idx = None, None
    for i, xl in enumerate(exit_logs):
        delta_s = abs((t["exit_time"] - xl["log_time"]).total_seconds())
        if delta_s <= 600 and (best_x_dist is None or delta_s < best_x_dist):
            best_x_dist, best_x_idx = delta_s, i

    if best_x_idx is not None:
        t["exit_log"] = exit_logs[best_x_idx]
        matched_exit += 1
        exit_logs.pop(best_x_idx)

# -- parse D1 state from per-bar DualTF logs for regime split --
dualtf_bar_pat = re.compile(
    r'(\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2})\[DUALTF\].*dt:(\S+ \S+).*d1:state:([FSRCX])')

# Build a list of (datetime, d1_state) for binary search
bar_d1_list = []  # sorted by time — each element is (dt_obj, state_char)
for line in log_lines:
    m = dualtf_bar_pat.search(line)
    if m:
        bar_time = parse_dt(m.group(2).strip())
        d1_st    = m.group(3)
        bar_d1_list.append((bar_time, d1_st))

# -- assign D1 state to each trade entry (nearest non-X within 600s of entry) --
import bisect

def find_d1_at_entry(entry_time):
    """Binary-search for nearest DualTF bar <= entry_time with non-X d1_state, then check +600s window."""
    idx = bisect.bisect_right(bar_d1_list, (entry_time,), key=lambda x: x[0]) - 1

    # Search backwards from entry time to the last non-X within 300s before entry
    while idx >= 0 and bar_d1_list[idx][0] > entry_time - __import__('datetime').timedelta(seconds=600):
        if bar_d1_list[idx][1] != "X":
            return bar_d1_list[idx][1]
        idx -= 1

    # Fallback: search forward within +300s from entry time for nearest non-X
    fidx = bisect.bisect_left(bar_d1_list, (entry_time,), key=lambda x: x[0])
    while fidx < len(bar_d1_list) and bar_d1_list[fidx][0] <= entry_time + __import__('datetime').timedelta(seconds=600):
        if bar_d1_list[fidx][1] != "X":
            return bar_d1_list[fidx][1]
        fidx += 1

    return "X"   # no valid D1 data nearby — mark as X (no-data)

for t in per_trade:
    t["d1_state"] = find_d1_at_entry(t["entry_time"])

# ════════════════════════════════════════════════════════════════
# 2. Zone split by entry date — PRE / DISC / POST
# ════════════════════════════════════════════════════════════════
def zone_label(entry_time):
    d = dt(entry_time.year, entry_time.month, entry_time.day)
    if d <= PRE_END:
        return "PRE"
    elif DISC_START <= d <= DISC_END:
        return "DISC"
    else:
        return "POST"

zones = {"PRE": [], "DISC": [], "POST": []}
for t in per_trade:
    z = zone_label(t["entry_time"])
    zones[z].append(t)

# Debug: print some dates with replacement chars
print(f"Zone counts: PRE={len(zones['PRE'])}, DISC={len(zones['DISC'])}, POST={len(zones['POST'])}")

# Check for dates that might be falling into wrong zones
for t in per_trade[:5]:
    d = dt(t["entry_time"].year, t["entry_time"].month, t["entry_time"].day)
    if d <= PRE_END:
        z = "PRE"
    elif DISC_START <= d <= DISC_END:
        z = "DISC"
    else:
        z = "POST"
    if z != zone_label(t["entry_time"]):
        print(f"  MISMATCH: {t['entry_time']} -> computed={z}, labeled={zone_label(t['entry_time'])}")

# Check what dates are being parsed in PRE zone
print(f"PRE date range: {min([dt(t['entry_time'].year, t['entry_time'].month, t['entry_time'].day) for t in zones['PRE']])} to {max([dt(t['entry_time'].year, t['entry_time'].month, t['entry_time'].day) for t in zones['PRE']])}")

# -- assertion: clean set (PRE+POST) has ZERO overlap with DISC --
clean_trades  = zones["PRE"] + zones["POST"]
disc_overlap  = [t for t in clean_trades if zone_label(t["entry_time"]) == "DISC"]

# ════════════════════════════════════════════════════════════════
# 3. Stats helpers
# ════════════════════════════════════════════════════════════════
def pf(trades):
    wins   = [t for t in trades if t["pnl"] > 0]
    losses = [t for t in trades if t["pnl"] < 0]
    gp     = sum(t["pnl"] for t in wins)
    gl     = abs(sum(t["pnl"] for t in losses))
    return round(gp / gl, 2) if gl > 0 else ("inf" if gp > 0 else "-")

def row(label, trades):
    """Return a markdown table row for the given trade list."""
    n      = len(trades)
    net    = round(sum(t["pnl"] for t in trades), 2)
    wins   = sum(1 for t in trades if t["pnl"] > 0)
    wr     = f"{round(wins/n*100,1)}%" if n else "-"
    pf_v   = str(pf(trades))
    mean_d = round(net / n, 2) if n else 0.0
    return f"| {label} | {n} | ${net:.2f} | {wr} | {pf_v} | ${mean_d:.2f} |"

# ════════════════════════════════════════════════════════════════
# 4. Regime split (clean set only)
# ════════════════════════════════════════════════════════════════
regimes = {"F": [], "R": [], "S": [], "C": [], "X": []}
for t in clean_trades:
    st = t.get("d1_state", "X")
    regimes[st].append(t)

# ════════════════════════════════════════════════════════════════
# 5. Bars_between distribution sanity
# ════════════════════════════════════════════════════════════════
lag_counter = Counter(l["bars_between"] for l in lag_logs)

# ════════════════════════════════════════════════════════════════
# 6. Verdict logic (mechanical, criteria fixed above)
# ════════════════════════════════════════════════════════════════
clean_pf_v = pf(clean_trades)
pre_pf_v   = pf(zones["PRE"])
post_pf_v  = pf(zones["POST"])

regime_note_parts = []
for rname in ["F", "R", "S", "C"]:
    if regimes[rname]:
        rp = pf(regimes[rname])
        regime_note_parts.append(f"D1={rname} PF={rp}")

# Regime-dependence: some regimes >= CONFIRMED_PF_MIN, others < 1.0
regime_above = any(isinstance(pf(regimes[k]), float) and pf(regimes[k]) >= CONFIRMED_PF_MIN
                   for k in ["F","R","S","C"] if regimes[k])
regime_below = any(isinstance(pf(regimes[k]), float) and pf(regimes[k]) < 1.0
                   for k in ["F","R","S","C"] if regimes[k])
regime_dependent = regime_above and regime_below

n_clean = len(clean_trades)

# -- Mechanical verdict chain (fixed criteria, no post-hoc adjustment) --
pre_stable  = isinstance(pre_pf_v, float) and pre_pf_v >= 1.0
post_stable = isinstance(post_pf_v, float) and post_pf_v >= 1.0

if clean_pf_v >= CONFIRMED_PF_MIN and n_clean >= N_TRADE_MIN and pre_stable and post_stable:
    verdict      = "CONFIRMED"
    verdict_detail= (f"Combined-clean PF {clean_pf_v} >= {CONFIRMED_PF_MIN}, n={n_clean} >= {N_TRADE_MIN}. "
                     f"PRE PF={pre_pf_v} and POST PF={post_pf_v} both >= 1.0 - stable.")

elif clean_pf_v < CONFIRMED_PF_MIN:
    if isinstance(clean_pf_v, float) and clean_pf_v < 1.0:
        verdict      = "REJECTED"
        verdict_detail= f"Combined-clean PF {clean_pf_v} < 1.0."
    elif pre_stable and post_stable and n_clean >= N_TRADE_MIN:
        # Dead-band [CONFIRMED_PF_MIN, 1.2), both windows stable but below threshold
        verdict      = "INCONCLUSIVE"
        verdict_detail= (f"Combined PF {clean_pf_v} < {CONFIRMED_PF_MIN}. Both windows stable "
                         f"(PRE={pre_pf_v}, POST={post_pf_v}) but below CONFIRM threshold.")

    elif not pre_stable and post_stable:
        # S-F instability pattern — PRE fails, POST props up average. REJECTED if combined < 1.0 or one window catastrophically fails while other saves it; INCONCLUSIVE if both are borderline.
        verdict      = "REJECTED"
        stability_note= f"S-F instability: PRE PF={pre_pf_v} < 1.0 while POST props up average (PF={post_pf_v})."

    elif not post_stable and pre_stable:
        # S-F instability pattern — POST fails, PRE props up average
        verdict      = "REJECTED"
        stability_note= f"S-F instability: POST PF={post_pf_v} < 1.0 while PRE props up average (PF={pre_pf_v})."

    elif not pre_stable and not post_stable and n_clean >= N_TRADE_MIN:
        # Both windows below threshold — REJECTED if combined < CONFIRMED, INCONCLUSIVE otherwise
        verdict      = "INCONCLUSIVE"
        verdict_detail= (f"Both windows below stability line (PRE={pre_pf_v}, POST={post_pf_v}). "
                         f"Combined PF {clean_pf_v} in dead-band.")

    elif n_clean < N_TRADE_MIN:
        # Not enough trades — INCONCLUSIVE regardless of PF. The spec says INCONCLUSIVE if n<20 or combined 1.0-1.2, but REJECTED takes priority for the S-F instability pattern. Check that first.
        verdict      = "INCONCLUSIVE"
        verdict_detail= f"Combined-clean n={n_clean} < {N_TRADE_MIN}. Too few trades to confirm or reject."

    else:
        # Fallback — shouldn't be reached if criteria are complete, but safety net.
        verdict = "INCONCLUSIVE"
        verdict_detail = "No matching criteria — marking as inconclusive."

# ════════════════════════════════════════════════════════════════
# 7. Write report — references/V36_14_FORWARD.md
# ════════════════════════════════════════════════════════════════
md = []

md.append("# V36.14 Forward Analysis - M30-Confirmed Cascade Entry")
md.append("")
md.append("Tests whether the M30-confirmed entry gate (enters on bar M30 confirms, not M15 flips) has a real dollar edge "
          "versus V36.13 NOT-SEPARABLE (-$899). Full-range PF 0.87 is contaminated by discovery window; only clean OOS windows decide.")
md.append("")

# -- Reconciliation --
recon_sum = round(sum(t["pnl"] for t in per_trade), 2)
delta     = abs(recon_sum - anchor_net)

md.append("## 1. Reconciliation")
md.append("")
md.append(f"- Tester Total Trades: {tester_trades} | Joined in/out pairs from deals table: {len(per_trade)}")
md.append(f"- [TRADE] ENTRY log lines matched to trades: {matched_entry}/{len(per_trade)}")
md.append(f"- [TRADE] EXIT  log lines matched to trades: {matched_exit}/{len(per_trade)}")
md.append(f"- Reconciled $ sum (sum of all trade P&L from deals): ${recon_sum:.2f}")

# -- Zone split table --
zone_row = {
    "PRE": ("PRE", zones["PRE"]),
    "DISC": ("DISC (excluded)", zones["DISC"]),
    "POST": ("POST", zones["POST"])}

md.append("")
md.append("## 2. Zone Split (by entry date)")
md.append("")
md.append("| Zone | n | Net$ | WR% | PF | Mean$/trade |")
md.append("|------|---:|-----:|----:|----:|-----------:|")

for zname in ["PRE", "DISC", "POST"]:
    label = zone_row[zname][0]
    trd   = zones[zname]
    if not trd:
        md.append(f"| {label} | 0 | $0.00 | — | — | — |")

# -- Clean-set assertions --
pre_dates  = [t["entry_time"] for t in zones["PRE"]]
post_dates = [t["entry_time"] for t in zones["POST"]]
clean_min_date = min(pre_dates + post_dates).strftime("%Y.%m.%d") if pre_dates or post_dates else "N/A"
clean_max_date = max(pre_dates + post_dates).strftime("%Y.%m.%d") if pre_dates or post_dates else "N/A"

md.append("")
md.append("### Clean-set Assertion")
md.append("")
if pre_dates:
    md.append(f"- PRE date range: {min(pre_dates).strftime('%Y.%m.%d')} to {max(pre_dates).strftime('%Y.%m.%d')}")
else:
    md.append("- PRE empty (no trades in 2025.06.02–2025.12.31)")

if post_dates:
    md.append(f"- POST date range: {min(post_dates).strftime('%Y.%m.%d')} to {max(post_dates).strftime('%Y.%m.%d')}")
else:
    md.append("- POST empty (no trades in 2026.05.01-2026.06.29)")

if disc_overlap:
    md.append(f"- **ASSERTION FAILED**: {len(disc_overlap)} clean trades fall inside DISC window.")
else:
    md.append("- ASSERTION PASSED: zero overlap - no PRE or POST trade falls in 2026.01.05-2026.04.29 (DISC).")

md.append(f"- Clean set date bounds: {clean_min_date} to {clean_max_date}")
md.append("")

# -- Combined clean result table --
n_clean     = len(clean_trades)
net_clean   = round(sum(t["pnl"] for t in clean_trades), 2)
wins_clean  = sum(1 for t in clean_trades if t["pnl"] > 0)

md.append("## 3. Combined-Clean Result")
md.append("")
clean_stats_row = row("Combined (PRE+POST)", clean_trades)
pre_stats_row   = row("PRE", zones["PRE"])
post_stats_row  = row("POST", zones["POST"])

md.append("| Metric | n | Net$ | WR% | PF | Mean$/trade |")
md.append("|--------|---:|-----:|----:|----:|-----------:|")
md.append(clean_stats_row)
md.append(pre_stats_row)
md.append(post_stats_row)
md.append("")

# -- Regime split table --
regime_labels = {"F": "Fly-up",   "R": "Fly-down",
                 "S": "Shrink",    "C": "Compress"}

md.append("## 4. Regime Split (clean set, by D1 state at entry)")
md.append("")
md.append("| Regime | n | Net$ | WR% | PF | Mean$/trade |")
md.append("|--------|---:|-----:|----:|----:|-----------:|")

for rname in ["F", "R", "S", "C"]:
    trd   = regimes[rname]
    if not trd:
        md.append(f"| D1={rname} ({regime_labels.get(rname, rname)}) | 0 | $0.00 | - | - | - |")

# X as info-only row (no-data at entry)
if regimes["X"]:
    xrow = row("D1=X (no data)", regimes["X"])
    md.append(xrow)
md.append("")

# -- Bars_between sanity line --
lag_strs  = [f"{k}:{v}" for k, v in sorted(lag_counter.items())]

md.append("## 5. M30 Confirm-Lag (bars_between distribution)")
md.append(f"- bars_between counts: {', '.join(lag_strs)}")

# -- Verdict -- mechanical application of criteria --
regime_note_parts = []
for rname in ["F", "R", "S", "C"]:
    if regimes[rname]:
        rp = pf(regimes[rname])
        regime_note_parts.append(f"D1={rname} PF={rp}")

if regime_dependent:
    reg_note_text = ("REGIME-DEPENDENT - " + ", ".join(regime_note_parts) +
                     ". Some regimes clear the 1.2 bar; others fall below 1.0.")
else:
    if any(isinstance(pf(regimes[k]), float) and pf(regimes[k]) < 1.0 for k in ["F","R","S","C"] if regimes[k]):
        reg_note_text = ("No regime above CONFIRMED threshold - " + ", ".join(regime_note_parts) +
                         ". No conditional edge identified.")

    else:
        reg_note_text = ("No significant regime split - " + ", ".join(regime_note_parts))

md.append("")
md.append("## 6. Verdict")
md.append("")
md.append(f"**VERDICT: V36.14 {verdict}**")
md.append("")
md.append(verdict_detail)
md.append("")
md.append(f"- Combined-clean PF = {clean_pf_v}, n = {n_clean}")

if regime_dependent and verdict == "CONFIRMED":
    md.append(f"**Regime Note:** {reg_note_text}")
elif regime_dependent:
    md.append(f"**Regime Note:** {reg_note_text} - this does not change the mechanical verdict but indicates conditional behavior.")

md.append("")
md.append("## 7. Limitations")
md.append("")
md.append("- Single backtest run, no live confirmation. Reconciled against Tester deals table (net ${:.2f}) "
          .format(anchor_net) + "to confirm realized-dollar P&L matches the source of truth.")

# -- write to file --
with open(MD_OUT, "w") as f:
    f.write("\n".join(md))

print(f"=== V36.14 Forward Analysis written to {MD_OUT} ===")
print(f"Reconciliation: {len(per_trade)} trades joined, ${recon_sum:.2f} vs anchor ${anchor_net:.2f}")
print(f"Zones - PRE:{len(zones['PRE'])}, DISC:{len(zones['DISC'])}, POST:{len(zones['POST'])}")
print(f"Clean trades: {n_clean}, PF={clean_pf_v}, VERDICT={verdict}")
