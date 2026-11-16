// El campo de tendencia como imagen suave, al estilo de los mapas meteorológicos:
// interpolación bilineal entre los centros de las celdas de 0,1° del contrato (sin inventar valores fuera de ellas)
// y recortado a la costa con los límites oficiales, para que el borde sea la isla y no un cuadro.
import type { CellLayer, FC, Rej } from "./datos";

export type RGB = [number, number, number];
const GREY: RGB = [120, 124, 130];
// Escalas divergentes: hacia lo seco (cálida) y hacia lo húmedo (fría), con gris en el cero
const WARM: [number, RGB][] = [[0, GREY], [0.25, [255, 214, 10]], [0.55, [255, 159, 10]], [0.8, [255, 69, 58]], [1, [200, 30, 70]]];
const COOL: [number, RGB][] = [[0, GREY], [0.25, [120, 214, 245]], [0.55, [40, 160, 240]], [0.8, [10, 110, 220]], [1, [8, 78, 170]]];
const ramp = (stops: [number, RGB][], t: number): RGB => {
  for (let k = 1; k < stops.length; k++) if (t <= stops[k][0]) {
    const [a, ca] = stops[k - 1], [b, cb] = stops[k], u = (t - a) / (b - a);
    return ca.map((v, i) => Math.round(v + (cb[i] - v) * u)) as RGB;
  }
  return stops[stops.length - 1][1];
};
/** Color de un valor con signo: m = |v| / máximo, hacia lo seco o lo húmedo. */
export const colorOf = (m: number, towardDry: boolean): RGB => ramp(towardDry ? WARM : COOL, Math.min(1, Math.max(0, m)));
/** La rampa en CSS, para la leyenda (de lo húmedo a lo seco, pasando por el cero). */
export const rampCss = (dryRight: boolean) => {
  const side = (s: [number, RGB][]) => s.map(([, c]) => `rgb(${c.join(",")})`);
  const w = side(WARM), c = side(COOL);
  const left = dryRight ? c.slice().reverse() : w.slice().reverse();
  const right = dryRight ? w.slice(1) : c.slice(1);
  return `linear-gradient(90deg, ${[...left, ...right].join(", ")})`; // taste-skill-ignore: escala de color de los datos
};

/** Máximo para la escala: percentil 95 de |pendiente| (un valor extremo no apaga el resto). */
export const scaleMax = (vals: (number | null)[]) => {
  const a = vals.filter((x): x is number => x !== null).map(Math.abs).sort((x, y) => x - y);
  return a[Math.floor(a.length * 0.95)] || a[a.length - 1] || 1;
};

export function trendField(R: Rej, lay: CellLayer, qMax: number, max: number, towardDry: (v: number) => boolean, land: FC | null, S = 12) {
  const W = R.nx * S, H = R.ny * S;
  const lon0 = R.lon_bordes[0], lon1 = R.lon_bordes[R.nx], lat0 = R.lat_bordes[0], lat1 = R.lat_bordes[R.ny];
  const val = (i: number, j: number) => {
    if (i < 0 || j < 0 || i >= R.ny || j >= R.nx) return null;
    const k = i * R.nx + j;
    return R.incluida[k] ? lay.pendiente_decada[k] : null;
  };
  const sig = (i: number, j: number) => (lay.q[i * R.nx + j] ?? 1) <= qMax ? 1 : 0;
  const px = new Uint8ClampedArray(W * H * 4);
  const res = R.lon[1] - R.lon[0];
  for (let y = 0; y < H; y++) {
    const lat = lat1 - ((y + 0.5) / H) * (lat1 - lat0);
    const fi = (lat - R.lat[0]) / res;
    for (let x = 0; x < W; x++) {
      const lon = lon0 + ((x + 0.5) / W) * (lon1 - lon0);
      const fj = (lon - R.lon[0]) / res;
      const i0 = Math.floor(fi), j0 = Math.floor(fj), ty = fi - i0, tx = fj - j0;
      let sw = 0, sv = 0, ss = 0;
      for (const [di, dj, w] of [[0, 0, (1 - ty) * (1 - tx)], [0, 1, (1 - ty) * tx], [1, 0, ty * (1 - tx)], [1, 1, ty * tx]] as const) {
        const v = val(i0 + di, j0 + dj);
        if (v === null || w === 0) continue;
        sw += w; sv += w * v; ss += w * sig(i0 + di, j0 + dj);
      }
      if (sw === 0) {
        // Borde de la costa: la celda incluida más cercana (no se inventa nada fuera del alcance de una celda)
        const ni = Math.round(fi), nj = Math.round(fj), v = val(ni, nj);
        if (v === null) continue;
        sw = 1; sv = v; ss = sig(ni, nj);
      }
      const v = sv / sw, s = ss / sw, m = Math.min(1, Math.abs(v) / max);
      const c = colorOf(m, towardDry(v));
      const o = 4 * (y * W + x);
      px[o] = c[0]; px[o + 1] = c[1]; px[o + 2] = c[2];
      px[o + 3] = Math.round(255 * ((0.2 + 0.3 * m) * (1 - s) + (0.6 + 0.32 * m) * s));
    }
  }
  if (land) clipToLand(px, W, H, land, (lon) => ((lon - lon0) / (lon1 - lon0)) * W, (lat) => ((lat1 - lat) / (lat1 - lat0)) * H);
  return { px, w: W, h: H, bounds: [lon0, lat0, lon1, lat1] as [number, number, number, number] };
}

