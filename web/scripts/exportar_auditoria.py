"""Datos de la pantalla Auditoría (web/public/data/auditoria/) y figuras de la galería (web/public/figuras/).

No calcula nada nuevo: reordena lo que ya producen los motores y la galería, y comprueba con assert que los recuentos
son los mismos que los de figures/galeria/01_barcode_of_doubt.json.

    docker compose run --rm -v "$PWD/web:/app/web" -v "$PWD/figures:/app/figures:ro" \
      --entrypoint "uv run --frozen --no-sync python web/scripts/exportar_auditoria.py" galeria
"""

from __future__ import annotations

import json
import math
import shutil
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
GAL = ROOT / "figures/galeria"
AUD = ROOT / "results/auditoria"
OUT = ROOT / "web/public/data/auditoria"
FIG = ROOT / "web/public/figuras"
PRODUCTOS = ["IMERG", "CHIRPS", "GLDAS_forzamiento", "MERRA2"]
ESTADOS = {-1: "no_data", 0: "no_alarm", 1: "split", 2: "majority", 3: "unanimous", 4: "contradiction"}
PIEZAS = ["01b_yuna_flood_atlas.png", "01c_yuna_flood_recurrence.png", "04_genealogy_of_the_data.png",
          "05_bivariate_where_to_measure.png", "06_santo_domingo_storm.gif", "06_santo_domingo_storm_keyframes.png"]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)
    E = pd.read_csv(GAL / "_datos/estados_acuerdo_provincia_mes.csv", index_col=0, encoding="utf-8")
    spi = pd.read_parquet(GAL / "_datos/spi3_provincias.parquet")
    prov = pd.read_csv(AUD / "cambio_decision_sequia_provincias.csv", encoding="utf-8")
    prov = prov[prov["umbral_spi3"] == -1].set_index("provincia")
    orden = prov.sort_values(["tasa_condicional", "n_no_unanime"], ascending=[False, False]).index.tolist()
    meses = [m[:7] for m in E.index]
    ref = json.loads((GAL / "01_barcode_of_doubt.json").read_text(encoding="utf-8"))["numeros_codificados"]
    M = E[orden]
    for k, name in ESTADOS.items():
        assert int((M.to_numpy() == k).sum()) == ref[name], (name, int((M.to_numpy() == k).sum()), ref[name])

    def r2(v: float):
        return None if v is None or (isinstance(v, float) and math.isnan(v)) else round(float(v), 2)

    piv = {p: spi[spi["producto"] == p].pivot(index="mes", columns="provincia", values="spi3") for p in PRODUCTOS}
    filas = []
    for p in orden:
        r = prov.loc[p]
        filas.append({
            "provincia": p, "codigo": r["codigo"],
            "tasa_condicional": round(float(r["tasa_condicional"]), 4),
            "ic95": [round(float(r["ic95_condicional_bajo"]), 4), round(float(r["ic95_condicional_alto"]), 4)],
            "tasa_contradiccion_clara": round(float(r["tasa_contradiccion_clara"]), 4),
            "n_alguna_alarma": int(r["n_alguna_alarma"]), "n_no_unanime": int(r["n_no_unanime"]),
            "estados": [int(x) for x in M[p].tolist()],
            "spi3": {k: [r2(v) for v in piv[k][p].tolist()] for k in PRODUCTOS},
        })
    doc = {
        "fuente": "figures/galeria/_datos (pieza 01, commit 3ef9c74) y results/auditoria/cambio_decision_sequia_provincias.csv",
        "umbral_spi3": -1.0, "productos": PRODUCTOS, "meses": meses,
        "codigos": {str(k): v for k, v in ESTADOS.items()},
        "recuentos": {k: ref[k] for k in ["unanimous", "majority", "split", "contradiction", "no_alarm", "no_data",
                                           "n_casos", "n_alguna_alarma", "n_no_unanime"]},
        "nacional": ref["auditoria_nacional"],
        "por_anio_unanime": ref["por_anio_unanime"],
        "filas": filas,
    }
    (OUT / "codigo_barras.json").write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    for f in ["procedencia.json", "donde_medir_prototipo.json", "CONTRATO.md"]:
        shutil.copy2(AUD / "web" / f, OUT / f)
    for f in PIEZAS:
        shutil.copy2(GAL / "dark" / f, FIG / f)
    alt = {}
    for f in GAL.glob("*.alt.txt"):
        t = f.read_text(encoding="utf-8")
        alt[f.name.replace(".alt.txt", "")] = {k: t.split(f"{k.upper()}:", 1)[1].split("\n\n")[0].strip() for k in ["es", "en"] if f"{k.upper()}:" in t}
    (FIG / "alt.json").write_text(json.dumps(alt, ensure_ascii=False, indent=1), encoding="utf-8")
    nums = {f.stem: json.loads(f.read_text(encoding="utf-8")).get("numeros_codificados", {}) for f in GAL.glob("0*.json")}
    (FIG / "numeros.json").write_text(json.dumps(nums, ensure_ascii=False), encoding="utf-8")
    print(OUT / "codigo_barras.json", f"{(OUT / 'codigo_barras.json').stat().st_size / 1024:.0f} KB", len(filas), "provincias ×", len(meses), "meses")


if __name__ == "__main__":
    main()
