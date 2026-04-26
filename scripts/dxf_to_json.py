import argparse
import json
import os
import sys

# Ensure the root directory is in the path to allow imports from tools/
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tools.dxf_parser import extract_entities, build_floor_plan

def main():
    parser = argparse.ArgumentParser(description="Convert DXF files directly to FloorPlan JSON")
    parser.add_argument("input_file", help="Path to the input .dxf file")
    parser.add_argument("-o", "--output", help="Optional output path for the .json file", default=None)
    
    args = parser.parse_args()
    input_path = args.input_file
    
    if not os.path.isfile(input_path):
        print(f"Error: File not found -> {input_path}")
        sys.exit(1)
        
    ext = os.path.splitext(input_path)[1].lower()
    
    if ext != ".dxf":
        print(f"Error: Unsupported file extension '{ext}'. Only .dxf is supported.")
        sys.exit(1)

    print("Extracting entities from DXF...")
    try:
        entities = extract_entities(input_path)
        print(f"Extracted {len(entities.get('polylines', []))} polylines, "
              f"{len(entities.get('lines', []))} lines, "
              f"{len(entities.get('texts', []))} texts.")
    except Exception as e:
        print(f"Error parsing DXF entities: {e}")
        sys.exit(1)

    print("Building FloorPlan...")
    try:
        floor_plan, issues = build_floor_plan(entities)
        if issues:
            print(f"Note: Found {len(issues)} parsing ambiguities/issues:")
            for issue in issues:
                print(f"  - {issue}")
    except Exception as e:
        print(f"Error building FloorPlan: {e}")
        sys.exit(1)

    output_data = {
        "parsed_plan": floor_plan.to_dict(),
        "flagged_issues": issues,
    }

    output_path = args.output
    if not output_path:
        base_name = os.path.splitext(input_path)[0]
        output_path = f"{base_name}.json"

    print(f"Writing output to {output_path}...")
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2)
        print("Done!")
    except Exception as e:
        print(f"Error writing to {output_path}: {e}")

if __name__ == "__main__":
    main()
