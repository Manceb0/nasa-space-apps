"""Variante «sin el escalón de 2013-10» para la vista de Tendencias (web/public/data/tendencias/sin_escalon.json).

No calcula nada: reordena results/tropical/recalculo/ (variante A_frec, producida por el chat de datos con el mismo
motor P0) en la forma de rejilla.json, solo para los índices de frecuencia e intensidad, donde IMERG cambió en
2013-10 su forma de contar días de lluvia. Comprueba con assert:
  · que la celda→índice es la misma que la de rejilla.json (los índices sin corregir dan la misma clase y la misma q),
  · que los recuentos por índice y época son los de comparacion_clases.csv y el total el de resumen.json.

    MSYS_NO_PATHCONV=1 docker compose run --rm -v "$(pwd -W)/web:/app/web" -v "$(pwd -W)/results:/app/results:ro" \
      -v "$(pwd -W)/figures:/app/figures:ro" --entrypoint "uv run --frozen --no-sync python web/scripts/exportar_sin_escalon.py" galeria
"""

from __future__ import annotations

import json
import math
import shutil
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
REC = ROOT / "results/tropical/recalculo"
OUT = ROOT / "web/public/data/tendencias/sin_escalon.json"
FIG = ROOT / "web/public/figuras"
FRECUENCIA = ["R1mm", "SDII", "CDD", "CWD", "RACHAS10", "RACHAS15"]
SIN_CORREGIR = ["PRCPTOT", "R20mm", "Rx1day"]


def r(v, d=4):
    return None if v is None or (isinstance(v, float) and math.isnan(v)) else round(float(v), d)


def main() -> None:
    R = json.loads((ROOT / "web/public/data/tendencias/rejilla.json").read_text(encoding="utf-8"))
    codes = R["clases_codigo"]
    nx = R["nx"]
    lat = [round(v, 3) for v in R["lat"]]
    lon = [round(v, 3) for v in R["lon"]]
    df = pd.read_csv(REC / "tendencias_celdas_A_frec.csv", encoding="utf-8")
    df["k"] = [lat.index(round(a, 3)) * nx + lon.index(round(b, 3)) for a, b in zip(df["lat"], df["lon"])]
    n = len(R["incluida"])

    def layer(ind: str, per: str):
        sub = df[(df["indice"] == ind) & (df["periodo"] == per)]
        im = sub[sub["fuente"] == "IMERG"].set_index("k")
        cl: list[int | None] = [None] * n
        pend: list[float | None] = [None] * n
        q: list[float | None] = [None] * n
        for k, row in im.iterrows():
            cl[k] = codes.index(row["clase_confianza"])
            pend[k] = r(row["pendiente_decada"])
            q[k] = r(row["q_fdr"])
        return cl, pend, q, im

    # 1) El mapeo celda→índice es el de rejilla.json: en los índices que no se corrigen, todo coincide
    for ind in SIN_CORREGIR:
        for per in R["capas"][ind]:
            cl, _, q, _ = layer(ind, per)
            pub = R["capas"][ind][per]
            assert cl == pub["clase"], (ind, per, "clase")
            dq = [abs(a - b) for a, b in zip(q, pub["IMERG"]["q"]) if a is not None and b is not None]
            assert max(dq) < 5e-3, (ind, per, "q", max(dq))  # rejilla.json redondea a 3 cifras significativas
            _, pend, _, _ = layer(ind, per)
            dp = [abs(a - b) / max(abs(b), 1e-9) for a, b in zip(pend, pub["IMERG"]["pendiente_decada"]) if a is not None and b is not None and abs(b) > 0.05]
            assert max(dp) < 0.01, (ind, per, "pendiente", max(dp))

    # 2) Las capas corregidas y sus recuentos, contra comparacion_clases.csv y resumen.json
    comp = pd.read_csv(REC / "comparacion_clases.csv", header=[0, 1], index_col=[0, 1], encoding="utf-8")
    resumen = json.loads((REC / "resumen.json").read_text(encoding="utf-8"))
    capas, recuentos, total = {}, {}, 0
    for ind in FRECUENCIA:
        capas[ind], recuentos[ind] = {}, {}
        for per in R["capas"][ind]:
            cl, pend, q, im = layer(ind, per)
            antes = sum(1 for c in R["capas"][ind][per]["clase"] if c is not None and codes[c] == "en disputa")
            despues = sum(1 for c in cl if c is not None and codes[c] == "en disputa")
            assert despues == int(comp.loc[(ind, per), ("A_frec", "en disputa")]), (ind, per)
            assert antes == int(comp.loc[(ind, per), ("original", "en disputa")]), (ind, per, "original")
            total += despues
            capas[ind][per] = {"IMERG": {"pendiente_decada": pend, "q": q}, "clase": cl}
            recuentos[ind][per] = {"en_disputa_publicado": antes, "en_disputa_sin_escalon": despues}
    nac = pd.read_csv(REC / "nacional_IMERG_foco.csv", encoding="utf-8")
    nacional = {}
    for _, row in nac[nac["variante"].isin(["original", "A_frec"])].iterrows():
        if row["indice"] not in FRECUENCIA:
            continue
        nacional.setdefault(row["indice"], {}).setdefault(row["periodo"], {})[
            "publicado" if row["variante"] == "original" else "sin_escalon"] = {
            "pendiente_decada": r(row["pendiente_decada"]), "pendiente_pct_decada": r(row["pendiente_pct_decada"], 2),
            "p": r(row["p"]), "clase": row["clase_confianza"]}
    sens = pd.read_csv(REC / "sensibilidad_corte.csv", encoding="utf-8")
    doc = {
        "fuente": "results/tropical/recalculo/ (variante A_frec, corte " + str(resumen["corte"]) + ", commit 317724b)",
        "indices": FRECUENCIA, "corte": resumen["corte"],
        "total_en_disputa": {"publicado": resumen["total_en_disputa"]["original"], "sin_escalon": resumen["total_en_disputa"]["A_frec"]},
        "recuentos": recuentos, "nacional_IMERG": nacional,
        "sensibilidad_corte": sens.to_dict(orient="records"),
        "capas": capas,
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    FIG.mkdir(parents=True, exist_ok=True)
    for f in ["07_the_step_in_2013_dark.png", "08_after_the_correction_dark.png"]:
        shutil.copy2(ROOT / "figures/tropical" / f, FIG / f)
    print(OUT, f"{OUT.stat().st_size / 1024:.0f} KB", "en disputa (frecuencia):", total,
          "· total del recálculo:", resumen["total_en_disputa"])


if __name__ == "__main__":
    main()
