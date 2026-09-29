"""The flight research agent: a spec for the shared research subgraph."""

from app.graph.subgraphs.research_agent import (
    ResearchAgentSpec,
    build_research_agent,
    make_research_node,
)
from app.prompts.flight_research import (
    FLIGHT_AGENT_SYSTEM_PROMPT,
    build_flight_request_prompt,
)
from app.schemas import FlightResult
from app.tools import FLIGHT_TOOLS

FLIGHT_AGENT = ResearchAgentSpec(
    name="flight",
    result_key="flights",
    system_prompt=FLIGHT_AGENT_SYSTEM_PROMPT,
    build_request_prompt=build_flight_request_prompt,
    tools=FLIGHT_TOOLS,
    result_type=list[FlightResult],
)

flight_graph = build_research_agent(FLIGHT_AGENT)
flight_research = make_research_node(FLIGHT_AGENT, flight_graph)
