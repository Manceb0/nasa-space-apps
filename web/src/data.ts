// Tipos de los JSON que escribe phantom/export_web.py. La web solo lee; no calcula estadística.

export type Verdict = "sube" | "baja" | "indicio" | "sin_evidencia" | "insuficiente";

export interface Trend {
  n: number;
  pendiente_decada: number;
  intercepto: number;
  ic95_decada: [number, number];
  p_mk: number; // corregido por autocorrelación AR(1)
  p_mk_simple: number;
  factor_varianza_ar1: number;
  tau: number;
  autocorr_lag1: number | null;
  cambio_total: number;
  veredicto: Verdict;
  q_bh?: number;
}

export interface Window extends Trend {
  inicio: number;
  fin: number;
}

export interface VariableMeta {
  nombre: string;
  pregunta: string;
  definicion: string;
  unidad: string;
  unidad_larga: string;
  fuente: string;
  producto: string;
  tipo: string;
  aviso: string | null;
}

export interface RegionMeta {
  nombre: string;
  zona: string;
  descripcion: string;
  centro: [number, number];
}

export interface Index {
  generado: string;
  variables: Record<string, VariableMeta>;
  regiones: Record<string, RegionMeta>;
  series: { id: string; variable: string; region: string; veredicto: Verdict }[];
}

export interface Series {
  id: string;
  variable: string;
  region: string;
  meses: string[];
  valores: (number | null)[];
  climatologia: number[];
  amplitud_estacional: number;
  anomalia_mensual: (number | null)[];
  anual: { anios: number[]; anomalia: number[] };
  completa: Trend;
  ventanas: Window[];
  ventanas_que_enganan: Window[];
  autocorr_lag1_mensual: number | null;
  pasaporte: {
    fuente: string;
    producto: string;
    herramienta: string;
    caja_pedida: [number, number, number, number] | null;
    caja_datos: [number, number, number, number] | null;
    puntos?: [number, number, string][] | null;
    url_reproducir: string | null;
    archivo: string;
    reconstruido: boolean;
    verificacion: string;
    metodo: string;
    codigo: string;
    descargado: string;
  };
}

export interface DroughtEvent {
  inicio: string;
  fin: string;
  duracion_meses: number;
  severidad: number;
  pico: number;
  recuperacion_candidata: string | null;
}

export interface PhantomEventRow {
  id: string;
  region: string;
  evento_inicio: string;
  evento_fin: string;
  funcion: "gpp_modelo" | "lst_menos_aire";
  estado: string;
  dt_dias: number | null;
  dt_es_cota_inferior: boolean;
  verde_recuperacion: string | null;
  funcion_recuperacion: string | null;
  colision_verde?: boolean;
  funcion_cae_despues_del_verde?: boolean;
  rob_etiqueta: string;
  rob_n_validas: number;
  rob_dt_mediana: number | null;
}

export interface SensRow {
  id: string;
  evento_inicio: string;
  funcion: string;
  verde: string;
  umbral: number;
  persistencia: number;
  estado: string;
  dt_dias: number | null;
}

export interface Phantom {
  estado_modis: string;
  sequias: { region: string; spi3: { meses: string[]; valores: (number | null)[] }; eventos: DroughtEvent[] }[];
  eventos: PhantomEventRow[];
  sensibilidad: SensRow[];
  colisiones: { eventos_evaluados: number; ventanas_cortadas: number; colisiones: number } | null;
}

const cache = new Map<string, unknown>();

export async function load<T>(path: string): Promise<T> {
  if (!cache.has(path)) {
    const r = await fetch(`./data/${path}`);
    if (!r.ok) throw new Error(`No pude leer ${path} (${r.status})`);
    cache.set(path, await r.json());
  }
  return cache.get(path) as T;
}
