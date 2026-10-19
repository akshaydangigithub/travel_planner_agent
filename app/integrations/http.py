"""Cached JSON GET shared by every external travel API client."""

import hashlib
import json
from typing import Any

import httpx

from app.core.cache import get_cache
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class IntegrationError(RuntimeError):
    """An external API could not answer the request."""


def _cache_key(url: str, params: dict[str, Any]) -> str:
    canonical = json.dumps([url, params], sort_keys=True, default=str)
    return "travel-api:" + hashlib.sha256(canonical.encode()).hexdigest()


def get_json(
    url: str,
    params: dict[str, Any],
    *,
    secret_params: dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
) -> Any:
    """GET ``url`` and return its JSON body, served from cache when possible.

    ``secret_params`` (API keys) are sent but kept out of the cache key and
    the logs.
    """

    settings = get_settings()
    params = {key: value for key, value in params.items() if value is not None}
    key = _cache_key(url, params)
    cache = get_cache()

    cached = cache.get(key)

    if cached is not None:
        logger.debug("Cache hit for %s", url)
        return json.loads(cached)

    try:
        response = httpx.get(
            url,
            params={**params, **(secret_params or {})},
            headers=headers,
            timeout=settings.http_timeout_seconds,
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as error:
        raise IntegrationError(
            f"{url} returned HTTP {error.response.status_code}"
        ) from error
    except httpx.HTTPError as error:
        raise IntegrationError(f"{url} request failed: {type(error).__name__}") from error

    body = response.json()
    cache.set(key, json.dumps(body), settings.cache_ttl_seconds)

    return body
