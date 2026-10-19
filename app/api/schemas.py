"""Request bodies accepted by the HTTP API."""

from typing import Literal

from pydantic import BaseModel, Field


class TripRequest(BaseModel):
    request: str = Field(
        min_length=3,
        max_length=4000,
        examples=["Plan a 7 day trip to Japan from Delhi for 2 people, budget ₹2 lakh."],
    )


class ResumeRequest(BaseModel):
    """Answer to a paused trip.

    - ``needs_input``: send ``answer`` with the missing details.
    - ``awaiting_review``: send ``action`` (approve / revise / reject) and,
      for revise, ``feedback`` describing the changes.
    """

    answer: str | None = Field(default=None, max_length=4000)
    action: Literal["approve", "revise", "reject"] | None = None
    feedback: str | None = Field(default=None, max_length=4000)

    def to_resume_value(self) -> str | dict:
        if self.action:
            return {"action": self.action, "feedback": self.feedback or ""}

        return self.answer or ""


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=8000)


class AskRequest(BaseModel):
    """A question about one trip; ``history`` holds earlier turns."""

    question: str = Field(min_length=2, max_length=2000)
    history: list[ChatTurn] = Field(default=[], max_length=20)


class AskResponse(BaseModel):
    answer: str
