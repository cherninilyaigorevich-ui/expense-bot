from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="💸 Добавить расход"),
                KeyboardButton(text="💵 Добавить доход"),
            ],
            [
                KeyboardButton(text="📊 Статистика"),
                KeyboardButton(text="🗑 Последние расходы"),
            ],
            [
                KeyboardButton(text="🗑 Последние доходы"),
                KeyboardButton(text="📤 Выгрузка"),
            ],
        ],
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Выбери действие",
    )


def expense_categories() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🍔 Продукты",
                    callback_data="expense_category:food",
                ),
                InlineKeyboardButton(
                    text="🍽 Кафе",
                    callback_data="expense_category:cafe",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🚕 Транспорт/Авто",
                    callback_data="expense_category:transport",
                ),
                InlineKeyboardButton(
                    text="🏠 Дом",
                    callback_data="expense_category:home",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🎮 Развлечения",
                    callback_data="expense_category:entertainment",
                ),
                InlineKeyboardButton(
                    text="👕 Одежда",
                    callback_data="expense_category:clothes",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="💊 Здоровье",
                    callback_data="expense_category:health",
                ),
                InlineKeyboardButton(
                    text="🏃 Спорт",
                    callback_data="expense_category:sport",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="✈️ Путешествия",
                    callback_data="expense_category:travel",
                ),
                InlineKeyboardButton(
                    text="📦 Другое",
                    callback_data="expense_category:other",
                ),
            ],
        ]
    )
