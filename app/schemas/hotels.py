"""Hotel search results."""

from pydantic import BaseModel


class HotelResult(BaseModel):
    name: str
    destination: str

    check_in: str | None = None
    check_out: str | None = None

    travelers: int

    price_per_night: float
    currency: str
    rating: float | None = None
