# Roadmap: 24-Hour Hackathon — Fire Safety Evacuation Copilot

> **Stack**: Python + Tkinter · Gemini API (free tier) · Romanian P118 validation
> **Team**: 4 Python generalists · **Goal**: Working desktop app + 90-second demo
> **AI Adoption Level**: L3 — Agent-based development (each agent performs a distinct job, engineer controls the workflow)

---

## Team Roles

| Person | Codename | Owns |
|--------|----------|------|
| **A** | **GUI** | Tkinter shell, sector layout, canvas rendering, overlays, controls |
| **B** | **LLM** | Gemini API integration, all agent logic (vision parse, diagnosis, fix proposals), conversational prompts |
| **C** | **Rules** | Romanian P118 validation engine, structural anomaly detection, metrics |
| **D** | **Glue** | JSON schema, dataclasses, example floor plans, agent sector box UI, agent chat widget, data export/import |

---

## Architecture: L3 — Engineer as Middleman

The app contains **four independent AI agents**, each performing a distinct job. There is **no orchestrator** and **no automated pipeline**. The civil engineer (user) is the middleman:

- The engineer decides which agent to use and in what order
- The engineer manually passes data between agents (export output from one, import into another)
- Each agent has its own **sector box** in the UI with file input, conversational output, and export
- Agents are **conversational** — they flag issues, answer follow-ups, and discuss trade-offs
- Agents **never communicate with each other** — all data flows through the engineer

This is **L3** (agents performing distinct jobs) and explicitly **not L4** (no orchestrated workflows, no DAGs, no agent-to-agent coordination).

### Why L3, not L4

| L3 (what we build) | L4 (what we avoid) |
|---------------------|---------------------|
| Each agent does one specific job | Agents coordinated via workflows/DAGs |
| Engineer manually triggers each agent | Automatic pipeline triggers agents in sequence |
| Engineer passes data between agents | Agents pass data to each other |
| Engineer has free will in ordering | Fixed execution order |
| Repo contains agents with definition files | Repo contains orchestration logic |

---

## UI Layout: Sector Boxes

The main window has two regions:

1. **Agent Sectors (main area)** — four agent sector boxes arranged in a 2x2 grid (or tabbed view for smaller screens)
2. **Shared Canvas (toggleable panel)** — floor plan rendering + violation overlays, any sector can push data to it

Each **agent sector box** contains:
- Agent name, one-line description, and status indicator (idle / running / done / error)
- **File input area** — file picker for that agent's expected input type
- **"Run" button** — triggers the agent on the loaded input
- **Conversational chat area** — scrollable chat-like display showing agent output and follow-up conversation
- **"Export Output" button** — saves the agent's structured output to a file for use in another sector
- **"Show on Canvas" button** — pushes the agent's output (plan or violations) to the shared canvas
- **"Show Agent Definition" button** — displays the agent's `.md` definition file (L3 showcase)

### The Four Sector Boxes

| Sector | Agent | Input | Output | Conversational Behavior |
|--------|-------|-------|--------|------------------------|
| 1 | **PlanParser** | Floor plan image/PDF | Parsed JSON (rooms, walls, doors, exits) | Flags ambiguous areas ("Room R5 polygon is unusual — verify?"), answers questions about the parse |
| 2 | **EgressChecker** | Parsed floor plan JSON | List of violations with severities | Explains which rules were checked, flags borderline cases ("corridor C2 is exactly at 1.4m minimum — passes but barely") |
| 3 | **EvacDiagnoser** | Violations JSON | Plain-language diagnosis ranked by severity | Discusses specific violations in detail on follow-up, explains impact |
| 4 | **Redesigner** | Floor plan JSON + violations JSON | Ranked fix proposals | Discusses trade-offs, proposes alternatives when engineer pushes back ("What if we can't add a south exit?") |

### Example Workflows (Engineer's Free Will)

The engineer chooses the order. Some possibilities:
- **Normal flow**: PlanParser → EgressChecker → EvacDiagnoser → Redesigner
- **Skip parsing**: Load hand-crafted JSON directly into EgressChecker
- **Skip diagnosis**: Go from EgressChecker straight to Redesigner
- **Iterate**: Run Redesigner, then go back to EgressChecker with a modified plan
- **Any order**: The UI imposes no constraints

---

## Project Structure

