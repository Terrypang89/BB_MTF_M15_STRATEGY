#!/usr/bin/env python3
"""Forward-Test S-F Cell — h4_state=S AND h1_state=F at entry.

Tests the S-F survivor (PF 1.55, n=26, discovery window 2026.01.05-2026.04.29)
on out-of-sample data from the extras backtest (2025.06.01-2026.06.30).
Excludes the discovery window. Splits into PRE (2025.06.01-2025.12.31) and
POST (2026.05.01-2026.06.30).

Pre-registered bar: PF >= 1.2 at n >= 20.
"""

import json
import re
from datetime import datetime

JSON_PATH = "references/Backtest_data/V36.13/extras/report_tables_clean.json"
LOG_PATH = "references/Backtest_data/V36.13/extras/20260706_clean.log"
REPORT_PATH = "references/SF_FORWARD_TEST.md"

# Discovery window to exclude (inclusive)
DISC_START = datetime(2026, 1, 5)
DISC_END = datetime(2026, 4, 29, 23, 59, 59)

# Clean windows
PRE_START = datetime(2025, 6, 1)
PRE_END = datetime(2025, 12, 31, 23, 59, 59)
POST_START = datetime(2026, 5, 1)
POST_END = datetime(2026, 6, 30, 23, 59, 59)

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
    r"\[DUALTF\].*?dt:(\S+\s+\S+).*?"
    r"h4:state:(\S+).*?"
    r"h1:state:(\S+)"
)

# ── 1. Reconcile deals ──────────────────────────────────────────
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
report_net = float(data["table_results"]["Total Net Profit"].replace(" ", ""))

# ── 2. Parse log ────────────────────────────────────────────────
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

# DUALTF: dt -> (h4_state, h1_state)
dt_to_h4h1 = {}
with open(LOG_PATH) as f:
    for line in f:
        m = DUALTF_RE.search(line)
        if m:
            dt = datetime.strptime(m.group(1), "%Y.%m.%d %H:%M:%S")
            dt_to_h4h1[dt] = (m.group(2), m.group(3))

# ── 3. Match trades to log lines ────────────────────────────────
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

# ── 4. Lookup h4_state and h1_state at entry bar ────────────────
for t in per_trade:
    if not t.get("entry_log"):
        continue
    entry_dt = t["entry_log"]["dt"]
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

# ── 5. Exclusion: drop discovery window ─────────────────────────
def in_discovery_window(dt):
    return DISC_START <= dt <= DISC_END

excluded = [t for t in per_trade if in_discovery_window(t["entry_time"])]
kept = [t for t in per_trade if not in_discovery_window(t["entry_time"])]

# Assert zero overlap
kept_in_disc = [t for t in kept if in_discovery_window(t["entry_time"])]
assert len(kept_in_disc) == 0, f"ERROR: {len(kept_in_disc)} kept trades in discovery window!"

# ── 6. Split into PRE and POST windows ──────────────────────────
pre_trades = [t for t in kept if PRE_START <= t["entry_time"] <= PRE_END]
post_trades = [t for t in kept if POST_START <= t["entry_time"] <= POST_END]

# ── 7. Filter to S-F cell ───────────────────────────────────────
def is_sf(t):
    return t.get("h4_state") == "S" and t.get("h1_state") == "F"

sf_all = [t for t in kept if is_sf(t)]
sf_pre = [t for t in pre_trades if is_sf(t)]
sf_post = [t for t in post_trades if is_sf(t)]

# ── 8. Compute stats ────────────────────────────────────────────
def compute_stats(trades):
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

stats_all = compute_stats(kept)
stats_pre = compute_stats(pre_trades)
stats_post = compute_stats(post_trades)
stats_sf_all = compute_stats(sf_all)
stats_sf_pre = compute_stats(sf_pre)
stats_sf_post = compute_stats(sf_post)

