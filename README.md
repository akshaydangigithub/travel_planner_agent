# Travel Planner

A LangGraph agent that turns a free-form travel request into an itinerary.
It extracts structured requirements with an LLM, validates them (asking the
user for corrections when something is missing), then researches flights,
hotels, weather and activities in parallel before combining the results.

## Flow

```
START
  └─ parse_request ──> validate_requirements
                          │
              ┌───────────┴───────────┐
         ask_user                continue_plan
              │                        │
     (back to parse_request)   ┌───────┼────────┬─────────────┐
                        flight_research  hotel_research  weather_research  activity_research
                               └───────┴────────┴─────────────┘
                                          │
                                   combine_research
                                          │
                                   itinerary_agent ──> validate_itinerary ──> END
                                          ↑                    │ invalid
                                          └── replan_itinerary ┘ (max 2 attempts)
```

Each `*_research` node runs its own tool-calling subgraph, built from one
shared factory (`app/graph/subgraphs/research_agent/`) and a small
per-agent `ResearchAgentSpec`. Each subgraph keeps a private message history,
and only its typed result (`flights`, `hotels`, `weather`, `activities`)
is written back to `TravelState`.

## Layout

```
app/
├── cli.py                     entrypoint: build state, run the graph, report
├── core/                      settings, logging, LLM factory, console I/O
├── graph/
│   ├── builder.py             top level graph assembly
│   ├── constants.py           node and route names
│   ├── routers.py             conditional edges
│   ├── state.py               TravelState + initial_state()
│   ├── nodes/                 one module per stage of the flow
│   └── subgraphs/
│       ├── research_agent/    shared agent → tools → extract subgraph
│       ├── flights/           flight agent spec
│       ├── hotels/            hotel agent spec
│       ├── weather/           weather agent spec
│       └── activities/        activity agent spec
├── prompts/                   prompt text, kept out of the node logic
├── schemas/                   pydantic models
└── tools/                     LangChain tools available to the agents (mock data)
```

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env      # then fill in GOOGLE_GENAI_API_KEY
```

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `GOOGLE_GENAI_API_KEY` | yes | — | Gemini credentials (active provider) |
| `GOOGLE_GENAI_MODEL` | no | `gemini-2.5-flash` | chat model to use |
| `MISTRAL_API_KEY` | no | — | Mistral credentials (not currently used) |
| `MISTRAL_MODEL` | no | `mistral-small-latest` | Mistral chat model |
| `LOG_LEVEL` | no | `INFO` | root log level |

## Run

```bash
python main.py
```

The run is interactive: if the request is missing an origin, destination,
traveller count or a sensible budget, the planner prints the problems and
waits for a correction on stdin.
