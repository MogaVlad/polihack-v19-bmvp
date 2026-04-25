"""
P118 Validator — Romanian fire safety regulation checks.

Validates floor plans against P118 norms:
- Travel distance to exits
- Exit capacity
- Door widths
- Corridor widths
- Dead-end corridor limits
- Minimum exit count
"""

from typing import List, Dict
from models.violations import Violation
from tools.pathfinding import find_all_travel_distances, _extract_plan_data, _build_graph, _find_exit_nodes
import config


_violation_counter = 0


def _next_id() -> str:
    global _violation_counter
    _violation_counter += 1
    return f"V{_violation_counter:03d}"


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


def validate_p118(inputs: Dict) -> List[dict]:
    """
    Run all P118 validation checks on a floor plan.

    Args:
        inputs: Dict containing floor plan data, either directly or as
                {"floor_plan": {...}}

    Returns:
        List of Violation dicts.
    """
    global _violation_counter
    _violation_counter = 0

    violations = []
    checks = [
        _check_travel_distance,
        _check_exit_capacity,
        _check_door_widths,
        _check_corridor_widths,
        _check_dead_ends,
        _check_exit_count,
        _check_room_exit_count,
        _check_emergency_lighting,
    ]
    for check_fn in checks:
        try:
            violations.extend(check_fn(inputs))
        except Exception as e:
            violations.append(_make_violation(
                rule="validator_error",
                article="N/A",
                severity="info",
                location="building",
                description=f"Check '{check_fn.__name__}' failed: {e}",
            ))
    return violations


def _check_travel_distance(inputs: Dict) -> List[dict]:
    """
    P118 Art. 3.6.4 — Maximum travel distance to nearest exit.
    Max 30m general, 20m for dead-end paths.
    """
    violations = []
    plan_data = _extract_plan_data(inputs)
    distances = find_all_travel_distances(inputs)

    # Identify dead-end rooms: rooms connected to exactly one corridor/node
    graph = _build_graph(plan_data)
    dead_end_rooms = set()
    for room in plan_data.get("rooms", []):
        rid = room["id"]
        neighbors = graph.get(rid, {})
        if len(neighbors) <= 1:
            dead_end_rooms.add(rid)

    for room in plan_data.get("rooms", []):
        rid = room["id"]
        dist = distances.get(rid, float("inf"))

        if dist == float("inf"):
            violations.append(_make_violation(
                rule="travel_distance",
                article="P118 Art. 3.6.4",
                severity="critical",
                location=rid,
                description=f"Room '{room.get('name', rid)}' has no reachable exit.",
            ))
            continue

        if rid in dead_end_rooms:
            max_dist = config.P118_MAX_DEAD_END_TRAVEL
            label = "dead-end"
        else:
            max_dist = config.P118_MAX_TRAVEL_DISTANCE
            label = "general"

        if dist > max_dist:
            violations.append(_make_violation(
                rule="travel_distance",
                article="P118 Art. 3.6.4",
                severity="critical",
                location=rid,
                description=(
                    f"Room '{room.get('name', rid)}' travel distance to nearest exit "
                    f"is {dist:.1f}m, exceeding {label} limit of {max_dist}m."
                ),
                measured=dist,
                threshold=max_dist,
            ))
        else:
            violations.extend(_borderline_check(
                dist, max_dist,
                "travel_distance", "P118 Art. 3.6.4", rid,
                f"Room '{room.get('name', rid)}' travel distance ({dist:.1f}m) is near "
                f"the {label} limit of {max_dist}m.",
                is_min=False,
            ))

    return violations


