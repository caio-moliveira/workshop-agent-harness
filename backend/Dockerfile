# API FastAPI — imagem de runtime. Build context = raiz do repo (ver docker-compose.yml).
FROM python:3.13-slim

# uv para instalar as deps de forma reprodutível (a partir do uv.lock).
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_HTTP_TIMEOUT=120 \
    PYTHONUNBUFFERED=1

# Camada de deps primeiro (cache): só muda quando pyproject/uv.lock mudam.
# Cache mount + retry: o download do PyPI pode dropar a conexão (TLS reset); cada
# tentativa retoma do cache persistido até completar (ou falha após 5 rodadas).
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    sh -c 'for i in 1 2 3 4 5; do \
        uv sync --frozen --no-dev --no-install-project && exit 0; \
        echo "uv sync: tentativa $i falhou, repetindo em 5s..."; sleep 5; \
    done; exit 1'

# Código da aplicação.
COPY backend ./backend
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH=/app/backend

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
