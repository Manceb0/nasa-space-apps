# Pasada Jane: qué recorrido ve el jurado (15-nov-2026, noche)

Modo `hackathon`. Se pasaron los 7 movimientos con al menos una skill por fila, y se abrió el archivo de cada una.
Todas las cifras están en el repo; las fuentes van en la última tabla. Aquí no se calcula nada nuevo, salvo la
comprobación del contador de microondas.

## 1. La deducción

**Nuestro hallazgo no es un culpable. Cada conclusión fuerte que tuvimos se movió cuando alguien tocó una elección
escondida:**
- **El umbral de día lluvioso:** 202 → 160 → 64 → 0 celdas en disputa.
- **El método de corrección:** borra el 74,6 % de una tendencia inventada sin ningún salto.
- **La referencia:** la fecha del cambio pasa de 2013 a 2016 o a 2018 según con qué se compare.
- **La ventana de tiempo:** el mismo aguacero de nov-2024 cuenta a la vez como fallo y como falsa alarma.
- **La propia prueba:** la resta de contadores de la prueba GOES no era válida.

Ese patrón es el producto: una herramienta que enseña **qué elección escondida sostiene cada tendencia** y deja que el
jurado la mueva con su mano.

El último ejemplo es de hoy. La prueba de GOES parecía absolverlo, hasta que una revisión miró cómo estaba construida.
Lo comprobé en los datos: en el 2 % de los celda-días las microondas cuentan más medias horas con lluvia que el producto
combinado, así que la resta no separaba las dos vías. GOES pasa a **sin resolver**, no a «debilitada».

## 2. Las pistas

| Pista | Dato | Fuente |
|---|---|---|
| La intensidad de IMERG sube en el país | SDII +6,7 %/década (p 0,035) | recalculo/nacional_IMERG_foco.csv |
| CHIRPS no está de acuerdo | 160 celdas SDII en disputa; en 29 los dos productos son significativos con signo opuesto | tendencias_celdas.csv (comprobado hoy) |
| La disputa depende del umbral | 202 / 160 / 64 / 0 a 0,5 / 1 / 2 / 5 mm. El 0 es falta de potencia, no acuerdo | CONEXIONES_UMBRALES_Y_SESGOS |
| La corrección no discrimina | Quita el 74,6 % de una tendencia sintética sin salto; Pettitt da p 0,0003 con esa misma serie | results/tropical/revision |
| La consecuencia sí es real | La decisión de sequía cambia según el producto: en el 39 % de las alarmas otro producto dice normal o húmedo | AUDITORIA_CONFIANZA |
| La prueba también se interroga | En el 2,0 % de los celda-días, las microondas cuentan más lluvia que el combinado | PRUEBAS_TROPICALES (corrección GOES) |

## 3. Lo evidente y por qué no basta

1. **«Expediente: ¿quién borró los días de lluvia? Sospechoso GOES, hipótesis debilitada».** La prueba que lo
   sostenía no era válida. Ante un experto sería el punto más débil del pitch.
2. **«Unificar Investigar y Recovery Ribbon».** El código ya lo hizo: los dos viven en Tendencias y `#investigar` y
   `#ribbon` redirigen (`web/src/main.ts`, alrededor de la línea 1388). Recovery Ribbon conserva su significado de
   recuperación de la vegetación.
3. **«Tres expedientes completos».** Con las horas que quedan, tres a medias valen menos que uno terminado.

## 4. Rutas posibles

| Ruta | Mecanismo | Qué la diferencia |
|---|---|---|
| A. Expediente GOES (propuesta del colaborador) | Sospechoso, experimento y veredicto | Narrativa de detective, pero el veredicto no se sostiene |
| B. Interrogar al método (propuesta de la revisión) | El usuario aplica la corrección a una serie sintética y ve que la borra | Muestra profundidad; es abstracto si va solo |
| C. Mover el umbral | 202 / 160 / 64 / 0 celdas | Inmediato y real, pero el 0 puede leerse como «acuerdo» |
| D. La ventana de Yuna | El mismo aguacero es fallo y falsa alarma según la ventana | Local y concreto; la confirmación de MODIS es débil (unos 4 km²) |
| **E. «La conclusión se mueve en tu mano»** | Una sola tendencia real que el usuario sostiene y luego mueve, primero con la definición y después con el método | Une B y C con datos reales; GOES queda como investigación abierta |

## 5. Prueba en contra

- **A.** Lo que hoy la tumba es que su prueba central no separaba las vías. No es presentable.
- **B y E.** La mejor objeción: «muy bien, todo es incierto, ¿y qué?», que pesa en el criterio de impacto.
  - *Respuesta:* el veredicto final muestra lo que **sí** está confirmado y su consecuencia (la decisión de sequía
    cambia según el producto en el 39 % de las alarmas).
  - *Riesgo:* que la serie sintética se lea como dato falso. Se etiqueta «SINTÉTICA» en pantalla.
- **C.** El 0 a 5 mm hay que explicarlo como falta de potencia; si no, parece que los productos coinciden.
- **D.** Un solo evento con una confirmación débil. Sirve como ejemplo en «Mostrar evidencia», no como gancho.
- **Pre-mortem.** El fallo más probable no es científico: que la web crezca más y no se entregue, o que el repo siga
  privado a las 23:59.

