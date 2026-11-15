"""Índices ETCCDI de lluvia diaria y métricas de sequía SPI, vectorizados sobre celdas.

Definiciones (Zhang et al. 2011, WIREs Climate Change 2:851-870, doi:10.1002/wcc.147; Karl et al. 1999):
día húmedo = P ≥ 1 mm; día seco = P < 1 mm.
- PRCPTOT  lluvia total de los días húmedos (mm)
- R1mm     número de días húmedos (días; Rnnmm con nn = 1)
- SDII     PRCPTOT / número de días húmedos (mm/día)
- R20mm, R50mm   número de días con P ≥ 20 mm / ≥ 50 mm (días)
- Rx1day   máximo de 1 día (mm);  Rx5day  máximo de 5 días consecutivos (mm)
- R95pTOT, R99pTOT   lluvia total de los días con P > percentil 95 / 99 de los días húmedos del periodo base (mm).
  Base = 2001-2024 (no hay 1961-1990 en estos productos); umbral fijo por celda y por producto.
- CDD, CWD   máxima racha de días secos / húmedos consecutivos (días)
- RACHAS10, RACHAS15   número de rachas secas de ≥ 10 y ≥ 15 días (no es ETCCDI; definición propia, documentada)
Las rachas se cuentan DENTRO del bloque (año o estación): una racha que cruza el borde se corta (como climdex con
spells.can.span.years = FALSE). Si a una celda le falta algún día del bloque, el índice queda NaN.

SPI (McKee et al. 1993): suma móvil de k meses → gamma de dos parámetros por mes calendario con estimador de máxima
verosimilitud aproximado de Thom (1958) (como Edwards y McKee 1997) y probabilidad de cero mixta. Ajuste sobre
2001-2024 (24 valores por mes calendario: frágil, ver el informe). Sequía = SPI ≤ −1.
Por año (2002-2024; 2001 no tiene SPI-12 completo y se excluye en ambas escalas para que sean comparables):
- MESES   meses del año con SPI ≤ −1 (frecuencia, meses/año)
- EVENTOS número de eventos (rachas de meses consecutivos con SPI ≤ −1) que EMPIEZAN en el año
- SEVER   severidad: Σ(−SPI) de los meses del año con SPI ≤ −1 (adimensional)
- DURAC   duración media (meses) de los eventos que empiezan en el año; NaN si no empieza ninguno
"""

from __future__ import annotations

import numpy as np
from scipy import stats as sstats

WET = 1.0

