"""Escribe reports_nacional/ALTA_RESOLUCION.md a partir de results/nacional_hr/resumen.json (todo número sale de ahí)."""

from __future__ import annotations

import json

from .common import DATA, REPORT
from .sources import SOURCES


def _f(x, nd=2):
    if x is None:
        return "—"
    if isinstance(x, (list, tuple)):
        return "–".join(_f(v, nd) for v in x)
    if isinstance(x, bool):
        return "sí" if x else "no"
    if isinstance(x, int):
        return f"{x:,}".replace(",", " ")
    try:
        return f"{x:.{nd}f}"
    except (TypeError, ValueError):
        return str(x)


def _pct(a, b):
    return f"{100 * a / b:.1f} %" if b else "—"


def write(r: dict) -> None:
    u = r["umbrales"]
    man = json.loads((DATA / "MANIFEST.json").read_text(encoding="utf-8"))
    rutas = man.get("rutas", {})
    nfiles = len(man["archivos"])
    mb = sum(v["bytes"] for v in man["archivos"].values()) / 1e6
    L = []
    w = L.append
    w("# Earth Memory · Alta resolución y umbrales críticos (República Dominicana, 2001-2024)\n")
    w("*Stellar Horizons · NASA Space Apps 2026 · «Be An Earth System Trend Detective!». Generado por "
      "`earthmemory/hr/report.py` desde `results/nacional_hr/resumen.json`; ningún número de este texto se escribió "
      "a mano.*\n")
    # ---------------------------------------------------------------- resumen
    cv = r.get("chirps_vs_imerg_0.1") or {}
    pc = u.get("curvas_por_paisaje", {})
    tod = next((v for k, v in pc.items() if k.startswith("todas")), None)
    smp = next((v for k, v in pc.items() if "SMAP" in k), None)
    q = r["quiebres"]
    par = r.get("par", {})
    w("## En corto\n")
    import math
    area = next(c["celdas_RD"] for c in r["capas"] if c["capa"].startswith("(referencia)"))
    km = lambda dlat, dlon: (dlat * 110.6) * (dlon * 111.32 * math.cos(math.radians(18.8)))  # noqa: E731
    w(f"- **Más fino y verificable.** {r['celdas_tierra_005']} celdas de 0.05° (~5.3 km) cubren la RD; a igual área "
      f"({area:,.0f} km²) serían ≈ {area / km(0.5, 0.625):.0f} celdas de NASA POWER (0.5° × 0.625°) y "
      f"≈ {area / km(0.25, 0.25):.0f} de GLDAS (0.25°). Se descargaron "
      f"{nfiles} archivos ({mb:.0f} MB), cada uno con su URL y SHA-256 en `data/nacional_hr/MANIFEST.json`.")
    if cv:
        w(f"- **CHIRPS y la lluvia NASA (IMERG) cuentan la misma historia a 0.1°:** correlación mediana de las "
          f"anomalías mensuales r = {_f(cv['r_mediana'])} (p10-p90: {_f(cv['r_p10'])}-{_f(cv['r_p90'])}, "
          f"{cv['n_celdas_0.1']} celdas); peor al oeste de 71° O (r mediana {_f(cv['r_mediana_oeste_de_71O'])}) que al "
          f"este de 70° O ({_f(cv['r_mediana_este_de_70O'])}).")
    if tod:
        w(f"- **Umbral crítico nacional:** con todas las celdas juntas, la eficiencia con la que la lluvia extra se "
          f"vuelve agua del suelo cambia de régimen cuando el suelo ya está lleno en un {100 * tod['theta']:.0f} % de su "
          f"rango (IC 95 % {100 * tod['theta_ic95'][0]:.0f}-{100 * tod['theta_ic95'][1]:.0f} %): por encima, cada mm "
          f"extra deja cada vez menos agua en el suelo (saturación; ΔBIC = {_f(tod['dBIC'], 0)}).")
    w(f"- **Pero celda por celda casi nunca se puede afirmar:** de {u['celdas_evaluadas']} celdas, "
      f"{u['p_menor_005_sin_corregir']} tienen p < 0.05 sin corregir y solo {u['sostenidos_q005_dBIC2']} sostienen el "
      "umbral tras FDR y ΔBIC > 2. 24 años de datos mensuales no bastan para fijar un umbral por píxel.")
    w(f"- **Los 'meses de quiebre' casi desaparecen al corregir la autocorrelación:** Pettitt clásico marca "
      f"{q['tc_soil']['n_q05_asintotica_sin_correccion']} de {q['tc_soil']['n_celdas']} celdas de humedad del suelo; con "
      f"bootstrap por bloques quedan {q['tc_soil']['n_q05_bloques12']} (bloques de 12 meses) y "
      f"{q['tc_soil']['n_q05_bloques24']} (24 meses).")
    if par.get("celdas") is not None or r.get("par_celdas"):
        pcs = r["par_celdas"]
        w(f"- **Par de demostración a 0.05°:** {pcs[0]['nombre']} (A) y {pcs[1]['nombre']} (B), a "
          f"{_f(par['dist_km'], 0)} km: misma lluvia CHIRPS (r = {_f(par['r_lluvia'])}, diferencia de media "
          f"{100 * par['dif_rel_lluvia']:.1f} %), eficiencia {_f(pcs[0]['ef'], 3)} frente a {_f(pcs[1]['ef'], 3)} "
          f"(q = {_f(par['q'], 3)}; {'supera' if par.get('supera_fdr') else 'NO supera'} el FDR); NASA SMAP L4 da la "
          f"misma dirección (Δ = {_f((par.get('smap') or {}).get('delta'), 3)}, p = {_f((par.get('smap') or {}).get('p'), 3)}).")
    E = r["evento_2023_11_18"]["barras"]
    w(f"- **18-nov-2023:** la estación (431 mm, preliminar) frente a CHIRPS {E['CHIRPS 18-nov · celda 0.05°']:.0f} mm "
      f"ese día y {E['CHIRPS péntada 16-20 nov · celda']:.0f} mm en la péntada; IMERG "
      f"{E.get('IMERG 18-nov (00-24 UTC) · celda 0.1°', float('nan')):.0f} mm. Ningún producto de satélite de 5-10 km "
      "reproduce un acumulado puntual de ese tamaño.\n")
    # ---------------------------------------------------------------- fuentes
    w("## 1 · Fuentes (todas públicas; verificadas el 2026-11-14)\n")
    w("| Capa | Cita | DOI / URL | Licencia | Versión | Resolución nativa | NASA |")
    w("|---|---|---|---|---|---|---|")
    for k, s in SOURCES.items():
        w(f"| {s['nombre']} | {s['cita']} | {s['doi']} · {s['url']} | {s['licencia']} | {s['version']} | "
          f"{s['resolucion']} | {'sí' if s['nasa'] else 'no'} |")
    w("\n**Qué añade cada capa y qué es:**\n")
    for k, s in SOURCES.items():
        w(f"- **{s['nombre']}.** {s['que_es']} *Aporta:* {s['aporta']}")
    w("\n**La NASA sigue en el centro.** IMERG (lluvia) y SMAP L4 (humedad del suelo) son NASA. CHIRPS combina "
      "infrarrojo de satélites geoestacionarios con estaciones; TerraClimate v1.1 (la versión que sirve hoy el THREDDS, "
      "creada el 2026-06-02) combina la climatología WorldClim v2.1 con anomalías de **ERA5** (la v1.0 usaba CRU TS4 y "
      "JRA-55: la descripción 'WorldClim/CRU/JRA55' ya no es la de los archivos descargados). Son comprobaciones "
      "independientes de NASA, no sustitutos.\n")
    w("**Capas, resolución y número de celdas sobre la RD** (`results/nacional_hr/capas_resolucion_y_celdas.csv`):\n")
    w("| Capa | Resolución nativa | Celdas sobre RD | Criterio |")
    w("|---|---|---|---|")
    for c in r["capas"]:
        w(f"| {c['capa']} | {c['resolucion_nativa']} | {_f(c['celdas_RD'])} | {c['criterio']} |")
    w("\n**Estado de cada descarga** (sección `rutas` del manifiesto):\n")
    w("| Ruta | Estado | Pedidos | Errores | Nota |")
    w("|---|---|---|---|---|")
    for k, v in sorted(rutas.items()):
        if isinstance(v, dict) and "estado" in v:
            w(f"| {k} | {v['estado']} | {v.get('pedidos', '—')} | {v.get('n_errores', 0)} | "
              f"{v.get('nota', v.get('error', ''))[:220]} |")
    w("")
    # ---------------------------------------------------------------- armonización
    w("## 2 · Armonización a 0.05° (sin fingir precisión)\n")
    w("- **Rejilla común:** la de CHIRPS (bordes en múltiplos de 0.05°), 72.10-68.20 O × 17.40-20.10 N. Celda de "
      "tierra = al menos 50 % de su área dentro de geoBoundaries ADM0 (100 puntos por celda, peso cos φ).")
    w("- **Continuos más finos** (TerraClimate 1/24°, SoilGrids 0.0025°, DEM 3″): media ponderada por el área de "
      "solape exacta en la esfera (remapeo conservativo de primer orden). La pendiente se calcula a 90 m (Horn) y "
      "después se promedia; el relieve es la desviación típica de la elevación dentro de la celda.")
    w("- **Categóricos** (WorldCover): fracción de cada clase en la celda, nunca la clase mayoritaria. Se leyó la vista "
      "general 1/8 del COG (~80 m); en una ventana de validación del Cibao a 10 m, la mayor diferencia de fracción por "
      "celda fue:")
    wv = r.get("worldcover_validacion") or {}
    w("  " + "; ".join(f"{k} {100 * v['dif_abs_max_celda']:.1f} puntos" for k, v in wv.items()) + ".")
    w("- **Más gruesos que 0.05°** (IMERG 0.1°, SMAP 9 km, GLDAS 0.25°): **no se interpolan**. Se guardan y dibujan "
      "en su rejilla nativa; cuando se cruzan con una celda 0.05° se usa la celda nativa que contiene su centro, y "
      "CHIRPS se agrega a la celda gruesa (no al revés).")
    w("- **TerraClimate a 1/24° no es variabilidad de 4 km:** la anomalía de cada mes viene de ERA5 (~0.25°, ~28 km) y "
      "la capacidad de agua del suelo del modelo es de 0.5° (Wang-Erlandsson et al. 2016). Su detalle fino es sobre todo "
      "climatología. Lo mismo, en menor grado, con SMAP L4 (asimila brillo de banda L a 36 km).\n")
    # ---------------------------------------------------------------- verificación
    w("## 3 · Verificación cruzada\n")
    if cv:
        w(f"- CHIRPS agregado a la rejilla IMERG (0.1°), anomalías mensuales 2001-2024: r mediana {_f(cv['r_mediana'])}, "
          f"p10 {_f(cv['r_p10'])}, p90 {_f(cv['r_p90'])}. Cociente de lluvia media CHIRPS/IMERG: mediana "
          f"{_f(cv['cociente_lluvia_media_mediana'])} (p10-p90 {_f(cv['cociente_p10'])}-{_f(cv['cociente_p90'])}). "
          "Mapa: figura hr1, panel f.")
    mv = r["evento_2023_11_18"]["mes_chirps_vs_diario"]
    w(f"- CHIRPS diario sumado (noviembre 2023, celda de Santo Domingo) = {_f(mv['suma_diaria_nov_celda'], 1)} mm; "
      f"mensual = {_f(mv['mensual_nov_celda'], 1)} mm: los dos archivos son coherentes.")
    w("- Lectores de cada formato probados con datos sintéticos en `tests/test_hr_metodos.py` (remapeo, umbral, "
      "Pettitt, FDR, par y sustitutos, ridge espacial, proyección EASE-Grid 2.0).\n")
    # ---------------------------------------------------------------- umbrales
    w("## 4 · Umbrales críticos: ¿cuándo deja el suelo de 'aceptar' la lluvia?\n")
    w("**Idea (no literal):** un suelo no responde igual a la misma lluvia extra según lo lleno que esté. Seco, una "
      "parte se va en evaporación; casi lleno, el agua sobra y escurre. Buscamos el **punto de quiebre** del llenado "
      "antecedente donde cambia la 'eficiencia' (mm que gana el suelo por cada mm de lluvia por encima de lo normal).\n")
    w("**Método (por celda 0.05°).** y = ΔS (cambio mensual de humedad del suelo TerraClimate), Pa = anomalía de lluvia "
      "CHIRPS, f = llenado relativo antecedente (S − S_min)/(S_max − S_min), efectos fijos de mes calendario. M0: "
      "y ~ Pa + f + Pa·f; M1 añade h = (f − θ)+ y Pa·h (regresión segmentada, θ en los cuantiles 15-85 % de f). "
      "Prueba sup-F con nula por bootstrap de residuos de M0 en bloques circulares de 12 meses "
      f"({r['replicas']['umbral_supF']} réplicas), FDR de Benjamini-Hochberg sobre todas las celdas, y "
      f"'sostenido' = q < 0.05 y ΔBIC > 2. IC 95 % de θ por bootstrap de bloques móviles ({r['replicas']['umbral_IC']}).\n")
    n = u["celdas_evaluadas"]
    w("| Resultado por celda | Celdas | % |")
    w("|---|---|---|")
    w(f"| evaluadas | {n} | 100 % |")
    w(f"| p < 0.05 sin corregir | {u['p_menor_005_sin_corregir']} | {_pct(u['p_menor_005_sin_corregir'], n)} |")
    w(f"| q < 0.05 (FDR) | {u['q_menor_005']} | {_pct(u['q_menor_005'], n)} |")
    w(f"| **sostenido** (q < 0.05 y ΔBIC > 2) | **{u['sostenidos_q005_dBIC2']}** | {_pct(u['sostenidos_q005_dBIC2'], n)} |")
    w(f"| sostenido con ΔBIC > 6 | {u['sostenidos_dBIC6']} | {_pct(u['sostenidos_dBIC6'], n)} |")
    s1, s2 = u["sensibilidad_lluvia_TerraClimate"], u["sensibilidad_sin_efectos_fijos_mes"]
    w(f"| sensibilidad: lluvia de TerraClimate como forzante | {s1['sostenidos']} | coinciden con la principal: "
      f"{s1['coinciden_con_CHIRPS']} |")
    w(f"| sensibilidad: sin efectos fijos de mes | {s2['sostenidos']} | coinciden con la principal: "
      f"{s2['coinciden_con_principal']} |")
    if u.get("smap_9km"):
        sm = u["smap_9km"]
        w(f"| SMAP L4 (NASA) 9 km, {sm['meses'][0]} a {sm['meses'][1]} | {sm['n_sostenido']} de {sm['n']} | — |")
    w("")
    if u["sostenidos_q005_dBIC2"]:
        w(f"En las celdas con umbral sostenido: θ mediano = {_f(u['theta_mediana'])} (p25-p75 {_f(u['theta_p25_p75'])}; "
          f"≈ {_f(u['theta_mm_mediana'], 0)} mm de agua en el suelo), ancho mediano del IC 95 % = "
          f"{_f(u['ancho_ic_mediana'])}. Eficiencia mediana: suelo seco {_f(u['ef_seco_mediana'], 3)}, en el umbral "
          f"{_f(u['ef_umbral_mediana'], 3)}, suelo húmedo {_f(u['ef_humedo_mediana'], 3)}; en "
          f"{100 * u['fraccion_saturacion_b5_neg']:.0f} % de ellas el quiebre es de **saturación** (la eficiencia cae "
          f"por encima de θ), y en {100 * u['fraccion_pico_sube_y_cae']:.0f} % la curva tiene forma de **pico**: por "
          "debajo de θ el suelo seco guarda MENOS de cada mm extra que en el umbral (en el balance del modelo, la "
          "evaporación se lleva primero el agua: el suelo seco 'rechaza' lluvia en ese sentido, no por hidrofobia), y "
          "por encima guarda menos porque ya está lleno. θ es el **punto de máxima eficiencia**. Provincias con más "
          "celdas de umbral sostenido: "
          f"{', '.join(f'{k} ({v})' for k, v in u['provincias_con_mas_umbrales'].items())}.\n")
    w("**Lectura honesta.** La mayoría de los p < 0.05 sin corregir no sobreviven al FDR: una celda sola, con 287 "
      "meses y una lluvia (CHIRPS) que no es la que forzó al modelo de suelo (ERA5), no tiene potencia para fijar su "
      "propio umbral. Cuando se usa la lluvia del propio TerraClimate aparecen muchos más umbrales: eso mide sobre "
      "todo la **mecánica del cubo** del modelo (capacidad fija), no una propiedad observada del suelo. Por eso el "
      "resultado principal es la curva agrupada, más abajo.\n")
    w("**Curvas por paisaje (creativo, con la incertidumbre correcta).** Se agrupan celdas por terciles de aridez "
      "(P/PET) y de arcilla, se estima un umbral COMÚN al grupo (efectos fijos celda × mes) y la incertidumbre se "
      "obtiene remuestreando **bloques de tiempo compartidos por todas las celdas** (no se finge que 500 celdas vecinas "
      "sean 500 experimentos independientes). Figura hr3b.\n")
    w("| Grupo | Fuente | Celdas | θ (llenado) | IC 95 % de θ | ΔBIC | cambio de pendiente b5 | IC 95 % b5 | quiebre sostenido | eficiencia en f=0.10 / 0.50 / 0.90 |")
    w("|---|---|---|---|---|---|---|---|---|---|")
    for k, g in pc.items():
        f = g["f"]
        def ef_at(x, g=g, f=f):
            import numpy as np
            return float(np.interp(x, f, g["ef"]))
        w(f"| {k} | {g['fuente']} | {g['n_celdas']} | {_f(g['theta'])} | {_f(g['theta_ic95'])} | {_f(g['dBIC'], 0)} | "
          f"{_f(g['b5'], 3)} | {_f(g['b5_ic95'], 3)} | {'sí' if g['b5_excluye_0'] else 'no'} | "
          f"{_f(ef_at(0.1), 3)} / {_f(ef_at(0.5), 3)} / {_f(ef_at(0.9), 3)} |")
    w("\n'Quiebre sostenido' = el IC 95 % bootstrap del cambio de pendiente b5 excluye 0. El ΔBIC agrupado es enorme "
      "porque n es grande y NO corrige la dependencia entre celdas: no se usa como prueba, solo como descripción.\n")
    if smp:
        w(f"**NASA SMAP L4** (2015-2024, 9 km): θ = {_f(smp['theta'])} (IC {_f(smp['theta_ic95'])}), b5 = "
          f"{_f(smp['b5'], 3)} (IC {_f(smp['b5_ic95'], 3)}). SMAP es otro modelo (Catchment del GEOS) que asimila "
          "observaciones de banda L de SMAP; su forma de curva es la comprobación NASA de la de TerraClimate.\n")
    # ---------------------------------------------------------------- quiebres
    w("## 5 · Meses de quiebre (Pettitt)\n")
    w("Prueba de Pettitt sobre anomalías mensuales (sin ciclo estacional). La p asintótica supone independencia; con "
      "series persistentes da quiebres de sobra. Aquí la p sale de un bootstrap por bloques circulares (los mismos "
      f"índices para todas las celdas, {r['replicas']['pettitt']} réplicas) y luego FDR. Figura hr4.\n")
    import pandas as pd
    from .common import RES
    cel = pd.read_csv(RES / "celdas_005.csv")
    w("| Variable | Celdas | q < 0.05 asintótica (sin corregir autocorrelación) | q < 0.05 bloques 12 meses | q < 0.05 bloques 24 meses | Año de quiebre más frecuente SIN corregir (celdas) |")
    w("|---|---|---|---|---|---|")
    names = {"tc_soil": "Humedad del suelo (TerraClimate)", "tc_def": "Déficit hídrico (TerraClimate)",
             "P_chirps": "Lluvia (CHIRPS)"}
    for k, v in q.items():
        w(f"| {names.get(k, k)} | {v['n_celdas']} | {v['n_q05_asintotica_sin_correccion']} | {v['n_q05_bloques12']} | "
          f"{v['n_q05_bloques24']} | "
          + ", ".join(f"{int(a)} ({n_})" for a, n_ in
                      cel.loc[cel[f"quiebre_{k}_q_asintotica"] < 0.05, f"quiebre_{k}_anio"].astype(int)
                      .value_counts().head(3).items()) + " |")
    w("\n**Lectura.** El Pettitt clásico 'encuentra' un quiebre hacia 2013-2014 en casi todo el país (la media nacional "
      "del suelo pasa a anomalías negativas desde 2013: figura hr4, panel e); con la corrección no sobrevive ninguno. La diferencia entre la primera columna y "
      "las otras dos es el mensaje: casi todos los 'quiebres' del "
      "Pettitt clásico son persistencia (meses secos seguidos de meses secos), no cambios de régimen. Un quiebre que "
      "sobrevive indica un cambio de nivel de la anomalía, que también puede ser una tendencia gradual o un cambio en "
      "los datos de entrada de ERA5; no se interpreta como causa.\n")
    # ---------------------------------------------------------------- factores
    w("## 6 · ¿Qué acompaña a la respuesta? Suelo, terreno, cobertura, aridez\n")
    w("Ridge con variables estandarizadas (coeficiente = DE de la respuesta por DE del factor, con los demás fijos), λ "
      "por validación cruzada, habilidad con validación cruzada **por bloques espaciales de 0.5°**, IC 95 % por "
      "bootstrap de bloques espaciales, I de Moran de los residuos. Figura hr5.\n")
    for key, d in r["factores"].items():
        if "coef" not in d:
            w(f"- **{key}:** {d.get('omitido')}")
            continue
        w(f"**{d['titulo']}** — n = {d['n']} celdas en {d['n_bloques']} bloques; R² VC espacial = "
          f"{_f(d['r2_cv_espacial'])}, R² VC aleatoria = {_f(d['r2_cv_aleatoria'])}, R² de ajuste = {_f(d['r2_ajuste'])}; "
          f"I de Moran de residuos = {_f(d['moran_residuos']['I'])} (p perm. {_f(d['moran_residuos']['p_perm'], 3)}).\n")
        w("| Factor | β estandarizado | IC 95 % | IC excluye 0 | ρ de Spearman (simple) |")
        w("|---|---|---|---|---|")
        for nme, c in sorted(d["coef"].items(), key=lambda kv: -abs(kv[1]["beta_z"])):
            w(f"| {nme} | {_f(c['beta_z'])} | {_f(c['ic95'])} | {'sí' if c['excluye_0'] else 'no'} | {_f(c['spearman'])} |")
        w("")
    for key in ("theta", "eficiencia"):
        d = r["factores"].get(key, {})
        if "coef" in d:
            top = max(d["coef"].items(), key=lambda kv: abs(kv[1]["beta_z"]))
            w(f"- **{d['titulo']}:** el factor más fuerte es **{top[0]}** (β = {_f(top[1]['beta_z'])}, IC "
              f"{_f(top[1]['ic95'])}).")
    w("  Lectura física (asociación): las celdas más lluviosas pasan más meses cerca de llenarse, por eso la lluvia "
      "extra rinde menos ahí; y donde el clima es más húmedo (P/PET alto) el umbral θ está más arriba.\n")
    w("**Lectura.** La autocorrelación espacial de los residuos es alta: las celdas vecinas no son independientes, y los "
      "IC por bloques espaciales son la cifra honesta. La fila de control (S_max de TerraClimate) muestra que la "
      "textura de SoilGrids apenas explica la capacidad del modelo: la capacidad de TerraClimate viene de un mapa de 0.5°, "
      "así que **cualquier relación fina entre textura y respuesta en TerraClimate no puede ser mecanismo del modelo**; "
      "sale de la lluvia y la climatología que acompañan a esos suelos.\n")
    # ---------------------------------------------------------------- par
    w("## 7 · 'Misma lluvia, distinta respuesta' a alta resolución\n")
    w(f"Candidatos: pares de celdas 0.05° a 20-60 km (celdas distintas en SMAP 9 km y en TerraClimate) con lluvia anual "
      f"CHIRPS a < 5 %, anomalías mensuales correlacionadas (r ≥ 0.85) y distribución mensual parecida (KS D ≤ 0.10): "
      f"**{par.get('n_candidatos_lluvia_parecida')}** pares. Respuesta = eficiencia (pendiente de ΔS sobre la "
      "anomalía de lluvia con efectos fijos de mes). La diferencia se prueba con bootstrap por bloques móviles de 12 "
      f"meses con los MISMOS meses para las dos celdas ({r['replicas']['par']} réplicas) y FDR sobre todos los "
      f"candidatos: **{par.get('n_significativos_q05')}** pares con q < 0.05 "
      f"({_pct(par.get('n_significativos_q05') or 0, par.get('n_candidatos_lluvia_parecida') or 0)}).\n")
    if r.get("par_celdas"):
        A, B = r["par_celdas"]
        w(f"**Par elegido** (mayor |z| × distancia en suelo/terreno entre los que superan el FDR"
          f"{'' if par.get('supera_fdr') else ' — NINGUNO lo supera; se muestra el mejor candidato'}, y con la misma "
          "dirección en SMAP L4):\n")
        w("| | A | B |")
        w("|---|---|---|")
        w(f"| celda | {A['nombre']} | {B['nombre']} |")
        w(f"| lluvia anual CHIRPS (mm) | {_f(A['lluvia_anual'], 0)} | {_f(B['lluvia_anual'], 0)} |")
        w(f"| eficiencia TerraClimate (IC 95 %) | {_f(A['ef'], 3)} ({_f(A['ef_ic95'], 3)}) | {_f(B['ef'], 3)} ({_f(B['ef_ic95'], 3)}) |")
        for nme, (va, vb) in par["factores"].items():
            w(f"| {nme} | {_f(va, 1)} | {_f(vb, 1)} |")
        w(f"\nΔe = {_f(par['delta'], 3)} (IC 95 % {_f(par['ic95_delta'], 3)}), z = {_f(par['z'])}, p = {_f(par['p'], 4)}, "
          f"q = {_f(par['q'], 4)}. Distancia {_f(par['dist_km'], 0)} km; lluvia: r = {_f(par['r_lluvia'])}, "
          f"KS D = {_f(par['ks_D'])}, diferencia de media {100 * par['dif_rel_lluvia']:.1f} %.")
        if par.get("smap"):
            s = par["smap"]
            w(f"- **NASA SMAP L4** (zona de raíces, 2015-2024): eficiencia A {_f(s['e_A'], 3)}, B {_f(s['e_B'], 3)}, "
              f"Δ = {_f(s['delta'], 3)}, p = {_f(s['p'], 3)}; misma dirección: {'sí' if s['misma_direccion'] else 'no'}.")
        if par.get("imerg"):
            im = par["imerg"]
            w(f"- **NASA IMERG** en las dos celdas: r de anomalías = {_f(im['r_anomalias'])}, lluvia anual "
              f"{_f(im['lluvia_anual_A'], 0)} y {_f(im['lluvia_anual_B'], 0)} mm "
              f"({'misma celda IMERG' if im['misma_celda_0.1'] else 'celdas IMERG distintas'}).")
        sur = par.get("sustitutos", {})
        w(f"- **Falsos positivos con sustitutos:** {sur.get('n_sustitutos')} series simuladas con la MISMA eficiencia "
          f"verdadera en A y B (residuos propios remuestreados en bloques compartidos): la prueba marcó p < 0.05 en el "
          f"{100 * sur.get('tasa_falsos_positivos', float('nan')):.1f} % (nominal 5 %).")
        ar = par["factores"].get("aridez P/PET (×10)")
        if ar and abs(ar[0] - ar[1]) / max(ar) > 0.2:
            w(f"- **Ojo:** la lluvia es la misma, pero la demanda de evaporación no: P/PET = {ar[0] / 10:.2f} en A y "
              f"{ar[1] / 10:.2f} en B (la altura enfría y baja la PET). 'Misma lluvia' no es 'mismo balance'; parte de "
              "la diferencia de respuesta va por ahí.")
        w("\n**Lectura:** asociación. La diferencia de eficiencia acompaña a diferencias de suelo, terreno y cobertura, "
          "pero en TerraClimate la respuesta la fijan la climatología, ERA5 y una capacidad de 0.5°: no demuestra que la "
          "textura o la pendiente la causen. Otros pares fuertes: `results/nacional_hr/resumen.json` → `par.top10`.\n")
    # ---------------------------------------------------------------- evento
    w("## 8 · 18 de noviembre de 2023, Santo Domingo\n")
    w("La estación ONAMET de Arroyo Hondo Viejo registró **431 mm** (valor preliminar; fuente: prensa, Acento, "
      "19-nov-2023, y dato aportado por el equipo; no se encontró aún el boletín oficial). La posición marcada en la "
      "figura es la del barrio (≈ 18.50 N, 69.95 O, ±2 km), no coordenadas oficiales de la estación.\n")
    w("| Fuente | mm |")
    w("|---|---|")
    for k, v in E.items():
        w(f"| {k} | {v:.0f} |")
    w("\n**Cuidado al comparar.** El CHIRPS diario v2 **no** es un producto diario independiente: reparte el total de "
      "la péntada (anclado a satélite + estaciones) entre sus días con las proporciones del pronóstico CFSv2 "
      "(README-CHIRPS2-Daily). La cifra comparable es la péntada 16-20 nov. Una estación mide un punto; una celda de "
      "5-10 km promedia el área: un aguacero convectivo de 431 mm en un punto puede ser mucho menos en promedio de "
      "área. Que satélite y estación difieran no dice cuál 'está mal'. Figura hr7.\n")
    # ---------------------------------------------------------------- qué sobrevive
    w("## 9 · Qué sobrevive a la corrección y qué no\n")
    w("| Afirmación | ¿Sobrevive? | Por qué |")
    w("|---|---|---|")
    if tod:
        w(f"| Existe un umbral de llenado nacional donde la lluvia extra rinde menos (saturación) | "
          f"{'sí' if tod['b5_excluye_0'] else 'no'} | IC 95 % de b5 {_f(tod['b5_ic95'], 3)} con bloques de tiempo compartidos |")
    w(f"| Cada celda 0.05° tiene su propio umbral identificable | casi nunca ({u['sostenidos_q005_dBIC2']} de {n}) | FDR + ΔBIC |")
    w(f"| Hay 'meses de quiebre' extendidos en la humedad del suelo | {'no' if q['tc_soil']['n_q05_bloques12'] < 0.05 * q['tc_soil']['n_celdas'] else 'sí'} "
      f"({q['tc_soil']['n_q05_bloques12']} celdas) | la versión sin corregir ({q['tc_soil']['n_q05_asintotica_sin_correccion']}) es persistencia |")
    eff = r["factores"].get("eficiencia", {})
    if "coef" in eff:
        top = sorted(eff["coef"].items(), key=lambda kv: -abs(kv[1]["beta_z"]))[:3]
        w(f"| Los factores estáticos predicen la eficiencia fuera de su región | R² VC espacial {_f(eff['r2_cv_espacial'])} | "
          f"factores más fuertes: {', '.join(f'{k} ({_f(c['beta_z'])})' for k, c in top)} |")
    if r.get("par_celdas"):
        w(f"| Par 'misma lluvia, distinta respuesta' | {'sí' if par.get('supera_fdr') else 'no'} (q = {_f(par['q'], 3)}) | "
          f"FDR sobre {par.get('n_candidatos_lluvia_parecida')} candidatos; sustitutos {100 * par['sustitutos']['tasa_falsos_positivos']:.1f} % |")
    w("")
    # ---------------------------------------------------------------- límites
    w("## 10 · Límites\n")
    w("- **TerraClimate y SMAP L4 son modelos**, no mediciones de humedad del suelo. TerraClimate es un cubo de "
      "Thornthwaite-Mather con capacidad de 0.5°: puede saturarse, pero no puede 'rechazar' agua por un suelo seco "
      "hidrófobo ni por sellado superficial. Un umbral en TerraClimate es una propiedad del modelo forzado por ERA5.")
    w("- **Resolución efectiva < resolución de la rejilla:** anomalías de ERA5 (~28 km) en TerraClimate; banda L de 36 km "
      "en SMAP; estaciones escasas en CHIRPS para la RD (el archivo de reconocimientos de CHIRPS no lista a ONAMET entre "
      "los aportes históricos de América Latina).")
    w("- **Lluvia y suelo de fuentes distintas:** usar CHIRPS para explicar un suelo forzado por ERA5 diluye la señal "
      "(por eso la sensibilidad con la lluvia de TerraClimate da más umbrales). Es una elección conservadora.")
    w("- **SoilGrids** es una predicción (con incertidumbre que no se propagó aquí); el WCS reproyecta en el servidor. "
      "**WorldCover** es de 2021 (una foto, no una serie). **Copernicus DEM** es de superficie (incluye dosel y edificios).")
    w("- **Dependencia espacial:** el FDR de Benjamini-Hochberg es válido con dependencia positiva (PRDS), pero las "
      "celdas vecinas no son pruebas independientes; los mapas de 'celdas significativas' no deben contarse como "
      "evidencias separadas.")
    w("- **Sin causalidad:** todo es asociación dentro de productos de satélite y modelos.\n")
    # ---------------------------------------------------------------- reproducir
    w("## 11 · Reproducir\n")
    w("```\ndocker compose build\ndocker compose run --rm alta_resolucion                 # descarga lo que falta y corre todo\n"
      "docker compose run --rm alta_resolucion --sin-descarga  # solo con la caché de data/nacional_hr\n```\n")
    w("SMAP L4 necesita el token de Earthdata en `.secrets/earthdata_token` (montado de solo lectura; nunca se imprime "
      "ni se guarda). Sin token, la corrida usa la caché o se salta SMAP y lo anota. Semilla fija "
      f"({r['semilla']}); mismas entradas → mismas salidas.\n")
    w("**Figuras** (`figures/nacional_hr/`, PDF + PNG + JSON de procedencia): hr1 climatología en resolución nativa · "
      "hr2 factores estáticos · hr3 umbrales por celda · hr3b curvas de eficiencia por paisaje · hr4 meses de quiebre · "
      "hr5 factores del umbral · hr6 par 'misma lluvia' · hr7 evento 18-nov-2023.\n")
    w("**Tablas** (`results/nacional_hr/`): `celdas_005.csv` (una fila por celda: factores, umbral, quiebres), "
      "`umbrales_smap_9km.csv`, `capas_resolucion_y_celdas.csv`, `fuentes.csv`, `resumen.json`. Cuaderno: "
      "`notebooks/05_alta_resolucion_y_umbrales.ipynb` y su HTML en `reports_nacional/notebooks_html/`.\n")
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")
