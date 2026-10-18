FROM python:3.12-slim AS base
COPY --from=ghcr.io/astral-sh/uv:0.12.7 /uv /uvx /bin/
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
ENV UV_SYSTEM_CERTS=true PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY . .

FROM base AS test
RUN uv sync --frozen
CMD ["uv", "run", "--no-sync", "pytest", "-q"]

FROM base AS runtime
RUN uv sync --frozen --no-dev \
    && useradd --create-home --uid 10001 tracework \
    && mkdir -p /app/.data && chown -R tracework:tracework /app
USER tracework
EXPOSE 8765
HEALTHCHECK --interval=20s --timeout=3s --start-period=10s \
    CMD ["/app/.venv/bin/python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8765/api/health',timeout=2)"]
CMD ["/app/.venv/bin/tracework", "serve", "--host", "0.0.0.0"]
