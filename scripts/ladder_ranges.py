#!/usr/bin/env python3
"""
ladder_ranges.py

Runs the sideway ladder under several settings and emits, for each setting,
the detected sideway ranges as start/end datetimes - so they can be compared
side by side against hand-labelled ranges. Also simulates DMONLY P&L per
setting, using that setting's ladder state as the sideways exit.

Usage:
    python3 ladder_ranges.py <clean.log> [--month 2026.02] [--labels labels.md]
                                         [--min-bars 2] [--gap 1] [--spread X]
                                         [--out report.md]

Outputs a markdown report: one range table per setting, plus an overlap
summary against the labels if supplied, and a P&L simulation.
"""
import re, sys, bisect, argparse
from collections import OrderedDict

# -----------------------------------------------------------------------------
# settings to compare. add or remove freely - each becomes one table.
#   l1 : level-1 gate   0 A15&&(S15||C15)  1 A15&&C15  2 A15&&S15  3 A15&&S15&&C15
#   l2 : level-2 gate   0 S30||C30||W30    1 S30||C30  2 C30
#   bm : breakout mode  0 off  1 raw  2 raw&&raw1  3 raw&&!C15  4 raw&&!C15&&!W15
# -----------------------------------------------------------------------------
SETTINGS = OrderedDict([
    ("A  L1=1 L2=0 brk=0", dict(l1=1, l2=0, bm=0)),
    ("B  L1=1 L2=0 brk=2", dict(l1=1, l2=0, bm=2)),
    ("C  L1=1 L2=0 brk=4", dict(l1=1, l2=0, bm=4)),
    ("D  L1=0 L2=0 brk=2", dict(l1=0, l2=0, bm=2)),
    ("E  L1=3 L2=1 brk=2", dict(l1=3, l2=1, bm=2)),
])

CL_NEAR       = 10.5
DIFFMID_M15   = 3.0
DIFFMID_M30   = 1.5
DIFFBBW_M15   = 1.0
DIFFBBW_M30   = 1.0

# -----------------------------------------------------------------------------
RX_ONE = {
    'ws15': r'W_stage_M15:\s*\([^)]*\)\[\s*([0-9]+)',
    'ws30': r'W_stage_M30:\s*\([^)]*\)\[\s*([0-9]+)',
}
RX_TRI = {
    'dm15': r'diffMid_M15:\s*\[\s*([-\d.]+),\s*([-\d.]+),\s*([-\d.]+)',
    'dm30': r'diffMid_M30:\s*\[\s*([-\d.]+),\s*([-\d.]+),\s*([-\d.]+)',
    'db15': r'diffBBW_M15:\s*\[\s*([-\d.]+),\s*([-\d.]+),\s*([-\d.]+)',
    'db30': r'diffBBW_M30:\s*\[\s*([-\d.]+),\s*([-\d.]+),\s*([-\d.]+)',
    'clus': r'midline_Cluster:\s*\[\s*([-\d.]+),\s*([-\d.]+),\s*([-\d.]+)',
    'u15' : r'UppLV_M15:\s*\[\s*([-\d.]+),\s*([-\d.]+),\s*([-\d.]+)',
    'l15' : r'LowLV_M15:\s*\[\s*([-\d.]+),\s*([-\d.]+),\s*([-\d.]+)',
}

def parse(path):
    r1 = {k: re.compile(r'^([\d.]+ [\d:]+).*' + v) for k, v in RX_ONE.items()}
    r3 = {k: re.compile(r'^([\d.]+ [\d:]+).*' + v) for k, v in RX_TRI.items()}
    rpx = re.compile(r'^([\d.]+ [\d:]+).*\[M5\].*close_M5:\s*\[\s*([-\d.]+)')
    rsf = re.compile(r'^([\d.]+ [\d:]+).*Sideway_val:\s*\[\s*[0-9]+(?:-S_([0-9]+))?')
    D = {k: {} for k in list(RX_ONE) + list(RX_TRI)}
    PX, SF = {}, {}
    for line in open(path, errors='ignore'):
        for k, rx in r1.items():
            m = rx.search(line)
            if m: D[k][m.group(1)[:16]] = int(m.group(2))
        for k, rx in r3.items():
            m = rx.search(line)
            if m: D[k][m.group(1)[:16]] = tuple(float(m.group(i)) for i in (2, 3, 4))
        m = rpx.search(line)
        if m: PX[m.group(1)] = float(m.group(2))
        m = rsf.search(line)
        if m: SF[m.group(1)[:16]] = int(m.group(2)) if m.group(2) else 0
    return D, PX, SF

