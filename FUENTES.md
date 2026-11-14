# Fuentes y parámetros

Todo lo que usa PHANTOM, con la consulta exacta para repetirlo. Fecha de acceso: 2026-11-14.

## Datos

| Dato | Proveedor y herramienta | Consulta | Archivo |
|---|---|---|---|
| GPM IMERG V07 mensual | NASA GES DISC, Giovanni | `GPM_3IMERGM_07_precipitation`, área promedio, 2001-01 → 2024-12 | `data/giovanni/imerg_precip_*.csv` |
| MERRA-2 T2M mensual | NASA GMAO / GES DISC, Giovanni | `M2TMNXSLV_5_12_4_T2M` | `data/giovanni/merra2_t2m_*.csv` |
| GLDAS Noah 2.1 mensual | NASA GES DISC, Giovanni | `GLDAS_NOAH025_M_2_1_SoilMoi0_10cm_inst`, `..._RootMoist_inst` | `data/giovanni/gldas_*.csv` |
| MOD13Q1.061, MOD11A2.061, MOD17A2HGF.061, MCD12Q1.061 | NASA LP DAAC, AppEEARS | Point Sample `phantom-rd-puntos-v2`, ID `9490ce7b-3268-46aa-84a6-bbe8a3b648ed` | `appeears/phantom-rd-puntos.json` (pedido); resultados en `data/appeears/` |

Cada CSV de Giovanni trae en su cabecera la caja pedida, la caja real de los datos y la fila
"URL to Reproduce Results". Cinco de ellos son reconstrucciones del texto CSV de Giovanni
(descarga bloqueada por el navegador). Se verificaron valor por valor contra el original regenerado: son el original redondeado a 4 decimales. Ver `data/giovanni/SEQUIAS.md`.

Cajas (O, S, E, N):
- Noroeste: −71.60, 19.75, −71.35, 19.92 (GLDAS ampliada a −71.63, 19.62, −71.35, 19.92).
- Jaragua: −71.60, 17.62, −71.30, 17.85 (GLDAS ampliada a −71.60, 17.62, −71.30, 17.88).

Revisión de los puntos en imagen satelital: Google Maps (vista satélite), 2026-11-14. Solo se usó
para comprobar visualmente la cobertura; no entra en ningún cálculo.

## Herramientas que nos indicaron y cómo se usaron

| Herramienta | Uso |
|---|---|
| Giovanni | Series de lluvia, temperatura del aire y humedad del suelo |
| AppEEARS | Series MODIS por punto |
| Hydrology Time Series | No usado todavía. NLDAS no cubre República Dominicana (~25° N mínimo); GLDAS se tomó de Giovanni |
| NOAA Climate Data Online | Pendiente: validar con una estación GHCN-Daily cercana |
| KNMI Climate Explorer | Pendiente: repetir la tendencia en otra herramienta como segunda opinión |
| Artículo SeaWiFS (NTRS 20090042747) | Precedente de quitar la estacionalidad antes de probar significación |
| CSA RCM, SWOT, tutorial SAR | No usados en el piloto; candidatos para una fase posterior |

## Métodos (referencias de los procedimientos)

- SPI: McKee, Doesken y Kleist (1993), *The relationship of drought frequency and duration to time scales*.
- Mann-Kendall: Mann (1945); Kendall (1975).
- Theil-Sen: Theil (1950); Sen (1968).
- FDR: Benjamini y Hochberg (1995).
- MOD17: guía de usuario de MOD17 C6.1 (Running y Zhao), para la fórmula GPP = ε × FPAR × PAR
  con escalares de VPD y temperatura mínima.

Regla del equipo: **no entra en la entrega ninguna cita que alguien no haya abierto.** Las citas del
informe inicial de investigación que no se pudieron verificar no se usan.
