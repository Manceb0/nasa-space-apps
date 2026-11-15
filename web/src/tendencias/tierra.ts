// La vegetación dentro de Tendencias: lo que antes vivía en «Investigar» (tendencias MODIS por punto) y en
// «Recovery Ribbon» (la auditoría de recuperación tras cada sequía), con las mismas piezas que el resto de la pantalla:
// cuánto cambia, si es claro y por qué importa. Solo lee puntos.json, phantom.json e index.json; no calcula estadística.
import { load } from "../data";
import { T } from "../i18n";
import { esc, LL, num, sgn } from "./datos";

export interface LandTr { n: number; pendiente_decada: number; ic95_decada: [number, number]; p_mk: number; q_bh?: number; veredicto: string }
export interface Site { id: string; nombre: string; lat: number; lon: number; estable: boolean; tendencias: Record<string, LandTr> }
export interface Audit { id: string; evento_inicio: string; evento_fin: string; veredicto: string; estabilidad: number; combinaciones: number; evento_severidad_spi3: number }
export interface VMeta { nombre: string; unidad: string; definicion: string; fuente: string; tipo: string; aviso?: string }
export interface Land { sites: Site[]; audits: Audit[]; meta: Record<string, VMeta> }

const ORDER = ["montecristimontesecoa", "montecristimontesecob", "sierramontecristi", "jaraguacomparacionseco", "cordilleracomparacionhumedo"];

export async function loadLand(): Promise<Land | null> {
  try {
    const [P, H, I] = await Promise.all([
      load<{ puntos: Site[] }>("puntos.json"), load<{ auditorias: Audit[] }>("phantom.json"), load<{ variables: Record<string, VMeta> }>("index.json"),
    ]);
    const sites = ORDER.map((id) => P.puntos.find((p) => p.id === id)).filter((p): p is Site => !!p);
    return { sites, audits: H.auditorias ?? [], meta: I.variables };
  } catch { return null; }
}

export const LAND_Q = [
  { id: "verde", es: "¿Cambia la vegetación?", en: "Is the vegetation changing?" },
  { id: "recupera", es: "¿Se recupera tras cada sequía?", en: "Does it recover after each drought?" },
] as const;
export type LandQ = "" | (typeof LAND_Q)[number]["id"];
export const LAND_VARS = ["modis_ndvi", "modis_lst", "modis_gpp"] as const;
const SHORT: Record<string, [string, string]> = {
  modis_ndvi: ["Verdor (NDVI)", "Greenness (NDVI)"],
  modis_lst: ["Temperatura de la superficie", "Surface temperature"],
  modis_gpp: ["Productividad (modelo GPP)", "Productivity (GPP model)"],
};
const ENDS: Record<string, [[string, string], [string, string]]> = {
  modis_ndvi: [["menos verde", "less green"], ["más verde", "greener"]],
  modis_lst: [["más fresca", "cooler"], ["más caliente", "hotter"]],
  modis_gpp: [["menos carbono", "less carbon"], ["más carbono", "more carbon"]],
};
const WORSE_HIGH: Record<string, boolean> = { modis_ndvi: false, modis_lst: true, modis_gpp: false };
const WHY: Record<string, [string, string]> = {
  modis_ndvi: ["Resume cuánta hoja verde hay. En el bosque seco, perderla deja el suelo más expuesto al sol y a la erosión.", "It sums up how much green leaf there is. In dry forest, losing it leaves the soil more exposed to sun and erosion."],
  modis_lst: ["Una superficie que se calienta más que el aire indica plantas que transpiran menos: es una señal de estrés por agua que el verdor no muestra.", "A surface that heats up more than the air points to plants transpiring less: a water-stress signal that greenness does not show."],
  modis_gpp: ["Es el carbono que fija la vegetación. Aquí sale de un modelo que usa el mismo verdor, así que no lo confirma por sí solo.", "It is the carbon the vegetation fixes. Here it comes from a model that uses the same greenness, so it does not confirm it on its own."],
};
const WORSE = "#ff9f0a", BETTER = "#28a0f0";
/** El mismo criterio que usaba «Investigar»: Mann-Kendall con AR(1), p < 0,05 y el IC 95 % no cruza el cero. */
export const landSig = (t: LandTr) => t.p_mk < 0.05 && (t.ic95_decada[0] > 0 || t.ic95_decada[1] < 0);
const tone = (v: string, x: number) => ((x > 0) === WORSE_HIGH[v] ? WORSE : BETTER);
const pTxt = (p: number) => (p < 0.001 ? `&lt; ${num(0.001, 3)}` : num(p, 3));
const dig = (v: string) => (v === "modis_ndvi" ? 3 : 2);

