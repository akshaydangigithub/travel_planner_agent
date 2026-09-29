"""Prompt text kept out of the node logic so it can be reviewed and tuned."""

from app.prompts.activity_research import (
    ACTIVITY_AGENT_SYSTEM_PROMPT,
    build_activity_request_prompt,
)
from app.prompts.flight_research import (
    FLIGHT_AGENT_SYSTEM_PROMPT,
    build_flight_request_prompt,
)
from app.prompts.hotel_research import (
    HOTEL_AGENT_SYSTEM_PROMPT,
    build_hotel_request_prompt,
)
from app.prompts.weather_research import (
    WEATHER_AGENT_SYSTEM_PROMPT,
    build_weather_request_prompt,
)

__all__ = [
    "ACTIVITY_AGENT_SYSTEM_PROMPT",
    "FLIGHT_AGENT_SYSTEM_PROMPT",
    "HOTEL_AGENT_SYSTEM_PROMPT",
    "WEATHER_AGENT_SYSTEM_PROMPT",
    "build_activity_request_prompt",
    "build_flight_request_prompt",
    "build_hotel_request_prompt",
    "build_weather_request_prompt",
]
