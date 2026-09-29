"""Hotel search tool exposed to the hotel research agent."""

from langchain_core.tools import tool


@tool
def search_hotels(
    destination: str,
    check_in: str | None = None,
    check_out: str | None = None,
    travelers: int = 1,
) -> list[dict]:
    """
    Search for hotels at the destination.

    Returns accommodation options for the requested
    stay dates and number of travelers.
    """

    return [
        {
            "name": "Demo Central Hotel",
            "destination": destination,
            "check_in": check_in,
            "check_out": check_out,
            "travelers": travelers,
            "price_per_night": 6000,
            "currency": "INR",
            "rating": 4.3,
        },
        {
            "name": "Demo Budget Inn",
            "destination": destination,
            "check_in": check_in,
            "check_out": check_out,
            "travelers": travelers,
            "price_per_night": 3500,
            "currency": "INR",
            "rating": 3.9,
        },
    ]


HOTEL_TOOLS = [search_hotels]
