from aiogram.types import KeyboardButton
from aiogram.types.reply_keyboard_markup import ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder


# создание реплай кнопок
def get_kyboard(
    *btns: str,
    placeholder: str = None,
    size: tuple[int] = (2,),
) -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardBuilder()

    for text in btns:
        keyboard.add(KeyboardButton(text=text))

    return keyboard.adjust(*size).as_markup(
        resize_keyboard=True, input_field_placeholder=placeholder
    )
