# Travel Planner Agent — Project Memory + Tutor Brief

> Last update: 2026-10-19.
> Single source of truth for the project. Update it after every
> meaningful implementation step.
>
> **This file is self-contained.** To continue learning in another chat
> (e.g. ChatGPT), paste the whole file and send it. Section 0 tells the
> assistant how to behave.

------------------------------------------------------------------------

## 0. Instructions for the AI assistant reading this (START HERE)

You are a **senior AI engineer mentoring a junior developer** who is
learning **LangGraph** by building a production-level Travel Planner
Agent. Everything below is the current project state. Continue from
**§17 (Next session)**.

How to teach:

-   Begin by briefly confirming where we are (2–3 lines), then go
    straight to the next step. Do not re-teach concepts in §5.
-   Introduce **one new LangGraph concept at a time**; keep theory short
    (a few paragraphs), spend most of the time implementing in this
    project.
-   Explain *why* a design decision is made (production patterns over
    toy shortcuts).
-   Give complete, paste-ready code with file paths that follow the
    package rules in §4. Do not dump the whole project; change only what
    is needed and preserve working code.
-   After each meaningful step, tell the user exactly what to run and
    what output to expect, and let them run it. Debug real errors they
    paste; do not jump to unrelated architecture.
-   End each step with one short comprehension question, and remind the
    user to update this file (provide the updated sections).
-   Tests and Observability/LangSmith/production hardening were
    deliberately left out by the user (2026-10-19); do not start them
    unless asked.

Code conventions (must follow): keep prompts out of nodes; no
`print`/`input` in graph code except `app/core/console.py`; node names
live in `app/graph/constants.py`; nodes return **only the keys they
change** (never `{**state}`); deterministic Python for validation, LLM
only where judgement/extraction is needed.

------------------------------------------------------------------------

## 1. Project Goal

Build a **production-level Travel Planner Agent with LangGraph**.

Example request:

> Plan a 7 day trip to Japan from Delhi for 2 people. My budget is ₹2
> lakh. I like food, nature and photography.

Final system goals:

1.  Extract structured travel requirements.
2.  Validate requirements; ask for missing/invalid info.
3.  Research flights, hotels, weather, activities (parallel, specialised
    agents with tools).
4.  Aggregate research, check budget, re-research if needed.
5.  Generate a structured day-by-day itinerary; validate; replan.
6.  Human approval, checkpoints/persistence, long-term user memory,
    streaming.
7.  FastAPI, caching, auth, observability, real APIs, production error
    handling.

------------------------------------------------------------------------

## 2. Roadmap

``` text
LangGraph fundamentals → requirement workflow → validation + routing
→ cycles / human feedback → parallel research → reducers → tools
→ agent loops → subgraphs → fan-out/fan-in → production structure   ✅
→ itinerary generation / validation / replanning + retry guard       ✅
→ hotel / weather / activity agents, shared agent factory            ✅
→ private subgraph state (split messages)                            ✅
→ supervisor + Send dispatch                                         ✅
→ budget check + targeted re-research + Command                      ✅ (verified on Gemini 2026-10-19)
→ Human-in-the-Loop (interrupt)                                      ✅ 2026-10-19
→ Checkpointing / persistence (memory / sqlite / postgres)           ✅ 2026-10-19
→ Long-term user memory (Store)                                      ✅ 2026-10-19
→ Streaming (updates + custom, SSE)                                  ✅ 2026-10-19
→ FastAPI + API-key auth → PostgreSQL / Redis → real travel APIs     ✅ 2026-10-19
→ Streamlit UI (API client) + Docker image/compose                   ✅ 2026-10-19
→ Tests                                                              OMITTED (user decision)
→ Observability / LangSmith → production hardening                   OMITTED (user decision)
```

------------------------------------------------------------------------

## 3. Stack

-   Python 3.12, LangGraph 1.2.x, LangChain Core
-   Google Gemini via `ChatGoogleGenerativeAI` on **Vertex AI** (service
    account credentials file), model `gemini-2.5-flash`
-   Mistral remains in settings/deps but is not the active provider
-   Pydantic, python-dotenv, typing-extensions

