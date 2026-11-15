// P0 · Tendencias. Pantalla de trabajo (taste-skill, app · true-black-flat, semilla 280888739).
// Pregunta de la pantalla: «¿Están cambiando la sequía y la lluvia extrema en mi provincia, y qué tan seguros estamos?»
// Marco fijo en tres columnas que comparten bordes: preguntas y respuesta | mapa con su línea de tiempo | año a año y
// dónde poner atención. En tableta la tercera columna baja a la primera; en el teléfono la primera es una hoja inferior.
// Cara de la pantalla: el campo de tendencia sobre la isla con su punteado de significancia; y la escalera de evidencia.
import "./tendencias.css";
import type maplibregl from "maplibre-gl";
import { fmt } from "../text";
import { terrain3d } from "../terrain3d";
import { esc, LL, digits, loadTrends, num, sgn, type Sel, type Tr, type TrendData } from "./datos";
import { cellAt, classField, colorOf, rampCss, scaleMax, stipple, trendField } from "./campo";
import { capsule, forest, PROD_COLOR, seriesChart } from "./graficas";
import { cellProvinces, ridges, type RGBA } from "./crestas";
import { bottomSheet, PEEK } from "./hoja";
import { finding, QUESTIONS, questionOf, shortName, verdict } from "./preguntas";
import { timeline } from "./tiempo";

