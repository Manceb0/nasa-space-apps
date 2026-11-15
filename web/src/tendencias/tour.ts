// Recorrido automático del pitch, como un vídeo: la cámara vuela sobre el mapa, se acerca al panel donde está la
// prueba y un subtítulo entra palabra a palabra. Escenas: la disputa, el Yuna, el ajuste, la llovizna y Puerto Rico,
// los huracanes, qué vigilar hoy y el cierre. Usa la propia herramienta (no un vídeo grabado): cada escena toca los
// mismos botones que tocaría una persona, así que todo lo que se ve son datos reales.
import { esc, LL } from "./datos";
import "./tour.css";

export interface TourApi {
  wx: HTMLElement;
  map: () => { flyTo: (o: object) => void; fitBounds: (b: [[number, number], [number, number]], o: object) => void } | null;
  yuna: [[number, number], [number, number]] | null;
  reset: () => void;
}
interface Scene { dur: number; text: string; run: (api: TourApi) => void; zoom?: string | null }

const RM = () => matchMedia("(prefers-reduced-motion: reduce)").matches;
const $q = (api: TourApi, sel: string) => api.wx.querySelector<HTMLElement>(sel) ?? document.querySelector<HTMLElement>(sel);
const click = (api: TourApi, sel: string) => $q(api, sel)?.click();
const closeAll = (api: TourApi) => {
  const dlg = document.querySelector<HTMLDialogElement>("#s13-lb"); if (dlg?.open) dlg.close();
  if (api.wx.dataset.cy === "on") { if ($q(api, "[data-prepq].on")) click(api, "[data-prepq]"); if ($q(api, "[data-cyq].on")) click(api, "[data-cyq]"); }
  if ($q(api, "#s13-h.on")) click(api, "#s13-h");
};

function scenes(): Scene[] {
  return [
    { dur: 7000, zoom: null, text: LL("¿Está cambiando la lluvia en República Dominicana? Lo preguntamos a los satélites de la NASA.", "Is rainfall changing in the Dominican Republic? We asked NASA's satellites."),
      run: (a) => { closeAll(a); a.reset(); a.map()?.flyTo({ center: [-70.2, 18.85], zoom: 6.9, pitch: 0, bearing: 0, duration: RM() ? 0 : 4500, essential: true }); } },
    { dur: 9000, zoom: "#ans .vd", text: LL("IMERG dice que hay más rachas secas: +19 % por década. CHIRPS, con pluviómetros, dice que menos: −22 %. Mismo país, direcciones opuestas.", "IMERG says dry spells are rising: +19 % per decade. CHIRPS, built with rain gauges, says they are falling: −22 %. Same country, opposite directions."),
      run: (a) => { click(a, '[data-q="secos"]'); } },
    { dur: 8000, zoom: null, text: LL("Las disputas caen donde más importa: la cuenca del Yuna, la que más se inunda.", "The disputes fall where it matters most: the Yuna basin, the one that floods the most."),
      run: (a) => { if (a.yuna) a.map()?.fitBounds(a.yuna, { padding: 140, duration: RM() ? 0 : 3500, essential: true }); } },
    { dur: 9000, zoom: "#ans .adj-res, #s13-h", text: LL("Si IMERG contara los días como antes de 2018, casi todas las disputas desaparecen: de 117 celdas a 2.", "If IMERG counted days as it did before 2018, almost every dispute disappears: from 117 cells to 2."),
      run: (a) => { click(a, '[data-per="seca"]'); setTimeout(() => { if (!$q(a, "#s13-h.on")) click(a, "#s13-h"); }, 600); a.map()?.flyTo({ center: [-70.2, 18.85], zoom: 6.9, duration: RM() ? 0 : 2500, essential: true }); } },
    { dur: 11000, zoom: null, text: LL("Lo que cambia es cómo IMERG cuenta la llovizna. En Puerto Rico, bajo el mismo satélite, 18 de 19 pluviómetros lo confirman.", "What changes is how IMERG counts drizzle. In Puerto Rico, under the same satellite, 18 of 19 rain gauges confirm it."),
      run: (a) => { if ($q(a, "#s13-h.on")) click(a, "#s13-h"); click(a, '[data-per="anual"]'); setTimeout(() => { click(a, "[data-fig13]"); setTimeout(() => document.querySelector("#s13-lb .hz-pr")?.scrollIntoView({ behavior: RM() ? "auto" : "smooth", block: "center" }), 3500); }, 500); } },
    { dur: 13000, zoom: null, text: LL("Dos lluvias, dos alertas. Con María, el boletín oficial del NHC ya la ponía cerca del Yuna 103 horas antes.", "Two kinds of rain, two alerts. With María, the official NHC advisory already put it near the Yuna 103 hours ahead."),
      run: (a) => { const dlg = document.querySelector<HTMLDialogElement>("#s13-lb"); if (dlg?.open) dlg.close(); click(a, "[data-cyq]"); setTimeout(() => click(a, '[data-cy-yuna="yuna"]'), 2500); } },
    { dur: 10000, zoom: null, text: LL("Y hoy: qué municipio vigilar, con el pronóstico de dos modelos y la lluvia de 90 días frente a 24 años.", "And today: which municipality to watch, with two models' forecast and 90-day rain against 24 years."),
      run: (a) => { click(a, "[data-prepq]"); } },
    { dur: 8000, zoom: null, text: LL("Stellar Horizons: datos de la NASA, comprobados antes de creerlos.", "Stellar Horizons: NASA data, checked before it is believed."),
      run: (a) => { closeAll(a); a.reset(); } },
  ];
}

