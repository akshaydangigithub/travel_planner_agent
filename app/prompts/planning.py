"""Prompts used while turning the raw user request into requirements."""

from datetime import date

REQUIREMENTS_SYSTEM_PROMPT = (
    "You extract structured travel requirements from a user's request. "
    "Only record what the user actually stated. "
    "Use null for any field the user did not state; never guess, and never "
    "write placeholders such as 'Unknown' or 'N/A'. "
    "Do not infer the origin from the budget currency. "
    "Set duration_days from the dates when both dates are given. "
    "Set flights_booked or accommodation_booked to true only when the user "
    "says that part of the trip is already booked. "
    "Today is {today}; resolve relative or partial dates (\"next Friday\", "
    "\"15 Dec\") to the next matching future date as YYYY-MM-DD. "
    "Read amounts like '1 lakh' as 100000 and '2.5k' as 2500."
)


def requirements_system_prompt() -> str:
    return REQUIREMENTS_SYSTEM_PROMPT.replace("{today}", date.today().isoformat())


def build_requirements_prompt(user_request: str, user_feedback: str) -> str:
    """Combine the original request with any correction the user supplied."""

    if not user_feedback:
        return user_request

    return (
        f"Original request:\n"
        f"{user_request}\n\n"
        f"User corrections (newest last; they override the request):\n"
        f"{user_feedback}"
    )
