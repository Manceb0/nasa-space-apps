# RESULTS

Generado por `phantom.pipeline` el 2026-11-14 16:00 UTC. Este archivo se reescribe en cada corrida; no editarlo a mano.

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

**Pendiente.** Sin resultados MODIS: no se calculó ninguna recuperación. Faltan: MOD11A2, MOD13Q1, MOD17A2HGF.

No hay ningún resultado sobre la brecha todavía.
