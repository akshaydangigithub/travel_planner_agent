"""Assembly of the flight research subgraph."""

from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from app.graph.constants import FlightNode, FlightRoute
from app.graph.state import TravelState
from app.graph.subgraphs.flights.agent import flight_agent
from app.graph.subgraphs.flights.nodes import extract_flights
from app.graph.subgraphs.flights.routers import route_flight_agent
from app.tools import FLIGHT_TOOLS


def build_flight_graph():
    """Wire the flight agent, its tools and the result extraction together."""

    builder = StateGraph(TravelState)

    builder.add_node(FlightNode.AGENT, flight_agent)
    builder.add_node(FlightNode.TOOLS, ToolNode(FLIGHT_TOOLS))
    builder.add_node(FlightNode.EXTRACT_FLIGHTS, extract_flights)

    builder.add_edge(START, FlightNode.AGENT)

    builder.add_conditional_edges(
        FlightNode.AGENT,
        route_flight_agent,
        {
            FlightRoute.TOOLS: FlightNode.TOOLS,
            FlightRoute.END: END,
        },
    )

    builder.add_edge(FlightNode.TOOLS, FlightNode.EXTRACT_FLIGHTS)
    builder.add_edge(FlightNode.EXTRACT_FLIGHTS, FlightNode.AGENT)

    return builder.compile()


flight_graph = build_flight_graph()
