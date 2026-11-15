# Pruebas tropicales · método Jane (República Dominicana, 2001-2024)

*Stellar Horizons · NASA Space Apps 2026. Código: `earthmemory/tropical/run.py` y `figuras.py`
(`docker compose run --rm tropical`). Resultados: `results/tropical/`. Figura: `figures/tropical/07_the_step_in_2013_{dark,light}.png`.
Las predicciones se escribieron en el código ANTES de correrlo (`results/tropical/predicciones_registradas.json`).
Es un registro local: el código y el resultado entran en el mismo commit, así que la cronología no es verificable
desde fuera. No es un pre-registro externo.*

> **Aviso (15-nov, tarde).** Este informe conserva el razonamiento tal como se hizo, con correcciones en línea. Hubo
> una revisión independiente (`REVISION_JANE.md`) y un tercer testigo (ERA5). Antes de citar nada, lee el
> **veredicto actual** al final. En corto: IMERG cuenta cada vez menos días de lluvia que sus testigos (eso se
> sostiene), pero no está demostrado que sea un escalón en octubre de 2013. El 82 % mide la sensibilidad a un
> ajuste, no un mecanismo.

## La deducción inicial (hipótesis de trabajo; ver el veredicto al final)

**Hipótesis inicial: buena parte de lo que llamábamos «las fuentes se contradicen» podría no ser un desacuerdo sobre
el clima dominicano, sino tres cosas medibles:**

1. **Un cambio en la forma de contar días de lluvia** (la forma y la fecha no están identificadas; ver el veredicto).
   Según Pettitt frente a CHIRPS, en octubre de 2013 IMERG pasa de contar más días húmedos
   que CHIRPS a contar menos (de +2,1 a −2,4 puntos porcentuales; Pettitt, p = 0,001 con 2.999 permutaciones de
   bloques de 12 meses). En los cuatro pluviómetros GHCN-Daily con datos, IMERG pierde entre 4 y 12 puntos de días
   húmedos mientras los pluviómetros, de media, apenas cambian (+0,2). La «lluvia más intensa, en menos días» que
   IMERG muestra podría venir de ese cambio en el conteo, porque intensidad = lluvia total ÷ días húmedos. Es una
   hipótesis: ni el escalón ni su causa están demostrados.
2. **El relieve frente al alisio.** En las laderas que suben en la dirección del alisio del ENE, CHIRPS da un 14 %
   más de lluvia media que IMERG; en las que bajan (sotavento), un 12 % menos (ρ = 0,56 con el ascenso forzado;
   p exhaustiva 0,012 con las 82 traslaciones toroidales distintas; el 0,002 original contaba sorteos repetidos). El
   alisio se supuso fijo del ENE (70°); no se usaron vientos medidos de cada episodio.
3. **El tipo de tormenta.** Con un ciclón tropical a menos de 500 km, los dos productos coinciden mucho más en dónde
   cae la lluvia fuerte (CSI ≥ 50 mm: 0,27 frente a 0,10 en días sin ciclón de agosto a noviembre). Sin ciclón, la
   lluvia fuerte es convectiva y local, y casi no coinciden. Pero ni con ciclón coinciden en **cuánta** llueve: el
   disparador de 100 mm en 48 h sigue sin confirmarse en el 74 % de los casos.

## Predicciones registradas y veredicto