function clipToLand(px: Uint8ClampedArray, W: number, H: number, land: FC, X: (lon: number) => number, Y: (lat: number) => number) {
  const c = document.createElement("canvas");
  c.width = W; c.height = H;
  const ctx = c.getContext("2d")!;
  const img = ctx.createImageData(W, H);
  img.data.set(px);
  ctx.putImageData(img, 0, 0);
  ctx.globalCompositeOperation = "destination-in";
  ctx.beginPath();
  for (const f of land.features) {
    const polys = f.geometry.type === "Polygon" ? [f.geometry.coordinates] : f.geometry.coordinates;
    for (const p of polys) for (const ring of p) ring.forEach(([lon, lat]: number[], k: number) => (k ? ctx.lineTo(X(lon), Y(lat)) : ctx.moveTo(X(lon), Y(lat))));
  }
  ctx.fill("evenodd");
  px.set(ctx.getImageData(0, 0, W, H).data);
}

/** Centros de las celdas significativas: el punteado clásico de los mapas de tendencia (Wilks 2016). */
export function stipple(R: Rej, lay: CellLayer, qMax: number) {
  const features = [];
  for (let i = 0; i < R.ny; i++) for (let j = 0; j < R.nx; j++) {
    const k = i * R.nx + j;
    if (R.incluida[k] && lay.pendiente_decada[k] !== null && (lay.q[k] ?? 1) <= qMax)
      features.push({ type: "Feature" as const, properties: {}, geometry: { type: "Point" as const, coordinates: [R.lon[j], R.lat[i]] } });
  }
  return { type: "FeatureCollection" as const, features };
}

/** La celda bajo un punto del mapa (o -1). */
export const cellAt = (R: Rej, lon: number, lat: number) => {
  const j = R.lon_bordes.findIndex((b, k) => k < R.nx && lon >= b && lon < R.lon_bordes[k + 1]);
  const i = R.lat_bordes.findIndex((b, k) => k < R.ny && lat >= b && lat < R.lat_bordes[k + 1]);
  return i < 0 || j < 0 ? -1 : i * R.nx + j;
};

/** La clase de confianza por celda (robusta, consistente, en disputa, sin señal) como imagen de celdas nítidas,
 *  recortada a la costa: es una categoría, así que no se interpola. */
export function classField(R: Rej, clase: (number | null)[], colors: string[], land: FC | null, S = 12) {
  const W = R.nx * S, H = R.ny * S;
  const lon0 = R.lon_bordes[0], lon1 = R.lon_bordes[R.nx], lat0 = R.lat_bordes[0], lat1 = R.lat_bordes[R.ny];
  const rgb = colors.map((c) => [parseInt(c.slice(1, 3), 16), parseInt(c.slice(3, 5), 16), parseInt(c.slice(5, 7), 16)]);
  const alpha = [0.9, 0.85, 0.9, 0.16];
  const px = new Uint8ClampedArray(W * H * 4);
  for (let y = 0; y < H; y++) {
    const i = R.ny - 1 - Math.floor(y / S);
    for (let x = 0; x < W; x++) {
      const k = i * R.nx + Math.floor(x / S), c = clase[k];
      if (!R.incluida[k] || c === null || c === undefined) continue;
      const o = 4 * (y * W + x);
      px[o] = rgb[c][0]; px[o + 1] = rgb[c][1]; px[o + 2] = rgb[c][2]; px[o + 3] = Math.round(255 * alpha[c]);
    }
  }
  if (land) clipToLand(px, W, H, land, (lon) => ((lon - lon0) / (lon1 - lon0)) * W, (lat) => ((lat1 - lat) / (lat1 - lat0)) * H);
  return { px, w: W, h: H, bounds: [lon0, lat0, lon1, lat1] as [number, number, number, number] };
}

// ── Calor: el mismo dato como un campo de color suave, saturado y con un brillo leve ──
// Escala divergente con la esencia de los mapas de calor: violeta y azul hacia lo húmedo, verde en el cero,
// amarillo, naranja y rojo hacia lo seco. El color es el dato; el brillo crece con la magnitud.
const HEAT: [number, RGB][] = [[0, [112, 44, 232]], [0.17, [44, 96, 255]], [0.33, [0, 196, 255]], [0.5, [52, 214, 128]], [0.67, [255, 226, 46]], [0.83, [255, 134, 24]], [1, [244, 36, 56]]];
/** Color de un valor normalizado en [-1, 1] (positivo = hacia lo seco). */
export const heatOf = (s: number): RGB => ramp(HEAT, (Math.max(-1, Math.min(1, s)) + 1) / 2);
/** La rampa del calor en CSS, para la leyenda. */
export const heatCss = () => `linear-gradient(90deg, ${HEAT.map(([t, c]) => `rgb(${c.join(",")}) ${Math.round(t * 100)}%`).join(", ")})`; // taste-skill-ignore: escala de color de los datos

