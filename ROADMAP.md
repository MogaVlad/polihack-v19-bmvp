# Roadmap: 24-Hour Hackathon — Fire Safety Evacuation Copilot

> **Stack**: Python + Tkinter · Gemini API (free tier) · Romanian P118 validation
> **Team**: 4 Python generalists · **Goal**: Working desktop app + 90-second demo

---

## Team Roles

| Person | Codename | Owns |
|--------|----------|------|
| **A** | **GUI** | Tkinter shell, canvas rendering, overlays, controls, keyboard shortcuts |
| **B** | **LLM** | Gemini API integration, all prompts (vision parse, diagnosis, fix proposals) |
| **C** | **Rules** | Romanian P118 validation engine, structural anomaly detection, metrics |
| **D** | **Glue** | JSON schema, dataclasses, example floor plans, agent orchestration, agents panel UI |

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
│   └── violations.py        # Dataclasses: Violation, DiagnosisResult, FixProposal
├── gui/
│   ├── __init__.py
│   ├── app.py               # Main window, three-region layout
│   ├── canvas.py            # Floor plan canvas rendering + overlays
│   ├── agents_panel.py      # Right panel — agent status cards
│   ├── controls.py          # Left strip — file picker, buttons
│   ├── metrics_bar.py       # Top bar — violation counts, compliance status
│   └── diagnosis_view.py    # Diagnosis list + fix proposals display
├── agents/
│   ├── __init__.py
│   ├── orchestrator.py      # Pipeline: parse → validate → diagnose → propose
│   ├── plan_parser.py       # PlanParser agent — image → JSON via Gemini vision
│   ├── egress_checker.py    # EgressChecker agent — wraps validation engine
│   ├── evac_diagnoser.py    # EvacDiagnoser agent — violations → plain language
│   ├── redesigner.py        # Redesigner agent — propose fixes
│   └── base.py              # Base agent class with state machine (idle/running/done/error)
├── validation/
│   ├── __init__.py
│   ├── p118_rules.py        # Romanian P118 rule checks (pure functions)
│   ├── structural.py        # Structural anomaly detection (blocked rooms, dead ends)
│   └── metrics.py           # Metric calculations (violation counts, severities)
├── llm/
│   ├── __init__.py
│   └── gemini_client.py     # Gemini API wrapper (vision + text, retries, rate limit handling)
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

---

## PHASE 0 — Foundation (Hours 0–2) · ALL TOGETHER

**Most important phase. Everyone in the same room. No solo work until the shared contract is locked.**

### Hour 0–1: Schema & Interfaces

- **ALL**: Define the JSON schema for a parsed floor plan. This is THE shared contract that every module depends on. Example:
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
- **ALL**: Review and agree on the dataclasses — these are the function signatures everyone codes against

### Hour 1–2: Project Setup

- **B**: Get Gemini API key (5 min on Google AI Studio). Share with team via `.env` file (gitignored)
- **A**: Create project structure (folders, `__init__.py` files, `main.py` skeleton)
- **A**: Write `requirements.txt`: `google-generativeai`, `Pillow`, `python-dotenv`
- **C**: Define validation function signatures in `validation/p118_rules.py` (stubs returning empty lists)
- **D**: Write `agents/base.py` — BaseAgent class with state enum (IDLE, RUNNING, DONE, ERROR) and callbacks
- **ALL**: `pip install -r requirements.txt`, verify everyone can import everything
- **ALL**: Agree on git workflow (feature branches, merge to main at integration points)

**EXIT GATE**: Everyone can run `python main.py` and see an empty Tkinter window. Schema dataclasses importable from all modules.

---

## PHASE 1 — Core Build (Hours 2–8) · FULL PARALLEL

No cross-team dependencies. Everyone works on their own module using the agreed schema.

### Person A — GUI Shell

