"""Empaqueta resultados existentes para la demo; no calcula nuevas pruebas."""
import hashlib
import json
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sources = [ROOT / "results/cierre/resumen.json", ROOT / "results/tropical/cierre_alertas/demo_yuna.json",
           ROOT / "web/public/data/tendencias/provincias.json"]
thresholds, yuna, trends = [json.loads(p.read_text(encoding="utf-8")) for p in sources]
rows = [r for r in thresholds["lluvia_umbrales"] if r["metrica"] == "SDII" and r["umbral_mm"] in (.5, 1, 2, 5)]
assert [r["opuestas_al_menos_una_sig"] for r in rows] == [202, 160, 64, 0]
assert len(yuna["eventos"]) == 16
national = trends["tendencias"]["SDII"]["anual"]["DO"]
payload = {"umbrales": rows, "yuna": yuna, "nacional": national, "procedencia": [
    {"archivo": p.relative_to(ROOT).as_posix(), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
    for p in sources
]}
target = ROOT / "web/public/data/recorrido.json"
target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print(target.relative_to(ROOT))

# Respaldo de una sola pagina, sin peticiones de red ni dependencias.
national_rows = "".join(f"<tr><th>{p}</th><td>{national[p]['pendiente_decada']:+.4f}</td><td>{national[p]['p']}</td></tr>"
                        for p in ("IMERG", "CHIRPS"))
threshold_rows = "".join(f"<tr><th>{r['umbral_mm']} mm</th><td>{r['opuestas_al_menos_una_sig']}/442</td>"
                         f"<td>{r['opuestas_ambas_sig']}/442</td></tr>" for r in rows)
signal_rows = "".join(f"<tr><th>{'IMERG' if r['regla']=='IMERG' else 'Confirmacion hoy/ayer, misma celda'}</th>"
                      f"<td>{r['h']}/8</td><td>{r['fa']}</td><td>{r['eventos_senal_fecha_anterior']}/8</td></tr>"
                      for r in yuna["resumen"])
data = escape(json.dumps(payload, ensure_ascii=False, indent=2))
html = f'''<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Stellar Horizons · Respaldo de demo</title><style>
body{{max-width:920px;margin:auto;padding:24px;background:#111315;color:#eee;font:16px/1.6 system-ui}}
h1,h2{{line-height:1.2}}section{{margin:36px 0;padding-top:12px;border-top:1px solid #666}}
table{{width:100%;border-collapse:collapse}}th,td{{text-align:left;border-bottom:1px solid #444;padding:10px 4px}}
.note{{border-left:3px solid #f2cf83;padding:12px}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}}
</style><h1>Stellar Horizons</h1><p>Investigamos cómo cambia el agua y qué evidencia respalda las señales con las que nos preparamos.</p>
<p>Respaldo local de resultados calculados. No emite alertas en vivo.</p>
<section><h2>1. Investigar · República Dominicana, 2001–2024</h2><p>SDII: lluvia por día húmedo, umbral de 1 mm.</p>
<table><tr><th>Producto</th><th>Cambio (mm/día húmedo/década)</th><th>p</th></tr>{national_rows}</table>
<p>Una tendencia de un producto no basta para confirmar un cambio físico. Pendiente Theil–Sen y prueba Mann–Kendall con autocorrelación.</p></section>
<section><h2>2. Comprobar la definición</h2><table><tr><th>Día húmedo</th><th>Signos contrarios, al menos una significativa</th><th>Ambas significativas</th></tr>{threshold_rows}</table>
<p class="note">0 disputas no demuestra acuerdo: al subir el umbral disminuye la potencia para detectar tendencias. Comparaciones por celda con FDR.</p></section>
<section><h2>3. Aplicar · Yuna, 2016–2024</h2><p>8 inundaciones catalogadas; disparador &gt;100 mm/48 h.</p>
<table><tr><th>Regla</th><th>Eventos detectados</th><th>Episodios sin evento catalogado</th><th>Señal anterior al inicio</th></tr>{signal_rows}</table>
<p class="note">Confirmar reduce episodios de 39 a 16, pero pierde septiembre de 2022: detecciones 7/8→6/8.
Ninguna primera señal precede estrictamente al inicio catalogado. CHIRPS llega tarde; el catálogo puede omitir inundaciones.</p>
<p>Uso propuesto: evaluar filtros de monitoreo para la preparación. No se ha demostrado anticipación ni reducción de daños.
Fuentes: NASA GPM IMERG V07 Final y CHC CHIRPS v2.0, parcialmente dependientes. GOES: sin resolver.</p></section>
<details><summary>Datos y trazabilidad (incluye los 8 eventos)</summary><pre>{data}</pre></details></html>'''
(ROOT / "reports_nacional/RESPALDO_DEMO.html").write_text(html, encoding="utf-8")
