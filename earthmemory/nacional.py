"""Earth Memory nacional (motor principal): IMERG 0.1° + GLDAS Noah 0.25°, todo el país.

    python -m earthmemory.nacional --pais DOM          (dentro de Docker: docker compose run --rm nacional)

Celda de análisis = celda GLDAS 0.25° con al menos 25 % de su área en el país, más país que vecino y
con dato de suelo en GLDAS. La lluvia de esa celda es IMERG remapeada de forma conservativa (solo la
parte del país). Mapas de lluvia a 0.1° (celda IMERG nativa). Series de provincia = medias
ponderadas por el área de cada celda dentro de la provincia (geoBoundaries ADM1).

NASA POWER (MERRA-2, ~0.5°) se corre aparte como comprobación (earthmemory.pipeline).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from phantom import drought
from phantom import stats as pstats

from . import (anomalies, appeears_hook, boundaries, calibration, contrasts, coupling, episodes, extremes,
               grid, gridded, power, region)
from .pipeline import _clean, write_csv, write_json

RESP = ["SM_RAIZ", "SM_0_10", "ET", "TAIRE"]
RESP_NAME = {"SM_RAIZ": "humedad zona de raíces 0-100 cm (GLDAS)", "SM_0_10": "humedad superficial 0-10 cm (GLDAS)",
             "ET": "evapotranspiración (GLDAS)", "TAIRE": "temperatura del aire (forzamiento GLDAS)",
             "NDVI": "NDVI MODIS (AppEEARS)", "EVI": "EVI MODIS (AppEEARS)"}
SOIL = ("SM_RAIZ", "SM_0_10")
DROUGHT_WINDOWS = {"2015": ("2014-12-01", "2015-11-01"), "2019-2020": ("2019-06-01", "2020-05-01")}


# ------------------------------------------------------------------ datos

def load(args) -> dict:
    ddir = Path(args.datos)
    man = power.Manifest(ddir / "MANIFEST.json")
    adm1_p, adm1_meta = boundaries.ensure_adm(ddir, args.pais, "ADM1", man)
    units = boundaries.load_units(adm1_p)
    ne = region.ensure_boundaries(ddir, args.pais, man)
    others = region.load_country(ne, args.pais).others
    g_im, P_im = gridded.imerg_monthly(ddir)
    g_gl, GL = gridded.gldas_monthly(ddir)
    y0, y1 = f"{args.anio0}-01-01", f"{args.anio1}-12-01"
    P_im = P_im.loc[y0:y1]
    GL = {k: v.loc[y0:y1] for k, v in GL.items()}
    cells_im, w_im = grid.fractions(g_im, units, others, n=12)
    cells_gl, w_gl = grid.fractions(g_gl, units, others, n=25)
    cells_im["incluida"] = grid.include_mask(cells_im, args.min_frac)
    cells_im["meses_con_dato"] = P_im.notna().sum().reindex(cells_im["celda"]).to_numpy()
    land = GL["SM_RAIZ"].notna().all()
    cells_gl["tierra_gldas"] = cells_gl["celda"].map(land).fillna(False).astype(bool)
    cells_gl["elevacion_m"] = cells_gl["celda"].map(gridded.gldas_elevation(ddir, g_gl))
    cells_gl["incluida"] = grid.include_mask(cells_gl, args.min_frac) & cells_gl["tierra_gldas"]
    motivo = []
    for _, c in cells_gl.iterrows():
        m = []
        if not c["tierra_gldas"]:
            m.append("GLDAS la trata como mar")
        if c["frac_pais"] < args.min_frac:
            m.append(f"fracción en {args.pais} {c['frac_pais']:.2f} < {args.min_frac}")
        if c["frac_otro_pais"] > c["frac_pais"]:
            m.append(f"dominada por {c['otro_pais']}")
        motivo.append("; ".join(m))
    cells_gl["motivo_exclusion"] = motivo
    rw = grid.remap_weights(g_im, g_gl, cells_im["frac_pais"].to_numpy())
    P_gl = grid.apply_weights(P_im, rw, "celda_fina", "celda_gruesa")
    g_d, D_im = gridded.imerg_daily(ddir, g_im)
    if len(D_im):
        D_im = D_im.loc[f"{args.anio0}-01-01":f"{args.anio1}-12-31"]
        D_gl = grid.apply_weights(D_im, rw, "celda_fina", "celda_gruesa")
    else:
        D_gl = pd.DataFrame()
    g_hh, HH = gridded.imerg_halfhour(ddir)
    extra = appeears_hook.load_monthly(Path(args.appeears), g_gl, P_gl.index)
    npp = appeears_hook.annual_npp(Path(args.appeears), g_gl)
    _, P_mod = gridded.gldas_rain(ddir)
    if len(P_mod):
        P_mod = P_mod.loc[y0:y1]
    return {"man": man, "adm1_meta": adm1_meta, "units": units, "others": others, "g_im": g_im, "g_gl": g_gl,
            "P_im": P_im, "GL": GL, "cells_im": cells_im, "cells_gl": cells_gl, "w_im": w_im, "w_gl": w_gl,
            "rw": rw, "P_gl": P_gl, "D_im": D_im, "D_gl": D_gl, "HH": HH, "extra": extra, "npp": npp,
            "P_mod": P_mod}


# ------------------------------------------------------------------ análisis

def morans_i(values: pd.Series, cells: pd.DataFrame, res: float) -> float | None:
    """I de Moran con vecindad reina (celdas que se tocan) sobre una rejilla regular. Descriptivo."""
    v = values.dropna()
    if len(v) < 5:
        return None
    c = cells.set_index("celda").loc[v.index]
    la, lo = c["lat"].to_numpy(), c["lon"].to_numpy()
    W = ((np.abs(la[:, None] - la[None, :]) <= res * 1.01) & (np.abs(lo[:, None] - lo[None, :]) <= res * 1.01))
    np.fill_diagonal(W, False)
    x = v.to_numpy() - v.mean()
    s0 = W.sum()
    if s0 == 0:
        return None
    return float(len(x) / s0 * (x @ W.astype(float) @ x) / (x @ x))


def trends_block(name: str, df: pd.DataFrame, unit: str, cells: pd.DataFrame, res: float, n_surr: int,
                 rel: pd.Series | None = None) -> tuple[pd.DataFrame, dict]:
    rows = anomalies.cell_trends(name, df, unit)
    rows = anomalies.add_bh(rows)
    t = pd.DataFrame(rows)
    cal = {}
    for meth in ("fase", "bloques"):
        summ, pc = calibration.trend_calibration(df[t["celda"]], n_surr=n_surr, method=meth,
                                                 seed=2026 if meth == "fase" else 2027)
        cal[meth] = summ
        if meth == "fase":
            t = t.merge(pc[["celda", "p_empirico", "q_bh_empirico", "Z_obs"]], on="celda", how="left")
    if rel is not None:
        t["pendiente_pct_clim_decada"] = 100 * t["pendiente_decada"] / t["celda"].map(rel)
    t["sig_bh_nominal"] = t["q_bh"] < 0.05
    t["sig_bh_calibrado"] = t["q_bh_empirico"] < 0.05
    cal["moran_I_pendiente"] = morans_i(t.set_index("celda")["pendiente_decada"], cells, res)
    cal["n_celdas"] = int(len(t))
    cal["celdas_q05_nominal"] = int(t["sig_bh_nominal"].sum())
    cal["celdas_q05_calibrado"] = int(t["sig_bh_calibrado"].sum())
    cal["mediana_pendiente_decada"] = float(t["pendiente_decada"].median())
    return t, cal


def run(args) -> dict:
    rdir = Path(args.resultados)
    D = load(args)
    cells_gl, cells_im = D["cells_gl"], D["cells_im"]
    inc = sorted(cells_gl.loc[cells_gl["incluida"], "celda"])
    inc_im = sorted(cells_im.loc[cells_im["incluida"], "celda"])
    print(f"celdas IMERG en la caja: {len(cells_im)}, incluidas: {len(inc_im)}; GLDAS en la caja: {len(cells_gl)}, "
          f"incluidas: {len(inc)}", flush=True)
    P = D["P_gl"][inc]
    spi = {k: anomalies.spi_table(P, k) for k in (1, 3, 6)}
    raw = {r: D["GL"][r][inc] for r in RESP}
    for k, v in D["extra"].items():
        raw[k] = v[inc]
    responses = RESP + sorted(D["extra"])
    zt = {kind: {r: anomalies.zscore(raw[r], kind) for r in responses} for kind in ("robusta", "estandar")}
    z = zt["robusta"]
    spi_im3 = anomalies.spi_table(D["P_im"][inc_im], 3)
    has_mod = len(D["P_mod"]) > 0
    spi_mod = {k: anomalies.spi_table(D["P_mod"][inc], k) for k in (1, 3, 6)} if has_mod else None

    # --- tendencias + calibración de falsos positivos
    print("tendencias y calibración…", flush=True)
    clim_im = D["P_im"][inc_im].mean()
    tr, cal_tr = [], {}
    t, c = trends_block("PRECIP_IMERG_0.1", D["P_im"][inc_im], "mm/mes por década", cells_im, 0.1, args.n_surr, clim_im)
    tr.append(t)
    cal_tr["PRECIP_IMERG_0.1"] = c
    units_tr = {"SM_RAIZ": "mm por década", "SM_0_10": "mm por década", "TAIRE": "°C por década", "ET": "mm/día por década"}
    for r in ("SM_RAIZ", "SM_0_10", "TAIRE", "ET"):
        t, c = trends_block(r, raw[r], units_tr[r], cells_gl, 0.25, args.n_surr,
                            raw[r].mean() if r != "TAIRE" else None)
        tr.append(t)
        cal_tr[r] = c
    if has_mod:  # diagnóstico: ¿la lluvia que forzó a GLDAS tiene la misma tendencia que IMERG?
        for name, dfp in (("LLUVIA_GLDAS_FORZAMIENTO", D["P_mod"][inc]), ("LLUVIA_IMERG_EN_CELDA_GLDAS", P)):
            t, c = trends_block(name, dfp, "mm/mes por década", cells_gl, 0.25, args.n_surr, dfp.mean())
            tr.append(t)
            cal_tr[name] = c
    trends = pd.concat(tr, ignore_index=True)

    # --- acople y memoria
    print("acople y memoria…", flush=True)
    st = coupling.Settings(B=args.B)
    cm = coupling.compute(z, spi, inc, responses, st)
    lagp = coupling.lag_profile(z, spi[3], inc, responses)
    ante = coupling.antecedent_table(z, spi, inc, list(SOIL), st)
    ante["q_bh"] = pstats.benjamini_hochberg(ante["p_delta_gamma"].tolist())

    # --- pares con lluvia parecida
    print("pares…", flush=True)
    pairs = contrasts.candidate_pairs(cells_gl, P, spi[3])
    tests = contrasts.test_pairs(pairs, cm, responses)

    # --- calibración de la prueba de pares (nulo paramétrico)
    print("calibración de pares…", flush=True)
    sim = pairs[pairs["lluvia_parecida"]][["celda_a", "celda_b"]].to_numpy().tolist()
    rng = np.random.default_rng(31)
    pick = [tuple(sim[i]) for i in sorted(rng.choice(len(sim), size=min(args.pares_calib, len(sim)), replace=False))]
    null = calibration.pair_null(z, spi, pick, responses, st, n_surr=args.n_surr_pares, B=400)
    null_sum = calibration.pair_null_summary(null)
    tests["p_calibrado"] = calibration.calibrated_p(tests, null)
    tests["p_empirico_nulo"] = calibration.empirical_p(tests, null)
    tests["q_bh_calibrado"] = pstats.benjamini_hochberg([None if not np.isfinite(v) else float(v)
                                                         for v in tests["p_calibrado"]])
    tests["q_bh_calibrado"] = tests["q_bh_calibrado"].astype(float)

    # --- sensibilidad de las pruebas más fuertes (tras calibrar)
    sig = tests[tests["q_bh_calibrado"] < 0.05].copy()
    targets = sig if len(sig) else tests.nsmallest(20, "p_calibrado")
    targets = targets.assign(z_abs=(targets["delta"] / targets["ee_boot"]).abs()).nlargest(40, "z_abs")
    variants = {
        "bloque 6 meses": st.but(block=6), "bloque 24 meses": st.but(block=24),
        "z estándar (media/DE)": None, "SPI-1 en r": st.but(spi_r=1), "SPI-6 en r": st.but(spi_r=6),
        "lag 1 mes en r": st.but(lag_r=1), "lag 2 meses en r": st.but(lag_r=2),
        "ARX forzado con SPI-3": st.but(spi_arx=3), "Spearman en r": st.but(corr="spearman"),
        "2001-2012": st.but(period=(2001, 2012)), "2013-2024": st.but(period=(2013, 2024)),
    }
    print("sensibilidad…", flush=True)
    vcm = {lab: (coupling.compute(zt["estandar"], spi, inc, responses, st) if s is None
                 else coupling.compute(z, spi, inc, responses, s)) for lab, s in variants.items()}
    if has_mod:  # ¿el contraste sigue con la lluvia que de verdad forzó a GLDAS?
        vcm[MODEL_RAIN] = coupling.compute(z, spi_mod, inc, responses, st)
    sens = contrasts.sensitivity(targets, vcm)
    ranked = contrasts.rank(targets.drop(columns=["z_abs"]), sens[sens["variante"] != MODEL_RAIN], pairs, cells_gl)
    if has_mod:
        mr = sens[sens["variante"] == MODEL_RAIN][["celda_a", "celda_b", "respuesta", "metrica", "delta", "ic95_bajo",
                                                    "ic95_alto", "mismo_signo", "ic_excluye_0"]]
        mr = mr.rename(columns={"delta": "delta_lluvia_modelo", "ic95_bajo": "ic95_bajo_lluvia_modelo",
                                "ic95_alto": "ic95_alto_lluvia_modelo", "mismo_signo": "mismo_signo_lluvia_modelo",
                                "ic_excluye_0": "ic_excluye_0_lluvia_modelo"})
        ranked = ranked.merge(mr, on=["celda_a", "celda_b", "respuesta", "metrica"], how="left")
        ranked["sobrevive_lluvia_modelo"] = (ranked["mismo_signo_lluvia_modelo"].fillna(False).astype(bool)
                                             & ranked["ic_excluye_0_lluvia_modelo"].fillna(False).astype(bool))
        ranked["etiqueta_producto"] = np.where(ranked["sobrevive_lluvia_modelo"], "sobrevive con la lluvia del modelo",
                                               "posible diferencia entre productos")
    ranked["significativo_q05_nominal"] = ranked["q_bh"] < 0.05
    ranked["significativo_q05_calibrado"] = ranked["q_bh_calibrado"] < 0.05
    keys = (["significativo_q05_calibrado"] + (["sobrevive_lluvia_modelo"] if has_mod else [])
            + ["robustez", "pasa_criterio_estricto", "q_bh_calibrado", "efecto_abs"])
    ranked = ranked.sort_values(keys, ascending=[False] * (len(keys) - 2) + [True, False])
    ranked["rango"] = np.arange(1, len(ranked) + 1)
    ranked = ranked.reset_index(drop=True)

    # --- episodios, contradicciones y factores
    print("episodios…", flush=True)
    daily = D["D_gl"]
    eps, rev = [], []
    for c in inc:
        dly = daily[c] if c in daily else None
        zc = {r: z[r][c] for r in SOIL}
        eps += episodes.cell_episodes(c, spi[3][c], zc, dly, responses=SOIL)
        rev.append(episodes.reverse_counts(c, spi[3][c], z["SM_RAIZ"][c]))
    ep = pd.DataFrame(eps)
    contra = contradiction_table(ep, rev)
    if has_mod:  # mismas contradicciones, pero con la lluvia que forzó al modelo
        eps_m, rev_m = [], []
        for c in inc:
            eps_m += episodes.cell_episodes(c, spi_mod[3][c], {r: z[r][c] for r in SOIL}, None, responses=SOIL)
            rev_m.append(episodes.reverse_counts(c, spi_mod[3][c], z["SM_RAIZ"][c]))
        ep_mod = pd.DataFrame(eps_m)
        cm_ = contradiction_table(ep_mod, rev_m)
        keep = ["celda", "n_episodios", "n_con_retorno", "n_A_raiz", "n_A_superficial", "n_B1_suelo_seco_sin_sequia",
                "n_B2_suelo_normal_en_sequia"]
        contra = contra.merge(cm_[keep].rename(columns={k: f"{k}_lluvia_modelo" for k in keep if k != "celda"}),
                              on="celda", how="left")
        ep = ep.merge(match_episodes_across_products(ep, ep_mod), on=["celda", "inicio"], how="left")
    else:
        ep_mod = pd.DataFrame()
    whip = whiplash_table(inc, spi[3], spi_mod[3] if has_mod else None, z)
    outcomes = [("z_retorno_SM_RAIZ", "SM_RAIZ"), ("z_retorno_SM_0_10", "SM_0_10"),
                ("contradiccion_A_SM_RAIZ", "SM_RAIZ")]
    fac = factor_table(ep, outcomes, args.B)
    fsens = factor_sensitivity(ep, inc, spi, z, daily, outcomes, args.B)
    icl = intensity_climatology(daily, inc, args)

    # --- episodios emparejados para los 3 mejores pares distintos
    top_pairs = []
    for _, r in ranked.iterrows():
        k = (r["celda_a"], r["celda_b"])
        if k not in top_pairs:
            top_pairs.append(k)
        if len(top_pairs) == 3:
            break
    matched = {}
    for a, b in top_pairs:
        m = episodes.matched_pair_episodes(ep[ep["celda"] == a].reset_index(drop=True),
                                           ep[ep["celda"] == b].reset_index(drop=True), resp="SM_RAIZ")
        matched[f"{a}|{b}"] = {"episodios": m, "resumen": [episodes.paired_summary(m, v) for v in
                                                            ("z_retorno", "meses_recuperacion", "fraccion_intensa",
                                                             "max1d", "z_antecedente", "meses_previos")] if len(m) else []}

    # --- provincias (series ponderadas por área)
    print("provincias…", flush=True)
    prov = province_block(D, inc_im, inc)

    # --- evento de Santo Domingo
    ev = event_block(D, args) if len(D["D_im"]) else None

    # --- comprobación cruzada con POWER/MERRA-2
    xval = power_crosscheck(D, args, spi[3], z["SM_RAIZ"], cells_gl, inc)
    grace = grace_block(D, args)

    R = {"args": vars(args), "D": D, "inc": inc, "inc_im": inc_im, "P": P, "spi": spi, "spi_im3": spi_im3, "z": z,
         "raw": raw, "responses": responses, "trends": trends, "cal_tr": cal_tr, "cm": cm, "lagp": lagp, "ante": ante,
         "pairs": pairs, "tests": tests, "null": null, "null_sum": null_sum, "pares_calibracion": pick, "sens": sens,
         "ranked": ranked, "ep": ep, "contra": contra, "fac": fac, "fsens": fsens, "icl": icl, "matched": matched, "ep_mod": ep_mod, "whip": whip,
         "has_mod": has_mod, "grace": grace, "spi_mod": spi_mod, "rue": rain_use_efficiency(D, inc),
         "prov": prov, "event": ev, "xval": xval, "settings": st, "variants": list(variants)}
    ensure_demo_matched(R)
    write_outputs(R, rdir)
    if args.cache:  # solo para desarrollo: rehacer figuras/informe sin recalcular
        import pickle
        Path(args.cache).parent.mkdir(parents=True, exist_ok=True)
        Path(args.cache).write_bytes(pickle.dumps(R))
    from . import figures, report
    figs = figures.make_all(R, Path(args.figuras))
    report.write(R, figs, Path(args.informe))
    return R


MODEL_RAIN = "lluvia GLDAS (forzamiento del modelo)"
WHIP_THR = 0.84   # ≈ percentiles 20/80 de una normal estándar (umbral de Stojanovic et al. 2025)
WHIP_GAP = 3      # meses como máximo entre el extremo seco y el húmedo


def whiplash_events(s: pd.Series, thr: float = WHIP_THR, gap: int = WHIP_GAP) -> dict:
    """Transiciones bruscas: seco→húmedo = mes con índice <= −thr seguido, en <= gap meses, por uno >= +thr;
    húmedo→seco al revés. Se cuentan eventos que no se solapan (tras uno se sigue desde su llegada)."""
    v = s.to_numpy(float)
    out = {"seco_a_humedo": 0, "humedo_a_seco": 0}
    for key, a, b in (("seco_a_humedo", lambda x: x <= -thr, lambda x: x >= thr),
                      ("humedo_a_seco", lambda x: x >= thr, lambda x: x <= -thr)):
        t = 0
        while t < len(v):
            if np.isfinite(v[t]) and a(v[t]):
                hit = next((u for u in range(t + 1, min(len(v), t + gap + 1)) if np.isfinite(v[u]) and b(v[u])), None)
                if hit is not None:
                    out[key] += 1
                    t = hit
            t += 1
    return out


def whiplash_table(inc, spi3, spi3_mod, z) -> pd.DataFrame:
    rows = []
    for c in inc:
        rec = {"celda": c}
        series = {"lluvia_imerg_spi3": spi3[c], "suelo_raiz_z": z["SM_RAIZ"][c], "suelo_sup_z": z["SM_0_10"][c]}
        if spi3_mod is not None:
            series["lluvia_modelo_spi3"] = spi3_mod[c]
        for k, s in series.items():
            for d, n in whiplash_events(s).items():
                rec[f"{k}_{d}"] = n
        rows.append(rec)
    return pd.DataFrame(rows)


def rain_use_efficiency(D: dict, inc: list) -> pd.DataFrame:
    """RUE = NPP anual (MOD17A3HGF) / lluvia anual IMERG, por celda y año. Vacío hasta que llegue AppEEARS."""
    npp = D["npp"]
    if npp is None or not len(npp):
        return pd.DataFrame()
    P = D["P_gl"][inc]
    Pa = P.groupby(P.index.year).sum()
    cols = [c for c in inc if c in npp.columns]
    rue = (npp[cols] * 1000.0) / Pa.reindex(npp.index)[cols]  # g C m-2 por mm
    rue.index.name = "anio"
    return rue.reset_index().melt(id_vars="anio", var_name="celda", value_name="rue_gC_m2_por_mm")


def match_episodes_across_products(ep: pd.DataFrame, ep_mod: pd.DataFrame) -> pd.DataFrame:
    """Para cada episodio IMERG: ¿hay un episodio con la lluvia del modelo que se solape (±2 meses) en la misma
    celda, y fue también contradicción A (raíz)? Si la contradicción solo aparece con IMERG → 'posible
    diferencia entre productos'."""
    rows = []
    for _, e in ep.iterrows():
        m = ep_mod[(ep_mod["celda"] == e["celda"]) & (ep_mod["inicio"] <= e["fin"] + pd.DateOffset(months=2))
                   & (ep_mod["fin"] >= e["inicio"] - pd.DateOffset(months=2))] if len(ep_mod) else ep_mod
        has = len(m) > 0
        contra_mod = bool((m["contradiccion_A_SM_RAIZ"] == True).any()) if has else False  # noqa: E712
        lab = None
        if e["contradiccion_A_SM_RAIZ"] == True:  # noqa: E712
            lab = "también con la lluvia del modelo" if contra_mod else "posible diferencia entre productos"
        rows.append({"celda": e["celda"], "inicio": e["inicio"], "episodio_en_lluvia_modelo": has,
                     "contradiccion_A_SM_RAIZ_lluvia_modelo": contra_mod, "contradiccion_A_SM_RAIZ_etiqueta": lab})
    return pd.DataFrame(rows)


