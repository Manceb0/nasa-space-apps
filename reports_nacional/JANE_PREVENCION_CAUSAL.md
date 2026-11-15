# Segunda pasada Jane: alerta con testigo, versión causal (15-nov-2026, noche)

Sustituye la prueba de `JANE_PREVENCION.md`. La revisión señaló tres fallos y los tres estaban en el código:
- `near(C)` incluía el día **siguiente**, así que la confirmación podía venir del futuro.
- «Detectado» aceptaba disparos **durante** la inundación.
- Para CHIRPS se sumaban máximos diarios de **celdas distintas**.

La versión nueva (`earthmemory/tropical/alerta_causal.py`, salidas en `results/tropical/alerta_causal/`):
- Confirma solo con información del mismo día o del anterior.
- Usa la suma de 48 h **en la misma celda** también para CHIRPS.
- Separa el **momento** del primer disparo y mide el **retraso** que añade la confirmación.

Las predicciones M1-M3 se registraron antes de correr.

## 1. La deducción

**La alerta con testigo sobrevive sin mirar al futuro y casi no cuesta tiempo, pero no anticipa. Lo que previene es
movilizar en falso, no la inundación.** En la prueba 2016-2024:
- Pedir el testigo de CHIRPS deja las falsas alarmas en 16 en vez de 39, detecta 6 de 8 eventos en vez de 7 y no
  retrasa la alerta en 5 de los 6 eventos comunes.
- Pero, con un satélite o con dos, la regla casi siempre se dispara **durante** la inundación. Solo 2 de 8 eventos
  (IMERG solo) o 1 de 8 (con testigo) tuvieron disparo antes o el día del inicio.

## 2. Las pistas

| Prueba 2016-2024 (8 eventos) | Detectados | Antes o el día del inicio | Durante | Falsas alarmas | CSI [IC 95 %] |
|---|---|---|---|---|---|
| IMERG solo (> 100 mm en 48 h) | 7 | 2 | 5 | 39 | 0,15 [0,08-0,21] |
| CHIRPS solo (48 h, misma celda) | 7 | 5 * | 2 | 55 | 0,11 [0,05-0,16] |
| **IMERG con testigo CHIRPS (mismo día o anterior)** | **6** | 1 | 5 | **16** | **0,25 [0,12-0,42]** |

\* La aparente anticipación de CHIRPS probablemente es un artefacto **[INFERIDO]**. Su diario se reparte desde la
péntada con proporciones de pronóstico, así que el momento de su lluvia no es fiable. Además, no llega en tiempo real.

- **Calibración 2001-2015:** IMERG solo detecta 5 de 6 con 89 falsas alarmas; con testigo, 4 de 6 con 35.
- **Retraso que añade la confirmación:** 0 días en 5 de 6 eventos de prueba y 1 día en 1 (`retraso_confirmacion.csv`).
- **El evento que se pierde** al pedir testigo es 2022-09 (CHIRPS no pasó de 100 mm en ninguna celda). **2024-11** no
  lo detecta ninguna regla con IMERG.

| Predicción | Resultado | Veredicto |
|---|---|---|
| M1: con testigo causal, ≥ 6 de 8 eventos y falsas alarmas ≤ 60 % de IMERG solo | 6 de 8; 16 de 39 (41 %) | Se cumple |
| M2: la confirmación retrasa ≥ 1 día en la mitad de los eventos | 1 de 6 | **No se cumple**: confirmar casi no cuesta tiempo |
| M3: con IMERG solo, menos de la mitad de los eventos tienen disparo anticipado | 2 de 8 | Se cumple: la regla no es una alerta temprana |

## 3. Lo evidente y por qué no basta

1. **«La alerta con testigo previene inundaciones».** No: casi nunca avisa antes. Lo que mejora es la **confianza para
   actuar** cuando la lluvia ya está cayendo.
2. **«Exigir siempre confirmación».** En un caso urgente, esperar puede costar. Aquí costó 1 día en 1 de 6 eventos,
   pero hizo perder uno (2022-09).
3. **«Usar lluvia observada para anticipar».** La anticipación tendría que venir del **pronóstico** (lo que usa la sEAP
   de la Cruz Roja), no de la lluvia ya caída.

## 4. Rutas

| Ruta | Mecanismo | Estado |
|---|---|---|
| A. Alerta con testigo única | Movilizar solo si los dos productos coinciden | Pierde 2022-09; esperar puede perjudicar |
| **B. Alerta en dos niveles** | **Pre-alerta** con un producto (acciones baratas: avisar, verificar, preparar). **Alerta** cuando llega el testigo (acciones caras: movilizar, evacuar) | Usa los números de arriba: confirmar costó 0 días en 5 de 6 |
| C. Testigo para el pronóstico | Aplicar el mismo principio a dos modelos de pronóstico (datos de fuera de la NASA) | Sin probar; habría pocos eventos con pronósticos archivados |
| D. Dónde falta un testigo | Priorizar pluviómetros donde más discrepan los productos | Planificación, no requiere validación de alerta |

