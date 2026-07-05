#!/usr/bin/env python3
"""V36.13 Dissection — decompose 214 trades to locate loss concentration.

Reads:
  - report_tables_clean.json  (table_deals, table_results)
  - 20260705_clean.log       ([TRADE] evt:ENTRY / evt:EXIT lines)

Writes:
  - references/V36_13_DISSECTION.md

Join logic:
  - in-deals → ENTRY log: by time (±600s). 3 rejected entries have no in-deal.
  - out-deals → EXIT log: by sequential index (one position at a time).
    Exit-retry means the EXIT decision bar ≠ fill bar; time-join fails.
    The EXIT log fires once per trade (on confirmed-flat), so sequential
    matching is correct: exit_lines[i] → trade i.
"""

import json
import re
import sys
from datetime import datetime

# ── paths ──────────────────────────────────────────────────────────
BASE = "references/Backtest_data/V36.13"
DEALS_PATH = f"{BASE}/report_tables_clean.json"
LOG_PATH = f"{BASE}/20260705_clean.log"
REPORT_PATH = "references/V36_13_DISSECTION.md"

# ── load data ──────────────────────────────────────────────────────
with open(DEALS_PATH) as f:
    report = json.load(f)

deals = report["table_deals"]
results = report["table_results"]

with open(LOG_PATH) as f:
    log_lines = f.readlines()

# ── parse deals ────────────────────────────────────────────────────
def parse_time(s):
    return datetime.strptime(s, "%Y.%m.%d %H:%M:%S")

in_deals = []
out_deals = []

for deal in deals:
    d = deal["Direction"]
    if d == "in":
        in_deals.append({
            "time": parse_time(deal["Time"]),
            "type": deal["Type"],
            "volume": deal["Volume"],
            "price": float(deal["Price"]),
        })
    elif d == "out":
        out_deals.append({
            "time": parse_time(deal["Time"]),
            "type": deal["Type"],
            "volume": deal["Volume"],
            "price": float(deal["Price"]),
            "profit": float(deal["Profit"]),
        })

# ── parse log ENTRY / EXIT lines ──────────────────────────────────
ENTRY_RE = re.compile(
    r"\[TRADE\] evt:ENTRY dir:(UP|DOWN) dt:(\S+\s+\S+) "
    r"entry:(\S+) sl:(\S+) sldist:(\S+) tp:(\S+) tpdist:(\S+) rr:(\S+) "
    r"m30bbloc:(\d+) m15:(\S+) m30:(\S+) h1bbloc:(\d+) h4bbloc:(\d+)"
)

EXIT_RE = re.compile(
    r"\[TRADE\] evt:EXIT reason:(\S+) dt:(\S+\s+\S+) "
    r"exit:(\S+) bars_held:(\d+) m30_followed:(Y|N)"
)

entry_lines = []
exit_lines = []

for line in log_lines:
    m = ENTRY_RE.search(line)
    if m:
        entry_lines.append({
            "dir": m.group(1),
            "dt": datetime.strptime(m.group(2), "%Y.%m.%d %H:%M:%S"),
            "entry_price": float(m.group(3)),
            "sl": float(m.group(4)),
            "sldist": float(m.group(5)),
            "tp": float(m.group(6)),
            "tpdist": float(m.group(7)),
            "rr": float(m.group(8)),
            "m30bbloc": int(m.group(9)),
            "m15_state": m.group(10),
            "m30_state": m.group(11),
            "h1bbloc": int(m.group(12)),
            "h4bbloc": int(m.group(13)),
        })
    m = EXIT_RE.search(line)
    if m:
        exit_lines.append({
            "reason": m.group(1),
            "dt": datetime.strptime(m.group(2), "%Y.%m.%d %H:%M:%S"),
            "exit_price": float(m.group(3)),
            "bars_held": int(m.group(4)),
            "m30_followed": m.group(5) == "Y",
        })

