from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)


def export_period_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Неделя",
                    callback_data="export:week",
                ),
                InlineKeyboardButton(
                    text="Месяц",
                    callback_data="export:month",
                ),
            ],
        ]
    )
