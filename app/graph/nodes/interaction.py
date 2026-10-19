"""Nodes that pause the run for the human and act on their answer.

``interrupt()`` saves the run in the checkpointer and returns control to the
caller (CLI or API). The caller resumes with ``Command(resume=answer)``; the
node then runs again from the top and ``interrupt()`` returns that answer.
Because the node re-runs, everything before ``interrupt()`` must be free of
side effects.
"""

from typing import Any, Literal

from langgraph.graph import END
from langgraph.types import Command, interrupt

from app.core.logging import get_logger
from app.graph.constants import InterruptKind, Node, ReviewAction
from app.graph.state import TravelState

logger = get_logger(__name__)

MAX_REVISIONS = 3

_APPROVE_WORDS = {"approve", "approved", "yes", "y", "ok", "looks good"}
_REJECT_WORDS = {"reject", "rejected", "no", "n", "cancel"}


def ask_user(state: TravelState) -> dict:
    """Pause until the user supplies the missing or invalid information."""

    answer = interrupt(
        {
            "kind": InterruptKind.MISSING_REQUIREMENTS,
            "question": "Some trip details are missing or invalid. "
            "Please provide the corrected information.",
            "errors": state["validation_errors"],
        }
    )

    if isinstance(answer, dict):
        answer = answer.get("answer", "")

    corrections = [state["user_feedback"], str(answer).strip()]

    return {
        "user_feedback": "\n".join(filter(None, corrections)),
        "progress": ["User supplied missing trip details."],
    }


def continue_plan(state: TravelState) -> dict:
    """Fan out into the research branches once requirements are valid."""

    logger.info("Requirements are valid. Continuing with travel planning...")

    return {"progress": ["Requirements validated."]}


def _parse_review(answer: Any) -> tuple[str, str]:
    """Accept ``{"action", "feedback"}`` or free text ("yes", "add a beach day")."""

    if isinstance(answer, dict):
        action = str(answer.get("action", "")).strip().casefold()
        feedback = str(answer.get("feedback") or "").strip()

        if action in {ReviewAction.APPROVE, ReviewAction.REVISE, ReviewAction.REJECT}:
            return action, feedback

        answer = feedback

    text = str(answer).strip()

    if text.casefold() in _APPROVE_WORDS:
        return ReviewAction.APPROVE, ""

    if text.casefold() in _REJECT_WORDS:
        return ReviewAction.REJECT, ""

    return ReviewAction.REVISE, text


def review_itinerary(
    state: TravelState,
) -> Command[Literal["save_profile", "apply_revision", "review_itinerary", "__end__"]]:
    """Ask the user to approve, revise or reject the validated itinerary."""

    itinerary = state["itinerary"]

    if itinerary is None:
        raise ValueError("There is no itinerary to review")

    revisions_left = MAX_REVISIONS - state["revision_count"]

    answer = interrupt(
        {
            "kind": InterruptKind.ITINERARY_REVIEW,
            "question": "Approve this itinerary, describe the changes you want, "
            "or reject it.",
            "itinerary": itinerary.model_dump(),
            "revisions_left": revisions_left,
        }
    )

    action, feedback = _parse_review(answer)

    if action == ReviewAction.APPROVE:
        return Command(
            update={"review_decision": "approved", "progress": ["Itinerary approved."]},
            goto=Node.SAVE_PROFILE,
        )

    if action == ReviewAction.REJECT:
        return Command(
            update={"review_decision": "rejected", "progress": ["Itinerary rejected."]},
            goto=END,
        )

    if not feedback:
        note = "No changes were described; asking again."
    elif revisions_left <= 0:
        note = f"Revision limit ({MAX_REVISIONS}) reached; please approve or reject."
    else:
        note = None

    if note:
        logger.info(note)
        return Command(update={"progress": [note]}, goto=Node.REVIEW_ITINERARY)

    count = state["revision_count"] + 1
    logger.info("Revising itinerary (revision %s): %s", count, feedback)

    return Command(
        update={
            "itinerary_feedback": feedback,
            "revision_count": count,
            # A revision gets a fresh validation retry budget.
            "replan_count": 0,
            "progress": [f"Revising itinerary (revision {count}): {feedback}"],
        },
        goto=Node.APPLY_REVISION,
    )
