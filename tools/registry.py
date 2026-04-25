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
            results.extend(detect_blocked_rooms(inputs))
            results.extend(detect_dead_ends(inputs))
            results.extend(detect_anomalies(inputs))
            return results

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
