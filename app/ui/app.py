"""Streamlit front end for the travel planner.

A thin client of the HTTP API: it signs in with an API key, streams runs
over SSE, answers pauses (missing details, itinerary review), lists and
reopens trips, retries failed runs and manages the traveller's memory.

    streamlit run streamlit_app.py
"""

from collections.abc import Iterator
from typing import Any

import httpx
import streamlit as st

from app.ui.client import ApiError, ApiUnavailable, AuthError, TravelApiClient
from app.ui.components import (
    describe_event,
    render_costs,
    render_flights,
    render_hotels,
    render_itinerary,
    render_overview,
    render_places,
    render_profile,
    render_progress,
    render_requirements,
    render_weather,
    short,
    status_label,
)
from app.ui.config import get_ui_settings

EXAMPLES = [
    "Plan a 7 day trip to Japan from Delhi for 2 people. My budget is ₹2 lakh. "
    "I like food, nature and photography.",
    "5 days in Goa from Mumbai for 3 friends, budget ₹60,000, beaches and nightlife.",
    "Weekend in Jaipur from Delhi for 2, hotel already booked. We love history.",
]

ss = st.session_state


# --- session ---------------------------------------------------------------


@st.cache_resource
def _http_pool(base_url: str) -> httpx.Client:
    """One connection pool per server process, shared by every visitor."""

    return httpx.Client(
        base_url=base_url,
        limits=httpx.Limits(max_connections=50, max_keepalive_connections=10),
    )


def _client(api_key: str) -> TravelApiClient:
    settings = get_ui_settings()
    return TravelApiClient(
        _http_pool(settings.api_url),
        api_key,
        settings.request_timeout_seconds,
        settings.stream_timeout_seconds,
    )


def _flash(message: str, icon: str = "✅") -> None:
    """Show a toast after the next rerun."""

    ss["flash"] = (message, icon)


def _show_flash() -> None:
    if "flash" in ss:
        message, icon = ss.pop("flash")
        st.toast(message, icon=icon)


def _sign_out(message: str | None = None) -> None:
    for key in ("api_key", "user_id", "thread_id"):
        ss.pop(key, None)

    if message:
        _flash(message, "🔒")


def _open_trip(thread_id: str | None) -> None:
    ss["thread_id"] = thread_id


def _sign_in() -> TravelApiClient | None:
    """Return a signed-in client, or render the sign-in form and return None."""

    settings = get_ui_settings()

    if "user_id" in ss:
        return _client(ss["api_key"])

    if settings.api_key:  # single-user deployment: key comes from the env
        client = _client(settings.api_key)
        ss["user_id"] = client.whoami()
        ss["api_key"] = settings.api_key
        return client

    st.title("✈️ Travel Planner")
    st.write("Sign in with the API key you were given.")

    if not _client("").health():
        st.warning(f"The planner API at {settings.api_url} is not reachable right now.")

    with st.form("sign-in"):
        api_key = st.text_input("API key", type="password")
        submitted = st.form_submit_button("Sign in", type="primary")

    if submitted and api_key.strip():
        try:
            ss["user_id"] = _client(api_key.strip()).whoami()
        except AuthError:
            st.error("That API key was not accepted.")
            return None

        ss["api_key"] = api_key.strip()
        st.rerun()

    return None


# --- running ---------------------------------------------------------------


def _run(events: Iterator[dict[str, Any]], label: str) -> dict | None:
    """Show a streamed run live; return the final snapshot."""

    snapshot = None
    error = None

    with st.status(label, expanded=True) as box:
        try:
            for event in events:
                kind = event["event"]

                if kind == "started":
                    _open_trip(event["thread_id"])
                elif kind == "done":
                    snapshot = event
                elif kind == "error":
                    error = f"the planner stopped ({event.get('message', 'error')})"
                elif line := describe_event(event):
                    st.markdown(line)
        except ApiUnavailable as unavailable:
            error = str(unavailable)

        if error:
            box.update(label=f"Stopped: {error}", state="error")
        elif snapshot:
            box.update(label=status_label(snapshot["status"]), state="complete")

    if snapshot:
        _open_trip(snapshot["thread_id"])

    return snapshot


# --- views -----------------------------------------------------------------


