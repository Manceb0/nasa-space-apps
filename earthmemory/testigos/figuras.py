"""Figuras del motor de testigos (estilo de artículo: Okabe-Ito, letras de panel, PDF + PNG ≥ 200 ppp).
Solo LEEN lo que dejó la corrida en results/testigos/ (y el recorte SMAP L3 en data/testigos/derivados)."""

from __future__ import annotations

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

from phantom.figures import GREY, MM, OI, RC  # noqa: E402

from .common import FIG, NAC_HR, PAR_GLDAS, PAR_HR, RES, YUNA_ALTO  # noqa: E402

LAT0 = 18.8
NL = chr(10)
SRC = "Límites: geoBoundaries DOM ADM1 (dominio público, Natural Earth)."


def _note(fig, y, text, width=150, **_kw):
    import textwrap
    fig.text(0.01, y, textwrap.fill(text, width), fontsize=5.4, color="#444444", va="top")


def _save(fig, name):
    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / f"{name}.png", dpi=250, bbox_inches="tight", pad_inches=0.04, metadata={"Software": None})
    fig.savefig(FIG / f"{name}.pdf", bbox_inches="tight", pad_inches=0.04, metadata={"CreationDate": None})
    plt.close(fig)


def _j(name):
    p = RES / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def _adm1():
    from ..region import _polys
    gj = json.loads((NAC_HR / "limites" / "geoBoundaries-DOM-ADM1.geojson").read_text(encoding="utf-8"))
    return [p for f in gj["features"] for p in _polys(f["geometry"])]


def _borders(ax, polys, lw=0.3):
    for ext, _ in polys:
        ax.plot(ext[:, 0], ext[:, 1], color="#4D4D4D", lw=lw, zorder=4)


def _frame(ax, extent=(-72.05, -68.25, 17.45, 20.0)):
    ax.set_xlim(extent[0], extent[1])
    ax.set_ylim(extent[2], extent[3])
    ax.set_aspect(1 / np.cos(np.radians(LAT0)))
    ax.tick_params(labelsize=6, length=2, pad=1)
    xt = [x for x in np.arange(-72, -68, 0.5 if extent[1] - extent[0] < 2 else 1.0) if extent[0] <= x <= extent[1]]
    yt = [y for y in np.arange(17.5, 20.5, 0.5 if extent[3] - extent[2] < 2 else 1.0) if extent[2] <= y <= extent[3]]
    ax.set_xticks(xt)
    ax.set_xticklabels([f"{abs(x):g}°O" for x in xt])
    ax.set_yticks(yt)
    ax.set_yticklabels([f"{y:g}°N" for y in yt])


def _letter(ax, l, t=""):
    ax.text(0, 1.02, l, transform=ax.transAxes, fontsize=8, fontweight="bold", va="bottom")
    if t:
        ax.text(0.06, 1.02, t, transform=ax.transAxes, fontsize=6.6, va="bottom")


def _sites(ax, hr=True, gl=True):
    if gl:
        for k, c in (("A", OI["vermillion"]), ("B", OI["blue"])):
            p = PAR_GLDAS[k]
            ax.add_patch(Rectangle((p["lon"] - .125, p["lat"] - .125), .25, .25, fill=False, ec=c, lw=1.0, zorder=6))
            ax.text(p["lon"] + .14, p["lat"] + .1, f"G{k}", color=c, fontsize=6, fontweight="bold", zorder=7)
    if hr:
        for k, c in (("A", OI["vermillion"]), ("B", OI["blue"])):
            p = PAR_HR[k]
            ax.plot(p["lon"], p["lat"], marker="^", ms=4.5, mfc=c, mec="k", mew=0.4, zorder=7, ls="none")
            ax.text(p["lon"] + .03, p["lat"] + .03, f"H{k}", color=c, fontsize=6, fontweight="bold", zorder=7, ha="left")


def _edges(c):
    d = np.diff(c)
    return np.concatenate([[c[0] - d[0] / 2], c[:-1] + d / 2, [c[-1] + d[-1] / 2]])


# ------------------------------------------------------------------ T1: qué ve SMAP L3

