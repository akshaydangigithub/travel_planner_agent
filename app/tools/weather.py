"""Weather forecast tool exposed to the weather research agent."""

from langchain_core.tools import tool


@tool
def get_weather_forecast(
    destination: str,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict:
    """
    Get the expected weather at the destination.

    Returns a summary of the conditions expected
    during the requested travel dates.
    """

    return {
        "destination": destination,
        "start_date": start_date,
        "end_date": end_date,
        "summary": "Mostly sunny with mild temperatures",
        "avg_high_c": 24,
        "avg_low_c": 15,
        "rain_chance_percent": 20,
    }


WEATHER_TOOLS = [get_weather_forecast]