def _sidebar(client: TravelApiClient) -> None:
    with st.sidebar:
        st.title("✈️ Travel Planner")
        healthy = client.health()
        st.caption(f"Signed in as **{ss['user_id']}** · API {'🟢' if healthy else '🔴'}")

        st.button(
            "➕ New trip",
            width="stretch",
            type="primary" if not ss.get("thread_id") else "secondary",
            on_click=_open_trip,
            args=(None,),
        )

        st.subheader("Your trips")
        trips = client.list_trips() if healthy else []

        if not trips:
            st.caption("No trips yet.")

        for trip in trips:
            icon = status_label(trip["status"]).split(" ", 1)[0]
            st.button(
                f"{icon} {short(trip['request'], 34)}",
                key=f"trip-{trip['thread_id']}",
                help=f"{trip['created_at'][:16].replace('T', ' ')} UTC · "
                f"{status_label(trip['status'])}",
                width="stretch",
                type="primary" if trip["thread_id"] == ss.get("thread_id") else "tertiary",
                on_click=_open_trip,
                args=(trip["thread_id"],),
            )

        with st.expander("Open a trip by id"):
            thread_id = st.text_input("Trip id", key="open-trip-id")

            if st.button("Open", disabled=not thread_id.strip()):
                _open_trip(thread_id.strip())
                st.rerun()

        if not get_ui_settings().api_key:
            st.divider()
            if st.button("Sign out", width="stretch"):
                _sign_out("Signed out.")
                st.rerun()


def _new_trip(client: TravelApiClient) -> None:
    st.header("Plan a new trip")
    st.write(
        "Describe the trip in your own words: where from and to, how many "
        "people, how long or which dates, your budget and what you enjoy. "
        "Anything missing will be asked for."
    )

    def use_example(text: str) -> None:
        ss["draft_request"] = text

    cols = st.columns(len(EXAMPLES))
    for col, example in zip(cols, EXAMPLES):
        col.button(
            short(example, 40),
            help=example,
            width="stretch",
            on_click=use_example,
            args=(example,),
        )

    with st.form("new-trip"):
        request = st.text_area(
            "Your trip",
            key="draft_request",
            height=140,
            max_chars=4000,
            placeholder=EXAMPLES[0],
        )
        submitted = st.form_submit_button("Plan my trip", type="primary")

    if submitted:
        if len(request.strip()) < 3:
            st.warning("Please describe your trip first.")
            return

        if _run(client.start_trip(request.strip()), "Planning your trip…"):
            st.rerun()


def _answer_missing(client: TravelApiClient, trip: dict) -> None:
    pending = trip["pending"]
    st.warning(pending["question"], icon="📝")

    for error in pending.get("errors", []):
        st.markdown(f"- {error}")

    with st.form(f"answer-{trip['thread_id']}", clear_on_submit=True):
        answer = st.text_area(
            "Your answer", placeholder="e.g. From Delhi, 6 days, 2 people"
        )
        submitted = st.form_submit_button("Continue planning", type="primary")

    if submitted and answer.strip():
        events = client.resume_trip(trip["thread_id"], {"answer": answer.strip()})

        if _run(events, "Continuing…"):
            st.rerun()


def _review(client: TravelApiClient, trip: dict) -> None:
    pending = trip["pending"]
    thread_id = trip["thread_id"]
    revisions_left = pending.get("revisions_left", 0)

    st.subheader("🧭 Your decision")
    st.caption(pending["question"])
    approve_col, reject_col = st.columns(2)

    if approve_col.button("✅ Approve itinerary", type="primary", width="stretch"):
        if _run(client.resume_trip(thread_id, {"action": "approve"}), "Saving your trip…"):
            _flash("Itinerary approved and saved to your profile.")
            st.rerun()

    with reject_col.popover("✖ Reject", width="stretch"):
        st.write("Reject this itinerary? The trip will be closed.")

        if st.button("Yes, reject it", type="primary"):
            if _run(client.resume_trip(thread_id, {"action": "reject"}), "Closing trip…"):
                st.rerun()

    with st.form(f"revise-{thread_id}", clear_on_submit=True):
        feedback = st.text_area(
            "Request changes",
            placeholder="e.g. Our budget is now ₹1 lakh, make it 5 days and add a "
            "relaxed spa afternoon.",
            disabled=revisions_left <= 0,
        )
        st.caption(
            (
                f"{revisions_left} revision(s) left. Change anything: dates, "
                "budget, travellers, pace or activities. The planner re-researches "
                "only what your change affects."
            )
            if revisions_left > 0
            else "No revisions left; please approve or reject."
        )
        submitted = st.form_submit_button("Revise itinerary", disabled=revisions_left <= 0)

    if submitted and feedback.strip():
        events = client.resume_trip(
            thread_id, {"action": "revise", "feedback": feedback.strip()}
        )

        if _run(events, "Revising your trip…"):
            st.rerun()


