# Pruebas tropicales · método Jane (República Dominicana, 2001-2024)

*Stellar Horizons · NASA Space Apps 2026. Código: `earthmemory/tropical/run.py` y `figuras.py`
(`docker compose run --rm tropical`). Resultados: `results/tropical/`. Figura: `figures/tropical/07_the_step_in_2013_{dark,light}.png`.
Las predicciones se escribieron en el código ANTES de correrlo (`results/tropical/predicciones_registradas.json`).*

## La deducción

**Buena parte de lo que llamábamos «las fuentes se contradicen» no es un desacuerdo sobre el clima dominicano. Son
tres cosas medibles:**

1. **Un escalón en la forma de contar días de lluvia.** En octubre de 2013, IMERG pasa de contar más días húmedos
   que CHIRPS a contar menos (de +2,1 a −2,4 puntos porcentuales; Pettitt, p = 0,001 con 2.999 permutaciones de
   bloques de 12 meses). En los cuatro pluviómetros GHCN-Daily con datos, IMERG pierde entre 4 y 12 puntos de días
   húmedos mientras los pluviómetros, de media, apenas cambian (+0,2). La «lluvia más intensa, en menos días» que
   IMERG muestra es, con mucha probabilidad, ese escalón: intensidad = lluvia total ÷ días húmedos.
2. **El relieve frente al alisio.** En las laderas que suben en la dirección del alisio del ENE, CHIRPS da un 14 %
   más de lluvia media que IMERG; en las que bajan (sotavento), un 12 % menos (ρ = 0,56 con el ascenso forzado;
   p = 0,002 con desplazamientos toroidales).
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
| P2 | En barlovento CHIRPS da más lluvia que IMERG | ρ = 0,56, p toroidal 0,002. Tercil barlovento: CHIRPS/IMERG = 1,14; sotavento: 0,88 | **Confirmada** |
| P2 | … y el acuerdo diario es menor en barlovento | ρ = +0,15 (p 0,06): al revés. El acuerdo es menor en la sombra de lluvia (ρ = −0,39 con la sombra, p 0,017) | **Refutada**; el desacuerdo diario está a sotavento |
| P2b | Las celdas con SDII en disputa son las que más difieren en frecuencia de días húmedos | ρ = 0,41, p toroidal 0,006. La disputa de SDII no se relaciona con el relieve (p ≥ 0,18) | **Confirmada** |
| P3 | Los 28 episodios sin explicar se concentran en retornos de la estación seca | Seca 15 de 51, tardía 9 de 36, temprana 4 de 9; p por permutación 0,62. Lluvia del mes de retorno: 0,93 de la climatología frente a 1,39 en el resto (p 0,08). Sin relación con ciclones | **Refutada** (indicio débil: retornos con lluvia normal, no abundante) |
| P4 | La diferencia de frecuencia de días húmedos cambia cerca de 2014-2015 | Punto de cambio 2013-10, p 0,001. En la cantidad de lluvia no hay salto claro (p 0,10) | **Confirmada**, con fecha algo anterior a la esperada |
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

- **Solo cuatro pluviómetros**, y los cuatro alimentan a CHIRPS (circular para CHIRPS). Para IMERG no es circular en
  frecuencia: GPCC le corrige el total mensual, no cuántos días llueve. Hace falta la red de INDOMET para cerrarlo.
- **Pettitt siempre encuentra un punto**; el valor p viene de permutar bloques de 12 meses (conserva la estación y la
  autocorrelación). Un cambio gradual también daría un punto. La figura muestra la serie completa para juzgarlo.
- **No atribuimos el escalón a un sensor concreto.** 2013-10 es anterior al lanzamiento de GPM (feb-2014); coincide
  con la ventana de transiciones del sistema de observación que documenta Zhu et al. 2026, pero no lo hemos probado.
- **El CSI depende de la frecuencia del evento**: en días de ciclón hay más celdas con lluvia fuerte y el CSI sube un
  poco por azar. Falta repetirlo con una medida corregida por azar (ETS).
- **La rejilla solo admite 466 desplazamientos toroidales válidos**, así que el p más pequeño posible es 0,002.

## Qué cambia para la entrega

- Las tendencias de P0 en frecuencia e intensidad diaria de IMERG (R1mm, SDII, rachas secas) deben llevar la nota:
  «posible artefacto de medición: escalón en 2013-10». Siguiente paso: recalcularlas con un término de escalón o solo
  desde 2014.
- El disparador de inundación no se arregla con un umbral distinto: con ciclón los productos coinciden en dónde,
  pero no en cuánto. La decisión debería apoyarse en dónde coinciden (patrón espacial) y no en un número de mm.
- Para el jurado, una frase: **«La lluvia no cambió en 2013; cambió la forma en que un satélite cuenta los días de
  lluvia. Y en las montañas, cada producto reparte la lluvia distinto según de dónde sopla el alisio.»**

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
