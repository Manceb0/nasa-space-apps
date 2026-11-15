"""reports_nacional/TENDENCIAS_P0.md: método, resultados, qué se sostiene, qué no es detectable, límites, citas."""

from __future__ import annotations

import numpy as np
import pandas as pd

from ..hr.common import ROOT
from . import indices as ix
from .motor import NATIONAL

REPORT = ROOT / "reports_nacional" / "TENDENCIAS_P0.md"


def f(v, nd=2):
    if v is None or (isinstance(v, float) and not np.isfinite(v)):
        return "–"
    return f"{v:.{nd}f}" if abs(v) < 1000 else f"{v:.0f}"


def _cls_row(s, idx, per="anual"):
    a = s[(s["indice"] == idx) & (s["periodo"] == per) & (s["fuente"] == "IMERG")]
    return a.iloc[0] if len(a) else None


def disputes_and_single(s: pd.DataFrame, min_cells: int = 20) -> tuple[list, list]:
    disp, solo = [], []
    for per in ix.PERIODS:
        for k in ix.DAILY + ix.SPI_KEYS:
            a = s[(s["indice"] == k) & (s["periodo"] == per) & (s["fuente"] == "IMERG")]
            b = s[(s["indice"] == k) & (s["periodo"] == per) & (s["fuente"] == "CHIRPS")]
            if a.empty or b.empty:
                continue
            a, b = a.iloc[0], b.iloc[0]
            lab = f"{k} ({ix.PERIODS[per][0].lower()})"
            def _lib(r):
                v = r.get("prueba_liberal")
                return v is not None and pd.notna(v) and bool(v)
            lib = " ⚠" if (_lib(a) or _lib(b)) else ""
            da = np.sign(a["celdas_sig_fdr_aumento"] - a["celdas_sig_fdr_descenso"])
            db = np.sign(b["celdas_sig_fdr_aumento"] - b["celdas_sig_fdr_descenso"])
            if a["celdas_sig_fdr"] >= min_cells and b["celdas_sig_fdr"] >= min_cells and da * db < 0:
                disp.append(f"- **{lab}**: IMERG {a['celdas_sig_fdr']} celdas significativas ({a['celdas_sig_fdr_aumento']} ↑ / "
                            f"{a['celdas_sig_fdr_descenso']} ↓) frente a CHIRPS {b['celdas_sig_fdr']} ({b['celdas_sig_fdr_aumento']} ↑ / "
                            f"{b['celdas_sig_fdr_descenso']} ↓); {a['celdas_en_disputa']} celdas en disputa, {a['celdas_robusta']} robustas.{lib}")
                continue
            for one, other, n1, n2 in ((a, b, "IMERG", "CHIRPS"), (b, a, "CHIRPS", "IMERG")):
                if one["celdas_sig_fdr"] >= min_cells and one["celdas_robusta"] < 0.25 * one["celdas_sig_fdr"]:
                    solo.append(f"- {lab}: {n1} {one['celdas_sig_fdr']} celdas significativas ({one['celdas_sig_fdr_aumento']} ↑ / "
                                f"{one['celdas_sig_fdr_descenso']} ↓), {n2} {other['celdas_sig_fdr']}; {one['celdas_robusta']} robustas, "
                                f"{one['celdas_en_disputa']} en disputa.{lib}")
    return disp, solo


