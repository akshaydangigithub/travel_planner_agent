"""Cross-cutting concerns: settings, logging, LLM access and console I/O."""

from app.core.config import Settings, get_settings
from app.core.llm import get_llm
from app.core.logging import configure_logging, get_logger

__all__ = [
    "Settings",
    "get_settings",
    "get_llm",
    "configure_logging",
    "get_logger",
]
