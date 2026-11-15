"""Figuras del caso Yuna (matplotlib, estilo de artículo: Okabe-Ito, letras de panel, PNG 300 ppp + PDF + JSON de
procedencia). Cada panel dice la CLASE de cada variable: OBSERVACIÓN, RECUPERACIÓN SATELITAL, MODELO CON
ASIMILACIÓN, MODELO FORZADO, SIMULACIÓN HIDROLÓGICA."""

from __future__ import annotations

import json

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LightSource
from matplotlib.patches import Patch, Rectangle
from shapely.geometry import shape

from phantom.figures import GREY, MM, OI, panel_letter, save, style

from .common import DATA, FIG, HATILLO, HR, PUNTOS, RES

LAT0 = 19.1
Z_COL = {"alto_hatillo": OI["vermillion"], "camu": OI["blue"], "bajo_yuna": OI["green"], "yuna": OI["black"]}
Z_LAB = {"alto_hatillo": "Alto Yuna (sobre Hatillo)", "camu": "Camú (no regulado)", "bajo_yuna": "Bajo Yuna (resto)",
         "yuna": "Cuenca del Yuna"}
CL = {"imerg": "IMERG V07 · RECUPERACIÓN SATELITAL", "smap": "SMAP L4 · MODELO CON ASIMILACIÓN",
      "gldas": "GLDAS-2.1 · MODELO FORZADO", "geoglows": "GEOGLOWS v2 · SIMULACIÓN HIDROLÓGICA",
      "gsw": "JRC GSW (Landsat) · OBSERVACIÓN", "chirps": "CHIRPS v2 · RECUPERACIÓN SATELITAL + estaciones"}


def _geoms(path) -> dict:
    d = json.loads(path.read_text(encoding="utf-8"))
    return d["features"]


def _plot_geom(ax, g, **kw):
    polys = [g] if g.geom_type == "Polygon" else list(g.geoms)
    for p in polys:
        x, y = p.exterior.xy
        ax.plot(x, y, **kw)


def _fill_geom(ax, g, **kw):
    polys = [g] if g.geom_type == "Polygon" else list(g.geoms)
    for p in polys:
        x, y = p.exterior.xy
        ax.fill(x, y, **kw)


def _dem_hillshade(ext, res=0.0025):
    import rasterio
    from rasterio.transform import from_origin
    from rasterio.warp import Resampling, reproject
    x0, x1, y0, y1 = ext
    w, h = int((x1 - x0) / res), int((y1 - y0) / res)
    dst = np.full((h, w), np.nan, np.float32)
    for f in sorted((HR / "dem").glob("Copernicus_DSM_COG_30_*_DEM.tif")):
        with rasterio.open(f) as s:
            tmp = np.full((h, w), np.nan, np.float32)
            reproject(s.read(1).astype(np.float32), tmp, src_transform=s.transform, src_crs=s.crs,
                      dst_transform=from_origin(x0, y1, res, res), dst_crs="EPSG:4326",
                      resampling=Resampling.average, src_nodata=s.nodata, dst_nodata=np.nan)
            dst = np.where(np.isnan(dst), tmp, dst)
    return dst


