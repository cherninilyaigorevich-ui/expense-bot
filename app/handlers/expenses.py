from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from app.constants import CATEGORY_NAMES
from app.database.repository import (
    create_expense,
    get_user_budget,
)
from app.keyboards.menu import expense_categories
from app.services.dashboard import update_budget_dashboard
from app.states import AddExpense


router = Router()

MAX_EXPENSE_AMOUNT = Decimal("100000000.00")


def format_money(amount: Decimal) -> str:
    if amount == amount.to_integral_value():
        return f"{amount:,.0f}".replace(",", " ")
    return f"{amount:,.2f}".replace(",", " ")


def date_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Сегодня",
                    callback_data="expense_date:today",
                ),
                InlineKeyboardButton(
                    text="Вчера",
                    callback_data="expense_date:yesterday",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="Ввести дату вручную",
                    callback_data="expense_date:manual",
                ),
            ],
        ]
    )


def confirmation_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💬 Добавить / изменить комментарий",
                    callback_data="expense_confirm:comment",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="✅ Сохранить",
                    callback_data="expense_confirm:save",
                ),
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data="expense_confirm:cancel",
                ),
            ],
        ]
    )


@router.message(F.text == "💸 Добавить расход")
async def add_expense_handler(
    message: Message,
    state: FSMContext,
) -> None:
    if message.from_user is None:
        return

    budget = await get_user_budget(
        telegram_user_id=message.from_user.id,
    )

    if budget is None:
        await state.clear()

        await message.answer(
            "⛔ У вас нет доступа к семейному бюджету."
        )
        return

    await state.clear()

    await state.update_data(
        budget_id=budget.id,
    )

    await message.answer(
        "💸 Выбери категорию расхода:",
        reply_markup=expense_categories(),
    )


@router.callback_query(
    F.data.startswith("expense_category:")
)
async def category_selected_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    if callback.data is None or callback.message is None:
        return

    category = callback.data.split(":", 1)[1]

    if category not in CATEGORY_NAMES:
        await callback.answer(
            "Неизвестная категория.",
            show_alert=True,
        )
        return

    data = await state.get_data()

    if "budget_id" not in data:
        await state.clear()

        await callback.answer(
            "Сессия устарела. Начни добавление расхода заново.",
            show_alert=True,
        )
        return

    await state.update_data(
        category=category,
    )

    await state.set_state(
        AddExpense.waiting_for_amount,
    )

    await callback.answer()

    await callback.message.answer(
        f"{CATEGORY_NAMES[category]}\n\n"
        "💰 Введи сумму расхода:"
    )


@router.message(AddExpense.waiting_for_amount)
async def amount_handler(
    message: Message,
    state: FSMContext,
) -> None:
    if not message.text:
        await message.answer(
            "❌ Введи сумму числом."
        )
        return

    normalized_amount = (
        message.text
        .strip()
        .replace(" ", "")
        .replace(",", ".")
    )

    try:
        amount = Decimal(normalized_amount)

    except InvalidOperation:
        await message.answer(
            "❌ Не удалось распознать сумму.\n\n"
            "Например:\n"
            "1500\n"
            "1250,50"
        )
        return

    if not amount.is_finite():
        await message.answer(
            "❌ Введи корректную сумму."
        )
        return

    if amount <= 0:
        await message.answer(
            "❌ Сумма должна быть больше нуля."
        )
        return

    if amount > MAX_EXPENSE_AMOUNT:
        await message.answer(
            "❌ Слишком большая сумма.\n\n"
            "Максимальный единичный расход: "
            "100 000 000 ₽"
        )
        return

    amount = amount.quantize(
        Decimal("0.01")
    )

    await state.update_data(
        amount=str(amount),
    )

    await state.set_state(
        AddExpense.waiting_for_date,
    )

    await message.answer(
        "📅 Когда был расход?",
        reply_markup=date_keyboard(),
    )


