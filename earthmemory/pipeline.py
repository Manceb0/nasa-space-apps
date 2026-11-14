"""Earth Memory con NASA POWER (MERRA-2, 0.5° × 0.625°): motor de COMPROBACIÓN CRUZADA.

El motor principal es earthmemory.nacional (IMERG 0.1° + GLDAS 0.25°). Este se corre con
    python -m earthmemory.pipeline   (resultados en results/nacional/power_merra2/)

Otro país: --pais HTI (código ADM0_A3 de Natural Earth). La caja de descarga se calcula del polígono.
"""

from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path

import numpy as np
import pandas as pd

from phantom import drought, giovanni
from phantom import stats as pstats

from . import anomalies, contrasts, coupling, episodes, extremes, power, region

LF = "\n"
RESP_MAIN = ["GWETROOT", "GWETTOP", "EVLAND", "T2M"]


# ---------------------------------------------------------------- utilidades de salida

def _clean(o):
    if isinstance(o, dict):
        return {str(k): _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if isinstance(o, (pd.Timestamp,)):
        return o.strftime("%Y-%m-%d")
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, (float, np.floating)):
        f = float(o)
        if not math.isfinite(f):
            return None
        return float(f"{f:.6g}")
    return o


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_clean(obj), ensure_ascii=False, indent=2) + LF, encoding="utf-8", newline=LF)


