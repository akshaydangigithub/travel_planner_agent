"""Hotel search tool exposed to the hotel research agent."""

from langchain_core.tools import tool

from app.core.config import get_settings
from app.integrations import serpapi


@tool
def search_hotels(
    destination: str,
    check_in: str | None = None,
    check_out: str | None = None,
    travelers: int = 1,
    max_price_per_night: float | None = None,
    currency: str | None = None,
) -> list[dict]:
    """
    Search for hotels at the destination.

    Returns accommodation options for the requested
    stay dates and number of travelers. When max_price_per_night is
    given, only hotels at or below that price are returned.
    """

    settings = get_settings()

    if settings.travel_data_provider == "live":
        return serpapi.search_hotels(
            destination,
            check_in,
            check_out,
            travelers,
            currency or settings.default_currency,
            max_price_per_night,
        )

    hotels = [
        {
            "name": name,
            "destination": destination,
            "check_in": check_in,
            "check_out": check_out,
            "travelers": travelers,
            "price_per_night": price,
            "currency": "INR",
            "rating": rating,
            "reviews": reviews,
            "hotel_class": hotel_class,
            "amenities": amenities,
        }
        for name, price, rating, reviews, hotel_class, amenities in (
            ("Demo Central Hotel", 6000, 4.3, 1240, "4-star hotel",
             ["Free Wi-Fi", "Free breakfast", "Pool", "Restaurant"]),
            ("Demo Budget Inn", 3500, 3.9, 410, "2-star hotel",
             ["Free Wi-Fi", "Air conditioning"]),
        )
    ]

    if max_price_per_night is not None:
        hotels = [h for h in hotels if h["price_per_night"] <= max_price_per_night]

    return hotels


HOTEL_TOOLS = [search_hotels]
