"""Auditoría de confianza (Evidence Intelligence) · punto de entrada.

    docker compose run --rm auditoria                    # descarga lo que falta, calcula, figuras, informe, cuaderno
    docker compose run --rm auditoria --sin-descarga     # solo con la caché
    docker compose run --rm auditoria --solo-salidas     # rehace figuras/informe/cuaderno desde el estado guardado

Pregunta: ¿qué conclusión aparentemente correcta sobre sequías/inundaciones en RD podría resultar falsa al
incluir la información que falta, y cuándo bastan los datos para actuar?
Escribe en results/auditoria, figures/auditoria, reports_nacional/AUDITORIA_CONFIANZA.md y notebooks/07_*.
"""

from __future__ import annotations

import argparse
import json
import pickle
import time
from pathlib import Path

import numpy as np
import pandas as pd

from . import analisis, datos, descarga, procedencia, reauditoria

RES = Path("results/auditoria")
FIG = Path("figures/auditoria")
STATE = Path("data/auditoria/cache/estado.pkl")


def _clean(o):
    if isinstance(o, dict):
        return {str(k): _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if isinstance(o, (np.floating, float)):
        return None if not np.isfinite(o) else float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, (pd.Timestamp,)):
        return str(o.date())
    return o


def wjson(p: Path, obj) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(_clean(obj), ensure_ascii=False, indent=1), encoding="utf-8")


def wcsv(p: Path, df: pd.DataFrame) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(p, index=False, float_format="%.6g")


def compute(args) -> dict:
    t0 = time.time()
    if not args.sin_descarga:
        descarga.run()
    g = datos.G05()
    oni = analisis.load_oni()
    print(f"[auditoria] rejilla y provincias ({time.time() - t0:.0f} s)", flush=True)
    cubes = analisis.monthly_cubes(g)
    print(f"[auditoria] cubos mensuales ({time.time() - t0:.0f} s)", flush=True)
    stv = analisis.station_validation(g, cubes)
    print(f"[auditoria] estaciones ({time.time() - t0:.0f} s)", flush=True)
    re = reauditoria.run(g, oni)
    print(f"[auditoria] re-auditoría 50/96 ({time.time() - t0:.0f} s)", flush=True)
    dr = analisis.drought_flips(g, cubes, B=args.B)
    print(f"[auditoria] cambio de decisión sequía ({time.time() - t0:.0f} s)", flush=True)
    fl = analisis.flood_flips(g, B=args.B)
    print(f"[auditoria] disparador 48 h ({time.time() - t0:.0f} s)", flush=True)
    sd = analisis.santo_domingo(g, stv)
    wm = analisis.where_to_measure(g, cubes, stv["meta"])
    print(f"[auditoria] Santo Domingo y dónde medir ({time.time() - t0:.0f} s)", flush=True)
    S = {"stv": {k: v for k, v in stv.items()}, "re": re, "dr": dr, "fl": fl, "sd": sd, "wm": wm,
         "oni": oni, "chirps_diario": datos.chirps_daily_status(), "B": args.B,
         "g_meta": {"provs": g.provs, "codes": g.codes}}
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_bytes(pickle.dumps(S))
    return S


