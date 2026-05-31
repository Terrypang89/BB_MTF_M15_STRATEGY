"""Generate references/version_profit.md from all version JSON files."""
import json, os

base = 'references/Backtest_data'

def load_version(ver_dir):
    rpt = os.path.join(ver_dir, 'report_tables_clean.json')
    if not os.path.exists(rpt):
        return None
    with open(rpt) as f:
        data = json.load(f)
    res = data.get('table_results', {})
    if isinstance(res, list):
        res = {row['label'].rstrip(':'): row['value']
               for row in res if isinstance(row, dict) and 'label' in row}

    def floatval(s):
        try:
            return float(str(s).replace(' ', '').replace(',', ''))
        except Exception:
            return None

    net = floatval(res.get('Total Net Profit'))
    pf  = floatval(res.get('Profit Factor'))
    deals = []
    for row in data.get('table_deals', []):
        try:
            p   = floatval(row.get('Profit', ''))
            t   = str(row.get('Time', ''))
            sym = str(row.get('Symbol', ''))
            if p is None or not sym or sym == 'nan':
                continue
            deals.append({
                'time':   t,
                'profit': p,
                'type':   str(row.get('Type', '')),
                'dir':    str(row.get('Direction', '')),
                'deal':   str(row.get('Deal', '')),
            })
        except Exception:
            pass
    return {'net': net, 'pf': pf, 'deals': deals, 'n_deals': len(deals)}


all_dirs = sorted([
    d for d in os.listdir(base)
    if os.path.isdir(os.path.join(base, d)) and d.startswith('V')
])

# Separate standard M5-period dirs from multi-period (_M15/_M30) variants
ver_names    = [d for d in all_dirs if '_M' not in d]
ver_names_m15 = [d for d in all_dirs if d.endswith('_M15')]
ver_names_m30 = [d for d in all_dirs if d.endswith('_M30')]

versions = {}
for d in ver_names:
    v = load_version(os.path.join(base, d))
    if v:
        versions[d] = v

versions_m15 = {}
for d in ver_names_m15:
    v = load_version(os.path.join(base, d))
    if v:
        versions_m15[d] = v

versions_m30 = {}
for d in ver_names_m30:
    v = load_version(os.path.join(base, d))
    if v:
        versions_m30[d] = v

vlist = sorted(versions.keys())

periods = {
    'V22.22': 'Jan-Apr 2026',
    'V22.23': 'Jan 2026 only',
    'V22.24': 'Jan-Apr 2026',
    'V22.25': 'Jan-Apr 2026',
    'V22.26': 'Jan-Apr 2026',
    'V22.27': 'Jan-Apr 2026',
    'V22.28': 'Jan-Apr 2026',
    'V22.29': 'Jan-Apr 2026',
    'V22.30': 'Jan-Apr 2026',
    'V22.31': 'Jan-Apr 2026',
    'V22.32': 'Jan-Apr 2026',
    'V22.33': 'Jan-Apr 2026',
    'V22.34': 'Jan-Apr 2026',
    'V22.35': 'Jan-Apr 2026',
    'V22.36': 'Jan-Apr 2026',
    'V22.37': 'Jan-Apr 2026',
    'V22.38': 'Jan-Apr 2026',
    'V22.39': 'Jan-Apr 2026',
    'V22.40': 'Jan-Apr 2026',
    'V22.41': 'Jan-Apr 2026',
    'V22.42': 'Jan-Apr 2026',
    'V22.43': 'Jan-Apr 2026',
    'V22.45': 'Jan-Apr 2026',
    'V22.46': 'Jan-Apr 2026',
    'V22.47': 'Jan-Apr 2026',
    # multi-period variants (chart period, not test period)
    'V22.41_M15': 'Jan-Apr 2026',
    'V22.41_M30': 'Jan-Apr 2026',
    'V22.42_M15': 'Jan-Apr 2026',
    'V22.42_M30': 'Jan-Apr 2026',
    'V22.46_M15': 'Jan-Apr 2026',
    'V22.46_M30': 'Jan-Apr 2026',
}

# Collect all timestamps where any version had a loss < -10
all_loss_times = set()
for ver, v in versions.items():
    for deal in v['deals']:
        if deal['profit'] < -10:
            all_loss_times.add(deal['time'])