def fig_calidad():
    q = pd.read_csv(RES / "smap_l3_calidad_pixeles.csv")
    res = _j("smap_l3_calidad_resumen.json")
    ny, nx = q["fila"].max() + 1, q["col"].max() + 1
    LA = q["lat"].to_numpy().reshape(ny, nx)
    LO = q["lon"].to_numpy().reshape(ny, nx)
    land = q["tierra_rd"].to_numpy().reshape(ny, nx)
    le, oe = _edges(LA[:, 0]), _edges(LO[0])
    polys = _adm1()
    with plt.rc_context(RC):
        fig = plt.figure(figsize=(180 * MM, 128 * MM))
        gs = fig.add_gridspec(2, 2, height_ratios=[1, 0.62], hspace=0.62, wspace=0.12)
        for k, (col, cmap, vmin, vmax, lab, title) in enumerate((
                ("frac_recomendado_am_pm", "cividis", 0, 0.7, "fracción de pasos con calidad recomendada", "¿Cuándo SMAP L3 ve el suelo?"),
                ("vwc_mediana_am", "viridis_r", 0, 12, "agua en la vegetación, mediana (kg/m²)", "Vegetación que tapa la banda L"))):
            ax = fig.add_subplot(gs[0, k])
            A = np.where(land, q[col].to_numpy().reshape(ny, nx), np.nan)
            m = ax.pcolormesh(oe, le, A, cmap=cmap, vmin=vmin, vmax=vmax, shading="flat", rasterized=True)
            if col.startswith("vwc"):
                ax.contour(LO, LA, np.where(land, A, np.nan), levels=[5], colors=[OI["vermillion"]], linewidths=0.8)
            _borders(ax, polys)
            _sites(ax)
            _frame(ax)
            cb = fig.colorbar(m, ax=ax, orientation="horizontal", fraction=0.05, pad=0.09, aspect=35)
            cb.set_label(lab, fontsize=6.3)
            cb.ax.tick_params(labelsize=5.8)
            _letter(ax, "ab"[k], title)
        ax.text(0.02, 0.03, "contorno: VWC = 5 kg/m²", transform=ax.transAxes, fontsize=5.6, color=OI["vermillion"])
        ax = fig.add_subplot(gs[1, :])
        pts = res["puntos"]
        keys = ["GLDAS_A", "GLDAS_B", "HR_A", "HR_B"]
        lab = [("G" if k.startswith("GLDAS") else "H") + k[-1] + NL + pts[k]["nombre"].replace(" (", NL + "(") for k in keys]
        series = (("frac_exito_am", "retrieval con éxito (AM)", OI["sky"]),
                  ("frac_recomendado_am", "calidad recomendada (AM)", OI["blue"]),
                  ("frac_recomendado_pm", "calidad recomendada (PM)", OI["green"]),
                  ("bandera_vegetacion_densa_am", "bandera 'vegetación densa'", OI["vermillion"]),
                  ("bandera_urbano_am", "bandera 'zona urbana'", OI["orange"]))
        w = 0.15
        x = np.arange(len(keys))
        for s, (c, l, colr) in enumerate(series):
            ax.bar(x + (s - 2) * w, [pts[k][c] for k in keys], w, color=colr, label=l, edgecolor="none")
        ax.set_xticks(x)
        ax.set_xticklabels(lab, fontsize=5.8)
        ax.set_ylabel("fracción de días 2015-04 a 2024-12", fontsize=6.3)
        ax.set_ylim(0, 1.12)
        ax.legend(fontsize=5.6, ncol=3, frameon=False, loc="lower center", bbox_to_anchor=(0.5, 1.03))
        for xx, k in zip(x, keys):
            ax.text(xx - 0.5 * w, 0.06, f"{100 * pts[k]['frac_recomendado_am_pm']:.0f} %", ha="center", fontsize=5.6,
                    color=OI["blue"], fontweight="bold")
            ax.text(xx + 1.6 * w, 1.07, f"VWC {pts[k]['vwc_mediana_am']:.1f} kg/m²", ha="center", fontsize=5.6, color="#333333")
        ax.spines[["top", "right"]].set_visible(False)
        ax.text(-0.08, 1.04, "c", transform=ax.transAxes, fontsize=8, fontweight="bold", va="bottom")
        _note(fig, -0.02, "SMAP L3 Enhanced SPL3SMP_E V006 (NSIDC), píxeles EASE-2 de 9 km (huella real de banda L ~40 km). "
                 "G = celdas GLDAS 0.25° del par de demostración; H = celdas 0.05° del par de alta resolución. " + SRC,
                 fontsize=5.4, color="#444444", wrap=True)
        _save(fig, "t1_smap_l3_calidad")


