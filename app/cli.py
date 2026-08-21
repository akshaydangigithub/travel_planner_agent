"""Command line entrypoint for the travel planner."""

from app.core.config import get_settings
from app.core.console import show
from app.core.logging import configure_logging
from app.graph import initial_state, travel_graph

DEFAULT_REQUEST = (
    "Plan a 7 day trip to Japan from Delhi "
    "for 2 people. My budget is ₹2 lakh. "
    "I like food, nature and photography."
)


def run(user_request: str = DEFAULT_REQUEST) -> dict:
    """Run one planning session and return the final state."""

    return travel_graph.invoke(initial_state(user_request))


def report(result: dict) -> None:
    """Print the messages collected during the run and the final state."""

    show(str(result))


def main() -> None:
    configure_logging(get_settings().log_level)

    report(run())


if __name__ == "__main__":
    main()
