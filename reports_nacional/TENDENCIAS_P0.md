# P0 · Tendencias de periodos secos y lluvia extrema en la República Dominicana (2001-2024)

Equipo Stellar Horizons · NASA Space Apps 2026 · reto *Be An Earth System Trend Detective!* · corrida 2026-11-15T01:58:47Z

**Pregunta.** ¿Cambiaron entre 2001 y 2024 los periodos secos y la lluvia extrema en la RD, dónde, cuánto, con qué incertidumbre, y lo confirman dos productos distintos? Todo lo que sigue es descriptivo: tendencias observadas, **sin atribución de causas**.

## Resumen

- **Tendencias robustas (IMERG y CHIRPS de acuerdo y significativas tras FDR): casi ninguna.** En los 21 índices anuales hay 0 celda-índice robustas de 442 × 21 posibles y 0 provincia-índice robustas; sumando estaciones, 2 celda-índice-periodo robustas.
- **Lluvia extrema (R20mm, R50mm, Rx1day, Rx5day, R95pTOT, R99pTOT, anual): sin tendencia detectable** a nivel de celda tras FDR (0 celda-índice significativas en IMERG, 1 en CHIRPS). Con 24 años solo se detectarían cambios grandes (tendencia mínima detectable de la serie nacional IMERG de Rx5day: 39 mm/década, 24 % de la media por década).
- **Las fuentes discrepan en la frecuencia y la intensidad de la lluvia diaria.** IMERG muestra menos días húmedos, más intensidad (SDII) y más rachas secas largas; CHIRPS muestra lo contrario o nada. Combinaciones en disputa (≥ 20 celdas significativas en cada producto con signo opuesto): SDII (año (ene-dic)), R1mm (estación seca (dic-abr)), RACHAS15 (estación seca (dic-abr)). Es una señal de los productos (cómo detectan llovizna, cómo reparten la lluvia entre días), no del clima, hasta que un tercer testigo la confirme.
- **Sequía (SPI):** sin tendencia en IMERG; CHIRPS indica más meses y eventos SPI-12 ≤ −1 en parte del país, pero para SPI-12 la prueba es **liberal** (falsos positivos medidos de hasta 0.20 frente a 0.05 nominal) y no se confirma con IMERG: no se presenta como hallazgo.
- **Falsos positivos medidos** (1 000 sustitutos por índice y método): tasa media de p < 0.05 por celda 0.063 (fases) y 0.051 (bloques), cerca del 0.05 nominal salvo en los índices SPI-12 y, en menor medida, PRCPTOT/R1mm de IMERG.
- 'Sin señal detectable' significa **no detectable con 24 años**, no 'sin cambio'. Nada aquí atribuye causas.

## 1 · Datos

| producto | tipo de fuente | resolución | días | uso |
|---|---|---|---|---|
| NASA GPM IMERG V07 Final diario (GPM_3IMERGDF.07) | recuperación satelital calibrada con pluviómetros (GPCC mensual) | 0.1° | 8 766 (2001-01-01 a 2024-12-31; día = 00-24 UTC) | producto principal |
| CHIRPS v2.0 diario (CHC/UCSB) | satélite + estaciones | 0.05° nativa, **agregada a 0.1°** por media de área | 8 766 | segundo producto (acuerdo) |

CHIRPS diario se descargó recortado en el servidor (IRI/LDEO Data Library, un netCDF por año, `data/tendencias/chirps_diario/`, URL + SHA-256 + licencia en `data/tendencias/MANIFEST.json`). Comprobación: noviembre de 2023 es idéntico a los GeoTIFF oficiales del CHC (diferencia máxima 0.0 mm en 60450 celda-días).

Coherencia diaria en las celdas analizadas: lluvia media 3.65 mm/día (IMERG) frente a 3.70 (CHIRPS); fracción de días ≥ 1 mm 0.332 frente a 0.313; correlación diaria mediana por celda 0.55.

