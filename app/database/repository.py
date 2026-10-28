from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import delete, func, select

from app.database.models import (
    ArchiveMonth,
    Budget,
    BudgetMember,
    Expense,
    Income,
)
from app.database.session import SessionFactory


@dataclass
class ExpenseExportRow:
    """Строка расхода для XLSX-экспорта."""

    expense_date: date
    category: str
    amount: Decimal
    display_name: str
    comment: str | None



@dataclass
class RecentExpenseRow:
    """Последний расход семейного бюджета."""

    id: int
    telegram_user_id: int
    expense_date: date
    category: str
    amount: Decimal
    display_name: str


async def create_expense(
    telegram_user_id: int,
    telegram_chat_id: int,
    message_thread_id: int | None,
    category: str,
    amount: Decimal,
    expense_date: date,
    budget_id: int | None = None,
    comment: str | None = None,
) -> Expense:
    """Создать новый расход."""

    async with SessionFactory() as session:
        expense = Expense(
            comment=comment,
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
    """Создать новый бюджет."""

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
    display_name: str | None = None,
) -> BudgetMember:
    """Добавить Telegram-пользователя в бюджет."""

    async with SessionFactory() as session:
        member = BudgetMember(
            budget_id=budget_id,
            telegram_user_id=telegram_user_id,
            display_name=display_name,
        )

        session.add(member)

        await session.commit()
        await session.refresh(member)

        return member


async def get_user_budget(
    telegram_user_id: int,
) -> Budget | None:
    """Получить бюджет пользователя."""

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

        result = await session.execute(
            query
        )

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
) -> tuple[
    Decimal,
    int,
    list[tuple[str, Decimal]],
]:
    """Получить статистику бюджета за период."""

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
            (
                category,
                Decimal(amount),
            )
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
    """Получить общую сумму расходов бюджета."""

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


