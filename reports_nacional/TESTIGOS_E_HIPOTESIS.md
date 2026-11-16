# Testigos e hipótesis · ¿Se sostienen las conclusiones de Earth Memory?

*Stellar Horizons · NASA Space Apps 2026 · «Be An Earth System Trend Detective!» (República Dominicana). Generado por `earthmemory/testigos/report.py` desde `results/testigos/`; ningún número se escribió a mano. Objetivo: intentar romper nuestras propias conclusiones con datos que no salen del mismo modelo.*

## Tabla de veredictos

| Afirmación | Prueba | ¿Independiente? | Resultado | Veredicto |
|---|---|---|---|---|
| Par Monseñor Nouel vs Santiago/La Vega: Δγ raíz −0.13 (GLDAS) | SMAP L3 (radiómetro) calidad recomendada, respuesta a eventos de lluvia IMERG + γ mensual | sí (L3 es retrieval) | 0 pasos con calidad recomendada en los 9 + 9 píxeles 9 km (VWC mediano 10.8 y 5.4 kg/m²; bandera urbana 1.00 en B) | **no comprobable** |
| Mismo par, mismo modelo, 2015-2024 | GLDAS γ en el periodo de SMAP, raíz y capa 0-10 cm | no | raíz: A 0.147 · B 0.276 · Δ -0.128 [-0.168, -0.049] · p calibrado 1.4e-05 · FPR nominal en sustitutos 0.060; **0-10 cm (la capa que un satélite podría ver): Δγ -0.033 [-0.132, 0.055], p calibrado 0.47** | el contraste vive solo en la raíz del modelo |
| Par 0.05° Cordillera Central vs La Vega: eficiencia 0.075 vs 0.168 (TerraClimate) | SMAP L3 calidad recomendada (mensual con CHIRPS y por evento con IMERG) | sí | 0 pasos recomendados en los dos píxeles (VWC mediano 10.1 y 7.7 kg/m²; bandera 'vegetación densa' 1.00 / 1.00) | **no comprobable** |
| Mismo par 0.05°, indicio fuera de especificación | SMAP L3 con retrievals NO recomendados, por evento | no cuenta (fuera de especificación) | A 0.0020 vs B 0.0014 m³/m³ por mm; Δ 0.0006 [0.0003, 0.0009], p calibrado 4.6e-04: **dirección opuesta** a la afirmación | indicio en contra, débil |
| Mismo par 0.05°, mismo modelo, 2015-2024 | TerraClimate en el periodo de SMAP | no | Δ -0.085 [-0.184, 0.005], p calibrado 0.08 | se debilita (el IC ya toca 0) |
| «SMAP confirma la misma dirección (p 0.001)» | revisión de procedencia | **no**: era SMAP L4 (modelo Catchment con asimilación de Tb), y desde la v6 su lluvia de forzamiento se corrige con IMERG Final | — | **se cae como confirmación independiente** (queda como acuerdo entre modelos) |
| «El suelo antecedente es el único factor significativo (β 0.46)» | modelos anidados con API de IMERG (k 0.85-0.95; 30/60/90 d), API del forzante de GLDAS, SPI-3, EF de mes, provincia, terreno o celda; 44 especificaciones; bootstrap por año; FDR | parcial (lluvia observada vs suelo modelado) | β del suelo con lluvia en el modelo 0.17 a 0.40; R² parcial del suelo dada la lluvia 0.016-0.180; suelo q<0.05 en 43/44, lluvia q<0.05 en 0/44 | **sostiene frente a la lluvia observada (IMERG: β 0.37-0.40, 30/30 con q<0.05); se debilita frente a la lluvia del propio modelo (SPI-6 del forzante: β 0.21-0.22; SPI-3+6+12 del forzante: β 0.17-0.19, q 0.020-0.068)** |
| Umbral nacional θ = 0.59 [0.49-0.73] (cubo TerraClimate) | misma regresión segmentada con SMAP L3 y con API en lugar del cubo | parcial | cubo 2015-2024: θ 0.46, quiebre no; estado = API IMERG: θ 0.31, quiebre sí (b5 > 0: otra forma); SMAP L3 recomendado: θ 0.44, quiebre no; SMAP L3 + API: θ 0.03, quiebre no; cubo en zonas SMAP, 24 años: θ 0.62, quiebre sí; cubo en zonas SMAP, 10 años: θ 0.41, quiebre no | **se debilita: solo aparece dentro del cubo con 24 años; con API cambia de forma; SMAP L3 (10 años, zonas secas) no tiene potencia para comprobarlo** |
| «La intensidad de la lluvia no importa» (probado solo con IMERG) | mismos factores con CHIRPS v2 diario y por péntadas (2001-2019) | parcial (CHIRPS comparte estaciones GTS) | CHIRPS diario: β -0.03 a 3.4e-03, q mín 0.97; CHIRPS péntada: β -0.02 a 0.07, q mín 0.97; IMERG diario (mismos episodios): β -0.07 a 0.07, q mín 0.97; n = 494 episodios; concordancia de factores CHIRPS-IMERG ρ = 0.17 | **sostiene (tampoco aparece con CHIRPS); con reserva: CHIRPS e IMERG apenas coinciden en qué episodios tuvieron lluvia intensa (ρ 0.17), así que 'no significativo' es 'no detectable con estos productos', no 'no importa'** |
| Bosque en los territorios comparados | Hansen GFC v1.13, pérdida 2001-2023 sobre bosque 2000 (≥ 30 %) | sí (Landsat) | GLDAS A: Monseñor Nouel (Bonao): 12.0 %; GLDAS B: Santiago / La Vega: 15.4 %; 0.05° A: Cordillera Central (bosque, ~2400 m): 43.3 %, 97 % en 2005; 0.05° B: La Vega (valle del Cibao): 2.8 %; Yuna alto / Bonao: 7.9 % | descriptivo, sin causa (los modelos usan cobertura fija) |
| Vegetación (NDVI) como testigo de los pares | AppEEARS 8ad4ac19… | — | API devolvió HTTP 403 con el token de Earthdata (pide su propio login; no se usaron contraseñas) | **no comprobable** |

