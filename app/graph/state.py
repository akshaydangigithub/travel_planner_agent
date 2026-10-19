"""The state object shared by every node of the travel planning graph."""

from operator import add
from typing import Annotated, Any, TypedDict

from app.schemas import (
    ActivityResult,
    FlightResult,
    HotelResult,
    Itinerary,
    TravelRequirements,
    WeatherReport,
)


class TravelState(TypedDict):
    # Owner of the thread; also the namespace of their long-term memory.
    user_id: str
    # Saved traveller profile, loaded from the store at the start of a run.
    user_profile: dict[str, Any]

    user_request: str
    # Every correction the user gave when requirements were incomplete.
    user_feedback: str

    requirements: TravelRequirements | None
    validation_errors: list[str]
    # Defaults the planner chose for the user (assumed dates, profile values).
    assumptions: list[str]

    flights: list[FlightResult]
    hotels: list[HotelResult]
    weather: WeatherReport | None
    activities: list[ActivityResult]

    # Research nodes the supervisor dispatched for this run.
    research_tasks: list[str]
    # Per-agent constraint text, e.g. {"hotel_research": "max 5000 per night"}.
    research_hints: dict[str, str]
    budget_retries: int

    itinerary: Itinerary | None
    itinerary_errors: list[str]
    replan_count: int

    # Human review of a valid itinerary.
    itinerary_feedback: str         # change requests, newest last
    revision_count: int
    review_decision: str            # "" | "approved" | "rejected"

    progress: Annotated[list[str], add]


def initial_state(user_request: str, user_id: str) -> TravelState:
    """Build the starting state for a planning run."""

    return {
        "user_id": user_id,
        "user_profile": {},
        "user_request": user_request,
        "user_feedback": "",
        "requirements": None,
        "validation_errors": [],
        "assumptions": [],
        "flights": [],
        "hotels": [],
        "weather": None,
        "activities": [],
        "research_tasks": [],
        "research_hints": {},
        "budget_retries": 0,
        "itinerary": None,
        "itinerary_errors": [],
        "replan_count": 0,
        "itinerary_feedback": "",
        "revision_count": 0,
        "review_decision": "",
        "progress": [],
    }
