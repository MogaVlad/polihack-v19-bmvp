import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

P118_MAX_TRAVEL_DISTANCE = 30.0
P118_MAX_DEAD_END_TRAVEL = 20.0
P118_MAX_DEAD_END_CORRIDOR = 12.0
P118_MIN_DOOR_WIDTH_ROOM = 0.9
P118_MIN_DOOR_WIDTH_EXIT = 1.2
P118_MIN_CORRIDOR_WIDTH = 1.4
P118_EXIT_CAPACITY_PER_METER = 80
P118_MIN_EXITS_THRESHOLD_OCCUPANCY = 50
P118_MIN_EXITS_COUNT = 2

P118_ROOM_HIGH_OCCUPANCY = 50
P118_ROOM_MIN_EXITS_HIGH_OCC = 2
P118_EMERGENCY_LIGHTING_MIN_OCCUPANCY = 30
P118_EMERGENCY_LIGHTING_CORRIDOR_MIN_LENGTH = 10.0

P118_BORDERLINE_TOLERANCE = 0.10

P118_OCCUPANCY_DENSITY = {
    "office": 10.0,
    "conference": 2.0,
    "corridor": 999.0,
    "stairwell": 999.0,
    "wc": 20.0,
    "server": 20.0,
}

TOOL_CONFIG = {
    "dxf_parser": {
        "name": "DXF Parser",
        "description": "Parses DXF floor plans into structured spatial data",
        "input_type": "DXF path",
        "output_type": "FloorPlan JSON",
    },
    "p118_validator": {
        "name": "P118 Validator",
        "description": "Validates floor plans against Romanian P118 fire safety regulations",
        "input_type": "FloorPlan",
        "output_type": "List[Violation]",
    },
    "pathfinding": {
        "name": "Pathfinding",
        "description": "Finds shortest evacuation paths using BFS/Dijkstra on room-corridor-exit graph",
        "input_type": "FloorPlan, room_id",
        "output_type": "(distance, path)",
    },
    "structural_checker": {
        "name": "Structural Checker",
        "description": "Detects blocked rooms, dead ends, and structural anomalies",
        "input_type": "FloorPlan",
        "output_type": "List[Violation]",
    },
    "metrics": {
        "name": "Metrics Calculator",
        "description": "Computes violation counts, severities, and compliance scoring",
        "input_type": "List[Violation]",
        "output_type": "MetricsReport",
    },
}

APP_TITLE = "AgentArchitect — Engineering Agent Platform"
AGENTS_DIR = "data/agents"
USER_AGENTS_DIR = "user_agents"
FLOOR_PLANS_DIR = "data/floor_plans"
PROMPTS_DIR = "prompts"
