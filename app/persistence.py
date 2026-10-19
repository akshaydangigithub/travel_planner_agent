"""Checkpointer (short-term, per thread) and store (long-term, per user).

Also the read/write helpers for long-term user memory, so graph nodes and
the API share one definition of where a profile lives.

The graph is compiled with both. Which backend is used is a deployment
decision made in settings, never in graph code:

- ``memory``: lost when the process exits; fine for experiments.
- ``sqlite``: a local file; lets the CLI resume a thread in a new process.
- ``postgres``: shared by every API worker; the production choice.
"""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.store.base import BaseStore
from langgraph.store.memory import InMemoryStore

from app.core.config import Settings
from app.core.logging import get_logger
from app.schemas import (
    ActivityResult,
    FlightResult,
    HotelResult,
    Itinerary,
    ItineraryDay,
    ThreadRecord,
    TravelRequirements,
    TripSummary,
    UserProfile,
    WeatherDay,
    WeatherReport,
)

logger = get_logger(__name__)

# Only our own models may be rebuilt from a checkpoint; anything else in the
# database is returned as plain data instead of being imported and executed.
_SERDE = JsonPlusSerializer(
    allowed_msgpack_modules=[
        ActivityResult,
        FlightResult,
        HotelResult,
        Itinerary,
        ItineraryDay,
        TravelRequirements,
        WeatherDay,
        WeatherReport,
    ]
)


@contextmanager
def open_persistence(
    settings: Settings,
) -> Iterator[tuple[BaseCheckpointSaver, BaseStore]]:
    """Open the configured checkpointer and store, closing them on exit."""

    backend = settings.persistence_backend
    logger.info("Using %s persistence", backend)

    if backend == "memory":
        yield InMemorySaver(serde=_SERDE), InMemoryStore()
        return

    if backend == "sqlite":
        from langgraph.checkpoint.sqlite import SqliteSaver
        from langgraph.store.sqlite import SqliteStore

        Path(settings.sqlite_path).parent.mkdir(parents=True, exist_ok=True)

        checkpoint_conn = sqlite3.connect(settings.sqlite_path, check_same_thread=False)
        store_conn = sqlite3.connect(
            settings.sqlite_path, check_same_thread=False, isolation_level=None
        )

        try:
            checkpointer = SqliteSaver(checkpoint_conn, serde=_SERDE)
            store = SqliteStore(store_conn)
            checkpointer.setup()
            store.setup()
            yield checkpointer, store
        finally:
            checkpoint_conn.close()
            store_conn.close()
        return

    from langgraph.checkpoint.postgres import PostgresSaver
    from langgraph.store.postgres import PostgresStore
    from psycopg.rows import dict_row
    from psycopg_pool import ConnectionPool

    with ConnectionPool(
        settings.database_url,
        kwargs={"autocommit": True, "prepare_threshold": 0, "row_factory": dict_row},
        open=True,
    ) as pool:
        checkpointer = PostgresSaver(pool, serde=_SERDE)
        store = PostgresStore(pool)
        checkpointer.setup()
        store.setup()
        yield checkpointer, store


# --- Long-term user memory -------------------------------------------------

PROFILE_KEY = "profile"
MAX_REMEMBERED_ITEMS = 15


def profile_namespace(user_id: str) -> tuple[str, ...]:
    return ("users", user_id)


def trips_namespace(user_id: str) -> tuple[str, ...]:
    return ("users", user_id, "trips")


def threads_namespace(user_id: str) -> tuple[str, ...]:
    return ("users", user_id, "threads")


def put_thread(store: BaseStore, user_id: str, record: ThreadRecord) -> None:
    store.put(threads_namespace(user_id), record.thread_id, record.model_dump())


def list_threads(store: BaseStore, user_id: str, limit: int = 50) -> list[ThreadRecord]:
    items = store.search(threads_namespace(user_id), limit=1000)
    records = [ThreadRecord.model_validate(item.value) for item in items]
    return sorted(records, key=lambda record: record.created_at, reverse=True)[:limit]


def get_profile(store: BaseStore, user_id: str) -> UserProfile:
    item = store.get(profile_namespace(user_id), PROFILE_KEY)
    return UserProfile.model_validate(item.value) if item else UserProfile()


def put_profile(store: BaseStore, user_id: str, profile: UserProfile) -> None:
    store.put(profile_namespace(user_id), PROFILE_KEY, profile.model_dump())


def list_trips(store: BaseStore, user_id: str, limit: int = 20) -> list[TripSummary]:
    items = store.search(trips_namespace(user_id), limit=limit)
    trips = [TripSummary.model_validate(item.value) for item in items]
    return sorted(trips, key=lambda trip: trip.approved_at, reverse=True)


def put_trip(store: BaseStore, user_id: str, trip: TripSummary) -> None:
    store.put(trips_namespace(user_id), trip.thread_id, trip.model_dump())


def delete_user_memory(store: BaseStore, user_id: str) -> None:
    """Forget everything stored about a user (profile, trip history, index)."""

    for namespace in (trips_namespace(user_id), threads_namespace(user_id)):
        for item in store.search(namespace, limit=1000):
            store.delete(namespace, item.key)

    store.delete(profile_namespace(user_id), PROFILE_KEY)


def merge_unique(existing: list[str], new: list[str]) -> list[str]:
    """Most recent first, case-insensitive de-duplication, bounded length."""

    merged: dict[str, str] = {}

    for value in [*new, *existing]:
        merged.setdefault(value.strip().casefold(), value.strip())

    return [value for value in merged.values() if value][:MAX_REMEMBERED_ITEMS]
