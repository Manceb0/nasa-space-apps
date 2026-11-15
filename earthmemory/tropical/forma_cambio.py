"""¿Tendencia, escalón, ambos o nada? Forma temporal de la diferencia de días húmedos IMERG − CHIRPS.

Por celda (442) y para la serie nacional: frecuencia mensual de días ≥ 1 mm, IMERG − CHIRPS, sin ciclo estacional.
Cuatro modelos con errores AR(1) (Prais-Winsten, verosimilitud gaussiana exacta):
  M0 constante · M1 tendencia lineal · M2 escalón en fecha libre · M3 tendencia + escalón en fecha libre.
La fecha del escalón NO se impone: se busca en toda la serie (12 meses de margen) y cuenta como un parámetro más.
Se elige por BIC. Si el mejor modelo con cambio y otro de FORMA distinta quedan a menos de 2 unidades de BIC, el
resultado es «indistinguibles». Antes de mirar los datos reales se valida el procedimiento con series sintéticas
de ruido AR(1) parecido al observado (sin cambio, tendencia, escalón, ambos) y se registran las predicciones.
Ejecutar: docker compose run --rm --entrypoint uv tropical run --frozen --no-sync python -m earthmemory.tropical.forma_cambio
"""

from __future__ import annotations

from datetime import datetime, timezone

import numpy as np
import pandas as pd

from ..hr.common import ROOT, write_json
from .run import SEED, load

OUT = ROOT / "results" / "tropical" / "forma"
MARGEN = 12
DBIC = 2.0
MODELOS = ("sin cambio", "tendencia", "escalón", "tendencia + escalón")
PREDICCIONES = {
    "F1": "Validación: con ruido como el de una celda y un cambio total de 4,5 pp, el procedimiento acierta la forma "
          "(tendencia / escalón / ambos) en al menos el 60 % de las series sintéticas con cambio. Si no, la forma por "
          "celda se declara no identificable con estos datos.",
    "F2": "Serie nacional: el escalón NO gana con claridad (ΔBIC ≥ 2) a la tendencia; el resultado será tendencia, "
          "tendencia + escalón o indistinguibles.",
    "F3": "Entre las celdas donde gana un modelo con escalón, ninguna ventana de 12 meses reúne más del 40 % de las "
          "fechas de escalón (no hay una fecha común).",
}


# ------------------------------------------------------------------ ajuste
def _pw(y, X, phi):
    s = np.sqrt(1 - phi * phi)
    ys = np.r_[s * y[0], y[1:] - phi * y[:-1]]
    Xs = np.vstack([s * X[0], X[1:] - phi * X[:-1]])
    return ys, Xs


def _ll(y, X, phi):
    ys, Xs = _pw(y, X, phi)
    b, *_ = np.linalg.lstsq(Xs, ys, rcond=None)
    e = ys - Xs @ b
    n = y.size
    s2 = max(e @ e / n, 1e-12)
    return -0.5 * n * np.log(2 * np.pi * s2) - 0.5 * n + 0.5 * np.log(1 - phi * phi), b


def _phi(y, X):
    phi = 0.0
    for _ in range(4):
        ys, Xs = _pw(y, X, phi)
        b, *_ = np.linalg.lstsq(Xs, ys, rcond=None)
        r = y - X @ b
        phi = float(np.clip(np.corrcoef(r[1:], r[:-1])[0, 1], -0.95, 0.95))
    return phi


