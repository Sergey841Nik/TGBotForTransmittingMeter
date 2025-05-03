from contextlib import nullcontext
from datetime import datetime
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram import Bot, Dispatcher

from handlers import user_handlers
from states.states import EditSerialsStates, MeterRegistration, UserRegistration


# Тесты для команды /start
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "user_data",
    [
        {"first_name": "Test1", "apartment_number": 42},
        {"first_name": "Test2", "apartment_number": 4},
        {"first_name": "Test3", "apartment_number": 173},
        {},
    ],
)
async def test_start_command(bot: Bot, dp: Dispatcher, user_data: dict):
    message = AsyncMock()
    mock_result = MagicMock()
    mock_result.mappings.return_value.first.return_value = user_data
    mock_session = AsyncMock()
    mock_session.execute.return_value = mock_result

    await user_handlers.start_handler(message, session=mock_session, state=AsyncMock())

    if user_data:
        expected_text = (
            f"Ваш профиль:\n"
            f"Ваше имя: {user_data['first_name']}\n"
            f"Вы проживаете в квартире: {user_data['apartment_number']}\n"
            f"Информация о счетчиках добавлена в базу данных\n"
            f"Для подачи показаний используйте /submit"
        )
    else:
        expected_text = "Введите номер квартиры (1-173):"

    message.answer.assert_called_with(expected_text)
    assert message.answer.called


# Тесты для регистрации квартиры
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "input_text, is_valid, expected_response",
    [
        ("42", True, "Сколько счетчиков горячей воды установлено? (1-3)"),
        ("173", True, "Сколько счетчиков горячей воды установлено? (1-3)"),
        ("0", False, "Номер квартиры должен быть от 1 до 173"),
        ("175", False, "Номер квартиры должен быть от 1 до 173"),
        ("abc", False, "Пожалуйста, введите число"),
    ],
)
async def test_process_apartment(
    bot: Bot, dp: Dispatcher, input_text: str, is_valid: bool, expected_response: str
):
    message = AsyncMock()
    message.text = input_text
    state = AsyncMock()

    # Создаем асинхронный мок для сессии
    mock_session = AsyncMock()

    db_mock = MagicMock()

    db_mock.get_all_meters_serials_and_descriptions = AsyncMock(return_value=None)

    with patch("handlers.user_handlers.Database", return_value=db_mock):
        await user_handlers.process_apartment(message, state, mock_session)

    if is_valid:
        state.update_data.assert_called_with(apartment_number=int(input_text))
        state.set_state.assert_called_with(UserRegistration.hot_water_count)
    message.answer.assert_called_with(expected_response)


# Тесты для обработки счетчиков горячей воды
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "input_text, is_valid, expected_response, expectation",
    [
        (
            "1",
            True,
            "Введите серийные номера горячей воды, разделенные пробелом:",
            nullcontext(),
        ),
        (
            "2",
            True,
            "Введите серийные номера горячей воды, разделенные пробелом:",
            nullcontext(),
        ),
        (
            "3",
            True,
            "Введите серийные номера горячей воды, разделенные пробелом:",
            nullcontext(),
        ),
        (
            "abc",
            False,
            "Пожалуйста, введите число от 1 до 3",
            pytest.raises(ValueError),
        ),
    ],
)
async def test_process_hot_water_count(
    bot: Bot,
    dp: Dispatcher,
    input_text: str,
    is_valid: bool,
    expected_response: str,
    expectation,
):
    message = AsyncMock()
    message.text = input_text
    state = AsyncMock()

    with expectation:
        await user_handlers.process_hot_water(message, state)

        if is_valid:
            state.update_data.assert_called_with(hot_water_count=int(input_text))
            state.set_state.assert_called_with(MeterRegistration.hot_water_serials)
        else:
            state.update_data.assert_not_called()
            state.set_state.assert_not_called()

        message.answer.assert_called_with(expected_response)


# Тесты для обработки серийных номеров
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "count, input_text, is_valid",
    [
        (2, "123 456", True),
        (1, "123", True),
        (3, "123 456 789", True),
        (2, "123", False),
        (3, "123 456", False),
        (1, "", False),
    ],
)
async def test_process_hot_water_serials(
    bot: Bot, dp: Dispatcher, count: int, input_text: str, is_valid: bool
):
    message = AsyncMock()
    message.text = input_text
    state = AsyncMock()
    state.get_data.return_value = {"hot_water_count": count}

    await user_handlers.process_hot_water_serials(message, state)

    if is_valid:
        state.update_data.assert_called()
        state.set_state.assert_called_with(MeterRegistration.hot_water_descriptions)
        message.answer.assert_called()
    else:
        message.answer.assert_called_with(f"Нужно ввести {count} номеров через пробел")


# Тесты для команды /submit
@pytest.mark.asyncio
async def test_start_submit(bot: Bot, dp: Dispatcher):
    message = AsyncMock()
    state = AsyncMock()
    session = AsyncMock()

    # Мок для пользователя
    db_mock = MagicMock()
    db_mock.get_info_for_user = AsyncMock(return_value={"apartment_number": 42})
    db_mock.get_meter_types_for_period = AsyncMock(
        return_value=["hot_water", "cold_water"]
    )

    with (
        patch("handlers.user_handlers.Database", return_value=db_mock),
        patch(
            "handlers.user_handlers.get_period",
            return_value=("Май", datetime(2025, 5, 1)),
        ),
    ):
        await user_handlers.start_submit(message, state, session)

    # Проверяем, что методы были вызваны
    db_mock.get_info_for_user.assert_awaited_once_with(message.from_user.id)
    db_mock.get_meter_types_for_period.assert_awaited_once()

    # Проверяем ответ
    message.answer.assert_called_once()
    print(f"{message.answer.call_args=}")
    assert "Подать показания за Май 2025" in message.answer.call_args[0][0]
