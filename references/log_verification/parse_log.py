#!/usr/bin/env python3
"""Parse 20260606_clean.log for March 2-20 period, extract H4-boundary samples + trade events."""

import re

LOG_FILE = r"C:\Users\Tofy5\Project\BB_MTF_M15_STRATEGY\references\Backtest_data\V30.02\20260606_clean.log"

DATE_START = "2026.03.02"
DATE_END = "2026.03.20"
END_TIME = "09:00"
H4_HOURS = {"00:00", "04:00", "08:00", "12:00", "16:00", "20:00"}

class TFState:
    def __init__(self):
        self.bbw_stage = None
        self.diff_mid = None
        self.bbudn = None
        self.diff_bbw = None
        self.trend = None

states = {tf: TFState() for tf in ["M15", "M30", "H1", "H4", "D1"]}

LINE_RE = re.compile(r'^(\d{4}\.\d{2}\.\d{2}\s+\d{2}:\d{2}:\d{2})\s+\[(\w+)\]')

def parse_tf_block(line, tf_name):
    st = states[tf_name]
    m = re.search(rf'W_stage_{tf_name}:\(\w+\)\[(\d+)', line)
    if m: st.bbw_stage = int(m.group(1))
    m = re.search(rf'diffMid_Trend_{tf_name}:\[(\d+)', line)
    if m: st.diff_mid = int(m.group(1))
    m = re.search(rf'BBUpDn_{tf_name}:\[(\d)', line)
    if m: st.bbudn = int(m.group(1))
    m = re.search(rf'diffBBW_{tf_name}:\[([-\d.]+)', line)
    if m: st.diff_bbw = float(m.group(1))
    m = re.search(rf'trend_{tf_name}:\[(\d)', line)
    if m: st.trend = int(m.group(1))

def is_in_range(dt_str):
    if dt_str < DATE_START: return False
    if dt_str > DATE_END: return False
    if dt_str == DATE_END:
        if dt_str[11:16] > END_TIME: return False
    return True

snapshots = []
seen_times = set()

with open(LOG_FILE, 'r', encoding='utf-8', errors='replace') as f:
    for line in f:
        line = line.strip()
        if not line: continue
        ts_match = LINE_RE.match(line)
        if not ts_match:
            for tf in ["M15", "M30", "H1", "H4", "D1"]:
                parse_tf_block(line, tf)
            continue

        dt_str = ts_match.group(1)
        tag = ts_match.group(2)
        hhmm = dt_str[11:16]

        if not is_in_range(dt_str):
            if dt_str > DATE_END: break
            continue

        if tag in ["M15", "M30", "H1", "H4", "D1"]:
            parse_tf_block(line, tag)

            # Capture at H4 boundary
            if tag == "H4" and hhmm in H4_HOURS:
                time_key = dt_str[:16]
                if time_key in seen_times:
                    # Update existing snapshot
                    for snap in reversed(snapshots):
                        if snap["time"][:16] == time_key:
                            snap["tf_states"] = {}
                            for tf in ["M15", "M30", "H1", "H4", "D1"]:
                                snap["tf_states"][tf] = {
                                    "bbw": states[tf].bbw_stage,
                                    "mid": states[tf].diff_mid,
                                    "budn": states[tf].bbudn,
                                    "dbbw": states[tf].diff_bbw,
                                }
                            break
                else:
                    seen_times.add(time_key)
                    snap = {
                        "time": dt_str,
                        "hhmm": hhmm,
                        "source": "H4",
                        "tf_states": {}
                    }
                    for tf in ["M15", "M30", "H1", "H4", "D1"]:
                        snap["tf_states"][tf] = {
                            "bbw": states[tf].bbw_stage,
                            "mid": states[tf].diff_mid,
                            "budn": states[tf].bbudn,
                            "dbbw": states[tf].diff_bbw,
                        }
                    snapshots.append(snap)