Veredicto en una línea: **ninguna de las dos parejas 'misma lluvia, distinta respuesta' puede confirmarse con una observación independiente de la humedad del suelo**: SMAP L3 no entrega retrievals de calidad recomendada en esas celdas (vegetación densa y, en Santiago, zona urbana). Lo que antes se presentó como confirmación (SMAP L4) es otro modelo que comparte lluvia con IMERG.

## 1 · Qué puede ver SMAP L3 en la RD

- Producto: SMAP L3 Enhanced Radiometer 9 km (SPL3SMP_E **V006**, NSIDC; colección CMR C2938664763-NSIDC_CPRD), 2015-03-31 a 2024-12-31, 3481 días, pasos AM (6:00 local) y PM (18:00). Recorte por OPeNDAP en la nube de la caja 17.3-20.1 N, 72.1-68.2 O: 3481 archivos, 0 errores, cada uno con URL, fecha y SHA-256 en `data/testigos/MANIFEST.json`.
- De 596 píxeles de 9 km con centro en tierra dominicana, **440 no tienen NINGÚN retrieval de calidad recomendada en casi 10 años** (mediana nacional de la fracción recomendada: 0.00); VWC mediano de los píxeles de tierra 5.6 kg/m² (el umbral de calidad del algoritmo es 5 kg/m²).
- En los cuatro territorios de las afirmaciones hay retrievals 'con éxito' en ~35 % de los días, pero **ninguno con calidad recomendada**:

| Sitio | Píxeles 9 km | Días con retrieval (AM) | Recomendados (AM / PM) | VWC mediano (kg/m²) | Fracción VWC > 5 | Bandera vegetación densa | Bandera urbana |
|---|---|---|---|---|---|---|---|
| GA · Monseñor Nouel (Bonao) | 9 | 0.36 | 0.00 / 0.00 | 10.8 | 1.00 | 1.00 | 0.33 |
| GB · Santiago / La Vega | 9 | 0.36 | 0.00 / 0.00 | 5.4 | 0.56 | 0.56 | 1.00 |
| HA · Cordillera Central (bosque, ~2400 m) | 1 | 0.36 | 0.00 / 0.00 | 10.1 | 1.00 | 1.00 | 0.00 |
| HB · La Vega (valle del Cibao) | 1 | 0.34 | 0.00 / 0.00 | 7.7 | 1.00 | 1.00 | 0.00 |

**Lectura (revisión adversarial):** la banda L 've' el suelo a través de la vegetación solo si hay poca agua en el dosel. En el bosque de la Cordillera Central y en el valle agrícola-boscoso de Bonao y La Vega el radiómetro mide sobre todo vegetación; en Santiago, ciudad. El algoritmo devuelve un número, pero lo marca como no recomendado. Forzar la prueba con esos números sería disfrazar de observación una cifra fuera de especificación. Además, la rejilla es de 9 km pero la huella real de la banda L es de ~40 km (el producto 'Enhanced' interpola con Backus-Gilbert): píxeles vecinos no son independientes. Figura `t1_smap_l3_calidad`.

## 2 · Los dos pares frente al testigo

Métrica: eficiencia = pendiente del cambio de humedad sobre la lluvia, con efectos fijos de mes (mensual: anomalía de lluvia; por evento: lluvia IMERG entre dos pasos del satélite ≤ 72 h, con la humedad inicial como covariable), y γ del ARX mensual como en el motor nacional. Bootstrap por bloques de 3 meses compartidos; p calibrado con 200 sustitutos de IGUAL respuesta en A y B (factor de inflación σ, como `earthmemory.calibration`).

**Par GLDAS · A = Monseñor Nouel (18.875 N, 70.375 O), B = Santiago/La Vega (19.375 N, 70.625 O)**

| Prueba | ¿Independiente? | Métrica | Resultado |
|---|---|---|---|
| GLDAS raíz 0-100 cm · 2001-2024 (afirmación original) | no (modelo) | gamma ARX | A 0.122 · B 0.255 · Δ -0.133 [-0.162, -0.093] · p calibrado 5.1e-13 |
| GLDAS raíz 0-100 cm · 2015-2024 (mismo periodo que SMAP) | no (modelo) | gamma ARX (z mensual ~ SPI-1) | A 0.147 · B 0.276 · Δ -0.128 [-0.168, -0.049] · p calibrado 1.4e-05 · FPR nominal en sustitutos 0.060 |
| GLDAS superficie 0-10 cm · 2015-2024 (mismo periodo que SMAP) | no (modelo) | gamma ARX (z mensual ~ SPI-1) | A 0.501 · B 0.534 · Δ -0.033 [-0.132, 0.055] · p calibrado 0.474 · FPR nominal en sustitutos 0.080 |
| SMAP L3 superficie · calidad recomendada · gamma mensual | sí (radiómetro) | gamma ARX (z mensual ~ SPI-1) | no comprobable (menos de 40 meses con dato de calidad; n A = 0, n B = 0) |
| SMAP L3 · todos los retrievals (sensibilidad) · gamma mensual | sí, pero con retrievals no recomendados | gamma ARX (z mensual ~ SPI-1) | A 0.708 · B 0.715 · Δ -0.007 [-0.140, 0.148] · p calibrado 0.927 · FPR nominal en sustitutos 0.085 |
| GLDAS superficie 0-10 cm · 2015-2024 | no (modelo) | eficiencia mensual (mm por mm de anomalía IMERG) | A 0.026 · B 0.026 · Δ 5.2e-04 [-0.009, 0.007] · p calibrado 0.904 · FPR nominal en sustitutos 0.040 · n 116/116 |
| SMAP L3 superficie · calidad recomendada | sí (radiómetro) | eficiencia mensual (m³/m³ por mm de anomalía IMERG) | no comprobable (menos de 40 meses con dato de calidad; n A = 0, n B = 0) |
| SMAP L3 · calidad recomendada | sí (radiómetro) | eficiencia por evento (m³/m³ por mm IMERG entre pasos) | no comprobable (menos de 60 eventos con dato de calidad; n A = 0, n B = 0) |
| SMAP L3 · todos los retrievals (sensibilidad) | sí, pero con retrievals no recomendados | eficiencia por evento (m³/m³ por mm IMERG entre pasos) | A 0.002 · B 0.001 · Δ 8.2e-05 [-2.0e-04, 4.2e-04] · p calibrado 0.653 · FPR nominal en sustitutos 0.080 · n 2453/2481 |