# Build deal map: time -> {ver: profit}
deal_map  = {}
deal_type = {}
for ver, v in versions.items():
    for deal in v['deals']:
        t = deal['time']
        if t in all_loss_times:
            if t not in deal_map:
                deal_map[t] = {}
            deal_map[t][ver] = deal['profit']
            if t not in deal_type:
                deal_type[t] = deal['type'].replace('/out', '').replace('/in', '')

lines = []
lines.append('# Version Profit Analysis')
lines.append('')
lines.append('Tracks net profit per version and deal-level loss comparison across all versions.')
lines.append('Generated from `report_tables_clean.json` in each version folder.')
lines.append('')
lines.append('---')
lines.append('')

# ---- Part 1 ----
lines.append('## Part 1 — Net Profit Comparison (All Versions)')
lines.append('')
lines.append('| Version | Period | Net Profit | PF | Deals | vs Prev Same-Period |')
lines.append('|---------|--------|-----------|-----|-------|---------------------|')

period_last = {}
for ver in vlist:
    v = versions[ver]
    net_val = v['net'] if v['net'] is not None else 0.0
    net_str = ('+' if net_val >= 0 else '') + f'{net_val:.2f}'
    pf_str  = str(v['pf']) if v['pf'] is not None else 'N/A'
    period  = periods.get(ver, 'unknown')
    prev    = period_last.get(period)
    if prev is not None and v['net'] is not None:
        diff   = v['net'] - prev[1]
        sign   = '+' if diff >= 0 else ''
        trend  = 'IMPROVED' if diff > 0 else 'REGRESSION'
        vs_str = f'{sign}{diff:.2f} vs {prev[0]} **{trend}**'
    else:
        vs_str = 'baseline'
    lines.append(
        f'| {ver} | {period} | {net_str} | {pf_str} | {v["n_deals"]} | {vs_str} |'
    )
    period_last[period] = (ver, v['net'])

lines.append('')
lines.append('> V22.23 covers Jan 2026 only and is not comparable to V22.24+ (Jan-Apr).')
lines.append('')
lines.append('---')
lines.append('')

# ---- Part 2 ----
lines.append('## Part 2 — Deal Loss Comparison (profit < -10)')
lines.append('')
lines.append('Each row is a deal close time. Value = deal profit for that version.')
lines.append('`--` = deal absent. Parenthesised values = profit >= -10 at that timestamp.')
lines.append('`ELIM` tag = eliminated in latest vs previous. `NEW` tag = appeared in latest.')
lines.append('')

header = '| Time | Dir | ' + ' | '.join(vlist) + ' |'
sep    = '|------|-----|' + '|'.join([':------:' for _ in vlist]) + '|'
lines.append(header)
lines.append(sep)

row_count = 0
for t in sorted(deal_map.keys()):
    # Only show rows where at least one version has a real loss (< -10)
    if not any(p < -10 for p in deal_map[t].values()):
        continue

    row_vals = []
    for ver in vlist:
        p = deal_map[t].get(ver)
        if p is None:
            row_vals.append('--')
        elif p < -10:
            row_vals.append(f'{p:.2f}')
        elif p <= 0:
            row_vals.append(f'({p:.2f})')
        else:
            row_vals.append(f'+{p:.2f}')

    tp   = deal_type.get(t, '')
    vlast = vlist[-1] if vlist else None
    vprev = vlist[-2] if len(vlist) >= 2 else None
    v_cur  = deal_map[t].get(vlast)  if vlast else None
    v_prev = deal_map[t].get(vprev) if vprev else None
    tag = ''
    if v_prev is not None and v_prev < -10 and (v_cur is None or v_cur >= -10):
        tag = ' **ELIM**'
    elif (v_prev is None or v_prev >= -10) and v_cur is not None and v_cur < -10:
        tag = ' **NEW**'

    lines.append('| ' + t + tag + ' | ' + tp + ' | ' + ' | '.join(row_vals) + ' |')
    row_count += 1

lines.append('')
lines.append(f'*{row_count} unique loss timestamps across all versions.*')
lines.append('')
lines.append('---')
lines.append('')

