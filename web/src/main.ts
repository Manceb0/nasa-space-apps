import "leaflet/dist/leaflet.css";
import "./style.css";
import L from "leaflet";
import {
  constellation, dualTimeline, evidenceChart, heatmap, rawChart, recoveryDist, sensitivityStrip, spiChart, windowMatrix,
} from "./charts";
import { load, type Index, type Phantom, type PhantomEventRow, type Puntos, type SensRow, type Series, type Window } from "./data";
import { T, getLang, regionMeta, setLang, varMeta } from "./i18n";
import {
  digitsFor, fmt, fmtP, fmtSigned, multipleTestingNote, predictionFeedback, robustLabel, seasonLesson, stateLabel,
  trapText, verdictExplain, verdictSentence, verdictShort, windowLabel, type Prediction,
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
  dualFn: "gpp_modelo" | "lst_menos_aire";
}
const state: State = {
  variable: "imerg_precip", region: "noroeste", prediction: null, revealed: false, window: null, raw: false,
  heatVar: "modis_ndvi", mapVar: "modis_ndvi", dualFn: "lst_menos_aire",
};

// Modo de prueba local: ?prueba=1 lee un archivo SINTÉTICO que solo existe en la máquina de desarrollo.
const TEST_MODE = new URLSearchParams(location.search).get("prueba") === "1";

let index: Index;
const maps: L.Map[] = [];

const POINT_NAMES: Record<string, string> = {
  montecristimontesecoa: "Montecristi A", montecristimontesecob: "Montecristi B", sierramontecristi: "Sierra de Montecristi",
  jaraguacomparacionseco: "Jaragua", cordilleracomparacionhumedo: "Cordillera Central",
};
const POINT_ORDER = ["montecristimontesecoa", "montecristimontesecob", "sierramontecristi", "jaraguacomparacionseco", "cordilleracomparacionhumedo"];
const pointName = (id: string) => POINT_NAMES[id.replace(/_/g, "")] ?? id;
// Para cada variable MODIS, qué dirección es "peor" (para el color del mapa de calor y del mapa de tendencias)
const WORSE_IS_HIGH: Record<string, boolean> = { modis_ndvi: false, modis_gpp: false, modis_lst: true };

const esc = (s: string) => s.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]!));

function clearMaps() {
  while (maps.length) maps.pop()!.remove();
}

function baseMap(el: HTMLElement, center: [number, number], zoom: number): L.Map {
  const m = L.map(el, { zoomControl: true, attributionControl: true, scrollWheelZoom: false }).setView(center, zoom);
  L.tileLayer("https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/BlueMarble_ShadedRelief_Bathymetry/default/GoogleMapsCompatible_Level8/{z}/{y}/{x}.jpeg", {
    maxNativeZoom: 8, maxZoom: 10, attribution: "NASA GIBS · Blue Marble",
  }).addTo(m);
  maps.push(m);
  return m;
}

function shell(): void {
  const t = T();
  document.title = t.title;
  app.innerHTML = `
    <header class="bar">
      <a class="brand" href="#investigar" aria-label="${esc(t.brand)}">
        <svg viewBox="0 0 32 32" aria-hidden="true"><circle cx="16" cy="16" r="9" fill="#f2b33d"/><path d="M3 20c6-9 20-15 26-8" stroke="#ffffff" stroke-width="2.4" fill="none" stroke-linecap="round"/></svg>
        <span>${esc(t.brand)}</span>
      </a>
      <nav>
        <a href="#investigar" data-nav="investigar">${esc(t.navInvestigate)}</a>
        <a href="#expedientes" data-nav="expedientes">${esc(t.navCases)}</a>
        <a href="#metodo" data-nav="metodo">${esc(t.navMethod)}</a>
      </nav>
      <span class="team">${esc(t.team)}</span>
      <button class="lang" id="lang" aria-label="${esc(t.langSwitchLabel)}" lang="${getLang() === "es" ? "en" : "es"}">${esc(t.langSwitch)}</button>
    </header>
    <main id="view"></main>
    <footer class="foot"><p>${esc(t.footer)}</p></footer>`;
  document.getElementById("lang")!.addEventListener("click", () => {
    setLang(getLang() === "es" ? "en" : "es");
    shell();
    route(false);
  });
}