let stopCur: (() => void) | null = null;
export function startTour(api: TourApi) {
  stopCur?.();
  const S = scenes();
  let i = 0, timer = 0, paused = false, left = 0, started = 0;
  const root = document.createElement("div");
  root.className = "tour";
  root.innerHTML = `<div class="tour-bars">${S.map(() => `<i><b></b></i>`).join("")}</div>
    <p class="tour-cap" aria-live="polite"></p>
    <div class="tour-ctl">
      <button data-t="prev" aria-label="${esc(LL("Escena anterior", "Previous scene"))}"><svg viewBox="0 0 16 16"><path d="M10 3.5 5.5 8l4.5 4.5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg></button>
      <button data-t="play" aria-label="${esc(LL("Pausar o seguir", "Pause or resume"))}"></button>
      <button data-t="next" aria-label="${esc(LL("Escena siguiente", "Next scene"))}"><svg viewBox="0 0 16 16"><path d="M6 3.5 10.5 8 6 12.5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg></button>
      <button data-t="close" class="x">${esc(LL("Salir del recorrido", "Exit the tour"))}</button>
    </div>`;
  document.body.appendChild(root);
  document.body.classList.add("touring");
  const cap = root.querySelector<HTMLElement>(".tour-cap")!, bars = [...root.querySelectorAll<HTMLElement>(".tour-bars b")];
  const syncPlay = () => { root.querySelector('[data-t="play"]')!.innerHTML = paused ? '<svg viewBox="0 0 16 16"><path d="M5 3.5v9l7.5-4.5z" fill="currentColor"/></svg>' : '<svg viewBox="0 0 16 16"><rect x="4" y="3" width="3" height="10" rx="1.2" fill="currentColor"/><rect x="9" y="3" width="3" height="10" rx="1.2" fill="currentColor"/></svg>'; };

  // Cámara sobre la interfaz: un acercamiento suave al elemento que lleva la prueba
  const zoomTo = (sel: string | null | undefined) => {
    const wx = api.wx;
    if (!sel || RM()) { wx.style.transform = ""; wx.classList.remove("tour-zoomed"); return; }
    const el = sel.split(",").map((x) => wx.querySelector<HTMLElement>(x.trim())).find((x) => x && x.offsetParent);
    if (!el) { wx.style.transform = ""; return; }
    el.scrollIntoView({ block: "center", behavior: "auto" });
    requestAnimationFrame(() => {
      const r = el.getBoundingClientRect(), w = wx.getBoundingClientRect();
      wx.style.transformOrigin = `${r.left + r.width / 2 - w.left}px ${r.top + r.height / 2 - w.top}px`;
      wx.classList.add("tour-zoomed");
      wx.style.transform = "scale(1.42)";
      el.classList.add("tour-focus");
      setTimeout(() => el.classList.remove("tour-focus"), S[i].dur - 600);
    });
  };
  const caption = (t: string) => {
    cap.classList.remove("in");
    cap.innerHTML = t.split(" ").map((w, k) => `<span style="--k:${k}">${esc(w)}</span>`).join(" ");
    requestAnimationFrame(() => requestAnimationFrame(() => cap.classList.add("in")));
  };
  const show = (k: number) => {
    i = Math.max(0, Math.min(S.length - 1, k));
    clearTimeout(timer);
    bars.forEach((b, j) => { b.style.transition = "none"; b.style.transform = `scaleX(${j < i ? 1 : 0})`; });
    zoomTo(null);
    try { S[i].run(api); } catch { /* una escena que falla no detiene el recorrido */ }
    caption(S[i].text);
    setTimeout(() => zoomTo(S[i].zoom), 900);
    left = S[i].dur; play();
  };
  const play = () => {
    paused = false; syncPlay(); started = performance.now();
    const b = bars[i]; void b.offsetWidth;
    b.style.transition = `transform ${left}ms linear`; b.style.transform = "scaleX(1)";
    timer = window.setTimeout(() => (i < S.length - 1 ? show(i + 1) : end()), left);
  };
  const pause = () => {
    paused = true; syncPlay(); clearTimeout(timer);
    left = Math.max(300, left - (performance.now() - started));
    const b = bars[i], m = getComputedStyle(b).transform; b.style.transition = "none"; b.style.transform = m === "none" ? "scaleX(0)" : m;
  };
  const end = () => {
    clearTimeout(timer); zoomTo(null);
    cap.innerHTML = `<span class="end">${esc(LL("Fin del recorrido.", "End of the tour."))}</span> <a href="#respuesta">${esc(LL("Ver la respuesta completa", "See the full answer"))}</a>`;
    cap.classList.add("in"); paused = true; syncPlay();
  };
  const stop = () => { clearTimeout(timer); zoomTo(null); root.remove(); document.body.classList.remove("touring"); document.removeEventListener("keydown", key); stopCur = null; };
  const key = (e: KeyboardEvent) => {
    if (e.key === "Escape") stop();
    else if (e.key === "ArrowRight") show(i + 1);
    else if (e.key === "ArrowLeft") show(i - 1);
    else if (e.key === " ") { e.preventDefault(); paused ? play() : pause(); }
  };
  document.addEventListener("keydown", key);
  root.addEventListener("click", (e) => {
    const t = (e.target as Element).closest<HTMLElement>("[data-t]")?.dataset.t;
    if (t === "prev") show(i - 1); else if (t === "next") (i < S.length - 1 ? show(i + 1) : end());
    else if (t === "play") (paused ? play() : pause()); else if (t === "close") stop();
    if ((e.target as Element).closest("a")) stop();
  });
  stopCur = stop;
  show(0);
  return stop;
}
export function stopTour() { stopCur?.(); }
