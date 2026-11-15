# Qué falta para defender Stellar Horizons

Revisión del repositorio del 15-nov-2026, posterior a los commits `3ac628d` y `3c683d8`. No modifica las investigaciones ni la interfaz de otros chats. La evidencia de comprobación está en `results/preparacion/REVISION_DEFENSA.json`; el repositorio sigue avanzando, por lo que los recuentos son una instantánea.

## Dictamen

Hay una propuesta defendible y un backend funcional. El siguiente salto no consiste en sumar capas o hipótesis: consiste en demostrar una decisión municipal concreta, el valor añadido frente a consultar las fuentes por separado y la integridad de la reproducción temporal. No asignamos una probabilidad de ganar ni puntuaciones de jurado a partir de una autoevaluación.

Los avances nuevos son útiles: comparar trayectorias oficiales históricas del NHC abre la vía de prealerta por ciclones; el análisis ciclones–déficit evita convertir una conexión plausible en una regla causal. Ambos necesitan una formulación más precisa antes de presentarse como capacidad preventiva.

## Revisión de la evaluación recibida

| Criterio | Qué sostiene el repositorio | Qué falta de mayor valor |
|---|---|---|
| Impacto | Problema territorial relevante y expedientes reproducibles; hay candidatos de señal temprana ciclónica. | Una tarea real revisada por el usuario previsto y evidencia del cambio que aporta el expediente. Una carta acredita interés; por sí sola no demuestra eficacia. |
| Creatividad | La combinación de auditoría, dependencia entre fuentes y expediente municipal puede diferenciar la aplicación. | Mostrar el valor frente al flujo habitual y herramientas existentes. No afirmar que contrastar productos es una técnica nunca inventada. |
| Validez | Pruebas sintéticas, retiradas explícitas y resultados trazables. | Corregir tiempos de NHC, revisar la selección de tormentas, precisar emparejamientos y separar muestras. No está en un «techo» inamovible. |
| Relevancia | IMERG y su contraste responden al reto de tendencias; el contexto ayuda a usar sus resultados. | Mostrar en un recorrido verificable variable NASA, territorio, serie, tasa y significancia; después, su consecuencia para preparación. Enumerar NASA datasets no sustituye ese vínculo. |
| Presentación | No está incluida en la tabla recibida ni se ha evaluado aquí una entrega final. | Una promesa clara, un caso comprensible, una diferencia observable y cifras trazables. |