# id, etiqueta ES, etiqueta EN, unidad, qué mide, por qué importa
VARIABLES = {
    "CDD": ("Días secos consecutivos (máx.)", "Consecutive dry days (max)", "días",
            "La racha más larga de días con menos de 1 mm.", "Rachas secas largas estresan cultivos, pastos y abasto de agua."),
    "CWD": ("Días húmedos consecutivos (máx.)", "Consecutive wet days (max)", "días",
            "La racha más larga de días con al menos 1 mm.", "Lluvia persistente satura el suelo y favorece crecidas."),
    "PRCPTOT": ("Lluvia total de días húmedos", "Total wet-day precipitation", "mm",
                "Suma de la lluvia de los días con al menos 1 mm.", "Es el agua total que recibe la zona en el periodo."),
    "R1mm": ("Días húmedos (≥1 mm)", "Wet days (≥1 mm)", "días",
             "Número de días con al menos 1 mm.", "Separa \"llueve menos veces\" de \"llueve menos\"; sensible a cómo cada producto detecta llovizna."),
    "SDII": ("Intensidad diaria simple", "Simple daily intensity index", "mm/día",
             "Lluvia total dividida por el número de días húmedos.", "Dice si cuando llueve, llueve más fuerte."),
    "R20mm": ("Días de lluvia fuerte (≥20 mm)", "Heavy rain days (≥20 mm)", "días",
              "Número de días con 20 mm o más.", "Días que pueden causar escorrentía y anegamiento local."),
    "R50mm": ("Días de lluvia muy fuerte (≥50 mm)", "Very heavy rain days (≥50 mm)", "días",
              "Número de días con 50 mm o más.", "Días asociados a inundaciones repentinas y deslizamientos."),
    "Rx1day": ("Lluvia máxima en 1 día", "Max 1-day precipitation", "mm",
               "La mayor lluvia de un solo día.", "Mide el aguacero más intenso del periodo."),
    "Rx5day": ("Lluvia máxima en 5 días", "Max 5-day precipitation", "mm",
               "La mayor lluvia acumulada en 5 días seguidos.", "Episodios de varios días (ondas, tormentas) que llenan ríos y presas."),
    "R95pTOT": ("Lluvia de días muy húmedos (>p95)", "Very wet day precipitation (>p95)", "mm",
                "Lluvia total de los días por encima del percentil 95 de los días húmedos 2001-2024.",
                "Cuánta del agua llega en los días más extremos."),
    "R99pTOT": ("Lluvia de días extremadamente húmedos (>p99)", "Extremely wet day precipitation (>p99)", "mm",
                "Lluvia total de los días por encima del percentil 99 de los días húmedos 2001-2024.",
                "La cola más extrema; con 24 años es muy ruidosa."),
    "RACHAS10": ("Rachas secas de ≥10 días", "Dry spells ≥10 days", "rachas",
                 "Número de rachas de 10 o más días seguidos con menos de 1 mm.", "Frecuencia de periodos secos que ya afectan la agricultura de secano."),
    "RACHAS15": ("Rachas secas de ≥15 días", "Dry spells ≥15 days", "rachas",
                 "Número de rachas de 15 o más días seguidos con menos de 1 mm.", "Periodos secos largos; relevantes para riego y embalses."),
    "SPI3_MESES": ("Meses en sequía (SPI-3 ≤ −1)", "Drought months (SPI-3 ≤ −1)", "meses",
                   "Meses del año con SPI-3 ≤ −1 (déficit de 3 meses).", "Sequía agrícola / de corto plazo."),
    "SPI3_EVENTOS": ("Eventos de sequía SPI-3", "SPI-3 drought events", "eventos",
                     "Eventos de sequía (meses seguidos con SPI-3 ≤ −1) que empiezan en el año.", "Cuántas veces se entra en sequía."),
    "SPI3_SEVER": ("Severidad de sequía SPI-3", "SPI-3 drought severity", "adimensional",
                   "Suma de −SPI-3 en los meses del año con SPI-3 ≤ −1.", "Combina duración e intensidad del déficit."),
    "SPI3_DURAC": ("Duración media de sequía SPI-3", "SPI-3 drought mean duration", "meses",
                   "Duración media de los eventos SPI-3 que empiezan en el año (vacío si no hay).", "Si las sequías duran más."),
    "SPI12_MESES": ("Meses en sequía (SPI-12 ≤ −1)", "Drought months (SPI-12 ≤ −1)", "meses",
                    "Meses del año con SPI-12 ≤ −1 (déficit de 12 meses).", "Sequía hidrológica: embalses y acuíferos."),
    "SPI12_EVENTOS": ("Eventos de sequía SPI-12", "SPI-12 drought events", "eventos",
                      "Eventos SPI-12 ≤ −1 que empiezan en el año.", "Entradas en sequía de largo plazo."),
    "SPI12_SEVER": ("Severidad de sequía SPI-12", "SPI-12 drought severity", "adimensional",
                    "Suma de −SPI-12 en los meses del año con SPI-12 ≤ −1.", "Déficit acumulado de largo plazo."),
    "SPI12_DURAC": ("Duración media de sequía SPI-12", "SPI-12 drought mean duration", "meses",
                    "Duración media de los eventos SPI-12 que empiezan en el año (vacío si no hay).", "Persistencia de la sequía larga."),
}
DAILY = ["CDD", "CWD", "PRCPTOT", "R1mm", "SDII", "R20mm", "R50mm", "Rx1day", "Rx5day", "R95pTOT", "R99pTOT", "RACHAS10", "RACHAS15"]
SPI_KEYS = ["SPI3_MESES", "SPI3_EVENTOS", "SPI3_SEVER", "SPI3_DURAC", "SPI12_MESES", "SPI12_EVENTOS", "SPI12_SEVER", "SPI12_DURAC"]

# Estaciones de la RD: régimen bimodal del Caribe (Taylor et al. 2002; Gamble y Curtis 2008): estación seca de
# diciembre a abril, primera temporada de lluvias mayo-julio (incluye la sequía de medio verano de julio, que se
# deja con la temprana para tener bloques de 3-5 meses) y segunda temporada agosto-noviembre (huracanes).
# La estación seca de un año AAAA va de diciembre de AAAA−1 a abril de AAAA (por eso empieza en 2002).
PERIODS = {
    "anual": ("Año (ene-dic)", "Year (Jan-Dec)", list(range(1, 13))),
    "seca": ("Estación seca (dic-abr)", "Dry season (Dec-Apr)", [12, 1, 2, 3, 4]),
    "humeda_temprana": ("Lluvias tempranas (may-jul)", "Early wet season (May-Jul)", [5, 6, 7]),
    "humeda_tardia": ("Lluvias tardías (ago-nov)", "Late wet season (Aug-Nov)", [8, 9, 10, 11]),
}