| # | Predicción (escrita antes de correr) | Resultado | Veredicto |
|---|---|---|---|
| P1 | Con ciclón a < 500 km los productos coinciden más en lluvia fuerte | CSI ≥ 50 mm 0,268 frente a 0,101 (diferencia +0,167; IC 95 % por años 0,094-0,234). CSI ≥ 20 mm 0,52 frente a 0,20 | **Confirmada** |
| P1 | … y el disparador de 100 mm/48 h queda menos veces sin confirmar | 74,5 % sin confirmar con ciclón frente a 79,4 % sin ciclón (ago-nov) | **No en lo sustancial**: coinciden en dónde, no en cuánto |
| P1b | Los máximos anuales (Rx1day) caen sobre todo en días de ciclón | IMERG: 37,6 % de los Rx1day en días de ciclón (±1 d), que son el 4,1 % de los días (×9,2). CHIRPS: 15,3 % (×3,7) | **Confirmada**, y los productos discrepan en cuánto pesan los ciclones |
| P2 | En barlovento CHIRPS da más lluvia que IMERG | ρ = 0,56, p toroidal 0,012 (exhaustiva; antes 0,002). Tercil barlovento: CHIRPS/IMERG = 1,14; sotavento: 0,88 | **Confirmada** |
| P2 | … y el acuerdo diario es menor en barlovento | ρ = +0,15 (p 0,06): al revés. El acuerdo es menor en la sombra de lluvia (ρ = −0,39 con la sombra, p exhaustiva 0,036; antes 0,017) | **Refutada**; el desacuerdo diario está a sotavento |
| P2b | Las celdas con SDII en disputa son las que más difieren en frecuencia de días húmedos | ρ = 0,41, p toroidal 0,024 (exhaustiva; antes 0,006). La disputa de SDII no se relaciona con el relieve (p ≥ 0,18) | **Confirmada** |
| P3 | Los 28 episodios sin explicar se concentran en retornos de la estación seca | Seca 15 de 51, tardía 9 de 36, temprana 4 de 9; p por permutación 0,62. Lluvia del mes de retorno: 0,93 de la climatología frente a 1,39 en el resto (p 0,08). Sin relación con ciclones | **Refutada** (indicio débil: retornos con lluvia normal, no abundante) |
| P4 | La diferencia de frecuencia de días húmedos cambia cerca de 2014-2015 | Punto de cambio 2013-10, p 0,001. En la cantidad de lluvia la prueba no detectó un salto (p 0,10; no prueba que no lo haya) | **Confirmada** como cambio, pero Pettitt también da p 0,0003 con una tendencia gradual sin salto: no prueba que sea abrupto ni fecha la causa (ver veredicto) |
| P5* | ¿Quién cambió? (añadida tras ver P4; no registrada antes) | Cambio medio después/antes en días húmedos: pluviómetros +0,2 pp; IMERG −8,5 pp (de −4,0 a −12,2 en las 4); CHIRPS −0,2 pp (pero −5,4 en Barahona) | Apunta a IMERG |

\* P5 es una prueba exploratoria posterior; se presenta como tal.

Datos: IMERG V07 Final diario y CHIRPS v2.0 diario agregado a 0.1° (442 celdas, motor P0); IBTrACS v04r01 Atlántico
Norte (NOAA NCEI; 78 sistemas a < 500 km entre 2001 y 2024, 205 días); Copernicus DEM GLO-90; GHCN-Daily (Puerto
Plata, Punta Cana, Barahona y Santo Domingo; la quinta estación no tiene datos en el periodo).

## Cómo encaja con el informe de conexiones (`CONEXIONES_UMBRALES_Y_SESGOS.md`)

Un agente independiente volvió a correr `earthmemory/cierre.py` en Docker y obtuvo salidas idénticas byte a byte;
recalculó además las cifras clave con las funciones originales de los motores. Verificadas:
- SPI con margen de 0,25 alrededor de −1: siguen discrepando 614 de 732 casos (83,9 %), con el 23,5 % de las alarmas.
  Matiz: de los 614, 359 son contradicciones claras (algún producto con SPI ≥ 0) y 145 son casos en que solo MERRA-2
  marca sequía.
- SDII en disputa según el umbral de día húmedo: 0,5 mm → 202; 1 mm → 160; 2 mm → 64; 5 mm → 0. A 5 mm el 0 refleja
  pérdida de potencia, no acuerdo.
