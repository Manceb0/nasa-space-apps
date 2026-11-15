# Conexiones, umbrales y sesgos: resultados nuevos y siguientes deducciones

Stellar Horizons · 15 de noviembre de 2026. Revisión dirigida, no revisión sistemática.

Se leyeron íntegros los dos textos adjuntos («Ahora sí estamos acercándonos…» y «Todavía no está completamente conectado…»), el chat de contexto y los informes locales pertinentes. Se ejecutaron diagnósticos nuevos en Docker con los datos existentes, sin modificar las salidas de los motores anteriores. Código: `earthmemory/cierre.py`; resultados: `results/cierre/`.

## 1. La conexión central: tres umbrales diferentes

| Umbral | Pregunta | Qué tenemos | Qué no permite concluir |
|---|---|---|---|
| De clasificación | ¿Qué cambia al declarar seco con SPI ≤ −1 o día húmedo con lluvia ≥ 1 mm? | Sensibilidad calculada abajo | Que exista una discontinuidad física en esos valores |
| De detección | ¿Tenemos longitud de serie, contraste y observabilidad para distinguir un efecto? | Potencia de tendencias y calidad de testigos ya auditadas | Que ausencia de significancia sea ausencia de fenómeno |
| Hidrológico | ¿Cuándo se activa escorrentía/conectividad suficiente para una crecida? | Hipótesis, modelos y catálogo pequeño del Yuna | Que 100 mm/48 h o θ = 0,59 sean un umbral físico dominicano validado |

La misma cifra puede parecer un «umbral» en una gráfica y tener significados científicos distintos. Antes de buscar uno nuevo, hay que identificar cuál de estos problemas queremos resolver.

## 2. Resultado nuevo: la discrepancia de sequía persiste al alejarse del umbral

Prueba: excluir un provincia-mes si **alguno** de los productos comparados queda a distancia menor que ε de SPI = −1. Calcular desacuerdo entre los casos retenidos donde al menos un producto declara sequía. No se cambia la definición de sequía ni se afirma cuál producto acierta.

| Productos | Margen ε | Alarmas retenidas/originales | Desacuerdos retenidos | Tasa condicional | IC 95 % |
|---|---:|---:|---:|---:|---:|
| Cuatro | 0 | 3111/3111 | 2836 | 91,2 % | 85,3–96,4 % |
| Cuatro | 0,10 | 1779/3111 | 1585 | 89,1 % | 81,8–96,2 % |
| Cuatro | 0,25 | 732/3111 | 614 | 83,9 % | 74,6–94,4 % |
| Cuatro | 0,50 | 128/3111 | 105 | 82,0 % | 62,9–97,8 % |
| IMERG–CHIRPS | 0 | 2245/2245 | 1498 | 66,7 % | 55,8–82,2 % |
| IMERG–CHIRPS | 0,25 | 1004/2245 | 581 | 57,9 % | 41,2–82,3 % |
| IMERG–CHIRPS | 0,50 | 452/2245 | 215 | 47,6 % | 25,4–81,5 % |

IC nuevos: 2000 réplicas de bootstrap circular en bloques de 3 años; todas las provincias y meses del año viajan juntos. Son IC distintos de los anteriores de bloques de un año. La dependencia de duración mayor de tres años no queda garantizada por este procedimiento.

**Deducción respaldada:** una explicación exclusivamente basada en pequeñas oscilaciones alrededor de −1 resulta insuficiente para estos casos retenidos.

**Límite:** con ε = 0,25, cuatro productos conservan solo 23,5 % de las alarmas; con ε = 0,50, 4,1 %. No aplicar sus tasas al conjunto original ni interpretar el descenso como porcentaje de discrepancias «explicadas». Al filtrar cambia la población.

Además, exigir unanimidad entre cuatro productos es más difícil que entre dos aun sin cambios de calidad. Sus tasas no son una comparación justa de cuál conjunto es mejor: cambian miembros, denominador y selección. Hace falta comparación sobre casos comunes y un referente externo para medir exactitud.

