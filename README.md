# PHANTOM

**Se ve verde, pero ¿ya funciona?**

Herramienta en línea: **https://earth-system-detective.vercel.app**

Stellar Horizons · NASA Space Apps 2026 · Santiago, República Dominicana

Después de una sequía, ¿la vegetación vuelve a verse normal antes de volver a funcionar normal?
PHANTOM mide esa diferencia en días (Δt) con datos de NASA, la prueba contra varios supuestos y
dice cuándo el resultado se sostiene y cuándo no.

## Estado

- Datos climáticos 2001–2024 (Giovanni): listos y validados.
- Catálogo de sequías (SPI-3, SPI-6, humedad del suelo): listo. Ver `RESULTS.md`.
- Datos MODIS (AppEEARS): pedido enviado y en proceso. **Todavía no hay ningún resultado sobre la brecha.**

## Reproducir

Requiere [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run pytest
uv run python -m phantom.pipeline
```

Cuando AppEEARS termine:
1. Descargar los CSV del pedido `phantom-rd-puntos-v2` desde https://appeears.earthdatacloud.nasa.gov/explore
2. Ponerlos en `data/appeears/`
3. Volver a correr `uv run python -m phantom.pipeline`

### Con Docker

La imagen corre las 22 pruebas durante el build: si alguna falla, no se construye.
La salida es idéntica byte a byte a la corrida local (comprobado en CSV y JSON; `RESULTS.md`
solo cambia en la fecha de generación).

Desde la carpeta del proyecto, igual en cmd, PowerShell o bash:

```bash
docker compose build
```

```bash
docker compose run --rm phantom
```

Queda todo en `out/`: `results/`, `figures/` y `RESULTS.md`. Si `data/appeears/` ya tiene los CSV
de AppEEARS, el mismo comando procesa también MODIS (la carpeta se monta en el contenedor).

Si `docker` responde "being used by another process", Docker Desktop todavía está arrancando:
espera unos segundos y repite.

El pipeline encuentra solo los archivos `*-MOD13Q1-061-results.csv`, `*-MOD11A2-061-results.csv`,
`*-MOD17A2HGF-061-results.csv` y `*-MCD12Q1-061-results.csv`.

## Salidas

| Archivo | Qué es |
|---|---|
| `RESULTS.md` | Resumen generado en cada corrida |
| `results/giovanni_validacion.json` | Fechas, faltantes y origen de cada serie |
| `results/sequias_catalogo.csv` | Sequías por tres criterios y si coinciden lluvia y suelo |
| `results/eventos_principales.csv` | Sequías usadas para medir recuperaciones |
| `results/estado_modis.json` | Estado de los datos MODIS y registro de calidad |
| `results/recuperacion_eventos.csv` | Δt por punto, evento y señal (cuando haya MODIS) |
| `results/sensibilidad.csv` | Las 18 combinaciones por evento |
| `results/tendencias.csv` | Theil-Sen, Mann-Kendall, autocorrelación y q (FDR) |
| `figures/` | Figuras hechas con datos reales |

## Documentos

- `METHODOLOGY.md`: el método completo y qué se puede afirmar.
- `FUENTES.md`: fuentes, consultas exactas y fechas.
- `appeears/METODO.md`: el pedido de AppEEARS, los puntos y su revisión en imagen.
- `data/giovanni/SEQUIAS.md`: cómo se sacaron las series de Giovanni.
- `INVESTIGACION.md`: el razonamiento inicial (borrador).

## Estructura

```
phantom/      código del pipeline
tests/        pruebas con datos sintéticos (marcados como tales)
data/         datos originales; no se sobrescriben
results/      salidas generadas
figures/      figuras generadas
```

## Herramienta web: Detective del Sistema Tierra

`web/` es un sitio estático (Vite + TypeScript) que lee los JSON que genera el pipeline en `web/public/data/`.
No calcula estadística: muestra lo que calculó `phantom/trends.py`.

```bash
uv run python -m phantom.pipeline
```

```bash
cd web && npm install && npm run build
```

El sitio queda en `web/dist/`. Para verlo en local: `npm run preview` (puerto 4180).
`?prueba=1` carga un archivo SINTÉTICO que solo existe en la máquina de desarrollo y lo marca con un aviso rojo.

Publicación: `cd web && npx vercel@latest deploy --prod` (proyecto de Vercel `earth-system-detective`).