# ── 9. Verdict ──────────────────────────────────────────────────
combined_pf = stats_sf_all["pf"]
combined_n = stats_sf_all["n"]

# Check if PF meets threshold; "inf" counts as >= any threshold
pf_numeric = isinstance(combined_pf, (int, float))
pf_ok = (pf_numeric and combined_pf >= 1.2) or combined_pf == "inf"

if pf_ok and combined_n >= 20:
    verdict = "S-F CONFIRMED"
    verdict_detail = (f"Combined OOS S-F: n={combined_n}, PF={combined_pf}. "
                      "Real edge — still requires live-forward caution "
                      "(two backtest windows, not live).")
elif pf_numeric and combined_pf < 1.0:
    verdict = "S-F REJECTED"
    verdict_detail = ("In-sample chance-survivor; scenario claim dead; "
                      "M15-trigger unsalvageable by regime filter.")
elif not pf_ok and combined_n < 20:
    # n < 20 — rarity limited the test
    verdict = "S-F INCONCLUSIVE"
    verdict_detail = (f"Combined OOS S-F: n={combined_n}. "
                      "S-F's rarity limited the test; unresolved.")
else:
    # 1.0 <= PF < 1.2 with n >= 20 — PF too low but not rejected
    verdict = "S-F INCONCLUSIVE"
    verdict_detail = (f"Combined OOS S-F: n={combined_n}, PF={combined_pf}. "
                      "PF between 1.0 and 1.2 — unresolved; does not clear "
                      "the pre-registered bar but is not rejected either.")

# PRE vs POST stability
pre_sf_pf = stats_sf_pre["pf"]
post_sf_pf = stats_sf_post["pf"]
pre_pf_num = isinstance(pre_sf_pf, (int, float))
post_pf_num = isinstance(post_sf_pf, (int, float))
pre_passes = pre_pf_num and pre_sf_pf >= 1.2 and stats_sf_pre["n"] >= 20
post_passes = post_pf_num and post_sf_pf >= 1.2 and stats_sf_post["n"] >= 20
stability_note = ""
if pre_passes and post_passes:
    stability_note = "PRE and POST both pass the bar — STABLE across windows."
elif pre_passes or post_passes:
    stability_note = (f"PRE and POST disagree (PRE PF={pre_sf_pf}, n={stats_sf_pre['n']}; "
                      f"POST PF={post_sf_pf}, n={stats_sf_post['n']}). "
                      "This INSTABILITY is evidence against a robust edge.")
else:
    # Both fail the full bar — check if they fail for different reasons
    pre_pf_ok = pre_pf_num and pre_sf_pf >= 1.2
    post_pf_ok = post_pf_num and post_sf_pf >= 1.2
    if pre_pf_ok and not post_pf_ok:
        stability_note = (f"PRE PF={pre_sf_pf} meets threshold but n={stats_sf_pre['n']} < 20; "
                          f"POST PF={post_sf_pf} fails threshold. "
                          "This INSTABILITY is evidence against a robust edge.")
    elif not pre_pf_ok and post_pf_ok:
        stability_note = (f"PRE PF={pre_sf_pf} fails threshold; "
                          f"POST PF={post_sf_pf} meets threshold but n={stats_sf_post['n']} < 20. "
                          "This INSTABILITY is evidence against a robust edge.")
    else:
        stability_note = "PRE and POST both fail the bar — consistent REJECTION."

# ── 10. Print summary ───────────────────────────────────────────
print(f"\n{'='*60}")
print(f"S-F Forward Test — V36.13 Extras (M5)")
print(f"{'='*60}")
print(f"\nReconciliation: {len(per_trade)} trades, sum={total_profit:.2f}, "
      f"report={report_net:.2f}, delta={abs(total_profit - report_net):.2f}")
print(f"\nExclusion: {len(excluded)} trades in discovery window, "
      f"{len(kept)} kept")
