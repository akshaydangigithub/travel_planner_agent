"""Hotel search tool exposed to the hotel research agent."""

from langchain_core.tools import tool


@tool
def search_hotels(
    destination: str,
    check_in: str | None = None,
    check_out: str | None = None,
    travelers: int = 1,
    max_price_per_night: float | None = None,
) -> list[dict]:
    """
    Search for hotels at the destination.

    Returns accommodation options for the requested
    stay dates and number of travelers. When max_price_per_night is
    given, only hotels at or below that price are returned.
    """

    hotels = [
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

    if max_price_per_night is not None:
        hotels = [h for h in hotels if h["price_per_night"] <= max_price_per_night]

    return hotels


HOTEL_TOOLS = [search_hotels]
