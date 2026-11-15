# Backend científico de preparación municipal

Implementado el 15 de noviembre de 2026. Alcance de este cierre: ingestión, motor Python, API local, resultados reproducibles y validación científica. No incluye diseño de interfaces ni material de presentación. El motor canónico es `earthmemory/preparacion/motor.py`; cualquier consumidor debe usar sus resultados en vez de mantener otra copia de las reglas.

## Qué resuelve

Construye un expediente por punto representativo de Bonao, Cotuí, Villa Riva y Monte Cristi. Separa lluvia prevista, déficit de precipitación observado mediante reanálisis y contexto provincial histórico NASA/CHIRPS. Devuelve señales, respaldo, contradicciones, exclusiones justificadas y tareas de verificación. Retirar una fuente cambia el expediente sin modificar la lluvia de las demás fuentes.

El expediente es apoyo a preparación municipal. No emite órdenes, no estima probabilidad de inundación y no demuestra daños evitados. Los puntos de consulta no cubren todo el municipio ni representan una cuenca completa.

## Ejecución

Desde la raíz del repositorio, con Python y su biblioteca estándar:

```powershell
# Consulta separada por proveedor/modelo; conserva la respuesta original en caché.
python -m earthmemory.preparacion.paquete
# Reconstruye desde caché, sin consultar proveedores y sin rejuvenecer sus fechas.
python -m earthmemory.preparacion.paquete --sin-red
# Expedientes de los cuatro pilotos; salida JSON con hashes de paquete y motor.
python -m earthmemory.preparacion.evaluar
python -m earthmemory.preparacion.evaluar --sitio villa-riva --sin-fuente GFS --salida results/preparacion/sin_gfs.json
# API local; no inicia ni modifica ninguna interfaz.
python -m earthmemory.preparacion.servidor --port 4178
# Pruebas y escenarios científicos con el paquete real.
python -m unittest discover -s tests -p 'test_preparacion*.py' -v
python scripts/validar_backend_preparacion.py
```

No hay credenciales en el navegador ni claves necesarias para estas consultas públicas. Los originales están en `data/preparacion/` (ignorado por Git); las versiones anteriores del paquete se conservan allí por SHA-256. El paquete normalizado, el manifiesto, la evaluación y los escenarios se guardan en `results/preparacion/`. El JSON normalizado permite usar la API sin conexión externa. `--exportar-web` es una copia opcional explícita del JSON; no se necesita para el backend.

La ingestión reintenta tres veces y usa la caché si falla el proveedor. Mantiene `first_seen_at` y `retrieved_at` originales al usarla. La prueba de caída simula el fallo de red y comprueba que ni las fechas ni los valores se rejuvenecen. Una copia vencida sigue disponible para auditoría, pero el motor la excluye del respaldo actual.

## Contratos y tiempo

Cada `EvidenceRecord` lleva `id`, `source_id`, `kind`, `site_id`, coordenadas `requested`/`returned`, `valid_start`/`valid_end`, `issued_at`, `first_seen_at`, `retrieved_at`, calidad, procedencia y datos. Los registros del proveedor añaden modelo, resolución y hash; una medición local conserva sus datos aportados y su calidad. El hash del paquete identifica los bytes archivados, no certifica su veracidad.

`kind` distingue `forecast`, `reanalysis` y `observation`. `issued_at=null` significa emisión desconocida: no se sustituye por la captura. La captura es un límite conservador de disponibilidad en nuestro sistema, no una reconstrucción de la publicación original del proveedor.

`InvestigationCase` devuelve `rain`, `drought`, `historical_context_sources`, `local`, `supporting`, `contradictions`, `missing`, `excluded`, `dependencies`, `decision_support`, `tasks` y `limits`, con `rule_version` y `decision_at`. Las envolturas CLI/API identifican además el motor cargado y el paquete mediante SHA-256.

