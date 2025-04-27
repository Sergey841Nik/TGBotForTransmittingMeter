from datetime import datetime

from sqlalchemy import Table, MetaData, Column, Integer, String, DateTime, ForeignKey, UniqueConstraint

metadata = MetaData()

users = Table(
    "users", metadata,
    Column("user_id", Integer, primary_key=True),
    Column("apartment_number", Integer, nullable=False),
    Column("first_name", String, nullable=True),
    Column("last_name", String, nullable=True),
)

meter_types = Table(
    "meter_types", metadata,
    Column("type_id", Integer, primary_key=True),
    Column("name", String, nullable=False),  # "electric", "heat", "hot_water", "cold_water"
    Column("unit", String, nullable=False),  # "kWh", "Gcal", "m3"
)

meters = Table(
    "meters", metadata,
    Column("meter_id", Integer, primary_key=True),
    Column("apartment_number", Integer, ForeignKey("users.apartment_number")),
    Column("type_id", Integer, ForeignKey("meter_types.type_id"), nullable=False),
    Column("count_meter", Integer, nullable=False),
)

serials = Table(
    "serials", metadata,
    Column("serial_id", Integer, primary_key=True),
    Column("meter_id", Integer, ForeignKey("meters.meter_id")),
    Column("serial_number", String(20), nullable=False), 
)

readings = Table(
    "readings", metadata,
    Column("reading_id", Integer, primary_key=True),
    Column("meter_id", Integer, ForeignKey("meters.meter_id")),
    Column("user_id", Integer, ForeignKey("users.user_id")),  # Кто подал показания
    Column("serial_id", Integer, default=None),
    Column("value", Integer, nullable=False),
    Column("reading_date", DateTime, nullable=False),  # Дата снятия показаний
    UniqueConstraint('meter_id', 'reading_date', "serial_id", name='uix_meter_reading_date'),  # Проверка дублирования
)

meter_descriptions = Table(
    "meter_descriptions", metadata,
    Column("desc_id", Integer, primary_key=True),
    Column("serial_id", Integer, ForeignKey("serials.serial_id")),
    Column("description", String(50), nullable=False),
)
