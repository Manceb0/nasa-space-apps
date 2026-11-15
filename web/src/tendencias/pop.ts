// Ventana emergente anclada a un elemento: entra con el mismo movimiento que los menús, se cierra con Esc,
// al tocar fuera o al elegir una acción. Las acciones son enlaces o botones con data-act.
import { esc, LL } from "./datos";

let closeCur: (() => void) | null = null;
const RM = () => matchMedia("(prefers-reduced-motion: reduce)").matches;

export function openPop(anchor: HTMLElement, html: string, onAct: (act: string) => void, title = "") {
  closeCur?.();
  const m = document.createElement("div");
  m.className = "menu pop";
  m.setAttribute("role", "dialog");
  if (title) m.setAttribute("aria-label", title);
  m.innerHTML = `<button class="pop-x" aria-label="${esc(LL("Cerrar", "Close"))}"><svg viewBox="0 0 16 16" aria-hidden="true"><path d="M4 4l8 8M12 4l-8 8" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg></button>${html}`;
  document.body.appendChild(m);
  const r = anchor.getBoundingClientRect(), w = Math.min(380, innerWidth - 24);
  m.style.width = `${w}px`;
  m.style.left = `${Math.max(12, Math.min(r.left, innerWidth - w - 12))}px`;
  const below = innerHeight - r.bottom - 12;
  if (below < 300 && r.top > below) { m.style.bottom = `${innerHeight - r.top + 8}px`; m.dataset.up = "1"; } else m.style.top = `${r.bottom + 8}px`;
  m.style.maxHeight = `${Math.max(220, Math.min(560, (m.dataset.up ? r.top : below) - 8))}px`;
  requestAnimationFrame(() => m.classList.add("in"));
  anchor.setAttribute("aria-expanded", "true");
  const done = () => {
    if (closeCur !== done) return;
    closeCur = null;
    anchor.setAttribute("aria-expanded", "false");
    document.removeEventListener("pointerdown", outside, true);
    document.removeEventListener("keydown", key);
    m.classList.remove("in"); m.classList.add("out");
    setTimeout(() => m.remove(), RM() ? 0 : 160);
  };
  const outside = (e: Event) => { if (!m.contains(e.target as Node) && !anchor.contains(e.target as Node)) done(); };
  const key = (e: KeyboardEvent) => { if (e.key === "Escape") { done(); anchor.focus(); } };
  closeCur = done;
  document.addEventListener("pointerdown", outside, true);
  document.addEventListener("keydown", key);
  m.addEventListener("click", (e) => {
    const el = e.target as Element;
    if (el.closest(".pop-x")) { done(); anchor.focus(); return; }
    const a = el.closest<HTMLElement>("[data-act]");
    if (a) { done(); onAct(a.dataset.act!); }
  });
  m.querySelector<HTMLElement>("[data-act]")?.focus({ preventScroll: true });
}
