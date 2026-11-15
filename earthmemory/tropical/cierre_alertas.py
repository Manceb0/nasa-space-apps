"""Auditoría de cierre: confirmación sin mirar días futuros y oportunidad de la señal.

Solo lee resultados existentes. No descarga, no recalibra y no simula disponibilidad
operativa: IMERG Final y CHIRPS son retrospectivos. Conserva el proxy espacial de
CHIRPS original para aislar el efecto temporal, y contrasta la versión de misma celda.
"""
from __future__ import annotations

import hashlib
import json

import pandas as pd
from shapely.geometry import shape

from ..yuna import analisis as an
from ..yuna.catalogo import ventanas
from ..yuna.common import ROOT
from .alerta_causal import chirps_max48

OUT = ROOT / "results" / "tropical" / "cierre_alertas"


def confirmar_pasado(a: pd.Series, c: pd.Series) -> pd.Series:
    """Confirma A hoy con C hoy o ayer; nunca mañana."""
    return a & (c | c.shift(1, fill_value=False))


def main():
    source = an.RES / "series_diarias_zonas.parquet"
    catalog = an.RES / "catalogo_eventos.csv"
    d = pd.read_parquet(source)
    assert d.index.is_monotonic_increasing and d.index.is_unique
    assert d.index.to_series().diff().dropna().eq(pd.Timedelta(days=1)).all()
    vent = ventanas(pd.read_csv(catalog))
    a = d.imerg_max48_yuna > 100
    c = an.suma_movil(d.chirps_max_yuna, 2) > 100
    geo = json.loads((an.RES / "cuencas_yuna.geojson").read_text(encoding="utf-8"))
    geom = next(shape(f["geometry"]) for f in geo["features"] if f["properties"]["zona"] == "yuna")
    c_same_cell = chirps_max48(geom).reindex(d.index) > 100
    rules = {
        "IMERG": a,
        "acuerdo_original_mas_menos_1d": a & (c | c.shift(1, fill_value=False) | c.shift(-1, fill_value=False)),
        "acuerdo_hoy_o_ayer": confirmar_pasado(a, c),
        "acuerdo_mismo_dia": a & c,
        "acuerdo_misma_celda_hoy_o_ayer": confirmar_pasado(a, c_same_cell),
    }
    # Prueba de fuga temporal: cambiar C mañana no debe alterar la señal de hoy.
    idx = pd.date_range("2020-01-01", periods=5)
    ta = pd.Series(True, index=idx)
    tc = pd.Series(False, index=idx)
    changed = tc.copy()
    changed.iloc[3:] = True
    assert confirmar_pasado(ta, tc).iloc[:3].equals(confirmar_pasado(ta, changed).iloc[:3])
    assert not confirmar_pasado(ta, changed).iloc[2]
    assert bool((ta & (changed | changed.shift(-1, fill_value=False))).iloc[2])

    summary, events = [], []
    for period, name in ((an.CAL, "2001-2015"), (an.TEST, "2016-2024")):
        for rule, signal in rules.items():
            scored = an.puntuar(signal, vent, period)
            counts = scored["tot"]
            if period == an.TEST and rule in ("IMERG", "acuerdo_original_mas_menos_1d"):
                assert (counts["h"], counts["fa"]) == ((7, 39) if rule == "IMERG" else (7, 20))
            if period == an.TEST and rule == "acuerdo_misma_celda_hoy_o_ayer":
                assert (counts["h"], counts["fa"]) == (6, 16)
            before = during = absent = unknown = 0
            for start, end, eid in vent:
                if not period[0] <= start.year <= period[1]:
                    continue
                segment = signal.loc[start - pd.Timedelta(days=2):end]
                fired = segment[segment].index
                first = fired[0] if len(fired) else None
                phase = "sin_senal" if first is None else "fecha_anterior" if first < start else "durante"
                before += phase == "fecha_anterior"
                during += phase == "durante"
                absent += phase == "sin_senal"
                # Fecha t significa día completo: incluso sin latencia, no existe antes de t+1.
                earliest = first + pd.Timedelta(days=1) if first is not None else None
                ideal_lead = (start - earliest).total_seconds() / 3600 if earliest is not None else None
                unknown += ideal_lead is not None and ideal_lead > 0
                events.append({
                    "periodo": name, "regla": rule, "evento": eid,
                    "inicio_catalogo": str(start.date()), "fin_catalogo": str(end.date()),
                    "primera_fecha_senal": str(first.date()) if first is not None else "",
                    "fase_por_fecha": phase,
                    "anticipacion_ideal_horas_sin_latencia": ideal_lead,
                    "anticipacion_operativa": "NO EVALUADA: faltan fechas de disponibilidad y hora de inicio",
                })
            summary.append({
                "periodo": name, "regla": rule, **counts,
                **an.metricas_ep(counts["h"], counts["m"], counts["fa"], counts["ep"]),
                "eventos_senal_fecha_anterior": before, "eventos_senal_durante": during,
                "eventos_sin_senal": absent,
                "eventos_margen_ideal_positivo_sin_latencia": unknown,
            })
    OUT.mkdir(parents=True, exist_ok=True)
    table = pd.DataFrame(summary)
    table.to_csv(OUT / "comparacion.csv", index=False, float_format="%.6f")
    pd.DataFrame(events).to_csv(OUT / "eventos.csv", index=False)
    # Paquete de evidencia listo para la interfaz; solo la versión espacial corregida.
    demo_rules = {"IMERG", "acuerdo_misma_celda_hoy_o_ayer"}
    demo = {
        "titulo": "¿Qué cambia al pedir confirmación?",
        "periodo": "2016-2024",
        "tipo": "comparacion_historica_no_operativa",
        "regla": ">100 mm/48 h; CHIRPS acumulado en misma celda; confirmacion hoy o ayer",
        "resumen": [r for r in summary if r["periodo"] == "2016-2024" and r["regla"] in demo_rules],
        "eventos": [r for r in events if r["periodo"] == "2016-2024" and r["regla"] in demo_rules],
        "avisos_obligatorios": [
            "Menos episodios sin evento catalogado: 39 a 16; detectados: 7/8 a 6/8.",
            "Ninguna primera senal en fecha estrictamente anterior al inicio catalogado.",
            "Son productos retrospectivos. No son avisos en vivo ni instrucciones de evacuacion.",
            "El catalogo puede omitir inundaciones; no se ha demostrado reduccion de danos.",
        ],
        "fuente": "reports_nacional/CIERRE_ALERTAS.md",
    }
    (OUT / "demo_yuna.json").write_text(json.dumps(demo, ensure_ascii=False, indent=2), encoding="utf-8")
    evidence = {
        "fuentes": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in (source, catalog, an.RES / "cuencas_yuna.geojson",
                              *sorted((ROOT / "data" / "tendencias" / "chirps_diario").glob("chirps_v2p0_diario_RD_*.nc")))},
        "comprobaciones": ["reproduce 7/8 y 39 originales", "reproduce 7/8 y 20 con futuro",
                            "reproduce 6/8 y 16 con CHIRPS de misma celda",
                            "confirmacion_pasado invariante a cambios futuros", "serie diaria sin huecos"],
        "limites": [
            "Retrospectivo; no reconstruye fechas de disponibilidad de IMERG Final ni CHIRPS.",
            "Las reglas sin 'misma_celda' conservan el proxy antiguo, solo para descomponer los cambios.",
            "Inicio del catalogo con precision diaria o semanal; no permite anticipacion horaria real.",
            "Episodios sin evento catalogado no equivalen a ausencia comprobada de inundacion.",
            "Prueba reutilizada para varias exploraciones; no es validacion externa ni test nuevo intacto.",
            "CSI heredado combina aciertos por evento y falsas por episodio; no es precision de alertas.",
        ],
    }
    (OUT / "evidencia.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    print(table.to_string(index=False))


if __name__ == "__main__":
    main()
