"""
Structural Checker — detects blocked rooms, dead ends, and anomalies.

Uses the pathfinding graph to identify structural issues in floor plans
that would affect evacuation safety.
"""

from typing import Dict, List
from models.violations import Violation
from tools.pathfinding import _build_graph, _find_exit_nodes, _dijkstra, _extract_plan_data


_violation_counter = 0


def _next_id(prefix: str = "S") -> str:
    global _violation_counter
    _violation_counter += 1
    return f"{prefix}{_violation_counter:03d}"


def _make_violation(
    rule: str,
    article: str,
    severity: str,
    location: str,
    description: str,
    measured: float = None,
    threshold: float = None,
) -> dict:
    v = Violation(
        id=_next_id(),
        rule=rule,
        article=article,
        severity=severity,
        location=location,
        description=description,
        measured_value=measured,
        threshold_value=threshold,
    )
    return v.to_dict()


def _bbox(polygon: list):
    xs = [p[0] for p in polygon]
    ys = [p[1] for p in polygon]
    return min(xs), min(ys), max(xs), max(ys)


def _bboxes_overlap(poly_a: list, poly_b: list) -> bool:
    ax1, ay1, ax2, ay2 = _bbox(poly_a)
    bx1, by1, bx2, by2 = _bbox(poly_b)
    if ax2 <= bx1 or bx2 <= ax1 or ay2 <= by1 or by2 <= ay1:
        return False
    overlap_x = min(ax2, bx2) - max(ax1, bx1)
    overlap_y = min(ay2, by2) - max(ay1, by1)
    overlap_area = overlap_x * overlap_y
    area_a = (ax2 - ax1) * (ay2 - ay1)
    area_b = (bx2 - bx1) * (by2 - by1)
    min_area = min(area_a, area_b) if min(area_a, area_b) > 0 else 1
    return (overlap_area / min_area) > 0.1


def detect_blocked_rooms(inputs: Dict) -> List[dict]:
    """
    Detect rooms that have no reachable path to any exit.

    A blocked room is a critical safety hazard — occupants cannot evacuate.
    """
    violations = []
    plan_data = _extract_plan_data(inputs)
    graph = _build_graph(plan_data)
    exit_nodes = _find_exit_nodes(plan_data)

    if not exit_nodes:
        # If there are no exits at all, every room is blocked
        for room in plan_data.get("rooms", []):
            rid = room["id"]
            rname = room.get("name", rid)
            violations.append(_make_violation(
                rule="blocked_room",
                article="P118 Art. 3.6.1",
                severity="critical",
                location=rid,
                description=(
                    f"Room '{rname}' is blocked — no exits exist in the building."
                ),
            ))
        return violations

    for room in plan_data.get("rooms", []):
        rid = room["id"]
        rname = room.get("name", rid)
        occupancy = room.get("occupancy", 0)

        dist, path = _dijkstra(graph, rid, exit_nodes)

        if dist == float("inf"):
            violations.append(_make_violation(
                rule="blocked_room",
                article="P118 Art. 3.6.1",
                severity="critical",
                location=rid,
                description=(
                    f"Room '{rname}' (occupancy: {occupancy}) has no reachable "
                    f"path to any exit. Occupants cannot evacuate."
                ),
            ))

    return violations


def detect_dead_ends(inputs: Dict) -> List[dict]:
    """
    Detect dead-end corridors — corridors with only one connection
    to another corridor or exit.

    Dead-end corridors force occupants to backtrack, increasing
    evacuation time and risk.
    """
    violations = []
    plan_data = _extract_plan_data(inputs)
    graph = _build_graph(plan_data)

    corridor_ids = {c["id"] for c in plan_data.get("corridors", [])}
    exit_nodes = _find_exit_nodes(plan_data)

    for corridor in plan_data.get("corridors", []):
        cid = corridor["id"]
        cname = corridor.get("name", cid)
        length = corridor.get("length", 0.0)

        neighbors = graph.get(cid, {})
        # Count connections to other corridors or exit nodes
        corridor_or_exit_neighbors = [
            n for n in neighbors if n in corridor_ids or n in exit_nodes
        ]

        if len(corridor_or_exit_neighbors) == 0:
            violations.append(_make_violation(
                rule="dead_end_corridor",
                article="P118 Art. 3.6.5",
                severity="major",
                location=cid,
                description=(
                    f"Corridor '{cname}' is isolated — no connections to other "
                    f"corridors or exits."
                ),
                measured=length,
            ))
        elif len(corridor_or_exit_neighbors) == 1 and cid not in exit_nodes:
            severity = "major" if length > 12.0 else "minor"
            violations.append(_make_violation(
                rule="dead_end_corridor",
                article="P118 Art. 3.6.5",
                severity=severity,
                location=cid,
                description=(
                    f"Corridor '{cname}' is a dead-end (length: {length}m, "
                    f"single connection to '{corridor_or_exit_neighbors[0]}')."
                ),
                measured=length,
                threshold=12.0,
            ))

    return violations


