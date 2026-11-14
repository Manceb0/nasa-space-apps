import * as Plot from "@observablehq/plot";
import type { Phantom, SensRow, Series, Trend, Window } from "./data";
import { fmt } from "./text";

export const C = {
  ground: "#0d1316",
  surface: "#151e22",
  surface2: "#1c272c",
  ink: "#e9edee",
  muted: "#93a1a7",
  data: "#e3a33b",
  dataSoft: "rgba(227,163,59,0.22)",
  cool: "#6fb7d6",
};

const base = {
  style: { background: "transparent", color: C.muted, fontFamily: "Poppins, system-ui, sans-serif", fontSize: "12px" },
  marginLeft: 52,
  marginRight: 16,
  marginTop: 16,
  marginBottom: 36,
};

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
  const xs = [x0, x1];
  return xs.map((x) => {
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
    height: Math.max(260, Math.min(360, width * 0.42)),
    x: { label: null, tickFormat: (d: number) => String(d), ticks: 8 },
    y: { label: `Diferencia con lo normal (${unit})`, labelAnchor: "top", grid: true, nice: true },
    marks: [
      Plot.ruleY([0], { stroke: C.muted, strokeOpacity: 0.5 }),
      Plot.areaY(fan(active, a0, a1), { x: "x", y1: "y1", y2: "y2", fill: C.data, fillOpacity: 0.16 }),
      w ? Plot.line(lineFor(full, y0, y1), { x: "x", y: "y", stroke: C.muted, strokeDasharray: "5,4", strokeWidth: 1.5 }) : null,
      Plot.line(lineFor(active, a0, a1), { x: "x", y: "y", stroke: C.data, strokeWidth: 2.5 }),
      Plot.dot(pts, {
        x: "x", y: "y", r: 4.5,
        fill: (d: { x: number }) => (inWin(d.x) ? C.data : C.ground),
        stroke: (d: { x: number }) => (inWin(d.x) ? C.data : C.muted),
        strokeWidth: 1.5,
        tip: true,
        title: (d: { x: number; y: number }) => `${d.x}: ${fmt(d.y, 2)} ${unit} respecto a lo normal`,
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
    height: Math.max(240, Math.min(320, width * 0.36)),
    x: { label: null, type: "utc" },
    y: { label: `Valor mensual (${unit})`, labelAnchor: "top", grid: true, nice: true },
    marks: [
      Plot.line(rows, { x: "date", y: "clim", stroke: C.muted, strokeWidth: 1, strokeDasharray: "3,3" }),
      Plot.line(rows, { x: "date", y: "v", stroke: C.data, strokeWidth: 1.2 }),
    ],
  });
}

const CELL = { sube: C.data, baja: C.data, indicio: "rgba(227,163,59,0.38)", sin_evidencia: C.surface2, insuficiente: C.surface };

/** El mapa de ventanas: cada celda es un intervalo de años; el color es lo que concluirías. Hecho a mano para poder hacer clic. */
export function windowMatrix(s: Series, selected: Window | null, onPick: (w: Window) => void): SVGSVGElement {
  const years = s.anual.anios;
  const y0 = years[0];
  const minLen = Math.min(...s.ventanas.map((w) => w.fin - w.inicio + 1));
  const firstEnd = y0 + minLen - 1;
  const n = years.length - minLen + 1; // filas = años de inicio posibles; columnas = años de fin posibles
  const cell = 28;
  const pad = { l: 48, t: 8, r: 8, b: 40 };
  const W = pad.l + n * cell + pad.r;
  const H = pad.t + n * cell + pad.b;
  const ns = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(ns, "svg");
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
  svg.setAttribute("class", "matrix");
  svg.setAttribute("role", "group");
  svg.setAttribute("aria-label", "Mapa de ventanas: filas = año de inicio, columnas = año de fin");
  const traps = new Set(s.ventanas_que_enganan.map((w) => `${w.inicio}-${w.fin}`));
  for (const w of s.ventanas) {
    const col = w.fin - firstEnd;
    const row = w.inicio - y0;
    const g = document.createElementNS(ns, "g");
    g.setAttribute("class", "mcell");
    g.setAttribute("tabindex", "0");
    g.setAttribute("role", "button");
    g.setAttribute("aria-label", `${w.inicio} a ${w.fin}: ${w.veredicto.replace("_", " ")}`);
    const r = document.createElementNS(ns, "rect");
    r.setAttribute("x", String(pad.l + col * cell + 1));
    r.setAttribute("y", String(pad.t + row * cell + 1));
    r.setAttribute("width", String(cell - 2));
    r.setAttribute("height", String(cell - 2));
    r.setAttribute("rx", "4");
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
    if (traps.has(`${w.inicio}-${w.fin}`)) g.setAttribute("data-trap", "1");
    const title = document.createElementNS(ns, "title");
    title.textContent = `${w.inicio}–${w.fin}`;
    g.appendChild(title);
    g.addEventListener("click", () => onPick(w));
    g.addEventListener("keydown", (e) => {
      if ((e as KeyboardEvent).key === "Enter" || (e as KeyboardEvent).key === " ") {
        e.preventDefault();
        onPick(w);
      }
    });
    svg.appendChild(g);
  }
  const label = (x: number, y: number, txt: string, anchor = "middle") => {
    const t = document.createElementNS(ns, "text");
    t.setAttribute("x", String(x));
    t.setAttribute("y", String(y));
    t.setAttribute("text-anchor", anchor);
    t.setAttribute("class", "axis");
    t.textContent = txt;
    svg.appendChild(t);
  };
  for (let i = 0; i < n; i += 2) {
    label(pad.l + i * cell + cell / 2, pad.t + n * cell + 16, String(firstEnd + i));
    label(pad.l - 6, pad.t + i * cell + cell / 2 + 4, String(y0 + i), "end");
  }
  label(pad.l + (n * cell) / 2, H - 4, "año en que termina el intervalo →");
  label(pad.l - 6, pad.t - 0, "", "end");
  return svg;
}

/** Expediente PHANTOM: SPI-3 real con las sequías usadas. */
export function spiChart(d: Phantom["sequias"][number], width: number): SVGSVGElement | HTMLElement {
  const rows = d.spi3.meses
    .map((m, i) => ({ date: new Date(`${m}-01T00:00:00`), v: d.spi3.valores[i] }))
    .filter((r) => r.v !== null) as { date: Date; v: number }[];
  const ev = d.eventos.map((e) => ({ a: new Date(`${e.inicio.slice(0, 7)}-01T00:00:00`), b: new Date(`${e.fin.slice(0, 7)}-28T00:00:00`) }));
  return Plot.plot({
    ...base,
    width,
    height: 200,
    x: { type: "utc", label: null },
    y: { label: "SPI-3", labelAnchor: "top", domain: [-3, 3] },
    marks: [
      Plot.rectX(ev, { x1: "a", x2: "b", y1: -3, y2: 3, fill: C.data, fillOpacity: 0.14 }),
      Plot.ruleY([0], { stroke: C.muted, strokeOpacity: 0.5 }),
      Plot.ruleY([-1], { stroke: C.muted, strokeDasharray: "4,3" }),
      Plot.rectY(rows, { x: "date", interval: "month", y: "v", fill: (r: { v: number }) => (r.v < 0 ? C.data : C.surface2) }),
    ],
  });
}

/** Challenge the Evidence: Δt de cada combinación precalculada. */
export function sensitivityStrip(rows: SensRow[], chosen: SensRow | null, width: number): SVGSVGElement | HTMLElement {
  const ok = rows.filter((r) => r.estado === "ambos_recuperados" && r.dt_dias !== null);
  return Plot.plot({
    ...base,
    width,
    height: 150,
    marginLeft: 16,
    x: { label: "Δt = función − verdor (días)", grid: true, nice: true },
    y: { axis: null },
    marks: [
      Plot.rectX([0], { x1: -32, x2: 32, y1: 0, y2: 1, fill: C.surface2 }),
      Plot.ruleX([0], { stroke: C.muted }),
      Plot.dot(ok, { x: "dt_dias", y: () => 0.5, r: 5, fill: C.data, fillOpacity: 0.55, stroke: C.data }),
      chosen && chosen.dt_dias !== null
        ? Plot.dot([chosen], { x: "dt_dias", y: () => 0.5, r: 9, stroke: C.ink, strokeWidth: 2.5, fill: "none" })
        : null,
    ],
  });
}
