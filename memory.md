# Travel Planner Agent --- Project Memory

> Last update: 2026-09-29 This file is the single source of truth for
> the current Travel Planner Agent project. Update it after every
> meaningful implementation step.

------------------------------------------------------------------------

## 1. Project Goal

We are building a **production-level Travel Planner Agent from scratch
using LangGraph**.

Example request:

> Plan a 7 day trip to Japan from Delhi for 2 people. My budget is ₹2
> lakh. I like food, nature and photography.

Final system goals:

1.  Extract structured travel requirements.
2.  Validate requirements.
3.  Ask for missing/invalid information.
4.  Research flights, hotels, weather, and activities.
5.  Run independent research branches in parallel.
6.  Use specialized agents/tools.
7.  Aggregate research.
8.  Generate a structured day-by-day itinerary.
9.  Validate the itinerary.
10. Replan when validation fails.
11. Add human approval.
12. Persist checkpoints/state.
13. Maintain useful long-term user memory.
14. Stream progress/results.
15. Expose through FastAPI.
16. Add caching, authentication, observability, real APIs, and
    production error handling.

We are learning LangGraph by implementing each concept directly inside
this project.

------------------------------------------------------------------------

## 2. Current Learning / Build Order

``` text
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
Production Code Structure              ✅
        ↓
Itinerary Generation                   ✅
        ↓
Itinerary Validation                   ✅
        ↓
Replanning Cycle + Retry Guard         ✅
        ↓
Hotel / Weather / Activity Agents      ✅
        ↓
Split Agent Messages (private state)   ✅
        ↓
Supervisor / Multi-Agent Architecture  NEXT
        ↓
Human-in-the-Loop
        ↓
Checkpointing / Persistence
        ↓
Long-Term User Memory
        ↓
Streaming
        ↓
Tests
        ↓
FastAPI
        ↓
PostgreSQL / Redis
        ↓
Real Travel APIs
        ↓
Observability / LangSmith
        ↓
Production Hardening
```

------------------------------------------------------------------------

## 3. Current Stack

-   Python 3.12
-   LangGraph
-   LangChain Core
-   Google Gemini through `ChatGoogleGenerativeAI`
-   Current model: `gemini-2.5-flash`
-   Mistral integration remains in settings/dependencies but is not the
    active provider
-   Pydantic
-   python-dotenv
-   typing-extensions

Current `requirements.txt` includes:

``` text
langgraph
langchain-core
langchain-mistralai
langchain-google-genai
python-dotenv
pydantic
typing-extensions
```

Packaging/docs: `requirements.txt`, `pyproject.toml`, `.env.example`
and README all document Google Gemini as the active provider (fixed
2026-09-29). `grandalf` is not installed, so `draw_ascii()` fails; use
`draw_mermaid()` or install it if a graph picture is needed.

Not introduced yet:

-   FastAPI
-   PostgreSQL
-   Redis
-   LangSmith
-   Authentication
-   Real travel APIs
-   Production deployment

------------------------------------------------------------------------

## 4. Current Project Structure

