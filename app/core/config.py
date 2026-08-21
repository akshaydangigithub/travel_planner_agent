"""Application settings loaded from the environment."""

import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv

DEFAULT_MISTRAL_MODEL = "mistral-small-latest"


class ConfigurationError(RuntimeError):
    """Raised when a required setting is missing or invalid."""


@dataclass(frozen=True)
class Settings:
    """Runtime configuration for the travel planner."""

    mistral_api_key: str
    mistral_model: str
    log_level: str

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()

        api_key = os.getenv("MISTRAL_API_KEY", "").strip()

        if not api_key:
            raise ConfigurationError(
                "MISTRAL_API_KEY is not set. "
                "Copy .env.example to .env and provide a valid key."
            )

        return cls(
            mistral_api_key=api_key,
            mistral_model=os.getenv("MISTRAL_MODEL", DEFAULT_MISTRAL_MODEL).strip()
            or DEFAULT_MISTRAL_MODEL,
            log_level=os.getenv("LOG_LEVEL", "INFO").strip().upper() or "INFO",
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide settings, loading them on first use."""

    return Settings.from_env()
