"""Run, stream, pause and resume planning threads.

Shared by the CLI and the HTTP API so both drive the graph the same way:

- every trip is one checkpointed thread (``thread_id``);
- a run streams events until it finishes or pauses on ``interrupt()``;
- a paused run is resumed with ``Command(resume=answer)``;
- a run that crashed (e.g. provider quota) is retried from its last
  checkpoint by streaming ``None``.
"""

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any, Literal

from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command
from pydantic import BaseModel

from app.core.logging import get_logger
from app.graph import initial_state
from app.graph.constants import InterruptKind
from app.services.assistant import answer_trip_question
from app.persistence import (
    delete_user_memory,
    get_profile,
    list_threads,
    list_trips,
    put_thread,
)
from app.costing import estimate_trip_cost
from app.schemas import (
    ActivityResult,
    CostBreakdown,
    FlightResult,
    HotelResult,
    Itinerary,
    ThreadRecord,
    TravelRequirements,
    TripSummary,
    UserProfile,
    WeatherReport,
)

logger = get_logger(__name__)

TripStatus = Literal[
    "needs_input",       # paused: requirements incomplete
    "awaiting_review",   # paused: itinerary ready for approval
    "approved",
    "rejected",
    "failed",            # itinerary never passed validation
    "incomplete",        # stopped by an error; can be retried
]


class TripNotFound(LookupError):
    """No thread with this id exists for this user."""


class TripNotPaused(RuntimeError):
    """A resume was sent to a thread that is not waiting for input."""


class TripSnapshot(BaseModel):
    """What a client needs to know about a trip right now."""

    thread_id: str
    status: TripStatus
    request: str = ""
    pending: dict[str, Any] | None = None
    """The interrupt payload when the trip is paused."""

    requirements: TravelRequirements | None = None
    assumptions: list[str] = []
    """Defaults the planner chose, e.g. assumed travel dates."""

    flights: list[FlightResult] = []
    hotels: list[HotelResult] = []
    weather: WeatherReport | None = None
    activities: list[ActivityResult] = []

    itinerary: Itinerary | None = None
    itinerary_errors: list[str] = []
    costs: CostBreakdown | None = None
    """Recommended flight and hotel plus planned daily spend vs the budget."""

    progress: list[str] = []


class TripListItem(BaseModel):
    thread_id: str
    request: str
    created_at: str
    status: TripStatus


class UserMemory(BaseModel):
    profile: UserProfile
    trips: list[TripSummary]


Event = dict[str, Any]