def fig_mapa(res: dict) -> None:
    ext = (-71.15, -69.25, 18.65, 19.75)
    feats = _geoms(RES / "cuencas_yuna.geojson")
    geoms = {f["properties"]["zona"]: shape(f["geometry"]) for f in feats}
    rivs = _geoms(RES / "rios_hydrorivers.geojson")
    dem = _dem_hillshade(ext)
    adm1 = json.loads((HR / "limites" / "geoBoundaries-DOM-ADM1.geojson").read_text(encoding="utf-8"))
    m = np.load(DATA / "derivados" / "mascaras_gsw.npz")
    with style():
        fig = plt.figure(figsize=(180 * MM, 90 * MM))
        ax = fig.add_axes([0.065, 0.07, 0.64, 0.90])
        ls = LightSource(azdeg=315, altdeg=45)
        land = np.where(np.isnan(dem) | (dem <= 0), np.nan, dem)
        hs = ls.hillshade(np.nan_to_num(land, nan=0), vert_exag=0.05, dx=250, dy=250)
        ax.imshow(np.where(np.isnan(land), np.nan, hs), extent=(ext[0], ext[1], ext[2], ext[3]), cmap="Greys_r",
                  vmin=-0.2, vmax=1.4, alpha=0.45, zorder=0, interpolation="bilinear")
        for z in ("alto_hatillo", "camu", "bajo_yuna"):
            _fill_geom(ax, geoms[z], color=Z_COL[z], alpha=0.22, lw=0, zorder=1)
            _plot_geom(ax, geoms[z], color=Z_COL[z], lw=1.0, zorder=3)
        _plot_geom(ax, geoms["yuna"], color="black", lw=1.4, zorder=4)
        _plot_geom(ax, geoms["Yaque del Norte"], color=OI["purple"], lw=0.9, ls="--", zorder=3)
        _plot_geom(ax, geoms["Yaque del Sur"], color=GREY, lw=0.7, ls=":", zorder=3)
        for f in adm1["features"]:
            g = shape(f["geometry"])
            _plot_geom(ax, g, color="#7A7A7A", lw=0.25, zorder=2)
        for f in rivs:
            up = f["properties"]["UPLAND_SKM"]
            if up < 100:
                continue
            xy = np.array(f["geometry"]["coordinates"])
            ax.plot(xy[:, 0], xy[:, 1], color="#1F5FA8", lw=0.25 + 0.45 * np.log10(up / 100), zorder=5,
                    solid_capstyle="round")
        # embalse de Hatillo (GSW: ocurrencia ≥ 25 % dentro de la máscara del embalse)
        from .download import GSW_WIN
        emb = np.where(m["embalse"] & (m["occ"] >= 0.25), 1.0, np.nan)
        ax.imshow(np.ma.masked_invalid(emb), extent=(GSW_WIN[0], GSW_WIN[2], GSW_WIN[1], GSW_WIN[3]),
                  cmap=plt.matplotlib.colors.ListedColormap([OI["sky"]]), zorder=6, interpolation="nearest")
        ax.plot(HATILLO["lon"], HATILLO["lat"], marker="s", ms=4.5, mfc=OI["orange"], mec="black", mew=0.6, zorder=9)
        ax.annotate("Presa de Hatillo", (HATILLO["lon"], HATILLO["lat"]), (HATILLO["lon"] + 0.06, HATILLO["lat"] - 0.13),
                    fontsize=6, ha="left", arrowprops={"arrowstyle": "-", "lw": 0.4}, zorder=9)
        towns = ["Bonao", "La Vega (ciudad)", "Santiago (ciudad)", "Cotuí", "San Francisco de Macorís", "Villa Riva",
                 "Arenoso", "Pimentel", "Jarabacoa", "Constanza"]
        off = {"Arenoso": (0.02, 0.03), "Villa Riva": (-0.02, -0.06), "Pimentel": (0.02, 0.025), "Cotuí": (0.03, -0.02),
               "Bonao": (-0.02, -0.055), "Constanza": (-0.05, -0.055)}
        for t in towns:
            la, lo = PUNTOS[t]
            ax.plot(lo, la, "o", ms=2.3, mfc="white", mec="black", mew=0.5, zorder=8)
            dx, dy = off.get(t, (0.02, 0.015))
            ax.text(lo + dx, la + dy, t.replace(" (ciudad)", ""), fontsize=5.5, zorder=8,
                    bbox={"fc": "white", "ec": "none", "alpha": 0.6, "pad": 0.3})
        # celdas del análisis previo
        for nombre, col in (("celda_GLDAS_MonsenorNouel_18.875_-70.375", OI["vermillion"]),
                            ("celda_GLDAS_Santiago_LaVega_19.375_-70.625", OI["blue"])):
            la, lo = PUNTOS[nombre]
            ax.add_patch(Rectangle((lo - 0.125, la - 0.125), 0.25, 0.25, fill=False, ec=col, lw=0.8, ls="--", zorder=7))
        for nombre in ("celda_HR_cordillera_19.025_-70.975", "celda_HR_LaVega_19.175_-70.475"):
            la, lo = PUNTOS[nombre]
            ax.add_patch(Rectangle((lo - 0.025, la - 0.025), 0.05, 0.05, fill=False, ec="black", lw=0.9, zorder=7))
        la, lo = PUNTOS["celda_HR_cordillera_19.025_-70.975"]
        ax.text(lo, la - 0.06, "celda «cubo lleno»\n(19.025N 70.975O)", fontsize=5, ha="center", va="top", zorder=8)
        cf = res["cuencas"]["camu"]["confluencia_lonlat"]
        ax.plot(cf[0], cf[1], marker="v", ms=3.5, mfc=OI["blue"], mec="black", mew=0.4, zorder=9)
        ax.set_xlim(ext[0], ext[1]); ax.set_ylim(ext[2], ext[3])
        ax.set_aspect(1 / np.cos(np.radians(LAT0)))
        ax.set_xticks([-71, -70.5, -70, -69.5]); ax.set_xticklabels(["71°O", "70.5°O", "70°O", "69.5°O"])
        ax.set_yticks([18.75, 19, 19.25, 19.5]); ax.set_yticklabels(["18.75°N", "19°N", "19.25°N", "19.5°N"])
        ax.tick_params(labelsize=6)
        A = res["cuencas"]["areas_km2"]
        h = [Patch(fc=Z_COL[z], ec=Z_COL[z], alpha=0.35, label=f"{Z_LAB[z]} · {A[z]:,.0f} km²")
             for z in ("alto_hatillo", "camu", "bajo_yuna")]
        h += [plt.Line2D([], [], color="black", lw=1.4, label=f"Cuenca del Yuna · {A['yuna']:,.0f} km²"),
              plt.Line2D([], [], color=OI["purple"], lw=0.9, ls="--", label="Yaque del Norte"),
              plt.Line2D([], [], color=GREY, lw=0.7, ls=":", label="Yaque del Sur"),
              plt.Line2D([], [], color="#1F5FA8", lw=1, label="Ríos HydroRIVERS (≥ 100 km² drenados)"),
              Patch(fc=OI["sky"], label="Embalse (JRC GSW, ocurrencia ≥ 25 %)"),
              plt.Line2D([], [], color="#7A7A7A", lw=0.4, label="Provincias (geoBoundaries ADM1)"),
              plt.Line2D([], [], color=OI["vermillion"], lw=0.8, ls="--", label="Celdas GLDAS 0.25° del par previo"),
              plt.Line2D([], [], color="black", lw=0.9, label="Celdas 0.05° del par de alta resolución"),
              plt.Line2D([], [], marker="v", ls="", mfc=OI["blue"], mec="black", label="Confluencia Camú → Yuna")]
        fig.legend(handles=h, loc="upper left", bbox_to_anchor=(0.715, 0.97), fontsize=5.6, frameon=False)
        fig.text(0.725, 0.08, "Relieve: Copernicus DEM 90 m (sombreado).\nCuencas: HydroBASINS v1c nivel 10 y\n"
                 "HydroRIVERS v1.0 (Lehner y Grill 2013).\nNo se usó hidrografía del IGN.", fontsize=5.3, va="bottom")
        save(fig, FIG / "fig_y1_cuenca_yuna", {"fuentes": ["HydroBASINS v1c", "HydroRIVERS v1.0", "Copernicus DEM GLO-90",
                                                          "JRC GSW v1.4", "geoBoundaries ADM1"]})