- En IMERG nacional, el aumento de intensidad viene del denominador (días húmedos −0,067 en log por década, lluvia
  en días húmedos +0,002).
- Yuna: los 115,5 mm/48 h fueron el 8-nov-2024, fuera de la ventana puntuada (máximo dentro: 92,3 mm). Matiz: ese
  mismo aguacero cuenta a la vez como el único fallo y como una falsa alarma del backtest, por un día de diferencia.
- Los tres DOI existen y sus resúmenes dicen lo que el informe afirma (Zhu et al. 2026, *Communications Earth &
  Environment*, 19 productos y discontinuidades en 2014-2015; Cui y Tian 2026, *J. Hydrol.* 677:135827; síntesis de
  138 cuencas en *HESS* 30:5281-5296). Solo se leyó el resumen.

**La conexión:** ese informe mostró que la intensidad de IMERG sube porque baja el número de días húmedos. Estas
pruebas muestran **cuándo** baja (un escalón en 2013-10), **que la lluvia en el suelo no bajó** (pluviómetros) y que la
disputa de SDII sigue a la diferencia de frecuencia (ρ = 0,41), no al relieve. La hipótesis integrada del colaborador
(«cambia la forma de observar y cambia la capacidad del territorio de responder») queda separada en sus dos mitades:
la primera mitad ya tiene una prueba; la segunda (territorio) sigue abierta.

## Jugar en contra

- **Solo cuatro pluviómetros**, y los cuatro alimentan a CHIRPS (circular para CHIRPS). *Corregido:* antes decía que
  para IMERG no era circular en frecuencia porque GPCC solo corrige el total mensual. Es falso. El ajuste
  multiplica la lluvia de cada media hora y puede mover días a través del umbral de 1 mm (0,8 × 1,5 = 1,2 mm;
  documentación técnica de IMERG V07, postprocesado). Hace falta la red de INDOMET para cerrarlo.
- **Pettitt siempre encuentra un punto**; el valor p viene de permutar bloques de 12 meses (conserva la estación y la
  autocorrelación). Un cambio gradual también daría un punto. La figura muestra la serie completa para juzgarlo.
- **No atribuimos el escalón a un sensor concreto.** 2013-10 es anterior al lanzamiento de GPM (feb-2014); coincide
  con la ventana de transiciones del sistema de observación que documenta Zhu et al. 2026, pero no lo hemos probado.
- **El CSI depende de la frecuencia del evento**: en días de ciclón hay más celdas con lluvia fuerte y el CSI sube un
  poco por azar. *Hecho en la revisión:* con ETS y los dos grupos en agosto-noviembre, el acuerdo sigue siendo mayor
  cerca de ciclones (ETS ≥ 50 mm 0,239 frente a 0,097; sin IC). «Sin ciclón» no equivale a convección local, porque
  también hay frentes, vaguadas y ondas.
- *Corregido:* los «466 desplazamientos» eran sorteos aceptados con repetición. Hay **82 traslaciones distintas**,
  así que la resolución mínima es 1/83 y los p exhaustivos son 0,012, 0,024 y 0,036, sin corregir por multiplicidad.

## Qué cambia para la entrega

- Las tendencias de P0 en frecuencia e intensidad diaria de IMERG (R1mm, SDII, rachas secas) deben llevar la nota:
  «posible inhomogeneidad temporal de IMERG en el conteo de días de lluvia; no confirmada». *(Antes decía «artefacto
  de medición: escalón en 2013-10», que quedó retirado.)* Siguiente paso: comparar tendencia, escalón y ambos, sin
  imponer fecha.
- El disparador de inundación no se arregla con un umbral distinto: con ciclón los productos coinciden en dónde,
  pero no en cuánto. La decisión debería apoyarse en dónde coinciden (patrón espacial) y no en un número de mm.
- ~~Para el jurado, una frase: «La lluvia no cambió en 2013; cambió la forma en que un satélite cuenta los días de
  lluvia…»~~ **Retirada:** afirma una fecha y una causa que no están demostradas.

