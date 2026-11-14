"""Episodios de sequía por celda, contradicciones lluvia/suelo y factores explicativos.

Episodio = racha de SPI-3 <= −1 durante 2+ meses (mismo criterio que PHANTOM).
- Retorno de la lluvia: primer mes después del fin con SPI-3 >= umbral_retorno (0 principal; −0.5 sensibilidad).
- Contradicción A ("la lluvia volvió, el suelo no"): z < −1 en el mes de retorno y en los k−1 meses
  siguientes (k = 2 principal; 3 sensibilidad).
- Contradicción B1 ("suelo seco sin sequía de lluvia"): k+ meses seguidos con z < −1 y SPI-3 >= 0.
- Contradicción B2 ("suelo normal durante sequía de lluvia"): k+ meses seguidos con z >= 0 y SPI-3 <= −1.
- Meses de recuperación: desde el fin del episodio hasta el primer mes con z >= −0.5 dos meses seguidos;
  censurado si antes empieza el siguiente episodio o termina la serie.

Factores (los que pidió el equipo; asociación, nunca causa):
(a) intensidad de la lluvia de retorno, con datos diarios POWER: fracción de la lluvia de la ventana
    [fin+1 mes, retorno+2 meses] caída en días por encima del percentil 95 de los días con lluvia
    (>= 1 mm) de esa celda, y lluvia máxima en 1 día en esa ventana;
(b) sequías previas: meses con SPI-3 <= −1 en los 12 meses antes del inicio;
(c) estado antecedente: z de la misma respuesta en el mes anterior al inicio.
Control: severidad del episodio (suma de SPI-3 en la racha).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats as sstats

from phantom import drought, stats

FACTORS = ["fraccion_lluvia_intensa", "lluvia_max_1dia_mm", "meses_sequia_previos", "z_antecedente"]


def _runs(flag: pd.Series, k: int) -> list[tuple]:
    s = pd.Series(np.where(flag.fillna(False).to_numpy(bool), -1.0, 0.0), index=flag.index)
    ev = drought.runs_below(s, -1.0, min_len=k)
    return list(zip(ev["inicio"], ev["fin"], ev["duracion_meses"]))


def heavy_threshold(daily: pd.Series, q: float = 0.95, wet: float = 1.0) -> float:
    d = daily.dropna()
    return float(d[d >= wet].quantile(q))


def cell_episodes(cell: str, spi3: pd.Series, z: dict, daily: pd.Series | None, thr_return: float = 0.0,
                  k: int = 2, heavy_q: float = 0.95, prior_months: int = 12,
                  responses=("GWETROOT", "GWETTOP")) -> list[dict]:
    ev = drought.runs_below(spi3, -1.0, min_len=2)
    months = spi3.index
    p95 = heavy_threshold(daily, heavy_q) if daily is not None else np.nan
    out = []
    starts = list(ev["inicio"])
    for i, e in ev.iterrows():
        start, end = e["inicio"], e["fin"]
        nxt = starts[i + 1] if i + 1 < len(starts) else None
        after = spi3[(months > end)]
        ret = after[after >= thr_return]
        t_ret = ret.index[0] if len(ret) else None
        if t_ret is not None and nxt is not None and t_ret >= nxt:
            t_ret = None
        rec = {"celda": cell, "inicio": start, "fin": end, "duracion_meses": int(e["duracion_meses"]),
               "severidad": float(e["severidad"]), "spi3_min": float(e["pico"]), "retorno_lluvia": t_ret,
               "anio_cluster": int(end.year)}
        prior = spi3[(months >= start - pd.DateOffset(months=prior_months)) & (months < start)]
        rec["meses_sequia_previos"] = int((prior <= -1).sum())
        if daily is not None and t_ret is not None:
            w0 = end + pd.offsets.MonthBegin(1)
            w1 = t_ret + pd.DateOffset(months=2) + pd.offsets.MonthEnd(0)
            dw = daily[(daily.index >= w0) & (daily.index <= w1)].dropna()
            tot = dw.sum()
            rec["fraccion_lluvia_intensa"] = float(dw[dw > p95].sum() / tot) if tot > 0 else np.nan
            rec["lluvia_max_1dia_mm"] = float(dw.max()) if len(dw) else np.nan
        else:
            rec["fraccion_lluvia_intensa"] = np.nan
            rec["lluvia_max_1dia_mm"] = np.nan
        rec["umbral_p95_diario_mm"] = p95
        for r in responses:
            zr = z[r]
            ante = zr.get(start - pd.DateOffset(months=1), np.nan)
            rec[f"z_antecedente_{r}"] = float(ante) if pd.notna(ante) else np.nan
            rec[f"z_min_{r}"] = float(zr[(zr.index >= start) & (zr.index <= end + pd.DateOffset(months=3))].min())
            if t_ret is not None:
                seg = zr[(zr.index >= t_ret)].iloc[:k]
                rec[f"z_retorno_{r}"] = float(zr.get(t_ret, np.nan))
                rec[f"contradiccion_A_{r}"] = bool(len(seg) == k and seg.notna().all() and (seg < -1).all())
            else:
                rec[f"z_retorno_{r}"] = np.nan
                rec[f"contradiccion_A_{r}"] = None
            post = zr[zr.index > end]
            ok = (post >= -0.5) & (post.shift(-1) >= -0.5)
            hit = post.index[ok.to_numpy()]
            limit = nxt if nxt is not None else months[-1]
            if len(hit) and hit[0] < limit:
                rec[f"meses_recuperacion_{r}"] = int((hit[0].year - end.year) * 12 + hit[0].month - end.month)
                rec[f"recuperacion_censurada_{r}"] = False
            else:
                rec[f"meses_recuperacion_{r}"] = np.nan
                rec[f"recuperacion_censurada_{r}"] = True
        out.append(rec)
    return out


def reverse_counts(cell: str, spi3: pd.Series, z: pd.Series, k: int = 2) -> dict:
    b1 = _runs((z < -1) & (spi3 >= 0) & z.notna() & spi3.notna(), k)
    b2 = _runs((z >= 0) & (spi3 <= -1) & z.notna() & spi3.notna(), k)
    return {"celda": cell, "n_B1_suelo_seco_sin_sequia": len(b1), "n_B2_suelo_normal_en_sequia": len(b2),
            "B1_periodos": "; ".join(f"{a:%Y-%m}..{b:%Y-%m}" for a, b, _ in b1),
            "B2_periodos": "; ".join(f"{a:%Y-%m}..{b:%Y-%m}" for a, b, _ in b2)}


def _std(x: np.ndarray) -> np.ndarray:
    s = np.nanstd(x)
    return (x - np.nanmean(x)) / s if s > 0 else x * np.nan


def association(ep: pd.DataFrame, outcome: str, factor: str, controls=("severidad",), B: int = 2000,
                seed: int = 7, within_cell: bool = False, extra_factors=()) -> dict:
    """Coeficiente estandarizado del factor (z del resultado por DE del factor), con control por severidad.
    IC y p por bootstrap de conglomerados (año de fin del episodio), porque celdas vecinas viven el
    mismo episodio a la vez."""
    cols = [outcome, factor, *controls, *extra_factors]
    d = ep[["celda", "anio_cluster", *cols]].dropna().copy()
    d[outcome] = d[outcome].astype(float)
    if within_cell:  # efectos fijos de celda: se compara cada celda consigo misma
        for c in cols:
            d[c] = d[c] - d.groupby("celda")[c].transform("mean")
    if len(d) < 15 or d["anio_cluster"].nunique() < 5 or d[factor].std() == 0:
        return {"n": int(len(d)), "beta": None, "ic95": None, "p": None}
    X_cols = [factor, *controls, *extra_factors]

    def fit(dd):
        X = np.column_stack([np.ones(len(dd))] + [_std(dd[c].to_numpy(float)) for c in X_cols])
        if not np.all(np.isfinite(X)):
            return np.nan
        return float(np.linalg.lstsq(X, dd[outcome].to_numpy(float), rcond=None)[0][1])

    beta = fit(d)
    rng = np.random.default_rng(seed)
    clusters = d["anio_cluster"].unique()
    groups = {c: d[d["anio_cluster"] == c] for c in clusters}
    bs = []
    for _ in range(B):
        pick = rng.choice(clusters, size=len(clusters), replace=True)
        bs.append(fit(pd.concat([groups[c] for c in pick])))
    bs = np.asarray(bs)
    bs = bs[np.isfinite(bs)]
    se = bs.std(ddof=1)
    p = float(2 * (1 - sstats.norm.cdf(abs(beta) / se))) if se > 0 else None
    return {"n": int(len(d)), "n_conglomerados": int(len(clusters)), "beta": beta,
            "ic95": [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))], "p": p}


def factor_table(ep: pd.DataFrame, outcomes: list[tuple[str, str]], B: int = 2000) -> pd.DataFrame:
    """outcomes: [(columna_resultado, respuesta)]. Antecedente usa la z de la misma respuesta."""
    rows = []
    for oc, resp in outcomes:
        for f in FACTORS:
            col = f"z_antecedente_{resp}" if f == "z_antecedente" else f
            a = association(ep, oc, col, B=B)
            rows.append({"resultado": oc, "factor": f, "columna_factor": col, **a})
    df = pd.DataFrame(rows)
    df["q_bh"] = stats.benjamini_hochberg(df["p"].tolist())
    df["n_pruebas_bh"] = int(df["p"].notna().sum())
    return df


def matched_pair_episodes(epa: pd.DataFrame, epb: pd.DataFrame, max_gap_months: int = 2,
                          max_spi_diff: float = 0.5, resp: str = "GWETROOT") -> pd.DataFrame:
    """Empareja episodios de A y B que terminan con <= 2 meses de diferencia y tienen SPI-3 mínimo
    parecido (|Δ| <= 0.5). Así se compara la respuesta ante lluvia comparable en el mismo momento."""
    rows, used = [], set()
    for _, a in epa.iterrows():
        best, gap_best = None, None
        for j, b in epb.iterrows():
            if j in used:
                continue
            gap = abs((a["fin"].year - b["fin"].year) * 12 + a["fin"].month - b["fin"].month)
            if gap <= max_gap_months and abs(a["spi3_min"] - b["spi3_min"]) <= max_spi_diff:
                if gap_best is None or gap < gap_best:
                    best, gap_best = j, gap
        if best is None:
            continue
        used.add(best)
        b = epb.loc[best]
        rows.append({"fin_a": a["fin"], "fin_b": b["fin"], "spi3_min_a": a["spi3_min"], "spi3_min_b": b["spi3_min"],
                     "severidad_a": a["severidad"], "severidad_b": b["severidad"],
                     f"z_retorno_a": a[f"z_retorno_{resp}"], f"z_retorno_b": b[f"z_retorno_{resp}"],
                     "meses_recuperacion_a": a[f"meses_recuperacion_{resp}"],
                     "meses_recuperacion_b": b[f"meses_recuperacion_{resp}"],
                     "contradiccion_a": a[f"contradiccion_A_{resp}"], "contradiccion_b": b[f"contradiccion_A_{resp}"],
                     "fraccion_intensa_a": a["fraccion_lluvia_intensa"], "fraccion_intensa_b": b["fraccion_lluvia_intensa"],
                     "max1d_a": a["lluvia_max_1dia_mm"], "max1d_b": b["lluvia_max_1dia_mm"],
                     "z_antecedente_a": a[f"z_antecedente_{resp}"], "z_antecedente_b": b[f"z_antecedente_{resp}"],
                     "meses_previos_a": a["meses_sequia_previos"], "meses_previos_b": b["meses_sequia_previos"]})
    return pd.DataFrame(rows)


def paired_summary(m: pd.DataFrame, col: str, B: int = 5000, seed: int = 11) -> dict:
    d = (m[f"{col}_a"] - m[f"{col}_b"]).astype(float).dropna().to_numpy()
    if d.size < 3:
        return {"variable": col, "n": int(d.size), "media_dif": float(d.mean()) if d.size else None,
                "ic95": None, "p_wilcoxon": None}
    rng = np.random.default_rng(seed)
    bs = rng.choice(d, size=(B, d.size), replace=True).mean(axis=1)
    try:
        p = float(sstats.wilcoxon(d).pvalue) if np.any(d != 0) else 1.0
    except ValueError:
        p = None
    return {"variable": col, "n": int(d.size), "media_dif": float(d.mean()),
            "ic95": [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))],
            "n_a_menor": int((d < 0).sum()), "p_wilcoxon": p}
