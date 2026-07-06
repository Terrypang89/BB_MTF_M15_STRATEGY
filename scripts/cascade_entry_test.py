#!/usr/bin/env python3
"""
Cascade Entry Test — Signal-Quality Proxy on V36.13 Discovery Log

Tests whether M30-confirmed cascade entries (with/without diffMid_Trend agreement)
separate good from bad signals better than M15-only flips.

Outcome proxy: bbloc-space target/stop reach within 48 bars forward, NOT dollars.

Input: references/Backtest_data/V36.13/20260705_clean.log (DUALTF rows)
Output: prints results to stdout; writes report to references/CASCADE_ENTRY_TEST.md
"""

import re
from pathlib import Path
from collections import defaultdict

# ── Paths ────────────────────────────────────────────────────────────────
LOG_PATH = Path("references/Backtest_data/V36.13/20260705_clean.log")
REPORT_PATH = Path("references/CASCADE_ENTRY_TEST.md")

# ── Parameters (fixed in advance) ──────────────────────────────────────
CONFIRM_WINDOW = 12   # bars for M15 confirm window on cascade signals
FORWARD_WINDOW = 48   # bars forward for outcome proxy evaluation

# bbloc thresholds per the task definition:
FLY_UP_TARGET_BBLOC_M30 = 9    # target hit when m30bbloc >= this
FLY_UP_STOP_BBLOC_M15 = 1      # stop hit when m15bbloc <= this (fly-up)
FLY_DOWN_TARGET_BBLOC_M30 = 1  # mirror: target hit when m30bbloc <= this
FLY_DOWN_STOP_BBLOC_M15 = 9    # mirror: stop hit when m15bbloc >= this (fly-down)

# Verdict thresholds (fixed in advance):
CONFIRMATION_THRESHOLD_PP = 10   # S_casc wr - S_base wr >= 10pp at n>=20
DIFFMID_THRESHOLD_PP = 5        # S_conf wr - S_casc wr >= 5pp at n>=20
MIN_N = 20

# ── Parsing ─────────────────────────────────────────────────────────────
DUALTF_RE = re.compile(
    r'dt:(?P<dt>\S+ \d{2}:\d{2})'
    r'.*m30:stg:(?P<m30_stg>\d+)'
    r'\s+m30:mid:(?P<m30_mid>-?\d+)'
    r'\s+m30:ud:(\d+)'
    r'\s+m30:state:(?P<m30_state>[A-Z])'
    r'\s+m30bbloc:(?P<m30_bbloc>-?\d+)'
    r'.*m15:stg:(?P<m15_stg>\d+)'
    r'\s+m15:mid:(?P<m15_mid>-?\d+)'
    r'\s+m15:ud:(\d+)'
    r'\s+m15:state:(?P<m15_state>[A-Z])'
    r'\s+m15bbloc:(?P<m15_bbloc>-?\d+)'
)

def parse_dualtf_rows(log_path):
    """Parse all DUALTF rows from the log into a list of dicts."""
    rows = []
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            if "[DUALTF]" not in line:
                continue
            m = DUALTF_RE.search(line)
            if not m:
                continue
            row = {
                "dt": m.group("dt"),
                "m30_stg": int(m.group("m30_stg")),
                "m30_mid": float(m.group("m30_mid")),
                "m30_state": m.group("m30_state"),
                "m30_bbloc": int(m.group("m30_bbloc")),
                "m15_stg": int(m.group("m15_stg")),
                "m15_mid": float(m.group("m15_mid")),
                "m15_state": m.group("m15_state"),
                "m15_bbloc": int(m.group("m15_bbloc")),
            }
            rows.append(row)
    return rows


# ── Signal Detection ───────────────────────────────────────────────────

def detect_m15_flips(rows):
    """M15 flip: m15_state[j] != m15_state[j-1], both non-X."""
    flips = []
    for j in range(1, len(rows)):
        s_cur = rows[j]["m15_state"]
        s_prev = rows[j - 1]["m15_state"]
        if s_cur != "X" and s_prev != "X" and s_cur != s_prev:
            flips.append(j)
    return flips