**Dominio.** 442 celdas de 0.1° con ≥ 25 % de su área en RD (y más RD que Haití) para mapas y FDR; las 32 provincias (geoBoundaries ADM1) y el total nacional como media ponderada por área de los índices de las celdas (pesos `results/nacional/pesos_provincia_imerg.csv`). Comparación de productos en la **misma rejilla de 0.1°**: se agrega la lluvia diaria de CHIRPS (2 × 2 sub-celdas, solo tierra) y después se calculan los índices.

## 2 · Índices

Definiciones ETCCDI (Zhang et al. 2011), día húmedo = P ≥ 1 mm. Percentiles 95/99 de los días húmedos 2001-2024 por celda y producto (no existe 1961-1990 en estos productos). Rachas secas ≥ 10 y ≥ 15 días (definición propia). Sequía con SPI-3 y SPI-12 (McKee et al. 1993; gamma por mes calendario, estimador de Thom) ajustado sobre 2001-2024: meses del año con SPI ≤ −1, eventos que empiezan en el año, severidad Σ(−SPI) y duración media (2002-2024).

| id | índice | unidad |
|---|---|---|
| CDD | Días secos consecutivos (máx.) | días |
| CWD | Días húmedos consecutivos (máx.) | días |
| PRCPTOT | Lluvia total de días húmedos | mm |
| R1mm | Días húmedos (≥1 mm) | días |
| SDII | Intensidad diaria simple | mm/día |
| R20mm | Días de lluvia fuerte (≥20 mm) | días |
| R50mm | Días de lluvia muy fuerte (≥50 mm) | días |
| Rx1day | Lluvia máxima en 1 día | mm |
| Rx5day | Lluvia máxima en 5 días | mm |
| R95pTOT | Lluvia de días muy húmedos (>p95) | mm |
| R99pTOT | Lluvia de días extremadamente húmedos (>p99) | mm |
| RACHAS10 | Rachas secas de ≥10 días | rachas |
| RACHAS15 | Rachas secas de ≥15 días | rachas |
| SPI3_MESES | Meses en sequía (SPI-3 ≤ −1) | meses |
| SPI3_EVENTOS | Eventos de sequía SPI-3 | eventos |
| SPI3_SEVER | Severidad de sequía SPI-3 | adimensional |
| SPI3_DURAC | Duración media de sequía SPI-3 | meses |
| SPI12_MESES | Meses en sequía (SPI-12 ≤ −1) | meses |
| SPI12_EVENTOS | Eventos de sequía SPI-12 | eventos |
| SPI12_SEVER | Severidad de sequía SPI-12 | adimensional |
| SPI12_DURAC | Duración media de sequía SPI-12 | meses |

**Estaciones** (régimen bimodal del Caribe; Taylor et al. 2002, Gamble y Curtis 2008): seca dic-abr (dic del año anterior; 2002-2024), lluvias tempranas may-jul (incluye la sequía de medio verano de julio), lluvias tardías ago-nov (temporada de huracanes). Las rachas no cruzan el borde del bloque.

## 3 · Estadística

- **Magnitud:** pendiente de Theil-Sen por década con IC 95 % de Sen (usando la varianza de S corregida).
- **Significancia local:** Mann-Kendall modificado de **Hamed y Rao (1998)** (autocorrelación de los rangos de la serie sin tendencia, solo lags significativos; el factor no baja de 1), con corrección por empates.
- **Multiplicidad:** FDR de Benjamini-Hochberg entre las 442 celdas (o entre las 32 provincias) de cada índice × periodo × producto. **Significancia de campo** de Wilks (2016): α_FDR = 2·α_global = 0.10; una celda es 'FDR-significativa' si q ≤ 0.10, y el campo es significativo si hay al menos una.
- **Calibración con sustitutos** (`earthmemory.calibration`): campos sin tendencia que conservan autocorrelación y correlación espacial (fases aleatorias multivariadas y bloques circulares de 3 años); se repite la prueba completa y se mide la tasa empírica de falsos positivos y una p de campo por bootstrap.
- **Tendencia mínima detectable (MDT):** pendiente detectable con 80 % de potencia a α = 0.05 por esta misma prueba, con n años, σ de los residuos y su r1 (factor calibrado por Monte Carlo). Si |pendiente| < MDT y no es significativa, se informa **'no detectable con 24 años'**, no 'sin cambio'.
- **Clase de confianza de dos productos:** *robusta* (IMERG y CHIRPS FDR-significativos, mismo signo), *consistente* (mismo signo, uno significativo), *en disputa* (signos opuestos, al menos uno significativo), *sin señal detectable*. El signo es el de Sen; si Sen = 0 (frecuente en conteos) se usa el signo de S.

