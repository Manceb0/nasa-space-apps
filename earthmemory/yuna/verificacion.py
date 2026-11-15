"""Verificación observada con MODIS MCDWD_L3 (OBSERVACIÓN, independiente de la lluvia).

Reglas (fijadas antes de mirar los eventos):
- Capa principal Flood_2Day_250m para eventos y meses GSW; Flood_3Day_250m para los episodios de lluvia fuerte (día +3,
  que cubre los días +1 a +3), por tener menos nubes. «Inundación» = clase 3 (inusual). La clase 2 (recurrente/estacional) se informa aparte.
- Un día cuenta como «observable» en una zona si < 80 % de sus píxeles son «datos insuficientes» (255).
- Referencia: días secos (antecedente 30 d < p25 y < 5 mm en 48 h), uno por año 2003-2024.
- Inundación observada en un evento/episodio = máximo de km² de clase 3 en la cuenca (días observables) > p95 de la
  referencia Y ≥ 2 km² (~40 píxeles). Anomalía = máximo − mediana de la referencia.
- Sin ningún día observable → «indeterminado» (nubes), no «sin inundación».
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
from scipy import stats

from .common import DATA, RES, SEED

ZONAS = ("yuna", "alto_hatillo", "camu", "bajo_yuna", "llanura")
MAX_INSUF = 0.80
MIN_KM2 = 2.0


def disponible() -> bool:
    return (DATA / "mcdwd").exists() and any((DATA / "mcdwd").glob("mcdwd_*.npz")) and (RES / "mcdwd_dias_pedidos.csv").exists()


def cargar_stats(zonas_geom: dict) -> pd.DataFrame:
    from . import mcdwd
    m = mcdwd.mascaras({k: zonas_geom[k] for k in ("yuna", "alto_hatillo", "camu", "bajo_yuna")})
    st = mcdwd.estadisticas(m)
    st.to_csv(RES / "mcdwd_diario_zonas.csv", index=False)
    fijo = mcdwd.siempre_enmascarado()
    (RES / "mcdwd_mascaras.json").write_text(json.dumps({k: {"pixeles": int(v.sum()), "km2": float(v.sum() * mcdwd.PX_KM2),
                                                              "frac_siempre_enmascarada": float((v & fijo).sum() / v.sum())}
                                                          for k, v in m.items()}, indent=1), encoding="utf-8")
    return st


def _capa(st, capa):
    s = st[st["capa"] == capa].copy()
    s["fecha"] = pd.to_datetime(s["fecha"])
    return s.set_index("fecha").sort_index()


def referencia(st: pd.DataFrame, dias: pd.DataFrame) -> dict:
    ref_d = pd.to_datetime(dias.loc[dias["motivo"] == "referencia_seca", "fecha"]).unique()
    out = {}
    for capa in ("Flood_2Day_250m", "Flood_3Day_250m"):
        s = _capa(st, capa)
        s = s[s.index.isin(ref_d)]
        r = {"n_dias": int(len(s))}
        for z in ZONAS:
            ok = s[f"insuf_{z}"] < MAX_INSUF
            r[f"n_observables_{z}"] = int(ok.sum())
            x = s.loc[ok, f"inund_km2_{z}"]
            r[f"mediana_{z}"] = float(x.median()) if len(x) else np.nan
            r[f"p95_{z}"] = float(x.quantile(0.95)) if len(x) else np.nan
            r[f"agua_ref_mediana_{z}"] = float(s.loc[ok, f"agua_ref_km2_{z}"].median()) if len(x) else np.nan
            r[f"insuf_media_{z}"] = float(s[f"insuf_{z}"].mean()) if len(s) else np.nan
        out[capa] = r
    return out


def resumir(st: pd.DataFrame, fechas, capa: str, ref: dict) -> dict:
    s = _capa(st, capa)
    s = s[s.index.isin(pd.to_datetime(list(fechas)))]
    r = {"n_dias": int(len(s))}
    for z in ZONAS:
        ok = s[f"insuf_{z}"] < MAX_INSUF
        r[f"n_obs_{z}"] = int(ok.sum())
        r[f"insuf_min_{z}"] = float(s[f"insuf_{z}"].min()) if len(s) else np.nan
        if ok.any():
            i = s.loc[ok, f"inund_km2_{z}"].idxmax()
            r[f"inund_km2_max_{z}"] = float(s.loc[i, f"inund_km2_{z}"])
            r[f"recurrente_km2_max_{z}"] = float(s.loc[ok, f"recurrente_km2_{z}"].max())
            r[f"dia_max_{z}"] = i.strftime("%Y-%m-%d")
            r[f"anomalia_km2_{z}"] = r[f"inund_km2_max_{z}"] - ref[capa][f"mediana_{z}"]
        else:
            r[f"inund_km2_max_{z}"] = np.nan
    x, p95 = r.get("inund_km2_max_yuna", np.nan), ref[capa]["p95_yuna"]
    r["observa"] = (None if not np.isfinite(x) else bool(x > p95 and x >= MIN_KM2))
    return r


def por_evento(st, dias, ref, cat) -> pd.DataFrame:
    filas = []
    ev = dias[dias["motivo"] == "evento"]
    for i, g in ev.groupby("id"):
        r = resumir(st, g["fecha"], "Flood_2Day_250m", ref)
        r3 = resumir(st, g["fecha"], "Flood_3Day_250m", ref)
        filas.append({"id": i, **r, "observa_3d": r3["observa"], "inund_km2_max_yuna_3d": r3.get("inund_km2_max_yuna")})
    return pd.DataFrame(filas)


def por_episodio(st, dias, ref, ep: pd.DataFrame) -> pd.DataFrame:
    filas = []
    e2 = dias[dias["motivo"] == "episodio_p99"]
    for i, g in e2.groupby("id"):
        r = resumir(st, g["fecha"], "Flood_3Day_250m", ref)
        filas.append({"inicio": pd.Timestamp(i), **r})
    out = pd.DataFrame(filas)
    if len(out):
        ep = ep.copy()
        ep["inicio"] = pd.to_datetime(ep["inicio"])
        out = ep.merge(out, on="inicio", how="left")
    return out


def por_mes_gsw(st, dias, ref) -> pd.DataFrame:
    filas = []
    for i, g in dias[dias["motivo"] == "gsw_sin_evento"].groupby("id"):
        filas.append({"mes": i, **resumir(st, g["fecha"], "Flood_2Day_250m", ref)})
    return pd.DataFrame(filas)


def auc_observado(epm: pd.DataFrame, b: int = 2000) -> dict:
    """AUC del antecedente/lluvia por zona para separar episodios de lluvia fuerte CON inundación observada (MCDWD)
    de los episodios SIN ella (solo episodios determinables)."""
    from .analisis import auc
    rng = np.random.default_rng(SEED)
    d = epm[epm["observa"].notna()].copy()
    d["observa"] = d["observa"].astype(bool)
    res = {"n_episodios_determinables": int(len(d)), "n_con_inundacion_observada": int(d["observa"].sum()),
           "n_indeterminados_nubes": int(epm["observa"].isna().sum())}
    for var in ("ant30_pct", "gldas_z", "r48"):
        for z in ("alto_hatillo", "camu", "bajo_yuna"):
            pos = d.loc[d["observa"], f"{var}_{z}"].to_numpy()
            neg = d.loc[~d["observa"], f"{var}_{z}"].to_numpy()
            a = auc(pos, neg)
            bs = [auc(rng.choice(pos, len(pos)), rng.choice(neg, len(neg))) for _ in range(b)] if len(pos) and len(neg) else [np.nan]
            res[f"AUC_{var}_{z}"] = a
            res[f"AUC_{var}_{z}_ic95"] = [float(np.nanpercentile(bs, 2.5)), float(np.nanpercentile(bs, 97.5))]
        dif = []
        for _ in range(b):
            s = d.iloc[rng.integers(0, len(d), len(d))]
            p, n = s[s["observa"]], s[~s["observa"]]
            dif.append(auc(p[f"{var}_alto_hatillo"], n[f"{var}_alto_hatillo"]) - auc(p[f"{var}_camu"], n[f"{var}_camu"]))
        res[f"dAUC_{var}_alto_menos_camu"] = res[f"AUC_{var}_alto_hatillo"] - res[f"AUC_{var}_camu"]
        res[f"dAUC_{var}_alto_menos_camu_ic95"] = [float(np.nanpercentile(dif, 2.5)), float(np.nanpercentile(dif, 97.5))]
    # tabla 2×2: antecedente húmedo (≥ p90 del mes en la cuenca entera, IMERG 30 d) × inundación observada
    if "ant30_pct_bajo_yuna" in d:
        hum = (d[["ant30_pct_alto_hatillo", "ant30_pct_camu", "ant30_pct_bajo_yuna"]].mean(axis=1) >= 90)
        t = pd.crosstab(hum, d["observa"]).reindex(index=[False, True], columns=[False, True], fill_value=0)
        res["tabla_humedo_x_observa"] = t.to_numpy().tolist()
        res["fisher_p"] = float(stats.fisher_exact(t.to_numpy())[1])
        res["frac_inund_si_humedo"] = float(t.loc[True, True] / t.loc[True].sum()) if t.loc[True].sum() else None
        res["frac_inund_si_no_humedo"] = float(t.loc[False, True] / t.loc[False].sum()) if t.loc[False].sum() else None
    return res


def run(zonas_geom: dict, cat: pd.DataFrame, ep: pd.DataFrame) -> dict | None:
    if not disponible():
        return None
    dias = pd.read_csv(RES / "mcdwd_dias_pedidos.csv", parse_dates=["fecha"])
    st = cargar_stats(zonas_geom)
    ref = referencia(st, dias)
    eve = por_evento(st, dias, ref, cat)
    eve.to_csv(RES / "mcdwd_por_evento.csv", index=False)
    epm = por_episodio(st, dias, ref, ep)
    epm.to_csv(RES / "mcdwd_episodios_lluvia_fuerte.csv", index=False)
    gm = por_mes_gsw(st, dias, ref)
    gm.to_csv(RES / "mcdwd_meses_gsw_sin_evento.csv", index=False)
    au = auc_observado(epm) if len(epm) else {}
    insuf_ev = float(_capa(st, "Flood_2Day_250m")["insuf_yuna"].mean())
    out = {"referencia": ref, "auc_observado": au, "insuf_media_yuna_2d": insuf_ev,
           "n_dias": int(st["fecha"].nunique()), "MAX_INSUF": MAX_INSUF, "MIN_KM2": MIN_KM2}
    (RES / "mcdwd_resumen.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    return {"st": st, "dias": dias, "ref": ref, "eventos": eve, "episodios": epm, "gsw": gm, "auc": au, "resumen": out}
