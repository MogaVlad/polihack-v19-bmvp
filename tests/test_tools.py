import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.registry import ToolRegistry
from tools.p118_validator import validate_p118
from tools.pathfinding import find_shortest_exit_path, find_all_travel_distances
from tools.structural_checker import detect_blocked_rooms, detect_dead_ends, detect_anomalies
from tools.metrics import compute_metrics


def test_registry():
    registry = ToolRegistry()
    names = registry.list_tool_names()
    assert "p118_validator" in names
    assert "pathfinding" in names
    assert "structural_checker" in names
    assert "metrics" in names

    tool_fn = registry.get_tool("p118_validator")
    assert tool_fn is not None

    info = registry.get_tool_info("p118_validator")
    assert info.name == "P118 Validator"

    assert registry.get_tool("nonexistent") is None
    print(f"PASS: test_registry ({len(names)} tools registered)")


def test_p118_validator_stub():
    result = validate_p118({})
    assert isinstance(result, list)
    print("PASS: test_p118_validator_stub")


def test_pathfinding_stub():
    dist, path = find_shortest_exit_path({}, "R1")
    assert dist == 0.0
    assert path == []

    distances = find_all_travel_distances({})
    assert isinstance(distances, dict)
    print("PASS: test_pathfinding_stub")


def test_structural_checker_stub():
    assert detect_blocked_rooms({}) == []
    assert detect_dead_ends({}) == []
    assert detect_anomalies({}) == []
    print("PASS: test_structural_checker_stub")


def test_metrics_stub():
    result = compute_metrics({})
    assert isinstance(result, dict)
    assert "total_violations" in result
    print("PASS: test_metrics_stub")


if __name__ == "__main__":
    test_registry()
    test_p118_validator_stub()
    test_pathfinding_stub()
    test_structural_checker_stub()
    test_metrics_stub()
    print("\nAll tool tests passed!")
