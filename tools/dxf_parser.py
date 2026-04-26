"""
Step 3 — DXF entity extraction.

Opens a DXF file with ezdxf and extracts all relevant entities
(polylines, lines, arcs, texts, block references) grouped by layer.
"""

import ezdxf
from typing import Dict, List, Any


# ── Layer classification patterns ──────────────────────────────────

LAYER_PATTERNS: Dict[str, List[str]] = {
    "wall": ["A-WALL", "WALL", "WALLS", "S-WALL", "AR-WALL"],
    "door": ["A-DOOR", "DOOR", "DOORS", "AR-DOOR"],
    "room": ["A-ROOM", "ROOM", "ROOMS", "A-AREA", "SPACE"],
    "text": ["A-TEXT", "TEXT", "ANNO", "A-ANNO", "LABEL"],
    "furniture": ["A-FURN", "FURN", "FURNITURE"],
    "window": ["A-GLAZ", "WINDOW", "WIN"],
}


def classify_layer(layer_name: str) -> str:
    """Classify a layer name into a category using known patterns.

    Returns one of: wall, door, room, text, furniture, window, or 'unknown'.
    """
    upper = layer_name.upper()
    for category, patterns in LAYER_PATTERNS.items():
        for pattern in patterns:
            if pattern in upper:
                return category
    return "unknown"


def extract_entities(dxf_path: str) -> dict:
    """Extract all relevant entities from a DXF file.

    Args:
        dxf_path: Path to the .dxf file.

    Returns:
        Dict with keys: polylines, lines, arcs, texts, blocks, layers.
    """
    from ezdxf import recover
    
    try:
        doc, auditor = recover.readfile(dxf_path)
    except Exception as e:
        # Fallback to standard readfile if recover somehow fails (rare)
        # or if the file is truly unreadable, let it raise so it's caught later
        doc = ezdxf.readfile(dxf_path)

    msp = doc.modelspace()

    polylines: List[Dict[str, Any]] = []
    lines: List[Dict[str, Any]] = []
    arcs: List[Dict[str, Any]] = []
    texts: List[Dict[str, Any]] = []
    blocks: List[Dict[str, Any]] = []
    layer_set: set = set()

    for entity in msp:
        layer = entity.dxf.layer if hasattr(entity.dxf, "layer") else "0"
        layer_set.add(layer)
        layer_category = classify_layer(layer)

        dxf_type = entity.dxftype()

        if dxf_type in ("LWPOLYLINE", "POLYLINE"):
            try:
                if dxf_type == "LWPOLYLINE":
                    vertices = [[p[0], p[1]] for p in entity.get_points(format="xy")]
                    is_closed = entity.closed
                else:
                    # POLYLINE (2D/3D)
                    vertices = [[v.dxf.location.x, v.dxf.location.y] for v in entity.vertices]
                    is_closed = entity.is_closed
                polylines.append({
                    "vertices": vertices,
                    "layer": layer,
                    "layer_category": layer_category,
                    "is_closed": bool(is_closed),
                })
            except Exception:
                continue

        elif dxf_type == "LINE":
            start = entity.dxf.start
            end = entity.dxf.end
            lines.append({
                "start": [start.x, start.y],
                "end": [end.x, end.y],
                "layer": layer,
                "layer_category": layer_category,
            })

        elif dxf_type in ("CIRCLE", "ARC"):
            center = entity.dxf.center
            radius = entity.dxf.radius
            entry = {
                "center": [center.x, center.y],
                "radius": radius,
                "layer": layer,
                "layer_category": layer_category,
            }
            if dxf_type == "ARC":
                entry["start_angle"] = entity.dxf.start_angle
                entry["end_angle"] = entity.dxf.end_angle
            else:
                entry["start_angle"] = 0.0
                entry["end_angle"] = 360.0
            arcs.append(entry)

        elif dxf_type in ("TEXT", "MTEXT"):
            try:
                if dxf_type == "TEXT":
                    content = entity.dxf.text
                    pos = entity.dxf.insert
                else:
                    content = entity.text  # MTEXT plain text
                    pos = entity.dxf.insert
                texts.append({
                    "content": content.strip(),
                    "position": [pos.x, pos.y],
                    "layer": layer,
                    "layer_category": layer_category,
                })
            except Exception:
                continue

        elif dxf_type == "INSERT":
            try:
                pos = entity.dxf.insert
                blocks.append({
                    "name": entity.dxf.name,
                    "position": [pos.x, pos.y],
                    "layer": layer,
                    "layer_category": layer_category,
                })
            except Exception:
                continue

    return {
        "polylines": polylines,
        "lines": lines,
        "arcs": arcs,
        "texts": texts,
        "blocks": blocks,
        "layers": sorted(layer_set),
    }
