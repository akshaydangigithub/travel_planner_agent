"""Generate the day-by-day itinerary from the combined research."""

from app.core.llm import get_llm
from app.core.logging import get_logger
from app.graph.state import TravelState
from app.prompts.itinerary import ITINERARY_SYSTEM_PROMPT, build_itinerary_prompt
from app.schemas import Itinerary

logger = get_logger(__name__)


def itinerary_agent(state: TravelState) -> dict:
    """Ask the model for a structured itinerary, fixing any earlier errors."""

    requirements = state["requirements"]

    if requirements is None:
        raise ValueError("Travel requirements are missing")

    logger.info("Generating itinerary...")

    structured_llm = get_llm().with_structured_output(Itinerary)

    prompt = build_itinerary_prompt(
        requirements=requirements,
        flights=state["flights"],
        hotels=state["hotels"],
        weather=state["weather"],
        activities=state["activities"],
        validation_errors=state["itinerary_errors"],
    )

    itinerary = structured_llm.invoke(
        [("system", ITINERARY_SYSTEM_PROMPT), ("human", prompt)]
    )

    return {
        "itinerary": itinerary,
        "progress": ["Itinerary generated."],
    }
