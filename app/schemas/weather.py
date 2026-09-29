"""Weather outlook for the destination."""

from pydantic import BaseModel


class WeatherReport(BaseModel):
    destination: str

    start_date: str | None = None
    end_date: str | None = None

    summary: str
    avg_high_c: float
    avg_low_c: float
    rain_chance_percent: int
