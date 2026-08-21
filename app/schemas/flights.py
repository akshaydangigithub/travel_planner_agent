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
    currency: str
