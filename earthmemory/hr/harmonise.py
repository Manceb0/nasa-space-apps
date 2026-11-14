"""Lee lo descargado y lo lleva a la rejilla común CHIRPS 0.05° sobre tierra dominicana. Conserva las nativas.

Reglas de remuestreo (documentadas en el informe):
- Continuos más finos que 0.05° (TerraClimate 1/24°, SoilGrids 0.0025°, DEM 3″): media ponderada por el área de
  solape (remapeo conservativo de primer orden). La pendiente se calcula ANTES de agregar (a 90 m, Horn 1981).
- Categóricos (WorldCover): fracción de cada clase en la celda (nunca la clase mayoritaria sola).
- Productos más gruesos que 0.05° (IMERG 0.1°, SMAP 9 km, GLDAS 0.25°): NO se interpolan. Se guardan en su
  rejilla nativa; si hace falta un valor por celda 0.05°, se usa el de la celda nativa que contiene su centro y
  el mapa/tabla dice la resolución nativa.
- Máscara: fracción de la celda 0.05° dentro de geoBoundaries ADM0 ≥ 0.5 (100 puntos por celda, peso cos φ).
"""

from __future__ import annotations

import gzip
import io
import json
from pathlib import Path

import numpy as np
from matplotlib.path import Path as MplPath

from .common import DATA, GRID, ROOT, YEARS, RGrid, conservative_regrid, edges_from_centers
from .sources import WORLDCOVER_CLASSES

DER = DATA / "derivados"
MONTHS = np.array([np.datetime64(f"{y}-{m:02d}") for y in range(YEARS[0], YEARS[1] + 1) for m in range(1, 13)])


# ------------------------------------------------------------------ límites y máscara

def _polys(geom: dict) -> list:
    rings = [geom["coordinates"]] if geom["type"] == "Polygon" else geom["coordinates"]
    return [(np.asarray(r[0], float), [np.asarray(h, float) for h in r[1:]]) for r in rings]


def load_boundaries() -> tuple[list, list[tuple[str, list]]]:
    d = DATA / "limites"
    adm0 = json.loads((d / "geoBoundaries-DOM-ADM0_simplified.geojson").read_text(encoding="utf-8"))
    country = [p for f in adm0["features"] for p in _polys(f["geometry"])]
    adm1 = json.loads((d / "geoBoundaries-DOM-ADM1.geojson").read_text(encoding="utf-8"))
    provs = sorted([(f["properties"]["shapeName"], _polys(f["geometry"])) for f in adm1["features"]])
    return country, provs


def inside(polys: list, x: np.ndarray, y: np.ndarray) -> np.ndarray:
    res = np.zeros(x.size, bool)
    pts = np.column_stack([x, y])
    for ext, holes in polys:
        sel = ((x >= ext[:, 0].min()) & (x <= ext[:, 0].max()) & (y >= ext[:, 1].min()) & (y <= ext[:, 1].max()))
        if not sel.any():
            continue
        m = MplPath(ext).contains_points(pts[sel])
        for h in holes:
            m &= ~MplPath(h).contains_points(pts[sel])
        res[np.flatnonzero(sel)[m]] = True
    return res


def cell_fractions(g: RGrid, polys: list, n: int = 10) -> np.ndarray:
    off = (np.arange(n) + 0.5) / n
    LO, LA = g.mesh()
    px = (LO[..., None, None] - g.res / 2 + off[None, None, None, :] * g.res + 0 * off[None, None, :, None])
    py = (LA[..., None, None] - g.res / 2 + off[None, None, :, None] * g.res + 0 * off[None, None, None, :])
    w = np.cos(np.radians(py))
    m = inside(polys, px.ravel(), py.ravel()).reshape(px.shape)
    return (m * w).sum(axis=(2, 3)) / w.sum(axis=(2, 3))


def province_index(g: RGrid, provs: list, n: int = 6) -> np.ndarray:
    """Índice de la provincia con más área en la celda (−1 si ninguna)."""
    fr = np.stack([cell_fractions(g, p, n) for _, p in provs])
    idx = np.argmax(fr, axis=0)
    idx[fr.max(axis=0) <= 0] = -1
    return idx


