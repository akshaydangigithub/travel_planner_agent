"""Turn a planned trip into files: Markdown, JSON and iCalendar (.ics)."""

import json
import re
from datetime import UTC, date, datetime, timedelta

from app.services.planner import TripSnapshot

EXPORT_FORMATS = {
    "markdown": ("text/markdown", "md"),
    "json": ("application/json", "json"),
    "ics": ("text/calendar", "ics"),
}


class NothingToExport(ValueError):
    """The trip has no itinerary yet."""


def _itinerary(snapshot: TripSnapshot):
    if snapshot.itinerary is None:
        raise NothingToExport(f"Trip {snapshot.thread_id} has no itinerary yet")

    return snapshot.itinerary


def file_name(snapshot: TripSnapshot, fmt: str) -> str:
    destination = _itinerary(snapshot).destination
    slug = re.sub(r"[^a-z0-9]+", "-", destination.casefold()).strip("-") or "trip"
    return f"itinerary-{slug}.{EXPORT_FORMATS[fmt][1]}"


def _money(amount: float, currency: str) -> str:
    return f"{amount:,.0f} {currency}"


def to_markdown(snapshot: TripSnapshot) -> str:
    itinerary = _itinerary(snapshot)
    requirements = snapshot.requirements
    lines = [f"# {itinerary.destination}: {itinerary.duration_days} days", ""]

    if requirements:
        facts = [
            f"**From:** {requirements.origin}",
            f"**Travellers:** {requirements.travelers}",
        ]
        if requirements.start_date:
            facts.append(f"**Dates:** {requirements.start_date} → {requirements.end_date}")
        if requirements.budget_amount:
            facts.append(
                f"**Budget:** {_money(requirements.budget_amount, requirements.budget_currency or '')}"
            )
        lines += [" · ".join(facts), ""]

    if itinerary.overview:
        lines += [itinerary.overview, ""]

    for note in snapshot.assumptions:
        lines += [f"> {note}", ""]

    if itinerary.getting_there:
        lines += ["## Getting there", "", itinerary.getting_there, ""]

    choices = [
        (label, value)
        for label, value in (("Flight", itinerary.flight_choice), ("Hotel", itinerary.hotel_choice))
        if value
    ]
    if choices:
        lines += [f"- **{label}:** {value}" for label, value in choices] + [""]

    for day in itinerary.days:
        heading = f"## Day {day.day}: {day.title}"
        if day.date:
            heading += f" ({day.date})"
        lines += [heading, ""]
        if day.weather_note:
            lines += [f"*{day.weather_note}*", ""]
        lines += [f"- {activity}" for activity in day.activities]
        if day.estimated_cost:
            currency = requirements.budget_currency if requirements else ""
            lines.append(f"- Estimated spend: {_money(day.estimated_cost, currency or '')}")
        lines.append("")

    if snapshot.costs and snapshot.costs.lines:
        costs = snapshot.costs
        lines += ["## Estimated cost", "", "| Item | Amount | Detail |", "| --- | ---: | --- |"]
        lines += [
            f"| {line.label} | {_money(line.amount, costs.currency)} | {line.detail} |"
            for line in costs.lines
        ]
        lines.append(f"| **Total** | **{_money(costs.total, costs.currency)}** | |")
        if costs.budget is not None:
            lines.append(f"| Budget | {_money(costs.budget, costs.currency)} | |")
        lines.append("")

    for title, items in (("Packing list", itinerary.packing_list), ("Tips", itinerary.tips)):
        if items:
            lines += [f"## {title}", ""] + [f"- {item}" for item in items] + [""]

    return "\n".join(lines)


def to_json(snapshot: TripSnapshot) -> str:
    _itinerary(snapshot)
    data = snapshot.model_dump(
        mode="json",
        include={
            "thread_id", "request", "requirements", "assumptions", "itinerary",
            "costs", "flights", "hotels", "weather", "activities",
        },
    )
    return json.dumps(data, indent=2, ensure_ascii=False)


# --- iCalendar (RFC 5545) ----------------------------------------------------


def _escape(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )


def _fold(line: str) -> list[str]:
    """Lines longer than 75 octets continue on lines starting with a space."""

    chunks: list[str] = []
    current = ""

    for char in line:
        limit = 75 if not chunks else 74
        if len((current + char).encode()) > limit:
            chunks.append(current)
            current = char
        else:
            current += char

    chunks.append(current)
    return [chunks[0], *(" " + chunk for chunk in chunks[1:])]


def _day_date(snapshot: TripSnapshot, index: int, value: str | None) -> date | None:
    try:
        if value:
            return date.fromisoformat(value)
        start = snapshot.requirements.start_date if snapshot.requirements else None
        return date.fromisoformat(start) + timedelta(days=index) if start else None
    except ValueError:
        return None


def to_ics(snapshot: TripSnapshot) -> str:
    """One all-day event per itinerary day; needs trip dates."""

    itinerary = _itinerary(snapshot)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Travel Planner//Itinerary//EN",
        "CALSCALE:GREGORIAN",
        f"X-WR-CALNAME:{_escape(itinerary.destination)} trip",
    ]

    for index, day in enumerate(itinerary.days):
        when = _day_date(snapshot, index, day.date)

        if when is None:
            raise NothingToExport("The itinerary has no dates to put in a calendar")

        description = "\n".join(
            [*day.activities, *([day.weather_note] if day.weather_note else [])]
        )
        lines += [
            "BEGIN:VEVENT",
            f"UID:{snapshot.thread_id}-day-{day.day}@travel-planner",
            f"DTSTAMP:{stamp}",
            f"DTSTART;VALUE=DATE:{when.strftime('%Y%m%d')}",
            f"DTEND;VALUE=DATE:{(when + timedelta(days=1)).strftime('%Y%m%d')}",
            f"SUMMARY:{_escape(f'Day {day.day}: {day.title}')}",
            f"LOCATION:{_escape(itinerary.destination)}",
            f"DESCRIPTION:{_escape(description)}",
            "END:VEVENT",
        ]

    lines.append("END:VCALENDAR")
    return "\r\n".join(folded for line in lines for folded in _fold(line)) + "\r\n"


def export(snapshot: TripSnapshot, fmt: str) -> str:
    renderers = {"markdown": to_markdown, "json": to_json, "ics": to_ics}
    return renderers[fmt](snapshot)
