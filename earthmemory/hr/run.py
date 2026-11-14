"""Corrida completa de alta resolución + umbrales críticos.

    python -m earthmemory.hr.run [--sin-descarga] [--rapido]

descarga (caché) → armonización 0.05° → verificación CHIRPS-IMERG → umbrales → quiebres → factores → par →
evento 18-nov-2023 → figuras → tablas → informe ALTA_RESOLUCION.md → cuaderno 05 (ejecutado, HTML).
Determinista: todas las semillas son fijas (SEED y semillas por celda).
"""

from __future__ import annotations

import argparse
import json
import time

import numpy as np
import pandas as pd

from . import changepoints, drivers, figures, harmonise, pair, thresholds
from .common import FIG, GRID, RES, SEED, bh_fdr, write_json
from .sources import SOURCES

# Posición APROXIMADA del barrio Arroyo Hondo Viejo (Distrito Nacional), ±2 km: no son coordenadas oficiales
# de la estación ONAMET. Dato de 431 mm (preliminar) según prensa (Acento, 19-nov-2023) y lo informado por el equipo.
STATION = {"nombre": "ONAMET Arroyo Hondo Viejo (posición aproximada)", "lat": 18.50, "lon": -69.95, "mm": 431.0}


def _cell_name(R, i, j) -> str:
    k = int(R["prov"][i, j])
    prov = R["provs"][k][0] if k >= 0 else "—"
    return f"{prov} ({GRID.lat[i]:.3f}°N, {abs(GRID.lon[j]):.3f}°O)"


def verify_chirps_imerg(R) -> dict:
    nat = R["nat"]
    if "imerg_P" not in nat:
        return {}
    C, I = nat["chirps_a_imerg"].astype(float), nat["imerg_P"].astype(float)
    months = R["meses"].astype("datetime64[M]")
    mo = months.astype(int) % 12
    ca = thresholds.month_demean(C.reshape(C.shape[0], -1), mo)
    ia = thresholds.month_demean(I.reshape(I.shape[0], -1), mo)
    ok = np.isfinite(ca).all(0) & np.isfinite(ia).all(0)
    r = np.full(ca.shape[1], np.nan)
    r[ok] = ((ca[:, ok] - ca[:, ok].mean(0)) * (ia[:, ok] - ia[:, ok].mean(0))).sum(0) / (
        ca.shape[0] * ca[:, ok].std(0) * ia[:, ok].std(0))
    r = r.reshape(C.shape[1:])
    land = nat["frac_rd_imerg"] >= 0.5
    ratio = np.nanmean(C, 0) / np.nanmean(I, 0)
    ok2 = land & np.isfinite(r)
    LOn = np.broadcast_to(nat["imerg_lon"][None, :], r.shape)
    return {"r_mapa": r, "n_celdas_0.1": int(ok2.sum()),
            "r_mediana_oeste_de_71O": float(np.nanmedian(r[ok2 & (LOn < -71)])),
            "r_mediana_este_de_70O": float(np.nanmedian(r[ok2 & (LOn > -70)])),
            "r_mediana": float(np.nanmedian(r[ok2])), "r_p10": float(np.nanpercentile(r[ok2], 10)),
            "r_p90": float(np.nanpercentile(r[ok2], 90)),
            "cociente_lluvia_media_mediana": float(np.nanmedian(ratio[ok2])),
            "cociente_p10": float(np.nanpercentile(ratio[ok2], 10)), "cociente_p90": float(np.nanpercentile(ratio[ok2], 90))}


