"""Cuaderno 09 · Testigos e hipótesis: se construye, se ejecuta sin pantalla y se exporta a HTML (patrón de
earthmemory/notebooks.py). Solo LEE results/testigos y figures/testigos: no recalcula nada."""

from __future__ import annotations

import nbformat
from nbclient import NotebookClient
from nbconvert import HTMLExporter

from .common import NB_DIR, NB_HTML, ROOT

SETUP = '''from pathlib import Path
import json
import numpy as np
import pandas as pd
from IPython.display import Image, Markdown, display
ROOT = Path.cwd()
while not (ROOT / "results" / "testigos").exists() and ROOT != ROOT.parent:
    ROOT = ROOT.parent
RES, FIG = ROOT / "results" / "testigos", ROOT / "figures" / "testigos"
J = lambda n: json.loads((RES / n).read_text(encoding="utf-8")) if (RES / n).exists() else None
pd.set_option("display.max_columns", 40); pd.set_option("display.width", 220)
def fig(nombre, ancho=900):
    p = FIG / f"{nombre}.png"
    display(Image(filename=str(p), width=ancho)) if p.exists() else print("sin figura", nombre)'''


def md(s):
    return nbformat.v4.new_markdown_cell(s)


def code(s):
    return nbformat.v4.new_code_cell(s)


CELLS = [
    md("# 09 · Testigos e hipótesis\n\nStellar Horizons · NASA Space Apps 2026. Aquí se intenta **romper** las "
       "conclusiones de Earth Memory con datos que no salen del mismo modelo: SMAP L3 (radiómetro de banda L), "
       "un índice de lluvia antecedente (API) de IMERG, CHIRPS y Hansen. Un resultado que se cae es un resultado. "
       "Este cuaderno solo lee `results/testigos/`."),
    code(SETUP),
    md("## 1 · ¿Qué puede ver SMAP L3?\n\nCalidad 'recomendada' por píxel de 9 km. En bosque denso de montaña "
       "(agua en la vegetación > 5 kg/m²) el radiómetro casi no ve el suelo: si no lo ve, no se fuerza un resultado."),
    code('fig("t1_smap_l3_calidad")\nq = J("smap_l3_calidad_resumen.json")\npd.DataFrame(q["puntos"]).T'),
    md("## 2 · Los dos pares con el testigo SMAP L3\n\nMisma métrica que antes cuando se puede (γ del ARX mensual; "
       "eficiencia mensual), más la respuesta a eventos de lluvia (IMERG diario entre dos pasos del satélite). "
       "p calibrado con sustitutos de igual respuesta."),
    code('fig("t2_pares_testigo_smap_l3")\nfig("t3_eventos_lluvia_smap_l3")\nP = J("pares_smap_l3.json")\n'
         'print(json.dumps(P["veredictos"], ensure_ascii=False, indent=1))\n'
         'pd.read_csv(RES / "pares_smap_l3.csv")[["par", "etiqueta", "metrica", "independiente", "delta", "delta_ic95", '
         '"p_calibrado", "tasa_p05_nulo", "n_A", "n_B"]]'),
    md("## 3 · ¿Memoria del suelo o memoria de la lluvia?\n\nModelos anidados: severidad + efectos fijos → + lluvia "
       "antecedente (API) → + suelo antecedente (GLDAS). Si el suelo deja de aportar al entrar la lluvia, la 'memoria' "
       "era de la lluvia."),
    code('fig("t4_memoria_lluvia_vs_suelo")\nM = J("memoria_lluvia_vs_suelo.json")\n'
         'print(json.dumps(M["reproduccion_original"], ensure_ascii=False, indent=1))\n'
         'print(json.dumps(M["resumen_principal"], ensure_ascii=False, indent=1))\n'
         'd = pd.read_csv(RES / "memoria_lluvia_vs_suelo.csv")\n'
         'd[d.resultado == "z_retorno_SM_RAIZ"][["lluvia_antecedente", "efectos_fijos", "n", "beta_suelo_M2", "beta_suelo_M3", '
         '"beta_suelo_M3_ic95", "q_beta_suelo_M3", "r2p_suelo_dado_lluvia", "r2p_lluvia_dado_suelo", "varianza_comun", "veredicto"]]'),
    md("## 4 · ¿Sobrevive el umbral θ fuera del cubo de TerraClimate?"),
    code('fig("t5_umbral_testigos")\nU = J("umbral_testigos.json")\n'
         'pd.DataFrame({k: {kk: v[kk] for kk in ("n_celdas", "n_obs", "theta", "theta_ic95", "b5", "b5_ic95", "b5_excluye_0")} '
         'for k, v in U["variantes"].items()}).T'),
    md("## 5 · Intensidad de la lluvia de retorno con CHIRPS"),
    code('fig("t7_intensidad_chirps")\nI = J("intensidad_chirps.json")\n'
         'print({k: v for k, v in I.items() if k != "tabla"})\npd.DataFrame(I.get("tabla", []))'),
    md("## 6 · Bosque (Hansen GFC v1.13), descriptivo"),
    code('fig("t6_bosque_hansen")\npd.read_csv(RES / "bosque_hansen.csv")'),
    md("## 7 · NDVI (AppEEARS) y límites\n\nEl pedido de AppEEARS no fue accesible con el token de Earthdata (la API "
       "pide su propio inicio de sesión); no se usaron contraseñas. Ver `data/testigos/MANIFEST.json`, sección `rutas`."),
    code('man = json.loads((ROOT / "data/testigos/MANIFEST.json").read_text(encoding="utf-8"))\n'
         'print(json.dumps({k: v for k, v in man["rutas"].items() if k != "SMAP_L3E_indices"}, ensure_ascii=False, indent=1)[:3000])'),
]


def build_and_run(timeout: int = 900):
    NB_DIR.mkdir(parents=True, exist_ok=True)
    NB_HTML.mkdir(parents=True, exist_ok=True)
    nb = nbformat.v4.new_notebook()
    nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
    nb.metadata["language_info"] = {"name": "python"}
    nb.cells = CELLS
    NotebookClient(nb, timeout=timeout, kernel_name="python3", resources={"metadata": {"path": str(ROOT)}}).execute()
    for c in nb.cells:
        c.metadata.pop("execution", None)
    p = NB_DIR / "09_testigos_e_hipotesis.ipynb"
    nbformat.write(nb, p)
    html, _ = HTMLExporter(embed_images=True).from_notebook_node(nb)
    (NB_HTML / "09_testigos_e_hipotesis.html").write_text(html, encoding="utf-8", newline="\n")
    print("  cuaderno 09 ejecutado", flush=True)
    return p


if __name__ == "__main__":
    build_and_run()