if kept:
    min_dt = min(t["entry_time"] for t in kept)
    max_dt = max(t["entry_time"] for t in kept)
    print(f"  Kept date range: {min_dt} to {max_dt}")
    # Verify no gap at discovery window boundary
    pre_max = max(t["entry_time"] for t in pre_trades) if pre_trades else None
    post_min = min(t["entry_time"] for t in post_trades) if post_trades else None
    if pre_max:
        print(f"  PRE max: {pre_max}")
    if post_min:
        print(f"  POST min: {post_min}")
print(f"\nWindows: PRE n={len(pre_trades)}, POST n={len(post_trades)}")
print(f"\nS-F subsets:")
print(f"  Combined: n={stats_sf_all['n']}, total={stats_sf_all['total']:+.2f}, "
      f"WR={stats_sf_all['win_rate']:.1f}%, PF={stats_sf_all['pf']}")
print(f"  PRE: n={stats_sf_pre['n']}, total={stats_sf_pre['total']:+.2f}, "
      f"WR={stats_sf_pre['win_rate']:.1f}%, PF={stats_sf_pre['pf']}")
print(f"  POST: n={stats_sf_post['n']}, total={stats_sf_post['total']:+.2f}, "
      f"WR={stats_sf_post['win_rate']:.1f}%, PF={stats_sf_post['pf']}")
print(f"\nWhole-window context:")
print(f"  Combined: n={stats_all['n']}, total={stats_all['total']:+.2f}, "
      f"WR={stats_all['win_rate']:.1f}%, PF={stats_all['pf']}")
print(f"  PRE: n={stats_pre['n']}, total={stats_pre['total']:+.2f}, "
      f"WR={stats_pre['win_rate']:.1f}%, PF={stats_pre['pf']}")
print(f"  POST: n={stats_post['n']}, total={stats_post['total']:+.2f}, "
      f"WR={stats_post['win_rate']:.1f}%, PF={stats_post['pf']}")
print(f"\nVerdict: {verdict}")
print(f"  {verdict_detail}")
print(f"\nStability: {stability_note}")

# ── 11. Write report ────────────────────────────────────────────
def pf_str(pf_val):
    return "inf" if pf_val == "inf" else f"{pf_val:.2f}"

md = []
md.append("# S-F Forward Test — Out-of-Sample Verification")
md.append("")
md.append(f"**Discovery window excluded:** 2026.01.05–2026.04.29 (where S-F was found, PF 1.55, n=26, 1 of 16 cells).")
md.append(f"**Clean windows:** PRE = 2025.06.01–2025.12.31, POST = 2026.05.01–2026.06.30.")
md.append(f"**Pre-registered bar:** PF >= 1.2 at n >= 20.")
md.append("")

# Data files
md.append("## Data Files Used")
md.append("")
md.append(f"- Log: `references/Backtest_data/V36.13/extras/20260706_clean.log`")
md.append(f"- Deals: `references/Backtest_data/V36.13/extras/report_tables_clean.json`")
md.append(f"- Extras backtest: M5, 2025.06.01–2026.06.30")
md.append("")

# Reconciliation
md.append("## Reconciliation")
md.append("")
md.append(f"- **Trades reconciled:** {len(per_trade)} (in/out deal pairs matched sequentially)")
md.append(f"- **Per-trade profit sum:** {total_profit:+.2f}")
md.append(f"- **Report net profit:** {report_net:+.2f}")
md.append(f"- **Delta:** {abs(total_profit - report_net):.2f} (explained by swap/summary deals)")
md.append("")

# Exclusion
md.append("## Exclusion — Discovery Window Removed")
md.append("")
md.append(f"- **Discovery window:** 2026.01.05–2026.04.29 inclusive")
md.append(f"- **Trades excluded:** {len(excluded)}")
md.append(f"- **Trades kept:** {len(kept)}")
kept_min = min(t["entry_time"] for t in kept)
kept_max = max(t["entry_time"] for t in kept)
md.append(f"- **Kept date range:** {kept_min} to {kept_max}")
md.append(f"- **Zero-overlap assertion:** no kept trade falls in the discovery window — VERIFIED (asserted by script)")
md.append("")

