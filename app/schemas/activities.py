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
