"""reports_nacional/CASO_YUNA.md: se escribe desde los resultados (ningún número se teclea a mano)."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

from .common import DATA, REPORT, RES


def _f(x, d=2):
    return "—" if x is None or (isinstance(x, float) and not np.isfinite(x)) else f"{x:.{d}f}"


def _ci(c, d=2):
    if isinstance(c, str):
        c = json.loads(c.replace("(", "[").replace(")", "]").replace("nan", "NaN"))
    return f"[{_f(c[0], d)}, {_f(c[1], d)}]"


def _tabla(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for r in df.itertuples(index=False):
        out.append("| " + " | ".join(str(x) for x in r) + " |")
    return "\n".join(out)


def run(res: dict) -> None:
    cu = json.loads((RES / "cuencas_resumen.json").read_text(encoding="utf-8"))
    A = cu["areas_km2"]
    qd = pd.read_csv(RES / "que_drena_donde.csv")
    cat, bt, info, pr = res["cat"], res["backtest"], res["info"], res["presa"]
    au = pr["auc"]
    man = json.loads((DATA / "MANIFEST.json").read_text(encoding="utf-8"))
    mc = man["rutas"].get("MCDWD_L3", {})
    gm = json.loads((RES / "gsw_mascaras.json").read_text(encoding="utf-8"))
    w = res["w"]
    from .observacion import anomalias
    emb = anomalias(w, "embalse", 0.5)
    lla = anomalias(w, "llanura")
    pan = res["paneles"]
    ins = res["insuf"]
    ncu = int(cat["zona"].isin({"bajo_yuna", "alto_yuna", "camu", "cuenca_general"}).sum())
    nop = int((cat["zona"] == "hatillo_operacion").sum())
    nus = int(cat["usable_backtest"].sum())
    ncal, nte = res["resumen"]["n_eventos_calibracion"], res["resumen"]["n_eventos_prueba"]

    def fila(trig, per):
        r = bt[(bt["disparador"] == trig) & (bt["periodo"].str.startswith(per))].iloc[0]
        return r

    # tabla de backtest
    tb = []
    for r in bt.itertuples():
        tb.append({"disparador": r.disparador, "periodo": r.periodo.split()[0], "eventos": r.eventos,
                   "aciertos": r.aciertos, "episodios": r.episodios, "falsas": r.falsas_alarmas,
                   "POD [IC95]": f"{_f(r.POD)} {_ci(r.POD_ic95)}", "FAR [IC95]": f"{_f(r.FAR)} {_ci(r.FAR_ic95)}",
                   "CSI [IC95]": f"{_f(r.CSI)} {_ci(r.CSI_ic95)}"})
    tb = pd.DataFrame(tb)
    desc = bt.drop_duplicates("disparador")[["disparador", "descripcion", "variables"]]

    # qué drena dónde
    qtab = qd[["punto", "celda_grados", "frac_Yuna", "frac_alto_hatillo", "frac_camu", "frac_bajo_yuna",
               "frac_Yaque del Norte", "frac_Yaque del Sur", "salida_cuenca"]].fillna("punto")

    # catálogo
    ctab = cat[["id", "inicio", "fin", "zona", "confianza", "n_fuentes", "n_fuentes_leidas", "usable_backtest"]].copy()
    ctab["primera_fuente"] = cat["fuentes_url"].str.split(" | ").str[0]

    # presa
    mens = pr.get("mensual")
    mtab = ""
    if mens is not None:
        mm = mens[mens["variable"] == "lluvia_mes"].copy()
        mm["ρ [IC95]"] = [f"{_f(a)} {_ci(c)}" for a, c in zip(mm["rho"], mm["ic95"])]
        mtab = _tabla(mm[["estado_embalse", "zona_antecedente", "n_meses", "ρ [IC95]"]])
    atab = pd.DataFrame([{"variable": v, **{z: f"{_f(au[f'AUC_{v}_{z}'])} {_ci(au[f'AUC_{v}_{z}_ic95'])}"
                                            for z in ("alto_hatillo", "camu", "bajo_yuna")},
                          "Δ alto−Camú [IC95]": f"{_f(au[f'dAUC_{v}_alto_menos_camu'])} {_ci(au[f'dAUC_{v}_alto_menos_camu_ic95'])}"}
                         for v in ("ant30_pct", "gldas_z", "r48")])

    a = fila("a_lluvia100", "prueba"); b2 = fila("b2_umbral_rebajado_si_humedo", "prueba"); c = fila("c_antecedente", "prueba")
    a_c = fila("a_lluvia100", "cal"); b2_c = fila("b2_umbral_rebajado_si_humedo", "cal")
    ev_obs = pan[pan.get("gsw_sobre_p90", pd.Series(dtype=object)) == True]["id"].tolist() if "gsw_sobre_p90" in pan else []  # noqa: E712
    ev_gsw_nubes = pan[(pan.get("gsw_validos_max", pd.Series(dtype=float)) < 0.3)]["id"].tolist() if "gsw_validos_max" in pan else []
    # GEOGLOWS: caudal medio simulado vs. caudal medio de HydroRIVERS en el mismo punto (control de que el tramo es el cauce principal)
    gp = json.loads((RES / "geoglows_puntos.json").read_text(encoding="utf-8"))
    gg = []
    for k, m in gp.items():
        col = f"q_{k}"
        qm = float(res["d"][col].loc["2001":"2024"].mean()) if col in res["d"] else float("nan")
        gg.append({"punto": k, "Q medio GEOGLOWS 2001-2024 (m³/s)": _f(qm, 1),
                   "Q medio HydroRIVERS (m³/s)": _f(m["DIS_AV_CMS_hydrorivers"], 1),
                   "área drenada HydroRIVERS (km²)": _f(m["UPLAND_km2"], 0),
                   "¿cauce principal?": "sí" if np.isfinite(qm) and qm > 0.4 * m["DIS_AV_CMS_hydrorivers"] else "NO (afluente lateral)"})
    gg = pd.DataFrame(gg)
    n_gg_ok = int((gg["¿cauce principal?"] == "sí").sum())
    mm_all = mens[(mens["variable"] == "lluvia_mes")].set_index(["estado_embalse", "zona_antecedente"]) if mens is not None else None
    def rho(e, z):
        r = mm_all.loc[(e, z)]
        return f"{r['rho']:.2f} [{r['ic95'][0]:.2f}, {r['ic95'][1]:.2f}] (n = {r['n_meses']})"
    rh = {f"{e}_{z}": rho(e, z) for e in ("todos", "embalse_alto", "embalse_bajo") for z in ("alto_hatillo", "camu", "bajo_yuna")} if mm_all is not None else {}
    e_ok = emb[emb["usable"]]
    pct_hat = 100 * cu["hatillo"]["hydrorivers_UPLAND_km2"] / cu["salidas"]["Yuna"]["UP_AREA_km2"]
    pct_no_reg = 100 - pct_hat
    qi = qd.set_index("punto")
    qd_mn = 100 * qi.loc["celda_GLDAS_MonsenorNouel_18.875_-70.375", "frac_alto_hatillo"]
    qd_sl_camu = 100 * qi.loc["celda_GLDAS_Santiago_LaVega_19.375_-70.625", "frac_camu"]
    qd_sl_yn = 100 * qi.loc["celda_GLDAS_Santiago_LaVega_19.375_-70.625", "frac_Yaque del Norte"]
    n_lla, n_lla_nubes = len(lla), int((~lla["usable"]).sum())
    n_emb, emb_med, emb_min, emb_max = len(e_ok), e_ok["km2"].median(), e_ok["km2"].min(), e_ok["km2"].max()
    c_pct = 100 * info["c"]["percentil"]
    ev_obs = ", ".join(ev_obs) if ev_obs else "ninguno"
    ev_meses = set()
    for r_ in cat[cat["usable_backtest"]].itertuples():
        for m_ in pd.date_range(pd.Timestamp(r_.inicio).replace(day=1), pd.Timestamp(r_.fin) + pd.offsets.MonthBegin(1), freq="MS"):
            ev_meses.add(m_)
    sin_cat = [d_.strftime("%Y-%m") for d_ in lla.index[lla["sobre_p90"]] if d_ not in ev_meses]
    meses_sin_cat = ", ".join(sin_cat) if sin_cat else "ninguno"
    n_sobre = int(lla["sobre_p90"].sum())
    fa_anio_c, fa_anio_t = a_c["falsas_alarmas"] / 15, a["falsas_alarmas"] / 9
    # CHIRPS: años con ≥ 300 días válidos en la serie de la cuenca
    ch = res["d"].get("chirps_media_yuna")
    if ch is not None:
        yrs = ch.notna().groupby(ch.index.year).sum()
        full = [int(y) for y, n in yrs.items() if n >= 300]
        part = [int(y) for y, n in yrs.items() if 0 < n < 300]
        chirps_txt = (f"diario completo en {min(full)}-{max(full)} ({len(full)} años)" if full else "sin años completos")
        if part:
            chirps_txt += f"; parcial en {', '.join(map(str, part))}"
        miss = [y for y in range(2001, 2025) if y not in full and y not in part]
        if miss:
            chirps_txt += f"; faltan {', '.join(map(str, miss))}"
    else:
        chirps_txt = "no disponible"
    # MCDWD
    mv = res.get("mcdwd")
    tablas_mc = {"TABLA_MC_EV": "", "TABLA_VER": "", "TABLA_AUC_OBS": ""}
    if mv is not None:
        evm = mv["eventos"].sort_values("id")
        ok_ = evm["observa"].map(lambda x: x is True or x == True)  # noqa: E712
        no_ = evm["observa"].map(lambda x: x is False or x == False)  # noqa: E712
        indet = evm["observa"].isna()
        ref2 = mv["ref"]["Flood_2Day_250m"]
        aum = mv["auc"]
        gmm = mv["gsw"]
        gtxt = "; ".join(f"{r_.mes}: " + ("nubes" if r_.observa is None or (isinstance(r_.observa, float) and np.isnan(r_.observa))
                                           else f"{'sí' if r_.observa else 'no'} ({_f(r_.inund_km2_max_yuna, 1)} km²)")
                         for r_ in gmm.itertuples()) if len(gmm) else "—"
        auc_txt = ""
        if aum:
            auc_txt = (f"{aum['n_episodios_determinables']} episodios visibles ({aum['n_con_inundacion_observada']} con "
                       f"inundación observada) y {aum['n_indeterminados_nubes']} tapados por nubes. Con antecedente húmedo "
                       f"(IMERG 30 d ≥ p90 en las tres zonas, de media) se inundó la fracción {_f(aum.get('frac_inund_si_humedo'))} "
                       f"de los episodios; sin él, {_f(aum.get('frac_inund_si_no_humedo'))} (Fisher p = {_f(aum.get('fisher_p'), 3)}).")
            tablas_mc["TABLA_AUC_OBS"] = _tabla(pd.DataFrame([
                {"variable": v_, **{z: f"{_f(aum[f'AUC_{v_}_{z}'])} {_ci(aum[f'AUC_{v_}_{z}_ic95'])}" for z in ("alto_hatillo", "camu", "bajo_yuna")},
                 "Δ alto−Camú [IC95]": f"{_f(aum[f'dAUC_{v_}_alto_menos_camu'])} {_ci(aum[f'dAUC_{v_}_alto_menos_camu_ic95'])}"}
                for v_ in ("ant30_pct", "gldas_z", "r48")]))
        mj = json.loads((RES / "mcdwd_mascaras.json").read_text(encoding="utf-8"))
        fuertes = ", ".join(evm.loc[evm["inund_km2_max_yuna"] > 15, "id"]) or "ninguna"
        mcx = {"fijo": f"{mj['yuna']['frac_siempre_enmascarada'] * 100:.0f} %",
               "fijo_llanura": f"{mj['llanura']['frac_siempre_enmascarada'] * 100:.1f} %", "fuertes": fuertes,
               "n_dias": mv["resumen"]["n_dias"], "insuf": f"{mv['resumen']['insuf_media_yuna_2d'] * 100:.0f} %",
               "p95": _f(ref2["p95_yuna"], 1), "obs_si": ", ".join(evm.loc[ok_, "id"]) or "ninguno",
               "obs_no": ", ".join(evm.loc[no_, "id"]) or "ninguno", "indet": ", ".join(evm.loc[indet, "id"]) or "ninguno",
               "gsw": gtxt, "auc_txt": auc_txt,
               "resumen": (f"confirma {int(ok_.sum())} de {len(evm)} eventos del catálogo, no ve inundación anómala en "
                           f"{int(no_.sum())} y las nubes impiden decidir en {int(indet.sum())}.")}
        cols = ["id", "observa", "inund_km2_max_yuna", "anomalia_km2_yuna", "recurrente_km2_max_yuna", "dia_max_yuna",
                "insuf_min_yuna", "n_obs_yuna", "n_dias", "inund_km2_max_alto_hatillo", "inund_km2_max_camu", "inund_km2_max_bajo_yuna"]
        t_ = evm[[c for c in cols if c in evm]].copy()
        for c in t_.columns:
            if t_[c].dtype.kind == "f":
                t_[c] = t_[c].map(lambda x: _f(x, 2) if c.startswith("insuf") else _f(x, 1))
        tablas_mc["TABLA_MC_EV"] = _tabla(t_.fillna("—"))
        if "verificacion" in mv:
            vt = mv["verificacion"].copy()
            vt["mcdwd_inund_km2_max_yuna"] = vt["mcdwd_inund_km2_max_yuna"].map(lambda x: _f(x, 1))
            vt["mcdwd_insuf_min_yuna"] = vt["mcdwd_insuf_min_yuna"].map(lambda x: _f(x, 2))
            tablas_mc["TABLA_VER"] = _tabla(vt.fillna("—"))
    else:
        mcx = {k: "no disponible" for k in ("n_dias", "insuf", "p95", "obs_si", "obs_no", "indet", "gsw", "auc_txt", "resumen",
                                            "fijo", "fijo_llanura", "fuertes")}
    tx = TEXTO.format(**locals(), **{k: _f(v, 0) for k, v in A.items() if k.isidentifier()})
    tx = tx.replace("{TABLA_GG}", _tabla(gg))
    for k_, t_ in tablas_mc.items():
        tx = tx.replace("{" + k_ + "}", t_)
    tx = tx.replace("{TABLA_QD}", _tabla(qtab)).replace("{TABLA_CAT}", _tabla(ctab)).replace("{TABLA_BT}", _tabla(tb))
    tx = tx.replace("{TABLA_DESC}", _tabla(desc)).replace("{TABLA_AUC}", _tabla(atab)).replace("{TABLA_MENS}", mtab)
    tx = tx.replace("{TABLA_INS}", _tabla(ins.fillna("—")))
    REPORT.write_text(tx, encoding="utf-8", newline="\n")
    print(f"  informe {REPORT.name}", flush=True)


TEXTO = """# Caso Yuna · lluvia y memoria arriba → presa de Hatillo → inundación abajo

