"""Long-term memory kept about a traveller across planning sessions."""

from pydantic import BaseModel


class UserProfile(BaseModel):
    """Defaults learned from the trips a user approved."""

    home_origin: str | None = None
    currency: str | None = None
    interests: list[str] = []
    preferences: list[str] = []
    trips_planned: int = 0


class ThreadRecord(BaseModel):
    """Index entry for every trip a user started, approved or not."""

    thread_id: str
    request: str
    created_at: str


class TripSummary(BaseModel):
    """One approved trip, kept so users can see their planning history."""

    thread_id: str
    destination: str
    duration_days: int
    budget_amount: float | None = None
    budget_currency: str | None = None
    day_titles: list[str] = []
    approved_at: str
