# Solución científica: investigar para preparar el territorio

Revisión del 15-nov-2026. Alcance: ciencia, datos y backend; no diseño de interfaces. Se contrastaron los dos mensajes de objetivo/límites con los resultados actuales, dos búsquedas SciSpace, extracción de métodos/limitaciones y documentación primaria de NASA, ECMWF y NCAR. Las referencias están archivadas en `references/preparacion_municipal/`, con URL, fecha, HTTP y SHA-256 en su manifiesto.

## Decisión

La solución es un **expediente municipal de preparación**: conecta vigilancia de lluvia prevista, seguimiento de déficit y evidencia histórica; explica qué requiere atención, qué lo respalda y qué falta comprobar. Investigar la confiabilidad de los datos protege la decisión, pero no sustituye al servicio que necesita el municipio. No hace falta resolver la causa de la discrepancia IMERG–CHIRPS para entregar esta capacidad.

El backend está implementado en `earthmemory/preparacion/`, con API local y expedientes para puntos representativos de Bonao, Cotuí, Villa Riva y Monte Cristi. Contratos, ejecución, método y límites: `BACKEND_PREPARACION.md`. Este informe añade la solución a los límites del planteamiento, sin atribuir capacidad operacional inexistente.

## Qué cambia en los dos mensajes

| Afirmación inicial | Evidencia actual | Formulación defendible |
|---|---|---|
| «Lo que más cambió no fue la lluvia, sino cómo IMERG cuenta días» | La discrepancia entre productos está medida; no hay una verdad territorial suficientemente observada para repartir sus causas. | Hay una posible inhomogeneidad en la frecuencia estimada de días húmedos; no está resuelto cuánto es clima, muestreo, ajuste o referencia. |
| «Después de 2018 unos −5 pp, p<0,001» | El nuevo análisis en 15 celdas MERRA-2 da mediana IMERG −5,10 pp y CHIRPS +0,04 pp. En ese mismo resumen IMERG solo tiene p=0,017; otros contrastes tienen p<0,001. | Citar estimador, soporte espacial, corte y contraste juntos. No adjuntar a la mediana el p de otra prueba. |
| «CHIRPS no muestra ese cambio» | No detectar un cambio depende de la prueba, potencia, escala y referencia. | No se detectó el mismo cambio con los contrastes utilizados; no prueba estabilidad ni exactitud. |
| «Testigos independientes» | IMERG usa ERA5; las familias de estaciones de CHIRPS/GPCC pueden solaparse. Las estaciones disponibles tampoco equivalen a validación territorial. | Fuentes de contraste con dependencias explícitas; corroboración parcial y localizada. |
| «Solo existen cuatro estaciones públicas» | La prueba concreta usa cuatro GHCN-Daily; el código también consulta GSOD y documenta circularidad y calidad. | Cuatro pluviómetros en esta comparación. No es un inventario exhaustivo de toda la observación pública dominicana. El acceso a INDOMET requiere comprobación específica, no una negación universal. |
| «GOES-16 es la causa más probable» | `ESTADO_CONCLUSIONES.md`, fila 8: sin resolver. La resta de contadores diarios era inválida. | GOES es una candidata temporal, junto con calibración, microondas, referencia y variabilidad real. No existe una clasificación de probabilidad causal. |
| «Solo puede probarse descargando archivos completos de media hora» | NASA documenta el producto de media hora con subsetting y OPeNDAP. | Los campos conjuntos de media hora son necesarios para este contraste; una extracción espacial/de variables puede reducir volumen. No se ha demostrado todavía el tiempo de acceso ni que un piloto atribuya causalidad. |
| «Los pronósticos originales solo existen desde 2024» | TIGGE documentado desde octubre de 2006; NCAR GFS 0,25° desde enero de 2015. | Puede ser un límite del proveedor/configuración ya probados, no de todos los archivos. Hay candidatos para ampliar la evaluación. |

El dato de −5,1 pp es la mediana sobre 15 soportes espaciales de comparación, no una nueva estimación de media nacional ponderada por superficie. `results/tropical/merra2/resumen.json` permite comprobarlo. MERRA-2 cambió fuertemente en esta prueba y fue descartado como testigo: añadir productos no garantiza añadir evidencia fiable.

## Solución que ya funciona

