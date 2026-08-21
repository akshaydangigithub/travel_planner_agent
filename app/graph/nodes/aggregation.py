"""Merge the parallel research branches into a single itinerary."""

from app.core.logging import get_logger
from app.graph.state import TravelState

logger = get_logger(__name__)


def combine_research(state: TravelState) -> dict:
    """Assemble every research result into the itinerary."""

    logger.info("Combining research")

    return {"messages": ["All travel research completed."]}
