"""Bloques de cálculo de la auditoría: estaciones, cambio de decisión, Santo Domingo y "dónde medir"."""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import datos, decision, estaciones
from .descarga import DATA

PRODUCTOS_M = ["IMERG", "CHIRPS", "GLDAS_forzamiento", "MERRA2"]
NOMBRE = {"IMERG": "IMERG V07 Final", "CHIRPS": "CHIRPS v2.0", "GLDAS_forzamiento": "Lluvia de forzamiento GLDAS-2.1 (GPCP)",
          "MERRA2": "MERRA-2 PRECTOTCORR (NASA POWER)"}


def load_oni() -> pd.Series | None:
    p = DATA / "enso" / "oni.ascii.txt"
    if not p.exists():
        return None
    seas = ["DJF", "JFM", "FMA", "MAM", "AMJ", "MJJ", "JJA", "JAS", "ASO", "SON", "OND", "NDJ"]
    rows = {}
    for ln in p.read_text().splitlines()[1:]:
        f = ln.split()
        if len(f) == 4 and f[0] in seas:
            rows[pd.Timestamp(int(f[1]), seas.index(f[0]) + 1, 1)] = float(f[3])
    return pd.Series(rows).sort_index()


# ------------------------------------------------------------------ cubos mensuales 0.05°

def monthly_cubes(g: datos.G05) -> dict:
    d = datos.imerg_daily()
    I, J = datos.nest_index(d["lat"], d["lon"], 0.1, 0.1, g)
    im = datos.to05(datos.monthly_from_daily(d["P"], d["dias"]), I, J)
    ch = datos.chirps_monthly()["P"]
    gf = datos.gldas_forcing()
    I2, J2 = datos.nest_index(gf["lat"], gf["lon"], 0.25, 0.25, g)
    gl = datos.to05(gf["P"], I2, J2)
    me = datos.merra2_monthly()
    I3, J3 = datos.nest_index(me["lat"], me["lon"], 0.5, 0.625, g)
    mr = datos.to05(me["P"], I3, J3)
    return {"IMERG": im, "CHIRPS": ch, "GLDAS_forzamiento": gl, "MERRA2": mr}


# ------------------------------------------------------------------ 4. cambio de decisión (sequía)

