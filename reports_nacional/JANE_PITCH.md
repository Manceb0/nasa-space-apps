# Pasada Jane completa: qué contamos al jurado

> **Superado (15-nov, tarde). No usar este guion tal cual.** La deducción «un solo cambio de octubre de 2013 fabrica
> las dos tendencias» y las frases «The trend that wasn't» y «82 % of the contradictions disappear» van por delante de
> la evidencia:
> - El tercer testigo (ERA5) sitúa la separación en 2016 y de forma gradual.
> - Una revisión independiente mostró que el ajuste y Pettitt no distinguen un escalón de una deriva.
>
> Lo defendible es esto: IMERG cuenta cada vez menos días de lluvia que sus testigos, y por eso sus tendencias de
> intensidad y de rachas secas no se pueden confirmar. Título candidato: **«The trend we cannot yet confirm»**. Ver
> el veredicto en `PRUEBAS_TROPICALES.md` y `REVISION_JANE.md`. El razonamiento de abajo se conserva como registro.

Fecha: 15-nov-2026, mañana. Modo `hackathon`. Esta es la primera pasada con la regla dura del método: los 7
movimientos y al menos una skill por fila, cada una con su archivo abierto. Todos los números salen de los informes
del repo (`PRUEBAS_TROPICALES.md`, `README.md`). Aquí no se calcula nada nuevo.

## 1. La deducción

**El registro del satélite contaba la historia climática de manual: «la lluvia cae más fuerte y las rachas secas
son más largas». Las dos mitades salen de un solo cambio: desde octubre de 2013 se cuentan menos días de
lluvia.** Con casi la misma lluvia repartida en menos días contados, la intensidad por día sube. Y con menos días
húmedos, los huecos secos se alargan. No son dos señales del clima, sino un solo escalón del registro, visto desde
dos lados.

- [OBSERVADO] Antes de corregir, en IMERG la intensidad sube un +6,7 %/década (p 0,035) y las rachas secas
  largas de diciembre a abril un +16,1 %/década (p < 0,001).
- [OBSERVADO] Al quitar el escalón ninguna de las dos es significativa: −8,8 % (p 0,09) y −13,2 % (p 0,07).
- [INFERIDO, por aritmética] Intensidad = lluvia total ÷ días húmedos. Si se cuentan menos días húmedos y la
  lluvia total casi no cambia, la intensidad sube sin que el clima cambie.

Esto se le pasó por alto a todos, a mí también: yo trataba la intensidad y las rachas secas como dos hallazgos
distintos.

## 2. Las pistas

| Pista | Dato | Fuente |
|---|---|---|
| Hay un salto en cómo se cuentan los días de lluvia | Punto de cambio en 2013-10 (Pettitt, p 0,001): IMERG pasa de contar 2,1 pp más días húmedos que CHIRPS a contar 2,4 pp menos | PRUEBAS_TROPICALES, P4 |
| La cantidad de lluvia no salta | Sin salto claro en la cantidad (p 0,10) | P4 |
| El suelo no lo ve | Días húmedos después frente a antes: pluviómetros +0,2 pp; IMERG −8,5 pp; CHIRPS −0,2 pp (−5,4 en Barahona) | P5 (exploratoria) |
| Corregir un solo escalón resuelve casi todo | Celdas-índice en disputa: 871 → 158 (−82 %); SDII 160 → 0 | Recálculo |
| Corregir no basta para fechar el salto | Cualquier año de corte entre 2010 y 2017 da casi lo mismo | sensibilidad_corte.csv |

## 3. Lo evidente y por qué no basta

1. **«Mostramos el mapa de tendencias de RD con su significancia».** Es lo que hará cualquier equipo de este reto,
   y un mapa con un escalón dentro muestra tendencias que no lo son.
2. **«Mostramos las tres piezas: P0, la auditoría y Yuna».** Esa historia del README es anterior al hallazgo del
   escalón. El hallazgo más fuerte no está en ella.
3. **«Más rigor = más puntos».** En 30 s el rigor que no se ve no puntúa, y el que no cabe estorba.

## 4. Rutas distintas

| Ruta | Mecanismo | Para quién | Qué la diferencia |
|---|---|---|---|
| **A. La tendencia que no era** | Abrir con una tendencia significativa y verla desaparecer al quitar el escalón | Jurado no experto | Los demás muestran tendencias; nosotros mostramos una que se cae y por qué |
| **B. Revisión del instrumento** | En la herramienta, toda tendencia lleva su prueba: ¿el registro salta frente a un segundo producto? Si salta, la etiqueta dice «posible artefacto de medición» | Estudiantes, lo que pide el texto oficial | Pasa de hallazgo a producto replicable en cualquier país |
| **C. Un testigo honesto** | Cuatro productos que «coinciden» comparten pluviómetros, así que coincidir no es confirmar | Jurado técnico | Auditoría de independencia (pieza 2 del README) |
| **D. Donde duele** | Yuna: el 67 % de los disparos de inundación de un producto no los confirma el otro; MODIS confirma 12 de 15 eventos | Criterio de Impacto | Cara humana: arrozales y presa de Hatillo |
| **E. Predicciones registradas** | 8 predicciones escritas antes de correr: 5 confirmadas, 3 refutadas y publicadas | Criterio de Validez | Credibilidad, pero lenta de contar |