Veredicto: **no comprobable**.

**Par 0.05° · A = Cordillera Central (19.025 N, 70.975 O), B = La Vega (19.175 N, 70.475 O)**

| Prueba | ¿Independiente? | Métrica | Resultado |
|---|---|---|---|
| TerraClimate · 2001-2024 (afirmación original) | no (modelo de cubo, ERA5) | eficiencia mensual (mm por mm de anomalía CHIRPS) | A 0.075 · B 0.168 · Δ -0.093 [-0.127, -0.057] · p 0.001 |
| SMAP L4 zona de raíces · 2015-2024 (afirmación original) | no (modelo Catchment; forzante de lluvia corregido con IMERG Final desde la v6) | eficiencia mensual | A 0.179 · B 0.250 · Δ -0.070 · p 0.001 |
| TerraClimate · 2015-2024 (mismo periodo que SMAP) | no (modelo de cubo, ERA5) | eficiencia mensual (mm por mm de anomalía CHIRPS) | A 0.075 · B 0.160 · Δ -0.085 [-0.184, 0.005] · p calibrado 0.082 · FPR nominal en sustitutos 0.020 · n 116/116 |
| SMAP L3 superficie · calidad recomendada | sí (radiómetro) | eficiencia mensual | no comprobable (sin datos de calidad; n A = 0, n B = 0) |
| SMAP L3 · todos los retrievals (sensibilidad) | sí, pero con retrievals no recomendados | eficiencia mensual (m³/m³ por mm de anomalía CHIRPS) | A 2.5e-04 · B 2.0e-04 · Δ 4.9e-05 [-8.4e-05, 1.8e-04] · p calibrado 0.480 · FPR nominal en sustitutos 0.050 · n 116/116 |
| SMAP L3 · calidad recomendada | sí (radiómetro) | eficiencia por evento | no comprobable (sin datos de calidad; n A = 0, n B = 0) |
| SMAP L3 · todos los retrievals (sensibilidad) | sí, pero con retrievals no recomendados | eficiencia por evento (m³/m³ por mm IMERG entre pasos) | A 0.002 · B 0.001 · Δ 5.9e-04 [3.2e-04, 9.2e-04] · p calibrado 4.6e-04 · FPR nominal en sustitutos 0.055 · n 2448/2296 |

Veredicto: **no comprobable**.

Las filas 'todos los retrievals' usan valores que el propio algoritmo marca como NO recomendados; se muestran como sensibilidad y **no cuentan para el veredicto**. Si apuntan en la misma dirección, es un indicio débil, no una confirmación. Figuras `t2_pares_testigo_smap_l3` y `t3_eventos_lluvia_smap_l3`.

## 3 · ¿Memoria del suelo o memoria de la lluvia?

Episodios de sequía del motor nacional (n = 813). Reproducción de la afirmación original (solo severidad como control): β del suelo antecedente sobre el z de la raíz al volver la lluvia = 0.46 [0.25, 0.60] (n = 714).

Correlación entre el z antecedente de la raíz (GLDAS) y cada índice de lluvia antecedente:

| Índice de lluvia antecedente | r con z raíz antecedente |
|---|---|
| API IMERG diario k=0.85 W=30 d | 0.06 |
| API IMERG diario k=0.85 W=60 d | 0.06 |
| API IMERG diario k=0.85 W=90 d | 0.06 |
| API IMERG diario k=0.90 W=30 d | 0.07 |
| API IMERG diario k=0.90 W=60 d | 0.08 |
| API IMERG diario k=0.90 W=90 d | 0.08 |
| API IMERG diario k=0.95 W=30 d | 0.08 |
| API IMERG diario k=0.95 W=60 d | 0.07 |
| API IMERG diario k=0.95 W=90 d | 0.09 |
| API IMERG mensual k=0.90 W=90 d | 0.03 |
| API lluvia del forzante GLDAS (GPCP) k=0.85 W=90 d | 0.35 |
| API lluvia del forzante GLDAS (GPCP) k=0.90 W=90 d | 0.36 |
| API lluvia del forzante GLDAS (GPCP) k=0.95 W=90 d | 0.42 |
| SPI-3 IMERG (mes previo) | 0.16 |
| SPI-6 IMERG (mes previo) | 0.36 |
| SPI-6 lluvia del forzante GLDAS (mes previo) | 0.79 |
| SPI-12 IMERG (mes previo) | 0.40 |
| SPI-12 lluvia del forzante GLDAS (mes previo) | 0.70 |
| SPI-3 lluvia del forzante GLDAS (mes previo) | 0.59 |