## 3. Resultado nuevo: frecuencia e intensidad son sensibles al umbral, pero el mecanismo no está identificado

Mismos 8766 días, 442 celdas incluidas de 0,1°, periodo 2001–2024 y observaciones disponibles en ambos productos. CHIRPS ya está agregado a la rejilla IMERG. Se recalcularon recuentos e intensidad para distintos umbrales y la misma prueba Hamed–Rao/Theil–Sen; BH dentro de las 442 celdas de cada producto × métrica × umbral, q ≤ 0,10.

| Día húmedo desde | Días húmedos: IMERG significativas | Días húmedos: CHIRPS significativas | SDII opuesto con ≥1 producto significativo | SDII opuesto con ambos significativos |
|---|---:|---:|---:|---:|
| 0,5 mm | 175 | 0 | 202 | 54 |
| 1 mm | 123 | 0 | 160 | 29 |
| 2 mm | 36 | 0 | 64 | 0 |
| 5 mm | 2 | 0 | 0 | 0 |
| 10 mm | 0 | 0 | 0 | 0 |

**Comprobación de reproducción:** a 1 mm se recuperan exactamente las 122 celdas significativas de SDII de IMERG, las 72 de CHIRPS y las 160 en disputa del informe original. Las 160 no significan que ambos productos sean significativos en todas ellas: con ese criterio más estricto son 29.

**Deducción:** la prominencia estadística del desacuerdo depende de cómo se define el día húmedo; la franja de lluvia débil merece investigación específica.

**Lo que esta prueba NO demuestra:** que 2 o 5 mm sea el umbral correcto ni que hayamos aislado un sesgo de llovizna. Al excluir días también cambian la muestra, la métrica y su potencia. A 5 mm las pendientes medianas de intensidad siguen siendo opuestas: +0,828 frente a −1,287 mm/día por década; simplemente no pasan el criterio de significancia. No confundir falta de evidencia de oposición con evidencia de acuerdo.

Estas son variantes exploratorias elegidas después de observar la discrepancia. BH no corrige la búsqueda completa entre umbrales y métricas, y no se repitió la calibración de falsos positivos de cada variante. Mantener 1 mm como resultado principal y presentar el resto como sensibilidad.

### Dependencia matemática que conecta dos pistas

Para una misma unidad y un mismo umbral:

`SDII = lluvia acumulada en días húmedos / número de días húmedos`.

Por tanto, menos días detectados pueden elevar SDII aun sin aumento de la lluvia acumulada. No son dos testimonios independientes.

Se calculó además una descomposición descriptiva exacta de las pendientes OLS de sus logaritmos sobre series nacionales ponderadas por área dominicana. Se usa OLS aquí porque permite la identidad aditiva; las pendientes de Sen no se suman en general.

| Producto | Pendiente log lluvia húmeda/década | Pendiente log días/década | Pendiente log intensidad/década |
|---|---:|---:|---:|
| IMERG | +0,0018 | −0,0668 | +0,0686 |
| CHIRPS | −0,1034 | +0,0101 | −0,1135 |

En IMERG, el aumento descriptivo de esa intensidad nacional viene principalmente del denominador; en CHIRPS pesa la caída del numerador. Son unidades logarítmicas por década, no mm ni porcentajes directos. No se infiere significancia ni causalidad de esta tabla. Es intensidad como cociente de cantidades nacionales, no promedio de los SDII de las celdas.

**Nueva deducción:** decir que ambos discrepan «por la llovizna» sería prematuro: los dos términos del cociente están cambiando de manera distinta. Guardé también frecuencias y cantidades por bandas de lluvia en `bandas_lluvia_anuales.csv` para investigar esa separación.

### Escala temporal

