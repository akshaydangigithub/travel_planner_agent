"""Count a replanning attempt before the itinerary is regenerated."""

from app.core.logging import get_logger
from app.graph.state import TravelState

logger = get_logger(__name__)


def replan_itinerary(state: TravelState) -> dict:
    """Bump the retry counter.

    ``itinerary_errors`` is left untouched on purpose: the itinerary agent
    reads it to learn what to fix, and the validator overwrites it after
    the next attempt.
    """

    next_count = state["replan_count"] + 1

    logger.info("Replanning itinerary... attempt %s", next_count)

    return {
        "replan_count": next_count,
        "progress": [f"Replanning itinerary (attempt {next_count})."],
    }
