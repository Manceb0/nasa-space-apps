"""Figura de la deducción tropical: el escalón de 2013 en la forma de contar días de lluvia + el relieve frente al
alisio. Solo datos reales de results/tropical/ (salidas de run.py). Tema oscuro (diapositiva) y claro (impresión).
Sin barras ni pasteles: franja temporal, pendientes por estación y mapa por celda."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.colors import TwoSlopeNorm  # noqa: E402

from ..galeria.estilo import OI, TEMAS, aplicar, cabecera, pie  # noqa: E402
from ..tendencias import datos  # noqa: E402

RES = Path("results/tropical")
OUT = Path("figures/tropical")
NOMBRES = {"DRM00078458": "Puerto Plata", "DRM00078479": "Punta Cana", "DRM00078482": "Barahona",
           "DRM00078486": "Santo Domingo"}


def _outline(ax, t):
    gj = datos.adm1_geojson()
    for f in gj["features"]:
        g = f["geometry"]
        polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        for poly in polys:
            ring = np.asarray(poly[0])
            ax.plot(ring[:, 0], ring[:, 1], color=t["muted"], lw=0.35, alpha=0.7)


def figura(t: dict):
    aplicar(t)
    m = pd.read_csv(RES / "p4_mensual.csv")
    m["ym"] = pd.PeriodIndex(m["ym"], freq="M")
    s = (m["wi"] - m["wc"])
    s = s - s.groupby(m["ym"].dt.month).transform("mean")
    s = s.to_numpy() * 100                                              # puntos porcentuales
    res = json.loads((RES / "resumen.json").read_text(encoding="utf-8"))
    cp = res["p4"]["frecuencia_dias_humedos_IMERG_menos_CHIRPS"]
    k = int(np.flatnonzero(m["ym"].astype(str) == cp["punto_de_cambio"])[0])
    st = pd.read_csv(RES / "p5_quien_cambio_estaciones.csv")
    st = st[st["n_dias"] > 0]
    cel = pd.read_csv(RES / "p2_celdas.csv")
    sp = pd.read_csv(RES / "p2_relieve_spearman.csv")
    rho = sp[(sp["resultado"] == "log_CHIRPS_sobre_IMERG") & (sp["covariable"] == "ascenso_forzado_m_km")].iloc[0]

    fig = plt.figure(figsize=(13.333, 7.5), facecolor=t["bg"])
    gs = fig.add_gridspec(2, 6, left=0.045, right=0.975, top=0.735, bottom=0.12, hspace=0.62, wspace=0.55,
                          height_ratios=[1, 1.35])
    # a) franja mensual
    ax = fig.add_subplot(gs[0, :])
    lim = float(np.nanpercentile(np.abs(s), 97))      # colores saturan en el 3 % más extremo
    ax.imshow(s[None, :], aspect="auto", cmap="RdBu_r", norm=TwoSlopeNorm(0, -lim, lim),
              extent=(0, s.size, -1, 1), interpolation="nearest")
    ax.plot(np.arange(s.size) + 0.5, np.clip(s / lim * 0.9, -0.98, 0.98), color=t["ink"], lw=0.6, alpha=0.6)
    ax.hlines([cp["media_antes"] * 100 / lim * 0.9], 0, k, color=t["ink"], lw=2)
    ax.hlines([cp["media_despues"] * 100 / lim * 0.9], k, s.size, color=t["ink"], lw=2)
    ax.axvline(k, color=OI["yellow"], lw=1.6)
    ax.text(k, 1.04, f"▼ change point {cp['punto_de_cambio']}  (block-permutation p = {cp['p_bloques_12m']:.3f})",
            color=OI["yellow"], fontsize=9.5, va="bottom", ha="center", clip_on=False)
    yrs = np.arange(2001, 2025, 2)
    ax.set_xticks((yrs - 2001) * 12)
    ax.set_xticklabels(yrs)
    ax.set_yticks([])
    for sp_ in ax.spines.values():
        sp_.set_visible(False)
    ax.set_title("a   IMERG minus CHIRPS: share of wet days (≥ 1 mm), monthly, seasonal cycle removed  ·  red = IMERG "
                 f"counts more wet days  ·  colour saturates at ±{lim:.0f} pp", loc="left", fontsize=10, color=t["ink"], pad=18)

    # b) estaciones: pendiente antes → después
    names = list(NOMBRES)
    for n, sid in enumerate(names):
        axs = fig.add_subplot(gs[1, n])
        d = st[st["estacion"] == sid].set_index("periodo")
        for col, lab, c, mk in (("frec_estacion", "rain gauge", t["ink"], "o"), ("frec_IMERG", "IMERG", OI["vermillion"], "s"),
                                ("frec_CHIRPS", "CHIRPS", OI["sky"], "D")):
            y = [d.loc["antes", col] * 100, d.loc["despues", col] * 100]
            axs.plot([0, 1], y, color=c, lw=2, marker=mk, ms=5)
        axs.set_xticks([0, 1])
        axs.set_xticklabels(["2001–\n2013-09", "2013-10–\n2024"], fontsize=8)
        axs.set_xlim(-0.2, 1.2)
        axs.set_title(NOMBRES[sid], fontsize=9.5, color=t["ink"], loc="left")
        axs.tick_params(axis="y", labelsize=8)
        for side in ("top", "right"):
            axs.spines[side].set_visible(False)
        if n == 0:
            axs.set_ylabel("wet days (%)", fontsize=9)
    fig.text(0.045, 0.468, "b   Who changed? Wet-day share on the days each GHCN-Daily gauge reported",
             fontsize=10, color=t["ink"])
    for x0, lab, c in ((0.50, "● rain gauge", t["ink"]), (0.59, "■ IMERG", OI["vermillion"]), (0.65, "◆ CHIRPS", OI["sky"])):
        fig.text(x0, 0.468, lab, fontsize=10, color=c, fontweight="bold")

    # c) mapa barlovento
    axm = fig.add_subplot(gs[1, 4:])
    r = np.log(cel["lluvia_CHIRPS_mm_anio"] / cel["lluvia_IMERG_mm_anio"])
    lr = np.nanmax(np.abs(r))
    sc = axm.scatter(cel["lon"], cel["lat"], c=r, cmap="BrBG", norm=TwoSlopeNorm(0, -lr, lr), marker="s", s=19,
                     linewidths=0)
    _outline(axm, t)
    axm.annotate("", xy=(-68.75, 19.75), xytext=(-68.35, 19.9), arrowprops=dict(arrowstyle="->", color=t["ink"], lw=1.5))
    axm.text(-68.3, 19.95, "trade wind", fontsize=8, color=t["ink"], ha="right", va="bottom")
    axm.set_aspect(1 / np.cos(np.radians(18.8)))
    axm.set_xlim(-72.1, -68.2)
    axm.set_ylim(17.5, 20.1)
    axm.set_xticks([])
    axm.set_yticks([])
    for sp_ in axm.spines.values():
        sp_.set_visible(False)
    cb = fig.colorbar(sc, ax=axm, orientation="horizontal", fraction=0.05, pad=0.02)
    cb.set_ticks([-0.3, 0, 0.3])
    cb.set_ticklabels([f"{np.exp(v):.2f}" for v in (-0.3, 0, 0.3)])
    cb.ax.tick_params(labelsize=7.5)
    cb.set_label("CHIRPS ÷ IMERG, mean annual rain", fontsize=8.5)
    axm.set_title(f"c   Windward slopes: CHIRPS wetter\n     ρ = {rho['rho']:.2f} vs forced ascent, "
                  f"toroidal p = {rho['p_toroidal']:.3f}", loc="left", fontsize=10, color=t["ink"])

    cabecera(fig, t, "The rain didn't change in 2013. The way one satellite counts rainy days did.",
             f"IMERG goes from {cp['media_antes'] * 100:+.1f} to {cp['media_despues'] * 100:+.1f} percentage points of wet days "
             "relative to CHIRPS. At all four gauges IMERG loses 4 to 12 points of wet days\n"
             "while the gauges themselves average +0.2: IMERG's 'fewer, more intense rain days' looks like a measurement step, "
             "not a climate trend.\nIn space, the disagreement follows the mountains: windward slopes are wetter in CHIRPS, "
             "the rain shadow in IMERG.", ts=19, ss=10.5)
    pie(fig, t, "Data: NASA GPM IMERG V07 Final daily · CHIRPS v2.0 daily (aggregated to 0.1°) · NOAA GHCN-Daily (4 gauges "
               "with data 2001–2024) · Copernicus DEM GLO-90 · 442 cells, Dominican Republic, 2001–2024.\n"
               "Change point: Pettitt test on the deseasonalised monthly series; p from 2,999 permutations of 12-month "
               "blocks. Stripe and lines encode the same series. Stellar Horizons · NASA Space Apps 2026.")
    OUT.mkdir(parents=True, exist_ok=True)
    base = OUT / f"07_the_step_in_2013_{t['name']}"
    fig.savefig(base.with_suffix(".png"), dpi=200, facecolor=t["bg"],
                metadata={"Software": "matplotlib; figure code written with AI assistance (Claude), data unaltered"})
    fig.savefig(base.with_suffix(".pdf"), facecolor=t["bg"])
    plt.close(fig)
    return base


def main():
    for k in ("dark", "light"):
        print(figura(TEMAS[k]))


if __name__ == "__main__":
    main()
