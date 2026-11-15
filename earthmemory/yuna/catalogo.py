"""Catálogo de eventos 2001-2025 (cuenca del Yuna) y marcadores de operación de Hatillo, con fuentes.

Fuente de entrada: earthmemory/yuna/catalogo_fuentes.json (investigación web del 2026-11-14; cada fuente marcada
«(leido)» si la página se abrió y leyó, o «(solo_busqueda)» si el dato salió del resumen del buscador).
Nada se agrega aquí que no esté en ese archivo. EM-DAT (requiere cuenta), DesInventar (RD solo 1966-2000),
DFO (páginas 404) y ReliefWeb (403 al acceso automático) no se pudieron consultar directamente.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

from .common import RES, YEARS

FUENTE = Path(__file__).with_name("catalogo_fuentes.json")
ZONAS_CUENCA = {"bajo_yuna", "alto_yuna", "camu", "cuenca_general"}


def cargar() -> dict:
    return json.loads(FUENTE.read_text(encoding="utf-8"))


def construir(guardar: bool = True) -> pd.DataFrame:
    d = cargar()
    filas = []
    for e in d["eventos"]:
        fu = e.get("fuentes", [])
        leidas = sum("(leido)" in (f.get("nota") or "") for f in fu)
        ini, fin = pd.Timestamp(e["fecha_inicio"]), pd.Timestamp(e["fecha_fin"])
        en_rango = YEARS[0] <= ini.year <= YEARS[1]
        en_cuenca = e["zona"] in ZONAS_CUENCA
        motivo = []
        if not en_cuenca:
            motivo.append("no es evento de inundación en la cuenca" if e["zona"] == "hatillo_operacion"
                          else "fuera de la cuenca")
        if not en_rango:
            motivo.append(f"fuera de {YEARS[0]}-{YEARS[1]} (sin IMERG diario local)")
        if e["fecha_precision"] == "mes":
            motivo.append("fecha solo al mes")
        filas.append({
            "id": e["id"], "inicio": ini.date(), "fin": fin.date(), "precision": e["fecha_precision"],
            "nombre": e["nombre"], "zona": e["zona"], "lugares": "; ".join(e.get("lugares", [])),
            "impacto": e.get("impacto", ""), "confianza": e["confianza"],
            "n_fuentes": len(fu), "n_fuentes_leidas": leidas,
            "fuentes_url": " | ".join(f["url"] for f in fu),
            "hatillo_menciones": e.get("hatillo_menciones", ""),
            "usable_backtest": en_cuenca and en_rango and e["fecha_precision"] != "mes",
            "motivo_exclusion": "; ".join(motivo),
        })
    # Precedente fuera de la cuenca: Tavera (Yaque del Norte) durante Olga, dic-2007
    tav = d.get("tavera_olga_2007", "")
    urls = re.findall(r"https?://[^\s;)]+", tav)
    filas.append({"id": "PRECEDENTE-Tavera-2007-12", "inicio": pd.Timestamp("2007-12-11").date(),
                  "fin": pd.Timestamp("2007-12-13").date(), "precision": "dia",
                  "nombre": "Olga: apertura de las compuertas de Tavera (Yaque del Norte, Santiago)",
                  "zona": "fuera_yuna_precedente_presa", "lugares": "Santiago; Yaque del Norte",
                  "impacto": "Apertura de compuertas hacia la medianoche del 11 al 12-dic-2007; ~20 muertes atribuidas a "
                             "la descarga (Wikipedia); caudales citados no fiables (300 a >5.200 m3/s); polémica sobre si "
                             "se abrió tarde.", "confianza": "media", "n_fuentes": len(urls),
                  "n_fuentes_leidas": None, "fuentes_url": " | ".join(urls), "hatillo_menciones": "",
                  "usable_backtest": False, "motivo_exclusion": "otra cuenca (precedente de operación de presa)"})
    cat = pd.DataFrame(filas)
    if guardar:
        RES.mkdir(parents=True, exist_ok=True)
        cat.to_csv(RES / "catalogo_eventos.csv", index=False)
        h = d["hatillo"]
        (RES / "hatillo_ficha.json").write_text(json.dumps(h, ensure_ascii=False, indent=1), encoding="utf-8")
    return cat


def ventanas(cat: pd.DataFrame, zonas: set | None = None) -> list[tuple[pd.Timestamp, pd.Timestamp, str]]:
    c = cat[cat["usable_backtest"]]
    if zonas:
        c = c[c["zona"].isin(zonas)]
    return [(pd.Timestamp(r.inicio), pd.Timestamp(r.fin), r.id) for r in c.itertuples()]
