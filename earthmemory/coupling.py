"""Acople lluvia → respuesta y memoria del terreno, con bootstrap por bloques móviles.

Métricas por celda y respuesta (respuesta = z mensual de GWETROOT, GWETTOP, EVLAND o T2M):
- r_spi: correlación entre SPI-k(t) y z(t + lag). Acople: cuánto sigue la respuesta a la lluvia.
- phi y gamma del modelo ARX  z(t) = c + phi·z(t−1) + gamma·SPI-1(t) + e:
    phi   = memoria: qué parte de la anomalía del mes anterior sigue presente, descontando la lluvia nueva;
    gamma = sensibilidad inmediata a la anomalía de lluvia del mes.
  (respuesta de equilibrio a una anomalía sostenida = gamma / (1 − phi)).
- Estado antecedente: gamma estimada solo en meses con z(t−1) en el tercil seco y en el tercil húmedo;
  delta_gamma = gamma_seco − gamma_humedo, y el término de interacción SPI-1(t)·z(t−1).

Bootstrap: bloques móviles de 12 meses (Künsch 1989) con LOS MISMOS índices para todas las celdas.
Así, la diferencia entre dos celdas se evalúa respetando la autocorrelación temporal y la
correlación entre celdas (mismo mes en las dos). p = 2·(1 − Φ(|Δ| / EE_bootstrap)).
"""

from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np
import pandas as pd
from scipy import stats as sstats

RESPONSES = ["GWETROOT", "GWETTOP", "EVLAND", "T2M"]
METRICS = ["r_spi", "phi", "gamma"]


@dataclass(frozen=True)
class Settings:
    z_kind: str = "robusta"
    spi_r: int = 3
    lag_r: int = 0
    spi_arx: int = 1
    block: int = 12
    period: tuple | None = None
    corr: str = "pearson"
    B: int = 2000
    seed: int = 2026

    def label(self) -> str:
        base = Settings()
        diffs = [f"{k}={v}" for k, v in self.__dict__.items() if v != getattr(base, k) and k not in ("B", "seed")]
        return ", ".join(diffs) if diffs else "principal"

    def but(self, **kw) -> "Settings":
        return replace(self, **kw)


def block_indices(n: int, block: int, B: int, seed: int) -> np.ndarray:
    """Índices de bootstrap por bloques móviles: matriz B × n."""
    rng = np.random.default_rng(seed)
    nb = int(np.ceil(n / block))
    starts = rng.integers(0, n - block + 1, size=(B, nb))
    idx = (starts[:, :, None] + np.arange(block)[None, None, :]).reshape(B, nb * block)
    return idx[:, :n]


def build_rows(z: dict, spi_r: pd.DataFrame, spi_arx: pd.DataFrame, cells: list, responses: list,
               lag: int = 0, period: tuple | None = None) -> tuple[pd.DatetimeIndex, dict]:
    """Tabla alineada por mes t, con meses válidos en TODAS las celdas y respuestas (índice común)."""
    rows, valid = {}, None
    for c in cells:
        for r in responses:
            y = z[r][c]
            d = pd.DataFrame({"s_r": spi_r[c], "y_lead": y.shift(-lag), "y": y, "y_lag1": y.shift(1),
                              "s_arx": spi_arx[c]})
            rows[(c, r)] = d
            v = d.notna().all(axis=1)
            valid = v if valid is None else (valid & v)
    if period is not None:
        yrs = valid.index.year
        valid &= (yrs >= period[0]) & (yrs <= period[1])
    dates = valid.index[valid.to_numpy()]
    return dates, {k: {col: d.loc[dates, col].to_numpy(float) for col in d.columns} for k, d in rows.items()}


def corr_rows(X: np.ndarray, Y: np.ndarray, kind: str = "pearson") -> np.ndarray:
    if kind == "spearman":
        X = sstats.rankdata(X, axis=-1)
        Y = sstats.rankdata(Y, axis=-1)
    X = X - X.mean(axis=-1, keepdims=True)
    Y = Y - Y.mean(axis=-1, keepdims=True)
    return (X * Y).sum(-1) / np.sqrt((X ** 2).sum(-1) * (Y ** 2).sum(-1))


def ols_rows(cols: list[np.ndarray], y: np.ndarray, w: np.ndarray | None = None) -> np.ndarray:
    """OLS por fila (bootstrap) con intercepto. cols: lista de matrices B × n. Devuelve B × (1+k)."""
    X = np.stack([np.ones_like(y)] + cols, axis=-1)  # B × n × p
    if w is None:
        w = np.ones_like(y)
    XtX = np.einsum("bni,bn,bnj->bij", X, w, X)
    Xty = np.einsum("bni,bn,bn->bi", X, w, y)
    p = X.shape[-1]
    XtX = XtX + 1e-9 * np.eye(p)[None]
    return np.linalg.solve(XtX, Xty[..., None])[..., 0]


