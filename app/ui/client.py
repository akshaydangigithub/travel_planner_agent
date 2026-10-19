"""Typed HTTP client for the travel planner API, including SSE streams."""

import json
from collections.abc import Iterator
from typing import Any

import httpx


class ApiError(RuntimeError):
    """The API answered with an error status."""

    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message


class AuthError(ApiError):
    """The API key was missing or rejected (401)."""


class ApiUnavailable(RuntimeError):
    """The API could not be reached or timed out."""


def _error_message(response: httpx.Response) -> str:
    try:
        detail = response.json().get("detail")
    except ValueError:
        detail = None

    if isinstance(detail, list):  # FastAPI validation errors
        detail = "; ".join(str(item.get("msg", item)) for item in detail)

    return str(detail or response.reason_phrase or "Request failed")


def _raise_for_status(response: httpx.Response) -> None:
    if response.status_code < 400:
        return

    message = _error_message(response)

    if response.status_code == 401:
        raise AuthError(401, message)

    raise ApiError(response.status_code, message)


def parse_sse(lines: Iterator[str]) -> Iterator[dict[str, Any]]:
    """Turn ``event:``/``data:`` lines into dicts; a blank line ends an event."""

    event_name = None
    data: list[str] = []

    for line in lines:
        if line == "":
            if data:
                payload = json.loads("\n".join(data))

                if isinstance(payload, dict):
                    payload.setdefault("event", event_name or "message")
                    yield payload

            event_name, data = None, []
        elif line.startswith("event:"):
            event_name = line[6:].strip()
        elif line.startswith("data:"):
            data.append(line[5:].lstrip())

    if data:
        payload = json.loads("\n".join(data))
        if isinstance(payload, dict):
            payload.setdefault("event", event_name or "message")
            yield payload


class TravelApiClient:
    """One instance per visitor; the connection pool is shared."""

    def __init__(
        self,
        http: httpx.Client,
        api_key: str,
        request_timeout: float,
        stream_timeout: float,
    ) -> None:
        self._http = http
        self._headers = {"X-API-Key": api_key}
        self._timeout = httpx.Timeout(request_timeout)
        self._stream_timeout = httpx.Timeout(request_timeout, read=stream_timeout)

    def _send(
        self, method: str, path: str, timeout: httpx.Timeout | None = None, **kwargs: Any
    ) -> httpx.Response:
        try:
            response = self._http.request(
                method,
                path,
                headers=self._headers,
                timeout=timeout or self._timeout,
                **kwargs,
            )
        except httpx.HTTPError as error:
            raise ApiUnavailable(f"Cannot reach the API ({type(error).__name__})") from error

        _raise_for_status(response)
        return response

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        response = self._send(method, path, **kwargs)
        return response.json() if response.content else None

    def _stream(self, path: str, body: dict) -> Iterator[dict[str, Any]]:
        try:
            with self._http.stream(
                "POST",
                path,
                json=body,
                headers={**self._headers, "Accept": "text/event-stream"},
                timeout=self._stream_timeout,
            ) as response:
                if response.status_code >= 400:
                    response.read()
                    _raise_for_status(response)

                yield from parse_sse(response.iter_lines())
        except httpx.HTTPError as error:
            raise ApiUnavailable(
                f"The connection to the API was lost ({type(error).__name__})"
            ) from error

    # --- endpoints ---------------------------------------------------------

    def health(self) -> bool:
        try:
            return self._request("GET", "/health").get("status") == "ok"
        except (ApiError, ApiUnavailable):
            return False

    def whoami(self) -> str:
        return self._request("GET", "/me")["user_id"]

    def list_trips(self, limit: int = 50) -> list[dict]:
        return self._request("GET", "/trips", params={"limit": limit})

    def get_trip(self, thread_id: str) -> dict:
        return self._request("GET", f"/trips/{thread_id}")

    def start_trip(self, request: str) -> Iterator[dict]:
        return self._stream("/trips/stream", {"request": request})

    def resume_trip(self, thread_id: str, body: dict) -> Iterator[dict]:
        return self._stream(f"/trips/{thread_id}/resume/stream", body)

    def retry_trip(self, thread_id: str) -> dict:
        response = self._send(
            "POST", f"/trips/{thread_id}/retry", timeout=self._stream_timeout
        )
        return response.json()

    def export_trip(self, thread_id: str, fmt: str) -> bytes:
        """The itinerary file as bytes (markdown, json or ics)."""

        response = self._send(
            "GET", f"/trips/{thread_id}/export", params={"format": fmt}
        )
        return response.content

    def ask(self, thread_id: str, question: str, history: list[dict]) -> str:
        response = self._send(
            "POST",
            f"/trips/{thread_id}/ask",
            json={"question": question, "history": history},
            timeout=self._stream_timeout,
        )
        return response.json()["answer"]

    def memory(self) -> dict:
        return self._request("GET", "/me/memory")

    def forget(self) -> None:
        self._request("DELETE", "/me/memory")
