// Los ciclones de República Dominicana, lugar por lugar: se elige un lugar (la cuenca del Yuna con sus inundaciones,
// todo el país o cualquiera de las 32 provincias) y aparecen todas las tormentas que pasaron a menos de 200 km entre
// 2001 y 2024 (IBTrACS), con el primer pronóstico oficial del NHC que la anunciaba (a-deck, tal como se emitió) y una
// cuenta atrás hasta su llegada. Capas: viento ERA5 con partículas (las tormentas que lo tienen descargado), lluvia
// NASA IMERG y la imagen real NASA MODIS del día (NASA GIBS). Se reproduce solo al abrir.
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { load } from "../data";
import { esc, LL } from "../tendencias/datos";
import { openMenu } from "../tendencias/menu";
import { getLang } from "../i18n";
import "./huracanes.css";

interface Pt { t: string; lat: number; lon: number; kt: number | null; hpa?: number | null }
interface FcPt { tau: number; lat: number; lon: number; kt?: number | null; hpa?: number | null }
interface Wind { lon0: number; lat0: number; step: number; nx: number; ny: number; frames: { t: string; u: (number | null)[]; v: (number | null)[] }[] }
interface Flood { id: string; name: string; year: number; onset: string; lead_h: number | null; track: Pt[]; forecast: { issued: string; pts: FcPt[] } | null; wind: Wind }
interface FloodIndex { yuna: { lat: number; lon: number }; r_km: number; storms: { id: string; name: string; year: number; onset: string; lead_h: number | null }[] }
type Tr = [string, number, number, number | null, number | null];
interface RdStorm { sid: string; name: string; year: number; peak_kt: number | null; wind: string | null; track: Tr[] }
interface Hit { sid: string; dmin_km: number; arrive: string; kt_closest: number | null; lead_h: number | null; issued: string | null; fc: [number, number, number, number | null][] | null }
interface Rd { r_km: number; provinces: { id: string; name: string; lat: number; lon: number }[]; storms: RdStorm[]; hits: Record<string, Hit[]> }
interface Case { key: string; name: string; year: number; track: Pt[]; forecast: { issued: string; pts: FcPt[] } | null; wind: Wind | null; lead_h: number | null; target: { lat: number; lon: number; label: string }; goal: number; flood: boolean; t0: number; t1: number }

const HOUR = 3600000;
// La antelación se cuenta desde la PUBLICACIÓN del boletín del NHC, unas 3 h después de su hora base (la que trae el
// a-deck). Los datos guardan la hora base; aquí se resta para mostrar lo que un técnico habría tenido en la mano.
const PUB = 3;
const pubLead = (h: number | null) => (h === null ? null : h - PUB);
const STOPS: [number, [number, number, number]][] = [[0, [24, 40, 92]], [6, [32, 104, 160]], [12, [44, 168, 148]], [17, [226, 206, 74]], [25, [244, 140, 52]], [33, [226, 58, 54]], [45, [176, 34, 140]]];
const ramp = (s: number) => {
  for (let i = 1; i < STOPS.length; i++) if (s <= STOPS[i][0]) {
    const [a, ca] = STOPS[i - 1], [b, cb] = STOPS[i], k = (s - a) / (b - a);
    return ca.map((c, j) => Math.round(c + (cb[j] - c) * k)) as [number, number, number];
  }
  return STOPS[STOPS.length - 1][1];
};
// Categoría por viento sostenido (nudos), como en el rastreador de huracanes
const CAT = (kt: number | null | undefined) => kt == null ? "#8a9099" : kt < 34 ? "#8fd3ff" : kt < 64 ? "#30d1c5" : kt < 83 ? "#ffe066" : kt < 96 ? "#ffb347" : kt < 113 ? "#ff6b35" : kt < 137 ? "#ff3b5c" : "#d33ad3";
const CAT_L = (kt: number | null | undefined) => kt == null ? "" : kt < 34 ? LL("depresión", "depression") : kt < 64 ? LL("tormenta", "storm") : `${LL("huracán", "hurricane")} ${kt < 83 ? 1 : kt < 96 ? 2 : kt < 113 ? 3 : kt < 137 ? 4 : 5}`;
const IMERG = (day: string) => `https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/IMERG_Precipitation_Rate/default/${day}/GoogleMapsCompatible_Level6/{z}/{y}/{x}.png`;
const GIBS = (day: string) => `https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/MODIS_Terra_CorrectedReflectance_TrueColor/default/${day}/GoogleMapsCompatible_Level9/{z}/{y}/{x}.jpg`;
type Layer = "wind" | "rain" | "sat";
const circle = (lat: number, lon: number, km: number) => {
  const pts: [number, number][] = [];
  for (let i = 0; i <= 96; i++) {
    const a = (i / 96) * 2 * Math.PI, dy = (km / 111.2) * Math.cos(a), dx = (km / (111.2 * Math.cos((lat * Math.PI) / 180))) * Math.sin(a);
    pts.push([lon + dx, lat + dy]);
  }
  return pts;
};
const toPt = (r: Tr): Pt => ({ t: r[0], lat: r[1], lon: r[2], kt: r[3], hpa: r[4] });

