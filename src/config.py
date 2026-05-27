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

    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    AGENT_MODEL = os.getenv("AGENT_MODEL", "claude-sonnet-4-6")
    AGENT_MAX_TOKENS = int(os.getenv("AGENT_MAX_TOKENS", "4096"))
    AGENT_TEMPERATURE = float(os.getenv("AGENT_TEMPERATURE", "0.3"))

    @classmethod
    def check(cls) -> bool:
        if not cls.ANTHROPIC_API_KEY:
            raise ValueError(
                "ANTHROPIC_API_KEY not set. Copy .env.example to .env and add your key."
            )
        return True


config = Config()
