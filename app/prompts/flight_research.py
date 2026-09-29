"""Prompts used by the flight research agent."""

from app.schemas import TravelRequirements

FLIGHT_AGENT_SYSTEM_PROMPT = (
    "You are a flight research agent. "
    "Always call the search_flights tool for every request, even when "
    "the start date, end date, or both are missing. "
    "Pass the provided origin, destination, and traveler count. "
    "Pass each provided date as given; pass null for any missing date. "
    "Do not ask follow-up questions or invent dates."
)


def build_flight_request_prompt(requirements: TravelRequirements) -> str:
    """Render the travel requirements as the agent's opening message."""

    return (
        f"Origin: {requirements.origin}\n"
        f"Destination: {requirements.destination}\n"
        f"Start date: {requirements.start_date}\n"
        f"End date: {requirements.end_date}\n"
        f"Travelers: {requirements.travelers}"
    )
