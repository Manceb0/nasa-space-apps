"""Pipeline completo de PHANTOM.

Uso:
    uv run python -m phantom.pipeline
    uv run python -m phantom.pipeline --appeears data/appeears --out results

Si la carpeta de AppEEARS no tiene resultados todavía, corre solo la parte de sequías
y lo deja escrito en results/estado_modis.json. Nunca usa datos sintéticos.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from . import appeears, audit, drought, export_web, figures, giovanni, recovery, stats

REGIONS = ("noroeste", "jaragua")
PRIMARY = {"verde": "ndvi", "umbral": -1.0, "persistencia": 3}
HORIZON_DAYS = 365
LF = "\n"  # fin de línea fijo: la misma salida en Windows, Linux y Docker


def _json_default(o):
    if isinstance(o, (pd.Timestamp, datetime)):
        return o.strftime("%Y-%m-%d")
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return None if np.isnan(o) else float(o)
    if isinstance(o, np.bool_):
        return bool(o)
    if o is pd.NaT:
        return None
    raise TypeError(type(o))


def write_json(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=_json_default), encoding="utf-8", newline=LF)


def region_of_point(pid: str, category: str) -> str | None:
    if category == "noroeste" or pid.startswith("montecristi") or pid.startswith("sierra"):
        return "noroeste"
    if pid.startswith("jaragua"):
        return "jaragua"
    return None  # sin serie climática de Giovanni (p. ej. cordillera)


def run_climate(gdir: Path, out: Path, figdir: Path) -> tuple[dict, dict]:
    series = giovanni.load_folder(gdir)
    validation = [giovanni.validate_monthly(s) for s in series.values()]
    write_json(out / "giovanni_validacion.json", validation)

    catalogs, events = [], {}
    for reg in REGIONS:
        p = series[f"imerg_precip_{reg}"].values
        soil = series[f"gldas_rootmoist_{reg}"].values
        catalogs.append(drought.drought_catalog(p, soil, reg))
        ev = drought.primary_events(p)
        ev.insert(0, "region", reg)
        events[reg] = ev
    cat = pd.concat(catalogs, ignore_index=True)
    cat.to_csv(out / "sequias_catalogo.csv", index=False, lineterminator=LF)
    pd.concat(events.values(), ignore_index=True).to_csv(out / "eventos_principales.csv", index=False, lineterminator=LF)
    figures.fig_droughts(series, events, figdir / "fig1_sequias")
    figures.fig_criteria(cat, figdir / "fig2_criterios_sequia")
    return series, events


def _stop_dates(ev: pd.DataFrame, series_end: pd.Timestamp) -> list[pd.Timestamp]:
    stops = []
    for i, r in ev.iterrows():
        end = r["fin"] + pd.offsets.MonthEnd(0)
        nxt = ev["inicio"].iloc[i + 1] if i + 1 < len(ev) else series_end
        stops.append(min(nxt, end + pd.Timedelta(days=HORIZON_DAYS), series_end))
    return stops


def run_modis(adir: Path, series: dict, events: dict, out: Path, figdir: Path) -> dict:
    data, log = appeears.load_point_sample(adir)
    needed = {"MOD13Q1", "MOD17A2HGF", "MOD11A2"}
    if not needed.issubset(data):
        status = {"estado": "pendiente", "faltan": sorted(needed - set(data)), "registro": log,
                  "nota": "Sin resultados MODIS: no se calculó ninguna recuperación."}
        write_json(out / "estado_modis.json", status)
        return status

    lc = appeears.landcover_stability(data["MCD12Q1"]) if "MCD12Q1" in data else pd.DataFrame()
    vi, lst, gpp = data["MOD13Q1"], data["MOD11A2"], data["MOD17A2HGF"]
    rows, sens_rows, figs = [], [], []
    zseries: dict[str, dict] = {}
    audits: list[dict] = []
    series_end = pd.Timestamp("2024-12-31")
    points = vi[["id", "categoria"]].drop_duplicates().itertuples(index=False)

    for pid, catg in points:
        reg = region_of_point(pid, catg)
        lc_row = lc[lc["id"] == pid].to_dict("records")[0] if len(lc) else None
        if reg is None:
            log.append(f"{pid}: sin región climática; se omite del análisis por eventos")
            continue
        if lc_row is not None and not lc_row["usar"]:
            log.append(f"{pid}: excluido por cobertura del suelo {lc_row['clases_2001_2021']}")
            continue

        v = vi[vi["id"] == pid].sort_values("fecha")
        g = gpp[gpp["id"] == pid].sort_values("fecha")
        t = lst[lst["id"] == pid].sort_values("fecha")
        tair = series[f"merra2_t2m_{reg}"].values
        t_air = t["fecha"].dt.to_period("M").dt.to_timestamp().map(tair)
        green = {
            "ndvi": recovery.robust_seasonal_z(v["fecha"], v["ndvi"], 16),
            "evi": recovery.robust_seasonal_z(v["fecha"], v["evi"], 16),
        }
        funcs = {
            "gpp_modelo": recovery.robust_seasonal_z(g["fecha"], g["gpp"], 8),
            "lst_menos_aire": recovery.robust_seasonal_z(t["fecha"], t["lst_c"].to_numpy() - t_air.to_numpy(), 8,
                                                         invert=True),
        }
        if "MOD09A1" in data:  # agua del dosel (NDII), observada, independiente del verdor
            w = data["MOD09A1"][data["MOD09A1"]["id"] == pid].sort_values("fecha")
            if w["ndii"].notna().sum() > 50:
                funcs["ndii_agua"] = recovery.robust_seasonal_z(w["fecha"], w["ndii"], 8)
        # Series z (las mismas que usa el cálculo de recuperación) para la doble línea de la web
        zseries[pid] = {name: {"fechas": [d.strftime("%Y-%m-%d") for d in z.dropna().index],
                               "z": [round(float(v), 2) for v in z.dropna()]}
                        for name, z in {"ndvi": green["ndvi"], "evi": green["evi"], **funcs}.items()}
        ev = events[reg].reset_index(drop=True)
        stops = _stop_dates(ev, series_end)
        for (i, e), stop in zip(ev.iterrows(), stops):
            e_end = e["fin"] + pd.offsets.MonthEnd(0)
            nxt = ev["inicio"].iloc[i + 1] if i + 1 < len(ev) else None
            aud = audit.audit_recovery({**green, **funcs}, e["inicio"], e_end, stop, nxt)
            audits.append({"id": pid, "region": reg, "evento_inicio": e["inicio"], "evento_fin": e_end,
                           "fin_ventana": stop, "evento_severidad_spi3": e["severidad"], **aud})
            recs = {}
            for fname, fz in funcs.items():
                prim = recovery.event_gap(green[PRIMARY["verde"]], fz, e["inicio"], e_end, stop,
                                          PRIMARY["umbral"], PRIMARY["persistencia"])
                sens = recovery.sensitivity(green, fz, e["inicio"], e_end, stop)
                sens.insert(0, "funcion", fname)
                sens.insert(0, "evento_inicio", e["inicio"])
                sens.insert(0, "id", pid)
                sens_rows.append(sens)
                recs["ndvi"] = prim["verde_recuperacion"]
                recs[fname] = prim["funcion_recuperacion"]
                rob = recovery.robustness_label(sens, prim["dt_dias"])
                cut_by_next = i + 1 < len(ev) and stop == ev["inicio"].iloc[i + 1]
                green_hit = prim["estado"] not in ("sin_impacto", "sin_impacto_verde")
                rows.append({"id": pid, "region": reg, "evento_inicio": e["inicio"], "evento_fin": e_end,
                             "evento_severidad_spi3": e["severidad"], "fin_ventana": stop, "funcion": fname,
                             "ventana_cortada_por_siguiente_sequia": bool(cut_by_next),
                             # Recovery Collision: el verdor seguía bajo su banda cuando empezó la siguiente sequía
                             "colision_verde": bool(cut_by_next and green_hit and prim["verde_recuperacion"] is None),
                             # La función toca fondo DESPUÉS de que el verdor ya se recuperó: es otra caída, no una recuperación tardía
                             "funcion_cae_despues_del_verde": bool(prim["verde_recuperacion"] is not None
                                                                   and prim["funcion_minimo"] is not None
                                                                   and prim["funcion_minimo"] > prim["verde_recuperacion"]),
                             **prim, **{f"rob_{k}": val for k, val in rob.items()}})
            if e["severidad"] <= ev["severidad"].nsmallest(3).max():
                stem = figdir / f"fig3_evento_{pid}_{e['inicio']:%Y-%m}"
                figs += figures.fig_event(pid, e["inicio"], e_end, stop, {"ndvi": green["ndvi"], **funcs}, recs, stem,
                                          threshold=PRIMARY["umbral"])

    write_json(out / "zseries.json", zseries)
    write_json(out / "auditorias.json", audits)
    res = pd.DataFrame(rows)
    res.to_csv(out / "recuperacion_eventos.csv", index=False, lineterminator=LF)
    if sens_rows:
        sens_all = pd.concat(sens_rows, ignore_index=True)
        sens_all.to_csv(out / "sensibilidad.csv", index=False, lineterminator=LF)
        if (sens_all["estado"] == "ambos_recuperados").any():
            figs += figures.fig_sensitivity(sens_all, figdir / "fig4_sensibilidad_dt")

    # Tendencias: Δt por evento (si hay >= 4 eventos recuperados) y verdor/función anual.
    tests = []
    for (pid, fname), gr in res.groupby(["id", "funcion"]) if len(res) else []:
        ok = gr[gr["estado"] == "ambos_recuperados"]
        yrs = ok["evento_inicio"].dt.year + ok["evento_inicio"].dt.month / 12
        mk = stats.mann_kendall(ok["dt_dias"])
        ts = stats.theil_sen(yrs, ok["dt_dias"])
        tests.append({"prueba": "tendencia_dt", "id": pid, "funcion": fname, **mk,
                      "pendiente_dias_por_anio": ts["pendiente"], "ic_bajo": ts["ic_bajo"], "ic_alto": ts["ic_alto"],
                      "autocorr_lag1": stats.lag1_autocorr(ok["dt_dias"])})
    for name, df, col in (("ndvi", vi, "ndvi"), ("gpp", gpp, "gpp"), ("lst_c", lst, "lst_c")):
        for pid, gr in df.groupby("id"):
            annual = gr.groupby(gr["fecha"].dt.year)[col].mean()
            mk = stats.mann_kendall(annual.to_numpy())
            ts = stats.theil_sen(annual.index.to_numpy(), annual.to_numpy())
            tests.append({"prueba": f"tendencia_anual_{name}", "id": pid, "funcion": None, **mk,
                          "pendiente_dias_por_anio": None, "pendiente_por_anio": ts["pendiente"],
                          "ic_bajo": ts["ic_bajo"], "ic_alto": ts["ic_alto"],
                          "autocorr_lag1": stats.lag1_autocorr(annual.to_numpy())})
    q = stats.benjamini_hochberg([t["p"] for t in tests])
    for t, qq in zip(tests, q):
        t["q_bh"] = qq
    tdf = pd.DataFrame(tests)
    tdf.to_csv(out / "tendencias.csv", index=False, lineterminator=LF)

    summary = {
        "estado": "procesado",
        "registro": log,
        "cobertura_suelo": lc.to_dict("records") if len(lc) else None,
        "n_filas_evento": int(len(res)),
        "estados": res["estado"].value_counts().to_dict() if len(res) else {},
        "etiquetas": res["rob_etiqueta"].value_counts().to_dict() if len(res) else {},
        "n_pruebas_estadisticas": int(sum(t["p"] is not None for t in tests)),
        "dt_por_funcion": {
            f: stats.bootstrap_mean_ci(gr.loc[gr["estado"] == "ambos_recuperados", "dt_dias"].tolist())
            for f, gr in res.groupby("funcion")
        } if len(res) else {},
        "figuras": figs,
    }
    write_json(out / "estado_modis.json", summary)
    return summary


def write_results_md(md_path: Path, out: Path, validation_path: Path, modis: dict) -> None:
    val = json.loads(validation_path.read_text(encoding="utf-8"))
    ev = pd.read_csv(out / "eventos_principales.csv", parse_dates=["inicio", "fin", "recuperacion_candidata"])
    lines = [
        "# RESULTS",
        "",
        f"Generado por `phantom.pipeline` el {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC. "
        "Este archivo se reescribe en cada corrida; no editarlo a mano.",
        "",
        "## 1. Datos climáticos (Giovanni)",
        "",
        "| Archivo | Fechas | Faltantes | Reconstruido | OK |",
        "|---|---|---|---|---|",
    ]
    for v in val:
        lines.append(f"| `{v['archivo']}` | {v['n_fechas']} ({v['inicio']} → {v['fin']}) | {v['faltantes']} | "
                     f"{'sí' if v['reconstruido'] else 'no'} | {'sí' if v['ok'] else 'NO: ' + '; '.join(v['problemas'])} |")
    lines += ["", "## 2. Sequías usadas para el análisis (SPI-3 ≤ −1 durante 2+ meses, IMERG)", "",
              "| Región | Inicio | Fin | Meses | Severidad (suma SPI-3) | Pico | Vuelve a SPI-3 ≥ 0 |",
              "|---|---|---|---|---|---|---|"]
    for _, r in ev.sort_values(["region", "severidad"]).iterrows():
        rec = r["recuperacion_candidata"]
        lines.append(f"| {r['region']} | {r['inicio']:%Y-%m} | {r['fin']:%Y-%m} | {r['duracion_meses']} | "
                     f"{r['severidad']:.2f} | {r['pico']:.2f} | {'' if pd.isna(rec) else f'{rec:%Y-%m}'} |")
    lines += ["", "Catálogo completo con los tres criterios: `results/sequias_catalogo.csv`. "
              "Figuras: `figures/fig1_sequias.pdf` y `figures/fig2_criterios_sequia.pdf` (leyendas en `figures/LEYENDAS.md`).", "", "## 3. Recuperación verde vs. función (MODIS)", ""]
    if modis.get("estado") != "procesado":
        lines += [f"**Pendiente.** {modis.get('nota', '')} Faltan: {', '.join(modis.get('faltan', []))}.",
                  "", "No hay ningún resultado sobre la brecha todavía."]
    else:
        lines += [f"- Filas evento × punto × señal: {modis['n_filas_evento']}",
                  f"- Estados: {modis['estados']}",
                  f"- Etiquetas de robustez: {modis['etiquetas']}",
                  f"- Pruebas estadísticas hechas (para leer los p con cuidado): {modis['n_pruebas_estadisticas']}",
                  "", "Δt medio (días, función − verde, solo eventos con ambas recuperaciones):", ""]
        for f, d in modis["dt_por_funcion"].items():
            ic = f"[{d['ic95'][0]:.0f}, {d['ic95'][1]:.0f}]" if d.get("ic95") else "—"
            media = f"{d['media']:.0f}" if d.get("media") is not None else "—"
            lines.append(f"- `{f}`: n = {d['n']}, media = {media} días, IC95 bootstrap = {ic}")
        rec = pd.read_csv(out / "recuperacion_eventos.csv")
        both = rec[rec["estado"] == "ambos_recuperados"]
        after, before = int((both["dt_dias"] > 32).sum()), int((both["dt_dias"] < -32).sum())
        lines += ["",
                  f"De {len(both)} comparaciones con ambas recuperaciones: {len(both) - after - before} dentro de ±32 días "
                  f"(precisión del método), {before} con la función antes que el verdor y {after} después.",
                  "Robustos (≥ 80 % de las combinaciones con el mismo signo y |mediana| > 32 días): " +
                  "; ".join(f"{r.id} {str(r.evento_inicio)[:7]} {r.funcion} Δt = {r.dt_dias:.0f}"
                            for r in rec[rec["rob_etiqueta"] == "ROBUSTO"].itertuples()) + ".",
                  "",
                  "Casos donde la función toca fondo después de que el verdor ya se recuperó (otra caída, no una "
                  "recuperación tardía): " + ("; ".join(f"{r.id} {str(r.evento_inicio)[:7]} {r.funcion}" for r in
                  rec[rec.get("funcion_cae_despues_del_verde", False) == True].itertuples()) or "ninguno") + ".",
                  "",
                  "**Lectura:** en estos puntos la hipótesis de PHANTOM (la función se recupera *después* del verdor) "
                  "no se sostiene. El único caso robusto en esa dirección (GPP, un modelo, en Jaragua 2015) es una caída "
                  "de GPP que empieza después de que el NDVI ya se había recuperado: no es una recuperación tardía. "
                  "El IC bootstrap trata cada comparación como independiente, pero no lo son (los puntos de Montecristi "
                  "comparten sequías); es optimista."]
        lines += ["", "Detalle: `results/recuperacion_eventos.csv`, `results/sensibilidad.csv`, "
                  "`results/tendencias.csv`.", "",
                  "Cinco puntos son una exploración. Estos números no describen bosques completos."]
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline=LF)


def append_trends_md(md_path: Path, web_data: Path) -> None:
    """Añade a RESULTS.md la tabla de tendencias que muestra la herramienta (mismos JSON)."""
    idx = json.loads((web_data / "index.json").read_text(encoding="utf-8"))
    lines = ["", "## 4. Tendencias 2001–2024 (herramienta de detective)", "",
             "Anomalía anual (se quita el ciclo estacional). Pendiente Theil-Sen por década con IC 95 %; p de "
             f"Mann-Kendall corregido por autocorrelación AR(1); q de Benjamini-Hochberg sobre las {len(idx['series'])} series. "
             "Las series MODIS son la media de anomalías de los puntos de cada zona (años con 9 meses o más).", "",
             "| Serie | Pendiente / década | IC 95 % | p corregido (p simple) | q | Veredicto | Ventanas que engañan |",
             "|---|---|---|---|---|---|---|"]
    sig, qs = [], []
    for item in idx["series"]:
        d = json.loads((web_data / "series" / f"{item['id']}.json").read_text(encoding="utf-8"))
        c = d["completa"]
        if c["veredicto"] in ("sube", "baja"):
            sig.append(f"{idx['variables'][d['variable']]['nombre']} · {idx['regiones'][d['region']]['nombre']} ({c['veredicto']})")
            qs.append(c["q_bh"])
        unit = idx["variables"][d["variable"]]["unidad"]
        traps = ", ".join(f"{w['inicio']}–{w['fin']}" for w in d["ventanas_que_enganan"]) or "—"
        lines.append(
            f"| {idx['variables'][d['variable']]['nombre']} · {idx['regiones'][d['region']]['nombre']} | "
            f"{c['pendiente_decada']:+.3f} {unit} | [{c['ic95_decada'][0]:+.3f}, {c['ic95_decada'][1]:+.3f}] | "
            f"{c['p_mk']:.3f} ({c['p_mk_simple']:.3f}) | {c['q_bh']:.3f} | {c['veredicto']} | {traps} |")
    survive = [s for s, q in zip(sig, qs) if q < 0.05]
    lines += ["",
              f"Lectura: con p corregido < 0,05 e IC sin el cero: {', '.join(sig) or 'ninguna'}. "
              f"Al corregir por las {len(idx['series'])} pruebas (q < 0,05) se mantienen: {', '.join(survive) or 'ninguna'}. "
              "\"Sin evidencia\" no significa \"sin cambio\": los IC muestran qué cambios siguen siendo posibles."]
    with md_path.open("a", encoding="utf-8", newline=LF) as fh:
        fh.write(LF.join(lines) + LF)


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=".")
    ap.add_argument("--giovanni", default="data/giovanni")
    ap.add_argument("--appeears", default="data/appeears")
    ap.add_argument("--out", default="results")
    ap.add_argument("--figures", default="figures")
    ap.add_argument("--results-md", default="RESULTS.md")
    ap.add_argument("--web", default="web/public/data", help="carpeta de datos de la web ('' para no exportar)")
    a = ap.parse_args(argv)
    root = Path(a.root)
    out, figdir = root / a.out, root / a.figures
    out.mkdir(parents=True, exist_ok=True)
    figdir.mkdir(parents=True, exist_ok=True)
    series, events = run_climate(root / a.giovanni, out, figdir)
    adir = root / a.appeears
    adir.mkdir(parents=True, exist_ok=True)
    modis = run_modis(adir, series, events, out, figdir)
    write_results_md(root / a.results_md, out, out / "giovanni_validacion.json", modis)
    if a.web:
        export_web.export(root, out, root / a.web)
        append_trends_md(root / a.results_md, root / a.web)
    print(f"listo: {out}  (MODIS: {modis.get('estado')})")


if __name__ == "__main__":
    main()