1. **Vigilancia:** obtener ECMWF y GFS por separado, conservar sus celdas reales y comparar acumulados completos de 24/48 horas. La regla >100 mm/48 h es exploratoria. Un acuerdo es un acuerdo entre modelos, no probabilidad de inundación ni dos votos independientes.
2. **Seguimiento de déficit:** ERA5 reciente frente a ventanas de calendario de 30/90 días del mismo producto/celda, referencia 2001–2024. Se exige al menos 20 años completos; el paquete actual tiene 24. P≤20 requiere seguimiento del déficit de precipitación, no declara sequía agrícola ni daños.
3. **Planificación:** incorporar tendencias provinciales NASA/CHIRPS y su sensibilidad; separar la prioridad de instalar o verificar medición del peligro y de la exposición.
4. **Verificación:** devolver tareas concretas: consultar el boletín oficial, comprobar el intervalo previsto y una medición local, resolver diferencias entre modelos y consultar disponibilidad real de agua. Una aportación local se conserva sin verificar, con ubicación y periodo; un dato sintético nunca pasa por observación real.
5. **Trazabilidad:** cada expediente registra versiones, hashes, coordenadas, fechas y exclusiones. Se puede retirar una fuente y reproducir el efecto sobre el respaldo. Una captura posterior no entra en una decisión anterior.

En la captura del 15-nov, Villa Riva tiene 300,6 mm/90 días y P4,17, estable en clasificación al retirar cualquiera de los 24 años. Los otros puntos no quedan bajo P20 y ninguno supera la regla de lluvia prevista. Son resultados fechados. La validación del paquete comprueba coherencia y contratos, no exactitud predictiva. El resultado histórico del Yuna permanece 39→16 episodios sin evento catalogado y 7/8→6/8 detecciones; no se presenta como mejora validada de alerta temprana.

## Cómo ampliar la evaluación sin confundir archivo con anticipación

Se ejecutó `python scripts/auditar_cobertura_pronosticos.py`. Su salida, `results/preparacion/COBERTURA_ARCHIVOS_PRONOSTICO.json`, cruza el catálogo de prueba con dos comienzos documentados de archivo:

