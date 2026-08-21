"""Research branches that run in parallel once requirements are valid."""

from app.core.logging import get_logger
from app.graph.state import TravelState

logger = get_logger(__name__)


def search_hotels(state: TravelState) -> TravelState:
    """Look up accommodation options for the trip."""

    logger.info("Searching hotels...")

    return {
        "hotels": [
            {
                "name": "Demo Hotel",
                "price_per_night": 6000,
                "currency": "INR",
            }
        ],
        "messages": ["Hotel research completed."],
    }


def search_weather(state: TravelState) -> TravelState:
    """Look up the expected weather at the destination."""

    logger.info("Checking weather...")

    return {
        "weather": {
            "condition": "Sunny",
            "temperature": 24,
        },
        "messages": ["Weather research completed."],
    }


def search_activities(state: TravelState) -> TravelState:
    """Look up activities that match the traveller's interests."""

    logger.info("Searching activities...")

    return {
        "activities": [
            {
                "name": "Local Food Tour",
                "category": "food",
            },
            {
                "name": "Nature Photography Tour",
                "category": "nature",
            },
        ],
        "messages": ["Activity research completed."],
    }
