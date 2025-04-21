from aiogram.types import BotCommand

privat = [
    BotCommand(command="start", description="Запуск бота"),
    BotCommand(command="submit", description="Подать показания"),
    BotCommand(
        command="edit_serials", description="Редактировать серийные номера счётчиков"
    ),
]
