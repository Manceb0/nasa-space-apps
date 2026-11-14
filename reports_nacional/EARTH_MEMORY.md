# Earth Memory · República Dominicana (todo el país, a nivel de celda)

Stellar Horizons · NASA Space Apps 2026 · reto *Be An Earth System Trend Detective!*

> Pregunta: ¿por qué dos territorios con lluvia parecida pueden responder distinto (suelo, agua en la zona de raíces, evapotranspiración, temperatura)? Todo lo que sigue son **asociaciones** en productos satelitales y de modelo; nada aquí demuestra causa.

Informe generado por `earthmemory/report.py` a partir de la corrida (`results/nacional/corrida.json`). Periodo 2001-2024. Ningún número de este archivo está escrito a mano.

## 1. Resumen

- **Tendencia de lluvia IMERG (0.1°)**: 0/442 celdas con q < 0.05 tras calibrar contra sustitutos nulos (nominal: 0); mediana de la pendiente -2.91 mm/mes por década; p de campo 0.327.
- **Tendencia de humedad de la zona de raíces (0-100 cm)**: 8/65 celdas con q < 0.05 tras calibrar contra sustitutos nulos (nominal: 2); mediana de la pendiente -34.11 mm por década; p de campo 0.028.
- **Tendencia de temperatura del aire**: 6/65 celdas con q < 0.05 tras calibrar contra sustitutos nulos (nominal: 6); mediana de la pendiente 0.24 °C por década; p de campo 0.080.
- **Falsos positivos**: la prueba de tendencia da 0.044 (raíz) y 0.042 (lluvia) de p < 0.05 en mapas nulos (nominal 0.05). La prueba de pares da 0.187: **está inflada** y por eso todas las conclusiones de pares usan el p calibrado contra el nulo.
- **Pares con lluvia parecida**: 992 de 2080 pares de celdas; 11904 pruebas; q < 0.05 con p nominal: 3506; con p calibrado: 1311.
- **Contradicciones "volvió la lluvia, la raíz no"**: 96 episodios con IMERG; 68 con la lluvia que forzó a GLDAS.
- **Santo Domingo 18-nov-2023**: la celda IMERG más lluviosa registró 184 mm en el día UTC (211 mm en 2 días UTC); máximo de 24 h móviles con datos de media hora 195 mm. El pluviómetro de ONAMET reportó 431 mm: el producto en rejilla suaviza el extremo.

## 2. Datos, cobertura y límites

| Producto | Resolución | Celdas en la caja | Celdas que tocan RD | Celdas usadas (≥25 % en RD) | Ruta | DOI |
|---|---|---|---|---|---|---|
| GPM IMERG Final V07 mensual (archivos V07B) | 0.1° | 1014 | 489 | 442 | OPeNDAP gpm1 (Bearer) | 10.5067/GPM/IMERG/3B-MONTH/07 |
| GPM IMERG Final V07 diario | 0.1° | 1014 | 489 | 442 | OPeNDAP en la nube (Bearer); respaldo gpm1 | 10.5067/GPM/IMERGDF/DAY/07 |
| GPM IMERG Final V07 media hora (17-19 nov 2023) | 0.1° | 1014 | 489 | solo evento | OPeNDAP gpm1 (Bearer) | 10.5067/GPM/IMERG/3B-HH/07 |
| GLDAS Noah 2.1 mensual (SoilMoi0_10cm, RootMoist, Tair_f, Evap, Rainf_f) | 0.25° | 176 | 100 | 65 | OPeNDAP en la nube (DAP4, Bearer) | 10.5067/SXAVCZFAQLNO |
| NASA POWER (MERRA-2) — solo comprobación | 0.5° × 0.625° | 42 | — | 15 | API POWER | — |

