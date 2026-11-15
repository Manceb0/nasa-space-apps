// La respuesta del reto en una vista, en el orden del relato: lo que parece (llueve más intenso), la prueba (el
// instrumento cuenta menos días) y la solución (dos lluvias, dos alertas). Después, cómo lo sabemos: las predicciones
// escritas antes de calcular, con las cumplidas y las fallidas, y el grado de certeza de cada conclusión.
// Todo sale de los archivos del proyecto (tendencias/*.json y hallazgos.json, que lee results/ y ESTADO_CONCLUSIONES.md).
import { load } from "../data";
import { esc, LL, loadTrends, num } from "../tendencias/datos";
import { hallazgo, type Hallazgos } from "../tendencias/hallazgo";
import "./respuesta.css";

interface Pred { id: string; texto: string; estudio: string; cumplida: boolean | null }
interface Conc { id: string; texto: string; grado: string; seccion: string }
type H = Hallazgos & { predicciones: Pred[]; conclusiones: Conc[] };

const GRADOS: [RegExp, string, string, string][] = [
  [/^confirmado/i, "conf", "Confirmado", "Confirmed"],
  [/^se sostiene/i, "lim", "Con límites", "With limits"],
  [/^indicio/i, "ind", "Indicio", "Indication"],
  [/^(hip|sin resolver|no detectado)/i, "abi", "Sin resolver", "Unresolved"],
  [/^(no respaldado|retirado)/i, "no", "No respaldado o retirado", "Not supported or retracted"],
];
const grado = (g: string) => GRADOS.find(([r]) => r.test(g)) ?? GRADOS[3];

