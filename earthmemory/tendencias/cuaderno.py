"""Cuaderno 06 · tendencias de sequía y lluvia extrema: se construye, se ejecuta sin pantalla y se exporta a HTML.

Solo LEE lo que dejó la corrida (results/tendencias, figures/tendencias) y recalcula a la vista dos piezas pequeñas
(la tendencia nacional de un índice con el código del motor y con scipy, y un índice ETCCDI de una celda desde la lluvia
diaria) para que el lector compruebe que los números salen de los datos.
"""

from __future__ import annotations

import nbformat
from nbclient import NotebookClient
from nbconvert import HTMLExporter

from ..hr.common import NB_DIR, NB_HTML, ROOT

NAME = "06_tendencias_sequia_y_extremos"

SETUP = '''from pathlib import Path
import json, sys
import numpy as np
import pandas as pd
from IPython.display import Image, Markdown, display
ROOT = Path.cwd()
while not (ROOT / "results" / "tendencias").exists() and ROOT != ROOT.parent:
    ROOT = ROOT.parent
sys.path.insert(0, str(ROOT))
RES, FIG = ROOT / "results" / "tendencias", ROOT / "figures" / "tendencias"
pd.set_option("display.max_columns", 40); pd.set_option("display.width", 220); pd.set_option("display.precision", 3)
def fig(nombre, ancho=950):
    display(Image(filename=str(FIG / f"{nombre}.png"), width=ancho))
resumen = pd.read_csv(RES / "resumen_indices.csv")
prov = pd.read_csv(RES / "tendencias_provincias.csv")
cal = pd.read_csv(RES / "calibracion_fpr.csv")
corrida = json.loads((RES / "corrida.json").read_text(encoding="utf-8"))'''


def md(s):
    return nbformat.v4.new_markdown_cell(s)


def code(s):
    return nbformat.v4.new_code_cell(s)