async def count_budget_expenses(
    budget_id: int,
    date_from: date,
    date_to: date,
) -> int:
    """Посчитать активные расходы бюджета за период."""

    async with SessionFactory() as session:
        query = (
            select(
                func.count(Expense.id)
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

        return int(
            result.scalar_one()
        )


async def get_budget_expenses(
    budget_id: int,
    date_from: date,
    date_to: date,
) -> list[Expense]:
    """Получить активные расходы бюджета за период."""

    async with SessionFactory() as session:
        query = (
            select(Expense)
            .where(
                Expense.budget_id == budget_id,
                Expense.is_deleted.is_(False),
                Expense.expense_date >= date_from,
                Expense.expense_date <= date_to,
            )
            .order_by(
                Expense.expense_date.asc(),
                Expense.id.asc(),
            )
        )

        result = await session.execute(
            query
        )

        return list(
            result.scalars().all()
        )


async def get_budget_expenses_for_export(
    budget_id: int,
    date_from: date,
    date_to: date,
) -> list[ExpenseExportRow]:
    """Получить расходы бюджета с именами участников."""

    async with SessionFactory() as session:
        query = (
            select(
                Expense.expense_date,
                Expense.category,
                Expense.amount,
                BudgetMember.display_name,
                Expense.comment,
            )
            .join(
                BudgetMember,
                (
                    BudgetMember.budget_id
                    == Expense.budget_id
                )
                & (
                    BudgetMember.telegram_user_id
                    == Expense.telegram_user_id
                ),
            )
            .where(
                Expense.budget_id == budget_id,
                Expense.is_deleted.is_(False),
                Expense.expense_date >= date_from,
                Expense.expense_date <= date_to,
            )
            .order_by(
                Expense.expense_date.asc(),
                Expense.id.asc(),
            )
        )

        result = await session.execute(
            query
        )

        return [
            ExpenseExportRow(
                expense_date=row.expense_date,
                category=row.category,
                amount=Decimal(row.amount),
                comment=row.comment,
                display_name=(
                    row.display_name
                    or "Неизвестный участник"
                ),
            )
            for row in result.all()
        ]


async def get_recent_budget_expenses(
    budget_id: int,
    date_from: date,
    date_to: date,
) -> list[RecentExpenseRow]:
    """Получить расходы всех участников бюджета за период."""

    async with SessionFactory() as session:
        query = (
            select(
                Expense.id,
                Expense.telegram_user_id,
                Expense.expense_date,
                Expense.category,
                Expense.amount,
                BudgetMember.display_name,
            )
            .join(
                BudgetMember,
                (
                    BudgetMember.budget_id
                    == Expense.budget_id
                )
                & (
                    BudgetMember.telegram_user_id
                    == Expense.telegram_user_id
                ),
            )
            .where(
                Expense.budget_id == budget_id,
                Expense.is_deleted.is_(False),
                Expense.expense_date >= date_from,
                Expense.expense_date <= date_to,
            )
            .order_by(
                Expense.expense_date.desc(),
                Expense.id.desc(),
            )
        )

        result = await session.execute(query)

        return [
            RecentExpenseRow(
                id=row.id,
                telegram_user_id=row.telegram_user_id,
                expense_date=row.expense_date,
                category=row.category,
                amount=Decimal(row.amount),
                display_name=(
                    row.display_name
                    or "Неизвестный участник"
                ),
            )
            for row in result.all()
        ]


async def get_user_expense(
    expense_id: int,
    budget_id: int,
    telegram_user_id: int,
) -> Expense | None:
    """Получить конкретный расход пользователя."""

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

        result = await session.execute(
            query
        )

        return result.scalar_one_or_none()


async def soft_delete_expense(
    expense_id: int,
    budget_id: int,
    telegram_user_id: int,
) -> bool:
    """Пометить расход как удалённый."""

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

        result = await session.execute(
            query
        )

        expense = result.scalar_one_or_none()

        if expense is None:
            return False

        expense.is_deleted = True
        expense.deleted_at = datetime.now(
            timezone.utc
        )

        await session.commit()

        return True


async def mark_month_archived(
    budget_id: int,
    year: int,
    month: int,
) -> None:
    """Зафиксировать успешную архивацию месяца."""

    async with SessionFactory() as session:
        query = (
            select(ArchiveMonth)
            .where(
                ArchiveMonth.budget_id == budget_id,
                ArchiveMonth.year == year,
                ArchiveMonth.month == month,
            )
            .limit(1)
        )

        result = await session.execute(
            query
        )

        archive = result.scalar_one_or_none()

        if archive is None:
            archive = ArchiveMonth(
                budget_id=budget_id,
                year=year,
                month=month,
            )

            session.add(archive)

        else:
            archive.archived_at = datetime.now(
                timezone.utc
            )

        archive.incomes_archived_at = datetime.now(timezone.utc)

        await session.commit()


async def is_month_archived(
    budget_id: int,
    year: int,
    month: int,
) -> bool:
    """Проверить, архивирован ли месяц."""

    async with SessionFactory() as session:
        query = (
            select(ArchiveMonth.id)
            .where(
                ArchiveMonth.budget_id == budget_id,
                ArchiveMonth.year == year,
                ArchiveMonth.month == month,
            )
            .limit(1)
        )

        result = await session.execute(
            query
        )

        return (
            result.scalar_one_or_none()
            is not None
        )


async def delete_archived_month_expenses(
    budget_id: int,
    year: int,
    month: int,
) -> int:
    """Физически удалить расходы архивированного месяца."""

    archived = await is_month_archived(
        budget_id=budget_id,
        year=year,
        month=month,
    )

    if not archived:
        return 0

    date_from = date(
        year,
        month,
        1,
    )

    if month == 12:
        date_to = date(
            year + 1,
            1,
            1,
        )
    else:
        date_to = date(
            year,
            month + 1,
            1,
        )

    async with SessionFactory() as session:
        query = (
            delete(Expense)
            .where(
                Expense.budget_id == budget_id,
                Expense.expense_date >= date_from,
                Expense.expense_date < date_to,
            )
        )

        result = await session.execute(
            query
        )

        await session.commit()

        return result.rowcount or 0


async def create_income(
    telegram_user_id: int,
    telegram_chat_id: int,
    message_thread_id: int | None,
    budget_id: int,
    category: str,
    amount: Decimal,
    income_date: date,
    comment: str | None = None,
) -> Income:
    """Создать доход семейного бюджета."""
    async with SessionFactory() as session:
        income = Income(
            telegram_user_id=telegram_user_id,
            telegram_chat_id=telegram_chat_id,
            message_thread_id=message_thread_id,
            budget_id=budget_id,
            category=category,
            amount=amount,
            income_date=income_date,
            comment=comment,
        )
        session.add(income)
        await session.commit()
        await session.refresh(income)
        return income


@dataclass
class IncomeExportRow:
    income_date: date
    category: str
    amount: Decimal
    display_name: str
    comment: str | None


async def get_budget_incomes_for_export(
    budget_id: int,
    date_from: date,
    date_to: date,
) -> list[IncomeExportRow]:
    async with SessionFactory() as session:
        query = (
            select(
                Income.income_date,
                Income.category,
                Income.amount,
                BudgetMember.display_name,
                Income.comment,
            )
            .outerjoin(
                BudgetMember,
                (BudgetMember.budget_id == Income.budget_id)
                & (
                    BudgetMember.telegram_user_id
                    == Income.telegram_user_id
                ),
            )
            .where(
                Income.budget_id == budget_id,
                Income.is_deleted.is_(False),
                Income.income_date >= date_from,
                Income.income_date <= date_to,
            )
            .order_by(Income.income_date, Income.id)
        )

        result = await session.execute(query)

        return [
            IncomeExportRow(
                income_date=row.income_date,
                category=row.category,
                amount=Decimal(row.amount),
                display_name=row.display_name or "Неизвестный участник",
                comment=row.comment,
            )
            for row in result.all()
        ]


async def get_budget_income_statistics(
    budget_id: int,
    date_from: date,
    date_to: date,
) -> tuple[Decimal, int, list[tuple[str, Decimal]]]:
    async with SessionFactory() as session:
        filters = (
            Income.budget_id == budget_id,
            Income.is_deleted.is_(False),
            Income.income_date >= date_from,
            Income.income_date <= date_to,
        )

        result = await session.execute(
            select(
                func.coalesce(
                    func.sum(Income.amount), Decimal("0.00")
                ),
                func.count(Income.id),
            ).where(*filters)
        )

        total, count = result.one()

        result = await session.execute(
            select(Income.category, func.sum(Income.amount))
            .where(*filters)
            .group_by(Income.category)
            .order_by(Income.category)
        )

        return (
            Decimal(total),
            int(count),
            [
                (category, Decimal(amount))
                for category, amount in result.all()
            ],
        )


async def count_budget_incomes(
    budget_id: int,
    date_from: date,
    date_to: date,
) -> int:
    async with SessionFactory() as session:
        result = await session.execute(
            select(func.count(Income.id)).where(
                Income.budget_id == budget_id,
                Income.is_deleted.is_(False),
                Income.income_date >= date_from,
                Income.income_date <= date_to,
            )
        )
        return int(result.scalar_one())


async def delete_archived_month_incomes(
    budget_id: int,
    year: int,
    month: int,
) -> int:
    """Удалять доходы только после их успешной архивации."""
    start = date(year, month, 1)
    end = (
        date(year + 1, 1, 1)
        if month == 12
        else date(year, month + 1, 1)
    )

    async with SessionFactory() as session:
        result = await session.execute(
            select(ArchiveMonth.id).where(
                ArchiveMonth.budget_id == budget_id,
                ArchiveMonth.year == year,
                ArchiveMonth.month == month,
                ArchiveMonth.incomes_archived_at.is_not(None),
            )
        )

        if result.scalar_one_or_none() is None:
            return 0

        deleted = await session.execute(
            delete(Income).where(
                Income.budget_id == budget_id,
                Income.income_date >= start,
                Income.income_date < end,
            )
        )

        await session.commit()
        return deleted.rowcount or 0
