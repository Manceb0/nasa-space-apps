"""Cuaderno 08 · caso Yuna: se construye, se ejecuta sin pantalla y se exporta a HTML (patrón de earthmemory/notebooks.py).
Solo LEE results/yuna y figures/yuna."""

from __future__ import annotations

import nbformat
from nbclient import NotebookClient
from nbconvert import HTMLExporter

from .common import NB_DIR, NB_HTML, ROOT

SETUP = '''from pathlib import Path
import json
import pandas as pd
from IPython.display import Image, Markdown, display
ROOT = Path.cwd()
while not (ROOT / "results" / "yuna").exists() and ROOT != ROOT.parent:
    ROOT = ROOT.parent
RES, FIG = ROOT / "results" / "yuna", ROOT / "figures" / "yuna"
pd.set_option("display.max_columns", 40); pd.set_option("display.width", 220); pd.set_option("display.max_colwidth", 80)
def fig(nombre, ancho=900):
    display(Image(filename=str(FIG / f"{nombre}.png"), width=ancho))'''


def md(s):
    return nbformat.v4.new_markdown_cell(s)


def code(s):
    return nbformat.v4.new_code_cell(s)


CELLS = [
    md("# 08 · Caso Yuna: lluvia y memoria arriba → presa de Hatillo → inundación abajo\n\n"
       "Hipótesis de investigación (no causalidad demostrada): la lluvia y el estado antecedente del Alto Yuna "
       "(IMERG · SMAP L4 · GLDAS) → escorrentía y respuesta del río → operación de Hatillo → inundación en el Bajo Yuna. "
       "Giro «Mentalist»: la correlación entre la humedad de cabecera y las inundaciones de abajo podría cambiar por la "
       "operación del embalse. Encontrar eso es un resultado válido.\n\n"
       "Cada variable lleva su clase: **OBSERVACIÓN** (JRC GSW), **RECUPERACIÓN SATELITAL** (IMERG, CHIRPS), "
       "**MODELO CON ASIMILACIÓN** (SMAP L4), **MODELO FORZADO** (GLDAS), **SIMULACIÓN HIDROLÓGICA** (GEOGLOWS v2)."),
    code(SETUP),
    md("## 1 · La cuenca y qué drena dónde\n\nHydroBASINS v1c nivel 10 + HydroRIVERS (Lehner y Grill 2013)."),
    code('fig("fig_y1_cuenca_yuna")'),
    code('''cu = json.loads((RES / "cuencas_resumen.json").read_text(encoding="utf-8"))
print(json.dumps({k: cu[k] for k in ("areas_km2", "hatillo", "camu", "salidas")}, ensure_ascii=False, indent=1))'''),
    code('''pd.read_csv(RES / "que_drena_donde.csv")[["punto", "celda_grados", "frac_Yuna", "frac_Yaque del Norte",
    "frac_Yaque del Sur", "frac_alto_hatillo", "frac_camu", "frac_bajo_yuna", "salida_cuenca"]]'''),
    md("## 2 · Catálogo de eventos (registro documental, cada uno con URL)"),
    code('''cat = pd.read_csv(RES / "catalogo_eventos.csv")
display(cat["zona"].value_counts())
cat[["id", "inicio", "fin", "precision", "zona", "confianza", "n_fuentes", "n_fuentes_leidas", "usable_backtest", "motivo_exclusion"]]'''),
    code('''cat.loc[cat["hatillo_menciones"].fillna("").str.len() > 0, ["id", "hatillo_menciones"]]'''),
    md("## 3 · Agua observada (JRC GSW mensual, Landsat) y el embalse de Hatillo"),
    code('fig("fig_y2_agua_observada_gsw")'),
    code('''print(json.loads((RES / "gsw_mascaras.json").read_text()))'''),
    md("## 3b · Inundación observada con MODIS MCDWD_L3 (2003-2025)\n\n"
       "Compuesto de 2 días (Flood_2Day_250m): 0 sin agua · 1 agua de referencia · 2 inundación recurrente · "
       "3 inundación inusual · 255 datos insuficientes (nubes). Inundación observada = clase 3 por encima del p95 de días "
       "secos de referencia y ≥ 2 km². Sin días visibles = indeterminado, no «sin inundación»."),
    code('fig("fig_y6_inundacion_observada_mcdwd")'),
    code('''r = json.loads((RES / "mcdwd_resumen.json").read_text(encoding="utf-8"))
print(json.dumps({k: r[k] for k in ("n_dias", "insuf_media_yuna_2d", "MAX_INSUF", "MIN_KM2")}, indent=1))
pd.read_csv(RES / "mcdwd_por_evento.csv")[["id", "observa", "inund_km2_max_yuna", "anomalia_km2_yuna", "insuf_min_yuna", "n_obs_yuna", "n_dias"]]'''),
    code('''pd.read_csv(RES / "mcdwd_meses_gsw_sin_evento.csv")[["mes", "observa", "inund_km2_max_yuna", "insuf_min_yuna"]]'''),
    code('''pd.read_csv(RES / "backtest_verificacion_mcdwd.csv")'''),
    md("## 4 · Paneles por evento (mismas escalas)"),
    code('''for f in sorted(FIG.glob("fig_y3_paneles_eventos_*.png")):
    display(Image(filename=str(f), width=950))'''),
    code('''pd.read_csv(RES / "paneles_eventos.csv").set_index("id").T.head(60)'''),
    code('''pd.read_csv(RES / "datos_suficientes_por_evento.csv")'''),
    md("## 5 · Backtest de disparadores (n pequeño)\n\nCalibración 2001-2015, prueba 2016-2024; IC 95 % por bootstrap "
       "de años. FAR es cota superior: el catálogo de prensa es incompleto."),
    code('fig("fig_y4_backtest_disparadores")'),
    code('''bt = pd.read_csv(RES / "backtest_disparadores.csv")
bt[["disparador", "periodo", "eventos", "aciertos", "fallos", "episodios", "falsas_alarmas", "POD", "POD_ic95", "FAR", "FAR_ic95", "CSI", "CSI_ic95"]]'''),
    md("## 6 · La presa como factor de confusión"),
    code('fig("fig_y5_presa_confusor")'),
    code('''r = json.loads((RES / "analisis_resumen.json").read_text(encoding="utf-8"))
print(json.dumps(r, ensure_ascii=False, indent=1)[:4000])'''),
    code('''pd.read_csv(RES / "presa_correlaciones_mensuales.csv")'''),
    md("## Límites\n\n- n de eventos pequeño: los IC son anchos y casi nada distingue un disparador de otro.\n"
       "- IMERG, SMAP L4 y CHIRPS comparten insumos (pluviómetros GPCC/GTS; SMAP L4 ajusta su lluvia a IMERG): "
       "su acuerdo no es validación independiente.\n- GEOGLOWS no son aforos ni representa la operación de Hatillo.\n"
       "- No hay series públicas de nivel/descarga de Hatillo: el área GSW es un sustituto mensual con huecos por nubes."),
]


def build_and_run(timeout: int = 900) -> None:
    NB_DIR.mkdir(parents=True, exist_ok=True)
    NB_HTML.mkdir(parents=True, exist_ok=True)
    nb = nbformat.v4.new_notebook()
    nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
    nb.metadata["language_info"] = {"name": "python"}
    nb.cells = CELLS
    NotebookClient(nb, timeout=timeout, kernel_name="python3", resources={"metadata": {"path": str(ROOT)}}).execute()
    for c in nb.cells:
        c.metadata.pop("execution", None)
    nbformat.write(nb, NB_DIR / "08_caso_yuna.ipynb")
    html, _ = HTMLExporter(embed_images=True).from_notebook_node(nb)
    (NB_HTML / "08_caso_yuna.html").write_text(html, encoding="utf-8", newline="\n")
    print("  cuaderno 08_caso_yuna ejecutado", flush=True)


if __name__ == "__main__":
    build_and_run()
