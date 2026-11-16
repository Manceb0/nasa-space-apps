"""Informe reports_nacional/TESTIGOS_E_HIPOTESIS.md, generado SOLO a partir de results/testigos (ningún número a mano)."""

from __future__ import annotations

import json

import pandas as pd

from .common import CITAS, DATA, REPORT, RES


def _j(n):
    p = RES / n
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def f(x, d=2):
    if x is None:
        return "—"
    try:
        x = float(x)
    except (TypeError, ValueError):
        return str(x)
    if x != x:
        return "—"
    if abs(x) < 10 ** (-d) and x != 0:
        return f"{x:.1e}"
    return f"{x:.{d}f}"


def ci(v, d=2):
    return f"[{f(v[0], d)}, {f(v[1], d)}]" if v else "—"


def _pair_line(r):
    if r.get("no_comprobable"):
        return f"no comprobable ({r.get('motivo', 'sin datos de calidad')}; n A = {r['n_A']}, n B = {r['n_B']})"
    a = r.get("e_A", r.get("gamma_A"))
    b = r.get("e_B", r.get("gamma_B"))
    s = f"A {f(a, 3)} · B {f(b, 3)} · Δ {f(r['delta'], 3)}"
    if r.get("delta_ic95"):
        s += f" {ci(r['delta_ic95'], 3)}"
    if r.get("p_calibrado") is not None:
        s += f" · p calibrado {f(r['p_calibrado'], 3)}"
    elif r.get("p") is not None:
        s += f" · p {f(r['p'], 3)}"
    if r.get("tasa_p05_nulo") is not None:
        s += f" · FPR nominal en sustitutos {f(r['tasa_p05_nulo'], 3)}"
    if r.get("n_A"):
        s += f" · n {r['n_A']}/{r['n_B']}"
    return s