def ensure_demo_matched(R: dict) -> None:
    """Asegura que el par elegido para la demo tenga su comparación de episodios emparejados."""
    from .figures import demo_pair
    dp = demo_pair(R)
    if dp is None:
        return
    a, b = dp["celda_a"], dp["celda_b"]
    key = f"{a}|{b}"
    if key in R["matched"]:
        return
    ep = R["ep"]
    m = episodes.matched_pair_episodes(ep[ep["celda"] == a].reset_index(drop=True),
                                       ep[ep["celda"] == b].reset_index(drop=True), resp="SM_RAIZ")
    R["matched"][key] = {"episodios": m, "resumen": [episodes.paired_summary(m, v) for v in
                                                      ("z_retorno", "meses_recuperacion", "fraccion_intensa", "max1d",
                                                       "z_antecedente", "meses_previos")] if len(m) else []}


def rerender(pkl: str) -> None:
    """Desarrollo: rehace salidas, figuras e informe desde el estado guardado con --cache (sin recalcular)."""
    import pickle
    from . import figures, report
    R = pickle.loads(Path(pkl).read_bytes())
    ensure_demo_matched(R)
    write_outputs(R, Path(R["args"]["resultados"]))
    figs = figures.make_all(R, Path(R["args"]["figuras"]))
    report.write(R, figs, Path(R["args"]["informe"]))