## 4 · Falsos positivos medidos

1000 sustitutos por método, índice anual y producto (19 índices).

| nivel | método | tasa de p<0.05 (media) | rango entre índices | sin corrección de Hamed-Rao | mapas nulos con ≥1 celda FDR |
|---|---|---|---|---|---|
| celdas | bloques | 0.051 | 0.030-0.099 | 0.058 | 0.049 |
| celdas | fases | 0.063 | 0.021-0.201 | 0.066 | 0.063 |
| provincias | bloques | 0.054 | 0.024-0.095 | 0.058 | 0.063 |
| provincias | fases | 0.059 | 0.018-0.189 | 0.061 | 0.073 |

Lectura: la tasa local debe quedar cerca o por debajo de 0.05; la columna de mapas nulos con al menos una celda FDR es la tasa de error de campo del criterio de Wilks (debería ser ≲ 0.10). Ver `figures/tendencias/fig4_calibracion_falsos_positivos.png`.

## 5 · Resultados (anual)

Celdas = 442 celdas de 0.1°. *sig* = FDR q ≤ 0.10. Clases: rob = robusta, cons = consistente, disp = en disputa. Nacional = serie media ponderada por área (Theil-Sen por década, IC 95 %, p de Hamed-Rao, MDT).

| índice | IMERG sig (↑/↓) | CHIRPS sig (↑/↓) | rob (↑/↓) | cons | disp | prov. rob | IMERG nacional /déc [IC95] p · MDT | CHIRPS nacional /déc [IC95] p · MDT |
|---|---|---|---|---|---|---|---|---|
| CDD | 0 (0/0) | 37 (0/37) | 0 (0/0) | 21 | 16 | 0 | -0.46 [-5.54, 4.40] p=0.901 · 8.82 | -2.73 [-4.60, -1.02] p=0.002 · 3.50 |
| CWD | 0 (0/0) | 0 (0/0) | 0 (0/0) | 0 | 0 | 0 | -0.79 [-2.54, 0.73] p=0.385 · 2.65 | -0.25 [-1.35, 0.77] p=0.535 · 1.49 |
| PRCPTOT | 0 (0/0) | 0 (0/0) | 0 (0/0) | 0 | 0 | 0 | -1.15 [-171.72, 170.86] p=1.000 · 295.18 | -126.67 [-282.60, 65.21] p=0.172 · 283.35 |
| R1mm | 123 (2/121) | 0 (0/0) | 0 (0/0) | 54 | 69 | 0 | -7.00 [-17.45, 0.96] p=0.070 · 15.99 | 0.59 [-4.24, 5.55] p=0.673 · 8.57 |
| SDII | 122 (122/0) | 72 (0/72) | 0 (0/0) | 5 | 160 | 0 | 0.73 [0.05, 1.59] p=0.035 · 1.06 | -1.05 [-2.20, 0.08] p=0.050 · 2.19 |
| R20mm | 0 (0/0) | 0 (0/0) | 0 (0/0) | 0 | 0 | 0 | 0.81 [-2.40, 4.21] p=0.747 · 5.21 | -2.46 [-5.96, 1.45] p=0.264 · 6.06 |
| R50mm | 0 (0/0) | 0 (0/0) | 0 (0/0) | 0 | 0 | 0 | 0.09 [-0.65, 0.94] p=0.637 · 1.29 | -0.80 [-1.63, 0.34] p=0.118 · 1.42 |
| Rx1day | 0 (0/0) | 0 (0/0) | 0 (0/0) | 0 | 0 | 0 | 6.46 [-9.22, 22.54] p=0.309 · 25.31 | -10.62 [-22.08, 0.40] p=0.063 · 20.95 |
| Rx5day | 0 (0/0) | 0 (0/0) | 0 (0/0) | 0 | 0 | 0 | 8.24 [-12.24, 28.81] p=0.413 · 39.42 | -20.55 [-49.39, -0.84] p=0.045 · 38.46 |
| R95pTOT | 0 (0/0) | 0 (0/0) | 0 (0/0) | 0 | 0 | 0 | 34.86 [-48.74, 108.22] p=0.359 · 133.85 | -92.23 [-188.79, 31.41] p=0.087 · 154.82 |
| R99pTOT | 0 (0/0) | 1 (0/1) | 0 (0/0) | 0 | 1 | 0 | 22.73 [-26.41, 68.49] p=0.333 · 78.29 | -41.46 [-92.72, 1.86] p=0.056 · 64.79 |
| RACHAS10 | 48 (48/0) | 0 (0/0) | 0 (0/0) | 16 | 32 | 0 | 0.78 [0.03, 1.29] p=0.035 · 1.33 | -0.51 [-1.06, 0.07] p=0.070 · 0.82 |
| RACHAS15 | 34 (34/0) | 1 (0/1) | 0 (0/0) | 5 | 30 | 0 | 0.61 [0.32, 0.80] p=0.001 · 0.50 | -0.56 [-1.04, -0.12] p=0.011 · 0.64 |
| SPI3_MESES | 0 (0/0) | 0 (0/0) | 0 (0/0) | 0 | 0 | 0 | 0.01 [-0.84, 1.24] p=1.000 · 2.08 | 0.87 [-0.23, 2.38] p=0.154 · 2.07 |
| SPI3_EVENTOS | 0 (0/0) | 0 (0/0) | 0 (0/0) | 0 | 0 | 0 | 0.04 [-0.39, 0.48] p=0.874 · 0.71 | 0.27 [-0.22, 0.77] p=0.224 · 0.73 |
| SPI3_SEVER | 0 (0/0) | 0 (0/0) | 0 (0/0) | 0 | 0 | 0 | 0.05 [-1.45, 1.90] p=0.958 · 3.41 | 1.14 [-0.26, 3.43] p=0.126 · 3.32 |
| SPI3_DURAC | 0 (0/0) | 0 (0/0) | 0 (0/0) | 0 | 0 | 0 | 0.00 [-0.52, 0.49] p=1.000 · 0.83 | 0.39 [-0.02, 0.98] p=0.096 · 1.14 |
| SPI12_MESES | 0 (0/0) | 95 (95/0) | 0 (0/0) | 81 | 14 | 0 | 0.23 [-0.64, 2.01] p=0.771 · 4.35 | 1.44 [0.00, 4.52] p=0.049 · 5.21 |
| SPI12_EVENTOS | 0 (0/0) | 151 (151/0) | 0 (0/0) | 131 | 20 | 0 | 0.06 [-0.14, 0.43] p=0.771 · 0.64 | 0.13 [0.00, 0.61] p=0.020 · 0.69 |
| SPI12_SEVER | 0 (0/0) | 183 (183/0) | 0 (0/0) | 161 | 22 | 0 | 0.22 [-0.76, 2.73] p=0.731 · 6.23 | 1.92 [0.00, 6.13] p=0.053 · 7.55 |
| SPI12_DURAC | 0 (0/0) | 0 (0/0) | 0 (0/0) | 0 | 0 | 0 | 0.23 [-1.28, 1.84] p=0.695 · 3.99 | 2.03 [-0.62, 7.25] p=0.124 · 14.60 |

