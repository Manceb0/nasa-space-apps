# Contrato de datos · P0 Tendencias (results/tendencias/web/)

Versión del esquema: **1.0**. Lo genera `python -m earthmemory.tendencias.run` (`earthmemory/tendencias/web.py`).
Todos los archivos son JSON UTF-8 compactos. Números redondeados a 3-4 cifras significativas; **`null` = sin dato**
(mar, celda fuera del país, periodo sin eventos o estadístico no aplicable). Total < 6 MB (`tamanos.json` lo dice).

| archivo | para qué pantalla | tamaño aprox. |
|---|---|---|
| `variables.json` | selector de variable / periodo, leyendas, textos de ayuda | ~11 kB |
| `provincias.json` | ficha de provincia: serie anual de cada índice y producto + tendencia | ~0.8 MB |
| `rejilla.json` | mapa por celdas de 0.1° (pendiente, q y clase de confianza) | ~1.3 MB |
| `resumen.json` | titulares nacionales, conteos de celdas/provincias, falsos positivos medidos | ~60 kB |

Ids que se repiten en todos los archivos:

- **índice** (`indice`): `CDD, CWD, PRCPTOT, R1mm, SDII, R20mm, R50mm, Rx1day, Rx5day, R95pTOT, R99pTOT, RACHAS10, RACHAS15`
  (lluvia diaria, 4 periodos) y `SPI3_MESES, SPI3_EVENTOS, SPI3_SEVER, SPI3_DURAC, SPI12_MESES, SPI12_EVENTOS,
  SPI12_SEVER, SPI12_DURAC` (sequía, solo periodo `anual`).
- **periodo**: `anual` (ene-dic), `seca` (dic del año anterior a abr), `humeda_temprana` (may-jul), `humeda_tardia` (ago-nov).
- **producto** (`fuente`): `IMERG` (NASA GPM IMERG V07 Final, "recuperación satelital calibrada con pluviómetros"),
  `CHIRPS` (CHIRPS v2.0, "satélite + estaciones"). Ambos en la misma rejilla de 0.1°.
- **región**: código ISO 3166-2 de geoBoundaries (`DO-01` … `DO-32`) y `DO` = República Dominicana (nacional).
- **clase de confianza**: `robusta`, `consistente`, `en disputa`, `sin señal detectable` (ver `variables.json → clases`).

---

## 1. `variables.json`

```json
{
  "version": "1.0",
  "generado_utc": "2026-11-15T01:23:45Z",
  "anios": [2001, 2024],
  "productos": {"IMERG": {"nombre": "IMERG V07 Final (NASA GPM)", "tipo_fuente": "recuperación satelital calibrada con pluviómetros",
                          "resolucion_nativa": "0.1°", "cita": "Huffman, G.J. et al. (2023) … doi:10.5067/GPM/IMERGDF/DAY/07"},
                "CHIRPS": {"nombre": "CHIRPS v2.0 (CHC/UCSB)", "tipo_fuente": "satélite + estaciones", "…": "…"}},
  "periodos": {"anual": {"label_es": "Año (ene-dic)", "label_en": "Year (Jan-Dec)", "meses": [1,2,3,4,5,6,7,8,9,10,11,12]},
               "seca": {"label_es": "Estación seca (dic-abr)", "label_en": "Dry season (Dec-Apr)", "meses": [12,1,2,3,4]}, "…": {}},
  "clases": {"robusta": {"label_es": "Robusta", "label_en": "Robust", "color": "#0072B2",
                         "descripcion": "Los dos productos muestran tendencia significativa (FDR q ≤ 0.10) en la misma dirección."},
             "consistente": {"…": "…", "color": "#56B4E9"}, "en disputa": {"…": "…", "color": "#D55E00"},
             "sin señal detectable": {"…": "…", "color": "#E6E6E6"}},
  "umbral_significancia": {"q_fdr": 0.1, "regla": "FDR de Benjamini-Hochberg con α_FDR = 2·α_global (Wilks 2016), α_global = 0.05"},
  "prueba": "Mann-Kendall modificado de Hamed y Rao (1998) + pendiente de Theil-Sen (IC 95 % de Sen)",
  "nota_causalidad": "Las tendencias describen cambios observados 2001-2024; no atribuyen causas.",
  "variables": [
    {"id": "CDD", "label_es": "Días secos consecutivos (máx.)", "label_en": "Consecutive dry days (max)",
     "unidad": "días", "unidad_tendencia": "días/década",
     "descripcion": "La racha más larga de días con menos de 1 mm.",
     "por_que_importa": "Rachas secas largas estresan cultivos, pastos y abasto de agua.",
     "tipo": "seco", "aumento_significa": "más seco",
     "periodos": ["anual", "seca", "humeda_temprana", "humeda_tardia"], "grupo": "periodos_secos"}
  ]
}
```

