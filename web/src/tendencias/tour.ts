// Recorrido automático para el pitch: se ve la herramienta usándose mientras se habla, sin tocar nada. Dura lo mismo
// que el guion (unos 4:20) y sigue su orden: el país y sus ríos, río arriba, qué vigilar hoy, dos satélites que se
// contradicen, la alarma de sequía, el ciclón con su aviso, el expediente de Villa Riva (comprobaciones, sequía y
// retirar una fuente), la prueba del ajuste, las predicciones y el cierre sobre el país. Un cursor toca cada vista y
// cada botón; la cámara se mueve despacio para que ningún plano quede quieto; dentro de capas con desplazamiento
// propio (Preparar, huracanes) solo ilumina. Si alguien toca la página mientras tanto, el recorrido sigue igual.
// Todo son datos reales.
import { esc, LL } from "./datos";
import "./tour.css";

type Pad = { left: number; right: number; top: number; bottom: number };
type Cam = { flyTo: (o: object) => void; easeTo: (o: object) => void; fitBounds: (b: [[number, number], [number, number]], o: object) => void; getBearing: () => number };
export interface TourApi {
  map: () => Cam | null;
  yuna: [[number, number], [number, number]] | null;
  hatillo: [number, number] | null;
  pad: () => Pad;
  rivers: (names: string[] | null) => void;
  reset: () => void;
}
type Ctx = { tap: (sel: string) => Promise<boolean>; wait: (ms: number) => Promise<void>; go: (hash: string, ready: string) => Promise<void>; look: (sel: string, scale?: number) => void };
interface Scene { dur: number; text: string; run: (api: TourApi, c: Ctx) => Promise<void> }

const RM = () => matchMedia("(prefers-reduced-motion: reduce)").matches;
const vis = (sel: string) => [...document.querySelectorAll<HTMLElement>(sel)].find((x) => x.offsetParent || x.getClientRects().length);
const RIOS = ["Río Yuna", "Río Camú"];
const VR: [number, number] = [-69.908, 19.176];
let busy = false;
export const tourBusy = () => busy;

