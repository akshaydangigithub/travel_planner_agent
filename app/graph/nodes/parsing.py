"""Turn the free form user request into structured requirements."""

from app.core.llm import get_llm
from app.core.logging import get_logger
from app.graph.state import TravelState
from app.prompts.planning import build_requirements_prompt, requirements_system_prompt
from app.schemas import TravelRequirements

logger = get_logger(__name__)


def extract_requirements(user_request: str, corrections: str) -> TravelRequirements:
    """Ask the model for structured requirements; corrections override."""

    structured_llm = get_llm().with_structured_output(TravelRequirements)
    prompt = build_requirements_prompt(user_request, corrections)

    return structured_llm.invoke(
        [("system", requirements_system_prompt()), ("human", prompt)]
    )


def parse_request(state: TravelState) -> dict:
    """Extract travel requirements from the request and any user correction."""

    logger.info("Parsing travel request...")

    return {
        "requirements": extract_requirements(
            state["user_request"], state["user_feedback"]
        )
    }