def _evento_meses(cat):
    c = cat[cat["usable_backtest"]]
    return [(pd.Timestamp(r.inicio), pd.Timestamp(r.fin), r.id) for r in c.itertuples()]


def fig_gsw(res: dict) -> None:
    from .observacion import anomalias
    w = res["w"]
    an = anomalias(w, "llanura")
    emb = anomalias(w, "embalse", 0.5)
    ev = _evento_meses(res["cat"])
    with style():
        fig, axs = plt.subplots(2, 1, figsize=(180 * MM, 105 * MM), sharex=True)
        fig.subplots_adjust(left=0.08, right=0.98, top=0.92, bottom=0.09, hspace=0.35)
        ax = axs[0]
        ok = emb["usable"]
        ax.plot(emb.index[ok], emb["km2"][ok], "o-", ms=1.8, lw=0.5, color=OI["blue"])
        ax.plot(emb.index[~ok], emb["km2"][~ok], "o", ms=1.4, color="#C8C8C8", label="mes con < 50 % de píxeles válidos")
        for d_, txt in (("2016-11-16", "120 % (solo búsqueda)"), ("2017-04-24", "89.7 m, aviso de compuertas"),
                        ("2017-09-22", "87.57 m, Q salida 87 m³/s")):
            ax.axvline(pd.Timestamp(d_), color=OI["orange"], lw=0.6, ls="--")
        ax.text(pd.Timestamp("2017-06-01"), ax.get_ylim()[1] if False else 1, "", fontsize=5)
        ax.set_ylabel("Agua en el embalse (km²)", fontsize=6.5)
        ax.legend(fontsize=5.5, frameon=False, loc="lower right")
        panel_letter(ax, "a", f"Embalse de Hatillo: superficie de agua mensual (fracción de agua entre píxeles válidos × área) · {CL['gsw']}")
        ax.text(0.01, 0.06, "líneas naranjas: niveles altos reportados (16-nov-2016 solo búsqueda; 24-abr-2017; 22-sep-2017)",
                transform=ax.transAxes, fontsize=5.3, color=OI["orange"])
        ax = axs[1]
        ok = an["usable"]
        ax.bar(an.index[ok], an["anomalia"][ok] * 100, width=25, color=np.where(an["sobre_p90"][ok], OI["vermillion"], GREY))
        for a, b, i in ev:
            if a.year <= 2020:
                ax.axvspan(a, b + pd.Timedelta(days=10), color=OI["sky"], alpha=0.35, lw=0)
        ax.axhline(0, color="black", lw=0.4)
        ax.set_ylabel("Anomalía de agua en la llanura\n(p. p. de píxeles válidos)", fontsize=6.5)
        panel_letter(ax, "b", f"Llanura del Bajo Yuna (< 20 m): anomalía vs. mediana del mismo mes · {CL['gsw']}")
        ax.text(0.01, 0.92, "rojo = sobre p90 y ≥ 1 p. p. · franja azul = evento del catálogo · sin barra = mes con < 30 % de píxeles válidos",
                transform=ax.transAxes, fontsize=5.3)
        ax.xaxis.set_major_locator(mdates.YearLocator(2)); ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        ax.set_xlim(pd.Timestamp("2000-12-01"), pd.Timestamp("2021-01-31"))
        for a in axs:
            a.tick_params(labelsize=6)
        save(fig, FIG / "fig_y2_agua_observada_gsw", {"fuente": "JRC GSW Monthly Water History v1.4 (Pekel et al. 2016)",
                                                       "nota": "meses con < 30 % (llanura) o < 50 % (embalse) de píxeles válidos no se usan"})


