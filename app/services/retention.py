from datetime import date

from app.database.repository import (
    delete_archived_month_expenses,
    is_month_archived,
)


RETENTION_MONTHS = 3


def subtract_months(
    year: int,
    month: int,
    months: int,
) -> tuple[int, int]:
    """Вычесть указанное количество календарных месяцев."""

    total_months = (
        year * 12
        + (month - 1)
        - months
    )

    result_year = total_months // 12
    result_month = total_months % 12 + 1

    return result_year, result_month


async def cleanup_old_expenses(
    budget_id: int,
    today: date | None = None,
) -> list[tuple[int, int, int]]:
    """Удалить архивированные месяцы старше retention.

    Возвращает:
    [(year, month, deleted_rows), ...]
    """

    if today is None:
        today = date.today()

    # Если сейчас август и RETENTION_MONTHS=3,
    # храним июнь, июль, август.
    # Значит май и всё более старое можно удалить.
    cutoff_year, cutoff_month = subtract_months(
        year=today.year,
        month=today.month,
        months=RETENTION_MONTHS,
    )

    deleted_months: list[
        tuple[int, int, int]
    ] = []

    # Начинаем с достаточно ранней даты.
    # Позже при необходимости заменим это запросом
    # к самой БД.
    start_year = 2026
    start_month = 1

    year = start_year
    month = start_month

    while (
        year < cutoff_year
        or (
            year == cutoff_year
            and month <= cutoff_month
        )
    ):
        archived = await is_month_archived(
            budget_id=budget_id,
            year=year,
            month=month,
        )

        if archived:
            deleted_rows = (
                await delete_archived_month_expenses(
                    budget_id=budget_id,
                    year=year,
                    month=month,
                )
            )

            deleted_months.append(
                (
                    year,
                    month,
                    deleted_rows,
                )
            )

        if month == 12:
            year += 1
            month = 1
        else:
            month += 1

    return deleted_months
