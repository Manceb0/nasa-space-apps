"""Galería de figuras de impacto (Evidence Intelligence) · punto de entrada.

    docker compose run --rm galeria                     # todas las piezas, tema oscuro y claro
    docker compose run --rm galeria --solo 1 3          # solo algunas piezas
    docker compose run --rm galeria --tema dark         # un solo tema

Solo lee data/ y results/ (montados en solo lectura) y escribe en figures/galeria/ (dark/, light/, _datos/,
<pieza>.json de procedencia y <pieza>.alt.txt).
"""

from __future__ import annotations

import argparse
import importlib
import json
import time

from .estilo import OUT, aplicar, TEMAS

PIEZAS = {"1": "f1_codigo_barras", "1b": "f1b_yuna_atlas", "2": "f2_espiral", "3": "f3_relieve",
          "4": "f4_genealogia", "5": "f5_bivariado", "6": "f6_tormenta"}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--solo", nargs="*", default=None)
    ap.add_argument("--tema", choices=list(TEMAS), nargs="*", default=None)
    a = ap.parse_args(argv)
    (OUT / "_datos").mkdir(parents=True, exist_ok=True)
    resumen = {}
    for k in a.solo or list(PIEZAS):
        t0 = time.time()
        try:
            mod = importlib.import_module(f".{PIEZAS[k]}", __package__)
        except ModuleNotFoundError:
            print(f"[galeria] pieza {k}: módulo no disponible", flush=True)
            continue
        aplicar(TEMAS["dark"])
        res = mod.run(a.tema)
        resumen[PIEZAS[k]] = {"archivos": res["archivos"], "segundos": round(time.time() - t0, 1)}
        print(f"[galeria] pieza {k} ({PIEZAS[k]}) lista en {time.time() - t0:.0f} s", flush=True)
    p = OUT / "_datos" / "ultima_corrida.json"
    prev = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    prev.update(resumen)
    p.write_text(json.dumps(prev, ensure_ascii=False, indent=1), encoding="utf-8")
    print("[galeria] listo", flush=True)


if __name__ == "__main__":
    main()
