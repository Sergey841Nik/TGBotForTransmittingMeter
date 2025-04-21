from logging import Logger, getLogger
from datetime import datetime
import locale
from webbrowser import get
from dateutil.relativedelta import relativedelta
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from database.database import Database
from states.states import UserRegistration, MeterRegistration, MeterSubmission, EditSerialsStates
from kbds.inline import get_btns, get_period_keyboard
from kbds.utils import get_text_for_keyboard, get_period
from filters.chat_type import ChatTypeFilter

logger: Logger = getLogger(__name__)

router = Router()
router.message.filter(ChatTypeFilter(chat_types=["private"]))

TEXT_FOR_ANSWER_TYPE: dict[str, str] = {"hot_water": "Горячей воды", "cold_water": "Холодной воды", "electricity": "Электричества", "heat": "Тепла"}

@router.message(Command("start"))
async def start_handler(message: Message, session: AsyncSession, state: FSMContext):
    db = Database(session)
    user = await db.get_info_for_user(message.from_user.id)
    if user:
        await show_user_info(message, user)
    else:
        await message.answer("Введите номер квартиры (1-100):")
        await state.set_state(UserRegistration.apartment_number)

async def show_user_info(message: Message, user: dict):
    """Показывает информацию о пользователе"""

    text = (
        f"Ваш профиль:\n"
        f"Ваше имя: {user['first_name']}\n"
        f"Вы проживаете в квартире: {user['apartment_number']}\n"
        f"Для подачи показаний используйте /submit"
    )
    await message.answer(text)


################################## FSM register #############################################
async def process_add_database(message: Message, state: FSMContext, session: AsyncSession):
    db = Database(session)
    user_data = await state.get_data()
    user_data["user_id"] = message.from_user.id
    user_data["first_name"] = message.from_user.first_name
    user_data["last_name"] = message.from_user.last_name
    logger.info("Информация для добавления в базу данных: %s", user_data)
    await db.add_info_apartment(user_data)
    await show_user_info(message, user_data)
    await state.clear()

async def process_meter_descriptions(
    message: Message, 
    state: FSMContext, 
    meter_type: str,
    next_state: State,
    next_prompt: str,
    session: AsyncSession = None
):
    """Обрабатывает ввод описаний счетчиков"""
    data = await state.get_data()
    descriptions = data[f'{meter_type}_descriptions']
    descriptions.append(message.text)
    
    current_index = data['current_meter_index'] + 1
    await state.update_data(
        **{f'{meter_type}_descriptions': descriptions},
        current_meter_index=current_index
    )
    
    if current_index < len(data[f'{meter_type}_serials']):
        await message.answer(f"Введите описание для счетчика {data[f'{meter_type}_serials'][current_index]}:")
    else:
        if session:
            await process_add_database(message, state, session)
        else:
            await message.answer(next_prompt)
            await state.set_state(next_state)

@router.message(UserRegistration.apartment_number)
async def process_apartment(message: Message, state: FSMContext, session: AsyncSession):
    if not message.text.isdigit():
        await message.answer("Пожалуйста, введите число")
        return
        
    apartment = int(message.text)
    db = Database(session)
    meters_in_apartment = await db.get_all_meters_serials_and_descriptions(apartment)
    if meters_in_apartment:
        pass
     # Сюда добавить проверку, что счётчики для этой квартиры ужк введены в базе данных
    if not 1 <= apartment <= 100:
        await message.answer("Номер квартиры должен быть от 1 до 100")
        return
        
    await state.update_data(apartment_number=apartment)
    await message.answer("Сколько счетчиков горячей воды установлено? (1-3)")
    await state.set_state(UserRegistration.hot_water_count)

@router.message(UserRegistration.hot_water_count, F.text.regexp(r'^[1-3]$'))
async def process_hot_water(message: Message, state: FSMContext) -> None:
    await state.update_data(hot_water_count=int(message.text))
   
    await message.answer("Введите серийные номера горячей воды, разделенные пробелом:")
    await state.set_state(MeterRegistration.hot_water_serials)

