import maplibregl from "maplibre-gl";
// P0 · Tendencias. Pantalla de trabajo (taste-skill, app · true-black-flat, semilla 280888739).
// Pregunta de la pantalla: «¿Están cambiando la sequía y la lluvia extrema en mi provincia, y qué tan seguros estamos?»
// Marco fijo en tres columnas que comparten bordes: preguntas y respuesta | mapa con su línea de tiempo | año a año y
// dónde poner atención. En tableta la tercera columna baja a la primera; en el teléfono la primera es una hoja inferior.
// Cara de la pantalla: el campo de tendencia sobre la isla con su punteado de significancia; y la escalera de evidencia.
import "./tendencias.css";
import { terrain3d } from "../terrain3d";
import { esc, LL, loadTrends, num, sgn, type Sel, type Tr, type TrendData } from "./datos";
import { cellAt, classField, colorOf, heatCss, heatField, rampCss, scaleMax, stipple, trendField } from "./campo";
import { LAND_Q, landPeek, loadLand, recuperaAnswer, siteMarks, sitesLayer, verdeAnswer, type Land, type LandQ } from "./tierra";
import { capsule, DRIFT_EN, DRIFT_ES, forest, PROD_COLOR, seriesChart } from "./graficas";
import { cellProvinces, ridges, type RGBA, type Rio } from "./crestas";
import { load } from "../data";
import { bottomSheet, PEEK } from "./hoja";
import { chip, QUESTIONS, questionOf, shortName, verdict } from "./preguntas";
import { openMenu } from "./menu";
import { openPop } from "./pop";
import { hallazgo, hallazgoCorto, type Hallazgos } from "./hallazgo";
import { startTour, stopTour, tourBusy } from "./tour";
import { destroyPreparation, viewPreparation } from "../preparacion/vista";
import { openAuditAt } from "../auditoria/vista";
import { hurricanes, type CyInfo } from "../preparacion/huracanes";
import { timeline } from "./tiempo";

type Style = "calor" | "crestas" | "plano" | "oscuro";
type Layout = "wide" | "mid" | "phone";
const sel: Sel = { ind: "RACHAS15", per: "anual", reg: "DO", src: "IMERG" };
const pick: Record<string, string> = Object.fromEntries(QUESTIONS.map((q) => [q.id, q.vars[0]]));
const ui = { trail: [] as { label: string; color: string; short: string }[], land: "" as LandQ, landVar: "modis_ndvi", landSite: "", d3: false, style: "crestas" as Style, year: null as number | null, show: "" as string, left: true, right: true };
let t3: ReturnType<typeof terrain3d> | null = null;
let cleanup: (() => void)[] = [];
const RD: [[number, number], [number, number]] = [[-72.05, 17.45], [-68.3, 19.98]];
const RM = () => matchMedia("(prefers-reduced-motion: reduce)").matches;
const TIERS = [["sabemos", "Lo que sabemos", "What we know"], ["creemos", "Lo que creemos saber", "What we think we know"], ["comprobar", "Lo que hay que comprobar", "What still needs checking"]] as const;
const CHEV = '<svg class="chev" viewBox="0 0 12 12" aria-hidden="true"><path d="M3 4.5l3 3 3-3" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>';
const MARK = '<svg viewBox="0 0 32 32" aria-hidden="true"><path d="M16 2.5l2.3 8.2 8.2 2.3-8.2 2.3L16 23.5l-2.3-8.2-8.2-2.3 8.2-2.3z" fill="#f2b33d"/><path d="M2.5 28.5c7.5-4.6 19.5-4.6 27 0" stroke="#fff" stroke-width="2.2" fill="none" stroke-linecap="round"/></svg>';
const PANEL_L = '<svg viewBox="0 0 16 16" aria-hidden="true"><rect x="1.75" y="2.75" width="12.5" height="10.5" rx="2" fill="none" stroke="currentColor" stroke-width="1.5"/><path d="M6 3v10" stroke="currentColor" stroke-width="1.5"/></svg>';
const PANEL_R = '<svg viewBox="0 0 16 16" aria-hidden="true"><rect x="1.75" y="2.75" width="12.5" height="10.5" rx="2" fill="none" stroke="currentColor" stroke-width="1.5"/><path d="M10 3v10" stroke="currentColor" stroke-width="1.5"/></svg>';
const SEASON: Record<string, [string, string]> = { anual: ["Año", "Year"], seca: ["Seca", "Dry"], humeda_temprana: ["May–jul", "May–Jul"], humeda_tardia: ["Ago–nov", "Aug–Nov"] };

let cyOff: (() => void) | null = null;
let prepOff: (() => void) | null = null;
let rios: Rio[] | null = null;
let hzData: Hallazgos | null = null;
let cyApi: { setPlace: (p: string) => void } | null = null;
export let autoTour = { on: false };
export function destroyTrends() {
  if (!tourBusy()) stopTour();
  cleanup.forEach((f) => f()); cleanup = [];
  t3?.destroy(); t3 = null;
  document.body.classList.remove("wx-on");
}

/** Abre Tendencias en una pregunta de la vegetación (los enlaces viejos de «Investigar» y «Recovery Ribbon»). */
export function openLand(q: LandQ) { ui.land = q; ui.year = null; }

export async function viewTrends(view: HTMLElement) {
  destroyTrends();
  document.body.classList.add("wx-on");
  view.innerHTML = `<div class="wx"><p class="wx-loading">${esc(LL("Cargando tendencias…", "Loading trends…"))}</p></div>`;
  const [d, land, riosData, hz] = await Promise.all([loadTrends(), loadLand(), load<{ rios: Rio[] }>("tendencias/rios.json").catch(() => null), load<Hallazgos>("tendencias/hallazgos.json").catch(() => null)]);
  rios = riosData?.rios ?? null; hzData = hz;
  if (!d.prods.includes(sel.src)) sel.src = d.prods[0];
  if (!ui.show || (ui.show === "acuerdo" && !d.both)) ui.show = d.both ? "acuerdo" : sel.src;
  if (!d.rel && ui.style === "crestas") ui.style = "oscuro";
  if (!land) ui.land = "";
  render(view, d, land);
}