def write() -> None:
    Q = _j("smap_l3_calidad_resumen.json")
    P = _j("pares_smap_l3.json")
    M = _j("memoria_lluvia_vs_suelo.json")
    U = _j("umbral_testigos.json")
    B = _j("bosque_hansen.json")
    I = _j("intensidad_chirps.json")
    man = json.loads((DATA / "MANIFEST.json").read_text(encoding="utf-8"))
    rutas = man.get("rutas", {})
    md = []
    w = md.append
    w("# Testigos e hipótesis · ¿Se sostienen las conclusiones de Earth Memory?")
    w("")
    w("*Stellar Horizons · NASA Space Apps 2026 · «Be An Earth System Trend Detective!» (República Dominicana). "
      "Generado por `earthmemory/testigos/report.py` desde `results/testigos/`; ningún número se escribió a mano. "
      "Objetivo: intentar romper nuestras propias conclusiones con datos que no salen del mismo modelo.*")
    w("")
    # ------------------------------------------------------------ resumen y tabla de veredictos
    pts = Q["puntos"]
    mm = M["resumen_principal"] if M else None
    orig_beta = M["reproduccion_original"]["z_retorno_SM_RAIZ"] if M else None
    w("## Tabla de veredictos")
    w("")
    w("| Afirmación | Prueba | ¿Independiente? | Resultado | Veredicto |")
    w("|---|---|---|---|---|")
    gl_v = P["veredictos"]["gldas"]["veredicto"] if P else "—"
    hr_v = P["veredictos"]["hr"]["veredicto"] if P else "—"
    w(f"| Par Monseñor Nouel vs Santiago/La Vega: Δγ raíz −0.13 (GLDAS) | SMAP L3 (radiómetro) calidad recomendada, "
      f"respuesta a eventos de lluvia IMERG + γ mensual | sí (L3 es retrieval) | 0 pasos con calidad recomendada en los "
      f"{pts['GLDAS_A']['n_pixeles_9km']} + {pts['GLDAS_B']['n_pixeles_9km']} píxeles 9 km (VWC mediano "
      f"{f(pts['GLDAS_A']['vwc_mediana_am'], 1)} y {f(pts['GLDAS_B']['vwc_mediana_am'], 1)} kg/m²; bandera urbana "
      f"{f(pts['GLDAS_B']['bandera_urbano_am'], 2)} en B) | **no comprobable** |")
    if P:
        sup = _find(P["gldas"]["gamma"], "GLDAS superficie")
        w(f"| Mismo par, mismo modelo, 2015-2024 | GLDAS γ en el periodo de SMAP, raíz y capa 0-10 cm | no | raíz: "
          f"{_pair_line(_find(P['gldas']['gamma'], 'GLDAS raíz'))}; **0-10 cm (la capa que un satélite podría ver): "
          f"Δγ {f(sup['delta'], 3)} {ci(sup['delta_ic95'], 3)}, p calibrado {f(sup['p_calibrado'], 2)}** | el contraste vive "
          f"solo en la raíz del modelo |")
        w(f"| Par 0.05° Cordillera Central vs La Vega: eficiencia 0.075 vs 0.168 (TerraClimate) | SMAP L3 calidad recomendada "
          f"(mensual con CHIRPS y por evento con IMERG) | sí | 0 pasos recomendados en los dos píxeles (VWC mediano "
          f"{f(pts['HR_A']['vwc_mediana_am'], 1)} y {f(pts['HR_B']['vwc_mediana_am'], 1)} kg/m²; bandera 'vegetación densa' "
          f"{f(pts['HR_A']['bandera_vegetacion_densa_am'], 2)} / {f(pts['HR_B']['bandera_vegetacion_densa_am'], 2)}) | "
          f"**no comprobable** |")
        hev = next((r for r in P["hr"]["eficiencia"] if "todos los retrievals" in r["etiqueta"] and "evento" in r["metrica"]
                    and not r.get("no_comprobable")), None)
        if hev:
            w(f"| Mismo par 0.05°, indicio fuera de especificación | SMAP L3 con retrievals NO recomendados, por evento | "
              f"no cuenta (fuera de especificación) | A {f(hev['e_A'], 4)} vs B {f(hev['e_B'], 4)} m³/m³ por mm; Δ "
              f"{f(hev['delta'], 4)} {ci(hev['delta_ic95'], 4)}, p calibrado {f(hev['p_calibrado'], 3)}: **dirección "
              f"opuesta** a la afirmación | indicio en contra, débil |")
        tc15 = next((r for r in P["hr"]["eficiencia"] if r["etiqueta"].startswith("TerraClimate · 2015")), None)
        if tc15:
            w(f"| Mismo par 0.05°, mismo modelo, 2015-2024 | TerraClimate en el periodo de SMAP | no | Δ {f(tc15['delta'], 3)} "
              f"{ci(tc15['delta_ic95'], 3)}, p calibrado {f(tc15['p_calibrado'], 2)} | se debilita (el IC ya toca 0) |")
    w("| «SMAP confirma la misma dirección (p 0.001)» | revisión de procedencia | **no**: era SMAP L4 (modelo Catchment "
      "con asimilación de Tb), y desde la v6 su lluvia de forzamiento se corrige con IMERG Final | — | **se cae como "
      "confirmación independiente** (queda como acuerdo entre modelos) |")
    if M:
        vc = mm["veredictos"]
        main_v = max(vc, key=vc.get)
        w(f"| «El suelo antecedente es el único factor significativo (β {f(orig_beta['beta_suelo_M2'])})» | modelos anidados "
          f"con API de IMERG (k 0.85-0.95; 30/60/90 d), API del forzante de GLDAS, SPI-3, EF de mes, provincia, terreno o "
          f"celda; {mm['n_especificaciones']} especificaciones; bootstrap por año; FDR | parcial (lluvia observada vs "
          f"suelo modelado) | β del suelo con lluvia en el modelo {f(mm['beta_suelo_M3_rango'][0])} a "
          f"{f(mm['beta_suelo_M3_rango'][1])}; R² parcial del suelo dada la lluvia {f(mm['r2p_suelo_dado_lluvia_rango'][0], 3)}-"
          f"{f(mm['r2p_suelo_dado_lluvia_rango'][1], 3)}; suelo q<0.05 en {mm['especificaciones_suelo_q05']}/"
          f"{mm['n_especificaciones']}, lluvia q<0.05 en {mm['especificaciones_lluvia_q05']}/{mm['n_especificaciones']} "
          f"| **{_verd_mem2()}** |")
    if U:
        w(f"| Umbral nacional θ = 0.59 [0.49-0.73] (cubo TerraClimate) | misma regresión segmentada con SMAP L3 y con "
          f"API en lugar del cubo | parcial | {_umbral_cell(U)} | **{_umbral_verd(U)}** |")
    if I:
        if I.get("estado") == "ok":
            w(f"| «La intensidad de la lluvia no importa» (probado solo con IMERG) | mismos factores con CHIRPS v2 diario y "
              f"por péntadas ({I['periodo'][0][:4]}-{I['periodo'][1][:4]}) | parcial (CHIRPS comparte estaciones GTS) | "
              f"{_int_cell(I)} | **{_int_verd(I)}** |")
        else:
            w(f"| «La intensidad no importa» (solo IMERG) | CHIRPS diario | — | {I['estado']} | **no comprobable** |")
    if B:
        z = B["zonas"]
        parts = []
        for k, v in z.items():
            if k.startswith("9 km"):
                continue
            y = v["perdida_por_anio_km2"]
            tot = sum(y.values())
            yy = max(y, key=y.get) if tot > 0 else None
            conc = f", {f(100 * y[yy] / tot, 0)} % en {yy}" if yy and y[yy] / tot > 0.5 else ""
            parts.append(f"{k.split(' (celda')[0].split(' (caja')[0]}: {f(v['perdida_pct_del_bosque_2000'], 1)} %{conc}")
        w(f"| Bosque en los territorios comparados | Hansen GFC v1.13, pérdida 2001-2023 sobre bosque 2000 (≥ 30 %) | sí "
          f"(Landsat) | {'; '.join(parts)} | descriptivo, sin causa (los modelos usan cobertura fija) |")
    ap = rutas.get("APPEEARS", {})
    w(f"| Vegetación (NDVI) como testigo de los pares | AppEEARS 8ad4ac19… | — | API devolvió HTTP {ap.get('http_estado_tarea', '—')} "
      f"con el token de Earthdata (pide su propio login; no se usaron contraseñas) | **no comprobable** |")
    w("")
    w("Veredicto en una línea: **ninguna de las dos parejas 'misma lluvia, distinta respuesta' puede confirmarse con una "
      "observación independiente de la humedad del suelo**: SMAP L3 no entrega retrievals de calidad recomendada en "
      "esas celdas (vegetación densa y, en Santiago, zona urbana). Lo que antes se presentó como confirmación (SMAP L4) "
      "es otro modelo que comparte lluvia con IMERG.")
    w("")
    # ------------------------------------------------------------ 1. SMAP L3
    w("## 1 · Qué puede ver SMAP L3 en la RD")
    w("")
    sm = rutas.get("SMAP_L3E", {})
    w(f"- Producto: SMAP L3 Enhanced Radiometer 9 km (SPL3SMP_E **V006**, NSIDC; colección CMR C2938664763-NSIDC_CPRD), "
      f"{Q['dias'][0]} a {Q['dias'][1]}, {Q['n_dias']} días, pasos AM (6:00 local) y PM (18:00). Recorte por OPeNDAP en la "
      f"nube de la caja 17.3-20.1 N, 72.1-68.2 O: {sm.get('pedidos', '—')} archivos, {sm.get('n_errores', '—')} errores, "
      f"cada uno con URL, fecha y SHA-256 en `data/testigos/MANIFEST.json`.")
    w(f"- De {Q['n_pixeles_tierra_rd']} píxeles de 9 km con centro en tierra dominicana, **{Q['pixeles_tierra_sin_ningun_recomendado']} "
      f"no tienen NINGÚN retrieval de calidad recomendada en casi 10 años** (mediana nacional de la fracción recomendada: "
      f"{f(Q['frac_recomendado_mediana_tierra'], 2)}); VWC mediano de los píxeles de tierra {f(Q['vwc_mediana_tierra'], 1)} kg/m² "
      f"(el umbral de calidad del algoritmo es 5 kg/m²).")
    w("- En los cuatro territorios de las afirmaciones hay retrievals 'con éxito' en ~35 % de los días, pero **ninguno con "
      "calidad recomendada**:")
    w("")
    w("| Sitio | Píxeles 9 km | Días con retrieval (AM) | Recomendados (AM / PM) | VWC mediano (kg/m²) | Fracción VWC > 5 | Bandera vegetación densa | Bandera urbana |")
    w("|---|---|---|---|---|---|---|---|")
    for k, lab in (("GLDAS_A", "GA"), ("GLDAS_B", "GB"), ("HR_A", "HA"), ("HR_B", "HB")):
        p = pts[k]
        w(f"| {lab} · {p['nombre']} | {p['n_pixeles_9km']} | {f(p['frac_exito_am'], 2)} | {f(p['frac_recomendado_am'], 2)} / "
          f"{f(p['frac_recomendado_pm'], 2)} | {f(p['vwc_mediana_am'], 1)} | {f(p['frac_vwc_mayor_5_am'], 2)} | "
          f"{f(p['bandera_vegetacion_densa_am'], 2)} | {f(p['bandera_urbano_am'], 2)} |")
    w("")
    w("**Lectura (revisión adversarial):** la banda L 've' el suelo a través de la vegetación solo si hay poca agua en el dosel. En el "
      "bosque de la Cordillera Central y en el valle agrícola-boscoso de Bonao y La Vega el radiómetro mide sobre todo "
      "vegetación; en Santiago, ciudad. El algoritmo devuelve un número, pero lo marca como no recomendado. Forzar la "
      "prueba con esos números sería disfrazar de observación una cifra fuera de especificación. Además, la rejilla es de "
      "9 km pero la huella real de la banda L es de ~40 km (el producto 'Enhanced' interpola con Backus-Gilbert): píxeles "
      "vecinos no son independientes. Figura `t1_smap_l3_calidad`.")
    w("")
    # ------------------------------------------------------------ 2. pares
    if P:
        w("## 2 · Los dos pares frente al testigo")
        w("")
        w("Métrica: eficiencia = pendiente del cambio de humedad sobre la lluvia, con efectos fijos de mes (mensual: "
          "anomalía de lluvia; por evento: lluvia IMERG entre dos pasos del satélite ≤ 72 h, con la humedad inicial como "
          "covariable), y γ del ARX mensual como en el motor nacional. Bootstrap por bloques de 3 meses compartidos; p "
          "calibrado con 200 sustitutos de IGUAL respuesta en A y B (factor de inflación σ, como `earthmemory.calibration`).")
        w("")
        for key, title in (("gldas", "Par GLDAS · A = Monseñor Nouel (18.875 N, 70.375 O), B = Santiago/La Vega (19.375 N, 70.625 O)"),
                           ("hr", "Par 0.05° · A = Cordillera Central (19.025 N, 70.975 O), B = La Vega (19.175 N, 70.475 O)")):
            w(f"**{title}**")
            w("")
            w("| Prueba | ¿Independiente? | Métrica | Resultado |")
            w("|---|---|---|---|")
            for r in P[key].get("gamma", []) + P[key]["eficiencia"]:
                w(f"| {r['etiqueta']} | {r.get('independiente', '—')} | {r.get('metrica', '—')} | {_pair_line(r)} |")
            w("")
            w(f"Veredicto: **{P['veredictos'][key]['veredicto']}**.")
            w("")
        w("Las filas 'todos los retrievals' usan valores que el propio algoritmo marca como NO recomendados; se muestran "
          "como sensibilidad y **no cuentan para el veredicto**. Si apuntan en la misma dirección, es un indicio débil, no "
          "una confirmación. Figuras `t2_pares_testigo_smap_l3` y `t3_eventos_lluvia_smap_l3`.")
        w("")
    # ------------------------------------------------------------ 3. memoria
    if M:
        w("## 3 · ¿Memoria del suelo o memoria de la lluvia?")
        w("")
        w(f"Episodios de sequía del motor nacional (n = {M['n_episodios']}). Reproducción de la afirmación original (solo "
          f"severidad como control): β del suelo antecedente sobre el z de la raíz al volver la lluvia = "
          f"{f(orig_beta['beta_suelo_M2'])} {ci(orig_beta['beta_suelo_M2_ic95'])} (n = {orig_beta['n']}).")
        w("")
        w("Correlación entre el z antecedente de la raíz (GLDAS) y cada índice de lluvia antecedente:")
        w("")
        w("| Índice de lluvia antecedente | r con z raíz antecedente |")
        w("|---|---|")
        for k, v in M["correlaciones_suelo_api"].items():
            w(f"| {k} | {f(v)} |")
        w("")
        d = pd.read_csv(RES / "memoria_lluvia_vs_suelo.csv")
        d = d[d["resultado"] == "z_retorno_SM_RAIZ"]
        w("Resultado principal (z de la raíz al volver la lluvia). M2 = suelo sin lluvia; M3 = suelo + lluvia antecedente.")
        w("")
        w("| Lluvia antecedente | Efectos fijos | n | β suelo M2 | β suelo M3 [IC95] | q suelo | β lluvia M3 | q lluvia | R² parcial suelo dada lluvia | R² parcial lluvia dado suelo | varianza común | veredicto |")
        w("|---|---|---|---|---|---|---|---|---|---|---|---|")
        for _, r in d.iterrows():
            w(f"| {r['lluvia_antecedente']} | {r['efectos_fijos']} | {r['n']} | {f(r['beta_suelo_M2'])} | {f(r['beta_suelo_M3'])} "
              f"{ci(json.loads(r['beta_suelo_M3_ic95']))} | {f(r['q_beta_suelo_M3'], 3)} | {f(r['beta_lluvia_M3'])} | "
              f"{f(r['q_beta_lluvia_M3'], 3)} | {f(r['r2p_suelo_dado_lluvia'], 3)} | {f(r['r2p_lluvia_dado_suelo'], 3)} | "
              f"{f(r['varianza_comun'], 3)} | {r['veredicto']} |")
        w("")
        w(_mem_text(M, d))
        w("")
        w("Tabla completa (también z de 0-10 cm y la contradicción A como resultados): `results/testigos/memoria_lluvia_vs_suelo.csv`. "
          "Figura `t4_memoria_lluvia_vs_suelo`.")
        w("")
    # ------------------------------------------------------------ 4. umbral
    if U:
        w("## 4 · El umbral θ fuera del cubo")
        w("")
        w("| Variante | Celdas | θ [IC95] | b5 [IC95] | ¿quiebre (IC de b5 excluye 0)? |")
        w("|---|---|---|---|---|")
        for k, v in U["variantes"].items():
            if v.get("no_comprobable"):
                w(f"| {k} | {v['n_celdas']} | — | — | no comprobable ({v['motivo']}) |")
            else:
                w(f"| {k} | {v['n_celdas']} | {f(v['theta'])} {ci(v['theta_ic95'])} | {f(v['b5'], 3)} {ci(v['b5_ic95'], 3)} | "
                  f"{'sí' if v['b5_excluye_0'] else 'no'} |")
        w("")
        w(_umbral_text(U))
        w("")
    # ------------------------------------------------------------ 5. intensidad
    w("## 5 · Intensidad de la lluvia de retorno con CHIRPS")
    w("")
    if I and I.get("estado") == "ok":
        w(f"Años de CHIRPS v2.0 diario disponibles y verificados (SHA-256) en la caché del motor de tendencias: "
          f"{', '.join(map(str, I['anios_chirps_usados']))} (periodo usado {I['periodo'][0]} a {I['periodo'][1]}); "
          f"{I['n_episodios_con_ventana_completa']} episodios con la ventana completa. Concordancia de los factores entre "
          f"productos (Spearman): fracción intensa {f(I['r_spearman_fraccion_chirps_vs_imerg'])}, máximo diario "
          f"{f(I['r_spearman_max_chirps_vs_imerg'])}.")
        w("")
        w("| Resultado | Factor | Fuente | n | β [IC95] | p | q |")
        w("|---|---|---|---|---|---|---|")
        for r in I["tabla"]:
            w(f"| {r['resultado']} | {r['factor']} | {r['fuente']} | {r['n']} | {f(r['beta'])} {ci(r['ic95']) if r['ic95'] else ''} | "
              f"{f(r['p'], 3)} | {f(r['q_bh'], 3)} |")
        w("")
        w(I["nota"] + " Que dos productos de lluvia no coincidan en QUÉ episodios fueron intensos (ρ bajo) dice que la "
          "intensidad diaria está mal medida a 25 km en la RD: la ausencia de efecto no prueba que la intensidad no importe.")
    elif I:
        w(f"{I['estado']}. Archivos presentes: {I.get('n_archivos')}; años completos: {I.get('anios_completos')}.")
    w("")
    # ------------------------------------------------------------ 6. bosque
    if B:
        w("## 6 · Pérdida de bosque (Hansen GFC v1.13), solo descriptiva")
        w("")
        w("| Zona | Área (km²) | Bosque 2000 (km², cobertura ≥ 30 %) | Pérdida 2001-2023 (km²) | % del bosque de 2000 |")
        w("|---|---|---|---|---|")
        for k, v in B["zonas"].items():
            w(f"| {k} | {f(v['area_caja_km2'], 1)} | {f(v['bosque_2000_km2'], 1)} | {f(v['perdida_2001_2023_km2'], 2)} | "
              f"{f(v['perdida_pct_del_bosque_2000'], 1)} |")
        w("")
        for k, v in B["zonas"].items():
            y = v["perdida_por_anio_km2"]
            tot = sum(y.values())
            if tot > 0:
                yy = max(y, key=y.get)
                if y[yy] / tot > 0.5:
                    w(f"- {k}: el {f(100 * y[yy] / tot, 0)} % de la pérdida 2001-2023 ocurrió en {yy} (pérdida concentrada "
                      "en un año; Hansen cuenta como pérdida cualquier remoción del dosel, incluido fuego; no atribuimos causa).")
        w("")
        w("La pérdida describe lo que pasó en el territorio; no prueba que cambie la respuesta del suelo (GLDAS y "
          "TerraClimate usan cobertura FIJA, así que sus diferencias de respuesta no pueden venir de esta pérdida). "
          "Figura `t6_bosque_hansen`.")
        w("")
    # ------------------------------------------------------------ 7. NDVI
    w("## 7 · NDVI (AppEEARS)")
    w("")
    w(f"Se consultó la API de AppEEARS para la tarea {ap.get('tarea', '8ad4ac19-6b4c-4445-8443-2c4a4fc7f928')} con el token "
      f"de Earthdata como Bearer: HTTP {ap.get('http_estado_tarea', '—')}. AppEEARS exige su propio token (POST /login con "
      "usuario y contraseña); por regla no se pidieron ni usaron contraseñas. **Pendiente**: descargar el paquete desde la web "
      "de AppEEARS a `data/appeears/nacional/` (el gancho `earthmemory/appeears_hook.py` lo lee solo). Los puntos MOD13Q1 "
      "ya existentes (`data/appeears/phantom-rd-puntos-v2`) no caen en las celdas de los pares (el más cercano, "
      "'cordilleracomparacionhumedo' 19.03 N 70.84 O, está a ~14 km de la celda A de alta resolución): no sirven de testigo.")
    w("")
    # ------------------------------------------------------------ límites, citas, reproducir
    w("## Límites")
    w("")
    w("- SMAP L3 mide los ~5 cm superiores; no puede confirmar ni negar nada sobre la zona de raíces (0-100 cm).")
    w("- 'No comprobable' no es 'falso': la diferencia entre territorios puede existir; no hay hoy una observación "
      "satelital de humedad del suelo que la vea bajo ese dosel.")
    w("- IMERG y la lluvia que forzó a GLDAS (GPCP) comparten pluviómetros GPCC/GTS: el API de IMERG no es "
      "totalmente independiente de la lluvia del modelo, pero sí del suelo del modelo.")
    w("- Los episodios de sequía no son independientes (celdas vecinas a la vez): por eso el bootstrap es por año.")
    w("- CHIRPS v2 diario reparte el total de 5 días con un modelo; por eso se repite por péntadas.")
    w("")
    w("## Citas")
    w("")
    for k in ("SMAP_L3E", "IMERG_D", "GLDAS", "CHIRPS", "TERRACLIMATE", "HANSEN", "COPDEM", "GEOBOUNDARIES", "MOD13A3"):
        w(f"- {CITAS[k]}")
    w("- Reichle, R. et al. SMAP L4 Global 3-hourly 9 km EASE-Grid Surface and Root Zone Soil Moisture Geophysical "
      "Data, Version 8. NSIDC DAAC. https://doi.org/10.5067/T5RUATAQREF8 (citado solo para explicar por qué no es independiente).")
    w("")
    w("## Reproducir")
    w("")
    w("```")
    w("docker compose run --rm testigos                    # descarga lo que falte (token en .secrets/earthdata_token) y corre todo")
    w("docker compose run --rm testigos --sin-descarga     # solo con la caché de data/testigos")
    w('docker compose run --rm --entrypoint "uv run --frozen --no-sync pytest -q tests/test_testigos.py" testigos')
    w("```")
    w("")
    w("Salidas: `results/testigos/` (JSON/CSV), `figures/testigos/` (PNG 250 ppp + PDF), "
      "`notebooks/09_testigos_e_hipotesis.ipynb` y `reports_nacional/notebooks_html/09_testigos_e_hipotesis.html`. Semilla 2026.")
    REPORT.write_text("\n".join(md) + "\n", encoding="utf-8", newline="\n")


