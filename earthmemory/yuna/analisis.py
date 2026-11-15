"""Paneles por evento, prueba de disparadores (backtest) y prueba de la presa como factor de confusión.

Backtest (n pequeño, se dice claro):
- Unidad: EVENTOS del catálogo (detectado si algún día de disparo cae en [inicio − 2 d, fin]) y EPISODIOS de
  disparo (días de disparo separados por > 3 días = episodios distintos; falsa alarma si no toca ningún evento ± 2 d).
  POD = aciertos / eventos; FAR = falsas alarmas / episodios; CSI = aciertos / (aciertos + fallos + falsas alarmas).
  Además, tabla de contingencia por bloques fijos de 3 días.
- Calibración 2001-2015, prueba 2016-2024. IC 95 % por bootstrap de años (los eventos y episodios de un año se
  remuestrean juntos), 2000 réplicas.
- Disparadores: (a) lluvia > 100 mm/48 h (máximo de celda IMERG en la cuenca, al estilo del sEAP de la Cruz Roja,
  que en realidad usa un PRONÓSTICO de INDOMET ligado a ciclones; aquí es lluvia estimada, no pronóstico);
  (b) (a) Y antecedente ≥ p90; (b') umbral de lluvia rebajado cuando el antecedente ≥ p90 (calibrado);
  (c) antecedente solo ≥ percentil calibrado.
- El catálogo es incompleto (prensa): una «falsa alarma» puede ser una inundación no reportada. FAR es cota superior.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
from scipy import stats

from .catalogo import ventanas
from .common import RES, SEED

CAL = (2001, 2015)
TEST = (2016, 2024)
TOL = 2
B = 2000


# ------------------------------------------------------------------ utilidades puras (probadas en tests)

def suma_movil(s: pd.Series, n: int) -> pd.Series:
    return s.rolling(n, min_periods=n).sum()


def antecedente(s: pd.Series, n: int, lag: int = 2) -> pd.Series:
    """Suma de los n días que terminan `lag` días antes de t (no incluye la lluvia del evento)."""
    return s.shift(lag).rolling(n, min_periods=int(np.ceil(0.9 * n))).sum()


def episodios(trig: pd.Series, gap: int = 3) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    d = trig[trig.fillna(False).astype(bool)].index
    if len(d) == 0:
        return []
    out, s, p = [], d[0], d[0]
    for t in d[1:]:
        if (t - p).days > gap:
            out.append((s, p))
            s = t
        p = t
    out.append((s, p))
    return out


def puntuar(trig: pd.Series, vent: list, periodo: tuple[int, int], tol: int = TOL) -> dict:
    """Cuentas por año: aciertos, fallos (eventos) y falsas alarmas (episodios)."""
    y0, y1 = periodo
    t = trig[(trig.index.year >= y0) & (trig.index.year <= y1)].fillna(False).astype(bool)
    ev = [(a, b, i) for a, b, i in vent if y0 <= a.year <= y1]
    por_anio = {y: {"h": 0, "m": 0, "fa": 0, "ep": 0} for y in range(y0, y1 + 1)}
    det = []
    for a, b, i in ev:
        w = t[(t.index >= a - pd.Timedelta(days=tol)) & (t.index <= b)]
        hit = bool(w.any())
        por_anio[a.year]["h" if hit else "m"] += 1
        det.append({"id": i, "detectado": hit})
    for s, e in episodios(t):
        por_anio[s.year]["ep"] += 1
        toca = any(s <= b + pd.Timedelta(days=tol) and e >= a - pd.Timedelta(days=tol) for a, b, _ in ev)
        if not toca:
            por_anio[s.year]["fa"] += 1
    tot = {k: sum(v[k] for v in por_anio.values()) for k in ("h", "m", "fa", "ep")}
    return {"tot": tot, "por_anio": por_anio, "eventos": det}


def metricas(h: float, m: float, fa: float) -> dict:
    pod = h / (h + m) if h + m else np.nan
    far = fa / (h + fa) if h + fa else np.nan  # episodios que tocan evento ~ aciertos
    csi = h / (h + m + fa) if h + m + fa else np.nan
    return {"POD": pod, "FAR": far, "CSI": csi}


def metricas_ep(h, m, fa, ep) -> dict:
    """FAR por episodios: falsas / episodios totales."""
    r = metricas(h, m, fa)
    r["FAR"] = fa / ep if ep else np.nan
    return r


def bootstrap(por_anio: dict, b: int = B, seed: int = SEED) -> dict:
    rng = np.random.default_rng(seed)
    ys = sorted(por_anio)
    arr = np.array([[por_anio[y][k] for k in ("h", "m", "fa", "ep")] for y in ys], float)
    out = {"POD": [], "FAR": [], "CSI": []}
    for _ in range(b):
        s = arr[rng.integers(0, len(ys), len(ys))].sum(0)
        r = metricas_ep(*s)
        for k in out:
            out[k].append(r[k])
    return {k: (float(np.nanpercentile(v, 2.5)), float(np.nanpercentile(v, 97.5))) if np.isfinite(v).any()
            else (np.nan, np.nan) for k, v in out.items()}


def bloques3(trig: pd.Series, vent: list, periodo: tuple[int, int]) -> dict:
    y0, y1 = periodo
    t = trig[(trig.index.year >= y0) & (trig.index.year <= y1)].fillna(False).astype(bool)
    obs = pd.Series(False, index=t.index)
    for a, b, _ in vent:
        obs[(obs.index >= a) & (obs.index <= b)] = True
    blk = (np.arange(len(t)) // 3)
    tb = t.groupby(blk).any()
    ob = obs.groupby(blk).any()
    h = int((tb & ob).sum()); m = int((~tb & ob).sum()); fa = int((tb & ~ob).sum()); cn = int((~tb & ~ob).sum())
    return {"h": h, "m": m, "fa": fa, "cn": cn, **metricas(h, m, fa)}


def auc(pos: np.ndarray, neg: np.ndarray) -> float:
    pos, neg = np.asarray(pos, float), np.asarray(neg, float)
    pos, neg = pos[np.isfinite(pos)], neg[np.isfinite(neg)]
    if len(pos) == 0 or len(neg) == 0:
        return np.nan
    u = stats.mannwhitneyu(pos, neg, alternative="two-sided").statistic
    return float(u / (len(pos) * len(neg)))


def pct_mes(s: pd.Series) -> pd.Series:
    """Percentil (0-100) de cada valor entre los valores del mismo mes del año (climatología de todo el registro)."""
    return s.groupby(s.index.month).rank(pct=True) * 100


# ------------------------------------------------------------------ análisis

def cargar() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    from .series import geoglows
    d = pd.read_parquet(RES / "series_diarias_zonas.parquet")
    d.index = pd.DatetimeIndex(d.index)
    d = d.drop(columns=[c for c in d.columns if c.startswith("q_")])
    ids = json.loads((RES / "geoglows_ids.json").read_text(encoding="utf-8"))
    q = geoglows({k: v for k, v in ids.items() if not k.startswith("_")})
    if q is not None:
        d = d.join(q, how="left")
    g = pd.read_csv(RES / "gldas_mensual_zonas.csv", index_col=0, parse_dates=True)
    w = pd.read_csv(RES / "gsw_mensual.csv", index_col=0, parse_dates=True)
    return d, g, w


def variables(d: pd.DataFrame, g: pd.DataFrame) -> pd.DataFrame:
    v = pd.DataFrame(index=d.index)
    for z in ("yuna", "alto_hatillo", "camu", "bajo_yuna"):
        p = d[f"imerg_media_{z}"]
        v[f"p_{z}"] = p
        v[f"r48_{z}"] = suma_movil(p, 2)
        v[f"r72_{z}"] = suma_movil(p, 3)
        v[f"r48max_{z}"] = d[f"imerg_max48_{z}"]
        for n in (30, 60, 90):
            v[f"ant{n}_{z}"] = antecedente(p, n)
        if f"chirps_media_{z}" in d:
            v[f"r48ch_{z}"] = suma_movil(d[f"chirps_media_{z}"], 2)
            v[f"r48chmax_{z}"] = d[f"chirps_max_{z}"].rolling(2, min_periods=2).max()  # aprox.: máx diario en 48 h
        if f"smap_raiz_{z}" in d:
            v[f"smap_raiz_{z}"] = d[f"smap_raiz_{z}"].shift(2)
        # GLDAS: raíz del MES ANTERIOR (no usa el mes del evento), z por mes del año
        gz = g[f"gldas_sm_raiz_{z}"]
        gz = (gz - gz.groupby(gz.index.month).transform("mean")) / gz.groupby(gz.index.month).transform("std")
        prev = gz.shift(1)
        v[f"gldas_z_{z}"] = prev.reindex(v.index, method="ffill")
        v[f"gldas_zmes_{z}"] = gz.reindex(v.index, method="ffill")
    return v


def calibrar_umbral(serie: pd.Series, grid, vent, base: pd.Series | None = None, modo="mayor") -> tuple[float, dict]:
    best, bt = None, None
    for thr in grid:
        trig = serie > thr if modo == "mayor" else serie >= thr
        if base is not None:
            trig = base | trig
        r = puntuar(trig, vent, CAL)["tot"]
        csi = metricas_ep(r["h"], r["m"], r["fa"], r["ep"])["CSI"]
        if best is None or (np.nan_to_num(csi) > np.nan_to_num(best[1]["CSI"])):
            best = (thr, {"CSI": csi, **r})
    return best


def backtest(v: pd.DataFrame, cat: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    vent = ventanas(cat)
    filas, info = [], {}
    r48max = v["r48max_yuna"]
    cal_mask = (v.index.year >= CAL[0]) & (v.index.year <= CAL[1])

    def registrar(nombre, trig, desc, clase, extra=None):
        for per, lab in ((CAL, "calibración 2001-2015"), (TEST, "prueba 2016-2024")):
            p = puntuar(trig, vent, per)
            t = p["tot"]
            m = metricas_ep(t["h"], t["m"], t["fa"], t["ep"])
            ci = bootstrap(p["por_anio"])
            b3 = bloques3(trig, vent, per)
            filas.append({"disparador": nombre, "descripcion": desc, "variables": clase, "periodo": lab,
                          "eventos": t["h"] + t["m"], "aciertos": t["h"], "fallos": t["m"], "episodios": t["ep"],
                          "falsas_alarmas": t["fa"],
                          "POD": m["POD"], "POD_ic95": ci["POD"], "FAR": m["FAR"], "FAR_ic95": ci["FAR"],
                          "CSI": m["CSI"], "CSI_ic95": ci["CSI"],
                          "bloques3_POD": b3["POD"], "bloques3_FAR": b3["FAR"], "bloques3_CSI": b3["CSI"],
                          "detectados": ",".join(e["id"] for e in p["eventos"] if e["detectado"]),
                          **(extra or {})})

    # (a) sEAP-style
    trig_a = r48max > 100
    registrar("a_lluvia100", trig_a, "máx. celda IMERG en la cuenca > 100 mm/48 h", "IMERG (recuperación)")
    # (a2) media de cuenca calibrada
    thr, best = calibrar_umbral(v["r48_yuna"], np.arange(20, 151, 5), vent)
    registrar("a2_lluvia_media_cal", v["r48_yuna"] > thr, f"media de cuenca IMERG > {thr:.0f} mm/48 h (calibrado)",
              "IMERG (recuperación)", {"umbral": thr})
    info["a2_umbral"] = float(thr)
    # antecedente: elegir n (30/60/90) por CSI de (c) en calibración
    mejor = None
    for n in (30, 60, 90):
        a = v[f"ant{n}_yuna"]
        for q in (0.80, 0.90, 0.95, 0.98, 0.99):
            thr_q = a[cal_mask].quantile(q)
            r = puntuar(a >= thr_q, vent, CAL)["tot"]
            csi = metricas_ep(r["h"], r["m"], r["fa"], r["ep"])["CSI"]
            if mejor is None or np.nan_to_num(csi) > np.nan_to_num(mejor[0]):
                mejor = (csi, n, q, thr_q)
    _, n_c, q_c, thr_c = mejor
    info["c"] = {"n_dias": n_c, "percentil": q_c, "umbral_mm": float(thr_c)}
    ant = v[f"ant{n_c}_yuna"]
    p90 = ant[cal_mask].quantile(0.90)
    info["antecedente_p90_mm"] = float(p90)
    registrar("c_antecedente", ant >= thr_c, f"lluvia antecedente IMERG {n_c} d ≥ p{int(q_c * 100)} ({thr_c:.0f} mm), sola",
              "IMERG (recuperación)", {"umbral": float(thr_c)})
    # (b) a Y antecedente ≥ p90
    registrar("b_lluvia100_y_ant_p90", trig_a & (ant >= p90),
              f"(a) y antecedente {n_c} d ≥ p90 ({p90:.0f} mm)", "IMERG (recuperación)")
    # (b') rebaja de umbral con antecedente húmedo
    wet = ant >= p90
    thr_low, _ = calibrar_umbral(r48max.where(wet), np.arange(30, 101, 5), vent, base=trig_a)
    registrar("b2_umbral_rebajado_si_humedo", trig_a | (wet & (r48max > thr_low)),
              f"(a) o [> {thr_low:.0f} mm/48 h y antecedente ≥ p90]", "IMERG (recuperación)", {"umbral": float(thr_low)})
    info["b2_umbral_bajo"] = float(thr_low)
    # (b'') con GLDAS (modelo forzado) como antecedente: z del mes anterior ≥ p90 de calibración
    gz = v["gldas_z_yuna"]
    gp90 = gz[cal_mask].quantile(0.90)
    registrar("b3_lluvia100_o_rebajado_gldas", trig_a | ((gz >= gp90) & (r48max > thr_low)),
              f"(a) o [> {thr_low:.0f} mm y GLDAS raíz (mes anterior) ≥ p90]", "IMERG + GLDAS (modelo forzado)")
    # SMAP L4 (2015+): solo prueba; umbral = p90 de su propio registro (no fuera de muestra)
    if "smap_raiz_yuna" in v:
        sm = v["smap_raiz_yuna"]
        sp90 = sm.quantile(0.90)
        registrar("b4_lluvia100_o_rebajado_smap", trig_a | ((sm >= sp90) & (r48max > thr_low)),
                  f"(a) o [> {thr_low:.0f} mm y SMAP L4 raíz ≥ p90] (en muestra)",
                  "IMERG + SMAP L4 (modelo con asimilación)")
    tab = pd.DataFrame(filas)
    return tab, info


def datos_insuficientes(cat: pd.DataFrame, d: pd.DataFrame, w: pd.DataFrame) -> pd.DataFrame:
    filas = []
    for r in cat.itertuples():
        a, b = pd.Timestamp(r.inicio), pd.Timestamp(r.fin)
        imerg_ok = bool(d.loc[a - pd.Timedelta(days=92): b, "imerg_media_yuna"].notna().mean() > 0.95) if a.year <= 2024 else False
        smap_ok = bool("smap_raiz_yuna" in d and d.loc[a - pd.Timedelta(days=5): b, "smap_raiz_yuna"].notna().any())
        gq = [c for c in d.columns if c.startswith("q_")]
        geo_ok = bool(gq and d.loc[a: b, gq].notna().any().any())
        m0 = pd.Timestamp(a.year, a.month, 1)
        wm = w.loc[m0: pd.Timestamp(b.year, b.month, 1)] if not w.empty else w
        gsw_val = float(wm["gsw_validos_llanura"].max()) if len(wm) else np.nan
        filas.append({"id": r.id, "zona": r.zona, "usable_backtest": r.usable_backtest, "motivo": r.motivo_exclusion,
                      "IMERG_antecedente_y_evento": imerg_ok, "SMAP_L4": smap_ok, "GEOGLOWS": geo_ok,
                      "GSW_mes_validos_llanura": gsw_val,
                      "GSW_observa": bool(np.isfinite(gsw_val) and gsw_val >= 0.30)})
    return pd.DataFrame(filas)


def paneles(cat: pd.DataFrame, d: pd.DataFrame, v: pd.DataFrame, w: pd.DataFrame) -> pd.DataFrame:
    from .observacion import anomalias
    an = anomalias(w, "llanura") if not w.empty else None
    emb = anomalias(w, "embalse", 0.5) if not w.empty else None
    pct = {}
    for z in ("yuna", "alto_hatillo", "camu", "bajo_yuna"):
        for n in (30, 60, 90):
            pct[f"ant{n}_{z}"] = pct_mes(v[f"ant{n}_{z}"])
        if f"smap_raiz_{z}" in v:
            pct[f"smap_{z}"] = pct_mes(v[f"smap_raiz_{z}"])
    filas = []
    ev = cat[cat["zona"].isin({"bajo_yuna", "alto_yuna", "camu", "cuenca_general"})]
    for r in ev.itertuples():
        a, b = pd.Timestamp(r.inicio), pd.Timestamp(r.fin)
        f = {"id": r.id, "nombre": r.nombre, "inicio": a.date(), "fin": b.date(), "zona": r.zona,
             "confianza": r.confianza}
        if a.year > 2024:
            f["nota"] = "fuera del registro diario local (2001-2024)"
            filas.append(f)
            continue
        win = slice(a - pd.Timedelta(days=3), b)
        for z in ("yuna", "alto_hatillo", "camu", "bajo_yuna"):
            f[f"r48_max_{z}"] = float(v.loc[win, f"r48_{z}"].max())
            f[f"r72_max_{z}"] = float(v.loc[win, f"r72_{z}"].max())
            for n in (30, 60, 90):
                f[f"ant{n}_{z}_mm"] = float(v.loc[a, f"ant{n}_{z}"])
                f[f"ant{n}_{z}_pct"] = float(pct[f"ant{n}_{z}"].loc[a])
            f[f"gldas_z_{z}"] = float(v.loc[a, f"gldas_z_{z}"])
            if f"smap_{z}" in pct:
                f[f"smap_raiz_{z}"] = float(v.loc[a, f"smap_raiz_{z}"])
                f[f"smap_raiz_{z}_pct"] = float(pct[f"smap_{z}"].loc[a])
            if f"r48ch_{z}" in v:
                f[f"chirps_r48_max_{z}"] = float(v.loc[win, f"r48ch_{z}"].max())
        f["r48_maxcelda_yuna"] = float(v.loc[win, "r48max_yuna"].max())
        for c in [c for c in d.columns if c.startswith("q_")]:
            q = d[c]
            f[f"{c}_pico"] = float(q.loc[a - pd.Timedelta(days=1): b + pd.Timedelta(days=3)].max())
            f[f"{c}_pico_pct"] = float((q < f[f"{c}_pico"]).mean() * 100) if np.isfinite(f[f"{c}_pico"]) else np.nan
        if an is not None:
            m0, m1 = pd.Timestamp(a.year, a.month, 1), pd.Timestamp(b.year, b.month, 1) + pd.offsets.MonthBegin(1)
            sub = an.loc[m0:m1]
            us = sub[sub["usable"]]
            f["gsw_meses"] = ",".join(x.strftime("%Y-%m") for x in sub.index)
            f["gsw_validos_max"] = float(sub["validos"].max()) if len(sub) else np.nan
            f["gsw_anomalia_max"] = float(us["anomalia"].max()) if len(us) else np.nan
            f["gsw_sobre_p90"] = bool(us["sobre_p90"].any()) if len(us) else None
            se = emb.loc[pd.Timestamp(a.year, a.month, 1) - pd.offsets.MonthBegin(1): m0]
            se = se[se["usable"]]
            f["embalse_km2_mes_previo"] = float(se["km2"].iloc[-1]) if len(se) else np.nan
        filas.append(f)
    return pd.DataFrame(filas)


def prueba_presa(v: pd.DataFrame, cat: pd.DataFrame, w: pd.DataFrame) -> dict:
    """¿El antecedente aguas arriba de Hatillo informa igual que el del Camú (no regulado) sobre las inundaciones
    del Bajo Yuna? Dos pruebas: (1) episodios de lluvia fuerte con/sin evento del catálogo, AUC del antecedente de
    cada zona; (2) meses 2001-2020 con agua observada (GSW) en la llanura: ρ de Spearman con el antecedente de cada
    zona, por estado del embalse (área GSW alta/baja)."""
    from .observacion import anomalias
    rng = np.random.default_rng(SEED)
    vent = ventanas(cat, {"bajo_yuna", "cuenca_general", "camu", "alto_yuna"})
    out = {}
    # (1) episodios de lluvia fuerte (r48 máx. celda ≥ p99 de los días)
    thr = v["r48max_yuna"].quantile(0.99)
    eps = episodios(v["r48max_yuna"] >= thr)
    filas = []
    for s, e in eps:
        if s.year > 2024:
            continue
        fl = any(s <= b + pd.Timedelta(days=TOL) and e >= a - pd.Timedelta(days=TOL) for a, b, _ in vent)
        r = {"inicio": s, "fin": e, "inundacion_catalogo": fl}
        for z in ("alto_hatillo", "camu", "bajo_yuna"):
            r[f"ant30_pct_{z}"] = float(pct_mes(v[f"ant30_{z}"]).loc[s])
            r[f"gldas_z_{z}"] = float(v.loc[s, f"gldas_z_{z}"])
            r[f"r48_{z}"] = float(v.loc[s:e + pd.Timedelta(days=1), f"r48_{z}"].max())
        filas.append(r)
    ep = pd.DataFrame(filas)
    out["episodios"] = ep
    res = {"umbral_r48max_p99_mm": float(thr), "n_episodios": int(len(ep)),
           "n_con_inundacion": int(ep["inundacion_catalogo"].sum()) if len(ep) else 0}
    for var in ("ant30_pct", "gldas_z", "r48"):
        for z in ("alto_hatillo", "camu", "bajo_yuna"):
            pos = ep.loc[ep["inundacion_catalogo"], f"{var}_{z}"].to_numpy()
            neg = ep.loc[~ep["inundacion_catalogo"], f"{var}_{z}"].to_numpy()
            bs = []
            for _ in range(B):
                bs.append(auc(rng.choice(pos, len(pos)), rng.choice(neg, len(neg))) if len(pos) and len(neg) else np.nan)
            res[f"AUC_{var}_{z}"] = auc(pos, neg)
            res[f"AUC_{var}_{z}_ic95"] = [float(np.nanpercentile(bs, 2.5)), float(np.nanpercentile(bs, 97.5))]
        # diferencia alto_hatillo − camu con bootstrap pareado de episodios
        dif = []
        for _ in range(B):
            idx = rng.integers(0, len(ep), len(ep))
            s_ = ep.iloc[idx]
            p_, n_ = s_[s_["inundacion_catalogo"]], s_[~s_["inundacion_catalogo"]]
            dif.append(auc(p_[f"{var}_alto_hatillo"], n_[f"{var}_alto_hatillo"]) - auc(p_[f"{var}_camu"], n_[f"{var}_camu"]))
        res[f"dAUC_{var}_alto_menos_camu"] = res[f"AUC_{var}_alto_hatillo"] - res[f"AUC_{var}_camu"]
        res[f"dAUC_{var}_alto_menos_camu_ic95"] = [float(np.nanpercentile(dif, 2.5)), float(np.nanpercentile(dif, 97.5))]
    out["auc"] = res
    # (2) mensual con GSW
    if not w.empty:
        an = anomalias(w, "llanura")
        emb = anomalias(w, "embalse", 0.5)
        mens = pd.DataFrame({"anom_llanura": an["anomalia"].where(an["usable"]), "embalse_km2": emb["km2"].where(emb["usable"])})
        for z in ("alto_hatillo", "camu", "bajo_yuna"):
            # lluvia del mes (IMERG, suma) y raíz GLDAS del mes (z)
            mens[f"lluvia_mes_{z}"] = v[f"p_{z}"].resample("MS").sum(min_count=25)   # IMERG, mm en el mes
            mens[f"gldas_z_{z}"] = v[f"gldas_zmes_{z}"].resample("MS").first()       # GLDAS raíz, z del propio mes
        mens = mens.loc["2001":"2020"]
        med = mens["embalse_km2"].median()
        filas = []
        for estado, sel in (("todos", mens["anom_llanura"].notna()),
                            ("embalse_alto", mens["anom_llanura"].notna() & (mens["embalse_km2"] >= med)),
                            ("embalse_bajo", mens["anom_llanura"].notna() & (mens["embalse_km2"] < med))):
            s_ = mens[sel]
            for z in ("alto_hatillo", "camu", "bajo_yuna"):
                for var in ("lluvia_mes", "gldas_z"):
                    x, y = s_[f"{var}_{z}"], s_["anom_llanura"]
                    ok = x.notna() & y.notna()
                    rho = stats.spearmanr(x[ok], y[ok]).statistic if ok.sum() > 5 else np.nan
                    # bootstrap por años
                    yrs = np.array(sorted(set(s_.index.year)))
                    bs = []
                    for _ in range(1000):
                        ys = rng.choice(yrs, len(yrs))
                        ss = pd.concat([s_[s_.index.year == yy] for yy in ys])
                        o = ss[f"{var}_{z}"].notna() & ss["anom_llanura"].notna()
                        bs.append(stats.spearmanr(ss.loc[o, f"{var}_{z}"], ss.loc[o, "anom_llanura"]).statistic
                                  if o.sum() > 5 else np.nan)
                    filas.append({"estado_embalse": estado, "zona_antecedente": z, "variable": var, "n_meses": int(ok.sum()),
                                  "rho": float(rho), "ic95": [float(np.nanpercentile(bs, 2.5)), float(np.nanpercentile(bs, 97.5))]})
        out["mensual"] = pd.DataFrame(filas)
        out["mensual_serie"] = mens
        out["embalse_mediana_km2"] = float(med) if np.isfinite(med) else None
        # ¿responde el embalse a la lluvia de arriba?
        ok = mens["embalse_km2"].notna() & mens["lluvia_mes_alto_hatillo"].notna()
        out["embalse_vs_lluvia_alta"] = {"n": int(ok.sum()), "rho": float(stats.spearmanr(
            mens.loc[ok, "lluvia_mes_alto_hatillo"], mens.loc[ok, "embalse_km2"]).statistic) if ok.sum() > 5 else None}
    return out


def run(cat: pd.DataFrame) -> dict:
    d, g, w = cargar()
    v = variables(d, g)
    tab, info = backtest(v, cat)
    tab.to_csv(RES / "backtest_disparadores.csv", index=False)
    ins = datos_insuficientes(cat, d, w)
    ins.to_csv(RES / "datos_suficientes_por_evento.csv", index=False)
    pan = paneles(cat, d, v, w)
    pan.to_csv(RES / "paneles_eventos.csv", index=False)
    pr = prueba_presa(v, cat, w)
    pr["episodios"].to_csv(RES / "presa_episodios_lluvia_fuerte.csv", index=False)
    if "mensual" in pr:
        pr["mensual"].to_csv(RES / "presa_correlaciones_mensuales.csv", index=False)
    resumen = {"backtest_info": info, "presa_auc": pr["auc"],
               "presa_embalse_mediana_km2": pr.get("embalse_mediana_km2"),
               "embalse_vs_lluvia_alta": pr.get("embalse_vs_lluvia_alta"),
               "n_eventos_catalogo_cuenca": int(cat["zona"].isin({"bajo_yuna", "alto_yuna", "camu", "cuenca_general"}).sum()),
               "n_eventos_usables": int(cat["usable_backtest"].sum()),
               "n_eventos_calibracion": int(sum(1 for a, _, _ in ventanas(cat) if CAL[0] <= a.year <= CAL[1])),
               "n_eventos_prueba": int(sum(1 for a, _, _ in ventanas(cat) if TEST[0] <= a.year <= TEST[1]))}
    (RES / "analisis_resumen.json").write_text(json.dumps(resumen, ensure_ascii=False, indent=1, default=str),
                                              encoding="utf-8")
    return {"d": d, "g": g, "w": w, "v": v, "cat": cat, "backtest": tab, "info": info, "insuf": ins,
            "paneles": pan, "presa": pr, "resumen": resumen}