# ------------------------------------------------------------------ T2: los pares con el testigo

def _rows_for_plot(lst):
    out = []
    for r in lst:
        if r.get("no_comprobable"):
            out.append({**r, "rel": np.nan})
            continue
        ea = r.get("e_A", r.get("gamma_A"))
        eb = r.get("e_B", r.get("gamma_B"))
        mean = (abs(ea) + abs(eb)) / 2
        ci = r.get("delta_ic95") or [np.nan, np.nan]
        out.append({**r, "rel": 100 * r["delta"] / mean, "lo": 100 * ci[0] / mean, "hi": 100 * ci[1] / mean})
    return out


def fig_pares():
    P = _j("pares_smap_l3.json")
    if P is None:
        return
    with plt.rc_context(RC):
        fig, axs = plt.subplots(2, 1, figsize=(180 * MM, 165 * MM), gridspec_kw={"hspace": 0.42})
        for ax, key, title, l in ((axs[0], "gldas", "Par GLDAS: Monseñor Nouel (A) vs Santiago/La Vega (B)", "a"),
                                  (axs[1], "hr", "Par 0.05°: Cordillera Central (A) vs La Vega (B)", "b")):
            lst = (P[key].get("gamma", []) + P[key]["eficiencia"])
            rows = _rows_for_plot(lst)
            y = np.arange(len(rows))[::-1]
            for yy, r in zip(y, rows):
                indep = r.get("independiente", "").startswith("sí (radiómetro)")
                sens = r.get("independiente", "").startswith("sí, pero")
                c = OI["blue"] if indep else (OI["sky"] if sens else GREY)
                if np.isfinite(r["rel"]):
                    if np.isfinite(r.get("lo", np.nan)):
                        ax.plot([r["lo"], r["hi"]], [yy, yy], color=c, lw=1.2)
                    ax.plot(r["rel"], yy, "o" if indep else ("s" if sens else "D"), color=c, ms=4,
                            mfc=c if indep else "white", mew=1)
                    pc = r.get("p_calibrado", r.get("p"))
                    if pc is not None and np.isfinite(pc):
                        ax.text(1.02, yy, f"p={pc:.2g}", transform=ax.get_yaxis_transform(), fontsize=5.3, va="center")
                else:
                    ax.text(0, yy, "no comprobable (pocos datos de calidad)", fontsize=5.6, va="center", ha="center",
                            color=OI["vermillion"])
            ax.axvline(0, color="k", lw=0.5)
            ax.set_yticks(y)
            ax.set_yticklabels([_short(r) for r in rows], fontsize=5.5)
            ax.set_xlabel("diferencia A − B, % de la respuesta media (IC 95 %)", fontsize=6.2)
            ax.spines[["top", "right"]].set_visible(False)
            ax.tick_params(labelsize=5.8)
            v = P["veredictos"][key]["veredicto"]
            _letter(ax, l, f"{title}  ·  veredicto con SMAP L3: {v}")
        _note(fig, -0.07, "Gris = modelo (no independiente); azul relleno = SMAP L3 con calidad recomendada (testigo "
                 "independiente); celeste vacío = SMAP L3 con todos los retrievals (sensibilidad). p = calibrado con "
                 "sustitutos de igual respuesta (σ de inflación) o, en filas originales, el p del informe.", fontsize=5.4,
                 color="#444444", wrap=True)
        _save(fig, "t2_pares_testigo_smap_l3")


def _short(r):
    m = r.get("metrica", "")
    met = "γ ARX" if m.startswith("gamma") else ("evento" if "evento" in m else "mensual")
    return f"{r['etiqueta'].replace(' (afirmación original)', ' [orig.]').replace(' (mismo periodo que SMAP)', '')} · {met}"