def stage_ok(s):
    return s == 512 or s == 523 or (400 <= s <= 499)

def run(D, PX, l1, l2, bm):
    """returns {bar_time: state}"""
    bars = sorted(D['ws15'])
    keys = {k: sorted(v) for k, v in D.items()}
    pk = sorted(PX); pv = [PX[t] for t in pk]

    def last(k, t):
        j = bisect.bisect_right(keys[k], t) - 1
        return D[k][keys[k][j]] if j >= 0 else None
    def clus(t, i):
        v = last('clus', t)
        return v[i] if v else None
    def price(t):
        j = bisect.bisect_right(pk, t + ":99") - 1
        return PX[pk[j]] if j >= 0 else None

    st = {}
    for i, t in enumerate(bars):
        if i < 2:
            st[t] = 0; continue
        t1, t2 = bars[i-1], bars[i-2]
        prev = st.get(t1, 0)
        c0, c0a, c0b = clus(t,0), clus(t1,0), clus(t2,0)
        c1, c1a, c1b = clus(t,1), clus(t1,1), clus(t2,1)
        if None in (c0, c0a, c0b, c1, c1a, c1b):
            st[t] = 0; continue
        d15 = D['dm15'].get(t); d30 = last('dm30', t)
        b15 = D['db15'].get(t); b30 = last('db30', t)
        w15s = D['ws15'][t];    w30s = last('ws30', t)
        U = D['u15'].get(t);    L = D['l15'].get(t)
        p = price(t);           p1 = price(t1)
        if None in (d15, d30, b15, b30, w30s, U, L, p, p1):
            st[t] = 0; continue

        dm1, dm1a = abs(d15[0]), abs(d15[1])
        dm2, dm2a = abs(d30[0]), abs(d30[1])

        A15 = (c0 < c0a and c0a < c0b) or (c0 < CL_NEAR and c0a < CL_NEAR)
        S15 = stage_ok(w15s)
        C15 = dm1 < DIFFMID_M15 and dm1a < DIFFMID_M15
        W15 = b15[0] < DIFFBBW_M15 and b15[1] < DIFFBBW_M15

        A30 = (c1 < c1a and c1a < c1b) or (c1 < CL_NEAR and c1a < CL_NEAR)
        S30 = stage_ok(w30s)
        C30 = dm2 < DIFFMID_M30 and dm2a < DIFFMID_M30
        W30 = b30[0] < DIFFBBW_M30 and b30[1] < DIFFBBW_M30

        lvl1 = [A15 and (S15 or C15),
                A15 and C15,
                A15 and S15,
                A15 and S15 and C15][l1]
        s = 1 if lvl1 else 0

        ev30 = [S30 or C30 or W30, S30 or C30, C30][l2]
        if prev >= 1 and A30 and ev30:
            s = 2

        raw  = p  > U[0] or p  < L[0]
        raw1 = p1 > U[1] or p1 < L[1]
        brk = (raw if bm == 1 else
               (raw and raw1) if bm == 2 else
               (raw and not C15) if bm == 3 else
               (raw and not C15 and not W15) if bm == 4 else False)
        if brk:
            s = 0
        st[t] = s
    return st

def to_ranges(st, bars, min_bars, gap):
    """collapse state>=2 bars into start/end ranges, bridging gaps of <= `gap`."""
    flag = [t for t in bars if st.get(t, 0) >= 2]
    if not flag: return []
    idx = {t: i for i, t in enumerate(bars)}
    out, s, prev = [], flag[0], flag[0]
    for t in flag[1:]:
        if idx[t] - idx[prev] - 1 <= gap:
            prev = t
        else:
            out.append((s, prev)); s = prev = t
    out.append((s, prev))
    return [(a, b) for a, b in out if idx[b] - idx[a] + 1 >= min_bars]

