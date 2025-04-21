# создание фильтров для проверки типа чата
from aiogram.filters import Filter
from aiogram import types

from config import settings

class ChatTypeFilter(Filter):
    def __init__(self, chat_types: list[str]) -> None:
        self.chat_types = chat_types

    async def __call__(self, message: types.Message) -> bool:
        return message.chat.type in self.chat_types
    

class IsAdmin(Filter):
    def __init__(self) -> None:
        pass

    async def  __call__(self, message: types.Message)  -> bool:
        
        return message.from_user.id in settings.ADMIN_IDS