# Stellar Horizons · pitch dominicano de cinco minutos

Guion para decirlo con voz propia ante el jurado local. La llamada inicial es una escena imaginada, no un testimonio. Las notas entre corchetes no se leen. Los tiempos requieren ensayo; no se modifican interfaces.

## 0:00–0:35 · Que el jurado entre en la escena

> Imagínense esta llamada desde Villa Riva:
>
> «Está cayendo un aguacero. ¿Cómo está la cosa por arriba? ¿Nos vamos preparando?»
>
> [Pausa. Mirar al jurado.]
>
> En el Bajo Yuna, esa pregunta tiene que ver con familias, caminos y comunidades que pueden quedar aisladas.
>
> Para responder, hay que juntar el pronóstico, la lluvia y lo que pasa en la cuenca.
>
> Ahí entra Stellar Horizons: un detective del agua que ayuda a investigar las señales y a saber qué falta comprobar para preparar nuestro territorio.

[Mapa del Yuna. No simular una llamada real ni una alerta vigente.]

## 0:35–1:15 · Qué hacemos, dicho claro

> Nuestro usuario es el técnico municipal que tiene que revisar la situación con los organismos responsables.
>
> Escoge su territorio y abre un expediente: qué merece atención, de dónde sale esa señal y qué debe verificar después.
>
> Trabajamos con tendencias de la NASA, pronósticos y mediciones locales. Para la historia cubrimos las treinta y dos provincias, con veintiún índices de lluvia entre 2001 y 2024.
>
> Podemos ver qué cambia, dónde, cuánto y si ese cambio es significativo.
>
> Y hacemos otra pregunta: ¿la conclusión se sostiene cuando la ponemos a prueba con otras fuentes?

[Una tendencia y el expediente. Distinguir cobertura provincial histórica de cuatro puntos piloto.]

## 1:15–2:10 · Miren lo que encontramos

> Miren lo que pasó cuando hicimos esa comparación.
>
> En quince áreas que cubren el país, IMERG baja unos cinco puntos porcentuales en frecuencia de días lluviosos después de febrero de 2018. CHIRPS cambia muy poco. MERRA-2 sube casi nueve.
>
> Mismo territorio. Misma pregunta. Tres respuestas.
>
> Fuimos a comprobarlo en Puerto Rico, con más pluviómetros. En dieciocho de diecinueve estaciones, IMERG pierde más días que la medición en tierra. La diferencia crece al incluir lluvia muy ligera.
>
> Ojo con esto: si contamos menos días húmedos, también puede cambiar la intensidad calculada y la duración de las rachas secas.
>
> Todavía investigamos la causa. Incluso MERRA-2 mostró un cambio propio y quedó descartado como testigo fiable en esa prueba.
>
> Eso es trabajar como detectives: también hay que revisar al testigo.

[Comparación y Puerto Rico. Son medianas antes/después; puntos porcentuales no equivalen a porcentaje de reducción del volumen.]

## 2:10–3:15 · Qué cambia para el municipio

> Ahora, llevemos eso al Yuna.
>
> Una tendencia histórica ayuda a planificar. Para los próximos días hacen falta pronósticos, mediciones y contexto.
>
> Puede llover poco en Villa Riva y estar cayendo agua más arriba. Hatillo regula parte de la cuenca, y el Camú entra aguas abajo de la presa. Nuestro expediente pone esas piezas y los datos faltantes a la vista.
>
> Los pronósticos del NHC aportan contexto temprano de ciclones. Una crecida exige revisar además lluvia, río y exposición.
>
> Probamos una regla histórica en ocho inundaciones. Pedir coincidencia entre productos bajó los episodios sin evento catalogado de treinta y nueve a dieciséis. Pero las detecciones bajaron de siete a seis.
>
> Hay que ver ese coste antes de adoptar una regla.
>
> Y cuando falta lluvia, el expediente pide comprobar cómo andan el almacenamiento y el suministro.

[Cuenca y tareas. La comparación histórica con CHIRPS no constituye una alerta operativa ni una regla de movilización.]

## 3:15–4:05 · La diferencia se puede demostrar

