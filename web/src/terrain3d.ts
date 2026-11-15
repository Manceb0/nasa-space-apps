// Escena 3D: relieve real (AWS Terrain Tiles, formato terrarium) con imagen satelital encima,
// y sobre el terreno los datos de verdad: el campo de lluvia IMERG por celda, las cajas exactas de cada zona
// y los lugares MODIS. Todo se puede girar, inclinar, acercar y tocar.
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import type { Grid } from "./field";

export interface Zone { id: string; name: string; req: number[] | null; data: number[] | null; on: boolean }
export interface Site { id: string; name: string; lat: number; lon: number; on: boolean; note?: string }

// Colores de sistema de Apple (modo oscuro)
const ORANGE = [255, 159, 10];
const RED = [255, 69, 58];
const BLUE = [10, 132, 255];
const MIST = [150, 170, 190];
const lerp = (a: number[], b: number[], t: number) => a.map((v, k) => Math.round(v + (b[k] - v) * t));
const ring = (b: number[]) => [[b[0], b[1]], [b[2], b[1]], [b[2], b[3]], [b[0], b[3]], [b[0], b[1]]];
let lastCam: { center: [number, number]; zoom: number; pitch: number; bearing: number } | null = null;

export function terrain3d(el: HTMLElement, opts: {
  zones: Zone[]; sites: Site[];
  onZone: (id: string) => void; onSite: (id: string) => void;
  cellLabel: (mes: string, mm: number | null, pct: number | null) => string;
  siteAction: string;
  provinces?: { type: "FeatureCollection"; features: unknown[] };
  onProvince?: (id: string, name: string) => void;
}) {
  const map = new maplibregl.Map({
    container: el,
    style: {
      version: 8,
      sources: {
        dark: { type: "raster", tiles: ["https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}"], tileSize: 256, maxzoom: 16,
          attribution: "Base: Esri World Dark Gray" },
        sat: { type: "raster", tiles: ["https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"], tileSize: 256, maxzoom: 17,
          attribution: "Imagen: Esri, Maxar, Earthstar Geographics" },
        dem: { type: "raster-dem", tiles: ["https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"], encoding: "terrarium", tileSize: 256, maxzoom: 13,
          attribution: "Relieve: AWS Terrain Tiles (SRTM y otras fuentes)" },
        shade: { type: "raster-dem", tiles: ["https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"], encoding: "terrarium", tileSize: 256, maxzoom: 13 },
      },
      layers: [
        { id: "bg", type: "background", paint: { "background-color": "#07080a" } },
        { id: "dark", type: "raster", source: "dark", layout: { visibility: "none" }, paint: { "raster-opacity": 1 } },
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
  const cvs = document.createElement("canvas");
  let corners: [[number, number], [number, number], [number, number], [number, number]] = [[0, 0], [0, 0], [0, 0], [0, 0]];
  let cur = -1;
  let pendingUrl = "";
  let imgTimer = 0;
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
      paint: { "fill-color": ["case", ["==", ["get", "on"], 1], "#ff9f0a", "#ffffff"], "fill-opacity": ["case", ["==", ["get", "on"], 1], 0.14, 0.05] } });
    map.addLayer({ id: "zone-req", type: "line", source: "zones", filter: ["==", ["get", "kind"], "req"],
      paint: { "line-color": "#ffffff", "line-width": 1.2, "line-dasharray": [3, 3], "line-opacity": 0.7 } });
    map.addLayer({ id: "zone-data", type: "line", source: "zones", filter: ["==", ["get", "kind"], "data"],
      paint: { "line-color": ["case", ["==", ["get", "on"], 1], "#ff9f0a", "#ffffff"], "line-width": ["case", ["==", ["get", "on"], 1], 2.5, 1.5] } });
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
    // Provincias: relleno por métrica (feature-state), borde fino y resaltado al pasar
    if (opts.provinces) {
      map.addSource("prov", { type: "geojson", data: opts.provinces as GeoJSON.FeatureCollection, promoteId: "shapeID" });
      map.addLayer({ id: "prov-fill", type: "fill", source: "prov", layout: { visibility: "none" }, paint: {
        "fill-color": ["coalesce", ["feature-state", "c"], "rgba(120,120,128,.15)"],
        "fill-opacity": ["case", ["boolean", ["feature-state", "hover"], false], 0.92, ["coalesce", ["feature-state", "o"], 0.72]],
      } }, "zone-fill");
      map.addLayer({ id: "prov-line", type: "line", source: "prov", paint: {
        "line-color": ["case", ["boolean", ["feature-state", "sel"], false], "#ffffff", "rgba(255,255,255,.35)"],
        "line-width": ["case", ["boolean", ["feature-state", "sel"], false], 2.4, ["boolean", ["feature-state", "hover"], false], 1.6, 0.7],
      } }, "zone-fill");
      let hov: string | number | undefined;
      map.on("mousemove", "prov-fill", (e) => {
        const f = e.features?.[0]; if (!f) return;
        map.getCanvas().style.cursor = "pointer";
        if (hov === f.id) return;
        if (hov !== undefined) map.setFeatureState({ source: "prov", id: hov }, { hover: false });
        hov = f.id; map.setFeatureState({ source: "prov", id: hov! }, { hover: true });
        refresh3d();
      });
      map.on("mouseleave", "prov-fill", () => { if (hov !== undefined) { map.setFeatureState({ source: "prov", id: hov }, { hover: false }); refresh3d(); } hov = undefined; map.getCanvas().style.cursor = ""; });
      map.on("click", "prov-fill", (e) => { const f = e.features?.[0]; if (f && opts.onProvince) opts.onProvince(String(f.id), String(f.properties?.shapeName ?? "")); });
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
    // Campo de lluvia como imagen: un píxel por celda IMERG; el mapa lo dibuja suave (lineal) entre centros
    const res = g.resolucion_grados / 2;
    cvs.width = g.lons.length; cvs.height = g.lats.length;
    corners = [[g.lons[0] - res, g.lats[0] + res], [g.lons[g.lons.length - 1] + res, g.lats[0] + res],
      [g.lons[g.lons.length - 1] + res, g.lats[g.lats.length - 1] - res], [g.lons[0] - res, g.lats[g.lats.length - 1] - res]];
    map.addSource("rain", { type: "image", url: cvs.toDataURL(), coordinates: corners });
    map.addLayer({ id: "rain", type: "raster", source: "rain", paint: {
      "raster-resampling": "linear", "raster-fade-duration": 300,
      "raster-opacity": ["interpolate", ["linear"], ["zoom"], 9.5, 0.85, 11.5, 0.3],
    } }, "zone-fill");
    const pop = new maplibregl.Popup({ closeButton: false, closeOnClick: false, className: "t3-pop", offset: 12 });
    map.on("mousemove", (e) => {
      if (cur < 0 || !grid) { pop.remove(); return; }
      const j = Math.round((e.lngLat.lng - g.lons[0]) / g.resolucion_grados);
      const i = Math.round((g.lats[0] - e.lngLat.lat) / g.resolucion_grados);
      const v = g.valores[cur]?.[i]?.[j];
      if (v === null || v === undefined) { pop.remove(); return; }
      const c = clim[Number(g.meses[cur].slice(5, 7)) - 1][i][j];
      pop.setLngLat([g.lons[j], g.lats[i]]).setHTML(opts.cellLabel(g.meses[cur], v, c ? Math.round(100 * v / c) : null)).addTo(map);
    });
    map.getCanvas().addEventListener("mouseleave", () => pop.remove());
  };
  const setField = (mes: string) => {
    if (!grid || !map.getSource("rain")) return;
    const g = grid;
    const t = g.meses.indexOf(mes);
    if (t < 0) return;
    cur = t;
    const mo = Number(mes.slice(5, 7)) - 1;
    const ctx = cvs.getContext("2d")!;
    const img = ctx.createImageData(cvs.width, cvs.height);
    for (let i = 0; i < g.lats.length; i++) for (let j = 0; j < g.lons.length; j++) {
      const v = g.valores[t][i][j];
      const k = 4 * (i * cvs.width + j);
      if (v === null) { img.data[k + 3] = 0; continue; }
      const c = clim[mo][i][j];
      const ratio = c ? v / c - 1 : 0;
      const mag = Math.min(1, Math.abs(ratio) / 0.8);
      const rgb = ratio < 0 ? lerp(ORANGE, RED, Math.min(1, -ratio / 0.75)) : lerp(MIST, BLUE, Math.min(1, ratio / 0.7));
      img.data[k] = rgb[0]; img.data[k + 1] = rgb[1]; img.data[k + 2] = rgb[2];
      img.data[k + 3] = Math.round(255 * (0.08 + 0.4 * mag));
    }
    ctx.putImageData(img, 0, 0);
    pendingUrl = cvs.toDataURL();
    if (!imgTimer) imgTimer = window.setTimeout(() => {
      imgTimer = 0;
      if (pendingUrl && map.getSource("rain")) (map.getSource("rain") as maplibregl.ImageSource).updateImage({ url: pendingUrl, coordinates: corners });
      pendingUrl = "";
    }, 140);
  };
  const tintZone = (color: string, opacity: number) => {
    if (!map.getLayer("zone-fill")) return;
    map.setPaintProperty("zone-fill", "fill-color", ["case", ["==", ["get", "on"], 1], color, "#ffffff"]);
    map.setPaintProperty("zone-fill", "fill-opacity", ["case", ["==", ["get", "on"], 1], opacity, 0.05]);
  };
  // Entrada: desde arriba, la cámara se inclina sobre el relieve del país (solo la primera vez)
  ready.then(() => { if (firstVisit) country(matchMedia("(prefers-reduced-motion: reduce)").matches ? 0 : 3600); });
  // Formas de ver el mapa: relieve 3D con foto, plano con foto, u oscuro para leer los datos
  const setMode = (mode: "3d" | "plano" | "oscuro") => {
    const flat = mode !== "3d";
    map.setTerrain(flat ? null : { source: "dem", exaggeration: 1.8 });
    map.setLayoutProperty("sat", "visibility", mode === "oscuro" ? "none" : "visible");
    map.setLayoutProperty("dark", "visibility", mode === "oscuro" ? "visible" : "none");
    map.setPaintProperty("shade", "hillshade-exaggeration", mode === "oscuro" ? 0.25 : 0.55);
    if (flat) map.fitBounds([[-72.05, 17.45], [-68.3, 19.98]], { padding: { top: 230, bottom: 360, left: 260, right: 460 }, pitch: 0, bearing: 0, duration: 1400 });
    else map.easeTo({ pitch: 52, bearing: -14, duration: 1400 });
  };
  let selProv: string | null = null;
  // Con relieve 3D, MapLibre guarda la escena en texturas y no las rehace al cambiar el feature-state:
  // hay que soltarlas para que el mapa pinte los colores nuevos (si no, se queda la variable anterior)
  const refresh3d = () => {
    (map as unknown as { terrain?: { sourceCache?: { freeRtt: () => void } } }).terrain?.sourceCache?.freeRtt();
    map.triggerRepaint();
  };
  const setLayer = (kind: "rain" | "prov" | "cells") => {
    if (map.getLayer("rain")) map.setLayoutProperty("rain", "visibility", kind === "rain" ? "visible" : "none");
    if (map.getLayer("prov-fill")) map.setLayoutProperty("prov-fill", "visibility", kind === "prov" ? "visible" : "none");
    if (map.getLayer("cells")) map.setLayoutProperty("cells", "visibility", kind === "cells" ? "visible" : "none");
  };
  // Capa genérica de celdas: una imagen RGBA (fila 0 = norte) estirada sobre su caja [oeste, sur, este, norte]
  const cvsCells = document.createElement("canvas");
  const setCells = (px: Uint8ClampedArray, w: number, h: number, b: [number, number, number, number]) => {
    cvsCells.width = w; cvsCells.height = h;
    const ctx = cvsCells.getContext("2d")!;
    const img = ctx.createImageData(w, h);
    img.data.set(px);
    ctx.putImageData(img, 0, 0);
    const url = cvsCells.toDataURL();
    const coords: [[number, number], [number, number], [number, number], [number, number]] = [[b[0], b[3]], [b[2], b[3]], [b[2], b[1]], [b[0], b[1]]];
    const src = map.getSource("cells") as maplibregl.ImageSource | undefined;
    if (src) { src.updateImage({ url, coordinates: coords }); return; }
    map.addSource("cells", { type: "image", url, coordinates: coords });
    map.addLayer({ id: "cells", type: "raster", source: "cells", layout: { visibility: "none" }, paint: {
      "raster-resampling": "linear", "raster-fade-duration": 400,
      "raster-opacity": ["interpolate", ["linear"], ["zoom"], 9.5, 0.92, 11.5, 0.35],
    } }, map.getLayer("prov-line") ? "prov-line" : "zone-fill");
  };
  const setChoro = (colors: Record<string, string>, opacity?: Record<string, number>) => {
    for (const [id, c] of Object.entries(colors)) map.setFeatureState({ source: "prov", id }, { c, ...(opacity ? { o: opacity[id] ?? 0.72 } : {}) });
    refresh3d();
  };
  const selectProvince = (id: string | null, bounds?: [[number, number], [number, number]]) => {
    if (selProv) map.setFeatureState({ source: "prov", id: selProv }, { sel: false });
    selProv = id;
    if (id) map.setFeatureState({ source: "prov", id }, { sel: true });
    refresh3d();
    if (bounds) map.fitBounds(bounds, { padding: fitPad, pitch: map.getPitch(), duration: 1800, maxZoom: 10 });
  };
  let fitPad = { top: 260, bottom: 340, left: 60, right: 460 };
  const setFitPadding = (p: typeof fitPad) => { fitPad = p; };
  return { setMode, setLayer, setChoro, selectProvince, setCells, setFitPadding, map, ready, setGrid, setField, tintZone, country, flyToSite, destroy: () => { markers.forEach((m) => m.remove()); map.remove(); } };
}