| Hour | Deliverable |
|------|-------------|
| 2–3 | Main window with three-region layout: canvas frame (center 60%), right panel frame (25%), top bar + left strip (15%). Use `ttk` for modern look. |
| 3–4 | Left control strip: file picker button (image/PDF/JSON), example plan dropdown (3 hardcoded entries), "Parse" / "Validate" / "Diagnose" / "Propose Fix" buttons (disabled until relevant). |
| 4–5 | Top metrics bar: labels for violation count (colored), compliance status (PASS/FAIL badge), breakdown by category. Wired to accept a `MetricsUpdate` dataclass. |
| 5–6 | Canvas basics: render a floor plan from JSON — draw room polygons as filled rectangles, walls as thick lines, doors as gaps with arcs, exits as green markers. Use Tkinter Canvas with `create_polygon`, `create_line`, `create_oval`. |
| 6–7 | Canvas interaction: zoom (mouse wheel), pan (click-drag), fit-to-window button. Coordinate transform system (world coords <-> screen coords). |
| 7–8 | Overlay system: toggle-able layer for violation markers (red/yellow circles at violation locations, clickable). Scaffold for diagnosis markers. |

**Test with**: Hardcoded JSON floor plan loaded on startup. All UI elements visible and responsive even with no backend.

### Person B — LLM Integration

