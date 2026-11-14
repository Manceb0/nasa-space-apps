import "leaflet/dist/leaflet.css";
import "./style.css";
import L from "leaflet";
import { evidenceChart, rawChart, sensitivityStrip, spiChart, windowMatrix } from "./charts";
import { load, type Index, type Phantom, type SensRow, type Series, type Window } from "./data";
import {
  VERDICT_SHORT, digitsFor, fmt, fmtP, fmtSigned, multipleTestingNote, predictionFeedback, seasonLesson,
  trapText, verdictExplain, verdictSentence, windowLabel, type Prediction,
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

let index: Index;
let map: L.Map | null = null;
let mapLayers: L.Layer[] = [];

const esc = (s: string) => s.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]!));

function shell(): void {
  app.innerHTML = `
    <header class="bar">
      <a class="brand" href="#investigar" aria-label="Detective del Sistema Tierra, inicio">
        <svg viewBox="0 0 32 32" aria-hidden="true"><circle cx="16" cy="16" r="9" fill="#e3a33b"/><path d="M3 20c6-9 20-15 26-8" stroke="#e9edee" stroke-width="2.4" fill="none" stroke-linecap="round"/></svg>
        <span>Detective del Sistema Tierra</span>
      </a>
      <nav>
        <a href="#investigar" data-nav="investigar">Investigar</a>
        <a href="#expedientes" data-nav="expedientes">Expedientes</a>
        <a href="#metodo" data-nav="metodo">Cómo funciona</a>
      </nav>
      <span class="team">Stellar Horizons · NASA Space Apps 2026</span>
    </header>
    <main id="view"></main>
    <footer class="foot">
      <p>Datos: NASA GPM IMERG, MERRA-2 y GLDAS vía Giovanni; MODIS vía AppEEARS; mapa base NASA GIBS Blue Marble. Hecho en República Dominicana por Stellar Horizons. Código y método abiertos.</p>
    </footer>`;
}

function setNav(route: string) {
  document.querySelectorAll<HTMLAnchorElement>("[data-nav]").forEach((a) => a.classList.toggle("on", a.dataset.nav === route));
}

/* ───────────── Investigar ───────────── */

