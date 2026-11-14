"""Figuras nacionales (matplotlib, estilo de artículo). Reglas de phantom.figures: Okabe-Ito / mapas de color
perceptualmente uniformes y aptos para daltonismo, PDF + PNG + JSON de procedencia, tamaño físico fijo.

Mapas: cada celda se dibuja como el rectángulo que ES (pcolormesh con los bordes reales de la celda IMERG
0.1° o GLDAS 0.25°). No se interpola nada. Se dibujan el contorno del país y los límites de provincia
(geoBoundaries ADM1). Celdas no incluidas (menos de 25 % en el país, o mar en GLDAS) quedan en blanco.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib import colors as mcolors  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

from phantom.figures import GREY, MM, OI, WIDTH_MM, save, style  # noqa: E402

LAT0 = 18.8
SRC_IMERG = "GPM IMERG Final V07 (doi:10.5067/GPM/IMERG/3B-MONTH/07; diario doi:10.5067/GPM/IMERGDF/DAY/07)"
SRC_GLDAS = "GLDAS Noah 2.1 mensual 0.25° (doi:10.5067/SXAVCZFAQLNO)"
SRC_ADM = "geoBoundaries gbOpen DOM ADM1 (fuente Natural Earth, dominio público)"
CMAP_DIV = "RdBu"          # divergente; rojo = seco / negativo
CMAP_SEQ = "viridis"
HATCH_COLOR = "#B5B5B5"
LIGHT_FILL = "#DDDDDD"


# ------------------------------------------------------------------ utilidades de mapa

def panel_letter(ax, letter: str, text: str = "") -> None:
    ax.set_title(text, loc="left", fontsize=6.5, pad=3)
    ax.text(-0.02, 1.0, letter, transform=ax.transAxes, fontsize=8, fontweight="bold", va="bottom", ha="right")


def demo_pair(R) -> pd.Series | None:
    """Caso para la demo: primer contraste del ranking que (1) es significativo tras calibrar y BH,
    (2) sobrevive con la lluvia del modelo y (3) es de suelo; si no hay, se relaja en ese orden."""
    rk = R["ranked"]
    if not len(rk):
        return None
    sig = rk["significativo_q05_calibrado"].fillna(False).astype(bool)
    surv = rk["sobrevive_lluvia_modelo"].fillna(False).astype(bool) if "sobrevive_lluvia_modelo" in rk else sig
    soil = rk["respuesta"].isin(["SM_RAIZ", "SM_0_10"])
    for m in (sig & surv & soil, sig & surv, sig & soil, sig):
        if m.any():
            return rk[m].iloc[0]
    return rk.iloc[0]

def grid_array(g, values: pd.Series) -> np.ma.MaskedArray:
    ids = g.ids()
    a = np.full(len(ids), np.nan)
    pos = {c: k for k, c in enumerate(ids)}
    for c, v in values.items():
        if c in pos and v is not None and np.isfinite(v):
            a[pos[c]] = v
    return np.ma.masked_invalid(a.reshape(g.lat.size, g.lon.size))


def base_map(ax, R, labels: bool = True, lw_prov: float = 0.25) -> None:
    D = R["D"]
    for u in D["units"]:
        for ext, _ in u.polygons:
            ax.plot(ext[:, 0], ext[:, 1], color="#555555", lw=lw_prov, zorder=3)
    for a3, polys in D["others"].items():
        for ext, _ in polys:
            ax.plot(ext[:, 0], ext[:, 1], color="#999999", lw=0.3, zorder=3)
    g = D["g_im"]
    ax.set_xlim(g.lon_edges()[0], g.lon_edges()[-1])
    ax.set_ylim(g.lat_edges()[0], g.lat_edges()[-1])
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


def cell_map(ax, R, g, values: pd.Series, cmap, norm, nonsig: list | None = None, labels=True):
    A = grid_array(g, values)
    m = ax.pcolormesh(g.lon_edges(), g.lat_edges(), A, cmap=cmap, norm=norm, shading="flat", zorder=1,
                      rasterized=True)
    if nonsig:
        pos = {c: k for k, c in enumerate(g.ids())}
        for c in nonsig:
            if c not in pos:
                continue
            i, j = divmod(pos[c], g.lon.size)
            ax.add_patch(Rectangle((g.lon_edges()[j], g.lat_edges()[i]), g.res, g.res, facecolor=(1, 1, 1, 0.55),
                                   edgecolor=HATCH_COLOR, hatch="//////", lw=0, zorder=2))
    base_map(ax, R, labels)
    return m


def cbar(fig, m, ax, label, **kw):
    cb = fig.colorbar(m, ax=ax, orientation="horizontal", fraction=0.06, pad=0.08, aspect=30, **kw)
    cb.set_label(label, fontsize=6)
    cb.ax.tick_params(labelsize=5.5, length=1.5)
    cb.outline.set_linewidth(0.4)
    return cb


def sym_norm(v, q=98):
    v = np.asarray(pd.Series(v).dropna(), float)
    lim = float(np.nanpercentile(np.abs(v), q)) if v.size else 1.0
    return mcolors.TwoSlopeNorm(vmin=-lim, vcenter=0, vmax=lim) if lim > 0 else mcolors.Normalize(-1, 1)


def prov(R, base: dict) -> dict:
    return {"limites": SRC_ADM, "rejillas": "celdas nativas: IMERG 0.1°, GLDAS 0.25° (sin interpolar)",
            "periodo": f"{R['args']['anio0']}-{R['args']['anio1']}", "codigo": "earthmemory/figures.py", **base}


# ------------------------------------------------------------------ figuras

def fig_climatologias(R, stem):
    D = R["D"]
    gi, gg = D["g_im"], D["g_gl"]
    P = D["P_im"][R["inc_im"]]
    ann = P.groupby(P.index.year).sum().mean()
    inc = R["inc"]
    with style():
        fig, axs = plt.subplots(2, 2, figsize=(WIDTH_MM * MM, 125 * MM), layout="constrained")
        m = cell_map(axs[0, 0], R, gi, ann, CMAP_SEQ, mcolors.Normalize(float(ann.quantile(0.01)), float(ann.quantile(0.99))))
        cbar(fig, m, axs[0, 0], "mm/año")
        panel_letter(axs[0, 0], "a", "Lluvia media anual, IMERG 0.1°")
        sm = D["GL"]["SM_RAIZ"][inc].mean()
        m = cell_map(axs[0, 1], R, gg, sm, "YlGnBu", mcolors.Normalize(float(sm.min()), float(sm.max())))
        cbar(fig, m, axs[0, 1], "mm de agua en 0-100 cm")
        panel_letter(axs[0, 1], "b", "Humedad media de la zona de raíces, GLDAS 0.25°")
        t = D["GL"]["TAIRE"][inc].mean()
        m = cell_map(axs[1, 0], R, gg, t, "cividis", mcolors.Normalize(float(t.min()), float(t.max())))
        cbar(fig, m, axs[1, 0], "°C")
        panel_letter(axs[1, 0], "c", "Temperatura media del aire (forzamiento GLDAS)")
        et = D["GL"]["ET"][inc].mean()
        m = cell_map(axs[1, 1], R, gg, et, CMAP_SEQ, mcolors.Normalize(float(et.min()), float(et.max())))
        cbar(fig, m, axs[1, 1], "mm/día")
        panel_letter(axs[1, 1], "d", "Evapotranspiración media, GLDAS 0.25°")
    return save(fig, stem, prov(R, {"datos": [SRC_IMERG, SRC_GLDAS],
                                    "transformaciones": ["media 2001-2024 de los totales anuales (a) o de los meses (b-d)"]}))


def fig_tendencias(R, stem):
    D = R["D"]
    tr = R["trends"]
    specs = [("PRECIP_IMERG_0.1", D["g_im"], "pendiente_pct_clim_decada", "% de la media por década",
              "Lluvia (IMERG 0.1°)"),
             ("SM_RAIZ", D["g_gl"], "pendiente_decada", "mm por década", "Raíz 0-100 cm (GLDAS)"),
             ("TAIRE", D["g_gl"], "pendiente_decada", "°C por década", "Temperatura aire (GLDAS)"),
             ("ET", D["g_gl"], "pendiente_decada", "mm/día por década", "Evapotranspiración (GLDAS)")]
    with style():
        fig, axs = plt.subplots(2, 2, figsize=(WIDTH_MM * MM, 125 * MM), layout="constrained")
        for ax, (var, g, col, unit, title), L in zip(axs.ravel(), specs, "abcd"):
            t = tr[tr["variable"] == var].set_index("celda")
            v = t[col]
            ns = list(t.index[~(t["q_bh_empirico"] < 0.05)])
            m = cell_map(ax, R, g, v, CMAP_DIV if var != "TAIRE" else "RdBu_r", sym_norm(v), nonsig=ns)
            cbar(fig, m, ax, unit)
            nsig = int((t["q_bh_empirico"] < 0.05).sum())
            panel_letter(ax, L, f"{title}: {nsig}/{len(t)} celdas q < 0.05")
    return save(fig, stem, prov(R, {
        "datos": [SRC_IMERG, SRC_GLDAS],
        "metodo": ("Theil-Sen sobre medias anuales de anomalías mensuales; Mann-Kendall con corrección AR(1); "
                   f"p calibrado contra {R['args']['n_surr']} sustitutos de fases aleatorias (misma fase en todas las celdas); "
                   "Benjamini-Hochberg por variable"),
        "rayado": "celda con q (BH sobre el p calibrado) >= 0.05: color atenuado y rayado = no se distingue de la variabilidad natural",
        "autocorrelacion_espacial": "celdas vecinas no son pruebas independientes; ver I de Moran y p de campo en el informe"}))


def _window(R, lo, hi, n=12):
    s = R["spi_im3"].mean(axis=1).loc[lo:hi]
    tmin = s.idxmin()
    k = s.index.get_loc(tmin)
    i0 = max(0, min(k - n // 2, len(s) - n))
    return s.index[i0:i0 + n]


def fig_sequia(R, stem, lo, hi, nombre):
    D = R["D"]
    months = _window(R, lo, hi)
    spi = R["spi_im3"]
    z = R["z"]["SM_RAIZ"]
    nS, nZ = mcolors.TwoSlopeNorm(vmin=-2.5, vcenter=0, vmax=2.5), mcolors.TwoSlopeNorm(vmin=-2.5, vcenter=0, vmax=2.5)
    with style():
        fig, axs = plt.subplots(4, 6, figsize=(WIDTH_MM * MM, 112 * MM), layout="constrained")
        for k, t in enumerate(months):
            r, c = divmod(k, 6)
            a1, a2 = axs[r, c], axs[r + 2, c]
            m1 = cell_map(a1, R, D["g_im"], spi.loc[t], CMAP_DIV, nS, labels=False)
            m2 = cell_map(a2, R, D["g_gl"], z.loc[t], CMAP_DIV, nZ, labels=False)
            a1.set_title(t.strftime("%Y-%m"), fontsize=6, pad=1.5)
            a2.set_title(t.strftime("%Y-%m"), fontsize=6, pad=1.5)
        cbar(fig, m1, axs[:2, :].ravel().tolist(), "SPI-3 (IMERG 0.1°): lluvia acumulada 3 meses, estandarizada")
        cbar(fig, m2, axs[2:, :].ravel().tolist(), "z robusto de humedad en la zona de raíces (GLDAS 0.25°)")
        fig.suptitle(f"Sequía {nombre}: lluvia (filas 1-2) y suelo (filas 3-4), mes a mes", fontsize=7)
    return save(fig, stem, prov(R, {"datos": [SRC_IMERG, SRC_GLDAS], "meses": [m.strftime("%Y-%m") for m in months],
                                    "seleccion_meses": f"12 meses centrados en el mínimo del SPI-3 medio nacional entre {lo} y {hi}",
                                    "escala": "misma escala de color −2.5..2.5 en todos los paneles"}))


def fig_contradicciones(R, stem):
    D = R["D"]
    ct = R["contra"].set_index("celda")
    panels = [("n_A_raiz", "A: volvió la lluvia (IMERG), la raíz no"),
              ("n_A_raiz_lluvia_modelo", "A con la lluvia que forzó a GLDAS"),
              ("n_B1_suelo_seco_sin_sequia", "B1: suelo seco sin sequía de lluvia"),
              ("n_B2_suelo_normal_en_sequia", "B2: suelo normal durante sequía de lluvia")]
    panels = [p for p in panels if p[0] in ct.columns]
    vmax = max(1, int(np.nanmax([ct[c].max() for c, _ in panels])))
    cmap = plt.get_cmap("magma_r", vmax + 1)
    norm = mcolors.BoundaryNorm(np.arange(-0.5, vmax + 1.5), cmap.N)
    with style():
        fig, axs = plt.subplots(2, 2, figsize=(WIDTH_MM * MM, 122 * MM), layout="constrained")
        for ax, (col, title), L in zip(axs.ravel(), panels, "abcd"):
            m = cell_map(ax, R, D["g_gl"], ct[col], cmap, norm)
            panel_letter(ax, L, f"{title} (total {int(ct[col].sum())})")
        for ax in axs.ravel()[len(panels):]:
            ax.axis("off")
        cbar(fig, m, axs.ravel().tolist(), "número de episodios 2001-2024", ticks=range(0, vmax + 1))
    return save(fig, stem, prov(R, {"datos": [SRC_IMERG, SRC_GLDAS, "GLDAS Rainf_f_tavg (lluvia de forzamiento)"],
                                    "definiciones": {"A": "SPI-3 vuelve a >= 0 tras SPI-3 <= -1 (2+ meses) y z raíz < -1 ese mes y el siguiente",
                                                     "B1": "2+ meses con z raíz < -1 y SPI-3 >= 0",
                                                     "B2": "2+ meses con z raíz >= 0 y SPI-3 <= -1"},
                                    "advertencia": "GLDAS-2.1 se forzó con GPCP, no con IMERG: A con IMERG puede ser diferencia entre productos (panel b)"}))


def fig_memoria(R, stem):
    D = R["D"]
    pt = R["cm"].point
    sel = lambda m: pt[(pt["respuesta"] == "SM_RAIZ") & (pt["metrica"] == m)].set_index("celda")["valor"]  # noqa: E731
    lag = R["lagp"][R["lagp"]["respuesta"] == "SM_RAIZ"].set_index("celda")["lag_max_meses"]
    with style():
        fig, axs = plt.subplots(1, 3, figsize=(WIDTH_MM * MM, 62 * MM), layout="constrained")
        phi = sel("phi")
        m = cell_map(axs[0], R, D["g_gl"], phi, CMAP_SEQ, mcolors.Normalize(float(phi.min()), float(phi.max())))
        cbar(fig, m, axs[0], "φ (fracción de la anomalía que queda al mes siguiente)")
        panel_letter(axs[0], "a", "Memoria de la raíz (ARX)")
        r = sel("r_spi")
        m = cell_map(axs[1], R, D["g_gl"], r, CMAP_SEQ, mcolors.Normalize(float(r.min()), float(r.max())))
        cbar(fig, m, axs[1], "r entre SPI-3 y z raíz (mismo mes)")
        panel_letter(axs[1], "b", "Acople lluvia → raíz")
        cmap = plt.get_cmap("cividis", 7)
        m = cell_map(axs[2], R, D["g_gl"], lag, cmap, mcolors.BoundaryNorm(np.arange(-0.5, 7.5), 7))
        cbar(fig, m, axs[2], "meses", ticks=range(7))
        panel_letter(axs[2], "c", "Desfase de máxima |r| (SPI-3 → raíz)")
    return save(fig, stem, prov(R, {"datos": [SRC_IMERG, SRC_GLDAS],
                                    "modelo": "z(t) = c + φ z(t−1) + γ SPI-1(t) + e; r = Pearson(SPI-3(t), z(t)); IC por bootstrap de bloques de 12 meses en results/"}))


def fig_contraste(R, stem):
    D = R["D"]
    top = demo_pair(R)
    if top is None:
        return []
    a, b, resp, met = top["celda_a"], top["celda_b"], top["respuesta"], top["metrica"]
    cg = D["cells_gl"].set_index("celda")
    key = f"{a}|{b}"
    mt = R["matched"].get(key, {}).get("episodios", pd.DataFrame())
    with style():
        fig = plt.figure(figsize=(WIDTH_MM * MM, 130 * MM), layout="constrained")
        gs = fig.add_gridspec(3, 3, height_ratios=[1.25, 1, 1])
        ax0 = fig.add_subplot(gs[0, :2])
        base_map(ax0, R)
        for c, col, lab in ((a, OI["blue"], "A"), (b, OI["vermillion"], "B")):
            la, lo = cg.loc[c, "lat"], cg.loc[c, "lon"]
            ax0.add_patch(Rectangle((lo - 0.125, la - 0.125), 0.25, 0.25, facecolor=col, alpha=0.85, edgecolor="black", lw=0.5, zorder=4))
            other = b if c == a else a
            dy = 0.19 if la >= cg.loc[other, "lat"] else -0.19
            ax0.text(lo, la + dy, f"{lab}: {cg.loc[c, 'provincia_principal']}", ha="center", va="center", fontsize=6,
                     zorder=5, bbox={"facecolor": "white", "edgecolor": "none", "pad": 0.5, "alpha": 0.8})
        inc = cg[cg["incluida"]]
        ax0.scatter(inc["lon"], inc["lat"], s=1.5, color=GREY, zorder=2)
        panel_letter(ax0, "a", "Par con lluvia parecida (celdas GLDAS 0.25°)")
        axt = fig.add_subplot(gs[0, 2])
        axt.axis("off")
        lines = [f"Respuesta: {resp}, métrica: {met}",
                 f"A = {top['valor_a']:.2f}, B = {top['valor_b']:.2f}",
                 f"Δ = {top['delta']:.2f}  IC95 [{top['ic95_bajo']:.2f}, {top['ic95_alto']:.2f}]",
                 f"q (BH, p calibrado) = {top['q_bh_calibrado']:.3g}",
                 f"robustez: {int(top['variantes_ok'])}/{int(top['n_variantes'])} variantes",
                 f"distancia {top['distancia_km']:.0f} km; r(SPI-3) = {top['r_spi3']:.2f}",
                 f"lluvia anual: dif. {100 * top['dif_rel_lluvia_anual']:.1f} %"]
        if "etiqueta_producto" in top:
            lines.append("con lluvia GLDAS: " + ("sobrevive" if top.get("sobrevive_lluvia_modelo") else "no sobrevive"))
        axt.text(0, 1, "\n".join(lines), va="top", fontsize=6, linespacing=1.5)
        ax1 = fig.add_subplot(gs[1, :])
        for c, col, ls in ((a, OI["blue"], "-"), (b, OI["vermillion"], (0, (3, 1.5)))):
            ax1.plot(R["spi"][3].index, R["spi"][3][c], color=col, lw=0.7, ls=ls)
        ax1.axhline(-1, color="#333333", lw=0.5, ls=(0, (4, 2)))
        ax1.set_ylabel("SPI-3")
        panel_letter(ax1, "b", "Lluvia: SPI-3 de A (azul, continua) y B (bermellón, discontinua)")
        ax2 = fig.add_subplot(gs[2, :2], sharex=ax1)
        for c, col, ls in ((a, OI["blue"], "-"), (b, OI["vermillion"], (0, (3, 1.5)))):
            ax2.plot(R["z"][resp].index, R["z"][resp][c], color=col, lw=0.7, ls=ls)
        ax2.axhline(-1, color="#333333", lw=0.5, ls=(0, (4, 2)))
        ax2.set_ylabel(f"z {resp}")
        ax2.xaxis.set_major_locator(mdates.YearLocator(4))
        ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        panel_letter(ax2, "c", f"Respuesta: z de {resp}")
        ax3 = fig.add_subplot(gs[2, 2])
        if len(mt):
            for _, e in mt.iterrows():
                ax3.plot([0, 1], [e["z_retorno_a"], e["z_retorno_b"]], color=GREY, lw=0.6)
            ax3.scatter(np.zeros(len(mt)), mt["z_retorno_a"], s=8, color=OI["blue"], zorder=3)
            ax3.scatter(np.ones(len(mt)), mt["z_retorno_b"], s=8, marker="s", color=OI["vermillion"], zorder=3)
            ax3.set_xticks([0, 1])
            ax3.set_xticklabels(["A", "B"])
            ax3.set_xlim(-0.4, 1.4)
            ax3.set_ylabel("z raíz al volver la lluvia")
            panel_letter(ax3, "d", f"{len(mt)} episodios emparejados")
        else:
            ax3.axis("off")
            ax3.text(0, 0.5, "sin episodios emparejables", fontsize=6)
    return save(fig, stem, prov(R, {"datos": [SRC_IMERG, SRC_GLDAS], "par": [a, b], "respuesta": resp, "metrica": met,
                                    "emparejamiento": "episodios que terminan con <= 2 meses de diferencia y |ΔSPI-3 mínimo| <= 0.5"}))


def fig_calibracion(R, stem):
    cal = R["cal_tr"]
    ns = R["null_sum"]
    with style():
        fig, axs = plt.subplots(1, 3, figsize=(WIDTH_MM * MM, 64 * MM), layout="constrained",
                                gridspec_kw={"width_ratios": [1.1, 1, 1.4]})
        vars_ = list(cal)
        for k, meth, col, mk in ((0, "fase", OI["blue"], "o"), (1, "bloques", OI["orange"], "s")):
            y = np.arange(len(vars_)) + (k - 0.5) * 0.25
            v = [cal[x][meth]["tasa_empirica_p05"] for x in vars_]
            lo = [cal[x][meth]["tasa_empirica_p05_ic95"][0] for x in vars_]
            hi = [cal[x][meth]["tasa_empirica_p05_ic95"][1] for x in vars_]
            axs[0].errorbar(v, y, xerr=[np.subtract(v, lo), np.subtract(hi, v)], fmt=mk, color=col, ms=3, lw=0.6,
                            capsize=0, label="fases aleatorias" if meth == "fase" else "bloques de 24 meses")
        axs[0].axvline(0.05, color="black", lw=0.6, ls=(0, (4, 2)))
        axs[0].set_yticks(range(len(vars_)))
        axs[0].set_yticklabels([x.replace("PRECIP_IMERG_0.1", "lluvia IMERG") for x in vars_])
        axs[0].set_xlabel("fracción de celdas con p < 0.05 en mapas nulos")
        axs[0].legend(frameon=False, fontsize=5.5, loc="lower right")
        panel_letter(axs[0], "a", "Tendencias: tasa de falsos positivos")
        v = "SM_RAIZ" if "SM_RAIZ" in cal else vars_[0]
        c = cal[v]["fase"]
        axs[1].bar(["nulo: media", "nulo: p95", "observado"],
                   [c["celdas_p05_nulo_media"], c["celdas_p05_nulo_p95"], c["celdas_p05_observadas"]],
                   color=[GREY, GREY, OI["vermillion"]], width=0.6)
        axs[1].set_ylabel("celdas con p < 0.05")
        panel_letter(axs[1], "b", f"Campo {v}: p de campo = {c['p_campo']:.3f}")
        d = ns[ns["respuesta"] != "TODAS"].copy()
        d["lab"] = d["respuesta"] + " · " + d["metrica"]
        y = np.arange(len(d))
        se = np.sqrt(d["tasa_empirica_p05"] * (1 - d["tasa_empirica_p05"]) / d["n"])
        axs[2].errorbar(d["tasa_empirica_p05"], y, xerr=1.96 * se, fmt="o", color=OI["green"], ms=3, lw=0.6)
        if "tasa_p05_tras_calibrar" in d:
            axs[2].scatter(d["tasa_p05_tras_calibrar"], y, s=10, facecolors="none", edgecolors="black", lw=0.6, zorder=3)
            axs[2].text(0.98, 0.02, "● bootstrap  ○ tras calibrar", transform=axs[2].transAxes, ha="right", fontsize=5.5)
        axs[2].axvline(0.05, color="black", lw=0.6, ls=(0, (4, 2)))
        axs[2].set_yticks(y)
        axs[2].set_yticklabels(d["lab"], fontsize=5.5)
        axs[2].set_xlabel("fracción con p < 0.05 bajo el nulo")
        tot = ns[ns["respuesta"] == "TODAS"].iloc[0]
        panel_letter(axs[2], "c", f"Pares: global {tot['tasa_empirica_p05']:.3f} (nominal 0.05)")
    return save(fig, stem, prov(R, {"metodo_tendencias": "sustitutos de fases aleatorias multivariadas y de bloques circulares de 24 meses sobre residuos sin ciclo ni recta; barras = percentiles 2.5-97.5 de la tasa por mapa nulo",
                                    "metodo_pares": "nulo paramétrico ARX común con residuos remuestreados en bloques conjuntos de 12 meses; barras = ±1.96 EE binomial",
                                    "n_sustitutos_tendencias": R["args"]["n_surr"], "n_sustitutos_pares": R["args"]["n_surr_pares"],
                                    "pares_calibracion": len(R["pares_calibracion"])}))


def fig_santo_domingo(R, stem):
    ev = R["event"]
    if ev is None:
        return []
    D = R["D"]
    per = ev["por_celda"].set_index("celda")
    with style():
        fig, axs = plt.subplots(1, 3, figsize=(WIDTH_MM * MM, 66 * MM), layout="constrained",
                                gridspec_kw={"width_ratios": [1.1, 1.2, 1.2]})
        if "media_hora" in ev:
            vals = ev["media_hora"]["max_24h_por_celda"]
            lab = "máximo de 24 h móviles 17-19 nov (UTC), mm"
        else:
            vals = per["mm_dia_utc_evento"]
            lab = "mm el 18-nov (día UTC)"
        m = cell_map(axs[0], R, D["g_im"], vals, "YlGnBu", mcolors.Normalize(0, float(vals.max())))
        axs[0].set_xlim(-70.45, -69.45)
        axs[0].set_ylim(18.25, 18.85)
        axs[0].set_xticks([-70.2, -69.8])
        axs[0].set_xticklabels(["70.2°O", "69.8°O"])
        axs[0].set_yticks([18.4, 18.7])
        axs[0].set_yticklabels(["18.4°N", "18.7°N"])
        cbar(fig, m, axs[0], lab)
        panel_letter(axs[0], "a", "Distrito Nacional y Santo Domingo")
        am = ev["maximos_anuales_cobertura"]
        order = per.index.tolist()
        data = [am[c].dropna().to_numpy() for c in order]
        axs[1].boxplot(data, vert=False, widths=0.6, showfliers=True, flierprops={"ms": 1.5},
                       medianprops={"color": "black", "lw": 0.6}, boxprops={"lw": 0.5}, whiskerprops={"lw": 0.5},
                       capprops={"lw": 0.5})
        axs[1].scatter(per["mm_dia_utc_evento"], np.arange(1, len(order) + 1), color=OI["vermillion"], s=6, zorder=3,
                       label="18-nov-2023 (día UTC)")
        axs[1].set_yticks([])
        axs[1].set_xlabel("máximo anual de lluvia diaria, mm (2001-2024)")
        axs[1].axvline(431, color="black", lw=0.6, ls=(0, (4, 2)))
        axs[1].text(425, len(order) / 2, "431 mm\npluviómetro\nONAMET", fontsize=5.5, ha="right", va="center")
        axs[1].legend(frameon=False, fontsize=5.5, loc="upper right", bbox_to_anchor=(1.0, 1.0))
        axs[1].set_ylim(0.3, len(order) + 0.7)
        panel_letter(axs[1], "b", f"{len(order)} celdas IMERG (DN + Santo Domingo)")
        if "serie_hh_celda" in ev:
            s = ev["serie_hh_celda"].loc["2023-11-17":"2023-11-20"]
            axs[2].bar(s.index, s.to_numpy(), width=1 / 48, color=OI["blue"], align="edge")
            axs[2].set_ylabel("mm por media hora")
            ax2 = axs[2].twinx()
            ax2.plot(s.index, s.rolling(48, min_periods=46).sum(), color="black", lw=0.7)
            ax2.set_ylabel("suma móvil 24 h, mm")
            ax2.spines["right"].set_visible(True)
            axs[2].xaxis.set_major_formatter(mdates.DateFormatter("%d-nov"))
            axs[2].xaxis.set_major_locator(mdates.DayLocator())
            axs[2].set_xlabel("día (00 UTC)")
            panel_letter(axs[2], "c", f"Media hora IMERG, celda {ev['media_hora']['celda']}")
        else:
            axs[2].axis("off")
    return save(fig, stem, prov(R, {"datos": [SRC_IMERG, "IMERG Final V07 media hora (doi:10.5067/GPM/IMERG/3B-HH/07)"],
                                    "referencia": ev["afirmacion_contrastada"], "nota": ev["nota"]}))


def fig_provincias(R, stem):
    pr = R["prov"]
    order = pr["spi3"].columns.tolist()
    lat = {u.name: np.mean(u.bounds[1::2]) for u in R["D"]["units"]}
    order = sorted(order, key=lambda p: -lat.get(p, 0))
    with style():
        fig, axs = plt.subplots(2, 1, figsize=(WIDTH_MM * MM, 150 * MM), layout="constrained", sharex=True)
        for ax, key, lab, L in ((axs[0], "spi3", "SPI-3 (IMERG, media ponderada por área)", "a"),
                                (axs[1], "z_raiz", "z robusto raíz (GLDAS, media ponderada por área)", "b")):
            d = pr[key][order]
            t = mdates.date2num(d.index.to_pydatetime())
            m = ax.pcolormesh(np.append(t, t[-1] + 31), np.arange(len(order) + 1), d.T.to_numpy(), cmap=CMAP_DIV,
                              norm=mcolors.TwoSlopeNorm(vmin=-2.5, vcenter=0, vmax=2.5), rasterized=True)
            ax.set_yticks(np.arange(len(order)) + 0.5)
            ax.set_yticklabels(order, fontsize=5)
            ax.invert_yaxis()
            cbar(fig, m, ax, lab)
            panel_letter(ax, L, lab)
        axs[1].xaxis_date()
        axs[1].xaxis.set_major_locator(mdates.YearLocator(2))
        axs[1].xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    return save(fig, stem, prov(R, {"datos": [SRC_IMERG, SRC_GLDAS],
                                    "ponderacion": "peso de cada celda = su área × fracción de la celda dentro de la provincia",
                                    "orden": "provincias de norte a sur (latitud media de su caja)"}))


def fig_grace(R, stem):
    g = R.get("grace")
    if g is None or not len(g):
        return []
    D = R["D"]
    soil = D["GL"]["SM_RAIZ"][R["inc"]].mean(axis=1)
    anom = soil - soil.groupby(soil.index.month).transform("mean")
    with style():
        fig, axs = plt.subplots(2, 1, figsize=(WIDTH_MM * MM, 85 * MM), sharex=True, layout="constrained")
        axs[0].fill_between(g["fecha"], g["tws_cm"] - g["incertidumbre_cm"], g["tws_cm"] + g["incertidumbre_cm"],
                            color=LIGHT_FILL, lw=0)
        axs[0].plot(g["fecha"], g["tws_cm"], color="black", lw=0.8, marker="o", ms=1.2)
        axs[0].axvspan(pd.Timestamp("2017-07-01"), pd.Timestamp("2018-06-01"), color="#EEEEEE", lw=0)
        axs[0].text(pd.Timestamp("2017-12-01"), 0.98, "sin satélite (GRACE → GRACE-FO)", transform=axs[0].get_xaxis_transform(),
                    ha="center", va="top", fontsize=5.5)
        axs[0].axhline(0, color="#333333", lw=0.4)
        axs[0].set_ylabel("cm de agua equivalente")
        panel_letter(axs[0], "a", f"Agua total almacenada, media nacional (GRACE/GRACE-FO JPL RL06.3, ~3° efectivos; "
                                  f"{int(g['celdas_0_5_usadas'].iloc[0])} celdas 0.5°)")
        axs[1].plot(anom.index, anom, color=OI["blue"], lw=0.7)
        axs[1].axhline(0, color="#333333", lw=0.4)
        axs[1].set_ylabel("mm (anomalía)")
        axs[1].xaxis.set_major_locator(mdates.YearLocator(2))
        axs[1].xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        panel_letter(axs[1], "b", "Humedad de la zona de raíces, media nacional GLDAS (anomalía mensual)")
    return save(fig, stem, prov(R, {"datos": ["JPL GRACE/GRACE-FO Mascon RL06.3 CRI v04 (doi:10.5067/TEMSC-3JC634)", SRC_GLDAS],
                                    "nota": "contexto nacional; no sirve para provincias ni celdas; sin factores de ganancia; banda = incertidumbre JPL"}))


def make_all(R: dict, fdir: Path) -> dict:
    fdir = Path(fdir)
    fdir.mkdir(parents=True, exist_ok=True)
    out = {}
    jobs = [("fig01_climatologias", fig_climatologias), ("fig02_tendencias", fig_tendencias),
            ("fig05_contradicciones", fig_contradicciones), ("fig06_memoria_acople", fig_memoria),
            ("fig07_mejor_contraste", fig_contraste), ("fig08_calibracion_fpr", fig_calibracion),
            ("fig09_santo_domingo_2023", fig_santo_domingo), ("fig10_provincias", fig_provincias),
            ("fig11_grace_contexto", fig_grace)]
    for name, fn in jobs:
        out[name] = fn(R, fdir / name)
        print(f"  figura {name}", flush=True)
    for name, (lo, hi), lab in (("fig03_sequia_2015", ("2014-06-01", "2016-06-01"), "2015"),
                                ("fig04_sequia_2019_2020", ("2019-01-01", "2020-12-01"), "2019-2020")):
        out[name] = fig_sequia(R, fdir / name, lo, hi, lab)
        print(f"  figura {name}", flush=True)
    return out


if __name__ == "__main__":  # desarrollo: python -m earthmemory.figures estado.pkl carpeta
    import pickle
    import sys
    make_all(pickle.loads(Path(sys.argv[1]).read_bytes()), Path(sys.argv[2]))
