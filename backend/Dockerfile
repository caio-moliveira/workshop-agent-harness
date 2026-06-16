# Imagem do serviço FastAPI (api). Build context = raiz do repo (ver docker-compose.yml).
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

RUN pip install --no-cache-dir uv

# Deps de runtime (espelham as deps de produção do pyproject.toml).
RUN uv pip install --system --no-cache \
    fastapi \
    "uvicorn[standard]" \
    "sqlalchemy[asyncio]" \
    asyncpg \
    pydantic \
    pydantic-settings

COPY backend ./backend
WORKDIR /app/backend

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
