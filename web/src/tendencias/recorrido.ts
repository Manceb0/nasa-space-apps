// Recorrido de cierre: resultados precalculados, sin interpolaciones ni alertas en vivo.
import { load } from "../data";
import { esc, LL, num, sgn, type TrendData } from "./datos";
import { seriesChart } from "./graficas";
import "./recorrido.css";

interface Threshold { umbral_mm: number; opuestas_al_menos_una_sig: number; opuestas_ambas_sig: number }
interface Summary { regla: string; h: number; m: number; fa: number; ep: number; eventos_senal_fecha_anterior: number }
interface Event { regla: string; evento: string; inicio_catalogo: string; primera_fecha_senal: string }
interface Evidence { umbrales: Threshold[]; yuna: { resumen: Summary[]; eventos: Event[] }; procedencia: { archivo: string; sha256: string }[] }

export function wireTour(button: HTMLButtonElement, d: TrendData) {
  let dialog: HTMLDialogElement | null = null;
  const open = async () => {
    button.disabled = true;
    try {
      const e = await load<Evidence>("recorrido.json");
      let step = 0, threshold = 1, confirmed = false;
      dialog = document.createElement("dialog");
      dialog.className = "tour";
      dialog.setAttribute("aria-labelledby", "tour-title");
      document.body.append(dialog);
      const close = () => { dialog?.close(); dialog?.remove(); dialog = null; button.focus(); };
      const render = () => {
        const titles = [LL("¿Está cambiando la lluvia?", "Is rainfall changing?"), LL("Mueve la definición", "Change the definition"), LL("¿Qué cambia al pedir confirmación?", "What changes when we ask for confirmation?")];
        const selected = { ind: "SDII", per: "anual", reg: "DO", src: "IMERG" };
        let content = "";
        if (step === 0) {
          const rows = d.prods.map(p => {
            const t = d.tr(selected, p);
            return t ? `<tr><th scope="row">${esc(p)}</th><td>${sgn(t.pendiente_decada)}<small>mm / ${esc(LL("día húmedo / década", "wet day / decade"))}</small></td><td>${num(t.p, 4)}</td></tr>` : "";
          }).join("");
          content = `<p>${esc(LL("República Dominicana · 2001–2024. Compara las dos estimaciones de lluvia por día húmedo (SDII, umbral 1 mm).", "Dominican Republic · 2001–2024. Compare two estimates of rain per wet day (SDII, 1 mm threshold)."))}</p>
            <div class="tour-series">${seriesChart(d, selected, Math.min(650, Math.max(270, innerWidth - 80)), null, 180)}</div>
            <table><thead><tr><th>${esc(LL("Producto", "Product"))}</th><th>${esc(LL("Cambio por década", "Change per decade"))}</th><th>p</th></tr></thead><tbody>${rows}</tbody></table>
            <p class="tour-take">${esc(LL("Una tendencia en un producto no basta para confirmar un cambio físico. El contraste ayuda a decidir qué evidencia revisar antes de planificar.", "A trend in one product is not enough to confirm physical change. Comparison helps identify what evidence to review before planning."))}</p>`;
        } else if (step === 1) {
          const row = e.umbrales.find(r => r.umbral_mm === threshold)!;
          content = `<p>${esc(LL("Mismo país, mismos años, 442 celdas. Cambia qué cuenta como día húmedo al calcular la intensidad.", "Same country, same years, 442 cells. Change what counts as a wet day when calculating intensity."))}</p>
            <div class="tour-options" role="group" aria-label="${esc(LL("Umbral de día húmedo", "Wet-day threshold"))}">${e.umbrales.map(r => `<button data-threshold="${r.umbral_mm}" aria-pressed="${r.umbral_mm === threshold}">${num(r.umbral_mm, r.umbral_mm < 1 ? 1 : 0)} mm</button>`).join("")}</div>
            <div class="tour-number" aria-live="polite"><strong>${row.opuestas_al_menos_una_sig}<span> / 442</span></strong><p>${esc(LL("celdas con pendientes de signo contrario y al menos una significativa", "cells with opposite slope signs and at least one significant"))}</p><small>${row.opuestas_ambas_sig} ${esc(LL("con ambas significativas y signos contrarios", "with both significant and opposite signs"))}</small></div>
            <p class="tour-take">${esc(LL("0 disputas no demuestra acuerdo: al subir el umbral disminuye la potencia para detectar tendencias. Este control compara resultados ya calculados; no modifica el mapa de fondo.", "0 disputed cells does not prove agreement: raising the threshold reduces power to detect trends. This control compares precomputed results; it does not change the background map."))}</p>`;
        } else {
          const rule = confirmed ? "acuerdo_misma_celda_hoy_o_ayer" : "IMERG";
          const r = e.yuna.resumen.find(x => x.regla === rule)!;
          const dates = e.yuna.eventos.filter(x => x.regla === rule);
          content = `<p>${esc(LL("Yuna · comparación histórica 2016–2024 · 8 inundaciones catalogadas. Umbral >100 mm/48 h; CHIRPS acumulado en la misma celda y confirmación del mismo día o anterior.", "Yuna · historical comparison, 2016–2024 · 8 catalogued floods. Threshold >100 mm/48 h; CHIRPS accumulated in the same cell, confirmation on the same or previous day."))}</p>
            <div class="tour-options"><button data-confirm="false" aria-pressed="${!confirmed}">${esc(LL("Solo IMERG", "IMERG only"))}</button><button data-confirm="true" aria-pressed="${confirmed}">${esc(LL("Pedir confirmación", "Ask for confirmation"))}</button></div>
            <div class="tour-stats" aria-live="polite"><div><strong>${r.h}/8</strong><span>${esc(LL("eventos detectados", "events detected"))}</span></div><div><strong>${r.fa}</strong><span>${esc(LL("episodios sin evento catalogado", "episodes without a catalogued event"))}</span></div><div><strong>${r.eventos_senal_fecha_anterior}/8</strong><span>${esc(LL("señales anteriores al inicio", "signals before the start"))}</span></div></div>
            <p class="tour-take">${esc(LL("Confirmar reduce episodios sin evento catalogado de 39 a 16, pero pierde una inundación: septiembre de 2022. Ninguna primera señal precede estrictamente al inicio catalogado. CHIRPS llega tarde: esto no es una alerta en vivo.", "Confirmation reduces episodes without a catalogued event from 39 to 16, but misses one flood: September 2022. No first signal strictly precedes the catalogued start. CHIRPS arrives late: this is not a live warning."))}</p>
            <details><summary>${esc(LL("Ver los 8 eventos y sus fechas", "See all 8 events and dates"))}</summary><table><thead><tr><th>${esc(LL("Evento", "Event"))}</th><th>${esc(LL("Inicio catalogado", "Catalogued start"))}</th><th>${esc(LL("Primera señal", "First signal"))}</th></tr></thead><tbody>${dates.map(x => `<tr><th scope="row">${esc(x.evento)}</th><td>${esc(x.inicio_catalogo)}</td><td>${esc(x.primera_fecha_senal || LL("Sin señal", "No signal"))}</td></tr>`).join("")}</tbody></table></details>
            <p>${esc(LL("Uso propuesto: evaluar qué señales merecen verificación y mejorar el monitoreo para la preparación. No se ha demostrado anticipación ni reducción de daños; el catálogo puede omitir inundaciones. Exigir confirmación también puede perder eventos.", "Proposed use: evaluate which signals warrant verification and improve monitoring for preparedness. Lead time and damage reduction have not been demonstrated; the catalogue may omit floods. Requiring confirmation can also miss events."))}</p>`;
        }
        dialog!.innerHTML = `<header><span>${esc(LL("Recorrido · 90 s", "90-second tour"))} · ${step + 1}/3</span><button data-close aria-label="${esc(LL("Cerrar recorrido", "Close tour"))}">×</button></header><h1 id="tour-title" tabindex="-1">${esc(titles[step])}</h1><div class="tour-content">${content}</div>
          <details class="tour-evidence"><summary>${esc(LL("Mostrar evidencia y límites", "Show evidence and limitations"))}</summary><p>${esc(LL("Lluvia: NASA GPM IMERG V07 Final y CHC CHIRPS v2.0. Tendencias: Theil–Sen y Mann–Kendall con corrección de autocorrelación; comparaciones por celda con FDR. Las fuentes tienen dependencias parciales. Causa del cambio de IMERG: sin resolver (no es solo el GOES-16).", "Rainfall: NASA GPM IMERG V07 Final and CHC CHIRPS v2.0. Trends: Theil–Sen and autocorrelation-corrected Mann–Kendall; cell comparisons with FDR. Sources are partially dependent. Cause of the IMERG change: unresolved (not only GOES-16)."))}</p><p>${esc(LL("Yuna: catálogo de prensa incompleto, fechas de inicio de precisión variable y productos retrospectivos. Antes del inicio y el mismo día son categorías diferentes. Comparación exploratoria reutilizando eventos, sin validación operacional.", "Yuna: incomplete press catalogue, variable precision of start dates and retrospective products. Before the start and on the same day are different categories. Exploratory comparison reusing events, without operational validation."))}</p><button data-download>${esc(LL("Descargar evidencia (JSON)", "Download evidence (JSON)"))}</button></details>
          <footer><button data-back ${step === 0 ? "disabled" : ""}>${esc(LL("Anterior", "Back"))}</button><button data-next>${esc(step === 2 ? LL("Volver al mapa", "Return to map") : LL("Siguiente", "Next"))}</button></footer>`;
        dialog!.querySelector("[data-close]")!.addEventListener("click", close);
        dialog!.querySelector("[data-back]")!.addEventListener("click", () => { step--; render(); });
        dialog!.querySelector("[data-next]")!.addEventListener("click", () => { if (step === 2) close(); else { step++; render(); } });
        dialog!.querySelectorAll<HTMLButtonElement>("[data-threshold]").forEach(b => b.addEventListener("click", () => { threshold = Number(b.dataset.threshold); render(); }));
        dialog!.querySelectorAll<HTMLButtonElement>("[data-confirm]").forEach(b => b.addEventListener("click", () => { confirmed = b.dataset.confirm === "true"; render(); }));
        dialog!.querySelector("[data-download]")!.addEventListener("click", () => {
          const national = { periodo: "2001-2024", region: "DO", indice: "SDII", umbral_mm: 1,
            tendencias: Object.fromEntries(d.prods.map(p => [p, d.tr(selected, p)])),
            fuente: "data/tendencias/provincias.json" };
          const blob = new Blob([JSON.stringify({ ...e, nacional: national }, null, 2)], { type: "application/json" });
          const url = URL.createObjectURL(blob), a = document.createElement("a");
          a.href = url; a.download = "stellar-horizons-evidencia.json"; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
        });
        dialog!.scrollTop = 0;
        dialog!.querySelector<HTMLElement>("#tour-title")!.focus();
      };
      dialog.addEventListener("cancel", ev => { ev.preventDefault(); close(); });
      render(); dialog.showModal();
    } catch {
      button.textContent = LL("No se pudo cargar. Reintentar", "Could not load. Retry");
    } finally { button.disabled = false; }
  };
  button.addEventListener("click", open);
  return () => { button.removeEventListener("click", open); dialog?.remove(); };
}
