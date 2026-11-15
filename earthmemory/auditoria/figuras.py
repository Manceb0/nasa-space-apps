"""Figuras de la auditoría (estilo de artículo, Okabe-Ito / viridis-cividis, PNG 300 dpi + PDF + JSON de procedencia)."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib import colors as mcolors  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

from phantom.figures import GREY, MM, OI, WIDTH_MM, save, style  # noqa: E402

from . import analisis, datos, procedencia  # noqa: E402


def panel_letter(ax, letter: str, text: str = "") -> None:
    ax.annotate(letter, (0, 1.03), xycoords="axes fraction", fontsize=8, fontweight="bold", va="bottom", ha="left")
    if text:
        t = ax.annotate(text, (0, 1.03), xycoords="axes fraction", xytext=(10 if letter else 0, 0),
                        textcoords="offset points", fontsize=7, va="bottom", ha="left")
        t.set_in_layout(False)  # que un título largo no encoja el panel en constrained layout

LAT0 = 18.8
EXT = (-72.1, -68.3, 17.45, 20.0)
PCOL = {"IMERG": OI["blue"], "CHIRPS": OI["orange"], "GLDAS_forzamiento": OI["green"], "MERRA2": OI["purple"],
        "SMAP_L4": OI["sky"], "SMAP_L3": OI["yellow"], "TerraClimate": OI["vermillion"], "GRACE": "#555555",
        "MOD13A3": "#8C6D31", "MOD17": "#B07AA1", "GEOGLOWS": "#4E79A7", "Estaciones": OI["black"]}
CORTO = {"IMERG": "IMERG", "CHIRPS": "CHIRPS", "GLDAS_forzamiento": "GLDAS (forz.)", "MERRA2": "MERRA-2",
         "SMAP_L4": "SMAP L4", "SMAP_L3": "SMAP L3", "TerraClimate": "TerraClimate", "GRACE": "GRACE-FO",
         "MOD13A3": "MOD13A3", "MOD17": "MOD17", "GEOGLOWS": "GEOGLOWS", "Estaciones": "Estaciones"}


def base_map(ax, g: datos.G05, labels=True):
    for u in g.units:
        for ext, _ in u.polygons:
            ax.plot(ext[:, 0], ext[:, 1], color="#4D4D4D", lw=0.3, zorder=4)
    for polys in g.others.values():
        for ext, _ in polys:
            ax.plot(ext[:, 0], ext[:, 1], color="#AAAAAA", lw=0.3, zorder=4)
    ax.set_xlim(EXT[0], EXT[1])
    ax.set_ylim(EXT[2], EXT[3])
    ax.set_aspect(1 / np.cos(np.radians(LAT0)))
    ax.tick_params(labelsize=5.5, length=1.5, pad=1)
    if labels:
        ax.set_xticks([-72, -71, -70, -69])
        ax.set_xticklabels(["72°O", "71°O", "70°O", "69°O"])
        ax.set_yticks([18, 19])
        ax.set_yticklabels(["18°N", "19°N"])
    else:
        ax.set_xticks([])
        ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_visible(True)
        sp.set_linewidth(0.4)


def prov_map(ax, g: datos.G05, values: dict, cmap, norm):
    """Colorea cada provincia (polígonos ADM1) con su valor."""
    from matplotlib.patches import Polygon
    cm = plt.get_cmap(cmap)
    for u in g.units:
        v = values.get(u.name, np.nan)
        col = cm(norm(v)) if np.isfinite(v) else "#EEEEEE"
        for ext, _ in u.polygons:
            ax.add_patch(Polygon(ext, closed=True, facecolor=col, edgecolor="none", zorder=2))
    base_map(ax, g)
    return plt.cm.ScalarMappable(norm=norm, cmap=cm)


def cbar(fig, m, ax, label):
    cb = fig.colorbar(m, ax=ax, orientation="horizontal", fraction=0.05, pad=0.1, aspect=30)
    cb.set_label(label, fontsize=6)
    cb.ax.tick_params(labelsize=5.5, length=1.5)
    cb.outline.set_linewidth(0.4)
    return cb


# ------------------------------------------------------------------ 1. procedencia

def fig_procedencia(S, stem):
    ins = procedencia.INSUMOS
    prods = [p["id"] for p in procedencia.PRODUCTOS]
    inputs = list(ins.keys())
    with style():
        fig = plt.figure(figsize=(WIDTH_MM * MM, 120 * MM), layout="constrained")
        gs = fig.add_gridspec(1, 2, width_ratios=[1.35, 1])
        ax = fig.add_subplot(gs[0])
        ya = {k: 1 - i / (len(inputs) - 1) for i, k in enumerate(inputs)}
        yp = {k: 1 - i / (len(prods) - 1) for i, k in enumerate(prods)}
        for k, d in ins.items():
            for p, st in d.items():
                ax.plot([0.0, 1.0], [ya[k], yp[p]], color=PCOL.get(p, GREY), lw=0.9 if st == "V" else 0.7,
                        ls="-" if st == "V" else (0, (2, 1.5)), alpha=0.85, zorder=1)
        for k, y in ya.items():
            ax.text(-0.04, y, k, ha="right", va="center", fontsize=5.8)
            ax.plot(0, y, "o", ms=3, color="#333333", zorder=2)
        clase_ab = {"observación in situ": "in situ", "recuperación satelital": "satélite",
                    "recuperación satelital ajustada con pluviómetros": "satélite + pluviómetros",
                    "modelo con asimilación": "modelo con asimilación", "modelo forzado": "modelo forzado",
                    "simulación hidrológica": "simulación"}
        cl = {p["id"]: clase_ab[p["clase"]] for p in procedencia.PRODUCTOS}
        for p, y in yp.items():
            ax.plot(1, y, "s", ms=4, color=PCOL.get(p, GREY), zorder=2)
            ax.text(1.03, y, f"{CORTO[p]}  ·  {cl[p]}", ha="left", va="center", fontsize=5.8)
        ax.set_xlim(-0.8, 1.85)
        ax.set_ylim(-0.05, 1.1)
        ax.axis("off")
        ax.text(0, 1.065, "insumo", ha="center", fontsize=6, color="#333333", style="italic")
        ax.text(1.03, 1.065, "producto · clase", ha="left", fontsize=6, color="#333333", style="italic")
        ax.legend([Line2D([], [], color="#333", lw=0.9), Line2D([], [], color="#333", lw=0.7, ls=(0, (2, 1.5)))],
                  ["verificado en la documentación", "inferido"], loc="lower left", fontsize=5.5, frameon=False,
                  bbox_to_anchor=(-0.05, -0.08))
        panel_letter(ax, "a", "Qué insumos comparte cada producto")
        # b: matriz producto × producto: nº de familias de insumo compartidas
        ax2 = fig.add_subplot(gs[1])
        P = ["IMERG", "CHIRPS", "GLDAS_forzamiento", "MERRA2", "SMAP_L4", "SMAP_L3", "TerraClimate", "Estaciones"]
        M = np.zeros((len(P), len(P)))
        for d in ins.values():
            for a in P:
                for b in P:
                    if a != b and a in d and b in d:
                        M[P.index(a), P.index(b)] += 1
        np.fill_diagonal(M, np.nan)
        m = ax2.imshow(M, cmap="cividis", vmin=0, vmax=np.nanmax(M))
        for i in range(len(P)):
            for j in range(len(P)):
                if i != j:
                    ax2.text(j, i, f"{int(M[i, j])}", ha="center", va="center", fontsize=5.5,
                             color="white" if M[i, j] < np.nanmax(M) * 0.6 else "black")
        ax2.set_xticks(range(len(P)), [CORTO[p] for p in P], rotation=55, ha="right", fontsize=5.8)
        ax2.set_yticks(range(len(P)), [CORTO[p] for p in P], fontsize=5.8)
        for sp in ax2.spines.values():
            sp.set_visible(False)
        cb = fig.colorbar(m, ax=ax2, orientation="horizontal", fraction=0.05, pad=0.02, aspect=25)
        cb.set_label("familias de insumo compartidas (verificadas + inferidas)", fontsize=5.8)
        cb.ax.tick_params(labelsize=5.5)
        panel_letter(ax2, "b", "Quién puede compartir errores")
    return save(fig, stem, {"fuente": "earthmemory/auditoria/procedencia.py (URLs en results/auditoria/procedencia.json)"})


# ------------------------------------------------------------------ 2. estaciones

def fig_estaciones(S, stem, g):
    st = S["stv"]
    meta, dd, mm = st["meta"], st["diario"], st["mensual"]
    ok = meta[meta["dias_validos"] > 365]
    with style():
        fig = plt.figure(figsize=(WIDTH_MM * MM, 125 * MM), layout="constrained")
        gs = fig.add_gridspec(2, 3)
        ax = fig.add_subplot(gs[0, :2])
        d = datos.imerg_daily()
        clim = np.nanmean(d["P"], 0) * 365.25
        lo_e = np.r_[d["lon"] - 0.05, d["lon"][-1] + 0.05]
        la_e = np.r_[d["lat"] - 0.05, d["lat"][-1] + 0.05]
        m = ax.pcolormesh(lo_e, la_e, clim, cmap="YlGnBu", shading="flat", rasterized=True, zorder=1,
                          norm=mcolors.Normalize(500, 2500))
        base_map(ax, g)
        for _, s in ok.iterrows():
            inch = s.get("fraccion_meses_en_chirps", 0) or 0
            mk = "o" if s["red"] == "GHCN-Daily" else "^"
            ax.plot(s["lon"], s["lat"], mk, ms=4.5, mfc=OI["vermillion"] if inch > 0.5 else "white",
                    mec="black", mew=0.6, zorder=6)
            off = {"Santo Domingo": (-4, 5), "Las Américas": (-3, -11), "La Romana": (3, 4), "Punta Cana": (-30, 5),
                   "Sabana de la Mar": (3, 3), "Barahona": (3, 3)}.get(s["nombre"], (3, 3))
            ax.annotate(f"{s['nombre']}", (s["lon"], s["lat"]), xytext=off, textcoords="offset points", fontsize=5,
                        ha="right" if off[0] < -5 else "left", zorder=7,
                        bbox=dict(boxstyle="round,pad=0.1", fc="white", ec="none", alpha=0.7))
        ax.legend([Line2D([], [], marker="o", ls="", mfc="white", mec="k", ms=4),
                   Line2D([], [], marker="^", ls="", mfc="white", mec="k", ms=4),
                   Line2D([], [], marker="s", ls="", mfc=OI["vermillion"], mec="k", ms=4)],
                  ["GHCN-Daily", "GSOD (ISD)", "relleno: en la mezcla de CHIRPS > 50 % de los meses"],
                  fontsize=5.2, loc="lower left", frameon=True, framealpha=0.8, edgecolor="none", ncol=1)
        cb = fig.colorbar(m, ax=ax, orientation="vertical", fraction=0.03, pad=0.01)
        cb.set_label("lluvia media anual IMERG\n2001-2024 (mm)", fontsize=5.5)
        cb.ax.tick_params(labelsize=5)
        panel_letter(ax, "a", f"{len(ok)} estaciones sinópticas con datos 2001-2024 (todas en el GTS)")
        # b: KGE diaria (mejor desfase) por producto
        ax = fig.add_subplot(gs[0, 2])
        best = dd[dd["es_mejor_desfase"]]
        prods = [p for p in ("IMERG", "CHIRPS", "MERRA2") if p in set(best["producto"])]
        names = ok["nombre"].tolist()
        for k, p in enumerate(prods):
            b = best[best["producto"] == p].set_index("nombre")
            y = np.arange(len(names)) + (k - 1) * 0.22
            ax.plot(b.reindex(names)["r"], y, "o", ms=3, color=PCOL[p], label=CORTO[p])
        ax.set_yticks(range(len(names)), names, fontsize=5.5)
        ax.set_xlabel("r diaria (mejor desfase −1/0/+1 d)")
        ax.set_xlim(0, 1)
        ax.axvline(0.5, color=GREY, lw=0.4, ls=":")
        ax.legend(fontsize=5.5, frameon=False, loc="lower right")
        panel_letter(ax, "b", "Acuerdo diario")
        # c: POD / FAR para >= 50 mm (todas las estaciones juntas)
        ax = fig.add_subplot(gs[1, 0])
        cats = [("pod", 50), ("far", 50), ("csi", 50), ("pod", 100), ("far", 100), ("csi", 100)]
        for k, p in enumerate(prods):
            b = best[best["producto"] == p]
            v = [np.nanmedian(b[f"{m}_{t}"]) for m, t in cats]
            ax.plot(np.arange(len(cats)) + (k - 1) * 0.18, v, "o", ms=3.2, color=PCOL[p], label=CORTO[p])
        ax.set_xticks(range(len(cats)), [f"{m.upper()}\n≥{t}" for m, t in cats], fontsize=5.5)
        ax.axvline(2.5, color=GREY, lw=0.4)
        ax.set_ylim(-0.03, 1.03)
        ax.set_ylabel("mediana entre estaciones")
        ax.legend(fontsize=5, frameon=False, loc="center left")
        panel_letter(ax, "c", "Días ≥ 50 y ≥ 100 mm")
        # d: mensual r por producto, CHIRPS con y sin estación ingerida
        ax = fig.add_subplot(gs[1, 1])
        allm = mm[mm["subconjunto"] == "todos los meses"]
        pr = [p for p in analisis.PRODUCTOS_M if p in set(allm["producto"])]
        for k, p in enumerate(pr):
            v = allm[allm["producto"] == p]["kge"].dropna()
            ax.plot(np.full(v.size, k) + np.linspace(-0.12, 0.12, v.size), v, "o", ms=2.8, color=PCOL[p], alpha=0.9)
            ax.plot([k - 0.2, k + 0.2], [v.median()] * 2, color="black", lw=0.8)
        ax.set_xticks(range(len(pr)), [CORTO[p] for p in pr], rotation=20)
        ax.set_ylabel("KGE mensual por estación")
        ax.axhline(0, color=GREY, lw=0.4)
        ax.axhline(-0.41, color=GREY, lw=0.4, ls=":")
        ax.text(len(pr) - 0.5, -0.39, "KGE = −0.41 (media clim.)", fontsize=4.8, ha="right", color="#555")
        panel_letter(ax, "d", "Escala mensual")
        ax = fig.add_subplot(gs[1, 2])
        for prod, mk in (("CHIRPS", "o"), ("IMERG", "s")):
            cm = mm[(mm["producto"] == prod)]
            for lab, col, off in (("meses con la estación en CHIRPS", OI["vermillion"], -0.15),
                                  ("meses sin la estación en CHIRPS", OI["sky"], 0.15)):
                c = cm[cm["subconjunto"] == lab].set_index("nombre").reindex(names)
                ax.plot(c["r"], np.arange(len(names)) + off + (0.05 if prod == "IMERG" else -0.05), mk, ms=3,
                        mfc=col if prod == "CHIRPS" else "white", mec=col, mew=0.8)
        ax.set_yticks(range(len(names)), names, fontsize=5.5)
        ax.set_xlabel("r mensual producto vs estación")
        ax.set_xlim(0, 1)
        ax.legend([Line2D([], [], marker="o", ls="", color=OI["vermillion"], ms=3),
                   Line2D([], [], marker="o", ls="", color=OI["sky"], ms=3),
                   Line2D([], [], marker="s", ls="", mfc="white", mec="#555", ms=3)],
                  ["meses con la estación en CHIRPS", "meses sin ella", "cuadrado hueco: IMERG (control)"],
                  fontsize=4.8, frameon=False, loc="upper left")
        panel_letter(ax, "e", "Circularidad")
    return save(fig, stem, {"fuentes": "GHCN-Daily (doi:10.7289/V5D21VHZ), GSOD, IMERG V07, CHIRPS v2.0, POWER/MERRA-2"})


# ------------------------------------------------------------------ 3. re-auditoría 50/96

def fig_reauditoria(S, stem, g):
    re = S["re"]
    rs = re["resumen"]
    with style():
        fig = plt.figure(figsize=(WIDTH_MM * MM, 118 * MM), layout="constrained")
        gs = fig.add_gridspec(2, 3)
        ax = fig.add_subplot(gs[0, 0])
        labs = ["a) escala\n0.5°", "b) tiempo\n±1 d, ±1 mes", "c) umbral", "sin\nexplicar"]
        att = rs["atribucion_secuencial"]
        seq = [att.get("a_escala", 0), att.get("b_tiempo", 0), att.get("c_variable_umbral", 0), att.get("sin_explicar", 0)]
        nonex = [rs["explica_a_escala"], rs["explica_b_tiempo"], rs["explica_c_variable_umbral"], np.nan]
        x = np.arange(4)
        ax.bar(x, seq, 0.6, color=[OI["sky"], OI["orange"], OI["green"], OI["vermillion"]], edgecolor="black", lw=0.4)
        ax.plot(x[:3], nonex[:3], "_", ms=12, mew=1.2, color="black", label="explica (sin orden)")
        for xi, v in zip(x, seq):
            ax.text(xi, v + 0.6, str(v), ha="center", fontsize=6)
        ax.set_xticks(x, labs, fontsize=5.2)
        ax.set_ylabel("episodios (de 50)")
        ax.legend(fontsize=5, frameon=False, loc="upper left")
        panel_letter(ax, "a", "Por qué no coinciden")
        # b mapa por celda 0.25
        ax = fig.add_subplot(gs[0, 1:])
        ci = re["celdas"]
        A = np.full((len(np.arange(17.375, 20.01, 0.25)), len(np.arange(-72.125, -68.2, 0.25))), np.nan)
        las = np.round(np.arange(17.375, 20.01, 0.25), 3)
        los = np.round(np.arange(-72.125, -68.2, 0.25), 3)
        for c, r in ci.iterrows():
            A[np.argmin(np.abs(las - r["lat"])), np.argmin(np.abs(los - r["lon"]))] = r["desacuerdo_spi3_imerg_vs_modelo"]
        m = ax.pcolormesh(np.r_[los - 0.125, los[-1] + 0.125], np.r_[las - 0.125, las[-1] + 0.125], A, cmap="cividis",
                          shading="flat", rasterized=True, zorder=1)
        base_map(ax, g)
        un = re["tabla"][re["tabla"]["causa_atribuida"] == "sin_explicar"].groupby("celda").size()
        mm_ = re["tabla"][re["tabla"]["posible_diferencia"]].groupby("celda").size()
        for c, n in mm_.items():
            la, lo = map(float, c.split("_"))
            ax.plot(lo, la, "o", ms=2 + 1.5 * n, mfc="none", mec="white", mew=0.7, zorder=6)
        for c, n in un.items():
            la, lo = map(float, c.split("_"))
            ax.plot(lo, la, "x", ms=2 + 1.5 * n, color=OI["vermillion"], mew=0.9, zorder=7)
        cb = fig.colorbar(m, ax=ax, orientation="vertical", fraction=0.03, pad=0.01)
        cb.set_label("1 − r(SPI-3 IMERG, SPI-3 lluvia\nde forzamiento GLDAS), 2001-2024", fontsize=5.5)
        cb.ax.tick_params(labelsize=5)
        ax.legend([Line2D([], [], marker="o", ls="", mfc="none", mec="#444", ms=4),
                   Line2D([], [], marker="x", ls="", color=OI["vermillion"], ms=4)],
                  ["'posible diferencia' (tamaño = nº)", "sin explicar tras a-c"], fontsize=5.2, frameon=False,
                  loc="upper left", bbox_to_anchor=(0.0, -0.08), ncol=2)
        panel_letter(ax, "b", "Dónde discrepan IMERG y la lluvia que vio GLDAS")
        # c por año
        ax = fig.add_subplot(gs[1, 0])
        py = pd.DataFrame(re["persistencia"]["por_anio"])
        ax.bar(py["anio_fin"], py["n_A"], color="#CCCCCC", edgecolor="black", lw=0.3, label="96 contradicciones A")
        ax.bar(py["anio_fin"], py["n_posible_diferencia"], color=OI["vermillion"], edgecolor="black", lw=0.3,
               label="50 'posible diferencia'")
        ax.set_xlabel("año de fin del episodio")
        ax.set_ylabel("episodios")
        ax.legend(fontsize=5, frameon=False)
        p = re["persistencia"]
        ax.text(0.02, 0.62, f"concentración anual: p = {p['p_perm_max_fraccion_anual']:.2f}\n"
                            f"celdas repetidas: p = {p['p_perm_celdas_repetidas']:.2f}\n(permutación)",
                transform=ax.transAxes, fontsize=5)
        panel_letter(ax, "c", "Persistencia")
        # d relieve
        ax = fig.add_subplot(gs[1, 1])
        rl = re["relieve"]
        ax.scatter(ci["elevacion_m"], ci["desacuerdo_spi3_imerg_vs_modelo"], s=8, color=OI["blue"], edgecolor="none")
        r0 = rl[(rl["resultado"] == "desacuerdo_spi3_imerg_vs_modelo") & (rl["covariable"] == "elevacion_m")].iloc[0]
        ax.set_xlabel("elevación media de la celda (m, Copernicus DEM)")
        ax.set_ylabel("1 − r SPI-3")
        ax.text(0.02, 0.9, f"ρ = {r0['rho_spearman']:.2f}; p toroidal = {r0['p_toroidal']:.3f}", transform=ax.transAxes, fontsize=5.5)
        panel_letter(ax, "d", "Relieve")
        ax = fig.add_subplot(gs[1, 2])
        ax.scatter(ci["dist_costa_km"], ci["desacuerdo_spi3_imerg_vs_modelo"], s=8, color=OI["green"], edgecolor="none")
        r1 = rl[(rl["resultado"] == "desacuerdo_spi3_imerg_vs_modelo") & (rl["covariable"] == "dist_costa_km")].iloc[0]
        ax.set_xlabel("distancia a la costa (km)")
        ax.text(0.02, 0.9, f"ρ = {r1['rho_spearman']:.2f}; p toroidal = {r1['p_toroidal']:.3f}", transform=ax.transAxes, fontsize=5.5)
        panel_letter(ax, "e", "Costa")
    return save(fig, stem, {"fuente": "results/auditoria/reauditoria_*.csv; GLDAS-2.1, IMERG V07, Copernicus DEM GLO-90"})


# ------------------------------------------------------------------ 4. cambio de decisión

def fig_cambio_decision(S, stem, g):
    dr = S["dr"]
    pv = dr["provincia"]
    with style():
        fig = plt.figure(figsize=(WIDTH_MM * MM, 165 * MM), layout="constrained")
        gs = fig.add_gridspec(3, 2, width_ratios=[1.3, 1], height_ratios=[1.15, 1, 0.75])
        ax = fig.add_subplot(gs[0, 0])
        p1 = pv[pv["umbral_spi3"] == -1.0].set_index("provincia")
        norm = mcolors.Normalize(0.7, 1.0)
        m = prov_map(ax, g, p1["tasa_condicional"].to_dict(), "viridis", norm)
        cb = fig.colorbar(m, ax=ax, orientation="vertical", fraction=0.03, pad=0.01)
        cb.set_label("tasa condicional\n(SPI-3 ≤ −1)", fontsize=5.5)
        cb.ax.tick_params(labelsize=5)
        panel_letter(ax, "a", "¿Cambia 'hay sequía' según el producto? (4 productos)")
        ax = fig.add_subplot(gs[0:2, 1])
        s = p1.sort_values("tasa_condicional")
        y = np.arange(len(s))
        ax.errorbar(s["tasa_condicional"], y, xerr=[s["tasa_condicional"] - s["ic95_condicional_bajo"],
                                                     s["ic95_condicional_alto"] - s["tasa_condicional"]],
                    fmt="o", ms=2.5, color=OI["blue"], ecolor="#7A9CC6", elinewidth=0.6, capsize=0)
        p15 = pv[pv["umbral_spi3"] == -1.5].set_index("provincia").reindex(s.index)
        ax.plot(p15["tasa_condicional"], y, "d", ms=2.5, color=OI["vermillion"], label="SPI-3 ≤ −1.5")
        ax.plot(s["tasa_contradiccion_clara"], y, "|", ms=4, mew=1.0, color="black")
        ax.set_yticks(y, s.index, fontsize=5.2)
        ax.set_xlabel("tasa condicional (IC 95 %, bloques de año)")
        ax.set_xlim(0, 1.02)
        ax.legend([Line2D([], [], marker="o", ls="", color=OI["blue"], ms=3), Line2D([], [], marker="d", ls="", color=OI["vermillion"], ms=3),
                   Line2D([], [], marker="|", ls="", color="black", ms=4)],
                  ["SPI-3 ≤ −1.0", "SPI-3 ≤ −1.5", "contradicción clara (otro producto SPI-3 ≥ 0)"], fontsize=5,
                  frameon=False, loc="upper left", bbox_to_anchor=(0, -0.07))
        panel_letter(ax, "b", "Provincias")
        ax = fig.add_subplot(gs[2, :])
        n = dr["provincias_en_sequia"]
        A = np.vstack([n[p].to_numpy() / 32 for p in analisis.PRODUCTOS_M])
        import matplotlib.dates as mdates
        x0, x1 = mdates.date2num(n.index[0]), mdates.date2num(n.index[-1] + pd.offsets.MonthEnd(1))
        mm2 = ax.imshow(A, aspect="auto", cmap="YlOrBr", vmin=0, vmax=1, extent=(x0, x1, 3.5, -0.5), interpolation="nearest")
        ax.xaxis_date()
        ax.set_yticks(range(4), [CORTO[p] for p in analisis.PRODUCTOS_M], fontsize=5.8)
        cb = fig.colorbar(mm2, ax=ax, orientation="vertical", fraction=0.02, pad=0.01)
        cb.set_label("fracción de provincias\ncon SPI-3 ≤ −1", fontsize=5.5)
        cb.ax.tick_params(labelsize=5)
        panel_letter(ax, "c", "La misma sequía, cuatro relatos (2001-2024)")
        ax = fig.add_subplot(gs[1, 0])
        pr = dr["pares"]
        pr = pr[pr["umbral_spi3"] == -1.0]
        P = analisis.PRODUCTOS_M
        M = np.full((4, 4), np.nan)
        for _, r in pr.iterrows():
            i, j = P.index(r["producto_a"]), P.index(r["producto_b"])
            M[i, j] = M[j, i] = r["tasa_condicional"]
        mm_ = ax.imshow(M, cmap="viridis", vmin=0, vmax=1)
        for i in range(4):
            for j in range(4):
                if i != j:
                    ax.text(j, i, f"{M[i, j]:.2f}", ha="center", va="center", fontsize=6,
                            color="white" if M[i, j] < 0.6 else "black")
        ax.set_xticks(range(4), [CORTO[p] for p in P], rotation=30, ha="right")
        ax.set_yticks(range(4), [CORTO[p] for p in P])
        for sp in ax.spines.values():
            sp.set_visible(False)
        cb = fig.colorbar(mm_, ax=ax, fraction=0.05, pad=0.02)
        cb.set_label("1 − Jaccard (meses-provincia en sequía)", fontsize=5.5)
        cb.ax.tick_params(labelsize=5)
        panel_letter(ax, "d", "Por pares")
    return save(fig, stem, {"fuente": "results/auditoria/cambio_decision_sequia_*.csv"})


def fig_inundacion(S, stem, g):
    fl = S["fl"]
    if fl is None:
        return []
    with style():
        fig = plt.figure(figsize=(WIDTH_MM * MM, 80 * MM), layout="constrained")
        gs = fig.add_gridspec(1, 2, width_ratios=[1.25, 1])
        ax = fig.add_subplot(gs[0])
        pp = fl["provincia"]
        sub = pp[(pp["escala"] == "maximo_celda") & (pp["tolerancia_dias"] == 1)].set_index("provincia")
        m = prov_map(ax, g, sub["tasa_cambio_decision"].to_dict(), "viridis", mcolors.Normalize(0, 1))
        cbar(fig, m, ax, "fracción de disparos (> 100 mm en 48 h) no confirmados por el otro producto")
        panel_letter(ax, "a", f"IMERG vs CHIRPS diario, máximo de celda, ±1 día ({fl['anios'][0]}-{fl['anios'][-1]})")
        ax = fig.add_subplot(gs[1])
        r = fl["resumen"]
        labs, vals, los, his, cols = [], [], [], [], []
        for _, x in r.iterrows():
            labs.append(f"{'media prov.' if x['escala'] == 'media_provincia' else 'máx. celda'} · IMERG {x['desplazamiento_imerg_dias']:+d} d · ±{x['tolerancia_dias']} d")
            vals.append(x["tasa_cambio_decision"])
            los.append(x["ic95"][0])
            his.append(x["ic95"][1])
            cols.append(OI["blue"] if x["escala"] == "maximo_celda" else OI["orange"])
        y = np.arange(len(labs))
        v = np.array(vals, float)
        ax.errorbar(v, y, xerr=[v - np.array(los, float), np.array(his, float) - v], fmt="none", ecolor="#999", elinewidth=0.6)
        ax.scatter(v, y, c=cols, s=10, zorder=3)
        ax.set_yticks(y, labs, fontsize=4.8)
        ax.set_xlim(0, 1)
        ax.set_xlabel("tasa de cambio de decisión (IC 95 %)")
        panel_letter(ax, "b", "Escala y desfase")
    return save(fig, stem, {"fuente": "results/auditoria/cambio_decision_inundacion_48h*.csv; CHIRPS v2.0 diario (IRI), IMERG V07"})


# ------------------------------------------------------------------ 5. Santo Domingo

def fig_santo_domingo(S, stem, g):
    sd = S["sd"]
    h = sd["horaria"]
    d = sd["descomposicion"]
    with style():
        fig = plt.figure(figsize=(WIDTH_MM * MM, 78 * MM), layout="constrained")
        gs = fig.add_gridspec(1, 2, width_ratios=[1.4, 1])
        ax = fig.add_subplot(gs[0])
        t = pd.to_datetime(h["inicio_utc"])
        ax.bar(t, h["vecinas_max_mm"] * 2, width=1 / 48, color="#BBBBBB", label="máx. de las 9 celdas (mm/h)", align="edge")
        ax.bar(t, h["celda_mm"] * 2, width=1 / 48, color=OI["blue"], label="celda de Arroyo Hondo (mm/h)", align="edge")
        ax.axvspan(pd.Timestamp("2023-11-18T00:00"), pd.Timestamp("2023-11-19T00:00"), color=OI["orange"], alpha=0.12, lw=0)
        ax.text(pd.Timestamp("2023-11-18T01:00"), ax.get_ylim()[1] * 0.70, "día UTC 18", fontsize=5.5, color="#8A5A00")
        ax.axvline(pd.Timestamp("2023-11-18T21:00"), color=OI["vermillion"], lw=0.6, ls="--")
        ax.text(pd.Timestamp("2023-11-18T21:30"), ax.get_ylim()[1] * 0.75, "~17 h local:\ncae el muro\n(prensa)", fontsize=5)
        ax.set_ylabel("IMERG media hora (mm/h)")
        ax.set_xlabel("hora UTC (local = UTC − 4)")
        import matplotlib.dates as mdates
        ax.xaxis.set_major_locator(mdates.HourLocator(byhour=[0, 12]))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d nov\n%H UTC"))
        ax.tick_params(axis="x", labelsize=5.5)
        ax.set_xlim(pd.Timestamp("2023-11-17T00:00"), pd.Timestamp("2023-11-20T00:00"))
        ax.legend(fontsize=5.2, frameon=False, loc="upper left")
        panel_letter(ax, "a", "IMERG V07 Final, media hora, 17-19 nov 2023")
        ax = fig.add_subplot(gs[1])
        steps = [("estación\n(NHC)", 431, None), ("IMERG\ncelda,\ndía UTC", d["imerg_celda_dia_utc_mm"], None),
                 ("+ mejor\nventana\n24 h", d["imerg_celda_mejor_ventana_mm"], None),
                 ("+ mejor\ncelda\nvecina", d["imerg_mejor_vecina_mejor_ventana_mm"], None),
                 ("media 11\npluvióm.\n(prensa)", d["media_11_pluviometros_prensa_mm"], None),
                 ("CHIRPS\nmejor celda\n18+19 nov", d["chirps_mejor_vecina_18_19_mm"], None)]
        x = np.arange(len(steps))
        cols = [OI["black"], OI["blue"], OI["blue"], OI["blue"], "#777777", OI["orange"]]
        ax.bar(x, [s[1] for s in steps], color=cols, edgecolor="black", lw=0.4, alpha=0.9)
        for xi, s in zip(x, steps):
            ax.text(xi, s[1] + 6, f"{s[1]:.0f}", ha="center", fontsize=5.8)
        ax.set_xticks(x, [s[0] for s in steps], fontsize=5)
        ax.set_ylabel("mm en 24 h (CHIRPS: 2 días)")
        ax.set_ylim(0, 480)
        panel_letter(ax, "b", "¿Ventana, escala o lo que queda?")
    return save(fig, stem, {"fuente": "results/auditoria/santo_domingo_*; NHC TCR AL222023; Listín Diario 21-nov-2023"})


# ------------------------------------------------------------------ 6. dónde medir

def fig_donde_medir(S, stem, g):
    wm = S["wm"]
    meta = S["stv"]["meta"]
    with style():
        fig = plt.figure(figsize=(WIDTH_MM * MM, 92 * MM), layout="constrained")
        gs = fig.add_gridspec(1, 2, width_ratios=[2.1, 1])
        ax = fig.add_subplot(gs[0])
        lat = np.round(np.arange(17.45, 20.06, 0.1), 3)
        lon = np.round(np.arange(-72.05, -68.24, 0.1), 3)
        A = np.full((lat.size, lon.size), np.nan)
        for _, r in wm.iterrows():
            A[np.argmin(np.abs(lat - r["lat"])), np.argmin(np.abs(lon - r["lon"]))] = r["indice_prioridad"]
        m = ax.pcolormesh(np.r_[lon - 0.05, lon[-1] + 0.05], np.r_[lat - 0.05, lat[-1] + 0.05], A, cmap="magma_r",
                          vmin=0.2, vmax=0.9, shading="flat", rasterized=True, zorder=1)
        base_map(ax, g)
        act = meta[(meta["red"] == "GHCN-Daily") & (meta["activa_2024"] == True)]  # noqa: E712
        oth = meta[(meta["dias_validos"] > 365) & ~meta["omm"].isin(act["omm"])]
        ax.plot(act["lon"], act["lat"], "o", ms=5, mfc="white", mec="black", zorder=6, label="GHCN-D activa 2024")
        ax.plot(oth["lon"], oth["lat"], "^", ms=4, mfc="white", mec="#555", zorder=6, label="GSOD (no en GHCN-D)")
        top = wm.head(10)
        ax.plot(top["lon"], top["lat"], "s", ms=6, mfc="none", mec=OI["sky"], mew=1.0, zorder=7, label="10 celdas de mayor índice")
        ax.legend(fontsize=5.3, frameon=False, loc="upper left", bbox_to_anchor=(0, -0.07), ncol=3)
        cb = fig.colorbar(m, ax=ax, orientation="vertical", fraction=0.03, pad=0.01)
        cb.set_label("índice de prioridad (0-1)", fontsize=5.5)
        cb.ax.tick_params(labelsize=5)
        panel_letter(ax, "a", "PRELIMINAR · dónde una medición nueva reduciría más la incertidumbre")
        ax2 = fig.add_subplot(gs[1])
        ax2.axis("off")
        cols = ["desacuerdo_1_menos_r_imerg_chirps", "persistencia_anios_con_cambio", "tasa_cambio_condicional_spi3",
                "dist_estacion_ghcn_activa_km"]
        txt = ["10 celdas de mayor índice", "(1−r · persist. · cambio · km)", ""]
        for k, r in top.reset_index(drop=True).iterrows():
            txt.append(f"{k + 1:>2}. {r['lat']:.2f}N {r['lon']:.2f}  {str(r['provincia'])[:16]}")
            txt.append(f"     {r[cols[0]]:.2f} · {r[cols[1]]:.2f} · {r[cols[2]]:.2f} · {r[cols[3]]:.0f} km")
        txt += ["", "Índice = media de rangos percentiles", "de los 4 componentes (pesos iguales).",
                "NO incluye acceso, exposición,", "población ni la red ONAMET/INDRHI.",
                "No prueba dónde deben ir estaciones."]
        ax2.text(0, 1, "\n".join(txt), va="top", ha="left", fontsize=5.2, family="DejaVu Sans Mono", transform=ax2.transAxes)
        panel_letter(ax2, "b", "Componentes")
    return save(fig, stem, {"fuente": "results/auditoria/donde_medir_prototipo.csv"})


def make_all(S, fdir: Path) -> dict:
    g = datos.G05()
    out = {}
    for name, fn, needs_g in (("fig01_procedencia", fig_procedencia, False), ("fig02_estaciones", fig_estaciones, True),
                              ("fig03_reauditoria_50_96", fig_reauditoria, True), ("fig04_cambio_decision_sequia", fig_cambio_decision, True),
                              ("fig05_cambio_decision_inundacion", fig_inundacion, True), ("fig06_santo_domingo", fig_santo_domingo, True),
                              ("fig07_donde_medir_prototipo", fig_donde_medir, True)):
        try:
            out[name] = fn(S, fdir / name, g) if needs_g else fn(S, fdir / name)
        except Exception as e:  # noqa: BLE001  (una figura rota no debe tumbar las demás; se informa)
            import traceback
            traceback.print_exc()
            out[name] = f"ERROR: {e}"
    return out
