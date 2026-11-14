import "leaflet/dist/leaflet.css";
import "./style.css";
import L from "leaflet";
import {
  DISCORDANT, dualTimeline, evidenceChart, gapIndex, heatmap, hysteresis, ledger, monthTimeline, quadrant, rawChart, spiChart, uncertaintyBar, windowLength, windowMatrix,
} from "./charts";
import { load, type Audit, type Index, type Phantom, type Puntos, type Series, type Window } from "./data";
import { T, getLang, regionMeta, setLang, varMeta } from "./i18n";
import { buildLanes, FUNC, fnName, GREEN, ribbon2D, ribbonStage, verdictColor, type Fn, type Stage } from "./ribbon";
import {
  digitsFor, fmt, fmtP, fmtSigned, multipleTestingNote, predictionFeedback, seasonLesson,
  trapText, verdictSentence, verdictShort, windowLabel, type Prediction,
} from "./text";

const app = document.getElementById("app")!;

interface State {
  variable: string;
  region: string;
  prediction: Prediction | null;
  revealed: boolean;
  window: Window | null;
  raw: boolean;
  heatVar: string;
  mapVar: string;
  fn: "gpp_modelo" | "lst_menos_aire" | "ndii_agua";
  audit: { id: string; ev: string } | null;
  audited: boolean;
}
const state: State = {
  variable: "imerg_precip", region: "noroeste", prediction: null, revealed: false, window: null, raw: false,
  heatVar: "modis_ndvi", mapVar: "modis_ndvi", fn: "lst_menos_aire", audit: null, audited: false,
};

const TEST_MODE = new URLSearchParams(location.search).get("prueba") === "1";

let index: Index;
const maps: L.Map[] = [];

const POINT_NAMES: Record<string, string> = {
  montecristimontesecoa: "Montecristi A", montecristimontesecob: "Montecristi B", sierramontecristi: "Sierra de Montecristi",
  jaraguacomparacionseco: "Jaragua", cordilleracomparacionhumedo: "Cordillera Central",
};
const POINT_ORDER = ["montecristimontesecoa", "montecristimontesecob", "sierramontecristi", "jaraguacomparacionseco", "cordilleracomparacionhumedo"];
const pointName = (id: string) => POINT_NAMES[id.replace(/_/g, "")] ?? id;
const NAMES = Object.fromEntries(POINT_ORDER.map((id) => [id, pointName(id)]));
const WORSE_IS_HIGH: Record<string, boolean> = { modis_ndvi: false, modis_gpp: false, modis_lst: true };
const AMBER = "#f2b33d";

const esc = (s: string) => s.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]!));

function clearMaps() { while (maps.length) { const m = maps.pop()!; m.stop(); m.off(); m.remove(); } }

function baseMap(el: HTMLElement, center: [number, number], zoom: number): L.Map {
  const m = L.map(el, { zoomControl: true, attributionControl: true, scrollWheelZoom: false }).setView(center, zoom);
  L.tileLayer("https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/BlueMarble_ShadedRelief_Bathymetry/default/GoogleMapsCompatible_Level8/{z}/{y}/{x}.jpeg", {
    maxNativeZoom: 8, maxZoom: 10, attribution: "NASA GIBS · Blue Marble",
  }).addTo(m);
  maps.push(m);
  return m;
}

const ICON: Record<string, string> = {
  investigar: '<path d="M2.75 5.25l4.75-2 5 2 4.75-2v11.5l-4.75 2-5-2-4.75 2z"/><path d="M7.5 3.25v11.5M12.5 5.25v11.5"/>',
  expedientes: '<path d="M3.5 5.5l1.5 1.5 2.5-2.5M3.5 11.5l1.5 1.5 2.5-2.5"/><path d="M10.5 6h6M10.5 12h6M3.5 16.5h13"/>',
  ribbon: '<path d="M2.5 8c2.5-4 5-4 7.5 0s5 4 7.5 0"/><path d="M2.5 13c2.5-4 5-4 7.5 0s5 4 7.5 0"/><path d="M2.5 8v5M17.5 8v5"/>',
  metodo: '<path d="M3 4.75c2.5-1 5-1 7 .5 2-1.5 4.5-1.5 7-.5v11c-2.5-1-5-1-7 .5-2-1.5-4.5-1.5-7-.5z"/><path d="M10 5.25v11"/>',
};

function shell(): void {
  const t = T();
  document.title = t.title;
  const item = (r: "investigar" | "ribbon" | "expedientes" | "metodo", label: string) =>
    `<a class="rail-i" href="#${r}" data-nav="${r}" title="${esc(label)}" aria-label="${esc(label)}"><svg viewBox="0 0 20 20" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">${ICON[r]}</svg><span>${esc(label)}</span></a>`;
  app.innerHTML = `
    <nav class="rail" aria-label="${esc(t.brand)}">
      <a class="rail-mark" href="#investigar" title="Stellar Horizons · ${esc(t.brand)}" aria-label="Stellar Horizons · ${esc(t.brand)}">
        <svg viewBox="0 0 32 32" aria-hidden="true"><path d="M16 2.5l2.3 8.2 8.2 2.3-8.2 2.3L16 23.5l-2.3-8.2-8.2-2.3 8.2-2.3z" fill="${AMBER}"/><path d="M2.5 28.5c7.5-4.6 19.5-4.6 27 0" stroke="#ffffff" stroke-width="2.2" fill="none" stroke-linecap="round"/></svg>
      </a>
      ${item("investigar", t.navInvestigate)}
      ${item("ribbon", "Recovery Ribbon")}
      ${item("expedientes", t.navAudit)}
      ${item("metodo", t.navMethod)}
      <button class="rail-lang" id="lang" aria-label="${esc(t.langSwitchLabel)}" title="${esc(t.langSwitchLabel)}" lang="${getLang() === "es" ? "en" : "es"}">${getLang() === "es" ? "EN" : "ES"}</button>
    </nav>
    <main id="view"></main>
    <footer class="foot"><p>${esc(t.team)} · ${esc(t.footer)}</p></footer>`;
  document.getElementById("lang")!.addEventListener("click", () => {
    setLang(getLang() === "es" ? "en" : "es");
    shell();
    route(false);
  });
}

function setNav(r: string) {
  document.querySelectorAll<HTMLAnchorElement>("[data-nav]").forEach((a) => a.classList.toggle("on", a.dataset.nav === r));
}

/* ───────────── Investigar: la consola del observatorio ───────────── */
// Pregunta de la pantalla: ¿cambió esta variable en esta zona desde 2001, y cuánto?
// Estilo data-terminal (taste-skill, semilla 2114408584): paneles más oscuros que el fondo, cifras tabulares,
// y la única marca de selección es una línea de 1px en ámbar (el color de la sequía) del ancho de su etiqueta.
// Elemento propio: el mapa de la zona responde a la serie; al recorrer los meses, la zona toma el valor de ese mes.

// Variables en las que "más alto que lo normal" es la dirección del estrés (más calor)
const STRESS_HIGH = new Set(["merra2_t2m", "modis_lst"]);
const SHORT: Record<string, [string, string]> = {
  imerg_precip: ["Lluvia", "Rain"],
  merra2_t2m: ["Temp. del aire", "Air temp."],
  gldas_soilmoi0_10cm: ["Humedad del suelo", "Soil moisture"],
  gldas_rootmoist: ["Agua en raíces", "Root-zone water"],
  modis_ndvi: ["Verdor (NDVI)", "Greenness (NDVI)"],
  modis_lst: ["Temp. de superficie", "Surface temp."],
  modis_gpp: ["Productividad (GPP)", "Productivity (GPP)"],
};
const shortName = (k: string) => (SHORT[k] ? SHORT[k][getLang() === "es" ? 0 : 1] : varMeta(index, k).nombre);

interface ZoneMarks { paths: L.Path[]; label: L.Layer | null; name: string }
let zone: ZoneMarks = { paths: [], label: null, name: "" };
let playTimer: number | null = null;

function stopPlay() {
  if (playTimer !== null) { clearInterval(playTimer); playTimer = null; }
}

