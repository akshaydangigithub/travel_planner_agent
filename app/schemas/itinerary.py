"""The itinerary produced at the end of the planning run."""

from pydantic import BaseModel


class ItineraryDay(BaseModel):
    day: int
    title: str
    activities: list[str]


class Itinerary(BaseModel):
    destination: str
    duration_days: int
    days: list[ItineraryDay]
