# Galería · Evidence Intelligence (Stellar Horizons, NASA Space Apps 2026)

Figuras no estándar para diapositivas (16:9, 2667 × 1500 px), web y redes (cuadradas de 1080 × 1080 px cuando tienen
sentido). Cada marca codifica un dato real de los resultados verificados: no hay nada inventado ni decorativo.

- **Reproducir:** `docker compose run --rm galeria` (todas las piezas, tema oscuro y claro). Una sola pieza:
  `docker compose run --rm galeria --solo 3`.
- **Pruebas:** `docker compose run --rm --entrypoint "uv run --frozen --no-sync pytest -q tests/test_galeria.py" galeria`.
  Las 8 pruebas comprueban que los números codificados son iguales a los de `results/` (auditoría, tendencias y Yuna),
  y que cada PNG lleva sus metadatos.
- **Código:** `earthmemory/galeria/` (`run.py`, `estilo.py`, `datos.py` y un módulo por pieza). Reutiliza los
  cargadores de los motores (`auditoria.datos`, `auditoria.analisis`, `auditoria.decision`, `yuna.mcdwd`, `yuna.common`).
- **Archivos:** `dark/` (diapositivas), `light/` (impresión). Junto a cada pieza hay un `<pieza>.json` de procedencia
  (entradas con ruta, bytes y SHA-256, cálculo, números codificados, avisos, fecha) y un `<pieza>.alt.txt` con el
  texto alternativo en inglés y en español. Las tablas intermedias están en `_datos/`.
- **Metadatos de cada PNG:** `Description`, `Source`, `Author` y
  `Software: matplotlib; figure code written with AI assistance (Claude), data unaltered`. Esta última es la
  declaración de uso de IA que piden las reglas de Space Apps 2026. Los PDF llevan lo mismo en `Creator` y `Subject`.
  No hay marcas de agua de IA: son gráficos de datos, no imágenes generadas.
- **Estilo:** fondo #0e1013 (oscuro) o blanco (claro). Paletas aptas para daltónicos: Okabe-Ito para categorías,
  cividis o viridis para escalas secuenciales y Stevens o una mezcla aditiva para el mapa bivariado. Tipografía
  DejaVu Sans. No hay barras, pasteles, 3D ni degradados decorativos.
- Las leyendas en español para usar fuera de las diapositivas están en `LEYENDAS_ES.md`.

---

## 1 · The barcode of doubt / El código de barras de la duda

`dark/01_barcode_of_doubt.png` (+ `_square`), `light/…`, `.pdf`

- **Qué muestra.** Una matriz de 32 provincias (filas) × 288 meses de 2001 a 2024 (columnas). Cada celda es el
  estado de acuerdo de cuatro productos de lluvia (IMERG V07 Final, CHIRPS v2.0, lluvia de forzamiento de GLDAS-2.1 y
  MERRA-2 vía POWER) sobre la sequía, definida como SPI-3 ≤ −1.
- **Cómo se lee.**
  - **Verde:** los cuatro dicen sequía.
  - **Celeste:** 3 de 4.
  - **Azul:** 1 o 2 de 4, y el resto entre −1 y 0.
  - **Bermellón (contradicción clara):** al menos uno dice sequía y otro da SPI-3 ≥ 0.
  - **Gris oscuro:** ninguno da alarma.

  Las filas van ordenadas por la tasa condicional de cambio de decisión de la auditoría, que aparece a la derecha.
- **Números.** De 3111 provincia-mes con alarma, 275 son unánimes, 460 son 3 de 4, 1175 son 1-2 de 4 y 1201 son
  contradicciones claras. Hay además 6041 sin alarma, en total 9152 casos. El 2015 reúne 93 de los 275 casos
  unánimes. Las provincias más sensibles son Hato Mayor (97 %), La Romana, San Pedro de Macorís y La Altagracia
  (96 %).
- **Comprobación.** Los SPI-3 se recalculan con las funciones del motor de auditoría y un `assert` los compara con
  `cambio_decision_sequia_nacional.json`, `_por_anio.csv` y `_provincias.csv`.
- **Avisos.** Los productos comparten insumos, así que esta tasa es un mínimo. Los estados azules son en parte un
  efecto de umbral. Enero y febrero de 2001 quedan en blanco porque el SPI-3 necesita tres meses.

## 1b · Where the water was / Dónde estuvo el agua (atlas del Yuna)

`dark/01b_yuna_flood_atlas.png` y `dark/01c_yuna_flood_recurrence.png`, `light/…`, `.pdf`. Procedencia en
`01b_yuna_flood_atlas.json`. Sustituye a la figura de barras de MODIS del motor Yuna.

- **Qué muestra (a).** Quince pequeños mapas, uno por evento del catálogo, ordenados en el tiempo de 2003 a 2025.
  Todos tienen el mismo encuadre y la misma escala. Cada mapa pone la cuenca del Yuna sobre el sombreado de relieve
  (Copernicus DEM) con los ríos de HydroRIVERS, la presa de Hatillo (▼), Cotuí, Villa Riva y Arenoso, y los píxeles
  de 250 m de MODIS MCDWD `Flood_2Day_250m` del día de máxima extensión.
