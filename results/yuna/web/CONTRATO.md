# Contrato de datos · caso Yuna (results/yuna/web/)

Generado por `docker compose run --rm yuna`. Todo es JSON UTF-8 (GeoJSON en WGS84 lon/lat). Los valores
faltantes son `null`. Cada variable lleva su CLASE; la pantalla debe mostrarla junto al dato:

| clase | productos |
|---|---|
| OBSERVACIÓN | JRC Global Surface Water mensual (Landsat 30 m; nubes = sin dato) |
| RECUPERACIÓN SATELITAL | IMERG Final V07 (calibrado con pluviómetros GPCC), CHIRPS v2 (+ estaciones) |
| MODELO CON ASIMILACIÓN | SMAP L4 (Catchment + Tb SMAP; su lluvia se ajusta a IMERG: no es independiente de IMERG) |
| MODELO FORZADO | GLDAS-2.1 Noah (GDAS + GPCP; sin asimilación de suelo) |
| SIMULACIÓN HIDROLÓGICA | GEOGLOWS v2 retrospectivo (forzado con ERA5; no son aforos; sin operación de Hatillo) |
| REGISTRO DOCUMENTAL | catálogo de eventos (prensa, gobierno, IFRC, CEPAL), cada evento con URL |

## Archivos

- `cuencas.geojson` — FeatureCollection; `properties.zona` ∈ {`yuna`, `alto_hatillo`, `camu`, `bajo_yuna`,
  `Yaque del Norte`, `Yaque del Sur`, `Ozama`}, `properties.area_km2`. Simplificado (0.004°). Fuente: HydroBASINS v1c nivel 10.
  `alto_hatillo` + `camu` + `bajo_yuna` = `yuna` (disjuntas).
- `rios.geojson` — tramos HydroRIVERS con ≥ 300 km² drenados: `HYRIV_ID`, `UPLAND_SKM`, `ORD_STRA`, `DIS_AV_CMS`
  (caudal medio MODELADO de HydroRIVERS).
- `que_drena_donde.json` — lista de puntos/celdas: `punto`, `lat`, `lon`, `celda_grados` (null = punto),
  `frac_<cuenca>` (fracción del rectángulo de la celda, o 0/1 para un punto), `salida_cuenca`.
- `catalogo.json` — `{clase, eventos:[{id, inicio, fin, precision, nombre, zona, lugares, impacto, confianza,
  n_fuentes, n_fuentes_leidas, fuentes_url:[...], hatillo_menciones, usable_backtest, motivo_exclusion}]}`.
  `zona = hatillo_operacion` son marcadores de operación de la presa, no inundaciones.
- `series_eventos.json` — `{clases, eventos:[{id, inicio, fin, series:{fecha:[...], imerg_media_yuna_mm,
  imerg_max_celda_yuna_mm, imerg_ant30_yuna_mm, smap_raiz_<zona>_m3m3, q_<punto>_m3s, chirps_media_yuna_mm},
  resumen:{...fila de results/yuna/paneles_eventos.csv...}}]}`; ventana −60 a +15 días. `q_yuna_villa_riva`,
  `q_yuna_cotui`, `q_camu_confluencia`, `q_yuna_hatillo` son GEOGLOWS (simulación) **pero quedaron en arroyos
  laterales, no en el cauce del Yuna: NO mostrarlos como caudal del Yuna** (ver CASO_YUNA.md §5).
- `hatillo.json` — `ficha` (datos publicados, con fuentes y conflictos: capacidad 710 / 441,6 / ~400 / 374,88 hm³ según
  definición y fuente) y `gsw_mensual` (área de agua del embalse y de la llanura, km², con fracción de píxeles válidos;
  usar solo meses con fracción válida ≥ 0.5 en el embalse y ≥ 0.3 en la llanura).
- `backtest.json` — `tabla` (una fila por disparador y periodo: POD, FAR, CSI con `*_ic95`, n de eventos,
  episodios), `info` (umbrales calibrados), `presa` (AUC por zona) y `presa_mensual` (ρ por estado del embalse).

- `mcdwd.json` — inundación observada MODIS MCDWD (OBSERVACIÓN): `reglas`, `referencia` (días secos: mediana y p95
  de km² de clase 3 por zona), `eventos` (por evento del catálogo: `observa` true/false/null = nubes,
  `inund_km2_max_<zona>`, `anomalia_km2_<zona>`, `insuf_min_<zona>`, `dia_max_<zona>`) y `dias` (por fecha bajada:
  `insuf_<zona>` fracción de datos insuficientes, `agua_ref_km2_<zona>`, `recurrente_km2_<zona>`, `inund_km2_<zona>`).
  Zonas: `yuna`, `alto_hatillo`, `camu`, `bajo_yuna`, `llanura` (Bajo Yuna < 20 m).

## Reglas de lectura
- No decir «Hatillo regula/controla las crecidas»; la presa opera en «vertido libre» según INDRHI (2021).
- No decir «predice» ni «alerta temprana»: es evidencia retrospectiva con n pequeño.
- FAR es cota superior (el catálogo de prensa es incompleto).
