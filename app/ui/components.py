"""Rendering helpers for trips, research results, costs and the profile.

Model output is shown with ``st.markdown`` (HTML disabled) or plain text,
so nothing an LLM writes can inject markup into the page. External links
are only rendered when they are https URLs.
"""

from typing import Any

import streamlit as st

STATUS_LABELS = {
    "needs_input": ("Needs your input", "🟠"),
    "awaiting_review": ("Ready for review", "🔵"),
    "approved": ("Approved", "🟢"),
    "rejected": ("Rejected", "⚪"),
    "failed": ("Failed validation", "🔴"),
    "incomplete": ("Stopped on an error", "🟡"),
}

# Map marker colours.
HOTEL_COLOR = "#e4572e"
PLACE_COLOR = "#2e86ab"


def status_label(status: str) -> str:
    label, icon = STATUS_LABELS.get(status, (status, "•"))
    return f"{icon} {label}"


def short(text: str, limit: int = 48) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def money(amount: float | None, currency: str | None) -> str:
    if amount is None:
        return "—"
    return f"{amount:,.0f} {currency or ''}".strip()


def _safe_url(url: str | None) -> str | None:
    return url if isinstance(url, str) and url.startswith("https://") else None


def _stars(rating: float | None, reviews: int | None = None) -> str:
    if not rating:
        return "No rating"
    text = f"⭐ {rating:.1f}"
    return f"{text} ({reviews:,} reviews)" if reviews else text


def _duration(minutes: int | None) -> str:
    if not minutes:
        return "—"
    hours, mins = divmod(minutes, 60)
    return f"{hours}h {mins:02d}m" if hours else f"{mins}m"


def _same(choice: str | None, name: str) -> bool:
    if not choice:
        return False
    choice, name = choice.casefold().strip(), name.casefold().strip()
    return choice == name or choice in name or name in choice


# --- streaming -----------------------------------------------------------------


def describe_event(event: dict[str, Any]) -> str | None:
    """One readable line for a streamed event, or None to skip it."""

    kind = event.get("event")

    if kind == "progress":
        return f"✓ {event['message']}"

    if kind == "tool_call":
        args = ", ".join(
            f"{key}={value}" for key, value in event.get("args", {}).items()
            if value not in (None, "", [])
        )
        return f"🔎 {event['agent']} agent → `{event['tool']}`({args})"

    if kind == "interrupt":
        return "⏸ Waiting for you."

    return None


# --- summary ---------------------------------------------------------------------


def render_overview(trip: dict[str, Any]) -> None:
    """Headline numbers: route, dates, travellers, budget vs estimate."""

    requirements = trip.get("requirements") or {}
    costs = trip.get("costs") or {}
    currency = requirements.get("budget_currency")

    dates = "—"
    if requirements.get("start_date"):
        dates = f"{requirements['start_date']} → {requirements.get('end_date') or '?'}"

    cols = st.columns(5)
    cols[0].metric("Route", f"{requirements.get('origin') or '—'} → {requirements.get('destination') or '—'}")
    cols[1].metric("Dates", dates, help="Assumed, see the note below" if trip.get("assumptions") else None)
    cols[2].metric("Travellers · days", f"{requirements.get('travelers') or '—'} · {requirements.get('duration_days') or '—'}")
    cols[3].metric("Budget", money(requirements.get("budget_amount"), currency))

    if costs.get("lines"):
        remaining = costs.get("remaining")
        cols[4].metric(
            "Estimated cost",
            money(costs["total"], costs["currency"]),
            delta=(
                f"{money(abs(remaining), costs['currency'])} "
                f"{'over' if remaining < 0 else 'left'}"
                if remaining is not None
                else None
            ),
            delta_color="inverse" if remaining is not None and remaining < 0 else "normal",
        )
    else:
        cols[4].metric("Estimated cost", "—")

    for note in trip.get("assumptions") or []:
        st.info(note, icon="📅")


