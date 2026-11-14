// Gráficas de la herramienta. Reglas (taste-skill, app screen): un solo tono de datos (ámbar),
// neutrales para lo demás, 3-5 líneas de cuadrícula tenues, sin línea de eje Y, líneas rectas,
// leyenda solo cuando hay más de una serie y con la misma marca que explica.
import * as Plot from "@observablehq/plot";
import type { Audit, Phantom, PhantomEventRow, Puntos, SensRow, Series, Trend, Window, ZSeries } from "./data";
import { fmt, fmtSigned } from "./text";
import { T } from "./i18n";

export const C = {
  ground: "#0c0d0f",
  surface: "#15171a",
  raised: "#23262a",
  control: "#44484d",
  ink: "#ffffff",
  second: "#e6e6e6",
  muted: "#b4b4b4",
  faint: "#949494",
  grid: "#2a2d31",
  data: "#f2b33d",
};

const base = {
  style: { background: "transparent", color: C.faint, fontFamily: "Poppins, system-ui, sans-serif", fontSize: "12px" },
  marginLeft: 48,
  marginRight: 12,
  marginTop: 18,
  marginBottom: 30,
};
const gridY = { grid: true, ticks: 5 } as const;

function lineFor(t: Trend, x0: number, x1: number) {
  const s = t.pendiente_decada / 10;
  return [{ x: x0, y: t.intercepto + s * x0 }, { x: x1, y: t.intercepto + s * x1 }];
}

function fan(t: Trend, x0: number, x1: number) {
  // Rango de pendientes compatibles (IC 95 %), girando sobre el centro de la ventana
  const s = t.pendiente_decada / 10;
  const [lo, hi] = t.ic95_decada.map((v) => v / 10);
  const xc = (x0 + x1) / 2;
  const yc = t.intercepto + s * xc;
  return [x0, x1].map((x) => {
    const a = yc + lo * (x - xc);
    const b = yc + hi * (x - xc);
    return { x, y1: Math.min(a, b), y2: Math.max(a, b) };
  });
}

/** La evidencia: anomalías anuales, recta Theil-Sen de la serie completa y de la ventana elegida. */
export function evidenceChart(s: Series, unit: string, win: Window | null, width: number): SVGSVGElement | HTMLElement {
  const pts = s.anual.anios.map((y, i) => ({ x: y, y: s.anual.anomalia[i] }));
  const full = s.completa;
  const y0 = s.anual.anios[0];
  const y1 = s.anual.anios[s.anual.anios.length - 1];
  const w = win && !(win.inicio === y0 && win.fin === y1) ? win : null;
  const inWin = (x: number) => !w || (x >= w.inicio && x <= w.fin);
  const active = w ?? full;
  const a0 = w ? w.inicio : y0;
  const a1 = w ? w.fin : y1;
  return Plot.plot({
    ...base,
    width,
    height: Math.max(240, Math.min(320, width * 0.36)),
    x: { label: null, tickFormat: (d: number) => String(d), ticks: 7 },
    y: { label: T().axisAnom(unit), labelAnchor: "top", nice: true, ...gridY },
    marks: [
      Plot.areaY(fan(active, a0, a1), { x: "x", y1: "y1", y2: "y2", fill: C.data, fillOpacity: 0.14 }),
      Plot.ruleY([0], { stroke: C.control, strokeWidth: 1.5 }),
      w ? Plot.line(lineFor(full, y0, y1), { x: "x", y: "y", stroke: C.muted, strokeDasharray: "5,4", strokeWidth: 1.5 }) : null,
      Plot.line(lineFor(active, a0, a1), { x: "x", y: "y", stroke: C.data, strokeWidth: 2.5 }),
      Plot.dot(pts, {
        x: "x", y: "y", r: 4,
        fill: (d: { x: number }) => (inWin(d.x) ? C.second : C.ground),
        stroke: (d: { x: number }) => (inWin(d.x) ? C.second : C.faint),
        strokeWidth: 1.5,
        tip: true,
        title: (d: { x: number; y: number }) => T().tipYear(d.x, fmt(d.y, 2), unit),
      }),
    ],
  });
}

/** La lección de la estación: valores mensuales crudos frente a su promedio de cada mes. */
export function rawChart(s: Series, unit: string, width: number): SVGSVGElement | HTMLElement {
  const rows = s.meses.map((m, i) => ({
    date: new Date(`${m}-01T00:00:00`),
    v: s.valores[i],
    clim: s.climatologia[Number(m.slice(5, 7)) - 1],
  }));
  return Plot.plot({
    ...base,
    width,
    height: Math.max(220, Math.min(300, width * 0.32)),
    x: { label: null, type: "utc" },
    y: { label: T().axisRaw(unit), labelAnchor: "top", nice: true, ...gridY },
    marks: [
      Plot.line(rows, { x: "date", y: "clim", stroke: C.muted, strokeWidth: 1.2, strokeDasharray: "3,3" }),
      Plot.line(rows, { x: "date", y: "v", stroke: C.data, strokeWidth: 1.2 }),
    ],
  });
}

const CELL = { sube: C.data, baja: C.data, indicio: "rgba(242,179,61,0.35)", sin_evidencia: C.raised, insuficiente: C.surface };

