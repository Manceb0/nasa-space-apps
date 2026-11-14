# RESULTS

Generado por `phantom.pipeline` el 2026-11-14 19:06 UTC. Este archivo se reescribe en cada corrida; no editarlo a mano.

## 1. Datos climáticos (Giovanni)

| Archivo | Fechas | Faltantes | Reconstruido | OK |
|---|---|---|---|---|
| `gldas_rootmoist_jaragua.csv` | 288 (2001-01-01 → 2024-12-01) | 0 | sí | sí |
| `gldas_rootmoist_noroeste.csv` | 288 (2001-01-01 → 2024-12-01) | 0 | sí | sí |
| `gldas_soilmoi0_10cm_jaragua.csv` | 288 (2001-01-01 → 2024-12-01) | 0 | sí | sí |
| `gldas_soilmoi0_10cm_noroeste.csv` | 288 (2001-01-01 → 2024-12-01) | 0 | no | sí |
| `imerg_precip_jaragua.csv` | 288 (2001-01-01 → 2024-12-01) | 0 | sí | sí |
| `imerg_precip_noroeste.csv` | 288 (2001-01-01 → 2024-12-01) | 0 | no | sí |
| `merra2_t2m_jaragua.csv` | 288 (2001-01-01 → 2024-12-01) | 0 | sí | sí |
| `merra2_t2m_noroeste.csv` | 288 (2001-01-01 → 2024-12-01) | 0 | no | sí |

## 2. Sequías usadas para el análisis (SPI-3 ≤ −1 durante 2+ meses, IMERG)

| Región | Inicio | Fin | Meses | Severidad (suma SPI-3) | Pico | Vuelve a SPI-3 ≥ 0 |
|---|---|---|---|---|---|---|
| jaragua | 2015-05 | 2015-11 | 7 | -10.86 | -2.07 | 2015-12 |
| jaragua | 2023-01 | 2023-06 | 6 | -9.24 | -2.24 | 2023-08 |
| jaragua | 2004-12 | 2005-04 | 5 | -8.68 | -2.44 | 2005-05 |
| jaragua | 2020-05 | 2020-07 | 3 | -5.45 | -2.06 | 2020-08 |
| jaragua | 2021-11 | 2022-01 | 3 | -5.25 | -2.16 | 2022-03 |
| jaragua | 2019-04 | 2019-06 | 3 | -4.22 | -1.65 | 2019-09 |
| jaragua | 2013-03 | 2013-05 | 3 | -3.77 | -1.40 | 2013-07 |
| jaragua | 2001-08 | 2001-09 | 2 | -3.69 | -1.87 | 2001-12 |
| jaragua | 2009-10 | 2009-11 | 2 | -2.81 | -1.45 | 2010-01 |
| jaragua | 2017-08 | 2017-09 | 2 | -2.66 | -1.44 | 2017-11 |
| jaragua | 2018-12 | 2019-01 | 2 | -2.62 | -1.55 | 2019-09 |
| jaragua | 2018-08 | 2018-09 | 2 | -2.44 | -1.30 | 2019-09 |
| jaragua | 2021-05 | 2021-06 | 2 | -2.43 | -1.24 | 2022-03 |
| jaragua | 2014-11 | 2014-12 | 2 | -2.24 | -1.20 | 2015-01 |
| jaragua | 2002-08 | 2002-09 | 2 | -2.12 | -1.07 | 2003-02 |
| noroeste | 2015-04 | 2015-11 | 8 | -13.21 | -2.52 | 2016-05 |
| noroeste | 2020-04 | 2020-07 | 4 | -7.69 | -2.45 | 2021-08 |
| noroeste | 2022-12 | 2023-03 | 4 | -7.55 | -2.06 | 2023-08 |
| noroeste | 2019-05 | 2019-08 | 4 | -5.70 | -1.86 | 2019-09 |
| noroeste | 2011-02 | 2011-04 | 3 | -5.02 | -2.01 | 2011-06 |
| noroeste | 2018-07 | 2018-09 | 3 | -5.00 | -1.84 | 2019-09 |
| noroeste | 2019-01 | 2019-03 | 3 | -4.97 | -2.10 | 2019-09 |
| noroeste | 2013-11 | 2014-01 | 3 | -4.41 | -1.75 | 2014-05 |
| noroeste | 2002-09 | 2002-11 | 3 | -4.41 | -1.71 | 2003-01 |
| noroeste | 2009-10 | 2009-12 | 3 | -4.30 | -1.71 | 2010-02 |
| noroeste | 2021-11 | 2022-01 | 3 | -3.61 | -1.50 | 2022-02 |
| noroeste | 2013-03 | 2013-04 | 2 | -3.49 | -1.96 | 2013-07 |
| noroeste | 2022-06 | 2022-07 | 2 | -2.67 | -1.54 | 2022-09 |

Catálogo completo con los tres criterios: `results/sequias_catalogo.csv`. Figuras: `figures/fig1_sequias.pdf` y `figures/fig2_criterios_sequia.pdf` (leyendas en `figures/LEYENDAS.md`).

## 3. Recuperación verde vs. función (MODIS)

- Filas evento × punto × señal: 108
- Estados: {'sin_impacto': 53, 'ambos_recuperados': 24, 'sin_impacto_funcion': 18, 'sin_impacto_verde': 7, 'ambos_censurados': 4, 'verde_censurado': 2}
- Etiquetas de robustez: {'SIN DATOS SUFICIENTES': 84, 'SENSIBLE A SUPUESTOS': 20, 'ROBUSTO': 4}
- Pruebas estadísticas hechas (para leer los p con cuidado): 18

