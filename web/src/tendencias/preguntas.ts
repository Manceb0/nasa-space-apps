// Los objetivos del equipo, convertidos en las cuatro preguntas que guían la pantalla.
// Cada pregunta agrupa los índices que la responden (contrato 1.0) y abre con el más fácil de entender.
import { LL, sgn, type Sel, type TrendData } from "./datos";

export interface Question {
  id: string; es: string; en: string;
  /** Cómo se nombra el cambio en una frase: «más rachas secas largas», «menos lluvia fuerte». */
  noun: [string, string];
  vars: string[];
}

export const QUESTIONS: Question[] = [
  { id: "secos", es: "¿Hay más días secos seguidos?", en: "More dry days in a row?", noun: ["rachas secas largas", "long dry spells"], vars: ["RACHAS15", "RACHAS10", "CDD"] },
  { id: "sequia", es: "¿Hay más sequías?", en: "More droughts?", noun: ["sequía", "drought"], vars: ["SPI3_MESES", "SPI3_EVENTOS", "SPI3_SEVER", "SPI3_DURAC", "SPI12_MESES", "SPI12_EVENTOS", "SPI12_SEVER", "SPI12_DURAC"] },
  { id: "fuerte", es: "¿Llueve más fuerte?", en: "Heavier rain?", noun: ["lluvia fuerte", "heavy rain"], vars: ["Rx1day", "Rx5day", "SDII", "R20mm", "R50mm", "R95pTOT", "R99pTOT"] },
  { id: "total", es: "¿Llueve más o menos en el año?", en: "More or less rain in the year?", noun: ["lluvia en el año", "rain over the year"], vars: ["PRCPTOT", "R1mm", "CWD"] },
];

/** Nombres cortos y llanos para el selector «Medido como». */
export const SHORT: Record<string, [string, string]> = {
  RACHAS15: ["Rachas secas de 15 días o más", "Dry spells of 15+ days"],
  RACHAS10: ["Rachas secas de 10 días o más", "Dry spells of 10+ days"],
  CDD: ["La racha seca más larga del año", "Longest dry spell of the year"],
  SPI3_MESES: ["Meses en sequía (SPI-3)", "Months in drought (SPI-3)"],
  SPI3_EVENTOS: ["Sequías que empiezan (SPI-3)", "Droughts starting (SPI-3)"],
  SPI3_SEVER: ["Severidad de la sequía (SPI-3)", "Drought severity (SPI-3)"],
  SPI3_DURAC: ["Duración de la sequía (SPI-3)", "Drought duration (SPI-3)"],
  SPI12_MESES: ["Meses en sequía (SPI-12)", "Months in drought (SPI-12)"],
  SPI12_EVENTOS: ["Sequías que empiezan (SPI-12)", "Droughts starting (SPI-12)"],
  SPI12_SEVER: ["Severidad de la sequía (SPI-12)", "Drought severity (SPI-12)"],
  SPI12_DURAC: ["Duración de la sequía (SPI-12)", "Drought duration (SPI-12)"],
  Rx1day: ["Lo máximo que llovió en un día", "Most rain in one day"],
  Rx5day: ["Lo máximo que llovió en cinco días", "Most rain in five days"],
  SDII: ["Lluvia por día de lluvia", "Rain per wet day"],
  R20mm: ["Días con 20 mm o más", "Days with 20 mm or more"],
  R50mm: ["Días con 50 mm o más", "Days with 50 mm or more"],
  R95pTOT: ["Lluvia de los días muy lluviosos", "Rain on very wet days"],
  R99pTOT: ["Lluvia de los días extremos", "Rain on extreme days"],
  PRCPTOT: ["Lluvia total del año", "Total rain in the year"],
  R1mm: ["Días con lluvia", "Wet days"],
  CWD: ["La racha húmeda más larga", "Longest wet spell"],
};
export const shortName = (id: string) => LL(...(SHORT[id] ?? [id, id]));

export const questionOf = (ind: string) => QUESTIONS.find((q) => q.vars.includes(ind)) ?? QUESTIONS[0];

/** Respuesta corta de una pregunta en una región: dirección, cuánto por década y si es significativa. */
export function verdict(d: TrendData, s: Sel, ind: string) {
  const t = d.tr({ ...s, ind, per: d.perFor(ind, s.per) });
  if (!t) return { sig: false, text: "—", dry: false, up: false };
  const sig = d.isSig(t, s.reg), up = t.pendiente_decada > 0;
  const pct = Number.isFinite(t.pendiente_pct_decada) ? `${sgn(t.pendiente_pct_decada, 0)} %` : sgn(t.pendiente_decada);
  return {
    sig, up, dry: d.towardDry(ind, t.pendiente_decada),
    text: sig ? LL(`${up ? "Sube" : "Baja"} ${pct} por década`, `${up ? "Rising" : "Falling"} ${pct} per decade`) : LL("Sin señal detectable", "No detectable signal"),
  };
}

/** La frase que resume la región: qué cambia de verdad y qué no se distingue del azar. */
export function finding(d: TrendData, s: Sel, pick: Record<string, string>) {
  const sig = QUESTIONS.map((q) => ({ q, v: verdict(d, s, pick[q.id] ?? q.vars[0]) })).filter((x) => x.v.sig);
  if (!sig.length) return LL("Con 24 años de datos, ningún cambio se distingue del azar en esta región. Eso no quiere decir que no haya cambio.", "With 24 years of data, no change stands out from chance here. That does not mean there is no change.");
  const parts = sig.map(({ q, v }) => `${v.up ? LL("más", "more") : LL("menos", "less")} ${LL(...q.noun)}`);
  const s0 = parts.join(LL(" y ", " and "));
  return LL(`Cambio claro: ${s0}. Lo demás no se distingue del azar con 24 años.`, `Clear change: ${s0}. The rest is indistinguishable from chance over 24 years.`);
}
