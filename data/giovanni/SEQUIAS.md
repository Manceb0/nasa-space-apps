# SEQUIAS — series de Giovanni para fechar sequías (PHANTOM)

Generado el 2026-11-14 con NASA Giovanni v4.40, servicio **Time Series, Area-Averaged** (`service=ArAvTs`), mensual, 2001-01 a 2024-12 (288 meses por serie, sin valores faltantes).
Cálculo: `sequias.py` (en esta carpeta), ejecutado con `python -I sequias.py <esta carpeta> salida.json`.

## Variables (ID exacto de Giovanni)

| Variable | ID de Giovanni | Producto y versión | Resolución | Unidades en el CSV |
|---|---|---|---|---|
| Precipitación | `GPM_3IMERGM_07_precipitation` | GPM_3IMERGM v07, "Final Run" combinado satélite-pluviómetro | 0.1°, mensual (Giovanni la ofrece de 1998-01 a 2025-09) | mm/mes (conversión de Giovanni desde mm/h) |
| Temperatura del aire a 2 m | `M2TMNXSLV_5_12_4_T2M` | MERRA-2 M2TMNXSLV v5.12.4 | 0.5° x 0.625°, mensual | °C |
| Humedad del suelo 0-10 cm | `GLDAS_NOAH025_M_2_1_SoilMoi0_10cm_inst` | GLDAS_NOAH025_M v2.1 | 0.25°, mensual | kg m-2 |
| Humedad de la zona radicular (sí existe) | `GLDAS_NOAH025_M_2_1_RootMoist_inst` | GLDAS_NOAH025_M v2.1 | 0.25°, mensual | kg m-2 |

Enlace base: https://giovanni.gsfc.nasa.gov/giovanni/ . Cada CSV trae en su cabecera la fila "URL to Reproduce Results" con la consulta exacta.

## Cajas usadas (W,S,E,N)

| Región | Variable | Caja pedida a Giovanni | Celdas que usó Giovanni ("Data Bounding Box", centros de celda) |
|---|---|---|---|
| A. Noroeste / Montecristi | IMERG | -71.60,19.75,-71.35,19.92 (la original) | -71.55,19.75 a -71.45,19.85 |
| A | MERRA-2 T2M | -71.60,19.75,-71.35,19.92 (la original) | una sola celda, centro -71.25, 20.0 (la más cercana; Giovanni no rechazó la caja) |
| A | GLDAS (las dos) | **-71.63,19.62,-71.35,19.92 (agrandada)** | -71.625,19.625 a -71.375,19.875 (4 celdas) |
| B. Jaragua | IMERG | -71.60,17.62,-71.30,17.85 (la original) | -71.55,17.65 a -71.35,17.75 |
| B | MERRA-2 T2M | -71.60,17.62,-71.30,17.85 (la original) | una sola celda, centro -71.25, 17.5 |
| B | GLDAS (las dos) | **-71.60,17.62,-71.30,17.88 (agrandada al norte)** | -71.375,17.625 y -71.375,17.875 |

Por qué se agrandaron las cajas de GLDAS: con la caja original, cada región caía en una sola celda de 0.25° (A: -71.375,19.875; B: -71.375,17.625). Para esa celda Giovanni respondió "no valid data points were found" (celda sin datos en la máscara de tierra de GLDAS). En A se extendió 0.03° al oeste y 0.13° al sur para meter 4 celdas. En B se extendió 0.03° al norte para meter la celda -71.375,17.875. Como la celda -71.375,17.625 no tiene datos válidos, en B la serie de GLDAS corresponde en la práctica a la celda -71.375,17.875.

## Archivos

| Archivo | Cómo se obtuvo |
|---|---|
| `imerg_precip_noroeste.csv` | CSV de Giovanni descargado tal cual |
| `merra2_t2m_noroeste.csv` | CSV de Giovanni descargado tal cual |
| `gldas_soilmoi0_10cm_noroeste.csv` | CSV de Giovanni descargado tal cual |
| `gldas_rootmoist_noroeste.csv` | reconstruido (ver problemas) |
| `imerg_precip_jaragua.csv` | reconstruido |
| `merra2_t2m_jaragua.csv` | reconstruido |
| `gldas_soilmoi0_10cm_jaragua.csv` | reconstruido |
| `gldas_rootmoist_jaragua.csv` | reconstruido |
| `sequias.py` | script del cálculo |

