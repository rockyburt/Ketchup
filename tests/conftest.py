import asyncio
import uuid
from urllib.parse import urlparse, urlunparse

import pytest
from sqlalchemy import pool, text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_scoped_session,
    create_async_engine,
)
from sqlalchemy.orm import close_all_sessions, sessionmaker

from ketchup import __version__, base, sqlamodels


def test_version():
    assert __version__ == "0.1.0"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def session_monkeypatch():
    mpatch = pytest.MonkeyPatch()
    yield mpatch
    mpatch.undo()


@pytest.fixture(scope="session")
async def empty_db(session_monkeypatch: pytest.MonkeyPatch):
    parsed = urlparse(base.config.DB_URI)
    dbname = parsed.path[1:] + "_test_" + uuid.uuid4().hex

    newuri = urlunparse([parsed[0], parsed[1], "/template1", parsed[3], parsed[4], parsed[5]])

    anony_engine = create_async_engine(
        newuri,
        future=True,
        poolclass=pool.NullPool,
        isolation_level="AUTOCOMMIT",
    )

    async with anony_engine.connect() as conn:
        await (await conn.execution_options(isolation_level="AUTOCOMMIT")).execute(text(f"CREATE DATABASE {dbname}"))

    async_engine = None
    async_session_factory = None
    make_session = None
    try:
        newuri = urlunparse([parsed[0], parsed[1], "/" + dbname, parsed[3], parsed[4], parsed[5]])
        async_engine = create_async_engine(newuri, future=True)
        async_session_factory = sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
        make_session = async_scoped_session(async_session_factory, scopefunc=asyncio.current_task)
        session_monkeypatch.setattr(sqlamodels, "make_session", make_session)

        async with async_engine.begin() as conn:
            await conn.run_sync(sqlamodels.mapper_registry.metadata.create_all)

        yield
    finally:
        close_all_sessions()
        if async_engine is not None:
            try:
                await async_engine.dispose()
            except Exception:
                ...
        async with anony_engine.connect() as conn:
            await (await conn.execution_options(isolation_level="AUTOCOMMIT")).execute(text(f"DROP DATABASE {dbname}"))
