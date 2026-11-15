"""¿El cambio de IMERG viene de su parte infrarroja? Prueba de la pista GOES-13 → GOES-16 (GOES-East desde 18-dic-2017).

IMERG Final diario V07 (GPM_3IMERGDF) trae, por celda y día, cuántas medias horas tienen dato (precipitation_cnt) y
cuántas tienen lluvia (precipitation_cnt_cond), y lo mismo solo para las medias horas con observación directa de
microondas (MWprecipitation_cnt, MWprecipitation_cnt_cond). Las medias horas SIN microondas se rellenan con
morphing de microondas + infrarrojo (IR): ahí es donde un cambio en la entrada IR (GOES) debería notarse.

  f_mw = lluvia / medias horas con microondas  (los huecos de microondas quedan como AUSENTES, no como secos)
  f_ir = lluvia / medias horas sin microondas  (componente morphing + IR)
  cob  = medias horas con microondas / medias horas con dato  (cobertura: posible confusor)

Antes = 2016-01..2017-11; después = 2018-12..2019-12; se excluye la transición (2017-12..2018-11, que contiene la
ventana del modelo de forma, 2018-02..2018-11). Anomalías respecto al mes del calendario; IC por bootstrap de meses.
Limitación: el diario no trae precipitationUncal (sin el ajuste con pluviómetros) ni IRinfluence; esa parte de la
prueba queda pendiente (media hora). Predicciones registradas antes de descargar.
Ejecutar: docker compose run --rm --entrypoint uv tropical run --frozen --no-sync python -m earthmemory.tropical.gpm_fuentes
"""

from __future__ import annotations

import json
import urllib.parse
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from .. import earthdata as ed
from ..hr.common import ROOT, write_json
from ..power import Manifest
from ..tendencias import datos
from .run import SEED

OUT = ROOT / "results" / "tropical" / "gpm_fuentes"
DDIR = ROOT / "data" / "tropical" / "imerg_fuentes"
BBOX = (-72.10, 17.40, -68.20, 20.00)
VARS = ["precipitation", "precipitation_cnt", "precipitation_cnt_cond",
        "MWprecipitation_cnt", "MWprecipitation_cnt_cond"]
ANTES = ("2016-01", "2017-11")
DESPUES = ("2018-12", "2019-12")
PREDICCIONES = {
    "H1": "Control: en esta ventana, la diferencia de días ≥ 1 mm IMERG − CHIRPS baja después frente a antes.",
    "H2": "Si la vía infrarroja contribuye: el cambio (después − antes, sin ciclo estacional) de la fracción de medias "
          "horas con lluvia SIN microondas (f_ir) es más negativo que el de las medias horas CON microondas (f_mw), "
          "y el IC 95 % de (Δf_ir − Δf_mw) queda por debajo de 0.",
    "H3": "Confusor: la cobertura de microondas (cob) cambia menos de un 10 % relativo; si cambia más, la prueba es "
          "ambigua.",
    "interpretacion": {
        "cambia sobre todo f_ir": "apoya investigar la vía infrarroja; NO identifica a GOES como causa",
        "cambia también f_mw": "debilita una explicación solo infrarroja",
        "no cambia ninguna pero sí H1": "orienta hacia la calibración con pluviómetros o el umbral diario (no se "
                                        "puede probar con el producto diario)",
        "cobertura insuficiente o ambiguo": "hipótesis sin resolver",
    },
}


def url(day, i0, i1, j0, j1):
    n = f"3B-DAY.MS.MRG.3IMERG.{day:%Y%m%d}-S000000-E235959.V07B.nc4"
    ds = ed.DATASETS["IMERG_D"]
    gid = urllib.parse.quote(f"{ds['short']}.{ds['ver']}:{n}")
    ce = ";".join([f"/{v}[0:1:0][{i0}:1:{i1}][{j0}:1:{j1}]" for v in VARS] + [f"/lat[{j0}:1:{j1}]", f"/lon[{i0}:1:{i1}]"])
    principal = f"{ed.CLOUD_OPENDAP}/{ds['cmr']}/granules/{gid}.dap.nc4?dap4.ce={urllib.parse.quote(ce, safe='/:;')}"
    ce2 = ",".join([f"{v}[0:0][{i0}:{i1}][{j0}:{j1}]" for v in VARS] + [f"lat[{j0}:{j1}]", f"lon[{i0}:{i1}]"])
    respaldo = f"{ed.GPM_OPENDAP}/GPM_3IMERGDF.07/{day:%Y/%m}/{n}?{ce2}"
    return n, principal, respaldo


def descargar():
    DDIR.mkdir(parents=True, exist_ok=True)
    i0, i1, j0, j1 = ed.bbox_to_edges(BBOX, ed.IMERG_GRID)
    jobs, alt = [], {}
    for day in pd.date_range("2016-01-01", "2019-12-31", freq="D"):
        n, u, r = url(day, i0, i1, j0, j1)
        d = DDIR / str(day.year) / n
        jobs.append((u, d, {"dataset": "IMERG_D", "doi": ed.DATASETS["IMERG_D"]["doi"], "granulo": n,
                            "variables": VARS}))
        alt[str(d)] = r
    res = ed.fetch_many(jobs, Manifest(DDIR / "MANIFEST.json"), workers=8, log_every=200,
                        fallback=lambda u, d: alt.get(str(d)))
    print({k: (v if k != "errores" else len(v)) for k, v in res.items()}, flush=True)
    if res["errores"]:
        print("primeros errores:", res["errores"][:3], flush=True)
    return res