``` text
travel_planner/
│
├── main.py                         thin launcher → app.cli:main
├── pyproject.toml
├── requirements.txt
├── README.md
├── memory.md                       ← this file
├── .env
├── .env.example
│
└── app/
    ├── __init__.py
    ├── cli.py                      run + readable report (progress, itinerary)
    │
    ├── core/
    │   ├── config.py
    │   ├── llm.py
    │   ├── logging.py
    │   └── console.py
    │
    ├── graph/
    │   ├── state.py                TravelState + initial_state()
    │   ├── constants.py            Node, ValidationRoute, ItineraryRoute,
    │   │                           ResearchAgentNode, ResearchAgentRoute
    │   ├── routers.py
    │   ├── builder.py
    │   │
    │   ├── nodes/
    │   │   ├── parsing.py
    │   │   ├── validation.py
    │   │   ├── interaction.py
    │   │   ├── aggregation.py
    │   │   ├── itinerary.py
    │   │   ├── itinerary_validation.py
    │   │   └── replanning.py
    │   │
    │   └── subgraphs/
    │       ├── __init__.py         exports the 4 *_research parent nodes
    │       ├── research_agent/     shared, reusable agent subgraph
    │       │   ├── state.py        ResearchAgentState (private messages)
    │       │   ├── spec.py         ResearchAgentSpec dataclass
    │       │   ├── nodes.py        make_agent_node, make_extract_node
    │       │   ├── routers.py      route_agent, route_after_extract
    │       │   └── builder.py      build_research_agent, make_research_node
    │       ├── flights/builder.py  FLIGHT_AGENT spec → flight_graph, flight_research
    │       ├── hotels/builder.py   HOTEL_AGENT spec → hotel_graph, hotel_research
    │       ├── weather/builder.py  WEATHER_AGENT spec → weather_graph, weather_research
    │       └── activities/builder.py ACTIVITY_AGENT spec → activity_graph, activity_research
    │
    ├── prompts/
    │   ├── planning.py
    │   ├── flight_research.py
    │   ├── hotel_research.py
    │   ├── weather_research.py
    │   ├── activity_research.py
    │   └── itinerary.py            renders research as JSON
    │
    ├── schemas/
    │   ├── requirements.py         TravelRequirements
    │   ├── flights.py              FlightResult
    │   ├── hotels.py               HotelResult
    │   ├── weather.py              WeatherReport
    │   ├── activities.py           ActivityResult
    │   └── itinerary.py            Itinerary, ItineraryDay
    │
    └── tools/                      all mock data
        ├── flights.py              search_flights       → FLIGHT_TOOLS
        ├── hotels.py               search_hotels        → HOTEL_TOOLS
        ├── weather.py              get_weather_forecast → WEATHER_TOOLS
        └── activities.py           search_activities    → ACTIVITY_TOOLS
```

The old `flights/agent.py`, `flights/nodes.py`, `flights/routers.py` and
`nodes/research.py` were removed; the factory replaces them.

### Package rules

  Adding                Location
  --------------------- -------------------------------------------
  Graph node            `app/graph/nodes/<stage>.py`
  Router                `app/graph/routers.py` or subgraph router
  Node/route constant   `app/graph/constants.py`
  New research agent    `ResearchAgentSpec` in `app/graph/subgraphs/<name>/builder.py`
  Pydantic model        `app/schemas/<concept>.py`
  Prompt                `app/prompts/<area>.py`
  Tool                  `app/tools/<area>.py`
  Setting/env var       `app/core/config.py` + `.env.example`
  User I/O              `app/core/console.py`
  Progress output       logger + `progress` state entry

Keep dependencies flowing inward:

``` text
core      → cross-cutting concerns
schemas   → pure data contracts
tools     → capabilities
prompts   → prompt text
graph     → orchestration
cli       → driver
```

------------------------------------------------------------------------

## 5. Completed LangGraph Concepts

Already learned and implemented:

-   State / `TypedDict`
-   Nodes
-   `StateGraph`
-   `START`, `END`
-   `add_node()`
-   `add_edge()`
-   `add_conditional_edges()`
-   Structured LLM output
-   Deterministic validation
-   Conditional routing
-   Cycles
-   Parallel research / fan-out
-   Fan-in synchronization
-   Reducers
-   Tools
-   `bind_tools()`
-   `ToolNode`
-   Agent tool loops
-   Tool-loop debugging
-   Structured Pydantic results
-   Subgraphs
-   Compiled subgraph used as a node
-   Production package structure
-   Itinerary generation
-   Itinerary validation
-   Controlled replanning cycle
-   Retry guard
-   Subgraph with its own private state schema
-   Invoking a subgraph from a node (explicit input/output mapping)
-   Node/subgraph factories driven by a spec
-   `add_messages` reducer
-   Fan-in with a single list edge `add_edge([a, b, c], d)`