Tabla completa (también estaciones): `results/tendencias/resumen_indices.csv`.

### Por estación (celdas robustas ↑/↓ · en disputa)

| índice | Año (ene-dic) | Estación seca (dic-abr) | Lluvias tempranas (may-jul) | Lluvias tardías (ago-nov) |
|---|---|---|---|---|
| CDD | 0/0 · 16 | 0/0 · 1 | 0/0 · 0 | 0/0 · 0 |
| CWD | 0/0 · 0 | 0/0 · 2 | 0/0 · 0 | 0/0 · 0 |
| PRCPTOT | 0/0 · 0 | 0/0 · 0 | 0/0 · 0 | 0/0 · 0 |
| R1mm | 0/0 · 69 | 0/2 · 106 | 0/0 · 0 | 0/0 · 19 |
| SDII | 0/0 · 160 | 0/0 · 0 | 0/0 · 203 | 0/0 · 53 |
| R20mm | 0/0 · 0 | 0/0 · 0 | 0/0 · 0 | 0/0 · 0 |
| R50mm | 0/0 · 0 | 0/0 · 0 | 0/0 · 0 | 0/0 · 0 |
| Rx1day | 0/0 · 0 | 0/0 · 0 | 0/0 · 0 | 0/0 · 0 |
| Rx5day | 0/0 · 0 | 0/0 · 0 | 0/0 · 0 | 0/0 · 0 |
| R95pTOT | 0/0 · 0 | 0/0 · 0 | 0/0 · 0 | 0/0 · 0 |
| R99pTOT | 0/0 · 1 | 0/0 · 0 | 0/0 · 0 | 0/0 · 0 |
| RACHAS10 | 0/0 · 32 | 0/0 · 5 | 0/0 · 1 | 0/0 · 0 |
| RACHAS15 | 0/0 · 30 | 0/0 · 117 | 0/0 · 0 | 0/0 · 0 |

