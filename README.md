# Stellar Horizons · Evidence Intelligence

NASA Space Apps 2026 · reto **«Be An Earth System Trend Detective!»** · Santiago, República Dominicana.
Cierre de la entrega: **domingo 15 de noviembre de 2026, 23:59 (hora de RD)**. Meta interna: 20:00.

> **Pregunta guía:** ¿qué conclusión aparentemente correcta sobre sequías e inundaciones en República
> Dominicana podría resultar equivocada cuando incorporamos la información que faltaba?
>
> **Regla de lenguaje:** nunca decimos que «el satélite miente». Distintas fuentes científicas pueden
> ofrecer interpretaciones contradictorias del mismo territorio, y nuestro sistema investiga por qué.

Este README es la guía para el líder y el equipo: qué hay, qué leer primero y qué falta.

## La historia en tres piezas

1. **Mapa nacional de tendencias (P0, obligatorio por el reto).** Variable, región, serie, ritmo de cambio y
   significancia para toda la RD, 2001-2024, con IMERG (NASA) y CHIRPS. Resultado: casi ninguna tendencia es
   robusta cuando se exige que las dos fuentes estén de acuerdo; la lluvia extrema no es detectable en 24 años;
   y las fuentes discrepan en la intensidad de la lluvia diaria en 160 de 442 celdas.
2. **Auditoría de confianza (el momento central).** Cuatro productos de lluvia que parecen independientes
   comparten pluviómetros. Solo en 275 de 3.111 provincia-meses con alarma de sequía coinciden los cuatro; en el
   39 % otro producto dice «normal o húmedo». El 67 % de los disparos de inundación (> 100 mm en 48 h) de un
   producto no los confirma el otro.
3. **Caso Yuna.** Lluvia y memoria del suelo arriba → presa de Hatillo → inundación de arrozales abajo, contrastado
   con agua observada por MODIS (MCDWD): confirma 12 de 15 eventos; 228 km² inundados al menos una vez y 50 km²
   en tres o más eventos.

## Qué leer primero (unos 20 minutos)

| Orden | Archivo | Para qué |
|---|---|---|
| 1 | `reports_nacional/AUDITORIA_CONFIANZA.md` (sección «En corto») | El hallazgo central |
| 2 | `reports_nacional/TENDENCIAS_P0.md` (sección «Resumen») | Lo que pide el reto |
| 3 | `reports_nacional/CASO_YUNA.md` | El caso concreto |
| 4 | `figures/galeria/GALERIA.md` y `figures/galeria/dark/` | Las figuras candidatas a diapositivas |
| 5 | `reports_nacional/TESTIGOS_E_HIPOTESIS.md` | Humedad del suelo, SMAP y lo que no se pudo probar |

Para leer sin instalar nada: los cuadernos ya ejecutados en `reports_nacional/notebooks_html/` (abrir en el
navegador). Los mismos cuadernos editables están en `notebooks/`.

Todos los números de los informes los genera el código desde los datos; ninguno está escrito a mano.

## Mapa del repositorio

| Carpeta | Contenido |
|---|---|
| `earthmemory/` | Motor de análisis: `tendencias/`, `auditoria/`, `yuna/`, `testigos/`, `galeria/` |
| `results/` | Salidas en CSV y JSON; `*/web/` son los datos que lee la web |
| `figures/` | Figuras (PNG + PDF + JSON de procedencia). `figures/galeria/` = piezas para el pitch |
| `reports_nacional/` | Informes en español, generados desde la corrida |
| `notebooks/` | Cuadernos 01-09, uno por etapa |
| `tests/` | Pruebas del motor (corren en el build de Docker) |
| `web/` | La aplicación (Vite + TypeScript, MapLibre/Leaflet, Observable Plot) |
| `phantom/`, `appeears/` | Primera versión del proyecto (PHANTOM, recuperación tras sequía); se conserva |
| `data/` | Solo manifiestos; los datos crudos no se suben (ver «Reproducir») |