`requirements.txt`: langgraph, langgraph-checkpoint-sqlite,
langgraph-checkpoint-postgres, langchain-core, langchain-mistralai,
langchain-google-genai, python-dotenv, pydantic, typing-extensions,
fastapi, uvicorn[standard], httpx, psycopg[binary,pool], redis.
Installed with `uv pip install --python .venv/bin/python ...` (the venv has
no pip).

`grandalf` is not installed, so `draw_ascii()` fails; use
`graph.get_graph().draw_mermaid()`.

Live data: SerpApi (Google Flights / Hotels / Maps) + Open-Meteo weather
(geocoded with OSM Nominatim). Amadeus Self-Service was NOT used: it was
shut down on 2026-07-17. Not introduced: LangSmith, deployment (by choice).

------------------------------------------------------------------------

## 4. Project Structure

``` text
travel_planner/
├── main.py                  thin launcher → app.cli:main
├── pyproject.toml, requirements.txt, README.md, .env, .env.example
├── streamlit_app.py         thin launcher → app.ui.app:main
├── Dockerfile, .dockerignore  one image: API (default CMD) and UI (streamlit command)
├── .streamlit/config.toml   production Streamlit settings
├── docker-compose.yml       postgres (host port 5433) + redis; `--profile app` adds api + ui
├── memory.md                ← this file
└── app/
    ├── ui/                  Streamlit UI: app.py, client.py (httpx + SSE parser), components.py, config.py
    ├── cli.py               argparse CLI: stream, answer interrupts, --thread/--user/--memory/--forget
    ├── api/                 main.py (create_app, lifespan), routes.py, auth.py, schemas.py
    ├── services/planner.py  TripPlanner: start/resume/retry/_stream/snapshot/memory/forget
    ├── persistence.py       open_persistence() + user-memory helpers (get/put profile, trips)
    ├── integrations/        http.py (cached get_json), serpapi.py, open_meteo.py
    ├── core/                config.py, llm.py (get_llm), logging.py, console.py, cache.py
    ├── graph/
    │   ├── state.py         TravelState + initial_state()
    │   ├── constants.py     Node, ValidationRoute, ItineraryRoute,
    │   │                    ResearchAgentNode, ResearchAgentRoute
    │   ├── routers.py       route_after_validation, route_after_itinerary_validation,
    │   │                    route_research_agents
    │   ├── builder.py       build_travel_graph() → travel_graph
    │   ├── nodes/
    │   │   parsing.py  supervisor.py  validation.py  interaction.py
    │   │   aggregation.py  budget.py  itinerary.py  memory.py
    │   │   itinerary_validation.py  replanning.py
    │   └── subgraphs/
    │       research_agent/  state.py spec.py nodes.py routers.py builder.py   (shared factory)
    │       flights/ hotels/ weather/ activities/   each: builder.py with a ResearchAgentSpec
    ├── prompts/     planning, flight_research, hotel_research, weather_research,
    │                activity_research, itinerary
    ├── schemas/     requirements, flights, hotels, weather, activities, itinerary, profile
    └── tools/       flights, hotels, weather, activities   (mock INR data, or live via integrations/)
```

Package rules:

| Adding | Location |
|---|---|
| Graph node | `app/graph/nodes/<stage>.py` (export in `nodes/__init__.py`) |
| Router | `app/graph/routers.py` or subgraph router |
| Node/route constant | `app/graph/constants.py` |
| New research agent | `ResearchAgentSpec` in `app/graph/subgraphs/<name>/builder.py` |
| Pydantic model | `app/schemas/<concept>.py` |
| Prompt | `app/prompts/<area>.py` |
| Tool | `app/tools/<area>.py` |
| Setting/env var | `app/core/config.py` + `.env.example` |
| User I/O | `app/core/console.py` |
| Progress output | logger + `progress` state entry |
| External API client | `app/integrations/<provider>.py` (returns schema-shaped dicts) |
| Run/resume logic shared by CLI + API | `app/services/planner.py` |
| HTTP route | `app/api/routes.py` |

Dependencies flow inward: core → schemas → integrations → tools → prompts
→ persistence → graph → services → cli / api. (`core` must not import
`schemas`; that is why `persistence.py` is not in `core/`.)

------------------------------------------------------------------------

