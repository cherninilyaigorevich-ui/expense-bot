from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)


def budget_panel() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔄 Обновить",
                    callback_data="panel:refresh",
                ),
            ],
        ]
    )
