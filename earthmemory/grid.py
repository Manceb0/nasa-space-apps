"""Rejillas regulares (IMERG 0.1°, GLDAS 0.25°), fracciones de celda por país y provincia, y
remapeo conservativo IMERG → GLDAS.

- Fracción de una celda dentro de un polígono: n × n puntos dentro de la celda, ponderados por cos(lat).
- Área de la celda: R² · Δλ · (sin φ2 − sin φ1), R = 6371.0 km.
- Serie de provincia = Σ_c w_pc · x_c / Σ_c w_pc con w_pc = área_c · fracción_de_c_en_p (solo celdas
  con dato ese mes). Es la media ponderada por área de la provincia, sin interpolar nada.
- Remapeo conservativo: la lluvia de una celda GLDAS es la media de las celdas IMERG que la tocan,
  ponderada por el área de solape × la fracción de tierra del país de cada celda IMERG
  (= lluvia sobre la parte del país de la celda). 0.25 no es múltiplo de 0.1: los solapes son exactos.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from matplotlib.path import Path as MplPath

R_EARTH = 6371.0


@dataclass
class Grid:
    name: str
    res: float
    lat: np.ndarray   # centros, ascendente
    lon: np.ndarray   # centros, ascendente

    @property
    def n(self) -> int:
        return self.lat.size * self.lon.size

    def mesh(self) -> tuple[np.ndarray, np.ndarray]:
        LO, LA = np.meshgrid(self.lon, self.lat)
        return LA.ravel(), LO.ravel()

    def ids(self) -> list[str]:
        la, lo = self.mesh()
        return [cell_id(a, b) for a, b in zip(la, lo)]

    def lat_edges(self) -> np.ndarray:
        return np.round(np.concatenate([self.lat - self.res / 2, [self.lat[-1] + self.res / 2]]), 6)

    def lon_edges(self) -> np.ndarray:
        return np.round(np.concatenate([self.lon - self.res / 2, [self.lon[-1] + self.res / 2]]), 6)


def cell_id(lat: float, lon: float) -> str:
    return f"{lat:.3f}_{lon:.3f}"


def cell_area_km2(lat: np.ndarray, res: float) -> np.ndarray:
    lat = np.asarray(lat, float)
    return (R_EARTH ** 2 * np.radians(res)
            * (np.sin(np.radians(lat + res / 2)) - np.sin(np.radians(lat - res / 2))))


def _sample_points(grid: Grid, n: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    la, lo = grid.mesh()
    off = (np.arange(n) + 0.5) / n - 0.5
    OL, OA = np.meshgrid(off * grid.res, off * grid.res)
    plat = (la[:, None] + OA.ravel()[None, :]).ravel()
    plon = (lo[:, None] + OL.ravel()[None, :]).ravel()
    cell = np.repeat(np.arange(la.size), n * n)
    return plat, plon, cell


def _inside(polys: list, plon: np.ndarray, plat: np.ndarray) -> np.ndarray:
    res = np.zeros(plon.size, bool)
    for ext, holes in polys:
        x0, y0 = ext.min(axis=0)
        x1, y1 = ext.max(axis=0)
        sel = (plon >= x0) & (plon <= x1) & (plat >= y0) & (plat <= y1)
        if not sel.any():
            continue
        pts = np.column_stack([plon[sel], plat[sel]])
        m = MplPath(ext).contains_points(pts)
        for h in holes:
            m &= ~MplPath(h).contains_points(pts)
        res[np.flatnonzero(sel)[m]] = True
    return res


def fractions(grid: Grid, units: list, others: dict, n: int = 12) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Devuelve (tabla de celdas, pesos celda × provincia).
    units: lista de boundaries.Unit (provincias del país); others: {iso3: polígonos} de países vecinos."""
    plat, plon, cell = _sample_points(grid, n)
    w = np.cos(np.radians(plat))
    wsum = np.bincount(cell, weights=w, minlength=grid.n)
    owner = np.full(plat.size, -1)
    for k, u in enumerate(units):
        m = _inside(u.polygons, plon, plat) & (owner < 0)
        owner[m] = k
    la, lo = grid.mesh()
    ids = grid.ids()
    rows = []
    for k, u in enumerate(units):
        f = np.bincount(cell[owner == k], weights=w[owner == k], minlength=grid.n) / wsum
        for c in np.flatnonzero(f > 0):
            rows.append({"celda": ids[c], "provincia": u.name, "codigo": u.code, "fraccion": round(float(f[c]), 5)})
    weights = pd.DataFrame(rows)
    fpais = np.bincount(cell[owner >= 0], weights=w[owner >= 0], minlength=grid.n) / wsum
    fo_best, fo_name, fo_total = np.zeros(grid.n), [None] * grid.n, np.zeros(grid.n)
    for a3, polys in sorted(others.items()):
        m = _inside(polys, plon, plat) & (owner < 0)
        f = np.bincount(cell[m], weights=w[m], minlength=grid.n) / wsum
        fo_total += f
        better = f > fo_best
        fo_best = np.where(better, f, fo_best)
        for c in np.flatnonzero(better):
            fo_name[c] = a3
    area = cell_area_km2(la, grid.res)
    cells = pd.DataFrame({"celda": ids, "lat": la, "lon": lo, "area_km2": np.round(area, 3),
                          "frac_pais": np.round(fpais, 5), "frac_otro_pais": np.round(fo_best, 5),
                          "otro_pais": fo_name, "frac_mar": np.round(np.clip(1 - fpais - fo_total, 0, 1), 5)})
    if len(weights):
        main = (weights.sort_values(["celda", "fraccion"], ascending=[True, False]).drop_duplicates("celda")
                .set_index("celda"))
        cells["provincia_principal"] = cells["celda"].map(main["provincia"])
    else:
        cells["provincia_principal"] = None
    return cells, weights


