"""Estilo común de la galería: temas (oscuro para diapositivas, claro para impresión), paletas, cabecera/pie y guardado.

Reglas: cada marca codifica un dato real; escalas honestas; línea de fuente y clave de color siempre visibles.
Paletas seguras para daltonismo: Okabe-Ito (categórica), cividis (secuencial), divergente equilibrada centrada en 0.
Cada figura se guarda como PNG + PDF con metadatos (Description, Source, Software con la nota de asistencia de IA
exigida por las reglas de Space Apps 2026) y un .json de procedencia con entradas (ruta, bytes, SHA-256), cálculo,
números codificados y texto alternativo. Nada de marcas de agua: son gráficos de datos, no imágenes generadas.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import platform
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

OUT = Path("figures/galeria")
DATOS = OUT / "_datos"

SOFTWARE = "matplotlib; figure code written with AI assistance (Claude), data unaltered"
AUTOR = "Stellar Horizons · NASA Space Apps 2026"

# Okabe-Ito
OI = {"orange": "#E69F00", "sky": "#56B4E9", "green": "#009E73", "yellow": "#F0E442", "blue": "#0072B2",
      "vermillion": "#D55E00", "purple": "#CC79A7", "black": "#000000"}

TEMAS = {
    "dark": {"name": "dark", "bg": "#0e1013", "ink": "#e8e8ea", "muted": "#8a8f98", "faint": "#2b3038",
             "panel": "#161a1f", "none": "#1d2229", "cmap_seq": "cividis", "cmap_seq_r": "cividis_r"},
    "light": {"name": "light", "bg": "#ffffff", "ink": "#16181d", "muted": "#5c626c", "faint": "#d5d8dd",
              "panel": "#f3f4f6", "none": "#eceef1", "cmap_seq": "cividis_r", "cmap_seq_r": "cividis"},
}

SLIDE = (13.333, 7.5)       # 16:9
SQUARE = (5.4, 5.4)         # 1080 × 1080 px a 200 dpi
DPI = 200


def aplicar(t: dict) -> None:
    plt.rcdefaults()
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 11,
        "figure.facecolor": t["bg"], "axes.facecolor": t["bg"], "savefig.facecolor": t["bg"],
        "text.color": t["ink"], "axes.labelcolor": t["ink"], "axes.edgecolor": t["muted"],
        "xtick.color": t["muted"], "ytick.color": t["muted"], "xtick.labelcolor": t["muted"],
        "ytick.labelcolor": t["muted"], "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": False, "legend.frameon": False, "pdf.fonttype": 42, "svg.fonttype": "none",
        "path.simplify": True,
    })


def lienzo(t: dict, size=SLIDE):
    aplicar(t)
    return plt.figure(figsize=size, dpi=DPI)


def cabecera(fig, t: dict, titulo: str, subtitulo: str, x: float = 0.045, y: float = 0.935,
             ts: float = 25, ss: float = 13.5) -> None:
    fig.text(x, y, titulo, ha="left", va="top", fontsize=ts, fontweight="bold", color=t["ink"])
    off = (ts * 1.6 / 72) / fig.get_figheight()
    fig.text(x, y - off, subtitulo, ha="left", va="top", fontsize=ss, color=t["muted"], linespacing=1.3)


def pie(fig, t: dict, fuente: str, x: float = 0.045, y: float = 0.03, size: float = 8.5) -> None:
    fig.text(x, y, fuente, ha="left", va="bottom", fontsize=size, color=t["muted"], linespacing=1.35)


def sha256(p: Path, limite: int = 400 * 2**20) -> str | None:
    p = Path(p)
    if not p.exists() or p.is_dir():
        return None
    if p.stat().st_size > limite:
        return None
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(2**20), b""):
            h.update(b)
    return h.hexdigest()


def entrada(p: str | Path, nota: str = "") -> dict:
    p = Path(p)
    files = sorted(p.glob("*")) if p.is_dir() else [p]
    d = {"ruta": str(p).replace("\\", "/"), "nota": nota}
    if p.is_dir():
        d["n_archivos"] = len(files)
        d["bytes"] = int(sum(f.stat().st_size for f in files if f.is_file()))
    elif p.exists():
        d["bytes"] = p.stat().st_size
        d["sha256"] = sha256(p)
    else:
        d["falta"] = True
    return d


def guardar(fig, nombre: str, t: dict, descripcion: str, fuente: str, sufijo: str = "") -> list[str]:
    """PNG + PDF en figures/galeria/<tema>/<nombre><sufijo>.*, con metadatos. Devuelve las rutas."""
    d = OUT / t["name"]
    d.mkdir(parents=True, exist_ok=True)
    base = d / f"{nombre}{sufijo}"
    png_meta = {"Title": nombre, "Author": AUTOR, "Description": descripcion, "Source": fuente,
                "Software": SOFTWARE, "Comment": "Data plot; every mark encodes real data. No generative imagery."}
    fig.savefig(base.with_suffix(".png"), dpi=DPI, metadata=png_meta, facecolor=t["bg"])
    pdf_meta = {"Title": nombre, "Author": AUTOR, "Subject": descripcion[:500], "Keywords": fuente[:500],
                "Creator": SOFTWARE}
    fig.savefig(base.with_suffix(".pdf"), metadata=pdf_meta, facecolor=t["bg"])
    plt.close(fig)
    return [str(base.with_suffix(".png")).replace("\\", "/"), str(base.with_suffix(".pdf")).replace("\\", "/")]


def _clean(o):
    if isinstance(o, dict):
        return {str(k): _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if isinstance(o, (np.floating,)):
        return None if not np.isfinite(o) else float(o)
    if isinstance(o, float):
        return None if not np.isfinite(o) else o
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.bool_):
        return bool(o)
    return o


def procedencia(nombre: str, titulo_en: str, titulo_es: str, archivos: list[str], entradas: list[dict],
                calculo: str, numeros: dict, alt_en: str, alt_es: str, avisos: list[str] | None = None) -> Path:
    import matplotlib as mpl
    import pandas as pd
    doc = {"pieza": nombre, "titulo_en": titulo_en, "titulo_es": titulo_es,
           "generado_utc": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "generado_por": "earthmemory/galeria (docker compose run --rm galeria)",
           "archivos": archivos, "entradas": entradas, "calculo": calculo, "numeros_codificados": numeros,
           "avisos": avisos or [], "alt_en": alt_en, "alt_es": alt_es,
           "software": {"python": platform.python_version(), "matplotlib": mpl.__version__,
                        "numpy": np.__version__, "pandas": pd.__version__},
           "nota_ia": SOFTWARE}
    p = OUT / f"{nombre}.json"
    p.write_text(json.dumps(_clean(doc), ensure_ascii=False, indent=1), encoding="utf-8")
    (OUT / f"{nombre}.alt.txt").write_text(f"EN: {alt_en}\n\nES: {alt_es}\n", encoding="utf-8")
    return p


def theme_list(temas=None):
    return [TEMAS[k] for k in (temas or ("dark", "light"))]