> Aquí está el trabajo tecnológico.
>
> El motor guarda ubicaciones, fechas y relaciones entre las fuentes. Comprueba qué datos estaban disponibles y cuáles llegaron después.
>
> Dos productos pueden compartir información; su coincidencia no garantiza independencia.
>
> [Retirar una fuente.]
>
> Quitamos esta fuente. El expediente vuelve a calcular qué respaldo queda y explica qué cambió.
>
> Si añadimos una medición local, conserva quién la aportó y aparece sin verificar.
>
> Y podemos descargar el expediente con sus cifras y fuentes para que otra persona lo revise.
>
> Esa es la diferencia que queremos demostrar: que el técnico pueda entender y revisar cómo se llegó a cada conclusión.

[Acción funcional de retirada y exportación. Si la interfaz no la implementa, mostrar entrada/salida del backend. Retirar una fuente puede cambiar cobertura sin cambiar la clasificación.]

## 4:05–4:35 · Hasta dónde hemos llegado

> El backend funciona en cuatro territorios piloto. Hemos probado sus reglas, publicado hipótesis que fallaron y retirado conclusiones que no resistieron la revisión.
>
> Ahora toca comprobar con técnicos municipales si el expediente les ayuda a encontrar antes la información crítica que falta.
>
> Tenemos que medir esa utilidad. Y evaluar por separado la capacidad de anticipar inundaciones.

[Resultados verificables. No atribuir uso real, aval institucional ni daños evitados.]

## 4:35–5:00 · Volver a nuestra gente

> Volvamos a aquella llamada: «¿Cómo está la cosa por arriba? ¿Nos vamos preparando?»
>
> Trabajamos para que esa respuesta tenga evidencia, sus límites claros y una próxima comprobación.
>
> Porque cuando el Yuna crece, lo que está en juego son nuestras comunidades.
>
> **Stellar Horizons: investigar el agua para preparar a nuestra gente.**

---

## Preguntas del jurado y respuestas para practicar

### Fuentes: estas hay que sabérselas

**1. ¿Cuáles son sus fuentes principales?**

Para tendencias: NASA GPM IMERG V07 Final y CHIRPS v2.0. Para contrastes: ERA5 y pluviómetros GHCN-Daily. Para próximos días: ECMWF y NOAA GFS mediante Open-Meteo. Para ciclones: IBTrACS histórico y pronósticos oficiales NHC OFCL. Cada uno cumple una función distinta.

**2. ¿Cuáles son de la NASA?**

IMERG es nuestro producto principal de lluvia. MERRA-2, consultado mediante NASA POWER, se usó en la auditoría y se descartó como testigo fiable para ese contraste. GLDAS, SMAP y MODIS se usaron en investigaciones complementarias de suelo y agua; no todos respaldan la misma conclusión ni todos intervienen en cada expediente.

**3. ¿CHIRPS y ERA5 también son NASA?**

CHIRPS es un producto del Climate Hazards Center de UC Santa Barbara con colaboración del USGS. ERA5 es un reanálisis de ECMWF/Copernicus. Son fuentes externas que contrastamos con NASA. No presentamos todo lo integrado como dato NASA.

**4. ¿Qué diferencia hay entre satélite, pluviómetro, reanálisis y pronóstico?**

El pluviómetro mide en un punto; el producto satelital estima lluvia sobre una celda. El reanálisis reconstruye el estado pasado usando modelo y observaciones. El pronóstico estima lo que puede ocurrir después. Se etiquetan por separado porque no tienen el mismo significado ni disponibilidad.

**5. ¿Por qué usan Open-Meteo? ¿Es el modelo?**

Es la vía de acceso. Consultamos por separado los modelos ECMWF y GFS, conservando sus nombres y coordenadas devueltas. Para la referencia de déficit pedimos ERA5 explícitamente. Open-Meteo no convierte esas fuentes en un modelo único.

**6. ¿Son realmente independientes sus testigos?**

No todos. IMERG utiliza ERA5 como auxiliar y ajuste mensual con pluviómetros; las redes pueden compartir estaciones. Documentamos esas dependencias y no convertimos coincidencia en votos independientes ni en una probabilidad de confianza.

