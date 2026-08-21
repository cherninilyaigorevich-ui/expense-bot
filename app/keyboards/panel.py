from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)


def budget_panel() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💸 Добавить расход",
                    callback_data="panel:add_expense",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📊 Статистика",
                    callback_data="panel:statistics",
                ),
                InlineKeyboardButton(
                    text="📤 Выгрузка",
                    callback_data="panel:export",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🔄 Обновить",
                    callback_data="panel:refresh",
                ),
            ],
        ]
    )