function render(view: HTMLElement, d: TrendData, land: Land | null) {
  const layout: Layout = innerWidth < 760 ? "phone" : innerWidth < 1180 ? "mid" : "wide";
  const updated = new Date(d.V.generado_utc).toLocaleString(LL("es-DO", "en-US"), { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
  // Secciones plegables: abiertas en ancho (tienen su columna), cerradas en tableta y teléfono (comparten la hoja)
  const sect = (id: string, title: string) => `
    <details class="sec" id="${id}-sec" ${layout === "wide" ? "open" : ""}>
      <summary><h2 id="${id}-h">${title}</h2><span class="meta num" id="${id}-meta"></span>${CHEV}</summary>
      <div class="sec-b" id="${id}-plot"></div>
    </details>`;
  const extra = `
    ${sect("s", "")}
    ${sect("r", esc(LL("Dónde poner atención", "Where to look")))}
    <p class="fine">${esc(LL("NASA GPM IMERG V07 y CHC CHIRPS v2.0, 2001–2024. Theil-Sen con Mann-Kendall de Hamed y Rao; FDR de Benjamini-Hochberg. Describe; no atribuye causas.", "NASA GPM IMERG V07 and CHC CHIRPS v2.0, 2001–2024. Theil-Sen with Hamed & Rao Mann-Kendall; Benjamini-Hochberg FDR. Describes; does not attribute causes."))}</p>`;
  const styles: [Style, string][] = [...(d.rel ? [["crestas", LL("Crestas", "Ridges")] as [Style, string]] : []), ["calor", LL("Calor", "Heat")], ["oscuro", LL("Mapa oscuro", "Dark map")], ["plano", LL("Satélite", "Satellite")]];
  const fold = (side: "left" | "right") => layout === "phone" || (side === "right" && layout !== "wide") ? "" : `<button class="fold" data-fold="${side}" aria-controls="wx-${side}">${side === "left" ? PANEL_L : PANEL_R}</button>`;

  const r15 = d.s13?.recuentos.RACHAS15 ?? {};
  const nuevas = ["humeda_tardia", "humeda_temprana"].map((k) => `${LL(...SEASON[k])}: ${r15[k]?.en_disputa_sin_escalon ?? 0}`).join(" · ");
  const S13 = d.s13, era = S13?.era5, rev = S13?.revision;
  const pp = (v: number) => `${sgn(v, 1)} pp`;
  const warn13 = S13 ? `<ul class="s13-w">
        <li>${esc(LL("El conmutador es una prueba de sensibilidad, no una corrección: el resultado publicado sigue siendo el principal.", "The switch is a sensitivity test, not a correction: the published result remains the main one."))}</li>
        ${era ? `<li>${esc(LL(`Frente a ERA5 (${era.n_puntos} puntos), IMERG pierde de media más días de lluvia. La prueba sitúa un cambio en ${era.punto_de_cambio_IMERG_menos_ERA5}, pero no identifica su forma ni su causa. Cambio medio: IMERG ${pp(era.cambio_medio_pp.IMERG)}, ERA5 ${pp(era.cambio_medio_pp.ERA5)}, CHIRPS ${pp(era.cambio_medio_pp.CHIRPS)}. IMERG usa ERA5 como dato auxiliar: la dependencia es parcial.`, `Against ERA5 (${era.n_puntos} points), IMERG loses more rain days on average. The test locates a change in ${era.punto_de_cambio_IMERG_menos_ERA5}, but does not identify its shape or cause. Mean change: IMERG ${pp(era.cambio_medio_pp.IMERG)}, ERA5 ${pp(era.cambio_medio_pp.ERA5)}, CHIRPS ${pp(era.cambio_medio_pp.CHIRPS)}. IMERG uses ERA5 as ancillary input: dependence is partial.`))}</li>` : ""}
        ${rev ? `<li>${esc(LL(`El ajuste hacia CHIRPS le quita el ${num(rev.reduccion_pendiente_sintetica_pct, 1)} % a una tendencia sintética sin ningún salto: no distingue una deriva de un escalón. Por eso las disputas que desaparecen miden la sensibilidad al ajuste, no un mecanismo.`, `The adjustment towards CHIRPS removes ${num(rev.reduccion_pendiente_sintetica_pct, 1)} % of a synthetic trend with no jump: it cannot tell a drift from a step. The disputes that vanish measure sensitivity to the adjustment, not a mechanism.`))}</li>` : ""}
        <li>${esc(LL("La variante ajustada tiene valores imposibles (rachas o intensidades negativas): no es lluvia.", "The adjusted variant has impossible values (negative spells or intensities): it is not rainfall."))}</li>
        <li>${esc(LL("Parte del acuerdo lo induce el propio ajuste: en esa capa no se muestra «robusta».", "Part of the agreement is induced by the adjustment itself: that layer shows no \"robust\"."))}</li>
        <li>${esc(LL(`Con el ajuste aparecen disputas nuevas en las rachas de 15 días de las temporadas lluviosas (${nuevas} celdas).`, `With the adjustment, new disputes appear in 15-day spells in the rainy seasons (${nuevas} cells).`))}</li>
        <li>${esc(LL("Las salidas publicadas no se tocaron; la variante está aparte.", "The published outputs were not touched; the variant is kept apart."))}</li>
      </ul>` : "";
  view.innerHTML = `
  <div class="wx" id="wx" data-layout="${layout}" data-mode="trend" data-land="${ui.land ? "on" : "off"}" data-sty="${ui.style}" data-d3="${ui.d3 ? "on" : "off"}" data-left="${ui.left ? "on" : "off"}" data-right="${ui.right ? "on" : "off"}">
    <header class="wx-top">
      <a class="wx-brand" href="#tendencias">${MARK}<b>Stellar Horizons</b><span>${esc(LL("Detective de tendencias", "Trend detective"))}</span></a>
      <button class="tour-start" id="tour-go"><svg viewBox="0 0 16 16" aria-hidden="true"><path d="M5 3.5v9l7.5-4.5z" fill="currentColor" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"/></svg><span>${esc(LL("Ver el recorrido", "Watch the tour"))}</span></button>
      ${d.both ? "" : `<p class="wx-stamp" title="${esc(LL(`Corrida del ${updated}`, `Run of ${updated}`))}">${esc(LL("Preliminar: solo IMERG", "Preliminary: IMERG only"))}</p>`}
    </header>
    <div class="wx-main">
      <aside class="wx-left" id="wx-left">
        ${layout === "phone" ? `<button class="wx-grab" id="wx-grab" aria-label="${esc(LL("Subir o bajar el panel", "Raise or lower the panel"))}"><i></i></button>` : ""}
        <section class="blk-reg" id="wx-peek">
          <h1 class="place"><button id="r-btn" aria-haspopup="listbox" aria-expanded="false" title="${esc(LL("Elegir el lugar", "Choose the place"))}"><span id="wx-h1"></span>${CHEV}</button></h1>
          <p class="place-hint" id="finding"></p>
          ${layout === "phone" ? `<p class="peek-ans" id="peek-ans"></p>` : ""}
        </section>
        <div class="wx-scroll">
          <section class="blk-q" aria-labelledby="q-h">
            <h2 id="q-h">${esc(LL("¿Está cambiando la lluvia?", "Is the rain changing?"))}</h2>
            <div class="qs" id="qs" role="radiogroup" aria-labelledby="q-h"></div>
          </section>
          <section class="blk-ans" aria-labelledby="ans-h">
            <h2 id="ans-h" class="sr">${esc(LL("Qué dicen las dos fuentes", "What the two sources say"))}</h2>
            <div id="ans" aria-live="polite"></div>
          </section>
          <section class="blk-land blk-cy" aria-labelledby="pq-h"><h2 id="pq-h">${esc(LL("¿Y hoy?", "And today?"))}</h2><div class="lqs"><button class="ql" data-prepq aria-pressed="false"><i></i>${esc(LL("¿Qué municipio vigilar hoy?", "Which municipality to watch today?"))}</button></div></section>
          <section class="blk-land blk-cy" aria-labelledby="cq-h"><h2 id="cq-h">${esc(LL("¿Y los ciclones?", "And the cyclones?"))}</h2><div class="lqs"><button class="ql" data-cyq aria-pressed="false"><i></i>${esc(LL("¿Con cuánto aviso llegan aquí?", "How much warning before they arrive here?"))}</button></div></section>
          ${land ? `<section class="blk-land" aria-labelledby="lq-h"><h2 id="lq-h">${esc(LL("¿Y la vegetación?", "And the vegetation?"))}</h2><div class="lqs" id="lqs"></div></section>` : ""}
          ${layout === "wide" ? "" : extra}
        </div>
      </aside>
      <section class="wx-mapcol" aria-label="${esc(LL("Mapa de tendencias", "Trend map"))}">
        <div id="map"></div>
        <div class="map-top">
          ${fold("left")}
          <div class="seg map-data" role="radiogroup" aria-label="${esc(LL("Qué muestra el mapa", "What the map shows"))}">
            ${d.both ? `<button data-show="acuerdo" role="radio" title="${esc(LL("Dónde coinciden y dónde se contradicen IMERG y CHIRPS", "Where IMERG and CHIRPS agree and where they contradict each other"))}">${esc(LL("Veredicto", "Verdict"))}</button>` : ""}
            ${d.prods.map((p) => `<button data-show="${p}" role="radio">${p}</button>`).join("")}
          </div>
          <span class="sp"></span>
          <button class="pick map-sty" id="sty-btn" aria-haspopup="listbox" aria-expanded="false"><span>${esc(LL("Vista", "View"))}</span><b id="sty-l"></b>${CHEV}</button>
          <div class="seg map-cam" role="radiogroup" aria-label="${esc(LL("Cámara", "Camera"))}"><button data-cam="2d" role="radio">2D</button><button data-cam="3d" role="radio" title="${esc(LL("Inclinar: arrastra con el botón derecho o con dos dedos", "Tilt: drag with the right button or two fingers"))}">3D</button></div>
          ${fold("right")}
        </div>
        <div class="heat-ttl" id="heat-ttl" hidden><h2 id="heat-h"></h2><p id="heat-s"></p></div>
        <div class="wx-time" id="wx-bar" data-mode="trend">
          <button class="wx-play"></button>
          <button class="wx-trendbtn" aria-pressed="true"></button>
          <div class="wx-track" role="slider" tabindex="0" aria-label="${esc(LL("Año", "Year"))}"></div>
          <div class="wx-legend" id="wx-legend"></div>
        </div>
      </section>
      ${layout === "wide" ? `<aside class="wx-right" id="wx-right"><div class="wx-scroll">${extra}</div></aside>` : ""}
    </div>
    <div class="tr-tip" id="tr-tip" role="tooltip" hidden></div>
    <dialog class="s13-lb" id="s13-lb" aria-labelledby="s13-lb-h">
      <button class="s13-x" aria-label="${esc(LL("Cerrar", "Close"))}">×</button>
      <h2 id="s13-lb-h">${esc(LL("¿IMERG cuenta menos días de lluvia?", "Is IMERG counting fewer rain days?"))}</h2>
      ${hallazgo(hzData)}
      <details class="s13-more"><summary>${esc(LL("Notas sobre el ajuste y figuras del informe", "Notes on the adjustment and report figures"))}</summary>${warn13}
      <img data-src="figuras/09_tercer_testigo_era5_dark.png" alt="${esc(LL("Diferencia de días de lluvia de IMERG y de CHIRPS frente a ERA5 en seis puntos de República Dominicana, 2001-2024.", "Rain-day difference of IMERG and CHIRPS against ERA5 at six points in the Dominican Republic, 2001-2024."))}">
      <img data-src="figuras/08_after_the_correction_dark.png" alt="${esc(LL("Mapas de SDII y de rachas secas de 15 días, publicados y con el ajuste hacia CHIRPS, y celdas en disputa según el año de corte del ajuste.", "SDII and 15-day dry-spell maps, published and with the adjustment towards CHIRPS, and disputed cells by cut year of the adjustment."))}"></details>
    </dialog>
  </div>`;

  const $ = <T extends HTMLElement = HTMLElement>(id: string) => document.getElementById(id) as T;
  const wx = $("wx"), tip = $("tr-tip");
  // la capa de lugares se crea más abajo, pero el mapa puede pintarse antes (al redimensionar): se declara aquí
  let sites: ReturnType<typeof sitesLayer> | null = null;
  const vm = () => d.vm(sel.ind);
  const years = () => d.years(sel);
  const regName = () => (sel.reg === "DO" ? LL("República Dominicana", "Dominican Republic") : d.regName(sel.reg));

  // ── Región y hallazgo ──
  const both = () => d.prods.map((p) => ({ p, t: d.tr(sel, p) })).filter((x): x is { p: string; t: Tr } => !!x.t);
  const renderHead = () => {
    $("wx-h1").textContent = regName();
    // la pista dice cómo cambiar de lugar; con una provincia elegida, cómo volver al país
    $("finding").innerHTML = sel.reg === "DO" ? esc(LL("o toca una provincia en el mapa", "or tap a province on the map")) : `<button class="place-back" data-reg-all>${esc(LL("Ver todo el país", "See the whole country"))}</button>`;
    if (layout === "phone" && ui.land && land) { $("peek-ans").innerHTML = landPeek(land, ui.land, ui.landVar); return; }
    if (layout === "phone") {
      const ti = d.tier(sel), q = questionOf(sel.ind);
      $("peek-ans").innerHTML = `<span class="pa-q">${esc(LL(q.es, q.en))}</span>${both().map(({ p, t }) => `<span class="pa-w"><i style="background:${PROD_COLOR[p]}"></i>${p} <b class="num">${sgn(t.pendiente_decada)}</b></span>`).join("")}<span class="chip" style="--c:${ti.color}">${esc(ti.label)}</span>`;
    }
  };

  // ── Preguntas: una lista de selección (un solo nivel); la respuesta de la elegida va siempre debajo ──
  const renderQuestions = () => {
    const q0 = questionOf(sel.ind);
    // cuatro aspectos de la lluvia, cada uno con su veredicto: lo que está en disputa llama primero
    const tiles = QUESTIONS.map((q) => {
      const v = verdict(d, sel, pick[q.id]), on = !ui.land && q.id === q0.id;
      return `<button class="qt ${on ? "on" : ""}" data-q="${q.id}" role="radio" aria-checked="${on}" title="${esc(`${LL(q.es, q.en)} ${v.text}`)}"><span class="qt-l">${esc(chip(q.id))}</span><span class="qt-v" style="--c:${v.color}"><i class="${v.strong ? "" : "no"}"></i>${esc(v.short)}</span></button>`;
    }).join("");
    // la medida: un solo selector (las alternativas se consultan, no compiten por la vista)
    const mv = verdict(d, sel, sel.ind);
    const measure = ui.land ? "" : `<button class="pick mpick" id="m-btn" aria-haspopup="listbox" aria-expanded="false"><span>${esc(LL("Medido como", "Measured as"))}</span><b>${esc(chip(sel.ind))}</b><i class="mp-d ${mv.strong ? "" : "no"}" style="--c:${mv.color}"></i><em style="--vc:${mv.strong ? mv.color : "var(--muted)"}">${esc(mv.short)}</em>${CHEV}</button>`;
    $("qs").innerHTML = `<div class="qgrid">${tiles}</div>${measure}`;
    const lqs = document.getElementById("lqs");
    if (lqs && land) lqs.innerHTML = LAND_Q.map((q) => {
      const on = ui.land === q.id;
      return `<button class="ql ${on ? "on" : ""}" data-landq="${q.id}" role="radio" aria-checked="${on}"><i></i>${esc(LL(q.es, q.en))}</button>`;
    }).join("");
  };

  // ── El rastro: cómo cambió el veredicto mientras se interrogaba la respuesta ──
  const stamp = (label: string) => {
    if (ui.land) return;
    let v = verdict(d, sel, sel.ind) as { color: string; short: string };
    const nac = d.fix && sel.reg === "DO" ? d.s13?.nacional_IMERG[sel.ind]?.[d.perFor(sel.ind, sel.per)]?.sin_escalon : undefined;
    if (nac) v = { color: d.V.clases[nac.clase]?.color ?? v.color, short: d.V.clases[nac.clase] ? d.lab(d.V.clases[nac.clase]) : nac.clase };
    ui.trail.push({ label, color: v.color, short: v.short });
    if (ui.trail.length > 6) ui.trail.shift();
  };

  // ── La respuesta: época, medidas con su veredicto, los dos testigos, la frase, la escalera y la prueba ──
  // Sensibilidad al ajuste hacia CHIRPS: no identifica ni elimina un mecanismo físico.
  const adjLever = () => {
    const S = d.s13;
    if (!S || !d.stepped(sel.ind)) return "";
    const rc = S.recuentos[sel.ind]?.[d.perFor(sel.ind, sel.per)];
    return `<button class="adj ${d.fix ? "on" : ""}" id="s13-h" data-fix="${d.fix ? 0 : 1}" aria-pressed="${d.fix}" title="${esc(LL(DRIFT_ES, DRIFT_EN))}"><span>${esc(LL("¿Y si IMERG cuenta mal los días de lluvia?", "What if IMERG miscounts rain days?"))}</span><i aria-hidden="true"></i></button>
      ${d.fix && rc ? `<div class="adj-res"><p><b class="num">${rc.en_disputa_publicado}</b><svg viewBox="0 0 28 12" aria-hidden="true"><path d="M2 6h20m-5-4 5 4-5 4" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg><b class="num ok">${rc.en_disputa_sin_escalon}</b></p><span>${esc(LL("celdas en disputa en el mapa al ajustar IMERG hacia CHIRPS. Es una prueba de sensibilidad, no una corrección.", "disputed cells on the map when IMERG is adjusted towards CHIRPS. A sensitivity test, not a correction."))}</span><button class="s13-fig" data-fig13>${esc(LL("Ver los testigos", "See the witnesses"))}</button></div>` : ""}`;
  };
  const cyAnswer = (i: CyInfo) => {
    const box = $("ans"); if (!cyApi) return;
    $("ans-h").textContent = LL("Ciclones", "Cyclones");
    const G = (svg: string) => `<svg viewBox="0 0 40 16" aria-hidden="true">${svg}</svg>`;
    const CATS: [string, string, string][] = [["#8fd3ff", "depresión", "depression"], ["#30d1c5", "tormenta", "storm"], ["#ffe066", "H1", "H1"], ["#ffb347", "H2", "H2"], ["#ff6b35", "H3", "H3"], ["#ff3b5c", "H4", "H4"], ["#d33ad3", "H5", "H5"]];
    const nf = (x: number, dg = 0) => x.toLocaleString(LL("es-DO", "en-US"), { maximumFractionDigits: dg });
    box.innerHTML = `
      <p class="vd" style="--c:#64d2ff"><b>${esc(i.yuna ? LL(`${i.n} inundaciones`, `${i.n} floods`) : LL(`${i.n} tormentas`, `${i.n} storms`))}</b><span>${esc(i.yuna ? LL("del río Yuna llegaron con un ciclón, 2001–2024", "of the Yuna river came with a cyclone, 2001–2024") : (i.place === "DO" ? LL("pasaron a menos de 200 km de alguna provincia, 2001–2024", "passed within 200 km of some province, 2001–2024") : LL(`pasaron a menos de 200 km de ${i.label}, 2001–2024`, `passed within 200 km of ${i.label}, 2001–2024`)))}</span></p>
      <div class="cy-k">
        <p><b>${i.med === null ? "—" : `${i.med} h`}</b><span>${esc(LL("de aviso mediano", "median warning"))}</span></p>
        <p><b class="w">${i.late + i.none}</b><span>${esc(LL("sin aviso o tarde", "no or late warning"))}</span></p>
      </div>
      <p class="cy-def">${esc(LL("Aviso: desde que el NHC publica el boletín hasta que la tormenta llega.", "Warning: from the NHC advisory's publication until the storm arrives."))}</p>
      <h3 class="cy-h">${esc(LL("En el mapa", "On the map"))}</h3>
      <ul class="cy-read">
        <li>${G('<path d="M2 8h36" stroke="#fff" stroke-width="3" stroke-linecap="round"/><circle cx="10" cy="8" r="4" fill="#ffe066"/><circle cx="28" cy="8" r="4" fill="#ff3b5c"/>')}<span>${esc(LL("Trayectoria; el color es su fuerza", "Track; colour is strength"))}</span></li>
        <li class="cy-cats" aria-label="${esc(LL("Fuerza", "Strength"))}">${CATS.map(([c, es, en]) => `<em style="--k:${c}">${esc(LL(es, en))}</em>`).join("")}</li>
        <li>${G('<path d="M2 8h36" stroke="#fff" stroke-width="3" stroke-dasharray="5 5" stroke-linecap="round"/><circle cx="20" cy="8" r="4" fill="#fff" stroke="#ff3b30" stroke-width="2"/>')}<span>${esc(LL("Primer pronóstico del NHC", "First NHC forecast"))}</span></li>
        <li>${G('<circle cx="20" cy="8" r="6.5" fill="none" stroke="#ff9f0a" stroke-width="2" stroke-dasharray="3 3"/>')}<span>${esc(i.place === "DO" ? LL("200 km de la provincia más cercana", "200 km of the nearest province") : LL(`200 km de ${i.label}`, `200 km of ${i.label}`))}</span></li>
        <li>${G('<rect x="2" y="6" width="36" height="5" rx="2.5" fill="#2a2d31"/><rect x="11" y="2" width="2" height="13" rx="1" fill="#64d2ff"/><rect x="27" y="2" width="2" height="13" rx="1" fill="#ff9f0a"/>')}<span><i class="cy-b">${esc(LL("Aviso", "Warning"))}</i> · <i class="cy-o">${esc(LL("llegada", "arrival"))}</i></span></li>
      </ul>
      ${hzData ? (() => { const c = hzData!.ciclones_sequia, pct = (x: number) => `${nf(x * 100 < 1 ? Math.round(x * 1000) / 10 : Math.round(x * 100), 1)} %`;
        return `<h3 class="cy-h">${esc(LL("¿Dejan sequía los ciclones?", "Do cyclones leave drought behind?"))} <b class="cy-no">${esc(LL("No se sostiene", "Not supported"))}</b></h3>
        <dl class="cy-facts">
          <div><dt>${pct(c.fraccion_ciclon_media)}</dt><dd>${esc(LL("de la lluvia de junio a noviembre llega con un ciclón", "of June–November rain comes with a cyclone"))}<span>${esc(LL(`a menos de 500 km · de ${pct(c.fraccion_ciclon_rango[0])} a ${pct(c.fraccion_ciclon_rango[1])} según el año`, `within 500 km · ${pct(c.fraccion_ciclon_rango[0])} to ${pct(c.fraccion_ciclon_rango[1])} by year`))}</span></dd></div>
          <div><dt>${pct(c.frac_dias_sequia_90d_tras_ciclon)}</dt><dd>${esc(LL("de los días en sequía, 90 días tras un ciclón", "of days in drought, 90 days after a cyclone"))}<span>${esc(LL(`${pct(c.frac_dias_sequia_resto_ago_dic)} el resto del tiempo`, `${pct(c.frac_dias_sequia_resto_ago_dic)} otherwise`))}</span></dd></div>
          <div><dt>p ${nf(c.p_permutacion_S2, 2)}</dt><dd>${esc(LL("poca lluvia de ciclón no trae más sequía después", "little cyclone rain does not bring more drought afterwards"))}</dd></div>
        </dl>`; })() : ""}
      <button class="pop-go alt" data-cy-yuna="${i.yuna ? sel.reg : "yuna"}"><span>${esc(i.yuna ? LL(`Volver a ${sel.reg === "DO" ? LL("todo el país", "the whole country") : d.regName(sel.reg)}`, `Back to ${sel.reg === "DO" ? "the whole country" : d.regName(sel.reg)}`) : LL("Ver las inundaciones del Yuna, con su viento", "See the Yuna floods, with their wind"))}</span>${CHEV}</button>
      <p class="cy-src">${esc(LL("Trayectorias IBTrACS (NOAA) · pronósticos NHC tal como se emitieron · lluvia y satélite NASA (IMERG, MODIS). Apoyo para preparar; no es una orden de evacuación.", "Tracks IBTrACS (NOAA) · NHC forecasts as issued · NASA rain and satellite (IMERG, MODIS). Support for preparedness, not an evacuation order."))}</p>`;
  };
  const prepStart = () => {
    if (cyApi) { cyOff?.(); renderAnswer(); }
    const col = wx.querySelector<HTMLElement>(".wx-mapcol")!;
    const over = document.createElement("div"); over.className = "prep-over"; col.appendChild(over);
    viewPreparation(over, true);
    wx.dataset.cy = "on";
    const b = wx.querySelector("[data-prepq]"); b?.setAttribute("aria-pressed", "true"); b?.classList.add("on");
    prepOff = () => { destroyPreparation(); over.remove(); prepOff = null; wx.dataset.cy = "off"; b?.setAttribute("aria-pressed", "false"); b?.classList.remove("on"); };
    cleanup.push(() => prepOff?.());
  };
  const cyStart = () => {
    if (prepOff) prepOff();
    const col = wx.querySelector<HTMLElement>(".wx-mapcol")!;
    const over = document.createElement("div"); over.className = "cy-over"; col.appendChild(over);
    const rs = wx.querySelector<HTMLElement>("#wx-right .wx-scroll");
    const list = rs ? Object.assign(document.createElement("section"), { className: "cy-list" }) : null;
    if (rs && list) { rs.prepend(list); rs.scrollTop = 0; wx.dataset.cyl = "on"; }
    const h = hurricanes(over, { place: sel.reg, hidePlace: true, onInfo: cyAnswer, list });
    cyApi = h; wx.dataset.cy = "on";
    wx.querySelector("[data-cyq]")?.setAttribute("aria-pressed", "true");
    wx.querySelector("[data-cyq]")?.classList.add("on");
    $("sty-l").textContent = LL("Huracanes", "Hurricanes");
    cyOff = () => { h.destroy(); over.remove(); list?.remove(); delete wx.dataset.cyl; cyOff = null; cyApi = null; wx.dataset.cy = "off"; $("sty-l").textContent = styles.find(([k]) => k === ui.style)?.[1] ?? ""; wx.querySelector("[data-cyq]")?.setAttribute("aria-pressed", "false"); wx.querySelector("[data-cyq]")?.classList.remove("on"); };
    cleanup.push(() => cyOff?.());
    $("ans").innerHTML = `<p class="cy-src">${esc(LL("Cargando las tormentas…", "Loading the storms…"))}</p>`;
    $("ans").scrollIntoView({ block: "start", behavior: RM() ? "auto" : "smooth" });
  };
  const renderAnswer = () => {
    const box = $("ans");
    if (cyApi) { cyApi.setPlace(sel.reg); return; }
    if (ui.land && land) {
      renderHead();
      $("ans-h").textContent = ui.land === "verde" ? LL("Qué dice MODIS", "What MODIS says") : LL("Qué dice la auditoría", "What the audit says");
      box.innerHTML = ui.land === "verde" ? verdeAnswer(land, ui.landVar, ui.landSite) : recuperaAnswer(land, ui.landSite);
      return;
    }
    $("ans-h").textContent = LL("Qué dicen las dos fuentes", "What the two sources say");
    const v = vm(), ws = both(), cls = d.row(sel)?.clase ?? "";
    const season = `<div class="per4" role="radiogroup" aria-label="${esc(LL("Época del año", "Season"))}">
        ${Object.keys(d.V.periodos).map((k) => { const ok = v.periodos.includes(k), pv = ok ? verdict(d, { ...sel, per: k }, sel.ind) : null;
          return `<button data-per="${k}" role="radio" aria-checked="${k === sel.per}" class="${k === sel.per ? "on" : ""}" title="${esc(ok ? d.lab(d.V.periodos[k]) : LL("El SPI solo existe para el año completo", "SPI exists for the whole year only"))}" ${ok ? "" : "disabled"}><b>${esc(LL(...SEASON[k]))}</b>${pv ? `<em class="${pv.strong ? "" : "weak"}" style="--c:${pv.color}">${esc(pv.short)}</em>` : ""}</button>`; }).join("")}
      </div>`;
    const levers = `<div class="lev"><h3 class="lev-h">${esc(LL("Ponlo a prueba", "Put it to the test"))}</h3><p class="lev-q">${esc(LL("¿Cambia según la época del año?", "Does it change with the season?"))}</p>${season}${adjLever()}</div>`;
    const last = ui.trail.length - 1;
    const trail = ui.trail.length > 1 ? `<h3 class="lev-h trail-h">${esc(LL("Lo que has probado", "What you have tried"))}</h3><ol class="trail" aria-label="${esc(LL("Cómo cambió el veredicto", "How the verdict changed"))}">${ui.trail.map((t, i) => `<li class="${i === last ? "on" : ""}" style="--c:${t.color}"><span>${esc(t.label)}</span><em>${esc(t.short)}</em></li>`).join("")}</ol>` : "";
    if (!ws.length) { box.innerHTML = `${levers}<p class="empty">${esc(LL("No hay datos para esta combinación.", "No data for this combination."))}</p>`; return; }
    const ti = d.tier(sel), vv = verdict(d, sel, sel.ind);
    const sigW = ws.filter((w) => d.isSig(w.t, sel.reg)), other = ws.filter((w) => !d.isSig(w.t, sel.reg));
    const mdt = Math.max(...ws.map((w) => w.t.mdt));
    const up = (sigW[0] ?? ws[0]).t.pendiente_decada > 0, dir = up ? LL("sube", "rising") : LL("baja", "falling");
    // lo que se puede afirmar y lo que no, en una línea cada uno
    const [yes, no] =
      cls === "robusta" ? [LL(`Las dos fuentes coinciden: ${dir}.`, `Both sources agree: ${dir}.`), LL("Por qué: los datos describen, no atribuyen causas.", "Why: the data describe, they do not attribute causes.")]
      : cls === "consistente" ? [LL(`Probablemente ${dir}: lo confirma ${sigW.map((w) => w.p).join(" y ")}.`, `Probably ${dir}: ${sigW.map((w) => w.p).join(" and ")} confirms it.`), LL(`Si ${other.map((w) => w.p).join(" y ")} lo confirmará con más años.`, `Whether ${other.map((w) => w.p).join(" and ")} will confirm it with more years.`)]
      : cls === "en disputa" ? [LL("Las dos fuentes apuntan en sentidos opuestos.", "The two sources point in opposite directions."), d.stepped(sel.ind) ? LL("Si cambia la lluvia o la forma en que IMERG cuenta los días.", "Whether the rain changes or the way IMERG counts the days.") : LL("Cuál de las dos lee mejor este lugar.", "Which of the two reads this place better.")]
      : cls === "sin dato" ? [LL("Faltan años en una de las series.", "Years are missing in one of the series."), LL("La tendencia: no se calcula.", "The trend: it is not computed.")]
      : cls === "un solo producto" && sigW.length ? [LL(`${up ? "Sube" : "Baja"} según ${ws[0].p}.`, `${up ? "Rising" : "Falling"} according to ${ws[0].p}.`), LL("Falta la segunda fuente.", "The second source is missing.")]
      : [LL(`No hay cambio mayor de ±${num(mdt)} ${v.unidad} por década.`, `No change larger than ±${num(mdt)} ${v.unidad} per decade.`), LL("Si hay cambios más pequeños: con 24 años no se ven.", "Whether there are smaller changes: 24 years cannot show them.")];
    const tierIdx = TIERS.findIndex(([k]) => k === ti.tier);
    const pFmt = (t: Tr) => (t.p < 0.001 ? `&lt;&#8239;${num(0.001, 3)}` : num(t.p, 3));
    box.innerHTML = `
      <button class="vd" data-vd style="--c:${vv.color}" aria-haspopup="dialog" aria-expanded="false" title="${esc(LL("Ver por qué y compararlo en la Auditoría", "See why and compare it in the Audit"))}"><b>${esc(vv.short)}</b>${tierIdx >= 0 ? `<span>${esc(LL(TIERS[tierIdx][1], TIERS[tierIdx][2]))}</span>` : ""}<em>${esc(LL("Por qué", "Why"))}${CHEV}</em></button>
      ${capsule(d, sel)}
      ${hallazgoCorto(hzData) ? `${hallazgoCorto(hzData)}<button class="pop-go alt hzc-go" data-fig13><span>${esc(LL("Ver el hallazgo completo: Hawái y los dos escalones", "See the full finding: Hawaii and the two steps"))}</span>${CHEV}</button>` : ""}
      ${levers}
      ${trail}
      <ul class="claims">
        <li class="yes"><b>${esc(LL("Sabemos:", "We know:"))}</b> ${esc(yes)}</li>
        <li class="no"><b>${esc(LL("Falta saber:", "Still unknown:"))}</b> ${esc(no)}</li>
        <li class="why"><b>${esc(LL("Importa porque:", "It matters because:"))}</b> ${esc(v.por_que_importa)}</li>
      </ul>
      <div class="ans-go">
        <button class="pop-go" data-act-audit><span>${esc(LL(`¿Coinciden los 4 productos en la sequía? Ver ${sel.reg === "DO" ? "el país" : d.regName(sel.reg)} en la Auditoría`, `Do the 4 products agree on drought? See ${sel.reg === "DO" ? "the country" : d.regName(sel.reg)} in the Audit`))}</span>${CHEV}</button>
      </div>
      <details class="ans-more">
      <summary>${esc(LL("Estadística y notas", "Statistics and notes"))}${CHEV}</summary>
      <table class="stats-t">
        <thead><tr><th></th><th class="num" title="${esc(LL("Mann-Kendall modificado de Hamed y Rao (1998)", "Hamed & Rao (1998) modified Mann-Kendall"))}">p</th><th class="num" title="${esc(LL("Benjamini-Hochberg entre las 32 provincias", "Benjamini-Hochberg across the 32 provinces"))}">q (FDR)</th><th class="num" title="${esc(LL("80 % de potencia, α = 0,05", "80 % power, α = 0.05"))}">${esc(LL("Mín. detect.", "Min. detect."))}</th><th class="num">${esc(LL("Media", "Mean"))}</th></tr></thead>
        <tbody>${ws.map(({ p, t }) => `<tr><th scope="row"><i style="background:${PROD_COLOR[p]}"></i>${p}</th><td class="num">${pFmt(t)}</td><td class="num">${t.q === null ? "—" : num(t.q, 3)}</td><td class="num">±${num(t.mdt)}</td><td class="num">${num(t.media)}</td></tr>`).join("")}</tbody>
      </table>
      <p class="rule">${esc(LL(`Significativa si ${d.sigRule(sel.reg)}. ${v.descripcion}`, `Significant if ${d.sigRule(sel.reg)}. ${v.descripcion}`))}</p>
      <p class="rule">${esc(LL("IMERG y CHIRPS comparten insumos (infrarrojo y pluviómetros): si discrepan, cada uno lee distinto la misma lluvia, y eso es lo que se investiga.", "IMERG and CHIRPS share inputs (infrared and gauges): if they disagree, each reads the same rain differently, and that is what gets investigated."))} ${esc(d.V.nota_causalidad)}</p>
      </details>`;
  };

  // ── Año a año y las 32 provincias (plegables) ──
  const plotW = (el: HTMLElement) => Math.max(260, el.clientWidth);
  const isOpen = (id: string) => (document.getElementById(`${id}-sec`) as HTMLDetailsElement | null)?.open ?? false;
  const showYear = (k: number | null) => {
    const r = $("s-meta"), s = d.series(sel);
    if (k === null || !s) { r.textContent = ""; return; }
    const v = s[k];
    r.textContent = v === null ? `${years()[k]} · —` : `${years()[k]} · ${num(v)} ${vm().unidad}`;
  };
  const renderSeries = () => {
    $("s-h").textContent = LL("Año a año", "Year by year");
    if (!isOpen("s")) { showYear(ui.year); return; }
    const el = $("s-plot");
    const vv = vm(), unitY = vv.unidad.includes("/") ? vv.unidad : `${vv.unidad} ${sel.per === "anual" ? LL("por año", "per year") : LL("por temporada", "per season")}`;
    const tI = d.tr(sel, "IMERG"), tC = d.tr(sel, "CHIRPS");
    const reads = d.stepped(sel.ind) && tI && tC && Math.sign(tI.pendiente_decada) !== Math.sign(tC.pendiente_decada)
      ? `<p class="tr-read">${esc(LL("IMERG cuenta menos días de llovizna, sobre todo desde 2018; por eso este índice puede cambiar en IMERG sin que cambie la lluvia. CHIRPS no lo confirma.", "IMERG counts fewer drizzle days, above all since 2018, so this index can change in IMERG without the rain changing. CHIRPS does not confirm it."))}</p>` : "";
    el.innerHTML = `<p class="tr-what"><b>${esc(d.lab(vv))}</b> ${esc(vv.descripcion)} <span>${esc(LL(`Eje vertical: ${unitY}. Pendiente: ${vv.unidad_tendencia}.`, `Vertical axis: ${unitY}. Slope: ${vv.unidad_tendencia}.`))}</span></p>`
      + seriesChart(d, sel, plotW(el), ui.year === null ? null : years()[ui.year], layout === "wide" ? 190 : 170) + reads;
    el.title = LL("Toca un año para verlo en el mapa", "Tap a year to see it on the map");
    const hit = el.querySelector<SVGRectElement>(".tr-hit");
    if (hit) {
      const yrs = years(), W = Number(hit.dataset.w), ml = Number(hit.dataset.ml), mr = Number(hit.dataset.mr);
      const idxAt = (x: number) => { const r = hit.ownerSVGElement!.getBoundingClientRect(); return Math.max(0, Math.min(yrs.length - 1, Math.round(((((x - r.left) / r.width) * W - ml) / (W - ml - mr)) * (yrs.length - 1)))); };
      hit.addEventListener("mousemove", (e) => showYear(idxAt(e.clientX)));
      hit.addEventListener("mouseleave", () => showYear(ui.year));
      hit.addEventListener("click", (e) => tl.pick(idxAt(e.clientX)));
    }
    showYear(ui.year);
  };
  const renderRank = () => {
    const el = $("r-plot"), f = forest(d, sel, plotW(el));
    const c = f.counts, n = (k: string) => c[k] ?? 0;
    $("r-meta").textContent = d.both
      ? ([["robusta", "robustas", "robust"], ["consistente", "consistentes", "consistent"], ["en disputa", "en disputa", "disputed"]] as const).filter(([k]) => n(k)).map(([k, es, en]) => `${n(k)} ${LL(es, en)}`).join(" · ") || LL("ninguna con señal", "none with a signal")
      : LL(`${n("un solo producto")} con una fuente`, `${n("un solo producto")} with one source`);
    if (!isOpen("r")) return;
    el.innerHTML = `<p class="tr-what"><b>${esc(d.lab(vm()))}</b> ${esc(LL(`Posición: cambio por década, en ${vm().unidad_tendencia}. A la izquierda del 0, baja; a la derecha, sube.`, `Position: change per decade, in ${vm().unidad_tendencia}. Left of 0 it falls; right of 0 it rises.`))}</p><p class="hint">${esc(LL("Punto lleno: cambio claro · línea: intervalo del 95 % · toca una provincia", "Filled dot: clear change · line: 95 % interval · tap a province"))}</p>${f.svg}`;
  };
  (["s", "r"] as const).forEach((id) => document.getElementById(`${id}-sec`)?.addEventListener("toggle", () => (id === "s" ? renderSeries() : renderRank())));

  // ── El mapa ──
  const INDUCED = "#8f9ba8";
  const induced = () => d.fix && d.stepped(sel.ind);
  const clsName = (k: string) => (induced() && k === "robusta" ? LL("Acuerdo inducido por el ajuste", "Agreement induced by the adjustment") : d.V.clases[k] ? d.lab(d.V.clases[k]) : k);
  const clsColor = (k: string) => (induced() && k === "robusta" ? INDUCED : d.V.clases[k]?.color ?? "#6b6f75");
  const fixTag = () => (d.fix && d.stepped(sel.ind) && (ui.show === "acuerdo" || sel.src === "IMERG") ? ` · <b class="lg-fix">${esc(LL("sensibilidad: IMERG ajustado hacia CHIRPS", "sensitivity: IMERG adjusted to CHIRPS"))}</b>` : "");
  const renderLegend = (max: number, pct: boolean) => {
    const v = vm(), up = v.tipo === "seco" ? LL("más seco", "drier") : LL("más lluvia", "more rain"), dn = v.tipo === "seco" ? LL("menos seco", "less dry") : LL("menos lluvia", "less rain");
    const f = (x: number) => (pct ? `${sgn(x, 0)} %` : sgn(x));
    $("wx-legend").innerHTML = `
      <div class="lg-w"><span>${esc(dn)}</span><span>${esc(pct ? LL("frente a su media", "vs its mean") : v.unidad_tendencia)}${pct ? "" : fixTag()}</span><span>${esc(up)}</span></div>
      <div class="lg-bar" style="background:${rampCss(d.warmIfUp(sel.ind))}"></div>
      <div class="lg-ax num"><span>${f(-max)}</span><span>0</span><span>${f(max)}</span></div>`;
  };
  const yearMax = new Map<string, number>();
  const anomaly = (reg: string, k: number) => {
    const s = d.series(sel, sel.src, reg); if (!s) return null;
    const vals = s.filter((x): x is number => x !== null), mean = vals.reduce((a, b) => a + b, 0) / vals.length;
    return s[k] === null || !mean ? null : ((s[k]! - mean) / mean) * 100;
  };
  const hexRGB = (h: string): [number, number, number] => { const n = parseInt(h.replace("#", ""), 16); return [(n >> 16) & 255, (n >> 8) & 255, n & 255]; };
  let ridgeColor: (k: number) => RGBA | null = () => null;
  const renderMap = (anim = true) => {
    wx.dataset.land = ui.land ? "on" : "off";
    $("heat-ttl").hidden = !(ui.year === null && ui.style === "calor" && !ui.land);
    riversOn();
    if (ui.land && land) { renderLandMap(anim); return; }
    sites?.set([]);
    renderMap0(anim);
    if (ui.style === "crestas" && ui.d3) ridges3d();
  };
  const renderLandMap = (anim: boolean) => {
    if (!land) return;
    paintRidge(anim);
    sites?.set(siteMarks(land, ui.land, ui.landVar, ui.landSite));
    $("wx-legend").innerHTML = ui.land === "verde"
      ? `<p class="lg-w"><span>${esc(LL("Puntos de MODIS: relleno = cambio claro · naranja = hacia lo seco o caliente", "MODIS points: filled = clear change · orange = towards dry or hot"))}</span></p>`
      : `<p class="lg-w"><span>${esc(LL("Lugares auditados: relleno = alguna sequía con impacto · naranja = estrés invisible", "Audited sites: filled = some drought with impact · orange = invisible stress"))}</span></p>`;
    describeRidge();
    if (!t3) return;
    const m = t3.map;
    if (m.getLayer("cells")) m.setLayoutProperty("cells", "visibility", "none");
    if (m.getLayer("stip")) m.setLayoutProperty("stip", "visibility", "none");
    const clear: Record<string, string> = {}, zero: Record<string, number> = {};
    d.provs.forEach((r) => { const id = d.isoToShape[r.id]; if (id) { clear[id] = "rgba(0,0,0,0)"; zero[id] = 0; } });
    t3.setChoro(clear, zero);
    if (ui.style === "crestas" && ui.d3) ridges3d();
  };
  const renderMap0 = (anim = true) => {
    wx.dataset.mode = ui.year === null ? "trend" : "year";
    paintRidge(anim);
    if (!t3) return;
    const map = t3.map;
    if (ui.year === null && ui.style === "calor") { renderHeat(); return; }
    shadeOver(false);
    if (ui.year === null && ui.show === "acuerdo") {
      const cl = d.cellClass(sel), codes = d.R.clases_codigo ?? [];
      if (!cl) return;
      const colors = codes.map(clsColor);
      const f = classField(d.R, cl, colors, d.fc);
      t3.setCells(f.px, f.w, f.h, f.bounds);
      t3.setLayer("cells");
      if (map.getLayer("stip")) map.setLayoutProperty("stip", "visibility", "none");
      const clear: Record<string, string> = {}, zero: Record<string, number> = {};
      d.provs.forEach((r) => { const id = d.isoToShape[r.id]; if (id) { clear[id] = "rgba(0,0,0,0)"; zero[id] = 0; } });
      t3.setChoro(clear, zero);
      map.setLayoutProperty("prov-fill", "visibility", "visible");
      const counts = codes.map((_, i) => cl.filter((x, k) => x === i && d.R.incluida[k]).length);
      $("wx-legend").innerHTML = `<p class="lg-w"><span>${esc(LL("Veredicto de las dos fuentes, celda a celda (11 km)", "Verdict of the two sources, cell by cell (11 km)"))}${fixTag()}</span></p>
        <p class="lg-cls">${codes.map((k, i) => `<span><i style="background:${colors[i]}"></i>${esc(clsName(k))} <b class="num">${counts[i]}</b></span>`).join("")}</p>`;
      describeRidge();
      return;
    }
    if (ui.year === null) {
      const lay = d.cells(sel);
      if (!lay) return;
      const max = scaleMax(lay.pendiente_decada), q = d.V.umbral_significancia.q_fdr;
      const f = trendField(d.R, lay, q, max, (v) => d.towardDry(sel.ind, v), d.fc);
      t3.setCells(f.px, f.w, f.h, f.bounds);
      t3.setLayer("cells");
      const src = map.getSource("stip") as maplibregl.GeoJSONSource | undefined;
      if (src) src.setData(stipple(d.R, lay, q));
      else {
        map.addSource("stip", { type: "geojson", data: stipple(d.R, lay, q) });
        map.addLayer({ id: "stip", type: "circle", source: "stip", paint: { "circle-radius": ["interpolate", ["linear"], ["zoom"], 6, 1, 8, 1.8, 11, 3.5], "circle-color": "#ffffff", "circle-opacity": 0.85 } });
      }
      map.setLayoutProperty("stip", "visibility", "visible");
      const clear: Record<string, string> = {}, zero: Record<string, number> = {};
      d.provs.forEach((r) => { const id = d.isoToShape[r.id]; if (id) { clear[id] = "rgba(0,0,0,0)"; zero[id] = 0; } });
      t3.setChoro(clear, zero);
      map.setLayoutProperty("prov-fill", "visibility", "visible");
      renderLegend(max, false);
      describeRidge();
    } else {
      const k = ui.year, key = `${sel.ind}|${sel.per}|${sel.src}`;
      if (!yearMax.has(key)) yearMax.set(key, scaleMax(d.provs.flatMap((r) => years().map((_, j) => anomaly(r.id, j)))));
      const max = yearMax.get(key)!;
      const colors: Record<string, string> = {}, alpha: Record<string, number> = {};
      d.provs.forEach((r) => {
        const id = d.isoToShape[r.id], a = anomaly(r.id, k); if (!id) return;
        colors[id] = a === null ? "rgba(0,0,0,0)" : `rgb(${colorOf(Math.abs(a) / max, d.towardDry(sel.ind, a)).join(",")})`;
        alpha[id] = a === null ? 0 : 0.82;
      });
      t3.setChoro(colors, alpha);
      t3.setLayer("prov");
      if (map.getLayer("stip")) map.setLayoutProperty("stip", "visibility", "none");
      renderLegend(max, true);
      describeRidge();
    }
  };
  // ── Calor: el dato de cada celda como un campo suave; con «Veredicto», IMERG menos CHIRPS ──
  const renderHeat = () => {
    if (!t3) return;
    const map = t3.map, v = vm(), ver = ui.show === "acuerdo" && d.both;
    const lI = d.cells(sel, "IMERG"), lC = d.cells(sel, "CHIRPS"), lay = ver ? null : d.cells(sel);
    if (ver ? !lI || !lC : !lay) return;
    const raw = (k: number): number | null => {
      if (!ver) return lay!.pendiente_decada[k] ?? null;
      const a = lI!.pendiente_decada[k], b = lC!.pendiente_decada[k];
      return a === null || a === undefined || b === null || b === undefined ? null : a - b;
    };
    const vals = d.R.incluida.map((inc, k) => (inc ? raw(k) : null));
    const max = scaleMax(vals), dry = d.towardDry(sel.ind, 1) ? 1 : -1, q = d.V.umbral_significancia.q_fdr;
    const f = heatField(d.R, (k) => { const x = raw(k); return x === null ? null : (dry * x) / max; }, (k) => !ver && (lay!.q[k] ?? 1) > q, d.fc);
    t3.setCells(f.px, f.w, f.h, f.bounds);
    t3.setLayer("cells");
    shadeOver(true);
    if (map.getLayer("stip")) map.setLayoutProperty("stip", "visibility", "none");
    const clear: Record<string, string> = {}, zero: Record<string, number> = {};
    d.provs.forEach((r) => { const id = d.isoToShape[r.id]; if (id) { clear[id] = "rgba(0,0,0,0)"; zero[id] = 0; } });
    t3.setChoro(clear, zero);
    map.setLayoutProperty("prov-fill", "visibility", "visible");
    const ys = years(), span = ys.length ? `${ys[0]}–${ys[ys.length - 1]}` : "";
    const seco = v.tipo === "seco";
    $("heat-h").textContent = ver ? LL("Dónde se contradicen los dos satélites", "Where the two satellites contradict each other") : LL(`${d.lab(v)}: hacia dónde va según ${sel.src}`, `${d.lab(v)}: where it is heading according to ${sel.src}`);
    $("heat-s").textContent = ver ? LL(`Tendencia de IMERG menos la de CHIRPS · ${chip(sel.ind)} · ${span}`, `IMERG trend minus CHIRPS trend · ${chip(sel.ind)} · ${span}`)
      : LL(`Tendencia ${span}, ${v.unidad_tendencia} · pálido: no se distingue del azar`, `Trend ${span}, ${v.unidad_tendencia} · pale: indistinguishable from chance`);
    const wet = ver ? LL("IMERG, más húmedo", "IMERG wetter") : seco ? LL("menos seco", "less dry") : LL("más lluvia", "more rain");
    const dryW = ver ? LL("IMERG, más seco", "IMERG drier") : seco ? LL("más seco", "drier") : LL("menos lluvia", "less rain");
    const mid = ver ? LL("coinciden", "they agree") : LL("sin cambio", "no change");
    $("wx-legend").innerHTML = `
      <div class="lg-w lg-heat-w"><span>${esc(wet)}</span><span>${esc(mid)}</span><span>${esc(dryW)}</span></div>
      <div class="lg-bar" style="background:${heatCss()}"></div>
      <div class="lg-ax num"><span>${sgn(-dry * max)}</span><span>0 · ${esc(v.unidad_tendencia)}${fixTag()}</span><span>${sgn(dry * max)}</span></div>`;
    describeRidge();
  };
  // El sombreado del relieve pasa encima del calor (solo sombras y luces; lo llano queda transparente): así el campo
  // de color no aplana el relieve, sobre todo en 3D. Fuera del calor vuelve a su sitio, debajo de los datos.
  let shadeHome = "";
  const shadeOver = (on: boolean) => {
    const m = t3?.map; if (!m || !m.getLayer("shade") || !m.getLayer("cells") || !m.getLayer("prov-line")) return;
    const ids = m.getStyle().layers.map((l) => l.id);
    if (!shadeHome) shadeHome = ids[ids.indexOf("shade") + 1] ?? "";
    if (on) { m.moveLayer("shade", "prov-line"); m.setPaintProperty("shade", "hillshade-exaggeration", 0.5); }
    else if (shadeHome && shadeHome !== "shade" && m.getLayer(shadeHome) && ids.indexOf("shade") > ids.indexOf("cells")) m.moveLayer("shade", shadeHome);
  };
  // ── Ríos: con halo azul encima del calor; el Yuna y el Camú, más marcados y con su nombre ──
  const MAIN_RIOS = ["Río Yuna", "Río Camú"];
  let rioPins: maplibregl.Marker[] = [];
  const riversOn = () => {
    const m = t3?.map; if (!m || !rios) return;
    const on = ui.style === "calor" && !ui.land;
    if (!m.getSource("rios-c")) {
      if (!on) return;
      const feat = (r: Rio) => ({ type: "Feature" as const, properties: { main: MAIN_RIOS.includes(r.name) ? 1 : 0, big: r.len_deg > 0.8 ? 1 : 0 }, geometry: { type: "MultiLineString" as const, coordinates: r.parts } });
      m.addSource("rios-c", { type: "geojson", data: { type: "FeatureCollection", features: rios.map(feat) } });
      const isMain = ["==", ["get", "main"], 1], isBig = ["==", ["get", "big"], 1];
      // el zoom va fuera: MapLibre solo admite una interpolación por zoom en la raíz de la expresión
      const z = (main: [number, number], big: [number, number], rest: [number, number]) => ["interpolate", ["linear"], ["zoom"], 7, ["case", isMain, main[0], isBig, big[0], rest[0]], 10, ["case", isMain, main[1], isBig, big[1], rest[1]]];
      const P = (o: Record<string, unknown>) => o as never;
      const lay = { type: "line" as const, source: "rios-c", layout: { "line-join": "round" as const, "line-cap": "round" as const } };
      m.addLayer({ ...lay, id: "rios-c-glow", paint: P({ "line-color": "#2f9bff", "line-blur": ["case", isMain, 7, 3], "line-width": z([14, 22], [5, 8], [5, 8]), "line-opacity": ["case", isMain, 0.7, 0.4] }) });
      m.addLayer({ ...lay, id: "rios-c-case", paint: P({ "line-color": "#04101c", "line-width": z([4.6, 7], [2.6, 4], [2, 3]), "line-opacity": 0.75 }) });
      m.addLayer({ ...lay, id: "rios-c", paint: P({ "line-color": ["case", isMain, "#f2fbff", "#a9dcff"], "line-width": z([2.4, 4], [1.2, 2], [0.8, 1.4]), "line-opacity": 0.95 }) });
    }
    for (const id of ["rios-c-glow", "rios-c-case", "rios-c"]) if (m.getLayer(id)) m.setLayoutProperty(id, "visibility", on ? "visible" : "none");
    // con el calor, los límites de provincia se apagan para que mande el color (la elegida sigue entera)
    if (m.getLayer("prov-line")) m.setPaintProperty("prov-line", "line-opacity", on ? ["case", ["boolean", ["feature-state", "sel"], false], 1, 0.4] as never : 1);
    if (m.getLayer("borde")) m.setPaintProperty("borde", "line-opacity", on ? 0.16 : 0.5);
    rioPins.forEach((p) => p.remove()); rioPins = [];
    if (!on) return;
    for (const r of rios.filter((x) => MAIN_RIOS.includes(x.name))) {
      const part = r.parts.reduce((a, b) => (b.length > a.length ? b : a), r.parts[0]);
      // el Yuna se rotula debajo de su cauce y el Camú encima, para que no se pisen
      const yuna = r.name === "Río Yuna", [lo, la] = part[Math.floor(part.length * (yuna ? 0.6 : 0.45))];
      const el = document.createElement("div"); el.className = "rio-lbl";
      el.textContent = LL(r.name, `${r.name.replace(/^Río /, "")} River`);
      rioPins.push(new maplibregl.Marker({ element: el, anchor: yuna ? "top" : "bottom", offset: [0, yuna ? 6 : -6] }).setLngLat([lo, la]).addTo(m));
    }
  };
  cleanup.push(() => { rioPins.forEach((p) => p.remove()); rioPins = []; });
  const cellProv = d.rel ? cellProvinces(d.R, d.fc) : [];
  let rg: ReturnType<typeof ridges> | null = null;
  const colorFor = (): ((k: number) => RGBA | null) => {
    if (ui.land) return () => null;
    if (ui.year === null && ui.show === "acuerdo") {
      const cl = d.cellClass(sel), codes = d.R.clases_codigo ?? [];
      if (!cl) return () => null;
      const rgb = codes.map((k) => hexRGB(clsColor(k)));
      return (k) => { const c = cl[k]; if (c === null || c === undefined) return null; return [...rgb[c], codes[c] === "sin señal detectable" ? 0.5 : 1]; };
    }
    if (ui.year === null) {
      const lay = d.cells(sel); if (!lay) return () => null;
      const max = scaleMax(lay.pendiente_decada), q = d.V.umbral_significancia.q_fdr;
      return (k) => { const v = lay.pendiente_decada[k]; if (v === null || v === undefined) return null; return [...colorOf(Math.abs(v) / max, d.towardDry(sel.ind, v)), (lay.q[k] ?? 1) <= q ? 1 : 0.5]; };
    }
    const yr = ui.year, key = `${sel.ind}|${sel.per}|${sel.src}`;
    if (!yearMax.has(key)) yearMax.set(key, scaleMax(d.provs.flatMap((r) => years().map((_, j) => anomaly(r.id, j)))));
    const max = yearMax.get(key)!, memo = new Map<string, number | null>();
    return (k) => {
      const iso = cellProv[k]; if (!iso) return null;
      if (!memo.has(iso)) memo.set(iso, anomaly(iso, yr));
      const a = memo.get(iso); if (a === null || a === undefined) return null;
      return [...colorOf(Math.abs(a) / max, d.towardDry(sel.ind, a)), 0.95];
    };
  };
  const paintRidge = (anim = true) => {
    ridgeColor = colorFor();
    if (ui.style !== "crestas") return;
    if (ui.d3) ridges3d(); else rg?.draw(anim && !RM());
  };
  // En 3D las crestas son líneas tendidas sobre el relieve real; el color lo lleva la línea, no la capa de celdas
  const ridges3d = () => {
    if (!t3 || !rg) return;
    const m = t3.map, on = ui.style === "crestas" && ui.d3;
    if (!m.isStyleLoaded() && !m.getSource("prov")) return;
    if (on) {
      const fc = rg.lines(), src = m.getSource("ridge3d") as maplibregl.GeoJSONSource | undefined;
      if (src) src.setData(fc);
      else {
        m.addSource("ridge3d", { type: "geojson", data: fc });
        m.addSource("yuna3d", { type: "geojson", data: rg.yunaLine() });
        m.addSource("rios3d", { type: "geojson", data: { type: "FeatureCollection", features: (rios ?? []).map((r) => ({ type: "Feature" as const, properties: { w: r.len_deg > 0.8 ? 2 : 1.2 }, geometry: { type: "MultiLineString" as const, coordinates: r.parts } })) } });
        const before = m.getLayer("prov-line") ? "prov-line" : undefined;
        m.addLayer({ id: "ridge3d", type: "line", source: "ridge3d", layout: { "line-join": "round", "line-cap": "round" }, paint: { "line-color": ["get", "c"], "line-width": ["interpolate", ["linear"], ["zoom"], 7, 1.3, 10, 2.4] } }, before);
        m.addLayer({ id: "rios3d", type: "line", source: "rios3d", layout: { "line-join": "round", "line-cap": "round" }, paint: { "line-color": "#64beff", "line-width": ["get", "w"], "line-opacity": 0.9 } }, before);
        m.addLayer({ id: "yuna3d", type: "line", source: "yuna3d", paint: { "line-color": "#ffffff", "line-width": 1.6, "line-dasharray": [3, 2] } }, before);
      }
      if (m.getLayer("cells")) m.setLayoutProperty("cells", "visibility", "none");
      if (m.getLayer("stip")) m.setLayoutProperty("stip", "visibility", "none");
      const clear: Record<string, string> = {}, zero: Record<string, number> = {};
      d.provs.forEach((r) => { const id = d.isoToShape[r.id]; if (id) { clear[id] = "rgba(0,0,0,0)"; zero[id] = 0; } });
      t3.setChoro(clear, zero);
    }
    for (const id of ["ridge3d", "yuna3d", "rios3d"]) if (m.getLayer(id)) m.setLayoutProperty(id, "visibility", on ? "visible" : "none");
    t3.refresh3d();
  };
  const base = (): "none" | "dark" | "sat" => (ui.style === "plano" ? "sat" : ui.style === "calor" ? "none" : "dark");
  const exag = () => (ui.style === "crestas" ? 4 : ui.style === "calor" ? 2.2 : 1.8);
  // Fondo y cámara: crestas en 2D se dibujan en su lienzo; todo lo demás lo dibuja el mapa
  const applyView = (fly: boolean) => {
    const flatRidges = ui.style === "crestas" && !ui.d3;
    rg?.show(flatRidges);
    if (!flatRidges) tip.hidden = true;
    if (!t3) return;
    t3.setView(base(), ui.d3, exag());
    lockCam();
    renderMap(false);
    frame(fly);
  };
  const describeRidge = () => rg?.describe(`${LL("Perfiles de relieve de La Española apilados de norte a sur; cada tramo lleva el color de su celda en el mapa.", "Relief profiles of Hispaniola stacked north to south; each stretch takes its cell's map colour.")} ${$("wx-legend").textContent?.replace(/\s+/g, " ").trim() ?? ""}`);
  // El margen inferior sale de la altura real de la línea de tiempo (cambia cuando la leyenda baja a otra fila)
  const barH = () => document.getElementById("wx-bar")?.offsetHeight ?? 76;
  const sideL = () => (layout !== "phone" && ui.left ? 372 : 0), sideR = () => (layout === "wide" && ui.right && !ui.land ? 352 : 0);
  const fitPad = () => (layout === "phone" ? { top: 70, bottom: PEEK + 120, left: 16, right: 16 } : { top: 64, bottom: barH() + 52, left: 32 + sideL(), right: 32 + sideR() });
  const frame = (fly = true) => {
    if (!t3) return;
    t3.setFitPadding(fitPad());
    const b = sel.reg === "DO" ? RD : d.bbox(sel.reg) ?? RD;
    const opts = { padding: fitPad(), pitch: ui.d3 ? 55 : 0, bearing: ui.d3 ? -14 : 0, maxZoom: 10 };
    // inclinado, el encuadre de la caja deja la isla lejos: se acerca medio nivel
    const cam = ui.d3 ? t3.map.cameraForBounds(b, opts) : undefined;
    if (cam && cam.zoom !== undefined) t3.map.easeTo({ ...cam, zoom: Math.min(10, cam.zoom + 0.55), pitch: 55, bearing: -14, duration: fly && !RM() ? 1500 : 0 });
    else t3.map.fitBounds(b, { ...opts, duration: fly && !RM() ? 1500 : 0 });
  };
  // Con las crestas el mapa no gira ni se inclina: el relieve se dibuja de frente
  const lockCam = () => {
    if (!t3) return;
    const m = t3.map, flat = ui.style === "crestas" && !ui.d3;
    if (flat) { m.dragRotate.disable(); m.touchZoomRotate.disableRotation(); m.touchPitch.disable(); if (m.getPitch() || m.getBearing()) m.jumpTo({ pitch: 0, bearing: 0 }); }
    else { m.dragRotate.enable(); m.touchZoomRotate.enableRotation(); m.touchPitch.enable(); }
  };
  const renderStyle = () => {
    wx.dataset.sty = ui.style; wx.dataset.d3 = ui.d3 ? "on" : "off"; wx.dataset.left = ui.left ? "on" : "off"; wx.dataset.right = ui.right && !ui.land ? "on" : "off";
    $("sty-l").textContent = styles.find(([k]) => k === ui.style)?.[1] ?? "";
    wx.querySelectorAll<HTMLButtonElement>("[data-cam]").forEach((b) => { const on = (b.dataset.cam === "3d") === ui.d3; b.classList.toggle("on", on); b.setAttribute("aria-checked", String(on)); });
    wx.querySelectorAll<HTMLButtonElement>("[data-fold]").forEach((b) => {
      const open = ui[b.dataset.fold as "left" | "right"], t = open ? LL("Ocultar panel", "Hide panel") : LL("Mostrar panel", "Show panel");
      b.setAttribute("aria-expanded", String(open)); b.setAttribute("aria-label", t); b.title = t;
    });
    wx.querySelectorAll<HTMLButtonElement>("[data-show]").forEach((b) => { const on = b.dataset.show === ui.show; b.classList.toggle("on", on); b.setAttribute("aria-checked", String(on)); });
  };

  // ── Qué cambia con cada acción ──
  const renderPanels = () => { renderHead(); renderQuestions(); renderAnswer(); renderSeries(); renderRank(); };
  const pickRegion = (reg: string) => {
    sel.reg = reg;
    stamp(reg === "DO" ? LL("País", "Country") : d.regName(reg));
    t3?.selectProvince(reg === "DO" ? null : d.isoToShape[reg] ?? null);
    frame();
    renderPanels();
    paintRidge();
  };
  const setInd = (ind: string) => {
    sel.ind = ind; sel.per = d.perFor(ind, sel.per); pick[questionOf(ind).id] = ind;
    stamp(chip(ind));
    tl.setYears(years()); renderPanels(); renderMap();
  };
  wx.addEventListener("click", (e) => {
    const el = e.target as Element;
    if (el.closest("[data-reg-all]")) { pickRegion("DO"); return; }
    // Ciclones: una pregunta del panel; el mapa de tormentas cubre el de tendencias y el panel explica cómo leerlo
    if (el.closest("[data-act-audit]")) { openAuditAt(sel.reg); location.hash = "#auditoria"; return; }
    // Preparar: el tablero de municipios cubre el mapa; el panel sigue a la izquierda
    if (el.closest("[data-prepq]")) { if (prepOff) { prepOff(); renderAnswer(); } else prepStart(); return; }
    if (el.closest("[data-cyq]")) { if (cyApi) { cyOff?.(); renderAnswer(); } else cyStart(); return; }
    const cyy = el.closest<HTMLElement>("[data-cy-yuna]");
    if (cyy && cyApi) { cyApi.setPlace(cyy.dataset.cyYuna!); return; }
    // El veredicto: una ventana con el porqué, las dos fuentes y el salto a la Auditoría del mismo lugar
    const vdb = el.closest<HTMLElement>("[data-vd]");
    if (vdb) {
      const vv = verdict(d, sel, sel.ind), cls = d.row(sel)?.clase ?? "", desc = d.V.clases[cls]?.descripcion ?? "";
      const rowsP = d.prods.map((p) => { const t = d.tr(sel, p); if (!t) return ""; const sig = d.isSig(t, sel.reg);
        return `<li><b style="color:${p === "IMERG" ? "#ffffff" : "#8fd3ff"}">${p}</b><span>${esc(`${t.pendiente_pct_decada > 0 ? "+" : ""}${num(t.pendiente_pct_decada, 0)} % ${LL("por década", "per decade")}`)}</span><em class="${sig ? "s" : ""}">${esc(sig ? LL("claro", "clear") : LL("incierto", "uncertain"))} · p ${t.p < 0.001 ? "&lt; 0,001" : esc(num(t.p, 3))}</em></li>`; }).join("");
      const place = regName();
      openPop(vdb, `<p class="pop-k">${esc(`${chip(sel.ind)} · ${place}`)}</p>
        <h3 class="pop-h" style="color:${vv.color}">${esc(vv.short)}</h3>
        ${desc ? `<p class="pop-s">${esc(desc)}</p>` : ""}
        <ul class="pop-l">${rowsP}</ul>
        <button class="pop-go" data-act="audit"><span>${esc(LL(`¿Y en la sequía? Auditoría de ${place}`, `And in drought? ${place} audit`))}</span>${CHEV}</button>
        <button class="pop-go alt" data-act="method"><span>${esc(LL("Cómo se decide el veredicto", "How the verdict is decided"))}</span>${CHEV}</button>`,
        (act) => { if (act === "audit") { openAuditAt(sel.reg); location.hash = "#auditoria"; } else if (act === "method") location.hash = "#metodo"; }, vv.short);
      return;
    }
    // Menús: cada opción dice qué es y, cuando aplica, su veredicto para la medida elegida
    const rb = el.closest<HTMLElement>("#r-btn");
    if (rb) {
      const opt = (id: string, label: string) => { const v = verdict(d, { ...sel, reg: id }, sel.ind); return { value: id, label, hint: v.short, color: v.color, hollow: !v.strong }; };
      openMenu(rb, [opt("DO", LL("Toda la República Dominicana", "Whole Dominican Republic")), ...d.provs.map((r) => opt(r.id, r.nombre))], sel.reg, pickRegion,
        ui.land ? LL("Elige un lugar", "Choose a place") : LL(`Elige un lugar · veredicto de «${chip(sel.ind)}»`, `Choose a place · verdict for "${chip(sel.ind)}"`));
      return;
    }
    const mb = el.closest<HTMLElement>("#m-btn");
    if (mb) {
      openMenu(mb, questionOf(sel.ind).vars.map((id) => { const v = verdict(d, sel, id); return { value: id, label: shortName(id), hint: `${v.short} · ${d.vm(id).descripcion}`, color: v.color, hollow: !v.strong }; }),
        sel.ind, setInd, LL("Cómo medirlo", "How to measure it"));
      return;
    }
    const sb = el.closest<HTMLElement>("#sty-btn");
    if (sb) {
      const hint: Record<Style, string> = {
        calor: LL("Campo de color suave: el color es el cambio", "Smooth colour field: the colour is the change"),
        crestas: LL("Relieve en perfiles; el color es el dato", "Relief in profiles; the colour is the data"),
        oscuro: LL("Mapa oscuro con las celdas de color", "Dark map with coloured cells"),
        plano: LL("Imagen de satélite con las celdas de color", "Satellite image with coloured cells"),
      };
      openMenu(sb, [
        ...styles.map(([k, l]) => ({ value: k, label: l, hint: hint[k] })),
        { value: "ciclones", label: LL("Huracanes", "Hurricanes"), hint: LL("73 tormentas 2001–2024: trayectoria, aviso oficial del NHC, viento, lluvia y satélite NASA", "73 storms 2001–2024: track, official NHC advisory, wind, NASA rain and satellite") },
      ], cyApi ? "ciclones" : ui.style, (v) => {
        if (v === "ciclones") { if (!cyApi) cyStart(); $("sty-l").textContent = LL("Huracanes", "Hurricanes"); return; }
        if (cyApi) { cyOff?.(); renderAnswer(); }
        ui.style = v as Style; renderStyle(); applyView(false);
      }, LL("Cómo se dibuja el mapa", "How the map is drawn"));
      return;
    }
    const lq = el.closest<HTMLElement>("[data-landq]");
    if (lq) {
      if (cyApi) cyOff?.();
      if (prepOff) prepOff();
      if (ui.land !== lq.dataset.landq) { ui.land = lq.dataset.landq as LandQ; ui.year = null; ui.landSite = ""; renderStyle(); renderPanels(); renderMap(); frameSites(); $("ans").scrollIntoView({ block: "start", behavior: RM() ? "auto" : "smooth" }); }
      return;
    }
    const lv = el.closest<HTMLElement>("[data-landvar]");
    if (lv) { ui.landVar = lv.dataset.landvar!; renderAnswer(); renderMap(); return; }
    const st = el.closest<HTMLElement>("[data-site]");
    if (st) { ui.landSite = ui.landSite === st.dataset.site ? "" : st.dataset.site!; renderAnswer(); renderMap(); return; }
    const q = el.closest<HTMLElement>("[data-q]");
    if (q) {
      if (prepOff) { prepOff(); if (questionOf(sel.ind).id === q.dataset.q && !ui.land) return; }
      if (cyApi) { cyOff?.(); if (questionOf(sel.ind).id === q.dataset.q && !ui.land) { renderAnswer(); return; } }
      const back = !!ui.land;
      if (back) { ui.land = ""; renderStyle(); }
      if (questionOf(sel.ind).id !== q.dataset.q) setInd(pick[q.dataset.q!]);
      else if (back) { renderPanels(); renderMap(); frame(); }
      return;
    }
    const mi = el.closest<HTMLElement>("[data-ind]");
    if (mi) {
      if (mi.dataset.ind !== sel.ind) setInd(mi.dataset.ind!);
      return;
    }
    if (el.closest("[data-go13]")) { const h = document.getElementById("s13-h"); h?.scrollIntoView({ behavior: RM() ? "auto" : "smooth", block: "center" }); h?.focus({ preventScroll: true }); return; }
    const fx = el.closest<HTMLButtonElement>("[data-fix]");
    if (fx) { const on = fx.dataset.fix === "1"; if (on !== d.fix) { d.fix = on; stamp(on ? LL("Ajuste", "Adjusted") : LL("Publicado", "Published")); renderAnswer(); renderMap(); } return; }
    if (el.closest("[data-fig13]")) {
      const lb = $<HTMLDialogElement>("s13-lb");
      lb.querySelectorAll<HTMLImageElement>("img[data-src]").forEach((im) => { if (!im.getAttribute("src")) im.src = im.dataset.src!; });
      lb.showModal(); return;
    }
    if (el.closest(".s13-x") || el.id === "s13-lb") { $<HTMLDialogElement>("s13-lb").close(); return; }
    const cam = el.closest<HTMLButtonElement>("[data-cam]");
    if (cam) { const d3 = cam.dataset.cam === "3d" ? (layout === "phone" ? !ui.d3 : true) : false; if (d3 !== ui.d3) { ui.d3 = d3; renderStyle(); applyView(true); } return; }
    const fo = el.closest<HTMLButtonElement>("[data-fold]");
    if (fo) { const side = fo.dataset.fold as "left" | "right"; ui[side] = !ui[side]; renderStyle(); return; }
    const per = el.closest<HTMLButtonElement>("[data-per]");
    if (per && !per.disabled) { sel.per = per.dataset.per!; stamp(LL(...SEASON[sel.per])); tl.setYears(years()); renderPanels(); renderMap(); return; }
    const src = el.closest<HTMLButtonElement>("[data-src]");
    if (src && !src.disabled) { sel.src = src.dataset.src!; renderPanels(); renderMap(); return; }
    const show = el.closest<HTMLButtonElement>("[data-show]");
    if (show) {
      ui.show = show.dataset.show!;
      if (ui.show !== "acuerdo") sel.src = ui.show;
      renderStyle(); renderPanels(); renderMap(); return;
    }
    const fr = el.closest<SVGGElement>(".fr");
    if (fr) pickRegion(fr.dataset.reg!);
  });
  wx.addEventListener("keydown", (e) => {
    const fr = (e.target as Element).closest<SVGGElement>(".fr");
    if (fr && e.key === "Enter") pickRegion(fr.dataset.reg!);
  });

  wx.querySelector(".wx-main")!.addEventListener("transitionend", (e) => { if ((e as TransitionEvent).propertyName === "grid-template-columns") { t3?.map.resize(); t3?.setFitPadding(fitPad()); } });

  // ── Línea de tiempo ──
  const tl = timeline($("wx-bar"), (i) => { ui.year = i; renderMap(); renderSeries(); });
  tl.setYears(years());
  if (ui.year !== null) tl.pick(ui.year);

  // ── Hoja inferior en el teléfono ──
  if (layout === "phone") {
    const sheet = bottomSheet($("wx-left"), [$("wx-grab"), $("wx-peek")], (s) => { wx.dataset.sheet = s; });
    wx.dataset.sheet = sheet.state;
  }

  // ── Lo que dice una celda (mapa y crestas) ──
  const lineFor = (k: number, iso: string | null | undefined) => {
    if (ui.year === null && ui.show === "acuerdo") {
      const cl = d.cellClass(sel), code = k >= 0 && cl ? cl[k] : null;
      if (code === null || code === undefined || !d.R.incluida[k]) return "";
      const name = (d.R.clases_codigo ?? [])[code];
      return `<b>${esc(clsName(name))}</b> · ${d.prods.map((p) => { const v = d.cells(sel, p)?.pendiente_decada[k]; return `${p} ${v === null || v === undefined ? "—" : sgn(v)}`; }).join(" · ")}`;
    }
    if (ui.year === null) {
      const lay = d.cells(sel), v = lay && k >= 0 && d.R.incluida[k] ? lay.pendiente_decada[k] : null;
      return v !== null && v !== undefined && lay ? `<b class="num">${sgn(v)}</b> ${esc(vm().unidad_tendencia)} · ${esc((lay.q[k] ?? 1) <= d.V.umbral_significancia.q_fdr ? LL("cambio claro", "clear change") : LL("no se distingue del azar", "indistinguishable from chance"))}` : "";
    }
    const s = iso ? d.series(sel, sel.src, iso) : null, v = s?.[ui.year];
    return v !== null && v !== undefined ? `<b class="num">${num(v)}</b> ${esc(vm().unidad)} ${LL("en", "in")} ${years()[ui.year]}` : "";
  };
  const showTip = (name: string, line: string, x: number, y: number) => {
    tip.innerHTML = `<p class="tt-n">${esc(name)}</p>${line ? `<p>${line}</p>` : ""}`;
    tip.hidden = false;
    tip.style.left = `${Math.min(innerWidth - tip.offsetWidth - 12, Math.max(12, x - tip.offsetWidth / 2))}px`;
    tip.style.top = `${y - tip.offsetHeight - 14}px`;
  };

  // ── Las crestas ──
  if (d.rel) {
    rg = ridges(wx.querySelector<HTMLElement>(".wx-mapcol")!, d.rel, d.R, {
      rivers: () => rios,
      color: (k) => ridgeColor(k),
      dim: (k) => (sel.reg === "DO" ? null : cellProv[k] !== sel.reg),
      pad: () => (layout === "phone" ? { top: 62, bottom: PEEK + 110, left: 10, right: 10 } : { ...fitPad(), top: 70 }),
      labels: { yuna: LL("Cuenca del Yuna", "Yuna basin"), hatillo: LL("Presa de Hatillo", "Hatillo dam"), scale: LL("1000 m (×11)", "1,000 m (×11)"), credit: LL("Relieve: Copernicus GLO-90 · ríos: OpenStreetMap · color: celdas de 0,1° del mapa", "Relief: Copernicus GLO-90 · rivers: OpenStreetMap · colour: the map's 0.1° cells") },
      proj: () => (t3 ? (lon, lat) => t3!.map.project([lon, lat]) : null),
    });
    const mineRg = rg;
    cleanup.push(() => mineRg.destroy());
    rg.show(ui.style === "crestas" && !ui.d3);
  }

  // ── Los lugares de la vegetación (encima de las crestas) ──
  sites = land ? sitesLayer(wx.querySelector<HTMLElement>(".wx-mapcol")!, () => (t3 ? (lon, lat) => t3!.map.project([lon, lat]) : null)) : null;
  if (sites) { const mineS = sites; cleanup.push(() => mineS.destroy()); }
  const frameSites = () => {
    if (!t3 || !land) return;
    // los lugares están repartidos por el país: se encuadra la isla entera, como en el resto de preguntas
    frame();
  };

  // ── Arranque ──
  if (!ui.trail.length) stamp(chip(sel.ind));
  t3 = terrain3d($("map"), {
    zones: [], sites: [], onZone: () => {}, onSite: () => {}, cellLabel: () => "", siteAction: "",
    provinces: (d.fc ?? undefined) as never,
    onProvince: (shape) => { const iso = d.shapeToIso[shape]; if (iso) pickRegion(iso === sel.reg ? "DO" : iso); },
    wheel: true,
  });
  const mine = t3;
  renderStyle(); renderPanels(); paintRidge(false);
  const tour = () => {
    const ys = d.rel?.yuna ?? [];
    const yb: [[number, number], [number, number]] | null = ys.length ? [[Math.min(...ys.map((p) => p[0])), Math.min(...ys.map((p) => p[1]))], [Math.max(...ys.map((p) => p[0])), Math.max(...ys.map((p) => p[1]))]] : null;
    let pins: maplibregl.Marker[] = [];
    const rivers = (names: string[] | null) => { try { riv(names); } catch { /* el mapa ya no existe */ } };
    const riv = (names: string[] | null) => {
      const m = t3?.map; if (!m) return;
      pins.forEach((p) => p.remove()); pins = [];
      const fc = { type: "FeatureCollection" as const, features: (names ? (rios ?? []).filter((r) => names.includes(r.name)) : []).map((r) => ({ type: "Feature" as const, properties: {}, geometry: { type: "MultiLineString" as const, coordinates: r.parts } })) };
      const src = m.getSource("tour-rios") as maplibregl.GeoJSONSource | undefined;
      if (src) src.setData(fc);
      else { m.addSource("tour-rios", { type: "geojson", data: fc }); m.addLayer({ id: "tour-rios-halo", type: "line", source: "tour-rios", layout: { "line-cap": "round", "line-join": "round" }, paint: { "line-color": "#64d2ff", "line-width": 14, "line-opacity": 0.28 } }); m.addLayer({ id: "tour-rios", type: "line", source: "tour-rios", layout: { "line-cap": "round", "line-join": "round" }, paint: { "line-color": "#9fe4ff", "line-width": 4 } }); }
      if (!names) return;
      const pin = (txt: string, lon: number, lat: number, kind = "") => { const el = document.createElement("div"); el.className = `tour-pin ${kind}`; el.textContent = txt; pins.push(new maplibregl.Marker({ element: el, anchor: kind === "pueblo" ? "top" : "bottom", offset: [0, kind === "pueblo" ? 6 : -6] }).setLngLat([lon, lat]).addTo(m)); };
      // Cada río se rotula en el tramo más alejado de los otros rótulos, para que ninguno tape a otro
      const used: [number, number][] = [[-69.908, 19.176]];
      if (d.rel?.hatillo) used.push([d.rel.hatillo.lon, d.rel.hatillo.lat]);
      for (const r of (rios ?? []).filter((x) => names.includes(x.name))) {
        const part = r.parts.reduce((a, b) => (b.length > a.length ? b : a), r.parts[0]);
        const cand = [0.2, 0.35, 0.5, 0.65, 0.8].map((f) => part[Math.floor(part.length * f)]);
        const far = (q: number[]) => Math.min(...used.map((u) => Math.hypot(q[0] - u[0], q[1] - u[1])));
        const [lo, la] = cand.reduce((a, b) => (far(b) > far(a) ? b : a));
        used.push([lo, la]); pin(r.name, lo, la, "rio");
      }
      pin("Villa Riva", -69.908, 19.176, "pueblo");
      if (d.rel?.hatillo) pin(LL("Presa de Hatillo", "Hatillo dam"), d.rel.hatillo.lon, d.rel.hatillo.lat, "presa");
    };
    const pad = () => { const L = document.getElementById("wx-left")?.getBoundingClientRect(), R = document.getElementById("wx-right")?.getBoundingClientRect(); return { left: (L && L.width ? L.right : 0) + 40, right: (R && R.width ? innerWidth - R.left : 0) + 40, top: 90, bottom: 230 }; };
    startTour({ map: () => (t3 ? t3.map as never : null), yuna: yb, hatillo: d.rel?.hatillo ? [d.rel.hatillo.lon, d.rel.hatillo.lat] : null, pad, rivers, reset: () => { if (sel.reg !== "DO") pickRegion("DO"); } });
  };
  $("tour-go").addEventListener("click", tour);
  mine.ready.then(() => {
    if (t3 !== mine) return;
    if (autoTour.on) { autoTour.on = false; setTimeout(tour, 1200); }
    mine.setFitPadding(fitPad());
    mine.setView(base(), ui.d3, exag());
    renderMap(false);
    if (sel.reg !== "DO") mine.selectProvince(d.isoToShape[sel.reg] ?? null);
    if (ui.land) frameSites(); else frame(true);
    const map = mine.map;
    if (d.fc && !map.getSource("medido")) {
      const holes: number[][][] = [];
      for (const f of d.fc.features) { const g = f.geometry; const polys = g.type === "Polygon" ? [g.coordinates] : g.coordinates; for (const pl of polys) holes.push(pl[0]); }
      map.addSource("medido", { type: "geojson", data: { type: "Feature", properties: {}, geometry: { type: "Polygon", coordinates: [[[-180, -85], [180, -85], [180, 85], [-180, 85], [-180, -85]], ...holes] } } });
      map.addLayer({ id: "fuera", type: "fill", source: "medido", paint: { "fill-color": "#050607", "fill-opacity": 0.66 } });
      map.addSource("borde", { type: "geojson", data: { type: "FeatureCollection", features: holes.map((r) => ({ type: "Feature" as const, properties: {}, geometry: { type: "LineString" as const, coordinates: r } })) } });
      map.addLayer({ id: "borde", type: "line", source: "borde", paint: { "line-color": "#ffffff", "line-opacity": ui.style === "calor" && !ui.land ? 0.16 : 0.5, "line-width": 1.3 } });
    }
    lockCam();
    map.on("move", () => { rg?.reframe(); sites?.place(); });
    rg?.reframe();
    map.on("mousemove", (e) => {
      const r = map.getCanvas().getBoundingClientRect();
      if (ui.style === "crestas" && !ui.d3 && rg) {
        const k = rg.cellAtPoint(e.point.x, e.point.y), iso = k >= 0 ? cellProv[k] : undefined;
        if (k < 0) { tip.hidden = true; return; }
        showTip(iso ? d.regName(iso) : LL("Celda de 11 km", "11 km cell"), lineFor(k, iso), r.left + e.point.x, r.top + e.point.y);
        return;
      }
      const f = map.queryRenderedFeatures(e.point, { layers: ["prov-fill"] })[0];
      if (!f) { tip.hidden = true; return; }
      showTip(String(f.properties?.shapeName ?? ""), lineFor(cellAt(d.R, e.lngLat.lng, e.lngLat.lat), d.shapeToIso[String(f.id)]), r.left + e.point.x, r.top + e.point.y);
    });
    map.getCanvas().addEventListener("mouseleave", () => { tip.hidden = true; });
  });
  cleanup.push(() => tl.stop());
}