def _has_dates(trip: dict) -> bool:
    itinerary = trip.get("itinerary") or {}
    requirements = trip.get("requirements") or {}
    return bool(
        requirements.get("start_date")
        or all(day.get("date") for day in itinerary.get("days") or [{}])
    )


def _downloads(client: TravelApiClient, trip: dict) -> None:
    thread_id = trip["thread_id"]
    slug = short(trip["itinerary"]["destination"], 30).casefold()
    slug = "".join(char if char.isalnum() else "-" for char in slug).strip("-") or "trip"

    formats = [
        ("📄 Markdown", "markdown", "md", "text/markdown"),
        ("🧾 JSON", "json", "json", "application/json"),
    ]
    if _has_dates(trip):
        formats.append(("📅 Calendar (.ics)", "ics", "ics", "text/calendar"))

    cols = st.columns(len(formats))

    for col, (label, fmt, extension, mime) in zip(cols, formats):
        col.download_button(
            label,
            # Fetched only when clicked.
            data=lambda fmt=fmt: client.export_trip(thread_id, fmt),
            file_name=f"itinerary-{slug}.{extension}",
            mime=mime,
            key=f"download-{thread_id}-{fmt}",
            on_click="ignore",
            width="stretch",
        )


def _chat(client: TravelApiClient, trip: dict) -> None:
    """Ask the trip assistant questions about this trip."""

    thread_id = trip["thread_id"]
    key = f"chat-{thread_id}"
    history: list[dict] = ss.setdefault(key, [])

    st.caption(
        "Ask anything about this trip: what to wear, how to get from the "
        "airport, where to eat near the hotel, what a day costs…"
    )

    suggestions = [
        "How do I get from the airport to my hotel?",
        "What should I pack?",
        "Which day is best for photography?",
    ]
    picked = None

    if not history:
        cols = st.columns(len(suggestions))
        for col, suggestion in zip(cols, suggestions):
            if col.button(suggestion, key=f"{key}-{suggestion}", width="stretch"):
                picked = suggestion

    messages = st.container(height=420 if history else "content", border=bool(history))

    for turn in history:
        messages.chat_message(turn["role"]).markdown(turn["content"])

    question = st.chat_input("Ask about this trip", key=f"{key}-input", max_chars=2000) or picked

    if not question:
        return

    messages.chat_message("user").markdown(question)

    with messages.chat_message("assistant"):
        with st.spinner("Thinking…"):
            try:
                answer = client.ask(thread_id, question, history)
            except ApiError as error:
                st.error(error.message)
                return

        st.markdown(answer)

    history += [
        {"role": "user", "content": question},
        {"role": "assistant", "content": answer},
    ]


def _restart_with(client: TravelApiClient, request: str, label: str) -> None:
    if st.button(label, type="primary"):
        if _run(client.start_trip(request), "Planning your trip again…"):
            st.rerun()


def _details_tabs(client: TravelApiClient, trip: dict) -> None:
    """Itinerary plus every piece of research behind it."""

    itinerary = trip.get("itinerary")
    currency = (trip.get("requirements") or {}).get("budget_currency")
    flights, hotels = trip.get("flights") or [], trip.get("hotels") or []
    places = trip.get("activities") or []

    tabs = st.tabs(
        [
            "🗓 Itinerary",
            f"✈️ Flights ({len(flights)})",
            f"🏨 Hotels ({len(hotels)})",
            "🌦 Weather",
            f"📍 Places ({len(places)})",
            "💰 Budget",
            "💬 Ask",
            "📜 Log",
        ]
    )

    with tabs[0]:
        if itinerary:
            render_itinerary(itinerary, currency)
        else:
            st.caption("The itinerary will appear here.")
    with tabs[1]:
        render_flights(trip)
    with tabs[2]:
        render_hotels(trip)
    with tabs[3]:
        render_weather(trip.get("weather"))
    with tabs[4]:
        render_places(trip)
    with tabs[5]:
        render_costs(trip)
    with tabs[6]:
        _chat(client, trip)
    with tabs[7]:
        st.markdown(f"> {trip['request']}")
        render_requirements(trip.get("requirements"))
        st.divider()
        render_progress(trip.get("progress", []))