## Método para los periodos secos

1. Para cada mes del calendario (enero, febrero, etc.) se calcula el percentil 20 de los 24 valores de 2001 a 2024 (interpolación lineal, como numpy). Es una anomalía estacional: cada mes se compara solo con ese mismo mes en otros años.
2. Un mes cuenta como "seco" si su valor está **por debajo** de ese percentil 20. Con 24 años, eso marca exactamente 5 años por mes calendario (60 de 288 meses por serie).
3. Un periodo seco candidato es una racha de **2 o más meses secos seguidos**.
4. Déficit = suma observada en el periodo menos la suma de las medianas de esos meses del calendario (2001-2024). "% de lo normal" = observado / esa suma de medianas.
5. Contexto: anomalía media de T2M (MERRA-2) en esos meses, respecto a la media 2001-2024 del mismo mes del calendario, en la celda de MERRA-2 de la región.

La humedad del suelo se analiza con el mismo método (0-10 cm y zona radicular). El déficit de humedad está en kg m-2 sumados mes a mes. Sirve para ordenar periodos dentro de una misma serie, no para compararlo con mm de lluvia.

## Tablas de periodos secos candidatos

### A. L�nea Noroeste / Montecristi


**Precipitaci�n IMERG** (15 periodos; ordenados por d�ficit acumulado, el m�s fuerte primero)

| Inicio | Fin | Meses | Observado (mm) | Normal = suma de medianas (mm) | D�ficit (mm) | % de lo normal | Anomal�a T2M media (�C) |
|---|---|---|---|---|---|---|---|
| 2020-04 | 2020-06 | 3 | 176.3 | 405.4 | -229.1 | 43 % | +0.88 |
| 2022-10 | 2022-12 | 3 | 143.8 | 317.5 | -173.6 | 45 % | +0.24 |
| 2009-09 | 2009-11 | 3 | 226.1 | 390.4 | -164.3 | 58 % | +0.10 |
| 2019-04 | 2019-06 | 3 | 244.3 | 405.4 | -161.2 | 60 % | +0.21 |
| 2018-11 | 2019-01 | 3 | 91.5 | 245.4 | -153.9 | 37 % | +0.36 |
| 2015-04 | 2015-05 | 2 | 127.2 | 279.3 | -152.1 | 46 % | +0.23 |
| 2015-07 | 2015-09 | 3 | 214.4 | 365.8 | -151.5 | 59 % | -0.01 |
| 2022-04 | 2022-05 | 2 | 135.0 | 279.3 | -144.3 | 48 % | +0.23 |
| 2021-11 | 2021-12 | 2 | 78.1 | 185.7 | -107.6 | 42 % | +0.23 |
| 2018-06 | 2018-07 | 2 | 122.0 | 226.2 | -104.1 | 54 % | -0.28 |
| 2010-12 | 2011-01 | 2 | 37.9 | 124.0 | -86.0 | 31 % | -1.26 |
| 2021-01 | 2021-02 | 2 | 26.9 | 96.2 | -69.4 | 28 % | +0.10 |
| 2013-01 | 2013-02 | 2 | 37.5 | 96.2 | -58.8 | 39 % | +0.09 |
| 2005-02 | 2005-03 | 2 | 34.0 | 81.2 | -47.2 | 42 % | -0.71 |
| 2023-02 | 2023-03 | 2 | 39.6 | 81.2 | -41.5 | 49 % | +0.27 |

**Humedad suelo 0-10 cm GLDAS** (12 periodos; ordenados por d�ficit acumulado, el m�s fuerte primero)

