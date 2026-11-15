"""¿Una alerta de inundación que pide testigos funciona mejor que una que cree a un solo producto? (cuenca del Yuna)

Mismo backtest y mismo catálogo de eventos que el caso Yuna (earthmemory/yuna/analisis.py): calibración 2001-2015,
prueba 2016-2024, evento detectado si hay disparo en [inicio − 2 d, fin], episodios separados por > 3 días, IC por
bootstrap de años. Disparadores:
  A   = IMERG: máximo de celda en la cuenca > 100 mm en 48 h (la regla tipo sEAP del caso Yuna)
  C   = CHIRPS: suma de 2 días del máximo de celda diario > 100 mm (aproximación por arriba del máximo en 48 h)
  A∧C = alerta solo si los dos productos la dan (± 1 día)
  A∨C = alerta si cualquiera la da
Predicción registrada antes de correr. Ningún umbral se recalibra: se usan los 100 mm de la regla original.
Ejecutar: docker compose run --rm --entrypoint uv tropical run --frozen --no-sync python -m earthmemory.tropical.alerta_acuerdo
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from ..hr.common import ROOT, write_json
from ..yuna import analisis as an

from ..yuna.catalogo import ventanas

OUT = ROOT / "results" / "tropical" / "alerta_acuerdo"
PREDICCION = {
    "K1": "En la prueba 2016-2024, exigir acuerdo (A∧C) conserva al menos 6 de los 8 eventos y reduce las falsas "
          "alarmas de A al menos a la mitad (de 39 a ≤ 20).",
    "K2": "A∨C no mejora el CSI de A en la prueba (añade más falsas alarmas que aciertos).",
    "nota": "n = 8 eventos de prueba: un evento mueve el POD 12,5 puntos. Resultado indicativo, no operativo.",
}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / "predicciones_registradas.json"
    if not p.exists():
        write_json(p, {"registradas_utc": datetime.now(timezone.utc).isoformat(), **PREDICCION})
    d = pd.read_parquet(an.RES / "series_diarias_zonas.parquet")
    d.index = pd.DatetimeIndex(d.index)
    cat = pd.read_csv(an.RES / "catalogo_eventos.csv")  # catálogo ya construido por el motor Yuna (solo lectura)
    vent = ventanas(cat)
    A = d["imerg_max48_yuna"] > 100
    C = an.suma_movil(d["chirps_max_yuna"], 2) > 100
    near = lambda s: s | s.shift(1, fill_value=False) | s.shift(-1, fill_value=False)  # noqa: E731
    trig = {"A_IMERG": A, "C_CHIRPS": C, "A_y_C_acuerdo": A & near(C), "A_o_C": A | C}
    filas = []
    for nombre, t in trig.items():
        for per, lab in ((an.CAL, "calibración 2001-2015"), (an.TEST, "prueba 2016-2024")):
            r = an.puntuar(t, vent, per)
            s = r["tot"]
            m = an.metricas_ep(s["h"], s["m"], s["fa"], s["ep"])
            ci = an.bootstrap(r["por_anio"])
            filas.append({"disparador": nombre, "periodo": lab, "eventos": s["h"] + s["m"], "aciertos": s["h"],
                          "episodios": s["ep"], "falsas_alarmas": s["fa"], "POD": m["POD"], "FAR": m["FAR"],
                          "CSI": m["CSI"], "CSI_ic95": ci["CSI"], "FAR_ic95": ci["FAR"],
                          "detectados": ",".join(e["id"] for e in r["eventos"] if e["detectado"])})
    T = pd.DataFrame(filas)
    T.to_csv(OUT / "backtest_acuerdo.csv", index=False, float_format="%.3f")
    pr = T[T["periodo"].str.startswith("prueba")].set_index("disparador")
    ver = {"K1": bool(pr.loc["A_y_C_acuerdo", "aciertos"] >= 6
                      and pr.loc["A_y_C_acuerdo", "falsas_alarmas"] <= pr.loc["A_IMERG", "falsas_alarmas"] / 2),
           "K2": bool(pr.loc["A_o_C", "CSI"] <= pr.loc["A_IMERG", "CSI"])}
    write_json(OUT / "resumen.json", {"veredicto": ver, "prueba": json.loads(pr.to_json(orient="index"))})
    pd.set_option("display.width", 220)
    print(T.drop(columns=["detectados"]).round(3).to_string())
    print(pr["detectados"].to_string())
    print(ver)


if __name__ == "__main__":
    main()
