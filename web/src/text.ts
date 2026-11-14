// Frases que se arman SOLO con números del JSON, en español o inglés. Ninguna afirma más de lo que el número dice.
import type { Trend, VariableMeta, Verdict, Window } from "./data";
import { getLang, locale } from "./i18n";

export type Prediction = "sube" | "baja" | "nada";

const es = () => getLang() === "es";

export function fmt(v: number, digits = 1): string {
  return new Intl.NumberFormat(locale(), { maximumFractionDigits: digits, minimumFractionDigits: digits })
    .format(v).replace("-", "−");
}

export function fmtSigned(v: number, digits = 1): string {
  return (v > 0 ? "+" : "") + fmt(v, digits);
}

export function fmtP(p: number): string {
  if (p < 0.001) return es() ? "menos de 0,001" : "less than 0.001";
  return fmt(p, p < 0.01 ? 3 : 2);
}

/** p como frecuencia que se entiende: "unas 3 de cada 100 veces" / "about 3 times in 100". */
export function chance(p: number): string {
  if (es()) {
    if (p < 0.001) return "menos de 1 de cada 1000 veces";
    if (p < 0.01) return `unas ${Math.max(1, Math.round(p * 1000))} de cada 1000 veces`;
    return `unas ${Math.round(p * 100)} de cada 100 veces`;
  }
  if (p < 0.001) return "less than once in 1000 times";
  if (p < 0.01) return `about ${Math.max(1, Math.round(p * 1000))} times in 1000`;
  return `about ${Math.round(p * 100)} times in 100`;
}

export function digitsFor(meta: VariableMeta): number {
  if (meta.unidad === "NDVI") return 3;
  if (meta.unidad === "°C" || meta.unidad.startsWith("gC")) return 2;
  return 1;
}

function rising(v: Verdict, t: Trend): boolean {
  if (v === "sube") return true;
  if (v === "baja") return false;
  return t.pendiente_decada >= 0;
}

const perDecade = () => (es() ? "por década" : "per decade");
const lower = (s: string) => s.charAt(0).toLowerCase() + s.slice(1);

/** Frase principal del veredicto. */
export function verdictSentence(meta: VariableMeta, region: string, t: Trend, a: number, b: number): string {
  const d = digitsFor(meta);
  const mag = `${fmt(Math.abs(t.pendiente_decada), d)} ${meta.unidad} ${perDecade()}`;
  const up = rising(t.veredicto, t);
  if (es()) {
    const dir = up ? "aumentó" : "disminuyó";
    switch (t.veredicto) {
      case "sube": case "baja": return `${meta.nombre} en ${region} ${dir} unos ${mag} entre ${a} y ${b}.`;
      case "indicio": return `Hay un indicio de que ${lower(meta.nombre)} ${dir} en ${region}, pero no alcanza para concluirlo.`;
      case "sin_evidencia": return `Entre ${a} y ${b}, los datos no muestran una tendencia clara en ${lower(meta.nombre)}.`;
      default: return "No hay datos suficientes para calcular una tendencia.";
    }
  }
  const dir = up ? "increased" : "decreased";
  switch (t.veredicto) {
    case "sube": case "baja": return `${meta.nombre} in ${region} ${dir} by about ${mag} between ${a} and ${b}.`;
    case "indicio": return `There is a hint that ${lower(meta.nombre)} ${dir} in ${region}, but it is not enough to conclude it.`;
    case "sin_evidencia": return `Between ${a} and ${b}, the data show no clear trend in ${lower(meta.nombre)}.`;
    default: return "There is not enough data to compute a trend.";
  }
}

/** Lo que el número significa, en una o dos frases. */
export function verdictExplain(meta: VariableMeta, t: Trend): string {
  const d = digitsFor(meta);
  const [lo, hi] = t.ic95_decada;
  const between = es() ? `entre ${fmtSigned(lo, d)} y ${fmtSigned(hi, d)}` : `between ${fmtSigned(lo, d)} and ${fmtSigned(hi, d)}`;
  const range = `${between} ${meta.unidad} ${perDecade()}`;
  const sig = t.veredicto === "sube" || t.veredicto === "baja";
  const ciExcludesZero = lo > 0 || hi < 0;
  if (es()) {
    if (sig) return `Si no hubiera ninguna tendencia real, un patrón así de ordenado aparecería por azar ${chance(t.p_mk)} (p = ${fmtP(t.p_mk)}). El cambio verdadero está probablemente ${range}.`;
    if (ciExcludesZero) return `El rango simple de pendientes (${range}) no incluye el cero, pero no tiene en cuenta que un año se parece al siguiente. Con esa corrección la prueba da p = ${fmtP(t.p_mk)}: hay una pista, pero no alcanza para afirmarlo. Con más años podría confirmarse o desaparecer.`;
    return `Que no sea significativo no prueba que no cambió: con estos años, cualquier cambio ${range} sigue siendo compatible con los datos.`;
  }
  if (sig) return `If there were no real trend, a pattern this orderly would appear by chance ${chance(t.p_mk)} (p = ${fmtP(t.p_mk)}). The true change is probably ${range}.`;
  if (ciExcludesZero) return `The simple range of slopes (${range}) does not include zero, but it ignores that one year resembles the next. With that correction the test gives p = ${fmtP(t.p_mk)}: there is a clue, but not enough to claim it. More years could confirm it or make it vanish.`;
  return `Not significant does not prove it did not change: with these years, any change ${range} is still compatible with the data.`;
}

