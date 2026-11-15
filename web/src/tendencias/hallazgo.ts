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

export function hallazgo() {
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
      <p>${esc(LL("Días con 1 mm o más, después menos antes de 2018-02, mediana de 15 celdas que cubren el país:", "Days with 1 mm or more, after minus before 2018-02, median of 15 cells covering the country:"))}</p>
      ${bars([{ k: "IMERG", v: [["IMERG", -5.1, C_IMERG]] }, { k: "CHIRPS", v: [["CHIRPS", 0.04, C_CHIRPS]] }, { k: "MERRA-2", v: [["MERRA-2", 8.6, C_OTRO]] }], -7, 10)}
      <p class="hz-n">${esc(LL("IMERG cae en las 15 celdas. MERRA-2 sube, pero tiene su propio salto en 2015-11: no sirve de testigo.", "IMERG drops in all 15 cells. MERRA-2 rises, but has its own jump in 2015-11: it cannot serve as a witness."))}</p>
    </div>

    <div class="hz-b">
      <h4>${esc(LL("Frente a ERA5, en 6 lugares", "Against ERA5, at 6 places"))}</h4>
      ${bars([{ k: "IMERG", v: [["IMERG", -6.1, C_IMERG]] }, { k: "ERA5", v: [["ERA5", -1.9, C_OTRO]] }, { k: "CHIRPS", v: [["CHIRPS", -0.2, C_CHIRPS]] }], -7, 1)}
      <p class="hz-n">${esc(LL("Y en 4 pluviómetros dominicanos IMERG cae más en los 4. Son pocos lugares, e IMERG usa ERA5 como dato auxiliar.", "And at 4 Dominican rain gauges IMERG drops more at all 4. Few places, and IMERG uses ERA5 as ancillary input."))}</p>
    </div>

    <div class="hz-b hz-pr">
      <h4>${esc(LL("La prueba de Puerto Rico", "The Puerto Rico test"))} <em>${esc(LL("en curso", "in progress"))}</em></h4>
      <p>${esc(LL("La isla vecina, bajo el mismo satélite GOES-East y con muchos pluviómetros (GHCN-D). Si IMERG también pierde días allí, el hallazgo deja de depender de 4 estaciones dominicanas. Predicciones registradas antes de descargar (15 nov, 19:13 UTC):", "The neighbouring island, under the same GOES-East satellite and with many rain gauges (GHCN-D). If IMERG also loses days there, the finding stops depending on 4 Dominican stations. Predictions registered before downloading (15 Nov, 19:13 UTC):"))}</p>
      <ol>
        <li>${esc(LL("En al menos 2 de cada 3 pluviómetros, IMERG pierde más días que el pluviómetro.", "At 2 of every 3 gauges or more, IMERG loses more days than the gauge."))}</li>
        <li>${esc(LL("La diferencia mediana es de −3 pp o más.", "The median difference is −3 pp or more."))}</li>
        <li>${esc(LL("Los pluviómetros apenas cambian (entre −2 y +2 pp).", "Gauges barely change (between −2 and +2 pp)."))}</li>
      </ol>
      <p class="hz-n">${esc(LL("Si los pluviómetros de Puerto Rico caen tanto como IMERG, la conclusión de la RD se debilita. Resultados pendientes.", "If Puerto Rico's gauges drop as much as IMERG, the DR conclusion weakens. Results pending."))}</p>
    </div>

    <p class="hz-open"><b>${esc(LL("Lo que no sabemos:", "What we do not know:"))}</b> ${esc(LL("la causa. GOES-16 y el sensor ATMS de NOAA-20 entraron con 19 días de diferencia; no podemos separar uno del otro. Tampoco afirmamos que la lluvia real haya cambiado: faltan pluviómetros densos en la RD.", "the cause. GOES-16 and NOAA-20's ATMS came in 19 days apart; we cannot separate them. Nor do we claim the real rain changed: the DR lacks dense rain gauges."))}</p>
  </section>`;
}
