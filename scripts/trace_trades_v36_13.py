#!/usr/bin/env python3
"""V36.13 Trade Tracer — bar-by-bar decision traces for 5 trades.

Reads:
  - references/Backtest_data/V36.13/20260705_clean.log

Writes:
  - references/TRADE_TRACE_V36_13.md

Selects 5 trades: 1 TP_HIT, 2 M15_REVERT, 1 TIMEOUT, 1 SL_HIT.
For each, traces from 3 bars before entry to the exit bar.
"""

import re
import sys
from datetime import datetime, timedelta

LOG_PATH = "references/Backtest_data/V36.13/20260705_clean.log"
REPORT_PATH = "references/TRADE_TRACE_V36_13.md"

# ── regexes ────────────────────────────────────────────────────────
DUALTF_RE = re.compile(
    r"\[DUALTF\] SIG:DUALTF evt:BAR dt:(\S+\s+\S+) "
    r"d1:stg:(\d+) d1:mid:(\d+) d1:ud:(\d+) d1:state:(\S+) d1bbloc:(-?\d+) "
    r"h4:stg:(\d+) h4:mid:(\d+) h4:ud:(\d+) h4:state:(\S+) h4bbloc:(-?\d+) "
    r"h1:stg:(\d+) h1:mid:(\d+) h1:ud:(\d+) h1:state:(\S+) h1bbloc:(-?\d+) "
    r"m30:stg:(\d+) m30:mid:(\d+) m30:ud:(\d+) m30:state:(\S+) m30bbloc:(-?\d+) "
    r"m15:stg:(\d+) m15:mid:(\d+) m15:ud:(\d+) m15:state:(\S+) m15bbloc:(-?\d+)"
)

ENTRY_RE = re.compile(
    r"\[TRADE\] evt:ENTRY dir:(UP|DOWN) dt:(\S+\s+\S+) "
    r"entry:(\S+) sl:(\S+) sldist:(\S+) tp:(\S+) tpdist:(\S+) rr:(\S+) "
    r"m30bbloc:(\d+) m15:(\S+) m30:(\S+) h1bbloc:(\d+) h4bbloc:(\d+)"
)

EXIT_RE = re.compile(
    r"\[TRADE\] evt:EXIT reason:(\S+) dt:(\S+\s+\S+) "
    r"exit:(\S+) bars_held:(\d+) m30_followed:(Y|N)"
)

# ── parse ──────────────────────────────────────────────────────────
dualtf_rows = []
entry_lines = []
exit_lines = []

with open(LOG_PATH) as f:
    for line in f:
        m = DUALTF_RE.search(line)
        if m:
            dualtf_rows.append({
                "dt": datetime.strptime(m.group(1), "%Y.%m.%d %H:%M:%S"),
                "d1_state": m.group(5),
                "d1bbloc": int(m.group(6)),
                "h4_state": m.group(10),
                "h4bbloc": int(m.group(11)),
                "h1_state": m.group(15),
                "h1bbloc": int(m.group(16)),
                "m30_state": m.group(20),
                "m30bbloc": int(m.group(21)),
                "m15_state": m.group(25),
                "m15bbloc": int(m.group(26)),
            })

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

print(f"Parsed: {len(dualtf_rows)} DUALTF rows, {len(entry_lines)} ENTRY, "
      f"{len(exit_lines)} EXIT")

# ── build per-trade records ────────────────────────────────────────
trades = []
used_entries = set()

for xi, exit_ in enumerate(exit_lines):
    best_ei = None
    best_diff = None
    for ei, entry in enumerate(entry_lines):
        if ei in used_entries:
            continue
        if entry["dt"] > exit_["dt"]:
            continue
        diff = (exit_["dt"] - entry["dt"]).total_seconds()
        if best_diff is None or diff < best_diff:
            best_ei = ei
            best_diff = diff
    if best_ei is not None:
        trades.append({"entry": entry_lines[best_ei], "exit": exit_})
        used_entries.add(best_ei)

print(f"Paired {len(trades)} trades")

