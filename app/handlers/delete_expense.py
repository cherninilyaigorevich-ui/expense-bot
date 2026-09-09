from datetime import timedelta
from decimal import Decimal

from aiogram import F, Router
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from app.constants import CATEGORY_NAMES
from app.dates import local_today
from app.database.repository import (
    get_recent_budget_expenses,
    get_user_budget,
    get_user_expense,
    soft_delete_expense,
)
from app.services.dashboard import update_budget_dashboard


router = Router()


def format_money(amount: Decimal) -> str:
    if amount == amount.to_integral_value():
        return f"{amount:,.0f}".replace(",", " ")

    return f"{amount:,.2f}".replace(",", " ")


def expenses_keyboard(
    expenses,
) -> InlineKeyboardMarkup:
    buttons = []

    for expense in expenses:
        category_name = CATEGORY_NAMES.get(
            expense.category,
            expense.category,
        )
        category_emoji = category_name.split(" ", 1)[0]

        buttons.append(
            [
                InlineKeyboardButton(
                    text=(
                        f"{category_emoji} "
                        f"{format_money(expense.amount)} ₽ · "
                        f"{expense.expense_date.strftime('%d.%m')} · "
                        f"{expense.display_name}"
                    ),
                    callback_data=f"delete_expense:{expense.id}",
                )
            ]
        )

    return InlineKeyboardMarkup(
        inline_keyboard=buttons,
    )


def confirm_delete_keyboard(
    expense_id: int,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Да, удалить",
                    callback_data=f"confirm_delete:{expense_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data="confirm_delete:cancel",
                ),
            ],
        ]
    )


@router.message(
    F.text == "🗑 Последние расходы"
)
async def recent_expenses_handler(
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

    today = local_today()

    expenses = await get_recent_budget_expenses(
        budget_id=budget.id,
        date_from=today - timedelta(days=2),
        date_to=today,
    )

    if not expenses:
        await message.answer(
            "🗑 За последние 3 дня расходов нет."
        )
        return

    await message.answer(
        "🗑 Расходы за последние 3 дня:",
        reply_markup=expenses_keyboard(expenses),
    )


@router.callback_query(
    F.data.startswith("delete_expense:")
)
async def select_expense_handler(
    callback: CallbackQuery,
) -> None:
    if callback.data is None or callback.message is None:
        return

    expense_id_text = callback.data.split(":", 1)[1]

    try:
        expense_id = int(expense_id_text)
    except ValueError:
        await callback.answer(
            "Некорректный расход.",
            show_alert=True,
        )
        return

    budget = await get_user_budget(
        telegram_user_id=callback.from_user.id,
    )

    if budget is None:
        await callback.answer(
            "Нет доступа к бюджету.",
            show_alert=True,
        )
        return

    expense = await get_user_expense(
        expense_id=expense_id,
        budget_id=budget.id,
        telegram_user_id=callback.from_user.id,
    )

    if expense is None:
        await callback.answer(
            "⛔ Можно удалять только свои расходы.",
            show_alert=True,
        )
        return

    category_name = CATEGORY_NAMES.get(
        expense.category,
        expense.category,
    )

    await callback.answer()

    await callback.message.answer(
        "Удалить этот расход?\n\n"
        f"{category_name}\n"
        f"💰 {format_money(expense.amount)} ₽\n"
        f"📅 {expense.expense_date.strftime('%d.%m.%Y')}",
        reply_markup=confirm_delete_keyboard(
            expense.id
        ),
    )


@router.callback_query(
    F.data.startswith("confirm_delete:")
)
async def confirm_delete_handler(
    callback: CallbackQuery,
) -> None:
    if callback.data is None or callback.message is None:
        return

    value = callback.data.split(":", 1)[1]

    if value == "cancel":
        await callback.answer()

        await callback.message.answer(
            "❌ Удаление отменено."
        )
        return

    try:
        expense_id = int(value)
    except ValueError:
        await callback.answer(
            "Некорректный расход.",
            show_alert=True,
        )
        return

    budget = await get_user_budget(
        telegram_user_id=callback.from_user.id,
    )

    if budget is None:
        await callback.answer(
            "Нет доступа к бюджету.",
            show_alert=True,
        )
        return

    deleted = await soft_delete_expense(
        expense_id=expense_id,
        budget_id=budget.id,
        telegram_user_id=callback.from_user.id,
    )

    if not deleted:
        await callback.answer(
            "Расход не найден или уже удалён.",
            show_alert=True,
        )
        return

    await update_budget_dashboard(
        bot=callback.bot,
        budget_id=budget.id,
    )

    await callback.answer()

    await callback.message.answer(
        "✅ Расход удалён."
    )
