from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    # App
    APP_NAME: str = "GOATAT Real or Clone API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    ENVIRONMENT: str = "development"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
    ]

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./goatat.db"
    DATABASE_ECHO: bool = False

    # Audio limits
    MAX_AUDIO_SIZE_MB: int = 50
    MAX_AUDIO_DURATION_SECONDS: int = 300
    AUDIO_SAMPLE_RATE: int = 16000
    SUPPORTED_AUDIO_FORMATS: list[str] = [
        ".wav", ".mp3", ".flac", ".m4a", ".ogg", ".opus", ".webm"
    ]

    # Model
    MODEL_PATH: Optional[str] = None
    MODEL_NAME: str = "XLS-R 300M (GOATAT fine-tuned)"
    MODEL_VERSION: str = "1.0.0-beta"
    USE_DEMO_MODE: bool = True
    INFERENCE_DEVICE: str = "cpu"

    # Speaker verification
    SPEAKER_MODEL_PATH: Optional[str] = None

    # Security
    SECRET_KEY: str = "goatat-dev-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Storage
    UPLOAD_DIR: str = "./uploads"
    REPORT_DIR: str = "./reports"

    # Alerts
    SYNTHETIC_ALERT_THRESHOLD: float = 0.75

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

# Ensure directories exist
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.REPORT_DIR, exist_ok=True)
