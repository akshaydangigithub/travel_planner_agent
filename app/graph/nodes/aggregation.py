"""Fan-in point where the parallel research branches meet."""

from app.core.logging import get_logger
from app.graph.state import TravelState

logger = get_logger(__name__)


def combine_research(state: TravelState) -> dict:
    """Wait for every research branch, then report what was found."""

    logger.info(
        "Combining research: %d flights, %d hotels, weather %s, %d activities",
        len(state["flights"]),
        len(state["hotels"]),
        "found" if state["weather"] else "missing",
        len(state["activities"]),
    )

    return {"progress": ["All travel research completed."]}
