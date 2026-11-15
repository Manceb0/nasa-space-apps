// Gráficas en SVG (cadenas): cápsula de IC frente a lo detectable, las 32 provincias en un eje y la serie anual.
import { esc, LL, num, sgn, type TrendData, type Sel, type Tr } from "./datos";

const SIG_DRY = "#ff9f0a", SIG_WET = "#0a84ff", NS = "#8e8e93";
export const trendColor = (d: TrendData, s: Sel, t: Tr, reg = s.reg) => (d.isSig(t, reg) ? (d.towardDry(s.ind, t.pendiente_decada) ? SIG_DRY : SIG_WET) : NS);

/** Eje simétrico en 0: el punto es la tendencia, la barra su IC 95 % y la banda gris lo que 24 años no permiten detectar. */
export function capsule(d: TrendData, s: Sel, t: Tr) {
  const W = 340, H = 92, pad = 14, cy = 40, unit = d.vm(s.ind).unidad_tendencia;
  const ext = Math.max(Math.abs(t.ic95[0]), Math.abs(t.ic95[1]), t.mdt, Math.abs(t.pendiente_decada)) * 1.12 || 1;
  const x = (v: number) => pad + ((v + ext) / (2 * ext)) * (W - 2 * pad);
  const col = trendColor(d, s, t), lo = x(t.ic95[0]), hi = x(t.ic95[1]);
  return `<svg class="tr-cap" viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(LL(`Tendencia ${sgn(t.pendiente_decada)} ${unit}; IC 95 % de ${num(t.ic95[0])} a ${num(t.ic95[1])}; mínima detectable ±${num(t.mdt)}`, `Trend ${sgn(t.pendiente_decada)} ${unit}; 95 % CI ${num(t.ic95[0])} to ${num(t.ic95[1])}; minimum detectable ±${num(t.mdt)}`))}">
    <rect class="cap-mdt" x="${x(-t.mdt)}" y="${cy - 17}" width="${x(t.mdt) - x(-t.mdt)}" height="34" rx="10"/>
    <line x1="${x(0)}" x2="${x(0)}" y1="${cy - 24}" y2="${cy + 24}" class="cap-zero"/>
    <g class="cap-ci" style="transform-origin:${x(t.pendiente_decada)}px ${cy}px"><rect x="${lo}" y="${cy - 5}" width="${Math.max(2, hi - lo)}" height="10" rx="5" fill="${col}" fill-opacity=".45"/></g>
    <circle class="cap-dot" cx="${x(t.pendiente_decada)}" cy="${cy}" r="7" fill="${col}" stroke="#000" stroke-opacity=".35"/>
    <text x="${x(0)}" y="${cy - 28}" text-anchor="middle" class="cap-t">0</text>
    <text x="${x(-t.mdt) + 4}" y="${cy + 32}" class="cap-t">${esc(LL("no detectable con 24 años", "undetectable with 24 years"))}</text>
    <text x="${lo}" y="${H - 2}" class="cap-t num" text-anchor="${lo < 40 ? "start" : "middle"}">${num(t.ic95[0])}</text>
    <text x="${hi}" y="${H - 2}" class="cap-t num" text-anchor="${hi > W - 40 ? "end" : "middle"}">${num(t.ic95[1])}</text>
  </svg>`;
}

/** Las 32 provincias en un mismo eje, de más subida a más bajada. Punto relleno = significativa. */
export function forest(d: TrendData, s: Sel, width: number) {
  const rows = d.provs.map((r) => ({ r, t: d.tr(s, s.src, r.id) })).filter((x): x is { r: typeof x.r; t: Tr } => !!x.t)
    .sort((a, b) => b.t.pendiente_decada - a.t.pendiente_decada);
  const ext = Math.max(...rows.map((x) => Math.max(Math.abs(x.t.ic95[0]), Math.abs(x.t.ic95[1])))) || 1;
  const W = width, rh = 24, L = Math.min(150, W * 0.42), pad = 8, H = rows.length * rh + 24;
  const x = (v: number) => L + ((v + ext) / (2 * ext)) * (W - L - pad);
  const svg = `<svg class="tr-forest" viewBox="0 0 ${W} ${H}" width="${W}" role="list">
    <line x1="${x(0)}" x2="${x(0)}" y1="0" y2="${H - 20}" class="fz"/>
    ${rows.map(({ r, t }, i) => {
      const y = i * rh + rh / 2, sig = d.isSig(t, r.id), col = trendColor(d, s, t, r.id);
      return `<g class="fr ${r.id === s.reg ? "on" : ""}" data-reg="${r.id}" role="listitem" tabindex="0" style="--i:${i}" aria-label="${esc(`${r.nombre}: ${sgn(t.pendiente_decada)}${sig ? `, ${LL("significativa", "significant")}` : ""}`)}">
        <rect x="0" y="${y - rh / 2}" width="${W}" height="${rh}" rx="8" class="fr-bg"/>
        <text x="8" y="${y + 4}" class="fr-n">${esc(r.nombre)}</text>
        <line x1="${x(t.ic95[0])}" x2="${x(t.ic95[1])}" y1="${y}" y2="${y}" stroke="${col}" stroke-width="3" stroke-linecap="round" stroke-opacity=".55"/>
        <circle cx="${x(t.pendiente_decada)}" cy="${y}" r="4.5" fill="${sig ? col : "#1c1c1e"}" stroke="${col}" stroke-width="1.6"/>
      </g>`;
    }).join("")}
    <text x="${x(-ext)}" y="${H - 4}" class="fr-ax num">${num(-ext)}</text>
    <text x="${x(0)}" y="${H - 4}" class="fr-ax" text-anchor="middle">0</text>
    <text x="${x(ext)}" y="${H - 4}" class="fr-ax num" text-anchor="end">${sgn(ext)}</text>
  </svg>`;
  return { svg, nSig: rows.filter((x) => d.isSig(x.t, x.r.id)).length };
}

