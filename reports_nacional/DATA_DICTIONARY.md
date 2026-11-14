# Diccionario de datos · Earth Memory nacional

Salidas de `python -m earthmemory.nacional` (Docker: `docker compose run --rm nacional`). Parquet ordenado (una fila por observación) en `results/nacional/parquet/`; CSV en `results/nacional/`. Celdas: id = `lat_lon` del centro. Fechas: primer día del mes. Generado automáticamente desde los archivos.

## `results/nacional/parquet/manifiesto.parquet`

9800 filas.

| columna | tipo | descripción |
|---|---|---|
| `archivo` | string |  |
| `url` | string | URL exacta del pedido (sin credenciales) |
| `sha256` | string | suma SHA-256 del archivo guardado |
| `bytes` | string | tamaño |
| `descargado_utc` | string | fecha de descarga |
| `dataset` | string |  |
| `doi` | string |  |
| `granulo` | string |  |
| `variables` | string |  |
| `ruta` | string |  |
| `error_ruta_principal` | string |  |
| `url_respaldo` | string |  |
| `nota` | string |  |
| `fuente` | string |  |
| `licencia` | string |  |
| `fuente_original` | string |  |
| `anio_representado` | string |  |
| `boundaryID` | string |  |
| `sha256_archivo_original` | string |  |
| `bytes_archivo_original` | string |  |
| `api` | string |  |
| `titulo` | string |  |
| `estandar_tiempo` | string |  |

## `results/nacional/parquet/metricas_celdas_gldas.parquet`

65 filas.

| columna | tipo | descripción |
|---|---|---|
| `celda` | str | id de celda = latitud_longitud del centro (3 decimales) |
| `lat` | float64 | latitud del centro (°) |
| `lon` | float64 | longitud del centro (°) |
| `area_km2` | float64 | área de la celda (km²) |
| `frac_pais` | float64 | fracción del área de la celda dentro de RD (ADM1) |
| `frac_otro_pais` | float64 | mayor fracción dentro de otro país (Natural Earth) |
| `otro_pais` | str | ISO3 de ese país |
| `frac_mar` | float64 | fracción fuera de todo país |
| `provincia_principal` | str | provincia con mayor fracción de la celda |
| `tierra_gldas` | bool | GLDAS tiene dato de suelo en la celda |
| `elevacion_m` | float64 | elevación de la celda en GLDAS (m) |
| `incluida` | bool | entra al análisis (≥25 % en RD, más RD que vecino y, en GLDAS, tierra en el modelo) |
| `motivo_exclusion` | str | por qué no entra |
| `gamma_ET` | float64 |  |
| `phi_ET` | float64 |  |
| `r_spi_ET` | float64 |  |
| `gamma_SM_0_10` | float64 |  |
| `phi_SM_0_10` | float64 |  |
| `r_spi_SM_0_10` | float64 |  |
| `gamma_SM_RAIZ` | float64 |  |
| `phi_SM_RAIZ` | float64 |  |
| `r_spi_SM_RAIZ` | float64 |  |
| `gamma_TAIRE` | float64 |  |
| `phi_TAIRE` | float64 |  |
| `r_spi_TAIRE` | float64 |  |
| `tendencia_ET_pendiente_decada` | float64 |  |
| `tendencia_SM_0_10_pendiente_decada` | float64 |  |
| `tendencia_SM_RAIZ_pendiente_decada` | float64 |  |
| `tendencia_TAIRE_pendiente_decada` | float64 |  |
| `tendencia_ET_q_bh` | float64 |  |
| `tendencia_SM_0_10_q_bh` | float64 |  |
| `tendencia_SM_RAIZ_q_bh` | float64 |  |
| `tendencia_TAIRE_q_bh` | float64 |  |
| `tendencia_ET_q_bh_empirico` | float64 |  |
| `tendencia_SM_0_10_q_bh_empirico` | float64 |  |
| `tendencia_SM_RAIZ_q_bh_empirico` | float64 |  |
| `tendencia_TAIRE_q_bh_empirico` | float64 |  |
| `n_B1_suelo_seco_sin_sequia` | int64 |  |
| `n_B2_suelo_normal_en_sequia` | int64 |  |
| `B1_periodos` | str |  |
| `B2_periodos` | str |  |
| `n_episodios` | int64 |  |
| `n_con_retorno` | int64 |  |
| `n_A_raiz` | int64 | episodios A (raíz) con lluvia IMERG |
| `n_A_superficial` | int64 |  |
| `mediana_meses_recuperacion_raiz` | float64 |  |
| `n_recuperacion_censurada_raiz` | int64 |  |
| `fraccion_A_raiz` | float64 |  |
| `n_episodios_lluvia_modelo` | int64 |  |
| `n_con_retorno_lluvia_modelo` | int64 |  |
| `n_A_raiz_lluvia_modelo` | int64 | episodios A con la lluvia de forzamiento de GLDAS |
| `n_A_superficial_lluvia_modelo` | int64 |  |
| `n_B1_suelo_seco_sin_sequia_lluvia_modelo` | int64 |  |
| `n_B2_suelo_normal_en_sequia_lluvia_modelo` | int64 |  |
| `lluvia_imerg_spi3_seco_a_humedo` | int64 |  |
| `lluvia_imerg_spi3_humedo_a_seco` | int64 |  |
| `suelo_raiz_z_seco_a_humedo` | int64 |  |
| `suelo_raiz_z_humedo_a_seco` | int64 |  |
| `suelo_sup_z_seco_a_humedo` | int64 |  |
| `suelo_sup_z_humedo_a_seco` | int64 |  |
| `lluvia_modelo_spi3_seco_a_humedo` | int64 |  |
| `lluvia_modelo_spi3_humedo_a_seco` | int64 |  |
| `p95_dias_lluvia_mm` | float64 |  |
| `fraccion_lluvia_en_dias_p95` | float64 |  |
| `max_anual_1dia_mediana_mm` | float64 |  |
| `dias_lluvia_por_anio` | float64 |  |