async function viewInvestigate() {
  stopPlay();
  const t = T();
  const view = document.getElementById("view")!;
  const vmeta = varMeta(index, state.variable);
  const rmeta = regionMeta(index, state.region);
  const keys = Object.keys(index.variables);
  const climate = keys.filter((k) => !k.startsWith("modis_"));
  const veg = keys.filter((k) => k.startsWith("modis_"));
  const ph = !TEST_MODE ? await load<Phantom>("phantom.json") : null;
  const auds = (ph?.auditorias ?? []).filter((a) => a.veredicto !== "sin_impacto");
  const count = (v: string) => auds.filter((a) => a.veredicto === v).length;
  const all = await Promise.all(Object.keys(index.regiones).map((k) => load<Series>(`series/${state.variable}_${k}.json`)));
  const s = all.find((x) => x.region === state.region) ?? (await load<Series>(`series/${state.variable}_${state.region}.json`));
  const y0 = s.anual.anios[0];
  const y1 = s.anual.anios[s.anual.anios.length - 1];
  const stressHigh = STRESS_HIGH.has(state.variable);
  const droughts = [...(ph?.sequias.find((d) => d.region === state.region)?.eventos ?? [])].reverse();
  const tab = (k: string) => `<button class="tab ${k === state.variable ? "on" : ""}" data-var="${k}" role="tab" aria-selected="${k === state.variable}">${esc(shortName(k))}</button>`;

  view.innerHTML = `
    <div class="con-head">
      <div>
        <p class="crumb">Stellar Horizons<span aria-hidden="true">/</span>${esc(t.brand)}</p>
        <h1>${esc(rmeta.nombre)}</h1>
        <p class="con-sub">${esc(vmeta.nombre)} · ${y0}–${y1} · ${esc(vmeta.fuente)}</p>
      </div>
      <div class="tabs" role="tablist" aria-label="${esc(t.whereH)}">
        ${Object.keys(index.regiones).map((k) => `<button class="tab ${k === state.region ? "on" : ""}" data-reg="${k}" role="tab" aria-selected="${k === state.region}">${esc(regionMeta(index, k).nombre)}</button>`).join("")}
      </div>
    </div>
    <div class="vtabs" role="tablist" aria-label="${esc(t.whatQ)}">
      <span class="vt-group">${esc(t.groupClimate)}</span>${climate.map(tab).join("")}
      <span class="vt-group">${esc(t.groupVegShort)}</span>${veg.map(tab).join("")}
    </div>

    <div class="console">
      <section class="pnl map-pnl" aria-label="${esc(t.mapLabel)}">
        <div id="map"></div>
        <p class="map-note" id="mapcap"></p>
      </section>

      <aside class="side-col">
        <section class="pnl verdict-pnl" id="verdict" aria-live="polite"></section>
        <section class="pnl drought-pnl">
          <div class="pnl-h"><h2>${esc(t.zoneDroughtsH(rmeta.nombre))}</h2><span class="meta num">${droughts.length}</span></div>
          <p class="meta">${esc(t.droughtsRule)}</p>
          <div class="dscroll">
            <table class="dtable">
              <thead><tr><th>${esc(t.dPeriod)}</th><th class="num">${esc(t.dDur)}</th><th class="num">${esc(t.dPeak)}</th></tr></thead>
              <tbody>${droughts.map((e, i) => `<tr data-ev="${i}" tabindex="0"><td>${e.inicio.slice(0, 7)} – ${e.fin.slice(0, 7)}</td><td class="num">${e.duracion_meses} ${esc(t.monthsShort)}</td><td class="num">${fmt(e.pico, 2)}</td></tr>`).join("")}</tbody>
            </table>
          </div>
          <a class="more" href="#expedientes">${esc(t.droughtsGo)} →</a>
        </section>
      </aside>

      <section class="pnl tl-pnl">
        <div class="pnl-h">
          <h2>${esc(t.tlTitle(vmeta.nombre, rmeta.nombre))}</h2>
          <div class="tl-tools">
            <span class="readout num" id="readout"></span>
            <button class="txt-btn" id="play" ${state.revealed ? "" : "disabled"}>${esc(t.play)}</button>
          </div>
        </div>
        <div class="legend tl-legend" id="tl-legend">
          <span><i class="sq" style="background:${AMBER}"></i>${esc(stressHigh ? t.tlAbove : t.tlBelow)}</span>
          <span><i class="sq" style="background:#6b6f74"></i>${esc(stressHigh ? t.tlBelow : t.tlAbove)}</span>
          <span><i class="ln" style="background:#ffffff"></i>${esc(t.tlTrend)}</span>
          <span><i class="sq" style="background:#2c2c31"></i>${esc(t.tlDrought)}</span>
        </div>
        <div class="tl-plot" id="tl"><div class="cursor" id="cursor" hidden></div></div>
        <p class="meta">${esc(state.revealed ? t.scrubHint : t.tlLocked)}</p>
      </section>
    </div>

    <div id="evidence"></div>

    ${auds.length ? `
    <section class="pnl band">
      <div>
        <h2>${esc(t.findingsH)}</h2>
        <p class="band-lead">${esc(t.verdictLead(auds.length, count("fantasma"), count("estres_invisible"), count("censurada"), count("inconclusa")))}</p>
        <a class="more" href="#expedientes">${esc(t.findingsGo)} →</a>
      </div>
      <div class="kstrip">
        ${(["fantasma", "estres_invisible", "censurada", "inconclusa"] as const).map((v) => `<p><span>${esc(t.verdictName[v])}</span><b class="num">${count(v)}</b></p>`).join("")}
      </div>
    </section>` : ""}`;

  view.querySelectorAll<HTMLButtonElement>("[data-var]").forEach((b) => b.addEventListener("click", () => {
    state.variable = b.dataset.var!; resetInvestigation(); route(false);
  }));
  view.querySelectorAll<HTMLButtonElement>("[data-reg]").forEach((b) => b.addEventListener("click", () => {
    state.region = b.dataset.reg!; resetInvestigation(); route(false);
  }));

  drawRegionMap(all);

  // ── La serie mes a mes, con cursor que mueve el mapa ──
  const d = digitsFor(vmeta);
  const tlEl = document.getElementById("tl")!;
  const cursor = document.getElementById("cursor")!;
  const readout = document.getElementById("readout")!;
  const months = s.meses.map((m) => m.slice(0, 7));
  const anom = s.anomalia_mensual;
  const absSorted = anom.filter((v): v is number => v !== null).map(Math.abs).sort((a, b) => a - b);
  const lim = (absSorted[Math.floor(absSorted.length * 0.98)] || 1) * 1.08;
  let xs: { apply: (v: Date) => number; invert: (v: number) => Date } | null = null;

  const setMonth = (i: number) => {
    if (!xs) return;
    const v = anom[i];
    const date = new Date(`${months[i]}-15T00:00:00`);
    cursor.hidden = false;
    cursor.style.left = `${xs.apply(date)}px`;
    const val = v === null ? "—" : `${fmtSigned(v, d)} ${vmeta.unidad}`;
    readout.textContent = `${months[i]} · ${val}`;
    const stress = v !== null && (stressHigh ? v > 0 : v < 0);
    const k = v === null ? 0 : Math.min(1, Math.abs(v) / lim);
    for (const p of zone.paths) p.setStyle({ fillColor: stress ? AMBER : "#ffffff", fillOpacity: 0.12 + 0.6 * k });
    if (zone.label) (zone.label as L.Rectangle).setTooltipContent(`${esc(zone.name)} · ${months[i]} · ${esc(val)}`);
  };
  const clearMonth = () => {
    cursor.hidden = true;
    readout.textContent = "";
    for (const p of zone.paths) p.setStyle({ fillColor: AMBER, fillOpacity: 0.16 });
    setZoneLabel(s);
  };
  const nearest = (x: number) => {
    if (!xs) return 0;
    const t0 = xs.invert(x).getTime();
    let best = 0;
    let bd = Infinity;
    months.forEach((m, i) => { const dd = Math.abs(new Date(`${m}-15T00:00:00`).getTime() - t0); if (dd < bd) { bd = dd; best = i; } });
    return best;
  };

  const drawTl = (animate: boolean) => {
    tlEl.querySelector("svg")?.remove();
    tlEl.classList.toggle("draw", animate);
    const bands = droughts.map((e) => ({ a: e.inicio, b: e.fin }));
    const plot = monthTimeline(s, stressHigh, state.revealed, tlEl.clientWidth || 900, state.revealed ? bands : []) as SVGSVGElement & { scale?: (n: string) => { apply: (v: Date) => number; invert: (v: number) => Date } };
    tlEl.prepend(plot);
    xs = state.revealed && plot.scale ? plot.scale("x") : null;
    if (!state.revealed) return;
    plot.addEventListener("pointermove", (e) => { stopPlay(); setMonth(nearest((e as PointerEvent).offsetX)); });
    plot.addEventListener("pointerleave", () => { if (playTimer === null) clearMonth(); });
  };
  drawTl(false);

  view.querySelectorAll<HTMLTableRowElement>("[data-ev]").forEach((r) => {
    const go = () => {
      if (!state.revealed) return;
      stopPlay();
      const e = droughts[Number(r.dataset.ev)];
      const i = months.indexOf(e.inicio.slice(0, 7));
      if (i >= 0) setMonth(i);
      view.querySelectorAll("[data-ev]").forEach((x) => x.classList.toggle("on", x === r));
    };
    r.addEventListener("click", go);
    r.addEventListener("keydown", (ev) => { if ((ev as KeyboardEvent).key === "Enter") go(); });
  });

  const play = document.getElementById("play") as HTMLButtonElement;
  play.addEventListener("click", () => {
    if (playTimer !== null) { stopPlay(); play.textContent = t.play; clearMonth(); return; }
    let i = 0;
    play.textContent = t.pause;
    playTimer = window.setInterval(() => {
      if (i >= months.length) { stopPlay(); play.textContent = t.play; return; }
      setMonth(i); i += 1;
    }, 32);
  });

  const reveal = (p: Prediction) => {
    const first = !state.revealed;
    state.prediction = p;
    state.revealed = true;
    if (first) {
      drawTl(true);
      play.disabled = false;
      view.querySelector(".tl-pnl > .meta")!.textContent = t.scrubHint;
    }
    renderVerdict(s, reveal);
    if (first) renderEvidence(s);
    setZoneLabel(s);
  };
  renderVerdict(s, reveal);
  if (state.revealed) { renderEvidence(s); setZoneLabel(s); }
}

