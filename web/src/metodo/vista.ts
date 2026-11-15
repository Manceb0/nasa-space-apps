// Cómo funciona: el método en acción. Una misma serie real (intensidad de la lluvia, todo el país, IMERG y CHIRPS)
// pasa por los cuatro pasos que la herramienta aplica a todo: el dato, la tendencia, si es real, y el testigo.
// Debajo, la regla del veredicto como una matriz de dos preguntas. El glosario y los límites quedan plegados.
import { esc, LL, loadTrends, num, sgn, type Sel, type TrendData } from "../tendencias/datos";
import { PROD_COLOR } from "../tendencias/graficas";
import "./metodo.css";
import { hallazgo, type Hallazgos } from "../tendencias/hallazgo";
import { load } from "../data";

const SEL: Sel = { ind: "SDII", per: "anual", reg: "DO", src: "IMERG" };
const median = (a: number[]) => { const s = [...a].sort((x, y) => x - y), m = s.length >> 1; return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2; };

function chart(d: TrendData, stage: number) {
  const yrs = d.years(SEL), W = 560, H = 250, L = 40, R = 16, T = 16, B = 28;
  const ser = (p: string) => (d.series(SEL, p) ?? []).map((v, i) => ({ x: yrs[i], y: v })).filter((p): p is { x: number; y: number } => p.y !== null && Number.isFinite(p.y));
  const a = ser("IMERG"), b = ser("CHIRPS"), all = [...a, ...(stage >= 4 ? b : [])].map((p) => p.y);
  const lo = Math.floor(Math.min(...all) - .5), hi = Math.ceil(Math.max(...all) + .5);
  const x = (v: number) => L + (v - yrs[0]) / (yrs[yrs.length - 1] - yrs[0]) * (W - L - R), y = (v: number) => T + (1 - (v - lo) / (hi - lo)) * (H - T - B);
  const line = (pts: { x: number; y: number }[], perDecade: number) => { const m = perDecade / 10, c = median(pts.map((p) => p.y - m * p.x)); return (xx: number) => m * xx + c; };
  const dots = (pts: { x: number; y: number }[], col: string) => pts.map((p) => `<circle cx="${x(p.x).toFixed(1)}" cy="${y(p.y).toFixed(1)}" r="4" fill="${col}"><title>${p.x}: ${num(p.y, 1)} mm</title></circle>`).join("");
  const seg = (f: (v: number) => number, col: string, w = 2.5) => `<path d="M${x(yrs[0]).toFixed(1)},${y(f(yrs[0])).toFixed(1)}L${x(yrs[yrs.length - 1]).toFixed(1)},${y(f(yrs[yrs.length - 1])).toFixed(1)}" stroke="${col}" stroke-width="${w}" stroke-linecap="round"/>`;
  const tI = d.tr(SEL, "IMERG")!, tC = d.tr(SEL, "CHIRPS")!, fI = line(a, tI.pendiente_decada), fC = line(b, tC.pendiente_decada);
  let fan = "";
  if (stage === 3) {
    const xc = median(a.map((p) => p.x)), yc = fI(xc), k = (s: number, xx: number) => yc + s / 10 * (xx - xc);
    const [s0, s1] = tI.ic95, x0 = yrs[0], x1 = yrs[yrs.length - 1];
    fan = `<path d="M${x(x0)},${y(k(s0, x0))}L${x(x1)},${y(k(s0, x1))}L${x(x1)},${y(k(s1, x1))}L${x(x0)},${y(k(s1, x0))}Z" fill="#ffffff" fill-opacity=".14"/>`;
  }
  const ticks = [yrs[0], 2008, 2016, yrs[yrs.length - 1]];
  const ys = [lo, (lo + hi) / 2, hi];
  return `<svg class="mt-chart" viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(LL("Intensidad de la lluvia en República Dominicana, 2001-2024", "Rain intensity in the Dominican Republic, 2001-2024"))}">
    ${ys.map((v) => `<text x="${L - 8}" y="${y(v) + 4}" text-anchor="end" fill="#949494" font-size="11">${num(v, 0)}</text>`).join("")}
    ${ticks.map((t) => `<text x="${x(t)}" y="${H - 6}" text-anchor="middle" fill="#949494" font-size="11">${t}</text>`).join("")}
    ${fan}
    ${stage >= 4 ? dots(b, PROD_COLOR.CHIRPS) + seg(fC, PROD_COLOR.CHIRPS) : ""}
    ${dots(a, stage >= 2 ? "#8a9099" : "#ffffff")}
    ${stage >= 2 ? seg(fI, "#ffffff", 3) : ""}
  </svg>`;
}