def contradiction_table(ep: pd.DataFrame, rev: list) -> pd.DataFrame:
    t = (ep.groupby("celda").agg(n_episodios=("inicio", "size"),
                                 n_con_retorno=("retorno_lluvia", lambda s: int(s.notna().sum())),
                                 n_A_raiz=("contradiccion_A_SM_RAIZ", lambda s: int((s == True).sum())),  # noqa: E712
                                 n_A_superficial=("contradiccion_A_SM_0_10", lambda s: int((s == True).sum())),  # noqa: E712
                                 mediana_meses_recuperacion_raiz=("meses_recuperacion_SM_RAIZ", "median"),
                                 n_recuperacion_censurada_raiz=("recuperacion_censurada_SM_RAIZ", "sum"))
         .reset_index())
    t = pd.DataFrame(rev).merge(t, on="celda", how="left")
    t["fraccion_A_raiz"] = t["n_A_raiz"] / t["n_con_retorno"].replace(0, np.nan)
    return t


def factor_table(ep, outcomes, B) -> pd.DataFrame:
    rows = []
    for oc, resp in outcomes:
        for f in episodes.FACTORS:
            col = f"z_antecedente_{resp}" if f == "z_antecedente" else f
            a = episodes.association(ep, oc, col, B=B)
            rows.append({"resultado": oc, "factor": f, "columna_factor": col, **a})
    df = pd.DataFrame(rows)
    df["q_bh"] = pstats.benjamini_hochberg(df["p"].tolist())
    df["n_pruebas_bh"] = int(df["p"].notna().sum())
    return df


