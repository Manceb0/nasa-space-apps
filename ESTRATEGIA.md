# ESTRATEGIA: auditoría del brief maestro (documentos A–G)

## Estado de cada capacidad (actualizado: sábado 14, tarde-noche)

**Instrucción del equipo:** por ahora todo en local; no se publica nada sin aprobación.

| Capacidad | Estado | Evidencia |
|---|---|---|
| Flujo variable → zona → hipótesis → serie → tendencia → significancia → explicación | **Implementado y validado** | `web/`, datos de `phantom/trends.py`; 28 pruebas; revisado en navegador, en escritorio y teléfono |
| Predict Before Reveal (predecir antes de ver) | **Implementado** | La evidencia no se muestra hasta elegir una predicción; luego se compara con ella |
| Lección de la estación (datos crudos frente a anomalía) | **Implementado** | Botón "Ver los datos crudos" con la amplitud estacional real |
| Mapa de ventanas (cambiar el intervalo y ver si la conclusión se mantiene) | **Implementado y validado** | 120 ventanas reales por serie, precalculadas por Python; "intervalos que engañan" en 7 de 8 series |
| Corrección por autocorrelación (Mann-Kendall AR(1)) | **Implementado y validado** | Prueba sintética: menos falsos positivos que Mann-Kendall simple |
| Corrección por comparaciones múltiples (BH) | **Implementado** | q sobre las 8 series, visible en la evidencia y en el pasaporte |
| Pasaporte de la evidencia | **Implementado** | Fuente, producto, caja, archivo, verificación, método, URL para reproducir en Giovanni |
| Expediente PHANTOM con resultados | **Implementado con datos MODIS reales (puntos)** | 108 filas evento × punto × señal; resumen generado desde los datos |
| Challenge the Evidence (18 combinaciones) | **Implementado con datos reales** | `results/sensibilidad.csv`; arranca en el caso robusto Jaragua 2015 |
| Expediente Recovery Collision | **Implementado con datos reales** | 3 colisiones en 54 sequías evaluadas (punto × evento) |
| Variables MODIS en el detective (NDVI, LST, GPP) | **Implementado y validado** | Promedio de anomalías de los puntos de cada zona; 14 series en total con BH |
| Módulo de idiomas español / inglés | **Implementado**, probado en local | Selector en la barra, recordado en el navegador; `?lang=es` o `?lang=en` |
| Atlas de impacto (mapa de discordancia) | **Pendiente** | Pedido de área `eec5627a…` enviado; sin datos no hay mapa |
| URL pública | **Existe una versión anterior publicada** (solo español, sin MODIS) en https://earth-system-detective.vercel.app; el equipo pidió no publicar todavía | Decidir si se baja o se deja |


Stellar Horizons · 14 de noviembre de 2026, sábado por la tarde · cierre: domingo 15, 11:59 p. m. (hora RD)

Responde al "Master Research & Innovation Brief" (versión 1.0, 13 de noviembre). Separo en todo
momento **verificado**, **hipótesis** y **pendiente**. Fuentes abiertas hoy:
- texto oficial del reto (spaceappschallenge.org, leído en el navegador);
- los tres DOI del brief, comprobados en Crossref y OpenAlex;
- el código y los datos de este repo.

---

## A. Auditoría de la idea

### A1. Lo que dice el reto (verificado, texto oficial)

El reto pide **una herramienta** que permita:
1. elegir variables de misiones o modelos de la NASA;
2. obtenerlas para una región;
3. visualizar su serie de tiempo;
4. calcular la tasa de cambio y probar su significancia (t-test, Mann-Kendall o intervalos de confianza).

En sus "consideraciones", el reto añade:
- **Audiencia:** estudiantes de secundaria y universidad, y público con algo de base científica.
- **Definiciones simples** de cada variable.
- **Que el usuario se vuelva "detective"**: que elija qué y dónde investigar y compruebe si hay tendencia.
- **Un par de ejemplos de demostración** que el usuario pueda ver.
- Quitar el ciclo estacional antes de buscar tendencias. Con tendencias lineales "sería un gran comienzo".
- Una tendencia es interesante aunque no sea significativa; a veces solo falta una serie más larga.

### A2. El hallazgo más importante de esta auditoría

