# Trazabilidad: de la pregunta al veredicto

Generado por `earthmemory/trazabilidad.py` a partir de `results/` (no recalcula nada). Versión para máquinas: `results/tropical/trazabilidad/registro.json`. Cada prueba escribió sus predicciones en disco ANTES de bajar o calcular; la hora de registro va al lado de la hora en que se escribió el resultado. Las huellas SHA-256 permiten comprobar que nadie tocó los archivos después.

**12 pruebas, 43 predicciones registradas: 20 se cumplen, 16 no se cumplen y 7 se remiten a la tabla de conclusiones.** Las que fallaron se publican igual.

| Prueba | Pregunta | Datos | Predicciones registradas (UTC) | Resultado escrito (UTC) | Antes | Se cumplen | Filas |
|---|---|---|---|---|---|---|---|
| `primera_tanda` | ¿Las contradicciones entre productos de lluvia siguen la física de una isla tropical? | IMERG V07 (NASA GPM), CHIRPS, IBTrACS, pluviómetros GHCN-D | 2026-11-15 | 2026-11-15T07:05:19 | solo fecha | 0 de 0 | 9, 12, 13 |
| `era5` | ¿Un tercer testigo (ERA5) ve el mismo escalón de IMERG? | IMERG V07 (NASA GPM), CHIRPS, ERA5 | 2026-11-15T13:17:40 | 2026-11-15T13:54:26 | sí | 3 de 4 | 4, 9 |
| `forma` | ¿El cambio IMERG − CHIRPS es tendencia, escalón, ambos o nada? | IMERG V07 (NASA GPM), CHIRPS | 2026-11-15T14:08:19 | 2026-11-15T14:09:24 | sí | 1 de 3 | 6, 7 |
| `gpm_fuentes` | ¿El cambio de IMERG viene de su parte infrarroja (GOES-16)? | IMERG V07 contadores de microondas (NASA GPM), CHIRPS, ERA5 | 2026-11-15T14:41:09 | 2026-11-15T14:48:47 | sí | 2 de 3 | 8 |
| `alerta_acuerdo` | ¿Una alerta que pide testigo funciona mejor que una que cree a un solo producto? (versión retrospectiva) | IMERG V07 (NASA GPM), CHIRPS, catálogo de inundaciones del Yuna | 2026-11-15T15:23:48 | 2026-11-15T15:23:58 | sí | 1 de 2 | 22, 23 |
| `alerta_causal` | La misma alerta, solo con información disponible al emitir | IMERG V07 (NASA GPM), CHIRPS, catálogo de inundaciones del Yuna | 2026-11-15T15:29:54 | 2026-11-15T15:29:58 | sí | 2 de 3 | 22, 24 |
| `merra2` | ¿IMERG pierde días frente a un testigo en todo el país? | IMERG V07 (NASA GPM), CHIRPS, MERRA-2 por NASA POWER | 2026-11-15T17:22:43 | 2026-11-15T17:22:49 | sí | 2 de 4 | 7b |
| `puerto_rico` | ¿IMERG pierde días también en Puerto Rico, frente a pluviómetros densos? | IMERG V07 (NASA GPM), pluviómetros GHCN-D (NOAA) | 2026-11-15T19:13:45 | 2026-11-15T19:51:40 | sí | 3 de 3 | 4d |
| `hawaii` | ¿Pierde días también en Hawái, bajo GOES-West? (separa GOES-16 de las microondas de NOAA-20) | IMERG V07 (NASA GPM), pluviómetros GHCN-D (NOAA) | 2026-11-15T23:36:33 | 2026-11-16T00:12:36 | sí | 2 de 5 | 8b |
| `era_gpm` | ¿El salto de IMERG es de 2018 o del paso de la era TRMM a la era GPM (2014)? | IMERG V07 (NASA GPM), pluviómetros GHCN-D (NOAA), CHIRPS | 2026-11-16T00:03:53 | 2026-11-16T00:03:53 | sí | 1 de 3 | 8b, 9 |
| `ciclones` | ¿Cuántas inundaciones del Yuna vinieron de un ciclón y con cuánta antelación las anunció el NHC? | IBTrACS, pronósticos oficiales NHC (ATCF), catálogo de inundaciones del Yuna | 2026-11-15T17:57:35 | 2026-11-15T18:00:44 | sí | 1 de 3 | 25 |
| `ciclones_sequia` | ¿Después de los ciclones queda sequía, o llega cuando no hay ciclones? | CHIRPS, IBTrACS | 2026-11-15T18:05:44 | 2026-11-15T18:05:53 | sí | 2 de 3 | 26 |

