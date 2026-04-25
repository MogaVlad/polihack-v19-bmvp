# Roadmap: 24-Hour Hackathon — Engineering Agent Platform

> **Stack**: Python + Tkinter · Gemini API (free tier) · Domain tools (pathfinding, P118 validator)
> **Team**: 4 developers · **Goal**: Working desktop platform + 90-second demo
> **AI Adoption Level**: L3 — Agent-based development (agents as structured objects, not prompts)
> **Hackathon Theme**: Build a solution that helps engineers progress from L2 to L3

---

## The Product

**"A platform where engineers turn domain knowledge into executable, conversational AI agents."**

Engineers don't write prompts. They define agents through a structured form:
- **Goal**: What the agent does
- **Inputs**: What it needs (files, JSON, parameters)
- **Constraints**: Domain rules the agent must respect
- **Outputs**: What it produces (structured data, reports, suggestions)
- **Tools**: Which computational tools it can use (pathfinding, P118 validator, structural checker)

The platform turns that definition into a runnable, conversational agent with structured I/O, tool access, explainable results, and multi-turn follow-up.

**Fire safety is the first vertical.** The app ships with 4 pre-built agents for fire evacuation analysis. Engineers can also create their own agents from scratch.

### Two core workflows

1. **Use an agent**: Browse the Agent Library → select an agent → provide inputs → run → get structured output → ask follow-up questions → export results
2. **Create an agent**: Open Agent Builder → fill in goal, inputs, constraints, outputs, tools → save → agent appears in the library → run it immediately

### Why this is L3, not L2 or L4

| Level | What it looks like | Our platform |
|-------|-------------------|--------------|
| **L2** (Systematized Prompting) | Versioned prompt templates in the repo, engineer copy-pastes data, gets raw text back | We SHOW this in a "Prompt Console" tab to contrast with L3 |
| **L3** (Agent-Based Development) | Repo contains agents as structured objects with definitions, tools, and conversational behavior | **This is us.** Agent definitions in `data/agents/`, tool registry, structured I/O, conversation |
| **L4** (Orchestrated Workflows) | Agents coordinated via DAGs, automatic pipelines, agent-to-agent communication | **We avoid this.** No orchestrator, no pipelines, engineer controls everything |

### How we showcase the L2 → L3 transition

The app has a dedicated "L2 vs L3" tab that shows:
- **Left column**: A versioned prompt template (L2 artifact from `prompts/`)
- **Right column**: The corresponding agent definition (L3 artifact from `data/agents/`)
- **Annotations**: What changed — structured I/O, tool access, constraints, conversational behavior, reusability

During the demo, we show both the L2 Prompt Console and the L3 Agent Runner side by side. Same task, same LLM, but fundamentally different workflow. That's adoption.

---

## Team Roles

| Person | Codename | Owns |
|--------|----------|------|
| **A** | **Platform UI** | Main window shell, navigation, agent library sidebar, canvas renderer, L2 prompt console |
| **B** | **Agent Engine** | Gemini API wrapper, agent execution engine, conversational layer, prompt assembly from definitions |
| **C** | **Tools** | Tool registry, P118 validator, pathfinding, structural checker, metrics, domain logic |
| **D** | **Builder + Runner** | Agent Builder form, Agent Runner UI, agent schema/models, data files, adoption showcase panel |

---

## Architecture

### Main Window Layout

```
+------------------------------------------------------------------+
|  Engineering Agent Platform              [Settings] [Theme]       |
+------------------------------------------------------------------+
|          |                                                        |
|  AGENT   |  [Agent Library] [Agent Builder] [L2 Console] [L2vsL3]|
|  LIBRARY |  +--------------------------------------------------+ |
|  (sidebar)|  |                                                  | |
|          |  |          ACTIVE TAB CONTENT                       | |
|  [Search]|  |                                                  | |
|          |  |  (Agent Runner / Builder / Console / Showcase)    | |
|  Fire    |  |                                                  | |
|  Safety  |  |                                                  | |
|   > Plan |  |                                                  | |
|     Parse|  |                                                  | |
|   > Egres|  |                                                  | |
|   > Diag |  |                                                  | |
|   > Exit |  |                                                  | |
|     Advis|  |                                                  | |
|          |  |                                                  | |
|  Custom  |  +--------------------------------------------------+ |
|   > ...  |  |        CANVAS (toggleable, bottom panel)         | |
|          |  |        Floor plan + violation overlays            | |
| [+Create]|  +--------------------------------------------------+ |
+------------------------------------------------------------------+
|  Status: Ready | Agents: 4 loaded | Tools: 3 available           |
+------------------------------------------------------------------+
```

### Agent Library (Sidebar)