export async function viewAnswer(view: HTMLElement) {
  document.body.classList.remove("wx-on");
  const [d, h] = await Promise.all([loadTrends(), load<H>("tendencias/hallazgos.json")]);
  const s = { ind: "SDII", per: "anual", reg: "DO", src: "IMERG" };
  const tI = d.tr(s, "IMERG")!, tC = d.tr(s, "CHIRPS")!;
  const pct = (v: number) => `${v > 0 ? "+" : ""}${num(v, 0)} %`;
  const pv = (p: number) => (p < 0.001 ? "p < 0,001" : `p = ${num(p, 3)}`);
  const ok = h.predicciones.filter((p) => p.cumplida === true).length, ko = h.predicciones.filter((p) => p.cumplida === false).length, na = h.predicciones.length - ok - ko;
  const byG = GRADOS.map((g) => ({ g, rows: h.conclusiones.filter((c) => grado(c.grado) === g) }));
  const retir = h.conclusiones.filter((c) => grado(c.grado)[1] === "no");

  view.innerHTML = `<div class="rs">
    <header class="rs-head">
      <h1>${esc(LL("¿Está cambiando la lluvia en la RD?", "Is rainfall changing in the DR?"))}</h1>
      <p>${esc(LL("Un satélite dice que la lluvia se intensifica; otro, que se debilita. Lo que de verdad cambia es cómo IMERG cuenta los días de lluvia, y eso cambia cómo avisar de una inundación.", "One satellite says rain is intensifying; another, that it is weakening. What really changes is how IMERG counts rain days, and that changes how to warn of a flood."))}</p>
    </header>

    <section class="rs-act" aria-labelledby="rs-a1">
      <h2 id="rs-a1"><span>${esc(LL("Lo que parece: ", "What it looks like: "))}</span>${esc(LL("Llueve más intenso", "Rain is getting heavier"))}</h2>
      <div class="rs-two">
        <p class="rs-num"><b>${pct(tI.pendiente_pct_decada)}</b><span>${esc(LL(`por década: así de más intensa es la lluvia de un día lluvioso según NASA IMERG, en todo el país (${pv(tI.p)}).`, `per decade: that is how much heavier a rainy day gets according to NASA IMERG, across the country (${pv(tI.p)}).`))}</span></p>
        <p class="rs-num dn"><b>${pct(tC.pendiente_pct_decada)}</b><span>${esc(LL(`dice CHIRPS, que usa pluviómetros (${pv(tC.p)}). Dos fuentes serias, direcciones opuestas.`, `says CHIRPS, which uses rain gauges (${pv(tC.p)}). Two serious sources, opposite directions.`))}</span></p>
      </div>
    </section>

    <section class="rs-act" aria-labelledby="rs-a2">
      <h2 id="rs-a2"><span>${esc(LL("Lo que encontramos: ", "What we found: "))}</span>${esc(LL("IMERG cuenta menos días de lluvia", "IMERG counts fewer rain days"))}</h2>
      <div class="rs-four">
        <p><span>${esc(LL("Qué cambia", "What changes"))}</span><b>${esc(LL("Los días de lluvia que cuenta IMERG, sobre todo la llovizna", "The rain days IMERG counts, above all drizzle"))}</b></p>
        <p><span>${esc(LL("Dónde", "Where"))}</span><b>${esc(LL("En todo el país: IMERG cae más que CHIRPS en el 99 % de las celdas", "Across the country: IMERG drops more than CHIRPS in 99 % of cells"))}</b></p>
        <p><span>${esc(LL("Cuánto", "How much"))}</span><b>${esc(LL("Unos 5 puntos: de cada 100 días del calendario, 5 menos contados como lluviosos", "About 5 points: out of every 100 calendar days, 5 fewer counted as rainy"))}</b></p>
        <p><span>${esc(LL("¿Es significativo?", "Is it significant?"))}</span><b>${esc(LL("Sí para el instrumento (p < 0,001 frente a cada testigo). No para el clima: 0 tendencias robustas en 21 índices", "Yes for the instrument (p < 0.001 against each witness). Not for the climate: 0 robust trends in 21 indices"))}</b></p>
      </div>
      ${hallazgo(h)}
    </section>

    <section class="rs-act" aria-labelledby="rs-a3">
      <h2 id="rs-a3"><span>${esc(LL("Lo que proponemos: ", "What we propose: "))}</span>${esc(LL("Dos lluvias, dos alertas", "Two kinds of rain, two alerts"))}</h2>
      <div class="rs-two">
        <div class="rs-card">
          <p class="rs-big"><b>${esc(LL("6 de 14", "6 of 14"))}</b> ${esc(LL("inundaciones del Yuna llegaron con un ciclón", "Yuna floods came with a cyclone"))}</p>
          <p>${esc(LL("El pronóstico oficial del NHC ya ponía la tormenta a menos de 200 km, contado desde que se publicó el boletín:", "The official NHC forecast already put the storm within 200 km, counted from the advisory's publication:"))}</p>
          <ul class="rs-leads"><li><b>103 h</b> María 2017</li><li><b>85 h</b> Fiona 2022</li><li><b>37 h</b> Isaac 2012</li><li><b>37 h</b> Isaías 2020</li></ul>
          <p class="rs-n">${esc(LL("Es una revisión histórica, no una capacidad operativa demostrada.", "This is a historical review, not a demonstrated operational capability."))}</p>
        </div>
        <div class="rs-card">
          <p class="rs-big"><b class="w">${esc(LL("8 de 14", "8 of 14"))}</b> ${esc(LL("llegaron sin ciclón: vaguadas y frentes", "came without a cyclone: troughs and fronts"))}</p>
          <p>${esc(LL("Ninguna señal llegó antes del inicio. Ahí la respuesta es medir: el mapa de dónde falta un pluviómetro, en Tendencias.", "No signal arrived before onset. There the answer is to measure: the map of where a rain gauge is missing, in Trends."))}</p>
        </div>
      </div>
      <div class="rs-levels">
        <p><span>${esc(LL("Pre-alerta", "Pre-alert"))}</span><b>${esc(LL("con el boletín del NHC", "on the NHC advisory"))}</b>${esc(LL("Para lo barato: albergues, nivel de Hatillo, avisar a Villa Riva.", "For cheap actions: shelters, Hatillo level, notify Villa Riva."))}</p>
        <svg viewBox="0 0 40 16" aria-hidden="true"><path d="M2 8h32m-6-5 6 5-6 5" fill="none" stroke="#949494" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
        <p><span>${esc(LL("Alerta confirmada", "Confirmed alert"))}</span><b>${esc(LL("cuando dos satélites coinciden", "when two satellites agree"))}</b>${esc(LL("Para lo caro: movilizar. Falsas alarmas de 39 a 16; detecta 6 de 8 inundaciones en vez de 7.", "For costly actions: mobilise. False alarms from 39 to 16; detects 6 of 8 floods instead of 7."))}</p>
      </div>
      <p class="rs-reach"><b>${esc(LL("Sirve en cualquier país que use IMERG.", "It works in any country that uses IMERG."))}</b> ${esc(LL(`Puerto Rico ya lo demuestra: IMERG pierde días frente a ${h.pr.resumen.imerg_cae_mas} de ${h.pr.resumen.estaciones} pluviómetros que no cambian.`, `Puerto Rico already shows it: IMERG loses days against ${h.pr.resumen.imerg_cae_mas} of ${h.pr.resumen.estaciones} rain gauges that do not change.`))}</p>
      <a class="rs-go" href="#tendencias">${esc(LL("Verlo en el mapa", "See it on the map"))}<svg viewBox="0 0 12 12" aria-hidden="true"><path d="M4.5 3l3 3-3 3" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg></a>
    </section>

    <section class="rs-act" aria-labelledby="rs-a4">
      <h2 id="rs-a4"><span>${esc(LL("Cómo lo sabemos: ", "How we know: "))}</span>${esc(LL(`${h.predicciones.length} predicciones escritas antes de calcular`, `${h.predicciones.length} predictions written before computing`))}</h2>
      <p class="rs-sub"><b class="ok">${ok} ${esc(LL("se cumplieron", "held"))}</b> · <b class="ko">${ko} ${esc(LL("fallaron", "failed"))}</b> · ${na} ${esc(LL("con el veredicto en el informe", "with the verdict in the report"))}. ${esc(LL("Las fallidas se publican igual. Pasa el cursor o toca cada cuadro para leerla.", "Failed ones are published too. Hover or tap each square to read it."))}</p>
      <div class="rs-preds">${h.predicciones.map((p) => `<button class="rs-p ${p.cumplida === true ? "ok" : p.cumplida === false ? "ko" : "na"}" title="${esc(`${p.id} · ${p.cumplida === true ? LL("se cumplió", "held") : p.cumplida === false ? LL("falló", "failed") : LL("ver informe", "see report")} · ${p.texto}`)}" data-pred="${esc(p.id)}"><b>${esc(p.id.split("_")[0])}</b></button>`).join("")}</div>
      <p class="rs-pred-t" id="rs-pred-t" aria-live="polite"></p>

      <h3 class="rs-h3">${esc(LL("Con qué certeza afirmamos cada cosa", "How certain each claim is"))}</h3>
      <div class="rs-bar" aria-hidden="true">${byG.filter((x) => x.rows.length).map((x) => `<i class="g-${x.g[1]}" style="flex:${x.rows.length}"></i>`).join("")}</div>
      <div class="rs-grades">${byG.filter((x) => x.rows.length).map((x) => `
        <div class="rs-g"><h4><i class="g-${x.g[1]}"></i>${esc(LL(x.g[2], x.g[3]))} <span>${x.rows.length}</span></h4>
          <ul>${x.rows.map((c) => `<li>${esc(c.texto.replace(/[«»]/g, ""))}</li>`).join("")}</ul></div>`).join("")}</div>
      ${retir.length ? `<p class="rs-n">${esc(LL(`${retir.length} conclusiones nuestras no se sostuvieron o se retiraron tras revisarlas; siguen a la vista.`, `${retir.length} of our own conclusions did not hold or were retracted after review; they stay visible.`))}</p>` : ""}
    </section>
  </div>`;
  view.querySelectorAll<HTMLButtonElement>("[data-pred]").forEach((b) => b.addEventListener("click", () => {
    const p = h.predicciones.find((x) => x.id === b.dataset.pred)!;
    view.querySelector("#rs-pred-t")!.textContent = `${p.id}: ${p.texto} (${p.cumplida === true ? LL("se cumplió", "held") : p.cumplida === false ? LL("falló", "failed") : LL("veredicto en el informe", "verdict in the report")})`;
    view.querySelectorAll(".rs-p.on").forEach((x) => x.classList.remove("on")); b.classList.add("on");
  }));
}
