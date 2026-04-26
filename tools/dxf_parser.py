import math
import os
from typing import Dict, List, Tuple

import ezdxf

import config
from models.floor_plan import FloorPlan, Room, Corridor, Door, Exit, Wall


ROOM_LAYERS = {"A-ROOM", "ROOM", "ROOMS", "A-AREA", "SPACE"}
CORRIDOR_LAYERS = {"A-CORRIDOR", "CORRIDOR", "CORRIDORS", "HALL", "HALLWAY"}
WALL_LAYERS = {"A-WALL", "WALL", "WALLS", "S-WALL", "AR-WALL"}
DOOR_LAYERS = {"A-DOOR", "DOOR", "DOORS", "AR-DOOR"}
TEXT_LAYERS = {"A-TEXT", "TEXT", "ANNO", "A-ANNO", "LABEL"}
WINDOW_LAYERS = {"A-GLAZ", "WINDOW", "WIN"}


def _layer_match(layer: str, candidates: set) -> bool:
    if not layer:
        return False
    upper = layer.upper()
    return upper in candidates


def extract_entities(dxf_path: str) -> dict:
    if not os.path.isfile(dxf_path):
        raise FileNotFoundError(f"DXF file not found: {dxf_path}")

    doc = ezdxf.readfile(dxf_path)
    msp = doc.modelspace()

    polylines = []
    lines = []
    arcs = []
    texts = []
    blocks = []
    layers = set()

    def handle_entity(entity, fallback_layer: str | None = None):
        etype = entity.dxftype()
        layer = fallback_layer or (entity.dxf.layer if hasattr(entity, "dxf") else "")
        if layer:
            layers.add(layer)

        if etype in ("LWPOLYLINE", "POLYLINE"):
            vertices = []
            if etype == "LWPOLYLINE":
                vertices = [[p[0], p[1]] for p in entity.get_points("xy")]
                is_closed = bool(entity.closed)
            else:
                vertices = [[v.dxf.location.x, v.dxf.location.y] for v in entity.vertices]
                is_closed = bool(entity.is_closed)
            if len(vertices) > 2 and vertices[0] == vertices[-1]:
                is_closed = True
            polylines.append({"vertices": vertices, "layer": layer, "is_closed": is_closed})
            return

        if etype == "SPLINE":
            try:
                points = [[p.x, p.y] for p in entity.flattening(distance=1.0)]
            except Exception:
                points = []
            if points:
                is_closed = bool(getattr(entity, "closed", False)) or (len(points) > 2 and points[0] == points[-1])
                polylines.append({"vertices": points, "layer": layer, "is_closed": is_closed})
            return

        if etype == "LINE":
            start = [entity.dxf.start.x, entity.dxf.start.y]
            end = [entity.dxf.end.x, entity.dxf.end.y]
            lines.append({"start": start, "end": end, "layer": layer})
            return

        if etype in ("CIRCLE", "ARC"):
            center = [entity.dxf.center.x, entity.dxf.center.y]
            radius = float(entity.dxf.radius)
            start_angle = getattr(entity.dxf, "start_angle", 0.0)
            end_angle = getattr(entity.dxf, "end_angle", 360.0)
            arcs.append({
                "center": center,
                "radius": radius,
                "start_angle": start_angle,
                "end_angle": end_angle,
                "layer": layer,
            })
            return

        if etype in ("TEXT", "MTEXT"):
            if etype == "MTEXT":
                content = entity.plain_text()
                pos = entity.dxf.insert
            else:
                content = entity.dxf.text
                pos = entity.dxf.insert
            texts.append({"content": content, "position": [pos.x, pos.y], "layer": layer})
            return

        if etype == "HATCH":
            try:
                for path in entity.paths:
                    if hasattr(path, "vertices"):
                        vertices = [[v[0], v[1]] for v in path.vertices]
                        if len(vertices) > 2:
                            polylines.append({"vertices": vertices, "layer": layer, "is_closed": True})
                    else:
                        edge_vertices = []
                        for edge in getattr(path, "edges", []):
                            if edge.EDGE_TYPE == "LineEdge":
                                edge_vertices.append([edge.start[0], edge.start[1]])
                                edge_vertices.append([edge.end[0], edge.end[1]])
                        if len(edge_vertices) > 2:
                            polylines.append({"vertices": edge_vertices, "layer": layer, "is_closed": True})
            except Exception:
                pass
            return

        if etype == "INSERT":
            pos = entity.dxf.insert
            blocks.append({"name": entity.dxf.name, "position": [pos.x, pos.y], "layer": layer})
            try:
                for virtual in entity.virtual_entities():
                    handle_entity(virtual, fallback_layer=layer)
            except Exception:
                pass
            return

    for entity in msp:
        handle_entity(entity)

    for layout in doc.layouts:
        if layout.name.lower() == "model":
            continue
        for entity in layout:
            handle_entity(entity)

    return {
        "polylines": polylines,
        "lines": lines,
        "arcs": arcs,
        "texts": texts,
        "blocks": blocks,
        "layers": sorted(layers),
    }