def dataset_counts(R) -> list[dict]:
    nat = R["nat"]
    area_rd = float((GRID.area_km2() * R["frac_rd"]).sum())
    rows = [{"capa": "CHIRPS v2.0 mensual", "resolucion_nativa": "0.05°", "celdas_RD": int(R["land"].sum()),
             "criterio": "celdas 0.05° con ≥50 % de área en RD y dato en todos los meses"}]

    def centers_in(la, lo):
        LO, LA = np.meshgrid(lo, la)
        return int(harmonise.inside(R["country"], LO.ravel(), LA.ravel()).sum())

    rows.append({"capa": "TerraClimate v1.1", "resolucion_nativa": "1/24° (~4.6 km)",
                 "celdas_RD": centers_in(nat["tc_lat"], nat["tc_lon"]), "criterio": "centro de celda dentro de RD"})
    if "imerg_lat" in nat:
        rows.append({"capa": "IMERG V07 (NASA)", "resolucion_nativa": "0.1°",
                     "celdas_RD": centers_in(nat["imerg_lat"], nat["imerg_lon"]), "criterio": "centro dentro de RD"})
    if "smap_lat" in nat:
        la, lo = nat["smap_lat"], nat["smap_lon"]
        rows.append({"capa": "SMAP L4 V008 (NASA)", "resolucion_nativa": "9 km EASE-2",
                     "celdas_RD": int(harmonise.inside(R["country"], lo.ravel(), la.ravel()).sum()),
                     "criterio": "centro dentro de RD"})
    for name, res_km, how in (("SoilGrids 2.0 (pedido a 0.0025°)", 0.0025, "≈ área RD / área de píxel"),
                              ("Copernicus DEM GLO-90", 1 / 1200, "≈ área RD / área de píxel"),
                              ("ESA WorldCover 2021 (vista 1/8)", 1 / 1500, "≈ área RD / área de píxel")):
        px = (res_km * 111.32) * (res_km * 111.32 * np.cos(np.radians(18.8)))
        rows.append({"capa": name, "resolucion_nativa": f"{res_km:.5f}°", "celdas_RD": int(round(area_rd / px)),
                     "criterio": how})
    rows.append({"capa": "(referencia) área RD en la máscara", "resolucion_nativa": "—", "celdas_RD": round(area_rd),
                 "criterio": "km² (Σ área de celda × fracción en RD)"})
    return rows


