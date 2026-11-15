# Cierre científico y encargo al colaborador

15 de noviembre de 2026 · Stellar Horizons · propuesta basada en los archivos locales.

**Actualización posterior:** se ejecutaron las primeras pruebas. Ver `reports_nacional/CONEXIONES_UMBRALES_Y_SESGOS.md` y `results/cierre/resumen.json`. El máximo de 115,5 mm del panel de noviembre de 2024 ocurrió el 8 de noviembre, fuera de la ventana puntuada; dentro de ella el máximo fue 92,3 mm. La discrepancia temporal señalada abajo ya tiene esa explicación concreta. Las hipótesis se conservan como registro del encargo inicial.

Este documento conecta resultados existentes y define pruebas pendientes. No contiene nuevos resultados experimentales ni una revisión actualizada de competidores. El chat «Contexto NASA Space Apps» se recuperó como antecedente; sus comparaciones competitivas requieren verificación externa antes de publicarse.

## Decisión propuesta

Concentrar el cierre en una pregunta demostrable: **¿qué evidencia cambia una conclusión sobre el agua en República Dominicana, y qué sigue sin poder resolverse?**

Mantener visible el recorrido del reto: variable NASA → región → serie → tasa de cambio → incertidumbre. Añadir un expediente donde el usuario vea una afirmación inicial, cambie una condición y observe qué ocurre con el veredicto. El valor debe estar en la prueba reproducible y en la decisión de monitoreo que permite tomar.

La decisión práctica inicial es **qué dato revisar o medir después**. No hay validación suficiente para recomendar evacuaciones o presentar un sistema operativo de alertas.

## Qué ya permite afirmar el repositorio

| Conexión | Evidencia local | Alcance defendible |
|---|---|---|
| Tendencias → desacuerdo entre productos | `reports_nacional/TENDENCIAS_P0.md`: 0 combinaciones celda-índice robustas en los 21 índices anuales; al incluir periodos estacionales sí aparecen 2 combinaciones celda-índice-periodo | Falta acuerdo significativo anual bajo el criterio implementado. No equivale a ausencia de cambio climático ni a ausencia de tendencias individuales. |
| Elección de fuente → clasificación de sequía | `reports_nacional/AUDITORIA_CONFIANZA.md`: 2836 de 3111 provincia-meses con alguna alarma no tienen unanimidad entre cuatro productos; 91,2 % condicional y 31,0 % sobre todos los provincia-meses evaluados | Sensibilidad de la clasificación a la fuente. El 91 % no es tasa de error ni porcentaje de desacuerdo sobre todos los meses. |
| Fuentes compartidas → falsa sensación de corroboración | `results/auditoria/procedencia.json` y `reports_nacional/TESTIGOS_E_HIPOTESIS.md` | El acuerdo entre modelos/productos con insumos comunes no constituye validación independiente. Tampoco demuestra que sean equivalentes o inútiles. |
| Memoria del suelo → memoria de su lluvia de entrada | `reports_nacional/TESTIGOS_E_HIPOTESIS.md`: el efecto del suelo se debilita al controlar SPI de la lluvia que fuerza GLDAS | Hay asociación residual en varias especificaciones; no está identificada una causa física separada del modelo y de su forzamiento. |
| Testigo independiente → territorio observable | Mismo informe: 440 de 596 píxeles terrestres SMAP L3 sin retrieval recomendado durante el periodo; cero en ambos pares principales | La posibilidad de comprobar una conclusión cambia por lugar y calidad del dato. Una rejilla de 9 km no equivale a observaciones independientes a esa escala. |
| Lluvia → agua observada → cuenca | `reports_nacional/CASO_YUNA.md`, MODIS MCDWD y delimitación HydroSHEDS | Se puede contrastar el disparador con agua clasificada como inundación y con conectividad territorial. Nubes, ventanas compuestas y posibles falsos positivos deben acompañar el resultado. |
| Antecedente húmedo → mejora del disparador | `results/yuna/web/backtest.json`: en prueba, regla base y variantes de umbral rebajado tienen POD 0,875 y CSI 0,149 | No se observó mejora en esas reglas y esa muestra. No prueba que el estado antecedente carezca de importancia hidrológica. SMAP L4 está etiquetado en muestra. |

## Pista que debe cerrarse antes de escoger el caso protagonista

**Noviembre de 2024 contiene una discrepancia de presentación y asociación temporal pendiente de resolver.**

- `results/yuna/backtest_verificacion_mcdwd.csv`: todos los disparadores aparecen como `False`.
- `results/yuna/paneles_eventos.csv`: `r48_maxcelda_yuna = 115.47499465942383` mm, por encima de 100; catálogo del 11 al 20 de noviembre; máximo MCDWD el 21, de 4,239 km² para la cuenca.
- `earthmemory/yuna/analisis.py`, función `paneles`: resumen de lluvia desde inicio − 3 días hasta fin.
- La función `puntuar`: acierto desde inicio − 2 días hasta fin. Para asociar episodios a falsas alarmas permite además fin + 2 días. Las dos cuentas no usan exactamente el mismo criterio temporal.

