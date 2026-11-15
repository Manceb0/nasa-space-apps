# Del reto a la evidencia (15-nov-2026)

Cada frase del reto y cada criterio del jurado, con la prueba que lo sostiene y dónde está. Las cifras salen de
`ESTADO_CONCLUSIONES.md`, que manda si algo difiere. Sirve para el texto de la entrega y para el vídeo.

## La respuesta en una frase

**En República Dominicana, lo que más cambia en la lluvia medida por satélite es cómo IMERG cuenta los días de lluvia,
no la lluvia misma; y las inundaciones del Yuna vienen de dos máquinas distintas (ciclones y vaguadas), que piden
dos alertas distintas.**

## Frase por frase del reto

| El reto dice | Nuestra respuesta | Evidencia |
|---|---|---|
| «Una variable puede mostrar una tendencia en una región y la opuesta en otra, incluso respondiendo al mismo proceso» | En el **mismo** territorio, la frecuencia de días de lluvia baja 5 pp en IMERG, no cambia en CHIRPS y sube 9 pp en MERRA-2. La herramienta dice cuál cambió de verdad | Fila 7b; `results/tropical/merra2` |
| «Seleccionar variables, de misiones o de modelos» | 21 índices de lluvia de IMERG (misión GPM) y CHIRPS; vegetación MODIS; humedad SMAP y GLDAS (modelo); MERRA-2 y ERA5 (reanálisis) | `TENDENCIAS_P0.md`; web, Tendencias |
| «Visualizar su evolución en el tiempo» | Series por provincia y celda 2001-2024, con el punto de cambio marcado | Web, Tendencias |
| «Qué está cambiando» | Los días de lluvia ligera en IMERG: −7,2 pp con umbral de 0,1 mm, −4,8 con 1 mm, −2,0 con 5 mm. Las tendencias de intensidad y rachas secas de IMERG heredan ese cambio | Fila 4c (umbral), filas 4-5 |
| «Dónde» | En todo el país: IMERG cae más que CHIRPS en el 99 % de las celdas a 1 mm y en los 15 recuadros MERRA-2. Y fuera: en Puerto Rico, frente a 18 de 19 pluviómetros | Filas 6, 7b, 4d |
| «Cuánto» | Unos 5 pp de días húmedos (de cada 100 días, 5 lluviosos menos), con escalón hacia 2018 | Filas 6-7 |
| «Si es significativo» | Sí para el instrumento (p < 0,001 frente a cada testigo). No para el clima: 0 tendencias robustas en 21 índices; un cambio en extremos tendría que ser de 39 mm/década para detectarse | Filas 1-2, 4 |

## Los cuatro criterios, a nivel 5

| Criterio | Qué pide el 5 | Nuestra prueba |
|---|---|---|
| **Impacto** | Problema significativo, alcance amplio, beneficia a mucha gente | Las inundaciones del Bajo Yuna (14 en 2001-2024; Fiona: 1,4 millones de afectados a nivel nacional). En ciclones, el aviso oficial del NHC dio 40-106 h de margen en 4 de 6; la alerta con testigo baja las falsas alarmas de 39 a 16. El método se aplica fuera de la RD: en Puerto Rico, IMERG pierde días frente a 18 de 19 pluviómetros que no cambian (fila 4d) |
| **Creatividad** | Enfoque nunca intentado, desafía métodos convencionales | Auditar el instrumento antes de creer la tendencia: testigos independientes, contraejemplos sintéticos y predicciones registradas antes de calcular. Separar las inundaciones por mecanismo antes de evaluar la alerta |
| **Validez** | Científicamente sólido, factible, usable | 26+ predicciones registradas antes de calcular (las fallidas publicadas), validación sintética del método, 4 testigos (CHIRPS, ERA5, pluviómetros, MERRA-2 descartado por su propio salto), 4 conclusiones propias retiradas tras revisión (escalón de 2013, el 82 %, la prueba GOES diaria, el backtest que miraba al día siguiente). App funcionando con pruebas automáticas |
| **Relevancia** | Responde de lleno al reto; los datos NASA son el centro | La tabla de arriba, frase por frase. El hallazgo central ES sobre un producto NASA (IMERG) y usa MERRA-2, GLDAS, SMAP y MODIS |

## Lo que no afirmamos

- Que la lluvia real de la RD haya cambiado: no hay pluviómetros densos dominicanos para comprobarlo.
- La causa del cambio de IMERG: GOES-16 y el ATMS de NOAA-20 entraron con 19 días de diferencia.
- Que predecimos inundaciones: en las que no son de ciclón, ninguna señal llega antes.
