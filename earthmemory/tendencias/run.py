"""P0 · Tendencias de periodos secos y lluvia extrema en la República Dominicana (2001-2024), IMERG y CHIRPS.

    docker compose run --rm tendencias                     # todo: descarga (si falta), cálculo, figuras, web, informe, cuaderno
    docker compose run --rm tendencias --sin-descarga      # solo con lo que ya está en caché
    docker compose run --rm tendencias --n-sustitutos 200  # calibración más rápida (por defecto 1000)
    docker compose run --rm tendencias --desde figuras     # rehace figuras, web, informe y cuaderno sin recalcular

Escribe SOLO en data/tendencias, results/tendencias, figures/tendencias, reports_nacional y notebooks.
"""

from __future__ import annotations

import argparse
import json
import pickle
import time
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from ..hr.common import ROOT, write_json
from . import datos, descarga, motor

RES = ROOT / "results" / "tendencias"
FIG = ROOT / "figures" / "tendencias"
STATE = datos.DER / "estado_corrida.pkl"


def log(msg: str) -> None:
    print(msg, flush=True)


def compute(args) -> dict:
    t0 = time.time()
    estado_desc = {"estado": "omitida (--sin-descarga)"}
    if descarga.MANIFEST.exists():
        estado_desc = json.loads(descarga.MANIFEST.read_text(encoding="utf-8")).get("rutas", {}).get("chirps_diario", estado_desc)
    if not args.sin_descarga:
        estado_desc = descarga.ensure_chirps_daily()
    S = motor.setup()
    mask = S["mask"]
    log(f"[datos] celdas analizadas {int(mask.sum())} (incluidas para mapas/FDR: {int(S['inc'].sum())}), regiones {len(S['regions'])}")
    Pi = datos.imerg_daily()
    series = {"IMERG": motor.product_indices(datos.to_cells(Pi, mask))}
    log(f"[datos] IMERG diario {Pi.shape} listo ({time.time() - t0:.0f} s)")
    Pc = datos.chirps_daily_01()
    if Pc is not None:
        series["CHIRPS"] = motor.product_indices(datos.to_cells(Pc, mask))
        log(f"[datos] CHIRPS diario agregado a 0.1° {Pc.shape} listo ({time.time() - t0:.0f} s)")
    else:
        log("[datos] AVISO: CHIRPS diario incompleto; solo IMERG (sin clase de confianza de dos productos)")
    # coherencia diaria entre productos (celdas incluidas, días con dato en ambos)
    coh = {}
    if Pc is not None:
        a = datos.to_cells(Pi, mask)[:, S["inc"]]
        b = datos.to_cells(Pc, mask)[:, S["inc"]]
        ok = np.isfinite(a) & np.isfinite(b)
        coh = {"media_diaria_IMERG_mm": float(a[ok].mean()), "media_diaria_CHIRPS_mm": float(b[ok].mean()),
               "fraccion_dias_humedos_IMERG": float((a[ok] >= 1).mean()),
               "fraccion_dias_humedos_CHIRPS": float((b[ok] >= 1).mean()),
               "correlacion_diaria_mediana_celdas": float(np.nanmedian([np.corrcoef(a[ok[:, j], j], b[ok[:, j], j])[0, 1]
                                                                         for j in range(a.shape[1]) if ok[:, j].sum() > 100]))}
    out = motor.run_all(series, S, log=log)
    log(f"[tendencias] listo ({time.time() - t0:.0f} s); calibración con {args.n_sustitutos} sustitutos por método…")
    cal = motor.calibration({p: v for p, v in series.items()}, S, n_surr=args.n_sustitutos, log=log)
    log(f"[calibracion] listo ({time.time() - t0:.0f} s)")
    state = {"S": S, "series": {p: {k: v for k, v in d.items() if not (isinstance(k, str) and k in ("_spi3",))}
                                for p, d in series.items()},
             "spi3": {p: d["_spi3"] for p, d in series.items()}, "out": out, "cal": cal,
             "descarga": estado_desc, "coherencia_diaria": coh,
             "fecha_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
             "n_sustitutos": args.n_sustitutos, "segundos_calculo": round(time.time() - t0)}
    datos.DER.mkdir(parents=True, exist_ok=True)
    with STATE.open("wb") as fh:
        pickle.dump(state, fh)
    return state


def write_tables(state: dict) -> dict:
    RES.mkdir(parents=True, exist_ok=True)
    out, cal = state["out"], state["cal"]
    cols_c = ["celda", "lat", "lon", "provincia_principal", "indice", "periodo", "fuente", "tipo_fuente", "n", "media",
              "pendiente_decada", "ic95_inf", "ic95_sup", "pendiente_pct_decada", "S", "Z", "p", "p_sin_correccion",
              "factor_hr", "q_fdr", "sig_fdr", "signo", "mdt", "detectable", "clase_confianza", "sigma_res", "r1"]
    tc = out["celdas"][cols_c].rename(columns={"n": "n_anios", "p": "p", "p_sin_correccion": "p_mk_sin_correccion"})
    tc.to_csv(RES / "tendencias_celdas.csv", index=False, float_format="%.5g")
    cols_r = ["region", "codigo"] + cols_c[4:]
    tr = out["regiones"][cols_r].rename(columns={"n": "n_anios", "p_sin_correccion": "p_mk_sin_correccion"})
    tr.to_csv(RES / "tendencias_provincias.csv", index=False, float_format="%.5g")
    out["series_regiones"].to_csv(RES / "series_provincias.csv", index=False, float_format="%.4f")
    cal.to_csv(RES / "calibracion_fpr.csv", index=False, float_format="%.4f")
    summ = motor.summary(out["celdas"], out["regiones"], cal)
    summ.to_csv(RES / "resumen_indices.csv", index=False, float_format="%.4g")
    (RES / "por_indice").mkdir(exist_ok=True)
    for idx, g in tc.groupby("indice"):
        g.to_csv(RES / "por_indice" / f"{idx}.csv", index=False, float_format="%.5g")
    return {"resumen": summ}


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sin-descarga", action="store_true")
    ap.add_argument("--n-sustitutos", type=int, default=1000)
    ap.add_argument("--desde", choices=["calculo", "figuras", "web", "informe", "cuaderno"], default="calculo")
    ap.add_argument("--sin-cuaderno", action="store_true")
    args = ap.parse_args(argv)
    if args.desde == "calculo":
        state = compute(args)
    else:
        with STATE.open("rb") as fh:
            state = pickle.load(fh)
    tabs = write_tables(state)
    from . import figuras, informe, web
    if args.desde in ("calculo", "figuras"):
        figuras.all_figures(state)
    if args.desde in ("calculo", "figuras", "web"):
        web.export(state, tabs["resumen"])
    if args.desde in ("calculo", "figuras", "web", "informe"):
        informe.write(state, tabs["resumen"])
    if not args.sin_cuaderno:
        from . import cuaderno
        cuaderno.build()
    write_json(RES / "corrida.json", {"fecha_utc": state["fecha_utc"], "n_sustitutos": state["n_sustitutos"],
                                      "descarga_chirps": state["descarga"], "coherencia_diaria": state["coherencia_diaria"],
                                      "productos": list(state["series"]), "segundos_calculo": state["segundos_calculo"]})
    log("[tendencias] terminado")


if __name__ == "__main__":
    main()
