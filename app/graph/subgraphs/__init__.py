"""Subgraphs mounted as nodes inside the top level travel graph."""

from app.graph.subgraphs.activities import activity_research
from app.graph.subgraphs.flights import flight_research
from app.graph.subgraphs.hotels import hotel_research
from app.graph.subgraphs.weather import weather_research

__all__ = [
    "activity_research",
    "flight_research",
    "hotel_research",
    "weather_research",
]
