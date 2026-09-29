"""Nodes that talk to the person running the planner."""

from app.core.console import prompt, show
from app.core.logging import get_logger
from app.graph.state import TravelState

logger = get_logger(__name__)


def ask_user(state: TravelState) -> dict:
    """Report the validation errors and collect a correction."""

    show("Requirements are incomplete.")
    show("Errors:")

    for error in state["validation_errors"]:
        show(f"- {error}")

    feedback = prompt("\nPlease provide corrected information: ")

    return {"user_feedback": feedback}


def continue_plan(state: TravelState) -> dict:
    """Fan out into the research branches once requirements are valid."""

    logger.info("Requirements are valid. Continuing with travel planning...")

    return {"progress": ["Requirements validated."]}