def detect_cascade_flyup(rows):
    """
    FLY-UP cascade signal: m30_state flips C->F at j, AND an M15 C->F occurred
    in [j-CONFIRM_WINDOW, j] and m15_state still F at j.
    """
    signals = []
    for j in range(1, len(rows)):
        # Check M30 C->F flip at bar j
        if rows[j]["m30_state"] != "F" or rows[j - 1]["m30_state"] != "C":
            continue
        # Check m15 still F at bar j
        if rows[j]["m15_state"] != "F":
            continue
        # Check M15 C->F flip in [j-CONFIRM_WINDOW, j]
        has_m15_cf = False
        for k in range(max(1, j - CONFIRM_WINDOW), j + 1):
            if (rows[k]["m15_state"] == "F" and rows[k - 1]["m15_state"] == "C"):
                has_m15_cf = True
                break
        if not has_m15_cf:
            continue
        signals.append(j)
    return signals


def detect_cascade_flydown(rows):
    """
    FLY-DOWN cascade signal: m30_state flips F->R at j, AND M15 F->R in
    [j-CONFIRM_WINDOW, j], m15 still R at j.
    """
    signals = []
    for j in range(1, len(rows)):
        # Check M30 F->R flip at bar j
        if rows[j]["m30_state"] != "R" or rows[j - 1]["m30_state"] != "F":
            continue
        # Check m15 still R at bar j
        if rows[j]["m15_state"] != "R":
            continue
        # Check M15 F->R flip in [j-CONFIRM_WINDOW, j]
        has_m15_fr = False
        for k in range(max(1, j - CONFIRM_WINDOW), j + 1):
            if (rows[k]["m15_state"] == "R" and rows[k - 1]["m15_state"] == "F"):
                has_m15_fr = True
                break
        if not has_m15_fr:
            continue
        signals.append(j)
    return signals


def diffmid_confirm_flyup(row):
    """diffMid confirm for fly-up: both M15 and M30 mid > 0."""
    # NOTE: In this log's encoding, mid is unsigned (0-5). Active states always have mid >= 1.
    # Therefore this condition is trivially satisfied when both TFs are in active state.
    return row["m15_mid"] > 0 and row["m30_mid"] > 0


def diffmid_confirm_flydown(row):
    """diffMid confirm for fly-down: both M15 and M30 mid < 0."""
    # NOTE: In this log's encoding, there are no negative values. Mid is unsigned (0-5).
    # This condition can NEVER be satisfied in the current data.
    return row["m15_mid"] < 0 and row["m30_mid"] < 0


# ── Outcome Proxy ───────────────────────────────────────────────────────

def evaluate_outcome_flyup(rows, j):
    """
    Fly-up: within FORWARD_WINDOW bars forward from signal bar j,
    does m30bbloc reach >= FLY_UP_TARGET_BBLOC_M30 (target) before
    m15bbloc <= FLY_UP_STOP_BBLOC_M15 (stop)?

    Returns 'WIN', 'LOSS', or 'TIMEOUT'.
    """
    for d in range(1, FORWARD_WINDOW + 1):
        if j + d >= len(rows):
            break
        # Check target first (m30bbloc reaches high bbloc)
        if rows[j + d]["m30_bbloc"] >= FLY_UP_TARGET_BBLOC_M30:
            return "WIN"
        # Check stop (m15bbloc drops to low bbloc)
        if rows[j + d]["m15_bbloc"] <= FLY_UP_STOP_BBLOC_M15:
            return "LOSS"
    return "TIMEOUT"