- Lists all available agents (pre-built + user-created)
- Grouped by category (e.g., "Fire Safety", "Custom")
- Each entry shows: name, one-line goal, status icon
- Search/filter bar at top
- "[+ Create New Agent]" button at bottom
- Click an agent → opens it in the Agent Runner tab
- Right-click → "Edit Definition", "Duplicate", "Delete"

### Agent Runner (Main Tab — when running an agent)

```
+---------------------------------------------------+
| Agent: Floor Plan Parser                    [Def]  |
| Goal: Parse a floor plan image into structured     |
|       room/corridor/exit data                      |
+---------------------------------------------------+
| INPUTS                 | OUTPUTS                   |
| Floor plan: [Browse..] | Status: Done              |
|                        | +--- Structured Output --+|
|       [Run Agent]      | | {rooms: 12, exits: 3,  ||
|                        | |  corridors: 4, ...}     ||
|                        | +------------------------+|
|                        | [Export JSON] [To Canvas]  |
+---------------------------------------------------+
| CONVERSATION                                       |
| Agent: Parsed 12 rooms. Room R5 has an unusual     |
|        L-shape — is this intentional?              |
| You: Yes, it's an L-shaped conference room.        |
| Agent: Understood. I've kept R5 as a single room   |
|        with the L-polygon. Occupancy estimate: 25. |
| [Type follow-up question...              ] [Send]  |
+---------------------------------------------------+
| CONSTRAINTS USED           | TOOLS USED             |
| - P118 room classification | - Gemini Vision API    |
| - Min polygon area 4m^2    |                        |
+---------------------------------------------------+
```

### Agent Builder (Main Tab — when creating/editing an agent)

```
+---------------------------------------------------+
| CREATE NEW AGENT                                   |
+---------------------------------------------------+
| Name:  [___________________________]               |
| Goal:  [___________________________]               |
|        [___________________________]               |
+---------------------------------------------------+
| INPUTS                                             |
| [+ Add Input]                                      |
| 1. Name: [floor_plan] Type: [JSON v] Desc: [...]  |
| 2. Name: [risk_zones] Type: [JSON v] Desc: [...]  |
+---------------------------------------------------+
| CONSTRAINTS                                        |
| [+ Add Constraint]                                 |
| 1. [Max 30m travel distance to nearest exit   ]    |
| 2. [At least 2 exits per floor                ]    |
+---------------------------------------------------+
| OUTPUTS                                            |
| [+ Add Output]                                     |
| 1. Name: [exit_suggestions] Type: [JSON v]         |
| 2. Name: [compliance_note] Type: [Text v]          |
+---------------------------------------------------+
| TOOLS                                              |
| [x] P118 Validator   [ ] Pathfinding               |
| [x] Structural Check [ ] Metrics Calculator        |
+---------------------------------------------------+
| Conversational: [x] Enable follow-up conversation  |
+---------------------------------------------------+
|          [Save Agent]  [Save & Run]                |
+---------------------------------------------------+
```

### L2 Prompt Console (Tab — for transition showcase)

Simple interface representing L2 (Systematized Prompting):
- Prompt template dropdown (reads from `prompts/`)
- "View Template" button showing the raw `.md` file
- Data input text area (paste or load file)
- "Send to LLM" button
- Raw text response area (unstructured, no follow-up, no export)
- Banner: *"This is L2: versioned prompts, manual data flow, raw text output. Switch to the Agent Library to see L3."*

### L2 vs L3 Showcase (Tab — for judges)

Side-by-side comparison:
- Left: L2 prompt template (from `prompts/`)
- Right: Corresponding L3 agent definition (from `data/agents/`)
- Dropdown to switch between the 4 agent pairs
- Annotations highlighting what changed: structured I/O, tool access, constraints, conversational behavior
- Summary: "Same task. L2 = copy-paste + raw text. L3 = structured agents with tools and conversation."

### Canvas (Toggleable Bottom Panel)

- Renders parsed floor plans: rooms, walls, doors, exits, corridors
- Overlay layers: violation markers (red/yellow), room labels, occupancy numbers
- Zoom, pan, fit-to-window
- Any agent can push output to the canvas via "Show on Canvas" button
- Clickable violation markers linked to agent conversation

---

## Agent Definition Schema

Agents are stored as JSON files in `data/agents/` (pre-built) or `user_agents/` (user-created):

```json
{
  "id": "floor_plan_parser",
  "name": "Floor Plan Parser",
  "category": "Fire Safety",
  "goal": "Parse a floor plan image into structured room, corridor, and exit data",
  "inputs": [
    {"name": "floor_plan", "type": "image", "description": "Floor plan image or PDF"}
  ],
  "constraints": [
    "Identify all rooms, corridors, doors, exits, and stairs",
    "Classify rooms by type (office, corridor, stairwell, etc.)",
    "Estimate occupancy based on room type and area",
    "Flag ambiguous or unusual features for engineer review"
  ],
  "outputs": [
    {"name": "parsed_plan", "type": "json", "description": "Structured floor plan matching the platform schema"},
    {"name": "flagged_issues", "type": "json", "description": "List of ambiguities or unusual features found"}
  ],
  "tools": ["gemini_vision"],
  "conversational": true,
  "conversation_guidelines": "After parsing, proactively flag unusual features. Answer questions about the parse. Stay within scope — redirect validation questions to the Egress Validator agent."
}
```

