from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


# Locate the backend folder regardless of the terminal's current directory
BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    # Firestore is the active API store. Keep PostgreSQL available for the
    # retained legacy models/migrations without requiring it just to import
    # the Firestore application or run its tests.
    DATABASE_URL: str | None = None
    NVIDIA_API_KEY: str | None = None
    PRIVORA_CORS_ORIGINS: str = (
        "http://localhost:8443,http://127.0.0.1:8443,"
        "http://localhost:5173,http://127.0.0.1:5173"
    )

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
