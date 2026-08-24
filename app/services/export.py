from datetime import date
from decimal import Decimal
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter

from app.constants import CATEGORY_NAMES
from app.database.repository import (
    get_budget_expenses_for_export,
)


EXPORT_DIR = Path("/opt/expense-bot/exports")


def money_to_excel(amount: Decimal) -> float:
    return float(amount)


async def create_budget_xlsx(
    budget_id: int,
    date_from: date,
    date_to: date,
) -> Path:
    """Создать XLSX-отчёт семейного бюджета."""

    expenses = await get_budget_expenses_for_export(
        budget_id=budget_id,
        date_from=date_from,
        date_to=date_to,
    )

    EXPORT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    filename = (
        f"expenses_"
        f"{date_from.isoformat()}_"
        f"{date_to.isoformat()}.xlsx"
    )

    file_path = EXPORT_DIR / filename

    workbook = Workbook()

    sheet = workbook.active
    sheet.title = "Расходы"

    headers = [
        "Дата",
        "Категория",
        "Сумма",
        "Кто добавил",
    ]

    sheet.append(headers)

    for cell in sheet[1]:
        cell.font = Font(
            bold=True,
        )

        cell.alignment = Alignment(
            horizontal="center",
        )

    total_amount = Decimal("0.00")

    for expense in expenses:
        category_name = CATEGORY_NAMES.get(
            expense.category,
            expense.category,
        )

        sheet.append(
            [
                expense.expense_date.strftime(
                    "%d.%m.%Y"
                ),
                category_name,
                money_to_excel(expense.amount),
                expense.display_name,
            ]
        )

        total_amount += expense.amount

    sheet.append([])

    sheet.append(
        [
            "",
            "ИТОГО",
            money_to_excel(total_amount),
            "",
        ]
    )

    total_row = sheet.max_row

    sheet.cell(
        row=total_row,
        column=2,
    ).font = Font(
        bold=True,
    )

    sheet.cell(
        row=total_row,
        column=3,
    ).font = Font(
        bold=True,
    )

    for row_number in range(
        2,
        total_row + 1,
    ):
        sheet.cell(
            row=row_number,
            column=3,
        ).number_format = '#,##0.00'

    column_widths = {
        1: 15,
        2: 30,
        3: 18,
        4: 22,
    }

    for column_number, width in column_widths.items():
        sheet.column_dimensions[
            get_column_letter(column_number)
        ].width = width

    sheet.freeze_panes = "A2"

    workbook.save(
        file_path
    )

    return file_path
