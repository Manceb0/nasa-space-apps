"""Alcance del hallazgo: cuántos trabajos publicados desde 2018 usan IMERG para tendencias, sequía o frecuencia de
lluvia, que son justo las medidas que hereda la pérdida de días de lluvia ligera.

Fuente: OpenAlex (búsqueda en título y resumen, sin cuenta). Es un conteo de menciones, una cota del público
expuesto, no de estudios equivocados: no sabemos cuántos usan días de lluvia ni cuántos cruzan 2018.
Ejecutar: docker compose run --rm --entrypoint uv tropical run --frozen --no-sync python -m earthmemory.tropical.alcance
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from ..hr.common import ROOT, write_json

OUT = ROOT / "results" / "tropical" / "alcance"
DESDE = "2018-01-01"
BUSQUEDAS = ["IMERG", "IMERG trend", "IMERG drought", "IMERG frequency", "IMERG wet days", "IMERG extreme",
             "IMERG Caribbean", "IMERG Dominican", "IMERG Puerto Rico", "IMERG Hawaii"]


def contar(q, solo_articulos):
    f = f"title_and_abstract.search:{q},from_publication_date:{DESDE}" + (",type:article" if solo_articulos else "")
    url = "https://api.openalex.org/works?" + urllib.parse.urlencode({"filter": f, "per-page": 1})
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.load(r)["meta"]["count"], url


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    filas = []
    for q in BUSQUEDAS:
        n_todo, url = contar(q, False)
        n_art, _ = contar(q, True)
        filas.append({"busqueda": q, "trabajos": n_todo, "articulos": n_art, "url": url})
    res = {"consultado_utc": datetime.now(timezone.utc).isoformat(), "fuente": "OpenAlex", "desde": DESDE,
           "nota": "Menciones en título o resumen. Cota del público expuesto, no de estudios afectados.",
           "busquedas": filas}
    write_json(OUT / "openalex.json", res)
    print(json.dumps(res, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
