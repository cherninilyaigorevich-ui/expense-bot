from datetime import date
from decimal import Decimal

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.dates import local_today
from app.constants import CATEGORY_NAMES
from app.database.repository import (
    get_budget_statistics,
    set_budget_dashboard,
)
from app.keyboards.panel import budget_panel


router = Router()


FAMILY_BUDGET_ID = 1


MONTH_NAMES = {
    1: "Январь",
    2: "Февраль",
    3: "Март",
    4: "Апрель",
    5: "Май",
    6: "Июнь",
    7: "Июль",
    8: "Август",
    9: "Сентябрь",
    10: "Октябрь",
    11: "Ноябрь",
    12: "Декабрь",
}


def format_money(
    amount: Decimal,
) -> str:
    return (
        f"{amount:,.2f}"
        .replace(",", " ")
    )


async def build_panel_text(
    budget_id: int,
) -> str:
    """Сформировать текст dashboard семейного бюджета."""

    today = local_today()
    month_start = today.replace(day=1)

    total_amount, operations_count, categories = (
        await get_budget_statistics(
            budget_id=budget_id,
            date_from=month_start,
            date_to=today,
        )
    )

    month_name = MONTH_NAMES[
        today.month
    ]

    lines = [
        "💰 Семейный бюджет",
        "",
        f"📊 {month_name} {today.year}",
        "",
        f"💰 Всего: {format_money(total_amount)} ₽",
        f"🧾 Операций: {operations_count}",
    ]

    if categories:
        lines.append("")
        lines.append("Расходы по категориям:")

        for category, amount in categories:
            category_name = CATEGORY_NAMES.get(
                category,
                category,
            )

            percentage = (
                amount / total_amount * 100
                if total_amount > 0
                else Decimal("0")
            )

            lines.append(
                f"{category_name} — "
                f"{format_money(amount)} ₽ "
                f"({percentage:.1f}%)"
            )

    else:
        lines.append("")
        lines.append(
            "Расходов за этот месяц пока нет."
        )

    return "\n".join(lines)


@router.message(
    Command("panel")
)
async def show_panel_handler(
    message: Message,
    state: FSMContext,
) -> None:
    """Создать dashboard в текущем Telegram-топике."""

    await state.clear()

    if message.chat.type == "private":
        await message.answer(
            "ℹ️ Команда /panel предназначена "
            "для группового топика."
        )
        return

    panel_text = await build_panel_text(
        budget_id=FAMILY_BUDGET_ID,
    )

    dashboard_message = await message.answer(
        panel_text,
        reply_markup=budget_panel(),
    )

    await set_budget_dashboard(
        budget_id=FAMILY_BUDGET_ID,
        telegram_chat_id=message.chat.id,
        message_thread_id=message.message_thread_id,
        dashboard_message_id=dashboard_message.message_id,
    )


@router.callback_query(
    F.data == "panel:refresh"
)
async def panel_refresh_handler(
    callback: CallbackQuery,
) -> None:
    """Обновить dashboard вручную."""

    if callback.message is None:
        return

    panel_text = await build_panel_text(
        budget_id=FAMILY_BUDGET_ID,
    )

    try:
        await callback.message.edit_text(
            panel_text,
            reply_markup=budget_panel(),
        )

        await callback.answer(
            "✅ Статистика обновлена"
        )

    except TelegramBadRequest as error:
        if "message is not modified" in str(error):
            await callback.answer(
                "ℹ️ Данных без изменений"
            )
            return

        raise