La [guía oficial de evaluación de 2025](https://spaceapps-v2-staging.s3.amazonaws.com/media/documents/Final_Space_Apps_2025_Judging_Guidelines_for_web.pdf) incluye Presentación y evalúa también factibilidad/usabilidad dentro de Validez; define Best Use of Technology por innovación tecnológica. Se usa como referencia, no como verificación de las instrucciones finales de 2026. Las notas 3,5/4/4/4,5 son una opinión orientativa, no una medición reproducible ni un resultado oficial.

## Tres correcciones antes de vender cifras

### 1. Los 40–106 h aún no son anticipación operacional de inundación

La regla nueva identifica cuándo una trayectoria OFCL pone un centro ciclónico pronosticado dentro de 200 km de un punto de referencia del Yuna, entre 12 y 120 horas de pronóstico. No pronostica lluvia, caudal ni una inundación municipal. Cercanía en trayectoria real tampoco demuestra que el ciclón causara cada inundación.

El código `earthmemory/tropical/ciclones_anticipacion.py` interpreta `p[2]` de ATCF como `emision`. La documentación de [NCAR TCGP](https://verif.rap.ucar.edu/jntweb/hurricanes-beta/guide/) distingue ciclo sinóptico y publicación del pronóstico oficial, normalmente tres horas posterior. Se verificaron además dos boletines originales:

| Caso | Hora usada por el CSV | Publicación del boletín | Margen del CSV | Margen desde publicación, con el mismo inicio supuesto |
|---|---|---|---:|---:|
| María, aviso 2 | 16-sep-2017 18 UTC | 16-sep-2017 21 UTC | 106 h | 103 h |
| Fiona, aviso 1 | 14-sep-2022 12 UTC | 14-sep-2022 15 UTC | 88 h | 85 h |

Fuentes: [María](https://www.nhc.noaa.gov/archive/2017/al15/al152017.fstadv.002.shtml), [Fiona](https://www.nhc.noaa.gov/archive/2022/al07/al072022.fstadv.001.shtml), copias y hashes en `references/revision_defensa/`. **Solo se comprobaron estos dos ejemplos de emisión.** No se ha regenerado la tabla completa ni se propone restar tres horas ciegamente a todos los avisos.

El inicio de inundación es 04 UTC de la fecha del catálogo por convención. La hora real no está establecida; la fecha de prensa no garantiza un límite temporal inferior. Incluso los 103/85 h corregidos son márgenes respecto a esa convención, no horas operacionales certificadas. No hay contradicción con el resultado anterior de lluvia observada: son señales y muestras distintas.

**Frase válida ahora:** «Los archivos históricos del NHC muestran oportunidades de prealerta ciclónica anteriores a algunas inundaciones del catálogo. Estamos distinguiendo la hora de emisión, la incertidumbre del inicio y el coste de falsas señales antes de afirmar anticipación operacional».

### 2. El coste de la prealerta aún está condicionado por la selección

El script solo descarga pronósticos de tormentas cuya trayectoria **real** pasó a menos de 800 km. Esa selección retrospectiva puede excluir tormentas pronosticadas cerca que luego se alejaron: justo casos relevantes para evaluar señales no confirmadas. Los 33 casos no representan necesariamente el universo de prealertas.

Además, el emparejamiento temporal permite asociar cualquier inicio del catálogo desde un día antes de la primera señal hasta cinco días después del último ciclo de la tormenta. Hay que revisar por separado correspondencia temporal y atribución al sistema. Los 5/33 emparejamientos no equivalen a precisión operacional de un predictor de inundación.

**Qué falta comprobar:** pronósticos de todo el universo elegible definido sin usar la trayectoria futura; disponibilidad completa por año; episodios de señal con cierre explícito; eventos y no eventos; emparejamiento predefinido y revisión de los casos discordantes. El catálogo incompleto impide declarar falsa toda señal no emparejada.

### 3. «26 predicciones» no es un inventario auditado

La tabla de conclusiones alcanza la fila 26, pero las predicciones están en archivos separados. El recuento de esta revisión encuentra **31 entradas en nueve registros**, más **tres PR1–PR3 en un registro de Puerto Rico que solo tenía predicciones al revisarse**: 34 definiciones locales en total en ese momento. Algunas corresponden a pruebas retiradas o distintas versiones de una misma pregunta.

No se sustituyen «26» por «34» como argumento de calidad. Falta un registro único con identificador, enunciado, fecha, hash de datos/código, dependencia de análisis anteriores, resultado, estado y razón de retirada. Las marcas locales no acreditan por sí solas un preregistro externo ni ausencia de exposición previa a los resultados.

**Frase válida ahora:** «Registramos predicciones locales antes de ejecutar sus pruebas y publicamos también fallos y retiradas; cada afirmación del proyecto enlaza a su evidencia». Cuando no pueda comprobarse el orden temporal de una prueba, no se afirma que fue anterior.

## Conclusiones listas para escribir

1. **Problema:** «Prepararse requiere distinguir cambios históricos, señales próximas y datos contradictorios. Un acumulado municipal aislado no describe el agua que llega desde toda una cuenca».
2. **Solución:** «Stellar Horizons construye expedientes municipales que conectan datos NASA, pronósticos y mediciones locales para mostrar qué requiere atención, qué lo respalda y qué verificar después».
3. **Hallazgo histórico:** «IMERG y CHIRPS discrepan en el cambio de frecuencia de días húmedos en RD. La comparación con otras fuentes obliga a tratar algunas tendencias de intensidad y rachas con cautela; la causa sigue abierta». No convertirlo en demostración de que la lluvia real no cambió.
4. **Conexión territorial:** «En el Yuna, Hatillo no controla toda la cuenca y el Camú aporta aguas abajo. Nuestro expediente identifica esos datos faltantes antes de convertir la lluvia de un punto en una conclusión sobre crecidas».
5. **Ciclones:** «Separamos vigilancia ciclónica de evaluación de inundación. Un pronóstico de trayectoria aporta contexto temprano, pero necesita lluvia, respuesta de cuenca y exposición para sostener una decisión local». [NOAA distingue trayectoria del centro e impactos](https://www.noaa.gov/understand-forecast-information).
6. **Ciclones y déficit:** «La comparación exploratoria no respaldó que temporadas con menos lluvia en días de ciclón tuvieran más déficit posterior». El 11 % es lluvia **en días clasificados por cercanía**, no atribución física de toda esa lluvia al ciclón. El 16 % frente a 21 % es una asociación descriptiva, no prueba de que el ciclón elimina sequías.
7. **Aporte tecnológico:** «Al retirar una fuente, el motor recalcula el respaldo y explica el cambio. Conserva coordenadas, fechas, versiones y datos faltantes para que otra persona pueda reproducir el expediente».
8. **Estado del producto:** «El backend funciona; falta validar con responsables municipales si mejora una tarea de preparación y comprobar habilidad operacional antes de prometer alertas o daños evitados».

**Propuesta en inglés:** “Stellar Horizons turns NASA data, forecasts and local measurements into traceable municipal investigations: what needs attention, what supports it, and what to verify before preparing a response.”

## Qué investigar o verificar primero

### Prioridad 0: cerrar lo que podría invalidar la promesa

- Corregir la interpretación temporal NHC y comprobar los boletines correspondientes de todos los casos usados en una cifra pública. Preservar resultados anteriores como superados; no borrar la trazabilidad.
- Revisar universo y emparejamiento de tormentas antes de usar 33/5 como coste de prealerta. Separar n=14 del catálogo, seis coincidencias ciclónicas, ocho eventos de prueba de lluvia y 23 temporadas de la comparación ciclones–déficit: no son una muestra única.
- Revisar en `ciclones_sequia.py` el dominio espacial (media de toda la caja versus las 442 celdas RD), el calendario bisiesto del rango por día del año y la diferencia entre lluvia en días próximos y lluvia atribuida. No usar ese resultado como regla predictiva o causal.

### Prioridad 1: probar valor para una persona

- Realizar una pequeña prueba de tarea con un técnico municipal o de un organismo competente: el mismo caso con fuentes habituales y con el expediente, alternando el orden. No se han enviado mensajes ni solicitado avales en esta revisión.
- Medir si identifica el intervalo, distingue señal de confirmación, encuentra datos críticos faltantes —Camú/río/Hatillo/exposición según el caso— y evita concluir «sin riesgo» por ausencia de tendencia o cruce de umbral. Registrar tiempo, errores, dudas y cambios de decisión. Un piloto cualitativo no demuestra reducción de daños.
- Preferir evidencia concreta de uso a una carta genérica. Si existe interés institucional, dejar claro qué se probó, quién participó y qué no se avala; una carta no convierte el prototipo en servicio oficial.

### Prioridad 1: demostrar el valor incremental de la tecnología

- Reproducir un expediente con entradas fechadas, salida del motor, retirada de una fuente y exportación con las mismas cifras/hashes. Si una parte solo está calculada en un CSV de investigación —como el nuevo análisis NHC—, no decir que ya está integrada operativamente en el backend.
- Comparar contra el flujo real de consultar un boletín y un mapa de lluvia: qué contradicción detecta, qué información faltante hace visible y qué paso ahorra. El valor no es «tenemos más capas» ni competir con la capacidad de pronóstico del NHC.
- Mostrar NASA como parte de la decisión histórica y su incertidumbre. MERRA-2 descartado es una lección de auditoría; SMAP/GLDAS o MODIS solo se muestran si apoyan una afirmación concreta, con su calidad y límites.

### Prioridad 2: cerrar la comunicación

- Un usuario, una decisión y un caso principal. Las demás investigaciones respaldan las preguntas del jurado.
- Una tabla final de afirmación → evidencia → alcance → limitación → frase permitida; sin mezclar ventanas de tiempo ni muestras.
- Contrastar las condiciones de entrega de 2026 con la convocatoria vigente. Este informe solo pudo verificar la guía de evaluación de 2025 como referencia.

## Respuestas breves al jurado

**¿Qué mejora frente a un mapa meteorológico?** Hace explícito qué fuentes sostienen cada afirmación, cuáles comparten insumos y qué falta comprobar en ese territorio; permite reproducir el cambio al retirar evidencia. El beneficio de uso debe medirse con responsables reales.

**¿Predice inundaciones con cuatro días de antelación?** No está demostrado. Hay señales históricas de trayectoria ciclónica previas a algunos eventos; faltan las verificaciones temporales y de habilidad para convertirlas en una promesa de alerta.

**¿Por qué no basta con exigir dos fuentes?** Pueden compartir insumos, equivocarse juntas o llegar tarde. Confirmar también puede perder eventos: en el test histórico de lluvia, 7/8 pasa a 6/8 mientras los episodios no emparejados bajan de 39 a 16.

**¿Necesitáis resolver GOES para que el producto tenga sentido?** No. La herramienta debe representar esa incertidumbre. Resolver la causa es una investigación separada; no es condición para verificar señales y datos faltantes.

**¿Qué probaríais después del hackathon?** Una tarea de preparación con usuario real, captura prospectiva y evaluación de señales con tiempos y costes relevantes. No aumentar el número de hipótesis para sustituir esas pruebas.
