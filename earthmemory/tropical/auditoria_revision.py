"""Revisión independiente del argumento de las pruebas tropicales. No altera los motores ni sus salidas.

Diagnósticos exploratorios, no validación causal. Ejecutar en Docker.
"""
from __future__ import annotations

import hashlib
import json
import pickle
from pathlib import Path

import numpy as np
import pandas as pd

from earthmemory.auditoria.estaciones import read_ghcnd
from earthmemory.tropical import recalculo as rc
from earthmemory.tropical import run as tr

OUT = Path('results/tropical/revision')


def counterexample():
    years = np.arange(2001, 2025)
    reference = np.full((24, 1), 100.)
    smooth = reference + (years-years[0])[:, None]
    series = {'IMERG':{('R1mm', 'anual'):(years, smooth)},
              'CHIRPS':{('R1mm', 'anual'):(years, reference)}}
    corrected = rc.corregir(series, 'A_frec')[('R1mm', 'anual')][1][:, 0]
    slope_before = np.polyfit(years, smooth[:, 0], 1)[0]
    slope_after = np.polyfit(years, corrected, 1)[0]
    smooth_monthly = np.linspace(0, 1, 288)
    k, K = tr.pettitt(smooth_monthly)
    rng = np.random.default_rng(20261115)
    blocks = smooth_monthly.reshape(-1, 12)
    null = [tr.pettitt(blocks[rng.permutation(24)].ravel())[1] for _ in range(2999)]
    return {'datos':'SINTETICOS: tendencia lineal sin salto, referencia constante',
            'pendiente_ols_original':float(slope_before), 'pendiente_ols_ajustada':float(slope_after),
            'reduccion_pendiente_pct':float((1-slope_after/slope_before)*100),
            'pettitt_mes_indice_0':int(k), 'pettitt_p_mismo_nulo_bloques12':float((1+np.sum(np.array(null)>=K))/3000)}


def design(dates, model, tau=None):
    t = (np.arange(len(dates))-len(dates)/2)/12
    columns = [np.ones(len(dates))] + [(dates.month == m).astype(float) for m in range(2, 13)]
    if model in ['tendencia', 'tendencia_escalon', 'cuadratica']:
        columns.append(t)
    if model == 'cuadratica':
        columns.append(t*t)
    if model in ['escalon', 'tendencia_escalon']:
        columns.append((np.arange(len(dates)) >= tau).astype(float))
    return np.column_stack(columns)


def fit_model(dates, y, model, train):
    candidates = range(48, len(y)-48) if model in ['escalon', 'tendencia_escalon'] else [None]
    best = None
    for tau in candidates:
        if tau is not None and (train[:tau].sum()<36 or train[tau:].sum()<36):
            continue
        X = design(dates, model, tau)
        beta = np.linalg.lstsq(X[train], y[train], rcond=None)[0]
        pred = X @ beta
        rss = float(((y[train]-pred[train])**2).sum())
        if best is None or rss < best['rss']:
            best = {'rss':rss, 'pred':pred, 'tau':tau, 'beta':beta, 'k':X.shape[1]}
    return best


def change_models():
    m = pd.read_csv('results/tropical/p4_mensual.csv')
    dates = pd.DatetimeIndex(pd.to_datetime(m.ym))
    responses = {'dif_frecuencia':(m.wi-m.wc).to_numpy(),
                 'log_cantidad':np.log(m.pi/m.pc).to_numpy()}
    rows = []
    for name, y in responses.items():
        for model in ['estacional', 'tendencia', 'escalon', 'tendencia_escalon', 'cuadratica']:
            r = fit_model(dates, y, model, np.ones(len(y), bool))
            errors, folds = [], []
            for lo in range(0, len(y), 36):
                test = np.zeros(len(y), bool)
                test[lo:lo+36] = True
                rr = fit_model(dates, y, model, ~test)
                errors.extend((y[test]-rr['pred'][test])**2)
                folds.append(str(dates[rr['tau']].date()) if rr['tau'] is not None else None)
            rows.append(dict(respuesta=name, modelo=model, rmse_ajuste=float(np.sqrt(r['rss']/len(y))),
                             rmse_cv_bloques3=float(np.sqrt(np.mean(errors))),
                             corte=str(dates[r['tau']].date()) if r['tau'] is not None else None,
                             cortes_por_fold=folds,
                             coef_escalon=float(r['beta'][-1]) if model in ['escalon','tendencia_escalon'] else None))
    return rows


