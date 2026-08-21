"""Structured travel requirements extracted from the user's request."""

from pydantic import BaseModel


class TravelRequirements(BaseModel):
    origin: str
    destination: str
    travelers: int

    start_date: str | None = None
    end_date: str | None = None
    duration_days: int | None = None

    budget_amount: float | None = None
    budget_currency: str = "USD"

    interests: list[str] = []
    preferences: list[str] = []
