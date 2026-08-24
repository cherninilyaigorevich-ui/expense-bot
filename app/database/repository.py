from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select

from app.database.models import (
    Budget,
    BudgetMember,
    Expense,
)
from app.database.session import SessionFactory


async def create_expense(
    telegram_user_id: int,
    telegram_chat_id: int,
    message_thread_id: int | None,
    category: str,
    amount: Decimal,
    expense_date: date,
    budget_id: int | None = None,
) -> Expense:
    """Создать новый расход."""

    async with SessionFactory() as session:
        expense = Expense(
            telegram_user_id=telegram_user_id,
            telegram_chat_id=telegram_chat_id,
            message_thread_id=message_thread_id,
            budget_id=budget_id,
            category=category,
            amount=amount,
            expense_date=expense_date,
        )

        session.add(expense)

        await session.commit()
        await session.refresh(expense)

        return expense


async def create_budget(
    name: str,
) -> Budget:
    """Создать бюджет."""

    async with SessionFactory() as session:
        budget = Budget(
            name=name,
        )

        session.add(budget)

        await session.commit()
        await session.refresh(budget)

        return budget


async def get_budget(
    budget_id: int,
) -> Budget | None:
    """Получить бюджет по ID."""

    async with SessionFactory() as session:
        return await session.get(
            Budget,
            budget_id,
        )


async def add_budget_member(
    budget_id: int,
    telegram_user_id: int,
) -> BudgetMember:
    """Добавить пользователя в бюджет."""

    async with SessionFactory() as session:
        member = BudgetMember(
            budget_id=budget_id,
            telegram_user_id=telegram_user_id,
        )

        session.add(member)

        await session.commit()
        await session.refresh(member)

        return member


async def get_user_budget(
    telegram_user_id: int,
) -> Budget | None:
    """Найти бюджет пользователя."""

    async with SessionFactory() as session:
        query = (
            select(Budget)
            .join(
                BudgetMember,
                BudgetMember.budget_id == Budget.id,
            )
            .where(
                BudgetMember.telegram_user_id
                == telegram_user_id
            )
            .limit(1)
        )

        result = await session.execute(query)

        return result.scalar_one_or_none()


async def set_budget_dashboard(
    budget_id: int,
    telegram_chat_id: int,
    message_thread_id: int | None,
    dashboard_message_id: int,
) -> None:
    """Сохранить расположение dashboard бюджета."""

    async with SessionFactory() as session:
        budget = await session.get(
            Budget,
            budget_id,
        )

        if budget is None:
            raise ValueError(
                f"Budget {budget_id} not found"
            )

        budget.telegram_chat_id = telegram_chat_id
        budget.message_thread_id = message_thread_id
        budget.dashboard_message_id = dashboard_message_id

        await session.commit()


async def get_budget_statistics(
    budget_id: int,
    date_from: date,
    date_to: date,
) -> tuple[Decimal, int, list[tuple[str, Decimal]]]:
    """Получить статистику бюджета без удалённых расходов."""

    async with SessionFactory() as session:
        filters = [
            Expense.budget_id == budget_id,
            Expense.is_deleted.is_(False),
            Expense.expense_date >= date_from,
            Expense.expense_date <= date_to,
        ]

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


async def get_budget_total(
    budget_id: int,
    date_from: date,
    date_to: date,
) -> Decimal:
    """Получить сумму бюджета без удалённых расходов."""

    async with SessionFactory() as session:
        query = (
            select(
                func.coalesce(
                    func.sum(Expense.amount),
                    Decimal("0.00"),
                )
            )
            .where(
                Expense.budget_id == budget_id,
                Expense.is_deleted.is_(False),
                Expense.expense_date >= date_from,
                Expense.expense_date <= date_to,
            )
        )

        result = await session.execute(
            query
        )

        return Decimal(
            result.scalar_one()
        )


async def get_recent_user_expenses(
    budget_id: int,
    telegram_user_id: int,
    limit: int = 10,
) -> list[Expense]:
    """Получить последние неудалённые расходы пользователя."""

    async with SessionFactory() as session:
        query = (
            select(Expense)
            .where(
                Expense.budget_id == budget_id,
                Expense.telegram_user_id == telegram_user_id,
                Expense.is_deleted.is_(False),
            )
            .order_by(
                Expense.expense_date.desc(),
                Expense.id.desc(),
            )
            .limit(limit)
        )

        result = await session.execute(query)

        return list(
            result.scalars().all()
        )


async def get_user_expense(
    expense_id: int,
    budget_id: int,
    telegram_user_id: int,
) -> Expense | None:
    """Получить конкретный неудалённый расход пользователя."""

    async with SessionFactory() as session:
        query = (
            select(Expense)
            .where(
                Expense.id == expense_id,
                Expense.budget_id == budget_id,
                Expense.telegram_user_id == telegram_user_id,
                Expense.is_deleted.is_(False),
            )
            .limit(1)
        )

        result = await session.execute(query)

        return result.scalar_one_or_none()


async def soft_delete_expense(
    expense_id: int,
    budget_id: int,
    telegram_user_id: int,
) -> bool:
    """Пометить расход пользователя как удалённый."""

    async with SessionFactory() as session:
        query = (
            select(Expense)
            .where(
                Expense.id == expense_id,
                Expense.budget_id == budget_id,
                Expense.telegram_user_id == telegram_user_id,
                Expense.is_deleted.is_(False),
            )
            .limit(1)
        )

        result = await session.execute(query)
        expense = result.scalar_one_or_none()

        if expense is None:
            return False

        expense.is_deleted = True
        expense.deleted_at = datetime.now(
            timezone.utc
        )

        await session.commit()

        return True


# ============================================================
# LEGACY
# Пока оставляем старые функции до полного удаления
# chat_id/thread_id из модели расходов.
# ============================================================


async def get_expense_statistics(
    telegram_chat_id: int,
    message_thread_id: int | None,
    date_from: date,
    date_to: date,
) -> tuple[Decimal, int, list[tuple[str, Decimal]]]:
    """Legacy: статистика по Telegram-чату/топику."""

    async with SessionFactory() as session:
        filters = [
            Expense.telegram_chat_id == telegram_chat_id,
            Expense.is_deleted.is_(False),
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
                func.sum(Expense.amount).label("total"),
            )
            .where(*filters)
            .group_by(Expense.category)
            .order_by(
                func.sum(Expense.amount).desc()
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
    """Legacy: сумма по Telegram-чату/топику."""

    async with SessionFactory() as session:
        filters = [
            Expense.telegram_chat_id == telegram_chat_id,
            Expense.is_deleted.is_(False),
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

        result = await session.execute(query)

        return Decimal(
            result.scalar_one()
        )
