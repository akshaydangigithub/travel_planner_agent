"""The weather research agent: a spec for the shared research subgraph."""

from app.graph.subgraphs.research_agent import (
    ResearchAgentSpec,
    build_research_agent,
    make_research_node,
)
from app.prompts.weather_research import (
    WEATHER_AGENT_SYSTEM_PROMPT,
    build_weather_request_prompt,
)
from app.schemas import WeatherReport
from app.tools import WEATHER_TOOLS

WEATHER_AGENT = ResearchAgentSpec(
    name="weather",
    result_key="weather",
    system_prompt=WEATHER_AGENT_SYSTEM_PROMPT,
    build_request_prompt=build_weather_request_prompt,
    tools=WEATHER_TOOLS,
    result_type=WeatherReport | None,
    empty_result=lambda: None,
)

weather_graph = build_research_agent(WEATHER_AGENT)
weather_research = make_research_node(WEATHER_AGENT, weather_graph)
