import asyncio
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from openpyxl import Workbook

from app.services.archive import write_month_to_sheet, append_income_summary


def test_month_archive_with_incomes():
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "2026"

    expenses = [
        SimpleNamespace(
            expense_date=date(2026, 10, 20),
            category="food",
            amount=Decimal("5000.00"),
            display_name="Илья",
            comment="Продукты",
        )
    ]

    incomes = [
        SimpleNamespace(
            income_date=date(2026, 10, 21),
            category="ilya",
            amount=Decimal("150000.00"),
            display_name="Илья",
            comment="Зарплата",
        ),
        SimpleNamespace(
            income_date=date(2026, 10, 22),
            category="liza",
            amount=Decimal("80000.00"),
            display_name="Лиза",
            comment="Зарплата",
        ),
    ]

    async def run():
        with (
            patch(
                "app.services.archive.get_budget_expenses_for_export",
                new_callable=AsyncMock,
                return_value=expenses,
            ),
            patch(
                "app.services.archive.get_budget_incomes_for_export",
                new_callable=AsyncMock,
                return_value=incomes,
            ),
        ):
            await write_month_to_sheet(sheet, 1, 2026, 10)
            await append_income_summary(sheet, 1, 2026, 10)

    asyncio.run(run())

    values = [
        cell.value
        for row in sheet.iter_rows()
        for cell in row
        if cell.value is not None
    ]

    assert "MONTH:2026-10" in values
    assert "ДОХОДЫ" in values
    assert "Илья" in values
    assert "Лиза" in values
    assert "ВСЕГО ДОХОДОВ" in values
    assert "ВСЕГО РАСХОДОВ" in values
    assert "БАЛАНС" in values
    assert 230000.0 in values
    assert 5000.0 in values
    assert 225000.0 in values

    workbook.close()
