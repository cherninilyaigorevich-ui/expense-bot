from datetime import date, datetime, timedelta

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.keyboards.menu import expense_categories
from app.states import AddExpense


router = Router()


CATEGORY_NAMES = {
    "food": "🍔 Продукты",
    "cafe": "🍽 Кафе",
    "transport": "🚕 Транспорт/Автомобиль",
    "home": "🏠 Дом",
    "entertainment": "🎮 Развлечения",
    "clothes": "👕 Одежда",
    "health": "💊 Здоровье",
    "travel": "✈️ Путешествия",
    "other": "📦 Другое",
}


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
                )
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
            ]
        ]
    )


@router.message(F.text == "💸 Добавить расход")
async def add_expense_handler(message: Message, state: FSMContext) -> None:
    await state.clear()

    await message.answer(
        "Выбери категорию расхода:",
        reply_markup=expense_categories(),
    )


@router.callback_query(F.data.startswith("expense_category:"))
async def category_selected_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    category = callback.data.split(":", 1)[1]

    await state.update_data(category=category)
    await state.set_state(AddExpense.waiting_for_amount)

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
    try:
        amount = float(message.text.replace(",", "."))
    except (ValueError, AttributeError):
        await message.answer(
            "Не удалось распознать сумму.\n"
            "Например: 1500 или 1250.50"
        )
        return

    if amount <= 0:
        await message.answer("Сумма должна быть больше нуля.")
        return

    await state.update_data(amount=amount)
    await state.set_state(AddExpense.waiting_for_date)

    await message.answer(
        "Когда был расход?",
        reply_markup=date_keyboard(),
    )


@router.callback_query(
    AddExpense.waiting_for_date,
    F.data.startswith("expense_date:")
)
async def date_selected_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    choice = callback.data.split(":", 1)[1]

    await callback.answer()

    if choice == "today":
        expense_date = date.today()

    elif choice == "yesterday":
        expense_date = date.today() - timedelta(days=1)

    elif choice == "manual":
        await callback.message.answer(
            "Введи дату в формате ДД.ММ.ГГГГ\n"
            "Например: 18.08.2026"
        )
        return

    else:
        return

    await state.update_data(expense_date=expense_date.isoformat())
    await show_confirmation(callback.message, state)


@router.message(AddExpense.waiting_for_date)
async def manual_date_handler(
    message: Message,
    state: FSMContext,
) -> None:
    try:
        expense_date = datetime.strptime(
            message.text,
            "%d.%m.%Y",
        ).date()
    except (ValueError, TypeError):
        await message.answer(
            "Неверный формат даты.\n"
            "Используй ДД.ММ.ГГГГ, например 18.08.2026"
        )
        return

    await state.update_data(expense_date=expense_date.isoformat())
    await show_confirmation(message, state)


async def show_confirmation(
    message: Message,
    state: FSMContext,
) -> None:
    data = await state.get_data()

    expense_date = date.fromisoformat(data["expense_date"])

    await state.set_state(AddExpense.waiting_for_confirmation)

    await message.answer(
        "Проверь расход:\n\n"
        f"{CATEGORY_NAMES[data['category']]}\n"
        f"💰 {data['amount']:.2f} ₽\n"
        f"📅 {expense_date.strftime('%d.%m.%Y')}",
        reply_markup=confirmation_keyboard(),
    )


@router.callback_query(
    AddExpense.waiting_for_confirmation,
    F.data == "expense_confirm:save"
)
async def save_expense_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    data = await state.get_data()

    await callback.answer()

    await callback.message.answer(
        "✅ Расход сохранён\n\n"
        f"{CATEGORY_NAMES[data['category']]}\n"
        f"💰 {data['amount']:.2f} ₽"
    )

    await state.clear()


@router.callback_query(
    AddExpense.waiting_for_confirmation,
    F.data == "expense_confirm:cancel"
)
async def cancel_expense_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await callback.answer()

    await state.clear()

    await callback.message.answer(
        "❌ Добавление расхода отменено."
    )