## Cada predicción

### `primera_tanda`: ¿Las contradicciones entre productos de lluvia siguen la física de una isla tropical?

Script `earthmemory/tropical/run.py` (sha256 `81f982947ac7`). Predicciones `results/tropical/predicciones_registradas.json` (sha256 `2c732113c48e`); resultado `results/tropical/resumen.json` (sha256 `d0a0bf332515`).

Guardado en git: predicciones en `1b13fbc` (2026-11-15T03:09:17-04:00); resultado en `1b13fbc`.

- **P1_ciclones** · ver fila 12 (se sostiene con límites). En días con un ciclón tropical a < 500 km, IMERG y CHIRPS coinciden MÁS en lluvia fuerte (CSI ≥ 50 mm mayor) y el disparador > 100 mm/48 h queda MENOS veces sin confirmar que en días sin ciclón de la misma temporada (ago-nov).
- **P1b_extremos** · ver fila 12 (se sostiene con límites). La fracción de máximos anuales de lluvia diaria (Rx1day) que cae en días de ciclón es mucho mayor que la fracción de días con ciclón.
- **P2_barlovento** · ver fila 13 (asociación, se sostiene con límites). En las laderas que miran al alisio (ascenso forzado > 0), CHIRPS da más lluvia media que IMERG (IMERG subestima la lluvia orográfica cálida) y el acuerdo diario es menor.
- **P2b_lluvia_debil** · ver fila 3. Las celdas con SDII en disputa son las que más difieren en frecuencia de días húmedos (≥ 1 mm) entre productos.
- **P3_sin_explicar** · no se cumple (p de permutación 0,62). Los 28 episodios sin explicar se concentran en retornos de la estación seca (dic-abr) con lluvia de retorno modesta, más que el resto de los 96.
- **P4_instrumento** · punto de cambio hallado en 2013-10, conclusión retirada después (fila 9). La diferencia mensual IMERG − CHIRPS en frecuencia de días húmedos tiene un punto de cambio cerca de 2014-2015 (paso de TRMM a GPM).

### `era5`: ¿Un tercer testigo (ERA5) ve el mismo escalón de IMERG?

Script `earthmemory/tropical/era5_testigo.py` (sha256 `f81e1721b647`). Predicciones `results/tropical/era5/predicciones_registradas.json` (sha256 `9a544950741c`); resultado `results/tropical/era5/resumen.json` (sha256 `a87dda1e0171`).

Guardado en git: predicciones en `acc26d6` (2026-11-15T09:27:22-04:00); resultado en `acc26d6`.

- **E1** · no se cumple. La serie mensual desestacionalizada de frecuencia de días húmedos IMERG − ERA5 tiene un punto de cambio entre 2012-10 y 2014-12 con p < 0,05 (permutación de bloques de 12 meses).
- **E2** · se cumple. En ERA5 la frecuencia de días húmedos después − antes de 2013-10 cambia menos de 2 pp (media de puntos), mientras IMERG baja al menos 4 pp en los mismos puntos.
- **E3** · se cumple. CHIRPS − ERA5 no tiene un punto de cambio significativo (p ≥ 0,05) entre 2012-10 y 2014-12.
- **E4** · se cumple. En la CANTIDAD de lluvia (log IMERG/ERA5) no hay un salto significativo en esa ventana.

### `forma`: ¿El cambio IMERG − CHIRPS es tendencia, escalón, ambos o nada?