- Meses IMERG faltantes: ninguno; días IMERG: 8766 (faltantes 0).
- Comparación honesta con el equipo chileno ProGarLabs (9 694 celdas IMERG + 419 MERRA-2 para Chile, según su página): Chile tiene ~15 veces la superficie de RD; aquí usamos 442 celdas IMERG 0.1° y 65 celdas GLDAS 0.25° con al menos 25 % de su área en RD (de 489 y 100 que la tocan).
- Límites (geoBoundaries gbOpen DOM ADM1, DOM-ADM1-93820187): fuente Natural Earth, licencia **Public Domain** según los metadatos de la API (no CC BY 4.0), 32 unidades, año representado 2022. Haití se toma de Natural Earth 10m v5.1.2 (dominio público) para excluir celdas dominadas por Haití.
- **GLDAS-2.1 se forzó con lluvia GPCP (desagregada con GDAS), no con IMERG, y no asimila datos de suelo.** Una "contradicción" entre lluvia IMERG y suelo GLDAS puede ser una diferencia entre productos y no un comportamiento del terreno. Por eso cada contradicción y cada contraste se recalcula con la lluvia de forzamiento del propio modelo (Rainf_f_tavg) y se etiqueta.
- IMERG Final V07 (mensual hasta 2025-09 en el archivo); aquí 2001-2024. Celda IMERG ≈ 10.5 × 10.6 km; GLDAS ≈ 26 × 28 km.
- SMAP L3/L4: no se descargó en esta corrida (prioridad menor que IMERG diario + GLDAS; requiere la rejilla EASE de 9 km). GRACE-FO: su resolución efectiva (~3°, ~300 km) cubre RD con 1-2 mascons; solo sirve como contexto nacional, no provincial; no se usó en el motor.
- AppEEARS nacional (MOD13A3 NDVI/EVI + MOD17A3HGF NPP, pedido 8ad4ac19-…): no hay GeoTIFF de AppEEARS en data/appeears/nacional (gancho listo). Cuando lleguen los GeoTIFF a `data/appeears/nacional/`, NDVI/EVI entran solos como respuestas (con su perfil de desfases SPI→NDVI) y se calcula la eficiencia de uso de la lluvia (NPP/lluvia).

- Comprobación con NASA POWER/MERRA-2 en 18 celdas POWER: mediana de r(SPI-3 IMERG, SPI-3 MERRA-2) = 0.43; mediana de r(z raíz GLDAS, z raíz MERRA-2) = 0.15 (`results/nacional/comparacion_power_merra2.csv`).

Rutas de descarga (de `data/nacional/MANIFEST.json`, sección `rutas`):

- `IMERG_M`: ok — 288 pedidos, 0 errores
- `GLDAS_M`: ok — 288 pedidos, 0 errores
- `IMERG_HH`: ok — 144 pedidos, 0 errores
- `GLDAS_RAIN`: ok — 288 pedidos, 0 errores
- `IMERG_D`: ok — 8766 pedidos, 0 errores
- `GRACE`: ok — 1 pedidos, 0 errores
- OPeNDAP de GLDAS en hydro1.gesdisc.eosdis.nasa.gov: `HTTP 410 Gone · The OPeNDAP service is no longer available` (retirado); se usó el OPeNDAP en la nube (opendap.earthdata.nasa.gov).
- Historial de la descarga del 2026-11-14: gpm1 devolvió `HTTP 503 Service Unavailable` intermitentes (2 meses IMERG y 1 media hora en el primer intento, recuperados al reintentar); el respaldo en la nube para los HDF5 de IMERG dio `HTTP 400` hasta usar la ruta del grupo `/Grid/` (corregido). IMERG diario se pidió a la nube con nombres de archivo construidos. GRACE: el OPeNDAP en la nube dio 404 para el granulo de mascons; se bajó el archivo completo (46 MB) por HTTPS con el token solo en el primer salto.

Todas las rutas terminaron sin errores pendientes.

### Contexto: agua total (GRACE/GRACE-FO)

- Media nacional de 22 celdas 0.5° de los mascons JPL RL06.3 CRI (240 meses con dato en 2001-2024; hueco 2017-07 a 2018-05 entre misiones). Mínimo -8.8 cm en 2004-05. Resolución efectiva ~3°: no se usa en celdas ni provincias. Figura `fig11_grace_contexto`.

