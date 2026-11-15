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

**Guion fijado; pendiente comprobarlo en la interfaz renderizada.** Un recorrido principal, tres momentos:

| Momento | Qué muestra | Para qué sirve |
|---|---|---|
| 0–25 s: investigar | Región, variable, serie NASA, tasa y confianza; contraste con CHIRPS | Entender qué tendencia puede sostener la planificación |
| 25–50 s: comprobar | Cuatro umbrales ya calculados; diferencia entre cambio de definición y pérdida de potencia | Evitar presentar una conclusión frágil como certeza |
| 50–90 s: aplicar | Caso Yuna: señal IMERG frente a confirmación de hoy/ayer, CHIRPS 48 h en misma celda; 39→16 episodios sin evento catalogado, detecciones 7/8→6/8, 0 señales estrictamente anteriores al inicio | Mostrar una vía concreta para evaluar filtros de monitoreo, con su coste y alcance |

Frase de producto: **«Investigamos cómo cambia el agua y qué evidencia respalda las señales con las que nos preparamos».**

La serie sintética del 74,6 % queda en «Poner a prueba el método», como evidencia opcional; no ocupa otro paso obligatorio.
La comparación de reglas es histórica. La web no emite recomendaciones operativas de evacuación ni avisos en vivo.
No se afirma que IMERG y CHIRPS sean testigos totalmente independientes.

Criterios para dar esta meta por terminada:

- El recorrido puede completarse en móvil y escritorio sin cambiar de aplicación.
- Cada cifra lleva periodo, denominador, unidad y fuente accesibles.
- «0 disputas» nunca aparece como demostración de acuerdo; GOES dice «sin resolver».
- Las detecciones 7/8 y 6/8 se distinguen de anticipación: 0 primeras señales estrictamente anteriores al inicio catalogado.
- El tercer momento explica su uso potencial en preparación sin afirmar beneficios operativos validados.

## 3. Verificar y preparar la entrega

**Hecho:** `npm run build` pasó (TypeScript y Vite). Esto no prueba la experiencia visual.

Pendiente antes de declarar la versión lista:

- Revisar el recorrido renderizado en móvil y escritorio: controles, textos, fuentes y navegación.
- Comprobar que README, demo y pitch cuentan la misma historia y usan el resultado de cierre.
- Preparar un guion de 90 s y una copia de respaldo que funcione con resultados locales.
- Verificar el estado de Git y la versión concreta a entregar. Publicación y visibilidad se resuelven
  dentro de las instrucciones explícitas del usuario; este documento no las ejecuta.

No añadir módulos, nuevos competidores ni más casos al recorrido hasta superar estas tres metas.
