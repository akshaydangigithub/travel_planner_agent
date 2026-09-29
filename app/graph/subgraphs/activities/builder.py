"""The activity research agent: a spec for the shared research subgraph."""

from app.graph.subgraphs.research_agent import (
    ResearchAgentSpec,
    build_research_agent,
    make_research_node,
)
from app.prompts.activity_research import (
    ACTIVITY_AGENT_SYSTEM_PROMPT,
    build_activity_request_prompt,
)
from app.schemas import ActivityResult
from app.tools import ACTIVITY_TOOLS

ACTIVITY_AGENT = ResearchAgentSpec(
    name="activity",
    result_key="activities",
    system_prompt=ACTIVITY_AGENT_SYSTEM_PROMPT,
    build_request_prompt=build_activity_request_prompt,
    tools=ACTIVITY_TOOLS,
    result_type=list[ActivityResult],
)

activity_graph = build_research_agent(ACTIVITY_AGENT)
activity_research = make_research_node(ACTIVITY_AGENT, activity_graph)