## 3. Métodos (resumen)

- **Celdas**: rectángulos nativos de cada producto (sin interpolar). Fracción de cada celda en el país y en cada provincia con 12×12 (IMERG) o 25×25 (GLDAS) puntos ponderados por cos(lat). Celda incluida: ≥ 25 % en RD, más RD que Haití y (GLDAS) tierra en el modelo.
- **Lluvia en la celda GLDAS**: remapeo conservativo de IMERG (área de solape × fracción en RD de cada celda IMERG).
- **Provincias**: media ponderada por área (peso = área de la celda × fracción de la celda en la provincia).
- **Anomalías**: SPI-1/3/6 (gamma por mes calendario con masa en cero); z robusto (mediana/MAD por mes) para las respuestas.
- **Tendencias**: Theil-Sen + Mann-Kendall con corrección AR(1) sobre medias anuales de anomalías; BH por variable; p calibrado con 1 000 sustitutos de fases aleatorias multivariadas (misma fase en todas las celdas: conserva la autocorrelación y la correlación espacial) y control con bloques circulares de 24 meses; significancia de campo (Livezey y Chen 1983) e I de Moran de la pendiente.
- **Acople y memoria**: r(SPI-3, z) y ARX z(t) = c + φ z(t−1) + γ SPI-1(t); IC por bootstrap de bloques móviles (12 meses, mismos índices en todas las celdas).
- **Pares con lluvia parecida**: ≤ 150 km, r(SPI-3) ≥ 0.70 y lluvia anual a ≤ 25 %. Δ por bootstrap conjunto; p calibrado contra un nulo paramétrico (ARX común, mismo forzamiento, residuos en bloques conjuntos); BH sobre todas las pruebas; 11 variantes de sensibilidad + la variante "lluvia del modelo".
- **Episodios**: SPI-3 ≤ −1 por 2+ meses. A = la lluvia vuelve (SPI-3 ≥ 0) pero la raíz sigue con z < −1 ese mes y el siguiente; B1 = suelo seco sin sequía de lluvia; B2 = suelo normal en sequía de lluvia. Comparación justa: episodios de dos celdas que terminan con ≤ 2 meses de diferencia y SPI-3 mínimo parecido (|Δ| ≤ 0.5).
- **Factores** (asociación): fracción de lluvia en días > p95 de la celda y máximo en 1 día (IMERG diario remapeado), meses de sequía en los 12 previos, z antecedente; coeficiente estandarizado con control por severidad; IC por bootstrap por conglomerados de año; BH; sensibilidad (efectos fijos de celda, todos juntos, p90, 24 meses, retorno a −0.5, 3 meses).
- **Latigazos** (whiplash): SPI-3 o z cruza de ≤ −0.84 a ≥ +0.84 (o al revés) en ≤ 3 meses, umbral de Stojanovic et al. 2025 (Sci. Data 12:1700, doi:10.1038/s41597-025-05992-9), que usa MSWEP, trata La Española como una sola isla y no considera humedad del suelo; aquí se cuentan por celda para lluvia y para suelo.

## 4. Qué sobrevive a la corrección y qué no

### 4.1 Tendencias por celda

| Variable | Celdas | q<0.05 nominal | q<0.05 calibrado | p<0.05 observadas | p<0.05 en nulo (media / p95) | p de campo (fases / bloques) | I de Moran | Pendiente mediana |
|---|---|---|---|---|---|---|---|---|
| lluvia IMERG (0.1°) | 442 | 0 | 0 | 10 | 18.5 / 99.0 | 0.327 / 0.249 | 0.85 | -2.914 |
| humedad de la zona de raíces (0-100 cm) | 65 | 2 | 8 | 21 | 2.9 / 14.0 | 0.028 / 0.069 | 0.43 | -34.113 |
| humedad superficial (0-10 cm) | 65 | 0 | 0 | 11 | 2.6 / 15.0 | 0.084 / 0.106 | 0.39 | -1.560 |
| temperatura del aire | 65 | 6 | 6 | 11 | 3.6 / 12.0 | 0.080 / 0.138 | 0.25 | 0.240 |
| evapotranspiración | 65 | 0 | 0 | 0 | 3.0 / 17.0 | 1.000 / 1.000 | 0.23 | -0.072 |
| lluvia que forzó a GLDAS (0.25°) | 65 | 0 | 0 | 0 | 2.8 / 19.1 | 1.000 / 1.000 | 0.41 | -6.467 |
| lluvia IMERG remapeada a celdas GLDAS | 65 | 0 | 0 | 0 | 2.7 / 15.0 | 1.000 / 1.000 | 0.63 | -2.730 |

