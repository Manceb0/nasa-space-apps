import "leaflet/dist/leaflet.css";
import "./style.css";
import L from "leaflet";
import {
  DISCORDANT, dualTimeline, evidenceChart, gapIndex, heatmap, hysteresis, ledger, monthTimeline, quadrant, rawChart, spiChart, uncertaintyBar, windowLength, windowMatrix,
} from "./charts";
import { load, type Audit, type Index, type Phantom, type Puntos, type Series, type Window } from "./data";
import { T, getLang, regionMeta, setLang, varMeta } from "./i18n";
import { pillNav, wirePillNav } from "./pillnav";
import { type Grid } from "./field";
import { terrain3d } from "./terrain3d";
import { provinceStats, type ProvStat } from "./provincias";
import { destroyTrends, openLand, viewTrends } from "./tendencias/vista";
import { destroyAudit, viewAudit } from "./auditoria/vista";
import { destroyPreparation, viewPreparation } from "./preparacion/vista";
import { viewMethodV2 } from "./metodo/vista";
import { viewAnswer } from "./respuesta/vista";
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
const AMBER = "#ff9f0a";

const esc = (s: string) => s.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]!));

function clearMaps() { while (maps.length) { const m = maps.pop()!; m.stop(); m.off(); m.remove(); } }

function baseMap(el: HTMLElement, center: [number, number], zoom: number): L.Map {
  const m = L.map(el, { zoomControl: true, attributionControl: true, scrollWheelZoom: false, zoomSnap: 0.25 }).setView(center, zoom);
  L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", {
    maxZoom: 16, attribution: "Imagen: Esri, Maxar, Earthstar Geographics",
  }).addTo(m);
  maps.push(m);
  return m;
}

export const ICON: Record<string, string> = {
  investigar: '<path d="M2.75 5.25l4.75-2 5 2 4.75-2v11.5l-4.75 2-5-2-4.75 2z"/><path d="M7.5 3.25v11.5M12.5 5.25v11.5"/>',
  expedientes: '<path d="M3.5 5.5l1.5 1.5 2.5-2.5M3.5 11.5l1.5 1.5 2.5-2.5"/><path d="M10.5 6h6M10.5 12h6M3.5 16.5h13"/>',
  ribbon: '<path d="M2.5 8c2.5-4 5-4 7.5 0s5 4 7.5 0"/><path d="M2.5 13c2.5-4 5-4 7.5 0s5 4 7.5 0"/><path d="M2.5 8v5M17.5 8v5"/>',
  metodo: '<path d="M3 4.75c2.5-1 5-1 7 .5 2-1.5 4.5-1.5 7-.5v11c-2.5-1-5-1-7 .5-2-1.5-4.5-1.5-7-.5z"/><path d="M10 5.25v11"/>',
};

function shell(): void {
  const t = T();
  document.title = t.title;
  app.innerHTML = `
    ${pillNav({
      logo: `<svg viewBox="0 0 32 32" aria-hidden="true"><path d="M16 2.5l2.3 8.2 8.2 2.3-8.2 2.3L16 23.5l-2.3-8.2-8.2-2.3 8.2-2.3z" fill="${AMBER}"/><path d="M2.5 28.5c7.5-4.6 19.5-4.6 27 0" stroke="#ffffff" stroke-width="2.2" fill="none" stroke-linecap="round"/></svg>`,
      logoAlt: `Stellar Horizons · ${esc(t.brand)}`, logoHref: "#tendencias", ariaLabel: esc(t.brand),
      items: [
        { key: "tendencias", href: "#tendencias", label: getLang() === "es" ? "Tendencias" : "Trends", short: getLang() === "es" ? "Tendencias" : "Trends" },
        { key: "respuesta", href: "#respuesta", label: getLang() === "es" ? "La respuesta" : "The answer", short: getLang() === "es" ? "Respuesta" : "Answer" },
        { key: "auditoria", href: "#auditoria", label: esc(t.navAudit), short: esc(t.navAudit) },
        { key: "metodo", href: "#metodo", label: esc(t.navMethod), short: getLang() === "es" ? "Método" : "Method" },
      ],
      extra: `<button class="pill-nav__lang pill-nav__surface" id="lang" aria-label="${esc(t.langSwitchLabel)}" title="${esc(t.langSwitchLabel)}" lang="${getLang() === "es" ? "en" : "es"}">${getLang() === "es" ? "EN" : "ES"}<span class="pill-nav__rim"></span></button>`,
    })}
    <main id="view"></main>
    <footer class="foot"><p>${esc(t.team)} · ${esc(t.footer)}</p></footer>`;
  pnav = wirePillNav(app);
  document.getElementById("lang")!.addEventListener("click", () => {
    setLang(getLang() === "es" ? "en" : "es");
    shell();
    route(false);
  });
}

