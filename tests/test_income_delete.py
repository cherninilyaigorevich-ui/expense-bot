import asyncio
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from app.database.repository import (
    get_recent_budget_incomes,
    get_user_income,
    soft_delete_income,
)


def run(coro):
    return asyncio.run(coro)


def test_delete_rejects_another_users_income():
    session = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    session.execute.return_value = result

    with patch(
        "app.database.repository.SessionFactory"
    ) as factory:
        factory.return_value.__aenter__.return_value = session

        deleted = run(soft_delete_income(
            income_id=10,
            budget_id=1,
            telegram_user_id=999,
        ))

    assert deleted is False
    session.commit.assert_not_awaited()


def test_delete_marks_income_as_deleted():
    income = SimpleNamespace(
        is_deleted=False,
        deleted_at=None,
    )
    session = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = income
    session.execute.return_value = result

    with patch(
        "app.database.repository.SessionFactory"
    ) as factory:
        factory.return_value.__aenter__.return_value = session

        deleted = run(soft_delete_income(10, 1, 123))

    assert deleted is True
    assert income.is_deleted is True
    assert income.deleted_at is not None
    session.commit.assert_awaited_once()


def test_income_queries_exclude_deleted():
    from sqlalchemy import select
    from app.database.models import Income

    query = (
        select(Income)
        .where(
            Income.budget_id == 1,
            Income.is_deleted.is_(False),
        )
    )

    sql = str(query.compile())
    assert "incomes.is_deleted IS false" in sql