Las celdas vecinas no son pruebas independientes (I de Moran alto = pendientes muy parecidas entre vecinas). La significancia de campo responde a: "¿hay más celdas significativas de las que daría el azar con esta misma correlación espacial?". Una tendencia de 24 años no separa cambio de largo plazo de variabilidad decenal.

- humedad de la zona de raíces (0-100 cm): 2 celdas con q < 0.05 usando el p de Mann-Kendall AR(1) y 8 usando el p calibrado. Se informa el calibrado (su tasa de falsos positivos medida es la nominal); la diferencia indica que la corrección AR(1) con 24 valores anuales no reproduce exactamente la memoria de esta variable.
- humedad de la zona de raíces (0-100 cm): la significancia de campo depende del sustituto (fases 0.028, bloques 0.069): **no es robusta**.

Diagnóstico de productos: en las mismas 65 celdas GLDAS, la tendencia mediana de la lluvia que forzó a GLDAS es -6.1 % de su media por década y la de IMERG -2.4 %; r entre los dos mapas de pendiente = -0.25. Si el suelo de GLDAS baja más que la lluvia IMERG, parte de esa caída puede venir del forzamiento del modelo y no del terreno.

### 4.2 Calibración de falsos positivos

| Prueba | Sustituto | Tasa empírica p<0.05 | Mapas nulos con ≥1 descubrimiento BH |
|---|---|---|---|
| tendencia · lluvia IMERG (0.1°) | fases aleatorias multivariadas | 0.042 | 0.013 |
| tendencia · lluvia IMERG (0.1°) | bloques circulares de 24 meses | 0.055 | 0.020 |
| tendencia · humedad de la zona de raíces (0-100 cm) | fases aleatorias multivariadas | 0.044 | 0.018 |
| tendencia · humedad de la zona de raíces (0-100 cm) | bloques circulares de 24 meses | 0.061 | 0.029 |
| tendencia · humedad superficial (0-10 cm) | fases aleatorias multivariadas | 0.040 | 0.014 |
| tendencia · humedad superficial (0-10 cm) | bloques circulares de 24 meses | 0.057 | 0.025 |
| tendencia · temperatura del aire | fases aleatorias multivariadas | 0.055 | 0.095 |
| tendencia · temperatura del aire | bloques circulares de 24 meses | 0.060 | 0.054 |
| tendencia · evapotranspiración | fases aleatorias multivariadas | 0.046 | 0.017 |
| tendencia · evapotranspiración | bloques circulares de 24 meses | 0.063 | 0.035 |
| tendencia · lluvia que forzó a GLDAS (0.25°) | fases aleatorias multivariadas | 0.043 | 0.013 |
| tendencia · lluvia que forzó a GLDAS (0.25°) | bloques circulares de 24 meses | 0.053 | 0.022 |
| tendencia · lluvia IMERG remapeada a celdas GLDAS | fases aleatorias multivariadas | 0.042 | 0.020 |
| tendencia · lluvia IMERG remapeada a celdas GLDAS | bloques circulares de 24 meses | 0.055 | 0.025 |

Prueba de pares (nulo paramétrico, 30 pares × 100 sustitutos × 4 respuestas × 3 métricas):