## `results/nacional/parquet/metricas_celdas_imerg.parquet`

442 filas.

| columna | tipo | descripción |
|---|---|---|
| `celda` | str | id de celda = latitud_longitud del centro (3 decimales) |
| `lat` | float64 | latitud del centro (°) |
| `lon` | float64 | longitud del centro (°) |
| `area_km2` | float64 | área de la celda (km²) |
| `frac_pais` | float64 | fracción del área de la celda dentro de RD (ADM1) |
| `frac_otro_pais` | float64 | mayor fracción dentro de otro país (Natural Earth) |
| `otro_pais` | str | ISO3 de ese país |
| `frac_mar` | float64 | fracción fuera de todo país |
| `provincia_principal` | str | provincia con mayor fracción de la celda |
| `incluida` | bool | entra al análisis (≥25 % en RD, más RD que vecino y, en GLDAS, tierra en el modelo) |
| `meses_con_dato` | int64 | meses IMERG con dato |
| `unidad_por_decada` | str |  |
| `n_anios` | int64 |  |
| `pendiente_decada` | float64 | pendiente Theil-Sen por década |
| `ic95_bajo` | float64 | límite inferior IC95 (bootstrap) |
| `ic95_alto` | float64 | límite superior IC95 |
| `p_mk_simple` | float64 |  |
| `p_mk_ar1` | float64 | p Mann-Kendall con corrección AR(1) |
| `autocorr_lag1` | float64 |  |
| `q_bh` | float64 | q Benjamini-Hochberg (p nominal) |
| `p_empirico` | float64 | p calibrado con sustitutos de fases aleatorias |
| `q_bh_empirico` | float64 | q BH sobre el p calibrado |
| `Z_obs` | float64 |  |
| `pendiente_pct_clim_decada` | float64 |  |
| `sig_bh_nominal` | bool |  |
| `sig_bh_calibrado` | bool |  |

## `results/nacional/parquet/panel_celdas_gldas_mensual.parquet`

224640 filas.
Variables: `ET`, `P_mm_imerg_remapeada`, `SM_0_10`, `SM_RAIZ`, `SPI1`, `SPI3`, `SPI6`, `TAIRE`, `z_ET`, `z_SM_0_10`, `z_SM_RAIZ`, `z_TAIRE`.

| columna | tipo | descripción |
|---|---|---|
| `fecha` | datetime64[us] | primer día del mes (o día) |
| `rejilla` | str | rejilla de origen |
| `celda` | str | id de celda = latitud_longitud del centro (3 decimales) |
| `variable` | str | nombre de la variable |
| `valor` | float64 | valor |

## `results/nacional/parquet/panel_celdas_imerg_mensual.parquet`

254592 filas.
Variables: `P_mm`, `SPI3`.

| columna | tipo | descripción |
|---|---|---|
| `fecha` | datetime64[us] | primer día del mes (o día) |
| `rejilla` | str | rejilla de origen |
| `celda` | str | id de celda = latitud_longitud del centro (3 decimales) |
| `variable` | str | nombre de la variable |
| `valor` | float64 | valor |