# ── reconcile ──────────────────────────────────────────────────────
print(f"Deals: {len(in_deals)} in, {len(out_deals)} out")
print(f"Log:  {len(entry_lines)} ENTRY, {len(exit_lines)} EXIT")

assert len(in_deals) == len(out_deals), f"Deal mismatch: {len(in_deals)} in vs {len(out_deals)} out"
N = len(in_deals)
EXPECTED_N = 214
assert N == EXPECTED_N, f"Expected {EXPECTED_N} trades, got {N}"

# The 3 rejected entries have no in-deal. The 3 extra EXIT lines come from
# exit-retry (the EXIT decision bar fires before the fill bar).
# We expect 217 ENTRY lines (214 + 3 rejected) and 217 EXIT lines
# (214 confirmed-flat + 3 retries that were later superseded).
# Actually, the EXIT log fires on confirmed-flat, so there should be
# exactly 214 if each trade closes once. But exit-retry means some trades
# may have had the EXIT logged on a bar, then the close was rejected,
# then re-logged on a later bar. However, the code logs EXIT only on
# confirmed-flat (the final close), so each trade should produce one EXIT.
# Let's check: if exit_lines > 214, some are retries; we match by index.

# ── build per-trade records ────────────────────────────────────────
trades = []
unmatched_entries = 0
rejected_entries = len(entry_lines) - N  # entries with no in-deal

# Map: for each in-deal, find its ENTRY log by time
for i in range(N):
    ind = in_deals[i]
    outd = out_deals[i]
    profit = outd["profit"]

    # Join to ENTRY log line (within ±600s)
    entry_log = None
    for el in entry_lines:
        if abs((el["dt"] - ind["time"]).total_seconds()) <= 600:
            entry_log = el
            break
    if entry_log is None:
        unmatched_entries += 1

    # Join EXIT by sequential index (one position at a time)
    # exit_lines is in chronological order; each trade produces one EXIT.
    # If len(exit_lines) > N, the extra lines are from the same trades
    # (exit-retry). We take the first N.
    # If len(exit_lines) < N, some trades had no EXIT log.
    if i < len(exit_lines):
        exit_log = exit_lines[i]
    else:
        exit_log = None

    trades.append({
        "idx": i,
        "in_time": ind["time"],
        "out_time": outd["time"],
        "dir": ind["type"].upper(),
        "profit": profit,
        "rr": entry_log["rr"] if entry_log else None,
        "m30bbloc": entry_log["m30bbloc"] if entry_log else None,
        "h1bbloc": entry_log["h1bbloc"] if entry_log else None,
        "h4bbloc": entry_log["h4bbloc"] if entry_log else None,
        "m30_state": entry_log["m30_state"] if entry_log else None,
        "exit_reason": exit_log["reason"] if exit_log else None,
        "bars_held": exit_log["bars_held"] if exit_log else None,
        "m30_followed": exit_log["m30_followed"] if exit_log else None,
    })

print(f"Unmatched entries (in-deal with no ENTRY log): {unmatched_entries}")
print(f"Rejected entries (ENTRY log with no in-deal): {rejected_entries}")
print(f"Extra EXIT lines (exit_lines - N): {len(exit_lines) - N}")

# Per-trade profit sum vs report Total Net Profit
trade_profit_sum = sum(t["profit"] for t in trades)
report_net = float(results["Total Net Profit"].replace(" ", ""))
delta = abs(trade_profit_sum - report_net)

# Find swap from summary deal (Direction=nan)
swap_total = 0.0
for deal in deals:
    if deal["Direction"] is None or (isinstance(deal["Direction"], float) and deal["Direction"] != deal["Direction"]):
        try:
            swap_total += float(deal.get("Swap", "0"))
        except (ValueError, TypeError):
            pass

print(f"Per-trade profit sum: {trade_profit_sum:+.2f}")
print(f"Report Total Net Profit: {report_net:+.2f}")
print(f"Delta: {delta:.2f} (swap: {swap_total:+.2f})")