/** El mapa de ventanas: cada celda es un intervalo de años; el color es lo que concluirías. */
/** Con cuántos años se ve: por cada largo de intervalo, qué parte de los intervalos detecta la tendencia de la serie completa. */
export function windowLength(s: Series, width: number): SVGSVGElement | HTMLElement {
  const t = T();
  const full = s.completa.veredicto;
  const dir = full === "sube" || full === "baja" ? full : null;
  const byLen = new Map<number, { n: number; hit: number; opp: number }>();
  for (const w of s.ventanas) {
    const L = w.fin - w.inicio + 1;
    const r = byLen.get(L) ?? { n: 0, hit: 0, opp: 0 };
    r.n += 1;
    const sig = w.veredicto === "sube" || w.veredicto === "baja";
    if (sig && (dir === null || w.veredicto === dir)) r.hit += 1;
    if (sig && dir !== null && w.veredicto !== dir) r.opp += 1;
    byLen.set(L, r);
  }
  const rows = [...byLen.entries()].sort((a, b) => a[0] - b[0])
    .map(([L, r]) => ({ L, pct: (100 * r.hit) / r.n, opp: (100 * r.opp) / r.n, n: r.n, hit: r.hit }));
  return Plot.plot({
    ...base,
    width,
    height: 250,
    marginLeft: 40,
    marginBottom: 36,
    x: { label: t.wlAxisX, labelAnchor: "center", labelOffset: 32, tickFormat: (d: number) => (d % 2 === 0 ? String(d) : ""), padding: 0.15 },
    y: { domain: [0, 100], label: t.wlAxisY, labelAnchor: "top", ticks: [0, 50, 100], grid: true },
    marks: [
      Plot.barY(rows, { x: "L", y: "pct", fill: C.data, rx: 3,
        title: (r: { L: number; hit: number; n: number }) => t.wlTip(r.L, r.hit, r.n) }),
      Plot.barY(rows.filter((r) => r.opp > 0), { x: "L", y: "opp", fill: C.second }),
      Plot.ruleY([0], { stroke: C.control }),
    ],
  });
}

export function windowMatrix(s: Series, selected: Window | null, onPick: (w: Window) => void): SVGSVGElement {
  const years = s.anual.anios;
  const y0 = years[0];
  const minLen = Math.min(...s.ventanas.map((w) => w.fin - w.inicio + 1));
  const firstEnd = y0 + minLen - 1;
  const n = years.length - minLen + 1;
  const cell = 28;
  const pad = { l: 44, t: 6, r: 6, b: 38 };
  const W = pad.l + n * cell + pad.r;
  const H = pad.t + n * cell + pad.b;
  const ns = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(ns, "svg");
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
  svg.setAttribute("class", "matrix");
  svg.setAttribute("role", "group");
  svg.setAttribute("aria-label", T().matrixAria);
  for (const w of s.ventanas) {
    const col = w.fin - firstEnd;
    const row = w.inicio - y0;
    const g = document.createElementNS(ns, "g");
    g.setAttribute("class", "mcell");
    g.setAttribute("tabindex", "0");
    g.setAttribute("role", "button");
    g.setAttribute("aria-label", `${w.inicio}–${w.fin}: ${w.veredicto.replace("_", " ")}`);
    const r = document.createElementNS(ns, "rect");
    r.setAttribute("x", String(pad.l + col * cell + 1));
    r.setAttribute("y", String(pad.t + row * cell + 1));
    r.setAttribute("width", String(cell - 2));
    r.setAttribute("height", String(cell - 2));
    r.setAttribute("rx", "5");
    r.setAttribute("fill", CELL[w.veredicto]);
    if (selected && selected.inicio === w.inicio && selected.fin === w.fin) {
      r.setAttribute("stroke", C.ink);
      r.setAttribute("stroke-width", "2.5");
    }
    g.appendChild(r);
    if (w.veredicto === "sube" || w.veredicto === "baja") {
      const t = document.createElementNS(ns, "text");
      t.setAttribute("x", String(pad.l + col * cell + cell / 2));
      t.setAttribute("y", String(pad.t + row * cell + cell / 2 + 4));
      t.setAttribute("text-anchor", "middle");
      t.setAttribute("class", "glyph");
      t.textContent = w.veredicto === "sube" ? "▲" : "▼";
      g.appendChild(t);
    }
    const title = document.createElementNS(ns, "title");
    title.textContent = `${w.inicio}–${w.fin}`;
    g.appendChild(title);
    g.addEventListener("click", () => onPick(w));
    g.addEventListener("keydown", (e) => {
      if ((e as KeyboardEvent).key === "Enter" || (e as KeyboardEvent).key === " ") { e.preventDefault(); onPick(w); }
    });
    svg.appendChild(g);
  }
  const label = (x: number, y: number, txt: string, anchor = "middle") => {
    const t = document.createElementNS(ns, "text");
    t.setAttribute("x", String(x)); t.setAttribute("y", String(y));
    t.setAttribute("text-anchor", anchor); t.setAttribute("class", "axis");
    t.textContent = txt; svg.appendChild(t);
  };
  for (let i = 0; i < n; i += 2) {
    label(pad.l + i * cell + cell / 2, pad.t + n * cell + 16, String(firstEnd + i));
    label(pad.l - 6, pad.t + i * cell + cell / 2 + 4, String(y0 + i), "end");
  }
  label(pad.l + (n * cell) / 2, H - 4, T().matrixAxis);
  return svg;
}

/** SPI-3 real con las sequías usadas (franjas). */
export function spiChart(d: Phantom["sequias"][number], width: number): SVGSVGElement | HTMLElement {
  const rows = d.spi3.meses
    .map((m, i) => ({ date: new Date(`${m}-01T00:00:00`), v: d.spi3.valores[i] }))
    .filter((r) => r.v !== null) as { date: Date; v: number }[];
  const ev = d.eventos.map((e) => ({ a: new Date(`${e.inicio.slice(0, 7)}-01T00:00:00`), b: new Date(`${e.fin.slice(0, 7)}-28T00:00:00`) }));
  return Plot.plot({
    ...base,
    width,
    height: 150,
    x: { type: "utc", label: null },
    y: { label: "SPI-3", labelAnchor: "top", domain: [-3, 3], ticks: [-2, 0, 2], grid: true },
    marks: [
      Plot.rectX(ev, { x1: "a", x2: "b", y1: -3, y2: 3, fill: C.raised }),
      Plot.ruleY([-1], { stroke: C.faint, strokeDasharray: "4,3" }),
      Plot.rectY(rows, { x: "date", interval: "month", y: "v", fill: (r: { v: number }) => (r.v < 0 ? C.data : C.control) }),
      Plot.ruleY([0], { stroke: C.control }),
    ],
  });
}

