"""MODIS MCDWD_L3 C6.1 (archivo reprocesado 2003-2025, LAADS): inundación observada, independiente de la lluvia.

Producto: «MODIS/Aqua+Terra Flood Map Daily L3 Global 250m LLL Grid» (doi:10.5067/MODIS/MCDWD_L3.061), teselas de
10° × 10° (4800 × 4800 píxeles de 1/480°, ≈ 231 m × 219 m a 19° N). La cuenca del Yuna necesita h10v07 (−80 a −70)
y h11v07 (−70 a −60). Valores de las capas Flood_* (atributo «description» del propio HDF):
    0 = sin agua · 1 = agua (coincide con el agua de referencia) · 2 = inundación recurrente (estacional esperada)
    3 = inundación (inusual) · 255 = datos insuficientes (nubes, sin pasada, sombra de relieve enmascarada)
Capa principal: Flood_2Day_250m. La guía de usuario y la documentación de NASA desaconsejan el compuesto de 1 día con
nubes (falsos positivos por sombra de nube) y el visor de NASA usa por defecto el de 2 días; se guarda también el de
3 días (menos nubes) y el 1 día con sombras de nube filtradas (FloodCS_1Day). Es OBSERVACIÓN óptica: no ve bajo
nubes ni bajo dosel denso, y una crecida que dura menos que el compuesto puede perderse.

Solo se bajan los días necesarios (ventanas de evento, días secos de referencia, episodios de lluvia fuerte y meses
con señal GSW sin evento). De cada HDF se guarda el recorte de la cuenca (npz); el HDF original se borra tras
recortarlo, y su URL, tamaño y SHA-256 quedan en data/yuna/MANIFEST.json.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from .common import DATA, RES, USER_AGENT, earthdata_token, manifest

BASE = "https://ladsweb.modaps.eosdis.nasa.gov/archive/allData/61/MCDWD_L3"
DX = 10.0 / 4800
WIN = (-70.95, 18.70, -69.25, 19.60)  # lon0, lat0, lon1, lat1 (múltiplos exactos de DX)
TILES = {"h10v07": -80.0, "h11v07": -70.0}  # lon oeste de cada tesela; ambas de 20 N a 10 N
CAPAS = ("Flood_2Day_250m", "Flood_3Day_250m", "FloodCS_1Day_250m")
LIC = "NASA LANCE/LAADS: datos abiertos sin restricciones (NASA Earth Science Data and Information Policy); cita doi:10.5067/MODIS/MCDWD_L3.061"
DOI = "10.5067/MODIS/MCDWD_L3.061"
PX_KM2 = (DX * 110.574) * (DX * 111.32 * np.cos(np.radians(19.15)))


def shape() -> tuple[int, int]:
    lon0, lat0, lon1, lat1 = WIN
    return int(round((lat1 - lat0) / DX)), int(round((lon1 - lon0) / DX))


def transform():
    from rasterio.transform import from_origin
    return from_origin(WIN[0], WIN[3], DX, DX)


def _session():
    import requests
    s = requests.Session()
    s.headers.update({"Authorization": "Bearer " + (earthdata_token() or ""), "User-Agent": USER_AGENT})
    return s


def _links(s, d: pd.Timestamp) -> dict:
    u = f"{BASE}/{d.year}/{d.dayofyear:03d}.json"
    r = s.get(u, timeout=120)
    r.raise_for_status()
    js = r.json()
    cont = js["content"] if isinstance(js, dict) else js
    return {t: c["downloadsLink"] for c in cont for t in TILES if f".{t}." in c["name"]}


def _recorte(path: str, tile: str) -> dict:
    from pyhdf.SD import SD
    f = SD(path)
    lon0, lat0, lon1, lat1 = WIN
    west = TILES[tile]
    a0, a1 = max(lon0, west), min(lon1, west + 10)
    c0, c1 = int(round((a0 - west) / DX)), int(round((a1 - west) / DX))
    r0, r1 = int(round((20 - lat1) / DX)), int(round((20 - lat0) / DX))
    out = {k: f.select(k)[r0:r1, c0:c1].astype(np.uint8) for k in CAPAS}
    f.end()
    return out, int(round((a0 - lon0) / DX))


def bajar_dia(s, d: pd.Timestamp) -> dict:
    dest = DATA / "mcdwd" / f"mcdwd_{d:%Y%m%d}.npz"
    links = _links(s, d)
    if set(links) != set(TILES):
        return {"fecha": d, "estado": f"faltan teselas: {sorted(set(TILES) - set(links))}"}
    h, w = shape()
    capas = {k: np.full((h, w), 255, np.uint8) for k in CAPAS}
    origen = {}
    for tile, url in links.items():
        r = s.get(url, timeout=600)
        r.raise_for_status()
        body = r.content
        if body[:4] != b"\x0e\x03\x13\x01":
            return {"fecha": d, "estado": f"{tile}: no es HDF4 (¿licencia/redirección?)"}
        origen[tile] = {"url": url, "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()}
        fd, tmp = tempfile.mkstemp(suffix=".hdf")
        try:
            with os.fdopen(fd, "wb") as fh:
                fh.write(body)
            rec, off = _recorte(tmp, tile)
        finally:
            os.remove(tmp)
        for k, a in rec.items():
            capas[k][:, off: off + a.shape[1]] = a
    dest.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(dest, **capas)
    return {"fecha": d, "estado": "ok", "archivo": dest, "origen": origen}


def bajar(dias: list[pd.Timestamp], workers: int = 12) -> pd.DataFrame:
    man = manifest()
    s = _session()
    # orden de prioridad: el orden de `dias` (eventos primero); sin repetir
    vistos, pend = set(), []
    for d in dias:
        if d not in vistos and not man.has(DATA / "mcdwd" / f"mcdwd_{d:%Y%m%d}.npz"):
            pend.append(d)
        vistos.add(d)
    filas = []
    with ThreadPoolExecutor(workers) as ex:
        fut = {ex.submit(bajar_dia, s, d): d for d in pend}
        for i, f in enumerate(as_completed(fut)):
            d = fut[f]
            try:
                r = f.result()
            except Exception as e:  # noqa: BLE001
                r = {"fecha": d, "estado": f"error: {type(e).__name__}: {str(e)[:160]}"}
            if r["estado"] == "ok":
                man.add(r["archivo"], " | ".join(o["url"] for o in r["origen"].values()), save=False,
                        dataset="MODIS_MCDWD_L3_C61", doi=DOI, licencia=LIC,
                        accedido=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                        originales={t: {k: v for k, v in o.items()} for t, o in r["origen"].items()},
                        ventana_lonlat=list(WIN), capas=list(CAPAS),
                        nota="recorte de la cuenca; HDF original borrado tras recortar (SHA-256 del original arriba)")
            filas.append({"fecha": d.date(), "estado": r["estado"]})
            if i % 20 == 0:
                man.save()
                print(f"  MCDWD {i + 1}/{len(pend)}", flush=True)
    man.save()
    est = pd.DataFrame(filas)
    if len(est):
        man.note("MCDWD_L3", {"estado": "ok", "fecha_prueba": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                              "dias_pedidos": int(len(pend)), "dias_ok": int((est["estado"] == "ok").sum()),
                              "fallos": est.loc[est["estado"] != "ok"].astype(str).to_dict("records")[:30]})
    return est


# ------------------------------------------------------------------ selección de días

def dias_necesarios(cat: pd.DataFrame, v: pd.DataFrame, episodios: pd.DataFrame, gsw_sin_cat: list[str],
                    seed: int = 2026) -> pd.DataFrame:
    filas = []
    ev = cat[cat["zona"].isin({"bajo_yuna", "alto_yuna", "camu", "cuenca_general"})]
    for r in ev.itertuples():
        a, b = pd.Timestamp(r.inicio), pd.Timestamp(r.fin)
        if a.year < 2003 or a.year > 2025:
            continue
        # en eventos largos, además cada 3 días hasta el fin + 3
        # días −1, +1, +3, +5, +7: con el compuesto de 2 días cubren de −2 a +7 sin huecos
        ds = [a + pd.Timedelta(days=k) for k in (-1, 1, 3, 5, 7)]
        if (b - a).days > 7:
            ds += list(pd.date_range(a + pd.Timedelta(days=10), b + pd.Timedelta(days=3), freq="3D"))
        filas += [{"fecha": d, "motivo": "evento", "id": r.id} for d in ds]
    for _, e in episodios.iterrows():
        s0 = pd.Timestamp(e["inicio"])
        if 2003 <= s0.year <= 2024:
            filas += [{"fecha": s0 + pd.Timedelta(days=k), "motivo": "episodio_p99", "id": s0.strftime("%Y-%m-%d")}
                      for k in (3,)]
    for m in gsw_sin_cat:
        m0 = pd.Timestamp(m + "-01")
        filas += [{"fecha": m0 + pd.Timedelta(days=k), "motivo": "gsw_sin_evento", "id": m} for k in (3, 10, 17, 24)]
    # días secos de referencia: antecedente 30 d < p25 y < 5 mm en 48 h, uno o dos por año 2003-2024
    rng = np.random.default_rng(seed)
    ant, r48 = v["ant30_yuna"], v["r48_yuna"]
    seco = v.index[(ant < ant.quantile(0.25)) & (r48 < 5) & (v.index.year >= 2003) & (v.index.year <= 2024)]
    for y in range(2003, 2025):
        cand = seco[seco.year == y]
        if len(cand):
            for d in rng.choice(cand, size=min(1, len(cand)), replace=False):
                filas.append({"fecha": pd.Timestamp(d), "motivo": "referencia_seca", "id": str(y)})
    out = pd.DataFrame(filas)
    out["fecha"] = pd.to_datetime(out["fecha"])
    return out


# ------------------------------------------------------------------ máscaras y estadísticas

def mascaras(zonas: dict) -> dict:
    import rasterio
    from rasterio.features import rasterize
    from rasterio.warp import Resampling, reproject
    from .common import HR
    h, w = shape()
    tr = transform()
    m = {k: rasterize([(g, 1)], out_shape=(h, w), transform=tr, all_touched=False) == 1 for k, g in zonas.items()}
    dem = np.full((h, w), np.nan, np.float32)
    for f in sorted((HR / "dem").glob("Copernicus_DSM_COG_30_*_DEM.tif")):
        with rasterio.open(f) as s:
            tmp = np.full((h, w), np.nan, np.float32)
            reproject(s.read(1).astype(np.float32), tmp, src_transform=s.transform, src_crs=s.crs, dst_transform=tr,
                      dst_crs="EPSG:4326", resampling=Resampling.average, src_nodata=s.nodata, dst_nodata=np.nan)
            dem = np.where(np.isnan(dem), tmp, dem)
    m["llanura"] = m["bajo_yuna"] & (dem < 20)
    return m


def siempre_enmascarado(capa: str = "Flood_2Day_250m") -> np.ndarray:
    """Píxeles con 255 en TODOS los días bajados: el producto los enmascara siempre (sombra de relieve, filtro HAND
    de terreno alto respecto al drenaje). No son «nubes»: se excluyen del denominador de la fracción insuficiente."""
    acc = None
    for p in sorted((DATA / "mcdwd").glob("mcdwd_*.npz")):
        a = np.load(p)[capa] == 255
        acc = a if acc is None else (acc & a)
    return acc


def estadisticas(masks: dict) -> pd.DataFrame:
    filas = []
    fijo = {c: siempre_enmascarado(c) for c in ("Flood_2Day_250m", "Flood_3Day_250m")}
    for p in sorted((DATA / "mcdwd").glob("mcdwd_*.npz")):
        d = pd.Timestamp(p.stem.split("_")[1])
        z = np.load(p)
        for capa in ("Flood_2Day_250m", "Flood_3Day_250m"):
            a = z[capa]
            r = {"fecha": d, "capa": capa}
            for k, m in masks.items():
                v = a[m & ~fijo[capa]]
                n = v.size
                r[f"insuf_{k}"] = float((v == 255).mean()) if n else np.nan
                r[f"agua_ref_km2_{k}"] = float((v == 1).sum() * PX_KM2)
                r[f"recurrente_km2_{k}"] = float((v == 2).sum() * PX_KM2)
                r[f"inund_km2_{k}"] = float((v == 3).sum() * PX_KM2)
            filas.append(r)
    return pd.DataFrame(filas)


def guardar_dias(dias: pd.DataFrame) -> None:
    dias.to_csv(RES / "mcdwd_dias_pedidos.csv", index=False)


def resumen_json(est: pd.DataFrame) -> None:
    (RES / "mcdwd_estado.json").write_text(json.dumps(est.astype(str).to_dict("records"), ensure_ascii=False, indent=0),
                                           encoding="utf-8")
