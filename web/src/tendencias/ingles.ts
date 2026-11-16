// Inglés de los textos de variables.json que solo vienen en español (descripción, unidades, por qué importa, clases).
// Se aplica con getters (bilingue): los datos no cambian y el idioma se puede cambiar sin recargar.
import { LL } from "./datos";

const EN: Record<string, string> = {
  "Combina duración e intensidad del déficit.": "Combines how long and how deep the deficit is.",
  "Cuánta del agua llega en los días más extremos.": "How much of the water comes on the most extreme days.",
  "Cuántas veces se entra en sequía.": "How often drought begins.",
  "Dice si cuando llueve, llueve más fuerte.": "Tells whether, when it rains, it rains harder.",
  "Direcciones opuestas y al menos uno significativo: las fuentes no están de acuerdo.": "Opposite directions and at least one significant: the sources disagree.",
  "Duración media de los eventos SPI-12 que empiezan en el año (vacío si no hay).": "Mean length of SPI-12 events starting in the year (empty if none).",
  "Duración media de los eventos SPI-3 que empiezan en el año (vacío si no hay).": "Mean length of SPI-3 events starting in the year (empty if none).",
  "Déficit acumulado de largo plazo.": "Long-term accumulated deficit.",
  "Días asociados a inundaciones repentinas y deslizamientos.": "Days linked to flash floods and landslides.",
  "Días que pueden causar escorrentía y anegamiento local.": "Days that can cause runoff and local waterlogging.",
  "Entradas en sequía de largo plazo.": "Onsets of long-term drought.",
  "Episodios de varios días (ondas, tormentas) que llenan ríos y presas.": "Multi-day episodes (waves, storms) that fill rivers and reservoirs.",
  "Es el agua total que recibe la zona en el periodo.": "The total water the area receives in the period.",
  "Eventos SPI-12 ≤ −1 que empiezan en el año.": "SPI-12 ≤ −1 events starting in the year.",
  "Eventos de sequía (meses seguidos con SPI-3 ≤ −1) que empiezan en el año.": "Drought events (consecutive months with SPI-3 ≤ −1) starting in the year.",
  "Frecuencia de periodos secos que ya afectan la agricultura de secano.": "How often dry spells already hurt rain-fed farming.",
  "La cola más extrema; con 24 años es muy ruidosa.": "The most extreme tail; with 24 years it is very noisy.",
  "La mayor lluvia acumulada en 5 días seguidos.": "The largest rainfall over 5 consecutive days.",
  "La mayor lluvia de un solo día.": "The largest single-day rainfall.",
  "La racha más larga de días con al menos 1 mm.": "The longest run of days with at least 1 mm.",
  "La racha más larga de días con menos de 1 mm.": "The longest run of days with less than 1 mm.",
  "Las tendencias describen cambios observados 2001-2024; no atribuyen causas.": "Trends describe observed changes in 2001-2024; they do not attribute causes.",
  "Lluvia persistente satura el suelo y favorece crecidas.": "Persistent rain saturates the soil and favours floods.",
  "Lluvia total de los días por encima del percentil 95 de los días húmedos 2001-2024.": "Total rain on days above the 95th percentile of 2001-2024 wet days.",
  "Lluvia total de los días por encima del percentil 99 de los días húmedos 2001-2024.": "Total rain on days above the 99th percentile of 2001-2024 wet days.",
  "Lluvia total dividida por el número de días húmedos.": "Total rain divided by the number of wet days.",
  "Los dos productos muestran tendencia significativa (FDR q ≤ 0.10) en la misma dirección.": "Both products show a significant trend (FDR q ≤ 0.10) in the same direction.",
  "Meses del año con SPI-12 ≤ −1 (déficit de 12 meses).": "Months of the year with SPI-12 ≤ −1 (12-month deficit).",
  "Meses del año con SPI-3 ≤ −1 (déficit de 3 meses).": "Months of the year with SPI-3 ≤ −1 (3-month deficit).",
  "Mide el aguacero más intenso del periodo.": "Measures the heaviest downpour of the period.",
  "Misma dirección en los dos; solo uno es significativo.": "Same direction in both; only one is significant.",
  "Ninguno significativo. Con 24 años no se puede detectar; no quiere decir que no haya cambio.": "Neither significant. With 24 years it cannot be detected; that does not mean there is no change.",
  "Número de días con 20 mm o más.": "Number of days with 20 mm or more.",
  "Número de días con 50 mm o más.": "Number of days with 50 mm or more.",
  "Número de días con al menos 1 mm.": "Number of days with at least 1 mm.",
  "Número de rachas de 10 o más días seguidos con menos de 1 mm.": "Number of runs of 10 or more consecutive days with less than 1 mm.",
  "Número de rachas de 15 o más días seguidos con menos de 1 mm.": "Number of runs of 15 or more consecutive days with less than 1 mm.",
  "Periodos secos largos; relevantes para riego y embalses.": "Long dry periods; they matter for irrigation and reservoirs.",
  "Persistencia de la sequía larga.": "How long long-term drought persists.",
  "Rachas secas largas estresan cultivos, pastos y abasto de agua.": "Long dry spells stress crops, pasture and water supply.",
  "Separa \"llueve menos veces\" de \"llueve menos\"; sensible a cómo cada producto detecta llovizna.": "Separates \"it rains less often\" from \"it rains less\"; sensitive to how each product detects drizzle.",
  "Sequía agrícola / de corto plazo.": "Agricultural / short-term drought.",
  "Sequía hidrológica: embalses y acuíferos.": "Hydrological drought: reservoirs and aquifers.",
  "Si las sequías duran más.": "Whether droughts last longer.",
  "Suma de la lluvia de los días con al menos 1 mm.": "Sum of rain on days with at least 1 mm.",
  "Suma de −SPI-12 en los meses del año con SPI-12 ≤ −1.": "Sum of −SPI-12 over the months of the year with SPI-12 ≤ −1.",
  "Suma de −SPI-3 en los meses del año con SPI-3 ≤ −1.": "Sum of −SPI-3 over the months of the year with SPI-3 ≤ −1.",
  "adimensional": "dimensionless",
  "adimensional/década": "dimensionless/decade",
  "días": "days",
  "días/década": "days/decade",
  "eventos": "events",
  "eventos/década": "events/decade",
  "meses": "months",
  "meses/década": "months/decade",
  "mm": "mm",
  "mm/década": "mm/decade",
  "mm/día": "mm/day",
  "mm/día/década": "mm/day/decade",
  "más lluvia / más extremo": "more rain / more extreme",
  "más seco": "drier",
  "rachas": "spells",
  "rachas/década": "spells/decade",
};

/** Convierte los campos de texto de un objeto en getters bilingües (el valor original queda en español). */
export function bilingue<T extends object>(o: T, campos: string[]) {
  for (const k of campos) {
    const es = (o as Record<string, unknown>)[k];
    if (typeof es !== "string") continue;
    Object.defineProperty(o, k, { get: () => LL(es, EN[es] ?? es), enumerable: true, configurable: true });
  }
  return o;
}
