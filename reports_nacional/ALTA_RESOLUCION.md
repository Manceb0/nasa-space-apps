# Earth Memory · Alta resolución y umbrales críticos (República Dominicana, 2001-2024)

*Stellar Horizons · NASA Space Apps 2026 · «Be An Earth System Trend Detective!». Generado por `earthmemory/hr/report.py` desde `results/nacional_hr/resumen.json`; ningún número de este texto se escribió a mano.*

## En corto

- **Más fino y verificable.** 1649 celdas de 0.05° (~5.3 km) cubren la RD; a igual área (48,232 km²) serían ≈ 13 celdas de NASA POWER (0.5° × 0.625°) y ≈ 66 de GLDAS (0.25°). Se descargaron 4048 archivos (332 MB), cada uno con su URL y SHA-256 en `data/nacional_hr/MANIFEST.json`.
- **CHIRPS y la lluvia NASA (IMERG) cuentan la misma historia a 0.1°:** correlación mediana de las anomalías mensuales r = 0.68 (p10-p90: 0.50-0.76, 409 celdas); peor al oeste de 71° O (r mediana 0.60) que al este de 70° O (0.74).
- **Umbral crítico nacional:** con todas las celdas juntas, la eficiencia con la que la lluvia extra se vuelve agua del suelo cambia de régimen cuando el suelo ya está lleno en un 59 % de su rango (IC 95 % 49-73 %): por encima, cada mm extra deja cada vez menos agua en el suelo (saturación; ΔBIC = 5462).
- **Pero celda por celda casi nunca se puede afirmar:** de 1649 celdas, 407 tienen p < 0.05 sin corregir y solo 75 sostienen el umbral tras FDR y ΔBIC > 2. 24 años de datos mensuales no bastan para fijar un umbral por píxel.
- **Los 'meses de quiebre' casi desaparecen al corregir la autocorrelación:** Pettitt clásico marca 1536 de 1649 celdas de humedad del suelo; con bootstrap por bloques quedan 0 (bloques de 12 meses) y 0 (24 meses).
- **Par de demostración a 0.05°:** San Juan (19.025°N, 70.975°O) (A) y La Vega (19.175°N, 70.475°O) (B), a 55 km: misma lluvia CHIRPS (r = 0.90, diferencia de media 3.8 %), eficiencia 0.075 frente a 0.168 (q = 0.036; supera el FDR); NASA SMAP L4 da la misma dirección (Δ = -0.070, p = 0.001).
- **18-nov-2023:** la estación (431 mm, preliminar) frente a CHIRPS 91 mm ese día y 160 mm en la péntada; IMERG 140 mm. Ningún producto de satélite de 5-10 km reproduce un acumulado puntual de ese tamaño.

## 1 · Fuentes (todas públicas; verificadas el 2026-11-14)