# ── select 5 trades ────────────────────────────────────────────────
by_reason = {}
for t in trades:
    r = t["exit"]["reason"]
    by_reason.setdefault(r, []).append(t)

print(f"By exit reason: { {k: len(v) for k, v in by_reason.items()} }")

selected = []
if by_reason.get("TP_HIT"):
    selected.append(by_reason["TP_HIT"][0])
if by_reason.get("M15_REVERT"):
    selected.append(by_reason["M15_REVERT"][0])
    for t in by_reason["M15_REVERT"][1:]:
        if (t["entry"]["dt"] - selected[-1]["entry"]["dt"]).total_seconds() > 86400:
            selected.append(t)
            break
    else:
        selected.append(by_reason["M15_REVERT"][1])
if by_reason.get("TIMEOUT"):
    selected.append(by_reason["TIMEOUT"][0])
if by_reason.get("SL_HIT"):
    selected.append(by_reason["SL_HIT"][0])

print(f"Selected {len(selected)} trades:")
for t in selected:
    print(f"  {t['entry']['dt']} {t['entry']['dir']} -> {t['exit']['reason']} "
          f"bars={t['exit']['bars_held']}")

# ── build dt->DUALTF lookup ────────────────────────────────────────
dt_to_row = {row["dt"]: row for row in dualtf_rows}

# ── zone/gate helpers ─────────────────────────────────────────────
def zone_name(bbloc, direction):
    if direction == "UP":
        if bbloc in (5, 7): return "NEAR/MID"
        if bbloc in (9, 10): return "ATBAND"
        return "FAR"
    else:
        if bbloc in (3, 5): return "NEAR/MID"
        if bbloc in (0, 1): return "ATBAND"
        return "FAR"

def gate_result(bbloc, direction):
    if direction == "UP":
        if bbloc in (5, 7): return "PASS"
        if bbloc in (9, 10): return "SKIP_ATBAND"
        return "SKIP_FAR"
    else:
        if bbloc in (3, 5): return "PASS"
        if bbloc in (0, 1): return "SKIP_ATBAND"
        return "SKIP_FAR"

# ── write report ───────────────────────────────────────────────────
md = []
md.append("# V36.13 Trade Traces - Bar-by-Bar Decision Traces\n")
md.append("> **VALIDATION USE:** For each trade, confirm the code's entry/exit "
          "decisions match the intended design rules. A mismatch = implementation "
          "bug; a match + loss = design premise issue.\n")

