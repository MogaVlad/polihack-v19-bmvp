# Floor Plan Parsing — Implementation Status

## Overview

The Floor Plan Parser agent accepts three input formats and converts them into the `FloorPlan` JSON schema (rooms, corridors, doors, exits, walls with real coordinates). The P118 tools then work with precise measurements.

**Supported formats**:
- **DXF** — parsed directly via `ezdxf` into exact geometry (primary path)
- **Images** (PNG, JPG, JPEG, BMP, TIFF, GIF) — parsed via Gemini Vision AI
- **PDF** — accepted in the file picker; handled through Gemini Vision
- **JSON** — hand-authored or previously-parsed `FloorPlan` JSON files (in `data/floor_plans/`)

DWG support is **not implemented** — DXF only for now.

---

## Step 1 — Dependencies ✅

`ezdxf` added to `requirements.txt`. Installed via:

```bash
pip install ezdxf
```

Full `requirements.txt`:
```
google-genai
Pillow
python-dotenv
PyQt6
ezdxf
```

---

## Step 2 — DWG-to-DXF conversion ❌ Deferred

Originally planned to use libredwg or ODA File Converter for DWG → DXF conversion. **Not implemented.** The parser only accepts `.dxf` files natively.

If DWG support is needed later, create `tools/dwg_converter.py` that shells out to `dwg2dxf` (from libredwg) or ODA File Converter.

---

## Step 3 — DXF entity extraction ✅

Implemented in **`tools/dxf_parser.py`** → `extract_entities(dxf_path) -> dict`.

Handles these entity types:
- **LWPOLYLINE / POLYLINE** → room/corridor boundaries (vertices + closed flag)
- **SPLINE** → flattened to polyline points
- **LINE** → wall segments (start, end)
- **CIRCLE / ARC** → door swings (center, radius, angles)
- **TEXT / MTEXT** → room labels (content, position)
- **HATCH** → boundary paths extracted as closed polylines
- **INSERT** (block references) → door/window/exit symbols; virtual entities recursively processed

Entities grouped by layer. Also scans non-model layouts.

Returns:
```python
{
    "polylines": [...],    # {vertices, layer, is_closed}
    "lines": [...],        # {start, end, layer}
    "arcs": [...],         # {center, radius, start_angle, end_angle, layer}
    "texts": [...],        # {content, position, layer}
    "blocks": [...],       # {name, position, layer}
    "layers": [...]        # sorted list of layer names found
}
```

---

## Step 4 — Entity-to-FloorPlan mapping ✅

Implemented in **`tools/dxf_parser.py`** → `build_floor_plan(entities) -> Tuple[FloorPlan, List[str]]`.

### 4a — Rooms
- All closed polylines → candidate rooms.
- Area computed via shoelace formula (`_polygon_area`).
- Nearest TEXT label matched via point-in-polygon test (`_nearest_label`).
- Room type classified by keyword matching (`_classify_room_type`): office, corridor, stairwell, WC, conference, server.
- Occupancy estimated from area ÷ P118 density table (`_estimate_occupancy` using `config.P118_OCCUPANCY_DENSITY`).
- IDs: `R1`, `R2`, ... in discovery order.

### 4b — Corridors
- Closed polylines with aspect ratio ≥ 3:1 or on corridor layers (`A-CORRIDOR`, `CORRIDOR`, `HALL`, etc.).
- Width = shorter bbox dimension, length = longer.
- IDs: `C1`, `C2`, ...

### 4c — Doors
- ARC entities → door width = radius × 2, position = arc center.
- INSERT blocks on door layers or with "door" in the block name.
- `connects` = two nearest rooms/corridors by centroid distance.
- `is_exit` = True if fewer than 2 adjacent spaces (leads outside) or block name contains "exit".

### 4d — Exits
- Every door with `is_exit=True` generates a corresponding `Exit` entry.

### 4e — Walls
- All LINE entities → `Wall` with start/end coordinates.