def _check_exit_capacity(inputs: Dict) -> List[dict]:
    """
    P118 Art. 3.6.9 — Exit capacity: max 80 persons per 1m of exit width.
    """
    violations = []
    plan_data = _extract_plan_data(inputs)

    exits = plan_data.get("exits", [])
    rooms = plan_data.get("rooms", [])

    total_occupancy = sum(r.get("occupancy", 0) for r in rooms)

    if not exits:
        return violations

    # Compute total exit width
    total_exit_width = sum(ex.get("width", 1.2) for ex in exits)
    total_capacity = total_exit_width * config.P118_EXIT_CAPACITY_PER_METER

    if total_occupancy > total_capacity:
        violations.append(_make_violation(
            rule="exit_capacity",
            article="P118 Art. 3.6.9",
            severity="critical",
            location="building",
            description=(
                f"Total building occupancy ({total_occupancy}) exceeds total "
                f"exit capacity ({total_capacity:.0f} persons for "
                f"{total_exit_width:.1f}m total exit width)."
            ),
            measured=float(total_occupancy),
            threshold=total_capacity,
        ))

    # Also check individual exits
    for ex in exits:
        ex_width = ex.get("width", 1.2)
        ex_capacity = ex_width * config.P118_EXIT_CAPACITY_PER_METER
        # For individual exits, check against occupancy of rooms they directly serve
        ex_room = ex.get("room_id", "")
        room_occ = 0
        for r in rooms:
            if r["id"] == ex_room:
                room_occ = r.get("occupancy", 0)
                break

        if room_occ > ex_capacity:
            violations.append(_make_violation(
                rule="exit_capacity",
                article="P118 Art. 3.6.9",
                severity="major",
                location=ex.get("id", ""),
                description=(
                    f"Exit '{ex.get('id', '')}' serves room '{ex_room}' with "
                    f"occupancy {room_occ}, but capacity is only "
                    f"{ex_capacity:.0f} (width {ex_width}m × "
                    f"{config.P118_EXIT_CAPACITY_PER_METER} persons/m)."
                ),
                measured=float(room_occ),
                threshold=ex_capacity,
            ))

    return violations


def _check_door_widths(inputs: Dict) -> List[dict]:
    """
    P118 Art. 3.6.11 — Minimum door widths.
    Room doors: 0.9m. Exit/evacuation doors: 1.2m.
    """
    violations = []
    plan_data = _extract_plan_data(inputs)

    for door in plan_data.get("doors", []):
        width = door.get("width", 0.9)
        door_id = door.get("id", "")
        is_exit = door.get("is_exit", False)

        if is_exit:
            min_width = config.P118_MIN_DOOR_WIDTH_EXIT
            label = "exit door"
        else:
            min_width = config.P118_MIN_DOOR_WIDTH_ROOM
            label = "room door"

        if width < min_width:
            connects = door.get("connects", [])
            location = f"{door_id} ({' ↔ '.join(connects)})"
            violations.append(_make_violation(
                rule="door_width",
                article="P118 Art. 3.6.11",
                severity="critical" if is_exit else "major",
                location=location,
                description=(
                    f"Door '{door_id}' width is {width}m, below minimum "
                    f"{min_width}m for {label}."
                ),
                measured=width,
                threshold=min_width,
            ))

    # Also check exit widths (from exits list, not doors)
    for ex in plan_data.get("exits", []):
        width = ex.get("width", 1.2)
        ex_id = ex.get("id", "")
        if width < config.P118_MIN_DOOR_WIDTH_EXIT:
            violations.append(_make_violation(
                rule="door_width",
                article="P118 Art. 3.6.11",
                severity="critical",
                location=ex_id,
                description=(
                    f"Exit '{ex_id}' width is {width}m, below minimum "
                    f"{config.P118_MIN_DOOR_WIDTH_EXIT}m for exit doors."
                ),
                measured=width,
                threshold=config.P118_MIN_DOOR_WIDTH_EXIT,
            ))

    return violations


def _check_corridor_widths(inputs: Dict) -> List[dict]:
    """
    P118 Art. 3.6.12 — Minimum corridor width: 1.4m.
    """
    violations = []
    plan_data = _extract_plan_data(inputs)

    for corridor in plan_data.get("corridors", []):
        width = corridor.get("width", 1.4)
        cid = corridor.get("id", "")
        cname = corridor.get("name", cid)

        if width < config.P118_MIN_CORRIDOR_WIDTH:
            violations.append(_make_violation(
                rule="corridor_width",
                article="P118 Art. 3.6.12",
                severity="major",
                location=cid,
                description=(
                    f"Corridor '{cname}' width is {width}m, below minimum "
                    f"{config.P118_MIN_CORRIDOR_WIDTH}m."
                ),
                measured=width,
                threshold=config.P118_MIN_CORRIDOR_WIDTH,
            ))
        else:
            tol = config.P118_BORDERLINE_TOLERANCE * config.P118_MIN_CORRIDOR_WIDTH
            if width < config.P118_MIN_CORRIDOR_WIDTH + tol:
                violations.append(_make_violation(
                    rule="borderline_corridor_width",
                    article="P118 Art. 3.6.12",
                    severity="info",
                    location=cid,
                    description=(
                        f"BORDERLINE: Corridor '{cname}' width ({width}m) is just above "
                        f"the minimum {config.P118_MIN_CORRIDOR_WIDTH}m."
                    ),
                    measured=width,
                    threshold=config.P118_MIN_CORRIDOR_WIDTH,
                ))

    return violations


