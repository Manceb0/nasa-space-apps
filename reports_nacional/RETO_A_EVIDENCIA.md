# Del reto a la evidencia (15-nov-2026)

Cada frase del reto y cada criterio del jurado, con la prueba que lo sostiene y dónde está. Las cifras salen de
`ESTADO_CONCLUSIONES.md`, que manda si algo difiere. Sirve para el texto de la entrega y para el vídeo.

## La respuesta en una frase

**En República Dominicana, lo que más cambia en la lluvia medida por satélite es cómo IMERG cuenta los días de lluvia,
no la lluvia misma. No es una rareza local: frente a 60 pluviómetros de Puerto Rico y Hawái, en dos océanos, IMERG
pierde días que los pluviómetros no pierden. Y las inundaciones del Yuna vienen de dos máquinas distintas (ciclones
y vaguadas), que piden dos alertas distintas.**

## Frase por frase del reto

| El reto dice | Nuestra respuesta | Evidencia |
|---|---|---|
| «Una variable puede mostrar una tendencia en una región y la opuesta en otra, incluso respondiendo al mismo proceso» | En el **mismo** territorio, la frecuencia de días de lluvia baja 5 pp en IMERG, no cambia en CHIRPS y sube 9 pp en MERRA-2. La herramienta dice cuál cambió de verdad | Fila 7b; `results/tropical/merra2` |
| «Seleccionar variables, de misiones o de modelos» | 21 índices de lluvia de IMERG (misión GPM) y CHIRPS; vegetación MODIS; humedad SMAP y GLDAS (modelo); MERRA-2 y ERA5 (reanálisis) | `TENDENCIAS_P0.md`; web, Tendencias |
| «Visualizar su evolución en el tiempo» | Series por provincia y celda 2001-2024, con el punto de cambio marcado | Web, Tendencias |
| «Qué está cambiando» | Los días de lluvia ligera en IMERG: −7,2 pp con umbral de 0,1 mm, −4,8 con 1 mm, −2,0 con 5 mm. Las tendencias de intensidad y rachas secas de IMERG heredan ese cambio | Fila 4c (umbral), filas 4-5 |
| «Dónde» | En todo el país: IMERG cae más que CHIRPS en el 99 % de las celdas a 1 mm y en los 15 recuadros MERRA-2. Y fuera: en Puerto Rico, frente a 18 de 19 pluviómetros, y en Hawái, en el otro océano y bajo otro satélite geoestacionario, frente a 39 de 41 | Filas 6, 7b, 4d, 8b |
| «Cuánto» | Unos 5 pp de días húmedos en la RD (de cada 100 días del calendario, 5 lluviosos menos). Llega en dos escalones: con el paso de la era TRMM a la GPM (2014: −9,6 pp en Hawái, −6,2 en Puerto Rico frente a pluviómetros) y otro después de 2018 que se ve en el Caribe (−3,5 Puerto Rico, −4,5 RD frente a CHIRPS) y no en Hawái | Filas 6-7, 8b |
| «Si es significativo» | Sí para el instrumento (p < 0,001 frente a cada testigo). No para el clima: 0 tendencias robustas en 21 índices; un cambio en extremos tendría que ser de 39 mm/década para detectarse | Filas 1-2, 4 |

## Los cuatro criterios, a nivel 5

| Criterio | Qué pide el 5 | Nuestra prueba |
|---|---|---|
| **Impacto** | Problema significativo, alcance amplio, beneficia a mucha gente | Las inundaciones del Bajo Yuna (14 en 2001-2024; Fiona: 1,4 millones de afectados a nivel nacional). En ciclones, el aviso oficial del NHC dio 40-106 h de margen en 4 de 6; la alerta con testigo baja las falsas alarmas de 39 a 16. El método se aplica fuera de la RD: en Puerto Rico, IMERG pierde días frente a 18 de 19 pluviómetros que no cambian (fila 4d). Alcance: desde 2018, 2.853 trabajos publicados usan IMERG; 206 calculan tendencias, 204 sequía y 383 frecuencia, las medidas que hereda la pérdida de días (fila 8d, cota). El propio equipo de IMERG reconoce inhomogeneidades en V07 y las corrige en V08 (fila 8c): auditar antes de creer una tendencia sirve hoy y servirá para comprobar V08 |
| **Creatividad** | Enfoque nunca intentado, desafía métodos convencionales | Auditar el instrumento antes de creer la tendencia: testigos independientes, contraejemplos sintéticos y predicciones registradas antes de calcular. Separar las inundaciones por mecanismo antes de evaluar la alerta. Usar el planeta como laboratorio: Hawái, bajo otro satélite geoestacionario, separa dos causas que en el Caribe llegaron con 19 días de diferencia |
| **Validez** | Científicamente sólido, factible, usable | Trazabilidad completa en `TRAZABILIDAD.md`: cada prueba con su pregunta, datos, script, predicciones con hora de registro anterior al resultado, veredicto, huellas SHA-256 y commit. Predicciones registradas antes de calcular (las fallidas publicadas), validación sintética del método, 4 testigos (CHIRPS, ERA5, pluviómetros, MERRA-2 descartado por su propio salto), 4 conclusiones propias retiradas tras revisión (escalón de 2013, el 82 %, la prueba GOES diaria, el backtest que miraba al día siguiente). App funcionando con pruebas automáticas |
| **Relevancia** | Responde de lleno al reto; los datos NASA son el centro | La tabla de arriba, frase por frase. El hallazgo central ES sobre un producto NASA (IMERG) y usa MERRA-2, GLDAS, SMAP y MODIS |

## Lo que no afirmamos

- Que la lluvia real de la RD haya cambiado: no hay pluviómetros densos dominicanos para comprobarlo.
- La causa exacta. Sabemos que no es solo el GOES-16: la pérdida aparece también en Hawái, bajo GOES-West, y su escalón grande coincide con el paso de la era TRMM a la GPM en 2014. El escalón caribeño de 2018 es compatible con el GOES-16, sin probar. El propio equipo de IMERG reconoce inhomogeneidades en V07 (fila 8c).
- Que predecimos inundaciones: en las que no son de ciclón, ninguna señal llega antes.
