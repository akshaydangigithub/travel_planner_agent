"""Compare the researched trip cost with the budget and re-research if needed."""

from typing import Literal

from langgraph.types import Command, Send

from app.core.logging import get_logger
from app.graph.constants import Node
from app.graph.state import TravelState

logger = get_logger(__name__)

MAX_BUDGET_RETRIES = 1


def check_budget(
    state: TravelState,
) -> Command[Literal["itinerary_agent", "hotel_research"]]:
    """Continue to the itinerary, or re-run hotel research with a price cap.

    One node both updates state and chooses the next step, so the numbers
    computed here do not need a separate router to recompute them.
    """

    requirements = state["requirements"]

    if requirements is None:
        raise ValueError("Travel requirements are missing")

    budget = requirements.budget_amount
    nights = requirements.duration_days or 1
    travelers = requirements.travelers or 1

    def proceed(note: str) -> Command:
        logger.info(note)
        return Command(update={"progress": [note]}, goto=Node.ITINERARY_AGENT)

    if budget is None or not state["hotels"]:
        return proceed("Budget check skipped: no budget or no hotels to price.")

    currencies = {f.currency for f in state["flights"]} | {
        h.currency for h in state["hotels"]
    }

    if currencies != {requirements.budget_currency}:
        return proceed(
            f"Budget check skipped: currency mismatch "
            f"({requirements.budget_currency} vs {sorted(currencies)})."
        )

    flight_cost = (
        min(f.price for f in state["flights"]) * travelers if state["flights"] else 0
    )
    # Worst case: the itinerary may pick any hotel we found.
    hotel_cost = max(h.price_per_night for h in state["hotels"]) * nights
    estimate = flight_cost + hotel_cost

    if estimate <= budget:
        return proceed(f"Budget check passed: estimated {estimate:,.0f} of {budget:,.0f}.")

    if state["budget_retries"] >= MAX_BUDGET_RETRIES:
        return proceed(
            f"Over budget (estimated {estimate:,.0f} of {budget:,.0f}); "
            "retry limit reached, continuing."
        )

    cap = (budget - flight_cost) / nights

    if cap <= 0:
        return proceed("Flights alone exceed the budget; hotels cannot fix that.")

    hint = f"maximum price per night {cap:,.0f} {requirements.budget_currency}"
    summary = (
        f"Over budget (estimated {estimate:,.0f} of {budget:,.0f}); "
        f"re-researching hotels with {hint}."
    )
    logger.info(summary)

    hints = {**state["research_hints"], Node.HOTEL_RESEARCH: hint}
    retries = state["budget_retries"] + 1

    # Send carries its own input, so the new hint must be in this payload too.
    payload = {**state, "research_hints": hints}

    return Command(
        update={
            "research_hints": hints,
            "budget_retries": retries,
            "progress": [summary],
        },
        goto=[Send(Node.HOTEL_RESEARCH, payload)],
    )