def include_mask(cells: pd.DataFrame, min_frac: float = 0.25) -> pd.Series:
    return (cells["frac_pais"] >= min_frac) & (cells["frac_pais"] >= cells["frac_otro_pais"])


def remap_weights(fine: Grid, coarse: Grid, fine_land: np.ndarray) -> pd.DataFrame:
    """Pesos de solape fino → grueso: (celda_gruesa, celda_fina, peso), peso = área de solape × tierra_fina.
    fine_land: fracción del país de cada celda fina (en el orden de fine.ids())."""
    fl = fine.lat_edges()
    fo = fine.lon_edges()
    cl = coarse.lat_edges()
    co = coarse.lon_edges()
    fid = np.array(fine.ids()).reshape(fine.lat.size, fine.lon.size)
    cid = np.array(coarse.ids()).reshape(coarse.lat.size, coarse.lon.size)
    land = np.asarray(fine_land, float).reshape(fine.lat.size, fine.lon.size)
    rows = []
    for a in range(coarse.lat.size):
        for b in range(coarse.lon.size):
            for i in range(fine.lat.size):
                dlat0, dlat1 = max(cl[a], fl[i]), min(cl[a + 1], fl[i + 1])
                if dlat1 <= dlat0:
                    continue
                band = np.sin(np.radians(dlat1)) - np.sin(np.radians(dlat0))
                for j in range(fine.lon.size):
                    dlo = min(co[b + 1], fo[j + 1]) - max(co[b], fo[j])
                    if dlo <= 0 or land[i, j] <= 0:
                        continue
                    rows.append((cid[a, b], fid[i, j], R_EARTH ** 2 * np.radians(dlo) * band * land[i, j]))
    return pd.DataFrame(rows, columns=["celda_gruesa", "celda_fina", "peso"])


def apply_weights(df: pd.DataFrame, w: pd.DataFrame, src: str, dst: str) -> pd.DataFrame:
    """Media ponderada de columnas de df (tiempo × celda_src) hacia celdas dst, ignorando NaN mes a mes."""
    out = {}
    X = df.to_numpy(float)
    col = {c: k for k, c in enumerate(df.columns)}
    for d, g in w.groupby(dst):
        idx = np.array([col[c] for c in g[src] if c in col])
        ww = g.loc[g[src].isin(col), "peso"].to_numpy(float)
        if idx.size == 0:
            continue
        v = X[:, idx]
        m = np.isfinite(v)
        num = np.where(m, v, 0) @ ww
        den = m.astype(float) @ ww
        out[d] = np.where(den > 0, num / np.where(den > 0, den, 1), np.nan)
    return pd.DataFrame(out, index=df.index)[sorted(out)]


def province_weights(weights: pd.DataFrame, cells: pd.DataFrame) -> pd.DataFrame:
    a = cells.set_index("celda")["area_km2"]
    w = weights.copy()
    w["peso"] = w["fraccion"] * w["celda"].map(a)
    return w


def province_series(df: pd.DataFrame, pw: pd.DataFrame) -> pd.DataFrame:
    return apply_weights(df, pw.rename(columns={"celda": "src", "provincia": "dst"}), "src", "dst")
