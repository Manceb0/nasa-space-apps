"""Figuras de artículo (matplotlib): mapas de tendencia IMERG | CHIRPS, mapa de clases de confianza, series por
provincia con Theil-Sen e IC, calibración de falsos positivos y tendencia mínima detectable. PNG 220 ppp + PDF."""

from __future__ import annotations

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.colors import BoundaryNorm, ListedColormap, TwoSlopeNorm  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

from ..hr.common import ROOT  # noqa: E402
from . import datos  # noqa: E402
from . import indices as ix  # noqa: E402
from .motor import NATIONAL  # noqa: E402

FIG = ROOT / "figures" / "tendencias"
G = datos.GRID01
DRY = {"CDD", "RACHAS10", "RACHAS15", "SPI3_MESES", "SPI3_EVENTOS", "SPI3_SEVER", "SPI3_DURAC", "SPI12_MESES",
       "SPI12_EVENTOS", "SPI12_SEVER", "SPI12_DURAC"}
CLASS_COL = {"robusta": "#0072B2", "consistente": "#56B4E9", "en disputa": "#D55E00", "sin señal detectable": "#E6E6E6"}
PROD_COL = {"IMERG": "#0072B2", "CHIRPS": "#E69F00"}
SRC = "Fuentes: NASA GPM IMERG V07 Final diario 0.1° y CHIRPS v2.0 diario 0.05° (agregado a 0.1°), 2001-2024."

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8, "axes.titlesize": 9, "axes.labelsize": 8,
                     "xtick.labelsize": 7, "ytick.labelsize": 7, "legend.fontsize": 7, "axes.linewidth": 0.6,
                     "savefig.bbox": "tight", "savefig.pad_inches": 0.06, "pdf.fonttype": 42})


def save(fig, name: str) -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / f"{name}.png", dpi=220)
    fig.savefig(FIG / f"{name}.pdf")
    plt.close(fig)


_RINGS = None


def rings():
    global _RINGS
    if _RINGS is None:
        gj = datos.adm1_geojson()
        out = []
        for f in gj["features"]:
            g = f["geometry"]
            polys = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
            for p in polys:
                out.append(np.asarray(p[0]))
        _RINGS = out
    return _RINGS


def to_grid(df: pd.DataFrame, col: str) -> np.ndarray:
    A = np.full((G.ny, G.nx), np.nan)
    i = np.round((df["lat"].to_numpy() - G.lat[0]) / G.res).astype(int)
    j = np.round((df["lon"].to_numpy() - G.lon[0]) / G.res).astype(int)
    A[i, j] = df[col].to_numpy(float)
    return A


def base_map(ax, lab_left=True, lab_bottom=True, scale=True):
    for r in rings():
        ax.plot(r[:, 0], r[:, 1], color="#333333", lw=0.35, zorder=4)
    ax.set_xlim(-72.1, -68.25)
    ax.set_ylim(17.45, 20.0)
    ax.set_aspect(1 / np.cos(np.radians(18.8)))
    ax.set_xticks([-72, -71, -70, -69])
    ax.set_yticks([18, 19, 20])
    ax.set_xticklabels([f"{abs(v)}°O" for v in [-72, -71, -70, -69]] if lab_bottom else [])
    ax.set_yticklabels([f"{v}°N" for v in [18, 19, 20]] if lab_left else [])
    ax.tick_params(length=2, pad=1.5)
    if scale:
        km = 100
        dlon = km / (111.32 * np.cos(np.radians(17.7)))
        x0, y0 = -69.35, 19.80
        ax.plot([x0, x0 + dlon], [y0, y0], color="k", lw=1.6, solid_capstyle="butt", zorder=6)
        ax.text(x0 + dlon / 2, y0 + 0.06, f"{km} km", ha="center", va="bottom", fontsize=6.5, zorder=6)


def stipple(ax, df: pd.DataFrame, mask_col: str = "sig_fdr"):
    s = df[df[mask_col].astype(bool)]
    ax.scatter(s["lon"], s["lat"], s=2.6, c="k", marker="o", linewidths=0, zorder=5)