def adjusted_integrity():
    with Path('data/tendencias/derivados/estado_corrida.pkl').open('rb') as f:
        state = pickle.load(f)
    series = state['series']
    inc = state['S']['inc']
    adjusted = rc.corregir(series, 'A_frec')
    rows = []
    for key, val in adjusted.items():
        if isinstance(key, str) or key[0] not in rc.FRECUENCIA:
            continue
        years, a = val
        a = a[:, inc]
        finite = a[np.isfinite(a)]
        rows.append(dict(indice=key[0], periodo=key[1], n_negativos=int((finite<0).sum()),
                         n_valores=int(len(finite)), minimo=float(finite.min())))
    return rows


def station_controls():
    dates = pd.DatetimeIndex(tr.datos.DAYS)
    pi = np.load('data/tendencias/derivados/imerg_diario_01.npz')['P']
    pc = np.load('data/tendencias/derivados/chirps_diario_01.npz')['P']
    rows, monthly = [], []
    for p in sorted(Path('data/auditoria/ghcnd').glob('DRM*.csv')):
        d = read_ghcnd(p.stem)
        s = d.groupby('fecha').mm.first().reindex(dates)
        la, lo = float(d.LATITUDE.iloc[0]), float(d.LONGITUDE.iloc[0])
        i = int((la-tr.datos.GRID01.lat0)/.1)
        j = int((lo-tr.datos.GRID01.lon0)/.1)
        z = pd.DataFrame({'estacion':s.to_numpy(), 'IMERG':pi[:, i, j], 'CHIRPS':pc[:, i, j]}, index=dates)
        z = z.dropna()
        wet = (z >= 1).astype(float)
        wet['mes'] = wet.index.to_period('M')
        grouped = wet.groupby('mes')
        means = grouped[['estacion', 'IMERG', 'CHIRPS']].mean()
        counts = grouped.size()
        mm = means.copy()
        mm['dias_validos'] = counts
        mm['id'] = p.stem
        mm['fecha'] = mm.index.astype(str)
        monthly.append(mm.reset_index(drop=True))
        for min_days in [10, 15, 20]:
            means = mm.loc[mm.dias_validos>=min_days, ['estacion', 'IMERG', 'CHIRPS']].copy()
            idx = pd.DatetimeIndex(means.index.to_timestamp())
            before = idx < '2013-10-01'
            # Equal weight to each calendar month, after pairing the products' dates.
            for source in ['estacion', 'IMERG', 'CHIRPS']:
                a = means[source].to_numpy()
                common = [m for m in range(1, 13) if (before & (idx.month==m)).any() and (~before & (idx.month==m)).any()]
                pre = np.array([np.mean(a[before & (idx.month==m)]) for m in common])
                post = np.array([np.mean(a[~before & (idx.month==m)]) for m in common])
                rows.append(dict(id=p.stem, min_dias_mes=min_days, fuente=source,
                                 cambio_pp_equilibrado_meses=float(np.mean(post-pre)*100) if len(common) else None,
                                 meses_calendario_comunes=len(common),
                                 meses_antes=int(before.sum()), meses_despues=int((~before).sum())))
    pd.concat(monthly).to_csv(OUT/'estaciones_mes.csv', index=False)
    return rows