class TripPlanner:
    """Facade over the compiled, checkpointed travel graph."""

    def __init__(self, graph: CompiledStateGraph) -> None:
        self.graph = graph

    @staticmethod
    def _config(thread_id: str) -> dict:
        return {"configurable": {"thread_id": thread_id}}

    # --- running -----------------------------------------------------------

    def start(
        self, user_id: str, request: str, thread_id: str | None = None
    ) -> tuple[str, Iterator[Event]]:
        """Start a new trip; returns its thread id and the event stream."""

        thread_id = thread_id or str(uuid.uuid4())
        logger.info("Starting trip %s for user %s", thread_id, user_id)

        if self.graph.store is not None:
            put_thread(
                self.graph.store,
                user_id,
                ThreadRecord(
                    thread_id=thread_id,
                    request=request,
                    created_at=datetime.now(UTC).isoformat(),
                ),
            )

        return thread_id, self._stream(initial_state(request, user_id), thread_id)

    def resume(self, user_id: str, thread_id: str, answer: Any) -> Iterator[Event]:
        """Answer the question a paused trip is waiting on."""

        if self.snapshot(user_id, thread_id).pending is None:
            raise TripNotPaused(f"Trip {thread_id} is not waiting for input")

        return self._stream(Command(resume=answer), thread_id)

    def retry(self, user_id: str, thread_id: str) -> Iterator[Event]:
        """Continue a trip that stopped on an error from its last checkpoint."""

        if self.snapshot(user_id, thread_id).status != "incomplete":
            raise TripNotPaused(f"Trip {thread_id} has nothing to retry")

        return self._stream(None, thread_id)

    def _stream(self, payload: Any, thread_id: str) -> Iterator[Event]:
        """Translate LangGraph stream chunks into small client events.

        ``updates`` gives each node's state update as it finishes (progress
        lines and interrupts); ``custom`` carries what nodes emit through
        ``get_stream_writer()`` (research agents' tool calls).

        ``subgraphs=True`` is needed for custom events written inside the
        research subgraphs; their internal node updates are ignored.
        """

        for namespace, mode, chunk in self.graph.stream(
            payload,
            self._config(thread_id),
            stream_mode=["updates", "custom"],
            subgraphs=True,
        ):
            if mode == "custom":
                yield chunk
                continue

            if namespace:
                continue

            for node, update in chunk.items():
                if node == "__interrupt__":
                    for pending in update:
                        yield {"event": "interrupt", **pending.value}
                    continue

                for message in (update or {}).get("progress", []):
                    yield {"event": "progress", "node": node, "message": message}

    # --- reading -----------------------------------------------------------

    def snapshot(self, user_id: str, thread_id: str) -> TripSnapshot:
        """Current state of a trip owned by ``user_id``."""

        state = self.graph.get_state(self._config(thread_id))
        values = state.values

        # Unknown and foreign threads look the same, so ids cannot be probed.
        if not values or values.get("user_id") != user_id:
            raise TripNotFound(thread_id)

        pending = state.interrupts[0].value if state.interrupts else None
        requirements = values.get("requirements")
        flights = values.get("flights") or []
        hotels = values.get("hotels") or []
        itinerary = values.get("itinerary")

        return TripSnapshot(
            thread_id=thread_id,
            status=self._status(values, pending, bool(state.next)),
            request=values.get("user_request", ""),
            pending=pending,
            requirements=requirements,
            assumptions=values.get("assumptions") or [],
            flights=flights,
            hotels=hotels,
            weather=values.get("weather"),
            activities=values.get("activities") or [],
            itinerary=itinerary,
            itinerary_errors=values.get("itinerary_errors", []),
            costs=(
                estimate_trip_cost(requirements, flights, hotels, itinerary)
                if requirements is not None and (flights or hotels or itinerary)
                else None
            ),
            progress=values.get("progress", []),
        )

    @staticmethod
    def _status(values: dict, pending: dict | None, has_next: bool) -> TripStatus:
        if pending is not None:
            if pending.get("kind") == InterruptKind.MISSING_REQUIREMENTS:
                return "needs_input"
            return "awaiting_review"

        if has_next:
            return "incomplete"

        if values.get("review_decision") == "approved":
            return "approved"

        if values.get("review_decision") == "rejected":
            return "rejected"

        return "failed"

    def list_trips(self, user_id: str, limit: int = 50) -> list[TripListItem]:
        """Every trip the user started, newest first, with its status."""

        items: list[TripListItem] = []

        for record in list_threads(self.graph.store, user_id, limit):
            try:
                status = self.snapshot(user_id, record.thread_id).status
            except TripNotFound:  # started but no checkpoint written yet
                continue

            items.append(TripListItem(**record.model_dump(), status=status))

        return items

    def ask(
        self,
        user_id: str,
        thread_id: str,
        question: str,
        history: list[dict[str, str]] | None = None,
    ) -> str:
        """Answer a question about one trip from its plan and research."""

        snapshot = self.snapshot(user_id, thread_id)
        return answer_trip_question(snapshot.model_dump(mode="json"), question, history or [])

    # --- long-term memory ---------------------------------------------------

    def memory(self, user_id: str) -> UserMemory:
        store = self.graph.store
        return UserMemory(
            profile=get_profile(store, user_id),
            trips=list_trips(store, user_id),
        )

    def forget(self, user_id: str) -> None:
        delete_user_memory(self.graph.store, user_id)
