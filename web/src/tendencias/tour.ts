// Recorrido automático del pitch, como un vídeo hecho con la propia herramienta: un cursor visible va tocando los
// mismos botones que tocaría una persona, la cámara se acerca y centra lo que importa (lo demás se oscurece) y un
// subtítulo cuenta la historia. Conecta sequía e inundación de principio a fin: la disputa entre satélites, el Yuna,
// el ajuste, la llovizna y Puerto Rico, la alarma de sequía en la Auditoría, los huracanes, qué vigilar hoy,
// la respuesta del reto, cómo lo sabemos y, al final, cómo funciona el método. Todo lo que se ve son datos reales.
import { esc, LL } from "./datos";
import "./tour.css";

export interface TourApi {
  map: () => { flyTo: (o: object) => void; fitBounds: (b: [[number, number], [number, number]], o: object) => void } | null;
  yuna: [[number, number], [number, number]] | null;
  reset: () => void;
}
type Ctx = { tap: (sel: string) => Promise<boolean>; wait: (ms: number) => Promise<void>; go: (hash: string, ready: string) => Promise<void>; focus: (sel: string, scale?: number) => void };
interface Scene { dur: number; text: string; run: (api: TourApi, c: Ctx) => Promise<void> }

const RM = () => matchMedia("(prefers-reduced-motion: reduce)").matches;
const vis = (sel: string) => [...document.querySelectorAll<HTMLElement>(sel)].find((x) => x.offsetParent || x.getClientRects().length);
let busy = false;
export const tourBusy = () => busy;

