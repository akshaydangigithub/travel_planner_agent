"""Assembly of a research agent subgraph and its parent graph adapter."""

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode

from app.core.logging import get_logger
from app.graph.constants import ResearchAgentNode, ResearchAgentRoute
from app.graph.state import TravelState
from app.graph.subgraphs.research_agent.nodes import (
    make_agent_node,
    make_extract_node,
)
from app.graph.subgraphs.research_agent.routers import (
    route_after_extract,
    route_agent,
)
from app.graph.subgraphs.research_agent.spec import ResearchAgentSpec
from app.graph.subgraphs.research_agent.state import ResearchAgentState

logger = get_logger(__name__)


def build_research_agent(spec: ResearchAgentSpec) -> CompiledStateGraph:
    """Wire an agent, its tools and the result extraction together.

    START → agent ─┬─ tool call ──→ tools → extract ─┬─ results → END
                   │                                 └─ none → agent
                   └─ no tool call → END
    """

    builder = StateGraph(ResearchAgentState)

    builder.add_node(ResearchAgentNode.AGENT, make_agent_node(spec))
    builder.add_node(ResearchAgentNode.TOOLS, ToolNode(spec.tools))
    builder.add_node(ResearchAgentNode.EXTRACT, make_extract_node(spec))

    builder.add_edge(START, ResearchAgentNode.AGENT)

    builder.add_conditional_edges(
        ResearchAgentNode.AGENT,
        route_agent,
        {
            ResearchAgentRoute.TOOLS: ResearchAgentNode.TOOLS,
            ResearchAgentRoute.END: END,
        },
    )

    builder.add_edge(ResearchAgentNode.TOOLS, ResearchAgentNode.EXTRACT)

    builder.add_conditional_edges(
        ResearchAgentNode.EXTRACT,
        route_after_extract,
        {
            ResearchAgentRoute.RETRY: ResearchAgentNode.AGENT,
            ResearchAgentRoute.END: END,
        },
    )

    return builder.compile(name=f"{spec.name}_agent")


def make_research_node(spec: ResearchAgentSpec, graph: CompiledStateGraph):
    """Adapt a research subgraph to ``TravelState``.

    The subgraph has its own schema, so this node maps state in both
    directions: only the requirements go in (as the opening messages), and
    only the typed results come back out. The agent conversation stays
    inside the subgraph run.
    """

    def research(state: TravelState, config: RunnableConfig) -> dict:
        requirements = state["requirements"]

        if requirements is None:
            raise ValueError("Travel requirements are missing")

        request = spec.build_request_prompt(requirements)
        hint = state["research_hints"].get(f"{spec.name}_research")

        if hint:
            request += f"\nConstraint: {hint}"

        logger.info("Starting %s research", spec.name)

        result = graph.invoke(
            {
                "messages": [
                    SystemMessage(content=spec.system_prompt),
                    HumanMessage(content=request),
                ],
                "results": spec.empty_result(),
                "tool_rounds": 0,
            },
            config,
        )

        return {
            spec.result_key: result["results"],
            "progress": [f"{spec.name.capitalize()} research completed."],
        }

    research.__name__ = f"{spec.name}_research"

    return research
