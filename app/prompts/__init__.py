"""Prompt text kept out of the node logic so it can be reviewed and tuned."""

from app.prompts.flight_research import (
    FLIGHT_AGENT_SYSTEM_PROMPT,
    build_flight_request_prompt,
)

__all__ = [
    "FLIGHT_AGENT_SYSTEM_PROMPT",
    "build_flight_request_prompt",
]
