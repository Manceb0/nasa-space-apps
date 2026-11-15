# Estado de las conclusiones (15-nov-2026, noche)

Una sola tabla con cada hallazgo, su grado de certeza y dónde está la prueba. Si otro documento dice algo distinto,
manda esta tabla. Antes de ponerle una etiqueta a cada fila se comprobaron todas sus cifras en el repo.

**Grados de certeza**
- **Confirmado:** sale directamente de nuestros datos y no depende de supuestos fuertes.
- **Se sostiene con límites:** hay evidencia a favor, con límites que se dicen siempre.
- **Indicio:** el resultado apunta en una dirección, pero el método no basta para afirmarlo.
- **Hipótesis:** plausible y sin probar.
- **No respaldado / retirado:** las pruebas no lo sostienen, o se retiró por un error.

## Tendencias (lo que pide el reto)

| # | Conclusión | Grado | Cifras clave | Fuente |
|---|---|---|---|---|
| 1 | Con 24 años, casi ninguna tendencia de lluvia es robusta cuando se exige que IMERG y CHIRPS coincidan | **Confirmado** | 0 celda-índice robustas en los 21 índices anuales; 2 si se suman las estaciones | TENDENCIAS_P0 |
| 2 | La lluvia extrema no es detectable en 24 años. Eso significa «no detectable», no «sin cambio» | **Confirmado** | Mínimo detectable de Rx5day nacional: 39 mm/década (24 % de la media) | TENDENCIAS_P0 |
| 3 | Las disputas de intensidad (SDII) dependen del umbral de día húmedo | **Confirmado** | Celdas en disputa: 202 / 160 / 64 / 0 con 0,5 / 1 / 2 / 5 mm. El 0 a 5 mm es falta de potencia, no acuerdo | CONEXIONES_UMBRALES_Y_SESGOS |
| 4 | En los lugares con testigo, IMERG pierde más días de lluvia que sus testigos | **Se sostiene con límites** | 6 puntos con ERA5: IMERG −6,1 pp, ERA5 −1,9 (mediana −2,5), CHIRPS −0,2. 4 pluviómetros: IMERG cae más en los 4. Solo 6 y 4 lugares; IMERG usa ERA5 como dato auxiliar | PRUEBAS_TROPICALES (ERA5) |
| 5 | Por lo anterior, las tendencias de IMERG de «llueve más intenso» y «rachas secas más largas» no se pueden confirmar | **Se sostiene con límites** | Dejan de ser significativas con un ajuste hacia CHIRPS. Es una sensibilidad, no una corrección | PRUEBAS_TROPICALES (recálculo) |
| 6 | Hay un cambio extendido en la diferencia de días húmedos IMERG − CHIRPS | **Indicio** fuerte | 265 de 442 celdas eligen un modelo con cambio (219 si se exige ΔBIC > 2; 161 si > 6), frente a un 5 % de falsos positivos | PRUEBAS_TROPICALES (forma) |
| 7 | En el país, ese cambio se parece más a un escalón hacia 2018 que a una tendencia recta | **Indicio** | Escalón en 2018-02: ΔBIC 7,1 frente a la tendencia, pero solo 2,3 frente a tendencia + escalón. El método acierta la forma el 27 % de las veces. Por celda, la forma no es identificable (10 %) | PRUEBAS_TROPICALES (forma) |
| 8 | La causa sería el paso de GOES-13 a GOES-16 en las entradas infrarrojas de IMERG | **Sin resolver** | Las fechas son cercanas (GOES-East desde el 18-dic-2017). La prueba diaria no separa las dos vías: la resta de contadores no es válida (en el 2 % de los celda-días las microondas cuentan más lluvia que el combinado) y no hay días sin microondas. Lo único válido es que bajan tanto el combinado (−3,1 pp) como las microondas disponibles (−3,0 pp). La prueba correcta necesita los archivos de media hora | PRUEBAS_TROPICALES (infrarrojo o microondas) |
| 9 | «Un escalón en octubre de 2013 explica el 82 % de las contradicciones» | **Retirado** | La fecha falla frente a ERA5 (2016-10) y frente al modelo (2018-02). El 82 % es la sensibilidad a un ajuste que también borra tendencias sin salto (−74,6 %) | PRUEBAS_TROPICALES, REVISION_JANE |

## Fuentes en desacuerdo (sequía e inundación)

