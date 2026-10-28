import asyncio
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from openpyxl import Workbook

from app.services.archive import (
    append_income_summary,
    write_month_to_sheet,
)


def test_repeated_month_archive_does_not_duplicate_income():
    workbook = Workbook()
    sheet = workbook.active

    incomes = [
        SimpleNamespace(
            income_date=date(2026, 10, 21),
            category="ilya",
            amount=Decimal("150000.00"),
            display_name="Илья",
            comment="Зарплата",
        )
    ]

    async def run():
        with (
            patch(
                "app.services.archive.get_budget_expenses_for_export",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.services.archive.get_budget_incomes_for_export",
                new_callable=AsyncMock,
                return_value=incomes,
            ),
        ):
            for _ in range(2):
                await write_month_to_sheet(sheet, 1, 2026, 10)
                await append_income_summary(sheet, 1, 2026, 10)

    asyncio.run(run())

    values = [
        cell.value
        for row in sheet.iter_rows()
        for cell in row
    ]

    assert values.count("MONTH:2026-10") == 1
    assert values.count("ДОХОДЫ") == 1
    assert values.count("ВСЕГО ДОХОДОВ") == 1

    workbook.close()
