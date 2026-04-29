# AgentArchitect

**Engineering Agent Platform for Civil Engineers Specialized in Fire Safety**

AgentArchitect is a desktop application that helps civil engineering teams move beyond copy-paste prompting and adopt structured AI agents for real work. It targets a specific, high-stakes domain — **fire safety compliance review against the Romanian P118 standard** — to demonstrate that AI adoption works best when agents have defined roles, access to computational tools, and the ability to hold multi-turn conversations with domain experts.

Built during **PoliHack v.19** [App Development] under the theme *"Apps that encourage AI adoption"*.

**Team:** The Bity Ministry of Vibes & Prayers

---

## The Problem

Civil engineers already use AI. They paste floor plan data into ChatGPT, write ad-hoc prompts, and get back unstructured text that they can't verify, reuse, or build on. This "legacy prompting" approach has real limitations:

- **No tool access** — the LLM guesses distances and regulations instead of computing them.
- **No structure** — outputs are raw prose, not machine-readable data that can feed into other workflows.
- **No conversation** — asking a follow-up means resending the entire prompt from scratch.
- **No reusability** — every engineer writes their own prompts; knowledge doesn't transfer.

AgentArchitect solves this by giving engineers a platform where AI is packaged into **specialized agents** with defined inputs, outputs, constraints, and tools — turning ad-hoc prompting into a repeatable, verifiable workflow.

---

## How It Works

The platform offers two modes and a comparison view:

| Mode | What it looks like |
|------|--------------------|
| **Legacy Prompting** | Select a prompt template, paste data, get raw text back. No tools, no conversation. |
| **Agent Mode** | Select a specialized agent, provide structured inputs, get verified outputs with tool-grounded reasoning and multi-turn follow-up. |
| **Side-by-Side Comparison** | View the same task done both ways to see exactly what changes when you move from prompts to agents. |

---

## Features

### Pre-Built Fire Safety Agents

AgentArchitect ships with three specialized agents for P118 fire safety review:

- **Egress Validator** — Checks a parsed floor plan against P118 regulations and reports all violations with severity, location, and article references. Uses the P118 Validator, Pathfinding, and Structural Checker tools for real calculations.
- **Evacuation Diagnoser** — Takes violations from the Egress Validator and explains them in plain language. Ranks issues by real-world safety impact and describes what would happen in an actual fire.
- **Exit Placement Advisor** — Suggests optimal exit locations and plan modifications to resolve violations. Ranks proposals by impact-to-effort ratio and handles engineer pushback with alternatives.

Each agent has a defined scope and will redirect out-of-scope questions to the appropriate agent.

### Supported Floor Plan Formats

The platform accepts multiple input formats and converts them into a unified FloorPlan JSON schema that all tools and agents work with:

| Format | How it's parsed |
|--------|----------------|
| **DXF** | Parsed directly via `ezdxf` into exact geometry — rooms, corridors, doors, exits, and walls with real coordinates. This is the primary path for precise measurements. |
| **Images** (PNG, JPG, BMP, TIFF, GIF) | Parsed via Gemini Vision AI, which identifies rooms, corridors, doors, exits, and spatial relationships from the image. |
| **PDF** | Accepted in the file picker and handled through Gemini Vision. |
| **JSON** | Hand-authored or previously-parsed FloorPlan JSON files. Example files are included in `data/floor_plans/`. |

**Note:** DWG files are not supported — convert to DXF first using AutoCAD or a free converter like ODA File Converter.

For DXF files, the parser recognizes common AutoCAD layer naming conventions:

| Entity | Recognized layers |
|--------|------------------|
| Walls | `A-WALL`, `WALL`, `WALLS`, `S-WALL`, `AR-WALL` |
| Doors | `A-DOOR`, `DOOR`, `DOORS`, `AR-DOOR` |
| Rooms | `A-ROOM`, `ROOM`, `ROOMS`, `A-AREA`, `SPACE` |
| Corridors | `A-CORRIDOR`, `CORRIDOR`, `HALL`, `HALLWAY` |
| Windows | `A-GLAZ`, `WINDOW`, `WIN` |