## `results/nacional/parquet/provincias_mensual.parquet`

55296 filas.
Variables: `P_mm`, `SM_0_10`, `SM_RAIZ`, `SPI3`, `z_SM_0_10`, `z_SM_RAIZ`.

| columna | tipo | descripción |
|---|---|---|
| `fecha` | datetime64[us] | primer día del mes (o día) |
| `provincia` | str | nombre ADM1 (geoBoundaries) |
| `variable` | str | nombre de la variable |
| `valor` | float64 | valor |

## `results/nacional/acople_memoria_celdas.csv`

| columna | tipo | descripción |
|---|---|---|
| `celda` | str | id de celda = latitud_longitud del centro (3 decimales) |
| `respuesta` | str | SM_RAIZ, SM_0_10, ET, TAIRE (z robusto) |
| `metrica` | str | r_spi (acople), phi (memoria ARX), gamma (sensibilidad ARX) |
| `valor` | float64 | valor |
| `ic95_bajo` | float64 | límite inferior IC95 (bootstrap) |
| `ic95_alto` | float64 | límite superior IC95 |
| `ee_boot` | float64 | error estándar bootstrap |
| `n_meses` | int64 |  |

## `results/nacional/calibracion_pares_resumen.csv`

| columna | tipo | descripción |
|---|---|---|
| `respuesta` | str | SM_RAIZ, SM_0_10, ET, TAIRE (z robusto) |
| `metrica` | str | r_spi (acople), phi (memoria ARX), gamma (sensibilidad ARX) |
| `n` | int64 |  |
| `tasa_empirica_p05` | float64 |  |
| `factor_inflacion_EE` | float64 |  |
| `tasa_p05_tras_calibrar` | float64 |  |
| `z_abs_critico_95` | float64 |  |

## `results/nacional/celdas_gldas.csv`

| columna | tipo | descripción |
|---|---|---|
| `celda` | str | id de celda = latitud_longitud del centro (3 decimales) |
| `lat` | float64 | latitud del centro (°) |
| `lon` | float64 | longitud del centro (°) |
| `area_km2` | float64 | área de la celda (km²) |
| `frac_pais` | float64 | fracción del área de la celda dentro de RD (ADM1) |
| `frac_otro_pais` | float64 | mayor fracción dentro de otro país (Natural Earth) |
| `otro_pais` | str | ISO3 de ese país |
| `frac_mar` | float64 | fracción fuera de todo país |
| `provincia_principal` | str | provincia con mayor fracción de la celda |
| `tierra_gldas` | bool | GLDAS tiene dato de suelo en la celda |
| `elevacion_m` | float64 | elevación de la celda en GLDAS (m) |
| `incluida` | bool | entra al análisis (≥25 % en RD, más RD que vecino y, en GLDAS, tierra en el modelo) |
| `motivo_exclusion` | str | por qué no entra |

## `results/nacional/celdas_imerg.csv`

| columna | tipo | descripción |
|---|---|---|
| `celda` | str | id de celda = latitud_longitud del centro (3 decimales) |
| `lat` | float64 | latitud del centro (°) |
| `lon` | float64 | longitud del centro (°) |
| `area_km2` | float64 | área de la celda (km²) |
| `frac_pais` | float64 | fracción del área de la celda dentro de RD (ADM1) |
| `frac_otro_pais` | int64 | mayor fracción dentro de otro país (Natural Earth) |
| `otro_pais` | float64 | ISO3 de ese país |
| `frac_mar` | float64 | fracción fuera de todo país |
| `provincia_principal` | str | provincia con mayor fracción de la celda |
| `incluida` | bool | entra al análisis (≥25 % en RD, más RD que vecino y, en GLDAS, tierra en el modelo) |
| `meses_con_dato` | int64 | meses IMERG con dato |

## `results/nacional/comparacion_power_merra2.csv`

| columna | tipo | descripción |
|---|---|---|
| `celda_power` | str |  |
| `celdas_imerg` | int64 |  |
| `celdas_gldas` | int64 |  |
| `r_spi3_imerg_vs_merra2` | float64 |  |
| `r_z_raiz_gldas_vs_merra2` | float64 |  |
| `lluvia_anual_imerg_mm` | float64 |  |
| `lluvia_anual_merra2_mm` | float64 |  |

## `results/nacional/contradicciones_por_celda.csv`