```
polihack-v19-bmvp/
├── main.py                  # Entry point — launches the Tkinter app
├── requirements.txt         # google-generativeai, Pillow, python-dotenv
├── config.py                # API keys, constants, P118 thresholds
├── models/
│   ├── __init__.py
│   ├── schema.py            # Dataclasses: FloorPlan, Room, Wall, Door, Exit, Corridor
│   ├── violations.py        # Dataclasses: Violation, DiagnosisResult, FixProposal
│   └── chat.py              # Dataclass: AgentChatMessage (role, content, timestamp, flags)
├── gui/
│   ├── __init__.py
│   ├── app.py               # Main window, sector-based layout
│   ├── canvas.py            # Floor plan canvas rendering + overlays
│   ├── agent_sectors.py     # Reusable AgentSectorBox widget (one per agent)
│   ├── agent_chat.py        # AgentChat widget — conversational UI within each sector
│   ├── controls.py          # Global controls strip — example plan dropdown, reset, theme
│   └── metrics_bar.py       # Top bar — violation counts, compliance status
├── agents/
│   ├── __init__.py
│   ├── plan_parser.py       # PlanParser agent — image → JSON via Gemini vision
│   ├── egress_checker.py    # EgressChecker agent — wraps validation engine
│   ├── evac_diagnoser.py    # EvacDiagnoser agent — violations → plain language
│   ├── redesigner.py        # Redesigner agent — propose fixes
│   └── base.py              # Base agent class with state machine + conversational interface
├── validation/
│   ├── __init__.py
│   ├── p118_rules.py        # Romanian P118 rule checks (pure functions)
│   ├── structural.py        # Structural anomaly detection (blocked rooms, dead ends)
│   └── metrics.py           # Metric calculations (violation counts, severities)
├── llm/
│   ├── __init__.py
│   └── gemini_client.py     # Gemini API wrapper (vision + text + chat_followup, retries, rate limit)
├── data/
│   ├── example_office.json  # Example floor plan — office with violations
│   ├── example_school.json  # Example floor plan — school, clean
│   ├── example_hospital.json# Example floor plan — hospital with violations
│   └── agent_definitions/   # agent.md files for each agent (L3 showcase)
│       ├── plan_parser.md
│       ├── egress_checker.md
│       ├── evac_diagnoser.md
│       └── redesigner.md
└── tests/
    ├── test_validation.py   # Unit tests for P118 rules
    └── test_models.py       # Unit tests for schema parsing
```

**Notable removals vs. L4 design**:
- No `agents/orchestrator.py` — the engineer is the orchestrator
- No `gui/diagnosis_view.py` — diagnosis lives inside the EvacDiagnoser sector chat

---

## PHASE 0 — Foundation (Hours 0–2) · ALL TOGETHER

**Most important phase. Everyone in the same room. No solo work until the shared contract is locked.**

### Hour 0–1: Schema & Interfaces

- **ALL**: Define the JSON schema for a parsed floor plan. This is THE shared contract. Example:
  ```json
  {
    "building_name": "Office Building A",
    "floor": 1,
    "dimensions": {"width_m": 40, "height_m": 25},
    "rooms": [
      {"id": "R1", "name": "Office 101", "polygon": [[0,0],[10,0],[10,8],[0,8]], "type": "office", "occupancy": 20}
    ],
    "walls": [
      {"start": [0,0], "end": [10,0], "thickness_m": 0.2}
    ],
    "doors": [
      {"id": "D1", "position": [5,0], "width_m": 0.9, "connects": ["R1","corridor_1"], "is_exit": false}
    ],
    "exits": [
      {"id": "E1", "position": [0,12], "width_m": 1.2, "type": "main"}
    ],
    "corridors": [
      {"id": "C1", "polygon": [[10,0],[12,0],[12,25],[10,25]], "width_m": 2.0}
    ],
    "stairs": []
  }
  ```
- **D**: Write `models/schema.py` — Python dataclasses matching the schema
- **D**: Write `models/violations.py` — Violation, DiagnosisResult, FixProposal dataclasses
- **D**: Write `models/chat.py` — AgentChatMessage dataclass (role: user|agent, content, timestamp, flagged_issues list)
- **ALL**: Review and agree on the dataclasses — these are the function signatures everyone codes against

### Hour 1–2: Project Setup