- [NCAR GFS 0,25°](https://gdex.ucar.edu/datasets/d084001/): inicio 15-ene-2015; ocho de ocho eventos son posteriores.
- [ECMWF TIGGE](https://www.ecmwf.int/en/forecasts/datasets/tigge-global-medium-range-ensemble-forecasts-multiple-nwp-centres-2006): inicio oct-2006; ocho de ocho eventos son posteriores.

**Se recuperaron cero corridas en esta auditoría y se validaron cero anticipaciones nuevas.** El archivo documentado no garantiza continuidad, variables, descarga autorizada ni disponibilidad local en cada evento. Son fuentes distintas de la pareja actual de modelos de Open-Meteo; el resultado de una no se transferirá a otra.

La siguiente evaluación debe seguir estos pasos, antes de presentar cifras de capacidad preventiva:

1. Comprobar una corrida anterior a un evento y otro periodo sin evento: formato, precipitación acumulada/incremental, unidades, celda, paso temporal, miembros y hora de inicialización. Un piloto de acceso no demuestra habilidad.
2. Mantener una tabla por corrida con inicialización, publicación conocida/documentada, recuperación actual, horizonte y versión. Si la publicación histórica no se conoce, declararla desconocida. La recuperación de hoy no se retrofecha. No se puede reutilizar sin más el filtro de primera captura del motor actual para simular que este sistema ya existía entonces.
3. Congelar regla, intervalos de comparación y partición temporal antes de consultar los resultados de prueba. Recorrer también periodos sin evento, no descargar solo tormentas exitosas. Separar modelos y cambios de versión; no sustituir pronósticos originales por hindcasts.
4. Obtener horas de inicio e incertidumbre del catálogo. Con fechas solamente, distinguir «fecha anterior» de horas de anticipación operacional; si se desconoce la zona horaria no asignarle UTC por conveniencia.
5. Evaluar detecciones, omisiones, episodios sin evento catalogado, anticipación y coste de confirmación frente a la regla de referencia. Ocho eventos producen incertidumbre alta; el catálogo de prensa no demuestra que toda señal no emparejada sea falsa. Reportar intervalos y no seleccionar umbrales mirando la prueba.

Si esta vía no cabe en el cierre, se entrega como ruta verificada de investigación, no como una imposibilidad de los datos. El prototipo municipal funciona con la captura actual y puede empezar a guardar paquetes prospectivos mediante su comando de ingestión; esta revisión no programa una automatización ni afirma un servicio continuo.

## Cómo investigar GOES sin bloquear el producto

[NASA documenta acceso de media hora y subsetting](https://gpm.nasa.gov/node/3328). Eso permite plantear un piloto acotado antes de descargar todo 2016–2019. El tamaño geográfico reducido no elimina la cantidad de archivos ni el coste de solicitudes: cuatro años contienen 70.128 intervalos de media hora. Reducir variables y territorio puede reducir bytes, no garantiza terminar antes del cierre.

La prueba debe conservar, en los mismos instantes, lluvia calibrada/no calibrada, influencia IR y fuente/tiempo de microondas según el esquema real de V07. Hay que verificar nombres, máscaras y unidades antes de programarla; no reutilizar nombres de V06 sin comprobar. Se comparan periodos con estaciones del año equivalentes, disponibilidad de sensores y umbrales previamente fijados. Si el piloto se selecciona por conveniencia, es diagnóstico de factibilidad, no atribución representativa nacional.

Primero se comprueba si el ajuste mensual mueve valores a través del umbral de día húmedo. Después se estudia la evolución de las vías IR/microondas en muestras comparables, sin restar contadores de productos diferentes. Ningún resultado por sí solo elimina meteorología real, cambio de referencia ni selección de muestras. No se modifica el estado «GOES sin resolver» con esta revisión.

## Qué aportó SciSpace y qué no

Se archivaron las dos búsquedas y las extracciones en `references/preparacion_municipal/SCISPACE.json`. Son ayudas de descubrimiento, no observaciones nuevas en RD.

- [Zhu et al. (2024)](https://scispace.com/papers/evaluation-of-imerg-climate-trends-over-land-in-the-trmm-and-11rq92jiqz1z): evalúa tendencias de precipitación anual en **V06**, emparejamiento espacial y eras TRMM/GPM. Justifica comprobar homogeneidad y escala; también encuentra capacidad útil de IMERG. No prueba un fallo de V07 en 2018 ni autoriza a declarar inválido todo IMERG. DOI: 10.1088/1748-9326/ad984e.
- [Talchabhadel et al. (2022)](https://scispace.com/papers/evaluation-of-the-spatiotemporal-distribution-of-lgazyh0a): compara cuatro componentes/productos e índices en Nepal. Motiva analizar frecuencia, intensidad y componentes por separado. Sus errores regionales no se transfieren a RD. DOI: 10.3390/rs14235954.
- Ficchì, Fayaz Mir y Castelletti, [EGU25-17698](https://meetingorganizer.copernicus.org/EGU25/EGU25-17698.html): plantea valorar pronósticos con métricas relevantes para acciones, no solo ajuste estadístico. **Fuente primaria verificada: resumen de congreso de 2025.** SciSpace lo etiquetó como artículo; no adoptamos esa clasificación ni extrapolamos su habilidad de África austral al Yuna. La conexión útil es metodológica, no una justificación para entrenar una LSTM con ocho eventos.

## Conectar el contexto con una decisión útil

La persona usuaria inicial es un técnico municipal que prepara una revisión con los organismos competentes. Su trabajo no es decidir cuál satélite «gana», sino saber qué señal revisar, a quién consultar y qué dato impide una conclusión territorial. El criterio de producto es que el expediente deje esa decisión y sus condiciones explícitas.

| Problema del territorio | Conexión con tendencias y datos | Pregunta que debe ayudar a resolver | Información que aún falta |
|---|---|---|---|
| Lluvia extrema en un entorno ciclónico | Rx1day/Rx5day describen extremos históricos; no sustituyen el pronóstico. IBTrACS permite contextualizar episodios, no afirmar un ciclón actual. | ¿Qué periodo y territorio deben revisar los responsables ante la lluvia prevista? | Boletín vigente, lluvia de cuenca, nivel del río, exposición y accesos. |
| Crecida del Bajo Yuna | La lluvia en Villa Riva no representa el agua que llega desde arriba. El Camú desemboca aguas abajo de Hatillo. | ¿Qué aportes de cuenca y estado del río faltan antes de concluir sobre una crecida? | Aportes del Camú y Alto Yuna, nivel/caudal y operaciones actuales de Hatillo. |
| Déficit de lluvia y uso del agua | Una racha seca o P≤20 no mide por sí sola agua disponible ni necesidad de riego. | ¿Debemos verificar disponibilidad y demanda de agua con operadores y usuarios? | Almacenamiento, servicio/suministro, demanda y etapa del cultivo si corresponde. |
| Infraestructura y planificación | La falta de tendencia significativa no elimina un peligro existente; la disputa entre productos puede señalar dónde medir mejor. | ¿Qué medición conviene verificar o mejorar antes de apoyar una inversión en esa tendencia? | Capacidad de monitoreo local, calidad de estaciones, activos expuestos y criterio de inversión. |
| Inundación urbana, costa, laderas | Un ciclón puede producir peligros distintos de la lluvia acumulada en una celda. No existe aquí un modelo de drenaje, marejada, viento o deslizamiento. | ¿Hace falta derivar el análisis al producto u organismo competente? | Indicadores específicos de cada peligro; no se extrapola este motor a ellos. |

### Conexiones que sí tienen evidencia local

En el análisis 2001–2024, los días a ±1 día de un ciclón cercano representan aproximadamente 4,1 % del calendario, pero contienen 37,6 % de los máximos anuales por celda en IMERG y 15,3 % en CHIRPS. Son resultados de la definición concreta de cercanía (500 km) y soporte espacial, no porcentajes de inundaciones ni prueba de una tendencia en ciclones. La diferencia entre productos muestra por qué importa contrastar extremos además del promedio.

La revisión calcula mayor acuerdo espacial de lluvia fuerte cerca de ciclones (ETS 0,239 frente a 0,097, sin intervalo). Eso no significa que ambos midan bien el volumen ni que la regla de 100 mm ya sea fiable. Tampoco «sin ciclón cercano» equivale a convección local. Fuentes: `PRUEBAS_TROPICALES.md` y `ESTADO_CONCLUSIONES.md`, filas 12–13.

La geometría del caso Yuna estima que Hatillo drena alrededor del 23 % de la cuenca; el Camú aporta aguas abajo. Los cuatro puntos del piloto **no forman una red hidrológica suficiente**: falta expresamente la rama del Camú. Esta conexión ya aparece en `decision_support.domain_information_missing`. No se le asigna a la presa el control de toda la crecida ni se construye un tiempo de propagación sin aforos. Fuente: `CASO_YUNA.md`, delimitación HydroBASINS/HydroRIVERS.

El uso del agua conecta además preparación por crecidas con riego y suministro; [EGEHID describe esos servicios de Hatillo](https://egehid.gob.do/readecuacion-ambiental-y-extraccion-de-sedimentos-cola-del-embalse-de-hatillo/). Es contexto del uso, no evidencia de pérdidas agrícolas actuales. Sin déficit real de suministro, etapa del cultivo y demanda no se traduce el percentil de lluvia en una orden de riego o en daño a flora/fauna.

La temporada atlántica oficial es [junio–noviembre según NHC](https://www.nhc.noaa.gov/climo/index.php). El protocolo humanitario citado en el caso Yuna usa otra ventana de preparación (mayo–noviembre). No se confunden ambas ni se ignora lluvia peligrosa fuera de ellas. El motor 1.1 conserva estado ciclónico actual no incorporado y solicita el boletín: calendario no es detección.

### Mínimo para demostrar que la idea ayuda a alguien

El funcionamiento técnico está comprobado; utilidad operacional no está establecida. La prueba de producto propuesta es una revisión estructurada con responsables municipales, sin enviarles mensajes ni realizar un estudio en su nombre:

1. Elegir de antemano una decisión: qué información priorizar para revisar preparativos ante lluvia intensa en el Bajo Yuna. Comparar el flujo habitual con el expediente en los mismos casos, con orden alternado para reducir aprendizaje.
2. Incluir casos con y sin señal, desacuerdo entre modelos, datos vencidos y déficit junto a lluvia prevista. No usar solo un caso favorable ni hacer creer que son alertas reales.
3. Registrar tiempo de revisión, si identifica periodo/lugar, si detecta el dato crítico faltante (Camú, río, Hatillo o exposición según el caso), si distingue una fuente no independiente y si evita concluir «sin peligro» por falta de tendencia o de cruce del umbral.
4. Registrar también errores introducidos por el expediente y desacuerdos con el criterio del responsable. El éxito y los costes aceptables se acuerdan antes de evaluar; no se inventa ahora un porcentaje de mejora.

Eso puede validar comprensión y utilidad para una tarea de preparación. Demostrar anticipación o daños evitados requiere otro estudio. Esta revisión no presenta la prueba de usuarios como ejecutada.

## Dos mensajes corregidos para comunicar el proyecto

**Qué resolvemos.** Stellar Horizons conecta datos NASA, pronósticos y mediciones locales para preparar el territorio. Detecta señales de lluvia prevista y déficit, muestra sus fuentes y contradicciones y devuelve qué verificar después. La investigación histórica en RD encuentra una discrepancia extendida en la frecuencia de días húmedos de IMERG frente a CHIRPS; se usa para examinar la confianza en las tendencias, sin atribuir aún una causa ni asumir independientes todos los contrastes.

**Hasta dónde llega.** Ya funciona un backend reproducible en cuatro puntos piloto, con control temporal, referencias históricas, dependencias y aportaciones locales identificadas. Todavía no está validado como alerta operacional ni como reducción de daños. GOES sigue sin resolver y la comparación terrestre es limitada. Sí existen archivos de pronósticos anteriores a 2024 que abren una evaluación adicional, pendiente de comprobar corridas, disponibilidad histórica e inicio de eventos. No confundimos esas tareas pendientes con la imposibilidad de construir una solución útil.
