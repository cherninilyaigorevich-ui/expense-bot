from datetime import date, timedelta
from decimal import Decimal

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from app.dates import local_today
from app.constants import CATEGORY_NAMES
from app.database.repository import (
    get_budget_statistics,
    get_budget_income_statistics,
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

    today = local_today()

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


    income_total, income_count, income_categories = (
        await get_budget_income_statistics(
            budget_id=budget.id,
            date_from=date_from,
            date_to=date_to,
        )
    )

    if operations_count == 0 and income_count == 0:
        await callback.message.answer(
            f"📊 За {title} операций пока нет."
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


    income_by_person = dict(income_categories)

    await callback.message.answer(
        f"📊 Семейный бюджет за {title}\n\n"
        f"💵 Доходы: {format_money(income_total)} ₽\n"
        f"   👨 Илья: {format_money(income_by_person.get('ilya', Decimal('0')))} ₽\n"
        f"   👩 Лиза: {format_money(income_by_person.get('liza', Decimal('0')))} ₽\n"
        f"💸 Расходы: {format_money(total_amount)} ₽\n"
        f"💰 Баланс: {format_money(income_total - total_amount)} ₽\n"
        f"🧾 Операций: {operations_count + income_count}\n\n"
        f"Расходы по категориям:\n"
        f"{categories_text or 'Нет расходов'}\n\n"
        f"📅 {date_from:%d.%m.%Y} — {date_to:%d.%m.%Y}"
    )
