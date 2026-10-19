"""Command line entrypoint for the travel planner.

    python main.py "Plan a 5 day trip to Goa from Delhi for 2 people"
    python main.py --thread <id>        # resume a paused or failed trip
    python main.py --user alice --memory

Each trip is a checkpointed thread, so a run can be stopped at a question
(Ctrl+C) and resumed later with ``--thread``.
"""

import argparse
from collections.abc import Iterator
from typing import Any

from app.core.config import get_settings
from app.core.console import prompt, show
from app.core.logging import configure_logging, get_logger
from app.graph import build_travel_graph
from app.graph.constants import InterruptKind
from app.persistence import open_persistence
from app.schemas import Itinerary
from app.services import TripNotFound, TripPlanner, TripSnapshot

logger = get_logger(__name__)

DEFAULT_USER = "local"
DEFAULT_REQUEST = (
    "Plan an 8 day trip to Dubai from Delhi for 2 people. "
    "My budget is ₹40,000. I like food, nature and photography. "
    "My flight is already booked."
)


def show_events(events: Iterator[dict[str, Any]]) -> None:
    """Print progress as the graph streams it."""

    for event in events:
        if event["event"] == "progress":
            show(f"  • {event['message']}")
        elif event["event"] == "tool_call":
            show(f"    ↳ {event['agent']} agent → {event['tool']}({event['args']})")


def show_itinerary(itinerary: Itinerary) -> None:
    show(f"\n{itinerary.destination} — {itinerary.duration_days} days")

    if itinerary.overview:
        show(itinerary.overview)

    for label, value in (
        ("Getting there", itinerary.getting_there),
        ("Flight", itinerary.flight_choice),
        ("Hotel", itinerary.hotel_choice),
    ):
        if value:
            show(f"{label}: {value}")

    for day in itinerary.days:
        show(f"\nDay {day.day}: {day.title}" + (f" ({day.date})" if day.date else ""))

        if day.weather_note:
            show(f"  ~ {day.weather_note}")

        for activity in day.activities:
            show(f"  - {activity}")

    if itinerary.packing_list:
        show(f"\nPack: {', '.join(itinerary.packing_list)}")


def show_research(snapshot: TripSnapshot) -> None:
    """Flights, hotels, weather and the cost estimate behind the plan."""

    for note in snapshot.assumptions:
        show(f"\nNote: {note}")

    if snapshot.flights:
        show("\nFlights:")
        for flight in sorted(snapshot.flights, key=lambda item: item.price)[:3]:
            route = f"{flight.departure_airport or flight.origin} → {flight.arrival_airport or flight.destination}"
            show(f"  - {flight.airline} {route}: {flight.price:,.0f} {flight.currency} per person")

    if snapshot.hotels:
        show("Hotels:")
        for hotel in sorted(snapshot.hotels, key=lambda item: item.price_per_night)[:3]:
            rating = f", rated {hotel.rating}" if hotel.rating else ""
            show(f"  - {hotel.name}: {hotel.price_per_night:,.0f} {hotel.currency}/night{rating}")

    if snapshot.weather:
        show(f"Weather: {snapshot.weather.summary}")

    costs = snapshot.costs

    if costs and costs.lines:
        show("Estimated cost:")
        for line in costs.lines:
            show(f"  - {line.label}: {line.amount:,.0f} {costs.currency} ({line.detail})")

        total = f"  = {costs.total:,.0f} {costs.currency}"
        if costs.budget is not None:
            total += f" of {costs.budget:,.0f} budget" + (" (OVER)" if costs.over_budget else "")
        show(total)


def ask(pending: dict[str, Any], snapshot: TripSnapshot) -> Any:
    """Turn an interrupt into a question for the person at the terminal."""

    if pending["kind"] == InterruptKind.MISSING_REQUIREMENTS:
        show(f"\n{pending['question']}")

        for error in pending["errors"]:
            show(f"  - {error}")

        return prompt("\nYour answer: ")

    show_itinerary(Itinerary.model_validate(pending["itinerary"]))
    show_research(snapshot)
    show(f"\n{pending['question']} ({pending['revisions_left']} revisions left)")

    return prompt("Type 'approve', 'reject', or the changes you want: ")


def report(snapshot: TripSnapshot) -> None:
    show(f"\nTrip {snapshot.thread_id}: {snapshot.status}")

    if snapshot.status == "failed":
        show("Itinerary failed validation:")

        for error in snapshot.itinerary_errors:
            show(f"  - {error}")

    if snapshot.status == "incomplete":
        show(f"The run stopped on an error. Retry with: --thread {snapshot.thread_id}")

    if snapshot.status == "approved" and snapshot.itinerary is not None:
        show_itinerary(snapshot.itinerary)
        show_research(snapshot)


def drive(planner: TripPlanner, user_id: str, thread_id: str) -> TripSnapshot:
    """Answer every pause until the trip reaches a final status."""

    snapshot = planner.snapshot(user_id, thread_id)

    while snapshot.pending is not None:
        show_events(planner.resume(user_id, thread_id, ask(snapshot.pending, snapshot)))
        snapshot = planner.snapshot(user_id, thread_id)

    return snapshot


def show_memory(planner: TripPlanner, user_id: str) -> None:
    memory = planner.memory(user_id)
    show(memory.profile.model_dump_json(indent=2))

    for trip in memory.trips:
        show(f"- {trip.approved_at[:10]} {trip.destination} ({trip.duration_days} days)")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plan a trip with the LangGraph agent.")
    parser.add_argument("request", nargs="?", default=DEFAULT_REQUEST)
    parser.add_argument("--user", default=DEFAULT_USER, help="user id (memory namespace)")
    parser.add_argument("--thread", help="resume this trip instead of starting one")
    parser.add_argument("--memory", action="store_true", help="show the saved profile")
    parser.add_argument("--forget", action="store_true", help="delete the saved profile")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = get_settings()
    configure_logging(settings.log_level)

    with open_persistence(settings) as (checkpointer, store):
        planner = TripPlanner(build_travel_graph(checkpointer, store))

        if args.forget:
            planner.forget(args.user)
            show(f"Forgot everything about user '{args.user}'.")
            return

        if args.memory:
            show_memory(planner, args.user)
            return

        if args.thread:
            thread_id = args.thread

            try:
                snapshot = planner.snapshot(args.user, thread_id)
            except TripNotFound:
                show(f"No trip {thread_id} for user '{args.user}'.")
                return

            events = (
                planner.retry(args.user, thread_id)
                if snapshot.status == "incomplete"
                else iter(())
            )
        else:
            thread_id, events = planner.start(args.user, args.request)
            show(f"Trip {thread_id} (resume later with --thread {thread_id})")

        try:
            show_events(events)
            report(drive(planner, args.user, thread_id))
        except (KeyboardInterrupt, EOFError):
            show(f"\nPaused. Resume with: --thread {thread_id}")
        except Exception as error:  # noqa: BLE001 - checkpoint keeps the progress
            logger.exception("Run stopped on an error")
            show(f"\nRun stopped ({type(error).__name__}). Retry with: --thread {thread_id}")


if __name__ == "__main__":
    main()