type Style = "crestas" | "3d" | "plano" | "oscuro";
type Layout = "wide" | "mid" | "phone";
const sel: Sel = { ind: "RACHAS15", per: "anual", reg: "DO", src: "IMERG" };
const pick: Record<string, string> = Object.fromEntries(QUESTIONS.map((q) => [q.id, q.vars[0]]));
const ui = { style: "crestas" as Style, year: null as number | null, show: "" as string };
let t3: ReturnType<typeof terrain3d> | null = null;
let cleanup: (() => void)[] = [];
const RD: [[number, number], [number, number]] = [[-72.05, 17.45], [-68.3, 19.98]];
const RM = () => matchMedia("(prefers-reduced-motion: reduce)").matches;
const TIERS = [["sabemos", "Lo que sabemos", "What we know"], ["creemos", "Lo que creemos saber", "What we think we know"], ["comprobar", "Lo que hay que comprobar", "What still needs checking"]] as const;
const CHEV = '<svg class="chev" viewBox="0 0 12 12" aria-hidden="true"><path d="M3 4.5l3 3 3-3" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>';
const MARK = '<svg viewBox="0 0 32 32" aria-hidden="true"><path d="M16 2.5l2.3 8.2 8.2 2.3-8.2 2.3L16 23.5l-2.3-8.2-8.2-2.3 8.2-2.3z" fill="#f2b33d"/><path d="M2.5 28.5c7.5-4.6 19.5-4.6 27 0" stroke="#fff" stroke-width="2.2" fill="none" stroke-linecap="round"/></svg>';
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
  const side = `
    <section class="blk blk-q" aria-labelledby="q-h">
      <h2 id="q-h">${esc(LL("Lo que quieres saber", "What you want to know"))}</h2>
      <div class="qs" id="qs" role="radiogroup"></div>
    </section>
    <section class="blk blk-ans" id="ans" aria-live="polite"></section>`;
  const extra = `
    <section class="blk blk-series" aria-labelledby="s-h">
      <div class="blk-h"><h2 id="s-h"></h2><span class="readout num" id="s-read"></span></div>
      <div id="s-plot"></div>
    </section>
    <section class="blk blk-rank" aria-labelledby="r-h">
      <div class="blk-h"><h2 id="r-h">${esc(LL("Dónde poner atención", "Where to look"))}</h2><span class="meta" id="r-meta"></span></div>
      <p class="hint">${esc(LL("Las 32 provincias, de más subida a más bajada. Barra: intervalo del 95 %. Punto relleno: cambio claro. Toca una para abrirla.", "All 32 provinces, largest rise to largest fall. Bar: 95 % interval. Filled dot: clear change. Tap one to open it."))}</p>
      <div class="rank-scroll" id="r-plot"></div>
    </section>
    <p class="fine">${esc(LL("Fuente: NASA GPM IMERG V07 (Huffman et al. 2023). Tendencia de Theil-Sen con Mann-Kendall de Hamed y Rao (1998); FDR de Benjamini-Hochberg. Describe 2001–2024; no atribuye causas.", "Source: NASA GPM IMERG V07 (Huffman et al. 2023). Theil-Sen trend with Hamed & Rao (1998) Mann-Kendall; Benjamini-Hochberg FDR. Describes 2001–2024; no attribution of causes."))}</p>`;

  view.innerHTML = `
  <div class="wx" id="wx" data-layout="${layout}" data-mode="trend" data-sty="${ui.style}">
    <header class="wx-top">
      <a class="wx-brand" href="#tendencias">${MARK}<b>Stellar Horizons</b><span>${esc(LL("Detective de tendencias", "Trend detective"))}</span></a>
      ${d.both ? "" : `<p class="wx-stamp" title="${esc(LL(`Corrida del ${updated}`, `Run of ${updated}`))}"><i></i>${esc(LL("Preliminar: solo IMERG, CHIRPS en camino", "Preliminary: IMERG only, CHIRPS on its way"))}</p>`}
    </header>
    <div class="wx-main">
      <aside class="wx-left" id="wx-left">
        ${layout === "phone" ? `<button class="wx-grab" id="wx-grab" aria-label="${esc(LL("Subir o bajar el panel", "Raise or lower the panel"))}"><i></i></button>` : ""}
        <section class="blk blk-reg" id="wx-peek">
          <div class="reg-row">
            <h1 id="wx-h1"></h1>
            <label class="reg-pick"><span>${esc(LL("Cambiar", "Change"))}</span><select id="r-sel" aria-label="${esc(LL("Región", "Region"))}">
              <option value="DO">${esc(LL("Toda la República Dominicana", "Whole Dominican Republic"))}</option>
              ${d.provs.map((r) => `<option value="${r.id}">${esc(r.nombre)}</option>`).join("")}
            </select>${CHEV}</label>
          </div>
          <p class="finding" id="finding"></p>
          ${d.both ? "" : `<p class="wx-stamp in-panel"><i></i>${esc(LL("Preliminar: solo IMERG, CHIRPS en camino", "Preliminary: IMERG only, CHIRPS on its way"))}</p>`}
          ${layout === "phone" ? `<p class="peek-ans" id="peek-ans"></p>` : ""}
        </section>
        <div class="wx-scroll">${side}${layout === "wide" ? "" : extra}</div>
      </aside>
      <section class="wx-mapcol" aria-label="${esc(LL("Mapa de tendencias", "Trend map"))}">
        <div id="map"></div>
        <div class="seg map-data" role="radiogroup" aria-label="${esc(LL("Qué muestra el mapa", "What the map shows"))}">
          ${d.both ? `<button data-show="acuerdo" role="radio">${esc(LL("¿Coinciden?", "Agree?"))}</button>` : ""}
          ${d.prods.map((p) => `<button data-show="${p}" role="radio">${p}</button>`).join("")}
        </div>
        <div class="seg map-sty" role="radiogroup" aria-label="${esc(LL("Estilo del mapa", "Map style"))}">
          ${([...(d.rel ? [["crestas", LL("Crestas", "Ridges")]] : []), ["oscuro", LL("Oscuro", "Dark")], ["3d", LL("Relieve", "Terrain")], ["plano", LL("Satélite", "Satellite")]] as [Style, string][]).map(([k, l]) => `<button data-sty="${k}" role="radio">${esc(l)}</button>`).join("")}
        </div>
        <div class="wx-time" id="wx-bar" data-mode="trend">
          <button class="wx-play"></button>
          <button class="wx-trendbtn" aria-pressed="true"></button>
          <div class="wx-track" role="slider" tabindex="0" aria-label="${esc(LL("Año", "Year"))}"></div>
          <div class="wx-legend" id="wx-legend"></div>
        </div>
      </section>
      ${layout === "wide" ? `<aside class="wx-right"><div class="wx-scroll">${extra}</div></aside>` : ""}
    </div>
    <div class="tr-tip" id="tr-tip" role="tooltip" hidden></div>
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

  // ── Preguntas (los objetivos) con su respuesta corta para la región ──
  const renderQuestions = () => {
    const q0 = questionOf(sel.ind);
    $("qs").innerHTML = QUESTIONS.map((q) => {
      const v = verdict(d, sel, pick[q.id]), on = q.id === q0.id;
      return `<button class="q ${on ? "on" : ""}" data-q="${q.id}" role="radio" aria-checked="${on}">
        <span class="q-t">${esc(LL(q.es, q.en))}</span>
        <span class="q-v ${v.strong ? "sig" : ""}" style="--c:${v.color}"><i></i>${esc(v.text)}</span>
      </button>`;
    }).join("");
  };

  // ── La respuesta: los dos testigos, la frase según su acuerdo, la escalera de evidencia y la prueba ──
  const countUp = (root: HTMLElement) => root.querySelectorAll<HTMLElement>("[data-count]").forEach((el) => {
    if (RM()) return;
    const to = Number(el.dataset.count), dg = Number(el.dataset.d), t0 = performance.now();
    const step = (now: number) => {
      const k = Math.min(1, (now - t0) / 700), v = to * (1 - Math.pow(1 - k, 3));
      el.textContent = (v > 0 ? "+" : "") + fmt(v, dg);
      if (k < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  });
  const renderAnswer = () => {
    const q = questionOf(sel.ind), v = vm(), ws = both(), row = d.row(sel), cls = row?.clase ?? "";
    const ctl = `
      <div class="ans-ctl">
        <label class="pick"><span>${esc(LL("Medido como", "Measured as"))}</span><select id="v-sel">${q.vars.map((id) => `<option value="${id}" ${id === sel.ind ? "selected" : ""}>${esc(shortName(id))}</option>`).join("")}</select>${CHEV}</label>
        <div class="seg seg-per" role="radiogroup" aria-label="${esc(LL("Época del año", "Season"))}">
          ${Object.keys(d.V.periodos).map((k) => `<button data-per="${k}" role="radio" aria-checked="${k === sel.per}" class="${k === sel.per ? "on" : ""}" title="${esc(v.periodos.includes(k) ? d.lab(d.V.periodos[k]) : LL("El SPI solo existe para el año completo", "SPI exists for the whole year only"))}" ${v.periodos.includes(k) ? "" : "disabled"}>${esc(LL(...SEASON[k]))}</button>`).join("")}
        </div>
      </div>`;
    if (!ws.length) { $("ans").innerHTML = `${ctl}<p class="empty">${esc(LL("No hay datos para esta combinación.", "No data for this combination."))}</p>`; return; }
    const ti = d.tier(sel), unit = v.unidad;
    const sigW = ws.filter((w) => d.isSig(w.t, sel.reg));
    const mdt = Math.max(...ws.map((w) => w.t.mdt));
    const s0 = ws[0].t, up = (sigW[0] ?? ws[0]).t.pendiente_decada > 0;
    const says = (lang: "es" | "en") => ws.map((w) => `${w.p} ${lang === "es" ? "dice" : "says"} ${sgn(w.t.pendiente_decada)}`).join(lang === "es" ? " y " : " and ");
    const sentence =
      cls === "robusta" ? LL(`Las dos fuentes coinciden: ${up ? "sube" : "baja"} entre ${ws.map((w) => num(Math.abs(w.t.pendiente_decada))).join(" y ")} ${unit} por década. Es lo que sabemos.`, `Both sources agree: ${up ? "rising" : "falling"} by ${ws.map((w) => num(Math.abs(w.t.pendiente_decada))).join(" to ")} ${unit} per decade. This is what we know.`)
      : cls === "consistente" ? LL(`Las dos apuntan a que ${up ? "sube" : "baja"}, pero solo ${sigW.map((w) => w.p).join(" y ")} lo confirma. Es probable, todavía no seguro.`, `Both point to it ${up ? "rising" : "falling"}, but only ${sigW.map((w) => w.p).join(" and ")} confirms it. Likely, not yet certain.`)
      : cls === "en disputa" ? LL(`${says("es")} ${unit} por década: direcciones opuestas y al menos una significativa. No se puede afirmar una tendencia; hay que investigar por qué discrepan.`, `${says("en")} ${unit} per decade: opposite directions, at least one significant. No trend can be claimed; why they disagree needs checking.`)
      : cls === "sin dato" ? LL("Faltan años en alguna serie, así que no se calcula la tendencia.", "Some years are missing, so no trend is computed.")
      : cls === "un solo producto" && sigW.length ? LL(`${s0.pendiente_decada > 0 ? "Sube" : "Baja"} ${num(Math.abs(s0.pendiente_decada))} ${unit} por década según ${ws[0].p}; falta la segunda fuente para confirmarlo.`, `${s0.pendiente_decada > 0 ? "Rising" : "Falling"} ${num(Math.abs(s0.pendiente_decada))} ${unit} per decade according to ${ws[0].p}; a second source is needed to confirm it.`)
      : LL(`Ninguna fuente detecta una tendencia. «Sin señal» no es «sin cambio»: con 24 años solo se vería un cambio mayor de ±${num(mdt)} ${unit} por década.`, `Neither source detects a trend. "No signal" is not "no change": with 24 years only a change beyond ±${num(mdt)} ${unit} per decade would show.`);
    const tierIdx = TIERS.findIndex(([k]) => k === ti.tier);
    const pFmt = (t: Tr) => (t.p < 0.001 ? `&lt;&#8239;${num(0.001, 3)}` : num(t.p, 3));
    $("ans").innerHTML = `${ctl}
      <div class="wits">${ws.map(({ p, t }) => { const sg = d.isSig(t, sel.reg); return `<div class="wit">
        <p class="wit-p"><i style="background:${PROD_COLOR[p]}"></i>${p}</p>
        <p class="wit-n"><b class="num" data-count="${t.pendiente_decada}" data-d="${digits(t.pendiente_decada)}">${sgn(t.pendiente_decada)}</b></p>
        <p class="wit-s">${esc(v.unidad_tendencia)} · ${esc(sg ? LL("significativa", "significant") : LL("no significativa", "not significant"))}</p>
      </div>`; }).join("")}</div>
      <p class="ans-sent">${esc(sentence)}</p>
      <div class="ladder" role="img" aria-label="${esc(`${LL("Evidencia", "Evidence")}: ${ti.label}`)}">${TIERS.map(([, es, en], i) => `<span class="${i === tierIdx ? "on" : ""}" style="--c:${ti.color}"><i></i>${esc(LL(es, en))}</span>`).join("")}</div>
      <p class="ans-why"><span class="chip" style="--c:${ti.color}">${esc(ti.label)}</span>${esc(ti.why)}</p>
      ${capsule(d, sel)}
      <table class="stats-t">
        <thead><tr><th></th><th class="num" title="${esc(LL("Mann-Kendall modificado de Hamed y Rao (1998)", "Hamed & Rao (1998) modified Mann-Kendall"))}">p</th><th class="num" title="${esc(LL("Benjamini-Hochberg entre las 32 provincias", "Benjamini-Hochberg across the 32 provinces"))}">q (FDR)</th><th class="num" title="${esc(LL("80 % de potencia, α = 0,05", "80 % power, α = 0.05"))}">${esc(LL("Mín. detect.", "Min. detect."))}</th><th class="num">${esc(LL("Media", "Mean"))}</th></tr></thead>
        <tbody>${ws.map(({ p, t }) => `<tr><th scope="row"><i style="background:${PROD_COLOR[p]}"></i>${p}</th><td class="num">${pFmt(t)}</td><td class="num">${t.q === null ? "—" : num(t.q, 3)}</td><td class="num">±${num(t.mdt)}</td><td class="num">${num(t.media)}</td></tr>`).join("")}</tbody>
      </table>
      <p class="rule">${esc(LL(`Significativa si ${d.sigRule(sel.reg)}.`, `Significant if ${d.sigRule(sel.reg)}.`))} ${ws.map((w) => `${w.p}: ${esc(d.V.productos[w.p]?.tipo_fuente ?? "")}`).join(" · ")}.</p>
      <details class="why"><summary>${esc(LL("Por qué importa y qué no dice", "Why it matters and what it does not say"))}</summary>
        <p>${esc(v.descripcion)} ${esc(v.por_que_importa)}</p>
        <p>${esc(LL("IMERG y CHIRPS no son testigos totalmente independientes: comparten infrarrojo geoestacionario y pluviómetros. Cuando discrepan no es que el satélite mienta: cada producto interpreta distinto la misma lluvia, y eso es lo que hay que investigar.", "IMERG and CHIRPS are not fully independent: they share geostationary infrared and rain gauges. When they disagree it is not that a satellite lies: each product reads the same rain differently, and that is what needs checking."))}</p>
        <p>${esc(d.V.nota_causalidad)}</p>
      </details>`;
    countUp($("ans"));
  };

  // ── Año a año y las 32 provincias ──
  const plotW = (el: HTMLElement) => Math.max(260, el.clientWidth);
  const showYear = (k: number | null) => {
    const r = $("s-read");
    const s = d.series(sel);
    if (k === null || !s) { r.textContent = ""; return; }
    const vals = s.filter((x): x is number => x !== null), mean = vals.reduce((a, b) => a + b, 0) / vals.length, v = s[k];
    r.textContent = v === null ? `${years()[k]} · —` : `${years()[k]} · ${num(v)} ${vm().unidad} · ${sgn(((v - mean) / mean) * 100, 0)} % ${LL("vs su media", "vs its mean")}`;
  };
  const renderSeries = () => {
    const el = $("s-plot");
    $("s-h").textContent = LL(`Año a año en ${regName()}`, `Year by year in ${regName()}`);
    el.innerHTML = seriesChart(d, sel, plotW(el), ui.year === null ? null : years()[ui.year], layout === "wide" ? 200 : 180)
      + `<p class="hint">${esc(LL("Toca un año para verlo en el mapa.", "Tap a year to see it on the map."))}</p>`;
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
    el.innerHTML = f.svg;
    const c = f.counts, n = (k: string) => c[k] ?? 0;
    $("r-meta").textContent = d.both
      ? LL(`${n("robusta")} robustas · ${n("consistente")} consistentes · ${n("en disputa")} en disputa`, `${n("robusta")} robust · ${n("consistente")} consistent · ${n("en disputa")} disputed`)
      : LL(`${n("un solo producto")} con una sola fuente`, `${n("un solo producto")} with one source`);
  };

  // ── El mapa ──
  const renderLegend = (max: number, pct: boolean) => {
    const v = vm(), up = v.tipo === "seco" ? LL("más seco", "drier") : LL("más lluvia", "more rain"), dn = v.tipo === "seco" ? LL("menos seco", "less dry") : LL("menos lluvia", "less rain");
    const f = (x: number) => (pct ? `${sgn(x, 0)} %` : sgn(x));
    $("wx-legend").innerHTML = `
      <div class="lg-w"><span>${esc(dn)}</span><span>${esc(pct ? LL("frente a su media", "vs its mean") : v.unidad_tendencia)}</span><span>${esc(up)}</span></div>
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
      $("wx-legend").innerHTML = `<p class="lg-w"><span>${esc(LL("Celdas de 11 km según el acuerdo de IMERG y CHIRPS", "11 km cells by IMERG–CHIRPS agreement"))}</span></p>
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
  const fitPad = () => (layout === "phone" ? { top: 70, bottom: PEEK + 120, left: 16, right: 16 } : { top: 64, bottom: layout === "mid" ? 150 : 110, left: 32, right: 32 });
  const frame = (fly = true) => {
    if (!t3) return;
    t3.setFitPadding(fitPad());
    const b = sel.reg === "DO" ? RD : d.bbox(sel.reg) ?? RD;
    t3.map.fitBounds(b, { padding: fitPad(), pitch: ui.style === "3d" ? 52 : 0, bearing: ui.style === "3d" ? -14 : 0, duration: fly && !RM() ? 1500 : 0, maxZoom: 10 });
  };
  const renderStyle = () => {
    wx.dataset.sty = ui.style;
    wx.querySelectorAll<HTMLButtonElement>("[data-sty]").forEach((b) => { const on = b.dataset.sty === ui.style; b.classList.toggle("on", on); b.setAttribute("aria-checked", String(on)); });
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
    if (q) { setInd(pick[q.dataset.q!]); return; }
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
    const sty = el.closest<HTMLButtonElement>("[data-sty]");
    if (sty) {
      ui.style = sty.dataset.sty as Style; renderStyle();
      rg?.show(ui.style === "crestas");
      if (ui.style !== "crestas") { tip.hidden = true; t3?.setMode(ui.style); frame(false); }
      return;
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
  });

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
      pad: () => (layout === "phone" ? { top: 100, bottom: PEEK + 110, left: 10, right: 10 } : { ...fitPad(), top: 70 }),
      labels: { yuna: LL("Cuenca del Yuna", "Yuna basin"), hatillo: LL("Presa de Hatillo", "Hatillo dam"), scale: LL("1000 m (×11)", "1,000 m (×11)"), credit: LL("Relieve: Copernicus GLO-90 · color: celdas de 0,1° del mapa", "Relief: Copernicus GLO-90 · colour: the map's 0.1° cells") },
      onHover: (k, x, y) => { const iso = cellProv[k]; showTip(iso ? d.regName(iso) : LL("Celda de 11 km", "11 km cell"), lineFor(k, iso), x, y); },
      onLeave: () => { tip.hidden = true; },
      onClick: (k) => { const iso = cellProv[k]; if (iso) pickRegion(iso === sel.reg ? "DO" : iso); },
    });
    const mineRg = rg;
    cleanup.push(() => mineRg.destroy());
    rg.show(ui.style === "crestas");
  }

  // ── Arranque ──
  t3 = terrain3d($("map"), {
    zones: [], sites: [], onZone: () => {}, onSite: () => {}, cellLabel: () => "", siteAction: "",
    provinces: (d.fc ?? undefined) as never,
    onProvince: (shape) => { const iso = d.shapeToIso[shape]; if (iso) pickRegion(iso); },
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
    map.on("mousemove", (e) => {
      const f = map.queryRenderedFeatures(e.point, { layers: ["prov-fill"] })[0];
      if (!f) { tip.hidden = true; return; }
      const r = map.getCanvas().getBoundingClientRect();
      showTip(String(f.properties?.shapeName ?? ""), lineFor(cellAt(d.R, e.lngLat.lng, e.lngLat.lat), d.shapeToIso[String(f.id)]), r.left + e.point.x, r.top + e.point.y);
    });
    map.getCanvas().addEventListener("mouseleave", () => { tip.hidden = true; });
  });
  cleanup.push(() => tl.stop());
}