Do not repeat these concepts unless needed for debugging.

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

    itinerary: Itinerary | None
    itinerary_errors: list[str]           # itinerary validation only
    replan_count: int

    progress: Annotated[list[str], add]   # human readable run log
```

`initial_state()` initializes **every** key (lists `[]`, `weather` /
`itinerary` / `requirements` `None`, `replan_count` 0).

There is **no `messages` key in TravelState anymore**. Agent
conversations live in each research subgraph's private
`ResearchAgentState` (see §9).

Important principles:

-   Nodes return only the fields they change. **Never `{**state}`**;
    with any reducer field (`progress`) that duplicates the list, and in
    parallel branches it causes conflicting writes. (Fixed on
    2026-09-29 in `parse_request`, `validate_requirements`, `ask_user`,
    `continue_plan`.)
-   Reducers are used only where multiple branches legitimately update a
    field (`progress`).
-   `validation_errors` and `itinerary_errors` are separate on purpose.

------------------------------------------------------------------------

## 7. Requirement Extraction + Validation

`TravelRequirements` (`app/schemas/requirements.py`): `origin`,
`destination`, `travelers`, `start_date`, `end_date`, `duration_days`
are all **`| None = None` with `Field(description=...)`**, so the model
can say "not given" as null. `budget_amount`, `budget_currency`,
`interests`, `preferences` unchanged.

Extraction uses `get_llm().with_structured_output(TravelRequirements)`
with `REQUIREMENTS_SYSTEM_PROMPT` (`app/prompts/planning.py`): only
record stated facts, null for anything missing, no placeholders, don't
infer origin from currency, derive `duration_days` from dates.

### Bug fixed 2026-09-29 (verified against Gemini)

"Plan a trip to Japan for 2 people. My budget is ₹2 lakh..." used to
pass validation: `origin` was a required `str`, so Gemini wrote
`"Unknown"` (non-empty → passed `not origin`), and nothing required a
trip length, so the itinerary agent invented 5 days and itinerary
validation (which skips the duration check when it is `None`) said VALID.
Lesson: a required schema field forces the LLM to invent a value; make
it optional and let deterministic validation decide what is mandatory.

Business validation is deterministic Python (`nodes/validation.py`):

-   requirements exist
-   origin / destination present (placeholders like "Unknown", "N/A"
    count as missing)
-   travelers present and > 0
-   trip length known: `duration_days`, or both ISO dates (then
    `_normalize` fills `duration_days` and the node writes the
    normalized `requirements` back)
-   end date not before start date; duration >= 1
-   budget, when provided, > 0

Flow:

``` text
parse_request
      ↓
validate_requirements
      ↓
 ┌────┴─────┐
VALID      INVALID
 ↓           ↓
continue   ask_user
             ↓
        parse_request
```

------------------------------------------------------------------------

## 8. Parallel Research

``` text
continue_plan
      │
 ┌────┼──────────────┬──────────────┬──────────────┐
 ↓                   ↓              ↓              ↓
flight_research  hotel_research  weather_research  activity_research
 └───────────────────┴──────────────┴──────────────┘
                     ↓
             combine_research