function setNav(r: string) {
  document.querySelectorAll<HTMLAnchorElement>("[data-nav]").forEach((a) => a.classList.toggle("on", a.dataset.nav === r));
}

/* ───────────── Investigar ───────────── */

async function viewInvestigate() {
  const t = T();
  const view = document.getElementById("view")!;
  const vmeta = varMeta(index, state.variable);
  const rmeta = regionMeta(index, state.region);
  const predLabel: Record<Prediction, string> = { sube: t.predUp, baja: t.predDown, nada: t.predNone };
  const groups: [string, string[]][] = [
    [t.groupClimate, Object.keys(index.variables).filter((k) => !k.startsWith("modis_"))],
    [t.groupVeg, Object.keys(index.variables).filter((k) => k.startsWith("modis_"))],
  ];
  view.innerHTML = `
    <div class="title-row">
      <h1>${esc(t.invTitle)}</h1>
      <p>${esc(t.invSub)}</p>
    </div>

    <div class="grid">
      <section class="card s4">
        <h2>${esc(t.whatQ)}</h2>
        ${groups.filter(([, ks]) => ks.length).map(([title, ks]) => `
          <p class="group">${esc(title)}</p>
          <div class="choices" role="radiogroup" aria-label="${esc(title)}" style="--n:${ks.length}">
            ${ks.map((k) => { const v = varMeta(index, k); return `
              <button class="choice ${k === state.variable ? "on" : ""}" data-var="${k}" role="radio" aria-checked="${k === state.variable}">
                <strong>${esc(v.nombre)}</strong><span>${esc(v.pregunta)}</span>
              </button>`; }).join("")}
          </div>`).join("")}
        <p class="def">${esc(vmeta.definicion)} ${esc(t.measuredIn)} ${esc(vmeta.unidad_larga)}. <span class="kind">${esc(t.dataType)}: ${esc(vmeta.tipo)}.</span>${vmeta.aviso ? ` ${esc(vmeta.aviso)}` : ""}</p>
      </section>
      <section class="card s2 map-card">
        <h2>${esc(t.whereH)}</h2>
        <div class="choices regions" role="radiogroup" aria-label="${esc(t.whereH)}">
          ${Object.keys(index.regiones).map((k) => { const r = regionMeta(index, k); return `
            <button class="choice ${k === state.region ? "on" : ""}" data-reg="${k}" role="radio" aria-checked="${k === state.region}">
              <strong>${esc(r.nombre)}</strong><span>${esc(r.zona)}</span>
            </button>`; }).join("")}
        </div>
        <div id="map" aria-label="${esc(t.mapLabel)}"></div>
        <figcaption id="mapcap"></figcaption>
        <p class="caption">${esc(rmeta.descripcion)}</p>
      </section>

      <section class="card s6" id="predict">
        <h2>${esc(t.hypothesis)}</h2>
        <p class="q">${esc(t.since2001(vmeta.nombre.charAt(0).toLowerCase() + vmeta.nombre.slice(1), rmeta.nombre))}</p>
        <div class="answers">
          ${(["sube", "baja", "nada"] as Prediction[]).map((p) => `
            <button class="answer ${state.prediction === p ? "on" : ""}" data-pred="${p}">${esc(predLabel[p])}</button>`).join("")}
        </div>
        <button class="reveal" id="reveal" ${state.prediction ? "" : "disabled"}>${esc(t.reveal)}</button>
      </section>
    </div>

    <div id="evidence"></div>`;

  view.querySelectorAll<HTMLButtonElement>("[data-var]").forEach((b) => b.addEventListener("click", () => {
    state.variable = b.dataset.var!; resetInvestigation(); route(false);
  }));
  view.querySelectorAll<HTMLButtonElement>("[data-reg]").forEach((b) => b.addEventListener("click", () => {
    state.region = b.dataset.reg!; resetInvestigation(); route(false);
  }));
  view.querySelectorAll<HTMLButtonElement>("[data-pred]").forEach((b) => b.addEventListener("click", () => {
    state.prediction = b.dataset.pred as Prediction;
    view.querySelectorAll("[data-pred]").forEach((x) => x.classList.toggle("on", x === b));
    (document.getElementById("reveal") as HTMLButtonElement).disabled = false;
  }));
  document.getElementById("reveal")!.addEventListener("click", () => {
    state.revealed = true; renderEvidence(true);
  });

  const s = await load<Series>(`series/${state.variable}_${state.region}.json`);
  drawRegionMap(s);
  if (state.revealed) renderEvidence(false);
}

