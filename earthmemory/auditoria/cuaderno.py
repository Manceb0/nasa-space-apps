"""Cuaderno 07 · auditoría de confianza: solo LEE results/auditoria y figures/auditoria (no recalcula nada).
Se guarda ejecutado en notebooks/ y en HTML en reports_nacional/notebooks_html/ (mismo patrón que earthmemory/notebooks.py)."""

from __future__ import annotations

from pathlib import Path

import nbformat
from nbclient import NotebookClient
from nbconvert import HTMLExporter

ROOT = Path(__file__).resolve().parent.parent.parent
NAME = "07_auditoria_de_confianza"

SETUP = '''from pathlib import Path
import json
import pandas as pd
from IPython.display import Image, Markdown, display
ROOT = Path.cwd()
while not (ROOT / "results" / "auditoria").exists() and ROOT != ROOT.parent:
    ROOT = ROOT.parent
RES, FIG = ROOT / "results" / "auditoria", ROOT / "figures" / "auditoria"
pd.set_option("display.max_columns", 40); pd.set_option("display.width", 220)
def fig(nombre, ancho=950):
    p = FIG / f"{nombre}.png"
    display(Image(filename=str(p), width=ancho)) if p.exists() else print("figura no disponible:", nombre)'''


def md(s):
    return nbformat.v4.new_markdown_cell(s)


def code(s):
    return nbformat.v4.new_code_cell(s)