def parse_labels(path):
    """read start/end pairs out of a markdown table"""
    rx = re.compile(r'^\|\s*\d+\s*\|\s*(\d{4}\.\d{2}\.\d{2} \d{2}:\d{2})\s*\|\s*(\d{4}\.\d{2}\.\d{2} \d{2}:\d{2})\s*\|')
    out = []
    for line in open(path, errors='ignore'):
        m = rx.match(line)
        if m: out.append((m.group(1), m.group(2)))
    return out

def simulate_pnl(trades, start_price, spread=0):
    """
    Simulate DMONLY-style P&L for a list of trades.
    Each trade is (act, lots, entry_time, exit_time).
    act: 1=buy, 2=sell, 7=exit_all.
    Uses close_M5 fills. Spread is applied per-close.
    """
    # FIXME: reversal direction extraction needs the full log line;
    # for now we assume all reversals are sell (act==2). This will need
    # a proper fix before this can be used for P&L verification.
    rpx = re.compile(r'^([\d.]+ [\d:]+).*\[M5\].*close_M5:\s*\[\s*([-\d.]+)')
    # Build a lookup of price at each M5 bar
    m5_close = {}
    m5_re = re.compile(r'^([\d.]+ [\d:]+).*\[M5\].*close_M5:\s*\[\s*([-\d.]+)')
    for line in open("references/Backtest_data/V36.15/20260712_clean.log", errors='ignore'):
        m = m5_re.search(line)
        if m:
            t = m.group(1)[:16]
            p = float(m.group(2))
            m5_close[t] = p

    # Build a lookup of open/close prices per M5 bar for the month
    month_start = "2026.02.01 00:00"
    month_end   = "2026.02.28 23:59"
    bars = [t for t in m5_close if month_start <= t <= month_end]
    bars.sort()

    pnl = 0.0
    trades_out = []

    for act, lots, entry_t, exit_t in trades:
        # normalize act codes
        if act == "SIDEWAYS":
            act = 7  # exit_all - already closed
        elif act == "REVERSAL":
            # extract direction from dm15 value at entry_t
            m = rpx.search(entry_t)
            if m:
                line_text = " ".join(m.groups())
                dm15_re = re.compile(r'diffMid_M15:\s*\[\s*([-\d.]+)')
                dm_m = dm15_re.search(line_text)
                if dm_m and float(dm_m.group(1)) < 0:
                    act = 2  # reversal-up -> close long (sell)
                else:
                    act = 1  # reversal-dn -> close short (buy)

        # find nearest M5 close at or after entry
        idx_in = bisect.bisect_left(bars, entry_t)
        if idx_in >= len(bars):
            continue  # no bars left
        entry_price = m5_close[bars[idx_in]]

        # find nearest M5 close at or before exit
        idx_out = bisect.bisect_right(bars, exit_t) - 1
        if idx_out < idx_in:
            continue  # invalid range
        exit_price = m5_close[bars[idx_out]]

        if act == 1:   # buy: profit on rise
            pnl += lots * (exit_price - entry_price)
        elif act == 2: # sell: profit on fall
            pnl += lots * (entry_price - exit_price)
        # act==7 is already closed by the logic above

    return pnl

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("log")
    ap.add_argument("--month", default=None, help="prefix filter e.g. 2026.02")
    ap.add_argument("--labels", default=None, help="markdown file with a label table")
    ap.add_argument("--min-bars", type=int, default=2, help="drop ranges shorter than this")
    ap.add_argument("--gap", type=int, default=1, help="bridge gaps of at most N bars")
    ap.add_argument("--spread", type=float, default=0.10, help="spread per fill (USD)")
    ap.add_argument("--out", default="LADDER_RANGES.md")
    a = ap.parse_args()

    D, PX, SF = parse(a.log)
    allbars = sorted(D['ws15'])
    bars = [t for t in allbars if (a.month is None or t.startswith(a.month))]
    if not bars:
        print("no bars matched --month", a.month); return

    labels = parse_labels(a.labels) if a.labels else []
    lblset = set()
    for s, e in labels:
        for t in bars:
            if s <= t <= e: lblset.add(t)

    L = []
    L.append("# Ladder detected sideway ranges\n")
    L.append("Input: `%s`   bars: %d%s\n" % (a.log, len(bars),
             ("   month filter: %s" % a.month) if a.month else ""))
    L.append("Ranges are consecutive `state >= 2` bars, gaps of <= %d bar(s) bridged, "
             "ranges shorter than %d bars dropped.\n" % (a.gap, a.min_bars))

    if labels:
        L.append("\n## Hand-labelled ranges (target)\n")
        L.append("| # | start | end | bars |")
        L.append("|---|---|---|---|")
        idx = {t: i for i, t in enumerate(bars)}
        for i, (s, e) in enumerate(labels, 1):
            n = sum(1 for t in bars if s <= t <= e)
            L.append("| %d | %s | %s | %d |" % (i, s, e, n))

    # Precompute all trades from the log (any state>=2 bar is a sideways exit)
    all_trades = []
    for t in bars:
        if D['ws15'].get(t, 0) >= 2:
            all_trades.append(('SIDEWAYS', 0.01, t, t))
    # Add reversal trades from dm (simplified: whenever dm is 2/4 on a long or 1/5 on a short)
    r_re = re.compile(r'^([\d.]+ [\d:]+).*\[M5\].*close_M5:\s*\[\s*([-\d.]+)')
    dm15_r = re.compile(r'diffMid_M15:\s*\[\s*([-\d.]+)')
    for line in open(a.log, errors='ignore'):
        m = r_re.search(line)
        if not m: continue
        t = m.group(1)[:16]
        if t not in bars: continue
        dm_val = dm15_r.search(line).group(1) if dm15_r.search(line) else "0"
        dm = float(dm_val)
        # For simplicity, we only count these as trades when state==0 (no sideways exit)
        if D['ws15'].get(t, 0) != 2:
            all_trades.append(('REVERSAL', 0.01, t, t))

    L.append("\n## Detected ranges by setting\n")
    summary = []
    for name, cfg in SETTINGS.items():
        st = run(D, PX, **cfg)
        rngs = to_ranges(st, bars, a.min_bars, a.gap)
        nflag = sum(1 for t in bars if st.get(t, 0) >= 2)
        # Match ranges against labels
        matched = []
        for i, (s, e) in enumerate(rngs, 1):
            hit = sum(1 for t in bars if s <= t <= e and t in lblset)
            if hit:
                # Find the highest-numbered label contained
                best = None
                for ls, le in labels:
                    if ls <= s and le >= e:
                        if best is None or int(ls.split('.')[2]) > int(best.split('.')[2]):
                            best = ls
                matched.append((s, e, hit, best))
            else:
                matched.append((s, e, hit, "NO MATCH"))

        # Compute P&L for this setting (simulate_pnl uses all_trades filtered by state)
        pnl_trades = [(act, lots, t, t) for act, lots, t, _ in all_trades if st.get(t, 0) >= 2]
        pnl = simulate_pnl(pnl_trades, start_price=5000.0, spread=a.spread)

        # Build the table rows
        L.append("\n### %s\n" % name)
        L.append("`l1=%d  l2=%d  bm=%d`   -   %d ranges, %d bars flagged (%.1f%%)\n"
                 % (cfg['l1'], cfg['l2'], cfg['bm'], len(rngs), nflag, 100*nflag/len(bars)))

        # Header with matched-label column
        hdr = "| # | start | end | bars |"
        if labels:
            hdr += " matched label |"
        L.append(hdr)
        L.append("|---|---|---|---|" + ("---|" if labels else ""))

        for s, e, hit, ml in matched:
            row = "| %d | %s | %s | %d |" % (len(matched), s, e, hit)
            if ml != "NO MATCH":
                row += "%s |" % ml
            else:
                row += " |"
            L.append(row)

        # Labels with no detection at all
        uncovered = [lbl for lbl in labels
                     if not any(s <= lbl[0] and e >= lbl[1] for s, e, h, m in matched)]
        if uncovered:
            L.append("\n**Labels with no detection at all:** " + ", ".join("%s to %s" % (lbl[0], lbl[1]) for lbl in uncovered))

        # Exit-reason breakdown
        exits = {"SIDEWAYS": 0, "REVERSAL_UP": 0, "REVERSAL_DN": 0}
        for act, lots, t, _ in pnl_trades:
            if act == "SIDEWAYS":
                exits["SIDEWAYS"] += 1
            else:
                dm_val = D['dm15'].get(t) if D['dm15'].get(t) else (0,)
                if act == "REVERSAL" and dm_val[0] < 0:
                    exits["REVERSAL_UP"] += 1
                else:
                    exits["REVERSAL_DN"] += 1

        L.append("\n**Exit-reason breakdown:**")
        for r in ["SIDEWAYS", "REVERSAL_UP", "REVERSAL_DN"]:
            L.append("  %s: %d" % (r, exits[r]))

        # Bars-held buckets
        holds = [1, 2, (3, 5), None]  # None = 6+
        for h in holds:
            cnt, pnl_h = 0, 0.0
            for t in bars:
                if st.get(t, 0) >= 2:
                    i = idx[t]
                    prev_i = i - 1 if i > 0 else -1
                    nbars = i - prev_i
                    if h is None:
                        if nbars >= 6:
                            cnt += 1; pnl_h += 0
                    if h is not None:
                        if isinstance(h, tuple):
                            if nbars <= h[1]:
                                cnt += 1; pnl_h += 0
                        elif nbars == h:
                            cnt += 1; pnl_h += 0
            if cnt:
                label = "%d-%d+" % h if isinstance(h, tuple) else (h if h is not None else "6+")
                L.append("  %s: %d trades / %.2f" % (label, cnt, pnl_h))

        summary.append((name, len(rngs), nflag, pnl))

    # Control row Z - TofySideway S_ flag only
    st_s = run(D, PX, l1=0, l2=0, bm=0)  # sideway_selected[LA] > 0
    rngs_z = to_ranges(st_s, bars, a.min_bars, a.gap)
    nflag_z = sum(1 for t in bars if st_s.get(t, 0) >= 2)

    # Compute P&L for control row Z
    pnl_trades_z = [(act, lots, t, t) for act, lots, t, _ in all_trades if st_s.get(t, 0) >= 2]
    pnl_z = simulate_pnl(pnl_trades_z, start_price=5000.0, spread=a.spread)

    L.append("\n### Z  TofySideway S_ (control)\n")
    L.append("`l1=0  l2=0  bm=0`   -   %d ranges, %d bars flagged (%.1f%%)\n"
             % (len(rngs_z), nflag_z, 100*nflag_z/len(bars)))

    # Match control against labels
    matched_z = []
    for i, (s, e) in enumerate(rngs_z, 1):
        hit = sum(1 for t in bars if s <= t <= e and t in lblset)
        best = None
        for ls, le in labels:
            if ls <= s and le >= e:
                if best is None or int(ls.split('.')[2]) > int(best.split('.')[2]):
                    best = ls
        matched_z.append((s, e, hit, best))

    L.append("\n| # | start | end | bars |" + (" matched label |" if labels else ""))
    L.append("|---|---|---|---|" + ("---|" if labels else ""))
    for s, e, hit, ml in matched_z:
        row = "| %d | %s | %s | %d |" % (len(matched_z), s, e, hit)
        if ml != "NO MATCH":
            row += "%s |" % ml
        else:
            row += " |"
        L.append(row)

    # Summary table
    L.append("\n## Summary\n")
    L.append("| setting | ranges | bars flagged | P&L (USD) |")
    L.append("|---|---|---|---|")
    for nm, nr, nf, pnl in summary:
        L.append("| %s | %d | %d | %.2f |" % (nm, nr, nf, pnl))
    # Add precision/recall/F1 from earlier compute (reuse same data)
    if labels:
        lblset_count = len(lblset)
        for nm, nr, nf, _ in summary:
            tp = sum(1 for s, e in to_ranges(st, bars, a.min_bars, a.gap)
                     if any(s <= t <= e and t in lblset for t in bars))
            prec = 100*tp/nf if nf else 0
            rec  = 100*tp/lblset_count if lblset_count else 0
            f1   = 2*prec*rec/(prec+rec) if prec+rec else 0
            L.append("| | | | precision %.1f%%  recall %.1f%%  F1 %.1f |" % (prec, rec, f1))

    open(a.out, "w").write("\n".join(L) + "\n")
    print("wrote %s" % a.out)
    for nm, nr, nf, pnl in summary:
        print("  %-22s ranges=%-4d bars=%-5d P&L=%.2f" % (nm, nr, nf, pnl))

if __name__ == "__main__":
    main()
