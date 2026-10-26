from datetime import date
from decimal import Decimal

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest

from app.dates import local_today
from app.constants import CATEGORY_NAMES
from app.database.repository import (
    get_budget,
    get_budget_statistics,
    set_budget_dashboard,
)
from app.keyboards.panel import budget_panel


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


async def build_budget_dashboard_text(
    budget_id: int,
) -> str:
    """Сформировать текущий dashboard семейного бюджета."""

    today = local_today()
    month_start = today.replace(
        day=1
    )

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
        lines.append(
            "Расходы по категориям:"
        )

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


async def create_new_dashboard(
    bot: Bot,
    budget_id: int,
    telegram_chat_id: int,
    message_thread_id: int | None,
    dashboard_text: str,
) -> None:
    """Создать новый dashboard и сохранить его ID."""

    message = await bot.send_message(
        chat_id=telegram_chat_id,
        message_thread_id=message_thread_id,
        text=dashboard_text,
        reply_markup=budget_panel(),
    )

    await set_budget_dashboard(
        budget_id=budget_id,
        telegram_chat_id=telegram_chat_id,
        message_thread_id=message_thread_id,
        dashboard_message_id=message.message_id,
    )


async def update_budget_dashboard(
    bot: Bot,
    budget_id: int,
) -> None:
    """Обновить dashboard бюджета.

    Если старое сообщение было удалено,
    автоматически создать новое.
    """

    budget = await get_budget(
        budget_id=budget_id,
    )

    if budget is None:
        return

    if budget.telegram_chat_id is None:
        return

    dashboard_text = await build_budget_dashboard_text(
        budget_id=budget_id,
    )

    # Если dashboard ещё ни разу не создавался,
    # создаём его сразу.
    if budget.dashboard_message_id is None:
        await create_new_dashboard(
            bot=bot,
            budget_id=budget_id,
            telegram_chat_id=budget.telegram_chat_id,
            message_thread_id=budget.message_thread_id,
            dashboard_text=dashboard_text,
        )

        return

    try:
        await bot.edit_message_text(
            chat_id=budget.telegram_chat_id,
            message_id=budget.dashboard_message_id,
            text=dashboard_text,
            reply_markup=budget_panel(),
        )

    except TelegramBadRequest as error:
        error_text = str(error).lower()

        if "message is not modified" in error_text:
            return

        if "message to edit not found" in error_text:
            await create_new_dashboard(
                bot=bot,
                budget_id=budget_id,
                telegram_chat_id=budget.telegram_chat_id,
                message_thread_id=budget.message_thread_id,
                dashboard_text=dashboard_text,
            )

            return

        raise