def fig_eventos():
    P = _j("pares_smap_l3.json")
    if P is None:
        return
    with plt.rc_context(RC):
        fig, axs = plt.subplots(1, 2, figsize=(180 * MM, 70 * MM), gridspec_kw={"wspace": 0.28})
        for ax, key, title, l in ((axs[0], "gldas", "Par GLDAS (celdas 0.25°)", "a"), (axs[1], "hr", "Par 0.05° (píxel 9 km)", "b")):
            ev = P[key].get("eventos_rec", {})
            fuera = not any(len(v["x"]) for v in ev.values())
            if fuera:                         # sin calidad recomendada: se muestra lo no recomendado, marcado
                ev = P[key].get("eventos_exito", {})
                ax.text(0.98, 0.97, NL.join(["SIN retrievals recomendados:", "se muestran los NO recomendados",
                                             "(fuera de especificación)"]),
                        transform=ax.transAxes, ha="right", va="top", fontsize=5.4, color=OI["vermillion"])
            for k, c in (("A", OI["vermillion"]), ("B", OI["blue"])):
                if k not in ev or not ev[k]["x"]:
                    continue
                x, y = np.array(ev[k]["x"]), np.array(ev[k]["y"])
                ax.scatter(x, y, s=2, color=c, alpha=0.25, lw=0, rasterized=True)
                bins = np.array([0, 1, 3, 6, 10, 20, 40, 80, 200])
                mid, med = [], []
                for a, b in zip(bins[:-1], bins[1:]):
                    s = (x >= a) & (x < b)
                    if s.sum() >= 8:
                        mid.append(np.median(x[s]))
                        med.append(np.median(y[s]))
                ax.plot(mid, med, "-o", color=c, ms=3, lw=1.2, label=f"{k} (n={x.size})")
            ax.axhline(0, color="k", lw=0.4)
            ax.set_xscale("symlog", linthresh=1)
            ax.set_xlim(-0.2, 300)
            ax.set_xticks([0, 1, 10, 100])
            ax.set_xticklabels(["0", "1", "10", "100"])
            ax.set_xlabel("lluvia IMERG entre dos pasos de SMAP (mm)", fontsize=6.3)
            ax.set_ylabel("cambio de humedad superficial (m³/m³)", fontsize=6.3)
            ax.set_ylim(-0.15, 0.25)
            ax.legend(fontsize=5.8, frameon=False, loc="upper left")
            ax.spines[["top", "right"]].set_visible(False)
            _letter(ax, l, title)
        _note(fig, -0.06, "Puntos: pares de pasos consecutivos (≤ 72 h); línea: mediana por "
                 "tramo de lluvia. SMAP L3 SPL3SMP_E V006 · IMERG Final V07 diario.", fontsize=5.4, color="#444444")
        _save(fig, "t3_eventos_lluvia_smap_l3")


# ------------------------------------------------------------------ T4: memoria de lluvia vs suelo

