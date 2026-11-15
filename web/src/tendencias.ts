// P0 · ¿Están cambiando las sequías y la lluvia extrema? Variable × región × periodo → serie anual,
// tendencia por década con IC 95 %, p, q (FDR) y la clase de confianza de dos productos.
// Solo lee results/tendencias/web (copiado a public/data/tendencias por scripts/sincronizar_tendencias.py).
// Nada se calcula aquí salvo la recta de Theil-Sen para dibujarla (intercepto = mediana de y − b·x).
import { load } from "./data";
import { getLang } from "./i18n";
import { fmt } from "./text";
import { terrain3d } from "./terrain3d";

interface VarMeta {
  id: string; label_es: string; label_en: string; unidad: string; unidad_tendencia: string;
  descripcion: string; por_que_importa: string; tipo: "seco" | "humedo"; aumento_significa: string;
  periodos: string[]; grupo: "periodos_secos" | "lluvia" | "sequia";
}
interface Vars {
  anios: [number, number];
  productos: Record<string, { nombre: string; tipo_fuente: string; resolucion_nativa: string; cita: string }>;
  periodos: Record<string, { label_es: string; label_en: string; meses: number[] }>;
  clases: Record<string, { label_es: string; label_en: string; color: string; descripcion: string }>;
  umbral_significancia: { q_fdr: number; regla: string };
  prueba: string; nota_causalidad: string; generado_utc: string;
  variables: VarMeta[];
}
interface Tr {
  pendiente_decada: number; ic95: [number, number]; p: number; q: number | null; sig: boolean | null; sig_p05?: boolean;
  mdt: number; media: number; detectable: boolean; pendiente_pct_decada: number;
}
type TrRow = { clase: string } & Record<string, Tr | string>;
interface Prov {
  regiones: { id: string; nombre: string; es_nacional: boolean }[];
  anios: Record<string, number[]>;
  series: Record<string, Record<string, Record<string, Record<string, (number | null)[]>>>>;
  tendencias: Record<string, Record<string, Record<string, TrRow>>>;
}
interface Rej {
  nx: number; ny: number; lat_bordes: number[]; lon_bordes: number[]; incluida: number[];
  clases_codigo: string[];
  capas: Record<string, Record<string, Record<string, { pendiente_decada: (number | null)[]; q: (number | null)[] } | (number | null)[]>>>;
}

const LL = (es: string, en: string) => (getLang() === "es" ? es : en);
const esc = (s: string) => s.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]!));
const RM = () => matchMedia("(prefers-reduced-motion: reduce)").matches;
const CHEV = '<svg class="pill-chev" viewBox="0 0 12 12" aria-hidden="true"><path d="M3 4.5l3 3 3-3" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>';
const PIN = '<svg class="pill-ico" viewBox="0 0 16 16" aria-hidden="true"><path d="M8 14s4.5-4.2 4.5-7.5a4.5 4.5 0 1 0-9 0C3.5 9.8 8 14 8 14z" fill="none" stroke="currentColor" stroke-width="1.4"/><circle cx="8" cy="6.5" r="1.6" fill="currentColor"/></svg>';
const pillSelect = (id: string, label: string, icon: string, opts: string) =>
  `<label class="pill-select">${icon}<span class="pill-lab">${label}</span><select id="${id}" aria-label="${label}">${opts}</select>${CHEV}</label>`;

// Colores de sistema (Apple, modo oscuro): cálido = hacia lo seco, azul = hacia lo húmedo
const WARM = [255, 159, 10], HOT = [255, 69, 58], COOL = [100, 210, 255], DEEP = [10, 132, 255];
const mix = (a: number[], b: number[], t: number) => a.map((v, k) => Math.round(v + (b[k] - v) * t));

// Escalera de evidencia: lo que sabemos, lo que creemos saber, lo que hay que comprobar
type Tier = "sabemos" | "creemos" | "comprobar" | "nada";
const TIERS: [Tier, string, string][] = [
  ["sabemos", "Lo que sabemos", "What we know"],
  ["creemos", "Lo que creemos saber", "What we think we know"],
  ["comprobar", "Lo que hay que comprobar", "What still needs checking"],
];

const st = { ind: "RACHAS15", per: "anual", reg: "DO", src: "IMERG", layer: "prov" as "prov" | "cells", mode: "3d" as "3d" | "plano" | "oscuro" };
let t3: ReturnType<typeof terrain3d> | null = null;
let hideTip: (() => void) | null = null;

export function destroyTrends() { t3?.destroy(); t3 = null; hideTip?.(); }

