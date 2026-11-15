"""Datos de la galería: SOLO se leen resultados verificados y se reutilizan los cargadores de los motores.

- SPI-3 por provincia y mes de los cuatro productos (IMERG, CHIRPS, lluvia de forzamiento GLDAS, MERRA-2): se
  recalcula importando las funciones del motor de auditoría (datos.G05, analisis.monthly_cubes, decision.spi3),
  exactamente como en analisis.drought_flips, y se guarda en figures/galeria/_datos/ (única carpeta escribible).
- Estados de acuerdo por provincia-mes con las definiciones de la auditoría (decision.flip_components y la
  'contradicción clara' de analisis.drought_flips). Los totales se comprueban contra results/auditoria.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from .estilo import DATOS

R_AUD = Path("results/auditoria")
R_TEN = Path("results/tendencias")
R_YUNA = Path("results/yuna")
D_HR = Path("data/nacional_hr/derivados")
ADM1 = Path("data/nacional/limites/geoBoundaries-DOM-ADM1.geojson")
ADM0 = Path("data/nacional_hr/limites/geoBoundaries-DOM-ADM0_simplified.geojson")
PRODUCTOS = ["IMERG", "CHIRPS", "GLDAS_forzamiento", "MERRA2"]
NOMBRE_EN = {"IMERG": "IMERG V07 Final", "CHIRPS": "CHIRPS v2.0", "GLDAS_forzamiento": "GLDAS-2.1 forcing (GPCP)",
             "MERRA2": "MERRA-2 (NASA POWER)"}
MESES = pd.date_range("2001-01-01", "2024-12-01", freq="MS")

# estados (códigos enteros para la matriz)
NODATA, NONE, SPLIT, MAJ, UNAN, CONTRA = -1, 0, 1, 2, 3, 4
ESTADOS = {UNAN: "unanimous", MAJ: "majority", SPLIT: "split", CONTRA: "contradiction", NONE: "no_alarm",
           NODATA: "no_data"}


def spi3_provincias() -> dict:
    """{producto: DataFrame (288 meses × 32 provincias)} de SPI-3. Caché en _datos/spi3_provincias.parquet."""
    p = DATOS / "spi3_provincias.parquet"
    if p.exists():
        df = pd.read_parquet(p)
    else:
        from ..auditoria import analisis, decision
        from ..auditoria import datos as adatos
        g = adatos.G05()
        cubes = analisis.monthly_cubes(g)
        rows = []
        for k, v in cubes.items():
            spi = decision.spi3(g.province_mean(v), adatos.MESES)
            d = pd.DataFrame(spi, index=adatos.MESES, columns=g.provs)
            d.index.name = "mes"
            d = d.reset_index().melt(id_vars="mes", var_name="provincia", value_name="spi3")
            d["producto"] = k
            rows.append(d)
        df = pd.concat(rows, ignore_index=True)
        DATOS.mkdir(parents=True, exist_ok=True)
        df.to_parquet(p, index=False)
    out = {}
    for k in PRODUCTOS:
        s = df[df["producto"] == k].pivot(index="mes", columns="provincia", values="spi3")
        out[k] = s.reindex(MESES)
    return out


def estados(spi: dict, thr: float = -1.0) -> tuple[pd.DataFrame, dict]:
    """Estado de acuerdo por provincia-mes (mismas definiciones que la auditoría) + recuentos."""
    from ..auditoria import decision
    provs = list(spi[PRODUCTOS[0]].columns)
    S = {k: spi[k][provs].to_numpy(float) for k in PRODUCTOS}
    F = {k: decision.flags(S[k], thr) for k in PRODUCTOS}
    c = decision.flip_components(F)
    with np.errstate(all="ignore"), __import__("warnings").catch_warnings():
        __import__("warnings").simplefilter("ignore", RuntimeWarning)
        smax = np.nanmax(np.stack([S[k] for k in PRODUCTOS]), 0)
    n = c["n_alarmas"]
    clara = c["no_unanime"] & (smax >= 0)
    E = np.full(n.shape, NODATA, int)
    E[c["valido"]] = NONE
    E[c["no_unanime"] & (n <= 2)] = SPLIT
    E[c["no_unanime"] & (n == 3)] = MAJ
    E[clara] = CONTRA                                  # la contradicción clara tiene prioridad (1-3 de 4 + otro ≥ 0)
    E[c["alguna_alarma"] & ~c["no_unanime"]] = UNAN
    cnt = {ESTADOS[k]: int((E == k).sum()) for k in ESTADOS}
    cnt.update({"n_casos": int(c["valido"].sum()), "n_alguna_alarma": int(c["alguna_alarma"].sum()),
                "n_no_unanime": int(c["no_unanime"].sum()), "n_contradiccion_clara": int(clara.sum())})
    return pd.DataFrame(E, index=spi[PRODUCTOS[0]].index, columns=provs), cnt


def auditoria_nacional(thr: float = -1.0, combo: str = "4 productos") -> dict:
    doc = json.loads((R_AUD / "cambio_decision_sequia_nacional.json").read_text(encoding="utf-8"))
    return next(d for d in doc if d["umbral_spi3"] == thr and d["productos"] == combo)


def auditoria_provincias(thr: float = -1.0) -> pd.DataFrame:
    d = pd.read_csv(R_AUD / "cambio_decision_sequia_provincias.csv")
    return d[d["umbral_spi3"] == thr].set_index("provincia")


def auditoria_por_anio() -> pd.DataFrame:
    return pd.read_csv(R_AUD / "cambio_decision_sequia_por_anio.csv").set_index("anio")


def check_contra_auditoria(E: pd.DataFrame, cnt: dict) -> dict:
    """Comprueba que los recuentos re-calculados son idénticos a los de results/auditoria (lanza si no)."""
    nat = auditoria_nacional()
    for k in ("n_casos", "n_alguna_alarma", "n_no_unanime", "n_contradiccion_clara"):
        assert cnt[k] == nat[k], f"{k}: galería {cnt[k]} ≠ auditoría {nat[k]}"
    assert cnt["unanimous"] == nat["n_unanime_sequia"] == 275, cnt["unanimous"]
    pa = auditoria_por_anio()
    yrs = E.index.year
    for y, r in pa.iterrows():
        sub = E[yrs == y].to_numpy()
        assert int((sub == UNAN).sum()) == r["n_unanime_sequia"], y
        assert int((sub == CONTRA).sum()) == r["n_contradiccion_clara"], y
        assert int(np.isin(sub, (SPLIT, MAJ, CONTRA)).sum()) == r["n_no_unanime"], y
    pr = auditoria_provincias()
    for p in E.columns:
        col = E[p].to_numpy()
        assert int(np.isin(col, (SPLIT, MAJ, CONTRA)).sum()) == pr.loc[p, "n_no_unanime"], p
        assert int(np.isin(col, (SPLIT, MAJ, CONTRA, UNAN)).sum()) == pr.loc[p, "n_alguna_alarma"], p
    return nat


# ------------------------------------------------------------------ geografía

def adm1_rings() -> list[tuple[str, list[np.ndarray]]]:
    from .. import boundaries
    return [(u.name, [e for e, _ in u.polygons]) for u in boundaries.load_units(ADM1)]


def adm0_rings() -> list[np.ndarray]:
    from .. import region
    doc = json.loads(ADM0.read_text(encoding="utf-8"))
    out = []
    for f in doc["features"]:
        out += [e for e, _ in region._polys(f["geometry"])]
    return out


def yuna_ring() -> np.ndarray:
    doc = json.loads((R_YUNA / "cuencas_yuna.geojson").read_text(encoding="utf-8"))
    f = next((f for f in doc["features"] if f["properties"].get("zona") == "yuna"), doc["features"][0])
    from .. import region
    polys = region._polys(f["geometry"])
    return max((e for e, _ in polys), key=len), f["properties"]


def hatillo() -> tuple[float, float]:
    # results/yuna/hatillo_ficha.json: "19°02′00.91″N 70°12′01.49″W (19.0336, -70.2004)"
    txt = json.loads((R_YUNA / "hatillo_ficha.json").read_text(encoding="utf-8"))["coordenadas_cortina"]
    a = txt.split("(")[1].split(")")[0].split(",")
    return float(a[0]), float(a[1])


def dem_nativo() -> dict:
    z = np.load(D_HR / "nativas.npz")
    return {"Z": z["dem_Z"].astype(float), "lat": z["dem_lat"].astype(float), "lon": z["dem_lon"].astype(float)}