## Lentes del método Jane usadas

- `thinking-map-territory`: los productos son el mapa y los pluviómetros el territorio. De ahí salió P5 (quién cambió).
- `system-operator` (9 pantallas): el supersistema (la constelación de satélites) cambia en el tiempo. De ahí la
  prueba de punto de cambio (P4).
- `inversion`: «¿y si la tendencia no está en la lluvia sino en el contador?». Esa frase guió P4 y P5.
- `physical-contradictions` (separación en el tiempo): necesitamos un registro largo y homogéneo a la vez; se separa
  antes y después del escalón.
- `thinking-scientific-method`: predicciones registradas antes de correr; dos refutadas se publican igual.
- `the-fool` / `thinking-red-team`: las objeciones de arriba (circularidad, Pettitt, CSI y frecuencia).
- `thinking-probabilistic`: tasas base (4,1 % de días con ciclón frente al 37,6 % de los máximos).

## Recálculo de P0 sin el escalón de IMERG

Código: `earthmemory/tropical/recalculo.py` y `sensibilidad_corte.py`. Salidas: `results/tropical/recalculo/`.
Figura: `figures/tropical/08_after_the_correction_{dark,light}.png`. Se usa el **mismo motor P0** (Theil-Sen,
Mann-Kendall con Hamed-Rao, BH-FDR) sobre las mismas series anuales; la corrida sin cambios reproduce exactamente
las clases publicadas en `results/tendencias/tendencias_celdas.csv`. Las salidas de P0 no se tocaron.

**Variante principal (A_frec):** solo en los índices que cuentan días húmedos (R1mm, SDII, CDD, CWD, RACHAS10,
RACHAS15), porque el escalón está en la frecuencia y no en la cantidad. Por celda e índice se resta a IMERG, desde
2014, el cambio de su diferencia media con CHIRPS (CHIRPS como referencia, respaldada por los pluviómetros).

| Índice | Celdas en disputa: publicado → corregido | IMERG nacional: publicado → corregido |
|---|---|---|
| SDII (intensidad), año | 160 → 0 | +6,7 %/década (p 0,035) → −8,8 % (p 0,09) |
| Rachas secas ≥ 15 d, dic-abr | 117 → 2 | +16,1 %/década (p < 0,001) → −13,2 % (p 0,07) |
| Días ≥ 1 mm (R1mm), dic-abr | 106 → 1 | −9,9 % (p 0,21) → +8,1 % (p 0,37) |
| R1mm, año | 69 → 0 | −5,8 % (p 0,07) → +0,2 % (p 0,98) |
| Total celda-índice (todos los índices) | 871 → 158 | — |

**Lo que se concluye (redacción revisada):** las dos tendencias nacionales significativas de IMERG que más llamaban la
atención («llueve más intenso» y «las rachas secas de la estación seca se alargan») dejan de ser significativas con
un ajuste aditivo hacia CHIRPS. Eso muestra que son **sensibles a ese ajuste**. No muestra que su causa sea un
artefacto, porque el mismo ajuste también borra tendencias graduales sin ningún salto (ver el veredicto). P0 queda
igual en lo esencial: **ninguna tendencia robusta** de frecuencia o intensidad.

**Jugar en contra (lo que NO se puede afirmar):**
- **La corrección no fecha el escalón.** Con casi cualquier año de corte entre 2010 y 2017 las disputas anuales caen de
  307 a menos de 10 (`sensibilidad_corte.csv`): un escalón en 24 años absorbe casi cualquier diferencia de tendencia.
  Lo que fecha el salto es la prueba de Pettitt (2013-10, p 0,001); lo que dice quién cambió son los pluviómetros.
- **El acuerdo tras corregir es en parte mecánico**, porque la corrección usa CHIRPS. Por eso no se presentan como
  hallazgos las 128 celdas «robustas» nuevas de SDII en la temporada temprana (may-jul, descenso): son producto de la
  corrección, no evidencia independiente.
