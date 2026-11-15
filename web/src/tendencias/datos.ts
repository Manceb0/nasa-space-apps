// Datos de la pantalla de tendencias: tipos del contrato 1.0 (results/tendencias/web/CONTRATO.md)
// y consultas de solo lectura. Aquí no se calcula estadística: todo viene del chat de datos.
import { load } from "../data";
import { getLang } from "../i18n";
import { fmt } from "../text";

export interface VarMeta {
  id: string; label_es: string; label_en: string; unidad: string; unidad_tendencia: string;
  descripcion: string; por_que_importa: string; tipo: "seco" | "humedo"; aumento_significa: string;
  periodos: string[]; grupo: "periodos_secos" | "lluvia" | "sequia";
}
export interface Vars {
  generado_utc: string;
  productos: Record<string, { nombre: string; tipo_fuente: string; resolucion_nativa: string; cita: string }>;
  periodos: Record<string, { label_es: string; label_en: string; meses: number[] }>;
  clases: Record<string, { label_es: string; label_en: string; color: string; descripcion: string }>;
  umbral_significancia: { q_fdr: number; regla: string };
  prueba: string; nota_causalidad: string;
  variables: VarMeta[];
}
export interface Tr {
  pendiente_decada: number; ic95: [number, number]; p: number; q: number | null; sig: boolean | null; sig_p05?: boolean;
  mdt: number; media: number; detectable: boolean; pendiente_pct_decada: number;
}
type TrRow = { clase: string } & Record<string, Tr | string>;
export interface Prov {
  regiones: { id: string; nombre: string; es_nacional: boolean }[];
  anios: Record<string, number[]>;
  series: Record<string, Record<string, Record<string, Record<string, (number | null)[]>>>>;
  tendencias: Record<string, Record<string, Record<string, TrRow>>>;
}
export interface CellLayer { pendiente_decada: (number | null)[]; q: (number | null)[] }
export interface Rej {
  nx: number; ny: number; lat: number[]; lon: number[]; lat_bordes: number[]; lon_bordes: number[]; incluida: number[];
  clases_codigo?: string[];
  capas: Record<string, Record<string, Record<string, CellLayer | (number | null)[]>>>;
}
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type FC = { features: any[] };

export const LL = (es: string, en: string) => (getLang() === "es" ? es : en);
export const esc = (s: string) => s.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]!));
export const digits = (v: number) => (Math.abs(v) >= 100 ? 0 : Math.abs(v) >= 10 ? 1 : 2);
export const num = (v: number, d = digits(v)) => fmt(v, d);
export const sgn = (v: number, d = digits(v)) => (v > 0 ? "+" : "") + num(v, d);

/** Lo que el usuario está mirando. */
export interface Sel { ind: string; per: string; reg: string; src: string }

export type Tier = "sabemos" | "creemos" | "comprobar" | "nada";

export async function loadTrends() {
  const [V, P, R, fc] = await Promise.all([
    load<Vars>("tendencias/variables.json"), load<Prov>("tendencias/provincias.json"),
    load<Rej>("tendencias/rejilla.json"), load<FC>("limites/provincias.geojson").catch(() => null),
  ]);
  return new TrendData(V, P, R, fc);
}

