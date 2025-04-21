from typing import Any
from datetime import datetime
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_btns(*, btn: dict[str, Any], sizes: tuple[int] = (2,)) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardBuilder()
    for text, callback_data in btn.items():
        keyboard.add(InlineKeyboardButton(text=text, callback_data=callback_data))
    return keyboard.adjust(*sizes).as_markup()

def get_period_keyboard(year: int | None = None) -> InlineKeyboardMarkup:
    current_date = datetime.now()
    current_year = year if year is not None else current_date.year
    
    keyboard = InlineKeyboardBuilder()
    
    # Добавляем кнопки для месяцев
    months = (
        "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
        "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
    )
    
    for i, month in enumerate(months, 1):
        keyboard.add(InlineKeyboardButton(
            text=f"{month} {current_year}",
            callback_data=f"period_{i:02d}_{current_year}"
        ))
    
    # Кнопки для навигации по годам
    keyboard.row(
        InlineKeyboardButton(
            text="<< Предыдущий год",
            callback_data=f"year_{current_year-1}"
        ),
        InlineKeyboardButton(
            text="Следующий год >>",
            callback_data=f"year_{current_year+1}"
        )
    )
    
    return keyboard.adjust(3).as_markup()

def get_meters_keyboard(meters: list[dict]) -> InlineKeyboardMarkup:
    """Создает клавиатуру с серийными номерами и описаниями счетчиков"""
    keyboard = InlineKeyboardBuilder()
    for meter in meters:
        text = f"{meter['serial_number']} - {meter.get('description', '')}"
        keyboard.add(InlineKeyboardButton(
            text=text,
            callback_data=f"edit_serial_{meter['serial_number']}"
        ))
    keyboard.row(
        InlineKeyboardButton(
            text="Отмена",
            callback_data="cancel_edit"
        )
    )
    return keyboard.adjust(1).as_markup()
