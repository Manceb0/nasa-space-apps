"""Figura 11: ¿el cambio está en la parte infrarroja o en la de microondas de IMERG? Lee results/tropical/gpm_fuentes/.
Sin barras ni pasteles: series de anomalías y estimaciones con su intervalo."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from ..galeria.estilo import OI, TEMAS, aplicar, cabecera, pie  # noqa: E402

RES = Path("results/tropical/gpm_fuentes")
OUT = Path("figures/tropical")


def titulo(R):
    V, n = R["veredicto"], R["zonas"]["nacional"]
    if not V["H3"]:
        return "La cobertura de microondas también cambió: la prueba es ambigua."
    if V["H2"]:
        return "El cambio se concentra en la parte infrarroja de IMERG; la causa sigue sin probar."
    if n["f_mw"]["ic95"][1] < 0:
        return "La parte de microondas también cambia: la pista solo infrarroja pierde fuerza."
    return "Ni la parte infrarroja ni la de microondas explican el cambio con claridad."


def figura(t):
    aplicar(t)
    R = json.loads((RES / "resumen.json").read_text(encoding="utf-8"))
    P = json.loads((RES / "predicciones_registradas.json").read_text(encoding="utf-8"))
    A = pd.read_csv(RES / "anomalias_mensuales_nacional.csv", index_col=0)
    A.index = pd.PeriodIndex(A.index, freq="M").to_timestamp()
    n = R["zonas"]["nacional"]
    fig = plt.figure(figsize=(13.333, 7.5), facecolor=t["bg"])
    gs = fig.add_gridspec(2, 2, left=0.18, right=0.97, top=0.74, bottom=0.14, hspace=0.55, wspace=0.25,
                          width_ratios=[1.25, 1])
    # a) anomalías mensuales
    ax = fig.add_subplot(gs[0, :])
    ax.axvspan(pd.Timestamp("2017-12-01"), pd.Timestamp("2018-11-30"), color=t["muted"], alpha=0.15, lw=0)
    ax.text(pd.Timestamp("2017-12-10"), 0.97, "transición excluida\n(GOES-16 → GOES-East 18-dic-2017;\nventana del "
            "modelo feb-nov 2018)", transform=ax.get_xaxis_transform(), va="top", fontsize=8, color=t["muted"])
    for c, col, lab in (("f_mw", OI["blue"], "con microondas directas (f_mw)"),
                        ("f_ir", OI["vermillion"], "sin microondas: morphing + infrarrojo (f_ir)")):
        s = 100 * A[c]
        ax.plot(s.index, s, color=col, lw=0.7, alpha=0.45)
        ax.plot(s.index, s.rolling(3, center=True).mean(), color=col, lw=2.2, label=lab)
    ax.axhline(0, color=t["muted"], lw=0.6)
    ax.set_ylabel("anomalía del % de medias\nhoras con lluvia (pp)", fontsize=9)
    ax.legend(loc="lower left", fontsize=8.5, frameon=False, ncol=2)
    ax.set_title("a   Serie nacional, 2016-2019, sin ciclo estacional (línea gruesa: media móvil de 3 meses)",
                 loc="left", fontsize=10, color=t["ink"])
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    # b) cambios con IC
    ax = fig.add_subplot(gs[1, 0])
    filas = [("f_mw", "con microondas (f_mw)", OI["blue"]), ("f_ir", "sin microondas (f_ir)", OI["vermillion"]),
             ("ir_menos_mw", "diferencia f_ir − f_mw", OI["orange"]), ("cob", "cobertura de microondas", t["muted"]),
             ("dias_humedos", "días ≥ 1 mm (IMERG)", t["ink"])]
    for y, (k, lab, col) in enumerate(filas):
        d, (lo, hi) = 100 * n[k]["delta"], [100 * v for v in n[k]["ic95"]]
        ax.plot([lo, hi], [y, y], color=col, lw=2)
        ax.scatter(d, y, color=col, s=50, zorder=3)
        ax.text(hi, y, f"  {d:+.2f} [{lo:+.2f}, {hi:+.2f}]", va="center", fontsize=8, color=t["ink"])
    hc = R["control_H1"]["IMERG_menos_CHIRPS"]
    d, (lo, hi) = 100 * hc["delta"], [100 * v for v in hc["ic95"]]
    y = len(filas)
    ax.plot([lo, hi], [y, y], color=OI["green"], lw=2)
    ax.scatter(d, y, color=OI["green"], s=50, marker="D", zorder=3)
    ax.text(hi, y, f"  {d:+.2f} [{lo:+.2f}, {hi:+.2f}]", va="center", fontsize=8, color=t["ink"])
    ax.set_yticks(range(len(filas) + 1), [f[1] for f in filas] + ["IMERG − CHIRPS (días ≥ 1 mm)"], fontsize=8.5)
    ax.invert_yaxis()
    ax.axvline(0, color=t["muted"], lw=0.8)
    ax.set_xlabel("después − antes (puntos porcentuales; IC 95 % por bootstrap de meses)", fontsize=8.5)
    ax.set_title("b   Cambio nacional (2018-12..2019-12 frente a 2016-01..2017-11)", loc="left", fontsize=10,
                 color=t["ink"])
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    xl = ax.get_xlim()
    ax.set_xlim(xl[0], xl[1] + (xl[1] - xl[0]) * 0.45)
    # c) veredicto y lugares
    ax = fig.add_subplot(gs[1, 1])
    ax.axis("off")
    ax.set_title("c   Predicciones registradas antes de descargar", loc="left", fontsize=10, color=t["ink"])
    txt = {"H1": "Control: IMERG − CHIRPS baja en esta ventana",
           "H2": "f_ir baja más que f_mw (IC de la diferencia < 0)",
           "H3": "La cobertura de microondas cambia < 10 %"}
    for i, k in enumerate(("H1", "H2", "H3")):
        ok = R["veredicto"][k]
        ax.text(0, 0.9 - i * 0.17, k + ("  se cumple" if ok else "  no se cumple"), color=OI["green"] if ok else
                OI["vermillion"], fontsize=9.5, fontweight="bold", transform=ax.transAxes, va="top")
        ax.text(0, 0.9 - i * 0.17 - 0.075, txt[k], color=t["ink"], fontsize=8.5, transform=ax.transAxes, va="top")
    lugares = [z for z in R["zonas"] if z != "nacional"]
    ax.text(0, 0.36, "f_ir − f_mw por lugar (pp):", color=t["muted"], fontsize=8.5, transform=ax.transAxes, va="top")
    for i, z in enumerate(lugares):
        ax.text(0.5 * (i % 2), 0.28 - 0.08 * (i // 2), f"{z}: {100 * R['zonas'][z]['ir_menos_mw']['delta']:+.1f}",
                color=t["ink"], fontsize=8.5, transform=ax.transAxes, va="top")
    cabecera(fig, t, titulo(R),
             "Si el paso de GOES-13 a GOES-16 en la entrada infrarroja cambió cuánto llueve según IMERG, el cambio "
             "debe verse en las medias horas sin microondas\ny no en las que tienen microondas directas. "
             f"IMERG V07 Final diario; 442 celdas. Predicciones registradas el {P['registradas_utc'][:16]} UTC.",
             ts=18, ss=10.5)
    pie(fig, t, "Fracciones de medias horas con lluvia: precipitation_cnt_cond / precipitation_cnt y las mismas solo "
                "con microondas (MWprecipitation_cnt*); los huecos de microondas son ausentes, no secos.\nNo es un "
                "grupo experimental independiente: el morphing también usa microondas. El diario no trae "
                "precipitationUncal ni IRinfluence (pendiente en media hora). NASA GPM IMERG V07 · CHIRPS v2.0.",
        y=0.012)
    base = OUT / f"11_infrarrojo_o_microondas_{t['name']}"
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
