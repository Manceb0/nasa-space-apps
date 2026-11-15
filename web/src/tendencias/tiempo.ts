// Línea de tiempo al pie (como la de Windy): «Tendencia» muestra 2001–2024 resumido en una pendiente;
// tocar un año, arrastrar o darle a reproducir pasa al modo año a año.
import { esc, LL } from "./datos";

const PLAY = '<svg viewBox="0 0 20 20" aria-hidden="true"><path d="M6.5 4.5v11l9-5.5z" fill="currentColor"/></svg>';
const PAUSE = '<svg viewBox="0 0 20 20" aria-hidden="true"><path d="M6 4.5h2.8v11H6zM11.2 4.5H14v11h-2.8z" fill="currentColor"/></svg>';

export function timeline(root: HTMLElement, onPick: (i: number | null) => void) {
  const track = root.querySelector<HTMLElement>(".wx-track")!;
  const play = root.querySelector<HTMLButtonElement>(".wx-play")!;
  const trend = root.querySelector<HTMLButtonElement>(".wx-trendbtn")!;
  let yrs: number[] = [], idx: number | null = null, timer = 0;

  const paint = () => {
    root.dataset.mode = idx === null ? "trend" : "year";
    trend.classList.toggle("on", idx === null);
    trend.setAttribute("aria-pressed", String(idx === null));
    const knob = track.querySelector<HTMLElement>(".wx-knob")!;
    if (idx !== null) knob.style.left = `${(idx / Math.max(1, yrs.length - 1)) * 100}%`;
    knob.querySelector("b")!.textContent = idx === null ? "" : String(yrs[idx]);
    track.setAttribute("aria-valuenow", idx === null ? "" : String(yrs[idx]));
    track.setAttribute("aria-valuetext", idx === null ? LL("Tendencia 2001–2024", "Trend 2001–2024") : String(yrs[idx]));
    track.querySelectorAll<HTMLElement>(".tk").forEach((t, k) => t.classList.toggle("on", k === idx));
    play.innerHTML = timer ? PAUSE : PLAY;
    play.setAttribute("aria-label", timer ? LL("Pausa", "Pause") : LL("Reproducir año a año", "Play year by year"));
  };
  const pick = (i: number | null) => { idx = i === null ? null : Math.max(0, Math.min(yrs.length - 1, i)); paint(); onPick(idx); };
  const stop = () => { if (timer) { clearInterval(timer); timer = 0; paint(); } };

  const setYears = (y: number[]) => {
    const cur = idx === null ? null : yrs[idx];
    yrs = y;
    track.innerHTML = `${yrs.map((yr, k) => `<span class="tk ${k === 0 || k === yrs.length - 1 || yr % 5 === 0 ? "lb" : ""}" data-y="${yr}"><i></i>${k === 0 || k === yrs.length - 1 || yr % 5 === 0 ? `<em>${yr}</em>` : ""}</span>`).join("")}<span class="wx-knob"><b></b></span>`;
    track.setAttribute("aria-valuemin", String(yrs[0])); track.setAttribute("aria-valuemax", String(yrs[yrs.length - 1]));
    if (cur !== null) { const k = yrs.indexOf(cur); idx = k >= 0 ? k : Math.min(idx!, yrs.length - 1); }
    paint();
  };
  const fromX = (x: number) => {
    const r = track.getBoundingClientRect();
    return Math.round(((x - r.left) / r.width) * (yrs.length - 1));
  };
  let pressing = false;
  track.addEventListener("pointerdown", (e) => { pressing = true; stop(); try { track.setPointerCapture(e.pointerId); } catch { /* puntero sintético */ } pick(fromX(e.clientX)); });
  track.addEventListener("pointermove", (e) => { if (pressing) { const k = fromX(e.clientX); if (k !== idx) pick(k); } });
  track.addEventListener("pointerup", () => { pressing = false; });
  track.addEventListener("keydown", (e) => {
    const k = idx ?? -1;
    if (e.key === "ArrowRight") pick(k + 1);
    else if (e.key === "ArrowLeft") pick(k <= 0 ? 0 : k - 1);
    else if (e.key === "Home") pick(0);
    else if (e.key === "End") pick(yrs.length - 1);
    else if (e.key === "Escape") pick(null);
    else return;
    e.preventDefault(); stop();
  });
  play.addEventListener("click", () => {
    if (timer) { stop(); return; }
    if (idx === null || idx === yrs.length - 1) pick(0);
    timer = window.setInterval(() => { if (idx === null || idx >= yrs.length - 1) { stop(); return; } pick(idx + 1); }, 900);
    paint();
  });
  trend.addEventListener("click", () => { stop(); pick(null); });
  trend.innerHTML = esc(LL("Tendencia", "Trend"));
  return { setYears, pick, stop, get index() { return idx; } };
}