| Capa | Cita | DOI / URL | Licencia | Versión | Resolución nativa | NASA |
|---|---|---|---|---|---|---|
| CHIRPS v2.0 mensual (subconjunto Centroamérica-Caribe, camer-carib) | Funk, C., Peterson, P., Landsfeld, M., Pedreros, D., Verdin, J., Shukla, S., Husak, G., Rowland, J., Harrison, L., Hoell, A., Michaelsen, J. (2015). The climate hazards infrared precipitation with stations — a new environmental record for monitoring extremes. Scientific Data 2, 150066. | 10.1038/sdata.2015.66 · https://data.chc.ucsb.edu/products/CHIRPS/v2.0/camer-carib_monthly/tifs/ | Dominio público (CC0: 'Pete Peterson has waived all copyright…', chc.ucsb.edu/data/chirps) | 2.0 (producto final) | 0.05° (~5.3 km en RD), mensual | no |
| CHIRPS v2.0 diario (hemisferio occidental, whem p05) | Funk et al. (2015), Scientific Data 2, 150066. | 10.1038/sdata.2015.66 · https://data.chc.ucsb.edu/products/CHIRPS/v2.0/whem_daily/tifs/p05/2023/ | Dominio público (CC0) | 2.0 (producto final) | 0.05°, diario (etiqueta de día UTC; README-CHIRPS2-Daily) | no |
| TerraClimate v1.1 (THREDDS de Northwest Knowledge Network, subconjunto NCSS) | Abatzoglou, J.T., Dobrowski, S.Z., Parks, S.A., Hegewisch, K.C. (2018). TerraClimate, a high-resolution global dataset of monthly climate and climatic water balance from 1958–2015. Scientific Data 5, 170191. Versión servida: Abatzoglou, J.T., Hegewisch, K.C., Yin, C., Kalashinkov, D.A. (2026). TerraClimate v1.1 (referencia del propio archivo). | 10.1038/sdata.2017.191 · http://thredds.northwestknowledge.net:8080/thredds/catalog/TERRACLIMATE_ALL/data/catalog.html | CC0 1.0 (atributo 'license' del archivo) | V1.1 (atributo 'version'; date_created 2026-06-02) | 1/24° (~4.6 km en RD), mensual; PERO las anomalías mes a mes vienen de ERA5 (~0.25°) y la capacidad de agua del suelo del modelo de balance es de 0.5° (Wang-Erlandsson et al. 2016) | no |
| SoilGrids 2.0 (ISRIC), arcilla y arena 0-5, 5-15, 15-30 cm (media), por WCS | Poggio, L., de Sousa, L.M., Batjes, N.H., Heuvelink, G.B.M., Kempen, B., Ribeiro, E., Rossiter, D. (2021). SoilGrids 2.0: producing soil information for the globe with quantified spatial uncertainty. SOIL 7, 217–240. | 10.5194/soil-7-217-2021 · https://maps.isric.org/mapserv?map=/map/{prop}.map (WCS 2.0.1) | CC BY 4.0 | SoilGrids 2.0 (2020) | 250 m nativo (Homolosine); pedido en EPSG:4326 a 0.0025° (el servidor reproyecta) | no |
| Copernicus DEM GLO-90 (COG públicos en AWS) | European Space Agency (2021). Copernicus DEM — Global and European Digital Elevation Model (COP-DEM), GLO-90. Teselas COG del registro AWS Open Data. | 10.5270/ESA-c5d3d65 · https://copernicus-dem-90m.s3.amazonaws.com/ | Licencia Copernicus DEM GLO-90: uso libre mundial con atribución '© DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018 provided under COPERNICUS by the European Union and ESA' | GLO-90 (teselas COG 1°×1° del bucket público) | 3″ (~90 m) | no |
| ESA WorldCover 10 m 2021 v200 | Zanaga, D., Van De Kerchove, R., Daems, D., De Keersmaecker, W., Brockmann, C., Kirches, G., Wevers, J., Cartus, O., Santoro, M., Fritz, S., Lesiv, M., Herold, M., Tsendbazar, N.E., Xu, P., Ramoino, F., Arino, O. (2022). ESA WorldCover 10 m 2021 v200. | 10.5281/zenodo.7254221 · https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/ | CC BY 4.0 | v200 (algorithm_version V2.0.0) | 10 m; aquí leído de la vista general 1/8 del COG (~80 m) y llevado a fracciones por celda 0.05° | no |
| geoBoundaries gbOpen DOM ADM0 (simplificado, en appeears/) y ADM1 | Runfola, D. et al. (2020). geoBoundaries: A global database of political administrative boundaries. PLoS ONE 15(4): e0231866. | 10.1371/journal.pone.0231866 · https://www.geoboundaries.org/api/current/gbOpen/DOM/ | ADM0: CC BY 4.0 (fuente Caribbean GeoPortal); ADM1: dominio público (fuente Natural Earth) | DOM-ADM0-20870125 (2020); DOM-ADM1 según metadatos de la API | vectorial | no |
| SMAP L4 Global 3-hourly 9 km EASE-Grid Surface and Root Zone Soil Moisture Geophysical Data V008 (SPL4SMGP) | Reichle, R., De Lannoy, G., Koster, R.D., Crow, W.T., Kimball, J.S., Liu, Q., Bechtold, M. SMAP L4 Global 3-hourly 9 km EASE-Grid Surface and Root Zone Soil Moisture Geophysical Data, Version 8. NASA NSIDC DAAC. | 10.5067/T5RUATAQREF8 · https://opendap.earthdata.nasa.gov/collections/C3480440870-NSIDC_CPRD/ (OPeNDAP en la nube, token) | Datos NASA EOSDIS: uso libre y sin restricciones con cita (NSIDC use & copyright) | V008 | 9 km (EASE-Grid 2.0), cada 3 h; aquí 1 ventana de 3 h por día (12-15 UTC) promediada por mes | sí |
| GPM IMERG Final V07 mensual (descargado por el motor nacional, solo lectura aquí) | Huffman, G.J., Stocker, E.F., Bolvin, D.T., Nelkin, E.J., Tan, J. (2023). GPM IMERG Final Precipitation L3 1 month 0.1 degree x 0.1 degree V07. GES DISC. | 10.5067/GPM/IMERG/3B-MONTH/07 · https://gpm1.gesdisc.eosdis.nasa.gov/opendap/GPM_L3/GPM_3IMERGM.07/ | Datos NASA EOSDIS: uso libre con cita | V07 | 0.1°, mensual | sí |

**Qué añade cada capa y qué es:**