export function multipleTestingNote(t: Trend, nSeries: number): string | null {
  if ((t.veredicto === "sube" || t.veredicto === "baja") && t.q_bh !== undefined && t.q_bh >= 0.05) {
    return es()
      ? `Cuidado: en esta herramienta revisamos ${nSeries} series. Con tantas pruebas, alguna saldría "significativa" por azar. Al corregir por eso (q = ${fmtP(t.q_bh)}), esta tendencia deja de ser concluyente por sí sola.`
      : `Careful: this tool checks ${nSeries} records. With that many tests, one could look "significant" by chance. After correcting for that (q = ${fmtP(t.q_bh)}), this trend is no longer conclusive on its own.`;
  }
  return null;
}

export function predictionFeedback(pred: Prediction, t: Trend): { ok: boolean | null; text: string } {
  const v = t.veredicto;
  const E = es();
  if (v === "sube" || v === "baja") {
    if (pred === v) return { ok: true, text: E ? "Tu predicción coincide con la evidencia." : "Your prediction matches the evidence." };
    if (pred === "nada") return { ok: false, text: E ? "Predijiste que no cambiaba, pero los datos muestran una tendencia." : "You predicted no change, but the data show a trend." };
    return { ok: false, text: E ? "Los datos van en la dirección contraria a tu predicción." : "The data go the opposite way to your prediction." };
  }
  if (pred === "nada") return { ok: null, text: E ? "Los datos no muestran una tendencia clara, como predijiste. Pero eso no demuestra que no haya cambio." : "The data show no clear trend, as you predicted. But that does not prove there was no change." };
  return { ok: null, text: E ? "Los datos no confirman tu predicción, y tampoco la descartan: falta evidencia en cualquier sentido." : "The data neither confirm nor rule out your prediction: there is not enough evidence either way." };
}

export function seasonLesson(meta: VariableMeta, amp: number, t: Trend, years: number): string {
  const d = digitsFor(meta);
  return es()
    ? `Entre el mes más seco o frío y el más lluvioso o caliente hay ${fmt(amp, d)} ${meta.unidad}. En cambio, la tendencia de ${years} años suma ${fmtSigned(t.cambio_total, d)} ${meta.unidad}. El ciclo de las estaciones es mucho más grande que la tendencia: por eso comparamos cada mes con su propio promedio antes de buscarla.`
    : `Between the driest or coolest month and the wettest or hottest there are ${fmt(amp, d)} ${meta.unidad}. The ${years}-year trend, by contrast, adds up to ${fmtSigned(t.cambio_total, d)} ${meta.unidad}. The seasonal cycle is much larger than the trend: that is why each month is compared with its own average before looking for it.`;
}

export function windowLabel(w: Window): string {
  return `${w.inicio}–${w.fin}`;
}

export function trapText(w: Window, full: Trend, meta: VariableMeta): string {
  const up = w.veredicto === "sube";
  const noClear = full.veredicto === "sin_evidencia" || full.veredicto === "indicio";
  return es()
    ? `Si solo miraras ${windowLabel(w)}, dirías que ${lower(meta.nombre)} ${up ? "aumentó" : "disminuyó"} de forma significativa. Con los 24 años, ${noClear ? "no hay una tendencia clara" : "la tendencia va en otra dirección"}.`
    : `If you only looked at ${windowLabel(w)}, you would say ${lower(meta.nombre)} ${up ? "increased" : "decreased"} significantly. With all 24 years, ${noClear ? "there is no clear trend" : "the trend goes another way"}.`;
}

export function verdictShort(v: Verdict): string {
  const m = es()
    ? { sube: "Aumenta", baja: "Disminuye", indicio: "Indicio", sin_evidencia: "Sin tendencia clara", insuficiente: "Sin datos" }
    : { sube: "Increasing", baja: "Decreasing", indicio: "Hint", sin_evidencia: "No clear trend", insuficiente: "No data" };
  return m[v];
}

export function stateLabel(s: string): string {
  if (es()) return s.replace(/_/g, " ");
  const m: Record<string, string> = {
    ambos_recuperados: "both recovered", verde_censurado: "greenness censored", funcion_censurada: "function censored",
    ambos_censurados: "both censored", sin_impacto: "no impact", sin_impacto_verde: "no greenness impact",
    sin_impacto_funcion: "no function impact",
  };
  return m[s] ?? s.replace(/_/g, " ");
}

export function robustLabel(s: string): string {
  if (es()) return s;
  return ({ "ROBUSTO": "ROBUST", "SENSIBLE A SUPUESTOS": "SENSITIVE TO ASSUMPTIONS", "SIN DATOS SUFICIENTES": "NOT ENOUGH DATA" } as Record<string, string>)[s] ?? s;
}
