"""Recovery Integrity: auditoría de la afirmación "la vegetación se recuperó" tras una sequía.

No certifica la salud del ecosistema. Comprueba cuánta evidencia satelital independiente sostiene
la afirmación y qué evidencia la contradice, con tres fallos posibles:

1. Discordancia: el verdor vuelve, pero una señal de función (GPP modelo, dosel vs. aire) no vuelve
   o vuelve mucho después (o al revés).
2. Colisión: la siguiente sequía empieza antes de que todas las señales impactadas se recuperen;
   el episodio queda censurado y no se puede etiquetar como "recuperado".
3. Fragilidad de la definición: la conclusión cambia al mover el umbral o la persistencia.

Más la condición previa de calidad: suficientes observaciones válidas en la ventana.
"""

from __future__ import annotations

from itertools import product

import pandas as pd

from .recovery import recovery_time

GREEN = "ndvi"
GREEN_ALT = "evi"
FUNCTIONS = ("gpp_modelo", "lst_menos_aire")
PRECISION_DAYS = 32          # dos compuestos de 16 días
PERIOD_DAYS = {"ndvi": 16, "evi": 16, "gpp_modelo": 8, "lst_menos_aire": 8}
MIN_COVERAGE = 0.5            # fracción mínima de observaciones esperadas en la ventana de impacto
IMPACT_WINDOW_DAYS = 120
THRESHOLDS = (-1.5, -1.0, -0.5)
PERSISTS = (2, 3, 4)

CATEGORIES = ("consistente", "fantasma", "verdor_tarde", "caida_posterior", "estres_invisible", "solo_modelo",
              "censurada", "sin_recuperacion", "sin_impacto")


def _classify(rec: dict, collision: bool) -> str:
    """Categoría de integridad para un conjunto de recuperaciones (una combinación de supuestos)."""
    g = rec[GREEN]
    impacted = {k: r for k, r in rec.items() if r.impactado}
    if not impacted:
        return "sin_impacto"
    if collision and any(r.censurado for r in impacted.values()):
        return "censurada"
    funcs = [rec[f] for f in FUNCTIONS if f in rec and rec[f].impactado]
    if not g.impactado:
        # El verdor no cayó. Si la señal térmica (independiente del verdor) cayó, es estrés que el verdor no muestra.
        # Si solo cayó la GPP, puede ser el clima del reanálisis que usa el modelo MOD17, no la planta.
        if "lst_menos_aire" in rec and rec["lst_menos_aire"].impactado:
            return "estres_invisible"
        return "solo_modelo" if funcs else "sin_impacto"
    if g.censurado:
        return "verdor_tarde" if any(not f.censurado for f in funcs) else "sin_recuperacion"
    if not funcs:
        return "consistente"
    # Una función que toca fondo después de que el verdor ya volvió es otra caída, no una recuperación tardía
    same = [f for f in funcs if f.fecha_minimo is None or f.fecha_minimo <= g.fecha_recuperacion]
    if not same:
        return "caida_posterior"
    lags = []
    for f in same:
        if f.censurado:
            return "fantasma"  # el verdor volvió y la función no, dentro de la ventana
        lags.append((f.fecha_recuperacion - g.fecha_recuperacion).days)
    if any(l > PRECISION_DAYS for l in lags):
        return "fantasma"
    if any(l < -PRECISION_DAYS for l in lags):
        return "verdor_tarde"
    return "consistente"


def audit_recovery(signals: dict[str, pd.Series], event_start, event_end, stop, next_event_start=None) -> dict:
    """Audita un episodio en un punto.

    signals: z robustos por señal (negativo = peor), claves en {"ndvi", "evi", "gpp_modelo", "lst_menos_aire"}.
    stop: fin de la ventana (siguiente sequía, horizonte o fin de serie).
    next_event_start: inicio de la siguiente sequía si fue ella la que cortó la ventana.
    """
    event_start, event_end, stop = map(pd.Timestamp, (event_start, event_end, stop))
    collision = next_event_start is not None and pd.Timestamp(next_event_start) == stop

    primary = {k: recovery_time(z, event_start, event_end, stop) for k, z in signals.items()}
    category = _classify(primary, collision)

    # Calidad: fracción de observaciones esperadas que existen (y pasaron QC) en la ventana de impacto
    span = (event_end - event_start).days + IMPACT_WINDOW_DAYS
    qc = {k: r.n_validas_ventana for k, r in primary.items()}
    coverage = {k: n / max(1.0, span / PERIOD_DAYS.get(k, 16)) for k, n in qc.items()}
    qc_ok = all(coverage[k] >= MIN_COVERAGE for k in (GREEN, *FUNCTIONS) if k in coverage)

    # Sensibilidad: misma auditoría con 3 umbrales × 3 persistencias × {NDVI, EVI} como verdor
    combos = []
    for thr, per, green in product(THRESHOLDS, PERSISTS, (GREEN, GREEN_ALT)):
        sig = dict(signals)
        if green == GREEN_ALT and GREEN_ALT in signals:
            sig[GREEN] = signals[GREEN_ALT]
        rec = {k: recovery_time(z, event_start, event_end, stop, thr, per) for k, z in sig.items()}
        combos.append(_classify(rec, collision))
    stability = sum(c == category for c in combos) / len(combos)

    reason = None
    if category not in ("sin_impacto", "censurada") and not qc_ok:
        verdict, reason = "inconclusa", "calidad"
    elif category not in ("sin_impacto", "censurada") and stability < 0.6:
        verdict, reason = "inconclusa", "definicion"
    else:
        verdict = category

    def days(r):
        return None if r.fecha_recuperacion is None else int((r.fecha_recuperacion - event_end).days)

    return {
        "categoria_principal": category,
        "veredicto": verdict,
        "motivo_inconclusa": reason,
        "colision": bool(collision and category == "censurada"),
        "estabilidad": round(stability, 3),
        "combinaciones": len(combos),
        "categorias_combinaciones": {c: combos.count(c) for c in sorted(set(combos))},
        "calidad_ok": qc_ok,
        **{f"{k}_impactado": r.impactado for k, r in primary.items()},
        **{f"{k}_recupera": None if r.fecha_recuperacion is None else r.fecha_recuperacion.strftime("%Y-%m-%d")
           for k, r in primary.items()},
        **{f"{k}_dias": days(r) for k, r in primary.items()},
        **{f"{k}_censurado": r.censurado for k, r in primary.items()},
        **{f"{k}_n": n for k, n in qc.items()},
        **{f"{k}_cobertura": round(min(1.0, c), 2) for k, c in coverage.items()},
    }