/** Mediana móvil de 3 observaciones válidas: la misma suavización que usa el cálculo de recuperación. */
function smooth(zs: ZSeries): { date: Date; z: number }[] {
  const out: { date: Date; z: number }[] = [];
  for (let i = 0; i < zs.z.length; i++) {
    const win = zs.z.slice(Math.max(0, i - 1), i + 2).slice().sort((a, b) => a - b);
    out.push({ date: new Date(`${zs.fechas[i]}T00:00:00`), z: win[Math.floor((win.length - 1) / 2)] });
  }
  return out;
}

const DAY = 86400000;

/** La gráfica protagonista: verdor contra función tras una sequía, con umbral, fechas y la brecha. */
export function dualTimeline(o: {
  green: ZSeries; func: ZSeries; start: string; end: string; stop: string;
  greenRec: string | null; funcRec: string | null; threshold: number; width: number;
}): SVGSVGElement | HTMLElement {
  const t = T();
  const start = new Date(`${o.start.slice(0, 10)}T00:00:00`);
  const end = new Date(`${o.end.slice(0, 10)}T00:00:00`);
  const stop = new Date(`${o.stop.slice(0, 10)}T00:00:00`);
  const lo = new Date(start.getTime() - 200 * DAY);
  const hi = new Date(Math.max(stop.getTime(), (o.funcRec ? new Date(o.funcRec).getTime() : 0)) + 60 * DAY);
  const within = (r: { date: Date }) => r.date >= lo && r.date <= hi;
  const g = smooth(o.green).filter(within);
  const f = smooth(o.func).filter(within);
  const gr = o.greenRec ? new Date(`${o.greenRec.slice(0, 10)}T00:00:00`) : null;
  const fr = o.funcRec ? new Date(`${o.funcRec.slice(0, 10)}T00:00:00`) : null;
  const top = 3;
  const marks: Plot.Markish[] = [
    Plot.rectX([{ a: start, b: end }], { x1: "a", x2: "b", y1: -6, y2: top, fill: C.raised }),
    Plot.text([{ x: start }], { x: "x", y: -5.6, text: () => t.droughtLabel, textAnchor: "start", dx: 6, fill: C.faint, fontSize: 11 }),
    Plot.ruleY([0], { stroke: C.control }),
    Plot.ruleY([o.threshold], { stroke: C.faint, strokeDasharray: "4,3" }),
    Plot.text([{ x: hi }], { x: "x", y: o.threshold, text: () => t.recoveredLine, textAnchor: "end", dy: -7, fill: C.faint, fontSize: 11 }),
    Plot.line(g, { x: "date", y: "z", stroke: C.second, strokeWidth: 2 }),
    Plot.line(f, { x: "date", y: "z", stroke: C.data, strokeWidth: 2 }),
  ];
  if (gr) marks.push(Plot.ruleX([gr], { stroke: C.second, strokeWidth: 1 }));
  if (fr) marks.push(Plot.ruleX([fr], { stroke: C.data, strokeWidth: 1 }));
  if (gr && fr) {
    const dt = Math.round((fr.getTime() - gr.getTime()) / DAY);
    const mid = new Date((gr.getTime() + fr.getTime()) / 2);
    marks.push(Plot.link([{ x1: gr, x2: fr }], { x1: "x1", x2: "x2", y1: 2.2, y2: 2.2, stroke: C.data, strokeWidth: 2 }));
    marks.push(Plot.text([{ x: mid }], { x: "x", y: 2.2, dy: -10, text: () => `Δt = ${dt > 0 ? "+" : ""}${dt} ${t.days}`, fill: C.ink, fontSize: 12, fontWeight: 600 }));
  } else if (gr && !fr) {
    marks.push(Plot.text([{ x: gr }], { x: "x", y: 2.2, dx: 6, textAnchor: "start", text: () => t.funcNoRecovery, fill: C.muted, fontSize: 12 }));
  }
  return Plot.plot({
    ...base,
    width: o.width,
    height: 300,
    clip: true,
    x: { type: "utc", domain: [lo, hi], label: null, ticks: 6 },
    y: { domain: [-6, top], label: t.axisZ, labelAnchor: "top", ticks: [-4, -2, 0, 2], grid: true },
    marks,
  });
}

