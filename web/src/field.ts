// Campo de lluvia: cada punto es el centro real de una celda IMERG de 0,1° (unos 11 km).
// No se interpola nada: el tamaño y el color de cada punto dicen cuánto llovió ese mes frente a lo normal
// para ese mismo mes del año en esa celda (media 2001–2024, calculada aquí, a la vista).
import L from "leaflet";

export interface Grid {
  lats: number[]; lons: number[]; meses: string[]; valores: (number | null)[][][];
  resolucion_grados: number; fuente: string; cita: string; unidad: string;
}

interface Dot { m: L.CircleMarker; i: number; j: number; r: number; tr: number }

const DRY = [255, 159, 10];
const VERY_DRY = [229, 86, 111];
const WET = [142, 240, 198];
const mix = (a: number[], b: number[], t: number) => `rgb(${a.map((v, k) => Math.round(v + (b[k] - v) * t)).join(",")})`;

export function rainField(map: L.Map, g: Grid, label: (mes: string, mm: number | null, pct: number | null) => string) {
  const renderer = L.canvas({ padding: 0.4 });
  const nT = g.meses.length;
  // Normal de cada celda para cada mes del año
  const clim: (number | null)[][][] = Array.from({ length: 12 }, () => g.lats.map(() => g.lons.map(() => null)));
  for (let mo = 0; mo < 12; mo++) {
    for (let i = 0; i < g.lats.length; i++) for (let j = 0; j < g.lons.length; j++) {
      let s = 0, n = 0;
      for (let t = mo; t < nT; t += 12) { const v = g.valores[t][i][j]; if (v !== null) { s += v; n++; } }
      clim[mo][i][j] = n ? s / n : null;
    }
  }
  const dots: Dot[] = [];
  for (let i = 0; i < g.lats.length; i++) for (let j = 0; j < g.lons.length; j++) {
    if (g.valores.every((m) => m[i][j] === null)) continue;
    const m = L.circleMarker([g.lats[i], g.lons[j]], { renderer, radius: 0, stroke: false, fillColor: "#8a8c92", fillOpacity: 0.9 }).addTo(map);
    dots.push({ m, i, j, r: 0, tr: 0 });
  }
  const cellPx = () => {
    const a = map.latLngToContainerPoint([g.lats[0], g.lons[0]]);
    const b = map.latLngToContainerPoint([g.lats[0], g.lons[0] + g.resolucion_grados]);
    return Math.abs(b.x - a.x);
  };
  let current = -1;
  let raf = 0;
  const animate = (ms: number) => {
    cancelAnimationFrame(raf);
    const from = dots.map((d) => d.r);
    const t0 = performance.now();
    const step = (now: number) => {
      const f = ms <= 0 ? 1 : Math.min(1, (now - t0) / ms);
      const e = 1 - Math.pow(1 - f, 3);
      dots.forEach((d, k) => { d.r = from[k] + (d.tr - from[k]) * e; d.m.setRadius(Math.max(0, d.r)); });
      if (f < 1) raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
  };
  const show = (mes: string, ms = 320) => {
    const t = g.meses.indexOf(mes);
    if (t < 0) return;
    current = t;
    const mo = Number(mes.slice(5, 7)) - 1;
    const base = Math.max(2.2, cellPx() * 0.5);
    for (const d of dots) {
      const v = g.valores[t][d.i][d.j];
      const c = clim[mo][d.i][d.j];
      const ratio = v !== null && c ? v / c - 1 : null;
      const mag = ratio === null ? 0 : Math.min(1, Math.abs(ratio) / 0.8);
      d.tr = ratio === null ? base * 0.25 : base * (0.32 + 0.68 * mag);
      const col = ratio === null ? "#5a5c62" : ratio < 0 ? mix(DRY, VERY_DRY, Math.min(1, -ratio / 0.7)) : mix([170, 190, 185], WET, Math.min(1, ratio / 0.6));
      d.m.setStyle({ fillColor: col, fillOpacity: ratio === null ? 0.35 : 0.55 + 0.4 * mag });
      d.m.unbindTooltip().bindTooltip(label(mes, v, ratio === null ? null : Math.round(100 * (1 + ratio))), { className: "zone-tip", direction: "top" });
    }
    animate(ms);
  };
  // Entrada: los puntos crecen desde el centro del mapa hacia fuera
  const intro = (mes: string) => {
    show(mes, 0);
    cancelAnimationFrame(raf);
    const c = map.getCenter();
    const targets = dots.map((d) => d.tr);
    dots.forEach((d) => { d.r = 0; d.m.setRadius(0); });
    const dist = dots.map((d) => Math.hypot(g.lats[d.i] - c.lat, g.lons[d.j] - c.lng));
    const maxD = Math.max(...dist, 0.01);
    const t0 = performance.now();
    const step = (now: number) => {
      let busy = false;
      dots.forEach((d, k) => {
        const f = Math.max(0, Math.min(1, (now - t0 - (dist[k] / maxD) * 900) / 600));
        if (f < 1) busy = true;
        d.r = targets[k] * (1 - Math.pow(1 - f, 3));
        d.m.setRadius(d.r);
      });
      if (busy) raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
  };
  map.on("zoomend", () => { if (current >= 0) show(g.meses[current], 0); });
  return { show, intro, months: g.meses };
}