def fig_memoria():
    p = RES / "memoria_lluvia_vs_suelo.csv"
    if not p.exists():
        return
    df = pd.read_csv(p)
    for c in [c for c in df.columns if c.endswith("_ic95")]:
        df[c] = df[c].map(json.loads)
    d = df[df["resultado"] == "z_retorno_SM_RAIZ"]
    orig = _j("memoria_lluvia_vs_suelo.json")["reproduccion_original"]["z_retorno_SM_RAIZ"]
    specs = list(dict.fromkeys(d["lluvia_antecedente"]))
    specs = [x for x in specs if "forzante" not in x] + [x for x in specs if "forzante" in x]
    nfz = sum("forzante" in x for x in specs)
    with plt.rc_context(RC):
        fig, axs = plt.subplots(1, 2, figsize=(180 * MM, 100 * MM), gridspec_kw={"wspace": 0.12, "width_ratios": [1.3, 1]},
                                sharey=True)
        y = np.arange(len(specs))[::-1]
        for fe, off, mk in (("mes + provincia + terreno", 0.17, "o"), ("mes + celda", -0.17, "s")):
            s = d[d["efectos_fijos"] == fe].set_index("lluvia_antecedente").reindex(specs)
            for col, colr, lab in (("beta_suelo_M2", GREY, "suelo solo (sin lluvia)"), ("beta_suelo_M3", OI["blue"], "suelo con lluvia antecedente"),
                                   ("beta_lluvia_M3", OI["orange"], "lluvia antecedente con suelo")):
                ci = np.array(s[f"{col}_ic95"].tolist())
                yy = y + off + {"beta_suelo_M2": 0.08, "beta_suelo_M3": 0, "beta_lluvia_M3": -0.08}[col]
                axs[0].errorbar(s[col], yy, xerr=[s[col] - ci[:, 0], ci[:, 1] - s[col]], fmt=mk, color=colr, ms=2.6,
                                lw=0.7, capsize=0, label=f"{lab} · EF {fe}")
        for a_ in axs:
            a_.axhspan(-0.5, nfz - 0.5, color="#EDEDED", zorder=0, lw=0)
        axs[0].axvline(0, color="k", lw=0.5)
        axs[0].axvline(orig["beta_suelo_M2"], color=OI["vermillion"], lw=0.8, ls="--")
        axs[0].text(orig["beta_suelo_M2"] - 0.01, len(specs) - 0.4, f"afirmación original β={orig['beta_suelo_M2']:.2f}",
                    color=OI["vermillion"], fontsize=5.4, va="bottom", ha="right")
        axs[0].set_yticks(y)
        axs[0].set_yticklabels(specs, fontsize=5.5)
        axs[0].set_xlabel("β estandarizado sobre z de la raíz al volver la lluvia (IC 95 %)", fontsize=6.2)
        axs[0].legend(fontsize=4.9, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2)
        axs[0].spines[["top", "right"]].set_visible(False)
        _letter(axs[0], "a", "¿Sobrevive el suelo antecedente a la lluvia antecedente?")
        s = d[d["efectos_fijos"] == "mes + provincia + terreno"].set_index("lluvia_antecedente").reindex(specs)
        h = 0.36
        for col, colr, lab, off in (("r2p_suelo_dado_lluvia", OI["blue"], "R² parcial del suelo | lluvia", h / 2),
                                    ("r2p_lluvia_dado_suelo", OI["orange"], "R² parcial de la lluvia | suelo", -h / 2)):
            ci = np.array(s[f"{col}_ic95"].tolist())
            axs[1].barh(y + off, s[col], h, color=colr, label=lab)
            axs[1].errorbar(s[col], y + off, xerr=[np.clip(s[col] - ci[:, 0], 0, None), ci[:, 1] - s[col]], fmt="none",
                            ecolor="k", lw=0.5)
        axs[1].plot(s["varianza_comun"], y, "k|", ms=6, label="varianza común (suelo ∩ lluvia)")
        axs[1].set_xlabel("fracción de varianza (EF mes + provincia + terreno)", fontsize=6.2)
        axs[1].legend(fontsize=5.2, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.12))
        axs[1].spines[["top", "right"]].set_visible(False)
        _letter(axs[1], "b", "¿Quién explica qué?")
        _note(fig, -0.2, "Episodios de sequía del motor nacional (GLDAS 0.25°, 2001-2024). Lluvia antecedente = API "
                 "(IMERG diario, o lluvia del forzante de GLDAS) el último día del mes anterior al inicio, en z por mes "
                 "calendario. Fondo gris: lluvia del PROPIO modelo (forzante GPCP de GLDAS). IC por bootstrap de conglomerados de año.", fontsize=5.4, color="#444444", wrap=True)
        _save(fig, "t4_memoria_lluvia_vs_suelo")


# ------------------------------------------------------------------ T5: umbral

