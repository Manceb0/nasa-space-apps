// Gráficas en SVG (cadenas). Las dos fuentes son dos testigos: cada gráfica las muestra juntas en el mismo eje.
// IMERG en blanco, CHIRPS en celeste, en todas las gráficas; el color de la clase de confianza solo en sus marcas.
import { esc, LL, num, sgn, type TrendData, type Sel, type Tr } from "./datos";

export const PROD_COLOR: Record<string, string> = { IMERG: "#ffffff", CHIRPS: "#8fd3ff" };
const pc = (p: string) => PROD_COLOR[p] ?? "#bbbbbb";

/** El medidor: un semicírculo cuyo extremo izquierdo y derecho dicen en palabras qué significa cada lado (con los
 *  colores del mapa); arriba, «sin cambio». Cada fuente es una aguja que gira desde arriba hasta su tendencia, con un
 *  abanico detrás que es su margen del 95 %. Aguja sólida = cambio claro; discontinua = puede ser azar. El anillo se
 *  satura hacia los extremos: cuanto más lejos de «sin cambio», más cambio. Debajo, la lectura de cada fuente. */
export function capsule(d: TrendData, s: Sel) {
  const rows = d.prods.map((p) => ({ p, t: d.tr(s, p) })).filter((x): x is { p: string; t: Tr } => !!x.t);
  if (!rows.length) return "";
  const ext = Math.max(...rows.flatMap((x) => [Math.abs(x.t.ic95[0]), Math.abs(x.t.ic95[1]), Math.abs(x.t.pendiente_decada)])) * 1.1 || 1;
  const v = d.vm(s.ind), dry = v.tipo === "seco";
  const DRY = "#ff9f0a", WET = "#28a0f0";
  const right = dry ? LL("más seco", "drier") : LL("más lluvia", "more rain"), left = dry ? LL("menos seco", "less dry") : LL("menos lluvia", "less rain");
  const cR = dry ? DRY : WET, cL = dry ? WET : DRY;
  const W = 340, R = 132, cx = W / 2, cy = R + 30, H = cy + 30, rf = 112, rn = 104;
  const deg = (val: number) => Math.max(-90, Math.min(90, (val / ext) * 90));
  const pt = (a: number, r: number) => { const t = (a * Math.PI) / 180; return `${(cx + r * Math.sin(t)).toFixed(1)},${(cy - r * Math.cos(t)).toFixed(1)}`; };
  const band = (a1: number, a2: number, ro: number, ri: number) => `M${pt(a1, ro)} A${ro} ${ro} 0 0 1 ${pt(a2, ro)} L${pt(a2, ri)} A${ri} ${ri} 0 0 0 ${pt(a1, ri)}Z`;
  // Anillo graduado: 9 segmentos por lado, más intensos hacia el extremo
  const N = 9, step = 90 / N, gap = 1.4;
  const ring = [-1, 1].map((side) => Array.from({ length: N }, (_, k) => {
    const a1 = side * (k * step + gap / 2), a2 = side * ((k + 1) * step - gap / 2);
    return `<path d="${band(Math.min(a1, a2), Math.max(a1, a2), R, R - 12)}" fill="${side < 0 ? cL : cR}" fill-opacity="${(0.16 + 0.7 * (k / (N - 1))).toFixed(2)}"/>`;
  }).join("")).join("");
  const sig = rows.map((r) => d.isSig(r.t, s.reg));
  const fans = rows.map(({ p, t }, i) => {
    const a1 = deg(t.ic95[0]), a2 = deg(t.ic95[1]), c = pc(p);
    if (a2 - a1 < 0.5) return "";
    return `<path d="M${cx},${cy} L${pt(a1, rf)} A${rf} ${rf} 0 0 1 ${pt(a2, rf)}Z" fill="${c}" fill-opacity="${sig[i] ? 0.16 : 0.08}"/>
      <path d="M${pt(a1, rf)} A${rf} ${rf} 0 0 1 ${pt(a2, rf)}" fill="none" stroke="${c}" stroke-width="3" stroke-linecap="round" stroke-opacity="${sig[i] ? 0.75 : 0.4}"/>`;
  }).join("");
  const needles = rows.map(({ p, t }, i) => {
    const c = pc(p), a = deg(t.pendiente_decada);
    return `<g class="cap-n" style="--a:${a.toFixed(1)}deg;transform-origin:${cx}px ${cy}px">
      <line x1="${cx}" y1="${cy}" x2="${cx}" y2="${cy - rn}" stroke="${c}" stroke-width="4" stroke-linecap="round" ${sig[i] ? "" : 'stroke-dasharray="7 6"'}/>
      <circle cx="${cx}" cy="${cy - rn}" r="6" fill="${sig[i] ? c : "var(--surface)"}" stroke="${c}" stroke-width="2.5"/>
    </g>`;
  }).join("");
  // La lectura de cada fuente va del lado al que apunta su aguja
  const read = rows.map((r, i) => ({ ...r, i })).sort((a, b) => a.t.pendiente_decada - b.t.pendiente_decada).map(({ p, t, i }) => {
    const up = t.pendiente_decada > 0, side = up ? right : left, sc = up ? cR : cL;
    return `<div class="cr">
      <p class="cr-p"><i style="background:${pc(p)}"></i>${p}</p>
      <p class="cr-v num">${sgn(t.pendiente_decada)}</p>
      <p class="cr-s"><b style="color:${sc}">${esc(side)}</b> · ${esc(sig[i] ? LL("cambio claro", "clear change") : LL("puede ser azar", "may be chance"))}</p>
    </div>`;
  }).join("");
  return `<svg class="tr-cap" viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(rows.map(({ p, t }, i) => `${p} ${sgn(t.pendiente_decada)} ${v.unidad_tendencia} (IC ${num(t.ic95[0])} a ${num(t.ic95[1])})${sig[i] ? "" : `, ${LL("no significativa", "not significant")}`}`).join("; "))}">
    ${ring}
    <line x1="${cx}" y1="${cy - R - 4}" x2="${cx}" y2="${cy - 18}" class="cap-zero"/>
    <text x="${cx}" y="${cy - R - 12}" text-anchor="middle" class="cap-t">${esc(LL("sin cambio", "no change"))}</text>
    ${fans}${needles}
    <circle cx="${cx}" cy="${cy}" r="8" class="cap-hub"/>
    <text x="${cx - R}" y="${cy + 22}" class="cap-end" fill="${cL}">◀ ${esc(left)}</text>
    <text x="${cx + R}" y="${cy + 22}" text-anchor="end" class="cap-end" fill="${cR}">${esc(right)} ▶</text>
  </svg>
  <div class="cap-read">${read}</div>
  <p class="cap-note">${esc(LL(`En ${v.unidad_tendencia}. Aguja sólida: cambio claro · discontinua: puede ser azar · abanico: margen del 95 %.`, `In ${v.unidad_tendencia}. Solid needle: clear change · dashed: may be chance · fan: 95 % margin.`))}</p>`;
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
  <p class="tr-key">${lines.map((l) => `<span><i class="ln" style="background:${pc(l.p)}"></i>${esc(l.p)}${l.t ? ` ${sgn(l.t.pendiente_decada)}` : ""}</span>`).join("")}<span>${esc(LL("discontinua: no significativa", "dashed: not significant"))}</span></p>`;
}