let pnav: { setActive: (k: string) => void } | null = null;
function setNav(r: string) {
  pnav?.setActive(r);
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
  const spiS = ph?.sequias.find((d) => d.region === state.region)?.spi3;
  const startMonth = (() => {
    const e = droughts[0];
    if (!e || !spiS) return "2024-12";
    let best = e.inicio.slice(0, 7), bv = Infinity;
    spiS.meses.forEach((m, k) => { const v = spiS.valores[k]; if (m >= e.inicio.slice(0, 7) && m <= e.fin.slice(0, 7) && v !== null && v < bv) { bv = v; best = m; } });
    return best;
  })();

  view.innerHTML = `
    <div class="con-head">
      <div>
        <p class="crumb">Stellar Horizons<span aria-hidden="true">/</span>${esc(t.brand)}</p>
        <h1>${esc(rmeta.nombre)}</h1>
        <p class="con-sub">${esc(vmeta.nombre)} · ${y0}–${y1} · ${esc(vmeta.fuente)}</p>
      </div>
      <div class="rb-ctrl pills">
        ${pillSelect("inv-var", t.whatQ.replace(/[¿?]/g, ""), "", `<optgroup label="${esc(t.groupClimate)}">${climate.map((k) => `<option value="${k}" ${k === state.variable ? "selected" : ""}>${esc(shortName(k))}</option>`).join("")}</optgroup><optgroup label="${esc(t.groupVegShort)}">${veg.map((k) => `<option value="${k}" ${k === state.variable ? "selected" : ""}>${esc(shortName(k))}</option>`).join("")}</optgroup>`)}
        ${pillSelect("inv-reg", t.whereH, PIN, Object.keys(index.regiones).map((k) => `<option value="${k}" ${k === state.region ? "selected" : ""}>${esc(regionMeta(index, k).nombre)}</option>`).join(""))}
      </div>
    </div>


    <div class="console">
      <section class="pnl map-pnl" aria-label="${esc(t.mapLabel)}">
        <div id="map"></div>
        <p class="map-note" id="mapcap"></p>
        <div class="t3-hint" id="t3-hint">
          <span>${esc(LL("Arrastra para mover · Ctrl + arrastrar para girar e inclinar · Toca un lugar para bajar a su terreno", "Drag to move · Ctrl + drag to rotate and tilt · Tap a site to fly down to its terrain"))}</span>
          <button class="txt-btn" id="t3-country">${esc(LL("Ver todo el país", "See the whole country"))}</button>
        </div>
        <div class="map-tools">
          <div class="seg-pill" role="radiogroup" aria-label="${esc(LL("Estilo del mapa", "Map style"))}">
            ${([["3d", "3D"], ["plano", LL("Plano", "Flat")], ["oscuro", LL("Oscuro", "Dark")]] as const).map(([k, l]) => `<button data-mmode="${k}" class="${mapMode === k ? "on" : ""}" role="radio" aria-checked="${mapMode === k}">${l}</button>`).join("")}
          </div>
          <div class="seg-pill" role="radiogroup" aria-label="${esc(LL("Qué mostrar", "What to show"))}">
            ${([["seco", LL("Sequías", "Droughts")], ["extremo", LL("Lluvias extremas", "Extreme rain")], ["cambio", LL("¿Van a más?", "Getting worse?")], ["mes", LL("Lluvia del mes", "Monthly rain")]] as const).map(([k, l]) => `<button data-mlayer="${k}" class="${mapLayer === k ? "on" : ""}" role="radio" aria-checked="${mapLayer === k}">${l}</button>`).join("")}
          </div>
          <p class="map-legend" id="map-legend"></p>
        </div>
        <div class="field-hud" aria-live="polite">
          <p class="field-cap">${esc(LL("Mes en el mapa", "Month on the map"))}</p>
          <p class="field-month num loading" id="f-month">${esc(LL("Cargando lluvia…", "Loading rain…"))}</p>
          <p class="field-leg">${esc(LL("Lluvia del mes frente a lo normal. Cada punto es una celda IMERG de 0,1° (unos 11 km).", "Monthly rain against normal. Each dot is one 0.1° IMERG cell (about 11 km)."))}</p>
          <p class="field-key"><i style="background:#ff453a"></i>${esc(LL("mucho más seca", "much drier"))}<i style="background:#ff9f0a"></i>${esc(LL("más seca", "drier"))}<i style="background:#0a84ff"></i>${esc(LL("más húmeda", "wetter"))}</p>
          <p class="field-src">NASA GPM IMERG V07 · Huffman et al. 2023</p>
        </div>
      </section>

      <button class="drawer-tab" id="drawer-tab" aria-expanded="true" aria-controls="side-col" title="${esc(LL("Esconder o mostrar el panel", "Hide or show the panel"))}"><svg viewBox="0 0 12 12" aria-hidden="true"><path d="M4.5 3l3 3-3 3" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/></svg></button>
      <aside class="side-col" id="side-col">
        <section class="pnl verdict-pnl" id="verdict" aria-live="polite"></section>
<section class="pnl prov-pnl" id="prov-card" aria-live="polite"></section>
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

  document.getElementById("inv-var")!.addEventListener("change", (e) => { state.variable = (e.target as HTMLSelectElement).value; resetInvestigation(); route(false); });
  document.getElementById("inv-reg")!.addEventListener("change", (e) => { state.region = (e.target as HTMLSelectElement).value; resetInvestigation(); route(false); });
  view.querySelectorAll<HTMLButtonElement>("[data-var]").forEach((b) => b.addEventListener("click", () => {
    state.variable = b.dataset.var!; resetInvestigation(); route(false);
  }));
  view.querySelectorAll<HTMLButtonElement>("[data-reg]").forEach((b) => b.addEventListener("click", () => {
    state.region = b.dataset.reg!; resetInvestigation(); route(false);
  }));

  // ── El mapa en 3D: relieve real, zonas exactas, lugares y el campo de lluvia ──
  zone = { paths: [], label: null, name: regionMeta(index, state.region).nombre };
  t3?.destroy();
  const ptsAll = await load<Puntos>("puntos.json").catch(() => null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const provFC = await load<any>("limites/provincias.geojson").catch(() => null);
  t3 = terrain3d(document.getElementById("map")!, {
    zones: all.map((z) => {
      const pp = z.pasaporte;
      return { id: z.region, name: regionMeta(index, z.region).nombre, req: pp.caja_pedida,
        data: pp.caja_datos && pp.caja_datos[0] !== pp.caja_datos[2] ? pp.caja_datos : pp.caja_pedida, on: z.region === state.region };
    }),
    sites: (ptsAll?.puntos ?? []).map((q) => ({ id: q.id, name: pointName(q.id), lat: q.lat, lon: q.lon, on: q.region === state.region })),
    onZone: (id) => { if (id !== state.region) { state.region = id; resetInvestigation(); route(false); } },
    onSite: (id) => { rb.id = id; rb.lane = -1; },
    cellLabel: (mes, mm, pct) => `${mes} · ${mm === null ? "—" : `${fmt(mm, 0)} mm`}${pct === null ? "" : ` · ${pct} % ${LL("de lo normal", "of normal")}`}`,
    siteAction: LL("Ver su recuperación →", "See its recovery →"),
    provinces: provFC ?? undefined,
    onProvince: (id) => pickProv(id, true),
  });
  const hint = document.getElementById("t3-hint");
  t3.map.once("mousedown", () => hint?.classList.add("gone"));
  setTimeout(() => hint?.classList.add("gone"), 8000);
  t3.map.once("touchstart", () => hint?.classList.add("gone"));
  document.getElementById("t3-country")?.addEventListener("click", () => t3?.country(2200));
  const fMonth = document.getElementById("f-month")!;
  let fieldReady = false;
  const showField = (mes: string) => {
    if (!fieldReady || !t3) return;
    t3.setField(mes);
    if (fMonth.dataset.m !== mes) { fMonth.dataset.m = mes; fMonth.textContent = fmtMonth(mes); fMonth.classList.remove("flip", "loading"); void fMonth.offsetWidth; fMonth.classList.add("flip"); }
    view.querySelectorAll(".dm.on").forEach((x) => x.classList.remove("on"));
    view.querySelector(`[data-month="${mes}"]`)?.classList.add("on");
  };
  // ── Provincias: coropletas, ficha y controles del mapa ──
  let stats: ProvStat[] = [];
  const consoleEl = view.querySelector<HTMLElement>(".console")!;
  const legend = document.getElementById("map-legend")!;
  const provCard = document.getElementById("prov-card")!;
  const ramp = (a: number[], b: number[], t: number, al: number) => `rgba(${a.map((v, k) => Math.round(v + (b[k] - v) * t)).join(",")},${al})`;
  const metric = (st: ProvStat) => (mapLayer === "seco" ? st.dryA + st.dryB : mapLayer === "extremo" ? st.wetA + st.wetB : st.dryB - st.dryA);
  const applyLayer = () => {
    if (!t3) return;
    consoleEl.dataset.layer = mapLayer;
    t3.setLayer(mapLayer === "mes" ? "rain" : "prov");
    if (mapLayer === "mes" || !stats.length) {
      legend.innerHTML = `<i class="lg lg-rain"></i>${esc(LL("más seca · normal · más húmeda que lo normal de ese mes", "drier · normal · wetter than normal for that month"))}`;
      return;
    }
    const vals = stats.map(metric);
    const lo = Math.min(...vals), hi = Math.max(...vals), m = Math.max(Math.abs(lo), Math.abs(hi), 1);
    const colors: Record<string, string> = {};
    stats.forEach((st, k) => {
      const v = vals[k];
      colors[st.id] = mapLayer === "seco" ? ramp([255, 214, 10], [255, 69, 58], (v - lo) / Math.max(1, hi - lo), 0.25 + 0.6 * (v - lo) / Math.max(1, hi - lo))
        : mapLayer === "extremo" ? ramp([100, 210, 255], [10, 132, 255], (v - lo) / Math.max(1, hi - lo), 0.25 + 0.6 * (v - lo) / Math.max(1, hi - lo))
        : v >= 0 ? `rgba(255,69,58,${(0.15 + 0.7 * v / m).toFixed(2)})` : `rgba(48,209,88,${(0.15 + 0.7 * -v / m).toFixed(2)})`;
    });
    t3.setChoro(colors);
    legend.innerHTML = mapLayer === "seco"
      ? `<i class="lg lg-dry"></i>${esc(LL(`meses muy secos, 2001–2024: de ${lo} a ${hi}`, `very dry months, 2001–2024: ${lo} to ${hi}`))}`
      : mapLayer === "extremo"
        ? `<i class="lg lg-wet"></i>${esc(LL(`meses de lluvia extrema, 2001–2024: de ${lo} a ${hi}`, `extreme-rain months, 2001–2024: ${lo} to ${hi}`))}`
        : `<i class="lg lg-chg"></i>${esc(LL("meses muy secos: 2013–2024 frente a 2001–2012 (rojo: más; verde: menos)", "very dry months: 2013–2024 vs 2001–2012 (red: more; green: fewer)"))}`;
  };
  const bboxOf = (id: string): [[number, number], [number, number]] | undefined => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const f = provFC?.features.find((x: any) => x.properties.shapeID === id);
    if (!f) return undefined;
    const polys = f.geometry.type === "Polygon" ? [f.geometry.coordinates] : f.geometry.coordinates;
    let x0 = 180, y0 = 90, x1 = -180, y1 = -90;
    for (const pl of polys) for (const [x, y] of pl[0]) { x0 = Math.min(x0, x); y0 = Math.min(y0, y); x1 = Math.max(x1, x); y1 = Math.max(y1, y); }
    return [[x0, y0], [x1, y1]];
  };
  const defaultProv = () => {
    const want = state.region === "jaragua" ? "Pedernales" : "Monte Cristi";
    return (stats.find((x) => x.name === want) ?? stats[0]).id;
  };
  const delta = (a: number, b: number, worseUp: boolean) => {
    const d = b - a;
    const cls = d === 0 ? "eq" : (d > 0) === worseUp ? "bad" : "good";
    return `<span class="dl ${cls}">${d > 0 ? "▲" : d < 0 ? "▼" : "="} ${Math.abs(d)}</span>`;
  };
  const pickProv = (id: string, fly: boolean) => {
    const st = stats.find((x) => x.id === id);
    if (!st || !t3) return;
    t3.selectProvince(id, fly ? bboxOf(id) : undefined);
    const yrs = Array.from({ length: st.dryYear.length }, (_, k) => 2001 + k);
    const mx = Math.max(1, ...st.dryYear, ...st.wetYear);
    const W = 340, H = 132, mid = 64, bw = W / yrs.length;
    const bars = yrs.map((y, k) => {
      const hd = (st.dryYear[k] / mx) * 52, hw = (st.wetYear[k] / mx) * 52;
      return `<g class="yb" data-year="${y}" tabindex="0" role="button" aria-label="${y}: ${st.dryYear[k]} ${LL("meses muy secos", "very dry months")}, ${st.wetYear[k]} ${LL("de lluvia extrema", "of extreme rain")}" style="--i:${k}">
        <rect x="${k * bw}" y="0" width="${bw}" height="${H}" fill="transparent"/>
        ${hd ? `<rect class="bd" x="${k * bw + 2}" y="${mid - hd}" width="${bw - 4}" height="${hd}" rx="${Math.min(3, (bw - 4) / 2)}"/>` : ""}
        ${hw ? `<rect class="bw" x="${k * bw + 2}" y="${mid + 2}" width="${bw - 4}" height="${hw}" rx="${Math.min(3, (bw - 4) / 2)}"/>` : ""}
      </g>`;
    }).join("");
    provCard.innerHTML = `
      <div class="pnl-h"><h2>${esc(st.name)}</h2><span class="meta">${esc(LL("provincia", "province"))}</span></div>
      <div class="pc-stats">
        <div><p class="pc-l">${esc(LL("Meses muy secos", "Very dry months"))}</p><p class="pc-v"><b>${st.dryA}</b><span>→</span><b>${st.dryB}</b>${delta(st.dryA, st.dryB, true)}</p><p class="pc-s">2001–12 → 2013–24</p></div>
        <div><p class="pc-l">${esc(LL("Lluvia extrema", "Extreme rain"))}</p><p class="pc-v"><b>${st.wetA}</b><span>→</span><b>${st.wetB}</b>${delta(st.wetA, st.wetB, true)}</p><p class="pc-s">${esc(LL("meses", "months"))} · 2001–12 → 2013–24</p></div>
      </div>
      <svg class="pc-bars" viewBox="0 0 ${W} ${H}" role="group" aria-label="${esc(LL("Meses muy secos (arriba) y de lluvia extrema (abajo) por año", "Very dry (up) and extreme-rain (down) months per year"))}">
        <line x1="0" x2="${W}" y1="${mid + 1}" y2="${mid + 1}" stroke="rgba(235,235,245,.25)"/>${bars}
      </svg>
      <div class="pc-axis"><span>2001</span><span>2012</span><span>2024</span></div>
      <p class="pc-key"><i class="k-d"></i>${esc(LL("meses muy secos", "very dry months"))}<i class="k-w"></i>${esc(LL("lluvia extrema", "extreme rain"))} · ${esc(LL("toca un año", "tap a year"))}</p>
      <details class="pc-how"><summary>${esc(LL("¿Qué tan confiable es?", "How reliable is it?"))}</summary>
        <p>${esc(LL(`Promedio de ${st.cells} celda${st.cells === 1 ? "" : "s"} IMERG de unos 11 km${st.near ? " (la más cercana: la provincia es más pequeña que una celda)" : ""}. Mes muy seco: menos del 50 % de lo normal de ese mes (solo meses con normal ≥ 20 mm). Lluvia extrema: el 10 % de meses más lluviosos de la provincia (≥ ${Math.round(st.p90)} mm). Es lluvia medida por satélite: no mide ríos, drenaje, suelos ni población.`,
          `Average of ${st.cells} IMERG cell${st.cells === 1 ? "" : "s"} of about 11 km${st.near ? " (the nearest one: the province is smaller than a cell)" : ""}. Very dry month: under 50 % of that month's normal (only months with normal ≥ 20 mm). Extreme rain: the province's wettest 10 % of months (≥ ${Math.round(st.p90)} mm). Satellite rain only: it does not measure rivers, drainage, soils or people.`))}</p></details>`;
    provCard.classList.remove("in"); void provCard.offsetWidth; provCard.classList.add("in");
    provCard.querySelectorAll<SVGGElement>(".yb").forEach((gEl) => {
      const go = () => {
        const y = gEl.dataset.year!;
        // El mes más seco de ese año en la provincia, en el mapa de lluvia
        let best = -1, bv = Infinity;
        st.ratio.forEach((r, t) => { if (r !== null && t >= (Number(y) - 2001) * 12 && t < (Number(y) - 2000) * 12 && r < bv) { bv = r; best = t; } });
        if (best < 0) return;
        mapLayer = "mes";
        view.querySelectorAll<HTMLButtonElement>("[data-mlayer]").forEach((b) => { const on = b.dataset.mlayer === "mes"; b.classList.toggle("on", on); b.setAttribute("aria-checked", String(on)); });
        applyLayer();
        showField(`${y}-${String((best % 12) + 1).padStart(2, "0")}`);
      };
      gEl.addEventListener("click", go);
      gEl.addEventListener("keydown", (e) => { if ((e as KeyboardEvent).key === "Enter") go(); });
    });
  };
  view.querySelectorAll<HTMLButtonElement>("[data-mmode]").forEach((b) => b.addEventListener("click", () => {
    mapMode = b.dataset.mmode as typeof mapMode;
    view.querySelectorAll<HTMLButtonElement>("[data-mmode]").forEach((x) => { const on = x === b; x.classList.toggle("on", on); x.setAttribute("aria-checked", String(on)); });
    t3?.setMode(mapMode);
  }));
  view.querySelectorAll<HTMLButtonElement>("[data-mlayer]").forEach((b) => b.addEventListener("click", () => {
    mapLayer = b.dataset.mlayer as typeof mapLayer;
    view.querySelectorAll<HTMLButtonElement>("[data-mlayer]").forEach((x) => { const on = x === b; x.classList.toggle("on", on); x.setAttribute("aria-checked", String(on)); });
    applyLayer();
  }));
  document.getElementById("drawer-tab")!.addEventListener("click", (e) => {
    const off = consoleEl.classList.toggle("drawer-off");
    (e.currentTarget as HTMLElement).setAttribute("aria-expanded", String(!off));
  });
  t3.ready.then(() => { if (mapMode !== "3d") t3?.setMode(mapMode); });
  const mine = t3;
  Promise.all([t3.ready, load<Grid>("grid/precip_imerg.json")]).then(([, g]) => {
    if (t3 !== mine) return;
    t3.setGrid(g); fieldReady = true; showField(startMonth);
    if (provFC) { stats = provinceStats(g, provFC); applyLayer(); pickProv(defaultProv(), false); }
  }).catch(() => { fMonth.textContent = ""; });


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
  let curIdx = -1;

  const setMonth = (i: number) => {
    if (!xs) return;
    const v = anom[i];
    const date = new Date(`${months[i]}-15T00:00:00`);
    cursor.hidden = false;
    cursor.style.left = `${xs.apply(date)}px`;
    const val = v === null ? "—" : `${fmtSigned(v, d)} ${vmeta.unidad}`;
    readout.textContent = `${fmtMonth(months[i])} · ${val}`;
    curIdx = i;
    showField(months[i]);
    const stress = v !== null && (stressHigh ? v > 0 : v < 0);
    const k = v === null ? 0 : Math.min(1, Math.abs(v) / lim);
    for (const p of zone.paths) p.setStyle({ fillColor: stress ? AMBER : "#ffffff", fillOpacity: 0.12 + 0.6 * k });
    t3?.tintZone(stress ? "#ff453a" : "#0a84ff", 0.08 + 0.45 * k);
    if (zone.label) (zone.label as L.Rectangle).setTooltipContent(`${esc(zone.name)} · ${months[i]} · ${esc(val)}`);
  };
  const clearMonth = () => {
    cursor.hidden = true;
    readout.textContent = "";
    for (const p of zone.paths) p.setStyle({ fillColor: AMBER, fillOpacity: 0.16 });
    t3?.tintZone(AMBER, 0.14);
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
  tlEl.tabIndex = 0;
  tlEl.setAttribute("aria-label", LL("Serie mes a mes. Usa las flechas izquierda y derecha para recorrer los meses.", "Monthly record. Use the left and right arrows to move through the months."));
  tlEl.addEventListener("keydown", (e) => {
    if (!state.revealed || (e.key !== "ArrowLeft" && e.key !== "ArrowRight")) return;
    e.preventDefault(); stopPlay();
    const n = Math.max(0, Math.min(months.length - 1, (curIdx < 0 ? months.length - 1 : curIdx) + (e.key === "ArrowRight" ? 1 : -1)));
    setMonth(n);
  });

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

  view.querySelectorAll<HTMLButtonElement>("[data-month]").forEach((b) => b.addEventListener("click", () => {
    const m = b.dataset.month!;
    stopPlay();
    const i = months.indexOf(m);
    if (state.revealed && i >= 0) setMonth(i); else showField(m);
  }));
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
export function drawRegionMap(all: Series[]) {
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
      <div class="pnl-h"><h2>${esc(t.resultH)}</h2><button class="txt-btn rebet" id="rebet">${esc(LL("Cambiar apuesta", "Change bet"))}</button><span class="meta">${esc(t.yourBet)}: ${arrow[state.prediction ?? "nada"]} ${esc(predLabel[state.prediction ?? "nada"])}</span></div>
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
  document.getElementById("rebet")?.addEventListener("click", () => { resetInvestigation(); route(false); });
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
let mapMode: "3d" | "plano" | "oscuro" = "3d";
let mapLayer: "seco" | "extremo" | "cambio" | "mes" = "seco";
let t3: ReturnType<typeof terrain3d> | null = null;
let rbStoried = false;
let storyToken = 0;
const rbHide: Record<string, boolean> = { top: false, panel: false, bottom: false };
const colBtn = (k: string, label: string) =>
  `<button class="col-btn" data-col="${k}" aria-expanded="${!rbHide[k]}" aria-label="${label}" title="${label}"><svg viewBox="0 0 12 12" aria-hidden="true"><path d="M3 7.5l3-3 3 3" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg></button>`;
const CHEV = '<svg class="pill-chev" viewBox="0 0 12 12" aria-hidden="true"><path d="M3 4.5l3 3 3-3" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>';
const PIN = '<svg class="pill-ico" viewBox="0 0 16 16" aria-hidden="true"><path d="M8 14s4.5-4.2 4.5-7.5a4.5 4.5 0 1 0-9 0C3.5 9.8 8 14 8 14z" fill="none" stroke="currentColor" stroke-width="1.4"/><circle cx="8" cy="6.5" r="1.6" fill="currentColor"/></svg>';
const pillSelect = (id: string, label: string, icon: string, opts: string) =>
  `<label class="pill-select">${icon}<span class="pill-lab">${label}</span><select id="${id}" aria-label="${label}">${opts}</select>${CHEV}</label>`;
const MODE_ICON: Record<string, string> = {
  "3d": '<svg viewBox="0 0 20 20" aria-hidden="true"><path d="M2.5 8.5c2.5-4 5-4 7.5 0s5 4 7.5 0M2.5 13c2.5-4 5-4 7.5 0s5 4 7.5 0" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>',
  "2d": '<svg viewBox="0 0 20 20" aria-hidden="true"><path d="M3 3.5v13h14" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><path d="M5.5 12l3-3.5 3 2 4-5" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  map: '<svg viewBox="0 0 20 20" aria-hidden="true"><path d="M10 17s5.5-5 5.5-9a5.5 5.5 0 1 0-11 0c0 4 5.5 9 5.5 9z" fill="none" stroke="currentColor" stroke-width="1.5"/><circle cx="10" cy="8" r="2" fill="currentColor"/></svg>',
};
const TIP_SIDE = (id: string): { direction: L.Direction; offset: [number, number] } =>
  id === "montecristimontesecoa" ? { direction: "left", offset: [-10, 0] }
  : id === "montecristimontesecob" ? { direction: "top", offset: [0, -10] }
  : id === "sierramontecristi" ? { direction: "bottom", offset: [0, 10] }
  : { direction: "right", offset: [10, 0] };
const rb = { id: "sierramontecristi", fn: "gpp_modelo" as Fn, lane: -1, mode: (innerWidth < 640 ? "2d" : "3d") as "3d" | "2d" | "map" };
const LL = (es: string, en: string) => (getLang() === "es" ? es : en);
const MONTHS_ES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];
const MONTHS_EN = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const monthName = (k: number) => (getLang() === "es" ? MONTHS_ES : MONTHS_EN)[k];
/** "2023-02" → "feb 2023" */
const fmtMonth = (m: string) => `${monthName(Number(m.slice(5, 7)) - 1)} ${m.slice(0, 4)}`;

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
      <div class="story" id="story" hidden aria-live="polite">
        <div class="story-bar" aria-hidden="true"><span id="st-prog"></span></div>
        <h2 class="story-h" id="st-h"></h2>
        <p class="story-p" id="st-p"></p>
        <button class="txt-btn" id="st-skip">${esc(LL("Saltar y explorar", "Skip and explore"))}</button>
      </div>
      <div class="rb-head rb-top ${rbHide.top ? "collapsed" : ""}" data-panel="top">
        <div>
          <p class="crumb">Stellar Horizons<span aria-hidden="true">/</span>PHANTOM</p>
          <h1>Recovery Ribbon ${colBtn("top", LL("Contraer o abrir la explicación", "Collapse or expand the explanation"))}</h1>
          <p class="rb-q">${esc(LL("¿Vuelve el verdor antes que la función? Cada cinta es una sequía. Sus bordes son el verdor y la función; la superficie entre ellos es la brecha, del color de la señal que va delante.",
            "Does greenness come back before function? Each ribbon is a drought. Its edges are greenness and function; the surface between them is the gap, coloured by whichever signal leads."))}</p>
        </div>
        <div class="rb-ctrl pills">
          <button class="txt-btn st-replay" id="st-replay">${esc(LL("▶ Ver la historia", "▶ Watch the story"))}</button>
          <div class="icon-seg" role="radiogroup" aria-label="${esc(LL("Forma de ver", "View"))}">
            ${([["3d", LL("Cintas 3D", "3D ribbons")], ["2d", LL("Brecha 2D", "2D gap")], ["map", LL("Lugares", "Sites")]] as const).map(([m, lab]) => `<button data-rbmode="${m}" class="${rb.mode === m ? "on" : ""}" role="radio" aria-checked="${rb.mode === m}" title="${esc(lab)}" aria-label="${esc(lab)}">${MODE_ICON[m]}<span>${esc(lab)}</span></button>`).join("")}
          </div>
          ${pillSelect("rb-site", LL("Lugar", "Site"), PIN, ids.map((id) => `<option value="${id}" ${id === rb.id ? "selected" : ""}>${esc(NAMES[id])}</option>`).join(""))}
          ${pillSelect("rb-fn", LL("Función", "Function"), "", fns.map((f) => `<option value="${f}" ${f === rb.fn ? "selected" : ""}>${esc(fnName(f))}</option>`).join(""))}
        </div>
      </div>

      <div class="rb-bottom ${rbHide.bottom ? "collapsed" : ""}" data-panel="bottom">
      ${colBtn("bottom", LL("Contraer o abrir la leyenda", "Collapse or expand the legend"))}
      <div class="rb-bar">
        <div class="legend">
          <span><i class="ln" style="background:${GREEN}"></i>${esc(LL("Verdor (NDVI)", "Greenness (NDVI)"))}</span>
          <span><i class="ln" style="background:${FUNC}"></i>${esc(fLabel)}</span>
          <span><i class="sq" style="background:${GREEN};opacity:.5"></i>${esc(LL("brecha: el verdor va delante", "gap: greenness leads"))}</span>
          <span><i class="sq" style="background:${FUNC};opacity:.5"></i>${esc(LL("brecha: la función va delante", "gap: function leads"))}</span>
          <span><i class="sq" style="background:#ff453a;opacity:.7"></i>${esc(LL("sequía (SPI-3)", "drought (SPI-3)"))}</span>
          <span><i class="ln dash"></i>${esc(LL("recuperado: z ≥ −1", "recovered: z ≥ −1"))}</span>
        </div>
        <div class="rb-tools">
          <span class="readout num" id="rb-day"></span>
          <button class="txt-btn" id="rb-play">${esc(LL("▶ Reproducir la recuperación", "▶ Play the recovery"))}</button>
        </div>
      </div>
      <p class="meta">${esc(LL("Eje horizontal: días desde el inicio de cada sequía (−90 a 540). Altura: z. ", "Horizontal axis: days since each drought began (−90 to 540). Height: z. "))}${esc(LL("Arrastra para girar. Toca una fecha a la izquierda de una cinta, o elige abajo, para ver esa sequía con sus valores exactos.",
        "Drag to rotate. Tap a date at the left of a ribbon, or choose below, to see that drought with its exact values."))}</p>

      <div class="rb-time" role="group" aria-label="${esc(LL("Sequías en el tiempo", "Droughts over time"))}">
        <div class="rb-time-track">
          ${[2001, 2005, 2009, 2013, 2017, 2021, 2025].map((y) => `<span class="rb-year" style="left:${(100 * (y - 2001)) / 24}%">${y}</span>`).join("")}
          ${lanes.map((l, i) => { const d = new Date(`${l.audit.evento_inicio.slice(0, 10)}T00:00:00`); const x = (100 * (d.getFullYear() - 2001 + d.getMonth() / 12)) / 24; return `<button class="rb-ev ${i === rb.lane ? "on" : ""}" data-lane="${i}" style="left:${x.toFixed(2)}%" aria-pressed="${i === rb.lane}" title="${l.label} · ${esc(t.verdictName[l.audit.veredicto] ?? l.audit.veredicto)}"><i style="background:${verdictColor(l.audit.veredicto)}"></i><span>${l.label}</span></button>`; }).join("")}
        </div>
      </div>


      </div>
      <aside class="rb-panel ${rbHide.panel ? "collapsed" : ""}" data-panel="panel">
        ${colBtn("panel", LL("Contraer o abrir la ficha", "Collapse or expand the card"))}
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
  const here = sites.find((q) => q.id === rb.id);
  if (rb.mode === "map" || !here) {
    map.fitBounds(L.latLngBounds(sites.map((q) => [q.lat, q.lon] as [number, number])), {
      paddingTopLeft: wide ? [120, 300] : [40, 40], paddingBottomRight: wide ? [480, 220] : [40, 40], maxZoom: 10, animate: false,
    });
  } else {
    map.setView([here.lat, here.lon], wide ? 11 : 10, { animate: false });
    const sz = map.getSize();
    map.panBy([sz.x * (wide ? 0.22 : 0), -sz.y * (wide ? 0.1 : 0)], { animate: false });
  }
  const anchor = () => { if (here && rbStage) { const c = map.latLngToContainerPoint([here.lat, here.lon]); rbStage.setAnchor(rb.mode === "3d" ? [c.x, c.y] : null); } };
  map.on("move zoom resize", anchor);
  anchor();

  // ── Modo historia: la cámara cuenta la sequía en el lugar exacto donde se midió ──
  const sec = view.querySelector<HTMLElement>(".rb")!;
  const story = document.getElementById("story")!;
  const stH = document.getElementById("st-h")!;
  const stP = document.getElementById("st-p")!;
  const stProg = document.getElementById("st-prog")!;
  const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const region = pts.puntos.find((q) => q.id === rb.id)?.region ?? null;
  const zoneSeries = region ? await load<Series>(`series/imerg_precip_${region}.json`).catch(() => null) : null;
  const spi = region ? ph.sequias.find((d) => d.region === region)?.spi3 : undefined;
  const toB = (b: number[]) => L.latLngBounds([b[1], b[0]], [b[3], b[2]]);
  const fmtBox = (b: number[]) => `${b[1]}–${b[3]}° N, ${Math.abs(b[2])}–${Math.abs(b[0])}° O`;
  let zoneLayer: L.Rectangle | null = null;
  let reqLayer: L.Rectangle | null = null;
  let ring: L.Marker | null = null;
  const STEPS = 6;
  const wait = (ms: number, my: number) => new Promise<boolean>((res) =>
    setTimeout(() => res(my === storyToken && sec.isConnected), reduceMotion ? Math.min(ms, 600) : ms));
  const caption = (h: string, p: string, step: number) => {
    story.classList.remove("in"); void story.offsetWidth; story.classList.add("in");
    stH.textContent = h; stP.textContent = p; stProg.style.width = `${(100 * step) / STEPS}%`;
  };
  const dur = reduceMotion ? 0 : 2.4;
  const frame3d = () => {
    if (!here) return;
    const z = wide ? 11 : 10;
    const sz = map.getSize();
    const c = map.unproject(map.project([here.lat, here.lon], z).add([sz.x * (wide ? 0.22 : 0), -sz.y * (wide ? 0.1 : 0)]), z);
    map.flyTo(c, z, { duration: reduceMotion ? 0 : 1.8 });
  };
  const endStory = (my: number) => {
    if (my !== storyToken || !sec.isConnected) return;
    sec.removeAttribute("data-story");
    story.hidden = true;
    ring?.remove(); ring = null;
    rb.mode = wide ? "3d" : "2d"; sec.dataset.mode = rb.mode;
    if (rb.mode === "2d") renderDetail();
    view.querySelectorAll<HTMLButtonElement>("[data-rbmode]").forEach((b) => { const on = b.dataset.rbmode === rb.mode; b.classList.toggle("on", on); b.setAttribute("aria-checked", String(on)); });
    frame3d(); anchor();
  };
  const runStory = async () => {
    const my = ++storyToken;
    rbStoried = true; rbPlayed = true;
    const lane = lanes[rb.lane];
    if (!lane || !here) return;
    sec.dataset.story = "on"; story.hidden = false;
    rbStage?.stop(); rb.mode = "map"; sec.dataset.mode = "map"; anchor();
    // 1. El país
    caption(LL("República Dominicana, 2001–2024", "Dominican Republic, 2001–2024"),
      LL("Buscamos sequías en bosques secos con satélites de la NASA. Primero: dónde.", "We look for droughts in dry forests with NASA satellites. First: where."), 1);
    map.flyToBounds([[17.45, -72.05], [19.98, -68.3]], { duration: dur, padding: [40, 40] });
    if (!(await wait(3200, my))) return;
    // 2. La zona exacta donde se promedió la lluvia
    const pp = zoneSeries?.pasaporte;
    const cd = pp?.caja_datos && pp.caja_datos[0] !== pp.caja_datos[2] ? pp.caja_datos : pp?.caja_pedida ?? null;
    zoneLayer?.remove(); reqLayer?.remove();
    if (pp?.caja_pedida) reqLayer = L.rectangle(toB(pp.caja_pedida), { color: "#ffffff", weight: 1.5, dashArray: "5 6", fill: false, className: "st-draw" }).addTo(map);
    if (cd) zoneLayer = L.rectangle(toB(cd), { color: FUNC, weight: 2.5, fillColor: "#ff453a", fillOpacity: 0, className: "st-draw" }).addTo(map);
    if (cd && region) {
      map.flyToBounds(toB(pp?.caja_pedida ?? cd).pad(0.9), { duration: dur });
      caption(LL(`${regionMeta(index, region).nombre}: aquí se midió la lluvia`, `${regionMeta(index, region).nombre}: where the rain was measured`),
        LL(`Rectángulo ámbar: las celdas de IMERG que se promedian (${fmtBox(cd)}). Línea discontinua: la zona pedida a Giovanni.`,
          `Amber rectangle: the IMERG cells that are averaged (${fmtBox(cd)}). Dashed line: the area requested from Giovanni.`), 2);
      if (!(await wait(3800, my))) return;
    }
    // 3. La sequía, mes a mes, sobre esa misma caja (SPI-3 real)
    caption(`${LL("Sequía", "Drought")} ${lane.label}`, "", 3);
    if (spi && zoneLayer) {
      const a = spi.meses.indexOf(lane.audit.evento_inicio.slice(0, 7));
      const b = spi.meses.indexOf(lane.audit.evento_fin.slice(0, 7));
      for (let i = Math.max(0, a - 3); i <= Math.min(spi.meses.length - 1, b + 3); i++) {
        const v = spi.valores[i];
        const dry = v !== null && v < -1;
        zoneLayer.setStyle({ fillColor: dry ? "#ff453a" : "#8a8c92", fillOpacity: v === null ? 0.05 : v < 0 ? Math.min(0.72, -v * 0.3) : 0.06 });
        stP.textContent = `${spi.meses[i]} · SPI-3 ${v === null ? "—" : fmtSigned(v, 2)}${dry ? LL(" · en sequía", " · in drought") : ""}`;
        if (!(await wait(560, my))) return;
      }
    }
    // 4. El lugar donde se mide la vegetación
    map.flyTo([here.lat, here.lon], 12, { duration: dur });
    ring?.remove();
    ring = L.marker([here.lat, here.lon], { icon: L.divIcon({ className: "st-ring", iconSize: [64, 64] }), interactive: false }).addTo(map);
    caption(LL(`${NAMES[rb.id]}: aquí se mide la vegetación`, `${NAMES[rb.id]}: where vegetation is measured`),
      (cd && toB(cd).contains([here.lat, here.lon])
        ? LL(`Punto MODIS ${here.lat}, ${here.lon}, dentro de las celdas de lluvia. Después de la sequía, ¿volvió el verde? ¿Volvió la función?`,
          `MODIS point ${here.lat}, ${here.lon}, inside the rain cells. After the drought, did the green come back? Did function?`)
        : LL(`Punto MODIS ${here.lat}, ${here.lon}: dentro de la zona pedida, a pocos km de las celdas de lluvia (ámbar). ¿Volvió el verde? ¿Volvió la función?`,
          `MODIS point ${here.lat}, ${here.lon}: inside the requested area, a few km from the rain cells (amber). Did the green come back? Did function?`)), 4);
    if (!(await wait(3600, my))) return;
    // 5. Las cintas suben del lugar
    rb.mode = "3d"; sec.dataset.mode = "3d"; ring?.remove(); ring = null; frame3d(); anchor();
    caption(LL("La recuperación, día a día", "The recovery, day by day"),
      LL("Cada cinta es una sequía de este lugar. Verde: el verdor (NDVI). Ámbar: la función. La superficie entre ambos es la brecha.",
        "Each ribbon is a drought at this site. Green: greenness (NDVI). Amber: function. The surface between them is the gap."), 5);
    rbStage?.play();
    if (!(await wait(7800, my))) return;
    // 6. El veredicto
    caption(t.verdictName[lane.audit.veredicto] ?? lane.audit.veredicto, t.verdictWhy[lane.audit.veredicto] ?? "", 6);
    if (!(await wait(5600, my))) return;
    endStory(my);
  };
  document.getElementById("st-skip")!.addEventListener("click", () => { rbStage?.stop(); endStory(storyToken); });
  document.getElementById("st-replay")!.addEventListener("click", () => { runStory(); });
  if (!rbStoried) setTimeout(() => { if (sec.isConnected) runStory(); }, 700);

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
  if (rb.mode === "3d" && rbStoried && !rbPlayed && !matchMedia("(prefers-reduced-motion: reduce)").matches) {
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
      <details class="rb-how"><summary>${esc(LL("Cómo se calcula", "How it is computed"))}</summary><p class="meta">${esc(LL("En esta ficha los días se cuentan desde el fin de la sequía (negativo: volvió antes de que terminara); en las gráficas, desde su inicio.", "In this card days count from the end of the drought (negative: back before it ended); in the charts, from its start."))} ${esc(LL("z: desviación robusta de lo normal para esa época del año (mediana y MAD, 8 años o más), suavizada con mediana de 3. Impacto: z < −1,5 durante 3 observaciones; recuperado: z ≥ −1 durante 3. La GPP es salida del modelo MOD17 y usa el mismo FPAR que el verdor: no es una medición independiente.",
        "z: robust departure from normal for that time of year (median and MAD, 8+ years), smoothed with a median of 3. Impact: z < −1.5 for 3 observations; recovered: z ≥ −1 for 3. GPP is MOD17 model output and uses the same FPAR as greenness: it is not an independent measurement."))}</p></details>`;
  };
  const pickLane = (i: number) => {
    rb.lane = i;
    rbStage?.select(i);
    view.querySelectorAll<HTMLButtonElement>("[data-lane]").forEach((b) => { const on = Number(b.dataset.lane) === i; b.classList.toggle("on", on); b.setAttribute("aria-pressed", String(on)); });
    renderDetail();
  };
  renderDetail();

  playBtn.addEventListener("click", () => {
    if (rbStage!.playing()) { rbStage!.stop(); return; }
    playBtn.textContent = LL("Detener", "Stop");
    rbStage!.play();
  });
  view.querySelectorAll<HTMLButtonElement>("[data-lane]").forEach((b) => b.addEventListener("click", () => pickLane(Number(b.dataset.lane))));
  view.querySelectorAll<HTMLButtonElement>("[data-col]").forEach((b) => b.addEventListener("click", () => {
    const k = b.dataset.col!;
    rbHide[k] = !rbHide[k];
    view.querySelector(`[data-panel="${k}"]`)!.classList.toggle("collapsed", rbHide[k]);
    b.setAttribute("aria-expanded", String(!rbHide[k]));
    if (k === "panel" && !rbHide[k]) renderDetail();
  }));
  document.getElementById("rb-site")!.addEventListener("change", (e) => { rb.id = (e.target as HTMLSelectElement).value; rb.lane = -1; viewRibbon(); });
  document.getElementById("rb-fn")!.addEventListener("change", (e) => { rb.fn = (e.target as HTMLSelectElement).value as Fn; viewRibbon(); });
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