- **B**: Get Gemini API key (5 min on Google AI Studio). Share with team via `.env` file (gitignored)
- **A**: Create project structure (folders, `__init__.py` files, `main.py` skeleton)
- **A**: Write `requirements.txt`: `google-generativeai`, `Pillow`, `python-dotenv`
- **C**: Define validation function signatures in `validation/p118_rules.py` (stubs returning empty lists)
- **D**: Write `agents/base.py` — BaseAgent class with state enum (IDLE, RUNNING, DONE, ERROR), `run()` method, and `chat_followup(message) -> str` method for conversational interaction
- **ALL**: `pip install -r requirements.txt`, verify everyone can import everything
- **ALL**: Agree on git workflow (feature branches, merge to main at integration points)

**EXIT GATE**: Everyone can run `python main.py` and see an empty Tkinter window. Schema dataclasses importable from all modules. No orchestrator interfaces — each agent is standalone.

---

## PHASE 1 — Core Build (Hours 2–8) · FULL PARALLEL

No cross-team dependencies. Everyone works on their own module using the agreed schema.

### Person A — GUI Shell + Sector Layout

| Hour | Deliverable |
|------|-------------|
| 2–3 | Main window with sector-based layout: 4 agent sector boxes arranged in a 2x2 grid. Each sector is a `ttk.LabelFrame`. Shared canvas area as a toggleable/collapsible panel. Use `ttk` for modern look. |
| 3–4 | Sector box widget template: agent name header, file input area (file picker button + drag-drop zone), "Run" button (disabled until input loaded), status indicator (colored dot/label), output area placeholder, "Export Output" button, "Show on Canvas" button. |
| 4–5 | Shared canvas component: render a floor plan from JSON — draw room polygons as filled rectangles, walls as thick lines, doors as gaps with arcs, exits as green markers. Use Tkinter Canvas with `create_polygon`, `create_line`, `create_oval`. |
| 5–6 | Canvas interaction: zoom (mouse wheel), pan (click-drag), fit-to-window button. Coordinate transform system (world coords <-> screen coords). |
| 6–7 | Canvas overlays: toggle-able layer for violation markers (red/yellow circles at violation locations, clickable). Checkboxes in a small toolbar above the canvas to show/hide layers (violations, room labels, occupancy numbers). |
| 7–8 | Global controls strip: example plan dropdown (3 pre-loaded entries), "Reset All" button, theme toggle. Top metrics bar: labels for violation count (colored), compliance status (PASS/FAIL badge), breakdown by category. Wired to accept a `MetricsUpdate` dataclass. |

**Test with**: Hardcoded JSON floor plan loaded on startup. All UI elements visible and responsive even with no backend.

### Person B — LLM Integration + Conversational Agents