Esto **no demuestra** un fallo del cálculo ni que el umbral se superara dentro de la ventana puntuada. El máximo podría pertenecer al día adicional del panel; hay que localizarlo en la serie diaria. Tampoco se puede fechar el inicio de la inundación con el día de máximo de un compuesto MODIS.

**Entrega requerida:** una tabla por día desde inicio − 5 hasta fin + 5 con máximo de celda IMERG en 48 h, media de cuenca, antecedente, resultado de cada regla, observabilidad MODIS, capa/compuesto, agua anómala y pertenencia a cada ventana. Adjuntar el motivo exacto del fallo y repetir la sensibilidad con ventanas declaradas de antemano para todos los eventos. No ampliar solo este evento para convertirlo en acierto.

Si el problema es de fechas, la historia pasa a ser «el veredicto depende de cómo asociamos lluvia e inundación». Si persiste con fechas coherentes, investigar lluvia omitida, conectividad o duración. No adjudicarlo aún a Hatillo ni al suelo.

## Hipótesis prioritarias y cómo intentar romperlas

### H1 · Parte de las tendencias opuestas nace en el reparto diario de la lluvia

**Pistas conectadas:** IMERG y CHIRPS tienen lluvia media parecida, pero difieren en días húmedos e intensidad; SDII divide lluvia de días húmedos por su número. La auditoría documenta desagregación diaria de CHIRPS v2. Intensidad y frecuencia no son dos confirmaciones independientes de un cambio.

**Predicción:** el desacuerdo se concentra alrededor del umbral de día húmedo o disminuye al sumar 5 días. Comparar totales, frecuencia e intensidad, conservando idéntica rejilla, periodo y máscara.

**Prueba mínima:** umbrales de sensibilidad 0,5/1/2/5 mm, con 1 mm como definición principal; agregación en bloques de 5 días con diferentes orígenes para evitar un resultado dependiente del calendario; mostrar cuánto cambia el desacuerdo y su incertidumbre. Usar estaciones con circularidad declarada como contraste adicional.

**Se debilita si:** las tendencias opuestas persisten para cantidades alejadas de los umbrales y acumulados de varios días. Que disminuyan apoyaría una explicación por escala/reparto; por sí solo no identifica qué algoritmo falla ni cuál producto es verdadero.

**Prioridad:** primera prueba nueva, después de cerrar la cronología del Yuna. Código relacionado: `earthmemory/tendencias/indices.py`, `motor.py`, `datos.py`.

### H2 · Los regímenes meteorológicos explican una parte reproducible del desacuerdo residual

**Pistas:** quedan 28 de 50 episodios sin explicar después de controles de escala, tiempo y umbral; la asociación simple con elevación pierde apoyo al conservar estructura espacial (p toroidal 0,207).

**Predicción:** la diferencia entre fuentes depende de un régimen definido con datos externos, y esa relación se mantiene en años reservados.

**Prueba:** empezar por temporada; después ciclones con trayectorias/fechas oficiales y viento sobre el relieve con campos vectoriales. Barlovento/sotavento exige viento del episodio; la orientación de una ladera sola no basta. Controlar cantidad de lluvia, altura, costa y cambios de sensores. Comparar modelos anidados con validación temporal y espacial por bloques. No añadir todos los predictores a la vez.

**Se debilita si:** la mejora desaparece fuera de muestra o al controlar la cantidad de lluvia. Si no hay viento ni catálogo de ciclones preparado, dejar esa extensión pendiente. ENSO es contexto de gran escala; una asociación no atribuye el mecanismo de un aguacero local.

### H3 · La señal estacional de «volvió la lluvia, siguió seco el suelo» mezcla clima y definición de retorno

**Pista:** la auditoría cuenta contradicción A en 9/230 retornos de AMJJ, 51/290 de DEFM y 36/194 de ASON. Esas temporadas difieren de las del motor de tendencias (dic–abr, may–jul, ago–nov): no cruzar sus porcentajes como si fueran grupos idénticos.

**Prueba:** definición común de temporada; mismos episodios y periodo; repetir con lluvia IMERG y con el forzante GLDAS, controlando sequía previa, lluvia acumulada y estado inicial. Reportar denominadores y efectos, con incertidumbre por bloques de años y territorio. Añadir demanda evaporativa solo como extensión predefinida.

**Se debilita si:** la diferencia se explica por fecha de retorno, selección de episodios o lluvia del propio modelo. Mientras la respuesta sea GLDAS, el resultado describe suelo modelado.

### H4 · La falta de observación es territorialmente selectiva

**Pistas:** SMAP L3 falla como testigo en nuestros lugares boscosos/urbanos; MODIS queda limitado por nubes en determinados días.

**Prueba:** mapa de cobertura de calidad por producto, temporada y paisaje; comparar distribución de sitios observables y no observables, sin confundir las máscaras de suelo y de agua. Evaluar coincidencia con los lugares donde las fuentes discrepan y repetir con máscaras alternativas razonables.

**Resultado útil aunque no aparezca una relación:** identificar dónde una conclusión necesita otro instrumento. Un radar para agua inundada no sustituye una medida de humedad de raíces.

