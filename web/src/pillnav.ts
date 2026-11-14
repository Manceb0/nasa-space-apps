// PillNav, portado de React Bits (variante JS + CSS) a TypeScript sin React.
// Conserva: burbuja del logo que gira al pasar, barra de vidrio, relleno que sube con la etiqueta rodando
// (hoverEffect "fill") y el punto que se desliza hasta la página activa (indicator "dot").
import "./pillnav.css";

export interface PillItem { label: string; short?: string; href: string; key: string }

export function pillNav(opts: { logo: string; logoAlt: string; logoHref: string; items: PillItem[]; extra?: string; ariaLabel: string }): string {
  const face = (it: PillItem) => `<span class="pn-long">${it.label}</span>${it.short ? `<span class="pn-short">${it.short}</span>` : ""}`;
  return `
    <nav class="pill-nav" data-layout="split" data-items="plain" aria-label="${opts.ariaLabel}">
      <span class="pill-nav__logo pill-nav__surface">
        <a class="pill-nav__logo-link" href="${opts.logoHref}" aria-label="${opts.logoAlt}"><span class="pill-nav__mark">${opts.logo}</span></a>
        <span class="pill-nav__rim"></span>
      </span>
      <div class="pill-nav__bar pill-nav__surface">
        <div class="pill-nav__track">
          <ul class="pill-nav__list">
            ${opts.items.map((it) => `
            <li class="pill-nav__slot">
              <a class="pill-nav__item" href="${it.href}" data-nav="${it.key}">
                <span class="pill-nav__fill" aria-hidden="true"></span>
                <span class="pill-nav__face">${face(it)}</span>
                <span class="pill-nav__face-alt" aria-hidden="true">${face(it)}</span>
              </a>
            </li>`).join("")}
          </ul>
          <span class="pill-nav__dot" aria-hidden="true"></span>
        </div>
        <span class="pill-nav__rim"></span>
      </div>
      ${opts.extra ?? ""}
    </nav>`;
}

/** Medidas, hover y el punto deslizante. Se llama una vez tras pintar el menú. */
export function wirePillNav(root: HTMLElement): { setActive: (key: string) => void } {
  const nav = root.querySelector<HTMLElement>(".pill-nav")!;
  const track = nav.querySelector<HTMLElement>(".pill-nav__track")!;
  const dot = nav.querySelector<HTMLElement>(".pill-nav__dot")!;
  const slots = [...nav.querySelectorAll<HTMLElement>(".pill-nav__slot")];
  let active = "";

  const measure = () => slots.forEach((s) => {
    const reach = Math.ceil(2 * Math.sqrt((s.offsetWidth / 2) ** 2 + s.offsetHeight ** 2)) + 2;
    s.style.setProperty("--pn-fill", `${reach}px`);
  });
  const place = () => {
    const a = slots.find((s) => s.querySelector<HTMLElement>("[data-nav]")!.dataset.nav === active);
    if (!a) { dot.style.opacity = "0"; return; }
    dot.style.opacity = "1";
    dot.style.transform = `translate3d(${a.offsetLeft + a.offsetWidth / 2}px, 0, 0)`;
  };
  slots.forEach((s) => {
    s.addEventListener("pointerenter", (e) => { if ((e as PointerEvent).pointerType !== "touch") s.setAttribute("data-hover", ""); });
    s.addEventListener("pointerleave", () => s.removeAttribute("data-hover"));
    s.addEventListener("focusin", (e) => { if ((e.target as Element).matches(":focus-visible")) s.setAttribute("data-hover", ""); });
    s.addEventListener("focusout", () => s.removeAttribute("data-hover"));
  });
  const mark = nav.querySelector<HTMLElement>(".pill-nav__mark")!;
  nav.querySelector(".pill-nav__logo-link")!.addEventListener("pointerenter", (e) => {
    if ((e as PointerEvent).pointerType === "touch" || mark.getAnimations().length || matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    mark.animate([{ transform: "rotate(0deg)" }, { transform: "rotate(360deg)" }], { duration: 900, easing: "cubic-bezier(0.65, 0, 0.25, 1)" });
  });
  new ResizeObserver(() => { measure(); place(); }).observe(track);
  document.fonts?.ready?.then(() => { measure(); place(); }).catch(() => {});
  measure();
  return {
    setActive(key: string) {
      active = key;
      slots.forEach((s) => {
        const a = s.querySelector<HTMLAnchorElement>("[data-nav]")!;
        if (a.dataset.nav === key) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current");
      });
      place();
    },
  };
}