function resetInvestigation() {
  state.prediction = null; state.revealed = false; state.window = null; state.raw = false;
}

function drawRegionMap(s: Series) {
  const t = T();
  const el = document.getElementById("map");
  if (!el) return;
  const r = index.regiones[s.region];
  const map = baseMap(el, r.centro, 8);
  const p = s.pasaporte;
  const toBounds = (b: number[]) => L.latLngBounds([b[1], b[0]], [b[3], b[2]]);
  let note = t.mapDashed;
  if (p.puntos && p.puntos.length) {
    const pts = p.puntos.map(([lat, lon]) => L.latLng(lat, lon));
    p.puntos.forEach(([lat, lon, id]) => L.circleMarker([lat, lon], { radius: 7, color: "#f2b33d", weight: 2, fillOpacity: 0.8 })
      .bindTooltip(pointName(id)).addTo(map));
    note = t.mapPoints;
    if (pts.length === 1) map.setView(pts[0], 9);
    else map.fitBounds(L.latLngBounds(pts).pad(1.2), { maxZoom: 9 });
  } else {
    if (p.caja_pedida) L.rectangle(toBounds(p.caja_pedida), { color: "#ffffff", weight: 1.5, dashArray: "4 4", fill: false }).addTo(map);
    if (p.caja_datos) {
      const [w, so, e, n] = p.caja_datos;
      if (w === e && so === n) {
        L.circleMarker([so, w], { radius: 7, color: "#f2b33d", weight: 2, fillOpacity: 0.7 }).addTo(map);
        note += t.mapPoint;
      } else {
        L.rectangle(toBounds(p.caja_datos), { color: "#f2b33d", weight: 2, fillOpacity: 0.12 }).addTo(map);
        note += t.mapBox;
      }
    }
    if (p.caja_pedida) map.fitBounds(toBounds(p.caja_pedida).pad(1.6), { maxZoom: 9 });
  }
  document.getElementById("mapcap")!.textContent = note;
}

