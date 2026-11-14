"""Un día extremo dentro de la distribución diaria 2001-2024 de su celda.

Un solo evento no es una tendencia. Y una celda de reanálisis de 0.5° × 0.625° (unos 55 × 66 km)
promedia la lluvia sobre toda la celda: un aguacero convectivo de pocas horas sobre una ciudad
queda muy suavizado. Lo que sí se puede decir: qué tan raro fue ese día PARA EL REANÁLISIS.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats as sstats


def event_in_distribution(daily: pd.Series, day: str, window_days: int = 3) -> dict:
    daily = daily.dropna()
    day = pd.Timestamp(day)
    v = float(daily.get(day, np.nan))
    roll = daily.rolling(window_days, min_periods=window_days).sum()
    # suma de 3 días centrada en el día del evento
    v3 = float(roll.get(day + pd.Timedelta(days=window_days // 2), np.nan))
    amax = daily.groupby(daily.index.year).max()
    amax3 = roll.groupby(roll.index.year).max()
    n_days = int(daily.size)
    rank_all = int((daily > v).sum()) + 1
    rank_amax = int((amax > v).sum()) + 1
    out = {
        "fecha": day.date().isoformat(), "valor_mm": v, "suma_3_dias_mm": v3,
        "n_dias": n_days, "puesto_entre_todos_los_dias": rank_all,
        "percentil_entre_todos_los_dias": float(100 * (daily < v).mean()),
        "n_anios": int(amax.size), "puesto_entre_maximos_anuales": rank_amax,
        "periodo_retorno_empirico_anios": float((amax.size + 1) / rank_amax),  # posición de Weibull
        "puesto_3dias_entre_maximos_anuales": int((amax3 > v3).sum()) + 1,
        "maximo_anual_mediana_mm": float(amax.median()),
        "maximo_registro_mm": float(daily.max()), "fecha_maximo_registro": daily.idxmax().date().isoformat(),
        "maximos_anuales": {int(k): float(x) for k, x in amax.items()},
        "maximos_anuales_3dias": {int(k): float(x) for k, x in amax3.items()},
    }
    # GEV sobre 24 máximos anuales: solo orientativo, la cola está muy mal restringida
    try:
        c, loc, scale = sstats.genextreme.fit(amax.to_numpy())
        p_exc = float(sstats.genextreme.sf(v, c, loc, scale))
        out["gev"] = {"forma_c": float(c), "loc": float(loc), "escala": float(scale),
                      "periodo_retorno_anios": float(1 / p_exc) if p_exc > 0 else None,
                      "nota": "24 máximos anuales: estimación muy incierta; no se usa para conclusiones"}
    except Exception as e:  # noqa: BLE001
        out["gev"] = {"error": str(e)}
    return out
