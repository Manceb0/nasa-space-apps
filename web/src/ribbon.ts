// Recovery Ribbon: la visualización protagonista de PHANTOM.
// Cada cinta es una sequía auditada en un lugar. A lo largo de la cinta corre el tiempo desde el inicio de la
// sequía; sus dos bordes son el verdor (NDVI) y la función (GPP del modelo, o las hojas frente al aire), ambos en
// desviaciones robustas de lo normal para esa época del año (z). La superficie entre los bordes es la brecha:
// toma el color de la señal que va por delante. Las sequías se apilan en profundidad por fecha.
// Todo lo que se dibuja sale de puntos.json (series z) y phantom.json (auditorías); nada es decorativo.
// La vista 2D muestra exactamente los mismos valores para la sequía elegida.
import * as Plot from "@observablehq/plot";
import type { Audit, Puntos, ZSeries } from "./data";
import { alignTo, smooth } from "./charts";
import { fmt } from "./text";
import { getLang, T } from "./i18n";

const DAY = 86400000;
const D0 = -90;
const D1 = 540;
const ZLO = -4;
const ZHI = 3;
export const GREEN = "#30d158";
export const FUNC = "#ff9f0a";
const L = (es: string, en: string) => (getLang() === "es" ? es : en);

export type Fn = "gpp_modelo" | "lst_menos_aire" | "ndii_agua";

export interface Lane {
  audit: Audit;
  label: string;
  rows: { day: number; g: number; f: number; date: Date }[];
  endDay: number;
  greenRec: number | null;
  funcRec: number | null;
}

const toDate = (s: string) => new Date(`${s.slice(0, 10)}T00:00:00`);
const days = (a: Date, b: Date) => Math.round((b.getTime() - a.getTime()) / DAY);

/** Una cinta por sequía: verdor y función alineados en las fechas de la función, suavizados (mediana de 3). */
export function buildLanes(pts: Puntos, audits: Audit[], id: string, fn: Fn): Lane[] {
  const z = pts.z[id];
  if (!z || !z.ndvi || !z[fn]) return [];
  const rows = alignTo(smooth(z.ndvi as ZSeries), smooth(z[fn] as ZSeries));
  return audits
    .filter((a) => a.id === id)
    .sort((a, b) => a.evento_inicio.localeCompare(b.evento_inicio))
    .map((a) => {
      const on = toDate(a.evento_inicio);
      const rec = (k: string) => (a[k] ? days(on, toDate(a[k] as string)) : null);
      return {
        audit: a,
        label: a.evento_inicio.slice(0, 7),
        rows: rows
          .map((r) => ({ day: days(on, r.date), g: r.za, f: r.zb, date: r.date }))
          .filter((r) => r.day >= D0 && r.day <= D1),
        endDay: days(on, toDate(a.evento_fin)),
        greenRec: rec("ndvi_recupera"),
        funcRec: rec(`${fn}_recupera`),
      };
    })
    .filter((l) => l.rows.length > 4);
}

/* ───────────── 3D: cintas apiladas en un canvas, con cámara que se puede girar ───────────── */

export interface Stage {
  setLanes(l: Lane[], selected: number): void;
  setAnchor(a: [number, number] | null): void;
  select(i: number): void;
  play(): void;
  stop(): void;
  playing(): boolean;
  destroy(): void;
}