def ajustar(y):
    """Devuelve dict modelo → (BIC, info). y: serie sin ciclo estacional, sin NaN."""
    n = y.size
    t = (np.arange(n) - n / 2) / 120.0                     # décadas
    one = np.ones(n)
    out = {}
    for name, X in (("sin cambio", one[:, None]), ("tendencia", np.c_[one, t])):
        phi = _phi(y, X)
        ll, b = _ll(y, X, phi)
        out[name] = (-2 * ll + (X.shape[1] + 2) * np.log(n), {"phi": phi, "coef": b.tolist()})
    phi_t = _phi(y, np.c_[one, t])
    for name, base in (("escalón", one[:, None]), ("tendencia + escalón", np.c_[one, t])):
        taus = np.arange(MARGEN, n - MARGEN)
        lls = np.array([_ll(y, np.c_[base, (np.arange(n) >= k).astype(float)], phi_t)[0] for k in taus])
        k = int(taus[np.argmax(lls)])
        X = np.c_[base, (np.arange(n) >= k).astype(float)]
        phi = _phi(y, X)
        ll, b = _ll(y, X, phi)
        kpar = X.shape[1] + 3                              # + sigma, phi, fecha
        bic_tau = -2 * lls + kpar * np.log(n)
        cerca = taus[bic_tau - bic_tau.min() < DBIC]
        out[name] = (-2 * ll + kpar * np.log(n),
                     {"phi": phi, "coef": b.tolist(), "tau": k, "tau_rango": [int(cerca.min()), int(cerca.max())]})
    return out


def clasificar(fit):
    bic = {m: fit[m][0] for m in MODELOS}
    orden = sorted(bic, key=bic.get)
    best = orden[0]
    if best == "sin cambio":
        return "sin cambio", bic
    rivales = [m for m in MODELOS if m not in ("sin cambio", best)]
    if min(bic[m] for m in rivales) - bic[best] < DBIC:
        return "indistinguibles", bic
    return best, bic


# ------------------------------------------------------------- validación
def sintetica(clase, delta, phi, sigma, n, rng):
    e = np.empty(n)
    e[0] = rng.normal(0, sigma / np.sqrt(1 - phi * phi))
    for i in range(1, n):
        e[i] = phi * e[i - 1] + rng.normal(0, sigma)
    i = np.arange(n)
    tau = int(rng.integers(60, n - 60))
    if clase == "tendencia":
        s = delta * (i / (n - 1) - 0.5)
    elif clase == "escalón":
        s = delta * (i >= tau)
    elif clase == "tendencia + escalón":
        s = 0.5 * delta * (i / (n - 1) - 0.5) + 0.5 * delta * (i >= tau)
    else:
        s = np.zeros(n)
    return s + e


def validar(phi, sigma, n, etiqueta, rng, reps=150, deltas=(0.02, 0.045, 0.09)):
    rows = []
    for delta in deltas:
        for clase in MODELOS:
            for _ in range(reps):
                pred, _ = clasificar(ajustar(sintetica(clase, delta, phi, sigma, n, rng)))
                rows.append({"ruido": etiqueta, "cambio_total_pp": round(100 * delta, 2), "verdad": clase, "elegido": pred})
    return pd.DataFrame(rows)


