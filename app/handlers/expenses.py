from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from app.keyboards.menu import expense_categories


router = Router()


@router.message(F.text == "💸 Добавить расход")
async def add_expense_handler(message: Message) -> None:
    await message.answer(
        "Выбери категорию расхода:",
        reply_markup=expense_categories(),
    )


@router.callback_query(F.data.startswith("expense_category:"))
async def category_selected_handler(callback: CallbackQuery) -> None:
    category = callback.data.split(":", 1)[1]

    await callback.answer()

    await callback.message.answer(
        f"Выбрана категория: {category}\n\n"
        "Следующим шагом здесь будет ввод суммы."
    )
