"""Motor de testigos e hipótesis: pone a prueba las afirmaciones de Earth Memory con datos independientes.

    docker compose run --rm testigos                         # descarga lo que falte y corre todo
    docker compose run --rm testigos --sin-descarga          # solo con la caché de data/testigos
    docker compose run --rm testigos --pasos pares memoria   # solo algunos pasos

Pasos: datos → calidad SMAP L3 → pares → memoria (lluvia vs suelo) → umbral → bosque → intensidad (CHIRPS) →
figuras → informe → cuaderno 09. Cada paso escribe en results/testigos/ (JSON/CSV); las figuras y el informe solo
leen esos archivos. Semilla fija (2026).
"""

from __future__ import annotations

import argparse
import json
import pickle
import time
from pathlib import Path

import numpy as np
import pandas as pd

from .. import anomalies, calibration, contrasts, coupling
from ..grid import cell_id
from ..hr import pair as hrpair
from . import bosque, memoria, pares, smap_l3, umbral
from .common import (BBOX, CHIRPS_D, DATA, NAC_HR, PAR_GLDAS, PAR_HR, RES, RES_HR, RES_NAC, SEED, YUNA_ALTO,
                     write_json)

CACHE_NAC = DATA / "derivados" / "nacional_imerg_gldas.pkl"
P15 = ("2015-04-01", "2024-12-31")


def log(msg):
    print(f"[testigos {time.strftime('%H:%M:%S')}] {msg}", flush=True)


# ------------------------------------------------------------------ datos de base (solo lectura)

def national() -> dict:
    if CACHE_NAC.exists():
        return pickle.loads(CACHE_NAC.read_bytes())
    from .. import nacional, region
    a = argparse.Namespace(datos=str(Path("data/nacional")), pais="DOM", anio0=2001, anio1=2024,
                           min_frac=region.MIN_FRAC, appeears="data/appeears/nacional")
    D = nacional.load(a)
    keep = {k: D[k] for k in ("P_gl", "D_im", "D_gl", "P_mod", "cells_gl", "P_im")}
    keep["GL"] = {k: D["GL"][k] for k in ("SM_RAIZ", "SM_0_10")}
    CACHE_NAC.parent.mkdir(parents=True, exist_ok=True)
    CACHE_NAC.write_bytes(pickle.dumps(keep))
    return keep


def hr_grid() -> dict:
    z = np.load(NAC_HR / "derivados" / "rejilla_005.npz", allow_pickle=False)
    n = np.load(NAC_HR / "derivados" / "nativas.npz", allow_pickle=False)
    out = {k: z[k] for k in ("frac_rd", "prov", "P_chirps", "meses", "lat", "lon", "tc_soil", "dem_elev_m",
                             "dem_pendiente_grados", "lc_bosque", "smap_idx")}
    out.update({k: n[k] for k in ("smap_sm_rootzone", "smap_meses", "smap_lat", "smap_lon")})
    out["meses"] = np.array([m[:7] for m in out["meses"]], dtype="datetime64[M]")
    out["smap_meses"] = np.array([m[:7] for m in out["smap_meses"]], dtype="datetime64[M]")
    return out


def imerg_col(D_im: pd.DataFrame, lat: float, lon: float) -> str:
    la = np.floor(lat * 10) / 10 + 0.05
    lo = np.floor(lon * 10) / 10 + 0.05
    c = cell_id(la, lo)
    if c not in D_im:
        raise KeyError(c)
    return c


# ------------------------------------------------------------------ 1. calidad SMAP L3

def step_calidad(S, land) -> dict:
    q = smap_l3.quality_table(S, land)
    q.to_csv(RES / "smap_l3_calidad_pixeles.csv", index=False, float_format="%.4g")
    ql = q[q["tierra_rd"]]
    out = {"n_pixeles_caja": int(len(q)), "n_pixeles_tierra_rd": int(len(ql)),
           "dias": [str(S["dias"][0]), str(S["dias"][-1])], "n_dias": int(S["dias"].size),
           "frac_recomendado_mediana_tierra": float(ql["frac_recomendado_am_pm"].median()),
           "frac_recomendado_de_intentados_mediana_am": float(ql["frac_recomendado_de_intentados_am"].median()),
           "pixeles_tierra_sin_ningun_recomendado": int((ql["frac_recomendado_am_pm"] == 0).sum()),
           "pixeles_tierra_menos_10pct_recomendado": int((ql["frac_recomendado_am_pm"] < 0.10).sum()),
           "vwc_mediana_tierra": float(ql["vwc_mediana_am"].median()), "puntos": {}}
    pts = {"GLDAS_A": PAR_GLDAS["A"], "GLDAS_B": PAR_GLDAS["B"], "HR_A": PAR_HR["A"], "HR_B": PAR_HR["B"]}
    for k, p in pts.items():
        if p["res"] == 0.25:
            m = (np.abs(q["lat"] - p["lat"]) <= 0.125) & (np.abs(q["lon"] - p["lon"]) <= 0.125) & q["tierra_rd"]
            sub = q[m]
        else:
            i, j = smap_l3.nearest_pixel(S, p["lat"], p["lon"])
            sub = q[(q["fila"] == i) & (q["col"] == j)]
        out["puntos"][k] = {"nombre": p["nombre"], "n_pixeles_9km": int(len(sub)),
                            **{c: float(sub[c].mean()) for c in
                               ("frac_dias_con_dato_am", "frac_exito_am", "frac_recomendado_am", "frac_recomendado_pm",
                                "frac_recomendado_am_pm", "frac_recomendado_de_intentados_am", "vwc_mediana_am",
                                "frac_vwc_mayor_5_am", "bandera_montana_am", "bandera_vegetacion_densa_am",
                                "bandera_costa_am", "bandera_urbano_am")}}
    write_json(RES / "smap_l3_calidad_resumen.json", out)
    return out


