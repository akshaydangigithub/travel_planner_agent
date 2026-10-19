"""HTTP routes. Each trip is a checkpointed LangGraph thread.

Every run endpoint has two forms:

- JSON: runs until the trip pauses or finishes and returns a snapshot;
- ``/stream``: Server-Sent Events (``started``, ``progress``, ``tool_call``,
  ``interrupt``, then ``done`` with the snapshot, or ``error``).

Routes are plain ``def``: the graph is synchronous, so FastAPI runs them
in its thread pool instead of blocking the event loop.
"""

import json
from collections.abc import Iterator
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.responses import StreamingResponse

from app.api.auth import CurrentUser
from app.api.schemas import AskRequest, AskResponse, ResumeRequest, TripRequest
from app.core.logging import get_logger
from app.services import (
    EXPORT_FORMATS,
    NothingToExport,
    TripNotFound,
    TripListItem,
    TripNotPaused,
    TripPlanner,
    TripSnapshot,
    UserMemory,
    export,
    file_name,
)

logger = get_logger(__name__)

router = APIRouter()


def _planner(request: Request) -> TripPlanner:
    return request.app.state.planner


def _run(events: Iterator[dict[str, Any]]) -> None:
    """Drain a run; provider failures leave the trip retryable."""

    try:
        for _ in events:
            pass
    except (TripNotFound, TripNotPaused):
        raise
    except Exception:  # noqa: BLE001 - reported through the snapshot status
        logger.exception("Trip run stopped on an error")


def _sse(
    planner: TripPlanner, user_id: str, thread_id: str, events: Iterator[dict]
) -> StreamingResponse:
    def body() -> Iterator[str]:
        # First event: lets a client keep the trip even if the stream breaks.
        yield f"event: started\ndata: {json.dumps({'event': 'started', 'thread_id': thread_id})}\n\n"

        try:
            for event in events:
                yield f"event: {event['event']}\ndata: {json.dumps(event, default=str)}\n\n"
        except Exception as error:  # noqa: BLE001
            logger.exception("Trip stream stopped on an error")
            data = json.dumps({"event": "error", "message": type(error).__name__})
            yield f"event: error\ndata: {data}\n\n"

        snapshot = planner.snapshot(user_id, thread_id)
        yield f"event: done\ndata: {snapshot.model_dump_json()}\n\n"

    return StreamingResponse(
        body(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _not_found(thread_id: str) -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, f"Trip {thread_id} not found")


@router.get("/health", tags=["meta"])
def health() -> dict:
    return {"status": "ok"}


@router.get("/me", tags=["meta"])
def whoami(user_id: CurrentUser) -> dict:
    return {"user_id": user_id}


@router.get("/trips", response_model=list[TripListItem], tags=["trips"])
def list_trips(user_id: CurrentUser, request: Request, limit: int = 50):
    return _planner(request).list_trips(user_id, min(max(limit, 1), 200))


@router.post("/trips", response_model=TripSnapshot, tags=["trips"])
def create_trip(body: TripRequest, user_id: CurrentUser, request: Request):
    planner = _planner(request)
    thread_id, events = planner.start(user_id, body.request)
    _run(events)
    return planner.snapshot(user_id, thread_id)


@router.post("/trips/stream", tags=["trips"])
def create_trip_stream(body: TripRequest, user_id: CurrentUser, request: Request):
    planner = _planner(request)
    thread_id, events = planner.start(user_id, body.request)
    return _sse(planner, user_id, thread_id, events)


@router.get("/trips/{thread_id}", response_model=TripSnapshot, tags=["trips"])
def get_trip(thread_id: str, user_id: CurrentUser, request: Request):
    try:
        return _planner(request).snapshot(user_id, thread_id)
    except TripNotFound:
        raise _not_found(thread_id) from None


def _resume_events(
    planner: TripPlanner, user_id: str, thread_id: str, body: ResumeRequest
) -> Iterator[dict]:
    try:
        return planner.resume(user_id, thread_id, body.to_resume_value())
    except TripNotFound:
        raise _not_found(thread_id) from None
    except TripNotPaused as error:
        raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from None


@router.post("/trips/{thread_id}/resume", response_model=TripSnapshot, tags=["trips"])
def resume_trip(
    thread_id: str, body: ResumeRequest, user_id: CurrentUser, request: Request
):
    planner = _planner(request)
    _run(_resume_events(planner, user_id, thread_id, body))
    return planner.snapshot(user_id, thread_id)


@router.post("/trips/{thread_id}/resume/stream", tags=["trips"])
def resume_trip_stream(
    thread_id: str, body: ResumeRequest, user_id: CurrentUser, request: Request
):
    planner = _planner(request)
    events = _resume_events(planner, user_id, thread_id, body)
    return _sse(planner, user_id, thread_id, events)


@router.post("/trips/{thread_id}/retry", response_model=TripSnapshot, tags=["trips"])
def retry_trip(thread_id: str, user_id: CurrentUser, request: Request):
    planner = _planner(request)

    try:
        events = planner.retry(user_id, thread_id)
    except TripNotFound:
        raise _not_found(thread_id) from None
    except TripNotPaused as error:
        raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from None

    _run(events)
    return planner.snapshot(user_id, thread_id)


@router.get("/trips/{thread_id}/export", tags=["trips"])
def export_trip(
    thread_id: str,
    user_id: CurrentUser,
    request: Request,
    format: Literal["markdown", "json", "ics"] = "markdown",
) -> Response:
    """Download the itinerary as Markdown, JSON or an iCalendar file."""

    try:
        snapshot = _planner(request).snapshot(user_id, thread_id)
        body = export(snapshot, format)
        name = file_name(snapshot, format)
    except TripNotFound:
        raise _not_found(thread_id) from None
    except NothingToExport as error:
        raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from None

    return Response(
        body,
        media_type=f"{EXPORT_FORMATS[format][0]}; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )


@router.post("/trips/{thread_id}/ask", response_model=AskResponse, tags=["trips"])
def ask_about_trip(
    thread_id: str, body: AskRequest, user_id: CurrentUser, request: Request
):
    """Ask the trip assistant a question about this trip."""

    try:
        answer = _planner(request).ask(
            user_id,
            thread_id,
            body.question,
            [turn.model_dump() for turn in body.history],
        )
    except TripNotFound:
        raise _not_found(thread_id) from None
    except Exception as error:  # noqa: BLE001 - model/provider failure
        logger.exception("Trip assistant failed")
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            f"The assistant is unavailable right now ({type(error).__name__}).",
        ) from None

    return AskResponse(answer=answer)


@router.get("/me/memory", response_model=UserMemory, tags=["memory"])
def get_memory(user_id: CurrentUser, request: Request):
    return _planner(request).memory(user_id)


@router.delete("/me/memory", status_code=status.HTTP_204_NO_CONTENT, tags=["memory"])
def forget_memory(user_id: CurrentUser, request: Request) -> None:
    _planner(request).forget(user_id)
