"""Flight research subgraph: a tool calling agent that returns flight options."""

from app.graph.subgraphs.flights.builder import FLIGHT_AGENT, flight_graph, flight_research

__all__ = ["FLIGHT_AGENT", "flight_graph", "flight_research"]