def detect_anomalies(inputs: Dict) -> List[dict]:
    """
    Detect structural anomalies in the floor plan:
    - Rooms with no polygon / empty polygon
    - Zero-width corridors
    - Rooms with zero or negative area
    """
    violations = []
    plan_data = _extract_plan_data(inputs)

    # Check rooms
    for room in plan_data.get("rooms", []):
        rid = room["id"]
        rname = room.get("name", rid)
        polygon = room.get("polygon", [])
        area = room.get("area", 0.0)

        if not polygon or len(polygon) < 3:
            violations.append(_make_violation(
                rule="anomaly_missing_polygon",
                article="N/A",
                severity="minor",
                location=rid,
                description=(
                    f"Room '{rname}' has no polygon or fewer than 3 vertices "
                    f"({len(polygon)} vertices). Cannot render on canvas."
                ),
            ))

        if area <= 0:
            violations.append(_make_violation(
                rule="anomaly_invalid_area",
                article="N/A",
                severity="info",
                location=rid,
                description=(
                    f"Room '{rname}' has zero or negative area ({area}m²)."
                ),
                measured=area,
            ))

    # Check corridors
    for corridor in plan_data.get("corridors", []):
        cid = corridor["id"]
        cname = corridor.get("name", cid)
        width = corridor.get("width", 0.0)
        length = corridor.get("length", 0.0)

        if width <= 0:
            violations.append(_make_violation(
                rule="anomaly_zero_width_corridor",
                article="N/A",
                severity="minor",
                location=cid,
                description=(
                    f"Corridor '{cname}' has zero or negative width ({width}m)."
                ),
                measured=width,
            ))

        if length <= 0:
            violations.append(_make_violation(
                rule="anomaly_zero_length_corridor",
                article="N/A",
                severity="info",
                location=cid,
                description=(
                    f"Corridor '{cname}' has zero or negative length ({length}m)."
                ),
                measured=length,
            ))

    # Check for overlapping rooms/corridors (bounding-box test)
    all_polys = []
    for r in plan_data.get("rooms", []):
        poly = r.get("polygon", [])
        if poly and len(poly) >= 3:
            all_polys.append((r["id"], r.get("name", r["id"]), "room", poly))
    for c in plan_data.get("corridors", []):
        poly = c.get("polygon", [])
        if poly and len(poly) >= 3:
            all_polys.append((c["id"], c.get("name", c["id"]), "corridor", poly))

    for i in range(len(all_polys)):
        for j in range(i + 1, len(all_polys)):
            id_a, name_a, type_a, poly_a = all_polys[i]
            id_b, name_b, type_b, poly_b = all_polys[j]
            if _bboxes_overlap(poly_a, poly_b):
                violations.append(_make_violation(
                    rule="anomaly_overlapping_spaces",
                    article="N/A",
                    severity="minor",
                    location=f"{id_a}, {id_b}",
                    description=(
                        f"{type_a.title()} '{name_a}' ({id_a}) and "
                        f"{type_b.title()} '{name_b}' ({id_b}) have overlapping "
                        f"bounding boxes — verify spatial layout."
                    ),
                ))

    # Check doors referencing nonexistent rooms/corridors
    all_node_ids = set()
    for r in plan_data.get("rooms", []):
        all_node_ids.add(r["id"])
    for c in plan_data.get("corridors", []):
        all_node_ids.add(c["id"])

    for door in plan_data.get("doors", []):
        did = door.get("id", "")
        connects = door.get("connects", [])
        for node_id in connects:
            if node_id not in all_node_ids:
                violations.append(_make_violation(
                    rule="anomaly_invalid_reference",
                    article="N/A",
                    severity="minor",
                    location=did,
                    description=(
                        f"Door '{did}' references nonexistent room/corridor "
                        f"'{node_id}'."
                    ),
                ))

    return violations
