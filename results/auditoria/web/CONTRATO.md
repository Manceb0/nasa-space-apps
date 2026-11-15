# Contrato de datos · results/auditoria/web/

Generado por `earthmemory/auditoria/run.py` (`docker compose run --rm auditoria`). JSON UTF-8; `null` = sin dato.
Números en tasa (0-1), no en %. Nada se escribe a mano.

## cambio_decision_provincias.json
- `version` (int), `periodo` ("2001-2024"), `productos_sequia` (lista: IMERG, CHIRPS, GLDAS_forzamiento, MERRA2).
- `nacional_sequia`: lista de objetos {`umbral_spi3` (−1.0 / −1.5), `productos` ("4 productos" | "IMERG vs CHIRPS" |
  "3 sin MERRA-2"), `n_casos`, `n_alguna_alarma`, `n_no_unanime`, `tasa_global`, `tasa_condicional`,
  `ic95_global` [bajo, alto], `ic95_condicional` [bajo, alto]}.
- `provincias`: lista de {`provincia`, `codigo` (ISO 3166-2, p. ej. "DO-01"),
  `spi3_menor_igual_1_0` y `spi3_menor_igual_1_5`: {`tasa_condicional`, `ic95` [bajo, alto], `tasa_contradiccion_clara`
  (un producto declara sequía y otro da SPI-3 ≥ 0, es decir normal o húmedo), `tasa_global`, `n_casos`,
  `n_alguna_alarma`, `n_no_unanime`}, `inundacion_48h_100mm` (si hay CHIRPS diario): {"<escala>_tol<d>":
  {`tasa_cambio_decision`, `disparos_imerg`, `disparos_chirps`}} con escala = media_provincia | maximo_celda y d = 0 | 1}.
- Lectura: `tasa_condicional` = de los meses en que AL MENOS un producto declara sequía (SPI-3 ≤ umbral), fracción en
  que los productos no están de acuerdo. IC 95 % por bootstrap de bloques de año.
- Mostrar SIEMPRE con su IC y con la frase: "los productos no son independientes; el acuerdo no es validación".

## procedencia.json
- `productos`: lista de {`id`, `producto`, `clase` (una de 6), `mide_o_modela`, `insumos`, `pluviometros`, `resolucion`,
  `latencia`, `version`, `citas`, `urls` (lista), `verificado`}.
- `aristas`: {`a`, `b`, `insumo`, `estado` ("V" verificado | "I" inferido)}: pares que pueden compartir errores.
- `veredicto`: lista de frases para pantalla.

## donde_medir_prototipo.json
- `etiqueta`: texto obligatorio "PRELIMINAR…". `celdas`: 40 celdas 0.1° con mayor `indice_prioridad` (0-1, media de
  rangos percentiles de: desacuerdo 1−r IMERG/CHIRPS, persistencia (fracción de años con cambio de decisión), tasa de
  cambio condicional SPI-3 ≤ −1 y distancia a la estación GHCN-D activa más cercana). Campos: `lat`, `lon`, `provincia`,
  `indice_prioridad`, `indice_sin_distancia`, y los cuatro componentes.
- No usar como recomendación de dónde instalar estaciones sin acceso, exposición, población y la red ONAMET/INDRHI.
