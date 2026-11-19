"""Test setup. Run inside the backend container: docker compose exec backend pytest -q

Tests use their own database (experiment_test) on the same Postgres, so they never
touch the live app's data. DATABASE_URL must be switched before `app` is imported.
"""
import asyncio
import os

import asyncpg
import pytest


def _use_test_database() -> None:
    url = os.environ["DATABASE_URL"]
    prefix, _, _ = url.rpartition("/")
    os.environ["DATABASE_URL"] = f"{prefix}/experiment_test"

    admin_dsn = prefix.replace("postgresql+asyncpg://", "postgresql://") + "/postgres"

    async def create_if_missing() -> None:
        conn = await asyncpg.connect(admin_dsn)
        try:
            if not await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = 'experiment_test'"):
                await conn.execute('CREATE DATABASE "experiment_test"')
        finally:
            await conn.close()

    asyncio.run(create_if_missing())


_use_test_database()


@pytest.fixture(scope="session")
def loop():
    # One event loop for the whole session: the async DB engine pools connections per loop.
    lp = asyncio.new_event_loop()
    yield lp
    from app import db

    lp.run_until_complete(db.engine.dispose())
    lp.close()


@pytest.fixture(scope="session")
def run(loop):
    return loop.run_until_complete


@pytest.fixture(scope="session")
def schema(run):
    """Create tables and start from empty ones."""
    from sqlalchemy import text

    from app import db

    async def setup() -> None:
        await db.init_db()
        async with db.engine.begin() as conn:
            await conn.execute(text("TRUNCATE votes, messages, participants, sessions CASCADE"))

    run(setup())