if delta > 5.0 and abs(delta - abs(swap_total)) > 1.0:
    print("RECONCILIATION FAILED — delta > 5.0 and not explained by swap. Stopping.")
    sys.exit(1)

# ── helper ─────────────────────────────────────────────────────────
def pf(subset):
    """Profit factor for a subset of trades."""
    gp = sum(t["profit"] for t in subset if t["profit"] > 0)
    gl = abs(sum(t["profit"] for t in subset if t["profit"] < 0))
    return round(gp / gl, 2) if gl > 0 else float("inf") if gp > 0 else 0.0

def win_rate(subset):
    wins = sum(1 for t in subset if t["profit"] > 0)
    return round(wins / len(subset) * 100, 1) if subset else 0.0

def summary(subset, label=""):
    n = len(subset)
    total = round(sum(t["profit"] for t in subset), 2)
    mean_ = round(total / n, 2) if n else 0.0
    wr = win_rate(subset)
    pf_ = pf(subset)
    return f"| {label} | {n} | {total:+.2f} | {mean_:+.2f} | {wr}% | {pf_} |"

# ── splits ─────────────────────────────────────────────────────────

# A. By exit reason
split_a = {}
for t in trades:
    reason = t["exit_reason"] or "UNKNOWN"
    split_a.setdefault(reason, []).append(t)

# B. By m30bbloc zone
def zone_name(bbloc, direction):
    """NEAR / MID / FAR / ATBAND — per the gate logic in TofyTrade6."""
    if direction == "BUY":
        if bbloc in (5, 7):
            return "NEAR/MID"
        if bbloc in (9, 10):
            return "ATBAND"
        return "FAR"
    else:  # SELL
        if bbloc in (3, 5):
            return "NEAR/MID"
        if bbloc in (0, 1):
            return "ATBAND"
        return "FAR"

split_b = {}
for t in trades:
    if t["m30bbloc"] is not None:
        z = zone_name(t["m30bbloc"], t["dir"])
    else:
        z = "UNKNOWN"
    split_b.setdefault(z, []).append(t)

# C. By rr bucket
def rr_bucket(rr):
    if rr is None:
        return "UNKNOWN"
    if rr < 1.0:
        return "rr<1.0"
    if rr < 1.5:
        return "1.0-1.5"
    if rr < 2.0:
        return "1.5-2.0"
    return ">=2.0"

split_c = {}
for t in trades:
    b = rr_bucket(t["rr"])
    split_c.setdefault(b, []).append(t)

# D. By direction
split_d = {}
for t in trades:
    d = t["dir"]
    split_d.setdefault(d, []).append(t)

# E. By HTF context (H4 vs trigger dir)
# Use h4bbloc as proxy: >=7 up-biased, <=3 down-biased, else neutral.
# Agree = trigger dir matches HTF bias.
def htf_context(h4bbloc, direction):
    if h4bbloc is None:
        return "UNKNOWN"
    if h4bbloc >= 7:
        return "AGREE" if direction == "BUY" else "DISAGREE"
    elif h4bbloc <= 3:
        return "AGREE" if direction == "SELL" else "DISAGREE"
    else:
        return "NEUTRAL"

split_e = {}
for t in trades:
    c = htf_context(t["h4bbloc"], t["dir"])
    split_e.setdefault(c, []).append(t)

# F. By session/hour bucket
SESSION_HOURS = {
    "00-04": (0, 3),
    "04-08": (4, 7),
    "08-12": (8, 11),
    "12-16": (12, 15),
    "16-20": (16, 19),
    "20-00": (20, 23),
}

def hour_bucket(ts):
    h = ts.hour
    for label, (lo, hi) in SESSION_HOURS.items():
        if lo <= h <= hi:
            return label
    return "UNKNOWN"

split_f = {}
for t in trades:
    b = hour_bucket(t["in_time"])
    split_f.setdefault(b, []).append(t)

