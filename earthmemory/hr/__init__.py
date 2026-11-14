"""Earth Memory · ALTA RESOLUCIÓN y UMBRALES CRÍTICOS (República Dominicana, 2001-2024).

Subpaquete independiente del motor nacional (earthmemory/*.py): no modifica nada de él.

- common:      rutas, manifiesto (URL + SHA-256), HTTP con reintentos, rejilla común 0.05°.
- sources:     catálogo de fuentes (autores, año, DOI/URL, licencia, versión, resolución nativa).
- download:    descargas públicas sin login (CHIRPS, TerraClimate, SoilGrids, Copernicus DEM, WorldCover,
               geoBoundaries) y, si hay token de Earthdata, SMAP L4 (NASA).
- harmonise:   todo a la rejilla CHIRPS 0.05° sobre tierra dominicana (media ponderada por área para
               continuos, fracciones de clase para categóricos); las versiones nativas se conservan.
- thresholds:  umbral de humedad antecedente donde cambia la respuesta suelo-lluvia (regresión segmentada,
               prueba sup-F con bootstrap por bloques, IC bootstrap del umbral, FDR).
- changepoints: meses de quiebre (Pettitt con p por bootstrap por bloques circulares, FDR).
- drivers:     qué factores estáticos acompañan a los umbrales (ridge + validación cruzada por bloques).
- pair:        el par "misma lluvia, distinta respuesta" a alta resolución, con sustitutos.
- figures, report, notebook, run.

Todo es ASOCIACIÓN: ningún resultado se presenta como causa.
"""
