"""FastAPI application.

    uvicorn app.api.main:app --reload
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import router
from app.core.config import ConfigurationError, get_settings
from app.core.logging import configure_logging
from app.graph import build_travel_graph
from app.persistence import open_persistence
from app.services import TripPlanner


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Open persistence once per process and share one compiled graph."""

    settings = get_settings()
    configure_logging(settings.log_level)

    if not settings.api_keys:
        raise ConfigurationError("Set API_KEYS before starting the API.")

    with open_persistence(settings) as (checkpointer, store):
        app.state.planner = TripPlanner(build_travel_graph(checkpointer, store))
        yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="Travel Planner Agent",
        version="0.2.0",
        description="LangGraph travel planner with human review, "
        "persistent threads and long-term traveller memory.",
        lifespan=lifespan,
    )
    app.include_router(router)
    return app


app = create_app()


def run() -> None:
    """Console script: serve the API with uvicorn."""

    import uvicorn

    uvicorn.run("app.api.main:app", host="0.0.0.0", port=8000)