Δt medio (días, función − verde, solo eventos con ambas recuperaciones):

- `gpp_modelo`: n = 11, media = -22 días, IC95 bootstrap = [-65, 15]
- `lst_menos_aire`: n = 13, media = -32 días, IC95 bootstrap = [-60, -12]

De 24 comparaciones con ambas recuperaciones: 19 dentro de ±32 días (precisión del método), 4 con la función antes que el verdor y 1 después.
Robustos (≥ 80 % de las combinaciones con el mismo signo y |mediana| > 32 días): jaraguacomparacionseco 2015-05 gpp_modelo Δt = 104; montecristimontesecob 2013-11 lst_menos_aire Δt = -8; montecristimontesecob 2020-04 lst_menos_aire Δt = -8; sierramontecristi 2022-12 lst_menos_aire Δt = -88.

Casos donde la función toca fondo después de que el verdor ya se recuperó (otra caída, no una recuperación tardía): jaraguacomparacionseco 2004-12 gpp_modelo; jaraguacomparacionseco 2015-05 gpp_modelo; jaraguacomparacionseco 2017-08 gpp_modelo; jaraguacomparacionseco 2020-05 gpp_modelo; sierramontecristi 2021-11 lst_menos_aire.

**Lectura:** en estos puntos la hipótesis de PHANTOM (la función se recupera *después* del verdor) no se sostiene. El único caso robusto en esa dirección (GPP, un modelo, en Jaragua 2015) es una caída de GPP que empieza después de que el NDVI ya se había recuperado: no es una recuperación tardía. El IC bootstrap trata cada comparación como independiente, pero no lo son (los puntos de Montecristi comparten sequías); es optimista.

Detalle: `results/recuperacion_eventos.csv`, `results/sensibilidad.csv`, `results/tendencias.csv`.

Cinco puntos son una exploración. Estos números no describen bosques completos.

## 4. Tendencias 2001–2024 (herramienta de detective)

Anomalía anual (se quita el ciclo estacional). Pendiente Theil-Sen por década con IC 95 %; p de Mann-Kendall corregido por autocorrelación AR(1); q de Benjamini-Hochberg sobre las 14 series. Las series MODIS son la media de anomalías de los puntos de cada zona (años con 9 meses o más).

| Serie | Pendiente / década | IC 95 % | p corregido (p simple) | q | Veredicto | Ventanas que engañan |
|---|---|---|---|---|---|---|
| Lluvia · Montecristi | -14.023 mm/mes | [-29.060, -1.155] | 0.031 (0.031) | 0.128 | baja | — |
| Lluvia · Jaragua | -2.315 mm/mes | [-17.203, +11.108] | 0.867 (0.823) | 0.867 | sin_evidencia | 2005–2021, 2005–2022, 2007–2021 |
| Temperatura del aire · Montecristi | +0.162 °C | [-0.003, +0.347] | 0.234 (0.063) | 0.364 | sin_evidencia | 2008–2024, 2009–2024, 2008–2023 |
| Temperatura del aire · Jaragua | +0.127 °C | [-0.031, +0.315] | 0.325 (0.130) | 0.414 | sin_evidencia | 2011–2023, 2008–2023, 2012–2023 |
| Humedad del suelo · Montecristi | -0.987 kg/m² | [-1.884, +0.272] | 0.279 (0.130) | 0.390 | sin_evidencia | 2005–2022, 2005–2021, 2006–2021 |
| Humedad del suelo · Jaragua | -1.204 kg/m² | [-2.133, +0.029] | 0.184 (0.063) | 0.321 | sin_evidencia | 2005–2016, 2005–2015, 2005–2020 |
| Agua para las raíces · Montecristi | -17.518 kg/m² | [-35.488, +0.098] | 0.150 (0.050) | 0.300 | sin_evidencia | 2004–2022, 2004–2021, 2005–2022 |
| Agua para las raíces · Jaragua | -22.846 kg/m² | [-42.010, -4.252] | 0.132 (0.021) | 0.300 | sin_evidencia | 2004–2023, 2004–2020, 2004–2022 |
| Verdor de la vegetación · Montecristi | -0.067 NDVI | [-0.102, -0.029] | 0.010 (0.002) | 0.128 | baja | — |
| Verdor de la vegetación · Jaragua | +0.003 NDVI | [-0.005, +0.009] | 0.556 (0.472) | 0.605 | sin_evidencia | — |
| Temperatura de la superficie · Montecristi | +1.161 °C | [+0.484, +2.024] | 0.037 (0.004) | 0.128 | sube | — |
| Temperatura de la superficie · Jaragua | -0.123 °C | [-0.316, +0.034] | 0.119 (0.097) | 0.300 | sin_evidencia | 2005–2024 |
| Productividad estimada · Montecristi | -0.626 gC/m²/día | [-1.083, -0.193] | 0.023 (0.003) | 0.128 | baja | — |
| Productividad estimada · Jaragua | +0.063 gC/m²/día | [-0.182, +0.262] | 0.562 (0.535) | 0.605 | sin_evidencia | 2005–2022, 2003–2022, 2005–2021 |

Lectura: con p corregido < 0,05 e IC sin el cero: Lluvia · Montecristi (baja), Verdor de la vegetación · Montecristi (baja), Temperatura de la superficie · Montecristi (sube), Productividad estimada · Montecristi (baja). Al corregir por las 14 pruebas (q < 0,05) se mantienen: ninguna. "Sin evidencia" no significa "sin cambio": los IC muestran qué cambios siguen siendo posibles.