def trend_map_pair(tc: pd.DataFrame, idx: str, per: str = "anual", name: str | None = None, axes=None, row_label=True):
    lab, _, unit = ix.VARIABLES[idx][:3]
    sub = tc[(tc["indice"] == idx) & (tc["periodo"] == per)]
    v = sub["pendiente_decada"].to_numpy(float)
    vmax = float(np.nanpercentile(np.abs(v), 98)) or 1.0
    cmap = plt.get_cmap("BrBG_r" if idx in DRY else "BrBG")
    own = axes is None
    if own:
        fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.55), constrained_layout=True)
    for k, (ax, prod) in enumerate(zip(axes, ["IMERG", "CHIRPS"])):
        d = sub[sub["fuente"] == prod]
        A = to_grid(d, "pendiente_decada")
        m = ax.pcolormesh(G.lon_edges, G.lat_edges, A, cmap=cmap, norm=TwoSlopeNorm(0, -vmax, vmax), shading="flat",
                          rasterized=True)
        base_map(ax, lab_left=(k == 0), lab_bottom=True, scale=(k == 0))
        stipple(ax, d)
        nsig = int(d["sig_fdr"].sum())
        ax.set_title(f"{'abcdefgh'[k] if own else ''}{')' if own else ''} {prod}: {nsig} de {int(d['p'].notna().sum())} celdas q≤0.10".strip(),
                     loc="left", fontsize=8)
    cb = axes[0].figure.colorbar(m, ax=list(axes), shrink=0.9, pad=0.01, extend="both")
    cb.set_label(f"{unit} por década", fontsize=7)
    cb.ax.tick_params(labelsize=6.5)
    if own:
        fig.suptitle(f"Tendencia de {lab[0].lower() + lab[1:]} ({idx}, {ix.PERIODS[per][0].lower()}), Theil-Sen por década", fontsize=9, x=0.01,
                     ha="left")
        fig.text(0.01, -0.04, "Puntos: celdas con tendencia significativa tras FDR (Mann-Kendall de Hamed-Rao, q ≤ 0.10 = "
                 "2·α_global, Wilks 2016). " + ("Marrón = más seco. " if idx in DRY else "Verde-azul = aumento (más lluvia o lluvia más intensa). ")
                 + SRC, fontsize=6.3, ha="left", va="top", wrap=True)
        save(fig, name or f"mapa_tendencia_{idx}_{per}")


def fig_trend_maps(tc):
    for idx in ["CDD", "Rx5day", "R95pTOT", "SPI3_MESES", "SDII", "R1mm", "RACHAS15", "PRCPTOT"]:
        trend_map_pair(tc, idx)
    # panel combinado de 4 índices
    sel = ["CDD", "Rx5day", "R95pTOT", "SPI3_MESES"]
    fig, axs = plt.subplots(4, 2, figsize=(7.2, 9.4), constrained_layout=True)
    for r, idx in enumerate(sel):
        trend_map_pair(tc, idx, axes=axs[r], row_label=False)
        lab = ix.VARIABLES[idx][0]
        for k, ax in enumerate(axs[r]):
            t = ax.get_title(loc="left")
            ax.set_title(f"{'abcdefgh'[2 * r + k]}) {idx} · {t}", loc="left", fontsize=7.5)
        axs[r, 0].text(-0.16, 0.5, lab, transform=axs[r, 0].transAxes, rotation=90, va="center", ha="center", fontsize=7.5)
    fig.suptitle("Tendencias 2001-2024 de periodos secos y lluvia extrema (Theil-Sen por década; anual)", x=0.01,
                 ha="left", fontsize=9)
    fig.text(0.01, -0.012, "Puntos negros: celdas significativas tras FDR (Hamed-Rao, q ≤ 0.10, Wilks 2016). Marrón = más seco "
             "(CDD y meses SPI-3 ≤ −1 en aumento, o lluvia extrema en descenso). " + SRC, fontsize=6.3, ha="left", va="top",
             wrap=True)
    save(fig, "fig1_mapas_tendencia_IMERG_vs_CHIRPS")


