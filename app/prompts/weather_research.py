"""Prompts used by the weather research agent."""

from app.schemas import TravelRequirements

WEATHER_AGENT_SYSTEM_PROMPT = (
    "You are a weather research agent. "
    "Always call the get_weather_forecast tool for every request, even when "
    "the start date, end date, or both are missing. "
    "Pass the provided destination. "
    "Pass each provided date as given; pass null for any missing date. "
    "Do not ask follow-up questions or invent dates."
)


def build_weather_request_prompt(requirements: TravelRequirements) -> str:
    """Render the travel requirements as the agent's opening message."""

    return (
        f"Destination: {requirements.destination}\n"
        f"Start date: {requirements.start_date}\n"
        f"End date: {requirements.end_date}"
    )
