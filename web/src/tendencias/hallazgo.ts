// Lo que encontramos sobre IMERG: el hallazgo central de la investigación, con sus cifras y sus límites.
// Cifras de reports_nacional/ESTADO_CONCLUSIONES.md (filas 4, 4c, 7b, 8b y 8c) y de las réplicas con pluviómetros en
// Puerto Rico y Hawái (results/tropical/puerto_rico, hawaii y era_gpm). Si ese informe cambia, manda el informe.
import { esc, LL } from "./datos";
import "./hallazgo.css";

const C_IMERG = "#ffffff", C_CHIRPS = "#8fd3ff", C_OTRO = "#ffb347";

const nf = (v: number) => `${v > 0 ? "+" : ""}${v.toLocaleString(LL("es-DO", "en-US"))}`;

/** Puntos sobre un eje (sin barras): una fila por producto, el punto en su cambio y la línea del cero. */
function dots(rows: [string, number, string][], lo: number, hi: number, unit = "pp") {
  const W = 360, L = 80, R = 24, rh = 26, T = 6, H = T + rows.length * rh + 22;
  const x = (v: number) => L + ((v - lo) / (hi - lo)) * (W - L - R), x0 = x(0);
  let out = `<line x1="${x0}" x2="${x0}" y1="${T - 2}" y2="${H - 20}" stroke="#5b6066" stroke-width="1.5" stroke-linecap="round"/>`;
  rows.forEach(([name, v, col], i) => {
    const y = T + i * rh + rh / 2;
    out += `<text x="${L - 10}" y="${y + 4}" text-anchor="end" fill="#d6d6d6" font-size="12">${esc(name)}</text>
      <line x1="${x0}" x2="${x(v).toFixed(1)}" y1="${y}" y2="${y}" stroke="${col}" stroke-opacity=".35" stroke-width="2" stroke-dasharray="2 3" stroke-linecap="round"/>
      <circle cx="${x(v).toFixed(1)}" cy="${y}" r="6" fill="${col}"><title>${esc(`${name}: ${nf(v)} ${unit}`)}</title></circle>
      <text x="${(x(v) + (v < 0 ? -12 : 12)).toFixed(1)}" y="${y + 4}" text-anchor="${v < 0 ? "end" : "start"}" fill="${col}" font-size="12" font-weight="700">${nf(v)}</text>`;
  });
  out += `<text x="${x0}" y="${H - 6}" text-anchor="middle" fill="#949494" font-size="11">0 ${unit}</text>`;
  return `<svg class="hz-c" viewBox="0 0 ${W} ${H}" role="img">${out}</svg>`;
}

/** Dos líneas con puntos: el cambio de cada producto según el umbral del día lluvioso, con la línea del cero. */
function lines(xs: string[], series: [string, number[], string][], lo: number, hi: number) {
  const W = 360, L = 40, R = 52, T = 12, B = 30, H = 200;
  const x = (i: number) => L + (i / (xs.length - 1)) * (W - L - R), y = (v: number) => T + ((hi - v) / (hi - lo)) * (H - T - B);
  let out = [hi, 0, lo].map((v) => `<line x1="${L}" x2="${W - R}" y1="${y(v)}" y2="${y(v)}" stroke="${v === 0 ? "#5b6066" : "#2a2d31"}" stroke-width="${v === 0 ? 1.5 : 1}"/><text x="${L - 8}" y="${y(v) + 4}" text-anchor="end" fill="#949494" font-size="11">${nf(v)}</text>`).join("");
  out += xs.map((k, i) => `<text x="${x(i)}" y="${H - 10}" text-anchor="middle" fill="#949494" font-size="11">${esc(k)}</text>`).join("");
  for (const [name, vs, col] of series) {
    out += `<path d="${vs.map((v, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join("")}" fill="none" stroke="${col}" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>`;
    out += vs.map((v, i) => `<circle cx="${x(i).toFixed(1)}" cy="${y(v).toFixed(1)}" r="4.5" fill="${col}"><title>${esc(`${name} · ${xs[i]}: ${nf(v)} pp`)}</title></circle>`).join("");
    // el nombre va junto al primer punto, donde las líneas están más separadas
    out += `<text x="${(x(0) + 10).toFixed(1)}" y="${(y(vs[0]) + (vs[0] < 0 ? 18 : -10)).toFixed(1)}" fill="${col}" font-size="12" font-weight="700">${esc(name)}</text>`;
  }
  return `<svg class="hz-c" viewBox="0 0 ${W} ${H}" role="img">${out}</svg>`;
}

