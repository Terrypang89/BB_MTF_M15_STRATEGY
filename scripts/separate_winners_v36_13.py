#!/usr/bin/env python3
"""Winner-vs-Loser Entry Separation with BB_diffmid_trend Ablation.

For 197 trades (45 TP_HIT winners + 152 M15_REVERT losers), parse entry-time
features and test how well each separates winners from losers.

Two ablation sets:
  BASE: dir, m30bbloc, h1bbloc, h4bbloc, rr, h4_state, h1_state, m30_state, entry_hour.
  BASE + diffMid_Trend_M30, diffMid_Trend_H1, diffMid_Trend_H4.

A feature "separates" if any category/threshold yields win-rate >= 50% at n >= 20.
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

# DUALTF: captures dt, h4_state, h1_state, m30_state
DUALTF_RE = re.compile(
    r"\[DUALTF\].*?dt:(\S+\s+\S+).*?"
    r"h4:state:(\S+).*?"
    r"h1:state:(\S+).*?"
    r"m30:state:(\S+)"
)

# TF-specific lines: [M30], [H1], [H4] with diffMid_Trend arrays
M30_LINE_RE = re.compile(
    r"\[M30\].*?dt:(\S+\s+\S+).*?diffMid_Trend_M30:\[([^\]]+)\]"
)
# Actually, the [M30] lines don't have dt fields — they're timestamped by the log.
# Re-parse: the log timestamp IS the bar time.
M30_LINE_RE2 = re.compile(r"\[M30\].*?diffMid_Trend_M30:\[([^\]]+)\]")
H1_LINE_RE2 = re.compile(r"\[H1\].*?diffMid_Trend_H1:\[([^\]]+)\]")
H4_LINE_RE2 = re.compile(r"\[H4\].*?diffMid_Trend_H4:\[([^\]]+)\]")

# ── 1. Load deals and match to exit reasons ─────────────────────
with open(JSON_PATH) as f:
    data = json.load(f)

trade_deals = [d for d in data["table_deals"]
               if d["Type"] != "balance" and d["Direction"] in ("in", "out")]
in_deals = [d for d in trade_deals if d["Direction"] == "in"]
out_deals = [d for d in trade_deals if d["Direction"] == "out"]

per_trade = []
for i, (ind, outd) in enumerate(zip(in_deals, out_deals)):
    profit = float(outd["Profit"].replace(" ", ""))
    per_trade.append({
        "idx": i,
        "entry_time": datetime.strptime(ind["Time"], "%Y.%m.%d %H:%M:%S"),
        "profit": profit,
    })

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
                "rr": float(m.group(8)),
                "m30bbloc": int(m.group(9)),
                "m30_state": m.group(11),
                "h1bbloc": int(m.group(12)),
                "h4bbloc": int(m.group(13)),
            })
        m = EXIT_RE.search(line)
        if m:
            exit_log.append({
                "reason": m.group(1),
            })

# DUALTF: dt -> (h4_state, h1_state, m30_state)
dt_dual = {}
with open(LOG_PATH) as f:
    for line in f:
        m = DUALTF_RE.search(line)
        if m:
            dt = datetime.strptime(m.group(1), "%Y.%m.%d %H:%M:%S")
            dt_dual[dt] = (m.group(2), m.group(3), m.group(4))

# TF lines: parse log timestamp + diffMid_Trend
# We need to capture the log timestamp from each [M30]/[H1]/[H4] line.
# Strategy: track timestamps as we encounter lines; the log is chronological.
m30_trend_by_ts = []  # list of (datetime, first_value)
h1_trend_by_ts = []
h4_trend_by_ts = []

with open(LOG_PATH) as f:
    current_ts = None
    for line in f:
        # Extract timestamp from log line (first 19 chars: YYYY.MM.DD HH:MM:SS)
        ts_match = re.match(r"(\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2})", line)
        if ts_match:
            current_ts = datetime.strptime(ts_match.group(1), "%Y.%m.%d %H:%M:%S")

        m = M30_LINE_RE2.search(line)
        if m and current_ts:
            vals = [float(v) for v in m.group(1).split(",")]
            m30_trend_by_ts.append((current_ts, vals[0] if vals else None))

        m = H1_LINE_RE2.search(line)
        if m and current_ts:
            vals = [float(v) for v in m.group(1).split(",")]
            h1_trend_by_ts.append((current_ts, vals[0] if vals else None))

        m = H4_LINE_RE2.search(line)
        if m and current_ts:
            vals = [float(v) for v in m.group(1).split(",")]
            h4_trend_by_ts.append((current_ts, vals[0] if vals else None))

def find_nearest_trend(trend_list, target_dt, max_gap_seconds):
    """Find the nearest trend value at or before target_dt within max_gap."""
    best = None
    best_gap = None
    for ts, val in trend_list:
        gap = (target_dt - ts).total_seconds()
        if 0 <= gap <= max_gap_seconds:
            if best_gap is None or gap < best_gap:
                best = val
                best_gap = gap
    return best

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
        t["exit_reason"] = exit_log[i]["reason"]

# ── 4. Filter to TP_HIT + M15_REVERT only ───────────────────────
win_loss_trades = [
    t for t in per_trade
    if t.get("exit_reason") in ("TP_HIT", "M15_REVERT") and t.get("entry_log")
]
for t in win_loss_trades:
    t["is_winner"] = t["exit_reason"] == "TP_HIT"

n_win = sum(1 for t in win_loss_trades if t["is_winner"])
n_lose = sum(1 for t in win_loss_trades if not t["is_winner"])
print(f"Trade set: {n_win} TP_HIT winners + {n_lose} M15_REVERT losers = {len(win_loss_trades)}")
print(f"Excluded: {len(per_trade) - len(win_loss_trades)} trades "
      f"(TIMEOUT/SL_HIT — not clean win/loss contrast)")

# ── 5. Enrich with per-TF states and diffMid_trend ──────────────
trend_parsed = {"m30": 0, "h1": 0, "h4": 0}
trend_missing = {"m30": 0, "h1": 0, "h4": 0}

for t in win_loss_trades:
    el = t["entry_log"]
    t["dir"] = el["dir"]
    t["m30bbloc"] = el["m30bbloc"]
    t["h1bbloc"] = el["h1bbloc"]
    t["h4bbloc"] = el["h4bbloc"]
    t["rr"] = el["rr"]
    t["m30_state"] = el["m30_state"]
    t["entry_hour"] = el["dt"].hour

    # h4_state, h1_state from DUALTF at entry bar
    entry_dt = el["dt"]
    dual = dt_dual.get(entry_dt, None)
    if dual is None:
        for delta in [-15, 15, -30, 30]:
            check_min = max(0, min(59, entry_dt.minute + delta))
            check_dt = entry_dt.replace(minute=check_min)
            dual = dt_dual.get(check_dt, None)
            if dual:
                break
    if dual:
        t["h4_state"] = dual[0]
        t["h1_state"] = dual[1]
    else:
        t["h4_state"] = "MISSING"
        t["h1_state"] = "MISSING"

    # diffMid_trend from TF lines
    m30_val = find_nearest_trend(m30_trend_by_ts, entry_dt, max_gap_seconds=1800)
    h1_val = find_nearest_trend(h1_trend_by_ts, entry_dt, max_gap_seconds=3600)
    h4_val = find_nearest_trend(h4_trend_by_ts, entry_dt, max_gap_seconds=14400)

    t["dm_trend_m30"] = m30_val
    t["dm_trend_h1"] = h1_val
    t["dm_trend_h4"] = h4_val

    if m30_val is not None:
        trend_parsed["m30"] += 1
    else:
        trend_missing["m30"] += 1
    if h1_val is not None:
        trend_parsed["h1"] += 1
    else:
        trend_missing["h1"] += 1
    if h4_val is not None:
        trend_parsed["h4"] += 1
    else:
        trend_missing["h4"] += 1

# ── 6. Bucket diffMid_trend values ──────────────────────────────
# Bucket by sign: -1 (negative), 0 (zero), +1 (positive)
# Also magnitude: low (0-1), med (1-3), high (3+)
def trend_sign(v):
    if v is None:
        return "MISSING"
    elif v < 0:
        return "NEG"
    elif v == 0:
        return "ZERO"
    else:
        return "POS"

def trend_magnitude(v):
    if v is None:
        return "MISSING"
    av = abs(v)
    if av <= 1.0:
        return "LOW"
    elif av <= 3.0:
        return "MED"
    else:
        return "HIGH"

for t in win_loss_trades:
    for tf in ["m30", "h1", "h4"]:
        key = f"dm_trend_{tf}"
        t[f"dm_trend_{tf}_sign"] = trend_sign(t[key])
        t[f"dm_trend_{tf}_mag"] = trend_magnitude(t[key])

# ── 7. Separation stats ─────────────────────────────────────────
def win_rate(trades):
    """Win rate as float 0-1."""
    if not trades:
        return 0.0
    return sum(1 for t in trades if t["is_winner"]) / len(trades)

def quartiles(vals):
    """Return Q1, median, Q3 for a list of floats."""
    s = sorted(vals)
    n = len(s)
    if n == 0:
        return (None, None, None)
    def q(i):
        idx = i * (n - 1)
        lo = int(idx)
        hi = lo + 1
        if hi >= n:
            return s[-1]
        frac = idx - lo
        return s[lo] * (1 - frac) + s[hi] * frac
    return (round(q(0.25), 2), round(q(0.5), 2), round(q(0.75), 2))

def categorical_separation(feature_key, trades):
    """For a categorical feature, return per-category stats and spread.
    Also returns the best subset that meets the separation criterion (>=50% WR, n>=20)."""
    groups = defaultdict(list)
    for t in trades:
        val = t.get(feature_key, "MISSING")
        groups[val].append(t)

    results = {}
    best_separator = None  # (category, wr, n)
    for cat, grp in groups.items():
        wr = win_rate(grp)
        n = len(grp)
        results[cat] = {"n": n, "wr": round(wr * 100, 1)}
        if wr >= 0.50 and n >= 20 and best_separator is None:
            best_separator = (cat, round(wr * 100, 1), n)
        elif wr >= 0.50 and n >= 20 and best_separator:
            # Pick the one with highest WR, then highest n
            if (wr > best_separator[1] / 100) or (wr == best_separator[1] / 100 and n > best_separator[2]):
                best_separator = (cat, round(wr * 100, 1), n)

    wrs = [v["wr"] for v in results.values()]
    spread = round(max(wrs) - min(wrs), 1) if len(wrs) > 1 else 0.0
    return results, spread, best_separator

def numeric_separation(feature_key, trades):
    """For a numeric feature, return winner vs loser stats and best threshold separator."""
    win_vals = [t[feature_key] for t in trades if t["is_winner"] and t.get(feature_key) is not None]
    lose_vals = [t[feature_key] for t in trades if not t["is_winner"] and t.get(feature_key) is not None]

    win_mean = round(sum(win_vals) / len(win_vals), 2) if win_vals else None
    lose_mean = round(sum(lose_vals) / len(lose_vals), 2) if lose_vals else None
    gap = round(abs(win_mean - lose_mean), 2) if (win_mean is not None and lose_mean is not None) else None

    win_q = quartiles(win_vals) if win_vals else (None, None, None)
    lose_q = quartiles(lose_vals) if lose_vals else (None, None, None)

    # Try thresholds at quartile boundaries
    all_vals = sorted(set(win_vals + lose_vals))
    best_separator = None
    for threshold in all_vals:
        below = [t for t in trades if t.get(feature_key) is not None and t[feature_key] <= threshold]
        above = [t for t in trades if t.get(feature_key) is not None and t[feature_key] > threshold]
        for grp, label in [(below, f"<={threshold}"), (above, f">{threshold}")]:
            wr = win_rate(grp)
            if wr >= 0.50 and len(grp) >= 20:
                if best_separator is None or wr > best_separator[1] / 100 or (wr == best_separator[1] / 100 and len(grp) > best_separator[2]):
                    best_separator = (label, round(wr * 100, 1), len(grp))

    return {
        "win_mean": win_mean, "lose_mean": lose_mean, "gap": gap,
        "win_q": win_q, "lose_q": lose_q,
        "win_n": len(win_vals), "lose_n": len(lose_vals),
    }, best_separator

# ── 8. Define features for each ablation set ────────────────────
BASE_CATEGORICAL = ["dir", "m30_state", "h1_state", "h4_state"]
BASE_NUMERIC = ["m30bbloc", "h1bbloc", "h4bbloc", "rr", "entry_hour"]

TREND_CATEGORICAL = [
    "dm_trend_m30_sign", "dm_trend_h1_sign", "dm_trend_h4_sign",
    "dm_trend_m30_mag", "dm_trend_h1_mag", "dm_trend_h4_mag",
]
TREND_NUMERIC = ["dm_trend_m30", "dm_trend_h1", "dm_trend_h4"]

# ── 9. Compute separation for BASE set ──────────────────────────
base_results = {}
base_best_separator = None  # (feature, direction, wr, n)

for fk in BASE_CATEGORICAL:
    cats, spread, sep = categorical_separation(fk, win_loss_trades)
    base_results[fk] = {"type": "categorical", "cats": cats, "spread": spread, "separator": sep}
    if sep and (base_best_separator is None or sep[1] > base_best_separator[2] or
                (sep[1] == base_best_separator[2] and sep[2] > base_best_separator[3])):
        base_best_separator = (fk, sep[0], sep[1], sep[2])

for fk in BASE_NUMERIC:
    stats, sep = numeric_separation(fk, win_loss_trades)
    base_results[fk] = {"type": "numeric", "stats": stats, "separator": sep}
    if sep and (base_best_separator is None or sep[1] > base_best_separator[2] or
                (sep[1] == base_best_separator[2] and sep[2] > base_best_separator[3])):
        base_best_separator = (fk, sep[0], sep[1], sep[2])

# ── 10. Compute separation for BASE + TREND set ─────────────────
all_results = dict(base_results)
all_best_separator = None

for fk in TREND_CATEGORICAL:
    cats, spread, sep = categorical_separation(fk, win_loss_trades)
    all_results[fk] = {"type": "categorical", "cats": cats, "spread": spread, "separator": sep}
    if sep and (all_best_separator is None or sep[1] > all_best_separator[2] or
                (sep[1] == all_best_separator[2] and sep[2] > all_best_separator[3])):
        all_best_separator = (fk, sep[0], sep[1], sep[2])

for fk in TREND_NUMERIC:
    stats, sep = numeric_separation(fk, win_loss_trades)
    all_results[fk] = {"type": "numeric", "stats": stats, "separator": sep}
    if sep and (all_best_separator is None or sep[1] > all_best_separator[2] or
                (sep[1] == all_best_separator[2] and sep[2] > all_best_separator[3])):
        all_best_separator = (fk, sep[0], sep[1], sep[2])

# Also check: does the TREND set have a best separator that BASE doesn't?
# Compare: is all_best_separator better than base_best_separator?
trend_only_improvement = False
if all_best_separator and not base_best_separator:
    trend_only_improvement = True
elif all_best_separator and base_best_separator:
    if (all_best_separator[2] > base_best_separator[2]) or \
       (all_best_separator[2] == base_best_separator[2] and all_best_separator[3] > base_best_separator[3]):
        if all_best_separator[0] not in BASE_CATEGORICAL + BASE_NUMERIC:
            trend_only_improvement = True

# ── 11. Verdicts ────────────────────────────────────────────────
# ABLATION verdict
if trend_only_improvement:
    ablation_verdict = "BB_DIFFMID_TREND ADDS VALUE"
    ablation_detail = (f"Trend features isolate a >=50% WR subset at n>=20 that no base feature achieves: "
                       f"{all_best_separator[0]}={all_best_separator[1]} "
                       f"(WR={all_best_separator[2]}%, n={all_best_separator[3]})")
else:
    ablation_verdict = "BB_DIFFMID_TREND REDUNDANT"
    ablation_detail = (f"No trend feature yields a >=50% WR subset at n>=20 unmatched by base features. "
                       f"Base best: {base_best_separator[0]}={base_best_separator[1]} "
                       f"(WR={base_best_separator[2]}%, n={base_best_separator[3]})"
                       if base_best_separator else "Base has no separator >=50%/n>=20.")

# OVERALL salvage verdict
if all_best_separator:
    salvage_verdict = "SEPARABLE"
    salvage_detail = (f"{all_best_separator[0]}={all_best_separator[1]} yields "
                      f"WR={all_best_separator[2]}% at n={all_best_separator[3]}")
else:
    salvage_verdict = "NOT-SEPARABLE"
    salvage_detail = ("No entry-time feature in either set isolates a >=50% win-rate subset at n>=20. "
                      "Winners and losers are indistinguishable at entry time.")

# ── 12. Print summary ───────────────────────────────────────────
print(f"\n{'='*60}")
print(f"diffMid_Trend parse status:")
for tf in ["m30", "h1", "h4"]:
    print(f"  {tf}: parsed={trend_parsed[tf]}, missing={trend_missing[tf]}")

print(f"\nBASE best separator: {base_best_separator}")
print(f"BASE+TREND best separator: {all_best_separator}")

print(f"\nAblation verdict: {ablation_verdict}")
print(f"  {ablation_detail}")
print(f"\nSalvage verdict: {salvage_verdict}")
print(f"  {salvage_detail}")

print(f"\n--- Categorical separation (spread) ---")
for fk in BASE_CATEGORICAL:
    r = base_results[fk]
    print(f"  {fk}: spread={r['spread']}%, sep={r['separator']}")
    for cat, v in r["cats"].items():
        print(f"    {cat}: n={v['n']}, WR={v['wr']}%")

for fk in TREND_CATEGORICAL:
    r = all_results[fk]
    print(f"  {fk}: spread={r['spread']}%, sep={r['separator']}")
    for cat, v in r["cats"].items():
        print(f"    {cat}: n={v['n']}, WR={v['wr']}%")

print(f"\n--- Numeric separation (gap) ---")
for fk in BASE_NUMERIC:
    r = base_results[fk]
    s = r["stats"]
    print(f"  {fk}: win_mean={s['win_mean']}, lose_mean={s['lose_mean']}, gap={s['gap']}, "
          f"sep={r['separator']}")

for fk in TREND_NUMERIC:
    r = all_results[fk]
    s = r["stats"]
    print(f"  {fk}: win_mean={s['win_mean']}, lose_mean={s['lose_mean']}, gap={s['gap']}, "
          f"sep={r['separator']}")

# ── 13. Append section to report ────────────────────────────────
with open(REPORT_PATH, "r", encoding="utf-8") as f:
    existing = f.read()

if "## Winner-vs-loser entry separation" in existing:
    print(f"\nSection already exists in {REPORT_PATH} — skipping append.")
else:
    md = []
    md.append("")
    md.append("## Winner-vs-loser entry separation (with BB_diffmid_trend ablation)")
    md.append("")
    md.append(
        "45 TP_HIT winners vs 152 M15_REVERT losers (197 trades). "
        "TIMEOUT (8) and SL_HIT (9) excluded — not clean win/loss contrast.\n"
        "A feature separates if any category/threshold yields WR >= 50% at n >= 20.\n"
        "Two feature sets: BASE (dir, m30bbloc, h1bbloc, h4bbloc, rr, h4_state, h1_state, m30_state, entry_hour) "
        "and BASE + diffMid_trend (diffMid_Trend_M30/H1/H4 as sign and magnitude)."
    )
    md.append("")

    # Parse status
    md.append("### diffMid_Trend Parse Status")
    md.append("")
    md.append("| TF | Parsed | Missing |")
    md.append("|----|--------|---------|")
    for tf in ["m30", "h1", "h4"]:
        tf_label = tf.upper()
        md.append(f"| {tf_label} | {trend_parsed[tf]} | {trend_missing[tf]} |")
    md.append("")

    # Categorical separation
    md.append("### Categorical Feature Separation")
    md.append("")
    md.append("| Feature | Type | Spread (%) | Best Category | WR (%) | n | Separator (>=50%/n>=20)? |")
    md.append("|---------|------|------------|---------------|--------|---|-------------------------|")

    all_cat_features = BASE_CATEGORICAL + TREND_CATEGORICAL
    for fk in all_cat_features:
        r = all_results[fk]
        sep = r["separator"]
        if sep:
            best_cat = sep[0]
            best_wr = sep[1]
            best_n = sep[2]
            sep_str = f"**{best_cat} (WR={best_wr}%, n={best_n})**"
        else:
            # Find category with highest WR regardless of threshold
            best_cat = max(r["cats"], key=lambda c: r["cats"][c]["wr"])
            best_wr = r["cats"][best_cat]["wr"]
            best_n = r["cats"][best_cat]["n"]
            sep_str = f"{best_cat} (WR={best_wr}%, n={best_n}) — below threshold"
        is_base = "no" if fk in TREND_CATEGORICAL else "yes"
        md.append(f"| {fk} | cat | {r['spread']} | {best_cat} | {best_wr} | {best_n} | {sep_str} |")
    md.append("")

    # Numeric separation
    md.append("### Numeric Feature Separation")
    md.append("")
    md.append("| Feature | Win Mean | Lose Mean | Gap | Separator (>=50%/n>=20)? |")
    md.append("|---------|----------|-----------|-----|-------------------------|")

    all_num_features = BASE_NUMERIC + TREND_NUMERIC
    for fk in all_num_features:
        r = all_results[fk]
        s = r["stats"]
        wm = s["win_mean"] if s["win_mean"] is not None else "—"
        lm = s["lose_mean"] if s["lose_mean"] is not None else "—"
        gp = s["gap"] if s["gap"] is not None else "—"
        sep = r["separator"]
        if sep:
            sep_str = f"**{sep[0]} (WR={sep[1]}%, n={sep[2]})**"
        else:
            sep_str = "none"
        md.append(f"| {fk} | {wm} | {lm} | {gp} | {sep_str} |")
    md.append("")

    # Ablation verdict
    md.append("### Ablation Verdict — Does BB_diffmid_trend add value?")
    md.append("")
    md.append(f"**{ablation_verdict}**")
    md.append("")
    md.append(f"{ablation_detail}")
    md.append("")
    md.append("| | Best Separator | WR (%) | n |")
    md.append("|---|---|---|---|")
    if base_best_separator:
        md.append(f"| BASE only | {base_best_separator[0]}={base_best_separator[1]} | {base_best_separator[2]} | {base_best_separator[3]} |")
    else:
        md.append("| BASE only | none | — | — |")
    if all_best_separator:
        md.append(f"| BASE + trend | {all_best_separator[0]}={all_best_separator[1]} | {all_best_separator[2]} | {all_best_separator[3]} |")
    else:
        md.append("| BASE + trend | none | — | — |")
    md.append("")

    # Overall salvage verdict
    md.append("### Overall Salvage Verdict")
    md.append("")
    md.append(f"**{salvage_verdict}**")
    md.append("")
    md.append(f"{salvage_detail}")
    md.append("")

    # Limitations
    md.append("### Limitations")
    md.append("")
    md.append("- **In-sample post-hoc:** Any separator identified here is in-sample — selected on the same data it was evaluated on. Overfitting is possible. A forward test on a fresh data window is required before trusting any entry filter.")
    md.append("- **Win/loss by realized exit:** TP_HIT = realized win; M15_REVERT = realized loss. A REVERT exit does not mean the trade would have been a loss had it been held — and a TP_HIT does not mean the trade would not have reverted later. Exit reason ≠ ultimate outcome.")
    md.append("- **Single-feature only:** This tests each feature in isolation. Multi-feature combos (e.g., h4_state=F AND dm_trend_h4_sign=POS) may separate better — but testing all combos is a different analysis.")
    md.append("- **Sub-n=20 subsets not promoted:** Categories with WR >= 50% but n < 20 exist and are reported but not promoted — too small to trade.")
    md.append("")

    with open(REPORT_PATH, "a", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")

    print(f"\nSection appended to {REPORT_PATH}")