| columna | tipo | descripción |
|---|---|---|
| `celda` | str | id de celda = latitud_longitud del centro (3 decimales) |
| `n_B1_suelo_seco_sin_sequia` | int64 |  |
| `n_B2_suelo_normal_en_sequia` | int64 |  |
| `B1_periodos` | str |  |
| `B2_periodos` | str |  |
| `n_episodios` | int64 |  |
| `n_con_retorno` | int64 |  |
| `n_A_raiz` | int64 | episodios A (raíz) con lluvia IMERG |
| `n_A_superficial` | int64 |  |
| `mediana_meses_recuperacion_raiz` | float64 |  |
| `n_recuperacion_censurada_raiz` | int64 |  |
| `fraccion_A_raiz` | float64 |  |
| `n_episodios_lluvia_modelo` | int64 |  |
| `n_con_retorno_lluvia_modelo` | int64 |  |
| `n_A_raiz_lluvia_modelo` | int64 | episodios A con la lluvia de forzamiento de GLDAS |
| `n_A_superficial_lluvia_modelo` | int64 |  |
| `n_B1_suelo_seco_sin_sequia_lluvia_modelo` | int64 |  |
| `n_B2_suelo_normal_en_sequia_lluvia_modelo` | int64 |  |

## `results/nacional/contrastes_ranking.csv`

| columna | tipo | descripción |
|---|---|---|
| `rango` | int64 |  |
| `celda_a` | str |  |
| `celda_b` | str |  |
| `respuesta` | str | SM_RAIZ, SM_0_10, ET, TAIRE (z robusto) |
| `metrica` | str | r_spi (acople), phi (memoria ARX), gamma (sensibilidad ARX) |
| `valor_a` | float64 |  |
| `valor_b` | float64 |  |
| `delta` | float64 | métrica(A) − métrica(B) |
| `ic95_bajo` | float64 | límite inferior IC95 (bootstrap) |
| `ic95_alto` | float64 | límite superior IC95 |
| `ee_boot` | float64 | error estándar bootstrap |
| `p` | float64 |  |
| `q_bh` | float64 | q Benjamini-Hochberg (p nominal) |
| `n_pruebas_bh` | int64 |  |
| `p_calibrado` | float64 | p calibrado con el nulo paramétrico de pares |
| `p_empirico_nulo` | float64 |  |
| `q_bh_calibrado` | float64 | q BH sobre el p calibrado |
| `n_variantes` | int64 |  |
| `variantes_ok` | int64 |  |
| `variantes_mismo_signo` | int64 |  |
| `robustez` | float64 | fracción de variantes con mismo signo e IC sin 0 |
| `distancia_km` | float64 |  |
| `r_spi3` | float64 |  |
| `dif_rel_lluvia_anual` | float64 |  |
| `dif_elevacion_m` | float64 |  |
| `frac_pais_min` | float64 |  |
| `pasa_criterio_estricto` | bool |  |
| `efecto_abs` | float64 |  |
| `mascara_estricta_ok` | bool |  |
| `delta_lluvia_modelo` | float64 |  |
| `ic95_bajo_lluvia_modelo` | float64 |  |
| `ic95_alto_lluvia_modelo` | float64 |  |
| `mismo_signo_lluvia_modelo` | bool |  |
| `ic_excluye_0_lluvia_modelo` | bool |  |
| `sobrevive_lluvia_modelo` | bool |  |
| `etiqueta_producto` | str | si el contraste sigue con la lluvia de forzamiento de GLDAS |
| `significativo_q05_nominal` | bool |  |
| `significativo_q05_calibrado` | bool |  |

## `results/nacional/episodios.csv`

| columna | tipo | descripción |
|---|---|---|
| `celda` | str | id de celda = latitud_longitud del centro (3 decimales) |
| `inicio` | str |  |
| `fin` | str |  |
| `duracion_meses` | int64 |  |
| `severidad` | float64 |  |
| `spi3_min` | float64 |  |
| `retorno_lluvia` | str |  |
| `anio_cluster` | int64 |  |
| `meses_sequia_previos` | int64 |  |
| `fraccion_lluvia_intensa` | float64 |  |
| `lluvia_max_1dia_mm` | float64 |  |
| `umbral_p95_diario_mm` | float64 |  |
| `z_antecedente_SM_RAIZ` | float64 |  |
| `z_min_SM_RAIZ` | float64 |  |
| `z_retorno_SM_RAIZ` | float64 |  |
| `contradiccion_A_SM_RAIZ` | object |  |
| `meses_recuperacion_SM_RAIZ` | float64 |  |
| `recuperacion_censurada_SM_RAIZ` | bool |  |
| `z_antecedente_SM_0_10` | float64 |  |
| `z_min_SM_0_10` | float64 |  |
| `z_retorno_SM_0_10` | float64 |  |
| `contradiccion_A_SM_0_10` | object |  |
| `meses_recuperacion_SM_0_10` | float64 |  |
| `recuperacion_censurada_SM_0_10` | bool |  |
| `episodio_en_lluvia_modelo` | bool |  |
| `contradiccion_A_SM_RAIZ_lluvia_modelo` | bool |  |
| `contradiccion_A_SM_RAIZ_etiqueta` | str |  |

