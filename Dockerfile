# PHANTOM · NASA Space Apps 2026 · Stellar Horizons
# Reproduce el análisis completo: pruebas + pipeline sobre los datos de data/.
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.12.13 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    MPLBACKEND=Agg \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Dependencias primero (capa cacheable), con las versiones exactas de uv.lock
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

COPY phantom ./phantom
COPY tests ./tests
COPY data ./data
COPY appeears ./appeears
RUN uv sync --frozen

# Las pruebas corren en el build: si fallan, la imagen no se construye.
RUN uv run --frozen --no-sync pytest -q

# Escribe todo en /app/out: results/, figures/ y RESULTS.md. Montar /app/out para verlo en el host.
# Para incluir MODIS, montar también /app/data/appeears (ver README).
CMD ["uv", "run", "--frozen", "--no-sync", "python", "-m", "phantom.pipeline", \
     "--out", "out/results", "--figures", "out/figures", "--results-md", "out/RESULTS.md"]