| Inicio | Fin | Meses | Observado (kg m-2) | Normal = suma de medianas (kg m-2) | D�ficit (kg m-2) | % de lo normal | Anomal�a T2M media (�C) |
|---|---|---|---|---|---|---|---|
| 2021-09 | 2022-01 | 5 | 101.8 | 128.1 | -26.3 | 79 % | +0.06 |
| 2002-10 | 2003-03 | 6 | 108.7 | 132.6 | -23.9 | 82 % | +0.89 |
| 2009-08 | 2009-11 | 4 | 87.7 | 111.6 | -23.9 | 79 % | +0.03 |
| 2018-11 | 2019-01 | 3 | 50.2 | 71.1 | -20.8 | 71 % | +0.36 |
| 2013-12 | 2014-03 | 4 | 56.5 | 75.9 | -19.3 | 75 % | +0.59 |
| 2020-04 | 2020-06 | 3 | 53.6 | 72.0 | -18.4 | 74 % | +0.88 |
| 2018-06 | 2018-08 | 3 | 64.8 | 78.9 | -14.1 | 82 % | -0.34 |
| 2021-05 | 2021-07 | 3 | 64.1 | 76.4 | -12.4 | 84 % | -0.34 |
| 2020-09 | 2020-10 | 2 | 45.7 | 57.0 | -11.4 | 80 % | +0.26 |
| 2015-03 | 2015-05 | 3 | 51.5 | 61.0 | -9.4 | 85 % | +0.21 |
| 2015-07 | 2015-09 | 3 | 71.6 | 79.8 | -8.2 | 90 % | -0.01 |
| 2019-03 | 2019-04 | 2 | 29.7 | 37.0 | -7.3 | 80 % | +0.33 |

**Humedad zona radicular GLDAS** (11 periodos; ordenados por d�ficit acumulado, el m�s fuerte primero)

| Inicio | Fin | Meses | Observado (kg m-2) | Normal = suma de medianas (kg m-2) | D�ficit (kg m-2) | % de lo normal | Anomal�a T2M media (�C) |
|---|---|---|---|---|---|---|---|
| 2018-06 | 2019-04 | 11 | 1559.3 | 2179.0 | -619.7 | 72 % | +0.02 |
| 2009-08 | 2009-12 | 5 | 761.6 | 1157.2 | -395.6 | 66 % | +0.15 |
| 2020-04 | 2020-10 | 7 | 1045.5 | 1433.3 | -387.8 | 73 % | +0.52 |
| 2021-09 | 2022-01 | 5 | 753.0 | 1138.0 | -384.9 | 66 % | +0.06 |
| 2015-03 | 2015-09 | 7 | 969.5 | 1315.0 | -345.5 | 74 % | +0.04 |
| 2002-11 | 2003-03 | 5 | 705.4 | 937.0 | -231.5 | 75 % | +1.02 |
| 2021-05 | 2021-07 | 3 | 414.4 | 619.4 | -205.0 | 67 % | -0.34 |
| 2022-12 | 2023-03 | 4 | 494.1 | 681.6 | -187.5 | 72 % | +0.20 |
| 2014-01 | 2014-04 | 4 | 471.4 | 593.7 | -122.3 | 79 % | +0.65 |
| 2019-06 | 2019-07 | 2 | 310.9 | 428.2 | -117.2 | 73 % | +0.32 |
| 2013-04 | 2013-05 | 2 | 258.9 | 331.3 | -72.4 | 78 % | -0.06 |

### B. Jaragua


**Precipitaci�n IMERG** (16 periodos; ordenados por d�ficit acumulado, el m�s fuerte primero)

| Inicio | Fin | Meses | Observado (mm) | Normal = suma de medianas (mm) | D�ficit (mm) | % de lo normal | Anomal�a T2M media (�C) |
|---|---|---|---|---|---|---|---|
| 2015-04 | 2015-07 | 4 | 89.9 | 297.3 | -207.4 | 30 % | -0.33 |
| 2020-04 | 2020-06 | 3 | 64.9 | 215.2 | -150.3 | 30 % | +0.52 |
| 2015-09 | 2015-10 | 2 | 97.5 | 240.0 | -142.5 | 41 % | -0.04 |
| 2021-09 | 2021-10 | 2 | 100.8 | 240.0 | -139.2 | 42 % | +0.22 |
| 2019-04 | 2019-06 | 3 | 77.0 | 215.2 | -138.2 | 36 % | -0.20 |
| 2001-08 | 2001-09 | 2 | 109.0 | 241.8 | -132.8 | 45 % | -0.02 |
| 2004-10 | 2004-11 | 2 | 73.0 | 198.5 | -125.5 | 37 % | -0.21 |
| 2023-05 | 2023-06 | 2 | 50.8 | 168.1 | -117.2 | 30 % | +0.81 |
| 2017-07 | 2017-08 | 2 | 109.7 | 215.2 | -105.5 | 51 % | +0.04 |
| 2018-11 | 2018-12 | 2 | 28.4 | 99.4 | -71.1 | 29 % | -0.31 |
| 2021-04 | 2021-05 | 2 | 63.6 | 133.4 | -69.8 | 48 % | -0.25 |
| 2022-12 | 2023-03 | 4 | 37.7 | 102.4 | -64.7 | 37 % | -0.14 |
| 2005-02 | 2005-03 | 2 | 11.9 | 52.0 | -40.2 | 23 % | -0.40 |
| 2010-02 | 2010-03 | 2 | 27.0 | 52.0 | -25.0 | 52 % | +0.47 |
| 2021-12 | 2022-01 | 2 | 25.3 | 50.3 | -25.0 | 50 % | +0.08 |
| 2021-01 | 2021-02 | 2 | 19.9 | 41.3 | -21.4 | 48 % | +0.24 |

