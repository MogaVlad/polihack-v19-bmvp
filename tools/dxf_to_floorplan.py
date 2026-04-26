"""
Step 4 — Entity-to-FloorPlan mapping.

Converts raw DXF entities into a structured FloorPlan object,
identifying rooms, corridors, doors, exits, and walls with
automated spatial analysis and ambiguity flagging.
"""

import math
from typing import List, Tuple, Dict, Any, Optional

from models.floor_plan import FloorPlan, Room, Corridor, Door, Exit, Wall
from config import P118_OCCUPANCY_DENSITY


# ── Geometry helpers ───────────────────────────────────────────────

def _shoelace_area(vertices: List[List[float]]) -> float:
    """Compute area of a polygon using the shoelace formula."""
    n = len(vertices)
    if n < 3:
        return 0.0
    area = 0.0
    for i in range(n):
        j = (i + 1) % n
        area += vertices[i][0] * vertices[j][1]
        area -= vertices[j][0] * vertices[i][1]
    return abs(area) / 2.0


def _centroid(vertices: List[List[float]]) -> Tuple[float, float]:
    """Compute the centroid of a polygon."""
    n = len(vertices)
    if n == 0:
        return (0.0, 0.0)
    cx = sum(v[0] for v in vertices) / n
    cy = sum(v[1] for v in vertices) / n
    return (cx, cy)


def _bounding_box(vertices: List[List[float]]) -> Tuple[float, float, float, float]:
    """Return (min_x, min_y, max_x, max_y) bounding box."""
    xs = [v[0] for v in vertices]
    ys = [v[1] for v in vertices]
    return (min(xs), min(ys), max(xs), max(ys))


def _bbox_dimensions(vertices: List[List[float]]) -> Tuple[float, float]:
    """Return (width, height) of the bounding box."""
    min_x, min_y, max_x, max_y = _bounding_box(vertices)
    return (max_x - min_x, max_y - min_y)


def _aspect_ratio(vertices: List[List[float]]) -> float:
    """Return the aspect ratio (longer / shorter) of the bounding box."""
    w, h = _bbox_dimensions(vertices)
    if min(w, h) == 0:
        return float("inf")
    return max(w, h) / min(w, h)