## 5. Prueba contra cada ruta

- **A.**
  - *A favor:* sorprende, se entiende y tiene números propios.
  - *En contra (versión fuerte, `thinking-steel-manning`):* «Corrigieron un producto de la NASA con CHIRPS, que usa
    pluviómetros y también se mueve (−5,4 en Barahona). Lo que llaman escalón podría ser una tendencia, porque
    cualquier corte sirve. Y solo hay 4 pluviómetros, que además alimentan a CHIRPS».
  - *Respuesta:* el punto de cambio fecha el salto, los pluviómetros dicen quién cambió y la cantidad de lluvia no
    salta, que es justo lo que predice un cambio en el conteo. Aun así, el pitch dice «no podemos confirmar la
    tendencia», nunca «no hay tendencia». Tampoco decimos «corregimos IMERG», sino «al descontar el escalón de
    2013».
  - *Cambiaría de opinión si* los pluviómetros mostraran la misma caída de días húmedos que IMERG.
- **B.**
  - *A favor:* responde a la herramienta para estudiantes que pide el reto.
  - *En contra:* solo existe la etiqueta para IMERG y estos índices. No hay una prueba genérica para cualquier
    variable, y venderla como general sería prometer de más.
  - *Experimento:* mostrar la etiqueta funcionando en la vista de Tendencias, que ya está encargada al chat de
    pantallas.
- **C.**
  - *A favor:* es una idea sólida.
  - *En contra:* en 30 s compite con A y la diluye. Mejor como una línea dentro de A («coincidir no es confirmar»).
- **D.**
  - *A favor:* lleva el Impacto a un lugar concreto.
  - *En contra:* es otra historia con otro mecanismo.
  - *Salida:* una sola diapositiva de «por qué importa», no el gancho.
- **E.**
  - *A favor:* da credibilidad.
  - *En contra:* no cabe en 30 s. Va al repo y a la diapositiva de método.
- **Pre-mortem (`the-fool`, modo «buscar los modos de fallo»).** La peor forma de perder no es científica. Son las
  23:59 y el repo sigue privado, el video no está o falta la declaración de uso de IA. Es el modo de fallo más
  probable y el más barato de evitar.

## 6. Decisión

**A es el gancho y la columna del pitch, B es la prueba de que es un producto, D aporta una diapositiva de impacto y
C y E van dentro del método.** Se termina el análisis nuevo, ni corrección estacional ni ETS: todo el tiempo
restante va al pitch y la entrega.

Cambiaría si el equipo sabe que el jurado local premia lo local por encima de todo. En ese caso D abre y A explica.

## 7. Primer entregable: guion

**Video de 30 s (inglés)**

| Tiempo | Voz | Imagen |
|---|---|---|
| 0-5 s | "Satellite records say Dominican rain is getting more intense, with longer dry spells." | Mapa de IMERG tal como se publicó (fig. 08, a1) |
| 5-11 s | "Rain gauges on the ground don't see it." | Pendientes de las 4 estaciones (fig. 07, b) |
| 11-20 s | "In October 2013 the satellite record began counting fewer rainy days. Nearly the same rain, fewer days: rain looks heavier, dry spells look longer." | Franja con el punto de cambio (fig. 07, a) |
| 20-26 s | "Account for that one step, and 82% of the contradictions disappear." | Mapas antes → después (fig. 08) |
| 26-30 s | "Evidence Intelligence: before you trust a trend, check the instrument. Stellar Horizons, Dominican Republic." | Herramienta con la etiqueta de artefacto |

**7 diapositivas**

1. **The trend that wasn't.** Stellar Horizons · Evidence Intelligence.
2. **What the record says.** IMERG national trends: rain intensity +6.7 %/decade (p 0.035); long dry spells
   +16.1 %/decade (p < 0.001). P0: what changes, where, how much, how significant.
3. **The contradiction.** CHIRPS disagrees in 871 cell-index pairs. Gauges: +0.2 pp wet days, IMERG −8.5 pp.
4. **The twist.** A step in Oct 2013 in how wet days are counted, not in how much rain falls. Intensity = total ÷
   wet days.
5. **The proof.** Account for one step: disputes 871 → 158 (−82 %); both trends lose significance. Limits: any cut
   year from 2010 to 2017 works, only 4 gauges, partly circular.
6. **Why it matters.** Yuna basin: 67 % of one product's flood triggers are not confirmed by the other; MODIS
   confirms 12 of 15 events. Decisions made on a measurement artifact cost money and trust.
7. **What we built.** A tool where every trend comes with an instrument check, plus the open repo, the method, the
   predictions registered before running (5 confirmed, 3 refuted) and the AI-use declaration.

Lenguaje: nunca «the satellite lies» ni «we corrected NASA».

