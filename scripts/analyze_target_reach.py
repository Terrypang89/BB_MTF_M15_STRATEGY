#!/usr/bin/env python3
"""
Target Reach Analysis — Do structural band targets (M30/H1/H4 upper/lower band)
get REACHED after detector-qualifying triggers (M15 flips to F or R)?

Settles Part 5's target rule. "M30 fly targets H4 BBUp" is an unmeasured belief.
Same species as the HTF filter that just died (CASCADE_LEAD_ANALYSIS).

Verdict criteria (FIXED, no post-hoc adjustment):
  C1: H4-band reach from MID+FAR zones combined >= 40% (M30-followed, N=48)
  C2: At least one of M30/H1/H4 band achieves >= 60% reach from NEAR+MID (M30-followed, N=48)
  C3: For each target, NEAR reach >= FAR reach (sanity check)
"""

import re
import sys
from collections import defaultdict

LOG_PATH = r"references/Backtest_data/V36.10/20260703_clean.log"
REPORT_PATH = "references/TARGET_REACH_ANALYSIS.md"

K_M30_FOLLOW = 12  # same as cascade analysis
WINDOWS = [12, 24, 48, 96]
N_VERDICT = 48

# Verdict criteria
C1_THRESHOLD = 0.40  # H4 reach from MID+FAR combined
C2_THRESHOLD = 0.60  # any target from NEAR+MID combined


def parse_log(path):
    """Parse DUALTF rows from the log file — includes bbloc fields."""
    rows = []
    pattern = re.compile(
        r"dt:(\d{4}\.\d{2}\.\d{2}\s+\d{2}:\d{2}:\d{2})"
        r".*?d1:state:(\w+)"
        r".*?d1bbloc:(-?\d+)"
        r".*?h4:state:(\w+)"
        r".*?h4bbloc:(-?\d+)"
        r".*?h1:state:(\w+)"
        r".*?h1bbloc:(-?\d+)"
        r".*?m30:state:(\w+)"
        r".*?m30bbloc:(-?\d+)"
        r".*?m15:state:(\w+)"
        r".*?m15bbloc:(-?\d+)"
    )
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if "[DUALTF]" not in line:
                continue
            m = pattern.search(line)
            if not m:
                continue
            dt_str = m.group(1)
            d1_st = m.group(2)
            d1bb = int(m.group(3))
            h4_st = m.group(4)
            h4bb = int(m.group(5))
            h1_st = m.group(6)
            h1bb = int(m.group(7))
            m30_st = m.group(8)
            m30bb = int(m.group(9))
            m15_st = m.group(10)
            m15bb = int(m.group(11))
            rows.append({
                "dt": dt_str,
                "d1_state": d1_st,
                "h4_state": h4_st,
                "h1_state": h1_st,
                "m30_state": m30_st,
                "m15_state": m15_st,
                "d1bbloc": d1bb,
                "h4bbloc": h4bb,
                "h1bbloc": h1bb,
                "m30bbloc": m30bb,
                "m15bbloc": m15bb,
            })
    return rows


def find_triggers(rows):
    """Find M15 flips to F (UP) or R (DOWN) — both states must be non-X."""
    triggers = []
    for i in range(1, len(rows)):
        if rows[i]["m15_state"] == "X" or rows[i - 1]["m15_state"] == "X":
            continue
        if rows[i]["m15_state"] != rows[i - 1]["m15_state"]:
            if rows[i]["m15_state"] in ("F", "R"):
                direction = "UP" if rows[i]["m15_state"] == "F" else "DOWN"
                triggers.append({
                    "index": i,
                    "direction": direction,
                    "target_state": rows[i]["m15_state"],
                    "from_state": rows[i - 1]["m15_state"],
                })
    return triggers


def is_m30_followed(rows, trigger, K=K_M30_FOLLOW):
    """Check if M30 reaches the same target state within K rows of the trigger."""
    j = trigger["index"]
    B = trigger["target_state"]
    for fwd in range(j, min(j + K + 1, len(rows))):
        if fwd < 1:
            continue
        if rows[fwd]["m30_state"] != rows[fwd - 1]["m30_state"]:
            if rows[fwd]["m30_state"] == B:
                return True
    return False