- **CHIRPS v2.0 mensual (subconjunto Centroamérica-Caribe, camer-carib).** Infrarrojo térmico de satélites geoestacionarios (duración de nubes frías) calibrado con la climatología CHPclim y mezclado con estaciones (GTS/GHCN y redes nacionales que comparten datos). *Aporta:* Lluvia a 0.05°: 4 celdas por cada celda IMERG (0.1°) y 25 por cada GLDAS (0.25°). Comprobación independiente de IMERG (NASA), no sustituto.
- **CHIRPS v2.0 diario (hemisferio occidental, whem p05).** NO es un producto diario independiente: el total de la PÉNTADA (mezcla satélite + estaciones) se reparte entre sus 5 días con las proporciones diarias del pronóstico CFSv2 (README-CHIRPS2-Daily). Solo el total de 5 días está anclado a estaciones; el valor de un día es una redistribución. *Aporta:* Mirada a 0.05° del evento del 18-nov-2023 en Santo Domingo frente al dato de estación.
- **TerraClimate v1.1 (THREDDS de Northwest Knowledge Network, subconjunto NCSS).** Interpolación climáticamente asistida: climatología de alta resolución (WorldClim v2.1 según el atributo 'source') + anomalías mensuales de ERA5, y un balance hídrico Thornthwaite-Mather modificado (humedad del suelo, ET real, déficit hídrico, PDSI). OJO: la v1.0 usaba CRU TS4/JRA-55; la v1.1 que sirve hoy el THREDDS usa ERA5. *Aporta:* Respuesta del suelo (balance hídrico) a ~4 km, independiente de NASA. Es un MODELO, no una medición: su detalle fino viene de la climatología, no de la variabilidad mensual.
- **SoilGrids 2.0 (ISRIC), arcilla y arena 0-5, 5-15, 15-30 cm (media), por WCS.** Predicción por aprendizaje automático a partir de perfiles de suelo (WoSIS) y covariables; incluye incertidumbre (no usada aquí). *Aporta:* Textura del suelo (factor explicativo estático) a ~250 m.
- **Copernicus DEM GLO-90 (COG públicos en AWS).** Modelo digital de superficie (TanDEM-X, radar interferométrico). *Aporta:* Elevación y pendiente (Horn, a 90 m) agregadas a 0.05°.
- **ESA WorldCover 10 m 2021 v200.** Clasificación de Sentinel-1 y Sentinel-2 (11 clases). *Aporta:* Fracción de bosque, cultivo, pasto, urbano, etc. por celda (factor explicativo estático).
- **geoBoundaries gbOpen DOM ADM0 (simplificado, en appeears/) y ADM1.** Límites administrativos. *Aporta:* Máscara de tierra dominicana y bordes de provincia en los mapas.
- **SMAP L4 Global 3-hourly 9 km EASE-Grid Surface and Root Zone Soil Moisture Geophysical Data V008 (SPL4SMGP).** Modelo Catchment del GEOS con asimilación de temperaturas de brillo de SMAP (banda L, 36 km). *Aporta:* Humedad superficial y de zona de raíces NASA a 9 km (2015-04 en adelante): la respuesta del suelo con la observación de NASA más directa del agua del suelo.
- **GPM IMERG Final V07 mensual (descargado por el motor nacional, solo lectura aquí).** Precipitación multisatélite (microondas pasivas + IR) calibrada con GPCC. *Aporta:* La lluvia NASA de referencia; se compara con CHIRPS celda a celda (sin pretender 0.05°).

**La NASA sigue en el centro.** IMERG (lluvia) y SMAP L4 (humedad del suelo) son NASA. CHIRPS combina infrarrojo de satélites geoestacionarios con estaciones; TerraClimate v1.1 (la versión que sirve hoy el THREDDS, creada el 2026-06-02) combina la climatología WorldClim v2.1 con anomalías de **ERA5** (la v1.0 usaba CRU TS4 y JRA-55: la descripción 'WorldClim/CRU/JRA55' ya no es la de los archivos descargados). Son comprobaciones independientes de NASA, no sustitutos.

**Capas, resolución y número de celdas sobre la RD** (`results/nacional_hr/capas_resolucion_y_celdas.csv`):

| Capa | Resolución nativa | Celdas sobre RD | Criterio |
|---|---|---|---|
| CHIRPS v2.0 mensual | 0.05° | 1 649 | celdas 0.05° con ≥50 % de área en RD y dato en todos los meses |
| TerraClimate v1.1 | 1/24° (~4.6 km) | 2 384 | centro de celda dentro de RD |
| IMERG V07 (NASA) | 0.1° | 413 | centro dentro de RD |
| SMAP L4 V008 (NASA) | 9 km EASE-2 | 590 | centro dentro de RD |
| SoilGrids 2.0 (pedido a 0.0025°) | 0.00250° | 657 832 | ≈ área RD / área de píxel |
| Copernicus DEM GLO-90 | 0.00083° | 5 920 492 | ≈ área RD / área de píxel |
| ESA WorldCover 2021 (vista 1/8) | 0.00067° | 9 250 769 | ≈ área RD / área de píxel |
| (referencia) área RD en la máscara | — | 48 232 | km² (Σ área de celda × fracción en RD) |

**Estado de cada descarga** (sección `rutas` del manifiesto):

| Ruta | Estado | Pedidos | Errores | Nota |
|---|---|---|---|---|
| CHIRPS_D | ok | 30 | 0 |  |
| CHIRPS_M | ok | 288 | 0 |  |
| COPDEM | parcial | 12 | 3 | Las 404 son las teselas 17-18 N entre 71 y 68 O: solo mar al sur de la isla (el bucket no publica teselas sin tierra). Beata y Alto Velo caen en N17 W072, que sí se descargó. |
| LIMITES | ok | — | 0 |  |
| SMAP_L4 | ok | 3564 | 0 |  |
| SOILGRIDS | ok | 6 | 0 |  |
| TERRACLIMATE | ok | 144 | 0 |  |
| WORLDCOVER | ok | — | 0 |  |

