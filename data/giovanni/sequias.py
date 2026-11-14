import csv, sys, os, json
D = sys.argv[1]
def load(name):
    rows = list(csv.reader(open(os.path.join(D, name))))
    out = []
    for r in rows:
        if r and r[0][:2] == '20' and r[0][4] == '-':
            v = float(r[1])
            if v <= -9999 or v >= 1e14: v = None
            out.append((r[0][:7], v))
    return out
def pct(xs, p):  # numpy 'linear' percentile
    xs = sorted(xs); k = (len(xs)-1)*p/100; f = int(k); c = min(f+1, len(xs)-1)
    return xs[f] + (xs[c]-xs[f])*(k-f)
def median(xs): return pct(xs, 50)
def runs(series, tag):
    by = {m: [v for d, v in series if int(d[5:7]) == m and v is not None] for m in range(1, 13)}
    p20 = {m: pct(by[m], 20) for m in by}; med = {m: median(by[m]) for m in by}
    flags = [(d, v, v is not None and v < p20[int(d[5:7])]) for d, v in series]
    res = []; cur = []
    for d, v, f in flags + [(None, None, False)]:
        if f: cur.append((d, v))
        else:
            if len(cur) >= 2:
                obs = sum(v for _, v in cur); nor = sum(med[int(d2[5:7])] for d2, _ in cur)
                res.append(dict(ini=cur[0][0], fin=cur[-1][0], n=len(cur), obs=obs, normal=nor, deficit=obs-nor, pct=100*obs/nor))
            cur = []
    nflag = sum(1 for *_, f in flags if f)
    return res, nflag, sum(1 for _, v in series if v is None)
def t2m_anom(series):
    by = {m: [v for d, v in series if int(d[5:7]) == m and v is not None] for m in range(1, 13)}
    mean = {m: sum(by[m])/len(by[m]) for m in by}
    return {d: v - mean[int(d[5:7])] for d, v in series if v is not None}
def months(a, b):
    y, m = int(a[:4]), int(a[5:7]); out = []
    while True:
        s = f'{y}-{m:02d}'; out.append(s)
        if s == b: return out
        m += 1
        if m > 12: y, m = y+1, 1
out = {}
for reg in ['noroeste', 'jaragua']:
    ta = t2m_anom(load(f'merra2_t2m_{reg}.csv'))
    out[reg] = {}
    for var, fn in [('precip', f'imerg_precip_{reg}.csv'), ('soil0_10', f'gldas_soilmoi0_10cm_{reg}.csv'), ('rootzone', f'gldas_rootmoist_{reg}.csv')]:
        s = load(fn); r, nflag, nmiss = runs(s, var)
        for x in r:
            ms = months(x['ini'], x['fin']); x['t2m_anom'] = sum(ta[m] for m in ms)/len(ms)
        out[reg][var] = dict(periods=r, n_months_flagged=nflag, n_missing=nmiss, n=len(s))
json.dump(out, open(sys.argv[2], 'w'), indent=1)
for reg in out:
    for var in out[reg]:
        o = out[reg][var]; print(f'\n### {reg} {var}: n={o["n"]} missing={o["n_missing"]} flagged={o["n_months_flagged"]} periods={len(o["periods"])}')
        for x in sorted(o['periods'], key=lambda x: x['deficit']):
            print(f"{x['ini']}..{x['fin']} n={x['n']} obs={x['obs']:.1f} normal={x['normal']:.1f} def={x['deficit']:.1f} pct={x['pct']:.0f}% dT={x['t2m_anom']:+.2f}")