Resultado principal (z de la raíz al volver la lluvia). M2 = suelo sin lluvia; M3 = suelo + lluvia antecedente.

| Lluvia antecedente | Efectos fijos | n | β suelo M2 | β suelo M3 [IC95] | q suelo | β lluvia M3 | q lluvia | R² parcial suelo dada lluvia | R² parcial lluvia dado suelo | varianza común | veredicto |
|---|---|---|---|---|---|---|---|---|---|---|---|
| API IMERG diario k=0.85 W=30 d | mes + provincia + terreno | 714 | 0.38 | 0.38 [0.18, 0.49] | 9.6e-06 | -0.03 | 0.809 | 0.171 | 8.2e-04 | 0.003 | sostiene |
| API IMERG diario k=0.85 W=30 d | mes + celda | 714 | 0.38 | 0.38 [0.17, 0.49] | 9.6e-06 | -0.02 | 0.809 | 0.173 | 7.4e-04 | 0.003 | sostiene |
| API IMERG diario k=0.85 W=60 d | mes + provincia + terreno | 714 | 0.38 | 0.38 [0.18, 0.49] | 9.6e-06 | -0.03 | 0.809 | 0.171 | 8.2e-04 | 0.003 | sostiene |
| API IMERG diario k=0.85 W=60 d | mes + celda | 714 | 0.38 | 0.38 [0.17, 0.49] | 9.6e-06 | -0.02 | 0.809 | 0.173 | 7.4e-04 | 0.003 | sostiene |
| API IMERG diario k=0.85 W=90 d | mes + provincia + terreno | 714 | 0.38 | 0.38 [0.18, 0.49] | 9.6e-06 | -0.03 | 0.809 | 0.171 | 8.2e-04 | 0.003 | sostiene |
| API IMERG diario k=0.85 W=90 d | mes + celda | 714 | 0.38 | 0.38 [0.17, 0.49] | 9.6e-06 | -0.02 | 0.809 | 0.173 | 7.4e-04 | 0.003 | sostiene |
| API IMERG diario k=0.90 W=30 d | mes + provincia + terreno | 714 | 0.38 | 0.38 [0.18, 0.49] | 9.6e-06 | -0.02 | 0.809 | 0.172 | 7.4e-04 | 0.002 | sostiene |
| API IMERG diario k=0.90 W=30 d | mes + celda | 714 | 0.38 | 0.38 [0.18, 0.50] | 9.6e-06 | -0.02 | 0.809 | 0.174 | 7.4e-04 | 0.002 | sostiene |
| API IMERG diario k=0.90 W=60 d | mes + provincia + terreno | 714 | 0.38 | 0.38 [0.18, 0.49] | 9.6e-06 | -0.02 | 0.809 | 0.172 | 7.3e-04 | 0.002 | sostiene |
| API IMERG diario k=0.90 W=60 d | mes + celda | 714 | 0.38 | 0.38 [0.18, 0.50] | 9.6e-06 | -0.02 | 0.809 | 0.174 | 7.3e-04 | 0.002 | sostiene |
| API IMERG diario k=0.90 W=90 d | mes + provincia + terreno | 714 | 0.38 | 0.38 [0.18, 0.49] | 9.6e-06 | -0.02 | 0.809 | 0.172 | 7.2e-04 | 0.002 | sostiene |
| API IMERG diario k=0.90 W=90 d | mes + celda | 714 | 0.38 | 0.38 [0.18, 0.50] | 9.6e-06 | -0.02 | 0.809 | 0.174 | 7.2e-04 | 0.002 | sostiene |
| API IMERG diario k=0.95 W=30 d | mes + provincia + terreno | 714 | 0.38 | 0.38 [0.19, 0.49] | 9.6e-06 | -0.04 | 0.809 | 0.173 | 0.002 | 0.002 | sostiene |
| API IMERG diario k=0.95 W=30 d | mes + celda | 714 | 0.38 | 0.38 [0.18, 0.50] | 9.6e-06 | -0.04 | 0.809 | 0.174 | 0.002 | 0.002 | sostiene |
| API IMERG diario k=0.95 W=60 d | mes + provincia + terreno | 714 | 0.38 | 0.38 [0.18, 0.49] | 9.6e-06 | -0.03 | 0.809 | 0.174 | 0.001 | 8.8e-04 | sostiene |
| API IMERG diario k=0.95 W=60 d | mes + celda | 714 | 0.38 | 0.38 [0.18, 0.50] | 9.6e-06 | -0.03 | 0.809 | 0.175 | 0.001 | 8.2e-04 | sostiene |
| API IMERG diario k=0.95 W=90 d | mes + provincia + terreno | 714 | 0.38 | 0.38 [0.18, 0.50] | 9.6e-06 | -0.03 | 0.809 | 0.175 | 0.001 | 9.5e-05 | sostiene |
| API IMERG diario k=0.95 W=90 d | mes + celda | 714 | 0.38 | 0.38 [0.19, 0.50] | 9.6e-06 | -0.03 | 0.809 | 0.176 | 0.001 | 6.9e-05 | sostiene |
| API IMERG mensual k=0.90 W=90 d | mes + provincia + terreno | 714 | 0.38 | 0.38 [0.19, 0.50] | 9.6e-06 | -0.05 | 0.809 | 0.176 | 0.004 | -3.3e-04 | sostiene |
| API IMERG mensual k=0.90 W=90 d | mes + celda | 714 | 0.38 | 0.38 [0.19, 0.51] | 9.6e-06 | -0.05 | 0.809 | 0.177 | 0.004 | -2.2e-04 | sostiene |
| API lluvia del forzante GLDAS (GPCP) k=0.85 W=90 d | mes + provincia + terreno | 714 | 0.38 | 0.38 [0.16, 0.49] | 1.7e-05 | 0.03 | 0.809 | 0.159 | 9.9e-04 | 0.014 | sostiene |
| API lluvia del forzante GLDAS (GPCP) k=0.85 W=90 d | mes + celda | 714 | 0.38 | 0.38 [0.16, 0.49] | 2.3e-05 | 0.03 | 0.809 | 0.161 | 8.9e-04 | 0.012 | sostiene |
| API lluvia del forzante GLDAS (GPCP) k=0.90 W=90 d | mes + provincia + terreno | 714 | 0.38 | 0.37 [0.16, 0.49] | 1.8e-05 | 0.03 | 0.809 | 0.156 | 0.001 | 0.016 | sostiene |
| API lluvia del forzante GLDAS (GPCP) k=0.90 W=90 d | mes + celda | 714 | 0.38 | 0.37 [0.16, 0.49] | 2.5e-05 | 0.03 | 0.809 | 0.158 | 0.001 | 0.015 | sostiene |
| API lluvia del forzante GLDAS (GPCP) k=0.95 W=90 d | mes + provincia + terreno | 714 | 0.38 | 0.36 [0.15, 0.47] | 3.2e-05 | 0.06 | 0.809 | 0.138 | 0.004 | 0.031 | sostiene |
| API lluvia del forzante GLDAS (GPCP) k=0.95 W=90 d | mes + celda | 714 | 0.38 | 0.36 [0.15, 0.48] | 4.8e-05 | 0.06 | 0.809 | 0.140 | 0.004 | 0.029 | sostiene |
| SPI-3 IMERG (mes previo) | mes + provincia + terreno | 714 | 0.38 | 0.38 [0.18, 0.52] | 3.5e-05 | 1.3e-03 | 0.994 | 0.168 | 3.0e-06 | 0.006 | sostiene |
| SPI-3 IMERG (mes previo) | mes + celda | 714 | 0.38 | 0.38 [0.18, 0.52] | 4.8e-05 | 0.01 | 0.935 | 0.168 | 2.4e-04 | 0.007 | sostiene |
| SPI-6 IMERG (mes previo) | mes + provincia + terreno | 710 | 0.38 | 0.38 [0.20, 0.49] | 9.6e-06 | -0.01 | 0.919 | 0.159 | 3.3e-04 | 0.009 | sostiene |
| SPI-6 IMERG (mes previo) | mes + celda | 710 | 0.38 | 0.38 [0.19, 0.49] | 9.6e-06 | -6.8e-03 | 0.960 | 0.159 | 7.6e-05 | 0.010 | sostiene |
| SPI-6 lluvia del forzante GLDAS (mes previo) | mes + provincia + terreno | 710 | 0.38 | 0.22 [0.09, 0.36] | 0.003 | 0.21 | 0.809 | 0.032 | 0.028 | 0.102 | se debilita |
| SPI-6 lluvia del forzante GLDAS (mes previo) | mes + celda | 710 | 0.38 | 0.21 [0.06, 0.35] | 0.013 | 0.23 | 0.809 | 0.028 | 0.034 | 0.102 | se debilita |
| SPI-12 IMERG (mes previo) | mes + provincia + terreno | 653 | 0.37 | 0.40 [0.21, 0.53] | 9.6e-06 | -0.12 | 0.809 | 0.180 | 0.020 | -0.012 | sostiene |
| SPI-12 IMERG (mes previo) | mes + celda | 653 | 0.37 | 0.40 [0.21, 0.53] | 9.6e-06 | -0.12 | 0.809 | 0.179 | 0.019 | -0.011 | sostiene |
| SPI-12 lluvia del forzante GLDAS (mes previo) | mes + provincia + terreno | 653 | 0.37 | 0.34 [0.15, 0.46] | 8.6e-05 | 0.05 | 0.828 | 0.091 | 0.002 | 0.057 | sostiene |
| SPI-12 lluvia del forzante GLDAS (mes previo) | mes + celda | 653 | 0.37 | 0.33 [0.14, 0.46] | 2.6e-04 | 0.06 | 0.809 | 0.088 | 0.002 | 0.057 | sostiene |
| SPI-3 lluvia del forzante GLDAS (mes previo) | mes + provincia + terreno | 714 | 0.38 | 0.33 [0.14, 0.45] | 1.7e-04 | 0.09 | 0.809 | 0.090 | 0.008 | 0.066 | sostiene |
| SPI-3 lluvia del forzante GLDAS (mes previo) | mes + celda | 714 | 0.38 | 0.32 [0.13, 0.46] | 5.4e-04 | 0.10 | 0.809 | 0.089 | 0.010 | 0.066 | sostiene |
| API inicio + API al retorno (k=0.90 W=90 d) | mes + provincia + terreno | 714 | 0.38 | 0.37 [0.18, 0.48] | 9.6e-06 | -0.03 | 0.809 | 0.167 | 0.006 | 0.007 | sostiene |
| API inicio + API al retorno (k=0.90 W=90 d) | mes + celda | 714 | 0.38 | 0.37 [0.17, 0.49] | 9.6e-06 | -0.03 | 0.809 | 0.169 | 0.006 | 0.007 | sostiene |
| SPI-3 + SPI-6 + SPI-12 IMERG | mes + provincia + terreno | 653 | 0.37 | 0.38 [0.20, 0.51] | 1.2e-05 | -1.7e-03 | 0.994 | 0.161 | 0.035 | 0.007 | sostiene |
| SPI-3 + SPI-6 + SPI-12 IMERG | mes + celda | 653 | 0.37 | 0.38 [0.19, 0.51] | 2.5e-05 | 9.1e-03 | 0.952 | 0.159 | 0.036 | 0.008 | sostiene |
| SPI-3 + SPI-6 + SPI-12 forzante GLDAS | mes + provincia + terreno | 653 | 0.37 | 0.19 [0.04, 0.36] | 0.020 | 0.07 | 0.809 | 0.020 | 0.033 | 0.105 | se debilita |
| SPI-3 + SPI-6 + SPI-12 forzante GLDAS | mes + celda | 653 | 0.37 | 0.17 [6.5e-04, 0.36] | 0.068 | 0.08 | 0.809 | 0.016 | 0.040 | 0.104 | se cae |