/** Mapa de calor espacio-tiempo: puntos × meses, color = cuánto peor (ámbar) o mejor (gris claro) que lo normal. */
export function heatmap(p: Puntos, variable: string, worseIsHigh: boolean, order: string[], names: Record<string, string>,
  droughts: { region: string; a: string; b: string }[], regionOf: Record<string, string | null>, width: number): SVGSVGElement {
  const ns = "http://www.w3.org/2000/svg";
  const months = p.calor.meses;
  const series = p.calor.series[variable] ?? {};
  const rows = order.filter((id) => series[id]);
  const narrow = width < 560;
  const left = narrow ? 0 : 150;
  const label = narrow ? 18 : 0; // espacio para el nombre encima de la fila
  const rowH = narrow ? 30 : 26;
  const gap = 8 + label;
  const top = 8 + label;
  const bottom = 26;
  const cw = (width - left - 8) / months.length;
  const H = top + rows.length * (rowH + gap) + bottom - label;
  const svg = document.createElementNS(ns, "svg");
  svg.setAttribute("viewBox", `0 0 ${width} ${H}`);
  svg.setAttribute("role", "img");
  svg.setAttribute("aria-label", T().heatAria);
  const idx = new Map(months.map((m, i) => [m, i]));
  rows.forEach((id, r) => {
    const y = top + r * (rowH + gap);
    const lab = document.createElementNS(ns, "text");
    lab.setAttribute("x", "0"); lab.setAttribute("y", String(narrow ? y - 9 : y + rowH / 2 + 4));
    lab.setAttribute("fill", C.muted); lab.setAttribute("font-size", "12");
    lab.textContent = names[id] ?? id;
    svg.appendChild(lab);
    // Sequías de su zona como una franja de 2px sobre la fila
    for (const d of droughts.filter((x) => x.region === regionOf[id])) {
      const a = idx.get(d.a.slice(0, 7)); const b = idx.get(d.b.slice(0, 7));
      if (a === undefined || b === undefined) continue;
      const band = document.createElementNS(ns, "rect");
      band.setAttribute("x", String(left + a * cw)); band.setAttribute("y", String(y - 3));
      band.setAttribute("width", String(Math.max(2, (b - a + 1) * cw))); band.setAttribute("height", "2");
      band.setAttribute("fill", C.ink);
      svg.appendChild(band);
    }
    const vals = series[id];
    vals.forEach((v, i) => {
      const cell = document.createElementNS(ns, "rect");
      cell.setAttribute("x", String(left + i * cw)); cell.setAttribute("y", String(y));
      cell.setAttribute("width", String(cw + 0.3)); cell.setAttribute("height", String(rowH));
      if (v === null) { cell.setAttribute("fill", C.surface); }
      else {
        const worse = worseIsHigh ? v : -v;
        const a = Math.min(1, Math.abs(worse) / 2.5);
        cell.setAttribute("fill", worse > 0 ? C.data : C.second);
        cell.setAttribute("fill-opacity", String(worse > 0 ? 0.08 + 0.92 * a : 0.05 + 0.55 * a));
      }
      const tt = document.createElementNS(ns, "title");
      tt.textContent = `${names[id] ?? id} · ${months[i]}: ${v === null ? "—" : `z = ${fmt(v, 1)}`}`;
      cell.appendChild(tt);
      svg.appendChild(cell);
    });
  });
  const yAxis = top + rows.length * (rowH + gap) - gap + 22;
  const every = narrow ? 8 : 4;
  months.forEach((m, i) => {
    if (m.endsWith("-01") && (Number(m.slice(0, 4)) - 2001) % every === 0) {
      const t = document.createElementNS(ns, "text");
      t.setAttribute("x", String(left + i * cw)); t.setAttribute("y", String(yAxis));
      t.setAttribute("fill", C.faint); t.setAttribute("font-size", "11");
      t.textContent = m.slice(0, 4);
      svg.appendChild(t);
    }
  });
  return svg;
}

/** Constelación de impactos: cada sequía × punto con ambas recuperaciones. */
export function constellation(rows: PhantomEventRow[], names: Record<string, string>, width: number): SVGSVGElement | HTMLElement {
  const t = T();
  const ok = rows.filter((r) => r.estado === "ambos_recuperados" && r.dt_dias !== null && r.verde_dias_desde_fin !== null);
  const sev = (r: PhantomEventRow) => Math.abs(r.evento_severidad_spi3 ?? 0);
  const xs = ok.map((r) => r.verde_dias_desde_fin as number);
  const pad = 20;
  const x0 = Math.min(0, ...xs) - pad;
  const x1 = Math.max(0, ...xs) + pad;
  return Plot.plot({
    ...base,
    width,
    height: 300,
    marginLeft: 52,
    x: { label: t.axisGreenDays, ticks: 5, grid: true, domain: [x0, x1] },
    y: { label: t.axisDtShort, labelAnchor: "top", ticks: 5, grid: true, nice: true },
    r: { range: [3, 11] },
    symbol: { domain: ["gpp_modelo", "lst_menos_aire"], range: ["circle", "triangle"] },
    marks: [
      Plot.rect([{ x1: x0, x2: x1, y1: -32, y2: 32 }], { x1: "x1", x2: "x2", y1: "y1", y2: "y2", fill: C.raised }),
      Plot.ruleY([0], { stroke: C.control }),
      Plot.dot(ok, {
        x: "verde_dias_desde_fin", y: "dt_dias", r: sev, symbol: "funcion",
        stroke: (r: PhantomEventRow) => (r.rob_etiqueta === "ROBUSTO" ? C.data : C.muted),
        fill: (r: PhantomEventRow) => (r.rob_etiqueta === "ROBUSTO" ? C.data : "none"),
        fillOpacity: 0.85, strokeWidth: 1.5,
        tip: true,
        title: (r: PhantomEventRow) => `${names[r.id] ?? r.id} · ${r.evento_inicio.slice(0, 7)}\n${r.funcion === "gpp_modelo" ? t.sigGpp : t.sigLst}: Δt = ${fmt(r.dt_dias as number, 0)} ${t.days}\n${r.rob_etiqueta}`,
      }),
    ],
  });
}

