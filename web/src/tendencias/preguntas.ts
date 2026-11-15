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

/** Respuesta corta de una pregunta en una región, desde la clase de confianza de las dos fuentes. */
export function verdict(d: TrendData, s: Sel, ind: string) {
  const s2 = { ...s, ind, per: d.perFor(ind, s.per) };
  const row = d.row(s2), cls = row?.clase ?? "";
  const ts = d.prods.map((p) => d.tr(s2, p)).filter((t): t is NonNullable<typeof t> => !!t);
  const sigT = ts.filter((t) => d.isSig(t, s.reg));
  const lead = sigT[0] ?? ts[0];
  const up = lead ? lead.pendiente_decada > 0 : false;
  const pct = lead && Number.isFinite(lead.pendiente_pct_decada) ? `${sgn(lead.pendiente_pct_decada, 0)} %` : "";
  const color = d.V.clases[cls]?.color ?? "#6b6f75";
  const dir = up ? LL("Sube", "Rising") : LL("Baja", "Falling");
  const text =
    cls === "robusta" ? LL(`${dir} ${pct} por década · las dos fuentes coinciden`, `${dir} ${pct} per decade · both sources agree`)
    : cls === "consistente" ? LL(`Probablemente ${up ? "sube" : "baja"} · una fuente lo confirma`, `Probably ${up ? "rising" : "falling"} · one source confirms`)
    : cls === "en disputa" ? LL("En disputa · las fuentes no coinciden", "Disputed · the sources disagree")
    : cls === "un solo producto" ? (sigT.length ? LL(`${dir} ${pct} por década · una sola fuente`, `${dir} ${pct} per decade · one source only`) : LL("Sin señal detectable", "No detectable signal"))
    : cls === "sin dato" ? LL("Sin dato", "No data")
    : LL("Sin señal detectable", "No detectable signal");
  const short =
    cls === "robusta" ? `${dir} ${pct}`.trim()
    : cls === "consistente" ? LL(`Probablemente ${up ? "sube" : "baja"}`, `Probably ${up ? "rising" : "falling"}`)
    : cls === "en disputa" ? LL("En disputa", "Disputed")
    : cls === "un solo producto" && sigT.length ? `${dir} ${pct}`.trim()
    : cls === "sin dato" ? LL("Sin dato", "No data")
    : LL("Sin señal", "No signal");
  return { cls, color, up, text, short, strong: cls === "robusta" || cls === "consistente" || cls === "en disputa" || (cls === "un solo producto" && sigT.length > 0) };
}

/** La frase que resume la región: qué se sabe, qué está en disputa y qué no se distingue del azar. */
export function finding(d: TrendData, s: Sel, pick: Record<string, string>) {
  const all = QUESTIONS.map((q) => ({ q, v: verdict(d, s, pick[q.id] ?? q.vars[0]) }));
  const name = (q: Question) => LL(...q.noun);
  const of = (c: string) => all.filter((x) => x.v.cls === c);
  const rob = of("robusta"), con = of("consistente"), dis = of("en disputa");
  const parts = [rob.length ? "" : LL("Nada robusto todavía.", "Nothing robust yet.")];
  if (rob.length) parts.push(LL(`Coinciden: ${rob.map((x) => `${x.v.up ? "más" : "menos"} ${name(x.q)}`).join(" y ")}.`, `Agreed: ${rob.map((x) => `${x.v.up ? "more" : "less"} ${name(x.q)}`).join(" and ")}.`));
  if (con.length) parts.push(LL(`Probable: ${con.map((x) => `${x.v.up ? "más" : "menos"} ${name(x.q)}`).join(" y ")}.`, `Likely: ${con.map((x) => `${x.v.up ? "more" : "less"} ${name(x.q)}`).join(" and ")}.`));
  if (dis.length) parts.push(LL(`En disputa: ${dis.map((x) => name(x.q)).join(" y ")}.`, `Disputed: ${dis.map((x) => name(x.q)).join(" and ")}.`));
  if (!rob.length && !con.length && !dis.length) parts.push(LL("Ningún cambio se distingue del azar con 24 años.", "No change stands out from chance in 24 years."));
  return parts.filter(Boolean).join(" ");
}