## 6 · Qué se sostiene

- **R1mm (estación seca (dic-abr))**: 2 celdas robustas (0 en aumento, 2 en descenso; mayoría: descenso); 0 provincias robustas; 106 celdas en disputa.

**En disputa: los dos productos ven tendencias significativas en sentidos opuestos** (≥ 20 celdas cada uno):

- **SDII (año (ene-dic))**: IMERG 122 celdas significativas (122 ↑ / 0 ↓) frente a CHIRPS 72 (0 ↑ / 72 ↓); 160 celdas en disputa, 0 robustas.
- **R1mm (estación seca (dic-abr))**: IMERG 36 celdas significativas (0 ↑ / 36 ↓) frente a CHIRPS 102 (96 ↑ / 6 ↓); 106 celdas en disputa, 2 robustas.
- **RACHAS15 (estación seca (dic-abr))**: IMERG 38 celdas significativas (38 ↑ / 0 ↓) frente a CHIRPS 93 (0 ↑ / 93 ↓); 117 celdas en disputa, 0 robustas.

**Señal de un solo producto (no confirmada por el otro)** (≥ 20 celdas):

- CDD (año (ene-dic)): CHIRPS 37 celdas significativas (0 ↑ / 37 ↓), IMERG 0; 0 robustas, 16 en disputa.
- R1mm (año (ene-dic)): IMERG 123 celdas significativas (2 ↑ / 121 ↓), CHIRPS 0; 0 robustas, 69 en disputa. ⚠
- RACHAS10 (año (ene-dic)): IMERG 48 celdas significativas (48 ↑ / 0 ↓), CHIRPS 0; 0 robustas, 32 en disputa.
- RACHAS15 (año (ene-dic)): IMERG 34 celdas significativas (34 ↑ / 0 ↓), CHIRPS 1; 0 robustas, 30 en disputa.
- SPI12_MESES (año (ene-dic)): CHIRPS 95 celdas significativas (95 ↑ / 0 ↓), IMERG 0; 0 robustas, 14 en disputa. ⚠
- SPI12_EVENTOS (año (ene-dic)): CHIRPS 151 celdas significativas (151 ↑ / 0 ↓), IMERG 0; 0 robustas, 20 en disputa. ⚠
- SPI12_SEVER (año (ene-dic)): CHIRPS 183 celdas significativas (183 ↑ / 0 ↓), IMERG 0; 0 robustas, 22 en disputa. ⚠
- SDII (lluvias tempranas (may-jul)): CHIRPS 235 celdas significativas (0 ↑ / 235 ↓), IMERG 7; 0 robustas, 203 en disputa.
- R1mm (lluvias tardías (ago-nov)): IMERG 44 celdas significativas (0 ↑ / 44 ↓), CHIRPS 0; 0 robustas, 19 en disputa.
- SDII (lluvias tardías (ago-nov)): IMERG 56 celdas significativas (56 ↑ / 0 ↓), CHIRPS 0; 0 robustas, 53 en disputa.

