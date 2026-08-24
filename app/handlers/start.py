from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from app.keyboards.menu import main_menu


router = Router()


@router.message(CommandStart())
async def start_handler(
    message: Message,
) -> None:
    if message.from_user is None:
        return

    # Временно выводим Telegram ID пользователя в консоль.
    print(
        "USER:",
        message.from_user.id,
        message.from_user.full_name,
    )

    await message.answer(
        "💰 Семейный бюджет\n\n"
        "Здесь можно добавлять расходы, "
        "смотреть общую статистику семьи "
        "и управлять своими расходами.",
        reply_markup=main_menu(),
    )
