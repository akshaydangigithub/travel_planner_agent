"""Assembly of the top level travel planning graph."""

from langgraph.graph import END, START, StateGraph

from app.graph.constants import Node, ValidationRoute
from app.graph.nodes import (
    ask_user,
    combine_research,
    continue_plan,
    parse_request,
    search_activities,
    search_hotels,
    search_weather,
    validate_requirements,
    itinerary_agent,
)
from app.graph.routers import route_after_validation
from app.graph.state import TravelState
from app.graph.subgraphs.flights import flight_graph

RESEARCH_NODES = (
    Node.FLIGHT_RESEARCH,
    Node.SEARCH_HOTELS,
    Node.SEARCH_WEATHER,
    Node.SEARCH_ACTIVITIES,
)


def build_travel_graph():
    """Wire parsing, validation, parallel research and aggregation together."""

    builder = StateGraph(TravelState)

    builder.add_node(Node.PARSE_REQUEST, parse_request)
    builder.add_node(Node.VALIDATE_REQUIREMENTS, validate_requirements)
    builder.add_node(Node.ASK_USER, ask_user)
    builder.add_node(Node.CONTINUE_PLAN, continue_plan)
    builder.add_node(Node.FLIGHT_RESEARCH, flight_graph)
    builder.add_node(Node.SEARCH_HOTELS, search_hotels)
    builder.add_node(Node.SEARCH_WEATHER, search_weather)
    builder.add_node(Node.SEARCH_ACTIVITIES, search_activities)
    builder.add_node(Node.COMBINE_RESEARCH, combine_research)
    builder.add_node(Node.ITINERARY_AGENT, itinerary_agent)

    builder.add_edge(START, Node.PARSE_REQUEST)
    builder.add_edge(Node.PARSE_REQUEST, Node.VALIDATE_REQUIREMENTS)

    builder.add_conditional_edges(
        Node.VALIDATE_REQUIREMENTS,
        route_after_validation,
        {
            ValidationRoute.ASK_USER: Node.ASK_USER,
            ValidationRoute.CONTINUE_PLAN: Node.CONTINUE_PLAN,
        },
    )

    builder.add_edge(Node.ASK_USER, Node.PARSE_REQUEST)

    for research_node in RESEARCH_NODES:
        builder.add_edge(Node.CONTINUE_PLAN, research_node)
        builder.add_edge(research_node, Node.COMBINE_RESEARCH)

    builder.add_edge(Node.COMBINE_RESEARCH, Node.ITINERARY_AGENT)

    builder.add_edge(Node.ITINERARY_AGENT, END)

    return builder.compile()


travel_graph = build_travel_graph()