function resetInvestigation() {
  stopPlay();
  state.prediction = null; state.revealed = false; state.window = null; state.raw = false;
}

/** Visor: las cuatro esquinas de la zona, como el encuadre de un instrumento. */
function reticle(map: L.Map, b: L.LatLngBounds, color: string, weight: number, opacity: number) {
  const n = b.getNorth(), s = b.getSouth(), w = b.getWest(), e = b.getEast();
  const dx = (e - w) * 0.32, dy = (n - s) * 0.32;
  const arms: L.LatLngExpression[][] = [
    [[n - dy, w], [n, w], [n, w + dx]],
    [[n, e - dx], [n, e], [n - dy, e]],
    [[s + dy, e], [s, e], [s, e - dx]],
    [[s, w + dx], [s, w], [s + dy, w]],
  ];
  L.polyline(arms, { color, weight, opacity, lineCap: "square", lineJoin: "miter", interactive: false }).addTo(map);
}

/** Mapa de terreno: las dos zonas a la vez; la elegida con visor ámbar; clic en la otra para cambiar. */
function drawRegionMap(all: Series[]) {
  const t = T();
  const el = document.getElementById("map");
  if (!el) return;
  const map = baseMap(el, [18.8, -71.2], 8);
  if (L.Browser.mobile) map.dragging.disable();
  const toBounds = (b: number[]) => L.latLngBounds([b[1], b[0]], [b[3], b[2]]);
  const pts: L.LatLng[] = [];
  let note = t.obsMapNote;
  zone = { paths: [], label: null, name: regionMeta(index, state.region).nombre };
  for (const s of all) {
    const on = s.region === state.region;
    const color = on ? AMBER : "#ffffff";
    const name = regionMeta(index, s.region).nombre;
    const pick = () => { if (!on) { state.region = s.region; resetInvestigation(); route(false); } };
    const p = s.pasaporte;
    if (p.puntos && p.puntos.length) {
      note = t.mapPoints;
      p.puntos.forEach(([lat, lon, id], i) => {
        const m = L.circleMarker([lat, lon], { radius: on ? 8 : 6, color, weight: 2, fillColor: on ? AMBER : color, fillOpacity: on ? 0.16 : 0.25 })
          .on("click", pick).addTo(map);
        if (i === 0) {
          m.bindTooltip(name, { permanent: true, direction: "right", offset: [12, 0], className: on ? "zone-tip on" : "zone-tip" });
          if (on) zone.label = m;
        } else m.bindTooltip(pointName(id));
        if (on) zone.paths.push(m);
        pts.push(L.latLng(lat, lon));
      });
    } else {
      const box = p.caja_datos && !(p.caja_datos[0] === p.caja_datos[2]) ? p.caja_datos : p.caja_pedida;
      if (box) {
        const b = toBounds(box);
        reticle(map, b, color, on ? 2.5 : 1.5, on ? 1 : 0.8);
        const hit = L.rectangle(b, { stroke: false, fill: true, fillColor: color, fillOpacity: on ? 0.16 : 0.0001 })
          .bindTooltip(name, { permanent: true, direction: "right", offset: [12, 0], className: on ? "zone-tip on" : "zone-tip" })
          .on("click", pick).addTo(map);
        if (on) { zone.paths.push(hit); zone.label = hit; }
        pts.push(b.getNorthEast(), b.getSouthWest());
      }
      if (p.caja_datos && p.caja_datos[0] === p.caja_datos[2] && on) {
        L.circleMarker([p.caja_datos[1], p.caja_datos[0]], { radius: 5, color: AMBER, weight: 2, fillOpacity: 0.6 }).addTo(map);
        note += t.mapPoint;
      }
    }
  }
  if (pts.length) map.fitBounds(L.latLngBounds(pts).pad(0.2), { maxZoom: 9, animate: false });
  document.getElementById("mapcap")!.textContent = note;
}

/** Tras revelar, la etiqueta de la zona lleva el resultado. */
function setZoneLabel(s: Series) {
  if (!zone.label || !state.revealed) return;
  const meta = varMeta(index, state.variable);
  (zone.label as L.Rectangle).setTooltipContent(`${esc(zone.name)} · ${fmtSigned(s.completa.pendiente_decada, digitsFor(meta))} ${esc(meta.unidad)} ${esc(T().factPerDecade)}`);
}

/** Panel lateral: primero la apuesta; después, el resultado con su incertidumbre. */
function renderVerdict(s: Series, onPick: (p: Prediction) => void) {
  const t = T();
  const el = document.getElementById("verdict")!;
  const meta = varMeta(index, state.variable);
  const rname = regionMeta(index, state.region).nombre;
  const full = s.completa;
  const y0 = s.anual.anios[0];
  const y1 = s.anual.anios[s.anual.anios.length - 1];
  const predLabel: Record<Prediction, string> = { sube: t.predUp, baja: t.predDown, nada: t.predNone };
  const arrow: Record<Prediction, string> = { sube: "↑", baja: "↓", nada: "→" };
  if (!state.revealed) {
    el.innerHTML = `
      <div class="pnl-h"><h2>${esc(t.hypothesis)}</h2></div>
      <p class="vq">${esc(t.since2001(vmeta0(meta.nombre), rname))}</p>
      <div class="pred" role="radiogroup" aria-label="${esc(t.hypothesis)}">
        ${(["sube", "baja", "nada"] as Prediction[]).map((p) => `<button class="pred-b" data-pred="${p}" role="radio" aria-checked="false"><span class="arw" aria-hidden="true">${arrow[p]}</span>${esc(predLabel[p])}</button>`).join("")}
      </div>
      <p class="meta">${esc(t.predHint)}</p>`;
  } else {
    const fb = predictionFeedback(state.prediction ?? "nada", full);
    const d = digitsFor(meta);
    const mt = multipleTestingNote(full, index.series.length);
    el.innerHTML = `
      <div class="pnl-h"><h2>${esc(t.resultH)}</h2><span class="meta">${esc(t.yourBet)}: ${arrow[state.prediction ?? "nada"]} ${esc(predLabel[state.prediction ?? "nada"])}</span></div>
      <p class="fb ${fb.ok === true ? "yes" : fb.ok === false ? "no" : ""}">${esc(fb.text)}</p>
      <p class="fig"><b class="num">${fmtSigned(full.pendiente_decada, d)}</b><span>${esc(meta.unidad)} ${esc(t.factPerDecade)}</span></p>
      <p class="vs">${esc(verdictSentence(meta, rname, full, y0, y1))}</p>
      <div id="unc" class="chart"></div>
      <div class="kstrip three">
        <p><span>p</span><b class="num">${fmtP(full.p_mk)}</b></p>
        <p><span>q · ${index.series.length} ${esc(t.seriesWord)}</span><b class="num">${full.q_bh === undefined ? "—" : fmtP(full.q_bh)}</b></p>
        <p><span>${esc(t.years)}</span><b class="num">${full.n}</b></p>
      </div>
      ${mt ? `<p class="notice">${esc(t.mtShort)}</p>` : ""}`;
    const unc = document.getElementById("unc")!;
    unc.append(uncertaintyBar(full, d, meta.unidad, unc.clientWidth || 320));
  }
  el.querySelectorAll<HTMLButtonElement>("[data-pred]").forEach((b) => b.addEventListener("click", () => onPick(b.dataset.pred as Prediction)));
}
const vmeta0 = (n: string) => n.charAt(0).toLowerCase() + n.slice(1);

