from datetime import timedelta

from aiogram import F, Router
from aiogram.types import (
    CallbackQuery, InlineKeyboardButton,
    InlineKeyboardMarkup, Message,
)

from app.dates import local_today
from app.database.repository import (
    get_recent_budget_incomes,
    get_user_budget,
    get_user_income,
    soft_delete_income,
)
from app.services.dashboard import update_budget_dashboard

router = Router()

NAMES = {"ilya": "👨 Илья", "liza": "👩 Лиза"}


@router.message(F.text == "🗑 Последние доходы")
async def recent_incomes(message: Message):
    if message.from_user is None:
        return

    budget = await get_user_budget(message.from_user.id)
    if budget is None:
        await message.answer("⛔ Нет доступа к бюджету.")
        return

    today = local_today()
    incomes = await get_recent_budget_incomes(
        budget.id, today - timedelta(days=2), today
    )

    if not incomes:
        await message.answer("🗑 За последние 3 дня доходов нет.")
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=(
                f"{NAMES.get(i.category, i.category)} · "
                f"{i.amount:,.2f} ₽ · {i.income_date:%d.%m}"
            ).replace(",", " "),
            callback_data=f"delete_income:{i.id}",
        )]
        for i in incomes
    ])

    await message.answer(
        "💵 Доходы за последние 3 дня:",
        reply_markup=keyboard,
    )


@router.callback_query(F.data.startswith("delete_income:"))
async def select_income(callback: CallbackQuery):
    if callback.data is None or callback.message is None:
        return

    try:
        income_id = int(callback.data.split(":", 1)[1])
    except ValueError:
        await callback.answer("Некорректный доход.", show_alert=True)
        return

    budget = await get_user_budget(callback.from_user.id)
    if budget is None:
        await callback.answer("Нет доступа.", show_alert=True)
        return

    income = await get_user_income(
        income_id, budget.id, callback.from_user.id
    )
    if income is None:
        await callback.answer(
            "⛔ Можно удалять только свои доходы.",
            show_alert=True,
        )
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="✅ Да, удалить",
            callback_data=f"confirm_delete_income:{income.id}",
        )],
        [InlineKeyboardButton(
            text="❌ Отмена",
            callback_data="confirm_delete_income:cancel",
        )],
    ])

    await callback.answer()
    await callback.message.answer(
        "Удалить этот доход?\n\n"
        f"{NAMES.get(income.category, income.category)}\n"
        f"💰 {income.amount:,.2f} ₽\n"
        f"📅 {income.income_date:%d.%m.%Y}".replace(",", " "),
        reply_markup=keyboard,
    )


@router.callback_query(F.data.startswith("confirm_delete_income:"))
async def confirm_delete_income(callback: CallbackQuery):
    if callback.data is None or callback.message is None:
        return

    value = callback.data.split(":", 1)[1]

    if value == "cancel":
        await callback.answer()
        await callback.message.answer("❌ Удаление отменено.")
        return

    try:
        income_id = int(value)
    except ValueError:
        await callback.answer("Некорректный доход.", show_alert=True)
        return

    budget = await get_user_budget(callback.from_user.id)
    if budget is None:
        await callback.answer("Нет доступа.", show_alert=True)
        return

    deleted = await soft_delete_income(
        income_id, budget.id, callback.from_user.id
    )
    if not deleted:
        await callback.answer(
            "Доход не найден или уже удалён.",
            show_alert=True,
        )
        return

    await update_budget_dashboard(
        bot=callback.bot,
        budget_id=budget.id,
    )

    await callback.answer()
    await callback.message.answer("✅ Доход удалён.")
