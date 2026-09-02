from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import router

app = FastAPI(
    title="TG Source Radar",
    description="Telegram Source Discovery Engine",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health")
async def health():
    from app.config import get_settings
    from app.database import _get_engine

    status = {"status": "ok", "checks": {}}

    settings = get_settings()

    try:
        engine = _get_engine()
        async with engine.connect() as conn:
            await conn.execute(
                __import__("sqlalchemy").text("SELECT 1")
            )
        status["checks"]["database"] = "ok"
    except Exception as e:
        status["checks"]["database"] = f"error: {type(e).__name__}"
        status["status"] = "degraded"

    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(settings.redis_url, socket_timeout=3)
        await r.ping()
        await r.aclose()
        status["checks"]["redis"] = "ok"
    except Exception as e:
        status["checks"]["redis"] = f"error: {type(e).__name__}"
        status["status"] = "degraded"

    return status
