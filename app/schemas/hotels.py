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

    reviews: int | None = None
    hotel_class: str | None = None
    amenities: list[str] = []
    latitude: float | None = None
    longitude: float | None = None
    image_url: str | None = None
    link: str | None = None