| Respuesta | Métrica | n nulas | Tasa p<0.05 | σ (inflación EE) | Tasa tras calibrar | |Δ/EE| crítico 95 % |
|---|---|---|---|---|---|---|
| ET | gamma | 3000 | 0.065 | 1.02 | 0.060 | 2.10 |
| ET | phi | 3000 | 0.212 | 1.53 | 0.063 | 3.26 |
| ET | r_spi | 3000 | 0.111 | 1.26 | 0.043 | 2.40 |
| SM_0_10 | gamma | 3000 | 0.072 | 1.07 | 0.057 | 2.14 |
| SM_0_10 | phi | 3000 | 0.452 | 2.60 | 0.026 | 4.54 |
| SM_0_10 | r_spi | 3000 | 0.213 | 1.63 | 0.030 | 2.90 |
| SM_RAIZ | gamma | 3000 | 0.060 | 1.02 | 0.059 | 2.10 |
| SM_RAIZ | phi | 3000 | 0.316 | 2.07 | 0.015 | 3.33 |
| SM_RAIZ | r_spi | 3000 | 0.217 | 1.64 | 0.038 | 3.05 |
| TAIRE | gamma | 3000 | 0.068 | 1.04 | 0.059 | 2.15 |
| TAIRE | phi | 3000 | 0.354 | 2.03 | 0.083 | 4.56 |
| TAIRE | r_spi | 3000 | 0.103 | 1.18 | 0.053 | 2.36 |
| TODAS | TODAS | 36000 | 0.187 | 1.40 | 0.049 | 3.16 |

Lectura: nominal 5 %. La prueba de tendencia está bien calibrada (máximo 0.055). La prueba de pares con bootstrap de bloques da 0.187: el error estándar del bootstrap subestima la variabilidad real de Δ (bloques de 12 meses cortos para series con mucha memoria). **Corrección aplicada**: se mide cuánto subestima el bootstrap la variabilidad (factor de inflación σ por respuesta y métrica, columna `factor_inflacion_EE`) y el p calibrado usa |Δ/EE|/σ; tras calibrar, la tasa en el nulo es 0.049 (columna `tasa_p05_tras_calibrar`; medida en los mismos sustitutos, así que es un control de consistencia, no una validación independiente). Control adicional: `p_empirico_nulo` (posición en el nulo) en `pruebas_pares.csv`.

### 4.3 Pares

| # | A | B | Respuesta | Métrica | Δ [IC95] | q nominal | q calibrado | Robustez | Lluvia del modelo | km |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 19.625_-70.625 | 19.875_-70.875 | ET | gamma | -0.26 [-0.32, -0.21] | < 1e-15 | 1.82e-15 | 11/11 | sobrevive con la lluvia del modelo | 38 |
| 2 | 19.625_-70.375 | 19.875_-70.875 | ET | gamma | -0.23 [-0.29, -0.18] | 3.78e-13 | 2.16e-12 | 11/11 | sobrevive con la lluvia del modelo | 59 |
| 3 | 19.375_-70.125 | 19.875_-70.875 | ET | gamma | -0.31 [-0.40, -0.24] | 5.75e-12 | 5.36e-11 | 11/11 | sobrevive con la lluvia del modelo | 96 |
| 4 | 19.375_-70.375 | 19.875_-70.875 | ET | gamma | -0.27 [-0.35, -0.21] | 3.58e-11 | 4.9e-10 | 11/11 | sobrevive con la lluvia del modelo | 76 |
| 5 | 19.125_-70.875 | 19.875_-70.875 | ET | gamma | -0.40 [-0.52, -0.31] | 4.85e-11 | 5.73e-10 | 11/11 | sobrevive con la lluvia del modelo | 83 |
| 6 | 18.875_-70.375 | 19.375_-70.625 | SM_RAIZ | gamma | -0.13 [-0.16, -0.09] | 6.51e-11 | 6.05e-10 | 11/11 | sobrevive con la lluvia del modelo | 61 |
| 7 | 19.125_-69.625 | 19.375_-69.875 | SM_0_10 | gamma | -0.14 [-0.18, -0.10] | 3.72e-11 | 3.28e-09 | 11/11 | sobrevive con la lluvia del modelo | 38 |
| 8 | 19.125_-71.125 | 19.875_-70.875 | ET | gamma | -0.46 [-0.56, -0.37] | < 1e-15 | 5.73e-16 | 11/11 | sobrevive con la lluvia del modelo | 87 |
| 9 | 19.125_-71.125 | 19.875_-71.125 | ET | gamma | -0.34 [-0.44, -0.27] | 1.47e-12 | 1.13e-11 | 11/11 | sobrevive con la lluvia del modelo | 83 |
| 10 | 19.125_-71.125 | 19.625_-71.625 | ET | gamma | -0.34 [-0.44, -0.27] | 2.86e-12 | 2.44e-11 | 11/11 | sobrevive con la lluvia del modelo | 76 |