```

`RESEARCH_NODES` in `builder.py` is a `{node_name: node}` dict. The
fan-out is one edge per branch; the fan-in is a single
`builder.add_edge(list(RESEARCH_NODES), Node.COMBINE_RESEARCH)`, which
makes `combine_research` wait for all branches even if they take a
different number of steps.

Each branch writes only its own key and a `progress` entry.

------------------------------------------------------------------------

## 9. Research Agents (Flight / Hotel / Weather / Activity) --- DONE

All four agents share **one subgraph factory**
(`app/graph/subgraphs/research_agent/`). An agent is only a spec:

``` python
HOTEL_AGENT = ResearchAgentSpec(
    name="hotel",
    result_key="hotels",                      # TravelState key
    system_prompt=HOTEL_AGENT_SYSTEM_PROMPT,
    build_request_prompt=build_hotel_request_prompt,
    tools=HOTEL_TOOLS,
    result_type=list[HotelResult],            # validated via pydantic TypeAdapter
)                                             # empty_result defaults to list
hotel_graph = build_research_agent(HOTEL_AGENT)
hotel_research = make_research_node(HOTEL_AGENT, hotel_graph)
```

Weather uses `result_type=WeatherReport | None, empty_result=lambda: None`.

### Subgraph (private state)

``` python
class ResearchAgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    results: Any
    tool_rounds: int
```

``` text
START → agent ─┬─ tool call ──→ tools (ToolNode) → extract ─┬─ results → END
               │                                             └─ none → agent (retry)
               └─ no tool call → END
MAX_TOOL_ROUNDS = 2
```

### Parent adapter: `make_research_node`

The subgraph is **invoked from a node** (`graph.invoke(..., config)`),
not mounted directly on TravelState:

-   Input mapping: builds `[SystemMessage, HumanMessage]` from
    `requirements` and seeds the subgraph with them **once**. The old
    `if not state["messages"]: messages = _opening_messages(state)`
    check in the agent node is gone; the agent just does
    `llm.invoke(state["messages"])`.
-   Output mapping: returns only `{spec.result_key: results, "progress": [...]}`.

### Why (the bug this fixed)

Before, the flight subgraph used `TravelState`, so:

1.  its whole final state (including `requirements`,
    `validation_errors`…) was written back to the parent, and a second
    `TravelState` subgraph running in parallel would write the same
    keys in the same step → `InvalidUpdateError`;
2.  every agent would read and append to the one shared `messages`
    list and see the others' tool calls.

Now each agent's conversation is isolated and discarded after the run.

### Extract node

-   Reads only the ToolMessages after the most recent AIMessage.
-   Skips tool errors (`status == "error"`) and output that fails
    validation (logged as warnings) instead of crashing.
-   Concatenates list results when the agent made several calls.

### Optimization

The agent no longer loops back to summarise after the tool result
(nothing used that summary). It ends as soon as results are extracted,
so each agent costs **1 LLM call** and a full run costs **6 calls**
(parse + 4 agents + itinerary) instead of 10. Verified offline with a
fake LLM on 2026-09-29, including the replan path.

### Prompts

Each agent's system prompt forces exactly one tool call, passes `null`
for missing dates, and forbids follow-up questions or invented
dates/interests (the same rules that were verified with Gemini for flights).

------------------------------------------------------------------------

## 10. Itinerary Agent --- DONE

Schemas:

``` python
class ItineraryDay(BaseModel):
    day: int
    title: str
    activities: list[str]


class Itinerary(BaseModel):
    destination: str
    duration_days: int
    days: list[ItineraryDay]
```

`itinerary_agent` uses:

``` python
get_llm().with_structured_output(Itinerary)
```

It receives:

-   `TravelRequirements`
-   flights, hotels, weather, activities (rendered as JSON by
    `_to_json` in `app/prompts/itinerary.py`)
-   `itinerary_errors` when replanning

If `duration_days` is `None` the prompt asks for "a sensible length"
instead of rendering "a None-day itinerary".

Current flow:

``` text
combine_research
      ↓
itinerary_agent
      ↓