| Hour | Deliverable |
|------|-------------|
| 2–3 | `llm/gemini_client.py`: Gemini API wrapper. `parse_image(image_path) -> str`, `diagnose(violations_json) -> str`, `propose_fixes(plan_json, violations_json) -> str`. Handle API key from env, retries on rate limit (free tier: 15 RPM for Flash). |
| 3–5 | `agents/plan_parser.py`: PlanParser agent. Takes an image, sends to Gemini with a carefully crafted prompt that demands JSON output matching the schema. **This is the hardest prompt — spend 2 hours here.** Test with 3+ floor plan images. Validate output parses into schema dataclasses. Include a system prompt with the exact JSON schema and 1 example. |
| 5–6 | `agents/evac_diagnoser.py`: EvacDiagnoser agent. Takes a list of Violations, sends to Gemini with context, gets back plain-language diagnosis. Prompt: "You are a fire safety engineer reviewing a building plan. Here are the violations found. Explain each in plain language, rank by severity, and reference specific rooms/corridors by name." |
| 6–7 | `agents/redesigner.py`: Redesigner agent. Takes floor plan JSON + violations, asks Gemini to propose fixes. Prompt: "Given this floor plan and these violations, propose specific modifications. Each fix: what to change, where, why, estimated impact. Rank by priority." Output: list of FixProposal objects. |
| 7–8 | `agents/egress_checker.py`: Thin wrapper that calls the validation engine (Person C's code) and packages results. Write agent definition files in `data/agent_definitions/`. |

**Test with**: Standalone scripts that call each agent and print results. Don't need GUI.

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

### Person D — Data, Agents Panel & Orchestration

| Hour | Deliverable |
|------|-------------|
| 2–4 | Create 2–3 example floor plans as JSON files in `data/`. **This is critical for the demo.** One office plan WITH intentional violations (blocked room, insufficient exits, narrow corridor). One school plan that is mostly clean. Design realistic-looking plans, then hand-write the JSON. These must look good on canvas. |
| 4–5 | `agents/orchestrator.py` — Pipeline class. Methods: `run_parse(image_path)`, `run_validate(plan)`, `run_diagnose(violations)`, `run_propose(plan, violations)`. Each method: updates agent state -> calls the agent -> updates state -> fires callback. Runs agents in background threads so GUI doesn't freeze. |
| 5–6 | `gui/agents_panel.py` — Right panel UI. Four cards (one per agent), each card is a `ttk.LabelFrame` with: agent name, one-line description, state indicator (colored dot/label), last output (truncated, expandable on click), timestamp. Cards update via callbacks from orchestrator. |
| 6–7 | Agent state animations: when an agent is RUNNING, its card shows a "working..." indicator (text changes or indeterminate progress bar). DONE -> flash green. ERROR -> red with error message. |
| 7–8 | Agent inspection: clicking a card opens a `Toplevel` window showing the agent's `agent.md` definition file and its last raw JSON output. Write the 4 `agent.md` files in `data/agent_definitions/`. |

**Test with**: Standalone test script that creates an orchestrator, fires the pipeline with a hardcoded plan, and prints agent state changes.

**EXIT GATE (Hour 8)**: Each person can demo their module independently. GUI shows a rendered floor plan. LLM returns parsed JSON from an image. Validation returns violations from a test plan. Orchestrator fires agents in sequence and updates state.

---

## PHASE 2 — Integration Wave 1 (Hours 8–12) · PAIRED WORK

### Pair A+D — GUI + Orchestration

| Hour | Deliverable |
|------|-------------|
| 8–9 | Wire file picker: selecting a JSON file loads it into schema dataclasses, renders on canvas. Selecting an image triggers PlanParser (via orchestrator). |
| 9–10 | Wire agent cards to orchestrator callbacks. When user clicks "Validate", EgressChecker card goes to RUNNING, canvas shows loading state, then violations render as overlays. |
| 10–11 | Wire metrics bar to validation results. Color-coded violation counts update live. |
| 11–12 | Wire diagnosis view: clicking "Diagnose" triggers EvacDiagnoser, results appear as a scrollable list below canvas or in a pane. Each item clickable -> highlights location on canvas. |

### Pair B+C — LLM + Validation Chain

| Hour | Deliverable |
|------|-------------|
| 8–9 | Test PlanParser output against validation engine. Fix schema mismatches — the LLM output may not perfectly match the schema. Add a `normalize_parsed_plan()` function that coerces LLM output into valid dataclasses (fill defaults, fix types, clamp values). |
| 9–10 | Fine-tune EvacDiagnoser prompt: feed it real validation output, iterate until the plain-language explanation is clear and references specific rooms by name/ID. |
| 10–11 | Fine-tune Redesigner prompt: feed it plan + violations, iterate until fix proposals are specific and actionable ("add exit door on east wall of Room R3 at position [15, 8], width 1.2m"). |
| 11–12 | Add **cached/fallback responses**: for each example floor plan, save a known-good LLM response as a JSON file. If the API is down or rate-limited during demo, load the cached response instead. **This is the demo safety net.** |

**EXIT GATE (Hour 12)**: File picker loads a plan -> renders on canvas -> violations appear as overlays -> diagnosis shows in a list. LLM chain works end-to-end on at least 1 example plan.

---

## PHASE 3 — Full Pipeline (Hours 12–16) · ALL CONVERGE

Everyone works on the same branch now. Frequent commits, frequent pulls.

| Hour | Who | Deliverable |
|------|-----|-------------|
| 12–13 | **ALL** | End-to-end test: file picker -> parse -> render -> validate -> overlays -> diagnose -> propose. Fix every bug that blocks this flow. |
| 13–14 | **A** | Canvas polish: better room labels, door arcs, exit arrows, violation markers with severity colors (red = critical, yellow = warning, green = info). Click a violation marker -> scrolls to that item in diagnosis list. |
| 13–14 | **B** | "Propose Fix" button: triggers Redesigner, results display as a ranked list in diagnosis view area. Each fix proposal shows: what, where, why, priority. |
| 13–14 | **C** | Edge case handling: what if a room has no polygon? What if corridors overlap? What if doors reference nonexistent rooms? Return graceful violations instead of crashing. |
| 13–14 | **D** | Pipeline error handling: if any agent fails, show error in its card, don't crash the app. Allow re-running individual agents. "Reset" button clears all state. |
| 14–15 | **A+D** | Overlay layer toggles: checkboxes in control strip to show/hide violation markers, room labels, occupancy numbers. |
| 14–15 | **B+C** | Test with the 2nd and 3rd example plans. Fix any prompt/validation issues specific to school and hospital layouts. |
| 15–16 | **ALL** | Full run-through of the demo script. Time it. Identify any step that takes too long or looks bad. |

**EXIT GATE (Hour 16)**: Demo script runs start to finish without crashes. All 4 agent cards animate through their states. Violations render on canvas. Diagnosis is readable. Fix proposals appear.

---

## PHASE 4 — Polish & Hardening (Hours 16–20) · PARALLEL

### Person A — Visual Polish
- Better color scheme (dark sidebar, light canvas, accent colors for violations)
- App icon and window title
- Resize handling (responsive three-region layout)
- Loading states (cursor changes, disabled buttons while agents run)
- Tooltips on buttons and violation markers

### Person B — Robustness
- Rate limit handling (queue requests, show "waiting for API" in agent card)
- Timeout handling (agent stuck for >30s -> show error, allow retry)
- Validate that ALL cached/fallback responses still match current schema
- Test with edge-case images (blurry, rotated, partial floor plans)

### Person C — Validation Depth
- Add 2–3 more P118 rules if time allows (min exits per room based on occupancy, emergency lighting requirements)
- Refine severity levels (graduated: critical / major / minor / info)
- Add rule citations: each violation references the specific P118 article number

### Person D — Integration Polish
- Agent run history: store last 3 runs per agent, viewable in inspection window
- Keyboard shortcuts working: `Space` (validate), `D` (diagnose), `R` (reset), `F` (fit-to-window)
- Status bar at bottom: "Ready" / "Parsing floor plan..." / "4 violations found" / etc.
- Pre-load default example plan on app startup (no blank canvas on first open)

**EXIT GATE (Hour 20)**: App looks and feels polished. No crashes on any of the 3 example plans. Cached fallbacks work if API is down.

---

## PHASE 5 — Demo Prep (Hours 20–24) · ALL TOGETHER

| Hour | Activity |
|------|----------|
| 20–21 | **Full demo rehearsal #1.** One person drives, others watch. Time every step. Write down every bug, visual glitch, or awkward pause. |
| 21–22 | **Fix everything from rehearsal.** Priority: crashes > wrong data > visual glitches > nice-to-haves. If a fix is risky, use the cached fallback instead. |
| 22–23 | **Full demo rehearsal #2.** Different person drives. Practice the speaking parts. Make sure the "wow moment" (violations lighting up on canvas) is visually clear on a projector. |
| 23–23:30 | **Prepare backup plan.** If live API fails: cached responses ready, switch in <5 seconds. If parsing fails: start from pre-loaded JSON plan. |
| 23:30–24 | **Final commit. Tag release. Everyone rest before the presentation.** |

---

## Critical Path & Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Gemini free tier rate limit (15 RPM) | Can't demo live parsing | Cache all LLM responses for example plans; load cached if API fails |
| Vision parsing returns bad JSON | Validation and rendering break | Ship with 2-3 hand-crafted JSON plans; live parsing is a stretch goal |
| P118 rules wrong or incomplete | Judges question accuracy | Cite specific P118 article numbers; disclaim "decision support, not certification" |
| Tkinter looks ugly | Bad first impression | Use `ttk` themes (`clam` or `alt`), custom colors, consistent spacing |
| Integration conflicts at hour 12 | Lost time on merge issues | Strict module boundaries; each person owns their folder; only D touches orchestrator |

---

## Parallel Work Visualization

```
Hour  0    2    4    6    8   10   12   14   16   18   20   22   24
      |----|----|----|----|----|----|----|----|----|----|----|----|
A:    [SETUP] [=== GUI Shell ===] [= GUI+Orch =] [= Pipeline =] [Polish] [DEMO]
B:    [SETUP] [=== LLM Agents ==] [= LLM+Valid =] [= Pipeline =] [Robust] [DEMO]
C:    [SETUP] [=== Validation ==] [= LLM+Valid =] [= Pipeline =] [Depth ] [DEMO]
D:    [SETUP] [=== Data+Orch ===] [= GUI+Orch =] [= Pipeline =] [Polish] [DEMO]
      |----|----|----|----|----|----|----|----|----|----|----|----|
Phase: P0     P1 (parallel)   P2 (pairs)  P3 (all)  P4 (par) P5(all)
```

---

## File Ownership

| File / Folder | Owner | Others touch? |
|---------------|-------|---------------|
| `models/` | D (initial), then shared | Everyone reads, nobody else writes |
| `gui/app.py`, `gui/canvas.py`, `gui/controls.py`, `gui/metrics_bar.py` | A | D wires callbacks |
| `gui/agents_panel.py`, `gui/diagnosis_view.py` | D | A helps with layout |
| `llm/gemini_client.py` | B | Nobody else touches |
| `agents/plan_parser.py`, `agents/evac_diagnoser.py`, `agents/redesigner.py` | B | D calls via orchestrator |
| `agents/egress_checker.py`, `agents/orchestrator.py`, `agents/base.py` | D | B implements agent logic |
| `validation/` | C | D calls via egress_checker |
| `data/*.json` | D | B uses for prompt testing |
| `data/agent_definitions/` | B | D displays in UI |
| `config.py` | C (rules), B (API) | Split ownership |
| `main.py` | A | Entry point, kept minimal |
| `tests/` | C | B adds LLM output tests |
