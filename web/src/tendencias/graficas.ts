// Gráficas en SVG (cadenas). Las dos fuentes son dos testigos: cada gráfica las muestra juntas en el mismo eje.
// IMERG en blanco, CHIRPS en celeste, en todas las gráficas; el color de la clase de confianza solo en sus marcas.
import { esc, LL, num, sgn, type TrendData, type Sel, type Tr } from "./datos";

export const PROD_COLOR: Record<string, string> = { IMERG: "#ffffff", CHIRPS: "#8fd3ff" };
const pc = (p: string) => PROD_COLOR[p] ?? "#bbbbbb";

/** Cápsula de los dos testigos: cada fuente en su fila con su IC 95 %, en un eje común con el cero
 *  y la banda de lo que 24 años no permiten detectar (la mayor de las dos tendencias mínimas detectables). */
export function capsule(d: TrendData, s: Sel) {
  const rows = d.prods.map((p) => ({ p, t: d.tr(s, p) })).filter((x): x is { p: string; t: Tr } => !!x.t);
  if (!rows.length) return "";
  const W = 340, pad = 14, rh = 30, top = 18, H = top + rows.length * rh + 18;
  const mdt = Math.max(...rows.map((x) => x.t.mdt));
  const ext = Math.max(mdt, ...rows.flatMap((x) => [Math.abs(x.t.ic95[0]), Math.abs(x.t.ic95[1]), Math.abs(x.t.pendiente_decada)])) * 1.12 || 1;
  const L = 64, x = (v: number) => L + ((v + ext) / (2 * ext)) * (W - L - pad);
  const unit = d.vm(s.ind).unidad_tendencia;
  return `<svg class="tr-cap" viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(rows.map(({ p, t }) => `${p} ${sgn(t.pendiente_decada)} ${unit} (IC ${num(t.ic95[0])} a ${num(t.ic95[1])})`).join("; "))}">
    <rect class="cap-mdt" x="${x(-mdt)}" y="${top - 6}" width="${x(mdt) - x(-mdt)}" height="${rows.length * rh + 2}" rx="8"/>
    <line x1="${x(0)}" x2="${x(0)}" y1="${top - 10}" y2="${top + rows.length * rh}" class="cap-zero"/>
    <text x="${x(0)}" y="${top - 12}" text-anchor="middle" class="cap-t">0</text>
    ${rows.map(({ p, t }, i) => {
      const y = top + i * rh + rh / 2 - 4, sig = d.isSig(t, s.reg), lo = x(t.ic95[0]), hi = x(t.ic95[1]);
      return `<text x="0" y="${y + 4}" class="cap-p">${p}</text>
        <rect x="${lo}" y="${y - 4}" width="${Math.max(2, hi - lo)}" height="8" rx="4" fill="${pc(p)}" fill-opacity="${sig ? 0.55 : 0.22}"/>
        <circle cx="${x(t.pendiente_decada)}" cy="${y}" r="6" fill="${sig ? pc(p) : "#15171a"}" stroke="${pc(p)}" stroke-width="2"/>
        <text x="${W}" y="${y + 4}" text-anchor="end" class="cap-v num">${sgn(t.pendiente_decada)}</text>`;
    }).join("")}
    <text x="${x(-mdt) + 4}" y="${H - 2}" class="cap-t">${esc(LL(`no detectable con 24 años (±${num(mdt)})`, `undetectable with 24 years (±${num(mdt)})`))}</text>
  </svg>`;
}

/** Las 32 provincias en un mismo eje: arriba IMERG, debajo CHIRPS; el punto relleno es significativo
 *  y la marca a la izquierda del nombre lleva el color de la clase de confianza. Orden: por clase y luego por tendencia. */
