from datetime import date, timedelta

from aiogram import F, Router
from aiogram.types import (
    CallbackQuery,
    FSInputFile,
    Message,
)

from app.dates import local_today
from app.database.repository import get_user_budget
from app.keyboards.export import export_period_keyboard
from app.services.export import create_budget_xlsx


router = Router()


@router.message(F.text == "📤 Выгрузка")
async def export_handler(
    message: Message,
) -> None:
    if message.from_user is None:
        return

    budget = await get_user_budget(
        telegram_user_id=message.from_user.id,
    )

    if budget is None:
        await message.answer(
            "⛔ У вас нет доступа к семейному бюджету."
        )
        return

    await message.answer(
        "📤 За какой период сделать выгрузку?",
        reply_markup=export_period_keyboard(),
    )


@router.callback_query(
    F.data.startswith("export:")
)
async def export_period_handler(
    callback: CallbackQuery,
) -> None:
    if callback.data is None or callback.message is None:
        return

    budget = await get_user_budget(
        telegram_user_id=callback.from_user.id,
    )

    if budget is None:
        await callback.answer(
            "Нет доступа к семейному бюджету.",
            show_alert=True,
        )
        return

    period = callback.data.split(":", 1)[1]

    today = local_today()

    if period == "week":
        date_from = today - timedelta(days=6)
        date_to = today
        period_name = "последние 7 дней"

    elif period == "month":
        date_from = today.replace(day=1)
        date_to = today
        period_name = "текущий месяц"

    else:
        await callback.answer(
            "Неизвестный период.",
            show_alert=True,
        )
        return

    await callback.answer(
        "Формирую файл..."
    )

    file_path = await create_budget_xlsx(
        budget_id=budget.id,
        date_from=date_from,
        date_to=date_to,
    )

    try:
        document = FSInputFile(
            path=file_path,
            filename=file_path.name,
        )

        await callback.message.answer_document(
            document=document,
            caption=(
                f"📤 Выгрузка семейного бюджета "
                f"за {period_name}\n"
                f"📅 {date_from.strftime('%d.%m.%Y')}"
                f" — {date_to.strftime('%d.%m.%Y')}"
            ),
        )

    finally:
        file_path.unlink(
            missing_ok=True,
        )
