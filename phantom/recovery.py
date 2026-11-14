"""Tiempo de recuperación de cada señal tras una sequía, y la brecha entre señales.

Señal "se ve": NDVI o EVI.  Señal "funciona": GPP (modelo) o LST menos temperatura del aire.
Todas se convierten en anomalía estandarizada robusta por época del año, orientada para que
valores negativos = peor de lo normal.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

MIN_YEARS_PER_BIN = 8


def robust_seasonal_z(dates: pd.Series, values: pd.Series, period_days: int, invert: bool = False) -> pd.Series:
    """Anomalía robusta: (x - mediana del bin) / (1.4826 * MAD del bin). Bin = época del año.

    invert=True cuando un valor alto es peor (p. ej. dosel más caliente que el aire).
    """
    dates = pd.to_datetime(pd.Series(dates).reset_index(drop=True))
    v = pd.Series(values).reset_index(drop=True).astype(float)
    bins = (dates.dt.day_of_year - 1) // period_days
    med = v.groupby(bins).transform("median")
    mad = v.groupby(bins).transform(lambda x: np.nanmedian(np.abs(x - np.nanmedian(x))))
    count = v.groupby(bins).transform("count")
    scale = 1.4826 * mad
    z = (v - med) / scale.replace(0, np.nan)
    z = z.where(count >= MIN_YEARS_PER_BIN)
    if invert:
        z = -z
    return pd.Series(z.to_numpy(), index=pd.DatetimeIndex(dates))


@dataclass
class Recovery:
    impactado: bool
    fecha_minimo: pd.Timestamp | None
    z_minimo: float | None
    fecha_recuperacion: pd.Timestamp | None
    censurado: bool
    n_validas_ventana: int

    def dias_desde(self, ref: pd.Timestamp) -> float | None:
        if self.fecha_recuperacion is None:
            return None
        return float((self.fecha_recuperacion - ref).days)


def _first_run(mask: np.ndarray, length: int) -> int | None:
    for i in range(len(mask) - length + 1):
        if mask[i:i + length].all():
            return i
    return None


def recovery_time(z: pd.Series, event_start, event_end, stop_date, threshold: float = -1.0,
                  persist: int = 3, impact_window_days: int = 120, impact_threshold: float = -1.5,
                  smooth: int = 3) -> Recovery:
    """Impacto = `persist` observaciones válidas seguidas con z < min(impact_threshold, threshold)
    dentro de [inicio, fin + ventana]. Una sola observación baja es ruido, no impacto.

    Antes de todo, z se suaviza con una mediana móvil de `smooth` observaciones válidas.

    Recuperación = primera fecha, después del inicio del impacto, en que z >= threshold durante
    `persist` observaciones válidas seguidas, antes de `stop_date`.

    - Sin impacto: no hay caída sostenida en la ventana.
    - Censurado: hubo impacto pero no hay recuperación antes de stop_date (siguiente sequía,
      fin de la serie o límite de horizonte).
    """
    event_start, event_end, stop_date = map(pd.Timestamp, (event_start, event_end, stop_date))
    z = z.dropna().sort_index()
    if smooth > 1:  # mediana móvil centrada sobre observaciones válidas: quita picos sueltos
        z = z.rolling(smooth, center=True, min_periods=1).median()
    win = z[(z.index >= event_start) & (z.index <= event_end + pd.Timedelta(days=impact_window_days))]
    n_win = int(win.size)
    if n_win == 0:
        return Recovery(False, None, None, None, True, 0)
    t_min = win.idxmin()
    z_min = float(win.min())
    i_imp = _first_run((win < min(impact_threshold, threshold)).to_numpy(), persist)
    if i_imp is None:
        return Recovery(False, t_min, z_min, None, False, n_win)
    t_imp = win.index[i_imp]
    after = z[(z.index > t_imp) & (z.index < stop_date)]
    i_rec = _first_run((after >= threshold).to_numpy(), persist)
    if i_rec is not None:
        return Recovery(True, t_min, z_min, after.index[i_rec], False, n_win)
    return Recovery(True, t_min, z_min, None, True, n_win)


def gap_status(green: Recovery, func: Recovery) -> str:
    if not green.impactado and not func.impactado:
        return "sin_impacto"
    if not green.impactado:
        return "sin_impacto_verde"
    if not func.impactado:
        return "sin_impacto_funcion"
    if green.censurado and func.censurado:
        return "ambos_censurados"
    if green.censurado:
        return "verde_censurado"
    if func.censurado:
        return "funcion_censurada"
    return "ambos_recuperados"


def event_gap(green_z: pd.Series, func_z: pd.Series, event_start, event_end, stop_date,
              threshold: float = -1.0, persist: int = 3) -> dict:
    """Δt = t_funcion - t_verde (días). Positivo: la función se recupera después del verdor."""
    g = recovery_time(green_z, event_start, event_end, stop_date, threshold, persist)
    f = recovery_time(func_z, event_start, event_end, stop_date, threshold, persist)
    status = gap_status(g, f)
    dt = None
    if status == "ambos_recuperados":
        dt = float((f.fecha_recuperacion - g.fecha_recuperacion).days)
    elif status == "funcion_censurada" and g.fecha_recuperacion is not None:
        dt = float((pd.Timestamp(stop_date) - g.fecha_recuperacion).days)  # cota inferior
    return {
        "estado": status,
        "dt_dias": dt,
        "dt_es_cota_inferior": status == "funcion_censurada",
        "verde_recuperacion": g.fecha_recuperacion,
        "funcion_recuperacion": f.fecha_recuperacion,
        "verde_minimo": g.fecha_minimo,
        "funcion_minimo": f.fecha_minimo,
        "verde_z_min": g.z_minimo,
        "funcion_z_min": f.z_minimo,
        "verde_dias_desde_fin": g.dias_desde(pd.Timestamp(event_end)),
        "funcion_dias_desde_fin": f.dias_desde(pd.Timestamp(event_end)),
        "n_validas_verde": g.n_validas_ventana,
        "n_validas_funcion": f.n_validas_ventana,
    }


def sensitivity(green_by_name: dict[str, pd.Series], func_z: pd.Series, event_start, event_end, stop_date,
                thresholds=(-1.5, -1.0, -0.5), persists=(2, 3, 4)) -> pd.DataFrame:
    rows = []
    for gname, gz in green_by_name.items():
        for thr in thresholds:
            for p in persists:
                r = event_gap(gz, func_z, event_start, event_end, stop_date, thr, p)
                rows.append({"verde": gname, "umbral": thr, "persistencia": p, **r})
    return pd.DataFrame(rows)


def robustness_label(sens: pd.DataFrame, primary_dt: float | None, resolution_days: int = 32,
                     min_valid: int = 6, agreement: float = 0.8) -> dict:
    """ROBUSTO si >= 80 % de las combinaciones válidas tienen el mismo signo que la principal
    y la mediana |Δt| supera dos compuestos del producto más grueso (2 × 16 = 32 días)."""
    valid = sens.loc[sens["estado"] == "ambos_recuperados", "dt_dias"].dropna()
    n = int(valid.size)
    if primary_dt is None or n < min_valid:
        return {"etiqueta": "SIN DATOS SUFICIENTES", "n_validas": n, "acuerdo_signo": None,
                "dt_mediana": float(valid.median()) if n else None,
                "dt_p10": None, "dt_p90": None}
    sign = np.sign(primary_dt)
    agree = float((np.sign(valid) == sign).mean()) if sign != 0 else float((valid.abs() <= resolution_days).mean())
    med = float(valid.median())
    robust = agree >= agreement and abs(med) > resolution_days
    return {
        "etiqueta": "ROBUSTO" if robust else "SENSIBLE A SUPUESTOS",
        "n_validas": n,
        "acuerdo_signo": agree,
        "dt_mediana": med,
        "dt_p10": float(valid.quantile(0.1)),
        "dt_p90": float(valid.quantile(0.9)),
    }
