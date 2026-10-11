from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


# Locate the backend folder regardless of the terminal's current directory
BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    DATABASE_URL: str

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
