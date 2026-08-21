"""The tool calling agent that researches flights."""

from functools import lru_cache

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.llm import get_llm
from app.core.logging import get_logger
from app.graph.state import TravelState
from app.prompts.flight_research import (
    FLIGHT_AGENT_SYSTEM_PROMPT,
    build_flight_request_prompt,
)
from app.tools import FLIGHT_TOOLS

logger = get_logger(__name__)


@lru_cache(maxsize=1)
def get_flight_llm():
    """Return the chat model bound to the flight research tools."""

    return get_llm().bind_tools(FLIGHT_TOOLS)


def _opening_messages(state: TravelState) -> list:
    requirements = state["requirements"]

    return [
        SystemMessage(content=FLIGHT_AGENT_SYSTEM_PROMPT),
        HumanMessage(content=build_flight_request_prompt(requirements)),
    ]


def flight_agent(state: TravelState) -> TravelState:
    """Ask the model for the next step of the flight research conversation."""

    logger.info("Calling flight agent")

    messages = state["messages"]

    if not messages:
        messages = _opening_messages(state)

    response = get_flight_llm().invoke(messages)

    if not state["messages"]:
        return {
            "messages": [
                *messages,
                response,
            ]
        }

    return {
        "messages": [response],
    }
