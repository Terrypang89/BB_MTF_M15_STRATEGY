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
    ("Z  TofySideway S_ (control)", dict(l1=1, l2=0, bm=2, use_sflag=True)),
])

# ----------------------------------------------------------------------------
# Reference bounds. These are NOT ladder settings - they bracket what any
# detector could achieve. P uses the hand labels directly (a hindsight ceiling);
# N removes the sideway exit entirely (the floor). With --ceiling-out they are
# written to their own file so they do not sit among the ladder results.
# ----------------------------------------------------------------------------
CEILING_SETTINGS = OrderedDict([
    ("P  PERFECT - the labels themselves", dict(l1=1, l2=0, bm=2, use_labels=True)),
    ("N  NO sideway exit at all", dict(l1=1, l2=0, bm=2, use_none=True)),
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
    'dmt15': r'diffMid_Trend_M15:\s*\[\s*([-\d.]+)',
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
            if m: D[k][m.group(1)[:16]] = float(m.group(2))
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

def run(D, PX, l1, l2, bm, use_sflag=False, SF=None, use_labels=False, use_none=False, LBLSET=None):
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
    if use_none:
        for t in bars: st[t] = 0
        return st
    if use_labels:
        for t in bars: st[t] = 2 if t in (LBLSET or set()) else 0
        return st
    if use_sflag:
        # control: the existing TofySideway S_ flag, not the ladder
        for t in bars:
            st[t] = 2 if (SF or {}).get(t, 0) > 0 else 0
        return st
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
        w15s = int(D['ws15'][t]); w30s = last('ws30', t)
        if w30s is not None: w30s = int(w30s)
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


def simulate_pnl(D, PX, st, bars, spread=0.0):
    """
    DMONLY with the ladder as its sideways exit.
      priority 1  sideway (state >= 2)      -> exit all, never enter
      priority 2  opposite dm               -> exit (no same-bar re-entry)
      priority 3  flat and dm 1|5 -> LONG, dm 2|4 -> SHORT
    close-only: after any exit, no re-entry on the same bar.
    Returns (trades, summary_dict).
    """
    pk = sorted(PX); pv = [PX[t] for t in pk]
    def price(t):
        j = bisect.bisect_right(pk, t + ":99") - 1
        return PX[pk[j]] if j >= 0 else None

    pos, ent, ent_i, trades = 'FLAT', 0.0, 0, []
    for i, t in enumerate(bars):
        dm = D['dmt15'].get(t)
        p  = price(t)
        if dm is None or p is None:
            continue
        sw = st.get(t, 0) >= 2
        dm_up   = dm in (1.0, 5.0)
        dm_down = dm in (2.0, 4.0)

        reason = None
        if pos != 'FLAT':
            if sw:                              reason = 'SIDEWAYS'
            elif pos == 'LONG'  and dm_down:    reason = 'REVERSAL_DN'
            elif pos == 'SHORT' and dm_up:      reason = 'REVERSAL_UP'

        if reason:
            pnl = (p - ent) if pos == 'LONG' else (ent - p)
            trades.append(dict(entry=bars[ent_i], exit=t, dir=pos,
                               pnl=pnl - spread, bars=i - ent_i, reason=reason))
            pos = 'FLAT'
            continue                            # close-only

        if pos == 'FLAT' and not sw:
            if dm_up:     pos, ent, ent_i = 'LONG',  p, i
            elif dm_down: pos, ent, ent_i = 'SHORT', p, i

    tot  = sum(x['pnl'] for x in trades)
    wins = [x for x in trades if x['pnl'] > 0]
    buckets = {'1': [0, 0.0], '2': [0, 0.0], '3-5': [0, 0.0], '6+': [0, 0.0]}
    for x in trades:
        k = '1' if x['bars'] <= 1 else '2' if x['bars'] == 2 else '3-5' if x['bars'] <= 5 else '6+'
        buckets[k][0] += 1; buckets[k][1] += x['pnl']
    reasons = {}
    for x in trades:
        r = reasons.setdefault(x['reason'], [0, 0.0])
        r[0] += 1; r[1] += x['pnl']
    return trades, dict(n=len(trades), total=tot,
                        wr=(100.0*len(wins)/len(trades) if trades else 0.0),
                        buckets=buckets, reasons=reasons)

def match_label(s, e, labels, bars):
    """
    Which label does a detected range correspond to?
    Returns (text, matched_bool). Matched = the two ranges overlap at all.
    """
    idx = {t: i for i, t in enumerate(bars)}
    det = set(t for t in bars if s <= t <= e)
    if not det: return ("-", False)
    best, bestn = None, 0
    for k, (ls, le) in enumerate(labels, 1):
        lab = set(t for t in bars if ls <= t <= le)
        ov = len(det & lab)
        if ov > bestn: best, bestn = k, ov
    if best is None:
        return ("MISS", False)
    return ("L%d %d/%d" % (best, bestn, len(det)), True)


def combined_timeline(trades, rngs, bars, PX, labels=None):
    """
    One chronological table: TRADE rows (positions) interleaved with SIDEWAY rows
    (detected ranges the strategy sat out). start/end are entry/exit for a trade and
    range start/end for a sideway. Cumulative P&L carries through both.
    """
    pk = sorted(PX)
    def price(t):
        j = bisect.bisect_right(pk, t + ":99") - 1
        return PX[pk[j]] if j >= 0 else None
    idx = {t: i for i, t in enumerate(bars)}

    rows = []
    for x in trades:
        rows.append(dict(kind='TRADE', start=x['entry'], end=x['exit'], bars=x['bars'],
                         what=x['dir'], pnl=x['pnl'], note=x['reason']))
    for k, (s_, e) in enumerate(rngs, 1):
        nb = idx[e] - idx[s_] + 1 if s_ in idx and e in idx else 0
        note = 'flat - sitting out'
        if labels:
            mtxt, ok = match_label(s_, e, labels, bars)
            note = ('flat - %s' % mtxt) if ok else 'flat - NO MATCHING LABEL'
        rows.append(dict(kind='SIDEWAY', start=s_, end=e, bars=nb,
                         what='R%d' % k, pnl=None, note=note))
    rows.sort(key=lambda r: (r['start'], 0 if r['kind'] == 'TRADE' else 1))

    L = []
    L.append("")
    L.append("#### Combined timeline")
    L.append("")
    L.append("`TRADE` rows are positions, `SIDEWAY` rows are detected ranges. "
             "`start`/`end` = entry/exit or range start/end. Cumulative carries through both.")
    L.append("")
    L.append("| # | type | start | end | bars | dir / range | start px | end px | P&L | cumulative | note |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|")
    cum = 0.0
    for i, r in enumerate(rows, 1):
        if r['pnl'] is not None:
            cum += r['pnl']; p = "%+.2f" % r['pnl']
        else:
            p = "-"
        p1 = price(r['start']); p2 = price(r['end'])
        L.append("| %d | %s | %s | %s | %d | %s | %s | %s | %s | %+.2f | %s |" % (
            i, r['kind'], r['start'], r['end'], r['bars'], r['what'],
            ("%.2f" % p1) if p1 else "-", ("%.2f" % p2) if p2 else "-",
            p, cum, r['note']))
    tb = sum(r['bars'] for r in rows if r['kind'] == 'TRADE')
    sb = sum(r['bars'] for r in rows if r['kind'] == 'SIDEWAY')
    ntr = sum(1 for r in rows if r['kind'] == 'TRADE')
    nsw = sum(1 for r in rows if r['kind'] == 'SIDEWAY')
    L.append("")
    L.append("**%d trades (%d bars in position) and %d detected ranges (%d bars flat).** "
             "Ranges are %.0f%% of the period." % (ntr, tb, nsw, sb, 100.0*sb/(tb+sb) if tb+sb else 0))
    return L

def parse_labels(path):
    """read start/end pairs out of a markdown table"""
    rx = re.compile(r'^\|\s*\d+\s*\|\s*(\d{4}\.\d{2}\.\d{2} \d{2}:\d{2})\s*\|\s*(\d{4}\.\d{2}\.\d{2} \d{2}:\d{2})\s*\|')
    out = []
    for line in open(path, errors='ignore'):
        m = rx.match(line)
        if m: out.append((m.group(1), m.group(2)))
    return out

def build_report(D, PX, SF, bars, labels, lblset, settings, a, title, note):
    """Generate one markdown report for a set of settings."""
    L = [title, ""]
    L.append("Input: `%s`   bars: %d%s\n" % (a.log, len(bars),
             ("   month filter: %s" % a.month) if a.month else ""))
    L.append("Ranges are consecutive `state >= 2` bars, gaps of <= %d bar(s) bridged, "
             "ranges shorter than %d bars dropped.\n" % (a.gap, a.min_bars))
    if note:
        L.append(note + "\n")

    if labels:
        L.append("\n## Hand-labelled ranges (target)\n")
        L.append("| # | start | end | bars |")
        L.append("|---|---|---|---|")
        for i, (s, e) in enumerate(labels, 1):
            n = sum(1 for t in bars if s <= t <= e)
            L.append("| %d | %s | %s | %d |" % (i, s, e, n))
        L.append("\n**%d labelled ranges, %d bars (%.1f%% of the period).**\n"
                 % (len(labels), len(lblset), 100*len(lblset)/len(bars)))

    L.append("\n## Results by setting\n")
    summary = []
    for name, cfg in settings.items():
        st = run(D, PX, SF=SF, LBLSET=lblset, **cfg)
        rngs = to_ranges(st, bars, a.min_bars, a.gap)
        nflag = sum(1 for t in bars if st.get(t, 0) >= 2)
        trades, pl = simulate_pnl(D, PX, st, bars, a.spread)
        prec = rec = f1 = 0.0
        if labels and nflag:
            tp = sum(1 for t in bars if st.get(t, 0) >= 2 and t in lblset)
            prec = 100.0*tp/nflag
            rec = 100.0*tp/len(lblset) if lblset else 0.0
            f1 = 2*prec*rec/(prec+rec) if prec+rec else 0.0
        summary.append((name, len(rngs), nflag, prec, rec, f1, pl))

        L.append("\n### %s\n" % name)
        L.append("`l1=%d  l2=%d  bm=%d`   -   %d ranges, %d bars flagged (%.1f%%)\n"
                 % (cfg['l1'], cfg['l2'], cfg['bm'], len(rngs), nflag, 100.0*nflag/len(bars)))
        L.append("**P&L (gross%s):** %d trades, %.1f%% win rate, **%+.2f**\n"
                 % ((", spread %.2f/trade" % a.spread) if a.spread else "",
                    pl['n'], pl['wr'], pl['total']))
        L.append("| # | start | end | bars |" + (" overlap | matched label |" if labels else ""))
        L.append("|---|---|---|---|" + ("---|---|" if labels else ""))
        idx = {t: i for i, t in enumerate(bars)}
        nmatch = 0
        for i, (s, e) in enumerate(rngs, 1):
            n = idx[e] - idx[s] + 1
            row = "| %d | %s | %s | %d |" % (i, s, e, n)
            if labels:
                hit = sum(1 for t in bars if s <= t <= e and t in lblset)
                mtxt, ok = match_label(s, e, labels, bars)
                if ok: nmatch += 1
                row += " %d/%d | %s |" % (hit, n, mtxt if ok else "**NO MATCH**")
            L.append(row)
        if labels and rngs:
            L.append("\n%d of %d detected ranges overlap a label; %d are false positives."
                     % (nmatch, len(rngs), len(rngs) - nmatch))
            covered = set()
            for (s, e) in rngs:
                for k, (ls, le) in enumerate(labels, 1):
                    if any(ls <= t <= le for t in bars if s <= t <= e): covered.add(k)
            missed = [k for k in range(1, len(labels)+1) if k not in covered]
            L.append("Labels with no detection at all: %s\n"
                     % (", ".join("L%d" % k for k in missed) if missed else "none"))
        L.append("\n| exit reason | trades | P&L |")
        L.append("|---|---|---|")
        for r in sorted(pl['reasons']):
            L.append("| %s | %d | %+.2f |" % (r, pl['reasons'][r][0], pl['reasons'][r][1]))
        L.append("\n| bars held | trades | P&L |")
        L.append("|---|---|---|")
        for k in ('1', '2', '3-5', '6+'):
            L.append("| %s | %d | %+.2f |" % (k, pl['buckets'][k][0], pl['buckets'][k][1]))
        if a.timeline:
            L += combined_timeline(trades, rngs, bars, PX, labels if labels else None)

    L.append("\n## Summary\n")
    L.append("| setting | ranges | bars | precision | recall | F1 | trades | win% | **P&L** | 6+ bar P&L |")
    L.append("|---|---|---|---|---|---|---|---|---|---|")
    for nm, nr, nf, p, r, f, pl in summary:
        L.append("| %s | %d | %d | %.1f%% | %.1f%% | %.1f | %d | %.1f%% | **%+.2f** | %+.2f |"
                 % (nm, nr, nf, p, r, f, pl['n'], pl['wr'], pl['total'], pl['buckets']['6+'][1]))
    return L, summary

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("log")
    ap.add_argument("--month", default=None, help="prefix filter e.g. 2026.02")
    ap.add_argument("--labels", default=None, help="markdown file with a label table")
    ap.add_argument("--min-bars", type=int, default=2, help="drop ranges shorter than this")
    ap.add_argument("--gap", type=int, default=1, help="bridge gaps of at most N bars")
    ap.add_argument("--spread", type=float, default=0.0, help="cost per trade")
    ap.add_argument("--timeline", action="store_true",
                    help="emit a combined chronological table of trades and detected ranges")
    ap.add_argument("--out", default="LADDER_RANGES.md")
    ap.add_argument("--ceiling-out", default=None,
                    help="write the label-derived ceiling (P) and no-exit floor (N) to this "
                         "file instead of mixing them in with the ladder settings")
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

    if a.ceiling_out:
        ladder_set, ceil_set = SETTINGS, CEILING_SETTINGS
    else:
        ladder_set = OrderedDict(list(SETTINGS.items()) + list(CEILING_SETTINGS.items()))
        ceil_set = None

    L, summary = build_report(
        D, PX, SF, bars, labels, lblset, ladder_set, a,
        "# Ladder detected sideway ranges",
        None if ceil_set else None)
    open(a.out, "w").write("\n".join(L) + "\n")
    print("wrote %s" % a.out)
    for nm, nr, nf, p, r, f, pl in summary:
        print("  %-30s ranges=%-3d prec=%.1f%% rec=%.1f%% F1=%.1f | trades=%-4d P&L=%+.2f"
              % (nm, nr, p, r, f, pl['n'], pl['total']))

    if ceil_set:
        note = ("> **These two rows are NOT detector settings.** They bracket what any\n"
                "> detector could achieve on this period.\n"
                ">\n"
                "> - **P** uses the hand labels directly as the sideway signal. The labels are\n"
                ">   hindsight, so this is a **ceiling, not a strategy** - it is not tradeable.\n"
                "> - **N** removes the sideway exit entirely - the floor.\n"
                ">\n"
                "> Every real detector lands between them. See `LADDER_RANGES_FEB.md` for those.")
        L2, sum2 = build_report(
            D, PX, SF, bars, labels, lblset, ceil_set, a,
            "# Ceiling and floor — what perfect sideway detection is worth", note)
        open(a.ceiling_out, "w").write("\n".join(L2) + "\n")
        print("wrote %s" % a.ceiling_out)
        for nm, nr, nf, p, r, f, pl in sum2:
            print("  %-30s ranges=%-3d prec=%.1f%% rec=%.1f%% F1=%.1f | trades=%-4d P&L=%+.2f"
                  % (nm, nr, p, r, f, pl['n'], pl['total']))

if __name__ == "__main__":
    main()