for idx, trade in enumerate(selected, 1):
    entry = trade["entry"]
    exit_ = trade["exit"]
    trigger_state = "F" if entry["dir"] == "UP" else "R"

    md.append(f"## Trade {idx}: {entry['dir']} - {exit_['reason']}\n")
    md.append(f"**Entry:** {entry['dt']} | **Exit:** {exit_['dt']} | "
              f"**Bars held:** {exit_['bars_held']} | "
              f"**RR:** {entry['rr']:.2f}\n")
    md.append(f"**SL:** {entry['sl']:.2f} (opposite M15 band) | "
              f"**TP:** {entry['tp']:.2f} (M30 band) | "
              f"**m30bbloc at entry:** {entry['m30bbloc']} "
              f"({zone_name(entry['m30bbloc'], entry['dir'])})\n")

    # Collect bars: filter DUALTF rows to window [entry-3, exit]
    start_dt = entry["dt"] - timedelta(minutes=15 * 3)
    end_dt = exit_["dt"]

    window_rows = [r for r in dualtf_rows if start_dt <= r["dt"] <= end_dt]

    m30_followed = False
    bars_count = 0

    # Find prev m15 state (1 bar before entry)
    prev_entry_dt = entry["dt"] - timedelta(minutes=15)
    prev_m15_before_entry = dt_to_row.get(prev_entry_dt, {}).get("m15_state", "?")

    # Build bar list from available DUALTF rows
    bars = []
    for row in window_rows:
        dt = row["dt"]
        annotations = []

        # --- Entry bar ---
        if dt == entry["dt"]:
            annotations.append(
                f"TRIGGER: M15 flip {prev_m15_before_entry}->{row['m15_state']} "
                f"({entry['dir']}) | m30bbloc={row['m30bbloc']} "
                f"({zone_name(row['m30bbloc'], entry['dir'])}) | "
                f"gate {gate_result(row['m30bbloc'], entry['dir'])} -> "
                f"entry {entry['dir']} at {entry['entry_price']:.2f}"
            )
            annotations.append(
                f"SL={entry['sl']:.2f} (opp M15 band) | "
                f"TP={entry['tp']:.2f} (M30 band) | rr={entry['rr']:.2f}"
            )
            bars_count = 0

        # --- Post-entry bars ---
        elif dt > entry["dt"]:
            bars_count += 1

            # m30_followed update
            if not m30_followed:
                if (entry["dir"] == "UP" and row["m30_state"] == "F" or
                    entry["dir"] == "DOWN" and row["m30_state"] == "R"):
                    m30_followed = True
                    annotations.append("m30_followed->TRUE")

            # Exit condition check
            if dt == exit_["dt"]:
                if exit_["reason"] == "M15_REVERT":
                    annotations.append(
                        f"EXIT: M15 {row['m15_state']} != trigger state {trigger_state} "
                        f"-> M15_REVERT"
                    )
                elif exit_["reason"] == "TP_HIT":
                    annotations.append(
                        f"EXIT: price {exit_['exit_price']:.2f} reached TP {entry['tp']:.2f} "
                        f"-> TP_HIT"
                    )
                elif exit_["reason"] == "TIMEOUT":
                    annotations.append(
                        f"EXIT: {bars_count} bars, m30_followed={m30_followed} "
                        f"-> TIMEOUT"
                    )
                elif exit_["reason"] == "SL_HIT":
                    annotations.append(
                        f"EXIT: price {exit_['exit_price']:.2f} reached SL {entry['sl']:.2f} "
                        f"-> SL_HIT"
                    )
            else:
                # Non-exit post-entry bar
                if bars_count >= 8:
                    annotations.append(
                        f"timeout: {bars_count}/12, m30_followed={m30_followed}"
                    )
                if row["m15_state"] != trigger_state:
                    annotations.append(
                        f"M15 {row['m15_state']} != trigger {trigger_state}"
                    )

        bars.append({
            "dt": row["dt"],
            "d1": row["d1_state"],
            "d1b": str(row["d1bbloc"]),
            "h4": row["h4_state"],
            "h4b": str(row["h4bbloc"]),
            "h1": row["h1_state"],
            "h1b": str(row["h1bbloc"]),
            "m30": row["m30_state"],
            "m30b": str(row["m30bbloc"]),
            "m15": row["m15_state"],
            "m15b": str(row["m15bbloc"]),
            "annos": annotations,
        })

    # Write bar table
    md.append("| dt | d1 | d1b | h4 | h4b | h1 | h1b | m30 | m30b | m15 | m15b | annotation |")
    md.append("|----|----|-----|----|-----|----|-----|-----|------|-----|------|------------|")

    for bar in bars:
        annos = " | ".join(bar["annos"]) if bar["annos"] else ""
        md.append(
            f"| {bar['dt'].strftime('%m.%d %H:%M')} | {bar['d1']} | {bar['d1b']} | "
            f"{bar['h4']} | {bar['h4b']} | {bar['h1']} | {bar['h1b']} | "
            f"{bar['m30']} | {bar['m30b']} | {bar['m15']} | {bar['m15b']} | {annos} |"
        )

    md.append("")

# Footer
md.append("---\n")
md.append("> This report contains raw decision-trace data only. No profitability "
          "verdict, no design recommendations. For each trade, compare the code's "
          "entry/exit decisions against the intended design rules.")
md.append("")

with open(REPORT_PATH, "w", encoding="utf-8") as f:
    f.write("\n".join(md))

print(f"\nReport written to {REPORT_PATH}")
