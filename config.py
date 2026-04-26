import os
from dotenv import load_dotenv

# Ensure .env is loaded from the directory containing config.py
_base_dir = os.path.dirname(os.path.abspath(__file__))
_env_path = os.path.join(_base_dir, ".env")
load_dotenv(dotenv_path=_env_path)

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

TOOL_CONFIG = {
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
    "dxf_parser": {
        "name": "DXF/DWG Parser",
        "description": "Parses DXF/DWG floor plans into structured room, corridor, door, exit, and wall data",
        "input_type": "DXF/DWG file path",
        "output_type": "FloorPlan + flagged issues",
    },
}

APP_TITLE = "AgentArchitect — Engineering Agent Platform"
AGENTS_DIR = "data/agents"
USER_AGENTS_DIR = "user_agents"
FLOOR_PLANS_DIR = "data/floor_plans"
PROMPTS_DIR = "prompts"

# ODA File Converter path for DWG → DXF conversion (optional external tool)
ODA_CONVERTER_PATH = os.getenv(
    "ODA_CONVERTER_PATH",
    r"C:\Program Files\ODA\ODAFileConverter\ODAFileConverter.exe",
)

# P118 occupancy density tables: room_type → m² per person
P118_OCCUPANCY_DENSITY = {
    "office": 10.0,
    "open_office": 7.0,
    "conference": 1.5,
    "meeting": 2.0,
    "corridor": 0,       # corridors don't contribute occupancy
    "stairwell": 0,
    "lobby": 3.0,
    "reception": 5.0,
    "storage": 30.0,
    "wc": 0,
    "toilet": 0,
    "kitchen": 5.0,
    "server_room": 20.0,
    "default": 10.0,
}
