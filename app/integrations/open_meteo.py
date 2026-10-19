"""Live weather through Open-Meteo (free, no API key).

Places are geocoded with OpenStreetMap Nominatim, which knows regions and
states ("Goa", "Bali"); Open-Meteo's own geocoder is the fallback.

Trips inside the 16-day forecast window use the forecast. Trips further out
use last year's observations for the same dates as a climate estimate.
"""

from datetime import date, timedelta

from app.integrations.http import IntegrationError, get_json

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
# Nominatim's usage policy requires an identifying User-Agent.
NOMINATIM_HEADERS = {"User-Agent": "travel-planner-agent/0.2"}
GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

FORECAST_HORIZON_DAYS = 15
DEFAULT_WINDOW_DAYS = 7
RAINY_DAY_MM = 1.0


def _coordinates(destination: str) -> tuple[float, float, str]:
    try:
        places = get_json(
            NOMINATIM_URL,
            {"q": destination, "format": "jsonv2", "limit": 1, "accept-language": "en"},
            headers=NOMINATIM_HEADERS,
        )
    except IntegrationError:
        places = []

    if places:
        place = places[0]
        return float(place["lat"]), float(place["lon"]), place.get("name") or destination

    return _open_meteo_coordinates(destination)


def _open_meteo_coordinates(destination: str) -> tuple[float, float, str]:
    # The geocoder matches place names, so "Tokyo, Japan" → "Tokyo" with
    # "Japan" as a hint for choosing between candidates.
    name, *hints = [part.strip() for part in destination.split(",")]
    body = get_json(GEOCODING_URL, {"name": name, "count": 10, "language": "en"})
    results = body.get("results") or []

    if not results:
        raise IntegrationError(f"Unknown location '{destination}'")

    def score(place: dict) -> tuple:
        country = place.get("country", "").casefold()
        return (
            place.get("name", "").casefold() == name.casefold(),
            any(hint.casefold() in country for hint in hints),
            place.get("population") or 0,
        )

    place = max(results, key=score)
    return place["latitude"], place["longitude"], place.get("name", name)


def _parse(value: str | None) -> date | None:
    try:
        return date.fromisoformat(value) if value else None
    except ValueError:
        return None


def _years_earlier(day: date, years: int) -> date:
    try:
        return day.replace(year=day.year - years)
    except ValueError:  # 29 February
        return day.replace(year=day.year - years, day=28)


def _mean(values: list[float | None]) -> float:
    numbers = [value for value in values if value is not None]
    return round(sum(numbers) / len(numbers), 1) if numbers else 0.0


def get_weather(
    destination: str, start_date: str | None, end_date: str | None
) -> dict:
    """Return a ``WeatherReport`` shaped dict for the trip dates."""

    latitude, longitude, place = _coordinates(destination)
    today = date.today()

    start = _parse(start_date) or today
    end = _parse(end_date) or start + timedelta(days=DEFAULT_WINDOW_DAYS - 1)
    location = {"latitude": latitude, "longitude": longitude, "timezone": "auto"}

    if start >= today and end <= today + timedelta(days=FORECAST_HORIZON_DAYS):
        daily = get_json(
            FORECAST_URL,
            {
                **location,
                "daily": "temperature_2m_max,temperature_2m_min,"
                "precipitation_probability_max",
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
            },
        )["daily"]
        rain_chance = round(_mean(daily["precipitation_probability_max"]))
        source = "forecast"
        label = "Forecast"
        days = [
            {
                "date": day,
                "high_c": high,
                "low_c": low,
                "rain_chance_percent": chance,
            }
            for day, high, low, chance in zip(
                daily["time"],
                daily["temperature_2m_max"],
                daily["temperature_2m_min"],
                daily["precipitation_probability_max"],
            )
        ]
    else:
        # Same calendar dates one year earlier (archive data lags a few days).
        years = 1

        while _years_earlier(start, years) + (end - start) >= today - timedelta(days=5):
            years += 1

        previous_start = _years_earlier(start, years)
        previous_end = previous_start + (end - start)

        daily = get_json(
            ARCHIVE_URL,
            {
                **location,
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
                "start_date": previous_start.isoformat(),
                "end_date": previous_end.isoformat(),
            },
        )["daily"]
        precipitation = [value or 0 for value in daily["precipitation_sum"]]
        rainy_days = sum(1 for value in precipitation if value >= RAINY_DAY_MM)
        rain_chance = round(100 * rainy_days / max(len(precipitation), 1))
        source = "historical"
        label = f"Typical conditions (observed {previous_start.year})"
        # Shown against the trip's own dates.
        days = [
            {
                "date": (start + timedelta(days=offset)).isoformat(),
                "high_c": high,
                "low_c": low,
                "rain_chance_percent": 100 if rain >= RAINY_DAY_MM else 0,
                "precipitation_mm": rain,
            }
            for offset, (high, low, rain) in enumerate(
                zip(daily["temperature_2m_max"], daily["temperature_2m_min"], precipitation)
            )
        ]

    high = _mean(daily["temperature_2m_max"])
    low = _mean(daily["temperature_2m_min"])

    return {
        "destination": destination,
        "start_date": start_date,
        "end_date": end_date,
        "summary": (
            f"{label} for {place}: highs around {high}°C, lows around {low}°C, "
            f"{rain_chance}% chance of rain."
        ),
        "avg_high_c": high,
        "avg_low_c": low,
        "rain_chance_percent": rain_chance,
        "source": source,
        "daily": days,
    }
