"""Pydantic models describing the data that flows through the graph."""

from app.schemas.activities import ActivityResult
from app.schemas.flights import FlightResult
from app.schemas.hotels import HotelResult
from app.schemas.itinerary import Itinerary, ItineraryDay
from app.schemas.requirements import TravelRequirements
from app.schemas.weather import WeatherReport

__all__ = [
    "ActivityResult",
    "FlightResult",
    "HotelResult",
    "Itinerary",
    "ItineraryDay",
    "TravelRequirements",
    "WeatherReport",
]
