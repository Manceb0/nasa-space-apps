// Portada al abrir: el logo en grande con la estrella girando y dos salidas, ver el recorrido o explorar. Al elegir,
// solo la estrella gira más rápido y se expande hasta llenar la pantalla; debajo ya está la herramienta.
// No aparece con navegadores automatizados (pruebas e inspector) salvo con ?intro=1.
import { getLang } from "./i18n";
import "./intro.css";

const L = (es: string, en: string) => (getLang() === "es" ? es : en);
const STAR = '<path d="M16 2.5l2.3 8.2 8.2 2.3-8.2 2.3L16 23.5l-2.3-8.2-8.2-2.3 8.2-2.3z" fill="#f2b33d"/>';

export function intro(go: (tour: boolean) => void, auto: boolean) {
  const q = new URLSearchParams(location.search).get("intro");
  if (q === "0" || (navigator.webdriver && q !== "1")) return false;
  const rm = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const el = document.createElement("div");
  el.className = "intro";
  el.setAttribute("role", "dialog");
  el.setAttribute("aria-label", "Stellar Horizons");
  el.innerHTML = `
    <div class="in-mark" aria-hidden="true">
      <svg class="in-star" viewBox="2 0 28 26">${STAR}</svg>
      <svg class="in-arc" viewBox="0 0 32 8"><path d="M2.5 6.5c7.5-4.6 19.5-4.6 27 0" stroke="#fff" stroke-width="1.1" fill="none" stroke-linecap="round"/></svg>
    </div>
    <h1 class="in-name">Stellar Horizons</h1>
    <p class="in-tag">${L("Investigar el agua para preparar a nuestra gente.", "Investigating water to prepare our people.")}</p>
    <div class="in-go">
      <button class="in-tour" data-in="tour"><svg viewBox="0 0 16 16" aria-hidden="true"><path d="M5 3.5v9l7.5-4.5z" fill="currentColor" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"/></svg>${L("Ver el recorrido", "Watch the tour")}</button>
      <button class="in-free" data-in="free">${L("Explorar", "Explore")}</button>
    </div>`;
  document.body.appendChild(el);
  document.body.classList.add("intro-on");
  const star = el.querySelector<SVGElement>(".in-star")!;
  let done = false;
  const leave = (tour: boolean) => {
    if (done) return; done = true;
    document.removeEventListener("keydown", key);
    const finish = () => { el.remove(); document.body.classList.remove("intro-on"); go(tour); };
    if (rm) { finish(); return; }
    // la estrella toma el giro desde donde va y crece hasta cubrir la pantalla
    const mt = getComputedStyle(star).transform, r = star.getBoundingClientRect();
    const m = /matrix\(([^)]+)\)/.exec(mt)?.[1].split(",").map(Number);
    const deg = m ? (Math.atan2(m[1], m[0]) * 180) / Math.PI : 0, a0 = deg < 0 ? deg + 360 : deg;
    const big = (Math.hypot(innerWidth, innerHeight) / Math.min(r.width, r.height)) * 2.6;
    star.style.animation = "none";
    el.classList.add("out");
    const a = star.animate([
      { transform: `rotate(${a0.toFixed(1)}deg) scale(1)`, opacity: 1 },
      { transform: `rotate(${(a0 + 150).toFixed(1)}deg) scale(1.4)`, opacity: 1, offset: 0.35 },
      { transform: `rotate(${(a0 + 320).toFixed(1)}deg) scale(${(big * 0.7).toFixed(2)})`, opacity: 1, offset: 0.78 },
      { transform: `rotate(${(a0 + 390).toFixed(1)}deg) scale(${big.toFixed(2)})`, opacity: 0 },
    ], { duration: 1500, easing: "cubic-bezier(.55, 0, .35, 1)", fill: "forwards" });
    el.animate([{ backgroundColor: "rgb(0, 0, 0)" }, { backgroundColor: "rgba(0, 0, 0, 0)" }], { duration: 500, delay: 1050, easing: "ease-out", fill: "forwards" });
    setTimeout(() => go(tour), 900);
    a.finished.then(() => { el.remove(); document.body.classList.remove("intro-on"); });
  };
  const key = (e: KeyboardEvent) => { if (e.key === "Enter") leave(true); else if (e.key === "Escape") leave(false); };
  document.addEventListener("keydown", key);
  el.addEventListener("click", (e) => { const b = (e.target as Element).closest<HTMLElement>("[data-in]"); if (b) leave(b.dataset.in === "tour"); });
  if (auto) setTimeout(() => leave(true), 2200);
  return true;
}