## 5. Prueba en contra

- **B (`the-fool` y `thinking-steel-manning`):**
  - **La objeción más fuerte:** con 8 eventos, los intervalos de CSI se solapan (0,08-0,21 frente a 0,12-0,42). Es
    una dirección, no una mejora demostrada.
  - **El catálogo es de prensa:** las «falsas alarmas» son una cota superior.
  - **2022-09:** la pre-alerta con IMERG sí lo marca, así que no se pierde del todo.
  - **Respuesta:** presentarlo como «una regla de dos niveles probada en 8 eventos», nunca como «evita
    inundaciones».
- **C:** sin pronósticos archivados para 2016-2024 no se puede validar hoy. Queda como siguiente paso explícito.
- **Pre-mortem:** decir «nuestra alerta anticipa» y que un juez pregunte cuántas avisaron antes. La respuesta honesta
  es 1 o 2 de 8, y el pitch tiene que decirlo primero.

## 6. Decisión

**B (dos niveles) más D**, sobre la herramienta de tendencias. La pre-alerta conserva la rapidez de un solo satélite;
el testigo da la confianza para las acciones caras. C es el siguiente paso, con datos de fuera de la NASA (pronósticos).

Cambiaría de opinión si, con pronósticos archivados (aunque sean pocos eventos), el testigo de pronóstico avisara antes
del inicio en la mayoría de los casos. Entonces C pasaría al frente.

## 7. Entregable

**La frase:** *«A first warning from one satellite, a confirmed alarm when a second agrees: in the Yuna basin
(2016-2024) confirmation cut false alarms from 39 to 16 and almost never cost time, but rain-based rules mostly fire
once flooding has started, so real anticipation needs forecasts.»*

**Paso del recorrido:** «Pre-alerta / Alerta confirmada» sobre la línea de tiempo de cada evento del Yuna. Muestra el
primer disparo de cada regla frente al inicio de la inundación, con los 39 frente a 16 y la honestidad de «1 de 8
avisó antes».

## 8. Lentes usadas, fila por fila

| Fila | Skill | Qué reveló |
|---|---|---|
| 1. Escena | `thinking-map-territory` | Las tres críticas se confirmaron en el código (`shift(-1)`, la ventana hasta el fin del evento, la suma entre celdas). El mapa de «7 de 8, 39 a 20» no era el territorio. |
| 2. Premisa | `thinking-first-principles` | El primitivo de prevenir es el **tiempo de aviso**, no «detectar». «Detectado» era una convención del backtest; se separó en antes, durante o ninguno. |
| 3. Ideas | `lateral` → `analogy` | Dos etapas antes de actuar: el cribado médico con prueba confirmatoria y la preseñal de una alarma de incendio que se verifica antes de la alarma general **[SIN VERIFICAR como norma concreta]**. El mecanismo común es actuar barato pronto y caro al confirmar. |
| 3. Ideas | `physical-contradictions` | La alerta debe ser inmediata (para ganar tiempo) y confirmada (para no movilizar en falso). Se resuelve con separación en el tiempo y por condición: pre-alerta y alerta. |
| 3. Ideas | `thinking-second-order` | Menos falsas alarmas → más confianza → más respuesta cuando importa. Efecto plausible **[INFERIDO, sin fuente verificada aquí]**. |
| 4. Detalle | `thinking-scientific-method` | El backtest causal con predicciones registradas: M1 se cumple, M2 falla (confirmar no cuesta tiempo) y M3 se cumple (no anticipa). |
| 5. En contra | `the-fool` (falsación) y `thinking-steel-manning` | Los IC se solapan con 8 eventos; las falsas alarmas son cota superior; esperar puede perjudicar. De ahí los dos niveles en vez de una sola regla. |
| 6. Decisión | `thinking-margin-of-safety` | Ante un daño potencialmente grave, no se espera para las acciones baratas. El margen va en la pre-alerta; la confirmación solo se exige para lo caro. |
| 7. Memorable | `thinking-jobs-to-be-done` y `six-hats` (sombrero rojo) | «Cuando cae lluvia peligrosa, quiero saber qué hacer ya y qué esperar a confirmar.» Incomodidad: «no anticipa» suena a fracaso. Alivio: es verdad y es útil, y el pronóstico es el paso siguiente claro. |
