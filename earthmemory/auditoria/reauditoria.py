"""Re-auditoría de "50 de 96 episodios = posible diferencia entre productos".

Definición exacta en el código del motor nacional (earthmemory/episodes.py + nacional.match_episodes_across_products):
- Celda = celda GLDAS 0.25° incluida (65). Lluvia = IMERG mensual remapeada de forma conservativa a la celda.
- Episodio = racha de SPI-3 <= −1 durante >= 2 meses. Retorno = primer mes posterior con SPI-3 >= 0 (antes
  del siguiente episodio).
- Contradicción A (raíz) = z robusto de la humedad de la zona de raíces GLDAS < −1 en el mes de retorno y el
  siguiente.
- Etiqueta: se repite TODO con la lluvia que forzó a GLDAS-2.1 (Rainf_f_tavg, GPCP 1DD desagregado). Si en la
  misma celda hay un episodio de esa lluvia que se solapa (±2 meses) y también es contradicción A → "también con
  la lluvia del modelo"; si no → "posible diferencia entre productos". OJO: la humedad del suelo es la MISMA serie
  en las dos ramas; la etiqueta solo cambia por la lluvia (¿hubo sequía? ¿en qué mes volvió?).

Descomposición (no excluyentes; además se atribuye en orden a → b → c):
(a) escala: se recuenta a 0.5° (bloques de 2 × 2 celdas GLDAS; suelo promediado y z recalculado). A 0.1° no se
    puede: GLDAS no tiene información por debajo de 0.25°.
(b) tiempo: IMERG mensual rehecho desde IMERG diario con el día desplazado ±1 (cota superior del efecto
    UTC frente a hora local, que es de 4 h) y tolerancia de ±1 mes en el mes de retorno.
(c) variable/umbral: la contradicción aparece con la lluvia del modelo si se relajan los umbrales (episodio
    SPI-3 <= −0.8, retorno SPI-3 >= −0.25) o el SPI-3 mínimo del modelo quedó a < 0.2 del umbral.
Además: CHIRPS como tercer producto (¿se pone del lado de IMERG o del forzamiento?).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats as sstats

from .. import anomalies, episodes
from ..nacional import match_episodes_across_products
from . import datos

SOIL = ("SM_RAIZ", "SM_0_10")
RES = "results/nacional"


def load_panel():
    p = pd.read_parquet(f"{RES}/parquet/panel_celdas_gldas_mensual.parquet")
    piv = {v: p[p["variable"] == v].pivot(index="fecha", columns="celda", values="valor").sort_index()
           for v in ("SPI3", "z_SM_RAIZ", "z_SM_0_10", "SM_RAIZ", "SM_0_10", "P_mm_imerg_remapeada")}
    for v in piv.values():
        v.index = pd.to_datetime(v.index)
    return piv


def episodes_for(spi3: pd.DataFrame, z: dict, cells, thr_ep=-1.0, thr_ret=0.0) -> pd.DataFrame:
    rows = []
    for c in cells:
        s = spi3[c]
        if thr_ep != -1.0:  # umbral de episodio relajado: se reescala para reutilizar runs_below(-1)
            s = s / abs(thr_ep)
            rows += episodes.cell_episodes(c, s, {r: z[r][c] for r in SOIL}, None, thr_return=thr_ret / abs(thr_ep),
                                           responses=SOIL)
        else:
            rows += episodes.cell_episodes(c, s, {r: z[r][c] for r in SOIL}, None, thr_return=thr_ret, responses=SOIL)
    return pd.DataFrame(rows)


def label(ep: pd.DataFrame, ep_mod: pd.DataFrame) -> pd.DataFrame:
    m = match_episodes_across_products(ep, ep_mod)
    return ep.merge(m, on=["celda", "inicio"], how="left")


def coarse_blocks(cells: list) -> dict:
    """celda 0.25 → bloque 0.5 (bordes en múltiplos de 0.5)."""
    out = {}
    for c in cells:
        la, lo = map(float, c.split("_"))
        bl = np.floor(la / 0.5) * 0.5 + 0.25
        bo = np.floor(lo / 0.5) * 0.5 + 0.25
        out[c] = f"{bl:.3f}_{bo:.3f}"
    return out


def chirps_to_gldas(g: datos.G05, cells: list) -> pd.DataFrame:
    """CHIRPS mensual 0.05 → celdas 0.25 (media ponderada por fracción en RD de cada subcelda 0.05)."""
    ch = datos.chirps_monthly()
    P = ch["P"]
    out = {}
    for c in cells:
        la, lo = map(float, c.split("_"))
        mi = (np.abs(g.lat - la) < 0.125 - 1e-6)
        mj = (np.abs(g.lon - lo) < 0.125 - 1e-6)
        w = g.frac_rd[np.ix_(mi, mj)]
        X = P[:, mi][:, :, mj]
        ok = np.isfinite(X) & (w[None] > 0)
        out[c] = np.where(ok, X * w[None], 0).sum((1, 2)) / np.where(ok, w[None], 0).sum((1, 2))
    return pd.DataFrame(out, index=ch["meses"])


def imerg_monthly_shifted(g: datos.G05, cells: list, k: int) -> pd.DataFrame:
    """IMERG diario con el calendario desplazado k días → mensual → celdas 0.25 (pesos fracción RD)."""
    d = datos.imerg_daily()
    I, J = datos.nest_index(d["lat"], d["lon"], 0.1, 0.1, g)
    dias = d["dias"] + pd.Timedelta(days=k)
    M = datos.monthly_from_daily(d["P"], dias)
    meses = pd.date_range(f"{dias[0].year}-{dias[0].month:02d}-01", periods=M.shape[0], freq="MS")
    M05 = datos.to05(M, I, J)
    out = {}
    for c in cells:
        la, lo = map(float, c.split("_"))
        mi = (np.abs(g.lat - la) < 0.125 - 1e-6)
        mj = (np.abs(g.lon - lo) < 0.125 - 1e-6)
        w = g.frac_rd[np.ix_(mi, mj)]
        X = M05[:, mi][:, :, mj]
        ok = np.isfinite(X) & (w[None] > 0)
        out[c] = np.where(ok, X * w[None], 0).sum((1, 2)) / np.where(ok, w[None], 0).sum((1, 2))
    df = pd.DataFrame(out, index=meses)
    return df.loc["2001-01-01":"2024-12-01"]


def overlap(ep2: pd.DataFrame, cell, ini, fin, gap=2) -> pd.DataFrame:
    return ep2[(ep2["celda"] == cell) & (ep2["inicio"] <= fin + pd.DateOffset(months=gap))
               & (ep2["fin"] >= ini - pd.DateOffset(months=gap))]


def run(g: datos.G05, oni: pd.Series | None) -> dict:
    piv = load_panel()
    cells = sorted(piv["SPI3"].columns)
    z = {"SM_RAIZ": piv["z_SM_RAIZ"], "SM_0_10": piv["z_SM_0_10"]}
    gf = datos.gldas_forcing()
    gid = [f"{a:.3f}_{b:.3f}" for a in gf["lat"] for b in gf["lon"]]
    Pmod = pd.DataFrame(gf["P"].reshape(gf["P"].shape[0], -1), index=gf["meses"], columns=gid)[cells]
    spi_mod = anomalies.spi_table(Pmod, 3)

    # 0) reproducir la cuenta original
    ep = label(episodes_for(piv["SPI3"], z, cells), episodes_for(spi_mod, z, cells))
    A = ep[ep["contradiccion_A_SM_RAIZ"] == True].copy()  # noqa: E712
    n96 = len(A)
    n50 = int((A["contradiccion_A_SM_RAIZ_etiqueta"] == "posible diferencia entre productos").sum())
    orig = pd.read_csv(f"{RES}/episodios.csv", parse_dates=["inicio", "fin"])
    n96_orig = int((orig["contradiccion_A_SM_RAIZ"] == True).sum())  # noqa: E712
    n50_orig = int((orig["contradiccion_A_SM_RAIZ_etiqueta"] == "posible diferencia entre productos").sum())

    # (a) escala 0.5°
    blk = coarse_blocks(cells)
    bl_cells = sorted(set(blk.values()))
    raw = {r: piv[r].T.groupby(pd.Series(blk)).mean().T for r in ("SM_RAIZ", "SM_0_10")}
    z05 = {r: anomalies.zscore(raw[r], "robusta") for r in raw}
    P05 = piv["P_mm_imerg_remapeada"].T.groupby(pd.Series(blk)).mean().T
    Pm05 = Pmod.T.groupby(pd.Series(blk)).mean().T
    ep05 = label(episodes_for(anomalies.spi_table(P05, 3), z05, bl_cells),
                 episodes_for(anomalies.spi_table(Pm05, 3), z05, bl_cells))
    # (b) tiempo: IMERG mensual desde el diario, sin desplazar y con ±1 día (misma ruta de cálculo)
    lab_shift = {}
    for k in (0, -1, 1):
        Pk = imerg_monthly_shifted(g, cells, k)
        lab_shift[k] = label(episodes_for(anomalies.spi_table(Pk, 3), z, cells), episodes_for(spi_mod, z, cells))
    # (c) umbrales relajados con la lluvia del modelo
    ep_mod = episodes_for(spi_mod, z, cells)
    ep_mod_rel = episodes_for(spi_mod, z, cells, thr_ep=-0.8, thr_ret=-0.25)
    # tercer producto: CHIRPS
    Pch = chirps_to_gldas(g, cells)
    ep_ch = episodes_for(anomalies.spi_table(Pch, 3), z, cells)

    rows = []
    for _, e in A.iterrows():
        c, ini, fin, tret = e["celda"], e["inicio"], e["fin"], e["retorno_lluvia"]
        mism = e["contradiccion_A_SM_RAIZ_etiqueta"] == "posible diferencia entre productos"
        w = (spi_mod.index >= ini - pd.DateOffset(months=2)) & (spi_mod.index <= fin + pd.DateOffset(months=2))
        mod_min = float(spi_mod.loc[w, c].min())
        om = overlap(ep_mod, c, ini, fin)
        mod_ret = om["retorno_lluvia"].dropna()
        gap_ret = (min(abs((r.year - tret.year) * 12 + r.month - tret.month) for r in mod_ret)
                   if len(mod_ret) and pd.notna(tret) else np.nan)
        # (a) 0.5°
        b = blk[c]
        o5 = overlap(ep05, b, ini, fin)
        a05_im = bool((o5["contradiccion_A_SM_RAIZ"] == True).any())  # noqa: E712
        a05_mod = bool((o5["contradiccion_A_SM_RAIZ_lluvia_modelo"] == True).any())  # noqa: E712
        acuerdo_05 = a05_im == a05_mod if len(o5) else False
        # (b) desplazamientos de 1 día
        res_k = {}
        for k, L in lab_shift.items():
            o = overlap(L, c, ini, fin, gap=0)
            a_im = bool((o["contradiccion_A_SM_RAIZ"] == True).any())  # noqa: E712
            a_md = bool((o["contradiccion_A_SM_RAIZ_lluvia_modelo"] == True).any())  # noqa: E712
            res_k[k] = (a_im, a_md)
        cambia_dia = any(res_k[k] != res_k[0] for k in (-1, 1)) and any(v[0] == v[1] for v in res_k.values())
        tol_mes = bool(pd.notna(gap_ret) and gap_ret <= 1)
        # (c) umbral
        orel = overlap(ep_mod_rel, c, ini, fin)
        rel = bool((orel["contradiccion_A_SM_RAIZ"] == True).any())  # noqa: E712
        frontera = bool(-1.2 < mod_min <= -0.8) if np.isfinite(mod_min) else False
        # CHIRPS
        oc = overlap(ep_ch, c, ini, fin)
        ch_a = bool((oc["contradiccion_A_SM_RAIZ"] == True).any())  # noqa: E712
        rows.append({"celda": c, "inicio": ini.date(), "fin": fin.date(),
                     "retorno_imerg": tret.date() if pd.notna(tret) else None, "etiqueta_original": e["contradiccion_A_SM_RAIZ_etiqueta"],
                     "posible_diferencia": mism, "spi3_min_imerg": e["spi3_min"], "spi3_min_modelo_ventana": mod_min,
                     "episodio_en_modelo": bool(len(om)), "dif_meses_retorno_modelo": gap_ret,
                     "a_escala_05_acuerdo": acuerdo_05, "a05_imerg": a05_im, "a05_modelo": a05_mod,
                     "b_desplazamiento_1dia_cambia": cambia_dia,
                     "b_imerg_desde_diario_k0": res_k[0][0], "b_tolerancia_retorno_1mes": tol_mes,
                     "c_aparece_con_umbral_relajado": rel, "c_modelo_cerca_del_umbral": frontera,
                     "chirps_tambien_contradiccion": ch_a,
                     "anio_fin": fin.year, "mes_retorno": tret.month if pd.notna(tret) else np.nan})
    D = pd.DataFrame(rows)
    mm = D[D["posible_diferencia"]].copy()
    mm["explica_a"] = mm["a_escala_05_acuerdo"]
    mm["explica_b"] = mm["b_desplazamiento_1dia_cambia"] | mm["b_tolerancia_retorno_1mes"]
    mm["explica_c"] = mm["c_aparece_con_umbral_relajado"] | mm["c_modelo_cerca_del_umbral"]
    mm["causa_atribuida"] = np.select([mm["explica_a"], mm["explica_b"], mm["explica_c"]],
                                      ["a_escala", "b_tiempo", "c_variable_umbral"], "sin_explicar")
    D = D.merge(mm[["celda", "inicio", "explica_a", "explica_b", "explica_c", "causa_atribuida"]],
                on=["celda", "inicio"], how="left")
    un = mm[mm["causa_atribuida"] == "sin_explicar"]
    summary = {"definicion": __doc__.split("Descomposición")[0].strip(),
               "reproduccion": {"n_A_original": n96_orig, "n_posible_diferencia_original": n50_orig,
                                "n_A_reproducido": n96, "n_posible_diferencia_reproducido": n50},
               "n_posible_diferencia": int(len(mm)),
               "explica_a_escala": int(mm["explica_a"].sum()), "explica_b_tiempo": int(mm["explica_b"].sum()),
               "explica_b_desplazamiento_dia": int(mm["b_desplazamiento_1dia_cambia"].sum()),
               "explica_b_tolerancia_mes": int(mm["b_tolerancia_retorno_1mes"].sum()),
               "explica_c_variable_umbral": int(mm["explica_c"].sum()),
               "atribucion_secuencial": mm["causa_atribuida"].value_counts().to_dict(),
               "sin_explicar": int(len(un)),
               "sin_explicar_chirps_con_imerg": int(un["chirps_tambien_contradiccion"].sum()),
               "sin_explicar_chirps_con_modelo": int((~un["chirps_tambien_contradiccion"]).sum()),
               "todos_50_chirps_con_imerg": int(mm["chirps_tambien_contradiccion"].sum()),
               "recuento_05": {"bloques": len(bl_cells),
                               "n_A_imerg_05": int((ep05["contradiccion_A_SM_RAIZ"] == True).sum()),  # noqa: E712
                               "n_posible_diferencia_05": int((ep05["contradiccion_A_SM_RAIZ_etiqueta"] == "posible diferencia entre productos").sum())},
               "recuento_desde_diario": {str(k): {"n_A": int((L["contradiccion_A_SM_RAIZ"] == True).sum()),  # noqa: E712
                                                  "n_posible_diferencia": int((L["contradiccion_A_SM_RAIZ_etiqueta"] == "posible diferencia entre productos").sum())}
                                         for k, L in lab_shift.items()},
               "n_A_con_chirps": int((ep_ch["contradiccion_A_SM_RAIZ"] == True).sum())}  # noqa: E712

    # (d) relieve y costa, (e) persistencia, (f) representatividad
    cellinfo = cell_covariates(g, cells)
    disc = 1 - pd.Series({c: piv["SPI3"][c].corr(spi_mod[c]) for c in cells})
    cellinfo["desacuerdo_spi3_imerg_vs_modelo"] = disc
    cellinfo["n_posible_diferencia"] = mm.groupby("celda").size().reindex(cells).fillna(0)
    cellinfo["n_sin_explicar"] = un.groupby("celda").size().reindex(cells).fillna(0)
    terr = terrain_tests(g, cellinfo, cells)
    pers = persistence(D, ep)
    rep = representativeness(ep, oni)
    return {"tabla": D, "resumen": summary, "celdas": cellinfo, "relieve": terr, "persistencia": pers,
            "representatividad": rep, "spi_mod": spi_mod, "spi_imerg": piv["SPI3"]}


def cell_covariates(g: datos.G05, cells) -> pd.DataFrame:
    coast = g.coast_km()
    rows = []
    for c in cells:
        la, lo = map(float, c.split("_"))
        mi = (np.abs(g.lat - la) < 0.125 - 1e-6)
        mj = (np.abs(g.lon - lo) < 0.125 - 1e-6)
        land = g.frac_rd[np.ix_(mi, mj)] > 0.5
        rows.append({"celda": c, "lat": la, "lon": lo,
                     "elevacion_m": float(np.nanmean(g.elev[np.ix_(mi, mj)][land])) if land.any() else np.nan,
                     "pendiente_grados": float(np.nanmean(g.slope[np.ix_(mi, mj)][land])) if land.any() else np.nan,
                     "dist_costa_km": float(np.nanmean(coast[np.ix_(mi, mj)][land])) if land.any() else np.nan})
    return pd.DataFrame(rows).set_index("celda")


def terrain_tests(g: datos.G05, info: pd.DataFrame, cells, n_surr: int = 999, seed: int = 31) -> pd.DataFrame:
    """ρ de Spearman entre desacuerdo y covariables; p calibrado con desplazamientos toroidales del campo de la
    covariable (conserva su autocorrelación espacial). Campo en una caja 0.25° que cubre las celdas."""
    rng = np.random.default_rng(seed)
    lats = np.round(np.arange(info["lat"].min(), info["lat"].max() + 0.01, 0.25), 3)
    lons = np.round(np.arange(info["lon"].min(), info["lon"].max() + 0.01, 0.25), 3)
    ii = {v: k for k, v in enumerate(lats)}
    jj = {v: k for k, v in enumerate(lons)}
    pos = np.array([(ii[round(r.lat, 3)], jj[round(r.lon, 3)]) for r in info.itertuples()])
    rows = []
    for ycol in ("desacuerdo_spi3_imerg_vs_modelo", "n_posible_diferencia", "n_sin_explicar"):
        y = info[ycol].to_numpy(float)
        for xcol in ("elevacion_m", "pendiente_grados", "dist_costa_km"):
            F = np.full((lats.size, lons.size), np.nan)
            F[pos[:, 0], pos[:, 1]] = info[xcol].to_numpy(float)
            x = F[pos[:, 0], pos[:, 1]]
            ok = np.isfinite(x) & np.isfinite(y)
            rho = sstats.spearmanr(x[ok], y[ok]).statistic
            null = []
            for _ in range(n_surr * 3):
                di, dj = rng.integers(0, lats.size), rng.integers(0, lons.size)
                xs = np.roll(np.roll(F, di, 0), dj, 1)[pos[:, 0], pos[:, 1]]
                okk = np.isfinite(xs) & np.isfinite(y)
                if okk.sum() < 0.7 * ok.sum() or (di == 0 and dj == 0):
                    continue
                null.append(sstats.spearmanr(xs[okk], y[okk]).statistic)
                if len(null) >= n_surr:
                    break
            null = np.asarray(null)
            p_emp = (1 + np.sum(np.abs(null) >= abs(rho))) / (1 + null.size) if null.size else np.nan
            rows.append({"resultado": ycol, "covariable": xcol, "n_celdas": int(ok.sum()), "rho_spearman": rho,
                         "p_nominal": sstats.spearmanr(x[ok], y[ok]).pvalue, "p_toroidal": p_emp,
                         "n_sustitutos": int(null.size)})
    return pd.DataFrame(rows)


def persistence(D: pd.DataFrame, ep: pd.DataFrame, n_perm: int = 4999, seed: int = 5) -> dict:
    """¿Los 50 se concentran en ciertos años o celdas más de lo que daría reetiquetar al azar los 96?"""
    rng = np.random.default_rng(seed)
    lab = D["posible_diferencia"].to_numpy(bool)
    yr = D["anio_fin"].to_numpy()
    cell = D["celda"].to_numpy()

    def stat(l):
        by_y = pd.Series(l).groupby(yr).mean()
        tot = pd.Series(np.ones_like(l)).groupby(yr).sum()
        frac_top = by_y[tot >= 3].max() if (tot >= 3).any() else np.nan
        rep_cells = (pd.Series(l).groupby(cell).sum() >= 2).sum()
        return frac_top, rep_cells
    obs = stat(lab)
    perms = np.array([stat(rng.permutation(lab)) for _ in range(n_perm)])
    by_year = D.groupby("anio_fin").agg(n_A=("celda", "size"), n_posible_diferencia=("posible_diferencia", "sum"))
    return {"por_anio": by_year.reset_index().to_dict(orient="records"),
            "max_fraccion_anual_obs": float(obs[0]),
            "p_perm_max_fraccion_anual": float((1 + np.sum(perms[:, 0] >= obs[0])) / (1 + n_perm)),
            "celdas_con_2mas_obs": int(obs[1]),
            "p_perm_celdas_repetidas": float((1 + np.sum(perms[:, 1] >= obs[1])) / (1 + n_perm)),
            "nota": "permutación de la etiqueta entre los 96 episodios A (conserva cuántos hay por año y celda)"}


def representativeness(ep: pd.DataFrame, oni: pd.Series | None, n_perm: int = 4999, seed: int = 9) -> pd.DataFrame:
    """¿Los episodios A (96) y los 'posible diferencia' (50) cubren regiones, estaciones y fases ENSO como el
    conjunto de todos los episodios con retorno de lluvia? χ² con p por permutación de etiquetas."""
    info = pd.read_csv(f"{RES}/celdas_gldas.csv").set_index("celda")
    e = ep[ep["retorno_lluvia"].notna()].copy()
    e["retorno_lluvia"] = pd.to_datetime(e["retorno_lluvia"])
    lon = e["celda"].str.split("_").str[1].astype(float)
    lat = e["celda"].str.split("_").str[0].astype(float)
    e["region"] = np.select([lon < -70.75, lat >= 19.0], ["oeste/suroeste", "norte (Cibao)"], "este/sureste")
    m = e["retorno_lluvia"].dt.month
    e["temporada"] = np.select([m.isin([12, 1, 2, 3]), m.isin([4, 5, 6, 7])], ["seca DEFM", "primera AMJJ"], "segunda ASON")
    if oni is not None:
        o = oni.reindex(e["retorno_lluvia"].values).to_numpy()
        e["enso"] = np.select([o >= 0.5, o <= -0.5], ["El Niño", "La Niña"], "neutro")
    e["provincia"] = e["celda"].map(info["provincia_principal"])
    e["es_A"] = e["contradiccion_A_SM_RAIZ"] == True  # noqa: E712
    e["es_dif"] = e["contradiccion_A_SM_RAIZ_etiqueta"] == "posible diferencia entre productos"
    rng = np.random.default_rng(seed)
    rows = []
    for var in [v for v in ("region", "temporada", "enso") if v in e]:
        for grp, base in (("es_A", e), ("es_dif", e[e["es_A"]])):
            tab = pd.crosstab(base[var], base[grp])
            if tab.shape[1] < 2:
                continue
            chi = sstats.chi2_contingency(tab)[0]
            lab = base[grp].to_numpy()
            cat = base[var].to_numpy()
            null = [sstats.chi2_contingency(pd.crosstab(cat, rng.permutation(lab)))[0] for _ in range(n_perm // 5)]
            p = (1 + np.sum(np.asarray(null) >= chi)) / (1 + len(null))
            for k, r in tab.iterrows():
                rows.append({"variable": var, "comparacion": "A vs todos con retorno" if grp == "es_A" else "posible diferencia vs A",
                             "categoria": k, "n_base": int(r.sum()), "n_marcados": int(r.get(True, 0)),
                             "fraccion": float(r.get(True, 0) / r.sum()), "chi2": chi, "p_perm": p})
    return pd.DataFrame(rows)