# ------------------------------------------------------------------ 2. pares

def _arx_test(zdf: pd.DataFrame, spi: dict, a: str, b: str, period, n_surr: int, label: str) -> dict:
    nA, nB = int(zdf[a].notna().sum()), int(zdf[b].notna().sum())
    if min(nA, nB) < 40:
        return {"etiqueta": label, "metrica": "gamma ARX (z mensual ~ SPI-1)", "no_comprobable": True,
                "n_A": nA, "n_B": nB, "motivo": "menos de 40 meses con dato de calidad"}
    st = coupling.Settings(B=2000, period=period)
    z = {"R": zdf}
    sp = {k: v[[a, b]] for k, v in spi.items()}
    cm = coupling.compute(z, sp, [a, b], ["R"], st)
    d = contrasts.pair_delta(cm, a, b, "R", "gamma")
    null = calibration.pair_null(z, sp, [(a, b)], ["R"], st, n_surr=n_surr, B=400, seed=SEED)
    t = pd.DataFrame([{"respuesta": "R", "metrica": "gamma", **d}])
    pc = float(calibration.calibrated_p(t, null).iloc[0])
    sig = calibration.inflation(null)[("R", "gamma")]
    g = null[null["metrica"] == "gamma"]
    return {"etiqueta": label, "metrica": "gamma ARX (z mensual ~ SPI-1)", "n_meses": int(len(cm.dates)),
            "gamma_A": d["valor_a"], "gamma_B": d["valor_b"], "delta": d["delta"],
            "delta_ic95": [d["ic95_bajo"], d["ic95_alto"]], "p_bootstrap": d["p"], "sigma_inflacion": sig,
            "tasa_p05_nulo": float((g["p"] < 0.05).mean()), "p_calibrado": pc}


def _eff(A: pares.Serie, B: pares.Serie, label: str, metric: str, n_sur: int) -> dict:
    nmin = 60 if "evento" in metric else 40
    if min(A.ok().n, B.ok().n) < nmin:
        return {"etiqueta": label, "metrica": metric, "no_comprobable": True, "n_A": A.ok().n, "n_B": B.ok().n,
                "motivo": f"menos de {nmin} {'eventos' if nmin == 60 else 'meses'} con dato de calidad"}
    r = pares.test_pair(A, B, n_boot=999, L=3, seed=SEED)
    s = pares.surrogates(A, B, n_sur=n_sur, n_boot=199, L=3, seed=SEED)
    r.update({"etiqueta": label, "metrica": metric, "tasa_p05_nulo": s["tasa_p05"],
              "sigma_inflacion": s["sigma_inflacion"], "p_calibrado": pares.calibrated_p(r["z"], s["sigma_inflacion"])})
    return r


def _cell_series(S, land, X, p, res):
    if res == 0.25:
        m = (np.abs(S["lat"] - p["lat"]) <= res / 2) & (np.abs(S["lon"] - p["lon"]) <= res / 2) & land
        frac = np.isfinite(X[:, m]).mean(1)
        with np.errstate(invalid="ignore"):
            v = np.nanmean(X[:, m], axis=1)
        return np.where(frac >= 0.5, v, np.nan), int(m.sum())
    i, j = smap_l3.nearest_pixel(S, p["lat"], p["lon"])
    return X[:, i, j], 1


