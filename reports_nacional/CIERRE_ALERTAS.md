# Cierre de la comparación de alertas del Yuna

15-nov-2026. Sustituye el alcance preventivo atribuido a la prueba de JANE_PREVENCION.md.

## Resultado para la entrega

**Un segundo producto reduce los episodios de disparo sin inundación catalogada en esta comparación histórica.
No se ha demostrado anticipación.** No es una alerta operativa, ni una evaluación del sistema de la Cruz Roja.

Se conserva el umbral >100 mm, el catálogo, los periodos, el agrupamiento y la puntuación del análisis anterior.
Se separa el efecto de quitar fechas futuras del efecto de corregir el acumulado espacial de CHIRPS. La versión
de cierre es la de misma celda de `JANE_PREVENCION_CAUSAL.md`; las otras filas son controles históricos.
No se optimiza un nuevo umbral. La alternativa del mismo día es exploratoria, no una nueva predicción acertada.

| Regla, prueba 2016–2024 | Eventos detectados | Episodios sin evento catalogado | Episodios totales | Primera señal anterior al inicio catalogado | Primera señal durante el evento |
|---|---:|---:|---:|---:|---:|
| IMERG | 7/8 | 39 | 48 | 0 | 7 |
| Confirmación original ±1 día (admite futuro) | 7/8 | 20 | 29 | 0 | 7 |
| Confirmación del mismo día o el anterior | 7/8 | 20 | 29 | 0 | 7 |
| Confirmación del mismo día | 7/8 | 19 | 28 | 0 | 7 |
| **Cierre: CHIRPS 48 h en misma celda, hoy o ayer** | **6/8** | **16** | **24** | **0** | **6** |

Eliminar el día futuro no cambia los totales originales en 2016–2024. Al corregir también el acumulado espacial,
la reducción es 39→16 (59,0 %), a cambio de perder el evento 2022-09. Eso no vuelve disponible CHIRPS en tiempo real.
En 2001–2015 la versión de cierre detecta 4/6 frente a 5/6 de IMERG y reduce episodios sin evento catalogado
de 89 a 35: el coste de sensibilidad aparece en ambas muestras.

**Antes y mismo día no son equivalentes:** el informe causal agrupa «antes o el día de inicio» y obtiene 2/8
para IMERG y 1/8 con testigo. Esta auditoría los separa: no hay primeros disparos en una fecha estrictamente anterior
al inicio en la muestra de prueba. Los del mismo día usan lluvia de ese día completo: no prueban anticipación.

## Qué se comprobó

- Reproducción exacta del resultado previo: 7/8 y 39; con confirmación ±1 día, 7/8 y 20.
- Reproducción de la versión de misma celda: 6/8 y 16.
- Prueba sintética de causalidad temporal: cambiar la confirmación futura no altera la señal presente de la nueva regla.
- Clasificación por evento: señal anterior a la fecha de inicio, durante el evento, o ninguna.
- Cota ideal ilustrativa: una señal fechada en t que usa el día completo no estaría disponible antes de t+1,
  incluso sin latencia de publicación. En la prueba, ningún evento presenta margen positivo bajo esa cota.
- Serie diaria sin huecos y sin fechas duplicadas; hashes de los dos archivos de entrada.

## Límites que permanecen

1. **Disponibilidad.** No se reconstruyen las fechas de publicación de IMERG Final ni CHIRPS. Esta auditoría
   elimina la mirada explícita a mañana en la regla, pero no el uso retrospectivo de productos tardíos.
2. **Espacio.** Solo las filas de control sin «misma celda» conservan la suma de máximos diarios potencialmente
   de celdas diferentes. La fila de cierre corrige ese defecto; las resoluciones de ambos productos siguen siendo distintas.
3. **Tiempo del impacto.** Las fechas de inicio del catálogo tienen precisión diaria o semanal; no se conoce
   la hora real del comienzo. «Durante» describe la posición frente al catálogo, no un tiempo de aviso operacional.
4. **Catálogo.** Un episodio sin evento catalogado puede corresponder a una inundación no registrada.
5. **Selección.** Los ocho eventos se han reutilizado en exploraciones anteriores: no son una validación externa nueva.
6. **Unidades.** La puntuación heredada mezcla detección por evento y falsos disparos por episodio. Por eso 48−39=9
   episodios asociados no equivale a 9 inundaciones: hay 7 eventos detectados. No llamar al CSI «acierto global».

## Decisión de cierre

Mostrar esta prueba como **evaluación histórica de un filtro**, con la regla de misma celda y sus costes.
No convertir el filtro en una orden de esperar confirmación o de movilizar personas.
La conexión con prevención es una propuesta de mejora del monitoreo y de preparación, no una reducción de daños
ya demostrada. GOES, nuevos sensores y nuevos pronósticos quedan fuera de la entrega de esta iteración.

La validación futura requerirá productos disponibles a la hora de decisión, acumulados espaciales equivalentes,
eventos con hora de inicio, registro de señales emitidas y costes de demora/omisión. No se abre esa investigación ahora.

## Reproducción

`docker compose run --rm --no-deps --entrypoint uv tropical run --frozen --no-sync python -m earthmemory.tropical.cierre_alertas`

Código: `earthmemory/tropical/cierre_alertas.py`. Salidas: `results/tropical/cierre_alertas/comparacion.csv`,
`eventos.csv`, `evidencia.json`. No requiere red ni credenciales; usa las tablas ya calculadas.
