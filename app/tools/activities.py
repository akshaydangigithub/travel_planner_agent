"""Activity search tool exposed to the activity research agent."""

from langchain_core.tools import tool


@tool
def search_activities(
    destination: str,
    interests: list[str] | None = None,
) -> list[dict]:
    """
    Search for activities at the destination.

    Returns activities that match the traveler's
    interests, or popular activities when none are given.
    """

    categories = interests or ["sightseeing"]

    return [
        {
            "name": f"{destination} {category.title()} Tour",
            "destination": destination,
            "category": category,
            "description": f"A guided {category} experience in {destination}.",
            "duration_hours": 4,
            "price_per_person": 3000,
            "currency": "INR",
        }
        for category in categories
    ]


ACTIVITY_TOOLS = [search_activities]
