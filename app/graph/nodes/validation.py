"""Check that the extracted requirements are usable before planning."""

from datetime import date, timedelta

from app.core.config import get_settings
from app.graph.state import TravelState
from app.schemas import TravelRequirements, UserProfile

# Placeholders a model sometimes writes instead of leaving a field null.
_PLACEHOLDERS = {"", "unknown", "n/a", "na", "none", "null", "not specified"}


def _is_missing(value: str | None) -> bool:
    return value is None or value.strip().casefold() in _PLACEHOLDERS


def _parse_date(value: str | None) -> date | None:
    try:
        return date.fromisoformat(value) if value else None
    except ValueError:
        return None


_CURRENCY_CODES = {
    "₹": "INR", "rs": "INR", "rs.": "INR", "rupee": "INR", "rupees": "INR",
    "lakh": "INR", "lakhs": "INR",
    "$": "USD", "us$": "USD", "dollar": "USD", "dollars": "USD",
    "€": "EUR", "euro": "EUR", "euros": "EUR",
    "£": "GBP", "pound": "GBP", "pounds": "GBP",
    "¥": "JPY", "yen": "JPY",
    "dirham": "AED", "dirhams": "AED",
    "baht": "THB",
}


def currency_code(value: str | None) -> str:
    """ISO 4217 code for a code, symbol or name; the default otherwise."""

    default = get_settings().default_currency
    text = (value or "").strip()
    code = _CURRENCY_CODES.get(text.casefold(), text.upper())

    return code if len(code) == 3 and code.isalpha() else default


def _apply_profile(
    requirements: TravelRequirements, profile: UserProfile
) -> tuple[TravelRequirements, list[str]]:
    """Fill fields the user did not state from their saved profile.

    Only gaps are filled; anything stated in this request wins. Each default
    is reported so the user can correct it at the review step.
    """

    updates: dict = {}
    notes: list[str] = []

    if _is_missing(requirements.origin) and profile.home_origin:
        updates["origin"] = profile.home_origin
        notes.append(f"Using saved home city as origin: {profile.home_origin}.")

    if not requirements.interests and profile.interests:
        updates["interests"] = profile.interests
        notes.append(f"Using saved interests: {', '.join(profile.interests)}.")

    if not requirements.budget_currency:
        updates["budget_currency"] = profile.currency or get_settings().default_currency

    return requirements.model_copy(update=updates), notes


def _normalize(requirements: TravelRequirements) -> TravelRequirements:
    """Canonicalise the currency and fill ``duration_days`` from the dates."""

    requirements = requirements.model_copy(
        update={"budget_currency": currency_code(requirements.budget_currency)}
    )

    if requirements.duration_days is not None:
        return requirements

    start = _parse_date(requirements.start_date)
    end = _parse_date(requirements.end_date)

    if start and end and end >= start:
        return requirements.model_copy(
            update={"duration_days": (end - start).days + 1}
        )

    return requirements


def _fill_dates(
    requirements: TravelRequirements, today: date
) -> tuple[TravelRequirements, list[str]]:
    """Complete the trip dates from whatever was given.

    Live flight and hotel prices need dates. When the user gave none, the
    trip is assumed to start ``default_trip_lead_days`` from today; the
    assumption is reported so it can be corrected at review.
    """

    length = requirements.duration_days

    if not length or length <= 0:
        return requirements, []

    start = _parse_date(requirements.start_date)
    end = _parse_date(requirements.end_date)
    span = timedelta(days=length - 1)

    if start and end:
        return requirements, []

    if start:
        end = start + span
        note = None
    elif end:
        start = end - span
        note = None
    else:
        start = today + timedelta(days=get_settings().default_trip_lead_days)
        end = start + span
        note = (
            f"No travel dates given; assuming {start.isoformat()} to "
            f"{end.isoformat()} to price flights and hotels. Tell the planner "
            "your dates to change this."
        )

    filled = requirements.model_copy(
        update={"start_date": start.isoformat(), "end_date": end.isoformat()}
    )
    return filled, [note] if note else []


def _collect_errors(requirements: TravelRequirements, today: date) -> list[str]:
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

    if start and start < today:
        errors.append(f"Start date {start.isoformat()} is in the past.")

    if requirements.duration_days is None:
        errors.append(
            "Trip length is required: give a number of days or both dates."
        )
    elif requirements.duration_days <= 0:
        errors.append("Trip length must be at least one day.")

    if requirements.budget_amount is not None and requirements.budget_amount <= 0:
        errors.append("Budget must be greater than zero.")

    return errors


def prepare_requirements(
    requirements: TravelRequirements, profile: UserProfile
) -> tuple[TravelRequirements, list[str], list[str]]:
    """Fill defaults and check the result.

    Returns the completed requirements, notes about the defaults used
    (profile values, assumed dates) and the errors that block planning.
    """

    today = date.today()
    requirements, notes = _apply_profile(requirements, profile)
    requirements = _normalize(requirements)
    errors = _collect_errors(requirements, today)

    if not errors:
        requirements, date_notes = _fill_dates(requirements, today)
        notes += date_notes

    return requirements, notes, errors


def validate_requirements(state: TravelState) -> dict:
    """Record any problem that stops the run from continuing."""

    requirements = state["requirements"]

    if requirements is None:
        return {"validation_errors": ["Travel requirements were not extracted."]}

    profile = UserProfile.model_validate(state["user_profile"])
    requirements, notes, errors = prepare_requirements(requirements, profile)

    return {
        "requirements": requirements,
        "validation_errors": errors,
        "assumptions": notes,
        "progress": notes,
    }