### Pre-built Fire Safety Agents

| Agent | Goal | Inputs | Outputs | Tools |
|-------|------|--------|---------|-------|
| **Floor Plan Parser** | Parse image → structured data | Floor plan image | Parsed JSON + flagged issues | Gemini Vision |
| **Egress Validator** | Check P118 compliance | Parsed floor plan JSON | Violation list with severities | P118 Validator, Pathfinding |
| **Evacuation Diagnoser** | Explain violations in plain language | Violations JSON | Ranked diagnosis + impact analysis | Gemini Text |
| **Exit Placement Advisor** | Suggest optimal exit locations | Floor plan + violations JSON | Ranked fix proposals + justification | Pathfinding, P118 Validator |

---

## Project Structure

```
polihack-v19-bmvp/
├── main.py                       # Entry point — launches the platform
├── requirements.txt              # google-generativeai, Pillow, python-dotenv
├── config.py                     # API keys, P118 thresholds, tool config
├── models/
│   ├── __init__.py
│   ├── agent_definition.py       # AgentDefinition, AgentInput, AgentOutput, AgentConstraint
│   ├── floor_plan.py             # FloorPlan, Room, Wall, Door, Exit, Corridor dataclasses
│   ├── violations.py             # Violation, DiagnosisResult, FixProposal dataclasses
│   └── chat.py                   # ChatMessage dataclass (role, content, timestamp)
├── gui/
│   ├── __init__.py
│   ├── app.py                    # Main window: sidebar + tabbed content area + canvas
│   ├── agent_library.py          # Sidebar: browse, search, select agents
│   ├── agent_builder.py          # Tab: create/edit agent definition form
│   ├── agent_runner.py           # Tab: run agent, show I/O, conversation panel
│   ├── canvas.py                 # Floor plan rendering + overlays (toggleable panel)
│   ├── l2_console.py             # Tab: L2 prompt console (transition showcase)
│   ├── adoption_panel.py         # Tab: L2 vs L3 side-by-side comparison
│   └── controls.py               # Status bar, theme toggle, global controls
├── engine/
│   ├── __init__.py
│   ├── runner.py                 # Agent execution: load definition → assemble prompt → call LLM → parse output
│   ├── prompt_builder.py         # Build LLM prompt from agent definition + inputs + constraints
│   └── conversation.py           # Multi-turn conversation manager per agent session
├── tools/
│   ├── __init__.py
│   ├── registry.py               # Tool registry: maps tool names → implementations
│   ├── pathfinding.py            # BFS/Dijkstra shortest path to exit
│   ├── p118_validator.py         # Romanian P118 rule checks (travel distance, exits, doors, corridors)
│   ├── structural_checker.py     # Blocked rooms, dead ends, inaccessible areas, anomalies
│   └── metrics.py                # Violation counts, severities, compliance scoring
├── llm/
│   ├── __init__.py
│   └── gemini_client.py          # Gemini API wrapper (vision + text + chat, retries, rate limit)
├── prompts/                      # L2 artifacts — versioned prompt templates (transition showcase)
│   ├── v1_parse_floor_plan.md
│   ├── v1_check_egress.md
│   ├── v1_diagnose_issues.md
│   └── v1_propose_fixes.md
├── data/
│   ├── floor_plans/              # Example floor plans
│   │   ├── example_office.json
│   │   ├── example_school.json
│   │   └── example_hospital.json
│   └── agents/                   # Pre-built agent definitions (L3 artifacts)
│       ├── floor_plan_parser.json
│       ├── egress_validator.json
│       ├── evacuation_diagnoser.json
│       └── exit_placement_advisor.json
├── user_agents/                  # User-created agent definitions (saved here at runtime)
│   └── .gitkeep
└── tests/
    ├── test_tools.py             # Unit tests for P118 rules, pathfinding
    └── test_models.py            # Unit tests for schema parsing
```

### Key structural differences from "just a fire safety app"

| Element | Fire Safety App | Agent Platform |
|---------|----------------|----------------|
| `agents/` | Hardcoded agent classes | Gone — replaced by `engine/` + JSON definitions |
| `engine/` | N/A | Generic agent runner that executes ANY definition |
| `tools/` | N/A | Pluggable tool registry — agents SELECT which tools to use |
| `data/agents/` | Agent `.md` files | Agent `.json` definitions with full schema |
| `user_agents/` | N/A | User-created agents saved at runtime |
| `gui/agent_builder.py` | N/A | Form to create new agents |
| `gui/agent_runner.py` | N/A | Generic runner for any agent |

