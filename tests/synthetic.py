"""Generadores de DATOS SINTÉTICOS solo para pruebas. Nada de esto se usa en results/ ni en figures/."""

from __future__ import annotations

import numpy as np
import pandas as pd

SYNTHETIC = "DATOS SINTETICOS DE PRUEBA"


def composite_dates(period_days: int, start="2001-01-01", end="2024-12-31") -> pd.DatetimeIndex:
    dates = []
    for y in range(pd.Timestamp(start).year, pd.Timestamp(end).year + 1):
        d = pd.Timestamp(f"{y}-01-01")
        while d.year == y:
            dates.append(d)
            d += pd.Timedelta(days=period_days)
    return pd.DatetimeIndex(dates)


def signal(period_days: int, dips: list[tuple[str, str, float]], noise=0.01, base=0.6, amp=0.15,
           seed=1, missing_frac=0.0) -> pd.Series:
    """Ciclo estacional + ruido + caídas [(inicio, fin_de_caida, profundidad)] (valor bajo hasta fin_de_caida)."""
    rng = np.random.default_rng(seed)
    d = composite_dates(period_days)
    v = base + amp * np.sin(2 * np.pi * d.day_of_year / 365.25) + rng.normal(0, noise, d.size)
    s = pd.Series(v, index=d, name=SYNTHETIC)
    for a, b, depth in dips:
        s[(s.index >= a) & (s.index < b)] -= depth
    if missing_frac:
        drop = rng.random(d.size) < missing_frac
        s[drop] = np.nan
    return s