La correlación de Spearman mediana entre productos pasa de 0,542 en diario a 0,657–0,669 en bloques de 5 días y 0,714–0,727 en bloques de 10 días, al variar el origen de los bloques.

Esto es compatible con diferencias de reparto/fecha y con el suavizado del ruido al agregar. No demuestra cuál domina. Los bloques son consecutivos en toda la serie, no las péntadas oficiales del calendario CHIRPS. La correlación contiene estacionalidad; no mide por sí sola acuerdo de tendencias ni exactitud frente a la realidad.

## 4. Resultado nuevo: noviembre de 2024 ya tiene una explicación temporal concreta

- Catálogo: 11–20 de noviembre.
- Panel: incluye inicio −3 días; máximo 115,475 mm/48 h el **8 de noviembre**.
- Puntuación de acierto: incluye inicio −2 días; máximo 92,310 mm/48 h el **11 de noviembre**.
- El máximo MODIS reportado es el 21 de noviembre, fuera del final del catálogo. La fecha de un compuesto no demuestra el momento de inicio del agua.

Los 115,5 mm no contradicen el fallo de la regla >100 dentro de la ventana puntuada. No hay que modificar el umbral para arreglar una incoherencia que proviene de comparar resúmenes temporales distintos.

**Lo pendiente:** decidir y documentar una regla común de asociación lluvia–evento–observación para todos los casos. La tabla `cronologia_yuna.csv` cubre inicio −5 a fin +5 para noviembre de 2024, abril de 2017 y octubre de 2025, con lluvia disponible, pertenencia a ventanas y capas MODIS. En 2025 falta la serie local diaria de lluvia: celdas vacías no son ceros ni ausencia de disparo. Los valores de los compuestos MODIS solapados no son observaciones diarias independientes.

Tampoco queda descartada una influencia hidrológica de lluvia anterior: simplemente no está identificada por esta comprobación. No mover las fechas de un caso por conveniencia.

## 5. Literatura que conecta las pistas y cambia la próxima prueba

### Cambios de instrumentos frente a cambios del clima

