"""Pieza 1 · «Barcode of doubt»: 32 provincias × 288 meses, estado de acuerdo de los cuatro productos de lluvia.

Cada celda = una provincia-mes. Estados (SPI-3 ≤ −1 = alarma de sequía; definiciones de la auditoría):
  unánime (4 de 4 en alarma) · mayoría (3 de 4, el cuarto entre −1 y 0) · dividido (1-2 de 4, el resto entre
  −1 y 0) · contradicción clara (1-3 de 4 en alarma y otro con SPI-3 ≥ 0) · sin alarma (0 de 4).
Filas ordenadas por la tasa condicional de cambio de decisión (results/auditoria/cambio_decision_sequia_provincias.csv).
"""

from __future__ import annotations

import numpy as np
from matplotlib.colors import ListedColormap
from matplotlib.patches import Rectangle

from . import datos as D
from .estilo import OI, SLIDE, SQUARE, cabecera, entrada, guardar, lienzo, pie, procedencia, theme_list

NOMBRE = "01_barcode_of_doubt"
FUENTE = ("Data: NASA GPM IMERG V07 Final · CHC CHIRPS v2.0 · NASA GLDAS-2.1 forcing rain (GPCP) · NASA MERRA-2 "
          "PRECTOTCORR via POWER · geoBoundaries ADM1 · SPI-3 per product, own 2001–2024 climatology,\n"
          "area-weighted province means. The four products share gauge and satellite inputs: agreement is not "
          "independent validation, so this disagreement is a lower bound.  ·  Analysis: Stellar Horizons, NASA Space Apps 2026")


def colores(t: dict) -> dict:
    return {D.NODATA: t["bg"], D.NONE: t["none"], D.SPLIT: OI["blue"], D.MAJ: OI["sky"], D.UNAN: OI["green"],
            D.CONTRA: OI["vermillion"]}


def _matriz(E, orden):
    M = E[orden].to_numpy().T  # (32, 288)
    return M