- **Cómo se lee (a).**
  - **Azul fuerte:** inundación inusual (clase 3).
  - **Azul tenue:** inundación recurrente (clase 2).
  - **Azul muy tenue:** agua de referencia (clase 1).
  - **Trama:** zona que no se vio ese día (255: nube o sin pasada).
  - **Velo liso:** zona que el producto nunca mapea (255 en todos los días descargados, por la máscara fija de
    relieve).

  Cada panel indica los km² de clase 3 y el % de la cuenca mapeable que no se vio.
- **Números (a).**

  | Evento | Día de máxima extensión | Clase 3 | Sin ver |
  |---|---|---|---|
  | 2003-11 | 21-11-2003 | 19 km² | 23 % |
  | 2007-10 (Noel) | 04-11-2007 | 71 km² | 32 % |
  | 2007-12 (Olga) | 10-12-2007 | 59 km² | 59 % |
  | 2011-06 | 29-05-2011 | — | 99.5 % (sin vista útil) |
  | 2012-08 | 29-08-2012 | 6 km² | 48 % |
  | 2012-10 | 28-10-2012 | 9 km² | 0 % |
  | 2016-11 | 26-11-2016 | 32 km² | 42 % |
  | 2017-04 | 05-05-2017 | 13 km² | 8 % |
  | 2017-09 | 24-09-2017 | 11 km² | 30 % |
  | 2020-07 | 02-08-2020 | < 1 km² | 75 % |
  | 2022-09 | 23-09-2022 | 5 km² | 21 % |
  | 2023-11 | 22-11-2023 | 63 km² | 11 % |
  | 2024-11 | 21-11-2024 | 4 km² | 11 % |
  | 2024-12 | 20-12-2024 | 7 km² | 45 % |
  | 2025-10 | 20-10-2025 | 2 km² | 8 % |

  El 62 % de la cuenca está siempre enmascarado. Los km² se recalculan y se comprueban contra
  `mcdwd_por_evento.csv` (±2 %).
- **Qué muestra (b).** En cuántos de los 15 eventos fue «inundación inusual» cada píxel, en cualquier día de la
  ventana del evento. El mapa amplía el bajo Yuna.
- **Números (b).** 228 km² de la cuenca aparecen en al menos un evento y 50 km² en 3 o más. El máximo es 10 de 15
  eventos, en la llanura de Villa Riva y Arenoso. Solo 14 de los 15 eventos vieron al menos la mitad de la cuenca
  mapeable.
- **Avisos.** MODIS es un sensor óptico: no ve bajo nubes ni bajo el dosel, y una crecida más corta que el compuesto
  de 2 días puede perderse. Por eso los recuentos son mínimos. El evento 2025-10 queda fuera del periodo 2001-2024
  del resto del análisis.

## 2 · Spiral of disagreement / Espiral del desacuerdo

`dark/02_spiral_of_disagreement.png` (+ `_square`), `light/…`, `.pdf`

- **Qué muestra.** Los 288 meses dibujados como una espiral de Arquímedes, con 2001 en el centro y 2024 en el
  borde, una vuelta por año y enero arriba.
- **Cómo se lee.** El color (cividis) indica en cuántas de las 32 provincias los cuatro productos no fueron unánimes
  sobre la sequía. Es la misma definición que en la pieza 1, pero sumada por mes.
- **Números.** 180 de 286 meses tienen al menos una provincia en desacuerdo. En 85 meses el desacuerdo alcanza la
  mitad del país o más. En 19 meses las 32 provincias quedan divididas; el primero es septiembre de 2001. La suma de
  la serie es 2836, igual que la auditoría (comprobado con `assert`).
- **Avisos.** La escala es de recuentos enteros. La pieza hereda los límites de la pieza 1.

## 3 · Two satellites, two climates / Dos satélites, dos climas (relieve en crestas)

`dark/03_ridgeline_relief.png` (+ `_square`), `light/…`, `.pdf`

- **Qué muestra.** Unos 80 perfiles de elevación este-oeste de La Española, tomados del Copernicus GLO-90
  remuestreado a 1/300°, cada 0.03° de latitud. La exageración vertical es ×11 y se indica con una barra de
  1000 m.
- **Cómo se lee.** El color de cada tramo es la clase de confianza de la tendencia 2001-2024 de la intensidad diaria
  simple (SDII, anual) en su celda de 0.1°, según `results/tendencias/tendencias_celdas.csv`:
  - **Bermellón (en disputa):** signos opuestos y al menos una tendencia significativa tras FDR.
  - **Blanco o gris:** sin tendencia detectable.
  - **Celeste:** consistente.
  - **Tenue:** fuera del dominio de 442 celdas.

  La línea discontinua marca la cuenca del Yuna, elevada sobre el relieve; el triángulo marca Hatillo.