def fig_umbral():
    U = _j("umbral_testigos.json")
    if U is None:
        return
    V = U["variantes"]
    names = list(V)
    pal = [GREY, "#666666", OI["orange"], OI["blue"], OI["green"], OI["sky"], OI["purple"]]
    nc = 3
    nr = int(np.ceil(len(names) / nc))
    with plt.rc_context(RC):
        fig, axs = plt.subplots(nr, nc, figsize=(180 * MM, 62 * MM * nr), gridspec_kw={"wspace": 0.42, "hspace": 0.9})
        axs = np.atleast_2d(axs).ravel()
        for k, n in enumerate(names):
            ax = axs[k]
            v = V[n]
            short = n.replace("todos los retrievals, fuera de especificación", "NO recomendados").replace(" · reconstrucción", " (reconstruido)")
            ax.set_title("abcdefghijkl"[k] + "  " + short.replace(" · ", NL), fontsize=5.4, loc="left")
            ax.spines[["top", "right"]].set_visible(False)
            ax.tick_params(labelsize=5.5)
            if v.get("no_comprobable"):
                ax.text(0.5, 0.5, "no comprobable" + NL + v["motivo"], transform=ax.transAxes, ha="center", va="center",
                        fontsize=5.6, color=OI["vermillion"], wrap=True)
                ax.set_xticks([])
                ax.set_yticks([])
                continue
            f = np.array(v["f"])
            lo, hi = v["f_q05_q95"]
            s_ = (f >= lo) & (f <= hi)
            c = pal[k % len(pal)]
            ax.fill_between(f[s_], np.array(v["ef_lo"])[s_], np.array(v["ef_hi"])[s_], color=c, alpha=0.25, lw=0)
            ax.plot(f[s_], np.array(v["ef"])[s_], color=c, lw=1.3)
            ax.axvline(v["theta"], color="k", lw=0.6, ls="--")
            ax.axvspan(*v["theta_ic95"], color="k", alpha=0.07, lw=0)
            txt = NL.join([f"n={v['n_celdas']} celdas",
                           f"θ={v['theta']:.2f} [{v['theta_ic95'][0]:.2f}–{v['theta_ic95'][1]:.2f}]",
                           f"b5 [{v['b5_ic95'][0]:.2g}, {v['b5_ic95'][1]:.2g}]",
                           f"quiebre: {'sí' if v['b5_excluye_0'] else 'no'}"])
            ax.text(0.03, 0.03, txt,
                    transform=ax.transAxes, fontsize=5.0, va="bottom",
                    bbox={"facecolor": "white", "alpha": 0.75, "edgecolor": "none", "pad": 1})
            ax.set_xlabel("llenado antecedente f", fontsize=5.8)
            if k % nc == 0:
                ax.set_ylabel("eficiencia", fontsize=6)
        for ax in axs[len(names):]:
            ax.set_visible(False)
        _note(fig, -0.03 / nr, "Regresión segmentada agrupada (EF celda × mes); banda = IC 95 % por bootstrap de bloques de "
                 "12 meses compartidos por todas las celdas. Eficiencia en mm/mm (TerraClimate) o m³/m³ por mm (SMAP): "
                 "comparar la FORMA, no el nivel.", fontsize=5.4, color="#444444", wrap=True)
        _save(fig, "t5_umbral_testigos")


# ------------------------------------------------------------------ T6: bosque (Hansen)

def fig_bosque():
    B = _j("bosque_hansen.json")
    if B is None:
        return
    z = np.load(RES / "bosque_mapa.npz")
    polys = _adm1()
    zonas = B["zonas"]
    with plt.rc_context(RC):
        fig = plt.figure(figsize=(180 * MM, 82 * MM))
        gs = fig.add_gridspec(1, 2, width_ratios=[1.05, 1], wspace=0.35)
        ax = fig.add_subplot(gs[0])
        la, lo = z["lat"], z["lon"]
        ax.pcolormesh(_edges(lo), _edges(la[::-1])[::-1] if la[0] > la[-1] else _edges(la), z["cobertura"],
                      cmap="Greens", vmin=0, vmax=100, shading="flat", rasterized=True, alpha=0.55)
        L = np.ma.masked_less(z["perdida"], 0.02)
        m = ax.pcolormesh(_edges(lo), _edges(la[::-1])[::-1] if la[0] > la[-1] else _edges(la), L, cmap="magma_r",
                          vmin=0, vmax=0.5, shading="flat", rasterized=True)
        _borders(ax, polys, lw=0.4)
        _sites(ax)
        y = YUNA_ALTO
        ax.add_patch(Rectangle((y["lon0"], y["lat0"]), y["lon1"] - y["lon0"], y["lat1"] - y["lat0"], fill=False,
                               ec=OI["green"], lw=1.0, ls="--", zorder=6))
        ax.text(y["lon0"] + 0.01, y["lat0"] + 0.015, "Yuna alto", color=OI["green"], fontsize=5.8, zorder=7,
                fontweight="bold")
        _frame(ax, (-71.25, -70.05, 18.55, 19.65))
        cb = fig.colorbar(m, ax=ax, orientation="horizontal", fraction=0.05, pad=0.09)
        cb.set_label("fracción del píxel de ~300 m con pérdida 2001-2023 (fondo verde: cobertura 2000)", fontsize=5.6)
        cb.ax.tick_params(labelsize=5.5)
        _letter(ax, "a", "Pérdida de cobertura arbórea (Hansen GFC v1.13)")
        ax = fig.add_subplot(gs[1])
        sel = [k for k in zonas if not k.startswith("9 km")]
        yrs = np.arange(2001, 2024)
        colors = [OI["vermillion"], OI["blue"], OI["orange"], OI["sky"], OI["green"]]
        for k, c in zip(sel, colors):
            s = np.array([zonas[k]["perdida_por_anio_km2"][str(yy)] for yy in yrs])
            f0 = zonas[k]["bosque_2000_km2"]
            ax.plot(yrs, 100 * np.cumsum(s) / f0 if f0 > 0 else np.nan * yrs, color=c, lw=1.2,
                    label=f"{k.split(' (celda')[0].split(' (caja')[0].replace('0.05° ', 'H').replace('GLDAS ', 'G')} "
                          f"({zonas[k]['perdida_pct_del_bosque_2000']:.1f} %)")
        ax.set_ylabel("pérdida acumulada, % del bosque de 2000", fontsize=6.2)
        ax.legend(fontsize=5.3, frameon=False, loc="center left", bbox_to_anchor=(0.03, 0.6))
        ax.spines[["top", "right"]].set_visible(False)
        ax.tick_params(labelsize=5.8)
        _letter(ax, "b", "Acumulado por zona (descriptivo, sin causa)")
        _note(fig, -0.05, "Hansen et al. (2013) Science 342:850, Global Forest Change 2000-2025 v1.13, tesela 20N_080W; "
                 "bosque = cobertura 2000 ≥ 30 %. " + SRC, fontsize=5.4, color="#444444")
        _save(fig, "t6_bosque_hansen")


