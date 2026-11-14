// Módulo de idiomas: español e inglés. Todos los textos visibles salen de aquí.
import type { Index, RegionMeta, VariableMeta } from "./data";

export type Lang = "es" | "en";
const KEY = "esd-lang";

function initial(): Lang {
  const q = new URLSearchParams(location.search).get("lang");
  if (q === "es" || q === "en") return q;
  try {
    const s = localStorage.getItem(KEY);
    if (s === "es" || s === "en") return s;
  } catch { /* almacenamiento bloqueado: se usa el idioma del navegador */ }
  return navigator.language?.toLowerCase().startsWith("es") ? "es" : "en";
}

let current: Lang = initial();

export const getLang = (): Lang => current;
export function setLang(l: Lang): void {
  current = l;
  document.documentElement.lang = l;
  try { localStorage.setItem(KEY, l); } catch { /* sin almacenamiento, solo esta sesión */ }
}
document.documentElement.lang = current;

export const locale = (): string => (current === "es" ? "es-DO" : "en-US");

const UI = {
  es: {
    title: "Detective del Sistema Tierra · Stellar Horizons",
    brand: "Detective del Sistema Tierra",
    navInvestigate: "Investigar",
    navCases: "Expedientes",
    navMethod: "Cómo funciona",
    team: "Stellar Horizons · NASA Space Apps 2026",
    langSwitch: "English",
    langSwitchLabel: "Switch to English",
    footer: "Datos: NASA GPM IMERG, MERRA-2 y GLDAS vía Giovanni; MODIS vía AppEEARS; mapa base NASA GIBS Blue Marble. Hecho en República Dominicana por Stellar Horizons. Código y método abiertos.",
    h1: "Elige qué investigar. Predice. Comprueba.",
    lede: "Datos reales de la NASA sobre dos zonas de bosque seco de República Dominicana, de 2001 a 2024. Antes de ver la respuesta, di qué crees que pasó.",
    whatQ: "¿Qué quieres investigar?",
    groupClimate: "Clima y agua",
    groupVeg: "Vegetación vista desde el espacio",
    mapPoints: "Puntos ámbar: lugares de monte seco revisados en imagen satelital; la serie es su promedio.",
    whereQ: "¿Dónde?",
    measuredIn: "Se mide en",
    dataType: "Tipo de dato",
    mapLabel: "Mapa de la zona elegida",
    mapDashed: "Línea discontinua: zona pedida.",
    mapPoint: " Punto ámbar: centro de la única celda del modelo que usa Giovanni (queda fuera de la zona).",
    mapBox: " Recuadro ámbar: celdas de datos que promedia Giovanni.",
    hypothesis: "Tu hipótesis",
    since2001: (v: string, r: string) => `Desde 2001, ${v} en ${r}…`,
    predUp: "ha aumentado",
    predDown: "ha disminuido",
    predNone: "no cambió de forma clara",
    reveal: "Revelar la evidencia",
    factSlope: "pendiente Theil-Sen",
    factPerDecade: "por década",
    factRange: "rango probable (IC 95 %)",
    factP: "p de Mann-Kendall, corregido porque los años se parecen entre sí",
    factYears: "años completos",
    chartAnom: "Cada año comparado con lo normal",
    chartRaw: "Los datos tal como llegan",
    btnRaw: "Ver los datos crudos",
    btnAnom: "Ver sin la estación",
    captionAnom: "Cada punto es un año: cuánto se separó, en promedio, de lo normal para cada mes. La recta ámbar es la tendencia (Theil-Sen); la franja, las pendientes compatibles con los datos.",
    axisAnom: (u: string) => `Diferencia con lo normal (${u})`,
    axisRaw: (u: string) => `Valor mensual (${u})`,
    tipYear: (y: number, v: string, u: string) => `${y}: ${v} ${u} respecto a lo normal`,
    otherWindow: "¿Y si miras otro intervalo?",
    windowLede: "Cada cuadro es un intervalo de 10 años o más: la fila dice el año en que empieza y la columna, el año en que termina. Ámbar intenso: mirando solo esos años concluirías una tendencia significativa (▲ sube, ▼ baja). Ámbar tenue: un indicio. Gris: nada claro. Toca cualquiera y compara.",
    trapsTitle: "Intervalos que engañan",
    trapsNote: "Escoger el intervalo que confirma lo que uno quiere ver es uno de los errores más comunes en ciencia. Por eso aquí se ven todos.",
    noTraps: "Ningún intervalo de 10 años o más muestra una tendencia significativa en la dirección contraria. Pero fíjate en los cuadros grises: con pocos años, muchas veces no se detecta nada. Por eso importa tener series largas.",
    fullSeries: (a: number, b: number) => `Serie completa ${a}–${b}`,
    tapCell: "Toca un cuadro para ver otro intervalo.",
    years: "años",
    range: "rango",
    backFull: "Volver a la serie completa",
    matrixAria: "Mapa de ventanas: filas = año de inicio, columnas = año de fin",
    matrixAxis: "año en que termina el intervalo →",
    passport: "Pasaporte de la evidencia",
    pSource: "Fuente", pVariable: "Variable", pTool: "Herramienta", pBox: "Zona pedida", pBoxNote: "(oeste, sur, este, norte)",
    pData: "Datos usados", pFile: "Archivo", pMethod: "Método", pAutocorr: "Autocorrelación", pMulti: "Comparaciones múltiples",
    pCode: "Código", pRepro: "Reproducir", pOpenGiovanni: "Abrir la misma consulta en Giovanni",
    pAutocorrText: (r: string, f: string, p: string) => `lag 1 anual = ${r}; la varianza de Mann-Kendall se multiplicó por ${f} (p sin corregir: ${p})`,
    pMultiText: (n: number, q: string) => `q de Benjamini-Hochberg sobre ${n} series = ${q}`,
    pVerifyRecon: "Reconstruido del CSV de Giovanni; verificado valor por valor contra el original regenerado (idéntico redondeado a 4 decimales)",
    pVerifyOrig: "CSV descargado de Giovanni sin cambios",
    pVerifyModis: "CSV de NASA AppEEARS sin cambios; solo observaciones que pasan el filtro de calidad",
    pMethodModis: "Media mensual de observaciones válidas en cada punto; la zona es la media de las anomalías de sus puntos. Anomalía anual con al menos 9 meses con dato. Theil-Sen con IC 95 %; Mann-Kendall corregido por empates y autocorrelación AR(1); q de Benjamini-Hochberg sobre todas las series.",
    pMethodText: "Anomalía = valor − media del mismo mes (2001–2024). Media anual de anomalías (solo años con 12 meses). Pendiente Theil-Sen con IC 95 %; prueba de Mann-Kendall con corrección por empates y por autocorrelación AR(1); q de Benjamini-Hochberg sobre todas las series.",
    loadError: "No se pudieron cargar los datos",
    testBanner: "DATOS SINTÉTICOS DE PRUEBA. Nada de esta página es un resultado real.",
    caseH1: "Expediente PHANTOM: ¿verde es recuperado?",
    caseLede: "Después de una sequía, el bosque puede volver a verse verde antes de volver a funcionar como antes. Este expediente compara cuándo se recupera el verdor (NDVI) y cuándo se recuperan dos señales de funcionamiento: la productividad estimada (GPP, un modelo) y la temperatura de las hojas frente a la del aire.",
    caseResultsReal: "Resultados con datos MODIS reales",
    caseResultsTest: "Resultados de prueba (sintéticos)",
    caseWaiting: "Estado: esperando los datos MODIS",
    caseWaitingText: "Los datos de vegetación se pidieron a NASA AppEEARS el 14 de noviembre: un pedido por puntos (5 lugares revisados en imagen satelital, 2001–2024) y uno por área (2 zonas, 2012–2021). Mientras no lleguen, este expediente <strong>no muestra ningún resultado</strong> sobre la brecha. Lo que sí es real desde ya: las sequías que vamos a estudiar.",
    droughtsH: "Las sequías del expediente",
    droughtsNote: "SPI-3: lluvia de 3 meses comparada con lo normal para esa época (IMERG V07). Las franjas son las sequías que usamos: SPI-3 por debajo de −1 durante 2 meses o más.",
    howH: "Cómo se decide \"recuperado\"",
    howP1: "Cada señal se compara con lo normal para esa época del año (mediana de los años disponibles). Una señal está <strong>impactada</strong> si pasa 3 observaciones seguidas muy por debajo de lo normal (z &lt; −1,5). Se <strong>recupera</strong> cuando vuelve a menos de una desviación de lo normal (z ≥ −1) y se queda ahí 3 observaciones seguidas. Si la siguiente sequía llega antes, el evento queda <strong>censurado</strong>: no inventamos cuánto habría tardado.",
    howP2: "Δt = día en que se recupera la función − día en que se recupera el verdor. Con compuestos de 8 y 16 días, una diferencia menor de 32 días no se distingue de cero.",
    notClaimH: "Lo que este expediente no afirma",
    notClaim: "No mide la salud completa del ecosistema. GPP sale de un modelo que usa en parte el mismo verdor, así que no es independiente; por eso añadimos la señal térmica. Cinco puntos son una exploración, no la superficie afectada de una región.",
    case2H: "Expediente 2: ¿llega la siguiente sequía antes de recuperarse?",
    case2Lede: "Una colisión ocurre cuando empieza una nueva sequía mientras el verdor todavía está por debajo de lo normal tras la anterior.",
    case2Count: (c: number, n: number) => `${c} colisiones en ${n} sequías evaluadas (punto × evento).`,
    case2Pending: "Pendiente de los mismos datos MODIS. La regla ya está programada y probada.",
    gapTableH: "Brecha por sequía y punto",
    caseRealNote: "Datos MODIS por puntos (AppEEARS, 5 lugares, 2001–2024). El pedido por área para el mapa sigue en proceso. Los puntos son una exploración, no la región completa.",
    phantomNoH: "Lo que encontramos: la hipótesis no se sostiene en estos puntos",
    phantomYesH: "Lo que encontramos: hay señales a favor de la hipótesis",
    phantomSummary: (n: number, w: number, b: number, a: number) => `De ${n} comparaciones en que ambas señales se recuperaron, ${w} quedan dentro de la precisión del método (±32 días), en ${b} la función volvió antes que el verdor y en ${a} después.`,
    phantomRobust: (after: string[], nBefore: number) => after.length
      ? `Robusto en la dirección de PHANTOM (función después del verdor): ${after.join("; ")}. Robusto en la dirección contraria: ${nBefore}.`
      : `Ningún caso robusto en la dirección de PHANTOM. Casos robustos en la dirección contraria: ${nBefore}.`,
    phantomLateDip: (cases: string[]) => `Ojo: en ${cases.join("; ")} la señal de función empezó a caer cuando el verdor ya se había recuperado. Es otra caída, no una recuperación tardía de la misma, así que no cuenta a favor de la hipótesis. En GPP puede venir del clima que usa el modelo, no de la planta.`,
    phantomCaveat: "Que la función vuelva antes que el verdor es coherente con hojas que retoman la transpiración (y se enfrían) antes de que el follaje se recupere del todo. Es una lectura posible, no una prueba: cinco puntos y pocas sequías por punto.",
    hiddenRows: (n: number) => `Se ocultan ${n} filas en las que ninguna de las dos señales tuvo una caída sostenida (sin impacto).`,
    thPoint: "Punto", thDrought: "Sequía", thSignal: "Señal de función", thState: "Estado", thDt: "Δt (días)", thRobust: "Robustez",
    sigGpp: "GPP (modelo)", sigLst: "Hojas vs. aire",
    challengeH: "Cuestiona el hallazgo",
    challengeLede: "Cambia los supuestos. Las 18 combinaciones están <strong>precalculadas por el mismo código</strong> del análisis (phantom/recovery.py); aquí eliges cuál ver y compruebas si la conclusión se mantiene.",
    cPoint: "Punto", cDrought: "Sequía", cSignal: "Señal", cGreen: "Verdor", cThreshold: "Umbral", cPersist: "Persistencia",
    cWith: "Con estos supuestos:",
    cNA: "Combinación no disponible.",
    cSummary: (n: number, v: number, pos: number, neg: number, mid: number) => `De ${n} combinaciones, ${v} tienen ambas recuperaciones: ${pos} dan la función más de 32 días después del verdor, ${neg} más de 32 días antes, y ${mid} quedan dentro de la precisión del método.`,
    days: "días",
    axisDt: "Δt = función − verdor (días)",
    methodH1: "Cómo piensa un detective de datos",
    methodLede: "Ningún número de esta herramienta está escrito a mano: todos salen del mismo código abierto que corre sobre los datos de la NASA. Estas son las ideas que usa.",
    limitsH: "Límites que hay que conocer",
    limits: "MERRA-2 y GLDAS son modelos, no mediciones directas, y sus celdas son más grandes que las zonas. GLDAS usa la lluvia como dato de entrada: si coincide con IMERG, no es una confirmación independiente. Con 24 años, una tendencia pequeña puede existir sin ser detectable.",
    updated: (d: string) => `Datos actualizados: ${d}. Método completo: METHODOLOGY.md en el repositorio.`,
    glossary: [
      ["Variable", "Lo que se mide: lluvia, temperatura, humedad. Cada una tiene una unidad y una fuente."],
      ["Estacionalidad", "El ciclo que se repite cada año: la temporada de lluvias, el verano. Es mucho más grande que una tendencia de décadas, así que hay que quitarla primero."],
      ["Anomalía", "Cuánto se separa un mes de su promedio para ese mismo mes. Junio se compara con los otros junios, no con enero."],
      ["Tendencia", "Hacia dónde se mueve la serie con los años. Usamos la pendiente de Theil-Sen: la mediana de las pendientes entre todos los pares de años, que no se deja arrastrar por un año extremo."],
      ["Significancia", "Si no hubiera ninguna tendencia real, ¿qué tan raro sería ver un patrón así de ordenado? Eso es el valor p de la prueba de Mann-Kendall. Menos de 0,05 se suele llamar significativo."],
      ["Autocorrelación", "Cuando un año se parece al anterior, los datos tienen menos información de la que aparentan. Corregimos la prueba por eso; si no, encontraría tendencias donde no las hay."],
      ["Intervalo de confianza", "El rango de pendientes compatibles con los datos. Si incluye el cero, no podemos decir hacia dónde va."],
      ["Muchas pruebas", "Si pruebas muchas series, alguna saldrá significativa por azar. El valor q (Benjamini-Hochberg) corrige por eso."],
      ["Sin evidencia no es sin cambio", "Que una tendencia no sea significativa solo dice que estos datos no alcanzan para afirmarla. A veces solo hacen falta más años."],
    ] as [string, string][],
  },
  en: {
    title: "Earth System Detective · Stellar Horizons",
    brand: "Earth System Detective",
    navInvestigate: "Investigate",
    navCases: "Case files",
    navMethod: "How it works",
    team: "Stellar Horizons · NASA Space Apps 2026",
    langSwitch: "Español",
    langSwitchLabel: "Cambiar a español",
    footer: "Data: NASA GPM IMERG, MERRA-2 and GLDAS via Giovanni; MODIS via AppEEARS; base map NASA GIBS Blue Marble. Made in the Dominican Republic by Stellar Horizons. Open code and method.",
    h1: "Pick what to investigate. Predict. Check.",
    lede: "Real NASA data for two dry-forest areas of the Dominican Republic, 2001 to 2024. Before you see the answer, say what you think happened.",
    whatQ: "What do you want to investigate?",
    groupClimate: "Climate and water",
    groupVeg: "Vegetation seen from space",
    mapPoints: "Amber dots: dry-forest sites checked on satellite imagery; the record is their average.",
    whereQ: "Where?",
    measuredIn: "Measured in",
    dataType: "Data type",
    mapLabel: "Map of the selected area",
    mapDashed: "Dashed line: requested area.",
    mapPoint: " Amber dot: centre of the single model cell Giovanni uses (it falls outside the area).",
    mapBox: " Amber box: the data cells Giovanni averages.",
    hypothesis: "Your hypothesis",
    since2001: (v: string, r: string) => `Since 2001, ${v} in ${r}…`,
    predUp: "has increased",
    predDown: "has decreased",
    predNone: "has not changed clearly",
    reveal: "Reveal the evidence",
    factSlope: "Theil-Sen slope",
    factPerDecade: "per decade",
    factRange: "likely range (95 % CI)",
    factP: "Mann-Kendall p, corrected because consecutive years resemble each other",
    factYears: "complete years",
    chartAnom: "Each year compared with normal",
    chartRaw: "The data as it arrives",
    btnRaw: "See the raw data",
    btnAnom: "See it without the seasons",
    captionAnom: "Each dot is a year: how far, on average, it was from normal for each month. The amber line is the trend (Theil-Sen); the band shows the slopes compatible with the data.",
    axisAnom: (u: string) => `Difference from normal (${u})`,
    axisRaw: (u: string) => `Monthly value (${u})`,
    tipYear: (y: number, v: string, u: string) => `${y}: ${v} ${u} from normal`,
    otherWindow: "What if you look at another period?",
    windowLede: "Each square is a period of 10 years or more: the row is the start year and the column is the end year. Solid amber: looking only at those years you would conclude a significant trend (▲ up, ▼ down). Light amber: a hint. Grey: nothing clear. Tap any square and compare.",
    trapsTitle: "Misleading periods",
    trapsNote: "Picking the period that confirms what you want to see is one of the most common mistakes in science. That is why every period is shown here.",
    noTraps: "No period of 10 years or more shows a significant trend in the opposite direction. But look at the grey squares: with few years, often nothing can be detected. That is why long records matter.",
    fullSeries: (a: number, b: number) => `Full record ${a}–${b}`,
    tapCell: "Tap a square to see another period.",
    years: "years",
    range: "range",
    backFull: "Back to the full record",
    matrixAria: "Window map: rows = start year, columns = end year",
    matrixAxis: "year the period ends →",
    passport: "Evidence passport",
    pSource: "Source", pVariable: "Variable", pTool: "Tool", pBox: "Requested area", pBoxNote: "(west, south, east, north)",
    pData: "Data used", pFile: "File", pMethod: "Method", pAutocorr: "Autocorrelation", pMulti: "Multiple comparisons",
    pCode: "Code", pRepro: "Reproduce", pOpenGiovanni: "Open the same query in Giovanni",
    pAutocorrText: (r: string, f: string, p: string) => `annual lag-1 = ${r}; the Mann-Kendall variance was multiplied by ${f} (uncorrected p: ${p})`,
    pMultiText: (n: number, q: string) => `Benjamini-Hochberg q across ${n} series = ${q}`,
    pVerifyRecon: "Rebuilt from Giovanni's CSV; checked value by value against the regenerated original (identical when rounded to 4 decimals)",
    pVerifyOrig: "CSV downloaded from Giovanni, unchanged",
    pVerifyModis: "NASA AppEEARS CSV, unchanged; only observations that pass the quality filter",
    pMethodModis: "Monthly mean of valid observations at each point; the area is the mean of its points' anomalies. Annual anomaly with at least 9 months of data. Theil-Sen with 95 % CI; Mann-Kendall corrected for ties and AR(1) autocorrelation; Benjamini-Hochberg q across all records.",
    pMethodText: "Anomaly = value − mean of the same calendar month (2001–2024). Annual mean of anomalies (only years with 12 months). Theil-Sen slope with 95 % CI; Mann-Kendall test corrected for ties and for AR(1) autocorrelation; Benjamini-Hochberg q across all records.",
    loadError: "The data could not be loaded",
    testBanner: "SYNTHETIC TEST DATA. Nothing on this page is a real result.",
    caseH1: "PHANTOM case file: is green the same as recovered?",
    caseLede: "After a drought, a forest can look green again before it works as it did before. This case file compares when greenness (NDVI) recovers with when two signals of functioning recover: estimated productivity (GPP, a model) and leaf temperature compared with air temperature.",
    caseResultsReal: "Results with real MODIS data",
    caseResultsTest: "Test results (synthetic)",
    caseWaiting: "Status: waiting for the MODIS data",
    caseWaitingText: "The vegetation data was requested from NASA AppEEARS on 14 November: a point request (5 sites checked on satellite imagery, 2001–2024) and an area request (2 zones, 2012–2021). Until it arrives, this case file <strong>shows no result</strong> about the gap. What is already real: the droughts we will study.",
    droughtsH: "The droughts in this case file",
    droughtsNote: "SPI-3: 3-month rainfall compared with normal for that time of year (IMERG V07). Shaded bands are the droughts we use: SPI-3 below −1 for 2 months or more.",
    howH: "How \"recovered\" is decided",
    howP1: "Each signal is compared with normal for that time of year (median of the available years). A signal is <strong>impacted</strong> if it stays far below normal for 3 observations in a row (z &lt; −1.5). It <strong>recovers</strong> when it comes back to within one deviation of normal (z ≥ −1) and stays there for 3 observations in a row. If the next drought arrives first, the event is <strong>censored</strong>: we do not invent how long it would have taken.",
    howP2: "Δt = day function recovers − day greenness recovers. With 8- and 16-day composites, a difference under 32 days cannot be told apart from zero.",
    notClaimH: "What this case file does not claim",
    notClaim: "It does not measure the full health of the ecosystem. GPP comes from a model that partly uses the same greenness, so it is not independent; that is why we added the thermal signal. Five points are an exploration, not the affected area of a region.",
    case2H: "Case file 2: does the next drought arrive before recovery?",
    case2Lede: "A collision happens when a new drought starts while greenness is still below normal after the previous one.",
    case2Count: (c: number, n: number) => `${c} collisions in ${n} droughts evaluated (point × event).`,
    case2Pending: "Waiting for the same MODIS data. The rule is already coded and tested.",
    gapTableH: "Gap by drought and point",
    caseRealNote: "MODIS point data (AppEEARS, 5 sites, 2001–2024). The area request for the map is still processing. The points are an exploration, not the whole region.",
    phantomNoH: "What we found: the hypothesis does not hold at these points",
    phantomYesH: "What we found: there are signals supporting the hypothesis",
    phantomSummary: (n: number, w: number, b: number, a: number) => `Of ${n} comparisons where both signals recovered, ${w} fall within the method's precision (±32 days), in ${b} function came back before greenness and in ${a} after.`,
    phantomRobust: (after: string[], nBefore: number) => after.length
      ? `Robust in PHANTOM's direction (function after greenness): ${after.join("; ")}. Robust in the opposite direction: ${nBefore}.`
      : `No robust case in PHANTOM's direction. Robust cases in the opposite direction: ${nBefore}.`,
    phantomLateDip: (cases: string[]) => `Note: in ${cases.join("; ")} the function signal started to fall after greenness had already recovered. That is a separate drop, not a late recovery from the same one, so it does not count for the hypothesis. For GPP it may come from the weather the model uses, not from the plant.`,
    phantomCaveat: "Function returning before greenness fits leaves that resume transpiring (and cool down) before the foliage fully recovers. It is one possible reading, not proof: five points and few droughts per point.",
    hiddenRows: (n: number) => `${n} rows where neither signal had a sustained drop (no impact) are hidden.`,
    thPoint: "Point", thDrought: "Drought", thSignal: "Function signal", thState: "Status", thDt: "Δt (days)", thRobust: "Robustness",
    sigGpp: "GPP (model)", sigLst: "Leaves vs. air",
    challengeH: "Challenge the finding",
    challengeLede: "Change the assumptions. All 18 combinations are <strong>precomputed by the same code</strong> as the analysis (phantom/recovery.py); here you choose which one to see and check whether the conclusion holds.",
    cPoint: "Point", cDrought: "Drought", cSignal: "Signal", cGreen: "Greenness", cThreshold: "Threshold", cPersist: "Persistence",
    cWith: "With these assumptions:",
    cNA: "Combination not available.",
    cSummary: (n: number, v: number, pos: number, neg: number, mid: number) => `Of ${n} combinations, ${v} have both recoveries: ${pos} put function more than 32 days after greenness, ${neg} more than 32 days before, and ${mid} fall within the method's precision.`,
    days: "days",
    axisDt: "Δt = function − greenness (days)",
    methodH1: "How a data detective thinks",
    methodLede: "No number in this tool is typed by hand: they all come from the same open code that runs on NASA data. These are the ideas it uses.",
    limitsH: "Limits worth knowing",
    limits: "MERRA-2 and GLDAS are models, not direct measurements, and their cells are larger than the areas. GLDAS uses rainfall as an input: if it agrees with IMERG, that is not an independent confirmation. With 24 years, a small trend can exist without being detectable.",
    updated: (d: string) => `Data updated: ${d}. Full method: METHODOLOGY.md in the repository.`,
    glossary: [
      ["Variable", "What is measured: rainfall, temperature, moisture. Each has a unit and a source."],
      ["Seasonality", "The cycle that repeats every year: the rainy season, summer. It is much larger than a trend over decades, so it has to be removed first."],
      ["Anomaly", "How far a month is from its own average. June is compared with other Junes, not with January."],
      ["Trend", "Which way the record moves over the years. We use the Theil-Sen slope: the median of the slopes between every pair of years, which one extreme year cannot drag around."],
      ["Significance", "If there were no real trend, how unusual would such an orderly pattern be? That is the p-value of the Mann-Kendall test. Below 0.05 is usually called significant."],
      ["Autocorrelation", "When one year resembles the previous one, the data carry less information than they seem to. We correct the test for that; otherwise it would find trends that are not there."],
      ["Confidence interval", "The range of slopes compatible with the data. If it includes zero, we cannot say which way it is going."],
      ["Many tests", "If you test many records, some will look significant by chance. The q-value (Benjamini-Hochberg) corrects for that."],
      ["No evidence is not no change", "A trend that is not significant only means these data are not enough to claim it. Sometimes all it needs is more years."],
    ] as [string, string][],
  },
};

