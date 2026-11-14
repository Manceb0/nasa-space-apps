// Frases que se arman SOLO con números del JSON. Ninguna afirma más de lo que el número dice.
import type { Trend, VariableMeta, Verdict, Window } from "./data";

export type Prediction = "sube" | "baja" | "nada";

const nf = (d: number) => new Intl.NumberFormat("es-DO", { maximumFractionDigits: d, minimumFractionDigits: d });

export function fmt(v: number, digits = 1): string {
  return nf(digits).format(v).replace("-", "−");
}

export function fmtSigned(v: number, digits = 1): string {
  return (v > 0 ? "+" : "") + fmt(v, digits);
}

export function fmtP(p: number): string {
  if (p < 0.001) return "menos de 0,001";
  return fmt(p, p < 0.01 ? 3 : 2);
}

/** p como frecuencia que se entiende: "unas 3 de cada 100 veces". */
export function chance(p: number): string {
  if (p < 0.001) return "menos de 1 de cada 1000 veces";
  if (p < 0.01) return `unas ${Math.max(1, Math.round(p * 1000))} de cada 1000 veces`;
  return `unas ${Math.round(p * 100)} de cada 100 veces`;
}

export function digitsFor(meta: VariableMeta): number {
  return meta.unidad === "°C" ? 2 : 1;
}

export function directionWord(v: Verdict, t: Trend): "aumentó" | "disminuyó" {
  if (v === "sube") return "aumentó";
  if (v === "baja") return "disminuyó";
  return t.pendiente_decada >= 0 ? "aumentó" : "disminuyó";
}

/** Frase principal del veredicto. */
export function verdictSentence(meta: VariableMeta, region: string, t: Trend, span: string): string {
  const d = digitsFor(meta);
  const mag = `${fmt(Math.abs(t.pendiente_decada), d)} ${meta.unidad} por década`;
  switch (t.veredicto) {
    case "sube":
    case "baja":
      return `${meta.nombre} en ${region} ${directionWord(t.veredicto, t)} unos ${mag} entre ${span}.`;
    case "indicio":
      return `Hay un indicio de que ${meta.nombre.toLowerCase()} ${directionWord(t.veredicto, t)} en ${region}, pero no alcanza para concluirlo.`;
    case "sin_evidencia":
      return `Entre ${span}, los datos no muestran una tendencia clara en ${meta.nombre.toLowerCase()}.`;
    default:
      return "No hay datos suficientes para calcular una tendencia.";
  }
}

/** Lo que el número significa, en una o dos frases. */
export function verdictExplain(meta: VariableMeta, t: Trend): string {
  const d = digitsFor(meta);
  const [lo, hi] = t.ic95_decada;
  const range = `entre ${fmtSigned(lo, d)} y ${fmtSigned(hi, d)} ${meta.unidad} por década`;
  if (t.veredicto === "sube" || t.veredicto === "baja") {
    return `Si no hubiera ninguna tendencia real, un patrón así de ordenado aparecería por azar ${chance(t.p_mk)} (p = ${fmtP(t.p_mk)}). El cambio verdadero está probablemente ${range}.`;
  }
  if (lo > 0 || hi < 0) {
    return `El rango simple de pendientes (${range}) no incluye el cero, pero no tiene en cuenta que un año se parece al siguiente. Con esa corrección la prueba da p = ${fmtP(t.p_mk)}: hay una pista, pero no alcanza para afirmarlo. Con más años podría confirmarse o desaparecer.`;
  }
  return `Que no sea significativo no prueba que no cambió: con estos años, cualquier cambio ${range} sigue siendo compatible con los datos.`;
}

export function multipleTestingNote(t: Trend, nSeries: number): string | null {
  if ((t.veredicto === "sube" || t.veredicto === "baja") && t.q_bh !== undefined && t.q_bh >= 0.05) {
    return `Cuidado: en esta herramienta revisamos ${nSeries} series. Con tantas pruebas, alguna saldría "significativa" por azar. Al corregir por eso (q = ${fmtP(t.q_bh)}), esta tendencia deja de ser concluyente por sí sola.`;
  }
  return null;
}

export function predictionFeedback(pred: Prediction, t: Trend): { ok: boolean | null; text: string } {
  const v = t.veredicto;
  if (v === "sube" || v === "baja") {
    if (pred === v) return { ok: true, text: "Tu predicción coincide con la evidencia." };
    if (pred === "nada") return { ok: false, text: "Predijiste que no cambiaba, pero los datos muestran una tendencia." };
    return { ok: false, text: "Los datos van en la dirección contraria a tu predicción." };
  }
  if (pred === "nada") return { ok: null, text: "Los datos no muestran una tendencia clara, como predijiste. Pero eso no demuestra que no haya cambio." };
  return { ok: null, text: "Los datos no confirman tu predicción, y tampoco la descartan: falta evidencia en cualquier sentido." };
}

export function seasonLesson(meta: VariableMeta, amp: number, t: Trend, years: number): string {
  const d = digitsFor(meta);
  return `Entre el mes más seco o frío y el más lluvioso o caliente hay ${fmt(amp, d)} ${meta.unidad}. En cambio, la tendencia de ${years} años suma ${fmtSigned(t.cambio_total, d)} ${meta.unidad}. El ciclo de las estaciones es mucho más grande que la tendencia: por eso comparamos cada mes con su propio promedio antes de buscarla.`;
}

export function windowLabel(w: Window): string {
  return `${w.inicio}–${w.fin}`;
}

export function trapText(w: Window, full: Trend, meta: VariableMeta): string {
  const dir = w.veredicto === "sube" ? "aumentó" : "disminuyó";
  const fullTxt = full.veredicto === "sin_evidencia" || full.veredicto === "indicio"
    ? "no hay una tendencia clara"
    : `la tendencia va en otra dirección`;
  return `Si solo miraras ${windowLabel(w)}, dirías que ${meta.nombre.toLowerCase()} ${dir} de forma significativa. Con los 24 años, ${fullTxt}.`;
}

export const VERDICT_SHORT: Record<Verdict, string> = {
  sube: "Aumenta",
  baja: "Disminuye",
  indicio: "Indicio",
  sin_evidencia: "Sin tendencia clara",
  insuficiente: "Sin datos",
};
