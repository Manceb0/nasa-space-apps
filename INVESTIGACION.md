# PHANTOM — investigación de trabajo

Equipo Stellar Horizons · NASA Space Apps 2026 · 14 y 15 de noviembre

Pregunta: **después de una sequía, ¿la vegetación se ve recuperada antes de estarlo de verdad, y esa
diferencia está creciendo?**

El reto pide responder qué cambia, dónde, cuánto y si el cambio es estadísticamente significativo.
PHANTOM responde las cuatro sobre una sola variable propia: los días entre "se ve verde" y "funciona".

---

## 1. El agujero del informe anterior (arreglarlo antes de empezar)

El informe propone medir lo "funcional" con **MODIS GPP (MOD17A2HGF)**. Un jurado que sepa de
teledetección lo va a tumbar en una pregunta:

MOD17 no mide fotosíntesis. La calcula así:

```
GPP = ε_max × f(Tmin) × f(VPD) × FPAR × 0.45 × radiación solar
```

- **FPAR** sale de la misma reflectancia que el NDVI. Es "verdor" otra vez.
- **f(Tmin)** y **f(VPD)** salen de un reanálisis meteorológico (GMAO), no de la planta.

O sea: si el GPP tarda más que el NDVI en recuperarse, casi seguro es porque el aire siguió seco
(VPD alto en el modelo), no porque la planta siga dañada. El "fantasma" estaría en nuestro método.

### Arreglo propuesto: temperatura de la hoja (MODIS LST)

Una planta que transpira se enfría. Si cierra los estomas por estrés, el dosel se calienta aunque
siga verde. La temperatura de superficie (**MOD11A2**, 8 días, 1 km) es una medición térmica
independiente del NDVI, tomada por el mismo satélite.

- **Se ve:** NDVI / EVI (MOD13Q1).
- **Funciona:** anomalía de LST de día menos anomalía de temperatura del aire (MERRA-2 en Giovanni).
  Si el dosel sigue más caliente que el aire de lo normal, todavía no está transpirando bien.
- **Apoyo, no protagonista:** MOD17 GPP, dicho con honestidad como "modelo".

Frase para el pitch: **"Se ve verde, pero tiene fiebre."**

Riesgo del arreglo: la LST la afectan nubes, viento y suelo desnudo. Por eso se usa la máscara de
calidad (`QC_Day`) y la diferencia contra la temperatura del aire, no la LST cruda.

---

## 2. Qué hacer con cada fuente que nos pidieron usar

| Fuente | Para qué la usamos | Qué bajar |
|---|---|---|
| **AppEEARS** | Fuente principal. Series de tiempo por punto o polígono. | `MOD13Q1.061`: `_250m_16_days_NDVI`, `_250m_16_days_EVI`, `_250m_16_days_pixel_reliability`. `MOD11A2.061`: `LST_Day_1km`, `QC_Day`. `MOD17A2HGF.061`: `Gpp_500m`, `Psn_QC_500m`. 2000-01-01 → 2025-12-31. Salida CSV. |
| **Giovanni** | Encontrar las sequías y la temperatura del aire. | Precipitación GPM IMERG mensual; temperatura del aire a 2 m de MERRA-2; humedad del suelo GLDAS Noah. Promedio de área del polígono, descarga CSV. |
| **Hydrology Time Series** | Humedad del suelo diaria en el punto exacto, para fechar el inicio y fin de cada sequía. | GLDAS (global). NLDAS **no** cubre República Dominicana: solo llega a ~25° N. |
| **Climate Data Online (NOAA)** | Validar con una estación real que las sequías de IMERG ocurrieron. | GHCN-Daily, precipitación de la estación más cercana a Santiago. Revisar en el mapa qué estación tiene serie larga. |
| **KNMI Climate Explorer** | Segunda opinión: correr la misma tendencia en otra herramienta y comprobar que da lo mismo. | Subir nuestra serie del "gap" o usar su precipitación para la región. |
| **Artículo SeaWiFS (NTRS)** | Precedente metodológico: quitar la estacionalidad y luego probar la significación. Citarlo en la metodología. | Leer la sección de métodos. |
| **Guías de tendencia y significación** | Explicar Mann-Kendall y p-valor en lenguaje simple en la entrega. | Citar. |
| **SWOT (CSA/NASA/CNES)** | Contexto local opcional: nivel de embalses del Cibao. La serie empieza en 2023, es muy corta para tendencia. | Solo si sobra tiempo. |
| **RCM y tutorial SAR (CSA)** | El radar ve la estructura a través de las nubes. Bueno para una versión 2, demasiado pesado para 48 h. | Mencionarlo como trabajo futuro. |