- `tipo` ∈ {`seco`, `humedo`}; `grupo` ∈ {`periodos_secos`, `lluvia`, `sequia`}. Para colorear: si `tipo == "seco"` un
  aumento es "más seco" (paleta marrón para valores positivos); si `humedo`, un aumento es más lluvia (verde-azul).
- Los colores de clase son Okabe-Ito (aptos para daltonismo).

## 2. `provincias.json`

```json
{
  "version": "1.0",
  "regiones": [{"id": "DO", "nombre": "República Dominicana", "es_nacional": true},
               {"id": "DO-02", "nombre": "Azua", "es_nacional": false}, "…"],
  "anios": {"anual": [2001, …, 2024], "seca": [2002, …, 2024], "humeda_temprana": [2001, …, 2024],
            "humeda_tardia": [2001, …, 2024], "spi": [2002, …, 2024]},
  "series": {
    "CDD": {"anual": {"IMERG":  {"DO": [41.63, 37.39, 41.5, …], "DO-02": […], …},
                      "CHIRPS": {"DO": […], …}},
            "seca": {…}, …},
    "SPI3_MESES": {"anual": {"IMERG": {"DO": [ … 23 valores … ]}, …}}
  },
  "tendencias": {
    "CDD": {"anual": {"DO": {
        "IMERG":  {"pendiente_decada": -0.455, "ic95": [-5.54, 4.40], "p": 0.901, "q": null, "sig": null, "sig_p05": false,
                   "mdt": 8.82, "media": 39.31, "detectable": false, "pendiente_pct_decada": -1.16},
        "CHIRPS": {…},
        "clase": "sin señal detectable"},
      "DO-02": {…}}}}
}
```

- **Años de cada serie:** `series[indice][periodo][producto][region]` es una lista alineada con
  `anios[periodo]`, salvo los índices `SPI*`, que se alinean con `anios.spi` (2002-2024). Valores `null` posibles
  (p. ej. `SPI*_DURAC` en años sin eventos).
- **Serie de provincia** = media ponderada por área de los índices de las celdas de 0.1° que tocan la provincia.
- **Tendencia:** `pendiente_decada` (Theil-Sen, unidad del índice por década), `ic95` [inferior, superior],
  `p` (Mann-Kendall de Hamed-Rao), `q` (FDR de Benjamini-Hochberg **entre las 32 provincias**; `null` en `DO`),
  `sig` = `q ≤ 0.10` (`null` en `DO`), `sig_p05` = `p < 0.05` (úsese para `DO`), `mdt` = tendencia mínima
  detectable (misma unidad que la pendiente; 80 % de potencia, α = 0.05), `detectable` = `|pendiente| ≥ mdt`,
  `media` = media 2001-2024 del índice, `pendiente_pct_decada` = pendiente / media × 100.
- `clase`: clase de confianza de dos productos para esa región. En provincias, "significativo" = `sig` (q ≤ 0.10
  entre las 32 provincias). En `DO` (una sola serie, una sola prueba) "significativo" = `sig_p05` (p < 0.05).

## 3. `rejilla.json`

```json
{
  "version": "1.0", "resolucion_grados": 0.1, "nx": 39, "ny": 26,
  "lat": [17.45, 17.55, …, 19.95], "lon": [-72.05, -71.95, …, -68.25],
  "lat_bordes": [17.4, …, 20.0], "lon_bordes": [-72.1, …, -68.2],
  "orden": "lista plana de ny*nx valores; k = fila*nx + col; fila 0 = latitud más al SUR (lat[0]), col 0 = más al OESTE (lon[0])",
  "incluida": [0, 0, …, 1, …],
  "provincia_principal": [null, …, "DO-21", …],
  "clases_codigo": ["robusta", "consistente", "en disputa", "sin señal detectable"],
  "capas": {
    "CDD": {"anual": {"IMERG":  {"pendiente_decada": [null, …, 1.67, …], "q": [null, …, 0.83, …]},
                      "CHIRPS": {"pendiente_decada": […], "q": […]},
                      "clase": [null, …, 3, …]},
            "seca": {…}, …}, …}
}
```