/** Distribución de los días hasta recuperarse, por señal. */
export function recoveryDist(rows: PhantomEventRow[], width: number): SVGSVGElement | HTMLElement {
  const t = T();
  const pts: { s: string; d: number }[] = [];
  const seen = new Set<string>();
  for (const r of rows) {
    const key = `${r.id}|${r.evento_inicio}`;
    if (r.verde_dias_desde_fin !== null && r.verde_dias_desde_fin !== undefined && !seen.has(key)) {
      seen.add(key); pts.push({ s: t.sigGreen, d: r.verde_dias_desde_fin });
    }
    if (r.funcion_dias_desde_fin !== null && r.funcion_dias_desde_fin !== undefined) {
      pts.push({ s: r.funcion === "gpp_modelo" ? t.sigGpp : t.sigLst, d: r.funcion_dias_desde_fin });
    }
  }
  const order = [t.sigGreen, t.sigGpp, t.sigLst];
  // Desplazamiento vertical determinista dentro de cada fila para que los puntos no se tapen
  const placed = pts.map((p, i) => ({ ...p, y: order.indexOf(p.s) + (((i * 37) % 11) / 11 - 0.5) * 0.5 }));
  const med = order.map((s, k) => {
    const v = pts.filter((p) => p.s === s).map((p) => p.d).sort((a, b) => a - b);
    return { s, k, d: v.length ? v[Math.floor(v.length / 2)] : NaN, n: v.length };
  }).filter((m) => !Number.isNaN(m.d));
  return Plot.plot({
    ...base,
    width,
    height: 300,
    marginLeft: 110,
    x: { label: t.axisRecDays, ticks: 5, grid: true, nice: true },
    y: { domain: [-0.6, order.length - 0.4], ticks: [0, 1, 2], tickFormat: (k: number) => order[k] ?? "", label: null, reverse: true },
    marks: [
      Plot.ruleX([0], { stroke: C.control }),
      Plot.dot(placed, { x: "d", y: "y", r: 3.5, fill: C.second, fillOpacity: 0.55 }),
      Plot.ruleX(med, { x: "d", y1: (m: { k: number }) => m.k - 0.38, y2: (m: { k: number }) => m.k + 0.38, stroke: C.data, strokeWidth: 3 }),
      Plot.text(med, { x: "d", y: (m: { k: number }) => m.k - 0.38, text: (m: { d: number; n: number }) => `${t.median} ${fmt(m.d, 0)} (n = ${m.n})`, dy: -8, fill: C.data, fontSize: 11 }),
    ],
  });
}

/** Challenge the Evidence: Δt de cada combinación precalculada. */
export function sensitivityStrip(rows: SensRow[], chosen: SensRow | null, width: number): SVGSVGElement | HTMLElement {
  const ok = rows.filter((r) => r.estado === "ambos_recuperados" && r.dt_dias !== null);
  return Plot.plot({
    ...base,
    width,
    height: 120,
    marginLeft: 16,
    x: { label: T().axisDt, grid: true, nice: true, ticks: 6 },
    y: { axis: null },
    marks: [
      Plot.rectX([0], { x1: -32, x2: 32, y1: 0, y2: 1, fill: C.raised }),
      Plot.ruleX([0], { stroke: C.control }),
      Plot.dot(ok, { x: "dt_dias", y: () => 0.5, r: 5, fill: C.data, fillOpacity: 0.55, stroke: C.data }),
      chosen && chosen.dt_dias !== null
        ? Plot.dot([chosen], { x: "dt_dias", y: () => 0.5, r: 9, stroke: C.ink, strokeWidth: 2.5, fill: "none" })
        : null,
    ],
  });
}


/** Interpola la serie suavizada `a` en las fechas de `b`. */
function alignTo(a: { date: Date; z: number }[], b: { date: Date; z: number }[]) {
  const out: { date: Date; za: number; zb: number }[] = [];
  let j = 0;
  for (const p of b) {
    while (j < a.length - 2 && a[j + 1].date < p.date) j++;
    const p0 = a[j], p1 = a[j + 1];
    if (!p0 || !p1 || p.date < p0.date || p.date > p1.date) continue;
    const f = (p.date.getTime() - p0.date.getTime()) / Math.max(1, p1.date.getTime() - p0.date.getTime());
    out.push({ date: p.date, za: p0.z + f * (p1.z - p0.z), zb: p.z });
  }
  return out;
}

/** Brecha fantasma: z(verdor) − z(función). Positivo = se ve mejor de lo que funciona. */
export function gapIndex(o: { green: ZSeries; func: ZSeries; start: string; end: string; stop: string; width: number }): SVGSVGElement | HTMLElement {
  const t = T();
  const start = new Date(`${o.start.slice(0, 10)}T00:00:00`);
  const end = new Date(`${o.end.slice(0, 10)}T00:00:00`);
  const stop = new Date(`${o.stop.slice(0, 10)}T00:00:00`);
  const lo = new Date(start.getTime() - 200 * DAY);
  const hi = new Date(stop.getTime() + 60 * DAY);
  const rows = alignTo(smooth(o.green), smooth(o.func))
    .filter((r) => r.date >= lo && r.date <= hi)
    .map((r) => ({ date: r.date, gap: Math.max(-6, Math.min(6, r.za - r.zb)) }));
  return Plot.plot({
    ...base,
    width: o.width,
    height: 170,
    clip: true,
    x: { type: "utc", domain: [lo, hi], label: null, ticks: 6 },
    y: { domain: [-4, 4], ticks: [-2, 0, 2], label: t.axisGap, labelAnchor: "top", grid: true },
    marks: [
      Plot.rectX([{ a: start, b: end }], { x1: "a", x2: "b", y1: -4, y2: 4, fill: C.raised }),
      Plot.areaY(rows, { x: "date", y1: 0, y2: (r: { gap: number }) => Math.max(0, r.gap), fill: C.data, fillOpacity: 0.35 }),
      Plot.ruleY([0], { stroke: C.control }),
      Plot.ruleY([1, -1], { stroke: C.faint, strokeDasharray: "4,3" }),
      Plot.line(rows, { x: "date", y: "gap", stroke: C.data, strokeWidth: 1.8 }),
      Plot.text([{ x: hi }], { x: "x", y: 3.4, text: () => t.gapUp, textAnchor: "end", fill: C.faint, fontSize: 11 }),
      Plot.text([{ x: hi }], { x: "x", y: -3.4, text: () => t.gapDown, textAnchor: "end", fill: C.faint, fontSize: 11 }),
    ],
  });
}

