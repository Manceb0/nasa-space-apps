# Pedido AppEEARS: phantom-rd-puntos-v2

**Fase 1: exploración.** Sirve para ver si hay señal y elegir sitios. No es evidencia regional.
Cinco puntos aislados no prueban una tendencia en los bosques secos dominicanos.

## Fechas: 01-01-2001 → 12-31-2024

Disponibilidad real, consultada en la API de AppEEARS el 2026-11-14:

| Producto | Desde | Hasta |
|---|---|---|
| MOD13Q1.061 | 2000-02-18 | presente |
| MOD11A2.061 | 2000-02-18 | presente |
| MOD17A2HGF.061 | 2000-01-01 | presente |
| MCD12Q1.061 | 2001-01-01 | presente (anual; los últimos años pueden faltar) |

2001–2024 es la ventana común de años completos. Aviso de NASA: MCD12Q1 posterior a 2021 se
interpreta con cautela, porque sus datos de entrenamiento no se actualizaron.

## Puntos (revisados en imagen satelital de Google Maps, 2026-11-14)

| id | lat, lon | Qué se ve | Notas |
|---|---|---|---|
| montecristi_monte_seco_a | 19.87, -71.50 | Monte seco continuo en lomas | Hay fincas a ~2 km |
| montecristi_monte_seco_b | 19.86, -71.46 | Monte seco continuo, camino cerca | A ~4.5 km de `a`: no son independientes |
| sierra_montecristi | 19.80, -71.42 | Bosque denso en la sierra | Hay claros dispersos alrededor |
| jaragua_comparacion_seco | 17.74, -71.45 | Bosque seco continuo, P. N. Jaragua | Otro clima y otro suelo: no es un control estadístico |
| cordillera_comparacion_humedo | 19.03, -70.84 | Bosque de montaña continuo | Más nubes; menos LST limpia |

Descartados en la v1: 19.80,-71.58 (río Yaque y arrozales), 19.68,-71.55 (mosaico de fincas),
17.85,-71.45 y 17.83,-71.41 (campos y la pista de un aeropuerto), 19.05,-70.80 (poblado de Manabao).

Jaragua y Cordillera son **comparaciones**, no controles: tienen otro clima y otra vegetación.

**Regla de estabilidad:** si `LC_Type1` cambia de clase en algún año 2001–2021, el punto se excluye.
Clases aceptadas: 1–5 (bosques), 6–7 (matorral), 8–9 (sabana arbolada / sabana).
Si es 12 o 14 (cultivos), se excluye.

## Escala, unidades y relleno (consultado en la API de AppEEARS)

| Capa | Factor | Unidad | Relleno | Rango válido |
|---|---|---|---|---|
| `_250m_16_days_NDVI` | 0.0001 | NDVI | -3000 | -0.2 a 1 |
| `_250m_16_days_EVI` | 0.0001 | EVI | -3000 | -0.2 a 1 |
| `LST_Day_1km` | 0.02 | Kelvin | 0 | 150 a 1310.7 (crudo 7500–65535) |
| `Gpp_500m` | 0.0001 | kgC/m²/8 días | 32767 | 0 a 3 |
| `LC_Type1` | — | clase IGBP | 255 | 1 a 17 |

AppEEARS suele entregar el CSV ya escalado. **Comprobar en la primera fila**: si el NDVI sale
como 0.65, ya está escalado; si sale como 6500, falta multiplicar.

## Filtro de calidad (antes de cualquier cálculo)

- **NDVI/EVI:** se queda solo `pixel_reliability` = 0 (bueno) o 1 (marginal). Fuera 2 (nieve),
  3 (nubes) y -1 (sin dato). Análisis de sensibilidad: repetir solo con 0.
- **LST:** `QC_Day` bits 0–1 = 00 (buena calidad). Con 01 (otra calidad) se acepta solo si los
  bits 6–7 (error de LST) ≤ 01, es decir ≤ 2 K. Todo lo demás, fuera.
- **GPP:** se descartan los valores de relleno (≥ 32761). `Psn_QC_500m` se guarda para documentar
  qué fechas usaron FPAR rellenado.
- Después de filtrar, anotar cuántas observaciones quedan por punto y año. Si un año pierde más
  del 50 %, se marca y no se usa para fechar una recuperación.

## Qué es cada señal (y qué no es)

- **NDVI / EVI:** verdor. No es salud ni productividad.
- **LST:** temperatura de la superficie, **no del aire**. Se compara contra la temperatura del aire
  (MERRA-2 en Giovanni) para aislar el calentamiento de la vegetación.
- **MOD17 GPP:** productividad **estimada por un modelo**. Usa FPAR (sacado de la misma
  reflectancia que el NDVI) y la meteorología de un reanálisis (VPD, temperatura mínima). No es una
  medición independiente del verdor y no se presenta como tal.

