"""Deterministic checks on the generated itinerary."""

from app.core.logging import get_logger
from app.graph.state import TravelState

logger = get_logger(__name__)


def validate_itinerary(state: TravelState) -> dict:
    """Record every rule the itinerary breaks; an empty list means valid."""

    logger.info("Validating itinerary...")

    itinerary = state["itinerary"]
    requirements = state["requirements"]

    errors: list[str] = []

    if itinerary is None:
        errors.append("Itinerary was not generated.")
        return {"itinerary_errors": errors}

    if requirements is None:
        errors.append("Travel requirements are missing.")
        return {"itinerary_errors": errors}

    # 1. Destination ("Tokyo, Japan" is fine for a trip to "Japan")
    if requirements.destination.casefold() not in itinerary.destination.casefold():
        errors.append(
            f"Itinerary destination '{itinerary.destination}' "
            f"does not match requested destination "
            f"'{requirements.destination}'."
        )

    # 2. Duration
    if requirements.duration_days is not None:
        if itinerary.duration_days != requirements.duration_days:
            errors.append(
                f"Itinerary duration is {itinerary.duration_days} days, "
                f"but {requirements.duration_days} days were requested."
            )

        # 3. Number of itinerary days
        if len(itinerary.days) != requirements.duration_days:
            errors.append(
                f"Itinerary contains {len(itinerary.days)} days, "
                f"but {requirements.duration_days} days were expected."
            )

    # 4. Day numbers
    expected_days = list(range(1, len(itinerary.days) + 1))
    actual_days = [day.day for day in itinerary.days]

    if actual_days != expected_days:
        errors.append(
            f"Itinerary day numbers are invalid: {actual_days}. "
            f"Expected: {expected_days}."
        )

    # 5. Every day must contain activities
    for day in itinerary.days:
        if not day.activities:
            errors.append(f"Day {day.day} has no activities.")

    logger.info(
        "Itinerary validation completed: %s",
        "VALID" if not errors else f"INVALID - {errors}",
    )

    return {"itinerary_errors": errors}