## 5. Concepts Already Learned (do not re-teach unless debugging)

State/`TypedDict`, nodes, `StateGraph`, `START`/`END`, `add_node`,
`add_edge`, `add_conditional_edges`, structured LLM output
(`with_structured_output`), deterministic validation, conditional
routing, cycles, parallel fan-out/fan-in, reducers (`Annotated[..., add]`,
`add_messages`), tools, `bind_tools`, `ToolNode`, agent tool loops,
subgraphs (compiled graph as node, private state schema, invoking from a
node with explicit input/output mapping), spec-driven node/subgraph
factories, supervisor pattern, dynamic fan-out with `Send`, why list
edges break with optional branches, controlled replanning + retry guard,
**`Command(update=..., goto=...)` including `goto=[Send(...)]`**.

Built 2026-10-19 (explain these when the user asks; they were implemented
for them, not yet taught step by step): `interrupt()` +
`Command(resume=...)`, checkpointers (`InMemorySaver`, `SqliteSaver`,
`PostgresSaver`) and `thread_id`, `graph.get_state()` (`.values`,
`.next`, `.interrupts`), retry from last checkpoint with
`graph.stream(None, config)`, the `Store` (`InMemoryStore`, `SqliteStore`,
`PostgresStore`) with namespaces, `Runtime` injection
(`runtime.store`), `get_config()`, `stream_mode=["updates","custom"]`
with `subgraphs=True`, `get_stream_writer()`, serializer allowlist.

------------------------------------------------------------------------

## 6. TravelState

``` python
class TravelState(TypedDict):
    user_id: str                          # thread owner + memory namespace
    user_profile: dict[str, Any]          # UserProfile dump, from load_profile

    user_request: str
    user_feedback: str                    # all corrections, joined by newlines

    requirements: TravelRequirements | None
    validation_errors: list[str]          # requirement validation only

    flights: list[FlightResult]
    hotels: list[HotelResult]
    weather: WeatherReport | None
    activities: list[ActivityResult]

    research_tasks: list[str]             # nodes the supervisor dispatched
    research_hints: dict[str, str]        # per research node constraint text
    budget_retries: int

    itinerary: Itinerary | None
    itinerary_errors: list[str]           # itinerary validation only
    replan_count: int

    itinerary_feedback: str               # latest change request from review
    revision_count: int
    review_decision: str                  # "" | "approved" | "rejected"

    progress: Annotated[list[str], add]   # human readable run log (only reducer field)
```

`initial_state(user_request, user_id)` initialises **every** key (lists `[]`,
`research_hints` `{}`, `budget_retries`/`replan_count` 0, optional
objects `None`).

There is no `messages` in `TravelState`: agent conversations live in
each research subgraph's private `ResearchAgentState`.

Principles: nodes return only changed fields; reducers only where
branches legitimately write the same field (`progress`);
`validation_errors` and `itinerary_errors` are separate on purpose.

------------------------------------------------------------------------

## 7. Requirement Extraction + Validation

`TravelRequirements` (`app/schemas/requirements.py`): `origin`,
`destination`, `travelers`, `start_date`, `end_date`, `duration_days`
are `| None = None` with `Field(description=...)`; `flights_booked`,
`accommodation_booked` (`bool = False`, set only if the user says it is
already booked); `budget_amount: float | None`, `budget_currency: str |
None = None` (was `"USD"`, which caused false currency mismatches),
`interests`, `preferences`.

Extraction: `get_llm().with_structured_output(TravelRequirements)` +
`REQUIREMENTS_SYSTEM_PROMPT` (`app/prompts/planning.py`): only stated
facts, null for missing, no placeholders, don't infer origin from
currency, derive `duration_days` from dates.

Lesson (2026-09-29): a *required* schema field forces the LLM to invent a
value ("Unknown"); make fields optional and let deterministic validation
decide what is mandatory.

`validate_requirements` (`nodes/validation.py`, deterministic):
origin/destination present (placeholders "Unknown", "N/A"… count as
missing), travelers > 0, trip length known (`duration_days` or both ISO
dates; `_normalize` fills `duration_days`), end ≥ start, duration ≥ 1,
budget > 0 when given. **`_normalize` also canonicalises the currency**
(`₹`→`INR`, `$`→`USD`, `€`, `£`, `¥`, else upper-cased) — added
2026-09-30 because Gemini returned `'₹'` and the budget check refused to
compare it with the tools' `'INR'`. A missing currency becomes the profile
currency, else `DEFAULT_CURRENCY` (INR).