---

## PHASE 0 — Foundation (Hours 0–2) · ALL TOGETHER

**Everyone in the same room. No solo work until the shared contracts are locked.**

### Hour 0–1: Schemas & Contracts

- **ALL**: Define and agree on:
  1. **Agent Definition schema** (JSON) — the structure every agent follows (goal, inputs, constraints, outputs, tools, conversational flag)
  2. **Floor Plan schema** (JSON) — rooms, walls, doors, exits, corridors (the data agents work with)
  3. **Violation schema** — severity, location, rule, description
  4. **ChatMessage schema** — role (user/agent), content, timestamp
- **D**: Write `models/agent_definition.py` — `AgentDefinition`, `AgentInput`, `AgentOutput` dataclasses with `load_from_json()` and `save_to_json()` methods
- **D**: Write `models/floor_plan.py`, `models/violations.py`, `models/chat.py` dataclasses
- **ALL**: Review and agree — these are the function signatures everyone codes against

### Hour 1–2: Project Setup

- **B**: Get Gemini API key via Google AI Studio. Share via `.env` (gitignored). Write `llm/gemini_client.py` skeleton
- **A**: Create project structure (all folders, `__init__.py` files, `main.py` skeleton with sidebar + tabs). Write `requirements.txt`
- **C**: Define tool function signatures in `tools/` (stubs returning empty results). Write P118 constants in `config.py`
- **D**: Write 2 pre-built agent definition JSON files in `data/agents/` (Floor Plan Parser + Egress Validator)
- **B**: Write the 4 L2 prompt templates in `prompts/` — versioned `.md` files with instructions + `{{DATA}}` placeholders
- **ALL**: `pip install -r requirements.txt`, verify imports, agree on git workflow

**EXIT GATE**: `python main.py` shows a window with sidebar + 4 tabs. Agent definition JSON files loadable. All stubs importable.

---

## PHASE 1 — Core Build (Hours 2–8) · FULL PARALLEL

No cross-dependencies. Everyone works against the agreed schemas.

### Person A — Platform Shell + Canvas + L2 Console

| Hour | Deliverable |
|------|-------------|
| 2–3 | Main window: left sidebar (`agent_library.py` skeleton — list of agent names loaded from `data/agents/` + `user_agents/`), center area with `ttk.Notebook` (4 tabs: Agent Runner, Agent Builder, L2 Console, L2 vs L3). Status bar at bottom. |
| 3–4 | Agent Library sidebar: load agent definitions from JSON files, display as clickable list items grouped by category. Search bar filters by name/goal. "[+ Create New Agent]" button at bottom switches to Builder tab. Click agent → switches to Runner tab with that agent loaded. |
| 4–5 | Canvas component (`canvas.py`): render floor plan from JSON — room polygons, walls, doors, exits. Zoom (mouse wheel), pan (click-drag), fit-to-window. Canvas is a toggleable bottom panel in the main window. |
| 5–6 | Canvas overlays: toggleable violation markers (red/yellow circles), room labels, occupancy numbers. Checkboxes for layer visibility. Click violation marker → tooltip with details. |
| 6–7 | L2 Console tab (`l2_console.py`): prompt template dropdown (reads filenames from `prompts/`), "View Template" button (opens `.md` in `Toplevel`), data input text area, "Load File" button, "Send to LLM" button, raw response text area. Banner explaining L2. |
| 7–8 | Global controls: status bar ("Ready" / "Running agent..." / "4 violations found"), theme toggle, example floor plan dropdown in the canvas panel. Window title, icon, resize handling. |

**Test with**: Hardcoded agent list in sidebar. Canvas renders a hardcoded floor plan. L2 console UI complete.

### Person B — LLM Client + Agent Engine + Conversation

| Hour | Deliverable |
|------|-------------|
| 2–3 | `llm/gemini_client.py`: Gemini API wrapper. Methods: `send_prompt(prompt_text) -> str` (for L2 mode), `send_with_context(system_prompt, user_message, history) -> str` (for L3 agent conversations), `parse_image(image_path, prompt) -> str` (for vision). API key from env, retries on rate limit. |
| 3–4 | `engine/prompt_builder.py`: Takes an `AgentDefinition` + user inputs → assembles a system prompt. Includes: agent goal, constraints as rules, expected output format, conversation guidelines. Injects tool results if tools were run. |
| 4–5 | `engine/runner.py`: The core execution loop. `run_agent(definition, inputs) -> AgentResult`. Steps: (1) check which tools the agent needs, (2) run tools to get structured data, (3) build prompt from definition + inputs + tool results, (4) call LLM, (5) parse output into structured form, (6) return result with explanation. Runs in background thread. |
| 5–6 | `engine/conversation.py`: Multi-turn conversation manager. Maintains chat history per agent session. `followup(user_message) -> str` sends the message with full conversation history + agent context to LLM. Agents stay within scope (system prompt instructs them to redirect out-of-scope questions). |
| 6–7 | Write L2 prompt templates in `prompts/` with detailed instructions and `{{DATA}}` markers. Write `send_with_template(template_path, data) -> str` for L2 mode. Test that L2 produces useful but visibly less structured output than L3. |
| 7–8 | Write remaining 2 pre-built agent definitions (Evacuation Diagnoser + Exit Placement Advisor) in `data/agents/`. Test engine with all 4 agents: structured output, tool integration, multi-turn conversation (3+ turns). |