# ---- Summary ----
lines.append('## Summary Statistics')
lines.append('')
lines.append('| Version | Total Deals | Losses<-10 | Sum of Losses | Avg Loss |')
lines.append('|---------|------------|-----------|--------------|---------|')
for ver in vlist:
    v      = versions[ver]
    losses = [d for d in v['deals'] if d['profit'] < -10]
    s      = sum(d['profit'] for d in losses) if losses else 0.0
    avg    = s / len(losses) if losses else 0.0
    lines.append(
        f'| {ver} | {v["n_deals"]} | {len(losses)} | {s:.2f} | {avg:.2f} |'
    )

lines.append('')
lines.append('---')
lines.append('')

# ---- Latest vs Previous key observations (dynamic) ----
vlast = vlist[-1] if vlist else None
vprev = vlist[-2] if len(vlist) >= 2 else None

if vlast and vprev:
    lines.append(f'## {vlast} vs {vprev} — Key Changes')
    lines.append('')

    vlast_loss = {t for t in deal_map if (deal_map[t].get(vlast) or 0) < -10}
    vprev_loss = {t for t in deal_map if (deal_map[t].get(vprev) or 0) < -10}

    elim   = sorted(vprev_loss - vlast_loss)
    new_   = sorted(vlast_loss - vprev_loss)
    shared = sorted(vlast_loss & vprev_loss)
    worse  = [(t, deal_map[t][vlast] - deal_map[t][vprev])
              for t in shared if deal_map[t][vlast] - deal_map[t][vprev] <= -1]
    better = [(t, deal_map[t][vlast] - deal_map[t][vprev])
              for t in shared if deal_map[t][vlast] - deal_map[t][vprev] >= 1]
    same_c = len(shared) - len(worse) - len(better)

    lines.append('| Category | Count | Timestamps & Profits |')
    lines.append('|----------|-------|----------------------|')

    elim_detail = '; '.join(f'{t} ({deal_map[t][vprev]:.2f})' for t in elim)
    new_detail  = '; '.join(f'{t} ({deal_map[t][vlast]:.2f})' for t in new_) or 'none'
    worse_d     = '; '.join(f'{t} (delta {d:.2f})' for t, d in worse) or 'none'
    better_d    = '; '.join(f'{t} (delta +{d:.2f})' for t, d in better) or 'none'

    lines.append(f'| ELIMINATED | {len(elim)} | {elim_detail} |')
    lines.append(f'| NEW | {len(new_)} | {new_detail} |')
    lines.append(f'| WORSE (delta <= -1) | {len(worse)} | {worse_d} |')
    lines.append(f'| BETTER (delta >= +1) | {len(better)} | {better_d} |')
    lines.append(f'| SAME | {same_c} | (all other {same_c} deals unchanged) |')

# ---- Part 3 ----
lines.append('## Part 3 — Per-Version Loss Details (sorted highest loss first)')
lines.append('')
lines.append('Each version lists all deals with profit < -10, sorted from largest loss to smallest.')
lines.append('')

for ver in vlist:
    v = versions[ver]
    losses = sorted(
        [d for d in v['deals'] if d['profit'] < -10],
        key=lambda x: x['profit']
    )
    lines.append(f'### {ver} — {len(losses)} losses, sum {sum(d["profit"] for d in losses):.2f}')
    lines.append('')
    lines.append('| # | Deal | Time | Dir | Loss |')
    lines.append('|---|------|------|-----|------|')
    for rank, d in enumerate(losses, 1):
        dir_str = d['type'].replace('/out', '').replace('/in', '')
        lines.append(
            f'| {rank} | {d["deal"]} | {d["time"]} | {dir_str} | {d["profit"]:.2f} |'
        )
    lines.append('')

