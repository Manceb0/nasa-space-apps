"""Cuaderno 05 · alta resolución y umbrales críticos: se construye, se ejecuta sin pantalla y se exporta a HTML.

Solo LEE lo que dejó la corrida (results/nacional_hr, figures/nacional_hr, data/nacional_hr/derivados) y
recalcula a la vista dos piezas pequeñas (el ajuste segmentado de la celda ejemplo y el filtro de lluvia del par)
para que el lector vea que los números del informe salen de los datos.
"""

from __future__ import annotations

import nbformat
from nbclient import NotebookClient
from nbconvert import HTMLExporter

from .common import NB_DIR, NB_HTML, ROOT

NAME = "05_alta_resolucion_y_umbrales"

SETUP = '''from pathlib import Path
import json
import numpy as np
import pandas as pd
from IPython.display import Image, Markdown, display
ROOT = Path.cwd()
while not (ROOT / "results" / "nacional_hr").exists() and ROOT != ROOT.parent:
    ROOT = ROOT.parent
RES, FIG = ROOT / "results" / "nacional_hr", ROOT / "figures" / "nacional_hr"
r = json.loads((RES / "resumen.json").read_text(encoding="utf-8"))
pd.set_option("display.max_columns", 40); pd.set_option("display.width", 220)
def fig(nombre, ancho=950):
    display(Image(filename=str(FIG / f"{nombre}.png"), width=ancho))'''


def md(s):
    return nbformat.v4.new_markdown_cell(s)


def code(s):
    return nbformat.v4.new_code_cell(s)