## 2 · Armonización a 0.05° (sin fingir precisión)

- **Rejilla común:** la de CHIRPS (bordes en múltiplos de 0.05°), 72.10-68.20 O × 17.40-20.10 N. Celda de tierra = al menos 50 % de su área dentro de geoBoundaries ADM0 (100 puntos por celda, peso cos φ).
- **Continuos más finos** (TerraClimate 1/24°, SoilGrids 0.0025°, DEM 3″): media ponderada por el área de solape exacta en la esfera (remapeo conservativo de primer orden). La pendiente se calcula a 90 m (Horn) y después se promedia; el relieve es la desviación típica de la elevación dentro de la celda.
- **Categóricos** (WorldCover): fracción de cada clase en la celda, nunca la clase mayoritaria. Se leyó la vista general 1/8 del COG (~80 m); en una ventana de validación del Cibao a 10 m, la mayor diferencia de fracción por celda fue:
  bosque 4.6 puntos; pastizal 2.2 puntos; cultivo 0.6 puntos; urbano 3.4 puntos; suelo_desnudo 0.5 puntos; agua 0.1 puntos.
- **Más gruesos que 0.05°** (IMERG 0.1°, SMAP 9 km, GLDAS 0.25°): **no se interpolan**. Se guardan y dibujan en su rejilla nativa; cuando se cruzan con una celda 0.05° se usa la celda nativa que contiene su centro, y CHIRPS se agrega a la celda gruesa (no al revés).
- **TerraClimate a 1/24° no es variabilidad de 4 km:** la anomalía de cada mes viene de ERA5 (~0.25°, ~28 km) y la capacidad de agua del suelo del modelo es de 0.5° (Wang-Erlandsson et al. 2016). Su detalle fino es sobre todo climatología. Lo mismo, en menor grado, con SMAP L4 (asimila brillo de banda L a 36 km).

## 3 · Verificación cruzada

- CHIRPS agregado a la rejilla IMERG (0.1°), anomalías mensuales 2001-2024: r mediana 0.68, p10 0.50, p90 0.76. Cociente de lluvia media CHIRPS/IMERG: mediana 0.92 (p10-p90 0.61-1.17). Mapa: figura hr1, panel f.
- CHIRPS diario sumado (noviembre 2023, celda de Santo Domingo) = 159.8 mm; mensual = 159.8 mm: los dos archivos son coherentes.
- Lectores de cada formato probados con datos sintéticos en `tests/test_hr_metodos.py` (remapeo, umbral, Pettitt, FDR, par y sustitutos, ridge espacial, proyección EASE-Grid 2.0).

## 4 · Umbrales críticos: ¿cuándo deja el suelo de 'aceptar' la lluvia?

**Idea (no literal):** un suelo no responde igual a la misma lluvia extra según lo lleno que esté. Seco, una parte se va en evaporación; casi lleno, el agua sobra y escurre. Buscamos el **punto de quiebre** del llenado antecedente donde cambia la 'eficiencia' (mm que gana el suelo por cada mm de lluvia por encima de lo normal).

**Método (por celda 0.05°).** y = ΔS (cambio mensual de humedad del suelo TerraClimate), Pa = anomalía de lluvia CHIRPS, f = llenado relativo antecedente (S − S_min)/(S_max − S_min), efectos fijos de mes calendario. M0: y ~ Pa + f + Pa·f; M1 añade h = (f − θ)+ y Pa·h (regresión segmentada, θ en los cuantiles 15-85 % de f). Prueba sup-F con nula por bootstrap de residuos de M0 en bloques circulares de 12 meses (499 réplicas), FDR de Benjamini-Hochberg sobre todas las celdas, y 'sostenido' = q < 0.05 y ΔBIC > 2. IC 95 % de θ por bootstrap de bloques móviles (300).

| Resultado por celda | Celdas | % |
|---|---|---|
| evaluadas | 1649 | 100 % |
| p < 0.05 sin corregir | 407 | 24.7 % |
| q < 0.05 (FDR) | 85 | 5.2 % |
| **sostenido** (q < 0.05 y ΔBIC > 2) | **75** | 4.5 % |
| sostenido con ΔBIC > 6 | 53 | 3.2 % |
| sensibilidad: lluvia de TerraClimate como forzante | 519 | coinciden con la principal: 54 |
| sensibilidad: sin efectos fijos de mes | 413 | coinciden con la principal: 41 |
| SMAP L4 (NASA) 9 km, 2015-04 a 2024-12 | 0 de 545 | — |

