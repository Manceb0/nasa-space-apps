"""Diagnóstico exploratorio de umbrales; solo lee resultados/cachés existentes.

Ejecutar en la imagen phantom:latest, con el repositorio en /app de solo lectura
y results/cierre montado aparte con permiso de escritura. No descarga datos.
"""
from __future__ import annotations

import hashlib
import json
import pickle
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from earthmemory.hr.common import bh_fdr
from earthmemory.tendencias.estadistica import trend_rows

OUT = Path('results/cierre')
SEED = 20261115


def ci_ratio(num, den):
    """Bootstrap circular de bloques de 3 años; todos los lugares viajan juntos."""
    rng = np.random.default_rng(SEED)
    starts = rng.integers(0, len(num), (2000, int(np.ceil(len(num) / 3))))
    ix = ((starts[..., None] + np.arange(3)) % len(num)).reshape(2000, -1)[:, :len(num)]
    n, d = np.asarray(num)[ix].sum(1), np.asarray(den)[ix].sum(1)
    ratios = n[d > 0] / d[d > 0]
    return np.quantile(ratios, [0.025, 0.975]).tolist() if ratios.size else [None, None]


def drought_margin():
    state = pickle.loads(Path('data/auditoria/cache/estado.pkl').read_bytes())
    spi = state['dr']['spi_prov']
    dates = pd.date_range('2001-01-01', '2024-12-01', freq='MS')
    rows = []
    for name, keys in [('cuatro', list(spi)), ('IMERG_CHIRPS', ['IMERG', 'CHIRPS'])]:
        s = np.stack([spi[k] for k in keys])
        valid = np.isfinite(s).all(0)
        alarm = valid & (s <= -1).any(0)
        flip = alarm & (s > -1).any(0)
        for margin in [0, 0.1, 0.25, 0.5]:
            keep = valid & (np.abs(s + 1) >= margin).all(0)
            n = np.array([(flip & keep)[dates.year == y].sum() for y in range(2001, 2025)])
            d = np.array([(alarm & keep)[dates.year == y].sum() for y in range(2001, 2025)])
            rows.append(dict(productos=name, margen_spi=margin, n_validos=int(valid.sum()),
                             n_alarmas_original=int(alarm.sum()), n_alarmas_retenidas=int(d.sum()),
                             n_discrepancias_retenidas=int(n.sum()),
                             tasa_condicional=float(n.sum()/d.sum()), ic95_bloques3=ci_ratio(n, d),
                             cobertura_alarmas=float(d.sum()/alarm.sum())))
    return rows


def rainfall():
    cells = pd.read_csv('results/nacional/celdas_imerg.csv').set_index('celda')
    lat = 17.45 + np.arange(26) * .1
    lon = -72.05 + np.arange(39) * .1
    ids = [f'{a:.3f}_{b:.3f}' for a in lat for b in lon]
    use = cells.reindex(ids)['incluida'].to_numpy(bool)
    assert use.sum() == 442
    arrays = [np.load(f'data/tendencias/derivados/{k}_diario_01.npz')['P'].reshape(-1, 1014)[:, use]
              for k in ['imerg', 'chirps']]
    dates = pd.date_range('2001-01-01', '2024-12-31')
    assert all(a.shape == (len(dates), 442) for a in arrays)
    paired = np.isfinite(arrays[0]) & np.isfinite(arrays[1])
    arrays = [np.where(paired, a, np.nan) for a in arrays]
    # Series de bandas y descomposición algebraica; área RD dentro de cada celda.
    weights = cells.reindex(ids).iloc[np.flatnonzero(use)]
    weights = (weights['area_km2'] * weights['frac_pais']).to_numpy(float)
    weights = weights / weights.sum()
    bands = [(0, .5), (.5, 1), (1, 2), (2, 5), (5, 10), (10, np.inf)]
    band_rows, decomposition = [], []
    for product, a in zip(['IMERG', 'CHIRPS'], arrays):
        counts, masses = [], []
        for year in range(2001, 2025):
            b = a[dates.year == year]
            for lower, upper in bands:
                mask = (b >= lower) & (b < upper)
                band_rows.append(dict(producto=product, anio=year, banda_inf_mm=lower,
                                      banda_sup_mm=upper if np.isfinite(upper) else None,
                                      dias_media_area=float(mask.sum(0) @ weights),
                                      lluvia_mm_media_area=float(np.where(mask, b, 0).sum(0) @ weights)))
            wet = b >= 1
            counts.append(wet.sum(0) @ weights)
            masses.append(np.where(wet, b, 0).sum(0) @ weights)
        log_count, log_mass = np.log(counts), np.log(masses)
        x = np.arange(24)
        slope = lambda y: float(np.polyfit(x, y, 1)[0] * 10)
        value = dict(producto=product, log_dias_pendiente_decada=slope(log_count),
                     log_lluvia_humeda_pendiente_decada=slope(log_mass),
                     log_intensidad_pendiente_decada=slope(log_mass-log_count))
        assert np.isclose(value['log_intensidad_pendiente_decada'],
                          value['log_lluvia_humeda_pendiente_decada']-value['log_dias_pendiente_decada'])
        decomposition.append(value)
    pd.DataFrame(band_rows).to_csv(OUT/'bandas_lluvia_anuales.csv', index=False)
    rows, detailed = [], []
    for threshold in [.5, 1, 2, 5, 10]:
        for metric in ['R_dias', 'SDII']:
            results = []
            for product, a in zip(['IMERG', 'CHIRPS'], arrays):
                annual = []
                for year in range(2001, 2025):
                    b = a[dates.year == year]
                    wet = b >= threshold
                    count = wet.sum(0)
                    value = count.astype(float) if metric == 'R_dias' else np.divide(
                        np.where(wet, b, 0).sum(0), count, out=np.full(442, np.nan), where=count > 0)
                    value[np.isfinite(b).sum(0) < .95 * len(b)] = np.nan
                    annual.append(value)
                trend = trend_rows(np.stack(annual).T, np.arange(2001, 2025))
                q = bh_fdr(trend['p'])
                results.append((trend, q))
                detailed.extend(dict(celda=cell, producto=product, umbral_mm=threshold, metrica=metric,
                                     pendiente_decada=float(trend['pendiente_decada'][i]),
                                     ic95_inf=float(trend['ic95_inf'][i]), ic95_sup=float(trend['ic95_sup'][i]),
                                     p=float(trend['p'][i]), q=float(q[i]))
                                for i, cell in enumerate(np.array(ids)[use]))
            a, b = results
            opposite = a[0]['signo'] * b[0]['signo'] < 0
            sig_a, sig_b = a[1] <= .10, b[1] <= .10
            rows.append(dict(umbral_mm=threshold, metrica=metric,
                             significativas_imerg=int(sig_a.sum()), significativas_chirps=int(sig_b.sum()),
                             opuestas_al_menos_una_sig=int((opposite & (sig_a | sig_b)).sum()),
                             opuestas_ambas_sig=int((opposite & sig_a & sig_b).sum()),
                             mediana_pendiente_imerg=float(np.nanmedian(a[0]['pendiente_decada'])),
                             mediana_pendiente_chirps=float(np.nanmedian(b[0]['pendiente_decada']))))
    pd.DataFrame(detailed).to_csv(OUT/'tendencias_sensibilidad_celdas.csv', index=False)
    correlations = []
    for block in [1, 2, 5, 10]:
        for phase in range(block):
            count = (len(dates)-phase)//block
            aa, bb = [x[phase:phase+count*block].reshape(count, block, 442).sum(1) for x in arrays]
            rho = [spearmanr(aa[:, i], bb[:, i], nan_policy='omit').statistic for i in range(442)]
            correlations.append(dict(dias_bloque=block, fase=phase, n_bloques=count,
                                     rho_mediana=float(np.nanmedian(rho))))
    return rows, correlations, decomposition


