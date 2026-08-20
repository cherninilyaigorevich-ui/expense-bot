from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from app.keyboards.menu import main_menu


router = Router()


@router.message(CommandStart())
async def start_handler(message: Message) -> None:
    await message.answer(
        "Привет! 👋\n\n"
        "Я бот для учёта расходов.\n"
        "Выбери действие:",
        reply_markup=main_menu(),
    )