- **La corrección crea disputas nuevas** en las rachas secas de las temporadas húmedas (RACHAS15 ago-nov 41,
  may-jul 49): el escalón no es igual en todas las estaciones. Una corrección por temporada sería el siguiente paso.
- **Sin una serie de referencia, el escalón y la tendencia no se separan.** La variante B (escalón estimado en la
  propia serie de IMERG) fabrica tendencias por todas partes (PRCPTOT +16 %/década, 9.147 celdas en disputa). Es la
  prueba de por qué hacen falta testigos independientes.
- El índice SPI-12 queda igual (no depende de contar días) y su prueba sigue siendo liberal según la calibración de P0.

~~**Frase para el jurado:** «Quitamos un solo escalón del registro del satélite y el 82 % de las contradicciones
desaparece. No eran dos climas: era una forma distinta de contar los días de lluvia.»~~ **Retirada:** con una
tendencia gradual sintética, sin salto, el mismo ajuste le quita el 74,6 % de la pendiente. El 82 % mide la
sensibilidad al ajuste, no demuestra el mecanismo. Además, la variante ajustada tiene 8.375 valores imposibles
(rachas o intensidades negativas): es una sensibilidad estadística, no lluvia corregida.

## Tercer testigo: ERA5 (15-nov, tarde)

Código: `earthmemory/tropical/era5_testigo.py` y `figura_era5.py`. Salidas: `results/tropical/era5/`. Figura:
`figures/tropical/09_tercer_testigo_era5_{dark,light}.png`.

**Por qué ERA5.** Es el reanálisis europeo (ECMWF). No usa los pluviómetros que alimentan a CHIRPS. *Dependencia
parcial:* IMERG Final usa ERA5 como dato auxiliar en GPROF, así que no es un testigo del todo independiente de IMERG.
Se bajó la lluvia diaria (`models=era5`, día UTC) de la API de archivo de Open-Meteo para 6 celdas de 0,25°: las 4
estaciones GHCN-D más Santiago y Constanza. Las predicciones se escribieron a disco antes de bajar nada
(`predicciones_registradas.json`; registro local).

*Corrección de alineación (segunda revisión):* la API devolvió otra celda en Santo Domingo (−69,50° en vez de −69,75°)
y en Puerto Plata (−70,75° en vez de −70,50°), unos 26 km de diferencia. Ahora IMERG y CHIRPS se promedian, ponderados
por área, en la celda que **devuelve** la API (las coordenadas quedan en `resumen.json`). El resultado apenas cambia:
IMERG pasa de −6,3 a −6,1 pp, ERA5 se queda en −1,9 y el punto de cambio sigue en 2016-10. Coincide con la reproducción
que hizo la revisión.

| Predicción | Resultado (alineado) | Veredicto |
|---|---|---|
| E1: IMERG − ERA5 salta entre 2012-10 y 2014-12 | El punto de cambio cae en **2016-10** (p < 0,001) | **No se cumple** |
| E2: ERA5 cambia < 2 pp e IMERG baja ≥ 4 pp (antes/después de 2013-10) | ERA5 −1,9 pp de media, pero −2,5 de mediana; IMERG −6,1; CHIRPS −0,2 | Se cumple la regla aritmética, por cancelación entre lugares (ver abajo) |
| E3: CHIRPS − ERA5 no salta en esa ventana | No se detecta salto (p 0,56). No prueba estabilidad | Se cumple |
| E4: no salta la relación de cantidad IMERG/ERA5 | No se detecta salto (p 0,56). Ambos podrían cambiar juntos | Se cumple |

**Qué queda en pie.**
- En los seis lugares, IMERG pierde de media más días de lluvia que ERA5 y que CHIRPS. Esto aguanta la corrección de
  alineación.
