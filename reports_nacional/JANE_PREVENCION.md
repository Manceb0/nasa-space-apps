# Pasada Jane: ¿qué solución preventiva entregamos? (15-nov-2026, noche)

> **Superado por `JANE_PREVENCION_CAUSAL.md`.** La prueba de este documento miraba al día siguiente, contaba alertas
> que llegaban durante la inundación y sumaba celdas distintas de CHIRPS. En la versión causal, el testigo deja 16
> falsas alarmas en vez de 39 y detecta 6 de 8 eventos, pero casi nunca avisa **antes** del inicio (1 o 2 de 8).

Modo `hackathon`. Se pasaron los 7 movimientos con una o más skills por fila, abriendo cada archivo. Hay una prueba
nueva hecha con datos que ya teníamos (`earthmemory/tropical/alerta_acuerdo.py`); todo lo demás sale del repo.

## 1. La deducción

**El desacuerdo entre satélites que encontramos no es lo opuesto a prevenir: es lo que hace fiable una alerta.** Si la
alerta de inundación del Yuna exige que un segundo producto la confirme, las falsas alarmas bajan casi a la mitad sin
perder inundaciones en la prueba 2016-2024. La prevención defendible no es predecir la próxima inundación, sino decir
**cuándo creerle a una alarma y dónde falta un testigo**.

## 2. Las pistas

| Pista | Dato | Fuente |
|---|---|---|
| El reto pide detectar tendencias, no predecir | «Elegir variable → región → serie → ritmo de cambio → significancia», para estudiantes. No menciona predicción ni prevención | `ESTRATEGIA.md` A1 (texto oficial leído el 14-nov; la URL da 404 el 15-nov) |
| Se pueden usar datos de fuera de la NASA | Ya los usamos: CHIRPS, ERA5, GHCN-D, IBTrACS, Copernicus DEM. El equipo dice que la organización lo permite **[SIN VERIFICAR en texto oficial]** | repo |
| Existe una regla real de acción anticipatoria | La Cruz Roja (sEAP MDRDO020) usa más de 100 mm en 2 días como disparador | `CASO_YUNA.md` |
| Esa regla con un solo producto falla mucho | IMERG solo: 7 de 8 eventos detectados, pero 39 falsas alarmas de 48 episodios (CSI 0,15) | `CASO_YUNA.md` |
| **Pedir un testigo funciona mejor** | Con IMERG **y** CHIRPS (± 1 día), en la prueba 2016-2024: 7 de 8 eventos, falsas alarmas 39 → **20**, CSI 0,15 → **0,25**. En la calibración 2001-2015: falsas alarmas 89 → 46, pero pierde 1 evento de 6 | `results/tropical/alerta_acuerdo/` (nuevo) |
| Aceptar cualquiera de los dos empeora | IMERG **o** CHIRPS: 8 de 8, pero 88 falsas alarmas (CSI 0,08) | ídem |
| La memoria del suelo no ayuda a anticipar | La lluvia previa no mejora el disparador (AUC ≈ 0,4-0,5) | `CASO_YUNA.md` |
| En sequía pasa lo mismo | En el 39 % de las alarmas de sequía, otro producto dice normal o húmedo | `AUDITORIA_CONFIANZA.md` |

**Predicciones registradas** (antes de correr):
- **K1, no se cumple por una alarma.** Pedía conservar al menos 6 de 8 eventos y bajar las falsas alarmas a la
  mitad (19,5); quedaron en 20.
- **K2, se cumple.** Aceptar cualquiera de los dos productos no mejora.

## 3. Lo evidente y por qué no basta

1. **«Hagamos un sistema que prediga inundaciones».** El reto no lo pide, no podríamos validarlo (8 eventos de
   prueba) y lo único que probamos para anticipar, la memoria del suelo, no funcionó.
2. **«La herramienta solo explica por qué los datos no coinciden».** Eso deja el hallazgo sin nadie que decida con él.
   El usuario tiene razón en que se queda corto.
3. **«Ponerle a la web un botón de alerta».** Una alerta con un solo producto es justo la que falla 39 veces de 48.

## 4. Rutas

| Ruta | Mecanismo | Para quién | Estado |
|---|---|---|---|
| A. Pronóstico de inundaciones | Modelo que anticipa el evento | COE | Fuera del reto; sin validación posible. **Descartada** |
| **B. Alerta con testigo** | Alertar solo si dos productos independientes coinciden; si no coinciden, «verificar en terreno» | Cruz Roja (sEAP), COE, INDRHI | **Probada hoy** en el Yuna |
| C. Semáforo de sequía | Actuar cuando ≥ 2 productos marcan sequía; si se contradicen, verificar | Agricultura, INDRHI | Desacuerdo medido (39 %); sin contraste con impactos |
| **D. Dónde falta un testigo** | Mapa de celdas con más desacuerdo entre productos y más exposición, para priorizar pluviómetros | INDOMET, INDRHI | Datos listos (disputas por celda, Yuna); es planificación, no predicción |
| E. Memoria del suelo para anticipar | El suelo húmedo amplifica la crecida | — | **Refutada** con estos datos |

