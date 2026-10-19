# Travel Planner

A LangGraph agent that turns a free-form travel request into a reviewed,
day-by-day itinerary. It extracts structured requirements with an LLM,
asks the user for anything missing, researches flights, hotels, weather and
activities in parallel, checks the budget (re-researching hotels when over),
generates and validates an itinerary, and pauses for the user to approve,
revise or reject it. Approved trips teach a per-user long-term profile.

Usable from a Streamlit web UI, the command line, or over HTTP (FastAPI,
with streaming).

## Flow

```
START → load_profile → parse_request → validate_requirements
                            ↑                 │ invalid
                            └──── ask_user ◄──┘ (interrupt: missing details)
validate_requirements ─ valid → continue_plan → supervisor
supervisor ──Send──→ {flight|hotel|weather|activity}_research   (only those needed)
        → combine_research → check_budget ─┬─ over budget → hotel_research (price cap) → combine_research
                                           └─ ok → itinerary_agent → validate_itinerary
validate_itinerary ─┬─ invalid → replan_itinerary → itinerary_agent   (max 2)
                    ├─ failed → END
                    └─ valid → review_itinerary  (interrupt: approve / revise / reject)
review_itinerary ─┬─ approve → save_profile → END
                  ├─ revise  → apply_revision (max 3) ─┬─ route/dates/people/interests changed → only the affected research agents
                  │                                    ├─ budget changed → check_budget
                  │                                    └─ otherwise → itinerary_agent
                  └─ reject  → END
```

A revision such as "our budget is now ₹1 lakh" or "make it 5 days from
10 Dec" updates the trip's requirements and re-runs only the research the
change affects. Undated trips are priced for dates
`DEFAULT_TRIP_LEAD_DAYS` from today, and the planner says so.

Each `*_research` node runs its own tool-calling subgraph built from one
shared factory (`app/graph/subgraphs/research_agent/`) and a small
`ResearchAgentSpec`, with a private message history.

## Layout

```
app/
├── cli.py                 interactive CLI (stream, answer pauses, resume threads)
├── ui/                    Streamlit UI: an HTTP client of the API (app, client, components)
├── api/                   FastAPI app: routes, API-key auth, request bodies
├── services/              TripPlanner (start / resume / retry / snapshot / memory),
│                          exports (Markdown, JSON, iCalendar), trip assistant
├── costing.py             trip cost estimate vs budget (shared by graph and API)
├── persistence.py         checkpointer + store backends, user memory helpers
├── core/                  settings, logging, LLM factory, cache, console I/O
├── graph/                 state, constants, routers, builder, nodes, subgraphs
├── integrations/          SerpApi (flights, hotels, places) and Open-Meteo (weather)
├── prompts/               prompt text, kept out of node logic
├── schemas/               pydantic models
└── tools/                 LangChain tools (mock or live data)
```

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # then edit
```

Place the Vertex AI service account JSON at `ai.json` (or set
`GOOGLE_CREDENTIALS_FILE`).

| Variable | Default | Purpose |
| --- | --- | --- |
| `GOOGLE_CREDENTIALS_FILE` | `ai.json` | Vertex AI service account |
| `GOOGLE_CLOUD_LOCATION` | `us-central1` | Vertex AI region |
| `GOOGLE_GENAI_MODEL` | `gemini-2.5-flash` | chat model |
| `LOG_LEVEL` | `INFO` | root log level |
| `DEFAULT_CURRENCY` | `INR` | budget currency when none is stated or remembered |
| `DEFAULT_TRIP_LEAD_DAYS` | `30` | an undated trip is assumed to start this many days from today |
| `PERSISTENCE_BACKEND` | `sqlite` | `memory`, `sqlite` or `postgres` |
| `SQLITE_PATH` | `.data/travel_planner.db` | sqlite file |
| `DATABASE_URL` | — | Postgres URL (required for `postgres`) |
| `REDIS_URL` | — | Redis cache for travel API responses (in-process when empty) |
| `CACHE_TTL_SECONDS` | `21600` | cache lifetime |
| `TRAVEL_DATA_PROVIDER` | `mock` | `mock` demo data or `live` APIs |
| `SERPAPI_API_KEY` | — | required for `live` (flights, hotels, places) |
| `HTTP_TIMEOUT_SECONDS` | `20` | external API timeout |
| `API_KEYS` | — | `key:user_id,...`; required for the HTTP API |

### Postgres and Redis (optional)

```bash
docker compose up -d
# .env
PERSISTENCE_BACKEND=postgres
DATABASE_URL=postgresql://travel:travel@localhost:5433/travel_planner
REDIS_URL=redis://localhost:6379/0
```

Tables are created on startup.

### Live travel data

`TRAVEL_DATA_PROVIDER=live` uses SerpApi (Google Flights, Google Hotels,
Google Maps) and Open-Meteo for weather (geocoded with OpenStreetMap
Nominatim; no key needed). Flights and hotels need dates, so undated trips
use assumed dates (shown to the user). Prices are requested in the budget
currency. Results include airports, flight numbers, hotel photos,
amenities and map coordinates.

## Web UI (Streamlit)

The UI talks to the API over HTTP, so start the API first:

```bash
API_KEYS=dev-key:alice uvicorn app.api.main:app      # terminal 1
streamlit run streamlit_app.py                        # terminal 2 → http://localhost:8501
```

Sign in with an API key (`dev-key`). The UI covers every feature:

- plan a trip from free text, with live progress and research tool calls;
- answer missing details when the planner asks;
- see everything behind the plan: overview metrics (budget vs estimated
  cost), a day-by-day itinerary with dates, weather notes and daily spend,
  flight options, hotel cards with photos, a weather chart, a map of
  hotels and places, and a cost breakdown;
- review the itinerary: approve, request changes (up to 3; dates, budget,
  travellers or pace), or reject;
- ask the trip assistant questions ("how do I get from the airport?");
- download the itinerary as Markdown, JSON or a calendar file (.ics);
- list and reopen all your trips, or open one by id;
- retry a run that stopped on an error;
- see your saved profile and approved trips, or delete them.

| Variable | Default | Purpose |
| --- | --- | --- |
| `TRAVEL_API_URL` | `http://localhost:8000` | API base URL |
| `TRAVEL_API_KEY` | — | if set, every visitor uses this key (no sign-in; single-user only) |
| `UI_REQUEST_TIMEOUT_SECONDS` | `30` | normal requests |
| `UI_STREAM_TIMEOUT_SECONDS` | `300` | longest silence on a streaming run |