**Test with**: Standalone script that loads an agent definition, runs it with example data, and has a multi-turn conversation.

### Person C — Tool Layer + Domain Logic

| Hour | Deliverable |
|------|-------------|
| 2–3 | `tools/registry.py`: Tool registry pattern. `register_tool(name, function)`, `get_tool(name) -> function`, `list_tools() -> [ToolInfo]`. Each tool has: name, description, input type, output type. The engine calls `registry.get_tool(name)` to find the right function. |
| 3–4 | `tools/p118_validator.py`: `validate_p118(plan) -> [Violation]`. Implement core rules: `check_travel_distance()` (max 30m, 20m dead-end), `check_exit_capacity()` (80 persons per 1m exit width), `check_door_widths()` (0.9m rooms, 1.2m exits), `check_corridor_widths()` (min 1.4m). |
| 4–5 | `tools/p118_validator.py` continued: `check_dead_ends()` (max 12m), `check_exit_count()` (min 2 per floor for >50 occupants). Each violation includes: rule name, P118 article reference, severity, location, description. |
| 5–6 | `tools/pathfinding.py`: `find_shortest_exit_path(plan, room_id) -> (distance, path)`. BFS/Dijkstra on room-corridor-exit graph. `find_all_travel_distances(plan) -> dict`. Used by P118 travel distance checks and by the Exit Placement Advisor agent. |
| 6–7 | `tools/structural_checker.py`: `detect_blocked_rooms(plan) -> [Violation]` (rooms with no reachable exit), `detect_dead_ends(plan) -> [Violation]` (corridors with one connection), `detect_anomalies(plan) -> [Violation]` (overlapping rooms, zero-width corridors). |
| 7–8 | `tools/metrics.py`: `compute_metrics(violations) -> MetricsReport` (counts by severity, by category, overall pass/fail). Register ALL tools in `registry.py`. Write unit tests in `tests/test_tools.py` with a known-bad floor plan. |

**Test with**: `python -m pytest tests/test_tools.py`. Each tool callable standalone and via registry.

### Person D — Agent Builder + Runner UI + Data

| Hour | Deliverable |
|------|-------------|
| 2–3 | Create 2 example floor plans as JSON in `data/floor_plans/`. One office WITH intentional violations (blocked room, insufficient exits, narrow corridor). One school that is mostly clean. Must look good on canvas and trigger known tool failures. |
| 3–4 | `gui/agent_runner.py`: Agent Runner tab. Layout: agent header (name, goal, [View Definition] button), inputs section (dynamic fields generated from agent definition — file pickers for image/JSON, text fields for parameters), "[Run Agent]" button, outputs section (structured output display, [Export JSON] and [Show on Canvas] buttons). |
| 4–5 | Agent Runner conversation panel: below the I/O section, a chat area showing agent messages + user follow-ups. Text input + "Send" button. Auto-scroll. Input disabled until agent has run. Flagged issues highlighted in agent responses. "[Clear Chat]" button. |
| 5–6 | `gui/agent_builder.py`: Agent Builder tab. Form fields: name, goal (text inputs), inputs section ([+ Add Input] button, each input has name/type/description fields), constraints section ([+ Add Constraint] button, each is a text field), outputs section ([+ Add Output] button), tools section (checkboxes from tool registry), conversational toggle. "[Save Agent]" and "[Save & Run]" buttons. |
| 6–7 | Agent Builder save logic: validates the form, creates `AgentDefinition` object, saves to `user_agents/` as JSON. Agent Library sidebar auto-refreshes to show the new agent. "[Save & Run]" saves then switches to Runner tab with the new agent loaded. |
| 7–8 | `gui/adoption_panel.py`: L2 vs L3 tab. Two-column layout. Left: loads prompt template from `prompts/`. Right: loads corresponding agent definition from `data/agents/`. Dropdown to switch between the 4 pairs. Annotations highlighting differences (structured I/O, tools, constraints, conversation). Create 3rd example floor plan (hospital) if time allows. |

**Test with**: Standalone test — create an agent via Builder, verify JSON saved, load in Runner, verify I/O fields generated correctly.

**EXIT GATE (Hour 8)**: Each person can demo independently. Platform shell with sidebar + tabs works. Engine runs agents with tools. All 4 tools work and pass tests. Builder creates agents, Runner shows I/O + conversation. L2 console UI ready.