def drought_flips(g: datos.G05, cubes: dict, B: int = 2000) -> dict:
    meses = datos.MESES
    years = meses.year.to_numpy()
    Pp = {k: g.province_mean(v) for k, v in cubes.items()}
    spi = {k: decision.spi3(v, meses) for k, v in Pp.items()}
    out_prov, out_nat, out_pair, per_year = [], [], [], []
    for thr in (-1.0, -1.5):
        F = {k: decision.flags(s, thr) for k, s in spi.items()}
        for combo_name, combo in (("4 productos", PRODUCTOS_M), ("IMERG vs CHIRPS", ["IMERG", "CHIRPS"]),
                                  ("3 sin MERRA-2", ["IMERG", "CHIRPS", "GLDAS_forzamiento"])):
            c = decision.flip_components({k: F[k] for k in combo})
            r = decision.rates(c)
            lo_g, hi_g, _ = decision.ratio_bootstrap(c["no_unanime"], c["valido"], years, B)
            lo_c, hi_c, _ = decision.ratio_bootstrap(c["no_unanime"], c["alguna_alarma"], years, B)
            # tipo de desacuerdo: claro (un producto <= umbral y otro >= 0: normal o húmedo) o de frontera
            Ssp = np.stack([spi[k] for k in combo])
            smax = np.nanmax(Ssp, 0)
            clara = c["no_unanime"] & (smax >= 0)
            frontera = c["no_unanime"] & (smax < thr + 0.5)
            unanime = c["alguna_alarma"] & ~c["no_unanime"]
            lo_cl, hi_cl, _ = decision.ratio_bootstrap(clara, c["alguna_alarma"], years, B)
            na = max(int(c["alguna_alarma"].sum()), 1)
            out_nat.append({"umbral_spi3": thr, "productos": combo_name, **r, "ic95_global": [lo_g, hi_g],
                            "ic95_condicional": [lo_c, hi_c], "n_contradiccion_clara": int(clara.sum()),
                            "tasa_contradiccion_clara": clara.sum() / na, "ic95_contradiccion_clara": [lo_cl, hi_cl],
                            "n_frontera": int(frontera.sum()), "tasa_frontera": frontera.sum() / na,
                            "n_unanime_sequia": int(unanime.sum())})
            if combo_name != "4 productos":
                continue
            if thr == -1.0:
                per_year += [{"anio": int(y), "n_alguna_alarma": int(c["alguna_alarma"][years == y].sum()),
                              "n_no_unanime": int(c["no_unanime"][years == y].sum()),
                              "n_unanime_sequia": int(unanime[years == y].sum()),
                              "n_contradiccion_clara": int(clara[years == y].sum())} for y in np.unique(years)]
            # por provincia: conteos por año → bootstrap vectorizado
            yrs = np.unique(years)
            num = np.stack([c["no_unanime"][years == y].sum(0) for y in yrs])
            den = np.stack([c["alguna_alarma"][years == y].sum(0) for y in yrs])
            val = np.stack([c["valido"][years == y].sum(0) for y in yrs])
            rng = np.random.default_rng(2026)
            pick = rng.integers(0, yrs.size, size=(B, yrs.size))
            bn, bd, bv = num[pick].sum(1), den[pick].sum(1), val[pick].sum(1)
            with np.errstate(invalid="ignore", divide="ignore"):
                bc, bg = bn / bd, bn / bv
            for k, p in enumerate(g.provs):
                rr = decision.rates(c, cols=np.array([k]))
                out_prov.append({"umbral_spi3": thr, "provincia": p, "codigo": g.codes.get(p), **rr,
                                 "ic95_condicional_bajo": float(np.nanpercentile(bc[:, k], 2.5)),
                                 "ic95_condicional_alto": float(np.nanpercentile(bc[:, k], 97.5)),
                                 "ic95_global_bajo": float(np.nanpercentile(bg[:, k], 2.5)),
                                 "ic95_global_alto": float(np.nanpercentile(bg[:, k], 97.5)),
                                 "tasa_contradiccion_clara": float(clara[:, k].sum() / max(c["alguna_alarma"][:, k].sum(), 1)),
                                 "meses_alarma_" + "_".join(PRODUCTOS_M): "/".join(
                                     str(int(np.nansum(F[q][:, k]))) for q in PRODUCTOS_M)})
        for i, a in enumerate(PRODUCTOS_M):
            for b in PRODUCTOS_M[i + 1:]:
                pdg = decision.pair_disagreement(F[a], F[b])
                lo, hi, _ = decision.ratio_bootstrap(((F[a] > 0.5) ^ (F[b] > 0.5)) & np.isfinite(F[a]) & np.isfinite(F[b]),
                                                     ((F[a] > 0.5) | (F[b] > 0.5)) & np.isfinite(F[a]) & np.isfinite(F[b]),
                                                     years, B)
                out_pair.append({"umbral_spi3": thr, "producto_a": a, "producto_b": b, **pdg, "ic95_condicional": [lo, hi]})
    # serie nacional de cuántos productos dicen "sequía" (para la figura)
    F1 = {k: decision.flags(s, -1.0) for k, s in spi.items()}
    nprov = pd.DataFrame({k: np.nansum(v, 1) for k, v in F1.items()}, index=meses)
    return {"provincia": pd.DataFrame(out_prov), "nacional": out_nat, "pares": pd.DataFrame(out_pair),
            "por_anio": pd.DataFrame(per_year), "spi_prov": spi, "provincias_en_sequia": nprov, "P_prov": Pp}


# ------------------------------------------------------------------ 4ii. disparador de inundación 48 h