export function ribbonStage(host: HTMLElement, onSelect: (i: number) => void, onTick: (day: number) => void): Stage {
  const canvas = document.createElement("canvas");
  canvas.setAttribute("role", "img");
  canvas.setAttribute("aria-label", L("Cintas de recuperación en 3D. La misma información está en la vista 2D y en la tabla.",
    "3D recovery ribbons. The same information is in the 2D view and the table."));
  host.append(canvas);
  const ctx = canvas.getContext("2d")!;
  let lanes: Lane[] = [];
  let sel = 0;
  let yaw = -0.28;
  let pitch = 0.36;
  let playhead = D1;
  let anchor: [number, number] | null = null;
  let raf = 0;
  let anim = 0;
  let W = 0;
  let H = 0;
  const labelHits: { x: number; y: number; i: number }[] = [];

  const resize = () => {
    const r = host.getBoundingClientRect();
    const dpr = Math.min(2, window.devicePixelRatio || 1);
    W = r.width; H = r.height;
    canvas.width = Math.round(W * dpr); canvas.height = Math.round(H * dpr);
    canvas.style.width = `${W}px`; canvas.style.height = `${H}px`;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    draw();
  };

  // Mundo: x = días (−90…540) → −1.7…1.7; y = z (−4…3) → altura; profundidad = sequía (la más reciente al fondo)
  const X = (d: number) => -1.7 + ((d - D0) / (D1 - D0)) * 3.4;
  const Y = (z: number) => Math.max(ZLO, Math.min(ZHI, z)) * 0.17;
  const Zl = (i: number) => (lanes.length < 2 ? 0 : -1.25 + (i / (lanes.length - 1)) * 2.5);
  const FLOOR = Y(ZLO);

  const project = (x: number, y: number, z: number): [number, number, number] => {
    const cy = Math.cos(yaw), sy = Math.sin(yaw), cp = Math.cos(pitch), sp = Math.sin(pitch);
    const x1 = x * cy - z * sy;
    const z1 = x * sy + z * cy;
    const y2 = y * cp - z1 * sp;
    const z2 = y * sp + z1 * cp;
    const f = 4.2 / (4.2 + z2 + 1.2);
    const s = Math.min(W * (W > 1000 ? 0.175 : W < 600 ? 0.34 : 0.25), H * 0.46);
    return [W * (W > 1000 ? 0.37 : 0.5) + x1 * f * s, H * (W > 1000 ? 0.53 : 0.5) - y2 * f * s, z2];
  };

  const line = (pts: [number, number, number][], color: string, w: number, dash: number[] = []) => {
    if (pts.length < 2) return;
    ctx.beginPath();
    ctx.moveTo(pts[0][0], pts[0][1]);
    for (const p of pts.slice(1)) ctx.lineTo(p[0], p[1]);
    ctx.setLineDash(dash);
    ctx.strokeStyle = color; ctx.lineWidth = w; ctx.stroke();
    ctx.setLineDash([]);
  };

  const rgba = (hex: string, a: number) => {
    const n = parseInt(hex.slice(1), 16);
    return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${a})`;
  };

  function draw() {
    if (!W) return;
    ctx.clearRect(0, 0, W, H);
    labelHits.length = 0;
    if (!lanes.length) return;
    ctx.font = "12px Inter, -apple-system, system-ui, sans-serif";

    // Suelo: una retícula de puntos cada 30 días por sequía (el entramado real de tiempo × sequías)
    for (let i = 0; i < lanes.length; i++) {
      for (let d = 0; d <= D1; d += 30) {
        const p = project(X(d), FLOOR, Zl(i));
        ctx.fillStyle = d % 90 === 0 ? "rgba(255,255,255,0.32)" : "rgba(255,255,255,0.14)";
        ctx.fillRect(p[0] - 1, p[1] - 1, 2, 2);
      }
    }
    // El lugar en el mapa, unido al inicio de su cinta elegida
    if (anchor) {
      const o = project(X(0), FLOOR, Zl(sel));
      line([[anchor[0], anchor[1], 0], o], "rgba(255,159,10,0.55)", 1, [4, 4]);
      ctx.beginPath(); ctx.arc(anchor[0], anchor[1], 13, 0, Math.PI * 2);
      ctx.strokeStyle = "rgba(255,159,10,0.6)"; ctx.lineWidth = 1; ctx.stroke();
    }
    // Eje de días al frente
    const front = Zl(lanes.length - 1) + 0.25;
    for (let d = 0; d <= D1; d += W < 600 ? 180 : 90) {
      const p = project(X(d), FLOOR, front);
      ctx.fillStyle = "#8a8c92"; ctx.textAlign = "center";
      ctx.fillText(d === 0 ? L("inicio", "onset") : `${d} d`, p[0], p[1] + 16);
    }
    // Orden del pintor: de la cinta más lejana a la más cercana
    const order = lanes.map((_, i) => i).sort((a, b) => project(0, 0, Zl(b))[2] - project(0, 0, Zl(a))[2]);
    for (const i of order) {
      const ln = lanes[i];
      const z = Zl(i);
      const on = i === sel;
      const k = on ? 1 : 0.2;
      // Sequía (inicio → fin) como franja en el suelo
      const s0 = project(X(0), FLOOR, z - 0.05), s1 = project(X(Math.min(D1, ln.endDay)), FLOOR, z - 0.05);
      const s2 = project(X(Math.min(D1, ln.endDay)), FLOOR, z + 0.05), s3 = project(X(0), FLOOR, z + 0.05);
      ctx.beginPath(); ctx.moveTo(s0[0], s0[1]); ctx.lineTo(s1[0], s1[1]); ctx.lineTo(s2[0], s2[1]); ctx.lineTo(s3[0], s3[1]); ctx.closePath();
      ctx.fillStyle = `rgba(229,86,111,${0.55 * k})`; ctx.fill();

      const rows = ln.rows.filter((r) => r.day <= playhead);
      // La brecha: la superficie entre los dos bordes, del color de la señal que va delante
      for (let j = 0; j < rows.length - 1; j++) {
        const a = rows[j], b = rows[j + 1];
        const g0 = project(X(a.day), Y(a.g), z), g1 = project(X(b.day), Y(b.g), z);
        const f0 = project(X(a.day), Y(a.f), z), f1 = project(X(b.day), Y(b.f), z);
        const gap = (a.g - a.f + b.g - b.f) / 2;
        const alpha = (0.12 + 0.5 * Math.min(1, Math.abs(gap) / 2.5)) * k;
        ctx.beginPath(); ctx.moveTo(g0[0], g0[1]); ctx.lineTo(g1[0], g1[1]); ctx.lineTo(f1[0], f1[1]); ctx.lineTo(f0[0], f0[1]); ctx.closePath();
        ctx.fillStyle = rgba(gap >= 0 ? GREEN : FUNC, alpha); ctx.fill();
      }
      // Umbral de recuperación (z = −1)
      line([project(X(D0), Y(-1), z), project(X(D1), Y(-1), z)], `rgba(255,255,255,${0.18 * k + 0.04})`, 1, [3, 4]);
      // Los dos bordes
      line(rows.map((r) => project(X(r.day), Y(r.f), z)), rgba(FUNC, 0.25 + 0.75 * k), on ? 2.4 : 1);
      line(rows.map((r) => project(X(r.day), Y(r.g), z)), rgba(GREEN, 0.25 + 0.75 * k), on ? 2.4 : 1);
      // Día en que cada señal se recupera
      for (const [d, c] of [[ln.greenRec, GREEN], [ln.funcRec, FUNC]] as [number | null, string][]) {
        if (d === null || d > playhead || d > D1) continue;
        const p = project(X(d), Y(-1), z);
        const fl = project(X(d), FLOOR, z);
        line([fl, p], rgba(c, 0.5 * k), 1);
        ctx.beginPath(); ctx.arc(p[0], p[1], on ? 4.5 : 3, 0, Math.PI * 2);
        ctx.fillStyle = rgba(c, 0.4 + 0.6 * k); ctx.fill();
      }
      // Etiqueta de la sequía, a la izquierda de su cinta
      const lp = project(X(D0) - 0.06, FLOOR, z);
      ctx.textAlign = "right";
      ctx.fillStyle = on ? "#ffffff" : "rgba(169,171,176,0.8)";
      ctx.font = `${on ? 600 : 400} 12px Inter, -apple-system, system-ui, sans-serif`;
      if (on || i === 0 || i === lanes.length - 1) ctx.fillText(ln.label, lp[0], lp[1] + 4);
      labelHits.push({ x: lp[0] - 24, y: lp[1], i });
    }
    // La escala de z en la cinta elegida
    {
      const z = Zl(sel);
      ctx.textAlign = "right"; ctx.font = "11px Inter, -apple-system, system-ui, sans-serif";
      for (const v of [-2, -1, 0, 2]) {
        const p = project(X(D0) - 0.02, Y(v), z);
        const q = project(X(D0), Y(v), z);
        line([p, q], "rgba(255,255,255,0.5)", 1);
        ctx.fillStyle = "#a9abb0"; ctx.fillText(v === -1 ? "z −1" : `${v > 0 ? "+" : ""}${v}`, p[0] - 4, p[1] + 4);
      }
    }
    // Cabezal de reproducción
    if (playhead < D1) {
      const a = project(X(playhead), FLOOR, Zl(0) - 0.15), b = project(X(playhead), FLOOR, front);
      line([a, b], "rgba(255,255,255,0.7)", 1);
    }
  }

  // Girar arrastrando (ratón o dedo); en el teléfono el arrastre vertical sigue desplazando la página
  let drag: { x: number; y: number; yaw: number; pitch: number } | null = null;
  canvas.addEventListener("pointerdown", (e) => { drag = { x: e.clientX, y: e.clientY, yaw, pitch }; canvas.setPointerCapture(e.pointerId); });
  canvas.addEventListener("pointermove", (e) => {
    if (!drag) return;
    yaw = Math.max(-1.0, Math.min(0.35, drag.yaw + (e.clientX - drag.x) * 0.006));
    pitch = Math.max(0.12, Math.min(0.8, drag.pitch + (e.clientY - drag.y) * 0.004));
    if (!raf) raf = requestAnimationFrame(() => { raf = 0; draw(); });
  });
  canvas.addEventListener("pointerup", (e) => {
    const moved = drag ? Math.hypot(e.clientX - drag.x, e.clientY - drag.y) : 99;
    drag = null;
    if (moved < 4) {
      const r = canvas.getBoundingClientRect();
      const x = e.clientX - r.left, y = e.clientY - r.top;
      let best = -1, bd = 26;
      for (const h of labelHits) { const d = Math.hypot(h.x - x, h.y - y); if (d < bd) { bd = d; best = h.i; } }
      if (best >= 0) onSelect(best);
    }
  });
  const ro = new ResizeObserver(resize);
  ro.observe(host);

  const stopAnim = () => { if (anim) cancelAnimationFrame(anim); anim = 0; };
  return {
    setLanes(l, s) { lanes = l; sel = Math.min(s, Math.max(0, l.length - 1)); resize(); },
    select(i) { sel = i; draw(); },
    setAnchor(a) { anchor = a; draw(); },
    play() {
      stopAnim();
      const t0 = performance.now();
      const dur = 7000;
      const step = (now: number) => {
        const f = Math.min(1, (now - t0) / dur);
        playhead = D0 + f * (D1 - D0);
        draw(); onTick(playhead);
        if (f < 1) anim = requestAnimationFrame(step); else { anim = 0; onTick(D1 + 1); }
      };
      anim = requestAnimationFrame(step);
    },
    stop() { stopAnim(); playhead = D1; draw(); onTick(D1 + 1); },
    playing: () => anim !== 0,
    destroy() { stopAnim(); ro.disconnect(); canvas.remove(); },
  };
}

/* ───────────── 2D: la sequía elegida con sus valores exactos ───────────── */

export function ribbon2D(ln: Lane, fnLabel: string, width: number, height = 300): SVGSVGElement | HTMLElement {
  const rows = ln.rows;
  const marks: Plot.Markish[] = [
    Plot.rectX([0], { x1: 0, x2: Math.min(D1, ln.endDay), fill: "#ff453a", fillOpacity: 0.16 }),
    Plot.ruleY([-1], { stroke: "#ffffff", strokeOpacity: 0.35, strokeDasharray: "3,4" }),
    Plot.differenceY(rows, { x: "day", y1: "f", y2: "g", positiveFill: GREEN, negativeFill: FUNC, fillOpacity: 0.32, stroke: "none" }),
    Plot.line(rows, { x: "day", y: "f", stroke: FUNC, strokeWidth: 2 }),
    Plot.line(rows, { x: "day", y: "g", stroke: GREEN, strokeWidth: 2 }),
    Plot.tip(rows, Plot.pointerX({ x: "day", y: "g", title: (r: Lane["rows"][number]) =>
      `${r.date.toISOString().slice(0, 10)} · ${r.day} ${L("días", "days")}\n${L("Verdor", "Greenness")} z ${fmt(r.g, 2)}\n${fnLabel} z ${fmt(r.f, 2)}\n${L("Brecha", "Gap")} ${fmt(r.g - r.f, 2)}` })),
  ];
  for (const [d, c, name] of [[ln.greenRec, GREEN, L("verdor", "greenness")], [ln.funcRec, FUNC, fnLabel]] as [number | null, string, string][]) {
    if (d === null || d > D1) continue;
    marks.push(Plot.ruleX([d], { stroke: c, strokeOpacity: 0.7 }));
    marks.push(Plot.text([d], { x: (v: number) => v, frameAnchor: "top", text: () => `${name} ${L("vuelve", "back")} · ${L("día", "day")} ${d}`, fill: c, dy: -6, fontSize: 11, textAnchor: c === GREEN ? "end" : "start", dx: c === GREEN ? -4 : 4 }));
  }
  return Plot.plot({
    width,
    height,
    marginLeft: 40,
    marginTop: 26,
    marginBottom: 34,
    style: { background: "transparent", color: "#8a8c92", fontFamily: "Inter, -apple-system, system-ui, sans-serif", fontSize: "12px" },
    x: { domain: [D0, D1], label: L("días desde el inicio de la sequía →", "days since the drought began →"), ticks: [0, 90, 180, 270, 360, 450, 540] },
    y: { domain: [ZLO, ZHI], label: L("↑ z (desviación de lo normal)", "↑ z (departure from normal)"), ticks: [-4, -2, -1, 0, 2], grid: true },
    marks,
  });
}

export const verdictColor = (v: string) =>
  ["fantasma", "verdor_tarde", "caida_posterior", "estres_invisible", "sin_recuperacion"].includes(v) ? FUNC : v === "consistente" ? "#ffffff" : "#8a8c92";

export const fnName = (fn: Fn) => ({ gpp_modelo: T().sigGpp, lst_menos_aire: T().sigLst, ndii_agua: T().sigNdii }[fn]);
