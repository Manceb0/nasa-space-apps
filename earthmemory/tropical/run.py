"""Pruebas tropicales (método Jane): ¿las contradicciones entre productos de lluvia siguen la física de una isla
tropical?

Predicciones REGISTRADAS ANTES de correr (2026-11-15; ver PREDICCIONES): si la tabla de resultados las contradice,
se informa tal cual.

Datos (todo de solo lectura):
- IMERG V07 Final diario y CHIRPS v2.0 diario agregado a 0.1° (data/tendencias/derivados/*.npz, motor P0).
- IBTrACS v04r01, cuenca Atlántico Norte (NOAA NCEI), data/tropical/ibtracs/.
- Copernicus DEM GLO-90 (data/nacional_hr/dem/*.tif).
- Resultados P0 (results/tendencias/tendencias_celdas.csv) y re-auditoría (results/auditoria/reauditoria_96_episodios.csv).
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats as sstats

from ..hr.common import ROOT, sha256, write_json
from ..tendencias import datos

OUT = ROOT / "results" / "tropical"
IBT = ROOT / "data" / "tropical" / "ibtracs" / "ibtracs.NA.list.v04r01.csv"
DEM_DIR = ROOT / "data" / "nacional_hr" / "dem"
SEED = 20261115
WIND_FROM_DEG = 70.0          # alisio del ENE (dirección DESDE la que sopla)
RADII_KM = (300, 500, 800)
R_MAIN = 500

PREDICCIONES = {
    "P1_ciclones": "En días con un ciclón tropical a < 500 km, IMERG y CHIRPS coinciden MÁS en lluvia fuerte "
                   "(CSI ≥ 50 mm mayor) y el disparador > 100 mm/48 h queda MENOS veces sin confirmar que en días "
                   "sin ciclón de la misma temporada (ago-nov).",
    "P1b_extremos": "La fracción de máximos anuales de lluvia diaria (Rx1day) que cae en días de ciclón es mucho "
                    "mayor que la fracción de días con ciclón.",
    "P2_barlovento": "En las laderas que miran al alisio (ascenso forzado > 0), CHIRPS da más lluvia media que IMERG "
                     "(IMERG subestima la lluvia orográfica cálida) y el acuerdo diario es menor.",
    "P2b_lluvia_debil": "Las celdas con SDII en disputa son las que más difieren en frecuencia de días húmedos "
                        "(≥ 1 mm) entre productos.",
    "P3_sin_explicar": "Los 28 episodios sin explicar se concentran en retornos de la estación seca (dic-abr) con "
                       "lluvia de retorno modesta, más que el resto de los 96.",
    "P4_instrumento": "La diferencia mensual IMERG − CHIRPS en frecuencia de días húmedos tiene un punto de cambio "
                      "cerca de 2014-2015 (paso de TRMM a GPM).",
}


# ---------------------------------------------------------------- utilidades
def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dphi = p2 - p1
    dl = np.radians(lon2 - lon1)
    a = np.sin(dphi / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return 2 * r * np.arcsin(np.sqrt(a))


def csi(a, b, thr):
    A, B = a >= thr, b >= thr
    hit = np.sum(A & B)
    union = np.sum(A | B)
    return hit / union if union else np.nan, int(hit), int(union)


def year_boot(fn, years_of_day, groups, n=2000, seed=SEED):
    """IC 95 % remuestreando AÑOS completos (conserva la dependencia dentro de cada temporada)."""
    rng = np.random.default_rng(seed)
    uy = np.unique(years_of_day)
    idx_by_year = {y: np.flatnonzero(years_of_day == y) for y in uy}
    out = []
    for _ in range(n):
        ys = rng.choice(uy, uy.size, replace=True)
        sel = np.concatenate([idx_by_year[y] for y in ys])
        out.append(fn(sel))
    return np.asarray(out)


# ---------------------------------------------------------------- datos base
def load():
    Pi = np.load(datos.DER / "imerg_diario_01.npz")["P"]
    Pc = np.load(datos.DER / "chirps_diario_01.npz")["P"]
    cells = datos.cells_table()
    inc = cells["incluida"].fillna(False).astype(bool).to_numpy()
    I = Pi.reshape(Pi.shape[0], -1)[:, inc].astype(float)
    C = Pc.reshape(Pc.shape[0], -1)[:, inc].astype(float)
    days = datos.DAYS
    assert I.shape[0] == days.size == C.shape[0]
    LO, LA = datos.GRID01.mesh()
    lat = LA.ravel()[inc]
    lon = LO.ravel()[inc]
    ids = cells["celda"].to_numpy()[inc]
    return I, C, days, lat, lon, ids, inc


def tc_days(days, lat, lon):
    """Días (UTC) con al menos una posición de ciclón tropical/subtropical a < R km de alguna celda de RD."""
    t = pd.read_csv(IBT, skiprows=[1], usecols=["SID", "SEASON", "NAME", "ISO_TIME", "NATURE", "LAT", "LON",
                                                 "TRACK_TYPE", "USA_WIND"], low_memory=False)
    t = t[(t["SEASON"].astype(int).between(2000, 2025)) & (t["TRACK_TYPE"] == "main")
          & (t["NATURE"].isin(["TS", "SS", "MX", "NR"]))].copy()
    t["LAT"] = t["LAT"].astype(float)
    t["LON"] = t["LON"].astype(float)
    t = t[t["LAT"].between(5, 35) & t["LON"].between(-90, -50)]
    # distancia mínima a las celdas de RD (submuestreo de celdas para velocidad)
    sub = np.arange(0, lat.size, 3)
    d = haversine_km(t["LAT"].to_numpy()[:, None], t["LON"].to_numpy()[:, None], lat[sub][None, :], lon[sub][None, :])
    t["dist_km"] = d.min(1)
    t["dia"] = pd.to_datetime(t["ISO_TIME"]).dt.floor("D")
    out = {}
    dd = pd.DatetimeIndex(days.astype("datetime64[D]"))
    for R in RADII_KM:
        near = t[t["dist_km"] < R]
        s = set(near["dia"])
        out[R] = np.array([x in s for x in dd])
    storms = (t[t["dist_km"] < R_MAIN].groupby(["SID", "NAME"])
              .agg(primer_dia=("dia", "min"), ultimo_dia=("dia", "max"), dist_min_km=("dist_km", "min"),
                   viento_max_kt=("USA_WIND", lambda s: pd.to_numeric(s, errors="coerce").max()))
              .reset_index().sort_values("primer_dia"))
    storms = storms[storms["primer_dia"].dt.year.between(2001, 2024)]
    return out, storms


# ---------------------------------------------------------------- prueba 1
def prueba_ciclones(I, C, days, TC, storms):
    dd = pd.DatetimeIndex(days.astype("datetime64[D]"))
    month = dd.month.to_numpy()
    year = dd.year.to_numpy()
    ason = np.isin(month, [8, 9, 10, 11])
    I2 = I + np.vstack([np.zeros((1, I.shape[1])), I[:-1]])       # suma 48 h (día y anterior)
    C2 = C + np.vstack([np.zeros((1, C.shape[1])), C[:-1]])
    rows = []
    for R, tc in TC.items():
        groups = {"ciclon": tc, "sin_ciclon_ago-nov": ason & ~tc, "sin_ciclon_todo": ~tc}
        for g, m in groups.items():
            sel = np.flatnonzero(m)
            for thr in (20, 50):
                v, hit, uni = csi(I[sel], C[sel], thr)
                rows.append({"radio_km": R, "grupo": g, "metrica": f"CSI_diario_{thr}mm", "valor": v,
                             "n_dias": int(m.sum()), "aciertos": hit, "union": uni})
            # disparador 48 h en IMERG, confirmado si CHIRPS >= 100 en la celda el mismo día ±1
            trig = I2[sel] >= 100
            cc = C2 >= 100
            conf_any = cc.copy()
            conf_any[1:] |= cc[:-1]
            conf_any[:-1] |= cc[1:]
            n_tr = int(trig.sum())
            n_unconf = int((trig & ~conf_any[sel]).sum())
            rows.append({"radio_km": R, "grupo": g, "metrica": "disparo_48h_IMERG_sin_confirmar", "valor":
                         n_unconf / n_tr if n_tr else np.nan, "n_dias": int(m.sum()), "aciertos": n_tr - n_unconf,
                         "union": n_tr})
    tab = pd.DataFrame(rows)

    # IC por años de la diferencia (radio principal)
    tc = TC[R_MAIN]
    ctrl = ason & ~tc

    def diff_csi(sel, thr=50):
        a = sel[tc[sel]]
        b = sel[ctrl[sel]]
        return csi(I[a], C[a], thr)[0] - csi(I[b], C[b], thr)[0]

    boot = year_boot(diff_csi, year, None)
    v0 = diff_csi(np.arange(days.size))

    # extremos: día del Rx1day anual por celda
    ext = {}
    for name, P in (("IMERG", I), ("CHIRPS", C)):
        fr = []
        tot = 0
        on_tc = 0
        for y in np.unique(year):
            iy = np.flatnonzero(year == y)
            Py = np.nan_to_num(P[iy], nan=-1)
            k = iy[Py.argmax(0)]
            near = tc[k] | tc[np.clip(k - 1, 0, None)] | tc[np.clip(k + 1, None, days.size - 1)]
            on_tc += int(near.sum())
            tot += k.size
        base = float(((tc | np.roll(tc, 1) | np.roll(tc, -1))).mean())
        ext[name] = {"fraccion_rx1day_en_ciclon_pm1d": on_tc / tot, "fraccion_dias_ciclon_pm1d": base,
                     "razon": (on_tc / tot) / base if base else None}
    res = {"tabla": tab, "dif_csi50_ciclon_menos_control": float(v0),
           "ic95_por_anios": [float(np.nanpercentile(boot, 2.5)), float(np.nanpercentile(boot, 97.5))],
           "extremos": ext, "n_tormentas_500km_2001_2024": int(len(storms)),
           "dias_ciclon_500km": int(tc.sum())}
    return res


# ---------------------------------------------------------------- prueba 2
def dem_ascent(lat_c, lon_c, res=0.1):
    """Ascenso forzado medio (m por km recorrido por el alisio) y sombra (máx. elevación a barlovento − propia)."""
    import rasterio
    from rasterio.merge import merge

    srcs = [rasterio.open(p) for p in sorted(DEM_DIR.glob("*.tif"))]
    Z, tr = merge(srcs, res=(1 / 120, 1 / 120), resampling=rasterio.enums.Resampling.average)  # ~0.93 km
    for s in srcs:
        s.close()
    Z = Z[0].astype(float)
    Z[Z < -100] = np.nan
    Z = np.where(np.isnan(Z), 0.0, Z)                    # mar = 0 m
    ny, nx = Z.shape
    x0, dx, y0, dy = tr.c, tr.a, tr.f, tr.e
    lats = y0 + (np.arange(ny) + 0.5) * dy
    lons = x0 + (np.arange(nx) + 0.5) * dx
    km_lat = 111.32
    km_lon = 111.32 * np.cos(np.radians(lats))[:, None]
    dzdy = np.gradient(Z, axis=0) / (dy * km_lat)        # m/km hacia el norte (dy<0 => filas hacia el sur)
    dzdx = np.gradient(Z, axis=1) / (dx * km_lon)        # m/km hacia el este
    to = np.radians(WIND_FROM_DEG + 180)                 # el aire viaja hacia el OSO
    ascent = dzdx * np.sin(to) + dzdy * np.cos(to)       # > 0: el terreno sube en la dirección del viento
    asc_c, elev_c, shadow_c = [], [], []
    frm = np.radians(WIND_FROM_DEG)
    for la, lo in zip(lat_c, lon_c):
        r = (lats >= la - res / 2) & (lats < la + res / 2)
        c = (lons >= lo - res / 2) & (lons < lo + res / 2)
        blk = ascent[np.ix_(r, c)]
        zb = Z[np.ix_(r, c)]
        asc_c.append(float(np.mean(blk)))
        elev_c.append(float(np.mean(zb)))
        # perfil a barlovento: 5..40 km hacia el ENE
        mx = 0.0
        for dist in np.arange(5, 41, 2.5):
            pla = la + dist * np.cos(frm) / km_lat
            plo = lo + dist * np.sin(frm) / (km_lat * np.cos(np.radians(la)))
            i = int((pla - y0) / dy)
            j = int((plo - x0) / dx)
            if 0 <= i < ny and 0 <= j < nx:
                mx = max(mx, Z[i, j])
        shadow_c.append(float(mx - np.mean(zb)))
    return np.array(asc_c), np.array(elev_c), np.array(shadow_c)


def toroidal_spearman(x, y, lat, lon, n=999, seed=SEED):
    """ρ de Spearman con p calibrado desplazando de forma toroidal el campo de la covariable en la rejilla 0.1°."""
    rng = np.random.default_rng(seed)
    ii = np.round((lat - lat.min()) / 0.1).astype(int)
    jj = np.round((lon - lon.min()) / 0.1).astype(int)
    F = np.full((ii.max() + 1, jj.max() + 1), np.nan)
    F[ii, jj] = x
    ok = np.isfinite(x) & np.isfinite(y)
    rho = sstats.spearmanr(x[ok], y[ok]).statistic
    null = []
    tries = 0
    while len(null) < n and tries < n * 5:
        tries += 1
        di, dj = rng.integers(0, F.shape[0]), rng.integers(0, F.shape[1])
        if di == 0 and dj == 0:
            continue
        xs = np.roll(np.roll(F, di, 0), dj, 1)[ii, jj]
        okk = np.isfinite(xs) & np.isfinite(y)
        if okk.sum() < 0.7 * ok.sum():
            continue
        null.append(sstats.spearmanr(xs[okk], y[okk]).statistic)
    null = np.asarray(null)
    p = (1 + np.sum(np.abs(null) >= abs(rho))) / (1 + null.size)
    return float(rho), float(p), int(ok.sum()), int(null.size)


def prueba_relieve(I, C, lat, lon, ids):
    asc, elev, shadow = dem_ascent(lat, lon)
    tc = pd.read_csv(ROOT / "results" / "tendencias" / "tendencias_celdas.csv")
    s = tc[(tc["indice"] == "SDII") & (tc["periodo"] == "anual") & (tc["fuente"] == "IMERG")].set_index("celda")
    disputa = s.reindex(ids)["clase_confianza"].eq("en disputa").astype(float).to_numpy()
    mi, mc = np.nanmean(I, 0) * 365.25, np.nanmean(C, 0) * 365.25
    log_ratio = np.log(mc / mi)
    wet_i, wet_c = np.nanmean(I >= 1, 0), np.nanmean(C >= 1, 0)
    dwet = wet_i - wet_c                               # > 0: IMERG ve más días húmedos
    agree = np.array([csi(I[:, k], C[:, k], 20)[0] for k in range(I.shape[1])])
    cov = {"ascenso_forzado_m_km": asc, "sombra_barlovento_m": shadow, "elevacion_m": elev}
    outc = {"log_CHIRPS_sobre_IMERG": log_ratio, "CSI_diario_20mm": agree, "SDII_en_disputa": disputa,
            "dif_frecuencia_dias_humedos_IMERG_menos_CHIRPS": dwet}
    rows = []
    for yn, y in outc.items():
        for xn, x in cov.items():
            rho, p, n, ns = toroidal_spearman(x, y, lat, lon)
            rows.append({"resultado": yn, "covariable": xn, "rho": rho, "p_toroidal": p, "n_celdas": n,
                         "n_sustitutos": ns})
        if yn != "SDII_en_disputa":
            rho, p, n, ns = toroidal_spearman(y, disputa, lat, lon)
            rows.append({"resultado": "SDII_en_disputa", "covariable": yn, "rho": rho, "p_toroidal": p,
                         "n_celdas": n, "n_sustitutos": ns})
    # barlovento frente a sotavento (terciles de ascenso)
    q = np.quantile(asc, [1 / 3, 2 / 3])
    clase = np.where(asc <= q[0], "sotavento/bajada", np.where(asc >= q[1], "barlovento/subida", "intermedio"))
    by = (pd.DataFrame({"clase": clase, "log_ratio": log_ratio, "csi20": agree, "disputa": disputa, "dwet": dwet})
          .groupby("clase").agg(n=("csi20", "size"), CHIRPS_sobre_IMERG_mediana=("log_ratio", lambda v: float(np.exp(np.median(v)))),
                                CSI20_mediana=("csi20", "median"), fraccion_SDII_en_disputa=("disputa", "mean"),
                                dif_frecuencia_humeda_mediana=("dwet", "median")).reset_index())
    celdas = pd.DataFrame({"celda": ids, "lat": lat, "lon": lon, "ascenso_m_km": asc, "sombra_m": shadow,
                           "elevacion_m": elev, "lluvia_IMERG_mm_anio": mi, "lluvia_CHIRPS_mm_anio": mc,
                           "frec_humeda_IMERG": wet_i, "frec_humeda_CHIRPS": wet_c, "CSI20": agree,
                           "SDII_en_disputa": disputa, "clase_relieve": clase})
    return pd.DataFrame(rows), by, celdas


# ---------------------------------------------------------------- prueba 3
def prueba_sin_explicar(I, days, lat, lon, TC):
    D = pd.read_csv(ROOT / "results" / "auditoria" / "reauditoria_96_episodios.csv")
    D["sin_explicar"] = D["causa_atribuida"].eq("sin_explicar") & D["posible_diferencia"].astype(bool)
    dd = pd.DatetimeIndex(days.astype("datetime64[D]"))
    tc = TC[R_MAIN]
    feats = []
    for r in D.itertuples():
        la, lo = map(float, r.celda.split("_"))
        m = (np.abs(lat - la) <= 0.125) & (np.abs(lon - lo) <= 0.125)
        ret = pd.Timestamp(r.retorno_imerg)
        sel = (dd.year == ret.year) & (dd.month == ret.month)
        p = np.nanmean(I[np.ix_(sel, m)], 1) if m.any() else np.full(sel.sum(), np.nan)
        clim = np.nanmean(I[np.ix_(dd.month == ret.month, m)], 1).sum() / 24 if m.any() else np.nan
        tot = float(np.nansum(p))
        feats.append({"total_mes_retorno_mm": tot, "fraccion_dia_mas_lluvioso": float(np.nanmax(p) / tot) if tot > 0 else np.nan,
                      "dias_ciclon_mes_retorno": int(tc[sel].sum()), "anomalia_vs_clim": tot / clim if clim else np.nan})
    F = pd.concat([D.reset_index(drop=True), pd.DataFrame(feats)], axis=1)
    F["temporada_retorno"] = np.select([F["mes_retorno"].isin([12, 1, 2, 3, 4]), F["mes_retorno"].isin([5, 6, 7])],
                                       ["seca dic-abr", "temprana may-jul"], "tardía ago-nov")
    ct = pd.crosstab(F["temporada_retorno"], F["sin_explicar"])
    rng = np.random.default_rng(SEED)
    chi0 = sstats.chi2_contingency(ct).statistic
    lab = F["sin_explicar"].to_numpy()
    seas = F["temporada_retorno"].to_numpy()
    null = [sstats.chi2_contingency(pd.crosstab(seas, rng.permutation(lab))).statistic for _ in range(4999)]
    p_seas = (1 + np.sum(np.asarray(null) >= chi0)) / 5000
    comp = []
    for col in ("total_mes_retorno_mm", "anomalia_vs_clim", "fraccion_dia_mas_lluvioso", "dias_ciclon_mes_retorno"):
        a = F.loc[lab, col].dropna()
        b = F.loc[~lab, col].dropna()
        u = sstats.mannwhitneyu(a, b)
        comp.append({"variable": col, "mediana_sin_explicar": float(a.median()), "mediana_resto": float(b.median()),
                     "n_sin_explicar": int(a.size), "n_resto": int(b.size), "p_mann_whitney": float(u.pvalue)})
    return F, ct, float(p_seas), pd.DataFrame(comp)


# ---------------------------------------------------------------- prueba 4
def pettitt(x):
    n = x.size
    r = sstats.rankdata(x)
    U = np.array([2 * r[:k].sum() - k * (n + 1) for k in range(1, n)])
    k = int(np.argmax(np.abs(U)))
    return k + 1, float(np.abs(U[k]))


def prueba_instrumento(I, C, days):
    dd = pd.DatetimeIndex(days.astype("datetime64[D]"))
    ym = dd.to_period("M")
    df = pd.DataFrame({"ym": ym, "wi": np.nanmean(I >= 1, 1), "wc": np.nanmean(C >= 1, 1),
                       "pi": np.nanmean(I, 1), "pc": np.nanmean(C, 1)})
    m = df.groupby("ym").mean()
    out = {}
    rng = np.random.default_rng(SEED)
    for name, s in (("frecuencia_dias_humedos_IMERG_menos_CHIRPS", m["wi"] - m["wc"]),
                    ("log_lluvia_IMERG_sobre_CHIRPS", np.log(m["pi"] / m["pc"]))):
        s = s - s.groupby(s.index.month).transform("mean")          # quita el ciclo estacional
        x = s.to_numpy()
        k, K = pettitt(x)
        # nulo: permutación de bloques de 12 meses (conserva autocorrelación intra-anual)
        blocks = x[: (x.size // 12) * 12].reshape(-1, 12)
        null = []
        for _ in range(2999):
            xb = blocks[rng.permutation(blocks.shape[0])].ravel()
            null.append(pettitt(xb)[1])
        p = (1 + np.sum(np.asarray(null) >= K)) / 3000
        out[name] = {"punto_de_cambio": str(s.index[k]), "K": K, "p_bloques_12m": float(p),
                     "media_antes": float(x[:k].mean()), "media_despues": float(x[k:].mean())}
    return out, m


def prueba_quien_cambio(corte="2013-10-01"):
    """¿Quién cambió en el punto de cambio: IMERG, CHIRPS o la lluvia? Testigo: pluviómetros GHCN-Daily.
    Frecuencia de días húmedos (≥ 1 mm) solo en los días con dato de la estación, antes y después del corte."""
    from ..auditoria.estaciones import read_ghcnd

    Pi = np.load(datos.DER / "imerg_diario_01.npz")["P"]
    Pc = np.load(datos.DER / "chirps_diario_01.npz")["P"]
    days = pd.DatetimeIndex(datos.DAYS.astype("datetime64[D]"))
    g = datos.GRID01
    rows = []
    for p in sorted((ROOT / "data" / "auditoria" / "ghcnd").glob("*.csv")):
        d = read_ghcnd(p.stem)
        if d is None or d.empty:
            continue
        la, lo = float(d["LATITUDE"].iloc[0]), float(d["LONGITUDE"].iloc[0])
        i = int((la - g.lat0) / g.res)
        j = int((lo - g.lon0) / g.res)
        s = d.set_index("fecha")["mm"].groupby(level=0).first().reindex(days)
        ok = s.notna().to_numpy()
        for per, m in (("antes", days < corte), ("despues", days >= corte)):
            k = ok & m
            ci = Pc[k, i, j]
            kk = np.isfinite(ci)
            rows.append({"estacion": p.stem, "periodo": per, "n_dias": int(kk.sum()),
                         "frec_estacion": float(np.mean(s.to_numpy()[k][kk] >= 1)),
                         "frec_IMERG": float(np.mean(Pi[k, i, j][kk] >= 1)),
                         "frec_CHIRPS": float(np.mean(ci[kk] >= 1))})
    T = pd.DataFrame(rows)
    W = T.pivot(index="estacion", columns="periodo")
    chg = pd.DataFrame({f"cambio_{c}": W[(c, "despues")] - W[(c, "antes")]
                        for c in ("frec_estacion", "frec_IMERG", "frec_CHIRPS")})
    chg["n_antes"] = W[("n_dias", "antes")]
    chg["n_despues"] = W[("n_dias", "despues")]
    return T, chg.reset_index()


# ---------------------------------------------------------------- main
def main():
    OUT.mkdir(parents=True, exist_ok=True)
    write_json(OUT / "predicciones_registradas.json", {"fecha": "2026-11-15", "predicciones": PREDICCIONES})
    I, C, days, lat, lon, ids, inc = load()
    TC, storms = tc_days(days, lat, lon)
    storms.to_csv(OUT / "ciclones_a_500km.csv", index=False)

    r1 = prueba_ciclones(I, C, days, TC, storms)
    r1["tabla"].to_csv(OUT / "p1_ciclones_acuerdo.csv", index=False)
    print("[P1]", json.dumps({k: v for k, v in r1.items() if k != "tabla"}, ensure_ascii=False, default=float))
    print(r1["tabla"][r1["tabla"]["radio_km"] == R_MAIN].to_string(index=False))

    t2, by2, cel2 = prueba_relieve(I, C, lat, lon, ids)
    t2.to_csv(OUT / "p2_relieve_spearman.csv", index=False)
    by2.to_csv(OUT / "p2_relieve_terciles.csv", index=False)
    cel2.to_csv(OUT / "p2_celdas.csv", index=False)
    print("[P2]\n", t2.to_string(index=False), "\n", by2.to_string(index=False))

    F3, ct3, p3, comp3 = prueba_sin_explicar(I, days, lat, lon, TC)
    F3.to_csv(OUT / "p3_96_episodios.csv", index=False)
    comp3.to_csv(OUT / "p3_comparacion.csv", index=False)
    print("[P3]\n", ct3.to_string(), "\np_temporada", p3, "\n", comp3.to_string(index=False))

    r4, m4 = prueba_instrumento(I, C, days)
    m4.to_csv(OUT / "p4_mensual.csv")
    print("[P4]", json.dumps(r4, ensure_ascii=False))

    T5, chg5 = prueba_quien_cambio(r4["frecuencia_dias_humedos_IMERG_menos_CHIRPS"]["punto_de_cambio"] + "-01")
    T5.to_csv(OUT / "p5_quien_cambio_estaciones.csv", index=False)
    chg5.to_csv(OUT / "p5_quien_cambio_resumen.csv", index=False)
    print("[P5]\n", chg5.to_string(index=False))

    write_json(OUT / "resumen.json", {
        "p5_quien_cambio": chg5.to_dict(orient="records"),
        "predicciones": PREDICCIONES,
        "p1": {k: v for k, v in r1.items() if k != "tabla"},
        "p3": {"tabla_temporada": ct3.to_dict(), "p_permutacion_temporada": p3},
        "p4": r4,
        "entradas_sha256": {"ibtracs": sha256(IBT)},
        "semilla": SEED,
    })


if __name__ == "__main__":
    main()
