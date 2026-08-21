"""Nodes of the flight research subgraph."""

import json

from langchain_core.messages import ToolMessage

from app.graph.state import TravelState
from app.schemas import FlightResult

FLIGHT_TOOL_NAME = "search_flights"


def extract_flights(state: TravelState) -> dict:
    """Parse the most recent flight tool result into ``FlightResult`` models."""

    for message in reversed(state["messages"]):
        if isinstance(message, ToolMessage):
            if message.name == FLIGHT_TOOL_NAME:

                raw_flights = json.loads(message.content)

                flights = [FlightResult(**flight) for flight in raw_flights]

                return {"flights": flights}

    return {"flights": []}
