from datetime import date
from decimal import Decimal

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.constants import CATEGORY_NAMES
from app.database.repository import get_expense_statistics
from app.keyboards.menu import expense_categories
from app.keyboards.panel import budget_panel
from app.keyboards.statistics import statistics_period_keyboard


router = Router()


def format_money(amount: Decimal) -> str:
    return f"{amount:,.2f}".replace(",", " ")


async def build_panel_text(
    chat_id: int,
    message_thread_id: int | None,
) -> str:
    today = date.today()
    month_start = today.replace(day=1)

    total_amount, operations_count, categories = (
        await get_expense_statistics(
            telegram_chat_id=chat_id,
            message_thread_id=message_thread_id,
            date_from=month_start,
            date_to=today,
        )
    )

    lines = [
        "💰 Семейный бюджет",
        "",
        f"📊 За текущий месяц: {format_money(total_amount)} ₽",
        f"🧾 Операций: {operations_count}",
    ]

    if categories:
        lines.append("")
        lines.append("Категории:")

        for category, amount in categories[:5]:
            category_name = CATEGORY_NAMES.get(
                category,
                category,
            )

            lines.append(
                f"{category_name} — {format_money(amount)} ₽"
            )

    lines.append("")
    lines.append("Выбери действие:")

    return "\n".join(lines)


@router.message(Command("panel"))
async def show_panel_handler(
    message: Message,
    state: FSMContext,
) -> None:
    await state.clear()

    panel_text = await build_panel_text(
        chat_id=message.chat.id,
        message_thread_id=message.message_thread_id,
    )

    await message.answer(
        panel_text,
        reply_markup=budget_panel(),
    )


@router.callback_query(
    F.data == "panel:add_expense"
)
async def panel_add_expense_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    if callback.message is None:
        return

    await state.clear()
    await callback.answer()

    await callback.message.answer(
        "💸 Выбери категорию расхода:",
        reply_markup=expense_categories(),
    )


@router.callback_query(
    F.data == "panel:statistics"
)
async def panel_statistics_handler(
    callback: CallbackQuery,
) -> None:
    if callback.message is None:
        return

    await callback.answer()

    await callback.message.answer(
        "📊 Выбери период:",
        reply_markup=statistics_period_keyboard(),
    )


@router.callback_query(
    F.data == "panel:refresh"
)
async def panel_refresh_handler(
    callback: CallbackQuery,
) -> None:
    if callback.message is None:
        return

    panel_text = await build_panel_text(
        chat_id=callback.message.chat.id,
        message_thread_id=callback.message.message_thread_id,
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


@router.callback_query(
    F.data == "panel:export"
)
async def panel_export_handler(
    callback: CallbackQuery,
) -> None:
    await callback.answer(
        "Выгрузку добавим следующим этапом.",
        show_alert=True,
    )