def step_pares(N, H, S, land, n_sur: int) -> dict:
    out = {}
    tt, Xr = smap_l3.daily_merged(S, "recomendado")
    _, Xa = smap_l3.daily_merged(S, "exito")
    mo_r, Mr, Nr = smap_l3.monthly(S, "recomendado")
    mo_a, Ma, _ = smap_l3.monthly(S, "exito")
    days = N["D_im"].index.values.astype("datetime64[D]")
    sel15 = lambda df: df.loc[P15[0]:P15[1]]  # noqa: E731

    # ---- par GLDAS (Monseñor Nouel vs Santiago/La Vega)
    a, b = PAR_GLDAS["A"]["celda"], PAR_GLDAS["B"]["celda"]
    P = N["P_gl"]
    spi = {k: anomalies.spi_table(P, k) for k in (1, 3)}
    rows = []
    orig = pd.read_csv(RES_NAC / "contrastes_ranking.csv")
    o = orig[(orig.celda_a == a) & (orig.celda_b == b) & (orig.respuesta == "SM_RAIZ") & (orig.metrica == "gamma")].iloc[0]
    rows.append({"etiqueta": "GLDAS raíz 0-100 cm · 2001-2024 (afirmación original)", "independiente": "no (modelo)",
                 "metrica": "gamma ARX", "gamma_A": o.valor_a, "gamma_B": o.valor_b, "delta": o.delta,
                 "delta_ic95": [o.ic95_bajo, o.ic95_alto], "p_calibrado": o.p_calibrado, "q_calibrado": o.q_bh_calibrado})
    for resp, lab in (("SM_RAIZ", "GLDAS raíz 0-100 cm"), ("SM_0_10", "GLDAS superficie 0-10 cm")):
        zz = anomalies.zscore(N["GL"][resp][[a, b]], "robusta").loc["2015-04-01":]
        r = _arx_test(zz, spi, a, b, (2015, 2024), n_sur, f"{lab} · 2015-2024 (mismo periodo que SMAP)")
        r["independiente"] = "no (modelo)"
        rows.append(r)
    sm_cells, npx = {}, {}
    for key, X in (("rec", Mr), ("exito", Ma)):
        cols = {}
        for k, c in (("A", a), ("B", b)):
            v, n = _cell_series(S, land, X, PAR_GLDAS[k], 0.25)
            cols[c] = v
            npx[k] = n
        sm_cells[key] = pd.DataFrame(cols, index=pd.DatetimeIndex(mo_r.astype("datetime64[ns]")))
    for key, lab in (("rec", "SMAP L3 superficie · calidad recomendada"), ("exito", "SMAP L3 · todos los retrievals (sensibilidad)")):
        zz = anomalies.zscore(sm_cells[key], "robusta")
        r = _arx_test(zz, spi, a, b, (2015, 2024), n_sur, lab + " · gamma mensual")
        r["independiente"] = "sí (radiómetro)" if key == "rec" else "sí, pero con retrievals no recomendados"
        rows.append(r)
    # eficiencia mensual (misma métrica que el par de alta resolución) e IMERG
    Pm = sel15(P)
    mm = Pm.index.values.astype("datetime64[M]")
    gl15 = sel15(N["GL"]["SM_0_10"])
    eff_rows = [_eff(pares.monthly_series(gl15[a].to_numpy(), Pm[a].to_numpy(), mm),
                     pares.monthly_series(gl15[b].to_numpy(), Pm[b].to_numpy(), mm),
                     "GLDAS superficie 0-10 cm · 2015-2024", "eficiencia mensual (mm por mm de anomalía IMERG)", n_sur)]
    eff_rows[-1]["independiente"] = "no (modelo)"
    smr = sm_cells["rec"].reindex(Pm.index)
    eff_rows.append(_eff(pares.monthly_series(smr[a].to_numpy(), Pm[a].to_numpy(), mm),
                         pares.monthly_series(smr[b].to_numpy(), Pm[b].to_numpy(), mm),
                         "SMAP L3 superficie · calidad recomendada", "eficiencia mensual (m³/m³ por mm de anomalía IMERG)", n_sur))
    eff_rows[-1]["independiente"] = "sí (radiómetro)"
    ev = {}
    for mode, X in (("rec", Xr), ("exito", Xa)):
        ser = {}
        for k, c in (("A", a), ("B", b)):
            v, _ = _cell_series(S, land, X, PAR_GLDAS[k], 0.25)
            ser[k] = pares.event_series(tt, v, days, N["D_gl"][c].to_numpy(float))
        lab = "SMAP L3 · calidad recomendada" if mode == "rec" else "SMAP L3 · todos los retrievals (sensibilidad)"
        eff_rows.append(_eff(ser["A"], ser["B"], lab, "eficiencia por evento (m³/m³ por mm IMERG entre pasos)", n_sur))
        eff_rows[-1]["independiente"] = "sí (radiómetro)" if mode == "rec" else "sí, pero con retrievals no recomendados"
        ev[mode] = ser
    out["gldas"] = {"A": PAR_GLDAS["A"], "B": PAR_GLDAS["B"], "pixeles_9km": npx, "gamma": rows, "eficiencia": eff_rows,
                    "eventos_rec": {k: {"x": s.x.tolist(), "y": s.y.tolist()} for k, s in ev["rec"].items()},
                    "eventos_exito": {k: {"x": s.x.tolist(), "y": s.y.tolist()} for k, s in ev["exito"].items()}}

    # ---- par de alta resolución (Cordillera Central vs La Vega)
    resumen = json.loads((RES_HR / "resumen.json").read_text(encoding="utf-8"))
    par = resumen["par"]
    ij = {}
    for k in ("A", "B"):
        i = int(np.argmin(np.abs(H["lat"] - PAR_HR[k]["lat"])))
        j = int(np.argmin(np.abs(H["lon"] - PAR_HR[k]["lon"])))
        ij[k] = (i, j)
    e_full = {k: pares.slope(pares.monthly_series(H["tc_soil"][:, i, j], H["P_chirps"][:, i, j], H["meses"]).ok())
              for k, (i, j) in ij.items()}
    hr_rows = [{"etiqueta": "TerraClimate · 2001-2024 (afirmación original)", "independiente": "no (modelo de cubo, ERA5)",
                "metrica": "eficiencia mensual (mm por mm de anomalía CHIRPS)", "e_A": e_full["A"], "e_B": e_full["B"],
                "delta": par["delta"], "delta_ic95": par["ic95_delta"], "p": par["p"], "q": par["q"]},
               {"etiqueta": "SMAP L4 zona de raíces · 2015-2024 (afirmación original)",
                "independiente": "no (modelo Catchment; forzante de lluvia corregido con IMERG Final desde la v6)",
                "metrica": "eficiencia mensual", "e_A": par["smap"]["e_A"], "e_B": par["smap"]["e_B"],
                "delta": par["smap"]["delta"], "p": par["smap"]["p"]}]
    hm = H["meses"]
    s15 = (hm >= np.datetime64("2015-04")) & (hm <= np.datetime64("2024-12"))
    PA_ = {k: H["P_chirps"][:, i, j] for k, (i, j) in ij.items()}
    TC_ = {k: H["tc_soil"][:, i, j] for k, (i, j) in ij.items()}
    hr_rows.append(_eff(pares.monthly_series(TC_["A"][s15], PA_["A"][s15], hm[s15]),
                        pares.monthly_series(TC_["B"][s15], PA_["B"][s15], hm[s15]),
                        "TerraClimate · 2015-2024 (mismo periodo que SMAP)", "eficiencia mensual (mm por mm de anomalía CHIRPS)", n_sur))
    hr_rows[-1]["independiente"] = "no (modelo de cubo, ERA5)"
    pix = {k: smap_l3.nearest_pixel(S, PAR_HR[k]["lat"], PAR_HR[k]["lon"]) for k in ("A", "B")}
    sm_m = {}
    for key, M in (("rec", Mr), ("exito", Ma)):
        sm_m[key] = {k: pd.Series(M[:, i, j], index=mo_r) for k, (i, j) in pix.items()}
    chirps_s = {k: pd.Series(PA_[k], index=hm) for k in ("A", "B")}
    common = mo_r[(mo_r >= np.datetime64("2015-04")) & (mo_r <= hm[-1])]
    for key, lab, ind in (("rec", "SMAP L3 superficie · calidad recomendada", "sí (radiómetro)"),
                          ("exito", "SMAP L3 · todos los retrievals (sensibilidad)", "sí, pero con retrievals no recomendados")):
        ss = [pares.monthly_series(sm_m[key][k].reindex(common).to_numpy(), chirps_s[k].reindex(common).to_numpy(), common)
              for k in ("A", "B")]
        if min(s.ok().n for s in ss) < 40:
            hr_rows.append({"etiqueta": lab, "independiente": ind, "metrica": "eficiencia mensual",
                            "no_comprobable": True, "n_A": ss[0].ok().n, "n_B": ss[1].ok().n})
            continue
        hr_rows.append(_eff(ss[0], ss[1], lab, "eficiencia mensual (m³/m³ por mm de anomalía CHIRPS)", n_sur))
        hr_rows[-1]["independiente"] = ind
    hr_ev = {}
    for mode, X in (("rec", Xr), ("exito", Xa)):
        ser = {}
        for k in ("A", "B"):
            i, j = pix[k]
            col = imerg_col(N["D_im"], PAR_HR[k]["lat"], PAR_HR[k]["lon"])
            ser[k] = pares.event_series(tt, X[:, i, j], days, N["D_im"][col].to_numpy(float))
        lab = "SMAP L3 · calidad recomendada" if mode == "rec" else "SMAP L3 · todos los retrievals (sensibilidad)"
        ind = "sí (radiómetro)" if mode == "rec" else "sí, pero con retrievals no recomendados"
        if min(s.ok().n for s in ser.values()) < 60:
            hr_rows.append({"etiqueta": lab, "independiente": ind, "metrica": "eficiencia por evento",
                            "no_comprobable": True, "n_A": ser["A"].ok().n, "n_B": ser["B"].ok().n})
        else:
            hr_rows.append(_eff(ser["A"], ser["B"], lab, "eficiencia por evento (m³/m³ por mm IMERG entre pasos)", n_sur))
            hr_rows[-1]["independiente"] = ind
        hr_ev[mode] = ser
    out["hr"] = {"A": PAR_HR["A"], "B": PAR_HR["B"], "pixeles_9km": {k: list(v) for k, v in pix.items()},
                 "pixeles_lat_lon": {k: [float(S["lat"][v]), float(S["lon"][v])] for k, v in pix.items()},
                 "eficiencia": hr_rows,
                 "eventos_rec": {k: {"x": s.x.tolist(), "y": s.y.tolist()} for k, s in hr_ev["rec"].items()},
                 "eventos_exito": {k: {"x": s.x.tolist(), "y": s.y.tolist()} for k, s in hr_ev["exito"].items()},
                 "meses_validos_rec": {k: int(np.isfinite(sm_m["rec"][k].reindex(common)).sum()) for k in ("A", "B")},
                 "meses_validos_exito": {k: int(np.isfinite(sm_m["exito"][k].reindex(common)).sum()) for k in ("A", "B")}}
    out["veredictos"] = {"gldas": verdict_pair(out["gldas"]["eficiencia"], out["gldas"]["gamma"], -1),
                         "hr": verdict_pair(hr_rows, [], -1)}
    write_json(RES / "pares_smap_l3.json", out)
    flat = []
    for par_, lst in (("GLDAS Monseñor Nouel vs Santiago/La Vega", out["gldas"]["gamma"] + out["gldas"]["eficiencia"]),
                      ("0.05° Cordillera Central vs La Vega", hr_rows)):
        for r in lst:
            flat.append({"par": par_, **{k: (json.dumps(v) if isinstance(v, list) else v) for k, v in r.items()}})
    pd.DataFrame(flat).to_csv(RES / "pares_smap_l3.csv", index=False, float_format="%.5g")
    return out