def flood_flips(g: datos.G05, B: int = 2000, thr: float = 100.0) -> dict | None:
    ch = datos.chirps_daily(g)
    if ch is None:
        return None
    d = datos.imerg_daily()
    I, J = datos.nest_index(d["lat"], d["lon"], 0.1, 0.1, g)
    sel = d["dias"].isin(ch["dias"])
    IM = datos.to05(d["P"][sel], I, J)
    CH = np.asarray(ch["P"], float)
    dias = ch["dias"]
    years = dias.year.to_numpy()
    inprov = [(g.prov_of == k) & (g.prov_frac >= 0.5) for k in range(len(g.provs))]
    res, perprov = [], []
    variants = {}
    for k_shift in (0, -1, 1):
        IMk = decision.shift(IM, k_shift)
        for modo in ("media_provincia", "maximo_celda"):
            if modo == "media_provincia":
                a = decision.accum(g.province_mean(IMk), 2)
                b = decision.accum(g.province_mean(CH), 2)
            else:
                A2 = decision.accum(IMk.reshape(IMk.shape[0], -1), 2)
                B2 = decision.accum(CH.reshape(CH.shape[0], -1), 2)
                a = np.stack([np.nanmax(np.where(np.isfinite(A2[:, m]), A2[:, m], -1), 1) for m in inprov], 1)
                b = np.stack([np.nanmax(np.where(np.isfinite(B2[:, m]), B2[:, m], -1), 1) for m in inprov], 1)
                a[a < 0], b[b < 0] = np.nan, np.nan
            fa, fb = decision.flags(-a, -thr - 1e-9), decision.flags(-b, -thr - 1e-9)  # a > thr
            variants[(k_shift, modo)] = (fa, fb)
            for tol in (0, 1):
                ag = decision.trigger_agreement(fa, fb, tol)

                def stat(rows, fa=fa, fb=fb, tol=tol):
                    return decision.trigger_agreement(fa[rows], fb[rows], tol)["tasa_cambio_decision"]
                lo, hi, _ = decision.year_bootstrap(years, stat, B=min(B, 500))
                res.append({"desplazamiento_imerg_dias": k_shift, "escala": modo, "tolerancia_dias": tol, **ag,
                            "ic95": [lo, hi]})
    fa, fb = variants[(0, "maximo_celda")]
    for k, p in enumerate(g.provs):
        for tol in (0, 1):
            ag = decision.trigger_agreement(fa[:, [k]], fb[:, [k]], tol)
            perprov.append({"provincia": p, "codigo": g.codes.get(p), "escala": "maximo_celda", "tolerancia_dias": tol, **ag})
    fa, fb = variants[(0, "media_provincia")]
    for k, p in enumerate(g.provs):
        for tol in (0, 1):
            ag = decision.trigger_agreement(fa[:, [k]], fb[:, [k]], tol)
            perprov.append({"provincia": p, "codigo": g.codes.get(p), "escala": "media_provincia", "tolerancia_dias": tol, **ag})
    return {"resumen": pd.DataFrame(res), "provincia": pd.DataFrame(perprov),
            "anios": ch["anios"], "completo": ch["completo"], "n_dias": int(len(dias))}


# ------------------------------------------------------------------ 2. estaciones

def _cell(lat_c, lon_c, res_lat, res_lon, la, lo):
    i = int(np.floor((la - (lat_c[0] - res_lat / 2)) / res_lat))
    j = int(np.floor((lo - (lon_c[0] - res_lon / 2)) / res_lon))
    return i, j


