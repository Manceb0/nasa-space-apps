# METHODOLOGY

PHANTOM pregunta: **después de una sequía, ¿la vegetación vuelve a verse normal antes de volver a
funcionar normal? ¿Cuánto tiempo, y es una diferencia robusta?**

Este documento manda sobre la sección 4 de `INVESTIGACION.md`, que era el borrador inicial.
El código que lo implementa está en `phantom/`. Cada número de `RESULTS.md` sale de ese código.

---

## 1. Datos

| Señal | Producto | Resolución | Fuente | Para qué |
|---|---|---|---|---|
| Lluvia | GPM IMERG V07 mensual (`GPM_3IMERGM_07_precipitation`) | 0.1°, mensual | Giovanni | Fechar sequías (SPI) |
| Humedad del suelo | GLDAS Noah 2.1 (`RootMoist_inst`, `SoilMoi0_10cm_inst`) | 0.25°, mensual | Giovanni | Contraste con la lluvia |
| Temperatura del aire | MERRA-2 (`M2TMNXSLV_5_12_4_T2M`) | 0.5° × 0.625°, mensual | Giovanni | Restarla a la LST |
| Verdor | MOD13Q1.061 NDVI y EVI | 250 m, 16 días | AppEEARS | "Se ve" |
| Productividad | MOD17A2HGF.061 GPP | 500 m, 8 días | AppEEARS | "Funciona" (modelo) |
| Temperatura de superficie | MOD11A2.061 LST de día | 1 km, 8 días | AppEEARS | "Funciona" (térmica) |
| Cobertura | MCD12Q1.061 LC_Type1 | 500 m, anual | AppEEARS | Excluir puntos que cambiaron |

Ventana común: **2001-01 a 2024-12** (MCD12Q1 empieza en 2001).
Detalle del pedido de AppEEARS, de los puntos y de su revisión en imagen: `appeears/METODO.md`.
Detalle de Giovanni (cajas, celdas, reconstrucciones): `data/giovanni/SEQUIAS.md`.

**Los productos no son independientes entre sí.** MOD17 GPP se calcula con FPAR, que sale de la
misma reflectancia que el NDVI, y con VPD y temperatura mínima de un reanálisis meteorológico.
GLDAS es un modelo que recibe lluvia como entrada. Por eso:
- GPP se presenta como **productividad estimada por un modelo**, no como una medición.
- Una diferencia entre MOD13 y MOD17 **no demuestra** por sí sola daño fisiológico.
- La señal térmica (LST − T aire) es la más independiente del verdor, pero la LST es temperatura
  de la superficie, no del aire, y le afectan las nubes, el viento y el suelo desnudo.

## 2. Calidad, escalas y unidades

`phantom/appeears.py` detecta si el CSV viene crudo o ya escalado y lo anota en el registro.

| Capa | Escala | Unidad final | Filtro |
|---|---|---|---|
| NDVI, EVI | × 0.0001 | adimensional | `pixel_reliability` ∈ {0, 1}; rango −0.2 a 1 |
| LST_Day_1km | × 0.02, − 273.15 | °C | `QC_Day` bits 0–1 = 00, o 01 con error ≤ 2 K (bits 6–7 ≤ 01); 0 = relleno |
| Gpp_500m | × 0.0001 | kgC/m² por periodo de 8 días (acumulado) | relleno 32761–32767 fuera; 0 a 3 |
| LC_Type1 | — | clase IGBP | punto válido si todas las clases 2001–2021 son 1–9 (bosque, matorral, sabana) |

MCD12Q1 posterior a 2021 no se usa para decidir, por el aviso de NASA sobre sus datos de entrenamiento.
Cada producto se analiza en su propio paso temporal (16 u 8 días). No se agregan a mensual para
calcular recuperaciones: así no se mezclan promedios con acumulados.

## 3. Sequías

`phantom/drought.py`, sobre IMERG y GLDAS (24 años):

1. **Exploratorio:** meses bajo el percentil 20 de su mes calendario (el criterio de `sequias.py`).
2. **Anomalía:** valor menos la media del mismo mes calendario.
3. **SPI-3 y SPI-6:** gamma de dos parámetros por mes calendario, con probabilidad de cero.
   Un evento es una racha de **2 o más meses con SPI ≤ −1**.

Eventos usados para medir recuperaciones: **SPI-3 ≤ −1 durante 2+ meses** (`results/eventos_principales.csv`).

Limitaciones del SPI aquí:
- Con 24 años, cada mes calendario tiene 24 valores para ajustar la gamma. Las colas (SPI < −2)
  son poco fiables.
- En la estación seca hay meses con muy poca lluvia; si hay menos de 10 acumulados positivos
  en un mes calendario, ese mes queda sin SPI.
- IMERG y GLDAS no se validan entre sí de forma independiente (GLDAS recibe lluvia).
  El catálogo marca cuándo coinciden (`coincide_lluvia_y_suelo`), sin llamarlo confirmación.

