// Menú desplegable propio: cada opción explica qué es (una línea) y, si aplica, lleva el punto de su veredicto.
// Entra y sale con movimiento (opacidad y desplazamiento, opciones escalonadas), se maneja con teclado
// (flechas, Inicio/Fin, Intro, Esc) y con más de diez opciones trae un buscador.
import { esc, LL } from "./datos";

export interface Opt { value: string; label: string; hint?: string; color?: string; hollow?: boolean }

let close: (() => void) | null = null;
const RM = () => matchMedia("(prefers-reduced-motion: reduce)").matches;
const norm = (s: string) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

export function openMenu(anchor: HTMLElement, opts: Opt[], current: string, onPick: (v: string) => void, title = "") {
  close?.();
  const m = document.createElement("div");
  m.className = "menu";
  m.setAttribute("role", "dialog");
  if (title) m.setAttribute("aria-label", title);
  const search = opts.length > 10;
  m.innerHTML = `${title ? `<p class="menu-h">${esc(title)}</p>` : ""}
    ${search ? `<input class="menu-q" type="search" placeholder="${esc(LL("Buscar…", "Search…"))}" aria-label="${esc(LL("Buscar", "Search"))}" autocomplete="off">` : ""}
    <div class="menu-l" role="listbox">${opts.map((o, i) => `
      <button class="mi ${o.value === current ? "on" : ""}" role="option" aria-selected="${o.value === current}" data-v="${esc(o.value)}" data-k="${esc(norm(o.label))}" style="--i:${Math.min(i, 12)}">
        ${o.color ? `<i class="mi-d ${o.hollow ? "no" : ""}" style="--c:${o.color}"></i>` : ""}
        <span class="mi-t"><b>${esc(o.label)}</b>${o.hint ? `<small>${esc(o.hint)}</small>` : ""}</span>
        ${o.value === current ? '<svg class="mi-ok" viewBox="0 0 16 16" aria-hidden="true"><path d="M3.5 8.5l3 3 6-7" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>' : ""}
      </button>`).join("")}</div>`;
  document.body.appendChild(m);

  // Debajo del botón, o encima si no cabe; nunca fuera de la pantalla
  const place = () => {
    const r = anchor.getBoundingClientRect(), w = Math.min(Math.max(r.width, 300), innerWidth - 24);
    const left = Math.max(12, Math.min(r.left, innerWidth - w - 12));
    const below = innerHeight - r.bottom - 12, above = r.top - 12, up = below < 260 && above > below;
    const maxH = Math.max(160, Math.min(440, up ? above - 8 : below - 8));
    m.style.width = `${w}px`; m.style.left = `${left}px`; m.style.maxHeight = `${maxH}px`;
    if (up) { m.style.top = ""; m.style.bottom = `${innerHeight - r.top + 8}px`; m.dataset.up = "1"; }
    else { m.style.bottom = ""; m.style.top = `${r.bottom + 8}px`; delete m.dataset.up; }
  };
  place();
  anchor.setAttribute("aria-expanded", "true");
  requestAnimationFrame(() => m.classList.add("in"));

  const items = () => [...m.querySelectorAll<HTMLButtonElement>(".mi:not([hidden])")];
  const focusAt = (i: number) => { const l = items(); if (l.length) l[(i + l.length) % l.length].focus(); };
  const q = m.querySelector<HTMLInputElement>(".menu-q");
  // en pantallas táctiles no se enfoca el buscador: el teclado taparía la lista
  const touch = matchMedia("(pointer: coarse)").matches;
  ((touch ? null : q) ?? m.querySelector<HTMLButtonElement>(".mi.on") ?? items()[0])?.focus({ preventScroll: true });
  m.querySelector(".mi.on")?.scrollIntoView({ block: "center" });

  const done = (v?: string) => {
    if (close !== shut) return;
    close = null;
    anchor.setAttribute("aria-expanded", "false");
    document.removeEventListener("pointerdown", outside, true);
    removeEventListener("resize", shut);
    m.classList.remove("in");
    m.classList.add("out");
    setTimeout(() => m.remove(), RM() ? 0 : 160);
    anchor.focus({ preventScroll: true });
    if (v !== undefined && v !== current) onPick(v);
  };
  const shut = () => done();
  const outside = (e: Event) => { if (!m.contains(e.target as Node) && !anchor.contains(e.target as Node)) done(); };
  close = shut;
  document.addEventListener("pointerdown", outside, true);
  addEventListener("resize", shut);

  m.addEventListener("click", (e) => { const b = (e.target as Element).closest<HTMLButtonElement>(".mi"); if (b) done(b.dataset.v); });
  m.addEventListener("keydown", (e) => {
    const l = items(), i = l.indexOf(document.activeElement as HTMLButtonElement);
    if (e.key === "Escape") { e.preventDefault(); done(); }
    else if (e.key === "ArrowDown") { e.preventDefault(); focusAt(i + 1); }
    else if (e.key === "ArrowUp") { e.preventDefault(); if (i <= 0 && q) q.focus(); else focusAt(i - 1); }
    else if (e.key === "Home") { e.preventDefault(); focusAt(0); }
    else if (e.key === "End") { e.preventDefault(); focusAt(-1); }
    else if (e.key === "Enter" && document.activeElement === q) { e.preventDefault(); const f = items()[0]; if (f) done(f.dataset.v); }
    else if (e.key === "Tab") done();
  });
  q?.addEventListener("input", () => {
    const k = norm(q.value.trim());
    m.querySelectorAll<HTMLButtonElement>(".mi").forEach((b) => { b.hidden = !!k && !b.dataset.k!.includes(k); });
  });
}