En las celdas con umbral sostenido: θ mediano = 0.37 (p25-p75 0.23–0.53; ≈ 62 mm de agua en el suelo), ancho mediano del IC 95 % = 0.56. Eficiencia mediana: suelo seco 0.201, en el umbral 0.517, suelo húmedo 0.161; en 95 % de ellas el quiebre es de **saturación** (la eficiencia cae por encima de θ), y en 95 % la curva tiene forma de **pico**: por debajo de θ el suelo seco guarda MENOS de cada mm extra que en el umbral (en el balance del modelo, la evaporación se lleva primero el agua: el suelo seco 'rechaza' lluvia en ese sentido, no por hidrofobia), y por encima guarda menos porque ya está lleno. θ es el **punto de máxima eficiencia**. Provincias con más celdas de umbral sostenido: Azua (19), San José de Ocoa (15), Peravia (10), Hato Mayor (9), Barahona (6), San Pedro de Macorís (5).

**Lectura honesta.** La mayoría de los p < 0.05 sin corregir no sobreviven al FDR: una celda sola, con 287 meses y una lluvia (CHIRPS) que no es la que forzó al modelo de suelo (ERA5), no tiene potencia para fijar su propio umbral. Cuando se usa la lluvia del propio TerraClimate aparecen muchos más umbrales: eso mide sobre todo la **mecánica del cubo** del modelo (capacidad fija), no una propiedad observada del suelo. Por eso el resultado principal es la curva agrupada, más abajo.

**Curvas por paisaje (creativo, con la incertidumbre correcta).** Se agrupan celdas por terciles de aridez (P/PET) y de arcilla, se estima un umbral COMÚN al grupo (efectos fijos celda × mes) y la incertidumbre se obtiene remuestreando **bloques de tiempo compartidos por todas las celdas** (no se finge que 500 celdas vecinas sean 500 experimentos independientes). Figura hr3b.

| Grupo | Fuente | Celdas | θ (llenado) | IC 95 % de θ | ΔBIC | cambio de pendiente b5 | IC 95 % b5 | quiebre sostenido | eficiencia en f=0.10 / 0.50 / 0.90 |
|---|---|---|---|---|---|---|---|---|---|
| todas las celdas | CHIRPS → TerraClimate (0.05°) | 1649 | 0.59 | 0.49–0.73 | 5462 | -0.499 | -0.792–-0.298 | sí | 0.241 / 0.253 / 0.112 |
| más seco (P/PET ≤ 0.74) | CHIRPS → TerraClimate (0.05°) | 550 | 0.47 | 0.03–0.47 | 1398 | -0.622 | -2.894–3.217 | no | 0.239 / 0.334 / 0.198 |
| intermedio (P/PET 0.74–0.99) | CHIRPS → TerraClimate (0.05°) | 549 | 0.64 | 0.38–0.84 | 1337 | -0.486 | -0.824–-0.236 | sí | 0.235 / 0.247 / 0.135 |
| más húmedo (P/PET > 0.99) | CHIRPS → TerraClimate (0.05°) | 550 | 0.69 | 0.21–0.86 | 1113 | -0.349 | -0.739–0.344 | no | 0.264 / 0.217 / 0.098 |
| menos arcilla (arcilla % ≤ 39.99) | CHIRPS → TerraClimate (0.05°) | 536 | 0.61 | 0.07–0.88 | 1257 | -0.501 | -1.953–-0.166 | sí | 0.249 / 0.263 / 0.130 |
| intermedio (arcilla % 39.99–43.79) | CHIRPS → TerraClimate (0.05°) | 535 | 0.57 | 0.46–0.68 | 1728 | -0.540 | -0.840–-0.312 | sí | 0.245 / 0.275 / 0.126 |
| más arcilla (arcilla % > 43.79) | CHIRPS → TerraClimate (0.05°) | 535 | 0.62 | 0.30–0.81 | 2011 | -0.459 | -0.830–0.060 | no | 0.231 / 0.230 / 0.100 |
| SMAP L4 (NASA), todas las celdas 9 km | CHIRPS → SMAP L4 zona de raíces (9 km) | 545 | 0.25 | 0.12–0.55 | 306 | -0.712 | -2.352–0.155 | no | 0.236 / 0.296 / 0.251 |

'Quiebre sostenido' = el IC 95 % bootstrap del cambio de pendiente b5 excluye 0. El ΔBIC agrupado es enorme porque n es grande y NO corrige la dependencia entre celdas: no se usa como prueba, solo como descripción.

**NASA SMAP L4** (2015-2024, 9 km): θ = 0.25 (IC 0.12–0.55), b5 = -0.712 (IC -2.352–0.155). SMAP es otro modelo (Catchment del GEOS) que asimila observaciones de banda L de SMAP; su forma de curva es la comprobación NASA de la de TerraClimate.

## 5 · Meses de quiebre (Pettitt)

Prueba de Pettitt sobre anomalías mensuales (sin ciclo estacional). La p asintótica supone independencia; con series persistentes da quiebres de sobra. Aquí la p sale de un bootstrap por bloques circulares (los mismos índices para todas las celdas, 999 réplicas) y luego FDR. Figura hr4.