**Lectura.** Original: β 0.46. Contra la lluvia OBSERVADA (IMERG: API 30-90 d, SPI-3/6/12; 30 especificaciones) el suelo antecedente sobrevive: β 0.37-0.40, q < 0.05 en 30/30, R² parcial del suelo dada la lluvia 0.159-0.180, y la lluvia, conocido el suelo, aporta 3.0e-06-0.036. La correlación entre el z antecedente de GLDAS y cualquier índice de IMERG no pasa de 0.40. Contra la lluvia que FORZÓ al modelo (GPCP desagregado; API 90 d y SPI-3/6/12; 14 especificaciones) la correlación sube hasta 0.79 y el suelo queda en β 0.17-0.38, q < 0.05 en 13/14, R² parcial 0.016-0.161; veredictos sostiene: 10, se debilita: 3, se cae: 1. Interpretación honesta: la 'memoria' del suelo de GLDAS no es la memoria de la lluvia que IMERG observa (r bajo); es en buena parte la memoria de SU PROPIA lluvia de forzamiento, integrada durante meses. Lo que queda tras controlar esa lluvia es dinámica del modelo (drenaje, evaporación, capacidad), no una memoria del suelo medida. Ningún dato observado de humedad de raíz existe aquí para comprobarla.

Tabla completa (también z de 0-10 cm y la contradicción A como resultados): `results/testigos/memoria_lluvia_vs_suelo.csv`. Figura `t4_memoria_lluvia_vs_suelo`.

