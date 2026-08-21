"""Conditional edges for the top level travel graph."""

from app.graph.constants import ValidationRoute
from app.graph.state import TravelState


def route_after_validation(state: TravelState) -> str:
    """Send the run back to the user when requirements are incomplete."""

    if state["validation_errors"]:
        return ValidationRoute.ASK_USER

    return ValidationRoute.CONTINUE_PLAN
