"""NASA POWER: URLs exactas, descarga con pausa y reintentos, caché con SHA-256 y lectura.

POWER sirve MERRA-2 a su resolución nativa (0.5° lat × 0.625° lon). El endpoint regional mensual
acepta un solo parámetro por pedido y cajas de 2° a 10°. El endpoint diario por punto devuelve la
celda nativa que contiene el punto (comprobado: tres puntos de la misma celda dan valores idénticos).
"""

from __future__ import annotations

import hashlib
import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

BASE = "https://power.larc.nasa.gov/api/temporal"
COMMUNITY = "AG"
FILL = -999.0
USER_AGENT = "earthmemory/0.1 (NASA Space Apps 2026; reproducible research)"

# Parámetros mensuales: (nombre POWER, descripción, unidades POWER)
MONTHLY_PARAMS = {
    "PRECTOTCORR": ("Precipitación corregida (MERRA-2 PRECTOTCORR)", "mm/día"),
    "GWETTOP": ("Humedad relativa del suelo superficial, 0-5 cm (MERRA-2 Catchment)", "0-1"),
    "GWETROOT": ("Humedad relativa de la zona de raíces, 0-100 cm (MERRA-2 Catchment)", "0-1"),
    "GWETPROF": ("Humedad relativa del perfil completo (MERRA-2 Catchment)", "0-1"),
    "T2M": ("Temperatura del aire a 2 m (MERRA-2)", "°C"),
    "EVLAND": ("Evaporación sobre tierra (MERRA-2)", "mm/día"),
}


def monthly_regional_url(param: str, bbox: tuple[float, float, float, float], y0: int, y1: int) -> str:
    lon0, lat0, lon1, lat1 = bbox
    return (f"{BASE}/monthly/regional?parameters={param}&community={COMMUNITY}"
            f"&longitude-min={lon0:.4f}&longitude-max={lon1:.4f}&latitude-min={lat0:.4f}&latitude-max={lat1:.4f}"
            f"&start={y0}&end={y1}&format=json")


def daily_point_url(params: list[str], lon: float, lat: float, start: str, end: str) -> str:
    return (f"{BASE}/daily/point?parameters={','.join(params)}&community={COMMUNITY}"
            f"&longitude={lon:.4f}&latitude={lat:.4f}&start={start}&end={end}&format=json")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class Manifest:
    """Registro de cada archivo descargado: URL, SHA-256, bytes, fecha UTC y fuente declarada."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.data = json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else {"archivos": {}}

    def rel(self, p: Path) -> str:
        return Path(p).relative_to(self.path.parent).as_posix()

    def add(self, p: Path, url: str, save: bool = True, **extra) -> None:
        self.data["archivos"][self.rel(p)] = {"url": url, "sha256": sha256(p), "bytes": Path(p).stat().st_size,
                                              "descargado_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                                              **extra}
        if save:
            self.save()

    def note(self, section: str, key: str, value) -> None:
        """Secciones libres del manifiesto (p. ej. 'rutas': qué ruta funcionó o falló y el error exacto)."""
        self.data.setdefault(section, {})[key] = value
        self.save()

    def verify(self, p: Path) -> bool:
        rec = self.data["archivos"].get(self.rel(p))
        return bool(rec) and Path(p).exists() and sha256(p) == rec["sha256"]

    def save(self) -> None:
        self.data["archivos"] = dict(sorted(self.data["archivos"].items()))
        self.data = {k: self.data[k] for k in sorted(self.data, key=lambda k: (k == "archivos", k))}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def http_get(url: str, retries: int = 5, pause: float = 1.5, timeout: int = 300) -> bytes:
    last = None
    for k in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                body = r.read()
            time.sleep(pause)  # cortesía con el servicio
            return body
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:  # 429/5xx incluidos
            last = e
            time.sleep(pause * (2 ** k))
    raise RuntimeError(f"No se pudo descargar {url}: {last}")


def fetch(url: str, dest: Path, manifest: Manifest, refresh: bool = False) -> Path:
    """Descarga solo si falta o si la suma no coincide con el manifiesto. Valida que sea JSON de POWER."""
    dest = Path(dest)
    if not refresh and manifest.verify(dest):
        return dest
    if dest.exists() and not refresh and manifest.rel(dest) in manifest.data["archivos"]:
        raise RuntimeError(f"{dest}: la suma SHA-256 no coincide con MANIFEST.json (archivo alterado)")
    body = http_get(url)
    doc = json.loads(body)
    if "features" not in doc and "properties" not in doc:
        raise RuntimeError(f"Respuesta inesperada de POWER para {url}: {str(doc)[:300]}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(body)
    hdr = doc.get("header", {}) if isinstance(doc.get("header"), dict) else {}
    manifest.add(dest, url, fuente=hdr.get("sources"), api=hdr.get("api"), titulo=hdr.get("title"),
                 estandar_tiempo=hdr.get("time_standard"))
    return dest


def cell_id(lat: float, lon: float) -> str:
    return f"{lat:.2f}_{lon:.3f}"


def _month_key_to_ts(k: str) -> pd.Timestamp | None:
    if len(k) != 6 or k[4:] == "13":  # YYYY13 = media anual: se descarta
        return None
    return pd.Timestamp(int(k[:4]), int(k[4:]), 1)


def parse_regional_monthly(doc: dict, param: str) -> tuple[pd.DataFrame, dict]:
    """Devuelve (DataFrame mes × celda, {celda: (lat, lon, elevación_m)}). −999 → NaN."""
    cols, meta = {}, {}
    for f in doc["features"]:
        lon, lat = f["geometry"]["coordinates"][:2]
        elev = f["geometry"]["coordinates"][2] if len(f["geometry"]["coordinates"]) > 2 else np.nan
        cid = cell_id(lat, lon)
        vals = {}
        for k, v in f["properties"]["parameter"][param].items():
            ts = _month_key_to_ts(k)
            if ts is not None:
                vals[ts] = np.nan if v is None or v == FILL else float(v)
        cols[cid] = pd.Series(vals)
        meta[cid] = (float(lat), float(lon), float(elev))
    df = pd.DataFrame(cols).sort_index()
    df.index.name = "fecha"
    return df[sorted(df.columns)], meta


def parse_daily_point(doc: dict, param: str) -> pd.Series:
    vals = doc["properties"]["parameter"][param]
    s = pd.Series({pd.Timestamp(k): (np.nan if v == FILL else float(v)) for k, v in vals.items()}).sort_index()
    s.index.name = "fecha"
    return s


def load_json(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))