Cuenta necesaria: **NASA Earthdata Login** (gratis) para AppEEARS y Giovanni. Créenla ya; AppEEARS
tarda de minutos a horas en procesar una solicitud grande. Pidan primero un solo punto.

---

## 3. Dónde mirar

El evento es en Santiago. Candidatos, de más a menos fuerte:

1. **Línea Noroeste (Montecristi, Dajabón, Valverde):** bosque seco, sequías frecuentes, poca
   agricultura de riego en las zonas protegidas. Mejor señal.
2. **Cordillera Central cerca de Santiago:** bosque, más nublado (menos datos limpios de LST).
3. **Un control fuera del país** con buena cobertura (bosque tropical seco en otra región) por si
   la serie dominicana sale corta.

Regla del informe que mantengo: si RD tiene menos de 4–5 sequías claras en 2000–2025, no
alcanza para una tendencia. Entonces se usa RD como caso para el pitch y el control como evidencia.

Sequías a comprobar en IMERG primero: 2014–2016 (El Niño 2015) y 2019–2020. No las den por hechas
hasta verlas en la serie.

---

## 4. Método (lo mínimo que aguanta preguntas)

1. **Limpiar:** quitar píxeles con mala calidad (`pixel_reliability > 1`, `QC_Day` malo).
2. **Quitar la estación:** para cada fecha, restar el promedio de ese día del año (2000–2025).
   Así queda la anomalía.
3. **Fechar la sequía:** de Giovanni/GLDAS, inicio = humedad del suelo bajo el percentil 20 durante
   ≥ 2 meses; fin = vuelve a su banda normal.
4. **Recuperación visual:** primer día en que la anomalía de NDVI vuelve a ≥ 90 % de su nivel
   previo y se queda ahí 3 observaciones seguidas.
5. **Recuperación funcional:** lo mismo con la anomalía de LST − T aire (que vuelva a su banda normal).
6. **Gap del evento** = día funcional − día visual.
7. **Tendencia del gap:** Theil-Sen (cuánto cambia por década) + Mann-Kendall (si es significativo).
   Con pocos eventos, decirlo claramente y mostrar el intervalo con bootstrap.
8. **"Challenge the finding":** repetir con umbral 90 % y 95 %, con NDVI y EVI. Si el resultado se
   mantiene: ROBUSTO. Si cambia: SENSIBLE A SUPUESTOS. Mostrar las dos cosas.

Lo que **no** decimos: causalidad, ni que el satélite diagnostica la salud del bosque. Decimos:
"la diferencia entre estas dos señales está cambiando".

---

## 5. Cosas del informe que no podemos citar todavía

El informe trae citas que no pude confirmar, en particular el supuesto artículo de *Nature
Geoscience* de noviembre de 2026 sobre VPD y humedad del suelo. Lo más cercano que encontré es un
trabajo de PNNL con aprendizaje automático explicable que concluye lo **contrario** (la humedad del
suelo domina en la mayoría de los ecosistemas).

NASA exige citar todas las fuentes. Regla: **no entra a la entrega ninguna cita que alguien del
equipo no haya abierto**. Si no se puede abrir, se quita.

---

## 6. Las primeras 3 horas

| Hora | Quién | Qué |
|---|---|---|
| 0:00 | Todos | Earthdata Login. Elegir un punto en la Línea Noroeste. |
| 0:15 | Datos | Solicitud a AppEEARS de un punto: MOD13Q1 + MOD11A2 + MOD17A2HGF. |
| 0:15 | Datos 2 | Giovanni: IMERG mensual + T aire MERRA-2 del mismo punto. Marcar las sequías. |
| 1:30 | Estadística | Con los CSV: anomalías y la primera sequía. ¿Hay gap o no? |
| 2:30 | Todos | **Decisión:** si hay señal, sigue PHANTOM. Si no, pasar a ECHO (precipitación del año anterior vs. productividad), que solo necesita IMERG + MOD13Q1. |

La pantalla y el video se empiezan en paralelo con datos falsos marcados como tales, y se cambian
por los reales cuando lleguen.