def fig_classes(tc):
    sel = [("CDD", "anual"), ("Rx5day", "anual"), ("R95pTOT", "anual"), ("SPI3_MESES", "anual"), ("SDII", "anual"),
           ("R1mm", "anual"), ("RACHAS15", "anual"), ("PRCPTOT", "anual"), ("RACHAS15", "seca")]
    order = list(CLASS_COL)
    cmap = ListedColormap([CLASS_COL[c] for c in order])
    norm = BoundaryNorm(np.arange(len(order) + 1) - 0.5, len(order))
    fig, axs = plt.subplots(3, 3, figsize=(7.4, 5.6), constrained_layout=True)
    for k, ((idx, per), ax) in enumerate(zip(sel, axs.ravel())):
        d = tc[(tc["indice"] == idx) & (tc["periodo"] == per) & (tc["fuente"] == "IMERG")].copy()
        d["code"] = d["clase_confianza"].map({c: i for i, c in enumerate(order)})
        A = to_grid(d, "code")
        ax.pcolormesh(G.lon_edges, G.lat_edges, A, cmap=cmap, norm=norm, shading="flat", rasterized=True)
        base_map(ax, lab_left=(k % 3 == 0), lab_bottom=(k >= 6), scale=(k == 6))
        dd = d[d["clase_confianza"].isin(["robusta", "consistente"])]
        up, dn = dd[dd["signo"] > 0], dd[dd["signo"] < 0]
        ax.scatter(up["lon"], up["lat"], marker="^", s=3.5, c="k", linewidths=0, zorder=5)
        ax.scatter(dn["lon"], dn["lat"], marker="v", s=3.5, c="w", edgecolors="k", linewidths=0.2, zorder=5)
        n = d["clase_confianza"].value_counts()
        per_lab = "" if per == "anual" else f" ({ix.PERIODS[per][0].split(' (')[0].lower()})"
        ax.set_title(f"{'abcdefghi'[k]}) {idx}{per_lab}: rob. {n.get('robusta', 0)}, cons. {n.get('consistente', 0)}, "
                     f"disp. {n.get('en disputa', 0)}", loc="left", fontsize=7)
    handles = [Patch(color=CLASS_COL[c], label=c) for c in order] + [
        Line2D([], [], marker="^", ls="", color="k", ms=4, label="aumento"),
        Line2D([], [], marker="v", ls="", mfc="w", mec="k", ms=4, label="descenso")]
    fig.legend(handles=handles, loc="lower center", ncol=6, bbox_to_anchor=(0.5, -0.045), frameon=False)
    fig.suptitle("Clase de confianza de dos productos (IMERG vs CHIRPS en la rejilla común de 0.1°), 2001-2024", x=0.01,
                 ha="left", fontsize=9)
    fig.text(0.01, -0.075, "robusta: ambos productos con tendencia FDR-significativa (q ≤ 0.10) y el mismo signo; consistente: "
             "mismo signo y solo uno significativo; en disputa: signos opuestos con al menos uno significativo; sin señal "
             "detectable: ninguno significativo (no implica 'sin cambio', ver la tendencia mínima detectable). " + SRC,
             fontsize=6.3, ha="left", va="top", wrap=True)
    save(fig, "fig2_clases_de_confianza")