- No se detectó un cambio en CHIRPS − ERA5 ni en la relación de cantidades IMERG/ERA5. Que no se detecte no prueba que
  CHIRPS sea estable, ni que la cantidad absoluta no cambie. Tampoco dice cuál producto se acerca más a la realidad.

**E2 se cumple por promedio.** ERA5 pierde 4,0 pp en Puerto Plata, 4,8 en Santiago y 4,2 en Constanza, y gana días en
Santo Domingo y Punta Cana. Sin Punta Cana, la media de ERA5 sería −2,6 y E2 fallaría. En Santiago, ERA5 pierde incluso
más que IMERG. «ERA5 apenas cambia» no es una descripción justa. La pista abierta más interesante es por qué el norte y
la montaña pierden días también en ERA5, mientras el sur y el este divergen mucho más de IMERG. Todavía no se puede
atribuir ni al relieve, ni al clima, ni al algoritmo.

**Qué se cae.**
- La palabra «escalón» y la fecha de octubre de 2013 no aguantan frente a ERA5. Pettitt parte la serie en 2016-10, pero
  eso no prueba que el cambio empezara ahí, ni que sea suave, ni que haya un solo cambio. La media móvil sugiere una
  separación que se profundiza desde 2022, aunque también suaviza los saltos (figura 09, panel a). Hasta comparar
  explícitamente las alternativas, la forma correcta es **«posible inhomogeneidad temporal»**.
- El salto de 2013-10 se detectó frente a CHIRPS. Frente a ERA5, en 2013-2016 las dos diferencias suben a la vez, así
  que en esos años ERA5 cuenta menos días de lluvia que ambos productos.
- Es coherente con lo que ya mostraba la sensibilidad del recálculo: cualquier año de corte entre 2010 y 2017
  funcionaba. Una deriva gradual se comporta así; un escalón limpio, no.
- Lenguaje corregido: «posible inhomogeneidad temporal de IMERG en la frecuencia de días de lluvia», no «un escalón en
  octubre de 2013».

**Límites.**
- Son solo 6 puntos, no las 442 celdas.
- ERA5 baja 4-5 pp en Puerto Plata, Santiago y Constanza, en el norte y la montaña. Ahí parte de la caída de IMERG
  podría ser real o compartida.
- ERA5 también cambia con las observaciones que asimila a lo largo de los años.
- El recálculo de P0 ajustó con un escalón en 2014. Todavía no se sabe qué forma (deriva, escalón, varios cambios)
  representa mejor los datos, así que ninguna corrección está justificada por ahora.

## Veredicto actual de la hipótesis (tras ERA5 y la revisión independiente)

En paralelo, otra sesión escribió una revisión independiente (`reports_nacional/REVISION_JANE.md`, no es de este
chat). Llega por otro camino a lo mismo que ERA5:
- Con una serie sintética que sube en línea recta y no tiene ningún salto, el ajuste A_frec quita el 74,6 % de la
  pendiente y Pettitt da p 0,0003. Es decir, ni la corrección ni Pettitt distinguen un escalón de una deriva gradual.
- La variante corregida produce 8.375 valores imposibles (rachas e intensidades negativas).
- ERA5 se usa como información auxiliar en GPROF (IMERG Final), así que no es un testigo del todo independiente.

Verifiqué dos puntos de esa revisión:
- El umbral del motor es q = 0,10 (`ALPHA_FDR = 2·α`, Wilks 2016) y no 0,05. Se corrigió el pie de la figura 08.
- El contraejemplo sintético está en `results/tropical/revision/resumen.json`.

**Hipótesis original:** «Un escalón de IMERG en octubre de 2013 explica el 82 % de las contradicciones».
**No se sostiene así.** La fecha falla frente a ERA5 (2016-10), la forma (escalón frente a deriva) no está
identificada y el 82 % mide la sensibilidad a un ajuste, no un mecanismo demostrado.

