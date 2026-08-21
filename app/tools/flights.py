"""Flight search tool exposed to the flight research agent."""

from langchain_core.tools import tool


@tool
def search_flights(
    origin: str,
    destination: str,
    start_date: str | None = None,
    end_date: str | None = None,
    travelers: int = 1,
) -> list[dict]:
    """
    Search for available flights.

    Returns flight options matching the requested
    route, dates, and number of travelers.
    """

    return [
        {
            "airline": "Demo Airways",
            "origin": origin,
            "destination": destination,
            "departure": start_date,
            "arrival": end_date,
            "travelers": travelers,
            "price": 42000,
            "currency": "INR",
        }
    ]


FLIGHT_TOOLS = [search_flights]