def fig_province_series(sr: pd.DataFrame, tr: pd.DataFrame, idx: str, per: str = "anual"):
    lab, _, unit = ix.VARIABLES[idx][:3]
    regs = [NATIONAL] + sorted(r for r in sr["region"].unique() if r != NATIONAL)
    nc = 6
    nr = int(np.ceil(len(regs) / nc))
    fig, axs = plt.subplots(nr, nc, figsize=(7.4, 1.18 * nr + 0.4), sharex=True, constrained_layout=True)
    s = sr[(sr["indice"] == idx) & (sr["periodo"] == per)]
    t = tr[(tr["indice"] == idx) & (tr["periodo"] == per)]
    for k, ax in enumerate(axs.ravel()):
        if k >= len(regs):
            ax.axis("off")
            continue
        reg = regs[k]
        cls = ""
        for prod in ["IMERG", "CHIRPS"]:
            d = s[(s["region"] == reg) & (s["fuente"] == prod)].sort_values("anio")
            if d.empty:
                continue
            x, y = d["anio"].to_numpy(float), d["valor"].to_numpy(float)
            tt = t[(t["region"] == reg) & (t["fuente"] == prod)].iloc[0]
            col = PROD_COL[prod]
            ax.plot(x, y, color=col, lw=0.7, alpha=0.85)
            xm, ym = np.median(x[np.isfinite(y)]), np.median(y[np.isfinite(y)])
            xx = np.array([x.min(), x.max()])
            b, lo, hi = tt["pendiente_decada"] / 10, tt["ic95_inf"] / 10, tt["ic95_sup"] / 10
            # banda: rectas por la mediana con las pendientes del IC 95 % de Sen
            ylo = np.minimum(ym + lo * (xx - xm), ym + hi * (xx - xm))
            yhi = np.maximum(ym + lo * (xx - xm), ym + hi * (xx - xm))
            xs = np.linspace(xx[0], xx[1], 30)
            ax.fill_between(xs, np.interp(xs, [xx[0], xm, xx[1]], [ylo[0], ym, ylo[1]]),
                            np.interp(xs, [xx[0], xm, xx[1]], [yhi[0], ym, yhi[1]]), color=col, alpha=0.15, lw=0)
            ax.plot(xx, ym + b * (xx - xm), color=col, lw=1.3 if tt["sig_fdr"] or reg == NATIONAL and tt["p"] < 0.05 else 0.9,
                    ls="-" if (tt["sig_fdr"] or (reg == NATIONAL and tt["p"] < 0.05)) else "--")
            cls = tt["clase_confianza"]
        name = "Nacional (RD)" if reg == NATIONAL else (reg if len(reg) <= 18 else reg[:17] + ".")
        ax.set_title(f"{name}\n{cls}", fontsize=6.2, loc="left", pad=1.5,
                     fontweight="bold" if reg == NATIONAL else "normal")
        ax.tick_params(labelsize=5.8, length=1.5, pad=1)
        ax.set_xticks([2005, 2015, 2024])
        ax.grid(alpha=0.25, lw=0.3)
    handles = [Line2D([], [], color=PROD_COL[p], lw=1.2, label=p) for p in PROD_COL] + [
        Line2D([], [], color="0.3", lw=1.3, label="Theil-Sen, significativa (FDR q≤0.10)"),
        Line2D([], [], color="0.3", lw=0.9, ls="--", label="Theil-Sen, no significativa"),
        Patch(color="0.5", alpha=0.25, label="IC 95 % de la pendiente")]
    fig.legend(handles=handles, loc="lower center", ncol=5, bbox_to_anchor=(0.5, -0.035), frameon=False, fontsize=6.5)
    fig.suptitle(f"{lab} ({idx}, {ix.PERIODS[per][0].lower()}, {unit}) por provincia: series anuales y tendencia", x=0.01,
                 ha="left", fontsize=9)
    fig.text(0.01, -0.05, "Serie de provincia = media ponderada por área de los índices de las celdas 0.1°. Debajo del nombre, "
             "la clase de confianza de dos productos. FDR entre las 32 provincias; en el panel nacional, línea continua = p < 0.05. " + SRC, fontsize=6.2, ha="left",
             va="top", wrap=True)
    save(fig, f"fig3_provincias_{idx}_{per}")


