from logging import Logger, getLogger, basicConfig, FileHandler, INFO, ERROR, StreamHandler
from pathlib import Path
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from database.engine import create_db, drop_db
from middlewere.db_middleware import DbSessionMiddleware
from config import settings
from handlers.user_handlers import router as user_routers
from commands.bot_cmds_list import privat

logger: Logger = getLogger(__name__)

BASE_DIR: Path = Path(__file__).parent
LOG_FILE: Path = BASE_DIR / "logs.log"

# Формат логов
FORMAT = "%(asctime)s:%(levelname)s:%(name)s:%(message)s"

# Настройка обработчиков для вывода логов
stream_handler = StreamHandler()
file_handler = FileHandler(LOG_FILE, encoding="utf-8")

# Установка уровня логирования
stream_handler.setLevel(INFO)
file_handler.setLevel(ERROR)

# Настройка базовой конфигурации логгера
basicConfig(level=INFO, format=FORMAT, handlers=[stream_handler, file_handler])

default=DefaultBotProperties(parse_mode=ParseMode.HTML)
bot = Bot(token=settings.BOT_TOKEN, default=default)
dp = Dispatcher()

dp.include_router(user_routers)


async def on_startup(bot):
    # await drop_db()
    await create_db()


async def on_shutdown(bot):
    print("бот лег")


async def main():
    dp.startup.register(on_startup)  # запускается при старте бота
    dp.shutdown.register(on_shutdown)  # запускается при остановке бота

    dp.update.middleware(DbSessionMiddleware())

    await bot.delete_webhook(drop_pending_updates=True)
    # await bot.delete_my_commands(scope=types.BotCommandScopeAllPrivateChats())
    await bot.set_my_commands(
        commands=privat, scope=types.BotCommandScopeAllPrivateChats()
    )
    await dp.start_polling(
        bot, polling_timeout=3, allowed_updates=dp.resolve_used_update_types()
    )

if __name__ == "__main__":
    asyncio.run(main())