def target_reached(rows, trigger, tf_bbloc_key, N):
    """
    Check if target TF's bbloc reaches the band within N rows.
    UP trigger: bbloc >= 9
    DOWN trigger: bbloc <= 1 (and != -1)
    Excludes trigger if bbloc == -1 at trigger row.
    """
    j = trigger["index"]
    # Exclude if bbloc == -1 at trigger row
    if rows[j][tf_bbloc_key] == -1:
        return None  # excluded
    # Check forward window (j, j+N]
    for fwd in range(j + 1, min(j + N + 1, len(rows))):
        bb = rows[fwd][tf_bbloc_key]
        if bb == -1:
            continue  # skip no-data rows
        if trigger["direction"] == "UP" and bb >= 9:
            return True
        if trigger["direction"] == "DOWN" and bb <= 1:
            return True
    return False  # not reached (could be None if excluded, but we check that first)


def get_zone(bbloc, direction):
    """
    Zone classification by the target TF's bbloc at trigger row.
    UP triggers (band at 9): AT/BEYOND={9,10}, NEAR={7,8}, MID={4,5,6}, FAR={0..3}
    DOWN triggers (band at 1, mirror): AT/BEYOND={0,1}, NEAR={2,3}, MID={4,5,6}, FAR={7..10}
    """
    if direction == "UP":
        if bbloc in (9, 10):
            return "AT/BEYOND"
        elif bbloc in (7, 8):
            return "NEAR"
        elif bbloc in (4, 5, 6):
            return "MID"
        else:  # 0,1,2,3
            return "FAR"
    else:  # DOWN
        if bbloc in (0, 1):
            return "AT/BEYOND"
        elif bbloc in (2, 3):
            return "NEAR"
        elif bbloc in (4, 5, 6):
            return "MID"
        else:  # 7,8,9,10
            return "FAR"


