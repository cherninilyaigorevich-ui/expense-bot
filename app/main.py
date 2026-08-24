import asyncio

from aiogram import Bot, Dispatcher

from app.config import BOT_TOKEN
from app.handlers.delete_expense import router as delete_expense_router
from app.handlers.expenses import router as expenses_router
from app.handlers.export import router as export_router
from app.handlers.panel import router as panel_router
from app.handlers.start import router as start_router
from app.handlers.statistics import router as statistics_router


async def main() -> None:
    bot = Bot(token=BOT_TOKEN)

    dp = Dispatcher()

    dp.include_router(start_router)
    dp.include_router(panel_router)
    dp.include_router(expenses_router)
    dp.include_router(delete_expense_router)
    dp.include_router(statistics_router)
    dp.include_router(export_router)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
