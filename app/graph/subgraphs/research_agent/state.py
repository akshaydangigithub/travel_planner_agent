"""Private state of a research agent subgraph.

Each agent run gets its own copy of this state, so its conversation never
leaks into ``TravelState`` or into a sibling agent running in parallel.
"""

from typing import Annotated, Any, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


class ResearchAgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    results: Any
    tool_rounds: int
