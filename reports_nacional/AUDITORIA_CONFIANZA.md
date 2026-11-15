# Auditoría de confianza · Evidence Intelligence (República Dominicana, 2001-2024)

*Stellar Horizons · NASA Space Apps 2026 · «Be An Earth System Trend Detective!». Generado por `earthmemory/auditoria/informe.py` desde la corrida; ningún número de este texto se escribió a mano.*

> **Pregunta:** ¿qué conclusión aparentemente correcta sobre sequías e inundaciones en RD podría resultar falsa al incluir la información que falta, y cuándo bastan los datos para actuar?
>
> Regla de lenguaje: no decimos que un satélite «miente». Distintas fuentes científicas pueden dar interpretaciones contradictorias del mismo territorio; el sistema investiga por qué.

## En corto

- **Ningún par de productos de lluvia es independiente.** IMERG Final, la lluvia que forzó a GLDAS-2.1 (GPCP) y SMAP L4 cuelgan de los pluviómetros de GPCC; CHIRPS mezcla las mismas estaciones dominicanas del GTS/GSOD (lista oficial mes a mes); MERRA-2 corregido cuelga de CPC Unified (también GTS). Que coincidan no es validación robusta.
- **La decisión de sequía cambia según el producto.** Por provincia y mes, de los casos en que al menos un producto declara sequía (SPI-3 ≤ −1), los cuatro productos no son unánimes en el **91 %** (IC 95 % 85 %-96 %; 2836 de 3111 casos). Con SPI-3 ≤ −1.5: 98 % (IC 97 %-100 %). Solo IMERG frente a CHIRPS: 67 %. Parte es efecto de umbral (productos a ambos lados de −1), pero en el **39 %** de los casos con alarma (IC 28 %-51 %) otro producto dice lo contrario: SPI-3 ≥ 0 (normal o húmedo). Solo en 275 de 3111 provincia-meses con alarma los cuatro coinciden en «sequía».
- **Provincias más sensibles al producto** (SPI-3 ≤ −1): Hato Mayor 97 % [94 %-100 %]; La Romana 96 % [92 %-100 %]; San Pedro de Macorís 96 % [92 %-99 %]; La Altagracia 96 % [91 %-100 %]; San Juan 95 % [91 %-99 %]. Los IC se solapan mucho: el orden entre provincias es frágil.
- **Disparador de inundación (> 100 mm en 48 h)**, IMERG frente a CHIRPS diario (2001-2014, AÑOS INCOMPLETOS): con el máximo de celda de cada provincia y ±1 día de tolerancia, 67 % de los disparos no los confirma el otro producto (IC 60 %-77 %; IMERG 2066 disparos, CHIRPS 3811). Con la media de provincia: 67 % (IMERG 579, CHIRPS 720).
- **'50 de 96' se reproduce** (50 de 96). Tras escala (0.5°), tiempo (±1 día, ±1 mes de retorno) y umbral, quedan **28 sin explicar** de 50.
- **Santo Domingo 18-nov-2023:** 431 mm (estación, NHC) frente a IMERG 140 mm en el día UTC; la mejor ventana de 24 h sube a 160 mm y la mejor celda vecina a 185 mm. Quedan 246 mm sin explicar por ventana ni escala; frente a la media de 11 pluviómetros de ONAMET publicados en prensa (336 mm) quedan 151 mm. Veredicto: **inconcluso** para repartir la brecha; **se sostiene** que un producto de 10 km no reproduce este extremo.

## 1 · Procedencia e independencia de cada producto

Verificado el 2026-11-14 contra la documentación oficial (ATBD, README, guías de usuario, artículos). V = escrito así en la fuente; I = inferido; NV = no verificado. Figura `figures/auditoria/fig01_procedencia.png`; tabla completa con URLs en `results/auditoria/procedencia_matriz.csv` y `procedencia.json`.

