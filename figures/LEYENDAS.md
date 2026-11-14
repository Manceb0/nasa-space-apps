# Leyendas y texto alternativo

Cada figura existe en PDF (vectorial, para la entrega) y PNG (300 ppp). Junto a cada una hay un
`.json` con los datos de origen, las transformaciones y el tamaño físico. Todas salen de
`phantom/figures.py`. Colores: paleta Okabe-Ito, siempre con una segunda pista (posición,
marcador o estilo de línea).

## Figura 1. Sequías 2001–2024 (`fig1_sequias`)

**Leyenda.** (a, c) Índice estandarizado de precipitación a 3 meses (SPI-3) calculado con
GPM IMERG V07 mensual, promediado sobre cada zona. Barras bermellón: SPI-3 negativo; grises:
positivo. Línea discontinua: SPI = −1. Barras negras bajo el eje: sequías usadas en el análisis
(SPI-3 ≤ −1 durante 2 o más meses), con el año de las tres más severas (suma del SPI-3).
(b, d) Anomalía estandarizada mensual de la humedad del suelo en la zona de raíces (GLDAS
Noah 2.1) frente a su mismo mes de 2001–2024. GLDAS recibe lluvia como entrada, así que (b, d)
no es una validación independiente de (a, c). Los dos primeros meses no tienen SPI-3.

**Texto alternativo.** Cuatro paneles apilados, de 2001 a 2024. Montecristi y Jaragua comparten
una sequía larga en 2015. En Montecristi, las otras dos más severas son 2020 y 2022–23. En Jaragua
son 2004–05 y 2023. La humedad del suelo queda bajo −1 de forma sostenida en 2015 y en 2018–2020
en las dos zonas.

## Figura 2. Coincidencia entre criterios de sequía (`fig2_criterios_sequia`)

**Leyenda.** Periodos de 2 o más meses bajo −1 según tres criterios: SPI-3 y SPI-6 (lluvia,
IMERG) y humedad del suelo estandarizada (GLDAS, zona de raíces). (a) Montecristi; (b) Jaragua.
Sirve para ver qué sequías aparecen con más de un criterio.

**Texto alternativo.** Tres filas de barras horizontales por zona. Los tres criterios coinciden
en 2015 y en 2018–2020 en las dos zonas. Antes de 2014, en Jaragua la humedad del suelo nunca
baja de −1 durante 2 meses seguidos, aunque la lluvia sí marca sequías.

## Figura 3. Recuperación tras una sequía (`fig3_evento_<punto>_<inicio>`)

Se genera solo con datos MODIS reales, para las tres sequías más severas de cada punto.

**Leyenda.** Anomalía estandarizada robusta (z, por época del año) de (a) NDVI, (b) GPP MOD17
(producto de modelo) y (c) temperatura del dosel menos la del aire (LST MOD11A2 − T2M MERRA-2,
con el signo invertido: negativo = dosel más caliente). Puntos: observaciones que pasan el
control de calidad. Línea: mediana móvil de 3 observaciones. Franja gris: sequía (SPI-3).
Línea discontinua: umbral de recuperación z = −1. Línea punteada: fecha en que la señal vuelve
y se mantiene sobre el umbral durante 3 observaciones.

## Figura 4. Sensibilidad de Δt (`fig4_sensibilidad_dt`)

Se genera solo con datos MODIS reales.

**Leyenda.** Δt = recuperación de la función − recuperación del verdor, en días, para las 18
combinaciones de supuestos (verdor NDVI o EVI × umbral −1.5, −1, −0.5 × persistencia 2, 3, 4),
por punto y sequía. Azul: GPP MOD17; bermellón: dosel frente a aire. Círculo: NDVI; rombo: EVI.
Franja gris: ±32 días, la precisión del método (dos compuestos de 16 días). Solo aparecen las
combinaciones en que las dos señales se recuperaron dentro de la ventana.
