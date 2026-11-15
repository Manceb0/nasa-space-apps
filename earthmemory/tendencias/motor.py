"""Cálculo: índices por celda → series de provincia → tendencias, FDR, clases, MDT y calibración con sustitutos."""

from __future__ import annotations

import zlib

import numpy as np
import pandas as pd

from . import datos
from . import estadistica as st
from . import indices as ix

PRODUCTS = {
    "IMERG": {"nombre": "IMERG V07 Final (NASA GPM)", "tipo_fuente": "recuperación satelital calibrada con pluviómetros",
              "resolucion_nativa": "0.1°", "cita": "Huffman, G.J. et al. (2023). GPM IMERG Final Precipitation L3 1 day "
              "0.1 degree x 0.1 degree V07. GES DISC. doi:10.5067/GPM/IMERGDF/DAY/07"},
    "CHIRPS": {"nombre": "CHIRPS v2.0 (CHC/UCSB)", "tipo_fuente": "satélite + estaciones",
               "resolucion_nativa": "0.05° (agregado a 0.1° para comparar)",
               "cita": "Funk, C. et al. (2015). Scientific Data 2, 150066. doi:10.1038/sdata.2015.66"},
}
NATIONAL = "República Dominicana"


def setup() -> dict:
    cells = datos.cells_table()
    ids = cells["celda"].to_numpy()
    w = datos.province_weights()
    in_w = np.isin(ids, w["celda"].unique())
    inc = cells["incluida"].fillna(False).astype(bool).to_numpy()
    mask = in_w | inc                                   # celdas con las que se calcula algo
    an_ids = ids[mask]
    provs = sorted(w["provincia"].unique())
    codes = w.drop_duplicates("provincia").set_index("provincia")["codigo"]
    col = {c: k for k, c in enumerate(an_ids)}
    W = np.zeros((len(provs) + 1, an_ids.size))
    for k, p in enumerate(provs):
        g = w[w["provincia"] == p]
        W[k, [col[c] for c in g["celda"]]] = g["peso"].to_numpy()
    nat = w.groupby("celda")["peso"].sum()
    W[-1, [col[c] for c in nat.index]] = nat.to_numpy()
    regions = provs + [NATIONAL]
    return {"cells": cells.loc[mask].reset_index(drop=True), "mask": mask, "inc": inc[mask], "W": W,
            "regions": regions, "codes": [codes[p] for p in provs] + ["DO"]}


def product_indices(X: np.ndarray) -> dict:
    """{(índice, periodo): (años, años × celdas)} para un producto (X: días × celdas)."""
    thr = ix.wet_percentiles(X)
    out = ix.daily_indices(X, datos.DAYS, thr, datos.YEARS)
    months, M = ix.monthly_totals(X, datos.DAYS)
    for scale in (3, 12):
        S = ix.spi(M, months, scale)
        for k, v in ix.drought_metrics(S, months).items():
            out[(f"SPI{scale}_{k}", "anual")] = v
    out["_umbrales"] = thr
    out["_spi3"] = (months, ix.spi(M, months, 3))
    return out


def region_mean(A: np.ndarray, W: np.ndarray) -> np.ndarray:
    """Media ponderada por área (años × celdas) → (años × regiones), ignorando celdas sin dato."""
    ok = np.isfinite(A)
    num = np.where(ok, A, 0) @ W.T
    den = ok.astype(float) @ W.T
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(den > 0, num / den, np.nan)


def _stats_frame(Y: np.ndarray, years: np.ndarray, do_fdr: np.ndarray) -> pd.DataFrame:
    r = st.trend_rows(Y, years.astype(float))
    df = pd.DataFrame({k: r[k] for k in ("n", "media", "pendiente_decada", "ic95_inf", "ic95_sup", "S", "Z", "p",
                                         "p_sin_correccion", "factor_hr", "sigma_res", "r1", "signo", "constante")})
    df["mdt"] = st.mdt_decade(r)
    q = np.full(len(df), np.nan)
    sel = do_fdr & np.isfinite(df["p"].to_numpy())
    q[sel] = st.fdr(df["p"].to_numpy()[sel])
    df["q_fdr"] = q
    df["sig_fdr"] = df["q_fdr"] <= st.ALPHA_FDR
    with np.errstate(invalid="ignore", divide="ignore"):
        df["pendiente_pct_decada"] = 100 * df["pendiente_decada"] / df["media"].where(df["media"].abs() > 0)
    df["detectable"] = df["pendiente_decada"].abs() >= df["mdt"]
    return df