/** Histéresis: verdor (x) contra función (y) a lo largo del episodio; el camino de ida no es el de vuelta. */
export function hysteresis(o: { green: ZSeries; func: ZSeries; start: string; end: string; stop: string; width: number }): SVGSVGElement | HTMLElement {
  const t = T();
  const start = new Date(`${o.start.slice(0, 10)}T00:00:00`);
  const end = new Date(`${o.end.slice(0, 10)}T00:00:00`);
  const stop = new Date(`${o.stop.slice(0, 10)}T00:00:00`);
  const lo = new Date(start.getTime() - 120 * DAY);
  const rows = alignTo(smooth(o.green), smooth(o.func))
    .filter((r) => r.date >= lo && r.date <= stop)
    .map((r) => ({ x: Math.max(-6, Math.min(3, r.za)), y: Math.max(-6, Math.min(3, r.zb)), date: r.date,
      phase: r.date < start ? t.phBefore : r.date <= end ? t.phDuring : t.phAfter }));
  const colors: Record<string, string> = { [t.phBefore]: C.faint, [t.phDuring]: C.second, [t.phAfter]: C.data };
  const segs = rows.slice(1).map((r, i) => ({ x1: rows[i].x, y1: rows[i].y, x2: r.x, y2: r.y, phase: r.phase }));
  const first = rows[0];
  const last = rows[rows.length - 1];
  // Encuadre: la trayectoria más la zona normal (z ≥ -1), con el mismo tramo en los dos ejes
  const ext = (k: "x" | "y") => [Math.min(-1.5, ...rows.map((r) => r[k])), Math.max(1, ...rows.map((r) => r[k]))];
  const [ex0, ex1] = ext("x");
  const [ey0, ey1] = ext("y");
  const span = Math.max(ex1 - ex0, ey1 - ey0) + 0.8;
  const dom = (a: number, b: number): [number, number] => { const c = (a + b) / 2; return [c - span / 2, c + span / 2]; };
  const dx = dom(ex0, ex1);
  const dy = dom(ey0, ey1);
  const side = Math.max(240, Math.min(440, o.width));
  return Plot.plot({
    ...base,
    width: o.width,
    height: side,
    marginLeft: 44,
    marginBottom: 40,
    x: { domain: dx, label: t.axisGreenZ, labelAnchor: "center", labelOffset: 34, ticks: 5, grid: true },
    y: { domain: dy, label: t.axisFuncZ, labelAnchor: "top", ticks: 5, grid: true },
    marks: [
      Plot.rect([{ x1: -1, x2: dx[1], y1: -1, y2: dy[1] }], { x1: "x1", x2: "x2", y1: "y1", y2: "y2", fill: C.raised }),
      Plot.text([{ x: dx[1], y: dy[1] }], { x: "x", y: "y", text: () => t.normalZone, textAnchor: "end", dx: -6, dy: 12, fill: C.faint, fontSize: 11 }),
      Plot.link(segs, { x1: "x1", y1: "y1", x2: "x2", y2: "y2", stroke: (s: { phase: string }) => colors[s.phase], strokeWidth: 2.2, markerEnd: "arrow" }),
      Plot.dot(rows, { x: "x", y: "y", r: 2.2, fill: (r: { phase: string }) => colors[r.phase] }),
      first ? Plot.text([first], { x: "x", y: "y", text: () => t.phStart, dx: 8, textAnchor: "start", fill: C.muted, fontSize: 11 }) : null,
      last ? Plot.text([last], { x: "x", y: "y", text: () => t.phEnd, dx: 8, textAnchor: "start", fill: C.data, fontSize: 11 }) : null,
    ],
  });
}

const VERDICT_GLYPH: Record<string, string> = {
  consistente: "C", estres_invisible: "E", censurada: "I", inconclusa: "?", fantasma: "F",
  verdor_tarde: "V", caida_posterior: "P", sin_recuperacion: "N", solo_modelo: "M",
};
export const DISCORDANT = new Set(["fantasma", "verdor_tarde", "caida_posterior", "estres_invisible", "sin_recuperacion"]);