Las fechas de entrada necesitan zona explícita. Se normalizan a UTC. El motor excluye captura o recuperación posteriores a la decisión, emisión futura, observaciones cuyo intervalo aún no terminó y registros inválidos. Pronósticos con recuperación de hace más de 12 horas o periodo terminado se excluyen; reanálisis con final del periodo de hace más de ocho días también. Son políticas conservadoras del prototipo, no estándares meteorológicos validados.

Registros repetidos de un modelo no añaden votos. Se usa su captura elegible más reciente. Si dos registros de igual fuente y captura contienen datos diferentes, se excluyen como conflicto. La reproducción anterior a todas las capturas queda sin respaldo meteorológico ni contexto histórico elegible. `derived_context_available=false` avisa además de que el paquete derivado no existía aún: no se puede presentar la reproducción como una decisión efectivamente tomada entonces.

## Lluvia prevista

ECMWF `ecmwf_ifs025` y NOAA GFS `gfs_global` se consultan por separado mediante [Open-Meteo Forecast API](https://open-meteo.com/en/docs), con siete días de precipitación horaria y zona GMT. Cada modelo conserva su celda y resolución devueltas. IFS 0,25° tiene interpolación horaria del proveedor; la resolución horaria del archivo no equivale siempre a una hora nativa del modelo.

Se suman únicamente 24 o 48 horas consecutivas, finitas y no negativas, del mismo modelo y celda. Cada marca horaria representa la hora precedente. Un cero es un dato; un ausente, una discontinuidad o un valor inválido impide ese acumulado. Solo se admiten intervalos completamente posteriores a la decisión y dentro de los siete días siguientes. Como la consulta cubre días de calendario, pueden quedar menos de siete días completos después de la captura; no se rellena el final.

La comparación usa el intervalo de 48 horas con mayor acumulado de cualquiera de los modelos; en empate, el de final más temprano. No se elige el intervalo que maximiza el acuerdo. Ambos modelos se comparan en ese mismo intervalo; se conservan también los máximos individuales de 24 y 48 horas. Dos picos en fechas distintas no constituyen confirmación simultánea. Se usa **más de 100 mm/48 h** como regla exploratoria, sin transferir a estos puntos la validez de una regla operativa o de una cuenca.

El acuerdo es entre celdas representativas de modelos distintos: no hay remallado ni prueba de equivalencia espacial entre ellas. Para contexto, en Villa Riva IFS devuelve 19,25/−70,0 y GFS 19,153923/−69,96094. Esas coordenadas acompañan las cifras. No se interpreta el acuerdo como independencia estadística ni como probabilidad.

## Déficit de precipitación

Se consulta ERA5 explícitamente, con selección de celda `nearest`, mediante [Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api). No se usa una selección automática de modelos de archivo. Se busca el último día válido: en esta captura fue el **9 de noviembre de 2026**, cuyo intervalo termina el día 10 a las 00:00 UTC. No se rellena el retraso con pronóstico.

Para 30 y 90 días se compara el total completo con las mismas ventanas de calendario de 2001–2024, del mismo producto y celda. Para disponer de las ventanas de comienzos de 2001 se descarga desde octubre de 2000. Se requieren al menos 20 años completos. El 29 de febrero se empareja con el 28 en años no bisiestos; esta convención queda registrada.

El motor comprueba fechas, duración, unicidad de años y totales de cada ventana histórica. Recalcula el percentil desde los totales y no confía en un percentil recibido:

`100 × (n(referencia < actual) + 0,5 × n(referencia = actual)) / n`

Percentil ≤20 genera una señal descriptiva de déficit para seguimiento. No equivale a sequía agrícola, escasez medida, impacto ecológico ni probabilidad de daño. Con 24 años la resolución por rango es 4,17 puntos percentiles. Se informa el rango obtenido al retirar cada año y si cambia la clasificación; **no es un intervalo de confianza**, ni cubre la incertidumbre del reanálisis, el clima no estacionario o la elección de referencia. Las ventanas de 30 y 90 días se solapan y no son dos testigos independientes.

### Resultado de la captura validada

| Punto | 30 días (mm) | Percentil | 90 días (mm) | Percentil | Clasificación a 90 días |
|---|---:|---:|---:|---:|---|
| Bonao | 150,1 | 79,17 | 358,6 | 25,00 | No bajo P20 |
| Cotuí | 104,1 | 62,50 | 208,2 | 25,00 | No bajo P20 |
| Villa Riva | 87,3 | 25,00 | 300,6 | 4,17 | Déficit para seguimiento |
| Monte Cristi | 118,1 | 87,50 | 169,2 | 54,17 | No bajo P20 |

Los ocho percentiles usan 24 ventanas completas y mantienen su clasificación al retirar cualquier año. Para Villa Riva a 90 días el rango es P0–P4,35. Los cuatro puntos quedan por debajo de la regla exploratoria de lluvia prevista en esta captura; eso no descarta inundaciones. Los resultados son una instantánea fechada, no información permanentemente actual.

## Dependencias, contexto y medición local

El grafo de familias de insumos se recorre para señalar relaciones aguas arriba y familias compartidas entre fuentes elegibles. IMERG usa ERA5 como auxiliar y ajuste mensual GPCC; CHIRPS y GPCC pueden compartir familias de estaciones, y los modelos/reanálisis asimilan observaciones satelitales. El grafo es cualitativo y no exhaustivo: no demuestra coincidencia de estaciones concretas, ni estima correlaciones de error. La falta de un enlace nunca prueba independencia. Su efecto es reducir la interpretación de corroboración a parcial o no establecida, sin un puntaje numérico inventado.

El paquete conserva las tendencias provinciales existentes de SDII, CDD y PRCPTOT y el backtest histórico corregido del Yuna. Este último permanece en **39→16 episodios sin evento catalogado y 7/8→6/8 detecciones**, sin anticipación estrictamente anterior al inicio catalogado. No se vuelve a utilizar el resultado anterior de 20 episodios ni la atribución GOES retirada. La prioridad de medición se entrega aparte del peligro y la exposición. El backend no vuelve a calcular estas investigaciones ni las convierte en evidencia causal.

Una medición local requiere territorio, inicio/final, milímetros y procedencia. Coordenadas instrumentales son opcionales; si faltan, se marca ubicación instrumental no especificada en vez de fingir una estación en el centro municipal. Se rechazan fechas sin zona, intervalos futuros, negativos, valores no finitos y coordenadas inválidas. Una aportación válida conserva `unverified`; un ejemplo conserva `synthetic`. Puede añadir una tarea de verificación, pero no confirmar un pronóstico. Un ejemplo sintético no satisface la falta de una medición real.

## API para consumidores

El servidor se limita a `127.0.0.1`; es un servicio local de prototipo, sin autenticación ni despliegue multiusuario. No envía mediciones a proveedores externos.

| Ruta | Contrato |
|---|---|
| `GET /health` | Estado del proceso y versión de reglas; no certifica frescura de datos. |
| `GET /api/preparacion` | Paquete fechado y hash; devuelve 503 si no está disponible o su versión es inválida. |
| `POST /api/investigacion` | Recalcula un expediente y devuelve registros, grafo, hashes, exclusiones y tareas. |

Ejemplo de petición JSON:

```json
{"site_id":"villa-riva","disabled_sources":["GFS"]}
```

`decision_at` es opcional y, al omitirse, toma la captura del servidor. Para añadir una medición se utiliza `measurements`:

```json
{
  "site_id":"villa-riva",
  "measurements":[{
    "site_id":"villa-riva",
    "start":"2026-11-14T00:00:00Z",
    "end":"2026-11-15T00:00:00Z",
    "mm":0,
    "source":"Ejemplo de prueba, no una estación real",
    "synthetic":true
  }]
}
```

El servidor asigna la captura y el identificador; ignora cualquier intento de retrofechar `first_seen_at`. La respuesta incluye `measurement_ids`. Pueden reenviarse para recalcular el mismo caso con otra decisión o retirada de fuentes conservando la captura original. Un identificador ajeno al territorio o desconocido se rechaza. El registro local es **en memoria** y se pierde al reiniciar; para archivo reproducible deben conservarse los JSON de entrada/salida. No se presenta como una base de observaciones permanente.

Se limita el cuerpo a 1 MB y cada lote a 100 mediciones nuevas; se exige `application/json`. Un lote inválido se rechaza completo. Los errores de datos devuelven 400, territorio desconocido 404, tamaño inadmisible 413 y formato 415. CORS está desactivado por defecto; un consumidor local puede habilitar su origen exacto con `--allow-origin http://127.0.0.1:5173`.

## Validación y lo que sigue abierto

**24 pruebas automatizadas aprobadas**, sin proveedores externos: calendario, umbrales, ausentes/cero, continuidad horaria, ventanas simultáneas, selección sin maximizar acuerdo, disponibilidad temporal, vencimiento, coordenadas, duplicados, conflictos, dependencias, sensibilidad de referencia, mediciones y contrato HTTP. Incluyen una caída simulada de proveedor y cuatro controles de conexión territorial y decisiones.

**14 comprobaciones aprobadas con el paquete real**, archivadas en `results/preparacion/VALIDACION_CIENTIFICA.json`: cuatro pilotos, ingestión sin errores, referencias verificadas, percentiles recalculados, retirada de GFS/ERA5, reproducción anterior a captura, dependencias e igualdad entre API y motor puro. La validación levanta un servidor efímero y lo cierra; no necesita acceso externo. Al repetirla con una captura vencida, los controles de cobertura pueden fallar deliberadamente: hay que actualizar el paquete, no relajar las reglas.

Esto valida el funcionamiento y coherencia del prototipo, no la exactitud de sus pronósticos. Quedan pendientes una evaluación prospectiva con archivos de corridas realmente capturados antes de las decisiones, verificación territorial/hidrológica, calibración de reglas con responsables locales, validación de mediciones y evaluación de costes de actuar o esperar. Un hindcast o una hora de inicialización no demuestra disponibilidad histórica: véase [Single Runs API](https://open-meteo.com/en/docs/single-runs-api).

## Conexión territorial y decisión (reglas 1.1)

`decision_support` conecta señales con preguntas de preparación, no con órdenes automáticas. Conserva por separado la temporada climatológica atlántica (junio–noviembre), el estado ciclónico actual (`not_ingested`) y el peligro de lluvia previsto. Estar en temporada no prueba un ciclón activo; estar fuera no suprime una señal de lluvia. Viento, marejada, deslizamientos y drenaje urbano se identifican como peligros no modelados.

Para los tres puntos del Yuna se explicitan aportes de aguas arriba y del Camú, y la información faltante de entradas/salidas/almacenamiento de Hatillo. La presa no regula toda la cuenca. No hay pronóstico de caudal ni tiempos de propagación. Monte Cristi no hereda esas conexiones del Yuna. El conocimiento territorial es contexto actual y se etiqueta como tal; no se presenta como información disponible en una reproducción operacional histórica.

Una señal de lluvia en cualquiera de los modelos genera la pregunta de qué preparativos verificar, aunque falte confirmación. Un déficit genera la pregunta de disponibilidad de agua y demanda, no una recomendación de riego. Ambas preguntas pueden coexistir. Los datos de comunidades, rutas, vulnerabilidad y estado real de agua siguen faltando: no se inventa exposición. La aceptación del expediente por responsables municipales y su beneficio operacional siguen sin validar. El razonamiento territorial y la ruta de evaluación se detallan en `SOLUCION_LIMITES_Y_PREPARACION.md`.
