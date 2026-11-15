# Guion de entrega · 90 segundos

Abrir Tendencias y pulsar «Recorrido · 90 s». No depende de cálculos nuevos ni de llamadas a servicios de datos.
Si falla la conexión o el servidor, abrir `RESPALDO_DEMO.html` desde disco.

## 0–25 s · Investigar

«Para prepararnos ante cambios del agua necesitamos saber qué podemos creer. En República Dominicana,
IMERG y CHIRPS no cuentan la misma historia sobre la intensidad de la lluvia. Aquí vemos los 24 años,
el cambio por década y la evidencia estadística. Una fuente no basta para confirmar un cambio físico».

Mostrar la serie y la tabla. Pulsar Siguiente.

## 25–50 s · Comprobar

«Una elección pequeña cambia la conclusión: qué llamamos día lluvioso. Con estos cuatro umbrales,
las celdas en disputa pasan de 202 a cero. Cero no significa acuerdo: con menos días disponibles también
perdemos capacidad de detectar tendencias. Por eso mostramos la definición junto al resultado».

Tocar 0,5, 1 y 5 mm. Son resultados precalculados, sin interpolación. Pulsar Siguiente.

## 50–90 s · Aplicar

«Lo conectamos con una tarea útil: evaluar señales para mejorar el monitoreo del Yuna. En ocho inundaciones
históricas, exigir confirmación reduce episodios sin inundación catalogada de 39 a 16. Pero perdemos un evento:
detectamos seis de ocho en vez de siete. Y ninguna primera señal es anterior al inicio catalogado.
Esta prueba no anticipa desastres: permite evaluar el intercambio entre confirmación y omisiones antes de
construir un servicio operativo. Todos los resultados y límites se pueden descargar».

Activar Pedir confirmación. Si preguntan por el evento perdido, abrir los ocho eventos: septiembre de 2022.
No leer los detalles técnicos durante el recorrido; reservarlos para preguntas.

## Preguntas previsibles

- **¿Para qué sirve en prevención?** Para evaluar filtros de monitoreo y orientar qué señales necesitan
  verificación antes de usarlas en preparación. No hemos validado decisiones de evacuación ni daños evitados.
- **¿Por qué no lo desplegamos como alerta?** Los productos usados son retrospectivos y CHIRPS llega tarde;
  faltan validación de disponibilidad y tiempos reales. No presentamos esta comparación como servicio en vivo.
- **¿Por qué 39 y no «39 falsas inundaciones»?** Son episodios de señal sin correspondencia en el catálogo,
  que puede omitir impactos. La unidad del disparo es un episodio; la detección se cuenta por evento.
- **¿Qué pasó con GOES?** Sigue sin resolver. La resta de contadores diarios no separaba las vías de observación.
- **¿Qué falta para anticipar?** Datos disponibles antes de la decisión, un diseño que produzca tiempo de aviso,
  fechas de impacto fiables y una validación independiente. Es trabajo posterior a esta entrega.

## Alcance de la verificación

Recorrido automatizado en Edge a 1280×800, 390×844 y 360×740: umbrales, comparación, ocho eventos,
descarga de evidencia, ausencia de desbordamiento horizontal, cierre con Escape y retorno del foco.
Traducción inglesa comprobada. Emulación de móvil; no prueba en un dispositivo físico ni con un jurado externo.
Las capturas y `scripts/verificar_recorrido.js` permiten repetir la comprobación.
