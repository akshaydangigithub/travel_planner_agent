"""The itinerary produced at the end of the planning run.

Field descriptions double as instructions for the model's structured
output. Everything after ``activities`` is optional so older saved trips
still load.
"""

from pydantic import BaseModel, Field


class ItineraryDay(BaseModel):
    day: int
    title: str
    activities: list[str] = Field(
        description="Ordered plan for the day, each entry starting with "
        "'Morning:', 'Afternoon:' or 'Evening:'."
    )

    date: str | None = Field(
        default=None, description="YYYY-MM-DD when the trip has dates, else null."
    )
    places: list[str] = Field(
        default=[],
        description="Names of researched places or hotels visited this day, "
        "copied exactly from the research.",
    )
    estimated_cost: float | None = Field(
        default=None,
        description="Spend for the whole group this day on food, tickets and "
        "local transport, in the budget currency. Excludes flights and hotel.",
    )
    weather_note: str | None = Field(
        default=None, description="One short line on the expected weather."
    )


class Itinerary(BaseModel):
    destination: str
    duration_days: int
    days: list[ItineraryDay]

    overview: str | None = Field(
        default=None, description="Two or three sentences summarising the trip."
    )
    getting_there: str | None = Field(
        default=None,
        description="How to reach the destination, including any ground "
        "transfer from the arrival airport.",
    )
    flight_choice: str | None = Field(
        default=None,
        description="Airline of the recommended researched flight, copied "
        "exactly; null when flights are booked or none were found.",
    )
    hotel_choice: str | None = Field(
        default=None,
        description="Name of the recommended researched hotel, copied exactly; "
        "null when accommodation is booked or none were found.",
    )
    packing_list: list[str] = Field(
        default=[], description="What to pack for this weather and these activities."
    )
    tips: list[str] = Field(
        default=[], description="Practical local tips (transport, money, customs)."
    )