## `results/nacional/episodios_emparejados_18.875_-70.375__19.375_-70.625.csv`

| columna | tipo | descripción |
|---|---|---|
| `fin_a` | str |  |
| `fin_b` | str |  |
| `spi3_min_a` | float64 |  |
| `spi3_min_b` | float64 |  |
| `severidad_a` | float64 |  |
| `severidad_b` | float64 |  |
| `z_retorno_a` | float64 |  |
| `z_retorno_b` | float64 |  |
| `meses_recuperacion_a` | float64 |  |
| `meses_recuperacion_b` | float64 |  |
| `contradiccion_a` | object |  |
| `contradiccion_b` | object |  |
| `fraccion_intensa_a` | float64 |  |
| `fraccion_intensa_b` | float64 |  |
| `max1d_a` | float64 |  |
| `max1d_b` | float64 |  |
| `z_antecedente_a` | float64 |  |
| `z_antecedente_b` | float64 |  |
| `meses_previos_a` | int64 |  |
| `meses_previos_b` | int64 |  |

## `results/nacional/episodios_emparejados_19.375_-70.125__19.875_-70.875.csv`

| columna | tipo | descripción |
|---|---|---|
| `fin_a` | str |  |
| `fin_b` | str |  |
| `spi3_min_a` | float64 |  |
| `spi3_min_b` | float64 |  |
| `severidad_a` | float64 |  |
| `severidad_b` | float64 |  |
| `z_retorno_a` | float64 |  |
| `z_retorno_b` | float64 |  |
| `meses_recuperacion_a` | float64 |  |
| `meses_recuperacion_b` | float64 |  |
| `contradiccion_a` | object |  |
| `contradiccion_b` | object |  |
| `fraccion_intensa_a` | float64 |  |
| `fraccion_intensa_b` | float64 |  |
| `max1d_a` | float64 |  |
| `max1d_b` | float64 |  |
| `z_antecedente_a` | float64 |  |
| `z_antecedente_b` | float64 |  |
| `meses_previos_a` | int64 |  |
| `meses_previos_b` | int64 |  |

## `results/nacional/episodios_emparejados_19.625_-70.375__19.875_-70.875.csv`

| columna | tipo | descripción |
|---|---|---|
| `fin_a` | str |  |
| `fin_b` | str |  |
| `spi3_min_a` | float64 |  |
| `spi3_min_b` | float64 |  |
| `severidad_a` | float64 |  |
| `severidad_b` | float64 |  |
| `z_retorno_a` | float64 |  |
| `z_retorno_b` | float64 |  |
| `meses_recuperacion_a` | float64 |  |
| `meses_recuperacion_b` | float64 |  |
| `contradiccion_a` | object |  |
| `contradiccion_b` | object |  |
| `fraccion_intensa_a` | float64 |  |
| `fraccion_intensa_b` | float64 |  |
| `max1d_a` | float64 |  |
| `max1d_b` | float64 |  |
| `z_antecedente_a` | float64 |  |
| `z_antecedente_b` | float64 |  |
| `meses_previos_a` | int64 |  |
| `meses_previos_b` | int64 |  |

## `results/nacional/episodios_emparejados_19.625_-70.625__19.875_-70.875.csv`

| columna | tipo | descripción |
|---|---|---|
| `fin_a` | str |  |
| `fin_b` | str |  |
| `spi3_min_a` | float64 |  |
| `spi3_min_b` | float64 |  |
| `severidad_a` | float64 |  |
| `severidad_b` | float64 |  |
| `z_retorno_a` | float64 |  |
| `z_retorno_b` | float64 |  |
| `meses_recuperacion_a` | float64 |  |
| `meses_recuperacion_b` | float64 |  |
| `contradiccion_a` | object |  |
| `contradiccion_b` | object |  |
| `fraccion_intensa_a` | float64 |  |
| `fraccion_intensa_b` | float64 |  |
| `max1d_a` | float64 |  |
| `max1d_b` | float64 |  |
| `z_antecedente_a` | float64 |  |
| `z_antecedente_b` | float64 |  |
| `meses_previos_a` | int64 |  |
| `meses_previos_b` | int64 |  |

