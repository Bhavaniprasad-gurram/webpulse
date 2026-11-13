import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent

# Load environment variables from .env file if it exists
load_dotenv(BASE_DIR / ".env")


class Config:
    """Application configuration management loaded from environment variables."""

    # Database Settings
    DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
    DB_PORT = int(os.getenv("DB_PORT", "3306"))
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_NAME = os.getenv("DB_NAME", "webpulse_db")

    # Override URL if explicitly specified
    _DATABASE_URL = os.getenv("DATABASE_URL")

    @classmethod
    def get_database_url(cls) -> str:
        if cls._DATABASE_URL and cls._DATABASE_URL.strip():
            return cls._DATABASE_URL.strip()
        # Default MySQL connection string
        password_part = f":{cls.DB_PASSWORD}" if cls.DB_PASSWORD else ""
        return f"mysql+pymysql://{cls.DB_USER}{password_part}@{cls.DB_HOST}:{cls.DB_PORT}/{cls.DB_NAME}?charset=utf8mb4"

    # Monitoring Parameters
    DEFAULT_INTERVAL_SECONDS = int(os.getenv("DEFAULT_INTERVAL_SECONDS", "60"))
    DEFAULT_TIMEOUT_SECONDS = int(os.getenv("DEFAULT_TIMEOUT_SECONDS", "10"))
    FAILURE_THRESHOLD = int(os.getenv("FAILURE_THRESHOLD", "2"))  # Consecutive failures to trigger incident
    SLOW_RESPONSE_THRESHOLD_MS = int(os.getenv("SLOW_RESPONSE_THRESHOLD_MS", "1500"))  # ms

    # Email Alert Configuration (SMTP)
    SMTP_ENABLED = os.getenv("SMTP_ENABLED", "false").lower() in ("true", "1", "yes")
    SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
    SMTP_SENDER = os.getenv("SMTP_SENDER", "WebPulse Alerts <alerts@webpulse.local>")
    ALERT_RECIPIENT = os.getenv("ALERT_RECIPIENT", "")

    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")


config = Config()