/** Libro de auditorías: lugares × tiempo; cada sequía con impacto es una marca con su veredicto. */
export function ledger(audits: Audit[], order: string[], names: Record<string, string>, width: number,
  selected: Audit | null, onPick: (a: Audit) => void): SVGSVGElement {
  const ns = "http://www.w3.org/2000/svg";
  const rows = order.filter((id) => audits.some((a) => a.id === id));
  const narrow = width < 560;
  const left = narrow ? 14 : 150, rowH = 36, bottom = 26;
  const label = narrow ? 16 : 0;
  const top = 6 + label;
  const mw = narrow ? 16 : 22; // ancho de cada marca
  const t0 = new Date("2001-01-01").getTime();
  const t1 = new Date("2025-01-01").getTime();
  const X = (d: string) => left + ((new Date(d).getTime() - t0) / (t1 - t0)) * (width - left - 16);
  const H = top + rows.length * (rowH + label) - label + bottom;
  const svg = document.createElementNS(ns, "svg");
  svg.setAttribute("viewBox", `0 0 ${width} ${H}`);
  svg.setAttribute("role", "group");
  svg.setAttribute("class", "ledger");
  rows.forEach((id, r) => {
    const y = top + r * (rowH + label);
    const lab = document.createElementNS(ns, "text");
    lab.setAttribute("x", "0"); lab.setAttribute("y", String(narrow ? y - 2 : y + rowH / 2 + 4));
    lab.setAttribute("fill", C.muted); lab.setAttribute("font-size", "12"); lab.textContent = names[id] ?? id;
    svg.appendChild(lab);
    const track = document.createElementNS(ns, "rect");
    track.setAttribute("x", String(left)); track.setAttribute("y", String(y + rowH / 2 - 1));
    track.setAttribute("width", String(width - left - 16)); track.setAttribute("height", "2"); track.setAttribute("fill", C.raised);
    svg.appendChild(track);
    for (const a of audits.filter((x) => x.id === id && x.veredicto !== "sin_impacto")) {
      const cx = X(a.evento_inicio);
      const g = document.createElementNS(ns, "g");
      g.setAttribute("class", "lmark"); g.setAttribute("tabindex", "0"); g.setAttribute("role", "button");
      const disc = DISCORDANT.has(a.veredicto);
      const c = document.createElementNS(ns, "rect");
      c.setAttribute("x", String(cx - mw / 2)); c.setAttribute("y", String(y + 6));
      c.setAttribute("width", String(mw)); c.setAttribute("height", String(rowH - 12)); c.setAttribute("rx", "6");
      c.setAttribute("fill", disc ? C.data : a.veredicto === "consistente" ? C.second : C.raised);
      if (a.veredicto === "censurada" || a.veredicto === "inconclusa") { c.setAttribute("stroke", C.control); c.setAttribute("stroke-width", "1.5"); }
      if (selected && selected.id === a.id && selected.evento_inicio === a.evento_inicio) { c.setAttribute("stroke", C.ink); c.setAttribute("stroke-width", "2.5"); }
      g.appendChild(c);
      const txt = document.createElementNS(ns, "text");
      txt.setAttribute("x", String(cx)); txt.setAttribute("y", String(y + rowH / 2 + 4)); txt.setAttribute("text-anchor", "middle");
      txt.setAttribute("font-size", "11"); txt.setAttribute("font-weight", "600");
      txt.setAttribute("fill", disc || a.veredicto === "consistente" ? "#000" : C.ink);
      txt.textContent = VERDICT_GLYPH[a.veredicto] ?? "?";
      g.appendChild(txt);
      const tt = document.createElementNS(ns, "title");
      tt.textContent = `${names[id] ?? id} · ${a.evento_inicio.slice(0, 7)}: ${T().verdictName[a.veredicto] ?? a.veredicto}`;
      g.appendChild(tt);
      g.addEventListener("click", () => onPick(a));
      g.addEventListener("keydown", (e) => { if ((e as KeyboardEvent).key === "Enter") onPick(a); });
      svg.appendChild(g);
    }
  });
  for (let yy = 2001; yy <= 2025; yy += narrow ? 8 : 4) {
    const tx = document.createElementNS(ns, "text");
    tx.setAttribute("x", String(X(`${yy}-01-01`))); tx.setAttribute("y", String(H - 6));
    tx.setAttribute("fill", C.faint); tx.setAttribute("font-size", "11"); tx.setAttribute("text-anchor", "middle");
    tx.textContent = String(yy);
    svg.appendChild(tx);
  }
  return svg;
}

/** Cuadrantes: días hasta que vuelve el verdor (x) y la función (y); la diagonal es "vuelven juntos". */
export function quadrant(audits: Audit[], names: Record<string, string>, width: number): SVGSVGElement | HTMLElement {
  const t = T();
  const CAP = 420; // más allá: no volvió dentro de la ventana
  const pts: { x: number; y: number; f: string; name: string; v: string; censX: boolean; censY: boolean }[] = [];
  for (const a of audits) {
    if (!a.ndvi_impactado) continue;
    for (const f of ["gpp_modelo", "lst_menos_aire"]) {
      if (!a[`${f}_impactado`]) continue;
      const gx = a.ndvi_dias as number | null;
      const fy = a[`${f}_dias`] as number | null;
      pts.push({ x: gx ?? CAP, y: fy ?? CAP, f, name: `${names[a.id] ?? a.id} ${a.evento_inicio.slice(0, 7)}`, v: a.veredicto, censX: gx === null, censY: fy === null });
    }
  }
  const lo = -120;
  const hi = CAP + 20;
  return Plot.plot({
    ...base,
    width,
    height: Math.min(470, width),
    marginLeft: 52,
    x: { domain: [lo, hi], label: t.axisGreenDays, ticks: [0, 100, 200, 300], grid: true },
    y: { domain: [lo, hi], label: t.axisFuncDays, labelAnchor: "top", ticks: [0, 100, 200, 300], grid: true },
    symbol: { domain: ["gpp_modelo", "lst_menos_aire"], range: ["circle", "triangle"] },
    marks: [
      Plot.areaY([{ x: lo, y1: lo - 32, y2: lo + 32 }, { x: hi, y1: hi - 32, y2: hi + 32 }], { x: "x", y1: "y1", y2: "y2", fill: C.raised }),
      Plot.ruleX([CAP], { stroke: C.control, strokeDasharray: "3,3" }),
      Plot.ruleY([CAP], { stroke: C.control, strokeDasharray: "3,3" }),
      Plot.text([{ x: lo + 10, y: CAP - 16 }], { x: "x", y: "y", text: () => t.qPhantom, textAnchor: "start", fill: C.faint, fontSize: 11 }),
      Plot.text([{ x: CAP - 10, y: lo + 16 }], { x: "x", y: "y", text: () => t.qGreenLate, textAnchor: "end", fill: C.faint, fontSize: 11 }),
      Plot.text([{ x: 150, y: 150 }], { x: "x", y: "y", text: () => t.qJoint, rotate: -45, dy: -16, fill: C.faint, fontSize: 11 }),
      Plot.dot(pts, {
        x: "x", y: "y", symbol: "f", r: 5,
        stroke: (p: { v: string }) => (DISCORDANT.has(p.v) ? C.data : C.second),
        fill: (p: { v: string }) => (DISCORDANT.has(p.v) ? C.data : "none"),
        fillOpacity: 0.85, strokeWidth: 1.5,
        tip: true,
        title: (p: { name: string; f: string; x: number; y: number; censX: boolean; censY: boolean }) =>
          `${p.name}\n${t.sigGreen}: ${p.censX ? t.fNot : `${p.x} ${t.days}`}\n${p.f === "gpp_modelo" ? t.sigGpp : t.sigLst}: ${p.censY ? t.fNot : `${p.y} ${t.days}`}`,
      }),
    ],
  });
}