## `results/nacional/episodios_lluvia_modelo.csv`

| columna | tipo | descripción |
|---|---|---|
| `celda` | str | id de celda = latitud_longitud del centro (3 decimales) |
| `inicio` | str |  |
| `fin` | str |  |
| `duracion_meses` | int64 |  |
| `severidad` | float64 |  |
| `spi3_min` | float64 |  |
| `retorno_lluvia` | str |  |
| `anio_cluster` | int64 |  |
| `meses_sequia_previos` | int64 |  |
| `fraccion_lluvia_intensa` | float64 |  |
| `lluvia_max_1dia_mm` | float64 |  |
| `umbral_p95_diario_mm` | float64 |  |
| `z_antecedente_SM_RAIZ` | float64 |  |
| `z_min_SM_RAIZ` | float64 |  |
| `z_retorno_SM_RAIZ` | float64 |  |
| `contradiccion_A_SM_RAIZ` | object |  |
| `meses_recuperacion_SM_RAIZ` | float64 |  |
| `recuperacion_censurada_SM_RAIZ` | bool |  |
| `z_antecedente_SM_0_10` | float64 |  |
| `z_min_SM_0_10` | float64 |  |
| `z_retorno_SM_0_10` | float64 |  |
| `contradiccion_A_SM_0_10` | object |  |
| `meses_recuperacion_SM_0_10` | float64 |  |
| `recuperacion_censurada_SM_0_10` | bool |  |

## `results/nacional/estado_antecedente.csv`

| columna | tipo | descripción |
|---|---|---|
| `celda` | str | id de celda = latitud_longitud del centro (3 decimales) |
| `respuesta` | str | SM_RAIZ, SM_0_10, ET, TAIRE (z robusto) |
| `n_meses` | int64 |  |
| `umbral_tercil_seco` | float64 |  |
| `umbral_tercil_humedo` | float64 |  |
| `gamma_seco` | float64 |  |
| `gamma_seco_ic95` | str |  |
| `gamma_humedo` | float64 |  |
| `gamma_humedo_ic95` | str |  |
| `delta_gamma` | float64 |  |
| `delta_gamma_ic95` | str |  |
| `interaccion` | float64 |  |
| `interaccion_ic95` | str |  |
| `p_delta_gamma` | float64 |  |
| `q_bh` | float64 | q Benjamini-Hochberg (p nominal) |

## `results/nacional/evento_santo_domingo_por_celda.csv`

| columna | tipo | descripción |
|---|---|---|
| `celda` | str | id de celda = latitud_longitud del centro (3 decimales) |
| `mm_dia_utc_evento` | float64 |  |
| `mm_dia_utc_siguiente` | float64 |  |
| `mm_2_dias` | float64 |  |
| `puesto_entre_todos_los_dias` | int64 |  |
| `puesto_entre_maximos_anuales` | int64 |  |
| `periodo_retorno_empirico_anios` | float64 |  |
| `maximo_anual_mediana_mm` | float64 |  |
| `maximo_registro_mm` | float64 |  |
| `fecha_maximo_registro` | str |  |
| `n_dias` | int64 |  |

## `results/nacional/factores_asociacion.csv`

| columna | tipo | descripción |
|---|---|---|
| `resultado` | str |  |
| `factor` | str |  |
| `columna_factor` | str |  |
| `n` | int64 |  |
| `n_conglomerados` | int64 |  |
| `beta` | float64 |  |
| `ic95` | str |  |
| `p` | float64 |  |
| `q_bh` | float64 | q Benjamini-Hochberg (p nominal) |
| `n_pruebas_bh` | int64 |  |

## `results/nacional/factores_sensibilidad.csv`

| columna | tipo | descripción |
|---|---|---|
| `variante` | str |  |
| `resultado` | str |  |
| `factor` | str |  |
| `n` | int64 |  |
| `n_conglomerados` | int64 |  |
| `beta` | float64 |  |
| `ic95` | str |  |
| `p` | float64 |  |

## `results/nacional/grace_contexto_nacional.csv`

| columna | tipo | descripción |
|---|---|---|
| `fecha` | str | primer día del mes (o día) |
| `tws_cm` | float64 |  |
| `incertidumbre_cm` | float64 |  |
| `celdas_0_5_usadas` | int64 |  |