/** Cada lugar en una fila del mismo eje: punto = cambio por década, barra = IC 95 %, relleno = claro. */
function siteChart(L: Land, v: string, focus: string) {
  const rows = L.sites.filter((s) => s.tendencias[v]);
  const ext = Math.max(...rows.flatMap((s) => s.tendencias[v].ic95_decada.map(Math.abs))) * 1.12 || 1;
  const W = 340, top = 44, rh = 40, H = top + rows.length * rh + 4, L0 = 138, R0 = 10;
  const x = (val: number) => L0 + ((val + ext) / (2 * ext)) * (W - L0 - R0), x0 = x(0);
  const [lo, hi] = ENDS[v];
  const cL = WORSE_HIGH[v] ? BETTER : WORSE, cR = WORSE_HIGH[v] ? WORSE : BETTER;
  const d = dig(v);
  return `<svg class="tr-cap land-chart" viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(rows.map((s) => `${s.nombre} ${sgn(s.tendencias[v].pendiente_decada, d)}`).join("; "))}">
    <text x="${L0}" y="12" class="cap-end" fill="${cL}">◀ ${esc(LL(...lo))}</text>
    <text x="${W - R0}" y="12" text-anchor="end" class="cap-end" fill="${cR}">${esc(LL(...hi))} ▶</text>
    <line x1="${x0}" x2="${x0}" y1="${top - 8}" y2="${H}" class="cap-zero"/>
    <text x="${x0}" y="${top - 14}" text-anchor="middle" class="cap-t">${esc(LL("sin cambio", "no change"))}</text>
    ${rows.map((s, i) => {
      const t = s.tendencias[v], y = top + i * rh + rh / 2, c = tone(v, t.pendiente_decada), sg = landSig(t), xe = x(t.pendiente_decada);
      const right = xe > x0, lx = right ? Math.min(xe + 8, W - R0) : Math.max(xe - 8, L0);
      return `<g class="land-row ${s.id === focus ? "on" : ""}" data-site="${s.id}">
        <title>${esc(`${s.nombre}: ${sgn(t.pendiente_decada, d)} ${LL("por década", "per decade")} (IC ${num(t.ic95_decada[0], d)} a ${num(t.ic95_decada[1], d)}), p ${t.p_mk < 0.001 ? "< 0,001" : num(t.p_mk, 3)}`)}</title>
        <rect x="0" y="${y - rh / 2 + 2}" width="${W}" height="${rh - 4}" rx="8" class="land-bg"/>
        <text x="8" y="${y + 4}" class="cap-p">${esc(s.nombre)}${s.estable ? "" : " *"}</text>
        <line x1="${x(t.ic95_decada[0])}" x2="${x(t.ic95_decada[1])}" y1="${y}" y2="${y}" stroke="${c}" stroke-opacity=".55" stroke-width="3" stroke-linecap="round"/>
        <circle cx="${xe}" cy="${y}" r="6" fill="${sg ? c : "var(--surface)"}" stroke="${c}" stroke-width="2.5"/>
        <text x="${lx}" y="${y - 9}" text-anchor="${right ? "end" : "start"}" class="land-v num">${sgn(t.pendiente_decada, d)}</text>
      </g>`;
    }).join("")}
  </svg>`;
}

