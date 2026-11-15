// Recorrido automático para el pitch: se ve la herramienta usándose. Un cursor toca cada vista y cada botón, la cámara
// centra lo que se investiga (los ríos Yuna y Camú, Villa Riva, Hatillo) en el hueco libre entre paneles, y un rótulo
// corto nombra la interacción. Dentro de capas con desplazamiento propio (Preparar, huracanes) nunca mueve la página:
// solo ilumina. Orden: el país en 3D, los ríos, dos satélites en el mismo mapa y en el tiempo, ponerlo a prueba,
// el ciclón, qué vigilar hoy, la sequía en la Auditoría y la respuesta del reto. Todo son datos reales.
import { esc, LL } from "./datos";
import "./tour.css";

type Pad = { left: number; right: number; top: number; bottom: number };
type Cam = { flyTo: (o: object) => void; fitBounds: (b: [[number, number], [number, number]], o: object) => void };
export interface TourApi {
  map: () => Cam | null;
  yuna: [[number, number], [number, number]] | null;
  pad: () => Pad;
  rivers: (names: string[] | null) => void;
  reset: () => void;
}
type Ctx = { tap: (sel: string) => Promise<boolean>; wait: (ms: number) => Promise<void>; go: (hash: string, ready: string) => Promise<void>; look: (sel: string, scale?: number) => void };
interface Scene { dur: number; text: string; run: (api: TourApi, c: Ctx) => Promise<void> }

const RM = () => matchMedia("(prefers-reduced-motion: reduce)").matches;
const vis = (sel: string) => [...document.querySelectorAll<HTMLElement>(sel)].find((x) => x.offsetParent || x.getClientRects().length);
const RIOS = ["Río Yuna", "Río Camú"];
let busy = false;
export const tourBusy = () => busy;

function scenes(): Scene[] {
  const ms = (n: number) => (RM() ? 0 : n);
  const home = (a: TourApi) => ({ center: [-70.3, 18.75], zoom: 7.3, pitch: 58, bearing: -16, padding: a.pad(), duration: ms(4500), essential: true });
  return [
    { dur: 8000, text: LL("Toca 3D: el país, con su relieve", "Tap 3D: the country, with its relief"),
      run: async (a, c) => { a.reset(); await c.wait(400); await c.tap('[data-cam="3d"]'); await c.wait(900); a.map()?.flyTo(home(a)); } },
    { dur: 12000, text: LL("El Yuna y el Camú, hasta Villa Riva", "The Yuna and the Camú, down to Villa Riva"),
      run: async (a, c) => {
        a.rivers(RIOS);
        if (a.yuna) a.map()?.fitBounds(a.yuna, { padding: a.pad(), pitch: 60, bearing: -24, duration: ms(4500), essential: true });
        await c.wait(5600);
        a.map()?.flyTo({ center: [-70.0, 19.12], zoom: 9.3, pitch: 64, bearing: 10, padding: a.pad(), duration: ms(4500), essential: true });
      } },
    { dur: 10000, text: LL("Toca IMERG: la lluvia se intensifica", "Tap IMERG: rain is intensifying"),
      run: async (a, c) => {
        a.rivers(null); a.map()?.flyTo(home(a));
        await c.tap('[data-q="fuerte"]'); await c.wait(400); await c.tap("#m-btn"); await c.wait(450); await c.tap('.menu .mi[data-v="SDII"]'); await c.wait(700);
        await c.tap('[data-show="IMERG"]');
      } },
    { dur: 12000, text: LL("Toca CHIRPS: se debilita. Míralo año a año", "Tap CHIRPS: it weakens. Watch it year by year"),
      run: async (_a, c) => { await c.tap('[data-show="CHIRPS"]'); await c.wait(2600); await c.tap(".wx-play"); await c.wait(6000); await c.tap(".wx-play"); await c.wait(500); await c.tap(".wx-trendbtn"); } },
    { dur: 9000, text: LL("Veredicto: dónde se contradicen", "Verdict: where they contradict"),
      run: async (a, c) => { await c.tap('[data-show="acuerdo"]'); a.map()?.flyTo({ center: [-70.45, 18.95], zoom: 8.1, pitch: 55, bearing: -10, padding: a.pad(), duration: RM() ? 0 : 5000, essential: true }); } },
    { dur: 11000, text: LL("¿Y si IMERG contara bien los días de lluvia?", "What if IMERG counted rain days right?"),
      run: async (_a, c) => {
        c.look("", 1);
        if (!vis("#s13-h.on")) await c.tap("#s13-h");
        await c.wait(900); c.look(".adj-res", 1);
      } },
    { dur: 16000, text: LL("Vista Huracanes: el aviso del NHC, 103 h antes", "Hurricanes view: the NHC warning, 103 h ahead"),
      run: async (_a, c) => {
        c.look("", 1); if (vis("#s13-h.on")) await c.tap("#s13-h");
        await c.tap("#sty-btn"); await c.wait(500); await c.tap('.menu .mi[data-v="ciclones"]'); await c.wait(2400);
        await c.tap('[data-cy-yuna="yuna"]'); await c.wait(2200); c.look(".cy-over .hx-top", 1); await c.wait(5200); c.look(".cy-over .hx-time", 1);
      } },
    { dur: 11000, text: LL("¿Qué municipio vigilar hoy?", "Which municipality to watch today?"),
      run: async (_a, c) => {
        c.look("", 1); await c.tap("#sty-btn"); await c.wait(450); await c.tap('.menu .mi[data-v="crestas"]'); await c.wait(900);
        await c.tap("[data-prepq]"); await c.wait(1800); c.look(".prep-over .pb-list", 1);
      } },
    { dur: 11000, text: LL("Sequía: la alarma depende del satélite", "Drought: the alarm depends on the satellite"),
      run: async (_a, c) => { c.look("", 1); await c.go("#auditoria", "#au-kpi .au-lead"); await c.wait(500); c.look("#au-kpi", 1.3); } },
    { dur: 10000, text: LL("La respuesta del reto, en una vista", "The challenge's answer, in one view"),
      run: async (_a, c) => { c.look("", 1); await c.go("#respuesta", ".rs-four"); await c.wait(400); c.look(".rs-four", 1); } },
  ];
}