type Est = { estaciones: { id: string; lat: number; lon: number; [k: string]: number | string }[]; resumen: { estaciones: number; imerg_cae_mas: number; mediana_cambio_pp: Record<string, number> } };
type Era = { medias_anuales_pp: Record<string, number>; paso_era_pp: number; paso_2018_pp: number };
export interface Hallazgos {
  hi?: Est;
  era_gpm?: { hawaii: Era; puerto_rico: Era; rd_imerg_menos_chirps: Era };
  alcance?: Record<string, number>;
  merra2: { lat: number; lon: number; IMERG: number; CHIRPS: number; MERRA2: number }[];
  pr: { estaciones: { id: string; lat: number; lon: number; [k: string]: number | string }[]; resumen: { estaciones: number; imerg_cae_mas: number; mediana_cambio_pp: Record<string, number> } };
  ciclones_sequia: { fraccion_ciclon_media: number; fraccion_ciclon_rango: [number, number]; p_permutacion_S2: number; frac_dias_sequia_90d_tras_ciclon: number; frac_dias_sequia_resto_ago_dic: number };
}
const fmt = (v: number, d = Math.abs(v) < 0.1 && v !== 0 ? 2 : 1) => `${v > 0 ? "+" : ""}${v.toLocaleString(LL("es-DO", "en-US"), { maximumFractionDigits: d, minimumFractionDigits: d })}`;

/** Tres mapas del mismo territorio: un cuadro por recuadro MERRA-2, color por el cambio (azul sube, naranja baja). */
function tresMapas(cells: Hallazgos["merra2"]) {
  const lons = [...new Set(cells.map((c) => c.lon))].sort((a, b) => a - b), lats = [...new Set(cells.map((c) => c.lat))].sort((a, b) => b - a);
  const S = 26, G = 3, w = lons.length * (S + G), h = lats.length * (S + G);
  const col = (v: number) => { const k = Math.min(1, Math.abs(v) / 15); return v < 0 ? `rgba(255,107,53,${0.25 + 0.75 * k})` : `rgba(100,190,255,${0.25 + 0.75 * k})`; };
  const one = (key: "IMERG" | "CHIRPS" | "MERRA2", name: string) => {
    const vals = cells.map((c) => c[key]).sort((a, b) => a - b), med = vals[vals.length >> 1];
    return `<figure class="hz-map"><figcaption><b>${name}</b><span class="${med < 0 ? "dn" : "up"}">${fmt(med)} pp</span></figcaption>
      <svg viewBox="0 0 ${w} ${h}" role="img" aria-label="${esc(`${name}: ${cells.length} recuadros`)}">${cells.map((c) => {
        const x = lons.indexOf(c.lon) * (S + G), y = lats.indexOf(c.lat) * (S + G);
        return `<rect x="${x}" y="${y}" width="${S}" height="${S}" rx="5" fill="${col(c[key])}"><title>${c.lat}, ${c.lon}: ${fmt(c[key])} pp</title></rect>`;
      }).join("")}</svg></figure>`;
  };
  return `<div class="hz-maps">${one("IMERG", "IMERG")}${one("CHIRPS", "CHIRPS")}${one("MERRA2", "MERRA-2")}</div>
    <p class="hz-key"><span style="--k:#ff6b35">${esc(LL("menos días de lluvia", "fewer rain days"))}</span><span style="--k:#64beff">${esc(LL("más días de lluvia", "more rain days"))}</span></p>`;
}