/** Debajo de la consola: el año a año, los intervalos y el pasaporte. */
function renderEvidence(s: Series) {
  const t = T();
  const host = document.getElementById("evidence")!;
  const meta = varMeta(index, state.variable);
  const full = s.completa;
  const years = s.anual.anios;
  const y0 = years[0];
  const y1 = years[years.length - 1];
  const d = digitsFor(meta);
  const pp = s.pasaporte;
  const dir = full.veredicto === "sube" || full.veredicto === "baja";
  host.innerHTML = `
    <div class="ev-grid">
      <section class="pnl ev-year">
        <div class="pnl-h">
          <h2>${esc(state.raw ? t.chartRaw : t.chartAnom)}</h2>
          <button class="txt-btn" id="rawtoggle">${esc(state.raw ? t.btnAnom : t.btnRaw)}</button>
        </div>
        <div id="chart" class="chart"></div>
        <p class="meta">${esc(state.raw ? seasonLesson(meta, s.amplitud_estacional, full, full.n) : t.captionAnom)}</p>
      </section>

      <section class="pnl ev-win">
        <div class="pnl-h"><h2>${esc(t.windowsH)}</h2></div>
        <p class="meta">${esc(t.windowLede)}</p>
        <div id="matrix"></div>
      </section>
      <section class="pnl ev-len side">
        <div id="wininfo"></div>
        <div class="pnl-h" style="margin-top:20px"><h2>${esc(t.wlTitle)}</h2></div>
        <p class="meta">${esc(t.wlSub)}</p>
        <div class="legend"><span><i class="sq" style="background:${AMBER}"></i>${esc(t.wlHit)}</span>${dir ? `<span><i class="sq" style="background:#e6e6e6"></i>${esc(t.wlOpp)}</span>` : ""}</div>
        <div id="wlen" class="chart"></div>
        ${s.ventanas_que_enganan.length ? `
          <h3>${esc(t.trapsTitle)}</h3>
          <div class="traps">${s.ventanas_que_enganan.map((w, i) => `<button class="trap" data-trap="${i}">${windowLabel(w)}</button>`).join("")}</div>
          <p class="meta">${esc(t.trapsNote)}</p>` : `<p class="meta" style="margin-top:12px">${esc(t.noTraps)}</p>`}
      </section>

      <details class="pnl passport">
        <summary>${esc(t.passport)}</summary>
        <dl>
          <dt>${esc(t.pSource)}</dt><dd>${esc(pp.fuente)}</dd>
          <dt>${esc(t.pVariable)}</dt><dd>${esc(pp.producto)}</dd>
          <dt>${esc(t.pTool)}</dt><dd>${esc(pp.herramienta)}</dd>
          <dt>${esc(t.pBox)}</dt><dd>${pp.caja_pedida ? pp.caja_pedida.join(", ") + " " + esc(t.pBoxNote) : "—"}</dd>
          <dt>${esc(t.pData)}</dt><dd>${pp.puntos ? pp.puntos.map(([la, lo, id]) => `${esc(pointName(id))} (${la}, ${lo})`).join(" · ") : pp.caja_datos ? pp.caja_datos.join(", ") : "—"}</dd>
          <dt>${esc(t.pFile)}</dt><dd>${esc(pp.archivo)} · ${esc(pp.puntos ? t.pVerifyModis : pp.reconstruido ? t.pVerifyRecon : t.pVerifyOrig)}</dd>
          <dt>${esc(t.pMethod)}</dt><dd>${esc(pp.puntos ? t.pMethodModis : t.pMethodText)}</dd>
          <dt>${esc(t.pAutocorr)}</dt><dd>${esc(t.pAutocorrText(full.autocorr_lag1 === null ? "—" : fmt(full.autocorr_lag1, 2), fmt(full.factor_varianza_ar1, 2), fmtP(full.p_mk_simple)))}</dd>
          <dt>${esc(t.pMulti)}</dt><dd>${esc(t.pMultiText(index.series.length, full.q_bh === undefined ? "—" : fmtP(full.q_bh)))}</dd>
          <dt>${esc(t.pCode)}</dt><dd>${esc(pp.codigo)}</dd>
          <dt>${esc(t.pRepro)}</dt><dd>${pp.url_reproducir ? `<a href="${esc(pp.url_reproducir)}" target="_blank" rel="noopener">${esc(t.pOpenGiovanni)}</a>` : "—"}</dd>
        </dl>
      </details>
    </div>`;

  const chartEl = document.getElementById("chart")!;
  const drawChart = () => {
    chartEl.innerHTML = "";
    chartEl.append(state.raw ? rawChart(s, meta.unidad, chartEl.clientWidth || 800) : evidenceChart(s, meta.unidad, state.window, chartEl.clientWidth || 800));
  };
  drawChart();
  const wl = document.getElementById("wlen")!;
  wl.append(windowLength(s, wl.clientWidth || 420));
  document.getElementById("rawtoggle")!.addEventListener("click", () => { state.raw = !state.raw; renderEvidence(s); });

  const winInfo = () => {
    const el = document.getElementById("wininfo")!;
    const w = state.window;
    if (!w) {
      el.innerHTML = `<p class="wtitle">${esc(t.fullSeries(y0, y1))}</p><p>${esc(verdictShort(full.veredicto))}. ${esc(t.tapCell)}</p>`;
      return;
    }
    const isTrap = s.ventanas_que_enganan.some((x) => x.inicio === w.inicio && x.fin === w.fin);
    el.innerHTML = `
      <p class="wtitle">${windowLabel(w)} · ${w.fin - w.inicio + 1} ${esc(t.years)}</p>
      <p><strong>${esc(verdictShort(w.veredicto))}</strong>: ${fmtSigned(w.pendiente_decada, d)} ${esc(meta.unidad)} ${esc(t.factPerDecade)} (${esc(t.range)} ${fmtSigned(w.ic95_decada[0], d)} ${esc(t.to)} ${fmtSigned(w.ic95_decada[1], d)}), p = ${fmtP(w.p_mk)}.</p>
      ${isTrap ? `<p class="notice">${esc(trapText(w, full, meta))}</p>` : ""}
      <button class="txt-btn" id="clearwin">${esc(t.backFull)}</button>`;
    document.getElementById("clearwin")?.addEventListener("click", () => pick(null));
  };
  const matrixEl = document.getElementById("matrix")!;
  const pick = (w: Window | null) => {
    state.window = w; state.raw = false;
    matrixEl.innerHTML = "";
    matrixEl.append(windowMatrix(s, state.window, pick));
    drawChart(); winInfo();
  };
  matrixEl.append(windowMatrix(s, state.window, pick));
  winInfo();
  host.querySelectorAll<HTMLButtonElement>("[data-trap]").forEach((b) => b.addEventListener("click", () => {
    pick(s.ventanas_que_enganan[Number(b.dataset.trap)]);
    document.getElementById("chart")!.scrollIntoView({ behavior: "smooth", block: "center" });
  }));
}

/* ───────────── Recovery Ribbon (PHANTOM) ───────────── */

let rbStage: Stage | null = null;
let rbPlayed = false;
const TIP_SIDE = (id: string): { direction: L.Direction; offset: [number, number] } =>
  id === "montecristimontesecoa" ? { direction: "left", offset: [-10, 0] }
  : id === "montecristimontesecob" ? { direction: "top", offset: [0, -10] }
  : id === "sierramontecristi" ? { direction: "bottom", offset: [0, 10] }
  : { direction: "right", offset: [10, 0] };
const rb = { id: "sierramontecristi", fn: "gpp_modelo" as Fn, lane: -1, mode: "3d" as "3d" | "2d" | "map" };
const LL = (es: string, en: string) => (getLang() === "es" ? es : en);