CELLS = [
    md("# 05 · Alta resolución y umbrales críticos\n\nEarth Memory nacional (República Dominicana, 2001-2024). "
       "Los mapas anteriores eran 'cuadrados grandes' porque NASA POWER es de 0.5° y GLDAS de 0.25°. Aquí se suman "
       "capas más finas y **verificables** (cada archivo con URL y SHA-256 en `data/nacional_hr/MANIFEST.json`) y se "
       "busca **dónde cambia de régimen la respuesta del suelo a la lluvia**.\n\n"
       "**Reglas:** cada mapa dice su resolución nativa; nada se interpola para parecer más fino; todo resultado es "
       "asociación (no causa); las pruebas corrigen autocorrelación (bootstrap por bloques) y comparaciones "
       "múltiples (FDR de Benjamini-Hochberg)."),
    code(SETUP),
    md("## 1 · Qué capas entraron y con qué resolución\n\nLa columna `celdas_RD` cuenta celdas nativas sobre la RD. "
       "CHIRPS y TerraClimate no son NASA: son comprobaciones independientes; IMERG y SMAP L4 (NASA) siguen siendo el "
       "núcleo."),
    code('''display(pd.read_csv(RES / "capas_resolucion_y_celdas.csv"))
f = pd.read_csv(RES / "fuentes.csv"); f[["clave", "nombre", "doi", "licencia", "version", "nasa"]]'''),
    code('''man = json.loads((ROOT / "data/nacional_hr/MANIFEST.json").read_text(encoding="utf-8"))
a = pd.DataFrame([{"archivo": k, "dataset": v.get("dataset"), "bytes": v["bytes"]} for k, v in man["archivos"].items()])
display(a.groupby("dataset").agg(archivos=("archivo", "size"), MB=("bytes", lambda b: round(b.sum() / 1e6, 1))))
pd.DataFrame({k: v for k, v in man["rutas"].items() if isinstance(v, dict)}).T.reindex(columns=["estado", "pedidos", "descargados", "n_errores"])'''),
    md("## 2 · Climatología en resolución nativa\n\nCHIRPS (0.05°) frente a IMERG (0.1°, NASA): misma lluvia vista con "
       "otra rejilla. El panel f mide el acuerdo de las anomalías mensuales a 0.1° (CHIRPS agregado a la celda IMERG, "
       "no IMERG 'bajado' a 0.05°)."),
    code('''fig("hr1_climatologia_resolucion_nativa")
pd.Series(r["chirps_vs_imerg_0.1"])'''),
    md("**Cuidado con TerraClimate:** su rejilla es de 1/24°, pero la variación mes a mes viene de ERA5 (~0.25°) y la "
       "capacidad de agua del suelo del modelo es de 0.5°. El detalle fino de sus mapas es sobre todo climatología."),
    code('''pd.Series(r["terraclimate_atributos"])'''),
    md("## 3 · Factores estáticos (suelo, terreno, cobertura)\n\nSoilGrids, Copernicus DEM y WorldCover agregados a 0.05° "
       "por media de área (continuos) o fracción de clase (categóricos). La vista 1/8 de WorldCover se validó contra "
       "10 m en una ventana del Cibao:"),
    code('''fig("hr2_factores_estaticos")
pd.DataFrame(r["worldcover_validacion"]).T'''),
    md("## 4 · Umbral crítico de humedad antecedente\n\nPor celda: ΔS (cambio mensual de humedad del suelo TerraClimate) "
       "frente a la anomalía de lluvia CHIRPS, con la eficiencia dependiendo del llenado relativo antecedente f = (S(t−1) − S_min)/(S_max − S_min). "
       "Modelo lineal (M0) frente a segmentado con quiebre θ (M1). sup-F con bootstrap de residuos por bloques "
       "circulares de 12 meses, FDR, ΔBIC > 2, IC de θ por bootstrap de bloques móviles."),
    code('''fig("hr3_umbrales")
pd.Series({k: v for k, v in r["umbrales"].items() if not isinstance(v, dict)})'''),
    md("### Curvas por paisaje: un umbral común por grupo de celdas\n\nCelda a celda casi no hay potencia; agrupando "
       "por aridez o por arcilla sí. La incertidumbre sale de remuestrear bloques de TIEMPO compartidos por todas las "
       "celdas del grupo (las celdas vecinas no son experimentos independientes)."),
    code('''fig("hr3b_curvas_por_paisaje")
cp = r["umbrales"]["curvas_por_paisaje"]
pd.DataFrame({k: {"fuente": v["fuente"], "celdas": v["n_celdas"], "theta": v["theta"], "theta_ic95": v["theta_ic95"],
                  "b5": v["b5"], "b5_ic95": v["b5_ic95"], "quiebre_sostenido": v["b5_excluye_0"]} for k, v in cp.items()}).T'''),
    code('''display(pd.Series(r["umbrales"]["sensibilidad_lluvia_TerraClimate"], name="lluvia TerraClimate como forzante"))
display(pd.Series(r["umbrales"]["sensibilidad_sin_efectos_fijos_mes"], name="sin efectos fijos de mes"))
pd.Series(r["umbrales"]["smap_9km"] or {}, name="SMAP L4 9 km (NASA)")'''),
    md("### Recalcular la celda ejemplo a la vista\n\nSe vuelve a ajustar M0 y M1 en la celda ejemplo con los datos "
       "armonizados (sin bootstrap) para comprobar el umbral del informe."),
    code('''import sys; sys.path.insert(0, str(ROOT))
from earthmemory.hr import thresholds
from earthmemory.hr.common import GRID
D = np.load(ROOT / "data/nacional_hr/derivados/rejilla_005.npz")
ex = r.get("celda_ejemplo_umbral")
c = pd.read_csv(RES / "celdas_005.csv")
row = c.loc[c["umbral_dBIC"].idxmax()]
i, j = int(np.argmin(abs(GRID.lat - row.lat))), int(np.argmin(abs(GRID.lon - row.lon)))
y, Pa, f, mo, smax = thresholds.series_for_cell(D["P_chirps"][:, i, j], D["tc_soil"][:, i, j], D["meses"].astype("datetime64[M]"))
fit = thresholds.fit_cell(y, Pa, f, mo, n_boot=99, rng=np.random.default_rng(0)); fit.pop("_ci_args")
pd.DataFrame({"informe": pd.Series(ex), "recalculado": pd.Series({"theta": fit["theta"], "dBIC": fit["dBIC"]})})'''),
    md("## 5 · Meses de quiebre (Pettitt, corregido por autocorrelación)\n\nLa p asintótica de Pettitt supone "
       "independencia; con series persistentes da quiebres de más. Se compara el número de celdas con q < 0.05 con "
       "bloques de 12 y 24 meses y sin corrección:"),
    code('''fig("hr4_quiebres")
pd.DataFrame(r["quiebres"]).T'''),
    md("## 6 · ¿Qué acompaña a los umbrales? (asociación)\n\nRidge estandarizado; habilidad con validación cruzada "
       "por bloques espaciales de 0.5° (y, para comparar, aleatoria). Si la R² espacial es mucho menor que la "
       "aleatoria, la autocorrelación espacial inflaba la segunda."),
    code('''fig("hr5_factores_del_umbral", 900)
rows = []
for k, d in r["factores"].items():
    for n, cc in d["coef"].items():
        rows.append({"respuesta": k, "factor": n, "beta_z": cc["beta_z"], "ic95": cc["ic95"], "excluye_0": cc["excluye_0"], "spearman": cc["spearman"]})
display(pd.DataFrame(rows))
pd.DataFrame({k: {kk: d[kk] for kk in ("n", "n_bloques", "r2_cv_espacial", "r2_cv_aleatoria", "r2_ajuste")} | {"moran_I": d["moran_residuos"]["I"]} for k, d in r["factores"].items()}).T'''),
    md("## 7 · 'Misma lluvia, distinta respuesta' a 0.05°\n\nFiltro de lluvia parecida (CHIRPS), diferencia de eficiencia "
       "por bootstrap por bloques compartidos, FDR sobre todos los candidatos, comprobación con SMAP L4 (NASA) y con "
       "sustitutos sin diferencia real."),
    code('''fig("hr6_par_misma_lluvia")
display(pd.DataFrame(r["par_celdas"]))
pd.Series({k: v for k, v in r["par"].items() if k not in ("top10", "smap", "factores")})'''),
    code('''display(pd.Series({k: v for k, v in (r["par"].get("smap") or {}).items() if not isinstance(v, list)}, name="SMAP"))
display(pd.DataFrame(r["par"]["factores"], index=["A", "B"]).T)
pd.DataFrame(r["par"]["top10"])'''),
    md("## 8 · El 18 de noviembre de 2023 en Santo Domingo\n\nCHIRPS diario NO es independiente día a día: reparte el "
       "total de la péntada con CFSv2. Por eso se muestra también la péntada (anclada a estaciones) e IMERG (NASA). "
       "El valor de estación (431 mm) es preliminar y la posición marcada es aproximada."),
    code('''fig("hr7_evento_2023-11-18")
pd.Series(r["evento_2023_11_18"]["barras"])'''),
    md("## 9 · Límites\n\nVer `reports_nacional/ALTA_RESOLUCION.md`, sección *Límites*. En corto: TerraClimate y SMAP L4 "
       "son modelos; la resolución efectiva de la variación mensual es más gruesa que su rejilla; los umbrales son "
       "asociaciones estadísticas en esos modelos, no mediciones de infiltración."),
]


def build() -> None:
    NB_DIR.mkdir(parents=True, exist_ok=True)
    NB_HTML.mkdir(parents=True, exist_ok=True)
    nb = nbformat.v4.new_notebook()
    nb.cells = CELLS
    nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
    NotebookClient(nb, timeout=900, kernel_name="python3", resources={"metadata": {"path": str(ROOT)}}).execute()
    p = NB_DIR / f"{NAME}.ipynb"
    nbformat.write(nb, p)
    body, _ = HTMLExporter().from_notebook_node(nb)
    (NB_HTML / f"{NAME}.html").write_text(body, encoding="utf-8")
    print(f"[cuaderno] {p} y {NB_HTML / (NAME + '.html')}", flush=True)