- **Números.** 160 de 442 celdas están en disputa, y en las 160 IMERG sube mientras CHIRPS baja. La mediana es
  +1.46 mm/día por década en IMERG y −1.54 en CHIRPS. IMERG es significativo en 122 de ellas y CHIRPS en 67. Hay
  además 277 celdas sin señal y 5 consistentes.
- **Avisos.** Es una señal de los productos (cómo detectan la llovizna y cómo reparten la lluvia entre días), no del
  clima, hasta que un tercer testigo la confirme. El pico rotulado, 3050 m, es la mayor muestra de la rejilla
  diezmada; el Pico Duarte mide unos 3098 m.

## 4 · Agreement is not validation / Coincidir no es validar (genealogía de los datos)

`dark/04_genealogy_of_the_data.png`, `light/…`, `.pdf`

- **Qué muestra.** Un diagrama aluvial con curvas de Bézier que une 12 insumos (pluviómetros, sensores satelitales y
  modelos) con 12 productos. La única fuente es `procedencia_insumos_compartidos.csv`.
- **Cómo se lee.**
  - **Línea sólida:** relación verificada en la documentación oficial.
  - **Línea discontinua:** relación inferida.
  - **Bermellón:** insumos que alimentan a dos o más de los cuatro productos de lluvia usados en la decisión de
    sequía.
  - **Verde:** GRACE, el único testigo independiente de los pluviómetros, aunque con una resolución de unos 3°.
- **Números.** 39 aristas: 34 verificadas y 5 inferidas. 7 de 12 insumos son compartidos: pluviómetros GTS/SYNOP,
  GPCC, GHCN/GSOD, IR geoestacionario, microondas pasivas, GEOS/MERRA-2 y NCEP. Los pluviómetros del GTS alimentan a
  6 productos, entre ellos los cuatro de la auditoría.
- **Avisos.** Las URL que respaldan cada relación están en `procedencia_matriz.csv`.

## 5 · Where doubt is high and gauges are far / Donde la duda es alta y los pluviómetros están lejos (PROTOTIPO)

`dark/05_bivariate_where_to_measure.png`, `light/…`, `.pdf`

- **Qué muestra.** Un coroplético bivariado de 3 × 3 sobre 443 celdas de 0.1°. Cruza la tasa condicional de cambio
  de decisión (SPI-3 ≤ −1, cuatro productos) con la distancia a la estación GHCN-Daily activa más cercana (▲:
  Puerto Plata, Santo Domingo y Punta Cana). Los datos vienen de `donde_medir_prototipo.csv`.
- **Cómo se lee.** Las clases son terciles de cada variable. La leyenda cuadrada lleva los cortes: 91 % y 94 % de
  tasa de cambio, y 60 km y 97 km de distancia.
- **Números.** 68 celdas caen en la clase alta-alta: San Juan 23, La Estrelleta 14, Pedernales 13, Barahona 7 y otras.
- **Avisos.** Es un PROTOTIPO, como en la auditoría: no dice dónde deben ir las estaciones. Faltan el acceso, la
  exposición, la población y la red de ONAMET e INDRHI.

## 6 · Santo Domingo storm / Tormenta de Santo Domingo, 17-19 nov 2023

`dark/06_santo_domingo_storm.gif` (960 × 540 px; 144 fotogramas a 110 ms más una pausa final; unos 18 s; 0.5 MB) y
`dark/06_santo_domingo_storm_keyframes.png` (6 paneles), `light/…`, `.pdf`

- **Qué muestra.** La lluvia de IMERG V07 Final de media hora acumulándose sobre la RD desde el 17-nov 00:00 UTC,
  con reloj en UTC y en hora local (AST, UTC−4). Al lado, el acumulado en la celda de la auditoría
  (18.45 N, −69.95) y en la más lluviosa de sus 9 vecinas, frente a la línea de 431 mm del pluviómetro.
- **Números.** La celda recibe 140 mm en el día UTC 18, que es exactamente la cifra de la auditoría. En 72 h la
  celda llega a 188 mm y la mejor vecina a 210 mm; el máximo regional en 72 h es 255 mm. La mejor ventana de 24 h de
  la mejor vecina es 185 mm. La brecha sin explicar es de 246 mm.
- **Avisos.** La ventana exacta de 24 h y la coordenada del pluviómetro no son públicas. El veredicto de la
  auditoría es inconcluso para repartir la brecha, pero sí se sostiene que un producto de 10 km no reproduce este
  extremo puntual. La curva de IMERG es de 72 h y los 431 mm son de 24 h, así que la comparación favorece a IMERG.

## No incluido

La **pieza 7**, el *horizon chart* de SPI-3 de IMERG frente a CHIRPS, no se hizo por tiempo; se priorizó el atlas del
Yuna. Los datos ya están en `_datos/spi3_provincias.parquet`.
