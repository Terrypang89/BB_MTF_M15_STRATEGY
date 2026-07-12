#!/usr/bin/env python3
"""
touch_events_list.py — DIAGNOSTIC listing of H4 touch events

Reuses the existing parse from touch_reversal_test.py.
Outputs a markdown table with all 115 touch events, chronological.

Columns:
  # | datetime | H4 touch value | H4 state | M30 state | H1 state | predicted dir | reverted Y/N | bars-to-midline

This is NOT a verdict — it mirrors the already-computed touch rate (49.6%).
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SYSLOG_PATH = ROOT / "references" / "Backtest_data" / "V36.14" / "20260706_clean.log"

# Import the shared parse functions from touch_reversal_test.py
# We copy them here to keep this script self-contained and avoid modifying
# touch_reversal_test.py (which is used for the actual test).
import re

def read_log(path: Path):
    """Read the plain-text clean log and yield dicts of parsed fields per bar.
    Reuses the same logic as touch_reversal_test.py."""
    with open(path, encoding="utf-8") as f:
        raw_lines = [line.replace("\r", "").strip() for line in f if line.strip()]

    n = len(raw_lines)
    dualtf_by_ts = {}
    atrs_by_ts = {}
    close_by_ts = {}
    touch_data = {}

    # Parse DUALTF lines
    for idx, r in enumerate(raw_lines):
        if "[DUALTF]" not in r:
            continue
        d = {}
        m = re.search(r"h4:state:([SFCR])", r)
        d["h4_state"] = m.group(1) if m else None
        m = re.search(r"m30:state:([SFCR])", r)
        d["m30_state"] = m.group(1) if m else None
        m = re.search(r"h1:state:([SFCR])", r)
        d["h1_state"] = m.group(1) if m else None
        ts_match = re.match(r"(\d{4}\.\d{2}\.\d{2}) (\d{2}):", r)
        if ts_match:
            date_str = ts_match.group(1)
            hour = int(ts_match.group(2))
            minute_key = hour * 15
            ts = f"{date_str}:{minute_key:02d}"
            dualtf_by_ts[ts] = d

    # Parse ATRSL1buf lines
    for idx, r in enumerate(raw_lines):
        if "[ATRSL1buf]" not in r:
            continue
        bb_mid, bb_up, bb_low = None, None, None
        upper_match = re.search(r"Upper:\s*\[(.*?)\]", r)
        mid_match = re.search(r"SLMid:\s*\[(.*?)\]", r)
        lower_match = re.search(r"Lower:\s*\[(.*?)\]", r)
        if upper_match:
            vals = [float(v.strip()) for v in upper_match.group(1).split(",") if v.strip()]
            bb_up = vals[0] if vals else None
            bb_mid = vals[1] if len(vals) >= 2 else None
        if mid_match:
            vals = [float(v.strip()) for v in mid_match.group(1).split(",") if v.strip()]
            bb_mid = vals[0] if vals else None
        if lower_match:
            vals = [float(v.strip()) for v in lower_match.group(1).split(",") if v.strip()]
            bb_low = vals[0] if vals else None
        ts_match = re.match(r"(\d{4}\.\d{2}\.\d{2}) (\d{2}):", r)
        if ts_match:
            date_str = ts_match.group(1)
            hour = int(ts_match.group(2))
            minute_key = hour * 15
            ts = f"{date_str}:{minute_key:02d}"
            atrs_by_ts[ts] = {"bb_mid": bb_mid, "bb_up": bb_up, "bb_low": bb_low}

    # Parse close from M15 lines
    for idx, r in enumerate(raw_lines):
        if "[M15]" not in r:
            continue
        m15_match = re.search(r"close_M15:\s*\[(.*?)\](?:,\s*|\])", r)
        if not m15_match:
            continue
        vals_str = m15_match.group(1).strip()
        vals = [float(v.strip()) for v in vals_str.split(",") if v.strip()]
        ts_match = re.match(r"(\d{4}\.\d{2}\.\d{2}) (\d{2}):", r)
        if ts_match:
            date_str = ts_match.group(1)
            hour = int(ts_match.group(2))
            minute_key = hour * 15
            ts = f"{date_str}:{minute_key:02d}"
            close_by_ts[ts] = vals[0] if vals else None

    # Parse touch data from BBTFImpact lines — also store raw line for timestamp
    for idx, r in enumerate(raw_lines):
        if "[BBTFImpact]" not in r:
            continue
        try:
            tm = r.split("line_seq_touch:", 1)[1].split("],")[0].strip() if "line_seq_touch:" in r else ""
            h4_cur, h4_prev = None, None
            for part in tm.split(", "):
                part = part.strip()
                if part.startswith("H4_"):
                    sub = part[len("H4_"):]  # e.g. "6-9,9"
                    dash_idx = sub.find("-")
                    if dash_idx == -1:
                        continue
                    cur_str = sub[:dash_idx]
                    after_dash = sub[dash_idx+1:]
                    comma_idx = after_dash.find(",")
                    if comma_idx == -1:
                        continue
                    prev_str = after_dash[:comma_idx]
                    try:
                        h4_cur, h4_prev = int(cur_str), int(prev_str)
                    except ValueError:
                        pass
            ts_match = re.match(r"(\d{4}\.\d{2}\.\d{2}) (\d{2}):", r)
            if ts_match and h4_cur is not None:
                date_str = ts_match.group(1)
                hour = int(ts_match.group(2))
                minute_key = hour * 15
                ts = f"{date_str}:{minute_key:02d}"
                touch_data[ts] = {"cur": h4_cur, "prev": h4_prev, "raw_line": r}
        except Exception:
            pass

    # Yield records — match DUALTF/ATRSL1buf/close for each touch timestamp
    seen_ts = set()
    for ts in touch_data:
        if ts in seen_ts:
            continue
        seen_ts.add(ts)
        d = {"cur": touch_data[ts]["cur"], "prev": touch_data[ts]["prev"], "raw_line": touch_data[ts].get("raw_line", "")}
        dualtf = dualtf_by_ts.get(ts, {})
        d["h4_state"] = dualtf.get("h4_state")
        d["m30_state"] = dualtf.get("m30_state")
        d["h1_state"] = dualtf.get("h1_state")
        atrs = atrs_by_ts.get(ts, {})
        d["bb_mid"] = atrs.get("bb_mid")
        d["bb_up"] = atrs.get("bb_up")
        d["bb_low"] = atrs.get("bb_low")
        d["close"] = close_by_ts.get(ts)
        if all(v is not None for v in (d["h4_state"], d["m30_state"], d["h1_state"],
                                       d["bb_mid"], d["bb_up"], d["bb_low"], d["close"])):
            yield d


def is_touch_event(d: dict) -> bool:
    """Return True if H4 touches a band (cur in {6,7,8,9}) AND it's a NEW touch."""
    return d["cur"] in {6, 7, 8, 9} and d["cur"] != d["prev"]