def _point_in_polygon(px: float, py: float, vertices: List[List[float]]) -> bool:
    """Ray-casting point-in-polygon test."""
    n = len(vertices)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = vertices[i]
        xj, yj = vertices[j]
        if ((yi > py) != (yj > py)) and (px < (xj - xi) * (py - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def _distance(p1: List[float], p2: List[float]) -> float:
    """Euclidean distance between two 2D points."""
    return math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)


def _point_near_polygon(px: float, py: float, vertices: List[List[float]], tolerance: float = 2.0) -> bool:
    """Check if a point is inside or within tolerance of a polygon."""
    if _point_in_polygon(px, py, vertices):
        return True
    # Check distance to each edge
    n = len(vertices)
    for i in range(n):
        j = (i + 1) % n
        dist = _point_to_segment_distance(px, py, vertices[i], vertices[j])
        if dist <= tolerance:
            return True
    return False


def _point_to_segment_distance(px: float, py: float, a: List[float], b: List[float]) -> float:
    """Distance from point (px, py) to line segment a-b."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    length_sq = dx * dx + dy * dy
    if length_sq == 0:
        return _distance([px, py], a)
    t = max(0, min(1, ((px - a[0]) * dx + (py - a[1]) * dy) / length_sq))
    proj_x = a[0] + t * dx
    proj_y = a[1] + t * dy
    return _distance([px, py], [proj_x, proj_y])


def _segments_share_wall(verts_a: List[List[float]], verts_b: List[List[float]], tolerance: float = 1.0) -> bool:
    """Check if two polygons share a wall segment (any edge overlap within tolerance)."""
    for i in range(len(verts_a)):
        j = (i + 1) % len(verts_a)
        mid_a = [(verts_a[i][0] + verts_a[j][0]) / 2, (verts_a[i][1] + verts_a[j][1]) / 2]
        if _point_near_polygon(mid_a[0], mid_a[1], verts_b, tolerance):
            return True
    return False


# ── Room type classification ──────────────────────────────────────

ROOM_TYPE_KEYWORDS = {
    "office": ["office", "birou", "birouri"],
    "corridor": ["corridor", "coridor", "hall", "hol", "gang"],
    "stairwell": ["stair", "scara", "scari", "cage scara"],
    "wc": ["wc", "toilet", "toaleta", "baie", "bathroom", "restroom", "lavatory"],
    "conference": ["conference", "conf", "sala", "meeting", "sedinta", "intalnire"],
    "kitchen": ["kitchen", "bucatarie", "kitchenette", "pantry"],
    "lobby": ["lobby", "foyer", "vestibul", "entrance", "intrare"],
    "reception": ["reception", "receptie"],
    "storage": ["storage", "depozit", "arhiva", "archive", "magazie"],
    "server_room": ["server", "it room", "data"],
    "elevator": ["elevator", "lift", "ascensor"],
}


def _classify_room_type(label: str) -> str:
    """Classify room type from a text label using keyword matching."""
    lower = label.lower()
    for room_type, keywords in ROOM_TYPE_KEYWORDS.items():
        for kw in keywords:
            if kw in lower:
                return room_type
    return "office"  # default


def _estimate_occupancy(area: float, room_type: str) -> int:
    """Estimate occupancy from area using P118 density tables."""
    density = P118_OCCUPANCY_DENSITY.get(room_type, P118_OCCUPANCY_DENSITY["default"])
    if density <= 0:
        return 0
    return max(1, int(area / density))


# ── Main builder ──────────────────────────────────────────────────

def build_floor_plan(entities: dict) -> Tuple[FloorPlan, List[Dict[str, str]]]:
    """Convert extracted DXF entities into a FloorPlan and list of flagged issues.

    Args:
        entities: Dict from extract_entities() with polylines, lines, arcs, texts, blocks, layers.

    Returns:
        Tuple of (FloorPlan, list of flagged issue dicts).
    """
    issues: List[Dict[str, str]] = []

    # ── 4a: Identify rooms ────────────────────────────────────────
    closed_polys = [p for p in entities["polylines"] if p["is_closed"]]
    unclosed_room_polys = [
        p for p in entities["polylines"]
        if not p["is_closed"] and p["layer_category"] in ("room", "wall", "unknown")
    ]

    # Separate corridor candidates (aspect ratio > 3:1 or on corridor layer)
    room_polys = []
    corridor_polys = []

    for poly in closed_polys:
        verts = poly["vertices"]
        if len(verts) < 3:
            continue
        ar = _aspect_ratio(verts)
        layer_cat = poly["layer_category"]

        is_corridor = (
            layer_cat == "room" and ar > 3.0
        ) or (
            layer_cat == "unknown" and ar > 4.0
        ) or any(
            kw in poly["layer"].upper() for kw in ("CORR", "CORRIDOR", "HALL")
        )

        if is_corridor:
            corridor_polys.append(poly)
        elif layer_cat in ("wall", "room", "unknown"):
            room_polys.append(poly)

    # Build rooms
    rooms: List[Room] = []
    room_vertices_map: Dict[str, List[List[float]]] = {}  # room_id → vertices
    consumed_labels: set = set()  # track used text labels to avoid reuse

    for idx, poly in enumerate(room_polys):
        verts = poly["vertices"]
        area = _shoelace_area(verts)
        if area < 1.0:  # skip tiny polygons (< 1 m²)
            continue

        room_id = f"R{idx + 1}"

        # Find best text label for this polygon:
        # Priority: (1) text inside polygon, (2) text near polygon
        matched_label = ""
        matched_idx = -1
        best_inside_dist = float("inf")
        best_near_dist = float("inf")
        centroid_pt = _centroid(verts)

        for ti, text in enumerate(entities["texts"]):
            if ti in consumed_labels:
                continue
            pos = text["position"]
            dist_to_center = _distance(pos, list(centroid_pt))

            if _point_in_polygon(pos[0], pos[1], verts):
                if dist_to_center < best_inside_dist:
                    best_inside_dist = dist_to_center
                    matched_label = text["content"]
                    matched_idx = ti
            elif matched_idx == -1 or best_inside_dist == float("inf"):
                if _point_near_polygon(pos[0], pos[1], verts, tolerance=1.5):
                    if dist_to_center < best_near_dist:
                        best_near_dist = dist_to_center
                        if best_inside_dist == float("inf"):  # only use near if no inside match
                            matched_label = text["content"]
                            matched_idx = ti

        if matched_idx >= 0:
            consumed_labels.add(matched_idx)

        room_type = _classify_room_type(matched_label) if matched_label else "office"
        room_name = matched_label if matched_label else f"Room {idx + 1}"
        occupancy = _estimate_occupancy(area, room_type)

        rooms.append(Room(
            id=room_id,
            name=room_name,
            type=room_type,
            polygon=[tuple(v) for v in verts],
            area=round(area, 2),
            occupancy=occupancy,
        ))
        room_vertices_map[room_id] = verts

    # ── 4b: Identify corridors ────────────────────────────────────
    corridors: List[Corridor] = []
    corridor_vertices_map: Dict[str, List[List[float]]] = {}

    for idx, poly in enumerate(corridor_polys):
        verts = poly["vertices"]
        area = _shoelace_area(verts)
        if area < 1.0:
            continue

        corr_id = f"C{idx + 1}"
        w, h = _bbox_dimensions(verts)
        width = min(w, h)
        length = max(w, h)

        # Find connected rooms (those sharing a wall segment)
        connects = []
        for room_id, r_verts in room_vertices_map.items():
            if _segments_share_wall(verts, r_verts):
                connects.append(room_id)

        # Try to find a label (prefer inside, then near; skip consumed)
        matched_label = ""
        corr_matched_idx = -1
        corr_centroid = _centroid(verts)
        best_dist = float("inf")

        for ti, text in enumerate(entities["texts"]):
            if ti in consumed_labels:
                continue
            pos = text["position"]
            if _point_in_polygon(pos[0], pos[1], verts):
                dist = _distance(pos, list(corr_centroid))
                if dist < best_dist:
                    best_dist = dist
                    matched_label = text["content"]
                    corr_matched_idx = ti
            elif corr_matched_idx == -1 and _point_near_polygon(pos[0], pos[1], verts, tolerance=1.5):
                dist = _distance(pos, list(corr_centroid))
                if dist < best_dist:
                    best_dist = dist
                    matched_label = text["content"]
                    corr_matched_idx = ti

        if corr_matched_idx >= 0:
            consumed_labels.add(corr_matched_idx)

        corridors.append(Corridor(
            id=corr_id,
            name=matched_label if matched_label else f"Corridor {idx + 1}",
            width=round(width, 2),
            length=round(length, 2),
            connects=connects,
            polygon=[tuple(v) for v in verts],
        ))
        corridor_vertices_map[corr_id] = verts

    # Combine all space vertices for door-space matching
    all_space_verts: Dict[str, List[List[float]]] = {}
    all_space_verts.update(room_vertices_map)
    all_space_verts.update(corridor_vertices_map)

    # ── 4c: Identify doors ────────────────────────────────────────
    doors: List[Door] = []
    door_candidates: List[Dict[str, Any]] = []

    # Arcs (door swings)
    for arc in entities["arcs"]:
        if arc["layer_category"] in ("door", "unknown"):
            door_candidates.append({
                "position": arc["center"],
                "width": round(arc["radius"] * 2, 2),
                "source": "arc",
                "name": "",
            })

    # Block inserts referencing door blocks
    for block in entities["blocks"]:
        name_upper = block["name"].upper()
        if block["layer_category"] == "door" or any(kw in name_upper for kw in ("DOOR", "DR", "USI", "USA")):
            door_candidates.append({
                "position": block["position"],
                "width": 0.9,  # default door width, may be overridden by block attributes
                "source": "block",
                "name": block["name"],
            })

    for idx, dc in enumerate(door_candidates):
        door_id = f"D{idx + 1}"
        pos = dc["position"]

        # Find which spaces this door connects (nearest two polygons)
        connects = []
        for space_id, s_verts in all_space_verts.items():
            if _point_near_polygon(pos[0], pos[1], s_verts, tolerance=dc["width"] + 1.0):
                connects.append(space_id)
            if len(connects) >= 2:
                break

        # Check if it's an exit:
        # - Only one space on one side (the other side is outside)
        # - Or a door at the building boundary (near edge of all polygons)
        # - Or block name contains exit keywords
        is_exit = len(connects) < 2
        if not is_exit:
            # Check if the door position is at the extremes of the building envelope
            all_xs = [v[0] for vs in all_space_verts.values() for v in vs]
            all_ys = [v[1] for vs in all_space_verts.values() for v in vs]
            if all_xs and all_ys:
                margin = 0.5
                at_edge = (
                    pos[0] <= min(all_xs) + margin or pos[0] >= max(all_xs) - margin or
                    pos[1] <= min(all_ys) + margin or pos[1] >= max(all_ys) - margin
                )
                if at_edge:
                    is_exit = True
        if dc["name"]:
            name_upper = dc["name"].upper()
            if any(kw in name_upper for kw in ("EXIT", "IESIRE", "EVACUARE")):
                is_exit = True

        doors.append(Door(
            id=door_id,
            connects=connects,
            width=dc["width"],
            position=(pos[0], pos[1]),
            is_exit=is_exit,
        ))

    # ── 4d: Identify exits ────────────────────────────────────────
    exits: List[Exit] = []

    # From doors flagged as exits
    for door in doors:
        if door.is_exit:
            room_id = door.connects[0] if door.connects else ""
            exits.append(Exit(
                id=f"E{len(exits) + 1}",
                room_id=room_id,
                position=door.position,
                width=door.width,
                leads_outside=True,
            ))

    # From block references with exit names
    for block in entities["blocks"]:
        name_upper = block["name"].upper()
        if any(kw in name_upper for kw in ("EXIT", "IESIRE", "EVACUARE", "EMERGENCY")):
            pos = block["position"]
            # Avoid duplicating if already captured from a door
            already = any(
                _distance(list(e.position), pos) < 1.0 for e in exits
            )
            if not already:
                # Find nearest space
                nearest_space = ""
                min_dist = float("inf")
                for space_id, s_verts in all_space_verts.items():
                    c = _centroid(s_verts)
                    d = _distance(pos, list(c))
                    if d < min_dist:
                        min_dist = d
                        nearest_space = space_id
                exits.append(Exit(
                    id=f"E{len(exits) + 1}",
                    room_id=nearest_space,
                    position=(pos[0], pos[1]),
                    width=1.2,
                    leads_outside=True,
                ))

    # ── 4e: Identify walls ────────────────────────────────────────
    walls: List[Wall] = []

    # From LINE entities on wall layers
    for idx, line in enumerate(entities["lines"]):
        if line["layer_category"] in ("wall", "unknown"):
            start = line["start"]
            end = line["end"]
            # Find which room this wall belongs to
            mid = [(start[0] + end[0]) / 2, (start[1] + end[1]) / 2]
            room_id = ""
            for r_id, r_verts in room_vertices_map.items():
                if _point_near_polygon(mid[0], mid[1], r_verts, tolerance=1.0):
                    room_id = r_id
                    break
            walls.append(Wall(
                id=f"W{idx + 1}",
                start=(start[0], start[1]),
                end=(end[0], end[1]),
                room_id=room_id,
            ))

    # From room/corridor polygon edges
    wall_idx_offset = len(walls)
    for space_id, s_verts in all_space_verts.items():
        for i in range(len(s_verts)):
            j = (i + 1) % len(s_verts)
            walls.append(Wall(
                id=f"W{wall_idx_offset + 1}",
                start=(s_verts[i][0], s_verts[i][1]),
                end=(s_verts[j][0], s_verts[j][1]),
                room_id=space_id,
            ))
            wall_idx_offset += 1

    # ── 4f: Flag ambiguities ──────────────────────────────────────

    # Unclosed polylines on room layers
    for poly in unclosed_room_polys:
        issues.append({
            "type": "warning",
            "message": f"Possible incomplete room boundary on layer '{poly['layer']}' "
                       f"({len(poly['vertices'])} vertices, not closed)",
        })

    # Rooms with no detected door
    rooms_with_doors = set()
    for door in doors:
        for c in door.connects:
            rooms_with_doors.add(c)
    for room in rooms:
        if room.id not in rooms_with_doors:
            issues.append({
                "type": "warning",
                "message": f"Room {room.id} ('{room.name}') has no door connection",
            })

    # Overlapping room polygons
    for i, r1 in enumerate(rooms):
        for j, r2 in enumerate(rooms):
            if j <= i:
                continue
            c1 = _centroid([list(p) for p in r1.polygon])
            c2 = _centroid([list(p) for p in r2.polygon])
            if _point_in_polygon(c1[0], c1[1], [list(p) for p in r2.polygon]):
                issues.append({
                    "type": "warning",
                    "message": f"Rooms {r1.id} and {r2.id} may overlap (centroid of {r1.id} is inside {r2.id})",
                })

    # Unmatched text labels
    matched_texts = set()
    for room in rooms:
        if room.name and not room.name.startswith("Room "):
            matched_texts.add(room.name)
    for corridor in corridors:
        if corridor.name and not corridor.name.startswith("Corridor "):
            matched_texts.add(corridor.name)
    for text in entities["texts"]:
        content = text["content"].strip()
        if content and content not in matched_texts and text["layer_category"] in ("text", "room", "unknown"):
            issues.append({
                "type": "info",
                "message": f"Unmatched label: '{content}' at position ({text['position'][0]:.1f}, {text['position'][1]:.1f})",
            })

    # Build the FloorPlan
    floor_plan = FloorPlan(
        id="dxf_parsed",
        name="DXF Parsed Floor Plan",
        floor=0,
        rooms=rooms,
        corridors=corridors,
        doors=doors,
        exits=exits,
        walls=walls,
    )

    return floor_plan, issues