| Variable | Celdas | q < 0.05 asintótica (sin corregir autocorrelación) | q < 0.05 bloques 12 meses | q < 0.05 bloques 24 meses | Año de quiebre más frecuente SIN corregir (celdas) |
|---|---|---|---|---|---|
| Humedad del suelo (TerraClimate) | 1649 | 1536 | 0 | 0 | 2013 (763), 2014 (245), 2018 (225) |
| Déficit hídrico (TerraClimate) | 1649 | 875 | 0 | 0 | 2013 (667), 2012 (125), 2018 (38) |
| Lluvia (CHIRPS) | 1649 | 458 | 0 | 0 | 2012 (405), 2011 (51), 2013 (1) |

**Lectura.** El Pettitt clásico 'encuentra' un quiebre hacia 2013-2014 en casi todo el país (la media nacional del suelo pasa a anomalías negativas desde 2013: figura hr4, panel e); con la corrección no sobrevive ninguno. La diferencia entre la primera columna y las otras dos es el mensaje: casi todos los 'quiebres' del Pettitt clásico son persistencia (meses secos seguidos de meses secos), no cambios de régimen. Un quiebre que sobrevive indica un cambio de nivel de la anomalía, que también puede ser una tendencia gradual o un cambio en los datos de entrada de ERA5; no se interpreta como causa.

## 6 · ¿Qué acompaña a la respuesta? Suelo, terreno, cobertura, aridez

Ridge con variables estandarizadas (coeficiente = DE de la respuesta por DE del factor, con los demás fijos), λ por validación cruzada, habilidad con validación cruzada **por bloques espaciales de 0.5°**, IC 95 % por bootstrap de bloques espaciales, I de Moran de los residuos. Figura hr5.

**Umbral θ (celdas sostenidas)** — n = 75 celdas en 13 bloques; R² VC espacial = 0.42, R² VC aleatoria = 0.49, R² de ajuste = 0.60; I de Moran de residuos = 0.24 (p perm. 0.001).

| Factor | β estandarizado | IC 95 % | IC excluye 0 | ρ de Spearman (simple) |
|---|---|---|---|---|
| aridez_P/PET | 0.40 | 0.15–0.59 | sí | 0.73 |
| arcilla_% | 0.22 | -0.01–0.28 | no | 0.48 |
| cultivo_frac | 0.20 | 0.05–0.25 | sí | 0.38 |
| arena_% | -0.12 | -0.25–0.09 | no | -0.37 |
| elevación_m | 0.10 | -0.12–0.20 | no | 0.07 |
| pendiente_° | 0.09 | -0.04–0.20 | no | 0.05 |
| urbano_frac | -0.08 | -0.14–0.06 | no | -0.12 |
| pasto+matorral_frac | -0.05 | -0.13–0.01 | no | 0.17 |
| bosque_frac | 0.03 | -0.02–0.11 | no | -0.14 |
| relieve_m | 0.02 | -0.08–0.08 | no | -0.10 |
| lluvia_anual_CHIRPS_mm | 0.01 | -0.11–0.16 | no | 0.16 |

**Eficiencia lluvia→suelo** — n = 1606 celdas en 29 bloques; R² VC espacial = 0.60, R² VC aleatoria = 0.66, R² de ajuste = 0.66; I de Moran de residuos = 0.79 (p perm. 0.001).

| Factor | β estandarizado | IC 95 % | IC excluye 0 | ρ de Spearman (simple) |
|---|---|---|---|---|
| lluvia_anual_CHIRPS_mm | -0.71 | -0.83–-0.59 | sí | -0.82 |
| bosque_frac | 0.22 | 0.07–0.34 | sí | -0.16 |
| elevación_m | -0.19 | -0.39–-0.03 | sí | 0.01 |
| arena_% | 0.15 | 0.04–0.25 | sí | 0.37 |
| relieve_m | 0.13 | 0.04–0.20 | sí | 0.02 |
| pasto+matorral_frac | 0.07 | -0.03–0.17 | no | 0.15 |
| pendiente_° | -0.07 | -0.17–0.08 | no | -0.06 |
| cultivo_frac | -0.03 | -0.11–0.05 | no | 0.12 |
| aridez_P/PET | -0.03 | -0.21–0.14 | no | -0.64 |
| urbano_frac | 0.01 | -0.04–0.07 | no | 0.11 |
| arcilla_% | 0.01 | -0.08–0.11 | no | -0.42 |

**S_max TerraClimate (control)** — n = 1606 celdas en 29 bloques; R² VC espacial = 0.01, R² VC aleatoria = 0.16, R² de ajuste = 0.17; I de Moran de residuos = 1.00 (p perm. 0.001).