Entities on unrecognized layers are classified by geometry: closed polylines become rooms or corridors (based on aspect ratio), arcs become doors, and lines become walls.

### Computational Tools (Not LLM Guessing)

Agents don't rely on the LLM to estimate distances or remember rules. They call real tools:

- **P118 Validator** — Checks travel distances, exit capacity, door widths, corridor widths, dead-end limits, exit counts, room exit requirements, and emergency lighting against P118 articles.
- **Pathfinding** — Builds a weighted graph from rooms, corridors, and doors, then runs Dijkstra's algorithm to compute actual evacuation distances.
- **Structural Checker** — Detects blocked rooms (no path to any exit), dead-end corridors, overlapping spaces, rooms with no doors, and other structural anomalies.
- **Metrics Calculator** — Aggregates violations by severity and computes a weighted compliance score with pass/fail determination.
- **Gemini Vision** — Parses floor plan images into structured spatial descriptions using AI vision.
- **DXF Parser** — Parses DXF floor plan files into structured spatial data.

### Interactive Floor Plan Canvas

A built-in 2D canvas renders floor plans with:

- Room and corridor polygons with labels and occupancy counts
- Exit markers and door arcs
- Violation markers color-coded by severity (critical, major, minor, info)
- Room tinting based on worst violation severity
- Hover tooltips showing violation details
- Click-to-highlight with animated flashing rings
- Pan, zoom, and fit-to-window controls
- Toggle layers: labels, occupancy, violations
- Dark and light theme support

### Agent Builder

Create your own agents through a visual form:

- Define name, category, and goal
- Add typed input fields (string, number, boolean, image, JSON)
- Set constraints and rules the agent must follow
- Define output schema
- Select which tools the agent can use
- Domain validation ensures agents stay within civil engineering scope
- Save & Run to immediately test your new agent

### Multi-Turn Conversation

After an agent produces its initial analysis, you can ask follow-up questions:

- Agents maintain conversation history and context across turns
- Off-topic messages are blocked with a keyword gate + LLM classifier fallback
- Agents reference prior findings and incorporate new information
- Conversation depth is capped at 10 follow-ups to keep context coherent
- Retry button for failed API calls

### Legacy-to-Agent Comparison Panel

A side-by-side view that loads the same task as both a legacy prompt template and an agent definition, with annotations explaining exactly what changed:

- Structured I/O vs raw text
- Tool access vs LLM guessing
- Conversation vs one-shot
- Scope boundaries vs unbounded prompts

### Response Caching

Built-in cache system for demo resilience:

- Caches known-good LLM responses keyed by agent ID + input hash
- Falls back to cached responses when the API is unavailable (rate limits, outages, timeouts)
- Separate cache for legacy prompt template responses
- Cache validation on startup to detect corrupted entries

---

## Setup

### Prerequisites

- Python 3.10+
- A Google Gemini API key

### Installation

1. Clone the repository:

```bash
git clone https://github.com/MogaVlad/polihack-v19-bmvp.git
cd polihack-v19-bmvp
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. **Set up your API key** — create a `.env` file in the project root:

```
GEMINI_API_KEY=your_gemini_api_key_here
```

You must provide your own Gemini API key. Get one at [Google AI Studio](https://aistudio.google.com/apikey).

4. Run the application:

```bash
python main.py
```

---

## Usage

### Running a Pre-Built Agent

1. Launch the app — the agent library is in the left sidebar.
2. Click on an agent (e.g., **Egress Validator**).
3. Provide the required input (a floor plan JSON). Example floor plans are included in `data/floor_plans/`.
4. Click **Run**. The agent will execute its tools, build a prompt with tool results, call the LLM, and parse structured outputs.
5. Review the results. The canvas will render the floor plan with violation markers.
6. Ask follow-up questions in the chat panel.

### Creating a Custom Agent

1. Press `Ctrl+N` or click **+ New Agent** in the sidebar.
2. Fill in the form: name, description/goal, system prompt, inputs, constraints, outputs, and tools.
3. Click **Save Agent** or **Save & Run**.
4. Your agent appears in the sidebar under `user_agents/`.

### Using Legacy Prompting

1. Click **Legacy Prompting** in the sidebar.
2. Select a prompt template from the dropdown.
3. Paste or load your data.
4. Click **Send to LLM** and receive raw text output.

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+N` | Create new agent |
| `Ctrl+S` | Save agent |
| `Ctrl+R` | Run agent |
| `Ctrl+E` | Export results as JSON |
| `Ctrl+B` | Toggle sidebar |
| `F5` | Refresh agent library |
| `Ctrl+Q` | Quit |

---

## Project Structure

```
.
├── main.py                  # Application entry point
├── config.py                # P118 thresholds, paths, tool config
├── requirements.txt         # Python dependencies
├── .env                     # Your Gemini API key (not committed)
│
├── engine/                  # Agent execution engine
│   ├── runner.py            # Tool execution → prompt → LLM → output parsing
│   ├── prompt_builder.py    # System prompt assembly, domain validation
│   ├── conversation.py      # Multi-turn conversation manager
│   └── cache.py             # Response caching with fallback
│
├── gui/                     # PyQt6 desktop interface
│   ├── app.py               # Main window layout and navigation
│   ├── agent_runner.py      # Agent execution panel
│   ├── agent_builder.py     # Visual agent creation form
│   ├── agent_library.py     # Sidebar agent list
│   ├── l2_console.py        # Legacy prompting panel (L2 = internal codename)
│   ├── adoption_panel.py    # Legacy vs Agent comparison
│   ├── canvas.py            # Interactive floor plan renderer
│   ├── controls.py          # Status bar and controls
│   ├── theme.py             # Dark/light stylesheet
│   └── splash.py            # Startup splash screen
│
├── llm/
│   └── gemini_client.py     # Gemini API wrapper with retries and vision
│
├── models/                  # Data models
│   ├── agent_definition.py  # Agent schema (inputs, outputs, constraints, tools)
│   ├── floor_plan.py        # Floor plan model (rooms, corridors, doors, exits)
│   ├── violations.py        # Violation, diagnosis, fix proposal, metrics models
│   └── chat.py              # Chat messages and agent results
│
├── tools/                   # Computational tools agents can call
│   ├── registry.py          # Tool registration and lookup
│   ├── p118_validator.py    # P118 fire safety regulation checks
│   ├── pathfinding.py       # Dijkstra-based evacuation pathfinding
│   ├── structural_checker.py# Blocked rooms, dead ends, anomaly detection
│   ├── metrics.py           # Violation aggregation and compliance scoring
│   └── dxf_parser.py        # DXF floor plan parsing
│
├── data/
│   ├── agents/              # Pre-built agent definitions (JSON)
│   ├── floor_plans/         # Example floor plans (office, hospital, school)
│   └── cache/               # Cached LLM responses for demo safety
│
├── user_agents/             # Custom agents you create
└── prompts/                 # Legacy prompt templates
```

---

## Tech Stack

- **Python 3** with **PyQt6** for the desktop GUI
- **Google Gemini API** (gemma-3-27b-it / gemini-2.5-flash) for LLM and vision
- **Dijkstra's algorithm** for evacuation pathfinding
- **ezdxf** for DXF floor plan parsing
- **Pillow** for image handling

---

## License

This project is licensed under the **GNU General Public License v3.0** — see the [LICENSE](LICENSE) file for details.

Copyright (c) 2026 Moga Vlad-Mihai, Matenciuc George-Sebastian, Micle Ana-Maria, Mudure Naomi-Aida [Team: The Bity Ministry of Vibes & Prayers].
