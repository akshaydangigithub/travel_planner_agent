"""Weather outlook for the destination."""

from pydantic import BaseModel


class WeatherDay(BaseModel):
    date: str
    high_c: float | None = None
    low_c: float | None = None
    rain_chance_percent: int | None = None
    """Forecast probability, or for historical data 100 on a rainy day."""
    precipitation_mm: float | None = None


class WeatherReport(BaseModel):
    destination: str

    start_date: str | None = None
    end_date: str | None = None

    summary: str
    avg_high_c: float
    avg_low_c: float
    rain_chance_percent: int

    source: str | None = None
    """"forecast", or "historical" (the same dates in an earlier year)."""
    daily: list[WeatherDay] = []
