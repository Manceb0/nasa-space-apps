import "leaflet/dist/leaflet.css";
import "./style.css";
import L from "leaflet";
import { evidenceChart, rawChart, sensitivityStrip, spiChart, windowMatrix } from "./charts";
import { load, type Index, type Phantom, type SensRow, type Series, type Window } from "./data";
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
}
const state: State = { variable: "imerg_precip", region: "noroeste", prediction: null, revealed: false, window: null, raw: false };

// Modo de prueba local: ?prueba=1 lee un archivo SINTÉTICO que solo existe en la máquina de desarrollo.
const TEST_MODE = new URLSearchParams(location.search).get("prueba") === "1";

let index: Index;
let map: L.Map | null = null;

const POINT_NAMES: Record<string, string> = {
  montecristimontesecoa: "Montecristi A", montecristimontesecob: "Montecristi B", sierramontecristi: "Sierra de Montecristi",
  jaraguacomparacionseco: "Jaragua", cordilleracomparacionhumedo: "Cordillera Central",
};
const pointName = (id: string) => POINT_NAMES[id.replace(/_/g, "")] ?? id;

const esc = (s: string) => s.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]!));

function shell(): void {
  const t = T();
  document.title = t.title;
  app.innerHTML = `
    <header class="bar">
      <a class="brand" href="#investigar" aria-label="${esc(t.brand)}">
        <svg viewBox="0 0 32 32" aria-hidden="true"><circle cx="16" cy="16" r="9" fill="#e3a33b"/><path d="M3 20c6-9 20-15 26-8" stroke="#e9edee" stroke-width="2.4" fill="none" stroke-linecap="round"/></svg>
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
  view.innerHTML = `
    <section class="intro">
      <h1>${esc(t.h1)}</h1>
      <p class="lede">${esc(t.lede)}</p>
    </section>

    <section class="pick">
      <div class="pick-left">
        <h2>${esc(t.whatQ)}</h2>
        ${[[t.groupClimate, Object.keys(index.variables).filter((k) => !k.startsWith("modis_"))],
           [t.groupVeg, Object.keys(index.variables).filter((k) => k.startsWith("modis_"))]]
          .filter(([, ks]) => (ks as string[]).length).map(([title, ks]) => `
        <h3 class="group">${esc(title as string)}</h3>
        <div class="choices" role="radiogroup" aria-label="${esc(title as string)}">
          ${(ks as string[]).map((k) => { const v = varMeta(index, k); return `
            <button class="choice ${k === state.variable ? "on" : ""}" data-var="${k}" role="radio" aria-checked="${k === state.variable}">
              <strong>${esc(v.nombre)}</strong><span>${esc(v.pregunta)}</span>
            </button>`; }).join("")}
        </div>`).join("")}
        <p class="def">${esc(vmeta.definicion)} ${esc(t.measuredIn)} ${esc(vmeta.unidad_larga)}. <span class="kind">${esc(t.dataType)}: ${esc(vmeta.tipo)}.</span>${vmeta.aviso ? ` ${esc(vmeta.aviso)}` : ""}</p>
        <h2>${esc(t.whereQ)}</h2>
        <div class="choices two" role="radiogroup" aria-label="${esc(t.whereQ)}">
          ${Object.keys(index.regiones).map((k) => { const r = regionMeta(index, k); return `
            <button class="choice ${k === state.region ? "on" : ""}" data-reg="${k}" role="radio" aria-checked="${k === state.region}">
              <strong>${esc(r.nombre)}</strong><span>${esc(r.zona)}</span>
            </button>`; }).join("")}
        </div>
        <p class="def">${esc(rmeta.descripcion)}</p>
      </div>
      <figure class="pick-map">
        <div id="map" aria-label="${esc(t.mapLabel)}"></div>
        <figcaption id="mapcap"></figcaption>
      </figure>
    </section>

    <section class="predict" id="predict">
      <h2>${esc(t.hypothesis)}</h2>
      <p class="q">${esc(t.since2001(vmeta.nombre.charAt(0).toLowerCase() + vmeta.nombre.slice(1), rmeta.nombre))}</p>
      <div class="answers">
        ${(["sube", "baja", "nada"] as Prediction[]).map((p) => `
          <button class="answer ${state.prediction === p ? "on" : ""}" data-pred="${p}">${esc(predLabel[p])}</button>`).join("")}
      </div>
      <button class="reveal" id="reveal" ${state.prediction ? "" : "disabled"}>${esc(t.reveal)}</button>
    </section>

    <div id="evidence"></div>`;

  view.querySelectorAll<HTMLButtonElement>("[data-var]").forEach((b) => b.addEventListener("click", () => {
    state.variable = b.dataset.var!; resetInvestigation(); viewInvestigate();
  }));
  view.querySelectorAll<HTMLButtonElement>("[data-reg]").forEach((b) => b.addEventListener("click", () => {
    state.region = b.dataset.reg!; resetInvestigation(); viewInvestigate();
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
  drawMap(s);
  if (state.revealed) renderEvidence(false);
}

function resetInvestigation() {
  state.prediction = null; state.revealed = false; state.window = null; state.raw = false;
}

function drawMap(s: Series) {
  const t = T();
  const el = document.getElementById("map");
  if (!el) return;
  if (map) { map.remove(); map = null; }
  const r = index.regiones[s.region];
  map = L.map(el, { zoomControl: true, attributionControl: true, scrollWheelZoom: false }).setView(r.centro, 8);
  L.tileLayer("https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/BlueMarble_ShadedRelief_Bathymetry/default/GoogleMapsCompatible_Level8/{z}/{y}/{x}.jpeg", {
    maxNativeZoom: 8, maxZoom: 10, attribution: "NASA GIBS · Blue Marble",
  }).addTo(map);
  const p = s.pasaporte;
  const toBounds = (b: number[]) => L.latLngBounds([b[1], b[0]], [b[3], b[2]]);
  if (p.caja_pedida) L.rectangle(toBounds(p.caja_pedida), { color: "#e9edee", weight: 1.5, dashArray: "4 4", fill: false }).addTo(map);
  let note = t.mapDashed;
  if (p.caja_datos) {
    const [w, so, e, n] = p.caja_datos;
    if (w === e && so === n) {
      L.circleMarker([so, w], { radius: 7, color: "#e3a33b", weight: 2, fillOpacity: 0.6 }).addTo(map);
      note += t.mapPoint;
    } else {
      L.rectangle(toBounds(p.caja_datos), { color: "#e3a33b", weight: 2, fillOpacity: 0.12 }).addTo(map);
      note += t.mapBox;
    }
  }
  if (p.puntos && p.puntos.length) {
    const pts = p.puntos.map(([lat, lon]) => L.latLng(lat, lon));
    p.puntos.forEach(([lat, lon, id]) => L.circleMarker([lat, lon], { radius: 7, color: "#e3a33b", weight: 2, fillOpacity: 0.7 })
      .bindTooltip(pointName(id)).addTo(map!));
    note = t.mapPoints;
    map.fitBounds(L.latLngBounds(pts).pad(pts.length > 1 ? 1.2 : 0), { maxZoom: 9 });
    if (pts.length === 1) map.setView(pts[0], 9);
  } else if (p.caja_pedida) map.fitBounds(toBounds(p.caja_pedida).pad(1.6), { maxZoom: 9 });
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
    <section class="evidence">
      <p class="feedback ${fb.ok === true ? "yes" : fb.ok === false ? "no" : "maybe"}">${esc(fb.text)}</p>
      <h2 class="verdict">${esc(verdictSentence(meta, rname, full, y0, y1))}</h2>
      <p class="explain">${esc(verdictExplain(meta, full))}</p>
      ${mt ? `<p class="warn">${esc(mt)}</p>` : ""}
      <div class="facts">
        <p><span class="big">${fmtSigned(full.pendiente_decada, d)}</span> ${esc(meta.unidad)} ${esc(t.factPerDecade)} <em>${esc(t.factSlope)}</em></p>
        <p><span class="big">${fmtSigned(full.ic95_decada[0], d)} – ${fmtSigned(full.ic95_decada[1], d)}</span> <em>${esc(t.factRange)}</em></p>
        <p><span class="big">${fmtP(full.p_mk)}</span> <em>${esc(t.factP)}</em></p>
        <p><span class="big">${full.n}</span> <em>${esc(t.factYears)}</em></p>
      </div>
      <div class="chart-head">
        <h3>${esc(state.raw ? t.chartRaw : t.chartAnom)}</h3>
        <button class="toggle" id="rawtoggle">${esc(state.raw ? t.btnAnom : t.btnRaw)}</button>
      </div>
      <div id="chart" class="chart"></div>
      <p class="caption">${esc(state.raw ? seasonLesson(meta, s.amplitud_estacional, full, full.n) : t.captionAnom)}</p>
    </section>

    <section class="challenge">
      <h2>${esc(t.otherWindow)}</h2>
      <p class="lede small">${esc(t.windowLede)}</p>
      <div class="challenge-grid">
        <div id="matrix"></div>
        <div class="challenge-side">
          <div id="wininfo"></div>
          ${s.ventanas_que_enganan.length ? `
            <h3>${esc(t.trapsTitle)}</h3>
            <div class="traps">${s.ventanas_que_enganan.map((w, i) => `<button class="trap" data-trap="${i}">${windowLabel(w)}</button>`).join("")}</div>
            <p class="small">${esc(t.trapsNote)}</p>` : `
            <p class="small">${esc(t.noTraps)}</p>`}
        </div>
      </div>
    </section>

    <details class="passport">
      <summary>${esc(t.passport)}</summary>
      <dl>
        <dt>${esc(t.pSource)}</dt><dd>${esc(pp.fuente)}</dd>
        <dt>${esc(t.pVariable)}</dt><dd>${esc(pp.producto)}</dd>
        <dt>${esc(t.pTool)}</dt><dd>${esc(pp.herramienta)}</dd>
        <dt>${esc(t.pBox)}</dt><dd>${pp.caja_pedida ? pp.caja_pedida.join(", ") : "—"} ${esc(t.pBoxNote)}</dd>
        <dt>${esc(t.pData)}</dt><dd>${pp.puntos ? pp.puntos.map(([la, lo, id]) => `${pointName(id)} (${la}, ${lo})`).join(" · ") : pp.caja_datos ? pp.caja_datos.join(", ") : "—"}</dd>
        <dt>${esc(t.pFile)}</dt><dd>${esc(pp.archivo)} · ${esc(pp.puntos ? t.pVerifyModis : pp.reconstruido ? t.pVerifyRecon : t.pVerifyOrig)}</dd>
        <dt>${esc(t.pMethod)}</dt><dd>${esc(pp.puntos ? t.pMethodModis : t.pMethodText)}</dd>
        <dt>${esc(t.pAutocorr)}</dt><dd>${esc(t.pAutocorrText(full.autocorr_lag1 === null ? "—" : fmt(full.autocorr_lag1, 2), fmt(full.factor_varianza_ar1, 2), fmtP(full.p_mk_simple)))}</dd>
        <dt>${esc(t.pMulti)}</dt><dd>${esc(t.pMultiText(index.series.length, full.q_bh === undefined ? "—" : fmtP(full.q_bh)))}</dd>
        <dt>${esc(t.pCode)}</dt><dd>${esc(pp.codigo)}</dd>
        <dt>${esc(t.pRepro)}</dt><dd>${pp.url_reproducir ? `<a href="${esc(pp.url_reproducir)}" target="_blank" rel="noopener">${esc(t.pOpenGiovanni)}</a>` : "—"}</dd>
      </dl>
    </details>`;

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
      <p><strong>${esc(verdictShort(w.veredicto))}</strong>: ${fmtSigned(w.pendiente_decada, d)} ${esc(meta.unidad)} ${esc(t.factPerDecade)} (${esc(t.range)} ${fmtSigned(w.ic95_decada[0], d)} – ${fmtSigned(w.ic95_decada[1], d)}), p = ${fmtP(w.p_mk)}.</p>
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
  const done = ph.estado_modis === "procesado" && ph.eventos.length > 0;
  view.innerHTML = `
    ${TEST_MODE ? `<p class="test-banner">${esc(t.testBanner)}</p>` : ""}
    <section class="intro">
      <h1>${esc(t.caseH1)}</h1>
      <p class="lede">${esc(t.caseLede)}</p>
    </section>

    <section class="case-status">
      <h2>${esc(done ? (TEST_MODE ? t.caseResultsTest : t.caseResultsReal) : t.caseWaiting)}</h2>
      ${done ? `<p>${esc(TEST_MODE ? "" : t.caseRealNote)}</p>` : `<p>${t.caseWaitingText}</p>`}
    </section>

    <section class="droughts">
      <h2>${esc(t.droughtsH)}</h2>
      <p class="small">${esc(t.droughtsNote)}</p>
      ${ph.sequias.map((d, i) => `
        <h3>${esc(regionMeta(index, d.region).nombre)}</h3>
        <div class="chart" id="spi${i}"></div>`).join("")}
    </section>

    ${done ? phantomResults(ph) : ""}

    <section class="method-box">
      <h2>${esc(t.howH)}</h2>
      <p>${t.howP1}</p>
      <p>${esc(t.howP2)}</p>
      <h3>${esc(t.notClaimH)}</h3>
      <p>${esc(t.notClaim)}</p>
    </section>

    <section class="intro">
      <h1>${esc(t.case2H)}</h1>
      <p class="lede">${esc(t.case2Lede)}</p>
      ${ph.colisiones
        ? `<p class="verdict">${esc(t.case2Count(ph.colisiones.colisiones, ph.colisiones.eventos_evaluados))}</p>`
        : `<p>${esc(t.case2Pending)}</p>`}
    </section>`;

  ph.sequias.forEach((d, i) => {
    const el = document.getElementById(`spi${i}`)!;
    el.append(spiChart(d, el.clientWidth || 800));
  });
  if (done) wirePhantom(ph);
}

