"""Verdad de terreno (con circularidad marcada): estaciones GHCN-Daily y GSOD de RD frente a los productos.

- GHCN-Daily (prefijo DR): PRCP en décimas de mm; se descartan valores con bandera de calidad (QFLAG).
- GSOD: PRCP en pulgadas (99.99 = sin dato). Se aceptan solo las banderas que cubren 24 h completas:
  D (4 reportes de 6 h), F (2 de 12 h), G (1 de 24 h). Readme GSOD: el día GSOD es 00-24 UTC y el acumulado
  "usually will not end with the midnight observation" → la fecha puede ir un día después del aguacero.
- Por eso se prueban desfases de −1, 0 y +1 días entre producto y estación y se informa el mejor.
- Circularidad: CHIRPS v2 publica qué estaciones entraron a su mezcla cada mes (diagnostics/monthly_station_data):
  se cruza por coordenadas (≤ 0.03°). GPCC (ajuste mensual de IMERG Final) y CPC Unified (corrección de la
  lluvia de MERRA-2) usan informes SYNOP del GTS: una estación sinóptica OMM con informes en GTS es
  PROBABLEMENTE parte de ambos (no hay lista pública por estación para comprobarlo → "probable", no "seguro").
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from .descarga import DATA, WMO_DOM

GSOD_OK = {"D", "F", "G"}


def load_oscar() -> pd.DataFrame:
    p = DATA / "oscar" / "oscar_DOM.json"
    rows = []
    if p.exists():
        doc = json.loads(p.read_text(encoding="utf-8"))
        items = doc.get("stationSearchResults", doc if isinstance(doc, list) else [])
        for s in items:
            wid = str(s.get("wigosStationIdentifier", "") or s.get("wigosId", ""))
            w = wid.split("-")[-1] if wid else ""
            if w in WMO_DOM:
                rows.append({"omm": w, "nombre_oscar": s.get("name"), "lat": s.get("latitude"), "lon": s.get("longitude"),
                             "elev_m": s.get("elevation")})
    return pd.DataFrame(rows)


def read_ghcnd(sid: str) -> pd.DataFrame | None:
    p = DATA / "ghcnd" / f"{sid}.csv"
    if not p.exists():
        return None
    d = pd.read_csv(p, low_memory=False)
    if "PRCP" not in d:
        return None
    d = d[["STATION", "DATE", "LATITUDE", "LONGITUDE", "PRCP", "PRCP_ATTRIBUTES"]].dropna(subset=["PRCP"])
    att = d["PRCP_ATTRIBUTES"].fillna(",,,").str.split(",", expand=True)
    d["mflag"], d["qflag"], d["sflag"] = att[0].str.strip(), att[1].str.strip(), att[2].str.strip()
    d = d[(d["qflag"] == "") | d["qflag"].isna()]
    d["fecha"] = pd.to_datetime(d["DATE"])
    d["mm"] = d["PRCP"].astype(float) / 10.0
    return d


def read_gsod(w: str, y0=2001, y1=2024) -> pd.DataFrame | None:
    parts = []
    for y in range(y0, y1 + 1):
        p = DATA / "gsod" / w / f"{y}.csv"
        if p.exists():
            parts.append(pd.read_csv(p, low_memory=False))
    if not parts:
        return None
    d = pd.concat(parts)
    d["fecha"] = pd.to_datetime(d["DATE"])
    d["flag"] = d["PRCP_ATTRIBUTES"].astype(str).str.strip()
    d = d[(d["PRCP"] < 99.0) & d["flag"].isin(GSOD_OK)]
    d["mm"] = d["PRCP"].astype(float) * 25.4
    return d


def station_table(y0=2001, y1=2024) -> tuple[pd.DataFrame, dict]:
    """Una serie diaria por estación OMM: GHCN-D si existe (red pedida), si no GSOD. Metadatos y completitud."""
    osc = load_oscar().set_index("omm") if len(load_oscar()) else pd.DataFrame()
    dias = pd.date_range(f"{y0}-01-01", f"{y1}-12-31", freq="D")
    series, meta = {}, []
    for w, name in WMO_DOM.items():
        g = read_ghcnd(f"DRM000{w}")
        src = "GHCN-Daily"
        if g is not None:
            g = g[(g["fecha"] >= dias[0]) & (g["fecha"] <= dias[-1])]
        if g is None or len(g) < 365:
            g = read_gsod(w, y0, y1)
            src = "GSOD (ISD)"
        if g is None or not len(g):
            meta.append({"omm": w, "nombre": name, "red": "sin datos 2001-2024", "dias_validos": 0})
            continue
        s = g.groupby("fecha")["mm"].first().reindex(dias)
        lat = float(osc.loc[w, "lat"]) if w in getattr(osc, "index", []) else float(g["LATITUDE"].iloc[0])
        lon = float(osc.loc[w, "lon"]) if w in getattr(osc, "index", []) else float(g["LONGITUDE"].iloc[0])
        sflags = (g["sflag"].value_counts().to_dict() if "sflag" in g else g["flag"].value_counts().to_dict())
        series[w] = s
        yrs = s.notna().groupby(s.index.year).mean()
        meta.append({"omm": w, "nombre": name, "red": src, "id_ghcnd": f"DRM000{w}" if src == "GHCN-Daily" else "",
                     "lat": lat, "lon": lon, "lat_red": float(g["LATITUDE"].iloc[0]), "lon_red": float(g["LONGITUDE"].iloc[0]),
                     "dias_validos": int(s.notna().sum()), "completitud": float(s.notna().mean()),
                     "anios_con_80pc": int((yrs >= 0.8).sum()), "primer_dia": str(s.first_valid_index().date()),
                     "ultimo_dia": str(s.last_valid_index().date()),
                     "activa_2024": bool(s.loc["2024"].notna().mean() > 0.5),
                     "banderas_fuente": json.dumps({str(k): int(v) for k, v in sflags.items()})})
    return pd.DataFrame(meta), series


def chirps_ingestion(meta: pd.DataFrame) -> pd.DataFrame:
    """Por estación y mes: ¿aparece en la lista de estaciones de CHIRPS v2 de ese mes? (GTS / GSOD / otra)."""
    rows = []
    for p in sorted((DATA / "chirps_estaciones").glob("*_RD.csv")):
        ym = p.stem.split("_")[0]
        try:
            d = pd.read_csv(p)
        except pd.errors.EmptyDataError:
            continue
        for _, m in meta.dropna(subset=["lat"]).iterrows():
            near = d[(np.abs(d["latitude"] - m["lat_red"]) <= 0.03) & (np.abs(d["longitude"] - m["lon_red"]) <= 0.03)]
            near2 = d[(np.abs(d["latitude"] - m["lat"]) <= 0.03) & (np.abs(d["longitude"] - m["lon"]) <= 0.03)]
            near = pd.concat([near, near2]).drop_duplicates()
            rows.append({"omm": m["omm"], "mes": ym, "en_chirps": bool(len(near)),
                         "fuentes_chirps": "+".join(sorted(near["source"].astype(str).unique())) if len(near) else ""})
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ métricas

def kge(o: np.ndarray, m: np.ndarray) -> dict:
    r = np.corrcoef(o, m)[0, 1] if o.std() > 0 and m.std() > 0 else np.nan
    alpha = m.std() / o.std() if o.std() > 0 else np.nan
    beta = m.mean() / o.mean() if o.mean() > 0 else np.nan
    return {"r": r, "alfa": alpha, "beta": beta, "kge": 1 - np.sqrt((r - 1) ** 2 + (alpha - 1) ** 2 + (beta - 1) ** 2)}


def metrics(o: pd.Series, m: pd.Series, thresholds=(50, 100)) -> dict:
    d = pd.DataFrame({"o": o, "m": m}).dropna()
    out = {"n": int(len(d))}
    if len(d) < 30:
        return out
    oo, mm = d["o"].to_numpy(float), d["m"].to_numpy(float)
    out.update(kge(oo, mm))
    out["sesgo_rel"] = (mm.sum() - oo.sum()) / oo.sum() if oo.sum() > 0 else np.nan
    for t in thresholds:
        O, M = oo >= t, mm >= t
        h, mi, fa = int((O & M).sum()), int((O & ~M).sum()), int((~O & M).sum())
        out[f"n_obs_{t}"] = int(O.sum())
        out[f"pod_{t}"] = h / (h + mi) if h + mi else np.nan
        out[f"far_{t}"] = fa / (h + fa) if h + fa else np.nan
        out[f"csi_{t}"] = h / (h + mi + fa) if h + mi + fa else np.nan
    wo, wm = oo[oo >= 1], mm[mm >= 1]
    for q in (95, 99):
        out[f"p{q}_obs"] = float(np.percentile(wo, q)) if wo.size > 20 else np.nan
        out[f"p{q}_prod"] = float(np.percentile(wm, q)) if wm.size > 20 else np.nan
    out["max_obs"], out["max_prod"] = float(oo.max()), float(mm.max())
    return out


def best_lag(o: pd.Series, m: pd.Series, lags=(-1, 0, 1)) -> dict:
    """lag k: se compara o[t] con m[t − k] (k = +1 → la estación fecha el aguacero un día después)."""
    best = None
    for k in lags:
        d = pd.DataFrame({"o": o.to_numpy(), "m": m.shift(k).to_numpy()}).dropna()
        if len(d) < 30:
            continue
        r = float(np.corrcoef(d["o"], d["m"])[0, 1])
        if best is None or r > best["r"]:
            best = {"lag_dias": k, "r": r}
    return best or {"lag_dias": None, "r": np.nan}