| Hour | Deliverable |
|------|-------------|
| 2–3 | `llm/gemini_client.py`: Gemini API wrapper. `parse_image(image_path) -> str`, `diagnose(violations_json) -> str`, `propose_fixes(plan_json, violations_json) -> str`, `chat_followup(agent_context, conversation_history, user_message) -> str`. Handle API key from env, retries on rate limit (free tier: 15 RPM for Flash). |
| 3–5 | `agents/plan_parser.py`: PlanParser agent. Takes an image, sends to Gemini with a carefully crafted prompt that demands JSON output matching the schema. **Conversational**: system prompt instructs the agent to flag ambiguities and unusual features in the parsed plan. After initial parse, agent includes flagged issues in its response. Engineer can ask follow-ups via `chat_followup()`. **This is the hardest prompt — spend 2 hours here.** Test with 3+ floor plan images. |
| 5–6 | `agents/evac_diagnoser.py`: EvacDiagnoser agent. Takes a list of Violations, sends to Gemini with context, gets back plain-language diagnosis. **Conversational**: engineer can ask "Tell me more about the east wing issue" or "Which violation is most dangerous?" and get focused follow-ups. Prompt: "You are a fire safety engineer reviewing a building plan. Explain each violation in plain language, rank by severity, reference specific rooms by name. Flag any borderline or surprising findings." |
| 6–7 | `agents/redesigner.py`: Redesigner agent. Takes floor plan JSON + violations, asks Gemini to propose fixes. **Conversational**: engineer can push back ("We can't add a south exit — budget constraints") and get alternative proposals. Prompt includes instruction to discuss trade-offs and offer alternatives. Output: list of FixProposal objects. |
| 7–8 | `agents/egress_checker.py`: Thin wrapper that calls the validation engine (Person C's code) and packages results. **Conversational**: wraps validation output with LLM explanations — flags borderline cases ("corridor C2 is exactly at the 1.4m minimum"), explains which rules were checked. Write agent definition files in `data/agent_definitions/` — each defines scope, input/output schema, prompt template, conversational guidelines. |

**Test with**: Standalone scripts that call each agent and print results. Test multi-turn conversations.

### Person C — Validation Engine

| Hour | Deliverable |
|------|-------------|
| 2–3 | Research Romanian P118 norms — key rules to implement. Write them as constants in `config.py`: max travel distance (30m normal, 20m dead-end), min door width (0.9m rooms, 1.2m exits), min corridor width (1.4m), max dead-end length (12m), exit capacity (80 persons per 1m of exit width). |
| 3–4 | `validation/p118_rules.py` — implement `check_travel_distance(plan) -> [Violation]`: for each room, compute shortest path to nearest exit. If > threshold, violation. Use BFS/simple distance on the room-corridor-exit graph. |
| 4–5 | Continue `p118_rules.py` — `check_exit_capacity(plan) -> [Violation]`: sum total occupancy, sum total exit width, check ratio. `check_door_widths(plan) -> [Violation]`: iterate doors, check min width. `check_dead_ends(plan) -> [Violation]`: detect corridors with only one connection, check length. |
| 5–6 | `validation/structural.py` — `detect_blocked_rooms(plan) -> [Violation]`: rooms with no door or all doors leading to other blocked rooms (graph reachability to any exit). `detect_inaccessible_areas(plan) -> [Violation]`: rooms not connected to the corridor/exit graph. |
| 6–7 | `validation/structural.py` — `detect_anomalies(plan) -> [Violation]`: nonsensical geometry (overlapping rooms, zero-width corridors, doors in walls that don't exist). Corridor width check vs minimum. |
| 7–8 | `validation/metrics.py` — `compute_metrics(violations) -> MetricsUpdate`: count by severity, count by category, overall pass/fail. Write unit tests in `tests/test_validation.py` with a known-bad floor plan. |

**Test with**: Unit tests. `python -m pytest tests/test_validation.py`. Create a tiny test floor plan with known violations.

### Person D — Data, Sector UI Components, Agent Chat Widget

| Hour | Deliverable |
|------|-------------|
| 2–4 | Create 2–3 example floor plans as JSON files in `data/`. **This is critical for the demo.** One office plan WITH intentional violations (blocked room, insufficient exits, narrow corridor). One school plan that is mostly clean. Design realistic-looking plans, then hand-write the JSON. These must look good on canvas. |
| 4–5 | `gui/agent_sectors.py` — reusable `AgentSectorBox` widget class. Each instance takes: agent name, description, accepted file types, agent reference. Contains: header with name + description + status dot, file input area with picker button, "Run" button, chat output area (uses `AgentChat` widget), "Export Output" button, "Show on Canvas" button, "Show Agent Definition" button. |
| 5–6 | `gui/agent_chat.py` — `AgentChat` widget. Scrollable message list (alternating user/agent messages, styled differently). Text input field + "Send" button for follow-up questions. Agent messages can contain **flagged issues** (highlighted in yellow/orange). Supports auto-scroll on new messages. Input field disabled until agent has run at least once. |
| 6–7 | Data flow helpers: "Export Output" button saves agent's last structured output to a JSON file (file save dialog). "Load Input" file picker in each sector accepts files. No auto-passing between sectors — engineer must explicitly export from one and import to another. Add "Copy to Clipboard" for JSON outputs. |
| 7–8 | Write 4 `agent.md` definition files in `data/agent_definitions/`. Each defines: scope, input schema, output schema, prompt template, conversational guidelines, retry policy. "Show Agent Definition" button in each sector opens a `Toplevel` window displaying the `.md` file. Pre-load default example plan on app startup (PlanParser sector shows a pre-loaded plan). |

**Test with**: Standalone test script that creates sector widgets, loads data, and verifies export/import works.

**EXIT GATE (Hour 8)**: Each person can demo their module independently. GUI shows 4 sector boxes with chat areas. LLM agents respond conversationally with flagged issues. Validation returns violations from a test plan. Sector boxes can export/import data manually.

---

## PHASE 2 — Integration Wave 1 (Hours 8–12) · PAIRED WORK

### Pair A+D — Sector UI + Data Flow Wiring

| Hour | Deliverable |
|------|-------------|
| 8–9 | Wire each sector's "Run" button to its agent (runs in background thread so GUI doesn't freeze, updates chat area with result). Wire file picker in PlanParser sector to accept images/PDFs, other sectors to accept JSON files. |
| 9–10 | Wire "Show on Canvas" button: when PlanParser produces output, clicking "Show on Canvas" renders the parsed plan on the shared canvas. When EgressChecker produces violations, "Show on Canvas" adds violation overlay markers to the canvas. |
| 10–11 | Wire metrics bar: when engineer runs EgressChecker, metrics bar updates with violation counts and compliance status. Wire conversational follow-up: after agent output appears in chat, text input field enables → engineer types a question → "Send" calls `chat_followup()` → response appears in chat thread. |
| 11–12 | Polish data flow: "Export" opens a file save dialog. Other sectors' "Load Input" opens a file browse dialog. Add "Copy to Clipboard" for quick JSON sharing. Test the full manual handoff: export PlanParser output → import into EgressChecker → export violations → import into EvacDiagnoser. |

### Pair B+C — LLM + Validation + Conversational Quality

| Hour | Deliverable |
|------|-------------|
| 8–9 | Test PlanParser output against validation engine. Fix schema mismatches — the LLM output may not perfectly match the schema. Add a `normalize_parsed_plan()` function that coerces LLM output into valid dataclasses (fill defaults, fix types, clamp values). |
| 9–10 | Fine-tune conversational prompts: PlanParser must flag ambiguities proactively, EvacDiagnoser must answer follow-ups coherently and stay on-topic, Redesigner must handle pushback and offer alternatives. Test multi-turn conversations (3+ turns). |
| 10–11 | Fine-tune EgressChecker conversational wrapper: when validation finds borderline cases (values near thresholds), the LLM wrapper explains them conversationally. Redesigner prompt iteration: proposals must be specific and actionable ("add exit door on east wall of Room R3 at position [15, 8], width 1.2m"). |
| 11–12 | Add **cached/fallback responses**: for each example floor plan, save a known-good LLM response as a JSON file — including initial output AND 2-3 pre-written follow-up exchanges. If the API is down or rate-limited during demo, load the cached response instead. **This is the demo safety net.** |

**EXIT GATE (Hour 12)**: Each sector box works independently. Engineer can manually run agents in any order, export/import data between them, and have follow-up conversations. Canvas shows plans and violations when engineer chooses. No automatic pipeline — all actions are engineer-initiated.

---

## PHASE 3 — Full Manual Workflow (Hours 12–16) · ALL CONVERGE

Everyone works on the same branch now. Frequent commits, frequent pulls.

| Hour | Who | Deliverable |
|------|-----|-------------|
| 12–13 | **ALL** | End-to-end manual workflow test: Engineer opens app → uploads image to PlanParser sector → chats with PlanParser about flagged issues → exports JSON → loads into EgressChecker → runs validation → exports violations → loads into EvacDiagnoser → reads diagnosis → asks follow-up → loads plan+violations into Redesigner → gets fix proposals → discusses alternatives. Fix every bug that blocks this flow. |
| 13–14 | **A** | Canvas polish: better room labels, door arcs, exit arrows, violation markers with severity colors (red = critical, yellow = warning, green = info). Click a violation marker on canvas → shows tooltip with details. Sector box layout responsiveness (resize handling). |
| 13–14 | **B** | Conversational quality: test that agents flag issues proactively without being asked, handle follow-ups coherently, and stay within their scope. Test edge cases: asking PlanParser about violations (should say "I only parse plans — try EgressChecker for validation"). Each agent knows its boundaries. |
| 13–14 | **C** | Edge case handling: what if a room has no polygon? What if corridors overlap? What if doors reference nonexistent rooms? Return graceful violations instead of crashing. Provide borderline case data so EgressChecker's conversational wrapper can flag them. |
| 13–14 | **D** | Error handling per sector: if any agent fails, show error message in its chat area, don't crash the app. Allow re-running. "Clear Chat" button per sector to reset conversation. Test out-of-order workflows: run Redesigner before EvacDiagnoser, run EgressChecker without PlanParser, etc. |
| 14–15 | **A+D** | Canvas ↔ sector linkage: clicking a violation in EgressChecker's chat highlights the location on canvas. Overlay toggle checkboxes. Polish "Show on Canvas" flow. |
| 14–15 | **B+C** | Test with the 2nd and 3rd example plans. Fix any prompt/validation issues specific to school and hospital layouts. Test conversational follow-ups on each plan. |
| 15–16 | **ALL** | Full run-through of the demo script. Time it. Identify any step that takes too long or looks bad. Test the "engineer skips a step" demo moment. |

**EXIT GATE (Hour 16)**: Manual workflow runs start to finish without crashes. All 4 sector boxes work independently. Conversational follow-ups work in every sector. Out-of-order workflows don't crash. Canvas shows plans and violations. Flagged issues are visible in chat.

---

## PHASE 4 — Polish & Hardening (Hours 16–20) · PARALLEL

### Person A — Visual Polish
- Better color scheme (dark sidebar, light canvas, accent colors for violations)
- Sector box styling — clear visual separation, consistent spacing
- App icon and window title
- Resize handling (responsive sector grid)
- Loading states (cursor changes, disabled buttons while agents run)
- Tooltips on buttons and violation markers

### Person B — Robustness
- Rate limit handling (show "waiting for API" in agent chat)
- Timeout handling (agent stuck for >30s → show error in chat, allow retry)
- Validate that ALL cached/fallback responses still match current schema
- Test with edge-case images (blurry, rotated, partial floor plans)
- Test conversational edge cases (very long follow-up chains, off-topic questions)

### Person C — Validation Depth
- Add 2–3 more P118 rules if time allows (min exits per room based on occupancy, emergency lighting requirements)
- Refine severity levels (graduated: critical / major / minor / info)
- Add rule citations: each violation references the specific P118 article number
- Provide threshold data for borderline case flagging

### Person D — UX Polish
- Keyboard shortcuts: `V` (validate in EgressChecker), `D` (diagnose in EvacDiagnoser), `R` (reset all), `F` (fit canvas to window)
- Status bar at bottom: "Ready" / "PlanParser running..." / "4 violations found" / etc.
- Agent chat formatting: render agent responses with basic markdown (bold, bullet lists)
- "Show Agent Definition" button polish — display `.md` file in a formatted `Toplevel` window (the L3 proof for judges)
- Pre-load default example plan on app startup (PlanParser sector pre-populated, no blank canvas)

**EXIT GATE (Hour 20)**: App looks and feels polished. No crashes on any of the 3 example plans. Cached fallbacks work if API is down. Agent definition files are viewable and well-formatted.

---

## PHASE 5 — Demo Prep (Hours 20–24) · ALL TOGETHER

| Hour | Activity |
|------|----------|
| 20–21 | **Full demo rehearsal #1.** One person drives, others watch. Time every step. Write down every bug, visual glitch, or awkward pause. Focus on the "engineer controls the workflow" narrative. |
| 21–22 | **Fix everything from rehearsal.** Priority: crashes > wrong data > visual glitches > nice-to-haves. If a fix is risky, use the cached fallback instead. |
| 22–23 | **Full demo rehearsal #2.** Different person drives. Practice the speaking parts. Make sure the "engineer as middleman" workflow is clear. Test the "skip a step" moment and the conversational follow-up moment. |
| 23–23:30 | **Prepare backup plan.** If live API fails: cached responses ready, switch in <5 seconds. If parsing fails: start from pre-loaded JSON plan in EgressChecker sector. |
| 23:30–24 | **Final commit. Tag release. Everyone rest before the presentation.** |

---

## Demo Script (90 seconds)

1. "Every commercial building must pass fire egress review. Architects today get this feedback weeks later from a specialist." (10s)
2. Show the four agent sector boxes — all idle. Engineer **chooses** to start with PlanParser. (5s)
3. Engineer uploads floor plan image to PlanParser sector → agent processes → shows parsed JSON in chat. **Agent flags an issue**: "I noticed room R5 has an unusual polygon shape — is this intentional?" Engineer responds: "Yes, it's an L-shaped room." Agent acknowledges. (15s)
4. Engineer **exports** parsed JSON, **imports** it into EgressChecker sector → runs validation → violations appear in chat with severity colors. Agent says: "Found 4 violations, 2 critical. The east wing exit capacity is the most urgent. Corridor C2 is at exactly the 1.4m minimum — technically compliant but worth noting." Engineer clicks "Show on Canvas" — violations light up on the floor plan. (15s)
5. Engineer **skips EvacDiagnoser** (free will!) and jumps to Redesigner → loads plan + violations → gets ranked fix proposals. Has a conversation: "What if we can't add a south exit?" Agent: "Alternative: widen the existing east exit from 1.0m to 1.8m and add an emergency door from Room R12 to corridor C1. This reduces travel distance by 8m." (20s)
6. Show the "Agent Definition" button → opens PlanParser's `.md` file showing scope, input/output schema, prompt template. "This is L3 AI adoption — each agent has a clear definition, does one specific job, and the engineer stays in control. No black-box pipeline. The architect decides the workflow." (15s)
7. "This is how fire safety review should work — AI agents as specialist tools, the engineer as the decision maker, powered by real Romanian P118 regulations." (10s)

---

## Critical Path & Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Gemini free tier rate limit (15 RPM) | Can't demo live parsing or conversations | Cache all LLM responses + follow-up exchanges for example plans; load cached if API fails |
| Vision parsing returns bad JSON | Validation and rendering break | Ship with 2-3 hand-crafted JSON plans; live parsing is a stretch goal |
| P118 rules wrong or incomplete | Judges question accuracy | Cite specific P118 article numbers; disclaim "decision support, not certification" |
| Tkinter looks ugly | Bad first impression | Use `ttk` themes (`clam` or `alt`), custom colors, consistent spacing |
| Manual data passing feels clunky | Bad UX impression | Smooth export/import flow, "Copy to Clipboard" for JSON, clear file naming |
| Conversational follow-ups go off-topic | Agent gives irrelevant answers | System prompt boundaries ("you are PlanParser — only discuss floor plan parsing"), test edge cases |

---

## Parallel Work Visualization

```
Hour  0    2    4    6    8   10   12   14   16   18   20   22   24
      |----|----|----|----|----|----|----|----|----|----|----|----|
A:    [SETUP] [= Sector Layout + Canvas =] [= Sector+Data =] [= All Converge =] [Polish] [DEMO]
B:    [SETUP] [= LLM + Conversational  =] [= LLM+Valid   =] [= All Converge =] [Robust] [DEMO]
C:    [SETUP] [= Validation Engine =====] [= LLM+Valid   =] [= All Converge =] [Depth ] [DEMO]
D:    [SETUP] [= Data + SectorUI + Chat] [= Sector+Data =] [= All Converge =] [UX Pol] [DEMO]
      |----|----|----|----|----|----|----|----|----|----|----|----|
Phase: P0     P1 (parallel)   P2 (pairs)  P3 (all)  P4 (par) P5(all)
```

---

## File Ownership

| File / Folder | Owner | Others touch? |
|---------------|-------|---------------|
| `models/` | D (initial), then shared | Everyone reads, nobody else writes |
| `gui/app.py`, `gui/canvas.py`, `gui/controls.py`, `gui/metrics_bar.py` | A | D helps wire sectors |
| `gui/agent_sectors.py` | D | A helps with layout |
| `gui/agent_chat.py` | D | B provides conversational logic |
| `llm/gemini_client.py` | B | Nobody else touches |
| `agents/plan_parser.py`, `agents/evac_diagnoser.py`, `agents/redesigner.py` | B | D calls from sector UI |
| `agents/egress_checker.py`, `agents/base.py` | D (base), B (agent logic) | Split ownership |
| `validation/` | C | B wraps in egress_checker |
| `data/*.json` | D | B uses for prompt testing |
| `data/agent_definitions/` | B writes content, D displays in UI | Shared |
| `config.py` | C (rules), B (API) | Split ownership |
| `main.py` | A | Entry point, kept minimal |
| `tests/` | C | B adds LLM output tests |

**No `agents/orchestrator.py`** — the engineer is the orchestrator.

---

## L3 Compliance Checklist

**L3 requirements (must have)**:
- [ ] Repository contains agents performing distinct jobs
- [ ] Agent definition files (`.md`) in `data/agent_definitions/`
- [ ] Each agent has clear scope, input/output schema
- [ ] Engineer manually triggers each agent
- [ ] Engineer controls workflow order (free will)
- [ ] Agents are conversational (flag issues, answer follow-ups)
- [ ] "Show Agent Definition" button proves L3 to judges

**L4 elements (must NOT have)**:
- ~~Orchestrator coordinating agents~~
- ~~Automatic pipeline (parse → validate → diagnose → propose)~~
- ~~Agents passing data to each other~~
- ~~DAG or workflow definition~~
- ~~Agent-to-agent communication~~
