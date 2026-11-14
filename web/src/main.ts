import "leaflet/dist/leaflet.css";
import "./style.css";
import L from "leaflet";
import {
  DISCORDANT, dualTimeline, evidenceChart, gapIndex, heatmap, hysteresis, ledger, quadrant, rawChart, spiChart, windowMatrix,
} from "./charts";
import { load, type Audit, type Index, type Phantom, type Puntos, type Series, type Window } from "./data";
import { T, getLang, regionMeta, setLang, varMeta } from "./i18n";
import {
  digitsFor, fmt, fmtP, fmtSigned, multipleTestingNote, predictionFeedback, seasonLesson,
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
  fn: "gpp_modelo" | "lst_menos_aire";
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

function clearMaps() { while (maps.length) maps.pop()!.remove(); }

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
        <svg viewBox="0 0 32 32" aria-hidden="true"><circle cx="16" cy="16" r="9" fill="${AMBER}"/><path d="M3 20c6-9 20-15 26-8" stroke="#ffffff" stroke-width="2.4" fill="none" stroke-linecap="round"/></svg>
        <span>${esc(t.brand)}</span>
      </a>
      <nav>
        <a href="#investigar" data-nav="investigar">${esc(t.navInvestigate)}</a>
        <a href="#expedientes" data-nav="expedientes">${esc(t.navAudit)}</a>
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
  const ph = !TEST_MODE ? await load<Phantom>("phantom.json") : null;
  const auds = (ph?.auditorias ?? []).filter((a) => a.veredicto !== "sin_impacto");
  const count = (v: string) => auds.filter((a) => a.veredicto === v).length;

  view.innerHTML = `
    <div class="title-row">
      <h1>${esc(t.invTitle)}</h1>
      <p>${esc(t.invSub)}</p>
    </div>

    <section class="card hero">
      <div class="hero-map">
        <div class="seg" role="radiogroup" aria-label="${esc(t.whereH)}">
          ${Object.keys(index.regiones).map((k) => `<button data-reg="${k}" class="${k === state.region ? "on" : ""}">${esc(regionMeta(index, k).nombre)}</button>`).join("")}
        </div>
        <div id="map" aria-label="${esc(t.mapLabel)}"></div>
        <figcaption id="mapcap"></figcaption>
      </div>
      <div class="hero-pick">
        <h2>${esc(t.whatQ)}</h2>
        ${groups.filter(([, ks]) => ks.length).map(([title, ks]) => `
          <p class="group">${esc(title)}</p>
          <div class="vlist" role="radiogroup" aria-label="${esc(title)}">
            ${ks.map((k) => { const v = varMeta(index, k); return `
              <button class="vrow ${k === state.variable ? "on" : ""}" data-var="${k}" role="radio" aria-checked="${k === state.variable}">
                <strong>${esc(v.nombre)}</strong><span>${esc(v.pregunta)}</span>
              </button>`; }).join("")}
          </div>`).join("")}
        <p class="def">${esc(vmeta.definicion)} <span class="kind">${esc(t.dataType)}: ${esc(vmeta.tipo)}.</span>${vmeta.aviso ? ` ${esc(vmeta.aviso)}` : ""}</p>
        <p class="def">${esc(rmeta.descripcion)}</p>
      </div>
    </section>

    <div class="grid">
      <section class="card s6 predict" id="predict">
        <h2>${esc(t.hypothesis)}</h2>
        <p class="q">${esc(t.since2001(vmeta.nombre.charAt(0).toLowerCase() + vmeta.nombre.slice(1), rmeta.nombre))}</p>
        <div class="answers">
          ${(["sube", "baja", "nada"] as Prediction[]).map((p) => `
            <button class="answer ${state.prediction === p ? "on" : ""}" data-pred="${p}">${esc(predLabel[p])}</button>`).join("")}
        </div>
        <button class="reveal" id="reveal" ${state.prediction ? "" : "disabled"}>${esc(t.reveal)}</button>
      </section>
    </div>

    <div id="evidence"></div>

    ${auds.length ? `
    <section class="band">
      <div>
        <h2>${esc(t.findingsH)}</h2>
        <p class="band-lead">${esc(t.verdictLead(auds.length, count("fantasma"), count("estres_invisible"), count("censurada"), count("inconclusa")))}</p>
        <a class="band-link" href="#expedientes">${esc(t.findingsGo)} →</a>
      </div>
      <div class="numbers band-numbers">
        ${(["fantasma", "estres_invisible", "censurada", "inconclusa"] as const).map((v) => `<p>${esc(t.verdictName[v])}<b>${count(v)}</b></p>`).join("")}
      </div>
    </section>` : ""}`;

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
  document.getElementById("reveal")!.addEventListener("click", () => { state.revealed = true; renderEvidence(true); });

  const all = await Promise.all(Object.keys(index.regiones).map((k) => load<Series>(`series/${state.variable}_${k}.json`)));
  drawRegionMap(all);
  if (state.revealed) renderEvidence(false);
}

