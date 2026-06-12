#!/usr/bin/env python3
"""Extract H4-boundary + trade-event snapshots from V30.02 clean log."""

import re
import sys
from collections import OrderedDict

LOG_PATH = r"C:\Users\Tofy3\Project\BB_MTF_M15_Strategy\references\Backtest_data\V30.02\20260606_clean.log"
START_DATE = "2026.03.02"
END_DATE = "2026.03.20"
END_TIME = "09:00"

H4_HOURS = {"00", "04", "08", "12", "16", "20"}

def parse_stage(raw):
    """Extract cur stage number from e.g. '(FLY)[511, 511, 511]' -> 511"""
    m = re.search(r'\[(\d+)', raw)
    return int(m.group(1)) if m else None

def parse_array_first(raw):
    """Extract first value from '[1.0, 2.0, 3.0]' -> 1.0"""
    m = re.search(r'\[([\d.\-]+)', raw)
    if m:
        return float(m.group(1))
    return None

def parse_int_array_first(raw):
    """Extract first int from '[2, 0, 1]' -> 2"""
    m = re.search(r'\[(\d+)', raw)
    return int(m.group(1)) if m else None

def parse_tf_line(line, tf_name):
    """Parse a TF block line and return dict of fields."""
    result = {}
    # Stage
    m = re.search(rf'W_stage_{tf_name}:\((\w+)\)\[([^\]]+)\]', line)
    if m:
        regime = m.group(1)
        vals = [int(x.strip()) for x in m.group(2).split(',') if x.strip()]
        result['stage'] = vals[0] if vals else None
        result['stage_prev'] = vals[1] if len(vals) > 1 else None
        result['regime'] = regime

    # diffMid_Trend
    m = re.search(rf'diffMid_Trend_{tf_name}:\[([^\]]+)\]', line)
    if m:
        vals = [float(x.strip()) for x in m.group(1).split(',') if x.strip()]
        result['mid'] = int(vals[0]) if vals else None
        result['mid_prev'] = int(vals[1]) if len(vals) > 1 else None

    # BBUpDn
    m = re.search(rf'BBUpDn_{tf_name}:\[([^\]]+)\]', line)
    if m:
        vals = [int(x.strip()) for x in m.group(1).split(',') if x.strip()]
        result['bbupdn'] = vals[0] if vals else None
        result['bbupdn_prev'] = vals[1] if len(vals) > 1 else None

    # diffBBW
    m = re.search(rf'diffBBW_{tf_name}:\[([^\]]+)\]', line)
    if m:
        vals = [float(x.strip()) for x in m.group(1).split(',') if x.strip()]
        result['diffBBW'] = vals[0] if vals else None

    # trend
    m = re.search(rf'trend_{tf_name}:\[([^\]]+)\]', line)
    if m:
        vals_str = m.group(1).replace(' ', '').rstrip(',').split(',')
        vals = [int(float(x)) for x in vals_str if x]
        result['trend'] = vals[0] if vals else None

    # MidLV
    m = re.search(rf'MidLV_{tf_name}:\[([^\]]+)\]', line)
    if m:
        vals = [float(x.strip()) for x in m.group(1).split(',') if x.strip()]
        result['midlv'] = vals[0] if vals else None

    # UppLV
    m = re.search(rf'UppLV_{tf_name}:\[([^\]]+)\]', line)
    if m:
        vals = [float(x.strip()) for x in m.group(1).split(',') if x.strip()]
        result['upplv'] = vals[0] if vals else None

    # LowLV
    m = re.search(rf'LowLV_{tf_name}:\[([^\]]+)\]', line)
    if m:
        vals = [float(x.strip()) for x in m.group(1).split(',') if x.strip()]
        result['lowlv'] = vals[0] if vals else None

    # WLV (BB width)
    m = re.search(rf'WLV_{tf_name}:\[([^\]]+)\]', line)
    if m:
        vals = [float(x.strip()) for x in m.group(1).split(',') if x.strip()]
        result['wlv'] = vals[0] if vals else None

    # close (M15 block only)
    m = re.search(rf'close_{tf_name}:\[([^\]]+)\]', line)
    if m:
        vals = [float(x.strip()) for x in m.group(1).split(',') if x.strip()]
        result['close'] = vals[0] if vals else None

    return result

