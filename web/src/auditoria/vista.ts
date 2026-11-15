// Auditoría de la decisión de sequía. Pantalla de trabajo, misma dirección que Tendencias (true-black-flat).
// Pregunta de la pantalla: «Cuando un producto de lluvia declara sequía, ¿los otros tres dicen lo mismo?»
// Cara: el código de barras de la duda, vivo: 32 provincias × 288 meses; al pasar el cursor, lo que dice cada fuente;
// la leyenda es un filtro (toca «Los 4 dicen sequía» y aparece 2015). El panel izquierdo responde con cifras y guarda,
// plegadas, las piezas de la galería que explican por qué (genealogía, tormenta, prototipo, cuenca del Yuna).
import "../tendencias/tendencias.css";
import "./auditoria.css";
import { load } from "../data";
import { esc, LL, num } from "../tendencias/datos";
import { bottomSheet } from "../tendencias/hoja";

interface Fila {
  provincia: string; codigo: string; tasa_condicional: number; ic95: [number, number]; tasa_contradiccion_clara: number;
  n_alguna_alarma: number; n_no_unanime: number; estados: number[]; spi3: Record<string, (number | null)[]>;
}
interface CB {
  productos: string[]; meses: string[]; umbral_spi3: number;
  recuentos: Record<string, number>;
  nacional: { tasa_condicional: number; ic95_condicional: [number, number]; n_alguna_alarma: number; n_unanime_sequia: number; n_contradiccion_clara: number; tasa_contradiccion_clara: number; ic95_contradiccion_clara: [number, number] };
  por_anio_unanime: Record<string, number>;
  filas: Fila[];
}
type Nums = Record<string, Record<string, any>>; // eslint-disable-line @typescript-eslint/no-explicit-any
type Alt = Record<string, { es?: string; en?: string }>;

// Estados (mismos códigos y colores Okabe-Ito que la pieza 01 de la galería)
const ST: Record<number, { c: string; es: string; en: string }> = {
  3: { c: "#30d158", es: "Los 4 dicen sequía", en: "All 4 say drought" },
  2: { c: "#8a9099", es: "3 de 4", en: "3 of 4" },
  1: { c: "#4b5058", es: "1 o 2 de 4", en: "1 or 2 of 4" },
  4: { c: "#ff6b35", es: "Contradicción clara", en: "Clear contradiction" },
  0: { c: "#17191c", es: "Sin alarma", en: "No alarm" },
};
const ORDER = [3, 2, 1, 4, 0];
const KEY: Record<number, string> = { 3: "unanimous", 2: "majority", 1: "split", 4: "contradiction", 0: "no_alarm" };
const PNAME: Record<string, string> = { IMERG: "IMERG", CHIRPS: "CHIRPS", GLDAS_forzamiento: "GLDAS", MERRA2: "MERRA-2" };
const CHEV = '<svg class="chev" viewBox="0 0 12 12" aria-hidden="true"><path d="M3 4.5l3 3 3-3" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>';
const MARK = '<svg viewBox="0 0 32 32" aria-hidden="true"><path d="M16 2.5l2.3 8.2 8.2 2.3-8.2 2.3L16 23.5l-2.3-8.2-8.2-2.3 8.2-2.3z" fill="#f2b33d"/><path d="M2.5 28.5c7.5-4.6 19.5-4.6 27 0" stroke="#fff" stroke-width="2.2" fill="none" stroke-linecap="round"/></svg>';
const PANEL_L = '<svg viewBox="0 0 16 16" aria-hidden="true"><rect x="1.75" y="2.75" width="12.5" height="10.5" rx="2" fill="none" stroke="currentColor" stroke-width="1.5"/><path d="M6 3v10" stroke="currentColor" stroke-width="1.5"/></svg>';
const MES_ES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"];
const MES_EN = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
const pct = (x: number) => `${num(x * 100, 0)} %`;
const int = (x: number) => Math.round(x).toLocaleString(LL("es-DO", "en-US"));

const ui = { reg: "DO", filter: null as number | null, left: true };
let cleanup: (() => void)[] = [];

/** Abre la Auditoría ya situada en un lugar (desde el veredicto de Tendencias). */
export function openAuditAt(reg: string) { ui.reg = reg; }