def dibujar(t: dict, E, cnt: dict, prov, pa, size=SLIDE) -> object:
    sq = size == SQUARE
    fig = lienzo(t, size)
    col = colores(t)
    codes = [D.NODATA, D.NONE, D.SPLIT, D.MAJ, D.UNAN, D.CONTRA]
    cmap = ListedColormap([col[c] for c in codes])
    orden = prov.sort_values(["tasa_condicional", "n_no_unanime"], ascending=[False, False]).index.tolist()
    M = _matriz(E, orden)
    idx = np.searchsorted(codes, M) if False else np.vectorize({c: i for i, c in enumerate(codes)}.get)(M)
    if sq:
        ax = fig.add_axes([0.235, 0.155, 0.70, 0.60])
    else:
        ax = fig.add_axes([0.175, 0.165, 0.745, 0.555])
    ax.imshow(idx, cmap=cmap, vmin=-0.5, vmax=len(codes) - 0.5, aspect="auto", interpolation="nearest",
              extent=(0, M.shape[1], M.shape[0], 0))
    for s in ax.spines.values():
        s.set_visible(False)
    # años
    yrs = E.index.year.to_numpy()
    starts = [int(np.flatnonzero(yrs == y)[0]) for y in range(2001, 2025)]
    lab_y = (2001, 2005, 2010, 2015, 2020, 2024)
    ax.set_xticks(starts)
    ax.set_xticklabels([str(y) if y in lab_y else "" for y in range(2001, 2025)], fontsize=6.5 if sq else 10)
    ax.tick_params(axis="x", length=2.5 if sq else 4, color=t["muted"], pad=2)
    ax.set_xlim(0, M.shape[1])
    # provincias (etiqueta directa) y tasa condicional a la derecha
    ax.set_yticks(np.arange(M.shape[0]) + 0.5)
    ax.set_yticklabels(orden, fontsize=4.6 if sq else 7.6)
    ax.tick_params(axis="y", length=0, pad=3)
    if not sq:
        for i, p in enumerate(orden):
            r = prov.loc[p]
            ax.text(M.shape[1] + 2, i + 0.5, f"{r['tasa_condicional'] * 100:.0f}%", va="center", ha="left",
                    fontsize=7.3, color=t["ink"] if i < 5 else t["muted"])
        ax.text(M.shape[1] + 2, -0.9, "flip rate*", va="bottom", ha="left", fontsize=7.5, color=t["muted"])
        ax.text(-0.5, -0.9, "most product-sensitive ↓", va="bottom", ha="right", fontsize=7.5, color=t["muted"])
    # 2015: el único episodio en que los cuatro coinciden a gran escala
    y15 = starts[14]
    n15 = int(pa.loc[2015, "n_unanime_sequia"])
    a15 = int(pa.loc[2015, "n_alguna_alarma"])
    ax.annotate("", xy=(y15, -0.3), xytext=(y15 + 12, -0.3), xycoords="data",
                arrowprops=dict(arrowstyle="-", color=OI["green"], lw=1.6), annotation_clip=False)
    ax.text(y15 + 6, -0.8, f"2015: {n15} of the {cnt['unanimous']} unanimous calls ({a15} alarms that year)",
            ha="center", va="bottom", fontsize=5.0 if sq else 8.6, color=OI["green"])
    # clave compacta con recuentos
    items = [(D.UNAN, "All 4 agree: drought", cnt["unanimous"]),
             (D.MAJ, "3 of 4", cnt["majority"]),
             (D.SPLIT, "1–2 of 4 (rest near −1)", cnt["split"]),
             (D.CONTRA, "Contradiction: another reads normal/wet (SPI-3 ≥ 0)", cnt["contradiction"]),
             (D.NONE, "No alarm", cnt["no_alarm"])]
    if sq:
        kx, ky, dy = 0.05, 0.11, 0.0
        x = kx
        for k, lab, n in items:
            lab = {D.CONTRA: "Contradiction", D.SPLIT: "1–2 of 4", D.UNAN: "All 4 agree"}.get(k, lab)
            fig.patches.append(Rectangle((x, ky - 0.008), 0.022, 0.022, transform=fig.transFigure, color=col[k],
                                         ec=t["faint"] if k == D.NONE else "none", lw=0.5))
            txt = fig.text(x + 0.028, ky + 0.003, f"{lab}: {n:,}", fontsize=5.6, va="center", color=t["ink"])
            fig.canvas.draw()
            bb = txt.get_window_extent().transformed(fig.transFigure.inverted())
            x = bb.x1 + 0.022
    else:
        x, ky = 0.045, 0.785
        for k, lab, n in items:
            fig.patches.append(Rectangle((x, ky - 0.011), 0.014, 0.025, transform=fig.transFigure, color=col[k],
                                         ec=t["faint"] if k == D.NONE else "none", lw=0.6))
            txt = fig.text(x + 0.019, ky + 0.002, f"{lab}  ", fontsize=9.4, va="center", color=t["ink"])
            fig.canvas.draw()
            bb = txt.get_window_extent().transformed(fig.transFigure.inverted())
            t2 = fig.text(bb.x1, ky + 0.002, f"{n:,}", fontsize=9.4, va="center", color=t["muted"], fontweight="bold")
            fig.canvas.draw()
            bb = t2.get_window_extent().transformed(fig.transFigure.inverted())
            x = bb.x1 + 0.018
    if sq:
        cabecera(fig, t, "The barcode of doubt",
                 f"Only {cnt['unanimous']} of {cnt['n_alguna_alarma']:,} drought alarms (SPI-3 ≤ −1) were unanimous\n"
                 f"across four rainfall products · 32 provinces × 288 months", x=0.05, y=0.955, ts=15, ss=7.4)
        pie(fig, t, "Data: NASA IMERG V07 · CHIRPS v2.0 · GLDAS-2.1 (GPCP) · MERRA-2/POWER · geoBoundaries.\n"
                    "Rows sorted by flip rate. Analysis: Stellar Horizons, NASA Space Apps 2026", x=0.05, y=0.018, size=4.8)
    else:
        cabecera(fig, t, "The barcode of doubt: drought depends on which satellite you ask",
                 f"Each cell is one province-month, 2001–2024. Of {cnt['n_alguna_alarma']:,} drought alarms (SPI-3 ≤ −1 in at "
                 f"least one of four rainfall products),\n"
                 f"only {cnt['unanimous']} were unanimous; in "
                 f"{cnt['contradiction']:,} another product read normal or wet at the same time.", ts=23, ss=12)
        pie(fig, t, FUENTE + "\n*flip rate = share of a province's alarm months in which the four products are not "
                    "unanimous (results/auditoria/cambio_decision_sequia_provincias.csv). Jan–Feb 2001 blank: SPI-3 "
                    "needs three months.", size=7.6, y=0.022)
    return fig