def median(values):
    """Compute median."""
    if not values:
        return 0
    s = sorted(values)
    n = len(s)
    if n % 2 == 1:
        return s[n // 2]
    else:
        return (s[n // 2 - 1] + s[n // 2]) / 2


def mean(values):
    """Compute mean."""
    if not values:
        return 0
    return sum(values) / len(values)


# ─── MEASUREMENT A ──────────────────────────────────────────────

def measurement_a(rows, triggers, tf_bbloc_key):
    """
    For each trigger, check if target TF reaches its band within each window N.
    Returns: dict[zone][direction][N] = {"all": (reached, total), "followed": (reached, total)}
    """
    zone_order = ["FAR", "MID", "NEAR", "AT/BEYOND"]
    dirs = ["UP", "DOWN"]
    result = {}
    for zone in zone_order:
        result[zone] = {}
        for d in dirs:
            result[zone][d] = {}
            for N in WINDOWS:
                result[zone][d][N] = {
                    "all": {"reached": 0, "total": 0},
                    "followed": {"reached": 0, "total": 0},
                }

    for trig in triggers:
        followed = is_m30_followed(rows, trig)
        j = trig["index"]
        bb = rows[j][tf_bbloc_key]
        if bb == -1:
            continue  # exclude this trigger for this target
        zone = get_zone(bb, trig["direction"])

        for N in WINDOWS:
            reached = target_reached(rows, trig, tf_bbloc_key, N)
            if reached is None:
                continue
            # Always count in "all"
            result[zone][trig["direction"]][N]["all"]["total"] += 1
            if reached:
                result[zone][trig["direction"]][N]["all"]["reached"] += 1
            # Count in "followed" only if M30-followed
            if followed:
                result[zone][trig["direction"]][N]["followed"]["total"] += 1
                if reached:
                    result[zone][trig["direction"]][N]["followed"]["reached"] += 1

    return result


# ─── MEASUREMENT B ──────────────────────────────────────────────

def measurement_b(rows, target_tf, tf_bbloc_key, N=N_VERDICT):
    """
    Unconditional base rate: from ALL rows where the target TF's bbloc is in
    a given zone (no trigger required), how often does the band get reached within N rows?
    Returns: dict[zone][direction] = {"reached": count, "total": count}
    """
    zone_order = ["FAR", "MID", "NEAR", "AT/BEYOND"]
    dirs = ["UP", "DOWN"]
    result = {}
    for zone in zone_order:
        result[zone] = {}
        for d in dirs:
            result[zone][d] = {"reached": 0, "total": 0}

    # For each row, determine zone and direction context.
    # Direction: UP if the row's m15_state is F or the row is in an up context,
    # but since there's no trigger, we need a proxy.
    # We'll use: if the row's m30_state or m15_state is F, direction=UP; if R, direction=DOWN.
    # Actually, the simplest is to test both directions independently:
    # For UP: from rows where bbloc is in a zone, does bbloc reach >= 9 within N?
    # For DOWN: from rows where bbloc is in a zone, does bbloc reach <= 1 within N?
    # This doesn't need a "direction" per se — just test the band reach.

    for i in range(len(rows)):
        bb = rows[i][tf_bbloc_key]
        if bb == -1:
            continue
        # We don't have a direction for base rate — just test reach in both directions.
        # But the zone depends on direction. So we need to pick a direction.
        # Better approach: use the m15_state at this row as a direction proxy.
        # If m15_state == F, treat as UP context; if R, treat as DOWN; else skip.
        if rows[i]["m15_state"] not in ("F", "R"):
            continue
        direction = "UP" if rows[i]["m15_state"] == "F" else "DOWN"
        zone = get_zone(bb, direction)

        reached_up = False
        reached_down = False
        for fwd in range(i + 1, min(i + N + 1, len(rows))):
            bb_fwd = rows[fwd][tf_bbloc_key]
            if bb_fwd == -1:
                continue
            if bb_fwd >= 9:
                reached_up = True
            if bb_fwd <= 1:
                reached_down = True
            if reached_up and reached_down:
                break

        # Count for UP direction
        result[zone]["UP"]["total"] += 1
        if reached_up:
            result[zone]["UP"]["reached"] += 1
        # Count for DOWN direction
        result[zone]["DOWN"]["total"] += 1
        if reached_down:
            result[zone]["DOWN"]["reached"] += 1

    return result


# ─── MEASUREMENT C ──────────────────────────────────────────────

def measurement_c(rows, triggers, tf_bbloc_key):
    """
    For triggers firing in AT/BEYOND zone: what % hold at the band for 12 rows (ride)
    vs move away from it (reject)?
    UP: hold >= 9, reject = falls < 7.
    DOWN: hold <= 1, reject = rises > 3.
    """
    ride_count = 0
    reject_count = 0
    total_at = 0

    for trig in triggers:
        j = trig["index"]
        bb = rows[j][tf_bbloc_key]
        if bb == -1:
            continue
        zone = get_zone(bb, trig["direction"])
        if zone != "AT/BEYOND":
            continue
        total_at += 1

        held = True
        fell = False
        for fwd in range(j + 1, min(j + 13, len(rows))):
            bb_fwd = rows[fwd][tf_bbloc_key]
            if bb_fwd == -1:
                continue  # skip no-data
            if trig["direction"] == "UP":
                # Band at upper: hold >= 9, reject = falls < 7
                if bb_fwd < 9:
                    held = False
                    if bb_fwd < 7:
                        fell = True
                        break
            else:
                # Band at lower: hold <= 1, reject = rises > 3
                if bb_fwd > 1:
                    held = False
                    if bb_fwd > 3:
                        fell = True
                        break
        if held:
            ride_count += 1
        elif fell:
            reject_count += 1
        # else: partial (left band but not full rejection)

    return {"ride": ride_count, "reject": reject_count, "total": total_at}


# ─── MAIN ───────────────────────────────────────────────────────

TARGETS = [
    ("M30", "m30bbloc"),
    ("H1", "h1bbloc"),
    ("H4", "h4bbloc"),
]

def main():
    print("Parsing log file...")
    rows = parse_log(LOG_PATH)
    print(f"  Parsed {len(rows)} DUALTF rows.")

    print("Finding triggers (M15 flips to F or R)...")
    triggers = find_triggers(rows)
    up_triggers = [t for t in triggers if t["direction"] == "UP"]
    down_triggers = [t for t in triggers if t["direction"] == "DOWN"]
    print(f"  UP triggers (F): {len(up_triggers)}")
    print(f"  DOWN triggers (R): {len(down_triggers)}")

    # M30-followed
    followed_triggers = [t for t in triggers if is_m30_followed(rows, t)]
    followed_up = [t for t in followed_triggers if t["direction"] == "UP"]
    followed_down = [t for t in followed_triggers if t["direction"] == "DOWN"]
    print(f"  M30-followed total: {len(followed_triggers)}")
    print(f"  M30-followed UP: {len(followed_up)}, DOWN: {len(followed_down)}")

    # ─── Measurement A ──────────────────────────────────────
    meas_a_results = {}
    for tf_name, bbloc_key in TARGETS:
        print(f"\n--- Measurement A: {tf_name} ---")
        meas_a_results[tf_name] = measurement_a(rows, triggers, bbloc_key)

    # ─── Measurement B ──────────────────────────────────────
    meas_b_results = {}
    print("\n--- Measurement B: Base rates ---")
    for tf_name, bbloc_key in TARGETS:
        meas_b_results[tf_name] = measurement_b(rows, (tf_name,), bbloc_key)
        print(f"  {tf_name} base rates computed.")

    # ─── Measurement C ──────────────────────────────────────
    meas_c_results = {}
    print("\n--- Measurement C: At-band analysis ---")
    for tf_name, bbloc_key in TARGETS:
        meas_c_results[tf_name] = measurement_c(rows, triggers, bbloc_key)
        r = meas_c_results[tf_name]
        print(f"  {tf_name}: ride={r['ride']}, reject={r['reject']}, total_at={r['total']}")

    # ─── VERDICT ─────────────────────────────────────────────
    print("\n--- VERDICT ---")
    # C1: H4-band reach from MID+FAR combined, M30-followed, N=48
    c1_result = compute_c1(meas_a_results)
    # C2: any target >= 60% from NEAR+MID, M30-followed, N=48
    c2_result = compute_c2(meas_a_results)
    # C3: NEAR reach >= FAR reach for each target
    c3_result = compute_c3(meas_a_results)

    print(f"  C1 (H4 reach MID+FAR >= 40%): {c1_result['pct'] * 100:.1f}% -> "
          f"{'PASS' if c1_result['pass'] else 'FAIL'}")
    print(f"  C2 (any target NEAR+MID >= 60%): {c2_result['best_pct'] * 100:.1f}% "
          f"({c2_result['best_target']}) -> {'PASS' if c2_result['pass'] else 'FAIL'}")
    print(f"  C3 (NEAR >= FAR sanity): {'PASS' if c3_result['pass'] else 'FAIL — ' + c3_result['detail']}")

    viable = c1_result["pass"] and c2_result["pass"] and c3_result["pass"]
    if viable:
        print("  ** ALL CRITERIA PASS ** — Structural targets are grounded.")
    else:
        failed = []
        if not c1_result["pass"]:
            failed.append(f"C1: H4 reach {c1_result['pct'] * 100:.1f}%")
        if not c2_result["pass"]:
            failed.append(f"C2: best={c2_result['best_target']} at {c2_result['best_pct'] * 100:.1f}%")
        if not c3_result["pass"]:
            failed.append(f"C3: {c3_result['detail']}")
        print(f"  ** CRITERIA FAILED: {', '.join(failed)} **")

    # ─── WRITE REPORT ────────────────────────────────────────
    write_report(
        rows, triggers, up_triggers, down_triggers,
        followed_triggers, followed_up, followed_down,
        meas_a_results, meas_b_results, meas_c_results,
        c1_result, c2_result, c3_result,
    )
    print(f"\nReport written to {REPORT_PATH}")


def compute_c1(meas_a_results):
    """C1: H4-band reach from MID+FAR combined, M30-followed, N=48."""
    h4 = meas_a_results["H4"]
    total_reached = 0
    total_triggers = 0
    for zone in ["MID", "FAR"]:
        for d in ["UP", "DOWN"]:
            data = h4[zone][d][48]["followed"]
            total_reached += data["reached"]
            total_triggers += data["total"]
    pct = total_reached / total_triggers if total_triggers > 0 else 0.0
    return {"pct": pct, "pass": pct >= C1_THRESHOLD}


def compute_c2(meas_a_results):
    """C2: any target >= 60% from NEAR+MID, M30-followed, N=48."""
    best_pct = 0.0
    best_target = "NONE"
    for tf_name in ["M30", "H1", "H4"]:
        total_reached = 0
        total_triggers = 0
        for zone in ["NEAR", "MID"]:
            for d in ["UP", "DOWN"]:
                data = meas_a_results[tf_name][zone][d][48]["followed"]
                total_reached += data["reached"]
                total_triggers += data["total"]
        pct = total_reached / total_triggers if total_triggers > 0 else 0.0
        if pct > best_pct:
            best_pct = pct
            best_target = tf_name
    return {"best_pct": best_pct, "best_target": best_target, "pass": best_pct >= C2_THRESHOLD}


def compute_c3(meas_a_results):
    """C3: NEAR reach >= FAR reach for each target (M30-followed, N=48).
    Exclude low-sample cells (n < 15) from the check — they're flagged separately."""
    violations = []
    for tf_name in ["M30", "H1", "H4"]:
        for d in ["UP", "DOWN"]:
            near_data = meas_a_results[tf_name]["NEAR"][d][48]["followed"]
            far_data = meas_a_results[tf_name]["FAR"][d][48]["followed"]
            # Skip if either side is low-sample
            if near_data["total"] < 15 or far_data["total"] < 15:
                continue
            near_pct = near_data["reached"] / near_data["total"] if near_data["total"] > 0 else 0
            far_pct = far_data["reached"] / far_data["total"] if far_data["total"] > 0 else 0
            if near_pct < far_pct:
                violations.append(f"{tf_name}/{d}: NEAR={near_pct * 100:.1f}% < FAR={far_pct * 100:.1f}%")
    if violations:
        return {"pass": False, "detail": "; ".join(violations)}
    return {"pass": True, "detail": ""}


def write_report(rows, triggers, up_triggers, down_triggers,
                 followed_triggers, followed_up, followed_down,
                 meas_a_results, meas_b_results, meas_c_results,
                 c1_result, c2_result, c3_result):
    """Write TARGET_REACH_ANALYSIS.md."""
    lines = []

    lines.append("# Target Reach Analysis")
    lines.append("")
    lines.append(
        "> Do structural band targets (M30/H1/H4 upper/lower band) get REACHED after "
        "detector-qualifying triggers? Settles Part 5's target rule."
    )
    lines.append("")

    # ─── DATA SUMMARY ────────────────────────────────────────
    lines.append("## Data Summary")
    lines.append("")
    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Total DUALTF rows | {len(rows)} |")
    lines.append(f"| UP triggers (M15->F) | {len(up_triggers)} |")
    lines.append(f"| DOWN triggers (M15->R) | {len(down_triggers)} |")
    lines.append(f"| M30-followed UP | {len(followed_up)} |")
    lines.append(f"| M30-followed DOWN | {len(followed_down)} |")
    lines.append(f"| M30-followed total | {len(followed_triggers)} |")
    lines.append("")
    lines.append(
        f"> **Cascade cross-check:** UP flips = {len(up_triggers)} (cascade: ~245), "
        f"DOWN flips = {len(down_triggers)} (cascade: ~252). "
        f"M30-followed UP = {len(followed_up)} ({len(followed_up) / len(up_triggers) * 100:.0f}%), "
        f"DOWN = {len(followed_down)} ({len(followed_down) / len(down_triggers) * 100:.0f}%)."
    )
    lines.append("")

    # ─── MEASUREMENT A ───────────────────────────────────────
    lines.append("## Measurement A — Reach Rates")
    lines.append("")
    lines.append(
        "For each target TF x direction x zone x window: reach % on ALL triggers "
        "and on the M30-FOLLOWED subset."
    )
    lines.append("")

    zone_order = ["FAR", "MID", "NEAR", "AT/BEYOND"]
    for tf_name, _ in TARGETS:
        lines.append(f"### {tf_name}")
        lines.append("")
        for N in WINDOWS:
            lines.append(f"**Window N={N} rows ({N * 5} minutes)**")
            lines.append("")
            lines.append(
                f"| Zone | Direction | ALL Reach % (n) | FOLLOWED Reach % (n) |"
            )
            lines.append(f"|------|-----------|-----------------|---------------------|")
            for zone in zone_order:
                for d in ["UP", "DOWN"]:
                    all_data = meas_a_results[tf_name][zone][d][N]["all"]
                    fol_data = meas_a_results[tf_name][zone][d][N]["followed"]
                    all_pct = all_data["reached"] / all_data["total"] * 100 if all_data["total"] > 0 else 0
                    fol_pct = fol_data["reached"] / fol_data["total"] * 100 if fol_data["total"] > 0 else 0
                    low_all = " *" if all_data["total"] < 15 else ""
                    low_fol = " *" if fol_data["total"] < 15 else ""
                    lines.append(
                        f"| {zone} | {d} | {all_pct:.0f}% (n={all_data['total']}){low_all} | "
                        f"{fol_pct:.0f}% (n={fol_data['total']}){low_fol} |"
                    )
            lines.append("")
        lines.append("* = low sample (n < 15)")
        lines.append("")

    # ─── MEASUREMENT B ───────────────────────────────────────
    lines.append("## Measurement B — Base-Rate Lift")
    lines.append("")
    lines.append(
        "Unconditional: from ALL rows in a zone (no trigger), how often does the band "
        "get reached within N=48? Lift = trigger-conditioned reach / unconditional reach."
    )
    lines.append("")

    for tf_name, _ in TARGETS:
        lines.append(f"### {tf_name}")
        lines.append("")
        lines.append("| Zone | Direction | Trigger Reach % | Base Rate % | Lift |")
        lines.append(f"|------|-----------|-----------------|-------------|------|")
        for zone in zone_order:
            for d in ["UP", "DOWN"]:
                # Trigger-conditioned: from Measurement A, ALL triggers, N=48
                trig_pct = 0
                trig_data = meas_a_results[tf_name][zone][d][48]["all"]
                trig_pct = trig_data["reached"] / trig_data["total"] * 100 if trig_data["total"] > 0 else 0

                # Base rate
                base_data = meas_b_results[tf_name][zone][d]
                base_pct = base_data["reached"] / base_data["total"] * 100 if base_data["total"] > 0 else 0
                lift = (trig_pct / base_pct) if base_pct > 0 else 0

                lines.append(
                    f"| {zone} | {d} | {trig_pct:.0f}% | {base_pct:.0f}% | {lift:.2f}x |"
                )
        lines.append("")

    # ─── MEASUREMENT C ───────────────────────────────────────
    lines.append("## Measurement C — The At-Band Question")
    lines.append("")
    lines.append(
        "For triggers firing in AT/BEYOND zone: does bbloc hold at the band for 12 rows "
        "(ride) or move away from it (reject)? "
        "UP: hold >= 9, reject = falls < 7. DOWN: hold <= 1, reject = rises > 3."
    )
    lines.append("")

    total_at_all = 0
    for tf_name, _ in TARGETS:
        r = meas_c_results[tf_name]
        total_at_all += r["total"]

    lines.append(
        f"**AT/BEYOND triggers across all targets:** {total_at_all} "
        f"(note: a single trigger can be AT/BEYOND for multiple targets, "
        f"so this sum exceeds the {len(triggers)} total triggers)."
    )
    lines.append("")
    lines.append("| Target | AT/BEYOND Triggers | Ride (holds band 12 rows) | Reject (moves away) | Ride % |")
    lines.append(f"|--------|-------------------|--------------------------|--------------------|--------|")
    for tf_name, bbloc_key in TARGETS:
        r = meas_c_results[tf_name]
        ride_pct = r["ride"] / r["total"] * 100 if r["total"] > 0 else 0
        lines.append(
            f"| {tf_name} | {r['total']} | {r['ride']} | {r['reject']} | {ride_pct:.0f}% |"
        )
    lines.append("")

    # ─── VERDICT ─────────────────────────────────────────────
    lines.append("## VERDICT")
    lines.append("")
    lines.append("**Criteria applied mechanically at N=48 on M30-FOLLOWED subset — no post-hoc adjustment.**")
    lines.append("")
    lines.append("| Criterion | Threshold | Actual | Result |")
    lines.append(f"|-----------|-----------|--------|--------|")
    lines.append(
        f"| C1: H4 reach from MID+FAR >= 40% | >= 40% | "
        f"{c1_result['pct'] * 100:.1f}% | {'PASS' if c1_result['pass'] else 'FAIL'} |"
    )
    lines.append(
        f"| C2: any target NEAR+MID >= 60% | >= 60% | "
        f"{c2_result['best_target']} at {c2_result['best_pct'] * 100:.1f}% | "
        f"{'PASS' if c2_result['pass'] else 'FAIL'} |"
    )
    c3_detail = "No violation" if c3_result["pass"] else c3_result["detail"]
    lines.append(
        f"| C3: NEAR >= FAR (sanity) | No violation | {c3_detail} | "
        f"{'PASS' if c3_result['pass'] else 'FAIL'} |"
    )
    lines.append("")

    all_pass = c1_result["pass"] and c2_result["pass"] and c3_result["pass"]
    if all_pass:
        lines.append(
            "**CONCLUSION: ALL CRITERIA PASS.** Structural band targets are grounded. "
            f"{c2_result['best_target']} band is the recommended default take-profit "
            f"({c2_result['best_pct'] * 100:.0f}% reach from NEAR+MID)."
        )
    else:
        failed_parts = []
        if not c1_result["pass"]:
            failed_parts.append(f"C1: H4 reach {c1_result['pct'] * 100:.1f}% from MID+FAR")
        if not c2_result["pass"]:
            failed_parts.append(
                f"C2: best target {c2_result['best_target']} at "
                f"{c2_result['best_pct'] * 100:.1f}% from NEAR+MID"
            )
        if not c3_result["pass"]:
            failed_parts.append(f"C3: {c3_result['detail']}")
        lines.append(
            f"**CONCLUSION: CRITERIA FAILED.** " + "; ".join(failed_parts) + ". "
        )
        # Recommendation
        if c2_result["pass"]:
            lines.append(
                f"Recommendation: {c2_result['best_target']} band as default take-profit "
                f"({c2_result['best_pct'] * 100:.0f}% reach from NEAR+MID)."
            )
        elif not c2_result["pass"]:
            lines.append(
                "No structural target meets the bar. Recommendation: use fixed-RR "
                "until V36.11 backtest provides price-level targets."
            )
        if not c3_result["pass"]:
            lines.append(
                f"WARNING: C3 violation ({c3_result['detail']}). "
                "Investigate data/definition before trusting any reach numbers."
            )
    lines.append("")

    # ─── LIMITATIONS ─────────────────────────────────────────
    lines.append("## LIMITATIONS")
    lines.append("")
    lines.append(
        "1. **Reach is not profit.** Price can stop you out on the way, then reach the "
        "band. This measurement has no stops, no path analysis — only endpoint reach."
    )
    lines.append(
        "2. **bbloc-distance is not price-RR.** Band prices are not logged in this data. "
        "Real risk-reward waits for the V36.11 backtest with price-level targets."
    )
    lines.append(
        "3. **Weekend row-index caveat.** Rows are M5 bar index, not wall-clock. "
        "Weekend gaps mean 48 rows may cover > 4 hours of real time on Friday, "
        "or < 4 hours on a continuous session."
    )
    lines.append(
        "4. **Sparse bbloc scale.** H1/M30/M15 bbloc uses sparse values (0,1,3,5,7,9,10). "
        "Zone boundaries may not be equidistant in price terms."
    )
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(
        "*Analysis generated by `scripts/analyze_target_reach.py`. "
        "Deterministic — re-running produces identical numbers.*"
    )

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
