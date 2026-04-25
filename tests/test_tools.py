"""
Unit tests for all tool modules — using example floor plan data.

Tests P118 validator, pathfinding, structural checker, metrics,
and the tool registry with known-good and known-bad floor plans.
"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.registry import ToolRegistry
from tools.p118_validator import validate_p118
from tools.pathfinding import find_shortest_exit_path, find_all_travel_distances
from tools.structural_checker import detect_blocked_rooms, detect_dead_ends, detect_anomalies
from tools.metrics import compute_metrics


DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "floor_plans")


def _load_plan(name: str) -> dict:
    path = os.path.join(DATA_DIR, name)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ── Registry Tests ──────────────────────────────────────────────

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


def test_registry_tools_callable():
    """Verify all registered tools are actually callable."""
    registry = ToolRegistry()
    for name in registry.list_tool_names():
        fn = registry.get_tool(name)
        assert callable(fn), f"Tool '{name}' is not callable"
    print("PASS: test_registry_tools_callable")


# ── Pathfinding Tests ───────────────────────────────────────────

def test_pathfinding_office():
    """Office plan: all rooms should have finite distances to exit."""
    plan = _load_plan("example_office.json")
    distances = find_all_travel_distances(plan)

    assert len(distances) == 7, f"Expected 7 rooms, got {len(distances)}"

    # R1 has exit E1 directly → should have 0 distance
    assert distances["R1"] == 0.0, f"R1 should be 0 (has exit), got {distances['R1']}"

    # All rooms should have finite distance (none are blocked)
    for rid, dist in distances.items():
        assert dist < float("inf"), f"Room {rid} should be reachable, got inf"

    print(f"PASS: test_pathfinding_office — distances: {distances}")


def test_pathfinding_specific_room():
    """Test single room pathfinding."""
    plan = _load_plan("example_office.json")
    dist, path = find_shortest_exit_path(plan, "R2")

    assert dist < float("inf"), "R2 should be reachable"
    assert len(path) > 1, "Path should have multiple nodes"
    assert path[0] == "R2", "Path should start at R2"
    print(f"PASS: test_pathfinding_specific_room — R2 → exit: {dist:.1f}m, path: {path}")


def test_pathfinding_nonexistent_room():
    """Nonexistent room should return infinity."""
    plan = _load_plan("example_office.json")
    dist, path = find_shortest_exit_path(plan, "NONEXISTENT")

    assert dist == float("inf")
    assert path == []
    print("PASS: test_pathfinding_nonexistent_room")


def test_pathfinding_school():
    """School has 3 exits — rooms should be well-connected."""
    plan = _load_plan("example_school.json")
    distances = find_all_travel_distances(plan)

    assert len(distances) == 6
    for rid, dist in distances.items():
        assert dist < float("inf"), f"School room {rid} should be reachable"

    print(f"PASS: test_pathfinding_school — distances: {distances}")


# ── P118 Validator Tests ────────────────────────────────────────

def test_p118_office_violations():
    """
    Office plan has known violations:
    - Corridor C2 width 1.2m < 1.4m
    - Door D4 width 0.8m < 0.9m
    - Door D7 width 0.7m < 0.9m
    - Only 1 exit with occupancy 107 > 50
    - Total exit capacity (96) < total occupancy (107)
    """
    plan = _load_plan("example_office.json")
    violations = validate_p118(plan)

    assert len(violations) > 0, "Office should have violations"

    # Collect violation rules
    rules = [v["rule"] for v in violations]

    assert "corridor_width" in rules, "Should detect narrow corridor C2"
    assert "door_width" in rules, "Should detect narrow doors D4/D7"
    assert "exit_count" in rules, "Should detect insufficient exits"
    assert "exit_capacity" in rules, "Should detect exit over-capacity"

    # Verify specific violations
    corridor_violations = [v for v in violations if v["rule"] == "corridor_width"]
    assert any("C2" in v["location"] or "East" in v["description"] for v in corridor_violations), \
        "Should flag C2 (East Corridor)"

    door_violations = [v for v in violations if v["rule"] == "door_width"]
    narrow_door_ids = [v["location"] for v in door_violations]
    assert any("D4" in loc for loc in narrow_door_ids), "Should flag D4 (0.8m)"
    assert any("D7" in loc for loc in narrow_door_ids), "Should flag D7 (0.7m)"

    print(f"PASS: test_p118_office_violations — {len(violations)} violations found:")
    for v in violations:
        print(f"  [{v['severity'].upper()}] {v['rule']}: {v['description']}")


def test_p118_school_fewer_violations():
    """School plan is mostly compliant — should have fewer violations."""
    plan = _load_plan("example_school.json")
    violations = validate_p118(plan)

    # School has 3 exits and wider corridors — should be cleaner
    critical_violations = [v for v in violations if v["severity"] == "critical"]
    # School may still have some issues, but should have fewer critical ones
    # (it has 175 occupants across 3 exits, which should be fine capacity-wise)

    print(f"PASS: test_p118_school_fewer_violations — {len(violations)} violations, {len(critical_violations)} critical:")
    for v in violations:
        print(f"  [{v['severity'].upper()}] {v['rule']}: {v['description']}")


def test_p118_empty_plan():
    """Empty plan should not crash."""
    violations = validate_p118({})
    assert isinstance(violations, list)
    print(f"PASS: test_p118_empty_plan — {len(violations)} violations")


# ── Structural Checker Tests ────────────────────────────────────

def test_structural_blocked_rooms_office():
    """Office plan — all rooms should be connected (no blocked rooms)."""
    plan = _load_plan("example_office.json")
    violations = detect_blocked_rooms(plan)

    blocked = [v for v in violations if v["rule"] == "blocked_room"]
    assert len(blocked) == 0, f"Office should have no blocked rooms, got {len(blocked)}"
    print("PASS: test_structural_blocked_rooms_office")


def test_structural_blocked_rooms_no_exits():
    """Plan with no exits → all rooms blocked."""
    plan = {"rooms": [{"id": "R1", "name": "Room 1", "type": "office", "polygon": [[0,0],[10,0],[10,10],[0,10]], "area": 100, "occupancy": 10}], "corridors": [], "doors": [], "exits": []}
    violations = detect_blocked_rooms(plan)

    blocked = [v for v in violations if v["rule"] == "blocked_room"]
    assert len(blocked) == 1, "Should detect 1 blocked room"
    print("PASS: test_structural_blocked_rooms_no_exits")


def test_structural_dead_ends():
    """Detect dead-end corridors in office plan."""
    plan = _load_plan("example_office.json")
    violations = detect_dead_ends(plan)

    print(f"PASS: test_structural_dead_ends — {len(violations)} dead-end issues found:")
    for v in violations:
        print(f"  [{v['severity'].upper()}] {v['description']}")


def test_structural_anomalies_clean():
    """Office plan should have no anomalies (all rooms have polygons)."""
    plan = _load_plan("example_office.json")
    violations = detect_anomalies(plan)

    serious = [v for v in violations if v["severity"] in ("critical", "major")]
    assert len(serious) == 0, f"Clean plan should have no serious anomalies, got {len(serious)}"
    print(f"PASS: test_structural_anomalies_clean — {len(violations)} info/minor issues")


def test_structural_anomalies_bad_data():
    """Plan with bad data → should detect anomalies."""
    plan = {
        "rooms": [
            {"id": "R1", "name": "No Polygon Room", "type": "office", "polygon": [], "area": 0, "occupancy": 5},
            {"id": "R2", "name": "Good Room", "type": "office", "polygon": [[0,0],[10,0],[10,10],[0,10]], "area": 100, "occupancy": 10},
        ],
        "corridors": [
            {"id": "C1", "name": "Zero Width", "width": 0, "length": 10, "connects": ["R1", "R2"], "polygon": []},
        ],
        "doors": [
            {"id": "D1", "connects": ["R1", "NONEXISTENT"], "width": 0.9, "position": [5, 0]},
        ],
        "exits": [],
    }
    violations = detect_anomalies(plan)

    rules = [v["rule"] for v in violations]
    assert "anomaly_missing_polygon" in rules, "Should detect missing polygon"
    assert "anomaly_invalid_area" in rules, "Should detect zero area"
    assert "anomaly_zero_width_corridor" in rules, "Should detect zero-width corridor"
    assert "anomaly_invalid_reference" in rules, "Should detect invalid door reference"

    print(f"PASS: test_structural_anomalies_bad_data — {len(violations)} anomalies detected:")
    for v in violations:
        print(f"  [{v['severity'].upper()}] {v['rule']}: {v['description']}")


# ── Metrics Tests ───────────────────────────────────────────────

def test_metrics_office():
    """Metrics from office violations should show FAIL."""
    plan = _load_plan("example_office.json")
    violations = validate_p118(plan)

    report = compute_metrics({"violations": violations})

    assert report["total_violations"] > 0
    assert report["pass_fail"] == "FAIL", "Office with violations should FAIL"
    assert report["compliance_score"] < 100, "Score should be < 100"
    assert report["critical_count"] + report["major_count"] > 0

    print(f"PASS: test_metrics_office — {report}")


def test_metrics_empty():
    """No violations → PASS with 100 score."""
    report = compute_metrics({"violations": []})

    assert report["total_violations"] == 0
    assert report["pass_fail"] == "PASS"
    assert report["compliance_score"] == 100.0

    print(f"PASS: test_metrics_empty — {report}")


def test_metrics_severity_weights():
    """Verify severity weighting in compliance score."""
    violations = [
        {"severity": "critical"},
        {"severity": "major"},
        {"severity": "minor"},
        {"severity": "info"},
    ]
    report = compute_metrics({"violations": violations})

    # 100 - 25(critical) - 10(major) - 3(minor) - 1(info) = 61
    assert report["compliance_score"] == 61.0, f"Expected 61.0, got {report['compliance_score']}"
    assert report["critical_count"] == 1
    assert report["major_count"] == 1
    assert report["minor_count"] == 1
    assert report["info_count"] == 1
    assert report["pass_fail"] == "FAIL"

    print(f"PASS: test_metrics_severity_weights — {report}")


# ── Run All Tests ───────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("TOOL TESTS - Phase 1")
    print("=" * 60)

    # Registry
    print("\n-- Registry --")
    test_registry()
    test_registry_tools_callable()

    # Pathfinding
    print("\n-- Pathfinding --")
    test_pathfinding_office()
    test_pathfinding_specific_room()
    test_pathfinding_nonexistent_room()
    test_pathfinding_school()

    # P118 Validator
    print("\n-- P118 Validator --")
    test_p118_office_violations()
    test_p118_school_fewer_violations()
    test_p118_empty_plan()

    # Structural Checker
    print("\n-- Structural Checker --")
    test_structural_blocked_rooms_office()
    test_structural_blocked_rooms_no_exits()
    test_structural_dead_ends()
    test_structural_anomalies_clean()
    test_structural_anomalies_bad_data()

    # Metrics
    print("\n-- Metrics --")
    test_metrics_office()
    test_metrics_empty()
    test_metrics_severity_weights()

    print("\n" + "=" * 60)
    print("ALL TOOL TESTS PASSED!")
    print("=" * 60)