**7. ¿Qué resolución y periodo tienen?**

El análisis histórico principal cubre 2001–2024. IMERG tiene rejilla nativa de 0,1 grados; CHIRPS v2.0, 0,05 grados, agregado para las comparaciones comunes. Los modelos tienen otras celdas y resoluciones, conservadas en cada registro. Un punto piloto no representa todo el municipio.

**8. ¿Cómo sabemos de dónde salió una cifra?**

El expediente identifica producto, ubicación solicitada y devuelta, periodo, captura, calidad y procedencia. El paquete y el motor tienen hashes. La exportación permite revisar los números y reproducir las reglas. Un hash identifica contenido; no certifica que el fenómeno esté correctamente medido.

### Ciencia: donde pueden apretar

**9. ¿Están diciendo que IMERG está mal?**

Encontramos una discrepancia temporal que exige cautela para ciertos indicadores y umbrales en los lugares estudiados. No invalida todos los usos de IMERG ni demuestra una causa específica.

**10. ¿Cinco puntos porcentuales significa 5 % menos lluvia?**

No. Por ejemplo, pasar de 30 a 25 días húmedos por cada cien días del calendario es una caída de cinco puntos porcentuales. No dice cuánto cambió el volumen de lluvia.

**11. ¿Puerto Rico prueba que la causa es el satélite?**

Refuerza que la discrepancia merece investigación fuera de RD. No identifica por sí solo el mecanismo ni elimina diferencias de representatividad, horarios, insumos compartidos o meteorología real.

**12. ¿Saben que GOES-16 causó el cambio?**

No. GOES es una hipótesis pendiente, junto con otros cambios de sensores, procesamiento y referencias. La coincidencia de fechas no atribuye una causa.

**13. ¿Si dos fuentes coinciden, ya sabemos la verdad?**

No. Pueden compartir insumos y errores. La coincidencia es evidencia que se interpreta junto con calidad, tiempo, escala y mediciones disponibles.

**14. ¿Han demostrado que dejó de cambiar la lluvia real?**

No. Falta cobertura terrestre suficiente para esa afirmación. Medimos diferencias entre estimaciones y analizamos la solidez de determinadas tendencias.

**15. ¿Registraron las predicciones de verdad?**

Conservamos registros locales de predicciones y sus fechas, además de resultados fallidos y retiradas. Eso no equivale a preregistro externo. Solo afirmamos registro previo cuando su secuencia puede verificarse.

### Prevención e impacto

**16. ¿Predicen inundaciones?**

Tenemos un prototipo de apoyo a preparación, con vigilancia de lluvia prevista y seguimiento de déficit. Falta validar habilidad operacional de inundación y utilidad con responsables reales.

**17. ¿Y las 40–106 horas que aparecieron en sus informes?**

Son márgenes de una regla histórica de cercanía de trayectoria. La revisión detectó diferencias entre hora base y publicación del boletín; además, el inicio real de inundación tiene incertidumbre. No las presentamos como horas de alerta operacional demostradas.

**18. ¿Qué significa bajar de 39 a 16?**

Son episodios sin evento emparejado en el catálogo, en una prueba histórica 2016–2024. Las detecciones también bajaron de 7/8 a 6/8. El catálogo puede omitir inundaciones y CHIRPS llega tarde; no es una mejora operacional ya demostrada.

**19. ¿Entonces exigirían dos satélites antes de movilizar?**

No adoptamos esa regla como instrucción operacional. Confirmar tiene costes y puede perder eventos. Se necesita evaluación con responsables competentes, disponibilidad real y un criterio de decisión adecuado.

**20. ¿Para qué le sirve hoy a un ayuntamiento?**

Para revisar en un expediente las señales, sus fuentes, contradicciones e información faltante. En el Yuna incluye qué falta conocer aguas arriba, del Camú y de Hatillo. La utilidad en esa tarea aún debe probarse con sus usuarios.

**21. ¿Esto reemplaza al COE o a INDOMET?**

Los avisos y decisiones corresponden a las instituciones competentes. El expediente aporta una forma de revisar evidencia y preparar esa consulta. No tenemos aval institucional ni uso real que no hayamos documentado.