## 4. Anomalías de vegetación

Para cada punto y señal: **z robusto por época del año**.

- Época = (día del año − 1) // periodo del producto.
- z = (valor − mediana de esa época en 2001–2024) / (1.4826 × MAD de esa época).
- Se exige al menos 8 años válidos por época; si no, z queda vacío.
- Orientación: negativo = peor. Para la señal térmica se usa −z de (LST − T aire), porque un dosel
  más caliente que el aire indica menos transpiración.
- Antes de buscar recuperaciones, z se suaviza con una **mediana móvil de 3 observaciones válidas**.
  Las pruebas mostraron que, sin esto, una sola observación ruidosa movía la fecha de
  recuperación hasta tres meses.

## 5. Recuperación y brecha (Δt)

`phantom/recovery.py`. Para cada evento:

- **Impacto:** 3 observaciones válidas seguidas con z < −1.5, entre el inicio de la sequía y
  120 días después de su fin. Una sola observación baja es ruido, no impacto.
- **Recuperación:** primera fecha, después del inicio del impacto, en que z ≥ **−1** durante
  **3** observaciones válidas seguidas. Es decir: volver a menos de una desviación de lo normal
  y quedarse ahí.
- **Ventana:** termina en lo que llegue primero: la siguiente sequía, 365 días después del fin
  del evento o el fin de la serie.
- **Censurado:** hubo impacto, pero no hubo recuperación dentro de la ventana. Si solo la función
  está censurada, Δt se reporta como **cota inferior**.

**Δt = t(función) − t(verde)**, en días. Positivo: la función se recupera después del verdor.
Se calcula para dos señales de función: `gpp_modelo` y `lst_menos_aire`.

Por qué −1 y no −0.5: una serie sana pasa el 31 % del tiempo bajo −0.5 solo por ruido. Con −0.5,
las pruebas sintéticas daban recuperaciones falsas o tardías.

### Sensibilidad y robustez

Cada evento se recalcula con 18 combinaciones: verdor {NDVI, EVI} × umbral {−1.5, −1, −0.5} ×
persistencia {2, 3, 4}.

- **ROBUSTO:** al menos 6 combinaciones válidas, ≥ 80 % con el mismo signo que la principal
  y |mediana de Δt| > 32 días (dos compuestos de 16 días).
- **SENSIBLE A SUPUESTOS:** hay combinaciones válidas, pero el signo cambia o la diferencia es menor
  que la resolución.
- **SIN DATOS SUFICIENTES:** menos de 6 combinaciones válidas.

Precisión: ±2 compuestos (unos 32 días). Una brecha menor que eso no se distingue de cero.

## 6. Tendencias

`phantom/stats.py`:
- **Theil-Sen** (pendiente robusta, IC 95 %) y **Mann-Kendall** (con corrección por empates) para:
  - Δt de cada punto y señal frente al año del evento, **solo si hay 4 o más eventos** con ambas
    recuperaciones.
  - Medias anuales de NDVI, GPP y LST por punto (24 años).
- **Autocorrelación de lag 1**, informada junto a cada prueba. Mann-Kendall supone independencia;
  si la autocorrelación es alta, el p-valor es optimista.
- **Benjamini-Hochberg (FDR)** sobre todas las pruebas de la corrida. `RESULTS.md` dice cuántas
  pruebas se hicieron, para que nadie elija la mejor de muchas sin decirlo.

## 7. Qué se puede afirmar y qué no

| Si sale… | Se dice | No se dice |
|---|---|---|
| Δt > 32 días, ROBUSTO, en varios eventos y puntos | "En estos puntos, la señal X tardó más que el verdor en volver a lo normal" | "El bosque está dañado", "los bosques secos dominicanos…" |
| Δt cambia de signo con los supuestos | "La brecha depende del método; no es concluyente" | Que existe una brecha |
| Pocos datos válidos tras el filtro | "No hay datos suficientes" | Cualquier número |
| Tendencia con q < 0.05 | "Asociación estadística en esta muestra" | Causalidad |

Cinco puntos son un piloto. La fase 2 (pedido por áreas, todos los píxeles estables, dependencia
espacial) está descrita en `appeears/METODO.md`.

## 8. Pruebas automáticas

`uv run pytest` usa datos **sintéticos**, generados en `tests/synthetic.py` y marcados como tales.
Nunca escriben en `results/` ni en `figures/`. Cubren:
- recuperación completa con brecha conocida;
- recuperación incompleta (censura y cota inferior);
- 30 % de valores faltantes;
- una sequía que se superpone a la siguiente;
- ausencia de brecha y ausencia de impacto;
- inversión de la señal térmica;
- escalas crudas o ya escaladas, bits de QC de LST y relleno de GPP;
- estabilidad de la cobertura del suelo;
- SPI, rachas, Mann-Kendall, Theil-Sen y Benjamini-Hochberg;
- el pipeline completo con archivos con el formato de AppEEARS en una carpeta temporal.
