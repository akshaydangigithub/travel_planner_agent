# Travel Planner Agent — Project Memory

> Last structural update: 2026-08-18 (production restructure of the codebase).
> This file is the single source of truth for **what is built, how it is
> organised, and what comes next**. Update it after every meaningful step.

---

## 1. Project Goal

We are building a **production-level Travel Planner Agent from scratch using LangGraph**.

This is not just a demo chatbot. It is a serious learning + portfolio project where
each LangGraph concept is first understood and then implemented inside the Travel Planner.

### What the final system will do

A user provides a natural-language travel request such as:

> Plan a 7 day trip to Japan from Delhi for 2 people. My budget is ₹2 lakh. I like food, nature and photography.

The system will:

1. Extract structured travel requirements.
2. Validate the requirements.
3. Ask the user for missing/invalid information when necessary.
4. Research flights, hotels, weather, and activities.
5. Run independent research branches in parallel.
6. Use specialized agents/tools for research.
7. Aggregate research results.
8. Generate a structured day-by-day itinerary.
9. Validate the itinerary against constraints such as budget and duration.
10. Replan when validation fails.
11. Support human approval before finalizing the plan.
12. Persist graph state/checkpoints.
13. Maintain useful long-term user memory.
14. Stream progress/results.
15. Expose the system through a production API.
16. Add caching, persistence, authentication, observability, and production error handling.

---

## 2. How We Are Building It

The project is built **incrementally from the LangGraph core outward**.

We deliberately did NOT start with FastAPI, PostgreSQL, Redis, external APIs,
authentication, or deployment.

Learning/building order:

```text
LangGraph Fundamentals
        ↓
Travel Requirement Workflow
        ↓
Validation + Conditional Routing
        ↓
Cycles / Human Feedback
        ↓
Parallel Research
        ↓
Reducers
        ↓
Tools + Tool Calling
        ↓
Agent Loops
        ↓
Subgraphs
        ↓
Parallel Subgraphs / Fan-out + Fan-in
        ↓
Structured Research State
        ↓
Production Code Structure          ← DONE (2026-08-18)
        ↓
Itinerary Generation               ← CURRENT NEXT STEP
        ↓
Itinerary Validation
        ↓
Replanning
        ↓
Multi-Agent / Supervisor Architecture
        ↓
Human-in-the-Loop (interrupt)
        ↓
Checkpointing / Persistence
        ↓
Long-Term User Memory
        ↓
Streaming
        ↓
FastAPI
        ↓
PostgreSQL / Redis
        ↓
Real External Travel APIs
        ↓
Observability / LangSmith
        ↓
Production Hardening
```

Each step is implemented and tested before moving to the next.

---

## 3. Current Stack

- Python 3.12
- LangGraph
- LangChain Core
- Mistral LLM (`langchain-mistralai`)
- Pydantic
- python-dotenv
- typing-extensions

`requirements.txt`:

```text
langgraph
langchain-core
langchain-mistralai
python-dotenv
pydantic
typing-extensions
```

Not introduced yet: FastAPI, PostgreSQL, Redis, LangSmith, authentication,
real travel APIs, production deployment. These come later, once the LangGraph
architecture is mature.

---

## 4. Current Project Structure (after the production restructure)

