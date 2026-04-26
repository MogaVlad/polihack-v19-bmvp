"""Quick smoke test for the DXF parser pipeline."""
from tools.dxf_parser import extract_entities
from tools.dxf_to_floorplan import build_floor_plan

entities = extract_entities("data/floor_plans/test_simple.dxf")
fp, issues = build_floor_plan(entities)

print("=== ROOMS ===")
for r in fp.rooms:
    print(f"  {r.id}: {r.name} ({r.type}), area={r.area}m2, occ={r.occupancy}")

print(f"\n=== CORRIDORS ({len(fp.corridors)}) ===")
for c in fp.corridors:
    print(f"  {c.id}: {c.name}, {c.width}m x {c.length}m, connects={c.connects}")

print(f"\n=== DOORS ({len(fp.doors)}) ===")
for d in fp.doors:
    print(f"  {d.id}: connects={d.connects}, width={d.width}, exit={d.is_exit}")

print(f"\n=== EXITS ({len(fp.exits)}) ===")
for e in fp.exits:
    print(f"  {e.id}: room={e.room_id}, width={e.width}")

print(f"\n=== WALLS ({len(fp.walls)}) ===")
print(f"  Total: {len(fp.walls)} wall segments")

print(f"\n=== ISSUES ({len(issues)}) ===")
for i in issues:
    print(f"  [{i['type']}] {i['message']}")

print("\n=== SUMMARY ===")
print(f"  Rooms: {len(fp.rooms)}, Corridors: {len(fp.corridors)}, Doors: {len(fp.doors)}, Exits: {len(fp.exits)}, Walls: {len(fp.walls)}")
print("  PASS: Parser pipeline runs end-to-end!")