def render_requirements(requirements: dict[str, Any] | None) -> None:
    if not requirements:
        st.caption("Requirements not extracted yet.")
        return

    details = {
        "Interests": ", ".join(requirements.get("interests") or []) or "—",
        "Preferences": ", ".join(requirements.get("preferences") or []) or "—",
        "Already booked": ", ".join(
            name
            for name, booked in (
                ("flights", requirements.get("flights_booked")),
                ("accommodation", requirements.get("accommodation_booked")),
            )
            if booked
        )
        or "Nothing",
    }

    for label, value in details.items():
        st.markdown(f"**{label}:** {value}")


# --- itinerary -----------------------------------------------------------------


def render_itinerary(itinerary: dict[str, Any], currency: str | None = None) -> None:
    st.subheader(f"{itinerary['destination']} · {itinerary['duration_days']} days")

    if itinerary.get("overview"):
        st.markdown(itinerary["overview"])

    picks = [
        ("✈️ Flight", itinerary.get("flight_choice")),
        ("🏨 Hotel", itinerary.get("hotel_choice")),
    ]
    picks = [(label, value) for label, value in picks if value]

    if picks:
        cols = st.columns(len(picks))
        for col, (label, value) in zip(cols, picks):
            col.markdown(f"**{label}:** {value}")

    if itinerary.get("getting_there"):
        st.markdown(f"**🧭 Getting there:** {itinerary['getting_there']}")

    for day in itinerary["days"]:
        with st.container(border=True):
            heading = f"**Day {day['day']}: {day['title']}**"
            if day.get("date"):
                heading += f" · {day['date']}"

            top = st.columns([3, 1])
            top[0].markdown(heading)
            if day.get("estimated_cost"):
                top[1].markdown(f"💸 ~{money(day['estimated_cost'], currency)}")

            if day.get("weather_note"):
                st.caption(f"🌤 {day['weather_note']}")

            for activity in day["activities"]:
                st.markdown(f"- {activity}")

            if day.get("places"):
                st.caption("📍 " + " · ".join(day["places"]))

    packing, tips = itinerary.get("packing_list") or [], itinerary.get("tips") or []

    if packing or tips:
        cols = st.columns(2)
        with cols[0]:
            if packing:
                st.markdown("**🎒 Packing list**")
                for item in packing:
                    st.markdown(f"- {item}")
        with cols[1]:
            if tips:
                st.markdown("**💡 Local tips**")
                for tip in tips:
                    st.markdown(f"- {tip}")


# --- research ------------------------------------------------------------------


def render_flights(trip: dict[str, Any]) -> None:
    requirements = trip.get("requirements") or {}
    flights = trip.get("flights") or []
    choice = (trip.get("itinerary") or {}).get("flight_choice")

    if requirements.get("flights_booked"):
        st.info("Your flights are already booked, so none were researched.", icon="✈️")
        return

    if not flights:
        st.caption("No flights were found for this route and these dates.")
        return

    travelers = requirements.get("travelers") or 1
    cheapest = min(flight["price"] for flight in flights)

    for index, flight in enumerate(sorted(flights, key=lambda item: item["price"])):
        with st.container(border=True):
            cols = st.columns([3, 2, 2])
            badges = []
            if _same(choice, flight["airline"]):
                badges.append("⭐ Recommended")
            if flight["price"] == cheapest:
                badges.append("💰 Cheapest")

            route = " → ".join(
                filter(None, [flight.get("departure_airport"), flight.get("arrival_airport")])
            ) or f"{flight['origin']} → {flight['destination']}"

            cols[0].markdown(f"**{flight['airline']}** {' · '.join(badges)}")
            cols[0].caption(
                f"{route} · {', '.join(flight.get('flight_numbers') or []) or 'flight'}"
            )
            cols[1].markdown(
                f"🕑 {flight.get('departure') or '—'}  \n🛬 {flight.get('arrival') or '—'}"
            )
            stops = flight.get("stops")
            cols[1].caption(
                f"{_duration(flight.get('duration_minutes'))} · "
                f"{'non-stop' if stops == 0 else f'{stops} stop(s)' if stops else '—'}"
            )
            cols[2].markdown(f"**{money(flight['price'], flight['currency'])}** / person")
            cols[2].caption(
                f"{money(flight['price'] * travelers, flight['currency'])} for {travelers} · "
                f"{'round trip' if flight.get('round_trip') else 'one way'}"
            )

            if url := _safe_url(flight.get("booking_url")):
                cols[2].link_button("View on Google Flights", url, key=f"flight-link-{index}")

    if any(flight.get("arrival_airport") for flight in flights):
        st.caption(
            "The arrival airport can be some distance from the destination; "
            "the itinerary's 'Getting there' covers the transfer."
        )


