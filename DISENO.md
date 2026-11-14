# Diseño de la herramienta (taste-skill, pantalla de app)

## Dirección

- **Tipo de trabajo:** pantalla de app (se trabaja en ella), no página de lectura. Se siguió `references/app-screens.md`.
- **Estilo repartido:** `true-black-flat` (oscuro), semilla 1047065985, con la tipografía conservada: Poppins, por pedido del usuario.
  - Se descartó `data-terminal`: está pensado para monitoreo de muchas horas, y esto es una exploración de un rato.
  - Sin redibujos.
- **La cara del producto:**
  - un solo tono de datos, el ámbar de la sequía y el sol (#f2b33d);
  - sobre negro frío neutro (#0c0d0f), con tarjetas que se separan solo por luminosidad (#15171a, #23262a).
  - El ámbar nunca va en botones ni navegación: lo seleccionado se invierte a blanco.
- **Elemento propio:**
  - en Investigar, el **mapa de ventanas** (cada intervalo de 10 años o más, con su conclusión);
  - en Expedientes, la **doble línea de recuperación** (verdor contra función, con umbral, fechas y Δt).
- **Pregunta de cada pantalla:**
  - Investigar: "¿cambió esta variable aquí, y es significativo?".
  - Expedientes: "¿el bosque se ve recuperado antes de funcionar?".
- **Rejilla:** columna de 1160 px, 6 columnas con un solo hueco de 14 px (6 × 181,67 + 5 × 14 = 1160).

## Visualizaciones del atlas (especificación del equipo)

| Visualización | Estado | Datos |
|---|---|---|
| Doble línea de recuperación | Implementada | Series z reales por punto (`results/zseries.json`) |
| Mapa de calor espacio-tiempo | Implementado | Anomalía mensual estandarizada de NDVI, LST y GPP, 5 lugares × 288 meses |
| Constelación de impactos | Implementada | Sequía × lugar con ambas recuperaciones; tamaño = severidad; relleno = robusto |
| Distribución de días hasta recuperarse | Implementada | Verdor, GPP y dosel; mediana marcada |
| Mapa de tendencias (significancia) | Implementado **por puntos** | 5 lugares × 3 variables; relleno = p corregido < 0,05; tabla con q (BH sobre 15 pruebas) |
| Mapa de impacto por superficie | **Pendiente**, con estado vacío honesto | Pedido de área AppEEARS `eec5627a…`; sin píxeles no se dibuja ninguna zona |
| Challenge the Evidence | Implementado, en la ficha "Este caso" | 18 combinaciones precalculadas por `phantom/recovery.py` |

## Medición (inspect.mjs --app, 1440 / 768 / 390)

| Pantalla | Antes | Después |
|---|---|---|
| Investigar | 3 FAIL (h1 de 68 px en 3 líneas), 5 WARN | **0 FAIL, 0 WARN** |
| Expedientes | — | **0 FAIL, 2 WARN**: bloques bajo el pliegue (es un expediente largo) y una caja vacía del mapa por área (es el estado vacío) |
| Cómo funciona | — | **0 FAIL, 0 WARN** |

Lint: **0 FAIL**. Los avisos que quedan:
- "robust", que es el término estadístico;
- Poppins, que es la letra del usuario;
- las rayas largas, usadas como marca de valor faltante.

Los divisores de 1 px dentro de los contenedores divididos de cifras llevan `taste-skill-ignore` (regla de app §13).

## Crítica

```
ROUND 1 (antes)
Seen in one second: un titular de landing de 68 px sobre fondo azul pizarra; no se ve qué hacer.
Idea (one sentence): predecir y luego comprobar con datos de la NASA.
Live thing: elegir variable y zona, predecir, revelar, mover el intervalo.
Layout words by section: título=landing / elegir=dos columnas / predicción=bloque / evidencia=pila de texto / ventanas=matriz.
Scores: design 6 · usability 6 · creativity 7 · content 7 → overall 6.5.
Caps applied: titular de más de dos líneas.
Top three problems:
1. El h1 de 68 px en 3 líneas convierte la herramienta en una landing (desktop-fold). Arreglo: título de 28 px.
2. Fondo pizarra y ámbar en botones y selección (todas las capturas). Arreglo: negro neutro; ámbar solo en datos; selección en blanco.
3. Expedientes sin las visualizaciones que pidió el equipo. Arreglo: doble línea, mapa de calor, constelación, distribución y mapa de tendencias con datos reales.

ROUND 2 (después)
Seen in one second: una herramienta oscura y ordenada; en Expedientes, el hallazgo arriba con 4 cifras.
Idea (one sentence): el bosque puede verse verde antes de funcionar, y la herramienta comprueba si pasa.
Live thing: la doble línea por lugar y sequía, que cambia entre GPP y hojas contra aire.
Layout words by section: hallazgo=cifras divididas / doble línea=4+2 / calor=ancho completo / constelación+distribución=3+3 / mapa+tabla=4+2 / área+colisión=3+3 / método=dos columnas.
Scores: design 8 · usability 8 · creativity 8 · content 8.5 → overall 8.1.
Caps applied: ninguno.
Top three problems:
1. En el teléfono, el mapa de calor de 288 meses queda muy fino (mobile-page). Arreglo pendiente: en el teléfono, mostrar solo los últimos 10 años o permitir desplazamiento horizontal.
2. La distribución tiene pocos puntos por fila y deja aire (desktop-page-01). Aceptable: son los datos reales.
3. El mapa de tendencias amontona los 3 puntos de Montecristi a escala de isla. Arreglo pendiente: un botón para acercar a Montecristi.
```
