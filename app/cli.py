"""Command line entrypoint for the travel planner."""

from app.core.config import get_settings
from app.core.console import show
from app.core.logging import configure_logging
from app.graph import initial_state, travel_graph

DEFAULT_REQUEST = (
    "Plan a trip to Japan"
    "for 2 people. My budget is ₹2 lakh. "
    "I like food, nature and photography."
)


def run(user_request: str = DEFAULT_REQUEST) -> dict:
    """Run one planning session and return the final state."""

    return travel_graph.invoke(initial_state(user_request))


def report(result: dict) -> None:
    """Print the run log followed by the itinerary or why it failed."""

    show("Progress:")

    for entry in result["progress"]:
        show(f"- {entry}")

    if result["itinerary_errors"]:
        show("\nItinerary failed validation:")

        for error in result["itinerary_errors"]:
            show(f"- {error}")

    itinerary = result["itinerary"]

    if itinerary is not None:
        show(f"\n{itinerary.model_dump_json(indent=2)}")


def main() -> None:
    configure_logging(get_settings().log_level)

    report(run())


if __name__ == "__main__":
    main()