@router.callback_query(
    AddExpense.waiting_for_date,
    F.data.startswith("expense_date:"),
)
async def date_selected_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    if callback.data is None or callback.message is None:
        return

    choice = callback.data.split(":", 1)[1]

    await callback.answer()

    if choice == "today":
        expense_date = date.today()

    elif choice == "yesterday":
        expense_date = (
            date.today()
            - timedelta(days=1)
        )

    elif choice == "manual":
        await callback.message.answer(
            "📅 Введи дату в формате ДД.ММ.ГГГГ\n\n"
            "Например: 18.08.2026"
        )
        return

    else:
        return

    await state.update_data(
        expense_date=expense_date.isoformat(),
    )

    await show_confirmation(
        callback.message,
        state,
    )


@router.message(AddExpense.waiting_for_date)
async def manual_date_handler(
    message: Message,
    state: FSMContext,
) -> None:
    if not message.text:
        await message.answer(
            "❌ Введи дату в формате ДД.ММ.ГГГГ."
        )
        return

    try:
        expense_date = datetime.strptime(
            message.text.strip(),
            "%d.%m.%Y",
        ).date()

    except ValueError:
        await message.answer(
            "❌ Неверный формат даты.\n\n"
            "Используй ДД.ММ.ГГГГ\n"
            "Например: 18.08.2026"
        )
        return

    await state.update_data(
        expense_date=expense_date.isoformat(),
    )

    await show_confirmation(
        message,
        state,
    )


async def show_confirmation(
    message: Message,
    state: FSMContext,
) -> None:
    data = await state.get_data()

    category = data["category"]
    amount = Decimal(data["amount"])

    expense_date = date.fromisoformat(
        data["expense_date"]
    )

    await state.set_state(
        AddExpense.waiting_for_confirmation,
    )

    await message.answer(
        "🔎 Проверь расход:\n\n"
        f"{CATEGORY_NAMES[category]}\n"
        f"💰 {format_money(amount)} ₽\n"
        f"📅 {expense_date.strftime('%d.%m.%Y')}\n"
        f"💬 {data.get('comment') or 'Не указан'}",
        reply_markup=confirmation_keyboard(),
    )


@router.callback_query(
    AddExpense.waiting_for_confirmation,
    F.data == "expense_confirm:comment",
)
async def request_expense_comment(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await callback.answer()
    await state.set_state(AddExpense.waiting_for_comment)

    if callback.message is not None:
        await callback.message.answer(
            "💬 Введи комментарий к расходу (до 500 символов):"
        )


@router.message(AddExpense.waiting_for_comment)
async def receive_expense_comment(
    message: Message,
    state: FSMContext,
) -> None:
    if not message.text or not message.text.strip():
        await message.answer("❌ Введи текст комментария.")
        return

    comment = message.text.strip()

    if len(comment) > 500:
        await message.answer(
            "❌ Комментарий слишком длинный. Максимум 500 символов."
        )
        return

    await state.update_data(comment=comment)
    await show_confirmation(message, state)


@router.callback_query(
    AddExpense.waiting_for_confirmation,
    F.data == "expense_confirm:save",
)
async def save_expense_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    if callback.message is None:
        return

    data = await state.get_data()

    budget_id = data.get("budget_id")

    if budget_id is None:
        await state.clear()

        await callback.answer(
            "Сессия устарела.",
            show_alert=True,
        )
        return

    category = data["category"]
    amount = Decimal(data["amount"])

    expense_date = date.fromisoformat(
        data["expense_date"]
    )

    expense = await create_expense(
        telegram_user_id=callback.from_user.id,
        telegram_chat_id=callback.message.chat.id,
        message_thread_id=callback.message.message_thread_id,
        budget_id=budget_id,
        category=category,
        amount=amount,
        expense_date=expense_date,
        comment=data.get("comment"),
    )

    await update_budget_dashboard(
        bot=callback.bot,
        budget_id=budget_id,
    )

    await callback.answer()

    await callback.message.answer(
        "✅ Расход добавлен\n\n"
        f"{CATEGORY_NAMES[expense.category]}\n"
        f"💰 {format_money(expense.amount)} ₽\n"
        f"📅 {expense.expense_date.strftime('%d.%m.%Y')}"
        + (f"\n💬 {expense.comment}" if expense.comment else "")
    )

    await state.clear()


@router.callback_query(
    AddExpense.waiting_for_confirmation,
    F.data == "expense_confirm:cancel",
)
async def cancel_expense_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await callback.answer()

    await state.clear()

    if callback.message is not None:
        await callback.message.answer(
            "❌ Добавление расхода отменено."
        )