async function viewRibbon() {
  const t = T();
  const view = document.getElementById("view")!;
  const [pts, ph] = await Promise.all([load<Puntos>("puntos.json"), load<Phantom>("phantom.json")]);
  const audits = ph.auditorias ?? [];
  const ids = POINT_ORDER.filter((id) => pts.z[id]);
  if (!ids.includes(rb.id)) rb.id = ids[0];
  const fns = (["gpp_modelo", "lst_menos_aire", "ndii_agua"] as Fn[]).filter((f) => pts.z[rb.id]?.[f]);
  if (!fns.includes(rb.fn)) rb.fn = fns[0];
  const lanes = buildLanes(pts, audits, rb.id, rb.fn);
  if (rb.lane < 0 || rb.lane >= lanes.length) {
    const pref = lanes.findIndex((l) => DISCORDANT.has(l.audit.veredicto));
    const imp = lanes.findIndex((l) => l.audit.veredicto !== "sin_impacto");
    rb.lane = pref >= 0 ? pref : imp >= 0 ? imp : Math.max(0, lanes.length - 1);
  }
  const fLabel = fnName(rb.fn);

  view.innerHTML = `
    <section class="rb" data-mode="${rb.mode}">
      <div class="rb-scene">
        <div class="rb-map" id="rb-map" aria-label="${esc(LL("Mapa de los lugares", "Map of the sites"))}"></div>
        <div class="rb-scrim" aria-hidden="true"></div>
        <div class="rb-stage" id="rb-stage"></div>
        <div class="rb-big" id="rb-big"></div>
      </div>
      <div class="rb-head rb-top">
        <div>
          <p class="crumb">Stellar Horizons<span aria-hidden="true">/</span>PHANTOM</p>
          <h1>Recovery Ribbon</h1>
          <p class="rb-q">${esc(LL("¿Vuelve el verdor antes que la función? Cada cinta es una sequía. Sus bordes son el verdor y la función; la superficie entre ellos es la brecha, del color de la señal que va delante.",
            "Does greenness come back before function? Each ribbon is a drought. Its edges are greenness and function; the surface between them is the gap, coloured by whichever signal leads."))}</p>
        </div>
        <div class="rb-ctrl">
          <div class="seg rb-modes" role="radiogroup" aria-label="${esc(LL("Forma de ver", "View"))}">
            ${([["3d", LL("Cintas 3D", "3D ribbons")], ["2d", LL("Brecha 2D", "2D gap")], ["map", LL("Lugares", "Sites")]] as const).map(([m, lab]) => `<button data-rbmode="${m}" class="${rb.mode === m ? "on" : ""}" role="radio" aria-checked="${rb.mode === m}">${esc(lab)}</button>`).join("")}
          </div>
          <div class="tabs" role="tablist" aria-label="${esc(LL("Lugar", "Site"))}">
            ${ids.map((id) => `<button class="tab ${id === rb.id ? "on" : ""}" data-rbid="${id}" role="tab" aria-selected="${id === rb.id}">${esc(NAMES[id])}</button>`).join("")}
          </div>
          <div class="tabs" role="tablist" aria-label="${esc(LL("Señal de función", "Function signal"))}">
            ${fns.map((f) => `<button class="tab ${f === rb.fn ? "on" : ""}" data-rbfn="${f}" role="tab" aria-selected="${f === rb.fn}">${esc(fnName(f))}</button>`).join("")}
          </div>
        </div>
      </div>

      <div class="rb-bottom">
      <div class="rb-bar">
        <div class="legend">
          <span><i class="ln" style="background:${GREEN}"></i>${esc(LL("Verdor (NDVI)", "Greenness (NDVI)"))}</span>
          <span><i class="ln" style="background:${FUNC}"></i>${esc(fLabel)}</span>
          <span><i class="sq" style="background:${GREEN};opacity:.5"></i>${esc(LL("brecha: el verdor va delante", "gap: greenness leads"))}</span>
          <span><i class="sq" style="background:${FUNC};opacity:.5"></i>${esc(LL("brecha: la función va delante", "gap: function leads"))}</span>
          <span><i class="sq" style="background:#e5566f;opacity:.7"></i>${esc(LL("sequía (SPI-3)", "drought (SPI-3)"))}</span>
          <span><i class="ln dash"></i>${esc(LL("recuperado: z ≥ −1", "recovered: z ≥ −1"))}</span>
        </div>
        <div class="rb-tools">
          <span class="readout num" id="rb-day"></span>
          <button class="txt-btn" id="rb-play">${esc(LL("▶ Reproducir la recuperación", "▶ Play the recovery"))}</button>
        </div>
      </div>
      <p class="meta">${esc(LL("Eje horizontal: días desde el inicio de cada sequía (−90 a 540). Altura: z. ", "Horizontal axis: days since each drought began (−90 to 540). Height: z. "))}${esc(LL("Arrastra para girar. Toca una fecha a la izquierda de una cinta, o elige abajo, para ver esa sequía con sus valores exactos.",
        "Drag to rotate. Tap a date at the left of a ribbon, or choose below, to see that drought with its exact values."))}</p>

      <div class="rb-lanes" role="tablist" aria-label="${esc(LL("Sequías", "Droughts"))}">
        ${lanes.map((l, i) => `<button class="tab ${i === rb.lane ? "on" : ""}" data-lane="${i}" role="tab" aria-selected="${i === rb.lane}"><i class="dot" style="background:${verdictColor(l.audit.veredicto)}"></i>${l.label}</button>`).join("")}
      </div>

      </div>
      <aside class="rb-panel">
        <div class="rb-card" id="rb-card"></div>
        <div class="pnl-h rb-2d-h"><h2 id="rb-2d-h"></h2><span class="meta">${esc(LL("2D · mismos valores", "2D · same values"))}</span></div>
        <div id="rb-2d" class="chart"></div>
      </aside>
    </section>`;

  const stageEl = document.getElementById("rb-stage")!;
  const dayEl = document.getElementById("rb-day")!;
  const playBtn = document.getElementById("rb-play") as HTMLButtonElement;
  rbStage?.destroy();
  rbStage = ribbonStage(stageEl, (i) => pickLane(i), (d) => {
    if (d > 540) { dayEl.textContent = ""; playBtn.textContent = LL("▶ Reproducir la recuperación", "▶ Play the recovery"); return; }
    dayEl.textContent = `${LL("día", "day")} ${Math.round(d)}`;
  });
  rbStage.setLanes(lanes, rb.lane);

  // ── El mapa de fondo: los lugares reales; el elegido queda unido a sus cintas ──
  const mapEl = document.getElementById("rb-map")!;
  const map = baseMap(mapEl, [18.8, -71.2], 8);
  map.attributionControl.setPosition("bottomleft");
  const sites = pts.puntos.filter((q) => ids.includes(q.id));
  const summary = (id: string) => {
    const ev = audits.filter((a) => a.id === id && a.veredicto !== "sin_impacto");
    const disc = ev.filter((a) => DISCORDANT.has(a.veredicto)).length;
    return LL(`${ev.length} sequías con impacto · ${disc} discordantes`, `${ev.length} droughts with impact · ${disc} discordant`);
  };
  for (const q of sites) {
    const on = q.id === rb.id;
    L.circleMarker([q.lat, q.lon], { radius: on ? 7 : 5, color: on ? FUNC : "#ffffff", weight: 2, fillColor: on ? FUNC : "#ffffff", fillOpacity: on ? 0.9 : 0.35 })
      .bindTooltip(rb.mode === "map" ? `<b>${esc(NAMES[q.id])}</b><br>${esc(summary(q.id))}` : esc(NAMES[q.id]), { permanent: rb.mode === "map" || on, ...TIP_SIDE(q.id), className: on ? "zone-tip on" : "zone-tip" })
      .on("click", () => { rb.id = q.id; rb.lane = -1; if (rb.mode === "map") rb.mode = "3d"; viewRibbon(); })
      .addTo(map);
  }
  const wide = innerWidth > 1100;
  map.fitBounds(L.latLngBounds(sites.map((q) => [q.lat, q.lon] as [number, number])), {
    paddingTopLeft: wide ? [rb.mode === "map" ? 120 : 520, 300] : [40, 40],
    paddingBottomRight: wide ? [480, 220] : [40, 40], maxZoom: 9, animate: false,
  });
  const here = sites.find((q) => q.id === rb.id);
  const anchor = () => { if (here && rbStage) { const c = map.latLngToContainerPoint([here.lat, here.lon]); rbStage.setAnchor(rb.mode === "3d" ? [c.x, c.y] : null); } };
  map.on("move zoom resize", anchor);
  anchor();

  const big = document.getElementById("rb-big")!;
  const drawBig = () => {
    if (rb.mode !== "2d" || !lanes[rb.lane]) { big.innerHTML = ""; return; }
    big.innerHTML = `<div class="pnl-h"><h2>${esc(NAMES[rb.id])} · ${LL("sequía", "drought")} ${lanes[rb.lane].label}</h2><span class="meta">${esc(LL("Pasa el cursor: fecha, cada z y la brecha", "Hover: date, each z and the gap"))}</span></div>`;
    const box = document.createElement("div");
    big.append(box);
    box.append(ribbon2D(lanes[rb.lane], fLabel, big.clientWidth - 40, Math.max(240, big.clientHeight - 80)));
  };
  view.querySelectorAll<HTMLButtonElement>("[data-rbmode]").forEach((b) => b.addEventListener("click", () => {
    rb.mode = b.dataset.rbmode as typeof rb.mode;
    rbStage?.stop();
    viewRibbon();
  }));
  if (rb.mode === "3d" && !rbPlayed && !matchMedia("(prefers-reduced-motion: reduce)").matches) {
    rbPlayed = true;
    setTimeout(() => { if (rbStage && !rbStage.playing()) { (document.getElementById("rb-play") as HTMLButtonElement | null)?.click(); } }, 600);
  }

  const renderDetail = () => {
    const l = lanes[rb.lane];
    if (!l) return;
    const a = l.audit;
    document.getElementById("rb-2d-h")!.textContent = `${NAMES[rb.id]} · ${LL("sequía", "drought")} ${l.label}`;
    const el2 = document.getElementById("rb-2d")!;
    el2.innerHTML = "";
    el2.append(ribbon2D(l, fLabel, el2.clientWidth || 380, el2.clientWidth < 500 ? 210 : 300));
    drawBig();
    const gd = a.ndvi_dias as number | null;
    const fd = a[`${rb.fn}_dias`] as number | null;
    const dt = gd !== null && fd !== null ? fd - gd : null;
    const yes = (b: unknown) => (b ? LL("sí", "yes") : LL("no", "no"));
    const comb = Math.round((a.estabilidad as number) * (a.combinaciones as number));
    document.getElementById("rb-card")!.innerHTML = `
      <div class="pnl-h"><h2>${esc(LL("Lo que dice la auditoría", "What the audit says"))}</h2><span class="meta">${a.evento_inicio.slice(0, 7)} – ${a.evento_fin.slice(0, 7)}</span></div>
      <p class="rb-verdict" style="color:${verdictColor(a.veredicto)}">${esc(t.verdictName[a.veredicto] ?? a.veredicto)}</p>
      <p class="vs">${esc(t.verdictWhy[a.veredicto] ?? "")}</p>
      <div class="kstrip three">
        <p><span>${esc(LL("verdor vuelve", "greenness back"))}</span><b class="num" style="color:${GREEN}">${!a.ndvi_impactado ? esc(LL("no cayó", "no drop")) : gd === null ? "—" : `${gd} d`}</b></p>
        <p><span>${esc(fLabel)} ${esc(LL("vuelve", "back"))}</span><b class="num" style="color:${FUNC}">${!a[`${rb.fn}_impactado`] ? esc(LL("no cayó", "no drop")) : fd === null ? "—" : `${fd} d`}</b></p>
        <p><span>Δt</span><b class="num">${dt === null ? "—" : `${dt > 0 ? "+" : ""}${dt} d`}</b></p>
      </div>
      <dl class="rb-facts">
        <dt>${esc(LL("¿Cayó el verdor?", "Did greenness drop?"))}</dt><dd>${yes(a.ndvi_impactado)}</dd>
        <dt>${esc(LL(`¿Cayó ${fLabel}?`, `Did ${fLabel} drop?`))}</dt><dd>${yes(a[`${rb.fn}_impactado`])}</dd>
        <dt>${esc(LL("¿Llegó otra sequía antes?", "Did another drought arrive first?"))}</dt><dd>${yes(a.colision)}</dd>
        <dt>${esc(LL("Se mantiene al cambiar la definición", "Holds when the definition changes"))}</dt><dd class="num">${comb} ${esc(LL("de", "of"))} ${a.combinaciones}</dd>
        <dt>${esc(LL("Observaciones válidas", "Valid observations"))}</dt><dd class="num">${Math.round(100 * ((a.ndvi_cobertura as number) ?? 0))} %</dd>
      </dl>
      <p class="meta">${esc(LL("En esta ficha los días se cuentan desde el fin de la sequía (negativo: volvió antes de que terminara); en las gráficas, desde su inicio.", "In this card days count from the end of the drought (negative: back before it ended); in the charts, from its start."))} ${esc(LL("z: desviación robusta de lo normal para esa época del año (mediana y MAD, 8 años o más), suavizada con mediana de 3. Impacto: z < −1,5 durante 3 observaciones; recuperado: z ≥ −1 durante 3. La GPP es salida del modelo MOD17 y usa el mismo FPAR que el verdor: no es una medición independiente.",
        "z: robust departure from normal for that time of year (median and MAD, 8+ years), smoothed with a median of 3. Impact: z < −1.5 for 3 observations; recovered: z ≥ −1 for 3. GPP is MOD17 model output and uses the same FPAR as greenness: it is not an independent measurement."))}</p>`;
  };
  const pickLane = (i: number) => {
    rb.lane = i;
    rbStage?.select(i);
    view.querySelectorAll<HTMLButtonElement>("[data-lane]").forEach((b) => { const on = Number(b.dataset.lane) === i; b.classList.toggle("on", on); b.setAttribute("aria-selected", String(on)); });
    renderDetail();
  };
  renderDetail();

  playBtn.addEventListener("click", () => {
    if (rbStage!.playing()) { rbStage!.stop(); return; }
    playBtn.textContent = LL("❚❚ Detener", "❚❚ Stop");
    rbStage!.play();
  });
  view.querySelectorAll<HTMLButtonElement>("[data-lane]").forEach((b) => b.addEventListener("click", () => pickLane(Number(b.dataset.lane))));
  view.querySelectorAll<HTMLButtonElement>("[data-rbid]").forEach((b) => b.addEventListener("click", () => { rb.id = b.dataset.rbid!; rb.lane = -1; viewRibbon(); }));
  view.querySelectorAll<HTMLButtonElement>("[data-rbfn]").forEach((b) => b.addEventListener("click", () => { rb.fn = b.dataset.rbfn as Fn; viewRibbon(); }));
}

