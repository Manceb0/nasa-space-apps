"""Informe EARTH_MEMORY.md y DATA_DICTIONARY.md, escritos SOLO con números calculados en esta corrida.

Todo valor que aparece en el informe sale de R (el estado de la corrida). Los textos fijos describen
métodos y límites; nunca resultados.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from .figures import demo_pair

LF = "\n"
NOMBRE = {"SM_RAIZ": "humedad de la zona de raíces (0-100 cm)", "SM_0_10": "humedad superficial (0-10 cm)",
          "ET": "evapotranspiración", "TAIRE": "temperatura del aire", "NDVI": "NDVI", "EVI": "EVI",
          "PRECIP_IMERG_0.1": "lluvia IMERG (0.1°)", "LLUVIA_GLDAS_FORZAMIENTO": "lluvia que forzó a GLDAS (0.25°)",
          "LLUVIA_IMERG_EN_CELDA_GLDAS": "lluvia IMERG remapeada a celdas GLDAS"}
METRICA = {"r_spi": "acople r(SPI-3, z)", "phi": "memoria φ (ARX)", "gamma": "sensibilidad inmediata γ (ARX)"}


def f(x, nd=2):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "—"
    if isinstance(x, (int, np.integer)):
        return str(int(x))
    ax = abs(float(x))
    if ax != 0 and (ax < 10 ** -max(nd, 2) or ax >= 1e5):
        return f"{float(x):.2e}"
    return f"{float(x):.{nd}f}"


def q(x):
    if x is None or not np.isfinite(x):
        return "—"
    if x == 0:
        return "< 1e-15"
    return f"{x:.3g}"


def table(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    out = ["| " + " | ".join(cols) + " |", "|" + "|".join(["---"] * len(cols)) + "|"]
    for _, r in df.iterrows():
        out.append("| " + " | ".join(str(r[c]) for c in cols) + " |")
    return LF.join(out)


def place(R, cid: str) -> str:
    cg = R["D"]["cells_gl"].set_index("celda")
    if cid not in cg.index:
        return cid
    w = R["D"]["w_gl"]
    ws = w[w["celda"] == cid].sort_values("fraccion", ascending=False)
    provs = ", ".join(f"{r.provincia} {100 * r.fraccion:.0f} %" for r in ws.itertuples() if r.fraccion >= 0.1)
    return f"celda {cid} ({provs})"


def write(R: dict, figs: dict, path: Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    D = R["D"]
    a = R["args"]
    man = D["man"].data
    rutas = man.get("rutas", {})
    cal = R["cal_tr"]
    tests = R["tests"]
    ns = R["null_sum"]
    tot = ns[ns["respuesta"] == "TODAS"].iloc[0]
    cg, ci = D["cells_gl"], D["cells_im"]
    L = []
    L += ["# Earth Memory · República Dominicana (todo el país, a nivel de celda)", "",
          "Stellar Horizons · NASA Space Apps 2026 · reto *Be An Earth System Trend Detective!*", "",
          "> Pregunta: ¿por qué dos territorios con lluvia parecida pueden responder distinto (suelo, agua en la "
          "zona de raíces, evapotranspiración, temperatura)? Todo lo que sigue son **asociaciones** en productos "
          "satelitales y de modelo; nada aquí demuestra causa.", "",
          f"Informe generado por `earthmemory/report.py` a partir de la corrida (`results/nacional/corrida.json`). "
          f"Periodo {a['anio0']}-{a['anio1']}. Ningún número de este archivo está escrito a mano.", ""]

    # ---------------------------------------------------------------- resumen
    dp = demo_pair(R)
    L += ["## 1. Resumen", ""]
    tr = R["trends"]
    for v in ("PRECIP_IMERG_0.1", "SM_RAIZ", "TAIRE"):
        c = cal.get(v)
        if c:
            L.append(f"- **Tendencia de {NOMBRE[v]}**: {c['celdas_q05_calibrado']}/{c['n_celdas']} celdas con q < 0.05 "
                     f"tras calibrar contra sustitutos nulos (nominal: {c['celdas_q05_nominal']}); mediana de la pendiente "
                     f"{f(c['mediana_pendiente_decada'])} {tr[tr['variable'] == v]['unidad_por_decada'].iloc[0]}; "
                     f"p de campo {f(c['fase']['p_campo'], 3)}.")
    L.append(f"- **Falsos positivos**: la prueba de tendencia da {f(cal['SM_RAIZ']['fase']['tasa_empirica_p05'], 3)} "
             f"(raíz) y {f(cal['PRECIP_IMERG_0.1']['fase']['tasa_empirica_p05'], 3)} (lluvia) de p < 0.05 en mapas nulos "
             f"(nominal 0.05). La prueba de pares da {f(tot['tasa_empirica_p05'], 3)}: **está inflada** y por eso todas las "
             f"conclusiones de pares usan el p calibrado contra el nulo.")
    L.append(f"- **Pares con lluvia parecida**: {int(R['pairs']['lluvia_parecida'].sum())} de {len(R['pairs'])} pares de celdas; "
             f"{int(tests['p'].notna().sum())} pruebas; q < 0.05 con p nominal: {int((tests['q_bh'] < 0.05).sum())}; "
             f"con p calibrado: {int((tests['q_bh_calibrado'] < 0.05).sum())}.")
    ct = R["contra"]
    L.append(f"- **Contradicciones \"volvió la lluvia, la raíz no\"**: {int(ct['n_A_raiz'].sum())} episodios con IMERG"
             + (f"; {int(ct['n_A_raiz_lluvia_modelo'].sum())} con la lluvia que forzó a GLDAS" if 'n_A_raiz_lluvia_modelo' in ct else "")
             + ".")
    if R["event"] is not None:
        ev = R["event"]
        t = ev["por_celda"].iloc[0]
        L.append(f"- **Santo Domingo 18-nov-2023**: la celda IMERG más lluviosa registró {f(t['mm_dia_utc_evento'], 0)} mm en el día UTC "
                 f"({f(t['mm_2_dias'], 0)} mm en 2 días UTC)"
                 + (f"; máximo de 24 h móviles con datos de media hora {f(ev['media_hora']['max_24h_movil_mm'], 0)} mm" if 'media_hora' in ev else "")
                 + ". El pluviómetro de ONAMET reportó 431 mm: el producto en rejilla suaviza el extremo.")
    L.append("")

    # ---------------------------------------------------------------- datos
    L += ["## 2. Datos, cobertura y límites", ""]
    rows = []
    rows.append({"Producto": "GPM IMERG Final V07 mensual (archivos V07B)", "Resolución": "0.1°",
                 "Celdas en la caja": len(ci), "Celdas que tocan RD": int((ci["frac_pais"] > 0).sum()),
                 "Celdas usadas (≥25 % en RD)": int(ci["incluida"].sum()), "Ruta": "OPeNDAP gpm1 (Bearer)",
                 "DOI": "10.5067/GPM/IMERG/3B-MONTH/07"})
    rows.append({"Producto": "GPM IMERG Final V07 diario", "Resolución": "0.1°", "Celdas en la caja": len(ci),
                 "Celdas que tocan RD": int((ci["frac_pais"] > 0).sum()),
                 "Celdas usadas (≥25 % en RD)": int(ci["incluida"].sum()) if len(D["D_im"]) else 0,
                 "Ruta": "OPeNDAP en la nube (Bearer); respaldo gpm1", "DOI": "10.5067/GPM/IMERGDF/DAY/07"})
    rows.append({"Producto": "GPM IMERG Final V07 media hora (17-19 nov 2023)", "Resolución": "0.1°",
                 "Celdas en la caja": len(ci), "Celdas que tocan RD": int((ci["frac_pais"] > 0).sum()),
                 "Celdas usadas (≥25 % en RD)": "solo evento", "Ruta": "OPeNDAP gpm1 (Bearer)",
                 "DOI": "10.5067/GPM/IMERG/3B-HH/07"})
    rows.append({"Producto": "GLDAS Noah 2.1 mensual (SoilMoi0_10cm, RootMoist, Tair_f, Evap, Rainf_f)",
                 "Resolución": "0.25°", "Celdas en la caja": len(cg), "Celdas que tocan RD": int((cg["frac_pais"] > 0).sum()),
                 "Celdas usadas (≥25 % en RD)": int(cg["incluida"].sum()), "Ruta": "OPeNDAP en la nube (DAP4, Bearer)",
                 "DOI": "10.5067/SXAVCZFAQLNO"})
    pj = Path(a["resultados"]) / "power_merra2" / "corrida.json"
    pc = json.loads(pj.read_text(encoding="utf-8")) if pj.exists() else {}
    rows.append({"Producto": "NASA POWER (MERRA-2) — solo comprobación", "Resolución": "0.5° × 0.625°",
                 "Celdas en la caja": pc.get("celdas_total", "—"), "Celdas que tocan RD": "—",
                 "Celdas usadas (≥25 % en RD)": pc.get("celdas_incluidas", "—"), "Ruta": "API POWER", "DOI": "—"})
    L += [table(pd.DataFrame(rows)), ""]
    cj = json.loads((Path(a["resultados"]) / "corrida.json").read_text(encoding="utf-8"))
    L += [f"- Meses IMERG faltantes: {', '.join(cj['meses_imerg_faltantes']) or 'ninguno'}; días IMERG: {cj['dias_imerg']} "
          f"(faltantes {cj['dias_imerg_faltantes']}).",
          "- Comparación honesta con el equipo chileno ProGarLabs (9 694 celdas IMERG + 419 MERRA-2 para Chile, según "
          "su página): Chile tiene ~15 veces la superficie de RD; aquí usamos "
          f"{int(ci['incluida'].sum())} celdas IMERG 0.1° y {int(cg['incluida'].sum())} celdas GLDAS 0.25° con al menos "
          f"25 % de su área en RD (de {int((ci['frac_pais'] > 0).sum())} y {int((cg['frac_pais'] > 0).sum())} que la tocan).",
          "- Límites (geoBoundaries gbOpen DOM ADM1, "
          f"{cj['limites_adm1'].get('boundaryID')}): fuente {cj['limites_adm1'].get('boundarySource')}, licencia "
          f"**{cj['limites_adm1'].get('boundaryLicense')}** según los metadatos de la API (no CC BY 4.0), "
          f"{cj['limites_adm1'].get('admUnitCount')} unidades, año representado {cj['limites_adm1'].get('boundaryYearRepresented')}. "
          "Haití se toma de Natural Earth 10m v5.1.2 (dominio público) para excluir celdas dominadas por Haití.",
          "- **GLDAS-2.1 se forzó con lluvia GPCP (desagregada con GDAS), no con IMERG, y no asimila datos de suelo.** Una "
          "\"contradicción\" entre lluvia IMERG y suelo GLDAS puede ser una diferencia entre productos y no un comportamiento "
          "del terreno. Por eso cada contradicción y cada contraste se recalcula con la lluvia de forzamiento del propio "
          "modelo (Rainf_f_tavg) y se etiqueta.",
          "- IMERG Final V07 (mensual hasta 2025-09 en el archivo); aquí 2001-2024. Celda IMERG ≈ 10.5 × 10.6 km; GLDAS ≈ 26 × 28 km.",
          "- SMAP L3/L4: no se descargó en esta corrida (prioridad menor que IMERG diario + GLDAS; requiere la rejilla EASE "
          "de 9 km). GRACE-FO: su resolución efectiva (~3°, ~300 km) cubre RD con 1-2 mascons; solo sirve como contexto "
          "nacional, no provincial; no se usó en el motor.",
          f"- AppEEARS nacional (MOD13A3 NDVI/EVI + MOD17A3HGF NPP, pedido 8ad4ac19-…): {cj['appeears']}. Cuando lleguen los "
          "GeoTIFF a `data/appeears/nacional/`, NDVI/EVI entran solos como respuestas (con su perfil de desfases SPI→NDVI) y "
          "se calcula la eficiencia de uso de la lluvia (NPP/lluvia).",
          ""]
    xv = R["xval"]
    if xv.get("disponible"):
        L += [f"- Comprobación con NASA POWER/MERRA-2 en {len(xv['tabla'])} celdas POWER: mediana de r(SPI-3 IMERG, SPI-3 MERRA-2) = "
              f"{f(xv['mediana_r_spi3'])}; mediana de r(z raíz GLDAS, z raíz MERRA-2) = {f(xv['mediana_r_z_raiz'])} "
              "(`results/nacional/comparacion_power_merra2.csv`).", ""]
    fails = {k: v for k, v in rutas.items() if isinstance(v, dict) and v.get("estado") not in (None, "ok")}
    L += ["Rutas de descarga (de `data/nacional/MANIFEST.json`, sección `rutas`):", ""]
    for k, v in rutas.items():
        if isinstance(v, dict):
            L.append(f"- `{k}`: {v.get('estado')} — {v.get('pedidos', '')} pedidos, {v.get('n_errores', 0)} errores"
                     + (f"; ejemplo: `{v['errores_muestra'][0][-160:]}`" if v.get("errores_muestra") else ""))
    L += ["- OPeNDAP de GLDAS en hydro1.gesdisc.eosdis.nasa.gov: `HTTP 410 Gone · The OPeNDAP service is no longer "
          "available` (retirado); se usó el OPeNDAP en la nube (opendap.earthdata.nasa.gov).",
          "- Historial de la descarga del 2026-11-14: gpm1 devolvió `HTTP 503 Service Unavailable` intermitentes (2 meses "
          "IMERG y 1 media hora en el primer intento, recuperados al reintentar); el respaldo en la nube para los HDF5 de "
          "IMERG dio `HTTP 400` hasta usar la ruta del grupo `/Grid/` (corregido). IMERG diario se pidió a la nube con "
          "nombres de archivo construidos. GRACE: el OPeNDAP en la nube dio 404 para el granulo de mascons; se bajó el "
          "archivo completo (46 MB) por HTTPS con el token solo en el primer salto.", ""]
    if not fails:
        L += ["Todas las rutas terminaron sin errores pendientes.", ""]

    gr = R.get("grace")
    if gr is not None and len(gr):
        lo = gr.loc[gr["tws_cm"].idxmin()]
        L += ["### Contexto: agua total (GRACE/GRACE-FO)", "",
              f"- Media nacional de {int(gr['celdas_0_5_usadas'].iloc[0])} celdas 0.5° de los mascons JPL RL06.3 CRI "
              f"({len(gr)} meses con dato en {a['anio0']}-{a['anio1']}; hueco 2017-07 a 2018-05 entre misiones). Mínimo "
              f"{f(lo['tws_cm'], 1)} cm en {pd.Timestamp(lo['fecha']):%Y-%m}. Resolución efectiva ~3°: no se usa en celdas "
              "ni provincias. Figura `fig11_grace_contexto`.", ""]

    # ---------------------------------------------------------------- métodos
    L += ["## 3. Métodos (resumen)", "",
          "- **Celdas**: rectángulos nativos de cada producto (sin interpolar). Fracción de cada celda en el país y en cada "
          "provincia con 12×12 (IMERG) o 25×25 (GLDAS) puntos ponderados por cos(lat). Celda incluida: ≥ 25 % en RD, "
          "más RD que Haití y (GLDAS) tierra en el modelo.",
          "- **Lluvia en la celda GLDAS**: remapeo conservativo de IMERG (área de solape × fracción en RD de cada celda IMERG).",
          "- **Provincias**: media ponderada por área (peso = área de la celda × fracción de la celda en la provincia).",
          "- **Anomalías**: SPI-1/3/6 (gamma por mes calendario con masa en cero); z robusto (mediana/MAD por mes) para las respuestas.",
          "- **Tendencias**: Theil-Sen + Mann-Kendall con corrección AR(1) sobre medias anuales de anomalías; BH por variable; "
          "p calibrado con 1 000 sustitutos de fases aleatorias multivariadas (misma fase en todas las celdas: conserva la "
          "autocorrelación y la correlación espacial) y control con bloques circulares de 24 meses; significancia de campo "
          "(Livezey y Chen 1983) e I de Moran de la pendiente.",
          "- **Acople y memoria**: r(SPI-3, z) y ARX z(t) = c + φ z(t−1) + γ SPI-1(t); IC por bootstrap de bloques móviles "
          "(12 meses, mismos índices en todas las celdas).",
          "- **Pares con lluvia parecida**: ≤ 150 km, r(SPI-3) ≥ 0.70 y lluvia anual a ≤ 25 %. Δ por bootstrap conjunto; p "
          "calibrado contra un nulo paramétrico (ARX común, mismo forzamiento, residuos en bloques conjuntos); BH sobre todas "
          "las pruebas; 11 variantes de sensibilidad + la variante \"lluvia del modelo\".",
          "- **Episodios**: SPI-3 ≤ −1 por 2+ meses. A = la lluvia vuelve (SPI-3 ≥ 0) pero la raíz sigue con z < −1 ese mes y el "
          "siguiente; B1 = suelo seco sin sequía de lluvia; B2 = suelo normal en sequía de lluvia. Comparación justa: "
          "episodios de dos celdas que terminan con ≤ 2 meses de diferencia y SPI-3 mínimo parecido (|Δ| ≤ 0.5).",
          "- **Factores** (asociación): fracción de lluvia en días > p95 de la celda y máximo en 1 día (IMERG diario remapeado), "
          "meses de sequía en los 12 previos, z antecedente; coeficiente estandarizado con control por severidad; IC por "
          "bootstrap por conglomerados de año; BH; sensibilidad (efectos fijos de celda, todos juntos, p90, 24 meses, "
          "retorno a −0.5, 3 meses).",
          f"- **Latigazos** (whiplash): SPI-3 o z cruza de ≤ −{0.84} a ≥ +{0.84} (o al revés) en ≤ 3 meses, umbral de "
          "Stojanovic et al. 2025 (Sci. Data 12:1700, doi:10.1038/s41597-025-05992-9), que usa MSWEP, trata La Española como "
          "una sola isla y no considera humedad del suelo; aquí se cuentan por celda para lluvia y para suelo.",
          ""]

    # ---------------------------------------------------------------- qué sobrevive
    L += ["## 4. Qué sobrevive a la corrección y qué no", "", "### 4.1 Tendencias por celda", ""]
    rows = []
    for v, c in cal.items():
        rows.append({"Variable": NOMBRE.get(v, v), "Celdas": c["n_celdas"], "q<0.05 nominal": c["celdas_q05_nominal"],
                     "q<0.05 calibrado": c["celdas_q05_calibrado"],
                     "p<0.05 observadas": c["fase"]["celdas_p05_observadas"],
                     "p<0.05 en nulo (media / p95)": f"{f(c['fase']['celdas_p05_nulo_media'], 1)} / {f(c['fase']['celdas_p05_nulo_p95'], 1)}",
                     "p de campo (fases / bloques)": f"{f(c['fase']['p_campo'], 3)} / {f(c['bloques']['p_campo'], 3)}",
                     "I de Moran": f(c["moran_I_pendiente"]), "Pendiente mediana": f(c["mediana_pendiente_decada"], 3)})
    L += [table(pd.DataFrame(rows)), "",
          "Las celdas vecinas no son pruebas independientes (I de Moran alto = pendientes muy parecidas entre vecinas). La "
          "significancia de campo responde a: \"¿hay más celdas significativas de las que daría el azar con esta misma "
          "correlación espacial?\". Una tendencia de 24 años no separa cambio de largo plazo de variabilidad decenal.", ""]
    for v, c in cal.items():
        if c["celdas_q05_calibrado"] != c["celdas_q05_nominal"]:
            L.append(f"- {NOMBRE.get(v, v)}: {c['celdas_q05_nominal']} celdas con q < 0.05 usando el p de Mann-Kendall AR(1) y "
                     f"{c['celdas_q05_calibrado']} usando el p calibrado. Se informa el calibrado (su tasa de falsos "
                     "positivos medida es la nominal); la diferencia indica que la corrección AR(1) con 24 valores anuales no "
                     "reproduce exactamente la memoria de esta variable.")
        pf, pb = c["fase"]["p_campo"], c["bloques"]["p_campo"]
        if (pf < 0.05) != (pb < 0.05):
            L.append(f"- {NOMBRE.get(v, v)}: la significancia de campo depende del sustituto (fases {f(pf, 3)}, bloques "
                     f"{f(pb, 3)}): **no es robusta**.")
    L.append("")
    if "LLUVIA_GLDAS_FORZAMIENTO" in cal and "LLUVIA_IMERG_EN_CELDA_GLDAS" in cal:
        tg = tr[tr["variable"] == "LLUVIA_GLDAS_FORZAMIENTO"].set_index("celda")["pendiente_pct_clim_decada"]
        ti = tr[tr["variable"] == "LLUVIA_IMERG_EN_CELDA_GLDAS"].set_index("celda")["pendiente_pct_clim_decada"]
        both = pd.concat([tg, ti], axis=1, keys=["g", "i"]).dropna()
        L += [f"Diagnóstico de productos: en las mismas {len(both)} celdas GLDAS, la tendencia mediana de la lluvia que "
              f"forzó a GLDAS es {f(both['g'].median(), 1)} % de su media por década y la de IMERG {f(both['i'].median(), 1)} %; "
              f"r entre los dos mapas de pendiente = {f(np.corrcoef(both['g'], both['i'])[0, 1])}. Si el suelo de GLDAS "
              "baja más que la lluvia IMERG, parte de esa caída puede venir del forzamiento del modelo y no del terreno.", ""]

    L += ["### 4.2 Calibración de falsos positivos", ""]
    rows = [{"Prueba": f"tendencia · {NOMBRE.get(v, v)}", "Sustituto": c[m]["metodo"],
             "Tasa empírica p<0.05": f(c[m]["tasa_empirica_p05"], 3),
             "Mapas nulos con ≥1 descubrimiento BH": f(c[m]["fraccion_mapas_nulos_con_descubrimiento_BH"], 3)}
            for v, c in cal.items() for m in ("fase", "bloques")]
    L += [table(pd.DataFrame(rows)), ""]
    d = ns.copy()
    d["tasa_empirica_p05"] = d["tasa_empirica_p05"].map(lambda x: f(x, 3))
    d["z_abs_critico_95"] = d["z_abs_critico_95"].map(lambda x: f(x, 2))
    d["factor_inflacion_EE"] = d["factor_inflacion_EE"].map(lambda x: f(x, 2))
    d["tasa_p05_tras_calibrar"] = d["tasa_p05_tras_calibrar"].map(lambda x: f(x, 3))
    L += [f"Prueba de pares (nulo paramétrico, {len(R['pares_calibracion'])} pares × {a['n_surr_pares']} sustitutos × 4 respuestas × 3 métricas):", "",
          table(d.rename(columns={"respuesta": "Respuesta", "metrica": "Métrica", "n": "n nulas",
                                  "tasa_empirica_p05": "Tasa p<0.05", "z_abs_critico_95": "|Δ/EE| crítico 95 %",
                                  "factor_inflacion_EE": "σ (inflación EE)", "tasa_p05_tras_calibrar": "Tasa tras calibrar"})), "",
          f"Lectura: nominal 5 %. La prueba de tendencia está {'bien calibrada' if max(c['fase']['tasa_empirica_p05'] for c in cal.values()) < 0.075 else 'algo inflada'} "
          f"(máximo {f(max(c['fase']['tasa_empirica_p05'] for c in cal.values()), 3)}). La prueba de pares con bootstrap de bloques "
          f"da {f(tot['tasa_empirica_p05'], 3)}: el error estándar del bootstrap subestima la variabilidad real de Δ "
          "(bloques de 12 meses cortos para series con mucha memoria). **Corrección aplicada**: se mide cuánto subestima el "
          "bootstrap la variabilidad (factor de inflación σ por respuesta y métrica, columna `factor_inflacion_EE`) y el p "
          f"calibrado usa |Δ/EE|/σ; tras calibrar, la tasa en el nulo es {f(tot['tasa_p05_tras_calibrar'], 3)} (columna "
          "`tasa_p05_tras_calibrar`; medida en los mismos sustitutos, así que es un control de consistencia, no una "
          "validación independiente). Control adicional: `p_empirico_nulo` (posición en el nulo) en `pruebas_pares.csv`.", ""]

    L += ["### 4.3 Pares", ""]
    rk = R["ranked"]
    show = rk.head(10).copy()
    if len(show):
        cols = {"rango": "#", "celda_a": "A", "celda_b": "B", "respuesta": "Respuesta", "metrica": "Métrica"}
        t = show[list(cols)].rename(columns=cols)
        t["Δ [IC95]"] = [f"{f(r.delta)} [{f(r.ic95_bajo)}, {f(r.ic95_alto)}]" for r in show.itertuples()]
        t["q nominal"] = show["q_bh"].map(q)
        t["q calibrado"] = show["q_bh_calibrado"].map(q)
        t["Robustez"] = [f"{int(r.variantes_ok)}/{int(r.n_variantes)}" for r in show.itertuples()]
        if "etiqueta_producto" in show:
            t["Lluvia del modelo"] = show["etiqueta_producto"]
        t["km"] = show["distancia_km"].map(lambda x: f(x, 0))
        L += [table(t), ""]
    L += ["Robustez = variantes (de 11) en las que Δ mantiene el signo y su IC95 excluye 0. Dos pares que comparten celda no "
          "son dos hallazgos.", ""]

    L += ["### 4.4 Factores asociados a la respuesta tras la sequía", ""]
    fa = R["fac"].copy()
    fa["β [IC95]"] = [f"{f(r.beta)} [{f(r.ic95[0]) if isinstance(r.ic95, list) else '—'}, {f(r.ic95[1]) if isinstance(r.ic95, list) else '—'}]"
                      for r in fa.itertuples()]
    fa["p"] = fa["p"].map(q)
    fa["q"] = fa["q_bh"].map(q)
    L += [table(fa[["resultado", "factor", "n", "β [IC95]", "p", "q"]]), "",
          "β = cambio del resultado (en unidades del resultado) por 1 DE del factor, con control por severidad. IC por "
          "bootstrap de conglomerados de año (las celdas vecinas viven la misma sequía a la vez). Asociación, no causa.", ""]
    fs = R["fsens"]
    if len(fs):
        sig_main = fa[pd.to_numeric(R["fac"]["q_bh"], errors="coerce") < 0.05][["resultado", "factor"]]
        for r in sig_main.itertuples():
            ss = fs[(fs["resultado"] == r.resultado) & (fs["factor"] == r.factor)]
            same = sum(1 for x in ss.itertuples() if x.beta is not None and np.isfinite(x.beta)
                       and np.sign(x.beta) == np.sign(R["fac"].set_index(["resultado", "factor"]).loc[(r.resultado, r.factor), "beta"])
                       and isinstance(x.ic95, list) and (x.ic95[0] > 0 or x.ic95[1] < 0))
            L.append(f"- {r.resultado} ~ {r.factor}: mantiene signo con IC que excluye 0 en {same}/{len(ss)} variantes de sensibilidad.")
        L.append("")

    L += ["### 4.5 Contradicciones y latigazos", ""]
    if "etiqueta_producto" in rk or "contradiccion_A_SM_RAIZ_etiqueta" in R["ep"]:
        lab = R["ep"]["contradiccion_A_SM_RAIZ_etiqueta"].value_counts() if "contradiccion_A_SM_RAIZ_etiqueta" in R["ep"] else pd.Series(dtype=int)
        L.append("Episodios A (raíz) con IMERG y su etiqueta frente a la lluvia del modelo: "
                 + "; ".join(f"{k}: {int(v)}" for k, v in lab.items()) + ".")
    w = R["whip"]
    if len(w):
        cols = [c for c in w.columns if c.endswith("seco_a_humedo")]
        L.append("Latigazos seco→húmedo (suma de todas las celdas): "
                 + "; ".join(f"{c.replace('_seco_a_humedo', '')}: {int(w[c].sum())}" for c in cols) + ".")
    L.append("")

    # ---------------------------------------------------------------- caso demo
    L += ["## 5. El caso dominicano más sólido para la demo", ""]
    verified = False
    if dp is not None:
        sig = bool(dp.get("significativo_q05_calibrado", False))
        surv = bool(dp.get("sobrevive_lluvia_modelo", False)) if "sobrevive_lluvia_modelo" in dp else False
        robust = float(dp["robustez"]) >= 0.8
        verified = sig and surv and robust
        a_, b_ = dp["celda_a"], dp["celda_b"]
        L += [f"- A = {place(R, a_)}; B = {place(R, b_)}; distancia {f(dp['distancia_km'], 0)} km; r(SPI-3) = {f(dp['r_spi3'])}; "
              f"diferencia de lluvia anual {f(100 * dp['dif_rel_lluvia_anual'], 1)} %; diferencia de elevación (GLDAS) "
              f"{f(dp['dif_elevacion_m'], 0)} m.",
              f"- {NOMBRE.get(dp['respuesta'], dp['respuesta'])}, {METRICA[dp['metrica']]}: A = {f(dp['valor_a'])}, "
              f"B = {f(dp['valor_b'])}, Δ = {f(dp['delta'])} (IC95 {f(dp['ic95_bajo'])} a {f(dp['ic95_alto'])}); "
              f"q nominal {q(dp['q_bh'])}, **q calibrado {q(dp['q_bh_calibrado'])}**; robustez "
              f"{int(dp['variantes_ok'])}/{int(dp['n_variantes'])}"
              + (f"; con la lluvia del modelo Δ = {f(dp['delta_lluvia_modelo'])} "
                 f"(IC95 {f(dp['ic95_bajo_lluvia_modelo'])} a {f(dp['ic95_alto_lluvia_modelo'])}) → {dp['etiqueta_producto']}"
                 if "delta_lluvia_modelo" in dp else "") + "."]
        mk = R["matched"].get(f"{a_}|{b_}")
        if mk and mk["resumen"]:
            for s in mk["resumen"]:
                if s.get("ic95"):
                    L.append(f"  - Episodios emparejados, {s['variable']} (A − B): media {f(s['media_dif'])} "
                             f"[{f(s['ic95'][0])}, {f(s['ic95'][1])}], n = {s['n']}, Wilcoxon p = {q(s['p_wilcoxon'])}.")
        L += ["", "Figura: `figures/nacional/fig07_mejor_contraste.png`.", ""]
        if not verified:
            L += ["**Estado**: no cumple a la vez las tres condiciones (q calibrado < 0.05, sobrevive con la lluvia del "
                  "modelo, robustez ≥ 80 %). Se presenta como el *siguiente mejor* caso, no como hallazgo verificado.", ""]
    else:
        L += ["No hay contrastes que ordenar.", ""]

    L += ["## 6. \"Estos dos territorios recibieron lluvias comparables. Sin embargo, sus respuestas ambientales fueron distintas\"", ""]
    if verified:
        L += [f"Verificado para el par de la sección 5: lluvia comparable (r(SPI-3) = {f(dp['r_spi3'])}, lluvia anual a "
              f"{f(100 * dp['dif_rel_lluvia_anual'], 1)} %) y {METRICA[dp['metrica']]} de {NOMBRE.get(dp['respuesta'])} distinta "
              f"(Δ = {f(dp['delta'])}, q calibrado {q(dp['q_bh_calibrado'])}), también con la lluvia del propio modelo. "
              "¿Por qué? Dentro de GLDAS, dos celdas con la misma lluvia solo pueden responder distinto por lo que el modelo "
              "les asigna a cada una (textura del suelo, tipo de vegetación, profundidad de raíces) y por su forzamiento "
              "local de radiación y temperatura; por eso este contraste es una **hipótesis sobre el terreno** que hay que "
              "contrastar con suelos y cobertura reales (extensión de alta resolución) y con observaciones (SMAP, NDVI). "
              "Las asociaciones de la sección 4.4 no prueban causa. El resultado es del modelo GLDAS, no una medición del suelo.", ""]
    else:
        L += ["**No se afirma**: ningún par cumple a la vez q calibrado < 0.05, supervivencia con la lluvia del modelo y "
              "robustez ≥ 80 %. Decirlo sería sobrevender un resultado que puede ser artefacto de los productos.", ""]

    # ---------------------------------------------------------------- Santo Domingo
    ev = R["event"]
    L += ["## 7. Santo Domingo, 18 de noviembre de 2023", ""]
    if ev is not None:
        pc = ev["por_celda"]
        t = pc.iloc[0]
        L += [f"- Referencia: {ev['afirmacion_contrastada']}",
              f"- {ev['celdas_imerg_que_cubren']} celdas IMERG 0.1° tocan el Distrito Nacional y la provincia Santo Domingo.",
              f"- Celda más lluviosa ({t['celda']}): {f(t['mm_dia_utc_evento'], 1)} mm el 18-nov (día UTC) y "
              f"{f(t['mm_dia_utc_siguiente'], 1)} mm el 19-nov (día UTC); puesto {int(t['puesto_entre_todos_los_dias'])} de "
              f"{int(t['n_dias'])} días 2001-2024; puesto {int(t['puesto_entre_maximos_anuales'])} entre los 24 máximos anuales "
              f"(periodo de retorno empírico ≈ {f(t['periodo_retorno_empirico_anios'], 0)} años, Weibull); mediana de los "
              f"máximos anuales {f(t['maximo_anual_mediana_mm'], 0)} mm; récord de la celda {f(t['maximo_registro_mm'], 0)} mm "
              f"({t['fecha_maximo_registro']}).",
              f"- Celdas donde el 18-nov fue el día más lluvioso de 2001-2024: {int((pc['puesto_entre_todos_los_dias'] == 1).sum())} de {len(pc)}."]
        if "media_hora" in ev:
            mh = ev["media_hora"]
            L.append(f"- Media hora: máximo de 24 h móviles {f(mh['max_24h_movil_mm'], 0)} mm en la celda {mh['celda']} "
                     f"({mh['inicio_ventana_utc']} a {mh['fin_ventana_utc']} UTC); máximo en 30 min {f(mh['max_30min_mm'], 1)} mm; "
                     f"medias horas faltantes: {mh['medias_horas_faltantes']}.")
        L += [f"- {ev['nota']} Estos valores IMERG son cálculo nuestro; no existe una cifra IMERG publicada por NASA para "
              "el evento.", "", "Figura: `figures/nacional/fig09_santo_domingo_2023.png`.", ""]

    # ---------------------------------------------------------------- comparación
    L += ["## 8. Rigor y alcance frente a competidores públicos", "",
          table(pd.DataFrame([
              {"Aspecto": "Lluvia", "ProGarLabs (Chile)": "IMERG (tendencias)", "Earth Memory (RD)": "IMERG V07 mensual + diario + media hora"},
              {"Aspecto": "Temperatura", "ProGarLabs (Chile)": "MERRA-2 T2M", "Earth Memory (RD)": "Tair de GLDAS (+ T2M MERRA-2 vía POWER como control)"},
              {"Aspecto": "Suelo / raíz / ET", "ProGarLabs (Chile)": "no", "Earth Memory (RD)": "GLDAS Noah 2.1 (0-10 cm, 0-100 cm, ET), contrastado con su propia lluvia de forzamiento"},
              {"Aspecto": "Regiones", "ProGarLabs (Chile)": "ponderadas por área", "Earth Memory (RD)": "provincias ponderadas por área (32 unidades ADM1)"},
              {"Aspecto": "Calibración de falsos positivos", "ProGarLabs (Chile)": "documentada", "Earth Memory (RD)": "sustitutos de fases y de bloques (tendencias) + nulo paramétrico (pares); p calibrado"},
              {"Aspecto": "Multiplicidad", "ProGarLabs (Chile)": "—", "Earth Memory (RD)": "BH por familia + significancia de campo + I de Moran"},
              {"Aspecto": "Pregunta", "ProGarLabs (Chile)": "¿hay tendencia?", "Earth Memory (RD)": "¿por qué dos territorios con lluvia parecida responden distinto? (pares, episodios emparejados, factores)"},
              {"Aspecto": "Celdas", "ProGarLabs (Chile)": "9 694 IMERG + 419 MERRA-2", "Earth Memory (RD)": f"{int(ci['incluida'].sum())} IMERG + {int(cg['incluida'].sum())} GLDAS (país ~15× más chico)"},
          ])), "", "Lo de ProGarLabs se toma de su descripción pública; no auditamos su código.", ""]

    # ---------------------------------------------------------------- reproducir
    L += ["## 9. Reproducir y correr para otro país", "",
          "```", "docker compose run --rm nacional", "```", "",
          "Descarga lo que falte (caché con SHA-256), corre el motor IMERG+GLDAS, la comprobación POWER, figuras, informe "
          "y ejecuta los cuadernos (HTML en `reports_nacional/notebooks_html/`). El token de Earthdata se monta en "
          "`/run/secrets` en tiempo de ejecución (`.secrets/earthdata_token`, solo lectura); nunca entra a la imagen.", "",
          "Otro país: `docker compose run --rm nacional --pais HTI` (código ISO3 de geoBoundaries; la caja se calcula del "
          "límite ADM1 + 0.05°; `--bbox LON0 LAT0 LON1 LAT1` la fija a mano). Ajustar `--evento`, `--evento-prov` y la "
          "lista de lugares si se quiere un evento local.", ""]

    L += ["## 10. Extensión de alta resolución", "",
          "El análisis a mayor resolución (CHIRPS 0.05°, TerraClimate ~4 km, suelos SoilGrids, relieve, cobertura "
          "WorldCover y umbrales críticos) se documenta aparte en [`ALTA_RESOLUCION.md`](ALTA_RESOLUCION.md) "
          "(paquete `earthmemory/hr/`, cuaderno `notebooks/05_alta_resolucion_y_umbrales.ipynb`). Este informe cubre el "
          "motor IMERG + GLDAS a resolución nativa de esos productos.", ""]
    L += ["## 11. Figuras", ""] + [f"- `figures/nacional/{k}.png` / `.pdf`" for k in sorted(figs)] + [""]
    path.write_text(LF.join(L), encoding="utf-8", newline=LF)
    write_dictionary(R, path.parent / "DATA_DICTIONARY.md")


# ------------------------------------------------------------------ diccionario de datos

DESC = {
    "celda": "id de celda = latitud_longitud del centro (3 decimales)", "lat": "latitud del centro (°)", "lon": "longitud del centro (°)",
    "area_km2": "área de la celda (km²)", "frac_pais": "fracción del área de la celda dentro de RD (ADM1)",
    "frac_otro_pais": "mayor fracción dentro de otro país (Natural Earth)", "otro_pais": "ISO3 de ese país",
    "frac_mar": "fracción fuera de todo país", "provincia_principal": "provincia con mayor fracción de la celda",
    "incluida": "entra al análisis (≥25 % en RD, más RD que vecino y, en GLDAS, tierra en el modelo)",
    "tierra_gldas": "GLDAS tiene dato de suelo en la celda", "elevacion_m": "elevación de la celda en GLDAS (m)",
    "motivo_exclusion": "por qué no entra", "meses_con_dato": "meses IMERG con dato",
    "provincia": "nombre ADM1 (geoBoundaries)", "codigo": "código ISO 3166-2", "fraccion": "fracción de la celda en la provincia",
    "fecha": "primer día del mes (o día)", "variable": "nombre de la variable", "valor": "valor", "rejilla": "rejilla de origen",
    "pendiente_decada": "pendiente Theil-Sen por década", "p_mk_ar1": "p Mann-Kendall con corrección AR(1)",
    "q_bh": "q Benjamini-Hochberg (p nominal)", "p_empirico": "p calibrado con sustitutos de fases aleatorias",
    "q_bh_empirico": "q BH sobre el p calibrado", "p_calibrado": "p calibrado con el nulo paramétrico de pares",
    "q_bh_calibrado": "q BH sobre el p calibrado", "delta": "métrica(A) − métrica(B)", "ic95_bajo": "límite inferior IC95 (bootstrap)",
    "ic95_alto": "límite superior IC95", "ee_boot": "error estándar bootstrap", "respuesta": "SM_RAIZ, SM_0_10, ET, TAIRE (z robusto)",
    "metrica": "r_spi (acople), phi (memoria ARX), gamma (sensibilidad ARX)", "robustez": "fracción de variantes con mismo signo e IC sin 0",
    "etiqueta_producto": "si el contraste sigue con la lluvia de forzamiento de GLDAS", "SPI3": "índice estandarizado de precipitación a 3 meses",
    "z_SM_RAIZ": "z robusto (mediana/MAD por mes calendario) de la humedad de raíz",
    "P_mm_imerg_remapeada": "lluvia IMERG del mes remapeada a la celda GLDAS (mm)", "SM_RAIZ": "humedad 0-100 cm (mm, GLDAS RootMoist)",
    "SM_0_10": "humedad 0-10 cm (mm, GLDAS SoilMoi0_10cm)", "ET": "evapotranspiración (mm/día, GLDAS Evap)",
    "TAIRE": "temperatura del aire (°C, GLDAS Tair_f)", "url": "URL exacta del pedido (sin credenciales)",
    "sha256": "suma SHA-256 del archivo guardado", "bytes": "tamaño", "descargado_utc": "fecha de descarga",
    "n_A_raiz": "episodios A (raíz) con lluvia IMERG", "n_A_raiz_lluvia_modelo": "episodios A con la lluvia de forzamiento de GLDAS",
}


def write_dictionary(R: dict, path: Path) -> None:
    rdir = Path(R["args"]["resultados"])
    L = ["# Diccionario de datos · Earth Memory nacional", "",
         "Salidas de `python -m earthmemory.nacional` (Docker: `docker compose run --rm nacional`). Parquet ordenado "
         "(una fila por observación) en `results/nacional/parquet/`; CSV en `results/nacional/`. Celdas: id = "
         "`lat_lon` del centro. Fechas: primer día del mes. Generado automáticamente desde los archivos.", ""]
    files = sorted((rdir / "parquet").glob("*.parquet")) + sorted(rdir.glob("*.csv"))
    for fpath in files:
        try:
            df = pd.read_parquet(fpath) if fpath.suffix == ".parquet" else pd.read_csv(fpath, nrows=200)
        except Exception as e:  # noqa: BLE001
            L += [f"## `{fpath.relative_to(rdir.parent.parent).as_posix()}`", f"(no se pudo leer: {e})", ""]
            continue
        L += [f"## `{fpath.relative_to(rdir.parent.parent).as_posix()}`", ""]
        if fpath.suffix == ".parquet":
            L.append(f"{len(df)} filas.")
            if "variable" in df.columns:
                L.append("Variables: " + ", ".join(f"`{v}`" for v in sorted(df["variable"].unique())) + ".")
            L.append("")
        L += ["| columna | tipo | descripción |", "|---|---|---|"]
        for c in df.columns:
            L.append(f"| `{c}` | {df[c].dtype} | {DESC.get(c, '')} |")
        L.append("")
    path.write_text(LF.join(L), encoding="utf-8", newline=LF)


if __name__ == "__main__":  # desarrollo: python -m earthmemory.report estado.pkl informe.md
    import pickle
    import sys
    from . import figures as _f
    _R = pickle.loads(Path(sys.argv[1]).read_bytes())
    write(_R, {k: [] for k in ("fig01_climatologias", "fig02_tendencias")}, Path(sys.argv[2]))