/* ───────────── Router ───────────── */

async function route(scrollTop = true) {
  // «Investigar» y «Recovery Ribbon» viven ahora dentro de Tendencias como preguntas de la vegetación; sus pantallas
  // anteriores quedan en #investigar-v1 y #ribbon-v1, fuera del menú
  const raw = location.hash.replace("#", "") || "tendencias";
  if (raw === "investigar" || raw === "ribbon") { openLand(raw === "investigar" ? "verde" : "recupera"); history.replaceState(null, "", "#tendencias"); }
  const r = (raw === "investigar" || raw === "ribbon" ? "tendencias" : raw === "investigar-v1" ? "investigar" : raw === "ribbon-v1" ? "ribbon" : raw) as "respuesta" | "preparar" | "tendencias" | "investigar" | "ribbon" | "expedientes" | "auditoria" | "metodo";
  setNav(r);
  stopPlay();
  clearMaps();
  try {
    if (r !== "ribbon") { rbStage?.destroy(); rbStage = null; }
    if (r !== "investigar") { t3?.destroy(); t3 = null; }
    if (r !== "tendencias") destroyTrends();
    if (r !== "auditoria") destroyAudit();
    if (r !== "preparar") destroyPreparation();
    if (r === "preparar") await viewPreparation(document.getElementById("view")!);
    else if (r === "expedientes") await viewCases();
    else if (r === "auditoria") await viewAudit(document.getElementById("view")!);
    else if (r === "ribbon") await viewRibbon();
    else if (r === "respuesta") await viewAnswer(document.getElementById("view")!);
    else if (r === "metodo") { const t = T(); await viewMethodV2(document.getElementById("view")!, t.glossary, t.limitsH, t.limits); }
    else if (r === "tendencias") await viewTrends(document.getElementById("view")!);
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
    if (["#respuesta", "#preparar", "#tendencias", "#investigar", "#ribbon", "#investigar-v1", "#ribbon-v1", "#expedientes", "#auditoria", "#metodo", ""].includes(location.hash)) route();
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
