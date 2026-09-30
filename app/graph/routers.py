"""Conditional edges for the top level travel graph."""

from langgraph.types import Send

from app.graph.constants import ItineraryRoute, Node, ValidationRoute
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


def route_research_agents(state: TravelState) -> list[Send] | str:
    """Fan out to exactly the research nodes the supervisor chose.

    Each ``Send`` starts one branch with the current state as its input.
    With no tasks there is nothing to wait for, so go straight to the join.
    """

    if not state["research_tasks"]:
        return Node.COMBINE_RESEARCH

    return [Send(task, state) for task in state["research_tasks"]]