def parse_tradeinfo(line):
    """Parse TRADEINFO line for gate and trade action."""
    result = {'gate': '', 'tradeact': 0, 'act': 0}
    # Gates
    gates = re.findall(r'Gate:\[([^\]]+)\]', line)
    result['gate'] = ' | '.join(gates) if gates else ''
    # TradeAct
    m = re.search(r'TradeAct:(\d+)', line)
    if m:
        result['tradeact'] = int(m.group(1))
    # act
    m = re.search(r'act:(\d+)', line)
    if m:
        result['act'] = int(m.group(1))
    # cnt (shrink count)
    m = re.search(r'cnt:(\d+)', line)
    if m:
        result['cnt'] = m.group(1)
    # pen (penalty/size multiplier)
    m = re.search(r'pen:([\d.]+)', line)
    if m:
        result['pen'] = float(m.group(1))
    return result

def parse_bbtfimpact(line):
    """Parse BBTFImpact line."""
    result = {}
    m = re.search(r'Sideway_val:\[([^\]]+)\]', line)
    if m:
        result['sideway_val'] = m.group(1).strip()
    m = re.search(r'HTF_Drive_LTF_Sideway:\[([^\]]+)\]', line)
    if m:
        result['htf_drive'] = m.group(1).strip()
    else:
        result['htf_drive'] = ''
    m = re.search(r'LTF_Drive_HTF_Fly:\[([^\]]+)\]', line)
    if m:
        result['ltf_drive'] = m.group(1).strip()
    else:
        result['ltf_drive'] = ''
    m = re.search(r'midline_Cluster:\[([^\]]+)\]', line)
    if m:
        result['midline_cluster'] = m.group(1).strip()
    return result

def parse_order(line):
    """Parse NEW_ORDER_OPEN or NEW_ORDER_CLOSE."""
    result = {}
    if 'NEW_ORDER_OPEN' in line:
        result['event'] = 'OPEN'
        m = re.search(r'OPEN_TYPE:(\w+)', line)
        if m:
            result['type'] = m.group(1)
        m = re.search(r'OPEN_LOTS:([\d.]+)', line)
        if m:
            result['lots'] = m.group(1)
        m = re.search(r'DEAL_PRICE:([\d.]+)', line)
        if m:
            result['price'] = m.group(1)
        m = re.search(r'OPEN_TICKET:(\d+)', line)
        if m:
            result['ticket'] = m.group(1)
    elif 'NEW_ORDER_CLOSE' in line:
        result['event'] = 'CLOSE'
        m = re.search(r'OPEN_Type:(\w+)', line)
        if m:
            result['type'] = m.group(1)
        m = re.search(r'CLOSED_TYPE:(\w+)', line)
        if m:
            result['close_type'] = m.group(1)
        m = re.search(r'CLOSED_PRICE:([\d.]+)', line)
        if m:
            result['price'] = m.group(1)
        m = re.search(r'PROFIT:([\d.\-]+)', line)
        if m:
            result['profit'] = m.group(1)
        m = re.search(r'OPEN_TICKET:(\d+)', line)
        if m:
            result['ticket'] = m.group(1)
    return result

def derive_cascade(tf_states):
    """Derive cas_shrinkTF and cas_sqzCount from TF states."""
    tf_order = ['M15', 'M30', 'H1', 'H4', 'D1']
    tf_index = {'M15': 1, 'M30': 2, 'H1': 3, 'H4': 4, 'D1': 5}

    cas_shrinkTF = -1
    cas_sqzCount = 0
    sqz_tfs = []
    shrink_tfs = []

    for tf in tf_order:
        if tf in tf_states and tf_states[tf].get('stage') is not None:
            stage = tf_states[tf]['stage']
            if 400 <= stage <= 499:
                cas_sqzCount += 1
                sqz_tfs.append(tf)
            elif stage in (513, 523):
                if tf_index[tf] > cas_shrinkTF:
                    cas_shrinkTF = tf_index[tf]
                shrink_tfs.append(tf)

    return cas_shrinkTF, cas_sqzCount, shrink_tfs, sqz_tfs

