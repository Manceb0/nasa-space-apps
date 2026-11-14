"""Rutas, manifiesto, HTTP y rejilla común del subpaquete de alta resolución."""

from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "nacional_hr"
RES = ROOT / "results" / "nacional_hr"
FIG = ROOT / "figures" / "nacional_hr"
REPORT = ROOT / "reports_nacional" / "ALTA_RESOLUCION.md"
NB_DIR = ROOT / "notebooks"
NB_HTML = ROOT / "reports_nacional" / "notebooks_html"

USER_AGENT = "earthmemory-hr/0.1 (NASA Space Apps 2026; reproducible research)"
YEARS = (2001, 2024)
# Caja de descarga (lon0, lat0, lon1, lat1): RD (17.47-19.93 N, 72.01-68.32 O) + margen
BBOX = (-72.10, 17.40, -68.20, 20.10)
SEED = 2026


# ------------------------------------------------------------------ manifiesto

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class Manifest:
    """Cada archivo: URL exacta, SHA-256, bytes, fecha UTC de descarga y metadatos de la fuente.
    La sección 'rutas' guarda qué ruta funcionó o falló (con el error exacto)."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.data = (json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists()
                     else {"archivos": {}, "rutas": {}})
        self.data.setdefault("rutas", {})
        self._dirty = 0

    def rel(self, p: Path) -> str:
        return Path(p).resolve().relative_to(self.path.parent.resolve()).as_posix()

    def add(self, p: Path, url: str, save: bool = True, **extra) -> None:
        self.data["archivos"][self.rel(p)] = {
            "url": url, "sha256": sha256(p), "bytes": Path(p).stat().st_size,
            "descargado_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), **extra}
        self._dirty += 1
        if save or self._dirty >= 200:
            self.save()

    def note(self, key: str, value) -> None:
        self.data["rutas"][key] = value
        self.save()

    def has(self, p: Path) -> bool:
        """Rápido: el archivo existe, está registrado y tiene el tamaño registrado."""
        rec = self.data["archivos"].get(self.rel(p))
        return bool(rec) and Path(p).exists() and Path(p).stat().st_size == rec["bytes"]

    def verify(self, p: Path) -> bool:
        rec = self.data["archivos"].get(self.rel(p))
        return bool(rec) and Path(p).exists() and sha256(p) == rec["sha256"]

    def save(self) -> None:
        self.data["archivos"] = dict(sorted(self.data["archivos"].items()))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
        tmp.replace(self.path)
        self._dirty = 0


# ------------------------------------------------------------------ HTTP

class FetchError(RuntimeError):
    pass


def http_get(url: str, headers: dict | None = None, retries: int = 5, timeout: int = 300,
             pause: float = 0.0) -> bytes:
    """GET con reintentos exponenciales. Los mensajes de error llevan URL y código, nunca cabeceras."""
    last = None
    for k in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **(headers or {})})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                body = r.read()
            if pause:
                time.sleep(pause)
            return body
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code} {e.reason}"
            if e.code in (400, 401, 403, 404, 410):
                break
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
            last = f"{type(e).__name__}: {e}"
        time.sleep(min(60.0, 2.0 * (2 ** k)))
    raise FetchError(f"{url} -> {last}")


def http_head(url: str, timeout: int = 60, retries: int = 4) -> dict:
    """Cabeceras de identidad del archivo remoto (tamaño, ETag, fecha). No es fatal si falla."""
    last = None
    for k in range(retries):
        try:
            req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                h = {kk.lower(): v for kk, v in r.headers.items()}
            return {kk: h.get(kk) for kk in ("content-length", "etag", "last-modified")}
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
            last = f"{type(e).__name__}: {e}"
            time.sleep(2.0 * (2 ** k))
    return {"error_head": last}


def earthdata_token() -> str | None:
    """Token Bearer de Earthdata SOLO desde archivo (montaje de solo lectura). Nunca se imprime."""
    for p in (os.environ.get("EARTHDATA_TOKEN_FILE"), "/run/secrets/earthdata_token",
              str(ROOT / ".secrets" / "earthdata_token")):
        if p and Path(p).is_file() and Path(p).stat().st_size > 20:
            return Path(p).read_text(encoding="utf-8").strip()
    return None


# ------------------------------------------------------------------ rejilla común (CHIRPS 0.05°)

@dataclass(frozen=True)
class RGrid:
    """Rejilla regular lat/lon por bordes. Filas de SUR a NORTE (lat ascendente), columnas de O a E."""
    lon0: float
    lat0: float
    res: float
    nx: int
    ny: int

    @property
    def lon(self) -> np.ndarray:
        return np.round(self.lon0 + (np.arange(self.nx) + 0.5) * self.res, 6)

    @property
    def lat(self) -> np.ndarray:
        return np.round(self.lat0 + (np.arange(self.ny) + 0.5) * self.res, 6)

    @property
    def lon_edges(self) -> np.ndarray:
        return np.round(self.lon0 + np.arange(self.nx + 1) * self.res, 6)

    @property
    def lat_edges(self) -> np.ndarray:
        return np.round(self.lat0 + np.arange(self.ny + 1) * self.res, 6)

    def mesh(self) -> tuple[np.ndarray, np.ndarray]:
        LO, LA = np.meshgrid(self.lon, self.lat)
        return LO, LA

    def area_km2(self) -> np.ndarray:
        """Área de cada celda (ny, nx): R²·Δλ·(sin φ2 − sin φ1)."""
        e = np.radians(self.lat_edges)
        band = 6371.0 ** 2 * np.radians(self.res) * (np.sin(e[1:]) - np.sin(e[:-1]))
        return np.repeat(band[:, None], self.nx, axis=1)


# CHIRPS: bordes en múltiplos de 0.05° (−180 + k·0.05). Caja común: 72.10-68.20 O, 17.40-20.10 N.
GRID = RGrid(lon0=-72.10, lat0=17.40, res=0.05, nx=78, ny=54)


def overlap_matrix(src_edges: np.ndarray, dst_edges: np.ndarray, lat: bool) -> np.ndarray:
    """Matriz (n_dst, n_src) de solape a lo largo de un eje. En latitud se usa sin φ (área exacta en la
    esfera); en longitud, grados. src_edges y dst_edges ascendentes."""
    f = (lambda v: np.sin(np.radians(v))) if lat else (lambda v: v)
    lo = np.maximum(dst_edges[:-1, None], src_edges[None, :-1])
    hi = np.minimum(dst_edges[1:, None], src_edges[None, 1:])
    return np.where(hi > lo, f(hi) - f(np.minimum(lo, hi)), 0.0)


def conservative_regrid(arr: np.ndarray, src_lat_edges: np.ndarray, src_lon_edges: np.ndarray,
                        dst: RGrid = GRID, min_cover: float = 0.5) -> np.ndarray:
    """Media ponderada por área de solape (remapeo conservativo de primer orden) de arr[..., lat, lon]
    (lat ascendente) a la rejilla dst. Ignora NaN; deja NaN si el área con dato < min_cover del área de la
    celda destino. Vale para agregar (fino → grueso) y para repartir (grueso → fino, que solo replica)."""
    Wy = overlap_matrix(src_lat_edges, dst.lat_edges, lat=True)     # (ny_dst, ny_src)
    Wx = overlap_matrix(src_lon_edges, dst.lon_edges, lat=False)    # (nx_dst, nx_src)
    a = np.asarray(arr, float)
    m = np.isfinite(a).astype(float)
    num = (Wy @ np.where(m > 0, a, 0.0)) @ Wx.T
    den = (Wy @ m) @ Wx.T
    le = np.sin(np.radians(dst.lat_edges))
    full = np.diff(le)[:, None] * np.diff(dst.lon_edges)[None, :]   # área de la celda destino (mismas unidades)
    with np.errstate(invalid="ignore", divide="ignore"):
        out = num / den
    out[(den < min_cover * full) | (den <= 0)] = np.nan
    return out


def edges_from_centers(c: np.ndarray) -> np.ndarray:
    c = np.asarray(c, float)
    d = np.diff(c)
    return np.concatenate([[c[0] - d[0] / 2], c[:-1] + d / 2, [c[-1] + d[-1] / 2]])


def bh_fdr(p: np.ndarray) -> np.ndarray:
    """Benjamini-Hochberg sobre los finitos; NaN se conserva."""
    p = np.asarray(p, float)
    q = np.full(p.shape, np.nan)
    ok = np.isfinite(p)
    if not ok.any():
        return q
    v = p[ok]
    o = np.argsort(v)
    m = v.size
    r = v[o] * m / (np.arange(m) + 1)
    r = np.minimum.accumulate(r[::-1])[::-1]
    out = np.empty(m)
    out[o] = np.clip(r, 0, 1)
    q[ok] = out
    return q


def write_json(path: Path, obj) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=_jdefault) + "\n", encoding="utf-8",
                    newline="\n")


def _jdefault(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return None if not np.isfinite(o) else float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, np.bool_):
        return bool(o)
    return str(o)
