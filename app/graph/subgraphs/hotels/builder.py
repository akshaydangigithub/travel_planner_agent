"""The hotel research agent: a spec for the shared research subgraph."""

from app.graph.subgraphs.research_agent import (
    ResearchAgentSpec,
    build_research_agent,
    make_research_node,
)
from app.prompts.hotel_research import (
    HOTEL_AGENT_SYSTEM_PROMPT,
    build_hotel_request_prompt,
)
from app.schemas import HotelResult
from app.tools import HOTEL_TOOLS

HOTEL_AGENT = ResearchAgentSpec(
    name="hotel",
    result_key="hotels",
    system_prompt=HOTEL_AGENT_SYSTEM_PROMPT,
    build_request_prompt=build_hotel_request_prompt,
    tools=HOTEL_TOOLS,
    result_type=list[HotelResult],
)

hotel_graph = build_research_agent(HOTEL_AGENT)
hotel_research = make_research_node(HOTEL_AGENT, hotel_graph)