```text
travel_planner/
│
├── main.py                         thin launcher → app.cli:main
├── pyproject.toml                  deps + `travel-planner = "app.cli:main"` script
├── requirements.txt
├── README.md                       flow diagram, layout, env vars, run instructions
├── memory.md                       ← this file
├── .env                            real secrets (gitignored)
├── .env.example                    template: MISTRAL_API_KEY, MISTRAL_MODEL, LOG_LEVEL
│
└── app/
    ├── __init__.py
    ├── cli.py                      entrypoint: configure logging, build state, run, report
    │
    ├── core/                       cross-cutting concerns (no graph logic here)
    │   ├── __init__.py
    │   ├── config.py               Settings dataclass + get_settings() + ConfigurationError
    │   ├── llm.py                  get_llm() — one cached ChatMistralAI for the whole app
    │   ├── logging.py              configure_logging() / get_logger()
    │   └── console.py              show() / prompt() — the ONLY place using print/input
    │
    ├── graph/
    │   ├── __init__.py             exports travel_graph, build_travel_graph, TravelState
    │   ├── state.py                TravelState + initial_state()
    │   ├── constants.py            Node / ValidationRoute / FlightNode / FlightRoute names
    │   ├── routers.py              route_after_validation
    │   ├── builder.py              top-level graph assembly (build_travel_graph)
    │   │
    │   ├── nodes/                  one module per stage of the main flow
    │   │   ├── __init__.py         re-exports every node
    │   │   ├── parsing.py          parse_request
    │   │   ├── validation.py       validate_requirements (+ _collect_errors)
    │   │   ├── interaction.py      ask_user, continue_plan
    │   │   ├── research.py         search_hotels, search_weather, search_activities
    │   │   └── aggregation.py      combine_research
    │   │
    │   └── subgraphs/
    │       ├── __init__.py
    │       └── flights/            the flight research subgraph
    │           ├── __init__.py     exports flight_graph, build_flight_graph
    │           ├── agent.py        flight_agent + get_flight_llm() (bind_tools)
    │           ├── nodes.py        extract_flights
    │           ├── routers.py      route_flight_agent
    │           └── builder.py      subgraph assembly (build_flight_graph)
    │
    ├── prompts/                    prompt text lives here, never inside node logic
    │   ├── __init__.py
    │   ├── planning.py             build_requirements_prompt(request, feedback)
    │   └── flight_research.py      FLIGHT_AGENT_SYSTEM_PROMPT, build_flight_request_prompt()
    │
    ├── schemas/                    pydantic models (one file per domain concept)
    │   ├── __init__.py             re-exports everything: `from app.schemas import ...`
    │   ├── requirements.py         TravelRequirements
    │   ├── flights.py              FlightResult
    │   └── itinerary.py            Itinerary, ItineraryDay
    │
    └── tools/
        ├── __init__.py             exports search_flights, FLIGHT_TOOLS
        └── flights.py              @tool search_flights (mock data for now)
```

### Where new code goes (follow this from now on)

