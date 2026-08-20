from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)


def statistics_period_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Сегодня",
                    callback_data="stats:today",
                ),
                InlineKeyboardButton(
                    text="Неделя",
                    callback_data="stats:week",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="Месяц",
                    callback_data="stats:month",
                ),
            ],
        ]
    )