def fig_paneles(res: dict) -> None:
    d, v, pan, w = res["d"], res["v"], res["paneles"], res["w"]
    from .observacion import anomalias
    an = anomalias(w, "llanura") if not w.empty else None
    pan = pan[pan["r48_max_yuna"].notna()] if "r48_max_yuna" in pan else pan.iloc[0:0]
    grupos = [pan.iloc[i:i + 7] for i in range(0, len(pan), 7)]
    for gi, sub in enumerate(grupos):
        with style():
            fig, axs = plt.subplots(len(sub), 4, figsize=(180 * MM, (22 + 30 * len(sub)) * MM),
                                    gridspec_kw={"width_ratios": [1.5, 1.1, 1.3, 0.9]}, squeeze=False)
            fig.subplots_adjust(left=0.07, right=0.985, top=1 - 14 / (22 + 30 * len(sub)), bottom=0.05,
                                hspace=0.55, wspace=0.42)
            for i, r in enumerate(sub.itertuples()):
                a, b = pd.Timestamp(r.inicio), pd.Timestamp(r.fin)
                t0, t1 = a - pd.Timedelta(days=60), b + pd.Timedelta(days=15)
                # (1) lluvia diaria IMERG media de cuenca + máximo de celda
                ax = axs[i, 0]
                p = d.loc[t0:t1, "imerg_media_yuna"]
                ax.bar(p.index, p.values, width=1, color=OI["blue"], lw=0)
                ax.plot(d.loc[t0:t1].index, d.loc[t0:t1, "imerg_max_yuna"], lw=0.5, color=OI["vermillion"])
                ax.axvspan(a, b, color=OI["yellow"], alpha=0.35, lw=0)
                ax.set_ylim(0, 160)
                ax.set_title(f"{r.id} · {r.nombre[:48]}", fontsize=6.2, loc="left", pad=2)
                ax.xaxis.set_major_locator(mdates.MonthLocator()); ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
                ax.set_ylabel("mm/día", fontsize=5.5)
                ax.text(0.01, 0.95, f"48 h máx: media {r.r48_max_yuna:.0f} · celda {r.r48_maxcelda_yuna:.0f} mm",
                        transform=ax.transAxes, fontsize=5, va="top")
                # (2) estado antecedente (percentil del mismo mes) por zona
                ax = axs[i, 1]
                vars_ = [("ant30", "IMERG 30 d"), ("ant90", "IMERG 90 d"), ("smap", "SMAP L4 raíz"), ("gldas", "GLDAS raíz")]
                for j, z in enumerate(("alto_hatillo", "camu", "bajo_yuna")):
                    for k, (vv, lab) in enumerate(vars_):
                        if vv == "gldas":
                            zz = getattr(r, f"gldas_z_{z}", np.nan)
                            val = float(100 * __import__("scipy").stats.norm.cdf(zz)) if np.isfinite(zz) else np.nan
                        elif vv == "smap":
                            val = getattr(r, f"smap_raiz_{z}_pct", np.nan)
                        else:
                            val = getattr(r, f"{vv}_{z}_pct", np.nan)
                        y = k + (j - 1) * 0.25
                        if np.isfinite(val):
                            ax.plot(val, y, "o", ms=2.6, color=Z_COL[z], mec="none")
                        else:
                            ax.plot(50, y, "x", ms=2.2, color="#BBBBBB", mew=0.5)
                ax.axvline(90, color="black", lw=0.4, ls="--")
                ax.set_xlim(0, 100); ax.set_ylim(-0.6, 3.6)
                ax.set_yticks(range(4)); ax.set_yticklabels([l for _, l in vars_], fontsize=5)
                ax.invert_yaxis()
                ax.set_xlabel("percentil (mismo mes)", fontsize=5, labelpad=1)
                # (3) dónde cayó la lluvia respecto a la presa: 48 h por zona (IMERG). GEOGLOWS no se dibuja: los
                #     cuatro river_id quedaron en arroyos laterales (ver informe), no en el cauce del Yuna.
                ax = axs[i, 2]
                for z in ("alto_hatillo", "camu", "bajo_yuna"):
                    s = v.loc[a - pd.Timedelta(days=15):b + pd.Timedelta(days=10), f"r48_{z}"]
                    ax.plot(s.index, s.values, lw=0.8, color=Z_COL[z])
                ax.axvspan(a, b, color=OI["yellow"], alpha=0.35, lw=0)
                ax.set_ylim(0, 320)
                ax.xaxis.set_major_locator(mdates.AutoDateLocator(maxticks=3))
                ax.xaxis.set_major_formatter(mdates.DateFormatter("%d-%b"))
                ax.set_ylabel("mm / 48 h", fontsize=5.5)
                # (4) agua observada GSW
                ax = axs[i, 3]
                if an is not None and a.year <= 2020:
                    m0 = pd.Timestamp(a.year, a.month, 1)
                    meses = [m0 - pd.offsets.MonthBegin(1), m0, m0 + pd.offsets.MonthBegin(1)]
                    for k, mm in enumerate(meses):
                        if mm in an.index:
                            rr = an.loc[mm]
                            if rr["usable"]:
                                ax.bar(k, rr["frac"] * 100, color=OI["vermillion"] if rr["sobre_p90"] else GREY, width=0.7)
                                ax.plot([k - 0.35, k + 0.35], [rr["clim_p90"] * 100] * 2, color="black", lw=0.6, ls="--")
                            else:
                                ax.text(k, 0.6, f"nubes\n{rr['validos'] * 100:.0f}%\nválido", ha="center", fontsize=4.3)
                    ax.set_xticks(range(3)); ax.set_xticklabels([mm.strftime("%b") for mm in meses], fontsize=5)
                    ax.set_ylim(0, 8)
                    ax.set_xlim(-0.6, 2.6)
                    ax.set_ylabel("% agua (válidos)", fontsize=5)
                else:
                    ax.text(0.5, 0.5, "sin observación\n(GSW termina en 2020;\nMCDWD bloqueado)", ha="center",
                            va="center", fontsize=5, transform=ax.transAxes)
                    ax.set_xticks([]); ax.set_yticks([])
                for x in axs[i]:
                    x.tick_params(labelsize=5, length=1.5, pad=1)
            heads = ["a · Lluvia diaria\nbarras: media de cuenca; línea: máx. de celda\nIMERG · RECUPERACIÓN SATELITAL",
                     "b · Antecedente (percentil del mismo mes)\nIMERG · SMAP L4 (CON ASIMILACIÓN)\nGLDAS (MODELO FORZADO)",
                     "c · Lluvia 48 h por zona\n¿cayó arriba o abajo de la presa?\nIMERG · RECUPERACIÓN SATELITAL",
                     "d · Agua en la llanura\nmes −1/0/+1 (-- = p90 del mes)\nJRC GSW · OBSERVACIÓN"]
            for k, h in enumerate(heads):
                axs[0, k].annotate(h, (0.5, 1.0), xycoords="axes fraction", xytext=(0, 14), textcoords="offset points",
                                   ha="center", va="bottom", fontsize=4.9, linespacing=1.15)
            hz = [plt.Line2D([], [], marker="o", ls="", color=Z_COL[z], label=Z_LAB[z]) for z in ("alto_hatillo", "camu", "bajo_yuna")]
            fig.legend(handles=hz, loc="lower center", ncol=3, fontsize=5.5, frameon=False, bbox_to_anchor=(0.5, 0.0))
            save(fig, FIG / f"fig_y3_paneles_eventos_{gi + 1}", {"eventos": list(sub["id"])})