**Lo que hemos construido no es todavía lo que pide el reto.** PHANTOM es un pipeline de
investigación que responde una pregunta concreta: verdor contra función tras una sequía. El
reto pide una herramienta donde **el usuario** elige la variable y la región y descubre la tendencia.

Un jurado puede valorar mucho la ciencia de PHANTOM y aun así puntuar bajo en **Relevancia** si no
ve "elige variable → elige región → serie → pendiente → ¿significativa?".

**Recomendación (cambio de encuadre, no de trabajo):**
- **El producto** es la herramienta de detective: variables de la NASA con definición simple,
  regiones dominicanas, serie desestacionalizada, Theil-Sen + Mann-Kendall + IC, y un veredicto en
  lenguaje claro ("sube X por década; significativo / todavía no").
- **PHANTOM y Earth Recovery Gap** se convierten en los **"expedientes de demostración"** que el reto
  pide expresamente: la investigación seria que muestra hasta dónde llega la herramienta.

Casi todo el código ya existe: `phantom/stats.py` y `phantom/drought.py` hacen las tendencias y la
desestacionalización. Falta la capa de selección y la interfaz.

### A3. Dos ideas mezcladas: hay que nombrarlas

| | Earth Recovery Gap (brief del 13-nov) | PHANTOM (lo construido el 14-nov) |
|---|---|---|
| Pregunta | ¿Llega la siguiente perturbación antes de que la vegetación se recupere? | ¿La vegetación se *ve* recuperada antes de *funcionar* recuperada? |
| Métrica | Estado de recuperación al empezar el siguiente evento | Δt = t(función) − t(verdor) |
| En el código | **Ya se calcula sin nombre**: un evento "censurado porque empezó la siguiente sequía" es exactamente una colisión | `phantom/recovery.py` |

Las dos caben como dos expedientes. La "colisión" sale casi gratis: solo hay que etiquetarla y contarla.

### A4. Originalidad: lo que ya existe (verificado)

| Antecedente | Qué hace | Qué NO hace (frente a nosotros) |
|---|---|---|
| **NASA Giovanni** | Series, mapas y promedios de área de cientos de variables | No define eventos ni recuperación; no pone a prueba la conclusión con supuestos alternativos |
| **NASA AppEEARS** | Extrae MODIS por punto o área, con capas de calidad | Extracción, no análisis de recuperación |
| **LandTrendr (Google Earth Engine)** | Segmenta series Landsat en perturbación y recuperación de un índice | Un solo índice; no compara dos definiciones de recuperación |
| Bathiany et al. 2024, *Surveys in Geophysics*, "Ecosystem Resilience Monitoring and Early Warning Using Earth Observation Data: Challenges and Outlook" | Revisión: recuperación frente a intervalo entre perturbaciones | Es una revisión, no una herramienta |
| Yao, Liu, Zhou et al. 2023, *Global Change Biology*, "Soil moisture determines the recovery time of ecosystems from drought" | Tiempo de recuperación tras sequías y su control por la humedad del suelo | Global, sin interfaz de verificación |
| Smith, Traxl y Boers 2022, *Nature Climate Change*, "Empirical evidence for recent global shifts in vegetation resilience" | Cambios de resiliencia vegetal desde satélite | Global; método de autocorrelación, no recuperación por evento |

**Lo que NO podemos decir:** que inventamos medir la recuperación, ni el índice, ni la idea de
recuperación incompleta.

**Lo defendible (hipótesis de diferenciación, por demostrar con la demo):**
1. Dos definiciones independientes de "recuperado" (verdor y temperatura del dosel), además de GPP como modelo.
2. Censura explícita, en vez de inventar una duración.
3. **Recálculo de la conclusión con 18 supuestos**, con la etiqueta ROBUSTO o SENSIBLE A SUPUESTOS.
4. Todo reproducible con un comando y en Docker.
5. Pensado para estudiantes, como pide el reto.

Respuesta a "¿por qué un investigador usaría esto si existe Giovanni?": porque Giovanni muestra la
serie, pero no dice si una recuperación es robusta ni deja refutarla. Esa respuesta solo vale si la
demo lo muestra con datos reales.

### A5. Debilidades, de mayor a menor

1. **Todavía no hay datos MODIS.** El pedido de puntos va al 40 % tras unas 5 horas. Si un pedido
   de área se lanza tarde, puede no llegar al cierre.
