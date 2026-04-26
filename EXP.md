# AgentArchitect — Detailed Code Explanation

**PoliHack v19 | App Development Track**
*Team: The Bity Ministry of Vibes & Prayers*

A desktop platform where civil engineers turn domain knowledge into executable, conversational AI agents — without writing code. Built around Romanian **P118 fire safety regulations**, it demonstrates the transition from raw prompt engineering (L2) to structured agent-based development (L3).

---

## Table of Contents

- [Entry Point](#entry-point)
- [Models Layer](#models-layer)
  - [AgentDefinition](#agentdefinition)
  - [FloorPlan](#floorplan)
  - [Violations](#violations)
  - [Chat](#chat)
- [Engine Layer](#engine-layer)
  - [AgentRunner](#agentrunner)
  - [PromptBuilder](#promptbuilder)
  - [ConversationManager](#conversationmanager)
  - [ResponseCache](#responsecache)
- [Tools Layer](#tools-layer)
  - [ToolRegistry](#toolregistry)
  - [P118 Validator](#p118-validator)
  - [Pathfinding](#pathfinding)
  - [Structural Checker](#structural-checker)
  - [Metrics Calculator](#metrics-calculator)
  - [DXF Parser](#dxf-parser)
  - [Gemini Vision](#gemini-vision)
- [LLM Layer](#llm-layer)
  - [GeminiClient](#geminiclient)
- [Agent Definitions](#agent-definitions)
  - [Floor Plan Parser](#floor-plan-parser)
  - [Egress Validator](#egress-validator)
  - [Evacuation Diagnoser](#evacuation-diagnoser)
  - [Exit Placement Advisor](#exit-placement-advisor)
- [GUI Layer](#gui-layer)
  - [App (Main Window)](#app-main-window)
  - [AgentLibrary (Sidebar)](#agentlibrary-sidebar)
  - [AgentRunnerTab](#agentrunnertab)
  - [AgentBuilderTab](#agentbuildertab)
  - [L2ConsoleTab](#l2consoletab)
  - [AdoptionPanel](#adoptionpanel)
  - [CanvasPanel](#canvaspanel)
- [L2 Prompt Templates](#l2-prompt-templates)
- [Configuration](#configuration)
- [Testing](#testing)

---

## Entry Point

**File:** `main.py`

```python
def main():
    qapp = QApplication(sys.argv)
    qapp.setStyleSheet(get_stylesheet(dark_mode=True))
    app_window = App()
    app_window.show()
    sys.exit(qapp.exec())
```

Creates a PyQt6 `QApplication`, applies the dark theme stylesheet globally, instantiates the `App` main window, and enters the event loop. The path is inserted at line 5 so all project modules resolve correctly regardless of working directory.

---

## Models Layer

All models are Python `dataclass` types with `to_dict()` and `from_dict()` serialization methods. They form the shared data contract between tools, engine, and GUI.

### AgentDefinition

**File:** `models/agent_definition.py`

Defines the schema for an agent — everything needed to execute it.

```python
@dataclass
class AgentInput:
    name: str        # e.g. "floor_plan"
    type: str        # "file", "json", "text", "image"
    description: str # shown in UI placeholder

@dataclass
class AgentOutput:
    name: str        # e.g. "violations"
    type: str        # "json" or "text"
    description: str

@dataclass
class AgentDefinition:
    id: str                              # unique slug, e.g. "floor_plan_parser"
    name: str                            # display name
    category: str                        # "Fire Safety", "Custom"
    goal: str                            # one-sentence purpose
    inputs: List[AgentInput]             # what the user provides
    constraints: List[str]               # numbered rules in system prompt
    outputs: List[AgentOutput]           # what the agent produces
    tools: List[str]                     # tool keys from ToolRegistry
    conversational: bool = True          # enable multi-turn follow-up
    conversation_guidelines: str = ""    # injected into system prompt
```

**Key methods:**

- `load_from_json(filepath)` — reads a JSON file and returns an `AgentDefinition`
- `save_to_json(filepath)` — writes the definition as formatted JSON, creating directories if needed
- `load_all_from_directory(directory)` — scans a directory for `.json` files, returns a list of all valid agent definitions (silently skips malformed files)

Agents from `data/agents/` are pre-built; agents from `user_agents/` are user-created via the Builder tab.

---

### FloorPlan

**File:** `models/floor_plan.py`

The core spatial data model. Every tool and agent operates on this structure.

```python
@dataclass
class Room:
    id: str                                    # "R1", "R2", etc.
    name: str                                  # "Main Office", "Conference Room"
    type: str                                  # "office", "corridor", "stairwell", "wc", "conference", "server"
    polygon: List[Tuple[float, float]]         # vertices in meters — used for canvas rendering + area calc
    area: float                                # square meters
    occupancy: int                             # estimated persons (area / P118 density)
    floor: int                                 # floor number (0-indexed)
```

```python
@dataclass
class Corridor:
    id: str                                    # "C1", "C2"
    name: str
    width: float                               # meters (checked against P118 min 1.4m)
    length: float                              # meters (checked for dead-end limits)
    connects: List[str]                        # IDs of adjacent corridors (open passages)
    polygon: List[Tuple[float, float]]         # for rendering
    floor: int
```

```python
@dataclass
class Door:
    id: str                                    # "D1", "D2"
    connects: List[str]                        # exactly 2 node IDs (room↔corridor, room↔room)
    width: float                               # meters (0.9m min room, 1.2m min exit)
    position: Tuple[float, float]              # (x, y) in meters — for canvas placement
    is_exit: bool                              # True = leads outside
```

```python
@dataclass
class Exit:
    id: str
    room_id: str             # which room/corridor this exit is attached to
    position: Tuple[float, float]
    width: float             # default 1.2m
    leads_outside: bool      # always True for actual exits
```

```python
@dataclass
class Wall:
    id: str
    start: Tuple[float, float]
    end: Tuple[float, float]
    room_id: str             # optional — which room owns this wall
```

```python
@dataclass
class FloorPlan:
    id: str
    name: str
    floor: int
    rooms: List[Room]
    corridors: List[Corridor]
    doors: List[Door]
    exits: List[Exit]
    walls: List[Wall]
```

**Key methods:**

- `total_occupancy()` — sums `room.occupancy` across all rooms
- `get_room(room_id)` / `get_corridor(corridor_id)` — linear search by ID
- `load_from_json(filepath)` — reads JSON, delegates to `from_dict()` which recursively deserializes all nested objects
- `save_to_json(filepath)` — inverse

**Graph topology:** The floor plan is a graph where **rooms and corridors are nodes**, **doors are edges** (each door connects exactly 2 nodes), and **exits are terminal markers** on specific nodes. The pathfinding tool builds an adjacency graph from this structure.

---

### Violations

**File:** `models/violations.py`

```python
@dataclass
class Violation:
    id: str                      # "V001", "V002" (auto-incremented)
    rule: str                    # "travel_distance", "door_width", "exit_count"
    article: str                 # "P118 Art. 3.6.4"
    severity: str                # "critical", "major", "minor", "info"
    location: str                # room/corridor ID or "building"
    description: str             # human-readable explanation
    measured_value: float        # actual value (e.g. 35.2m travel distance)
    threshold_value: float       # P118 limit (e.g. 30.0m)
```

`to_dict()` omits `measured_value` and `threshold_value` if they are `None` — this keeps the JSON clean for violations that don't have numeric measurements (e.g., "no doors found").

```python
@dataclass
class DiagnosisResult:
    violation_id: str
    explanation: str        # plain-language for non-specialists
    impact: str             # "what happens in a fire"
    severity_rank: int      # 1 = most urgent
    affected_occupants: int
```

```python
@dataclass
class FixProposal:
    id: str
    target_violation: str        # violation ID this fixes
    description: str             # "Add exit door on south wall of R3"
    justification: str           # why this helps
    estimated_effort: str        # "low", "medium", "high"
    impact_score: float          # higher = more effective
    resolves_violations: List[str]  # which violation IDs are resolved
```

```python
@dataclass
class MetricsReport:
    total_violations: int
    critical_count: int
    major_count: int
    minor_count: int
    info_count: int
    compliance_score: float   # 0-100
    pass_fail: str            # "PASS" or "FAIL"
```

---

### Chat

**File:** `models/chat.py`

```python
@dataclass
class ChatMessage:
    role: str        # "user" or "agent"
    content: str
    timestamp: str   # ISO format, auto-filled in __post_init__

@dataclass
class AgentResult:
    agent_id: str
    success: bool
    outputs: dict              # parsed JSON outputs keyed by output name
    explanation: str           # full LLM response text
    tool_results: dict         # raw tool output strings keyed by tool name
    error: Optional[str]       # error message if success=False
```

`AgentResult` is the return type of `AgentRunner.run_agent()`. It carries everything: the structured outputs, the raw LLM explanation, the tool results that fed the LLM, and any error.

---

## Engine Layer

### AgentRunner

**File:** `engine/runner.py`

The core execution engine. Orchestrates the full agent pipeline.

**Constructor:**

```python
def __init__(self, gemini_client=None):
    self.client = gemini_client or GeminiClient()
    self.prompt_builder = PromptBuilder()
    self.registry = ToolRegistry()
    self.cache = ResponseCache()
    self.cache_validation_report = self.cache.validate_all_cached_responses()
```

On init, it validates all cached responses and stores a report. This catches corrupted cache files at startup.

**`run_agent(definition, inputs, status_callback)` — the main pipeline:**

```
1. _run_tools()    → execute each tool in definition.tools → collect JSON results
2. build_system_prompt() → assemble system prompt from definition + tool results
3. build_user_prompt()   → format user inputs as "[name]:\nvalue" pairs
4. send_with_context()   → call Gemini API with system + user prompt
5. _parse_outputs()      → extract JSON blocks from LLM response
6. Return AgentResult
```

**Fallback chain (line 57-82):**

If the LLM response starts with `[Error`, the runner:
1. Checks if "timeout" is in the error message
2. Tries `cache.get_cached_result(agent_id, inputs)` — hash-based lookup
3. If cache hit: injects fresh `tool_results`, re-parses outputs if empty, returns cached result
4. If cache miss: returns failed `AgentResult` with the error

**`_run_tools(definition, inputs, _status)` (line 119-139):**

Iterates `definition.tools`, looks up each tool function from `ToolRegistry`, calls it with a merged input dict. Results are JSON-serialized into `tool_results`. Errors are caught per-tool and stored as `{"error": "..."}`.

**`_prepare_tool_input(inputs)` (line 141-153):**

User inputs come as `Dict[str, str]` (raw text from UI). This method tries to `json.loads()` each value — if it parses as a dict, it merges into the tool input. This means when a user provides a floor plan JSON file, the file contents get parsed and flattened into the tool input dict.

**`_parse_outputs(response, definition)` (line 155-200):**

Extracts structured JSON from the LLM response using a three-pass strategy:

1. **Find JSON blocks** — regex `r'```(?:json)?\s*([\s\S]*?)\s*```'` extracts fenced code blocks. If none found, treats the entire response as a block.
2. **Match named outputs** — for each parsed JSON object, checks if it contains keys matching `definition.outputs[].name`. If `"parsed_plan"` is an expected output and the JSON has a `"parsed_plan"` key, it's assigned.
3. **Assign remaining** — unmatched expected outputs get assigned in order from unused JSON objects.
4. **Leftovers** — any extra JSON objects get generic keys like `"json_output_0"`.

**`run_agent_async(definition, inputs, callback, status_callback)` (line 96-117):**

Wraps `run_agent()` in a daemon thread. Calls `callback(result)` when done. Used by the GUI to avoid blocking the UI thread.

---

### PromptBuilder

**File:** `engine/prompt_builder.py`

Assembles LLM prompts from agent definitions. Also handles domain validation and follow-up relevance checking.

**`build_system_prompt(definition, tool_results)` (line 203-311):**

Constructs a multi-section system prompt:

```
1. Identity:     "You are the '{name}' agent on the AgentArchitect platform."
2. Goal:         "Your goal: {goal}"
3. Mode:         "L3 AGENT MODE: structured outputs, tool-grounded reasoning"
4. Topic guard:  "If the user asks about anything unrelated to civil engineering... decline"
5. Constraints:  Numbered list from definition.constraints
6. Inputs:       Expected input names and types
7. Outputs:      Expected output names and types
8. JSON format:  "Wrap JSON in ```json code blocks. Ensure valid JSON."
9. Tool results: Injected verbatim with tool names as headers
10. Tool rules:  "Cite the tool name. Quote specific values. Do NOT invent violations."
11. Conversation: Guidelines + scope boundaries (in-scope vs out-of-scope)
12. Scope map:   Per-agent scope boundaries from AGENT_SCOPE_MAP
13. Behavior:    Proactive flagging, pushback handling, coherent follow-ups
```

**`AGENT_SCOPE_MAP` (line 143-196):**

Hard-coded dict mapping each agent ID to what it can and cannot do:

```python
"floor_plan_parser": {
    "in_scope": ["Parsing floor plan images...", "Identifying rooms...", ...],
    "out_of_scope": {
        "compliance checking or P118 validation": "Egress Validator",
        "violation explanation or safety impact": "Evacuation Diagnoser",
        "fix proposals or exit placement": "Exit Placement Advisor",
    },
}
```

When a user asks the Floor Plan Parser about compliance, the agent redirects: "That's outside my role — use the Egress Validator agent."

**`validate_domain_relevance(name, goal, constraints)` (line 48-74):**

Two regex patterns:
- `_DOMAIN_KEYWORDS` — matches civil engineering terms (floor plan, fire, egress, P118, structural, hvac, etc.)
- `_OFFTOPIC_KEYWORDS` — matches clearly off-topic terms (recipe, movie, crypto, dating, etc.)

Logic:
1. If off-topic keywords found → reject ("This agent appears to be about non-engineering topics")
2. If no domain keywords found → reject ("Could not identify a civil-engineering purpose")
3. Otherwise → accept

Used by the Agent Builder to prevent creation of off-topic agents.

**`check_followup_relevance(user_message, agent_goal)` (line 115-140):**

Fast keyword gate for follow-up messages:

- If off-topic keywords found and no domain keywords → `"block"` (immediate reject)
- If domain keywords found → `"allow"`
- If short conversational phrase (yes/no/ok/thanks) → `"allow"`
- If references prior context (your findings, how can I fix) → `"allow"`
- Otherwise → `"uncertain"` (needs LLM classification)

---

### ConversationManager

**File:** `engine/conversation.py`

Manages multi-turn conversations after the initial agent run.

**State:**

```python
self.definition        # AgentDefinition (for scope checking)
self.client            # GeminiClient
self.history           # List[ChatMessage] — full conversation
self.system_prompt     # from initial run
self.tool_results      # from initial run
self._inputs           # original user inputs (for cache lookup)
self._last_user_message  # for retry
```

**`initialize(system_prompt, initial_response, tool_results, inputs)` (line 44-56):**

Called after the first agent run. Stores the system prompt and initial response. Clears any prior history and starts fresh with the agent's initial response as the first message.

**`followup(user_message, status_callback)` (line 62-127):**

1. Check turn count against `MAX_TURNS = 10` — if exceeded, returns limit message
2. Append user message to history
3. Run `check_followup_relevance()` — if "block", return refusal immediately
4. If "uncertain", call `_classify_relevant()` — asks the LLM "Is this on-topic? YES or NO"
5. Build `history_dicts` from all prior messages (excluding the new one)
6. Call `client.send_with_context()` with system prompt + history + new message
7. If LLM returns error, try `cache.get_cached_followup()` with fuzzy matching
8. Append response to history, return it

**`_classify_relevant(user_message)` (line 143-156):**

Sends a minimal prompt to the LLM:
```
"Is the following user message related to civil engineering...?
Agent purpose: {goal}
User message: "{message}"
Answer YES or NO:"
```

Parses the first word of the response. On error, defaults to `True` (allow) — fails open to avoid blocking legitimate questions.

**`retry_last_followup()` (line 129-141):**

Pops the last user+agent message pair from history, then re-calls `followup()` with the same user message. Used when the API timed out.

---

### ResponseCache

**File:** `engine/cache.py`

Hash-based caching for demo safety. Two classes: `ResponseCache` (L3 agents) and `L2ResponseCache` (L2 templates).

**`_input_hash(inputs)` (line 22-35):**

1. For each input value: try `json.loads()` → normalize with `json.dumps(sort_keys=True, separators=(",",":"))`
2. Sort all normalized values
3. Join with `\0` separator
4. MD5 hash → first 12 hex chars

This ensures the same floor plan JSON produces the same hash regardless of key ordering or whitespace.

**Cache key format:** `{agent_id}_{input_hash}.json` — e.g., `egress_validator_9bfee7beca1b.json`

**Cache file schema:**

```json
{
  "agent_id": "egress_validator",
  "input_hash": "9bfee7beca1b",
  "initial_response": "Full LLM response text...",
  "outputs": { "violations": [...], "compliance_summary": "..." },
  "tool_results": { "p118_validator": "...", "pathfinding": "..." },
  "followups": [
    { "question": "Which violation is most critical?", "response": "The blocked room..." }
  ]
}
```

**`get_cached_followup()` (line 63-82):**

Uses `_fuzzy_match()` — compares word sets between the user's question and each cached question. If >50% of the cached question's words appear in the user's question, it's a match. This allows questions like "what's the worst violation?" to match "which violation is most critical?"

**`validate_all_cached_responses()` (line 139-168):**

Called at startup by `AgentRunner.__init__()`. Iterates every `.json` file in `data/cache/`, validates schema (required fields, correct types), and reports any issues. Also validates L2 cache files.

---

## Tools Layer

### ToolRegistry

**File:** `tools/registry.py`

Singleton pattern — all tools registered once, accessible globally.

```python
class ToolRegistry:
    _instance = None
    _tools: Dict[str, ToolInfo] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._tools = {}
            cls._instance._register_defaults()
        return cls._instance
```

**`_register_defaults()` (line 25-134):**

Registers 6 tools:

| Key | Function | Description |
|-----|----------|-------------|
| `gemini_vision` | `gemini_vision_parse()` | Parse floor plan images via Gemini Vision API |
| `p118_validator` | `validate_p118()` | 8 P118 compliance checks |
| `pathfinding` | `find_all_travel_distances()` | Dijkstra evacuation paths |
| `structural_checker` | `structural_check_all()` | Combined: blocked rooms + dead ends + anomalies |
| `metrics` | `compute_metrics()` | Violation counting + compliance scoring |
| `dxf_parser` | `parse_dxf()` | DXF file → FloorPlan JSON |

**Wrapper functions defined inline:**

- `structural_check_all(inputs)` — calls `detect_blocked_rooms`, `detect_dead_ends`, `detect_anomalies` sequentially, catches per-function errors
- `gemini_vision_parse(inputs)` — validates image path, checks file extension, calls `GeminiClient.parse_image()`
- `parse_dxf(inputs)` — calls `extract_entities()` then `build_floor_plan()`, returns `{"parsed_plan": ..., "flagged_issues": ...}`

**`get_tool(key)`** — returns the callable function, or `None` if not found. The `AgentRunner` uses this to look up tools by name from agent definitions.

---

### P118 Validator

**File:** `tools/p118_validator.py`

Implements 8 Romanian P118 fire safety regulation checks. Each check function takes the floor plan as a dict and returns a list of `Violation` dicts.

**`validate_p118(inputs)` (line 50-86):**

Entry point. Resets the global violation counter, then calls all 8 check functions in sequence. Catches exceptions per-check (so one failing check doesn't stop the others) and appends an info-level "check failed" violation.

**Check 1: `_check_travel_distance()` (line 89-150)**

*P118 Art. 3.6.4 — Max 30m general, 20m dead-end*

1. Calls `find_all_travel_distances()` to get `{room_id: distance}` for every room
2. Builds the pathfinding graph to identify dead-end rooms (rooms with ≤1 neighbor)
3. For each room:
   - `inf` distance → critical "no reachable exit"
   - Dead-end room over 20m → critical
   - Normal room over 30m → critical
   - Otherwise → `_borderline_check()` for values within 10% of threshold

**Check 2: `_check_exit_capacity()` (line 153-215)**

*P118 Art. 3.6.9 — Max 80 persons per 1m exit width*

1. Computes total building occupancy and total exit width
2. If total occupancy > total capacity → critical
3. Also checks individual exits against the occupancy of the room they directly serve

**Check 3: `_check_door_widths()` (line 218-272)**

*P118 Art. 3.6.11 — Min 0.9m room doors, 1.2m exit doors*

Iterates all doors and exits. Exit doors below 1.2m → critical. Room doors below 0.9m → major. Also checks the `exits` list separately (exits have their own width field).

**Check 4: `_check_corridor_widths()` (line 275-316)**

*P118 Art. 3.6.12 — Min 1.4m corridor width*

Below 1.4m → major. Between 1.4m and 1.54m (within 10% tolerance) → info borderline.

**Check 5: `_check_dead_ends()` (line 319-354)**

*P118 Art. 3.6.5 — Max 12m dead-end corridor*

Builds the graph, identifies corridors with no other corridor neighbors. If such a corridor exceeds 12m → major.

**Check 6: `_check_exit_count()` (line 357-386)**

*P118 Art. 3.6.2 — Min 2 exits for occupancy > 50*

Simple: count exits, sum occupancy. If occupancy > 50 and exits < 2 → critical.

**Check 7: `_check_room_exit_count()` (line 389-432)**

*P118 Art. 3.6.3 — Rooms with occupancy ≥ 50 need 2+ exits*

For each high-occupancy room, counts its graph neighbors (i.e., doors). If < 2 → critical. For rooms approaching 50 occupancy → borderline check.

**Check 8: `_check_emergency_lighting()` (line 435-493)**

*P118 Art. 4.2.1 — Emergency lighting for rooms ≥ 30 occupancy, corridors ≥ 10m*

Checks `emergency_lighting` boolean field on rooms and corridors. If missing/false on qualifying spaces → major.

**`_borderline_check()` (line 497-536):**

Flags values within `P118_BORDERLINE_TOLERANCE` (10%) of a threshold:

- `is_min=False` (approaching max): flags if `threshold < value <= threshold * 1.1`
- `is_min=True` (approaching min): flags if `threshold * 0.9 <= value < threshold`

Returns an `info`-severity violation with "BORDERLINE:" prefix.

---

### Pathfinding

**File:** `tools/pathfinding.py`

Dijkstra's algorithm on the floor plan graph. The critical tool for travel distance calculations.

**`_build_graph(plan_data)` (line 29-76):**

Constructs a weighted adjacency graph:

1. **Nodes** — every room ID + every corridor ID
2. **Edges from doors** — each door's `connects` list links two nodes. Weight = Euclidean distance between polygon centroids.
3. **Edges from corridor.connects** — open passages between corridors (no door required). Only corridor-to-corridor connections, not corridor-to-room.

Key constraint: **rooms connect to corridors only through doors**. This models physical passageways correctly — you can't walk from a room into a corridor without a door.

**`_centroid(polygon)` (line 15-21):**

Average of all vertex coordinates. Used as the representative point for distance calculations.

**`_dijkstra(graph, start, targets)` (line 92-133):**

Standard min-heap Dijkstra. Returns `(distance, path)` where `path` is the list of node IDs from start to the nearest target. Returns `(float('inf'), [])` if no target is reachable.

Special case: if `start` is already in `targets` → returns `(0.0, [start])`.

**`_find_exit_nodes(plan_data)` (line 79-89):**

Scans the `exits` list and returns a set of `room_id` values — these are the target nodes for Dijkstra.

**`find_all_travel_distances(inputs)` (line 176-194):**

The main function called by the P118 validator. Returns `{room_id: distance}` for every room. Rooms with no path get `float('inf')`.

**`find_shortest_exit_path(inputs, room_id)` (line 148-173):**

Returns `(distance, path)` for a specific room. Used by the Exit Placement Advisor to evaluate fix proposals.

---

### Structural Checker

**File:** `tools/structural_checker.py`

Three sub-checks for structural anomalies.

**`detect_blocked_rooms(inputs)` (line 64-110):**

Uses Dijkstra to find rooms with no path to any exit. If the building has zero exits, every room is blocked. Otherwise, checks each room individually. Blocked rooms → critical severity.

**`detect_dead_ends(inputs)` (line 113-166):**

Builds the graph, identifies corridors whose only neighbors are rooms (no connections to other corridors or exit nodes):
- Zero corridor/exit neighbors → "isolated" (major)
- Exactly one corridor/exit neighbor and not itself an exit → "dead-end" (major if >12m, minor otherwise)

**`detect_anomalies(inputs)` (line 169-314):**

Multiple sub-checks:

1. **Missing polygons** — rooms with <3 vertices → minor
2. **Invalid area** — rooms with area ≤ 0 → info
3. **Zero-width corridors** — width ≤ 0 → minor
4. **Zero-length corridors** — length ≤ 0 → info
5. **Overlapping spaces** — bounding-box overlap test with >10% overlap threshold → minor
6. **Sealed rooms** — rooms not referenced by any door's `connects` list → critical (occupants trapped)
7. **Invalid door references** — doors referencing nonexistent room/corridor IDs → minor

The bounding-box overlap test (`_bboxes_overlap`) computes overlap area as a fraction of the smaller space's area.

---

### Metrics Calculator

**File:** `tools/metrics.py`

Aggregates violation statistics.

**`compute_metrics(inputs)` (line 23-69):**

Accepts violations as either:
- A raw `list` of violation dicts
- A `dict` with key `"violations"` containing the list
- A single violation dict (has "severity" key)

Counts violations by severity, computes compliance score:

```
score = max(0, 100 - 25*critical - 10*major - 3*minor - 1*info)
```

Pass/fail: `"PASS"` only if zero critical and zero major violations.

Returns a `MetricsReport` dict.

---

### DXF Parser

**File:** `tools/dxf_parser.py`

Converts AutoCAD DXF files into `FloorPlan` objects using the `ezdxf` library.

**Layer recognition constants (line 11-16):**

```python
ROOM_LAYERS = {"A-ROOM", "ROOM", "ROOMS", "A-AREA", "SPACE"}
CORRIDOR_LAYERS = {"A-CORRIDOR", "CORRIDOR", "CORRIDORS", "HALL", "HALLWAY"}
WALL_LAYERS = {"A-WALL", "WALL", "WALLS", "S-WALL", "AR-WALL"}
DOOR_LAYERS = {"A-DOOR", "DOOR", "DOORS", "AR-DOOR"}
TEXT_LAYERS = {"A-TEXT", "TEXT", "ANNO", "A-ANNO", "LABEL"}
```

**`extract_entities(dxf_path)` (line 27-144):**

Reads the DXF file and categorizes entities:

| Entity Type | Extraction Logic |
|-------------|-----------------|
| `LWPOLYLINE` | Extract (x,y) vertices, check `closed` flag |
| `POLYLINE` | Extract vertices from sub-entities |
| `SPLINE` | Flatten to polyline with `distance=1.0` tolerance |
| `LINE` | Extract start and end points |
| `CIRCLE`/`ARC` | Extract center, radius, angles |
| `TEXT`/`MTEXT` | Extract content string and position |
| `HATCH` | Extract boundary paths as polylines |
| `INSERT` | Record block name and position; recurse into virtual sub-entities |

The function processes both the modelspace and all layouts (except "model").

Returns:
```python
{
    "polylines": [...],  # closed/open polygon data
    "lines": [...],      # wall segments
    "arcs": [...],       # door arcs
    "texts": [...],      # labels
    "blocks": [...],     # block references
    "layers": [...]      # all unique layer names found
}
```

**`build_floor_plan(entities)` (line 147-299):**

Converts extracted entities into a `FloorPlan`:

1. **Room/corridor classification** — closed polylines are classified based on:
   - Layer name matching (e.g., `A-CORRIDOR` → corridor)
   - Aspect ratio ≥ 3.0 → corridor (long and narrow)
   - Nearest text label (via `_nearest_label` — point-in-polygon test)
   - Keyword matching in label text (`_classify_room_type`)

2. **Occupancy estimation** — `_estimate_occupancy(area, room_type)` uses P118 density tables from `config.py`:
   ```
   office: 10 m²/person, conference: 2, corridor: 999 (exempt), wc: 20, server: 20
   ```

3. **Wall creation** — each `LINE` entity becomes a `Wall`

4. **Door detection** — arcs are treated as door swings:
   - Width = radius × 2
   - `_nearest_spaces(center, space_polys)` finds the two closest rooms/corridors
   - If only one nearby space → `is_exit = True`

5. **Block-based doors** — `INSERT` entities with "door" in name or on door layers:
   - Same nearest-space logic for connectivity
   - "exit" in name → exit door

6. **Exit generation** — every door with `is_exit=True` gets an `Exit` object

7. **Issue flagging:**
   - Rooms with no door connections
   - Overlapping room polygons (`_polygons_overlap` — vertex-in-polygon test)
   - Unmatched text labels
   - No rooms/corridors/walls detected at all
   - Open (unclosed) polylines on room layers

**Helper functions:**

- `_polygon_area(vertices)` — shoelace formula for area calculation
- `_point_in_polygon(point, polygon)` — ray casting algorithm
- `_nearest_label(polygon, texts)` — finds text labels inside a polygon's bounding box, then verifies with point-in-polygon
- `_nearest_spaces(point, spaces)` — sorts all spaces by centroid distance, returns closest 2

---

### Gemini Vision

Defined inline in `tools/registry.py` as `gemini_vision_parse()` (line 43-67).

1. Validates image path exists and has an image extension
2. Creates a `GeminiClient`
3. Sends a detailed prompt asking for rooms, corridors, doors, exits, stairs, and unusual features
4. Returns `{"vision_analysis": result_text}`

Used by the Floor Plan Parser agent as a fallback when the input is an image instead of a DXF/JSON file.

---

## LLM Layer

### GeminiClient

**File:** `llm/gemini_client.py`

Wraps the Google Generative AI SDK with retry logic, timeout handling, and multi-mode support.

**Configuration:**

```python
MAX_RETRIES = 3
RETRY_BASE_DELAY = 2              # seconds, doubles each retry
REQUEST_TIMEOUT_SECONDS = 30
VISION_TIMEOUT_SECONDS = 90
MODEL = "gemma-3-27b-it"          # text/chat model
VISION_MODEL = "gemini-2.5-flash" # vision model
```

**`_ensure_init()` (line 27-34):**

Lazy initialization — creates the `genai.Client` on first use with the API key from `config.py`. Only initializes once.

**`_call_with_retry(fn, *args, timeout_seconds, status_callback)` (line 58-94):**

Core retry wrapper:

1. Wraps the function call in a `ThreadPoolExecutor` with a timeout (using `future.result(timeout=...)`)
2. If `FuturesTimeoutError` → return `"[Error: Timeout after Xs]"`
3. On exceptions: check error string for `429`, `resource`, `quota`, `500`, `503`
   - If transient → exponential backoff: sleep `2^attempt × 2` seconds, retry
   - If non-transient → return `"[Error: {e}]"` immediately
4. After 3 retries → return `"[Error: API failed after 3 retries...]"`

**`_response_text(response)` (line 36-56):**

Extracts text from the Gemini response object. Tries `response.text` first, then iterates `response.candidates[].content.parts[].text`. Falls back to `str(response)`.

**Three modes:**

**L2 Mode: `send_prompt(prompt_text)` (line 98-114)**

Single-shot text generation. No system prompt, no history. Uses `generate_content()` with `temperature=0.4, max_output_tokens=4096`.

**L2 Template Mode: `send_with_template(template_path, data)` (line 116-161)**

1. Reads the markdown template file
2. Replaces `{{DATA}}` with the user's data
3. Prepends L2 guardrails: "Single-shot only. Plain text only. No JSON. No tools."
4. Calls `send_prompt()`
5. On error → tries `L2ResponseCache.get_cached(template_name, data)`

**L3 Mode: `send_with_context(system_prompt, user_message, history)` (line 165-217)**

Full conversational mode with system prompt and chat history.

Special handling for Gemma models (`"gemma" in MODEL.lower()`):
- Gemma doesn't support `system_instruction` — instead, the system prompt is prepended to the first user message as `"System Instructions:\n{system_prompt}\n\nUser Input:\n{message}"`
- For non-Gemma models (like Gemini Flash), `system_instruction` is passed in the config

Creates a `chats.create()` session with full history, then sends the new message via `chat.send_message()`.

**Vision Mode: `parse_image(image_path, prompt)` (line 221-249)**

Opens the image with PIL, converts to RGB if needed, sends `[prompt, img]` to the vision model with `temperature=0.3`.

---

## Agent Definitions

JSON files in `data/agents/`. Each is loaded as an `AgentDefinition` and drives the entire agent execution pipeline.

### Floor Plan Parser

**File:** `data/agents/floor_plan_parser.json`

```json
{
  "id": "floor_plan_parser",
  "name": "Floor Plan Parser",
  "category": "Fire Safety",
  "goal": "Convert a floor plan file (image, PDF, or DXF) into a structured JSON representation that other agents in the pipeline can consume",
  "inputs": [{"name": "floor_plan", "type": "file", "description": "Floor plan file (.json, .dxf, or image/PDF)"}],
  "constraints": [
    "Identify all rooms, corridors, doors, exits, and stairs",
    "Classify rooms by type (office, corridor, stairwell, etc.)",
    "Estimate occupancy based on room type and area (P118 density tables)",
    "Flag ambiguous or unusual features for engineer review",
    "For DXF files, use the dxf_parser tool for precise extraction. For images/PDFs, fall back to gemini_vision.",
    "Your response MUST be a complete parsed_plan JSON block... sole deliverable",
    "Do NOT include human-readable summaries, prose explanations, or commentary. Output only valid JSON."
  ],
  "outputs": [
    {"name": "parsed_plan", "type": "json", "description": "Structured floor plan JSON..."},
    {"name": "flagged_issues", "type": "json", "description": "List of ambiguities..."}
  ],
  "tools": ["dxf_parser", "gemini_vision"],
  "conversational": false,
  "conversation_guidelines": "Output only valid JSON. No prose, no summaries, no commentary."
}
```

**Unique properties:** `conversational: false` — this is the only non-conversational agent. Its output is purely JSON, consumed programmatically by downstream agents.

**Tool execution flow:**
1. If input is `.dxf` → `dxf_parser` tool extracts entities and builds FloorPlan
2. If input is image → `gemini_vision` tool sends to Gemini Vision API
3. If input is `.json` → passed directly as tool input (tools parse the JSON)

---

### Egress Validator

**File:** `data/agents/egress_validator.json`

```json
{
  "id": "egress_validator",
  "goal": "Check a parsed floor plan against Romanian P118 fire safety regulations and report all violations",
  "inputs": [{"name": "parsed_plan", "type": "json"}],
  "constraints": [
    "Max travel distance to nearest exit: 30m (normal), 20m (dead-end)",
    "Min door width: 0.9m (rooms), 1.2m (exits)",
    "Min corridor width: 1.4m",
    "Max dead-end corridor length: 12m",
    "Exit capacity: 80 persons per 1m of exit width",
    "Min 2 exits per floor for occupancy > 50"
  ],
  "outputs": [
    {"name": "violations", "type": "json"},
    {"name": "compliance_summary", "type": "text"}
  ],
  "tools": ["p118_validator", "pathfinding", "structural_checker"],
  "conversational": true
}
```

**Tool execution flow:**
1. `p118_validator` — runs all 8 P118 checks, returns violation list
2. `pathfinding` — computes travel distances for every room
3. `structural_checker` — detects blocked rooms, dead ends, anomalies

All three tool results are injected into the system prompt. The LLM then produces a compliance summary interpreting the tool data — it cites specific tool findings rather than inventing violations.

---

### Evacuation Diagnoser

**File:** `data/agents/evacuation_diagnoser.json`

```json
{
  "id": "evacuation_diagnoser",
  "goal": "Explain fire safety violations in plain language, rank by severity, and assess impact on building occupants",
  "inputs": [
    {"name": "violations", "type": "json"},
    {"name": "parsed_plan", "type": "json", "description": "Original parsed floor plan for context (optional)"}
  ],
  "constraints": [
    "Explain each violation in terms a non-specialist architect can understand",
    "Rank violations by real-world impact on occupant safety",
    "Reference specific rooms, corridors, and exits by name",
    "Distinguish between life-safety-critical and code-compliance issues"
  ],
  "outputs": [{"name": "diagnosis", "type": "json"}],
  "tools": ["metrics"],
  "conversational": true
}
```

**Tool execution flow:**
1. `metrics` — computes violation counts, compliance score, pass/fail

The LLM uses the metrics data to rank and explain violations. The constraints force it to distinguish between truly dangerous issues (blocked rooms, no exits) and paperwork compliance issues (borderline measurements).

---

### Exit Placement Advisor

**File:** `data/agents/exit_placement_advisor.json`

```json
{
  "id": "exit_placement_advisor",
  "goal": "Suggest optimal fire exit locations and plan modifications to resolve violations",
  "inputs": [
    {"name": "parsed_plan", "type": "json"},
    {"name": "violations", "type": "json"}
  ],
  "constraints": [
    "Proposed fixes must comply with all P118 constraints",
    "Minimize structural changes (prefer adding doors over moving walls)",
    "Consider cost and feasibility of each proposal",
    "Rank proposals by impact-to-effort ratio",
    "Never auto-apply changes: present as recommendations for engineer review"
  ],
  "outputs": [
    {"name": "fix_proposals", "type": "json"},
    {"name": "remaining_violations", "type": "json"}
  ],
  "tools": ["pathfinding", "p118_validator"],
  "conversational": true
}
```

**Tool execution flow:**
1. `pathfinding` — current travel distances (to identify worst rooms)
2. `p118_validator` — current violations (to verify what needs fixing)

The LLM proposes modifications (add exit here, widen door there) and explains which violations each proposal resolves. The conversation guidelines specify: when the engineer pushes back ("Can't add a south exit"), offer alternative approaches.

---

## GUI Layer

### App (Main Window)

**File:** `gui/app.py`

`QMainWindow` subclass. Coordinates all UI components.

**Layout structure:**

```
QMainWindow
└── central_widget (QWidget)
    ├── header (QFrame, 48px)  →  [☰] [icon] [AgentArchitect] [Engineering Agent Platform]
    ├���─ body (QWidget)
    │   ├── sidebar_frame (QFrame, 280px)
    │   │   ├── AgentLibrary
    │   │   └── nav_frame (Legacy Prompting, Legacy→Agent buttons)
    │   └── right_frame (QFrame)
    │       ├── pages (QStackedWidget)
    │       │   ├── [0] AgentRunnerTab
    │       │   ├── [1] AgentBuilderTab
    │       │   ├── [2] L2ConsoleTab
    │       │   └── [3] AdoptionPanel
    │       ��── CanvasPanel
    └── StatusBar
```

**Sidebar toggle (line 221-244):**

Animated with `QPropertyAnimation` on `minimumWidth` and `maximumWidth`. Easing: `InOutCubic`, duration: 200ms. Toggles between 280px (expanded) and 0px (collapsed).

**Page visibility logic (line 255-260):**

Canvas panel is only visible when the Runner tab is active. When switching to Builder, L2 Console, or Adoption Panel, the canvas hides.

**Keyboard shortcuts (line 167-174):**

| Shortcut | Action |
|----------|--------|
| `Ctrl+N` | Create new agent |
| `Ctrl+S` | Save agent (Builder tab) |
| `Ctrl+Q` | Quit |
| `Ctrl+R` | Run agent |
| `Ctrl+E` | Export JSON |
| `F5` | Refresh agent library |
| `Ctrl+B` | Toggle sidebar |

**Splash screen (line 179-182):**

`SplashOverlay` is created on top of the central widget, plays a loading animation, then auto-destroys. The `resizeEvent` keeps the splash sized to the window.

**`_preload_example_plan()` (line 293-300):**

Loads `data/floor_plans/example_office.json` into the canvas on startup so the canvas panel isn't empty.

---

### AgentLibrary (Sidebar)

**File:** `gui/agent_library.py`

**`refresh()` (line 120-124):**

Loads agents from both `data/agents/` and `user_agents/`, concatenates them, renders the list.

**`AgentCard` (line 18-69):**

Custom `QPushButton` subclass (56px height) showing agent name + goal summary + status dot (green for built-in, blue for custom). Hover effect changes text color to black.

**`_render_list(agents)` (line 134-158):**

Groups agents by category, sorts categories (Fire Safety first, Custom second, others alphabetically). Creates category headers and agent cards.

**`_filter_agents(text)` (line 164-182):**

Real-time filtering as the user types in the search bar. Matches against agent name, goal, and category. Hides non-matching cards and empty category headers.

---

### AgentRunnerTab

**File:** `gui/agent_runner.py` (~998 lines)

The largest GUI module. Handles agent execution, output display, and conversation.

**Thread workers (line 32-98):**

Three `QThread` subclasses for non-blocking execution:

- `AgentRunnerWorker` — calls `engine.run_agent()`, emits `completed(AgentResult)` and `status_update(str)` signals
- `AgentFollowupWorker` — calls `conversation.followup()`, emits `completed(str)`
- `AgentRetryWorker` — calls `conversation.retry_last_followup()`, emits `completed(str)`

**`load_agent(agent_def)` (line 525-587):**

Called when user clicks an agent card in the sidebar:

1. Stores `current_agent`, resets all state
2. Updates header labels (name, goal)
3. Shows/hides delete button (only for user agents in `user_agents/`)
4. Renders constraints list
5. **Dynamically generates input widgets** based on `agent_def.inputs`:
   - `type="file"` or `type="image"` → `QLineEdit` + `[Browse]` button
   - `type="json"` → `QLineEdit` + `[Browse]` button (opens JSON file dialog)
   - Other → `QLineEdit` only

**`_run_agent()` (line 774-804):**

1. Collects inputs from widgets via `_collect_inputs()`
2. Validates required inputs
3. Clears output and chat, shows progress bar
4. Spawns `AgentRunnerWorker` thread
5. Connects `status_update` → updates status indicator + appends status to chat
6. Connects `completed` → `_on_run_complete()`

**`_collect_inputs()` (line 656-673):**

For each input widget:
- If value is a file path ending in `.json` → reads file contents as the input value
- If value is a file path ending in `.dxf` → passes the path string directly
- Otherwise → passes the raw text

**`_on_run_complete(result)` (line 806-841):**

1. On failure: shows error in chat, disables conversation
2. On success:
   - Displays `result.outputs` as formatted JSON in the output panel
   - Appends `result.explanation` (full LLM response) to chat
   - For floor plan parser: shows a conversion banner with extraction counts
   - Initializes `ConversationManager` with system prompt and initial response
   - Enables chat input
   - Renders results on canvas via `_show_on_canvas()`

**Chat message formatting (line 302-461):**

`_format_agent_message()` processes agent responses:

1. Extracts ````json` blocks → parses JSON → converts to human-readable report via `_json_to_report()`
2. Escapes HTML in remaining text
3. `_inject_location_links()` — converts room/corridor IDs (R1, C2, D3, E1) to clickable links. Clicking jumps to that location on the canvas.
4. `_inject_severity_colors()` — colorizes severity words (critical=red, major=orange, minor=yellow, info=gray)

**`_json_to_report(data)` (line 404-435):**

Recursively converts nested JSON into indented report lines:
- Dict → "Key: Value" lines (keys humanized: `snake_case` → `Title Case`)
- List → bulleted items with summary headers (extracts `rule`, `severity`, `location` from violation dicts)
- Nested structures → increased indentation

**Canvas integration (line 972-997):**

`_show_on_canvas()` extracts floor plan data from agent outputs:

1. Tries to find a plan dict in outputs (checks keys `parsed_plan`, `floor_plan`, `plan`, `layout`)
2. Falls back to plan data from user inputs (in case the agent didn't output a plan)
3. Loads plan into canvas via `FloorPlan.from_dict()`
4. Extracts violations from outputs, tool results, and explanation text
5. Calls `canvas_panel.show_violations()`

---

### AgentBuilderTab

**File:** `gui/agent_builder.py` (~446 lines)

No-code agent creation form.

**Form sections:**

1. **Basic Info** — Name (required), Category (default "Custom"), Description/Goal (required)
2. **Prompting** — System Prompt (required) — stored as `conversation_guidelines`
3. **Input Schema** — dynamic rows with `[+ Add Input]` button. Each row: name, type dropdown (string/number/boolean/image/json), description, required checkbox, delete button
4. **Constraints & Rules** — dynamic text fields with `[+ Add Constraint]`
5. **Output Schema** — dynamic rows: name, type dropdown (string/number/boolean/array/object), description
6. **Capabilities & Tools** — checkboxes for all registered tools from `ToolRegistry`

**`_gather_data()` (line 332-373):**

Reads all form fields into a dict. Auto-generates the agent `id` from the name: lowercase, spaces→underscores.

**`_validate(data)` (line 375-397):**

1. Name required
2. Goal required
3. System prompt required
4. At least one input required
5. **Domain relevance check** — calls `validate_domain_relevance()` from prompt_builder

**`_save_agent()` (line 399-420):**

Writes the gathered data as JSON to `user_agents/{name}.json`. Calls `on_agent_saved()` callback to refresh the sidebar.

**`_save_and_run_agent()` (line 422-425):**

Saves, then calls `on_save_and_run(agent_def)` callback which loads the agent in the Runner tab.

---

### L2ConsoleTab

**File:** `gui/l2_console.py` (~212 lines)

Demonstrates the L2 (legacy prompting) workflow.

**Components:**

1. **Banner** — "LEGACY PROMPTING: Versioned prompts, manual data flow, raw text output."
2. **Template selector** — dropdown populated from `prompts/*.md` files + `[View Template]` button (opens in dialog) + `[Browse...]` for custom templates
3. **Data input** — `QTextEdit` + `[Load File]` button (opens JSON file dialog)
4. **Send button** — triggers `_send_to_llm()`
5. **Response area** — read-only `QTextEdit`

**`_send_to_llm()` (line 192-207):**

Spawns `LlmWorker` thread which calls `GeminiClient.send_with_template()`. On completion, displays the raw text response. No JSON parsing, no structured output, no conversation — this is the point: L2 is raw text in, raw text out.

**`LlmWorker` (line 12-27):**

`QThread` that calls `send_with_template(template_path, data)` and emits the result string.

---

### AdoptionPanel

**File:** `gui/adoption_panel.py` (~215 lines)

Side-by-side L2 vs L3 comparison for judges.

**`AGENT_PROMPT_PAIRS` (line 11-16):**

Maps each agent JSON to its corresponding L2 prompt template:
```python
[
    ("floor_plan_parser.json", "v1_parse_floor_plan.md"),
    ("egress_validator.json", "v1_check_egress.md"),
    ("evacuation_diagnoser.json", "v1_diagnose_issues.md"),
    ("exit_placement_advisor.json", "v1_propose_fixes.md"),
]
```

**`_PAIR_ANNOTATIONS` (line 18-43):**

Per-pair annotations highlighting what changed. Example for Egress Validator:
- "Tool access: Agent calls P118 Validator and Pathfinding tools for real calculations. Legacy relies on the LLM to guess distances and rules."
- "Constraints: Agent explicitly lists P118 rules. Legacy buries them in prose instructions."

**Layout:**

```
[Dropdown: select pair]
[Left: L2 template text] [→ Arrow →] [Right: L3 agent JSON]
[Annotations: bulleted list of what changed]
```

**`_on_pair_selected()` (line 179-215):**

Loads the selected L2 template file and L3 agent JSON file, displays them side-by-side, and renders the corresponding annotations.

---

### CanvasPanel

**File:** `gui/canvas.py` (~582 lines)

Floor plan visualization with interactive graphics.

**`InteractiveGraphicsView` (line 18-33):**

Custom `QGraphicsView` with:
- Antialiasing
- Drag mode (scroll hand)
- Mouse wheel zoom (factor 1.15)
- No scroll bars (infinite canvas feel)

**`ToggleSwitch` (line 37-97):**

Custom animated toggle widget for layer visibility. Uses `QPropertyAnimation` on a custom `knobPos` property for smooth knob movement.

**`CanvasPanel` key methods:**

- `load_plan(floor_plan)` — clears the scene, renders all spatial elements:
  - Rooms as filled polygons (color-coded by type)
  - Corridors as lighter polygons
  - Walls as line segments
  - Doors as small arc symbols
  - Exits as arrow indicators
  - Room labels centered in polygons
- `show_violations(violations)` — overlays colored markers at violation locations:
  - Critical: red
  - Major: orange
  - Minor: yellow
  - Info: gray
- `highlight_location(location_id)` — scrolls to and highlights a specific room/corridor (triggered by clicking links in chat)
- `fit_to_window()` — auto-scales to show the entire floor plan
- `apply_theme(dark_mode)` — updates colors for light/dark mode
- Layer toggles: rooms, walls, doors, exits, violations — each controlled by a `ToggleSwitch`

---

## L2 Prompt Templates

**Directory:** `prompts/`

Four versioned markdown files with `{{DATA}}` placeholders:

### v1_parse_floor_plan.md

```markdown
You are a fire safety assistant. Parse floor plan data and extract a structured JSON representation.

## Instructions
1. Identify all rooms, corridors, doors, exits, and stairs
2. Classify each room by type
3. Estimate occupancy based on room type and area
4. Note any unusual or ambiguous features

## Floor Plan Data
{{DATA}}

## What to Produce
Output a single valid JSON object with parsed_plan and flagged_issues...
```

### v1_check_egress.md

Template for P118 compliance checking. Lists all P118 rules in prose, asks the LLM to check each one manually (without tool access).

### v1_diagnose_issues.md

Template for explaining violations in plain language. Asks for severity ranking and real-world impact assessment.

### v1_propose_fixes.md

Template for suggesting exit placements. Asks for ranked proposals with justification and effort estimates.

**Key difference from L3:** These templates have no tool access — the LLM must infer measurements, guess distances, and apply rules from memory. In L3, tools compute the exact values and the LLM interprets them.

---

## Configuration

**File:** `config.py`

**API:**
```python
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
```

**P118 Thresholds:**
```python
P118_MAX_TRAVEL_DISTANCE = 30.0          # meters
P118_MAX_DEAD_END_TRAVEL = 20.0          # meters
P118_MAX_DEAD_END_CORRIDOR = 12.0        # meters
P118_MIN_DOOR_WIDTH_ROOM = 0.9           # meters
P118_MIN_DOOR_WIDTH_EXIT = 1.2           # meters
P118_MIN_CORRIDOR_WIDTH = 1.4            # meters
P118_EXIT_CAPACITY_PER_METER = 80        # persons/meter
P118_MIN_EXITS_THRESHOLD_OCCUPANCY = 50  # persons
P118_MIN_EXITS_COUNT = 2
P118_ROOM_HIGH_OCCUPANCY = 50
P118_ROOM_MIN_EXITS_HIGH_OCC = 2
P118_EMERGENCY_LIGHTING_MIN_OCCUPANCY = 30
P118_EMERGENCY_LIGHTING_CORRIDOR_MIN_LENGTH = 10.0
P118_BORDERLINE_TOLERANCE = 0.10         # 10%
```

**Occupancy Density Table:**
```python
P118_OCCUPANCY_DENSITY = {
    "office": 10.0,      # 1 person per 10 m²
    "conference": 2.0,    # 1 person per 2 m²
    "corridor": 999.0,    # effectively 0 (exempt)
    "stairwell": 999.0,
    "wc": 20.0,
    "server": 20.0,
}
```

**Directories:**
```python
AGENTS_DIR = "data/agents"
USER_AGENTS_DIR = "user_agents"
FLOOR_PLANS_DIR = "data/floor_plans"
PROMPTS_DIR = "prompts"
```

---

## Testing

**Directory:** `tests/`

### test_tools.py

- `test_registry()` — verifies all 6 tools are registered and callable
- `test_pathfinding_office()` — loads `example_office.json`, verifies all rooms have finite exit distances
- `test_pathfinding_blocked()` — constructs a plan with an isolated room, verifies `inf` distance
- `test_p118_validator_office()` — runs validator on example office, checks for expected violation counts
- `test_p118_validator_violations()` — runs on borderline plan, verifies specific violations are detected
- `test_structural_checks()` — tests overlapping rooms, dead-end corridors, sealed rooms
- `test_metrics()` — verifies severity counting and compliance score calculation

### test_models.py

- Round-trip serialization: `to_dict()` → `from_dict()` for all model types
- JSON file I/O: `save_to_json()` → `load_from_json()`
- Edge cases: empty lists, optional fields, default values

### test_engine.py

- Agent runner execution with mock/real inputs
- Prompt builder output structure verification
- Cache fallback behavior (simulated API failure)
- Conversation turn counting and limit enforcement

### test_cross_agent.py

- Full pipeline test: Floor Plan Parser → Egress Validator → Evacuation Diagnoser → Exit Placement Advisor
- Verifies outputs from each stage are valid inputs for the next
- Tests the JSON export → import flow between agents
