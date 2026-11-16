"""Registro de trazabilidad: cada prueba con su pregunta, sus datos, el script que la corre, las predicciones que se
escribieron ANTES de calcular, el resultado y el veredicto, con huellas SHA-256 y el commit que guardó cada archivo.

No recalcula nada: lee lo que ya está en results/. El veredicto sale del resumen.json de cada prueba; solo las
predicciones P1-P4 de la primera tanda (results/tropical/predicciones_registradas.json) no traen veredicto en su
resumen y se remiten a su fila de ESTADO_CONCLUSIONES.md, dicho así.
El commit de cada archivo lo da `git log` (fuera de Docker, en results/tropical/trazabilidad/git_commits.tsv).
Ejecutar: docker compose run --rm --entrypoint uv tropical run --frozen --no-sync python -m earthmemory.trazabilidad
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from .hr.common import ROOT, write_json

OUT = ROOT / "results" / "tropical" / "trazabilidad"   # único results/ con escritura en el contenedor
T = "results/tropical"

# carpeta de resultados, script, pregunta en una línea, datos (los de la NASA, marcados), filas de ESTADO_CONCLUSIONES
PRUEBAS = [
    ("", "earthmemory/tropical/run.py",
     "¿Las contradicciones entre productos de lluvia siguen la física de una isla tropical?",
     ["IMERG V07 (NASA GPM)", "CHIRPS", "IBTrACS", "pluviómetros GHCN-D"], "9, 12, 13"),
    ("era5", "earthmemory/tropical/era5_testigo.py",
     "¿Un tercer testigo (ERA5) ve el mismo escalón de IMERG?",
     ["IMERG V07 (NASA GPM)", "CHIRPS", "ERA5"], "4, 9"),
    ("forma", "earthmemory/tropical/forma_cambio.py",
     "¿El cambio IMERG − CHIRPS es tendencia, escalón, ambos o nada?",
     ["IMERG V07 (NASA GPM)", "CHIRPS"], "6, 7"),
    ("gpm_fuentes", "earthmemory/tropical/gpm_fuentes.py",
     "¿El cambio de IMERG viene de su parte infrarroja (GOES-16)?",
     ["IMERG V07 contadores de microondas (NASA GPM)", "CHIRPS", "ERA5"], "8"),
    ("alerta_acuerdo", "earthmemory/tropical/alerta_acuerdo.py",
     "¿Una alerta que pide testigo funciona mejor que una que cree a un solo producto? (versión retrospectiva)",
     ["IMERG V07 (NASA GPM)", "CHIRPS", "catálogo de inundaciones del Yuna"], "22, 23"),
    ("alerta_causal", "earthmemory/tropical/alerta_causal.py",
     "La misma alerta, solo con información disponible al emitir",
     ["IMERG V07 (NASA GPM)", "CHIRPS", "catálogo de inundaciones del Yuna"], "22, 24"),
    ("merra2", "earthmemory/tropical/merra2_testigo.py",
     "¿IMERG pierde días frente a un testigo en todo el país?",
     ["IMERG V07 (NASA GPM)", "CHIRPS", "MERRA-2 por NASA POWER"], "7b"),
    ("puerto_rico", "earthmemory/tropical/puerto_rico.py",
     "¿IMERG pierde días también en Puerto Rico, frente a pluviómetros densos?",
     ["IMERG V07 (NASA GPM)", "pluviómetros GHCN-D (NOAA)"], "4d"),
    ("hawaii", "earthmemory/tropical/hawaii.py",
     "¿Pierde días también en Hawái, bajo GOES-West? (separa GOES-16 de las microondas de NOAA-20)",
     ["IMERG V07 (NASA GPM)", "pluviómetros GHCN-D (NOAA)"], "8b"),
    ("era_gpm", "earthmemory/tropical/era_gpm.py",
     "¿El salto de IMERG es de 2018 o del paso de la era TRMM a la era GPM (2014)?",
     ["IMERG V07 (NASA GPM)", "pluviómetros GHCN-D (NOAA)", "CHIRPS"], "8b, 9"),
    ("ciclones", "earthmemory/tropical/ciclones_anticipacion.py",
     "¿Cuántas inundaciones del Yuna vinieron de un ciclón y con cuánta antelación las anunció el NHC?",
     ["IBTrACS", "pronósticos oficiales NHC (ATCF)", "catálogo de inundaciones del Yuna"], "25"),
    ("ciclones_sequia", "earthmemory/tropical/ciclones_sequia.py",
     "¿Después de los ciclones queda sequía, o llega cuando no hay ciclones?",
     ["CHIRPS", "IBTrACS"], "26"),
]
# Primera tanda: su resumen.json guarda números, no veredictos. Se remite a la fila de la tabla de conclusiones.
VEREDICTO_MANUAL = {
    "P1_ciclones": "ver fila 12 (se sostiene con límites)",
    "P1b_extremos": "ver fila 12 (se sostiene con límites)",
    "P2_barlovento": "ver fila 13 (asociación, se sostiene con límites)",
    "P2b_lluvia_debil": "ver fila 3",
    "P3_sin_explicar": "no se cumple (p de permutación 0,62)",
    "P4_instrumento": "punto de cambio hallado en 2013-10, conclusión retirada después (fila 9)",
}
META = {"registradas_utc", "fecha", "corte", "R_km", "refutacion", "predicciones", "interpretacion", "nota"}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def leer(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def commits() -> dict:
    f = OUT / "git_commits.tsv"
    if not f.exists():
        return {}
    d = {}
    for line in f.read_text(encoding="utf-8").splitlines():
        ruta, h, fecha = (line.split("\t") + ["", ""])[:3]
        d[ruta] = {"commit": h, "fecha": fecha}
    return d


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    git = commits()
    filas, n_pred, n_si, n_no, n_otro = [], 0, 0, 0, 0
    for carpeta, script, pregunta, datos, estado in PRUEBAS:
        base = ROOT / T / carpeta if carpeta else ROOT / T
        fp, fr = base / "predicciones_registradas.json", base / "resumen.json"
        if not fp.exists():
            continue
        pr = leer(fp)
        textos = pr.get("predicciones", {k: v for k, v in pr.items() if k not in META})
        hora = pr.get("registradas_utc") or pr.get("fecha")
        res = leer(fr) if fr.exists() else {}
        ver = res.get("veredicto", {})
        mtime = (datetime.fromtimestamp(fr.stat().st_mtime, timezone.utc).isoformat() if fr.exists() else None)
        preds = []
        for k, txt in textos.items():
            if k in ver and isinstance(ver[k], str):
                v = ver[k]
            elif k in ver:
                v = "se cumple" if ver[k] else "no se cumple"
            elif k in VEREDICTO_MANUAL:
                v = VEREDICTO_MANUAL[k]
            else:
                v = "pendiente" if not fr.exists() else "sin veredicto propio (declarativa)"
            n_pred += 1
            n_si += v == "se cumple"
            n_no += v == "no se cumple"
            n_otro += v not in ("se cumple", "no se cumple")
            preds.append({"id": k, "texto": txt, "veredicto": v})
        rel = lambda p: str(p.relative_to(ROOT)).replace("\\", "/")  # noqa: E731
        filas.append({
            "prueba": carpeta or "primera_tanda", "pregunta": pregunta, "datos": datos, "script": script,
            "script_sha256": sha(ROOT / script),
            "predicciones_archivo": rel(fp), "predicciones_sha256": sha(fp), "registradas": hora,
            "resultado_archivo": rel(fr) if fr.exists() else None,
            "resultado_sha256": sha(fr) if fr.exists() else None, "resultado_escrito_utc": mtime,
            "registrada_antes_del_resultado": (bool(mtime and hora < mtime) if hora and len(hora) > 10 else None),
            "commit_predicciones": git.get(rel(fp)), "commit_resultado": git.get(rel(fr)) if fr.exists() else None,
            "commit_script": git.get(script), "filas_estado": estado, "predicciones": preds,
        })
    total = {"pruebas": len(filas), "predicciones": n_pred, "se_cumplen": n_si, "no_se_cumplen": n_no,
             "otras": n_otro, "generado_utc": datetime.now(timezone.utc).isoformat()}
    write_json(OUT / "registro.json", {"resumen": total, "pruebas": filas})
    md(filas, total)
    print(json.dumps(total, ensure_ascii=False))


def md(filas, total):
    L = ["# Trazabilidad: de la pregunta al veredicto", "",
         "Generado por `earthmemory/trazabilidad.py` a partir de `results/` (no recalcula nada). Versión para máquinas: "
         "`results/tropical/trazabilidad/registro.json`. Cada prueba escribió sus predicciones en disco ANTES de bajar o "
         "calcular; la hora de registro va al lado de la hora en que se escribió el resultado. Las huellas SHA-256 "
         "permiten comprobar que nadie tocó los archivos después.", "",
         f"**{total['pruebas']} pruebas, {total['predicciones']} predicciones registradas: {total['se_cumplen']} se "
         f"cumplen, {total['no_se_cumplen']} no se cumplen y {total['otras']} se remiten a la tabla de conclusiones.** "
         "Las que fallaron se publican igual.", "",
         "| Prueba | Pregunta | Datos | Predicciones registradas (UTC) | Resultado escrito (UTC) | Antes | Se cumplen | Filas |",
         "|---|---|---|---|---|---|---|---|"]
    for f in filas:
        si = sum(p["veredicto"] == "se cumple" for p in f["predicciones"])
        nn = sum(p["veredicto"] == "no se cumple" for p in f["predicciones"])
        antes = {True: "sí", False: "no", None: "solo fecha"}[f["registrada_antes_del_resultado"]]
        L.append(f"| `{f['prueba']}` | {f['pregunta']} | {', '.join(f['datos'])} | {(f['registradas'] or '')[:19]} | "
                 f"{(f['resultado_escrito_utc'] or 'pendiente')[:19]} | {antes} | {si} de {si + nn} | {f['filas_estado']} |")
    L += ["", "## Cada predicción", ""]
    for f in filas:
        L += [f"### `{f['prueba']}`: {f['pregunta']}", "",
              f"Script `{f['script']}` (sha256 `{f['script_sha256'][:12]}`). Predicciones `{f['predicciones_archivo']}` "
              f"(sha256 `{f['predicciones_sha256'][:12]}`); resultado `{f['resultado_archivo']}`"
              + (f" (sha256 `{f['resultado_sha256'][:12]}`)." if f["resultado_sha256"] else "."), ""]
        c = f["commit_predicciones"]
        if c:
            L += [f"Guardado en git: predicciones en `{c['commit']}` ({c['fecha']})"
                  + (f"; resultado en `{f['commit_resultado']['commit']}`" if f["commit_resultado"] else "") + ".", ""]
        for p in f["predicciones"]:
            L.append(f"- **{p['id']}** · {p['veredicto']}. {p['texto']}")
        L.append("")
    (ROOT / "reports_nacional" / "TRAZABILIDAD.md").write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    main()