---

## PHASE 2 — Integration Wave 1 (Hours 8–12) · PAIRED WORK

### Pair A+D — UI Wiring

| Hour | Deliverable |
|------|-------------|
| 8–9 | Wire sidebar: clicking an agent loads it in the Runner tab. "[+ Create]" opens Builder tab. Agent library refreshes when a new agent is saved. Wire Runner's "[View Definition]" button → opens JSON definition in a formatted `Toplevel` window. |
| 9–10 | Wire Runner's "[Run Agent]" button → calls `engine/runner.py` in a background thread → updates status → displays structured output. Wire conversation: after run completes, text input enables → "Send" calls `conversation.followup()` → response appears in chat. |
| 10–11 | Wire Runner's "[Show on Canvas]" → pushes floor plan or violations to the canvas panel. Wire "[Export JSON]" → file save dialog. Wire metrics display (violation counts, compliance status) in the status bar when Egress Validator runs. |
| 11–12 | Wire L2 Console: "Send to LLM" calls `send_with_template()`, displays raw text. Wire adoption panel: dropdown loads L2/L3 pairs. Polish agent Builder → save → appears in library → run flow. Test: create a custom agent, run it, have a conversation. |

### Pair B+C — Engine + Tools Integration

| Hour | Deliverable |
|------|-------------|
| 8–9 | Integrate tools into engine: when `runner.py` executes an agent, it checks which tools the agent requests, runs them via the registry, and injects results into the LLM prompt. Test: Egress Validator agent calls P118 validator tool + pathfinding tool, results appear in LLM context. |
| 9–10 | Prompt quality: fine-tune `prompt_builder.py` so agents produce well-structured output. Agents must reference tool results in their responses ("The pathfinding tool found that Room R3 is 34m from the nearest exit, exceeding the P118 limit of 30m"). Test multi-turn conversations with tool context preserved. |
| 10–11 | L2 vs L3 output contrast: verify that L2 prompt templates produce useful but raw text, while L3 agents produce structured output with tool references and conversational depth. This contrast must be visible in the demo. |
| 11–12 | Cached/fallback responses: for each pre-built agent + each example floor plan, save known-good responses (initial output + 2-3 follow-up exchanges). If API is down during demo, engine loads cached responses. Also cache L2 raw text responses. **Demo safety net.** |

**EXIT GATE (Hour 12)**: Full workflow works — browse agents, run them, get structured output, have conversations, export results. Agent Builder creates working agents. L2 Console works. Cached fallbacks ready.

---

## PHASE 3 — Full Workflow (Hours 12–16) · ALL CONVERGE

Everyone on the same branch. Frequent commits.

| Hour | Who | Deliverable |
|------|-----|-------------|
| 12–13 | **ALL** | **End-to-end test, both workflows.** (1) USE: select Floor Plan Parser → load image → run → chat about flagged issues → export JSON → select Egress Validator → load exported JSON → run → see violations on canvas → select Exit Placement Advisor → load plan+violations → get fix proposals → push back in conversation. (2) CREATE: open Builder → define a custom "Corridor Width Checker" agent → save → find it in library → run it → verify it works. Fix all blocking bugs. |
| 13–14 | **A** | Canvas polish: room labels, door arcs, exit arrows, violation severity colors (red/yellow/green). Click violation → tooltip. Sidebar polish: category headers, agent icons/status dots, search actually filters. |
| 13–14 | **B** | Agent scope boundaries: each agent redirects out-of-scope questions. Conversational quality: proactive flagging, coherent follow-ups, pushback handling. Verify L2 output is visibly less structured than L3 output. |
| 13–14 | **C** | Edge cases: rooms with no polygon, overlapping corridors, doors referencing nonexistent rooms → graceful violations, not crashes. Provide borderline case data (values near P118 thresholds) so agents can flag them. |
| 13–14 | **D** | Error handling: agent failure shows error in Runner, doesn't crash app. Builder form validation (required fields, valid types). Adoption panel annotations are accurate. Test creating agents with various tool combinations. |
| 14–15 | **A+D** | Canvas ↔ Runner linkage: clicking a violation in the Runner conversation highlights it on canvas. Polish Builder → Library → Runner flow. |
| 14–15 | **B+C** | Test all 4 pre-built agents on all example plans. Test user-created agents with tools. Conversational follow-ups work across all agents. |
| 15–16 | **ALL** | **Full demo rehearsal #1.** Time it. Focus on the L2→L3 narrative and the "create an agent" moment. |

**EXIT GATE (Hour 16)**: Both workflows (use + create) work without crashes. Canvas works. L2 vs L3 contrast is clear. Demo rehearsal completed.

---

## PHASE 4 — Polish & Hardening (Hours 16–20) · PARALLEL