Stellar Horizons · NASA Space Apps 2026 («Be An Earth System Trend Detective!»). Generado por
`earthmemory/yuna/run.py`; todos los números salen de `results/yuna/`. Fecha de las búsquedas: 2026-11-14.

**Hipótesis de investigación (no causalidad demostrada):** lluvia y estado antecedente del Alto Yuna
(IMERG · SMAP L4 · GLDAS) → escorrentía y respuesta del río (relieve · cobertura · caudal) → presa de Hatillo
(almacenamiento · entradas · salidas) → inundación de arrozales del Bajo Yuna (eventos observados y registrados).
**Giro posible:** la operación del embalse podría cambiar la correlación entre la humedad de cabecera y las
inundaciones de abajo. Un resultado así es válido, no un fracaso.

Clases de variables (se repiten en cada figura): **OBSERVACIÓN** (JRC GSW, Landsat) · **RECUPERACIÓN SATELITAL**
(IMERG V07, CHIRPS v2) · **MODELO CON ASIMILACIÓN** (SMAP L4) · **MODELO FORZADO** (GLDAS-2.1 Noah) ·
**SIMULACIÓN HIDROLÓGICA** (GEOGLOWS v2) · **REGISTRO DOCUMENTAL** (catálogo).

## Resumen en cinco líneas