## `results/nacional/intensidad_lluvia_celdas.csv`

| columna | tipo | descripción |
|---|---|---|
| `celda` | str | id de celda = latitud_longitud del centro (3 decimales) |
| `p95_dias_lluvia_mm` | float64 |  |
| `fraccion_lluvia_en_dias_p95` | float64 |  |
| `max_anual_1dia_mediana_mm` | float64 |  |
| `dias_lluvia_por_anio` | float64 |  |

## `results/nacional/latigazos_por_celda.csv`

| columna | tipo | descripción |
|---|---|---|
| `celda` | str | id de celda = latitud_longitud del centro (3 decimales) |
| `lluvia_imerg_spi3_seco_a_humedo` | int64 |  |
| `lluvia_imerg_spi3_humedo_a_seco` | int64 |  |
| `suelo_raiz_z_seco_a_humedo` | int64 |  |
| `suelo_raiz_z_humedo_a_seco` | int64 |  |
| `suelo_sup_z_seco_a_humedo` | int64 |  |
| `suelo_sup_z_humedo_a_seco` | int64 |  |
| `lluvia_modelo_spi3_seco_a_humedo` | int64 |  |
| `lluvia_modelo_spi3_humedo_a_seco` | int64 |  |

## `results/nacional/pares_candidatos.csv`

| columna | tipo | descripción |
|---|---|---|
| `celda_a` | str |  |
| `celda_b` | str |  |
| `distancia_km` | float64 |  |
| `r_spi3` | float64 |  |
| `lluvia_anual_a_mm` | float64 |  |
| `lluvia_anual_b_mm` | float64 |  |
| `dif_rel_lluvia_anual` | float64 |  |
| `r_ciclo_estacional` | float64 |  |
| `dif_elevacion_m` | float64 |  |
| `frac_pais_min` | float64 |  |
| `lluvia_parecida` | bool |  |
| `pasa_criterio_estricto` | bool |  |

## `results/nacional/perfil_lags.csv`

| columna | tipo | descripción |
|---|---|---|
| `celda` | str | id de celda = latitud_longitud del centro (3 decimales) |
| `respuesta` | str | SM_RAIZ, SM_0_10, ET, TAIRE (z robusto) |
| `r_lag0` | float64 |  |
| `r_lag1` | float64 |  |
| `r_lag2` | float64 |  |
| `r_lag3` | float64 |  |
| `r_lag4` | float64 |  |
| `r_lag5` | float64 |  |
| `r_lag6` | float64 |  |
| `lag_max_meses` | int64 |  |
| `r_max` | float64 |  |

## `results/nacional/pesos_provincia_gldas.csv`

| columna | tipo | descripción |
|---|---|---|
| `celda` | str | id de celda = latitud_longitud del centro (3 decimales) |
| `provincia` | str | nombre ADM1 (geoBoundaries) |
| `codigo` | str | código ISO 3166-2 |
| `fraccion` | float64 | fracción de la celda en la provincia |

## `results/nacional/pesos_provincia_imerg.csv`

| columna | tipo | descripción |
|---|---|---|
| `celda` | str | id de celda = latitud_longitud del centro (3 decimales) |
| `provincia` | str | nombre ADM1 (geoBoundaries) |
| `codigo` | str | código ISO 3166-2 |
| `fraccion` | float64 | fracción de la celda en la provincia |

## `results/nacional/provincias_cobertura.csv`

| columna | tipo | descripción |
|---|---|---|
| `provincia` | str | nombre ADM1 (geoBoundaries) |
| `celdas_imerg` | int64 |  |
| `area_km2` | float64 | área de la celda (km²) |
| `celdas_gldas` | int64 |  |

## `results/nacional/provincias_contradicciones.csv`

| columna | tipo | descripción |
|---|---|---|
| `provincia` | str | nombre ADM1 (geoBoundaries) |
| `n_B1_suelo_seco_sin_sequia` | int64 |  |
| `n_B2_suelo_normal_en_sequia` | int64 |  |
| `B1_periodos` | str |  |
| `B2_periodos` | str |  |
| `n_episodios` | int64 |  |
| `n_con_retorno` | int64 |  |
| `n_A_raiz` | int64 | episodios A (raíz) con lluvia IMERG |
| `n_A_superficial` | int64 |  |
| `mediana_meses_recuperacion_raiz` | float64 |  |
| `n_recuperacion_censurada_raiz` | int64 |  |
| `fraccion_A_raiz` | float64 |  |

## `results/nacional/provincias_episodios.csv`