def station_validation(g: datos.G05, cubes: dict) -> dict:
    meta, series = estaciones.station_table()
    ing = estaciones.chirps_ingestion(meta) if len(meta) else pd.DataFrame()
    d = datos.imerg_daily()
    ch = datos.chirps_daily(g)
    m2 = datos.merra2_daily_points()
    gf = datos.gldas_forcing()
    me = datos.merra2_monthly()
    chm = datos.chirps_monthly()
    rows_d, rows_m, spread = [], [], []
    for _, s in meta[meta["dias_validos"] > 365].iterrows():
        o = series[s["omm"]]
        la, lo = s["lat"], s["lon"]
        i, j = _cell(d["lat"], d["lon"], 0.1, 0.1, la, lo)
        prods = {"IMERG": pd.Series(d["P"][:, i, j], index=d["dias"])}
        neigh = [(i + a, j + b) for a in (-1, 0, 1) for b in (-1, 0, 1)
                 if 0 <= i + a < d["lat"].size and 0 <= j + b < d["lon"].size]
        if ch is not None:
            ci, cj = _cell(g.lat, g.lon, 0.05, 0.05, la, lo)
            prods["CHIRPS"] = pd.Series(np.asarray(ch["P"][:, ci, cj], float), index=ch["dias"])
        near = min(m2, key=lambda k: (k[0] - la) ** 2 + (k[1] - lo) ** 2)
        if abs(near[0] - la) <= 0.25 + 1e-6 and abs(near[1] - lo) <= 0.3125 + 1e-6:
            prods["MERRA2"] = m2[near]
        for name, pser in prods.items():
            pser = pser.reindex(o.index)
            bl = estaciones.best_lag(o, pser)
            for lag in sorted({0, bl["lag_dias"]} - {None}):
                rows_d.append({"omm": s["omm"], "nombre": s["nombre"], "red": s["red"], "producto": name,
                               "desfase_dias": lag, "es_mejor_desfase": lag == bl["lag_dias"],
                               **estaciones.metrics(o, pser.shift(lag))})
        # vecinas IMERG: dispersión punto-celda
        mean_ann = [np.nanmean(d["P"][:, a, b]) * 365.25 for a, b in neigh]
        ext = o[o >= 100].index
        for t in ext:
            k = d["dias"].get_loc(t) if t in d["dias"] else None
            if k is None:
                continue
            for lag in (0, 1):
                kk = k - lag
                vals = [float(d["P"][kk, a, b]) for a, b in neigh]
                spread.append({"omm": s["omm"], "fecha_estacion": str(t.date()), "desfase_dias": lag,
                               "estacion_mm": float(o[t]), "imerg_celda_mm": float(d["P"][kk, i, j]),
                               "imerg_vecinas_min_mm": min(vals), "imerg_vecinas_max_mm": max(vals)})
        spread.append({"omm": s["omm"], "fecha_estacion": "climatologia", "lluvia_anual_estacion_mm":
                       float(o.mean() * 365.25), "imerg_celda_anual_mm": float(np.nanmean(d["P"][:, i, j]) * 365.25),
                       "imerg_vecinas_anual_min_mm": float(min(mean_ann)), "imerg_vecinas_anual_max_mm": float(max(mean_ann))})
        # mensual (meses con >= 70 % de días; estación escalada al mes completo)
        om = o.groupby(o.index.to_period("M")).agg(["sum", "count"])
        om["ndias"] = om.index.days_in_month
        om = om[om["count"] >= 0.7 * om["ndias"]]
        osum = om["sum"] * om["ndias"] / om["count"]
        osum.index = osum.index.to_timestamp()
        mp = {}
        ci, cj = _cell(g.lat, g.lon, 0.05, 0.05, la, lo)
        mp["IMERG"] = pd.Series(cubes["IMERG"][:, ci, cj], index=datos.MESES)
        mp["CHIRPS"] = pd.Series(chm["P"][:, ci, cj], index=chm["meses"])
        gi, gj = _cell(gf["lat"], gf["lon"], 0.25, 0.25, la, lo)
        mp["GLDAS_forzamiento"] = pd.Series(gf["P"][:, gi, gj], index=gf["meses"])
        mi, mj = _cell(me["lat"], me["lon"], 0.5, 0.625, la, lo)
        if 0 <= mi < me["lat"].size and 0 <= mj < me["lon"].size:
            mp["MERRA2"] = pd.Series(me["P"][:, mi, mj], index=me["meses"])
        ingest = ing[ing["omm"] == s["omm"]].copy() if len(ing) else pd.DataFrame()
        if len(ingest):
            ingest["fecha"] = pd.to_datetime(ingest["mes"].str.replace(".", "-") + "-01")
            ingest = ingest.set_index("fecha")["en_chirps"]
        for name, pser in mp.items():
            pser = pser.reindex(osum.index)
            rows_m.append({"omm": s["omm"], "nombre": s["nombre"], "producto": name, "subconjunto": "todos los meses",
                           **estaciones.metrics(osum, pser, thresholds=(300,))})
            if name in ("CHIRPS", "IMERG") and len(ingest):
                fl = ingest.reindex(osum.index).fillna(False).astype(bool)
                for lab, msk in (("meses con la estación en CHIRPS", fl), ("meses sin la estación en CHIRPS", ~fl)):
                    rows_m.append({"omm": s["omm"], "nombre": s["nombre"], "producto": name, "subconjunto": lab,
                                   **estaciones.metrics(osum[msk], pser[msk], thresholds=(300,))})
        # mensual con días emparejados (productos diarios): suma de los mismos días válidos, meses con >= 15 días
        for name, pser in prods.items():
            lag = estaciones.best_lag(o, pser.reindex(o.index))["lag_dias"] or 0
            pd_ = pd.DataFrame({"o": o, "m": pser.reindex(o.index).shift(lag)}).dropna()
            gm = pd_.groupby(pd_.index.to_period("M")).agg(o=("o", "sum"), m=("m", "sum"), n=("o", "size"))
            gm = gm[gm["n"] >= 15]
            gm.index = gm.index.to_timestamp()
            rows_m.append({"omm": s["omm"], "nombre": s["nombre"], "producto": name,
                           "subconjunto": f"días emparejados (desfase {lag:+d} d)",
                           **estaciones.metrics(gm["o"], gm["m"], thresholds=(300,))})
    ing_sum = (ing.groupby("omm").agg(meses=("mes", "size"), meses_en_chirps=("en_chirps", "sum"),
                                       fuentes=("fuentes_chirps", lambda x: ",".join(sorted({f for v in x for f in v.split("+") if f}))))
               .reset_index() if len(ing) else pd.DataFrame())
    if len(ing_sum):
        meta = meta.merge(ing_sum, on="omm", how="left")
        meta["fraccion_meses_en_chirps"] = meta["meses_en_chirps"] / meta["meses"]
    meta["en_gts_probable"] = meta["red"].isin(["GHCN-Daily", "GSOD (ISD)"])
    meta["circularidad"] = np.where(meta.get("fraccion_meses_en_chirps", pd.Series(0, index=meta.index)).fillna(0) > 0.5,
                                    "CHIRPS: SÍ (lista oficial de estaciones); IMERG Final (GPCC) y MERRA-2 (CPCU): probable vía GTS",
                                    "IMERG Final (GPCC) y MERRA-2 (CPCU): probable vía GTS; CHIRPS: no o pocas veces")
    return {"meta": meta, "diario": pd.DataFrame(rows_d), "mensual": pd.DataFrame(rows_m),
            "dispersion": pd.DataFrame(spread), "ingesta": ing, "series": series}