def fig_backtest(res: dict) -> None:
    t = res["backtest"]
    trig = list(dict.fromkeys(t["disparador"]))
    with style():
        fig, axs = plt.subplots(1, 3, figsize=(180 * MM, 82 * MM), sharey=True)
        fig.subplots_adjust(left=0.33, right=0.98, top=0.86, bottom=0.17, wspace=0.12)
        for k, met in enumerate(("POD", "FAR", "CSI")):
            ax = axs[k]
            for j, (per, col, dy) in enumerate((("calibración 2001-2015", OI["blue"], -0.15), ("prueba 2016-2024", OI["vermillion"], 0.15))):
                s = t[t["periodo"] == per].set_index("disparador").reindex(trig)
                y = np.arange(len(trig)) + dy
                lo = np.array([c[0] for c in s[f"{met}_ic95"]]); hi = np.array([c[1] for c in s[f"{met}_ic95"]])
                ax.errorbar(s[met], y, xerr=[np.clip(s[met] - lo, 0, None), np.clip(hi - s[met], 0, None)], fmt="o",
                            ms=3, color=col, lw=0.7, capsize=1.2, label=per if k == 0 else None)
            ax.set_xlim(-0.02, 1.02)
            ax.set_title(met, fontsize=7)
            ax.grid(axis="x", lw=0.3, color="#DDDDDD")
            ax.tick_params(labelsize=5.5)
        desc = t.drop_duplicates("disparador").set_index("disparador")["descripcion"].reindex(trig)
        axs[0].set_yticks(range(len(trig)))
        axs[0].set_yticklabels([f"{k}\n{desc[k][:58]}" for k in trig], fontsize=4.8)
        axs[0].invert_yaxis()
        ncal = int(t[t["periodo"].str.startswith("cal")]["eventos"].iloc[0])
        nte = int(t[t["periodo"].str.startswith("prue")]["eventos"].iloc[0])
        fig.legend(loc="upper center", ncol=2, fontsize=6, frameon=False, bbox_to_anchor=(0.62, 1.0))
        fig.text(0.02, 0.015, f"Eventos del catálogo: {ncal} en calibración, {nte} en prueba. IC 95 % por bootstrap de años.\n"
                 "FAR = episodios sin evento / episodios (cota superior: el catálogo de prensa es incompleto).", fontsize=5.2)
        save(fig, FIG / "fig_y4_backtest_disparadores", {"tabla": "results/yuna/backtest_disparadores.csv"})