def write(state: dict, summ: pd.DataFrame) -> None:
    out, cal = state["out"], state["cal"]
    tr = out["regiones"]
    two = "CHIRPS" in state["series"]
    nat = tr[tr["region"] == NATIONAL]
    L = []
    A = L.append
    A("# P0 · Tendencias de periodos secos y lluvia extrema en la República Dominicana (2001-2024)\n")
    A(f"Equipo Stellar Horizons · NASA Space Apps 2026 · reto *Be An Earth System Trend Detective!* · corrida "
      f"{state['fecha_utc']}\n")
    A("**Pregunta.** ¿Cambiaron entre 2001 y 2024 los periodos secos y la lluvia extrema en la RD, dónde, cuánto, con "
      "qué incertidumbre, y lo confirman dos productos distintos? Todo lo que sigue es descriptivo: tendencias "
      "observadas, **sin atribución de causas**.\n")
    if two:
        sa = summ[(summ["periodo"] == "anual") & (summ["fuente"] == "IMERG")]
        sc = summ[(summ["periodo"] == "anual") & (summ["fuente"] == "CHIRPS")].set_index("indice")
        ext = ["R20mm", "R50mm", "Rx1day", "Rx5day", "R95pTOT", "R99pTOT"]
        ext_i = int(sa[sa["indice"].isin(ext)]["celdas_sig_fdr"].sum())
        ext_c = int(sc.loc[[e for e in ext if e in sc.index], "celdas_sig_fdr"].sum())
        rob = sa.set_index("indice")["celdas_robusta"]
        allrob = summ[summ["fuente"] == "IMERG"]
        disp, _ = disputes_and_single(summ)
        cc = cal[cal["nivel"] == "celdas"]
        rx = sa.set_index("indice").loc["Rx5day"]
        A("## Resumen\n")
        A(f"- **Tendencias robustas (IMERG y CHIRPS de acuerdo y significativas tras FDR): casi ninguna.** En los 21 "
          f"índices anuales hay {int(rob.sum())} celda-índice robustas de 442 × 21 posibles y "
          f"{int(sa['provincias_robusta'].sum())} provincia-índice robustas; sumando estaciones, "
          f"{int(allrob['celdas_robusta'].sum())} celda-índice-periodo robustas.")
        A(f"- **Lluvia extrema (R20mm, R50mm, Rx1day, Rx5day, R95pTOT, R99pTOT, anual): sin tendencia detectable** a nivel "
          f"de celda tras FDR ({ext_i} celda-índice significativas en IMERG, {ext_c} en CHIRPS). Con 24 años solo se "
          f"detectarían cambios grandes (tendencia mínima detectable de la serie nacional IMERG de Rx5day: "
          f"{f(rx['nacional_mdt'], 0)} mm/década, {f(100 * rx['nacional_mdt'] / rx['nacional_media'], 0)} % de la media por década).")
        A(f"- **Las fuentes discrepan en la frecuencia y la intensidad de la lluvia diaria.** IMERG muestra menos días "
          f"húmedos, más intensidad (SDII) y más rachas secas largas; CHIRPS muestra lo contrario o nada. Combinaciones "
          f"en disputa (≥ 20 celdas significativas en cada producto con signo opuesto): "
          + (", ".join(d.split("**")[1] for d in disp) if disp else "ninguna") + ". Es una señal de los productos "
          "(cómo detectan llovizna, cómo reparten la lluvia entre días), no del clima, hasta que un tercer testigo la confirme.")
        A(f"- **Sequía (SPI):** sin tendencia en IMERG; CHIRPS indica más meses y eventos SPI-12 ≤ −1 en parte del país, pero "
          f"para SPI-12 la prueba es **liberal** (falsos positivos medidos de hasta "
          f"{f(cc[cc['indice'].str.startswith('SPI12')]['fpr_local_p05'].max(), 2)} frente a 0.05 nominal) y no se confirma "
          "con IMERG: no se presenta como hallazgo.")
        A(f"- **Falsos positivos medidos** (1 000 sustitutos por índice y método): tasa media de p < 0.05 por celda "
          f"{f(cc[cc['metodo'].str.startswith('fases')]['fpr_local_p05'].mean(), 3)} (fases) y "
          f"{f(cc[~cc['metodo'].str.startswith('fases')]['fpr_local_p05'].mean(), 3)} (bloques), cerca del 0.05 nominal "
          "salvo en los índices SPI-12 y, en menor medida, PRCPTOT/R1mm de IMERG.")
        A("- 'Sin señal detectable' significa **no detectable con 24 años**, no 'sin cambio'. Nada aquí atribuye causas.\n")
    A("## 1 · Datos\n")
    A("| producto | tipo de fuente | resolución | días | uso |\n|---|---|---|---|---|")
    A("| NASA GPM IMERG V07 Final diario (GPM_3IMERGDF.07) | recuperación satelital calibrada con pluviómetros (GPCC mensual) "
      "| 0.1° | 8 766 (2001-01-01 a 2024-12-31; día = 00-24 UTC) | producto principal |")
    if two:
        d = state["descarga"]
        if "identidad_con_tif_oficial_nov2023" not in d:
            import json
            from .descarga import MANIFEST
            d = json.loads(MANIFEST.read_text(encoding="utf-8")).get("rutas", {}).get("chirps_diario", {})
        idn = d.get("identidad_con_tif_oficial_nov2023", {})
        A("| CHIRPS v2.0 diario (CHC/UCSB) | satélite + estaciones | 0.05° nativa, **agregada a 0.1°** por media de área | "
          "8 766 | segundo producto (acuerdo) |")
        A("")
        A(f"CHIRPS diario se descargó recortado en el servidor (IRI/LDEO Data Library, un netCDF por año, "
          f"`data/tendencias/chirps_diario/`, URL + SHA-256 + licencia en `data/tendencias/MANIFEST.json`). Comprobación: "
          f"noviembre de 2023 es idéntico a los GeoTIFF oficiales del CHC (diferencia máxima {idn.get('dif_max_mm')} mm en "
          f"{idn.get('celdas_comparadas')} celda-días).")
    coh = state.get("coherencia_diaria") or {}
    if coh:
        A(f"\nCoherencia diaria en las celdas analizadas: lluvia media {f(coh['media_diaria_IMERG_mm'])} mm/día (IMERG) "
          f"frente a {f(coh['media_diaria_CHIRPS_mm'])} (CHIRPS); fracción de días ≥ 1 mm {f(coh['fraccion_dias_humedos_IMERG'], 3)} "
          f"frente a {f(coh['fraccion_dias_humedos_CHIRPS'], 3)}; correlación diaria mediana por celda "
          f"{f(coh['correlacion_diaria_mediana_celdas'], 2)}.")
    A("\n**Dominio.** 442 celdas de 0.1° con ≥ 25 % de su área en RD (y más RD que Haití) para mapas y FDR; las 32 "
      "provincias (geoBoundaries ADM1) y el total nacional como media ponderada por área de los índices de las celdas "
      "(pesos `results/nacional/pesos_provincia_imerg.csv`). Comparación de productos en la **misma rejilla de 0.1°**: "
      "se agrega la lluvia diaria de CHIRPS (2 × 2 sub-celdas, solo tierra) y después se calculan los índices.\n")
    A("## 2 · Índices\n")
    A("Definiciones ETCCDI (Zhang et al. 2011), día húmedo = P ≥ 1 mm. Percentiles 95/99 de los días húmedos 2001-2024 por "
      "celda y producto (no existe 1961-1990 en estos productos). Rachas secas ≥ 10 y ≥ 15 días (definición propia). "
      "Sequía con SPI-3 y SPI-12 (McKee et al. 1993; gamma por mes calendario, estimador de Thom) ajustado sobre 2001-2024: "
      "meses del año con SPI ≤ −1, eventos que empiezan en el año, severidad Σ(−SPI) y duración media (2002-2024).\n")
    A("| id | índice | unidad |\n|---|---|---|")
    for k in ix.DAILY + ix.SPI_KEYS:
        A(f"| {k} | {ix.VARIABLES[k][0]} | {ix.VARIABLES[k][2]} |")
    A("\n**Estaciones** (régimen bimodal del Caribe; Taylor et al. 2002, Gamble y Curtis 2008): seca dic-abr (dic del año "
      "anterior; 2002-2024), lluvias tempranas may-jul (incluye la sequía de medio verano de julio), lluvias tardías ago-nov "
      "(temporada de huracanes). Las rachas no cruzan el borde del bloque.\n")
    A("## 3 · Estadística\n")
    A("- **Magnitud:** pendiente de Theil-Sen por década con IC 95 % de Sen (usando la varianza de S corregida).\n"
      "- **Significancia local:** Mann-Kendall modificado de **Hamed y Rao (1998)** (autocorrelación de los rangos de la "
      "serie sin tendencia, solo lags significativos; el factor no baja de 1), con corrección por empates.\n"
      "- **Multiplicidad:** FDR de Benjamini-Hochberg entre las 442 celdas (o entre las 32 provincias) de cada índice × "
      "periodo × producto. **Significancia de campo** de Wilks (2016): α_FDR = 2·α_global = 0.10; una celda es "
      "'FDR-significativa' si q ≤ 0.10, y el campo es significativo si hay al menos una.\n"
      "- **Calibración con sustitutos** (`earthmemory.calibration`): campos sin tendencia que conservan autocorrelación y "
      "correlación espacial (fases aleatorias multivariadas y bloques circulares de 3 años); se repite la prueba completa y "
      "se mide la tasa empírica de falsos positivos y una p de campo por bootstrap.\n"
      "- **Tendencia mínima detectable (MDT):** pendiente detectable con 80 % de potencia a α = 0.05 por esta misma prueba, "
      "con n años, σ de los residuos y su r1 (factor calibrado por Monte Carlo). Si |pendiente| < MDT y no es "
      "significativa, se informa **'no detectable con 24 años'**, no 'sin cambio'.\n"
      "- **Clase de confianza de dos productos:** *robusta* (IMERG y CHIRPS FDR-significativos, mismo signo), *consistente* "
      "(mismo signo, uno significativo), *en disputa* (signos opuestos, al menos uno significativo), *sin señal detectable*. "
      "El signo es el de Sen; si Sen = 0 (frecuente en conteos) se usa el signo de S.\n")
    # calibración
    A("## 4 · Falsos positivos medidos\n")
    c = cal[cal["nivel"] == "celdas"].copy()
    c["met"] = np.where(c["metodo"].str.startswith("fases"), "fases", "bloques")
    p = cal[cal["nivel"] == "provincias"].copy()
    p["met"] = np.where(p["metodo"].str.startswith("fases"), "fases", "bloques")
    A(f"{int(c['n_sustitutos'].iloc[0])} sustitutos por método, índice anual y producto ({c['indice'].nunique()} índices).\n")
    A("| nivel | método | tasa de p<0.05 (media) | rango entre índices | sin corrección de Hamed-Rao | mapas nulos con ≥1 celda FDR |\n|---|---|---|---|---|---|")
    for lab, d in (("celdas", c), ("provincias", p)):
        for met, g in d.groupby("met"):
            A(f"| {lab} | {met} | {f(g['fpr_local_p05'].mean(), 3)} | {f(g['fpr_local_p05'].min(), 3)}-{f(g['fpr_local_p05'].max(), 3)} "
              f"| {f(g['fpr_local_p05_sin_correccion_hr'].mean(), 3)} | {f(g['fraccion_mapas_nulos_con_celda_fdr'].mean(), 3)} |")
    A("\nLectura: la tasa local debe quedar cerca o por debajo de 0.05; la columna de mapas nulos con al menos una celda FDR es "
      "la tasa de error de campo del criterio de Wilks (debería ser ≲ 0.10). Ver `figures/tendencias/fig4_calibracion_falsos_positivos.png`.\n")
    # resultados
    A("## 5 · Resultados (anual)\n")
    A("Celdas = 442 celdas de 0.1°. *sig* = FDR q ≤ 0.10. Clases: rob = robusta, cons = consistente, disp = en disputa. "
      "Nacional = serie media ponderada por área (Theil-Sen por década, IC 95 %, p de Hamed-Rao, MDT).\n")
    A("| índice | IMERG sig (↑/↓) | CHIRPS sig (↑/↓) | rob (↑/↓) | cons | disp | prov. rob | IMERG nacional /déc [IC95] p · MDT | CHIRPS nacional /déc [IC95] p · MDT |\n|---|---|---|---|---|---|---|---|---|")
    s = summ
    for k in ix.DAILY + ix.SPI_KEYS:
        a = s[(s["indice"] == k) & (s["periodo"] == "anual") & (s["fuente"] == "IMERG")]
        b = s[(s["indice"] == k) & (s["periodo"] == "anual") & (s["fuente"] == "CHIRPS")]
        if a.empty:
            continue
        a = a.iloc[0]
        bb = b.iloc[0] if len(b) else None

        def nat_s(x):
            if x is None:
                return "–"
            return (f"{f(x['nacional_pendiente_decada'])} [{f(x['nacional_ic95_inf'])}, {f(x['nacional_ic95_sup'])}] "
                    f"p={f(x['nacional_p'], 3)} · {f(x['nacional_mdt'])}")
        A(f"| {k} | {a['celdas_sig_fdr']} ({a['celdas_sig_fdr_aumento']}/{a['celdas_sig_fdr_descenso']}) | "
          + (f"{bb['celdas_sig_fdr']} ({bb['celdas_sig_fdr_aumento']}/{bb['celdas_sig_fdr_descenso']})" if bb is not None else "–")
          + f" | {a['celdas_robusta']} ({a['celdas_robusta_aumento']}/{a['celdas_robusta_descenso']}) | {a['celdas_consistente']} | "
          f"{a['celdas_en_disputa']} | {a['provincias_robusta']} | {nat_s(a)} | {nat_s(bb)} |")
    A("\nTabla completa (también estaciones): `results/tendencias/resumen_indices.csv`.\n")
    A("### Por estación (celdas robustas ↑/↓ · en disputa)\n")
    A("| índice | " + " | ".join(ix.PERIODS[p][0] for p in ix.PERIODS) + " |\n|---|" + "---|" * len(ix.PERIODS))
    for k in ix.DAILY:
        cells = []
        for per in ix.PERIODS:
            a = _cls_row(s, k, per)
            cells.append("–" if a is None else f"{a['celdas_robusta_aumento']}/{a['celdas_robusta_descenso']} · {a['celdas_en_disputa']}")
        A(f"| {k} | " + " | ".join(cells) + " |")
    # qué se sostiene
    A("\n## 6 · Qué se sostiene\n")
    holds = s[(s["fuente"] == "IMERG") & (s["celdas_robusta"] > 0)].sort_values("celdas_robusta", ascending=False)
    if holds.empty:
        A("- Ninguna combinación índice × periodo tiene celdas *robustas* (los dos productos significativos y de acuerdo).")
    for _, h in holds.iterrows():
        sig_dir = "aumento" if h["celdas_robusta_aumento"] >= h["celdas_robusta_descenso"] else "descenso"
        A(f"- **{h['indice']} ({ix.PERIODS[h['periodo']][0].lower()})**: {h['celdas_robusta']} celdas robustas "
          f"({h['celdas_robusta_aumento']} en aumento, {h['celdas_robusta_descenso']} en descenso; mayoría: {sig_dir}); "
          f"{h['provincias_robusta']} provincias robustas; {h['celdas_en_disputa']} celdas en disputa.")
    if two:
        disp, solo = disputes_and_single(s)
        A("\n**En disputa: los dos productos ven tendencias significativas en sentidos opuestos** (≥ 20 celdas cada uno):\n")
        A("\n".join(disp) if disp else "- Ninguna.")
        A("\n**Señal de un solo producto (no confirmada por el otro)** (≥ 20 celdas):\n")
        A("\n".join(solo) if solo else "- Ninguna.")
        A("\nUna señal que aparece en un solo producto, o en los dos con signo contrario, puede deberse a cambios en los "
          "productos (sensores, algoritmo, red de estaciones, forma de repartir la lluvia entre días) y **no se presenta como "
          "tendencia del clima**. ⚠ = prueba liberal para ese índice (tasa de falsos positivos medida > 0.075, sección 4).\n")
    A("\n## 7 · Qué NO es detectable con 24 años\n")
    nd = nat[(nat["periodo"] == "anual") & (nat["fuente"] == "IMERG")]
    rows = []
    for _, t in nd.iterrows():
        if not (t["p"] < 0.05) and np.isfinite(t["mdt"]) and t["media"] != 0:
            rows.append((t["indice"], 100 * t["mdt"] / abs(t["media"]), t["mdt"], ix.VARIABLES[t["indice"]][2]))
    if rows:
        A("Serie nacional IMERG, sin tendencia significativa; cambio que haría falta para detectarla con 80 % de potencia:\n")
        A("| índice | MDT por década | % de la media por década |\n|---|---|---|")
        for k, pct, m, u in rows:
            A(f"| {k} | {f(m)} {u} | {f(pct, 0)} % |")
    A("\nEn celdas, la MDT mediana es mayor que en la serie nacional (más ruido): ver `mediana_mdt` en `resumen_indices.csv`. "
      "Para la cola extrema (Rx1day, R99pTOT, R50mm) los cambios detectables con 24 años son de decenas de por ciento por "
      "década: una tendencia moderada real pasaría desapercibida. **'Sin señal detectable' ≠ 'sin cambio'.**\n")
    A("## 8 · Límites\n")
    A("- **24 años** es corto para tendencias de extremos: la variabilidad interdecenal (ENOS, AMO) puede producir o tapar "
      "tendencias en esta ventana. Los resultados describen 2001-2024, no se extrapolan.\n"
      "- **IMERG no es homogéneo en el tiempo**: su constelación de microondas pasivas y sus sensores de entrada cambian "
      "(p. ej. TRMM → GPM en 2014); tendencias en la frecuencia de días húmedos o en la intensidad pueden ser en parte "
      "artefactos de detección. Por eso se exige el acuerdo con CHIRPS.\n"
      "- **CHIRPS diario no es independiente día a día**: el total de la péntada (anclado a estaciones) se reparte entre "
      "días con un campo de lluvia diaria de modelo/satélite; los índices diarios de CHIRPS (Rx1day, CDD, R1mm) heredan esa "
      "distribución. Tampoco es independiente de la red de estaciones, cuya densidad en RD cambia con el tiempo. Los dos "
      "productos usan infrarrojo geoestacionario y pluviómetros (GPCC en IMERG): **no son testigos totalmente independientes**.\n"
      "- **SPI** ajustado sobre los mismos 24 años: un 'mes en sequía' es relativo a 2001-2024; con 24 valores por mes "
      "calendario la cola de la gamma es frágil.\n"
      "- La rejilla de 0.1° (~11 km) promedia la lluvia convectiva: los extremos locales (estación) son mayores que los de "
      "la celda.\n"
      "- El día de IMERG es 00-24 UTC (20:00-20:00 hora local); el de CHIRPS no es exactamente el mismo: discrepancias de "
      "un día afectan a Rx1day pero poco a Rx5day.\n"
      "- Pruebas múltiples: FDR controla la proporción de falsos descubrimientos entre celdas, pero índices y estaciones no "
      "se corrigen entre sí (hay 56 combinaciones por producto); léanse como familias separadas.\n"
      "- Asociación temporal, **no causalidad**.\n")
    A("## 9 · Archivos\n")
    A("- `results/tendencias/tendencias_celdas.csv`, `tendencias_provincias.csv` (columnas `fuente`, `tipo_fuente`, "
      "`pendiente_decada`, `ic95_inf`, `ic95_sup`, `p`, `q_fdr`, `clase_confianza`, `mdt`, …), `series_provincias.csv`, "
      "`resumen_indices.csv`, `calibracion_fpr.csv`, `por_indice/*.csv`, `corrida.json`.\n"
      "- `results/tendencias/web/` (JSON para las pantallas; esquema en `CONTRATO.md`).\n"
      "- `figures/tendencias/` (PNG 220 ppp + PDF).\n"
      "- `notebooks/06_tendencias_sequia_y_extremos.ipynb` y `reports_nacional/notebooks_html/06_tendencias_sequia_y_extremos.html`.\n")
    A("## 10 · Reproducir\n")
    A("```\ndocker compose run --rm tendencias                       # descarga lo que falte, calcula, figuras, web, informe, cuaderno\n"
      "docker compose run --rm --entrypoint \"uv run --frozen --no-sync pytest -q tests/test_tendencias.py\" tendencias\n```\n")
    A("## Referencias\n")
    A("- Benjamini, Y., Hochberg, Y. (1995). Controlling the false discovery rate. *J. R. Stat. Soc. B* 57, 289-300.\n"
      "- Edwards, D.C., McKee, T.B. (1997). Characteristics of 20th century drought in the United States at multiple time "
      "scales. Climatology Report 97-2, Colorado State University.\n"
      "- Funk, C. et al. (2015). The climate hazards infrared precipitation with stations — a new environmental record for "
      "monitoring extremes. *Scientific Data* 2, 150066. doi:10.1038/sdata.2015.66\n"
      "- Gamble, D.W., Curtis, S. (2008). Caribbean precipitation: review, model and prospect. *Progress in Physical "
      "Geography* 32, 265-276.\n"
      "- Hamed, K.H., Rao, A.R. (1998). A modified Mann-Kendall trend test for autocorrelated data. *J. Hydrology* 204, 182-196.\n"
      "- Huffman, G.J. et al. (2023). GPM IMERG Final Precipitation L3 1 day 0.1° V07. GES DISC. doi:10.5067/GPM/IMERGDF/DAY/07\n"
      "- Karl, T.R., Nicholls, N., Ghazi, A. (1999). CLIVAR/GCOS/WMO workshop on indices and indicators for climate "
      "extremes. *Climatic Change* 42, 3-7.\n"
      "- Livezey, R.E., Chen, W.Y. (1983). Statistical field significance and its determination by Monte Carlo techniques. "
      "*Mon. Wea. Rev.* 111, 46-59.\n"
      "- McKee, T.B., Doesken, N.J., Kleist, J. (1993). The relationship of drought frequency and duration to time scales. "
      "8th Conf. Applied Climatology, AMS, 179-184.\n"
      "- Prichard, D., Theiler, J. (1994). Generating surrogate data for time series with several simultaneously measured "
      "variables. *Phys. Rev. Lett.* 73, 951-954.\n"
      "- Sen, P.K. (1968). Estimates of the regression coefficient based on Kendall's tau. *JASA* 63, 1379-1389.\n"
      "- Taylor, M.A., Enfield, D.B., Chen, A.A. (2002). Influence of the tropical Atlantic versus the tropical Pacific on "
      "Caribbean rainfall. *J. Geophys. Res.* 107(C9), 3127.\n"
      "- Thom, H.C.S. (1958). A note on the gamma distribution. *Mon. Wea. Rev.* 86, 117-122.\n"
      "- Wilks, D.S. (2016). \"The stippling shows statistically significant grid points\": how research results are "
      "routinely overstated and overinterpreted, and what to do about it. *BAMS* 97, 2263-2273.\n"
      "- Zhang, X. et al. (2011). Indices for monitoring changes in extremes based on daily temperature and precipitation "
      "data. *WIREs Climate Change* 2, 851-870. doi:10.1002/wcc.147\n")
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")
    print(f"[informe] {REPORT}", flush=True)