**Decisión:** seleccionar sitios candidatos a nueva medición considerando incertidumbre, observabilidad, conectividad y exposición documentada. Sin costes y validación externa, hablar de candidatos, no de emplazamientos óptimos.

### H5 · La ubicación de la lluvia dentro de la cuenca aporta información que pierde el promedio

**Pistas:** aproximadamente 23 % del área del Yuna pasa por Hatillo; el resto llega por otras rutas. Es una fracción de área, no una fracción medida del caudal. El agua observada en la llanura no identifica por sí sola su origen aguas arriba.

**Prueba:** comparar lluvia de cuenca con lluvia por Alto Hatillo/Camú/Bajo Yuna, con retardos definidos en calibración. Usar los mismos eventos, máscaras y ventanas. Reportar diferencias de habilidad e IC; el catálogo es pequeño e incompleto. Ninguna ausencia en prensa debe convertirse automáticamente en «no hubo inundación».

**Se debilita si:** no mejora fuera de muestra o cambia con uno o dos eventos. Sin niveles y descargas de Hatillo, dejar sin resolver su contribución causal. GEOGLOWS local queda excluido mientras los tramos no correspondan al cauce principal.

## Secuencia de cierre y entregables

1. **Congelar afirmaciones:** separar observado, modelado, asociación, hipótesis y no comprobable; copiar cada cifra de su resultado y conservar denominador, periodo y versión.
2. **Resolver noviembre de 2024:** cronología diaria y ventanas coherentes; si sigue ambiguo, escoger otro evento para la demo y mostrar este como pendiente.
3. **Ejecutar H1:** prueba acotada con datos ya descargados; entregar magnitudes, incertidumbre y casos que contradicen la explicación.
4. **Empaquetar un expediente completo:** pregunta → afirmación inicial → fuente/procedencia → objeción → prueba calculada → veredicto revisado → siguiente dato necesario. Una conclusión que resiste una prueba también cuenta.
5. **Continuar H2/H3 solo si pueden producir una comparación interpretable.** No bloquear la entrega por reunir variables nuevas. H4 puede convertir los límites ya medidos en una decisión de monitoreo; H5 queda condicionado a tamaño muestral y calidad.

Para cada prueba nueva: CSV/JSON con parámetros, periodo, máscara, n, estimación e IC; figura antes/después; ruta de los insumos y comando reproducible en Docker. Registrar variantes exploradas; fijar una comparación principal y corregir multiplicidad cuando corresponda. Elegir una historia después de mirar los datos no la convierte en validación confirmatoria.

Los porcentajes existentes se citaron desde los informes; no se recalcularon para este documento. No modificar silenciosamente sus generadores ni sus resultados.

## Encargo listo para pasar al colaborador

> Cierra primero la cronología de noviembre de 2024: el panel tiene 115,5 mm/48 h pero el backtest lo marca como fallo; panel y puntuación usan inicio −3 e inicio −2 respectivamente, y MODIS alcanza su máximo el día posterior al fin del catálogo. Localiza el máximo de lluvia, muestra las ventanas y explica el veredicto sin ajustarlo a conveniencia. Luego prueba si las tendencias opuestas IMERG–CHIRPS dependen de días próximos al umbral y de la agregación diaria frente a 5 días. Entrega un expediente reproducible que muestre qué conclusión cambia y qué dato sigue faltando. Mantén «memoria del suelo», «alisios» y «efecto de Hatillo» como hipótesis hasta que una prueba específica las sostenga. Usa Docker para cómputo y no publiques ni despliegues.

## Fuentes y verificaciones de esta revisión

- Informes locales: `TENDENCIAS_P0.md`, `AUDITORIA_CONFIANZA.md`, `TESTIGOS_E_HIPOTESIS.md`, `CASO_YUNA.md`; resultados y funciones citados arriba.
- Investigación previa localizada y consultada parcialmente: `../research_notes/Evidence Intelligence/verificacion_y_diferenciacion.md`, `../research_notes/Inundaciones y memoria del suelo RD/ciencia_humedad_antecedente.md`, `../research_notes/Earth Memory/notas.md`. Las notas previas pueden haber sido corregidas por auditorías posteriores: priorizar producto y versión exactos.
- [NASA IMERG](https://gpm.nasa.gov/data/imerg): consultado en esta revisión; confirma combinación de estimaciones, continuidad TRMM/GPM y distinción Early/Late/Final. Un resultado retrospectivo con Final no es automáticamente un pronóstico operativo.
- [NSIDC SPL3SMP_E V006](https://nsidc.org/data/spl3smp_e/versions/6): consultado; confirma producto diario de recuperación radiométrica, interpolación y rejilla de 9 km. Los recuentos de calidad dominicanos proceden del análisis local.
- El README oficial de desagregación diaria de CHIRPS v2 no fue accesible con la herramienta web en esta revisión; su mecanismo se cita desde la auditoría local, y debe reabrirse antes de presentarlo como verificación externa nueva.

No afirmar superioridad sobre todos los equipos ni prometer un premio. La propuesta competitiva pendiente de demostrar es que una objeción produce una prueba reproducible y una revisión explícita del veredicto.