| You are adding… | Put it in |
| --- | --- |
| a new graph node | `app/graph/nodes/<stage>.py`, export it from `nodes/__init__.py` |
| a new routing function | `app/graph/routers.py` (or the subgraph's `routers.py`) |
| a new node/route name | `app/graph/constants.py` |
| a new agent with a tool loop | `app/graph/subgraphs/<name>/` (agent.py, nodes.py, routers.py, builder.py) |
| a new pydantic model | `app/schemas/<concept>.py`, re-export from `schemas/__init__.py` |
| any prompt string | `app/prompts/<area>.py` |
| a new tool | `app/tools/<area>.py`, export a `*_TOOLS` list |
| a new setting / env var | `app/core/config.py` **and** `.env.example` |
| anything that prints to the user | `app/core/console.py` (interactive) or a logger (progress) |

---

## 5. The Production Restructure (2026-08-18)

**Nothing about the flow or the features changed.** The compiled graphs were
verified to have identical node and edge sets before/after, and the whole
pipeline was run end-to-end with a stubbed LLM.

### File moves

| Old | New |
| --- | --- |
| `app/config.py` | `app/core/config.py` |
| `app/graph/nodes.py` | split into `app/graph/nodes/{parsing,validation,interaction,research,aggregation}.py` |
| `app/graph/workflow.py` | `app/graph/builder.py` |
| `app/graph/flight_agent.py` | `app/graph/subgraphs/flights/{agent,routers}.py` |
| `app/graph/flight_workflow.py` | `app/graph/subgraphs/flights/{nodes,builder}.py` |
| `app/schemas/travel.py` | `app/schemas/{requirements,flights,itinerary}.py` |
| `main.py` (script body) | `app/cli.py` (`main.py` is now a 3-line launcher) |

### Improvements made

1. **One LLM instance.** `ChatMistralAI(...)` was constructed twice (in `nodes.py`
   and `flight_agent.py`) at import time. It is now `app/core/llm.py::get_llm()`,
   `@lru_cache`d and built lazily — importing the graph no longer needs credentials.
2. **Real settings object.** `Settings` is a frozen dataclass; a missing
   `MISTRAL_API_KEY` now raises a clear `ConfigurationError` instead of silently
   passing `None` and failing later as a confusing auth error.
3. **Logging instead of scattered `print`.** Progress messages
   (`Searching hotels...`, `Calling flight agent`) go through a configured logger.
   The genuinely interactive parts (`ask_user`) still use stdin/stdout but only
   through `app/core/console.py`, which makes them easy to swap for `interrupt()`
   in the human-in-the-loop phase.
4. **Prompts extracted.** System/human prompt text moved to `app/prompts/`.
5. **Named constants for nodes/routes.** `app/graph/constants.py` removes the
   risk of a typo'd edge silently creating a dangling node.
6. **Graph factories.** `build_travel_graph()` / `build_flight_graph()` return a
   compiled graph; the module-level `travel_graph` / `flight_graph` are kept for
   convenience. Factories matter later — checkpointers, test doubles and
   different configurations need to build the graph more than once.
7. **Fan-out/fan-in loop.** The four `continue_plan → X → combine_research` edge
   pairs are now a loop over `RESEARCH_NODES` in `builder.py`, so adding a fifth
   research branch is one list entry.
8. **`initial_state(user_request)`** in `state.py` — callers no longer hand-write
   the starting dict (this becomes important when FastAPI is the caller).
9. **Packaging fixed.** `pyproject.toml` had `travel-planner = "travel_planner:main"`
   pointing at a module that never existed; it is now `app.cli:main`, and the
   dependency list is filled in.
10. **Removed dead code:** the old unused `search_flights` *node* in `nodes.py`.
    It was never wired into the graph (`flight_research` uses the subgraph) and
    its name collided with the actual `@tool search_flights`.

### Architectural principle behind the layout

```text
app/core      →  knows nothing about the graph        (config, llm, logging, io)
app/schemas   →  knows nothing about the graph        (pure data contracts)
app/tools     →  knows only schemas                   (capabilities)
app/prompts   →  knows only schemas                   (text)
app/graph     →  wires all of the above into a flow   (orchestration)
app/cli       →  drives the graph                     (entrypoint / future API layer)
```

Dependencies point **inwards only**. When FastAPI arrives it replaces `app/cli.py`
and nothing inside `app/graph` has to change.

---

## 6. Current `TravelState`

`app/graph/state.py`:

```python
class TravelState(TypedDict):
    user_request: str
    user_feedback: str

    requirements: TravelRequirements | None

    validation_errors: list[str]

    flights: list[FlightResult]
    hotels: list
    weather: dict
    activities: list

    itinerary: Itinerary | None

    messages: Annotated[list, add]


def initial_state(user_request: str) -> TravelState:
    return {
        "user_request": user_request,
        "user_feedback": "",
        "requirements": None,
        "validation_errors": [],
        "itinerary": {},
        "messages": [],
    }
```

State principles learned:

- State is shared data flowing through the graph.
- Nodes should update only the fields they actually change.
- Do not blindly return `**state` from parallel nodes.
- Reducers only where multiple nodes legitimately update the same field.
- Application state and agent conversation history should eventually be
  separated (see the known issue in §21).

---

## 7. LangGraph Concepts Already Learned

### 7.1 State
`TravelState` via `TypedDict` — the shared structure passed between nodes.

### 7.2 Nodes
Current node inventory and where each one lives:

| Node | File |
| --- | --- |
| `parse_request` | `app/graph/nodes/parsing.py` |
| `validate_requirements` | `app/graph/nodes/validation.py` |
| `ask_user`, `continue_plan` | `app/graph/nodes/interaction.py` |
| `search_hotels`, `search_weather`, `search_activities` | `app/graph/nodes/research.py` |
| `combine_research` | `app/graph/nodes/aggregation.py` |
| `flight_research` (subgraph) | `app/graph/subgraphs/flights/` |

### 7.3 StateGraph
`StateGraph`, `add_node()`, `add_edge()`, `add_conditional_edges()`,
`START`, `END`, `compile()`, `invoke()`.

---

## 8. Structured LLM Output

`app/schemas/requirements.py`:

```python
class TravelRequirements(BaseModel):
    origin: str
    destination: str
    travelers: int

    start_date: str | None = None
    end_date: str | None = None
    duration_days: int | None = None

    budget_amount: float | None = None
    budget_currency: str = "USD"

    interests: list[str] = []
    preferences: list[str] = []
```

Used in `app/graph/nodes/parsing.py`:

```python
structured_llm = get_llm().with_structured_output(TravelRequirements)
prompt = build_requirements_prompt(state["user_request"], state["user_feedback"])
requirements = structured_llm.invoke(prompt)
```

**Architectural lesson: extraction and business validation are separate concerns.**
The LLM extracts. Python applies deterministic business rules.

---

## 9. Requirement Validation

`app/graph/nodes/validation.py` — deterministic Python, no LLM:

- Requirements exist
- Origin exists
- Destination exists
- Travelers > 0
- Budget, when provided, > 0

Errors accumulate in `validation_errors: list[str]`.

```text
parse_request
      ↓
validate_requirements
      ↓
 ┌────┴─────┐
VALID     INVALID
 ↓           ↓
Continue   Ask User
```

---

## 10. Conditional Edges

Nodes do work; routing functions decide where execution goes.

`app/graph/routers.py`:

```python
def route_after_validation(state: TravelState) -> str:
    if state["validation_errors"]:
        return ValidationRoute.ASK_USER
    return ValidationRoute.CONTINUE_PLAN
```

`app/graph/builder.py`:

```python
builder.add_conditional_edges(
    Node.VALIDATE_REQUIREMENTS,
    route_after_validation,
    {
        ValidationRoute.ASK_USER: Node.ASK_USER,
        ValidationRoute.CONTINUE_PLAN: Node.CONTINUE_PLAN,
    },
)
```

---

## 11. Cycles

Requirement correction loop:

```text
parse_request
      ↓
validate_requirements
      ├── VALID ──→ continue_plan
      └── INVALID
             ↓
          ask_user
             ↓
        user_feedback
             ↓
        parse_request
```

The current implementation uses `input()` via `app/core/console.py::prompt()`.
This is temporary. It becomes proper human-in-the-loop later:

```text
interrupt() → checkpoint → wait for user → resume
```

Because all console I/O is funnelled through one module, that swap is a small,
contained change.

---

## 12. Parallel Research / Fan-Out and Fan-In

```text
                         continue_plan
                              │
       ┌──────────────┬───────┼────────┬──────────────┐
       ▼              ▼       ▼        ▼              │
 flight_research   hotels  weather  activities        │
       │              │       │        │              │
       └──────────────┴───────┴────────┴──────────────┘
                              │
                              ▼
                     combine_research
                              │
                              ▼
                             END
```

Built in `builder.py` as:

```python
RESEARCH_NODES = (
    Node.FLIGHT_RESEARCH,
    Node.SEARCH_HOTELS,
    Node.SEARCH_WEATHER,
    Node.SEARCH_ACTIVITIES,
)

for research_node in RESEARCH_NODES:
    builder.add_edge(Node.CONTINUE_PLAN, research_node)
    builder.add_edge(research_node, Node.COMBINE_RESEARCH)
```

Taught: fan-out, fan-in, parallel branches, synchronization at the fan-in point,
state update rules during concurrent execution.

---

## 13. Parallel State Update Error (solved)

```text
InvalidUpdateError: At key 'user_request':
Can receive only one value per step. Use an Annotated key to handle multiple values.
```

Cause: parallel nodes returned the whole state (`{**state, "flights": ...}`), so
several nodes wrote the same keys in one step.

Fix — **parallel nodes return only the fields they update**:

```python
return {"hotels": [...], "messages": ["Hotel research completed."]}
```

Note: `parse_request` and `validate_requirements` still return `{**state, ...}`.
That is safe *only* because they run sequentially, alone in their step.

---

## 14. Reducers

```python
messages: Annotated[list, add]
```

Lets every branch append to one list:

```text
Flight agent    → conversation messages
Hotel node      → ["Hotel research completed."]
Weather node    → ["Weather research completed."]
Activity node   → ["Activity research completed."]
```

Do not add reducers merely to hide state conflicts.

---

## 15. Flight Tool

`app/tools/flights.py` — mock data for now, real API in Phase 9:

```python
@tool
def search_flights(origin, destination, start_date=None, end_date=None, travelers=1) -> list[dict]:
    return [{"airline": "Demo Airways", ..., "price": 42000, "currency": "INR"}]

FLIGHT_TOOLS = [search_flights]
```

`FLIGHT_TOOLS` exists so the agent and the `ToolNode` bind the **same** list —
they used to reference the tool separately in two files.

---

## 16. Flight Agent + Tool Calling

`app/graph/subgraphs/flights/`:

```python
# agent.py
@lru_cache(maxsize=1)
def get_flight_llm():
    return get_llm().bind_tools(FLIGHT_TOOLS)
```

Subgraph shape:

```text
START
  ↓
flight_agent
  ↓
route_flight_agent
  ├── tool call ──→ tools (ToolNode)
  │                    ↓
  │              extract_flights
  │                    ↓
  │              flight_agent
  └── no tool call ──→ END
```

Learned:

- `@tool` — defines what the system can do
- `bind_tools()` — makes the tool available to the LLM
- the LLM decides *whether* to call it
- `ToolNode` executes the call
- conditional routing decides loop vs. finish

---

## 17. Flight Tool-Calling Infinite Loop (solved)

Symptom: `Calling flight agent` printed forever.

Cause: the agent rebuilt the same `SystemMessage + HumanMessage` on every pass,
so it never saw the `ToolMessage` and re-requested the same tool.

Fix (now in `agent.py`):

```python
messages = state["messages"]

if not messages:
    messages = _opening_messages(state)   # System + Human, built once

response = get_flight_llm().invoke(messages)
```

Correct loop:

```text
SystemMessage + HumanMessage
     ↓
AIMessage(tool_call)
     ↓
ToolNode → ToolMessage
     ↓
flight_agent
     ↓
AIMessage(final answer)
     ↓
END
```

---

## 18. Structured Flight Results

`app/schemas/flights.py`:

```python
class FlightResult(BaseModel):
    airline: str
    origin: str
    destination: str
    departure: str | None = None
    arrival: str | None = None
    travelers: int
    price: float
    currency: str
```

`app/graph/subgraphs/flights/nodes.py` reads the last `ToolMessage`, parses its
JSON and validates each row into a `FlightResult`.

```text
search_flights → ToolMessage → extract_flights → FlightResult → state["flights"]
```

**Principle: the tool result is the source of truth for application data.**
Never parse the LLM's natural-language summary to recover critical data.

---

## 19. Flight Subgraph Integrated into Main Graph

```python
builder.add_node(Node.FLIGHT_RESEARCH, flight_graph)
```

A compiled graph is itself a runnable, so it plugs in as a node. It shares the
same `TravelState`, which is why the flight conversation lands in the shared
`messages` list (see §21).

---

## 20. Current Successful Execution

```text
INFO | app.graph.nodes.parsing            | Parsing travel request...
INFO | app.graph.nodes.interaction        | Requirements are valid. Continuing with travel planning...
INFO | app.graph.subgraphs.flights.agent  | Calling flight agent
INFO | app.graph.nodes.research           | Searching activities...
INFO | app.graph.subgraphs.flights.agent  | Calling flight agent
INFO | app.graph.nodes.research           | Searching hotels...
INFO | app.graph.nodes.research           | Checking weather...
INFO | app.graph.nodes.aggregation        | Combining research
```

Final state contains `requirements`, `flights` (`list[FlightResult]`), `hotels`,
`weather`, `activities`, `itinerary` (currently a raw dict), and `messages`.

The extractor correctly produces `duration_days=7` while leaving
`start_date=None` / `end_date=None`, because the user gave no calendar dates.
**We must NOT invent travel dates.**

Run it with:

```bash
python main.py          # or: travel-planner  (after `pip install -e .`)
```

---

## 21. Known Issues / Deliberate Debt

Tracked here so we fix them at the right step, not randomly.

1. **`combine_research` builds the itinerary.** It currently stuffs raw research
   into `state["itinerary"]` as a plain dict, which also disagrees with the
   declared type `Itinerary | None`. It should become a pure fan-in
   synchronization point once the itinerary agent exists. → fixed in Step 1 below.
2. **One shared `messages` list.** The flight agent's conversation and the
   branches' status strings live in the same reducer list. Once there is a second
   tool-calling agent they will interleave and confuse each other. → fixed in the
   multi-agent step (separate `flight_messages` / per-agent channels or a
   dedicated agent state).
3. **`ask_user` blocks on `input()`.** Fine for the CLI, impossible behind an API.
   → replaced by `interrupt()` in the human-in-the-loop step.
4. **Mock tools.** Flights/hotels/weather/activities all return fixed demo data.
   → replaced in Phase 9.
5. **No tests yet.** A `tests/` package should appear alongside the itinerary
   validator, when there is deterministic logic worth locking down.

---

## 22. NEXT IMMEDIATE TASK — Itinerary Agent

### Files to create/change

```text
CREATE  app/prompts/itinerary.py            ITINERARY_SYSTEM_PROMPT + build_itinerary_prompt(...)
CREATE  app/graph/nodes/itinerary.py        itinerary_agent node
EDIT    app/graph/constants.py              add Node.ITINERARY_AGENT = "itinerary_agent"
EDIT    app/graph/nodes/__init__.py         export itinerary_agent
EDIT    app/graph/nodes/aggregation.py      combine_research becomes a pure fan-in point
EDIT    app/graph/builder.py                combine_research → itinerary_agent → END
```

Schemas already exist in `app/schemas/itinerary.py`:

```python
class ItineraryDay(BaseModel):
    day: int
    title: str
    activities: list[str]


class Itinerary(BaseModel):
    destination: str
    duration_days: int
    days: list[ItineraryDay]
```

### The node

```python
structured_llm = get_llm().with_structured_output(Itinerary)
```

fed from `TravelRequirements` + `flights` + `hotels` + `weather` + `activities`.

### Target graph

```text
continue_plan
      ├── flight_research (subgraph)
      ├── search_hotels
      ├── search_weather
      └── search_activities
              ↓
       combine_research        ← fan-in only, no itinerary building
              ↓
       itinerary_agent
              ↓
        state["itinerary"] : Itinerary
              ↓
             END
```

### Done when

- `result["itinerary"]` is an `Itinerary` model (not a dict).
- `duration_days` matches the requirements.
- `len(days) == duration_days`.
- Activities in the plan come from the researched activities.

---

## 23. Roadmap — Ordered, With Dependencies

Each step depends on the one above it. Do not skip ahead; the "why it must come
after" column is the reason the order exists.

| # | Step | Depends on | Why it must come after | LangGraph concept |
| --- | --- | --- | --- | --- |
| 0 | ~~Production code structure~~ ✅ | research pipeline | needed a stable flow to reorganise | project architecture |
| 1 | **Itinerary Agent** ← NEXT | §0 | needs all research in state | structured output at the end of a fan-in |
| 2 | Itinerary Validation | 1 | nothing to validate until an itinerary exists | deterministic validation node |
| 3 | Replanning cycle | 2 | replanning is triggered *by* validation failure | cycles with a retry counter |
| 4 | Retry limits + failure path | 3 | only meaningful once a cycle can loop | loop guards, terminal states |
| 5 | Hotel / Weather / Activity agents + tools | 1 | mirrors the flight subgraph; needs the full flow working | subgraph reuse, parallel subgraphs |
| 6 | Supervisor / multi-agent routing | 5 | a supervisor needs ≥2 real agents to route between | supervisor pattern, agent state separation |
| 7 | Split `messages` per agent | 6 | the collision only hurts with multiple agents (Issue §21.2) | state channel design |
| 8 | Human-in-the-loop (`interrupt`) | 2, 4 | approval gates need a validated itinerary to approve | `interrupt()` + resume |
| 9 | Checkpointing / persistence | 8 | `interrupt()` is useless without a checkpointer | `MemorySaver` → `PostgresSaver`, threads |
| 10 | Long-term user memory | 9 | memory needs a persistence layer + a thread/user id | store vs. state separation |
| 11 | Streaming | 1 | needs a full pipeline worth streaming | `stream()` / `astream_events` modes |
| 12 | Test suite (`tests/`) | 2 | lock down deterministic validation + routing first | graph testing with stub LLMs |
| 13 | FastAPI layer | 8, 9, 11 | the API needs interrupt/resume, threads and streaming | app layer over the graph |
| 14 | PostgreSQL + Redis | 13 | real persistence/caching behind the API | checkpointer backends |
| 15 | Authentication | 13 | needs an API to protect | — |
| 16 | Real travel APIs | 5 | replace mocks once each agent is stable | tool error handling, retries, fallbacks |
| 17 | Observability / LangSmith | 13 | trace real traffic, not demo runs | tracing, evaluation |
| 18 | Production hardening | all | timeouts, rate limits, error contracts, deployment | — |

### Phase groupings (for context)

```text
Phase 1  Planning          → steps 1
Phase 2  Validation        → steps 2, 4
Phase 3  Replanning        → step 3
Phase 4  Multi-agent       → steps 5, 6, 7
Phase 5  Human-in-the-loop → step 8
Phase 6  Persistence       → step 9
Phase 7  User memory       → step 10
Phase 8  Streaming         → step 11
Phase 9  Real APIs         → step 16
Phase 10 Production backend→ steps 13, 14, 15, 17, 18
```

---

## 24. Long-Term Production Architecture

```text
                         CLIENT
                           │
                           ▼
                        FastAPI                    ← replaces app/cli.py
                           │
                    Authentication
                           │
                           ▼
                  Travel Application
                           │
                           ▼
                  LangGraph Supervisor
                           │
       ┌───────────────────┼───────────────────┐
       ▼                   ▼                   ▼
 Requirement          Research             Memory
 Workflow              System               System
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
           Flights       Hotels       Weather
              │            │            │
              └────────────┼────────────┘
                           ▼
                       Activities
                           │
                           ▼
                   Research Aggregator
                           │
                           ▼
                    Itinerary Agent
                           │
                           ▼
                  Itinerary Validator
                           │
                 ┌─────────┴─────────┐
                 ▼                   ▼
              Replanner          Human Review
                 │                   │
                 └─────────┬─────────┘
                           ▼
                    Final Response
                           │
                           ▼
                        Client
```

Supporting infrastructure:

```text
PostgreSQL → users, conversations, travel plans, checkpoints
Redis      → caching, rate limiting, temporary state
LangSmith  → traces, agent/tool debugging, latency, failures, evaluation
```

The current package layout already anticipates this: `app/graph` is the
orchestration core, and everything above it (CLI today, FastAPI later) is a
replaceable driver.

---

## 25. Teaching Rules

The user is learning LangGraph by building this one serious project progressively.

- Act as a senior AI Engineer mentoring a junior developer.
- Keep theory concise; spend most of the time implementing code.
- Explain architectural decisions and why they matter.
- Prefer production patterns over toy shortcuts.
- Introduce **one** LangGraph concept at a time.
- After each implementation, let the user run/test it.
- Debug the actual error instead of jumping to unrelated architecture.
- Do not repeat concepts already successfully learned (see §7–§19).
- Use the Travel Planner itself to reinforce every LangGraph concept.
- Avoid premature FastAPI/database/Redis.
- Do not dump the entire project at once — one meaningful improvement at a time.
- Preserve working code unless there is a concrete reason to refactor it.
- **New:** respect the package layout in §4 — put new code where the table says,
  keep prompts out of nodes, keep `print`/`input` out of everything except
  `app/core/console.py`, and add node names to `constants.py`.
- **New:** update this file (§4, §21, §22, §26) after every completed step.

---

## 26. Current Position

```text
State                          ✅
Nodes                          ✅
StateGraph                     ✅
Structured extraction          ✅
Validation                     ✅
Conditional routing            ✅
Cycles                         ✅
Parallel research              ✅
Fan-out / fan-in               ✅
Reducers                       ✅
Tools                          ✅
Tool calling                   ✅
ToolNode                       ✅
Agent loop                     ✅
Tool-loop debugging            ✅
Structured FlightResult        ✅
Flight subgraph                ✅
Parallel subgraph integration  ✅
Research aggregation point     ✅
Production code structure      ✅  (2026-08-18)

Itinerary Agent                ◀️  CURRENT NEXT STEP  (roadmap step 1)
Itinerary validation           ⏭  step 2
Replanning                     ⏭  step 3
Retry limits                   ⏭  step 4
Hotel/Weather/Activity agents  ⏭  step 5
Supervisor / multi-agent       ⏭  step 6
Split messages per agent       ⏭  step 7
Human-in-the-loop              ⏭  step 8
Checkpointing                  ⏭  step 9
Long-term memory               ⏭  step 10
Streaming                      ⏭  step 11
Tests                          ⏭  step 12
FastAPI                        ⏭  step 13
PostgreSQL / Redis             ⏭  step 14
Auth                           ⏭  step 15
Real travel APIs               ⏭  step 16
Observability                  ⏭  step 17
Production hardening           ⏭  step 18
```

Immediate goal: complete the **Itinerary Agent** (§22), test its structured
output, and only then move on to itinerary validation.