export function destroyAudit() {
  cleanup.forEach((f) => f()); cleanup = [];
  document.body.classList.remove("wx-on");
}

export async function viewAudit(view: HTMLElement) {
  destroyAudit();
  document.body.classList.add("wx-on");
  view.innerHTML = `<div class="wx"><p class="wx-loading">${esc(LL("Cargando la auditoría…", "Loading the audit…"))}</p></div>`;
  const [cb, proc, nums, alt] = await Promise.all([
    load<CB>("auditoria/codigo_barras.json"), load<{ veredicto: string[] }>("auditoria/procedencia.json"),
    load<Nums>("../figuras/numeros.json").catch(() => ({} as Nums)), load<Alt>("../figuras/alt.json").catch(() => ({} as Alt)),
  ]);
  render(view, cb, proc, nums, alt);
}

function render(view: HTMLElement, cb: CB, proc: { veredicto: string[] }, nums: Nums, alt: Alt) {
  const phone = innerWidth < 760;
  const fig = (id: string, file: string) => `<button class="au-fig" data-fig="${file}" aria-label="${esc(LL("Ampliar figura", "Enlarge figure"))}"><img src="figuras/${file}" alt="${esc(alt[id]?.[LL("es", "en") as "es" | "en"] ?? "")}" loading="lazy" decoding="async"></button>`;
  const sec = (id: string, title: string, body: string) => `
    <details class="sec" id="${id}"><summary><h2>${title}</h2><span class="meta"></span>${CHEV}</summary><div class="sec-b">${body}</div></details>`;
  const n4 = nums["04_genealogy_of_the_data"] ?? {}, n5 = nums["05_bivariate_where_to_measure"] ?? {}, n6 = nums["06_santo_domingo_storm"] ?? {}, n1b = nums["01b_yuna_flood_atlas"] ?? {};
  const top5 = Object.entries((n5.provincias_clase_alta_alta ?? {}) as Record<string, number>).slice(0, 3).map(([k, v]) => `${k} ${v}`).join(", ");
  const km = (n1b.km2_por_umbral_eventos ?? {}) as Record<string, number>;
  const sections = [
    sec("au-gen", esc(LL("¿Por qué coincidir no es validar?", "Why agreeing is not validating")), `
      <p class="au-p">${esc(proc.veredicto[0] ?? "")}</p>
      ${fig("04_genealogy_of_the_data", "04_genealogy_of_the_data.png")}
      <p class="au-cap">${esc(LL(`${n4.n_verificadas ?? "—"} enlaces verificados y ${n4.n_inferidas ?? "—"} inferidos. ${(n4.insumos_compartidos_por_productos_de_sequia ?? []).length} de ${n4.n_insumos ?? "—"} insumos alimentan a dos o más de los cuatro productos.`, `${n4.n_verificadas ?? "—"} verified and ${n4.n_inferidas ?? "—"} inferred links. ${(n4.insumos_compartidos_por_productos_de_sequia ?? []).length} of ${n4.n_insumos ?? "—"} inputs feed two or more of the four products.`))}</p>`),
    sec("au-sd", esc(LL("Santo Domingo, 18-nov-2023: sin resolver", "Santo Domingo, 18 Nov 2023: unresolved")), `
      <div class="au-figs">
        <div><b class="num">${n6.imerg_celda_dia_utc_18_mm !== undefined ? num(n6.imerg_celda_dia_utc_18_mm, 0) : "—"}</b><span>mm · ${esc(LL("IMERG en la celda, día UTC 18", "IMERG at the cell, UTC day 18"))}</span></div>
        <div><b class="num">${n6.imerg_mejor_vecina_mejor_ventana_mm !== undefined ? num(n6.imerg_mejor_vecina_mejor_ventana_mm, 0) : "—"}</b><span>mm · ${esc(LL("mejor ventana de 24 h, celda vecina", "best 24 h window, neighbour cell"))}</span></div>
        <div><b class="num">${n6.estacion_mm !== undefined ? num(n6.estacion_mm, 0) : "—"}</b><span>mm · ${esc(LL("pluviómetro, 24 h", "rain gauge, 24 h"))}</span></div>
      </div>
      <img class="au-gif" data-src="figuras/06_santo_domingo_storm.gif" alt="${esc(alt["06_santo_domingo_storm"]?.[LL("es", "en") as "es" | "en"] ?? "")}" width="960" height="540">
      <p class="au-cap">${esc(LL(`Inconcluso: quedan ${n6.brecha_restante_mm !== undefined ? num(n6.brecha_restante_mm, 0) : "—"} mm sin atribuir, porque la ventana exacta y la coordenada del pluviómetro no son públicas. Sí se sostiene que un producto de 10 km no reproduce este extremo puntual.`, `Inconclusive: ${n6.brecha_restante_mm !== undefined ? num(n6.brecha_restante_mm, 0) : "—"} mm remain unattributed, because the gauge's exact window and coordinate are not public. What holds is that a 10 km product does not reproduce this point extreme.`))}</p>`),
    sec("au-med", `${esc(LL("¿Dónde medir?", "Where to measure?"))} <span class="au-proto">${esc(LL("Prototipo", "Prototype"))}</span>`, `
      ${fig("05_bivariate_where_to_measure", "05_bivariate_where_to_measure.png")}
      <p class="au-cap">${esc(LL(`${n5.n_celdas_clase_alta_alta ?? "—"} celdas con duda alta y pluviómetro lejos: ${top5}. No dice dónde instalar estaciones: faltan el acceso, la exposición, la población y la red de ONAMET e INDRHI.`, `${n5.n_celdas_clase_alta_alta ?? "—"} cells with high doubt and a distant gauge: ${top5}. It does not say where to install stations: access, exposure, population and the ONAMET and INDRHI network are missing.`))}</p>`),
    sec("au-yuna", esc(LL("Cuenca del Yuna: dónde estuvo el agua", "Yuna basin: where the water was")), `
      ${fig("01c_yuna_flood_recurrence", "01c_yuna_flood_recurrence.png")}
      <p class="au-cap">${esc(LL(`${km["1"] !== undefined ? num(km["1"], 0) : "—"} km² aparecen inundados en al menos uno de los 15 eventos y ${km["3"] !== undefined ? num(km["3"], 0) : "—"} km² en 3 o más, en la llanura de Villa Riva y Arenoso. MODIS no ve bajo las nubes: cada recuento es un mínimo.`, `${km["1"] !== undefined ? num(km["1"], 0) : "—"} km² show as flooded in at least one of the 15 events and ${km["3"] !== undefined ? num(km["3"], 0) : "—"} km² in 3 or more, on the Villa Riva and Arenoso plain. MODIS cannot see under cloud: each count is a minimum.`))}</p>
      ${fig("01b_yuna_flood_atlas", "01b_yuna_flood_atlas.png")}
      <p class="au-cap">${esc(LL("Los 15 eventos, el día de mayor extensión, con el mismo encuadre. La trama marca lo que el satélite no pudo ver ese día.", "The 15 events on their day of largest extent, same frame. Hatching marks what the satellite could not see that day."))}</p>`),
  ].join("");

  view.innerHTML = `
  <div class="wx au" id="au" data-left="${ui.left ? "on" : "off"}" data-right="off" data-layout="${phone ? "phone" : "wide"}">
    <header class="wx-top">
      <a class="wx-brand" href="#auditoria">${MARK}<b>Stellar Horizons</b><span>${esc(LL("Auditoría de la decisión", "Decision audit"))}</span></a>
    </header>
    <div class="wx-main">
      <aside class="wx-left" id="au-left">
        ${phone ? `<button class="wx-grab" id="au-grab" aria-label="${esc(LL("Subir o bajar el panel", "Raise or lower the panel"))}"><i></i></button>` : ""}
        <section class="blk-reg" id="au-peek">
          <div class="reg-row">
            <h1 id="au-h1"></h1>
            <label class="reg-pick"><span>${esc(LL("Cambiar", "Change"))}</span><select id="au-reg" aria-label="${esc(LL("Región", "Region"))}">
              <option value="DO">${esc(LL("Toda la República Dominicana", "Whole Dominican Republic"))}</option>
              ${[...cb.filas].sort((a, b) => a.provincia.localeCompare(b.provincia, "es")).map((f) => `<option value="${f.codigo}">${esc(f.provincia)}</option>`).join("")}
            </select>${CHEV}</label>
          </div>
          <p class="finding" id="au-find"></p>
        </section>
        <div class="wx-scroll">
          <section class="au-kpi" id="au-kpi" aria-live="polite"></section>
          <p class="au-note">${esc(LL("Los productos no son independientes: que coincidan no es una validación.", "The products are not independent: agreement is not validation."))}</p>
          ${sections}
          <p class="fine">${esc(LL(`SPI-3 ≤ ${num(cb.umbral_spi3, 1)} con NASA GPM IMERG V07, CHC CHIRPS v2.0, lluvia de forzamiento de GLDAS-2.1 y MERRA-2 (NASA POWER), 2001–2024. IC del 95 % por bootstrap de bloques de año. Figuras: galería Stellar Horizons.`, `SPI-3 ≤ ${num(cb.umbral_spi3, 1)} with NASA GPM IMERG V07, CHC CHIRPS v2.0, GLDAS-2.1 forcing rain and MERRA-2 (NASA POWER), 2001–2024. 95 % CI by year-block bootstrap. Figures: Stellar Horizons gallery.`))}</p>
        </div>
      </aside>
      <section class="wx-mapcol au-stage" aria-labelledby="au-q">
        <div class="map-top">
          ${phone ? "" : `<button class="fold" data-fold="left" aria-controls="au-left">${PANEL_L}</button>`}
          <h2 class="au-q" id="au-q">${esc(LL("Mes a mes: cuando uno declara sequía, ¿qué dicen los otros tres?", "Month by month: when one declares drought, what do the other three say?"))}</h2>
        </div>
        <canvas class="au-cv" id="au-cv" role="img" aria-label="${esc(alt["01_barcode_of_doubt"]?.[LL("es", "en") as "es" | "en"] ?? "")}"></canvas>
        <div class="wx-time au-bar" id="au-bar" role="group" aria-label="${esc(LL("Filtrar por estado", "Filter by state"))}">
          ${ORDER.map((k) => `<button class="au-lg" data-st="${k}" aria-pressed="false"><i style="background:${ST[k].c}"></i>${esc(LL(ST[k].es, ST[k].en))} <b class="num">${int(cb.recuentos[KEY[k]] ?? 0)}</b></button>`).join("")}
        </div>
      </section>
    </div>
    <div class="tr-tip" id="au-tip" role="tooltip" hidden></div>
    <dialog class="au-lb" id="au-lb"><button class="au-x" aria-label="${esc(LL("Cerrar", "Close"))}">×</button><img alt=""></dialog>
  </div>`;

  const $ = <T extends HTMLElement = HTMLElement>(id: string) => document.getElementById(id) as T;
  const wx = $("au"), tip = $("au-tip"), cv = $<HTMLCanvasElement>("au-cv"), g = cv.getContext("2d")!;
  const N = cb.meses.length, rows = cb.filas;
  const rowOf = (code: string) => rows.findIndex((f) => f.codigo === code);

  // ── Panel: cifras de la región ──
  const renderPanel = () => {
    const f = ui.reg === "DO" ? null : rows[rowOf(ui.reg)];
    $("au-h1").textContent = f ? f.provincia : LL("República Dominicana", "Dominican Republic");
    ($("au-reg") as HTMLSelectElement).value = ui.reg;
    const nat = cb.nacional;
    const unan = f ? f.estados.filter((x) => x === 3).length : nat.n_unanime_sequia;
    const alarms = f ? f.n_alguna_alarma : nat.n_alguna_alarma;
    $("au-find").textContent = LL(`Solo ${int(unan)} de ${int(alarms)} alarmas de sequía fueron unánimes.`, `Only ${int(unan)} of ${int(alarms)} drought alarms were unanimous.`);
    const tc = f ? f.tasa_condicional : nat.tasa_condicional, ic = f ? f.ic95 : nat.ic95_condicional;
    const cc = f ? f.tasa_contradiccion_clara : nat.tasa_contradiccion_clara;
    $("au-kpi").innerHTML = `
      <div class="au-k au-lead"><p class="au-kl">${esc(LL("La decisión cambia según el producto", "The decision changes with the product"))}</p><p><b class="num">${pct(tc)}</b> <span class="num">${esc(LL("IC 95 %:", "95 % CI:"))} ${num(ic[0] * 100, 0)}–${pct(ic[1])}</span></p><p class="au-ks">${esc(LL("de los meses en que al menos uno declara sequía", "of the months when at least one declares drought"))}</p></div>
      <div class="au-k"><p class="au-kl">${esc(LL("Contradicción clara", "Clear contradiction"))}</p><p><b class="num" style="color:${ST[4].c}">${pct(cc)}</b></p><p class="au-ks">${esc(LL("otro decía normal o húmedo", "another said normal or wet"))}</p></div>
      <div class="au-k"><p class="au-kl">${esc(LL("Los 4 dicen sequía", "All 4 say drought"))}</p><p><b class="num" style="color:${ST[3].c}">${int(unan)}</b> <span class="num">${esc(LL("de", "of"))} ${int(alarms)}</span></p><p class="au-ks">${esc(LL("meses con alguna alarma", "months with any alarm"))}</p></div>`;
  };

  // ── El código de barras ──
  let hov: { r: number; c: number } | null = null;
  const geo = { L: 150, R: 48, T: 0, cw: 1, rh: 18, x0: 0, y0: 0, W: 0, H: 0 };
  const layout = () => {
    const r = cv.parentElement!.getBoundingClientRect(), dpr = Math.min(2, devicePixelRatio || 1);
    const bar = document.getElementById("au-bar")?.offsetHeight ?? 76;
    const top = phone ? 112 : 172, bottom = bar + (phone ? 172 + 26 : 34);
    geo.W = r.width; geo.H = r.height;
    cv.width = Math.round(r.width * dpr); cv.height = Math.round(r.height * dpr);
    cv.style.width = `${r.width}px`; cv.style.height = `${r.height}px`;
    g.setTransform(dpr, 0, 0, dpr, 0, 0);
    geo.L = phone ? 92 : 150; geo.R = phone ? 34 : 52;
    const pad = phone ? 16 : 24;
    geo.cw = (r.width - geo.L - geo.R - pad * 2) / N;
    geo.rh = Math.max(9, Math.min(22, (r.height - top - bottom) / rows.length));
    geo.x0 = pad + geo.L; geo.y0 = top + Math.max(0, (r.height - top - bottom - geo.rh * rows.length) / 2);
  };
  const draw = () => {
    const { cw, rh, x0, y0, W, H } = geo;
    g.fillStyle = "#0c0d0f"; g.fillRect(0, 0, W, H);
    const sel = rowOf(ui.reg);
    rows.forEach((f, r) => {
      const y = y0 + r * rh, dim = sel >= 0 && sel !== r;
      for (let c = 0; c < N; c++) {
        const s = f.estados[c];
        if (s < 0) continue;
        const off = ui.filter !== null && s !== ui.filter;
        g.globalAlpha = (off ? 0.12 : 1) * (dim ? 0.35 : 1);
        g.fillStyle = off && s !== 0 ? ST[0].c : ST[s].c;
        g.fillRect(x0 + c * cw, y + 1, Math.ceil(cw), rh - 2);
      }
      g.globalAlpha = 1;
      g.font = `${sel === r || hov?.r === r ? 600 : 400} ${phone ? 11 : 12}px Inter, system-ui, sans-serif`;
      g.textBaseline = "middle"; g.textAlign = "right";
      g.fillStyle = sel === r || hov?.r === r ? "#ffffff" : dim ? "#6b6f75" : "#b4b4b4";
      const name = phone && f.provincia.length > 13 ? `${f.provincia.slice(0, 12)}…` : f.provincia;
      g.fillText(name, x0 - 8, y + rh / 2);
      g.textAlign = "left";
      g.fillText(pct(f.tasa_condicional), x0 + N * cw + 8, y + rh / 2);
    });
    // franja nacional: por mes, provincias en contradicción (hacia arriba) y unánimes (hacia abajo)
    const hh = phone ? 26 : 34, ym = y0 - (phone ? 40 : 52), nR = rows.length;
    for (let c = 0; c < N; c++) {
      let k4 = 0, k3 = 0;
      rows.forEach((f) => { const s = f.estados[c]; if (s === 4) k4++; else if (s === 3) k3++; });
      if (k4) { g.fillStyle = ST[4].c; const h = (k4 / nR) * hh; g.fillRect(x0 + c * cw, ym - h, Math.ceil(cw), h); }
      if (k3) { g.fillStyle = ST[3].c; const h = (k3 / nR) * hh; g.fillRect(x0 + c * cw, ym + 1, Math.ceil(cw), h); }
    }
    g.fillStyle = "#2a2d31"; g.fillRect(x0, ym, N * cw, 1);
    g.font = `500 11px Inter, system-ui, sans-serif`; g.textAlign = "right"; g.textBaseline = "middle";
    g.fillStyle = ST[4].c; g.fillText(LL("se contradicen", "contradict"), x0 - 8, ym - hh / 2);
    g.fillStyle = ST[3].c; g.fillText(LL("los 4 coinciden", "all 4 agree"), x0 - 8, ym + hh / 2);
    g.textAlign = "left";
    // años
    const yb = y0 + rows.length * rh + 6;
    g.font = `500 11px Inter, system-ui, sans-serif`; g.textBaseline = "top"; g.fillStyle = "#949494"; g.textAlign = "center";
    cb.meses.forEach((m, c) => {
      if (!m.endsWith("-01")) return;
      const yr = Number(m.slice(0, 4));
      g.fillStyle = "#2a2d31"; g.fillRect(x0 + c * cw, yb - 4, 1, 4);
      if (yr % (phone ? 8 : 4) === 1 || yr === 2024) { g.fillStyle = "#949494"; g.fillText(String(yr), x0 + (c + 6) * cw, yb + 2); }
    });
    g.textAlign = "left"; g.textBaseline = "alphabetic"; g.fillStyle = "#949494";
    g.fillText(LL("cambia", "flips"), x0 + N * cw + 8, y0 - 6);
    // la anotación que importa: el año con más meses unánimes
    const [ybest, nbest] = Object.entries(cb.por_anio_unanime).sort((a, b) => b[1] - a[1])[0] ?? ["", 0];
    const cBest = cb.meses.findIndex((m) => m.startsWith(`${ybest}-`));
    if (cBest >= 0 && !phone) {
      const xm = x0 + (cBest + 6) * cw;
      g.fillStyle = ST[3].c; g.fillRect(xm, ym + hh + 2, 1, y0 - ym - hh - 4);
      g.font = `600 12px Inter, system-ui, sans-serif`; g.textAlign = "center";
      g.fillText(LL(`${ybest}: ${nbest} de los ${cb.recuentos.unanimous} meses unánimes`, `${ybest}: ${nbest} of the ${cb.recuentos.unanimous} unanimous months`), xm, ym - hh - 12);
      g.textAlign = "left";
    }
    if (hov) {
      g.strokeStyle = "#ffffff"; g.lineWidth = 1;
      g.strokeRect(x0 - 0.5, y0 + hov.r * rh + 0.5, N * cw + 1, rh - 1);
      g.strokeRect(x0 + hov.c * cw - 0.5, y0 - 0.5, Math.ceil(cw) + 1, rows.length * rh + 1);
    }
  };
  const at = (e: MouseEvent) => {
    const b = cv.getBoundingClientRect(), x = e.clientX - b.left, y = e.clientY - b.top;
    const r = Math.floor((y - geo.y0) / geo.rh), c = Math.floor((x - geo.x0) / geo.cw);
    if (r < 0 || r >= rows.length) return null;
    return { r, c: Math.max(-1, Math.min(N - 1, c)) };
  };
  cv.addEventListener("mousemove", (e) => {
    const h = at(e);
    if (!h || h.c < 0) { if (hov) { hov = null; draw(); } tip.hidden = true; cv.style.cursor = h ? "pointer" : "default"; return; }
    cv.style.cursor = "pointer";
    if (!hov || hov.r !== h.r || hov.c !== h.c) { hov = h; draw(); }
    const f = rows[h.r], m = cb.meses[h.c], s = f.estados[h.c], mo = Number(m.slice(5, 7)) - 1;
    const vals = cb.productos.map((p) => {
      const v = f.spi3[p]?.[h.c];
      return `<span class="tt-p ${v !== null && v !== undefined && v <= cb.umbral_spi3 ? "dry" : ""}"><i></i>${PNAME[p] ?? p} <b class="num">${v === null || v === undefined ? "—" : num(v, 2)}</b></span>`;
    }).join("");
    tip.innerHTML = `<p class="tt-n">${esc(f.provincia)} · ${LL(MES_ES[mo], MES_EN[mo])} ${m.slice(0, 4)}</p><p>${s < 0 ? esc(LL("Sin dato (el SPI-3 necesita 3 meses)", "No data (SPI-3 needs 3 months)")) : `<i class="tt-s" style="background:${ST[s].c}"></i>${esc(LL(ST[s].es, ST[s].en))}`}</p><p class="tt-vals">${vals}</p><p class="tt-f">${esc(LL("SPI-3; punto lleno: declara sequía", "SPI-3; filled dot: declares drought"))}</p>`;
    tip.hidden = false;
    tip.style.left = `${Math.min(innerWidth - tip.offsetWidth - 12, Math.max(12, e.clientX - tip.offsetWidth / 2))}px`;
    tip.style.top = `${Math.max(8, e.clientY - tip.offsetHeight - 14)}px`;
  });
  cv.addEventListener("mouseleave", () => { hov = null; tip.hidden = true; draw(); });
  cv.addEventListener("click", (e) => { const h = at(e); if (h) pickRegion(rows[h.r].codigo === ui.reg ? "DO" : rows[h.r].codigo); });

  // ── Acciones ──
  const pickRegion = (code: string) => { ui.reg = code; renderPanel(); draw(); };
  const renderBar = () => wx.querySelectorAll<HTMLButtonElement>("[data-st]").forEach((b) => {
    const on = ui.filter === Number(b.dataset.st);
    b.classList.toggle("on", on); b.setAttribute("aria-pressed", String(on));
  });
  const renderFold = () => {
    wx.dataset.left = ui.left ? "on" : "off";
    wx.querySelectorAll<HTMLButtonElement>("[data-fold]").forEach((b) => { const t = ui.left ? LL("Ocultar panel", "Hide panel") : LL("Mostrar panel", "Show panel"); b.title = t; b.setAttribute("aria-label", t); b.setAttribute("aria-expanded", String(ui.left)); });
  };
  wx.addEventListener("click", (e) => {
    const el = e.target as Element;
    const st = el.closest<HTMLButtonElement>("[data-st]");
    if (st) { const k = Number(st.dataset.st); ui.filter = ui.filter === k ? null : k; renderBar(); draw(); return; }
    if (el.closest("[data-fold]")) { ui.left = !ui.left; renderFold(); return; }
    const fg = el.closest<HTMLButtonElement>("[data-fig]");
    if (fg) { const lb = $<HTMLDialogElement>("au-lb"), im = lb.querySelector("img")!; im.src = `figuras/${fg.dataset.fig}`; im.alt = fg.querySelector("img")?.alt ?? ""; lb.showModal(); return; }
    if (el.closest(".au-x") || el.id === "au-lb") $<HTMLDialogElement>("au-lb").close();
  });
  $("au-reg").addEventListener("change", (e) => pickRegion((e.target as HTMLSelectElement).value));
  // La animación de la tormenta solo se descarga al abrir su sección
  $("au-sd").addEventListener("toggle", (e) => { const im = (e.target as HTMLElement).querySelector<HTMLImageElement>(".au-gif"); if (im && !im.src && im.dataset.src) im.src = im.dataset.src; });

  if (phone) {
    const sheet = bottomSheet($("au-left"), [$("au-grab"), $("au-peek")], (s) => { wx.dataset.sheet = s; });
    wx.dataset.sheet = sheet.state;
  }
  const ro = new ResizeObserver(() => { layout(); draw(); });
  ro.observe(cv.parentElement!);
  cleanup.push(() => ro.disconnect());
  renderPanel(); renderBar(); renderFold(); layout(); draw();
}