Robustez = variantes (de 11) en las que Δ mantiene el signo y su IC95 excluye 0. Dos pares que comparten celda no son dos hallazgos.

### 4.4 Factores asociados a la respuesta tras la sequía

| resultado | factor | n | β [IC95] | p | q |
|---|---|---|---|---|---|
| z_retorno_SM_RAIZ | fraccion_lluvia_intensa | 714 | -0.08 [-0.21, 0.06] | 0.259 | 0.484 |
| z_retorno_SM_RAIZ | lluvia_max_1dia_mm | 714 | -0.06 [-0.22, 0.16] | 0.531 | 0.58 |
| z_retorno_SM_RAIZ | meses_sequia_previos | 714 | -0.11 [-0.26, 0.14] | 0.296 | 0.484 |
| z_retorno_SM_RAIZ | z_antecedente | 714 | 0.46 [0.24, 0.60] | 2.29e-07 | 2.75e-06 |
| z_retorno_SM_0_10 | fraccion_lluvia_intensa | 714 | -0.07 [-0.25, 0.11] | 0.419 | 0.559 |
| z_retorno_SM_0_10 | lluvia_max_1dia_mm | 714 | -0.15 [-0.34, 0.15] | 0.277 | 0.484 |
| z_retorno_SM_0_10 | meses_sequia_previos | 714 | -0.09 [-0.25, 0.13] | 0.322 | 0.484 |
| z_retorno_SM_0_10 | z_antecedente | 714 | 0.22 [0.05, 0.38] | 0.00809 | 0.0324 |
| contradiccion_A_SM_RAIZ | fraccion_lluvia_intensa | 714 | 0.01 [-0.03, 0.04] | 0.498 | 0.58 |
| contradiccion_A_SM_RAIZ | lluvia_max_1dia_mm | 714 | 0.01 [-0.05, 0.05] | 0.614 | 0.614 |
| contradiccion_A_SM_RAIZ | meses_sequia_previos | 714 | 0.04 [-0.02, 0.08] | 0.121 | 0.363 |
| contradiccion_A_SM_RAIZ | z_antecedente | 714 | -0.11 [-0.14, -0.05] | 1.2e-05 | 7.19e-05 |

β = cambio del resultado (en unidades del resultado) por 1 DE del factor, con control por severidad. IC por bootstrap de conglomerados de año (las celdas vecinas viven la misma sequía a la vez). Asociación, no causa.

- z_retorno_SM_RAIZ ~ z_antecedente: mantiene signo con IC que excluye 0 en 6/6 variantes de sensibilidad.
- z_retorno_SM_0_10 ~ z_antecedente: mantiene signo con IC que excluye 0 en 6/6 variantes de sensibilidad.
- contradiccion_A_SM_RAIZ ~ z_antecedente: mantiene signo con IC que excluye 0 en 6/6 variantes de sensibilidad.

### 4.5 Contradicciones y latigazos

Episodios A (raíz) con IMERG y su etiqueta frente a la lluvia del modelo: posible diferencia entre productos: 50; también con la lluvia del modelo: 46.
Latigazos seco→húmedo (suma de todas las celdas): lluvia_imerg_spi3: 501; suelo_raiz_z: 67; suelo_sup_z: 272; lluvia_modelo_spi3: 548.

