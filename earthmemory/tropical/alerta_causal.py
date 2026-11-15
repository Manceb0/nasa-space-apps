"""Alerta con testigo, versión CAUSAL (corrige alerta_acuerdo.py tras la revisión del 15-nov).

Cambios frente a la versión retrospectiva:
- La confirmación de CHIRPS solo puede venir del mismo día o del anterior (información ya observada al emitir). Antes
  se permitía el día siguiente (mirar al futuro).
- CHIRPS: máximo de celda de la SUMA de 48 h en la misma celda (antes: suma de dos máximos diarios que podían ser de
  celdas distintas). Se usa la misma rejilla y los mismos pesos de cuenca que el caso Yuna.
- Además de «detectado», se separa el MOMENTO del primer disparo respecto al inicio del evento: antes (anticipado),
  el día de inicio, durante, o ninguno; y el RETRASO que añade la confirmación.
Límites que no se corrigen aquí: CHIRPS no llega en tiempo real (latencia de días o semanas), su diario se reparte
desde la péntada, el catálogo es de prensa (puede faltar inundaciones) y las fechas de inicio tienen precisión variable.
Ejecutar: docker compose run --rm --entrypoint uv tropical run --frozen --no-sync python -m earthmemory.tropical.alerta_causal
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from shapely.geometry import shape

from ..hr.common import ROOT, write_json
from ..yuna import analisis as an
from ..yuna.catalogo import ventanas
from ..yuna.common import RES as YRES
from ..yuna.common import TEND
from ..yuna.series import cell_weights, wmax

OUT = ROOT / "results" / "tropical" / "alerta_causal"
PREDICCIONES = {
    "M1": "Prueba 2016-2024, versión causal: exigir confirmación de CHIRPS del mismo día o del anterior conserva al "
          "menos 6 de 8 eventos y deja las falsas alarmas en ≤ 60 % de las de IMERG solo.",
    "M2": "La confirmación retrasa el primer disparo al menos 1 día en la mitad o más de los eventos que detectan ambas "
          "reglas.",
    "M3": "Con IMERG solo, menos de la mitad de los eventos de prueba tienen un disparo anticipado (antes del inicio o el "
          "mismo día de inicio).",
}


def chirps_max48(geom) -> pd.Series:
    from scipy.io import netcdf_file
    parts, w = [], None
    for f in sorted((TEND / "chirps_diario").glob("chirps_v2p0_diario_RD_*.nc")):
        with netcdf_file(f, "r", mmap=False) as nc:
            v = nc.variables
            X, Y, T = (np.asarray(v[k][:], float) for k in ("X", "Y", "T"))
            units = v["T"].units.decode() if isinstance(v["T"].units, bytes) else v["T"].units
            P = np.asarray(v["prcp"][:], float)
            fv = getattr(v["prcp"], "missing_value", None)
        if fv is not None:
            P[P == float(fv)] = np.nan
        P[P < 0] = np.nan
        if Y[0] > Y[-1]:
            Y, P = Y[::-1], P[:, ::-1, :]
        if "julian" in units:
            dates = pd.to_datetime(T, unit="D", origin="julian").normalize()
        else:
            m = re.search(r"since (\d{4})-(\d{1,2})-(\d{1,2})", units)
            dates = pd.Timestamp(int(m.group(1)), int(m.group(2)), int(m.group(3))) + pd.to_timedelta(np.floor(T), "D")
        if w is None:
            w = cell_weights(Y, X, 0.05, geom).ravel()
        parts.append(pd.DataFrame(P.reshape(P.shape[0], -1), index=pd.DatetimeIndex(dates)))
    Xf = pd.concat(parts).sort_index()
    Xf = Xf[~Xf.index.duplicated()]
    X48 = Xf.rolling(2, min_periods=2).sum().to_numpy()
    return pd.Series(wmax(X48, w, 0.5), index=Xf.index)


def momento(trig: pd.Series, vent: list, periodo) -> pd.DataFrame:
    y0, y1 = periodo
    filas = []
    for a, b, i in vent:
        if not y0 <= a.year <= y1:
            continue
        w = trig[(trig.index >= a - pd.Timedelta(days=an.TOL)) & (trig.index <= b)].fillna(False).astype(bool)
        f = w[w].index.min() if w.any() else None
        if f is None:
            cl = "ninguno"
        elif f < a:
            cl = "antes del inicio"
        elif f == a:
            cl = "el día de inicio"
        else:
            cl = "durante"
        filas.append({"id": i, "inicio": a.date(), "primer_disparo": f.date() if f is not None else None, "momento": cl})
    return pd.DataFrame(filas)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / "predicciones_registradas.json"
    if not p.exists():
        write_json(p, {"registradas_utc": datetime.now(timezone.utc).isoformat(), **PREDICCIONES})
    d = pd.read_parquet(an.RES / "series_diarias_zonas.parquet")
    d.index = pd.DatetimeIndex(d.index)
    geo = json.loads((YRES / "cuencas_yuna.geojson").read_text(encoding="utf-8"))
    geom = {f["properties"]["zona"]: shape(f["geometry"]) for f in geo["features"]}["yuna"]
    cat = pd.read_csv(an.RES / "catalogo_eventos.csv")
    vent = ventanas(cat)
    A = d["imerg_max48_yuna"] > 100
    C48 = chirps_max48(geom).reindex(d.index)
    C = C48 > 100
    Cc = C | C.shift(1, fill_value=False)                      # mismo día o anterior: ya observado
    trig = {"A_IMERG": A, "C_CHIRPS_48h_misma_celda": C, "A_y_C_causal": A & Cc}
    filas, mom = [], {}
    for nombre, t in trig.items():
        for per, lab in ((an.CAL, "calibración 2001-2015"), (an.TEST, "prueba 2016-2024")):
            r = an.puntuar(t, vent, per)
            s = r["tot"]
            m = an.metricas_ep(s["h"], s["m"], s["fa"], s["ep"])
            M = momento(t, vent, per)
            mom[(nombre, lab)] = M
            filas.append({"disparador": nombre, "periodo": lab, "eventos": s["h"] + s["m"], "aciertos": s["h"],
                          "anticipados": int(M["momento"].isin(["antes del inicio", "el día de inicio"]).sum()),
                          "durante": int((M["momento"] == "durante").sum()), "episodios": s["ep"],
                          "falsas_alarmas": s["fa"], "POD": m["POD"], "CSI": m["CSI"],
                          "CSI_ic95": an.bootstrap(r["por_anio"])["CSI"]})
    T = pd.DataFrame(filas)
    T.to_csv(OUT / "backtest_causal.csv", index=False, float_format="%.3f")
    detalle = pd.concat({f"{k[0]} | {k[1]}": v for k, v in mom.items()}).reset_index(level=0)
    detalle.to_csv(OUT / "momento_por_evento.csv", index=False)
    # retraso de la confirmación
    ret = []
    for lab in ("calibración 2001-2015", "prueba 2016-2024"):
        a = mom[("A_IMERG", lab)].set_index("id")["primer_disparo"]
        c = mom[("A_y_C_causal", lab)].set_index("id")["primer_disparo"]
        for i in a.index:
            if a[i] is not None and c.get(i) is not None:
                ret.append({"periodo": lab, "id": i, "retraso_dias": (pd.Timestamp(c[i]) - pd.Timestamp(a[i])).days})
    R = pd.DataFrame(ret)
    R.to_csv(OUT / "retraso_confirmacion.csv", index=False)
    pr = T[T["periodo"].str.startswith("prueba")].set_index("disparador")
    rt = R[R["periodo"].str.startswith("prueba")]["retraso_dias"]
    ver = {"M1": bool(pr.loc["A_y_C_causal", "aciertos"] >= 6
                      and pr.loc["A_y_C_causal", "falsas_alarmas"] <= 0.6 * pr.loc["A_IMERG", "falsas_alarmas"]),
           "M2": bool(len(rt) and (rt >= 1).mean() >= 0.5),
           "M3": bool(pr.loc["A_IMERG", "anticipados"] < pr.loc["A_IMERG", "eventos"] / 2)}
    write_json(OUT / "resumen.json", {"veredicto": ver, "retraso_prueba": rt.tolist(),
                                      "tabla": json.loads(T.to_json(orient="records"))})
    pd.set_option("display.width", 230)
    print(T.round(3).to_string())
    print(R.to_string())
    print(detalle[detalle["level_0"].str.contains("prueba")].to_string())
    print(ver)


if __name__ == "__main__":
    main()