@router.message(MeterRegistration.hot_water_serials)
async def process_hot_water_serials(message: Message, state: FSMContext):
    data = await state.get_data()
    count = data['hot_water_count']
    serials = [s.strip() for s in message.text.split()]
    if len(serials) != count:
        await message.answer(f"Нужно ввести {count} номеров через пробел")
        return
    
    await state.update_data(
        hot_water_serials=serials,
        current_meter_index=0,
        hot_water_descriptions=[]
    )
    await message.answer(f"Введите описание для счетчика {serials[0]}:")
    await state.set_state(MeterRegistration.hot_water_descriptions)

@router.message(MeterRegistration.hot_water_descriptions)
async def process_hot_water_descriptions(message: Message, state: FSMContext):
    data = await state.get_data()
    descriptions = data['hot_water_descriptions']
    descriptions.append(message.text)
    
    current_index = data['current_meter_index'] + 1
    await state.update_data(
        hot_water_descriptions=descriptions,
        current_meter_index=current_index
    )
    
    if current_index < len(data['hot_water_serials']):
        await message.answer(f"Введите описание для счетчика {data['hot_water_serials'][current_index]}:")
    else:
        await message.answer("Сколько счетчиков холодной воды установлено? (1-3)")
        await state.set_state(UserRegistration.cold_water_count)

@router.message(UserRegistration.cold_water_count, F.text.regexp(r'^[1-3]$'))
async def process_cold_water(message: Message, state: FSMContext) -> None:
    await state.update_data(cold_water_count=int(message.text))
    
    await message.answer("Введите серийные номера холодной воды, разделенные пробелом:")
    await state.set_state(MeterRegistration.cold_water_serials)

@router.message(MeterRegistration.cold_water_serials)
async def process_cold_water_serials(message: Message, state: FSMContext):
    data = await state.get_data()
    logger.info("Полученные данные о счетчиках холодной воды: %s", data)
    count = data['cold_water_count']
    serials = [s.strip() for s in message.text.split()]
    if len(serials) != count:
        await message.answer(f"Нужно ввести {count} номеров через пробел")
        return
    
    await state.update_data(
        cold_water_serials=serials,
        current_meter_index=0,
        cold_water_descriptions=[]
    )
    await message.answer(f"Введите описание для счетчика {serials[0]}:")
    await state.set_state(MeterRegistration.cold_water_descriptions)

@router.message(MeterRegistration.cold_water_descriptions)
async def process_cold_water_descriptions(message: Message, state: FSMContext):
    await process_meter_descriptions(
        message=message,
        state=state,
        meter_type='cold_water',
        next_state=UserRegistration.electricity_count,
        next_prompt="Сколько счетчиков электричества установено? (1-3)"
    )

@router.message(UserRegistration.electricity_count, F.text.regexp(r'^[1-3]$'))
async def process_electricity(message: Message, state: FSMContext) -> None:
    await state.update_data(electricity_count=int(message.text))
    await message.answer("Введите серийные номера электричества, разделенные пробелом:")
    await state.set_state(MeterRegistration.electricity_serials)

@router.message(MeterRegistration.electricity_serials)
async def process_electricity_serials(message: Message, state: FSMContext):
    data = await state.get_data()
    count = data['electricity_count']
    serials = [s.strip() for s in message.text.split()]
    if len(serials) != count:
        await message.answer(f"Нужно ввести {count} номеров через пробел")
        return
    
    await state.update_data(
        electricity_serials=serials,
        current_meter_index=0,
        electricity_descriptions=[]
    )
    await message.answer(f"Введите описание для счетчика {serials[0]}:")
    await state.set_state(MeterRegistration.electricity_descriptions)

