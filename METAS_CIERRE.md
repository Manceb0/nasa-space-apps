# Metas de cierre de Stellar Horizons

Objetivo: terminar una versión defendible y útil sin seguir ampliando hipótesis. 15-nov-2026.

## 1. Cerrar la evidencia que puede entrar a la demo

**Hecho:** auditoría ejecutada de la confirmación temporal del Yuna. Reproduce el resultado anterior y evalúa
reglas sin confirmación futura. Ver `reports_nacional/CIERRE_ALERTAS.md` y sus CSV por evento.

- Resultado de cierre con CHIRPS de la misma celda: 6/8 y 16 episodios sin evento catalogado, frente a 7/8 y 39.
- Los resultados 7/8 y 20 (o 19) conservaban el proxy espacial antiguo: solo sirven como controles históricos.
- Ninguna primera señal precede estrictamente al inicio catalogado en la prueba 2016–2024.
- Cierre: filtro histórico prometedor; anticipación y prevención de daños no demostradas.

**Regla de parada:** no nuevas descargas ni búsqueda de un culpable GOES. Solo se reabre ciencia si hay un error
que afecte a lo mostrado. No sustituir investigación pendiente por afirmaciones generales de imposibilidad.

## 2. Cerrar un recorrido y su utilidad

**Hecho:** recorrido implementado en Tendencias, entrada «Recorrido · 90 s». Comprobado en la compilación
de producción a 1280×800, 390×844 y 360×740 (móvil emulado). Resultado guardado en
`reports_nacional/VERIFICACION_RECORRIDO.json`; capturas `reports_nacional/recorrido-yuna-*.png`.
Un recorrido principal, tres momentos:

| Momento | Qué muestra | Para qué sirve |
|---|---|---|
| 0–25 s: investigar | Región, variable, serie NASA, tasa y confianza; contraste con CHIRPS | Entender qué tendencia puede sostener la planificación |
| 25–50 s: comprobar | Cuatro umbrales ya calculados; diferencia entre cambio de definición y pérdida de potencia | Evitar presentar una conclusión frágil como certeza |
| 50–90 s: aplicar | Caso Yuna: señal IMERG frente a confirmación de hoy/ayer, CHIRPS 48 h en misma celda; 39→16 episodios sin evento catalogado, detecciones 7/8→6/8, 0 señales estrictamente anteriores al inicio | Mostrar una vía concreta para evaluar filtros de monitoreo, con su coste y alcance |

Frase de producto: **«Investigamos cómo cambia el agua y qué evidencia respalda las señales con las que nos preparamos».**

La serie sintética del 74,6 % queda documentada en la revisión científica, fuera del recorrido obligatorio.
La comparación de reglas es histórica. La web no emite recomendaciones operativas de evacuación ni avisos en vivo.
No se afirma que IMERG y CHIRPS sean testigos totalmente independientes.

Criterios comprobados:

- El recorrido puede completarse en móvil y escritorio sin cambiar de aplicación.
- Cada cifra lleva periodo, denominador, unidad y fuente accesibles.
- «0 disputas» nunca aparece como demostración de acuerdo; GOES dice «sin resolver».
- Las detecciones 7/8 y 6/8 se distinguen de anticipación: 0 primeras señales estrictamente anteriores al inicio catalogado.
- El tercer momento explica su uso potencial en preparación sin afirmar beneficios operativos validados.

## 3. Verificar y preparar la entrega

**Hecho:** `npm run build` pasó (TypeScript y Vite), seguido de pruebas del recorrido en navegador sobre `vite preview`.
La advertencia de tamaño del paquete persiste; no impidió cargar ni completar las pruebas.

Entregables verificados para la versión local:

- Recorrido renderizado: cuatro umbrales, comparación base/confirmación, ocho eventos, descarga JSON,
  ausencia de desbordamiento horizontal en la comparación, Escape y restitución de foco. Inglés comprobado.
- README, recorrido y `reports_nacional/GUION_ENTREGA_90S.md` usan el mismo resultado 39→16 y 7/8→6/8,
  con ausencia de anticipación demostrada. El antiguo pitch sigue marcado como superado.
- `reports_nacional/RESPALDO_DEMO.html` se abre desde disco con cero peticiones HTTP:
  `reports_nacional/VERIFICACION_RESPALDO.json`. Se genera desde las mismas salidas con
  `python scripts/exportar_recorrido.py`.
- Cambios de cierre registrados en Git. No se hizo push ni se cambió la visibilidad del repositorio.

La versión local está lista para ensayo y entrega al responsable. No equivale a una evaluación por usuarios
externos, prueba en teléfono físico ni publicación en el portal del concurso.

## Repetir la comprobación

1. `python scripts/exportar_recorrido.py`
2. En `web/`: `npm run build` y `npm run preview -- --host 127.0.0.1` (puerto 4180).
3. Desde la raíz: `npx --yes --package @playwright/cli playwright-cli -s=stellar-cierre open http://127.0.0.1:4180 --browser msedge`
4. `npx --yes --package @playwright/cli playwright-cli -s=stellar-cierre --raw run-code --filename=scripts/verificar_recorrido.js`

No añadir módulos, nuevos competidores ni más casos al recorrido hasta superar estas tres metas.
