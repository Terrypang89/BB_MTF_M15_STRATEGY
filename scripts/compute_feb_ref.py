#!/usr/bin/env python3
# Extract February per-day reference data from the log

import re
from collections import defaultdict

LOG_PATH = "references/Backtest_data/V36.15/20260712_clean.log"

# Regex to match M5, M30, H1, H4 close_M5 values
# Regex for M15 close_M15 (M15 is every 15 min; first value of each M15 bar)
m15_close_re = re.compile(
    r"(?P<date_time>\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2})"
    r".*close_M15:\[\s*(?P<close>[-\d.]+)"
)

# Group M15 data by date (YYYY.MM.DD)
feb_data = defaultdict(list)

with open(LOG_PATH, "r", encoding="utf-8") as f:
    for line in f:
        m = m15_close_re.search(line)
        if m:
            dt_str = m.group("date_time")
            close = float(m.group("close"))
            # Extract just the date part (first 10 chars: YYYY.MM.DD)
            date = dt_str[:10]
            feb_data[date].append((dt_str, close))

# Filter to February 2026 only
feb_2026 = {d: bars for d, bars in feb_data.items() if d.startswith("2026.02.")}

# Sort by date
for date in sorted(feb_2026.keys()):
    bars = feb_2026[date]
    bars.sort(key=lambda x: x[0])  # sort by datetime string

    # Compute per-day stats from close_M5 values (M5 bars)
    close_vals = [b[1] for b in bars]
    open_val = close_vals[0]
    close_val = close_vals[-1]
    net = abs(close_val - open_val)
    high = max(close_vals)
    low = min(close_vals)
    range_ = high - low
    path = sum(abs(close_vals[i] - close_vals[i-1]) for i in range(1, len(close_vals)))

    er = net / path if path != 0 else 0.0

    print(f"{date} | {len(bars):3d} | {open_val:8.2f} | {close_val:8.2f} | "
          f"{net:6.2f} | {range_:6.2f} | {path:10.2f} | {er:.3f}")