| Factor | β estandarizado | IC 95 % | IC excluye 0 | ρ de Spearman (simple) |
|---|---|---|---|---|
| arena_% | 0.13 | 0.05–0.21 | sí | 0.31 |
| elevación_m | -0.12 | -0.19–-0.04 | sí | -0.06 |
| aridez_P/PET | -0.11 | -0.22–0.02 | no | -0.27 |
| bosque_frac | 0.08 | 0.02–0.13 | sí | 0.09 |
| arcilla_% | -0.08 | -0.13–0.01 | no | -0.23 |
| relieve_m | -0.05 | -0.09–0.01 | no | 0.01 |
| cultivo_frac | -0.04 | -0.11–0.02 | no | -0.14 |
| lluvia_anual_CHIRPS_mm | -0.04 | -0.16–0.10 | no | -0.18 |
| pasto+matorral_frac | -0.03 | -0.11–0.03 | no | -0.09 |
| pendiente_° | -0.02 | -0.08–0.04 | no | -0.02 |
| urbano_frac | -0.01 | -0.05–0.03 | no | 0.03 |

- **Umbral θ (celdas sostenidas):** el factor más fuerte es **aridez_P/PET** (β = 0.40, IC 0.15–0.59).
- **Eficiencia lluvia→suelo:** el factor más fuerte es **lluvia_anual_CHIRPS_mm** (β = -0.71, IC -0.83–-0.59).
  Lectura física (asociación): las celdas más lluviosas pasan más meses cerca de llenarse, por eso la lluvia extra rinde menos ahí; y donde el clima es más húmedo (P/PET alto) el umbral θ está más arriba.

**Lectura.** La autocorrelación espacial de los residuos es alta: las celdas vecinas no son independientes, y los IC por bloques espaciales son la cifra honesta. La fila de control (S_max de TerraClimate) muestra que la textura de SoilGrids apenas explica la capacidad del modelo: la capacidad de TerraClimate viene de un mapa de 0.5°, así que **cualquier relación fina entre textura y respuesta en TerraClimate no puede ser mecanismo del modelo**; sale de la lluvia y la climatología que acompañan a esos suelos.

## 7 · 'Misma lluvia, distinta respuesta' a alta resolución

Candidatos: pares de celdas 0.05° a 20-60 km (celdas distintas en SMAP 9 km y en TerraClimate) con lluvia anual CHIRPS a < 5 %, anomalías mensuales correlacionadas (r ≥ 0.85) y distribución mensual parecida (KS D ≤ 0.10): **17675** pares. Respuesta = eficiencia (pendiente de ΔS sobre la anomalía de lluvia con efectos fijos de mes). La diferencia se prueba con bootstrap por bloques móviles de 12 meses con los MISMOS meses para las dos celdas (999 réplicas) y FDR sobre todos los candidatos: **806** pares con q < 0.05 (4.6 %).

**Par elegido** (mayor |z| × distancia en suelo/terreno entre los que superan el FDR, y con la misma dirección en SMAP L4):

| | A | B |
|---|---|---|
| celda | San Juan (19.025°N, 70.975°O) | La Vega (19.175°N, 70.475°O) |
| lluvia anual CHIRPS (mm) | 1826 | 1897 |
| eficiencia TerraClimate (IC 95 %) | 0.075 (0.046–0.104) | 0.168 (0.132–0.200) |
| arcilla 0-30 cm (%) | 34.8 | 35.6 |
| arena 0-30 cm (%) | 29.1 | 40.7 |
| pendiente (°) | 22.7 | 2.2 |
| elevación (×100 m) | 24.4 | 0.9 |
| bosque (%) | 88.6 | 31.2 |
| cultivo (%) | 0.0 | 38.1 |
| aridez P/PET (×10) | 13.6 | 8.6 |
| S_max TerraClimate (×10 mm) | 12.1 | 13.5 |

Δe = -0.093 (IC 95 % -0.127–-0.057), z = -5.11, p = 0.0010, q = 0.0357. Distancia 55 km; lluvia: r = 0.90, KS D = 0.10, diferencia de media 3.8 %.
- **NASA SMAP L4** (zona de raíces, 2015-2024): eficiencia A 0.179, B 0.250, Δ = -0.070, p = 0.001; misma dirección: sí.
- **NASA IMERG** en las dos celdas: r de anomalías = 0.92, lluvia anual 1626 y 1607 mm (celdas IMERG distintas).
- **Falsos positivos con sustitutos:** 300 series simuladas con la MISMA eficiencia verdadera en A y B (residuos propios remuestreados en bloques compartidos): la prueba marcó p < 0.05 en el 4.7 % (nominal 5 %).
- **Ojo:** la lluvia es la misma, pero la demanda de evaporación no: P/PET = 1.36 en A y 0.86 en B (la altura enfría y baja la PET). 'Misma lluvia' no es 'mismo balance'; parte de la diferencia de respuesta va por ahí.

**Lectura:** asociación. La diferencia de eficiencia acompaña a diferencias de suelo, terreno y cobertura, pero en TerraClimate la respuesta la fijan la climatología, ERA5 y una capacidad de 0.5°: no demuestra que la textura o la pendiente la causen. Otros pares fuertes: `results/nacional_hr/resumen.json` → `par.top10`.

## 8 · 18 de noviembre de 2023, Santo Domingo

