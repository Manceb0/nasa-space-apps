"""JSON para las pantallas (results/tendencias/web/). Esquema en results/tendencias/web/CONTRATO.md."""

from __future__ import annotations

import json
import math

import numpy as np
import pandas as pd

from ..hr.common import ROOT
from . import datos
from . import estadistica as st
from . import indices as ix
from .motor import NATIONAL, PRODUCTS

WEB = ROOT / "results" / "tendencias" / "web"
VERSION = "1.0"
CLASSES = {
    "robusta": ("Robusta", "Robust", "#0072B2", "Los dos productos muestran tendencia significativa (FDR q ≤ 0.10) en la misma dirección."),
    "consistente": ("Consistente", "Consistent", "#56B4E9", "Misma dirección en los dos; solo uno es significativo."),
    "en disputa": ("En disputa", "Disputed", "#D55E00", "Direcciones opuestas y al menos uno significativo: las fuentes no están de acuerdo."),
    "sin señal detectable": ("Sin señal detectable", "No detectable signal", "#E6E6E6",
                             "Ninguno significativo. Con 24 años no se puede detectar; no quiere decir que no haya cambio."),
}


def r(v, nd=4):
    """Redondeo a nd cifras significativas; NaN → None."""
    if v is None:
        return None
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(v):
        return None
    if v == 0:
        return 0.0
    return float(f"{v:.{nd}g}")


def dump(name: str, obj) -> int:
    WEB.mkdir(parents=True, exist_ok=True)
    s = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    (WEB / name).write_text(s, encoding="utf-8")
    return len(s.encode("utf-8"))


def _trend_obj(t) -> dict:
    return {"pendiente_decada": r(t["pendiente_decada"]), "ic95": [r(t["ic95_inf"]), r(t["ic95_sup"])], "p": r(t["p"], 3),
            "q": r(t["q_fdr"], 3), "sig": bool(t["sig_fdr"]) if pd.notna(t["q_fdr"]) else None,
            "sig_p05": bool(t["p"] < 0.05) if pd.notna(t["p"]) else None,
            "mdt": r(t["mdt"], 3), "media": r(t["media"]), "detectable": bool(t["detectable"]),
            "pendiente_pct_decada": r(t["pendiente_pct_decada"], 3)}