- Cada capa es una **lista plana de 1014 valores** (26 × 39). Celda k: fila `i = k // 39`, columna `j = k % 39`,
  centro (`lat[i]`, `lon[j]`), rectángulo `[lon_bordes[j], lon_bordes[j+1]] × [lat_bordes[i], lat_bordes[i+1]]`.
- Solo las 442 celdas con `incluida = 1` (≥ 25 % del área en RD) tienen valores; el resto es `null`.
- `q` es el valor q de FDR **entre las 442 celdas** (por índice × periodo × producto). Marcar como significativa si
  `q ≤ 0.10` (punteado en las figuras).
- `clase` es un entero que indexa `clases_codigo` (0 = robusta … 3 = sin señal detectable).
- Para la dirección de una celda robusta/consistente use el signo de `pendiente_decada` (si es 0, la dirección viene de
  la S de Mann-Kendall; está en `results/tendencias/tendencias_celdas.csv`, columna `signo`).

## 4. `resumen.json`

```json
{
  "version": "1.0",
  "calibracion": {"fpr_nominal": 0.05, "fpr_local_celdas_fases": 0.06, "fpr_local_celdas_bloques": 0.04,
                  "fpr_local_provincias_fases": 0.06, "fpr_local_provincias_bloques": 0.04,
                  "fraccion_mapas_nulos_con_celda_fdr_media": 0.05, "n_sustitutos": 1000},
  "indices": [
    {"indice": "CDD", "periodo": "anual", "fuente": "IMERG", "celdas": 442, "celdas_sig_fdr": 0,
     "celdas_sig_fdr_aumento": 0, "celdas_sig_fdr_descenso": 0, "celdas_p05_sin_fdr": 50,
     "campo_significativo_wilks": false, "mediana_pendiente_decada": 0.0, "mediana_mdt": 13.95,
     "celdas_pendiente_mayor_mdt": 2, "provincias_sig_fdr": 0,
     "nacional_pendiente_decada": -0.455, "nacional_ic95_inf": -5.54, "nacional_ic95_sup": 4.40, "nacional_p": 0.901,
     "nacional_mdt": 8.82, "nacional_media": 39.31,
     "celdas_robusta": 0, "provincias_robusta": 0, "celdas_consistente": 0, "provincias_consistente": 0,
     "celdas_en_disputa": 0, "provincias_en_disputa": 0, "celdas_sin_senal_detectable": 442,
     "provincias_sin_senal_detectable": 32, "celdas_robusta_aumento": 0, "celdas_robusta_descenso": 0,
     "clase_nacional": "sin señal detectable",
     "p_campo_fase": 0.27, "fpr_fase": 0.048, "p_campo_bloques": 0.09, "fpr_bloques": 0.015}
  ]
}
```

- Una fila por índice × periodo × producto. Los conteos de clase (`celdas_robusta`, …) son por celda y valen lo mismo
  en la fila IMERG y en la CHIRPS (la clase combina los dos).
- `p_campo_*`, `fpr_*` solo existen en filas `periodo = "anual"` (la calibración se hizo con índices anuales).
- `campo_significativo_wilks`: hay al menos una celda con q ≤ 0.10 (criterio de Wilks 2016).

## Textos obligatorios en pantalla

1. "Sin señal detectable" **no** es "sin cambio": con 24 años solo se detectan cambios mayores que `mdt`.
2. Tendencias observadas 2001-2024; **no** atribuyen causas.
3. IMERG = recuperación satelital calibrada con pluviómetros; CHIRPS = satélite + estaciones. No son testigos
   totalmente independientes (comparten infrarrojo geoestacionario y pluviómetros).

## Equivalencia con los CSV

`results/tendencias/tendencias_celdas.csv` y `tendencias_provincias.csv` contienen todas las columnas (incluidas `S`,
`Z`, `p_mk_sin_correccion`, `factor_hr`, `sigma_res`, `r1`, `signo`); `series_provincias.csv` es la forma larga de
`provincias.json → series`.