def verdict_pair(eff_rows: list, gamma_rows: list, sign: int) -> dict:
    """Veredicto con el testigo independiente (SMAP L3, calidad recomendada). Prueba principal = eficiencia por
    evento; secundarias = eficiencia mensual y gamma mensual."""
    def ok(r):
        if r.get("no_comprobable"):
            return "no comprobable"
        lo, hi = r["delta_ic95"]
        same = np.sign(r["delta"]) == sign
        excl = lo > 0 or hi < 0
        if same and excl and r["p_calibrado"] < 0.05:
            return "confirma"
        if not same and excl and r["p_calibrado"] < 0.05:
            return "contradice"
        return "no confirma"
    tests = {}
    for r in eff_rows + gamma_rows:
        if r.get("independiente") == "sí (radiómetro)":
            tests[f"{r['metrica'].split(' (')[0]}"] = ok(r)
    main = tests.get("eficiencia por evento", "no comprobable")
    if main == "confirma":
        v = "confirmado por una observación independiente"
    elif main == "no comprobable":
        v = "no comprobable"
    elif main == "contradice":
        v = "contradicho por la observación independiente"
    else:
        v = "no confirmado"
    return {"pruebas": tests, "veredicto": v}


# ------------------------------------------------------------------ 3. memoria de lluvia vs suelo

