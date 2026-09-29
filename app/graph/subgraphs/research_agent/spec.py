"""Declarative description of one specialised research agent."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any

from langchain_core.tools import BaseTool

from app.schemas import TravelRequirements


@dataclass(frozen=True)
class ResearchAgentSpec:
    """Everything that differs between the flight, hotel, weather and
    activity agents. The graph wiring itself is shared."""

    name: str
    """Short name used in node names, logs and progress messages."""

    result_key: str
    """``TravelState`` key the extracted results are written to."""

    system_prompt: str
    build_request_prompt: Callable[[TravelRequirements], str]

    tools: Sequence[BaseTool]

    result_type: Any
    """Type the tool output is validated into, e.g. ``list[FlightResult]``."""

    empty_result: Callable[[], Any] = field(default=list)
    """Factory for the value written when the tool produced nothing usable."""
