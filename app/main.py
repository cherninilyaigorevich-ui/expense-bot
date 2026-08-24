import asyncio
import logging

from aiogram import Bot, Dispatcher

from app.config import BOT_TOKEN
from app.handlers.delete_expense import router as delete_expense_router
from app.handlers.expenses import router as expenses_router
from app.handlers.export import router as export_router
from app.handlers.panel import router as panel_router
from app.handlers.start import router as start_router
from app.handlers.statistics import router as statistics_router
from app.logging_config import setup_logging


logger = logging.getLogger(__name__)


async def main() -> None:
    setup_logging()

    logger.info(
        "Starting Expense Bot"
    )

    bot = Bot(
        token=BOT_TOKEN
    )

    dp = Dispatcher()

    dp.include_router(
        start_router
    )
    dp.include_router(
        panel_router
    )
    dp.include_router(
        expenses_router
    )
    dp.include_router(
        delete_expense_router
    )
    dp.include_router(
        statistics_router
    )
    dp.include_router(
        export_router
    )

    try:
        logger.info(
            "Telegram polling started"
        )

        await dp.start_polling(
            bot
        )

    finally:
        logger.info(
            "Expense Bot stopped"
        )

        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(
        main()
    )