function phantomResults(ph: Phantom): string {
  const t = T();
  const ids = [...new Set(ph.eventos.map((e) => e.id))];
  const informative = ph.eventos.filter((e) => e.estado !== "sin_impacto");
  const both = ph.eventos.filter((e) => e.estado === "ambos_recuperados" && e.dt_dias !== null);
  const after = both.filter((e) => (e.dt_dias as number) > 32);
  const before = both.filter((e) => (e.dt_dias as number) < -32);
  const within = both.length - after.length - before.length;
  // Una caída de la función que empieza cuando el verdor ya se recuperó no es "recuperación tardía"
  const robustAfter = after.filter((e) => e.rob_etiqueta === "ROBUSTO" && !e.funcion_cae_despues_del_verde);
  const lateDips = after.filter((e) => e.funcion_cae_despues_del_verde);
  const robustBefore = before.filter((e) => e.rob_etiqueta === "ROBUSTO")
    .concat(both.filter((e) => e.rob_etiqueta === "ROBUSTO" && (e.rob_dt_mediana ?? 0) < -32 && !before.includes(e)));
  const supported = after.length > before.length && robustAfter.length > 0;
  const rows = informative.map((e) => `
    <tr>
      <td>${esc(pointName(e.id))}</td><td>${esc(e.evento_inicio.slice(0, 7))}</td>
      <td>${esc(e.funcion === "gpp_modelo" ? t.sigGpp : t.sigLst)}</td>
      <td>${esc(stateLabel(e.estado))}</td>
      <td class="num">${e.dt_dias === null ? "—" : (e.dt_es_cota_inferior ? "≥ " : "") + fmt(e.dt_dias, 0)}</td>
      <td>${esc(robustLabel(e.rob_etiqueta))}</td>
    </tr>`).join("");
  return `
    <section class="results">
      <h2>${esc(supported ? t.phantomYesH : t.phantomNoH)}</h2>
      <p class="verdict">${esc(t.phantomSummary(both.length, within, before.length, after.length))}</p>
      <p class="explain">${esc(t.phantomRobust(robustAfter.map((e) => `${pointName(e.id)} ${e.evento_inicio.slice(0, 4)} (${e.funcion === "gpp_modelo" ? t.sigGpp : t.sigLst}, +${fmt(e.dt_dias as number, 0)} ${t.days})`), robustBefore.length))}</p>
      ${lateDips.length ? `<p class="warn">${esc(t.phantomLateDip(lateDips.map((e) => `${pointName(e.id)} ${e.evento_inicio.slice(0, 4)} (${e.funcion === "gpp_modelo" ? t.sigGpp : t.sigLst}, +${fmt(e.dt_dias as number, 0)} ${t.days})`)))}</p>` : ""}
      <p class="small">${esc(t.phantomCaveat)}</p>
      <h3>${esc(t.gapTableH)}</h3>
      <div class="table-wrap"><table>
        <thead><tr><th>${esc(t.thPoint)}</th><th>${esc(t.thDrought)}</th><th>${esc(t.thSignal)}</th><th>${esc(t.thState)}</th><th class="num">${esc(t.thDt)}</th><th>${esc(t.thRobust)}</th></tr></thead>
        <tbody>${rows}</tbody>
      </table></div>
      <p class="small">${esc(t.hiddenRows(ph.eventos.length - informative.length))}</p>
    </section>
    <section class="challenge">
      <h2>${esc(t.challengeH)}</h2>
      <p class="lede small">${t.challengeLede}</p>
      <div class="controls">
        <label>${esc(t.cPoint)} <select id="c-id">${ids.map((i) => `<option value="${esc(i)}">${esc(pointName(i))}</option>`).join("")}</select></label>
        <label>${esc(t.cDrought)} <select id="c-ev"></select></label>
        <label>${esc(t.cSignal)} <select id="c-fn"><option value="gpp_modelo">${esc(t.sigGpp)}</option><option value="lst_menos_aire">${esc(t.sigLst)}</option></select></label>
        <label>${esc(t.cGreen)} <select id="c-gr"><option value="ndvi">NDVI</option><option value="evi">EVI</option></select></label>
        <label>${esc(t.cThreshold)} <select id="c-th"><option>-1.5</option><option selected>-1</option><option>-0.5</option></select></label>
        <label>${esc(t.cPersist)} <select id="c-pe"><option>2</option><option selected>3</option><option>4</option></select></label>
      </div>
      <div id="c-out"></div>
      <div id="c-strip" class="chart"></div>
    </section>`;
}