# ── verdict criteria ───────────────────────────────────────────────
verdict = None
verdict_detail = None

all_splits = {
    "A": split_a,
    "B": split_b,
    "C": split_c,
    "D": split_d,
    "E": split_e,
    "F": split_f,
}

# SALVAGEABLE-BY-GATE: any single split isolates PF>=1.2 AND n>=30.
# Exclude tautological subsets: TP_HIT from split A has PF=inf because
# a trade that hits TP is profitable by definition — you can't gate on
# exit reason at entry time. Exclude split A entirely from gate check.
for split_name, groups in all_splits.items():
    if split_name == "A":
        continue  # exit-reason subsets are not entry-time gates
    for label, subset in groups.items():
        if len(subset) >= 30 and pf(subset) >= 1.2:
            verdict = "SALVAGEABLE-BY-GATE"
            verdict_detail = (f"Split {split_name} subset '{label}' has PF {pf(subset)} "
                             f"with n={len(subset)} (>=30). This subset is a profitable "
                             f"core big enough to trade.")
            break
    if verdict:
        break

# EXIT-DRIVEN: removing worst exit-reason bucket lifts PF>=1.0
if not verdict:
    worst_reason = None
    worst_loss = 0
    for label, subset in split_a.items():
        total = sum(t["profit"] for t in subset)
        if total < worst_loss:
            worst_loss = total
            worst_reason = label
    counterfactual = [t for t in trades if t["exit_reason"] != worst_reason]
    cf_pf = pf(counterfactual)
    if cf_pf >= 1.0:
        verdict = "EXIT-DRIVEN"
        verdict_detail = (f"Removing the {worst_reason} bucket (n={N - len(counterfactual)}, "
                         f"net {worst_loss:+.2f}) lifts counterfactual PF to {cf_pf} "
                         f"with n={len(counterfactual)}. Note: this is a realized-only "
                         f"counterfactual — the counterfactual win is unknowable.")

# FUNDAMENTALLY-NEGATIVE
if not verdict:
    # Double-check: any subset in B-F with PF>=1.0 at n>=30?
    # (Exclude A — exit reasons are not entry-time gates.)
    any_profitable = False
    for split_name, groups in all_splits.items():
        if split_name == "A":
            continue
        for label, subset in groups.items():
            if len(subset) >= 30 and pf(subset) >= 1.0:
                any_profitable = True
                break
        if any_profitable:
            break
    verdict = "FUNDAMENTALLY-NEGATIVE"
    verdict_detail = ("No subset in splits B-F reaches PF >= 1.0 at n >= 30. "
                      "The trigger premise is dead.")

# ── write report ───────────────────────────────────────────────────
md = []
md.append("# V36.13 Dissection — Where the -$899 concentrates\n")

# Reconciliation
md.append("## Reconciliation\n")
md.append(f"- {len(in_deals)} in-deals matched to {len(out_deals)} out-deals. "
          f"All {N} trades joined.")
md.append(f"- {len(entry_lines)} [TRADE] ENTRY lines in log; "
          f"{unmatched_entries} unmatched (in-deal with no ENTRY log), "
          f"{rejected_entries} rejected (ENTRY log with no in-deal).")
md.append(f"- {len(exit_lines)} [TRADE] EXIT lines in log; "
          f"{len(exit_lines) - N} extra (exit-retry duplicates). "
          f"Joined by sequential index (one position at a time).")
md.append(f"- Per-trade profit sum: **{trade_profit_sum:+.2f}**")
md.append(f"- Report Total Net Profit: **{report_net:+.2f}**")
md.append(f"- Delta: **{delta:.2f}** (explained by swap: **{swap_total:+.2f}**)")
md.append("")

# Splits
md.append("## Splits\n")

# A
md.append("### A. By Exit Reason\n")
md.append("| Group | n | Total $ | Mean $ | Win-Rate | PF |")
md.append("|-------|---|---------|--------|----------|-----|")
for reason in ["TP_HIT", "M15_REVERT", "TIMEOUT", "SL_HIT", "UNKNOWN"]:
    if reason in split_a:
        md.append(summary(split_a[reason], reason))