/** Línea temporal protagonista: cada mes frente a lo normal. Oculta hasta que la persona predice. */
export function monthTimeline(s: Series, stressHigh: boolean, show: boolean, width: number): SVGSVGElement | HTMLElement {
  const t = T();
  const years = s.anual.anios;
  const y0 = years[0];
  const y1 = years[years.length - 1];
  const at = (m: string) => new Date(`${m.slice(0, 7)}-15T00:00:00`);
  const rows = s.meses
    .map((m, i) => ({ date: at(m), v: s.anomalia_mensual[i] }))
    .filter((r): r is { date: Date; v: number } => r.v !== null);
  const abs = rows.map((r) => Math.abs(r.v)).sort((a, b) => a - b);
  const lim = (abs[Math.floor(abs.length * 0.98)] || 1) * 1.08;
  const clip = (v: number) => Math.max(-lim, Math.min(lim, v));
  const stress = (v: number) => (stressHigh ? v > 0 : v < 0);
  const narrow = width < 560;
  const bw = Math.max(1, ((width - 52) / rows.length) * 0.7);
  // La tendencia está ajustada sobre medias anuales: el valor del año y cae a mitad de ese año
  const tr = s.completa;
  const trend = [y0, y1].map((y) => ({ date: new Date(`${y}-07-01T00:00:00`), v: tr.intercepto + (tr.pendiente_decada / 10) * y }));
  return Plot.plot({
    ...base,
    width,
    height: narrow ? 180 : 240,
    marginLeft: 44,
    marginRight: 8,
    x: { domain: [new Date(`${y0}-01-01T00:00:00`), new Date(`${y1 + 1}-01-01T00:00:00`)], ticks: narrow ? 4 : 12, tickFormat: "%Y", label: null },
    y: { domain: [-lim, lim], ticks: 4, grid: true, label: null, tickFormat: (v: number) => fmt(v, Math.abs(lim) < 1 ? 2 : 0) },
    marks: [
      Plot.ruleY([0], { stroke: C.control }),
      show ? Plot.ruleX(rows, { x: "date", y1: 0, y2: (r: { v: number }) => clip(r.v), stroke: (r: { v: number }) => (stress(r.v) ? C.data : "#6b6f74"), strokeWidth: bw }) : null,
      show ? Plot.line(trend, { x: "date", y: "v", stroke: C.ink, strokeWidth: 2.5 }) : null,
      show ? null : Plot.text([0], { frameAnchor: "middle", dy: -18, text: () => t.tlHidden, fill: C.muted, fontSize: narrow ? 13 : 15 }),
    ],
  });
}

/** Incertidumbre a la vista: el rango probable de la pendiente frente al cero ("sin cambio"). */
export function uncertaintyBar(tr: Trend, digits: number, unit: string, width: number): SVGSVGElement | HTMLElement {
  const t = T();
  const [lo, hi] = tr.ic95_decada;
  const est = tr.pendiente_decada;
  const a = Math.min(lo, 0, est);
  const b = Math.max(hi, 0, est);
  const pad = (b - a) * 0.12 || 1;
  return Plot.plot({
    ...base,
    width,
    height: 118,
    marginLeft: 18,
    marginRight: 18,
    marginTop: 34,
    marginBottom: 40,
    x: { domain: [a - pad, b + pad], ticks: 5, label: `${unit} ${t.factPerDecade}`, labelAnchor: "center", labelOffset: 34 },
    y: { domain: [-1, 1], axis: null },
    marks: [
      Plot.ruleX([0], { stroke: C.muted, strokeDasharray: "3,3" }),
      // "0 = sin cambio" debajo de la barra, del lado que tenga sitio (arriba van los extremos del rango)
      Plot.text([0], { x: (d: number) => d, y: -0.95, text: () => t.uncZero, textAnchor: 0 > (a + b) / 2 ? "end" : "start", dx: 0 > (a + b) / 2 ? -6 : 6, fill: C.muted, fontSize: 12 }),
      Plot.link([{ x1: lo, x2: hi }], { x1: "x1", x2: "x2", y1: 0, y2: 0, stroke: C.data, strokeOpacity: 0.38, strokeWidth: 16, strokeLinecap: "round" }),
      Plot.dot([est], { x: (d: number) => d, y: 0, r: 8, fill: C.data, stroke: C.ground, strokeWidth: 2 }),
      Plot.text([lo, hi], { x: (d: number) => d, y: 0, text: (d: number) => fmtSigned(d, digits), dy: -20, fill: C.second, fontSize: 12 }),
    ],
  });
}