def _trip(client: TravelApiClient, thread_id: str) -> None:
    try:
        trip = client.get_trip(thread_id)
    except ApiError as error:
        if error.status_code != 404:
            raise

        st.error("This trip does not exist or belongs to another user.")
        st.button("Plan a new trip", on_click=_open_trip, args=(None,))
        return

    requirements = trip.get("requirements") or {}
    status = trip["status"]
    title = (
        f"Trip to {requirements['destination']}"
        if requirements.get("destination")
        else short(trip["request"], 60) or "Trip"
    )

    st.header(title)
    st.markdown(f"{status_label(status)} · `{thread_id}`")

    if status == "needs_input":
        with st.expander("Your request", expanded=True):
            st.markdown(f"> {trip['request']}")
            render_requirements(requirements)
        _answer_missing(client, trip)
        return

    render_overview(trip)

    if status == "approved":
        st.success("Approved. Your profile was updated from this trip.", icon="🎉")
    elif status == "rejected":
        st.info("You rejected this itinerary.", icon="✖")
    elif status == "failed":
        st.error("The itinerary did not pass validation after several attempts:")
        for error in trip.get("itinerary_errors", []):
            st.markdown(f"- {error}")
    elif status == "incomplete":
        st.warning(
            "This run stopped on an error (for example a model quota limit). "
            "Retrying continues from the last completed step.",
            icon="⚠️",
        )

        if st.button("🔁 Retry", type="primary"):
            with st.spinner("Retrying…"):
                client.retry_trip(thread_id)
            st.rerun()

    if trip.get("itinerary") and status in {"approved", "awaiting_review"}:
        _downloads(client, trip)

    _details_tabs(client, trip)

    if status == "awaiting_review":
        st.divider()
        _review(client, trip)
    elif status == "rejected":
        _restart_with(client, trip["request"], "Plan again with the same request")
    elif status == "failed":
        _restart_with(client, trip["request"], "Try again with the same request")


def _memory(client: TravelApiClient) -> None:
    st.header("Profile & memory")
    st.write(
        "Learned from the trips you approve and used to fill details you "
        "leave out, such as your home city or interests."
    )

    memory = client.memory()
    render_profile(memory["profile"])

    st.subheader("Approved trips")
    trips = memory["trips"]

    if trips:
        st.dataframe(
            [
                {
                    "Approved": trip["approved_at"][:10],
                    "Destination": trip["destination"],
                    "Days": trip["duration_days"],
                    "Budget": (
                        f"{trip['budget_amount']:,.0f} {trip.get('budget_currency') or ''}"
                        if trip.get("budget_amount")
                        else "—"
                    ),
                    "Plan": " · ".join(trip.get("day_titles", [])),
                }
                for trip in trips
            ],
            hide_index=True,
            width="stretch",
        )
    else:
        st.caption("No approved trips yet.")

    st.subheader("Privacy")

    with st.popover("🗑 Forget everything about me"):
        st.write("This deletes your profile, trip history and trip list. It cannot be undone.")

        if st.button("Delete my memory", type="primary"):
            client.forget()
            _open_trip(None)
            _flash("Your profile and trip history were deleted.", "🗑")
            st.rerun()


def main() -> None:
    st.set_page_config(
        page_title="Travel Planner",
        page_icon="✈️",
        layout="wide",
        menu_items={"About": "LangGraph travel planner"},
    )
    _show_flash()

    try:
        client = _sign_in()

        if client is None:
            return

        _sidebar(client)
        plan_tab, memory_tab = st.tabs(["🗺 Plan", "👤 Profile & memory"])

        with plan_tab:
            if ss.get("thread_id"):
                _trip(client, ss["thread_id"])
            else:
                _new_trip(client)

        with memory_tab:
            _memory(client)
    except AuthError:
        if get_ui_settings().api_key:
            st.error("The configured TRAVEL_API_KEY was rejected by the API.")
            return

        _sign_out("Your session expired. Please sign in again.")
        st.rerun()
    except ApiUnavailable as error:
        st.error(f"{error}. Check that the API is running at {get_ui_settings().api_url}.")
        st.button("Try again")
    except ApiError as error:
        st.error(f"The API returned an error ({error.status_code}): {error.message}")
        st.button("Reload")