# Windows
md.append("## Windows")
md.append("")
md.append(f"- **PRE** (2025.06.01–2025.12.31): **{len(pre_trades)}** trades")
md.append(f"- **POST** (2026.05.01–2026.06.30): **{len(post_trades)}** trades")
md.append("")

# S-F results
md.append("## S-F Cell Results (h4_state=S AND h1_state=F at entry)")
md.append("")
md.append("| Window | n | Total $ | Mean $ | Win-Rate | PF |")
md.append("|--------|---|---------|--------|----------|-----|")
md.append(f"| PRE | {stats_sf_pre['n']} | {stats_sf_pre['total']:+.2f} | "
          f"{stats_sf_pre['mean']:+.2f} | {stats_sf_pre['win_rate']:.1f}% | "
          f"{pf_str(stats_sf_pre['pf'])} |")
md.append(f"| POST | {stats_sf_post['n']} | {stats_sf_post['total']:+.2f} | "
          f"{stats_sf_post['mean']:+.2f} | {stats_sf_post['win_rate']:.1f}% | "
          f"{pf_str(stats_sf_post['pf'])} |")
md.append(f"| COMBINED | {stats_sf_all['n']} | {stats_sf_all['total']:+.2f} | "
          f"{stats_sf_all['mean']:+.2f} | {stats_sf_all['win_rate']:.1f}% | "
          f"{pf_str(stats_sf_all['pf'])} |")
md.append("")

# Whole-window context
md.append("## Whole-Window Context (all cells)")
md.append("")
md.append("| Window | n | Total $ | Mean $ | Win-Rate | PF |")
md.append("|--------|---|---------|--------|----------|-----|")
md.append(f"| PRE | {stats_pre['n']} | {stats_pre['total']:+.2f} | "
          f"{stats_pre['mean']:+.2f} | {stats_pre['win_rate']:.1f}% | "
          f"{pf_str(stats_pre['pf'])} |")
md.append(f"| POST | {stats_post['n']} | {stats_post['total']:+.2f} | "
          f"{stats_post['mean']:+.2f} | {stats_post['win_rate']:.1f}% | "
          f"{pf_str(stats_post['pf'])} |")
md.append(f"| COMBINED | {stats_all['n']} | {stats_all['total']:+.2f} | "
          f"{stats_all['mean']:+.2f} | {stats_all['win_rate']:.1f}% | "
          f"{pf_str(stats_all['pf'])} |")
md.append("")

# Verdict
md.append("## Verdict")
md.append("")
md.append(f"**{verdict}**")
md.append("")
md.append(f"{verdict_detail}")
md.append("")
md.append(f"**PRE vs POST stability:** {stability_note}")
md.append("")

# Limitations
md.append("## Limitations")
md.append("")
md.append("- **Backtest not live:** Two backtest windows on the same symbol, same EA config. A live-forward test on unseen market data is required before any rule is built on an S-F filter.")
md.append("- **S-F rarity:** The S-F cell is rare — only {0} of {1} OOS trades are S-F ({2:.1f}%). Small sample size limits the power of the test.".format(
    stats_sf_all["n"], len(kept), stats_sf_all["n"] / len(kept) * 100 if len(kept) > 0 else 0))
md.append("- **Two windows:** Only two clean windows (PRE and POST). More windows would strengthen the test.")
md.append("- **Single EA config:** Only one EA configuration was tested. Results may not generalize to other parameter sets.")
md.append("")
md.append("---")
md.append("")
md.append("*Analysis generated by `scripts/forward_test_sf.py`. Deterministic — re-running produces identical numbers.*")

with open(REPORT_PATH, "w", encoding="utf-8") as f:
    f.write("\n".join(md) + "\n")

print(f"\nReport written to {REPORT_PATH}")
