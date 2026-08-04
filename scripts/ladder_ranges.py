#!/usr/bin/env python3
"""
ladder_ranges.py

Runs the sideway ladder under several settings and emits, for each setting,
the detected sideway ranges as start/end datetimes - so they can be compared
side by side against hand-labelled ranges.

Usage:
    python3 ladder_ranges.py <clean.log> [--month 2026.02] [--labels labels.md]
                             [--min-bars 2] [--gap 1] [--out report.md]

Outputs a markdown report: one range table per setting, plus an overlap
summary against the labels if supplied.
"""
import re, sys, bisect, argparse
from collections import OrderedDict

# ----------------------------------------------------------------------------
# settings to compare. add or remove freely - each becomes one table.
#   l1 : level-1 gate   0 A15&&(S15||C15)  1 A15&&C15  2 A15&&S15  3 A15&&S15&&C15
#   l2 : level-2 gate   0 S30||C30||W30    1 S30||C30  2 C30
#   bm : breakout mode  0 off  1 raw  2 raw&&raw1  3 raw&&!C15  4 raw&&!C15&&!W15
# ----------------------------------------------------------------------------
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

# ----------------------------------------------------------------------------
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

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("log")
    ap.add_argument("--month", default=None, help="prefix filter e.g. 2026.02")
    ap.add_argument("--labels", default=None, help="markdown file with a label table")
    ap.add_argument("--min-bars", type=int, default=2, help="drop ranges shorter than this")
    ap.add_argument("--gap", type=int, default=1, help="bridge gaps of at most N bars")
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
        L.append("\n**%d labelled ranges, %d bars (%.1f%% of the month).**\n"
                 % (len(labels), len(lblset), 100*len(lblset)/len(bars)))

    L.append("\n## Detected ranges by setting\n")
    summary = []
    for name, cfg in SETTINGS.items():
        st = run(D, PX, **cfg)
        rngs = to_ranges(st, bars, a.min_bars, a.gap)
        nflag = sum(1 for t in bars if st.get(t, 0) >= 2)
        if labels:
            tp = sum(1 for t in bars if st.get(t,0) >= 2 and t in lblset)
            fp = nflag - tp
            fn = len(lblset) - tp
            prec = 100*tp/nflag if nflag else 0
            rec  = 100*tp/len(lblset) if lblset else 0
            f1   = 2*prec*rec/(prec+rec) if prec+rec else 0
            summary.append((name, len(rngs), nflag, prec, rec, f1))
        else:
            summary.append((name, len(rngs), nflag, 0, 0, 0))

        L.append("\n### %s\n" % name)
        L.append("`l1=%d  l2=%d  bm=%d`   -   %d ranges, %d bars flagged (%.1f%%)\n"
                 % (cfg['l1'], cfg['l2'], cfg['bm'], len(rngs), nflag, 100*nflag/len(bars)))
        L.append("| # | start | end | bars |" + (" overlaps label |" if labels else ""))
        L.append("|---|---|---|---|" + ("---|" if labels else ""))
        idx = {t: i for i, t in enumerate(bars)}
        for i, (s, e) in enumerate(rngs, 1):
            n = idx[e] - idx[s] + 1
            row = "| %d | %s | %s | %d |" % (i, s, e, n)
            if labels:
                hit = sum(1 for t in bars if s <= t <= e and t in lblset)
                row += " %d/%d |" % (hit, n)
            L.append(row)

    if labels:
        L.append("\n## Summary\n")
        L.append("| setting | ranges | bars flagged | precision | recall | F1 |")
        L.append("|---|---|---|---|---|---|")
        for nm, nr, nf, p, r, f in summary:
            L.append("| %s | %d | %d | %.1f%% | %.1f%% | %.1f |" % (nm, nr, nf, p, r, f))
        L.append("\nprecision = flagged bars that are inside a label.  "
                 "recall = labelled bars that were flagged.  "
                 "A random detector firing at the same rate would score "
                 "precision %.1f%%.\n" % (100*len(lblset)/len(bars)))

    open(a.out, "w").write("\n".join(L) + "\n")
    print("wrote %s" % a.out)
    for nm, nr, nf, p, r, f in summary:
        print("  %-22s ranges=%-4d bars=%-5d prec=%.1f%% rec=%.1f%% F1=%.1f" % (nm, nr, nf, p, r, f))

if __name__ == "__main__":
    main()
