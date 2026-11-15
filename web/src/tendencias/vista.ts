// P0 · Tendencias. Pantalla de trabajo (taste-skill, app · true-black-flat, semilla 280888739).
// Pregunta de la pantalla: «¿Están cambiando la sequía y la lluvia extrema en mi provincia, y qué tan seguros estamos?»
// Marco fijo en tres columnas que comparten bordes: preguntas y respuesta | mapa con su línea de tiempo | año a año y
// dónde poner atención. En tableta la tercera columna baja a la primera; en el teléfono la primera es una hoja inferior.
// Cara de la pantalla: el campo de tendencia sobre la isla con su punteado de significancia; y la escalera de evidencia.
import "./tendencias.css";
import type maplibregl from "maplibre-gl";
import { terrain3d } from "../terrain3d";
import { esc, LL, loadTrends, num, sgn, type Sel, type Tr, type TrendData } from "./datos";
import { cellAt, classField, colorOf, rampCss, scaleMax, stipple, trendField } from "./campo";
import { capsule, forest, PROD_COLOR, seriesChart, WARN } from "./graficas";
import { cellProvinces, ridges, type RGBA } from "./crestas";
import { bottomSheet, PEEK } from "./hoja";
import { finding, QUESTIONS, questionOf, shortName, verdict } from "./preguntas";
import { timeline } from "./tiempo";

type Style = "crestas" | "3d" | "plano" | "oscuro";
type Layout = "wide" | "mid" | "phone";
const sel: Sel = { ind: "RACHAS15", per: "anual", reg: "DO", src: "IMERG" };
const pick: Record<string, string> = Object.fromEntries(QUESTIONS.map((q) => [q.id, q.vars[0]]));
const ui = { style: "crestas" as Style, year: null as number | null, show: "" as string, left: true, right: true };
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

export function destroyTrends() {
  cleanup.forEach((f) => f()); cleanup = [];
  t3?.destroy(); t3 = null;
  document.body.classList.remove("wx-on");
}

export async function viewTrends(view: HTMLElement) {
  destroyTrends();
  document.body.classList.add("wx-on");
  view.innerHTML = `<div class="wx"><p class="wx-loading">${esc(LL("Cargando tendencias…", "Loading trends…"))}</p></div>`;
  const d = await loadTrends();
  if (!d.prods.includes(sel.src)) sel.src = d.prods[0];
  if (!ui.show || (ui.show === "acuerdo" && !d.both)) ui.show = d.both ? "acuerdo" : sel.src;
  if (!d.rel && ui.style === "crestas") ui.style = "oscuro";
  render(view, d);
}

