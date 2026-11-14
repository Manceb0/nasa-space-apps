"""Construye, ejecuta (sin pantalla) y exporta a HTML los cuadernos de Earth Memory nacional.

    python -m earthmemory.notebooks        (después de python -m earthmemory.nacional)

Los cuadernos solo LEEN lo que dejó la corrida (results/nacional, figures/nacional): no recalculan ni
inventan nada. Se guardan ejecutados en notebooks/ y en HTML en reports_nacional/notebooks_html/.
"""

from __future__ import annotations

from pathlib import Path

import nbformat
from nbclient import NotebookClient
from nbconvert import HTMLExporter

ROOT = Path(__file__).resolve().parent.parent

SETUP = '''from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from IPython.display import Image, Markdown, display
ROOT = Path.cwd()
while not (ROOT / "results" / "nacional").exists() and ROOT != ROOT.parent:
    ROOT = ROOT.parent
RES, FIG = ROOT / "results" / "nacional", ROOT / "figures" / "nacional"
corrida = json.loads((RES / "corrida.json").read_text(encoding="utf-8"))
pd.set_option("display.max_columns", 30); pd.set_option("display.width", 200)
def fig(nombre, ancho=900):
    display(Image(filename=str(FIG / f"{nombre}.png"), width=ancho))'''


def md(s):
    return nbformat.v4.new_markdown_cell(s)


def code(s):
    return nbformat.v4.new_code_cell(s)


