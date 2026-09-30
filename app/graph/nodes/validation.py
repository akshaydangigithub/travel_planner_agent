"""Check that the extracted requirements are usable before planning."""

from datetime import date

from app.graph.state import TravelState
from app.schemas import TravelRequirements

# Placeholders a model sometimes writes instead of leaving a field null.
_PLACEHOLDERS = {"", "unknown", "n/a", "na", "none", "null", "not specified"}


def _is_missing(value: str | None) -> bool:
    return value is None or value.strip().casefold() in _PLACEHOLDERS


def _parse_date(value: str | None) -> date | None:
    try:
        return date.fromisoformat(value) if value else None
    except ValueError:
        return None


_CURRENCY_CODES = {"₹": "INR", "rs": "INR", "rs.": "INR", "$": "USD", "€": "EUR", "£": "GBP", "¥": "JPY"}


def _normalize(requirements: TravelRequirements) -> TravelRequirements:
    """Canonicalise the currency and fill ``duration_days`` from the dates."""

    code = _CURRENCY_CODES.get(
        requirements.budget_currency.strip().casefold(),
        requirements.budget_currency.strip().upper(),
    )
    requirements = requirements.model_copy(update={"budget_currency": code})

    if requirements.duration_days is not None:
        return requirements

    start = _parse_date(requirements.start_date)
    end = _parse_date(requirements.end_date)

    if start and end and end >= start:
        return requirements.model_copy(
            update={"duration_days": (end - start).days + 1}
        )

    return requirements


def _collect_errors(requirements: TravelRequirements) -> list[str]:
    errors: list[str] = []

    if _is_missing(requirements.origin):
        errors.append("Origin is required (where does the trip start?).")

    if _is_missing(requirements.destination):
        errors.append("Destination is required.")

    if requirements.travelers is None or requirements.travelers <= 0:
        errors.append("Number of travelers must be greater than zero.")

    start = _parse_date(requirements.start_date)
    end = _parse_date(requirements.end_date)

    if start and end and end < start:
        errors.append("End date must not be before the start date.")

    if requirements.duration_days is None:
        errors.append(
            "Trip length is required: give a number of days or both dates."
        )
    elif requirements.duration_days <= 0:
        errors.append("Trip length must be at least one day.")

    if requirements.budget_amount is not None and requirements.budget_amount <= 0:
        errors.append("Budget must be greater than zero.")

    return errors


def validate_requirements(state: TravelState) -> dict:
    """Record any problem that stops the run from continuing."""

    requirements = state["requirements"]

    if requirements is None:
        return {"validation_errors": ["Travel requirements were not extracted."]}

    requirements = _normalize(requirements)

    return {
        "requirements": requirements,
        "validation_errors": _collect_errors(requirements),
    }
