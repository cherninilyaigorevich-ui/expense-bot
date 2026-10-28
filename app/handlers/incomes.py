from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery, InlineKeyboardButton,
    InlineKeyboardMarkup, Message,
)

from app.dates import local_today
from app.database.repository import create_income, get_user_budget
from app.services.dashboard import update_budget_dashboard
from app.states import AddIncome

router = Router()

INCOME_CATEGORIES = {
    "ilya": "👨 Илья",
    "liza": "👩 Лиза",
}

MAX_AMOUNT = Decimal("100000000.00")


def category_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=name, callback_data=f"income_category:{key}"
        )]
        for key, name in INCOME_CATEGORIES.items()
    ])


def date_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="Сегодня", callback_data="income_date:today"
            ),
            InlineKeyboardButton(
                text="Вчера", callback_data="income_date:yesterday"
            ),
        ],
        [InlineKeyboardButton(
            text="Ввести дату вручную",
            callback_data="income_date:manual",
        )],
    ])


def confirmation_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="💬 Добавить / изменить комментарий",
            callback_data="income_confirm:comment",
        )],
        [
            InlineKeyboardButton(
                text="✅ Сохранить", callback_data="income_confirm:save"
            ),
            InlineKeyboardButton(
                text="❌ Отмена", callback_data="income_confirm:cancel"
            ),
        ],
    ])


@router.message(F.text == "💵 Добавить доход")
async def start_income(message: Message, state: FSMContext):
    if message.from_user is None:
        return

    budget = await get_user_budget(message.from_user.id)
    if budget is None:
        await message.answer("⛔ Нет доступа к семейному бюджету.")
        return

    await state.clear()
    await state.update_data(budget_id=budget.id)
    await message.answer(
        "💵 Чей доход добавляем?",
        reply_markup=category_keyboard(),
    )


@router.callback_query(F.data.startswith("income_category:"))
async def select_category(callback: CallbackQuery, state: FSMContext):
    if callback.data is None or callback.message is None:
        return

    category = callback.data.split(":", 1)[1]
    data = await state.get_data()

    if category not in INCOME_CATEGORIES or "budget_id" not in data:
        await callback.answer(
            "Категория неизвестна или сессия устарела.",
            show_alert=True,
        )
        return

    await state.update_data(category=category)
    await state.set_state(AddIncome.waiting_for_amount)
    await callback.answer()
    await callback.message.answer("💰 Введи сумму дохода:")


@router.message(AddIncome.waiting_for_amount)
async def receive_amount(message: Message, state: FSMContext):
    if not message.text:
        await message.answer("❌ Введи сумму числом.")
        return

    try:
        amount = Decimal(
            message.text.strip().replace(" ", "").replace(",", ".")
        )
    except InvalidOperation:
        await message.answer("❌ Неверная сумма. Например: 150000")
        return

    if not amount.is_finite() or amount <= 0 or amount > MAX_AMOUNT:
        await message.answer("❌ Сумма должна быть от 0 до 100 млн ₽.")
        return

    amount = amount.quantize(Decimal("0.01"))
    if amount <= 0:
        await message.answer("❌ Минимальная сумма — 0,01 ₽.")
        return

    await state.update_data(amount=str(amount))
    await state.set_state(AddIncome.waiting_for_date)
    await message.answer(
        "📅 Когда получен доход?",
        reply_markup=date_keyboard(),
    )


@router.callback_query(
    AddIncome.waiting_for_date,
    F.data.startswith("income_date:"),
)
async def select_date(callback: CallbackQuery, state: FSMContext):
    if callback.data is None or callback.message is None:
        return

    choice = callback.data.split(":", 1)[1]
    await callback.answer()

    if choice == "manual":
        await callback.message.answer("Введи дату: ДД.ММ.ГГГГ")
        return

    if choice not in ("today", "yesterday"):
        return

    income_date = local_today()
    if choice == "yesterday":
        income_date -= timedelta(days=1)

    await state.update_data(income_date=income_date.isoformat())
    await show_confirmation(callback.message, state)


@router.message(AddIncome.waiting_for_date)
async def manual_date(message: Message, state: FSMContext):
    try:
        income_date = datetime.strptime(
            message.text.strip(), "%d.%m.%Y"
        ).date()
    except (ValueError, AttributeError):
        await message.answer("❌ Формат даты: ДД.ММ.ГГГГ")
        return

    await state.update_data(income_date=income_date.isoformat())
    await show_confirmation(message, state)


async def show_confirmation(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.set_state(AddIncome.waiting_for_confirmation)

    await message.answer(
        "🔎 Проверь доход:\n\n"
        f"{INCOME_CATEGORIES[data['category']]}\n"
        f"💰 {Decimal(data['amount']):,.2f} ₽\n"
        f"📅 {date.fromisoformat(data['income_date']):%d.%m.%Y}\n"
        f"💬 {data.get('comment') or 'Не указан'}",
        reply_markup=confirmation_keyboard(),
    )


@router.callback_query(
    AddIncome.waiting_for_confirmation,
    F.data == "income_confirm:comment",
)
async def request_comment(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(AddIncome.waiting_for_comment)
    if callback.message:
        await callback.message.answer(
            "💬 Введи комментарий (до 500 символов):"
        )


@router.message(AddIncome.waiting_for_comment)
async def receive_comment(message: Message, state: FSMContext):
    comment = (message.text or "").strip()

    if not comment or len(comment) > 500:
        await message.answer("❌ Введи комментарий до 500 символов.")
        return

    await state.update_data(comment=comment)
    await show_confirmation(message, state)


@router.callback_query(
    AddIncome.waiting_for_confirmation,
    F.data == "income_confirm:save",
)
async def save_income(callback: CallbackQuery, state: FSMContext):
    if callback.message is None:
        return

    data = await state.get_data()
    budget = await get_user_budget(callback.from_user.id)

    if (
        budget is None
        or budget.id != data.get("budget_id")
        or data.get("category") not in INCOME_CATEGORIES
    ):
        await state.clear()
        await callback.answer("Сессия устарела.", show_alert=True)
        return

    income = await create_income(
        telegram_user_id=callback.from_user.id,
        telegram_chat_id=callback.message.chat.id,
        message_thread_id=callback.message.message_thread_id,
        budget_id=budget.id,
        category=data["category"],
        amount=Decimal(data["amount"]),
        income_date=date.fromisoformat(data["income_date"]),
        comment=data.get("comment"),
    )

    await state.clear()
    await callback.answer()
    await callback.message.answer(
        f"✅ Доход добавлен\n\n"
        f"{INCOME_CATEGORIES[income.category]}\n"
        f"💰 {income.amount:,.2f} ₽\n"
        f"📅 {income.income_date:%d.%m.%Y}"
        + (f"\n💬 {income.comment}" if income.comment else "")
    )

    await update_budget_dashboard(
        bot=callback.bot, budget_id=budget.id
    )


@router.callback_query(
    AddIncome.waiting_for_confirmation,
    F.data == "income_confirm:cancel",
)
async def cancel_income(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer()
    if callback.message:
        await callback.message.answer("❌ Добавление дохода отменено.")
