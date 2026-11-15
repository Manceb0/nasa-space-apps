// Vista «Crestas»: perfiles de relieve este-oeste (Copernicus GLO-90) apilados de norte a sur, como la pieza 3 de la
// galería, pero vivos. El color de cada tramo es el de su celda de 0,1° en lo que el mapa esté mostrando (acuerdo de las
// dos fuentes, tendencia de una de ellas o el año elegido); quien decide el color es la vista, aquí solo se dibuja.
// Movimiento: al cambiar de pregunta el color nuevo baja de norte a sur, fila a fila, como se lee el mapa.
import { cellAt } from "./campo";
import type { FC, Rej } from "./datos";

export interface Relieve {
  lon0: number; dlon: number; nlon: number; paso_lat: number;
  filas: { lat: number; z: number[] }[];
  yuna: [number, number, number][];
  hatillo: { lat: number; lon: number; z: number };
  pico: { lat: number; lon: number; z: number };
}
/** Color de una celda: [r, g, b, alfa] o null (fuera del dominio). */
export type RGBA = [number, number, number, number];
type Pad = { top: number; bottom: number; left: number; right: number };

const K = 1e-4; // grados de latitud por metro: exageración vertical ≈ ×11, igual que la figura del informe
const LON: [number, number] = [-72.05, -68.3], LAT: [number, number] = [17.42, 20.02];
const OUT: RGBA = [138, 143, 150, 0.22];
const SWEEP = 520, FADE = 240;

/** Provincia (ISO) que contiene cada celda de la rejilla; prueba el centro y luego cuatro puntos interiores. */
export function cellProvinces(R: Rej, fc: FC | null): (string | null)[] {
  if (!fc) return R.incluida.map(() => null);
  const polys = fc.features.map((f) => {
    const g = f.geometry, rings: number[][][] = g.type === "Polygon" ? [g.coordinates[0]] : g.coordinates.map((p: number[][][]) => p[0]);
    let x0 = 180, y0 = 90, x1 = -180, y1 = -90;
    for (const r of rings) for (const [x, y] of r) { x0 = Math.min(x0, x); y0 = Math.min(y0, y); x1 = Math.max(x1, x); y1 = Math.max(y1, y); }
    return { iso: String(f.properties.shapeISO), rings, b: [x0, y0, x1, y1] };
  });
  const inside = (r: number[][], x: number, y: number) => {
    let c = false;
    for (let i = 0, j = r.length - 1; i < r.length; j = i++) {
      const [xi, yi] = r[i], [xj, yj] = r[j];
      if ((yi > y) !== (yj > y) && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) c = !c;
    }
    return c;
  };
  const at = (x: number, y: number) => polys.find((p) => x >= p.b[0] && x <= p.b[2] && y >= p.b[1] && y <= p.b[3] && p.rings.some((r) => inside(r, x, y)))?.iso ?? null;
  return R.incluida.map((_, k) => {
    const x = R.lon[k % R.nx], y = R.lat[Math.floor(k / R.nx)];
    for (const [dx, dy] of [[0, 0], [-0.03, -0.03], [0.03, -0.03], [-0.03, 0.03], [0.03, 0.03]]) { const p = at(x + dx, y + dy); if (p) return p; }
    return null;
  });
}

