"""API key authentication.

Clients send ``X-API-Key: <key>`` (or ``Authorization: Bearer <key>``).
Keys map to user ids in ``API_KEYS``; the user id scopes both the trips a
client may see and the long-term memory it reads and writes.
"""

import hmac
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status

from app.core.config import get_settings


def _match(candidate: str) -> str | None:
    """Constant time lookup, so response timing does not leak valid keys."""

    user_id = None

    for key, owner in get_settings().api_keys.items():
        if hmac.compare_digest(candidate.encode(), key.encode()):
            user_id = owner

    return user_id


def current_user(
    x_api_key: Annotated[str | None, Header()] = None,
    authorization: Annotated[str | None, Header()] = None,
) -> str:
    candidate = x_api_key

    if not candidate and authorization and authorization.lower().startswith("bearer "):
        candidate = authorization[7:].strip()

    user_id = _match(candidate) if candidate else None

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user_id


CurrentUser = Annotated[str, Depends(current_user)]
