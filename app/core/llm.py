"""Factory for the chat model used across the graph."""

from functools import lru_cache

# from langchain_mistralai import ChatMistralAI
from google.oauth2 import service_account
from langchain_google_genai import ChatGoogleGenerativeAI

from app.core.config import get_settings

# @lru_cache(maxsize=1)
# def get_llm() -> ChatMistralAI:
#     """Return a shared chat model instance built from the settings."""

#     settings = get_settings()

#     return ChatMistralAI(
#         model=settings.mistral_model,
#         api_key=settings.mistral_api_key,
#     )


@lru_cache(maxsize=1)
def get_llm() -> ChatGoogleGenerativeAI:
    """Return a shared chat model instance built from the settings."""

    settings = get_settings()

    credentials = service_account.Credentials.from_service_account_file(
        settings.google_credentials_file,
        scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )

    return ChatGoogleGenerativeAI(
        model=settings.google_genai_model,
        credentials=credentials,
        project=credentials.project_id,
        location=settings.google_cloud_location,
        vertexai=True,
    )