export function verdeAnswer(L: Land, v: string, focus: string) {
  const m = L.meta[v], rows = L.sites.filter((s) => s.tendencias[v]), clear = rows.filter((s) => landSig(s.tendencias[v]));
  const d = dig(v);
  const ms = LAND_VARS.map((id) => {
    const k = L.sites.filter((s) => s.tendencias[id] && landSig(s.tendencias[id])).length, n = L.sites.filter((s) => s.tendencias[id]).length, on = id === v;
    return `<button class="m ${on ? "on" : ""}" data-landvar="${id}" role="radio" aria-checked="${on}" title="${esc(L.meta[id]?.definicion ?? "")}"><span class="m-t">${esc(LL(...SHORT[id]))}</span><span class="q-v ${k ? "sig" : ""}" style="--c:${k ? "#ff9f0a" : "#E6E6E6"}"><i></i>${esc(LL(`${k} de ${n} claros`, `${k} of ${n} clear`))}</span></button>`;
  }).join("");
  const list = clear.map((s) => `${s.nombre} ${sgn(s.tendencias[v].pendiente_decada, d)}`).join(" · ");
  const sentence = clear.length
    ? LL(`${clear.length} de ${rows.length} lugares cambian de forma clara: ${list} (${m.unidad} por década).`, `${clear.length} of ${rows.length} sites change clearly: ${list} (${m.unidad} per decade).`)
    : LL("Ningún lugar cambia de forma clara, y eso no es «sin cambio»: con 24 años solo se ve un cambio grande.", "No site changes clearly, and that is not \"no change\": with 24 years only a large change shows.");
  return `<div class="ms" role="radiogroup" aria-label="${esc(LL("Medido como", "Measured as"))}">${ms}</div>
    ${siteChart(L, v, focus)}
    <p class="cap-key">
      <span><svg viewBox="0 0 12 12" aria-hidden="true"><circle cx="6" cy="6" r="4.5" fill="currentColor"/></svg>${esc(LL("claro", "clear"))}</span>
      <span><svg viewBox="0 0 12 12" aria-hidden="true"><circle cx="6" cy="6" r="4" fill="none" stroke="currentColor" stroke-width="2"/></svg>${esc(LL("incierto", "uncertain"))}</span>
      <span><svg viewBox="0 0 20 8" aria-hidden="true"><line x1="2" y1="4" x2="18" y2="4" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-opacity=".6"/></svg>${esc(LL("IC 95 %", "95 % CI"))}</span>
    </p>
    <p class="ans-sent">${esc(sentence)}</p>
    <p class="ans-why"><b>${esc(LL("Por qué importa", "Why it matters"))}</b> ${esc(LL(...WHY[v]))}</p>
    <details class="ans-more">
      <summary>${esc(LL("Estadística y notas", "Statistics and notes"))}<svg class="chev" viewBox="0 0 12 12" aria-hidden="true"><path d="M3 4.5l3 3 3-3" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg></summary>
      <table class="stats-t">
        <thead><tr><th></th><th class="num">${esc(LL("por década", "per decade"))}</th><th class="num">IC 95 %</th><th class="num">p</th><th class="num">q (FDR)</th></tr></thead>
        <tbody>${rows.map((s) => { const t = s.tendencias[v]; return `<tr><th scope="row">${esc(s.nombre)}</th><td class="num">${sgn(t.pendiente_decada, d)}</td><td class="num">${num(t.ic95_decada[0], d)} a ${num(t.ic95_decada[1], d)}</td><td class="num">${pTxt(t.p_mk)}</td><td class="num">${t.q_bh === undefined ? "—" : pTxt(t.q_bh)}</td></tr>`; }).join("")}</tbody>
      </table>
      <p class="rule">${esc(LL(`Claro si p < 0,05 (Mann-Kendall con corrección AR(1)) y el IC 95 % de Theil-Sen no cruza el cero. ${m.fuente}. ${m.definicion}`, `Clear if p < 0.05 (Mann-Kendall with AR(1) correction) and the Theil-Sen 95 % CI excludes zero. ${m.fuente}. ${m.definicion}`))}</p>
      ${m.aviso ? `<p class="rule">${esc(m.aviso)}</p>` : ""}
      ${rows.some((s) => !s.estable) ? `<p class="rule">${esc(LL("* La cobertura del suelo cambió en este punto entre 2001 y 2021 (MODIS MCD12Q1).", "* Land cover changed at this site between 2001 and 2021 (MODIS MCD12Q1)."))}</p>` : ""}
    </details>`;
}

const VCOL: Record<string, string> = {
  consistente: "#ffffff", estres_invisible: "#ff9f0a", verdor_tarde: "#ffd60a", caida_posterior: "#ffd60a", fantasma: "#ff453a",
  solo_modelo: "#8a8c92", censurada: "#28a0f0", inconclusa: "#b4b4b4", sin_recuperacion: "#ff453a", sin_impacto: "#3a3d42",
};
const VORDER = ["consistente", "estres_invisible", "verdor_tarde", "caida_posterior", "fantasma", "censurada", "solo_modelo", "inconclusa", "sin_impacto"];

