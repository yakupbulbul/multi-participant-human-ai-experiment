import asyncio
import logging
import os

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

log = logging.getLogger("uvicorn.error")

DATABASE_URL = os.environ["DATABASE_URL"]

engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def init_db(retries: int = 30, delay_s: float = 1.0) -> None:
    """Create tables if missing (no Alembic: deliberate 4-hour trade-off).

    Retries because Postgres may still be starting even with the compose healthcheck.
    """
    from .models import Base

    for attempt in range(1, retries + 1):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            log.info("schema ready")
            return
        except Exception as exc:
            if attempt == retries:
                raise
            log.warning("db not ready (attempt %d/%d): %s", attempt, retries, exc)
            await asyncio.sleep(delay_s)


async def ping() -> bool:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