Una señal que aparece en un solo producto, o en los dos con signo contrario, puede deberse a cambios en los productos (sensores, algoritmo, red de estaciones, forma de repartir la lluvia entre días) y **no se presenta como tendencia del clima**. ⚠ = prueba liberal para ese índice (tasa de falsos positivos medida > 0.075, sección 4).


## 7 · Qué NO es detectable con 24 años

Serie nacional IMERG, sin tendencia significativa; cambio que haría falta para detectarla con 80 % de potencia:

| índice | MDT por década | % de la media por década |
|---|---|---|
| CDD | 8.82 días | 22 % |
| CWD | 2.65 días | 23 % |
| PRCPTOT | 295.18 mm | 23 % |
| R1mm | 15.99 días | 13 % |
| R20mm | 5.21 días | 29 % |
| R50mm | 1.29 días | 41 % |
| Rx1day | 25.31 mm | 27 % |
| Rx5day | 39.42 mm | 24 % |
| R95pTOT | 133.85 mm | 37 % |
| R99pTOT | 78.29 mm | 64 % |
| SPI3_MESES | 2.08 meses | 110 % |
| SPI3_EVENTOS | 0.71 eventos | 79 % |
| SPI3_SEVER | 3.41 adimensional | 121 % |
| SPI3_DURAC | 0.83 meses | 44 % |
| SPI12_MESES | 4.35 meses | 198 % |
| SPI12_EVENTOS | 0.64 eventos | 152 % |
| SPI12_SEVER | 6.23 adimensional | 197 % |
| SPI12_DURAC | 3.99 meses | 98 % |

En celdas, la MDT mediana es mayor que en la serie nacional (más ruido): ver `mediana_mdt` en `resumen_indices.csv`. Para la cola extrema (Rx1day, R99pTOT, R50mm) los cambios detectables con 24 años son de decenas de por ciento por década: una tendencia moderada real pasaría desapercibida. **'Sin señal detectable' ≠ 'sin cambio'.**

## 8 · Límites

- **24 años** es corto para tendencias de extremos: la variabilidad interdecenal (ENOS, AMO) puede producir o tapar tendencias en esta ventana. Los resultados describen 2001-2024, no se extrapolan.
- **IMERG no es homogéneo en el tiempo**: su constelación de microondas pasivas y sus sensores de entrada cambian (p. ej. TRMM → GPM en 2014); tendencias en la frecuencia de días húmedos o en la intensidad pueden ser en parte artefactos de detección. Por eso se exige el acuerdo con CHIRPS.
- **CHIRPS diario no es independiente día a día**: el total de la péntada (anclado a estaciones) se reparte entre días con un campo de lluvia diaria de modelo/satélite; los índices diarios de CHIRPS (Rx1day, CDD, R1mm) heredan esa distribución. Tampoco es independiente de la red de estaciones, cuya densidad en RD cambia con el tiempo. Los dos productos usan infrarrojo geoestacionario y pluviómetros (GPCC en IMERG): **no son testigos totalmente independientes**.
- **SPI** ajustado sobre los mismos 24 años: un 'mes en sequía' es relativo a 2001-2024; con 24 valores por mes calendario la cola de la gamma es frágil.
- La rejilla de 0.1° (~11 km) promedia la lluvia convectiva: los extremos locales (estación) son mayores que los de la celda.
- El día de IMERG es 00-24 UTC (20:00-20:00 hora local); el de CHIRPS no es exactamente el mismo: discrepancias de un día afectan a Rx1day pero poco a Rx5day.
- Pruebas múltiples: FDR controla la proporción de falsos descubrimientos entre celdas, pero índices y estaciones no se corrigen entre sí (hay 56 combinaciones por producto); léanse como familias separadas.
- Asociación temporal, **no causalidad**.