export async function viewMethodV2(view: HTMLElement, glossary: [string, string][], limitsH: string, limits: string) {
  document.body.classList.remove("wx-on");
  const [d, hz] = await Promise.all([loadTrends(), load<Hallazgos>("tendencias/hallazgos.json").catch(() => null)]);
  const tI = d.tr(SEL, "IMERG")!, tC = d.tr(SEL, "CHIRPS")!;
  const pd = (v: number) => `${sgn(v, 0)} %`;
  const steps = [
    { h: LL("1 · El dato", "1 · The data"), big: LL(`${num(tI.media, 1)} mm`, `${num(tI.media, 1)} mm`),
      s: LL("Lluvia media en un día lluvioso, cada año desde 2001. NASA GPM IMERG, todo el país.", "Average rain on a rainy day, every year since 2001. NASA GPM IMERG, whole country.") },
    { h: LL("2 · La tendencia", "2 · The trend"), big: LL(`${pd(tI.pendiente_pct_decada)} por década`, `${pd(tI.pendiente_pct_decada)} per decade`),
      s: LL("La pendiente de Theil-Sen: la mediana de todas las pendientes entre pares de años. Un año extremo no la arrastra.", "The Theil-Sen slope: the median of every slope between pairs of years. One extreme year cannot drag it.") },
    { h: LL("3 · ¿Es real?", "3 · Is it real?"), big: `p = ${num(tI.p, 3)}`,
      s: LL(`Mann-Kendall, corregido por autocorrelación. La banda es el intervalo del 95 % de la pendiente: no incluye el cero.`, `Mann-Kendall, corrected for autocorrelation. The band is the 95 % interval of the slope: it excludes zero.`) },
    { h: LL("4 · El testigo", "4 · The witness"), big: LL(`CHIRPS: ${pd(tC.pendiente_pct_decada)}`, `CHIRPS: ${pd(tC.pendiente_pct_decada)}`), warn: true,
      s: LL(`Otro producto, con pluviómetros, dice lo contrario (p = ${num(tC.p, 3)}). Veredicto: en disputa. Una sola fuente no basta.`, `Another product, built with rain gauges, says the opposite (p = ${num(tC.p, 3)}). Verdict: disputed. One source is not enough.`) },
  ];
  const cls = d.V.clases;
  const cell = (k: string, title: string) => `<div class="mt-cell" style="--c:${cls[k]?.color ?? "#888"}"><b>${esc(title)}</b><span>${esc(cls[k]?.descripcion ?? "")}</span></div>`;
  view.innerHTML = `<div class="mt">
    <header class="mt-head">
      <h1>${esc(LL("Del dato de la NASA al veredicto", "From NASA data to a verdict"))}</h1>
      <p>${esc(LL("Cuatro pasos, aplicados igual a cada variable, provincia y época. Aquí, con una serie real.", "Four steps, applied the same way to every variable, province and season. Here, on one real series."))}</p>
    </header>
    <ol class="mt-steps">${steps.map((st, i) => `<li class="mt-step" style="--i:${i}">
      <h2>${esc(st.h)}</h2>
      <p class="mt-big ${st.warn ? "mt-warn" : ""}">${esc(st.big)}</p>
      ${chart(d, i + 1)}
      <p class="mt-s">${esc(st.s)}</p>
    </li>`).join("")}</ol>
    <section class="mt-rule" aria-labelledby="mt-rule-h">
      <h2 id="mt-rule-h">${esc(LL("La regla del veredicto", "The verdict rule"))}</h2>
      <p class="mt-rule-s">${esc(LL("Dos productos independientes en lo posible, dos preguntas: ¿van en la misma dirección? ¿alguno es significativo?", "Two products, as independent as possible, two questions: do they point the same way? Is either significant?"))}</p>
      <div class="mt-matrix">
        ${cell("robusta", LL("Robusta", "Robust"))}${cell("consistente", LL("Consistente", "Consistent"))}${cell("en disputa", LL("En disputa", "Disputed"))}${cell("sin señal detectable", LL("Sin señal detectable", "No detectable signal"))}
      </div>
      <p class="mt-rule-s">${esc(LL("En provincias, la significancia se corrige por las 32 pruebas a la vez (Benjamini-Hochberg, q ≤ 0,10).", "In provinces, significance is corrected for all 32 tests at once (Benjamini-Hochberg, q ≤ 0.10)."))}</p>
    </section>
    <div class="mt-hz">${hallazgo(hz)}</div>
    <details class="mt-more"><summary>${esc(LL("Glosario", "Glossary"))}</summary><dl>${glossary.map(([a, b]) => `<dt>${esc(a)}</dt><dd>${esc(b)}</dd>`).join("")}</dl></details>
    <details class="mt-more"><summary>${esc(limitsH)}</summary><p>${esc(limits)}</p></details>
  </div>`;
}
