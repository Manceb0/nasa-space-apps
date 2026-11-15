# Revisión independiente de la pasada Jane

15-nov-2026 · revisión de HEAD `a5262a4` y archivos nuevos presentes durante la sesión.

**Veredicto:** hay evidencia de diferencias temporales entre los productos y señales locales frente a estaciones que merecen seguirse. La historia «en octubre de 2013 cambió el instrumento y eso explica el 82 % de las contradicciones» todavía excede la evidencia. La reducción de disputas es reproducible, pero depende de un ajuste que también elimina tendencias sin escalón y que produce índices físicamente imposibles si se interpretan como observaciones corregidas.

Se revisaron `JANE_PITCH.md`, `PRUEBAS_TROPICALES.md`, `tropical/run.py`, `recalculo.py`, `sensibilidad_corte.py`, figuras y exportación/interfaz del recálculo, tablas y resultados asociados. Las comprobaciones nuevas están en `earthmemory/tropical/auditoria_revision.py` y `results/tropical/revision/`. No se modificaron el pitch, el motor, la interfaz ni sus resultados anteriores.

## 1. Prioridad alta: el ajuste no identifica un artefacto instrumental

En `recalculo.py:49` se estima para cada celda, índice y periodo:

`c = media(IM−CH después) − media(IM−CH antes)`

y se resta `c` al tramo posterior. Si IMERG y CHIRPS tienen tendencias graduales distintas, ese contraste también es distinto de cero, aunque no haya cambio abrupto.

**Prueba negativa ejecutada con la función original:** una serie sintética que sube linealmente de 100 a 123 en 2001–2024, sin ningún salto, frente a una referencia constante de 100. La variante A_frec reduce su pendiente OLS de 1 a 0,254 unidades/año: **74,6 % de reducción sin artefacto alguno**.

Esto no demuestra que el registro real sea homogéneo; demuestra que «el ajuste eliminó la tendencia» no discrimina entre tendencia y escalón. La frase del pitch «resuelve casi todo» debe sustituirse por «la conclusión es sensible a esta hipótesis de ajuste».

Además, no se estimó un único cambio del contador que después se propagó a los índices: se estimaron **muchos desplazamientos distintos**, uno por celda × índice × periodo, compartiendo un año de corte. «Un solo escalón» describe un corte común, no un solo parámetro físico.

**Falta para identificarlo:** comparación de tendencia gradual, cambio de nivel y ambos; incertidumbre de fecha y magnitud; contraste con referencia y metadatos del sistema de observación; validación fuera de los datos utilizados para ajustar.

## 2. Prioridad alta: Pettitt no demuestra que el cambio sea abrupto ni fecha una causa

La prueba actual elimina el ciclo mensual y permuta años, pero no distingue su alternativa de un cambio gradual. Con una segunda serie **sintética, lineal y sin discontinuidades**, el mismo Pettitt y el mismo nulo de 2999 permutaciones de bloques de 12 meses producen **p = 0,000333** y un corte en mitad de la serie.