# ------------------------------------------------------------------ rachas

def _runs(B: np.ndarray) -> tuple[np.ndarray, dict]:
    """B (T × N) booleano. Devuelve (racha máxima por columna, {L: número de rachas con longitud ≥ L})."""
    T, N = B.shape
    cur = np.zeros(N, int)
    mx = np.zeros(N, int)
    cnt = {10: np.zeros(N, int), 15: np.zeros(N, int)}
    for t in range(T):
        b = B[t]
        ended = (~b) & (cur > 0)
        for L in cnt:
            cnt[L] += ended & (cur >= L)
        cur = np.where(b, cur + 1, 0)
        mx = np.maximum(mx, cur)
    for L in cnt:
        cnt[L] += cur >= L  # racha abierta al final del bloque
    return mx, cnt


def wet_percentiles(X: np.ndarray, qs=(95, 99)) -> dict:
    """Percentiles de los días húmedos (≥ 1 mm) por columna (método lineal de numpy)."""
    W = np.where(X >= WET, X, np.nan)
    return {q: np.nanpercentile(W, q, axis=0) for q in qs}


def block_indices(X: np.ndarray, thr: dict) -> dict:
    """X: (días del bloque × celdas) en mm/día. thr: {95: p95, 99: p99} por celda."""
    X = np.asarray(X, float)
    bad = ~np.isfinite(X).all(0)
    Xz = np.where(np.isfinite(X), X, 0.0)
    wet = Xz >= WET
    nwet = wet.sum(0)
    prcptot = np.where(wet, Xz, 0).sum(0)
    out = {
        "PRCPTOT": prcptot,
        "R1mm": nwet.astype(float),
        "SDII": np.where(nwet > 0, prcptot / np.maximum(nwet, 1), 0.0),
        "R20mm": (Xz >= 20).sum(0).astype(float),
        "R50mm": (Xz >= 50).sum(0).astype(float),
        "Rx1day": Xz.max(0),
        "R95pTOT": np.where(wet & (Xz > thr[95][None, :]), Xz, 0).sum(0),
        "R99pTOT": np.where(wet & (Xz > thr[99][None, :]), Xz, 0).sum(0),
    }
    c = np.cumsum(np.vstack([np.zeros((1, X.shape[1])), Xz]), 0)
    out["Rx5day"] = (c[5:] - c[:-5]).max(0) if X.shape[0] >= 5 else np.full(X.shape[1], np.nan)
    cdd, sp = _runs(~wet)
    cwd, _ = _runs(wet)
    out["CDD"], out["CWD"] = cdd.astype(float), cwd.astype(float)
    out["RACHAS10"], out["RACHAS15"] = sp[10].astype(float), sp[15].astype(float)
    for k in out:
        out[k] = np.where(bad, np.nan, out[k]).astype(float)
    return out


def period_blocks(days: np.ndarray, period: str, years: tuple[int, int]) -> list[tuple[int, np.ndarray]]:
    """[(año, índices de días)] del periodo. La estación seca del año y = dic(y−1) + ene-abr(y)."""
    d = days.astype("datetime64[D]")
    yy = d.astype("datetime64[Y]").astype(int) + 1970
    mm = (d.astype("datetime64[M]").astype(int) % 12) + 1
    months = PERIODS[period][2]
    out = []
    for y in range(years[0], years[1] + 1):
        if period == "seca":
            sel = ((yy == y - 1) & (mm == 12)) | ((yy == y) & np.isin(mm, [1, 2, 3, 4]))
            if not ((yy == y - 1) & (mm == 12)).any():
                continue
        else:
            sel = (yy == y) & np.isin(mm, months)
        out.append((y, np.flatnonzero(sel)))
    return out


def daily_indices(X: np.ndarray, days: np.ndarray, thr: dict, years=(2001, 2024)) -> dict:
    """{(índice, periodo): (años, matriz años × celdas)}."""
    out = {}
    for per in PERIODS:
        blocks = period_blocks(days, per, years)
        yrs = np.array([b[0] for b in blocks])
        res = [block_indices(X[ix], thr) for _, ix in blocks]
        for k in DAILY:
            out[(k, per)] = (yrs, np.vstack([r[k] for r in res]))
    return out


# ------------------------------------------------------------------ SPI