def terrain_gldas(H, cells: list[str]) -> pd.DataFrame:
    LO, LA = np.meshgrid(H["lon"], H["lat"])
    land = H["frac_rd"] >= 0.5
    rows = []
    for c in cells:
        la, lo = map(float, c.split("_"))
        m = (np.abs(LA - la) <= 0.125) & (np.abs(LO - lo) <= 0.125) & land
        rows.append({"celda": c, "elev_m": float(np.nanmean(H["dem_elev_m"][m])) if m.any() else np.nan,
                     "pendiente_grados": float(np.nanmean(H["dem_pendiente_grados"][m])) if m.any() else np.nan})
    return pd.DataFrame(rows)


def step_memoria(N, H, B: int) -> dict:
    ep = pd.read_csv(RES_NAC / "episodios.csv", parse_dates=["inicio", "fin", "retorno_lluvia"])
    cells = sorted(ep["celda"].unique())
    cg = pd.read_csv(RES_NAC / "celdas_gldas.csv").set_index("celda")
    ep["provincia"] = ep["celda"].map(cg["provincia_principal"])
    ep = ep.merge(terrain_gldas(H, cells), on="celda", how="left")
    ep["mes_inicio"] = ep["inicio"].dt.month
    ep["clave"] = ep["inicio"] - pd.DateOffset(months=1)
    D = N["D_gl"][cells]
    rain = {}
    for k in memoria.KS:
        for w in memoria.WINDOWS:
            rain[f"API IMERG diario k={k:.2f} W={w} d"] = memoria.month_end_api_z(D, k, w)
    Pm = N["P_gl"][cells]
    rain["API IMERG mensual k=0.90 W=90 d"] = memoria.z_by_month(pd.DataFrame(memoria.api_monthly(Pm.to_numpy(), 0.90, 90), index=Pm.index, columns=cells))
    Pf = N["P_mod"][cells]
    for k in memoria.KS:
        rain[f"API lluvia del forzante GLDAS (GPCP) k={k:.2f} W=90 d"] = memoria.z_by_month(
            pd.DataFrame(memoria.api_monthly(Pf.to_numpy(), k, 90), index=Pf.index, columns=cells))
    rain["SPI-3 IMERG (mes previo)"] = anomalies.spi_table(Pm, 3)
    # Memoria de lluvia más larga que 90 días (la zona de raíces integra meses): SPI-6/12 de IMERG y del forzante
    for k in (6, 12):
        rain[f"SPI-{k} IMERG (mes previo)"] = anomalies.spi_table(Pm, k)
        rain[f"SPI-{k} lluvia del forzante GLDAS (mes previo)"] = anomalies.spi_table(Pf, k)
    rain["SPI-3 lluvia del forzante GLDAS (mes previo)"] = anomalies.spi_table(Pf, 3)

    def lookup(tab, when, cell):
        try:
            return float(tab.at[pd.Timestamp(when), cell])
        except KeyError:
            return np.nan

    for name, tab in rain.items():
        ep[name] = [lookup(tab, w, c) for w, c in zip(ep["clave"], ep["celda"])]
    ret_name = "API IMERG diario k=0.90 W=90 d"
    ep["API al retorno (k=0.90 W=90 d)"] = [lookup(rain[ret_name], (r.to_period("M").to_timestamp() if pd.notna(r) else pd.NaT), c)
                                             for r, c in zip(ep["retorno_lluvia"], ep["celda"])]
    specs = [(n, [n]) for n in rain] + [
        ("API inicio + API al retorno (k=0.90 W=90 d)", [ret_name, "API al retorno (k=0.90 W=90 d)"]),
        ("SPI-3 + SPI-6 + SPI-12 IMERG", ["SPI-3 IMERG (mes previo)", "SPI-6 IMERG (mes previo)", "SPI-12 IMERG (mes previo)"]),
        ("SPI-3 + SPI-6 + SPI-12 forzante GLDAS", ["SPI-3 lluvia del forzante GLDAS (mes previo)",
                                                   "SPI-6 lluvia del forzante GLDAS (mes previo)",
                                                   "SPI-12 lluvia del forzante GLDAS (mes previo)"])]
    fes = {"mes + provincia + terreno": (["severidad", "elev_m", "pendiente_grados"], ["mes_inicio", "provincia"]),
           "mes + celda": (["severidad"], ["mes_inicio", "celda"])}
    outcomes = [("z_retorno_SM_RAIZ", "SM_RAIZ"), ("z_retorno_SM_0_10", "SM_0_10"), ("contradiccion_A_SM_RAIZ", "SM_RAIZ")]
    ep["contradiccion_A_SM_RAIZ"] = ep["contradiccion_A_SM_RAIZ"].map({True: 1.0, False: 0.0, "True": 1.0, "False": 0.0})
    rows = []
    # reproducción de la afirmación original (solo severidad, sin EF): β del suelo ≈ 0.46
    for oc, resp in outcomes:
        soil = f"z_antecedente_{resp}"
        for sname, rcols in specs:
            for fname, (base, fe) in fes.items():
                d = ep[list(dict.fromkeys([oc, soil, *rcols, *base, *fe, "anio_cluster", "celda"]))].dropna()
                bb = B if oc == "z_retorno_SM_RAIZ" else max(300, B // 3)
                r = memoria.nested_boot(d, oc, base, fe, rcols, soil, B=bb, seed=SEED)
                rows.append({"resultado": oc, "lluvia_antecedente": sname, "efectos_fijos": fname, **r})
        log(f"memoria: {oc} listo")
    df = pd.DataFrame(rows)
    df["q_beta_suelo_M3"] = memoria.fdr(df, "p_beta_suelo_M3")
    df["q_beta_lluvia_M3"] = memoria.fdr(df, "p_beta_lluvia_M3")
    orig = {}
    for oc, resp in outcomes:
        d = ep[[oc, f"z_antecedente_{resp}", "severidad", "anio_cluster", "celda"]].dropna()
        orig[oc] = memoria.nested_boot(d.assign(_c=0.0), oc, ["severidad"], [], ["_c"], f"z_antecedente_{resp}", B=500, seed=SEED)
    df["veredicto"] = [memoria.verdict(r, orig[r["resultado"]]["beta_suelo_M2"]) for _, r in df.iterrows()]
    out = df.copy()
    for c in out.columns:
        if out[c].map(lambda v: isinstance(v, list)).any():
            out[c] = out[c].map(json.dumps)
    out.to_csv(RES / "memoria_lluvia_vs_suelo.csv", index=False, float_format="%.5g")
    main = df[df["resultado"] == "z_retorno_SM_RAIZ"]
    res = {"n_episodios": int(len(ep)), "reproduccion_original": {k: {kk: v[kk] for kk in ("n", "beta_suelo_M2", "beta_suelo_M2_ic95", "p_beta_suelo_M2")}
                                                                 for k, v in orig.items()},
           "resumen_principal": {
               "n_especificaciones": int(len(main)),
               "beta_suelo_M3_rango": [float(main["beta_suelo_M3"].min()), float(main["beta_suelo_M3"].max())],
               "r2p_suelo_dado_lluvia_rango": [float(main["r2p_suelo_dado_lluvia"].min()), float(main["r2p_suelo_dado_lluvia"].max())],
               "r2p_lluvia_dado_suelo_rango": [float(main["r2p_lluvia_dado_suelo"].min()), float(main["r2p_lluvia_dado_suelo"].max())],
               "especificaciones_suelo_q05": int((main["q_beta_suelo_M3"] < 0.05).sum()),
               "especificaciones_lluvia_q05": int((main["q_beta_lluvia_M3"] < 0.05).sum()),
               "veredictos": main["veredicto"].value_counts().to_dict()},
           "correlaciones_suelo_api": {n: float(ep[["z_antecedente_SM_RAIZ", n]].dropna().corr().iloc[0, 1]) for n in rain}}
    write_json(RES / "memoria_lluvia_vs_suelo.json", res)
    ep.to_csv(RES / "episodios_con_api.csv", index=False, float_format="%.5g")
    return res


# ------------------------------------------------------------------ 4. umbral

def step_umbral(N, H, S, land, n_boot: int) -> dict:
    out = {}
    hm = H["meses"]
    L = (H["frac_rd"] >= 0.5) & np.isfinite(H["tc_soil"]).all(0) & np.isfinite(H["P_chirps"]).all(0)
    P2 = H["P_chirps"][:, L]
    S2 = H["tc_soil"][:, L]
    ok = (np.nanmax(S2, 0) - np.nanmin(S2, 0)) > 5.0
    P2, S2 = P2[:, ok], S2[:, ok]
    Y, PA, F, mo = umbral.build(S2, P2, hm)
    out["TerraClimate (cubo) · 2001-2024 · reconstrucción"] = umbral.pooled(Y, PA, F, mo, n_boot=n_boot)
    log("umbral: TC listo")
    s15 = (hm >= np.datetime64("2015-04")) & (hm <= np.datetime64("2024-12"))
    Y, PA, F, mo = umbral.build(S2[s15], P2[s15], hm[s15])
    out["TerraClimate (cubo) · 2015-2024"] = umbral.pooled(Y, PA, F, mo, n_boot=n_boot)
    # API (IMERG diario, k 0.90, 90 d) al final de cada mes, en la celda IMERG que contiene cada celda 0.05°
    D = N["D_im"]
    A = pd.DataFrame(memoria.api_window(D.to_numpy(float), 0.90, 90), index=D.index, columns=D.columns)
    Ame = A.groupby(A.index.to_period("M")).last()
    Ame.index = Ame.index.to_timestamp()
    Ame = Ame.reindex(pd.DatetimeIndex(hm.astype("datetime64[ns]")))
    LO, LA = np.meshgrid(H["lon"], H["lat"])
    cols = [cell_id(np.floor(la * 10) / 10 + 0.05, np.floor(lo * 10) / 10 + 0.05) for la, lo in zip(LA[L][ok], LO[L][ok])]
    Fapi = Ame[cols].to_numpy(float)
    Y, PA, _, mo = umbral.build(S2, P2, hm)
    F = umbral.fill_fraction(Fapi)[:-1]
    out["TerraClimate (respuesta) · estado = API IMERG · 2001-2024"] = umbral.pooled(Y, PA, F, mo, n_boot=n_boot)
    log("umbral: API→TC listo")
    # SMAP L3 en su píxel 9 km; CHIRPS promediado dentro del píxel. Principal: calidad recomendada;
    # sensibilidad (fuera de especificación): todos los retrievals con éxito.
    sidx = H["smap_idx"]
    nxs = S["lat"].shape[1]
    pix = [p for p in np.unique(sidx[L]) if p >= 0 and land.ravel()[p]]
    hi = {m: k for k, m in enumerate(hm)}
    npix = {}
    for mode, tag in (("recomendado", "calidad recomendada"), ("exito", "todos los retrievals, fuera de especificación")):
        mo_r, Mr, _ = smap_l3.monthly(S, mode)
        sel = (mo_r >= np.datetime64("2015-04")) & (mo_r <= hm[-1])
        msm = mo_r[sel]
        Pp, Sp, Fp, keep = [], [], [], []
        for p in pix:
            i, j = divmod(int(p), nxs)
            sv = Mr[sel, i, j]
            if np.isfinite(sv).sum() < 60:
                continue
            m = (sidx == p) & L
            Pp.append(np.nanmean(H["P_chirps"][[hi[x] for x in msm]][:, m], axis=1))
            Sp.append(sv)
            la, lo = float(S["lat"][i, j]), float(S["lon"][i, j])
            c = cell_id(np.floor(la * 10) / 10 + 0.05, np.floor(lo * 10) / 10 + 0.05)
            Fp.append(Ame[c].reindex(pd.DatetimeIndex(msm.astype("datetime64[ns]"))).to_numpy(float) if c in Ame
                      else np.full(msm.size, np.nan))
            keep.append(int(p))
        npix[mode] = keep
        k1 = f"SMAP L3 ({tag}) · estado = SMAP L3 · 2015-2024"
        k2 = f"SMAP L3 ({tag}) · estado = API IMERG · 2015-2024"
        if len(keep) < 10:
            out[k1] = out[k2] = {"no_comprobable": True, "n_celdas": len(keep),
                                 "motivo": "menos de 10 píxeles con ≥ 60 meses de dato"}
            continue
        Pp, Sp, Fp = np.column_stack(Pp), np.column_stack(Sp), np.column_stack(Fp)
        Y, PA, F, mo = umbral.build(Sp, Pp, msm)
        out[k1] = umbral.pooled(Y, PA, F, mo, n_boot=n_boot)
        out[k2] = umbral.pooled(Y, PA, umbral.fill_fraction(Fp)[:-1], mo, n_boot=n_boot)
        out[k1]["pixeles"] = out[k2]["pixeles"] = keep
    # Control manzanas con manzanas: TerraClimate SOLO en las celdas 0.05° que caen en los píxeles que SMAP L3 sí ve
    seen = npix.get("recomendado", [])
    if len(seen) >= 10:
        cell_pix = sidx[L][ok]
        msk = np.isin(cell_pix, seen)
        for lab, sl in (("2001-2024", slice(None)), ("2015-2024", s15)):
            Y, PA, F, mo = umbral.build(S2[sl][:, msk], P2[sl][:, msk], hm[sl])
            out[f"TerraClimate (cubo) · solo zonas que SMAP L3 ve · {lab}"] = umbral.pooled(Y, PA, F, mo, n_boot=n_boot)
    for v in out.values():
        v.pop("theta_boot", None)
    res = {"n_pixeles_smap_usados": {k: len(v) for k, v in npix.items()}, "variantes": out,
           "original_informe": {"theta": 0.59, "theta_ic95": [0.49, 0.73], "n_celdas": 1649}}
    write_json(RES / "umbral_testigos.json", res)
    return res


# ------------------------------------------------------------------ 5. bosque (Hansen)

def step_bosque() -> dict:
    boxes = {}
    for k in ("A", "B"):
        p = PAR_GLDAS[k]
        boxes[f"GLDAS {k}: {p['nombre']} (celda 0.25°)"] = (p["lat"] - .125, p["lat"] + .125, p["lon"] - .125, p["lon"] + .125)
    for k in ("A", "B"):
        p = PAR_HR[k]
        boxes[f"0.05° {k}: {p['nombre']}"] = (p["lat"] - .025, p["lat"] + .025, p["lon"] - .025, p["lon"] + .025)
        boxes[f"9 km {k}: entorno SMAP de {p['nombre']} (±0.045°)"] = (p["lat"] - .045, p["lat"] + .045, p["lon"] - .045, p["lon"] + .045)
    y = YUNA_ALTO
    boxes[y["nombre"]] = (y["lat0"], y["lat1"], y["lon0"], y["lon1"])
    rows = {}
    for name, (a, b, c, d) in boxes.items():
        rows[name] = {"caja": [a, b, c, d], **bosque.summary(a, b, c, d)}
    from ..hr.common import write_json as wj
    wj(RES / "bosque_hansen.json", {"version": "GFC-2025-v1.13", "umbral_cobertura_2000_pct": bosque.TC_MIN,
                                    "periodo_perdida": "2001-2023", "zonas": rows})
    pd.DataFrame([{"zona": k, **{kk: v for kk, v in r.items() if kk != "perdida_por_anio_km2"}} for k, r in rows.items()]) \
        .to_csv(RES / "bosque_hansen.csv", index=False, float_format="%.4g")
    L, T, la, lo = bosque.loss_map(18.55, 19.65, -71.25, -70.05, decim=12)
    np.savez_compressed(RES / "bosque_mapa.npz", perdida=L.astype("float32"), cobertura=T.astype("float32"), lat=la, lon=lo)
    return rows


# ------------------------------------------------------------------ 6. intensidad con CHIRPS diario

def chirps_daily_status() -> dict:
    """Años de CHIRPS diario que el motor de tendencias ya dejó COMPLETOS (archivo registrado en su manifiesto con
    el mismo SHA-256). No descarga nada."""
    import hashlib
    man_p = CHIRPS_D.parent / "MANIFEST.json"
    man = json.loads(man_p.read_text(encoding="utf-8")) if man_p.exists() else {"archivos": {}}
    files = sorted(CHIRPS_D.glob("chirps_v2p0_diario_RD_*.nc")) if CHIRPS_D.exists() else []
    full = []
    for f in files:
        rec = man["archivos"].get(f"chirps_diario/{f.name}")
        if rec and f.stat().st_size == rec["bytes"] and hashlib.sha256(f.read_bytes()).hexdigest() == rec["sha256"]:
            full.append(int(f.stem.split("_")[-1]))
    return {"n_archivos": len(files), "anios_completos": sorted(full), "manifiesto": man_p.exists()}


def step_intensidad(N, B: int) -> dict:
    from . import intensidad
    st = chirps_daily_status()
    if not st["anios_completos"]:
        res = {"estado": "no comprobable: la caché de CHIRPS diario del motor de tendencias está vacía o incompleta",
               **st}
        write_json(RES / "intensidad_chirps.json", res)
        return res
    res = intensidad.run(N, st, B)
    write_json(RES / "intensidad_chirps.json", res)
    return res


# ------------------------------------------------------------------ principal

def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sin-descarga", dest="sin_descarga", action="store_true")
    ap.add_argument("--pasos", nargs="*", default=["calidad", "pares", "memoria", "umbral", "bosque", "intensidad",
                                                     "figuras", "informe", "cuaderno"])
    ap.add_argument("--B", type=int, default=1000)
    ap.add_argument("--n-sur", dest="n_sur", type=int, default=200)
    ap.add_argument("--n-boot-umbral", dest="nbu", type=int, default=150)
    a = ap.parse_args(argv)
    RES.mkdir(parents=True, exist_ok=True)
    if not a.sin_descarga:
        from . import download
        download.main(["--solo", "smap", "hansen", "appeears"])
    need = set(a.pasos)
    N = H = S = land = None
    if need & {"pares", "memoria", "umbral", "intensidad"}:
        log("cargando IMERG/GLDAS (caché)…")
        N = national()
        H = hr_grid()
    if need & {"calidad", "pares", "umbral"}:
        log("cargando SMAP L3…")
        S = smap_l3.load()
        land = smap_l3.land_mask(S)
    if "calidad" in need:
        log("calidad SMAP L3")
        step_calidad(S, land)
    if "pares" in need:
        log("pares")
        step_pares(N, H, S, land, a.n_sur)
    if "memoria" in need:
        log("memoria lluvia vs suelo")
        step_memoria(N, H, a.B)
    if "umbral" in need:
        log("umbral")
        step_umbral(N, H, S, land, a.nbu)
    if "bosque" in need:
        log("bosque (Hansen)")
        step_bosque()
    if "intensidad" in need:
        log("intensidad (CHIRPS)")
        step_intensidad(N, a.B)
    if "figuras" in need:
        from . import figuras
        log("figuras")
        figuras.all_figures()
    if "informe" in need:
        from . import report
        log("informe")
        report.write()
    if "cuaderno" in need:
        from . import notebook
        log("cuaderno 09")
        notebook.build_and_run()
    log("fin")


if __name__ == "__main__":
    main()