## 4 · El umbral θ fuera del cubo

| Variante | Celdas | θ [IC95] | b5 [IC95] | ¿quiebre (IC de b5 excluye 0)? |
|---|---|---|---|---|
| TerraClimate (cubo) · 2001-2024 · reconstrucción | 1649 | 0.59 [0.49, 0.73] | -0.499 [-0.792, -0.298] | sí |
| TerraClimate (cubo) · 2015-2024 | 1649 | 0.46 [0.09, 0.93] | -0.601 [-1.373, 0.855] | no |
| TerraClimate (respuesta) · estado = API IMERG · 2001-2024 | 1649 | 0.31 [0.17, 0.31] | 0.592 [0.066, 0.889] | sí |
| SMAP L3 (calidad recomendada) · estado = SMAP L3 · 2015-2024 | 151 | 0.44 [0.35, 0.66] | -2.3e-04 [-7.9e-04, 4.5e-04] | no |
| SMAP L3 (calidad recomendada) · estado = API IMERG · 2015-2024 | 151 | 0.03 [0.01, 0.12] | 6.9e-04 [-0.014, 0.011] | no |
| SMAP L3 (todos los retrievals, fuera de especificación) · estado = SMAP L3 · 2015-2024 | 562 | 0.51 [0.21, 0.67] | -1.1e-04 [-9.0e-04, 5.6e-04] | no |
| SMAP L3 (todos los retrievals, fuera de especificación) · estado = API IMERG · 2015-2024 | 562 | 0.03 [0.02, 0.14] | -3.9e-04 [-0.008, 0.004] | no |
| TerraClimate (cubo) · solo zonas que SMAP L3 ve · 2001-2024 | 404 | 0.62 [0.39, 0.76] | -0.694 [-1.080, -0.464] | sí |
| TerraClimate (cubo) · solo zonas que SMAP L3 ve · 2015-2024 | 404 | 0.41 [0.03, 0.81] | -0.801 [-1.469, 9.466] | no |

**Lectura.** El código reproduce el umbral del informe (θ 0.59 [0.49, 0.73]), así que las diferencias no son de implementación. Con el MISMO cubo pero solo 2015-2024 el quiebre ya no se detecta (b5 [-1.37, 0.85]): diez años no bastan ni dentro del modelo. Si el estado antecedente es la lluvia (API de IMERG) en vez del cubo, la eficiencia baja desde el principio y por encima de θ = 0.31 aumenta la pendiente (b5 0.59): no es el umbral de saturación en 0.59, y θ queda en el borde de la rejilla de búsqueda. SMAP L3 de calidad recomendada solo existe en 151 píxeles de 9 km (sobre todo zonas secas y abiertas): ahí no hay quiebre (b5 [-0.00079, 0.00045]). Control manzanas con manzanas: el cubo en esas mismas zonas SÍ tiene quiebre con 24 años (θ 0.62, b5 [-1.08, -0.46]) pero NO en 2015-2024 (b5 [-1.47, 9.47]). Por tanto la ausencia de quiebre en SMAP no refuta θ: el periodo de SMAP no tiene potencia para verlo. Conclusión: θ ≈ 0.59 es una propiedad del modelo de cubo de TerraClimate en 24 años; ningún testigo independiente lo reproduce, y el único que puede mirar (SMAP L3, 10 años, zonas secas) no tiene potencia para confirmarlo ni para negarlo.

## 5 · Intensidad de la lluvia de retorno con CHIRPS