## 5. El caso dominicano más sólido para la demo

- A = celda 18.875_-70.375 (Monseñor Nouel 86 %, Sánchez Ramírez 10 %); B = celda 19.375_-70.625 (Santiago 45 %, La Vega 36 %, Espaillat 19 %); distancia 61 km; r(SPI-3) = 0.93; diferencia de lluvia anual 0.3 %; diferencia de elevación (GLDAS) 163 m.
- humedad de la zona de raíces (0-100 cm), sensibilidad inmediata γ (ARX): A = 0.12, B = 0.25, Δ = -0.13 (IC95 -0.16 a -0.09); q nominal 6.51e-11, **q calibrado 6.05e-10**; robustez 11/11; con la lluvia del modelo Δ = -0.15 (IC95 -0.18 a -0.11) → sobrevive con la lluvia del modelo.
  - Episodios emparejados, z_retorno (A − B): media -0.63 [-1.15, -0.13], n = 8, Wilcoxon p = 0.0547.
  - Episodios emparejados, meses_recuperacion (A − B): media 2.00 [-0.60, 4.20], n = 5, Wilcoxon p = 0.25.
  - Episodios emparejados, fraccion_intensa (A − B): media -2.35e-03 [-0.06, 0.06], n = 8, Wilcoxon p = 0.547.
  - Episodios emparejados, max1d (A − B): media -0.93 [-13.88, 10.30], n = 8, Wilcoxon p = 0.945.
  - Episodios emparejados, z_antecedente (A − B): media -0.08 [-0.53, 0.28], n = 10, Wilcoxon p = 0.557.
  - Episodios emparejados, meses_previos (A − B): media -1.20 [-2.30, -0.20], n = 10, Wilcoxon p = 0.0938.

Figura: `figures/nacional/fig07_mejor_contraste.png`.

## 6. "Estos dos territorios recibieron lluvias comparables. Sin embargo, sus respuestas ambientales fueron distintas"

Verificado para el par de la sección 5: lluvia comparable (r(SPI-3) = 0.93, lluvia anual a 0.3 %) y sensibilidad inmediata γ (ARX) de humedad de la zona de raíces (0-100 cm) distinta (Δ = -0.13, q calibrado 6.05e-10), también con la lluvia del propio modelo. ¿Por qué? Dentro de GLDAS, dos celdas con la misma lluvia solo pueden responder distinto por lo que el modelo les asigna a cada una (textura del suelo, tipo de vegetación, profundidad de raíces) y por su forzamiento local de radiación y temperatura; por eso este contraste es una **hipótesis sobre el terreno** que hay que contrastar con suelos y cobertura reales (extensión de alta resolución) y con observaciones (SMAP, NDVI). Las asociaciones de la sección 4.4 no prueban causa. El resultado es del modelo GLDAS, no una medición del suelo.

## 7. Santo Domingo, 18 de noviembre de 2023

- Referencia: 431 mm en 24 h el sábado 18-nov-2023 en la estación de ONAMET Arroyo Hondo Viejo (dato preliminar; 474 mm acumulados desde el jueves). Es un pluviómetro (un punto); NASA no publicó una magnitud IMERG para este evento: todo valor IMERG aquí es cálculo nuestro sobre IMERG Final V07.
- 21 celdas IMERG 0.1° tocan el Distrito Nacional y la provincia Santo Domingo.
- Celda más lluviosa (18.650_-69.950): 183.9 mm el 18-nov (día UTC) y 27.1 mm el 19-nov (día UTC); puesto 1 de 8766 días 2001-2024; puesto 1 entre los 24 máximos anuales (periodo de retorno empírico ≈ 25 años, Weibull); mediana de los máximos anuales 86 mm; récord de la celda 184 mm (2023-11-18).
- Celdas donde el 18-nov fue el día más lluvioso de 2001-2024: 1 de 21.
- Media hora: máximo de 24 h móviles 195 mm en la celda 18.650_-69.950 (2023-11-18T02:30:00 a 2023-11-19T02:30:00 UTC); máximo en 30 min 22.8 mm; medias horas faltantes: 0.
- IMERG diario = día UTC (00-24 UTC = 20:00 del día anterior a 20:00 hora local). Una celda IMERG de 0.1° (~10.5 × 10.6 km) promedia el aguacero sobre ~110 km²; un pluviómetro mide un punto. Un solo evento no es una tendencia. Estos valores IMERG son cálculo nuestro; no existe una cifra IMERG publicada por NASA para el evento.

