"""Turn the free form user request into structured requirements."""

from app.core.llm import get_llm
from app.core.logging import get_logger
from app.graph.state import TravelState
from app.prompts.planning import build_requirements_prompt
from app.schemas import TravelRequirements

logger = get_logger(__name__)


def parse_request(state: TravelState) -> TravelState:
    """Extract travel requirements from the request and any user correction."""

    logger.info("Parsing travel request...")

    structured_llm = get_llm().with_structured_output(TravelRequirements)

    prompt = build_requirements_prompt(
        state["user_request"],
        state["user_feedback"],
    )

    requirements = structured_llm.invoke(prompt)

    return {
        **state,
        "requirements": requirements,
    }
