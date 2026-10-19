"""Prompts used by the itinerary agent."""

import json

from pydantic import BaseModel

from app.costing import pick_flight, pick_hotel, stay_cost
from app.schemas import (
    ActivityResult,
    FlightResult,
    HotelResult,
    Itinerary,
    TravelRequirements,
    WeatherReport,
)

ITINERARY_SYSTEM_PROMPT = """
You are a professional travel itinerary planner.

Create a practical day-by-day travel itinerary using only the
provided travel requirements and researched information.

Rules:
- Respect the requested destination and duration; return exactly the
  requested number of days, numbered from 1.
- Give each day its calendar date, counting from the trip start date.
- Day 1 starts with the arrival and the last day ends with the departure;
  if the arrival airport is not at the destination, include the ground
  transfer and say how long it takes in getting_there.
- Build days around the researched places and use their exact names in
  each day's places list. Group places that are close to each other.
- Plan around the weather: outdoor plans on the dry days, indoor
  alternatives on rainy ones, and a weather_note for every day.
- Recommend one researched flight (flight_choice) and one researched hotel
  (hotel_choice) that fit the budget, copying the name exactly.
- Estimate each day's spend for the whole group on food, tickets and local
  transport (estimated_cost, in the budget currency). Keep the total within
  the daily allowance given below when there is one.
- Consider the traveller's interests and preferences, and keep each day
  realistic: no more than three or four main stops.
- If flights_booked or accommodation_booked is true, the traveller has
  already arranged that part; do not recommend one.
- Add a packing list suited to the weather and activities, and a few
  practical local tips.
- When the traveller requested changes to a previous itinerary, apply
  them and keep everything they did not ask to change.
"""


def _to_json(research: BaseModel | list[BaseModel] | None) -> str:
    """Render research results as JSON so the model reads clean data."""

    if research is None or research == []:
        return "No results."

    if isinstance(research, list):
        return json.dumps([item.model_dump() for item in research], indent=2)

    return research.model_dump_json(indent=2)


def _revision_section(
    change_requests: str, previous_itinerary: Itinerary | None
) -> str:
    """Show the traveller's change requests and the itinerary they reviewed."""

    if not change_requests:
        return ""

    previous = _to_json(previous_itinerary)

    return f"""
Previous itinerary shown to the traveller:
{previous}

Traveller's requested changes:
{change_requests}
"""


def _budget_section(
    requirements: TravelRequirements,
    flights: list[FlightResult],
    hotels: list[HotelResult],
) -> str:
    """Tell the model how much is left per day after travel and lodging."""

    budget = requirements.budget_amount

    if budget is None:
        return "Budget: not given; keep daily spending moderate."

    flight = None if requirements.flights_booked else pick_flight(flights)
    hotel = None if requirements.accommodation_booked else pick_hotel(hotels)
    flight_cost, hotel_cost = stay_cost(requirements, flight, hotel)
    days = requirements.duration_days or 1
    allowance = (budget - flight_cost - hotel_cost) / days
    currency = requirements.budget_currency

    if allowance <= 0:
        return (
            f"Budget: {budget:,.0f} {currency}. The cheapest flight and hotel "
            f"already cost {flight_cost + hotel_cost:,.0f}; plan low-cost days "
            "and say in the overview that the budget is too tight."
        )

    return (
        f"Budget: {budget:,.0f} {currency} in total. Cheapest flights cost "
        f"{flight_cost:,.0f} and the cheapest hotel {hotel_cost:,.0f}, leaving "
        f"about {allowance:,.0f} {currency} per day for the group."
    )


def build_itinerary_prompt(
    requirements: TravelRequirements,
    flights: list[FlightResult],
    hotels: list[HotelResult],
    weather: WeatherReport | None,
    activities: list[ActivityResult],
    validation_errors: list[str] | None = None,
    change_requests: str = "",
    previous_itinerary: Itinerary | None = None,
    assumptions: list[str] | None = None,
) -> str:
    """Render the requirements, research and any earlier errors."""

    validation_errors = validation_errors or []
    assumed = "\n".join(f"- {note}" for note in assumptions or []) or "None."

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

Defaults the planner assumed (mention assumed dates in the overview):
{assumed}

{_budget_section(requirements, flights, hotels)}

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
{_revision_section(change_requests, previous_itinerary)}
Return only the structured itinerary.
"""
