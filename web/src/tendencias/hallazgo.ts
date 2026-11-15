// Lo que encontramos sobre IMERG: el hallazgo central de la investigación, con sus cifras y sus límites.
// Cifras de reports_nacional/ESTADO_CONCLUSIONES.md (filas 4, 4c y 7b) y de la réplica en Puerto Rico
// (results/tropical/puerto_rico/predicciones_registradas.json). Si ese informe cambia, manda el informe.
import { esc, LL } from "./datos";
import "./hallazgo.css";

const C_IMERG = "#ffffff", C_CHIRPS = "#8fd3ff", C_OTRO = "#ffb347";

/** Barras divergentes en puntos porcentuales: una fila por categoría, una barra por producto. */
function bars(rows: { k: string; v: [string, number, string][] }[], lo: number, hi: number, unit = "pp") {
  const W = 360, L = 96, R = 44, rh = 15, gap = 10;
  const H = rows.reduce((s, r) => s + r.v.length * rh + gap, 0) + 20;
  const x = (v: number) => L + ((v - lo) / (hi - lo)) * (W - L - R), x0 = x(0);
  let y = 4, out = "";
  for (const r of rows) {
    const h = r.v.length * rh;
    out += `<text x="${L - 8}" y="${y + h / 2 + 4}" text-anchor="end" fill="#d6d6d6" font-size="12">${esc(r.k)}</text>`;
    r.v.forEach(([name, v, col], i) => {
      const yy = y + i * rh + 2, a = Math.min(x(v), x0), w = Math.max(2, Math.abs(x(v) - x0));
      out += `<rect x="${a.toFixed(1)}" y="${yy}" width="${w.toFixed(1)}" height="${rh - 4}" rx="3" fill="${col}"><title>${esc(`${name}: ${v > 0 ? "+" : ""}${v.toLocaleString(LL("es-DO", "en-US"))} ${unit}`)}</title></rect>`;
      out += `<text x="${(v < 0 ? a - 4 : a + w + 4).toFixed(1)}" y="${yy + rh - 6}" text-anchor="${v < 0 ? "end" : "start"}" fill="${col}" font-size="11" font-weight="600">${v > 0 ? "+" : ""}${v.toLocaleString(LL("es-DO", "en-US"))}</text>`;
    });
    y += h + gap;
  }
  out += `<line x1="${x0}" x2="${x0}" y1="0" y2="${y - gap + 2}" stroke="#5b6066" stroke-width="1.5" stroke-linecap="round"/>`;
  out += `<text x="${x0}" y="${y + 10}" text-anchor="middle" fill="#949494" font-size="11">0 ${unit}</text>`;
  return `<svg class="hz-c" viewBox="0 0 ${W} ${H}" role="img">${out}</svg>`;
}