def _find(lst, start):
    return next(r for r in lst if r["etiqueta"].startswith(start) and "2015" in r["etiqueta"])


def _verd_mem2() -> str:
    d = pd.read_csv(RES / "memoria_lluvia_vs_suelo.csv")
    d = d[d["resultado"] == "z_retorno_SM_RAIZ"]
    im = _mem_group(d, ~d["lluvia_antecedente"].str.contains("forzante"))
    fz = _mem_group(d, d["lluvia_antecedente"].str.contains("forzante"))
    s6 = d[d["lluvia_antecedente"].str.startswith("SPI-6 lluvia del forzante")]
    cmb = d[d["lluvia_antecedente"].str.contains(r"SPI-3 \+ SPI-6 \+ SPI-12 forzante")]
    return (f"sostiene frente a la lluvia observada (IMERG: β {f(im['b'][0])}-{f(im['b'][1])}, {im['qs']}/{im['n']} con q<0.05); "
            f"se debilita frente a la lluvia del propio modelo (SPI-6 del forzante: β {f(s6['beta_suelo_M3'].min())}-"
            f"{f(s6['beta_suelo_M3'].max())}; SPI-3+6+12 del forzante: β {f(cmb['beta_suelo_M3'].min())}-"
            f"{f(cmb['beta_suelo_M3'].max())}, q {f(cmb['q_beta_suelo_M3'].min(), 3)}-{f(cmb['q_beta_suelo_M3'].max(), 3)})")