def write_results(S: dict) -> None:
    RES.mkdir(parents=True, exist_ok=True)
    # 1. procedencia
    wcsv(RES / "procedencia_matriz.csv", pd.DataFrame(procedencia.PRODUCTOS).assign(urls=lambda d: d["urls"].str.join(" ; ")))
    ins = pd.DataFrame(procedencia.INSUMOS).T.fillna("")
    ins.index.name = "insumo"
    ins.reset_index().to_csv(RES / "procedencia_insumos_compartidos.csv", index=False)
    wjson(RES / "procedencia.json", {"productos": procedencia.PRODUCTOS, "insumos": procedencia.INSUMOS,
                                      "aristas": [dict(zip(("a", "b", "insumo", "estado"), a)) for a in procedencia.ARISTAS],
                                      "veredicto": procedencia.veredicto()})
    # 2. estaciones
    st = S["stv"]
    wcsv(RES / "estaciones_meta.csv", st["meta"])
    wcsv(RES / "estaciones_validacion_diaria.csv", st["diario"])
    wcsv(RES / "estaciones_validacion_mensual.csv", st["mensual"])
    wcsv(RES / "estaciones_dispersion_vecinas.csv", st["dispersion"])
    if len(st["ingesta"]):
        wcsv(RES / "estaciones_en_chirps_por_mes.csv", st["ingesta"])
    # 3. re-auditoría
    re = S["re"]
    wcsv(RES / "reauditoria_96_episodios.csv", re["tabla"])
    wcsv(RES / "reauditoria_celdas.csv", re["celdas"].reset_index())
    wcsv(RES / "reauditoria_relieve_costa.csv", re["relieve"])
    wcsv(RES / "reauditoria_representatividad.csv", re["representatividad"])
    wjson(RES / "reauditoria_resumen.json", {**re["resumen"], "persistencia": re["persistencia"]})
    # 4. cambio de decisión
    dr = S["dr"]
    wcsv(RES / "cambio_decision_sequia_provincias.csv", dr["provincia"])
    wcsv(RES / "cambio_decision_sequia_pares.csv", dr["pares"])
    wcsv(RES / "cambio_decision_sequia_por_anio.csv", dr["por_anio"])
    wjson(RES / "cambio_decision_sequia_nacional.json", dr["nacional"])
    if S["fl"] is not None:
        wcsv(RES / "cambio_decision_inundacion_48h.csv", S["fl"]["resumen"])
        wcsv(RES / "cambio_decision_inundacion_48h_provincias.csv", S["fl"]["provincia"])
    # 5. Santo Domingo
    sd = S["sd"]
    wcsv(RES / "santo_domingo_ventanas.csv", sd["ventanas"])
    wjson(RES / "santo_domingo_2023-11-18.json", {k: v for k, v in sd.items() if k not in ("ventanas", "horaria")}
          | {"ventanas": sd["ventanas"].to_dict(orient="records"), "veredicto": veredicto_sd(sd),
             "fuentes": {"NHC TCR AL222023": "https://www.nhc.noaa.gov/data/tcr/AL222023_Twenty-Two.pdf",
                         "Listín Diario 21-nov-2023 (boletín ONAMET)": "https://listindiario.com/la-republica/20231121/viejo-arroyo-hondo-estacion-registro-mas-lluvias-sabado_783610.html",
                         "Diario Libre 19-nov-2023": "https://www.diariolibre.com/actualidad/nacional/2023/11/19/disturbio-tropical-dejo-lluvias-sin-precedentes-en-rd/2527677"}})
    # 6. dónde medir
    wcsv(RES / "donde_medir_prototipo.csv", S["wm"])
    write_web(S)


def veredicto_sd(sd: dict) -> dict:
    d = sd["descomposicion"]
    return {"conclusion": "inconclusa en la descomposición; se sostiene que los productos de 10 km no reproducen el extremo puntual",
            "motivo": ("La ventana exacta de 24 h de los 431 mm no está publicada (NHC: '24-h period ending on 18 November'); la "
                       "coordenada de la estación no es pública. Aun con la ventana más favorable y la mejor celda vecina, IMERG "
                       f"queda en {d['imerg_mejor_vecina_mejor_ventana_mm']:.0f} mm; la media de 11 pluviómetros de ONAMET publicados "
                       f"en prensa es {d['media_11_pluviometros_prensa_mm']:.0f} mm.")}


def write_web(S: dict) -> None:
    W = RES / "web"
    dr = S["dr"]["provincia"]
    rows = []
    for p, sub in dr.groupby("provincia"):
        rec = {"provincia": p, "codigo": sub["codigo"].iloc[0]}
        for _, r in sub.iterrows():
            k = "spi3_menor_igual_" + str(abs(r["umbral_spi3"])).replace(".", "_")
            rec[k] = {"tasa_condicional": r["tasa_condicional"], "ic95": [r["ic95_condicional_bajo"], r["ic95_condicional_alto"]],
                      "tasa_contradiccion_clara": r["tasa_contradiccion_clara"],
                      "tasa_global": r["tasa_global"], "n_casos": r["n_casos"], "n_alguna_alarma": r["n_alguna_alarma"],
                      "n_no_unanime": r["n_no_unanime"]}
        if S["fl"] is not None:
            f = S["fl"]["provincia"]
            f = f[(f["provincia"] == p)]
            rec["inundacion_48h_100mm"] = {f"{r['escala']}_tol{r['tolerancia_dias']}": {
                "tasa_cambio_decision": r["tasa_cambio_decision"], "disparos_imerg": r["n_A"], "disparos_chirps": r["n_B"]}
                for _, r in f.iterrows()}
        rows.append(rec)
    wjson(W / "cambio_decision_provincias.json", {"version": 1, "generado_por": "earthmemory/auditoria/run.py",
                                                  "periodo": "2001-2024",
                                                  "productos_sequia": analisis.PRODUCTOS_M,
                                                  "periodo_inundacion": S["fl"]["anios"] if S["fl"] else None,
                                                  "nacional_sequia": S["dr"]["nacional"], "provincias": rows})
    wjson(W / "procedencia.json", {"version": 1, "productos": [{k: v for k, v in p.items()} for p in procedencia.PRODUCTOS],
                                   "aristas": [dict(zip(("a", "b", "insumo", "estado"), a)) for a in procedencia.ARISTAS],
                                   "veredicto": procedencia.veredicto()})
    wm = S["wm"].head(40)
    wjson(W / "donde_medir_prototipo.json", {"version": 1, "etiqueta": "PRELIMINAR: no prueba dónde deben ir estaciones",
                                             "celdas": wm.to_dict(orient="records")})
    (W / "CONTRATO.md").write_text(CONTRATO, encoding="utf-8")


