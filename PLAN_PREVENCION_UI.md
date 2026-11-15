# Plan · la prevención dentro del diseño de Tendencias

15-nov-2026, 13:10. Cierre a las 23:59; meta interna a las 20:00.

## Decisión

El diseño de Tendencias se mantiene: mapa a pantalla completa, panel izquierdo con preguntas y veredicto grande.
La prevención entra como **una pregunta más**, igual que «¿Y la vegetación?». No va en una página aparte con otro estilo.

- `#tendencias` vuelve a ser la portada.
- «Preparar» sale del menú. Su ruta `#preparar` sigue funcionando, oculta.
- El botón «Recorrido · 90 s» sale de la cabecera.
- No se borra código ni datos de la otra sesión: `src/preparacion/`, `recorrido.ts`, `preparacion.json` y `recorrido.json` siguen en disco.
  Se reutiliza su lógica (`motor.ts`), no su interfaz.

## Alcances nuevos y dónde viven

Bloque nuevo al final del panel, debajo de la vegetación: **«¿Y para prevenir?»**. Lleva tres preguntas.

| # | Pregunta en el panel | Qué muestra | Datos ya calculados | En el mapa |
|---|---|---|---|---|
| 1 | ¿Alertar con un solo satélite? | Inundaciones del Yuna, prueba 2016–2024: con IMERG solo, 7 de 8 detectadas y 39 disparos sin evento. Con CHIRPS como testigo en la misma celda: 6 de 8 y 16. El mismo medidor y el mismo veredicto grande. | `results/tropical/cierre_alertas/` y `recorrido.json` | Cuenca del Yuna resaltada, con la línea que ya existe |
| 2 | ¿Cómo está mi municipio hoy? | Cuatro pilotos (Bonao, Cotuí, Villa Riva y Monte Cristi), cada uno con su lluvia prevista de 48 h (ECMWF frente a GFS) y su déficit de 30 y 90 días (percentil ERA5). Una tarea de verificación en una línea. | `preparacion.json` y `motor.ts` | Pilotos como marcadores `.site` |
| 3 | ¿Dónde falta medir? | Prioridad de medición: dónde los productos discrepan y no hay estación cerca. | `preparacion.json` (`measurement_priority`) | Capa de color de las celdas en crestas y 3D |

**Frase de portada** (en la pista bajo el lugar):
«Antes de alertar con un dato, mira si sus testigos están de acuerdo».

### Límites que se muestran en un plegable, nunca como párrafo

- No se ha demostrado anticipación.
- Es un prototipo de apoyo, no una alerta operativa.
- El umbral de 100 mm es exploratorio.
- Un percentil bajo no es una declaración de sequía.

## Orden de trabajo (por valor para el jurado)

1. **Pregunta 1, el Yuna**, en unos 90 minutos. Es la que convierte «los datos se contradicen» en «así se evita una falsa alarma». Es la más fuerte.
2. **Pregunta 2, los pilotos**, en unos 2 horas. Se reutiliza `investigate()` de `motor.ts`, con nuestra interfaz: sin tablas ni casillas.
3. **Pregunta 3, la prioridad**, en 1 hora, como capa del mapa.
4. **Comprobación**, en 1 hora:
   - `tsc`;
   - el inspector de taste-skill, con 0 FAIL;
   - el teléfono emulado;
   - el inglés.

Si el tiempo aprieta, se entregan 1 y 4. Los puntos 2 y 3 quedan como la siguiente fase en el pitch.

## Pendiente de coordinar

- `README.md` y `METAS_CIERRE.md` (cambios sin commit de la otra sesión) dicen que `#preparar` es la entrada por defecto. Hay que corregirlos cuando se cierre esto.
- La presentación de 7 diapositivas de `entrega/` y el guion municipal de 90 s se apoyan en `#preparar`. Hay que alinearlos con el bloque «¿Y para prevenir?».