function scenes(): Scene[] {
  return [
    { dur: 9000, text: LL("¿Está cambiando la lluvia en República Dominicana? Se lo preguntamos a los satélites de la NASA.", "Is rainfall changing in the Dominican Republic? We asked NASA's satellites."),
      run: async (a, c) => {
        a.reset(); await c.wait(500);
        await c.tap('[data-cam="3d"]'); await c.wait(900);
        a.map()?.flyTo({ center: [-70.3, 18.6], zoom: 7.4, pitch: 58, bearing: -16, duration: RM() ? 0 : 5000, essential: true });
      } },
    { dur: 12000, text: LL("Sequía. IMERG dice que hay más rachas secas: +19 % por década. CHIRPS, con pluviómetros, dice que menos: −22 %. Mismo país, direcciones opuestas.", "Drought. IMERG says dry spells are rising: +19 % per decade. CHIRPS, built with rain gauges, says they are falling: −22 %. Same country, opposite directions."),
      run: async (_a, c) => { await c.tap('[data-q="secos"]'); await c.wait(700); c.focus("#ans .vd", 1.8); await c.wait(4200); c.focus("#ans .cap-read", 1.6); } },
    { dur: 9000, text: LL("Las disputas caen donde más importa: la cuenca del Yuna y sus ríos, la que más se inunda del país.", "The disputes fall where it matters most: the Yuna basin and its rivers, the country's most flood-prone."),
      run: async (a, c) => { c.focus("", 1); if (a.yuna) a.map()?.fitBounds(a.yuna, { padding: 120, pitch: 55, bearing: -10, duration: RM() ? 0 : 3500, essential: true }); } },
    { dur: 12000, text: LL("Si IMERG contara los días como antes de 2018, casi todas las disputas desaparecen: de 117 celdas a 2.", "If IMERG counted days as it did before 2018, almost every dispute disappears: from 117 cells to 2."),
      run: async (a, c) => {
        a.map()?.flyTo({ center: [-70.3, 18.6], zoom: 7.4, pitch: 58, bearing: -16, duration: RM() ? 0 : 2500, essential: true });
        await c.tap('[data-per="seca"]'); await c.wait(500);
        if (!vis("#s13-h.on")) await c.tap("#s13-h");
        await c.wait(700); c.focus("#ans .adj-res", 1.8);
      } },
    { dur: 13000, text: LL("Lo que cambia es cómo IMERG cuenta la llovizna. En Puerto Rico, bajo el mismo satélite, 18 de 19 pluviómetros lo confirman.", "What changes is how IMERG counts drizzle. In Puerto Rico, under the same satellite, 18 of 19 rain gauges confirm it."),
      run: async (_a, c) => {
        c.focus("", 1);
        if (vis("#s13-h.on")) await c.tap("#s13-h");
        await c.tap('[data-per="anual"]'); await c.wait(400);
        await c.tap("[data-fig13]"); await c.wait(3200);
        document.querySelector("#s13-lb .hz-pr")?.scrollIntoView({ behavior: RM() ? "auto" : "smooth", block: "center" });
      } },
    { dur: 12000, text: LL("Y la alarma de sequía depende del satélite: de 3.111 meses con alarma, solo 275 fueron unánimes entre los cuatro productos.", "And the drought alarm depends on the satellite: of 3,111 months with an alarm, only 275 were unanimous across the four products."),
      run: async (_a, c) => {
        const d = document.querySelector<HTMLDialogElement>("#s13-lb"); if (d?.open) d.close();
        await c.go("#auditoria", "#au-kpi .au-lead"); await c.wait(600); c.focus("#au-kpi", 1.7); await c.wait(4500); c.focus("#au-cv", 1.05);
      } },
    { dur: 16000, text: LL("Inundación: dos lluvias, dos alertas. Con María, el boletín oficial del NHC ya la ponía cerca del Yuna 103 horas antes.", "Flood: two kinds of rain, two alerts. With María, the official NHC advisory already put it near the Yuna 103 hours ahead."),
      run: async (_a, c) => {
        await c.go("#tendencias", "#sty-btn"); await c.wait(900);
        await c.tap("#sty-btn"); await c.wait(500); await c.tap('.menu .mi[data-v="ciclones"]'); await c.wait(2200);
        await c.tap('[data-cy-yuna="yuna"]'); await c.wait(2400); c.focus(".cy-over .hx-top", 1.5); await c.wait(4500); c.focus(".cy-over .hx-time", 1.4);
      } },
    { dur: 12000, text: LL("Y hoy: qué municipio vigilar, con el pronóstico de dos modelos y la lluvia de 90 días frente a 24 años.", "And today: which municipality to watch, with two models' forecast and 90-day rain against 24 years."),
      run: async (_a, c) => { c.focus("", 1); await c.tap("[data-prepq]"); await c.wait(1500); c.focus(".prep-over .pb-head", 1.3); await c.wait(4000); c.focus(".prep-over .pb-row", 1.45); } },
    { dur: 11000, text: LL("La respuesta del reto: qué cambia, dónde, cuánto y si es significativo, en una sola vista.", "The challenge's answer: what changes, where, how much and whether it is significant, in one view."),
      run: async (_a, c) => { c.focus("", 1); await c.go("#respuesta", ".rs-four"); await c.wait(400); c.focus(".rs-four"); } },
    { dur: 10000, text: LL("Cómo lo sabemos: 34 predicciones escritas antes de calcular. 17 se cumplieron y 11 fallaron, y se publican igual.", "How we know: 34 predictions written before computing. 17 held and 11 failed, and both are published."),
      run: async (_a, c) => { c.focus(".rs-preds"); } },
    { dur: 10000, text: LL("Y para quien quiera el detalle: el método paso a paso, sobre una serie real.", "And for anyone who wants the detail: the method step by step, on a real series."),
      run: async (_a, c) => { await c.go("#metodo", ".mt-steps"); await c.wait(400); c.focus(".mt-steps"); } },
    { dur: 8000, text: LL("Stellar Horizons: datos de la NASA, comprobados antes de creerlos.", "Stellar Horizons: NASA data, checked before it is believed."),
      run: async (_a, c) => { c.focus("", 1); } },
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
      <button data-t="close" class="x">${esc(LL("Salir del recorrido", "Exit the tour"))}</button>
    </div>`;
  document.body.appendChild(root);
  document.body.classList.add("touring");
  const cap = root.querySelector<HTMLElement>(".tour-cap")!, bars = [...root.querySelectorAll<HTMLElement>(".tour-bars b")];
  const lens = root.querySelector<HTMLElement>(".tour-lens")!, cur = root.querySelector<HTMLElement>(".tour-cursor")!;
  let cx = innerWidth / 2, cy = innerHeight / 2;
  cur.style.transform = `translate(${cx}px, ${cy}px)`;
  const syncPlay = () => { root.querySelector('[data-t="play"]')!.innerHTML = paused ? '<svg viewBox="0 0 16 16"><path d="M5 3.5v9l7.5-4.5z" fill="currentColor"/></svg>' : '<svg viewBox="0 0 16 16"><rect x="4" y="3" width="3" height="10" rx="1.2" fill="currentColor"/><rect x="9" y="3" width="3" height="10" rx="1.2" fill="currentColor"/></svg>'; };

  // ── la cámara: centra y acerca lo que importa; el lente oscurece todo lo demás ──
  let lensT = 0;
  const hosts = () => [...document.querySelectorAll<HTMLElement>("#wx, #au")];
  const placeLens = (el: HTMLElement | null) => {
    if (!el) { lens.classList.remove("on"); return; }
    const r = el.getBoundingClientRect(), m = 10;
    Object.assign(lens.style, { left: `${r.left - m}px`, top: `${r.top - m}px`, width: `${r.width + 2 * m}px`, height: `${r.height + 2 * m}px` });
    lens.classList.add("on");
  };
  const focus = (sel: string, scale = 1.6) => {
    clearTimeout(lensT);
    hosts().forEach((h) => { h.style.transform = ""; });
    placeLens(null);
    if (!sel) return;
    const el = vis(sel); if (!el) return;
    const host = el.closest<HTMLElement>("#wx, #au");
    if (!host || RM() || scale <= 1.05) {
      el.scrollIntoView({ block: "center", behavior: RM() ? "auto" : "smooth" });
      lensT = window.setTimeout(() => placeLens(el), RM() ? 0 : 750);
      return;
    }
    el.scrollIntoView({ block: "center", behavior: "auto" });
    requestAnimationFrame(() => {
      const r = el.getBoundingClientRect(), w = host.getBoundingClientRect();
      const free = innerHeight - 230, sc = Math.min(scale, (innerWidth * 0.8) / r.width, (free * 0.85) / r.height);
      const ex = r.left + r.width / 2 - w.left, ey = r.top + r.height / 2 - w.top;
      const tx = innerWidth / 2 - w.left - sc * ex, ty = Math.max(70, free / 2) - w.top - sc * ey;
      host.style.transformOrigin = "0 0";
      host.style.transform = `translate(${tx.toFixed(1)}px, ${ty.toFixed(1)}px) scale(${sc.toFixed(3)})`;
      lensT = window.setTimeout(() => placeLens(el), 1450);
    });
  };

  // ── el cursor: viaja hasta el botón, marca el clic y lo pulsa de verdad ──
  const wait = (ms: number) => new Promise<void>((res) => setTimeout(res, ms));
  const tap = async (sel: string) => {
    const t = token, el = vis(sel);
    if (!el || t !== token) return false;
    const r = el.getBoundingClientRect(), x = r.left + Math.min(r.width / 2, 40), y = r.top + r.height / 2;
    const dist = Math.hypot(x - cx, y - cy), ms = RM() ? 0 : Math.min(900, 250 + dist * 0.6);
    cur.style.transition = `transform ${ms}ms cubic-bezier(.65, 0, .25, 1)`;
    cur.style.transform = `translate(${x}px, ${y}px)`; cx = x; cy = y;
    await wait(ms + 120);
    if (t !== token) return false;
    cur.classList.remove("hit"); void cur.offsetWidth; cur.classList.add("hit");
    el.classList.add("tour-press"); setTimeout(() => el.classList.remove("tour-press"), 260);
    await wait(180);
    if (t !== token) return false;
    el.click();
    return true;
  };
  const go = async (hash: string, ready: string) => {
    if (location.hash !== hash) { focus("", 1); location.hash = hash; }
    for (let k = 0; k < 60 && !vis(ready); k++) await wait(100);
    await wait(300);
  };
  const ctx = (): Ctx => { const t = token; return { tap, wait: (ms) => wait(ms), go, focus: (s, sc) => { if (t === token) focus(s, sc); } }; };

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
    clearTimeout(timer); token++; focus("", 1);
    cap.innerHTML = `<span class="end">${esc(LL("Fin del recorrido.", "End of the tour."))}</span> <a href="#tendencias">${esc(LL("Explorar por mi cuenta", "Explore on my own"))}</a>`;
    cap.classList.add("in"); paused = true; syncPlay();
  };
  const stop = () => { clearTimeout(timer); token++; focus("", 1); root.remove(); document.body.classList.remove("touring"); document.removeEventListener("keydown", key); stopCur = null; busy = false; };
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
