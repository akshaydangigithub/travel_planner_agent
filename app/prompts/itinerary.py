ITINERARY_SYSTEM_PROMPT = """
You are a professional travel itinerary planner.

Create a practical day-by-day travel itinerary using only the
provided travel requirements and researched information.

Rules:
- Respect the requested destination and duration.
- Do not invent travel dates when dates were not provided.
- Use researched activities when creating the itinerary.
- Consider the user's interests and preferences.
- Keep each day realistic and logically organized.
- Return exactly the requested number of days.
"""


def build_itinerary_prompt(
    requirements,
    flights,
    hotels,
    weather,
    activities,
):
    return f"""
Create a {requirements.duration_days}-day itinerary for {requirements.destination}.

Travel requirements:
{requirements.model_dump_json(indent=2)}

Flight research:
{flights}

Hotel research:
{hotels}

Weather research:
{weather}

Activity research:
{activities}

Create a complete day-by-day itinerary.
"""