export async function viewTrends(view: HTMLElement) {
  const [V, P, R] = await Promise.all([
    load<Vars>("tendencias/variables.json"), load<Prov>("tendencias/provincias.json"), load<Rej>("tendencias/rejilla.json"),
  ]);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const fc = await load<any>("limites/provincias.geojson").catch(() => null);
  const prods = Object.keys(V.productos);
  if (!prods.includes(st.src)) st.src = prods[0];
  const both = prods.includes("IMERG") && prods.includes("CHIRPS");
  const vm = (id = st.ind) => V.variables.find((v) => v.id === id)!;
  const lab = (o: { label_es: string; label_en: string }) => LL(o.label_es, o.label_en);
  const regName = (id: string) => P.regiones.find((r) => r.id === id)?.nombre ?? id;
  const isoToShape: Record<string, string> = {}, shapeToIso: Record<string, string> = {};
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  fc?.features.forEach((f: any) => { isoToShape[f.properties.shapeISO] = f.properties.shapeID; shapeToIso[f.properties.shapeID] = f.properties.shapeISO; });
  const provs = P.regiones.filter((r) => !r.es_nacional).sort((a, b) => a.nombre.localeCompare(b.nombre, "es"));
  const groups: [VarMeta["grupo"], string, string][] = [["periodos_secos", "Periodos secos", "Dry spells"], ["sequia", "Sequía (SPI)", "Drought (SPI)"], ["lluvia", "Lluvia y extremos", "Rain and extremes"]];
  const updated = new Date(V.generado_utc).toLocaleString(getLang() === "es" ? "es-DO" : "en-US", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });

  view.innerHTML = `
    <div class="con-head tr-head">
      <div>
        <p class="crumb">Stellar Horizons<span aria-hidden="true">/</span>${esc(LL("Detective de tendencias", "Trend detective"))}</p>
        <h1 id="tr-h1"></h1>
        <p class="con-sub" id="tr-sub"></p>
        ${both ? "" : `<p class="tr-prelim"><i></i>${esc(LL(`Preliminar · solo IMERG · CHIRPS en camino · corrida ${updated}`, `Preliminary · IMERG only · CHIRPS on its way · run ${updated}`))}</p>`}
      </div>
      <div class="rb-ctrl pills">
        ${pillSelect("tr-var", LL("Variable", "Variable"), "", groups.map(([g, es, en]) => `<optgroup label="${esc(LL(es, en))}">${V.variables.filter((v) => v.grupo === g).map((v) => `<option value="${v.id}" ${v.id === st.ind ? "selected" : ""}>${esc(lab(v))}</option>`).join("")}</optgroup>`).join(""))}
        ${pillSelect("tr-reg", LL("Región", "Region"), PIN, `<option value="DO">${esc(LL("Toda la República Dominicana", "Whole Dominican Republic"))}</option>${provs.map((r) => `<option value="${r.id}">${esc(r.nombre)}</option>`).join("")}`)}
      </div>
    </div>

    <div class="console trend" data-layer="prov">
      <section class="pnl map-pnl" aria-label="${esc(LL("Mapa de tendencias", "Trend map"))}">
        <div id="map"></div>
        <div class="map-tools">
          <div class="seg-pill" role="radiogroup" aria-label="${esc(LL("Periodo del año", "Season"))}" id="tr-per"></div>
          <div class="seg-pill" role="radiogroup" aria-label="${esc(LL("Detalle del mapa", "Map detail"))}">
            <button data-tlayer="prov" role="radio">${esc(LL("Provincias", "Provinces"))}</button>
            <button data-tlayer="cells" role="radio">${esc(LL("Celdas de 11 km", "11 km cells"))}</button>
          </div>
          <div class="seg-pill" role="radiogroup" aria-label="${esc(LL("Fuente", "Source"))}">
            ${["IMERG", "CHIRPS"].map((p) => `<button data-src="${p}" role="radio" ${prods.includes(p) ? "" : `disabled title="${esc(LL("Llega en la próxima corrida", "Arrives in the next run"))}"`}>${p}${prods.includes(p) ? "" : `<small>${esc(LL(" pronto", " soon"))}</small>`}</button>`).join("")}
          </div>
          <div class="seg-pill" role="radiogroup" aria-label="${esc(LL("Estilo del mapa", "Map style"))}">
            ${([["3d", "3D"], ["plano", LL("Plano", "Flat")], ["oscuro", LL("Oscuro", "Dark")]] as const).map(([k, l]) => `<button data-tmode="${k}" role="radio">${l}</button>`).join("")}
          </div>
          <p class="map-legend tr-legend" id="tr-legend"></p>
        </div>
      </section>

      <button class="drawer-tab" id="drawer-tab" aria-expanded="true" aria-controls="side-col" title="${esc(LL("Esconder o mostrar el panel", "Hide or show the panel"))}"><svg viewBox="0 0 12 12" aria-hidden="true"><path d="M4.5 3l3 3-3 3" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/></svg></button>
      <aside class="side-col" id="side-col">
        <section class="pnl tr-card" id="tr-card" aria-live="polite"></section>
        <section class="pnl tr-rank" id="tr-rank"></section>
      </aside>

      <section class="pnl tl-pnl tr-series">
        <div class="pnl-h"><h2 id="tr-sh"></h2><span class="readout num" id="tr-read"></span></div>
        <div class="tr-plot" id="tr-plot"></div>
        <p class="tr-key" id="tr-key"></p>
      </section>
    </div>
    <div class="tr-tip" id="tr-tip" role="tooltip" hidden></div>`;

  const consoleEl = view.querySelector<HTMLElement>(".console")!;
  const tip = document.getElementById("tr-tip")!;
  hideTip = () => { tip.hidden = true; };
  const showTip = (html: string, x: number, y: number) => {
    tip.innerHTML = html; tip.hidden = false;
    const w = tip.offsetWidth;
    tip.style.left = `${Math.min(innerWidth - w - 12, Math.max(12, x - w / 2))}px`;
    tip.style.top = `${y - tip.offsetHeight - 14}px`;
  };
  (document.getElementById("tr-reg") as HTMLSelectElement).value = st.reg;

  // ── Lecturas del contrato ──
  const yearsOf = () => (st.ind.startsWith("SPI") ? P.anios.spi : P.anios[st.per]);
  const seriesOf = (src: string, reg = st.reg) => P.series[st.ind]?.[st.per]?.[src]?.[reg] ?? null;
  const rowOf = (reg = st.reg) => P.tendencias[st.ind]?.[st.per]?.[reg] ?? null;
  const trOf = (src: string, reg = st.reg) => (rowOf(reg)?.[src] as Tr | undefined) ?? null;
  const isSig = (t: Tr, reg: string) => (reg === "DO" ? (t.sig_p05 ?? t.p < 0.05) : t.sig === true);
  const sigRule = (reg: string) => (reg === "DO" ? LL("p < 0,05 (una sola serie)", "p < 0.05 (single series)") : LL("q ≤ 0,10 (FDR entre 32 provincias)", "q ≤ 0.10 (FDR across 32 provinces)"));
  const digits = (v: number) => (Math.abs(v) >= 100 ? 0 : Math.abs(v) >= 10 ? 1 : 2);
  const n = (v: number, d = digits(v)) => fmt(v, d);
  const sgn = (v: number, d = digits(v)) => (v > 0 ? "+" : "") + n(v, d);
  const unitT = () => vm().unidad_tendencia;
  // Dirección pintada: lo que el índice significa (subir un índice seco = más seco)
  const warmIfUp = () => vm().tipo === "seco";

  const tierOf = (reg = st.reg): { tier: Tier; label: string; color: string; why: string } => {
    const row = rowOf(reg);
    const c = row?.clase ?? "";
    const cl = V.clases[c];
    const t = trOf(st.src, reg);
    if (c === "robusta") return { tier: "sabemos", label: lab(cl), color: cl.color, why: cl.descripcion };
    if (c === "consistente") return { tier: "creemos", label: lab(cl), color: cl.color, why: cl.descripcion };
    if (c === "en disputa") return { tier: "comprobar", label: lab(cl), color: cl.color, why: cl.descripcion };
    if (c === "sin señal detectable") return { tier: "nada", label: lab(cl), color: "#8e8e93", why: cl.descripcion };
    // Un solo producto: no hay segunda opinión todavía
    const sig = t ? isSig(t, reg) : false;
    return sig
      ? { tier: "creemos", label: LL("Una sola fuente", "One source only"), color: "#64d2ff", why: LL("IMERG muestra una tendencia significativa, pero falta que CHIRPS la confirme o la dispute.", "IMERG shows a significant trend, but CHIRPS has yet to confirm or dispute it.") }
      : { tier: "nada", label: LL("Sin señal detectable", "No detectable signal"), color: "#8e8e93", why: LL("Con una fuente y 24 años no se detecta una tendencia. No quiere decir que no haya cambio.", "With one source and 24 years no trend is detected. It does not mean there is no change.") };
  };

  // ── Cabecera, periodo y leyenda ──
  const perBtns = document.getElementById("tr-per")!;
  const renderHead = () => {
    const v = vm();
    document.getElementById("tr-h1")!.textContent = lab(v);
    document.getElementById("tr-sub")!.textContent = `${st.reg === "DO" ? LL("República Dominicana", "Dominican Republic") : regName(st.reg)} · ${lab(V.periodos[st.per])} · ${yearsOf()[0]}–${yearsOf().at(-1)} · ${v.descripcion}`;
    const pers = v.periodos;
    if (!pers.includes(st.per)) st.per = "anual";
    perBtns.innerHTML = Object.keys(V.periodos).map((k) => {
      const ok = pers.includes(k);
      const short: Record<string, [string, string]> = { anual: ["Año", "Year"], seca: ["Seca", "Dry"], humeda_temprana: ["Lluvias tempranas", "Early rains"], humeda_tardia: ["Lluvias tardías", "Late rains"] };
      return `<button data-per="${k}" role="radio" aria-checked="${k === st.per}" class="${k === st.per ? "on" : ""}" ${ok ? "" : `disabled title="${esc(LL("El SPI solo se calcula para el año completo", "SPI is computed for the whole year only"))}"`} >${esc(LL(...(short[k] ?? [k, k])))}</button>`;
    }).join("");
    perBtns.querySelectorAll<HTMLButtonElement>("button").forEach((b) => b.addEventListener("click", () => { st.per = b.dataset.per!; renderAll(); }));
    view.querySelectorAll<HTMLButtonElement>("[data-tlayer]").forEach((b) => { const on = b.dataset.tlayer === st.layer; b.classList.toggle("on", on); b.setAttribute("aria-checked", String(on)); });
    view.querySelectorAll<HTMLButtonElement>("[data-src]").forEach((b) => { const on = b.dataset.src === st.src; b.classList.toggle("on", on); b.setAttribute("aria-checked", String(on)); });
    view.querySelectorAll<HTMLButtonElement>("[data-tmode]").forEach((b) => { const on = b.dataset.tmode === st.mode; b.classList.toggle("on", on); b.setAttribute("aria-checked", String(on)); });
  };

  // ── Mapa: provincias o celdas, coloreadas por la pendiente; tenue si no es significativa ──
  const colorFor = (slope: number, max: number, sig: boolean) => {
    const t = Math.min(1, Math.abs(slope) / (max || 1));
    const towardDry = (slope > 0) === warmIfUp();
    const rgb = towardDry ? mix(WARM, HOT, t) : mix(COOL, DEEP, t);
    return { rgb, a: sig ? 0.5 + 0.45 * t : 0.05 + 0.1 * t };
  };
  const renderMap = () => {
    if (!t3) return;
    const v = vm();
    consoleEl.dataset.layer = st.layer;
    const legend = document.getElementById("tr-legend")!;
    const upWord = v.tipo === "seco" ? LL("más seco", "drier") : LL("más lluvia", "more rain");
    const ramp = (dn: string, up: string) => {
      const g = (a: number[], b: number[]) => `linear-gradient(90deg, rgba(${a.join(",")},.3), rgb(${b.join(",")}))`; // taste-skill-ignore: rampa de color de la escala de datos, no decoración
      const [dc, uc] = warmIfUp() ? [[COOL, DEEP], [WARM, HOT]] : [[WARM, HOT], [COOL, DEEP]];
      return `<span class="tr-ramp"><i class="lg" style="background:${g(dc[0], dc[1])}"></i>${esc(dn)}<i class="lg" style="background:${g(uc[0], uc[1])}"></i>${esc(up)}</span>`;
    };
    const dnWord = v.tipo === "seco" ? LL("menos seco", "less dry") : LL("menos lluvia", "less rain");
    if (st.layer === "prov") {
      const vals = provs.map((r) => trOf(st.src, r.id)?.pendiente_decada ?? 0);
      const max = Math.max(...vals.map(Math.abs));
      const colors: Record<string, string> = {}, alpha: Record<string, number> = {};
      let nSig = 0;
      provs.forEach((r) => {
        const t = trOf(st.src, r.id); if (!t || !isoToShape[r.id]) return;
        const sig = isSig(t, r.id); if (sig) nSig++;
        const { rgb } = colorFor(t.pendiente_decada, max, sig);
        colors[isoToShape[r.id]] = `rgb(${rgb.join(",")})`;
        alpha[isoToShape[r.id]] = sig ? 0.55 + 0.35 * Math.min(1, Math.abs(t.pendiente_decada) / (max || 1)) : 0.14;
      });
      t3.setChoro(colors, alpha);
      t3.setLayer("prov");
      legend.innerHTML = `${ramp(dnWord, upWord)}<span>${esc(LL(`Intenso: significativa (${nSig} de 32). Tenue: no se distingue del azar.`, `Strong: significant (${nSig} of 32). Faint: indistinguishable from chance.`))}</span>`;
    } else {
      const lay = R.capas[st.ind]?.[st.per]?.[st.src] as { pendiente_decada: (number | null)[]; q: (number | null)[] } | undefined;
      if (!lay) return;
      const vals = lay.pendiente_decada.filter((x): x is number => x !== null).map(Math.abs).sort((a, b) => a - b);
      const max = vals[Math.floor(vals.length * 0.95)] ?? 1;
      const px = new Uint8ClampedArray(R.nx * R.ny * 4);
      let nSig = 0, nIn = 0;
      for (let i = 0; i < R.ny; i++) for (let j = 0; j < R.nx; j++) {
        const k = i * R.nx + j, s = lay.pendiente_decada[k];
        if (!R.incluida[k] || s === null) continue;
        nIn++;
        const sig = (lay.q[k] ?? 1) <= V.umbral_significancia.q_fdr; if (sig) nSig++;
        const { rgb, a } = colorFor(s, max, sig);
        const o = 4 * ((R.ny - 1 - i) * R.nx + j); // fila 0 del contrato = sur; la imagen empieza al norte
        px[o] = rgb[0]; px[o + 1] = rgb[1]; px[o + 2] = rgb[2]; px[o + 3] = Math.round(255 * a);
      }
      t3.setCells(px, R.nx, R.ny, [R.lon_bordes[0], R.lat_bordes[0], R.lon_bordes[R.nx], R.lat_bordes[R.ny]]);
      t3.setLayer("cells");
      legend.innerHTML = `${ramp(dnWord, upWord)}<span>${esc(LL(`${nSig} de ${nIn} celdas significativas (q ≤ 0,10, FDR).`, `${nSig} of ${nIn} cells significant (q ≤ 0.10, FDR).`))}</span>`;
    }
  };

  // ── Ficha: la respuesta en una frase, la escalera de evidencia y la cápsula de detectabilidad ──
  const countUp = (root: HTMLElement) => root.querySelectorAll<HTMLElement>("[data-count]").forEach((el) => {
    const to = Number(el.dataset.count), d = Number(el.dataset.d ?? 1), plus = el.dataset.plus === "1";
    if (RM()) return;
    const t0 = performance.now(), dur = 900;
    const step = (now: number) => {
      const k = Math.min(1, (now - t0) / dur), e = 1 - Math.pow(1 - k, 3), v = to * e;
      el.textContent = (plus && v > 0 ? "+" : "") + fmt(v, d);
      if (k < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  });
  const capsule = (t: Tr, sig: boolean) => {
    // Eje simétrico alrededor de 0 que alcanza el IC y la tendencia mínima detectable
    const W = 340, H = 92, pad = 14, cy = 40;
    const ext = Math.max(Math.abs(t.ic95[0]), Math.abs(t.ic95[1]), t.mdt, Math.abs(t.pendiente_decada)) * 1.12 || 1;
    const x = (v: number) => pad + ((v + ext) / (2 * ext)) * (W - 2 * pad);
    const towardDry = (t.pendiente_decada > 0) === warmIfUp();
    const col = sig ? (towardDry ? "#ff9f0a" : "#0a84ff") : "#aeaeb2";
    const lo = x(t.ic95[0]), hi = x(t.ic95[1]);
    return `<svg class="tr-cap" viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(LL(`Tendencia ${sgn(t.pendiente_decada)} ${unitT()}; IC 95 % de ${n(t.ic95[0])} a ${n(t.ic95[1])}; tendencia mínima detectable ±${n(t.mdt)}`, `Trend ${sgn(t.pendiente_decada)} ${unitT()}; 95 % CI ${n(t.ic95[0])} to ${n(t.ic95[1])}; minimum detectable trend ±${n(t.mdt)}`))}">
      <rect class="cap-mdt" x="${x(-t.mdt)}" y="${cy - 17}" width="${x(t.mdt) - x(-t.mdt)}" height="34" rx="10"/>
      <line x1="${x(0)}" x2="${x(0)}" y1="${cy - 24}" y2="${cy + 24}" class="cap-zero"/>
      <g class="cap-ci" style="transform-origin:${x(t.pendiente_decada)}px ${cy}px"><rect x="${lo}" y="${cy - 5}" width="${Math.max(2, hi - lo)}" height="10" rx="5" fill="${col}" fill-opacity="${sig ? 0.5 : 0.35}"/></g>
      <circle class="cap-dot" cx="${x(t.pendiente_decada)}" cy="${cy}" r="7" fill="${col}" stroke="#000" stroke-opacity=".35"/>
      <text x="${x(0)}" y="${cy - 28}" text-anchor="middle" class="cap-t">0</text>
      <text x="${x(-t.mdt) + 2}" y="${cy + 32}" class="cap-t">${esc(LL("zona no detectable con 24 años", "undetectable with 24 years"))}</text>
      <text x="${lo}" y="${H - 2}" class="cap-t num" text-anchor="${lo < 40 ? "start" : "middle"}">${n(t.ic95[0])}</text>
      <text x="${hi}" y="${H - 2}" class="cap-t num" text-anchor="${hi > W - 40 ? "end" : "middle"}">${n(t.ic95[1])}</text>
    </svg>`;
  };
  const card = document.getElementById("tr-card")!;
  const renderCard = () => {
    const v = vm(), t = trOf(st.src), where = st.reg === "DO" ? LL("En la República Dominicana", "In the Dominican Republic") : LL(`En ${regName(st.reg)}`, `In ${regName(st.reg)}`);
    if (!t) { card.innerHTML = `<p class="meta">${esc(LL("Sin datos para esta combinación.", "No data for this combination."))}</p>`; return; }
    const sig = isSig(t, st.reg), ti = tierOf();
    const up = t.pendiente_decada > 0, zero = t.pendiente_decada === 0;
    const verb = zero ? LL("no cambia", "does not change") : up ? LL("sube", "rises by") : LL("baja", "falls by");
    const crosses = t.ic95[0] <= 0 && t.ic95[1] >= 0;
    const sentence = sig
      ? LL(`${where}, «${lab(v)}» ${verb} ${n(Math.abs(t.pendiente_decada))} ${v.unidad} por década (${sgn(t.pendiente_pct_decada, 0)} % sobre su media de ${n(t.media)}). Es más de lo que el azar explicaría.`,
        `${where}, «${lab(v)}» ${verb} ${n(Math.abs(t.pendiente_decada))} ${v.unidad} per decade (${sgn(t.pendiente_pct_decada, 0)} % of its mean of ${n(t.media)}). That is more than chance would explain.`)
      : t.detectable
        ? LL(`${where}, la tendencia (${sgn(t.pendiente_decada)} ${v.unidad} por década) es grande pero no significativa: no se distingue del azar.`, `${where}, the trend (${sgn(t.pendiente_decada)} ${v.unidad} per decade) is large but not significant: it is indistinguishable from chance.`)
        : LL(`${where} no se detecta tendencia. Con 24 años solo se vería un cambio mayor de ${n(t.mdt)} ${v.unidad} por década: «sin señal» no es «sin cambio».`, `${where} no trend is detected. With 24 years only a change larger than ${n(t.mdt)} ${v.unidad} per decade would show: "no signal" is not "no change".`);
    const tierIdx = ti.tier === "nada" ? -1 : TIERS.findIndex(([k]) => k === ti.tier);
    const otherSrc = prods.filter((p) => p !== st.src);
    card.innerHTML = `
      <p class="tr-eyebrow">${esc(st.reg === "DO" ? LL("Toda la RD", "Whole DR") : regName(st.reg))} · ${esc(lab(V.periodos[st.per]))}</p>
      <div class="tr-big">
        <b class="num" data-count="${t.pendiente_decada}" data-d="${digits(t.pendiente_decada)}" data-plus="1">${sgn(t.pendiente_decada)}</b>
        <span>${esc(unitT())}</span>
      </div>
      <p class="tr-sentence">${esc(sentence)}</p>
      <div class="tr-ladder" role="img" aria-label="${esc(`${LL("Evidencia", "Evidence")}: ${ti.label}`)}">
        ${TIERS.map(([k, es, en], i) => `<span class="${i === tierIdx ? "on" : ""}" style="--c:${ti.color};--i:${i}"><i></i>${esc(LL(es, en))}</span>`).join("")}
      </div>
      <p class="tr-class"><span class="chip" style="--c:${ti.color}">${esc(ti.label)}</span>${esc(ti.why)}</p>
      ${capsule(t, sig)}
      <p class="tr-capnote">${esc(crosses ? LL("El intervalo del 95 % cruza el cero: con estos datos podría subir o bajar.", "The 95 % interval crosses zero: with these data it could go up or down.") : LL("El intervalo del 95 % no toca el cero: la dirección es clara.", "The 95 % interval does not touch zero: the direction is clear."))}</p>
      <dl class="tr-stats">
        <div title="${esc(LL("Mann-Kendall modificado de Hamed y Rao (1998), corrige la autocorrelación", "Hamed & Rao (1998) modified Mann-Kendall, corrects for autocorrelation"))}"><dt>p</dt><dd class="num">${t.p < 0.001 ? `&lt;&#8239;${n(0.001, 3)}` : n(t.p, 3)}</dd></div>
        <div title="${esc(LL("Valor q de Benjamini-Hochberg entre las 32 provincias", "Benjamini-Hochberg q across the 32 provinces"))}"><dt>q (FDR)</dt><dd class="num">${t.q === null ? "—" : n(t.q, 3)}</dd></div>
        <div title="${esc(LL("Tendencia mínima detectable: 80 % de potencia, α = 0,05", "Minimum detectable trend: 80 % power, α = 0.05"))}"><dt>${esc(LL("Mín. detectable", "Min. detectable"))}</dt><dd class="num">±${n(t.mdt)}</dd></div>
        <div><dt>${esc(LL("Media", "Mean"))}</dt><dd class="num">${n(t.media)}</dd></div>
      </dl>
      <p class="tr-rule">${esc(LL(`Significativa si ${sigRule(st.reg)}. ${V.prueba}.`, `Significant if ${sigRule(st.reg)}. ${V.prueba}.`))}</p>
      <div class="tr-srcs">
        ${["IMERG", "CHIRPS"].map((p) => {
          const meta = V.productos[p];
          const tt = trOf(p);
          return `<p class="tr-src ${meta ? "" : "pending"}"><b>${p}</b><span>${esc(meta ? meta.tipo_fuente : LL("satélite + estaciones · llega en la próxima corrida", "satellite + stations · arrives in the next run"))}</span>${tt ? `<em class="num">${sgn(tt.pendiente_decada)}</em>` : ""}</p>`;
        }).join("")}
      </div>
      <details class="tr-why"><summary>${esc(LL("¿Por qué importa y qué no dice?", "Why it matters and what it does not say"))}</summary>
        <p>${esc(v.por_que_importa)} ${esc(LL(`Si sube: ${v.aumento_significa}.`, `If it rises: ${v.aumento_significa}.`))}</p>
        <p>${esc(V.nota_causalidad)}</p>
        <p>${esc(LL("IMERG es recuperación satelital calibrada con pluviómetros; CHIRPS es satélite + estaciones. No son testigos totalmente independientes: comparten infrarrojo geoestacionario y pluviómetros.", "IMERG is a gauge-calibrated satellite retrieval; CHIRPS is satellite + stations. They are not fully independent witnesses: they share geostationary infrared and rain gauges."))}${otherSrc.length ? "" : ` ${esc(LL("Hasta que llegue CHIRPS, ninguna tendencia puede ser «robusta».", "Until CHIRPS arrives, no trend can be \"robust\"."))}`}</p>
      </details>`;
    card.classList.remove("in"); void card.offsetWidth; card.classList.add("in");
    countUp(card);
  };

  // ── Las 32 provincias en un mismo eje: punto = tendencia, barra = IC 95 % ──
  const rank = document.getElementById("tr-rank")!;
  const renderRank = () => {
    const rows = provs.map((r) => ({ r, t: trOf(st.src, r.id) })).filter((x): x is { r: typeof provs[0]; t: Tr } => !!x.t)
      .sort((a, b) => b.t.pendiente_decada - a.t.pendiente_decada);
    const ext = Math.max(...rows.map((x) => Math.max(Math.abs(x.t.ic95[0]), Math.abs(x.t.ic95[1])))) || 1;
    const W = 340, rh = 22, L = 128, pad = 8, H = rows.length * rh + 26;
    const x = (v: number) => L + ((v + ext) / (2 * ext)) * (W - L - pad);
    const nSig = rows.filter((x) => isSig(x.t, x.r.id)).length;
    rank.innerHTML = `
      <div class="pnl-h"><h2>${esc(LL("Las 32 provincias", "All 32 provinces"))}</h2><span class="meta">${esc(LL(`${nSig} significativas · ${unitT()}`, `${nSig} significant · ${unitT()}`))}</span></div>
      <p class="tr-rank-lead">${esc(LL("Ordenadas de más subida a más bajada. Punto relleno: significativa. Toca una para verla.", "Sorted from largest rise to largest fall. Filled dot: significant. Tap one to open it."))}</p>
      <svg class="tr-forest" viewBox="0 0 ${W} ${H}" role="list">
        <line x1="${x(0)}" x2="${x(0)}" y1="0" y2="${H - 20}" class="fz"/>
        ${rows.map(({ r, t }, i) => {
          const y = i * rh + rh / 2, sig = isSig(t, r.id), towardDry = (t.pendiente_decada > 0) === warmIfUp();
          const col = sig ? (towardDry ? "#ff9f0a" : "#0a84ff") : "#8e8e93";
          return `<g class="fr ${r.id === st.reg ? "on" : ""}" data-reg="${r.id}" role="listitem" tabindex="0" style="--i:${i}" aria-label="${esc(`${r.nombre}: ${sgn(t.pendiente_decada)} ${unitT()}${sig ? `, ${LL("significativa", "significant")}` : ""}`)}">
            <rect x="0" y="${y - rh / 2}" width="${W}" height="${rh}" rx="8" class="fr-bg"/>
            <text x="8" y="${y + 4}" class="fr-n">${esc(r.nombre)}</text>
            <line x1="${x(t.ic95[0])}" x2="${x(t.ic95[1])}" y1="${y}" y2="${y}" stroke="${col}" stroke-width="3" stroke-linecap="round" stroke-opacity=".55" class="fr-ci"/>
            <circle cx="${x(t.pendiente_decada)}" cy="${y}" r="4.5" fill="${sig ? col : "#1c1c1e"}" stroke="${col}" stroke-width="1.6"/>
          </g>`;
        }).join("")}
        <text x="${x(-ext)}" y="${H - 4}" class="fr-ax num">${n(-ext)}</text>
        <text x="${x(0)}" y="${H - 4}" class="fr-ax" text-anchor="middle">0</text>
        <text x="${x(ext)}" y="${H - 4}" class="fr-ax num" text-anchor="end">${sgn(ext)}</text>
      </svg>`;
    rank.querySelectorAll<SVGGElement>(".fr").forEach((g) => {
      const go = () => pick(g.dataset.reg!, true);
      g.addEventListener("click", go);
      g.addEventListener("keydown", (e) => { if ((e as KeyboardEvent).key === "Enter") go(); });
    });
  };

  // ── Serie anual con la recta de Theil-Sen y su abanico del IC 95 % ──
  const plot = document.getElementById("tr-plot")!;
  const renderSeries = () => {
    const v = vm(), yrs = yearsOf(), t = trOf(st.src);
    document.getElementById("tr-sh")!.textContent = LL(`Serie anual · ${lab(v)} · ${st.reg === "DO" ? "toda la RD" : regName(st.reg)}`, `Annual series · ${lab(v)} · ${st.reg === "DO" ? "whole DR" : regName(st.reg)}`);
    const W = Math.max(320, plot.clientWidth || 700), H = 170, ml = 40, mr = 14, mt = 12, mb = 22;
    const lines = prods.map((p) => ({ p, s: seriesOf(p) })).filter((x): x is { p: string; s: (number | null)[] } => !!x.s);
    const all = lines.flatMap((x) => x.s).filter((x): x is number => x !== null);
    if (!all.length) { plot.innerHTML = ""; return; }
    let lo = Math.min(...all), hi = Math.max(...all);
    const span = hi - lo || Math.abs(hi) || 1; lo = Math.max(0, lo - span * 0.15); hi = hi + span * 0.15;
    const X = (yr: number) => ml + ((yr - yrs[0]) / (yrs.at(-1)! - yrs[0])) * (W - ml - mr);
    const Y = (val: number) => mt + (1 - (val - lo) / (hi - lo)) * (H - mt - mb);
    const ticks = [lo, (lo + hi) / 2, hi];
    const sig = t ? isSig(t, st.reg) : false;
    const towardDry = t ? (t.pendiente_decada > 0) === warmIfUp() : true;
    const tc = sig ? (towardDry ? "#ff9f0a" : "#0a84ff") : "#aeaeb2";
    let trend = "";
    const main = lines.find((x) => x.p === st.src) ?? lines[0];
    if (t) {
      const b = t.pendiente_decada / 10, pts = yrs.map((yr, k) => [yr, main.s[k]] as const).filter((q): q is readonly [number, number] => q[1] !== null);
      const res = pts.map(([yr, val]) => val - b * yr).sort((a, c) => a - c);
      const a = res[Math.floor(res.length / 2)];
      const xm = yrs[Math.floor(yrs.length / 2)], ym = a + b * xm;
      const at = (bb: number, yr: number) => ym + bb * (yr - xm);
      const [b0, b1] = [t.ic95[0] / 10, t.ic95[1] / 10];
      const fan = `M${X(yrs[0])},${Y(at(b0, yrs[0]))} L${X(yrs.at(-1)!)},${Y(at(b0, yrs.at(-1)!))} L${X(yrs.at(-1)!)},${Y(at(b1, yrs.at(-1)!))} L${X(yrs[0])},${Y(at(b1, yrs[0]))} Z`;
      trend = `<path d="${fan}" fill="${tc}" fill-opacity=".14" class="tr-fan"/>
        <line x1="${X(yrs[0])}" y1="${Y(at(b, yrs[0]))}" x2="${X(yrs.at(-1)!)}" y2="${Y(at(b, yrs.at(-1)!))}" stroke="${tc}" stroke-width="2.4" stroke-linecap="round" ${sig ? "" : 'stroke-dasharray="5 5"'} class="tr-trend"/>`;
    }
    const path = (s: (number | null)[]) => {
      let d = "", pen = false;
      s.forEach((val, k) => { if (val === null) { pen = false; return; } d += `${pen ? "L" : "M"}${X(yrs[k]).toFixed(1)},${Y(val).toFixed(1)}`; pen = true; });
      return d;
    };
    plot.innerHTML = `<svg viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" class="tr-svg" role="img" aria-label="${esc(LL(`Serie anual de ${lab(v)}`, `Annual series of ${lab(v)}`))}">
      ${ticks.map((tk) => `<line x1="${ml}" x2="${W - mr}" y1="${Y(tk)}" y2="${Y(tk)}" class="gl"/><text x="${ml - 8}" y="${Y(tk) + 4}" text-anchor="end" class="ax num">${n(tk)}</text>`).join("")}
      ${[yrs[0], 2010, 2015, 2020, yrs.at(-1)!].filter((yr, i, arr) => arr.indexOf(yr) === i && yr >= yrs[0]).map((yr) => `<text x="${X(yr)}" y="${H - 4}" text-anchor="middle" class="ax num">${yr}</text>`).join("")}
      ${trend}
      ${lines.map(({ p, s }) => `<path d="${path(s)}" class="tr-line ${p === st.src ? "main" : "alt"}" pathLength="1"/>`).join("")}
      ${main.s.map((val, k) => (val === null ? "" : `<circle cx="${X(yrs[k])}" cy="${Y(val)}" r="3.2" class="tr-pt" style="--i:${k}"/>`)).join("")}
      <line class="tr-cur" id="tr-cur" x1="0" x2="0" y1="${mt}" y2="${H - mb}" visibility="hidden"/>
      <rect x="${ml}" y="0" width="${W - ml - mr}" height="${H}" fill="transparent" id="tr-hit"/>
    </svg>`;
    document.getElementById("tr-key")!.innerHTML = `<span><i class="ln"></i>${esc(st.src)}</span>${lines.length > 1 ? `<span><i class="ln alt"></i>${esc(lines.filter((x) => x.p !== st.src).map((x) => x.p).join(", "))}</span>` : ""}<span><i class="ln tr" style="background:${tc}"></i>${esc(sig ? LL("tendencia de Theil-Sen (significativa)", "Theil-Sen trend (significant)") : LL("tendencia de Theil-Sen (no significativa, línea discontinua)", "Theil-Sen trend (not significant, dashed)"))}</span><span><i class="sq" style="background:${tc};opacity:.3"></i>${esc(LL("IC 95 % de la pendiente", "95 % CI of the slope"))}</span>`;
    const hit = document.getElementById("tr-hit")!, cur = document.getElementById("tr-cur")!;
    const read = document.getElementById("tr-read")!;
    read.textContent = "";
    hit.addEventListener("mousemove", (e) => {
      const r = (hit as unknown as SVGGraphicsElement).ownerSVGElement!.getBoundingClientRect();
      const sx = ((e.clientX - r.left) / r.width) * W;
      const k = Math.max(0, Math.min(yrs.length - 1, Math.round(((sx - ml) / (W - ml - mr)) * (yrs.length - 1))));
      cur.setAttribute("x1", String(X(yrs[k]))); cur.setAttribute("x2", String(X(yrs[k]))); cur.setAttribute("visibility", "visible");
      read.textContent = `${yrs[k]} · ${lines.map(({ p, s }) => `${p} ${s[k] === null ? "—" : n(s[k]!)} ${v.unidad}`).join(" · ")}`;
    });
    hit.addEventListener("mouseleave", () => { cur.setAttribute("visibility", "hidden"); read.textContent = ""; });
  };

  const renderAll = () => { renderHead(); renderCard(); renderRank(); renderSeries(); renderMap(); };

  const bboxOf = (iso: string): [[number, number], [number, number]] | undefined => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const f = fc?.features.find((x: any) => x.properties.shapeISO === iso);
    if (!f) return undefined;
    const polys = f.geometry.type === "Polygon" ? [f.geometry.coordinates] : f.geometry.coordinates;
    let x0 = 180, y0 = 90, x1 = -180, y1 = -90;
    for (const pl of polys) for (const [x, y] of pl[0]) { x0 = Math.min(x0, x); y0 = Math.min(y0, y); x1 = Math.max(x1, x); y1 = Math.max(y1, y); }
    return [[x0, y0], [x1, y1]];
  };
  const pick = (reg: string, fly: boolean) => {
    st.reg = reg;
    (document.getElementById("tr-reg") as HTMLSelectElement).value = reg;
    if (t3) {
      if (reg === "DO") { t3.selectProvince(null); if (fly) t3.country(1800); }
      else t3.selectProvince(isoToShape[reg] ?? null, fly ? bboxOf(reg) : undefined);
    }
    renderHead(); renderCard(); renderRank(); renderSeries();
  };

  // ── Controles ──
  document.getElementById("tr-var")!.addEventListener("change", (e) => { st.ind = (e.target as HTMLSelectElement).value; renderAll(); });
  document.getElementById("tr-reg")!.addEventListener("change", (e) => pick((e.target as HTMLSelectElement).value, true));
  view.querySelectorAll<HTMLButtonElement>("[data-tlayer]").forEach((b) => b.addEventListener("click", () => { st.layer = b.dataset.tlayer as typeof st.layer; renderHead(); renderMap(); }));
  view.querySelectorAll<HTMLButtonElement>("[data-src]").forEach((b) => b.addEventListener("click", () => { if (b.disabled) return; st.src = b.dataset.src!; renderAll(); }));
  view.querySelectorAll<HTMLButtonElement>("[data-tmode]").forEach((b) => b.addEventListener("click", () => { st.mode = b.dataset.tmode as typeof st.mode; renderHead(); t3?.setMode(st.mode); }));
  document.getElementById("drawer-tab")!.addEventListener("click", (e) => {
    const off = consoleEl.classList.toggle("drawer-off");
    (e.currentTarget as HTMLElement).setAttribute("aria-expanded", String(!off));
    window.setTimeout(renderSeries, 720);
  });

  // ── El mapa ──
  t3?.destroy();
  t3 = terrain3d(document.getElementById("map")!, {
    zones: [], sites: [], onZone: () => {}, onSite: () => {}, cellLabel: () => "", siteAction: "",
    provinces: fc ?? undefined,
    onProvince: (shape) => { const iso = shapeToIso[shape]; if (iso) pick(iso, true); },
  });
  const mine = t3;
  renderHead(); renderCard(); renderRank(); renderSeries();
  await mine.ready;
  if (t3 !== mine) return;
  if (st.mode !== "3d") mine.setMode(st.mode);
  renderMap();
  if (st.reg !== "DO") mine.selectProvince(isoToShape[st.reg] ?? null);
  // Valor de la celda bajo el cursor (capa de celdas)
  mine.map.on("mousemove", (e) => {
    if (st.layer !== "cells") { tip.hidden = true; return; }
    const j = R.lon_bordes.findIndex((b, k) => k < R.nx && e.lngLat.lng >= b && e.lngLat.lng < R.lon_bordes[k + 1]);
    const i = R.lat_bordes.findIndex((b, k) => k < R.ny && e.lngLat.lat >= b && e.lngLat.lat < R.lat_bordes[k + 1]);
    const lay = R.capas[st.ind]?.[st.per]?.[st.src] as { pendiente_decada: (number | null)[]; q: (number | null)[] } | undefined;
    const k = i * R.nx + j;
    if (i < 0 || j < 0 || !lay || !R.incluida[k] || lay.pendiente_decada[k] === null) { tip.hidden = true; return; }
    const q = lay.q[k];
    const rect = mine.map.getCanvas().getBoundingClientRect();
    showTip(`<b class="num">${sgn(lay.pendiente_decada[k]!)}</b> ${esc(unitT())}<br><span>q = ${q === null ? "—" : n(q, 2)} · ${esc((q ?? 1) <= V.umbral_significancia.q_fdr ? LL("significativa", "significant") : LL("no significativa", "not significant"))}</span>`, rect.left + e.point.x, rect.top + e.point.y);
  });
  mine.map.getCanvas().addEventListener("mouseleave", () => { tip.hidden = true; });
}