2. **GPP MOD17 es circular** con el verdor (FPAR) y con la meteorología (reanálisis). Mitigación ya
   implementada: segunda señal térmica (LST − T aire) y GPP rotulado como "modelo".
3. **Pocos eventos por punto.** La tendencia de Δt exige 4 o más eventos con ambas recuperaciones;
   es probable que no se alcance. Entonces se reporta por evento, sin tendencia.
4. **Cinco puntos no son una región.** Para mapas hace falta un pedido de área.
5. **Sede:** el brief dice Santo Domingo; el reporte anterior decía Santiago. Hay que confirmar la
   sede registrada y si exige pitch presencial.

### A6. Qué nos haría descartar PHANTOM como pieza central

Corte: **domingo, 10:00 a. m.** Si con los datos MODIS reales:
- menos de 3 eventos tienen las dos recuperaciones observadas en algún punto, o
- todas las etiquetas salen SENSIBLE A SUPUESTOS o SIN DATOS SUFICIENTES,

entonces PHANTOM se presenta como **"inconcluso, y la herramienta explica por qué"**, que también es
un resultado válido. La pieza central pasa a ser la herramienta de detective con las tendencias
climáticas reales que ya tenemos.

---

## B. Laboratorio de innovación

| # | Idea | ¿Existe algo equivalente? | Costo | ¿Responde al reto? | Decisión |
|---|---|---|---|---|---|
| 1 | **Detective de tendencias** (variable + región → serie desestacionalizada → Theil-Sen, MK, IC, veredicto simple) | Sí, en piezas (Giovanni, KNMI) | Bajo: el código existe | Directo, es el núcleo | **HACER YA** |
| 2 | **Challenge the Evidence**: cambiar umbral, persistencia, NDVI/EVI y filtro de calidad, y ver si la conclusión se mantiene | No conocemos una herramienta pública que lo haga sobre recuperación | Medio: la grilla de 18 combinaciones ya se calcula de verdad | Fuerte (Validez) | **HACER**: la interfaz lee la grilla precalculada por el mismo código y lo dice |
| 3 | **Recovery Collision** (ERG): marcar los eventos en que la siguiente sequía llegó antes de la recuperación | Concepto en Bathiany 2024 | Muy bajo: ya está en los datos censurados | Medio | **HACER** como etiqueta y conteo |
| 4 | **Evidence Passport**: una ficha por conclusión con fuente, versión, filtros, parámetros, prueba y límites | Partes en artículos | Bajo: ya hay JSON de procedencia | Validez y Presentación | **HACER** |
| 5 | **Señal térmica** como segunda "función" (LST − T aire) | La teledetección térmica del estrés existe; como contraste de recuperación frente al NDVI no la hemos visto en herramientas | Hecho | Medio | **YA HECHO**: destacarlo |
| 6 | **Recovery Debt Ledger**: área acumulada bajo la anomalía negativa | Equivale a "déficit acumulado" o "legado de sequía" en la literatura | Bajo | Bajo | **SOLO SI SOBRA TIEMPO**, rotulado exploratorio |
| 7 | **Climate Twin**: comparar Montecristi y Jaragua | Común en estudios | Medio | Bajo | **NO**: no están emparejados; sería sugerir causalidad |
| 8 | **Intérprete IA** | Muy común | Medio | Bajo | **NO** en 2026: el veredicto en lenguaje claro sale de plantillas sobre números calculados |

---

## C. Decisión de arquitectura

El brief propone Next.js + FastAPI + MapLibre + Xarray. **Recomiendo menos:**

| Pieza | Decisión | Por qué |
|---|---|---|
| Análisis | Python `phantom/` (existe), uv, Docker (existe) | Ya probado: 22 pruebas, salida local = Docker |
| Datos para la web | El pipeline exporta JSON/CSV estáticos | Sin servidor no hay nada que se caiga durante la evaluación |
| Interfaz | Un sitio estático (Vite + TypeScript o un solo HTML) con gráficas interactivas | Se publica en Vercel o GitHub Pages; el jurado lo abre con un enlace |
| Mapa | MapLibre **solo si** llega el pedido de área | Sin datos espaciales, un mapa sería decoración |
| Backend FastAPI | **No** | "Challenge the Evidence" lee una grilla precalculada de verdad; no hace falta calcular en vivo |
| Figuras estáticas | matplotlib (existe) | Evidencia para el PDF y el repo |