**Humedad suelo 0-10 cm GLDAS** (14 periodos; ordenados por d�ficit acumulado, el m�s fuerte primero)

| Inicio | Fin | Meses | Observado (kg m-2) | Normal = suma de medianas (kg m-2) | D�ficit (kg m-2) | % de lo normal | Anomal�a T2M media (�C) |
|---|---|---|---|---|---|---|---|
| 2015-05 | 2015-10 | 6 | 133.5 | 158.5 | -25.0 | 84 % | -0.28 |
| 2021-09 | 2022-01 | 5 | 114.5 | 131.0 | -16.5 | 87 % | +0.17 |
| 2019-04 | 2019-08 | 5 | 107.1 | 123.5 | -16.4 | 87 % | -0.08 |
| 2009-10 | 2009-12 | 3 | 69.9 | 83.0 | -13.2 | 84 % | +0.04 |
| 2014-01 | 2014-04 | 4 | 66.4 | 79.4 | -13.0 | 84 % | +0.02 |
| 2018-11 | 2018-12 | 2 | 41.1 | 53.5 | -12.3 | 77 % | -0.31 |
| 2020-04 | 2020-05 | 2 | 35.3 | 47.6 | -12.3 | 74 % | +0.59 |
| 2018-06 | 2018-08 | 3 | 64.2 | 75.9 | -11.7 | 85 % | -0.49 |
| 2014-06 | 2014-07 | 2 | 40.8 | 49.9 | -9.1 | 82 % | -0.42 |
| 2021-05 | 2021-06 | 2 | 42.6 | 50.4 | -7.8 | 85 % | -0.30 |
| 2013-08 | 2013-09 | 2 | 46.8 | 53.9 | -7.1 | 87 % | -0.35 |
| 2023-02 | 2023-04 | 3 | 53.0 | 59.3 | -6.3 | 89 % | -0.05 |
| 2005-02 | 2005-03 | 2 | 31.0 | 36.8 | -5.8 | 84 % | -0.40 |
| 2016-01 | 2016-02 | 2 | 33.0 | 38.4 | -5.3 | 86 % | +0.14 |

**Humedad zona radicular GLDAS** (9 periodos; ordenados por d�ficit acumulado, el m�s fuerte primero)

| Inicio | Fin | Meses | Observado (kg m-2) | Normal = suma de medianas (kg m-2) | D�ficit (kg m-2) | % de lo normal | Anomal�a T2M media (�C) |
|---|---|---|---|---|---|---|---|
| 2018-11 | 2019-12 | 14 | 2695.7 | 3287.1 | -591.4 | 82 % | -0.04 |
| 2014-12 | 2015-11 | 12 | 2249.1 | 2751.2 | -502.1 | 82 % | -0.13 |
| 2022-12 | 2023-05 | 6 | 1102.6 | 1309.1 | -206.5 | 84 % | +0.02 |
| 2021-11 | 2022-02 | 4 | 783.7 | 958.6 | -174.9 | 82 % | +0.16 |
| 2020-04 | 2020-07 | 4 | 736.1 | 882.9 | -146.8 | 83 % | +0.53 |
| 2013-08 | 2013-10 | 3 | 611.5 | 709.2 | -97.6 | 86 % | -0.29 |
| 2009-10 | 2009-11 | 2 | 442.1 | 528.2 | -86.0 | 84 % | -0.10 |
| 2014-03 | 2014-05 | 3 | 549.7 | 632.0 | -82.2 | 87 % | -0.11 |
| 2018-07 | 2018-09 | 3 | 598.4 | 680.6 | -82.2 | 88 % | -0.45 |