**Entrega, sin falta (dominio *Clear*, se ejecuta como una lista de pasos):**
- Repo público, con tu permiso.
- Video subido.
- Declaración de IA.
- Enlace a la herramienta.
- «Submit for Judging».
- Meta: las 20:00.

## 8. Lentes usadas, fila por fila

| Fila | Skill | Qué reveló |
|---|---|---|
| 1. Escena | `thinking-cynefin` | El cuello de botella ya no es el análisis (*Complicated*, hecho). Ahora es la entrega (*Clear*: una lista de pasos) y la recepción del pitch (*Complex*: probar el gancho con alguien antes de grabar). Seguir analizando era quedarse en el dominio cómodo. |
| 1. Escena | `system-operator` | Supersistema: cientos de equipos con el mismo reto mostrando mapas de tendencia. El hallazgo propio se ve contra ese fondo. |
| 2. Premisa | `thinking-first-principles` | Restricciones reales: 30 s o 7 diapositivas, inglés, 5 criterios y enlace público. «Contar las tres piezas» era convención, no restricción. |
| 2. Premisa | `perception-mapping` (ligera) | Par en conflicto del propio equipo: «mostrar todo = riguroso» frente a «el jurado recuerda una cosa». El nodo colector es «hay que enseñar todo lo que hicimos», el mismo error de la galería (lección 3). |
| 3. Ideas | `lateral` → `provocation` | El router lo eligió porque la regla «un detective de tendencias muestra tendencias» parecía inamovible. Cuatro provocaciones dieron ideas, una se fusionó y otra se abandonó: ver el anexo. |
| 3. Ideas | `resource-analysis` (resultado ideal) | «La tendencia falsa se delata sola». Con la cantidad de lluvia como recurso, la cantidad no salta y el conteo sí: eso discrimina clima de instrumento. Con el estudiante como recurso, el «Predict Before Reveal» de la herramienta ya es el escenario de la demo. |
| 3. Ideas | `contradiction-solver` (matriz de Altshuller) | Contradicción: si mostramos todo el rigor, sube la fiabilidad pero el mensaje se complica. La matriz cruza 27 Fiabilidad con 36 Complejidad y da IP #13 *The Other Way Around* (mostrar la tendencia que desaparece en vez de la que aparece), IP #1 Segmentación (30 s con un hallazgo; la prueba en capas) e IP #35 Cambio de parámetros (el detalle plegable). |
| 4. Detalle | `cause-effect-chain-analysis` | Cadena: menos días contados → intensidad por día más alta y rachas secas más largas → dos tendencias «climáticas» con una sola causa raíz. Problema clave: ¿cómo confía un estudiante en una prueba de tendencia sin conocer la historia del instrumento? |
| 5. En contra | `the-fool` (pre-mortem) y `thinking-steel-manning` | Versión fuerte contra A: «corrigieron NASA con CHIRPS». Se revisó la redacción, no la conclusión. El fallo más probable es no entregar, no la ciencia. |
| 6. Decisión | `thinking-opportunity-cost` | Una hora más de análisis frente a una hora de pitch: la mejora en Validez es pequeña, mientras que perder la entrega no tiene vuelta atrás. Decisión: cambiar al pitch. |
| 6. Decisión | `trimming` (regla C) | Ciclones y relieve se quitan del pitch: el escalón ya cumple la función de «contexto tropical que explica el desacuerdo». PHANTOM se quita (regla A: ya no es nuestra afirmación). Todo se queda en el repo. |
| 6. Decisión | `ideality` | Sistema ideal: el estudiante no hace nada y la revisión del instrumento viene hecha con cada tendencia. Dirección: bajar el daño (conclusiones falsas) sin pedir conocimiento de estadística. |
| 7. Memorable | `thinking-jobs-to-be-done` | «Cuando veo una tendencia significativa en 24 años de satélite, quiero saber si es el clima o el instrumento, para no engañarme». Hoy Giovanni y AppEEARS dan la tendencia sin esa revisión, y nadie la hace. |
| 7. Memorable | `six-hats` (solo sombrero rojo) | Alivio: por fin una historia que es nuestra. Incomodidad: abrir con «no era real» suena a aguafiestas. Miedo: un juez de la NASA lo lea como un ataque a IMERG. Por eso se redacta como «el registro empezó a contar distinto». |

### Anexo: provocaciones (con la que se abandonó)

- **Po: el pitch no muestra ninguna tendencia.** Principio: lo que se entrega es el veredicto sobre la tendencia.
  Lleva a la ruta A.
- **Po: el dato interroga al estudiante.** Antes de mostrar una tendencia, la herramienta pregunta «¿qué instrumento
  la midió y cambió?». Lleva a la ruta B.
- **Po: hay un solo pluviómetro en todo el país.** Principio: lo que vale es un testigo independiente, no muchos que
  coinciden. Lleva a la línea «coincidir no es confirmar».
- **Po: publicamos el resultado antes del análisis.** Es el registro previo de predicciones. Lleva a la ruta E.
- **Po: el mapa se corrige solo.** Se fusionó con B.
- **Po: no hay satélite.** No dio movimiento: RD tiene muy pocos pluviómetros y la herramienta vive del satélite.
  Abandonada.