/* ───────────── Auditoría de recuperación (Recovery Integrity) ───────────── */

// Marcas dibujadas (no emoji): sí, no, no aplica
const MARK: Record<string, string> = {
  ok: '<svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true"><path d="M3 8.5l3.2 3L13 4.5" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  bad: '<svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true"><path d="M4 4l8 8M12 4l-8 8" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"/></svg>',
  na: '<svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true"><path d="M4 8h8" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"/></svg>',
};

function auditKey(a: Audit) { return `${a.id}|${a.evento_inicio}`; }

function defaultAudit(auds: Audit[]): Audit | undefined {
  // La primera afirmación es la más reveladora: estrés invisible o interrumpida; si no, la más severa
  const pref = ["estres_invisible", "censurada", "fantasma", "verdor_tarde", "consistente"];
  for (const v of pref) {
    const c = auds.filter((a) => a.veredicto === v).sort((a, b) => a.evento_severidad_spi3 - b.evento_severidad_spi3)[0];
    if (c) return c;
  }
  return auds[0];
}

async function viewCases() {
  const t = T();
  const view = document.getElementById("view")!;
  const ph = await load<Phantom>(TEST_MODE ? "phantom-SINTETICO-prueba.json" : "phantom.json");
  const pts = index.puntos && !TEST_MODE ? await load<Puntos>("puntos.json") : null;
  const auds = (ph.auditorias ?? []).filter((a) => a.veredicto !== "sin_impacto");
  const done = ph.estado_modis === "procesado" && auds.length > 0;
  const count = (v: string) => auds.filter((a) => a.veredicto === v).length;

  if (!state.audit || !auds.some((a) => auditKey(a) === `${state.audit!.id}|${state.audit!.ev}`)) {
    const d = defaultAudit(auds);
    state.audit = d ? { id: d.id, ev: d.evento_inicio } : null;
    state.audited = false;
  }

  view.innerHTML = `
    ${TEST_MODE ? `<p class="test-banner">${esc(t.testBanner)}</p>` : ""}
    <div class="title-row">
      <h1>${esc(t.auditTitle)}</h1>
      <p>${esc(t.auditSub)}</p>
    </div>
    ${!done ? `<div class="grid"><section class="card s6"><h2>${esc(t.caseWaiting)}</h2><p class="explain">${t.caseWaitingText}</p></section></div>` : `
    <nav class="chapnav" aria-label="${esc(t.auditTitle)}">
      <a href="#c-discover" data-ch>${esc(t.chDiscover)}</a><a href="#c-evidence" data-ch>${esc(t.chEvidence)}</a><a href="#c-compare" data-ch>${esc(t.chCompare)}</a><a href="#c-verdict" data-ch>${esc(t.chVerdict)}</a>
    </nav>

    <section class="chapter" id="c-discover">
      <h2 class="ch-title">${esc(t.chDiscover)}</h2>
      <div class="card claim-card">
        <p class="claim" id="claim"></p>
        <div class="controls">
          <label>${esc(t.cPoint)} <select id="a-id">${POINT_ORDER.filter((id) => auds.some((a) => a.id === id)).map((id) => `<option value="${id}">${esc(pointName(id))}</option>`).join("")}</select></label>
          <label>${esc(t.cDrought)} <select id="a-ev"></select></label>
          <button class="reveal inline" id="audit-go">${esc(t.auditBtn)}</button>
        </div>
        <ol class="checklist" id="chk"></ol>
        <div class="verdict-box" id="vbox"></div>
      </div>
    </section>

    <section class="chapter" id="c-evidence">
      <div class="ch-head">
        <div><h2 class="ch-title">${esc(t.chEvidence)}</h2><p class="sub">${esc(t.evidenceSub)}</p></div>
        <div class="seg" role="radiogroup" aria-label="${esc(t.cSignal)}">
          <button data-fn="lst_menos_aire" class="${state.fn === "lst_menos_aire" ? "on" : ""}">${esc(t.sigLst)}</button>
          <button data-fn="gpp_modelo" class="${state.fn === "gpp_modelo" ? "on" : ""}">${esc(t.sigGpp)}</button>
          ${pts && Object.values(pts.z).some((z) => z.ndii_agua) ? `<button data-fn="ndii_agua" class="${state.fn === "ndii_agua" ? "on" : ""}">${esc(t.sigNdii)}</button>` : ""}
        </div>
      </div>
      <div class="grid">
        <section class="card s4">
          <div class="card-head"><h3>${esc(t.dualH)}</h3>
            <div class="legend"><span><i class="ln" style="background:#e6e6e6"></i>${esc(t.sigGreen)}</span><span><i class="ln" style="background:${AMBER}"></i><span class="fname"></span></span></div></div>
          <div id="dual" class="chart"></div>
          <h3 style="margin-top:14px">${esc(t.gapH)}</h3>
          <p class="sub">${esc(t.gapSub)}</p>
          <div id="gap" class="chart"></div>
        </section>
        <section class="card s2">
          <h3>${esc(t.hystH)}</h3>
          <p class="sub">${esc(t.hystSub)}</p>
          <div id="hyst" class="chart"></div>
          <div class="legend foot-note"><span><i class="ln" style="background:#949494"></i>${esc(t.phBefore)}</span><span><i class="ln" style="background:#e6e6e6"></i>${esc(t.phDuring)}</span><span><i class="ln" style="background:${AMBER}"></i>${esc(t.phAfter)}</span></div>
        </section>
      </div>
    </section>

    <section class="chapter" id="c-compare">
      <h2 class="ch-title">${esc(t.chCompare)}</h2>
      <p class="sub">${esc(t.compareSub)}</p>
      <div class="numbers wide">
        ${(["consistente", "estres_invisible", "solo_modelo", "censurada", "inconclusa", "fantasma"] as const).map((v) => `<p>${esc(t.verdictName[v])}<b>${count(v)}</b></p>`).join("")}
      </div>
      <div class="grid">
        <section class="card s6">
          <h3>${esc(t.ledgerH)}</h3>
          <p class="sub">${esc(t.ledgerSub)}</p>
          <div id="ledger" class="chart"></div>
          <div class="legend" style="margin-top:8px">${["C consistente", "E estres_invisible", "M solo_modelo", "I censurada", "? inconclusa", "P caida_posterior", "V verdor_tarde", "F fantasma"].map((x) => { const [g, k] = x.split(" "); return `<span><b>${g}</b>&nbsp;${esc(t.verdictName[k])}</span>`; }).join("")}</div>
        </section>
        <section class="card s3">
          <h3>${esc(t.quadH)}</h3>
          <p class="sub">${esc(t.quadSub)}</p>
          <div id="quad" class="chart"></div>
          <div class="legend foot-note"><span>● ${esc(t.sigGpp)}</span><span>▲ ${esc(t.sigLst)}</span><span><i class="dot" style="background:${AMBER}"></i>${esc(t.verdictName.fantasma)} / ${esc(t.verdictName.verdor_tarde)}…</span></div>
        </section>
        ${pts ? `
        <section class="card s3">
          <div class="card-head"><h3>${esc(t.mapH)}</h3>
            <div class="seg" role="radiogroup" aria-label="${esc(t.mapH)}">${["modis_ndvi", "modis_lst", "modis_gpp"].map((v) => `<button data-mapv="${v}" class="${state.mapVar === v ? "on" : ""}">${esc(varMeta(index, v).unidad === "NDVI" ? "NDVI" : v === "modis_lst" ? "LST" : "GPP")}</button>`).join("")}</div></div>
          <p class="sub">${esc(t.mapSub)}</p>
          <div id="pmap"></div>
          <table class="trend-list" id="pm-table" style="margin-top:10px"></table>
          <p class="small foot-note">${esc(t.qNote(pts.n_pruebas_mapa))}</p>
        </section>
        <section class="card s6">
          <div class="card-head">
            <div><h3>${esc(t.heatH)}</h3><p class="sub">${esc(t.heatSub)}</p></div>
            <div class="seg" role="radiogroup" aria-label="${esc(t.heatH)}">${["modis_ndvi", "modis_lst", "modis_gpp"].map((v) => `<button data-heat="${v}" class="${state.heatVar === v ? "on" : ""}"><span class="long">${esc(varMeta(index, v).nombre)}</span><span class="short">${v === "modis_ndvi" ? "NDVI" : v === "modis_lst" ? "LST" : "GPP"}</span></button>`).join("")}</div>
          </div>
          <div id="heat" class="chart"></div>
          <div class="legend" style="margin-top:10px"><span><i class="sq" style="background:${AMBER}"></i>${esc(t.worse)}</span><span><i class="sq" style="background:#a9a9a9"></i>${esc(t.better)}</span><span><i class="sq none"></i>${esc(t.noData)}</span></div>
        </section>` : ""}
      </div>
    </section>

    <section class="chapter" id="c-verdict">
      <h2 class="ch-title">${esc(t.chVerdict)}</h2>
      <div class="grid">
        <section class="card s6">
          <h3>${esc(t.verdictH)}</h3>
          <p class="claim small-claim">${esc(t.verdictLead(auds.length, count("fantasma"), count("estres_invisible"), count("censurada"), count("inconclusa")))}</p>
          <p class="explain">${esc(t.verdictClaimsText)}</p>
        </section>
        <section class="card s6">
          <div class="two-col">
            <div><h3>${esc(t.howH)}</h3><p class="explain">${t.howP1}</p><p class="explain">${esc(t.howP2)}</p></div>
            <div><h3>${esc(t.notClaimH)}</h3><p class="explain">${esc(t.notClaim)}</p></div>
          </div>
        </section>
        <section class="card s6">
          <h3>${esc(t.droughtsH)}</h3>
          <p class="sub">${esc(t.droughtsNote)}</p>
          ${ph.sequias.map((d, i) => `<p class="group">${esc(regionMeta(index, d.region).nombre)}</p><div class="chart" id="spi${i}"></div>`).join("")}
        </section>
      </div>
    </section>`}`;

  ph.sequias.forEach((d, i) => {
    const el = document.getElementById(`spi${i}`);
    if (el) el.append(spiChart(d, el.clientWidth || 800));
  });
  if (!done) return;

  const $ = <E extends HTMLElement>(id: string) => document.getElementById(id) as E;
  const draw = (id: string, f: (w: number) => Element) => {
    const el = document.getElementById(id);
    if (!el) return;
    el.innerHTML = "";
    el.append(f(el.clientWidth || 600));
  };
  const current = () => auds.find((a) => a.id === state.audit!.id && a.evento_inicio === state.audit!.ev)!;

  const fillEvents = () => {
    const id = $<HTMLSelectElement>("a-id").value;
    $<HTMLSelectElement>("a-ev").innerHTML = auds.filter((a) => a.id === id)
      .map((a) => `<option value="${a.evento_inicio}">${a.evento_inicio.slice(0, 7)}</option>`).join("");
  };

  const renderClaim = () => {
    const a = current();
    $("claim").textContent = t.claim(pointName(a.id), a.evento_inicio.slice(0, 4));
    $<HTMLSelectElement>("a-id").value = a.id;
    fillEvents();
    $<HTMLSelectElement>("a-ev").value = a.evento_inicio;
    const box = $("vbox");
    const chk = $("chk");
    if (!state.audited) { chk.innerHTML = ""; box.innerHTML = ""; box.className = "verdict-box"; return; }
    const sig = (k: string) => {
      if (!a[`${k}_impactado`]) return { cls: "na", txt: t.resNotHit };
      const r = a[`${k}_recupera`] as string | null;
      return r ? { cls: "ok", txt: t.resYes(r, a[`${k}_dias`] as number) } : { cls: "bad", txt: t.resNo };
    };
    const covs = ["ndvi", "gpp_modelo", "lst_menos_aire", "ndii_agua"].filter((k) => `${k}_cobertura` in a).map((k) => (a[`${k}_cobertura`] as number) ?? 0);
    const stableN = Math.round(a.estabilidad * a.combinaciones);
    const items = [
      { l: t.chkGreen, ...sig("ndvi") },
      { l: t.chkEvi, ...sig("evi") },
      { l: t.chkGpp, ...sig("gpp_modelo") },
      { l: t.chkLst, ...sig("lst_menos_aire") },
      ...("ndii_agua_impactado" in a ? [{ l: t.chkNdii, ...sig("ndii_agua") }] : []),
      a.colision ? { l: t.chkNext, cls: "bad", txt: t.resNextBad } : { l: t.chkNext, cls: "ok", txt: t.resNextOk },
      { l: t.chkStable, cls: a.estabilidad >= 0.6 ? "ok" : "bad", txt: t.resStable(stableN, a.combinaciones) },
      { l: t.chkQc, cls: a.calidad_ok ? "ok" : "bad", txt: t.resQc(Math.min(...covs)) },
    ];
    chk.innerHTML = items.map((it, i) => `<li class="${it.cls}" style="--i:${i}"><span class="mk">${MARK[it.cls]}</span><span class="lbl">${esc(it.l)}</span><span class="res">${esc(it.txt)}</span></li>`).join("");
    const disc = DISCORDANT.has(a.veredicto);
    box.className = `verdict-box shown ${disc ? "disc" : ""}`;
    box.style.setProperty("--i", String(items.length));
    const reason = a.motivo_inconclusa === "definicion" ? ` (${t.reasonDef})` : a.motivo_inconclusa === "calidad" ? ` (${t.reasonQc})` : "";
    box.innerHTML = `<p class="vlabel">${esc(t.verdictLabel)}</p><p class="vname">${esc(t.verdictName[a.veredicto] ?? a.veredicto)}${esc(reason)}</p><p class="explain">${esc(t.verdictWhy[a.veredicto] ?? "")}</p>`;
  };

  const renderEvidenceCh = () => {
    const a = current();
    const fname = { gpp_modelo: t.sigGpp, lst_menos_aire: t.sigLst, ndii_agua: t.sigNdii }[state.fn];
    document.querySelectorAll(".fname").forEach((e) => { e.textContent = fname; });
    const z = pts?.z[a.id];
    if (!z || !z[state.fn]) return;
    const common = { green: z.ndvi, func: z[state.fn], start: a.evento_inicio, end: a.evento_fin, stop: a.fin_ventana };
    draw("dual", (w) => dualTimeline({ ...common, greenRec: a.ndvi_recupera as string | null, funcRec: a[`${state.fn}_recupera`] as string | null, threshold: -1, width: w }));
    draw("gap", (w) => gapIndex({ ...common, width: w }));
    draw("hyst", (w) => hysteresis({ ...common, width: w }));
  };

  const renderLedger = () => draw("ledger", (w) => ledger(auds, POINT_ORDER, NAMES, w, current(), (a) => {
    state.audit = { id: a.id, ev: a.evento_inicio }; state.audited = true;
    renderClaim(); renderEvidenceCh(); renderLedger();
    document.getElementById("c-discover")!.scrollIntoView({ behavior: "smooth", block: "start" });
  }));

  $("a-id").addEventListener("change", () => {
    fillEvents();
    state.audit = { id: $<HTMLSelectElement>("a-id").value, ev: $<HTMLSelectElement>("a-ev").value };
    state.audited = false; renderClaim(); renderEvidenceCh(); renderLedger();
  });
  $("a-ev").addEventListener("change", () => {
    state.audit = { id: $<HTMLSelectElement>("a-id").value, ev: $<HTMLSelectElement>("a-ev").value };
    state.audited = false; renderClaim(); renderEvidenceCh(); renderLedger();
  });
  $("audit-go").addEventListener("click", () => { state.audited = true; renderClaim(); });
  view.querySelectorAll<HTMLButtonElement>("[data-fn]").forEach((b) => b.addEventListener("click", () => {
    state.fn = b.dataset.fn as State["fn"];
    view.querySelectorAll("[data-fn]").forEach((x) => x.classList.toggle("on", x === b));
    renderEvidenceCh();
  }));
  view.querySelectorAll<HTMLAnchorElement>("[data-ch]").forEach((a) => a.addEventListener("click", (e) => {
    e.preventDefault();
    document.querySelector(a.getAttribute("href")!)?.scrollIntoView({ behavior: "smooth", block: "start" });
  }));

  renderClaim();
  renderEvidenceCh();
  renderLedger();
  draw("quad", (w) => quadrant(auds, NAMES, w));
  if (pts) {
    const regionOf = Object.fromEntries(pts.puntos.map((p) => [p.id, p.region]));
    const droughts = ph.sequias.flatMap((d) => d.eventos.map((e) => ({ region: d.region, a: e.inicio, b: e.fin })));
    const drawHeat = () => draw("heat", (w) => heatmap(pts, state.heatVar, WORSE_IS_HIGH[state.heatVar], POINT_ORDER, NAMES, droughts, regionOf, w));
    drawHeat();
    view.querySelectorAll<HTMLButtonElement>("[data-heat]").forEach((b) => b.addEventListener("click", () => {
      state.heatVar = b.dataset.heat!;
      view.querySelectorAll("[data-heat]").forEach((x) => x.classList.toggle("on", x === b));
      drawHeat();
    }));
    drawPointMap(pts);
    view.querySelectorAll<HTMLButtonElement>("[data-mapv]").forEach((b) => b.addEventListener("click", () => {
      state.mapVar = b.dataset.mapv!;
      view.querySelectorAll("[data-mapv]").forEach((x) => x.classList.toggle("on", x === b));
      drawPointMap(pts);
    }));
  }
}

