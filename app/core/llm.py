"""Factory for the chat model used across the graph."""

from functools import lru_cache

from langchain_mistralai import ChatMistralAI

from app.core.config import get_settings


@lru_cache(maxsize=1)
def get_llm() -> ChatMistralAI:
    """Return a shared chat model instance built from the settings."""

    settings = get_settings()

    return ChatMistralAI(
        model=settings.mistral_model,
        api_key=settings.mistral_api_key,
    )