CONTRATO = """# Contrato de datos · results/auditoria/web/

Generado por `earthmemory/auditoria/run.py` (`docker compose run --rm auditoria`). JSON UTF-8; `null` = sin dato.
Números en tasa (0-1), no en %. Nada se escribe a mano.

## cambio_decision_provincias.json
- `version` (int), `periodo` ("2001-2024"), `productos_sequia` (lista: IMERG, CHIRPS, GLDAS_forzamiento, MERRA2).
- `nacional_sequia`: lista de objetos {`umbral_spi3` (−1.0 / −1.5), `productos` ("4 productos" | "IMERG vs CHIRPS" |
  "3 sin MERRA-2"), `n_casos`, `n_alguna_alarma`, `n_no_unanime`, `tasa_global`, `tasa_condicional`,
  `ic95_global` [bajo, alto], `ic95_condicional` [bajo, alto]}.
- `provincias`: lista de {`provincia`, `codigo` (ISO 3166-2, p. ej. "DO-01"),
  `spi3_menor_igual_1_0` y `spi3_menor_igual_1_5`: {`tasa_condicional`, `ic95` [bajo, alto], `tasa_contradiccion_clara`
  (un producto declara sequía y otro da SPI-3 ≥ 0, es decir normal o húmedo), `tasa_global`, `n_casos`,
  `n_alguna_alarma`, `n_no_unanime`}, `inundacion_48h_100mm` (si hay CHIRPS diario): {"<escala>_tol<d>":
  {`tasa_cambio_decision`, `disparos_imerg`, `disparos_chirps`}} con escala = media_provincia | maximo_celda y d = 0 | 1}.
- Lectura: `tasa_condicional` = de los meses en que AL MENOS un producto declara sequía (SPI-3 ≤ umbral), fracción en
  que los productos no están de acuerdo. IC 95 % por bootstrap de bloques de año.
- Mostrar SIEMPRE con su IC y con la frase: "los productos no son independientes; el acuerdo no es validación".

## procedencia.json
- `productos`: lista de {`id`, `producto`, `clase` (una de 6), `mide_o_modela`, `insumos`, `pluviometros`, `resolucion`,
  `latencia`, `version`, `citas`, `urls` (lista), `verificado`}.
- `aristas`: {`a`, `b`, `insumo`, `estado` ("V" verificado | "I" inferido)}: pares que pueden compartir errores.
- `veredicto`: lista de frases para pantalla.

## donde_medir_prototipo.json
- `etiqueta`: texto obligatorio "PRELIMINAR…". `celdas`: 40 celdas 0.1° con mayor `indice_prioridad` (0-1, media de
  rangos percentiles de: desacuerdo 1−r IMERG/CHIRPS, persistencia (fracción de años con cambio de decisión), tasa de
  cambio condicional SPI-3 ≤ −1 y distancia a la estación GHCN-D activa más cercana). Campos: `lat`, `lon`, `provincia`,
  `indice_prioridad`, `indice_sin_distancia`, y los cuatro componentes.
- No usar como recomendación de dónde instalar estaciones sin acceso, exposición, población y la red ONAMET/INDRHI.
"""


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--sin-descarga", action="store_true")
    ap.add_argument("--solo-salidas", action="store_true")
    ap.add_argument("--sin-cuaderno", action="store_true")
    ap.add_argument("--B", type=int, default=2000)
    args = ap.parse_args(argv)
    if args.solo_salidas and STATE.exists():
        S = pickle.loads(STATE.read_bytes())
    else:
        S = compute(args)
    write_results(S)
    from . import figuras, informe
    figs = figuras.make_all(S, FIG)
    informe.write(S, figs)
    if not args.sin_cuaderno:
        from . import cuaderno
        cuaderno.build()
    print("[auditoria] listo", flush=True)


if __name__ == "__main__":
    main()