# Now extract trade events
trade_events = []
with open(LOG_FILE, 'r', encoding='utf-8', errors='replace') as f:
    for line in f:
        line = line.strip()
        if not line: continue
        ts_match = LINE_RE.match(line)
        if not ts_match: continue
        dt_str = ts_match.group(1)
        tag = ts_match.group(2)
        if not is_in_range(dt_str):
            if dt_str > DATE_END: break
            continue

        if "NEW_ORDER_OPEN" in line:
            m = re.search(r'OPEN_TYPE:(BUY|SELL)', line)
            m2 = re.search(r'DEAL_PRICE:([-\d.]+)', line)
            m3 = re.search(r'OPEN_LOTS:([-\d.]+)', line)
            if m:
                trade_events.append({
                    "time": dt_str, "type": "BUY" if m.group(1)=="BUY" else "SELL",
                    "action": "BUY" if m.group(1)=="BUY" else "SELL",
                    "price": float(m2.group(1)) if m2 else None,
                    "lots": float(m3.group(1)) if m3 else None,
                })
        elif "NEW_ORDER_CLOSE" in line:
            m = re.search(r'OPEN_Type:(BUY|SELL)', line)
            m2 = re.search(r'CLOSED_PRICE:([-\d.]+)', line)
            m3 = re.search(r'PROFIT:([-\d.]+)', line)
            if m:
                trade_events.append({
                    "time": dt_str, "type": "CLOSE",
                    "closed_dir": m.group(1),
                    "price": float(m2.group(1)) if m2 else None,
                    "profit": float(m3.group(1)) if m3 else None,
                })

# Also get G0 exit events (TradeAct:7)
g0_events = []
with open(LOG_FILE, 'r', encoding='utf-8', errors='replace') as f:
    for line in f:
        line = line.strip()
        if not line: continue
        ts_match = LINE_RE.match(line)
        if not ts_match: continue
        dt_str = ts_match.group(1)
        tag = ts_match.group(2)
        if not is_in_range(dt_str):
            if dt_str > DATE_END: break
            continue
        if tag == "TRADEINFO" and "TradeAct:7" in line:
            m = re.search(r'Gate:\[(\w[\w-]*)\]', line)
            m2 = re.search(r'M30:(\d)', line)
            m3 = re.search(r'M15:(\d)', line)
            m4 = re.search(r'H1:(\d)', line)
            g0_events.append({
                "time": dt_str,
                "gate": m.group(1) if m else "G0",
                "m30_mid": int(m2.group(1)) if m2 else None,
                "m15_mid": int(m3.group(1)) if m3 else None,
                "h1_mid": int(m4.group(1)) if m4 else None,
            })

# Output
print("=== H4 BOUNDARY SNAPSHOTS ===")
for snap in snapshots:
    tf = snap["tf_states"]
    h4 = tf.get("H4", {})
    h1 = tf.get("H1", {})
    m30 = tf.get("M30", {})
    m15 = tf.get("M15", {})
    d1 = tf.get("D1", {})
    print(f"{snap['time'][:16]} | "
          f"H4:{h4.get('bbw','?')} m{h4.get('mid','?')} b{h4.get('budn','?')} dB={h4.get('dbbw','?'):.2f} | "
          f"H1:{h1.get('bbw','?')} m{h1.get('mid','?')} b{h1.get('budn','?')} | "
          f"M30:{m30.get('bbw','?')} m{m30.get('mid','?')} b{m30.get('budn','?')} | "
          f"M15:{m15.get('bbw','?')} m{m15.get('mid','?')} b{m15.get('budn','?')} | "
          f"D1:{d1.get('bbw','?')} m{d1.get('mid','?')} b{d1.get('budn','?')}")

print(f"\nTotal H4 boundary snapshots: {len(snapshots)}")

print("\n=== TRADE EVENTS ===")
for te in trade_events:
    print(f"  {te['time'][:16]}  {te.get('action', te.get('type','?')):10s}  "
          f"price={te.get('price','?')}  lots={te.get('lots','?')}  "
          f"profit={te.get('profit','N/A')}")

print(f"\nTotal trade events: {len(trade_events)}")

print("\n=== G0 EXIT EVENTS (TradeAct:7) ===")
for ge in g0_events:
    print(f"  {ge['time'][:16]}  Gate:[{ge['gate']}]  M30:{ge.get('m30_mid','?')} M15:{ge.get('m15_mid','?')} H1:{ge.get('h1_mid','?')}")

print(f"\nTotal G0 events: {len(g0_events)}")
