"""Flight search tool exposed to the flight research agent."""

from langchain_core.tools import tool

from app.core.config import get_settings
from app.integrations import serpapi


@tool
def search_flights(
    origin: str,
    destination: str,
    start_date: str | None = None,
    end_date: str | None = None,
    travelers: int = 1,
    currency: str | None = None,
) -> list[dict]:
    """
    Search for available flights.

    Returns flight options matching the requested
    route, dates, and number of travelers. Prices are per person,
    in the requested currency when one is given.
    """

    settings = get_settings()

    if settings.travel_data_provider == "live":
        return serpapi.search_flights(
            origin,
            destination,
            start_date,
            end_date,
            travelers,
            currency or settings.default_currency,
        )

    return [
        {
            "airline": airline,
            "origin": origin,
            "destination": destination,
            "departure": f"{start_date} {departs}" if start_date else None,
            "arrival": f"{start_date} {arrives}" if start_date else None,
            "travelers": travelers,
            "price": price,
            "currency": "INR",
            "flight_numbers": [number],
            "duration_minutes": duration,
            "stops": stops,
            "round_trip": bool(end_date),
        }
        for airline, number, departs, arrives, duration, stops, price in (
            ("Demo Airways", "DA 101", "06:10", "08:25", 135, 0, 42000),
            ("Sample Air", "SA 220", "13:40", "18:05", 265, 1, 31500),
        )
    ]


FLIGHT_TOOLS = [search_flights]