**Lo que se puede afirmar hoy (formulación de la segunda revisión):** «En los seis lugares estudiados, IMERG presenta
una disminución media de días húmedos mayor que ERA5 y CHIRPS. La diferencia persiste al alinear espacialmente la
comparación, pero su origen, su forma temporal y su alcance nacional siguen sin resolverse».

Consecuencia: las tendencias de IMERG de intensidad y de rachas secas son frágiles y no se pueden confirmar. Los apoyos
y sus límites:
- **Pluviómetros:** con meses comparables, IMERG cae más que la estación en los 4 sitios. Pero Punta Cana también
  pierde días y CHIRPS cambia mucho en Barahona.
- **CHIRPS frente a ERA5:** no se detecta un cambio, lo que no equivale a estabilidad.
- **ERA5:** de media, IMERG −6,1 pp y ERA5 −1,9 pp, con mucha diferencia entre lugares. Además, IMERG Final usa
  ERA5 como información auxiliar (GPROF), así que los dos no son del todo independientes.

**Cambios que esto pide:**
- La figura 08 y el conmutador de la web deben presentarse como *sensibilidad*: «ajuste hacia CHIRPS», no «sin el
  escalón».
- En los textos, «escalón de 2013» pasa a «posible deriva de IMERG en la frecuencia de días de lluvia».

## ¿Tendencia o escalón? Comparación de modelos con validación (15-nov, noche)

Código: `earthmemory/tropical/forma_cambio.py` y `figura_forma.py`. Salidas: `results/tropical/forma/`. Figura:
`figures/tropical/10_tendencia_o_escalon_{dark,light}.png`. Sigue la secuencia que propuso la revisión: primero validar
con series sintéticas, luego aplicar a las 442 celdas sin imponer ninguna fecha. Ideas tomadas de Beaulieu y Killick
(tendencias, saltos y memoria) y de «Drift vs Shift»; de ambos solo se leyó el resumen.

**Método.** Serie: frecuencia mensual de días ≥ 1 mm, IMERG − CHIRPS, sin ciclo estacional. Cuatro modelos con
errores AR(1) (Prais-Winsten, verosimilitud exacta): sin cambio, tendencia, escalón y tendencia + escalón. La fecha del
escalón se busca en toda la serie y cuenta como un parámetro. Se elige por BIC. Si otra forma queda a menos de 2
unidades, el resultado es «indistinguibles». Las predicciones F1-F3 se registraron al empezar la corrida, pero
después de ver ERA5.

**Validación** (150 series por caso, ruido AR(1) como el observado):

| Ruido | Cambio total | Acierta la forma | Falsos cambios (sin cambio simulado) |
|---|---|---|---|
| Una celda | 4,5 pp | 10 % | 5 % |
| Una celda | 9 pp | 41 % | 5 % |
| Serie nacional | 4,5 pp | 27 % | 4 % |
| Serie nacional | 9 pp | 55 % | 4 % |

Con ruido nacional y 4,5 pp, una tendencia simulada se etiqueta «escalón» solo el 5 % de las veces. Un escalón
simulado se etiqueta «escalón» el 45 %.

**Resultados.**
- **Serie nacional:** gana un escalón en **2018-02** (rango con ΔBIC < 2: 2018-02 a 2018-11). Supera a la tendencia por
  7,1 de BIC y a tendencia + escalón por 2,3. No es 2013. La revisión independiente encontró el mismo corte (2018-02)
  con otro método.
- **Celdas:** 265 de 442 muestran un cambio detectable, frente a un 5 % de falsos positivos esperables. La forma elegida
  por celda (97 escalón, 37 tendencia, 24 ambos, 107 indistinguibles) **no es fiable**: la validación da un 10 % de
  aciertos con un cambio de 4,5 pp. Las fechas de escalón se agrupan en 2018 (45 celdas, el 37 % en 12 meses), con
  grupos menores en 2013 (22) y 2006 (17). Las celdas vecinas no son independientes.