## 9 · Archivos

- `results/tendencias/tendencias_celdas.csv`, `tendencias_provincias.csv` (columnas `fuente`, `tipo_fuente`, `pendiente_decada`, `ic95_inf`, `ic95_sup`, `p`, `q_fdr`, `clase_confianza`, `mdt`, …), `series_provincias.csv`, `resumen_indices.csv`, `calibracion_fpr.csv`, `por_indice/*.csv`, `corrida.json`.
- `results/tendencias/web/` (JSON para las pantallas; esquema en `CONTRATO.md`).
- `figures/tendencias/` (PNG 220 ppp + PDF).
- `notebooks/06_tendencias_sequia_y_extremos.ipynb` y `reports_nacional/notebooks_html/06_tendencias_sequia_y_extremos.html`.

## 10 · Reproducir

```
docker compose run --rm tendencias                       # descarga lo que falte, calcula, figuras, web, informe, cuaderno
docker compose run --rm --entrypoint "uv run --frozen --no-sync pytest -q tests/test_tendencias.py" tendencias
```

## Referencias

- Benjamini, Y., Hochberg, Y. (1995). Controlling the false discovery rate. *J. R. Stat. Soc. B* 57, 289-300.
- Edwards, D.C., McKee, T.B. (1997). Characteristics of 20th century drought in the United States at multiple time scales. Climatology Report 97-2, Colorado State University.
- Funk, C. et al. (2015). The climate hazards infrared precipitation with stations — a new environmental record for monitoring extremes. *Scientific Data* 2, 150066. doi:10.1038/sdata.2015.66
- Gamble, D.W., Curtis, S. (2008). Caribbean precipitation: review, model and prospect. *Progress in Physical Geography* 32, 265-276.
- Hamed, K.H., Rao, A.R. (1998). A modified Mann-Kendall trend test for autocorrelated data. *J. Hydrology* 204, 182-196.
- Huffman, G.J. et al. (2023). GPM IMERG Final Precipitation L3 1 day 0.1° V07. GES DISC. doi:10.5067/GPM/IMERGDF/DAY/07
- Karl, T.R., Nicholls, N., Ghazi, A. (1999). CLIVAR/GCOS/WMO workshop on indices and indicators for climate extremes. *Climatic Change* 42, 3-7.
- Livezey, R.E., Chen, W.Y. (1983). Statistical field significance and its determination by Monte Carlo techniques. *Mon. Wea. Rev.* 111, 46-59.
- McKee, T.B., Doesken, N.J., Kleist, J. (1993). The relationship of drought frequency and duration to time scales. 8th Conf. Applied Climatology, AMS, 179-184.
- Prichard, D., Theiler, J. (1994). Generating surrogate data for time series with several simultaneously measured variables. *Phys. Rev. Lett.* 73, 951-954.
- Sen, P.K. (1968). Estimates of the regression coefficient based on Kendall's tau. *JASA* 63, 1379-1389.
- Taylor, M.A., Enfield, D.B., Chen, A.A. (2002). Influence of the tropical Atlantic versus the tropical Pacific on Caribbean rainfall. *J. Geophys. Res.* 107(C9), 3127.
- Thom, H.C.S. (1958). A note on the gamma distribution. *Mon. Wea. Rev.* 86, 117-122.
- Wilks, D.S. (2016). "The stippling shows statistically significant grid points": how research results are routinely overstated and overinterpreted, and what to do about it. *BAMS* 97, 2263-2273.
- Zhang, X. et al. (2011). Indices for monitoring changes in extremes based on daily temperature and precipitation data. *WIREs Climate Change* 2, 851-870. doi:10.1002/wcc.147