def render_hotels(trip: dict[str, Any]) -> None:
    requirements = trip.get("requirements") or {}
    hotels = trip.get("hotels") or []
    choice = (trip.get("itinerary") or {}).get("hotel_choice")

    if requirements.get("accommodation_booked"):
        st.info("Your stay is already booked, so no hotels were researched.", icon="🏨")
        return

    if not hotels:
        st.caption("No hotels were found for these dates.")
        return

    duration = requirements.get("duration_days") or 1
    nights = max(duration - 1, 1)
    hotels = sorted(hotels, key=lambda hotel: (not _same(choice, hotel["name"]), hotel["price_per_night"]))

    for row_start in range(0, len(hotels), 3):
        cols = st.columns(3)

        for col, hotel in zip(cols, hotels[row_start : row_start + 3]):
            with col.container(border=True):
                if url := _safe_url(hotel.get("image_url")):
                    st.image(url, width="stretch")

                title = hotel["name"]
                if _same(choice, hotel["name"]):
                    title = f"⭐ {title}"

                st.markdown(f"**{title}**")
                st.caption(
                    " · ".join(
                        filter(None, [hotel.get("hotel_class"), _stars(hotel.get("rating"), hotel.get("reviews"))])
                    )
                )
                st.markdown(
                    f"**{money(hotel['price_per_night'], hotel['currency'])}** / night  \n"
                    f"{money(hotel['price_per_night'] * nights, hotel['currency'])} for {nights} night(s)"
                )

                if hotel.get("amenities"):
                    st.caption(" · ".join(hotel["amenities"][:6]))

                if url := _safe_url(hotel.get("link")):
                    st.link_button("Hotel website", url, width="stretch")


def render_weather(weather: dict[str, Any] | None) -> None:
    if not weather:
        st.caption("No weather data.")
        return

    st.markdown(weather["summary"])

    cols = st.columns(3)
    cols[0].metric("Avg high", f"{weather['avg_high_c']:.0f} °C")
    cols[1].metric("Avg low", f"{weather['avg_low_c']:.0f} °C")
    cols[2].metric("Chance of rain", f"{weather['rain_chance_percent']}%")

    daily = weather.get("daily") or []

    if not daily:
        return

    rows = [
        {
            "date": day["date"],
            "High °C": day.get("high_c"),
            "Low °C": day.get("low_c"),
            "Rain %": day.get("rain_chance_percent") or 0,
        }
        for day in daily
    ]

    st.line_chart(rows, x="date", y=["High °C", "Low °C"], color=["#e4572e", "#2e86ab"], height=260)
    st.bar_chart(rows, x="date", y="Rain %", color="#5c80bc", height=180)

    if weather.get("source") == "historical":
        st.caption(
            "Your dates are beyond the 16-day forecast, so this shows what the "
            "same dates looked like in an earlier year (rain % is 100 on a rainy day)."
        )


def map_points(trip: dict[str, Any]) -> list[dict[str, Any]]:
    points = []

    for hotel in trip.get("hotels") or []:
        if hotel.get("latitude") is not None and hotel.get("longitude") is not None:
            points.append(
                {"lat": hotel["latitude"], "lon": hotel["longitude"], "name": hotel["name"],
                 "kind": "Hotel", "color": HOTEL_COLOR, "size": 60}
            )

    for place in trip.get("activities") or []:
        if place.get("latitude") is not None and place.get("longitude") is not None:
            points.append(
                {"lat": place["latitude"], "lon": place["longitude"], "name": place["name"],
                 "kind": place["category"], "color": PLACE_COLOR, "size": 45}
            )

    return points


