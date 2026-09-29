"""Node factories shared by every research agent subgraph."""

from functools import lru_cache

from langchain_core.messages import AIMessage, AnyMessage, ToolMessage
from pydantic import TypeAdapter, ValidationError

from app.core.llm import get_llm
from app.core.logging import get_logger
from app.graph.subgraphs.research_agent.spec import ResearchAgentSpec
from app.graph.subgraphs.research_agent.state import ResearchAgentState

logger = get_logger(__name__)


def make_agent_node(spec: ResearchAgentSpec):
    """Build the node that asks the tool-bound model for its next step."""

    @lru_cache(maxsize=1)
    def get_agent_llm():
        return get_llm().bind_tools(spec.tools)

    def agent(state: ResearchAgentState) -> dict:
        logger.info("Calling %s agent", spec.name)

        response = get_agent_llm().invoke(state["messages"])

        return {"messages": [response]}

    return agent


def _latest_tool_messages(messages: list[AnyMessage]) -> list[ToolMessage]:
    """Return the tool results produced for the most recent AI tool call."""

    latest: list[ToolMessage] = []

    for message in reversed(messages):
        if isinstance(message, AIMessage):
            break

        if isinstance(message, ToolMessage):
            latest.append(message)

    return list(reversed(latest))


def make_extract_node(spec: ResearchAgentSpec):
    """Build the node that validates tool output into the spec's result type."""

    adapter = TypeAdapter(spec.result_type)
    tool_names = {tool.name for tool in spec.tools}

    def extract(state: ResearchAgentState) -> dict:
        results = None

        for message in _latest_tool_messages(state["messages"]):
            if message.name not in tool_names:
                continue

            if message.status == "error" or not isinstance(message.content, str):
                logger.warning("%s tool failed: %s", spec.name, message.content)
                continue

            try:
                parsed = adapter.validate_json(message.content)
            except ValidationError as error:
                logger.warning("Invalid %s tool output: %s", spec.name, error)
                continue

            if isinstance(parsed, list):
                results = [*(results or []), *parsed]
            else:
                results = parsed

        return {
            "results": spec.empty_result() if results is None else results,
            "tool_rounds": state["tool_rounds"] + 1,
        }

    return extract
