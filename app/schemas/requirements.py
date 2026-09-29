"""Structured travel requirements extracted from the user's request."""

from pydantic import BaseModel, Field


class TravelRequirements(BaseModel):
    # Required for planning, but optional here so the model can report
    # "not given" as null instead of inventing a placeholder value.
    # validate_requirements decides what is actually mandatory.
    origin: str | None = Field(
        default=None,
        description="City or country the trip starts from. Null if not stated.",
    )
    destination: str | None = Field(
        default=None,
        description="City or country to visit. Null if not stated.",
    )
    travelers: int | None = Field(
        default=None,
        description="Number of people travelling. Null if not stated.",
    )

    start_date: str | None = Field(
        default=None,
        description="Trip start date as YYYY-MM-DD. Null if not stated.",
    )
    end_date: str | None = Field(
        default=None,
        description="Trip end date as YYYY-MM-DD. Null if not stated.",
    )
    duration_days: int | None = Field(
        default=None,
        description="Trip length in days. Null if neither stated nor derivable from the dates.",
    )

    budget_amount: float | None = None
    budget_currency: str = "USD"

    interests: list[str] = []
    preferences: list[str] = []