def render_places(trip: dict[str, Any]) -> None:
    activities = trip.get("activities") or []
    points = map_points(trip)

    if points:
        st.map(points, latitude="lat", longitude="lon", color="color", size="size", height=380)
        st.caption("🔴 hotels · 🔵 places to visit")

    if not activities:
        st.caption("No places were found.")
        return

    planned = {
        name.casefold()
        for day in ((trip.get("itinerary") or {}).get("days") or [])
        for name in day.get("places") or []
    }

    by_category: dict[str, list[dict]] = {}
    for activity in activities:
        by_category.setdefault(activity["category"], []).append(activity)

    for category, items in by_category.items():
        st.markdown(f"#### {category.title()}")
        cols = st.columns(2)

        for index, item in enumerate(items):
            with cols[index % 2].container(border=True):
                inner = st.columns([1, 3]) if _safe_url(item.get("image_url")) else None

                body = inner[1] if inner else st
                if inner:
                    inner[0].image(item["image_url"], width="stretch")

                in_plan = " · 🗓 in your plan" if item["name"].casefold() in planned else ""
                body.markdown(f"**{item['name']}**{in_plan}")
                body.caption(
                    " · ".join(
                        filter(None, [_stars(item.get("rating"), item.get("reviews")), item.get("address")])
                    )
                )
                body.markdown(item["description"])

                if item.get("price_per_person"):
                    body.caption(f"{money(item['price_per_person'], item.get('currency'))} per person")


def render_costs(trip: dict[str, Any]) -> None:
    costs = trip.get("costs")

    if not costs:
        st.caption("Costs appear once flights, hotels or an itinerary exist.")
        return

    currency = costs["currency"]
    budget = costs.get("budget")

    cols = st.columns(3)
    cols[0].metric("Estimated total", money(costs["total"], currency))
    cols[1].metric("Budget", money(budget, currency))
    if costs.get("remaining") is not None:
        cols[2].metric(
            "Over budget by" if costs["over_budget"] else "Left over",
            money(abs(costs["remaining"]), currency),
        )

    if budget:
        st.progress(
            min(costs["total"] / budget, 1.0),
            text=f"{costs['total'] / budget:.0%} of budget",
        )

    if costs["over_budget"]:
        st.warning(
            "This plan is over budget. Try 'Request changes' with something like "
            "\"choose a cheaper hotel\" or \"cut a day\".",
            icon="⚠️",
        )

    if costs["lines"]:
        st.bar_chart(
            [{"Item": line["label"], "Amount": line["amount"]} for line in costs["lines"]],
            x="Item",
            y="Amount",
            horizontal=True,
            height=200,
        )
        st.dataframe(
            [
                {"Item": line["label"], "Amount": money(line["amount"], currency), "Detail": line["detail"]}
                for line in costs["lines"]
            ],
            hide_index=True,
            width="stretch",
        )

    for note in costs.get("notes") or []:
        st.caption(f"ℹ️ {note}")


# --- misc ----------------------------------------------------------------------


def render_progress(progress: list[str]) -> None:
    if not progress:
        st.caption("No progress yet.")
        return

    for entry in progress:
        st.markdown(f"- {entry}")


def render_profile(profile: dict[str, Any]) -> None:
    cols = st.columns(3)
    cols[0].metric("Home city", profile.get("home_origin") or "—")
    cols[1].metric("Currency", profile.get("currency") or "—")
    cols[2].metric("Trips approved", profile.get("trips_planned", 0))

    st.markdown(f"**Interests:** {', '.join(profile.get('interests') or []) or '—'}")
    st.markdown(f"**Preferences:** {', '.join(profile.get('preferences') or []) or '—'}")
