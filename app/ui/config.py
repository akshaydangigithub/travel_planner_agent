"""Settings for the Streamlit UI.

Kept separate from ``app.core.config`` on purpose: the UI is only an HTTP
client of the API, so it needs no LLM credentials, database or cache.
"""

import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv

DEFAULT_API_URL = "http://localhost:8000"


@dataclass(frozen=True)
class UISettings:
    api_url: str
    """Base URL of the travel planner API."""

    api_key: str
    """Optional key used for every visitor (single-user deployments).
    Leave empty to make each visitor sign in with their own key."""

    request_timeout_seconds: float
    stream_timeout_seconds: float
    """Longest silence tolerated on a streaming run (LLM calls are slow)."""

    @classmethod
    def from_env(cls) -> "UISettings":
        load_dotenv()

        def env(name: str, default: str) -> str:
            return os.getenv(name, "").strip() or default

        return cls(
            api_url=env("TRAVEL_API_URL", DEFAULT_API_URL).rstrip("/"),
            api_key=env("TRAVEL_API_KEY", ""),
            request_timeout_seconds=float(env("UI_REQUEST_TIMEOUT_SECONDS", "30")),
            stream_timeout_seconds=float(env("UI_STREAM_TIMEOUT_SECONDS", "300")),
        )


@lru_cache(maxsize=1)
def get_ui_settings() -> UISettings:
    return UISettings.from_env()