Production settings (headless, XSRF protection, no usage stats, no error
details shown to visitors) are in `.streamlit/config.toml`.

## Docker

```bash
docker compose --profile app up -d --build
# UI  http://localhost:8501   API http://localhost:8000/docs
```

Runs Postgres, Redis, the API (2 uvicorn workers) and the UI from one
image, as a non-root user, with health checks. `.env` must contain
`API_KEYS`; `ai.json` is mounted read-only as the Google credentials.

## CLI

```bash
python main.py "Plan a 5 day trip to Goa from Mumbai for 2 people, budget ₹60,000"
python main.py --thread <id>          # resume a paused trip, or retry one that hit an error
python main.py --user alice "..."     # memory is per user (default: local)
python main.py --memory               # show the saved profile and trips
python main.py --forget               # delete them
```

The CLI streams progress and research tool calls, asks for missing details,
then shows the itinerary and asks you to `approve`, `reject` or describe
changes. Ctrl+C at a question pauses the trip; resume it later with
`--thread`.

## HTTP API

```bash
API_KEYS=dev-key:alice uvicorn app.api.main:app --reload
# docs: http://localhost:8000/docs
```

Send `X-API-Key: <key>` (or `Authorization: Bearer <key>`).

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health` | liveness |
| GET | `/me` | the user id behind the API key |
| GET | `/trips` | your trips, newest first, with status |
| POST | `/trips` | start a trip, run until it pauses or finishes |
| POST | `/trips/stream` | same, as Server-Sent Events |
| GET | `/trips/{id}` | current snapshot |
| POST | `/trips/{id}/resume` | answer a pause (`/resume/stream` for SSE) |
| POST | `/trips/{id}/retry` | continue a trip that stopped on an error |
| GET | `/trips/{id}/export?format=` | `markdown`, `json` or `ics` file |
| POST | `/trips/{id}/ask` | ask the trip assistant (`{"question", "history"}`) |
| GET / DELETE | `/me/memory` | read / delete your profile and trip history |

A snapshot holds the requirements, any `assumptions`, the research
(`flights`, `hotels`, `weather`, `activities`), the `itinerary` and
`costs` (estimate vs budget). Its `status` is one of `needs_input`, `awaiting_review`,
`approved`, `rejected`, `failed` or `incomplete`; `pending` holds the
question. Resume bodies: `{"answer": "From Delhi"}` for `needs_input`,
`{"action": "approve"}`, `{"action": "revise", "feedback": "add a beach day"}`
or `{"action": "reject"}` for `awaiting_review`.

```bash
curl -N -X POST localhost:8000/trips/stream \
  -H 'X-API-Key: dev-key' -H 'Content-Type: application/json' \
  -d '{"request": "7 day trip to Japan from Delhi for 2, budget ₹2 lakh"}'
```

SSE events: `started` (with the `thread_id`), `progress`, `tool_call`,
`interrupt`, then `done` (the snapshot), or `error` followed by `done`.