function drawPointMap(pts: Puntos) {
  const t = T();
  const el = document.getElementById("pmap");
  if (!el) return;
  const old = maps.findIndex((m) => m.getContainer() === el);
  if (old >= 0) maps.splice(old, 1)[0].remove();
  const map = baseMap(el, [18.8, -71.0], 7);
  const v = state.mapVar;
  const meta = varMeta(index, v);
  const d = digitsFor(meta);
  const rows = POINT_ORDER.map((id) => pts.puntos.find((p) => p.id === id)).filter(Boolean) as Puntos["puntos"];
  const bounds: L.LatLng[] = [];
  for (const p of rows) {
    const tr = p.tendencias[v];
    if (!tr) continue;
    const worse = WORSE_IS_HIGH[v] ? tr.pendiente_decada > 0 : tr.pendiente_decada < 0;
    const sig = tr.p_mk < 0.05 && (tr.ic95_decada[0] > 0 || tr.ic95_decada[1] < 0);
    const color = worse ? AMBER : "#e6e6e6";
    L.circleMarker([p.lat, p.lon], { radius: 9, color, weight: 2.5, fillColor: color, fillOpacity: sig ? 0.95 : 0 })
      .bindTooltip(`${pointName(p.id)}: ${fmtSigned(tr.pendiente_decada, d)} ${meta.unidad} ${t.factPerDecade} · p = ${fmtP(tr.p_mk)}`)
      .addTo(map);
    bounds.push(L.latLng(p.lat, p.lon));
  }
  if (bounds.length) map.fitBounds(L.latLngBounds(bounds).pad(0.35), { maxZoom: 9, animate: false });
  document.getElementById("pm-table")!.innerHTML = `
    <thead><tr><th>${esc(t.thPoint)}</th><th class="num">${esc(t.thSlope)}</th><th class="num">${esc(t.thP)}</th><th class="num">${esc(t.thQ)}</th></tr></thead>
    <tbody>${rows.map((p) => { const tr = p.tendencias[v]; return tr ? `
      <tr><td>${esc(pointName(p.id))}</td><td class="num">${fmtSigned(tr.pendiente_decada, d)}</td><td class="num">${fmtP(tr.p_mk)}</td><td class="num">${tr.q_bh === undefined ? "—" : fmtP(tr.q_bh)}</td></tr>` : ""; }).join("")}</tbody>`;
}

