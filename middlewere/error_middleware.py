from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject
import logging
from typing import Callable, Dict, Any, Awaitable

logger = logging.getLogger(__name__)

class GlobalErrorMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]], 
        event: TelegramObject, 
        data: Dict[str, Any]
    ) -> Any:
        try:
            return await handler(event, data)
        except Exception as e:
            # Логируем с полным трейсом
            logger.error(
                "Неожиданная ошибка: %s", 
                str(e), 
                exc_info=True
            )
            
            # Отправляем сообщение пользователю
            if isinstance(event, Message):
                await event.answer(
                    "⚠️ Произошла непредвиденная ошибка. "
                    "Сообщите админу."
                )
            
            # Пробрасываем исключение дальше (если нужно)
            raise