def predicted_direction(d: dict) -> str:
    """9 or 7 -> DOWN; 6 or 8 -> UP."""
    if d["cur"] in {9, 7}:
        return "DOWN"
    elif d["cur"] in {6, 8}:
        return "UP"
    return None


def count_reversions(d: dict, target: float, direction: str, horizon: int) -> tuple[bool, int]:
    """Within `horizon` bars after the touch bar, does price reach the midline?
    Returns (reverted, bars_needed) where bars_needed is -1 if never."""
    for i in range(horizon):
        if direction == "UP" and d["close"] >= target:
            return True, i + 1
        if direction == "DOWN" and d["close"] <= target:
            return True, i + 1
    return False, -1


def main():
    # Load all events
    events = list(read_log(SYSLOG_PATH))
    # Filter to actual touch events (cur in {6,7,8,9} and cur != prev)
    touch_events = [d for d in events if is_touch_event(d)]

    HORIZON = 24

    # Build rows - parse timestamp from the raw line
    rows = []
    for d in touch_events:
        # Extract timestamp from the log line (format: YYYY-MM-DD HH:MM)
        ts_match = re.match(r"(\d{4}\.\d{2}\.\d{2}) (\d{2}):", d.get("raw_line", ""))
        if not ts_match:
            # Fallback: use h4_state as placeholder (shouldn't happen with proper data)
            dt_str = f"{d['h4_state']}-{d['m30_state']}-{d['h1_state']}"
        else:
            date_str = ts_match.group(1).replace(".", "")  # YYYYMMDD
            hour = int(ts_match.group(2))
            minute_key = (hour * 15) % 60  # :00, :15, :30, :45
            dt_str = f"{date_str}:{minute_key:02d}"

        pred_dir = predicted_direction(d)
        reverted, bars = count_reversions(d, d["bb_mid"], pred_dir, HORIZON)
        # Reconstruct proper datetime: YYYY-MM-DD HH:MM
        date_part = ts_match.group(1)  # YYYY-MM-DD
        hour = int(ts_match.group(2))
        minute_key = (hour * 15) % 60  # :00, :15, :30, :45
        dt_sortable = f"{date_part} {hour:02d}:{minute_key:02d}"

        rows.append({
            "datetime": dt_sortable,
            "touch": d["cur"],
            "dir": pred_dir,
            "reverted": "Y" if reverted else "N",
            "bars": bars,
            "h4_state": d.get("h4_state"),  # F/S/C/R/X
            "m30_state": d.get("m30_state"),  # F/S/C/R/X
            "h1_state": d.get("h1_state"),  # F/S/C/R/X
        })

    # Sort chronologically by datetime string
    rows.sort(key=lambda r: r["datetime"])

    # Output markdown table with state columns
    header = "| # | datetime | H4 touch | H4 state | M30 state | H1 state | pred dir | reverted | bars |\n"
    header += "|---|---|---|---|---|---|---|---|---|\n"
    print(header)
    for i, r in enumerate(rows):
        # datetime is already properly formatted as "YYYY-MM-DD HH:MM"
        dt_display = r["datetime"]
        print(f"| {i+1} | {dt_display} | {r['touch']} | {r['h4_state']} | {r['m30_state']} | {r['h1_state']} | {r['dir']} | {r['reverted']} | {r['bars'] if r['bars'] != -1 else '-'} |")

    print(f"\n### Summary")
    print(f"- Total H4 touch events listed: {len(rows)}")


if __name__ == "__main__":
    main()
