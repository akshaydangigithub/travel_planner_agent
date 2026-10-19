"""Activity search tool exposed to the activity research agent."""

from langchain_core.tools import tool

from app.core.config import get_settings
from app.integrations import serpapi


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

    if get_settings().travel_data_provider == "live":
        return serpapi.search_places(destination, categories)

    return [
        {
            "name": f"{destination} {category.title()} Tour",
            "destination": destination,
            "category": category,
            "description": f"A guided {category} experience in {destination}.",
            "duration_hours": 4,
            "price_per_person": 3000,
            "currency": "INR",
            "rating": 4.5,
        }
        for category in categories
    ]


ACTIVITY_TOOLS = [search_activities]
