"""Figuras de alta resolución (matplotlib, estilo de phantom/figures.py: Okabe-Ito, letras de panel, tamaño físico
fijo, PDF + PNG + JSON de procedencia). Cada mapa dice la resolución NATIVA del producto que muestra; nada se
interpola para 'verse fino'. Bordes: geoBoundaries ADM0 (país) y ADM1 (provincias)."""

from __future__ import annotations

import numpy as np
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

from phantom.figures import GREY, MM, OI, panel_letter, save, style

from .common import GRID
from .harmonise import inside

LAT0 = 18.8
SRC = "Límites: geoBoundaries DOM ADM0 (CC BY 4.0) y ADM1 (dominio público, Natural Earth)"
NODATA = "#EDEDED"


def _borders(ax, R, lw_p=0.2, lw_c=0.45):
    for _, polys in R["provs"]:
        for ext, _h in polys:
            ax.plot(ext[:, 0], ext[:, 1], color="#6E6E6E", lw=lw_p, zorder=4)
    for ext, _h in R["country"]:
        if len(ext) > 30:
            ax.plot(ext[:, 0], ext[:, 1], color="#222222", lw=lw_c, zorder=5)


def _frame(ax, extent=None, ticks=True):
    x0, x1, y0, y1 = extent or (-72.05, -68.25, 17.45, 20.0)
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    ax.set_aspect(1 / np.cos(np.radians(LAT0)))
    ax.set_facecolor("white")
    ax.tick_params(labelsize=5.5, length=1.5, pad=1)
    if ticks and extent is None:
        ax.set_xticks([-72, -71, -70, -69])
        ax.set_xticklabels(["72°O", "71°O", "70°O", "69°O"])
        ax.set_yticks([18, 19, 20])
        ax.set_yticklabels(["18°N", "19°N", "20°N"])
    elif not ticks:
        ax.set_xticks([])
        ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_visible(True)
        sp.set_linewidth(0.4)


def grid_map(ax, R, A, cmap, norm, land=None, extent=None, ticks=True, grey_mask=None):
    """Campo en la rejilla 0.05°: solo celdas de tierra dominicana; grey_mask = celdas evaluadas sin resultado."""
    land = R["land"] if land is None else land
    if grey_mask is not None:
        G = np.where(grey_mask & land, 1.0, np.nan)
        ax.pcolormesh(GRID.lon_edges, GRID.lat_edges, np.ma.masked_invalid(G),
                      cmap=mcolors.ListedColormap([NODATA]), shading="flat", zorder=1, rasterized=True)
    m = ax.pcolormesh(GRID.lon_edges, GRID.lat_edges, np.ma.masked_invalid(np.where(land, A, np.nan)), cmap=cmap,
                      norm=norm, shading="flat", zorder=2, rasterized=True)
    _borders(ax, R)
    _frame(ax, extent, ticks)
    return m


def native_map(ax, R, lon_e, lat_e, A, lon_c, lat_c, cmap, norm, extent=None, ticks=True):
    """Campo en su rejilla nativa regular; se muestran las celdas cuyo centro cae en la RD."""
    LO, LA = np.meshgrid(lon_c, lat_c)
    ins = inside(R["country"], LO.ravel(), LA.ravel()).reshape(LO.shape)
    m = ax.pcolormesh(lon_e, lat_e, np.ma.masked_invalid(np.where(ins, A, np.nan)), cmap=cmap, norm=norm,
                      shading="flat", zorder=2, rasterized=True)
    _borders(ax, R)
    _frame(ax, extent, ticks)
    return m


def cbar(fig, m, ax, label, **kw):
    cb = fig.colorbar(m, ax=ax, orientation="horizontal", fraction=0.05, pad=0.06, aspect=28, **kw)
    cb.set_label(label, fontsize=6)
    cb.ax.tick_params(labelsize=5.5, length=1.5)
    cb.outline.set_linewidth(0.4)
    return cb


def _edges(c):
    c = np.asarray(c, float)
    d = np.diff(c)
    return np.concatenate([[c[0] - d[0] / 2], c[:-1] + d / 2, [c[-1] + d[-1] / 2]])