### 4f — Flagged issues
- Unclosed polylines on room layers → "Possible incomplete room boundary"
- Rooms with no door connection → "Room X has no door connection"
- Overlapping room polygons → "Rooms X and Y overlap"
- Unmatched text labels → "Unmatched label: ..."
- No geometry at all → "No rooms, corridors, or walls detected in DXF."

---

## Step 5 — Tool registration ✅

In **`tools/registry.py`**, two tools registered for the Floor Plan Parser:

1. **`dxf_parser`** — calls `extract_entities` → `build_floor_plan`, returns `{parsed_plan, flagged_issues}`. Only runs on `.dxf` files; skips otherwise.

2. **`gemini_vision`** — sends the image to `GeminiClient.parse_image()` with a structured prompt asking for rooms, corridors, doors, exits, stairs, and ambiguities. Only runs on image files (PNG/JPG/BMP/TIFF/GIF); skips for non-image input.

Both tools are in the agent's tool list. The engine runs all tools and injects their results into the LLM prompt. For a DXF file, `dxf_parser` produces exact geometry and `gemini_vision` returns `{"skipped": ...}`. For an image, the reverse.

---

## Step 6 — Agent definition ✅

**`data/agents/floor_plan_parser.json`** updated:

- **Input**: `floor_plan` with type `file` — accepts `.json`, `.dxf`, or image files.
- **Tools**: `["dxf_parser", "gemini_vision"]`
- **Constraints** include: "For DXF files, use the dxf_parser tool for precise extraction. For images, fall back to gemini_vision."
- **Outputs**: `parsed_plan` (json), `flagged_issues` (json)
- **Conversational**: true, with guidelines for proactive flagging and scope boundaries.

---

## Step 7 — UI file picker ✅

In **`gui/agent_runner.py`**:

- File dialog filter for `floor_plan` input:
  ```
  Floor plans (*.json *.dxf *.png *.jpg *.jpeg *.pdf);;All files (*.*)
  ```
- `_collect_inputs()`:
  - `.json` → file contents read as text and passed to the engine.
  - `.dxf` → file **path** passed directly (not read as text).
  - Images/PDF → file path passed directly for Gemini Vision.

---

## Step 8 — Sample data ✅

Five example floor plans in `data/floor_plans/`:

| File | Description |
|------|-------------|
| `example_office.json` | Office ground floor with rooms, corridors, doors, exits |
| `example_hospital.json` | Hospital layout |
| `example_school.json` | School layout |
| `example_borderline.json` | Edge-case plan for testing |
| `agent_output.json` | Sample agent output |

These are hand-authored JSON files in the `FloorPlan` schema. No sample DXF file exists yet — testing DXF parsing requires a real AutoCAD file.

---

## Layer name conventions

AutoCAD files vary in layer naming. The parser recognizes these patterns and falls back to entity-type heuristics when layers don't match:

| Entity | Recognized layer names |
|--------|----------------------|
| Walls | `A-WALL`, `WALL`, `WALLS`, `S-WALL`, `AR-WALL` |
| Doors | `A-DOOR`, `DOOR`, `DOORS`, `AR-DOOR` |
| Rooms | `A-ROOM`, `ROOM`, `ROOMS`, `A-AREA`, `SPACE` |
| Corridors | `A-CORRIDOR`, `CORRIDOR`, `CORRIDORS`, `HALL`, `HALLWAY` |
| Text | `A-TEXT`, `TEXT`, `ANNO`, `A-ANNO`, `LABEL` |
| Windows | `A-GLAZ`, `WINDOW`, `WIN` |

Unrecognized layers: closed polylines treated as rooms/corridors (by aspect ratio), arcs as doors, lines as walls, text as labels.

---

## What's left to do

| Item | Status |
|------|--------|
| DXF parsing (extract + build) | ✅ Done |
| Image parsing (Gemini Vision) | ✅ Done |
| PDF in file picker | ✅ Accepted (handled via Gemini Vision) |
| JSON floor plan loading | ✅ Done |
| Tool registration | ✅ Done |
| Agent definition | ✅ Done |
| UI file picker | ✅ Done |
| DWG → DXF conversion | ❌ Deferred |
| Sample DXF test file | ❌ Not created |
| Unit test for DXF parser | ❌ Not created |