Script `earthmemory/tropical/forma_cambio.py` (sha256 `68ab5be66ca0`). Predicciones `results/tropical/forma/predicciones_registradas.json` (sha256 `250d80545963`); resultado `results/tropical/forma/resumen.json` (sha256 `03664a58f73e`).

Guardado en git: predicciones en `d7dfdfc` (2026-11-15T10:11:56-04:00); resultado en `d7dfdfc`.

- **F1** · no se cumple. Validación: con ruido como el de una celda y un cambio total de 4,5 pp, el procedimiento acierta la forma (tendencia / escalón / ambos) en al menos el 60 % de las series sintéticas con cambio. Si no, la forma por celda se declara no identificable con estos datos.
- **F2** · no se cumple. Serie nacional: el escalón NO gana con claridad (ΔBIC ≥ 2) a la tendencia; el resultado será tendencia, tendencia + escalón o indistinguibles.
- **F3** · se cumple. Entre las celdas donde gana un modelo con escalón, ninguna ventana de 12 meses reúne más del 40 % de las fechas de escalón (no hay una fecha común).

### `gpm_fuentes`: ¿El cambio de IMERG viene de su parte infrarroja (GOES-16)?

Script `earthmemory/tropical/gpm_fuentes.py` (sha256 `629613034621`). Predicciones `results/tropical/gpm_fuentes/predicciones_registradas.json` (sha256 `af8fedfda8b7`); resultado `results/tropical/gpm_fuentes/resumen.json` (sha256 `1a10c7284ca5`).

Guardado en git: predicciones en `8980a09` (2026-11-15T10:50:01-04:00); resultado en `8980a09`.

- **H1** · se cumple. Control: en esta ventana, la diferencia de días ≥ 1 mm IMERG − CHIRPS baja después frente a antes.
- **H2** · no se cumple. Si la vía infrarroja contribuye: el cambio (después − antes, sin ciclo estacional) de la fracción de medias horas con lluvia SIN microondas (f_ir) es más negativo que el de las medias horas CON microondas (f_mw), y el IC 95 % de (Δf_ir − Δf_mw) queda por debajo de 0.
- **H3** · se cumple. Confusor: la cobertura de microondas (cob) cambia menos de un 10 % relativo; si cambia más, la prueba es ambigua.

### `alerta_acuerdo`: ¿Una alerta que pide testigo funciona mejor que una que cree a un solo producto? (versión retrospectiva)

Script `earthmemory/tropical/alerta_acuerdo.py` (sha256 `e15131126a45`). Predicciones `results/tropical/alerta_acuerdo/predicciones_registradas.json` (sha256 `d2e2c1764310`); resultado `results/tropical/alerta_acuerdo/resumen.json` (sha256 `3b81e883abba`).

Guardado en git: predicciones en `336318f` (2026-11-15T11:25:21-04:00); resultado en `336318f`.

- **K1** · no se cumple. En la prueba 2016-2024, exigir acuerdo (A∧C) conserva al menos 6 de los 8 eventos y reduce las falsas alarmas de A al menos a la mitad (de 39 a ≤ 20).
- **K2** · se cumple. A∨C no mejora el CSI de A en la prueba (añade más falsas alarmas que aciertos).

### `alerta_causal`: La misma alerta, solo con información disponible al emitir

Script `earthmemory/tropical/alerta_causal.py` (sha256 `b0717f82001a`). Predicciones `results/tropical/alerta_causal/predicciones_registradas.json` (sha256 `f946746abd1c`); resultado `results/tropical/alerta_causal/resumen.json` (sha256 `57f177303728`).

Guardado en git: predicciones en `b430634` (2026-11-15T11:31:51-04:00); resultado en `b430634`.

- **M1** · se cumple. Prueba 2016-2024, versión causal: exigir confirmación de CHIRPS del mismo día o del anterior conserva al menos 6 de 8 eventos y deja las falsas alarmas en ≤ 60 % de las de IMERG solo.
- **M2** · no se cumple. La confirmación retrasa el primer disparo al menos 1 día en la mitad o más de los eventos que detectan ambas reglas.
- **M3** · se cumple. Con IMERG solo, menos de la mitad de los eventos de prueba tienen un disparo anticipado (antes del inicio o el mismo día de inicio).