export interface Hallazgos {
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

/** Puerto Rico: cada estación, el cambio del pluviómetro y el de IMERG en su celda (puntos pareados). */
function puertoRico(pr: Hallazgos["pr"]) {
  const st = [...pr.estaciones].map((e) => ({ id: e.id, g: e["cambio_pluvio_pp_1.0"] as number, i: e["cambio_imerg_pp_1.0"] as number })).sort((a, b) => (a.i - a.g) - (b.i - b.g));
  const W = 360, L = 14, R = 14, rh = 11, T = 18, H = T + st.length * rh + 22, lo = -16, hi = 12;
  const x = (v: number) => L + ((v - lo) / (hi - lo)) * (W - L - R);
  const rows = st.map((e, k) => { const y = T + k * rh + rh / 2;
    return `<line x1="${x(e.g).toFixed(1)}" x2="${x(e.i).toFixed(1)}" y1="${y}" y2="${y}" stroke="${e.i < e.g ? "#ff6b35" : "#5b6066"}" stroke-width="2" stroke-linecap="round"/>
      <circle cx="${x(e.g).toFixed(1)}" cy="${y}" r="3.5" fill="#8fd3ff"><title>${esc(`${e.id} · ${LL("pluviómetro", "gauge")} ${fmt(e.g)} pp`)}</title></circle>
      <circle cx="${x(e.i).toFixed(1)}" cy="${y}" r="3.5" fill="#ffffff"><title>${esc(`${e.id} · IMERG ${fmt(e.i)} pp`)}</title></circle>`; }).join("");
  const ticks = [-15, -10, -5, 0, 5, 10].map((t) => `<text x="${x(t)}" y="${H - 6}" text-anchor="middle" fill="#949494" font-size="10">${t > 0 ? "+" : ""}${t}</text>`).join("");
  return `<svg class="hz-c" viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(LL("19 estaciones de Puerto Rico: cambio del pluviómetro y de IMERG", "19 Puerto Rico stations: gauge and IMERG change"))}">
    <line x1="${x(0)}" x2="${x(0)}" y1="${T - 4}" y2="${H - 18}" stroke="#3a3e44" stroke-width="1.5"/>${rows}${ticks}</svg>`;
}

export function hallazgo(h: Hallazgos | null = null) {
  const key = (items: [string, string][]) => `<p class="hz-key">${items.map(([c, l]) => `<span style="--k:${c}">${esc(l)}</span>`).join("")}</p>`;
  return `<section class="hz" aria-labelledby="hz-h">
    <h3 id="hz-h">${esc(LL("Lo que encontramos sobre IMERG", "What we found about IMERG"))}</h3>
    <p class="hz-lead">${esc(LL("Lo que más cambia en la lluvia medida por satélite en la RD es cómo IMERG cuenta los días de lluvia, no necesariamente la lluvia.", "What changes most in satellite-measured rain in the DR is how IMERG counts rain days, not necessarily the rain."))}</p>

    <div class="hz-b">
      <h4>${esc(LL("La pérdida está en la lluvia ligera", "The loss is in light rain"))}</h4>
      <p>${esc(LL("Días con lluvia, después menos antes de 2018-02, celdas de tierra, según el umbral del día lluvioso:", "Rain days, after minus before 2018-02, land cells, by rain-day threshold:"))}</p>
      ${key([[C_IMERG, "IMERG"], [C_CHIRPS, "CHIRPS"]])}
      ${bars([["0,1 mm", -7.2, 1.4], ["0,5 mm", -5.8, 0.8], ["1 mm", -4.8, 0.3], ["2 mm", -3.6, -0.6], ["5 mm", -2.0, -1.4]].map(([k, a, b]) => ({ k: String(k), v: [["IMERG", a as number, C_IMERG], ["CHIRPS", b as number, C_CHIRPS]] as [string, number, string][] })), -8, 2)}
      <p class="hz-n">${esc(LL("Crece hacia los días casi secos. El ajuste mensual con pluviómetros (GPCC) no cambia si llueve o no: no puede fabricar esta caída. CHIRPS diario a umbral muy bajo es poco fiable.", "It grows towards nearly dry days. The monthly gauge adjustment (GPCC) does not change whether it rains: it cannot create this drop. Daily CHIRPS at very low thresholds is unreliable."))}</p>
    </div>

    <div class="hz-b">
      <h4>${esc(LL("Mismo territorio, tres tendencias opuestas", "Same territory, three opposite trends"))}</h4>
      <p>${esc(LL("Días con 1 mm o más, después menos antes de 2018-02, en los 15 recuadros que cubren el país (mediana arriba):", "Days with 1 mm or more, after minus before 2018-02, in the 15 boxes covering the country (median above):"))}</p>
      ${h ? tresMapas(h.merra2) : bars([{ k: "IMERG", v: [["IMERG", -5.1, C_IMERG]] }, { k: "CHIRPS", v: [["CHIRPS", 0.04, C_CHIRPS]] }, { k: "MERRA-2", v: [["MERRA-2", 8.6, C_OTRO]] }], -7, 10)}
      <p class="hz-n">${esc(LL("IMERG cae en las 15 celdas. MERRA-2 sube, pero tiene su propio salto en 2015-11: no sirve de testigo.", "IMERG drops in all 15 cells. MERRA-2 rises, but has its own jump in 2015-11: it cannot serve as a witness."))}</p>
    </div>

    <div class="hz-b">
      <h4>${esc(LL("Frente a ERA5, en 6 lugares", "Against ERA5, at 6 places"))}</h4>
      ${bars([{ k: "IMERG", v: [["IMERG", -6.1, C_IMERG]] }, { k: "ERA5", v: [["ERA5", -1.9, C_OTRO]] }, { k: "CHIRPS", v: [["CHIRPS", -0.2, C_CHIRPS]] }], -7, 1)}
      <p class="hz-n">${esc(LL("Y en 4 pluviómetros dominicanos IMERG cae más en los 4. Son pocos lugares, e IMERG usa ERA5 como dato auxiliar.", "And at 4 Dominican rain gauges IMERG drops more at all 4. Few places, and IMERG uses ERA5 as ancillary input."))}</p>
    </div>

    <div class="hz-b hz-pr">
      <h4>${esc(LL("¿Pasa fuera de la RD? Puerto Rico", "Does it happen outside the DR? Puerto Rico"))} <em class="${h ? "ok" : ""}">${esc(h ? LL("se cumple", "confirmed") : LL("en curso", "in progress"))}</em></h4>
      ${h ? `<p class="hz-big"><b>${h.pr.resumen.imerg_cae_mas} ${esc(LL("de", "of"))} ${h.pr.resumen.estaciones}</b> ${esc(LL("pluviómetros: IMERG pierde días de lluvia y el pluviómetro no.", "rain gauges: IMERG loses rain days and the gauge does not."))}</p>
      <p>${esc(LL("Bajo el mismo satélite GOES-East. Días con 1 mm o más, después menos antes de 2018-02, cada estación frente a la celda IMERG que la contiene:", "Under the same GOES-East satellite. Days with 1 mm or more, after minus before 2018-02, each station against the IMERG cell containing it:"))}</p>
      <p class="hz-key"><span style="--k:#8fd3ff">${esc(LL("pluviómetro", "rain gauge"))} ${fmt(h.pr.resumen.mediana_cambio_pp["cambio_pluvio_pp_1.0"])}</span><span style="--k:#ffffff">IMERG ${fmt(h.pr.resumen.mediana_cambio_pp["cambio_imerg_pp_1.0"])}</span><span>${esc(LL("medianas, pp", "medians, pp"))}</span></p>
      ${puertoRico(h.pr)}
      <p class="hz-n">${esc(LL(`Misma firma de llovizna que en la RD: con 0,1 mm, IMERG ${fmt(h.pr.resumen.mediana_cambio_pp["cambio_imerg_pp_0.1"])} y pluviómetros ${fmt(h.pr.resumen.mediana_cambio_pp["cambio_pluvio_pp_0.1"])}; con 5 mm, ${fmt(h.pr.resumen.mediana_cambio_pp["cambio_imerg_pp_5.0"])} y ${fmt(h.pr.resumen.mediana_cambio_pp["cambio_pluvio_pp_5.0"])}. Las tres predicciones registradas antes de descargar se cumplen. Es la prueba más fuerte que tenemos.`, `Same drizzle signature as in the DR: at 0.1 mm, IMERG ${fmt(h.pr.resumen.mediana_cambio_pp["cambio_imerg_pp_0.1"])} and gauges ${fmt(h.pr.resumen.mediana_cambio_pp["cambio_pluvio_pp_0.1"])}; at 5 mm, ${fmt(h.pr.resumen.mediana_cambio_pp["cambio_imerg_pp_5.0"])} and ${fmt(h.pr.resumen.mediana_cambio_pp["cambio_pluvio_pp_5.0"])}. All three predictions registered before downloading hold. Our strongest test.`))}</p>`
      : `<p>${esc(LL("La isla vecina, bajo el mismo satélite GOES-East y con muchos pluviómetros (GHCN-D).", "The neighbouring island, under the same GOES-East satellite and with many rain gauges (GHCN-D)."))}</p>`}
    </div>

    <p class="hz-open"><b>${esc(LL("Lo que no sabemos:", "What we do not know:"))}</b> ${esc(LL("la causa. GOES-16 y el sensor ATMS de NOAA-20 entraron con 19 días de diferencia; no podemos separar uno del otro. Tampoco afirmamos que la lluvia real de la RD haya cambiado: allí faltan pluviómetros densos.", "the cause. GOES-16 and NOAA-20's ATMS came in 19 days apart; we cannot separate them. Nor do we claim the DR's real rain changed: it lacks dense rain gauges there."))}</p>
  </section>`;
}