@router.message(MeterRegistration.electricity_descriptions)
async def process_electricity_descriptions(message: Message, state: FSMContext):
    await process_meter_descriptions(
        message=message,
        state=state,
        meter_type='electricity',
        next_state=UserRegistration.heat_count,
        next_prompt="Сколько счетчиков тепла установено? (0-1)"
    )

@router.message(UserRegistration.heat_count, F.text.regexp(r'^[0-1]$'))
async def process_heat(message: Message, state: FSMContext, session: AsyncSession) -> None:
    count = int(message.text)
    await state.update_data(heat_count=count)
    if count == 0:
        await process_add_database(message, state, session)
        return
    
    await message.answer("Введите серийные номера тепла, разделенные пробелом:")
    await state.set_state(MeterRegistration.heat_serials)

@router.message(MeterRegistration.heat_serials)
async def process_heat_serials(message: Message, state: FSMContext):
    data = await state.get_data()
    count = data['heat_count']
    serials = [s.strip() for s in message.text.split()]
    if len(serials) != count:
        await message.answer(f"Нужно ввести {count} номеров через пробел")
        return
    
    await state.update_data(
        heat_serials=serials,
        current_meter_index=0,
        heat_descriptions=[]
    )
    await message.answer(f"Введите описание для счетчика {serials[0]}:")
    await state.set_state(MeterRegistration.heat_descriptions)

@router.message(MeterRegistration.heat_descriptions)
async def process_heat_descriptions(message: Message, state: FSMContext, session: AsyncSession):
    await process_meter_descriptions(
        message=message,
        state=state,
        meter_type='heat',
        next_state=None,
        next_prompt="",
        session=session
    )

##################################### FSM submit #####################################

@router.message(Command("submit"))
async def start_submit(message: Message, state: FSMContext, session: AsyncSession):
    db = Database(session)
    user = await db.get_info_for_user(message.from_user.id)
    if not user:
        await message.answer("Сначала зарегистрируйтесь через /start")
        return
    
    await state.update_data(user_id=message.from_user.id, apartment_number=user["apartment_number"])
    
    period_date: tuple[str, datetime] = get_period()
   
    check_readings = await db.get_meter_types_for_period(user["apartment_number"], period_date[1])
    logger.info("check_readings: %s", check_readings)
    btn: dict[str, str] = get_text_for_keyboard(check_readings)
    await message.answer(
        f"Подать показания за {period_date[0]} {period_date[1].year}:\n \
        ✅ - подано, ❌ - не подано\n",
        reply_markup=get_btns(btn=btn)
    )


