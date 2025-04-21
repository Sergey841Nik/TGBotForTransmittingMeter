from datetime import datetime
import locale
from dateutil.relativedelta import relativedelta
from config import settings


def get_period() -> tuple[str, datetime]:
        # Установка локали (для русского языка)
        locale.setlocale(locale.LC_TIME, 'ru_RU.UTF-8')
        period_date = datetime.now() - relativedelta(months=settings.DELTA_MONTH)
        month_name = period_date.strftime('%B')
        return month_name, period_date

def get_text_for_keyboard(
        meter_types: list,         
) -> dict:
        btn: dict[str, str] = {
        f"{"✅" if "hot_water" in meter_types else "❌"}Горячая вода": "type_hot_water", 
        f"{"✅" if "cold_water" in meter_types else "❌"}Холодная вода": "type_cold_water", 
        f"{"✅" if "electricity" in meter_types else "❌"}Электричество": "type_electricity", 
        f"{"✅" if "heat" in meter_types else "❌"}Тепло": "type_heat",
        "Завершить": "finish_submit"
        }
        return btn