async function viewInvestigate() {
  const view = document.getElementById("view")!;
  const vmeta = index.variables[state.variable];
  const rmeta = index.regiones[state.region];
  view.innerHTML = `
    <section class="intro">
      <h1>Elige qué investigar. Predice. Comprueba.</h1>
      <p class="lede">Datos reales de la NASA sobre dos zonas de bosque seco de República Dominicana, de 2001 a 2024. Antes de ver la respuesta, di qué crees que pasó.</p>
    </section>

    <section class="pick">
      <div class="pick-left">
        <h2>¿Qué quieres investigar?</h2>
        <div class="choices" role="radiogroup" aria-label="Variable">
          ${Object.entries(index.variables).map(([k, v]) => `
            <button class="choice ${k === state.variable ? "on" : ""}" data-var="${k}" role="radio" aria-checked="${k === state.variable}">
              <strong>${esc(v.nombre)}</strong><span>${esc(v.pregunta)}</span>
            </button>`).join("")}
        </div>
        <p class="def">${esc(vmeta.definicion)} Se mide en ${esc(vmeta.unidad_larga)}. <span class="kind">Tipo de dato: ${esc(vmeta.tipo)}.</span></p>
        <h2>¿Dónde?</h2>
        <div class="choices two" role="radiogroup" aria-label="Zona">
          ${Object.entries(index.regiones).map(([k, r]) => `
            <button class="choice ${k === state.region ? "on" : ""}" data-reg="${k}" role="radio" aria-checked="${k === state.region}">
              <strong>${esc(r.nombre)}</strong><span>${esc(r.zona)}</span>
            </button>`).join("")}
        </div>
        <p class="def">${esc(rmeta.descripcion)}</p>
      </div>
      <figure class="pick-map">
        <div id="map" aria-label="Mapa de la zona elegida"></div>
        <figcaption id="mapcap"></figcaption>
      </figure>
    </section>

    <section class="predict" id="predict">
      <h2>Tu hipótesis</h2>
      <p class="q">Desde 2001, ${esc(vmeta.nombre.toLowerCase())} en ${esc(rmeta.nombre)}…</p>
      <div class="answers">
        ${(["sube", "baja", "nada"] as Prediction[]).map((p) => `
          <button class="answer ${state.prediction === p ? "on" : ""}" data-pred="${p}">${{ sube: "ha aumentado", baja: "ha disminuido", nada: "no cambió de forma clara" }[p]}</button>`).join("")}
      </div>
      <button class="reveal" id="reveal" ${state.prediction ? "" : "disabled"}>Revelar la evidencia</button>
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
  const el = document.getElementById("map");
  if (!el) return;
  if (map) { map.remove(); map = null; }
  const r = index.regiones[s.region];
  map = L.map(el, { zoomControl: true, attributionControl: true, scrollWheelZoom: false }).setView(r.centro, 8);
  const zoomTo = s.pasaporte.caja_pedida;
  L.tileLayer("https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/BlueMarble_ShadedRelief_Bathymetry/default/GoogleMapsCompatible_Level8/{z}/{y}/{x}.jpeg", {
    maxNativeZoom: 8, maxZoom: 10, attribution: "NASA GIBS · Blue Marble",
  }).addTo(map);
  mapLayers = [];
  const p = s.pasaporte;
  const toBounds = (b: number[]) => L.latLngBounds([b[1], b[0]], [b[3], b[2]]);
  if (p.caja_pedida) mapLayers.push(L.rectangle(toBounds(p.caja_pedida), { color: "#e9edee", weight: 1.5, dashArray: "4 4", fill: false }).addTo(map));
  let note = "Línea discontinua: zona pedida.";
  if (p.caja_datos) {
    const [w, so, e, n] = p.caja_datos;
    if (w === e && so === n) {
      mapLayers.push(L.circleMarker([so, w], { radius: 7, color: "#e3a33b", weight: 2, fillOpacity: 0.6 }).addTo(map));
      note += " Punto ámbar: centro de la única celda del modelo que usa Giovanni (queda fuera de la zona).";
    } else {
      mapLayers.push(L.rectangle(toBounds(p.caja_datos), { color: "#e3a33b", weight: 2, fillOpacity: 0.12 }).addTo(map));
      note += " Recuadro ámbar: celdas de datos que promedia Giovanni.";
    }
  }
  if (zoomTo) map.fitBounds(toBounds(zoomTo).pad(1.6), { maxZoom: 9 });
  document.getElementById("mapcap")!.textContent = note;
}

async function renderEvidence(scroll: boolean) {
  const host = document.getElementById("evidence")!;
  const s = await load<Series>(`series/${state.variable}_${state.region}.json`);
  const meta = index.variables[state.variable];
  const rname = index.regiones[state.region].nombre;
  const full = s.completa;
  const years = s.anual.anios;
  const span = `${years[0]} y ${years[years.length - 1]}`;
  const fb = predictionFeedback(state.prediction ?? "nada", full);
  const mt = multipleTestingNote(full, index.series.length);
  const d = digitsFor(meta);
  host.innerHTML = `
    <section class="evidence">
      <p class="feedback ${fb.ok === true ? "yes" : fb.ok === false ? "no" : "maybe"}">${esc(fb.text)}</p>
      <h2 class="verdict">${esc(verdictSentence(meta, rname, full, span))}</h2>
      <p class="explain">${esc(verdictExplain(meta, full))}</p>
      ${mt ? `<p class="warn">${esc(mt)}</p>` : ""}
      <div class="facts">
        <p><span class="big">${fmtSigned(full.pendiente_decada, d)}</span> ${esc(meta.unidad)} por década <em>pendiente Theil-Sen</em></p>
        <p><span class="big">${fmtSigned(full.ic95_decada[0], d)} a ${fmtSigned(full.ic95_decada[1], d)}</span> <em>rango probable (IC 95 %)</em></p>
        <p><span class="big">${fmtP(full.p_mk)}</span> <em>p de Mann-Kendall, corregido porque los años se parecen entre sí</em></p>
        <p><span class="big">${full.n}</span> <em>años completos</em></p>
      </div>
      <div class="chart-head">
        <h3>${state.raw ? "Los datos tal como llegan" : "Cada año comparado con lo normal"}</h3>
        <button class="toggle" id="rawtoggle">${state.raw ? "Ver sin la estación" : "Ver los datos crudos"}</button>
      </div>
      <div id="chart" class="chart"></div>
      <p class="caption">${state.raw
        ? esc(seasonLesson(meta, s.amplitud_estacional, full, full.n))
        : "Cada punto es un año: cuánto se separó, en promedio, de lo normal para cada mes. La recta ámbar es la tendencia (Theil-Sen); la franja, las pendientes compatibles con los datos."}</p>
    </section>

    <section class="challenge">
      <h2>¿Y si miras otro intervalo?</h2>
      <p class="lede small">Cada cuadro es un intervalo de 10 años o más: la fila dice el año en que empieza y la columna, el año en que termina. Ámbar intenso: mirando solo esos años concluirías una tendencia significativa (▲ sube, ▼ baja). Ámbar tenue: un indicio. Gris: nada claro. Toca cualquiera y compara.</p>
      <div class="challenge-grid">
        <div id="matrix"></div>
        <div class="challenge-side">
          <div id="wininfo"></div>
          ${s.ventanas_que_enganan.length ? `
            <h3>Intervalos que engañan</h3>
            <div class="traps">${s.ventanas_que_enganan.map((w, i) => `<button class="trap" data-trap="${i}">${windowLabel(w)}</button>`).join("")}</div>
            <p class="small">Escoger el intervalo que confirma lo que uno quiere ver es uno de los errores más comunes en ciencia. Por eso aquí se ven todos.</p>` : `
            <p class="small">Ningún intervalo de 10 años o más contradice la serie completa: la conclusión no depende de qué años mires.</p>`}
        </div>
      </div>
    </section>

    <details class="passport">
      <summary>Pasaporte de la evidencia</summary>
      <dl>
        <dt>Fuente</dt><dd>${esc(s.pasaporte.fuente)}</dd>
        <dt>Variable</dt><dd>${esc(s.pasaporte.producto)}</dd>
        <dt>Herramienta</dt><dd>${esc(s.pasaporte.herramienta)}</dd>
        <dt>Zona pedida</dt><dd>${s.pasaporte.caja_pedida ? s.pasaporte.caja_pedida.join(", ") : "—"} (oeste, sur, este, norte)</dd>
        <dt>Datos usados</dt><dd>${s.pasaporte.caja_datos ? s.pasaporte.caja_datos.join(", ") : "—"}</dd>
        <dt>Archivo</dt><dd>${esc(s.pasaporte.archivo)} · ${esc(s.pasaporte.verificacion)}</dd>
        <dt>Método</dt><dd>${esc(s.pasaporte.metodo)}</dd>
        <dt>Autocorrelación</dt><dd>lag 1 anual = ${full.autocorr_lag1 === null ? "—" : fmt(full.autocorr_lag1, 2)}; la varianza de Mann-Kendall se multiplicó por ${fmt(full.factor_varianza_ar1, 2)} (p sin corregir: ${fmtP(full.p_mk_simple)})</dd>
        <dt>Comparaciones múltiples</dt><dd>q de Benjamini-Hochberg sobre ${index.series.length} series = ${full.q_bh === undefined ? "—" : fmtP(full.q_bh)}</dd>
        <dt>Código</dt><dd>${esc(s.pasaporte.codigo)}</dd>
        <dt>Reproducir</dt><dd>${s.pasaporte.url_reproducir ? `<a href="${esc(s.pasaporte.url_reproducir)}" target="_blank" rel="noopener">Abrir la misma consulta en Giovanni</a>` : "—"}</dd>
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
      el.innerHTML = `<p class="wtitle">Serie completa ${years[0]}–${years[years.length - 1]}</p><p>${VERDICT_SHORT[full.veredicto]}. Toca un cuadro para ver otro intervalo.</p>`;
      return;
    }
    const isTrap = s.ventanas_que_enganan.some((t) => t.inicio === w.inicio && t.fin === w.fin);
    el.innerHTML = `
      <p class="wtitle">${windowLabel(w)} · ${w.fin - w.inicio + 1} años</p>
      <p><strong>${VERDICT_SHORT[w.veredicto]}</strong>: ${fmtSigned(w.pendiente_decada, d)} ${esc(meta.unidad)} por década (rango ${fmtSigned(w.ic95_decada[0], d)} a ${fmtSigned(w.ic95_decada[1], d)}), p = ${fmtP(w.p_mk)}.</p>
      ${isTrap ? `<p class="warn">${esc(trapText(w, full, meta))}</p>` : ""}
      <button class="toggle" id="clearwin">Volver a la serie completa</button>`;
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

