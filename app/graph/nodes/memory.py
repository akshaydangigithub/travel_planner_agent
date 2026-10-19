"""Long-term memory: load the traveller's profile, learn from approved trips.

The checkpointer remembers one conversation (a thread). The store remembers
the *user* across threads, namespaced by ``user_id``.
"""

from datetime import UTC, datetime

from langgraph.config import get_config
from langgraph.runtime import Runtime

from app.core.logging import get_logger
from app.graph.state import TravelState
from app.persistence import get_profile, merge_unique, put_profile, put_trip
from app.schemas import TripSummary

logger = get_logger(__name__)


def load_profile(state: TravelState, runtime: Runtime) -> dict:
    """Read the saved profile so validation can fill unstated defaults."""

    if runtime.store is None:
        return {"user_profile": {}}

    profile = get_profile(runtime.store, state["user_id"])

    if profile.trips_planned:
        note = f"Loaded traveller profile ({profile.trips_planned} past trips)."
    else:
        note = "No saved traveller profile yet."

    logger.info(note)

    return {"user_profile": profile.model_dump(), "progress": [note]}


def save_profile(state: TravelState, runtime: Runtime) -> dict:
    """Remember what the approved trip taught us about the traveller."""

    requirements = state["requirements"]
    itinerary = state["itinerary"]

    if runtime.store is None or requirements is None or itinerary is None:
        return {}

    store = runtime.store
    user_id = state["user_id"]
    profile = get_profile(store, user_id)

    profile = profile.model_copy(
        update={
            "home_origin": requirements.origin or profile.home_origin,
            "currency": (
                requirements.budget_currency
                if requirements.budget_amount is not None
                else profile.currency
            ),
            "interests": merge_unique(profile.interests, requirements.interests),
            "preferences": merge_unique(profile.preferences, requirements.preferences),
            "trips_planned": profile.trips_planned + 1,
        }
    )
    put_profile(store, user_id, profile)

    put_trip(
        store,
        user_id,
        TripSummary(
            thread_id=get_config()["configurable"]["thread_id"],
            destination=itinerary.destination,
            duration_days=itinerary.duration_days,
            budget_amount=requirements.budget_amount,
            budget_currency=requirements.budget_currency,
            day_titles=[day.title for day in itinerary.days],
            approved_at=datetime.now(UTC).isoformat(),
        ),
    )

    logger.info("Saved profile and trip for user %s", user_id)

    return {"progress": ["Saved trip and updated traveller profile."]}
