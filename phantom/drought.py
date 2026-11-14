"""Catálogo de sequías a partir de series mensuales (IMERG, GLDAS).

Tres criterios, del más simple al más estándar:
- p20: meses bajo el percentil 20 de su mismo mes calendario (exploratorio, viene de sequias.py).
- anomalía: valor menos la media del mismo mes calendario.
- SPI-3 y SPI-6: índice estandarizado de precipitación (ajuste gamma por mes calendario con
  probabilidad de cero). Con 24 años el ajuste es frágil; se documenta en METHODOLOGY.md.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats


def monthly_climatology(s: pd.Series) -> pd.DataFrame:
    g = s.groupby(s.index.month)
    return pd.DataFrame({"media": g.mean(), "mediana": g.median(), "p20": g.quantile(0.2), "std": g.std()})


def monthly_anomaly(s: pd.Series) -> pd.Series:
    clim = s.groupby(s.index.month).transform("mean")
    return (s - clim).rename(f"anom_{s.name}")


def standardized_anomaly(s: pd.Series) -> pd.Series:
    g = s.groupby(s.index.month)
    z = (s - g.transform("mean")) / g.transform("std")
    return z.rename(f"z_{s.name}")


def spi(precip: pd.Series, scale: int, min_positive: int = 10) -> pd.Series:
    """SPI con gamma de dos parámetros por mes calendario y masa de probabilidad en cero.

    Devuelve NaN en los meses sin suficientes acumulados positivos para ajustar.
    """
    acc = precip.rolling(scale, min_periods=scale).sum()
    out = pd.Series(np.nan, index=precip.index, name=f"spi{scale}")
    for m in range(1, 13):
        sel = acc[acc.index.month == m].dropna()
        if sel.empty:
            continue
        zero = sel <= 0
        q = float(zero.mean())
        pos = sel[~zero]
        if len(pos) < min_positive or pos.nunique() < 3:
            continue
        a, _, b = stats.gamma.fit(pos.to_numpy(), floc=0)
        cdf = q + (1 - q) * stats.gamma.cdf(sel.clip(lower=0).to_numpy(), a, loc=0, scale=b)
        cdf = np.where(zero.to_numpy(), q / 2 if q > 0 else 1e-6, cdf)
        cdf = np.clip(cdf, 1e-6, 1 - 1e-6)
        out.loc[sel.index] = stats.norm.ppf(cdf)
    return out


def runs_below(index: pd.Series, threshold: float, min_len: int = 2) -> pd.DataFrame:
    """Rachas de meses consecutivos con index <= threshold.

    Columnas: inicio, fin, duracion_meses, severidad (suma del índice), pico (mínimo),
    recuperacion_candidata (primer mes posterior con índice >= 0, o NaT si no ocurre).
    """
    below = (index <= threshold) & index.notna()
    rows = []
    run_start = None
    dates = index.index
    for i, (d, flag) in enumerate(zip(dates, below)):
        if flag and run_start is None:
            run_start = i
        if run_start is not None and (not flag or i == len(dates) - 1):
            last = i if flag else i - 1
            n = last - run_start + 1
            if n >= min_len:
                seg = index.iloc[run_start:last + 1]
                after = index.iloc[last + 1:]
                rec = after[after >= 0]
                rows.append({
                    "inicio": dates[run_start],
                    "fin": dates[last],
                    "duracion_meses": n,
                    "severidad": float(seg.sum()),
                    "pico": float(seg.min()),
                    "recuperacion_candidata": rec.index[0] if len(rec) else pd.NaT,
                })
            run_start = None
    return pd.DataFrame(rows, columns=["inicio", "fin", "duracion_meses", "severidad", "pico",
                                       "recuperacion_candidata"])


def p20_runs(s: pd.Series, min_len: int = 2) -> pd.DataFrame:
    """Criterio exploratorio original: meses bajo el p20 de su mes calendario."""
    p20 = s.groupby(s.index.month).transform(lambda x: x.quantile(0.2))
    flag = pd.Series(np.where(s < p20, -1.0, 0.0), index=s.index)
    return runs_below(flag, -1.0, min_len).drop(columns=["severidad", "pico"])


def overlaps(a: pd.DataFrame, b: pd.DataFrame) -> list[bool]:
    """Para cada racha de `a`, si se solapa en el tiempo con alguna racha de `b`."""
    res = []
    for _, r in a.iterrows():
        res.append(bool(((b["inicio"] <= r["fin"]) & (b["fin"] >= r["inicio"])).any()) if len(b) else False)
    return res


def drought_catalog(precip: pd.Series, soil: pd.Series | None, region: str,
                    spi_threshold: float = -1.0) -> pd.DataFrame:
    """Une SPI-3 y SPI-6 (lluvia) y la humedad del suelo estandarizada en un solo catálogo."""
    frames = []
    for scale in (3, 6):
        ev = runs_below(spi(precip, scale), spi_threshold, min_len=2)
        ev.insert(0, "criterio", f"SPI-{scale} <= {spi_threshold}")
        frames.append(ev)
    if soil is not None:
        ev = runs_below(standardized_anomaly(soil), spi_threshold, min_len=2)
        ev.insert(0, "criterio", f"humedad suelo z <= {spi_threshold}")
        frames.append(ev)
    cat = pd.concat(frames, ignore_index=True)
    cat.insert(0, "region", region)
    if soil is not None:
        soil_ev = frames[-1]
        rain_ev = pd.concat(frames[:2], ignore_index=True)
        cat["coincide_lluvia_y_suelo"] = [
            ov for ov in overlaps(cat, soil_ev)
        ]
        is_soil = cat["criterio"].str.startswith("humedad")
        cat.loc[is_soil, "coincide_lluvia_y_suelo"] = overlaps(cat[is_soil], rain_ev)
    return cat.sort_values(["inicio", "criterio"]).reset_index(drop=True)


def primary_events(precip: pd.Series, threshold: float = -1.0, scale: int = 3) -> pd.DataFrame:
    """Eventos que usa el análisis de recuperación: rachas SPI-3 <= -1 de 2+ meses."""
    return runs_below(spi(precip, scale), threshold, min_len=2)