function wirePhantom(ph: Phantom) {
  const t = T();
  const $ = <E extends HTMLElement>(id: string) => document.getElementById(id) as E;
  const fillEvents = () => {
    const id = $<HTMLSelectElement>("c-id").value;
    const evs = [...new Set(ph.eventos.filter((e) => e.id === id).map((e) => e.evento_inicio))];
    $<HTMLSelectElement>("c-ev").innerHTML = evs.map((e) => `<option value="${e}">${e.slice(0, 7)}</option>`).join("");
  };
  const update = () => {
    const id = $<HTMLSelectElement>("c-id").value;
    const ev = $<HTMLSelectElement>("c-ev").value;
    const fn = $<HTMLSelectElement>("c-fn").value;
    const rows = ph.sensibilidad.filter((r) => r.id === id && r.evento_inicio.slice(0, 10) === ev.slice(0, 10) && r.funcion === fn);
    const chosen: SensRow | undefined = rows.find((r) => r.verde === $<HTMLSelectElement>("c-gr").value
      && Number(r.umbral) === Number($<HTMLSelectElement>("c-th").value)
      && Number(r.persistencia) === Number($<HTMLSelectElement>("c-pe").value));
    const valid = rows.filter((r) => r.estado === "ambos_recuperados" && r.dt_dias !== null);
    const pos = valid.filter((r) => (r.dt_dias as number) > 32).length;
    const neg = valid.filter((r) => (r.dt_dias as number) < -32).length;
    const head = chosen
      ? (chosen.dt_dias === null ? `${t.cWith} ${stateLabel(chosen.estado)}.` : `${t.cWith} Δt = ${fmt(chosen.dt_dias, 0)} ${t.days}.`)
      : t.cNA;
    $("c-out").innerHTML = `<p class="verdict">${esc(head)}</p><p>${esc(t.cSummary(rows.length, valid.length, pos, neg, valid.length - pos - neg))}</p>`;
    const strip = $("c-strip");
    strip.innerHTML = "";
    strip.append(sensitivityStrip(rows, chosen ?? null, strip.clientWidth || 800));
  };
  $("c-id").addEventListener("change", () => { fillEvents(); update(); });
  ["c-ev", "c-fn", "c-gr", "c-th", "c-pe"].forEach((i) => $(i).addEventListener("change", update));
  // Empieza en un caso con ambas recuperaciones (el robusto de mayor |Δt| si existe), no en uno vacío
  const start = [...ph.eventos].filter((e) => e.estado === "ambos_recuperados")
    .sort((x, y) => Number(y.rob_etiqueta === "ROBUSTO") - Number(x.rob_etiqueta === "ROBUSTO")
      || Math.abs(y.dt_dias ?? 0) - Math.abs(x.dt_dias ?? 0))[0];
  if (start) {
    $<HTMLSelectElement>("c-id").value = start.id;
    fillEvents();
    $<HTMLSelectElement>("c-ev").value = start.evento_inicio;
    $<HTMLSelectElement>("c-fn").value = start.funcion;
  } else fillEvents();
  update();
}

