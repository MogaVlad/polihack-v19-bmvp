"""
Step 8 — Generate a sample test DXF file for parser testing.

Creates a simple floor plan with:
- 3 rooms (Office, Conference, WC)
- 1 corridor connecting them
- 4 doors (including 1 exit)
- Text labels for room names
"""

import ezdxf
import os


def create_test_dxf(output_path: str):
    """Create a simple test DXF floor plan."""
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()

    # Create layers
    doc.layers.add("A-WALL", color=7)
    doc.layers.add("A-ROOM", color=3)
    doc.layers.add("A-DOOR", color=1)
    doc.layers.add("A-TEXT", color=2)

    # ── Room 1: Office (5m x 6m) ──
    office_verts = [(0, 0), (5, 0), (5, 6), (0, 6)]
    msp.add_lwpolyline(office_verts, close=True, dxfattribs={"layer": "A-ROOM"})
    msp.add_text("Office 101", dxfattribs={
        "layer": "A-TEXT",
        "insert": (2.5, 3.0),
        "height": 0.3,
    })

    # ── Room 2: Conference Room (6m x 5m) ──
    conf_verts = [(7, 0), (13, 0), (13, 5), (7, 5)]
    msp.add_lwpolyline(conf_verts, close=True, dxfattribs={"layer": "A-ROOM"})
    msp.add_text("Conference Room", dxfattribs={
        "layer": "A-TEXT",
        "insert": (9.0, 2.5),
        "height": 0.3,
    })

    # ── Room 3: WC (3m x 2m) ──
    wc_verts = [(7, 7), (10, 7), (10, 9), (7, 9)]
    msp.add_lwpolyline(wc_verts, close=True, dxfattribs={"layer": "A-ROOM"})
    msp.add_text("WC", dxfattribs={
        "layer": "A-TEXT",
        "insert": (8.5, 8.0),
        "height": 0.3,
    })

    # ── Corridor (long narrow shape connecting rooms, 12m x 2m) ──
    corr_verts = [(0, 6), (13, 6), (13, 7), (0, 7)]
    msp.add_lwpolyline(corr_verts, close=True, dxfattribs={"layer": "A-ROOM"})
    msp.add_text("Main Corridor", dxfattribs={
        "layer": "A-TEXT",
        "insert": (6.0, 6.5),
        "height": 0.2,
    })

    # ── Doors (arcs representing door swings) ──
    # Door 1: Office to corridor (at y=6, x=2.5)
    msp.add_arc(
        center=(2.5, 6.0), radius=0.45,
        start_angle=0, end_angle=90,
        dxfattribs={"layer": "A-DOOR"},
    )

    # Door 2: Conference room door (at y=5, x=10)
    msp.add_arc(
        center=(10.0, 5.0), radius=0.45,
        start_angle=0, end_angle=90,
        dxfattribs={"layer": "A-DOOR"},
    )

    # Door 3: WC door (at y=7, x=8.5)
    msp.add_arc(
        center=(8.5, 7.0), radius=0.4,
        start_angle=0, end_angle=90,
        dxfattribs={"layer": "A-DOOR"},
    )

    # Door 4: Exit door (at x=0, y=6.5 — corridor leading outside)
    msp.add_arc(
        center=(0.0, 6.5), radius=0.6,
        start_angle=90, end_angle=180,
        dxfattribs={"layer": "A-DOOR"},
    )

    # ── Some wall lines ──
    # Exterior walls
    wall_segments = [
        ((0, 0), (5, 0)),
        ((0, 0), (0, 6)),
        ((0, 7), (0, 9)),
        ((13, 0), (13, 9)),
    ]
    for start, end in wall_segments:
        msp.add_line(start, end, dxfattribs={"layer": "A-WALL"})

    doc.saveas(output_path)
    print(f"Test DXF saved to: {output_path}")


if __name__ == "__main__":
    out = os.path.join(os.path.dirname(__file__), "..", "data", "floor_plans", "test_simple.dxf")
    create_test_dxf(os.path.abspath(out))