Descartados: base de datos, microservicios, varios contenedores, chatbot.

---

## D. Protocolo científico

El método completo está en `METHODOLOGY.md`. Aquí van solo las hipótesis y los criterios de rechazo.

**Expediente PHANTOM**
- H1: tras las sequías SPI-3, la señal de función vuelve a lo normal después que el verdor (Δt > 32 días).
- H0: |Δt| ≤ 32 días, o el signo de Δt cambia con los supuestos razonables.
- Rechazo de H1: H0 en la mayoría de los eventos con ambas recuperaciones, o datos insuficientes.

**Expediente Recovery Collision**
- H1: hay sequías que empiezan con la vegetación todavía bajo su banda normal (z < −1 sostenido).
- H0: toda sequía empieza con la vegetación recuperada.
- Medida: número de colisiones / número de eventos, con la definición exacta del umbral.

**Tendencias** (núcleo del reto):
- Theil-Sen + Mann-Kendall sobre anomalías desestacionalizadas.
- Autocorrelación de lag 1 informada.
- Benjamini-Hochberg cuando hay muchas pruebas.
- Se dice cuántas pruebas se hicieron.

**Sin decir nunca:** causalidad, "daño ecológico", "colapso", o "bosques dominicanos" a partir de 5 puntos.

---

## E. Plan del hackatón (hora RD)

| Cuándo | Qué | Hecho cuando |
|---|---|---|
| Sábado, ahora | Decidir si se lanza un pedido de **área** pequeño en AppEEARS (2 polígonos, 2014–2021, sin LST) | Pedido enviado o descartado por escrito |
| Sábado, tarde y noche | Herramienta de detective sobre las 8 series de Giovanni ya validadas: selector de variable y región, serie, tendencia, veredicto, definiciones | Funciona con datos reales y publicada en una URL |
| Sábado, noche | Etiqueta de colisión + Evidence Passport en el pipeline | Pruebas pasan; en `RESULTS.md` |
| Domingo, al llegar MODIS | `docker compose run --rm phantom`; revisar las figuras 3 y 4 | Resultados reales en `RESULTS.md` |
| **Domingo, 10:00** | **Corte A6**: PHANTOM fuerte o inconcluso | Decisión escrita en el registro (G) |
| Domingo, 10:00–15:00 | Expedientes en la interfaz + Challenge the Evidence | Enlace público estable |
| Domingo, 15:00–18:00 | Video de 30 s, página del proyecto, revisión adversarial | Video grabado con datos reales |
| **Domingo, 20:00** | **Entrega** (margen interno de 4 h) | Confirmación de envío |

Qué se recorta primero si falta tiempo: mapa → Recovery Debt Ledger → animaciones → el expediente de colisión.
Lo que nunca se recorta: tendencia + significancia + definiciones (el reto) y la honestidad de los datos.

---

## F. Presentación

**Video de 30 s:**
1. 0–5 s: "¿Y si la naturaleza se ve recuperada antes de estarlo?"
2. 5–12 s: el usuario elige "Lluvia · Montecristi" y ve la tendencia con su veredicto.
3. 12–22 s: abre el expediente de 2015: verdor contra temperatura del dosel; cambia el umbral y la etiqueta se mantiene o cambia.
4. 22–27 s: el hallazgo real, sea fuerte o inconcluso.
5. 27–30 s: Stellar Horizons, República Dominicana.

**Preguntas probables del jurado:**
- *"GPP sale del mismo NDVI, ¿no es circular?"* Sí, en parte. Por eso hay una segunda señal térmica independiente y GPP va rotulado como modelo.
- *"¿Cinco puntos?"* Son un piloto. Lo decimos en pantalla, y la fase 2 por áreas está especificada.
- *"¿Qué hay de nuevo frente a LandTrendr?"* Dos definiciones de recuperación, censura explícita y recálculo con supuestos alternativos, para estudiantes.
- *"¿Y si no hay brecha?"* La herramienta lo dice y explica por qué; está programado así desde el principio.

---

## G. Registro de decisiones