`_apply_profile` (2026-10-19) fills only *gaps* from the saved profile:
origin → `home_origin`, empty interests → saved interests; each fill is
reported in `progress` so the user can correct it at review.

``` text
load_profile → parse_request → validate_requirements ─┬─ valid → continue_plan
                                                      └─ invalid → ask_user (interrupt) → parse_request
```

------------------------------------------------------------------------

## 8. Supervisor + Parallel Research (`Send`)

``` text
continue_plan → supervisor ──Send──→ flight/hotel/weather/activity_research (only chosen)
                                        └→ combine_research → check_budget → …
```

`supervisor` (deterministic, no LLM): skips flights when
`flights_booked`, hotels when `accommodation_booked`; weather and
activities always run. Writes `research_tasks` and a progress line.
`route_research_agents` returns `[Send(node, state) for node in tasks]`
(or `combine_research` if none).

**Fan-in = one edge per branch** (`for name in RESEARCH_NODES:
builder.add_edge(name, COMBINE_RESEARCH)`), *not* `add_edge([...], d)`: a
list edge waits for every listed node and silently never fires when the
supervisor skipped one. If a branch becomes multi-step at parent level,
use `defer=True` on the join node.

Verified with Gemini 2026-09-30: "my flight is already booked" →
`flights_booked=True` extracted, flight agent skipped, itinerary valid.

------------------------------------------------------------------------

## 9. Research Agents (shared factory) — DONE

All four agents use one factory
(`app/graph/subgraphs/research_agent/`). An agent is only a spec:

``` python
HOTEL_AGENT = ResearchAgentSpec(
    name="hotel",
    result_key="hotels",                 # TravelState key
    system_prompt=HOTEL_AGENT_SYSTEM_PROMPT,
    build_request_prompt=build_hotel_request_prompt,   # (requirements) -> str
    tools=HOTEL_TOOLS,
    result_type=list[HotelResult],       # validated with pydantic TypeAdapter
)                                        # empty_result defaults to list
hotel_graph = build_research_agent(HOTEL_AGENT)
hotel_research = make_research_node(HOTEL_AGENT, hotel_graph)
```

Weather: `result_type=WeatherReport | None, empty_result=lambda: None`.

Subgraph private state:
`ResearchAgentState{messages (add_messages), results, tool_rounds}`.

``` text
START → agent ─┬─ tool call → tools (ToolNode) → extract ─┬─ results → END
               │                                           └─ none → agent (retry)
               └─ no tool call → END          MAX_TOOL_ROUNDS = 2
```

`make_research_node` (parent adapter) invokes the subgraph from a node:
input = `[SystemMessage, HumanMessage]` built from `requirements`, **plus
`Constraint: <hint>` appended when
`state["research_hints"]["<name>_research"]` exists**; output = only
`{result_key: results, "progress": [...]}`. Why private state: a
subgraph sharing `TravelState` wrote all keys back (parallel
`InvalidUpdateError`) and agents saw each other's tool calls.

Extract node: reads only ToolMessages after the last AIMessage, skips
errors/invalid output with warnings, concatenates list results.
Each agent = 1 LLM call; a full run (parse + 4 agents + itinerary) = 6.

Prompts force exactly one tool call, `null` for missing dates, no
follow-ups/invented data. Hotel prompt also says: if the request has a
max price per night constraint, pass it as `max_price_per_night`.

Mock tools (INR): flights → one option, price 42000; hotels → "Demo
Central Hotel" 6000/night (4.3★) and "Demo Budget Inn" 3500/night
(3.9★); `search_hotels(..., max_price_per_night=None)` filters by price.

------------------------------------------------------------------------

## 10. Itinerary Agent, Validation, Replanning — DONE