export interface CyInfo { place: string; label: string; n: number; med: number | null; late: number; none: number; yuna: boolean }
// `list`: si se da, las tormentas se listan ahí (un panel lateral) en vez de en la fila de abajo
export function hurricanes(host: HTMLElement, opts: { place?: string; hidePlace?: boolean; onInfo?: (i: CyInfo) => void; list?: HTMLElement | null } = {}) {
  let alive = true, raf = 0, map: maplibregl.Map | null = null, fi: FloodIndex | null = null, rd: Rd | null = null;
  let cs: Case | null = null, place = opts.place ?? "yuna", layer: Layer = "wind", satDay = "", autoRain = false;
  let t = 0, playing = !matchMedia("(prefers-reduced-motion: reduce)").matches, last = 0;
  const floods: Record<string, Flood> = {};
  host.innerHTML = `<div class="hx ${opts.hidePlace ? "no-place" : ""} ${opts.list ? "ext-list" : ""}">
    <div class="hx-map" id="hx-map"></div>
    <canvas class="hx-wind" id="hx-wind" aria-hidden="true"></canvas>
    <div class="hx-layers" role="radiogroup" aria-label="${esc(LL("Capa", "Layer"))}">
      <button data-layer="wind" role="radio" aria-checked="true"><span>${esc(LL("Viento", "Wind"))}</span><i class="hx-th th-wind"></i></button>
      <button data-layer="rain" role="radio" aria-checked="false"><span>${esc(LL("Lluvia NASA", "NASA rain"))}</span><i class="hx-th th-rain"></i></button>
      <button data-layer="sat" role="radio" aria-checked="false"><span>${esc(LL("Satélite NASA", "NASA satellite"))}</span><i class="hx-th th-sat"></i></button>
    </div>
    <div class="hx-top">
      <p class="hx-name" id="hx-name"></p>
      <p class="hx-count" id="hx-count"></p>
      <p class="hx-now" id="hx-now"></p>
    </div>
    <div class="hx-bottom">
      <div class="hx-row">
        <button class="hx-place" id="hx-place" aria-haspopup="listbox" aria-expanded="false"><span>${esc(LL("Lugar", "Place"))}</span><b id="hx-place-l"></b><svg viewBox="0 0 12 12" aria-hidden="true"><path d="M3 4.5l3 3 3-3" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg></button>
        <div class="hx-pick" id="hx-pick" role="radiogroup" aria-label="${esc(LL("Tormenta", "Storm"))}"></div>
      </div>
      <div class="hx-time">
        <button class="hx-play" id="hx-play" aria-label="${esc(LL("Reproducir o pausar", "Play or pause"))}"></button>
        <div class="hx-tl" id="hx-tl">
          <div class="hx-marks" id="hx-marks"></div>
          <div class="hx-track" id="hx-bar"><i class="hx-fill" id="hx-fill"></i><b class="hx-bub" id="hx-bub"></b></div>
          <div class="hx-days" id="hx-days"></div>
        </div>
      </div>
      <div class="hx-key" id="hx-key"></div>
    </div>
  </div>`;
  const $ = (id: string) => host.querySelector<HTMLElement>(`#${id}`)!;
  const cv = $("hx-wind") as HTMLCanvasElement, g = cv.getContext("2d")!;
  const field = document.createElement("canvas");
  let targetLab: maplibregl.Marker | null = null;

  const keys: Record<Layer, string> = {
    wind: `<span>${esc(LL("Viento a 10 m · ERA5", "10 m wind · ERA5"))}</span><i class="hx-ramp r-wind"></i><span class="hx-ticks"><em>0</em><em>17 ${esc(LL("tormenta", "storm"))}</em><em>33 ${esc(LL("huracán", "hurricane"))}</em><em>m/s</em></span>`,
    rain: `<span>${esc(LL("Lluvia · NASA GPM IMERG, tasa del día", "Rain · NASA GPM IMERG, daily rate"))}</span><i class="hx-ramp r-rain"></i><span class="hx-ticks"><em>${esc(LL("poca", "light"))}</em><em>${esc(LL("mucha", "heavy"))}</em></span>`,
    sat: `<span>${esc(LL("NASA MODIS Terra, color real, imagen del día · franjas negras: entre dos pasadas", "NASA MODIS Terra, true colour, image of the day · black stripes: between two passes"))}</span>`,
  };
  const cats = `<span class="hx-cats">${[20, 50, 70, 90, 100, 120, 140].map((k) => `<em style="--k:${CAT(k)}">${esc(CAT_L(k))}</em>`).join("")}</span>`;
  const setKey = () => { $("hx-key").innerHTML = keys[layer] + (opts.list ? "" : cats); };
  setKey();
  const dayFmt = (ms: number) => new Date(ms).toLocaleString(getLang() === "es" ? "es-DO" : "en-US", { timeZone: "America/Santo_Domingo", weekday: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
  const metr = (kt?: number | null, hpa?: number | null) => [kt != null ? `${kt} kt` : "", hpa ? `${hpa} hPa` : ""].filter(Boolean).join(" | ");
  const placeName = (p: string) => p === "yuna" ? LL("Cuenca del Yuna", "Yuna basin") : p === "DO" ? LL("Todo el país", "Whole country") : rd?.provinces.find((x) => x.id === p)?.name ?? p;

  // ── Viento interpolado en el tiempo y en el espacio ──
  let fA = 0, fB = 0, fk = 0;
  const W = () => cs?.wind ?? null;
  const setFrame = () => {
    const w = W(); if (!w) return;
    const ts = w.frames.map((f) => Date.parse(f.t));
    let i = 0; while (i < ts.length - 2 && ts[i + 1] <= t) i++;
    fA = i; fB = Math.min(i + 1, ts.length - 1); fk = ts[fB] > ts[fA] ? Math.max(0, Math.min(1, (t - ts[fA]) / (ts[fB] - ts[fA]))) : 0;
  };
  const uv = (lon: number, lat: number): [number, number] | null => {
    const w = W(); if (!w) return null;
    const x = (lon - w.lon0) / w.step, y = (lat - w.lat0) / w.step;
    if (x < 0 || y < 0 || x >= w.nx - 1 || y >= w.ny - 1) return null;
    const i = Math.floor(x), j = Math.floor(y), dx = x - i, dy = y - j, A = w.frames[fA], B = w.frames[fB];
    const at = (arr: (number | null)[], ii: number, jj: number) => arr[jj * w.nx + ii] ?? 0;
    const bil = (arr: (number | null)[]) => at(arr, i, j) * (1 - dx) * (1 - dy) + at(arr, i + 1, j) * dx * (1 - dy) + at(arr, i, j + 1) * (1 - dx) * dy + at(arr, i + 1, j + 1) * dx * dy;
    return [bil(A.u) * (1 - fk) + bil(B.u) * fk, bil(A.v) * (1 - fk) + bil(B.v) * fk];
  };
  const paintField = () => {
    const w = W(); if (!w) return;
    field.width = w.nx; field.height = w.ny;
    const fg = field.getContext("2d")!, img = fg.createImageData(w.nx, w.ny), A = w.frames[fA], B = w.frames[fB];
    for (let j = 0; j < w.ny; j++) for (let i = 0; i < w.nx; i++) {
      const k = j * w.nx + i, o = ((w.ny - 1 - j) * w.nx + i) * 4;
      const u = (A.u[k] ?? 0) * (1 - fk) + (B.u[k] ?? 0) * fk, v = (A.v[k] ?? 0) * (1 - fk) + (B.v[k] ?? 0) * fk;
      const [r, gg, b] = ramp(Math.hypot(u, v));
      // el borde de la rejilla se desvanece: sin rectángulo cortado sobre el mapa
      const edge = Math.min(i, j, w.nx - 1 - i, w.ny - 1 - j), fade = Math.min(1, edge / 6);
      img.data[o] = r; img.data[o + 1] = gg; img.data[o + 2] = b; img.data[o + 3] = Math.round(175 * fade);
    }
    fg.putImageData(img, 0, 0);
    (map?.getSource("field") as maplibregl.CanvasSource | undefined)?.play();
  };

  const N = Math.min(1100, Math.round((innerWidth * 700) / 1440));
  let P: { lon: number; lat: number; age: number }[] = [];
  const seed = () => { const w = W()!; return { lon: w.lon0 + Math.random() * (w.nx - 1) * w.step, lat: w.lat0 + Math.random() * (w.ny - 1) * w.step, age: Math.random() * 80 }; };
  const resize = () => { const r = host.querySelector(".hx")!.getBoundingClientRect(), d = Math.min(2, devicePixelRatio || 1); cv.width = r.width * d; cv.height = r.height * d; cv.style.width = `${r.width}px`; cv.style.height = `${r.height}px`; g.setTransform(d, 0, 0, d, 0, 0); };
  const clearTrails = () => g.clearRect(0, 0, cv.width, cv.height);

  const stormPos = () => {
    const tr = cs!.track; if (!tr.length) return null;
    const ts = tr.map((p) => Date.parse(p.t));
    if (t <= ts[0]) return tr[0]; if (t >= ts[ts.length - 1]) return tr[tr.length - 1];
    let i = 0; while (ts[i + 1] < t) i++;
    const k = (t - ts[i]) / (ts[i + 1] - ts[i]), a = tr[i], b = tr[i + 1];
    return { t: "", lat: a.lat + (b.lat - a.lat) * k, lon: a.lon + (b.lon - a.lon) * k, kt: a.kt };
  };

  // ── Etiquetas del rastreador ──
  let labs: { m: maplibregl.Marker; at: number; kind: "obs" | "fc" }[] = [];
  const makeLabels = () => {
    labs.forEach((l) => l.m.remove()); labs = [];
    if (!map || !cs) return;
    for (const p of cs.track) {
      const at = Date.parse(p.t);
      if (p.t.slice(11, 13) !== "18" || at < cs.t0 || at > cs.t1) continue;
      const el = document.createElement("div"); el.className = "hx-lab"; el.style.setProperty("--k", CAT(p.kt));
      el.innerHTML = `<b>${esc(dayFmt(at))}</b><span>${esc(metr(p.kt, p.hpa))}</span>`;
      labs.push({ m: new maplibregl.Marker({ element: el, anchor: "bottom-left", offset: [8, -6] }).setLngLat([p.lon, p.lat]).addTo(map), at, kind: "obs" });
    }
    const fc = cs.forecast;
    if (fc) for (const p of fc.pts) {
      if (![24, 72, 120].includes(p.tau)) continue;
      const at = Date.parse(fc.issued) + p.tau * HOUR;
      const el = document.createElement("div"); el.className = "hx-lab fc";
      el.innerHTML = `<b>${esc(LL(`Pronóstico · ${dayFmt(at)}`, `Forecast · ${dayFmt(at)}`))}</b><span>${esc(metr(p.kt, p.hpa))}</span>`;
      labs.push({ m: new maplibregl.Marker({ element: el, anchor: "top-right", offset: [-8, 6] }).setLngLat([p.lon, p.lat]).addTo(map), at: Date.parse(fc.issued) + PUB * HOUR, kind: "fc" });
    }
  };

  let lastUpd = 0;
  const updateLayers = () => {
    if (!map || !cs || !map.getSource("trail")) return;
    const nowMs = performance.now(); if (nowMs - lastUpd < 70) return; lastUpd = nowMs;
    const obs = labs.filter((l) => l.kind === "obs" && l.at <= t).slice(-3);
    labs.forEach((l) => { l.m.getElement().style.display = (l.kind === "fc" ? t >= l.at : obs.includes(l)) ? "" : "none"; });
    const pos = stormPos();
    const past = cs.track.filter((p) => Date.parse(p.t) <= t).map((p) => [p.lon, p.lat]);
    if (pos) past.push([pos.lon, pos.lat]);
    (map.getSource("trail") as maplibregl.GeoJSONSource).setData({ type: "Feature", properties: {}, geometry: { type: "LineString", coordinates: past.length > 1 ? past : [[0, 0], [0, 0]] } });
    (map.getSource("pts") as maplibregl.GeoJSONSource).setData({ type: "FeatureCollection", features: cs.track.filter((p) => Date.parse(p.t) <= t && ["00", "06", "12", "18"].includes(p.t.slice(11, 13))).map((p) => ({ type: "Feature" as const, properties: { c: CAT(p.kt) }, geometry: { type: "Point" as const, coordinates: [p.lon, p.lat] } })) });
    const day = new Date(t).toISOString().slice(0, 10);
    if (layer !== "wind" && day !== satDay) { satDay = day; (map.getSource("sat") as maplibregl.RasterTileSource).setTiles([layer === "rain" ? IMERG(day) : GIBS(day)]); }
    (map.getSource("eye") as maplibregl.GeoJSONSource).setData({ type: "FeatureCollection", features: pos ? [{ type: "Feature", properties: {}, geometry: { type: "Point", coordinates: [pos.lon, pos.lat] } }] : [] });
    const fc = cs.forecast, shown = !!fc && t >= Date.parse(fc.issued) + PUB * HOUR;
    $("hx-marks").querySelector(".nhc")?.classList.toggle("on", shown);
    map.setLayoutProperty("fc", "visibility", shown ? "visible" : "none");
    map.setLayoutProperty("fc-pts", "visibility", shown ? "visible" : "none");
    const now = cs.track.filter((p) => Date.parse(p.t) <= t).pop();
    $("hx-now").innerHTML = now ? `<b style="color:${CAT(now.kt)}">${esc(CAT_L(now.kt))}</b> ${esc(metr(now.kt, now.hpa))}` : "";
    const h = Math.round((cs.goal - t) / HOUR), L = cs.target.label;
    $("hx-count").textContent = cs.flood
      ? (h > 0 ? LL(`Faltan ${h} h para la inundación`, `${h} h to the flood`) : LL(`Inundación en curso`, `Flood under way`))
      : (h > 0 ? LL(`Llega a ${L} en ${h} h`, `Reaches ${L} in ${h} h`) : LL(`A menos de 200 km de ${L}`, `Within 200 km of ${L}`));
    $("hx-count").classList.toggle("on", h <= 0);
    const f = (t - cs.t0) / (cs.t1 - cs.t0);
    $("hx-fill").style.transform = `scaleX(${f})`;
    const bub = $("hx-bub"); bub.textContent = dayFmt(t); bub.style.left = `${f * 100}%`;
  };

  const tick = (now: number) => {
    if (!alive) return;
    raf = requestAnimationFrame(tick);
    if (!cs || !map) return;
    const dt = Math.min(64, now - (last || now)); last = now;
    if (playing) { t += dt * 1.0 * HOUR / 100; if (t > cs.t1) { t = cs.t0; clearTrails(); } }
    g.save(); g.globalCompositeOperation = "destination-in"; g.fillStyle = "rgba(0,0,0,.86)"; g.fillRect(0, 0, cv.width, cv.height); g.restore();
    if (cs.wind && layer === "wind") {
      const pA = fA, pB = fB, pK = fk; setFrame();
      if (pA !== fA || pB !== fB || Math.abs(pK - fk) > 0.08) paintField();
      g.lineWidth = 1; g.strokeStyle = "rgba(255,255,255,.42)"; g.beginPath();
      const k = 0.0006 / Math.pow(2, map.getZoom() - 4.6);
      for (const p of P) {
        const w = uv(p.lon, p.lat);
        if (!w || p.age-- < 0) { Object.assign(p, seed(), { age: 40 + Math.random() * 60 }); continue; }
        const a = map.project([p.lon, p.lat]);
        p.lon += w[0] * k * 6 / Math.cos((p.lat * Math.PI) / 180); p.lat += w[1] * k * 6;
        const b = map.project([p.lon, p.lat]);
        g.moveTo(a.x, a.y); g.lineTo(b.x, b.y);
      }
      g.stroke();
    }
    updateLayers();
  };

  const applyLayer = () => {
    if (!map) return;
    if (layer === "wind" && !cs?.wind) { layer = "rain"; autoRain = true; }
    else if (autoRain && cs?.wind && layer === "rain") { layer = "wind"; autoRain = false; }
    host.querySelectorAll<HTMLButtonElement>("[data-layer]").forEach((x) => {
      x.setAttribute("aria-checked", String(x.dataset.layer === layer));
      if (x.dataset.layer === "wind") { x.disabled = !cs?.wind; x.title = cs?.wind ? "" : LL("Viento ERA5 descargado solo para las tormentas que inundaron el Yuna", "ERA5 wind downloaded only for the storms that flooded the Yuna"); }
    });
    satDay = "";
    map.setLayoutProperty("sat", "visibility", layer === "wind" ? "none" : "visible");
    map.setLayoutProperty("field", "visibility", layer === "wind" ? "visible" : "none");
    map.setPaintProperty("sat", "raster-opacity", layer === "rain" ? 0.9 : 1);
    if (layer !== "wind") clearTrails();
    setKey();
  };

  // ── Un caso: tormenta + lugar ──
  const show = async (c: Case) => {
    cs = c;
    if (!alive || !map) return;
    t = c.t0; clearTrails();
    if (c.wind) {
      setFrame(); paintField(); P = Array.from({ length: N }, seed);
      const w = c.wind;
      (map.getSource("field") as maplibregl.CanvasSource).setCoordinates([[w.lon0 - w.step / 2, w.lat0 + (w.ny - .5) * w.step], [w.lon0 + (w.nx - .5) * w.step, w.lat0 + (w.ny - .5) * w.step], [w.lon0 + (w.nx - .5) * w.step, w.lat0 - w.step / 2], [w.lon0 - w.step / 2, w.lat0 - w.step / 2]]);
    }
    // Con viento, el mapa se queda dentro de la rejilla medida: nunca se ve el borde sin datos
    if (c.wind) {
      const w = c.wind, b: [[number, number], [number, number]] = [[w.lon0 + w.step * 2, w.lat0 + w.step * 2], [w.lon0 + (w.nx - 3) * w.step, w.lat0 + (w.ny - 3) * w.step]];
      map.setMaxBounds(null); map.setMinZoom(0);
      const c0 = map.getCanvas(), Wc = c0.clientWidth, Hc = c0.clientHeight;
      const a = map.project(b[0]), bb = map.project(b[1]), pw = Math.abs(bb.x - a.x), ph = Math.abs(bb.y - a.y);
      const zCover = map.getZoom() + Math.log2(Math.max(Wc / pw, Hc / ph));
      map.setMinZoom(zCover); map.setMaxBounds(b);
      map.jumpTo({ center: [(b[0][0] + b[1][0]) / 2, (b[0][1] + b[1][1]) / 2], zoom: zCover + 0.2 });
    } else { map.setMaxBounds(null); map.setMinZoom(0); }
    applyLayer();
    (map.getSource("path") as maplibregl.GeoJSONSource).setData({ type: "Feature", properties: {}, geometry: { type: "LineString", coordinates: c.track.map((p) => [p.lon, p.lat]) } });
    const fc = c.forecast;
    (map.getSource("fc") as maplibregl.GeoJSONSource).setData({ type: "FeatureCollection", features: fc ? [
      { type: "Feature", properties: {}, geometry: { type: "LineString", coordinates: fc.pts.map((p) => [p.lon, p.lat]) } },
      ...fc.pts.filter((p) => p.tau % 24 === 0 && p.tau > 0).map((p) => ({ type: "Feature" as const, properties: {}, geometry: { type: "Point" as const, coordinates: [p.lon, p.lat] } })),
    ] : [] });
    (map.getSource("target") as maplibregl.GeoJSONSource).setData({ type: "Feature", properties: {}, geometry: { type: "Polygon", coordinates: [circle(c.target.lat, c.target.lon, 200)] } });
    const el = targetLab?.getElement(); if (el) el.textContent = `${c.target.label} · 200 km`;
    targetLab?.setLngLat([c.target.lon + 2.0, c.target.lat - 1.2]);
    const span = c.t1 - c.t0, pos = (ms: number) => ((ms - c.t0) / span) * 100;
    const loc = (ms: number) => new Date(ms - 4 * HOUR);  // hora de RD (UTC−4, sin horario de verano)
    const days: string[] = [];
    let d0 = Date.UTC(loc(c.t0).getUTCFullYear(), loc(c.t0).getUTCMonth(), loc(c.t0).getUTCDate()) + 4 * HOUR;
    for (let d = d0; d < c.t1; d += 24 * HOUR) {
      const a = Math.max(d, c.t0), b = Math.min(d + 24 * HOUR, c.t1); if (b - a < 10 * HOUR) continue;
      const lab = new Date(d + 12 * HOUR).toLocaleDateString(getLang() === "es" ? "es-DO" : "en-US", { timeZone: "America/Santo_Domingo", weekday: "short", day: "numeric" });
      days.push(`<span style="left:${pos(a)}%;width:${pos(b) - pos(a)}%">${esc(lab)}</span>`);
    }
    const my = new Date(c.t0).toLocaleDateString(getLang() === "es" ? "es-DO" : "en-US", { timeZone: "America/Santo_Domingo", month: "long", year: "numeric" });
    $("hx-days").innerHTML = `<em>${esc(my)}</em>${days.join("")}`;
    const marks: string[] = [];
    if (c.forecast) {
      const at = Date.parse(c.forecast.issued) + PUB * HOUR;
      const txt = c.lead_h !== null && c.lead_h < 0 ? LL(`Boletín NHC · ${-c.lead_h} h tarde`, `NHC advisory · ${-c.lead_h} h late`) : LL(`Boletín NHC publicado · ${c.lead_h} h antes`, `NHC advisory published · ${c.lead_h} h ahead`);
      // la etiqueta del aviso se abre hacia el lado contrario a la llegada, para no pisarse
      const side = (at <= c.goal ? pos(at) > 22 : pos(at) > 78) ? "l" : "r";
      if (at >= c.t0 && at <= c.t1) marks.push(`<i class="mk nhc ${side}" style="left:${pos(at)}%"><span>${esc(txt)}</span></i>`);
    }
    if (c.goal >= c.t0 && c.goal <= c.t1) marks.push(`<i class="mk goal ${pos(c.goal) > 70 ? "l" : "r"}" style="left:${pos(c.goal)}%"><span>${esc(c.flood ? LL("Inundación", "Flood") : LL(`Llega a ${c.target.label}`, `Reaches ${c.target.label}`))}</span></i>`);
    $("hx-marks").innerHTML = marks.join("");
    $("hx-name").innerHTML = `<b>${esc(c.name)}</b> ${c.year}${c.forecast ? "" : ` · <em>${esc(LL(`el NHC no la pronosticó a menos de 200 km de ${c.target.label}`, `NHC never forecast it within 200 km of ${c.target.label}`))}</em>`}`;
    lastUpd = 0; makeLabels();
  };
  const floodCase = async (id: string): Promise<Case> => {
    const f = floods[id] ??= await load<Flood>(`huracanes/${id}.json`);
    const F = f.wind.frames;
    return { key: id, name: f.name, year: f.year, track: f.track, forecast: f.forecast, wind: f.wind, lead_h: pubLead(f.lead_h),
      target: { lat: fi!.yuna.lat, lon: fi!.yuna.lon, label: LL("Cuenca del Yuna", "Yuna basin") }, goal: Date.parse(`${f.onset}T04:00:00Z`), flood: true,
      t0: Date.parse(F[0].t), t1: Date.parse(F[F.length - 1].t) };
  };
  const placeCase = async (h: Hit, p: string): Promise<Case> => {
    const s = rd!.storms.find((x) => x.sid === h.sid)!;
    // en «todo el país», la provincia de referencia es la mejor avisada para esa tormenta
    let pid = p, hit = h;
    if (p === "DO") for (const pr of rd!.provinces) { const x = rd!.hits[pr.id]?.find((y) => y.sid === h.sid && y.arrive === h.arrive && y.lead_h === h.lead_h); if (x) { pid = pr.id; hit = x; break; } }
    const pr = rd!.provinces.find((x) => x.id === pid)!;
    const wind = s.wind ? (floods[s.wind] ??= await load<Flood>(`huracanes/${s.wind}.json`)).wind : null;
    const arrive = Date.parse(hit.arrive), issued = hit.issued ? Date.parse(hit.issued) : null;
    let t0 = Math.min(arrive - 96 * HOUR, issued ? issued - 6 * HOUR : Infinity), t1 = arrive + 30 * HOUR;
    if (wind) { t0 = Math.max(t0, Date.parse(wind.frames[0].t)); t1 = Math.min(Math.max(t1, t0 + 48 * HOUR), Date.parse(wind.frames[wind.frames.length - 1].t)); }
    return { key: `${p}:${h.sid}`, name: s.name, year: s.year, track: s.track.map(toPt), wind, lead_h: pubLead(hit.lead_h),
      forecast: hit.fc && hit.issued ? { issued: hit.issued, pts: hit.fc.map(([tau, lat, lon, kt]) => ({ tau, lat, lon, kt })) } : null,
      target: { lat: pr.lat, lon: pr.lon, label: pr.name }, goal: arrive, flood: false, t0, t1 };
  };

  // ── Lugar: lista de tormentas y la maraña de todas sus trayectorias ──
  const setPlace = async (p: string) => {
    place = p; $("hx-place-l").textContent = placeName(p);
    type Row = { key: string; name: string; year: number; lead: number | null; k: string | null };
    let rows: Row[] = [], tracks: RdStorm[] = [];
    if (p === "yuna") {
      rows = fi!.storms.map((s) => ({ key: s.id, name: s.name, year: s.year, lead: pubLead(s.lead_h), k: null }));
      tracks = rd!.storms.filter((s) => fi!.storms.some((o) => o.name.toUpperCase() === s.name.toUpperCase() && o.year === s.year));
    } else {
      const hs = rd!.hits[p] ?? [];
      rows = hs.map((h) => { const s = rd!.storms.find((x) => x.sid === h.sid)!; return { key: h.sid, name: s.name, year: s.year, lead: pubLead(h.lead_h), k: CAT(s.peak_kt) }; });
      tracks = hs.map((h) => rd!.storms.find((x) => x.sid === h.sid)!);
    }
    rows.sort((a, b) => (b.lead ?? -999) - (a.lead ?? -999));
    const leadTxt = (l: number | null) => l === null ? LL("sin aviso", "no advisory") : l < 0 ? LL("aviso tarde", "late advisory") : `${l} h`;
    const empty = `<p class="hx-empty">${esc(LL("Ninguna tormenta pasó a menos de 200 km entre 2001 y 2024.", "No storm passed within 200 km between 2001 and 2024."))}</p>`;
    $("hx-pick").innerHTML = rows.length ? rows.map((r) => `<button data-hx="${esc(r.key)}" role="radio" aria-checked="false"><b${r.k ? ` style="--k:${r.k}"` : ""}>${esc(r.name)}</b><span>${r.year} · ${esc(leadTxt(r.lead))}</span></button>`).join("") : empty;
    if (opts.list) {
      // La lista lateral: cada tormenta con sus horas de aviso como un punto sobre una misma escala
      const top = Math.max(24, ...rows.map((r) => r.lead ?? 0)), x = (l: number) => Math.max(0, Math.min(100, (l / top) * 100));
      opts.list.innerHTML = `<h2 class="hxl-h">${esc(p === "yuna" ? LL("Las inundaciones, una a una", "The floods, one by one") : LL("Las tormentas, una a una", "The storms, one by one"))}</h2>
        <p class="hxl-sub">${esc(LL("Horas de aviso del NHC antes de llegar. Toca una para verla.", "Hours of NHC warning before arrival. Tap one to see it."))}</p>
        ${rows.length ? `<p class="hxl-ax" aria-hidden="true"><span>0 h</span><span>${top} h</span></p>
        <div class="hxl" role="radiogroup" aria-label="${esc(LL("Tormenta", "Storm"))}">${rows.map((r) => `<button class="hxl-r" data-hx="${esc(r.key)}" role="radio" aria-checked="false">
          <b${r.k ? ` style="--k:${r.k}"` : ""}>${esc(r.name)}</b><span class="hxl-y">${r.year}</span>
          <i class="hxl-s" aria-hidden="true">${r.lead !== null && r.lead >= 0 ? `<i style="left:${x(r.lead).toFixed(1)}%"></i>` : ""}</i>
          <em class="${r.lead === null || r.lead < 0 ? "w" : ""}">${esc(leadTxt(r.lead))}</em></button>`).join("")}</div>` : empty}`;
    }
    (map!.getSource("all") as maplibregl.GeoJSONSource).setData({ type: "FeatureCollection", features: tracks.map((s) => ({ type: "Feature" as const, properties: { c: CAT(s.peak_kt) }, geometry: { type: "LineString" as const, coordinates: s.track.map((r) => [r[2], r[1]]) } })) });
    if (opts.onInfo) {
      const leads = (p === "yuna" ? fi!.storms.map((s) => s.lead_h) : (rd!.hits[p] ?? []).map((h) => h.lead_h)).map(pubLead);
      const ok = leads.filter((x): x is number => x !== null && x >= 0).sort((a, b) => a - b);
      opts.onInfo({ place: p, label: placeName(p), n: leads.length, med: ok.length ? ok[ok.length >> 1] : null, late: leads.filter((x) => x !== null && x < 0).length, none: leads.filter((x) => x === null).length, yuna: p === "yuna" });
    }
    if (rows.length) await pickStorm(rows[0].key);
  };
  const pickStorm = async (key: string) => {
    [host, opts.list].forEach((r) => r?.querySelectorAll<HTMLButtonElement>("[data-hx]").forEach((b) => b.setAttribute("aria-checked", String(b.dataset.hx === key))));
    const c = place === "yuna" ? await floodCase(key) : await placeCase((rd!.hits[place] ?? []).find((h) => h.sid === key)!, place);
    await show(c);
  };

  const build = async () => {
    [fi, rd] = await Promise.all([load<FloodIndex>("huracanes/index.json"), load<Rd>("huracanes/rd.json")]);
    if (!alive) return;
    map = new maplibregl.Map({
      container: $("hx-map"),
      style: { version: 8, sources: {
        dark: { type: "raster", tiles: ["https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}"], tileSize: 256, maxzoom: 16, attribution: "Base: Esri · Viento: ERA5 (Copernicus) vía Open-Meteo · Lluvia y satélite: NASA GIBS (IMERG, MODIS) · Trayectorias: IBTrACS (NOAA) · Pronóstico: NHC" },
        labels: { type: "raster", tiles: ["https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Reference/MapServer/tile/{z}/{y}/{x}"], tileSize: 256, maxzoom: 16 },
        all: { type: "geojson", data: { type: "FeatureCollection", features: [] } },
        path: { type: "geojson", data: { type: "FeatureCollection", features: [] } },
        trail: { type: "geojson", data: { type: "FeatureCollection", features: [] } },
        pts: { type: "geojson", data: { type: "FeatureCollection", features: [] } },
        sat: { type: "raster", tiles: [GIBS("2017-09-20")], tileSize: 256, maxzoom: 9 },
        eye: { type: "geojson", data: { type: "FeatureCollection", features: [] } },
        fc: { type: "geojson", data: { type: "FeatureCollection", features: [] } },
        target: { type: "geojson", data: { type: "FeatureCollection", features: [] } },
      }, layers: [
        { id: "bg", type: "background", paint: { "background-color": "#07080a" } },
        { id: "dark", type: "raster", source: "dark" },
        { id: "sat", type: "raster", source: "sat", layout: { visibility: "none" }, paint: { "raster-fade-duration": 300 } },
        { id: "labels", type: "raster", source: "labels", paint: { "raster-opacity": 0.9 } },
        { id: "all", type: "line", source: "all", paint: { "line-color": ["get", "c"], "line-opacity": 0.22, "line-width": 1.2 }, layout: { "line-cap": "round", "line-join": "round" } },
        { id: "target", type: "line", source: "target", paint: { "line-color": "#ff9f0a", "line-width": 2, "line-dasharray": [2, 2] } },
        { id: "path", type: "line", source: "path", paint: { "line-color": "#ffffff", "line-opacity": 0.3, "line-width": 2 }, layout: { "line-cap": "round" } },
        { id: "trail", type: "line", source: "trail", paint: { "line-color": "#ffffff", "line-width": 3.5 }, layout: { "line-cap": "round", "line-join": "round" } },
        { id: "fc", type: "line", source: "fc", filter: ["==", ["geometry-type"], "LineString"], paint: { "line-color": "#ffffff", "line-opacity": 0.92, "line-width": 3, "line-dasharray": [1.4, 1.6] }, layout: { "line-cap": "round", visibility: "none" } },
        { id: "fc-pts", type: "circle", source: "fc", filter: ["==", ["geometry-type"], "Point"], layout: { visibility: "none" }, paint: { "circle-radius": 5, "circle-color": "#ffffff", "circle-stroke-color": "#ff3b30", "circle-stroke-width": 2.5 } },
        { id: "pts", type: "circle", source: "pts", paint: { "circle-radius": 4, "circle-color": ["get", "c"], "circle-stroke-color": "#07080a", "circle-stroke-width": 1 } },
        { id: "eye-halo", type: "circle", source: "eye", paint: { "circle-radius": 15, "circle-color": "#ff3b30", "circle-opacity": 0.22, "circle-stroke-color": "#ffffff", "circle-stroke-width": 2 } },
        { id: "eye", type: "circle", source: "eye", paint: { "circle-radius": 6, "circle-color": "#ff3b30", "circle-stroke-color": "#ffffff", "circle-stroke-width": 2 } },
      ] },
      center: [-70.2, 19.4], zoom: innerWidth < 760 ? 3.9 : 4.6, attributionControl: { compact: true }, cooperativeGestures: true,
    });
    map.on("load", async () => {
      resize();
      map!.addSource("field", { type: "canvas", canvas: field, animate: false, coordinates: [[-80, 27], [-60, 27], [-60, 13], [-80, 13]] } as unknown as maplibregl.SourceSpecification);
      map!.addLayer({ id: "field", type: "raster", source: "field", paint: { "raster-opacity": 0.78, "raster-resampling": "linear", "raster-fade-duration": 0 } } as maplibregl.LayerSpecification, "labels");
      const lab = document.createElement("div"); lab.className = "hx-yuna";
      targetLab = new maplibregl.Marker({ element: lab, anchor: "left" }).setLngLat([-68, 18]).addTo(map!);
      await setPlace(place);
      raf = requestAnimationFrame(tick);
    });
    host.querySelector<HTMLElement>(".th-sat")!.style.backgroundImage = `url(${GIBS("2017-09-20").replace("{z}/{y}/{x}", "3/3/2")})`;
    map.on("movestart", clearTrails);
    map.on("resize", () => { resize(); clearTrails(); });
  };

  host.addEventListener("click", (e) => {
    const el = e.target as Element;
    const lb = el.closest<HTMLButtonElement>("[data-layer]");
    if (lb && map && !lb.disabled) { layer = lb.dataset.layer as Layer; autoRain = false; applyLayer(); lastUpd = 0; updateLayers(); return; }
    const pb = el.closest<HTMLButtonElement>("#hx-place");
    if (pb && rd && fi) {
      const n = (p: string) => (rd!.hits[p] ?? []).length;
      const med = (p: string) => { const l = (rd!.hits[p] ?? []).map((h) => pubLead(h.lead_h)).filter((x): x is number => x !== null && x >= 0).sort((a, b) => a - b); return l.length ? l[l.length >> 1] : null; };
      const hint = (p: string) => { const m = med(p); return LL(`${n(p)} tormentas a menos de 200 km${m !== null ? ` · aviso mediano ${m} h antes` : ""}`, `${n(p)} storms within 200 km${m !== null ? ` · median advisory ${m} h ahead` : ""}`); };
      openMenu(pb, [
        { value: "yuna", label: LL("Cuenca del Yuna · inundaciones", "Yuna basin · floods"), hint: LL(`${fi.storms.length} inundaciones que llegaron con un ciclón`, `${fi.storms.length} floods that came with a cyclone`) },
        { value: "DO", label: LL("Todo el país", "Whole country"), hint: hint("DO") },
        ...rd.provinces.map((p) => ({ value: p.id, label: p.name, hint: hint(p.id) })),
      ], place, (v) => { setPlace(v); playing = true; syncPlay(); }, LL("¿Qué lugar quieres vigilar?", "Which place do you want to watch?"));
      return;
    }
    const b = el.closest<HTMLButtonElement>("[data-hx]"); if (b) { pickStorm(b.dataset.hx!); playing = true; syncPlay(); return; }
    if (el.closest("#hx-play")) { playing = !playing; syncPlay(); }
  });
  opts.list?.addEventListener("click", (e) => { const b = (e.target as Element).closest<HTMLButtonElement>("[data-hx]"); if (b) { pickStorm(b.dataset.hx!); playing = true; syncPlay(); } });
  $("hx-bar").addEventListener("pointerdown", (e) => {
    if (!cs) return;
    const r = $("hx-bar").getBoundingClientRect(); t = cs.t0 + Math.max(0, Math.min(1, (e.clientX - r.left) / r.width)) * (cs.t1 - cs.t0); clearTrails();
  });
  const syncPlay = () => { $("hx-play").innerHTML = playing ? '<svg viewBox="0 0 16 16" aria-hidden="true"><rect x="4" y="3" width="3" height="10" rx="1.2" fill="currentColor"/><rect x="9" y="3" width="3" height="10" rx="1.2" fill="currentColor"/></svg>' : '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M5 3.5v9l7.5-4.5z" fill="currentColor" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/></svg>'; };
  syncPlay();
  const io = new IntersectionObserver((es) => { if (es.some((x) => x.isIntersecting) && !map) build(); }, { rootMargin: "200px" });
  io.observe(host);
  return { setPlace(p: string) { if (p === place) return; place = p; if (map && rd && fi) { setPlace(p); playing = true; syncPlay(); } }, destroy() { labs.forEach((l) => l.m.remove()); alive = false; cancelAnimationFrame(raf); io.disconnect(); map?.remove(); map = null; } };
}