| Producto | Clase | Pluviómetros | Resolución | Versión | Fuente |
|---|---|---|---|---|---|
| GPM IMERG V07 Final (3IMERGHH/DF/M) | recuperación satelital ajustada con pluviómetros | GPCC (GTS SYNOP/CLIMAT + servicios nacionales + GHCN en Full Data) | 0.1°, 30 min; diario = día UTC | V07B | [1](https://gpm.nasa.gov/sites/default/files/2023-07/IMERG_TechnicalDocumentation_final_230713.pdf) · [2](https://gpm.nasa.gov/sites/default/files/2024-12/IMERG_V07_ReleaseNotes_241126.pdf) |
| CHIRPS v2.0 (mensual, péntada, diario) | recuperación satelital ajustada con pluviómetros | GTS + GSOD + GHCN (en RD: Puerto Plata, Santiago, Sabana de la Mar, Punta Cana, Barahona, Las Américas, Santo Domingo; lista oficial por mes) | 0.05°; péntada/mes (anclado a estaciones); diario redistribuido | 2.0 (final) | [1](https://doi.org/10.1038/sdata.2015.66) · [2](https://data.chc.ucsb.edu/products/CHIRPS/v2.0/README-CHIRPS.txt) · [3](https://data.chc.ucsb.edu/products/CHIRPS/v2.0/README-CHIRPS2-Daily.txt) · [4](https://data.chc.ucsb.edu/products/CHIRPS/v2.0/diagnostics/monthly_station_data/) |
| GLDAS-2.1 Noah 0.25° (incl. Rainf_f_tavg) | modelo forzado | Indirecto: GPCC (vía GPCP mensual) | 0.25°, 3 h / mensual | 2.1 | [1](https://hydro1.gesdisc.eosdis.nasa.gov/data/GLDAS/GLDAS_NOAH025_M.2.1/doc/README_GLDAS2.pdf) · [2](https://doi.org/10.1175/BAMS-85-3-381) · [3](https://www.ncei.noaa.gov/pub/data/sds/cdr/CDRs/Precipitation_GPCP-Daily/AlgorithmDescription_01B-35.pdf) |
| SMAP L4 SPL4SMGP V008 | modelo con asimilación | Indirecto: GPCC vía IMERG Final; CPCU en Norteamérica (si el Caribe entra: NV) | 9 km EASE-2, 3 h | V008 | [1](https://nsidc.org/sites/default/files/documents/user-guide/multi_spl4smau-v008-userguide.pdf) · [2](https://nsidc.org/data/spl4smgp/versions/8) |
| SMAP L3 SPL3SMP_E V6 (9 km mejorado) | recuperación satelital | ninguno | 9 km, diario (06 h y 18 h) | V6 | [1](https://nsidc.org/sites/default/files/documents/user-guide/spl3smp_e-v006-userguide.pdf) |
| TerraClimate v1.1 (servido hoy) | modelo forzado | solo en la climatología de fondo (CHELSA/WorldClim) y en ERA5 indirectamente | ~4 km, mensual | v1.1 | [1](https://doi.org/10.1038/sdata.2017.191) · [2](https://www.climatologylab.org/terraclimate.html) |
| MERRA-2 PRECTOTCORR vía NASA POWER | modelo con asimilación | CPCU (~30 000 estaciones: GTS, COOP, redes nacionales) | 0.5° × 0.625°, horario/diario | MERRA-2 / POWER v2 | [1](https://gmao.gsfc.nasa.gov/pubs/docs/Reichle734.pdf) · [2](https://ntrs.nasa.gov/api/citations/20170011571/downloads/20170011571.pdf) · [3](https://power.larc.nasa.gov/api/system/manager/parameters/PRECTOTCORR?community=AG) · [4](https://power.larc.nasa.gov/docs/methodology/) · [5](https://ftp.cpc.ncep.noaa.gov/precip/CPC_UNI_PRCP/GAUGE_GLB/DOCU/Chen_et_al_2008_JGR_Gauge_Algo.pdf) |
| GRACE/GRACE-FO JPL mascons RL06.3 v04 CRI | recuperación satelital | ninguno | rejilla 0.5°, resolución efectiva ~3° (> área de RD) | RL06.3 v04 | [1](https://grace.jpl.nasa.gov/data/get-data/jpl_global_mascons/) |
| MODIS MOD13A3 v061 (NDVI/EVI mensual) | recuperación satelital | ninguno | 1 km, mensual | v061 | [1](https://www.earthdata.nasa.gov/data/catalog/lpcloud-mod13a3-061) |
| MODIS MOD17A3HGF v061 (NPP anual) | modelo forzado | ninguno | 500 m, anual | v061 | [1](https://lpdaac.usgs.gov/documents/972/MOD17_User_Guide_V61.pdf) |
| GEOGLOWS v2 caudal | simulación hidrológica | ninguno directo | tramos de río, diario | v2 | [1](https://geoglows.ecmwf.int/about) |
| Estaciones GHCN-Daily / GSOD de RD (SYNOP) | observación in situ | es el pluviómetro | punto, diario | GHCN-D v3 | [1](https://www.ncei.noaa.gov/pub/data/ghcn/daily/readme.txt) · [2](https://www.ncei.noaa.gov/data/global-summary-of-the-day/doc/readme.txt) |

**Veredicto de independencia:**

- Ningún par de productos de LLUVIA de esta lista es independiente: IMERG Final, la lluvia de GLDAS-2.1 (GPCP) y SMAP L4 cuelgan de GPCC; CHIRPS mezcla las mismas estaciones SYNOP/GSOD dominicanas; MERRA-2 corregido cuelga de CPC Unified, que también usa el GTS. Su acuerdo no es una confirmación independiente.
- SMAP L4 (zona de raíces) es un modelo con asimilación cuya lluvia se corrige con IMERG: no confirma a GLDAS ni a IMERG. SMAP L3 (0-5 cm) es el testigo más observacional del suelo, pero solo de la superficie.
- CHIRPS diario no es un dato diario independiente: reparte la péntada con el CFSv2. Para disparadores diarios solo la suma de 5 días está anclada a estaciones.
- GRACE-FO es el único independiente en lluvia, pero su resolución (~3°) es mayor que el país.
- Las estaciones GHCN-D/GSOD de RD sirven de verdad de terreno solo con la circularidad marcada: entran en CHIRPS (verificado mes a mes) y muy probablemente en GPCC/CPCU (vía GTS).

Pares que pueden compartir errores (insumo común):

- IMERG ↔ GLDAS_forzamiento: GPCC (vía GPCP mensual) (V)
- IMERG ↔ SMAP_L4: IMERG Final corrige la lluvia de L4 (V)
- IMERG ↔ CHIRPS: IR CPC + calibración CCD con TMPA (predecesor ajustado a GPCC) (V)
- CHIRPS ↔ Estaciones: mismas estaciones GTS/GSOD en la mezcla (lista oficial) (V)
- IMERG ↔ Estaciones: GPCC usa SYNOP del GTS (I)
- MERRA2 ↔ Estaciones: CPCU usa SYNOP del GTS (I)
- IMERG ↔ MERRA2: morphing con campos de MERRA-2 (V)
- SMAP_L4 ↔ SMAP_L3: mismas Tb SMAP (V)
- SMAP_L4 ↔ MERRA2: sistema GEOS (V)
- CHIRPS ↔ GLDAS_forzamiento: familia NCEP (CFSv2 / GDAS) (I)
- TerraClimate ↔ GEOGLOWS: ERA5 (V)
- IMERG ↔ TerraClimate: ERA5 (V)
- MOD13A3 ↔ MOD17: reflectancia MODIS (I)

Correcciones respecto a borradores anteriores: CHIRPS v2 diario reparte la péntada con el **CFSv2** (README-CHIRPS2-Daily); el uso de IMERG Late para el reparto diario es de **CHIRPS v3 'sat'**, no de v2. SMAP L4 V008 corrige su lluvia con **IMERG V07 Final** fuera de Norteamérica (la nota de versión indica que el procesamiento más reciente lo deja de hacer). MOD17A3HGF es de 500 m y usa meteorología GEOS-5 de GMAO. TerraClimate v1.1 usa ERA5 + CHELSA, no CRU/JRA-55. El tramo reciente de NASA POWER viene de GEOS FP-IT, no de MERRA-2.

## 2 · Verdad de terreno, con la circularidad marcada

- GHCN-Daily tiene **5 estaciones con prefijo DR**; con datos 2001-2024 solo 4 (Santo Domingo 78486, Puerto Plata 78458, Punta Cana 78479, Barahona 78482), todas derivadas de informes SYNOP (fuente 'S' = GSOD). Se añadieron las estaciones sinópticas OMM de RD en GSOD con 24 h completas (banderas D/F/G). Total usado: **8 estaciones** (`results/auditoria/estaciones_meta.csv`).
- **Circularidad verificada:** 6 de 8 estaciones aparecen en la lista oficial de estaciones de CHIRPS v2 en más de la mitad de los meses (mediana 95 % de los meses). Todas son sinópticas del GTS: es **probable** (no comprobable con listas públicas por estación) que entren en GPCC (ajuste mensual de IMERG Final) y en CPC Unified (corrección de MERRA-2). Su acuerdo con los productos es en parte acuerdo consigo mismos.
- **Desfase de un día:** el mejor desfase diario fue +1 día (la estación fecha el aguacero un día después) en 11 de 22 combinaciones estación × producto; 0 días en 11; −1 en 0. GSOD resume en día UTC, pero el acumulado de 24 h del SYNOP no termina a medianoche.

Medianas entre estaciones, escala diaria (`estaciones_validacion_diaria.csv`):

| Producto | r diaria (desfase 0) | r diaria (mejor desfase) | KGE diaria | sesgo | POD ≥50 | FAR ≥50 | CSI ≥50 | POD ≥100 | CSI ≥100 | p99 obs / prod (mm) |
|---|---|---|---|---|---|---|---|---|---|---|
| IMERG V07 Final | 0.36 | 0.42 | 0.40 | 0 % | 0.25 | 0.74 | 0.14 | 0.21 | 0.11 | 106 / 91 |
| CHIRPS v2.0 | 0.30 | 0.30 | 0.20 | -10 % | 0.13 | 0.81 | 0.09 | 0.03 | 0.01 | 100 / 98 |
| MERRA-2 PRECTOTCORR (NASA POWER) | 0.25 | 0.34 | -0.06 | -51 % | 0.02 | 0.85 | 0.01 | 0.00 | 0.00 | 106 / 38 |

Escala mensual (meses con ≥ 90 % de días; `estaciones_validacion_mensual.csv`):

| Producto | r mensual | KGE mensual | sesgo |
|---|---|---|---|
| IMERG V07 Final | 0.79 | 0.62 | -13 % |
| CHIRPS v2.0 | 0.67 | 0.55 | -17 % |
| Lluvia de forzamiento GLDAS-2.1 (GPCP) | 0.65 | 0.42 | -24 % |
| MERRA-2 PRECTOTCORR (NASA POWER) | 0.51 | 0.07 | -60 % |

- **Prueba directa de circularidad (mensual):** CHIRPS frente a la estación, r mediana 0.70 en los meses en que la estación entró en CHIRPS (228 estación-meses) y 0.65 cuando no entró (114). Control con IMERG en los mismos meses: 0.78 y 0.79. Si CHIRPS mejora al ingerir la estación y IMERG no, ese acuerdo de CHIRPS no es evidencia independiente. Con tan pocos meses sin ingesta, la prueba es débil (estaciones con n < 30 meses no se informan).
- **Punto frente a celda:** la lluvia media anual de las 9 celdas IMERG alrededor de cada estación varía en mediana 161 mm/año entre la celda más seca y la más húmeda (`estaciones_dispersion_vecinas.csv`).
- En los 165 días con ≥ 100 mm en una estación (comparando con el día UTC anterior de IMERG), la más lluviosa de las 9 celdas vecinas quedó por debajo de la estación en 146.

## 3 · Re-auditoría de «50 de 96 episodios = posible diferencia entre productos»

**Definición exacta (código del motor nacional):**

Re-auditoría de "50 de 96 episodios = posible diferencia entre productos".

Definición exacta en el código del motor nacional (earthmemory/episodes.py + nacional.match_episodes_across_products):
- Celda = celda GLDAS 0.25° incluida (65). Lluvia = IMERG mensual remapeada de forma conservativa a la celda.
- Episodio = racha de SPI-3 <= −1 durante >= 2 meses. Retorno = primer mes posterior con SPI-3 >= 0 (antes
  del siguiente episodio).
- Contradicción A (raíz) = z robusto de la humedad de la zona de raíces GLDAS < −1 en el mes de retorno y el
  siguiente.
- Etiqueta: se repite TODO con la lluvia que forzó a GLDAS-2.1 (Rainf_f_tavg, GPCP 1DD desagregado). Si en la
  misma celda hay un episodio de esa lluvia que se solapa (±2 meses) y también es contradicción A → "también con
  la lluvia del modelo"; si no → "posible diferencia entre productos". OJO: la humedad del suelo es la MISMA serie
  en las dos ramas; la etiqueta solo cambia por la lluvia (¿hubo sequía? ¿en qué mes volvió?).

**Reproducción:** original 50/96; recalculado 50/96.

| Causa probada | Episodios que explica (de 50, no excluyentes) | Atribución en orden a→b→c |
|---|---|---|
| (a) escala: recuento a 0.5° | 14 | 14 |
| (b) tiempo: ±1 día en el mensual (7) o retorno a ±1 mes (3) | 9 | 2 |
| (c) variable/umbral: aparece con umbrales relajados o el modelo quedó cerca del umbral | 12 | 6 |
| **sin explicar** | — | **28** |

- Recuentos a otras escalas/rutas: a 0.5° hay 28 contradicciones A y 16 'posible diferencia' (23 bloques). IMERG mensual rehecho desde el diario: desplazamiento 0 d → 58/111; desplazamiento -1 d → 61/113; desplazamiento 1 d → 56/112.
- **Tercer producto (CHIRPS a 0.25°):** de los 50, CHIRPS reproduce la contradicción de IMERG en 5; de los 28 sin explicar, en 2. Con CHIRPS como lluvia hay 94 contradicciones A en total. Recordatorio: CHIRPS e IMERG comparten IR e insumos de pluviómetros; que coincidan no prueba que la lluvia del modelo esté mal.
- **(c) es estructural:** la humedad del suelo es la MISMA serie en las dos ramas. Toda la diferencia viene de la lluvia (si hubo sequía y en qué mes volvió). No es un desacuerdo entre suelo y lluvia, sino entre dos lluvias.

(d) Relieve y costa (ρ de Spearman por celda; p calibrado con desplazamientos toroidales del campo de la covariable):

| resultado | covariable | n_celdas | rho_spearman | p_nominal | p_toroidal |
|---|---|---|---|---|---|
| desacuerdo_spi3_imerg_vs_modelo | elevacion_m | 65 | 0.39 | 0.001 | 0.207 |
| desacuerdo_spi3_imerg_vs_modelo | pendiente_grados | 65 | 0.29 | 0.019 | 0.316 |
| desacuerdo_spi3_imerg_vs_modelo | dist_costa_km | 65 | 0.30 | 0.015 | 0.190 |
| n_posible_diferencia | elevacion_m | 65 | 0.16 | 0.205 | 0.389 |
| n_posible_diferencia | pendiente_grados | 65 | 0.14 | 0.258 | 0.612 |
| n_posible_diferencia | dist_costa_km | 65 | 0.14 | 0.257 | 0.285 |
| n_sin_explicar | elevacion_m | 65 | 0.01 | 0.935 | 0.931 |
| n_sin_explicar | pendiente_grados | 65 | -0.05 | 0.674 | 0.756 |
| n_sin_explicar | dist_costa_km | 65 | 0.14 | 0.282 | 0.516 |

(e) Persistencia: máxima fracción anual de 'posible diferencia' 1.00 (p por permutación 0.141); celdas con ≥ 2 episodios 'posible diferencia': 11 (p 0.954).

(f) Representatividad (fracción marcada por categoría; χ² con p por permutación):

| variable | comparacion | categoria | n_base | n_marcados | fraccion | chi2 | p_perm |
|---|---|---|---|---|---|---|---|
| region | A vs todos con retorno | este/sureste | 241 | 42 | 0.17 | 5.6 | 0.064 |
| region | A vs todos con retorno | norte (Cibao) | 129 | 12 | 0.09 | 5.6 | 0.064 |
| region | A vs todos con retorno | oeste/suroeste | 344 | 42 | 0.12 | 5.6 | 0.064 |
| region | posible diferencia vs A | este/sureste | 42 | 17 | 0.40 | 4.2 | 0.132 |
| region | posible diferencia vs A | norte (Cibao) | 12 | 8 | 0.67 | 4.2 | 0.132 |
| region | posible diferencia vs A | oeste/suroeste | 42 | 25 | 0.60 | 4.2 | 0.132 |
| temporada | A vs todos con retorno | primera AMJJ | 230 | 9 | 0.04 | 26.6 | 0.001 |
| temporada | A vs todos con retorno | seca DEFM | 290 | 51 | 0.18 | 26.6 | 0.001 |
| temporada | A vs todos con retorno | segunda ASON | 194 | 36 | 0.19 | 26.6 | 0.001 |
| temporada | posible diferencia vs A | primera AMJJ | 9 | 5 | 0.56 | 2.2 | 0.324 |
| temporada | posible diferencia vs A | seca DEFM | 51 | 23 | 0.45 | 2.2 | 0.324 |
| temporada | posible diferencia vs A | segunda ASON | 36 | 22 | 0.61 | 2.2 | 0.324 |
| enso | A vs todos con retorno | El Niño | 242 | 39 | 0.16 | 15.6 | 0.001 |
| enso | A vs todos con retorno | La Niña | 118 | 26 | 0.22 | 15.6 | 0.001 |
| enso | A vs todos con retorno | neutro | 354 | 31 | 0.09 | 15.6 | 0.001 |
| enso | posible diferencia vs A | El Niño | 39 | 22 | 0.56 | 6.9 | 0.029 |
| enso | posible diferencia vs A | La Niña | 26 | 8 | 0.31 | 6.9 | 0.029 |
| enso | posible diferencia vs A | neutro | 31 | 20 | 0.65 | 6.9 | 0.029 |

## 4 · Tasa de cambio de decisión (el resultado central)

Por provincia (32 unidades ADM1, media ponderada por área sobre una rejilla común 0.05°) y mes, 2001-2024. SPI-3 de cada producto con su propia climatología. Tasa condicional = de los casos en que al menos un producto declara sequía, fracción sin unanimidad. IC 95 % por bootstrap de bloques de año (2 000 réplicas). Como los productos comparten insumos, **esta tasa es un mínimo** de la incertidumbre de decisión real.

| umbral_spi3 | productos | n_casos | n_alguna_alarma | n_no_unanime | tasa global | tasa condicional |
|---|---|---|---|---|---|---|
| -1.0 | 4 productos | 9152 | 3111 | 2836 | 31.0 % [23.6 %-38.4 %] | 91.2 % [84.9 %-96.3 %] |
| -1.0 | IMERG vs CHIRPS | 9152 | 2245 | 1498 | 16.4 % [12.4 %-20.4 %] | 66.7 % [56.9 %-78.5 %] |
| -1.0 | 3 sin MERRA-2 | 9152 | 2636 | 2000 | 21.9 % [16.6 %-27.4 %] | 75.9 % [67.0 %-85.9 %] |
| -1.5 | 4 productos | 9152 | 1419 | 1396 | 15.3 % [9.5 %-21.3 %] | 98.4 % [96.8 %-99.6 %] |
| -1.5 | IMERG vs CHIRPS | 9152 | 897 | 660 | 7.2 % [4.6 %-9.8 %] | 73.6 % [64.9 %-86.3 %] |
| -1.5 | 3 sin MERRA-2 | 9152 | 1182 | 1003 | 11.0 % [6.9 %-15.1 %] | 84.9 % [78.8 %-93.0 %] |

**¿Cuándo bastan los datos para actuar?** Los provincia-meses en que los cuatro productos coinciden en «sequía» se concentran en pocos años: 2015: 93 de 224 con alarma; 2009: 42 de 145 con alarma; 2019: 32 de 265 con alarma; 2014: 26 de 252 con alarma (`cambio_decision_sequia_por_anio.csv`).

Provincias, SPI-3 ≤ −1 (5 más y 3 menos sensibles; tabla completa en `cambio_decision_sequia_provincias.csv`):

| Provincia | tasa condicional [IC 95 %] | meses en sequía IMERG/CHIRPS/GLDAS/MERRA-2 |
|---|---|---|
| Hato Mayor | 97 % [94 %-100 %] | 43/47/48/36 |
| La Romana | 96 % [92 %-100 %] | 55/48/50/38 |
| San Pedro de Macorís | 96 % [92 %-99 %] | 49/45/54/36 |
| La Altagracia | 96 % [91 %-100 %] | 50/47/50/36 |
| San Juan | 95 % [91 %-99 %] | 44/47/50/41 |
| María Trinidad Sánchez | 86 % [73 %-96 %] | 48/50/52/50 |
| Hermanas | 86 % [74 %-96 %] | 49/47/52/49 |
| Puerto Plata | 86 % [74 %-95 %] | 49/50/53/50 |

Por pares (1 − Jaccard de los meses-provincia en sequía):

| A | B | desacuerdo [IC 95 %] |
|---|---|---|
| IMERG | CHIRPS | 67 % [57 %-78 %] |
| IMERG | GLDAS_forzamiento | 52 % [45 %-60 %] |
| IMERG | MERRA2 | 71 % [63 %-82 %] |
| CHIRPS | GLDAS_forzamiento | 62 % [50 %-77 %] |
| CHIRPS | MERRA2 | 77 % [66 %-88 %] |
| GLDAS_forzamiento | MERRA2 | 75 % [66 %-86 %] |

**Disparador de inundación > 100 mm en 48 h** (IMERG frente a CHIRPS diario, 2001-2014, 4747 días; años INCOMPLETOS: resultado parcial). El sEAP de la Cruz Roja Dominicana (MDRDO020) usa un boletín de INDOMET con > 100 mm en 2 días asociado a ciclón tropical (pronóstico, no satélite); aquí se usa solo el umbral como prueba de sensibilidad, no se reproduce el protocolo.

| escala | desplazamiento_imerg_dias | tolerancia_dias | n_A | n_B | A_confirmado_por_B | B_confirmado_por_A | tasa | IC 95 % |
|---|---|---|---|---|---|---|---|---|
| media_provincia | 0 | 0 | 579 | 720 | 181 | 181 | 72 % | 63 %-85 % |
| media_provincia | 0 | 1 | 579 | 720 | 208 | 226 | 67 % | 55 %-82 % |
| maximo_celda | 0 | 0 | 2066 | 3811 | 747 | 747 | 75 % | 69 %-83 % |
| maximo_celda | 0 | 1 | 2066 | 3811 | 882 | 1067 | 67 % | 60 %-77 % |
| media_provincia | -1 | 0 | 579 | 720 | 88 | 88 | 86 % | 82 %-93 % |
| media_provincia | -1 | 1 | 579 | 720 | 196 | 211 | 69 % | 58 %-83 % |
| maximo_celda | -1 | 0 | 2066 | 3811 | 476 | 476 | 84 % | 81 %-89 % |
| maximo_celda | -1 | 1 | 2066 | 3811 | 846 | 960 | 69 % | 63 %-78 % |
| media_provincia | 1 | 0 | 579 | 720 | 82 | 82 | 87 % | 81 %-95 % |
| media_provincia | 1 | 1 | 579 | 720 | 193 | 203 | 70 % | 59 %-84 % |
| maximo_celda | 1 | 0 | 2066 | 3809 | 498 | 498 | 83 % | 79 %-89 % |
| maximo_celda | 1 | 1 | 2066 | 3809 | 836 | 984 | 69 % | 63 %-78 % |

n_A = disparos IMERG, n_B = disparos CHIRPS (provincia-día). Recordatorio: el día de CHIRPS v2 es una redistribución con el CFSv2.

## 5 · Santo Domingo, 18 de noviembre de 2023

- **Fuente de la estación:** NHC, Tropical Cyclone Report AL222023 (Hagen, 28-feb-2024): pluviómetro en Arroyo Hondo Viejo, «16.97 inches (431 mm) during the 24-h period ending on 18 November» y 482.5 mm en 16-19 nov (https://www.nhc.noaa.gov/data/tcr/AL222023_Twenty-Two.pdf). ONAMET vía prensa (Listín Diario 21-nov-2023; Diario Libre 19-nov-2023). **La ventana exacta de 24 h NO está publicada**; la prensa sitúa lo peor la tarde del sábado 18 (hora local). La cifra de 474 mm «desde el jueves» solo aparece en prensa de 2026; el NHC da 482.5 mm (16-19 nov).
- **GHCN-D Santo Domingo (DRM00078486, SYNOP):** 2023-11-16: — mm, 2023-11-17: — mm, 2023-11-18: 9.7 mm, 2023-11-19: 313.2 mm, 2023-11-20: 0.0 mm, 2023-11-21: — mm. El aguacero aparece fechado el 19: la ventana del SYNOP termina por la mañana del día siguiente.

| ventana | inicio_utc | fin_utc | imerg_celda_mm | imerg_vecinas_max_mm | imerg_vecinas_media_mm |
|---|---|---|---|---|---|
| día UTC 18-nov (00-24 UTC) | 2023-11-18T00:00 | 2023-11-19T00:00 | 140 | 170 | 128 |
| día civil local 18-nov (04 UTC 18 → 04 UTC 19) | 2023-11-18T04:00 | 2023-11-19T04:00 | 157 | 182 | 146 |
| 24 h que terminan 12 UTC 18-nov (SYNOP, 08 h local) | 2023-11-17T12:00 | 2023-11-18T12:00 | 26 | 48 | 28 |
| 24 h que terminan 12 UTC 19-nov (SYNOP fechado 19) | 2023-11-18T12:00 | 2023-11-19T12:00 | 159 | 179 | 150 |
| 07-07 local que termina el 19 (11 UTC 18 → 11 UTC 19) | 2023-11-18T11:00 | 2023-11-19T11:00 | 159 | 180 | 150 |
| máximo de 24 h móviles (17-19 nov) | 2023-11-18 10:00:00 | 2023-11-19 10:00:00 | 160 | 185 | 153 |

- CHIRPS v2.0 diario 0.05°: celda 86 mm el 18 y 62 mm el 19; mejor celda vecina 18+19: 148 mm (día redistribuido con CFSv2).
- Celda IMERG usada: centro 18.45 N, -69.95 (la coordenada de la estación no es pública; se usó el centroide aproximado del barrio, 18.495 N, −69.948).
- **Descomposición:** brecha total 291 mm = ventana 20 mm + escala (mejor de 9 celdas) 25 mm + **resto 246 mm**. Usar la media de 11 pluviómetros de ONAMET como aproximación del área (prensa, sin coordenadas ni ventana) deja 151 mm.
- **Veredicto: inconcluso** para atribuir la brecha (ventana y coordenada desconocidas). **Se sostiene** que ni IMERG ni CHIRPS reproducen el extremo puntual, incluso con la ventana y la celda más favorables.

## 6 · Prototipo «dónde medir después» (PRELIMINAR)

Índice por celda 0.1° = media de rangos percentiles de: desacuerdo persistente (1 − r de SPI-3 IMERG/CHIRPS), persistencia (fracción de años con algún mes de cambio de decisión), tasa de cambio condicional (SPI-3 ≤ −1, 4 productos) y distancia a la estación GHCN-D activa más cercana. **No prueba dónde deben ir estaciones.** Faltan: acceso y seguridad del sitio, exposición del pluviómetro, población y bienes expuestos, la red real de ONAMET/INDRHI (no está en GHCN-D) y el valor de cada sitio para las decisiones de quien actúa. El CIMH reconoce que las Antillas Mayores están poco representadas por estaciones en su monitoreo regional (https://rcc.cimh.edu.bb/spi-monitor/).

| lat | lon | provincia | índice | sin distancia | km a GHCN-D activa |
|---|---|---|---|---|---|
| 18.95 | -71.65 | La Estrelleta | 0.92 | 0.94 | 145 |
| 18.85 | -71.55 | San Juan | 0.90 | 0.92 | 145 |
| 19.05 | -71.45 | San Juan | 0.88 | 0.92 | 122 |
| 18.85 | -71.45 | San Juan | 0.88 | 0.89 | 137 |
| 18.95 | -71.75 | La Estrelleta | 0.87 | 0.87 | 154 |
| 19.05 | -71.75 | La Estrelleta | 0.87 | 0.88 | 147 |
| 18.85 | -71.65 | La Estrelleta | 0.87 | 0.87 | 152 |
| 18.95 | -71.45 | San Juan | 0.87 | 0.89 | 129 |
| 18.25 | -71.65 | Pedernales | 0.87 | 0.83 | 190 |
| 17.95 | -71.45 | Pedernales | 0.85 | 0.82 | 177 |

## Lo que sabemos

- Los productos de lluvia que usamos no son independientes entre sí: comparten pluviómetros (GPCC, GTS, CPC Unified), IR geoestacionario y sistemas de modelo (verificado en su documentación).
- La decisión «hay sequía» en una provincia cambia según el producto en 91 % de los casos con alguna alarma (IC 85 %-96 %), y eso con productos que comparten insumos.
- Las estaciones dominicanas de GHCN-D/GSOD entran en la mezcla de CHIRPS (lista oficial): la validación con ellas es parcialmente circular.
- La contradicción «volvió la lluvia, el suelo no» de GLDAS depende de qué lluvia se use; el suelo es el mismo en las dos ramas.
- En Santo Domingo (18-nov-2023) ningún producto de 5-10 km llega al acumulado puntual, aun con la ventana y celda más favorables.

## Lo que creemos saber

- Que las provincias más sensibles al producto son Hato Mayor, La Romana, San Pedro de Macorís: los IC se solapan con los de muchas otras.
- Que 28 de los 50 episodios 'posible diferencia' reflejan un desacuerdo real entre la lluvia IMERG y la que forzó a GLDAS (no de escala, día o umbral); no sabemos cuál de las dos lluvias está más cerca de la verdad.
- Que el desfase de un día entre estaciones SYNOP y productos en día UTC es la norma (mejor correlación con +1 día).
- Que el desacuerdo crece o no con el relieve y la costa: ver p calibrados en la sección 3 (con 65 celdas, la potencia es baja).

## Lo que todavía hay que comprobar

- La ventana exacta y la coordenada del pluviómetro de Arroyo Hondo Viejo (boletín original de ONAMET/INDOMET).
- La lista de estaciones de GPCC y CPC Unified en RD (no pública por estación): ¿cuánto de la validación es circular para IMERG y MERRA-2?
- Datos de la red densa de ONAMET e INDRHI (no están en GHCN-D) para una validación no circular.
- SMAP L3 (0-5 cm) como testigo del suelo en los 50 episodios (otro motor del equipo lo trabaja).
- Si el disparador real del sEAP (boletín de INDOMET con pronóstico) diverge igual que los productos satelitales.
- El disparador de 48 h con CHIRPS diario completo 2001-2024 (esta corrida usó 13 años).

## Limitaciones

- CHIRPS diario es una redistribución con el CFSv2 de la péntada; las comparaciones diarias con CHIRPS miden también esa redistribución.
- MERRA-2 se lleva a 0.05° con la celda POWER que contiene cada subcelda (0.5° × 0.625°): las provincias pequeñas quedan dentro de 1-2 celdas.
- Las tasas de cambio de decisión dependen del umbral y del índice (SPI-3, gamma por mes calendario, 2001-2024 como referencia).
- Las cifras de prensa de ONAMET no tienen coordenadas ni ventana; se usan solo como orden de magnitud y van marcadas.
- Ninguna asociación aquí es causa. Ningún dato es sintético salvo en `tests/test_auditoria.py` (etiquetado).

## Reproducir

```
docker compose run --rm auditoria
# pruebas:
docker compose run --rm --entrypoint "uv run --frozen --no-sync pytest -q tests/test_auditoria.py" auditoria
```

Descargas crudas (GHCN-D, GSOD, listas de estaciones de CHIRPS, ONI, OSCAR) en `data/auditoria/` con URL, fecha, SHA-256 y licencia en `data/auditoria/MANIFEST.json`. Salidas: `results/auditoria/` (CSV/JSON y `web/` con `CONTRATO.md`), `figures/auditoria/` (PNG 300 dpi + PDF + JSON de procedencia), `notebooks/07_auditoria_de_confianza.ipynb` y su HTML.

## Figuras

- `figures/auditoria/fig01_procedencia.png` / `.pdf`
- `figures/auditoria/fig02_estaciones.png` / `.pdf`
- `figures/auditoria/fig03_reauditoria_50_96.png` / `.pdf`
- `figures/auditoria/fig04_cambio_decision_sequia.png` / `.pdf`
- `figures/auditoria/fig05_cambio_decision_inundacion.png` / `.pdf`
- `figures/auditoria/fig06_santo_domingo.png` / `.pdf`
- `figures/auditoria/fig07_donde_medir_prototipo.png` / `.pdf`

## Citas

- Huffman, G.J. et al. (2023). IMERG V07 Technical Documentation. NASA GSFC. https://gpm.nasa.gov/sites/default/files/2023-07/IMERG_TechnicalDocumentation_final_230713.pdf
- Funk, C. et al. (2015). The climate hazards infrared precipitation with stations. Sci. Data 2, 150066. doi:10.1038/sdata.2015.66
- CHC (s.f.). README-CHIRPS2-Daily. https://data.chc.ucsb.edu/products/CHIRPS/v2.0/README-CHIRPS2-Daily.txt
- Rodell, M. et al. (2004). The Global Land Data Assimilation System. BAMS 85, 381-394. doi:10.1175/BAMS-85-3-381; README GLDAS-2: https://hydro1.gesdisc.eosdis.nasa.gov/data/GLDAS/GLDAS_NOAH025_M.2.1/doc/README_GLDAS2.pdf
- Reichle, R. et al. SMAP L4 Surface and Root-Zone Soil Moisture, User Guide V008. NSIDC. https://nsidc.org/sites/default/files/documents/user-guide/multi_spl4smau-v008-userguide.pdf
- O'Neill, P. et al. SMAP Enhanced L3 Radiometer Soil Moisture V6, User Guide. NSIDC. https://nsidc.org/sites/default/files/documents/user-guide/spl3smp_e-v006-userguide.pdf
- Abatzoglou, J.T. et al. (2018). TerraClimate. Sci. Data 5, 170191. doi:10.1038/sdata.2017.191
- Gelaro, R. et al. (2017). MERRA-2. J. Climate 30, 5419-5454. doi:10.1175/JCLI-D-16-0758.1
- Reichle, R. et al. (2017). Land surface precipitation in MERRA-2. J. Climate 30, 1643-1664. doi:10.1175/JCLI-D-16-0570.1
- Chen, M. et al. (2008). Assessing objective techniques for gauge-based analyses of global daily precipitation. JGR 113, D04110.
- Schneider, U. et al. GPCC products v2022 (DWD). https://opendata.dwd.de/climate_environment/GPCC/PDF/GPCC_intro_products_v2022.pdf
- Watkins, M. et al. (2015). Improved methods for observing Earth's time variable mass distribution with GRACE. JGR 120. doi:10.1002/2014JB011547
- Menne, M.J. et al. (2012). An overview of the GHCN-Daily database. JTECH 29, 897-910. doi:10.1175/JTECH-D-11-00103.1; doi:10.7289/V5D21VHZ
- Hagen, A. (2024). Tropical Cyclone Report: Potential Tropical Cyclone Twenty-Two (AL222023). NHC. https://www.nhc.noaa.gov/data/tcr/AL222023_Twenty-Two.pdf
- IFRC (2026). Simplified EAP Dominican Republic MDRDO020. https://go-api.ifrc.org/api/DownloadFile/94311/MDRDO020%20sEAP%20Summary
- Gupta, H.V. et al. (2009). Decomposition of the mean squared error and NSE performance criteria (KGE). J. Hydrol. 377, 80-91.
- NOAA CPC. Oceanic Niño Index (ONI). https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt
- WMO OSCAR/Surface, estaciones de RD. https://oscar.wmo.int/surface/