**Zhu et al., 27-oct-2026**, *Precipitation trend uncertainty from product choice rivals or exceeds the magnitude of actual trends*, Communications Earth & Environment, [DOI](https://doi.org/10.1038/s43247-026-04148-w). Artículo publicado; resumen editorial y metadatos/abstract Crossref verificados; acceso directo al texto completo falló.

Examina 19 productos y documenta discontinuidades vinculadas a cambios de observación, incluidas transiciones de 2014–2015. **Aplicación propuesta:** contrastar en RD un modelo de tendencia continua frente a cambio de nivel alrededor de una transición instrumental fijada externamente. Exigir controles y calibración: diez años posteriores no permiten afirmar automáticamente una tendencia separada. El artículo ya establece el problema general; no presentarlo como descubrimiento exclusivo nuestro.

### El entorno físico puede informar dónde desconfiar

**Derin y Kirstetter, 2022**, [Evaluation of IMERG Over CONUS Complex Terrain Using Environmental Variables](https://doi.org/10.1029/2022GL100186). PDF primario en NOAA y abstract Crossref consultados. Vincula el rendimiento con ascenso forzado por relieve y convergencia de humedad en su dominio de estudio. **Aplicación:** `viento · gradiente del relieve`, humedad transportada y régimen del episodio, con datos a resolución coherente. Altura o ladera orientada al este no identifican barlovento por sí solas.

**Goldenstern, 2025**, [Constraining satellite precipitation biases through geophysical arguments](https://mountainscholar.org/items/9edb6423-1671-49dc-9080-4c88acd5313d). Es una **tesis doctoral**, aunque SciSpace la etiquetó como artículo; ficha y abstract del repositorio universitario verificados. SPREAD utiliza condiciones ambientales para estimar errores de recuperación de lluvia. **Aplicación:** aprender condiciones de discrepancia fuera de muestra, sin fingir que la discrepancia IMERG–CHIRPS es el error verdadero ni transferir directamente resultados de GPROF a IMERG.

**Petković et al., 2023**, [Can We Estimate the Uncertainty Level of Satellite Long-Term Precipitation Records?](https://doi.org/10.1175/JAMC-D-22-0179.1). Abstract Crossref y registro/PDF NOAA localizados. La incertidumbre depende de estados de precipitación, muestreo y escalas. Motiva separar cambios en la frecuencia de regímenes de cambios dentro de cada régimen.

### Humedad medida a distinta profundidad no representa necesariamente el mismo control

**Cui y Tian, septiembre de 2026**, [Soil moisture thresholds for runoff generation: depth sensitivity and mechanistic controls](https://doi.org/10.1016/j.jhydrol.2026.135827). Publicación y autores verificados en Crossref; resumen y extractos del editor consultados mediante búsqueda; acceso directo falló. En cuatro cuencas, la profundidad integrada cambia cuánto explica la humedad la respuesta de escorrentía. **Aplicación:** comparar capas del mismo modelo en iguales periodos y eventos antes de usar SMAP superficial para evaluar una afirmación sobre raíces. No explica por sí solo nuestros pares ni valida θ = 0,59.

**Cui y Tian, agosto de 2026**, [Runoff thresholds, runoff generation mechanisms, and catchment characteristics: a global synthesis](https://doi.org/10.5194/hess-30-5281-2026). Texto primario consultado. Sintetiza 138 cuencas y respalda interpretar umbrales con estado y conectividad, sin un valor numérico universal transferible. **Aplicación:** sustituir la búsqueda de una cifra nacional por una hipótesis condicionada al estado y a rutas hidrológicas, cuando exista observación suficiente para comprobarla.

**Li et al., septiembre de 2026**, [Divergent responses of streamflow reanalysis errors to precipitation reanalysis errors modulated by catchment heterogeneity](https://doi.org/10.5194/hess-30-6115-2026). Abstract y métodos introductorios del texto primario consultados: en 671 cuencas la propagación del error depende del territorio. **Aplicación:** un desacuerdo de lluvia no equivale automáticamente a igual desacuerdo de crecida; probar interacciones con estado de cuenca. Sus coeficientes no se transfieren al Yuna.

### Una opción realmente reciente para una prueba externa futura

**Shalev et al., 10-nov-2026**, [PARDIG: Global Precipitation Estimates Learned from Sparse Satellite Observations](https://arxiv.org/abs/2611.13941). **Preprint**, consultado su resumen primario; no revisión por pares comprobada. Propone estimación global de lluvia aprendida de observaciones dispersas de radar y presenta variantes histórica y reciente. Puede ser un comparador candidato para casos reservados. No se descargó ni probó en RD; hay que auditar insumos, años, calidad y dependencia antes de llamarlo testigo independiente. Añadirlo no resuelve automáticamente el desacuerdo.

## 6. Hipótesis integrada propuesta, todavía por probar

**El desacuerdo cambia por una combinación de régimen de lluvia, sistema de observación, umbral de clasificación y capacidad del territorio para almacenar y conectar agua.**

Para evitar una explicación que lo abarque todo sin poder refutarse, separar dos etapas:

1. **Medición:** ¿bajo qué condiciones cambia ΔP = IMERG − CHIRPS? Usar cantidad continua, ocurrencia de lluvia y desacuerdo de clasificación como respuestas distintas.
2. **Respuesta territorial:** manteniendo un episodio meteorológico comparable, ¿qué información explica agua observada o aforos? En esta etapa intervienen almacenamiento, rutas y retardos; el suelo modelado se etiqueta como tal.

En la primera etapa, definir regímenes mediante información externa, no mediante el propio desacuerdo. Una descomposición útil es `media(ΔP) = suma_r frecuencia(r) × media(ΔP | r)`.

Comparar periodos sobre la misma máscara y temporada. Preguntar si cambia la mezcla de regímenes o cambia la diferencia dentro de cada régimen. Las dos cosas pueden coexistir y esta descomposición no atribuye causalidad. Añadir después la composición instrumental; no declarar que cualquier cambio de 2014 proviene del satélite.

**Controles prioritarios:**

- No clasificar todo día sin ciclón en IBTrACS como «convección local»: faltan frentes, vaguadas, ondas y disturbios.
- Preservar episodios, años y territorios en la partición de validación; provincias vecinas del mismo aguacero no son réplicas independientes.
- Separar dato ausente de valor cero. La selección por cielos despejados puede cambiar la población de eventos observados.
- No usar votación de productos como verdad. La procedencia compartida impide tratar los votos como independientes; tampoco permite deducir su correlación de errores sin medirla.
- No aplicar triple colocación estándar sin comprobar supuestos de independencia de errores, escalas y relación con la variable verdadera.
- No transferir desempeño retrospectivo de IMERG Final a disponibilidad operativa Early/Late. Final incorpora información posterior.

## 7. Una función innovadora que sí se deriva de estas pruebas

Proponer un expediente con **curva de estabilidad del veredicto y cobertura**: al cambiar margen de clasificación, escala temporal, máscara de calidad o fuente, mostrar qué conclusión resiste y cuántos casos dejamos fuera. Adjuntar procedencia y la próxima observación necesaria.

No llamarla «probabilidad de estar en lo correcto» sin validación externa. Los márgenes 0,10/0,25/0,50 son diagnósticos, no umbrales de seguridad. Un futuro umbral de abstención debe calibrarse en eventos reservados con una referencia adecuada y un coste de error definido.

Esto conecta los cinco motores: tendencias aportan cambio e incertidumbre; auditoría aporta sensibilidad y procedencia; testigos aportan observabilidad; Yuna aporta conectividad y agua observada; recuperación aporta definiciones y censura. No requiere inventar un nuevo índice compuesto que oculte cada limitación.

## Reproducción y trazabilidad

PowerShell, desde la raíz del proyecto:

```powershell
New-Item -ItemType Directory -Force results/cierre | Out-Null
$taskWorkspace = (Get-Location).Path
docker run --rm --mount "type=bind,source=$taskWorkspace,target=/app,readonly" --mount "type=bind,source=$taskWorkspace\results\cierre,target=/app/results/cierre" --entrypoint /opt/venv/bin/python phantom:latest -m earthmemory.cierre
```

Imagen utilizada: `sha256:86ef6ab5f7e9aa4e1fad8809c8c1ecf5290019d29a5142ae59dca807417facc9`. Semilla 20261115. Entradas con SHA-256 en `results/cierre/resumen.json`. El código verifica reproducción del resultado SDII principal y del desacuerdo SPI original. Pruebas existentes de tendencias y Yuna: **25 pasaron** en Docker. No se ejecutó el pipeline completo ni se alteraron los cálculos originales.

Salidas: `resumen.json`, `tendencias_sensibilidad_celdas.csv`, `bandas_lluvia_anuales.csv`, `cronologia_yuna.csv`, `bibliografia_crossref.json`.

Herramientas: skill **paper-lookup** (consulta y verificación de DOI con Crossref); MCP **SciSpace** (8 candidatos; reveló la pista SPREAD, cuya clasificación se corrigió con la fuente primaria); búsqueda web y fuentes editoriales/institucionales. PubMed no fue la base principal porque el problema es hidrología y teledetección.

Crossref: cinco consultas de DOI individuales, sin paginación, respuesta `status=ok`, metadatos completos guardados. Consulta SciSpace: “How do satellite precipitation product errors and changing sensor coverage affect wet day frequency and extreme rainfall trends, and how can environmental regimes distinguish physical changes from observational artifacts? year:2022-2026 limit:8”. Fecha de acceso: 15-nov-2026. No se reclama búsqueda exhaustiva ni lectura completa de todos los artículos.
