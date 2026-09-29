"""Conditional edges shared by every research agent subgraph."""

from app.graph.constants import ResearchAgentRoute
from app.graph.subgraphs.research_agent.state import ResearchAgentState

MAX_TOOL_ROUNDS = 2


def route_agent(state: ResearchAgentState) -> str:
    """Run the tools when the agent asked for them, otherwise finish."""

    last_message = state["messages"][-1]

    if getattr(last_message, "tool_calls", None):
        return ResearchAgentRoute.TOOLS

    return ResearchAgentRoute.END


def route_after_extract(state: ResearchAgentState) -> str:
    """Finish as soon as results exist; give the agent one more try otherwise.

    Ending here instead of always looping back saves an LLM call per agent:
    the agent's closing summary was never used by the rest of the graph.
    """

    if state["results"] or state["tool_rounds"] >= MAX_TOOL_ROUNDS:
        return ResearchAgentRoute.END

    return ResearchAgentRoute.RETRY