def leer():
    files = sorted(DDIR.glob("*/*.nc4"))
    out = {v: [] for v in VARS}
    days = []
    for f in files:
        for v in VARS:
            a, lat, lon, _ = ed.read_subset(f, v)
            out[v].append(a)
        days.append(pd.Timestamp(f.name.split(".")[4][:8]))
    A = {v: np.stack(x) for v, x in out.items()}
    for v in VARS[1:]:
        A[v] = np.where(A[v] < 0, np.nan, A[v])
    return A, pd.DatetimeIndex(days), lat, lon


def mensual(A, days, mask):
    def s(v):
        return pd.Series(np.nansum(A[v][:, mask], 1), index=days).groupby(days.to_period("M")).sum()
    tot, tc = s("precipitation_cnt"), s("precipitation_cnt_cond")
    mw, mc = s("MWprecipitation_cnt"), s("MWprecipitation_cnt_cond")
    wet = pd.Series(np.nanmean(A["precipitation"][:, mask] >= 1, 1), index=days).groupby(days.to_period("M")).mean()
    return pd.DataFrame({"f_tot": tc / tot, "f_mw": mc / mw, "f_ir": (tc - mc) / (tot - mw), "cob": mw / tot,
                         "dias_humedos": wet})


def delta(df, rng, n=2000):
    an = df - df.groupby(df.index.month).transform("mean")
    b = an[(an.index >= ANTES[0]) & (an.index <= ANTES[1])]
    a = an[(an.index >= DESPUES[0]) & (an.index <= DESPUES[1])]
    out = {}
    for c in df.columns:
        d0 = a[c].mean() - b[c].mean()
        boots = [rng.choice(a[c].to_numpy(), a.shape[0]).mean() - rng.choice(b[c].to_numpy(), b.shape[0]).mean()
                 for _ in range(n)]
        out[c] = {"delta": float(d0), "ic95": [float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))],
                  "media_antes": float(df.loc[b.index, c].mean())}
    if "f_ir" not in df:
        return out, an
    dd = (a["f_ir"].mean() - b["f_ir"].mean()) - (a["f_mw"].mean() - b["f_mw"].mean())
    bo = []
    for _ in range(n):
        ia, ib = rng.integers(0, a.shape[0], a.shape[0]), rng.integers(0, b.shape[0], b.shape[0])
        bo.append((a["f_ir"].to_numpy()[ia].mean() - b["f_ir"].to_numpy()[ib].mean())
                  - (a["f_mw"].to_numpy()[ia].mean() - b["f_mw"].to_numpy()[ib].mean()))
    out["ir_menos_mw"] = {"delta": float(dd), "ic95": [float(np.percentile(bo, 2.5)), float(np.percentile(bo, 97.5))]}
    return out, an


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / "predicciones_registradas.json"
    if not p.exists():
        write_json(p, {"registradas_utc": datetime.now(timezone.utc).isoformat(), **PREDICCIONES})
    descargar()
    A, days, lat, lon = leer()
    cells = datos.cells_table()
    inc = cells["incluida"].fillna(False).astype(bool).to_numpy().reshape(datos.GRID01.ny, datos.GRID01.nx)
    assert A["precipitation"].shape[1:] == inc.shape, (A["precipitation"].shape, inc.shape)
    rng = np.random.default_rng(SEED)
    res, anoms = {}, {}
    era5 = json.loads((ROOT / "results" / "tropical" / "era5" / "resumen.json").read_text(encoding="utf-8"))["puntos"]
    zonas = {"nacional": inc}
    for nombre, c in era5.items():
        la, lo = c["devuelta"]
        m = (np.abs(lat[:, None] - la) <= 0.125) & (np.abs(lon[None, :] - lo) <= 0.125)
        zonas[nombre] = m & inc if (m & inc).any() else m
    for z, mask in zonas.items():
        res[z], anoms[z] = delta(mensual(A, days, mask), rng)
    anoms["nacional"].to_csv(OUT / "anomalias_mensuales_nacional.csv", float_format="%.5f")
    # control H1 con CHIRPS (motor P0)
    Pc = np.load(datos.DER / "chirps_diario_01.npz")["P"]
    dP = pd.DatetimeIndex(datos.DAYS.astype("datetime64[D]"))
    sel = (dP >= "2016-01-01") & (dP <= "2019-12-31")
    wc = pd.Series(np.nanmean(Pc[sel][:, inc] >= 1, 1), index=dP[sel]).groupby(dP[sel].to_period("M")).mean()
    wi = pd.Series(np.nanmean(A["precipitation"][:, inc] >= 1, 1), index=days).groupby(days.to_period("M")).mean()
    h1, _ = delta(pd.DataFrame({"IMERG_menos_CHIRPS": wi - wc}), rng)
    n = res["nacional"]
    ver = {"H1": bool(h1["IMERG_menos_CHIRPS"]["delta"] < 0),
           "H2": bool(n["ir_menos_mw"]["ic95"][1] < 0),
           "H3": bool(abs(n["cob"]["delta"]) / n["cob"]["media_antes"] < 0.10)}
    write_json(OUT / "resumen.json", {"antes": ANTES, "despues": DESPUES, "control_H1": h1, "zonas": res,
                                      "n_dias": int(len(days)), "veredicto": ver})
    print(json.dumps({"control_H1": h1, "nacional": n, "veredicto": ver}, indent=1, ensure_ascii=False))
    filas = [{"zona": z, **{f"d_{k}": v["delta"] for k, v in r.items()},
              "ir_menos_mw_ic_hi": r["ir_menos_mw"]["ic95"][1]} for z, r in res.items()]
    pd.DataFrame(filas).to_csv(OUT / "deltas_por_zona.csv", index=False, float_format="%.5f")
    print(pd.DataFrame(filas).round(4).to_string())


if __name__ == "__main__":
    main()