| Fecha | Decisión | Alternativas | Evidencia | Qué la tumbaría | Pendiente |
|---|---|---|---|---|---|
| 14-nov | Señal funcional térmica además de GPP | Solo GPP (brief) | Fórmula MOD17: FPAR + VPD/Tmin de reanálisis | LST con demasiados huecos por nubes en los puntos | Ver la cobertura real de QC |
| 14-nov | Puntos verificados en imagen satelital | Coordenadas de memoria | 4 de 5 caían en arrozales, un aeropuerto o un pueblo | MCD12Q1 marca un cambio de clase | Leer `LC_Type1` |
| 14-nov | SPI-3 ≤ −1 durante 2+ meses como evento | Percentil 20 | El SPI estandariza; p20 marca el 20 % por construcción | Gamma mal ajustada en meses secos | Revisar los meses sin SPI |
| 14-nov | Recuperación: z ≥ −1 sostenido; impacto: z < −1.5 sostenido | z ≥ −0.5 | Las pruebas sintéticas: −0.5 da falsos "no recuperado" el 31 % del tiempo | Señal real muy ruidosa | Ver la sensibilidad real |
| 14-nov | **Reencuadre: herramienta de detective + expedientes** | Pipeline PHANTOM como producto | Texto oficial del reto | Que el equipo prefiera competir solo con la investigación | **Decisión del equipo** |
| 14-nov | Sitio estático sin backend | Next.js + FastAPI | Menos piezas que fallen; "Challenge" usa la grilla real | Necesidad de calcular en vivo | — |
| 14-nov | **Aprobado por el equipo:** herramienta de detective + PHANTOM como expediente principal + Predict Before Reveal | Solo PHANTOM | Texto oficial del reto | — | — |
| 14-nov | Pedido de área pequeño lanzado (2 polígonos de unos 18 km, 2012–2021, ID `eec5627a…`) | 2001–2024 completo | Los puntos llevan 6 h y van al 40 %; menos años y menos área dan más opciones de llegar | Que no llegue el domingo a las 10:00 | Vigilar |
| 14-nov | Mann-Kendall corregido por autocorrelación AR(1) para el veredicto | MK simple | Lag-1 anual de 0,5–0,6 en 6 de 8 series; la prueba sintética muestra más falsos positivos con MK simple | — | — |
| 14-nov | "Cambiar el intervalo" lee 120 ventanas precalculadas | Reimplementar la estadística en TypeScript | Una sola fuente de verdad (Python, probada) | — | — |
| 14-nov | Mapa base NASA GIBS Blue Marble | OSM o Esri | Es de la NASA, sin clave y con uso claro | — | — |
| 14-nov | **Resultado PHANTOM (puntos): hipótesis no respaldada en general** | — | De 24 comparaciones con ambas recuperaciones, 19 dentro de ±32 días, 4 con la función antes y 1 después; único robusto a favor: GPP en Jaragua 2015 (+104 d) | Que el pedido de área (más píxeles) muestre otra cosa | Esperar el área; presentarlo como hallazgo honesto |
| 14-nov | **Hallazgo de tendencia:** Montecristi pierde verdor (NDVI p = 0,010), se calienta en superficie (+1,16 °C/década, p = 0,037), baja GPP y baja la lluvia; Jaragua estable | — | Mann-Kendall corregido por AR(1), sin ventanas que engañen en Montecristi; q = 0,13 con 14 pruebas | Sesgo de muestreo de días despejados en LST; deriva de Terra (sesgaría hacia frío) | Contrastar con Aqua (MYD) si da tiempo |
| 14-nov | Regla de cobertura: se excluye solo por clase no natural (no por cambio bosque/sabana) | Excluir por cualquier cambio (regla escrita) | Ningún punto pasó a cultivo o urbano; la confusión bosque/sabana es común en MCD12Q1 | — | Documentado en `appeears/METODO.md` |
| 14-nov | Variables MODIS en el detective, agregadas por zona como media de anomalías | Una serie por punto | Responde "dónde" sin fingir región; el mapa muestra los puntos | — | — |
| 14-nov | Español e inglés | Solo español | El jurado global evalúa en inglés | — | — |
| pendiente | Confirmar sede (Santo Domingo o Santiago) y si hay pitch | — | El brief y el reporte anterior no coinciden | — | **Equipo** |