/* ───────────── Cómo funciona ───────────── */

function viewMethod() {
  const t = T();
  const view = document.getElementById("view")!;
  view.innerHTML = `
    <section class="intro">
      <h1>${esc(t.methodH1)}</h1>
      <p class="lede">${esc(t.methodLede)}</p>
    </section>
    <section class="glossary"><dl>${t.glossary.map(([a, b]) => `<dt>${esc(a)}</dt><dd>${esc(b)}</dd>`).join("")}</dl></section>
    <section class="intro">
      <h2>${esc(t.limitsH)}</h2>
      <p>${esc(t.limits)}</p>
      <p class="small">${esc(t.updated(index.generado))}</p>
    </section>`;
}

/* ───────────── Router ───────────── */

async function route(scrollTop = true) {
  const r = (location.hash.replace("#", "") || "investigar") as "investigar" | "expedientes" | "metodo";
  setNav(r);
  if (map) { map.remove(); map = null; }
  try {
    if (r === "expedientes") await viewCases();
    else if (r === "metodo") viewMethod();
    else await viewInvestigate();
  } catch (e) {
    document.getElementById("view")!.innerHTML = `<section class="intro"><h2>${esc(T().loadError)}</h2><p>${esc(String(e))}</p></section>`;
  }
  if (scrollTop) window.scrollTo({ top: 0 });
}

async function start() {
  shell();
  index = await load<Index>("index.json");
  window.addEventListener("hashchange", () => route());
  let timer: number | undefined;
  window.addEventListener("resize", () => {
    clearTimeout(timer);
    timer = window.setTimeout(() => {
      if (state.revealed && (location.hash === "" || location.hash === "#investigar")) renderEvidence(false);
    }, 200);
  });
  await route();
}

start();