### Person A — Visual Polish
- Professional color scheme (dark sidebar, light content, accent colors)
- L2 Console intentionally plainer than L3 Runner (visual contrast = adoption contrast)
- Agent Library: polished cards with category grouping, status indicators
- Loading states (spinner/progress while agent runs), disabled buttons during execution
- Window title: "AgentForge — Engineering Agent Platform"
- Resize handling, tooltips on all buttons

### Person B — Engine Robustness
- Rate limit handling (show "Waiting for API..." in conversation, auto-retry)
- Timeout handling (>30s → error message in chat, retry button)
- Validate all cached responses match current schema
- Fine-tune L2 vs L3 output contrast — L2 = useful but raw; L3 = structured + conversational
- Test conversation edge cases (long chains, off-topic, adversarial)

### Person C — Tool Depth
- Add 1-2 more P118 rules if time allows (min exits per room by occupancy, emergency lighting)
- Refine severity levels (critical / major / minor / info)
- P118 article citations in every violation
- Borderline case flagging data for agent conversation context
- Ensure tool descriptions in registry are clear (shown in Agent Builder)

### Person D — Builder + Showcase Polish
- Agent Builder: better form layout, field validation, preview of assembled definition
- Keyboard shortcuts: `Ctrl+N` (new agent), `Ctrl+R` (run), `Ctrl+E` (export), `F5` (refresh library)
- Adoption panel: visual arrows showing L2 prompt → L3 agent evolution, "What Changed" summary per pair
- Pre-load default example plan on startup (canvas shows a floor plan immediately)
- Agent chat formatting: bold, bullet lists, severity-colored text

**EXIT GATE (Hour 20)**: Platform looks polished and professional. Both workflows smooth. No crashes. Cached fallbacks work. Adoption showcase is compelling.

---

## PHASE 5 — Demo Prep (Hours 20–24) · ALL TOGETHER

| Hour | Activity |
|------|----------|
| 20–21 | **Demo rehearsal #1.** One person drives. Time every step. Focus on: (1) L2 prompt console moment, (2) L3 agent run + conversation, (3) "Create an agent" moment, (4) L2 vs L3 showcase. Write down all issues. |
| 21–22 | **Fix everything from rehearsal.** Priority: crashes > wrong data > visual glitches > nice-to-haves. If risky, use cached fallback. |
| 22–23 | **Demo rehearsal #2.** Different driver. Practice speaking parts. Nail the L2→L3 transition narrative. Test backup plan (cached responses). |
| 23–23:30 | **Backup plan finalized.** API failure: cached responses for L2 and L3. Parse failure: start from pre-loaded JSON. Builder failure: show a pre-saved user agent. |
| 23:30–24 | **Final commit. Tag release. Rest.** |

---

## Demo Script (90 seconds)

### Act 1: The Problem (10s)
*"Engineers solve complex domain problems — fire safety, structural loads, HVAC design. AI can help, but most teams are stuck at L2: shared prompt templates, copy-paste workflows, raw text outputs. We built a platform that takes them to L3."*

### Act 2: L2 — Where Most Teams Are Today (15s)
1. Open the L2 Console tab. Show versioned prompt templates. (3s)
2. Load example floor plan data, select a prompt, click "Send to LLM." Raw text response appears. (5s)
3. *"This works — but I'm copy-pasting data, reading unstructured text, and starting from scratch for every follow-up. This is L2: systematized prompting."* (7s)

### Act 3: L3 — Agent Workspace (35s)
4. Switch to Agent Library. Show 4 pre-built fire safety agents. Click "Floor Plan Parser." (5s)
5. Upload floor plan image → agent runs → structured output appears. Agent flags: *"Room R5 has an unusual shape — is this intentional?"* Engineer replies. Agent acknowledges. *"That's a conversation — L2 can't do this."* (10s)
6. Export parsed JSON → select Egress Validator → load JSON → run → violations with severities. Click "Show on Canvas" — violations light up on the floor plan. (10s)
7. Select Exit Placement Advisor → load plan + violations → agent proposes fixes. Push back: *"Can't add a south exit."* Agent offers alternatives with justification. (10s)

### Act 4: Create Your Own Agent (15s)
8. Click "[+ Create New Agent]." Fill in: Name = "Corridor Width Checker", Goal = "Verify all corridors meet minimum width requirements", add constraints, select P118 Validator tool. Click "Save & Run." (10s)
9. *"An engineer just created a reusable, conversational agent — no AI expertise needed. That's L3: agents as objects, not prompts."* (5s)

### Act 5: The Transition (10s)
10. Switch to "L2 vs L3" tab. Show side-by-side: prompt template vs agent definition. *"Same LLM. Same domain. But the agent has structured I/O, tool access, constraints, and conversation. This is what AI adoption looks like."* (10s)

### Act 6: Close (5s)
*"We let engineers turn domain knowledge into executable agents. This is the L2 to L3 transition."*