def run_thresholds(R, n_boot, n_ci) -> tuple[dict, dict]:
    months = R["meses"].astype("datetime64[M]")
    print("[umbrales] CHIRPS → TerraClimate…", flush=True)
    T = thresholds.run_grid(R["P_chirps"], R["tc_soil"], months, R["land"], n_boot=n_boot, n_ci=n_ci, seed=SEED)
    print("[umbrales] sensibilidad: lluvia TerraClimate → TerraClimate…", flush=True)
    T2 = thresholds.run_grid(R["tc_ppt"], R["tc_soil"], months, R["land"], n_boot=max(99, n_boot // 2), n_ci=0,
                             seed=SEED + 1)
    print("[umbrales] sensibilidad: sin efectos fijos de mes…", flush=True)
    T3 = thresholds.run_grid(R["P_chirps"], R["tc_soil"], months, R["land"], n_boot=max(99, n_boot // 2), n_ci=0,
                             seed=SEED + 2, fe=False)
    return T, T2, T3


def smap_thresholds(R, n_boot) -> dict | None:
    """Mismo análisis con SMAP L4 (NASA, 9 km nativo) y CHIRPS promediado dentro de cada celda SMAP."""
    nat = R["nat"]
    if "smap_sm_rootzone" not in nat:
        return None
    sm = nat["smap_sm_rootzone"] * 1000.0      # m³/m³ × 1000 mm (zona de raíces 0-100 cm) → mm
    sm_m = np.array(nat["smap_meses"], dtype="datetime64[M]")
    months = R["meses"].astype("datetime64[M]")
    sel = np.isin(months, sm_m)
    idx = R["smap_idx"]
    land = R["land"]
    flat = sm.reshape(sm.shape[0], -1)
    cells = np.unique(idx[land])
    la, lo = nat["smap_lat"].ravel(), nat["smap_lon"].ravel()
    rows, PP, SS = [], [], []
    for c in cells:
        m = land & (idx == c)
        if m.sum() < 2:
            continue
        P = R["P_chirps"][sel][:, m].mean(1)
        S = flat[np.isin(sm_m, months[sel]), c]
        if not np.isfinite(S).all() or not np.isfinite(P).all():
            continue
        PP.append(P)
        SS.append(S)
        y, Pa, f, mo, smax = thresholds.series_for_cell(P, S, months[sel])
        r = thresholds.fit_cell(y, Pa, f, mo, n_boot=n_boot, rng=np.random.default_rng([SEED, int(c)]))
        r.pop("_ci_args")
        rows.append({"celda_smap": int(c), "lat": float(la[c]), "lon": float(lo[c]), "n_celdas_005": int(m.sum()), **r})
    df = pd.DataFrame(rows)
    df["q"] = bh_fdr(df["p"].to_numpy())
    df["sostenido"] = (df["q"] < 0.05) & (df["dBIC"] > 2)
    return {"tabla": df, "n": int(len(df)), "n_sostenido": int(df["sostenido"].sum()),
            "theta_mediana": float(df.loc[df["sostenido"], "theta"].median()) if df["sostenido"].any() else None,
            "meses": [str(sm_m[0]), str(sm_m[-1])],
            "series": {"P": np.column_stack(PP), "S": np.column_stack(SS), "meses": months[sel]}}


def run_pooled(R, S, n_boot) -> dict:
    """Curvas de eficiencia frente a llenado, con umbral común por paisaje (terciles de aridez y de arcilla)."""
    months = R["meses"].astype("datetime64[M]")
    land = R["land"]
    feats = static_matrix(R)
    out = {}
    groups = {"todas las celdas": land}
    for key, short, lab in (("aridez_P/PET", "P/PET", ("más seco", "intermedio", "más húmedo")),
                            ("arcilla_%", "arcilla %", ("menos arcilla", "intermedio", "más arcilla"))):
        v = feats[key]
        q = np.nanquantile(v[land], [1 / 3, 2 / 3])
        cuts = [(-np.inf, q[0]), (q[0], q[1]), (q[1], np.inf)]
        for k, (lo, hi) in enumerate(cuts):
            rng_txt = f"≤ {hi:.2f}" if k == 0 else (f"> {lo:.2f}" if k == 2 else f"{lo:.2f}–{hi:.2f}")
            groups[f"{lab[k]} ({short} {rng_txt})"] = land & (v > lo) & (v <= hi)
    for name, m in groups.items():
        print(f"[curvas] {name} ({int(m.sum())} celdas)…", flush=True)
        r = thresholds.pooled_curve(R["P_chirps"][:, m], R["tc_soil"][:, m], months, n_boot=n_boot, seed=SEED)
        r["fuente"] = "CHIRPS → TerraClimate (0.05°)"
        out[name] = r
    if S is not None and "series" in S:
        print("[curvas] SMAP L4 (NASA)…", flush=True)
        r = thresholds.pooled_curve(S["series"]["P"], S["series"]["S"], S["series"]["meses"], n_boot=n_boot, seed=SEED)
        r["fuente"] = "CHIRPS → SMAP L4 zona de raíces (9 km)"
        out["SMAP L4 (NASA), todas las celdas 9 km"] = r
    return out


def run_changepoints(R, n_boot) -> dict:
    months = R["meses"].astype("datetime64[M]")
    land = R["land"]
    out = {}
    for k in ("tc_soil", "tc_def", "P_chirps"):
        X = R[k][:, land]
        A = changepoints.deseasonalise(X, months)
        res = changepoints.pettitt_grid(A, n_boot=n_boot, L=12, seed=SEED)
        res24 = changepoints.pettitt_grid(A, n_boot=max(199, n_boot // 2), L=24, seed=SEED)
        sd = A.std(0)
        tb = months[np.minimum(res["k"] + 1, len(months) - 1)]       # primer mes del segundo tramo
        anio = tb.astype("datetime64[Y]").astype(int) + 1970 + (tb.astype(int) % 12) / 12
        mp = {}
        for name, v in (("p", res["p"]), ("q", res["q"]), ("q_asintotica", res["q_asintotica"]), ("anio", anio),
                        ("cambio_z", res["cambio_media"] / sd), ("q24", res24["q"])):
            a = np.full(land.shape, np.nan)
            a[land] = v
            mp[name] = a
        mp["mes"] = np.full(land.shape, "", dtype=object)
        mp["mes"][land] = months[np.minimum(res["k"] + 1, len(months) - 1)].astype(str)
        mp["resumen"] = {"n_celdas": int(land.sum()), "n_q05_bloques12": int((res["q"] < 0.05).sum()),
                         "n_q05_bloques24": int((res24["q"] < 0.05).sum()),
                         "n_q05_asintotica_sin_correccion": int((res["q_asintotica"] < 0.05).sum())}
        sig = res["q"] < 0.05
        if sig.any():
            yrs = months[np.minimum(res["k"][sig] + 1, len(months) - 1)].astype("datetime64[Y]").astype(int) + 1970
            vals, cnt = np.unique(yrs, return_counts=True)
            mp["resumen"]["anios_mas_frecuentes"] = {int(v): int(c) for v, c in
                                                     sorted(zip(vals, cnt), key=lambda x: -x[1])[:5]}
            mp["resumen"]["fraccion_sube"] = float((res["cambio_media"][sig] > 0).mean())
        out[k] = mp
    return out


def static_matrix(R):
    ar = np.nanmean(R["tc_ppt"], 0) / np.nanmean(R["tc_pet"], 0)
    feats = {"arcilla_%": R["sg_clay"], "arena_%": R["sg_sand"], "pendiente_°": R["dem_pendiente_grados"],
             "elevación_m": R["dem_elev_m"], "relieve_m": R["dem_relieve_m"], "bosque_frac": R["lc_bosque"],
             "cultivo_frac": R["lc_cultivo"], "pasto+matorral_frac": R["lc_pastizal"] + R["lc_matorral"],
             "urbano_frac": R["lc_urbano"], "aridez_P/PET": ar,
             "lluvia_anual_CHIRPS_mm": np.nanmean(R["P_chirps"], 0) * 12}
    return feats


def run_drivers(R, T) -> dict:
    feats = static_matrix(R)
    names = list(feats)
    land = R["land"]
    ii, jj = np.nonzero(land)
    X = np.column_stack([feats[n][land] for n in names])
    lat, lon = GRID.lat[ii], GRID.lon[jj]
    out = {}
    sup = T["sostenido"][land]
    y = np.where(sup, T["theta"][land], np.nan)
    nval = int((np.isfinite(y) & np.isfinite(X).all(1)).sum())
    if nval >= 40:
        d = drivers.analyse(y, X, names, lat, lon, ii, jj, seed=SEED)
        d["titulo"] = "Umbral θ (celdas sostenidas)"
        out["theta"] = d
    else:
        out["theta"] = {"omitido": f"solo {nval} celdas con umbral sostenido y factores completos (< 40)"}
    y2 = T["ef_lineal_mediana"][land]
    d2 = drivers.analyse(y2, X, names, lat, lon, ii, jj, seed=SEED)
    d2["titulo"] = "Eficiencia lluvia→suelo"
    out["eficiencia"] = d2
    y3 = T["smax"][land]
    d3 = drivers.analyse(y3, X, names, lat, lon, ii, jj, seed=SEED)
    d3["titulo"] = "S_max TerraClimate (control)"
    out["smax"] = d3
    return out


def run_pair(R, n_boot) -> dict:
    land = R["land"]
    ii, jj = np.nonzero(land)
    months = R["meses"].astype("datetime64[M]")
    P = R["P_chirps"][:, land]
    S = R["tc_soil"][:, land]
    y, x, mo = pair.efficiency_inputs(P, S, months)
    est, B = pair.bootstrap_slopes(y, x, mo, n_boot=n_boot, seed=SEED)
    lat, lon = GRID.lat[ii], GRID.lon[jj]
    print("[par] candidatos…", flush=True)
    cands = pair.candidates(P, lat, lon, months)
    tst = pair.test_pairs(cands, est, B)
    feats = static_matrix(R)
    keyf = ["arcilla_%", "pendiente_°", "elevación_m", "bosque_frac"]
    F = np.column_stack([feats[k][land] for k in keyf])
    Fz = (F - np.nanmean(F, 0)) / np.nanstd(F, 0)
    a, b = tst["a"], tst["b"]
    sdist = np.sqrt(np.nansum((Fz[a] - Fz[b]) ** 2, 1))
    sig = tst["q"] < 0.05
    nat = R["nat"]
    smap_ok = "smap_sm_rootzone" in nat
    if smap_ok:
        sm = nat["smap_sm_rootzone"] * 1000.0
        sm_m = np.array(nat["smap_meses"], dtype="datetime64[M]")
        selm = np.isin(months, sm_m)
        sidx = R["smap_idx"][land]
    score = np.abs(tst["z"]) * sdist
    order = [k for k in np.argsort(-score) if sig[k]]
    supera = bool(order)
    if not order:   # ningún par supera el FDR: se muestra el mejor candidato, marcado como NO significativo
        order = list(np.lexsort((-score, tst["p"])))
    chosen, smap_res = None, None
    for k in order[:200]:
        A_, B_ = a[k], b[k]
        if smap_ok:
            ca, cb = sidx[A_], sidx[B_]
            if ca == cb:
                continue
            Ss = np.column_stack([sm[:, ca // sm.shape[2], ca % sm.shape[2]], sm[:, cb // sm.shape[2], cb % sm.shape[2]]])
            Ps = P[selm][:, [A_, B_]]
            ys, xs, ms = pair.efficiency_inputs(Ps, Ss, sm_m)
            es, Bs = pair.bootstrap_slopes(ys, xs, ms, n_boot=999, seed=SEED)
            ds, Ds = es[0] - es[1], Bs[:, 0] - Bs[:, 1]
            ps = (1 + (np.abs(Ds - ds) >= abs(ds)).sum()) / 1000
            same = np.sign(ds) == np.sign(tst["delta"][k])
            if not same:
                continue
            smap_res = {"meses": sm_m.astype(str).tolist(), "sm_A": (Ss[:, 0] / 1000).tolist(),
                        "sm_B": (Ss[:, 1] / 1000).tolist(), "e_A": float(es[0]), "e_B": float(es[1]),
                        "delta": float(ds), "p": float(ps), "misma_direccion": bool(same),
                        "celdas_smap": [int(ca), int(cb)]}
        chosen = k
        break
    if chosen is None and order:
        chosen = order[0]
    res = {"n_candidatos_lluvia_parecida": int(len(cands)), "n_significativos_q05": int(sig.sum()),
           "fraccion_significativos": float(sig.mean()) if len(cands) else None}
    if chosen is None:
        return res
    k = chosen
    A_, B_ = a[k], b[k]
    cells = []
    for c in (A_, B_):
        i, j = int(ii[c]), int(jj[c])
        yc, xc = y[:, c], x[:, c]
        cells.append({"ij": (i, j), "lat": float(GRID.lat[i]), "lon": float(GRID.lon[j]), "nombre": _cell_name(R, i, j),
                      "ef": float(est[c]), "ef_ic95": np.percentile(B[:, c], [2.5, 97.5]).tolist(),
                      "Pa": xc, "yd": yc, "S": R["tc_soil"][:, i, j],
                      "lluvia_anual": float(np.nanmean(R["P_chirps"][:, i, j]) * 12),
                      "theta": float(R["_T"]["theta"][i, j]), "sostenido": bool(R["_T"]["sostenido"][i, j])})
    fac = {"arcilla 0-30 cm (%)": (feats["arcilla_%"][cells[0]["ij"]], feats["arcilla_%"][cells[1]["ij"]]),
           "arena 0-30 cm (%)": (feats["arena_%"][cells[0]["ij"]], feats["arena_%"][cells[1]["ij"]]),
           "pendiente (°)": (feats["pendiente_°"][cells[0]["ij"]], feats["pendiente_°"][cells[1]["ij"]]),
           "elevación (×100 m)": (feats["elevación_m"][cells[0]["ij"]] / 100, feats["elevación_m"][cells[1]["ij"]] / 100),
           "bosque (%)": (100 * feats["bosque_frac"][cells[0]["ij"]], 100 * feats["bosque_frac"][cells[1]["ij"]]),
           "cultivo (%)": (100 * feats["cultivo_frac"][cells[0]["ij"]], 100 * feats["cultivo_frac"][cells[1]["ij"]]),
           "aridez P/PET (×10)": (10 * feats["aridez_P/PET"][cells[0]["ij"]], 10 * feats["aridez_P/PET"][cells[1]["ij"]]),
           "S_max TerraClimate (×10 mm)": (R["_T"]["smax"][cells[0]["ij"]] / 10, R["_T"]["smax"][cells[1]["ij"]] / 10)}
    fac = {n: (float(v[0]), float(v[1])) for n, v in fac.items()}
    # IMERG (NASA) en las dos celdas: ¿también 'misma lluvia' a 0.1°?
    imerg = None
    if "imerg_P" in nat:
        la, lo = nat["imerg_lat"], nat["imerg_lon"]
        sers = []
        for c in cells:
            ia = int(np.argmin(np.abs(la - c["lat"])))
            ja = int(np.argmin(np.abs(lo - c["lon"])))
            sers.append((ia, ja, nat["imerg_P"][:, ia, ja].astype(float)))
        ma = thresholds.month_demean(np.column_stack([s[2] for s in sers]), months.astype(int) % 12)
        imerg = {"misma_celda_0.1": sers[0][:2] == sers[1][:2],
                 "r_anomalias": float(np.corrcoef(ma[:, 0], ma[:, 1])[0, 1]),
                 "lluvia_anual_A": float(sers[0][2].mean() * 12), "lluvia_anual_B": float(sers[1][2].mean() * 12)}
    print("[par] sustitutos…", flush=True)
    fpr = pair.surrogate_fpr(y[:, A_], y[:, B_], x[:, A_], x[:, B_], mo, n_sur=300, n_boot=199, seed=SEED)
    # Tasa de 'descubrimientos' en una población nula: TODOS los candidatos con respuesta sustituta común
    res.update({"celdas": cells, "supera_fdr": supera, "dist_km": float(cands[k][2]), "dif_rel_lluvia": float(cands[k][3]),
                "r_lluvia": float(cands[k][4]), "ks_D": float(cands[k][5]), "delta": float(tst["delta"][k]),
                "ic95_delta": tst["ic95"][:, k].tolist(), "z": float(tst["z"][k]), "p": float(tst["p"][k]),
                "q": float(tst["q"][k]), "distancia_estatica_z": float(sdist[k]), "factores": fac, "smap": smap_res,
                "imerg": imerg, "sustitutos": fpr,
                "top10": [{"A": _cell_name(R, int(ii[a[q_]]), int(jj[a[q_]])), "B": _cell_name(R, int(ii[b[q_]]), int(jj[b[q_]])),
                           "delta": float(tst["delta"][q_]), "q": float(tst["q"][q_]), "dist_estatica": float(sdist[q_])}
                          for q_ in order[:10]]})
    return res


def event(R) -> dict:
    Pd = R["Pd_nov2023"]
    i = int(np.argmin(np.abs(GRID.lat - STATION["lat"])))
    j = int(np.argmin(np.abs(GRID.lon - STATION["lon"])))
    win = Pd[:, max(i - 1, 0):i + 2, max(j - 1, 0):j + 2]
    pent = Pd[15:20].sum(0)
    E = {"lat": STATION["lat"], "lon": STATION["lon"], "celda_chirps": _cell_name(R, i, j),
         "max_pentada_chirps": float(np.nanmax(np.where(R["land"], pent, np.nan))),
         "barras": {"estación ONAMET 18-nov (preliminar, prensa)": STATION["mm"],
                    "CHIRPS 18-nov · celda 0.05°": float(Pd[17, i, j]),
                    "CHIRPS 18-nov · máximo 3×3 celdas (~16 km)": float(np.nanmax(win[17])),
                    "CHIRPS péntada 16-20 nov · celda": float(pent[i, j]),
                    "CHIRPS noviembre completo · celda": float(np.nansum(Pd[:, i, j]))}}
    nat = R["nat"]
    if "imerg_Pd_nov2023" in nat:
        la, lo = nat["imerg_lat"], nat["imerg_lon"]
        ia, ja = int(np.argmin(np.abs(la - STATION["lat"]))), int(np.argmin(np.abs(lo - STATION["lon"])))
        I = nat["imerg_Pd_nov2023"].astype(float)
        E["barras"]["IMERG 18-nov (00-24 UTC) · celda 0.1°"] = float(I[17, ia, ja])
        E["barras"]["IMERG 16-20 nov · celda 0.1°"] = float(I[15:20, ia, ja].sum())
    E["mes_chirps_vs_diario"] = {"suma_diaria_nov_celda": float(np.nansum(Pd[:, i, j])),
                                 "mensual_nov_celda": float(R["P_chirps"][np.flatnonzero(R["meses"] == "2023-11")[0], i, j])}
    return E


def cell_table(R, T, T2, C) -> pd.DataFrame:
    land = R["land"]
    ii, jj = np.nonzero(land)
    feats = static_matrix(R)
    df = pd.DataFrame({"lat": GRID.lat[ii], "lon": GRID.lon[jj],
                       "provincia": [R["provs"][int(R["prov"][i, j])][0] if R["prov"][i, j] >= 0 else "" for i, j in zip(ii, jj)],
                       "frac_rd": R["frac_rd"][land]})
    for n, a in feats.items():
        df[n] = a[land]
    for k in ("theta", "theta_lo", "theta_hi", "p", "q", "dBIC", "dAIC", "sostenido", "ef_seco", "ef_umbral",
              "ef_humedo", "ef_lineal_mediana", "smax"):
        df[f"umbral_{k}"] = T[k][land]
    df["umbral_sostenido_con_lluvia_TC"] = T2["sostenido"][land]
    for v, Ck in C.items():
        for k in ("anio", "q", "q24", "q_asintotica", "cambio_z"):
            df[f"quiebre_{v}_{k}"] = Ck[k][land]
        df[f"quiebre_{v}_mes"] = Ck["mes"][land]
    return df


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sin-descarga", dest="sin_descarga", action="store_true")
    ap.add_argument("--rearmonizar", action="store_true")
    ap.add_argument("--rapido", action="store_true", help="menos réplicas bootstrap (solo para pruebas)")
    ap.add_argument("--sin-cuaderno", dest="sin_cuaderno", action="store_true")
    args = ap.parse_args(argv)
    t0 = time.time()
    nb, nci, ncp, npair = (99, 50, 199, 199) if args.rapido else (499, 300, 999, 999)
    if not args.sin_descarga:
        from . import download
        download.run(argparse.Namespace(hilos=12, sin_smap=False, solo=None))
    R = harmonise.build(force=args.rearmonizar)
    RES.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)
    A = {}
    V = verify_chirps_imerg(R)
    if V:
        A["r_chirps_imerg"] = V.pop("r_mapa")
    counts = dataset_counts(R)
    T, T2, T3 = run_thresholds(R, nb, nci)
    R["_T"] = T
    S = smap_thresholds(R, nb)
    G = run_pooled(R, S, 150 if not args.rapido else 30)
    print("[quiebres]…", flush=True)
    C = run_changepoints(R, ncp)
    print("[factores]…", flush=True)
    D = run_drivers(R, T)
    print("[par]…", flush=True)
    Pr = run_pair(R, npair)
    E = event(R)
    # ---- tablas
    df = cell_table(R, T, T2, C)
    df.to_csv(RES / "celdas_005.csv", index=False, float_format="%.5g")
    if S is not None:
        S["tabla"].to_csv(RES / "umbrales_smap_9km.csv", index=False, float_format="%.5g")
    pd.DataFrame(counts).to_csv(RES / "capas_resolucion_y_celdas.csv", index=False)
    pd.DataFrame([{"clave": k, **{kk: v[kk] for kk in ("nombre", "cita", "doi", "url", "licencia", "version",
                                                         "resolucion", "nasa")}} for k, v in SOURCES.items()]).to_csv(
        RES / "fuentes.csv", index=False)
    land = R["land"]
    tested = np.isfinite(T["p"]) & land
    sup = T["sostenido"] & land
    resumen = {
        "periodo": [str(R["meses"][0]), str(R["meses"][-1])], "rejilla": "CHIRPS 0.05° (bordes múltiplos de 0.05°)",
        "celdas_tierra_005": int(land.sum()), "capas": counts, "chirps_vs_imerg_0.1": V,
        "worldcover_validacion": R["meta"].get("worldcover_validacion"),
        "terraclimate_atributos": R["meta"]["terraclimate"].get("soil"),
        "umbrales": {
            "celdas_evaluadas": int(tested.sum()), "p_menor_005_sin_corregir": int((T["p"][tested] < 0.05).sum()),
            "q_menor_005": int((T["q"][tested] < 0.05).sum()), "sostenidos_q005_dBIC2": int(sup.sum()),
            "sostenidos_dBIC6": int((sup & (T["dBIC"] > 6)).sum()),
            "theta_mediana": float(np.nanmedian(T["theta"][sup])) if sup.any() else None,
            "theta_p25_p75": np.nanpercentile(T["theta"][sup], [25, 75]).tolist() if sup.any() else None,
            "theta_mm_mediana": float(np.nanmedian((T["smin"] + T["theta"] * (T["smax"] - T["smin"]))[sup])) if sup.any() else None,
            "ancho_ic_mediana": float(np.nanmedian((T["theta_hi"] - T["theta_lo"])[sup])) if sup.any() else None,
            "ef_seco_mediana": float(np.nanmedian(T["ef_seco"][sup])) if sup.any() else None,
            "ef_umbral_mediana": float(np.nanmedian(T["ef_umbral"][sup])) if sup.any() else None,
            "ef_humedo_mediana": float(np.nanmedian(T["ef_humedo"][sup])) if sup.any() else None,
            "fraccion_saturacion_b5_neg": float((T["b5"][sup] < 0).mean()) if sup.any() else None,
            "fraccion_pico_sube_y_cae": float(((T["ef_umbral"] > T["ef_seco"]) & (T["ef_humedo"] < T["ef_umbral"]))[sup].mean())
            if sup.any() else None,
            "provincias_con_mas_umbrales": (pd.Series([R["provs"][int(k)][0] for k in R["prov"][sup] if k >= 0])
                                            .value_counts().head(6).to_dict() if sup.any() else {}),
            "sensibilidad_lluvia_TerraClimate": {"sostenidos": int((T2["sostenido"] & land).sum()),
                                                 "coinciden_con_CHIRPS": int((T2["sostenido"] & sup).sum())},
            "sensibilidad_sin_efectos_fijos_mes": {"sostenidos": int((T3["sostenido"] & land).sum()),
                                                   "coinciden_con_principal": int((T3["sostenido"] & sup).sum()),
                                                   "theta_mediana": float(np.nanmedian(T3["theta"][T3["sostenido"] & land]))
                                                   if (T3["sostenido"] & land).any() else None},
            "smap_9km": {k: v for k, v in S.items() if k not in ("tabla", "series")} if S else None,
            "curvas_por_paisaje": {k: {kk: vv for kk, vv in v.items() if kk not in ("theta_boot",)} for k, v in G.items()}},
        "quiebres": {k: v["resumen"] for k, v in C.items()},
        "factores": D, "par": {k: v for k, v in Pr.items() if k != "celdas"},
        "par_celdas": [{k: v for k, v in c.items() if k not in ("Pa", "yd", "S")} for c in Pr.get("celdas", [])],
        "evento_2023_11_18": E, "semilla": SEED,
        "replicas": {"umbral_supF": nb, "umbral_IC": nci, "pettitt": ncp, "par": npair}}
    write_json(RES / "resumen.json", resumen)
    # ---- figuras
    print("[figuras]…", flush=True)
    figures.fig_climatologia(R, A, FIG / "hr1_climatologia_resolucion_nativa")
    figures.fig_estaticos(R, FIG / "hr2_factores_estaticos")
    if sup.any():
        # celda ejemplo: umbral sostenido con mayor ΔBIC
        i, j = np.unravel_index(np.nanargmax(np.where(sup, T["dBIC"], np.nan)), sup.shape)
        ex = thresholds.example_curve(R["P_chirps"], R["tc_soil"], R["meses"].astype("datetime64[M]"), i, j)
        ex.update({"nombre": _cell_name(R, i, j), "theta_lo": T["theta_lo"][i, j], "theta_hi": T["theta_hi"][i, j]})
        resumen["celda_ejemplo_umbral"] = {"nombre": ex["nombre"], "theta": ex["theta"],
                                           "ic95": [float(ex["theta_lo"]), float(ex["theta_hi"])],
                                           "dBIC": float(T["dBIC"][i, j]), "q": float(T["q"][i, j])}
        figures.fig_umbrales(R, T, ex, FIG / "hr3_umbrales")
    figures.fig_curvas(G, FIG / "hr3b_curvas_por_paisaje")
    figures.fig_quiebres(R, C, FIG / "hr4_quiebres")
    figures.fig_factores(D, FIG / "hr5_factores_del_umbral")
    if "celdas" in Pr:
        figures.fig_par(R, Pr, FIG / "hr6_par_misma_lluvia")
    figures.fig_evento(R, E, FIG / "hr7_evento_2023-11-18")
    resumen["segundos"] = round(time.time() - t0)
    write_json(RES / "resumen.json", resumen)
    from . import report
    report.write(resumen)
    if not args.sin_cuaderno:
        from . import notebook
        notebook.build()
    print(f"[listo] {resumen['segundos']} s", flush=True)


if __name__ == "__main__":
    main()