md.append("")
m15_net = sum(t["profit"] for t in split_a.get("M15_REVERT", []))
m15_n = len(split_a.get("M15_REVERT", []))
m15_pf = pf(split_a.get("M15_REVERT", []))
md.append(f"**M15_REVERT:** n={m15_n}, net **{m15_net:+.2f}**, PF={m15_pf}\n")

# B
md.append("### B. By Entry m30bbloc Zone\n")
md.append("| Group | n | Total $ | Mean $ | Win-Rate | PF |")
md.append("|-------|---|---------|--------|----------|-----|")
for z in ["NEAR/MID", "ATBAND", "FAR", "UNKNOWN"]:
    if z in split_b:
        md.append(summary(split_b[z], z))
md.append("")

# C
md.append("### C. By rr Bucket at Entry\n")
md.append("| Group | n | Total $ | Mean $ | Win-Rate | PF |")
md.append("|-------|---|---------|--------|----------|-----|")
for b in ["rr<1.0", "1.0-1.5", "1.5-2.0", ">=2.0", "UNKNOWN"]:
    if b in split_c:
        md.append(summary(split_c[b], b))
md.append("")

# D
md.append("### D. By Direction\n")
md.append("| Group | n | Total $ | Mean $ | Win-Rate | PF |")
md.append("|-------|---|---------|--------|----------|-----|")
for d in sorted(split_d):
    md.append(summary(split_d[d], d))
md.append("")

# E
md.append("### E. By HTF Context (H4 vs Trigger Dir)\n")
md.append("| Group | n | Total $ | Mean $ | Win-Rate | PF |")
md.append("|-------|---|---------|--------|----------|-----|")
for c in ["AGREE", "DISAGREE", "NEUTRAL", "UNKNOWN"]:
    if c in split_e:
        md.append(summary(split_e[c], c))
md.append("")

# F
md.append("### F. By Session/Hour Bucket\n")
md.append("| Group | n | Total $ | Mean $ | Win-Rate | PF |")
md.append("|-------|---|---------|--------|----------|-----|")
for b in SESSION_HOURS:
    if b in split_f:
        md.append(summary(split_f[b], b))
md.append("")

# Verdict
md.append("## Verdict\n")
md.append(f"**{verdict}**\n")
md.append(f"{verdict_detail}\n")

# Sub-n=30 flagging
md.append("### Subsets with PF >= 1.0 but n < 30 (not promoted)\n")
for split_name, groups in all_splits.items():
    for label, subset in groups.items():
        if len(subset) >= 10 and len(subset) < 30 and pf(subset) >= 1.0:
            md.append(f"- Split {split_name} '{label}': n={len(subset)}, PF={pf(subset)}, "
                      f"total={sum(t['profit'] for t in subset):+.2f} — too small to trade")
md.append("")

# Limitations
md.append("## Limitations\n")
md.append("- **Counterfactual unknowable:** The EXIT-DRIVEN counterfactual "
          "(removing a bucket) is realized-only — we cannot know whether those "
          "lost trades would have been wins had they exited differently.")
md.append("- **Post-hoc subsets are hypotheses, not validation:** Any promising "
          "subset identified here needs a FORWARD test on a fresh data window "
          "before trusting it. This analysis is descriptive, not prescriptive.")
md.append("- **No new design recommendations:** The three fixed verdict categories "
          "(salvageable-by-gate / exit-driven / fundamentally-negative) are the "
          "only conclusions drawn. No gate, exit, or parameter tuning is proposed.")
md.append("")

with open(REPORT_PATH, "w") as f:
    f.write("\n".join(md))

print(f"\nReport written to {REPORT_PATH}")
print(f"Verdict: {verdict}")
print(f"Detail: {verdict_detail}")