`Itinerary{destination, duration_days, days: list[ItineraryDay{day,
title, activities}]}`. `itinerary_agent` uses
`get_llm().with_structured_output(Itinerary)`; input = requirements +
flights/hotels/weather/activities as JSON (`_to_json`) + previous
`itinerary_errors` when replanning. Prompt tells it not to suggest
booking what `flights_booked`/`accommodation_booked` mark as arranged.

`validate_itinerary` (deterministic): itinerary and requirements exist;
destination contained in itinerary destination (case-insensitive);
duration matches; number of days matches; day numbers sequential; every
day has activities. Writes `itinerary_errors`.

Replanning:

``` python
MAX_REPLAN_ATTEMPTS = 2
def route_after_itinerary_validation(state):
    if not state["itinerary_errors"]: return ItineraryRoute.VALID
    if state["replan_count"] >= MAX_REPLAN_ATTEMPTS: return ItineraryRoute.FAILED
    return ItineraryRoute.REPLAN
```

`replan_itinerary` only increments `replan_count`. **Never clear
`itinerary_errors` there** — the agent must read them first; the
validator overwrites them on the next pass.

------------------------------------------------------------------------

## 11. Budget Check + Targeted Re-research (`Command`) — BUILT 2026-09-30

File: `app/graph/nodes/budget.py`. Wired as
`combine_research → check_budget`; **no outgoing edges** from
`check_budget` (it returns a `Command`). Signature:

``` python
def check_budget(state) -> Command[Literal["itinerary_agent", "hotel_research"]]:
```

Logic (all deterministic):

1.  No `budget_amount` or no hotels → proceed to `itinerary_agent`.
2.  Currencies of flights/hotels must equal `budget_currency`, else skip
    (logged with the currencies compared).
3.  `estimate = cheapest flight × travelers + most expensive hotel ×
    duration_days` (worst case: the itinerary may pick any hotel).
4.  `estimate <= budget` → proceed ("Budget check passed…").
5.  Over budget and `budget_retries >= MAX_BUDGET_RETRIES (1)` → proceed
    anyway (logged).
6.  `cap = (budget − flight_cost) / nights`; `cap <= 0` → proceed
    ("flights alone exceed the budget").
7.  Otherwise return `Command(update={research_hints, budget_retries+1,
    progress}, goto=[Send(HOTEL_RESEARCH, payload)])` where `payload =
    {**state, "research_hints": hints}` — **`Send` carries its own
    input, so the hint must be in the payload as well as in `update`.**

Loop: `combine_research → check_budget → hotel_research →
combine_research → check_budget → itinerary_agent` (the re-run hotel
result overwrites `hotels`; the second pass goes through `check_budget`
again because `hotel_research → combine_research` is a fixed edge).

Every outcome is logged through `logger.info` and appended to
`progress`.

Bugs found by the user's first real run (2026-09-30):

-   No budget logs: only the over-budget path logged. Fixed: every path
    logs.
-   "Budget check skipped: currency mismatch": Gemini extracted `'₹'`,
    tools return `'INR'`. Fixed by currency normalisation in §7.

