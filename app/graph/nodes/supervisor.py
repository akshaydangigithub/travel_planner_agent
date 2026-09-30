"""Decide which research agents this trip actually needs."""

from app.core.logging import get_logger
from app.graph.constants import Node
from app.graph.state import TravelState

logger = get_logger(__name__)


def supervisor(state: TravelState) -> dict:
    """Pick the research nodes to dispatch from the validated requirements.

    Deterministic on purpose: the facts it needs were already extracted by
    ``parse_request``, so another LLM call would only add cost and noise.
    """

    requirements = state["requirements"]

    if requirements is None:
        raise ValueError("Travel requirements are missing")

    tasks: list[str] = []
    skipped: list[str] = []

    if requirements.flights_booked:
        skipped.append("flights already booked")
    else:
        tasks.append(Node.FLIGHT_RESEARCH)

    if requirements.accommodation_booked:
        skipped.append("accommodation already booked")
    else:
        tasks.append(Node.HOTEL_RESEARCH)

    tasks += [Node.WEATHER_RESEARCH, Node.ACTIVITY_RESEARCH]

    summary = f"Supervisor dispatched: {', '.join(tasks)}."

    if skipped:
        summary += f" Skipped: {'; '.join(skipped)}."

    logger.info(summary)

    return {"research_tasks": tasks, "progress": [summary]}
