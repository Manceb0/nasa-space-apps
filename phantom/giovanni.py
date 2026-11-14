"""Lectura y validación de las series 'Time Series, Area-Averaged' exportadas de NASA Giovanni."""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass
class GiovanniSeries:
    path: Path
    meta: dict[str, str]
    variable: str
    values: pd.Series  # índice mensual (inicio de mes), valores en las unidades del CSV
    fill_value: float | None = None
    reconstructed: bool = False
    issues: list[str] = field(default_factory=list)


def read_giovanni_csv(path: str | Path) -> GiovanniSeries:
    path = Path(path)
    meta: dict[str, str] = {}
    rows: list[list[str]] = []
    header: list[str] | None = None
    with path.open(encoding="utf-8", newline="") as fh:
        for row in csv.reader(fh):
            if not row or not any(c.strip() for c in row):
                continue
            if header is None:
                if row[0].strip().lower() == "time":
                    header = [c.strip() for c in row]
                    continue
                key = row[0].strip().rstrip(":")
                meta[key] = ",".join(c.strip() for c in row[1:])
            else:
                rows.append(row)
    if header is None or len(header) < 2:
        raise ValueError(f"{path.name}: no encontré la fila de encabezado 'time,...'")

    variable = header[1]
    fill = None
    for k, v in meta.items():
        if k.lower().startswith("fill value"):
            try:
                fill = float(v)
            except ValueError:
                pass

    dates = pd.to_datetime([r[0].strip() for r in rows])
    vals = pd.to_numeric(pd.Series([r[1].strip() for r in rows]), errors="coerce").to_numpy(dtype=float)
    if fill is not None:
        vals = np.where(np.isclose(vals, fill), np.nan, vals)
    series = pd.Series(vals, index=pd.DatetimeIndex(dates, name="time"), name=variable)
    reconstructed = any(k.lower() == "note" and "reconstruido" in v.lower() for k, v in meta.items())
    return GiovanniSeries(path=path, meta=meta, variable=variable, values=series,
                          fill_value=fill, reconstructed=reconstructed)


def validate_monthly(gs: GiovanniSeries, start: str = "2001-01-01", end: str = "2024-12-01") -> dict:
    """Comprueba fechas mensuales únicas, ordenadas y completas, y valores faltantes."""
    s = gs.values
    expected = pd.date_range(start, end, freq="MS")
    issues = []
    if not s.index.is_monotonic_increasing:
        issues.append("fechas fuera de orden")
    if s.index.has_duplicates:
        issues.append(f"{int(s.index.duplicated().sum())} fechas duplicadas")
    missing_dates = expected.difference(s.index)
    extra_dates = s.index.difference(expected)
    if len(missing_dates):
        issues.append(f"faltan {len(missing_dates)} meses")
    if len(extra_dates):
        issues.append(f"{len(extra_dates)} fechas fuera del rango esperado")
    n_nan = int(s.isna().sum())
    if n_nan:
        issues.append(f"{n_nan} valores faltantes o de relleno")
    gs.issues = issues
    return {
        "archivo": gs.path.name,
        "variable": gs.variable,
        "n_fechas": int(len(s)),
        "n_unicas": int(s.index.nunique()),
        "inicio": str(s.index.min().date()) if len(s) else None,
        "fin": str(s.index.max().date()) if len(s) else None,
        "faltantes": n_nan,
        "min": float(np.nanmin(s.values)) if len(s) else None,
        "max": float(np.nanmax(s.values)) if len(s) else None,
        "caja_usuario": gs.meta.get("User Bounding Box"),
        "caja_datos": gs.meta.get("Data Bounding Box"),
        "url_reproducir": gs.meta.get("URL to Reproduce Results"),
        "reconstruido": gs.reconstructed,
        "ok": not issues,
        "problemas": issues,
    }


def load_folder(folder: str | Path) -> dict[str, GiovanniSeries]:
    """Carga los CSV de Giovanni de una carpeta. Clave = nombre del archivo sin extensión.

    Ignora las copias '*.giovanni_original.csv' (se usan solo para verificar integridad).
    """
    out = {}
    for p in sorted(Path(folder).glob("*.csv")):
        if p.name.endswith(".giovanni_original.csv"):
            continue
        out[p.stem] = read_giovanni_csv(p)
    return out
