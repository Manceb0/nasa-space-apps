# Formato que espera la web para datos en rejilla (para el chat de datos)

La web pinta campos continuos sobre el mapa, de modo que no se vean "cuadros". Para hacerlo sin inventar
nada, necesita que cada ráster llegue con su resolución real, su procedencia y su cita.
Ubicación: `web/public/data/grid/<variable>_<fuente>.json`. Si hace falta, un archivo por año para que pese menos.

```json
{
  "variable": "spi3",
  "nombre": "SPI-3 (lluvia de 3 meses frente a lo normal)",
  "unidad": "z",
  "fuente": "CHIRPS v2.0, UCSB Climate Hazards Center",
  "cita": "Funk et al. 2015, Scientific Data 2:150066, doi:10.1038/sdata.2015.66",
  "url": "https://www.chc.ucsb.edu/data/chirps",
  "resolucion_grados": 0.05,
  "bbox": [-72.1, 17.4, -68.3, 20.0],
  "lats": [19.975, 19.925, "..."],
  "lons": [-72.075, -72.025, "..."],
  "meses": ["2001-01", "2001-02", "..."],
  "valores": [[[1.2, null, "..."]]],
  "mascara_tierra": [[true, false, "..."]],
  "metodo": "SPI gamma por celda, referencia 2001–2024"
}
```

- `valores[t][fila][columna]`: las filas siguen el orden de `lats`. Usa `null` para mar o para celdas sin dato; nunca rellenes huecos.
- `lats` y `lons` son los **centros** de las celdas. La web dibuja cada celda en su tamaño real cuando se pide la vista exacta.
- Redondea los números a 2 decimales para que el JSON pese menos.
- Fuentes finas que ya se probaron: CHIRPS se puede bajar recortado a RD desde el IRI Data Library, sin cuenta
  (unos 190 KB por año a 0,05°, comprobado el 2026-11-14). La URL de ejemplo es
  `iridl.ldeo.columbia.edu/SOURCES/.UCSB/.CHIRPS/.v2p0/.monthly/.global/.precipitation/X/(-72.1)/(-68.3)/RANGEEDGES/Y/(17.4)/(20.0)/RANGEEDGES/data.nc`.
  MODIS NDVI a 250 m se obtiene con el pedido de área de AppEEARS.

Cómo lo pinta la web: un campo suave (interpolación bilineal solo para dibujar), isolíneas y la opción
"ver píxeles reales", con la resolución nativa y la cita en la leyenda. No se inventa ningún valor entre celdas.
