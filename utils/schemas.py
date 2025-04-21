from datetime import datetime
from pydantic import BaseModel


class MeterCountSchema(BaseModel):
    hot_water_count: int
    cold_water_count: int
    electricity_count: int
    heat_count: int

class UserRegistrShema(BaseModel):
    user_id: int
    first_name: str
    last_name: str | None = None
    apartment_number: int

class MeterSeriesSchema(BaseModel):
    hot_water_serials: list[str] 
    cold_water_serials: list[str] 
    electricity_serials: list[str] 
    heat_serials: list[str] | None = None


class SubmissionSchema(BaseModel):
    apartment_number: int
    meter_type: str
    serial_number: str
    user_id: int
    value: float
    reading_date: datetime

class DescriptionSchema(BaseModel):
    hot_water_descriptions: list[str]
    cold_water_descriptions: list[str]
    electricity_descriptions: list[str]
    heat_descriptions: list[str] | None = None