OUTPUT_PATH = r"C:\Users\Tofy3\Project\BB_MTF_M15_Strategy\scripts\extract_output.txt"

def main():
    import io
    outbuf = io.StringIO()
    def p(s=''):
        outbuf.write(s + '\n')

    with open(LOG_PATH, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Current state tracking
    tf_states = {}  # {TF_name: {stage, mid, bbupdn, diffBBW, ...}}
    for tf in ['M15', 'M30', 'H1', 'H4', 'D1', 'W1']:
        tf_states[tf] = {}

    current_tradeinfo = {}
    current_bbtfimpact = {}
    current_time = ''

    # Collect snapshots
    snapshots = []
    trade_events = []

    # Track which H4 boundaries we've captured
    captured_h4 = set()

    in_range = False

    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue

        # Extract timestamp
        m = re.match(r'(\d{4}\.\d{2}\.\d{2}) (\d{2}:\d{2}:\d{2})', line)
        if not m:
            continue

        date_str = m.group(1)
        time_str = m.group(2)

        # Check date range
        if date_str < START_DATE:
            continue
        if date_str > END_DATE or (date_str == END_DATE and time_str > END_TIME + ":59"):
            continue

        in_range = True
        current_time = f"{date_str} {time_str}"
        hour = time_str[:2]
        minute = time_str[3:5]

        # Parse TF blocks
        for tf in ['M15', 'M30', 'H1', 'H4', 'D1', 'W1']:
            if f'[{tf}]' in line:
                tf_states[tf] = parse_tf_line(line, tf)
                tf_states[tf]['last_update'] = current_time

        # Parse TRADEINFO
        if '[TRADEINFO]' in line:
            current_tradeinfo = parse_tradeinfo(line)

        # Parse BBTFImpact
        if '[BBTFImpact]' in line:
            current_bbtfimpact = parse_bbtfimpact(line)

        # Check for trade events
        if '[NEW_ORDER_OPEN]' in line or '[NEW_ORDER_CLOSE]' in line:
            order = parse_order(line)
            if order:
                order['time'] = current_time
                trade_events.append(order)
                # Snapshot at trade event
                cas_shrink, cas_sqz, shrink_tfs, sqz_tfs = derive_cascade(tf_states)
                snap = {
                    'time': current_time,
                    'line': i + 1,
                    'H4': dict(tf_states.get('H4', {})),
                    'H1': dict(tf_states.get('H1', {})),
                    'M30': dict(tf_states.get('M30', {})),
                    'M15': dict(tf_states.get('M15', {})),
                    'D1': dict(tf_states.get('D1', {})),
                    'W1': dict(tf_states.get('W1', {})),
                    'tradeinfo': dict(current_tradeinfo),
                    'bbtfimpact': dict(current_bbtfimpact),
                    'cas_shrinkTF': cas_shrink,
                    'cas_sqzCount': cas_sqz,
                    'shrink_tfs': shrink_tfs,
                    'sqz_tfs': sqz_tfs,
                    'trade_event': f"{order.get('event','')} {order.get('type','')}{order.get('close_type','')} @{order.get('price','')}" + (f" P&L:{order.get('profit','')}" if order.get('profit') else ''),
                }
                snapshots.append(snap)

        # Check for H4 boundary (first tick at hh:00 where hh in H4_HOURS)
        if hour in H4_HOURS and minute == "00":
            boundary_key = f"{date_str}_{hour}"
            if boundary_key not in captured_h4:
                # Wait until we have the ORDERINFO line (end of tick) to capture
                pass

        # Capture at ORDERINFO (end of tick) for H4 boundaries
        if '[ORDERINFO]' in line:
            if hour in H4_HOURS and minute == "00":
                boundary_key = f"{date_str}_{hour}"
                if boundary_key not in captured_h4:
                    captured_h4.add(boundary_key)
                    cas_shrink, cas_sqz, shrink_tfs, sqz_tfs = derive_cascade(tf_states)
                    snap = {
                        'time': current_time,
                        'line': i + 1,
                        'H4': dict(tf_states.get('H4', {})),
                        'H1': dict(tf_states.get('H1', {})),
                        'M30': dict(tf_states.get('M30', {})),
                        'M15': dict(tf_states.get('M15', {})),
                        'D1': dict(tf_states.get('D1', {})),
                        'W1': dict(tf_states.get('W1', {})),
                        'tradeinfo': dict(current_tradeinfo),
                        'bbtfimpact': dict(current_bbtfimpact),
                        'cas_shrinkTF': cas_shrink,
                        'cas_sqzCount': cas_sqz,
                        'shrink_tfs': shrink_tfs,
                        'sqz_tfs': sqz_tfs,
                        'trade_event': '',
                    }
                    snapshots.append(snap)

    # Also capture at H4 boundaries that aren't exactly :00 (weekend gaps etc)
    # Already handled above

    # Sort by time
    snapshots.sort(key=lambda x: x['time'])

    # Output summary table
    p("=" * 220)
    p("SUMMARY TABLE — V30.02 Log Data, 2026.03.02 to 2026.03.20 09:00")
    p("Sampled at H4 bar boundaries (00:00/04:00/08:00/12:00/16:00/20:00) + trade events")
    p("=" * 220)

    hdr = (f"{'Time':<22}| {'H4stg':>5} {'H4mid':>5} {'H4ud':>4} | "
           f"{'H1stg':>5} {'H1mid':>5} {'H1ud':>4} | "
           f"{'M30stg':>6} {'M30mid':>6} {'M30ud':>5} | "
           f"{'M15stg':>6} {'M15mid':>6} {'M15ud':>5} | "
           f"{'D1stg':>5} {'D1mid':>5} | "
           f"{'dBBW_H4':>8} | "
           f"{'casShrk':>7} {'casSqz':>6} | "
           f"{'Trade Event'}")
    p(hdr)
    p("-" * 220)

    for s in snapshots:
        h4 = s['H4']
        h1 = s['H1']
        m30 = s['M30']
        m15 = s['M15']
        d1 = s['D1']

        h4_stg = h4.get('stage', '?')
        h4_mid = h4.get('mid', '?')
        h4_ud = h4.get('bbupdn', '?')
        h1_stg = h1.get('stage', '?')
        h1_mid = h1.get('mid', '?')
        h1_ud = h1.get('bbupdn', '?')
        m30_stg = m30.get('stage', '?')
        m30_mid = m30.get('mid', '?')
        m30_ud = m30.get('bbupdn', '?')
        m15_stg = m15.get('stage', '?')
        m15_mid = m15.get('mid', '?')
        m15_ud = m15.get('bbupdn', '?')
        d1_stg = d1.get('stage', '?')
        d1_mid = d1.get('mid', '?')
        diffbbw = h4.get('diffBBW', '?')
        if isinstance(diffbbw, float):
            diffbbw = f"{diffbbw:+.1f}"

        cas_shrk = s['cas_shrinkTF']
        cas_sqz = s['cas_sqzCount']
        te = s.get('trade_event', '')

        row = (f"{s['time']:<22}| {h4_stg:>5} {h4_mid:>5} {h4_ud:>4} | "
               f"{h1_stg:>5} {h1_mid:>5} {h1_ud:>4} | "
               f"{m30_stg:>6} {m30_mid:>6} {m30_ud:>5} | "
               f"{m15_stg:>6} {m15_mid:>6} {m15_ud:>5} | "
               f"{d1_stg:>5} {d1_mid:>5} | "
               f"{diffbbw:>8} | "
               f"{cas_shrk:>7} {cas_sqz:>6} | "
               f"{te}")
        p(row)

    # Detailed state per snapshot
    p("\n")
    p("=" * 200)
    p("DETAILED STATE PER SNAPSHOT")
    p("=" * 200)

    for idx, s in enumerate(snapshots):
        p(f"\n--- [{idx+1}] {s['time']} {'*** '+s['trade_event']+' ***' if s['trade_event'] else '(H4 boundary)'} ---")
        p(f"  Log line: {s['line']}")

        for tf in ['D1', 'W1', 'H4', 'H1', 'M30', 'M15']:
            d = s[tf]
            if not d:
                p(f"  [{tf}] no data")
                continue
            stg = d.get('stage', '?')
            stg_p = d.get('stage_prev', '?')
            mid = d.get('mid', '?')
            mid_p = d.get('mid_prev', '?')
            ud = d.get('bbupdn', '?')
            ud_p = d.get('bbupdn_prev', '?')
            dbbw = d.get('diffBBW', '?')
            trnd = d.get('trend', '?')
            midlv = d.get('midlv', '?')
            upplv = d.get('upplv', '?')
            lowlv = d.get('lowlv', '?')
            wlv = d.get('wlv', '?')
            close = d.get('close', '')
            regime = d.get('regime', '?')
            upd = d.get('last_update', '?')

            line_out = (f"  [{tf}] stg:{stg}/{stg_p}({regime}) mid:{mid}/{mid_p} "
                       f"BBUpDn:{ud}/{ud_p} diffBBW:{dbbw} trend:{trnd} "
                       f"MidLV:{midlv} Upp:{upplv} Low:{lowlv} WLV:{wlv}")
            if close:
                line_out += f" close:{close}"
            line_out += f"  [upd:{upd}]"
            p(line_out)

        p(f"  Cascade: cas_shrinkTF={s['cas_shrinkTF']} cas_sqzCount={s['cas_sqzCount']} "
          f"shrink_tfs={s['shrink_tfs']} sqz_tfs={s['sqz_tfs']}")

        ti = s.get('tradeinfo', {})
        p(f"  TRADEINFO: gate={ti.get('gate','')} act={ti.get('act',0)} tradeact={ti.get('tradeact',0)}")

        bi = s.get('bbtfimpact', {})
        p(f"  BBTFImpact: sideway={bi.get('sideway_val','')} htf_drive={bi.get('htf_drive','')} "
          f"ltf_drive={bi.get('ltf_drive','')} midCluster={bi.get('midline_cluster','')}")

    # Cross-check flags
    p("\n")
    p("=" * 200)
    p("CROSS-CHECK: BBW_stage vs diffMid + diffBBW conflicts")
    p("=" * 200)

    for idx, s in enumerate(snapshots):
        flags = []
        for tf in ['H4', 'H1', 'M30', 'M15']:
            d = s[tf]
            if not d or d.get('stage') is None:
                continue
            stg = d['stage']
            mid = d.get('mid')
            dbbw = d.get('diffBBW')
            ud = d.get('bbupdn')

            if stg is None or mid is None or dbbw is None:
                continue

            if stg in (511, 512) and dbbw < -5 and mid >= 3:
                flags.append(f"{tf}: stage={stg}(FLY) but diffBBW={dbbw:.1f} + mid={mid} -> SHRINK signal (stage lags)")

            if stg in (511, 512) and ud == 2:
                flags.append(f"{tf}: stage={stg}(FLY) but BBUpDn=2(shrinking) -> stage lagging behind BBUpDn")

            if stg in (513, 523) and dbbw > 5 and ud == 1:
                flags.append(f"{tf}: stage={stg}(SHRINK) but diffBBW={dbbw:.1f} + BBUpDn=1(expanding) -> EXPANSION signal (stage lags)")

            if 400 <= stg <= 499 and dbbw > 10 and ud == 1:
                flags.append(f"{tf}: stage={stg}(SQZ) but diffBBW={dbbw:.1f} + BBUpDn=1(expanding) -> EXIT SQZ signal (stage lags)")

        if flags:
            p(f"\n[{idx+1}] {s['time']} {s.get('trade_event','')}")
            for fl in flags:
                p(f"  FLAG: {fl}")

    # Trade events summary
    p("\n")
    p("=" * 120)
    p("TRADE EVENTS SUMMARY")
    p("=" * 120)
    for te in trade_events:
        p(f"  {te['time']} -- {te.get('event','')} {te.get('type','')}{te.get('close_type','')} "
          f"@{te.get('price','')} ticket#{te.get('ticket','')} "
          f"{'P&L: '+te.get('profit','') if te.get('profit') else ''}")

    # Write output
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        f.write(outbuf.getvalue())
    print(f"Output written to {OUTPUT_PATH}")
    print(f"Total snapshots: {len(snapshots)}")
    print(f"Total trade events in range: {len(trade_events)}")

if __name__ == '__main__':
    main()