def write_csv(path: Path, df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    d = df.copy()
    for c in d.columns:
        if d[c].dtype == object:
            d[c] = d[c].map(lambda v: json.dumps(_clean(v)) if isinstance(v, (list, dict)) else
                            (v.strftime("%Y-%m-%d") if isinstance(v, pd.Timestamp) else v))
    d.to_csv(path, index=False, lineterminator=LF, float_format="%.6g")


# ---------------------------------------------------------------- credenciales (solo existencia)

def earthdata_status() -> dict:
    home = Path.home()
    files = [p for p in (home / ".netrc", home / "_netrc") if p.exists()]
    has_netrc_urs = False
    for p in files:
        try:
            has_netrc_urs |= "urs.earthdata.nasa.gov" in p.read_text(errors="ignore")
        except OSError:
            pass
    tok = bool(os.environ.get("EARTHDATA_TOKEN"))
    return {"netrc_con_urs": has_netrc_urs, "EARTHDATA_TOKEN": tok, "disponible": has_netrc_urs or tok,
            "que_hace_falta": (
                "Para IMERG (GPM_3IMERGM 0.1°) y GLDAS Noah 2.1 (GLDAS_NOAH025_M 0.25°) por OPeNDAP/Harmony: "
                "una cuenta gratuita de NASA Earthdata (https://urs.earthdata.nasa.gov) con la aplicación "
                "'NASA GESDISC DATA ARCHIVE' autorizada, y UNA de estas dos cosas en la máquina que corre Docker: "
                "(1) variable de entorno EARTHDATA_TOKEN con un token generado en urs.earthdata.nasa.gov "
                "('Generate Token'), pasada al contenedor con `-e EARTHDATA_TOKEN`; o (2) un archivo .netrc con "
                "'machine urs.earthdata.nasa.gov login USUARIO password CLAVE' montado en /root/.netrc. "
                "Nadie más que el usuario debe escribir la clave.")}


# ---------------------------------------------------------------- datos

def get_data(args, manifest: power.Manifest) -> dict:
    ddir = Path(args.datos)
    ne = region.ensure_boundaries(ddir, args.pais, manifest)
    country = region.load_country(ne, args.pais)
    bbox = region.fetch_bbox(country) if args.bbox is None else tuple(args.bbox)
    monthly, meta = {}, None
    for p in power.MONTHLY_PARAMS:
        url = power.monthly_regional_url(p, bbox, args.anio0, args.anio1)
        f = power.fetch(url, ddir / "power" / f"mensual_{args.pais}_{p}_{args.anio0}_{args.anio1}.json", manifest,
                        args.refrescar)
        monthly[p], m = power.parse_regional_monthly(power.load_json(f), p)
        meta = meta or m
    places = region.LUGARES_DOM if args.pais == "DOM" else {}
    cells = region.cell_table(country, meta, monthly["GWETTOP"], monthly["EVLAND"], args.min_frac, places)
    inc = cells[cells["incluida"]]
    # celdas con diario: incluidas + vecindario del evento
    ev_lat, ev_lon = args.evento_lat, args.evento_lon
    ev_cell = cells.loc[((cells["lat"] - ev_lat).abs() <= region.DLAT / 2)
                        & ((cells["lon"] - ev_lon).abs() <= region.DLON / 2)]
    need = set(inc["celda"])
    if len(ev_cell):
        c0 = ev_cell.iloc[0]
        neigh = cells[((cells["lat"] - c0["lat"]).abs() <= region.DLAT + 1e-6)
                      & ((cells["lon"] - c0["lon"]).abs() <= region.DLON + 1e-6) & cells["incluida"]]
        need |= set(neigh["celda"]) | {c0["celda"]}
    daily = {}
    for cid in sorted(need):
        r = cells.set_index("celda").loc[cid]
        url = power.daily_point_url(["PRECTOTCORR"], r["lon"], r["lat"], f"{args.anio0}0101", f"{args.anio1}1231")
        f = power.fetch(url, ddir / "power" / "diario" / f"PRECTOTCORR_{cid}.json", manifest, args.refrescar)
        doc = power.load_json(f)
        lon, lat = doc["geometry"]["coordinates"][:2]
        if power.cell_id(lat, lon) != cid:
            raise RuntimeError(f"POWER devolvió otra celda para {cid}: {lat},{lon}")
        daily[cid] = power.parse_daily_point(doc, "PRECTOTCORR")
    return {"country": country, "bbox": bbox, "monthly": monthly, "cells": cells, "daily": pd.DataFrame(daily),
            "ev_cell": ev_cell.iloc[0]["celda"] if len(ev_cell) else None}


def extra_responses(ddir: Path, index: pd.DatetimeIndex) -> dict:
    """Gancho para respuestas nuevas (p. ej. NDVI por celda cuando llegue un pedido AppEEARS de área):
    data/nacional/extra/<VARIABLE>.csv con columnas fecha (YYYY-MM-01), celda (id lat_lon), valor."""
    out = {}
    for f in sorted((ddir / "extra").glob("*.csv")) if (ddir / "extra").exists() else []:
        d = pd.read_csv(f, parse_dates=["fecha"])
        out[f.stem.upper()] = d.pivot(index="fecha", columns="celda", values="valor").reindex(index)
    return out


# ---------------------------------------------------------------- análisis

def run(args) -> dict:
    ddir, rdir = Path(args.datos), Path(args.resultados)
    manifest = power.Manifest(ddir / "MANIFEST.json")
    D = get_data(args, manifest)
    if args.solo_descargar:
        return {}
    cells, monthly = D["cells"], D["monthly"]
    inc = sorted(cells.loc[cells["incluida"], "celda"])
    rng = (pd.Timestamp(args.anio0, 1, 1), pd.Timestamp(args.anio1, 12, 1))
    monthly = {k: v.loc[rng[0]:rng[1]] for k, v in monthly.items()}
    P = anomalies.monthly_total_mm(monthly["PRECTOTCORR"])[inc]
    spi = {k: anomalies.spi_table(P, k) for k in (1, 3, 6)}
    extra = extra_responses(ddir, P.index)
    responses = RESP_MAIN + sorted(extra)
    raw = {r: monthly[r][inc] for r in RESP_MAIN} | {k: v[inc] for k, v in extra.items()}
    zt = {kind: {r: anomalies.zscore(raw[r], kind) for r in responses} for kind in ("robusta", "estandar")}
    z = zt["robusta"]

    # --- tendencias por celda
    trows = []
    for var, df, unit in (("PRECTOTCORR", P, "mm/mes por década"), ("GWETROOT", raw["GWETROOT"], "fracción 0-1 por década"),
                          ("GWETTOP", raw["GWETTOP"], "fracción 0-1 por década"), ("T2M", raw["T2M"], "°C por década"),
                          ("EVLAND", raw["EVLAND"], "mm/día por década")):
        trows += anomalies.cell_trends(var, df, unit)
    trows = anomalies.add_bh(trows)
    trends = pd.DataFrame(trows)

    # --- acople y memoria
    st = coupling.Settings(B=args.B)
    cm = coupling.compute(z, spi, inc, responses, st)
    lagp = coupling.lag_profile(z, spi[3], inc, responses)
    ante = coupling.antecedent_table(z, spi, inc, ["GWETROOT", "GWETTOP"], st)
    ante["q_bh"] = pstats.benjamini_hochberg(ante["p_delta_gamma"].tolist())

    # --- pares
    pairs = contrasts.candidate_pairs(cells, P, spi[3])
    tests = contrasts.test_pairs(pairs, cm, responses)
    sig = tests[tests["q_bh"] < 0.05].copy()
    targets = sig if len(sig) else tests.nsmallest(10, "p")
    targets = targets.assign(z_abs=(targets["delta"] / targets["ee_boot"]).abs()).nlargest(40, "z_abs")
    variants = {
        "bloque 6 meses": st.but(block=6), "bloque 24 meses": st.but(block=24),
        "z estándar (media/DE)": None, "SPI-1 en r": st.but(spi_r=1), "SPI-6 en r": st.but(spi_r=6),
        "lag 1 mes en r": st.but(lag_r=1), "lag 2 meses en r": st.but(lag_r=2),
        "ARX forzado con SPI-3": st.but(spi_arx=3), "Spearman en r": st.but(corr="spearman"),
        "2001-2012": st.but(period=(2001, 2012)), "2013-2024": st.but(period=(2013, 2024)),
    }
    vcm = {}
    for lab, s in variants.items():
        vcm[lab] = (coupling.compute(zt["estandar"], spi, inc, responses, st) if s is None
                    else coupling.compute(z, spi, inc, responses, s))
    sens = contrasts.sensitivity(targets, vcm)
    ranked = contrasts.rank(targets.drop(columns=["z_abs"]), sens, pairs, cells)
    ranked["significativo_q05"] = ranked["q_bh"] < 0.05

    # --- episodios, contradicciones y factores
    eps, rev = [], []
    for c in inc:
        dly = D["daily"][c] if c in D["daily"] else None
        zc = {r: z[r][c] for r in ("GWETROOT", "GWETTOP")}
        eps += episodes.cell_episodes(c, spi[3][c], zc, dly)
        rev.append(episodes.reverse_counts(c, spi[3][c], z["GWETROOT"][c]))
    ep = pd.DataFrame(eps)
    contra = (ep.groupby("celda").agg(n_episodios=("inicio", "size"),
                                      n_con_retorno=("retorno_lluvia", lambda s: int(s.notna().sum())),
                                      n_A_raiz=("contradiccion_A_GWETROOT", lambda s: int((s == True).sum())),  # noqa: E712
                                      n_A_superficial=("contradiccion_A_GWETTOP", lambda s: int((s == True).sum())),  # noqa: E712
                                      mediana_meses_recuperacion_raiz=("meses_recuperacion_GWETROOT", "median"),
                                      n_recuperacion_censurada_raiz=("recuperacion_censurada_GWETROOT", "sum"))
              .reset_index().merge(pd.DataFrame(rev), on="celda"))
    outcomes = [("z_retorno_GWETROOT", "GWETROOT"), ("z_retorno_GWETTOP", "GWETTOP"),
                ("contradiccion_A_GWETROOT", "GWETROOT")]
    fac = episodes.factor_table(ep, outcomes, B=args.B)
    fsens = factor_sensitivity(ep, inc, spi, z, D["daily"], outcomes, args.B)

    # climatología de intensidad por celda (para comparar celdas de un par)
    icl = []
    for c in inc:
        d = D["daily"][c].loc[f"{args.anio0}":f"{args.anio1}"].dropna()
        p95 = episodes.heavy_threshold(d)
        icl.append({"celda": c, "p95_dias_lluvia_mm": p95, "fraccion_lluvia_en_dias_p95": float(d[d > p95].sum() / d.sum()),
                    "max_anual_1dia_mediana_mm": float(d.groupby(d.index.year).max().median()),
                    "dias_lluvia_por_anio": float((d >= 1).groupby(d.index.year).sum().mean())})
    icl = pd.DataFrame(icl)

    # episodios emparejados para los 3 mejores pares distintos
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
                                           ep[ep["celda"] == b].reset_index(drop=True))
        matched[f"{a}|{b}"] = {"episodios": m, "resumen": [episodes.paired_summary(m, v) for v in
                                                            ("z_retorno", "meses_recuperacion", "fraccion_intensa",
                                                             "max1d", "z_antecedente", "meses_previos")] if len(m) else []}

    # --- comparación con Giovanni (IMERG, GLDAS) en las dos cajas de PHANTOM
    xval = giovanni_crosscheck(cells, monthly, spi[3])

    # --- evento diario
    ev = None
    if D["ev_cell"] is not None:
        ev = {"celda": D["ev_cell"], **extremes.event_in_distribution(D["daily"][D["ev_cell"]], args.evento)}
        neigh = [c for c in D["daily"].columns if c != D["ev_cell"]]
        ev["vecinas"] = {c: {k: v for k, v in extremes.event_in_distribution(D["daily"][c], args.evento).items()
                             if k not in ("maximos_anuales", "maximos_anuales_3dias", "gev")} for c in neigh
                         if abs(cells.set_index("celda").loc[c, "lat"] - cells.set_index("celda").loc[D["ev_cell"], "lat"]) <= 0.51
                         and abs(cells.set_index("celda").loc[c, "lon"] - cells.set_index("celda").loc[D["ev_cell"], "lon"]) <= 0.63}

    R = {"args": vars(args), "bbox": D["bbox"], "country": D["country"], "cells": cells, "inc": inc,
         "P": P, "spi": spi, "z": z, "raw": raw, "daily": D["daily"], "trends": trends, "cm": cm, "lagp": lagp,
         "ante": ante, "pairs": pairs, "tests": tests, "sens": sens, "ranked": ranked, "ep": ep, "contra": contra,
         "fac": fac, "fsens": fsens, "icl": icl, "matched": matched, "xval": xval, "event": ev,
         "earthdata": earthdata_status(), "manifest": manifest.data, "responses": responses,
         "variants": list(variants), "settings": st}
    write_outputs(R, rdir)
    # Este motor (POWER/MERRA-2, ~0.5°) queda como comprobación cruzada del motor principal
    # (earthmemory.nacional: IMERG + GLDAS). Las figuras y el informe los hace el motor principal.
    return R


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
            eps += episodes.cell_episodes(c, spi[3][c], {r: z[r][c] for r in ("GWETROOT", "GWETTOP")},
                                          daily[c] if c in daily else None, **kw)
        add(label, pd.DataFrame(eps))
    return pd.DataFrame(rows)