/** Campo de calor: interpolación bilineal entre centros de celda, desenfoque y brillo en el lienzo, y recorte
 *  a las celdas con dato (las nulas quedan sin color) y a la costa. `s(k)` da el valor normalizado de la celda k
 *  en [-1, 1] o null; `weak(k)` atenúa las celdas cuyo cambio no se distingue del azar. */
export function heatField(R: Rej, s: (k: number) => number | null, weak: (k: number) => boolean, land: FC | null, S = 16) {
  const W = R.nx * S, H = R.ny * S;
  const lon0 = R.lon_bordes[0], lon1 = R.lon_bordes[R.nx], lat0 = R.lat_bordes[0], lat1 = R.lat_bordes[R.ny];
  const res = R.lon[1] - R.lon[0];
  const val = (i: number, j: number) => (i < 0 || j < 0 || i >= R.ny || j >= R.nx || !R.incluida[i * R.nx + j] ? null : s(i * R.nx + j));
  const base = new Uint8ClampedArray(W * H * 4), mask = new Uint8ClampedArray(W * H * 4);
  for (let y = 0; y < H; y++) {
    const lat = lat1 - ((y + 0.5) / H) * (lat1 - lat0), fi = (lat - R.lat[0]) / res;
    for (let x = 0; x < W; x++) {
      const lon = lon0 + ((x + 0.5) / W) * (lon1 - lon0), fj = (lon - R.lon[0]) / res;
      const o = 4 * (y * W + x);
      // la máscara: la celda que contiene el píxel tiene dato
      if (val(Math.round(fi), Math.round(fj)) !== null) mask[o + 3] = 255;
      const i0 = Math.floor(fi), j0 = Math.floor(fj), ty = fi - i0, tx = fj - j0;
      let sw = 0, sv = 0, sk = 0;
      for (const [di, dj, w] of [[0, 0, (1 - ty) * (1 - tx)], [0, 1, (1 - ty) * tx], [1, 0, ty * (1 - tx)], [1, 1, ty * tx]] as const) {
        const v = val(i0 + di, j0 + dj);
        if (v === null || w === 0) continue;
        sw += w; sv += w * v; sk += w * (weak((i0 + di) * R.nx + j0 + dj) ? 1 : 0);
      }
      if (sw === 0) { const v = val(Math.round(fi), Math.round(fj)); if (v === null) continue; sw = 1; sv = v; sk = weak(Math.round(fi) * R.nx + Math.round(fj)) ? 1 : 0; }
      const v = sv / sw, m = Math.min(1, Math.abs(v)), c = heatOf(v);
      base[o] = c[0]; base[o + 1] = c[1]; base[o + 2] = c[2];
      base[o + 3] = Math.round(255 * (0.5 + 0.5 * m) * (1 - 0.4 * (sk / sw)));
    }
  }
  const cv = (px: Uint8ClampedArray) => { const c = document.createElement("canvas"); c.width = W; c.height = H; const x = c.getContext("2d")!; const im = x.createImageData(W, H); im.data.set(px); x.putImageData(im, 0, 0); return c; };
  const src = cv(base), out = document.createElement("canvas");
  out.width = W; out.height = H;
  const ctx = out.getContext("2d")!;
  // desenfoque suave y un poco más de saturación; encima, el mismo campo muy desenfocado en «screen» como brillo
  ctx.filter = `blur(${Math.round(S * 0.75)}px) saturate(1.25)`;
  ctx.drawImage(src, 0, 0);
  ctx.globalCompositeOperation = "screen"; ctx.globalAlpha = 0.4;
  ctx.filter = `blur(${Math.round(S * 1.8)}px)`;
  ctx.drawImage(src, 0, 0);
  // recorte a las celdas con dato (borde algo suave) y a la costa
  ctx.globalAlpha = 1; ctx.globalCompositeOperation = "destination-in";
  ctx.filter = `blur(${Math.round(S * 0.3)}px)`;
  ctx.drawImage(cv(mask), 0, 0);
  ctx.filter = "none"; ctx.globalCompositeOperation = "source-over";
  const px = new Uint8ClampedArray(ctx.getImageData(0, 0, W, H).data);
  if (land) clipToLand(px, W, H, land, (lon) => ((lon - lon0) / (lon1 - lon0)) * W, (lat) => ((lat1 - lat) / (lat1 - lat0)) * H);
  return { px, w: W, h: H, bounds: [lon0, lat0, lon1, lat1] as [number, number, number, number] };
}