// Modo de prueba local: ?prueba=1 lee un archivo SINTÉTICO que solo existe en la máquina de desarrollo.
const TEST_MODE = new URLSearchParams(location.search).get("prueba") === "1";

async function viewCases() {
  const view = document.getElementById("view")!;
  const ph = await load<Phantom>(TEST_MODE ? "phantom-SINTETICO-prueba.json" : "phantom.json");
  const done = ph.estado_modis === "procesado" && ph.eventos.length > 0;
  view.innerHTML = `
    ${TEST_MODE ? `<p class="test-banner">DATOS SINTÉTICOS DE PRUEBA. Nada de esta página es un resultado real.</p>` : ""}
    <section class="intro">
      <h1>Expediente PHANTOM: ¿verde es recuperado?</h1>
      <p class="lede">Después de una sequía, el bosque puede volver a verse verde antes de volver a funcionar como antes. Este expediente compara cuándo se recupera el verdor (NDVI) y cuándo se recuperan dos señales de funcionamiento: la productividad estimada (GPP, un modelo) y la temperatura de las hojas frente a la del aire.</p>
    </section>

    <section class="case-status">
      <h2>${done ? (TEST_MODE ? "Resultados de prueba (sintéticos)" : "Resultados con datos MODIS reales") : "Estado: esperando los datos MODIS"}</h2>
      ${done ? "" : `<p>Los datos de vegetación se pidieron a NASA AppEEARS el 14 de noviembre: un pedido por puntos (5 lugares revisados en imagen satelital, 2001–2024) y uno por área (2 zonas, 2012–2021). Mientras no lleguen, este expediente <strong>no muestra ningún resultado</strong> sobre la brecha. Lo que sí es real desde ya: las sequías que vamos a estudiar.</p>`}
    </section>

    <section class="droughts">
      <h2>Las sequías del expediente</h2>
      <p class="small">SPI-3: lluvia de 3 meses comparada con lo normal para esa época (IMERG V07). Las franjas son las sequías que usamos: SPI-3 por debajo de −1 durante 2 meses o más.</p>
      ${ph.sequias.map((d, i) => `
        <h3>${esc(index.regiones[d.region].nombre)}</h3>
        <div class="chart" id="spi${i}"></div>`).join("")}
    </section>

    ${done ? phantomResults(ph) : ""}

    <section class="method-box">
      <h2>Cómo se decide "recuperado"</h2>
      <p>Cada señal se compara con lo normal para esa época del año (mediana de los años disponibles). Una señal está <strong>impactada</strong> si pasa 3 observaciones seguidas muy por debajo de lo normal (z &lt; −1,5). Se <strong>recupera</strong> cuando vuelve a menos de una desviación de lo normal (z ≥ −1) y se queda ahí 3 observaciones seguidas. Si la siguiente sequía llega antes, el evento queda <strong>censurado</strong>: no inventamos cuánto habría tardado.</p>
      <p>Δt = día en que se recupera la función − día en que se recupera el verdor. Con compuestos de 8 y 16 días, una diferencia menor de 32 días no se distingue de cero.</p>
      <h3>Lo que este expediente no afirma</h3>
      <p>No mide la salud completa del ecosistema. GPP sale de un modelo que usa en parte el mismo verdor, así que no es independiente; por eso añadimos la señal térmica. Cinco puntos son una exploración, no la superficie afectada de una región.</p>
    </section>

    <section class="intro">
      <h1>Expediente 2: ¿llega la siguiente sequía antes de recuperarse?</h1>
      <p class="lede">Una colisión ocurre cuando empieza una nueva sequía mientras el verdor todavía está por debajo de lo normal tras la anterior.</p>
      ${ph.colisiones
        ? `<p class="verdict">${ph.colisiones.colisiones} colisiones en ${ph.colisiones.eventos_evaluados} sequías evaluadas (punto × evento).</p>`
        : `<p>Pendiente de los mismos datos MODIS. La regla ya está programada y probada.</p>`}
    </section>`;

  ph.sequias.forEach((d, i) => {
    const el = document.getElementById(`spi${i}`)!;
    el.append(spiChart(d, el.clientWidth || 800));
  });
  if (done) wirePhantom(ph);
}

