"""Weather forecast tool exposed to the weather research agent."""

from datetime import date, timedelta

from langchain_core.tools import tool

from app.core.config import get_settings
from app.integrations import open_meteo


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

    if get_settings().travel_data_provider == "live":
        return open_meteo.get_weather(destination, start_date, end_date)

    return {
        "destination": destination,
        "start_date": start_date,
        "end_date": end_date,
        "summary": "Mostly sunny with mild temperatures",
        "avg_high_c": 24,
        "avg_low_c": 15,
        "rain_chance_percent": 20,
        "source": "demo",
        "daily": _demo_days(start_date, end_date),
    }


def _demo_days(start_date: str | None, end_date: str | None) -> list[dict]:
    try:
        start = date.fromisoformat(start_date or "")
        end = date.fromisoformat(end_date or "")
    except ValueError:
        return []

    return [
        {
            "date": (start + timedelta(days=offset)).isoformat(),
            "high_c": 23 + offset % 3,
            "low_c": 14 + offset % 2,
            "rain_chance_percent": (10, 20, 40)[offset % 3],
        }
        for offset in range(min((end - start).days + 1, 16))
    ]


WEATHER_TOOLS = [get_weather_forecast]
