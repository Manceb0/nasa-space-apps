# Traspaso: pantallas de Stellar Horizons (para el chat de diseño)

Fecha: 2026-11-14. Hackatón NASA Space Apps 2026 («Be An Earth System Trend Detective!»). Cierre: domingo 15 de noviembre a las 23:59, hora de RD.

## Reparto del trabajo
- **El chat de pantallas** se encarga de todo lo de `web/`: diseño, interacción, gráficas visibles y fotos de los escenarios para recibir feedback.
- **El chat de investigación** se encarga de los datos nacionales, del motor Earth Memory, de los informes y de la propuesta científica. Sus resultados saldrán en `results/nacional/`, `figures/nacional/` y `reports_nacional/`. Las pantallas deben leer de ahí cuando esté listo, sin inventar números.

## Estado de la web (commits locales en `main`; todavía no hay push)
- Stack: Vite 5 + TypeScript, `@observablehq/plot`, Leaflet. Es un sitio estático que lee `web/public/data/*.json`.
- Servidor de vista previa: `.claude/launch.json` → «earth-detective» (puerto 4180, sirve `web/dist`). **Después de cada `npm run build` hay que reiniciarlo**, porque si no sigue sirviendo la compilación vieja.
- Rutas:
  - `#investigar`: consola con mapa teñido, apuesta, sequías y serie mes a mes.
  - `#ribbon`: **Recovery Ribbon**, la vista protagonista de PHANTOM. Tiene el mapa de fondo y tres vistas: Cintas 3D, Brecha 2D y Lugares.
  - `#expedientes`: Auditoría.
  - `#metodo`: Cómo funciona.
- Menú: PillNav de React Bits, portado a TypeScript (`web/src/pillnav.ts` y `pillnav.css`).
- Archivos clave: `web/src/main.ts` (vistas), `ribbon.ts` (canvas 3D y vista 2D), `charts.ts`, `i18n.ts` (ES/EN), `style.css`.

## Lo que el usuario pidió (en sus palabras)
- «Full inmersivo»: el mapa de fondo y los controles flotando encima. **Nada de paneles en cuadrícula, "cuadrito por cuadrito"**, porque «parece IA».
- Copiar el estilo de sus referencias: consolas espaciales oscuras, terreno teñido, datos anclados sobre el mapa y paneles flotantes. El vidrio está permitido porque lo pidió explícitamente.
- Poder cambiar entre formas de visualizar.
- Integrar React Bits donde sume.
- Cubrir **toda República Dominicana**, no 2 o 5 puntos.
- «La gráfica se ve fea»: hay que rehacer la estética de las gráficas.
- Guía científica: los elementos 3D deben representar variables reales y tener siempre una alternativa 2D con los mismos valores. No inventar mapas continuos sin datos raster. El Impact Field solo se hace cuando haya raster de área.

## Problemas conocidos
- En el Ribbon de escritorio, la etiqueta de la primera sequía queda cortada en el borde izquierdo. En teléfono, las cintas se recortan.
- En la vista Lugares, la etiqueta del sitio elegido se ve atenuada.
- Investigar, Auditoría y Cómo funciona aún no tienen el lenguaje inmersivo.

## Reglas del proyecto (obligatorias)
- Commits **sin** la línea `Co-Authored-By` de Claude. Autor local: Manceb0.
- No publicar ni desplegar sin aprobación explícita del usuario.
- Docker para todo el cómputo de datos (`compose.yaml`).
- No inventar datos; lo sintético va marcado.
- Responder en español.