function phantomResults(ph: Phantom): string {
  const ids = [...new Set(ph.eventos.map((e) => e.id))];
  const rows = ph.eventos.map((e) => `
    <tr>
      <td>${esc(e.id)}</td><td>${esc(e.evento_inicio.slice(0, 7))}</td>
      <td>${e.funcion === "gpp_modelo" ? "GPP (modelo)" : "Hojas vs. aire"}</td>
      <td>${esc(e.estado.replace(/_/g, " "))}</td>
      <td class="num">${e.dt_dias === null ? "—" : (e.dt_es_cota_inferior ? "≥ " : "") + fmt(e.dt_dias, 0)}</td>
      <td>${esc(e.rob_etiqueta)}</td>
    </tr>`).join("");
  return `
    <section class="results">
      <h2>Brecha por sequía y punto</h2>
      <div class="table-wrap"><table>
        <thead><tr><th>Punto</th><th>Sequía</th><th>Señal de función</th><th>Estado</th><th class="num">Δt (días)</th><th>Robustez</th></tr></thead>
        <tbody>${rows}</tbody>
      </table></div>
    </section>
    <section class="challenge">
      <h2>Cuestiona el hallazgo</h2>
      <p class="lede small">Cambia los supuestos. Las 18 combinaciones están <strong>precalculadas por el mismo código</strong> del análisis (phantom/recovery.py); aquí eliges cuál ver y compruebas si la conclusión se mantiene.</p>
      <div class="controls">
        <label>Punto <select id="c-id">${ids.map((i) => `<option>${esc(i)}</option>`).join("")}</select></label>
        <label>Sequía <select id="c-ev"></select></label>
        <label>Señal <select id="c-fn"><option value="gpp_modelo">GPP (modelo)</option><option value="lst_menos_aire">Hojas vs. aire</option></select></label>
        <label>Verdor <select id="c-gr"><option value="ndvi">NDVI</option><option value="evi">EVI</option></select></label>
        <label>Umbral <select id="c-th"><option>-1.5</option><option selected>-1</option><option>-0.5</option></select></label>
        <label>Persistencia <select id="c-pe"><option>2</option><option selected>3</option><option>4</option></select></label>
      </div>
      <div id="c-out"></div>
      <div id="c-strip" class="chart"></div>
    </section>`;
}

