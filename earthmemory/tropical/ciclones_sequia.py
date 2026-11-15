"""¿Después de los ciclones queda sequía, o la sequía llega cuando NO llegan los ciclones?
Lluvia diaria CHIRPS (media de las celdas de RD; CHIRPS no pierde días de lluvia como IMERG) e IBTrACS (Atlántico Norte).
Día con ciclón: algún punto de trayectoria a < 500 km del centro de RD ese día. Sequía: lluvia de 3 meses en el
percentil <= 20 de su misma ventana de calendario 2001-2024 (definición del déficit de Preparar, con CHIRPS).
Datos ya en disco; sin descargas. n = 24 temporadas: resultados indicativos.
Ejecutar: docker compose run --rm --entrypoint uv tropical run --frozen --no-sync python -m earthmemory.tropical.ciclones_sequia
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from ..hr.common import ROOT, write_json
from ..tendencias import datos
from .ciclones_anticipacion import ibtracs

OUT = ROOT / "results" / "tropical" / "ciclones_sequia"
CENTRO = (18.9, -70.2)
PREDICCIONES = {
    "S1": "Los días con ciclón a < 500 km aportan al menos el 10 % de la lluvia de junio-noviembre (media 2001-2024).",
    "S2": "Las 8 temporadas con MENOS lluvia de ciclón tienen más meses de sequía en diciembre-mayo siguiente que las 8 "
          "con MÁS lluvia de ciclón.",
    "S3": "Versión literal de la idea («después del ciclón queda sequía»): en los 90 días tras el paso de un ciclón la "
          "sequía es MENOS frecuente que en el resto de días de la misma época. Si fuera más frecuente, la idea literal "
          "se sostiene.",
}


def registrar():
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / "predicciones_registradas.json"
    if not p.exists():
        write_json(p, {"registradas_utc": datetime.now(timezone.utc).isoformat(), **PREDICCIONES})


def main():
    registrar()
    Pc = np.load(datos.DER / "chirps_diario_01.npz")["P"].astype(float)
    days = pd.DatetimeIndex(datos.DAYS.astype("datetime64[D]"))
    lluvia = pd.Series(np.nanmean(Pc, axis=(1, 2)), index=days)
    ib = ibtracs()
    from .ciclones_anticipacion import dist
    ib["dc"] = dist(ib.LAT, ib.LON, *CENTRO)
    dias_ciclon = pd.DatetimeIndex(ib.loc[ib.dc < 500, "t"].dt.normalize().unique())
    ciclon = pd.Series(days.isin(dias_ciclon), index=days)

    # S1: aporte de los ciclones a la lluvia de junio-noviembre
    jn = lluvia.index.month.isin(range(6, 12))
    temp = pd.DataFrame({"lluvia": lluvia[jn], "ciclon": ciclon[jn]})
    temp["anio"] = temp.index.year
    por = temp.groupby("anio").apply(lambda g: pd.Series({
        "lluvia_jn_mm": g.lluvia.sum(), "lluvia_ciclon_mm": g.lluvia[g.ciclon].sum(), "dias_ciclon": int(g.ciclon.sum())}))
    por["fraccion_ciclon"] = por.lluvia_ciclon_mm / por.lluvia_jn_mm

    # sequía: lluvia de 90 días en percentil <= 20 de su misma fecha de calendario
    s90 = lluvia.rolling(90, min_periods=90).sum()
    doy = np.minimum(s90.index.day_of_year.to_numpy(), 365)
    pct = s90.groupby(doy).rank(pct=True)
    sequia = (pct <= 0.20) & s90.notna()

    # S2: sequía en diciembre-mayo siguiente según la lluvia de ciclón de la temporada
    filas = []
    for y in por.index:
        if y >= 2024:
            continue
        v = sequia[(sequia.index >= f"{y}-12-01") & (sequia.index <= f"{y + 1}-05-31")]
        filas.append({"anio": y, "lluvia_ciclon_mm": por.loc[y, "lluvia_ciclon_mm"],
                      "fraccion_ciclon": por.loc[y, "fraccion_ciclon"], "dias_sequia_dic_may": int(v.sum()),
                      "dias_validos": int(v.size)})
    S = pd.DataFrame(filas).sort_values("lluvia_ciclon_mm")
    bajo, alto = S.head(8), S.tail(8)
    rho = S[["lluvia_ciclon_mm", "dias_sequia_dic_may"]].corr(method="spearman").iloc[0, 1]
    rng = np.random.default_rng(20261115)
    obs = bajo.dias_sequia_dic_may.mean() - alto.dias_sequia_dic_may.mean()
    x = S.dias_sequia_dic_may.to_numpy()
    null = [np.subtract(*[(p := rng.permutation(x))[:8].mean(), p[-8:].mean()]) for _ in range(9999)]
    p_s2 = float((1 + np.sum(np.asarray(null) >= obs)) / 10000)

    # S3: sequía en los 90 días tras un ciclón frente al resto de días de agosto-diciembre
    tras = pd.Series(False, index=days)
    for d in dias_ciclon:
        tras[(tras.index > d) & (tras.index <= d + pd.Timedelta(days=90))] = True
    epoca = days.month.isin([8, 9, 10, 11, 12]) & s90.notna().to_numpy()
    f_tras = float(sequia[epoca & tras.to_numpy()].mean())
    f_resto = float(sequia[epoca & ~tras.to_numpy()].mean())

    S.to_csv(OUT / "temporadas.csv", index=False, float_format="%.3f")
    por.to_csv(OUT / "aporte_ciclones_jun_nov.csv", float_format="%.3f")
    res = {
        "fraccion_ciclon_media": float(por.fraccion_ciclon.mean()),
        "fraccion_ciclon_rango": [float(por.fraccion_ciclon.min()), float(por.fraccion_ciclon.max())],
        "dias_sequia_dic_may_8_menos_ciclon": float(bajo.dias_sequia_dic_may.mean()),
        "dias_sequia_dic_may_8_mas_ciclon": float(alto.dias_sequia_dic_may.mean()),
        "anios_menos_ciclon": bajo.anio.tolist(), "anios_mas_ciclon": alto.anio.tolist(),
        "p_permutacion_S2": p_s2, "spearman_lluvia_ciclon_vs_sequia": float(rho),
        "frac_dias_sequia_90d_tras_ciclon": f_tras, "frac_dias_sequia_resto_ago_dic": f_resto,
        "veredicto": {"S1": bool(por.fraccion_ciclon.mean() >= 0.10),
                      "S2": bool(obs > 0), "S2_significativa_p05": bool(p_s2 < 0.05),
                      "S3": bool(f_tras < f_resto)},
    }
    write_json(OUT / "resumen.json", res)
    print(S.to_string())
    print(json.dumps(res, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
