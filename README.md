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
     (back to parse_request)   ┌───────┼───────┬────────────────┐
                        flight_research  search_hotels  search_weather  search_activities
                               └───────┴───────┴────────────────┘
                                          │
                                   combine_research ──> END
```

`flight_research` is a subgraph: a tool-calling agent that invokes the
`search_flights` tool, extracts the results into `FlightResult` models, and
loops back to the agent to summarise them.

## Layout

```
app/
├── cli.py                     entrypoint: build state, run the graph, report
├── core/                      settings, logging, LLM factory, console I/O
│   ├── config.py              environment-backed Settings
│   ├── console.py             the only place that uses print/input
│   ├── llm.py                 shared ChatMistralAI instance
│   └── logging.py             logging setup
├── graph/
│   ├── builder.py             top level graph assembly
│   ├── constants.py           node and route names
│   ├── routers.py             conditional edges
│   ├── state.py               TravelState + initial_state()
│   ├── nodes/                 one module per stage of the flow
│   │   ├── parsing.py         parse_request
│   │   ├── validation.py      validate_requirements
│   │   ├── interaction.py     ask_user, continue_plan
│   │   ├── research.py        search_hotels, search_weather, search_activities
│   │   └── aggregation.py     combine_research
│   └── subgraphs/flights/     flight research subgraph
│       ├── agent.py           tool-bound agent node
│       ├── builder.py         subgraph assembly
│       ├── nodes.py           extract_flights
│       └── routers.py         tools vs. end
├── prompts/                   prompt text, kept out of the node logic
├── schemas/                   pydantic models
└── tools/                     LangChain tools available to the agents
```

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env      # then fill in MISTRAL_API_KEY
```

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `MISTRAL_API_KEY` | yes | — | Mistral credentials |
| `MISTRAL_MODEL` | no | `mistral-small-latest` | chat model to use |
| `LOG_LEVEL` | no | `INFO` | root log level |

## Run

```bash
python main.py
```

The run is interactive: if the request is missing an origin, destination,
traveller count or a sensible budget, the planner prints the problems and
waits for a correction on stdin.