# --------------------------------------------------------------------- main
def main():
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / "predicciones_registradas.json"
    if not p.exists():
        write_json(p, {"registradas_utc": datetime.now(timezone.utc).isoformat(), **PREDICCIONES})
    I, C, days, lat, lon, ids, _ = load()
    ym = pd.DatetimeIndex(days.astype("datetime64[D]")).to_period("M")
    wi = pd.DataFrame((I >= 1).astype(float), index=ym).groupby(level=0).mean()
    wc = pd.DataFrame((C >= 1).astype(float), index=ym).groupby(level=0).mean()
    D = wi - wc
    D = D - D.groupby(D.index.month).transform("mean")
    meses = D.index.astype(str)
    n = len(D)
    # ruido observado (de la tendencia por celda) para la validación
    fits, rows = {}, []
    for j in range(D.shape[1]):
        y = D.iloc[:, j].to_numpy()
        if not np.isfinite(y).all():
            continue
        f = ajustar(y)
        fits[j] = f
    phis = np.array([f["tendencia"][1]["phi"] for f in fits.values()])
    sig = []
    for j, f in fits.items():
        y = D.iloc[:, j].to_numpy()
        tt = (np.arange(n) - n / 2) / 120.0
        r = y - np.c_[np.ones(n), tt] @ np.array(f["tendencia"][1]["coef"])
        ph = f["tendencia"][1]["phi"]
        sig.append(np.std(r[1:] - ph * r[:-1]))
    rng = np.random.default_rng(SEED)
    yn = D.mean(1).to_numpy()
    fn = ajustar(yn)
    tn = (np.arange(n) - n / 2) / 120.0
    rn = yn - np.c_[np.ones(n), tn] @ np.array(fn["tendencia"][1]["coef"])
    phn = fn["tendencia"][1]["phi"]
    V = pd.concat([validar(float(np.median(phis)), float(np.median(sig)), n, "celda", rng),
                   validar(phn, float(np.std(rn[1:] - phn * rn[:-1])), n, "nacional", rng)])
    V.to_csv(OUT / "validacion.csv", index=False)
    conf = V.groupby(["ruido", "cambio_total_pp", "verdad"])["elegido"].value_counts(normalize=True).unstack(fill_value=0)
    conf.to_csv(OUT / "validacion_confusion.csv", float_format="%.3f")
    con = V[V["verdad"] != "sin cambio"]
    acierto = (con["verdad"] == con["elegido"]).groupby([con["ruido"], con["cambio_total_pp"]]).mean()
    # datos reales
    for j, f in fits.items():
        cls, bic = clasificar(f)
        best = min(bic, key=bic.get)
        tau = f["escalón"][1]["tau"] if best == "escalón" else (
            f["tendencia + escalón"][1]["tau"] if best == "tendencia + escalón" else None)
        rows.append({"celda": ids[j], "lat": lat[j], "lon": lon[j], "clase": cls, "mejor_bic": best,
                     "fecha_escalon": meses[tau] if tau is not None else "",
                     "pendiente_pp_decada": 100 * f["tendencia"][1]["coef"][1],
                     **{f"bic_{m}": bic[m] for m in MODELOS}})
    T = pd.DataFrame(rows)
    T.to_csv(OUT / "celdas.csv", index=False, float_format="%.5g")
    cls_n, bic_n = clasificar(fn)
    nac = {"clase": cls_n, "bic": bic_n, "delta_bic_vs_mejor": {m: bic_n[m] - min(bic_n.values()) for m in MODELOS},
           "escalon_fecha": meses[fn["escalón"][1]["tau"]],
           "escalon_rango_dbic2": [meses[k] for k in fn["escalón"][1]["tau_rango"]],
           "ambos_fecha": meses[fn["tendencia + escalón"][1]["tau"]],
           "ambos_rango_dbic2": [meses[k] for k in fn["tendencia + escalón"][1]["tau_rango"]],
           "pendiente_pp_decada": 100 * fn["tendencia"][1]["coef"][1], "phi": phn}
    pd.Series(yn, index=meses).to_csv(OUT / "serie_nacional.csv", header=["IMERG_menos_CHIRPS"])
    # veredictos
    a45 = float(acierto.get(("celda", 4.5), np.nan))
    esc = T[T["clase"].isin(["escalón", "tendencia + escalón"])]
    fechas = pd.PeriodIndex(esc["fecha_escalon"], freq="M") if len(esc) else pd.PeriodIndex([], freq="M")
    max_ventana = 0.0
    if len(fechas):
        o = np.sort(fechas.asi8)
        max_ventana = max(np.searchsorted(o, v + 12) - i for i, v in enumerate(o)) / len(o)
    ver = {"F1": bool(a45 >= 0.6), "F2": bool(not (cls_n == "escalón")), "F3": bool(max_ventana <= 0.4)}
    res = {"n_celdas": int(len(T)), "clases_celdas": T["clase"].value_counts().to_dict(),
           "acierto_forma_validacion": {f"{k[0]} {k[1]:g} pp": float(v) for k, v in acierto.items()},
           "falsos_cambios_validacion": V[V["verdad"] == "sin cambio"].groupby("ruido")["elegido"].apply(
               lambda s: float((s != "sin cambio").mean())).to_dict(),
           "phi_mediana_celdas": float(np.median(phis)), "sigma_mediana_celdas": float(np.median(sig)),
           "nacional": nac, "max_frac_fechas_escalon_en_12_meses": max_ventana, "veredicto": ver}
    write_json(OUT / "resumen.json", res)
    import json
    print(json.dumps(res, indent=1, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