export type UIStrings = typeof UI.es;
export const T = (): UIStrings => UI[current] as UIStrings;

const VAR_EN: Record<string, Omit<VariableMeta, "fuente" | "producto">> = {
  imerg_precip: {
    nombre: "Rainfall", pregunta: "is it raining more or less than before?",
    definicion: "How much water falls on the area in a month. Measured by satellites of the GPM mission.",
    unidad: "mm/month", unidad_larga: "millimetres of water per month", tipo: "satellite observation", aviso: null,
  },
  merra2_t2m: {
    nombre: "Air temperature", pregunta: "is it hotter than before?",
    definicion: "Temperature 2 metres above the ground. It comes from MERRA-2, a model that combines thousands of observations.",
    unidad: "°C", unidad_larga: "degrees Celsius", tipo: "model (reanalysis)",
    aviso: "The MERRA-2 cell is about 55 × 65 km and its centre falls outside the area: it is the temperature of the surroundings, not of an exact spot.",
  },
  gldas_soilmoi0_10cm: {
    nombre: "Soil moisture", pregunta: "is the soil drier than before?",
    definicion: "Water held in the top 10 cm of soil. Estimated by the GLDAS model from rain, sunshine and temperature.",
    unidad: "kg/m²", unidad_larga: "kilograms of water per square metre (1 kg/m² = 1 mm of water)", tipo: "model",
    aviso: "GLDAS uses rainfall as an input: if it agrees with rainfall, that is not an independent confirmation.",
  },
  gldas_rootmoist: {
    nombre: "Water for roots", pregunta: "do plants have less water available?",
    definicion: "Water in the soil layer where roots live. Also estimated by the GLDAS model.",
    unidad: "kg/m²", unidad_larga: "kilograms of water per square metre (1 kg/m² = 1 mm of water)", tipo: "model",
    aviso: "GLDAS uses rainfall as an input: if it agrees with rainfall, that is not an independent confirmation.",
  },
};

