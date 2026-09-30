"""Node and route names, kept in one place so edges cannot drift."""


class Node:
    """Names of the nodes in the top level travel graph."""

    PARSE_REQUEST = "parse_request"
    VALIDATE_REQUIREMENTS = "validate_requirements"
    ASK_USER = "ask_user"
    CONTINUE_PLAN = "continue_plan"
    FLIGHT_RESEARCH = "flight_research"
    HOTEL_RESEARCH = "hotel_research"
    WEATHER_RESEARCH = "weather_research"
    ACTIVITY_RESEARCH = "activity_research"
    COMBINE_RESEARCH = "combine_research"
    ITINERARY_AGENT = "itinerary_agent"
    ITINERARY_VALIDATION = "validate_itinerary"
    REPLAN_ITINERARY = "replan_itinerary"
    SUPERVISOR = "supervisor"
    CHECK_BUDGET = "check_budget"


class ValidationRoute:
    """Branches taken after requirement validation."""

    ASK_USER = "ask_user"
    CONTINUE_PLAN = "continue_plan"


class ItineraryRoute:
    """Branches taken after itinerary validation."""

    VALID = "valid"
    REPLAN = "replan"
    FAILED = "failed"


class ResearchAgentNode:
    """Names of the nodes inside every research agent subgraph."""

    AGENT = "agent"
    TOOLS = "tools"
    EXTRACT = "extract"


class ResearchAgentRoute:
    """Branches taken inside a research agent subgraph."""

    TOOLS = "tools"
    RETRY = "retry"
    END = "end"