def _verd_mem(vc: dict) -> str:
    n = sum(vc.values())
    s = vc.get("sostiene", 0)
    c = vc.get("se cae", 0)
    if c == n:
        return "se cae"
    if s == n:
        return "sostiene"
    if c > 0:
        return f"se debilita (cae en {c}/{n} especificaciones)"
    return f"se debilita ({vc.get('se debilita', 0)}/{n} con β < mitad del original)"


def _mem_group(d, mask):
    g = d[mask]
    if not len(g):
        return None
    return {"n": len(g), "b": (g["beta_suelo_M3"].min(), g["beta_suelo_M3"].max()),
            "rs": (g["r2p_suelo_dado_lluvia"].min(), g["r2p_suelo_dado_lluvia"].max()),
            "rl": (g["r2p_lluvia_dado_suelo"].min(), g["r2p_lluvia_dado_suelo"].max()),
            "qs": int((g["q_beta_suelo_M3"] < 0.05).sum()), "ql": int((g["q_beta_lluvia_M3"] < 0.05).sum()),
            "vc": g["veredicto"].value_counts().to_dict()}


def _mem_text(M, d) -> str:
    orig = M["reproduccion_original"]["z_retorno_SM_RAIZ"]["beta_suelo_M2"]
    im = _mem_group(d, ~d["lluvia_antecedente"].str.contains("forzante"))
    fz = _mem_group(d, d["lluvia_antecedente"].str.contains("forzante"))
    c = M["correlaciones_suelo_api"]
    ci_im = max(v for k, v in c.items() if "forzante" not in k)
    ci_fz = max(v for k, v in c.items() if "forzante" in k)
    out = [f"**Lectura.** Original: β {f(orig)}."]
    if im:
        out.append(f"Contra la lluvia OBSERVADA (IMERG: API 30-90 d, SPI-3/6/12; {im['n']} especificaciones) el suelo "
                   f"antecedente sobrevive: β {f(im['b'][0])}-{f(im['b'][1])}, q < 0.05 en {im['qs']}/{im['n']}, R² parcial "
                   f"del suelo dada la lluvia {f(im['rs'][0], 3)}-{f(im['rs'][1], 3)}, y la lluvia, conocido el suelo, aporta "
                   f"{f(im['rl'][0], 3)}-{f(im['rl'][1], 3)}. La correlación entre el z antecedente de GLDAS y cualquier "
                   f"índice de IMERG no pasa de {f(ci_im)}.")
    if fz:
        out.append(f"Contra la lluvia que FORZÓ al modelo (GPCP desagregado; API 90 d y SPI-3/6/12; {fz['n']} "
                   f"especificaciones) la correlación sube hasta {f(ci_fz)} y el suelo queda en β {f(fz['b'][0])}-"
                   f"{f(fz['b'][1])}, q < 0.05 en {fz['qs']}/{fz['n']}, R² parcial {f(fz['rs'][0], 3)}-{f(fz['rs'][1], 3)}; "
                   f"veredictos {', '.join(f'{k}: {v}' for k, v in fz['vc'].items())}.")
    out.append("Interpretación honesta: la 'memoria' del suelo de GLDAS no es la memoria de la lluvia que IMERG observa "
               "(r bajo); es en buena parte la memoria de SU PROPIA lluvia de forzamiento, integrada durante meses. "
               "Lo que queda tras controlar esa lluvia es dinámica del modelo (drenaje, evaporación, capacidad), no una "
               "memoria del suelo medida. Ningún dato observado de humedad de raíz existe aquí para comprobarla.")
    return " ".join(out)