Object.assign(VAR_EN, {
  modis_ndvi: {
    nombre: "Vegetation greenness", pregunta: "is the forest more or less green?",
    definicion: "NDVI compares the red and near-infrared light that vegetation reflects. Higher = greener, denser leaves. Measured by the Terra satellite (MODIS) every 16 days at 250 m.",
    unidad: "NDVI", unidad_larga: "NDVI index (−1 to 1; healthy vegetation is usually 0.3 to 0.9)", tipo: "satellite observation",
    aviso: "These are dry-forest points checked on satellite imagery (3 in Montecristi, 1 in Jaragua), not the whole region.",
  },
  modis_lst: {
    nombre: "Surface temperature", pregunta: "are the ground and canopy heating up?",
    definicion: "Daytime temperature of the surface (leaves, soil) measured in the thermal infrared by Terra (MODIS), every 8 days at 1 km. It is not air temperature.",
    unidad: "°C", unidad_larga: "degrees Celsius at the surface", tipo: "satellite observation",
    aviso: "Only clear days count. Since 2020 Terra passes over earlier in the morning, which tends to give slightly cooler surfaces in recent years (NASA). These are points, not the whole region.",
  },
  modis_gpp: {
    nombre: "Estimated productivity", pregunta: "are plants fixing more or less carbon?",
    definicion: "GPP: how much carbon plants fix through photosynthesis. MODIS computes it with a model that uses greenness and weather; it is not a direct measurement.",
    unidad: "gC/m²/day", unidad_larga: "grams of carbon per square metre per day", tipo: "model with satellite data",
    aviso: "GPP partly uses the same greenness (FPAR) and reanalysis weather: it does not confirm NDVI independently. These are points, not the whole region.",
  },
});

const REG_EN: Record<string, Pick<RegionMeta, "zona" | "descripcion">> = {
  noroeste: { zona: "Northwest Line", descripcion: "Dry-forest hills and scrub in the far northwest, near the border with Haiti." },
  jaragua: { zona: "Southwest", descripcion: "Jaragua National Park: one of the largest dry forests in the Caribbean." },
};

export function varMeta(index: Index, id: string): VariableMeta {
  const es = index.variables[id];
  return current === "es" || !VAR_EN[id] ? es : { ...es, ...VAR_EN[id] };
}

export function regionMeta(index: Index, id: string): RegionMeta {
  const es = index.regiones[id];
  return current === "es" || !REG_EN[id] ? es : { ...es, ...REG_EN[id] };
}