CELLS = [
    md("# 07 · Auditoría de confianza (Evidence Intelligence)\n\n**Pregunta:** ¿qué conclusión aparentemente correcta "
       "sobre sequías e inundaciones en RD podría resultar falsa al incluir la información que falta, y cuándo bastan los "
       "datos para actuar?\n\nRegla: no decimos que un satélite 'miente'. Distintas fuentes científicas pueden dar "
       "interpretaciones contradictorias del mismo territorio; aquí investigamos por qué. Este cuaderno solo lee lo que dejó "
       "`docker compose run --rm auditoria`."),
    code(SETUP),
    md("## 1 · Procedencia e independencia\n\nCada producto, qué mide o modela, sus insumos y con quién puede compartir "
       "errores. Verificado contra la documentación oficial (URLs en la tabla). **Que dos o tres productos coincidan no es "
       "una validación robusta** si cuelgan de los mismos pluviómetros."),
    code('fig("fig01_procedencia")'),
    code('''m = pd.read_csv(RES / "procedencia_matriz.csv")
m[["id", "clase", "pluviometros", "resolucion", "version", "verificado"]]'''),
    code('''for v in json.loads((RES / "procedencia.json").read_text(encoding="utf-8"))["veredicto"]:
    display(Markdown("- " + v))'''),
    md("## 2 · Verdad de terreno, con la circularidad marcada\n\nGHCN-Daily solo tiene 4 estaciones dominicanas con datos "
       "2001-2024; se añaden las estaciones sinópticas de GSOD. Todas viajan por el GTS: CHIRPS las mezcla (lista oficial "
       "mes a mes) y muy probablemente GPCC (ajuste de IMERG Final) y CPC Unified (corrección de MERRA-2). El acuerdo con "
       "ellas es, en parte, un acuerdo consigo mismos."),
    code('fig("fig02_estaciones")'),
    code('''pd.read_csv(RES / "estaciones_meta.csv")[["omm", "nombre", "red", "lat", "lon", "dias_validos", "completitud", "activa_2024", "fraccion_meses_en_chirps", "circularidad"]]'''),
    code('''d = pd.read_csv(RES / "estaciones_validacion_diaria.csv")
d[d["es_mejor_desfase"]][["nombre", "producto", "desfase_dias", "n", "r", "kge", "sesgo_rel", "pod_50", "far_50", "csi_50", "pod_100", "csi_100", "p99_obs", "p99_prod"]].round(2)'''),
    code('''mm = pd.read_csv(RES / "estaciones_validacion_mensual.csv")
mm.pivot_table(index=["nombre"], columns=["producto", "subconjunto"], values="r").round(2)'''),
    md("## 3 · Re-auditoría de '50 de 96 episodios = posible diferencia entre productos'"),
    code('''r = json.loads((RES / "reauditoria_resumen.json").read_text(encoding="utf-8"))
display(Markdown(r["definicion"]))
{k: v for k, v in r.items() if k not in ("definicion", "persistencia")}'''),
    code('fig("fig03_reauditoria_50_96")'),
    code('''pd.read_csv(RES / "reauditoria_relieve_costa.csv").round(3)'''),
    code('''pd.read_csv(RES / "reauditoria_representatividad.csv").round(3)'''),
    md("## 4 · Tasa de cambio de decisión\n\nPor provincia y mes (2001-2024): ¿declara sequía (SPI-3 ≤ −1 o ≤ −1.5) un producto y "
       "otro no? Tasa condicional = de los meses en que alguno declara sequía, fracción sin unanimidad. IC por bootstrap "
       "de bloques de año. Los productos comparten insumos: esta tasa es un **mínimo** de la incertidumbre real."),
    code('fig("fig04_cambio_decision_sequia")'),
    code('''pd.DataFrame(json.loads((RES / "cambio_decision_sequia_nacional.json").read_text(encoding="utf-8")))'''),
    code('''p = pd.read_csv(RES / "cambio_decision_sequia_provincias.csv")
p[p["umbral_spi3"] == -1.0].sort_values("tasa_condicional", ascending=False).head(10).round(3)'''),
    md("### Disparador de inundación (> 100 mm en 48 h, estilo sEAP de la Cruz Roja Dominicana)\n\nIMERG frente a CHIRPS "
       "diario. Recordatorio: el día de CHIRPS es una redistribución con el CFSv2 de la péntada anclada a estaciones."),
    code('fig("fig05_cambio_decision_inundacion")'),
    code('''f = RES / "cambio_decision_inundacion_48h.csv"
pd.read_csv(f).round(3) if f.exists() else "CHIRPS diario 2001-2024 aún no disponible"'''),
    md("## 5 · Santo Domingo, 18 de noviembre de 2023"),
    code('fig("fig06_santo_domingo")'),
    code('''sd = json.loads((RES / "santo_domingo_2023-11-18.json").read_text(encoding="utf-8"))
display(pd.DataFrame(sd["ventanas"]).round(1))
sd["descomposicion"], sd["veredicto"], sd["ghcn_78486"]'''),
    md("## 6 · Prototipo: dónde medir después (PRELIMINAR)\n\nNo prueba dónde deben ir estaciones: faltan acceso, exposición, "
       "población y la red real de ONAMET/INDRHI (que no está en GHCN-D)."),
    code('fig("fig07_donde_medir_prototipo")'),
    code('''pd.read_csv(RES / "donde_medir_prototipo.csv").head(15).round(3)'''),
]


def build(out_nb: Path = ROOT / "notebooks", out_html: Path = ROOT / "reports_nacional" / "notebooks_html", timeout: int = 600):
    out_nb.mkdir(parents=True, exist_ok=True)
    out_html.mkdir(parents=True, exist_ok=True)
    nb = nbformat.v4.new_notebook()
    nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
    nb.metadata["language_info"] = {"name": "python"}
    nb.cells = CELLS
    NotebookClient(nb, timeout=timeout, kernel_name="python3", resources={"metadata": {"path": str(ROOT)}}).execute()
    for c in nb.cells:
        c.metadata.pop("execution", None)
    nbformat.write(nb, out_nb / f"{NAME}.ipynb")
    html, _ = HTMLExporter(embed_images=True).from_notebook_node(nb)
    (out_html / f"{NAME}.html").write_text(html, encoding="utf-8", newline="\n")
    print(f"  cuaderno {NAME} ejecutado", flush=True)


if __name__ == "__main__":
    build()
