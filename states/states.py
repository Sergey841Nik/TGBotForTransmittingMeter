from aiogram.fsm.state import StatesGroup, State

class UserRegistration(StatesGroup):
    apartment_number = State()
    hot_water_count = State()
    cold_water_count = State()
    electricity_count = State()
    heat_count = State()

class MeterRegistration(StatesGroup):
    hot_water_serials = State()
    hot_water_descriptions = State()
    cold_water_serials = State()
    cold_water_descriptions = State()
    electricity_serials = State()
    electricity_descriptions = State()
    heat_serials = State()
    heat_descriptions = State()

class MeterSubmission(StatesGroup):
    value = State()       # Значение показаний

class EditSerialsStates(StatesGroup):
    select_meter = State()  # Выбор счетчика для редактирования
    edit_serial = State()   # Ввод нового серийного номера
