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

from app.database.repository import create_expense
from app.keyboards.menu import expense_categories, main_menu
from app.states import AddExpense
from app.constants import CATEGORY_NAMES

router = Router()

MAX_EXPENSE_AMOUNT = Decimal("100000000.00")


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
    await state.clear()

    await message.answer(
        "Выбери категорию расхода:",
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

    await state.update_data(
        category=category,
    )

    await state.set_state(
        AddExpense.waiting_for_amount,
    )

    await callback.answer()

    await callback.message.answer(
        f"Категория: {CATEGORY_NAMES[category]}\n\n"
        "Введи сумму расхода:"
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
            "Примеры:\n"
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
        "Когда был расход?",
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
            date.today() - timedelta(days=1)
        )

    elif choice == "manual":
        await callback.message.answer(
            "Введи дату в формате ДД.ММ.ГГГГ\n\n"
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
            "Введи дату в формате ДД.ММ.ГГГГ."
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
        "Проверь расход:\n\n"
        f"{CATEGORY_NAMES[category]}\n"
        f"💰 {amount:,.2f} ₽\n"
        f"📅 {expense_date.strftime('%d.%m.%Y')}",
        reply_markup=confirmation_keyboard(),
    )


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

    category = data["category"]
    amount = Decimal(data["amount"])

    expense_date = date.fromisoformat(
        data["expense_date"]
    )

    expense = await create_expense(
        telegram_user_id=callback.from_user.id,
        telegram_chat_id=callback.message.chat.id,
        category=category,
        amount=amount,
        expense_date=expense_date,
    )

    await callback.answer()

    await callback.message.answer(
        "✅ Расход сохранён\n\n"
        f"{CATEGORY_NAMES[expense.category]}\n"
        f"💰 {expense.amount:,.2f} ₽\n"
        f"📅 {expense.expense_date.strftime('%d.%m.%Y')}",
        reply_markup=main_menu(),
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
            "❌ Добавление расхода отменено.",
            reply_markup=main_menu(),
        )
