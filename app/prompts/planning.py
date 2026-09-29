"""Prompts used while turning the raw user request into requirements."""

REQUIREMENTS_SYSTEM_PROMPT = (
    "You extract structured travel requirements from a user's request. "
    "Only record what the user actually stated. "
    "Use null for any field the user did not state; never guess, and never "
    "write placeholders such as 'Unknown' or 'N/A'. "
    "Do not infer the origin from the budget currency. "
    "Set duration_days from the dates when both dates are given."
)


def build_requirements_prompt(user_request: str, user_feedback: str) -> str:
    """Combine the original request with any correction the user supplied."""

    if not user_feedback:
        return user_request

    return (
        f"Original request:\n"
        f"{user_request}\n\n"
        f"User correction:\n"
        f"{user_feedback}"
    )
