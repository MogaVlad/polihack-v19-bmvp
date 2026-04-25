"""Generate cache entries for the borderline floor plan."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from models.floor_plan import FloorPlan
from engine.cache import ResponseCache
from models.chat import AgentResult

cache = ResponseCache()
plan = FloorPlan.load_from_json("data/floor_plans/example_borderline.json")
plan_json = json.dumps(plan.to_dict())
inputs = {"parsed_plan": plan_json}


# --- egress_validator ---
cache.save_result("egress_validator", inputs, AgentResult(
    agent_id="egress_validator",
    success=True,
    outputs={"response": "Borderline analysis", "violations": []},
    explanation=(
        "## P118 Compliance Report — Borderline Case\n\n"
        "I have analyzed this floor plan using the P118 Validator, Pathfinding, and Structural Checker tools.\n\n"
        "### Critical Issues\n\n"
        "**V001 — Room R4 (No-Polygon Room) has no reachable exit.**\n"
        "The P118 Validator found that Room R4 is completely disconnected from the building's exit network. "
        "Door D4 references a nonexistent corridor (GHOST_CORRIDOR), meaning this room's 3 occupants have no evacuation path.\n\n"
        "**V002 — Corridor C2 (Side Passage) width is 1.39m, below the 1.4m minimum (P118 Art. 3.6.12).**\n"
        "This is a borderline case — the corridor is only 0.01m below threshold. However, P118 compliance is binary: 1.39m fails.\n\n"
        "### Major Issues\n\n"
        "**V003 — Door D3 width is 0.89m, below the 0.9m minimum (P118 Art. 3.6.11).**\n"
        "Another borderline violation — just 0.01m below the threshold for room doors.\n\n"
        "### Structural Anomalies\n\n"
        "The Structural Checker flagged:\n"
        "- Room R4 has an empty polygon (cannot be rendered on canvas)\n"
        "- Room R4 has zero area\n"
        "- Door D4 references nonexistent corridor GHOST_CORRIDOR\n\n"
        "### Borderline Values (within 10% of threshold)\n\n"
        "| Element | Measured | Threshold | Margin |\n"
        "|---------|----------|-----------|--------|\n"
        "| Corridor C1 width | 1.42m | 1.40m | +1.4% — PASSES but barely |\n"
        "| Corridor C2 width | 1.39m | 1.40m | -0.7% — FAILS |\n"
        "| Door D1 width | 0.91m | 0.90m | +1.1% — PASSES but barely |\n"
        "| Door D2 width | 0.90m | 0.90m | +0.0% — PASSES at exact threshold |\n"
        "| Door D3 width | 0.89m | 0.90m | -1.1% — FAILS |\n\n"
        "### Overall: FAIL\n\n"
        "2 critical violations, 1 major violation, multiple structural anomalies. "
        "The disconnected Room R4 is the most urgent issue.\n\n"
        "```json\n"
        '[\n'
        '  {"id": "V001", "rule": "travel_distance", "severity": "critical", "location": "R4", "description": "Room R4 has no reachable exit"},\n'
        '  {"id": "V002", "rule": "corridor_width", "severity": "major", "location": "C2", "description": "Corridor width 1.39m < 1.4m minimum", "measured_value": 1.39, "threshold_value": 1.4},\n'
        '  {"id": "V003", "rule": "door_width", "severity": "major", "location": "D3", "description": "Door width 0.89m < 0.9m minimum", "measured_value": 0.89, "threshold_value": 0.9}\n'
        ']\n'
        "```"
    ),
    tool_results={},
), followups=[
    {
        "question": "Which violation is the most dangerous?",
        "response": (
            "The most dangerous violation is V001 — Room R4 (No-Polygon Room) being completely disconnected "
            "from all exits. Door D4 connects to a nonexistent corridor called GHOST_CORRIDOR, which means the "
            "3 occupants in this room literally have no way to evacuate during a fire.\n\n"
            "The borderline corridor width (C2 at 1.39m vs 1.4m minimum) and door width (D3 at 0.89m vs 0.9m "
            "minimum) are technically violations, but they are marginal.\n\n"
            "I would recommend consulting the **Exit Placement Advisor** agent for specific fix proposals."
        ),
    },
    {
        "question": "Tell me about the borderline values",
        "response": (
            "Several elements in this floor plan are very close to P118 thresholds:\n\n"
            "**Passing but barely:**\n"
            "- Corridor C1 at 1.42m width — only 0.02m above the 1.4m minimum.\n"
            "- Door D1 at 0.91m — just 0.01m above the 0.9m minimum.\n"
            "- Door D2 at exactly 0.90m — passes at the exact threshold.\n\n"
            "**Failing by a hair:**\n"
            "- Corridor C2 at 1.39m — just 0.01m below the 1.4m minimum.\n"
            "- Door D3 at 0.89m — just 0.01m below the 0.9m minimum.\n\n"
            "I would flag all of these to the building engineer. For fix proposals, please consult the "
            "**Exit Placement Advisor** agent."
        ),
    },
])

# --- evacuation_diagnoser ---
cache.save_result("evacuation_diagnoser", inputs, AgentResult(
    agent_id="evacuation_diagnoser",
    success=True,
    outputs={"response": "Borderline diagnosis"},
    explanation=(
        "## Evacuation Risk Diagnosis — Borderline Case\n\n"
        "The Metrics Calculator reports: **1 critical, 2 major violations. Compliance score: 45/100. Status: FAIL.**\n\n"
        "### Life-Safety-Critical\n\n"
        "**Room R4 is a death trap.** This room has 3 occupants but its door (D4) connects to a corridor that "
        "doesn't exist (GHOST_CORRIDOR). In a fire, these 3 people have literally no escape route.\n\n"
        "### Code-Compliance (Borderline)\n\n"
        "**Corridor C2 is 1mm too narrow.** At 1.39m vs the 1.4m minimum, this barely fails P118.\n\n"
        "**Door D3 is 1mm too narrow.** At 0.89m vs the 0.90m minimum.\n\n"
        "### Overall Assessment\n\n"
        "This building has one genuine safety hazard (the disconnected Room R4) and two technical violations "
        "that are borderline. For fix proposals, consult the **Exit Placement Advisor** agent.\n\n"
        "```json\n"
        '[\n'
        '  {"violation_id": "V001", "severity_rank": 1, "explanation": "Room R4 completely disconnected", "impact": "3 occupants trapped", "category": "life-safety-critical"},\n'
        '  {"violation_id": "V002", "severity_rank": 2, "explanation": "Corridor C2 1mm below minimum", "impact": "Minimal", "category": "code-compliance"},\n'
        '  {"violation_id": "V003", "severity_rank": 3, "explanation": "Door D3 1mm below minimum", "impact": "Minimal", "category": "code-compliance"}\n'
        ']\n'
        "```"
    ),
    tool_results={},
), followups=[
    {
        "question": "What would happen in a fire?",
        "response": (
            "In Room R4, the 3 occupants would discover their door leads nowhere — the corridor it connects "
            "to does not exist. They would be trapped. In the rest of the building, evacuation would proceed "
            "mostly normally. The borderline door and corridor widths would have negligible impact on evacuation speed."
        ),
    },
])

# --- exit_placement_advisor ---
cache.save_result("exit_placement_advisor", inputs, AgentResult(
    agent_id="exit_placement_advisor",
    success=True,
    outputs={"response": "Borderline fix proposals"},
    explanation=(
        "## Fix Proposals — Borderline Case\n\n"
        "### Proposal 1: Connect Room R4 to Corridor C1 (HIGH PRIORITY)\n"
        "**Resolves**: V001 (R4 no reachable exit)\n"
        "**What to change**: Add a new door from R4 to C1, width >= 0.9m\n"
        "**Effort**: Medium\n\n"
        "### Proposal 2: Widen Corridor C2 by 1cm (LOW PRIORITY)\n"
        "**Resolves**: V002 (C2 width 1.39m < 1.4m)\n"
        "**Effort**: Low\n\n"
        "### Proposal 3: Replace Door D3 (LOW PRIORITY)\n"
        "**Resolves**: V003 (D3 width 0.89m < 0.9m)\n"
        "**Effort**: Low\n\n"
        "### Remaining Violations After All Proposals: None\n\n"
        "```json\n"
        '[\n'
        '  {"proposal_id": "P1", "resolves": ["V001"], "change": "Add door from R4 to C1", "effort": "medium", "impact": "high"},\n'
        '  {"proposal_id": "P2", "resolves": ["V002"], "change": "Widen C2 by 1cm", "effort": "low", "impact": "low"},\n'
        '  {"proposal_id": "P3", "resolves": ["V003"], "change": "Replace D3 door frame", "effort": "low", "impact": "low"}\n'
        ']\n'
        "```"
    ),
    tool_results={},
), followups=[
    {
        "question": "Can we skip fixing the borderline violations?",
        "response": (
            "The borderline violations have minimal safety impact, but P118 compliance is binary — there is "
            "no 'close enough' in building code. The fixes are trivial (1cm wall adjustment, door frame replacement). "
            "**Proposal 1 (connecting Room R4) is non-negotiable** — that is a genuine life-safety issue."
        ),
    },
])

# --- floor_plan_parser ---
cache.save_result("floor_plan_parser", inputs, AgentResult(
    agent_id="floor_plan_parser",
    success=True,
    outputs={"response": "Borderline parse"},
    explanation=(
        "## Floor Plan Parse Results — Borderline Case\n\n"
        "### Rooms Identified (5 total)\n\n"
        "1. **R1 — Main Office** (96m2, occupancy: 20)\n"
        "2. **R2 — Meeting Room** (80m2, occupancy: 16)\n"
        "3. **R3 — Workshop** (96m2, occupancy: 15)\n"
        "4. **R4 — No-Polygon Room** (0m2, occupancy: 3) — FLAGGED: no polygon data\n"
        "5. **R5 — Storage** (48m2, occupancy: 2)\n\n"
        "### Flagged Issues\n\n"
        "1. Room R4 has no polygon — cannot render on canvas\n"
        "2. Door D4 references GHOST_CORRIDOR which does not exist\n"
        "3. Several measurements near P118 thresholds\n\n"
        "For validation, I recommend the **Egress Validator** agent.\n\n"
        "```json\n"
        '[\n'
        '  {"id": "FLAG1", "type": "missing_polygon", "location": "R4", "description": "Room has no spatial definition"},\n'
        '  {"id": "FLAG2", "type": "invalid_reference", "location": "D4", "description": "Door connects to nonexistent corridor GHOST_CORRIDOR"}\n'
        ']\n'
        "```"
    ),
    tool_results={},
), followups=[
    {
        "question": "What is wrong with Room R4?",
        "response": (
            "Room R4 has two problems:\n\n"
            "1. **No polygon data** — the polygon array is empty. Cannot determine location, shape, or area.\n\n"
            "2. **Its door connects to nothing** — Door D4 connects to 'GHOST_CORRIDOR' which doesn't exist.\n\n"
            "For compliance analysis, consult the **Egress Validator** agent."
        ),
    },
])

print("All borderline caches saved successfully")