# ------------------------------------------------------------------ 5. Santo Domingo 18-nov-2023

AHV = (18.495, -69.948)   # Arroyo Hondo Viejo: centroide APROXIMADO del barrio (no es la coordenada oficial)
PRENSA_ONAMET = {"Arroyo Hondo Viejo": 431.0, "Renacimiento": 426.0, "Paraíso": 394.7, "Ensanche Paraíso": 383.5,
                 "Los Cajuiles": 327.6, "Prolongación 27 de Febrero": 316.7, "Santo Domingo Este": 313.2,
                 "La Agustina": 285.5, "Ensanche La Fe": 285.0, "Centro de los Héroes": 267.2,
                 "Base Aérea de San Isidro": 264.16}


def santo_domingo(g: datos.G05, stv: dict | None) -> dict:
    hh = datos.imerg_halfhour()
    t = hh["t"]
    i, j = _cell(hh["lat"], hh["lon"], 0.1, 0.1, *AHV)
    neigh = [(i + a, j + b) for a in (-1, 0, 1) for b in (-1, 0, 1)]
    W = {"día UTC 18-nov (00-24 UTC)": ("2023-11-18T00:00", "2023-11-19T00:00"),
         "día civil local 18-nov (04 UTC 18 → 04 UTC 19)": ("2023-11-18T04:00", "2023-11-19T04:00"),
         "24 h que terminan 12 UTC 18-nov (SYNOP, 08 h local)": ("2023-11-17T12:00", "2023-11-18T12:00"),
         "24 h que terminan 12 UTC 19-nov (SYNOP fechado 19)": ("2023-11-18T12:00", "2023-11-19T12:00"),
         "07-07 local que termina el 19 (11 UTC 18 → 11 UTC 19)": ("2023-11-18T11:00", "2023-11-19T11:00")}
    rows = []
    P = hh["P"]
    for name, (a, b) in W.items():
        m = (t >= pd.Timestamp(a)) & (t < pd.Timestamp(b))
        tot = P[m].sum(0)
        vals = [float(tot[x, y]) for x, y in neigh]
        rows.append({"ventana": name, "inicio_utc": a, "fin_utc": b, "medias_horas": int(m.sum()),
                     "imerg_celda_mm": float(tot[i, j]), "imerg_vecinas_max_mm": max(vals),
                     "imerg_vecinas_media_mm": float(np.mean(vals)), "imerg_vecinas_min_mm": min(vals)})
    # máximo de 24 h móviles (celda y vecinas)
    roll = np.cumsum(np.concatenate([np.zeros((1,) + P.shape[1:]), P]), 0)
    r24 = roll[48:] - roll[:-48]
    k_c = int(np.argmax(r24[:, i, j]))
    best_n = max(neigh, key=lambda xy: r24[:, xy[0], xy[1]].max())
    k_n = int(np.argmax(r24[:, best_n[0], best_n[1]]))
    rows.append({"ventana": "máximo de 24 h móviles (17-19 nov)", "inicio_utc": str(t[k_c]), "fin_utc": str(t[k_c] + pd.Timedelta(hours=24)),
                 "medias_horas": 48, "imerg_celda_mm": float(r24[k_c, i, j]),
                 "imerg_vecinas_max_mm": float(r24[k_n, best_n[0], best_n[1]]),
                 "imerg_vecinas_media_mm": float(np.mean([r24[:, x, y].max() for x, y in neigh])),
                 "imerg_vecinas_min_mm": float(min(r24[:, x, y].max() for x, y in neigh))})
    win = pd.DataFrame(rows)
    # serie horaria (celda) para la figura
    hourly = pd.DataFrame({"inicio_utc": t, "celda_mm": P[:, i, j], "vecinas_max_mm": P[:, [x for x, _ in neigh], [y for _, y in neigh]].max(1)})
    # CHIRPS diario nov-2023 0.05°
    cd = datos.chirps_daily_nov2023()
    ci, cj = _cell(g.lat, g.lon, 0.05, 0.05, *AHV)
    cn = [(ci + a, cj + b) for a in (-1, 0, 1) for b in (-1, 0, 1)]
    chirps = {"celda_18": float(cd[17, ci, cj]), "celda_19": float(cd[18, ci, cj]),
              "celda_18_19": float(cd[17, ci, cj] + cd[18, ci, cj]),
              "vecinas_max_18": float(max(cd[17, x, y] for x, y in cn)),
              "vecinas_max_18_19": float(max(cd[17, x, y] + cd[18, x, y] for x, y in cn)),
              "region_max_18_19_en_RD": float(np.nanmax(np.where(g.frac_rd > 0.5, cd[17] + cd[18], np.nan)))}
    # IMERG diario (rejilla 0.1) región
    d = datos.imerg_daily()
    k18 = d["dias"].get_loc(pd.Timestamp("2023-11-18"))
    imd = {"celda_dia_utc_18": float(d["P"][k18, i, j]), "celda_dia_utc_19": float(d["P"][k18 + 1, i, j])}
    ghcn = {}
    if stv is not None and "78486" in stv["series"]:
        s = stv["series"]["78486"]
        ghcn = {str(k.date()): (None if pd.isna(v) else float(v)) for k, v in s.loc["2023-11-16":"2023-11-21"].items()}
    best = win["imerg_celda_mm"].max()
    best_n = win["imerg_vecinas_max_mm"].max()
    utc = win.iloc[0]["imerg_celda_mm"]
    prensa = np.array(list(PRENSA_ONAMET.values()))
    decomp = {"estacion_mm": 431.0, "imerg_celda_dia_utc_mm": utc,
              "efecto_ventana_mm": best - utc, "imerg_celda_mejor_ventana_mm": best,
              "efecto_escala_vecinas_mm": best_n - best, "imerg_mejor_vecina_mejor_ventana_mm": best_n,
              "brecha_restante_mm": 431.0 - best_n,
              "media_11_pluviometros_prensa_mm": float(prensa.mean()), "mediana_11_pluviometros_prensa_mm": float(np.median(prensa)),
              "brecha_restante_vs_media_pluviometros_mm": float(prensa.mean() - best_n),
              "chirps_mejor_vecina_18_19_mm": chirps["vecinas_max_18_19"]}
    return {"ventanas": win, "horaria": hourly, "chirps": chirps, "imerg_diario": imd, "ghcn_78486": ghcn,
            "descomposicion": decomp, "celda": {"i": i, "j": j, "lat": float(hh["lat"][i]), "lon": float(hh["lon"][j])}}