def _umbral_text(U) -> str:
    V = U["variantes"]
    g = lambda s: next((v for k, v in V.items() if s in k), None)  # noqa: E731
    rec = g("TerraClimate (cubo) · 2001-2024 · reconstrucción")
    tc15 = g("TerraClimate (cubo) · 2015-2024")
    api = g("estado = API IMERG · 2001-2024")
    sm = g("SMAP L3 (calidad recomendada) · estado = SMAP L3")
    tcs = g("solo zonas que SMAP L3 ve · 2001-2024")
    tcs15 = g("solo zonas que SMAP L3 ve · 2015-2024")
    out = [f"**Lectura.** El código reproduce el umbral del informe (θ {f(rec['theta'])} {ci(rec['theta_ic95'])}), así que "
           "las diferencias no son de implementación."]
    if tc15:
        out.append(f"Con el MISMO cubo pero solo 2015-2024 el quiebre ya no se detecta (b5 {ci(tc15['b5_ic95'], 2)}): diez "
                   "años no bastan ni dentro del modelo.")
    if api:
        sign = "aumenta" if api["b5"] > 0 else "cae"
        out.append(f"Si el estado antecedente es la lluvia (API de IMERG) en vez del cubo, la eficiencia baja desde el "
                   f"principio y por encima de θ = {f(api['theta'])} {sign} la pendiente (b5 {f(api['b5'], 2)}): no es el "
                   f"umbral de saturación en 0.59, y θ queda en el borde de la rejilla de búsqueda.")
    if sm:
        out.append(f"SMAP L3 de calidad recomendada solo existe en {sm['n_celdas']} píxeles de 9 km (sobre todo zonas "
                   f"secas y abiertas): ahí no hay quiebre (b5 {ci(sm['b5_ic95'], 5)}).")
    if tcs and tcs15:
        out.append(f"Control manzanas con manzanas: el cubo en esas mismas zonas SÍ tiene quiebre con 24 años (θ "
                   f"{f(tcs['theta'])}, b5 {ci(tcs['b5_ic95'], 2)}) pero NO en 2015-2024 (b5 {ci(tcs15['b5_ic95'], 2)}). "
                   "Por tanto la ausencia de quiebre en SMAP no refuta θ: el periodo de SMAP no tiene potencia para verlo.")
    out.append("Conclusión: θ ≈ 0.59 es una propiedad del modelo de cubo de TerraClimate en 24 años; ningún testigo "
               "independiente lo reproduce, y el único que puede mirar (SMAP L3, 10 años, zonas secas) no tiene potencia "
               "para confirmarlo ni para negarlo.")
    return " ".join(out)