/** Dónde y cuándo: una fila por lugar, un círculo por sequía en el año en que empezó, coloreado por su veredicto. */
function recoveryRibbon(L: Land, focus: string) {
  const t = T(), sites = L.sites.filter((s) => L.audits.some((a) => a.id === s.id));
  const W = 340, top = 8, rh = 42, L0 = 138, R0 = 8, y0 = 2001, y1 = 2025, H = top + sites.length * rh + 22;
  const x = (iso: string) => { const [yy, mm] = iso.split("-").map(Number); return L0 + ((yy + (mm - 1) / 12 - y0) / (y1 - y0)) * (W - L0 - R0); };
  return `<svg class="tr-cap land-chart" viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(LL("Sequías auditadas por lugar y año, coloreadas por su veredicto", "Audited droughts by site and year, coloured by verdict"))}">
    ${sites.map((s, i) => {
      const y = top + i * rh + rh / 2;
      return `<g class="land-row ${s.id === focus ? "on" : ""}" data-site="${s.id}">
        <rect x="0" y="${y - rh / 2 + 2}" width="${W}" height="${rh - 4}" rx="8" class="land-bg"/>
        <text x="8" y="${y + 4}" class="cap-p">${esc(s.nombre)}</text>
        <line x1="${L0}" x2="${W - R0}" y1="${y}" y2="${y}" class="land-axis"/>
        ${L.audits.filter((a) => a.id === s.id).map((a) => {
          const c = VCOL[a.veredicto] ?? "#8a8c92", none = a.veredicto === "sin_impacto", hollow = a.veredicto === "inconclusa";
          const tip = `${a.evento_inicio.slice(0, 7)} · ${t.verdictName[a.veredicto] ?? a.veredicto}${none ? "" : ` · ${LL("estable en", "stable in")} ${Math.round(a.estabilidad * a.combinaciones)}/${a.combinaciones} ${LL("definiciones", "definitions")}`}. ${(t as unknown as { verdictWhy: Record<string, string> }).verdictWhy[a.veredicto] ?? ""}`;
          return `<circle cx="${x(a.evento_inicio).toFixed(1)}" cy="${y}" r="${none ? 3 : 6}" fill="${hollow ? "var(--surface)" : c}" stroke="${c}" stroke-width="${hollow ? 2 : 0}"><title>${esc(tip)}</title></circle>`;
        }).join("")}
      </g>`;
    }).join("")}
    ${[2001, 2008, 2016, 2024].map((yy) => `<text x="${x(`${yy}-01`)}" y="${H - 4}" text-anchor="middle" class="cap-t num">${yy}</text>`).join("")}
  </svg>`;
}

export function recuperaAnswer(L: Land, focus: string) {
  const t = T(), imp = L.audits.filter((a) => a.veredicto !== "sin_impacto");
  const count = (k: string) => imp.filter((a) => a.veredicto === k).length;
  const stable = imp.filter((a) => a.estabilidad >= 2 / 3).length;
  const cats = VORDER.filter((k) => L.audits.some((a) => a.veredicto === k));
  return `${recoveryRibbon(L, focus)}
    <p class="land-legend">${cats.map((k) => `<span title="${esc((t as unknown as { verdictWhy: Record<string, string> }).verdictWhy[k] ?? "")}"><i style="--c:${VCOL[k]}" class="${k === "inconclusa" ? "hollow" : ""}"></i>${esc(t.verdictName[k] ?? k)} <b class="num">${L.audits.filter((a) => a.veredicto === k).length}</b></span>`).join("")}</p>
    <p class="ans-sent">${esc(t.verdictLead(imp.length, count("fantasma"), count("estres_invisible"), count("censurada"), count("inconclusa")))}</p>
    <p class="ans-why"><b>${esc(LL("¿Es robusto?", "Is it robust?"))}</b> ${esc(LL(`Cada sequía se juzga con 18 definiciones de «recuperado». ${stable} de ${imp.length} veredictos se repiten en al menos 2 de cada 3; el resto depende de la definición, y por eso se declaran inconclusos en vez de forzar un sí.`, `Each drought is judged with 18 definitions of "recovered". ${stable} of ${imp.length} verdicts repeat in at least 2 of every 3; the rest depend on the definition, so they are declared inconclusive instead of forcing a yes.`))}</p>
    <p class="ans-why"><b>${esc(LL("Por qué importa", "Why it matters"))}</b> ${esc(LL("Un bosque puede volver a verse verde sin haber vuelto a funcionar. Comparar verdor, función y temperatura de las hojas tras cada sequía separa la recuperación real de la aparente.", "A forest can look green again without working again. Comparing greenness, function and leaf temperature after each drought separates real recovery from apparent recovery."))}</p>
    <details class="ans-more">
      <summary>${esc(LL("Cómo se decide", "How it is decided"))}<svg class="chev" viewBox="0 0 12 12" aria-hidden="true"><path d="M3 4.5l3 3 3-3" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg></summary>
      <p class="rule">${esc(LL("Sequía: SPI-3 de IMERG. Señales MODIS: verdor (NDVI, EVI), función (GPP, modelo) y temperatura de las hojas frente al aire (LST menos aire). z robusto frente a la misma época del año; impacto: z < −1,5 durante 3 observaciones; recuperado: z ≥ −1 durante 3. La GPP sola no cuenta como evidencia de estrés.", "Drought: IMERG SPI-3. MODIS signals: greenness (NDVI, EVI), function (GPP, model) and leaf temperature against the air (LST minus air). Robust z against the same time of year; impact: z < −1.5 for 3 observations; recovered: z ≥ −1 for 3. GPP alone does not count as stress evidence."))}</p>
    </details>`;
}

