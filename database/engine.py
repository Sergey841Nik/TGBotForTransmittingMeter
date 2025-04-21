from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import MetaData

from config import settings
from database.models import metadata

# Создание engine с настройками подключения
engine = create_async_engine(settings.DB_LITE, echo=False, future=True)

# Создание фабрики сессий
session_maker = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)


async def create_db():
    """Создает все таблицы в БД"""
    async with engine.begin() as conn:
        await conn.run_sync(metadata.create_all)


async def drop_db():
    """Удаляет все таблицы из БД"""
    async with engine.begin() as conn:
        await conn.run_sync(metadata.drop_all)


async def get_metadata() -> MetaData:
    """Возвращает объект метаданных для работы с таблицами"""
    return metadata