def export(state: dict, summ: pd.DataFrame) -> None:
    out = state["out"]
    tc, tr, sr = out["celdas"], out["regiones"], out["series_regiones"]
    prods = list(state["series"])
    keys = sorted({(i, p) for i, p in zip(tc["indice"], tc["periodo"])}, key=lambda k: (list(ix.VARIABLES).index(k[0]), list(ix.PERIODS).index(k[1])))
    sizes = {}
    # ---------------------------------------------------------------- variables.json
    var_list = []
    for vid, (les, len_, unit, desc, why) in ix.VARIABLES.items():
        pers = [p for (i, p) in keys if i == vid]
        if not pers:
            continue
        var_list.append({"id": vid, "label_es": les, "label_en": len_, "unidad": unit, "unidad_tendencia": f"{unit}/década",
                         "descripcion": desc, "por_que_importa": why, "tipo": "seco" if vid in {"CDD", "RACHAS10", "RACHAS15"} or vid.startswith("SPI") else "humedo",
                         "aumento_significa": "más seco" if vid in {"CDD", "RACHAS10", "RACHAS15"} or vid.startswith("SPI") else "más lluvia / más extremo",
                         "periodos": pers, "grupo": "sequia" if vid.startswith("SPI") else ("periodos_secos" if vid in {"CDD", "RACHAS10", "RACHAS15"} else "lluvia")})
    meta = {"version": VERSION, "generado_utc": state["fecha_utc"], "anios": list(datos.YEARS),
            "productos": {p: {**PRODUCTS[p]} for p in prods},
            "periodos": {k: {"label_es": v[0], "label_en": v[1], "meses": v[2]} for k, v in ix.PERIODS.items()},
            "clases": {k: {"label_es": a, "label_en": b, "color": c, "descripcion": d} for k, (a, b, c, d) in CLASSES.items()},
            "umbral_significancia": {"q_fdr": st.ALPHA_FDR, "regla": "FDR de Benjamini-Hochberg con α_FDR = 2·α_global (Wilks 2016), α_global = 0.05"},
            "prueba": "Mann-Kendall modificado de Hamed y Rao (1998) + pendiente de Theil-Sen (IC 95 % de Sen)",
            "nota_causalidad": "Las tendencias describen cambios observados 2001-2024; no atribuyen causas.",
            "variables": var_list}
    sizes["variables.json"] = dump("variables.json", meta)
    # ---------------------------------------------------------------- provincias.json
    codes = tr.drop_duplicates("region").set_index("region")["codigo"]
    regs = [NATIONAL] + sorted(x for x in codes.index if x != NATIONAL)
    series, trends, years = {}, {}, {}
    sr_g = {k: g for k, g in sr.groupby(["indice", "periodo", "fuente"])}
    tr_g = {k: g.set_index("region") for k, g in tr.groupby(["indice", "periodo", "fuente"])}
    for idx, per in keys:
        series.setdefault(idx, {})[per] = {}
        trends.setdefault(idx, {})[per] = {}
        for prod in prods:
            g = sr_g[(idx, per, prod)]
            yrs = sorted(g["anio"].unique())
            years[f"{idx}|{per}"] = [int(y) for y in yrs]
            piv = g.pivot(index="anio", columns="region", values="valor").reindex(yrs)
            series[idx][per][prod] = {codes[rg]: [r(v) for v in piv[rg].to_numpy()] for rg in regs}
        for rg in regs:
            o = {}
            for prod in prods:
                t = tr_g[(idx, per, prod)].loc[rg]
                o[prod] = _trend_obj(t)
                o["clase"] = t["clase_confianza"]
            trends[idx][per][codes[rg]] = o
    # años por periodo (iguales para todos los índices diarios; SPI empieza en 2002)
    anios = {}
    for k, v in years.items():
        anios.setdefault(k.split("|")[1] if not k.startswith("SPI") else "spi", v)
    prov = {"version": VERSION, "regiones": [{"id": codes[rg], "nombre": rg, "es_nacional": rg == NATIONAL} for rg in regs],
            "anios": {"anual": anios.get("anual"), "seca": anios.get("seca"), "humeda_temprana": anios.get("humeda_temprana"),
                      "humeda_tardia": anios.get("humeda_tardia"), "spi": anios.get("spi")},
            "nota_anios": "Índices diarios: 'anual', 'humeda_temprana' y 'humeda_tardia' 2001-2024; 'seca' 2002-2024 (dic del año anterior a abr); índices SPI* (periodo 'anual') 2002-2024 → usar anios.spi.",
            "series": series, "tendencias": trends}
    sizes["provincias.json"] = dump("provincias.json", prov)
    # ---------------------------------------------------------------- rejilla.json
    G = datos.GRID01
    cells = state["S"]["cells"]
    inc_c = cells[state["S"]["inc"]]
    ii = np.round((inc_c["lat"].to_numpy() - G.lat[0]) / G.res).astype(int)
    jj = np.round((inc_c["lon"].to_numpy() - G.lon[0]) / G.res).astype(int)
    flat = ii * G.nx + jj
    pos = dict(zip(inc_c["celda"], flat))
    inc_mask = np.zeros(G.ny * G.nx, int)
    inc_mask[flat] = 1
    prov_main = [None] * (G.ny * G.nx)
    for c, p in zip(inc_c["celda"], inc_c["provincia_principal"]):
        prov_main[pos[c]] = codes.get(p) if isinstance(p, str) else None
    class_codes = list(CLASSES)
    layers = {}
    tc_g = {k: g for k, g in tc.groupby(["indice", "periodo", "fuente"])}
    for idx, per in keys:
        lay = {}
        for prod in prods:
            g = tc_g[(idx, per, prod)]
            k = g["celda"].map(pos).to_numpy()
            sl = [None] * (G.ny * G.nx)
            qq = [None] * (G.ny * G.nx)
            for kk, v, q in zip(k, g["pendiente_decada"], g["q_fdr"]):
                sl[kk] = r(v, 3)
                qq[kk] = r(q, 2)
            lay[prod] = {"pendiente_decada": sl, "q": qq}
        cl = [None] * (G.ny * G.nx)
        g = tc_g[(idx, per, prods[0])]
        for kk, c in zip(g["celda"].map(pos), g["clase_confianza"]):
            cl[kk] = class_codes.index(c) if c in class_codes else None
        lay["clase"] = cl
        layers.setdefault(idx, {})[per] = lay
    grid = {"version": VERSION, "resolucion_grados": G.res, "lat": [r(v, 6) for v in G.lat], "lon": [r(v, 6) for v in G.lon],
            "lat_bordes": [r(v, 6) for v in G.lat_edges], "lon_bordes": [r(v, 6) for v in G.lon_edges],
            "nx": G.nx, "ny": G.ny,
            "orden": "lista plana de ny*nx valores; k = fila*nx + col; fila 0 = latitud más al SUR (lat[0]), col 0 = más al OESTE (lon[0])",
            "incluida": inc_mask.tolist(), "provincia_principal": prov_main, "clases_codigo": class_codes,
            "capas": layers}
    sizes["rejilla.json"] = dump("rejilla.json", grid)
    # ---------------------------------------------------------------- resumen.json
    cal = state["cal"]
    calc = cal[cal["nivel"] == "celdas"]
    calp = cal[cal["nivel"] == "provincias"]
    res = {"version": VERSION, "generado_utc": state["fecha_utc"],
           "calibracion": {"fpr_nominal": 0.05,
                           "fpr_local_celdas_fases": r(calc[calc["metodo"].str.startswith("fases")]["fpr_local_p05"].mean(), 3),
                           "fpr_local_celdas_bloques": r(calc[~calc["metodo"].str.startswith("fases")]["fpr_local_p05"].mean(), 3),
                           "fpr_local_provincias_fases": r(calp[calp["metodo"].str.startswith("fases")]["fpr_local_p05"].mean(), 3),
                           "fpr_local_provincias_bloques": r(calp[~calp["metodo"].str.startswith("fases")]["fpr_local_p05"].mean(), 3),
                           "fraccion_mapas_nulos_con_celda_fdr_media": r(calc["fraccion_mapas_nulos_con_celda_fdr"].mean(), 3),
                           "n_sustitutos": int(state["n_sustitutos"])},
           "indices": []}
    for _, row in summ.iterrows():
        res["indices"].append({k: (r(v) if isinstance(v, (float, np.floating)) else (bool(v) if isinstance(v, (bool, np.bool_)) else (int(v) if isinstance(v, (np.integer,)) else v)))
                               for k, v in row.items()})
    sizes["resumen.json"] = dump("resumen.json", res)
    total = sum(sizes.values())
    sizes["TOTAL"] = total
    (WEB / "tamanos.json").write_text(json.dumps(sizes, indent=1), encoding="utf-8")
    print(f"[web] {sizes}", flush=True)
    if total > 6e6:
        print("[web] AVISO: más de 6 MB", flush=True)