Años de CHIRPS v2.0 diario disponibles y verificados (SHA-256) en la caché del motor de tendencias: 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019 (periodo usado 2001-01-01 a 2019-12-31); 494 episodios con la ventana completa. Concordancia de los factores entre productos (Spearman): fracción intensa 0.17, máximo diario 0.14.

| Resultado | Factor | Fuente | n | β [IC95] | p | q |
|---|---|---|---|---|---|---|
| z_retorno_SM_RAIZ | fracción en días/péntadas intensas | CHIRPS diario | 494 | -0.01 [-0.16, 0.20] | 0.913 | 0.967 |
| z_retorno_SM_RAIZ | máximo en 1 día / 5 días | CHIRPS diario | 494 | -6.4e-03 [-0.15, 0.15] | 0.932 | 0.967 |
| z_retorno_SM_RAIZ | fracción en días intensos | IMERG diario (mismos episodios) | 494 | -0.07 [-0.21, 0.10] | 0.394 | 0.967 |
| z_retorno_SM_RAIZ | máximo en 1 día | IMERG diario (mismos episodios) | 494 | 6.5e-03 [-0.14, 0.16] | 0.935 | 0.967 |
| z_retorno_SM_0_10 | fracción en días/péntadas intensas | CHIRPS diario | 494 | -0.02 [-0.12, 0.10] | 0.763 | 0.967 |
| z_retorno_SM_0_10 | máximo en 1 día / 5 días | CHIRPS diario | 494 | -0.03 [-0.14, 0.08] | 0.649 | 0.967 |
| z_retorno_SM_0_10 | fracción en días intensos | IMERG diario (mismos episodios) | 494 | 8.7e-03 [-0.13, 0.16] | 0.907 | 0.967 |
| z_retorno_SM_0_10 | máximo en 1 día | IMERG diario (mismos episodios) | 494 | 0.07 [-0.10, 0.23] | 0.395 | 0.967 |
| contradiccion_A_SM_RAIZ | fracción en días/péntadas intensas | CHIRPS diario | 494 | 3.4e-03 [-0.07, 0.07] | 0.923 | 0.967 |
| contradiccion_A_SM_RAIZ | máximo en 1 día / 5 días | CHIRPS diario | 494 | -5.0e-03 [-0.05, 0.05] | 0.840 | 0.967 |
| contradiccion_A_SM_RAIZ | fracción en días intensos | IMERG diario (mismos episodios) | 494 | -2.7e-03 [-0.04, 0.02] | 0.859 | 0.967 |
| contradiccion_A_SM_RAIZ | máximo en 1 día | IMERG diario (mismos episodios) | 494 | -0.02 [-0.06, 7.7e-03] | 0.222 | 0.967 |
| z_retorno_SM_RAIZ | fracción en días/péntadas intensas | CHIRPS péntada | 494 | 0.07 [-0.07, 0.23] | 0.366 | 0.967 |
| z_retorno_SM_RAIZ | máximo en 1 día / 5 días | CHIRPS péntada | 494 | 3.0e-03 [-0.11, 0.17] | 0.967 | 0.967 |
| z_retorno_SM_0_10 | fracción en días/péntadas intensas | CHIRPS péntada | 494 | 0.05 [-0.06, 0.16] | 0.379 | 0.967 |
| z_retorno_SM_0_10 | máximo en 1 día / 5 días | CHIRPS péntada | 494 | -0.01 [-0.10, 0.11] | 0.840 | 0.967 |
| contradiccion_A_SM_RAIZ | fracción en días/péntadas intensas | CHIRPS péntada | 494 | -0.02 [-0.08, 0.02] | 0.354 | 0.967 |
| contradiccion_A_SM_RAIZ | máximo en 1 día / 5 días | CHIRPS péntada | 494 | -0.01 [-0.05, 0.02] | 0.491 | 0.967 |

CHIRPS v2 diario reparte el total de la péntada entre sus días con un modelo: el factor diario no es una observación diaria independiente; la versión por péntadas es la escala anclada a estaciones. Que dos productos de lluvia no coincidan en QUÉ episodios fueron intensos (ρ bajo) dice que la intensidad diaria está mal medida a 25 km en la RD: la ausencia de efecto no prueba que la intensidad no importe.

## 6 · Pérdida de bosque (Hansen GFC v1.13), solo descriptiva

| Zona | Área (km²) | Bosque 2000 (km², cobertura ≥ 30 %) | Pérdida 2001-2023 (km²) | % del bosque de 2000 |
|---|---|---|---|---|
| GLDAS A: Monseñor Nouel (Bonao) (celda 0.25°) | 731.2 | 544.5 | 65.20 | 12.0 |
| GLDAS B: Santiago / La Vega (celda 0.25°) | 729.0 | 230.9 | 35.46 | 15.4 |
| 0.05° A: Cordillera Central (bosque, ~2400 m) | 29.2 | 28.0 | 12.14 | 43.3 |
| 9 km A: entorno SMAP de Cordillera Central (bosque, ~2400 m) (±0.045°) | 94.7 | 89.3 | 27.88 | 31.2 |
| 0.05° B: La Vega (valle del Cibao) | 29.2 | 11.2 | 0.32 | 2.8 |
| 9 km B: entorno SMAP de La Vega (valle del Cibao) (±0.045°) | 94.6 | 45.0 | 3.29 | 7.3 |
| Yuna alto / Bonao (caja aprox.) | 1228.3 | 990.3 | 78.67 | 7.9 |