def _title(ax, letter, text):
    panel_letter(ax, letter)
    ax.set_title(text, fontsize=6.3, loc="left", pad=2, x=0.06)


# ------------------------------------------------------------------ F1 climatología a resolución nativa

def fig_climatologia(R, A, stem):
    nat = R["nat"]
    with style():
        fig, axes = plt.subplots(2, 3, figsize=(180 * MM, 118 * MM), layout="constrained")
        P_ann = np.nanmean(R["P_chirps"], 0) * 12
        normP = mcolors.Normalize(500, 2600)
        m = grid_map(axes[0, 0], R, P_ann, "YlGnBu", normP)
        _title(axes[0, 0], "a", "Lluvia CHIRPS v2.0 · 0.05° nativa")
        cbar(fig, m, axes[0, 0], "mm/año (2001-2024)", extend="both")
        if "imerg_P" in nat:
            la, lo = nat["imerg_lat"], nat["imerg_lon"]
            m = native_map(axes[0, 1], R, _edges(lo), _edges(la), np.nanmean(nat["imerg_P"], 0) * 12, lo, la,
                           "YlGnBu", normP)
            _title(axes[0, 1], "b", "Lluvia IMERG V07 (NASA) · 0.1° nativa")
            cbar(fig, m, axes[0, 1], "mm/año (2001-2024)", extend="both")
        la, lo = nat["tc_lat"], nat["tc_lon"]
        soil = np.nanmean(nat["tc_soil"], 0)
        m = native_map(axes[0, 2], R, _edges(lo), _edges(la), soil, lo, la, "cividis_r", mcolors.Normalize(0, 250))
        _title(axes[0, 2], "c", "Suelo TerraClimate · 1/24° nativa*")
        cbar(fig, m, axes[0, 2], "mm (media 2001-2024)", extend="max")
        if "smap_sm_rootzone" in nat:
            sm = nat["smap_sm_rootzone"]
            lat2, lon2 = nat["smap_lat"], nat["smap_lon"]
            ins = inside(R["country"], lon2.ravel(), lat2.ravel()).reshape(lat2.shape)
            le = _edges(lat2[:, lat2.shape[1] // 2])
            oe = _edges(lon2[lon2.shape[0] // 2, :])
            mm = np.where(ins, np.nanmean(sm, 0), np.nan)
            m = axes[1, 0].pcolormesh(oe, le, np.ma.masked_invalid(mm), cmap="cividis_r",
                                      norm=mcolors.Normalize(0.15, 0.40), shading="flat", zorder=2, rasterized=True)
            if le[0] > le[-1]:
                pass
            _borders(axes[1, 0], R)
            _frame(axes[1, 0])
            _title(axes[1, 0], "d", "Zona de raíces SMAP L4 (NASA) · 9 km")
            cbar(fig, m, axes[1, 0], f"m³/m³ (media {str(nat['smap_meses'][0])[:7]} a {str(nat['smap_meses'][-1])[:7]})",
                 extend="both")
        ar = np.nanmean(R["tc_ppt"], 0) / np.nanmean(R["tc_pet"], 0)
        m = grid_map(axes[1, 1], R, ar, "BrBG", mcolors.TwoSlopeNorm(1.0, 0.3, 2.0))
        _title(axes[1, 1], "e", "Aridez P/PET · TerraClimate → 0.05°")
        cbar(fig, m, axes[1, 1], "P/PET (<0.65 semiárido)", extend="both")
        if "r_chirps_imerg" in A:
            la, lo = nat["imerg_lat"], nat["imerg_lon"]
            m = native_map(axes[1, 2], R, _edges(lo), _edges(la), A["r_chirps_imerg"], lo, la, "viridis",
                           mcolors.Normalize(0.5, 1.0))
            _title(axes[1, 2], "f", "Acuerdo CHIRPS–IMERG · 0.1°")
            cbar(fig, m, axes[1, 2], "r de Pearson, anomalías mensuales", extend="min")
        save(fig, stem, {"fuentes": ["CHIRPS v2.0", "IMERG V07", "TerraClimate v1.1", "SMAP L4 V008"], "limites": SRC,
                         "nota": "*TerraClimate: rejilla 1/24°, pero anomalías mensuales de ERA5 (~0.25°) y capacidad "
                                 "de agua del suelo de 0.5°. Cada panel en su rejilla nativa, sin interpolar."})


# ------------------------------------------------------------------ F2 factores estáticos

def fig_estaticos(R, stem):
    with style():
        fig, axes = plt.subplots(2, 3, figsize=(180 * MM, 112 * MM), layout="constrained")
        panels = [("sg_clay", "Arcilla 0-30 cm · SoilGrids 250 m → 0.05°", "%", "YlOrBr", mcolors.Normalize(10, 60)),
                  ("sg_sand", "Arena 0-30 cm · SoilGrids 250 m → 0.05°", "%", "YlOrBr", mcolors.Normalize(10, 55)),
                  ("dem_elev_m", "Elevación · Copernicus GLO-90 → 0.05°", "m", "cividis",
                   mcolors.Normalize(-50, 2200)),
                  ("dem_pendiente_grados", "Pendiente (Horn a 90 m) → 0.05°", "grados", "magma_r",
                   mcolors.Normalize(0, 25)),
                  ("lc_bosque", "Bosque · WorldCover 2021 → fracción 0.05°", "fracción", "Greens",
                   mcolors.Normalize(0, 1)),
                  ("lc_cultivo", "Cultivo · WorldCover 2021 → fracción 0.05°", "fracción", "Oranges",
                   mcolors.Normalize(0, 0.8))]
        for ax, (k, t, u, cm, nm), L in zip(axes.ravel(), panels, "abcdef"):
            m = grid_map(ax, R, R[k], cm, nm)
            _title(ax, L, t)
            cbar(fig, m, ax, u)
        save(fig, stem, {"fuentes": ["SoilGrids 2.0", "Copernicus DEM GLO-90", "ESA WorldCover 2021 v200"],
                         "remuestreo": "media ponderada por área (continuos); fracción de clase (WorldCover)",
                         "limites": SRC})


# ------------------------------------------------------------------ F3 umbrales

def fig_umbrales(R, T, ex, stem):
    land = R["land"]
    sup = T["sostenido"] & land
    tested = np.isfinite(T["p"]) & land
    with style():
        fig = plt.figure(figsize=(180 * MM, 120 * MM), layout="constrained")
        gs = fig.add_gridspec(2, 3)
        ax = fig.add_subplot(gs[0, 0])
        m = grid_map(ax, R, np.where(sup, T["theta"], np.nan), "viridis", mcolors.Normalize(0.2, 0.9),
                     grey_mask=tested)
        _title(ax, "a", f"Umbral θ sostenido: {int(sup.sum())} de {int(tested.sum())} celdas")
        cbar(fig, m, ax, "θ, llenado relativo (gris: sin umbral)")
        ax = fig.add_subplot(gs[0, 1])
        d = np.where(sup, T["ef_humedo"] - T["ef_seco"], np.nan)
        lim = np.nanpercentile(np.abs(d), 98) if np.isfinite(d).any() else 1
        m = grid_map(ax, R, d, "PuOr", mcolors.TwoSlopeNorm(0, -lim, lim), grey_mask=tested)
        _title(ax, "b", "Eficiencia: húmedo − seco")
        cbar(fig, m, ax, "mm/mm (llenado Q90 − Q10)")
        ax = fig.add_subplot(gs[0, 2])
        w = np.where(sup, T["theta_hi"] - T["theta_lo"], np.nan)
        m = grid_map(ax, R, w, "Greys", mcolors.Normalize(0, 0.6), grey_mask=tested)
        _title(ax, "c", "Ancho del IC 95 % de θ")
        cbar(fig, m, ax, "llenado relativo (0-1)")
        ax = fig.add_subplot(gs[1, 0:2])
        ax.plot(ex["bins_mid"], ex["bins_ef"], "o", color=OI["blue"], ms=3.5, label="pendiente local por octil de llenado")
        ff = np.linspace(ex["f"].min(), ex["f"].max(), 200)
        a_ = ex["ef_umbral"] - (ex["ef_umbral"] - ex["ef_seco"]) / (ex["theta"] - ex["f_q10"]) * (ex["theta"] - ff)
        b_ = ex["ef_umbral"] + (ex["ef_humedo"] - ex["ef_umbral"]) / (ex["f_q90"] - ex["theta"]) * (ff - ex["theta"])
        ax.plot(ff, np.where(ff <= ex["theta"], a_, b_), color=OI["vermillion"], lw=1.2, label="ajuste segmentado (M1)")
        ax.axvline(ex["theta"], color="#333333", lw=0.6, ls=(0, (4, 2)))
        if np.isfinite(ex.get("theta_lo", np.nan)):
            ax.axvspan(ex["theta_lo"], ex["theta_hi"], color=GREY, alpha=0.25, lw=0)
        ax.text(ex["theta"], ax.get_ylim()[1], f" θ = {ex['theta']:.2f}", va="top", fontsize=6)
        ax.set_xlabel("llenado relativo antecedente f = (S − S_min)/(S_max − S_min)")
        ax.set_ylabel("Eficiencia: ΔS por mm de anomalía de lluvia")
        ax.legend(frameon=False, fontsize=6, loc="upper right")
        _title(ax, "d", f"Celda ejemplo: {ex['nombre']} (CHIRPS → TerraClimate)")
        ax = fig.add_subplot(gs[1, 2])
        th = T["theta"][sup]
        ax.hist(th, bins=np.arange(0.1, 0.951, 0.05), color=OI["blue"], edgecolor="white", lw=0.4)
        ax.set_xlabel("θ (llenado)")
        ax.set_ylabel("celdas 0.05°")
        _title(ax, "e", "Distribución de umbrales sostenidos")
        save(fig, stem, {"metodo": "earthmemory/hr/thresholds.py: M0 lineal vs M1 segmentada; sup-F con bootstrap de "
                                   "residuos en bloques circulares de 12 meses (499); BH-FDR; sostenido = q<0.05 y ΔBIC>2",
                         "datos": "CHIRPS 0.05° (lluvia) y TerraClimate soil (1/24° → 0.05°), 2001-2024", "limites": SRC})


# ------------------------------------------------------------------ F3b curvas por paisaje

def fig_curvas(G, stem):
    keys = list(G)
    ar = [k for k in keys if "P/PET" in k]
    cl = [k for k in keys if "arcilla" in k]
    sm = [k for k in keys if "SMAP" in k]
    allk = [k for k in keys if k.startswith("todas")]
    cols = [OI["vermillion"], OI["orange"], OI["blue"]]
    lss = ["-", "--", ":"]
    with style():
        fig, axes = plt.subplots(1, 3, figsize=(180 * MM, 72 * MM), layout="constrained", sharey=True)
        for ax, ks, L, tt in ((axes[0], allk + ar, "a", "Por aridez (terciles P/PET)"),
                              (axes[1], allk + cl, "b", "Por arcilla 0-30 cm (terciles)"),
                              (axes[2], sm + allk, "c", "NASA SMAP L4 frente a TerraClimate")):
            for n, k in enumerate(ks):
                g = G[k]
                f = np.array(g["f"])
                lo_, hi_ = g["f_q05_q95"]
                s = (f >= lo_) & (f <= hi_)
                gray = k.startswith("todas")
                c = "#555555" if gray else (OI["green"] if "SMAP" in k else cols[(n - 1) % 3])
                ls = ":" if gray and ax is not axes[2] else ("-" if not gray else "--")
                ax.fill_between(f[s], np.array(g["ef_lo"])[s], np.array(g["ef_hi"])[s], color=c, alpha=0.15, lw=0)
                short = "SMAP L4 9 km" if "SMAP" in k else ("TerraClimate, todas" if gray else k.split(" (")[0])
                lab = f"{short}: θ={g['theta']:.2f}" + ("" if g["b5_excluye_0"] else " (n.s.)")
                ax.plot(f[s], np.array(g["ef"])[s], color=c, ls=ls if gray else lss[(n - 1) % 3] if "SMAP" not in k else "-",
                        lw=1.1, label=lab)
                ax.plot([g["theta"]], [np.interp(g["theta"], f, g["ef"])], "o", color=c, ms=3)
            ax.axhline(0, color=GREY, lw=0.5)
            ax.set_xlabel("llenado relativo antecedente f")
            ax.set_xlim(0, 1)
            ax.legend(frameon=False, fontsize=5.5, loc="lower left", handlelength=2.2)
            _title(ax, L, tt)
        axes[0].set_ylabel("eficiencia: mm de suelo por mm de lluvia extra")
        save(fig, stem, {"leyenda": "θ = umbral común del grupo; banda = IC 95 % bootstrap; n.s. = el IC del cambio de "
                                    "pendiente incluye 0", "metodo": "thresholds.pooled_curve: umbral común por grupo, efectos fijos celda×mes, bootstrap "
                                   "de bloques de tiempo compartidos (IC 95 %, banda)",
                         "datos": "CHIRPS + TerraClimate (0.05°); CHIRPS + SMAP L4 (9 km, 2015-2024)"})


# ------------------------------------------------------------------ F4 quiebres

def fig_quiebres(R, C, stem):
    """Lo que diría Pettitt sin corregir (fila 1) frente a lo que sobrevive con bootstrap por bloques (fila 2)."""
    land = R["land"]
    names = {"tc_soil": "Suelo (TerraClimate)", "tc_def": "Déficit hídrico (TerraClimate)", "P_chirps": "Lluvia (CHIRPS)"}
    months = np.array(R["meses"], dtype="datetime64[M]")
    mo = months.astype(int) % 12
    with style():
        fig = plt.figure(figsize=(180 * MM, 125 * MM), layout="constrained")
        gs = fig.add_gridspec(2, 3, height_ratios=[1, 1])
        cmap = plt.get_cmap("cividis", 6)
        for c, k in enumerate(("tc_soil", "tc_def", "P_chirps")):
            Ck = C[k]
            sig = (Ck["q_asintotica"] < 0.05) & land
            ax = fig.add_subplot(gs[0, c])
            m = grid_map(ax, R, np.where(sig, Ck["anio"], np.nan), cmap,
                         mcolors.BoundaryNorm(np.arange(2002, 2027, 4), cmap.N), grey_mask=land)
            _title(ax, "abc"[c], f"{names[k]}: Pettitt SIN corregir")
            cbar(fig, m, ax, f"año del quiebre · {int(sig.sum())} de {int(land.sum())} celdas q<0.05")
        ax = fig.add_subplot(gs[1, 0])
        m = grid_map(ax, R, C["tc_soil"]["p"], "Greys_r", mcolors.Normalize(0, 1))
        nsig = int(((C["tc_soil"]["q"] < 0.05) & land).sum())
        _title(ax, "d", "Suelo: p con bootstrap por bloques")
        cbar(fig, m, ax, f"p (bloques de 12 meses) · {nsig} celdas con q<0.05")
        ax = fig.add_subplot(gs[1, 1:])
        w = (R["frac_rd"] * GRID.area_km2())[land]
        t = months.astype("datetime64[D]")
        for k, col, ls, lab in (("tc_soil", OI["blue"], "-", "suelo TerraClimate"),
                                ("P_chirps", OI["vermillion"], "--", "lluvia CHIRPS")):
            X = R[k][:, land].astype(float)
            A = X.copy()
            for mm in range(12):
                s = mo == mm
                A[s] = (X[s] - X[s].mean(0)) / X[s].std(0)
            z = (A * w).sum(1) / w.sum()
            zr = np.convolve(z, np.ones(12) / 12, mode="same")
            ax.plot(t, z, color=col, lw=0.4, alpha=0.45)
            ax.plot(t[6:-6], zr[6:-6], color=col, lw=1.2, ls=ls, label=f"{lab} (media móvil 12 meses)")
        yrs = C["tc_soil"]["anio"][land]
        ymode = int(np.bincount(np.floor(yrs).astype(int) - 2000).argmax()) + 2000
        ax.axvline(np.datetime64(f"{ymode}-01-01"), color="#333333", lw=0.6, ls=(0, (4, 2)))
        ax.text(np.datetime64(f"{ymode}-03-01"), ax.get_ylim()[1] * 0.92, f"quiebre más frecuente\nsin corregir: {ymode}",
                fontsize=6, va="top")
        ax.axhline(0, color=GREY, lw=0.5)
        ax.set_ylabel("anomalía estandarizada\n(media nacional ponderada por área)")
        ax.legend(frameon=False, fontsize=6, loc="lower left")
        _title(ax, "e", "La señal nacional: ¿cambio de régimen o persistencia?")
        save(fig, stem, {"metodo": "Pettitt sobre anomalías mensuales; fila 1: p asintótica (supone independencia) + "
                                   "BH; panel d: p por bootstrap de bloques circulares de 12 meses (999, mismos índices "
                                   "para todas las celdas)", "limites": SRC})


# ------------------------------------------------------------------ F5 factores del umbral

def fig_factores(D, stem):
    resp = [k for k in D if "coef" in D[k]]
    with style():
        fig, axes = plt.subplots(1, len(resp), figsize=(180 * MM, 82 * MM), layout="constrained", sharey=True)
        axes = np.atleast_1d(axes)
        for ax, k, L in zip(axes, resp, "abc"):
            d = D[k]
            names = list(d["coef"])
            y = np.arange(len(names))[::-1]
            b = np.array([d["coef"][n]["beta_z"] for n in names])
            lo = np.array([d["coef"][n]["ic95"][0] for n in names])
            hi = np.array([d["coef"][n]["ic95"][1] for n in names])
            ex = np.array([d["coef"][n]["excluye_0"] for n in names])
            ax.hlines(y, lo, hi, color="#333333", lw=0.8)
            ax.plot(b[ex], y[ex], "o", color=OI["vermillion"], ms=3.5)
            ax.plot(b[~ex], y[~ex], "o", mfc="white", mec="#333333", ms=3.5)
            ax.axvline(0, color=GREY, lw=0.6)
            ax.set_yticks(y)
            ax.set_yticklabels(names)
            ax.set_xlabel("β estandarizado (IC 95 %)")
            _title(ax, L, d["titulo"] + "\n" + f"R² VC espacial {d['r2_cv_espacial']:.2f} · aleatoria "
                   f"{d['r2_cv_aleatoria']:.2f}\nMoran {d['moran_residuos']['I']:.2f} · n = {d['n']}")
        save(fig, stem, {"metodo": "ridge estandarizado; λ por VC; VC externa dejando fuera bloques de 0.5°; IC por "
                                   "bootstrap de bloques espaciales (500)"})


# ------------------------------------------------------------------ F6 par

def fig_par(R, Pr, stem):
    a, b = Pr["celdas"]
    (ia, ja), (ib, jb) = a["ij"], b["ij"]
    t = np.array(R["meses"], dtype="datetime64[M]")
    with style():
        fig = plt.figure(figsize=(180 * MM, 135 * MM), layout="constrained")
        gs = fig.add_gridspec(3, 3, height_ratios=[1.15, 1, 1])
        ax = fig.add_subplot(gs[0, 0])
        lat_c, lon_c = (a["lat"] + b["lat"]) / 2, (a["lon"] + b["lon"]) / 2
        ext = (lon_c - 0.55, lon_c + 0.55, lat_c - 0.38, lat_c + 0.38)
        m = grid_map(ax, R, R["dem_pendiente_grados"], "Greys", mcolors.Normalize(0, 30), extent=ext)
        for c, col, mk in ((a, OI["blue"], "A"), (b, OI["vermillion"], "B")):
            ax.add_patch(Rectangle((c["lon"] - 0.025, c["lat"] - 0.025), 0.05, 0.05, fill=False, ec=col, lw=1.4, zorder=6))
            ax.text(c["lon"] + 0.035, c["lat"], mk, color=col, fontsize=8, fontweight="bold", va="center", zorder=7)
        ax.tick_params(labelsize=5)
        _title(ax, "a", f"Par a {Pr['dist_km']:.0f} km (fondo: pendiente)")
        cbar(fig, m, ax, "pendiente (grados)")
        ax = fig.add_subplot(gs[0, 1])
        for c, col, ls in ((a, OI["blue"], "-"), (b, OI["vermillion"], "--")):
            v = np.sort(R["P_chirps"][:, c["ij"][0], c["ij"][1]])
            ax.plot(v, np.arange(1, v.size + 1) / v.size, color=col, ls=ls, lw=1.1)
        ax.set_xlabel("lluvia mensual CHIRPS (mm)")
        ax.set_ylabel("probabilidad acumulada")
        _title(ax, "b", "Misma lluvia (CHIRPS)")
        ax.text(0.97, 0.05, f"r = {Pr['r_lluvia']:.2f}\nKS D = {Pr['ks_D']:.2f}\nΔ media = {100 * Pr['dif_rel_lluvia']:.1f} %",
                transform=ax.transAxes, ha="right", va="bottom", fontsize=6)
        ax = fig.add_subplot(gs[0, 2])
        for c, col, mk in ((a, OI["blue"], "o"), (b, OI["vermillion"], "s")):
            ax.plot(c["Pa"], c["yd"], mk, ms=1.6, color=col, alpha=0.45, mew=0)
            xx = np.array([np.percentile(c["Pa"], 1), np.percentile(c["Pa"], 99)])
            ax.plot(xx, c["ef"] * xx, color=col, lw=1.4)
        ax.axhline(0, color=GREY, lw=0.5)
        ax.axvline(0, color=GREY, lw=0.5)
        ax.set_xlabel("anomalía de lluvia (mm/mes)")
        ax.set_ylabel("ΔS centrado (mm/mes)")
        _title(ax, "c", "Distinta respuesta")
        ax.text(0.97, 0.03, f"e_A = {a['ef']:.3f}\ne_B = {b['ef']:.3f}\nq = {Pr['q']:.3g}"
                + ("" if Pr.get("supera_fdr") else "\n(NO supera FDR)"), transform=ax.transAxes, va="bottom", ha="right", fontsize=6)
        ax = fig.add_subplot(gs[1, :])
        for c, col, ls, mk in ((a, OI["blue"], "-", "A"), (b, OI["vermillion"], "--", "B")):
            ax.plot(t.astype("datetime64[D]"), c["S"], color=col, ls=ls, lw=0.8, label=f"{mk}: {c['nombre']}")
        ax.set_ylabel("humedad del suelo\nTerraClimate (mm)")
        lo_, hi_ = ax.get_ylim()
        ax.set_ylim(lo_, hi_ + 0.3 * (hi_ - lo_))
        ax.legend(frameon=False, fontsize=6, ncol=2, loc="upper left")
        _title(ax, "d", "Serie mensual 2001-2024 (TerraClimate, 1/24° → 0.05°)")
        ax = fig.add_subplot(gs[2, 0:2])
        if Pr.get("smap"):
            tm = np.array(Pr["smap"]["meses"], dtype="datetime64[M]").astype("datetime64[D]")
            for c, col, ls in ((("A", OI["blue"], "-")), ("B", OI["vermillion"], "--")):
                ax.plot(tm, Pr["smap"][f"sm_{c}"], color=col, ls=ls, lw=0.9)
            ax.set_ylabel("zona de raíces SMAP L4\n(m³/m³, 9 km)")
            _title(ax, "e", f"NASA SMAP L4 9 km: Δe = {Pr['smap']['delta']:.3f} (p = {Pr['smap']['p']:.3g}), misma dirección: "
                            f"{'sí' if Pr['smap']['misma_direccion'] else 'no'}")
        else:
            ax.text(0.5, 0.5, "SMAP L4 no disponible", ha="center", transform=ax.transAxes)
            ax.set_axis_off()
        ax = fig.add_subplot(gs[2, 2])
        fac = Pr["factores"]
        names = list(fac)
        y = np.arange(len(names))[::-1]
        va = np.array([fac[n][0] for n in names])
        vb = np.array([fac[n][1] for n in names])
        ax.barh(y + 0.18, va, height=0.34, color=OI["blue"])
        ax.barh(y - 0.18, vb, height=0.34, color=OI["vermillion"], hatch="////", edgecolor="white", lw=0)
        ax.set_yticks(y)
        ax.set_yticklabels(names)
        ax.set_xlabel("valor")
        _title(ax, "f", "Suelo y terreno")
        ax.text(0.98, 0.02, "A sólido · B rayado", transform=ax.transAxes, ha="right", fontsize=5.5)
        save(fig, stem, {"metodo": "earthmemory/hr/pair.py", "limites": SRC,
                         "nota": "Asociación: la diferencia de eficiencia acompaña a diferencias de suelo/terreno; "
                                 "no demuestra que las cause."})


# ------------------------------------------------------------------ F7 evento 18-nov-2023

def fig_evento(R, E, stem):
    nat = R["nat"]
    ext = (-70.45, -69.35, 18.25, 18.95)
    with style():
        fig = plt.figure(figsize=(180 * MM, 108 * MM), layout="constrained")
        gs = fig.add_gridspec(2, 3)
        norm = mcolors.PowerNorm(0.6, 0, max(250, E["max_pentada_chirps"]))
        ax = fig.add_subplot(gs[0, 0])
        Pd = R["Pd_nov2023"]
        m = grid_map(ax, R, Pd[17], "YlGnBu", norm, extent=ext)
        _title(ax, "a", "CHIRPS 18-nov · día repartido (CFSv2)")
        ax = fig.add_subplot(gs[0, 1])
        m = grid_map(ax, R, Pd[15:20].sum(0), "YlGnBu", norm, extent=ext)
        _title(ax, "b", "CHIRPS péntada 16-20 nov · 0.05°")
        ax3 = fig.add_subplot(gs[0, 2])
        if "imerg_Pd_nov2023" in nat:
            la, lo = nat["imerg_lat"], nat["imerg_lon"]
            m = native_map(ax3, R, _edges(lo), _edges(la), nat["imerg_Pd_nov2023"][17], lo, la, "YlGnBu", norm, extent=ext)
            _title(ax3, "c", "IMERG 18-nov (NASA) · 0.1°")
        for ax in fig.axes:
            ax.plot(E["lon"], E["lat"], marker="*", color=OI["vermillion"], ms=7, mec="black", mew=0.4, zorder=8)
            ax.tick_params(labelsize=5)
        cbar(fig, m, ax3, "mm (misma escala en a, b y c)", extend="max")
        ax = fig.add_subplot(gs[1, :])
        labels = list(E["barras"])
        vals = [E["barras"][k] for k in labels]
        cols = [OI["vermillion"] if "estación" in k else (OI["green"] if "IMERG" in k else OI["blue"]) for k in labels]
        ax.barh(np.arange(len(labels))[::-1], vals, color=cols, height=0.6)
        for yy, v in zip(np.arange(len(labels))[::-1], vals):
            ax.text(v + 4, yy, f"{v:.0f} mm", va="center", fontsize=6)
        ax.set_yticks(np.arange(len(labels))[::-1])
        ax.set_yticklabels(labels, fontsize=6)
        ax.set_xlabel("lluvia (mm)")
        _title(ax, "d", "Estación (preliminar) frente a celdas de satélite en la posición aproximada de Arroyo Hondo Viejo")
        save(fig, stem, {"estacion": "ONAMET Arroyo Hondo Viejo, 431 mm el 18-nov-2023 (preliminar, según prensa: Acento)",
                         "posicion_estacion": "aproximada (barrio Arroyo Hondo Viejo, ±2 km); no son coordenadas oficiales",
                         "limites": SRC})