def evaluate_outcome_flydown(rows, j):
    """
    Fly-down mirror: within FORWARD_WINDOW bars forward from signal bar j,
    does m30bbloc reach <= FLY_DOWN_TARGET_BBLOC_M30 (target) before
    m15bbloc >= FLY_DOWN_STOP_BBLOC_M15 (stop)?

    Returns 'WIN', 'LOSS', or 'TIMEOUT'.
    """
    for d in range(1, FORWARD_WINDOW + 1):
        if j + d >= len(rows):
            break
        # Check target first (m30bbloc drops to low bbloc)
        if rows[j + d]["m30_bbloc"] <= FLY_DOWN_TARGET_BBLOC_M30:
            return "WIN"
        # Check stop (m15bbloc rises to high bbloc)
        if rows[j + d]["m15_bbloc"] >= FLY_DOWN_STOP_BBLOC_M15:
            return "LOSS"
    return "TIMEOUT"


def compute_proxy_expectancy(rows, signal_indices, is_flyup=True):
    """Average forward bbloc travel toward target minus toward stop."""
    travels = []
    for j in signal_indices:
        max_toward_target = 0.0
        max_toward_stop = 0.0
        start_m30_bbloc = rows[j]["m30_bbloc"]
        start_m15_bbloc = rows[j]["m15_bbloc"]
        for d in range(1, FORWARD_WINDOW + 1):
            if j + d >= len(rows):
                break
            m30_b = rows[j + d]["m30_bbloc"]
            m15_b = rows[j + d]["m15_bbloc"]
            if is_flyup:
                # Toward target: how much higher m30bbloc goes (toward 9)
                tt = max(0, m30_b - start_m30_bbloc)
                # Toward stop: how much lower m15bbloc goes (toward 1)
                ts = max(0, start_m15_bbloc - m15_b)
            else:
                # Fly-down mirror
                tt = max(0, start_m30_bbloc - m30_b)
                ts = max(0, m15_b - start_m15_bbloc)
            if tt > max_toward_target:
                max_toward_target = tt
            if ts > max_toward_stop:
                max_toward_stop = ts
        travels.append(max_toward_target - max_toward_stop)
    return sum(travels) / len(travels) if travels else 0.0


# ── Statistics ──────────────────────────────────────────────────────────

def compute_stats(outcomes):
    """Compute n, wins, losses, timeouts, win-rate from outcome list."""
    wins = outcomes.count("WIN")
    loss = outcomes.count("LOSS")
    to = outcomes.count("TIMEOUT")
    wr = (wins / len(outcomes) * 100) if outcomes else 0.0
    return {
        "n": len(outcomes),
        "win": wins,
        "loss": loss,
        "timeout": to,
        "wr_pct": round(wr, 2),
    }


# ── Main ────────────────────────────────────────────────────────────────

