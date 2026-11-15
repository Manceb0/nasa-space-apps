// P0 · Tendencias como una app de mapa (referencia: Windy): el mapa ocupa la pantalla y es la respuesta;
// las capas a la derecha, la línea de tiempo al pie y el detalle en un panel que en el teléfono es una hoja.
// Pregunta: ¿cambió esta variable en esta región entre 2001 y 2024, cuánto, con qué incertidumbre, y lo confirman dos fuentes?
import "./tendencias.css";
import type maplibregl from "maplibre-gl";
import { fmt } from "../text";
import { terrain3d } from "../terrain3d";
import { esc, LL, digits, loadTrends, num, sgn, type Sel, type TrendData } from "./datos";
import { cellAt, colorOf, rampCss, scaleMax, stipple, trendField } from "./campo";
import { capsule, forest, seriesChart } from "./graficas";
import { bottomSheet, isPhone, PEEK, type SheetState } from "./hoja";
import { timeline } from "./tiempo";

type Style = "3d" | "plano" | "oscuro";
type Tab = "res" | "serie" | "prov";
const sel: Sel = { ind: "RACHAS15", per: "anual", reg: "DO", src: "IMERG" };
const ui = { style: "oscuro" as Style, tab: "res" as Tab, year: null as number | null };
let t3: ReturnType<typeof terrain3d> | null = null;
let cleanup: (() => void)[] = [];
const RD: [[number, number], [number, number]] = [[-72.05, 17.45], [-68.3, 19.98]];
const RM = () => matchMedia("(prefers-reduced-motion: reduce)").matches;
const TIERS = [["sabemos", "Lo que sabemos", "What we know"], ["creemos", "Lo que creemos saber", "What we think we know"], ["comprobar", "Lo que hay que comprobar", "What still needs checking"]] as const;
const ICON = {
  layers: '<svg viewBox="0 0 20 20" aria-hidden="true"><path d="M10 3l7.5 4L10 11 2.5 7z" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/><path d="M2.5 10.5L10 14.5l7.5-4M2.5 13.8L10 17.8l7.5-4" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/></svg>',
  close: '<svg viewBox="0 0 20 20" aria-hidden="true"><path d="M5 5l10 10M15 5L5 15" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>',
  pin: '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M8 14s4.5-4.2 4.5-7.5a4.5 4.5 0 1 0-9 0C3.5 9.8 8 14 8 14z" fill="none" stroke="currentColor" stroke-width="1.4"/><circle cx="8" cy="6.5" r="1.6" fill="currentColor"/></svg>',
  chev: '<svg viewBox="0 0 12 12" aria-hidden="true"><path d="M3 4.5l3 3 3-3" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>',
};

export function destroyTrends() {
  cleanup.forEach((f) => f()); cleanup = [];
  t3?.destroy(); t3 = null;
  document.body.classList.remove("wx-on");
}

export async function viewTrends(view: HTMLElement) {
  destroyTrends();
  document.body.classList.add("wx-on");
  view.innerHTML = `<div class="wx"><div class="wx-map" id="map"></div><p class="wx-loading">${esc(LL("Cargando tendencias…", "Loading trends…"))}</p></div>`;
  const d = await loadTrends();
  if (!d.prods.includes(sel.src)) sel.src = d.prods[0];
  render(view, d);
}