La estación ONAMET de Arroyo Hondo Viejo registró **431 mm** (valor preliminar; fuente: prensa, Acento, 19-nov-2023, y dato aportado por el equipo; no se encontró aún el boletín oficial). La posición marcada en la figura es la del barrio (≈ 18.50 N, 69.95 O, ±2 km), no coordenadas oficiales de la estación.

| Fuente | mm |
|---|---|
| estación ONAMET 18-nov (preliminar, prensa) | 431 |
| CHIRPS 18-nov · celda 0.05° | 91 |
| CHIRPS 18-nov · máximo 3×3 celdas (~16 km) | 91 |
| CHIRPS péntada 16-20 nov · celda | 160 |
| CHIRPS noviembre completo · celda | 160 |
| IMERG 18-nov (00-24 UTC) · celda 0.1° | 140 |
| IMERG 16-20 nov · celda 0.1° | 188 |

**Cuidado al comparar.** El CHIRPS diario v2 **no** es un producto diario independiente: reparte el total de la péntada (anclado a satélite + estaciones) entre sus días con las proporciones del pronóstico CFSv2 (README-CHIRPS2-Daily). La cifra comparable es la péntada 16-20 nov. Una estación mide un punto; una celda de 5-10 km promedia el área: un aguacero convectivo de 431 mm en un punto puede ser mucho menos en promedio de área. Que satélite y estación difieran no dice cuál 'está mal'. Figura hr7.

## 9 · Qué sobrevive a la corrección y qué no

| Afirmación | ¿Sobrevive? | Por qué |
|---|---|---|
| Existe un umbral de llenado nacional donde la lluvia extra rinde menos (saturación) | sí | IC 95 % de b5 -0.792–-0.298 con bloques de tiempo compartidos |
| Cada celda 0.05° tiene su propio umbral identificable | casi nunca (75 de 1649) | FDR + ΔBIC |
| Hay 'meses de quiebre' extendidos en la humedad del suelo | no (0 celdas) | la versión sin corregir (1536) es persistencia |
| Los factores estáticos predicen la eficiencia fuera de su región | R² VC espacial 0.60 | factores más fuertes: lluvia_anual_CHIRPS_mm (-0.71), bosque_frac (0.22), elevación_m (-0.19) |
| Par 'misma lluvia, distinta respuesta' | sí (q = 0.036) | FDR sobre 17675 candidatos; sustitutos 4.7 % |

## 10 · Límites

- **TerraClimate y SMAP L4 son modelos**, no mediciones de humedad del suelo. TerraClimate es un cubo de Thornthwaite-Mather con capacidad de 0.5°: puede saturarse, pero no puede 'rechazar' agua por un suelo seco hidrófobo ni por sellado superficial. Un umbral en TerraClimate es una propiedad del modelo forzado por ERA5.
- **Resolución efectiva < resolución de la rejilla:** anomalías de ERA5 (~28 km) en TerraClimate; banda L de 36 km en SMAP; estaciones escasas en CHIRPS para la RD (el archivo de reconocimientos de CHIRPS no lista a ONAMET entre los aportes históricos de América Latina).
- **Lluvia y suelo de fuentes distintas:** usar CHIRPS para explicar un suelo forzado por ERA5 diluye la señal (por eso la sensibilidad con la lluvia de TerraClimate da más umbrales). Es una elección conservadora.
- **SoilGrids** es una predicción (con incertidumbre que no se propagó aquí); el WCS reproyecta en el servidor. **WorldCover** es de 2021 (una foto, no una serie). **Copernicus DEM** es de superficie (incluye dosel y edificios).
- **Dependencia espacial:** el FDR de Benjamini-Hochberg es válido con dependencia positiva (PRDS), pero las celdas vecinas no son pruebas independientes; los mapas de 'celdas significativas' no deben contarse como evidencias separadas.
- **Sin causalidad:** todo es asociación dentro de productos de satélite y modelos.

## 11 · Reproducir

```
docker compose build
docker compose run --rm alta_resolucion                 # descarga lo que falta y corre todo
docker compose run --rm alta_resolucion --sin-descarga  # solo con la caché de data/nacional_hr
```

SMAP L4 necesita el token de Earthdata en `.secrets/earthdata_token` (montado de solo lectura; nunca se imprime ni se guarda). Sin token, la corrida usa la caché o se salta SMAP y lo anota. Semilla fija (2026); mismas entradas → mismas salidas.

**Figuras** (`figures/nacional_hr/`, PDF + PNG + JSON de procedencia): hr1 climatología en resolución nativa · hr2 factores estáticos · hr3 umbrales por celda · hr3b curvas de eficiencia por paisaje · hr4 meses de quiebre · hr5 factores del umbral · hr6 par 'misma lluvia' · hr7 evento 18-nov-2023.

**Tablas** (`results/nacional_hr/`): `celdas_005.csv` (una fila por celda: factores, umbral, quiebres), `umbrales_smap_9km.csv`, `capas_resolucion_y_celdas.csv`, `fuentes.csv`, `resumen.json`. Cuaderno: `notebooks/05_alta_resolucion_y_umbrales.ipynb` y su HTML en `reports_nacional/notebooks_html/`.

