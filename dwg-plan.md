# Plan B — Direct DWG/DXF Parsing to FloorPlan JSON

## Overview

Parse AutoCAD floor plans directly into the existing `FloorPlan` schema using `ezdxf`, extracting real coordinates, dimensions, and labels. The P118 tools then work with precise measurements instead of LLM-guessed values.

**Scope**: DXF files natively. DWG files via a one-time conversion step (ODA File Converter).

---

## Step 1 — Install dependencies

```bash
pip install ezdxf
```

Add `ezdxf` to `requirements.txt`.

For DWG support, download the free [ODA File Converter](https://www.opendesign.com/guestfiles/oda_file_converter) and install it. It converts DWG → DXF via command line. This is an optional external tool — the core parser works on DXF directly.

---

## Step 2 — DWG-to-DXF conversion utility

Create `tools/dwg_converter.py`:

1. Accept a `.dwg` file path as input.
2. Shell out to ODA File Converter to produce a `.dxf` in a temp directory.
   - Command: `ODAFileConverter <input_dir> <output_dir> ACAD2018 DXF 0 1 <filename>`
   - The ODA path should be configurable in `config.py` (e.g. `ODA_CONVERTER_PATH`).
3. Return the path to the generated `.dxf` file.
4. If ODA is not installed, raise a clear error: "DWG files require ODA File Converter. Please provide a DXF file or install ODA."

This step is a thin wrapper — keep it under 40 lines.

---

## Step 3 — DXF entity extraction

Create `tools/dxf_parser.py` with a function `extract_entities(dxf_path) -> dict`:

1. Open the DXF with `ezdxf.readfile(dxf_path)`.
2. Get the modelspace: `msp = doc.modelspace()`.
3. Iterate entities and collect them by type:
   - **LWPOLYLINE / POLYLINE** → closed polylines are room/corridor boundaries. Extract vertices as `[[x, y], ...]`. Record whether the polyline is closed.
   - **LINE** → wall segments. Extract `start [x, y]` and `end [x, y]`.
   - **CIRCLE / ARC** → door swings. Extract center, radius, start/end angles.
   - **TEXT / MTEXT** → room labels, dimensions, annotations. Extract insertion point and text content.
   - **INSERT** (block references) → door/window/exit symbols. Extract block name and insertion point.
4. Group entities by layer name (AutoCAD convention: layers like `A-WALL`, `A-DOOR`, `A-ROOM`, `A-TEXT` etc.).
5. Return a dict:
   ```python
   {
       "polylines": [...],    # each: {vertices, layer, is_closed}
       "lines": [...],        # each: {start, end, layer}
       "arcs": [...],         # each: {center, radius, start_angle, end_angle, layer}
       "texts": [...],        # each: {content, position, layer}
       "blocks": [...],       # each: {name, position, layer}
       "layers": [...]        # list of layer names found
   }
   ```

---

## Step 4 — Entity-to-FloorPlan mapping

Add a function `build_floor_plan(entities: dict) -> FloorPlan` in the same file (or a new `tools/dxf_to_floorplan.py`):

### 4a — Identify rooms
- Take all closed polylines from wall/room layers.
- Each closed polyline becomes a `Room`:
  - `polygon`: the polyline vertices.
  - `area`: compute via the shoelace formula (`ezdxf` has `ezdxf.math.area()`).
  - `name` / `type`: match nearby TEXT/MTEXT entities (find text whose insertion point falls inside or near the polygon). Use the text content as the room name. Classify type by keyword matching ("office", "corridor", "stair", "WC", "conference", etc.).
  - `occupancy`: estimate from area using P118 density tables in `config.py`.
  - `id`: generate as `R1`, `R2`, ... in discovery order.

### 4b — Identify corridors
- Long narrow closed polylines (aspect ratio > 3:1) or polylines on a corridor-specific layer.
- Each becomes a `Corridor`:
  - `width`: the shorter dimension of the bounding box.
  - `length`: the longer dimension.
  - `connects`: find which rooms share a wall segment or are adjacent (within a tolerance).

### 4c — Identify doors
- ARC entities (door swings) or INSERT references to door blocks.
- Each becomes a `Door`:
  - `position`: the arc center or block insertion point.
  - `width`: arc radius × 2 (standard door swing = door width), or from block attributes.
  - `connects`: find the two rooms/corridors on either side of the door position (nearest polygons).
  - `is_exit`: True if one side leads outside (no enclosing polygon) or if the block name contains "exit".

### 4d — Identify exits
- INSERTs referencing exit blocks, or doors flagged as `is_exit`.
- Each becomes an `Exit`:
  - `position`, `width` from the door.
  - `room_id`: the room/corridor it connects to.
  - `leads_outside`: True.

### 4e — Identify walls
- LINE entities on wall layers, or the segments of room/corridor polylines.
- Each becomes a `Wall` with `start`, `end`, and optional `room_id`.

### 4f — Flag ambiguities
- Unclosed polylines on room layers → "Possible incomplete room boundary"
- Rooms with no detected door → "Room X has no door connection"
- Overlapping room polygons → "Rooms X and Y overlap"
- Text labels that couldn't be matched to a room → "Unmatched label: ..."
- Return these as a list of flagged issues alongside the FloorPlan.

---

## Step 5 — Register the tool

In `tools/registry.py`, register a new tool:

```python
def parse_dxf(input_data: dict) -> dict:
    """Parse a DXF/DWG floor plan into structured FloorPlan JSON."""
    file_path = input_data.get("floor_plan", "")
    if file_path.endswith(".dwg"):
        file_path = convert_dwg_to_dxf(file_path)
    entities = extract_entities(file_path)
    floor_plan, issues = build_floor_plan(entities)
    return {
        "parsed_plan": floor_plan.to_dict(),
        "flagged_issues": issues,
    }

registry.register_tool("dxf_parser", parse_dxf, description="Parse DXF/DWG floor plans into structured data")
```

---

## Step 6 — Update the Floor Plan Parser agent

Edit `data/agents/floor_plan_parser.json`:

1. Add `"dxf_parser"` to the `tools` list (alongside `gemini_vision`).
2. Update the input type to accept `"json"`, `"image"`, or `"dxf"`.
3. Update constraints to note: "For DXF/DWG files, use the dxf_parser tool for precise extraction. For images, fall back to gemini_vision."

The engine's `runner.py` already runs all tools in the agent's tool list and injects results. The LLM will receive exact geometry from the DXF parser and can use it to produce the structured output.

---

## Step 7 — Input handling in the Agent Runner UI

In `gui/agent_runner.py`, update the file picker for the Floor Plan Parser:

1. Add `.dxf` and `.dwg` to the file dialog filter:
   ```python
   filetypes=[("Floor plans", "*.json *.dxf *.dwg"), ("All files", "*.*")]
   ```
2. In `_collect_inputs()`, if the file is `.dxf` or `.dwg`, pass the file path directly (don't try to read it as JSON text).

---

## Step 8 — Test with a sample DXF

1. Find or create a simple test DXF with a few rooms, a corridor, doors, and an exit.
2. Run the Floor Plan Parser agent with the DXF file.
3. Verify:
   - Room polygons match the DXF geometry.
   - Areas are correct (compare with AutoCAD's measured area).
   - Doors are detected and connected to the right rooms.
   - The output feeds correctly into the Egress Validator (run the full pipeline).
4. Add a unit test in `tests/test_tools.py` that parses a known DXF and checks the output schema.

---

## Layer name conventions

AutoCAD files vary wildly in layer naming. Support these common patterns:

| Entity | Common layer names |
|--------|--------------------|
| Walls | `A-WALL`, `WALL`, `WALLS`, `S-WALL`, `AR-WALL` |
| Doors | `A-DOOR`, `DOOR`, `DOORS`, `AR-DOOR` |
| Rooms | `A-ROOM`, `ROOM`, `ROOMS`, `A-AREA`, `SPACE` |
| Text | `A-TEXT`, `TEXT`, `ANNO`, `A-ANNO`, `LABEL` |
| Furniture | `A-FURN`, `FURN`, `FURNITURE` (ignore for floor plan) |
| Windows | `A-GLAZ`, `WINDOW`, `WIN` (useful for exit detection) |

If layer names don't match known patterns, fall back to entity-type heuristics (closed polyline = room, arc = door, etc.).

---

## Estimated effort

| Step | Time |
|------|------|
| 1. Dependencies | 5 min |
| 2. DWG converter | 20 min |
| 3. Entity extraction | 45 min |
| 4. Entity-to-FloorPlan mapping | 60 min |
| 5. Tool registration | 10 min |
| 6. Agent definition update | 10 min |
| 7. UI file picker update | 10 min |
| 8. Testing | 30 min |
| **Total** | **~3 hours** |

Steps 3 and 4 are the core work. Everything else is wiring.