def metrics_for(d: dict, idx: np.ndarray, corr: str = "pearson") -> dict:
    """Métricas de una celda-respuesta para cada fila de índices (idx: B × n)."""
    s_r, y_lead = d["s_r"][idx], d["y_lead"][idx]
    y, ylag, s = d["y"][idx], d["y_lag1"][idx], d["s_arx"][idx]
    beta = ols_rows([ylag, s], y)
    return {"r_spi": corr_rows(s_r, y_lead, corr), "phi": beta[:, 1], "gamma": beta[:, 2]}


def antecedent_for(d: dict, idx: np.ndarray, lo: float, hi: float) -> dict:
    """gamma en tercil seco vs húmedo de z(t−1) (umbrales fijos de la muestra completa) e interacción."""
    y, ylag, s = d["y"][idx], d["y_lag1"][idx], d["s_arx"][idx]
    g_dry = ols_rows([ylag, s], y, w=(ylag <= lo).astype(float))[:, 2]
    g_wet = ols_rows([ylag, s], y, w=(ylag >= hi).astype(float))[:, 2]
    inter = ols_rows([ylag, s, s * ylag], y)[:, 3]
    return {"gamma_seco": g_dry, "gamma_humedo": g_wet, "delta_gamma": g_dry - g_wet, "interaccion": inter}


@dataclass
class CellMetrics:
    settings: Settings
    dates: pd.DatetimeIndex
    point: pd.DataFrame          # celda, respuesta, metrica, valor, ic95_bajo, ic95_alto, ee
    boot: dict                   # (celda, respuesta, metrica) → B valores


def compute(z: dict, spi_tables: dict, cells: list, responses: list, st: Settings) -> CellMetrics:
    dates, rows = build_rows(z, spi_tables[st.spi_r], spi_tables[st.spi_arx], cells, responses, st.lag_r, st.period)
    n = len(dates)
    idx = block_indices(n, st.block, st.B, st.seed)
    full = np.arange(n)[None, :]
    recs, boot = [], {}
    for (c, r), d in rows.items():
        pt = metrics_for(d, full, st.corr)
        bt = metrics_for(d, idx, st.corr)
        for m in METRICS:
            b = bt[m]
            boot[(c, r, m)] = b
            recs.append({"celda": c, "respuesta": r, "metrica": m, "valor": float(pt[m][0]),
                         "ic95_bajo": float(np.percentile(b, 2.5)), "ic95_alto": float(np.percentile(b, 97.5)),
                         "ee_boot": float(b.std(ddof=1)), "n_meses": n})
    return CellMetrics(st, dates, pd.DataFrame(recs), boot)


def antecedent_table(z: dict, spi_tables: dict, cells: list, responses: list, st: Settings) -> pd.DataFrame:
    dates, rows = build_rows(z, spi_tables[st.spi_r], spi_tables[st.spi_arx], cells, responses, st.lag_r, st.period)
    n = len(dates)
    idx = block_indices(n, st.block, st.B, st.seed + 1)
    full = np.arange(n)[None, :]
    recs = []
    for (c, r), d in rows.items():
        lo, hi = np.quantile(d["y_lag1"], [1 / 3, 2 / 3])
        pt = antecedent_for(d, full, lo, hi)
        bt = antecedent_for(d, idx, lo, hi)
        rec = {"celda": c, "respuesta": r, "n_meses": n, "umbral_tercil_seco": float(lo),
               "umbral_tercil_humedo": float(hi)}
        for k in ("gamma_seco", "gamma_humedo", "delta_gamma", "interaccion"):
            b = bt[k]
            rec[k] = float(pt[k][0])
            rec[f"{k}_ic95"] = [float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5))]
        se = float(bt["delta_gamma"].std(ddof=1))
        rec["p_delta_gamma"] = float(2 * (1 - sstats.norm.cdf(abs(rec["delta_gamma"]) / se))) if se > 0 else None
        recs.append(rec)
    return pd.DataFrame(recs)


def lag_profile(z: dict, spi3: pd.DataFrame, cells: list, responses: list, max_lag: int = 6) -> pd.DataFrame:
    """r(SPI-3(t), z(t+L)) para L = 0..max_lag y el lag de |r| máximo (descriptivo, sin prueba)."""
    recs = []
    for c in cells:
        for r in responses:
            rs = []
            for L in range(max_lag + 1):
                d = pd.DataFrame({"x": spi3[c], "y": z[r][c].shift(-L)}).dropna()
                rs.append(float(np.corrcoef(d["x"], d["y"])[0, 1]))
            k = int(np.argmax(np.abs(rs)))
            recs.append({"celda": c, "respuesta": r, **{f"r_lag{L}": v for L, v in enumerate(rs)},
                         "lag_max_meses": k, "r_max": rs[k]})
    return pd.DataFrame(recs)


def p_from_boot(delta: float, b: np.ndarray) -> float | None:
    se = float(np.std(b, ddof=1))
    if not np.isfinite(se) or se == 0:
        return None
    return float(2 * (1 - sstats.norm.cdf(abs(delta) / se)))