export function ridges(host: HTMLElement, rel: Relieve, R: Rej, o: {
  color: (k: number) => RGBA | null;
  /** null: nada elegido; true: fuera de la provincia elegida; false: dentro (se resalta). */
  dim: (k: number) => boolean | null;
  pad: () => Pad;
  labels: { yuna: string; hatillo: string; scale: string; credit: string };
  /** Proyección del mapa (lon, lat) → píxel del contenedor; null mientras el mapa no está listo. */
  proj: () => ((lon: number, lat: number) => { x: number; y: number }) | null;
}) {
  const cv = document.createElement("canvas");
  cv.className = "ridge";
  cv.setAttribute("role", "img");
  host.appendChild(cv);
  const g = cv.getContext("2d")!;
  const lons = Array.from({ length: rel.nlon }, (_, i) => rel.lon0 + i * rel.dlon);
  // celda de cada muestra (fija: el relieve no cambia)
  const cellIdx = rel.filas.map((f) => lons.map((x) => cellAt(R, x, f.lat)));
  let prev: RGBA[] = [], next: RGBA[] = [], t0 = 0, raf = 0, on = false;
  // Pantalla = cámara del mapa (sin giro ni inclinación): x lineal en la longitud, y lineal en la Mercator de la latitud
  let W = 0, H = 0, ax = 0, bx = 1, ay = 0, by = -1;
  const merc = (lat: number) => Math.log(Math.tan(Math.PI / 4 + (lat * Math.PI) / 360));
  const unmerc = (m: number) => ((2 * Math.atan(Math.exp(m)) - Math.PI / 2) * 180) / Math.PI;

  const size = () => {
    const r = host.getBoundingClientRect(), dpr = Math.min(2, devicePixelRatio || 1);
    const w = Math.round(r.width * dpr), h = Math.round(r.height * dpr);
    W = r.width; H = r.height;
    if (cv.width !== w || cv.height !== h) {
      cv.width = w; cv.height = h;
      cv.style.width = `${W}px`; cv.style.height = `${H}px`;
    }
    g.setTransform(dpr, 0, 0, dpr, 0, 0);
  };
  const camera = () => {
    const p = o.pad(), pr = o.proj();
    if (pr) {
      const a = pr(LON[0], LAT[0]), b = pr(LON[1], LAT[1]);
      bx = (b.x - a.x) / (LON[1] - LON[0]); ax = a.x - bx * LON[0];
      by = (b.y - a.y) / (merc(LAT[1]) - merc(LAT[0])); ay = a.y - by * merc(LAT[0]);
      return;
    }
    // antes de que el mapa esté listo: encajar la isla en el hueco libre
    const aw = Math.max(50, W - p.left - p.right), ah = Math.max(50, H - p.top - p.bottom);
    const m0 = merc(LAT[0]), m1 = merc(LAT[1]), lonRad = ((LON[1] - LON[0]) * Math.PI) / 180;
    const s = Math.min(aw / lonRad, ah / (m1 - m0));
    bx = (s * Math.PI) / 180; by = -s;
    ax = p.left + (aw - s * lonRad) / 2 - bx * LON[0];
    ay = p.top + (ah - s * (m1 - m0)) / 2 + s * m1;
  };
  const geom = () => { size(); camera(); };
  const X = (lon: number) => ax + bx * lon;
  const Y = (lat: number) => ay + by * merc(lat);
  // Lo fijo se calcula una vez: la Mercator de cada muestra (base y cresta)
  const baseM = rel.filas.map((f) => merc(f.lat));
  const topM = rel.filas.map((f) => f.z.map((z) => merc(f.lat + z * K)));
  // Colores ya resueltos cuando no hay transición (arrastrar no recalcula cadenas)
  let still: string[] | null = null;
  const target = (k: number): RGBA => {
    if (k < 0 || !R.incluida[k]) return OUT;
    const c = o.color(k) ?? OUT;
    const d = o.dim(k);
    return d === null ? c : d ? [c[0], c[1], c[2], c[3] * 0.22] : [c[0], c[1], c[2], Math.max(c[3], 0.95)];
  };
  const mix = (a: RGBA, b: RGBA, t: number): RGBA => (t >= 1 ? b : t <= 0 ? a : [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t, a[3] + (b[3] - a[3]) * t]);
  const css = (c: RGBA) => `rgba(${c[0] | 0},${c[1] | 0},${c[2] | 0},${c[3].toFixed(3)})`;

  const paint = (now: number) => {
    const ground = getComputedStyle(host).getPropertyValue("--ground").trim() || "#0c0d0f";
    g.fillStyle = ground; g.fillRect(0, 0, W, H);
    const lw = W < 600 ? 0.8 : 1.1, n = rel.filas.length;
    let busy = false;
    g.lineJoin = "round"; g.lineCap = "round"; g.lineWidth = lw;
    rel.filas.forEach((f, r) => {
      const t = (now - t0 - (r / n) * SWEEP) / FADE;
      if (t < 1) busy = true;
      const zs = f.z, base = ay + by * baseM[r], tm = topM[r], off = r * rel.nlon;
      const col = (q: number) => (still && t >= 1 ? still[off + q] : css(mix(prev[off + q] ?? OUT, next[off + q], t)));
      // tramos de tierra contiguos: se rellena debajo con el fondo para tapar las filas de atrás
      let i = 0;
      while (i < zs.length) {
        if (!zs[i]) { i++; continue; }
        let j = i; while (j < zs.length && zs[j]) j++;
        const a = Math.max(0, i - 1), b = Math.min(zs.length - 1, j);
        g.beginPath(); g.moveTo(X(lons[a]), base + 1.5);
        for (let s = a; s <= b; s++) g.lineTo(ax + bx * lons[s], ay + by * tm[s]);
        g.lineTo(X(lons[b]), base + 1.5); g.closePath();
        g.fillStyle = ground; g.fill();
        // la línea, en carreras del mismo color
        let s = a;
        while (s < b) {
          const c0 = col(s);
          let e = s + 1;
          while (e < b && col(e) === c0) e++;
          g.beginPath(); g.moveTo(ax + bx * lons[s], ay + by * tm[s]);
          for (let q = s + 1; q <= e; q++) g.lineTo(ax + bx * lons[q], ay + by * tm[q]);
          g.strokeStyle = c0; g.stroke();
          s = e;
        }
        i = j;
      }
    });
    // la cuenca del Yuna, elevada sobre el relieve, y la presa de Hatillo
    const ink = getComputedStyle(host).getPropertyValue("--text").trim() || "#f2f2f2", muted = getComputedStyle(host).getPropertyValue("--muted").trim() || "#9a9ea6";
    g.setLineDash([4, 3]); g.lineWidth = 1.2; g.strokeStyle = ink; g.beginPath();
    rel.yuna.forEach(([x, y, z], i) => (i ? g.lineTo(X(x), Y(y + z * K)) : g.moveTo(X(x), Y(y + z * K))));
    g.stroke(); g.setLineDash([]);
    const h = rel.hatillo, hx = X(h.lon), hy = Y(h.lat + h.z * K);
    g.fillStyle = "#E69F00"; g.beginPath(); g.moveTo(hx - 5, hy - 7); g.lineTo(hx + 5, hy - 7); g.lineTo(hx, hy + 1); g.closePath(); g.fill();
    g.font = "500 13px Inter, system-ui, sans-serif"; g.textBaseline = "middle";
    const east = rel.yuna.reduce((m, p) => (p[0] > m[0] ? p : m), rel.yuna[0]);
    const label = (txt: string, x: number, y: number, col: string) => {
      const w = g.measureText(txt).width;
      g.fillStyle = ground; g.fillRect(x - 3, y - 9, w + 6, 18);
      g.fillStyle = col; g.fillText(txt, x, y);
    };
    if (W >= 520) {
      label(o.labels.yuna, X(east[0]) + 10, Y(east[1] + east[2] * K) - 14, ink);
      label(o.labels.hatillo, hx + 10, hy + 12, "#E69F00");
      // barra de escala vertical: 1000 m
      const sx0 = X(-68.55), sy0 = Y(17.75), sy1 = Y(17.75 + 1000 * K);
      g.strokeStyle = ink; g.lineWidth = 1.2; g.beginPath(); g.moveTo(sx0, sy0); g.lineTo(sx0, sy1); g.stroke();
      label(o.labels.scale, sx0 - 10 - g.measureText(o.labels.scale).width, (sy0 + sy1) / 2, muted);
    }
    g.font = "12px Inter, system-ui, sans-serif";
    const cw = g.measureText(o.labels.credit).width;
    label(o.labels.credit, Math.max(8, W - o.pad().right - cw), W < 600 ? o.pad().top - 2 : H - o.pad().bottom + 24, muted);
    if (busy) raf = requestAnimationFrame(paint);
    else if (!still) { prev = next; still = next.map(css); }
  };

  const draw = (anim: boolean) => {
    if (!on) return;
    cancelAnimationFrame(raf);
    const cur = next;
    next = cellIdx.flatMap((row) => row.map(target));
    still = null;
    prev = anim && cur.length ? cur : next;
    t0 = performance.now() - (anim && cur.length ? 0 : SWEEP + FADE);
    geom();
    raf = requestAnimationFrame(paint);
  };

  /** Celda bajo un punto del contenedor (la fila de crestas más cercana por debajo). */
  const cellAtPoint = (x: number, y: number) => {
    const lon = (x - ax) / bx, lat = unmerc((y - ay) / by);
    // la fila más cercana por debajo del cursor (las crestas suben sobre su línea base)
    const f = rel.filas.find((row) => row.lat <= lat + rel.paso_lat * 0.5) ?? rel.filas[rel.filas.length - 1];
    const k = cellAt(R, lon, f.lat);
    return k >= 0 && R.incluida[k] ? k : -1;
  };
  // El lienzo no recibe el puntero: arrastrar, la rueda y el pellizco llegan al mapa, y las crestas lo siguen
  const reframe = () => { if (!on) return; camera(); cancelAnimationFrame(raf); paint(performance.now()); };
  const ro = new ResizeObserver(() => { if (on) { geom(); cancelAnimationFrame(raf); paint(performance.now()); } });
  ro.observe(host);

  return {
    show(v: boolean) { on = v; cv.hidden = !v; if (v) draw(false); else cancelAnimationFrame(raf); },
    draw,
    reframe,
    cellAtPoint,
    describe(text: string) { cv.setAttribute("aria-label", text); },
    destroy() { cancelAnimationFrame(raf); ro.disconnect(); cv.remove(); },
  };
}