def _check_dead_ends(inputs: Dict) -> List[dict]:
    """
    P118 Art. 3.6.5 — Dead-end corridors must not exceed 12m.
    """
    violations = []
    plan_data = _extract_plan_data(inputs)
    graph = _build_graph(plan_data)

    corridor_ids = {c["id"] for c in plan_data.get("corridors", [])}

    for corridor in plan_data.get("corridors", []):
        cid = corridor["id"]
        cname = corridor.get("name", cid)
        length = corridor.get("length", 0.0)

        # A dead-end corridor connects to rooms on only one end
        # Check if corridor has connections to other corridors
        neighbors = graph.get(cid, {})
        corridor_neighbors = [n for n in neighbors if n in corridor_ids]

        # If corridor has no other corridor neighbor, it's a dead-end corridor
        if len(corridor_neighbors) == 0 and length > config.P118_MAX_DEAD_END_CORRIDOR:
            violations.append(_make_violation(
                rule="dead_end_corridor",
                article="P118 Art. 3.6.5",
                severity="major",
                location=cid,
                description=(
                    f"Corridor '{cname}' is a dead-end with length {length}m, "
                    f"exceeding maximum {config.P118_MAX_DEAD_END_CORRIDOR}m."
                ),
                measured=length,
                threshold=config.P118_MAX_DEAD_END_CORRIDOR,
            ))

    return violations


def _check_exit_count(inputs: Dict) -> List[dict]:
    """
    P118 Art. 3.6.2 — Minimum 2 exits per floor for occupancy > 50.
    """
    violations = []
    plan_data = _extract_plan_data(inputs)

    exits = plan_data.get("exits", [])
    rooms = plan_data.get("rooms", [])

    total_occupancy = sum(r.get("occupancy", 0) for r in rooms)
    exit_count = len(exits)

    if total_occupancy > config.P118_MIN_EXITS_THRESHOLD_OCCUPANCY:
        if exit_count < config.P118_MIN_EXITS_COUNT:
            violations.append(_make_violation(
                rule="exit_count",
                article="P118 Art. 3.6.2",
                severity="critical",
                location="building",
                description=(
                    f"Floor has {exit_count} exit(s) but total occupancy is "
                    f"{total_occupancy} (>{config.P118_MIN_EXITS_THRESHOLD_OCCUPANCY}). "
                    f"Minimum {config.P118_MIN_EXITS_COUNT} exits required."
                ),
                measured=float(exit_count),
                threshold=float(config.P118_MIN_EXITS_COUNT),
            ))

    return violations


def _check_room_exit_count(inputs: Dict) -> List[dict]:
    """
    P118 Art. 3.6.3 — Rooms with occupancy >= 50 require at least 2 independent exits.
    """
    violations = []
    plan_data = _extract_plan_data(inputs)
    graph = _build_graph(plan_data)
    exit_nodes = _find_exit_nodes(plan_data)

    for room in plan_data.get("rooms", []):
        rid = room["id"]
        rname = room.get("name", rid)
        occupancy = room.get("occupancy", 0)

        if occupancy < config.P118_ROOM_HIGH_OCCUPANCY:
            violations.extend(_borderline_check(
                occupancy, config.P118_ROOM_HIGH_OCCUPANCY,
                "room_exit_count", "P118 Art. 3.6.3", rid,
                f"Room '{rname}' occupancy ({occupancy}) is near the {config.P118_ROOM_HIGH_OCCUPANCY}-person "
                f"threshold requiring multiple exits.",
                is_min=True,
            ))
            continue

        neighbors = graph.get(rid, {})
        door_count = len(neighbors)

        if door_count < config.P118_ROOM_MIN_EXITS_HIGH_OCC:
            violations.append(_make_violation(
                rule="room_exit_count",
                article="P118 Art. 3.6.3",
                severity="critical",
                location=rid,
                description=(
                    f"Room '{rname}' has occupancy {occupancy} "
                    f"(>={config.P118_ROOM_HIGH_OCCUPANCY}) but only {door_count} "
                    f"exit path(s). Minimum {config.P118_ROOM_MIN_EXITS_HIGH_OCC} "
                    f"independent exits required."
                ),
                measured=float(door_count),
                threshold=float(config.P118_ROOM_MIN_EXITS_HIGH_OCC),
            ))

    return violations


