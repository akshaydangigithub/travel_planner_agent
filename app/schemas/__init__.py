"""Pydantic models describing the data that flows through the graph."""

from app.schemas.activities import ActivityResult
from app.schemas.costs import CostBreakdown, CostLine
from app.schemas.flights import FlightResult
from app.schemas.hotels import HotelResult
from app.schemas.itinerary import Itinerary, ItineraryDay
from app.schemas.profile import ThreadRecord, TripSummary, UserProfile
from app.schemas.requirements import TravelRequirements
from app.schemas.weather import WeatherDay, WeatherReport

__all__ = [
    "ActivityResult",
    "CostBreakdown",
    "CostLine",
    "FlightResult",
    "HotelResult",
    "Itinerary",
    "ItineraryDay",
    "ThreadRecord",
    "TravelRequirements",
    "TripSummary",
    "UserProfile",
    "WeatherDay",
    "WeatherReport",
]