def cyclone_metrics():
    I, C, days, lat, lon, *_ = tr.load()
    TC, _ = tr.tc_days(days, lat, lon)
    dates = pd.DatetimeIndex(days)
    season = np.isin(dates.month, [8, 9, 10, 11])
    rows = []
    for label, group in [('ciclon_todos', TC[500]), ('ciclon_ASON', TC[500]&season),
                         ('sin_ciclon_ASON', ~TC[500]&season)]:
        a, b = I[group], C[group]
        valid = np.isfinite(a)&np.isfinite(b)
        for threshold in [20, 50]:
            A, B = a[valid]>=threshold, b[valid]>=threshold
            h = int((A&B).sum())
            u = int((A|B).sum())
            n = len(A)
            expected = A.sum()*B.sum()/n
            rows.append(dict(grupo=label, umbral=threshold, n_dias=int(group.sum()),
                             CSI=float(h/u), ETS=float((h-expected)/(u-expected)),
                             frecuencia_A=float(A.mean()), frecuencia_B=float(B.mean())))
    # Exhaustive unique toroidal translations: reconstruct support only; no assumptions about climate null.
    ii = np.round((lat-lat.min())/.1).astype(int)
    jj = np.round((lon-lon.min())/.1).astype(int)
    mask = np.zeros((ii.max()+1, jj.max()+1), bool)
    mask[ii, jj] = True
    unique = sum(int(np.roll(np.roll(mask, a, 0), b, 1)[ii,jj].sum()>=.7*len(ii))
                 for a in range(mask.shape[0]) for b in range(mask.shape[1]) if a or b)
    # Exhaustive counterpart of the original random-shift test, same overlap rule.
    from scipy.stats import spearmanr
    tab = pd.read_csv('results/tropical/p2_celdas.csv')
    exact = []
    for xname, yname in [('ascenso_m_km', 'log_ratio'), ('dif_humeda', 'SDII_en_disputa'), ('sombra_m', 'CSI20')]:
        values = {'log_ratio':np.log(tab.lluvia_CHIRPS_mm_anio/tab.lluvia_IMERG_mm_anio),
                  'dif_humeda':tab.frec_humeda_IMERG-tab.frec_humeda_CHIRPS}
        x = np.asarray(values[xname] if xname in values else tab[xname], float)
        y = np.asarray(values[yname] if yname in values else tab[yname], float)
        F = np.full(mask.shape, np.nan)
        F[ii,jj] = x
        observed = spearmanr(x,y).statistic
        null = []
        for a in range(mask.shape[0]):
            for b in range(mask.shape[1]):
                if not (a or b):
                    continue
                shifted = np.roll(np.roll(F,a,0),b,1)[ii,jj]
                ok = np.isfinite(shifted)&np.isfinite(y)
                if ok.sum()>=.7*len(y):
                    null.append(spearmanr(shifted[ok], y[ok]).statistic)
        p = (1+np.sum(np.abs(null)>=abs(observed)))/(1+len(null))
        exact.append({'x':xname,'y':yname,'rho':float(observed),'p_exhaustivo':float(p),'n':len(null)})
    return rows, {'traslaciones_unicas_con_70pc_solape':unique,
                  'pruebas_exhaustivas':exact,
                  'nota':'n_sustitutos=466 del motor es número de sorteos aceptados, no traducciones únicas'}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    result = {'estado':'diagnósticos exploratorios de revisión; no atribución instrumental',
              'contraejemplo':counterexample(), 'comparacion_modelos':change_models(),
              'integridad_indices_ajustados':adjusted_integrity(),
              'estaciones_control_mes':station_controls()}
    result['ciclones'], result['torus'] = cyclone_metrics()
    files = ['earthmemory/tropical/run.py', 'earthmemory/tropical/recalculo.py',
             'earthmemory/tropical/auditoria_revision.py', 'results/tropical/p4_mensual.csv']
    result['sha256'] = {p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in files}
    (OUT/'resumen.json').write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    for key in ['contraejemplo', 'comparacion_modelos', 'ciclones', 'torus']:
        print(json.dumps({key:result[key]}, ensure_ascii=False), flush=True)
    print('negativos:', sum(r['n_negativos'] for r in result['integridad_indices_ajustados']))
    print('control estaciones:', pd.DataFrame(result['estaciones_control_mes']).query('min_dias_mes==15').groupby('fuente').cambio_pp_equilibrado_meses.mean().to_dict())


if __name__ == '__main__':
    main()