def _check_emergency_lighting(inputs: Dict) -> List[dict]:
    """
    P118 Art. 4.2.1 — Emergency lighting required for:
    - Rooms with occupancy >= 30
    - Evacuation corridors >= 10m length
    """
    violations = []
    plan_data = _extract_plan_data(inputs)

    for room in plan_data.get("rooms", []):
        rid = room["id"]
        rname = room.get("name", rid)
        occupancy = room.get("occupancy", 0)
        has_lighting = room.get("emergency_lighting", False)

        if occupancy >= config.P118_EMERGENCY_LIGHTING_MIN_OCCUPANCY and not has_lighting:
            violations.append(_make_violation(
                rule="emergency_lighting",
                article="P118 Art. 4.2.1",
                severity="major",
                location=rid,
                description=(
                    f"Room '{rname}' has occupancy {occupancy} "
                    f"(>={config.P118_EMERGENCY_LIGHTING_MIN_OCCUPANCY}) but no "
                    f"emergency lighting indicated."
                ),
                measured=float(occupancy),
                threshold=float(config.P118_EMERGENCY_LIGHTING_MIN_OCCUPANCY),
            ))
        elif occupancy < config.P118_EMERGENCY_LIGHTING_MIN_OCCUPANCY:
            violations.extend(_borderline_check(
                occupancy, config.P118_EMERGENCY_LIGHTING_MIN_OCCUPANCY,
                "emergency_lighting", "P118 Art. 4.2.1", rid,
                f"Room '{rname}' occupancy ({occupancy}) is near the "
                f"{config.P118_EMERGENCY_LIGHTING_MIN_OCCUPANCY}-person emergency lighting threshold.",
                is_min=True,
            ))

    for corridor in plan_data.get("corridors", []):
        cid = corridor["id"]
        cname = corridor.get("name", cid)
        length = corridor.get("length", 0.0)
        has_lighting = corridor.get("emergency_lighting", False)

        if length >= config.P118_EMERGENCY_LIGHTING_CORRIDOR_MIN_LENGTH and not has_lighting:
            violations.append(_make_violation(
                rule="emergency_lighting",
                article="P118 Art. 4.2.1",
                severity="major",
                location=cid,
                description=(
                    f"Corridor '{cname}' length is {length}m "
                    f"(>={config.P118_EMERGENCY_LIGHTING_CORRIDOR_MIN_LENGTH}m) "
                    f"but no emergency lighting indicated."
                ),
                measured=length,
                threshold=config.P118_EMERGENCY_LIGHTING_CORRIDOR_MIN_LENGTH,
            ))

    return violations


def _borderline_check(
    value: float,
    threshold: float,
    rule: str,
    article: str,
    location: str,
    description: str,
    is_min: bool = False,
) -> List[dict]:
    """
    Flag values within BORDERLINE_TOLERANCE of a threshold as info-level warnings.
    Gives agents conversation context about near-miss situations.

    is_min=True: value approaching threshold from below (e.g., occupancy nearing 50).
    is_min=False: value approaching threshold from above (e.g., distance nearing 30m max).
    """
    tol = config.P118_BORDERLINE_TOLERANCE * threshold
    if is_min:
        if threshold - tol <= value < threshold:
            return [_make_violation(
                rule=f"borderline_{rule}",
                article=article,
                severity="info",
                location=location,
                description=f"BORDERLINE: {description}",
                measured=value,
                threshold=threshold,
            )]
    else:
        if threshold < value <= threshold + tol:
            return [_make_violation(
                rule=f"borderline_{rule}",
                article=article,
                severity="info",
                location=location,
                description=f"BORDERLINE: {description}",
                measured=value,
                threshold=threshold,
            )]
    return []
