"""Figura del veredicto del tercer testigo (ERA5) sobre el escalón de IMERG en 2013-10. Lee results/tropical/era5/.
Sin barras ni pasteles: series, puntos por lugar y el veredicto de cada predicción registrada."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from ..galeria.estilo import OI, TEMAS, aplicar, cabecera, pie  # noqa: E402

RES = Path("results/tropical/era5")
OUT = Path("figures/tropical")
PROD = {"IMERG": (OI["vermillion"], "o"), "CHIRPS": (OI["blue"], "s"), "ERA5": (OI["green"], "D")}


def figura(t):
    aplicar(t)
    S = pd.read_csv(RES / "series_mensuales_desestacionalizadas.csv", index_col=0)
    S.index = pd.PeriodIndex(S.index, freq="M").to_timestamp()
    T = pd.read_csv(RES / "cambio_frecuencia_por_punto.csv")
    R = json.loads((RES / "resumen.json").read_text(encoding="utf-8"))
    P = json.loads((RES / "predicciones_registradas.json").read_text(encoding="utf-8"))
    V, PT, med = R["veredicto"], R["pettitt"], R["cambio_medio_pp"]

    fig = plt.figure(figsize=(13.333, 7.5), facecolor=t["bg"])
    gs = fig.add_gridspec(2, 2, left=0.09, right=0.97, top=0.74, bottom=0.16, hspace=0.55, wspace=0.22,
                          height_ratios=[1, 1.05], width_ratios=[1.15, 1])
    # a) series
    ax = fig.add_subplot(gs[0, :])
    for k, c, lab in (("IMERG_menos_ERA5", OI["vermillion"], "IMERG − ERA5"),
                      ("CHIRPS_menos_ERA5", OI["blue"], "CHIRPS − ERA5")):
        s = 100 * S[k]
        ax.plot(s.index, s, color=c, lw=0.6, alpha=0.35)
        r = PT[k]
        ax.plot(s.index, s.rolling(12, center=True).mean(), color=c, lw=2.2,
                label=f"{lab}: punto de cambio {r['punto_de_cambio']} (p {r['p_bloques_12m']:.3f})")
    ax.legend(loc="lower left", fontsize=8.5, frameon=False)
    ax.axhline(0, color=t["muted"], lw=0.8)
    ax.axvline(pd.Timestamp("2013-10-01"), color=OI["yellow"], lw=1.2)
    ax.text(pd.Timestamp("2013-11-15"), ax.get_ylim()[1] * 0.92, "octubre 2013", color=OI["yellow"], fontsize=8.5,
            va="top")
    ax.set_xlim(pd.Timestamp("2001-01-01"), pd.Timestamp("2025-01-01"))
    ax.set_ylabel("diferencia en % de días\ncon lluvia (sin estación)", fontsize=9)
    ax.set_title("a   ¿Quién se separa de ERA5 en 2013? Media móvil de 12 meses (línea gruesa) sobre los valores "
                 "mensuales", loc="left", fontsize=10, color=t["ink"])
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    # b) cambio por punto
    ax = fig.add_subplot(gs[1, 0])
    pts = list(dict.fromkeys(T["punto"]))
    for y, p in enumerate(pts):
        d = T[T["punto"] == p].set_index("producto")["cambio_pp"]
        ax.plot([d.min(), d.max()], [y, y], color=t["muted"], lw=0.8, zorder=1)
        for prod, (c, mk) in PROD.items():
            ax.scatter(d[prod], y, color=c, marker=mk, s=46, zorder=2, label=prod if y == 0 else None)
    ax.axvline(0, color=t["muted"], lw=0.8)
    ax.set_yticks(range(len(pts)), pts, fontsize=9)
    ax.invert_yaxis()
    ax.set_xlabel("cambio en % de días con lluvia ≥ 1 mm: después − antes de oct-2013 (puntos porcentuales)",
                  fontsize=8.5)
    ax.legend(loc="lower left", fontsize=8.5, frameon=False, ncol=3, bbox_to_anchor=(0, 1.0))
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.set_title("b   Por lugar (celda ERA5 de 0,25°)", loc="left", fontsize=10, color=t["ink"], pad=26)
    # c) veredicto de las predicciones registradas
    ax = fig.add_subplot(gs[1, 1])
    ax.axis("off")
    ax.set_title("c   Predicciones escritas antes de bajar ERA5", loc="left", fontsize=10, color=t["ink"])
    cortas = {"E1": f"IMERG − ERA5 salta entre 2012-10 y 2014-12 (p < 0,05) → {PT['IMERG_menos_ERA5']['punto_de_cambio']}, "
                    f"p {PT['IMERG_menos_ERA5']['p_bloques_12m']:.3f}",
              "E2": f"ERA5 cambia < 2 pp e IMERG baja ≥ 4 pp → ERA5 {med['ERA5']:+.1f}, IMERG {med['IMERG']:+.1f}, "
                    f"CHIRPS {med['CHIRPS']:+.1f}",
              "E3": f"CHIRPS − ERA5 no salta en esa ventana → {PT['CHIRPS_menos_ERA5']['punto_de_cambio']}, "
                    f"p {PT['CHIRPS_menos_ERA5']['p_bloques_12m']:.3f}",
              "E4": f"La cantidad de lluvia no salta → {PT['log_cantidad_IMERG_sobre_ERA5']['punto_de_cambio']}, "
                    f"p {PT['log_cantidad_IMERG_sobre_ERA5']['p_bloques_12m']:.3f}"}
    for i, k in enumerate(("E1", "E2", "E3", "E4")):
        ok = V[k]
        ax.text(0.0, 0.92 - i * 0.24, "se cumple" if ok else "no se cumple", color=OI["green"] if ok else OI["vermillion"],
                fontsize=10, fontweight="bold", transform=ax.transAxes, va="top")
        ax.text(0.0, 0.92 - i * 0.24 - 0.085, f"{k}  {cortas[k]}", color=t["ink"], fontsize=8.6,
                transform=ax.transAxes, va="top", wrap=True)
    sostiene = V["E1"] and V["E2"] and V["E3"]
    if sostiene:
        titulo = "Un tercer testigo independiente confirma que el salto de 2013 es de IMERG."
    elif V["E2"] and V["E3"]:
        titulo = "ERA5 confirma que IMERG pierde días de lluvia, pero no de golpe en 2013."
    else:
        titulo = "El tercer testigo no confirma que el salto de 2013 sea solo de IMERG."
    cabecera(fig, t, titulo,
             "ERA5 (reanálisis europeo) no usa el algoritmo de IMERG ni los pluviómetros que alimentan a CHIRPS. "
             "Si IMERG empezó a contar menos días de lluvia,\nIMERG debe separarse de ERA5 en 2013 y CHIRPS no. "
             f"Seis lugares de RD, 2001-2024, día UTC. Predicciones registradas el {P['registradas_utc'][:16]} UTC.",
             ts=18, ss=10.5)
    pie(fig, t, "Pettitt sobre la serie mensual sin ciclo estacional; p por permutación de bloques de 12 meses "
                "(2999). IMERG y CHIRPS: media de las celdas de 0,1° dentro de cada celda ERA5.\nERA5 vía la API de "
                "archivo de Open-Meteo (models=era5). ERA5 es un modelo: tiende a la llovizna, por eso se compara "
                "el cambio y no el nivel;\nsus observaciones asimiladas también cambian con los años. NASA GPM IMERG "
                "V07 · CHIRPS v2.0 · ECMWF ERA5 · Stellar Horizons.", y=0.012)
    base = OUT / f"09_tercer_testigo_era5_{t['name']}"
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