@router.callback_query(F.data.startswith("type_"))
async def process_meter_type(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    meter_type = callback.data.replace("type_", "")
    # Получаем список доступных счетчиков
    db = Database(session)
    user_data = await state.get_data()
    logger.info("user_data: %s", user_data)
    meters_serials = await db.get_meters_serials_and_descriptions(user_data["apartment_number"], meter_type)
    if not meters_serials:
        await callback.message.answer(f"У вас нет счетчиков {meter_type}")
        return
    logger.info("meters_serials: %s", meters_serials)
    await state.update_data(meter_type=meter_type)
    
    # Сохраняем список счетчиков в состояние
    await state.update_data(meter_type=meter_type, meters_serials=meters_serials, current_meter_index=0)
    # Начинаем ввод показаний для первого счетчика
    await process_next_meter(callback.message, state, session)


async def process_next_meter(message: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    meters = data["meters_serials"]
    logger.info("meters: %s", meters)
    current_index = data["current_meter_index"]
    db = Database(session)
    
    if current_index >= len(meters):
        period_date: tuple[str, datetime] = get_period()
        check_readings = await db.get_meter_types_for_period(data["apartment_number"], period_date[1])
        logger.info("check_readings: %s", check_readings)
        btn: dict[str, str] = get_text_for_keyboard(check_readings)
        await message.answer(
            f"Продолжим ввод показаний за {period_date[0]} {period_date[1].year}\n \
            ✅ - подано, ❌ - не подано\n \
            Выберите пункт меню, чтобы продолжить",
            reply_markup=get_btns(btn=btn)
        )
        # Не очищаем состояние, чтобы сохранить информацию о пользователе
        return
    
    meter = meters[current_index] # Получаем информацию о счетчике по индексу далее индекс увеличиваем
    
    # Проверяем предыдущие показания
    prev_reading = await db.get_previous_reading(data["meter_type"], meter["serial_number"])
    await state.update_data(prev_reading=prev_reading)
    if prev_reading:
        await message.answer(
            f"Счетчик {meter['serial_number']}\n"
            f"Описание: {meter['description']}\n"
            f"Предыдущие показания: {prev_reading['value']}\n"
            "Введите новые показания:"
        )
    else:
        await message.answer(
            f"Счетчик {meter['serial_number']}\n"
            f"Описание: {meter['description']}\n"
            "Введите показания:"
        )
    
    await state.set_state(MeterSubmission.value)

@router.message(MeterSubmission.value)
async def process_value(message: Message, state: FSMContext, session: AsyncSession):
    try:
        data = await state.get_data()
        
        value = float(message.text)

        if data["prev_reading"] and value < data["prev_reading"]["value"]:
            await message.answer("Показания не могут быть меньше предыдущих")
            return
        
        db = Database(session)
        
        index = data.get("current_meter_index")
        # Переходим к следующему счетчику
        data["serial_number"] = data["meters_serials"][index]["serial_number"]
        data["value"] = value
        await db.add_reading(data)
        del data["serial_number"]
        
        await state.update_data(current_meter_index=data["current_meter_index"] + 1)
        await process_next_meter(message, state, session)
    

    except ValueError as e:
        logger.error("Ошибка: %s", e)
        await message.answer("Пожалуйста, введите число")


@router.message(Command("edit_serials"))
async def start_edit_serials(message: Message, state: FSMContext, session: AsyncSession):
    """Начало процесса редактирования серийных номеров"""

    db = Database(session)
    user = await db.get_info_for_user(message.from_user.id)
    
    if not user:
        await message.answer("Сначала зарегистрируйтесь через /start")
        return
    
    meters = await db.get_all_meters_serials_and_descriptions(user["apartment_number"])
    btn = {f"{meter['serial_number']} -> {meter['description']}": f"edit_serial_{meter['serial_number']}" for meter in meters}
    if not meters:
        await message.answer("У вас нет зарегистрированных счетчиков")
        return
    
    await message.answer(
        "Выберите счетчик для изменения серийного номера:",
        reply_markup=get_btns(btn=btn)
    )
    await state.set_state(EditSerialsStates.select_meter)

@router.callback_query(EditSerialsStates.select_meter, F.data.startswith("edit_serial_"))
async def select_meter_to_edit(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора счетчика для редактирования"""
    serial_number = callback.data.replace("edit_serial_", "")
    await state.update_data(selected_serial=serial_number)
    await callback.message.answer(f"Введите новый серийный номер для счетчика {serial_number}:")
    await state.set_state(EditSerialsStates.edit_serial)

@router.message(EditSerialsStates.edit_serial)
async def process_new_serial(message: Message, state: FSMContext, session: AsyncSession):
    """Обработка ввода нового серийного номера"""
    new_serial = message.text.strip()
    data = await state.get_data()
    
    db = Database(session)
    await db.update_serial_number(
        data["selected_serial"],
        new_serial,
        message.from_user.id
    )
    
    await message.answer("Серийный номер успешно изменен!")
    await state.clear()

@router.callback_query(F.data == "finish_submit")       
async def finish_submit(callback: CallbackQuery, state: FSMContext):
    # Очищаем состояние
    logger.info("Информация из состояния: %s", await state.get_data())
    await state.clear()
    logger.info("Информация из состояния после очистки: %s", await state.get_data())
    await callback.message.answer("Ввод показаний завершен.\n Для начала нового ввода используйте /submit")