| Predicción | Resultado | Veredicto |
|---|---|---|
| F1: la forma por celda se acierta en ≥ 60 % (4,5 pp) | 10 % | **No se cumple**: la forma por celda no es identificable con estos datos |
| F2: en el país el escalón no gana con claridad a la tendencia | Gana el escalón por 7,1 de BIC, en 2018-02 | **No se cumple** |
| F3: ninguna ventana de 12 meses reúne > 40 % de las fechas de escalón | 37 %, en 2018 | Se cumple, por poco: hay un agrupamiento claro en 2018 |

**Lectura.**
- Hay un cambio extendido en la diferencia de días de lluvia entre IMERG y CHIRPS. En la serie nacional se parece más
  a un salto hacia 2018 que a una tendencia recta, y una tendencia pura casi nunca imita ese resultado (5 %).
- Que tenga forma de escalón no dice quién cambió, ni por qué.
- Las fechas candidatas dependen de la referencia y del método:
  - 2013-10: Pettitt frente a CHIRPS.
  - 2016-10: Pettitt frente a ERA5, en 6 puntos.
  - 2018-02: este modelo y el de la revisión.
- No se simularon una deriva curva ni varios saltos, y cualquiera de las dos podría producir un «escalón en 2018».
- *Pista sin comprobar:* cotejar 2018 con la cronología de sensores de entrada de IMERG V07 (documentación técnica de
  NASA). No se ha hecho y no se atribuye nada a ningún sensor.

**Límites añadidos por la revisión** (verificados aquí):
- El escalón le gana a la tendencia recta por 7,1 de BIC, pero a tendencia + escalón solo por 2,3. Es el mejor de los
  modelos probados, no un ganador indiscutible. La revisión optimizó la autocorrelación en cada fecha candidata y
  obtuvo la misma fecha (2018-02) y casi los mismos BIC.
- Que solo el 5 % de las tendencias simuladas salgan como escalón **no** equivale a un 95 % de certeza sobre el
  resultado real. Con ruido nacional y 4,5 pp, el método acierta la forma el 27 % de las veces.
- Las 265 celdas son selecciones de modelo, no rechazos corregidos por multiplicidad. Si se exige más ventaja de BIC
  frente a «sin cambio», quedan 219 (más de 2) o 161 (más de 6); lo comprobé en `celdas.csv`. Son sensibilidades del
  criterio, no nuevos umbrales de significancia.
- La ventana candidata es todo el intervalo febrero-noviembre de 2018 del perfil del modelo. No es un intervalo de
  confianza.

**Pista candidata (sin atribución): el paso de GOES-13 a GOES-16.** La búsqueda la hizo la revisión; aquí se
registra sin haber cotejado las fuentes por mi cuenta.
- GOES-16 pasó a ser GOES-East el 18-dic-2017 (cronología de NOAA).
- La documentación técnica de IMERG V07 muestra esa transición en sus entradas infrarrojas de 2017-2018.
- Todo el registro se reprocesó con V07, pero las entradas infrarrojas vienen del procesamiento operativo de cada
  época. Un cambio de esas entradas podría quedar dentro del registro reprocesado.
- Esto hace plausible la hipótesis, pero no demuestra que explique el resultado.

Coincidencias que **no** sirven como explicación:
- La nota de documentación del 7-feb-2018 (procesamiento V05B).
- El corte infrarrojo del 21-22 de agosto de 2018, que afectó a Early/Late en tiempo real, no a V07 Final.

**Prueba que la discriminaría (sin hacer).** Ver si alrededor de la transición cambia la frecuencia de lluvia débil
sobre todo cuando domina la información infrarroja, y no en las observaciones directas de microondas. IMERG trae
campos para separarlo: influencia del infrarrojo, fuente de microondas y precipitación sin el ajuste final con
pluviómetros. Si el cambio aparece igual en las microondas, la pista de GOES pierde fuerza.
