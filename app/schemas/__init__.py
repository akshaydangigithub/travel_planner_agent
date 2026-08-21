"""Pydantic models describing the data that flows through the graph."""

from app.schemas.flights import FlightResult
from app.schemas.itinerary import Itinerary, ItineraryDay
from app.schemas.requirements import TravelRequirements

__all__ = [
    "FlightResult",
    "Itinerary",
    "ItineraryDay",
    "TravelRequirements",
]