---

## Critical Path & Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Gemini free tier rate limit (15 RPM) | Can't demo live agent runs | Cache all responses (L2 + L3) for every example plan; switch to cached in <5s |
| Vision parsing returns bad JSON | Egress Validator breaks | Ship with pre-crafted JSON floor plans; live image parsing is a stretch goal |
| Agent Builder creates broken agents | Demo embarrassment | Pre-test 2-3 custom agents; have a backup pre-saved user agent in `user_agents/` |
| L2 vs L3 contrast not clear to judges | Miss the theme | Dedicated showcase tab + demo script explicitly narrates the difference |
| P118 rules incomplete | Judges question accuracy | Cite P118 article numbers; disclaim "decision support, not certification" |
| Tkinter looks unprofessional | Platform doesn't feel "mature" | `ttk` themes, custom colors, consistent spacing, professional sidebar |
| Tool integration fragile | Agent output ignores tool data | Cached fallback responses that include tool references; test extensively |

---

## Parallel Work Visualization

```
Hour  0    2    4    6    8   10   12   14   16   18   20   22   24
      |----|----|----|----|----|----|----|----|----|----|----|----|
A:    [SETUP] [= Shell+Canvas+L2 ======] [= UI Wiring  =] [= Converge ==] [Visual] [DEMO]
B:    [SETUP] [= LLM+Engine+Convo =====] [= Engine+Tool=] [= Converge ==] [Robust] [DEMO]
C:    [SETUP] [= Tools+P118+Path ======] [= Engine+Tool=] [= Converge ==] [Depth ] [DEMO]
D:    [SETUP] [= Builder+Runner+Data ==] [= UI Wiring  =] [= Converge ==] [Polish] [DEMO]
      |----|----|----|----|----|----|----|----|----|----|----|----|
Phase: P0     P1 (full parallel) P2 (pairs)  P3 (all)  P4 (par) P5
```

---

## File Ownership

| File / Folder | Owner | Others touch? |
|---------------|-------|---------------|
| `models/` | D (initial), then shared | Everyone reads |
| `gui/app.py`, `gui/canvas.py`, `gui/controls.py` | A | D helps with wiring |
| `gui/agent_library.py`, `gui/l2_console.py` | A | — |
| `gui/agent_runner.py`, `gui/agent_builder.py` | D | A helps with layout |
| `gui/adoption_panel.py` | D | B reviews L2/L3 content |
| `engine/runner.py`, `engine/prompt_builder.py`, `engine/conversation.py` | B | C provides tool integration |
| `llm/gemini_client.py` | B | — |
| `tools/registry.py`, `tools/p118_validator.py`, `tools/pathfinding.py` | C | B calls via engine |
| `tools/structural_checker.py`, `tools/metrics.py` | C | — |
| `prompts/` | B writes content | A displays in L2 console |
| `data/agents/` | B writes definitions | D displays in UI, A loads in sidebar |
| `data/floor_plans/` | D | B uses for testing, C uses for validation tests |
| `user_agents/` | D (save logic) | Runtime only |
| `config.py` | C (rules), B (API) | Split |
| `main.py` | A | Minimal entry point |
| `tests/` | C (tools), D (models) | — |

---

## L2→L3 Compliance Checklist

### L2 elements (the "before" — what we show for contrast)
- [ ] `prompts/` directory with versioned prompt templates committed to repo
- [ ] L2 Prompt Console tab — functional, not just a mockup
- [ ] L2 mode produces useful output (proves L2 works, shows limitations)
- [ ] Templates use `{{PLACEHOLDER}}` markers for data injection

### L3 elements (the "after" — what we build)
- [ ] Repository contains agent definitions as structured JSON objects
- [ ] Agent definitions include: goal, inputs, constraints, outputs, tools, conversation guidelines
- [ ] Agents are reusable — anyone can run them without prompt knowledge
- [ ] Agents have access to domain tools (P118 validator, pathfinding), not just LLM
- [ ] Agents produce structured output with explanations
- [ ] Agents are conversational — multi-turn follow-up, proactive flagging, scope boundaries
- [ ] Engineers can CREATE new agents via the Builder (not just use pre-built ones)
- [ ] Agent definitions are viewable in the UI (the L3 proof for judges)

### L2→L3 transition showcase
- [ ] "L2 vs L3" tab with side-by-side comparison
- [ ] Visible contrast: L2 raw text vs L3 structured + conversational output
- [ ] Demo script explicitly narrates the transition
- [ ] Annotations explaining what changed (I/O, tools, constraints, conversation, reusability)

### L4 elements (must NOT have)
- ~~Orchestrator coordinating agents~~
- ~~Automatic pipeline between agents~~
- ~~Agents passing data to each other~~
- ~~DAG or workflow definition~~
- ~~Agent-to-agent communication~~
