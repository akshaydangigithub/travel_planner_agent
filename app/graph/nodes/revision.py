"""Apply a reviewer's change request to the trip, not just to the text.

"Make it 5 days", "my budget is now 1 lakh" or "we fly from Mumbai" change
the requirements, so the research behind the itinerary is stale. This node
re-extracts the requirements with the change request, compares them with
the previous ones and re-runs only what the change affects:

- route, dates, travellers, destination or interests → the matching
  research agents (then the budget check and the itinerary);
- budget only → the budget check;
- anything else (pace, a beach day, fewer museums) → the itinerary agent.
"""

from typing import Any, Literal

from langgraph.types import Command, Send

from app.core.logging import get_logger
from app.graph.constants import Node
from app.graph.nodes.parsing import extract_requirements
from app.graph.nodes.validation import prepare_requirements
from app.graph.state import TravelState
from app.schemas import TravelRequirements, UserProfile

logger = get_logger(__name__)

# Which requirement fields each research agent depends on.
RESEARCH_INPUTS: dict[str, set[str]] = {
    Node.FLIGHT_RESEARCH: {
        "origin", "destination", "start_date", "end_date", "travelers",
        "flights_booked", "budget_currency",
    },
    Node.HOTEL_RESEARCH: {
        "destination", "start_date", "end_date", "travelers",
        "accommodation_booked", "budget_currency",
    },
    Node.WEATHER_RESEARCH: {"destination", "start_date", "end_date"},
    Node.ACTIVITY_RESEARCH: {"destination", "interests"},
}
BUDGET_FIELDS = {"budget_amount", "budget_currency"}


def _comparable(value: Any) -> Any:
    if isinstance(value, str):
        return value.strip().casefold()

    if isinstance(value, list):
        return sorted(str(item).strip().casefold() for item in value)

    return value


def changed_fields(old: TravelRequirements, new: TravelRequirements) -> set[str]:
    return {
        name
        for name in TravelRequirements.model_fields
        if _comparable(getattr(old, name)) != _comparable(getattr(new, name))
    }


def _describe(old: TravelRequirements, new: TravelRequirements, fields: set[str]) -> str:
    def show(value: Any) -> str:
        if isinstance(value, list):
            return ", ".join(map(str, value)) or "none"
        if isinstance(value, float):
            return f"{value:,.0f}"
        return "none" if value is None else str(value)

    parts = [
        f"{name.replace('_', ' ')} {show(getattr(old, name))} → {show(getattr(new, name))}"
        for name in sorted(fields)
    ]
    return "Trip details changed: " + "; ".join(parts) + "."


def apply_revision(
    state: TravelState,
) -> Command[
    Literal[
        "flight_research", "hotel_research", "weather_research",
        "activity_research", "check_budget", "itinerary_agent",
    ]
]:
    previous = state["requirements"]

    if previous is None:
        raise ValueError("Travel requirements are missing")

    corrections = "\n".join(
        filter(None, [state["user_feedback"], state["itinerary_feedback"]])
    )
    extracted = extract_requirements(state["user_request"], corrections)
    profile = UserProfile.model_validate(state["user_profile"])
    revised, notes, errors = prepare_requirements(extracted, profile)

    if errors:
        note = "Trip details kept as they were (" + " ".join(errors) + ")"
        logger.info(note)
        return Command(update={"progress": [note]}, goto=Node.ITINERARY_AGENT)

    fields = changed_fields(previous, revised)

    if not fields:
        return Command(
            update={"progress": ["Applying your changes to the itinerary."]},
            goto=Node.ITINERARY_AGENT,
        )

    summary = _describe(previous, revised, fields)
    logger.info(summary)

    update: dict[str, Any] = {
        "requirements": revised,
        "user_feedback": corrections,
        "assumptions": notes,
        "progress": [summary],
    }

    tasks = [node for node, inputs in RESEARCH_INPUTS.items() if fields & inputs]
    hints = state["research_hints"]

    # A new budget lifts any hotel price cap derived from the old one.
    if fields & BUDGET_FIELDS and Node.HOTEL_RESEARCH in hints:
        tasks.append(Node.HOTEL_RESEARCH)

    if revised.flights_booked:
        update["flights"] = []
        tasks = [task for task in tasks if task != Node.FLIGHT_RESEARCH]

    if revised.accommodation_booked:
        update["hotels"] = []
        tasks = [task for task in tasks if task != Node.HOTEL_RESEARCH]

    tasks = list(dict.fromkeys(tasks))

    if tasks or fields & BUDGET_FIELDS:
        update["research_hints"] = {}
        update["budget_retries"] = 0

    if tasks:
        # Send carries its own input, so it needs the revised requirements.
        payload = {**state, **update, "progress": []}
        return Command(update=update, goto=[Send(task, payload) for task in tasks])

    if fields & BUDGET_FIELDS:
        return Command(update=update, goto=Node.CHECK_BUDGET)

    return Command(update=update, goto=Node.ITINERARY_AGENT)
