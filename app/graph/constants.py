"""Node and route names, kept in one place so edges cannot drift."""


class Node:
    """Names of the nodes in the top level travel graph."""

    PARSE_REQUEST = "parse_request"
    VALIDATE_REQUIREMENTS = "validate_requirements"
    ASK_USER = "ask_user"
    CONTINUE_PLAN = "continue_plan"
    FLIGHT_RESEARCH = "flight_research"
    SEARCH_HOTELS = "search_hotels"
    SEARCH_WEATHER = "search_weather"
    SEARCH_ACTIVITIES = "search_activities"
    COMBINE_RESEARCH = "combine_research"
    ITINERARY_AGENT = "itinerary_agent"


class ValidationRoute:
    """Branches taken after requirement validation."""

    ASK_USER = "ask_user"
    CONTINUE_PLAN = "continue_plan"


class FlightNode:
    """Names of the nodes in the flight research subgraph."""

    AGENT = "flight_agent"
    TOOLS = "tools"
    EXTRACT_FLIGHTS = "extract_flights"


class FlightRoute:
    """Branches taken after the flight agent replies."""

    TOOLS = "tools"
    END = "end"
