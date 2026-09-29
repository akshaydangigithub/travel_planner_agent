"""Application settings loaded from the environment."""

import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv


DEFAULT_MISTRAL_MODEL = "mistral-small-latest"
DEFAULT_GOOGLE_GENAI_MODEL = "gemini-2.5-flash"


class ConfigurationError(RuntimeError):
    """Raised when a required setting is missing or invalid."""


@dataclass(frozen=True)
class Settings:
    """Runtime configuration for the travel planner."""

    mistral_api_key: str
    mistral_model: str

    google_genai_api_key: str
    google_genai_model: str

    log_level: str

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()

        mistral_api_key = os.getenv("MISTRAL_API_KEY", "").strip()
        google_genai_api_key = os.getenv("GOOGLE_GENAI_API_KEY", "").strip()

        if not mistral_api_key and not google_genai_api_key:
            raise ConfigurationError(
                "At least one API key must be configured. "
                "Set MISTRAL_API_KEY or GOOGLE_GENAI_API_KEY in your .env file."
            )

        return cls(
            mistral_api_key=mistral_api_key,
            mistral_model=(
                os.getenv("MISTRAL_MODEL", DEFAULT_MISTRAL_MODEL).strip()
                or DEFAULT_MISTRAL_MODEL
            ),
            google_genai_api_key=google_genai_api_key,
            google_genai_model=(
                os.getenv(
                    "GOOGLE_GENAI_MODEL",
                    DEFAULT_GOOGLE_GENAI_MODEL,
                ).strip()
                or DEFAULT_GOOGLE_GENAI_MODEL
            ),
            log_level=os.getenv(
                "LOG_LEVEL",
                "INFO",
            ).strip().upper()
            or "INFO",
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide settings, loading them on first use."""

    return Settings.from_env()