def build_floor_plan(entities: dict) -> Tuple[FloorPlan, List[str]]:
    polylines = entities.get("polylines", [])
    lines = entities.get("lines", [])
    arcs = entities.get("arcs", [])
    texts = entities.get("texts", [])
    blocks = entities.get("blocks", [])

    issues = []
    rooms: List[Room] = []
    corridors: List[Corridor] = []
    doors: List[Door] = []
    exits: List[Exit] = []
    walls: List[Wall] = []

    closed_polys = [p for p in polylines if p.get("is_closed")]
    open_room_polys = [p for p in polylines if not p.get("is_closed") and _layer_match(p.get("layer", ""), ROOM_LAYERS)]

    for poly in open_room_polys:
        issues.append("Possible incomplete room boundary")

    room_id = 1
    corridor_id = 1

    for poly in closed_polys:
        vertices = [tuple(v) for v in poly.get("vertices", [])]
        if len(vertices) < 3:
            continue

        layer = (poly.get("layer") or "").upper()
        area = _polygon_area(vertices)
        bbox = _bbox(vertices)
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]
        aspect = max(width, height) / max(1e-6, min(width, height))

        is_corridor = _layer_match(layer, CORRIDOR_LAYERS) or aspect >= 3.0
        label = _nearest_label(vertices, texts)
        name = label or (f"Corridor {corridor_id}" if is_corridor else f"Room {room_id}")
        room_type = _classify_room_type(label or "", is_corridor)

        if is_corridor:
            corridor = Corridor(
                id=f"C{corridor_id}",
                name=name,
                width=min(width, height),
                length=max(width, height),
                connects=[],
                polygon=vertices,
                floor=0,
            )
            corridors.append(corridor)
            corridor_id += 1
        else:
            occupancy = _estimate_occupancy(area, room_type)
            room = Room(
                id=f"R{room_id}",
                name=name,
                type=room_type,
                polygon=vertices,
                area=area,
                occupancy=occupancy,
                floor=0,
            )
            rooms.append(room)
            room_id += 1

    for line in lines:
        walls.append(
            Wall(
                id=f"W{len(walls) + 1}",
                start=tuple(line.get("start", (0, 0))),
                end=tuple(line.get("end", (0, 0))),
                room_id="",
            )
        )

    space_polys = [(r.id, r.polygon) for r in rooms] + [(c.id, c.polygon) for c in corridors]

    for arc in arcs:
        center = tuple(arc.get("center", (0, 0)))
        width = float(arc.get("radius", 0.9)) * 2.0
        connects = _nearest_spaces(center, space_polys)
        is_exit = len(connects) < 2
        door = Door(
            id=f"D{len(doors) + 1}",
            connects=connects,
            width=width,
            position=center,
            is_exit=is_exit,
        )
        doors.append(door)

    for block in blocks:
        name = (block.get("name") or "").lower()
        position = tuple(block.get("position", (0, 0)))
        layer = (block.get("layer") or "").upper()
        is_door = _layer_match(layer, DOOR_LAYERS) or "door" in name
        is_exit = "exit" in name
        if not is_door and not is_exit:
            continue
        connects = _nearest_spaces(position, space_polys)
        door = Door(
            id=f"D{len(doors) + 1}",
            connects=connects,
            width=1.0,
            position=position,
            is_exit=is_exit or len(connects) < 2,
        )
        doors.append(door)

    for door in doors:
        if door.is_exit:
            room_id = door.connects[0] if door.connects else ""
            exits.append(
                Exit(
                    id=f"E{len(exits) + 1}",
                    room_id=room_id,
                    position=door.position,
                    width=door.width,
                    leads_outside=True,
                )
            )

    for room in rooms:
        if not any(room.id in d.connects for d in doors):
            issues.append(f"Room {room.name} has no door connection")

    for i in range(len(rooms)):
        for j in range(i + 1, len(rooms)):
            if _polygons_overlap(rooms[i].polygon, rooms[j].polygon):
                issues.append(f"Rooms {rooms[i].name} and {rooms[j].name} overlap")

    for text in texts:
        if not _label_used(text, rooms, corridors):
            issues.append(f"Unmatched label: {text.get('content', '').strip()}")

    if not rooms and not corridors and not walls:
        issues.append("No rooms, corridors, or walls detected in DXF.")
    elif not rooms and not corridors:
        issues.append("No closed room/corridor boundaries detected. Ensure rooms are closed polylines or hatches.")

    plan = FloorPlan(
        id="dxf_plan",
        name="DXF Plan",
        floor=0,
        rooms=rooms,
        corridors=corridors,
        doors=doors,
        exits=exits,
        walls=walls,
    )

    return plan, issues