def giovanni_crosscheck(cells: pd.DataFrame, monthly: dict, spi3_inc: pd.DataFrame) -> list[dict]:
    """POWER/MERRA-2 frente a IMERG y GLDAS (Giovanni, ya en data/giovanni) en las cajas de PHANTOM.
    No es validación independiente del suelo (los dos son modelos), pero sí de la lluvia (IMERG usa satélite)."""
    gdir = Path("data/giovanni")
    out = []
    if not gdir.exists():
        return out
    Pall = anomalies.monthly_total_mm(monthly["PRECTOTCORR"])
    for reg in ("noroeste", "jaragua"):
        fi, fg = gdir / f"imerg_precip_{reg}.csv", gdir / f"gldas_rootmoist_{reg}.csv"
        if not (fi.exists() and fg.exists()):
            continue
        gi, gg = giovanni.read_giovanni_csv(fi), giovanni.read_giovanni_csv(fg)
        box = [float(v) for v in gi.meta.get("User Bounding Box", "").split(",")]
        lon_c, lat_c = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
        sel = cells[((cells["lat"] - lat_c).abs() <= region.DLAT / 2) & ((cells["lon"] - lon_c).abs() <= region.DLON / 2)]
        if sel.empty:
            continue
        cid = sel.iloc[0]["celda"]
        imerg = gi.values.loc["2001":"2024"]
        spi_i = drought.spi(imerg, 3)
        spi_p = drought.spi(Pall[cid], 3)
        d1 = pd.DataFrame({"a": spi_i, "b": spi_p}).dropna()
        zg = anomalies.robust_z(gg.values.loc["2001":"2024"].to_frame("g"))["g"]
        zp = anomalies.robust_z(monthly["GWETROOT"][[cid]])[cid]
        d2 = pd.DataFrame({"a": zg, "b": zp}).dropna()
        out.append({"region_phantom": reg, "caja_giovanni": box, "celda_power": cid,
                    "celda_incluida": bool(sel.iloc[0]["incluida"]),
                    "r_spi3_imerg_vs_power": float(np.corrcoef(d1["a"], d1["b"])[0, 1]), "n_spi": int(len(d1)),
                    "r_z_raiz_gldas_vs_merra2": float(np.corrcoef(d2["a"], d2["b"])[0, 1]), "n_raiz": int(len(d2)),
                    "lluvia_anual_imerg_mm": float(imerg.groupby(imerg.index.year).sum().mean()),
                    "lluvia_anual_power_mm": float(Pall[cid].groupby(Pall.index.year).sum().mean())})
    return out


