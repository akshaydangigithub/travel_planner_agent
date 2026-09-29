"""Prompts used by the itinerary agent."""

import json

from pydantic import BaseModel

from app.schemas import (
    ActivityResult,
    FlightResult,
    HotelResult,
    TravelRequirements,
    WeatherReport,
)

ITINERARY_SYSTEM_PROMPT = """
You are a professional travel itinerary planner.

Create a practical day-by-day travel itinerary using only the
provided travel requirements and researched information.

Rules:
- Respect the requested destination and duration.
- Do not invent travel dates when dates were not provided.
- Use researched activities when creating the itinerary.
- Plan around the researched weather.
- Consider the user's interests and preferences.
- Keep each day realistic and logically organized.
- Return exactly the requested number of days.
"""


def _to_json(research: BaseModel | list[BaseModel] | None) -> str:
    """Render research results as JSON so the model reads clean data."""

    if research is None or research == []:
        return "No results."

    if isinstance(research, list):
        return json.dumps([item.model_dump() for item in research], indent=2)

    return research.model_dump_json(indent=2)


def build_itinerary_prompt(
    requirements: TravelRequirements,
    flights: list[FlightResult],
    hotels: list[HotelResult],
    weather: WeatherReport | None,
    activities: list[ActivityResult],
    validation_errors: list[str] | None = None,
) -> str:
    """Render the requirements, research and any earlier errors."""

    validation_errors = validation_errors or []

    if requirements.duration_days:
        task = (
            f"Create a {requirements.duration_days}-day itinerary "
            f"for {requirements.destination}."
        )
    else:
        task = (
            f"Create an itinerary of a sensible length "
            f"for {requirements.destination}."
        )

    return f"""
{task}

Travel requirements:
{requirements.model_dump_json(indent=2)}

Flight research:
{_to_json(flights)}

Hotel research:
{_to_json(hotels)}

Weather research:
{_to_json(weather)}

Activity research:
{_to_json(activities)}

Previous itinerary validation errors:
{validation_errors or "None."}

If previous itinerary validation errors are present, fix those problems
in the new itinerary.

Do not invent travel dates.

Return only the structured itinerary.
"""
