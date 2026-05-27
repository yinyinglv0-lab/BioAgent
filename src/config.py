"""BioAgent configuration management."""

import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Config:
    PROJECT_NAME = "BioAgent"
    VERSION = "1.0.0"
    BASE_DIR = BASE_DIR
    DATA_DIR = BASE_DIR / "data"
    LOGS_DIR = BASE_DIR / "logs"

    # Anthropic
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    AGENT_MODEL = os.getenv("AGENT_MODEL", "claude-sonnet-4-6")
    AGENT_MAX_TOKENS = int(os.getenv("AGENT_MAX_TOKENS", "4096"))
    AGENT_TEMPERATURE = float(os.getenv("AGENT_TEMPERATURE", "0.3"))

    # Database (optional)
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", "3306"))
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_NAME = os.getenv("DB_NAME", "disease_db")

    @classmethod
    def check(cls) -> bool:
        if not cls.ANTHROPIC_API_KEY:
            raise ValueError(
                "ANTHROPIC_API_KEY not set. Copy .env.example to .env and add your key."
            )
        return True

    @classmethod
    def get_db_url(cls) -> str:
        return (
            f"mysql+pymysql://{cls.DB_USER}:{cls.DB_PASSWORD}"
            f"@{cls.DB_HOST}:{cls.DB_PORT}/{cls.DB_NAME}"
            f"?charset=utf8mb4"
        )


config = Config()