# ------------------------------------------------------------------ 6. dónde medir (prototipo)

def where_to_measure(g: datos.G05, cubes: dict, meta: pd.DataFrame) -> pd.DataFrame:
    meses = datos.MESES
    ny, nx = g.shape[0] // 2, g.shape[1] // 2

    def to01(X):
        X = X[:, :ny * 2, :nx * 2].reshape(X.shape[0], ny, 2, nx, 2)
        return np.nanmean(X, axis=(2, 4))
    fr = g.frac_rd[:ny * 2, :nx * 2].reshape(ny, 2, nx, 2).mean((1, 3))
    lat = g.lat[:ny * 2].reshape(ny, 2).mean(1)
    lon = g.lon[:nx * 2].reshape(nx, 2).mean(1)
    keep = np.argwhere(fr >= 0.25)
    C = {k: to01(v)[:, keep[:, 0], keep[:, 1]] for k, v in cubes.items()}
    S = {k: decision.spi3(v, meses) for k, v in C.items()}
    F = {k: decision.flags(s, -1.0) for k, s in S.items()}
    comp = decision.flip_components(F)
    flip = comp["no_unanime"].sum(0) / np.maximum(comp["alguna_alarma"].sum(0), 1)
    r = np.array([pd.Series(S["IMERG"][:, k]).corr(pd.Series(S["CHIRPS"][:, k])) for k in range(keep.shape[0])])
    # persistencia: fracción de años con al menos un mes de cambio de decisión
    yrs = meses.year.to_numpy()
    pers = np.stack([comp["no_unanime"][yrs == y].any(0) for y in np.unique(yrs)]).mean(0)
    act = meta[(meta.get("red") == "GHCN-Daily") & (meta.get("activa_2024") == True)]  # noqa: E712
    la_c, lo_c = lat[keep[:, 0]], lon[keep[:, 1]]
    if len(act):
        dist = np.min([111.2 * np.hypot(la_c - a, (lo_c - b) * np.cos(np.radians(la_c)))
                       for a, b in zip(act["lat"], act["lon"])], axis=0)
    else:
        dist = np.full(la_c.size, np.nan)
    allst = meta[meta["dias_validos"] > 365]
    dist_all = np.min([111.2 * np.hypot(la_c - a, (lo_c - b) * np.cos(np.radians(la_c)))
                       for a, b in zip(allst["lat"], allst["lon"])], axis=0)
    df = pd.DataFrame({"lat": la_c, "lon": lo_c, "frac_rd": fr[keep[:, 0], keep[:, 1]],
                       "desacuerdo_1_menos_r_imerg_chirps": 1 - r, "tasa_cambio_condicional_spi3": flip,
                       "persistencia_anios_con_cambio": pers, "dist_estacion_ghcn_activa_km": dist,
                       "dist_cualquier_estacion_sinoptica_km": dist_all})
    prov = []
    for la_, lo_ in zip(la_c, lo_c):
        ii = np.argmin(np.abs(g.lat - (la_ - 0.025)))
        jj = np.argmin(np.abs(g.lon - (lo_ - 0.025)))
        k = g.prov_of[ii * g.shape[1] + jj]
        prov.append(g.provs[k] if k >= 0 else None)
    df["provincia"] = prov
    rk = lambda s: s.rank(pct=True)  # noqa: E731
    df["indice_prioridad"] = (rk(df["desacuerdo_1_menos_r_imerg_chirps"]) + rk(df["persistencia_anios_con_cambio"])
                              + rk(df["tasa_cambio_condicional_spi3"]) + rk(df["dist_estacion_ghcn_activa_km"])) / 4
    # sensibilidad: sin distancia; solo desacuerdo
    df["indice_sin_distancia"] = (rk(df["desacuerdo_1_menos_r_imerg_chirps"]) + rk(df["persistencia_anios_con_cambio"])
                                  + rk(df["tasa_cambio_condicional_spi3"])) / 3
    return df.sort_values("indice_prioridad", ascending=False).reset_index(drop=True)
