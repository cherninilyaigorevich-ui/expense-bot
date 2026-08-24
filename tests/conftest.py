import pytest
import pytest_asyncio

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.config import TEST_DATABASE_URL
from app.database.base import Base

import app.database.models  # noqa: F401
import app.database.repository as repository


if not TEST_DATABASE_URL:
    raise RuntimeError(
        "TEST_DATABASE_URL is not configured"
    )


if not TEST_DATABASE_URL.endswith(
    "/expenses_test"
):
    raise RuntimeError(
        "Refusing to run tests: "
        "TEST_DATABASE_URL must point to expenses_test"
    )


test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    poolclass=NullPool,
)


TestSessionFactory = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest_asyncio.fixture(
    scope="session",
    autouse=True,
)
async def prepare_test_database():
    """Создать чистую схему test DB перед тестами."""

    async with test_engine.begin() as conn:
        await conn.run_sync(
            Base.metadata.drop_all
        )

        await conn.run_sync(
            Base.metadata.create_all
        )

    yield

    async with test_engine.begin() as conn:
        await conn.run_sync(
            Base.metadata.drop_all
        )

    await test_engine.dispose()


@pytest.fixture(
    autouse=True,
)
def use_test_session_factory(
    monkeypatch,
):
    """Подменить production SessionFactory на test DB."""

    monkeypatch.setattr(
        repository,
        "SessionFactory",
        TestSessionFactory,
    )
