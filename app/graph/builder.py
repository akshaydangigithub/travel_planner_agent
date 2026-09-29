"""Assembly of the top level travel planning graph."""

from langgraph.graph import END, START, StateGraph

from app.graph.constants import ItineraryRoute, Node, ValidationRoute
from app.graph.nodes import (
    ask_user,
    combine_research,
    continue_plan,
    itinerary_agent,
    parse_request,
    replan_itinerary,
    validate_itinerary,
    validate_requirements,
)
from app.graph.routers import route_after_itinerary_validation, route_after_validation
from app.graph.state import TravelState
from app.graph.subgraphs import (
    activity_research,
    flight_research,
    hotel_research,
    weather_research,
)

RESEARCH_NODES = {
    Node.FLIGHT_RESEARCH: flight_research,
    Node.HOTEL_RESEARCH: hotel_research,
    Node.WEATHER_RESEARCH: weather_research,
    Node.ACTIVITY_RESEARCH: activity_research,
}


def build_travel_graph():
    """Wire parsing, validation, parallel research and itinerary planning."""

    builder = StateGraph(TravelState)

    builder.add_node(Node.PARSE_REQUEST, parse_request)
    builder.add_node(Node.VALIDATE_REQUIREMENTS, validate_requirements)
    builder.add_node(Node.ASK_USER, ask_user)
    builder.add_node(Node.CONTINUE_PLAN, continue_plan)
    builder.add_node(Node.COMBINE_RESEARCH, combine_research)
    builder.add_node(Node.ITINERARY_AGENT, itinerary_agent)
    builder.add_node(Node.ITINERARY_VALIDATION, validate_itinerary)
    builder.add_node(Node.REPLAN_ITINERARY, replan_itinerary)

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

    for name, research_node in RESEARCH_NODES.items():
        builder.add_node(name, research_node)
        builder.add_edge(Node.CONTINUE_PLAN, name)

    # A single edge from the list of branches makes combine_research wait
    # for all of them, rather than firing once per finished branch.
    builder.add_edge(list(RESEARCH_NODES), Node.COMBINE_RESEARCH)

    builder.add_edge(Node.COMBINE_RESEARCH, Node.ITINERARY_AGENT)
    builder.add_edge(Node.ITINERARY_AGENT, Node.ITINERARY_VALIDATION)

    builder.add_conditional_edges(
        Node.ITINERARY_VALIDATION,
        route_after_itinerary_validation,
        {
            ItineraryRoute.VALID: END,
            ItineraryRoute.REPLAN: Node.REPLAN_ITINERARY,
            ItineraryRoute.FAILED: END,
        },
    )

    builder.add_edge(Node.REPLAN_ITINERARY, Node.ITINERARY_AGENT)

    return builder.compile()


travel_graph = build_travel_graph()
