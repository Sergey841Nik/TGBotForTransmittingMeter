from io import BytesIO
from logging import Logger, getLogger
from typing import Sequence
from aiogram import Bot, Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import date

from aiogram.types import BufferedInputFile
from aiogram.filters import Command
from sqlalchemy.engine.row import RowMapping
from sqlalchemy.ext.asyncio import AsyncSession
from utils.excel_utils import create_excel_file


from config import settings
from filters.chat_type import ChatTypeFilter, IsAdmin
from kbds.repley import get_kyboard
from kbds.inline import get_btns
from database.database import Database
from states.states import DeleteUserState

logger: Logger = getLogger(__name__)

router = Router()
router.message.filter(ChatTypeFilter(["private"]), IsAdmin())

ADMIN_KB: types.ReplyKeyboardMarkup = get_kyboard(
    "Получить показания всех\nсчётчиков за отчётный период",
    "Получит квартиры\nне подавшие показания",
    "Удалить пользователя\nпо номеру квартиры",
    "Отправить напоминание\nо подаче показаний",
    placeholder="Выберите действие",
)

@router.message(Command("admin"))
async def cmd_admin(message: types.Message):
    await message.answer("Вы вошли как администратор.\nВыберите действие:", reply_markup=ADMIN_KB)

@router.message(F.text == "Получит квартиры\nне подавшие показания")
async def get_apartments_without_readings(message: types.Message, session: AsyncSession):
    db = Database(session)
    apartments = await db.get_apartments_without_readings()
    logger.info("Не подали показания квартиры: %s", apartments)
    for apartment in apartments:
        await message.answer(f"Вот кто не подал показания: {apartment} квартира")

@router.message(F.text == "Получить показания всех\nсчётчиков за отчётный период")
async def get_all_readings(message: types.Message, session: AsyncSession):
    db = Database(session)
    readings: Sequence[RowMapping] | None = await db.get_all_readings_for_period()
    logger.info("Показания счетчиков за выбранный период: %s", readings)
    if readings:
        excel_file: BytesIO = await create_excel_file(readings)

        file = BufferedInputFile(excel_file.read(), filename="meter_readings.xlsx")
        await message.answer_document(file, caption="Показания счетчиков за выбранный период")
    else:
        await message.answer("Нет данных за выбранный период.")
    

@router.message(F.text == "Удалить пользователя\nпо номеру квартиры")
async def delete_user(message: types.Message, state: FSMContext):
    await message.answer("Введите номер квартиры для удаления его жильца:")
    await state.set_state(DeleteUserState.apartment_number)

@router.message(DeleteUserState.apartment_number)
async def process_delete_user_apartment(message: types.Message, state: FSMContext, session: AsyncSession):
    try:
        apartment_number = int(message.text)
        await state.update_data(apartment_number=apartment_number)
        db = Database(session)
        users = await db.get_users_by_apartment(apartment_number)
        logger.info("Пользователи с квартирой %s: %s", apartment_number, users)
        if not users:
            await message.answer("Нет пользователей с такой квартирой.")
            await state.clear()
            return
        btn = {user["first_name"]: f"deleteuser_{user["user_id"]}_{user["first_name"]}" for user in users}
        logger.info("Текст для кнопки %s", btn)
        await message.answer(
            f"Выберете пользователя из {apartment_number} для удаления",
            reply_markup=get_btns(btn=btn)
        ) 
        await state.set_state(DeleteUserState.user_for_delete)
    
    except ValueError as e:
        await message.answer("Неверный формат номера квартиры. %s", e)
        await state.clear()

@router.callback_query(DeleteUserState.user_for_delete, F.data.startswith("deleteuser_"))
async def process_delete_user_callback(callback: types.CallbackQuery, state: FSMContext):
    logger.info("Кнопка %s", callback.data)
    user_data: list[str] = callback.data.split("_")
    user_id = int(user_data[1])
    first_name = "".join(user_data[2:])
    data = await state.get_data()
    apartment_number = data.get("apartment_number")
    btn = {"Удалить": "confirm_delete", "Отмена":"cancel_delete"}
    await callback.message.answer(
        f"Вы уверены, что хотите удалить пользователя {first_name}\nиз квартиры {apartment_number}?",
        reply_markup=get_btns(btn=btn)
    )
    await state.update_data(user_id=user_id)
    await state.set_state(DeleteUserState.confirm_delete)

@router.callback_query(DeleteUserState.confirm_delete, F.data == "confirm_delete")
async def process_delete_user_confirmation(callback: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    apartment_number = data.get("apartment_number")
    user_id = data.get("user_id")
    if apartment_number and user_id:
        db = Database(session)
        await db.delete_user_by_apartment(apartment_number, user_id)
        await callback.message.answer(f"Пользователь с квартирой {apartment_number} удален.")
    else:
        await callback.message.answer("Не удалось получить номер квартиры.")
    await state.clear()

@router.callback_query(DeleteUserState.confirm_delete, F.data == "cancel_delete")
async def process_delete_user_cancellation(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Удаление отменено.")
    await state.clear()

@router.message(F.text == "Отправить напоминание\nо подаче показаний")
async def send_reminder(message: types.Message, bot: Bot, session: AsyncSession):
    db = Database(session)
    users = await db.get_all_users()
    logger.info("Получен список пользователей: %s", users)
    for user in users:
        try:
            await bot.send_message(user["user_id"], "Пожалуйста, не забудьте подать показания счетчиков!")
        except Exception as e:
            await message.answer("Не удалось отправить сообщение пользователю %s", user["user_id"])
            logger.exception("Не удалось отправить сообщение пользователю %s: %s", user["user_id"], e)
    await message.answer("Напоминания отправлены.")
