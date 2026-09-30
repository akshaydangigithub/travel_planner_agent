# Travel Planner Agent — Project Memory + Tutor Brief

> Last update: 2026-09-30.
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
-   Avoid FastAPI / databases / Redis / auth / real APIs until their
    turn in the roadmap (§2).

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
→ budget check + targeted re-research + Command                      ✅ (built, see §17)
→ Human-in-the-Loop (interrupt)                                      NEXT
→ Checkpointing / persistence
→ Long-term user memory (Store)
→ Streaming
→ Tests
→ FastAPI → PostgreSQL / Redis → real travel APIs
→ Observability / LangSmith → production hardening
```

------------------------------------------------------------------------

## 3. Stack

-   Python 3.12, LangGraph 1.2.x, LangChain Core
-   Google Gemini via `ChatGoogleGenerativeAI` on **Vertex AI** (service
    account credentials file), model `gemini-2.5-flash`
-   Mistral remains in settings/deps but is not the active provider
-   Pydantic, python-dotenv, typing-extensions

`requirements.txt`: langgraph, langchain-core, langchain-mistralai,
langchain-google-genai, python-dotenv, pydantic, typing-extensions.

`grandalf` is not installed, so `draw_ascii()` fails; use
`graph.get_graph().draw_mermaid()`.

Not introduced yet: FastAPI, PostgreSQL, Redis, LangSmith, auth, real
travel APIs, deployment.

------------------------------------------------------------------------

## 4. Project Structure

``` text
travel_planner/
├── main.py                  thin launcher → app.cli:main
├── pyproject.toml, requirements.txt, README.md, .env, .env.example
├── memory.md                ← this file
└── app/
    ├── cli.py               run + readable report
    ├── core/                config.py, llm.py (get_llm), logging.py, console.py (show/prompt)
    ├── graph/
    │   ├── state.py         TravelState + initial_state()
    │   ├── constants.py     Node, ValidationRoute, ItineraryRoute,
    │   │                    ResearchAgentNode, ResearchAgentRoute
    │   ├── routers.py       route_after_validation, route_after_itinerary_validation,
    │   │                    route_research_agents
    │   ├── builder.py       build_travel_graph() → travel_graph
    │   ├── nodes/
    │   │   parsing.py  supervisor.py  validation.py  interaction.py
    │   │   aggregation.py  budget.py  itinerary.py
    │   │   itinerary_validation.py  replanning.py
    │   └── subgraphs/
    │       research_agent/  state.py spec.py nodes.py routers.py builder.py   (shared factory)
    │       flights/ hotels/ weather/ activities/   each: builder.py with a ResearchAgentSpec
    ├── prompts/     planning, flight_research, hotel_research, weather_research,
    │                activity_research, itinerary
    ├── schemas/     requirements, flights, hotels, weather, activities, itinerary
    └── tools/       flights, hotels, weather, activities   (all MOCK data, INR)
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

Dependencies flow inward: core → schemas → tools → prompts → graph → cli.

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
**`Command(update=..., goto=...)` including `goto=[Send(...)]`** (built
2026-09-30; user still to confirm it works against Gemini).

------------------------------------------------------------------------

## 6. TravelState

``` python
class TravelState(TypedDict):
    user_request: str
    user_feedback: str

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

    progress: Annotated[list[str], add]   # human readable run log (only reducer field)
```

`initial_state(user_request)` initialises **every** key (lists `[]`,
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
already booked); `budget_amount: float | None`, `budget_currency: str =
"USD"`, `interests`, `preferences`.

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
compare it with the tools' `'INR'`.

``` text
parse_request → validate_requirements ─┬─ valid → continue_plan
                                       └─ invalid → ask_user → parse_request
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

Offline unit checks passed (budget 200000 → pass; 120000 → re-research
cap 5143; 120000 with 1 retry used → proceed; 50000 → flights-only
message). Not yet verified end-to-end against Gemini: a run that actually
goes over budget. Test request idea: flights booked, 8 days, budget
₹40,000 → expect "Over budget (estimated 48,000 of 40,000);
re-researching hotels with maximum price per night 5,000 INR", a second
"Starting hotel research", then "Budget check passed: estimated 28,000 of
40,000" (only Demo Budget Inn returned). If the second hotel run still
returns both hotels, the agent did not pass `max_price_per_night` →
prompt problem; inspect the tool-call args.

Graph drawing does not show the `Command` edges from `check_budget`.

------------------------------------------------------------------------

## 12. Current Graph

``` text
START → parse_request → validate_requirements ─┬─ invalid → ask_user → parse_request
                                               └─ valid → continue_plan → supervisor