## 6. Decisión

**Ruta E, construida solo con resultados ya calculados.** Las alternativas quedan así:
- **GOES:** sale del recorrido; queda como «investigación abierta» en la tabla de estado.
- **Yuna:** queda como evidencia plegada.
- **Recovery Ribbon:** no se toca.

Cambiar de recorrido es reversible y barato, porque todo está calculado. Entregar tarde o con el repo privado no lo es.

Cambiaría de opinión si una persona ajena al equipo no entiende el paso 3 en 25 segundos. En ese caso se quita el
paso 3 y queda C + veredicto.

## 7. Primer entregable: el recorrido de 90 segundos

| Paso | Qué hace el jurado | Qué ve (datos reales) | Qué descubre |
|---|---|---|---|
| 1. Predice (15 s) | Responde «¿llueve más fuerte en RD?» | IMERG: intensidad +6,7 %/década (p 0,035). CHIRPS: 160 celdas en desacuerdo, 29 con los dos significativos | La respuesta depende del producto |
| 2. Mueve la definición (20 s) | Desliza el umbral de día lluvioso: 0,5 / 1 / 2 / 5 mm | Celdas en disputa: 202 / 160 / 64 / 0 (con la nota: 0 = sin potencia, no acuerdo) | «Día de lluvia» es una elección que cambia la conclusión |
| 3. Pone a prueba el método (25 s) | Aplica «la corrección que resolvía las disputas» a una serie **SINTÉTICA** con tendencia y sin salto | La corrección le quita el 74,6 % a esa tendencia | Un arreglo que lo resuelve todo también puede borrar lo real |
| 4. Veredicto (20 s) | Abre el veredicto | La tendencia de intensidad de IMERG: no se puede confirmar. Confirmado: la decisión de sequía cambia según el producto (39 %). Abierto: la causa (2013 retirado, 2018 indicio, GOES sin resolver). Botón «Mostrar evidencia» con fuente, periodo, método y límites | Qué se sostiene, qué depende de una elección y qué falta |

Frase final: *«We didn't just look for trends. We tested whether they survive being challenged, including by our own
methods.»*

## 8. Lentes usadas, fila por fila

| Fila | Skill | Qué reveló |
|---|---|---|
| 1. Escena | `thinking-map-territory` | Dos mapas no coincidían con el territorio. «GOES debilitada» se cayó con los contadores (2 % de violaciones, ningún día sin microondas). «Hay que unificar Ribbon» chocó con el código, que ya lo hace. |
| 2. Premisa | `inversion` | Supuesto: «el efecto sorpresa es encontrar al culpable». Invertido: «el efecto sorpresa es ver soltar a un sospechoso», que ya nos pasó dos veces (2013 y GOES). Otro supuesto: «el jurado evalúa nuestros hallazgos»; invertido: «evalúa si nuestro método aguanta», que coincide con el criterio de validez. Murió una inversión: «el jurado tiene tiempo para explorar»; no lo tiene, son 90 s. |
| 3. Ideas | `lateral` → `concept-fan` | ¿De qué es una forma el expediente GOES? De soltar a un sospechoso con una prueba. ¿Y eso? De mostrar que aquí las conclusiones deben aguantar ataques. Desde ahí salieron las ramas umbral, método, ventana y referencia. Se podó «GOES con mejor interfaz» por cosmética. Patrón común: en todas, la conclusión cambia cuando la mano del usuario toca una elección escondida. |
| 3. Ideas | `resource-analysis` (resultado ideal) | «La conclusión frágil se delata sola», con X = resultados ya calculados (umbrales, contraejemplo sintético, ventana de Yuna) y el «Predict Before Reveal» que ya existe en la web. No hace falta ningún dato nuevo. |
| 4. Detalle | `thinking-scientific-method` | Antes de opinar sobre la crítica, la prueba más barata que discrimina: ¿se cumple el subconjunto? No se cumple (2,0 %). La crítica era correcta. |
| 5. En contra | `the-fool` (modo «poner a prueba la evidencia») | La prueba de GOES no aguanta la falsación de su propio supuesto. La objeción más fuerte a E es «¿y qué?», y se responde con la consecuencia confirmada (39 %). `thinking-red-team` no aplica: es para seguridad. |
| 6. Decisión | `thinking-reversibility` | Elegir el recorrido es reversible (todo está calculado); entregar tarde no. Decidir rápido y proteger la entrega. |
| 7. Memorable | `thinking-jobs-to-be-done` | «Cuando una herramienta me da una tendencia significativa, quiero ver qué elección escondida la sostiene, para no decidir sobre un artefacto.» Hoy Giovanni y AppEEARS dan la tendencia sin enseñar sus elecciones. |
| 7. Memorable | `six-hats` (sombrero rojo) | Incomodidad: «hemos retirado tanto que parece que no encontramos nada». Alivio: «nada de lo que enseñamos se cae si pregunta un experto». La incomodidad se atiende con el paso 4, que muestra lo confirmado. |