## 5. Prueba en contra

- **B: la objeción más fuerte (`the-fool`, modo «poner a prueba la evidencia»).** Son 8 eventos; en la calibración
  pierde uno (4 de 6); y son estimaciones observadas, no el pronóstico que usa la sEAP. Además:
  - **CHIRPS diario no es diario de verdad.** Reparte el total de cada péntada entre sus días con proporciones de un
    modelo de pronóstico; la tolerancia de ± 1 día lo mitiga.
  - **CHIRPS llega tarde para operar en tiempo real.** Una versión operativa necesita un segundo testigo rápido
    (IMERG Early frente a GSMaP en casi tiempo real, o pluviómetros).
  - **Lo que sí se sostiene:** como principio, pedir un testigo reduce las falsas alarmas sin perder la mayoría de
    los eventos.
- **C.** Sin una serie de impactos de sequía no sabemos si el semáforo acierta. Solo muestra dónde no actuar a ciegas.
- **D.** Prioriza dónde medir; no demuestra cuánto mejoraría la alerta un pluviómetro nuevo.
- **Pre-mortem.** Nos pasamos al otro extremo y prometemos «prevenir desastres». Un juez pregunta cómo lo validamos, y
  no hay respuesta. La protección es decir «alerta más fiable, probada en 8 eventos», nunca «predecimos inundaciones».

## 6. Decisión

**B como núcleo preventivo y D como recomendación de inversión, sobre la herramienta de tendencias que ya existe**
(Relevancia). La cadena:
- La herramienta detecta tendencias en las que se puede confiar.
- Eso lleva a alertas en las que se puede confiar.
- Y a decidir dónde falta medir.

C queda como extensión, con su límite dicho. A y E quedan fuera.

Cambiaría de opinión si el texto oficial (o la organización, por escrito) pide explícitamente una solución de
prevención operativa. En ese caso B pasaría al frente, con el segundo testigo en tiempo real como siguiente paso.

## 7. Primer entregable

**La frase:** *«An alarm that asks for a second witness: in 2016-2024, half the false flood alarms in the Yuna basin,
and the same 7 of 8 floods caught.»*

**El paso que añade al recorrido del jurado.** Un paso 5, después del veredicto:
- El jurado ve la regla de la Cruz Roja aplicada con un solo satélite: 48 alarmas, 39 falsas.
- Activa «pedir testigo» y quedan 29 alarmas, 20 falsas, con las mismas 7 inundaciones detectadas.
- «Mostrar evidencia» enseña los 8 eventos, el periodo, la tolerancia y los límites: n = 8, observado y no pronóstico,
  CHIRPS diario desagregado.

## 8. Lentes usadas, fila por fila

| Fila | Skill | Qué reveló |
|---|---|---|
| 1. Escena | `thinking-map-territory` | El mapa del usuario («es dar una solución para prevenir») frente al territorio: el texto oficial verificado el 14-nov pide detectar tendencias y no habla de prevención. La URL da 404 hoy. Lo de los datos externos ya se cumple. |
| 2. Premisa | `thinking-five-whys-plus` | ¿Por qué se siente inútil? Porque el desacuerdo se presentó como hallazgo y no como insumo de una decisión. ¿Por qué? Porque nunca lo conectamos con una regla de alerta real. La causa raíz es que la sEAP de la Cruz Roja estaba en nuestro propio informe y nadie la probó con dos productos. Contramedida: probarla. |
| 3. Ideas | `lateral` → `analogy` | Medicina (una prueba positiva se confirma con otra independiente antes de tratar), aviación (sensores redundantes que votan antes de alarmar) y testigos en un juicio. Las tres transfieren el mismo mecanismo: **confirmar antes de actuar**. Se abandonó el sistema inmune, que necesitaba un segundo rol forzado. |
| 3. Ideas | `ideality` / `resource-analysis` | Sistema ideal: una alerta que se verifica sola sin sensores nuevos. El recurso ya presente es el segundo producto que calculamos para la auditoría. |
| 4. Detalle | `thinking-scientific-method` | La prueba más barata con datos existentes: el backtest con acuerdo. Reproduce exactamente la regla original (7/8, 39) antes de comparar. |
| 5. En contra | `the-fool` (falsación) y `thinking-pre-mortem` | La n es pequeña; es observado, no pronóstico; CHIRPS diario es desagregado y llega tarde. El riesgo de prometer «predecir» se evita con una formulación acotada. |
| 6. Decisión | `thinking-opportunity-cost` | Una prueba con datos existentes (minutos) frente a construir un pronóstico (imposible hoy). Gana la prueba. |
| 7. Memorable | `thinking-jobs-to-be-done` | «Cuando se dispara una alerta de lluvia, quiero saber si creerle antes de movilizar gente, para no gastar recursos ni perder credibilidad con falsas alarmas.» Hoy la sEAP usa un solo número. |
| 7. Memorable | `six-hats` (sombrero rojo) | Alivio: por fin el hallazgo sirve a alguien. Incomodidad: es un resultado con 8 eventos, y suena más grande de lo que es si se cuenta mal. |