function render(view: HTMLElement, d: TrendData) {
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
  const styles: [Style, string][] = [...(d.rel ? [["crestas", LL("Crestas", "Ridges")] as [Style, string]] : []), ["oscuro", LL("Oscuro", "Dark")], ["3d", LL("Relieve", "Terrain")], ["plano", LL("Satélite", "Satellite")]];
  const fold = (side: "left" | "right") => layout === "phone" || (side === "right" && layout !== "wide") ? "" : `<button class="fold" data-fold="${side}" aria-controls="wx-${side}">${side === "left" ? PANEL_L : PANEL_R}</button>`;

  const r15 = d.s13?.recuentos.RACHAS15 ?? {};
  const nuevas = ["humeda_tardia", "humeda_temprana"].map((k) => `${LL(...SEASON[k])}: ${r15[k]?.en_disputa_sin_escalon ?? 0}`).join(" · ");
  const warn13 = d.s13 ? `<ul class="s13-w">
        <li>${esc(LL("Solo cambia el mapa. El medidor y la tabla siguen con lo publicado: el recálculo es por celda, no por provincia.", "Only the map changes. The gauge and table keep the published values: the recalculation is per cell, not per province."))}</li>
        <li>${esc(LL("La corrección no fecha el escalón: cualquier año de corte entre 2010 y 2017 da casi el mismo resultado. La fecha sale de la prueba de Pettitt; que fue IMERG, de los pluviómetros.", "The correction does not date the step: any cut year from 2010 to 2017 gives almost the same result. The date comes from the Pettitt test; that it was IMERG, from the gauges."))}</li>
        <li>${esc(LL("Parte del acuerdo es mecánico: se corrige usando CHIRPS como referencia.", "Part of the agreement is mechanical: the correction uses CHIRPS as reference."))}</li>
        <li>${esc(LL(`Aparecen disputas nuevas en las rachas de 15 días de las temporadas lluviosas (${nuevas} celdas).`, `New disputes appear in 15-day spells in the rainy seasons (${nuevas} cells).`))}</li>
        <li>${esc(LL("Las salidas publicadas no se tocaron; la variante está aparte.", "The published outputs were not touched; the variant is kept apart."))}</li>
      </ul>` : "";
  view.innerHTML = `
  <div class="wx" id="wx" data-layout="${layout}" data-mode="trend" data-sty="${ui.style}" data-left="${ui.left ? "on" : "off"}" data-right="${ui.right ? "on" : "off"}">
    <header class="wx-top">
      <a class="wx-brand" href="#tendencias">${MARK}<b>Stellar Horizons</b><span>${esc(LL("Detective de tendencias", "Trend detective"))}</span></a>
      ${d.both ? "" : `<p class="wx-stamp" title="${esc(LL(`Corrida del ${updated}`, `Run of ${updated}`))}"><i></i>${esc(LL("Preliminar: solo IMERG", "Preliminary: IMERG only"))}</p>`}
    </header>
    <div class="wx-main">
      <aside class="wx-left" id="wx-left">
        ${layout === "phone" ? `<button class="wx-grab" id="wx-grab" aria-label="${esc(LL("Subir o bajar el panel", "Raise or lower the panel"))}"><i></i></button>` : ""}
        <section class="blk-reg" id="wx-peek">
          <div class="reg-row">
            <h1 id="wx-h1"></h1>
            <label class="reg-pick"><span>${esc(LL("Cambiar", "Change"))}</span><select id="r-sel" aria-label="${esc(LL("Región", "Region"))}">
              <option value="DO">${esc(LL("Toda la República Dominicana", "Whole Dominican Republic"))}</option>
              ${d.provs.map((r) => `<option value="${r.id}">${esc(r.nombre)}</option>`).join("")}
            </select>${CHEV}</label>
          </div>
          <p class="finding" id="finding"></p>
          ${layout === "phone" ? `<p class="peek-ans" id="peek-ans"></p>` : ""}
        </section>
        <div class="wx-scroll">
          <section class="blk-q" aria-labelledby="q-h">
            <h2 id="q-h">${esc(LL("Lo que quieres saber", "What you want to know"))}</h2>
            <div class="qs" id="qs" role="radiogroup" aria-labelledby="q-h"></div>
          </section>
          <section class="blk-ans" aria-labelledby="ans-h">
            <h2 id="ans-h">${esc(LL("Qué dicen las dos fuentes", "What the two sources say"))}</h2>
            <div id="ans" aria-live="polite"></div>
          </section>
          <p class="fine">${esc(LL("IMERG y CHIRPS comparten insumos (infrarrojo y pluviómetros). Si discrepan no es que uno mienta: cada producto lee distinto la misma lluvia, y eso es lo que se investiga.", "IMERG and CHIRPS share inputs (infrared and gauges). If they disagree, neither is lying: each reads the same rain differently, and that is what gets investigated."))} ${esc(d.V.nota_causalidad)}</p>
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
          <label class="pick map-sty"><span>${esc(LL("Vista", "View"))}</span><select id="sty-sel" aria-label="${esc(LL("Vista del mapa", "Map view"))}">${styles.map(([k, l]) => `<option value="${k}">${esc(l)}</option>`).join("")}</select>${CHEV}</label>
          ${fold("right")}
        </div>
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
      <h2 id="s13-lb-h">${esc(LL("El escalón de 2013-10 en IMERG", "The 2013-10 step in IMERG"))}</h2>
      <p>${esc(LL("IMERG cambió en 2013 su forma de contar días de lluvia. Arriba, el escalón frente a CHIRPS y los 4 pluviómetros; abajo, los mapas antes y después de quitarlo y la sensibilidad al año de corte. Figuras del equipo, en inglés.", "IMERG changed in 2013 the way it counts rain days. Top, the step against CHIRPS and the 4 gauges; bottom, the maps before and after removing it and the sensitivity to the cut year. Team figures."))}</p>
      ${warn13}
      <img data-src="figuras/07_the_step_in_2013_dark.png" alt="${esc(LL("Diferencia mensual de días húmedos entre IMERG y CHIRPS con el punto de cambio en 2013-10, y los cuatro pluviómetros GHCN-D antes y después de esa fecha.", "Monthly wet-day difference between IMERG and CHIRPS with the change point in 2013-10, and the four GHCN-D gauges before and after that date."))}">
      <img data-src="figuras/08_after_the_correction_dark.png" alt="${esc(LL("Mapas de SDII y de rachas secas de 15 días antes y después de quitar el escalón, y número de celdas en disputa según el año de corte.", "SDII and 15-day dry-spell maps before and after removing the step, and disputed cells by cut year."))}">
    </dialog>
  </div>`;

  const $ = <T extends HTMLElement = HTMLElement>(id: string) => document.getElementById(id) as T;
  const wx = $("wx"), tip = $("tr-tip");
  const vm = () => d.vm(sel.ind);
  const years = () => d.years(sel);
  const regName = () => (sel.reg === "DO" ? LL("República Dominicana", "Dominican Republic") : d.regName(sel.reg));

  // ── Región y hallazgo ──
  const both = () => d.prods.map((p) => ({ p, t: d.tr(sel, p) })).filter((x): x is { p: string; t: Tr } => !!x.t);
  const renderHead = () => {
    $("wx-h1").textContent = regName();
    ($("r-sel") as HTMLSelectElement).value = sel.reg;
    $("finding").textContent = finding(d, sel, pick);
    if (layout === "phone") {
      const ti = d.tier(sel), q = questionOf(sel.ind);
      $("peek-ans").innerHTML = `<span class="pa-q">${esc(LL(q.es, q.en))}</span>${both().map(({ p, t }) => `<span class="pa-w"><i style="background:${PROD_COLOR[p]}"></i>${p} <b class="num">${sgn(t.pendiente_decada)}</b></span>`).join("")}<span class="chip" style="--c:${ti.color}">${esc(ti.label)}</span>`;
    }
  };

  // ── Preguntas: una lista de selección (un solo nivel); la respuesta de la elegida va siempre debajo ──
  const renderQuestions = () => {
    const q0 = questionOf(sel.ind);
    $("qs").innerHTML = QUESTIONS.map((q) => {
      const v = verdict(d, sel, pick[q.id]), on = q.id === q0.id;
      return `<button class="q-h ${on ? "on" : ""}" data-q="${q.id}" role="radio" aria-checked="${on}" title="${esc(v.text)}">
          <span class="q-t">${esc(LL(q.es, q.en))}</span>
          <span class="q-v ${v.strong ? "sig" : ""}" style="--c:${v.color}"><i></i>${esc(v.short)}</span>
        </button>`;
    }).join("");
  };

  // ── La respuesta: época, medidas con su veredicto, los dos testigos, la frase, la escalera y la prueba ──
  // ── Escalón de 2013-10: IMERG cambió su forma de contar días de lluvia; el mapa puede verse sin él ──
  const stepBlock = () => {
    const S = d.s13;
    if (!S || !d.stepped(sel.ind)) return "";
    const per = d.perFor(sel.ind, sel.per), rc = S.recuentos[sel.ind]?.[per], nac = sel.reg === "DO" ? S.nacional_IMERG[sel.ind]?.[per] : undefined;
    const pTxt = (p: number) => (p < 0.001 ? `p < ${num(0.001, 3)}` : `p ${num(p, 3)}`);
    const clsLab = (c: string) => (d.V.clases[c] ? d.lab(d.V.clases[c]) : c);
    const pair = (a: string, b: string, lab: string, tip = "") => `<div class="s13-n"${tip ? ` title="${esc(tip)}"` : ""}><p class="s13-l">${lab}</p><p class="s13-v"><span class="${d.fix ? "" : "on"}">${a}</span><i aria-hidden="true">→</i><span class="${d.fix ? "on" : ""}">${b}</span></p></div>`;
    const nacTip = nac?.publicado && nac.sin_escalon ? `${pTxt(nac.publicado.p)}, ${clsLab(nac.publicado.clase)} → ${pTxt(nac.sin_escalon.p)}, ${clsLab(nac.sin_escalon.clase)}` : "";
    return `<section class="s13" aria-labelledby="s13-h">
      <h3 class="s13-h" id="s13-h" tabindex="-1">${WARN}${esc(LL("Posible artefacto de medición: escalón 2013-10", "Possible measurement artefact: 2013-10 step"))}</h3>
      <p class="s13-t">${esc(LL("IMERG cambió en 2013 su forma de contar días de lluvia; los pluviómetros y CHIRPS, no.", "IMERG changed in 2013 the way it counts rain days; the gauges and CHIRPS did not."))}</p>
      <div class="seg s13-seg" role="radiogroup" aria-label="${esc(LL("Versión de IMERG en el mapa", "IMERG version on the map"))}">
        <button data-fix="0" role="radio" aria-checked="${!d.fix}" class="${d.fix ? "" : "on"}">${esc(LL("Publicado", "Published"))}</button>
        <button data-fix="1" role="radio" aria-checked="${d.fix}" class="${d.fix ? "on" : ""}">${esc(LL("Sin el escalón", "Without the step"))}</button>
      </div>
      <div class="s13-ns">
        ${rc ? pair(String(rc.en_disputa_publicado), String(rc.en_disputa_sin_escalon), esc(LL("Celdas en disputa", "Disputed cells"))) : ""}
        ${nac?.publicado && nac.sin_escalon ? pair(sgn(nac.publicado.pendiente_pct_decada, 1), sgn(nac.sin_escalon.pendiente_pct_decada, 1), esc(LL("IMERG nacional, %/década", "IMERG national, %/decade")), nacTip) : ""}
      </div>
      ${d.fix ? `<p class="s13-t">${esc(LL("Solo cambia el mapa. Parte del acuerdo es mecánico: se corrige con CHIRPS.", "Only the map changes. Part of the agreement is mechanical: it is corrected with CHIRPS."))}</p>` : ""}
      <button class="s13-fig" data-fig13>${esc(LL("Figura y advertencias", "Figure and caveats"))}</button>
    </section>`;
  };
  const renderAnswer = () => {
    const box = $("ans");
    const q = questionOf(sel.ind), v = vm(), ws = both(), cls = d.row(sel)?.clase ?? "";
    const ctl = `
      <div class="seg seg-per" role="radiogroup" aria-label="${esc(LL("Época del año", "Season"))}">
        ${Object.keys(d.V.periodos).map((k) => `<button data-per="${k}" role="radio" aria-checked="${k === sel.per}" class="${k === sel.per ? "on" : ""}" title="${esc(v.periodos.includes(k) ? d.lab(d.V.periodos[k]) : LL("El SPI solo existe para el año completo", "SPI exists for the whole year only"))}" ${v.periodos.includes(k) ? "" : "disabled"}>${esc(LL(...SEASON[k]))}</button>`).join("")}
      </div>
      <div class="ms" role="radiogroup" aria-label="${esc(LL("Medido como", "Measured as"))}">
        ${q.vars.map((id) => { const mv = verdict(d, sel, id), on = id === sel.ind; return `<button class="m ${on ? "on" : ""}" data-ind="${id}" role="radio" aria-checked="${on}" title="${esc(`${mv.text}. ${d.vm(id).descripcion}`)}"><span class="m-t">${esc(shortName(id))}</span><span class="q-v ${mv.strong ? "sig" : ""}" style="--c:${mv.color}"><i></i>${esc(mv.short)}</span></button>`; }).join("")}
      </div>`;
    if (!ws.length) { box.innerHTML = `${ctl}${stepBlock()}<p class="empty">${esc(LL("No hay datos para esta combinación.", "No data for this combination."))}</p>`; return; }
    const ti = d.tier(sel), unit = v.unidad;
    const sigW = ws.filter((w) => d.isSig(w.t, sel.reg));
    const mdt = Math.max(...ws.map((w) => w.t.mdt));
    const up = (sigW[0] ?? ws[0]).t.pendiente_decada > 0, dir = up ? LL("sube", "rising") : LL("baja", "falling");
    const sentence =
      cls === "robusta" ? LL(`Las dos coinciden: ${dir}.`, `Both agree: ${dir}.`)
      : cls === "consistente" ? LL(`Probablemente ${dir}: solo ${sigW.map((w) => w.p).join(" y ")} lo confirma.`, `Probably ${dir}: only ${sigW.map((w) => w.p).join(" and ")} confirms it.`)
      : cls === "en disputa" ? LL("Se contradicen: no se puede afirmar una tendencia.", "They contradict each other: no trend can be claimed.")
      : cls === "sin dato" ? LL("Faltan años: no se calcula la tendencia.", "Years missing: no trend computed.")
      : cls === "un solo producto" && sigW.length ? LL(`${up ? "Sube" : "Baja"} según ${ws[0].p}; falta la segunda fuente.`, `${up ? "Rising" : "Falling"} according to ${ws[0].p}; a second source is missing.`)
      : LL(`Ninguna detecta tendencia, que no es «sin cambio»: solo se vería uno de más de ±${num(mdt)} ${unit}/década.`, `Neither detects a trend, which is not "no change": only one beyond ±${num(mdt)} ${unit}/decade would show.`);
    const tierIdx = TIERS.findIndex(([k]) => k === ti.tier);
    const pFmt = (t: Tr) => (t.p < 0.001 ? `&lt;&#8239;${num(0.001, 3)}` : num(t.p, 3));
    box.innerHTML = `${ctl}
      ${capsule(d, sel)}
      <div class="ladder" role="img" aria-label="${esc(`${LL("Evidencia", "Evidence")}: ${ti.label}`)}">${TIERS.map(([, es, en], i) => `<span class="${i === tierIdx ? "on" : ""}" style="--c:${ti.color}" title="${esc(LL(es, en))}"><i></i>${i === tierIdx ? esc(LL(es, en)) : ""}</span>`).join("")}</div>
      <p class="ans-sent">${esc(sentence)}</p>
      ${stepBlock()}
      <table class="stats-t">
        <thead><tr><th></th><th class="num" title="${esc(LL("Mann-Kendall modificado de Hamed y Rao (1998)", "Hamed & Rao (1998) modified Mann-Kendall"))}">p</th><th class="num" title="${esc(LL("Benjamini-Hochberg entre las 32 provincias", "Benjamini-Hochberg across the 32 provinces"))}">q (FDR)</th><th class="num" title="${esc(LL("80 % de potencia, α = 0,05", "80 % power, α = 0.05"))}">${esc(LL("Mín. detect.", "Min. detect."))}</th><th class="num">${esc(LL("Media", "Mean"))}</th></tr></thead>
        <tbody>${ws.map(({ p, t }) => `<tr><th scope="row"><i style="background:${PROD_COLOR[p]}"></i>${p}</th><td class="num">${pFmt(t)}</td><td class="num">${t.q === null ? "—" : num(t.q, 3)}</td><td class="num">±${num(t.mdt)}</td><td class="num">${num(t.media)}</td></tr>`).join("")}</tbody>
      </table>
      <p class="rule">${esc(LL(`Significativa si ${d.sigRule(sel.reg)}.`, `Significant if ${d.sigRule(sel.reg)}.`))}</p>`;
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
    el.innerHTML = seriesChart(d, sel, plotW(el), ui.year === null ? null : years()[ui.year], layout === "wide" ? 190 : 170);
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
    el.innerHTML = `<p class="hint">${esc(LL("Punto lleno: cambio claro · barra: intervalo del 95 % · toca una provincia", "Filled dot: clear change · bar: 95 % interval · tap a province"))}</p>${f.svg}`;
  };
  (["s", "r"] as const).forEach((id) => document.getElementById(`${id}-sec`)?.addEventListener("toggle", () => (id === "s" ? renderSeries() : renderRank())));

  // ── El mapa ──
  const fixTag = () => (d.fix && d.stepped(sel.ind) && (ui.show === "acuerdo" || sel.src === "IMERG") ? ` · <b class="lg-fix">${esc(LL("IMERG sin el escalón de 2013", "IMERG without the 2013 step"))}</b>` : "");
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
    wx.dataset.mode = ui.year === null ? "trend" : "year";
    paintRidge(anim);
    if (!t3) return;
    const map = t3.map;
    if (ui.year === null && ui.show === "acuerdo") {
      const cl = d.cellClass(sel), codes = d.R.clases_codigo ?? [];
      if (!cl) return;
      const colors = codes.map((k) => d.V.clases[k]?.color ?? "#6b6f75");
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
        <p class="lg-cls">${codes.map((k, i) => `<span><i style="background:${colors[i]}"></i>${esc(d.V.clases[k] ? d.lab(d.V.clases[k]) : k)} <b class="num">${counts[i]}</b></span>`).join("")}</p>`;
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
  const cellProv = d.rel ? cellProvinces(d.R, d.fc) : [];
  let rg: ReturnType<typeof ridges> | null = null;
  const colorFor = (): ((k: number) => RGBA | null) => {
    if (ui.year === null && ui.show === "acuerdo") {
      const cl = d.cellClass(sel), codes = d.R.clases_codigo ?? [];
      if (!cl) return () => null;
      const rgb = codes.map((k) => hexRGB(d.V.clases[k]?.color ?? "#6b6f75"));
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
  const paintRidge = (anim = true) => { ridgeColor = colorFor(); if (ui.style === "crestas") rg?.draw(anim && !RM()); };
  const describeRidge = () => rg?.describe(`${LL("Perfiles de relieve de La Española apilados de norte a sur; cada tramo lleva el color de su celda en el mapa.", "Relief profiles of Hispaniola stacked north to south; each stretch takes its cell's map colour.")} ${$("wx-legend").textContent?.replace(/\s+/g, " ").trim() ?? ""}`);
  // El margen inferior sale de la altura real de la línea de tiempo (cambia cuando la leyenda baja a otra fila)
  const barH = () => document.getElementById("wx-bar")?.offsetHeight ?? 76;
  const fitPad = () => (layout === "phone" ? { top: 70, bottom: PEEK + 120, left: 16, right: 16 } : { top: 64, bottom: barH() + 34, left: 32, right: 32 });
  const frame = (fly = true) => {
    if (!t3) return;
    t3.setFitPadding(fitPad());
    const b = sel.reg === "DO" ? RD : d.bbox(sel.reg) ?? RD;
    t3.map.fitBounds(b, { padding: fitPad(), pitch: ui.style === "3d" ? 52 : 0, bearing: ui.style === "3d" ? -14 : 0, duration: fly && !RM() ? 1500 : 0, maxZoom: 10 });
  };
  // Con las crestas el mapa no gira ni se inclina: el relieve se dibuja de frente
  const lockCam = () => {
    if (!t3) return;
    const m = t3.map, flat = ui.style === "crestas";
    if (flat) { m.dragRotate.disable(); m.touchZoomRotate.disableRotation(); m.touchPitch.disable(); if (m.getPitch() || m.getBearing()) m.jumpTo({ pitch: 0, bearing: 0 }); }
    else { m.dragRotate.enable(); m.touchZoomRotate.enableRotation(); m.touchPitch.enable(); }
  };
  const renderStyle = () => {
    wx.dataset.sty = ui.style; wx.dataset.left = ui.left ? "on" : "off"; wx.dataset.right = ui.right ? "on" : "off";
    ($("sty-sel") as HTMLSelectElement).value = ui.style;
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
    t3?.selectProvince(reg === "DO" ? null : d.isoToShape[reg] ?? null);
    frame();
    renderPanels();
    paintRidge();
  };
  const setInd = (ind: string) => {
    sel.ind = ind; sel.per = d.perFor(ind, sel.per); pick[questionOf(ind).id] = ind;
    tl.setYears(years()); renderPanels(); renderMap();
  };
  wx.addEventListener("click", (e) => {
    const el = e.target as Element;
    const q = el.closest<HTMLElement>("[data-q]");
    if (q) {
      if (questionOf(sel.ind).id !== q.dataset.q) setInd(pick[q.dataset.q!]);
      return;
    }
    const mi = el.closest<HTMLElement>("[data-ind]");
    if (mi) {
      if (mi.dataset.ind !== sel.ind) setInd(mi.dataset.ind!);
      return;
    }
    if (el.closest("[data-go13]")) { const h = document.getElementById("s13-h"); h?.scrollIntoView({ behavior: RM() ? "auto" : "smooth", block: "center" }); h?.focus({ preventScroll: true }); return; }
    const fx = el.closest<HTMLButtonElement>("[data-fix]");
    if (fx) { const on = fx.dataset.fix === "1"; if (on !== d.fix) { d.fix = on; renderAnswer(); renderMap(); } return; }
    if (el.closest("[data-fig13]")) {
      const lb = $<HTMLDialogElement>("s13-lb");
      lb.querySelectorAll<HTMLImageElement>("img[data-src]").forEach((im) => { if (!im.getAttribute("src")) im.src = im.dataset.src!; });
      lb.showModal(); return;
    }
    if (el.closest(".s13-x") || el.id === "s13-lb") { $<HTMLDialogElement>("s13-lb").close(); return; }
    const fo = el.closest<HTMLButtonElement>("[data-fold]");
    if (fo) { const side = fo.dataset.fold as "left" | "right"; ui[side] = !ui[side]; renderStyle(); return; }
    const per = el.closest<HTMLButtonElement>("[data-per]");
    if (per && !per.disabled) { sel.per = per.dataset.per!; tl.setYears(years()); renderPanels(); renderMap(); return; }
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
  wx.addEventListener("change", (e) => {
    const t = e.target as HTMLSelectElement;
    if (t.id === "r-sel") pickRegion(t.value);
    else if (t.id === "v-sel") setInd(t.value);
    else if (t.id === "sty-sel") {
      ui.style = t.value as Style; renderStyle();
      rg?.show(ui.style === "crestas");
      lockCam();
      if (ui.style !== "crestas") { tip.hidden = true; t3?.setMode(ui.style); frame(false); }
    }
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
      return `<b>${esc(d.V.clases[name] ? d.lab(d.V.clases[name]) : name)}</b> · ${d.prods.map((p) => { const v = d.cells(sel, p)?.pendiente_decada[k]; return `${p} ${v === null || v === undefined ? "—" : sgn(v)}`; }).join(" · ")}`;
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
      color: (k) => ridgeColor(k),
      dim: (k) => (sel.reg === "DO" ? null : cellProv[k] !== sel.reg),
      pad: () => (layout === "phone" ? { top: 62, bottom: PEEK + 110, left: 10, right: 10 } : { ...fitPad(), top: 70 }),
      labels: { yuna: LL("Cuenca del Yuna", "Yuna basin"), hatillo: LL("Presa de Hatillo", "Hatillo dam"), scale: LL("1000 m (×11)", "1,000 m (×11)"), credit: LL("Relieve: Copernicus GLO-90 · color: celdas de 0,1° del mapa", "Relief: Copernicus GLO-90 · colour: the map's 0.1° cells") },
      proj: () => (t3 ? (lon, lat) => t3!.map.project([lon, lat]) : null),
    });
    const mineRg = rg;
    cleanup.push(() => mineRg.destroy());
    rg.show(ui.style === "crestas");
  }

  // ── Arranque ──
  t3 = terrain3d($("map"), {
    zones: [], sites: [], onZone: () => {}, onSite: () => {}, cellLabel: () => "", siteAction: "",
    provinces: (d.fc ?? undefined) as never,
    onProvince: (shape) => { const iso = d.shapeToIso[shape]; if (iso) pickRegion(iso === sel.reg ? "DO" : iso); },
    wheel: true,
  });
  const mine = t3;
  renderStyle(); renderPanels(); paintRidge(false);
  mine.ready.then(() => {
    if (t3 !== mine) return;
    mine.setFitPadding(fitPad());
    mine.setMode(ui.style === "crestas" ? "oscuro" : ui.style);
    renderMap(false);
    if (sel.reg !== "DO") mine.selectProvince(d.isoToShape[sel.reg] ?? null);
    frame(true);
    const map = mine.map;
    lockCam();
    map.on("move", () => rg?.reframe());
    rg?.reframe();
    map.on("mousemove", (e) => {
      const r = map.getCanvas().getBoundingClientRect();
      if (ui.style === "crestas" && rg) {
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