# ------------------------------------------------------------------ lectores

def _read_tif(b: bytes) -> tuple[np.ndarray, object, float | None]:
    import rasterio
    with rasterio.MemoryFile(b) as mf, mf.open() as r:
        return r.read(1), r.transform, r.nodata


def _tif_to_grid_window(a: np.ndarray, tr, nodata, g: RGrid = GRID) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Recorta un ráster norte-arriba a la caja de g (+1 píxel) y lo devuelve con lat ascendente y sus bordes."""
    a = a.astype(float)
    if nodata is not None:
        a[a == nodata] = np.nan
    res_x, res_y = tr.a, -tr.e
    c0 = int(np.floor((g.lon_edges[0] - tr.c) / res_x)) - 1
    c1 = int(np.ceil((g.lon_edges[-1] - tr.c) / res_x)) + 1
    r0 = int(np.floor((tr.f - g.lat_edges[-1]) / res_y)) - 1
    r1 = int(np.ceil((tr.f - g.lat_edges[0]) / res_y)) + 1
    c0, r0 = max(c0, 0), max(r0, 0)
    c1, r1 = min(c1, a.shape[1]), min(r1, a.shape[0])
    sub = a[r0:r1, c0:c1][::-1]
    lon_e = tr.c + np.arange(c0, c1 + 1) * res_x
    lat_e = (tr.f - np.arange(r0, r1 + 1) * res_y)[::-1]
    return sub, lat_e, lon_e


def chirps_monthly() -> np.ndarray:
    out = np.full((MONTHS.size, GRID.ny, GRID.nx), np.nan)
    for k, t in enumerate(MONTHS):
        y, m = str(t).split("-")
        b = gzip.decompress((DATA / "chirps" / "mensual" / f"chirps-v2.0.{y}.{m}.tif.gz").read_bytes())
        a, tr, nd = _read_tif(b)
        sub, le, oe = _tif_to_grid_window(a, tr, nd)
        sub[sub < 0] = np.nan
        out[k] = conservative_regrid(sub, le, oe, GRID, min_cover=0.99)
    return out


def chirps_daily_nov2023() -> np.ndarray:
    out = np.full((30, GRID.ny, GRID.nx), np.nan)
    for d in range(1, 31):
        b = gzip.decompress((DATA / "chirps" / "diario" / f"chirps-v2.0.2023.11.{d:02d}.tif.gz").read_bytes())
        a, tr, nd = _read_tif(b)
        sub, le, oe = _tif_to_grid_window(a, tr, nd)
        sub[sub < 0] = np.nan
        out[d - 1] = conservative_regrid(sub, le, oe, GRID, min_cover=0.99)
    return out


def terraclimate(var: str) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict]:
    """Devuelve (datos [t, lat asc, lon], lat, lon, atributos) en la rejilla NATIVA 1/24°."""
    import scipy.io as sio
    arrs, lat, lon, attrs = [], None, None, {}
    for y in range(YEARS[0], YEARS[1] + 1):
        p = DATA / "terraclimate" / var / f"TerraClimate_{var}_{y}_RD.nc"
        with sio.netcdf_file(p, "r", mmap=False) as f:
            v = f.variables[var]
            raw = v[:].astype(float)
            fill = getattr(v, "_FillValue", None)
            miss = getattr(v, "missing_value", None)
            for fv in (fill, miss):
                if fv is not None:
                    raw[raw == float(np.asarray(fv).ravel()[0])] = np.nan
            sc = float(getattr(v, "scale_factor", 1.0))
            off = float(getattr(v, "add_offset", 0.0))
            arrs.append(raw * sc + off)
            lat, lon = f.variables["lat"][:].astype(float), f.variables["lon"][:].astype(float)
            if not attrs:
                attrs = {k: (v_.decode("utf-8", "replace") if isinstance(v_, bytes) else str(v_))
                         for k, v_ in f._attributes.items() if k in ("version", "date_created", "source", "license",
                                                                       "references", "method")}
                attrs["unidades"] = getattr(v, "units", b"").decode() if isinstance(getattr(v, "units", b""), bytes) else ""
    a = np.concatenate(arrs, axis=0)
    if lat[0] > lat[-1]:
        a, lat = a[:, ::-1], lat[::-1]
    return a, lat, lon, attrs


def soilgrids(prop: str) -> tuple[np.ndarray, dict]:
    """Media 0-30 cm ponderada por espesor (5, 10, 15 cm) en % → 0.05°. 0 = sin dato (agua/urbano sin predicción)."""
    acc, wsum, native = 0.0, 0.0, None
    for depth, w in (("0-5cm", 5), ("5-15cm", 10), ("15-30cm", 15)):
        import rasterio
        with rasterio.open(DATA / "soilgrids" / f"{prop}_{depth}_mean_RD_0.0025deg.tif") as r:
            a, tr = r.read(1).astype(float), r.transform
        a[a <= 0] = np.nan
        acc = acc + w * a / 10.0
        wsum += w
    native = acc / wsum
    sub, le, oe = _tif_to_grid_window(native, tr, None)
    return conservative_regrid(sub, le, oe, GRID, min_cover=0.5), {"nativo": sub, "lat_e": le, "lon_e": oe}


def dem() -> tuple[dict, dict]:
    """Mosaico 3″ de Copernicus GLO-90; pendiente (Horn) a 90 m; agrega media de elevación, pendiente y
    desviación típica de la elevación (relieve) a 0.05°."""
    import rasterio
    res = 1 / 1200
    lon0, lat0, lon1, lat1 = GRID.lon_edges[0], GRID.lat_edges[0], GRID.lon_edges[-1], GRID.lat_edges[-1]
    # centros de píxel en múltiplos enteros de 1/1200 (AREA_OR_POINT=Point)
    ci = np.arange(int(np.ceil(lon0 / res)), int(np.floor(lon1 / res)) + 1)
    ri = np.arange(int(np.ceil(lat0 / res)), int(np.floor(lat1 / res)) + 1)
    Z = np.full((ri.size, ci.size), np.nan, np.float32)
    for p in sorted((DATA / "dem").glob("*.tif")):
        with rasterio.open(p) as r:
            a = r.read(1)
            tr = r.transform
        clon = np.round((tr.c + tr.a / 2) / res + np.arange(a.shape[1])).astype(int)   # índice entero del centro
        clat = np.round((tr.f + tr.e / 2) / res - np.arange(a.shape[0])).astype(int)
        jx = clon - ci[0]
        iy = clat - ri[0]
        okx, oky = (jx >= 0) & (jx < ci.size), (iy >= 0) & (iy < ri.size)
        Z[np.ix_(iy[oky], jx[okx])] = a[np.ix_(oky, okx)]
    lat_c = ri * res
    # Pendiente de Horn con espaciado métrico (esfera local)
    dy = res * 110_574.0
    dx = res * 111_320.0 * np.cos(np.radians(lat_c))[:, None]
    zp = np.pad(Z, 1, mode="edge")
    gx = ((zp[:-2, 2:] + 2 * zp[1:-1, 2:] + zp[2:, 2:]) - (zp[:-2, :-2] + 2 * zp[1:-1, :-2] + zp[2:, :-2])) / (8 * dx)
    gy = ((zp[2:, :-2] + 2 * zp[2:, 1:-1] + zp[2:, 2:]) - (zp[:-2, :-2] + 2 * zp[:-2, 1:-1] + zp[:-2, 2:])) / (8 * dy)
    slope = np.degrees(np.arctan(np.hypot(gx, gy))).astype(np.float32)
    lat_e = np.concatenate([lat_c - res / 2, [lat_c[-1] + res / 2]])
    lon_e = np.concatenate([ci * res - res / 2, [ci[-1] * res + res / 2]])
    zz = Z.astype(float)
    zz[zz == 0] = np.nan   # mar = 0 exacto en las teselas; se CONSERVAN las cotas negativas (hoya de Enriquillo)
    s = slope.astype(float)
    s[~np.isfinite(zz)] = np.nan
    out = {"elev_m": conservative_regrid(zz, lat_e, lon_e, GRID, 0.3),
           "pendiente_grados": conservative_regrid(s, lat_e, lon_e, GRID, 0.3)}
    m2 = conservative_regrid(zz ** 2, lat_e, lon_e, GRID, 0.3)
    out["relieve_m"] = np.sqrt(np.clip(m2 - out["elev_m"] ** 2, 0, None))
    return out, {"Z": Z[::4, ::4], "lat": lat_c[::4], "lon": (ci * res)[::4]}


def worldcover() -> tuple[dict, dict]:
    import rasterio
    with rasterio.open(DATA / "worldcover" / "ESA_WorldCover_10m_2021_v200_RD_vista8.tif") as r:
        a, tr = r.read(1), r.transform
    out = {}
    valid = (a > 0).astype(float)
    sub_v, le, oe = _tif_to_grid_window(valid, tr, None)
    den = conservative_regrid(sub_v, le, oe, GRID, 0.0)
    for c, name in WORLDCOVER_CLASSES.items():
        ind = (a == c).astype(float)
        sub, le, oe = _tif_to_grid_window(ind, tr, None)
        f = conservative_regrid(sub, le, oe, GRID, 0.0)
        with np.errstate(invalid="ignore", divide="ignore"):
            out[f"lc_{name}"] = np.where(den > 0, f / den, np.nan)
    # Validación: vista 1/8 frente a 10 m en la ventana de validación (fracciones por celda 0.05°)
    with rasterio.open(DATA / "worldcover" / "ESA_WorldCover_10m_2021_v200_validacion_10m.tif") as r:
        v, trv = r.read(1), r.transform
    gv = RGrid(lon0=-70.75, lat0=19.25, res=0.05, nx=5, ny=5)
    diffs = {}
    for c, name in WORLDCOVER_CLASSES.items():
        s10, l10, o10 = _tif_to_grid_window((v == c).astype(float), trv, None, gv)
        s80, l80, o80 = _tif_to_grid_window((a == c).astype(float), tr, None, gv)
        f10 = conservative_regrid(s10, l10, o10, gv, 0.0)
        f80 = conservative_regrid(s80, l80, o80, gv, 0.0)
        if np.nanmax(f10) > 0.01:
            diffs[name] = {"media_10m": float(np.nanmean(f10)), "media_vista8": float(np.nanmean(f80)),
                           "dif_abs_max_celda": float(np.nanmax(np.abs(f10 - f80)))}
    return out, {"validacion_vista8_vs_10m": diffs, "mapa_vista8": a[::6, ::6], "tr": tr}


def smap_monthly() -> dict | None:
    """Medias mensuales en la rejilla NATIVA EASE 9 km (filas × columnas del recorte)."""
    import h5py
    files = sorted((DATA / "smap" / "diario").glob("*/SPL4SMGP_*_RD.nc4"))
    if not files:
        return None
    acc = {}
    lat = lon = None
    for p in files:
        day = p.name.split("_")[1]
        key = f"{day[:4]}-{day[4:6]}"
        with h5py.File(p, "r") as f:
            g = f["Geophysical_Data"]
            vals = {}
            for v in ("sm_rootzone", "sm_surface", "precipitation_total_surface_flux"):
                x = g[v][:].astype(float)
                x[x <= -9990] = np.nan
                vals[v] = x
            if lat is None:
                lat, lon = f["cell_lat"][:].astype(float), f["cell_lon"][:].astype(float)
        a = acc.setdefault(key, {k: [] for k in vals})
        for k, x in vals.items():
            a[k].append(x)
    keys = [k for k in sorted(acc) if len(acc[k]["sm_rootzone"]) >= 20]   # meses completos (descarta 2015-03: 1 día)
    out = {"meses": np.array([np.datetime64(k) for k in keys]), "lat": lat, "lon": lon,
           "n_dias": np.array([len(acc[k]["sm_rootzone"]) for k in keys])}
    for v in ("sm_rootzone", "sm_surface", "precipitation_total_surface_flux"):
        out[v] = np.stack([np.nanmean(np.stack(acc[k][v]), axis=0) for k in keys])
    out["precip_mm_mes"] = out.pop("precipitation_total_surface_flux") * 86400 * 30.4375  # kg m-2 s-1 → mm/mes aprox.
    return out


def imerg_monthly() -> dict | None:
    """IMERG Final V07 mensual 0.1° desde la caché del motor nacional (solo lectura). mm/h → mm/mes."""
    import h5py
    d = ROOT / "data" / "nacional" / "gesdisc" / "GPM_3IMERGM.07"
    files = sorted(d.glob("3B-MO.MS.MRG.3IMERG.*.nc4"))
    if len(files) < MONTHS.size:
        return None
    arr, lat, lon = [], None, None
    for t in MONTHS:
        y, m = str(t).split("-")
        p = [f for f in files if f".{y}{m}01-" in f.name][0]
        with h5py.File(p, "r") as f:
            v = f["precipitation"] if "precipitation" in f else f["Grid/precipitation"]
            x = v[0].astype(float)  # [lon][lat]
            lat = np.round((f["lat"] if "lat" in f else f["Grid/lat"])[:].astype(float), 3)
            lon = np.round((f["lon"] if "lon" in f else f["Grid/lon"])[:].astype(float), 3)
        x[x < 0] = np.nan
        days = (np.datetime64(f"{y}-{m}") + np.timedelta64(1, "M")).astype("datetime64[D]") - \
            np.datetime64(f"{y}-{m}").astype("datetime64[D]")
        arr.append(x.T * 24 * days.astype(int))
    a = np.stack(arr)
    if lat[0] > lat[-1]:
        a, lat = a[:, ::-1], lat[::-1]
    return {"P": a, "lat": lat, "lon": lon}


def imerg_daily_nov2023() -> dict | None:
    """IMERG Final V07 diario (00-24 UTC, mm/día) de noviembre 2023, desde la caché del motor nacional."""
    import h5py
    d = ROOT / "data" / "nacional" / "gesdisc" / "GPM_3IMERGDF.07" / "2023"
    arr, lat, lon = [], None, None
    for day in range(1, 31):
        ps = sorted(d.glob(f"3B-DAY.MS.MRG.3IMERG.202311{day:02d}-*.nc4"))
        if not ps:
            return None
        with h5py.File(ps[0], "r") as f:
            x = f["precipitation"][0].astype(float)
            lat, lon = np.round(f["lat"][:].astype(float), 3), np.round(f["lon"][:].astype(float), 3)
        x[x < 0] = np.nan
        arr.append(x.T)
    return {"Pd": np.stack(arr), "lat": lat, "lon": lon}


def native_to_grid_nearest(lat_c: np.ndarray, lon_c: np.ndarray, res_lat: float, res_lon: float,
                           g: RGrid = GRID) -> tuple[np.ndarray, np.ndarray]:
    """Índices (i, j) de la celda nativa regular que contiene el centro de cada celda 0.05° (−1 si fuera)."""
    LO, LA = g.mesh()
    i = np.floor((LA - (lat_c[0] - res_lat / 2)) / res_lat).astype(int)
    j = np.floor((LO - (lon_c[0] - res_lon / 2)) / res_lon).astype(int)
    bad = (i < 0) | (i >= lat_c.size) | (j < 0) | (j >= lon_c.size)
    i[bad], j[bad] = -1, -1
    return i, j


def smap_to_grid_nearest(sm: dict, g: RGrid = GRID) -> np.ndarray:
    """Para cada celda 0.05°, índice plano de la celda EASE 9 km más cercana a su centro (en grados escalados)."""
    LO, LA = g.mesh()
    la, lo = sm["lat"].ravel(), sm["lon"].ravel()
    ok = np.isfinite(la) & np.isfinite(lo)
    c = np.cos(np.radians(18.8))
    d = ((LA.ravel()[:, None] - la[None, ok]) ** 2 + (c * (LO.ravel()[:, None] - lo[None, ok])) ** 2)
    return np.flatnonzero(ok)[np.argmin(d, axis=1)].reshape(LA.shape)


# ------------------------------------------------------------------ orquestación

def build(force: bool = False) -> dict:
    """Construye data/nacional_hr/derivados/*.npz (caché) y devuelve un dict con todo."""
    DER.mkdir(parents=True, exist_ok=True)
    p_main = DER / "rejilla_005.npz"
    if p_main.exists() and not force:
        return load()
    country, provs = load_boundaries()
    print("[armonizar] máscara y provincias…", flush=True)
    frac = cell_fractions(GRID, country)
    prov = province_index(GRID, provs)
    print("[armonizar] CHIRPS…", flush=True)
    P = chirps_monthly()
    Pd = chirps_daily_nov2023()
    out = {"frac_rd": frac, "prov": prov, "P_chirps": P, "Pd_nov2023": Pd, "meses": MONTHS.astype(str),
           "lat": GRID.lat, "lon": GRID.lon}
    meta = {"terraclimate": {}}
    native = {}
    for v in ("soil", "PDSI", "aet", "def", "ppt", "pet"):
        print(f"[armonizar] TerraClimate {v}…", flush=True)
        a, la, lo, attrs = terraclimate(v)
        meta["terraclimate"][v] = attrs
        out[f"tc_{v}"] = conservative_regrid(a, edges_from_centers(la), edges_from_centers(lo), GRID, 0.5)
        native[f"tc_{v}"] = a.astype(np.float32)
        native["tc_lat"], native["tc_lon"] = la, lo
    print("[armonizar] SoilGrids, DEM, WorldCover…", flush=True)
    for prop in ("clay", "sand"):
        out[f"sg_{prop}"], _ = soilgrids(prop)
    d, dnat = dem()
    out.update({f"dem_{k}": v for k, v in d.items()})
    native.update({"dem_Z": dnat["Z"], "dem_lat": dnat["lat"], "dem_lon": dnat["lon"]})
    lc, lcmeta = worldcover()
    out.update(lc)
    meta["worldcover_validacion"] = lcmeta["validacion_vista8_vs_10m"]
    native["wc_vista"] = lcmeta["mapa_vista8"]
    sm = smap_monthly()
    if sm is not None:
        print("[armonizar] SMAP L4…", flush=True)
        native.update({f"smap_{k}": v for k, v in sm.items() if k != "meses"})
        native["smap_meses"] = sm["meses"].astype(str)
        out["smap_idx"] = smap_to_grid_nearest(sm)
    imd = imerg_daily_nov2023()
    if imd is not None:
        native["imerg_Pd_nov2023"] = imd["Pd"].astype(np.float32)
    im = imerg_monthly()
    if im is not None:
        print("[armonizar] IMERG (caché del motor nacional)…", flush=True)
        native.update({"imerg_P": im["P"].astype(np.float32), "imerg_lat": im["lat"], "imerg_lon": im["lon"]})
        # CHIRPS agregado de forma conservativa a la rejilla IMERG (para comparar a 0.1°, no a 0.05°)
        g10 = RGrid(lon0=float(im["lon"][0] - 0.05), lat0=float(im["lat"][0] - 0.05), res=0.1,
                    nx=im["lon"].size, ny=im["lat"].size)
        native["chirps_a_imerg"] = conservative_regrid(P, GRID.lat_edges, GRID.lon_edges, g10, 0.99).astype(np.float32)
        native["frac_rd_imerg"] = cell_fractions(g10, country)
    np.savez_compressed(p_main, **out)
    np.savez_compressed(DER / "nativas.npz", **native)
    (DER / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return load()


def load() -> dict:
    R = dict(np.load(DER / "rejilla_005.npz", allow_pickle=False))
    R["nat"] = dict(np.load(DER / "nativas.npz", allow_pickle=False))
    R["meta"] = json.loads((DER / "meta.json").read_text(encoding="utf-8"))
    R["land"] = (R["frac_rd"] >= 0.5) & np.isfinite(R["tc_soil"]).all(axis=0) & np.isfinite(R["P_chirps"]).all(axis=0)
    country, provs = load_boundaries()
    R["country"], R["provs"] = country, provs
    return R