/* ───────────── Cómo funciona ───────────── */

function viewMethod() {
  const t = T();
  const view = document.getElementById("view")!;
  view.innerHTML = `
    <div class="title-row">
      <h1>${esc(t.methodH1)}</h1>
      <p>${esc(t.methodLede)}</p>
    </div>
    <div class="grid">
      <section class="card s6 glossary"><dl>${t.glossary.map(([a, b]) => `<dt>${esc(a)}</dt><dd>${esc(b)}</dd>`).join("")}</dl></section>
      <section class="card s6">
        <h2>${esc(t.limitsH)}</h2>
        <p class="explain">${esc(t.limits)}</p>
        <p class="small foot-note">${esc(t.updated(index.generado))}</p>
      </section>
    </div>`;
}

/* ───────────── Router ───────────── */

async function route(scrollTop = true) {
  const r = (location.hash.replace("#", "") || "investigar") as "investigar" | "ribbon" | "expedientes" | "metodo";
  setNav(r);
  stopPlay();
  clearMaps();
  try {
    if (r !== "ribbon") { rbStage?.destroy(); rbStage = null; }
    if (r === "expedientes") await viewCases();
    else if (r === "ribbon") await viewRibbon();
    else if (r === "metodo") viewMethod();
    else await viewInvestigate();
  } catch (e) {
    document.getElementById("view")!.innerHTML = `<div class="title-row"><h1>${esc(T().loadError)}</h1><p>${esc(String(e))}</p></div>`;
  }
  if (scrollTop) window.scrollTo({ top: 0 });
}

async function start() {
  shell();
  index = await load<Index>("index.json");
  window.addEventListener("hashchange", () => {
    if (["#investigar", "#ribbon", "#expedientes", "#metodo", ""].includes(location.hash)) route();
  });
  let timer: number | undefined;
  let lastW = window.innerWidth;
  window.addEventListener("resize", () => {
    if (Math.abs(window.innerWidth - lastW) < 40) return;
    lastW = window.innerWidth;
    clearTimeout(timer);
    timer = window.setTimeout(() => route(false), 250);
  });
  await route();
}

start();