| columna | tipo | descripción |
|---|---|---|
| `provincia` | str | nombre ADM1 (geoBoundaries) |
| `inicio` | str |  |
| `fin` | str |  |
| `duracion_meses` | int64 |  |
| `severidad` | float64 |  |
| `spi3_min` | float64 |  |
| `retorno_lluvia` | str |  |
| `anio_cluster` | int64 |  |
| `meses_sequia_previos` | int64 |  |
| `fraccion_lluvia_intensa` | float64 |  |
| `lluvia_max_1dia_mm` | float64 |  |
| `umbral_p95_diario_mm` | float64 |  |
| `z_antecedente_SM_RAIZ` | float64 |  |
| `z_min_SM_RAIZ` | float64 |  |
| `z_retorno_SM_RAIZ` | float64 |  |
| `contradiccion_A_SM_RAIZ` | object |  |
| `meses_recuperacion_SM_RAIZ` | float64 |  |
| `recuperacion_censurada_SM_RAIZ` | bool |  |
| `z_antecedente_SM_0_10` | float64 |  |
| `z_min_SM_0_10` | float64 |  |
| `z_retorno_SM_0_10` | float64 |  |
| `contradiccion_A_SM_0_10` | object |  |
| `meses_recuperacion_SM_0_10` | float64 |  |
| `recuperacion_censurada_SM_0_10` | bool |  |

## `results/nacional/pruebas_pares.csv`

| columna | tipo | descripción |
|---|---|---|
| `celda_a` | str |  |
| `celda_b` | str |  |
| `respuesta` | str | SM_RAIZ, SM_0_10, ET, TAIRE (z robusto) |
| `metrica` | str | r_spi (acople), phi (memoria ARX), gamma (sensibilidad ARX) |
| `valor_a` | float64 |  |
| `valor_b` | float64 |  |
| `delta` | float64 | métrica(A) − métrica(B) |
| `ic95_bajo` | float64 | límite inferior IC95 (bootstrap) |
| `ic95_alto` | float64 | límite superior IC95 |
| `ee_boot` | float64 | error estándar bootstrap |
| `p` | float64 |  |
| `q_bh` | float64 | q Benjamini-Hochberg (p nominal) |
| `n_pruebas_bh` | int64 |  |
| `p_calibrado` | float64 | p calibrado con el nulo paramétrico de pares |
| `p_empirico_nulo` | float64 |  |
| `q_bh_calibrado` | float64 | q BH sobre el p calibrado |

## `results/nacional/sensibilidad_pares.csv`

| columna | tipo | descripción |
|---|---|---|
| `celda_a` | str |  |
| `celda_b` | str |  |
| `respuesta` | str | SM_RAIZ, SM_0_10, ET, TAIRE (z robusto) |
| `metrica` | str | r_spi (acople), phi (memoria ARX), gamma (sensibilidad ARX) |
| `variante` | str |  |
| `valor_a` | float64 |  |
| `valor_b` | float64 |  |
| `delta` | float64 | métrica(A) − métrica(B) |
| `ic95_bajo` | float64 | límite inferior IC95 (bootstrap) |
| `ic95_alto` | float64 | límite superior IC95 |
| `ee_boot` | float64 | error estándar bootstrap |
| `p` | float64 |  |
| `mismo_signo` | bool |  |
| `ic_excluye_0` | bool |  |

## `results/nacional/tendencias_celdas.csv`

| columna | tipo | descripción |
|---|---|---|
| `celda` | str | id de celda = latitud_longitud del centro (3 decimales) |
| `variable` | str | nombre de la variable |
| `unidad_por_decada` | str |  |
| `n_anios` | int64 |  |
| `pendiente_decada` | float64 | pendiente Theil-Sen por década |
| `ic95_bajo` | float64 | límite inferior IC95 (bootstrap) |
| `ic95_alto` | float64 | límite superior IC95 |
| `p_mk_simple` | float64 |  |
| `p_mk_ar1` | float64 | p Mann-Kendall con corrección AR(1) |
| `autocorr_lag1` | float64 |  |
| `q_bh` | int64 | q Benjamini-Hochberg (p nominal) |
| `p_empirico` | float64 | p calibrado con sustitutos de fases aleatorias |
| `q_bh_empirico` | int64 | q BH sobre el p calibrado |
| `Z_obs` | float64 |  |
| `pendiente_pct_clim_decada` | float64 |  |
| `sig_bh_nominal` | bool |  |
| `sig_bh_calibrado` | bool |  |