function render(view: HTMLElement, d: TrendData) {
  const updated = new Date(d.V.generado_utc).toLocaleString(LL("es-DO", "en-US"), { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
  const groups = [["periodos_secos", "Periodos secos", "Dry spells"], ["sequia", "Sequía (SPI)", "Drought (SPI)"], ["lluvia", "Lluvia y extremos", "Rain and extremes"]] as const;
  view.innerHTML = `
  <div class="wx" id="wx" data-mode="trend">
    <div class="wx-map" id="map" aria-label="${esc(LL("Mapa de tendencias", "Trend map"))}"></div>

    <header class="wx-top">
      <p class="wx-crumb">${esc(LL("Detective de tendencias · 2001–2024", "Trend detective · 2001–2024"))}</p>
      <h1 id="wx-h1"></h1>
      <p class="wx-sub" id="wx-sub"></p>
      ${d.both ? "" : `<p class="wx-prelim" title="${esc(LL(`Corrida del ${updated}`, `Run of ${updated}`))}"><i></i>${esc(LL("Preliminar · solo IMERG · CHIRPS en camino", "Preliminary · IMERG only · CHIRPS on its way"))}</p>`}
    </header>
    <button class="wx-fab" id="wx-open" aria-controls="wx-rail" aria-expanded="false">${ICON.layers}<span>${esc(LL("Capas", "Layers"))}</span></button>

    <div class="wx-scrim" id="wx-scrim" hidden></div>
    <nav class="wx-rail" id="wx-rail" aria-label="${esc(LL("Variables", "Variables"))}">
      <div class="wx-rail-h"><b>${esc(LL("¿Qué quieres ver?", "What do you want to see?"))}</b><button class="wx-x" id="wx-close" aria-label="${esc(LL("Cerrar", "Close"))}">${ICON.close}</button></div>
      <div class="wx-rail-list" id="wx-list">
        ${groups.map(([g, es, en]) => `<p class="wx-g">${esc(LL(es, en))}</p>${d.V.variables.filter((v) => v.grupo === g).map((v) => `<button class="ly" data-ind="${v.id}"><i class="ly-dot"></i><span>${esc(d.lab(v))}</span><em></em></button>`).join("")}`).join("")}
      </div>
      <div class="wx-opts">
        <p class="wx-g">${esc(LL("Época del año", "Season"))}</p><div class="mini-seg" id="o-per"></div>
        <p class="wx-g">${esc(LL("Fuente", "Source"))}</p><div class="mini-seg" id="o-src">${["IMERG", "CHIRPS"].map((p) => `<button data-src="${p}" ${d.prods.includes(p) ? "" : `disabled title="${esc(LL("Llega en la próxima corrida", "Arrives in the next run"))}"`}>${p}${d.prods.includes(p) ? "" : `<small> · ${esc(LL("pronto", "soon"))}</small>`}</button>`).join("")}</div>
        <p class="wx-g">${esc(LL("Mapa", "Map"))}</p><div class="mini-seg" id="o-sty">${([["oscuro", LL("Oscuro", "Dark")], ["3d", LL("Relieve 3D", "3D terrain")], ["plano", LL("Satélite", "Satellite")]] as const).map(([k, l]) => `<button data-sty="${k}">${esc(l)}</button>`).join("")}</div>
      </div>
    </nav>

    <section class="wx-sheet" id="wx-sheet" aria-label="${esc(LL("Detalle", "Detail"))}">
      <button class="wx-grab" id="wx-grab" aria-label="${esc(LL("Mostrar u ocultar el detalle", "Show or hide the detail"))}"><i></i></button>
      <div class="wx-peek" id="wx-peek"></div>
      <div class="wx-tabs" role="tablist">
        ${([["res", "Resumen", "Summary"], ["serie", "Año a año", "Year by year"], ["prov", "Provincias", "Provinces"]] as const).map(([k, es, en]) => `<button role="tab" data-tab="${k}" aria-selected="${ui.tab === k}" class="${ui.tab === k ? "on" : ""}">${esc(LL(es, en))}</button>`).join("")}
      </div>
      <div class="wx-body" id="wx-body"></div>
    </section>

    <div class="wx-bar" id="wx-bar" data-mode="trend">
      <button class="wx-play" aria-label="${esc(LL("Reproducir año a año", "Play year by year"))}"></button>
      <button class="wx-trendbtn on" aria-pressed="true"></button>
      <div class="wx-track" role="slider" tabindex="0" aria-label="${esc(LL("Año", "Year"))}"></div>
      <div class="wx-legend" id="wx-legend"></div>
    </div>
    <div class="tr-tip" id="tr-tip" role="tooltip" hidden></div>
  </div>`;

  const $ = <T extends HTMLElement = HTMLElement>(id: string) => document.getElementById(id) as T;
  const wx = $("wx"), body = $("wx-body"), peek = $("wx-peek"), tip = $("tr-tip"), rail = $("wx-rail"), scrim = $("wx-scrim");
  const vm = () => d.vm(sel.ind);
  const years = () => d.years(sel);

  // ── Hoja / panel ──
  const fitPad = () => (isPhone()
    ? { top: 150, bottom: PEEK + 100, left: 16, right: 16 }
    : { top: 90, bottom: 120, left: 440, right: 290 });
  const sheet = bottomSheet($("wx-sheet"), [$("wx-grab"), peek], (s: SheetState) => { wx.dataset.sheet = s; if (s !== "peek") renderPane(); });

  // ── Capas (menú lateral; en el teléfono, un cajón) ──
  const openRail = (on: boolean) => {
    rail.classList.toggle("open", on); scrim.hidden = !on;
    $("wx-open").setAttribute("aria-expanded", String(on));
  };
  $("wx-open").addEventListener("click", () => openRail(true));
  $("wx-close").addEventListener("click", () => openRail(false));
  scrim.addEventListener("click", () => openRail(false));
  rail.querySelectorAll<HTMLButtonElement>(".ly").forEach((b) => b.addEventListener("click", () => {
    sel.ind = b.dataset.ind!; sel.per = d.perFor(sel.ind, sel.per);
    if (isPhone()) openRail(false);
    tl.setYears(years()); renderAll();
  }));
  $("o-src").querySelectorAll<HTMLButtonElement>("button").forEach((b) => b.addEventListener("click", () => { if (!b.disabled) { sel.src = b.dataset.src!; renderAll(); } }));
  $("o-sty").querySelectorAll<HTMLButtonElement>("button").forEach((b) => b.addEventListener("click", () => {
    ui.style = b.dataset.sty as Style; renderRail();
    if (t3) { t3.setMode(ui.style === "plano" ? "plano" : ui.style); frame(false); }
  }));

  const renderRail = () => {
    rail.querySelectorAll<HTMLButtonElement>(".ly").forEach((b) => {
      const s2 = { ...sel, ind: b.dataset.ind!, per: d.perFor(b.dataset.ind!, sel.per) };
      const t = d.tr(s2);
      const sig = t ? d.isSig(t, sel.reg) : false;
      const dry = t ? d.towardDry(s2.ind, t.pendiente_decada) : false;
      b.classList.toggle("on", b.dataset.ind === sel.ind);
      b.setAttribute("aria-current", String(b.dataset.ind === sel.ind));
      b.style.setProperty("--c", sig ? (dry ? "#ff9f0a" : "#0a84ff") : "transparent");
      b.classList.toggle("sig", sig);
      b.querySelector("em")!.textContent = sig ? (t!.pendiente_decada > 0 ? "▲" : "▼") : "";
      b.title = t ? `${sgn(t.pendiente_decada)} ${d.vm(s2.ind).unidad_tendencia}${sig ? ` · ${LL("significativa", "significant")}` : ""}` : "";
    });
    const short: Record<string, [string, string]> = { anual: ["Año", "Year"], seca: ["Seca", "Dry"], humeda_temprana: ["Lluvias 1", "Rains 1"], humeda_tardia: ["Lluvias 2", "Rains 2"] };
    $("o-per").innerHTML = Object.keys(d.V.periodos).map((k) => {
      const ok = vm().periodos.includes(k);
      return `<button data-per="${k}" class="${k === sel.per ? "on" : ""}" title="${esc(d.lab(d.V.periodos[k]))}" ${ok ? "" : "disabled"}>${esc(LL(...short[k]))}</button>`;
    }).join("");
    $("o-per").querySelectorAll<HTMLButtonElement>("button").forEach((b) => b.addEventListener("click", () => { sel.per = b.dataset.per!; tl.setYears(years()); renderAll(); }));
    $("o-src").querySelectorAll<HTMLButtonElement>("button").forEach((b) => b.classList.toggle("on", b.dataset.src === sel.src));
    $("o-sty").querySelectorAll<HTMLButtonElement>("button").forEach((b) => b.classList.toggle("on", b.dataset.sty === ui.style));
  };

  // ── Cabecera y tarjeta asomada ──
  const renderTop = () => {
    $("wx-h1").textContent = d.lab(vm());
    $("wx-sub").textContent = `${d.lab(d.V.periodos[sel.per])} · ${vm().descripcion}`;
  };
  const countUp = (root: HTMLElement) => root.querySelectorAll<HTMLElement>("[data-count]").forEach((el) => {
    if (RM()) return;
    const to = Number(el.dataset.count), dg = Number(el.dataset.d), plus = el.dataset.plus === "1", t0 = performance.now();
    const step = (now: number) => {
      const k = Math.min(1, (now - t0) / 850), v = to * (1 - Math.pow(1 - k, 3));
      el.textContent = (plus && v > 0 ? "+" : "") + fmt(v, dg);
      if (k < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  });
  const yearInfo = () => {
    const yi = ui.year, s = d.series(sel);
    if (yi === null || !s) return null;
    const vals = s.filter((x): x is number => x !== null);
    const mean = vals.reduce((a, b) => a + b, 0) / vals.length, v = s[yi];
    return { yr: years()[yi], v, mean, pct: v === null || !mean ? null : ((v - mean) / mean) * 100 };
  };
  const renderPeek = () => {
    const t = d.tr(sel), ti = d.tier(sel), v = vm(), yi = yearInfo();
    const opts = `<option value="DO">${esc(LL("Toda la República Dominicana", "Whole Dominican Republic"))}</option>${d.provs.map((r) => `<option value="${r.id}" ${r.id === sel.reg ? "selected" : ""}>${esc(r.nombre)}</option>`).join("")}`;
    let big = "", line = "";
    if (yi) {
      big = yi.v === null ? "—" : `<b class="num" data-count="${yi.v}" data-d="${digits(yi.v)}">${num(yi.v)}</b><span>${esc(v.unidad)} ${esc(LL(`en ${yi.yr}`, `in ${yi.yr}`))}</span>`;
      line = yi.pct === null ? "" : LL(`${sgn(yi.pct, 0)} % frente a su media 2001–2024 (${num(yi.mean)} ${v.unidad})`, `${sgn(yi.pct, 0)} % vs its 2001–2024 mean (${num(yi.mean)} ${v.unidad})`);
    } else if (t) {
      big = `<b class="num" data-count="${t.pendiente_decada}" data-d="${digits(t.pendiente_decada)}" data-plus="1">${sgn(t.pendiente_decada)}</b><span>${esc(v.unidad_tendencia)}</span>`;
      line = d.isSig(t, sel.reg) ? LL("Más de lo que el azar explicaría.", "More than chance would explain.")
        : t.detectable ? LL("Grande, pero no se distingue del azar.", "Large, but indistinguishable from chance.")
          : LL(`Sin señal: con 24 años solo se vería un cambio mayor de ±${num(t.mdt)}.`, `No signal: with 24 years only a change beyond ±${num(t.mdt)} would show.`);
    }
    peek.innerHTML = `
      <label class="pk-reg">${ICON.pin}<select id="pk-reg" aria-label="${esc(LL("Región", "Region"))}">${opts}</select>${ICON.chev}</label>
      <div class="pk-big">${big}</div>
      <p class="pk-line"><span class="chip" style="--c:${ti.color}">${esc(ti.label)}</span>${esc(line)}</p>`;
    ($("pk-reg") as HTMLSelectElement).value = sel.reg;
    $("pk-reg").addEventListener("change", (e) => pickRegion((e.target as HTMLSelectElement).value, true));
    countUp(peek);
  };

  // ── Pestañas ──
  body.addEventListener("click", (e) => {
    const g = (e.target as Element).closest<SVGGElement>(".fr");
    if (g) pickRegion(g.dataset.reg!, true);
  });
  body.addEventListener("keydown", (e) => {
    const g = (e.target as Element).closest<SVGGElement>(".fr");
    if (g && e.key === "Enter") pickRegion(g.dataset.reg!, true);
  });
  $("wx-sheet").querySelectorAll<HTMLButtonElement>("[data-tab]").forEach((b) => b.addEventListener("click", () => {
    ui.tab = b.dataset.tab as Tab;
    $("wx-sheet").querySelectorAll<HTMLButtonElement>("[data-tab]").forEach((x) => { const on = x === b; x.classList.toggle("on", on); x.setAttribute("aria-selected", String(on)); });
    if (sheet.state === "peek") sheet.set("half"); else renderPane();
  }));
  const paneW = () => Math.max(260, body.clientWidth - 32);
  const renderPane = () => {
    if (sheet.state === "peek" && isPhone()) return;
    const v = vm(), t = d.tr(sel);
    let html = "";
    if (ui.tab === "res") {
      if (!t) html = `<p class="meta">${esc(LL("Sin datos para esta combinación.", "No data for this combination."))}</p>`;
      else {
        const sig = d.isSig(t, sel.reg), ti = d.tier(sel), where = sel.reg === "DO" ? LL("En la República Dominicana", "In the Dominican Republic") : LL(`En ${d.regName(sel.reg)}`, `In ${d.regName(sel.reg)}`);
        const verb = t.pendiente_decada === 0 ? LL("no cambia", "does not change") : t.pendiente_decada > 0 ? LL("sube", "rises by") : LL("baja", "falls by");
        const sentence = sig
          ? LL(`${where}, «${d.lab(v)}» ${verb} ${num(Math.abs(t.pendiente_decada))} ${v.unidad} por década (${sgn(t.pendiente_pct_decada, 0)} % sobre su media de ${num(t.media)}).`, `${where}, "${d.lab(v)}" ${verb} ${num(Math.abs(t.pendiente_decada))} ${v.unidad} per decade (${sgn(t.pendiente_pct_decada, 0)} % of its mean of ${num(t.media)}).`)
          : t.detectable
            ? LL(`${where}, la tendencia (${sgn(t.pendiente_decada)} ${v.unidad} por década) es grande pero no significativa.`, `${where}, the trend (${sgn(t.pendiente_decada)} ${v.unidad} per decade) is large but not significant.`)
            : LL(`${where} no se detecta tendencia. «Sin señal» no es «sin cambio»: 24 años solo revelan cambios mayores de ${num(t.mdt)} ${v.unidad} por década.`, `${where} no trend is detected. "No signal" is not "no change": 24 years only reveal changes beyond ${num(t.mdt)} ${v.unidad} per decade.`);
        const tierIdx = TIERS.findIndex(([k]) => k === ti.tier);
        const crosses = t.ic95[0] <= 0 && t.ic95[1] >= 0;
        html = `
          <p class="tr-sentence">${esc(sentence)}</p>
          <div class="tr-ladder" role="img" aria-label="${esc(`${LL("Evidencia", "Evidence")}: ${ti.label}`)}">${TIERS.map(([, es, en], i) => `<span class="${i === tierIdx ? "on" : ""}" style="--c:${ti.color}"><i></i>${esc(LL(es, en))}</span>`).join("")}</div>
          <p class="tr-class">${esc(ti.why)}</p>
          ${capsule(d, sel, t)}
          <p class="tr-capnote">${esc(crosses ? LL("El intervalo del 95 % cruza el cero: podría subir o bajar.", "The 95 % interval crosses zero: it could go up or down.") : LL("El intervalo del 95 % no toca el cero: la dirección es clara.", "The 95 % interval does not touch zero: the direction is clear."))}</p>
          <dl class="tr-stats">
            <div title="${esc(LL("Mann-Kendall modificado de Hamed y Rao (1998)", "Hamed & Rao (1998) modified Mann-Kendall"))}"><dt>p</dt><dd class="num">${t.p < 0.001 ? `&lt;&#8239;${num(0.001, 3)}` : num(t.p, 3)}</dd></div>
            <div title="${esc(LL("Benjamini-Hochberg entre las 32 provincias", "Benjamini-Hochberg across the 32 provinces"))}"><dt>q (FDR)</dt><dd class="num">${t.q === null ? "—" : num(t.q, 3)}</dd></div>
            <div title="${esc(LL("80 % de potencia, α = 0,05", "80 % power, α = 0.05"))}"><dt>${esc(LL("Mín. detectable", "Min. detectable"))}</dt><dd class="num">±${num(t.mdt)}</dd></div>
            <div><dt>${esc(LL("Media", "Mean"))}</dt><dd class="num">${num(t.media)}</dd></div>
          </dl>
          <p class="tr-rule">${esc(LL(`Significativa si ${d.sigRule(sel.reg)}. ${d.V.prueba}.`, `Significant if ${d.sigRule(sel.reg)}. ${d.V.prueba}.`))}</p>
          <div class="tr-srcs">${["IMERG", "CHIRPS"].map((p) => { const m = d.V.productos[p], tt = d.tr(sel, p); return `<p class="tr-src ${m ? "" : "pending"}"><b>${p}</b><span>${esc(m ? m.tipo_fuente : LL("satélite + estaciones · llega en la próxima corrida", "satellite + stations · arrives in the next run"))}</span>${tt ? `<em class="num">${sgn(tt.pendiente_decada)}</em>` : ""}</p>`; }).join("")}</div>
          <details class="tr-why"><summary>${esc(LL("¿Por qué importa y qué no dice?", "Why it matters and what it does not say"))}</summary>
            <p>${esc(v.por_que_importa)} ${esc(LL(`Si sube: ${v.aumento_significa}.`, `If it rises: ${v.aumento_significa}.`))}</p>
            <p>${esc(d.V.nota_causalidad)}</p>
            <p>${esc(LL("IMERG es recuperación satelital calibrada con pluviómetros; CHIRPS es satélite + estaciones. No son testigos totalmente independientes: comparten infrarrojo geoestacionario y pluviómetros.", "IMERG is a gauge-calibrated satellite retrieval; CHIRPS is satellite + stations. They are not fully independent: they share geostationary infrared and rain gauges."))}</p>
          </details>`;
      }
    } else if (ui.tab === "serie") {
      html = `<p class="pane-h">${esc(LL(`${d.lab(v)} · ${d.regName(sel.reg)}`, `${d.lab(v)} · ${d.regName(sel.reg)}`))}<span class="num" id="tr-read"></span></p>
        ${seriesChart(d, sel, paneW(), ui.year === null ? null : years()[ui.year], Math.max(170, Math.min(340, body.clientHeight - 120)))}
        <p class="pane-tip">${esc(LL("Toca un año para verlo en el mapa.", "Tap a year to see it on the map."))}</p>`;
    } else {
      const f = forest(d, sel, paneW());
      html = `<p class="pane-h">${esc(LL(`${f.nSig} de 32 significativas`, `${f.nSig} of 32 significant`))} <span>${esc(vm().unidad_tendencia)}</span></p>
        <p class="pane-tip">${esc(LL("De más subida a más bajada. Barra: IC 95 %. Punto relleno: significativa. Toca una.", "Largest rise to largest fall. Bar: 95 % CI. Filled dot: significant. Tap one."))}</p>${f.svg}`;
    }
    body.innerHTML = `<div class="pane in">${html}</div>`;
    const hit = body.querySelector<SVGRectElement>(".tr-hit");
    if (hit) {
      const yrs = years(), W = Number(hit.dataset.w), ml = Number(hit.dataset.ml), mr = Number(hit.dataset.mr);
      const idxAt = (x: number) => { const r = hit.ownerSVGElement!.getBoundingClientRect(); return Math.max(0, Math.min(yrs.length - 1, Math.round(((((x - r.left) / r.width) * W - ml) / (W - ml - mr)) * (yrs.length - 1)))); };
      hit.addEventListener("mousemove", (e) => {
        const k = idxAt(e.clientX), s = d.series(sel);
        $("tr-read").textContent = `${yrs[k]} · ${s?.[k] === null || !s ? "—" : num(s[k]!)} ${vm().unidad}`;
      });
      hit.addEventListener("click", (e) => tl.pick(idxAt(e.clientX)));
    }
  };

  // ── El mapa ──
  const renderLegend = (max: number, unit: string, pct: boolean) => {
    const v = vm(), up = v.tipo === "seco" ? LL("más seco", "drier") : LL("más lluvia", "more rain"), dn = v.tipo === "seco" ? LL("menos seco", "less dry") : LL("menos lluvia", "less rain");
    const f = (x: number) => (pct ? `${sgn(x, 0)} %` : sgn(x));
    $("wx-legend").innerHTML = `
      <div class="lg-bar" style="background:${rampCss(d.warmIfUp(sel.ind))}"></div>
      <div class="lg-ax num"><span>${f(-max)}</span><span>0</span><span>${f(max)}</span></div>
      <div class="lg-w"><span>${esc(dn)}</span><span>${esc(pct ? LL("frente a su media", "vs its mean") : unit)}</span><span>${esc(up)}</span></div>
      ${pct ? "" : `<p class="lg-dot"><i></i>${esc(LL("punto: significativa (q ≤ 0,10)", "dot: significant (q ≤ 0.10)"))}</p>`}`;
  };
  const yearMaxCache = new Map<string, number>();
  const renderMap = () => {
    if (!t3) return;
    const map = t3.map, mode = ui.year === null ? "trend" : "year";
    wx.dataset.mode = mode;
    if (mode === "trend") {
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
        map.addLayer({ id: "stip", type: "circle", source: "stip", paint: {
          "circle-radius": ["interpolate", ["linear"], ["zoom"], 6, 1, 8, 1.8, 11, 3.5], "circle-color": "#ffffff", "circle-opacity": 0.8,
        } });
      }
      map.setLayoutProperty("stip", "visibility", "visible");
      // Provincias invisibles pero tocables (para elegir región y ver su nombre)
      const clear: Record<string, string> = {}, zero: Record<string, number> = {};
      d.provs.forEach((r) => { const id = d.isoToShape[r.id]; if (id) { clear[id] = "rgba(0,0,0,0)"; zero[id] = 0; } });
      t3.setChoro(clear, zero);
      map.setLayoutProperty("prov-fill", "visibility", "visible");
      renderLegend(max, vm().unidad_tendencia, false);
    } else {
      const yi = ui.year!, key = `${sel.ind}|${sel.per}|${sel.src}`;
      const anom = (reg: string, k: number) => {
        const s = d.series(sel, sel.src, reg); if (!s) return null;
        const vals = s.filter((x): x is number => x !== null), mean = vals.reduce((a, b) => a + b, 0) / vals.length;
        return s[k] === null || !mean ? null : ((s[k]! - mean) / mean) * 100;
      };
      if (!yearMaxCache.has(key)) yearMaxCache.set(key, scaleMax(d.provs.flatMap((r) => years().map((_, k) => anom(r.id, k)))));
      const max = yearMaxCache.get(key)!;
      const colors: Record<string, string> = {}, alpha: Record<string, number> = {};
      d.provs.forEach((r) => {
        const id = d.isoToShape[r.id], a = anom(r.id, yi); if (!id) return;
        if (a === null) { colors[id] = "rgba(0,0,0,0)"; alpha[id] = 0; return; }
        colors[id] = `rgb(${colorOf(Math.abs(a) / max, d.towardDry(sel.ind, a)).join(",")})`;
        alpha[id] = 0.82;
      });
      t3.setChoro(colors, alpha);
      t3.setLayer("prov");
      if (map.getLayer("stip")) map.setLayoutProperty("stip", "visibility", "none");
      renderLegend(max, "", true);
    }
  };
  const frame = (fly = true) => {
    if (!t3) return;
    t3.setFitPadding(fitPad());
    const pitch = ui.style === "3d" ? 52 : 0, bearing = ui.style === "3d" ? -14 : 0;
    const b = sel.reg === "DO" ? RD : d.bbox(sel.reg) ?? RD;
    t3.map.fitBounds(b, { padding: fitPad(), pitch, bearing, duration: fly && !RM() ? 1600 : 0, maxZoom: 10 });
  };
  const pickRegion = (reg: string, fly: boolean) => {
    sel.reg = reg;
    t3?.selectProvince(reg === "DO" ? null : d.isoToShape[reg] ?? null);
    if (fly) frame();
    renderPeek(); renderRail(); renderPane();
  };

  const renderAll = () => { renderTop(); renderRail(); renderPeek(); renderPane(); renderMap(); };

  // ── Línea de tiempo ──
  const tl = timeline($("wx-bar"), (i) => { ui.year = i; renderPeek(); renderMap(); if (ui.tab === "serie") renderPane(); });
  tl.setYears(years());
  if (ui.year !== null) tl.pick(ui.year);

  // ── Arranque del mapa ──
  t3 = terrain3d($("map"), {
    zones: [], sites: [], onZone: () => {}, onSite: () => {}, cellLabel: () => "", siteAction: "",
    provinces: (d.fc ?? undefined) as never,
    onProvince: (shape) => { const iso = d.shapeToIso[shape]; if (iso) pickRegion(iso, true); },
  });
  const mine = t3;
  wx.dataset.sheet = sheet.state;
  renderTop(); renderRail(); renderPeek(); renderPane();
  mine.ready.then(() => {
    if (t3 !== mine) return;
    mine.setFitPadding(fitPad());
    mine.setMode(ui.style === "plano" ? "plano" : ui.style);
    renderMap();
    if (sel.reg !== "DO") mine.selectProvince(d.isoToShape[sel.reg] ?? null);
    frame(true);
    const map = mine.map;
    map.on("mousemove", (e) => {
      const f = map.queryRenderedFeatures(e.point, { layers: ["prov-fill"] })[0];
      if (!f) { tip.hidden = true; return; }
      const iso = d.shapeToIso[String(f.id)], name = String(f.properties?.shapeName ?? "");
      let line = "";
      if (ui.year === null) {
        const lay = d.cells(sel), k = cellAt(d.R, e.lngLat.lng, e.lngLat.lat);
        const v = lay && k >= 0 && d.R.incluida[k] ? lay.pendiente_decada[k] : null;
        if (v !== null && lay) line = `<b class="num">${sgn(v)}</b> ${esc(vm().unidad_tendencia)} <span>· ${esc((lay.q[k] ?? 1) <= d.V.umbral_significancia.q_fdr ? LL("significativa", "significant") : LL("no significativa", "not significant"))}</span>`;
      } else {
        const s = d.series(sel, sel.src, iso), v = s?.[ui.year];
        if (v !== null && v !== undefined) line = `<b class="num">${num(v)}</b> ${esc(vm().unidad)} <span>· ${years()[ui.year]}</span>`;
      }
      const r = map.getCanvas().getBoundingClientRect();
      tip.innerHTML = `<p class="tt-n">${esc(name)}</p>${line ? `<p>${line}</p>` : ""}`;
      tip.hidden = false;
      tip.style.left = `${Math.min(innerWidth - tip.offsetWidth - 12, Math.max(12, r.left + e.point.x - tip.offsetWidth / 2))}px`;
      tip.style.top = `${r.top + e.point.y - tip.offsetHeight - 16}px`;
    });
    map.getCanvas().addEventListener("mouseleave", () => { tip.hidden = true; });
  });
  const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") openRail(false); };
  addEventListener("keydown", onKey);
  cleanup.push(() => { removeEventListener("keydown", onKey); tl.stop(); });
}