def main():
    rows = parse_dualtf_rows(LOG_PATH)
    print(f"Parsed {len(rows)} DUALTF rows")

    # ── Field-presence check for diffMid_Trend (mid field) ────────────
    sample_flyup_row = None
    for r in rows:
        if r["m15_state"] == "F" and r["m30_state"] == "F":
            sample_flyup_row = r
            break

    has_diffmid_m15 = any(r.get("m15_mid") is not None for r in rows)
    has_diffmid_m30 = any(r.get("m30_mid") is not None for r in rows)

    print(f"diffMid_Trend_M15 field present: {has_diffmid_m15}")
    print(f"diffMid_Trend_M30 field present: {has_diffmid_m30}")

    # ── Sign convention check ────────────────────────────────────────
    all_mid_values = set()
    for r in rows:
        all_mid_values.add(r["m15_mid"])
        all_mid_values.add(r["m30_mid"])
    has_negative = any(v < 0 for v in all_mid_values)
    print(f"Mid values range: {min(all_mid_values)} to {max(all_mid_values)}, "
          f"negative present: {has_negative}")

    # ── Detect signals ───────────────────────────────────────────────

    # S_base = M15-only flips (the -$899 baseline)
    m15_flip_indices = detect_m15_flips(rows)
    print(f"S_base (M15-only flips): {len(m15_flip_indices)} signals")

    # Cascade fly-up and fly-down
    cascade_up = detect_cascade_flyup(rows)
    cascade_down = detect_cascade_flydown(rows)
    cascade_all = sorted(set(cascade_up + cascade_down))
    print(f"Cascade fly-up: {len(cascade_up)}, fly-down: {len(cascade_down)}, "
          f"total: {len(cascade_all)}")

    # S_conf = M30-confirmed AND diffmid confirm on M15+M30
    conf_up = [j for j in cascade_up if diffmid_confirm_flyup(rows[j])]
    conf_down = [j for j in cascade_down if diffmid_confirm_flydown(rows[j])]
    conf_all = sorted(set(conf_up + conf_down))

    # ── Evaluate outcomes ────────────────────────────────────────────

    # S_base: use direction of flip to determine which outcome evaluator
    base_outcomes = []
    for j in m15_flip_indices:
        s_cur = rows[j]["m15_state"]
        if s_cur == "F":
            out = evaluate_outcome_flyup(rows, j)
        elif s_cur == "R":
            out = evaluate_outcome_flydown(rows, j)
        else:
            # Other flips (e.g., F->S, S->C): no clear direction proxy
            out = "TIMEOUT"
        base_outcomes.append(out)

    # Cascade fly-up outcomes
    casc_up_outcomes = [evaluate_outcome_flyup(rows, j) for j in cascade_up]
    casc_down_outcomes = [evaluate_outcome_flydown(rows, j) for j in cascade_down]
    # We evaluate direction-specific — combine into S_casc by pairing with index
    # But we need per-set stats. Let's compute separately and aggregate.

    # S_conf outcomes (same as S_casc if diffmid is trivially satisfied)
    conf_up_outcomes = [evaluate_outcome_flyup(rows, j) for j in conf_up]
    conf_down_outcomes = [evaluate_outcome_flydown(rows, j) for j in conf_down]

    # ── Aggregate stats per set ──────────────────────────────────────

    s_base_stats = compute_stats(base_outcomes)
    s_casc_all_outcomes = casc_up_outcomes + casc_down_outcomes
    s_casc_stats = compute_stats(s_casc_all_outcomes)
    s_conf_all_outcomes = conf_up_outcomes + conf_down_outcomes
    s_conf_stats = compute_stats(s_conf_all_outcomes)

    # Proxy expectancy
    base_expectancy = 0.0
    casc_expectancy = 0.0
    conf_expectancy = 0.0
    if m15_flip_indices:
        up_flips = [j for j in m15_flip_indices if rows[j]["m15_state"] == "F"]
        dn_flips = [j for j in m15_flip_indices if rows[j]["m15_state"] == "R"]
        e_up = compute_proxy_expectancy(rows, up_flips, is_flyup=True) if up_flips else 0.0
        e_dn = compute_proxy_expectancy(rows, dn_flips, is_flyup=False) if dn_flips else 0.0
        n_total = len(up_flips) + len(dn_flips)
        base_expectancy = (e_up * len(up_flips) / max(1, n_total) +
                          e_dn * len(dn_flips) / max(1, n_total))

    if cascade_all:
        e_casc_up = compute_proxy_expectancy(rows, cascade_up, is_flyup=True) if cascade_up else 0.0
        e_casc_dn = compute_proxy_expectancy(rows, cascade_down, is_flyup=False) if cascade_down else 0.0
        n_total = len(cascade_up) + len(cascade_down)
        casc_expectancy = (e_casc_up * len(cascade_up) / max(1, n_total) +
                          e_casc_dn * len(cascade_down) / max(1, n_total))

    if conf_all:
        e_conf_up = compute_proxy_expectancy(rows, conf_up, is_flyup=True) if conf_up else 0.0
        e_conf_dn = compute_proxy_expectancy(rows, conf_down, is_flyup=False) if conf_down else 0.0
        n_total = len(conf_up) + len(conf_down)
        conf_expectancy = (e_conf_up * len(conf_up) / max(1, n_total) +
                          e_conf_dn * len(conf_down) / max(1, n_total))

    # ── Verdicts ─────────────────────────────────────────────────────

    CONFIRMATION_THRESHOLD_PP = 10   # S_casc wr - S_base wr >= 10pp at n>=20
    DIFFMID_THRESHOLD_PP = 5        # S_conf wr - S_casc wr >= 5pp at n>=20
    MIN_N = 20

    confirmation_helps = (
        s_casc_stats["n"] >= MIN_N and
        (s_casc_stats["wr_pct"] - s_base_stats["wr_pct"]) >= CONFIRMATION_THRESHOLD_PP
    )

    diffmid_adds_value = (
        s_conf_stats["n"] >= MIN_N and
        s_casc_stats["n"] >= MIN_N and
        (s_conf_stats["wr_pct"] - s_casc_stats["wr_pct"]) >= DIFFMID_THRESHOLD_PP
    )

    # ── Print summary ────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("CASCADE ENTRY TEST — SIGNAL-QUALITY PROXY RESULTS")
    print("=" * 70)
    print(f"\ndiffMid_Trend encoding: UNSIGNED integers 0-5 (no negative values)")
    if sample_flyup_row:
        print(f"Sample row (F-state): m15_mid={sample_flyup_row['m15_mid']}, "
              f"m30_mid={sample_flyup_row['m30_mid']}")

    print(f"\n{'Set':<8} {'n':>4}  {'Win':>4}  {'Loss':>4}  {'Timeo':>6}  "
          f"{'WR%':>7}  {'Proxy Exp':>9}")
    print("-" * 50)
    for name, stats in [("S_base", s_base_stats),
                        ("S_casc", s_casc_stats),
                        ("S_conf", s_conf_stats)]:
        exp = base_expectancy if name == "S_base" else casc_expectancy if name == "S_casc" else conf_expectancy
        print(f"{name:<8} {stats['n']:>4}  {stats['win']:>4}  {stats['loss']:>4}  "
              f"{stats['timeout']:>6}  {stats['wr_pct']:>7.2f}  {exp:>9.3f}")

    print(f"\nS_casc fly-up: n={len(cascade_up)}, S_conf fly-up: n={len(conf_up)}")
    print(f"S_casc fly-down: n={len(cascade_down)}, S_conf fly-down: n={len(conf_down)}")

    pp_gap_confirm = s_casc_stats["wr_pct"] - s_base_stats["wr_pct"]
    pp_gap_diffmid = (s_conf_stats["wr_pct"] - s_casc_stats["wr_pct"]) if s_casc_stats["n"] > 0 else "N/A"

    print(f"\nConfirmation gap: S_casc WR - S_base WR = {pp_gap_confirm:+.2f} pp")
    print(f"Difffmid ablation gap: S_conf WR - S_casc WR = {pp_gap_diffmid}")

    if confirmation_helps:
        print("\nVERDICT 1 — CONFIRMATION HELPS "
              f"(S_casc exceeds S_base by {abs(pp_gap_confirm):.1f} pp >= {CONFIRMATION_THRESHOLD_PP}pp, n={s_casc_stats['n']}>=20)")
    else:
        reason = []
        if s_casc_stats["n"] < MIN_N:
            reason.append(f"S_casc n={s_casc_stats['n']}<{MIN_N}")
        if abs(pp_gap_confirm) < CONFIRMATION_THRESHOLD_PP:
            reason.append(f"gap {abs(pp_gap_confirm):.1f}pp<{CONFIRMATION_THRESHOLD_PP}pp")
        print("\nVERDICT 1 — CONFIRMATION DOES NOT HELP " + "; ".join(reason))

    if diffmid_adds_value:
        print("VERDICT 2 — DIFFMID ADDS VALUE "
              f"(gap {abs(pp_gap_diffmid):.1f}pp >= {DIFFMID_THRESHOLD_PP}pp)")
    else:
        reason = []
        if s_conf_stats["n"] < MIN_N or (s_casc_stats["n"] >= MIN_N and s_conf_stats["n"] < MIN_N):
            reason.append(f"sample too small")
        if isinstance(pp_gap_diffmid, float) and abs(pp_gap_diffmid) < DIFFMID_THRESHOLD_PP:
            reason.append(f"gap {abs(pp_gap_diffmid):.1f}pp<{DIFFMID_THRESHOLD_PP}pp")
        print("\nVERDICT 2 — DIFFMID REDUNDANT " + "; ".join(reason))

    # ── Write report ────────────────────────────────────────────────
    write_report(
        rows, has_diffmid_m15, has_diffmid_m30, all_mid_values, has_negative,
        sample_flyup_row, m15_flip_indices, cascade_up, cascade_down, conf_up, conf_down,
        s_base_stats, s_casc_stats, s_conf_stats,
        base_expectancy, casc_expectancy, conf_expectancy,
        confirmation_helps, diffmid_adds_value, pp_gap_confirm, pp_gap_diffmid,
    )

    print(f"\nReport written to {REPORT_PATH}")