def run_all(series: dict, S: dict, n_surr: int = 300, log=print) -> dict:
    """series: {producto: {(índice, periodo): (años, años × celdas)}}."""
    keys = [k for k in series["IMERG"] if not (isinstance(k, str) and k.startswith("_"))]
    prods = [p for p in PRODUCTS if p in series]
    cell_rows, reg_rows, reg_series = [], [], []
    cells = S["cells"]
    inc = S["inc"]
    nreg = len(S["regions"])
    is_prov = np.arange(nreg) < nreg - 1
    for key in keys:
        idx, per = key
        frames_c, frames_r = {}, {}
        for prod in prods:
            years, A = series[prod][key]
            # celdas (solo las incluidas)
            Yc = A[:, inc].T
            dfc = _stats_frame(Yc, years, np.ones(Yc.shape[0], bool))
            dfc.insert(0, "celda", cells.loc[inc, "celda"].to_numpy())
            frames_c[prod] = dfc
            # provincias + nacional (FDR solo entre las 32 provincias)
            R = region_mean(A, S["W"])
            dfr = _stats_frame(R.T, years, is_prov)
            dfr.insert(0, "region", S["regions"])
            dfr.insert(1, "codigo", S["codes"])
            frames_r[prod] = dfr
            for k, reg in enumerate(S["regions"]):
                for y, v in zip(years, R[:, k]):
                    reg_series.append((reg, idx, per, prod, int(y), v))
        for frames, rows in ((frames_c, cell_rows), (frames_r, reg_rows)):
            if len(prods) == 2:
                a, b = frames["IMERG"], frames["CHIRPS"]
                sa, sb = a["sig_fdr"].to_numpy(bool), b["sig_fdr"].to_numpy(bool)
                if "region" in a:  # la serie nacional es una sola prueba: p < 0.05 sin FDR
                    nat = (a["region"] == NATIONAL).to_numpy()
                    sa = sa | (nat & (a["p"] < st.ALPHA).to_numpy())
                    sb = sb | (nat & (b["p"] < st.ALPHA).to_numpy())
                cls = st.confidence_class(sa, sb,
                                          a["signo"].to_numpy(float), b["signo"].to_numpy(float))
            else:
                cls = np.full(len(frames[prods[0]]), "un solo producto", dtype=object)
            for prod in prods:
                f = frames[prod].copy()
                f.insert(1 if "celda" in f else 2, "indice", idx)
                f.insert(2 if "celda" in f else 3, "periodo", per)
                f["fuente"] = prod
                f["tipo_fuente"] = PRODUCTS[prod]["tipo_fuente"]
                f["clase_confianza"] = cls
                rows.append(f)
        log(f"[tendencias] {idx:<14s} {per:<16s} celdas sig. IMERG={int(frames_c['IMERG']['sig_fdr'].sum())}"
            + (f" CHIRPS={int(frames_c['CHIRPS']['sig_fdr'].sum())}" if "CHIRPS" in frames_c else ""))
    tc = pd.concat(cell_rows, ignore_index=True)
    tc = tc.merge(cells[["celda", "lat", "lon", "provincia_principal"]], on="celda", how="left")
    tr = pd.concat(reg_rows, ignore_index=True)
    sr = pd.DataFrame(reg_series, columns=["region", "indice", "periodo", "fuente", "anio", "valor"])
    return {"celdas": tc, "regiones": tr, "series_regiones": sr}


