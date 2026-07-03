#!/usr/bin/env python3
"""
Tier 2 Reach Analysis — For detector triggers with M30 already at/beyond its band,
does the H1 band get reached? Decides cascade-vs-skip for the at-band majority.

TIER 1 (done): M30 band as default TP — 98% reach from NEAR+MID (C2 PASS).
But ~68% of followed triggers fire with M30 already at/beyond — M30 TP is incoherent.
TIER 2: for those triggers, does H1 band get reached?

Verdict criteria (FIXED, no post-hoc adjustment):
  T2-1 (reach): pooled H1-band reach >= 50% (FOLLOWED, N=48, NEAR+MID, dirs pooled)
  T2-2 (lift): pooled lift >= 1.3x
  BOTH PASS -> cascade rule lives. EITHER FAILS -> skip rule.
"""

import re
import sys
from collections import defaultdict

LOG_PATH = r"references/Backtest_data/V36.10/20260703_clean.log"
REPORT_PATH = "references/TIER2_REACH_ANALYSIS.md"

K_M30_FOLLOW = 12
WINDOWS = [12, 24, 48, 96]
N_VERDICT = 48

T2_REACH_THRESHOLD = 0.50
T2_LIFT_THRESHOLD = 1.3


# ─── PARSING (same as analyze_target_reach.py) ─────────────────

def parse_log(path):
    """Parse DUALTF rows — includes bbloc fields."""
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
            rows.append({
                "dt": m.group(1),
                "d1_state": m.group(2),
                "h4_state": m.group(4),
                "h1_state": m.group(6),
                "m30_state": m.group(8),
                "m15_state": m.group(10),
                "d1bbloc": int(m.group(3)),
                "h4bbloc": int(m.group(5)),
                "h1bbloc": int(m.group(7)),
                "m30bbloc": int(m.group(9)),
                "m15bbloc": int(m.group(11)),
            })
    return rows


