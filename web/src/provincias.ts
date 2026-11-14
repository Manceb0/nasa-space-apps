// Lluvia por provincia: promedio de las celdas IMERG (0,1°) cuyo centro cae dentro de cada provincia.
// Si una provincia no contiene ningún centro de celda (Distrito Nacional), se usa la celda más cercana y se avisa.
// Métricas, todas contadas sobre 2001–2024 y comparando dos mitades de 12 años:
//   · mes muy seco: lluvia por debajo del 50 % de lo normal de ese mes, en meses cuyo normal es ≥ 20 mm;
//   · mes de lluvia extrema: total del mes dentro del 10 % más lluvioso de todos los meses de esa provincia.
import type { Grid } from "./field";

export interface ProvStat {
  id: string; name: string; cells: number; near: boolean;
  ratio: (number | null)[]; mm: (number | null)[];
  dryYear: number[]; wetYear: number[];
  dryA: number; dryB: number; wetA: number; wetB: number; p90: number;
}

type Ring = number[][];
const inRing = (x: number, y: number, r: Ring) => {
  let inside = false;
  for (let i = 0, j = r.length - 1; i < r.length; j = i++) {
    const [xi, yi] = r[i], [xj, yj] = r[j];
    if ((yi > y) !== (yj > y) && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) inside = !inside;
  }
  return inside;
};
const inGeom = (x: number, y: number, g: { type: string; coordinates: unknown }) => {
  const polys = (g.type === "Polygon" ? [g.coordinates] : g.coordinates) as Ring[][];
  return polys.some((p) => inRing(x, y, p[0]) && !p.slice(1).some((h) => inRing(x, y, h)));
};
const centroid = (g: { type: string; coordinates: unknown }) => {
  const polys = (g.type === "Polygon" ? [g.coordinates] : g.coordinates) as Ring[][];
  let sx = 0, sy = 0, n = 0;
  for (const p of polys) for (const [x, y] of p[0]) { sx += x; sy += y; n++; }
  return [sx / n, sy / n];
};

export function provinceStats(g: Grid, fc: { features: { properties: Record<string, string>; geometry: { type: string; coordinates: unknown } }[] }): ProvStat[] {
  const nT = g.meses.length;
  const years = Array.from(new Set(g.meses.map((m) => Number(m.slice(0, 4)))));
  const half = years[Math.floor(years.length / 2)];
  const live: [number, number][] = [];
  for (let i = 0; i < g.lats.length; i++) for (let j = 0; j < g.lons.length; j++) if (g.valores.some((m) => m[i][j] !== null)) live.push([i, j]);
  return fc.features.map((f) => {
    let cells = live.filter(([i, j]) => inGeom(g.lons[j], g.lats[i], f.geometry));
    let near = false;
    if (!cells.length) {
      const [cx, cy] = centroid(f.geometry);
      cells = [live.reduce((b, c) => (Math.hypot(g.lons[c[1]] - cx, g.lats[c[0]] - cy) < Math.hypot(g.lons[b[1]] - cx, g.lats[b[0]] - cy) ? c : b), live[0])];
      near = true;
    }
    const mm = g.meses.map((_, t) => {
      const v = cells.map(([i, j]) => g.valores[t][i][j]).filter((x): x is number => x !== null);
      return v.length ? v.reduce((a, b) => a + b, 0) / v.length : null;
    });
    const clim = Array.from({ length: 12 }, (_, mo) => {
      const v = mm.filter((x, t) => t % 12 === mo && x !== null) as number[];
      return v.length ? v.reduce((a, b) => a + b, 0) / v.length : null;
    });
    const ratio = mm.map((v, t) => (v === null || !clim[t % 12] ? null : v / clim[t % 12]!));
    const sorted = (mm.filter((x) => x !== null) as number[]).sort((a, b) => a - b);
    const p90 = sorted[Math.floor(sorted.length * 0.9)] ?? Infinity;
    const dryYear = years.map(() => 0), wetYear = years.map(() => 0);
    let dryA = 0, dryB = 0, wetA = 0, wetB = 0;
    for (let t = 0; t < nT; t++) {
      const y = Number(g.meses[t].slice(0, 4));
      const k = years.indexOf(y);
      const dry = ratio[t] !== null && ratio[t]! < 0.5 && (clim[t % 12] ?? 0) >= 20;
      const wet = mm[t] !== null && mm[t]! >= p90;
      if (dry) { dryYear[k]++; if (y < half) dryA++; else dryB++; }
      if (wet) { wetYear[k]++; if (y < half) wetA++; else wetB++; }
    }
    return { id: f.properties.shapeID, name: f.properties.shapeName, cells: cells.length, near, ratio, mm, dryYear, wetYear, dryA, dryB, wetA, wetB, p90 };
  });
}