def calibration(series: dict, S: dict, n_surr: int = 300, log=print) -> pd.DataFrame:
    rows = []
    for prod in series:
        for key, val in series[prod].items():
            if isinstance(key, str) or key[1] != "anual" or key[0].endswith("DURAC"):
                continue
            years, A = val
            for nivel, Y in (("celdas", A[:, S["inc"]]), ("provincias", region_mean(A, S["W"])[:, :-1])):
                for method in ("fase", "bloques"):
                    r = st.calibrate(Y, years.astype(float), n_surr=n_surr, method=method,
                                     seed=zlib.crc32(f"{prod}|{key[0]}|{nivel}|{method}".encode()))
                    rows.append({"fuente": prod, "indice": key[0], "periodo": "anual", "nivel": nivel, **r})
            log(f"[calibracion] {prod} {key[0]}: FPR local fase={rows[-4]['fpr_local_p05']:.3f} "
                f"bloques={rows[-3]['fpr_local_p05']:.3f}")
    df = pd.DataFrame(rows)
    df["fpr_local_p05_ic95"] = df["fpr_local_p05_ic95"].map(lambda v: f"{v[0]:.3f}-{v[1]:.3f}")
    return df


def summary(tc: pd.DataFrame, tr: pd.DataFrame, cal: pd.DataFrame | None) -> pd.DataFrame:
    rows = []
    for (idx, per, prod), g in tc.groupby(["indice", "periodo", "fuente"], sort=False):
        gp = tr[(tr["indice"] == idx) & (tr["periodo"] == per) & (tr["fuente"] == prod)]
        prov = gp[gp["region"] != NATIONAL]
        nat = gp[gp["region"] == NATIONAL].iloc[0]
        row = {"indice": idx, "periodo": per, "fuente": prod, "celdas": int(g["p"].notna().sum()),
               "celdas_sig_fdr": int(g["sig_fdr"].sum()),
               "celdas_sig_fdr_aumento": int((g["sig_fdr"] & (g["signo"] > 0)).sum()),
               "celdas_sig_fdr_descenso": int((g["sig_fdr"] & (g["signo"] < 0)).sum()),
               "celdas_p05_sin_fdr": int((g["p"] < 0.05).sum()),
               "campo_significativo_wilks": bool(st.field_significance_wilks(g["q_fdr"].to_numpy())),
               "mediana_pendiente_decada": float(g["pendiente_decada"].median()),
               "mediana_mdt": float(g["mdt"].median()),
               "celdas_pendiente_mayor_mdt": int(g["detectable"].sum()),
               "provincias_sig_fdr": int(prov["sig_fdr"].sum()),
               "nacional_pendiente_decada": float(nat["pendiente_decada"]), "nacional_ic95_inf": float(nat["ic95_inf"]),
               "nacional_ic95_sup": float(nat["ic95_sup"]), "nacional_p": float(nat["p"]), "nacional_mdt": float(nat["mdt"]),
               "nacional_media": float(nat["media"])}
        for c in st.CLASSES:
            row[f"celdas_{c.replace(' ', '_').replace('ñ', 'n')}"] = int((g["clase_confianza"] == c).sum())
            row[f"provincias_{c.replace(' ', '_').replace('ñ', 'n')}"] = int((prov["clase_confianza"] == c).sum())
        row["celdas_robusta_aumento"] = int(((g["clase_confianza"] == "robusta") & (g["signo"] > 0)).sum())
        row["celdas_robusta_descenso"] = int(((g["clase_confianza"] == "robusta") & (g["signo"] < 0)).sum())
        row["clase_nacional"] = nat["clase_confianza"]
        if cal is not None and per == "anual":
            c = cal[(cal["indice"] == idx) & (cal["fuente"] == prod) & (cal["nivel"] == "celdas")]
            for _, cr in c.iterrows():
                tag = "fase" if cr["metodo"].startswith("fases") else "bloques"
                row[f"p_campo_{tag}"] = cr["p_campo_bootstrap"]
                row[f"fpr_{tag}"] = cr["fpr_local_p05"]
            if len(c):
                row["prueba_liberal"] = bool(max(row.get("fpr_fase", 0.0), row.get("fpr_bloques", 0.0)) > 0.075)
        rows.append(row)
    return pd.DataFrame(rows)