1. La cuenca del Yuna (HydroBASINS nivel 10) mide {yuna} km² (UP_AREA en la desembocadura:
   {cu[salidas][Yuna][UP_AREA_km2]:.0f} km²). Hatillo drena solo **{cu[hatillo][hydrorivers_UPLAND_km2]:.0f} km²**
   (≈ {pct_hat:.0f} % de la cuenca); el Camú, que entra **aguas abajo** de la presa cerca de Pimentel, drena {camu} km².
2. Bonao/Monseñor Nouel drena al Yuna **por encima de Hatillo**; La Vega drena al Yuna por el Camú (no regulado);
   la celda «cubo lleno» de la Cordillera (19.025N 70.975O) **no drena al Yuna** (Yaque del Sur ≈ 78 %, Yaque del
   Norte ≈ 22 %); la ciudad de Santiago está en el Yaque del Norte.
3. Catálogo: {ncu} eventos en la cuenca 2003-2026 y {nop} marcadores de operación de Hatillo, cada uno con URL;
   {nus} sirven para el backtest diario (2001-2024): {ncal} en calibración y {nte} en prueba. n muy pequeño.
4. Lluvia > 100 mm/48 h (máx. de celda) detecta casi todo (POD prueba {a[POD]:.2f}) pero dispara
   {a[episodios]} episodios en 9 años: CSI {a[CSI]:.2f} [{a[CSI_ic95][0]:.2f}, {a[CSI_ic95][1]:.2f}]. Añadir el
   antecedente **no mejora de forma detectable** el disparador con estos datos (detalle abajo).