state["itinerary"] = Itinerary
```

End-to-end generation has succeeded.

------------------------------------------------------------------------

## 11. Itinerary Validation --- DONE

File:

``` text
app/graph/nodes/itinerary_validation.py
```

Validation is deterministic Python, not LLM-driven.

Current rules:

1.  itinerary exists
2.  requirements exist
3.  requested destination is contained in the itinerary destination
    (case-insensitive, so "Tokyo, Japan" passes for "Japan")
4.  duration matches requested duration
5.  number of itinerary days matches requested duration
6.  day numbers are sequential
7.  every day contains activities

Successful example:

``` text
Validating itinerary...
Itinerary validation completed: VALID
```

with:

``` python
itinerary_errors == []
```

The validator writes `itinerary_errors` (not `validation_errors`).

The validator has been run successfully against the generated 7-day
Japan itinerary.

------------------------------------------------------------------------

## 12. Replanning Cycle --- IMPLEMENTED AND BUG FIXED

The graph now supports:

``` text
itinerary_agent
      ↓
validate_itinerary
      ↓
 ┌────┴──────────┐
VALID           INVALID
 ↓                 ↓
END              replan
                   ↓
            itinerary_agent
```

`replan_count` is stored in state.

Router:

``` python
MAX_REPLAN_ATTEMPTS = 2


def route_after_itinerary_validation(state: TravelState) -> str:
    if not state["itinerary_errors"]:
        return ItineraryRoute.VALID

    if state["replan_count"] >= MAX_REPLAN_ATTEMPTS:
        return ItineraryRoute.FAILED

    return ItineraryRoute.REPLAN
```

Router unit checks were verified directly:

``` text
validation_errors=[],
replan_count=0
→ valid

validation_errors=["Wrong duration"],
replan_count=0
→ replan

validation_errors=["Wrong duration"],
replan_count=2
→ failed
```

The temporary routing issue encountered during development was fixed. Do
not assume the previous erroneous behavior is still present.

`replan_itinerary` increments the counter and sends execution back to
`itinerary_agent`.

The itinerary prompt receives `itinerary_errors`, allowing a future
replan to understand what failed.

### Important design point

Do NOT clear `itinerary_errors` inside `replan_itinerary` before the
itinerary agent sees them. (The code was clearing them until
2026-09-29; fixed, and verified offline that the second itinerary
prompt contains the previous errors.)

Correct flow:

``` text
validate
  ↓
itinerary_errors
  ↓
replan
  ↓
itinerary_agent reads previous errors
  ↓
new itinerary
  ↓
validate again
```

The validator then overwrites `itinerary_errors` with the result of the
new validation.

------------------------------------------------------------------------

## 13. Important Gemini API Note

The current Gemini integration sometimes logs:

``` text
AFC is enabled with max remote calls: 10.
Direct use of automatic function calling (AFC) in Models.generate_content is not recommended...
```

This is a provider warning, not currently a graph failure.

Gemini `gemini-2.5-flash` also returned temporary:

``` text
503 UNAVAILABLE
```

responses due to high demand; the SDK retried and requests eventually
succeeded.

During replanning testing, the project also hit:

``` text
429 RESOURCE_EXHAUSTED
```

with the free-tier request limit reported as 20 requests for the
model/project.

Therefore, avoid repeatedly running full `main.py` while debugging pure
Python graph logic. Test routers/nodes directly where possible.

------------------------------------------------------------------------

## 14. Known Issues / Deliberate Debt

1.  **CLI `input()`**
    -   `ask_user` currently blocks on stdin.
    -   Replace with `interrupt()` during the human-in-the-loop phase.
2.  **Mock travel tools**
    -   Flights, hotels, weather, activities return demo/fixed data.
    -   Replace with real APIs later; the `ResearchAgentSpec` /
        schema contracts should not need to change.
3.  **No test suite yet**
    -   Add `tests/` next to deterministic validation/routing. A fake
        LLM (object with `bind_tools()` / `with_structured_output()`)
        patched into `get_llm` in `parsing`, `itinerary` and
        `research_agent.nodes` runs the whole graph offline; this was
        used on 2026-09-29.
4.  **Gemini quota / transient errors**
    -   Do not confuse provider 503/429 responses with LangGraph bugs.
    -   Four agents now call Gemini concurrently; watch the per-minute
        free-tier limit.
    -   Production hardening later should include backoff and provider
        fallback.
5.  **Research agents are strictly one-shot**
    -   They do not use the budget to filter results yet; the itinerary
        agent receives everything. Budget checks belong in validation
        or a supervisor later.

Resolved on 2026-09-29: the shared `messages` list (now private per
agent), `{**state}` returns, replan clearing errors, and the
provider packaging/docs debt.

------------------------------------------------------------------------

## 15. Current Graph

``` text
START
  ↓