- 0.05° A: Cordillera Central (bosque, ~2400 m): el 97 % de la pérdida 2001-2023 ocurrió en 2005 (pérdida concentrada en un año; Hansen cuenta como pérdida cualquier remoción del dosel, incluido fuego; no atribuimos causa).
- 9 km A: entorno SMAP de Cordillera Central (bosque, ~2400 m) (±0.045°): el 85 % de la pérdida 2001-2023 ocurrió en 2005 (pérdida concentrada en un año; Hansen cuenta como pérdida cualquier remoción del dosel, incluido fuego; no atribuimos causa).

La pérdida describe lo que pasó en el territorio; no prueba que cambie la respuesta del suelo (GLDAS y TerraClimate usan cobertura FIJA, así que sus diferencias de respuesta no pueden venir de esta pérdida). Figura `t6_bosque_hansen`.

## 7 · NDVI (AppEEARS)

Se consultó la API de AppEEARS para la tarea 8ad4ac19-6b4c-4445-8443-2c4a4fc7f928 con el token de Earthdata como Bearer: HTTP 403. AppEEARS exige su propio token (POST /login con usuario y contraseña); por regla no se pidieron ni usaron contraseñas. **Pendiente**: descargar el paquete desde la web de AppEEARS a `data/appeears/nacional/` (el gancho `earthmemory/appeears_hook.py` lo lee solo). Los puntos MOD13Q1 ya existentes (`data/appeears/phantom-rd-puntos-v2`) no caen en las celdas de los pares (el más cercano, 'cordilleracomparacionhumedo' 19.03 N 70.84 O, está a ~14 km de la celda A de alta resolución): no sirven de testigo.

## Límites

- SMAP L3 mide los ~5 cm superiores; no puede confirmar ni negar nada sobre la zona de raíces (0-100 cm).
- 'No comprobable' no es 'falso': la diferencia entre territorios puede existir; no hay hoy una observación satelital de humedad del suelo que la vea bajo ese dosel.
- IMERG y la lluvia que forzó a GLDAS (GPCP) comparten pluviómetros GPCC/GTS: el API de IMERG no es totalmente independiente de la lluvia del modelo, pero sí del suelo del modelo.
- Los episodios de sequía no son independientes (celdas vecinas a la vez): por eso el bootstrap es por año.
- CHIRPS v2 diario reparte el total de 5 días con un modelo; por eso se repite por péntadas.

## Citas

- O'Neill, P.E., Chan, S., Njoku, E.G., Jackson, T., Bindlish, R., Chaubell, J., Colliander, A. (2023). SMAP Enhanced L3 Radiometer Global and Polar Grid Daily 9 km EASE-Grid Soil Moisture, Version 6. Boulder, Colorado USA. NASA National Snow and Ice Data Center Distributed Active Archive Center. https://doi.org/10.5067/M20OXIZHY3RJ
- Huffman, G.J., Stocker, E.F., Bolvin, D.T., Nelkin, E.J., Tan, J. (2023). GPM IMERG Final Precipitation L3 1 day 0.1 degree x 0.1 degree V07. GES DISC. https://doi.org/10.5067/GPM/IMERGDF/DAY/07
- Beaudoing, H., Rodell, M. (2020). GLDAS Noah Land Surface Model L4 monthly 0.25 x 0.25 degree V2.1. GES DISC. https://doi.org/10.5067/SXAVCZFAQLNO
- Funk, C. et al. (2015). The climate hazards infrared precipitation with stations — a new environmental record for monitoring extremes. Scientific Data 2, 150066. https://doi.org/10.1038/sdata.2015.66
- Abatzoglou, J.T., Dobrowski, S.Z., Parks, S.A., Hegewisch, K.C. (2018). TerraClimate. Scientific Data 5, 170191. https://doi.org/10.1038/sdata.2017.191
- Hansen, M.C., Potapov, P.V., Moore, R., Hancher, M., Turubanova, S.A., Tyukavina, A., Thau, D., Stehman, S.V., Goetz, S.J., Loveland, T.R., Kommareddy, A., Egorov, A., Chini, L., Justice, C.O., Townshend, J.R.G. (2013). High-Resolution Global Maps of 21st-Century Forest Cover Change. Science 342, 850-853. https://doi.org/10.1126/science.1244693 · Datos: Global Forest Change 2000-2025 v1.13, https://storage.googleapis.com/earthenginepartners-hansen/GFC-2025-v1.13/download.html (CC BY 4.0)
- European Space Agency (2021). Copernicus DEM GLO-90. https://doi.org/10.5270/ESA-c5d3d65
- Runfola, D. et al. (2020). geoBoundaries. PLoS ONE 15(4): e0231866. https://doi.org/10.1371/journal.pone.0231866
- Didan, K. (2021). MODIS/Terra Vegetation Indices Monthly L3 Global 1km SIN Grid V061. NASA LP DAAC. https://doi.org/10.5067/MODIS/MOD13A3.061
- Reichle, R. et al. SMAP L4 Global 3-hourly 9 km EASE-Grid Surface and Root Zone Soil Moisture Geophysical Data, Version 8. NSIDC DAAC. https://doi.org/10.5067/T5RUATAQREF8 (citado solo para explicar por qué no es independiente).

## Reproducir

```
docker compose run --rm testigos                    # descarga lo que falte (token en .secrets/earthdata_token) y corre todo
docker compose run --rm testigos --sin-descarga     # solo con la caché de data/testigos
docker compose run --rm --entrypoint "uv run --frozen --no-sync pytest -q tests/test_testigos.py" testigos
```

Salidas: `results/testigos/` (JSON/CSV), `figures/testigos/` (PNG 250 ppp + PDF), `notebooks/09_testigos_e_hipotesis.ipynb` y `reports_nacional/notebooks_html/09_testigos_e_hipotesis.html`. Semilla 2026.