NB = {
    "01_datos_y_calidad": [
        md("# 01 · Datos y calidad\n\nEarth Memory nacional (República Dominicana). Este cuaderno revisa **qué datos "
           "entraron, de dónde salieron y con qué cobertura**, antes de mirar cualquier resultado. Solo lee archivos "
           "que dejó la corrida (`results/nacional`, `data/nacional/MANIFEST.json`)."),
        code(SETUP),
        md("## Manifiesto de descargas\n\nCada archivo descargado tiene su URL exacta (sin credenciales), SHA-256, "
           "tamaño y fecha. La sección `rutas` guarda qué ruta funcionó y el error exacto de la que falló."),
        code('''man = json.loads((ROOT / "data/nacional/MANIFEST.json").read_text(encoding="utf-8"))
arch = pd.DataFrame([{"archivo": k, **{kk: v[kk] for kk in ("bytes", "dataset") if kk in v}} for k, v in man["archivos"].items()])
arch["dataset"] = arch["dataset"].fillna(arch["archivo"].str.split("/").str[0])
display(arch.groupby("dataset").agg(archivos=("archivo", "size"), MB=("bytes", lambda b: round(b.sum() / 1e6, 1))))
pd.DataFrame({k: v for k, v in man.get("rutas", {}).items() if isinstance(v, dict)}).T[["estado", "pedidos", "n_errores"]]'''),
        md("## Celdas: cuántas hay y cuántas entran\n\nUna celda entra si tiene al menos 25 % de su área en RD, más "
           "RD que Haití y (en GLDAS) dato de suelo. Se informa también cuántas tocan el país."),
        code('''pd.Series({k: v for k, v in corrida.items() if k.startswith("celdas_") or k.startswith("dias_") or k.startswith("meses_")})'''),
        code('''ci = pd.read_csv(RES / "celdas_imerg.csv"); cg = pd.read_csv(RES / "celdas_gldas.csv")
fig_, ax = plt.subplots(1, 2, figsize=(10, 3.2))
for a, c, t in ((ax[0], ci, "IMERG 0.1°"), (ax[1], cg, "GLDAS 0.25°")):
    s = a.scatter(c["lon"], c["lat"], c=c["frac_pais"], s=6 if t.startswith("IMERG") else 30, marker="s", cmap="viridis")
    a.scatter(c.loc[c["incluida"], "lon"], c.loc[c["incluida"], "lat"], s=1, color="k")
    a.set_title(f"{t}: fracción en RD (punto negro = incluida)", fontsize=9); a.set_aspect(1 / np.cos(np.radians(18.8)))
plt.colorbar(s, ax=ax, shrink=0.8); plt.show()
cg["motivo_exclusion"].fillna("incluida").value_counts()'''),
        md("## Provincias (geoBoundaries ADM1)\n\nCuántas celdas aportan a cada provincia. Provincias chicas (p. ej. "
           "Distrito Nacional) dependen de muy pocas celdas GLDAS: sus series de suelo son casi las de 1-2 celdas."),
        code('''pd.read_csv(RES / "provincias_cobertura.csv").sort_values("area_km2")'''),
        md("## Lluvia IMERG frente a la lluvia que forzó a GLDAS\n\nGLDAS-2.1 se forzó con GPCP, no con IMERG. Si las "
           "dos lluvias no coinciden, una 'contradicción' entre lluvia IMERG y suelo GLDAS puede ser diferencia entre "
           "productos. Aquí se comparan los SPI-3 de las dos en cada celda GLDAS."),
        code('''p = pd.read_parquet(RES / "parquet/panel_celdas_gldas_mensual.parquet")
spi = p[p["variable"] == "SPI3"].pivot(index="fecha", columns="celda", values="valor")
ep_mod = RES / "episodios_lluvia_modelo.csv"
print("Episodios con lluvia del modelo:", len(pd.read_csv(ep_mod)) if ep_mod.exists() else "no disponible")
ct = pd.read_csv(RES / "contradicciones_por_celda.csv")
cols = [c for c in ct.columns if c.startswith("n_A_raiz") or c.startswith("n_episodios")]
ct[cols].sum()'''),
        md("## Comprobación con NASA POWER (MERRA-2)\n\nPOWER sirve MERRA-2 a ~0.5°. No es independiente para el suelo "
           "(los dos son modelos), pero sí ayuda a ver si la lluvia y la raíz se mueven igual."),
        code('''f = RES / "comparacion_power_merra2.csv"
pd.read_csv(f).describe().T[["count", "mean", "50%", "min", "max"]] if f.exists() else "sin datos POWER"'''),
    ],
    "02_mapas_nacionales": [
        md("# 02 · Mapas nacionales\n\nTodos los mapas dibujan cada celda como el rectángulo que es (IMERG 0.1°, GLDAS "
           "0.25°), sin interpolar, con el contorno del país y las provincias."),
        code(SETUP),
        md("## Climatologías 2001-2024"),
        code('fig("fig01_climatologias")'),
        md("## Tendencias por celda\n\nTheil-Sen + Mann-Kendall con corrección AR(1) sobre medias anuales de anomalías. "
           "Rayado = no significativo tras calibrar el p con sustitutos nulos y aplicar Benjamini-Hochberg por variable."),
        code('fig("fig02_tendencias")'),
        code('''tr = pd.read_csv(RES / "tendencias_celdas.csv")
tr.groupby("variable").agg(celdas=("celda", "size"), pendiente_mediana=("pendiente_decada", "median"),
                           q05_nominal=("q_bh", lambda q: int((q < 0.05).sum())),
                           q05_calibrado=("q_bh_empirico", lambda q: int((q < 0.05).sum())))'''),
        md("## Sequías de 2015 y 2019-2020, mes a mes\n\nArriba la lluvia (SPI-3, IMERG 0.1°), abajo el suelo (z de la "
           "zona de raíces, GLDAS 0.25°). Se ve cuándo el suelo sigue a la lluvia y cuándo se queda atrás."),
        code('fig("fig03_sequia_2015")'),
        code('fig("fig04_sequia_2019_2020")'),
        md("## Provincias (series ponderadas por área)"),
        code('fig("fig10_provincias", 800)'),
        code('''pv = pd.read_parquet(RES / "parquet/provincias_mensual.parquet")
z = pv[pv["variable"] == "z_SM_RAIZ"].pivot(index="fecha", columns="provincia", values="valor")
(z < -1).sum().sort_values(ascending=False).rename("meses con z raíz < -1").to_frame().head(10)'''),
    ],
    "03_memoria_y_contrastes": [
        md("# 03 · Memoria del terreno y contrastes\n\n¿Por qué dos territorios con lluvia parecida responden distinto? "
           "Aquí: memoria y acople por celda, episodios de contradicción, pares con lluvia parecida y factores asociados. "
           "Todo es asociación, nunca causa."),
        code(SETUP),
        md("## Memoria y acople"),
        code('fig("fig06_memoria_acople")'),
        md("## Contradicciones\n\nA = la lluvia volvió (SPI-3 ≥ 0 tras sequía) pero la raíz no (z < −1 dos meses). "
           "B1 = suelo seco sin sequía de lluvia. B2 = suelo normal en sequía de lluvia. El panel b repite A con la "
           "lluvia que forzó a GLDAS."),
        code('fig("fig05_contradicciones")'),
        code('''ep = pd.read_csv(RES / "episodios.csv")
ep["contradiccion_A_SM_RAIZ_etiqueta"].value_counts(dropna=False) if "contradiccion_A_SM_RAIZ_etiqueta" in ep else "sin etiqueta"'''),
        md("## Pares con lluvia parecida: ranking\n\n`q_bh_calibrado` usa el p corregido por la inflación medida en "
           "el nulo (cuaderno 04). `etiqueta_producto` dice si el contraste sigue con la lluvia del modelo."),
        code('''rk = pd.read_csv(RES / "contrastes_ranking.csv")
cols = [c for c in ["rango", "celda_a", "celda_b", "respuesta", "metrica", "delta", "ic95_bajo", "ic95_alto", "q_bh",
                    "q_bh_calibrado", "robustez", "etiqueta_producto", "distancia_km", "r_spi3"] if c in rk]
rk[cols].head(12)'''),
        md("## El caso para la demo"),
        code('fig("fig07_mejor_contraste")'),
        code('''print(json.dumps(json.loads((RES / "episodios_emparejados_resumen.json").read_text(encoding="utf-8")), ensure_ascii=False, indent=1)[:3000])'''),
        md("## Factores asociados\n\nβ = cambio del resultado por 1 DE del factor (control: severidad). IC por bootstrap "
           "de conglomerados de año."),
        code('''fa = pd.read_csv(RES / "factores_asociacion.csv")
fa[["resultado", "factor", "n", "beta", "ic95", "p", "q_bh"]]'''),
        md("## Latigazos de lluvia y de suelo\n\nTransiciones bruscas seco→húmedo (cruce de −0.84 a +0.84 en ≤ 3 "
           "meses). Stojanovic et al. (2025) las cuentan para la lluvia de toda La Española; aquí se comparan con las del suelo."),
        code('''w = pd.read_csv(RES / "latigazos_por_celda.csv")
w.drop(columns="celda").sum()'''),
    ],
    "04_calibracion_y_limites": [
        md("# 04 · Calibración de falsos positivos y límites\n\nSi no hubiera señal, ¿cuántas veces dirían "
           "\"significativo\" nuestras pruebas? Se mide con sustitutos nulos que conservan la autocorrelación, la "
           "estacionalidad y la correlación entre celdas."),
        code(SETUP),
        code('fig("fig08_calibracion_fpr")'),
        md("## Tendencias: tasa nominal vs empírica"),
        code('''cal = json.loads((RES / "calibracion_tendencias.json").read_text(encoding="utf-8"))
pd.DataFrame({v: {"fases": c["fase"]["tasa_empirica_p05"], "bloques": c["bloques"]["tasa_empirica_p05"],
                  "p_campo": c["fase"]["p_campo"], "I_Moran": c["moran_I_pendiente"],
                  "q05_nominal": c["celdas_q05_nominal"], "q05_calibrado": c["celdas_q05_calibrado"]} for v, c in cal.items()}).T'''),
        md("## Pares: inflación del error estándar\n\nLa prueba de pares con bootstrap de bloques de 12 meses rechaza "
           "más de lo nominal bajo el nulo. Se corrige dividiendo |Δ/EE| por el factor de inflación σ medido en el nulo."),
        code('''pd.read_csv(RES / "calibracion_pares_resumen.csv")'''),
        md("## Santo Domingo, 18 de noviembre de 2023\n\nEl pluviómetro de ONAMET en Arroyo Hondo Viejo reportó 431 mm "
           "en 24 h (preliminar). Una celda IMERG promedia ~110 km²: el producto en rejilla suaviza el extremo. Un evento no "
           "es una tendencia. Los valores IMERG son cálculo nuestro."),
        code('fig("fig09_santo_domingo_2023")'),
        code('''print(json.dumps(json.loads((RES / "evento_santo_domingo_2023-11-18.json").read_text(encoding="utf-8")), ensure_ascii=False, indent=1)[:2500])
pd.read_csv(RES / "evento_santo_domingo_por_celda.csv").head(10)'''),
        md("## Límites que no se pueden corregir con estadística\n\n- GLDAS es un modelo forzado con GPCP y sin asimilación "
           "de suelo: describe el suelo del modelo, no mediciones.\n- 24 años no separan cambio de largo plazo de "
           "variabilidad decenal.\n- Celdas vecinas comparten lluvia y forzamiento: dos pares que comparten celda no son "
           "dos hallazgos.\n- Ninguna asociación aquí es causa.\n- NDVI/NPP (AppEEARS) y SMAP no entraron en esta corrida; "
           "GRACE-FO (~3°) solo serviría como contexto nacional."),
    ],
}


def build_and_run(out_nb: Path = ROOT / "notebooks", out_html: Path = ROOT / "reports_nacional" / "notebooks_html",
                  timeout: int = 900) -> list[Path]:
    out_nb.mkdir(parents=True, exist_ok=True)
    out_html.mkdir(parents=True, exist_ok=True)
    done = []
    for name, cells in NB.items():
        nb = nbformat.v4.new_notebook()
        nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
        nb.metadata["language_info"] = {"name": "python"}
        nb.cells = cells
        NotebookClient(nb, timeout=timeout, kernel_name="python3", resources={"metadata": {"path": str(ROOT)}}).execute()
        for c in nb.cells:  # salidas deterministas: sin contadores ni tiempos de ejecución
            c.metadata.pop("execution", None)
        p = out_nb / f"{name}.ipynb"
        nbformat.write(nb, p)
        html, _ = HTMLExporter(embed_images=True).from_notebook_node(nb)
        (out_html / f"{name}.html").write_text(html, encoding="utf-8", newline="\n")
        done.append(p)
        print(f"  cuaderno {name} ejecutado", flush=True)
    return done


if __name__ == "__main__":
    build_and_run()