def yuna():
    daily = pd.read_parquet('results/yuna/series_diarias_zonas.parquet')
    daily.index = pd.to_datetime(daily.index)
    cat = pd.read_csv('results/yuna/catalogo_eventos.csv')
    summaries, frames = [], []
    obs = pd.read_csv('results/yuna/mcdwd_diario_zonas.csv', parse_dates=['fecha'])
    for ident in ['2024-11', '2017-04', '2025-10']:
        r = cat[cat.id == ident].iloc[0]
        start, end = pd.Timestamp(r.inicio), pd.Timestamp(r.fin)
        f = daily.loc[start-pd.Timedelta(days=5):end+pd.Timedelta(days=5),
                      [c for c in daily if c.startswith('imerg_')]].copy()
        f['fecha'] = f.index
        f['id'] = ident
        f['ventana_panel'] = (f.index >= start-pd.Timedelta(days=3)) & (f.index <= end)
        f['ventana_acierto'] = (f.index >= start-pd.Timedelta(days=2)) & (f.index <= end)
        f['disparo100'] = f['imerg_max48_yuna'] > 100
        o = obs[(obs.fecha >= start-pd.Timedelta(days=5)) & (obs.fecha <= end+pd.Timedelta(days=5))]
        f = f.reset_index(drop=True).merge(o, on='fecha', how='outer')
        f['id'] = ident
        frames.append(f)
        def peak(offset):
            s = daily.loc[start-pd.Timedelta(days=offset):end, 'imerg_max48_yuna'].dropna()
            return {'fecha':str(s.idxmax().date()), 'mm':float(s.max())} if len(s) else None
        summaries.append(dict(id=ident, inicio=str(start.date()), fin=str(end.date()),
                              max_panel=peak(3), max_puntuado=peak(2)))
    pd.concat(frames).to_csv(OUT/'cronologia_yuna.csv', index=False)
    return summaries


def main():
    OUT.mkdir(exist_ok=True, parents=True)
    inputs = ['data/auditoria/cache/estado.pkl', 'data/tendencias/derivados/imerg_diario_01.npz',
              'data/tendencias/derivados/chirps_diario_01.npz', 'results/nacional/celdas_imerg.csv',
              'results/yuna/series_diarias_zonas.parquet', 'results/yuna/catalogo_eventos.csv',
              'results/yuna/mcdwd_diario_zonas.csv']
    hashes = {p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in inputs}
    summary = {'estado':'exploratorio; no atribuye causas ni calibra umbral físico',
               'seed':SEED, 'bootstrap_replicas':2000, 'hashes_sha256':hashes}
    summary['yuna'] = yuna()
    print(json.dumps({'yuna':summary['yuna']}, ensure_ascii=False), flush=True)
    summary['spi_margenes'] = drought_margin()
    print(json.dumps({'spi_margenes':summary['spi_margenes']}, ensure_ascii=False), flush=True)
    summary['lluvia_umbrales'], summary['correlacion_acumulados'], summary['descomposicion_log'] = rainfall()
    base = next(r for r in summary['lluvia_umbrales'] if r['umbral_mm'] == 1 and r['metrica'] == 'SDII')
    assert (base['significativas_imerg'], base['significativas_chirps'], base['opuestas_al_menos_una_sig']) == (122, 72, 160)
    assert summary['spi_margenes'][0]['n_discrepancias_retenidas'] == 2836
    (OUT/'resumen.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    print(json.dumps({'validacion':'reproduce SDII 122/72/160 y desacuerdos SPI 2836',
                      'descomposicion_log':summary['descomposicion_log']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
