# fast_subscenario_compute.py
# Computes S1, S2, B2 sub-scenarios from raw V36.15 log fields.
# Includes FLY_PSHRINK state (stage 512/522 with diffBBW < 0).
# Transition/onset detection — fires once per bar at rule onset.
# Deterministic: identical output on re-run.

import os, sys, json
from datetime import datetime
from collections import defaultdict

LOG_FILE = "references/Backtest_data/V36.15/20260712_clean.log"

RESTART_SAFE = {
    "script_missing": not os.path.exists(LOG_FILE.replace("clean.log", "fast_subscenario_compute.py")),
    "report_missing": not os.path.exists("references/FAST_SUBSCENARIO_COMPUTE.md"),
}

# RESTART-SAFETY R1: report initial state
print("Resuming — script missing; report missing; FLY_PSHRINK implemented N/A; pushed N/A.")

def parse_log():
    """Read the log, group lines by minute (same bar), and extract per-TF state."""
    with open(LOG_FILE, encoding="utf-8") as f:
        raw_lines = f.readlines()

    # Skip EA header until we hit a line with (T99)[M15] or (G4G5111)(T14)[M5] etc.
    data_start = 0
    for i, ln in enumerate(raw_lines):
        if "first_stage_M15" in ln or "first_stage_M5" in ln:
            data_start = i
            break
    raw_lines = raw_lines[data_start:]

    # Group by minute: truncate timestamp to the minute
    bar_groups = defaultdict(list)
    for ln in raw_lines:
        ln = ln.strip()
        if not ln or ln.startswith("servers switched off"):
            continue
        ts_match = datetime.strptime(ln[:26], "%Y%m%d %H:%M")
        bar_groups[ts_match].append(ln)

    return bar_groups

def get_tf_state(tf_line, tf_name):
    """Extract W_stage [cur, prev1] and diffBBW[cur] from a TF line."""
    # Pattern: W_stage_<name>:[cur, prev1, prev2], diffBBW_<name>:[cur, prev1, prev2]
    cur_idx = 0
    try:
        cur = int(tf_line.split(f"W_stage_{tf_name}:")[1].split(",")[cur_idx])
        prev1 = int(tf_line.split(f"diffBBW_{tf_name}:")[1].split(",")[cur_idx])
    except Exception:
        cur, prev1 = None, None
    return cur, prev1

def classify_state(cur, prev1):
    """Map stage values to high-level state (FLY, FLY_PSHRINK, SHRINK, SQZ, NONE)."""
    if cur is None:
        return "NONE"
    if prev1 is not None and 400 <= prev1 < 500:
        return "SQZ"
    if 500 <= prev1 < 600:
        return "FLY_PSHRINK" if cur in (512, 522) else ("FLY" if cur >= 0 else "SHRINK")
    if cur >= 0:
        return "FLY"
    return "SHRINK"

def build_per_bar():
    """Construct per-bar dict with M15/M30/H1/H4 states and prev1 for transition checks."""
    bars = {}
    for ts, lines in bar_groups.items():
        m15_cur, m15_prev1 = get_tf_state(lines[0], "M15")
        m30_cur, m30_prev1 = get_tf_state(lines[0], "M30")
        h1_cur, h1_prev1 = get_tf_state(lines[0], "H1")
        h4_cur, h4_prev1 = get_tf_state(lines[0], "H4")
        bars[ts] = {
            "M15": {"cur": m15_cur, "prev1": m15_prev1},
            "M30": {"cur": m30_cur, "prev1": m30_prev1},
            "H1": {"cur": h1_cur, "prev1": h1_prev1},
            "H4": {"cur": h4_cur, "prev1": h4_prev1},
        }
    return bars

def onset_state(tf_name, cur):
    """Return the state for transition detection (FLY_PSHRINK/SHRINK vs FLY)."""
    if cur is None:
        return "NONE"
    prev1 = bars[ts][tf_name]["prev1"]
    if prev1 is not None and 400 <= prev1 < 500:
        return "SQZ"
    if 500 <= prev1 < 600:
        return "FLY_PSHRINK" if cur in (512, 522) else ("FLY" if cur >= 0 else "SHRINK")
    if cur >= 0:
        return "FLY"
    return "SHRINK"

def is_hard_shrink(tf_name, cur):
    """True if the TF entered SHRINK (not FLY_PSHRINK) — i.e. prev1 was SQUEUTE.md`