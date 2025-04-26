from logging import Logger, getLogger
from datetime import datetime, date
from typing import Any, Sequence

from dateutil.relativedelta import relativedelta
from sqlalchemy import TextClause, text
from sqlalchemy.engine.row import RowMapping
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from utils.schemas import UserRegistrShema, MeterCountSchema, MeterSeriesSchema, SubmissionSchema, DescriptionSchema
from config import settings

logger: Logger = getLogger(__name__)

class Database:
    def __init__(self, session: AsyncSession):
        self.session = session
        
    async def _ensure_meter_types_exist(self):
        # Проверяем, есть ли уже данные в таблице
        try:
            result = await self.session.execute(
                text("SELECT COUNT(*) FROM meter_types")
            )
            count = result.scalar()
            
            if count == 0:
                # Заполняем таблицу типами счетчиков
                meter_types = [
                    {"name": "electricity", "unit": "kWh"},
                    {"name": "heat", "unit": "Gcal"},
                    {"name": "hot_water", "unit": "m3"},
                    {"name": "cold_water", "unit": "m3"}
                ]
                
                for mt in meter_types:
                    stmt = text("INSERT INTO meter_types (name, unit) VALUES (:name, :unit)")
                    await self.session.execute(stmt.bindparams(**mt))

                await self.session.commit()
        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.error("Ошибка при проверке существования типов счетчиков: %s", e)

    async def add_user_info(self, user_info: UserRegistrShema):
        """Добавляет информацию о пользователе в базу данных"""
        try:
            stmt = text("""
                INSERT INTO users 
                VALUES (:user_id, :apartment_number, :first_name, :last_name)
            """)
            await self.session.execute(stmt.bindparams(**user_info.model_dump()))
            await self.session.commit()
            logger.info("Добавлен пользователе: %s", user_info)
        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.error("Ошибка при добавлении информации о пользователе: %s", e)

    async def add_meters_info(self, user_id: int, meters_info: MeterCountSchema):
        """Добавляет информацию о счетчиках в базу данных"""
        try:
            # Сохраняем информацию о счетчиках
            for meter_type, count in meters_info:
                meter_type = meter_type.replace('_count', "")
                if count > 0:  # Добавляем только если есть счетчики
                    stmt = text("""
                        INSERT INTO meters (apartment_number, type_id, "count_meter")
                        SELECT apartment_number, type_id, :count_meter
                        FROM users
                            JOIN meter_types ON meter_types.name = :meter_type
                        WHERE user_id = :user_id
                    """)
                    logger.info("Счетчик: %s добавлен в БД", meter_type)
                    await self.session.execute(stmt.bindparams(
                        user_id=user_id,
                        meter_type=meter_type,
                        count_meter=count
                    ))
            await self.session.commit()
        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.error("Ошибка при добавлении информации о счётчиках: %s", e)

    async def add_meter_series_info(self, apartment_number: int, series_info: MeterSeriesSchema):
        """Добавляет информацию о серийных номерах счетчиков в базу данных"""
        try:
            # Сохраняем информацию о сериях счетчиков
            for series in series_info:
                meter_type = series[0].replace('_serials', "")
                if series[1]:
                    for serial_number in series[1]:
                        stmt: TextClause = text("""
                            INSERT INTO serials (meter_id, serial_number)
                            SELECT meter_id, :series
                            FROM meters
                                    JOIN meter_types USING (type_id)
                            WHERE apartment_number = :apartment_number AND meter_types.name = :meter_type
                        """)
                        logger.info("Серийный номер %s счётчика: %s добавлен в БД", serial_number, meter_type)
                        await self.session.execute(stmt.bindparams(
                            apartment_number=apartment_number,
                            meter_type=meter_type,
                            series=serial_number,
                        ))
            await self.session.commit()
        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.error("Ошибка при добавлении информации о серийных номерах счётчиков: %s", e)

            
    async def add_meter_descriptions(
            self, 
            apartment_number: int, 
            descriptions_info: DescriptionSchema, 
            series_info: MeterSeriesSchema
        ) -> None:
        """Добавляет описания счетчиков в базу данных"""
        descriptions_info = descriptions_info.model_dump()
        series_info = series_info.model_dump()
        logger.info("Описания счётчиков %s", descriptions_info)
        try:
            for meter_type in ['hot_water', 'cold_water', 'electricity', 'heat']:
                if series_info[f'{meter_type}_serials'] and descriptions_info[f'{meter_type}_descriptions']:
                    for serial, description in zip(series_info[f'{meter_type}_serials'], descriptions_info[f'{meter_type}_descriptions']):
                        logger.info("Счётчик %s: %s", meter_type, serial)
                        stmt: TextClause = text("""
                            INSERT INTO meter_descriptions (serial_id, description)
                            SELECT serial_id, :description
                            FROM serials
                                JOIN meters USING (meter_id)
                                JOIN meter_types USING (type_id)
                            WHERE meters.apartment_number = :apartment_number
                            AND meter_types.name = :meter_type
                            AND serials.serial_number = :serial
                        """)
                        await self.session.execute(stmt.bindparams(
                            apartment_number=apartment_number,
                            meter_type=meter_type,
                            serial=serial,
                            description=description
                        ))
            await self.session.commit()
        except (Exception, SQLAlchemyError) as e:
            await self.session.rollback()
            logger.error("Ошибка при добавлении описаний счетчиков: %s", e)

    async def add_info_apartment(self, apartment_info) -> None:
        """Добавляет информацию об апартаментах в базу данных"""
        # Убедимся, что типы счетчиков существуют
        await self._ensure_meter_types_exist()
        logger.info("Вся инфа %s", apartment_info)
        # Сохраняем основную информацию о пользователе
        user_info = UserRegistrShema(**apartment_info)
        meters_info = MeterCountSchema(**apartment_info)
        series_info = MeterSeriesSchema(**apartment_info)
        descriptions_info = DescriptionSchema(**apartment_info)
        await self.add_user_info(user_info)
        await self.add_meters_info(user_info.user_id, meters_info)
        await self.add_meter_series_info(user_info.apartment_number, series_info)
        # Сохраняем описания счетчиков
        await self.add_meter_descriptions(user_info.apartment_number, descriptions_info, series_info)


    async def get_info_for_user(self, user_id: int) -> dict[str, Any]:
        """Получает информацию о пользователе и его счетчиках"""
        try:
            # Получаем информацию о пользователе
            query: TextClause = text("""
                        SELECT first_name, apartment_number
                        FROM users
                        WHERE users.user_id = :user_id
                    """)
            query = query.bindparams(user_id=user_id)

            result = await self.session.execute(query)
            res = result.mappings().first()
            if res:
                logger.info("Найденные данные о пользователе: %s", res)
                return res
            else:
                logger.info("Данные о пользователе не найдены")
                return None
        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.error("Ошибка при получении информации о пользователе: %s", e)
                
    
    async def get_meters_serials_and_descriptions(self, apartment: int, meter_type: str):
        """Получает список серийных номеров счётчиков"""
        try:
            query: TextClause = text("""
                SELECT serial_number, description
                FROM serials
                    JOIN meters USING (meter_id)
                    JOIN meter_types USING (type_id)
                    JOIN meter_descriptions USING (serial_id)
                WHERE meters.apartment_number = :apartment_number 
                AND meter_types.name = :meter_type
            """)

            query = query.bindparams(
                apartment_number=apartment,
                meter_type=meter_type,
            ) 
            result = await self.session.execute(query)
            res = result.mappings().fetchall()
            if res:
                logger.info("Найденные данные о серийных номерах счётчиков: %s", res)
                return res
            else:
                logger.info("Данные о серийных номерах счётчиков не найдены")
                return []
        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.error("Ошибка при получении информации о серийных номерах счётчиков: %s", e)

    async def get_all_meters_serials_and_descriptions(self, apartment: int):
        """Получает список серийных номеров счётчиков с описаниями"""
        try:
            query: TextClause = text("""
                SELECT serial_number, description
                FROM serials
                    JOIN meters USING (meter_id)
                    JOIN meter_types USING (type_id)
                    JOIN meter_descriptions USING (serial_id)
                WHERE meters.apartment_number = :apartment_number
            """)
            query = query.bindparams(apartment_number=apartment)
            result = await self.session.execute(query)
            res = result.mappings().fetchall()
            logger.info("Найденные данные о серийных номерах счётчиков с описаниями: %s", res)
            return res
        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.error("Ошибка при получении информации о серийных номерах счётчиков: %s", e)
        except Exception as e:
            logger.error("Неизвестная ошибка при получении информации о серийных номерах счётчиков: %s", e)

    async def add_reading(self, meter_value_info: dict) -> None:
        """Добавляет показания счётчика"""
        previous_month = date.today() - relativedelta(months=settings.DELTA_MONTH)
        meter_value_info["reading_date"] = previous_month
        readings = SubmissionSchema(**meter_value_info)
        logger.info("Показания от пользователя: %s", readings)
        try:
            # Добавляем показания
            stmt = text("""
                INSERT INTO readings (meter_id, user_id, serial_id, value, reading_date)
                SELECT meter_id, :user_id as user_id, serial_id, :value AS value, :reading_date AS reading_date
                FROM meters
                    JOIN meter_types USING (type_id)
                    JOIN serials USING (meter_id)
                WHERE apartment_number = :apartment_number 
                    AND meter_types.name = :meter_type 
                    AND  serial_number = :serial_number
            """)
            await self.session.execute(
                stmt.bindparams(**readings.model_dump())
            )
            logger.info("Показания добавлены")
            await self.session.commit()
            
        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.error("Ошибка при сохранении показаний: %s", e)

    async def get_all_users(self):
        """Получает информацию обо всех пользователях"""
        try:
            query: TextClause = text("""
                SELECT user_id
                FROM users
                """)
            result = await self.session.execute(query)
            res = result.mappings().fetchall()
            return res
        except SQLAlchemyError as e:
            logger.error("Ошибка при получении информации о пользователях: %s", e)
            
                    
    async def get_meter_types_for_period(self, apartment_number: int, period: datetime):
        """Получает список типов счётчиков для указанного периода"""
        logger.info("Проверка типов счетчиков за месяц: %s и год %s", f"{period.month:02d}", str(period.year))
        stmt = text("""
            SELECT name
            FROM readings
                JOIN meters USING (meter_id)
                JOIN meter_types USING (type_id)
            WHERE  strftime('%Y', reading_date) = :year
            AND strftime('%m', reading_date) = :month
            AND apartment_number = :apartment_number
        """)
        result = await self.session.execute(
            stmt.bindparams(
                year=str(period.year),
                month=f"{period.month:02d}",
                apartment_number=apartment_number)
        )
        res = [row[0] for row in result.fetchall()]  # Извлекаем первый элемент каждого кортежа
        logger.info("Получены типы счетчиков: %s", res)
        return res


    async def get_previous_reading(self, meter_type, serial_number: str) -> dict | None:
        """Получает предыдущие показания для указанного счетчика"""
        current_period = date.today()
        stmt = text("""
            SELECT value, reading_date
            FROM readings 
                JOIN serials USING (serial_id)
                JOIN meters USING (meter_id)
                JOIN meter_types USING (type_id)
            WHERE serials.serial_number = :serial_number 
            AND name = :meter_type
            AND readings.reading_date < :current_period
            ORDER BY readings.reading_date DESC
            LIMIT 1
        """)
        result = await self.session.execute(
            stmt.bindparams(serial_number=serial_number, 
                            current_period=current_period,
                            meter_type=meter_type
                            )  
        )
        return result.mappings().first()
    
    async def update_serial_number(
        self, 
        old_serial: str, 
        new_serial: str, 
        user_id: int
    ) -> bool:
        """Обновляет серийный номер счетчика"""
        try:
            stmt = text("""
                UPDATE serials
                SET serial_number = :new_serial
                WHERE serial_id IN (
                    SELECT s.serial_id
                    FROM serials s
                    JOIN meters m UNION (meter_id)
                    JOIN users u UNION (apartment_number)
                    WHERE s.serial_number = :old_serial
                    AND u.user_id = :user_id
                )
            """)
            await self.session.execute(
                stmt.bindparams(
                    old_serial=old_serial,
                    new_serial=new_serial,
                    user_id=user_id
                )
            )
            await self.session.commit()

        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.error("Ошибка при обновлении серийного номера: %e", e)
    
    async def get_all_readings_for_period(self) -> Sequence[RowMapping] | None:
        """Получает показания всех счетчиков за указанный период"""
        period: date = date.today() - relativedelta(months=settings.DELTA_MONTH)
        try:
            stmt = text("""
                SELECT users.apartment_number, name, serial_number, value, reading_date
                FROM readings
                JOIN meters USING (meter_id)
                JOIN serials USING (serial_id)
                JOIN meter_types USING (type_id)
                JOIN users USING (user_id)
                WHERE strftime('%Y', reading_date) = :year
                AND strftime('%m', reading_date) = :month
                ORDER BY users.apartment_number, meter_types.name
            """)
            result = await self.session.execute(
                stmt.bindparams(
                    year=str(period.year),
                    month=f"{period.month:02d}"
                )
            )
            return result.mappings().fetchall()
        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.error("Ошибка при получении показаний за период: %s", e)
            return None

    async def get_apartments_without_readings(self):
        """Получает список квартир, не подавших показания за указанный период"""
        period: date = date.today() - relativedelta(months=settings.DELTA_MONTH)
        try:
            stmt: TextClause = text("""
                WITH apartments_with_readings 
                    AS (
                        SELECT DISTINCT apartment_number
                        FROM readings
                            JOIN meters USING (meter_id)
                        WHERE strftime('%Y', readings.reading_date) = :year
                        AND strftime('%m', readings.reading_date) = :month
                    )
                SELECT users.apartment_number
                FROM users
                WHERE users.apartment_number NOT IN (
                    SELECT apartment_number FROM apartments_with_readings
                )
            """)
            result = await self.session.execute(
                stmt.bindparams(
                    year=str(period.year),
                    month=f"{period.month:02d}"
                )
            )
            return result.scalars().all()
        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.error("Ошибка при получении списка квартир без показаний: %s", e)
            return None

    async def delete_user_by_apartment(self, apartment_number: int, user_id: int):
        """Удаляет пользователя по номеру квартиры"""
        try:
            stmt = text("""
                DELETE FROM users
                WHERE apartment_number = :apartment_number
                AND user_id = :user_id
            """)
            await self.session.execute(stmt.bindparams(apartment_number=apartment_number, user_id=user_id))
            await self.session.commit()
        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.error("Ошибка при удалении пользователя: %s", e)