Otros documentos: `METHODOLOGY.md` (método de la primera versión), `FUENTES.md` (fuentes y consultas),
`ESTRATEGIA.md` (auditoría del brief), `DISENO.md` y `HANDOFF_PANTALLAS.md` (diseño de la web).

## Ver la aplicación

```bash
cd web
npm install
npm run build
npm run preview
```

Abre http://localhost:4180. Rutas: `#tendencias` (P0), `#auditoria`, `#expedientes`, `#ribbon`, `#investigar`,
`#metodo`. No hay ninguna versión publicada en internet.

## Reproducir el análisis

Todo el cómputo corre en Docker; la imagen ejecuta las pruebas durante el build y no se construye si alguna falla.

```bash
docker compose build
```

```bash
docker compose run --rm tendencias
```

Servicios: `nacional`, `alta_resolucion`, `tendencias`, `auditoria`, `yuna`, `testigos`, `galeria` (y `phantom`
para la primera versión). Los datos crudos (IMERG, CHIRPS, GLDAS, SMAP, MODIS, etc.) no están en el repositorio
por tamaño: cada `data/*/MANIFEST.json` dice qué archivo, de dónde y con qué consulta. Las descargas de NASA
necesitan una cuenta de Earthdata; el token va en `.secrets/earthdata_token`, que nunca se sube.

## Fuentes de datos

NASA: IMERG V07 (GPM), GLDAS-2.1, SMAP L3 y L4, MERRA-2 / POWER, MODIS MCDWD (inundación), MODIS vía AppEEARS.
Otras: CHIRPS v2.0 (UCSB/CHC), TerraClimate, estaciones GHCN-D y GSOD (NOAA), JRC Global Surface Water,
Hansen Global Forest Change, HydroBASINS/HydroRIVERS, Copernicus GLO-90. Detalle y enlaces en `FUENTES.md` y en
la sección de referencias de cada informe.

## Estado y pendientes (15 nov)

Hecho: P0, auditoría, caso Yuna, testigos, galería de figuras y la web con Tendencias y Auditoría.

Pendiente:
- [ ] Pitch para el jurado: máximo 7 diapositivas o un video de 30 s, **en inglés**.
- [ ] Declarar el uso de IA en la entrega (código y textos asistidos por IA; las imágenes generadas con IA
      llevarían marca de agua; la idea es del equipo).
- [ ] Actualizar la página del equipo en Space Apps y pulsar **«Submit for Judging»** antes de las 23:59.
- [ ] Hacer público este repositorio antes del cierre (Space Apps exige un enlace público).
- [x] Pruebas tropicales corridas (`reports_nacional/PRUEBAS_TROPICALES.md`). Con una revisión independiente
      (`REVISION_JANE.md`) y un tercer testigo (ERA5), la conclusión que se sostiene es esta: IMERG cuenta cada vez
      menos días de lluvia que los pluviómetros, CHIRPS y ERA5, así que sus tendencias de intensidad y de rachas secas
      no se pueden confirmar. **No** está demostrado un «escalón en octubre de 2013», y el «82 %» del recálculo es
      una sensibilidad a un ajuste, no un mecanismo.
- [ ] Pendiente de esas pruebas:
  - Comparar tendencia gradual, escalón y ambos, con incertidumbre de fecha y magnitud.
  - Repetir con ERA5 en todas las celdas, no solo en 6 puntos.
  - Conseguir estaciones de INDOMET.
  - Usar vientos medidos en vez del alisio fijo.
- [ ] Revisar la anomalía de MERRA-2 después de 2016 (auditoría, fig04c) y la pérdida de bosque de 2005 (Hansen)
      antes de mostrarlas.

## Reglas del equipo

- No inventar datos; lo sintético o de prototipo va marcado.
- Nada de gráficas de barras ni de pastel en las piezas del pitch: mapas, franjas y series con la estructura visible.
- No se publica ni se despliega nada sin aprobación del equipo.
- Ningún secreto en el repositorio (`.secrets/` está en `.gitignore`).