async function renderEvidence(scroll: boolean) {
  const t = T();
  const host = document.getElementById("evidence")!;
  const s = await load<Series>(`series/${state.variable}_${state.region}.json`);
  const meta = varMeta(index, state.variable);
  const rname = regionMeta(index, state.region).nombre;
  const full = s.completa;
  const years = s.anual.anios;
  const y0 = years[0];
  const y1 = years[years.length - 1];
  const fb = predictionFeedback(state.prediction ?? "nada", full);
  const mt = multipleTestingNote(full, index.series.length);
  const d = digitsFor(meta);
  const pp = s.pasaporte;
  host.innerHTML = `
    <div class="grid evidence">
      <section class="card s6">
        <p class="feedback ${fb.ok === true ? "yes" : ""}">${esc(fb.text)}</p>
        <h2 class="verdict">${esc(verdictSentence(meta, rname, full, y0, y1))}</h2>
        <p class="explain">${esc(verdictExplain(meta, full))}</p>
        ${mt ? `<p class="warn">${esc(mt)}</p>` : ""}
        <div class="facts">
          <p><em>${esc(t.factSlope)}</em><span class="big">${fmtSigned(full.pendiente_decada, d)}</span>${esc(meta.unidad)} ${esc(t.factPerDecade)}</p>
          <p><em>${esc(t.factRange)}</em><span class="big">${fmtSigned(full.ic95_decada[0], d)} ${esc(t.to)} ${fmtSigned(full.ic95_decada[1], d)}</span>${esc(meta.unidad)}</p>
          <p><em>${esc(t.factP)}</em><span class="big">${fmtP(full.p_mk)}</span>Mann-Kendall</p>
          <p><em>${esc(t.factYears)}</em><span class="big">${full.n}</span>${y0}–${y1}</p>
        </div>
      </section>

      <section class="card s6">
        <div class="card-head">
          <h3>${esc(state.raw ? t.chartRaw : t.chartAnom)}</h3>
          <button class="toggle" id="rawtoggle">${esc(state.raw ? t.btnAnom : t.btnRaw)}</button>
        </div>
        <div id="chart" class="chart"></div>
        <p class="caption">${esc(state.raw ? seasonLesson(meta, s.amplitud_estacional, full, full.n) : t.captionAnom)}</p>
      </section>

      <section class="card s3">
        <h2>${esc(t.windowsH)}</h2>
        <p class="sub">${esc(t.windowLede)}</p>
        <div id="matrix"></div>
      </section>
      <section class="card s3 side">
        <div id="wininfo"></div>
        ${s.ventanas_que_enganan.length ? `
          <h3>${esc(t.trapsTitle)}</h3>
          <div class="traps">${s.ventanas_que_enganan.map((w, i) => `<button class="trap" data-trap="${i}">${windowLabel(w)}</button>`).join("")}</div>
          <p class="small">${esc(t.trapsNote)}</p>` : `
          <p class="small" style="margin-top:14px">${esc(t.noTraps)}</p>`}
      </section>

      <details class="card s6 passport">
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
    const w = chartEl.clientWidth || 800;
    chartEl.append(state.raw ? rawChart(s, meta.unidad, w) : evidenceChart(s, meta.unidad, state.window, w));
  };
  drawChart();
  document.getElementById("rawtoggle")!.addEventListener("click", () => { state.raw = !state.raw; renderEvidence(false); });

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
      ${isTrap ? `<p class="warn">${esc(trapText(w, full, meta))}</p>` : ""}
      <button class="toggle" id="clearwin">${esc(t.backFull)}</button>`;
    document.getElementById("clearwin")?.addEventListener("click", () => pick(null));
  };
  const matrixEl = document.getElementById("matrix")!;
  const pick = (w: Window | null) => {
    state.window = w;
    state.raw = false;
    matrixEl.innerHTML = "";
    matrixEl.append(windowMatrix(s, state.window, pick));
    drawChart();
    winInfo();
  };
  matrixEl.append(windowMatrix(s, state.window, pick));
  winInfo();
  host.querySelectorAll<HTMLButtonElement>("[data-trap]").forEach((b) => b.addEventListener("click", () => {
    pick(s.ventanas_que_enganan[Number(b.dataset.trap)]);
    document.getElementById("chart")!.scrollIntoView({ behavior: "smooth", block: "center" });
  }));
  if (scroll) host.scrollIntoView({ behavior: "smooth", block: "start" });
}

/* ───────────── Expedientes ───────────── */

