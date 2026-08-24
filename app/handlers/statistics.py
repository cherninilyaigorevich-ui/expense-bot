from datetime import date, timedelta
from decimal import Decimal

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from app.constants import CATEGORY_NAMES
from app.database.repository import (
    get_budget_statistics,
    get_user_budget,
)
from app.keyboards.statistics import statistics_period_keyboard


router = Router()


def format_money(amount: Decimal) -> str:
    return f"{amount:,.2f}".replace(",", " ")


@router.message(F.text == "📊 Статистика")
async def statistics_handler(
    message: Message,
) -> None:
    if message.from_user is None:
        return

    budget = await get_user_budget(
        telegram_user_id=message.from_user.id,
    )

    if budget is None:
        await message.answer(
            "⛔ У вас нет доступа к семейному бюджету."
        )
        return

    await message.answer(
        "📊 Выбери период:",
        reply_markup=statistics_period_keyboard(),
    )


@router.callback_query(
    F.data.startswith("stats:")
)
async def statistics_period_handler(
    callback: CallbackQuery,
) -> None:
    if callback.data is None or callback.message is None:
        return

    budget = await get_user_budget(
        telegram_user_id=callback.from_user.id,
    )

    if budget is None:
        await callback.answer(
            "Нет доступа к семейному бюджету.",
            show_alert=True,
        )
        return

    period = callback.data.split(":", 1)[1]

    today = date.today()

    if period == "today":
        date_from = today
        date_to = today
        title = "сегодня"

    elif period == "week":
        date_from = today - timedelta(days=6)
        date_to = today
        title = "последние 7 дней"

    elif period == "month":
        date_from = today.replace(day=1)
        date_to = today
        title = "текущий месяц"

    else:
        await callback.answer(
            "Неизвестный период.",
            show_alert=True,
        )
        return

    await callback.answer()

    total_amount, operations_count, categories = (
        await get_budget_statistics(
            budget_id=budget.id,
            date_from=date_from,
            date_to=date_to,
        )
    )

    if operations_count == 0:
        await callback.message.answer(
            f"📊 За {title} расходов пока нет."
        )
        return

    category_lines = []

    for category, amount in categories:
        category_name = CATEGORY_NAMES.get(
            category,
            category,
        )

        percentage = (
            amount / total_amount * 100
            if total_amount > 0
            else Decimal("0")
        )

        category_lines.append(
            f"{category_name}\n"
            f"   {format_money(amount)} ₽ "
            f"({percentage:.1f}%)"
        )

    categories_text = "\n\n".join(
        category_lines
    )

    await callback.message.answer(
        f"📊 Семейный бюджет за {title}\n\n"
        f"💰 Всего: {format_money(total_amount)} ₽\n"
        f"🧾 Операций: {operations_count}\n\n"
        f"{categories_text}\n\n"
        f"📅 {date_from.strftime('%d.%m.%Y')}"
        f" — {date_to.strftime('%d.%m.%Y')}"
    )