supervisor ──Send──→ {flight|hotel|weather|activity}_research   (only chosen)
each research node (agent→tools→extract subgraph, private messages)
        → combine_research → check_budget ─┬─ over budget → Send(hotel_research) → combine_research → check_budget
                                           └─ ok / skip / retry limit → itinerary_agent
itinerary_agent → validate_itinerary ─┬─ valid → END
                                      ├─ invalid + attempts left → replan_itinerary → itinerary_agent
                                      └─ invalid + max attempts → END
```

------------------------------------------------------------------------

## 13. Provider Notes (Gemini on Vertex)

-   Logs `AFC is enabled…` warning: harmless.
-   `gemini-2.5-flash` sometimes returns 503 (SDK retries) and 429
    `RESOURCE_EXHAUSTED` (free-tier ≈ 20 requests). Four agents call
    Gemini concurrently. Do not confuse these with graph bugs; test
    routers/nodes directly and use a fake LLM offline.

------------------------------------------------------------------------

## 14. Known Issues / Deliberate Debt

1.  `ask_user` uses blocking `input()` → replace with `interrupt()` in the
    human-in-the-loop phase.
2.  Mock tools return fixed data; later real APIs (specs/schemas should
    not need to change).
3.  No `tests/` yet. A fake LLM (object with `bind_tools()` /
    `with_structured_output()`) patched into `get_llm` in `parsing`,
    `itinerary` and `research_agent.nodes` runs the whole graph offline
    (used 2026-09-29/30).
4.  Gemini quota/transient errors: need backoff/provider fallback later.
5.  Budget logic only re-researches hotels; activities' cost is not in
    the estimate; flight price is treated as per person.
6.  `cli.py` `DEFAULT_REQUEST` concatenates `"…Dubai" "for 2 people"` →
    "Dubaifor" and lacks origin/length, so it always goes through
    `ask_user` first (user's latest run even showed "Indiafor").
7.  `budget_currency` default is `"USD"` when the user states no
    currency; with INR tools that causes a "currency mismatch" skip.
8.  The Mermaid drawing omits `Command`/`Send` edges.

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
Everything through Supervisor + Send + Budget check/Command   ✅ (budget loop awaiting real Gemini run)
Human-in-the-loop                                            ⏭ NEXT
Checkpointing / persistence                                  ⏭
Long-term user memory                                        ⏭
Streaming                                                    ⏭
Tests                                                        ⏭
FastAPI → PostgreSQL/Redis → auth → real APIs                ⏭
Observability / LangSmith → production hardening             ⏭
```

------------------------------------------------------------------------

## 17. NEXT SESSION — Start Here

**Step 0 (quick, user action):** run `python3 main.py` with flights
booked, 8 days and a budget of ₹40,000 and confirm the over-budget loop
in §11 fires. Open question the user was asked (answer it if they have
not): *after the hotel re-run, why does `hotel_research →
combine_research` lead back into `check_budget` instead of the
itinerary, and what changes if we add an edge from `hotel_research`
straight to `itinerary_agent`?* (Answer: the fixed edge re-enters
`combine_research → check_budget`, so the new hotel result is re-priced
and the retry guard ends the loop; a direct edge would skip the check
and would also make the initial pass skip the budget check.)

**Step 1: Human-in-the-Loop with `interrupt()`.**

-   Replace `ask_user`'s `input()` with `interrupt({...})` and resume
    with `Command(resume=...)`.
-   This **requires a checkpointer** (start with `InMemorySaver`) and a
    `thread_id` in the run config — so introduce checkpointing minimally
    here, then deepen it next.
-   Add an itinerary approval gate: after a valid itinerary, interrupt
    for approve / request changes; changes route back to
    `itinerary_agent` (or re-research) with `user_feedback`.
-   Update `app/cli.py` to loop: invoke → detect `__interrupt__` →
    prompt via `app/core/console.py` → resume.
-   Keep `input()` out of graph code (console helper only).
-   Test offline with the fake LLM first.

Then: persistent checkpointing (SQLite/Postgres saver), long-term
memory, streaming, tests (`tests/` with the fake LLM), and only then
FastAPI/databases/real APIs.