function wirePhantom(ph: Phantom) {
  const $ = <T extends HTMLElement>(id: string) => document.getElementById(id) as T;
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
    $("c-out").innerHTML = `
      <p class="verdict">${chosen ? (chosen.dt_dias === null ? `Con estos supuestos: ${esc(chosen.estado.replace(/_/g, " "))}.` : `Con estos supuestos: Δt = ${fmt(chosen.dt_dias, 0)} días.`) : "Combinación no disponible."}</p>
      <p>De ${rows.length} combinaciones, ${valid.length} tienen ambas recuperaciones: ${pos} dan la función más de 32 días después del verdor, ${neg} más de 32 días antes, y ${valid.length - pos - neg} quedan dentro de la precisión del método.</p>`;
    const strip = $("c-strip");
    strip.innerHTML = "";
    strip.append(sensitivityStrip(rows, chosen ?? null, strip.clientWidth || 800));
  };
  $("c-id").addEventListener("change", () => { fillEvents(); update(); });
  ["c-ev", "c-fn", "c-gr", "c-th", "c-pe"].forEach((i) => $(i).addEventListener("change", update));
  fillEvents();
  update();
}

/* ───────────── Cómo funciona ───────────── */

function viewMethod() {
  const view = document.getElementById("view")!;
  const terms: [string, string][] = [
    ["Variable", "Lo que se mide: lluvia, temperatura, humedad. Cada una tiene una unidad y una fuente."],
    ["Estacionalidad", "El ciclo que se repite cada año: la temporada de lluvias, el verano. Es mucho más grande que una tendencia de décadas, así que hay que quitarla primero."],
    ["Anomalía", "Cuánto se separa un mes de su promedio para ese mismo mes. Junio se compara con los otros junios, no con enero."],
    ["Tendencia", "Hacia dónde se mueve la serie con los años. Usamos la pendiente de Theil-Sen: la mediana de las pendientes entre todos los pares de años, que no se deja arrastrar por un año extremo."],
    ["Significancia", "Si no hubiera ninguna tendencia real, ¿qué tan raro sería ver un patrón así de ordenado? Eso es el valor p de la prueba de Mann-Kendall. Menos de 0,05 se suele llamar significativo."],
    ["Autocorrelación", "Cuando un año se parece al anterior, los datos tienen menos información de la que aparentan. Corregimos la prueba por eso; si no, encontraría tendencias donde no las hay."],
    ["Intervalo de confianza", "El rango de pendientes compatibles con los datos. Si incluye el cero, no podemos decir hacia dónde va."],
    ["Muchas pruebas", "Si pruebas muchas series, alguna saldrá significativa por azar. El valor q (Benjamini-Hochberg) corrige por eso."],
    ["Sin evidencia no es sin cambio", "Que una tendencia no sea significativa solo dice que estos datos no alcanzan para afirmarla. A veces solo hacen falta más años."],
  ];
  view.innerHTML = `
    <section class="intro">
      <h1>Cómo piensa un detective de datos</h1>
      <p class="lede">Ningún número de esta herramienta está escrito a mano: todos salen del mismo código abierto que corre sobre los datos de la NASA. Estas son las ideas que usa.</p>
    </section>
    <section class="glossary"><dl>${terms.map(([t, d]) => `<dt>${t}</dt><dd>${d}</dd>`).join("")}</dl></section>
    <section class="intro">
      <h2>Límites que hay que conocer</h2>
      <p>MERRA-2 y GLDAS son modelos, no mediciones directas, y sus celdas son más grandes que las zonas. GLDAS usa la lluvia como dato de entrada: si coincide con IMERG, no es una confirmación independiente. Con 24 años, una tendencia pequeña puede existir sin ser detectable.</p>
      <p class="small">Datos actualizados: ${esc(index.generado)}. Método completo: METHODOLOGY.md en el repositorio.</p>
    </section>`;
}

/* ───────────── Router ───────────── */

async function route() {
  const r = (location.hash.replace("#", "") || "investigar") as "investigar" | "expedientes" | "metodo";
  setNav(r);
  if (map && r !== "investigar") { map.remove(); map = null; }
  try {
    if (r === "expedientes") await viewCases();
    else if (r === "metodo") viewMethod();
    else await viewInvestigate();
  } catch (e) {
    document.getElementById("view")!.innerHTML = `<section class="intro"><h2>No se pudieron cargar los datos</h2><p>${esc(String(e))}</p></section>`;
  }
  window.scrollTo({ top: 0 });
}

async function start() {
  shell();
  index = await load<Index>("index.json");
  window.addEventListener("hashchange", route);
  let t: number | undefined;
  window.addEventListener("resize", () => {
    clearTimeout(t);
    t = window.setTimeout(() => { if (state.revealed && (location.hash === "" || location.hash === "#investigar")) renderEvidence(false); }, 200);
  });
  await route();
}

start();
