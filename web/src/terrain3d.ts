// Escena 3D: relieve real (AWS Terrain Tiles, formato terrarium) con imagen satelital encima,
// y sobre el terreno los datos de verdad: el campo de lluvia IMERG por celda, las cajas exactas de cada zona
// y los lugares MODIS. Todo se puede girar, inclinar, acercar y tocar.
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import type { Grid } from "./field";

export interface Zone { id: string; name: string; req: number[] | null; data: number[] | null; on: boolean }
export interface Site { id: string; name: string; lat: number; lon: number; on: boolean; note?: string }

const DRY = [242, 179, 61];
const VERY_DRY = [229, 86, 111];
const WET = [142, 240, 198];
const mix = (a: number[], b: number[], t: number) => `rgb(${a.map((v, k) => Math.round(v + (b[k] - v) * t)).join(",")})`;
const ring = (b: number[]) => [[b[0], b[1]], [b[2], b[1]], [b[2], b[3]], [b[0], b[3]], [b[0], b[1]]];
let lastCam: { center: [number, number]; zoom: number; pitch: number; bearing: number } | null = null;

export function terrain3d(el: HTMLElement, opts: {
  zones: Zone[]; sites: Site[];
  onZone: (id: string) => void; onSite: (id: string) => void;
  cellLabel: (mes: string, mm: number | null, pct: number | null) => string;
  siteAction: string;
}) {
  const map = new maplibregl.Map({
    container: el,
    style: {
      version: 8,
      sources: {
        sat: { type: "raster", tiles: ["https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"], tileSize: 256, maxzoom: 17,
          attribution: "Imagen: Esri, Maxar, Earthstar Geographics" },
        dem: { type: "raster-dem", tiles: ["https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"], encoding: "terrarium", tileSize: 256, maxzoom: 13,
          attribution: "Relieve: AWS Terrain Tiles (SRTM y otras fuentes)" },
        shade: { type: "raster-dem", tiles: ["https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"], encoding: "terrarium", tileSize: 256, maxzoom: 13 },
      },
      layers: [
        { id: "bg", type: "background", paint: { "background-color": "#07080a" } },
        { id: "sat", type: "raster", source: "sat", paint: { "raster-saturation": -0.3, "raster-brightness-max": 0.78, "raster-contrast": 0.12 } },
        { id: "shade", type: "hillshade", source: "shade", paint: { "hillshade-exaggeration": 0.55, "hillshade-shadow-color": "#05070a", "hillshade-highlight-color": "#bfe8da", "hillshade-accent-color": "#0c1512" } },
      ],
      terrain: { source: "dem", exaggeration: 1.8 },
    },
    center: lastCam?.center ?? [-70.25, 18.75],
    zoom: lastCam?.zoom ?? 6.6,
    pitch: lastCam?.pitch ?? 0,
    bearing: lastCam?.bearing ?? 0,
    maxPitch: 78,
    attributionControl: { compact: true },
    cooperativeGestures: false,
  });
  map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), "top-right");
  // De lejos, los lugares cercanos se encimaban: el nombre aparece al acercarse o al pasar el cursor
  const far = () => el.classList.toggle("t3-far", map.getZoom() < 9.5);
  map.on("zoom", far);
  map.scrollZoom.disable();
  far();
  map.on("moveend", () => { const c = map.getCenter(); lastCam = { center: [c.lng, c.lat], zoom: map.getZoom(), pitch: map.getPitch(), bearing: map.getBearing() }; });

  let grid: Grid | null = null;
  let clim: (number | null)[][][] = [];
  const markers: maplibregl.Marker[] = [];
  const firstVisit = !lastCam;

  const ready = new Promise<void>((res) => map.on("load", () => {
    // Zonas: la caja exacta de celdas IMERG (ámbar) y la zona pedida (discontinua)
    map.addSource("zones", { type: "geojson", data: {
      type: "FeatureCollection",
      features: opts.zones.flatMap((z) => [
        ...(z.data ? [{ type: "Feature" as const, properties: { id: z.id, kind: "data", on: z.on ? 1 : 0 }, geometry: { type: "Polygon" as const, coordinates: [ring(z.data)] } }] : []),
        ...(z.req ? [{ type: "Feature" as const, properties: { id: z.id, kind: "req", on: z.on ? 1 : 0 }, geometry: { type: "Polygon" as const, coordinates: [ring(z.req)] } }] : []),
      ]),
    } });
    map.addLayer({ id: "zone-fill", type: "fill", source: "zones", filter: ["==", ["get", "kind"], "data"],
      paint: { "fill-color": ["case", ["==", ["get", "on"], 1], "#f2b33d", "#ffffff"], "fill-opacity": ["case", ["==", ["get", "on"], 1], 0.14, 0.05] } });
    map.addLayer({ id: "zone-req", type: "line", source: "zones", filter: ["==", ["get", "kind"], "req"],
      paint: { "line-color": "#ffffff", "line-width": 1.2, "line-dasharray": [3, 3], "line-opacity": 0.7 } });
    map.addLayer({ id: "zone-data", type: "line", source: "zones", filter: ["==", ["get", "kind"], "data"],
      paint: { "line-color": ["case", ["==", ["get", "on"], 1], "#f2b33d", "#ffffff"], "line-width": ["case", ["==", ["get", "on"], 1], 2.5, 1.5] } });
    map.on("click", "zone-fill", (e) => { const id = e.features?.[0]?.properties?.id; if (id) opts.onZone(String(id)); });
    map.on("mouseenter", "zone-fill", () => { map.getCanvas().style.cursor = "pointer"; });
    map.on("mouseleave", "zone-fill", () => { map.getCanvas().style.cursor = ""; });

    // Lugares: marcadores que laten y se pueden tocar
    for (const s of opts.sites) {
      const m = document.createElement("div");
      m.className = `t3-site ${s.on ? "on" : ""}`;
      m.innerHTML = `<button class="t3-dot" aria-label="${s.name}"><i></i><span>${s.name}</span></button><a class="t3-go" href="#ribbon">${opts.siteAction}</a>`;
      m.querySelector("button")!.addEventListener("click", (ev) => { ev.stopPropagation(); flyToSite(s); m.classList.add("open"); opts.onSite(s.id); });
      m.querySelector("a")!.addEventListener("click", () => opts.onSite(s.id));
      markers.push(new maplibregl.Marker({ element: m, anchor: "left", offset: [-9, 0] }).setLngLat([s.lon, s.lat]).addTo(map));
    }
    res();
  }));

  const flyToSite = (s: { lat: number; lon: number }) =>
    map.flyTo({ center: [s.lon, s.lat], zoom: 12.4, pitch: 68, bearing: map.getBearing() - 35, duration: 3800, essential: true });
  const country = (ms = 3200) => map.flyTo({ center: [-70.3, 18.55], zoom: 7.35, pitch: 52, bearing: -14, duration: ms, essential: true });

  const setGrid = (g: Grid) => {
    grid = g;
    clim = Array.from({ length: 12 }, (_, mo) => g.lats.map((_, i) => g.lons.map((_, j) => {
      let s = 0, n = 0;
      for (let t = mo; t < g.meses.length; t += 12) { const v = g.valores[t][i][j]; if (v !== null) { s += v; n++; } }
      return n ? s / n : null;
    })));
    map.addSource("rain", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
    map.addLayer({ id: "rain", type: "circle", source: "rain", paint: {
      "circle-radius": ["interpolate", ["exponential", 2], ["zoom"], 6, ["*", ["get", "r"], 4], 8, ["*", ["get", "r"], 13], 11, ["*", ["get", "r"], 90]],
      "circle-color": ["get", "c"], "circle-opacity": ["interpolate", ["linear"], ["zoom"], 9.5, ["get", "o"], 11.5, ["*", ["get", "o"], 0.28]], "circle-pitch-alignment": "map",

    } }, "zone-fill");
    const pop = new maplibregl.Popup({ closeButton: false, closeOnClick: false, className: "t3-pop", offset: 10 });
    map.on("mousemove", "rain", (e) => { const p = e.features?.[0]?.properties; if (p) pop.setLngLat(e.lngLat).setHTML(String(p.t)).addTo(map); });
    map.on("mouseleave", "rain", () => pop.remove());
  };
  const setField = (mes: string) => {
    if (!grid || !map.getSource("rain")) return;
    const g = grid;
    const t = g.meses.indexOf(mes);
    if (t < 0) return;
    const mo = Number(mes.slice(5, 7)) - 1;
    const features = [];
    for (let i = 0; i < g.lats.length; i++) for (let j = 0; j < g.lons.length; j++) {
      const v = g.valores[t][i][j];
      if (v === null) continue;
      const c = clim[mo][i][j];
      const ratio = c ? v / c - 1 : null;
      const mag = ratio === null ? 0 : Math.min(1, Math.abs(ratio) / 0.8);
      features.push({ type: "Feature" as const, geometry: { type: "Point" as const, coordinates: [g.lons[j], g.lats[i]] }, properties: {
        r: 0.3 + 0.7 * mag,
        c: ratio === null ? "#5a5c62" : ratio < 0 ? mix(DRY, VERY_DRY, Math.min(1, -ratio / 0.7)) : mix([170, 190, 185], WET, Math.min(1, ratio / 0.6)),
        o: 0.55 + 0.4 * mag,
        t: opts.cellLabel(mes, v, ratio === null ? null : Math.round(100 * (1 + ratio))),
      } });
    }
    (map.getSource("rain") as maplibregl.GeoJSONSource).setData({ type: "FeatureCollection", features });
  };
  const tintZone = (color: string, opacity: number) => {
    if (!map.getLayer("zone-fill")) return;
    map.setPaintProperty("zone-fill", "fill-color", ["case", ["==", ["get", "on"], 1], color, "#ffffff"]);
    map.setPaintProperty("zone-fill", "fill-opacity", ["case", ["==", ["get", "on"], 1], opacity, 0.05]);
  };
  // Entrada: desde arriba, la cámara se inclina sobre el relieve del país (solo la primera vez)
  ready.then(() => { if (firstVisit) country(matchMedia("(prefers-reduced-motion: reduce)").matches ? 0 : 3600); });
  return { map, ready, setGrid, setField, tintZone, country, flyToSite, destroy: () => { markers.forEach((m) => m.remove()); map.remove(); } };
}
