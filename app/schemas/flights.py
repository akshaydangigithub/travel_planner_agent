"""Flight search results."""

from pydantic import BaseModel


class FlightResult(BaseModel):
    airline: str
    origin: str
    destination: str

    departure: str | None = None
    arrival: str | None = None

    travelers: int

    price: float
    """Per person; for a round trip this covers both directions."""
    currency: str

    departure_airport: str | None = None
    arrival_airport: str | None = None
    """IATA codes; the arrival airport can be near, not at, the destination."""
    flight_numbers: list[str] = []
    duration_minutes: int | None = None
    stops: int | None = None
    round_trip: bool = False
    booking_url: str | None = None
