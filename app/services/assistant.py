"""Question answering over one trip (the "Ask about this trip" chat)."""

from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.core.llm import get_llm
from app.prompts.assistant import ASSISTANT_SYSTEM_PROMPT, build_trip_context

# Earlier turns kept for follow-up questions.
MAX_HISTORY_TURNS = 6


def answer_trip_question(
    snapshot: dict[str, Any], question: str, history: list[dict[str, str]]
) -> str:
    messages: list = [
        SystemMessage(content=ASSISTANT_SYSTEM_PROMPT),
        HumanMessage(content=f"Trip data:\n{build_trip_context(snapshot)}"),
        AIMessage(content="Thanks, I have the trip details. What would you like to know?"),
    ]

    for turn in history[-MAX_HISTORY_TURNS * 2 :]:
        content = str(turn.get("content", ""))[:4000]
        if turn.get("role") == "assistant":
            messages.append(AIMessage(content=content))
        else:
            messages.append(HumanMessage(content=content))

    messages.append(HumanMessage(content=question))
    response = get_llm().invoke(messages)

    return str(response.text).strip()
