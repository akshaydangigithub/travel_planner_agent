"""Conditional edges for the top level travel graph."""

from app.graph.constants import ItineraryRoute, ValidationRoute
from app.graph.state import TravelState

MAX_REPLAN_ATTEMPTS = 2


def route_after_validation(state: TravelState) -> str:
    """Send the run back to the user when requirements are incomplete."""

    if state["validation_errors"]:
        return ValidationRoute.ASK_USER

    return ValidationRoute.CONTINUE_PLAN


def route_after_itinerary_validation(state: TravelState) -> str:
    """Finish on a valid itinerary; replan until the retry budget runs out."""

    if not state["itinerary_errors"]:
        return ItineraryRoute.VALID

    if state["replan_count"] >= MAX_REPLAN_ATTEMPTS:
        return ItineraryRoute.FAILED

    return ItineraryRoute.REPLAN