# ---- Part 4 — Multi-Period Comparison ----
if versions_m15 or versions_m30:
    lines.append('')
    lines.append('---')
    lines.append('')
    lines.append('## Part 4 — Multi-Period Comparison (M5 vs M15 vs M30 chart period)')
    lines.append('')
    lines.append('When M15/M30 period data exists, compare net profit across chart periods.')
    lines.append('Goal: identify WHY other periods outperform M5 and apply insights to M5 gate improvements.')
    lines.append('')
    lines.append('| Version | Chart Period | Net Profit | Deals | vs M5 | Notes |')
    lines.append('|---------|-------------|-----------|-------|-------|-------|')

    # Find base versions that have multi-period data
    multi_bases = set()
    for d in list(versions_m15.keys()) + list(versions_m30.keys()):
        base_ver = d.replace('_M15', '').replace('_M30', '')
        multi_bases.add(base_ver)

    for base_ver in sorted(multi_bases):
        m5_data  = versions.get(base_ver)
        m15_data = versions_m15.get(base_ver + '_M15')
        m30_data = versions_m30.get(base_ver + '_M30')
        m5_net   = m5_data['net']  if m5_data  else None

        def fmt_vs(net):
            if net is None or m5_net is None:
                return 'N/A'
            diff = net - m5_net
            sign = '+' if diff >= 0 else ''
            tag  = 'BETTER' if diff > 0 else 'WORSE' if diff < 0 else 'SAME'
            return f'{sign}{diff:.2f} **{tag}**'

        def fmt_net(net):
            if net is None: return 'N/A'
            return ('+' if net >= 0 else '') + f'{net:.2f}'

        m5_str  = fmt_net(m5_net)
        m5_n    = str(m5_data['n_deals'])  if m5_data  else 'N/A'
        m15_net = m15_data['net'] if m15_data else None
        m30_net = m30_data['net'] if m30_data else None

        if m5_data:
            lines.append(f'| {base_ver} | M5 (production) | {m5_str} | {m5_n} | baseline | — |')
        if m15_data:
            m15_str = fmt_net(m15_net)
            m15_n   = str(m15_data['n_deals'])
            lines.append(f'| {base_ver}_M15 | M15 | {m15_str} | {m15_n} | {fmt_vs(m15_net)} | — |')
        if m30_data:
            m30_str = fmt_net(m30_net)
            m30_n   = str(m30_data['n_deals'])
            lines.append(f'| {base_ver}_M30 | M30 | {m30_str} | {m30_n} | {fmt_vs(m30_net)} | — |')

    lines.append('')
    lines.append('### Multi-Period Loss Analysis — Losses unique to M5 vs shared across periods')
    lines.append('')
    lines.append('Each loss in M5 is categorized: SHARED (also a loss in M15/M30) or M5-ONLY.')
    lines.append('M5-ONLY losses are gate fix candidates — they indicate the M5 trigger fires when higher-period charts remain in a valid direction.')
    lines.append('')

    for base_ver in sorted(multi_bases):
        m5_data  = versions.get(base_ver)
        m15_data = versions_m15.get(base_ver + '_M15')
        m30_data = versions_m30.get(base_ver + '_M30')
        if not m5_data:
            continue

        m5_losses = {d['time']: d['profit'] for d in m5_data['deals'] if d['profit'] < -10}
        m15_times = {d['time'] for d in m15_data['deals']} if m15_data else set()
        m30_times = {d['time'] for d in m30_data['deals']} if m30_data else set()

        m5_only = {t for t in m5_losses if t not in m15_times and t not in m30_times}
        shared  = {t for t in m5_losses if t in m15_times or t in m30_times}

        lines.append(f'#### {base_ver} — M5 loss breakdown ({len(m5_losses)} losses < -10)')
        lines.append('')
        lines.append(f'- **M5-ONLY**: {len(m5_only)} losses (gate fix candidates)')
        lines.append(f'- **SHARED** (also in M15 or M30): {len(shared)} losses (macro events, accept)')
        lines.append('')

        if m5_only:
            lines.append('| Time | M5 Profit | In M15? | In M30? |')
            lines.append('|------|----------|---------|---------|')
            for t in sorted(m5_only, key=lambda x: m5_losses[x]):
                in_m15 = 'yes' if t in m15_times else 'no'
                in_m30 = 'yes' if t in m30_times else 'no'
                lines.append(f'| {t} | {m5_losses[t]:.2f} | {in_m15} | {in_m30} |')
            lines.append('')

content = '\n'.join(lines)
out_path = 'references/version_profit.md'
with open(out_path, 'w', encoding='utf-8') as f:
    f.write(content)
print(f'Written {len(lines)} lines, {row_count} deal rows -> {out_path}')