## Fase 2 (si la fase 1 muestra señal)

Pedido de **área** (polígonos) en vez de puntos: todos los píxeles de vegetación natural estable
de la Línea Noroeste, quitando cultivos, riego y píxeles que cambiaron de clase. Se analiza la
dependencia espacial (píxeles vecinos no cuentan como muestras independientes) y se comparan
regiones con muchos píxeles, no con un punto.

## Registro del pedido

| Versión | Fecha | ID de AppEEARS | Estado |
|---|---|---|---|
| v2 | 2026-11-14 | `9490ce7b-3268-46aa-84a6-bbe8a3b648ed` | Pending al enviar. AppEEARS avisa por correo al terminar. |

Ver el estado: https://appeears.earthdatacloud.nasa.gov/explore
Descargar: https://appeears.earthdatacloud.nasa.gov/download/9490ce7b-3268-46aa-84a6-bbe8a3b648ed

**Todavía no hay ningún resultado científico.** Este pedido solo trae los datos.

**Estado del pedido de puntos:** terminado y descargado el 2026-11-14 (zip con 4 CSV de resultados, metadatos,
`request.json` y `granule-list.txt`) en `data/appeears/`. Notas de lectura:
- AppEEARS entrega los valores **ya escalados**. El lector lo detecta y no vuelve a escalar (queda en `results/estado_modis.json`).
- AppEEARS **quita los guiones bajos** de los ID (`montecristi_monte_seco_a` → `montecristimontesecoa`).
- Pasan calidad: MOD13Q1 2701 de 2765; MOD11A2 5310 de 5510; MOD17A2HGF 5525 de 5525.

**Cobertura del suelo (MCD12Q1, 2001–2021), y una corrección a la regla de arriba:**

| Punto | Clases IGBP | Lectura |
|---|---|---|
| Montecristi A | 2 (bosque perenne de hoja ancha) y 9 (sabana) | Cambia entre clases naturales |
| Montecristi B | 9 (sabana) | Estable |
| Sierra de Montecristi | 8 (sabana arbolada) y 9 (sabana) | Cambia entre clases naturales |
| Jaragua | 2 | Estable |
| Cordillera | 2 | Estable |

La regla escrita decía "si cambia de clase, se excluye". El código aplicó otra: se excluye si aparece alguna
clase no natural. Ningún punto pasó a cultivo ni a zona urbana. Los cambios bosque/sabana/sabana arbolada
son frecuentes en MCD12Q1 en bosques secos y pueden ser confusión de la clasificación o degradación real.
**Decisión:** los puntos se conservan y se marcan como "inestables". El paso de bosque a sabana en Montecristi A
es coherente con la bajada del NDVI, pero no se presenta como prueba de degradación.

### Pedido de área (para el atlas)

| Versión | Fecha | ID de AppEEARS | Contenido |
|---|---|---|---|
| area-v1 | 2026-11-14 | `eec5627a-a7a7-43c3-8433-ecc39685f375` | GeoTIFF geográfico (EPSG:4326), 2012–2021, mismas 8 capas. Polígonos: Montecristi monte seco (−71.55, 19.76, −71.38, 19.92) y Jaragua bosque seco (−71.52, 17.66, −71.36, 17.82). Archivo: `appeears/phantom-rd-area.json` |

Se recortó a 2012–2021 para que AppEEARS tenga más opciones de entregarlo antes del cierre. Cubre las
sequías de 2015 y 2019–2020 con 10 años de referencia: es el mínimo para la regla de 8 años por época
del año. Las superficies se calcularán solo con píxeles válidos y estables; si el pedido no llega a
tiempo, el atlas no se publica.

### Pedido de agua del dosel (NDII)

| Versión | Fecha | ID de AppEEARS | Contenido |
|---|---|---|---|
| ndii-v1 | 2026-11-14 | `6aacfca4-1303-4c60-9acb-7227f2329744` | MOD09A1.061 (500 m, 8 días): `sur_refl_b02` (NIR), `sur_refl_b06` (SWIR 1,6 µm), `sur_refl_state_500m`, `sur_refl_qc_500m`; mismos 5 puntos; 2001–2024. Archivo: `appeears/phantom-rd-ndii.json` |

Para qué sirve:
- **NDII = (b2 − b6) / (b2 + b6)** mide el agua del dosel. Es la señal que, según Yan et al. 2025 (*Nature Plants*), se recupera más tarde que el verdor.
- **Filtro:** despejado (bits 0-1 = 00), sin sombra (bit 2), sin nube interna (bit 10) y no adyacente a nube (bit 13).
- **Cuenta como señal observada,** igual que la térmica. Si cae y el verdor no, es "estrés invisible".
- **Integración automática:** al poner el CSV en `data/appeears/`, el pipeline lo incorpora sin cambios de código (`phantom/appeears.py:read_mod09`).