La documentación de [Pettitt en wql](https://search.r-project.org/CRAN/refmans/wql/html/pett.html) advierte expresamente este problema. La revisión de [Lund et al.](https://arxiv.org/abs/2212.02674) explica que permitir tendencia y correlación puede cambiar las conclusiones sobre puntos de cambio.

**Diagnóstico adicional sobre los datos reales:** ajusté modelos a la diferencia mensual de frecuencia IMERG−CHIRPS, todos con efectos de mes calendario. Validación por ocho bloques retenidos de tres años; el corte se vuelve a seleccionar solo en los datos de entrenamiento. Es predicción de bloques omitidos, con entrenamiento que puede incluir años futuros, no pronóstico prospectivo.

| Modelo | RMSE en bloques retenidos | Corte en ajuste completo |
|---|---:|---|
| Solo estacionalidad | 0,08007 | — |
| Estacionalidad + tendencia | 0,07833 | — |
| Estacionalidad + escalón | 0,07858 | febrero de 2018 |
| Estacionalidad + tendencia + escalón | 0,07938 | enero de 2006 |
| Estacionalidad + curva cuadrática | 0,07923 | — |

Unidades: fracción de días húmedos. Las diferencias son pequeñas, sin prueba de superioridad estadística entre modelos. Los criterios OLS y Pettitt no buscan lo mismo: no se interpreta un corte alternativo como prueba de que 2013 sea falso. **Sí muestra que fecha y forma del cambio dependen del modelo**, y que en este diagnóstico el escalón no mejora claramente la predicción frente a la tendencia gradual.

El corte seleccionado por los modelos con escalón también cambia entre bloques omitidos. No presentar octubre de 2013 como fecha identificada con precisión instrumental. Permutar años mantiene el orden dentro de cada año, no toda la dependencia entre años.

## 3. Prioridad alta: la variante «sin el escalón» no es un registro de lluvia físicamente corregido

La resta aditiva de índices anuales/estacionales genera **8375 valores negativos celda-año-índice-periodo dentro de las 442 celdas incluidas**, sumando los distintos índices y periodos. No son 8375 celdas distintas.

Ejemplos:

| Índice y periodo | Valores negativos | Mínimo ajustado |
|---|---:|---:|
| SDII, seca | 28 | −3,53 mm/día |
| CDD, anual | 8 | −3,27 días |
| RACHAS15, temprana | 2359 | −1,52 rachas |
| RACHAS15, tardía | 2627 | −1,05 rachas |

Una serie centrada o un residuo estadístico puede ser negativo; un recuento físico de rachas o intensidad de precipitación no. El ajuste independiente de cada índice tampoco garantiza que exista una serie diaria compatible con todos ellos. Menos días húmedos no determina por sí solo las rachas: importa su orden temporal.

**Acción:** presentar A_frec como sensibilidad de índices bajo un desplazamiento asumido. No llamarla lluvia corregida o versión sin artefacto. No truncar negativos a cero: sería otra transformación sin validación. Si se quiere homogeneizar físicamente el registro, hay que definir y validar un modelo de observación sobre la distribución diaria y recalcular los índices desde esa serie.

Los p/q posteriores tratan la corrección estimada como si fuera conocida. No incorporan la incertidumbre de fecha, referencia y magnitud. Reutilizar el motor P0 reproduce el cálculo, pero no calibra la inferencia de todo el procedimiento adaptativo. La variante B que produce muchas tendencias tampoco demuestra que una referencia sea siempre indispensable: su inferencia posterior requiere revisar esa misma incertidumbre.

## 4. Prioridad alta: las estaciones apoyan una diferencia relativa, no «la lluvia no cambió»

La media original +0,2 pp oculta diferencias: Punta Cana pierde 4,8 pp de días húmedos; Puerto Plata gana 2,7 pp, por ejemplo. No se midió directamente una tendencia nacional de intensidad o rachas en estas cuatro estaciones. El video muestra cambios de frecuencias antes/después, no pendientes de los dos indicadores que afirma refutar.

Hice un control exploratorio: mismos días disponibles para los tres productos, meses con al menos 15 días, y el mismo peso para cada mes calendario observado antes y después.

| Estación | Meses calendario comparables | Cambio estación | Cambio IMERG | Cambio CHIRPS |
|---|---:|---:|---:|---:|
| Puerto Plata | 12 | +2,99 pp | −4,21 pp | +2,02 pp |
| Punta Cana | 12 | −5,13 pp | −12,98 pp | −2,03 pp |
| Barahona | 8 | +2,71 pp | −13,37 pp | −10,57 pp |
| Santo Domingo | 12 | +3,60 pp | −3,08 pp | +2,76 pp |

**La pista favorable se mantiene:** IMERG cae más que la estación en los cuatro sitios. **La cautela también:** CHIRPS cambia mucho en Barahona, faltan meses comparables, cobertura espacial e intervalos de incertidumbre. El archivo incluye sensibilidad a exigir 10/15/20 días por mes. No atribuir causalidad instrumental con este contraste local, posterior a elegir la fecha.

La afirmación «IMERG no es circular en frecuencia porque GPCC solo ajusta cantidades mensuales» necesita corregirse. El [documento técnico de IMERG V07, sección de postprocesado](https://gpm.nasa.gov/sites/default/files/2023-07/IMERG_TechnicalDocumentation_final_230713.pdf) indica que se aplica un factor a la precipitación de cada media hora. Aunque eso no cambie el soporte lluvia/cero, **sí puede cambiar cuántos días superan 1 mm**. Ejemplo aritmético: 0,8 mm × 1,5 = 1,2 mm. Esto no demuestra que una estación concreta entre en GPCC; impide afirmar independencia por ese argumento.

## 5. Prioridad media: la significancia espacial se presenta con una precisión que los desplazamientos no sostienen

El código sortea desplazamientos con reemplazo y acepta solo los que conservan suficiente solape. Los **466** son sorteos aceptados, no 466 traslaciones distintas. Enumeré exhaustivamente las traslaciones con el mismo criterio: son **82**.

| Asociación | p publicada, muestreo aleatorio | p exhaustiva, mismo criterio |
|---|---:|---:|
| Ascenso supuesto frente a log(CHIRPS/IMERG) | 0,00214 | 0,01205 |
| Diferencia de días húmedos frente a SDII en disputa | 0,00642 | 0,02410 |
| Sombra frente a CSI20 | 0,01713 | 0,03614 |

No se anula la asociación observada. Cambia la resolución de la prueba y la fuerza de la evidencia. Los resultados exhaustivos son sin corrección por la familia de asociaciones examinadas y dependen de aceptar el nulo toroidal en una isla con máscara irregular. La muestra de celdas comparables cambia con el desplazamiento.

Con la enumeración exacta usada aquí, la resolución mínima es 1/83. Revisar las conclusiones tras corrección por multiplicidad, sin usar estas tres pruebas seleccionadas como única familia si se examinaron más.

## 6. Prioridad media: ciclones aporta una pista válida, pero falta separar régimen y exposición

Se resolvió parte de la objeción pendiente: calculé ETS además de CSI y limité ambos grupos a agosto–noviembre.

| Grupo ASON | Días | CSI ≥50 mm | ETS ≥50 mm |
|---|---:|---:|---:|
| Con ciclón a <500 km | 183 | 0,269 | 0,239 |
| Sin ciclón a <500 km | 2745 | 0,101 | 0,097 |

La diferencia descriptiva **persiste** tras ese ajuste por aciertos esperables al azar; el resultado original no se explica simplemente por ese componente del CSI. No calculé IC nuevos para la diferencia ETS y ETS no elimina todos los efectos de frecuencia o sesgo. [NCEP explica ambas métricas y sus dependencias](https://cfs.ncep.noaa.gov/GFS_test/NewIce/www/precip/precip_body.html).

El código original compara 205 días con ciclón de todos los meses contra controles ASON. Al restringir también el primer grupo quedan 183; la pista cambia poco, pero conviene reportar el contraste emparejado por temporada.

**Lo que falta:** ausencia de ciclón en IBTrACS no identifica convección local; pueden intervenir frentes, vaguadas y ondas. Además, se etiqueta todo el país por proximidad del ciclón a alguna celda, no exposición local de cada celda. Repetir por sistema, distancia y mes, controlando cobertura/intensidad; no confundir coincidencia de excedencia de umbral en la misma celda con validación general de la morfología y del volumen de lluvia. P1 usa celda-días y confirmación direccional de IMERG; el 67 % de la auditoría usa otro agregado y otra definición. No intercambiar sus denominadores.

## 7. Prioridad media: el viento de barlovento todavía es supuesto

`WIND_FROM_DEG = 70.0` es una dirección fija ENE para todo el periodo. No se utilizaron vientos medidos/reanalizados de cada episodio. Hay asociación con exposición topográfica bajo ese viento supuesto; todavía no una atribución al viento que realmente sopló. Falta comparar direcciones alternativas y controlar costa, localización y gradientes climáticos, además de usar campos de viento adecuados.

## 8. Registro de hipótesis, texto y herramienta

- `predicciones_registradas.json` se escribe al comenzar cada corrida y solo guarda el día. La primera versión Git del código y del resultado aparece en el mismo commit. Es un registro local de hipótesis escrito antes de ejecutar las funciones; **la cronología previa a observar resultados no es verificable independientemente con esa evidencia**. Evitar presentarlo como preregistro externo e inmutable. Para el futuro: plan con timestamp, hash/commit previo y salidas separadas, conservando las revisiones exploratorias.
- «No hay salto en cantidad» debe ser «la prueba no detectó un cambio de cantidad»: p = 0,10 no establece equivalencia ni constancia.
- El 82 % es la reducción del total de combinaciones celda-índice-periodo clasificadas en disputa bajo A_frec. No porcentaje de clima falso, errores explicados, celdas independientes o fenómenos resueltos.
- El exportador conserva las clases y q del recálculo, incluidas clases «robustas» inducidas hacia CHIRPS. La interfaz permite ver esas capas. Debe distinguirse acuerdo inducido por referencia de corroboración entre fuentes; el aviso plegado no basta si el mapa conserva la etiqueta de robustez sin esa distinción.
- La figura 08 escribe **BH-FDR q = 0,05** en el pie, pero el motor usa **q ≤ 0,10**. Corregir figura y volver a exportarla antes de presentarla.
- README y pendientes siguen diciendo que las pruebas tropicales no se ejecutaron. Actualizar la guía de lectura para evitar dos estados contradictorios del proyecto.

## 9. El nuevo testigo ERA5: revisión del código disponible, resultado pendiente

Durante esta revisión aparecieron `era5_testigo.py`, `figura_era5.py` y el registro de predicciones. En el momento de inspección aún no estaba `results/tropical/era5/resumen.json`; no se interpreta un resultado que no estaba disponible ni se ejecuta otra descarga en paralelo.

Elegir explícitamente `models=era5` y UTC es adecuado para mantener un modelo consistente, según [Open-Meteo](https://open-meteo.com/en/docs/historical-weather-api). Pero ERA5 sigue siendo un reanálisis; el documento IMERG señala uso de ERA5 como información auxiliar de GPROF en Final, de modo que no se debe proclamar independencia completa. Registrar coordenadas de celda devueltas, unidades y procedencia para compararlas con las cajas IMERG/CHIRPS.

Las pruebas E3/E4 pasan si el punto global más fuerte queda fuera de la ventana prevista o no resulta significativo. Eso no prueba homogeneidad dentro de la ventana. Su cálculo vuelve a utilizar Pettitt sin distinguir tendencia gradual: un tercer producto aporta evidencia, pero no resuelve esa identificación. E2 evalúa un cambio promedio con límites de 2/4 pp sin intervalos de incertidumbre y puede ocultar heterogeneidad espacial.

## 10. Qué cerrar primero

1. Cambiar el título «The trend that wasn't» por **«The trend we cannot yet confirm»**, y sustituir atribución instrumental por posible inhomogeneidad.
2. Etiquetar el conmutador como **«Sensibilidad: ajuste hacia CHIRPS»**, con acuerdo inducido y significancia condicional visibles. Mantener el resultado publicado como principal.
3. Llevar el contraejemplo sin salto a la metodología y exigir que el procedimiento distinga ese caso. Evaluar tendencia/escalón y propagar incertidumbre del ajuste antes de usar el 82 % como prueba de mecanismo.
4. Conservar la evidencia positiva: diferencia local IMERG–estaciones, dependencia del umbral y mayor coocurrencia entre productos cerca de ciclones. Presentar cada una con su unidad y limitación.
5. Actualizar p espaciales, pie FDR y README; integrar el resultado ERA5 solo cuando termine y pase la revisión anterior.

### Guion de reemplazo propuesto, inglés

> A significant trend can still be fragile. In the Dominican Republic, rainfall products disagree about wet days and rain intensity. Four gauges suggest a mismatch with IMERG, but we have not yet established its cause. Adjusting the records changes the conclusions—and can also erase a genuine trend. Stellar Horizons lets students examine the sources, challenge the assumptions, and see which conclusions survive. Before trusting a trend, investigate the evidence.

No se cronometró ni se grabó. No promete haber corregido NASA ni identificado una causa aún no demostrada.

## Reproducción y límites de esta revisión

```powershell
New-Item -ItemType Directory -Force results/tropical/revision | Out-Null
$taskWorkspace = (Get-Location).Path
docker run --rm --mount "type=bind,source=$taskWorkspace,target=/app,readonly" --mount "type=bind,source=$taskWorkspace\results\tropical\revision,target=/app/results/tropical/revision" --entrypoint /opt/venv/bin/python phantom:latest -m earthmemory.tropical.auditoria_revision
```

Entradas originales de solo lectura; diagnóstico en carpeta propia. `resumen.json` contiene modelos, cortes por bloque, pruebas sintéticas explícitamente etiquetadas, controles de estaciones, negativos y desplazamientos exhaustivos; `estaciones_mes.csv` permite auditar cobertura. SHA-256 de archivos principales en el resumen.

Pruebas existentes de tendencias y Yuna: **25 pasaron** en Docker. Esas pruebas no validan la atribución instrumental ni cubren todo el motor tropical. Los diagnósticos nuevos son exploratorios; no se recalculó todo P0 ni se ajustó la interfaz.

Skill aplicada: `statistical-analysis`, en particular independencia, supuestos y separación entre efecto, selección e incertidumbre. Fuentes externas primarias consultadas: documentación NASA IMERG, documentación técnica de Pettitt, revisión metodológica de autores, NCEP y Open-Meteo. No fue una búsqueda bibliográfica exhaustiva.
