"""The state object shared by every node of the travel planning graph."""

from operator import add
from typing import Annotated, TypedDict

from app.schemas import (
    ActivityResult,
    FlightResult,
    HotelResult,
    Itinerary,
    TravelRequirements,
    WeatherReport,
)


class TravelState(TypedDict):
    user_request: str
    user_feedback: str

    requirements: TravelRequirements | None
    validation_errors: list[str]

    flights: list[FlightResult]
    hotels: list[HotelResult]
    weather: WeatherReport | None
    activities: list[ActivityResult]

    itinerary: Itinerary | None
    itinerary_errors: list[str]
    replan_count: int

    # Human readable run log. Agent conversations live in each research
    # subgraph's own state and never reach this graph.
    progress: Annotated[list[str], add]


def initial_state(user_request: str) -> TravelState:
    """Build the starting state for a planning run."""

    return {
        "user_request": user_request,
        "user_feedback": "",
        "requirements": None,
        "validation_errors": [],
        "flights": [],
        "hotels": [],
        "weather": None,
        "activities": [],
        "itinerary": None,
        "itinerary_errors": [],
        "replan_count": 0,
        "progress": [],
    }