def write_outputs(R: dict, rdir: Path) -> None:
    write_csv(rdir / "celdas.csv", R["cells"])
    write_csv(rdir / "tendencias_celdas.csv", R["trends"])
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
    for k, v in R["matched"].items():
        write_csv(rdir / f"episodios_emparejados_{k.replace('|', '__')}.csv", v["episodios"])
    write_json(rdir / "episodios_emparejados_resumen.json", {k: v["resumen"] for k, v in R["matched"].items()})
    write_json(rdir / "comparacion_giovanni.json", R["xval"])
    if R["event"] is not None:
        write_json(rdir / "evento_santo_domingo_2023-11-18.json", R["event"])
    # series por celda (para la web u otros): z y SPI-3 mensuales
    long = []
    for name, df in [("SPI3", R["spi"][3])] + [(f"z_{r}", R["z"][r]) for r in R["responses"]]:
        d = df.copy()
        d.index.name = "fecha"
        long.append(d.reset_index().melt(id_vars="fecha", var_name="celda", value_name=name).set_index(["fecha", "celda"]))
    write_csv(rdir / "series_mensuales_celdas.csv", pd.concat(long, axis=1).reset_index())
    write_json(rdir / "corrida.json", {
        "pais": R["args"]["pais"], "caja_descarga": R["bbox"], "anios": [R["args"]["anio0"], R["args"]["anio1"]],
        "celdas_total": int(len(R["cells"])), "celdas_incluidas": int(len(R["inc"])),
        "respuestas": R["responses"], "ajustes_principales": R["settings"].__dict__,
        "variantes_sensibilidad": R["variants"], "earthdata": R["earthdata"],
        "n_pruebas_pares": int(R["tests"]["p"].notna().sum()) if len(R["tests"]) else 0,
        "n_pruebas_pares_q05": int((R["tests"]["q_bh"] < 0.05).sum()) if len(R["tests"]) else 0,
    })


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pais", default="DOM")
    ap.add_argument("--bbox", nargs=4, type=float, default=None, metavar=("LON0", "LAT0", "LON1", "LAT1"))
    ap.add_argument("--anio0", type=int, default=2001)
    ap.add_argument("--anio1", type=int, default=2024)
    ap.add_argument("--min-frac", dest="min_frac", type=float, default=region.MIN_FRAC)
    ap.add_argument("--datos", default="data/nacional")
    ap.add_argument("--resultados", default="results/nacional/power_merra2")
    ap.add_argument("--figuras", default="figures/nacional")
    ap.add_argument("--informe", default="reports_nacional/EARTH_MEMORY.md")
    ap.add_argument("--evento", default="2023-11-18")
    ap.add_argument("--evento-lat", dest="evento_lat", type=float, default=18.47)
    ap.add_argument("--evento-lon", dest="evento_lon", type=float, default=-69.90)
    ap.add_argument("--B", type=int, default=2000)
    ap.add_argument("--refrescar", action="store_true", help="vuelve a descargar aunque haya caché")
    ap.add_argument("--solo-descargar", dest="solo_descargar", action="store_true")
    run(ap.parse_args(argv))


if __name__ == "__main__":
    main()