def factor_sensitivity(ep, inc, spi, z, daily, outcomes, B) -> pd.DataFrame:
    rows = []

    def add(label, epx, within=False, joint=False):
        for oc, resp in outcomes:
            fcols = {f: (f"z_antecedente_{resp}" if f == "z_antecedente" else f) for f in episodes.FACTORS}
            for f, col in fcols.items():
                extra = [c for k, c in fcols.items() if k != f] if joint else []
                a = episodes.association(epx, oc, col, B=max(500, B // 4), within_cell=within, extra_factors=extra)
                rows.append({"variante": label, "resultado": oc, "factor": f, **a})

    add("efectos fijos de celda", ep, within=True)
    add("todos los factores juntos", ep, joint=True)
    for label, kw in (("p90 en lluvia intensa", {"heavy_q": 0.90}), ("sequías previas en 24 meses", {"prior_months": 24}),
                      ("retorno con SPI-3 >= -0.5", {"thr_return": -0.5}), ("contradicción con 3 meses", {"k": 3})):
        eps = []
        for c in inc:
            eps += episodes.cell_episodes(c, spi[3][c], {r: z[r][c] for r in SOIL},
                                          daily[c] if c in daily else None, responses=SOIL, **kw)
        add(label, pd.DataFrame(eps))
    return pd.DataFrame(rows)


def intensity_climatology(daily: pd.DataFrame, inc: list, args) -> pd.DataFrame:
    rows = []
    if not len(daily):
        return pd.DataFrame()
    for c in inc:
        d = daily[c].dropna()
        p95 = episodes.heavy_threshold(d)
        rows.append({"celda": c, "p95_dias_lluvia_mm": p95, "fraccion_lluvia_en_dias_p95": float(d[d > p95].sum() / d.sum()),
                     "max_anual_1dia_mediana_mm": float(d.groupby(d.index.year).max().median()),
                     "dias_lluvia_por_anio": float((d >= 1).groupby(d.index.year).sum().mean())})
    return pd.DataFrame(rows)


def province_block(D: dict, inc_im: list, inc: list) -> dict:
    pw_im = grid.province_weights(D["w_im"], D["cells_im"])
    pw_gl = grid.province_weights(D["w_gl"][D["w_gl"]["celda"].isin(D["cells_gl"].loc[D["cells_gl"]["tierra_gldas"], "celda"])],
                                  D["cells_gl"])
    P_prov = grid.province_series(D["P_im"], pw_im)
    soil = grid.province_series(D["GL"]["SM_RAIZ"], pw_gl)
    surf = grid.province_series(D["GL"]["SM_0_10"], pw_gl)
    spi3 = anomalies.spi_table(P_prov, 3)
    zr = anomalies.zscore(soil)
    zs = anomalies.zscore(surf)
    eps, rev = [], []
    for p in P_prov.columns:
        if p not in zr:
            continue
        eps += episodes.cell_episodes(p, spi3[p], {"SM_RAIZ": zr[p], "SM_0_10": zs[p]}, None, responses=SOIL)
        rev.append(episodes.reverse_counts(p, spi3[p], zr[p]))
    ep = pd.DataFrame(eps)
    contra = contradiction_table(ep, rev).rename(columns={"celda": "provincia"})
    cover = (pw_im.groupby("provincia").agg(celdas_imerg=("celda", "nunique"), area_km2=("peso", "sum")).reset_index()
             .merge(pw_gl.groupby("provincia").agg(celdas_gldas=("celda", "nunique")).reset_index(), on="provincia", how="left"))
    return {"P": P_prov, "SM_RAIZ": soil, "SM_0_10": surf, "spi3": spi3, "z_raiz": zr, "z_sup": zs,
            "ep": ep.rename(columns={"celda": "provincia"}), "contra": contra, "cobertura": cover,
            "pw_im": pw_im, "pw_gl": pw_gl}


def event_block(D: dict, args) -> dict:
    day = pd.Timestamp(args.evento)
    codes = set(args.evento_prov)
    w = D["w_im"]
    cover = sorted(w.loc[w["codigo"].isin(codes), "celda"].unique())
    daily = D["D_im"]
    res = {"fecha": day.date().isoformat(), "provincias": sorted(codes), "celdas_imerg_que_cubren": len(cover),
           "afirmacion_contrastada": ("431 mm en 24 h el sábado 18-nov-2023 en la estación de ONAMET Arroyo Hondo Viejo "
                                      "(dato preliminar; 474 mm acumulados desde el jueves). Es un pluviómetro (un punto); "
                                      "NASA no publicó una magnitud IMERG para este evento: todo valor IMERG aquí es cálculo "
                                      "nuestro sobre IMERG Final V07."),
           "nota": ("IMERG diario = día UTC (00-24 UTC = 20:00 del día anterior a 20:00 hora local). Una celda IMERG "
                    "de 0.1° (~10.5 × 10.6 km) promedia el aguacero sobre ~110 km²; un pluviómetro mide un punto. "
                    "Un solo evento no es una tendencia.")}
    per = []
    for c in cover:
        s = daily[c]
        e = extremes.event_in_distribution(s, args.evento)
        e2 = extremes.event_in_distribution(s, (day + pd.Timedelta(days=1)).date().isoformat())
        per.append({"celda": c, "mm_dia_utc_evento": e["valor_mm"], "mm_dia_utc_siguiente": e2["valor_mm"],
                    "mm_2_dias": e["valor_mm"] + e2["valor_mm"],
                    "puesto_entre_todos_los_dias": e["puesto_entre_todos_los_dias"],
                    "puesto_entre_maximos_anuales": e["puesto_entre_maximos_anuales"],
                    "periodo_retorno_empirico_anios": e["periodo_retorno_empirico_anios"],
                    "maximo_anual_mediana_mm": e["maximo_anual_mediana_mm"], "maximo_registro_mm": e["maximo_registro_mm"],
                    "fecha_maximo_registro": e["fecha_maximo_registro"], "n_dias": e["n_dias"]})
    per = pd.DataFrame(per).sort_values("mm_dia_utc_evento", ascending=False)
    res["por_celda"] = per
    best = per.iloc[0]["celda"]
    res["celda_max"] = best
    full = extremes.event_in_distribution(daily[best], args.evento)
    res["celda_max_detalle"] = full
    res["maximos_anuales_celda_max"] = full["maximos_anuales"]
    # máximos anuales de todas las celdas que cubren (para la figura)
    amax = daily[cover].groupby(daily.index.year).max()
    res["maximos_anuales_cobertura"] = amax
    HH = D["HH"]
    if len(HH):
        cov_hh = [c for c in cover if c in HH.columns]
        roll = HH[cov_hh].rolling(48, min_periods=46).sum()
        mx = roll.max()
        c_hh = mx.idxmax()
        t_end = roll[c_hh].idxmax()
        res["media_hora"] = {"celda": c_hh, "max_24h_movil_mm": float(mx.max()),
                             "fin_ventana_utc": (t_end + pd.Timedelta(minutes=30)).isoformat(),
                             "inicio_ventana_utc": (t_end - pd.Timedelta(hours=23, minutes=30)).isoformat(),
                             "max_30min_mm": float(HH[cov_hh].max().max()),
                             "medias_horas_faltantes": int(HH[cov_hh].isna().all(axis=1).sum()),
                             "max_24h_por_celda": mx.sort_values(ascending=False)}
        res["serie_hh_celda"] = HH[c_hh]
    return res


def grace_block(D: dict, args) -> pd.DataFrame | None:
    """GRACE/GRACE-FO (JPL mascons RL06.3 CRI, rejilla 0.5° pero resolución efectiva ~3°): media nacional del
    agua total (cm de espesor equivalente) ponderada por cos(lat) sobre las celdas 0.5° con ≥ 25 % en el país.
    Sin factores de ganancia. Solo contexto: RD cabe en 1-2 mascons."""
    f = Path(args.datos) / "grace" / "GRCTellus.JPL.200204_202609.GLO.RL06.3M.MSCNv04CRI.nc"
    if not f.exists():
        return None
    import h5py
    with h5py.File(f, "r") as h:
        lat = np.asarray(h["lat"][...], float)
        lon = np.asarray(h["lon"][...], float)
        lon = np.where(lon > 180, lon - 360, lon)
        b = boundaries.bounds(D["units"], 0.5)
        jj = np.flatnonzero((lat >= b[1]) & (lat <= b[3]))
        ii = np.flatnonzero((lon >= b[0]) & (lon <= b[2]))
        lwe = np.asarray(h["lwe_thickness"][:, jj.min():jj.max() + 1, ii.min():ii.max() + 1], float)
        unc = np.asarray(h["uncertainty"][:, jj.min():jj.max() + 1, ii.min():ii.max() + 1], float)
        t = np.asarray(h["time"][...], float)
    sub = grid.Grid("GRACE 0.5°", 0.5, lat[jj.min():jj.max() + 1], np.sort(lon[ii.min():ii.max() + 1]))
    if not np.all(np.diff(lon[ii.min():ii.max() + 1]) > 0):
        return None
    cells, _ = grid.fractions(sub, D["units"], D["others"], n=20)
    w = (cells["frac_pais"].to_numpy() * np.cos(np.radians(cells["lat"].to_numpy())))
    w = np.where(cells["frac_pais"].to_numpy() >= 0.25, w, 0.0).reshape(sub.lat.size, sub.lon.size)
    dates = pd.Timestamp("2002-01-01") + pd.to_timedelta(t, unit="D")
    tws = (lwe * w[None]).sum((1, 2)) / w.sum()
    un = (unc * w[None]).sum((1, 2)) / w.sum()
    out = pd.DataFrame({"fecha": dates.normalize(), "tws_cm": tws, "incertidumbre_cm": un,
                        "celdas_0_5_usadas": int((w > 0).sum())})
    return out[(out["fecha"].dt.year >= args.anio0) & (out["fecha"].dt.year <= args.anio1)].reset_index(drop=True)


def power_crosscheck(D: dict, args, spi3_gl: pd.DataFrame, zroot_gl: pd.DataFrame, cells_gl: pd.DataFrame,
                     inc: list) -> dict:
    """POWER (MERRA-2) frente a IMERG/GLDAS en las celdas POWER incluidas: misma lluvia y mismo suelo?"""
    pdir = Path(args.datos) / "power"
    fp, fr = pdir / f"mensual_{args.pais}_PRECTOTCORR_{args.anio0}_{args.anio1}.json", pdir / f"mensual_{args.pais}_GWETROOT_{args.anio0}_{args.anio1}.json"
    if not (fp.exists() and fr.exists()):
        return {"disponible": False}
    pp, meta = power.parse_regional_monthly(power.load_json(fp), "PRECTOTCORR")
    gr, _ = power.parse_regional_monthly(power.load_json(fr), "GWETROOT")
    Ppw = anomalies.monthly_total_mm(pp)
    rows = []
    ci = D["cells_im"]
    for cid, (lat, lon, _) in sorted(meta.items()):
        sel_im = ci[(ci["incluida"]) & ((ci["lat"] - lat).abs() < region.DLAT / 2) & ((ci["lon"] - lon).abs() < region.DLON / 2)]
        sel_gl = cells_gl[cells_gl["celda"].isin(inc) & ((cells_gl["lat"] - lat).abs() < region.DLAT / 2)
                          & ((cells_gl["lon"] - lon).abs() < region.DLON / 2)]
        if len(sel_im) < 5 or len(sel_gl) < 1:
            continue
        pim = D["P_im"][sel_im["celda"]].mean(axis=1)
        s1, s2 = drought.spi(pim, 3), drought.spi(Ppw[cid], 3)
        d = pd.DataFrame({"a": s1, "b": s2}).dropna()
        zg = anomalies.robust_z(D["GL"]["SM_RAIZ"][sel_gl["celda"]].mean(axis=1).to_frame("g"))["g"]
        zp = anomalies.robust_z(gr[[cid]])[cid]
        d2 = pd.DataFrame({"a": zg, "b": zp}).dropna()
        rows.append({"celda_power": cid, "celdas_imerg": int(len(sel_im)), "celdas_gldas": int(len(sel_gl)),
                     "r_spi3_imerg_vs_merra2": float(np.corrcoef(d["a"], d["b"])[0, 1]),
                     "r_z_raiz_gldas_vs_merra2": float(np.corrcoef(d2["a"], d2["b"])[0, 1]),
                     "lluvia_anual_imerg_mm": float(pim.groupby(pim.index.year).sum().mean()),
                     "lluvia_anual_merra2_mm": float(Ppw[cid].groupby(Ppw.index.year).sum().mean())})
    t = pd.DataFrame(rows)
    return {"disponible": True, "tabla": t,
            "mediana_r_spi3": float(t["r_spi3_imerg_vs_merra2"].median()) if len(t) else None,
            "mediana_r_z_raiz": float(t["r_z_raiz_gldas_vs_merra2"].median()) if len(t) else None}


# ------------------------------------------------------------------ salidas

def write_outputs(R: dict, rdir: Path) -> None:
    D = R["D"]
    pq = rdir / "parquet"
    pq.mkdir(parents=True, exist_ok=True)
    write_csv(rdir / "celdas_gldas.csv", D["cells_gl"])
    write_csv(rdir / "celdas_imerg.csv", D["cells_im"])
    write_csv(rdir / "pesos_provincia_imerg.csv", D["w_im"])
    write_csv(rdir / "pesos_provincia_gldas.csv", D["w_gl"])
    write_csv(rdir / "tendencias_celdas.csv", R["trends"])
    write_json(rdir / "calibracion_tendencias.json", R["cal_tr"])
    write_csv(rdir / "calibracion_pares_resumen.csv", R["null_sum"])
    write_csv(rdir / "acople_memoria_celdas.csv", R["cm"].point)
    write_csv(rdir / "perfil_lags.csv", R["lagp"])
    write_csv(rdir / "estado_antecedente.csv", R["ante"])
    write_csv(rdir / "pares_candidatos.csv", R["pairs"])
    write_csv(rdir / "pruebas_pares.csv", R["tests"])
    write_csv(rdir / "sensibilidad_pares.csv", R["sens"])
    write_csv(rdir / "contrastes_ranking.csv", R["ranked"])
    write_csv(rdir / "episodios.csv", R["ep"])
    write_csv(rdir / "contradicciones_por_celda.csv", R["contra"])
    write_csv(rdir / "factores_asociacion.csv", R["fac"])
    write_csv(rdir / "factores_sensibilidad.csv", R["fsens"])
    write_csv(rdir / "intensidad_lluvia_celdas.csv", R["icl"])
    write_csv(rdir / "latigazos_por_celda.csv", R["whip"])
    if R["grace"] is not None:
        write_csv(rdir / "grace_contexto_nacional.csv", R["grace"])
    if len(R["ep_mod"]):
        write_csv(rdir / "episodios_lluvia_modelo.csv", R["ep_mod"])
    if len(R["rue"]):
        write_csv(rdir / "eficiencia_uso_lluvia.csv", R["rue"])
    for k, v in R["matched"].items():
        write_csv(rdir / f"episodios_emparejados_{k.replace('|', '__')}.csv", v["episodios"])
    write_json(rdir / "episodios_emparejados_resumen.json", {k: v["resumen"] for k, v in R["matched"].items()})
    pr = R["prov"]
    write_csv(rdir / "provincias_contradicciones.csv", pr["contra"])
    write_csv(rdir / "provincias_episodios.csv", pr["ep"])
    write_csv(rdir / "provincias_cobertura.csv", pr["cobertura"])
    if R["xval"].get("disponible"):
        write_csv(rdir / "comparacion_power_merra2.csv", R["xval"]["tabla"])
    ev = R["event"]
    if ev is not None:
        evj = {k: v for k, v in ev.items() if k not in ("por_celda", "maximos_anuales_cobertura", "serie_hh_celda")}
        if "media_hora" in evj:
            evj["media_hora"] = {k: v for k, v in evj["media_hora"].items() if k != "max_24h_por_celda"}
        write_json(rdir / "evento_santo_domingo_2023-11-18.json", evj)
        write_csv(rdir / "evento_santo_domingo_por_celda.csv", ev["por_celda"])

    # ---- Parquet ordenado (tidy)
    def long(df, name, rejilla):
        d = df.copy()
        d.index.name = "fecha"
        return d.reset_index().melt(id_vars="fecha", var_name="celda", value_name="valor").assign(variable=name, rejilla=rejilla)

    parts = [long(R["P"], "P_mm_imerg_remapeada", "GLDAS 0.25°"), long(R["spi"][3], "SPI3", "GLDAS 0.25°"),
             long(R["spi"][1], "SPI1", "GLDAS 0.25°"), long(R["spi"][6], "SPI6", "GLDAS 0.25°")]
    for r in R["responses"]:
        parts += [long(R["raw"][r], r, "GLDAS 0.25°"), long(R["z"][r], f"z_{r}", "GLDAS 0.25°")]
    panel = pd.concat(parts, ignore_index=True)
    panel = panel[["fecha", "rejilla", "celda", "variable", "valor"]].sort_values(["variable", "celda", "fecha"])
    panel.to_parquet(pq / "panel_celdas_gldas_mensual.parquet", index=False)
    im = pd.concat([long(D["P_im"][R["inc_im"]], "P_mm", "IMERG 0.1°"), long(R["spi_im3"], "SPI3", "IMERG 0.1°")],
                   ignore_index=True)[["fecha", "rejilla", "celda", "variable", "valor"]]
    im.to_parquet(pq / "panel_celdas_imerg_mensual.parquet", index=False)
    pv = pd.concat([long(pr[k], n, "provincia") for k, n in (("P", "P_mm"), ("spi3", "SPI3"), ("SM_RAIZ", "SM_RAIZ"),
                                                              ("z_raiz", "z_SM_RAIZ"), ("SM_0_10", "SM_0_10"),
                                                              ("z_sup", "z_SM_0_10"))], ignore_index=True)
    pv = pv.rename(columns={"celda": "provincia"})[["fecha", "provincia", "variable", "valor"]]
    pv.to_parquet(pq / "provincias_mensual.parquet", index=False)
    # métricas por celda (una fila por celda GLDAS incluida)
    met = D["cells_gl"][D["cells_gl"]["incluida"]].copy()
    cmw = R["cm"].point.pivot_table(index="celda", columns=["respuesta", "metrica"], values="valor")
    cmw.columns = [f"{m}_{r}" for r, m in cmw.columns]
    met = met.merge(cmw.reset_index(), on="celda", how="left")
    trw = R["trends"][R["trends"]["variable"].isin(["SM_RAIZ", "SM_0_10", "TAIRE", "ET"])].pivot_table(
        index="celda", columns="variable", values=["pendiente_decada", "q_bh", "q_bh_empirico"])
    trw.columns = [f"tendencia_{v}_{m}" for m, v in trw.columns]
    met = (met.merge(trw.reset_index(), on="celda", how="left").merge(R["contra"], on="celda", how="left")
           .merge(R["whip"], on="celda", how="left"))
    if len(R["icl"]):
        met = met.merge(R["icl"], on="celda", how="left")
    met.to_parquet(pq / "metricas_celdas_gldas.parquet", index=False)
    mi = D["cells_im"][D["cells_im"]["incluida"]].merge(
        R["trends"][R["trends"]["variable"] == "PRECIP_IMERG_0.1"].drop(columns=["variable"]), on="celda", how="left")
    mi.to_parquet(pq / "metricas_celdas_imerg.parquet", index=False)
    man = D["man"].data
    mrows = [{"archivo": k, **{kk: (json.dumps(vv, ensure_ascii=False) if isinstance(vv, (list, dict)) else vv)
                              for kk, vv in v.items()}} for k, v in man["archivos"].items()]
    mdf = pd.DataFrame(mrows)
    for c in mdf.columns:
        mdf[c] = mdf[c].astype("string")
    mdf.to_parquet(pq / "manifiesto.parquet", index=False)
    write_json(rdir / "corrida.json", {
        "pais": R["args"]["pais"], "anios": [R["args"]["anio0"], R["args"]["anio1"]],
        "celdas_imerg_caja": int(len(D["cells_im"])), "celdas_imerg_incluidas": int(len(R["inc_im"])),
        "celdas_imerg_tocan_pais": int((D["cells_im"]["frac_pais"] > 0).sum()),
        "celdas_gldas_caja": int(len(D["cells_gl"])), "celdas_gldas_incluidas": int(len(R["inc"])),
        "celdas_gldas_tocan_pais": int((D["cells_gl"]["frac_pais"] > 0).sum()),
        "celdas_gldas_tierra_tocan_pais": int(((D["cells_gl"]["frac_pais"] > 0) & D["cells_gl"]["tierra_gldas"]).sum()),
        "meses_imerg_faltantes": [d.strftime("%Y-%m") for d in D["P_im"].index[D["P_im"].isna().all(axis=1)]],
        "dias_imerg": int(len(D["D_im"])), "dias_imerg_faltantes": int(D["D_im"].isna().all(axis=1).sum()) if len(D["D_im"]) else None,
        "respuestas": R["responses"], "ajustes_principales": R["settings"].__dict__,
        "variantes_sensibilidad": R["variants"], "n_pruebas_pares": int(R["tests"]["p"].notna().sum()),
        "n_pruebas_pares_q05_nominal": int((R["tests"]["q_bh"] < 0.05).sum()),
        "n_pruebas_pares_q05_calibrado": int((R["tests"]["q_bh_calibrado"] < 0.05).sum()),
        "pares_lluvia_parecida": int(R["pairs"]["lluvia_parecida"].sum()), "pares_candidatos": int(len(R["pairs"])),
        "pares_usados_en_calibracion": [list(p) for p in R["pares_calibracion"]],
        "limites_adm1": {k: R["D"]["adm1_meta"].get(k) for k in ("boundaryID", "boundarySource", "boundaryLicense",
                                                                    "boundaryYearRepresented", "admUnitCount", "gjDownloadURL")},
        "lluvia_forzamiento_gldas_disponible": bool(R["has_mod"]),
        "imerg_version": "IMERG Final V07 (archivos V07B); la serie mensual Final llega hasta 2025-09, aquí se usa 2001-2024",
        "appeears": sorted(R["D"]["extra"]) or "no hay GeoTIFF de AppEEARS en data/appeears/nacional (gancho listo)",
    })


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pais", default="DOM")
    ap.add_argument("--anio0", type=int, default=2001)
    ap.add_argument("--anio1", type=int, default=2024)
    ap.add_argument("--min-frac", dest="min_frac", type=float, default=region.MIN_FRAC)
    ap.add_argument("--datos", default="data/nacional")
    ap.add_argument("--appeears", default="data/appeears/nacional")
    ap.add_argument("--resultados", default="results/nacional")
    ap.add_argument("--figuras", default="figures/nacional")
    ap.add_argument("--informe", default="reports_nacional/EARTH_MEMORY.md")
    ap.add_argument("--evento", default="2023-11-18")
    ap.add_argument("--evento-prov", dest="evento_prov", nargs="+", default=["DO-01", "DO-32"],
                    help="códigos ISO de provincia (geoBoundaries shapeISO) que cubre el evento")
    ap.add_argument("--B", type=int, default=2000)
    ap.add_argument("--n-surr", dest="n_surr", type=int, default=1000)
    ap.add_argument("--n-surr-pares", dest="n_surr_pares", type=int, default=100)
    ap.add_argument("--pares-calib", dest="pares_calib", type=int, default=30)
    ap.add_argument("--cache", default=None, help="(desarrollo) guarda el estado en un pickle")
    run(ap.parse_args(argv))


if __name__ == "__main__":
    main()