def find_triggers(rows):
    """Find M15 flips to F (UP) or R (DOWN) — both states non-X."""
    triggers = []
    for i in range(1, len(rows)):
        if rows[i]["m15_state"] == "X" or rows[i - 1]["m15_state"] == "X":
            continue
        if rows[i]["m15_state"] != rows[i - 1]["m15_state"]:
            if rows[i]["m15_state"] in ("F", "R"):
                triggers.append({
                    "index": i,
                    "direction": "UP" if rows[i]["m15_state"] == "F" else "DOWN",
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


def band_reached(rows, trigger, bbloc_key, N):
    """
    Check if target TF's bbloc reaches the band within N rows.
    UP: bbloc >= 9. DOWN: bbloc <= 1 (and != -1).
    Returns None if bbloc == -1 at trigger row (excluded).
    """
    j = trigger["index"]
    if rows[j][bbloc_key] == -1:
        return None
    for fwd in range(j + 1, min(j + N + 1, len(rows))):
        bb = rows[fwd][bbloc_key]
        if bb == -1:
            continue
        if trigger["direction"] == "UP" and bb >= 9:
            return True
        if trigger["direction"] == "DOWN" and bb <= 1:
            return True
    return False


def is_at_band(rows, trigger):
    """Check if M30 is at/beyond its band at the trigger row."""
    j = trigger["index"]
    m30bb = rows[j]["m30bbloc"]
    if m30bb == -1:
        return False
    if trigger["direction"] == "UP" and m30bb >= 9:
        return True
    if trigger["direction"] == "DOWN" and m30bb <= 1:
        return True
    return False


def h1_zone(bbloc, direction):
    """
    H1 zone classification at trigger row.
    UP (band at 9): AT/BEYOND={9,10}, NEAR={7,8}, MID={4,5,6}, FAR={0..3}
    DOWN (mirror): AT/BEYOND={0,1}, NEAR={2,3}, MID={4,5,6}, FAR={7..10}
    """
    if direction == "UP":
        if bbloc in (9, 10):
            return "AT/BEYOND"
        elif bbloc in (7, 8):
            return "NEAR"
        elif bbloc in (4, 5, 6):
            return "MID"
        else:
            return "FAR"
    else:
        if bbloc in (0, 1):
            return "AT/BEYOND"
        elif bbloc in (2, 3):
            return "NEAR"
        elif bbloc in (4, 5, 6):
            return "MID"
        else:
            return "FAR"


def is_h1_at_band(rows, trigger):
    """Check if H1 is also at/beyond its band at the trigger row (tier-3 population)."""
    j = trigger["index"]
    h1bb = rows[j]["h1bbloc"]
    if h1bb == -1:
        return False
    if trigger["direction"] == "UP" and h1bb >= 9:
        return True
    if trigger["direction"] == "DOWN" and h1bb <= 1:
        return True
    return False


# ─── MEASUREMENT A ──────────────────────────────────────────────

def measurement_a(rows, at_band_triggers):
    """
    For at-band triggers: H1-band reach % per h1-zone x direction x N.
    ALL and FOLLOWED subsets.
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

    for trig in at_band_triggers:
        j = trig["index"]
        h1bb = rows[j]["h1bbloc"]
        if h1bb == -1:
            continue  # exclude if h1bbloc no-data
        followed = is_m30_followed(rows, trig)
        zone = h1_zone(h1bb, trig["direction"])

        for N in WINDOWS:
            reached = band_reached(rows, trig, "h1bbloc", N)
            if reached is None:
                continue
            # Count in "all"
            result[zone][trig["direction"]][N]["all"]["total"] += 1
            if reached:
                result[zone][trig["direction"]][N]["all"]["reached"] += 1
            # Count in "followed"
            if followed:
                result[zone][trig["direction"]][N]["followed"]["total"] += 1
                if reached:
                    result[zone][trig["direction"]][N]["followed"]["reached"] += 1

    return result


# ─── H1-ZONE DISTRIBUTION ───────────────────────────────────────

def h1_zone_distribution(rows, at_band_triggers):
    """How many at-band triggers fire with H1 in each zone."""
    zone_order = ["FAR", "MID", "NEAR", "AT/BEYOND"]
    dist = {z: 0 for z in zone_order}
    for trig in at_band_triggers:
        j = trig["index"]
        h1bb = rows[j]["h1bbloc"]
        if h1bb == -1:
            continue
        zone = h1_zone(h1bb, trig["direction"])
        dist[zone] += 1
    return dist


# ─── MEASUREMENT B ──────────────────────────────────────────────

def measurement_b(rows, N=N_VERDICT):
    """
    Unconditional: from ALL rows where m30bbloc is at/beyond AND h1bbloc is
    in the same zone (no trigger), how often is H1 band reached within N?
    Pooled across directions for thin cells.
    Returns: dict[zone] = {"reached": count, "total": count}
    """
    zone_order = ["FAR", "MID", "NEAR", "AT/BEYOND"]
    result = {z: {"reached": 0, "total": 0} for z in zone_order}

    for i in range(len(rows)):
        m30bb = rows[i]["m30bbloc"]
        h1bb = rows[i]["h1bbloc"]
        if m30bb == -1 or h1bb == -1:
            continue

        # Check if m30 is at/beyond its band — need direction context
        # Use m15_state as direction proxy (F=up, R=down)
        if rows[i]["m15_state"] not in ("F", "R"):
            continue
        direction = "UP" if rows[i]["m15_state"] == "F" else "DOWN"

        # Is m30 at/beyond?
        if direction == "UP" and m30bb < 9:
            continue
        if direction == "DOWN" and m30bb > 1:
            continue

        zone = h1_zone(h1bb, direction)

        # Does H1 band get reached within N?
        reached = False
        for fwd in range(i + 1, min(i + N + 1, len(rows))):
            h1bb_fwd = rows[fwd]["h1bbloc"]
            if h1bb_fwd == -1:
                continue
            if direction == "UP" and h1bb_fwd >= 9:
                reached = True
                break
            if direction == "DOWN" and h1bb_fwd <= 1:
                reached = True
                break

        result[zone]["total"] += 1
        if reached:
            result[zone]["reached"] += 1

    return result


# ─── MEASUREMENT C ──────────────────────────────────────────────

def measurement_c(rows, at_band_triggers, N):
    """
    Tier-3: at-band triggers where H1 is ALSO at/beyond.
    Measure H4-band reach within N rows.
    """
    tier3_triggers = []
    for trig in at_band_triggers:
        j = trig["index"]
        h1bb = rows[j]["h1bbloc"]
        if h1bb == -1:
            continue
        if not is_h1_at_band(rows, trig):
            continue
        tier3_triggers.append(trig)

    h4_reached = 0
    h4_followed_reached = 0
    h4_followed_count = 0

    for trig in tier3_triggers:
        reached = band_reached(rows, trig, "h4bbloc", N)
        if reached is None:
            continue
        if reached:
            h4_reached += 1
        followed = is_m30_followed(rows, trig)
        if followed:
            h4_followed_count += 1
            if reached:
                h4_followed_reached += 1

    return {
        "count": len(tier3_triggers),
        "h4_reached": h4_reached,
        "h4_total": len(tier3_triggers),  # all tier-3 triggers counted
        "h4_followed_reached": h4_followed_reached,
        "h4_followed_count": h4_followed_count,
    }


# ─── MAIN ───────────────────────────────────────────────────────

def main():
    print("Parsing log file...")
    rows = parse_log(LOG_PATH)
    print(f"  Parsed {len(rows)} DUALTF rows.")

    print("Finding triggers...")
    triggers = find_triggers(rows)
    up_triggers = [t for t in triggers if t["direction"] == "UP"]
    down_triggers = [t for t in triggers if t["direction"] == "DOWN"]
    print(f"  Total triggers: {len(triggers)} (UP={len(up_triggers)}, DOWN={len(down_triggers)})")

    # At-band triggers (M30 at/beyond)
    at_band_triggers = [t for t in triggers if is_at_band(rows, t)]
    at_band_up = [t for t in at_band_triggers if t["direction"] == "UP"]
    at_band_down = [t for t in at_band_triggers if t["direction"] == "DOWN"]
    print(f"  At-band triggers: {len(at_band_triggers)} (UP={len(at_band_up)}, DOWN={len(at_band_down)})")

    # Match-check against TARGET_REACH_ANALYSIS
    at_band_up_followed = [t for t in at_band_up if is_m30_followed(rows, t)]
    at_band_down_followed = [t for t in at_band_down if is_m30_followed(rows, t)]
    print(f"  At-band UP followed: {len(at_band_up_followed)}")
    print(f"  At-band DOWN followed: {len(at_band_down_followed)}")

    # Sanity anchor: should match 111/111 (ALL) and 63/53 (FOLLOWED)
    if len(at_band_up) != 111 or len(at_band_down) != 111:
        print(f"  WARNING: At-band ALL counts {len(at_band_up)}/{len(at_band_down)} != 111/111")
    if len(at_band_up_followed) != 63 or len(at_band_down_followed) != 53:
        print(f"  WARNING: At-band FOLLOWED counts {len(at_band_up_followed)}/{len(at_band_down_followed)} != 63/53")

    # H1 zone distribution
    h1_dist = h1_zone_distribution(rows, at_band_triggers)
    print(f"\n  H1 zone distribution: {h1_dist}")

    # Measurement A
    print(f"\n--- Measurement A ---")
    meas_a = measurement_a(rows, at_band_triggers)

    # Measurement B
    print(f"\n--- Measurement B ---")
    meas_b = measurement_b(rows)
    for zone, data in meas_b.items():
        pct = data["reached"] / data["total"] * 100 if data["total"] > 0 else 0
        print(f"  {zone}: {data['reached']}/{data['total']} = {pct:.0f}%")

    # Measurement C
    print(f"\n--- Measurement C ---")
    meas_c = measurement_c(rows, at_band_triggers, N_VERDICT)
    print(f"  Tier-3 count: {meas_c['count']}")
    print(f"  H4 reach (ALL): {meas_c['h4_reached']}/{meas_c['h4_total']}")
    print(f"  H4 reach (FOLLOWED): {meas_c['h4_followed_reached']}/{meas_c['h4_followed_count']}")

    # ─── VERDICT ─────────────────────────────────────────────
    # Pooled: FOLLOWED, N=48, NEAR+MID, both directions
    pooled_reached = 0
    pooled_total = 0
    for zone in ["NEAR", "MID"]:
        for d in ["UP", "DOWN"]:
            data = meas_a[zone][d][48]["followed"]
            pooled_reached += data["reached"]
            pooled_total += data["total"]
    pooled_pct = pooled_reached / pooled_total if pooled_total > 0 else 0

    # Base rate for pooled: average of NEAR+MID base rates
    base_pooled_reached = meas_b["NEAR"]["reached"] + meas_b["MID"]["reached"]
    base_pooled_total = meas_b["NEAR"]["total"] + meas_b["MID"]["total"]
    base_pooled_pct = base_pooled_reached / base_pooled_total if base_pooled_total > 0 else 0

    # Trigger-conditioned reach for pooled: same as meas_a but ALL triggers (not just followed)
    trig_pooled_reached = 0
    trig_pooled_total = 0
    for zone in ["NEAR", "MID"]:
        for d in ["UP", "DOWN"]:
            data = meas_a[zone][d][48]["all"]
            trig_pooled_reached += data["reached"]
            trig_pooled_total += data["total"]
    trig_pooled_pct = trig_pooled_reached / trig_pooled_total if trig_pooled_total > 0 else 0

    pooled_lift = trig_pooled_pct / base_pooled_pct if base_pooled_pct > 0 else 0

    t2_1_pass = pooled_pct >= T2_REACH_THRESHOLD
    t2_2_pass = pooled_lift >= T2_LIFT_THRESHOLD

    print(f"\n--- VERDICT ---")
    print(f"  T2-1 (reach >= 50%): {pooled_pct * 100:.1f}% -> {'PASS' if t2_1_pass else 'FAIL'}")
    print(f"  T2-2 (lift >= 1.3x): {pooled_lift:.2f}x -> {'PASS' if t2_2_pass else 'FAIL'}")

    if t2_1_pass and t2_2_pass:
        print("  ** TIER 2 LIVES ** — Cascade rule adopted.")
    else:
        failed = []
        if not t2_1_pass:
            failed.append(f"T2-1: reach {pooled_pct * 100:.1f}%")
        if not t2_2_pass:
            failed.append(f"T2-2: lift {pooled_lift:.2f}x")
        print(f"  ** TIER 2 DEAD ** — Skip rule. Failed: {', '.join(failed)}")

    # ─── WRITE REPORT ────────────────────────────────────────
    write_report(
        rows, triggers, at_band_triggers,
        at_band_up, at_band_down,
        at_band_up_followed, at_band_down_followed,
        h1_dist, meas_a, meas_b, meas_c,
        t2_1_pass, t2_2_pass,
        pooled_pct, pooled_lift,
        pooled_reached, pooled_total,
        trig_pooled_pct, base_pooled_pct,
    )
    print(f"\nReport written to {REPORT_PATH}")


def write_report(
    rows, triggers, at_band_triggers,
    at_band_up, at_band_down,
    at_band_up_followed, at_band_down_followed,
    h1_dist, meas_a, meas_b, meas_c,
    t2_1_pass, t2_2_pass,
    pooled_pct, pooled_lift,
    pooled_reached, pooled_total,
    trig_pooled_pct, base_pooled_pct,
):
    """Write TIER2_REACH_ANALYSIS.md."""
    lines = []

    lines.append("# Tier 2 Reach Analysis")
    lines.append("")
    lines.append(
        "> For detector triggers with M30 already at/beyond its band (~68% of followed triggers), "
        "does the H1 band get reached? Decides cascade-vs-skip for the at-band majority."
    )
    lines.append("")

    # ─── DATA SUMMARY ────────────────────────────────────────
    lines.append("## Data Summary")
    lines.append("")
    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Total DUALTF rows | {len(rows)} |")
    lines.append(f"| Total triggers | {len(triggers)} |")
    lines.append(f"| At-band triggers (M30 at/beyond) | {len(at_band_triggers)} |")
    lines.append(f"| At-band UP | {len(at_band_up)} |")
    lines.append(f"| At-band DOWN | {len(at_band_down)} |")
    lines.append(f"| At-band UP followed | {len(at_band_up_followed)} |")
    lines.append(f"| At-band DOWN followed | {len(at_band_down_followed)} |")
    lines.append("")

    # Match-check
    lines.append("### Match-Check Against TARGET_REACH_ANALYSIS")
    lines.append("")
    match_all = len(at_band_up) == 111 and len(at_band_down) == 111
    match_fol = len(at_band_up_followed) == 63 and len(at_band_down_followed) == 53
    lines.append(f"| Check | Expected | Actual | Match |")
    lines.append(f"|-------|----------|--------|-------|")
    lines.append(
        f"| At-band ALL UP | 111 | {len(at_band_up)} | "
        f"{'YES' if len(at_band_up) == 111 else 'NO'} |"
    )
    lines.append(
        f"| At-band ALL DOWN | 111 | {len(at_band_down)} | "
        f"{'YES' if len(at_band_down) == 111 else 'NO'} |"
    )
    lines.append(
        f"| At-band FOLLOWED UP | 63 | {len(at_band_up_followed)} | "
        f"{'YES' if len(at_band_up_followed) == 63 else 'NO'} |"
    )
    lines.append(
        f"| At-band FOLLOWED DOWN | 53 | {len(at_band_down_followed)} | "
        f"{'YES' if len(at_band_down_followed) == 53 else 'NO'} |"
    )
    lines.append("")

    # H1 zone distribution
    lines.append("### H1 Zone Distribution of At-Band Triggers")
    lines.append("")
    lines.append("| Zone | Count | % |")
    lines.append(f"|------|-------|---|")
    for zone in ["FAR", "MID", "NEAR", "AT/BEYOND"]:
        cnt = h1_dist[zone]
        pct = cnt / len(at_band_triggers) * 100 if at_band_triggers else 0
        lines.append(f"| {zone} | {cnt} | {pct:.1f}% |")
    lines.append("")

    # ─── MEASUREMENT A ───────────────────────────────────────
    lines.append("## Measurement A — Tier-2 Reach")
    lines.append("")
    lines.append(
        "For at-band triggers: H1-band reach % per h1-zone x direction x window. "
        "ALL and FOLLOWED subsets."
    )
    lines.append("")

    zone_order = ["FAR", "MID", "NEAR", "AT/BEYOND"]
    for N in WINDOWS:
        lines.append(f"**Window N={N} rows ({N * 5} minutes)**")
        lines.append("")
        lines.append(
            "| Zone | Direction | ALL Reach % (n) | FOLLOWED Reach % (n) |"
        )
        lines.append(f"|------|-----------|-----------------|---------------------|")
        for zone in zone_order:
            for d in ["UP", "DOWN"]:
                all_data = meas_a[zone][d][N]["all"]
                fol_data = meas_a[zone][d][N]["followed"]
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
        "Unconditional: from ALL rows (no trigger) where m30bbloc is at/beyond "
        "AND h1bbloc is in the given zone, how often is H1 band reached within N=48? "
        "Lift = trigger-conditioned reach / unconditional reach."
    )
    lines.append("")
    lines.append(
        "**Pooling:** trigger-conditioned uses ALL triggers (NEAR+MID pooled, both directions). "
        "Base rate uses NEAR+MID pooled, both directions."
    )
    lines.append("")
    lines.append("| Zone | Trigger Reach % (n) | Base Rate % (n) | Lift |")
    lines.append(f"|------|---------------------|-----------------|------|")
    for zone in zone_order:
        trig_pct = 0
        trig_n = 0
        for d in ["UP", "DOWN"]:
            data = meas_a[zone][d][48]["all"]
            trig_n += data["total"]
            trig_pct += data["reached"]
        trig_pct_pct = trig_pct / trig_n * 100 if trig_n > 0 else 0
        base_pct = meas_b[zone]["reached"] / meas_b[zone]["total"] * 100 if meas_b[zone]["total"] > 0 else 0
        lift = trig_pct_pct / base_pct if base_pct > 0 else 0
        lines.append(
            f"| {zone} | {trig_pct_pct:.0f}% (n={trig_n}) | {base_pct:.0f}% (n={meas_b[zone]['total']}) | {lift:.2f}x |"
        )
    lines.append("")

    # Pooled summary
    lines.append("**Pooled (NEAR+MID, both directions):**")
    lines.append("")
    lines.append(
        f"| | Trigger Reach % | Base Rate % | Lift |"
    )
    lines.append(f"|---|-----------------|-------------|------|")
    lines.append(
        f"| NEAR+MID | {trig_pooled_pct * 100:.1f}% (n={pooled_total}) | "
        f"{base_pooled_pct * 100:.1f}% | {pooled_lift:.2f}x |"
    )
    lines.append("")

    # ─── MEASUREMENT C ───────────────────────────────────────
    lines.append("## Measurement C — Tier-3 (Informational)")
    lines.append("")
    lines.append(
        "At-band triggers where H1 is ALSO at/beyond. H4-band reach at N=48."
    )
    lines.append("")

    tier3_pct_of_atband = meas_c["count"] / len(at_band_triggers) * 100 if at_band_triggers else 0
    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Tier-3 trigger count | {meas_c['count']} |")
    lines.append(f"| % of at-band triggers | {tier3_pct_of_atband:.1f}% |")
    lines.append(
        f"| H4 reach (ALL) | {meas_c['h4_reached']}/{meas_c['h4_total']} = "
        f"{meas_c['h4_reached'] / meas_c['h4_total'] * 100:.0f}%"
        + (" (*)" if meas_c['h4_total'] < 15 else "")
        + " |"
    )
    lines.append(
        f"| H4 reach (FOLLOWED) | {meas_c['h4_followed_reached']}/{meas_c['h4_followed_count']} = "
        f"{meas_c['h4_followed_reached'] / meas_c['h4_followed_count'] * 100:.0f}%"
        + (" (*)" if meas_c['h4_followed_count'] < 15 else "")
        + " |"
    )
    lines.append("")

    if meas_c["h4_followed_count"] < 15:
        lines.append(
            "> **Low sample:** tier-3 followed count < 15. "
            "Results are informational only, not verdict-relevant."
        )
        lines.append("")
    else:
        lines.append(
            f"> Tier-3 sample adequate (n={meas_c['h4_followed_count']}). "
            f"H4 reach from tier-3: {meas_c['h4_followed_reached'] / meas_c['h4_followed_count'] * 100:.0f}%."
        )
        lines.append("")

    # ─── VERDICT ─────────────────────────────────────────────
    lines.append("## VERDICT")
    lines.append("")
    lines.append(
        "**Criteria applied mechanically at N=48, FOLLOWED subset, NEAR+MID pooled, "
        "both directions — no post-hoc adjustment.**"
    )
    lines.append("")
    lines.append("| Criterion | Threshold | Actual | Result |")
    lines.append(f"|-----------|-----------|--------|--------|")
    lines.append(
        f"| T2-1: H1 reach >= 50% | >= 50% | "
        f"{pooled_pct * 100:.1f}% (n={pooled_total}) | {'PASS' if t2_1_pass else 'FAIL'} |"
    )
    lines.append(
        f"| T2-2: Lift >= 1.3x | >= 1.3x | "
        f"{pooled_lift:.2f}x | {'PASS' if t2_2_pass else 'FAIL'} |"
    )
    lines.append("")

    if t2_1_pass and t2_2_pass:
        lines.append(
            "**CONCLUSION: TIER 2 LIVES.** Cascade rule adopted for Part 5: "
            "when M30 is at/beyond its band, target the H1 band next. "
            f"H1 reach from NEAR+MID = {pooled_pct * 100:.1f}% with {pooled_lift:.2f}x lift."
        )
    else:
        failed_parts = []
        if not t2_1_pass:
            failed_parts.append(f"T2-1: reach {pooled_pct * 100:.1f}% < 50%")
        if not t2_2_pass:
            failed_parts.append(f"T2-2: lift {pooled_lift:.2f}x < 1.3x")
        lines.append(
            f"**CONCLUSION: TIER 2 DEAD.** At-band triggers are SKIPPED. "
            f"Failed: {'; '.join(failed_parts)}. "
            "Part 5 trades only the NEAR/MID minority (where M30 is not yet at the band) "
            "with the M30-band TP. No cascade for the at-band majority."
        )
    lines.append("")

    # ─── LIMITATIONS ─────────────────────────────────────────
    lines.append("## LIMITATIONS")
    lines.append("")
    lines.append(
        "1. **Reach is not profit.** Price can stop you out on the way, then reach "
        "the band. No stops, no path analysis — only endpoint reach."
    )
    lines.append(
        "2. **bbloc-distance is not price-RR.** Band prices not logged. "
        "Real risk-reward waits for V36.11 backtest."
    )
    lines.append(
        "3. **Small cells.** Some zone/direction combos have n < 15. Flagged with *. "
        "Do not over-interpret individual cells."
    )
    lines.append(
        "4. **Weekend row-index caveat.** Rows are M5 bar index, not wall-clock. "
        "48 rows may cover > 4 hours on Friday or < 4 hours mid-session."
    )
    lines.append(
        "5. **Tier-2 delay is not fill quality.** A trigger that reaches H1 band at "
        "row j+47 is technically 'reached' but the price move may have been too late "
        "to capture meaningful profit after the M30 band was already exhausted."
    )
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(
        "*Analysis generated by `scripts/analyze_tier2_reach.py`. "
        "Deterministic — re-running produces identical numbers.*"
    )

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