async function viewCases() {
  const t = T();
  const view = document.getElementById("view")!;
  const ph = await load<Phantom>(TEST_MODE ? "phantom-SINTETICO-prueba.json" : "phantom.json");
  const pts = index.puntos && !TEST_MODE ? await load<Puntos>("puntos.json") : null;
  const done = ph.estado_modis === "procesado" && ph.eventos.length > 0;
  const both = ph.eventos.filter((e) => e.estado === "ambos_recuperados" && e.dt_dias !== null);
  const after = both.filter((e) => (e.dt_dias as number) > 32);
  const before = both.filter((e) => (e.dt_dias as number) < -32);
  const robustAfter = after.filter((e) => e.rob_etiqueta === "ROBUSTO" && !e.funcion_cae_despues_del_verde);
  const robustBefore = both.filter((e) => e.rob_etiqueta === "ROBUSTO" && ((e.dt_dias as number) < -32 || (e.rob_dt_mediana ?? 0) < -32));
  const lateDips = after.filter((e) => e.funcion_cae_despues_del_verde);
  const supported = after.length > before.length && robustAfter.length > 0;
  const fnName = (f: string) => (f === "gpp_modelo" ? t.sigGpp : t.sigLst);

  view.innerHTML = `
    ${TEST_MODE ? `<p class="test-banner">${esc(t.testBanner)}</p>` : ""}
    <div class="title-row">
      <h1>${esc(t.caseTitle)}</h1>
      <p>${esc(done ? t.caseSub : t.caseLede)}</p>
    </div>

    ${!done ? `
    <div class="grid"><section class="card s6"><h2>${esc(t.caseWaiting)}</h2><p class="explain">${t.caseWaitingText}</p></section></div>` : `
    <div class="grid">
      <section class="card s6">
        <h2>${esc(supported ? t.phantomYesH : t.phantomNoH)}</h2>
        <div class="numbers">
          <p>${esc(t.numWithin)} <b>${both.length - after.length - before.length}</b>${esc(t.withinShort)}</p>
          <p>${esc(t.numBefore)} <b>${before.length}</b>${esc(t.beforeShort)}</p>
          <p>${esc(t.numAfter)} <b>${after.length}</b>${esc(t.afterShort)}</p>
          <p>${esc(t.robustShort)} <b>${robustAfter.length} / ${robustBefore.length}</b>${esc(t.robustSplit)}</p>
        </div>
        <p class="explain">${esc(t.phantomSummary(both.length, both.length - after.length - before.length, before.length, after.length))}</p>
        ${lateDips.length ? `<p class="warn">${esc(t.phantomLateDip(lateDips.map((e) => `${pointName(e.id)} ${e.evento_inicio.slice(0, 4)} (${fnName(e.funcion)}, +${fmt(e.dt_dias as number, 0)} ${t.days})`)))}</p>` : ""}
        <p class="small" style="margin-top:10px">${esc(t.phantomCaveat)}</p>
      </section>

      <section class="card s4">
        <div class="card-head">
          <div><h2>${esc(t.dualH)}</h2></div>
          <div class="seg" role="radiogroup" aria-label="${esc(t.cSignal)}">
            <button data-fn="lst_menos_aire" class="${state.dualFn === "lst_menos_aire" ? "on" : ""}">${esc(t.sigLst)}</button>
            <button data-fn="gpp_modelo" class="${state.dualFn === "gpp_modelo" ? "on" : ""}">${esc(t.sigGpp)}</button>
          </div>
        </div>
        <div class="controls">
          <label>${esc(t.cPoint)} <select id="d-id"></select></label>
          <label>${esc(t.cDrought)} <select id="d-ev"></select></label>
          <div class="legend"><span><i class="ln" style="background:#e6e6e6"></i>${esc(t.sigGreen)}</span><span><i class="ln" style="background:#f2b33d"></i><span id="d-fname"></span></span></div>
        </div>
        <div id="dual" class="chart" style="margin-top:8px"></div>
        <p class="caption">${esc(t.dualSub)}</p>
      </section>
      <section class="card s2">
        <h3>${esc(t.caseFacts)}</h3>
        <div class="facts-list" id="d-facts"></div>
        <div class="foot-note"><div id="d-strip" class="chart"></div><p class="small" id="d-sens"></p></div>
      </section>

      <section class="card s6">
        <div class="card-head">
          <div><h2>${esc(t.heatH)}</h2><p class="sub">${esc(t.heatSub)}</p></div>
          <div class="seg" role="radiogroup" aria-label="${esc(t.heatH)}">
            ${["modis_ndvi", "modis_lst", "modis_gpp"].map((v) => `<button data-heat="${v}" class="${state.heatVar === v ? "on" : ""}">${esc(varMeta(index, v).nombre)}</button>`).join("")}
          </div>
        </div>
        <div id="heat" class="chart"></div>
        <div class="legend" style="margin-top:10px"><span><i class="sq" style="background:#f2b33d"></i>${esc(t.worse)}</span><span><i class="sq" style="background:#a9a9a9"></i>${esc(t.better)}</span><span><i class="sq none"></i>${esc(t.noData)}</span><span><i class="sq" style="background:#fff;height:2px"></i>${esc(t.droughtLabel)} (SPI-3)</span></div>
      </section>

      <section class="card s3">
        <h2>${esc(t.constH)}</h2>
        <p class="sub">${esc(t.constSub)}</p>
        <div class="legend"><span><i class="dot" style="background:#f2b33d"></i>${esc(robustLabel("ROBUSTO"))}</span><span><i class="ring"></i>${esc(t.sigRing)}</span><span>● ${esc(t.sigGpp)}</span><span>▲ ${esc(t.sigLst)}</span></div>
        <div id="const" class="chart" style="margin-top:6px"></div>
      </section>
      <section class="card s3">
        <h2>${esc(t.distH)}</h2>
        <p class="sub">${esc(t.distSub)}</p>
        <div id="dist" class="chart"></div>
      </section>

      ${pts ? `
      <section class="card s4">
        <div class="card-head">
          <div><h2>${esc(t.mapH)}</h2><p class="sub">${esc(t.mapSub)}</p></div>
          <div class="seg" role="radiogroup" aria-label="${esc(t.mapH)}">
            ${["modis_ndvi", "modis_lst", "modis_gpp"].map((v) => `<button data-mapv="${v}" class="${state.mapVar === v ? "on" : ""}">${esc(varMeta(index, v).nombre)}</button>`).join("")}
          </div>
        </div>
        <div id="pmap"></div>
        <div class="legend" style="margin-top:10px"><span><i class="dot" style="background:#f2b33d"></i>${esc(t.worsens)}, ${esc(t.sigFilled)}</span><span><i class="dot" style="background:#e6e6e6"></i>${esc(t.improves)}, ${esc(t.sigFilled)}</span><span><i class="ring"></i>${esc(t.sigRing)}</span></div>
      </section>
      <section class="card s2">
        <h3 id="pm-title"></h3>
        <table class="trend-list" id="pm-table"></table>
        <p class="small foot-note">${esc(t.qNote(pts.n_pruebas_mapa))}</p>
      </section>` : ""}

      <section class="card s3">
        <h2>${esc(t.areaH)}</h2>
        <div class="empty" style="margin-top:12px">${esc(t.areaEmpty)}</div>
      </section>
      <section class="card s3">
        <h2>${esc(t.case2H)}</h2>
        <p class="sub">${esc(t.case2Lede)}</p>
        ${ph.colisiones ? `<p class="verdict">${esc(t.case2Count(ph.colisiones.colisiones, ph.colisiones.eventos_evaluados))}</p>` : `<p>${esc(t.case2Pending)}</p>`}
      </section>
    </div>`}

    <div class="grid">
      <section class="card s6">
        <h2>${esc(t.droughtsH)}</h2>
        <p class="sub">${esc(t.droughtsNote)}</p>
        ${ph.sequias.map((d, i) => `<h3 style="margin-top:12px">${esc(regionMeta(index, d.region).nombre)}</h3><div class="chart" id="spi${i}"></div>`).join("")}
      </section>
      <section class="card s6">
        <div class="two-col">
          <div><h2>${esc(t.howH)}</h2><p class="explain">${t.howP1}</p><p class="explain">${esc(t.howP2)}</p></div>
          <div><h2>${esc(t.notClaimH)}</h2><p class="explain">${esc(t.notClaim)}</p></div>
        </div>
      </section>
      ${done ? `
      <details class="card s6">
        <summary>${esc(t.tableAll)}</summary>
        <div class="table-wrap"><table class="events">
          <thead><tr><th>${esc(t.thPoint)}</th><th>${esc(t.thDrought)}</th><th>${esc(t.thSignal)}</th><th>${esc(t.thState)}</th><th class="num">${esc(t.thDt)}</th><th>${esc(t.thRobust)}</th></tr></thead>
          <tbody>${ph.eventos.filter((e) => e.estado !== "sin_impacto").map((e) => `
            <tr><td>${esc(pointName(e.id))}</td><td>${esc(e.evento_inicio.slice(0, 7))}</td><td>${esc(fnName(e.funcion))}</td>
            <td>${esc(stateLabel(e.estado))}</td><td class="num">${e.dt_dias === null ? "—" : (e.dt_es_cota_inferior ? "≥ " : "") + fmt(e.dt_dias, 0)}</td>
            <td>${esc(robustLabel(e.rob_etiqueta))}</td></tr>`).join("")}</tbody>
        </table></div>
        <p class="small" style="margin-top:10px">${esc(t.hiddenRows(ph.eventos.filter((e) => e.estado === "sin_impacto").length))}</p>
      </details>` : ""}
    </div>`;

  ph.sequias.forEach((d, i) => {
    const el = document.getElementById(`spi${i}`)!;
    el.append(spiChart(d, el.clientWidth || 800));
  });
  if (!done) return;
  wireDual(ph, pts);
  const draw = (id: string, f: (w: number) => Element) => {
    const el = document.getElementById(id);
    if (!el) return;
    el.innerHTML = "";
    el.append(f(el.clientWidth || 600));
  };
  draw("const", (w) => constellation(ph.eventos, Object.fromEntries(ph.eventos.map((e) => [e.id, pointName(e.id)])), w));
  draw("dist", (w) => recoveryDist(ph.eventos, w));
  if (pts) {
    const regionOf = Object.fromEntries(pts.puntos.map((p) => [p.id, p.region]));
    const droughts = ph.sequias.flatMap((d) => d.eventos.map((e) => ({ region: d.region, a: e.inicio, b: e.fin })));
    const drawHeat = () => draw("heat", (w) => heatmap(pts, state.heatVar, WORSE_IS_HIGH[state.heatVar], POINT_ORDER,
      Object.fromEntries(POINT_ORDER.map((id) => [id, pointName(id)])), droughts, regionOf, w));
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

function wireDual(ph: Phantom, pts: Puntos | null) {
  const t = T();
  const $ = <E extends HTMLElement>(id: string) => document.getElementById(id) as E;
  const ids = POINT_ORDER.filter((id) => ph.eventos.some((e) => e.id === id && e.estado !== "sin_impacto"));
  $<HTMLSelectElement>("d-id").innerHTML = ids.map((i) => `<option value="${i}">${esc(pointName(i))}</option>`).join("");
  const rowsFor = (id: string) => ph.eventos.filter((e) => e.id === id && e.funcion === state.dualFn);
  const fillEvents = () => {
    const evs = rowsFor($<HTMLSelectElement>("d-id").value).filter((e) => e.estado !== "sin_impacto");
    $<HTMLSelectElement>("d-ev").innerHTML = evs.map((e) => `<option value="${e.evento_inicio}">${e.evento_inicio.slice(0, 7)} · ${esc(stateLabel(e.estado))}</option>`).join("");
  };
  const update = () => {
    const id = $<HTMLSelectElement>("d-id").value;
    const ev = $<HTMLSelectElement>("d-ev").value;
    const row: PhantomEventRow | undefined = rowsFor(id).find((e) => e.evento_inicio === ev);
    $("d-fname").textContent = state.dualFn === "gpp_modelo" ? t.sigGpp : t.sigLst;
    const z = pts?.z[id];
    const el = $("dual");
    el.innerHTML = "";
    if (!row || !z) { el.innerHTML = `<div class="empty">${esc(t.cNA)}</div>`; return; }
    el.append(dualTimeline({
      green: z.ndvi, func: z[state.dualFn], start: row.evento_inicio, end: row.evento_fin, stop: row.fin_ventana,
      greenRec: row.verde_recuperacion, funcRec: row.funcion_recuperacion, threshold: -1, width: el.clientWidth || 700,
    }));
    const date = (s: string | null) => (s ? s.slice(0, 10) : t.fNot);
    $("d-facts").innerHTML = `
      <div><span>${esc(t.fDrought)}</span><b>${row.evento_inicio.slice(0, 7)} → ${row.evento_fin.slice(0, 7)}</b></div>
      <div><span>${esc(t.fGreen)}</span><b>${esc(date(row.verde_recuperacion))}</b></div>
      <div><span>${esc(t.fFunc)}</span><b>${esc(date(row.funcion_recuperacion))}</b></div>
      <div><span>${esc(t.fDt)}</span><b>${row.dt_dias === null ? "—" : `${row.dt_es_cota_inferior ? "≥ " : ""}${fmtSigned(row.dt_dias, 0)} ${esc(t.days)}`}</b></div>
      <div><span>${esc(t.fRobust)}</span><b>${esc(robustLabel(row.rob_etiqueta))}</b></div>
      <div><span>${esc(t.fSeverity)}</span><b>${row.evento_severidad_spi3 === null ? "—" : fmt(row.evento_severidad_spi3, 1)}</b></div>
      <div><span>${esc(t.fWindow)}</span><b>${esc(row.fin_ventana.slice(0, 10))}</b></div>`;
    const sens: SensRow[] = ph.sensibilidad.filter((r) => r.id === id && r.evento_inicio.slice(0, 10) === ev.slice(0, 10) && r.funcion === state.dualFn);
    const valid = sens.filter((r) => r.estado === "ambos_recuperados" && r.dt_dias !== null);
    const pos = valid.filter((r) => (r.dt_dias as number) > 32).length;
    const neg = valid.filter((r) => (r.dt_dias as number) < -32).length;
    const chosen = sens.find((r) => r.verde === "ndvi" && Number(r.umbral) === -1 && Number(r.persistencia) === 3) ?? null;
    const strip = $("d-strip");
    strip.innerHTML = "";
    strip.append(sensitivityStrip(sens, chosen, strip.clientWidth || 300));
    $("d-sens").textContent = t.cSummary(sens.length, valid.length, pos, neg, valid.length - pos - neg);
  };
  // Arranca en un caso con ambas recuperaciones de la señal elegida (el de mayor severidad)
  const pickDefault = () => {
    const best = ph.eventos.filter((e) => e.funcion === state.dualFn && e.estado === "ambos_recuperados")
      .sort((a, b) => (a.evento_severidad_spi3 ?? 0) - (b.evento_severidad_spi3 ?? 0))[0];
    if (best) $<HTMLSelectElement>("d-id").value = best.id;
    fillEvents();
    if (best) $<HTMLSelectElement>("d-ev").value = best.evento_inicio;
  };
  $("d-id").addEventListener("change", () => { fillEvents(); update(); });
  $("d-ev").addEventListener("change", update);
  document.querySelectorAll<HTMLButtonElement>("[data-fn]").forEach((b) => b.addEventListener("click", () => {
    state.dualFn = b.dataset.fn as State["dualFn"];
    document.querySelectorAll("[data-fn]").forEach((x) => x.classList.toggle("on", x === b));
    pickDefault();
    update();
  }));
  pickDefault();
  update();
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
    const color = worse ? "#f2b33d" : "#e6e6e6";
    L.circleMarker([p.lat, p.lon], { radius: 9, color, weight: 2.5, fillColor: color, fillOpacity: sig ? 0.95 : 0 })
      .bindTooltip(`${pointName(p.id)}: ${fmtSigned(tr.pendiente_decada, d)} ${meta.unidad} ${t.factPerDecade} · p = ${fmtP(tr.p_mk)}`)
      .addTo(map);
    bounds.push(L.latLng(p.lat, p.lon));
  }
  if (bounds.length) map.fitBounds(L.latLngBounds(bounds).pad(0.35), { maxZoom: 9 });
  document.getElementById("pm-title")!.textContent = `${meta.nombre} (${meta.unidad})`;
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
  const r = (location.hash.replace("#", "") || "investigar") as "investigar" | "expedientes" | "metodo";
  setNav(r);
  clearMaps();
  try {
    if (r === "expedientes") await viewCases();
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
  window.addEventListener("hashchange", () => route());
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