def monthly_totals(X: np.ndarray, days: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    m = days.astype("datetime64[M]")
    um = np.unique(m)
    M = np.vstack([X[m == u].sum(0) for u in um])  # NaN en un día → NaN en el mes de esa celda
    # celdas con algún NaN en el mes → NaN (sum de NaN da NaN igualmente)
    return um, M


def _gamma_thom(x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Estimador de Thom (1958) por columna sobre valores > 0 (NaN fuera). Devuelve (alfa, beta)."""
    with np.errstate(divide="ignore", invalid="ignore"):
        mean = np.nanmean(x, 0)
        A = np.log(mean) - np.nanmean(np.log(x), 0)
        alpha = (1 + np.sqrt(1 + 4 * A / 3)) / (4 * A)
        beta = mean / alpha
    return alpha, beta


def spi(M: np.ndarray, months: np.ndarray, scale: int, min_pos: int = 10) -> np.ndarray:
    """SPI-k por columna. M: totales mensuales (meses × celdas), months: datetime64[M]."""
    T, N = M.shape
    c = np.cumsum(np.vstack([np.zeros((1, N)), np.nan_to_num(M)]), 0)
    acc = np.full((T, N), np.nan)
    acc[scale - 1:] = c[scale:] - c[:-scale]
    nanwin = np.full((T, N), True)
    fin = np.isfinite(M).astype(int)
    cf = np.cumsum(np.vstack([np.zeros((1, N), int), fin]), 0)
    nanwin[scale - 1:] = (cf[scale:] - cf[:-scale]) < scale
    acc[nanwin] = np.nan
    mo = (months.astype(int) % 12) + 1
    out = np.full((T, N), np.nan)
    for m in range(1, 13):
        rows = np.flatnonzero(mo == m)
        a = acc[rows]
        ok = np.isfinite(a)
        zero = ok & (a <= 0)
        nok = ok.sum(0)
        q = np.where(nok > 0, zero.sum(0) / np.maximum(nok, 1), np.nan)
        pos = np.where(ok & (a > 0), a, np.nan)
        npos = np.isfinite(pos).sum(0)
        al, be = _gamma_thom(pos)
        fit = (npos >= min_pos) & np.isfinite(al) & (al > 0)
        cdf = q[None, :] + (1 - q[None, :]) * sstats.gamma.cdf(np.clip(np.nan_to_num(a), 0, None), al[None, :], scale=be[None, :])
        cdf = np.where(zero, np.where(q > 0, q / 2, 1e-6)[None, :], cdf)
        z = sstats.norm.ppf(np.clip(cdf, 1e-6, 1 - 1e-6))
        out[rows] = np.where(ok & fit[None, :], z, np.nan)
    return out


def drought_metrics(S: np.ndarray, months: np.ndarray, years=(2002, 2024), thr: float = -1.0) -> dict:
    """Métricas anuales de sequía a partir de un SPI mensual (meses × celdas)."""
    T, N = S.shape
    yy = months.astype("datetime64[Y]").astype(int) + 1970
    D = np.where(np.isfinite(S), S <= thr, False)
    yrs = np.arange(years[0], years[1] + 1)
    meses = np.zeros((yrs.size, N))
    sever = np.zeros((yrs.size, N))
    nev = np.zeros((yrs.size, N))
    dsum = np.zeros((yrs.size, N))
    for k, y in enumerate(yrs):
        sel = yy == y
        meses[k] = D[sel].sum(0)
        sever[k] = np.where(D[sel], -S[sel], 0).sum(0)
    # eventos: rachas de D; se asignan al año de inicio
    cur = np.zeros(N, int)
    start = np.full(N, -1)
    for t in range(T + 1):
        b = D[t] if t < T else np.zeros(N, bool)
        begin = b & (cur == 0)
        start = np.where(begin, t, start)
        ended = (~b) & (cur > 0)
        for j in np.flatnonzero(ended):
            ys = yy[start[j]]
            if years[0] <= ys <= years[1]:
                nev[ys - years[0], j] += 1
                dsum[ys - years[0], j] += cur[j]
        cur = np.where(b, cur + 1, 0)
    bad = ~np.isfinite(S[np.isin(yy, yrs)]).all(0)
    with np.errstate(invalid="ignore", divide="ignore"):
        durac = np.where(nev > 0, dsum / nev, np.nan)
    res = {"MESES": meses, "EVENTOS": nev, "SEVER": sever, "DURAC": durac}
    return {k: (yrs, np.where(bad[None, :], np.nan, v)) for k, v in res.items()}
