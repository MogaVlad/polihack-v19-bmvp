from typing import Callable, Dict, List, Optional
from dataclasses import dataclass


@dataclass
class ToolInfo:
    name: str
    description: str
    input_type: str
    output_type: str
    function: Callable


class ToolRegistry:
    _instance = None
    _tools: Dict[str, ToolInfo] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._tools = {}
            cls._instance._register_defaults()
        return cls._instance

    def _register_defaults(self):
        from tools.p118_validator import validate_p118
        from tools.pathfinding import find_shortest_exit_path, find_all_travel_distances
        from tools.structural_checker import detect_blocked_rooms, detect_dead_ends, detect_anomalies
        from tools.metrics import compute_metrics

        def structural_check_all(inputs):
            """Combined structural checker — runs all three sub-checks."""
            results = []
            for fn in (detect_blocked_rooms, detect_dead_ends, detect_anomalies):
                try:
                    results.extend(fn(inputs))
                except Exception as e:
                    results.append({"id": "ERR", "rule": "checker_error", "severity": "info",
                                    "location": "building", "description": f"{fn.__name__} failed: {e}"})
            return results

        def gemini_vision_parse(inputs):
            """Parse a floor plan image using Gemini Vision."""
            import os
            from llm.gemini_client import GeminiClient

            image_path = inputs.get("floor_plan", "")
            if not image_path or not os.path.isfile(image_path):
                return {"error": f"Image not found: {image_path}"}

            client = GeminiClient()
            prompt = (
                "Analyze this floor plan image. Identify and list:\n"
                "1. All rooms with their type, approximate dimensions, and estimated area\n"
                "2. All corridors with approximate width and length\n"
                "3. All doors and what spaces they connect\n"
                "4. All exits and their locations\n"
                "5. Any stairs, elevators, or vertical circulation\n"
                "6. Any unusual or ambiguous features\n"
                "Be precise about spatial relationships and measurements."
            )
            result = client.parse_image(image_path, prompt)
            return {"vision_analysis": result}

        self.register_tool(
            "gemini_vision",
            "Gemini Vision",
            "Parses floor plan images into structured spatial descriptions using AI vision",
            "image_path",
            "Text analysis of floor plan",
            gemini_vision_parse,
        )
        self.register_tool(
            "p118_validator",
            "P118 Validator",
            "Validates floor plans against Romanian P118 fire safety regulations",
            "FloorPlan",
            "List[Violation]",
            validate_p118,
        )
        self.register_tool(
            "pathfinding",
            "Pathfinding",
            "Finds shortest evacuation paths using BFS/Dijkstra",
            "FloorPlan, room_id",
            "(distance, path)",
            find_all_travel_distances,
        )
        self.register_tool(
            "structural_checker",
            "Structural Checker",
            "Detects blocked rooms, dead ends, and structural anomalies",
            "FloorPlan",
            "List[Violation]",
            structural_check_all,
        )
        self.register_tool(
            "metrics",
            "Metrics Calculator",
            "Computes violation counts, severities, and compliance scoring",
            "List[Violation]",
            "MetricsReport",
            compute_metrics,
        )

        # ── DXF/DWG parser tool ──────────────────────────────────
        def parse_dxf(input_data):
            """Parse a DXF/DWG floor plan into structured FloorPlan JSON."""
            import os
            from tools.dwg_converter import convert_dwg_to_dxf
            from tools.dxf_parser import extract_entities
            from tools.dxf_to_floorplan import build_floor_plan

            file_path = input_data.get("floor_plan", "")
            if not file_path or not os.path.isfile(file_path):
                return {"error": f"File not found: {file_path}"}

            if file_path.lower().endswith(".dwg"):
                try:
                    file_path = convert_dwg_to_dxf(file_path)
                except (RuntimeError, FileNotFoundError) as e:
                    return {"error": str(e)}

            entities = extract_entities(file_path)
            floor_plan, issues = build_floor_plan(entities)
            return {
                "parsed_plan": floor_plan.to_dict(),
                "flagged_issues": issues,
            }

        self.register_tool(
            "dxf_parser",
            "DXF/DWG Parser",
            "Parses DXF/DWG floor plans into structured room, corridor, door, exit, and wall data with precise geometry",
            "DXF/DWG file path",
            "FloorPlan + flagged issues",
            parse_dxf,
        )

    def register_tool(
        self,
        key: str,
        name: str,
        description: str,
        input_type: str,
        output_type: str,
        function: Callable,
    ):
        self._tools[key] = ToolInfo(
            name=name,
            description=description,
            input_type=input_type,
            output_type=output_type,
            function=function,
        )

    def get_tool(self, key: str) -> Optional[Callable]:
        info = self._tools.get(key)
        return info.function if info else None

    def get_tool_info(self, key: str) -> Optional[ToolInfo]:
        return self._tools.get(key)

    def list_tools(self) -> List[ToolInfo]:
        return list(self._tools.values())

    def list_tool_names(self) -> List[str]:
        return list(self._tools.keys())