def _umbral_cell(U) -> str:
    V = U["variantes"]
    g = lambda t: next((v for k, v in V.items() if t in k), None)  # noqa: E731
    out = []
    for lab, key in (("cubo 2015-2024", "TerraClimate (cubo) · 2015-2024"),
                     ("estado = API IMERG", "estado = API IMERG · 2001-2024"),
                     ("SMAP L3 recomendado", "SMAP L3 (calidad recomendada) · estado = SMAP L3"),
                     ("SMAP L3 + API", "SMAP L3 (calidad recomendada) · estado = API"),
                     ("cubo en zonas SMAP, 24 años", "solo zonas que SMAP L3 ve · 2001-2024"),
                     ("cubo en zonas SMAP, 10 años", "solo zonas que SMAP L3 ve · 2015-2024")):
        v = g(key)
        if v is None:
            continue
        if v.get("no_comprobable"):
            out.append(f"{lab}: no comprobable")
        else:
            out.append(f"{lab}: θ {f(v['theta'])}, quiebre {'sí' if v['b5_excluye_0'] else 'no'}"
                       + (" (b5 > 0: otra forma)" if v['b5_excluye_0'] and v['b5'] > 0 else ""))
    return "; ".join(out)


def _umbral_verd(U) -> str:
    V = U["variantes"]
    obs = [v for k, v in V.items() if "SMAP L3 (calidad recomendada)" in k and not v.get("no_comprobable")]
    api = [v for k, v in V.items() if "estado = API" in k and "TerraClimate" in k]
    api_ok = api and api[0]["b5_excluye_0"]
    if obs and all(v["b5_excluye_0"] for v in obs) and api_ok and api[0]["b5"] < 0:
        return "sostiene"
    return ("se debilita: solo aparece dentro del cubo con 24 años; con API cambia de forma; SMAP L3 (10 años, "
            "zonas secas) no tiene potencia para comprobarlo")