def _polygon_area(vertices: List[Tuple[float, float]]) -> float:
    area = 0.0
    for i in range(len(vertices)):
        x1, y1 = vertices[i]
        x2, y2 = vertices[(i + 1) % len(vertices)]
        area += x1 * y2 - x2 * y1
    return abs(area) / 2.0


def _bbox(vertices: List[Tuple[float, float]]) -> Tuple[float, float, float, float]:
    xs = [p[0] for p in vertices]
    ys = [p[1] for p in vertices]
    return min(xs), min(ys), max(xs), max(ys)


def _point_in_polygon(point: Tuple[float, float], polygon: List[Tuple[float, float]]) -> bool:
    x, y = point
    inside = False
    n = len(polygon)
    for i in range(n):
        x1, y1 = polygon[i]
        x2, y2 = polygon[(i + 1) % n]
        if ((y1 > y) != (y2 > y)) and (x < (x2 - x1) * (y - y1) / (y2 - y1 + 1e-9) + x1):
            inside = not inside
    return inside


def _nearest_label(polygon: List[Tuple[float, float]], texts: List[dict]) -> str | None:
    if not texts:
        return None
    bbox = _bbox(polygon)
    candidates = []
    for text in texts:
        pos = tuple(text.get("position", (0, 0)))
        if bbox[0] <= pos[0] <= bbox[2] and bbox[1] <= pos[1] <= bbox[3]:
            if _point_in_polygon(pos, polygon):
                candidates.append(text)
    if not candidates:
        return None
    return (candidates[0].get("content") or "").strip()


def _classify_room_type(label: str, is_corridor: bool) -> str:
    if is_corridor:
        return "corridor"
    text = (label or "").lower()
    for key, value in {
        "office": "office",
        "corridor": "corridor",
        "hall": "corridor",
        "stair": "stairwell",
        "wc": "wc",
        "toilet": "wc",
        "conference": "conference",
        "server": "server",
    }.items():
        if key in text:
            return value
    return "office"


def _estimate_occupancy(area: float, room_type: str) -> int:
    density = getattr(config, "P118_OCCUPANCY_DENSITY", {}).get(room_type, 10.0)
    return max(1, int(round(area / max(density, 0.1))))


def _nearest_spaces(point: Tuple[float, float], spaces: List[Tuple[str, List[Tuple[float, float]]]]) -> List[str]:
    distances = []
    for sid, poly in spaces:
        center = _polygon_centroid(poly)
        dist = math.dist(point, center)
        distances.append((dist, sid))
    distances.sort(key=lambda d: d[0])
    return [sid for _, sid in distances[:2]]


def _polygon_centroid(vertices: List[Tuple[float, float]]) -> Tuple[float, float]:
    if not vertices:
        return (0.0, 0.0)
    x = sum(p[0] for p in vertices) / len(vertices)
    y = sum(p[1] for p in vertices) / len(vertices)
    return (x, y)


def _polygons_overlap(a: List[Tuple[float, float]], b: List[Tuple[float, float]]) -> bool:
    if not a or not b:
        return False
    for point in a:
        if _point_in_polygon(point, b):
            return True
    for point in b:
        if _point_in_polygon(point, a):
            return True
    return False


def _label_used(text: dict, rooms: List[Room], corridors: List[Corridor]) -> bool:
    label = (text.get("content") or "").strip().lower()
    if not label:
        return True
    for room in rooms:
        if label == room.name.lower():
            return True
    for corridor in corridors:
        if label == corridor.name.lower():
            return True
    return False
