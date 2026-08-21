"""Conditional edges for the flight research subgraph."""

from app.graph.constants import FlightRoute
from app.graph.state import TravelState


def route_flight_agent(state: TravelState) -> str:
    """Run the tools when the agent asked for them, otherwise finish."""

    last_message = state["messages"][-1]

    if last_message.tool_calls:
        return FlightRoute.TOOLS

    return FlightRoute.END