CELLS = [
    md("# 06 · Tendencias de periodos secos y lluvia extrema (P0)\n\nRepública Dominicana, 2001-2024, celdas de 0.1° y "
       "32 provincias. Dos productos: **NASA GPM IMERG V07 Final** (recuperación satelital calibrada con pluviómetros) y "
       "**CHIRPS v2.0** (satélite + estaciones), comparados en la misma rejilla. Pregunta del reto *Be An Earth System "
       "Trend Detective!*: elegir variables y región, estudiar tendencias espaciales y temporales, **cuantificar** el "
       "cambio y **probar su significancia**.\n\nReglas: Theil-Sen + Mann-Kendall de Hamed-Rao (autocorrelación), FDR "
       "entre celdas, significancia de campo (Wilks 2016), falsos positivos medidos con sustitutos, tendencia mínima "
       "detectable, y clase de confianza de dos productos. Nada de esto atribuye causas."),
    code(SETUP),
    md("## 1 · Datos y descarga\n\nCHIRPS diario se recortó en el servidor (IRI/LDEO) y se verificó contra los GeoTIFF "
       "oficiales del CHC. Cada archivo con URL, SHA-256 y licencia en `data/tendencias/MANIFEST.json`."),
    code('''man = json.loads((ROOT / "data/tendencias/MANIFEST.json").read_text(encoding="utf-8"))
display(pd.DataFrame([{"archivo": k, "MB": round(v["bytes"] / 1e6, 2), "sha256": v["sha256"][:16] + "…", "url": v["url"][:90] + "…"}
                      for k, v in man["archivos"].items()]).head(5))
print(len(man["archivos"]), "archivos;", json.dumps(man["rutas"].get("chirps_diario", {}), ensure_ascii=False, indent=1))
pd.Series(corrida["coherencia_diaria"], name="coherencia diaria IMERG vs CHIRPS (celdas analizadas)")'''),
    md("## 2 · Falsos positivos: ¿la prueba dice 'significativo' cuando no hay nada?\n\nCampos nulos sin tendencia que "
       "conservan la autocorrelación y la correlación espacial (fases aleatorias multivariadas y bloques de 3 años). La "
       "tasa de p < 0.05 debería quedar cerca de 0.05."),
    code('''fig("fig4_calibracion_falsos_positivos")
cal.groupby(["nivel", "metodo"])[["fpr_local_p05", "fpr_local_p05_sin_correccion_hr", "fraccion_mapas_nulos_con_celda_fdr"]].mean()'''),
    md("## 3 · Mapas de tendencia IMERG | CHIRPS\n\nPendiente de Theil-Sen por década; puntos = celdas FDR-significativas "
       "(q ≤ 0.10). Marrón = más seco."),
    code('''fig("fig1_mapas_tendencia_IMERG_vs_CHIRPS", 820)'''),
    code('''for n in ["mapa_tendencia_SDII_anual", "mapa_tendencia_R1mm_anual", "mapa_tendencia_RACHAS15_anual", "mapa_tendencia_PRCPTOT_anual"]:
    fig(n, 820)'''),
    md("## 4 · ¿Están de acuerdo las fuentes? Clase de confianza\n\n*robusta* = las dos significativas y en la misma "
       "dirección; *en disputa* = direcciones opuestas con al menos una significativa."),
    code('''fig("fig2_clases_de_confianza")
cols = ["indice", "periodo", "fuente", "celdas_sig_fdr", "celdas_sig_fdr_aumento", "celdas_sig_fdr_descenso", "campo_significativo_wilks",
        "celdas_robusta", "celdas_robusta_aumento", "celdas_robusta_descenso", "celdas_consistente", "celdas_en_disputa", "provincias_robusta", "provincias_en_disputa"]
resumen.loc[resumen["fuente"] == "IMERG", cols].drop(columns="fuente").sort_values(["celdas_robusta", "celdas_en_disputa"], ascending=False).head(20)'''),
    md("## 5 · Serie nacional y tendencia mínima detectable\n\nCon 24 años, ¿qué tan grande tendría que ser un cambio para "
       "verlo? Si la pendiente cae dentro de la banda, el resultado es 'no detectable', no 'sin cambio'."),
    code('''fig("fig5_tendencia_minima_detectable", 850)
nat = prov[(prov["region"] == "República Dominicana") & (prov["periodo"] == "anual")]
nat.pivot(index="indice", columns="fuente", values=["media", "pendiente_decada", "ic95_inf", "ic95_sup", "p", "mdt", "clase_confianza"])'''),
    md("### Recalcular a la vista\n\nLa tendencia nacional de un índice con el código del motor y con `scipy.stats` "
       "(Theil-Sen debe coincidir exactamente; la p de Hamed-Rao es ≥ la de Kendall sin corrección)."),
    code('''from scipy import stats
from earthmemory.tendencias import estadistica as st
sr = pd.read_csv(RES / "series_provincias.csv")
for idx in ["SDII", "RACHAS15", "Rx5day"]:
    for prod in ["IMERG", "CHIRPS"]:
        d = sr[(sr["region"] == "República Dominicana") & (sr["indice"] == idx) & (sr["periodo"] == "anual") & (sr["fuente"] == prod)]
        if d.empty: continue
        x, y = d["anio"].to_numpy(float), d["valor"].to_numpy(float)
        r = st.trend_rows(y[None, :], x)
        ts = stats.theilslopes(y, x)
        kt = stats.kendalltau(x, y)
        tab = nat[(nat["indice"] == idx) & (nat["fuente"] == prod)].iloc[0]
        print(f"{idx:9s} {prod:6s} Sen motor={10*r['pendiente'][0]:.4f} scipy={10*ts.slope:.4f} tabla={tab['pendiente_decada']:.4f} | "
              f"p HR={r['p'][0]:.4f} p tabla={tab['p']:.4f} p Kendall(scipy)={kt.pvalue:.4f}")'''),
    md("### Un índice ETCCDI desde la lluvia diaria\n\nCDD y Rx5day de 2023 en la celda más cercana a Santo Domingo, "
       "desde IMERG diario, comparados con la tabla de la corrida."),
    code('''from earthmemory.tendencias import datos, indices as ix
P = datos.imerg_daily()
ids = datos.cell_ids()
cid = "18.450_-69.950"; k = list(ids).index(cid)
x = P.reshape(P.shape[0], -1)[:, k]
sel = (datos.DAYS >= np.datetime64("2023-01-01")) & (datos.DAYS <= np.datetime64("2023-12-31"))
thr = ix.wet_percentiles(x[:, None])
b = ix.block_indices(x[sel][:, None], thr)
print({kk: round(float(v[0]), 2) for kk, v in b.items()})
tc = pd.read_csv(RES / "por_indice" / "CDD.csv")
print("CDD 2023 recalculado:", b["CDD"][0], "| media 2001-2024 de la tabla:", tc[(tc.celda == cid) & (tc.periodo == "anual") & (tc.fuente == "IMERG")]["media"].values)'''),
    md("## 6 · Provincias\n\nSeries anuales (media ponderada por área de las celdas) con su Theil-Sen e IC 95 %. Debajo del "
       "nombre, la clase de confianza de dos productos."),
    code('''for n in ["fig3_provincias_SDII_anual", "fig3_provincias_R1mm_anual", "fig3_provincias_RACHAS15_anual", "fig3_provincias_CDD_anual", "fig3_provincias_Rx5day_anual", "fig3_provincias_SPI3_MESES_anual"]:
    fig(n, 900)'''),
    code('''p = prov[(prov["region"] != "República Dominicana") & (prov["periodo"] == "anual")]
p.groupby(["indice", "clase_confianza"]).size().unstack(fill_value=0) // 2'''),
    md("## 7 · Sequía (SPI-3)"),
    code('''fig("fig6_spi3_nacional", 900)'''),
    md("## 8 · Límites\n\nVer `reports_nacional/TENDENCIAS_P0.md`, sección *Límites*: 24 años; IMERG no es homogéneo en el "
       "tiempo (cambian sus sensores), CHIRPS diario reparte la péntada con un campo de modelo, los dos comparten "
       "infrarrojo y pluviómetros; SPI ajustado sobre la misma ventana; rejilla de 0.1°. Las tendencias son descriptivas, "
       "no causales."),
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
