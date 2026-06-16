"""API FastAPI da Bussola (issue #15: esqueleto andante).

Por enquanto so o `/health`, que prova o hop nginx -> api -> postgres. As rotas de
negocio (`/chat`) chegam na issue #19.
"""

from fastapi import Depends, FastAPI, Response, status
from sqlalchemy.ext.asyncio import AsyncEngine

from app.db import get_engine, ping_db

app = FastAPI(title="Bussola API")


@app.get("/health")
async def health(
    response: Response,
    engine: AsyncEngine = Depends(get_engine),
) -> dict[str, str]:
    """Liveness + conectividade com o Postgres. Retorna 503 se o banco nao responder."""
    try:
        await ping_db(engine)
    except Exception:
        # Health check reporta qualquer falha de conexao como indisponivel (nao vaza o erro).
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "unhealthy", "database": "unreachable"}
    return {"status": "ok", "database": "ok"}