**22. ¿Por qué una tendencia histórica ayudaría durante un aguacero?**

Su papel principal es la planificación y la revisión de confianza en datos. La vigilancia próxima depende de pronósticos, observaciones recientes y contexto. No usamos una tendencia como disparador de emergencia.

**23. ¿La falta de lluvia descarta una inundación?**

Un déficit acumulado puede coexistir con lluvia intensa posterior. Además, poca lluvia local no descarta aportes desde aguas arriba. Por eso mantenemos esas señales separadas.

### Tecnología y continuación

**24. ¿Qué tiene distinto de un mapa con varias capas?**

Se puede revisar qué sostiene cada afirmación, qué fuentes dependen de otras y qué cambia al retirar evidencia. El aporte está en las reglas y la trazabilidad del expediente. Su valor frente al flujo habitual debe medirse.

**25. ¿Dónde está la innovación para Best Use of Technology?**

En conectar evidencias con restricciones de tiempo, ubicación, calidad y dependencia, y recalcular un expediente explicable. La candidatura se demuestra ejecutando esa capacidad; no afirmando que inventamos la comparación científica entre productos.

**26. ¿Qué pasa si se cae internet o llega un dato viejo?**

Hay paquetes guardados con fecha. La copia no se hace pasar por información actual y el motor excluye registros vencidos del respaldo vigente según sus reglas. Si falta información, lo muestra.

**27. ¿Qué evita que una medición inventada cambie la conclusión?**

La aportación local conserva procedencia y queda sin verificar; los ejemplos conservan la etiqueta sintética. No se convierten automáticamente en confirmación de un pronóstico. La autenticación y validación permanente de observaciones requieren desarrollo adicional.

**28. ¿Qué papel tiene la IA?**

Debe declararse la asistencia usada para investigar, programar y redactar. Las cifras presentadas tienen que salir de datos y cálculos reproducibles. No atribuimos a un modelo de lenguaje mediciones, probabilidades o capacidad predictiva que no estén validadas.

**29. ¿Qué harían después?**

Una prueba de tarea con técnicos municipales, captura prospectiva y evaluación de señales con fechas de disponibilidad y costes de actuar o esperar. Conservaríamos también los errores que el expediente introduzca.

**30. ¿Se puede usar en otro país?**

La arquitectura se puede adaptar. Referencias climáticas, territorio, calidad, fuentes y reglas necesitan verificación local. No está validada universalmente por haber funcionado el código en estos pilotos.

## Cómo decirlo

- Hablar como explicándole el proyecto a alguien de aquí: “aguacero”, “por arriba”, “miren”, “ojo” y “nuestra gente”, con naturalidad. Evitar amontonar muletillas o imitar un acento.
- La pausa después de la llamada y antes de “Mismo territorio” vale más que acelerar para meter otra cifra.
- No memorizar treinta respuestas palabra por palabra. Aprender fuente, función, resultado y límite.
- Si algo no se sabe: “Eso no está demostrado todavía; esto es lo que sí pudimos comprobar”.
- Ensayar el texto con la demo. Los tiempos indicados no sustituyen un ensayo cronometrado.

## Evidencia para preparar las respuestas

Consultar ESTADO_CONCLUSIONES.md, BACKEND_PREPARACION.md, REVISION_PARA_DEFENSA.md, results/tropical/puerto_rico/resumen.json, results/tropical/merra2/resumen.json y results/preparacion/REVISION_DEFENSA.json. Las pantallas sugeridas requieren comprobarse en la versión que se expone.

Portales para identificar las fuentes: NASA GPM (https://gpm.nasa.gov/data/imerg), NASA POWER (https://power.larc.nasa.gov/), CHIRPS (https://www.chc.ucsb.edu/data/chirps), ERA5 (https://www.ecmwf.int/en/forecasts/dataset/ecmwf-reanalysis-v5), NOAA NHC (https://www.nhc.noaa.gov/), IBTrACS (https://www.ncei.noaa.gov/products/international-best-track-archive), y Open-Meteo (https://open-meteo.com/en/docs). Estos enlaces identifican proveedores; los archivos y versiones del proyecto sostienen sus cifras.
