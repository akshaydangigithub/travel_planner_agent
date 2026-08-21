from app.graph.state import TravelState
from app.core.llm import get_llm
from app.schemas.itinerary import Itinerary
from app.prompts.itinerary import build_itinerary_prompt, ITINERARY_SYSTEM_PROMPT


def itinerary_agent(state: TravelState):
    requirements = state["requirements"]

    if requirements is None:
        raise ValueError("Travel requirements are missing")

    structures_llm = get_llm().with_structured_output(Itinerary)

    prompt = build_itinerary_prompt(
        requirements=requirements,
        flights=state["flights"],
        hotels=state["hotels"],
        weather=state["weather"],
        activities=state["activities"],
    )

    itinerary = structures_llm.invoke(
        [("system", ITINERARY_SYSTEM_PROMPT), ("human", prompt)]
    )

    return {"itinerary": itinerary, "messages": ["Itinerary genrated successfully."]}