/** Serie anual con la recta de Theil-Sen (intercepto = mediana de y − b·x) y el abanico de su IC 95 %. */
export function seriesChart(d: TrendData, s: Sel, width: number, mark: number | null, height = 180) {
  const yrs = d.years(s), t = d.tr(s);
  const W = Math.max(280, width), H = height, ml = 40, mr = 12, mt = 14, mb = 22;
  const lines = d.prods.map((p) => ({ p, v: d.series(s, p) })).filter((x): x is { p: string; v: (number | null)[] } => !!x.v);
  const all = lines.flatMap((x) => x.v).filter((x): x is number => x !== null);
  if (!all.length) return "";
  let lo = Math.min(...all), hi = Math.max(...all);
  const span = hi - lo || Math.abs(hi) || 1; lo = Math.max(0, lo - span * 0.15); hi += span * 0.15;
  const X = (yr: number) => ml + ((yr - yrs[0]) / (yrs[yrs.length - 1] - yrs[0])) * (W - ml - mr);
  const Y = (v: number) => mt + (1 - (v - lo) / (hi - lo)) * (H - mt - mb);
  const main = lines.find((x) => x.p === s.src) ?? lines[0];
  const col = t ? trendColor(d, s, t) : NS, sig = t ? d.isSig(t, s.reg) : false;
  let trend = "";
  if (t) {
    const b = t.pendiente_decada / 10;
    const res = yrs.map((yr, k) => (main.v[k] === null ? null : main.v[k]! - b * yr)).filter((x): x is number => x !== null).sort((a, c) => a - c);
    const xm = yrs[Math.floor(yrs.length / 2)], ym = res[Math.floor(res.length / 2)] + b * xm;
    const at = (bb: number, yr: number) => ym + bb * (yr - xm);
    const [y0, y1] = [yrs[0], yrs[yrs.length - 1]], [b0, b1] = [t.ic95[0] / 10, t.ic95[1] / 10];
    trend = `<path d="M${X(y0)},${Y(at(b0, y0))} L${X(y1)},${Y(at(b0, y1))} L${X(y1)},${Y(at(b1, y1))} L${X(y0)},${Y(at(b1, y0))} Z" fill="${col}" fill-opacity=".14" class="tr-fan"/>
      <line x1="${X(y0)}" y1="${Y(at(b, y0))}" x2="${X(y1)}" y2="${Y(at(b, y1))}" stroke="${col}" stroke-width="2.4" stroke-linecap="round" ${sig ? "" : 'stroke-dasharray="5 5"'} class="tr-trend"/>`;
  }
  const path = (v: (number | null)[]) => {
    let p = "", pen = false;
    v.forEach((y, k) => { if (y === null) { pen = false; return; } p += `${pen ? "L" : "M"}${X(yrs[k]).toFixed(1)},${Y(y).toFixed(1)}`; pen = true; });
    return p;
  };
  const ticks = [lo, (lo + hi) / 2, hi];
  const xt = [yrs[0], 2010, 2015, 2020, yrs[yrs.length - 1]].filter((y, i, a) => a.indexOf(y) === i && y >= yrs[0]);
  return `<svg viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" class="tr-svg" role="img" aria-label="${esc(LL(`Serie anual de ${d.lab(d.vm(s.ind))}`, `Annual series of ${d.lab(d.vm(s.ind))}`))}">
    ${ticks.map((v) => `<line x1="${ml}" x2="${W - mr}" y1="${Y(v)}" y2="${Y(v)}" class="gl"/><text x="${ml - 8}" y="${Y(v) + 4}" text-anchor="end" class="ax num">${num(v)}</text>`).join("")}
    ${xt.map((y) => `<text x="${X(y)}" y="${H - 4}" text-anchor="middle" class="ax num">${y}</text>`).join("")}
    ${trend}
    ${lines.map(({ p, v }) => `<path d="${path(v)}" class="tr-line ${p === s.src ? "main" : "alt"}" pathLength="1"/>`).join("")}
    ${main.v.map((v, k) => (v === null ? "" : `<circle cx="${X(yrs[k])}" cy="${Y(v)}" r="${yrs[k] === mark ? 6 : 3.2}" class="tr-pt ${yrs[k] === mark ? "mark" : ""}" style="--i:${k}"/>`)).join("")}
    ${mark !== null ? `<line class="tr-cur" x1="${X(mark)}" x2="${X(mark)}" y1="${mt}" y2="${H - mb}"/>` : ""}
    <rect x="${ml}" y="0" width="${W - ml - mr}" height="${H}" fill="transparent" class="tr-hit" data-y0="${yrs[0]}" data-y1="${yrs[yrs.length - 1]}" data-ml="${ml}" data-mr="${mr}" data-w="${W}"/>
  </svg>
  <p class="tr-key"><span><i class="ln"></i>${esc(s.src)}</span>${lines.length > 1 ? `<span><i class="ln alt"></i>${esc(lines.filter((x) => x.p !== s.src).map((x) => x.p).join(", "))}</span>` : ""}<span><i class="ln" style="background:${col}"></i>${esc(sig ? LL("tendencia (significativa)", "trend (significant)") : LL("tendencia (no significativa)", "trend (not significant)"))}</span><span><i class="sq" style="background:${col}"></i>${esc(LL("IC 95 %", "95 % CI"))}</span></p>`;
}
