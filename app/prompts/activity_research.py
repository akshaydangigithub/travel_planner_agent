"""Prompts used by the activity research agent."""

from app.schemas import TravelRequirements

ACTIVITY_AGENT_SYSTEM_PROMPT = (
    "You are an activity research agent. "
    "Always call the search_activities tool exactly once for every request. "
    "Pass the provided destination and the full list of the traveler's "
    "interests in a single call; pass null when no interests are given. "
    "Do not ask follow-up questions or invent interests."
)


def build_activity_request_prompt(requirements: TravelRequirements) -> str:
    """Render the travel requirements as the agent's opening message."""

    return (
        f"Destination: {requirements.destination}\n"
        f"Interests: {', '.join(requirements.interests) or 'none'}\n"
        f"Preferences: {', '.join(requirements.preferences) or 'none'}"
    )
