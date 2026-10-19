"""Prompts used by the trip assistant that answers questions about a trip."""

import json
from typing import Any

ASSISTANT_SYSTEM_PROMPT = """
You are a friendly travel assistant answering questions about one trip the
traveller is planning. The trip's requirements, research results and
itinerary are given as JSON.

Rules:
- Answer from the trip data first. When you add general travel knowledge
  (visas, customs, local food, transport), say so and keep it practical.
- Quote prices only from the trip data, with their currency.
- If the question asks to change the plan, explain how and tell the
  traveller to use "Request changes" so the planner can update it.
- Be concise: a short paragraph or a few bullet points in Markdown.
"""

# Research lists are trimmed so the context stays small.
_MAX_ITEMS = 8
_KEEP = (
    "status", "request", "requirements", "assumptions", "flights", "hotels",
    "weather", "activities", "itinerary", "costs",
)


def build_trip_context(snapshot: dict[str, Any]) -> str:
    trip = {key: snapshot.get(key) for key in _KEEP}

    for key in ("flights", "hotels", "activities"):
        trip[key] = (trip.get(key) or [])[:_MAX_ITEMS]

    if not trip.get("itinerary") and snapshot.get("pending"):
        trip["itinerary"] = snapshot["pending"].get("itinerary")

    return json.dumps(trip, ensure_ascii=False, default=str)