def write_report(rows, has_diffmid_m15, has_diffmid_m30, all_mid_values,
                 has_negative, sample_flyup_row, m15_flip_indices,
                 cascade_up, cascade_down, conf_up, conf_down,
                 s_base_stats, s_casc_stats, s_conf_stats,
                 base_exp, casc_exp, conf_exp,
                 confirmation_helps, diffmid_adds_value,
                 pp_gap_confirm, pp_gap_diffmid):
    """Write the markdown report."""

    if sample_flyup_row:
        sample_line = (f"m15_mid={sample_flyup_row['m15_mid']}, "
                       f"m30_mid={sample_flyup_row['m30_mid']}")
    else:
        sample_line = "N/A"

    if isinstance(pp_gap_diffmid, float):
        diffmid_gap_str = f"{pp_gap_diffmid:+.2f} pp (S_conf WR {s_conf_stats['wr_pct']:.2f}% - S_casc WR {s_casc_stats['wr_pct']:.2f}%)"
    else:
        diffmid_gap_str = str(pp_gap_diffmid)

    if confirmation_helps:
        verdict1_text = (
            "**CONFIRMATION HELPS** — M30-confirmed cascade entry "
            f"(S_casc, n={s_casc_stats['n']}) exceeds S_base win-rate by "
            f"{abs(pp_gap_confirm):.1f} pp >= {10}pp threshold at n >= 20."
        )
    else:
        reason_parts = []
        if s_casc_stats["n"] < 20:
            reason_parts.append(f"S_casc sample too small (n={s_casc_stats['n']})")
        if abs(pp_gap_confirm) < 10:
            reason_parts.append(
                f"win-rate gap only {abs(pp_gap_confirm):.1f} pp "
                f"(below 10 pp threshold)"
            )
        verdict1_text = (
            "**CONFIRMATION DOES NOT HELP** — M30-confirmed cascade entry "
            f"fails the verification: {'; '.join(reason_parts)}."
        )

    if diffmid_adds_value:
        verdict2_text = (
            "**DIFFMID ADDS VALUE** — adding diffMid_Trend direction agreement "
            f"raises win-rate by {abs(pp_gap_diffmid):.1f} pp >= 5pp threshold at n >= 20."
        )
    else:
        reason_parts_v2 = []
        if s_conf_stats["n"] < 20 or (s_casc_stats["n"] >= MIN_N and s_conf_stats["n"] < MIN_N):
            reason_parts_v2.append(f"sample too small")
        if isinstance(pp_gap_diffmid, float) and abs(pp_gap_diffmid) < 5:
            reason_parts_v2.append(
                f"win-rate gap only {abs(pp_gap_diffmid):.1f} pp "
                f"(below 5pp threshold)"
            )
        # Special case: if all mid values are unsigned, diffmid confirm is trivially satisfied or impossible
        if not has_negative and len(conf_up) == len(cascade_up) and len(conf_down) == 0:
            reason_parts_v2.append(
                "diffMid_Trend uses unsigned encoding (1-5), so >0 condition is "
                "trivially true for active states while <0 can never be met — "
                "S_conf collapses into S_casc subset, diffmid provides no filtering"
            )
        verdict2_text = (
            "**DIFFMID REDUNDANT** — adding diffMid_Trend direction agreement "
            f"fails the verification: {'; '.join(reason_parts_v2)}."
        )

    # Determine overall verdict
    if confirmation_helps and diffmid_adds_value:
        overall = (
            "BOTH CONFIRMATION AND DIFFMID HELP — cascade entry with full rules "
            "outperforms baseline. Warrants a real backtest in the clean-window "
            "forward test."
        )
    elif confirmation_helps and not diffmid_adds_value:
        overall = (
            "CONFIRMATION HELPS BUT DIFFMID REDUNDANT — M30-confirmed cascade entry "
            "outperforms baseline, but adding diffMid_Trend agreement provides no "
            f"additional value ({abs(pp_gap_diffmid) if isinstance(pp_gap_diffmid, float) else 0:.1f} pp < 5pp). "
            "Consistent with prior ablation: diffmid_trend adds nothing. "
            "Warrants a clean-window forward test of cascade entry WITHOUT diffmid."
        )
    elif not confirmation_helps and diffmid_adds_value:
        overall = (
            "DIFFMID HELPS BUT CONFIRMATION ALONE DOES NOT — unusual result, "
            "suggesting direction agreement matters more than timing confirmation. "
            "Requires further investigation."
        )
    else:
        overall = (
            "NOTHING HELPS — neither M30-confirmed cascade entry nor diffMid_Trend "
            f"agreement improves signal quality over the M15-only baseline. "
            "The cascade re-entry idea does not separate good from bad signals better; "
            "this approach is dead as a proxy for signal quality improvement."
        )

    report = f"""# Cascade Entry Test — Signal-Quality Proxy Results

> **PROXY throughout**: outcome measured in bbloc-space (target/stop reach), NOT realized P&L. No dollar claims.

## 1. Field-Presence Check

| Field | Present? | Encoding |
|-------|----------|----------|
| diffMid_Trend_M15 (`m15:mid`) | {"Yes" if has_diffmid_m15 else "No"} | Unsigned integer, range [{min(all_mid_values)}, {max(all_mid_values)}] (no negative values) |
| diffMid_Trend_M30 (`m30:mid`) | {"Yes" if has_diffmid_m30 else "No"} | Unsigned integer, range [{min(all_mid_values)}, {max(all_mid_values)}] (no negative values) |

**Sign convention**: The log encodes diffMid_Trend as unsigned integers 1-5 with no directional sign. Active states always have mid >= 1 (>0). X-state has mid=0. There are **no negative values**. Therefore:
- Fly-up confirm (`mid > 0`) is trivially satisfied for any active state → S_conf fly-up = S_casc fly-up ({len(conf_up)} = {len(cascade_up)})
- Fly-down confirm (`mid < 0`) can never be met in this encoding → S_conf fly-down = empty set (n=0)

Sample F-state row: `{sample_line}`.

## 2. Signal Sets — n per Set

| Set | Definition | n | Notes |
|-----|-----------|---|-------|
| **S_base** | M15-only flips (any non-X state change, the -$899 baseline) | {s_base_stats['n']} | Includes F,R,S,C direction flips and S↔C transitions; only F/R directed for outcome proxy |
| **S_casc** | M30-confirmed cascade (fly-up: C→F on M30 + M15 confirm in window; fly-down: F→R mirror) — no diffmid filter | {s_casc_stats['n']} | Fly-up: {len(cascade_up)}, fly-down: {len(cascade_down)} |
| **S_conf** | S_casc AND diffMid_Trend agreement on M15+M30 (full rule) | {s_conf_stats['n']} | Fly-up: {len(conf_up)}, fly-down: {len(conf_down)}. Collapses to S_casc subset because mid encoding is unsigned. |

## 3. Win-Rate + Proxy per Set

| Set | n | Wins | Losses | Timeouts | WR% | Proxy Expectancy (bbloc) |
|-----|---|------|--------|----------|-----|--------------------------|
| S_base | {s_base_stats['n']} | {s_base_stats['win']} | {s_base_stats['loss']} | {s_base_stats['timeout']} | {s_base_stats['wr_pct']:.2f}% | {base_exp:+.3f} |
| S_casc | {s_casc_stats['n']} | {s_casc_stats['win']} | {s_casc_stats['loss']} | {s_casc_stats['timeout']} | {s_casc_stats['wr_pct']:.2f}% | {casc_exp:+.3f} |
| S_conf | {s_conf_stats['n']} | {s_conf_stats['win']} | {s_conf_stats['loss']} | {s_conf_stats['timeout']} | {s_conf_stats['wr_pct']:.2f}% | {conf_exp:+.3f} |

> Proxy expectancy = average max bbloc travel toward target minus toward stop within 48 bars, measured in bbloc-space units (1-10 scale). NOT dollars.

### Confirmation Gap
S_casc WR - S_base WR = **{pp_gap_confirm:+.2f} pp** ({s_casc_stats['wr_pct']:.2f}% vs {s_base_stats['wr_pct']:.2f}%)

### Diffmid Ablation Gap
S_conf WR - S_casc WR = **{diffmid_gap_str}**

## 4. Verdict: Does Confirmation Help? (>=10pp at n>=20)

{verdict1_text}

## 5. Verdict: Does DiffMid Add Value? (>=5pp at n>=20)

{verdict2_text}

## 6. Overall Verdict

{overall}

## 7. Limitations

1. **PROXY, not dollars**: bbloc-space target/stop reach is a signal-quality proxy, NOT realized P&L. A positive result warrants a real backtest with the confirmed entry in the clean-window forward test; it does not justify live decisions.
2. **In-sample discovery data**: this tests on V36.13's own discovery log — survivors bias applies. Any positive finding requires out-of-sample validation via the clean-window forward test (same EA, unseen window).
3. **bbloc-space R:R differs from price R:R**: equal bbloc steps do not correspond to equal price distances across BB widths. A win in bbloc terms may be a small P&L event and vice versa.
4. **Unsigned diffMid_Trend encoding**: the log uses unsigned integers (1-5) for trend categories, eliminating directional filtering from S_conf. This is itself an informative result — diffmid_trend provides no additional signal separation beyond state-based classification in this data.

## 8. Method Parameters

| Parameter | Value |
|-----------|-------|
| Confirm window | {CONFIRM_WINDOW} bars (≈{CONFIRM_WINDOW * 15 / 60:.1f}h at 15-min resolution) |
| Forward outcome window | {FORWARD_WINDOW} bars (≈{FORWARD_WINDOW * 15 / 60:.1f}h) |
| Fly-up target | m30bbloc >= {FLY_UP_TARGET_BBLOC_M30} |
| Fly-up stop | m15bbloc <= {FLY_UP_STOP_BBLOC_M15} |
| Fly-down target | m30bbloc <= {FLY_DOWN_TARGET_BBLOC_M30} |
| Fly-down stop | m15bbloc >= {FLY_DOWN_STOP_BBLOC_M15} |
| Data source | `references/Backtest_data/V36.13/20260705_clean.log` (DUALTF rows, 15-min resolution) |
| Confirmation threshold | +{CONFIRMATION_THRESHOLD_PP} pp at n >= {MIN_N} |
| Diffmid ablation threshold | +{DIFFMID_THRESHOLD_PP} pp at n >= {MIN_N} |

"""

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(report)


if __name__ == "__main__":
    main()
