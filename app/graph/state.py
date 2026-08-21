"""The state object shared by every node of the travel planning graph."""

from operator import add
from typing import Annotated, TypedDict

from app.schemas import FlightResult, Itinerary, TravelRequirements


class TravelState(TypedDict):
    user_request: str
    user_feedback: str

    requirements: TravelRequirements | None

    validation_errors: list[str]

    flights: list[FlightResult]
    hotels: list
    weather: dict
    activities: list

    itinerary: Itinerary | None

    messages: Annotated[list, add]


def initial_state(user_request: str) -> TravelState:
    """Build the starting state for a planning run."""

    return {
        "user_request": user_request,
        "user_feedback": "",
        "requirements": None,
        "validation_errors": [],
        "itinerary": {},
        "messages": [],
    }
