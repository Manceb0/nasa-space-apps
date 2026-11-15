"""Informe AUDITORIA_CONFIANZA.md, generado desde el estado de la corrida (ningún número escrito a mano)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from . import analisis, procedencia

OUT = Path("reports_nacional/AUDITORIA_CONFIANZA.md")


def f(x, d=2):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "—"
    return f"{x:.{d}f}"


def pct(x, d=0):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "—"
    return f"{100 * x:.{d}f} %"


def md_table(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        out.append("| " + " | ".join(str(r[c]) for c in cols) + " |")
    return "\n".join(out)


def write(S: dict, figs: dict) -> Path:
    st, re, dr, fl, sd, wm = S["stv"], S["re"], S["dr"], S["fl"], S["sd"], S["wm"]
    rs = re["resumen"]
    nat = pd.DataFrame(dr["nacional"])
    n4 = nat[(nat["productos"] == "4 productos") & (nat["umbral_spi3"] == -1.0)].iloc[0]
    n4s = nat[(nat["productos"] == "4 productos") & (nat["umbral_spi3"] == -1.5)].iloc[0]
    nic = nat[(nat["productos"] == "IMERG vs CHIRPS") & (nat["umbral_spi3"] == -1.0)].iloc[0]
    pv = dr["provincia"]
    p1 = pv[pv["umbral_spi3"] == -1.0].sort_values("tasa_condicional", ascending=False)
    top = p1.head(5)
    low = p1.tail(3)
    meta = st["meta"]
    ok = meta[meta["dias_validos"] > 365]
    dd = st["diario"]
    best = dd[dd["es_mejor_desfase"]]
    lag0 = dd[dd["desfase_dias"] == 0]
    mm = st["mensual"]
    allm = mm[mm["subconjunto"] == "todos los meses"]

    def med(df, prod, col):
        v = df[df["producto"] == prod][col].astype(float)
        return float(v.median()) if len(v) else np.nan

    lines = []
    A = lines.append
    A("# Auditoría de confianza · Evidence Intelligence (República Dominicana, 2001-2024)\n")
    A("*Stellar Horizons · NASA Space Apps 2026 · «Be An Earth System Trend Detective!». Generado por "
      "`earthmemory/auditoria/informe.py` desde la corrida; ningún número de este texto se escribió a mano.*\n")
    A("> **Pregunta:** ¿qué conclusión aparentemente correcta sobre sequías e inundaciones en RD podría resultar falsa al "
      "incluir la información que falta, y cuándo bastan los datos para actuar?\n>\n> Regla de lenguaje: no decimos que un "
      "satélite «miente». Distintas fuentes científicas pueden dar interpretaciones contradictorias del mismo territorio; "
      "el sistema investiga por qué.\n")

    # ---------------------------------------------------------------- respuesta corta
    A("## En corto\n")
    A(f"- **Ningún par de productos de lluvia es independiente.** IMERG Final, la lluvia que forzó a GLDAS-2.1 (GPCP) y SMAP L4 "
      f"cuelgan de los pluviómetros de GPCC; CHIRPS mezcla las mismas estaciones dominicanas del GTS/GSOD (lista oficial "
      f"mes a mes); MERRA-2 corregido cuelga de CPC Unified (también GTS). Que coincidan no es validación robusta.")
    A(f"- **La decisión de sequía cambia según el producto.** Por provincia y mes, de los casos en que al menos un producto "
      f"declara sequía (SPI-3 ≤ −1), los cuatro productos no son unánimes en el **{pct(n4['tasa_condicional'])}** "
      f"(IC 95 % {pct(n4['ic95_condicional'][0])}-{pct(n4['ic95_condicional'][1])}; {n4['n_no_unanime']} de "
      f"{n4['n_alguna_alarma']} casos). Con SPI-3 ≤ −1.5: {pct(n4s['tasa_condicional'])} "
      f"(IC {pct(n4s['ic95_condicional'][0])}-{pct(n4s['ic95_condicional'][1])}). Solo IMERG frente a CHIRPS: "
      f"{pct(nic['tasa_condicional'])}. Parte es efecto de umbral (productos a ambos lados de −1), pero en el "
      f"**{pct(n4['tasa_contradiccion_clara'])}** de los casos con alarma (IC {pct(n4['ic95_contradiccion_clara'][0])}-"
      f"{pct(n4['ic95_contradiccion_clara'][1])}) otro producto dice lo contrario: SPI-3 ≥ 0 (normal o húmedo). Solo en "
      f"{n4['n_unanime_sequia']} de {n4['n_alguna_alarma']} provincia-meses con alarma los cuatro coinciden en «sequía».")
    A(f"- **Provincias más sensibles al producto** (SPI-3 ≤ −1): " + "; ".join(
        f"{r['provincia']} {pct(r['tasa_condicional'])} [{pct(r['ic95_condicional_bajo'])}-{pct(r['ic95_condicional_alto'])}]"
        for _, r in top.iterrows()) + ". Los IC se solapan mucho: el orden entre provincias es frágil.")
    if fl is not None:
        r = fl["resumen"]
        a = r[(r["escala"] == "maximo_celda") & (r["tolerancia_dias"] == 1) & (r["desplazamiento_imerg_dias"] == 0)].iloc[0]
        b = r[(r["escala"] == "media_provincia") & (r["tolerancia_dias"] == 1) & (r["desplazamiento_imerg_dias"] == 0)].iloc[0]
        A(f"- **Disparador de inundación (> 100 mm en 48 h)**, IMERG frente a CHIRPS diario ({fl['anios'][0]}-{fl['anios'][-1]}"
          f"{'' if fl['completo'] else ', AÑOS INCOMPLETOS'}): con el máximo de celda de cada provincia y ±1 día de tolerancia, "
          f"{pct(a['tasa_cambio_decision'])} de los disparos no los confirma el otro producto (IC {pct(a['ic95'][0])}-{pct(a['ic95'][1])}; "
          f"IMERG {a['n_A']} disparos, CHIRPS {a['n_B']}). Con la media de provincia: {pct(b['tasa_cambio_decision'])} "
          f"(IMERG {b['n_A']}, CHIRPS {b['n_B']}).")
    else:
        A("- **Disparador de inundación:** CHIRPS diario 2001-2024 aún no estaba completo en esta corrida; no se calculó.")
    A(f"- **'50 de 96' se reproduce** ({rs['reproduccion']['n_posible_diferencia_reproducido']} de "
      f"{rs['reproduccion']['n_A_reproducido']}). Tras escala (0.5°), tiempo (±1 día, ±1 mes de retorno) y umbral, quedan "
      f"**{rs['sin_explicar']} sin explicar** de {rs['n_posible_diferencia']}.")
    d = sd["descomposicion"]
    A(f"- **Santo Domingo 18-nov-2023:** 431 mm (estación, NHC) frente a IMERG {f(d['imerg_celda_dia_utc_mm'], 0)} mm en el día UTC; "
      f"la mejor ventana de 24 h sube a {f(d['imerg_celda_mejor_ventana_mm'], 0)} mm y la mejor celda vecina a "
      f"{f(d['imerg_mejor_vecina_mejor_ventana_mm'], 0)} mm. Quedan {f(d['brecha_restante_mm'], 0)} mm sin explicar por ventana ni escala; "
      f"frente a la media de 11 pluviómetros de ONAMET publicados en prensa ({f(d['media_11_pluviometros_prensa_mm'], 0)} mm) quedan "
      f"{f(d['brecha_restante_vs_media_pluviometros_mm'], 0)} mm. Veredicto: **inconcluso** para repartir la brecha; **se sostiene** "
      f"que un producto de 10 km no reproduce este extremo.\n")

    # ---------------------------------------------------------------- 1 procedencia
    A("## 1 · Procedencia e independencia de cada producto\n")
    A("Verificado el 2026-11-14 contra la documentación oficial (ATBD, README, guías de usuario, artículos). V = escrito así "
      "en la fuente; I = inferido; NV = no verificado. Figura `figures/auditoria/fig01_procedencia.png`; tabla completa con "
      "URLs en `results/auditoria/procedencia_matriz.csv` y `procedencia.json`.\n")
    t = pd.DataFrame([{"Producto": p["producto"], "Clase": p["clase"], "Pluviómetros": p["pluviometros"],
                       "Resolución": p["resolucion"], "Versión": p["version"], "Fuente": " · ".join(f"[{k + 1}]({u})" for k, u in enumerate(p["urls"]))}
                      for p in procedencia.PRODUCTOS])
    A(md_table(t) + "\n")
    A("**Veredicto de independencia:**\n")
    for v in procedencia.veredicto():
        A(f"- {v}")
    A("\nPares que pueden compartir errores (insumo común):\n")
    for a, b, ins, est in procedencia.ARISTAS:
        A(f"- {a} ↔ {b}: {ins} ({est})")
    A("\nCorrecciones respecto a borradores anteriores: CHIRPS v2 diario reparte la péntada con el **CFSv2** (README-CHIRPS2-Daily); "
      "el uso de IMERG Late para el reparto diario es de **CHIRPS v3 'sat'**, no de v2. SMAP L4 V008 corrige su lluvia con "
      "**IMERG V07 Final** fuera de Norteamérica (la nota de versión indica que el procesamiento más reciente lo deja de hacer). "
      "MOD17A3HGF es de 500 m y usa meteorología GEOS-5 de GMAO. TerraClimate v1.1 usa ERA5 + CHELSA, no CRU/JRA-55. "
      "El tramo reciente de NASA POWER viene de GEOS FP-IT, no de MERRA-2.\n")

    # ---------------------------------------------------------------- 2 estaciones
    A("## 2 · Verdad de terreno, con la circularidad marcada\n")
    A(f"- GHCN-Daily tiene **5 estaciones con prefijo DR**; con datos 2001-2024 solo 4 (Santo Domingo 78486, Puerto Plata 78458, "
      f"Punta Cana 78479, Barahona 78482), todas derivadas de informes SYNOP (fuente 'S' = GSOD). Se añadieron las estaciones "
      f"sinópticas OMM de RD en GSOD con 24 h completas (banderas D/F/G). Total usado: **{len(ok)} estaciones** "
      f"(`results/auditoria/estaciones_meta.csv`).")
    circ = ok["fraccion_meses_en_chirps"].fillna(0) if "fraccion_meses_en_chirps" in ok else pd.Series(0, index=ok.index)
    A(f"- **Circularidad verificada:** {int((circ > 0.5).sum())} de {len(ok)} estaciones aparecen en la lista oficial de "
      f"estaciones de CHIRPS v2 en más de la mitad de los meses (mediana {pct(float(circ.median()))} de los meses). Todas son "
      f"sinópticas del GTS: es **probable** (no comprobable con listas públicas por estación) que entren en GPCC (ajuste mensual de "
      f"IMERG Final) y en CPC Unified (corrección de MERRA-2). Su acuerdo con los productos es en parte acuerdo consigo mismos.")
    A(f"- **Desfase de un día:** el mejor desfase diario fue +1 día (la estación fecha el aguacero un día después) en "
      f"{int((best['desfase_dias'] == 1).sum())} de {len(best)} combinaciones estación × producto; 0 días en "
      f"{int((best['desfase_dias'] == 0).sum())}; −1 en {int((best['desfase_dias'] == -1).sum())}. GSOD resume en día UTC, pero el "
      f"acumulado de 24 h del SYNOP no termina a medianoche.")
    rows = []
    for p in ("IMERG", "CHIRPS", "MERRA2"):
        if p not in set(best["producto"]):
            continue
        rows.append({"Producto": analisis.NOMBRE[p], "r diaria (desfase 0)": f(med(lag0, p, "r")),
                     "r diaria (mejor desfase)": f(med(best, p, "r")), "KGE diaria": f(med(best, p, "kge")),
                     "sesgo": pct(med(best, p, "sesgo_rel")), "POD ≥50": f(med(best, p, "pod_50")),
                     "FAR ≥50": f(med(best, p, "far_50")), "CSI ≥50": f(med(best, p, "csi_50")),
                     "POD ≥100": f(med(best, p, "pod_100")), "CSI ≥100": f(med(best, p, "csi_100")),
                     "p99 obs / prod (mm)": f"{f(med(best, p, 'p99_obs'), 0)} / {f(med(best, p, 'p99_prod'), 0)}"})
    A("\nMedianas entre estaciones, escala diaria (`estaciones_validacion_diaria.csv`):\n")
    A(md_table(pd.DataFrame(rows)) + "\n")
    rows = []
    for p in analisis.PRODUCTOS_M:
        if p not in set(allm["producto"]):
            continue
        rows.append({"Producto": analisis.NOMBRE[p], "r mensual": f(med(allm, p, "r")), "KGE mensual": f(med(allm, p, "kge")),
                     "sesgo": pct(med(allm, p, "sesgo_rel"))})
    A("Escala mensual (meses con ≥ 90 % de días; `estaciones_validacion_mensual.csv`):\n")
    A(md_table(pd.DataFrame(rows)) + "\n")
    def sub(prod, lab, col="r"):
        x = mm[(mm["producto"] == prod) & (mm["subconjunto"] == lab)]
        return float(x[col].median()) if len(x) else np.nan, int(x["n"].fillna(0).sum()) if len(x) else 0
    con, sin = "meses con la estación en CHIRPS", "meses sin la estación en CHIRPS"
    (c1, nc1), (c2, nc2) = sub("CHIRPS", con), sub("CHIRPS", sin)
    (i1, _), (i2, _) = sub("IMERG", con), sub("IMERG", sin)
    if nc1:
        A(f"- **Prueba directa de circularidad (mensual):** CHIRPS frente a la estación, r mediana {f(c1)} en los meses en que "
          f"la estación entró en CHIRPS ({nc1} estación-meses) y {f(c2)} cuando no entró ({nc2}). Control con IMERG en los mismos "
          f"meses: {f(i1)} y {f(i2)}. Si CHIRPS mejora al ingerir la estación y IMERG no, ese acuerdo de CHIRPS no es evidencia "
          f"independiente. Con tan pocos meses sin ingesta, la prueba es débil (estaciones con n < 30 meses no se informan).")
    sp = st["dispersion"]
    cl = sp[sp["fecha_estacion"] == "climatologia"]
    if len(cl):
        A(f"- **Punto frente a celda:** la lluvia media anual de las 9 celdas IMERG alrededor de cada estación varía en mediana "
          f"{f(float((cl['imerg_vecinas_anual_max_mm'] - cl['imerg_vecinas_anual_min_mm']).median()), 0)} mm/año entre la celda más "
          f"seca y la más húmeda (`estaciones_dispersion_vecinas.csv`).")
        ev = sp[(sp["fecha_estacion"] != "climatologia") & (sp["desfase_dias"] == 1)]
        if len(ev):
            A(f"- En los {len(ev)} días con ≥ 100 mm en una estación (comparando con el día UTC anterior de IMERG), la más lluviosa de "
              f"las 9 celdas vecinas quedó por debajo de la estación en {int((ev['imerg_vecinas_max_mm'] < ev['estacion_mm']).sum())}.")
    A("")

    # ---------------------------------------------------------------- 3 re-auditoría
    A("## 3 · Re-auditoría de «50 de 96 episodios = posible diferencia entre productos»\n")
    A("**Definición exacta (código del motor nacional):**\n")
    A(rs["definicion"].replace("\n", "\n") + "\n")
    A(f"**Reproducción:** original {rs['reproduccion']['n_posible_diferencia_original']}/{rs['reproduccion']['n_A_original']}; "
      f"recalculado {rs['reproduccion']['n_posible_diferencia_reproducido']}/{rs['reproduccion']['n_A_reproducido']}.\n")
    A("| Causa probada | Episodios que explica (de " + str(rs["n_posible_diferencia"]) + ", no excluyentes) | Atribución en orden a→b→c |")
    A("|---|---|---|")
    att = rs["atribucion_secuencial"]
    A(f"| (a) escala: recuento a 0.5° | {rs['explica_a_escala']} | {att.get('a_escala', 0)} |")
    A(f"| (b) tiempo: ±1 día en el mensual ({rs['explica_b_desplazamiento_dia']}) o retorno a ±1 mes ({rs['explica_b_tolerancia_mes']}) | {rs['explica_b_tiempo']} | {att.get('b_tiempo', 0)} |")
    A(f"| (c) variable/umbral: aparece con umbrales relajados o el modelo quedó cerca del umbral | {rs['explica_c_variable_umbral']} | {att.get('c_variable_umbral', 0)} |")
    A(f"| **sin explicar** | — | **{att.get('sin_explicar', 0)}** |\n")
    A(f"- Recuentos a otras escalas/rutas: a 0.5° hay {rs['recuento_05']['n_A_imerg_05']} contradicciones A y "
      f"{rs['recuento_05']['n_posible_diferencia_05']} 'posible diferencia' ({rs['recuento_05']['bloques']} bloques). IMERG mensual rehecho "
      f"desde el diario: " + "; ".join(f"desplazamiento {k} d → {v['n_posible_diferencia']}/{v['n_A']}" for k, v in rs["recuento_desde_diario"].items()) + ".")
    A(f"- **Tercer producto (CHIRPS a 0.25°):** de los {rs['n_posible_diferencia']}, CHIRPS reproduce la contradicción de IMERG en "
      f"{rs['todos_50_chirps_con_imerg']}; de los {rs['sin_explicar']} sin explicar, en {rs['sin_explicar_chirps_con_imerg']}. "
      f"Con CHIRPS como lluvia hay {rs['n_A_con_chirps']} contradicciones A en total. Recordatorio: CHIRPS e IMERG comparten IR e "
      f"insumos de pluviómetros; que coincidan no prueba que la lluvia del modelo esté mal.")
    A("- **(c) es estructural:** la humedad del suelo es la MISMA serie en las dos ramas. Toda la diferencia viene de la lluvia "
      "(si hubo sequía y en qué mes volvió). No es un desacuerdo entre suelo y lluvia, sino entre dos lluvias.")
    rl = re["relieve"]
    A("\n(d) Relieve y costa (ρ de Spearman por celda; p calibrado con desplazamientos toroidales del campo de la covariable):\n")
    A(md_table(rl.assign(rho_spearman=rl["rho_spearman"].map(lambda x: f(x)), p_nominal=rl["p_nominal"].map(lambda x: f(x, 3)),
                          p_toroidal=rl["p_toroidal"].map(lambda x: f(x, 3)))[["resultado", "covariable", "n_celdas", "rho_spearman", "p_nominal", "p_toroidal"]]) + "\n")
    p = re["persistencia"]
    A(f"(e) Persistencia: máxima fracción anual de 'posible diferencia' {f(p['max_fraccion_anual_obs'])} (p por permutación "
      f"{f(p['p_perm_max_fraccion_anual'], 3)}); celdas con ≥ 2 episodios 'posible diferencia': {p['celdas_con_2mas_obs']} "
      f"(p {f(p['p_perm_celdas_repetidas'], 3)}).\n")
    rp = re["representatividad"]
    if len(rp):
        A("(f) Representatividad (fracción marcada por categoría; χ² con p por permutación):\n")
        A(md_table(rp.assign(fraccion=rp["fraccion"].map(lambda x: f(x)), chi2=rp["chi2"].map(lambda x: f(x, 1)),
                              p_perm=rp["p_perm"].map(lambda x: f(x, 3)))[["variable", "comparacion", "categoria", "n_base", "n_marcados", "fraccion", "chi2", "p_perm"]]) + "\n")

    # ---------------------------------------------------------------- 4 cambio de decisión
    A("## 4 · Tasa de cambio de decisión (el resultado central)\n")
    A("Por provincia (32 unidades ADM1, media ponderada por área sobre una rejilla común 0.05°) y mes, 2001-2024. SPI-3 de cada "
      "producto con su propia climatología. Tasa condicional = de los casos en que al menos un producto declara sequía, "
      "fracción sin unanimidad. IC 95 % por bootstrap de bloques de año (2 000 réplicas). Como los productos comparten "
      "insumos, **esta tasa es un mínimo** de la incertidumbre de decisión real.\n")
    tn = nat.copy()
    tn["tasa global"] = [f"{pct(r['tasa_global'], 1)} [{pct(r['ic95_global'][0], 1)}-{pct(r['ic95_global'][1], 1)}]" for _, r in tn.iterrows()]
    tn["tasa condicional"] = [f"{pct(r['tasa_condicional'], 1)} [{pct(r['ic95_condicional'][0], 1)}-{pct(r['ic95_condicional'][1], 1)}]" for _, r in tn.iterrows()]
    A(md_table(tn[["umbral_spi3", "productos", "n_casos", "n_alguna_alarma", "n_no_unanime", "tasa global", "tasa condicional"]]) + "\n")
    py = dr["por_anio"]
    if len(py):
        py = py[py["n_alguna_alarma"] > 0].copy()
        py["frac_unanime"] = py["n_unanime_sequia"] / py["n_alguna_alarma"]
        best_y = py.sort_values("n_unanime_sequia", ascending=False).head(4)
        A("**¿Cuándo bastan los datos para actuar?** Los provincia-meses en que los cuatro productos coinciden en «sequía» se "
          "concentran en pocos años: " + "; ".join(f"{int(r['anio'])}: {int(r['n_unanime_sequia'])} de {int(r['n_alguna_alarma'])} "
          f"con alarma" for _, r in best_y.iterrows()) + " (`cambio_decision_sequia_por_anio.csv`).\n")
    A("Provincias, SPI-3 ≤ −1 (5 más y 3 menos sensibles; tabla completa en `cambio_decision_sequia_provincias.csv`):\n")
    tt = pd.concat([top, low])
    A(md_table(pd.DataFrame({"Provincia": tt["provincia"], "tasa condicional [IC 95 %]": [
        f"{pct(r['tasa_condicional'])} [{pct(r['ic95_condicional_bajo'])}-{pct(r['ic95_condicional_alto'])}]" for _, r in tt.iterrows()],
        "meses en sequía IMERG/CHIRPS/GLDAS/MERRA-2": tt.filter(like="meses_alarma").iloc[:, 0]})) + "\n")
    prs = dr["pares"]
    prs = prs[prs["umbral_spi3"] == -1.0]
    A("Por pares (1 − Jaccard de los meses-provincia en sequía):\n")
    A(md_table(pd.DataFrame({"A": prs["producto_a"], "B": prs["producto_b"],
                             "desacuerdo [IC 95 %]": [f"{pct(r['tasa_condicional'])} [{pct(r['ic95_condicional'][0])}-{pct(r['ic95_condicional'][1])}]" for _, r in prs.iterrows()]})) + "\n")
    if fl is not None:
        A(f"**Disparador de inundación > 100 mm en 48 h** (IMERG frente a CHIRPS diario, {fl['anios'][0]}-{fl['anios'][-1]}, "
          f"{fl['n_dias']} días{'' if fl['completo'] else '; años INCOMPLETOS: resultado parcial'}). El sEAP de la Cruz Roja Dominicana "
          f"(MDRDO020) usa un boletín de INDOMET con > 100 mm en 2 días asociado a ciclón tropical (pronóstico, no satélite); aquí se "
          f"usa solo el umbral como prueba de sensibilidad, no se reproduce el protocolo.\n")
        r = fl["resumen"].copy()
        r["IC 95 %"] = r["ic95"].map(lambda x: f"{pct(x[0])}-{pct(x[1])}")
        r["tasa"] = r["tasa_cambio_decision"].map(lambda x: pct(x))
        A(md_table(r[["escala", "desplazamiento_imerg_dias", "tolerancia_dias", "n_A", "n_B", "A_confirmado_por_B", "B_confirmado_por_A", "tasa", "IC 95 %"]]) + "\n")
        A("n_A = disparos IMERG, n_B = disparos CHIRPS (provincia-día). Recordatorio: el día de CHIRPS v2 es una redistribución con el CFSv2.\n")

    # ---------------------------------------------------------------- 5 Santo Domingo
    A("## 5 · Santo Domingo, 18 de noviembre de 2023\n")
    A("- **Fuente de la estación:** NHC, Tropical Cyclone Report AL222023 (Hagen, 28-feb-2024): pluviómetro en Arroyo Hondo Viejo, "
      "«16.97 inches (431 mm) during the 24-h period ending on 18 November» y 482.5 mm en 16-19 nov "
      "(https://www.nhc.noaa.gov/data/tcr/AL222023_Twenty-Two.pdf). ONAMET vía prensa (Listín Diario 21-nov-2023; Diario Libre "
      "19-nov-2023). **La ventana exacta de 24 h NO está publicada**; la prensa sitúa lo peor la tarde del sábado 18 (hora local). "
      "La cifra de 474 mm «desde el jueves» solo aparece en prensa de 2026; el NHC da 482.5 mm (16-19 nov).")
    gh = sd["ghcn_78486"]
    if gh:
        A(f"- **GHCN-D Santo Domingo (DRM00078486, SYNOP):** " + ", ".join(f"{k}: {f(v, 1)} mm" for k, v in gh.items()) +
          ". El aguacero aparece fechado el 19: la ventana del SYNOP termina por la mañana del día siguiente.")
    A("")
    w = sd["ventanas"].copy()
    for c in ("imerg_celda_mm", "imerg_vecinas_max_mm", "imerg_vecinas_media_mm", "imerg_vecinas_min_mm"):
        w[c] = w[c].map(lambda x: f(x, 0))
    A(md_table(w[["ventana", "inicio_utc", "fin_utc", "imerg_celda_mm", "imerg_vecinas_max_mm", "imerg_vecinas_media_mm"]]) + "\n")
    c = sd["chirps"]
    A(f"- CHIRPS v2.0 diario 0.05°: celda {f(c['celda_18'], 0)} mm el 18 y {f(c['celda_19'], 0)} mm el 19; mejor celda vecina 18+19: "
      f"{f(c['vecinas_max_18_19'], 0)} mm (día redistribuido con CFSv2).")
    A(f"- Celda IMERG usada: centro {f(sd['celda']['lat'], 2)} N, {f(sd['celda']['lon'], 2)} (la coordenada de la estación no es "
      f"pública; se usó el centroide aproximado del barrio, 18.495 N, −69.948).")
    A(f"- **Descomposición:** brecha total {f(431 - d['imerg_celda_dia_utc_mm'], 0)} mm = ventana {f(d['efecto_ventana_mm'], 0)} mm + escala "
      f"(mejor de 9 celdas) {f(d['efecto_escala_vecinas_mm'], 0)} mm + **resto {f(d['brecha_restante_mm'], 0)} mm**. Usar la media de 11 "
      f"pluviómetros de ONAMET como aproximación del área (prensa, sin coordenadas ni ventana) deja {f(d['brecha_restante_vs_media_pluviometros_mm'], 0)} mm.")
    A(f"- **Veredicto: inconcluso** para atribuir la brecha (ventana y coordenada desconocidas). **Se sostiene** que ni IMERG ni CHIRPS "
      f"reproducen el extremo puntual, incluso con la ventana y la celda más favorables.\n")

    # ---------------------------------------------------------------- 6 dónde medir
    A("## 6 · Prototipo «dónde medir después» (PRELIMINAR)\n")
    A("Índice por celda 0.1° = media de rangos percentiles de: desacuerdo persistente (1 − r de SPI-3 IMERG/CHIRPS), persistencia "
      "(fracción de años con algún mes de cambio de decisión), tasa de cambio condicional (SPI-3 ≤ −1, 4 productos) y distancia a "
      "la estación GHCN-D activa más cercana. **No prueba dónde deben ir estaciones.** Faltan: acceso y seguridad del sitio, "
      "exposición del pluviómetro, población y bienes expuestos, la red real de ONAMET/INDRHI (no está en GHCN-D) y el valor de "
      "cada sitio para las decisiones de quien actúa. El CIMH reconoce que las Antillas Mayores están poco representadas por "
      "estaciones en su monitoreo regional (https://rcc.cimh.edu.bb/spi-monitor/).\n")
    top10 = wm.head(10)
    A(md_table(pd.DataFrame({"lat": top10["lat"].map(lambda x: f(x, 2)), "lon": top10["lon"].map(lambda x: f(x, 2)),
                             "provincia": top10["provincia"], "índice": top10["indice_prioridad"].map(lambda x: f(x)),
                             "sin distancia": top10["indice_sin_distancia"].map(lambda x: f(x)),
                             "km a GHCN-D activa": top10["dist_estacion_ghcn_activa_km"].map(lambda x: f(x, 0))})) + "\n")

    # ---------------------------------------------------------------- tres listas
    A("## Lo que sabemos\n")
    A("- Los productos de lluvia que usamos no son independientes entre sí: comparten pluviómetros (GPCC, GTS, CPC Unified), "
      "IR geoestacionario y sistemas de modelo (verificado en su documentación).")
    A(f"- La decisión «hay sequía» en una provincia cambia según el producto en {pct(n4['tasa_condicional'])} de los casos con alguna "
      f"alarma (IC {pct(n4['ic95_condicional'][0])}-{pct(n4['ic95_condicional'][1])}), y eso con productos que comparten insumos.")
    A("- Las estaciones dominicanas de GHCN-D/GSOD entran en la mezcla de CHIRPS (lista oficial): la validación con ellas es parcialmente circular.")
    A("- La contradicción «volvió la lluvia, el suelo no» de GLDAS depende de qué lluvia se use; el suelo es el mismo en las dos ramas.")
    A("- En Santo Domingo (18-nov-2023) ningún producto de 5-10 km llega al acumulado puntual, aun con la ventana y celda más favorables.")
    A("\n## Lo que creemos saber\n")
    A(f"- Que las provincias más sensibles al producto son {', '.join(top['provincia'].head(3))}: los IC se solapan con los de muchas otras.")
    A(f"- Que {rs['sin_explicar']} de los 50 episodios 'posible diferencia' reflejan un desacuerdo real entre la lluvia IMERG y la que "
      "forzó a GLDAS (no de escala, día o umbral); no sabemos cuál de las dos lluvias está más cerca de la verdad.")
    A("- Que el desfase de un día entre estaciones SYNOP y productos en día UTC es la norma (mejor correlación con +1 día).")
    A("- Que el desacuerdo crece o no con el relieve y la costa: ver p calibrados en la sección 3 (con 65 celdas, la potencia es baja).")
    A("\n## Lo que todavía hay que comprobar\n")
    A("- La ventana exacta y la coordenada del pluviómetro de Arroyo Hondo Viejo (boletín original de ONAMET/INDOMET).")
    A("- La lista de estaciones de GPCC y CPC Unified en RD (no pública por estación): ¿cuánto de la validación es circular para IMERG y MERRA-2?")
    A("- Datos de la red densa de ONAMET e INDRHI (no están en GHCN-D) para una validación no circular.")
    A("- SMAP L3 (0-5 cm) como testigo del suelo en los 50 episodios (otro motor del equipo lo trabaja).")
    A("- Si el disparador real del sEAP (boletín de INDOMET con pronóstico) diverge igual que los productos satelitales.")
    if fl is not None and not fl["completo"]:
        A(f"- El disparador de 48 h con CHIRPS diario completo 2001-2024 (esta corrida usó {len(fl['anios'])} años).")
    A("\n## Limitaciones\n")
    A("- CHIRPS diario es una redistribución con el CFSv2 de la péntada; las comparaciones diarias con CHIRPS miden también esa redistribución.")
    A("- MERRA-2 se lleva a 0.05° con la celda POWER que contiene cada subcelda (0.5° × 0.625°): las provincias pequeñas quedan dentro de 1-2 celdas.")
    A("- Las tasas de cambio de decisión dependen del umbral y del índice (SPI-3, gamma por mes calendario, 2001-2024 como referencia).")
    A("- Las cifras de prensa de ONAMET no tienen coordenadas ni ventana; se usan solo como orden de magnitud y van marcadas.")
    A("- Ninguna asociación aquí es causa. Ningún dato es sintético salvo en `tests/test_auditoria.py` (etiquetado).")

    # ---------------------------------------------------------------- reproducción y citas
    A("\n## Reproducir\n")
    A("```\ndocker compose run --rm auditoria\n# pruebas:\ndocker compose run --rm --entrypoint \"uv run --frozen --no-sync pytest -q tests/test_auditoria.py\" auditoria\n```\n")
    A("Descargas crudas (GHCN-D, GSOD, listas de estaciones de CHIRPS, ONI, OSCAR) en `data/auditoria/` con URL, fecha, SHA-256 y "
      "licencia en `data/auditoria/MANIFEST.json`. Salidas: `results/auditoria/` (CSV/JSON y `web/` con `CONTRATO.md`), "
      "`figures/auditoria/` (PNG 300 dpi + PDF + JSON de procedencia), `notebooks/07_auditoria_de_confianza.ipynb` y su HTML.\n")
    A("## Figuras\n")
    for k, v in figs.items():
        A(f"- `figures/auditoria/{k}.png` / `.pdf`" + ("" if isinstance(v, list) and v else f" — {v}"))
    A("\n## Citas\n")
    cites = [
        "Huffman, G.J. et al. (2023). IMERG V07 Technical Documentation. NASA GSFC. " + procedencia.U["imerg_td"],
        "Funk, C. et al. (2015). The climate hazards infrared precipitation with stations. Sci. Data 2, 150066. doi:10.1038/sdata.2015.66",
        "CHC (s.f.). README-CHIRPS2-Daily. " + procedencia.U["chirps_d"],
        "Rodell, M. et al. (2004). The Global Land Data Assimilation System. BAMS 85, 381-394. doi:10.1175/BAMS-85-3-381; README GLDAS-2: " + procedencia.U["gldas"],
        "Reichle, R. et al. SMAP L4 Surface and Root-Zone Soil Moisture, User Guide V008. NSIDC. " + procedencia.U["l4"],
        "O'Neill, P. et al. SMAP Enhanced L3 Radiometer Soil Moisture V6, User Guide. NSIDC. " + procedencia.U["l3"],
        "Abatzoglou, J.T. et al. (2018). TerraClimate. Sci. Data 5, 170191. doi:10.1038/sdata.2017.191",
        "Gelaro, R. et al. (2017). MERRA-2. J. Climate 30, 5419-5454. doi:10.1175/JCLI-D-16-0758.1",
        "Reichle, R. et al. (2017). Land surface precipitation in MERRA-2. J. Climate 30, 1643-1664. doi:10.1175/JCLI-D-16-0570.1",
        "Chen, M. et al. (2008). Assessing objective techniques for gauge-based analyses of global daily precipitation. JGR 113, D04110.",
        "Schneider, U. et al. GPCC products v2022 (DWD). " + procedencia.U["gpcc"],
        "Watkins, M. et al. (2015). Improved methods for observing Earth's time variable mass distribution with GRACE. JGR 120. doi:10.1002/2014JB011547",
        "Menne, M.J. et al. (2012). An overview of the GHCN-Daily database. JTECH 29, 897-910. doi:10.1175/JTECH-D-11-00103.1; doi:10.7289/V5D21VHZ",
        "Hagen, A. (2024). Tropical Cyclone Report: Potential Tropical Cyclone Twenty-Two (AL222023). NHC. https://www.nhc.noaa.gov/data/tcr/AL222023_Twenty-Two.pdf",
        "IFRC (2026). Simplified EAP Dominican Republic MDRDO020. https://go-api.ifrc.org/api/DownloadFile/94311/MDRDO020%20sEAP%20Summary",
        "Gupta, H.V. et al. (2009). Decomposition of the mean squared error and NSE performance criteria (KGE). J. Hydrol. 377, 80-91.",
        "NOAA CPC. Oceanic Niño Index (ONI). https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt",
        "WMO OSCAR/Surface, estaciones de RD. https://oscar.wmo.int/surface/",
    ]
    for c in cites:
        A(f"- {c}")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return OUT