def run(temas=None) -> dict:
    spi = D.spi3_provincias()
    E, cnt = D.estados(spi, -1.0)
    nat = D.check_contra_auditoria(E, cnt)
    prov = D.auditoria_provincias(-1.0)
    pa = D.auditoria_por_anio()
    E.to_csv(D.DATOS / "estados_acuerdo_provincia_mes.csv", encoding="utf-8")
    files = []
    for t in theme_list(temas):
        desc = (f"Barcode of doubt: 32 Dominican provinces x 288 months (2001-2024). Of {cnt['n_alguna_alarma']} "
                f"province-months with a drought alarm (SPI-3 <= -1) in any of four rainfall products, "
                f"{cnt['unanimous']} unanimous, {cnt['majority']} 3-of-4, {cnt['split']} 1-2-of-4, "
                f"{cnt['contradiction']} clear contradictions.")
        files += guardar(dibujar(t, E, cnt, prov, pa), NOMBRE, t, desc, FUENTE.split("\n")[0])
        files += guardar(dibujar(t, E, cnt, prov, pa, SQUARE), NOMBRE, t, desc, FUENTE.split("\n")[0], "_square")
    top = prov.sort_values("tasa_condicional", ascending=False).head(5)
    numeros = {**cnt, "auditoria_nacional": nat,
               "por_anio_unanime": D.auditoria_por_anio()["n_unanime_sequia"].to_dict(),
               "top5_tasa_condicional": top["tasa_condicional"].round(4).to_dict()}
    alt_en = (f"Stripe chart with 32 rows (Dominican provinces, sorted by how often the drought decision flips with "
              f"the product) and 288 thin columns (months 2001-2024). Most cells are dark (no alarm); alarm months "
              f"are mostly vermillion (clear contradiction: {cnt['contradiction']}) and blue shades (partial "
              f"agreement); green cells, where all four products agree on drought, are rare ({cnt['unanimous']} of "
              f"{cnt['n_alguna_alarma']}) and cluster in 2015 ({int(pa.loc[2015, 'n_unanime_sequia'])}).")
    alt_es = (f"Gráfico de franjas: 32 filas (provincias, ordenadas por la tasa de cambio de decisión) y 288 columnas "
              f"(meses 2001-2024). La mayoría de celdas son oscuras (sin alarma); los meses con alarma son sobre todo "
              f"bermellón (contradicción clara: {cnt['contradiction']}) y azules (acuerdo parcial); las verdes, donde "
              f"los cuatro productos coinciden en sequía, son raras ({cnt['unanimous']} de {cnt['n_alguna_alarma']}) y "
              f"se concentran en 2015 ({int(pa.loc[2015, 'n_unanime_sequia'])}).")
    procedencia(NOMBRE, "The barcode of doubt", "El código de barras de la duda", files,
                [entrada("data/auditoria/cache/imerg_diario.npz", "IMERG V07 Final diario (caché del motor auditoría)"),
                 entrada("data/nacional_hr/derivados/rejilla_005.npz", "CHIRPS v2.0 mensual 0.05°"),
                 entrada("data/nacional/gesdisc/GLDAS_NOAH025_M.2.1_Rainf", "GLDAS-2.1 Rainf_f_tavg mensual"),
                 entrada("data/nacional/power/mensual_DOM_PRECTOTCORR_2001_2024.json", "MERRA-2 vía NASA POWER"),
                 entrada("data/auditoria/cache/pesos_provincia_005.parquet", "pesos de provincia 0.05°"),
                 entrada("results/auditoria/cambio_decision_sequia_nacional.json", "totales de control"),
                 entrada("results/auditoria/cambio_decision_sequia_provincias.csv", "orden de filas y tasas"),
                 entrada("results/auditoria/cambio_decision_sequia_por_anio.csv", "control por año")],
                "SPI-3 por provincia (auditoria.analisis.monthly_cubes + G05.province_mean + decision.spi3); estados con "
                "decision.flip_components (umbral −1.0) y contradicción clara = no unánime y máx SPI-3 ≥ 0. Recuentos "
                "comprobados con assert contra results/auditoria (nacional, por año y por provincia).",
                numeros, alt_en, alt_es,
                ["Los cuatro productos comparten insumos (pluviómetros GTS, IR): la tasa es un mínimo.",
                 "Parte del desacuerdo es efecto de umbral (estados 'dividido'/'3 de 4' con el resto entre −1 y 0)."])
    return {"archivos": files, "numeros": numeros}