# ------------------------------------------------------------------ T7: intensidad

def fig_intensidad():
    J = _j("intensidad_chirps.json")
    if J is None or J.get("estado") != "ok":
        return
    df = pd.DataFrame(J["tabla"])
    df = df[df["beta"].notna()]
    with plt.rc_context(RC):
        fig, axs = plt.subplots(1, 3, figsize=(180 * MM, 62 * MM), sharey=True, gridspec_kw={"wspace": 0.1})
        order = list(dict.fromkeys(df["fuente"] + " · " + df["factor"]))
        y = np.arange(len(order))[::-1]
        for ax, oc in zip(axs, ["z_retorno_SM_RAIZ", "z_retorno_SM_0_10", "contradiccion_A_SM_RAIZ"]):
            s = df[df["resultado"] == oc].assign(k=lambda t: t["fuente"] + " · " + t["factor"]).set_index("k").reindex(order)
            ci = np.array([v if isinstance(v, list) else [np.nan, np.nan] for v in s["ic95"]])
            c = [OI["blue"] if "CHIRPS" in k else GREY for k in order]
            for yy, b, lo_, hi_, cc in zip(y, s["beta"], ci[:, 0], ci[:, 1], c):
                ax.plot([lo_, hi_], [yy, yy], color=cc, lw=1)
                ax.plot(b, yy, "o", color=cc, ms=3)
            ax.axvline(0, color="k", lw=0.5)
            ax.set_title(oc, fontsize=6)
            ax.spines[["top", "right"]].set_visible(False)
            ax.tick_params(labelsize=5.5)
        axs[0].set_yticks(y)
        axs[0].set_yticklabels(order, fontsize=5.3)
        axs[1].set_xlabel("β estandarizado (control por severidad), IC 95 % por conglomerados de año", fontsize=6)
        yrs = J["anios_chirps_usados"]
        _note(fig, -0.1, f"CHIRPS v2.0 diario: {len(yrs)} años completos y verificados en la caché del motor de tendencias "
              f"({', '.join(map(str, yrs))}); IMERG recalculado en los mismos episodios. CHIRPS diario reparte la péntada "
              "con un modelo: la fila 'péntada' es la escala anclada a estaciones.")
        _save(fig, "t7_intensidad_chirps")


def all_figures():
    for f in (fig_calidad, fig_pares, fig_eventos, fig_memoria, fig_umbral, fig_bosque, fig_intensidad):
        try:
            f()
            print(f"  figura {f.__name__} lista", flush=True)
        except FileNotFoundError as e:
            print(f"  figura {f.__name__} omitida: {e}", flush=True)