/** Marcadores de los lugares sobre el mapa (encima de las crestas); siguen la cámara como ellas. */
export function sitesLayer(host: HTMLElement, proj: () => ((lon: number, lat: number) => { x: number; y: number }) | null) {
  const el = document.createElement("div");
  el.className = "sites";
  el.hidden = true;
  host.appendChild(el);
  let items: { id: string; lon: number; lat: number }[] = [];
  const place = () => {
    const pr = proj();
    if (!pr || el.hidden) return;
    el.querySelectorAll<HTMLElement>(".site").forEach((n, i) => { const p = pr(items[i].lon, items[i].lat); n.style.transform = `translate(${p.x.toFixed(1)}px, ${p.y.toFixed(1)}px)`; });
  };
  return {
    set(list: { id: string; lon: number; lat: number; color: string; filled: boolean; title: string; on: boolean }[]) {
      items = list;
      el.hidden = !list.length;
      el.innerHTML = list.map((s) => `<button class="site ${s.filled ? "" : "hollow"} ${s.on ? "on" : ""}" style="--c:${s.color}" data-site="${s.id}" title="${esc(s.title)}" aria-label="${esc(s.title)}"><i></i></button>`).join("");
      place();
    },
    place,
    destroy() { el.remove(); },
  };
}

/** Color y título del marcador de cada lugar según la pregunta. */
export function siteMarks(L: Land, q: LandQ, v: string, focus: string) {
  return L.sites.map((s) => {
    if (q === "recupera") {
      const imp = L.audits.filter((a) => a.id === s.id && a.veredicto !== "sin_impacto");
      const hot = imp.some((a) => a.veredicto === "estres_invisible");
      return { id: s.id, lon: s.lon, lat: s.lat, color: hot ? WORSE : "#ffffff", filled: imp.length > 0, on: s.id === focus,
        title: `${s.nombre}: ${imp.length} ${LL("sequías con impacto", "droughts with impact")}` };
    }
    const t = s.tendencias[v];
    return { id: s.id, lon: s.lon, lat: s.lat, color: t ? tone(v, t.pendiente_decada) : "#8a8c92", filled: !!t && landSig(t), on: s.id === focus,
      title: t ? `${s.nombre}: ${sgn(t.pendiente_decada, dig(v))} ${LL("por década", "per decade")}, p ${t.p_mk < 0.001 ? "< 0,001" : num(t.p_mk, 3)}` : s.nombre };
  });
}

/** La línea de la hoja plegada del teléfono para las preguntas de la vegetación. */
export function landPeek(L: Land, q: LandQ, v: string) {
  const qq = LAND_Q.find((x) => x.id === q);
  const head = qq ? `<span class="pa-q">${esc(LL(qq.es, qq.en))}</span>` : "";
  if (q === "recupera") {
    const imp = L.audits.filter((a) => a.veredicto !== "sin_impacto");
    return `${head}<span class="pa-w"><b class="num">${imp.length}</b> ${esc(LL("sequías con impacto", "droughts with impact"))}</span><span class="pa-w"><b class="num">${imp.filter((a) => a.veredicto === "estres_invisible").length}</b> ${esc(LL("estrés invisible", "invisible stress"))}</span>`;
  }
  const rows = L.sites.filter((s) => s.tendencias[v]), k = rows.filter((s) => landSig(s.tendencias[v])).length;
  return `${head}<span class="pa-w"><b class="num">${k}/${rows.length}</b> ${esc(LL("lugares con cambio claro", "sites with a clear change"))} · ${esc(LL(...SHORT[v]))}</span>`;
}