export class TrendData {
  readonly prods: string[];
  readonly provs: { id: string; nombre: string }[];
  readonly isoToShape: Record<string, string> = {};
  readonly shapeToIso: Record<string, string> = {};
  constructor(readonly V: Vars, readonly P: Prov, readonly R: Rej, readonly fc: FC | null) {
    this.prods = Object.keys(V.productos);
    this.provs = P.regiones.filter((r) => !r.es_nacional).sort((a, b) => a.nombre.localeCompare(b.nombre, "es"));
    fc?.features.forEach((f) => { this.isoToShape[f.properties.shapeISO] = f.properties.shapeID; this.shapeToIso[f.properties.shapeID] = f.properties.shapeISO; });
  }
  get both() { return this.prods.includes("IMERG") && this.prods.includes("CHIRPS"); }
  vm(id: string) { return this.V.variables.find((v) => v.id === id)!; }
  lab(o: { label_es: string; label_en: string }) { return LL(o.label_es, o.label_en); }
  regName(id: string) { return id === "DO" ? LL("República Dominicana", "Dominican Republic") : this.P.regiones.find((r) => r.id === id)?.nombre ?? id; }
  /** Periodo válido para esa variable (el SPI solo existe anual). */
  perFor(ind: string, per: string) { return this.vm(ind).periodos.includes(per) ? per : "anual"; }
  years(s: Sel) { return s.ind.startsWith("SPI") ? this.P.anios.spi : this.P.anios[this.perFor(s.ind, s.per)]; }
  series(s: Sel, src = s.src, reg = s.reg) { return this.P.series[s.ind]?.[this.perFor(s.ind, s.per)]?.[src]?.[reg] ?? null; }
  row(s: Sel, reg = s.reg) { return this.P.tendencias[s.ind]?.[this.perFor(s.ind, s.per)]?.[reg] ?? null; }
  tr(s: Sel, src = s.src, reg = s.reg) { return (this.row(s, reg)?.[src] as Tr | undefined) ?? null; }
  cells(s: Sel, src = s.src) { return this.R.capas[s.ind]?.[this.perFor(s.ind, s.per)]?.[src] as CellLayer | undefined; }
  /** Clase de confianza por celda (índice en clases_codigo) o null. */
  cellClass(s: Sel) { return (this.R.capas[s.ind]?.[this.perFor(s.ind, s.per)]?.clase as (number | null)[] | undefined) ?? null; }
  /** En DO hay una sola serie y una sola prueba: p < 0,05. En provincias: q ≤ 0,10 (FDR entre las 32). */
  isSig(t: Tr, reg: string) { return reg === "DO" ? (t.sig_p05 ?? t.p < 0.05) : t.sig === true; }
  sigRule(reg: string) { return reg === "DO" ? LL("p < 0,05 (una sola serie)", "p < 0.05 (single series)") : LL("q ≤ 0,10 (FDR entre 32 provincias)", "q ≤ 0.10 (FDR across 32 provinces)"); }
  /** Subir un índice «seco» es ir hacia lo seco; se pinta en cálido. */
  warmIfUp(ind: string) { return this.vm(ind).tipo === "seco"; }
  towardDry(ind: string, v: number) { return (v > 0) === this.warmIfUp(ind); }

  tier(s: Sel, reg = s.reg): { tier: Tier; label: string; color: string; why: string } {
    const c = this.row(s, reg)?.clase ?? "";
    const cl = this.V.clases[c];
    if (c === "robusta") return { tier: "sabemos", label: this.lab(cl), color: cl.color, why: cl.descripcion };
    if (c === "consistente") return { tier: "creemos", label: this.lab(cl), color: cl.color, why: cl.descripcion };
    if (c === "en disputa") return { tier: "comprobar", label: this.lab(cl), color: cl.color, why: cl.descripcion };
    if (c === "sin señal detectable") return { tier: "nada", label: this.lab(cl), color: cl.color, why: cl.descripcion };
    if (c === "sin dato") return { tier: "nada", label: LL("Sin dato", "No data"), color: "#6b6f75", why: LL("Faltan años en alguna de las dos series (por ejemplo, años sin sequía): no se calcula la tendencia.", "One of the two series has missing years (for example, years with no drought): no trend is computed.") };
    // «un solo producto»: todavía no hay segunda opinión
    const t = this.tr(s, s.src, reg);
    return t && this.isSig(t, reg)
      ? { tier: "creemos", label: LL("Una sola fuente", "One source only"), color: "#64d2ff", why: LL("IMERG muestra una tendencia significativa, pero falta que CHIRPS la confirme o la dispute.", "IMERG shows a significant trend, but CHIRPS has yet to confirm or dispute it.") }
      : { tier: "nada", label: LL("Sin señal detectable", "No detectable signal"), color: "#8e8e93", why: LL("Con una fuente y 24 años no se detecta una tendencia. No quiere decir que no haya cambio.", "With one source and 24 years no trend is detected. It does not mean there is no change.") };
  }

  /** Bounding box de una provincia (para encuadrar el mapa). */
  bbox(iso: string): [[number, number], [number, number]] | undefined {
    const f = this.fc?.features.find((x) => x.properties.shapeISO === iso);
    if (!f) return undefined;
    const polys = f.geometry.type === "Polygon" ? [f.geometry.coordinates] : f.geometry.coordinates;
    let x0 = 180, y0 = 90, x1 = -180, y1 = -90;
    for (const pl of polys) for (const [x, y] of pl[0]) { x0 = Math.min(x0, x); y0 = Math.min(y0, y); x1 = Math.max(x1, x); y1 = Math.max(y1, y); }
    return [[x0, y0], [x1, y1]];
  }
}
