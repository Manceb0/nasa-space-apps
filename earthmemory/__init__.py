"""Earth Memory: motor nacional (o de cualquier país) de memoria del agua en el terreno.

Pregunta: ¿por qué dos territorios con lluvia parecida responden distinto (humedad superficial,
agua en la zona de raíces, evaporación, temperatura)?

Módulos:
- power:      descarga reproducible de NASA POWER (MERRA-2) con caché y sumas de verificación.
- region:     límites Natural Earth, rejilla MERRA-2 y máscara de tierra del país.
- anomalies:  SPI, z robusto por mes calendario, tendencias por celda.
- coupling:   acople lluvia→respuesta, memoria (ARX), estado antecedente, bootstrap por bloques.
- episodes:   episodios de sequía, contradicciones lluvia/suelo y factores explicativos.
- contrasts:  pares de celdas con lluvia parecida y respuesta distinta (FDR, sensibilidad).
- extremes:   un evento diario extremo dentro de la distribución 2001-2024.
- figures, report, pipeline.

Reutiliza phantom.stats (Theil-Sen, Mann-Kendall AR(1), Benjamini-Hochberg) y phantom.drought (SPI).
"""
