// Panel que en el teléfono es una hoja inferior (como Apple Maps / Windy): asoma, media y completa.
// Se arrastra desde el asa o desde la cabecera; un toque alterna entre asomada y media.
// En escritorio es un panel lateral que se pliega a su cabecera.
export type SheetState = "peek" | "half" | "full";
export const isPhone = () => innerWidth < 760;
export const PEEK = 172;

export function bottomSheet(el: HTMLElement, handles: HTMLElement[], onChange: (s: SheetState) => void) {
  let state: SheetState = isPhone() ? "peek" : "half";
  const H = () => ({ peek: PEEK, half: Math.round(innerHeight * 0.58), full: innerHeight - 60 });
  const apply = (anim = true, notify = true) => {
    el.dataset.state = state;
    if (!isPhone()) { el.style.height = ""; if (notify) onChange(state); return; }
    el.style.transition = anim ? "" : "none";
    el.style.height = `${H()[state]}px`;
    if (notify) onChange(state);
  };
  const set = (s: SheetState) => { state = s; apply(); };

  let y0 = 0, h0 = 0, t0 = 0, dragging = false, moved = 0;
  const down = (e: PointerEvent) => {
    if ((e.target as HTMLElement).closest("select, a, button:not(.wx-grab), input")) return;
    dragging = true; moved = 0; y0 = e.clientY; t0 = performance.now(); h0 = el.getBoundingClientRect().height;
    try { (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId); } catch { /* puntero sintético */ }
  };
  const move = (e: PointerEvent) => {
    if (!dragging || !isPhone()) return;
    moved = Math.max(moved, Math.abs(e.clientY - y0));
    if (moved < 6) return;
    el.style.transition = "none";
    el.style.height = `${Math.min(H().full, Math.max(PEEK - 40, h0 + (y0 - e.clientY)))}px`;
  };
  const up = (e: PointerEvent) => {
    if (!dragging) return;
    dragging = false;
    if (moved < 6) { set(state === "half" ? "peek" : "half"); return; }
    const h = el.getBoundingClientRect().height, v = (y0 - e.clientY) / Math.max(1, performance.now() - t0); // px/ms, + hacia arriba
    const hs = H();
    const target = h + v * 220; // un gesto rápido llega más lejos
    state = (Object.keys(hs) as SheetState[]).reduce((a, b) => (Math.abs(hs[b] - target) < Math.abs(hs[a] - target) ? b : a));
    apply();
  };
  handles.forEach((h) => {
    h.addEventListener("pointerdown", down);
    h.addEventListener("pointermove", move);
    h.addEventListener("pointerup", up);
    h.addEventListener("pointercancel", () => { dragging = false; apply(); });
  });
  apply(false, false);
  return { set, get state() { return state; }, refresh: () => apply(false) };
}