function resetInvestigation() {
  state.prediction = null; state.revealed = false; state.window = null; state.raw = false;
}

/** El mapa protagonista: las dos zonas a la vez; la elegida en ámbar, la otra en blanco; clic para elegir. */
function drawRegionMap(all: Series[]) {
  const t = T();
  const el = document.getElementById("map");
  if (!el) return;
  const map = baseMap(el, [18.8, -71.2], 8);
  const toBounds = (b: number[]) => L.latLngBounds([b[1], b[0]], [b[3], b[2]]);
  const pts: L.LatLng[] = [];
  let note = t.mapDashed;
  for (const s of all) {
    const on = s.region === state.region;
    const color = on ? AMBER : "#ffffff";
    const pick = () => { if (!on) { state.region = s.region; resetInvestigation(); route(false); } };
    const p = s.pasaporte;
    if (p.puntos && p.puntos.length) {
      note = t.mapPoints;
      for (const [lat, lon, id] of p.puntos) {
        L.circleMarker([lat, lon], { radius: on ? 9 : 7, color, weight: 2, fillColor: color, fillOpacity: on ? 0.9 : 0.25 })
          .bindTooltip(pointName(id)).on("click", pick).addTo(map);
        pts.push(L.latLng(lat, lon));
      }
    } else {
      const box = p.caja_datos && !(p.caja_datos[0] === p.caja_datos[2]) ? p.caja_datos : p.caja_pedida;
      if (box) {
        L.rectangle(toBounds(box), { color, weight: on ? 2.5 : 1.5, dashArray: on ? undefined : "4 4", fillColor: color, fillOpacity: on ? 0.18 : 0.04 })
          .bindTooltip(regionMeta(index, s.region).nombre).on("click", pick).addTo(map);
        pts.push(toBounds(box).getNorthEast(), toBounds(box).getSouthWest());
      }
      if (p.caja_datos && p.caja_datos[0] === p.caja_datos[2] && on) {
        L.circleMarker([p.caja_datos[1], p.caja_datos[0]], { radius: 6, color: AMBER, weight: 2, fillOpacity: 0.6 }).addTo(map);
        note += t.mapPoint;
      }
    }
  }
  if (pts.length) map.fitBounds(L.latLngBounds(pts).pad(0.25), { maxZoom: 9 });
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
          <p class="small">${esc(t.trapsNote)}</p>` : `<p class="small" style="margin-top:14px">${esc(t.noTraps)}</p>`}
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
    chartEl.append(state.raw ? rawChart(s, meta.unidad, chartEl.clientWidth || 800) : evidenceChart(s, meta.unidad, state.window, chartEl.clientWidth || 800));
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
  if (scroll) host.scrollIntoView({ behavior: "smooth", block: "start" });
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
            <div class="seg" role="radiogroup" aria-label="${esc(t.heatH)}">${["modis_ndvi", "modis_lst", "modis_gpp"].map((v) => `<button data-heat="${v}" class="${state.heatVar === v ? "on" : ""}">${esc(varMeta(index, v).nombre)}</button>`).join("")}</div>
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
    const covs = ["ndvi", "gpp_modelo", "lst_menos_aire"].map((k) => (a[`${k}_cobertura`] as number) ?? 0);
    const stableN = Math.round(a.estabilidad * a.combinaciones);
    const items = [
      { l: t.chkGreen, ...sig("ndvi") },
      { l: t.chkEvi, ...sig("evi") },
      { l: t.chkGpp, ...sig("gpp_modelo") },
      { l: t.chkLst, ...sig("lst_menos_aire") },
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
    document.querySelectorAll(".fname").forEach((e) => { e.textContent = state.fn === "gpp_modelo" ? t.sigGpp : t.sigLst; });
    const z = pts?.z[a.id];
    if (!z) return;
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
  if (bounds.length) map.fitBounds(L.latLngBounds(bounds).pad(0.35), { maxZoom: 9 });
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
  window.addEventListener("hashchange", () => {
    if (["#investigar", "#expedientes", "#metodo", ""].includes(location.hash)) route();
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
