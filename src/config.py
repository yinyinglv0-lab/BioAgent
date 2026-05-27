"""BioAgent configuration - supports Claude, DeepSeek, and any OpenAI-compatible API."""

import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Config:
    PROJECT_NAME = "BioAgent"
    VERSION = "1.0.0"
    BASE_DIR = BASE_DIR

    # Provider: "anthropic" or "openai" (DeepSeek uses openai-compatible)
    AGENT_PROVIDER = os.getenv("AGENT_PROVIDER", "openai")
    AGENT_MODEL = os.getenv("AGENT_MODEL", "deepseek-chat")
    AGENT_MAX_TOKENS = int(os.getenv("AGENT_MAX_TOKENS", "4096"))
    AGENT_TEMPERATURE = float(os.getenv("AGENT_TEMPERATURE", "0.3"))

    # Anthropic
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

    # OpenAI-compatible (DeepSeek / GLM / Qwen / GPT)
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com")

    @classmethod
    def check(cls) -> bool:
        if cls.AGENT_PROVIDER == "anthropic":
            if not cls.ANTHROPIC_API_KEY:
                raise ValueError("ANTHROPIC_API_KEY not set.")
        else:
            if not cls.OPENAI_API_KEY:
                raise ValueError(
                    "OPENAI_API_KEY not set.\n"
                    "Get a free key at https://platform.deepseek.com/\n"
                    "Then add: OPENAI_API_KEY=sk-xxx to .env"
                )
        return True


config = Config()