let stopCur: (() => void) | null = null;
export function startTour(api: TourApi) {
  stopCur?.();
  busy = true;
  const S = scenes();
  let i = 0, timer = 0, paused = false, left = 0, started = 0, token = 0;
  const root = document.createElement("div");
  root.className = "tour";
  root.innerHTML = `<div class="tour-lens"></div>
    <div class="tour-cursor" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M5 3l14 8-6.2 1.6L10 19z" fill="#fff" stroke="#000" stroke-width="1.6" stroke-linejoin="round"/></svg><i></i></div>
    <div class="tour-bars">${S.map(() => `<i><b></b></i>`).join("")}</div>
    <p class="tour-cap" aria-live="polite"></p>
    <div class="tour-ctl">
      <button data-t="prev" aria-label="${esc(LL("Escena anterior", "Previous scene"))}"><svg viewBox="0 0 16 16"><path d="M10 3.5 5.5 8l4.5 4.5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg></button>
      <button data-t="play" aria-label="${esc(LL("Pausar o seguir", "Pause or resume"))}"></button>
      <button data-t="next" aria-label="${esc(LL("Escena siguiente", "Next scene"))}"><svg viewBox="0 0 16 16"><path d="M6 3.5 10.5 8 6 12.5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg></button>
      <button data-t="close" class="x">${esc(LL("Salir", "Exit"))}</button>
    </div>`;
  document.body.appendChild(root);
  document.body.classList.add("touring");
  const cap = root.querySelector<HTMLElement>(".tour-cap")!, bars = [...root.querySelectorAll<HTMLElement>(".tour-bars b")];
  const lens = root.querySelector<HTMLElement>(".tour-lens")!, cur = root.querySelector<HTMLElement>(".tour-cursor")!;
  let cx = innerWidth / 2, cy = innerHeight / 2;
  cur.style.transform = `translate(${cx}px, ${cy}px)`;
  const syncPlay = () => { root.querySelector('[data-t="play"]')!.innerHTML = paused ? '<svg viewBox="0 0 16 16"><path d="M5 3.5v9l7.5-4.5z" fill="currentColor"/></svg>' : '<svg viewBox="0 0 16 16"><rect x="4" y="3" width="3" height="10" rx="1.2" fill="currentColor"/><rect x="9" y="3" width="3" height="10" rx="1.2" fill="currentColor"/></svg>'; };

  // ── la cámara sobre la interfaz ──
  // Solo acerca (escala) lo que vive en un panel fijo de #wx o #au. Lo que está en una capa con desplazamiento propio
  // (Preparar, huracanes) o en una página larga se ilumina sin mover la página. El lente sigue al elemento cada fotograma
  // mientras termina la transición, así no se queda desplazado.
  let follow = 0, followEl: HTMLElement | null = null, lensT = 0;
  const hosts = () => [...document.querySelectorAll<HTMLElement>("#wx, #au")];
  const track = () => {
    cancelAnimationFrame(follow);
    const t0 = performance.now();
    const step = () => {
      if (!followEl || !followEl.isConnected) { lens.classList.remove("on"); return; }
      const r = followEl.getBoundingClientRect(), m = 10;
      Object.assign(lens.style, { left: `${r.left - m}px`, top: `${r.top - m}px`, width: `${r.width + 2 * m}px`, height: `${r.height + 2 * m}px` });
      lens.classList.add("on");
      if (performance.now() - t0 < 2400) follow = requestAnimationFrame(step);
    };
    follow = requestAnimationFrame(step);
  };
  const look = (sel: string, scale = 1.6) => {
    clearTimeout(lensT); cancelAnimationFrame(follow);
    hosts().forEach((h) => { h.style.transform = ""; });
    followEl = null; lens.classList.remove("on");
    if (!sel) return;
    const el = vis(sel); if (!el) return;
    const host = el.closest<HTMLElement>("#wx, #au"), inOverlay = !!el.closest(".prep-over, .cy-over");
    followEl = el;
    if (!host || inOverlay || RM() || scale <= 1.05) {
      if (!inOverlay) el.scrollIntoView({ block: "center", behavior: RM() ? "auto" : "smooth" });
      track();
      return;
    }
    el.scrollIntoView({ block: "nearest", behavior: "auto" });
    requestAnimationFrame(() => {
      const r = el.getBoundingClientRect(), w = host.getBoundingClientRect();
      const free = innerHeight - 230, sc = Math.min(scale, (innerWidth * 0.8) / r.width, (free * 0.85) / r.height);
      const ex = r.left + r.width / 2 - w.left, ey = r.top + r.height / 2 - w.top;
      const tx = innerWidth / 2 - w.left - sc * ex, ty = Math.max(70, free / 2) - w.top - sc * ey;
      host.style.transformOrigin = "0 0";
      host.style.transform = `translate(${tx.toFixed(1)}px, ${ty.toFixed(1)}px) scale(${sc.toFixed(3)})`;
      lensT = window.setTimeout(track, 200);
    });
  };

  // ── el cursor: viaja hasta el botón, marca el clic y lo pulsa de verdad ──
  const wait = (n: number) => new Promise<void>((res) => setTimeout(res, n));
  const tap = async (sel: string) => {
    const t = token, el = vis(sel);
    if (!el || t !== token) return false;
    const r = el.getBoundingClientRect(), x = r.left + Math.min(r.width / 2, 40), y = r.top + r.height / 2;
    const dist = Math.hypot(x - cx, y - cy), d = RM() ? 0 : Math.min(900, 250 + dist * 0.6);
    cur.style.transition = `transform ${d}ms cubic-bezier(.65, 0, .25, 1)`;
    cur.style.transform = `translate(${x}px, ${y}px)`; cx = x; cy = y;
    await wait(d + 120);
    if (t !== token) return false;
    cur.classList.remove("hit"); void cur.offsetWidth; cur.classList.add("hit");
    el.classList.add("tour-press"); setTimeout(() => el.classList.remove("tour-press"), 260);
    await wait(180);
    if (t !== token) return false;
    el.click();
    document.getElementById("tr-tip")?.setAttribute("hidden", "");
    return true;
  };
  const go = async (hash: string, ready: string) => {
    if (location.hash !== hash) { look("", 1); location.hash = hash; }
    for (let k = 0; k < 60 && !vis(ready); k++) await wait(100);
    await wait(300);
  };
  const ctx = (): Ctx => { const t = token; return { tap, wait, go, look: (s, sc) => { if (t === token) look(s, sc); } }; };

  const caption = (t: string) => {
    cap.classList.remove("in");
    cap.innerHTML = t.split(" ").map((w, k) => `<span style="--k:${k}">${esc(w)}</span>`).join(" ");
    requestAnimationFrame(() => requestAnimationFrame(() => cap.classList.add("in")));
  };
  const show = (k: number) => {
    i = Math.max(0, Math.min(S.length - 1, k)); token++;
    clearTimeout(timer);
    bars.forEach((b, j) => { b.style.transition = "none"; b.style.transform = `scaleX(${j < i ? 1 : 0})`; });
    caption(S[i].text);
    S[i].run(api, ctx()).catch(() => { /* una escena que falla no detiene el recorrido */ });
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
    clearTimeout(timer); token++; look("", 1);
    cap.innerHTML = `<span class="end">${esc(LL("Ahora, explóralo tú.", "Now, explore it yourself."))}</span> <a href="#tendencias">${esc(LL("Ir al mapa", "Go to the map"))}</a>`;
    cap.classList.add("in"); paused = true; syncPlay();
  };
  const stop = () => {
    clearTimeout(timer); token++; look("", 1);
    try { api.rivers(null); } catch { /* el mapa ya no existe */ }
    root.remove(); document.body.classList.remove("touring"); document.removeEventListener("keydown", key); stopCur = null; busy = false;
  };
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
