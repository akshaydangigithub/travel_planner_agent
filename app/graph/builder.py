"""Assembly of the top level travel planning graph."""

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.store.base import BaseStore

from app.graph.constants import ItineraryRoute, Node, ValidationRoute
from app.graph.nodes import (
    apply_revision,
    ask_user,
    check_budget,
    combine_research,
    continue_plan,
    itinerary_agent,
    load_profile,
    parse_request,
    replan_itinerary,
    review_itinerary,
    save_profile,
    supervisor,
    validate_itinerary,
    validate_requirements,
)
from app.graph.routers import (
    route_after_itinerary_validation,
    route_after_validation,
    route_research_agents,
)
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


def build_travel_graph(
    checkpointer: BaseCheckpointSaver | None = None,
    store: BaseStore | None = None,
) -> CompiledStateGraph:
    """Wire parsing, validation, parallel research and itinerary planning.

    ``ask_user`` and ``review_itinerary`` call ``interrupt()``, which needs a
    checkpointer; ``load_profile``/``save_profile`` use the store. Both are
    injected so the CLI and the API choose the backend (see app.persistence).
    """

    builder = StateGraph(TravelState)

    builder.add_node(Node.LOAD_PROFILE, load_profile)
    builder.add_node(Node.PARSE_REQUEST, parse_request)
    builder.add_node(Node.VALIDATE_REQUIREMENTS, validate_requirements)
    builder.add_node(Node.ASK_USER, ask_user)
    builder.add_node(Node.CONTINUE_PLAN, continue_plan)
    builder.add_node(Node.SUPERVISOR, supervisor)
    builder.add_node(Node.COMBINE_RESEARCH, combine_research)
    builder.add_node(Node.CHECK_BUDGET, check_budget)
    builder.add_node(Node.ITINERARY_AGENT, itinerary_agent)
    builder.add_node(Node.ITINERARY_VALIDATION, validate_itinerary)
    builder.add_node(Node.REPLAN_ITINERARY, replan_itinerary)
    # review_itinerary returns a Command (approve / revise / reject).
    builder.add_node(Node.REVIEW_ITINERARY, review_itinerary)
    # apply_revision also returns a Command: re-research, re-check the
    # budget or only rewrite the itinerary, depending on what changed.
    builder.add_node(Node.APPLY_REVISION, apply_revision)
    builder.add_node(Node.SAVE_PROFILE, save_profile)

    builder.add_edge(START, Node.LOAD_PROFILE)
    builder.add_edge(Node.LOAD_PROFILE, Node.PARSE_REQUEST)
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

    # Register all available research agents.
    # The supervisor decides which ones actually run.
    for name, research_node in RESEARCH_NODES.items():
        builder.add_node(name, research_node)

    builder.add_edge(
        Node.CONTINUE_PLAN,
        Node.SUPERVISOR,
    )

    builder.add_conditional_edges(
        Node.SUPERVISOR,
        route_research_agents,
        [*RESEARCH_NODES, Node.COMBINE_RESEARCH],
    )

    # One edge per branch, not add_edge([...], ...): a list edge waits for
    # every listed node, so it would never fire when a branch was skipped.
    # All dispatched branches finish in the same step, so combine_research
    # still runs once.
    for name in RESEARCH_NODES:
        builder.add_edge(name, Node.COMBINE_RESEARCH)

    # check_budget returns a Command, so it needs no outgoing edges here.
    builder.add_edge(Node.COMBINE_RESEARCH, Node.CHECK_BUDGET)
    builder.add_edge(Node.ITINERARY_AGENT, Node.ITINERARY_VALIDATION)

    builder.add_conditional_edges(
        Node.ITINERARY_VALIDATION,
        route_after_itinerary_validation,
        {
            ItineraryRoute.VALID: Node.REVIEW_ITINERARY,
            ItineraryRoute.REPLAN: Node.REPLAN_ITINERARY,
            ItineraryRoute.FAILED: END,
        },
    )

    builder.add_edge(Node.REPLAN_ITINERARY, Node.ITINERARY_AGENT)
    builder.add_edge(Node.SAVE_PROFILE, END)

    return builder.compile(checkpointer=checkpointer, store=store)
