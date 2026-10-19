"""Live flights, hotels and places through SerpApi (Google Flights / Hotels / Maps).

Every function returns plain dicts shaped like the app's result schemas, so
the tools and the rest of the graph do not know which provider answered.
"""

from typing import Any

from app.core.config import get_settings
from app.core.logging import get_logger
from app.integrations.http import IntegrationError, get_json

logger = get_logger(__name__)

SERPAPI_URL = "https://serpapi.com/search"
MAX_FLIGHT_OPTIONS = 5
MAX_HOTEL_OPTIONS = 6
MAX_AMENITIES = 8
MAX_PLACES_PER_INTEREST = 4
MAX_INTERESTS = 4


def _search(params: dict[str, Any]) -> dict[str, Any]:
    body = get_json(
        SERPAPI_URL,
        params,
        secret_params={"api_key": get_settings().serpapi_api_key},
    )

    if body.get("error"):
        raise IntegrationError(f"SerpApi error: {body['error']}")

    return body


def resolve_location_id(place: str) -> str:
    """Turn a city/country name into a Google Flights id (airport code or kgmid)."""

    candidate = place.strip()

    if len(candidate) == 3 and candidate.isalpha() and candidate.isupper():
        return candidate

    body = _search({"engine": "google_flights_autocomplete", "q": candidate})

    for suggestion in body.get("suggestions", []):
        location_id = suggestion.get("id", "")

        if location_id.startswith(("/m/", "/g/")):
            return location_id

        airports = suggestion.get("airports") or []

        if airports and airports[0].get("id"):
            return airports[0]["id"]

    raise IntegrationError(f"No airport found for '{place}'")


def search_flights(
    origin: str,
    destination: str,
    start_date: str | None,
    end_date: str | None,
    travelers: int,
    currency: str,
) -> list[dict]:
    """Return flight options; ``price`` is per person."""

    if not start_date:
        logger.info("Live flight search needs a start date; returning no flights")
        return []

    body = _search(
        {
            "engine": "google_flights",
            "departure_id": resolve_location_id(origin),
            "arrival_id": resolve_location_id(destination),
            "outbound_date": start_date,
            "return_date": end_date,
            "type": 1 if end_date else 2,
            "adults": travelers,
            "currency": currency,
            "hl": "en",
        }
    )

    options = [*body.get("best_flights", []), *body.get("other_flights", [])]
    booking_url = (body.get("search_metadata") or {}).get("google_flights_url")
    results: list[dict] = []

    for option in options[:MAX_FLIGHT_OPTIONS]:
        legs = option.get("flights") or []

        if not legs or option.get("price") is None:
            continue

        airlines = list(dict.fromkeys(leg.get("airline", "Unknown") for leg in legs))
        first, last = legs[0], legs[-1]

        results.append(
            {
                "airline": " / ".join(airlines),
                "origin": origin,
                "destination": destination,
                "departure": first.get("departure_airport", {}).get("time"),
                "arrival": last.get("arrival_airport", {}).get("time"),
                "travelers": travelers,
                # Google Flights quotes the total for all passengers.
                "price": round(option["price"] / max(travelers, 1), 2),
                "currency": currency,
                "departure_airport": first.get("departure_airport", {}).get("id"),
                "arrival_airport": last.get("arrival_airport", {}).get("id"),
                "flight_numbers": [
                    leg["flight_number"] for leg in legs if leg.get("flight_number")
                ],
                "duration_minutes": option.get("total_duration"),
                "stops": len(legs) - 1,
                "round_trip": bool(end_date),
                "booking_url": booking_url,
            }
        )

    return results


def search_hotels(
    destination: str,
    check_in: str | None,
    check_out: str | None,
    travelers: int,
    currency: str,
    max_price_per_night: float | None,
) -> list[dict]:
    """Return hotel options with a nightly price."""

    if not (check_in and check_out):
        logger.info("Live hotel search needs both dates; returning no hotels")
        return []

    body = _search(
        {
            "engine": "google_hotels",
            "q": f"hotels in {destination}",
            "check_in_date": check_in,
            "check_out_date": check_out,
            "adults": travelers,
            "currency": currency,
            "max_price": int(max_price_per_night) if max_price_per_night else None,
            "hl": "en",
        }
    )

    results: list[dict] = []

    for hotel in body.get("properties", []):
        price = (hotel.get("rate_per_night") or {}).get("extracted_lowest")

        if price is None:
            continue

        if max_price_per_night is not None and price > max_price_per_night:
            continue

        gps = hotel.get("gps_coordinates") or {}
        images = hotel.get("images") or [{}]

        results.append(
            {
                "name": hotel.get("name", "Unnamed hotel"),
                "destination": destination,
                "check_in": check_in,
                "check_out": check_out,
                "travelers": travelers,
                "price_per_night": price,
                "currency": currency,
                "rating": hotel.get("overall_rating"),
                "reviews": hotel.get("reviews"),
                "hotel_class": hotel.get("hotel_class"),
                "amenities": (hotel.get("amenities") or [])[:MAX_AMENITIES],
                "latitude": gps.get("latitude"),
                "longitude": gps.get("longitude"),
                "image_url": images[0].get("thumbnail"),
                "link": hotel.get("link"),
            }
        )

        if len(results) >= MAX_HOTEL_OPTIONS:
            break

    return results


def search_places(destination: str, interests: list[str]) -> list[dict]:
    """Return well rated places matching each interest (no prices)."""

    results: list[dict] = []

    for interest in interests[:MAX_INTERESTS]:
        body = _search(
            {
                "engine": "google_maps",
                "type": "search",
                "q": f"{interest} in {destination}",
                "hl": "en",
            }
        )

        for place in body.get("local_results", [])[:MAX_PLACES_PER_INTEREST]:
            description = place.get("description") or place.get("type") or ""

            if place.get("rating"):
                description = f"{description} (rated {place['rating']})".strip()

            gps = place.get("gps_coordinates") or {}

            results.append(
                {
                    "name": place.get("title", "Unnamed place"),
                    "destination": destination,
                    "category": interest,
                    "description": description or f"{interest.title()} spot",
                    "duration_hours": None,
                    "price_per_person": None,
                    "currency": None,
                    "rating": place.get("rating"),
                    "reviews": place.get("reviews"),
                    "address": place.get("address"),
                    "latitude": gps.get("latitude"),
                    "longitude": gps.get("longitude"),
                    "image_url": place.get("thumbnail"),
                }
            )

    return results
