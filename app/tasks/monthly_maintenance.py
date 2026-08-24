import asyncio
from datetime import date

from app.services.archive import update_month_archive
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
    today = date.today()

    year, month = previous_month(
        today
    )

    print(
        f"Archiving {year}-{month:02d}..."
    )

    file_id = await update_month_archive(
        budget_id=FAMILY_BUDGET_ID,
        year=year,
        month=month,
    )

    print(
        f"Archive successfully updated. "
        f"Google Drive file ID: {file_id}"
    )

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