parse_request
  ↓
validate_requirements
  ├── invalid → ask_user → parse_request
  └── valid
       ↓
  continue_plan
       ↓
 ┌─────┼───────────────┬────────────────┬──────────────────┐
 ↓                     ↓                ↓                  ↓
flight_research   hotel_research   weather_research   activity_research
 (agent→tools→extract subgraph, private messages, each)
 └─────────────────────┴────────────────┴──────────────────┘
                  ↓
          combine_research
                  ↓
           itinerary_agent  ←──────────┐
                  ↓                    │
        validate_itinerary             │
             ↓       ↓                 │
          valid     invalid → replan_itinerary
             ↓
            END
```

Retry guard:

``` text
invalid + attempts available → replan
invalid + max attempts       → failed → END
```

------------------------------------------------------------------------

## 16. Current Position

``` text
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
Production code structure      ✅
Itinerary Agent                ✅
Flight tool prompt verification✅
Itinerary validation           ✅
Replanning cycle               ✅
Retry guard                    ✅
Hotel/Weather/Activity agents  ✅
Shared research agent factory  ✅
Split messages per agent       ✅

Supervisor / multi-agent       ⏭ NEXT
Human-in-the-loop              ⏭
Checkpointing                  ⏭
Long-term user memory          ⏭
Streaming                      ⏭
Tests                          ⏭
FastAPI                        ⏭
PostgreSQL / Redis             ⏭
Authentication                 ⏭
Real travel APIs               ⏭
Observability / LangSmith      ⏭
Production hardening           ⏭
```

------------------------------------------------------------------------

## 17. NEXT SESSION --- Start Here

The next implementation should be:

# Supervisor / Multi-Agent Architecture

Today the four research agents always run, in a fixed fan-out. Next,
learn the supervisor pattern:

-   A supervisor node (LLM or deterministic) decides which research
    agents are needed (e.g. skip flights if the user already booked,
    re-run hotels only when the budget check fails).
-   Dispatch with `Send` / `Command` instead of static edges.
-   Reuse the existing `*_research` nodes and `ResearchAgentSpec`; do
    not rebuild the agents.
-   Consider a budget-check step that can send work back to a specific
    agent (targeted replanning instead of regenerating everything).

Before running `main.py` against Gemini, run the whole graph offline
with a fake LLM to avoid burning the 20 requests/day free-tier quota.

Do not jump to FastAPI, databases, Redis, authentication, or real APIs
yet.

------------------------------------------------------------------------

## 18. Teaching Rules

-   Act as a senior AI Engineer mentoring a junior developer.
-   Keep theory concise; spend most time implementing.
-   Explain architectural decisions and why they matter.
-   Prefer production patterns over toy shortcuts.
-   Introduce one LangGraph concept at a time.
-   Let the user run/test after each meaningful implementation.
-   Debug actual errors instead of jumping to unrelated architecture.
-   Do not repeat concepts already successfully learned.
-   Use the Travel Planner itself to reinforce concepts.
-   Avoid premature FastAPI/database/Redis.
-   Do not dump the entire project at once.
-   Preserve working code unless there is a concrete reason to refactor.
-   Follow the package layout.
-   Keep prompts out of nodes.
-   Keep `print`/`input` out of graph code except `app/core/console.py`.
-   Add node names to `constants.py`.
-   Update this memory after every meaningful step.
