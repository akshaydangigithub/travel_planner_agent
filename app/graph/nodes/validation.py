"""Check that the extracted requirements are usable before planning."""

from app.graph.state import TravelState
from app.schemas import TravelRequirements


def _collect_errors(requirements: TravelRequirements) -> list[str]:
    errors: list[str] = []

    if not requirements.origin:
        errors.append("Origin is required.")

    if not requirements.destination:
        errors.append("Destination is required.")

    if requirements.travelers <= 0:
        errors.append("Number of travelers must be greater than zero.")

    if requirements.budget_amount is not None and requirements.budget_amount <= 0:
        errors.append("Budget must be greater than zero.")

    return errors


def validate_requirements(state: TravelState) -> TravelState:
    """Record any problem that stops the run from continuing."""

    requirements = state["requirements"]

    if requirements is None:
        return {
            **state,
            "validation_errors": ["Travel requirements were not extracted."],
        }

    return {
        **state,
        "validation_errors": _collect_errors(requirements),
    }
