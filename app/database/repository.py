from datetime import date
from decimal import Decimal

from sqlalchemy import func, select

from app.database.models import Expense
from app.database.session import SessionFactory


async def create_expense(
    telegram_user_id: int,
    telegram_chat_id: int,
    message_thread_id: int | None,
    category: str,
    amount: Decimal,
    expense_date: date,
) -> Expense:
    """Создать новый расход."""

    async with SessionFactory() as session:
        expense = Expense(
            telegram_user_id=telegram_user_id,
            telegram_chat_id=telegram_chat_id,
            message_thread_id=message_thread_id,
            category=category,
            amount=amount,
            expense_date=expense_date,
        )

        session.add(expense)

        await session.commit()
        await session.refresh(expense)

        return expense


async def get_expense_statistics(
    telegram_chat_id: int,
    message_thread_id: int | None,
    date_from: date,
    date_to: date,
) -> tuple[Decimal, int, list[tuple[str, Decimal]]]:
    """Получить статистику расходов за период."""

    async with SessionFactory() as session:
        filters = [
            Expense.telegram_chat_id == telegram_chat_id,
            Expense.expense_date >= date_from,
            Expense.expense_date <= date_to,
        ]

        if message_thread_id is None:
            filters.append(
                Expense.message_thread_id.is_(None)
            )
        else:
            filters.append(
                Expense.message_thread_id == message_thread_id
            )

        total_query = (
            select(
                func.coalesce(
                    func.sum(Expense.amount),
                    Decimal("0.00"),
                ),
                func.count(Expense.id),
            )
            .where(*filters)
        )

        total_result = await session.execute(
            total_query
        )

        total_amount, operations_count = (
            total_result.one()
        )

        categories_query = (
            select(
                Expense.category,
                func.sum(
                    Expense.amount
                ).label("total"),
            )
            .where(*filters)
            .group_by(
                Expense.category
            )
            .order_by(
                func.sum(
                    Expense.amount
                ).desc()
            )
        )

        categories_result = await session.execute(
            categories_query
        )

        categories = [
            (category, amount)
            for category, amount
            in categories_result.all()
        ]

        return (
            Decimal(total_amount),
            operations_count,
            categories,
        )


async def get_month_total(
    telegram_chat_id: int,
    message_thread_id: int | None,
    date_from: date,
    date_to: date,
) -> Decimal:
    """Получить общую сумму расходов за период."""

    async with SessionFactory() as session:
        filters = [
            Expense.telegram_chat_id == telegram_chat_id,
            Expense.expense_date >= date_from,
            Expense.expense_date <= date_to,
        ]

        if message_thread_id is None:
            filters.append(
                Expense.message_thread_id.is_(None)
            )
        else:
            filters.append(
                Expense.message_thread_id == message_thread_id
            )

        query = (
            select(
                func.coalesce(
                    func.sum(Expense.amount),
                    Decimal("0.00"),
                )
            )
            .where(*filters)
        )

        result = await session.execute(
            query
        )

        return Decimal(
            result.scalar_one()
        )
