"""Re-prueba del factor 'intensidad de la lluvia de retorno' con CHIRPS v2.0 diario (en vez de IMERG).

Mismas definiciones que earthmemory.episodes: ventana [fin + 1 mes, retorno + 2 meses]; fracción de la lluvia
caída en días por encima del percentil 95 de los días con lluvia (≥ 1 mm) de la celda; máximo en 1 día. CHIRPS
0.05° se promedia dentro de cada celda GLDAS 0.25° (25 celdas). Misma regresión (control por severidad, bootstrap
de conglomerados de año) y, para comparar manzanas con manzanas, el factor IMERG se recalcula sobre los MISMOS
episodios.

Ojo (revisión adversarial): el CHIRPS v2 diario no es una observación diaria independiente: el total de cada péntada (anclado
a estaciones) se reparte entre sus días con un modelo (README-CHIRPS2-Daily). Por eso se repite con PÉNTADAS
(fracción de la lluvia en péntadas por encima del p95 de las péntadas con lluvia; máximo en 5 días), que es la
escala que CHIRPS sí ancla.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .. import episodes
from .common import CHIRPS_D, RES_NAC

OUTCOMES = ["z_retorno_SM_RAIZ", "z_retorno_SM_0_10", "contradiccion_A_SM_RAIZ"]


def read_year(path):
    from scipy.io import netcdf_file
    with netcdf_file(path, "r", mmap=False) as f:
        v = f.variables
        P = np.array(v["prcp"][:], dtype=float)
        lat = np.array(v["Y"][:], float)
        lon = np.array(v["X"][:], float)
        T = np.array(v["T"][:], float)
        units = v["T"].units.decode() if isinstance(v["T"].units, bytes) else v["T"].units
        miss = getattr(v["prcp"], "missing_value", None)
    if miss is not None:
        P[P == float(np.asarray(miss).ravel()[0])] = np.nan
    P[P < 0] = np.nan
    if "julian" in units:            # IRI: día juliano astronómico; JD 2451545.0 = 2000-01-01 12:00
        days = pd.Timestamp("2000-01-01") + pd.to_timedelta(np.floor(T - 2451545.0), unit="D")
    else:
        base = pd.Timestamp(units.split("since")[1].strip().split(" ")[0])
        days = base + pd.to_timedelta(np.floor(T), unit="D")
    if P.shape[1:] != (lat.size, lon.size):
        P = P.transpose(0, 2, 1)
    return days, P, lat, lon


def daily_gldas(cells: list[str], years: list[int]) -> pd.DataFrame:
    parts = []
    for y in years:
        days, P, lat, lon = read_year(CHIRPS_D / f"chirps_v2p0_diario_RD_{y}.nc")
        cols = {}
        for c in cells:
            la, lo = map(float, c.split("_"))
            mi = np.abs(lat - la) < 0.125
            mj = np.abs(lon - lo) < 0.125
            with np.errstate(invalid="ignore"):
                cols[c] = np.nanmean(P[:, mi][:, :, mj].reshape(P.shape[0], -1), axis=1)
        parts.append(pd.DataFrame(cols, index=days))
    return pd.concat(parts).sort_index()


def factors(ep: pd.DataFrame, daily: pd.DataFrame, pentad: bool = False) -> pd.DataFrame:
    out = ep.copy()
    fr, mx = [], []
    thr = {}
    for c in daily:
        s = daily[c].dropna()
        if pentad:
            s = s.resample("5D").sum(min_count=5)
        thr[c] = episodes.heavy_threshold(s, 0.95, 1.0 if not pentad else 5.0)
    for _, e in ep.iterrows():
        if pd.isna(e["retorno_lluvia"]) or e["celda"] not in daily:
            fr.append(np.nan)
            mx.append(np.nan)
            continue
        w0 = e["fin"] + pd.offsets.MonthBegin(1)
        w1 = e["retorno_lluvia"] + pd.DateOffset(months=2) + pd.offsets.MonthEnd(0)
        dw = daily[e["celda"]][(daily.index >= w0) & (daily.index <= w1)]
        if dw.isna().any() or len(dw) < (w1 - w0).days * 0.9:
            fr.append(np.nan)
            mx.append(np.nan)
            continue
        if pentad:
            dw = dw.resample("5D", origin=w0).sum(min_count=5).dropna()
        tot = dw.sum()
        fr.append(float(dw[dw > thr[e["celda"]]].sum() / tot) if tot > 0 else np.nan)
        mx.append(float(dw.max()) if len(dw) else np.nan)
    out["fraccion_intensa_chirps"] = fr
    out["max_chirps_mm"] = mx
    return out


def run(N, status: dict, B: int = 2000) -> dict:
    years = status["anios_completos"]
    ep = pd.read_csv(RES_NAC / "episodios.csv", parse_dates=["inicio", "fin", "retorno_lluvia"])
    ep["contradiccion_A_SM_RAIZ"] = ep["contradiccion_A_SM_RAIZ"].map({True: 1.0, False: 0.0, "True": 1.0, "False": 0.0})
    cells = sorted(ep["celda"].unique())
    daily = daily_gldas(cells, years)
    rows = []
    for scale, pent in (("diario", False), ("péntada", True)):
        f = factors(ep, daily, pentad=pent)
        ok = f["fraccion_intensa_chirps"].notna() & f["fraccion_lluvia_intensa"].notna()
        sub = f[ok]
        for oc in OUTCOMES:
            for lab, col, src in (("fracción en días/péntadas intensas", "fraccion_intensa_chirps", f"CHIRPS {scale}"),
                                  ("máximo en 1 día / 5 días", "max_chirps_mm", f"CHIRPS {scale}"),
                                  ("fracción en días intensos", "fraccion_lluvia_intensa", "IMERG diario (mismos episodios)"),
                                  ("máximo en 1 día", "lluvia_max_1dia_mm", "IMERG diario (mismos episodios)")):
                if src.startswith("IMERG") and pent:
                    continue
                a = episodes.association(sub, oc, col, B=B)
                rows.append({"resultado": oc, "factor": lab, "fuente": src, **a})
    df = pd.DataFrame(rows)
    from ..hr.common import bh_fdr
    df["q_bh"] = bh_fdr(df["p"].astype(float).to_numpy())
    df.assign(ic95=df["ic95"].map(lambda v: None if v is None else [round(x, 4) for x in v])) \
        .to_csv(__import__("earthmemory.testigos.common", fromlist=["RES"]).RES / "intensidad_chirps.csv",
                index=False, float_format="%.5g")
    # concordancia de los factores entre productos
    f = factors(ep, daily)
    m = f[["fraccion_intensa_chirps", "fraccion_lluvia_intensa"]].dropna()
    m2 = f[["max_chirps_mm", "lluvia_max_1dia_mm"]].dropna()
    return {"estado": "ok", "anios_chirps_usados": years, "periodo": [f"{min(years)}-01-01", f"{max(years)}-12-31"],
            "n_episodios_con_ventana_completa": int(len(m)),
            "r_spearman_fraccion_chirps_vs_imerg": float(m.corr("spearman").iloc[0, 1]) if len(m) > 5 else None,
            "r_spearman_max_chirps_vs_imerg": float(m2.corr("spearman").iloc[0, 1]) if len(m2) > 5 else None,
            "tabla": df.to_dict(orient="records"),
            "nota": "CHIRPS v2 diario reparte el total de la péntada entre sus días con un modelo: el factor diario no "
                    "es una observación diaria independiente; la versión por péntadas es la escala anclada a estaciones."}
