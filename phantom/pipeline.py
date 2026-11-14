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

from . import appeears, drought, figures, giovanni, recovery, stats

REGIONS = ("noroeste", "jaragua")
PRIMARY = {"verde": "ndvi", "umbral": -1.0, "persistencia": 3}
HORIZON_DAYS = 365


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
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=_json_default), encoding="utf-8")


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
    cat.to_csv(out / "sequias_catalogo.csv", index=False)
    pd.concat(events.values(), ignore_index=True).to_csv(out / "eventos_principales.csv", index=False)
    figures.drought_timeline(series, events, figdir / "sequias_timeline.png")
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
        ev = events[reg].reset_index(drop=True)
        stops = _stop_dates(ev, series_end)
        for (i, e), stop in zip(ev.iterrows(), stops):
            e_end = e["fin"] + pd.offsets.MonthEnd(0)
            for fname, fz in funcs.items():
                prim = recovery.event_gap(green[PRIMARY["verde"]], fz, e["inicio"], e_end, stop,
                                          PRIMARY["umbral"], PRIMARY["persistencia"])
                sens = recovery.sensitivity(green, fz, e["inicio"], e_end, stop)
                sens.insert(0, "funcion", fname)
                sens.insert(0, "evento_inicio", e["inicio"])
                sens.insert(0, "id", pid)
                sens_rows.append(sens)
                rob = recovery.robustness_label(sens, prim["dt_dias"])
                rows.append({"id": pid, "region": reg, "evento_inicio": e["inicio"], "evento_fin": e_end,
                             "evento_severidad_spi3": e["severidad"], "fin_ventana": stop, "funcion": fname,
                             **prim, **{f"rob_{k}": val for k, val in rob.items()}})
            if e["severidad"] <= ev["severidad"].nsmallest(3).max():
                fp = figdir / f"evento_{pid}_{e['inicio']:%Y-%m}.png"
                figures.event_panel(pid, e["inicio"], e_end, stop, green["ndvi"], funcs, fp)
                figs.append(fp.name)

    res = pd.DataFrame(rows)
    res.to_csv(out / "recuperacion_eventos.csv", index=False)
    if sens_rows:
        pd.concat(sens_rows, ignore_index=True).to_csv(out / "sensibilidad.csv", index=False)

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
    tdf.to_csv(out / "tendencias.csv", index=False)

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


def write_results_md(root: Path, out: Path, validation_path: Path, modis: dict) -> None:
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
              "Figura: `figures/sequias_timeline.png`.", "", "## 3. Recuperación verde vs. función (MODIS)", ""]
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
            lines.append(f"- `{f}`: n = {d['n']}, media = {d['media']}, IC95 bootstrap = {d['ic95']}")
        lines += ["", "Detalle: `results/recuperacion_eventos.csv`, `results/sensibilidad.csv`, "
                  "`results/tendencias.csv`.", "",
                  "Cinco puntos son una exploración. Estos números no describen bosques completos."]
    (root / "RESULTS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=".")
    ap.add_argument("--giovanni", default="data/giovanni")
    ap.add_argument("--appeears", default="data/appeears")
    ap.add_argument("--out", default="results")
    ap.add_argument("--figures", default="figures")
    a = ap.parse_args(argv)
    root = Path(a.root)
    out, figdir = root / a.out, root / a.figures
    out.mkdir(parents=True, exist_ok=True)
    figdir.mkdir(parents=True, exist_ok=True)
    series, events = run_climate(root / a.giovanni, out, figdir)
    adir = root / a.appeears
    adir.mkdir(parents=True, exist_ok=True)
    modis = run_modis(adir, series, events, out, figdir)
    write_results_md(root, out, out / "giovanni_validacion.json", modis)
    print(f"listo: {out}  (MODIS: {modis.get('estado')})")


if __name__ == "__main__":
    main()
