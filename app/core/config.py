"""Application settings loaded from the environment."""

import os
from dataclasses import dataclass, field
from functools import lru_cache

from dotenv import load_dotenv


DEFAULT_MISTRAL_MODEL = "mistral-small-latest"
DEFAULT_GOOGLE_GENAI_MODEL = "gemini-2.5-flash"
DEFAULT_GOOGLE_CREDENTIALS_FILE = "ai.json"
DEFAULT_GOOGLE_CLOUD_LOCATION = "us-central1"
DEFAULT_CURRENCY = "INR"
DEFAULT_SQLITE_PATH = ".data/travel_planner.db"
DEFAULT_CACHE_TTL_SECONDS = 6 * 60 * 60
DEFAULT_HTTP_TIMEOUT_SECONDS = 20.0
DEFAULT_TRIP_LEAD_DAYS = 30

PERSISTENCE_BACKENDS = {"memory", "sqlite", "postgres"}
TRAVEL_DATA_PROVIDERS = {"mock", "live"}


class ConfigurationError(RuntimeError):
    """Raised when a required setting is missing or invalid."""


def _env(name: str, default: str = "") -> str:
    """Read a variable, treating blank values as unset."""

    return os.getenv(name, "").strip() or default


def _parse_api_keys(raw: str) -> dict[str, str]:
    """Parse ``key:user_id,key:user_id`` into ``{key: user_id}``."""

    keys: dict[str, str] = {}

    for entry in filter(None, (part.strip() for part in raw.split(","))):
        key, separator, user_id = entry.partition(":")

        if not separator or not key.strip() or not user_id.strip():
            raise ConfigurationError(
                "API_KEYS entries must look like '<key>:<user_id>'."
            )

        keys[key.strip()] = user_id.strip()

    return keys


@dataclass(frozen=True)
class Settings:
    """Runtime configuration for the travel planner."""

    mistral_api_key: str
    mistral_model: str

    google_genai_api_key: str
    google_genai_model: str

    google_credentials_file: str
    google_cloud_location: str

    log_level: str

    default_currency: str = DEFAULT_CURRENCY
    """Currency assumed when the user states a budget without one."""

    default_trip_lead_days: int = DEFAULT_TRIP_LEAD_DAYS
    """Days from today an undated trip is assumed to start, so live flights
    and hotels can still be priced."""

    persistence_backend: str = "sqlite"
    """Where checkpoints and long-term memory live: memory, sqlite or postgres."""
    sqlite_path: str = DEFAULT_SQLITE_PATH
    database_url: str = ""

    redis_url: str = ""
    """Optional cache for travel API responses; in-process cache when empty."""
    cache_ttl_seconds: int = DEFAULT_CACHE_TTL_SECONDS

    travel_data_provider: str = "mock"
    """mock: built-in demo data. live: SerpApi + Open-Meteo."""
    serpapi_api_key: str = ""
    http_timeout_seconds: float = DEFAULT_HTTP_TIMEOUT_SECONDS

    api_keys: dict[str, str] = field(default_factory=dict)
    """API key → user id, accepted by the HTTP API."""

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()

        google_credentials_file = _env(
            "GOOGLE_CREDENTIALS_FILE", DEFAULT_GOOGLE_CREDENTIALS_FILE
        )

        if not os.path.isfile(google_credentials_file):
            raise ConfigurationError(
                f"Google service account file not found: {google_credentials_file}. "
                "Place it in the project root or set GOOGLE_CREDENTIALS_FILE."
            )

        persistence_backend = _env("PERSISTENCE_BACKEND", "sqlite").lower()

        if persistence_backend not in PERSISTENCE_BACKENDS:
            raise ConfigurationError(
                f"PERSISTENCE_BACKEND must be one of {sorted(PERSISTENCE_BACKENDS)}."
            )

        database_url = _env("DATABASE_URL")

        if persistence_backend == "postgres" and not database_url:
            raise ConfigurationError(
                "DATABASE_URL is required when PERSISTENCE_BACKEND=postgres."
            )

        travel_data_provider = _env("TRAVEL_DATA_PROVIDER", "mock").lower()

        if travel_data_provider not in TRAVEL_DATA_PROVIDERS:
            raise ConfigurationError(
                f"TRAVEL_DATA_PROVIDER must be one of {sorted(TRAVEL_DATA_PROVIDERS)}."
            )

        serpapi_api_key = _env("SERPAPI_API_KEY")

        if travel_data_provider == "live" and not serpapi_api_key:
            raise ConfigurationError(
                "SERPAPI_API_KEY is required when TRAVEL_DATA_PROVIDER=live."
            )

        return cls(
            mistral_api_key=_env("MISTRAL_API_KEY"),
            mistral_model=_env("MISTRAL_MODEL", DEFAULT_MISTRAL_MODEL),
            google_genai_api_key=_env("GOOGLE_GENAI_API_KEY"),
            google_genai_model=_env("GOOGLE_GENAI_MODEL", DEFAULT_GOOGLE_GENAI_MODEL),
            google_credentials_file=google_credentials_file,
            google_cloud_location=_env(
                "GOOGLE_CLOUD_LOCATION", DEFAULT_GOOGLE_CLOUD_LOCATION
            ),
            log_level=_env("LOG_LEVEL", "INFO").upper(),
            default_currency=_env("DEFAULT_CURRENCY", DEFAULT_CURRENCY).upper(),
            default_trip_lead_days=int(
                _env("DEFAULT_TRIP_LEAD_DAYS", str(DEFAULT_TRIP_LEAD_DAYS))
            ),
            persistence_backend=persistence_backend,
            sqlite_path=_env("SQLITE_PATH", DEFAULT_SQLITE_PATH),
            database_url=database_url,
            redis_url=_env("REDIS_URL"),
            cache_ttl_seconds=int(
                _env("CACHE_TTL_SECONDS", str(DEFAULT_CACHE_TTL_SECONDS))
            ),
            travel_data_provider=travel_data_provider,
            serpapi_api_key=serpapi_api_key,
            http_timeout_seconds=float(
                _env("HTTP_TIMEOUT_SECONDS", str(DEFAULT_HTTP_TIMEOUT_SECONDS))
            ),
            api_keys=_parse_api_keys(_env("API_KEYS")),
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide settings, loading them on first use."""

    return Settings.from_env()
