# Imagem da API FastAPI (issue #15: esqueleto andante nginx -> api -> postgres).
# Build context = raiz do repo. uv gerencia as dependencias (uv.lock no contexto).
FROM python:3.13-slim

# uv estatico, copiado da imagem oficial.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ENV UV_PROJECT_ENVIRONMENT=/usr/local \
    UV_COMPILE_BYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dependencias primeiro (camada cacheavel). Sem dev deps e sem instalar o proprio projeto.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Codigo da aplicacao.
COPY backend ./backend

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--app-dir", "backend", "--host", "0.0.0.0", "--port", "8000"]