def fig_calibration(cal: pd.DataFrame):
    c = cal[cal["nivel"] == "celdas"].copy()
    c["met"] = np.where(c["metodo"].str.startswith("fases"), "fase", "bloques")
    idxs = list(dict.fromkeys(c["indice"]))
    fig = plt.figure(figsize=(7.4, 4.3), layout="constrained")
    gs = fig.add_gridspec(2, 3, height_ratios=[1, 0.22], width_ratios=[1.4, 1, 1])
    axs = [fig.add_subplot(gs[0, i]) for i in range(3)]
    lax = fig.add_subplot(gs[1, :])
    lax.axis("off")
    y = np.arange(len(idxs))
    mk = {("IMERG", "fase"): ("o", PROD_COL["IMERG"], "full"), ("IMERG", "bloques"): ("s", PROD_COL["IMERG"], "none"),
          ("CHIRPS", "fase"): ("o", PROD_COL["CHIRPS"], "full"), ("CHIRPS", "bloques"): ("s", PROD_COL["CHIRPS"], "none")}
    off = {("IMERG", "fase"): -0.27, ("IMERG", "bloques"): -0.09, ("CHIRPS", "fase"): 0.09, ("CHIRPS", "bloques"): 0.27}
    for (prod, met), (m, col, fill) in mk.items():
        d = c[(c["fuente"] == prod) & (c["met"] == met)].set_index("indice").reindex(idxs)
        lo_hi = np.array([[float(v) for v in str(s).split("-")] if isinstance(s, str) else [np.nan, np.nan]
                          for s in d["fpr_local_p05_ic95"]])
        yy = y + off[(prod, met)]
        axs[0].errorbar(d["fpr_local_p05"], yy, xerr=[d["fpr_local_p05"] - lo_hi[:, 0], lo_hi[:, 1] - d["fpr_local_p05"]],
                        fmt=m, color=col, mfc=col if fill == "full" else "white", ms=3, lw=0.6, capsize=0,
                        label=f"{prod}, {'fases' if met == 'fase' else 'bloques 3 años'}")
        axs[1].plot(d["fraccion_mapas_nulos_con_celda_fdr"], yy, m, color=col, mfc=col if fill == "full" else "white", ms=3)
        axs[2].plot(d["p_campo_bootstrap"], yy, m, color=col, mfc=col if fill == "full" else "white", ms=3)
    axs[0].axvline(0.05, color="k", lw=0.7, ls=":")
    axs[1].axvline(0.05, color="k", lw=0.7, ls=":")
    axs[2].axvline(0.05, color="k", lw=0.7, ls=":")
    axs[0].set_yticks(y, idxs)
    for ax in axs[1:]:
        ax.set_yticks(y, [])
    for ax in axs:
        ax.invert_yaxis()
        ax.grid(axis="x", alpha=0.3, lw=0.3)
    axs[0].set_xlabel("tasa de p < 0.05 por celda\nbajo el nulo (FPR local)")
    axs[1].set_xlabel("fracción de mapas nulos\ncon ≥1 celda q ≤ 0.10")
    axs[2].set_xlabel("p de campo\n(nº de celdas p<0.05 vs. nulo)")
    axs[0].set_title("a) Falsos positivos locales", loc="left")
    axs[1].set_title("b) Error de campo", loc="left")
    axs[2].set_title("c) Campo observado", loc="left")
    h, l = axs[0].get_legend_handles_labels()
    lax.legend(h, l, loc="upper center", ncol=4, frameon=False, fontsize=6.5)
    n = int(c["n_sustitutos"].iloc[0])
    fig.suptitle(f"Calibración con sustitutos nulos ({n} por método e índice; índices anuales, celdas 0.1°)", x=0.01, ha="left",
                 fontsize=9)
    lax.text(0.0, 0.45, "Campos sin tendencia que conservan la autocorrelación y la correlación espacial: fases aleatorias "
             "multivariadas (Prichard y Theiler 1994) o bloques circulares de 3 años comunes a todas las celdas; en cada uno "
             "se repite la prueba de la corrida (Mann-Kendall de Hamed-Rao + FDR). Línea punteada: 0.05 nominal. Barras: "
             "IC 95 % entre sustitutos. " + SRC, fontsize=6.2, ha="left", va="top", wrap=True)
    save(fig, "fig4_calibracion_falsos_positivos")


