import asyncio
from datetime import date

from app.dates import local_today
from app.database.repository import count_budget_expenses, count_budget_incomes
from app.services.archive import (
    get_month_bounds,
    update_month_archive,
)
from app.services.retention import cleanup_old_expenses


FAMILY_BUDGET_ID = 1


def previous_month(
    today: date,
) -> tuple[int, int]:
    if today.month == 1:
        return (
            today.year - 1,
            12,
        )

    return (
        today.year,
        today.month - 1,
    )


async def main() -> None:
    today = local_today()

    year, month = previous_month(
        today
    )

    date_from, date_to = get_month_bounds(
        year=year,
        month=month,
    )

    expenses_count = await count_budget_expenses(
        budget_id=FAMILY_BUDGET_ID,
        date_from=date_from,
        date_to=date_to,
    )

    incomes_count = await count_budget_incomes(
        budget_id=FAMILY_BUDGET_ID,
        date_from=date_from,
        date_to=date_to,
    )

    if expenses_count == 0 and incomes_count == 0:
        print(
            f"Archive skipped: "
            f"{year}-{month:02d} has no expenses."
        )

    else:
        print(
            f"Archiving {year}-{month:02d} "
            f"({expenses_count} expenses, {incomes_count} incomes)..."
        )

        file_id = await update_month_archive(
            budget_id=FAMILY_BUDGET_ID,
            year=year,
            month=month,
        )

        print(
            "Archive successfully updated. "
            f"Google Drive file ID: {file_id}"
        )

    print("Running retention...")

    deleted = await cleanup_old_expenses(
        budget_id=FAMILY_BUDGET_ID,
        today=today,
    )

    if not deleted:
        print(
            "Retention: nothing to delete."
        )

    for (
        deleted_year,
        deleted_month,
        deleted_rows,
    ) in deleted:
        print(
            "Retention: "
            f"{deleted_year}-{deleted_month:02d}, "
            f"deleted rows={deleted_rows}"
        )


if __name__ == "__main__":
    asyncio.run(main())
