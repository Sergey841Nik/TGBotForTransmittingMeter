from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).parent

class Settings(BaseSettings):
    # Database config
    DB_LITE: str
    
    # App config
    BOT_TOKEN: str
    ADMIN_IDS: list[int]
    MODE: str
    DELTA_MONTH: int = 1

    @property
    def db_url(self):
        return self.DB_LITE  # Используем SQLite по умолчанию
        
    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()