### `merra2`: ¿IMERG pierde días frente a un testigo en todo el país?

Script `earthmemory/tropical/merra2_testigo.py` (sha256 `729571a3fdab`). Predicciones `results/tropical/merra2/predicciones_registradas.json` (sha256 `ebe6cfe46ef5`); resultado `results/tropical/merra2/resumen.json` (sha256 `4563cfd03ee5`).

Guardado en git: predicciones en `3dc5b09` (2026-11-15T13:23:31-04:00); resultado en `3dc5b09`.

- **N1** · se cumple. En al menos 10 de las 15 celdas MERRA-2, la frecuencia de dias >= 1 mm de IMERG cae mas que la de MERRA-2 (despues - antes de 2018-02).
- **N2** · no se cumple. Mediana de las 15 celdas: IMERG cae al menos 4 pp y MERRA-2 cambia menos de 2 pp en valor absoluto.
- **N3** · no se cumple. La diferencia mensual desestacionalizada IMERG - MERRA-2 (media nacional) tiene un punto de cambio entre 2016-01 y 2019-12 con p < 0,05 (permutacion de bloques de 12 meses).
- **N4** · se cumple. Control del testigo: MERRA-2 solo NO tiene un punto de cambio significativo entre 2016-01 y 2019-12. Si lo tiene, el testigo esta comprometido y N1-N3 no pueden atribuirse a IMERG.

### `puerto_rico`: ¿IMERG pierde días también en Puerto Rico, frente a pluviómetros densos?

Script `earthmemory/tropical/puerto_rico.py` (sha256 `30a46923a983`). Predicciones `results/tropical/puerto_rico/predicciones_registradas.json` (sha256 `fe411164405d`); resultado `results/tropical/puerto_rico/resumen.json` (sha256 `97b9eb543252`).

Guardado en git: predicciones en `4b89e78` (2026-11-15T15:52:09-04:00); resultado en `4b89e78`.

- **PR1** · se cumple. En al menos 2 de cada 3 pluviómetros de PR con registro completo, la frecuencia de días >= 1 mm de IMERG (celda que contiene la estación) cae más que la del pluviómetro (después - antes de 2018-02).
- **PR2** · se cumple. Mediana de (cambio IMERG - cambio pluviómetro) <= -3 pp.
- **PR3** · se cumple. Los pluviómetros cambian poco: mediana de su cambio entre -2 y +2 pp.

### `hawaii`: ¿Pierde días también en Hawái, bajo GOES-West? (separa GOES-16 de las microondas de NOAA-20)

Script `earthmemory/tropical/hawaii.py` (sha256 `792aff7ff165`). Predicciones `results/tropical/hawaii/predicciones_registradas.json` (sha256 `82068193ec33`); resultado `results/tropical/hawaii/resumen.json` (sha256 `0ded6536300b`).

Guardado en git: predicciones en `fcbf1da` (2026-11-15T20:12:57-04:00); resultado en `fcbf1da`.

- **HI_global** · se cumple. Si la causa es global (ATMS de NOAA-20 u otro cambio de la constelación de microondas), en Hawái IMERG también pierde días frente a los pluviómetros con el corte 2018-02: mediana de (cambio IMERG - cambio pluviómetro) a 1 mm <= -3 pp, y IMERG cae más en al menos 2 de cada 3 estaciones.
- **HI_goes_east** · no se cumple. Si la causa es el GOES-16 (solo GOES-East), en Hawái esa mediana queda entre -1,5 y +1,5 pp.
- **HI_zona_gris** · no se cumple. Entre -3 y -1,5 pp, o fuera de +1,5: no concluyente; se dice así.
- **HI_momento** · 2014-04: fuera de ambas ventanas. Punto de cambio (Pettitt) de la serie mensual de la mediana (IMERG - pluviómetro) a 1 mm en Hawái: con causa global, entre 2017-06 y 2018-12; si cae entre 2019-01 y 2019-12, apunta al GOES-17.
- **PR_momento** · no se cumple. Control: en Puerto Rico ese punto de cambio cae entre 2017-06 y 2018-12 (ambas causas lo predicen).
- **pluviometros_hawaii** · se cumple. Los pluviómetros de Hawái cambian poco: mediana de su cambio a 1 mm entre -2 y +2 pp. Si no, el corte no aísla al instrumento y se dice.

