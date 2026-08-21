"""Prompts used while turning the raw user request into requirements."""


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