def fig_mdt(tr: pd.DataFrame):
    d = tr[(tr["region"] == NATIONAL) & (tr["periodo"] == "anual")].copy()
    idxs = [i for i in ix.DAILY + ix.SPI_KEYS if i in set(d["indice"])]
    fig = plt.figure(figsize=(7.2, 4.6), layout="constrained")
    gs = fig.add_gridspec(2, 1, height_ratios=[1, 0.24])
    ax = fig.add_subplot(gs[0])
    lax = fig.add_subplot(gs[1])
    lax.axis("off")
    y = np.arange(len(idxs))
    for k, prod in enumerate(["IMERG", "CHIRPS"]):
        g = d[d["fuente"] == prod].set_index("indice").reindex(idxs)
        if g["media"].isna().all():
            continue
        m = g["media"].abs()
        s = 100 * g["pendiente_decada"] / m
        lo, hi = 100 * g["ic95_inf"] / m, 100 * g["ic95_sup"] / m
        mdt = 100 * g["mdt"] / m
        yy = y + (-0.17 if k == 0 else 0.17)
        ax.barh(yy, 2 * mdt, left=-mdt, height=0.3, color=PROD_COL[prod], alpha=0.18, lw=0)
        ax.errorbar(s, yy, xerr=[s - lo, hi - s], fmt="o", color=PROD_COL[prod], ms=3, lw=0.8)
        sig = g["p"] < 0.05
        ax.plot(s[sig], yy[sig.to_numpy()], "o", ms=6, mfc="none", mec="k", mew=0.6)
    ax.axvline(0, color="k", lw=0.6)
    ax.set_yticks(y, idxs)
    ax.invert_yaxis()
    ax.set_xlabel("cambio por década (% de la media 2001-2024), serie nacional")
    lim = 120
    ax.set_xlim(-lim, lim)
    ax.grid(axis="x", alpha=0.3, lw=0.3)
    handles = [Line2D([], [], marker="o", ls="", color=PROD_COL[p], ms=4, label=f"{p}: Theil-Sen ± IC 95 %") for p in PROD_COL] + [
        Patch(color="0.5", alpha=0.3, label="± tendencia mínima detectable (80 % potencia)"),
        Line2D([], [], marker="o", ls="", mfc="none", mec="k", ms=6, label="p < 0.05 (Hamed-Rao)")]
    lax.legend(handles=handles, loc="upper center", ncol=2, fontsize=6.3, frameon=False)
    ax.set_title("¿Qué cambio podríamos ver con 24 años? Tendencia nacional frente a la tendencia mínima detectable",
                 loc="left", fontsize=9)
    lax.text(0.0, 0.42, "Una tendencia dentro de la banda sombreada no se puede distinguir del ruido interanual con 24 años "
             "(α = 0.05, potencia 80 %, corrección por autocorrelación). 'Sin señal' significa 'no detectable a esta "
             "longitud', no 'sin cambio'. Valores recortados a ±120 %. " + SRC, fontsize=6.2, ha="left", va="top", wrap=True)
    save(fig, "fig5_tendencia_minima_detectable")


def fig_spi_example(state: dict):
    """Serie nacional de SPI-3 (media de celdas) de los dos productos, con los meses ≤ −1 sombreados."""
    S = state["S"]
    fig, ax = plt.subplots(figsize=(7.2, 2.2), constrained_layout=True)
    w = S["W"][-1]
    for prod, (months, spi) in state["spi3"].items():
        sp = spi[:, S["inc"]]
        ww = w[S["inc"]]
        ok = np.isfinite(sp)
        v = np.where(ok, sp, 0) @ ww / np.maximum(ok @ ww, 1e-9)
        v[ok.sum(1) == 0] = np.nan
        t = months.astype("datetime64[M]").astype("datetime64[D]")
        ax.plot(t, v, color=PROD_COL[prod], lw=0.8, label=f"{prod} (media de celdas)")
    ax.axhline(-1, color="k", lw=0.6, ls=":")
    ax.axhline(0, color="k", lw=0.4)
    ax.set_ylabel("SPI-3")
    ax.set_xlim(np.datetime64("2001-01-01"), np.datetime64("2025-01-01"))
    ax.legend(loc="upper left", ncol=2, frameon=False)
    ax.grid(alpha=0.25, lw=0.3)
    ax.set_title("SPI-3 nacional (media ponderada por área del SPI de cada celda); línea punteada: umbral de sequía −1",
                 loc="left", fontsize=8.5)
    fig.text(0.01, -0.06, "SPI ajustado por celda y mes calendario sobre 2001-2024 (gamma, estimador de Thom). " + SRC,
             fontsize=6.2, ha="left", va="top")
    save(fig, "fig6_spi3_nacional")


def all_figures(state: dict) -> None:
    out = state["out"]
    tc, tr, sr = out["celdas"], out["regiones"], out["series_regiones"]
    fig_trend_maps(tc)
    if "CHIRPS" in state["series"]:
        fig_classes(tc)
    for idx, per in [("CDD", "anual"), ("Rx5day", "anual"), ("SDII", "anual"), ("RACHAS15", "anual"), ("R1mm", "anual"),
                     ("SPI3_MESES", "anual")]:
        fig_province_series(sr, tr, idx, per)
    fig_calibration(state["cal"])
    fig_mdt(tr)
    fig_spi_example(state)
    (FIG / "LEYENDAS.json").write_text(json.dumps({"fuente": SRC}, ensure_ascii=False, indent=1), encoding="utf-8")
    print("[figuras] listo", flush=True)
