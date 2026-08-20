from datetime import date
from decimal import Decimal

from app.database.models import Expense
from app.database.session import SessionFactory


async def create_expense(
    telegram_user_id: int,
    telegram_chat_id: int,
    category: str,
    amount: Decimal,
    expense_date: date,
) -> Expense:
    async with SessionFactory() as session:
        expense = Expense(
            telegram_user_id=telegram_user_id,
            telegram_chat_id=telegram_chat_id,
            category=category,
            amount=amount,
            expense_date=expense_date,
        )

        session.add(expense)

        await session.commit()
        await session.refresh(expense)

        return expense