function scenes(): Scene[] {
  const ms = (n: number) => (RM() ? 0 : n);
  const home = (a: TourApi, d = 4500) => ({ center: [-70.3, 18.75], zoom: 7.3, pitch: 58, bearing: -16, padding: a.pad(), duration: ms(d), essential: true });
  // giro lento de la cámara: el plano nunca se queda quieto mientras se habla
  const drift = (a: TourApi, deg: number, d: number) => { const m = a.map(); if (m) m.easeTo({ bearing: m.getBearing() + deg, duration: ms(d), easing: (t: number) => t, essential: true }); };
  const prepClose = async (c: Ctx) => { c.look("", 1); if (vis("[data-prepq].on")) await c.tap("[data-prepq]"); };
  const sdii = async (c: Ctx) => { if (vis('[data-q="fuerte"].on') && vis("#s13-h")) return; await c.tap('[data-q="fuerte"]'); await c.wait(400); await c.tap("#m-btn"); await c.wait(450); await c.tap('.menu .mi[data-v="SDII"]'); await c.wait(700); };
  return [
    // 0:00 · el problema: el país y sus dos extremos
    { dur: 12000, text: LL("Toca 3D: el país, con su relieve", "Tap 3D: the country, with its relief"),
      run: async (a, c) => { a.reset(); await c.wait(400); await c.tap('[data-cam="3d"]'); await c.wait(900); a.map()?.flyTo(home(a, 5500)); await c.wait(5800); drift(a, 14, 5500); } },
    { dur: 23000, text: LL("El Yuna y el Camú, hasta Villa Riva", "The Yuna and the Camú, down to Villa Riva"),
      run: async (a, c) => {
        a.rivers(RIOS);
        if (a.yuna) a.map()?.fitBounds(a.yuna, { padding: a.pad(), pitch: 60, bearing: -24, duration: ms(5000), essential: true });
        await c.wait(7500);
        a.map()?.flyTo({ center: VR, zoom: 9.6, pitch: 64, bearing: 10, padding: a.pad(), duration: ms(5500), essential: true });
        await c.wait(6000); drift(a, 30, 9000);
      } },
    // 0:35 · la solución: río arriba no llueve igual
    { dur: 15000, text: LL("Río arriba: la presa de Hatillo", "Upstream: the Hatillo dam"),
      run: async (a, c) => {
        if (a.hatillo) a.map()?.flyTo({ center: a.hatillo, zoom: 9.8, pitch: 66, bearing: -30, padding: a.pad(), duration: ms(6000), essential: true });
        await c.wait(6500); drift(a, 22, 8000);
      } },
    { dur: 25000, text: LL("¿Qué municipio vigilar hoy?", "Which municipality to watch today?"),
      run: async (a, c) => {
        a.rivers(null);
        await c.tap("[data-prepq]"); await c.wait(1800); c.look(".prep-over .pb-head", 1);
        await c.wait(7000); c.look(".prep-over .pb-list", 1);
        await c.wait(8000); c.look(".prep-over .pb-list li:first-child", 1);
      } },
    // 1:15 · el descubrimiento: dos satélites, dos historias
    { dur: 10000, text: LL("Toca IMERG: la lluvia se intensifica", "Tap IMERG: rain is intensifying"),
      run: async (a, c) => { await prepClose(c); a.map()?.flyTo(home(a)); await sdii(c); await c.tap('[data-show="IMERG"]'); } },
    { dur: 17000, text: LL("Toca CHIRPS: se debilita. Míralo año a año", "Tap CHIRPS: it weakens. Watch it year by year"),
      run: async (_a, c) => { await c.tap('[data-show="CHIRPS"]'); await c.wait(5200); await c.tap(".wx-play"); await c.wait(8500); await c.tap(".wx-play"); await c.wait(500); await c.tap(".wx-trendbtn"); } },
    { dur: 9000, text: LL("Veredicto: dónde se contradicen", "Verdict: where they contradict"),
      run: async (a, c) => { await c.tap('[data-show="acuerdo"]'); a.map()?.flyTo({ center: [-70.45, 18.95], zoom: 8.1, pitch: 55, bearing: -10, padding: a.pad(), duration: ms(5000), essential: true }); await c.wait(5200); drift(a, 8, 3500); } },
    { dur: 12000, text: LL("Sequía: la alarma depende del satélite", "Drought: the alarm depends on the satellite"),
      run: async (_a, c) => { c.look("", 1); await c.go("#auditoria", "#au-kpi .au-lead"); await c.wait(500); c.look("#au-kpi", 1.3); } },
    // 2:00 · la demostración: el caso del Yuna
    { dur: 20000, text: LL("Si es un ciclón: el aviso del NHC, 103 h antes", "If it is a cyclone: the NHC warning, 103 h ahead"),
      run: async (_a, c) => {
        c.look("", 1); await c.go("#tendencias", "#sty-btn"); await c.wait(900);
        await c.tap("#sty-btn"); await c.wait(500); await c.tap('.menu .mi[data-v="ciclones"]'); await c.wait(2400);
        await c.tap('[data-cy-yuna="yuna"]');
      } },
    { dur: 18000, text: LL("Villa Riva: qué comprobar primero", "Villa Riva: what to check first"),
      run: async (_a, c) => {
        c.look("", 1); await c.tap("[data-prepq]"); await c.wait(1800);
        await c.tap('.prep-over [data-pick="villa-riva"]'); await c.wait(1500); c.look(".prep-over .prep-cards .prep-card", 1);
        await c.wait(7000); c.look(".prep-over .prep-tasks", 1);
      } },
    { dur: 12000, text: LL("Sequía: 90 días de lluvia frente a 24 años", "Drought: 90 days of rain against 24 years"),
      run: async (_a, c) => { c.look(".prep-over .prep-cards .prep-card:last-child", 1); } },
    { dur: 25000, text: LL("Retira una fuente: recalcula su respaldo", "Remove a source: it recalculates its support"),
      run: async (_a, c) => {
        c.look(".prep-over .prep-sources", 1); await c.wait(3500);
        await c.tap('.prep-over .source-toggle:has([data-source="ERA5"])'); await c.wait(600);
        c.look(".prep-over .prep-sources", 1); await c.wait(5000);
        c.look(".prep-over .prep-cards", 1); await c.wait(9000);
        // se devuelve la fuente para no dejar el expediente cambiado
        c.look(".prep-over .prep-sources", 1); await c.wait(1200);
        if (vis('.prep-over [data-source="ERA5"]:not(:checked)')) await c.tap('.prep-over .source-toggle:has([data-source="ERA5"])');
      } },
    // 3:15 · el avance: ponemos a prueba nuestras propias hipótesis
    { dur: 15000, text: LL("¿Y si IMERG contara bien los días de lluvia?", "What if IMERG counted rain days right?"),
      run: async (_a, c) => { await prepClose(c); await sdii(c); if (!vis("#s13-h.on")) await c.tap("#s13-h"); await c.wait(900); c.look(".adj-res", 1); } },
    { dur: 15000, text: LL("43 predicciones escritas antes de calcular. 16 fallaron", "43 predictions written before computing. 16 failed"),
      run: async (_a, c) => { c.look("", 1); if (vis("#s13-h.on")) await c.tap("#s13-h"); await c.go("#respuesta", ".rs-preds"); await c.wait(500); c.look(".rs-preds", 1); } },
    // 3:45 · el cierre, sobre el país
    { dur: 32000, text: LL("Investigar el agua para preparar a nuestra gente", "Investigating water to prepare our people"),
      run: async (a, c) => {
        c.look("", 1); await c.go("#tendencias", "#sty-btn"); await c.wait(1200);
        if (!vis('[data-cam="3d"][aria-checked="true"]')) await c.tap('[data-cam="3d"]');
        await c.wait(900); a.rivers(RIOS); a.map()?.flyTo(home(a, 6000)); await c.wait(6500); drift(a, 60, 23000);
      } },
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
      el.scrollIntoView({ block: inOverlay && el.getBoundingClientRect().height > innerHeight * 0.5 ? "start" : "center", behavior: RM() ? "auto" : "smooth" });
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
    let r = el.getBoundingClientRect();
    if (r.bottom > innerHeight - 200 || r.top < 70) { el.scrollIntoView({ block: "center", behavior: RM() ? "auto" : "smooth" }); await wait(RM() ? 0 : 650); r = el.getBoundingClientRect(); }
    const x = r.left + Math.min(r.width / 2, 40), y = r.top + r.height / 2;
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

  let capT = 0, idleT = 0;
  const wake = () => { root.classList.remove("idle"); clearTimeout(idleT); idleT = window.setTimeout(() => root.classList.add("idle"), 2500); };
  document.addEventListener("pointermove", wake); wake();
  const caption = (t: string, stay = false) => {
    clearTimeout(capT); cap.classList.remove("gone");
    if (!stay) capT = window.setTimeout(() => cap.classList.add("gone"), 5500);
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
    clearTimeout(capT); cap.classList.remove("gone");
    cap.innerHTML = `<span class="end">${esc(LL("Ahora, explóralo tú.", "Now, explore it yourself."))}</span> <a href="#tendencias">${esc(LL("Ir al mapa", "Go to the map"))}</a>`;
    cap.classList.add("in"); paused = true; syncPlay();
  };
  const stop = () => {
    clearTimeout(timer); token++; look("", 1);
    try { api.rivers(null); } catch { /* el mapa ya no existe */ }
    clearTimeout(capT); clearTimeout(idleT); document.removeEventListener("pointermove", wake);
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