### `era_gpm`: ¿El salto de IMERG es de 2018 o del paso de la era TRMM a la era GPM (2014)?

Script `earthmemory/tropical/era_gpm.py` (sha256 `baeee3911811`). Predicciones `results/tropical/era_gpm/predicciones_registradas.json` (sha256 `0ad8af307efd`); resultado `results/tropical/era_gpm/resumen.json` (sha256 `eab7df7e92b3`).

Guardado en git: predicciones en `fcbf1da` (2026-11-15T20:12:57-04:00); resultado en `fcbf1da`.

- **G1** · se cumple. En Hawái y en Puerto Rico, la media de (IMERG - pluviómetro) en 2015-01..2017-11 queda al menos 3 pp por debajo de la de 2001-01..2013-12.
- **G2** · no se cumple. En Hawái y en Puerto Rico, la media de 2018-02..2024-12 difiere de la de 2015-01..2017-11 en 1,5 pp o menos (no hay un segundo escalón grande en 2018).
- **G3** · no se cumple. En la RD (IMERG - CHIRPS), la caída de 2001-2013 a 2015-2017 es al menos la mitad de la caída total de 2001-2013 a 2018-2024.

### `ciclones`: ¿Cuántas inundaciones del Yuna vinieron de un ciclón y con cuánta antelación las anunció el NHC?

Script `earthmemory/tropical/ciclones_anticipacion.py` (sha256 `a360b109a15e`). Predicciones `results/tropical/ciclones/predicciones_registradas.json` (sha256 `6abe58f18426`); resultado `results/tropical/ciclones/resumen.json` (sha256 `a8d1b2738a11`).

Guardado en git: predicciones en `3ac628d` (2026-11-15T14:01:09-04:00); resultado en `3ac628d`.

- **C1** · no se cumple. Al menos la mitad de las 14 inundaciones del catálogo 2001-2024 coinciden con un ciclón tropical a menos de 500 km de la cuenca (IBTrACS) entre 3 días antes y 1 día después del inicio.
- **C2** · no se cumple. En al menos 2 de cada 3 inundaciones con ciclón, el primer aviso oficial del NHC que pone el centro a menos de 200 km de la cuenca se emitió 48 h o más antes del inicio.
- **C3** · se cumple. Más de la mitad de las tormentas cuyo pronóstico oficial pasó a menos de 200 km no tienen inundación del Yuna en el catálogo (la pre-alerta de ciclón tiene muchas falsas alarmas).

### `ciclones_sequia`: ¿Después de los ciclones queda sequía, o llega cuando no hay ciclones?

Script `earthmemory/tropical/ciclones_sequia.py` (sha256 `bb7455018c0e`). Predicciones `results/tropical/ciclones_sequia/predicciones_registradas.json` (sha256 `1da3589a7029`); resultado `results/tropical/ciclones_sequia/resumen.json` (sha256 `1682f55c5ecc`).

Guardado en git: predicciones en `3c683d8` (2026-11-15T14:06:12-04:00); resultado en `3c683d8`.

- **S1** · se cumple. Los días con ciclón a < 500 km aportan al menos el 10 % de la lluvia de junio-noviembre (media 2001-2024).
- **S2** · no se cumple. Las 8 temporadas con MENOS lluvia de ciclón tienen más meses de sequía en diciembre-mayo siguiente que las 8 con MÁS lluvia de ciclón.
- **S3** · se cumple. Versión literal de la idea («después del ciclón queda sequía»): en los 90 días tras el paso de un ciclón la sequía es MENOS frecuente que en el resto de días de la misma época. Si fuera más frecuente, la idea literal se sostiene.
