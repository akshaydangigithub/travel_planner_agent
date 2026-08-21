"""Prompts used by the flight research agent."""

from app.schemas import TravelRequirements

FLIGHT_AGENT_SYSTEM_PROMPT = (
    "You are a flight research agent. "
    "Use the search_flights tool to find "
    "flight options based on the travel requirements. "
    "After receiving the tool result, summarize "
    "the available flight options."
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