| # | Conclusión | Grado | Cifras clave | Fuente |
|---|---|---|---|---|
| 10 | La decisión de sequía cambia según el producto | **Confirmado** (descriptivo) | Con alarma de al menos uno, los cuatro productos no son unánimes en el 91 % de los casos. En el 39 % otro dice normal o húmedo. Solo coinciden en 275 de 3.111 provincia-meses | AUDITORIA_CONFIANZA |
| 11 | El disparador de inundación (> 100 mm en 48 h) de un producto no lo confirma el otro | **Confirmado** (descriptivo) | 67 % sin confirmar (IC 62-72 %) | AUDITORIA_CONFIANZA |
| 12 | Con ciclón cerca, los productos coinciden más en **dónde** cae la lluvia fuerte, no en **cuánta** | **Se sostiene con límites** | ETS ≥ 50 mm de agosto a noviembre: 0,239 con ciclón frente a 0,097 sin él. «Sin ciclón» no equivale a convección local | PRUEBAS_TROPICALES, REVISION_JANE |
| 13 | En el relieve, CHIRPS da más lluvia que IMERG a barlovento y menos a sotavento | **Se sostiene con límites** (asociación) | ρ 0,56, p exhaustiva 0,012 (82 traslaciones). El alisio se supuso fijo del ENE: es asociación, no atribución al viento | PRUEBAS_TROPICALES |
| 14 | Santo Domingo, 18-nov-2023: un producto de 10 km no reproduce un extremo puntual de 431 mm | **Se sostiene**; repartir la brecha queda inconcluso | Estación 431 mm frente a IMERG 140 mm (mejor celda vecina 185). Evento del NHC AL222023 (Twenty-Two) | AUDITORIA_CONFIANZA, ALTA_RESOLUCION |

## Caso Yuna y «memoria»

| # | Conclusión | Grado | Cifras clave | Fuente |
|---|---|---|---|---|
| 15 | El agua observada por MODIS confirma la mayoría de los eventos del catálogo | **Se sostiene con límites** | 12 de 15 confirmados, pero las confirmaciones de 4-8 km² son débiles (nov-2024: unos 4 km² en el Yuna) | CASO_YUNA |
| 16 | La regla > 100 mm en 48 h detecta casi todo, pero con muchas falsas alarmas | **Confirmado** (en esta muestra) | POD 0,88; CSI 0,15 [0,08-0,21]; 8 eventos de prueba | CASO_YUNA |
| 17 | Nov-2024 no es un fallo del umbral sino de la ventana | **Confirmado** | 115,5 mm el 8-nov, fuera de la ventana puntuada; dentro, 92,3 mm. No hay que tocar el umbral para arreglarlo | CONEXIONES_UMBRALES_Y_SESGOS |
| 18 | La humedad antecedente mejora el disparador | **No respaldado** con estos datos | AUC del antecedente ≈ 0,4-0,5, frente a 0,7-0,8 de la lluvia del episodio | CASO_YUNA |
| 19 | La presa de Hatillo cambia la relación entre la lluvia de arriba y el agua de abajo | **No detectado** (indeterminado) | Los intervalos se solapan | CASO_YUNA |
| 20 | «El suelo recuerda» (memoria del suelo de GLDAS) | **Hipótesis débil**: solo existe dentro del modelo | β 0,46 → 0,37-0,40 frente a la lluvia observada, pero 0,17-0,22 frente a la lluvia que fuerza al modelo. No hay humedad de raíz observada | TESTIGOS_E_HIPOTESIS |
| 21 | PHANTOM (la vegetación se ve verde pero sigue estresada tras la sequía) | **No respaldado** | 19 de 24 comparaciones dentro de ±32 días (la precisión del método) | RESULTS.md (primera versión) |

## Correcciones al `deep-research-report (8).md` (recibido el 15-nov)

Su enfoque general coincide con esta tabla: dar un grado de certeza a cada conclusión, no prometer predicciones y
presentar el desacuerdo entre fuentes como resultado. Pero al cotejarlo con el repo aparecen cifras y afirmaciones
que no deben copiarse:

1. **Santo Domingo 2023 no fue el huracán Lisa.** El NHC lo trata en el informe AL222023 («Twenty-Two», 2023). Lisa
   fue un huracán de 2022 en otra zona. Tampoco atribuimos el aguacero a la convección del alisio contra la montaña:
   el informe deja el reparto de la brecha como **inconcluso**.
2. **«CSI 0,239 vs 0,097 con ciclón»:** son valores **ETS**, y 0,239 es **con** ciclón y 0,097 **sin** ciclón. Los
   productos coinciden más con ciclón cerca.
3. **«La inundación invisible», nov-2024, «~23 km² inundados»:** no sale de nuestros datos. MODIS da unos 4 km² en el
   Yuna (máximo del evento, 21-nov), una confirmación débil. Además, MODIS es óptico, no radar.
4. **«Bajar el umbral y la alerta se activa»:** contradice lo que ya se verificó. El fallo de nov-2024 viene de la
   ventana temporal: los 115,5 mm cayeron el 8-nov, fuera de la ventana puntuada. Ese mismo aguacero cuenta a la vez
   como fallo y como falsa alarma. Bajar el umbral para «acertar» este caso sería ajustar a conveniencia y aumentaría
   las falsas alarmas. Una demo honesta mostraría **la ventana**, no un deslizador de umbral.
5. **«La regresión pierde casi 50 %»:** solo es así frente a la lluvia que fuerza al modelo (0,46 → 0,17-0,22).
   Frente a la lluvia observada cae poco (0,37-0,40).
6. **«NOAA-20 calibración en 2022»:** no está verificado y no se usa.
7. **«Hay indicios de un cambio de régimen en 2013»:** lo que hay ahora es un indicio de cambio con el mejor modelo en
   **2018**, y una hipótesis candidata (GOES-16). Ver las filas 6-9.
