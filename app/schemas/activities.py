"""Activity search results."""

from pydantic import BaseModel


class ActivityResult(BaseModel):
    name: str
    destination: str
    category: str
    description: str

    duration_hours: float | None = None
    price_per_person: float | None = None
    currency: str | None = None

    rating: float | None = None
    reviews: int | None = None
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    image_url: str | None = None