Figura: `figures/nacional/fig09_santo_domingo_2023.png`.

## 8. Rigor y alcance frente a competidores públicos

| Aspecto | ProGarLabs (Chile) | Earth Memory (RD) |
|---|---|---|
| Lluvia | IMERG (tendencias) | IMERG V07 mensual + diario + media hora |
| Temperatura | MERRA-2 T2M | Tair de GLDAS (+ T2M MERRA-2 vía POWER como control) |
| Suelo / raíz / ET | no | GLDAS Noah 2.1 (0-10 cm, 0-100 cm, ET), contrastado con su propia lluvia de forzamiento |
| Regiones | ponderadas por área | provincias ponderadas por área (32 unidades ADM1) |
| Calibración de falsos positivos | documentada | sustitutos de fases y de bloques (tendencias) + nulo paramétrico (pares); p calibrado |
| Multiplicidad | — | BH por familia + significancia de campo + I de Moran |
| Pregunta | ¿hay tendencia? | ¿por qué dos territorios con lluvia parecida responden distinto? (pares, episodios emparejados, factores) |
| Celdas | 9 694 IMERG + 419 MERRA-2 | 442 IMERG + 65 GLDAS (país ~15× más chico) |

Lo de ProGarLabs se toma de su descripción pública; no auditamos su código.

## 9. Reproducir y correr para otro país

```
docker compose run --rm nacional
```

Descarga lo que falte (caché con SHA-256), corre el motor IMERG+GLDAS, la comprobación POWER, figuras, informe y ejecuta los cuadernos (HTML en `reports_nacional/notebooks_html/`). El token de Earthdata se monta en `/run/secrets` en tiempo de ejecución (`.secrets/earthdata_token`, solo lectura); nunca entra a la imagen.

Otro país: `docker compose run --rm nacional --pais HTI` (código ISO3 de geoBoundaries; la caja se calcula del límite ADM1 + 0.05°; `--bbox LON0 LAT0 LON1 LAT1` la fija a mano). Ajustar `--evento`, `--evento-prov` y la lista de lugares si se quiere un evento local.

## 10. Extensión de alta resolución

El análisis a mayor resolución (CHIRPS 0.05°, TerraClimate ~4 km, suelos SoilGrids, relieve, cobertura WorldCover y umbrales críticos) se documenta aparte en [`ALTA_RESOLUCION.md`](ALTA_RESOLUCION.md) (paquete `earthmemory/hr/`, cuaderno `notebooks/05_alta_resolucion_y_umbrales.ipynb`). Este informe cubre el motor IMERG + GLDAS a resolución nativa de esos productos.

## 11. Figuras

- `figures/nacional/fig01_climatologias.png` / `.pdf`
- `figures/nacional/fig02_tendencias.png` / `.pdf`
- `figures/nacional/fig03_sequia_2015.png` / `.pdf`
- `figures/nacional/fig04_sequia_2019_2020.png` / `.pdf`
- `figures/nacional/fig05_contradicciones.png` / `.pdf`
- `figures/nacional/fig06_memoria_acople.png` / `.pdf`
- `figures/nacional/fig07_mejor_contraste.png` / `.pdf`
- `figures/nacional/fig08_calibracion_fpr.png` / `.pdf`
- `figures/nacional/fig09_santo_domingo_2023.png` / `.pdf`
- `figures/nacional/fig10_provincias.png` / `.pdf`
- `figures/nacional/fig11_grace_contexto.png` / `.pdf`