def fig_presa(res: dict) -> None:
    pr = res["presa"]
    au = pr["auc"]
    with style():
        fig, axs = plt.subplots(1, 2, figsize=(180 * MM, 72 * MM))
        fig.subplots_adjust(left=0.10, right=0.98, top=0.80, bottom=0.17, wspace=0.35)
        ax = axs[0]
        labs = [("ant30_pct", "Lluvia antecedente 30 d\n(IMERG, recuperación)"), ("gldas_z", "Raíz, mes anterior\n(GLDAS, modelo forzado)"),
                ("r48", "Lluvia del episodio 48 h\n(IMERG, recuperación)")]
        for i, (var, lab) in enumerate(labs):
            for j, z in enumerate(("alto_hatillo", "camu", "bajo_yuna")):
                a = au.get(f"AUC_{var}_{z}", np.nan); ci = au.get(f"AUC_{var}_{z}_ic95", [np.nan, np.nan])
                x = i + (j - 1) * 0.22
                ax.errorbar(x, a, yerr=[[max(a - ci[0], 0)], [max(ci[1] - a, 0)]], fmt="o", ms=3.2, color=Z_COL[z],
                            capsize=1.2, lw=0.7, label=Z_LAB[z] if i == 0 else None)
        ax.axhline(0.5, color="black", lw=0.4, ls="--")
        ax.set_xticks(range(3)); ax.set_xticklabels([l for _, l in labs], fontsize=5.3)
        ax.set_ylim(0, 1.05); ax.set_ylabel("AUC (inundación vs. no, entre episodios\nde lluvia fuerte)", fontsize=6)
        ax.legend(fontsize=5.3, frameon=False, loc="lower left")
        panel_letter(ax, "a")
        ax.text(0.06, 1.04, f"{au['n_episodios']} episodios ≥ p99 de lluvia 48 h; {au['n_con_inundacion']} con evento",
                transform=ax.transAxes, fontsize=6.2, va="bottom")
        ax = axs[1]
        if "mensual" in pr:
            m = pr["mensual"]
            m = m[m["variable"] == "lluvia_mes"]
            estados = ["todos", "embalse_alto", "embalse_bajo"]
            for j, z in enumerate(("alto_hatillo", "camu", "bajo_yuna")):
                s = m[m["zona_antecedente"] == z].set_index("estado_embalse").reindex(estados)
                x = np.arange(3) + (j - 1) * 0.22
                lo = np.array([c[0] for c in s["ic95"]]); hi = np.array([c[1] for c in s["ic95"]])
                ax.errorbar(x, s["rho"], yerr=[np.clip(s["rho"] - lo, 0, None), np.clip(hi - s["rho"], 0, None)], fmt="o",
                            ms=3.2, color=Z_COL[z], capsize=1.2, lw=0.7)
            ns = m.drop_duplicates("estado_embalse").set_index("estado_embalse")["n_meses"].reindex(estados)
            ax.set_xticks(range(3)); ax.set_xticklabels([f"{e.replace('_', ' ')}\n(n = {n} meses)" for e, n in ns.items()], fontsize=5.5)
            ax.axhline(0, color="black", lw=0.4)
            ax.set_ylim(-1, 1); ax.set_ylabel("ρ de Spearman: lluvia del mes en la zona\nvs. anomalía de agua en la llanura", fontsize=6)
            panel_letter(ax, "b")
            ax.text(0.06, 1.04, "Meses 2001-2020 · agua GSW (OBSERVACIÓN) vs. lluvia IMERG" + chr(10) +
                    "embalse alto/bajo = área de agua GSW ≥ / < mediana", transform=ax.transAxes, fontsize=6.2, va="bottom")
        for a in axs:
            a.tick_params(labelsize=5.5)
        save(fig, FIG / "fig_y5_presa_confusor", {"tablas": ["results/yuna/presa_episodios_lluvia_fuerte.csv",
                                                             "results/yuna/presa_correlaciones_mensuales.csv"]})


def run(res: dict) -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    res["cuencas"] = json.loads((RES / "cuencas_resumen.json").read_text(encoding="utf-8"))
    for f in (fig_mapa, fig_gsw, fig_paneles, fig_backtest, fig_presa):
        print(f"  figura {f.__name__}", flush=True)
        f(res)