export function forest(d: TrendData, s: Sel, width: number) {
  const order: Record<string, number> = { robusta: 0, consistente: 1, "en disputa": 2, "un solo producto": 3, "sin señal detectable": 4, "sin dato": 5 };
  const rows = d.provs.map((r) => ({ r, row: d.row(s, r.id), ts: d.prods.map((p) => ({ p, t: d.tr(s, p, r.id) })) }))
    .filter((x) => x.ts.some((y) => y.t))
    .sort((a, b) => (order[a.row?.clase ?? ""] ?? 9) - (order[b.row?.clase ?? ""] ?? 9) || (b.ts[0].t?.pendiente_decada ?? 0) - (a.ts[0].t?.pendiente_decada ?? 0));
  const ext = Math.max(...rows.flatMap((x) => x.ts.flatMap((y) => (y.t ? [Math.abs(y.t.ic95[0]), Math.abs(y.t.ic95[1])] : [])))) || 1;
  const W = width, rh = d.prods.length > 1 ? 30 : 24, L = Math.min(150, W * 0.42), pad = 8, H = rows.length * rh + 24;
  const x = (v: number) => L + ((v + ext) / (2 * ext)) * (W - L - pad);
  const counts: Record<string, number> = {};
  rows.forEach((r) => { const c = r.row?.clase ?? ""; counts[c] = (counts[c] ?? 0) + 1; });
  const svg = `<svg class="tr-forest" viewBox="0 0 ${W} ${H}" width="${W}" role="list">
    <line x1="${x(0)}" x2="${x(0)}" y1="0" y2="${H - 20}" class="fz"/>
    ${rows.map(({ r, row, ts }, i) => {
      const y0 = i * rh, cls = row?.clase ?? "", col = d.V.clases[cls]?.color ?? "#6b6f75";
      const marks = ts.map(({ p, t }, k) => {
        if (!t) return "";
        const y = y0 + rh / 2 + (ts.length > 1 ? (k - 0.5) * 8 : 0), sig = d.isSig(t, r.id);
        return `<line x1="${x(t.ic95[0])}" x2="${x(t.ic95[1])}" y1="${y}" y2="${y}" stroke="${pc(p)}" stroke-width="2" stroke-linecap="round" stroke-opacity="${sig ? 0.7 : 0.3}"/>
          <circle cx="${x(t.pendiente_decada)}" cy="${y}" r="3.6" fill="${sig ? pc(p) : "#15171a"}" stroke="${pc(p)}" stroke-width="1.4"/>`;
      }).join("");
      return `<g class="fr ${r.id === s.reg ? "on" : ""}" data-reg="${r.id}" role="listitem" tabindex="0" aria-label="${esc(`${r.nombre}: ${d.V.clases[cls] ? d.lab(d.V.clases[cls]) : cls}; ${ts.map(({ p, t }) => (t ? `${p} ${sgn(t.pendiente_decada)}` : "")).join(", ")}`)}">
        <rect x="0" y="${y0 + 1}" width="${W}" height="${rh - 2}" rx="8" class="fr-bg"/>
        <rect x="6" y="${y0 + rh / 2 - 6}" width="4" height="12" rx="2" fill="${col}"/>
        <text x="18" y="${y0 + rh / 2 + 4}" class="fr-n">${esc(r.nombre)}</text>
        ${marks}
      </g>`;
    }).join("")}
    <text x="${x(-ext)}" y="${H - 4}" class="fr-ax num">${num(-ext)}</text>
    <text x="${x(0)}" y="${H - 4}" class="fr-ax" text-anchor="middle">0</text>
    <text x="${x(ext)}" y="${H - 4}" class="fr-ax num" text-anchor="end">${sgn(ext)}</text>
  </svg>`;
  return { svg, counts };
}

/** Serie anual de las dos fuentes, cada una con su recta de Theil-Sen (intercepto = mediana de y − b·x);
 *  la de la fuente elegida lleva el abanico de su IC 95 %. Discontinua si no es significativa. */
export function seriesChart(d: TrendData, s: Sel, width: number, mark: number | null, height = 180) {
  const yrs = d.years(s);
  const W = Math.max(280, width), H = height, ml = 40, mr = 12, mt = 14, mb = 22;
  const lines = d.prods.map((p) => ({ p, v: d.series(s, p), t: d.tr(s, p) })).filter((x): x is { p: string; v: (number | null)[]; t: Tr | null } => !!x.v);
  const all = lines.flatMap((x) => x.v).filter((x): x is number => x !== null);
  if (!all.length) return "";
  let lo = Math.min(...all), hi = Math.max(...all);
  const span = hi - lo || Math.abs(hi) || 1; lo = Math.max(0, lo - span * 0.15); hi += span * 0.15;
  const X = (yr: number) => ml + ((yr - yrs[0]) / (yrs[yrs.length - 1] - yrs[0])) * (W - ml - mr);
  const Y = (v: number) => mt + (1 - (v - lo) / (hi - lo)) * (H - mt - mb);
  const [y0, y1] = [yrs[0], yrs[yrs.length - 1]];
  const trendOf = ({ p, v, t }: typeof lines[0]) => {
    if (!t) return "";
    const b = t.pendiente_decada / 10;
    const res = yrs.map((yr, k) => (v[k] === null ? null : v[k]! - b * yr)).filter((x): x is number => x !== null).sort((a, c) => a - c);
    const xm = yrs[Math.floor(yrs.length / 2)], ym = res[Math.floor(res.length / 2)] + b * xm;
    const at = (bb: number, yr: number) => ym + bb * (yr - xm);
    const sig = d.isSig(t, s.reg), [b0, b1] = [t.ic95[0] / 10, t.ic95[1] / 10];
    const fan = p === s.src ? `<path d="M${X(y0)},${Y(at(b0, y0))} L${X(y1)},${Y(at(b0, y1))} L${X(y1)},${Y(at(b1, y1))} L${X(y0)},${Y(at(b1, y0))} Z" fill="${pc(p)}" fill-opacity=".1"/>` : "";
    return `${fan}<line x1="${X(y0)}" y1="${Y(at(b, y0))}" x2="${X(y1)}" y2="${Y(at(b, y1))}" stroke="${pc(p)}" stroke-width="2.4" stroke-linecap="round" ${sig ? "" : 'stroke-dasharray="5 5"'} opacity="${sig ? 1 : 0.7}"/>`;
  };
  const path = (v: (number | null)[]) => {
    let p = "", pen = false;
    v.forEach((y, k) => { if (y === null) { pen = false; return; } p += `${pen ? "L" : "M"}${X(yrs[k]).toFixed(1)},${Y(y).toFixed(1)}`; pen = true; });
    return p;
  };
  const ticks = [lo, (lo + hi) / 2, hi];
  const xt = [y0, 2010, 2015, 2020, y1].filter((y, i, a) => a.indexOf(y) === i && y >= y0);
  const main = lines.find((x) => x.p === s.src) ?? lines[0];
  return `<svg viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" class="tr-svg" role="img" aria-label="${esc(LL(`Serie anual de ${d.lab(d.vm(s.ind))}`, `Annual series of ${d.lab(d.vm(s.ind))}`))}">
    ${ticks.map((v) => `<line x1="${ml}" x2="${W - mr}" y1="${Y(v)}" y2="${Y(v)}" class="gl"/><text x="${ml - 8}" y="${Y(v) + 4}" text-anchor="end" class="ax num">${num(v)}</text>`).join("")}
    ${xt.map((y) => `<text x="${X(y)}" y="${H - 4}" text-anchor="middle" class="ax num">${y}</text>`).join("")}
    ${lines.map(trendOf).join("")}
    ${lines.map((l) => `<path d="${path(l.v)}" fill="none" stroke="${pc(l.p)}" stroke-width="${l.p === s.src ? 1.8 : 1.4}" stroke-opacity="${l.p === s.src ? 0.9 : 0.6}" stroke-linejoin="round"/>`).join("")}
    ${main.v.map((v, k) => (v === null ? "" : `<circle cx="${X(yrs[k])}" cy="${Y(v)}" r="${yrs[k] === mark ? 5.5 : 2.6}" fill="${yrs[k] === mark ? "#ffd60a" : pc(main.p)}"/>`)).join("")}
    ${mark !== null ? `<line class="tr-cur" x1="${X(mark)}" x2="${X(mark)}" y1="${mt}" y2="${H - mb}"/>` : ""}
    <rect x="${ml}" y="0" width="${W - ml - mr}" height="${H}" fill="transparent" class="tr-hit" data-ml="${ml}" data-mr="${mr}" data-w="${W}"/>
  </svg>
  <p class="tr-key">${lines.map((l) => `<span><i class="ln" style="background:${pc(l.p)}"></i>${esc(l.p)}${l.t ? ` ${sgn(l.t.pendiente_decada)}` : ""}</span>`).join("")}<span>${esc(LL("recta: tendencia (discontinua si no es significativa)", "line: trend (dashed if not significant)"))}</span></p>`;
}
