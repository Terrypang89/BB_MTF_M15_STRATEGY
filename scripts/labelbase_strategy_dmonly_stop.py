#!/usr/bin/env python3
"""
labelbase_strategy_dmonly_stop.py
DMONLY + stop-loss variant.

Rules (priority order, exits before entries):
  1. TofySideway S_ flag present      -> EXIT ALL      (SIDEWAYS)
  2. adverse excursion >= STOP        -> EXIT ALL      (STOP_LOSS)  [new]
  3. LONG  and dm in {2,4}            -> EXIT          (REVERSAL_DN)
  4. SHORT and dm in {1,5}            -> EXIT          (REVERSAL_UP)
  5. FLAT and dm in {1,5}             -> OPEN LONG
  6. FLAT and dm in {2,4}             -> OPEN SHORT
Close-only: no re-entry on the same bar as an exit (matches committed DMONLY).
STOP = 0 disables the stop and MUST reproduce DMONLY: 1120 trades / +$968.93
"""
import re,sys,bisect

def run(LOG, STOP=0.0, verbose=True):
    rx15=re.compile(r'^([\d.]+ [\d:]+).*\[M15\].*diffMid_Trend_M15:\s*\[\s*([-\d.]+)')
    rxsf=re.compile(r'^([\d.]+ [\d:]+).*Sideway_val:\s*\[\s*[0-9]+(?:-S_([0-9]+))?')
    rxpx=re.compile(r'^([\d.]+ [\d:]+).*\[M5\].*close_M5:\s*\[\s*([-\d.]+)')
    M15={};SF={};PX={}
    for line in open(LOG,errors='ignore'):
        m=rxpx.search(line)
        if m: PX[m.group(1)]=float(m.group(2))
        m=rxsf.search(line)
        if m: SF[m.group(1)[:16]]=int(m.group(2)) if m.group(2) else 0
        m=rx15.search(line)
        if m: M15[m.group(1)[:16]]=float(m.group(2))
    ts=sorted(PX); pv=[PX[t] for t in ts]
    bars=sorted(M15)

    pos='FLAT'; ent=0.0; ent_bar=0; ent_i=0; mae=0.0
    trades=[]
    for bi,t in enumerate(bars):
        i=bisect.bisect_right(ts,t+":99")-1
        if i<0: continue
        p=pv[i]; dm=M15[t]; sf=SF.get(t,0)>0
        reason=None; exit_px=p

        if pos!='FLAT':
            # --- intrabar MAE + stop, walking M5 bars since the last M15 bar
            for j in range(ent_i+1, i+1):
                adv = (ent-pv[j]) if pos=='LONG' else (pv[j]-ent)
                if adv>mae: mae=adv
                if STOP>0 and mae>=STOP:
                    reason='STOP_LOSS'
                    exit_px = (ent-STOP) if pos=='LONG' else (ent+STOP)
                    break
            if reason is None:
                if sf: reason='SIDEWAYS'
                elif pos=='LONG'  and dm in (2.,4.): reason='REVERSAL_DN'
                elif pos=='SHORT' and dm in (1.,5.): reason='REVERSAL_UP'

        if reason:
            pnl=(exit_px-ent) if pos=='LONG' else (ent-exit_px)
            trades.append(dict(pnl=pnl,mae=mae,bars=bi-ent_bar,reason=reason,dir=pos))
            pos='FLAT'; mae=0.0
            ent_i=i
            continue                      # close-only: no re-entry this bar

        if pos=='FLAT':
            if dm in (1.,5.): pos,ent,ent_bar,ent_i,mae='LONG',p,bi,i,0.0
            elif dm in (2.,4.): pos,ent,ent_bar,ent_i,mae='SHORT',p,bi,i,0.0
        else:
            ent_i=i

    tot=sum(t['pnl'] for t in trades)
    wins=[t for t in trades if t['pnl']>0]
    if verbose:
        print("STOP=%s | trades %d | win %d (%.1f%%) | TOTAL %+.2f"%(
            ("OFF" if STOP==0 else "$%.0f"%STOP), len(trades), len(wins),
            100*len(wins)/len(trades) if trades else 0, tot))
    return trades, tot

if __name__=="__main__":
    LOG=sys.argv[1]
    print("=== REGRESSION: stop disabled must equal committed DMONLY (1120 / +968.93) ===")
    tr,tot=run(LOG,0.0)
    print()
    print("=== with stop ===")
    for s in (30.0,):
        tr2,tot2=run(LOG,s)
        from collections import defaultdict
        g=defaultdict(lambda:[0,0.0])
        for t in tr2:
            g[t['reason']][0]+=1; g[t['reason']][1]+=t['pnl']
        print("  exit reasons:")
        for k in sorted(g): print("    %-12s %4d  %+9.2f"%(k,g[k][0],g[k][1]))
        b=defaultdict(lambda:[0,0.0])
        for t in tr2:
            key='1' if t['bars']<=1 else '2' if t['bars']==2 else '3-5' if t['bars']<=5 else '6+'
            b[key][0]+=1; b[key][1]+=t['pnl']
        print("  bars held:")
        for k in ('1','2','3-5','6+'): print("    %-4s %4d  %+9.2f"%(k,b[k][0],b[k][1]))
