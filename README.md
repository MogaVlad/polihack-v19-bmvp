# AgentArchitect — Engineering Agent Platform

**PoliHack v19 | App Development Track**
*Team: The Bity Ministry of Vibes & Prayers*

A desktop platform where civil engineers turn domain knowledge into executable, conversational AI agents — without writing code. Built around Romanian **P118 fire safety regulations**, it demonstrates the transition from raw prompt engineering (L2) to structured agent-based development (L3).

---

## Table of Contents

- [Core Concept](#core-concept)
- [Architecture Overview](#architecture-overview)
- [Getting Started](#getting-started)
- [Pre-built Agents](#pre-built-agents)
- [Agent Pipeline](#agent-pipeline)
- [Tools](#tools)
- [The L2 to L3 Adoption Model](#the-l2-to-l3-adoption-model)
- [GUI Walkthrough](#gui-walkthrough)
- [DXF Floor Plan Support](#dxf-floor-plan-support)
- [P118 Compliance Engine](#p118-compliance-engine)
- [Response Caching & Demo Safety](#response-caching--demo-safety)
- [Data Models](#data-models)
- [Project Structure](#project-structure)
- [Testing](#testing)
- [Configuration](#configuration)

---

## Core Concept

AgentArchitect addresses a gap in how engineers interact with AI: most tools offer chat-based prompting (copy-paste data, get unstructured text back) with no reusability, no tool integration, and no structured outputs.

This platform provides a **three-level adoption path**:

| Level | Name | Description |
|-------|------|-------------|
| **L1** | Domain Code | Raw computational tools — pathfinding, P118 validation, structural checks |
| **L2** | Systematized Prompting | Versioned prompt templates with `{{DATA}}` injection, single-shot, raw text output |
| **L3** | Agent-Based Development | Structured agent definitions with tool access, JSON I/O, multi-turn conversation, and full reusability |

The same fire safety task (parsing a floor plan, checking egress compliance) is implemented at both L2 and L3, letting users see exactly what structured agents gain over raw prompting.

---

## Architecture Overview

```
                   +-----------+
                   |   GUI     |  PyQt6 desktop app
                   | (6 tabs)  |
                   +-----+-----+
                         |
          +--------------+--------------+
          |              |              |
    +-----+----+  +-----+-----+  +-----+-----+
    |  Engine  |  |    LLM    |  |   Tools   |
    | runner   |  |  gemini   |  | p118, dxf |
    | prompt   |  |  client   |  | pathfind  |
    | convo    |  +-----------+  | struct    |
    | cache    |                 | metrics   |
    +----------+                 +-----------+
          |
    +-----+-----+
    |   Models  |
    | floor_plan|
    | violations|
    | agent_def |
    | chat      |
    +-----------+
```

**Flow for running an agent:**
1. User selects agent from sidebar, provides inputs (file or JSON)
2. `AgentRunner` executes tools specified in agent definition, collects results
3. `PromptBuilder` assembles system prompt from definition + tool results
4. `GeminiClient` sends prompt to Gemini API (with retry and fallback)
5. Runner parses LLM response, extracts structured JSON outputs
6. GUI displays results; user can ask follow-up questions via `ConversationManager`

---

## Getting Started

### Prerequisites

- Python 3.8+
- A Google Gemini API key

### Installation

```bash
git clone https://github.com/<your-org>/polihack-v19-bmvp.git
cd polihack-v19-bmvp
pip install -r requirements.txt
```

### Environment Setup

Create a `.env` file in the project root:

```env
GEMINI_API_KEY=your_gemini_api_key_here
```

### Run

```bash
python main.py
```

The application launches in dark mode with all pre-built agents loaded in the sidebar.

### Dependencies

| Package | Purpose |
|---------|---------|
| `google-genai` | Gemini API integration (text, chat, vision) |
| `PyQt6` | Desktop UI framework |
| `ezdxf` | AutoCAD DXF file parsing |
| `Pillow` | Image processing for floor plan files |
| `python-dotenv` | Environment variable loading |

---

## Pre-built Agents

The platform ships with four agents that form a complete fire safety analysis pipeline:

### 1. Floor Plan Parser

| Property | Value |
|----------|-------|
| **Goal** | Convert a floor plan file (image, PDF, or DXF) into structured JSON |
| **Inputs** | `floor_plan` — file (.json, .dxf, image, or PDF) |
| **Outputs** | `parsed_plan` (JSON), `flagged_issues` (JSON) |
| **Tools** | `dxf_parser`, `gemini_vision` |
| **Conversational** | No |

Produces machine-readable JSON only — no prose, no commentary. Output is consumed directly by downstream agents. For DXF files, uses `ezdxf` for precise entity extraction. For images/PDFs, falls back to Gemini Vision API.

### 2. Egress Validator

| Property | Value |
|----------|-------|
| **Goal** | Check parsed floor plan against P118 fire safety regulations |
| **Inputs** | `parsed_plan` (JSON) |
| **Outputs** | `violations` (JSON), `compliance_summary` (text) |
| **Tools** | `p118_validator`, `pathfinding`, `structural_checker` |
| **Conversational** | Yes |

Runs 8 distinct P118 rule checks with article citations. Each violation includes severity level (critical/major/minor/info), measured value, threshold, and the specific P118 article reference. Supports multi-turn follow-up for engineers to ask about specific violations.

### 3. Evacuation Diagnoser

| Property | Value |
|----------|-------|
| **Goal** | Explain violations in plain language, rank by real-world safety impact |
| **Inputs** | `violations` (JSON), `parsed_plan` (optional JSON) |
| **Outputs** | `diagnosis` (JSON with rankings and explanations) |
| **Tools** | `metrics` |
| **Conversational** | Yes |

Translates technical code violations into plain language for non-specialists. Distinguishes between life-safety-critical issues and code-compliance paperwork. Describes what would happen in an actual fire scenario.

### 4. Exit Placement Advisor

| Property | Value |
|----------|-------|
| **Goal** | Suggest optimal exit locations to resolve violations |
| **Inputs** | `parsed_plan` (JSON), `violations` (JSON) |
| **Outputs** | `fix_proposals` (JSON), `remaining_violations` (JSON) |
| **Tools** | `pathfinding`, `p118_validator` |
| **Conversational** | Yes |

Proposes plan modifications ranked by impact-to-effort ratio. Adjusts recommendations when the engineer pushes back or provides new constraints.

---

## Agent Pipeline

Agents are chained manually by the engineer — the platform does not auto-orchestrate. This is intentional: engineers review and validate each stage before passing data forward.

```
 Floor Plan File (.dxf / .json / image)
          |
          v
 +-------------------+
 | Floor Plan Parser  |  --> parsed_plan.json
 +-------------------+
          |
          v
 +-------------------+
 |  Egress Validator  |  --> violations.json + compliance_summary
 +-------------------+
          |
     +----+----+
     v         v
 +----------+ +---------------------+
 | Evacuatn | | Exit Placement      |
 | Diagnosr | | Advisor             |
 +----------+ +---------------------+
  diagnosis    fix_proposals.json
```

**Workflow:**
1. Run Floor Plan Parser with a floor plan file → get `parsed_plan` JSON
2. Export JSON → load into Egress Validator → get `violations` JSON
3. Load violations into Evacuation Diagnoser for plain-language explanations
4. Load plan + violations into Exit Placement Advisor for fix proposals
5. At each stage, ask follow-up questions in the conversation panel

---

## Tools

Six computational tools execute deterministic analysis before the LLM sees anything. The LLM then interprets and explains tool results — it never invents measurements or violations.

### P118 Validator

Checks 8 Romanian fire safety regulations:

| Check | Rule | Article |
|-------|------|---------|
| Travel distance | Max 30m (normal), 20m (dead-end rooms) | P118 Art. 3.6.4 |
| Exit capacity | Max 80 persons per 1m exit width | P118 Art. 3.6.9 |
| Door widths | Min 0.9m (room doors), 1.2m (exit doors) | P118 Art. 3.6.6 |
| Corridor widths | Min 1.4m | P118 Art. 3.6.5 |
| Dead-end corridors | Max 12m dead-end corridor length | P118 Art. 3.6.4 |
| Exit count | Min 2 exits for occupancy > 50 | P118 Art. 3.6.2 |
| Room exit count | High-occupancy rooms (>50) need 2+ exits | P118 Art. 3.6.3 |
| Emergency lighting | Required for corridors > 10m | P118 Art. 4.5 |

Includes **borderline detection**: values within 10% of thresholds are flagged (e.g., 27m travel distance in a 30m-limit zone).

### Pathfinding

Dijkstra's algorithm on the room-corridor-exit graph. Computes shortest evacuation distance from every room to the nearest exit. Used by both the P118 validator (travel distance checks) and the Exit Placement Advisor (evaluating fix proposals).

### Structural Checker

Three sub-checks:
- **Blocked rooms** — rooms with no path to any exit (critical)
- **Dead ends** — corridors with only one connection
- **Anomalies** — overlapping polygons, zero-width corridors, unconnected geometry

### DXF Parser

Parses AutoCAD DXF files via `ezdxf`:
- LWPOLYLINE / POLYLINE → rooms and corridors
- LINE → walls
- CIRCLE / ARC → doors (detected by swing radius heuristics)
- TEXT / MTEXT → room labels
- INSERT → block references (door symbols, exit signs)
- Recognizes common AutoCAD layer conventions (`A-WALL`, `A-DOOR`, `A-CORRIDOR`, etc.)

### Metrics Calculator

Aggregates violations into a compliance report:
- Severity counts (critical, major, minor, info)
- Weighted compliance score (0-100): critical = -25, major = -10, minor = -3, info = -1
- Pass/fail determination (FAIL if any critical or major violations)

### Gemini Vision

Calls Gemini 2.5 Flash Vision API to parse floor plan images and PDFs when no structured data (DXF/JSON) is available. Used as fallback by the Floor Plan Parser agent.

---

## The L2 to L3 Adoption Model

The platform explicitly demonstrates what structured agents gain over raw prompting.

### L2: Systematized Prompting

Located in `prompts/` — four versioned markdown templates (`v1_parse_floor_plan.md`, `v1_check_egress.md`, etc.) with `{{DATA}}` placeholders. The **L2 Console** tab lets users:

1. Select a prompt template from dropdown
2. Paste floor plan data into text area
3. Send to LLM → get raw text response

**Limitations:** No tool access (LLM must guess measurements), no structured output (must read prose), no conversation (single-shot), no reusability (copy-paste each time).

### L3: Agent-Based Development

Located in `data/agents/` — four JSON agent definitions with explicit inputs, outputs, constraints, tool bindings, and conversation guidelines. The **Agent Runner** tab provides:

1. Typed input fields generated from agent definition
2. Tool execution before LLM call (grounded, factual analysis)
3. Structured JSON outputs (machine-parseable, exportable)
4. Multi-turn conversation with scope boundaries
5. Reusability — same agent, different floor plans, same quality

### Adoption Panel

The **Adoption Panel** tab shows L2 and L3 side by side for each agent. Left column: the raw prompt template. Right column: the structured agent definition. Annotations highlight what changed — tool access, structured I/O, constraints, conversation support, and reusability.

---

## GUI Walkthrough

The application is a PyQt6 desktop app with dark theme, organized into a sidebar + tabbed workspace + canvas.

### Sidebar: Agent Library

- Lists all agents from `data/agents/` and `user_agents/`, grouped by category
- Search/filter bar for quick lookup
- Click an agent to load it in the Runner tab
- `[+ Create New Agent]` button opens the Builder tab

### Tab 1: Agent Runner

The primary workspace for running agents and viewing results.

**Sections:**
- **Agent header** — name, goal, and `[View Definition]` button (opens raw JSON)
- **Inputs** — dynamically generated from agent definition: file pickers for `file` type, text areas for `json` type, `[Browse...]` buttons
- **Status bar** — real-time progress: "Running tools...", "Assembling prompt...", "Calling LLM...", "Done"
- **Outputs** — structured JSON display with `[Export JSON]` and `[Show on Canvas]` buttons
- **Conversation panel** — chat area with severity-colored text (critical=red, major=orange, minor=yellow), follow-up input, `[Send]`, `[Clear Chat]`, `[Retry]` buttons

All LLM calls run in background threads — the UI never freezes.

### Tab 2: Agent Builder

A no-code form for creating custom agents:

- **Name** and **Goal** fields
- **Inputs** — dynamic list with `[+ Add Input]`, each row has name, type (file/json/text), description
- **Constraints** — dynamic list of text fields
- **Outputs** — dynamic list with name, type, description
- **Tools** — checkboxes for all registered tools (P118 validator, pathfinding, etc.)
- **Conversational** — toggle for multi-turn follow-up support
- **`[Save Agent]`** — validates form (required fields + domain relevance check), saves to `user_agents/`
- **`[Save & Run]`** — save then immediately load in Runner tab

**Domain validation:** The builder rejects agents unrelated to civil engineering. Regex-based keyword matching checks for engineering terms and blocks off-topic agents (recipes, movies, crypto, etc.).

### Tab 3: L2 Console

Single-shot prompt mode for demonstrating L2 workflow:

- Prompt template dropdown (reads from `prompts/`)
- `[View Template]` button to inspect the raw markdown
- Data input area with `[Load File]` button
- `[Send to LLM]` button → raw text response
- Banner: *"This is L2: versioned prompts, manual data flow, raw text output."*

### Tab 4: Adoption Panel

Side-by-side L2 vs L3 comparison:

- Dropdown to switch between the four agent pairs
- Left column: L2 prompt template (markdown)
- Right column: L3 agent definition (JSON)
- Annotations highlighting structural differences

### Canvas Panel

Toggleable floor plan visualization at the bottom of the workspace:

- **Rendering:** Room polygons with labels, walls, door arcs, exit arrows, corridor paths
- **Violation overlays:** Colored markers at violation locations (severity-coded)
- **Interactions:** Zoom (mouse wheel), pan (click-drag), fit-to-window (auto-scale)
- **Layer toggles:** Show/hide rooms, walls, doors, exits, violations independently
- Click a violation marker for tooltip with rule reference

---

## DXF Floor Plan Support

The platform handles real AutoCAD DXF files, not just pre-structured JSON.

### Entity Extraction

The `dxf_parser` tool reads DXF entities and maps them to floor plan components:

| DXF Entity | Floor Plan Component |
|------------|---------------------|
| LWPOLYLINE / POLYLINE | Rooms, corridors (classified by aspect ratio + layer) |
| LINE | Walls |
| CIRCLE / ARC | Doors (detected by swing radius heuristics) |
| TEXT / MTEXT | Room labels and annotations |
| INSERT | Block references (door symbols, exit signs) |
| HATCH | Boundary paths |
| SPLINE | Flattened to polyline approximation |

### Classification Logic

- **Room type** determined by: layer name keywords, aspect ratio, and label text matching
- **Occupancy** estimated via P118 density tables (office=10 m²/person, conference=2 m²/person, corridor=exempt, etc.)
- **Door connectivity** via nearest-neighbor matching between door positions and adjacent rooms
- **Layer recognition** for common AutoCAD conventions: `A-WALL`, `A-DOOR`, `A-CORRIDOR`, `A-ROOM`, etc.

### Flagged Issues

The parser flags ambiguities during extraction:
- Unclosed polylines (incomplete room boundaries)
- Missing door-to-room connections
- Overlapping room geometries
- Unmatched text labels
- Unusual shapes that may be misclassified

A standalone conversion script is also available:

```bash
python scripts/dxf_to_json.py input.dxf output.json
```

---

## P118 Compliance Engine

The P118 validation system implements Romanian fire safety regulation **Normativ P118** with full article citations.

### Configurable Thresholds

All P118 thresholds are centralized in `config.py`:

```python
P118_MAX_TRAVEL_DISTANCE = 30.0          # meters (normal rooms)
P118_MAX_DEAD_END_TRAVEL = 20.0          # meters (dead-end rooms)
P118_MAX_DEAD_END_CORRIDOR = 12.0        # meters
P118_MIN_DOOR_WIDTH_ROOM = 0.9           # meters
P118_MIN_DOOR_WIDTH_EXIT = 1.2           # meters
P118_MIN_CORRIDOR_WIDTH = 1.4            # meters
P118_EXIT_CAPACITY_PER_METER = 80        # persons per meter of exit width
P118_MIN_EXITS_THRESHOLD_OCCUPANCY = 50  # occupancy triggering 2-exit rule
P118_BORDERLINE_TOLERANCE = 0.10         # 10% borderline detection band
```

### Violation Severity Levels

| Severity | Meaning | Compliance Score Impact |
|----------|---------|------------------------|
| `critical` | Immediate life safety risk (blocked rooms, no exits) | -25 |
| `major` | Significant code violation (excessive travel distance, narrow exits) | -10 |
| `minor` | Below threshold but close to borderline | -3 |
| `info` | Observation, no regulation breach | -1 |

### Borderline Detection

Values within 10% of a threshold are flagged even if they technically pass. A 27m travel distance in a 30m-limit zone passes the check but gets an `info` severity flag — it's close enough to warrant engineer attention.

### Compliance Score

The metrics tool computes a weighted score from 0 to 100:

- Start at 100
- Subtract penalties per violation by severity
- **PASS:** No critical or major violations
- **FAIL:** Any critical or major violation present

---

## Response Caching & Demo Safety

Every pre-built agent + example floor plan combination has a pre-computed cached response stored in `data/cache/`.

### How It Works

1. When an agent runs, inputs are hashed: `MD5(sorted_input_values)`
2. Cache key: `{agent_id}_{hash}.json`
3. **Fallback chain:** Try Gemini API → on failure, load cached response → on cache miss, show error
4. Cached responses include full `AgentResult`: outputs, explanation, and tool results

### L2 Cache

Separate cache at `data/cache/l2/` for L2 template responses, keyed by `{template_name}_{MD5(data)}`.

### Follow-up Caching

Cached agent results can include pre-stored follow-up Q&A pairs. The conversation manager performs fuzzy matching on user questions to find relevant cached follow-ups when the API is unavailable.

This ensures the platform works reliably during live demos even with API rate limits or network issues.

---

## Data Models

All data structures are Python dataclasses with `to_dict()` / `from_dict()` serialization.

### FloorPlan (`models/floor_plan.py`)

```
FloorPlan
├── id, name, floor
├── rooms: List[Room]         # id, name, type, polygon, area, occupancy
├── corridors: List[Corridor] # id, name, width, length, connects
├── doors: List[Door]         # id, connects, width, position, is_exit
├── exits: List[Exit]         # id, room_id, position, width, leads_outside
└── walls: List[Wall]         # id, start, end, room_id
```

### Violations (`models/violations.py`)

```
Violation           # id, rule, article, severity, location, description, measured/threshold
DiagnosisResult     # violation_id, explanation, impact, severity_rank, affected_occupants
FixProposal         # id, target_violation, description, justification, effort, impact_score
MetricsReport       # total_violations, severity counts, compliance_score, pass_fail
```

### Agent Definition (`models/agent_definition.py`)

```
AgentDefinition
├── id, name, category, goal
├── inputs: List[AgentInput]        # name, type, description
├── constraints: List[str]
├── outputs: List[AgentOutput]      # name, type, description
├── tools: List[str]
├── conversational: bool
└── conversation_guidelines: str
```

### Chat (`models/chat.py`)

```
ChatMessage    # role ("user" / "agent"), content, timestamp
AgentResult    # agent_id, success, outputs, explanation, tool_results, error
```

---

## Project Structure

```
polihack-v19-bmvp/
├── main.py                     # Application entry point
├── config.py                   # P118 thresholds, API keys, tool config
├── requirements.txt            # Python dependencies
├── .env                        # GEMINI_API_KEY
│
├── models/                     # Data schemas (dataclasses)
│   ├── agent_definition.py
│   ├── floor_plan.py
│   ├── violations.py
│   └── chat.py
│
├── engine/                     # Agent execution pipeline
│   ├── runner.py               # Tool execution → prompt → LLM → output parsing
│   ├── prompt_builder.py       # System/user prompt assembly + domain validation
│   ├── conversation.py         # Multi-turn chat with scope enforcement
│   └── cache.py                # Response caching with hash-based lookup
│
├── tools/                      # Deterministic analysis tools
│   ├── registry.py             # Singleton tool registry
│   ├── p118_validator.py       # 8 P118 compliance checks
│   ├── pathfinding.py          # Dijkstra evacuation paths
│   ├── structural_checker.py   # Blocked rooms, dead ends, anomalies
│   ├── metrics.py              # Compliance scoring
│   └── dxf_parser.py           # AutoCAD DXF → FloorPlan JSON
│
├── llm/                        # LLM integration
│   └── gemini_client.py        # Gemini API: text, chat, vision, retry logic
│
├── gui/                        # PyQt6 desktop UI
│   ├── app.py                  # Main window layout
│   ├── agent_library.py        # Sidebar: browse/search agents
│   ├── agent_runner.py         # Run agents, view outputs, conversation
│   ├── agent_builder.py        # No-code agent creation form
│   ├── canvas.py               # Floor plan visualization
│   ├── l2_console.py           # L2 single-shot prompt console
│   ├── adoption_panel.py       # L2 vs L3 side-by-side comparison
│   ├── controls.py             # Status bar + theme toggle
│   ├── theme.py                # Dark mode stylesheet
│   └── splash.py               # Loading overlay
│
├── prompts/                    # L2 prompt templates (markdown + {{DATA}})
│   ├── v1_parse_floor_plan.md
│   ├── v1_check_egress.md
│   ├── v1_diagnose_issues.md
│   └── v1_propose_fixes.md
│
├── data/
│   ├── agents/                 # Pre-built agent definitions (JSON)
│   ├── cache/                  # Cached LLM responses for demo safety
│   └── floor_plans/            # Example floor plans (.json, .dxf)
│
├── scripts/
│   ├── dxf_to_json.py          # Standalone DXF → JSON converter
│   └── generate_borderline_caches.py
│
├── tests/                      # Unit + integration tests
│   ├── test_tools.py
│   ├── test_models.py
│   ├── test_engine.py
│   └── test_cross_agent.py
│
└── user_agents/                # User-created agents (runtime)
```

---

## Testing

```bash
python -m pytest tests/ -v
```

### Test Coverage

| Module | Tests |
|--------|-------|
| `test_tools.py` | Tool registry, pathfinding (reachable + blocked rooms), P118 validation (pass + violation cases), structural checks, metrics scoring |
| `test_models.py` | Dataclass serialization round-trips (to_dict / from_dict / JSON) |
| `test_engine.py` | Agent runner execution, prompt building, cache fallback behavior |
| `test_cross_agent.py` | Full pipeline: Parser → Validator → Diagnoser → Advisor |

---

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | Yes | Google Gemini API key for LLM calls |

### LLM Models

Configured in `llm/gemini_client.py`:

| Task | Model |
|------|-------|
| Text / Chat | `gemma-3-27b-it` |
| Vision (image parsing) | `gemini-2.5-flash` |

### Example Floor Plans

Four example floor plans in `data/floor_plans/`:

| File | Description |
|------|-------------|
| `example_office.json` | Standard office building — should pass most P118 checks |
| `example_hospital.json` | Hospital layout with complex corridors |
| `example_school.json` | School building with high occupancy rooms |
| `example_borderline.json` | Deliberately near P118 thresholds — triggers borderline warnings |
| `building001-0_floor1.dxf` | Real AutoCAD DXF file for DXF parser testing |