/** Cada estación: el cambio del pluviómetro y el de IMERG en su celda (puntos pareados). */
function puertoRico(pr: Est, label = LL(`${pr.estaciones.length} estaciones: cambio del pluviómetro y de IMERG`, `${pr.estaciones.length} stations: gauge and IMERG change`)) {
  const st = [...pr.estaciones].map((e) => ({ id: e.id, g: e["cambio_pluvio_pp_1.0"] as number, i: e["cambio_imerg_pp_1.0"] as number })).sort((a, b) => (a.i - a.g) - (b.i - b.g));
  const W = 360, L = 14, R = 14, rh = 11, T = 18, H = T + st.length * rh + 22, lo = -17, hi = 13;
  const x = (v: number) => L + ((v - lo) / (hi - lo)) * (W - L - R);
  const rows = st.map((e, k) => { const y = T + k * rh + rh / 2;
    return `<line x1="${x(e.g).toFixed(1)}" x2="${x(e.i).toFixed(1)}" y1="${y}" y2="${y}" stroke="${e.i < e.g ? "#ff6b35" : "#5b6066"}" stroke-width="2" stroke-linecap="round"/>
      <circle cx="${x(e.g).toFixed(1)}" cy="${y}" r="3.5" fill="#8fd3ff"><title>${esc(`${e.id} · ${LL("pluviómetro", "gauge")} ${fmt(e.g)} pp`)}</title></circle>
      <circle cx="${x(e.i).toFixed(1)}" cy="${y}" r="3.5" fill="#ffffff"><title>${esc(`${e.id} · IMERG ${fmt(e.i)} pp`)}</title></circle>`; }).join("");
  const ticks = [-15, -10, -5, 0, 5, 10].map((t) => `<text x="${x(t)}" y="${H - 6}" text-anchor="middle" fill="#949494" font-size="11">${t > 0 ? "+" : ""}${t}</text>`).join("");
  return `<svg class="hz-c" viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(label)}">
    <line x1="${x(0)}" x2="${x(0)}" y1="${T - 4}" y2="${H - 18}" stroke="#3a3e44" stroke-width="1.5"/>${rows}${ticks}</svg>`;
}

/** Dos escalones: media anual de (IMERG − testigo) en Hawái, Puerto Rico y la RD; 2014 sombreado (paso a la era GPM). */
function escalones(e: NonNullable<Hallazgos["era_gpm"]>) {
  const S: [string, Era, string][] = [[LL("Hawái", "Hawaii"), e.hawaii, C_OTRO], ["Puerto Rico", e.puerto_rico, C_CHIRPS], [LL("RD (frente a CHIRPS)", "DR (vs CHIRPS)"), e.rd_imerg_menos_chirps, C_IMERG]];
  const ys = Object.keys(e.hawaii.medias_anuales_pp).map(Number), y0 = ys[0], y1 = ys[ys.length - 1];
  const W = 360, L = 34, R = 10, T = 10, B = 26, H = 210, lo = -18, hi = 9;
  const x = (yr: number) => L + ((yr - y0) / (y1 - y0)) * (W - L - R), y = (v: number) => T + ((hi - v) / (hi - lo)) * (H - T - B);
  let out = `<rect x="${x(2013.5)}" y="${T}" width="${x(2014.5) - x(2013.5)}" height="${H - T - B}" fill="#2a2d31"/>
    <text x="${x(2014)}" y="${T + 11}" text-anchor="middle" fill="#949494" font-size="12">GPM</text>
    <line x1="${x(2018)}" x2="${x(2018)}" y1="${T}" y2="${H - B}" stroke="#3a3e44" stroke-width="1" stroke-dasharray="3 3"/>`;
  out += [5, 0, -5, -10, -15].map((v) => `<line x1="${L}" x2="${W - R}" y1="${y(v)}" y2="${y(v)}" stroke="${v === 0 ? "#5b6066" : "#24272b"}" stroke-width="${v === 0 ? 1.5 : 1}"/><text x="${L - 6}" y="${y(v) + 4}" text-anchor="end" fill="#949494" font-size="12">${nf(v)}</text>`).join("");
  out += [2001, 2006, 2010, 2014, 2018, 2024].map((t) => `<text x="${x(t)}" y="${H - 8}" text-anchor="middle" fill="#949494" font-size="12">${t}</text>`).join("");
  for (const [name, s, col] of S) {
    const pts = ys.map((yr) => [x(yr), y(s.medias_anuales_pp[String(yr)])] as const);
    out += `<path d="${pts.map(([a, b], i) => `${i ? "L" : "M"}${a.toFixed(1)},${b.toFixed(1)}`).join("")}" fill="none" stroke="${col}" stroke-width="2" stroke-opacity=".9" stroke-linejoin="round"/>`;
    out += pts.map(([a, b], i) => `<circle cx="${a.toFixed(1)}" cy="${b.toFixed(1)}" r="2.6" fill="${col}"><title>${esc(`${name} · ${ys[i]}: ${nf(s.medias_anuales_pp[String(ys[i])])} pp`)}</title></circle>`).join("");
  }
  return `<svg class="hz-c" viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(LL("Media anual de IMERG menos el testigo, 2001-2024", "Annual mean of IMERG minus the witness, 2001-2024"))}">${out}</svg>
    <p class="hz-key">${S.map(([n, , c]) => `<span style="--k:${c}">${esc(n)}</span>`).join("")}</p>`;
}