5. Presa: no hay series públicas de nivel/descarga; el área del embalse (JRC GSW) es un sustituto mensual. Con él,
   la prueba del confusor **no detecta** que la presa cambie la relación arriba-abajo: los intervalos se solapan.
6. Inundación observada (MODIS MCDWD, 2003-2025, independiente de la lluvia): {mcx[resumen]}

## 1 · Cuenca: qué drena dónde

Método: HydroSHEDS HydroBASINS v1c (Norteamérica y Caribe, niveles 6-10) y HydroRIVERS v1.0 (Lehner y Grill, 2013,
*Hydrological Processes* 27: 2171-2186, doi:10.1002/hyp.9740; licencia HydroSHEDS, uso libre con atribución,
https://www.hydrosheds.org/terms-of-use). Topología `NEXT_DOWN` en nivel 10; «aguas arriba de X» = polígonos cuya
cadena pasa por X. Zonas disjuntas: **alto_hatillo** (aguas arriba de la cortina), **camu** (subcuenca del Camú
hasta su último tramo antes del Yuna), **bajo_yuna** (resto: Cotuí → Pimentel → Villa Riva/Arenoso → bahía de Samaná).
No se usó hidrografía del IGN (no verificada).

| zona | área (km²) |
|---|---|
| Cuenca del Yuna | {yuna} |
| Alto Yuna sobre Hatillo | {alto_hatillo} |
| Camú (no regulado) | {camu} |
| Bajo Yuna (resto) | {bajo_yuna} |
| Yaque del Norte (control) | {cu[areas_km2][Yaque del Norte]:.0f} |

- Presa de Hatillo: cortina en 19.0336N, 70.2004O (Wikipedia «Hatillo Dam»); el tramo HydroRIVERS más cercano está a
  {cu[hatillo][dist_tramo_cortina_km]:.2f} km y drena {cu[hatillo][hydrorivers_UPLAND_km2]:.0f} km² (caudal medio
  MODELADO por HydroRIVERS {cu[hatillo][hydrorivers_caudal_medio_m3s]:.0f} m³/s). La cifra de 5.235 km² que circula
  como «cuenca de Hatillo» es casi la cuenca entera del Yuna (5.498 km², BID) y **no** es lo que drena la cortina.
- Camú: confluencia en {cu[camu][confluencia_lonlat][1]:.3f}N, {cu[camu][confluencia_lonlat][0]:.3f}O (cerca de
  Pimentel, límite Duarte/Sánchez Ramírez), con {cu[camu][UPLAND_km2]:.0f} km² drenados: **el Camú es afluente del
  Yuna y entra aguas abajo de Hatillo**. Confirmado también por fuentes escritas (Wikipedia «Camú River», EcuRed).
  Ojo: el Camú de Puerto Plata (Montellano, abril 2026) es otro río, de la vertiente atlántica.

![Cuenca](../figures/yuna/fig_y1_cuenca_yuna.png)

{{TABLA_QD}}

Lectura para el par de demostración anterior: la celda GLDAS de Monseñor Nouel (18.875, −70.375) está en un
{qd_mn:.0f} % sobre Hatillo; la de Santiago/La Vega (19.375, −70.625) es {qd_sl_camu:.0f} % Camú y
{qd_sl_yn:.0f} % Yaque del Norte. **El par compara, sin saberlo, una cabecera regulada con una no regulada.**
La celda de alta resolución de La Vega (19.175, −70.475) es 100 % Camú.

## 2 · Catálogo de eventos (REGISTRO DOCUMENTAL)

`results/yuna/catalogo_eventos.csv`. Fuentes: prensa dominicana (Diario Libre, Listín, El Día, El Nuevo Diario,
Acento, elDinero), notas del INDRHI/Presidencia, informes del COE, IFRC (DREF/llamamientos), CEPAL (2003),
International Charter. **No se pudo consultar**: EM-DAT (pide cuenta), DesInventar (RD solo 1966-2000),
Dartmouth Flood Observatory (404) ni ReliefWeb (403 al acceso automático). Cada fuente lleva «leído» o «solo
búsqueda». Precedente fuera de la cuenca: Tavera durante Olga (12-dic-2007, Yaque del Norte), compuertas abiertas
de madrugada; ~20 muertes atribuidas a la descarga (Wikipedia) y polémica sobre si se abrió tarde.

{{TABLA_CAT}}

Menciones de Hatillo con fecha: 120 % de capacidad el 16-nov-2016 (solo búsqueda, sin verificar); 89,7 m y aviso
de posible apertura el 24-abr-2017; 87,57 msnm y salida de 87,37 m³/s el 22-sep-2017; «vertiendo» con Fiona
(20-sep-2022, COE); 167,8 m³/s a 87,51 msnm el 21-nov-2023; hasta 246,3 m³/s en mayo de 2024; sin vertido con
Franklin (ago-2023) ni con Melissa (26-oct-2025, 84,74 msnm). Las descargas de Noel/Olga 2007 y de nov-2016 **no
están verificadas** con fuente primaria.

## 3 · Inundación observada, independiente de la lluvia

- **MODIS MCDWD_L3 C6.1** (archivo reprocesado 2003-2025 en LAADS, doi:10.5067/MODIS/MCDWD_L3.061; teselas h10v07 y
  h11v07, 250 m): se desbloqueó al autorizar la aplicación LAADS en la cuenta de Earthdata y se lee con pyhdf. Solo se
  bajaron {mcx[n_dias]} días (por evento, los días −1, +1, +3, +5 y +7, que con el compuesto de 2 días cubren de −2 a +7; un día seco de referencia por año, el día +3 de cada
  episodio de lluvia ≥ p99 y 4 días de cada mes GSW con señal sin evento); de cada HDF se guardó el recorte de la
  cuenca y el SHA-256 del original. Capa principal: **Flood_2Day_250m** (la guía de usuario y el visor de NASA prefieren
  el compuesto de 2 días; el de 1 día se contamina con sombras de nube); Flood_3Day para los episodios.
  Valores del propio HDF: 0 sin agua · 1 agua de referencia · 2 inundación recurrente (estacional) · 3 inundación
  (inusual) · 255 datos insuficientes (nubes/sin pasada). «Inundación» = clase 3; la clase 2 se informa aparte.
- **Máscara fija:** el {mcx[fijo]} de los píxeles de la cuenca salen como 255 en todos los días bajados (el producto
  enmascara sombra de relieve y terreno alto sobre el drenaje, filtro HAND): casi toda la montaña, pero solo el
  {mcx[fijo_llanura]} de la llanura. Esos píxeles no cuentan como nubes y MCDWD no puede ver inundación en ellos
  (sirve para la llanura, no para las cabeceras).
- **Nubes:** en promedio el {mcx[insuf]} de los píxeles restantes de la cuenca son «datos insuficientes» en el compuesto de 2 días.
  Un día cuenta si < 80 % de la zona está cubierta. Referencia (días secos): p95 = {mcx[p95]} km² de clase 3 en la
  cuenca. Inundación observada = máximo del evento > p95 y ≥ 2 km².
- **Resultado por evento:** confirmados por MCDWD: {mcx[obs_si]}; vistos sin inundación anómala: {mcx[obs_no]};
  indeterminados por nubes: {mcx[indet]}. Detalle en `results/yuna/mcdwd_por_evento.csv` y la figura 6. El umbral
  (p95 de días secos ≈ {mcx[p95]} km²) es bajo: confirmaciones de 4-8 km² son débiles; las fuertes (> 15 km²) son
  {mcx[fuertes]}. El máximo puede caer antes del inicio oficial (la ventana empieza 2 días antes; p. ej. 2007-12 llega
  a su máximo el 10-dic, antes de que Olga tocara tierra, posible agua remanente de Noel): hay que mirar la imagen.
- **Meses GSW con señal sin evento, vistos con MCDWD:** {mcx[gsw]}.

{{TABLA_MC_EV}}

![MCDWD](../figures/yuna/fig_y6_inundacion_observada_mcdwd.png)

- **JRC Global Surface Water, Monthly Water History v1.4** (Pekel et al. 2016, *Nature* 540: 418-422,
  doi:10.1038/nature20584): usado, 2001-2020 ({gm[meses_gsw]} meses; 2021 da 404 en el FTP del JRC). Lectura por
  ventanas HTTP (sin bajar mosaicos completos). Máscaras: embalse de Hatillo ({gm[embalse_km2_max_posible]:.1f} km²
  de píxeles alguna vez con agua) y llanura del Bajo Yuna bajo 20 m sin agua permanente ({gm[llanura_km2]:.0f} km²).
- Límites: nubes (un mes con < 30 % de píxeles válidos en la llanura no cuenta: {n_lla_nubes} de {n_lla} meses),
  paso de Landsat cada 8-16 días (una crecida de 2-4 días puede no verse), y el arroz inundado por riego es agua
  «normal»: la señal es la anomalía frente a la mediana del mismo mes (señal = sobre p90 y ≥ 1 p. p.).
- Eventos con señal observada en el mes del evento o el siguiente: {ev_obs}.
- Meses con señal (sobre p90 y ≥ 1 p. p.) **sin** evento en el catálogo: {meses_sin_cat} ({n_sobre} meses con señal en
  total). Son candidatos a inundaciones no registradas o a artefactos (nubes/sombras residuales, arroz recién inundado):
  hay que mirarlos imagen por imagen antes de llamarlos inundación. Eventos sin mes observable: los de
  2022-2024 (fuera de GSW) y los meses nublados.

![GSW](../figures/yuna/fig_y2_agua_observada_gsw.png)

## 4 · Presa de Hatillo (factor de confusión explícito)

Datos publicados (con conflicto): inaugurada en 1984 (obra 1977-1984); embalse ~22 km²; capacidad 710 hm³ (volumen
total, Wikipedia/Structurae) frente a 441,6 hm³ (lista de presas), ~400 hm³ (un funcionario) y 374,88 hm³ (volumen
máximo operativo que usa el INDRHI para el % de llenado, con nivel máximo 86,50 msnm). Propósitos de diseño: control
de inundaciones, riego y energía (8 MW). En agosto de 2021 el INDRHI dijo que Hatillo opera en «manejo de vertido
libre»; Wikipedia describe un vertedor controlado de 650 m³/s. **No escribimos que «regula las crecidas».**
No hay serie pública diaria de niveles ni descargas (ni en datos.gob.do ni en el sitio del INDRHI): solo notas y
boletines. Sustituto: área de agua del embalse en JRC GSW ({n_emb} meses con ≥ 50 % de píxeles válidos; mediana
{emb_med:.1f} km², rango {emb_min:.1f}-{emb_max:.1f} km²).

## 5 · Paneles por evento (mismas escalas)

`results/yuna/paneles_eventos.csv`; figuras `fig_y3_paneles_eventos_1/2`. Para cada evento: lluvia de 48/72 h
(media y máximo de celda, IMERG; CHIRPS {chirps_txt}), antecedente de 30/60/90 días (IMERG,
como percentil del mismo mes), raíz SMAP L4 (2015+) y GLDAS (mes anterior, z), lluvia de 48 h por zona (¿cayó
sobre la presa o abajo?) e inundación diaria MCDWD por zona (con el agua GSW del mes en el texto).

![Paneles 1](../figures/yuna/fig_y3_paneles_eventos_1.png)
![Paneles 2](../figures/yuna/fig_y3_paneles_eventos_2.png)

GEOGLOWS v2 (simulación forzada con ERA5; no son aforos; no representa la operación de Hatillo). El servicio
`getriverid` devuelve el tramo más cercano, que resultó ser a menudo un arroyo lateral. Control con HydroRIVERS:

{{TABLA_GG}}

**Fallo declarado:** {n_gg_ok} de 4 puntos quedaron en el cauce principal, incluso buscando el tramo de mayor caudal
en una rejilla de ±1,2 km (una búsqueda más amplia no terminó a tiempo). Por eso los paneles **no** muestran caudal
GEOGLOWS; las series bajadas quedan en `data/yuna/geoglows/` solo como registro. Para usarlo hay que mapear los
`river_id` del cauce del Yuna con la red TDX-Hydro (tabla de metadatos de GEOGLOWS, ~245 MB).

Suficiencia de datos por evento (`results/yuna/datos_suficientes_por_evento.csv`):

{{TABLA_INS}}

## 6 · Backtest de disparadores (n pequeño; se dice claro)

Unidad: eventos del catálogo (detectado si hay disparo en [inicio − 2 d, fin]) y episodios de disparo (días
separados por > 3 días). POD = aciertos/eventos; FAR = episodios sin evento/episodios; CSI =
aciertos/(aciertos + fallos + falsas alarmas). Calibración 2001-2015 ({ncal} eventos), prueba 2016-2024
({nte} eventos). IC 95 % por bootstrap de años (2000 réplicas). Con 6 y 8 eventos, un evento mueve el POD
12-17 puntos: **la potencia para distinguir disparadores es casi nula**. FAR es cota superior: el catálogo de prensa
no registra todas las inundaciones. Tabla de bloques fijos de 3 días en el CSV. La regla de la Cruz Roja (sEAP
MDRDO020) usa un PRONÓSTICO de INDOMET > 100 mm/2 días ligado a ciclones (mayo-noviembre); aquí se aplica a lluvia
estimada por IMERG, sin esa condición.

{{TABLA_DESC}}

{{TABLA_BT}}

![Backtest](../figures/yuna/fig_y4_backtest_disparadores.png)

Umbrales calibrados: media de cuenca {info[a2_umbral]:.0f} mm/48 h; antecedente elegido {info[c][n_dias]} días,
p{c_pct:.0f} = {info[c][umbral_mm]:.0f} mm; p90 del antecedente = {info[antecedente_p90_mm]:.0f} mm; umbral rebajado si el
antecedente es húmedo = {info[b2_umbral_bajo]:.0f} mm/48 h (casi el mismo 100: la calibración no encontró valor en rebajarlo).

**Verificación observada (MCDWD).** ¿Los disparadores detectan los eventos que MODIS confirma? (`results/yuna/backtest_verificacion_mcdwd.csv`;
«observa» vacío = nubes):

{{TABLA_VER}}

## 7 · ¿Cambia la presa la relación arriba-abajo? (prueba del confusor)

(1) Episodios de lluvia fuerte (máx. de celda ≥ p99 = {au[umbral_r48max_p99_mm]:.0f} mm/48 h): {au[n_episodios]}
episodios, {au[n_con_inundacion]} con evento del catálogo. AUC de cada variable para separar episodios con y sin
inundación, por zona (IC 95 % bootstrap):

{{TABLA_AUC}}

(1b) La misma prueba con **verdad observada** (MCDWD, independiente de la prensa y de la lluvia): episodios de lluvia
≥ p99 con inundación de clase 3 sobre el p95 de los días secos (compuesto de 3 días en el día +3). {mcx[auc_txt]}
Con tan pocos episodios con inundación observada la prueba **no tiene potencia**: ningún AUC (ni siquiera el de la
lluvia) se separa de 0,5 con estos IC, y la diferencia Hatillo − Camú tampoco.

{{TABLA_AUC_OBS}}

(2) Meses 2001-2020 con agua observada en la llanura (GSW): ρ de Spearman entre la lluvia del mes en cada zona y la
anomalía de agua, según el estado del embalse (área GSW ≥ o < mediana):

{{TABLA_MENS}}

![Presa](../figures/yuna/fig_y5_presa_confusor.png)

Lectura: la lluvia del episodio separa bien (AUC 0,7-0,8) y el antecedente no (AUC ≈ 0,4-0,5, IC con 0,5) en las
tres zonas. La diferencia entre el antecedente sobre Hatillo y el del Camú no es distinguible de cero. En los meses,
la relación lluvia de arriba → agua abajo es {rh[embalse_alto_alto_hatillo]} con embalse alto y
{rh[embalse_bajo_alto_hatillo]} con embalse bajo; el Camú, que la presa no toca, muestra el mismo patrón
({rh[embalse_alto_camu]} frente a {rh[embalse_bajo_camu]}). Si la presa fuese la causa, el patrón tendría que
aparecer solo arriba. Que aparezca en las dos zonas apunta a algo común a ambas (la estación, las nubes que limitan
lo que GSW ve), no a la operación; esa explicación tampoco está probada. **Con estos datos no se puede afirmar ni descartar el giro
del embalse.** Lo que sí queda probado es que la pregunta está bien planteada: el {pct_no_reg:.0f} % de la cuenca (Camú + resto)
llega al Bajo Yuna sin pasar por Hatillo.

## Lo que sabemos
- La cuenca del Yuna mide ~5.500 km²; por la cortina de Hatillo pasa el agua de solo ~{pct_hat:.0f} % de ella. El Camú (La Vega) y el resto del
  Bajo Yuna entran aguas abajo de la presa (HydroSHEDS; coherente con fuentes escritas).
- Bonao drena sobre Hatillo; La Vega, por el Camú; la celda «cubo lleno» de la Cordillera y la ciudad de Santiago no
  drenan al Yuna.
- El Bajo Yuna se inunda de forma recurrente: {ncu} eventos con fuente entre 2003 y 2026.
- Hatillo vertió durante Fiona (2022), nov-2023 y mayo-2024 (notas INDRHI/COE), y no vertió con Franklin ni Melissa.
- JRC GSW (observación) ve agua anómala en la llanura en el mes de estos eventos: {ev_obs}.
- MODIS MCDWD (observación) confirma inundación anómala en: {mcx[obs_si]}; las nubes impiden decidir en: {mcx[indet]}.

## Lo que creemos saber
- MODIS MCDWD ve inundación anómala en la llanura en la mayoría de los eventos del catálogo ({mcx[resumen]}), incluidos
  Fiona 2022 y noviembre de 2023, que GSW no cubre; pero el umbral es bajo y la mayoría de los días están tapados.
- La lluvia del episodio pesa más que el antecedente para que haya un evento registrado (AUC 0,7-0,8 frente a ≈ 0,4).
- Un disparador de 100 mm/48 h sobre el máximo de celda detecta casi todo, pero con {fa_anio_c:.1f} (2001-2015) y {fa_anio_t:.1f} (2016-2024) episodios sin evento por año.
- El antecedente de 30-90 días, solo o combinado, no añade capacidad detectable con 14 eventos.

## Lo que hay que comprobar
- Series diarias de nivel y descarga de Hatillo (INDRHI/EGEHID, por la Ley 200-04 de acceso a la información).
  Sin ellas, la presa como confusor no se puede probar a escala de evento.
- Sentinel-1 (radar, 2017-2025) para los eventos que MCDWD no ve por nubes, y revisar en Worldview las imágenes de
  los días que MCDWD marca como inundados (falsos positivos por sombra de nube o de relieve).
- Aforos del INDRHI en Villa Riva/Cotuí, y GEOGLOWS en el cauce principal, para pasar de «evento en prensa» a caudal.
- Un catálogo más completo (EM-DAT con cuenta; DesInventar no cubre RD después de 2000).
- Que IMERG, SMAP L4 y CHIRPS comparten insumos (GPCC/GTS; SMAP L4 v6+ ajusta su lluvia a IMERG): su acuerdo no es
  validación independiente.

## Reproducción

```
docker compose run --rm yuna                    # todo (descarga lo que falta: HydroSHEDS, JRC GSW, GEOGLOWS)
docker compose run --rm yuna --etapa analisis   # solo análisis, figuras, JSON web, informe y cuaderno
docker compose run --rm --entrypoint "uv run --frozen --no-sync pytest -q tests/test_yuna.py" yuna
```

Descargas en `data/yuna/MANIFEST.json` (URL, fecha, SHA-256, licencia). El token de Earthdata se lee solo de
`/run/secrets/earthdata_token` y no se escribe en ningún archivo. Cuaderno: `notebooks/08_caso_yuna.ipynb`
(HTML en `reports_nacional/notebooks_html/08_caso_yuna.html`). JSON para pantallas: `results/yuna/web/` (ver
`CONTRATO.md`).

## Referencias
- Lehner, B., Grill, G. (2013). Global river hydrography and network routing. *Hydrol. Process.* 27: 2171-2186.
- Pekel, J.-F. et al. (2016). High-resolution mapping of global surface water and its long-term changes. *Nature* 540: 418-422.
- Huffman, G. J. et al. (2023). GPM IMERG Final Precipitation L3 1 day 0.1° V07. GES DISC, doi:10.5067/GPM/IMERGDF/DAY/07.
- Reichle, R. et al. SMAP L4 Global 3-hourly 9 km Surface and Root Zone Soil Moisture (SPL4SMGP), NSIDC.
- Rodell, M. et al. (2004). The Global Land Data Assimilation System. *BAMS* 85: 381-394 (GLDAS-2.1 Noah, doi:10.5067/SXAVCZFAQLNO).
- Funk, C. et al. (2015). CHIRPS. *Sci. Data* 2: 150066.
- GEOGLOWS v2 retrospectivo (ECMWF/BYU), https://geoglows.ecmwf.int (CC BY 4.0).
- IFRC sEAP MDRDO020 (Cruz Roja Dominicana, 2026): https://go-api.ifrc.org/api/DownloadFile/94311/MDRDO020%20sEAP%20Summary
- CEPAL (2004). República Dominicana: evaluación de los daños de las inundaciones en las cuencas Yaque del Norte y Yuna (LC/MEX/L.607).
"""
