from datetime import date
from decimal import Decimal

import pytest

from app.database.repository import (
    add_budget_member,
    create_budget,
    create_expense,
    get_budget_expenses_for_export,
)


@pytest.mark.asyncio
async def test_expense_comment_saved_and_retrieved():
    budget = await create_budget("Comments test")

    await add_budget_member(
        budget_id=budget.id,
        telegram_user_id=91001,
        display_name="Илья",
    )

    expense = await create_expense(
        telegram_user_id=91001,
        telegram_chat_id=91001,
        message_thread_id=None,
        budget_id=budget.id,
        category="food",
        amount=Decimal("850.00"),
        expense_date=date(2026, 10, 26),
        comment="Покупки на неделю",
    )

    assert expense.comment == "Покупки на неделю"

    rows = await get_budget_expenses_for_export(
        budget_id=budget.id,
        date_from=date(2026, 10, 26),
        date_to=date(2026, 10, 26),
    )

    assert len(rows) == 1
    assert rows[0].comment == "Покупки на неделю"
    assert rows[0].display_name == "Илья"


@pytest.mark.asyncio
async def test_excel_export_contains_comments(tmp_path, monkeypatch):
    from openpyxl import load_workbook
    import app.services.export as export_service

    monkeypatch.setattr(export_service, "EXPORT_DIR", tmp_path)

    budget = await create_budget("Excel comments test")

    await add_budget_member(
        budget_id=budget.id,
        telegram_user_id=92001,
        display_name="Илья",
    )

    for amount, comment in [
        ("850.00", "Покупки на неделю"),
        ("150.00", None),
    ]:
        await create_expense(
            telegram_user_id=92001,
            telegram_chat_id=92001,
            message_thread_id=None,
            budget_id=budget.id,
            category="food",
            amount=Decimal(amount),
            expense_date=date(2026, 10, 26),
            comment=comment,
        )

    path = await export_service.create_budget_xlsx(
        budget_id=budget.id,
        date_from=date(2026, 10, 26),
        date_to=date(2026, 10, 26),
    )

    workbook = load_workbook(path, data_only=True)
    try:
        sheet = workbook["Расходы"]

        assert sheet["E1"].value == "Комментарий"
        assert sheet["E2"].value == "Покупки на неделю"
        assert sheet["E3"].value is None
        assert sheet["C5"].value == 1000
    finally:
        workbook.close()
