from datetime import date
from decimal import Decimal

import pytest

from app.database.repository import (
    add_budget_member,
    create_budget,
    create_expense,
    get_budget_statistics,
    get_recent_user_expenses,
    mark_month_archived,
    soft_delete_expense,
    delete_archived_month_expenses,
)


pytestmark = pytest.mark.asyncio


async def test_soft_delete_hides_expense():
    budget = await create_budget(
        "Test budget"
    )

    await add_budget_member(
        budget_id=budget.id,
        telegram_user_id=1001,
        display_name="User 1",
    )

    expense = await create_expense(
        telegram_user_id=1001,
        telegram_chat_id=1001,
        message_thread_id=None,
        budget_id=budget.id,
        category="food",
        amount=Decimal("100.00"),
        expense_date=date(2026, 8, 10),
    )

    deleted = await soft_delete_expense(
        expense_id=expense.id,
        budget_id=budget.id,
        telegram_user_id=1001,
    )

    assert deleted is True

    recent = await get_recent_user_expenses(
        budget_id=budget.id,
        telegram_user_id=1001,
    )

    assert recent == []


async def test_user_cannot_delete_another_users_expense():
    budget = await create_budget(
        "Test budget"
    )

    await add_budget_member(
        budget_id=budget.id,
        telegram_user_id=2001,
        display_name="User 1",
    )

    await add_budget_member(
        budget_id=budget.id,
        telegram_user_id=2002,
        display_name="User 2",
    )

    expense = await create_expense(
        telegram_user_id=2001,
        telegram_chat_id=2001,
        message_thread_id=None,
        budget_id=budget.id,
        category="food",
        amount=Decimal("200.00"),
        expense_date=date(2026, 8, 11),
    )

    deleted = await soft_delete_expense(
        expense_id=expense.id,
        budget_id=budget.id,
        telegram_user_id=2002,
    )

    assert deleted is False

    recent = await get_recent_user_expenses(
        budget_id=budget.id,
        telegram_user_id=2001,
    )

    assert len(recent) == 1
    assert recent[0].id == expense.id


async def test_statistics_ignore_deleted_expenses():
    budget = await create_budget(
        "Test budget"
    )

    await add_budget_member(
        budget_id=budget.id,
        telegram_user_id=3001,
        display_name="User 1",
    )

    expense_1 = await create_expense(
        telegram_user_id=3001,
        telegram_chat_id=3001,
        message_thread_id=None,
        budget_id=budget.id,
        category="food",
        amount=Decimal("100.00"),
        expense_date=date(2026, 8, 12),
    )

    await create_expense(
        telegram_user_id=3001,
        telegram_chat_id=3001,
        message_thread_id=None,
        budget_id=budget.id,
        category="cafe",
        amount=Decimal("300.00"),
        expense_date=date(2026, 8, 12),
    )

    await soft_delete_expense(
        expense_id=expense_1.id,
        budget_id=budget.id,
        telegram_user_id=3001,
    )

    total, count, categories = await get_budget_statistics(
        budget_id=budget.id,
        date_from=date(2026, 8, 1),
        date_to=date(2026, 8, 31),
    )

    assert total == Decimal("300.00")
    assert count == 1
    assert categories == [
        ("cafe", Decimal("300.00"))
    ]


async def test_retention_does_not_delete_unarchived_month():
    budget = await create_budget(
        "Test budget"
    )

    await add_budget_member(
        budget_id=budget.id,
        telegram_user_id=4001,
        display_name="User 1",
    )

    await create_expense(
        telegram_user_id=4001,
        telegram_chat_id=4001,
        message_thread_id=None,
        budget_id=budget.id,
        category="home",
        amount=Decimal("500.00"),
        expense_date=date(2026, 4, 10),
    )

    deleted_rows = await delete_archived_month_expenses(
        budget_id=budget.id,
        year=2026,
        month=4,
    )

    assert deleted_rows == 0

    recent = await get_recent_user_expenses(
        budget_id=budget.id,
        telegram_user_id=4001,
    )

    assert len(recent) == 1


async def test_retention_deletes_archived_month():
    budget = await create_budget(
        "Test budget"
    )

    await add_budget_member(
        budget_id=budget.id,
        telegram_user_id=5001,
        display_name="User 1",
    )

    await create_expense(
        telegram_user_id=5001,
        telegram_chat_id=5001,
        message_thread_id=None,
        budget_id=budget.id,
        category="transport",
        amount=Decimal("750.00"),
        expense_date=date(2026, 4, 15),
    )

    await mark_month_archived(
        budget_id=budget.id,
        year=2026,
        month=4,
    )

    deleted_rows = await delete_archived_month_expenses(
        budget_id=budget.id,
        year=2026,
        month=4,
    )

    assert deleted_rows == 1

    recent = await get_recent_user_expenses(
        budget_id=budget.id,
        telegram_user_id=5001,
    )

    assert recent == []