## Lectura rápida (solo lo que sale de las tablas)

- **Noroeste.** Por déficit de lluvia, los periodos más fuertes son 2020-04..06 (43 % de lo normal), 2022-10..12 (45 %), 2009-09..11 (58 %), 2019-04..06 (60 %) y 2018-11..2019-01 (37 %). En la zona radicular de GLDAS, el periodo más largo y con más déficit es 2018-06..2019-04 (11 meses, 72 %). Le siguen 2009-08..12, 2020-04..10, 2021-09..2022-01 y 2015-03..09.
- **Jaragua.** Por déficit de lluvia, los periodos más fuertes son 2015-04..07 (30 %), 2020-04..06 (30 %), 2015-09..10 (41 %), 2021-09..10 (42 %) y 2019-04..06 (36 %). En la zona radicular, los dos periodos largos son 2018-11..2019-12 (14 meses, 82 %) y 2014-12..2015-11 (12 meses, 82 %).
- Hay periodos que aparecen en las dos regiones y en más de una variable: 2015, 2018-2019, 2020 (abril a junio, con T2M +0.5 a +0.9 °C sobre lo normal), 2021-2022 y el final de 2009.

## Problemas encontrados

1. **Descargas bloqueadas.** Los 3 primeros CSV se bajaron con el botón de descarga de Giovanni. Después, el navegador dejó de guardar archivos de ese sitio, probablemente por el bloqueo de "descargas múltiples automáticas". No cambié esa configuración. Los otros 5 CSV se leyeron como texto desde el mismo enlace "CSV" de Giovanni, dentro de la pestaña, y se escribieron con el mismo formato. Diferencias: valores redondeados a 4 decimales y una fila "Note:" en la cabecera. Para cada serie, la suma de los 288 valores coincide exactamente con la suma calculada sobre el CSV original de Giovanni. Si se quieren los originales byte a byte, se pueden regenerar con la URL de su cabecera.
2. **El primer clic en CSV dio "502 Proxy Error"** en `serializer.pl`. Al reintentarlo, funcionó.
3. **Celdas sin datos en GLDAS en la costa.** Ver "Cajas usadas". Por eso las series de GLDAS no cubren exactamente las mismas cajas que IMERG.
4. **MERRA-2 usa una sola celda por región.** Su centro cae fuera de la caja pedida (-71.25,20.0 y -71.25,17.5) y la celda es mucho más grande que la caja. Giovanni no rechazó la caja, así que no hizo falta agrandarla. T2M es contexto regional, no una medida local.
5. **Limitaciones del método.** No es un índice estandarizado como SPI o SPEI. El percentil 20 sale de solo 24 años, y por construcción el 20 % de los meses queda marcado como seco. Algunas rachas de 2 meses pueden ser azar. GLDAS es un modelo forzado con precipitación y no es independiente de los datos de lluvia.

## Verificación de los 5 CSV reconstruidos (2026-11-14)

Se regeneraron las 5 consultas en Giovanni y se descargó el CSV original completo:
`<nombre>.giovanni_original.csv`, junto a cada reconstruido. El pipeline lee el reconstruido e
ignora los originales; los originales quedan como prueba.

Resultado: mismas 288 fechas en el mismo orden, y **los 1440 valores reconstruidos son exactamente
`round(original, 4)`**. Diferencia máxima: 5.0e-05 (un empate de redondeo en gldas_rootmoist_noroeste,
2023-02-01: 112.67775 → 112.6778).

Diferencias solo en la cabecera de los reconstruidos: la fila `Title` está resumida en 4 de los 5 archivos
(GLDAS y MERRA-2), la fila `URL to Reproduce Results` es la versión corta (también reproduce el resultado)
y existe la fila `Note`. Caja, valor de relleno y nombres de columna son idénticos.