**Verified on Gemini 2026-10-19** (the CLI's default request): "Over budget
(estimated 48,000 of 40,000); re-researching hotels with maximum price per
night 5,000 INR" → second hotel search with `max_price_per_night: 5000` →
"Budget check passed: estimated 28,000 of 40,000".

That run exposed a prompt bug: on the *first* pass Gemini passed the
total budget (40000) as `max_price_per_night`. Fixed in the hotel system
prompt: only pass it when a `Constraint:` line gives one.

Graph drawing does not show the `Command` edges from `check_budget`.

------------------------------------------------------------------------

## 12. Current Graph

``` text
START → load_profile → parse_request → validate_requirements ─┬─ invalid → ask_user (interrupt) → parse_request
                                                              └─ valid → continue_plan → supervisor
supervisor ──Send──→ {flight|hotel|weather|activity}_research   (only chosen)
each research node (agent→tools→extract subgraph, private messages)
        → combine_research → check_budget ─┬─ over budget → Send(hotel_research) → combine_research → check_budget
                                           └─ ok / skip / retry limit → itinerary_agent
itinerary_agent → validate_itinerary ─┬─ valid → review_itinerary (interrupt)
                                      ├─ invalid + attempts left → replan_itinerary → itinerary_agent
                                      └─ invalid + max attempts → END
review_itinerary (Command) ─┬─ approve → save_profile → END
                            ├─ revise (≤3) → apply_revision (Command, see §12f)
                            ├─ revise with no text / over limit → review_itinerary (asks again)
                            └─ reject → END
```

`build_travel_graph(checkpointer, store)`; there is no module-level
`travel_graph` any more (an interrupting graph needs a checkpointer).

------------------------------------------------------------------------

## 12a. Human-in-the-Loop — DONE 2026-10-19 (`app/graph/nodes/interaction.py`)

-   `ask_user`: `answer = interrupt({"kind": "missing_requirements",
    "question", "errors"})`; appends the answer to `user_feedback`.
-   `review_itinerary` → `Command[...]`: `interrupt({"kind":
    "itinerary_review", "question", "itinerary", "revisions_left"})`.
    Resume value: `{"action": "approve"|"revise"|"reject", "feedback"}` or
    free text ("yes"/"approve" → approve, "no"/"reject" → reject, other
    text → revise with that text). Revise resets `replan_count` to 0.
    `MAX_REVISIONS = 3`.
-   Kinds/actions live in `constants.py` (`InterruptKind`, `ReviewAction`).
-   Lesson: the node **re-runs from the top on resume**, so nothing with
    side effects may come before `interrupt()`.

## 12b. Persistence + long-term memory — DONE 2026-10-19

`app/persistence.py`: `open_persistence(settings)` yields
`(checkpointer, store)` for `PERSISTENCE_BACKEND` = `memory` | `sqlite`
(default, `.data/travel_planner.db`) | `postgres` (`ConnectionPool`,
`autocommit`, `dict_row`, `prepare_threshold=0`; `.setup()` on start). The
checkpointer uses `JsonPlusSerializer(allowed_msgpack_modules=[our
schemas])` so only our models are rebuilt from the DB.

Memory (Store): namespace `("users", user_id)` key `"profile"` →
`UserProfile{home_origin, currency, interests, preferences,
trips_planned}`; namespace `("users", user_id, "trips")` key `thread_id`
→ `TripSummary`. `load_profile` (first node) reads it via
`runtime: Runtime` → `runtime.store`; `save_profile` (after approve)
merges and records the trip (`get_config()` for `thread_id`).
`delete_user_memory` = forget.

## 12c. Streaming + service layer — DONE 2026-10-19

`TripPlanner` (`app/services/planner.py`) is used by both CLI and API:
`start` / `resume` (`Command(resume=...)`) / `retry` (`stream(None)` from
the last checkpoint after e.g. a 429) / `snapshot` (status from
`get_state`: `needs_input`, `awaiting_review`, `approved`, `rejected`,
`failed`, `incomplete`) / `memory` / `forget`. `_stream` uses
`stream_mode=["updates","custom"], subgraphs=True`: top-level updates →
`progress` and `interrupt` events; custom events = research agents'
`tool_call`s written with `get_stream_writer()` (they only reach the
parent stream with `subgraphs=True` — learned the hard way). Ownership: a
thread whose `user_id` differs raises `TripNotFound` (same as unknown).

## 12d. FastAPI, auth, Postgres/Redis, real APIs — DONE 2026-10-19

-   `uvicorn app.api.main:app`; lifespan opens persistence once and stores
    a `TripPlanner` on `app.state`. Routes are sync `def` (thread pool).
    Endpoints: `/health`, `POST /trips` (+`/stream` SSE), `GET
    /trips/{id}`, `POST /trips/{id}/resume` (+`/stream`), `POST
    /trips/{id}/retry`, `GET|DELETE /me/memory`. 409 when resuming a trip
    that is not paused.
-   Auth: `API_KEYS=key:user_id,...`, header `X-API-Key` or Bearer,
    `hmac.compare_digest`; the API refuses to start without keys.
-   Redis: `app/core/cache.py` caches external API JSON (`REDIS_URL`,
    else in-process TTL cache); Redis errors = cache miss.
-   Real data (`TRAVEL_DATA_PROVIDER=live`, needs `SERPAPI_API_KEY`):
    flights (`google_flights_autocomplete` → id, `google_flights`; price
    divided by travellers, **assumed total-for-all-passengers — verify on
    first live run**), hotels (`google_hotels`, `rate_per_night`), places
    (`google_maps`, no prices), weather (Open-Meteo forecast ≤15 days,
    else last year's archive for the same dates; geocoding via Nominatim
    because Open-Meteo's geocoder maps "Goa" to Genoa/Philippines).
    Flights/hotels need dates, otherwise return `[]`. `ToolNode(...,
    handle_tool_errors=True)` turns API failures into error ToolMessages.
-   `GET /me`, `GET /trips` (thread index in the store, namespace
    `("users", uid, "threads")`, written by `TripPlanner.start`; deleted by
    forget). SSE starts with a `started` event carrying the `thread_id`.
-   Verified 2026-10-19: offline fake-LLM run on memory, sqlite (reopened
    between steps) and Postgres+Redis (temporary docker containers);
    FastAPI via TestClient (401/404/409, SSE); Open-Meteo live; SerpApi
    parsing with synthetic payloads only (no key available).

------------------------------------------------------------------------

## 12e. Streamlit UI — DONE 2026-10-19

`streamlit run streamlit_app.py`. The UI is **only an HTTP client** of the
API (`app/ui/client.py`; never imports the graph), so it needs no LLM
credentials or DB and scales separately. Its own settings
(`app/ui/config.py`: `TRAVEL_API_URL`, optional `TRAVEL_API_KEY`,
timeouts) are separate from `app.core.config` (which requires `ai.json`).
Features: API-key sign-in, new trip with live SSE progress (`st.status`),
missing-details form, review (approve / revise form with revisions left /
reject in a confirm popover), Markdown/JSON download, sidebar trip list +
open-by-id, retry for `incomplete`, profile + approved trips + forget.
Shared `httpx.Client` pool via `st.cache_resource`; 401 → sign out;
API down → clear message. Verified with `streamlit.testing.v1.AppTest`
against a live fake-LLM API, and both containers booted from the image.

------------------------------------------------------------------------

## 12f. Visible research, smart revisions, trip extras — DONE 2026-10-19

User report: UI showed only the itinerary; log said "Budget check skipped";
revising "my budget is 1 lakh" changed nothing. Root causes + fixes:

1.  **No dates → live flights/hotels return `[]`.** `validate_requirements`
    (`prepare_requirements` in `nodes/validation.py`) now fills dates:
    start+duration → end; neither → start = today + `DEFAULT_TRIP_LEAD_DAYS`
    (30). The note goes to state `assumptions` (shown in UI, CLI, prompt).
    Past start dates are an error. Parse prompt gets today's date and
    reads "1 lakh" = 100000.
2.  **Snapshot never carried research.** `TripSnapshot` now has
    `flights, hotels, weather, activities, assumptions, costs`.
3.  **Revise only rewrote text.** New node `apply_revision`
    (`nodes/revision.py`): re-extracts requirements with the change
    request, diffs fields (`changed_fields`) and routes with a `Command`:
    research inputs changed → `Send` only the affected research agents
    (`RESEARCH_INPUTS` map) → combine → check_budget; budget only →
    check_budget (hotel price cap lifted); otherwise → itinerary_agent.
4.  Currency words ("rupees") became code `RUPEES` → budget check always
    "currency mismatch". `currency_code()` maps names/symbols; non-ISO →
    default. Budget nights fixed: 3-day trip = 2 nights (`costing.nights`).

Extras:
-   Richer schemas (all new fields defaulted so old checkpoints load):
    flights (airports, flight numbers, duration, stops, round_trip,
    booking_url), hotels (class, reviews, amenities, lat/lon, image, link),
    places (rating, reviews, address, lat/lon, image), weather `daily`
    (`WeatherDay`, `source` forecast|historical|demo).
-   Structured itinerary: per-day `date`, `places`, `estimated_cost`,
    `weather_note`; plus `overview`, `getting_there` (e.g. DEL→IXC + 7 h
    drive to Manali), `flight_choice`, `hotel_choice`, `packing_list`,
    `tips`. Prompt gets a per-day allowance from the budget.
-   `app/costing.py` (top-level, depends only on schemas; used by prompts,
    graph and services): `estimate_trip_cost` → `CostBreakdown`.
    `validate_itinerary` adds one budget error (one replan only, never
    fails the trip) when daily spend pushes the total >5% over budget.
-   `GET /trips/{id}/export?format=markdown|json|ics`
    (`services/exports.py`, RFC 5545 escaping and line folding).
-   `POST /trips/{id}/ask` trip assistant (`services/assistant.py`,
    `prompts/assistant.py`), history passed by the client.
-   UI: overview metrics (budget vs estimate), tabs Itinerary / Flights /
    Hotels / Weather (charts) / Places (map) / Budget / Ask (chat) / Log,
    lazy downloads (callable `data`), revise hints. CLI prints research and
    costs at review.
-   Verified: Gemini + mock (budget revise → check_budget only; dates
    revise → flight/hotel/weather only), live SerpApi via API
    (Delhi→Manali: IndiGo DEL→IXC, 6 hotels, 12 mapped places, exports,
    ask), AppTest over all tabs/approve/chat.

------------------------------------------------------------------------

## 13. Provider Notes (Gemini on Vertex)

-   Logs `AFC is enabled…` warning: harmless.
-   `gemini-2.5-flash` sometimes returns 503 (SDK retries) and 429
    `RESOURCE_EXHAUSTED` (free-tier ≈ 20 requests). Four agents call
    Gemini concurrently. Do not confuse these with graph bugs; test
    routers/nodes directly and use a fake LLM offline.

------------------------------------------------------------------------

## 14. Known Issues / Deliberate Debt

1.  No `tests/` (user chose to omit). The fake LLM (object with
    `bind_tools()` / `with_structured_output()`) patched into `get_llm` in
    `parsing`, `itinerary` and `research_agent.nodes` runs the whole graph
    offline.
2.  Gemini quota/transient errors: no provider fallback; a failed run is
    `incomplete` and can be retried from its checkpoint (`--thread` /
    `POST /trips/{id}/retry`).
3.  Budget re-research only lowers hotel prices; daily spend is the LLM's
    estimate. "Find a cheaper hotel" as a revision rewrites the itinerary
    (it may pick a cheaper researched hotel) but does not re-search.
4.  Assistant chat history lives in the UI session only.
5.  SerpApi flight price basis (total vs per person) is an assumption.
6.  Two concurrent resumes of the same thread are not locked.
7.  The Mermaid drawing omits `Command`/`Send` edges.
8.  No LangSmith / tracing / rate limiting (omitted by the user).

------------------------------------------------------------------------

## 15. Teaching Rules (summary)

Senior-mentor tone; concise theory; implement inside this project; one
concept at a time; production patterns; user runs/tests after each step;
debug real errors; don't repeat learned concepts; follow the package
layout; prompts out of nodes; `print`/`input` only in
`app/core/console.py`; node names in `constants.py`; update this file
after every meaningful step.

------------------------------------------------------------------------

## 16. Current Position

``` text
Everything through Supervisor + Send + Budget/Command                ✅
Human-in-the-loop (interrupt, review gate)                           ✅
Checkpointing / persistence (memory, sqlite, postgres)               ✅
Long-term user memory (Store)                                        ✅
Streaming (CLI + SSE)                                                ✅
FastAPI + auth → PostgreSQL/Redis → real APIs                        ✅
Streamlit UI, visible research, smart revisions, costs, exports, chat ✅
Tests                                                                omitted by user
Observability / LangSmith → production hardening                     omitted by user
```

------------------------------------------------------------------------

## 17. NEXT SESSION — Start Here

The roadmap is complete except the two items the user omitted. Useful next
steps if the user wants to continue:

1.  Walk the user through the 2026-10-19 concepts (§5) using the code,
    one at a time: `interrupt` → checkpointer/thread → `get_state` →
    Store/Runtime → streaming modes.
2.  Confirm the SerpApi flight price basis (§12d) against Google Flights.
3.  Ideas: price alerts, multi-city trips, visa/advisory lookups.
4.  Postgres in practice: `docker compose up -d`,
    `PERSISTENCE_BACKEND=postgres`,
    `DATABASE_URL=postgresql://travel:travel@localhost:5433/travel_planner`
    (5433 because a local Postgres already uses 5432).