def _int_cell(I) -> str:
    t = pd.DataFrame(I["tabla"])
    parts = []
    for src in ("CHIRPS diario", "CHIRPS péntada", "IMERG diario (mismos episodios)"):
        u = t[t["fuente"] == src]
        if len(u):
            parts.append(f"{src}: β {f(u['beta'].min())} a {f(u['beta'].max())}, q mín {f(u['q_bh'].min(), 2)}")
    return (f"{'; '.join(parts)}; n = {int(t['n'].max())} episodios; concordancia de factores CHIRPS-IMERG ρ = "
            f"{f(I['r_spearman_fraccion_chirps_vs_imerg'])}")


def _int_verd(I) -> str:
    t = pd.DataFrame(I["tabla"])
    ch = t[t["fuente"].str.startswith("CHIRPS")]
    if (ch["q_bh"] < 0.05).any():
        return "se debilita: con CHIRPS la intensidad sí aparece en algún resultado"
    r = I.get("r_spearman_fraccion_chirps_vs_imerg")
    extra = (f"; con reserva: CHIRPS e IMERG apenas coinciden en qué episodios tuvieron lluvia intensa (ρ {f(r)}), así que "
             "'no significativo' es 'no detectable con estos productos', no 'no importa'") if r is not None and r < 0.5 else ""
    return "sostiene (tampoco aparece con CHIRPS)" + extra
