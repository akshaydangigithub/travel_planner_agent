"""Prompts used by the hotel research agent."""

from app.schemas import TravelRequirements

HOTEL_AGENT_SYSTEM_PROMPT = (
    "You are a hotel research agent. "
    "Always call the search_hotels tool for every request, even when "
    "the check-in date, check-out date, or both are missing. "
    "Pass the provided destination and traveler count. "
    "Use the trip start date as check_in and the end date as check_out; "
    "pass null for any missing date. "
    "Do not ask follow-up questions or invent dates."
)


def build_hotel_request_prompt(requirements: TravelRequirements) -> str:
    """Render the travel requirements as the agent's opening message."""

    return (
        f"Destination: {requirements.destination}\n"
        f"Start date: {requirements.start_date}\n"
        f"End date: {requirements.end_date}\n"
        f"Travelers: {requirements.travelers}\n"
        f"Budget: {requirements.budget_amount} {requirements.budget_currency}\n"
        f"Preferences: {', '.join(requirements.preferences) or 'none'}"
    )
