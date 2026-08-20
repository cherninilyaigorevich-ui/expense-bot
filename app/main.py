import asyncio

from aiogram import Bot, Dispatcher

from app.config import BOT_TOKEN
from app.handlers.expenses import router as expenses_router
from app.handlers.start import router as start_router
from app.handlers.statistics import router as statistics_router


async def main() -> None:
    bot = Bot(token=BOT_TOKEN)

    dp = Dispatcher()

    dp.include_router(start_router)
    dp.include_router(expenses_router)
    dp.include_router(statistics_router)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