export function hallazgo(h: Hallazgos | null = null) {
  return `<section class="hz" aria-labelledby="hz-h">
    <h3 id="hz-h">${esc(LL("Lo que encontramos sobre IMERG", "What we found about IMERG"))}</h3>
    <p class="hz-lead">${esc(LL("Lo que más cambia en la lluvia medida por satélite en la RD es cómo IMERG cuenta los días de lluvia, no necesariamente la lluvia.", "What changes most in satellite-measured rain in the DR is how IMERG counts rain days, not necessarily the rain."))}</p>

    <div class="hz-b">
      <h4>${esc(LL("La pérdida está en la lluvia ligera", "The loss is in light rain"))}</h4>
      <p>${esc(LL("Días con lluvia, después menos antes de 2018-02, celdas de tierra, según el umbral del día lluvioso:", "Rain days, after minus before 2018-02, land cells, by rain-day threshold:"))}</p>
      ${lines(["0,1 mm", "0,5 mm", "1 mm", "2 mm", "5 mm"], [["IMERG", [-7.2, -5.8, -4.8, -3.6, -2.0], C_IMERG], ["CHIRPS", [1.4, 0.8, 0.3, -0.6, -1.4], C_CHIRPS]], -8, 2)}
      <p class="hz-n">${esc(LL("Cuanto más débil la lluvia que cuenta como día lluvioso, más se separan: la brecha se abre hacia la llovizna.", "The weaker the rain that counts as a rainy day, the wider the gap: it opens towards drizzle."))}</p>
      <p class="hz-n">${esc(LL("Crece hacia los días casi secos. El ajuste mensual con pluviómetros (GPCC) no cambia si llueve o no: no puede fabricar esta caída. CHIRPS diario a umbral muy bajo es poco fiable.", "It grows towards nearly dry days. The monthly gauge adjustment (GPCC) does not change whether it rains: it cannot create this drop. Daily CHIRPS at very low thresholds is unreliable."))}</p>
    </div>

    <div class="hz-b">
      <h4>${esc(LL("Mismo territorio, tres tendencias opuestas", "Same territory, three opposite trends"))}</h4>
      <p>${esc(LL("Días con 1 mm o más, después menos antes de 2018-02, en los 15 recuadros que cubren el país (mediana arriba):", "Days with 1 mm or more, after minus before 2018-02, in the 15 boxes covering the country (median above):"))}</p>
      ${h ? tresMapas(h.merra2) : dots([["IMERG", -5.1, C_IMERG], ["CHIRPS", 0.04, C_CHIRPS], ["MERRA-2", 8.6, C_OTRO]], -7, 10)}
      <p class="hz-n">${esc(LL("IMERG cae en las 15 celdas. MERRA-2 sube, pero tiene su propio salto en 2015-11: no sirve de testigo.", "IMERG drops in all 15 cells. MERRA-2 rises, but has its own jump in 2015-11: it cannot serve as a witness."))}</p>
    </div>

    <div class="hz-b">
      <h4>${esc(LL("Frente a ERA5, en 6 lugares", "Against ERA5, at 6 places"))}</h4>
      ${dots([["IMERG", -6.1, C_IMERG], ["ERA5", -1.9, C_OTRO], ["CHIRPS", -0.2, C_CHIRPS]], -7, 1)}
      <p class="hz-n">${esc(LL("Y en 4 pluviómetros dominicanos IMERG cae más en los 4. Son pocos lugares, e IMERG usa ERA5 como dato auxiliar.", "And at 4 Dominican rain gauges IMERG drops more at all 4. Few places, and IMERG uses ERA5 as ancillary input."))}</p>
    </div>

    <div class="hz-b hz-pr">
      <h4>${esc(LL("¿Pasa fuera de la RD? Puerto Rico, la isla vecina", "Does it happen outside the DR? Puerto Rico, next door"))} <em class="${h ? "ok" : ""}">${esc(h ? LL("se cumple", "confirmed") : LL("en curso", "in progress"))}</em></h4>
      ${h ? `<p class="hz-big"><b>${h.pr.resumen.imerg_cae_mas} ${esc(LL("de", "of"))} ${h.pr.resumen.estaciones}</b> ${esc(LL("pluviómetros: IMERG pierde días de lluvia y el pluviómetro no.", "rain gauges: IMERG loses rain days and the gauge does not."))}</p>
      <p>${esc(LL("Días con 1 mm o más, después menos antes de 2018-02, cada estación frente a la celda IMERG que la contiene:", "Days with 1 mm or more, after minus before 2018-02, each station against the IMERG cell containing it:"))}</p>
      <p class="hz-key"><span style="--k:#8fd3ff">${esc(LL("pluviómetro", "rain gauge"))} ${fmt(h.pr.resumen.mediana_cambio_pp["cambio_pluvio_pp_1.0"])}</span><span style="--k:#ffffff">IMERG ${fmt(h.pr.resumen.mediana_cambio_pp["cambio_imerg_pp_1.0"])}</span><span>${esc(LL("medianas, pp", "medians, pp"))}</span></p>
      ${puertoRico(h.pr)}
      <p class="hz-n">${esc(LL(`Misma firma de llovizna que en la RD: con 0,1 mm, IMERG ${fmt(h.pr.resumen.mediana_cambio_pp["cambio_imerg_pp_0.1"])} y pluviómetros ${fmt(h.pr.resumen.mediana_cambio_pp["cambio_pluvio_pp_0.1"])}; con 5 mm, ${fmt(h.pr.resumen.mediana_cambio_pp["cambio_imerg_pp_5.0"])} y ${fmt(h.pr.resumen.mediana_cambio_pp["cambio_pluvio_pp_5.0"])}. Las tres predicciones registradas antes de descargar se cumplen.`, `Same drizzle signature as in the DR: at 0.1 mm, IMERG ${fmt(h.pr.resumen.mediana_cambio_pp["cambio_imerg_pp_0.1"])} and gauges ${fmt(h.pr.resumen.mediana_cambio_pp["cambio_pluvio_pp_0.1"])}; at 5 mm, ${fmt(h.pr.resumen.mediana_cambio_pp["cambio_imerg_pp_5.0"])} and ${fmt(h.pr.resumen.mediana_cambio_pp["cambio_pluvio_pp_5.0"])}. All three predictions registered before downloading hold.`))}</p>`
      : `<p>${esc(LL("La isla vecina, con muchos pluviómetros (GHCN-D).", "The neighbouring island, with many rain gauges (GHCN-D)."))}</p>`}
    </div>
${h?.hi ? `
    <div class="hz-b hz-pr">
      <h4>${esc(LL("En otro océano: Hawái", "In another ocean: Hawaii"))} <em class="ok">${esc(LL("se cumple", "confirmed"))}</em></h4>
      <p class="hz-big"><b>${h.hi.resumen.imerg_cae_mas} ${esc(LL("de", "of"))} ${h.hi.resumen.estaciones}</b> ${esc(LL("pluviómetros: IMERG pierde días y el pluviómetro no.", "rain gauges: IMERG loses days and the gauge does not."))}</p>
      <p>${esc(LL("Hawái lo vigila otro satélite geoestacionario (GOES-West). Si la causa fuera solo el GOES-16 del Caribe, aquí no pasaría. Mismo cálculo que en Puerto Rico:", "Hawaii is watched by another geostationary satellite (GOES-West). If the cause were only the Caribbean's GOES-16, it would not happen here. Same calculation as in Puerto Rico:"))}</p>
      <p class="hz-key"><span style="--k:#8fd3ff">${esc(LL("pluviómetro", "rain gauge"))} ${fmt(h.hi.resumen.mediana_cambio_pp["cambio_pluvio_pp_1.0"])}</span><span style="--k:#ffffff">IMERG ${fmt(h.hi.resumen.mediana_cambio_pp["cambio_imerg_pp_1.0"])}</span><span>${esc(LL("medianas, pp", "medians, pp"))}</span></p>
      ${puertoRico(h.hi)}
      <p class="hz-n">${esc(LL(`Con Puerto Rico suman ${h.hi.resumen.estaciones + h.pr.resumen.estaciones} pluviómetros en dos océanos. No es una rareza dominicana.`, `With Puerto Rico, ${h.hi.resumen.estaciones + h.pr.resumen.estaciones} rain gauges in two oceans. It is not a Dominican quirk.`))}</p>
    </div>` : ""}
${h?.era_gpm ? `
    <div class="hz-b">
      <h4>${esc(LL("Llega en dos escalones", "It comes in two steps"))}</h4>
      <p>${esc(LL("Media de cada año de IMERG menos su testigo (pluviómetros; en la RD, CHIRPS), en puntos porcentuales de días con 1 mm o más:", "Yearly mean of IMERG minus its witness (gauges; in the DR, CHIRPS), percentage points of days with 1 mm or more:"))}</p>
      ${escalones(h.era_gpm)}
      <p class="hz-n">${esc(LL(`Primero hacia 2014, con el paso de la era TRMM a la era GPM: Hawái ${fmt(h.era_gpm.hawaii.paso_era_pp)}, Puerto Rico ${fmt(h.era_gpm.puerto_rico.paso_era_pp)} pp. Después de 2018, solo en el Caribe: Puerto Rico ${fmt(h.era_gpm.puerto_rico.paso_2018_pp)}, RD ${fmt(h.era_gpm.rd_imerg_menos_chirps.paso_2018_pp)}, Hawái ${fmt(h.era_gpm.hawaii.paso_2018_pp)}. Habíamos predicho 2018 para todo: esa fecha falló.`, `First around 2014, with the switch from the TRMM era to the GPM era: Hawaii ${fmt(h.era_gpm.hawaii.paso_era_pp)}, Puerto Rico ${fmt(h.era_gpm.puerto_rico.paso_era_pp)} pp. After 2018, only in the Caribbean: Puerto Rico ${fmt(h.era_gpm.puerto_rico.paso_2018_pp)}, DR ${fmt(h.era_gpm.rd_imerg_menos_chirps.paso_2018_pp)}, Hawaii ${fmt(h.era_gpm.hawaii.paso_2018_pp)}. We had predicted 2018 for everything: that date failed.`))}</p>
    </div>` : ""}

    <p class="hz-open"><b>${esc(LL("Lo que no sabemos:", "What we do not know:"))}</b> ${esc(LL("la causa exacta. Hawái descarta que sea solo el GOES-16; el escalón caribeño de 2018 es compatible con él, sin probar. El propio equipo de IMERG (Joyce, Huffman y otros, EGU 2026) reconoce sesgos sistemáticos e inhomogeneidades en las entradas de microondas de la versión 7 y los corrige en la 8: es compatible con lo que vemos, no lo confirma. Tampoco afirmamos que la lluvia real de la RD haya cambiado: allí faltan pluviómetros densos.", "the exact cause. Hawaii rules out GOES-16 alone; the Caribbean 2018 step is compatible with it, unproven. The IMERG team itself (Joyce, Huffman et al., EGU 2026) acknowledges systematic biases and inhomogeneities in version 7 microwave inputs and fixes them in version 8: compatible with what we see, not a confirmation. Nor do we claim the DR's real rain changed: it lacks dense rain gauges there."))}</p>
  </section>`;
}
