"""Todo Earth Memory nacional con un comando (lo que corre `docker compose run --rm nacional`):

1. descarga con caché (límites, IMERG mensual/diario/media hora, GLDAS + su lluvia de forzamiento) si hay token;
2. motor de comprobación NASA POWER/MERRA-2 (results/nacional/power_merra2/);
3. motor principal IMERG + GLDAS (results/, figures/, reports_nacional/EARTH_MEMORY.md, DATA_DICTIONARY.md);
4. cuadernos ejecutados sin pantalla y exportados a HTML.

Argumentos comunes: --pais ISO3 (geoBoundaries), --anio0, --anio1, --bbox LON0 LAT0 LON1 LAT1, --sin-descarga,
--sin-power, --sin-cuadernos. El resto pasa tal cual al motor principal (p. ej. --B 2000).
"""

from __future__ import annotations

import argparse

from . import download, nacional, notebooks, pipeline


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pais", default="DOM")
    ap.add_argument("--anio0", type=int, default=2001)
    ap.add_argument("--anio1", type=int, default=2024)
    ap.add_argument("--bbox", nargs=4, type=float, default=None)
    ap.add_argument("--sin-descarga", dest="sin_descarga", action="store_true")
    ap.add_argument("--sin-power", dest="sin_power", action="store_true")
    ap.add_argument("--sin-cuadernos", dest="sin_cuadernos", action="store_true")
    a, rest = ap.parse_known_args(argv)
    common = ["--pais", a.pais, "--anio0", str(a.anio0), "--anio1", str(a.anio1)]
    if not a.sin_descarga:
        print("== 1/4 descargas (caché)", flush=True)
        download.main(common + (["--bbox", *map(str, a.bbox)] if a.bbox else []))
    if not a.sin_power:
        print("== 2/4 comprobación NASA POWER (MERRA-2)", flush=True)
        pipeline.main(common)
    print("== 3/4 motor principal IMERG + GLDAS", flush=True)
    nacional.main(common + rest)
    if not a.sin_cuadernos and a.pais == "DOM":
        print("== 4/4 cuadernos", flush=True)
        notebooks.build_and_run()


if __name__ == "__main__":
    main()
