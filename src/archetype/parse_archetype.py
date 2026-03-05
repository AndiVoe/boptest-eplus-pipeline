"""
Archetype Parser (Custom Text Version) — Micro-Step 3 Deliverable
================================================================
Parses an EnergyPlus IDF file into a structured JSON of key parameters
for downstream model generation.

This custom parser bypasses the `eppy` and EnergyPlus IDD dependency
by directly reading the text layout of the `.idf` file.

Usage:
  python src/archetype/parse_archetype.py data/archetypes/Model_Thesis_MPC_Optimized.idf
"""

import argparse
import json
import sys
import re
from pathlib import Path
from collections import defaultdict


def parse_idf_text(filepath: str) -> dict:
    """Read an IDF file and group objects by class name."""
    text = Path(filepath).read_text(encoding="utf-8", errors="replace")
    
    # Dictionary of ClassName -> List of lists (fields)
    objects = defaultdict(list)
    current_class = None
    
    # We will split the file by semicolons to get full objects,
    # but that's risky if semicolons exist in comments.
    # Better to process line by line.
    
    current_object = []
    
    lines = text.splitlines()
    for line in lines:
        line = line.strip()
        
        # Check for class headers
        if line.startswith("!-   ===========  ALL OBJECTS IN CLASS:"):
            match = re.search(r"CLASS:\s*(.+)\s*===========", line)
            if match:
                current_class = match.group(1).strip().upper()
            continue
            
        # Ignore full-line comments or empty lines
        if not line or line.startswith("!"):
            continue
            
        # If we reach here, it's data.
        # Strip inline comments
        if "!" in line:
            line = line.split("!", 1)[0].strip()
            
        if not line:
            continue
            
        # It's either comma-terminated row or semicolon-terminated.
        if line.endswith(","):
            current_object.append(line[:-1].strip())
        elif line.endswith(";"):
            current_object.append(line[:-1].strip())
            
            # An object is complete
            if current_object:
                # First field is usually the type if not prefixed by a header.
                # But in sorted order IDFs, we know `current_class`.
                # Wait, inside the object, the VERY FIRST word is the class name itself!
                obj_class = current_object[0].upper()
                obj_fields = current_object[1:]
                
                objects[obj_class].append(obj_fields)
                
            current_object = []
            
    return objects


def safe_float(val, default=None):
    try:
        if val is None or val == "":
            return default
        return float(val)
    except ValueError:
        return default


def extract_zones(objects: dict) -> dict:
    params = {}
    zones = []
    
    for fields in objects.get("ZONE", []):
        if not fields:
            continue
            
        name = fields[0]
        # In EP 23.2:
        # Field 1: Name
        # Field 2: Direction of Relative North {deg}
        # Field 3: X Origin {m}
        # Field 4: Y Origin {m}
        # Field 5: Z Origin {m}
        # Field 6: Type
        # Field 7: Multiplier
        # Field 8: Ceiling Height {m}
        # Field 9: Volume {m3}
        
        ceiling_height = safe_float(fields[7] if len(fields) > 7 else None)
        volume = safe_float(fields[8] if len(fields) > 8 else None)
        
        zones.append({
            "name": name,
            "ceiling_height_m": ceiling_height,
            "volume_m3": volume
        })
        
    params["zone_count"] = len(zones)
    params["zones"] = zones
    return params


def extract_materials(objects: dict) -> dict:
    params = {}
    materials = {}
    
    for fields in objects.get("MATERIAL", []):
        if not fields:
            continue
            
        name = fields[0]
        # Field 1: Name
        # Field 2: Roughness
        # Field 3: Thickness {m}
        # Field 4: Conductivity {W/m-K}
        # Field 5: Density {kg/m3}
        # Field 6: Specific Heat {J/kg-K}
        
        materials[name] = {
            "roughness": fields[1] if len(fields) > 1 else "Unknown",
            "thickness_m": safe_float(fields[2] if len(fields) > 2 else None),
            "conductivity_w_mk": safe_float(fields[3] if len(fields) > 3 else None),
            "density_kg_m3": safe_float(fields[4] if len(fields) > 4 else None),
            "specific_heat_j_kgk": safe_float(fields[5] if len(fields) > 5 else None)
        }
        
    params["material_count"] = len(materials)
    params["materials"] = materials
    return params


def extract_constructions(objects: dict) -> dict:
    params = {}
    constructions = {}
    
    for fields in objects.get("CONSTRUCTION", []):
        if not fields:
            continue
            
        name = fields[0]
        layers = fields[1:]
        constructions[name] = layers
        
    params["construction_count"] = len(constructions)
    params["constructions"] = constructions
    return params


def extract_calibration_multipliers(objects: dict) -> dict:
    """Extract ZoneCapacitanceMultiplier:ResearchSpecial, crucial for calibration."""
    params = {}
    multipliers = {}
    
    for fields in objects.get("ZONECAPACITANCEMULTIPLIER:RESEARCHSPECIAL", []):
        if not fields:
            continue
            
        name = fields[0]
        # Field 1: Name
        # Field 2: Zone or ZoneList Name
        # Field 3: Temperature Capacity Multiplier
        
        zone_target = fields[1] if len(fields) > 1 else "Unknown"
        temp_mult = safe_float(fields[2] if len(fields) > 2 else None, 1.0)
        
        multipliers[zone_target] = temp_mult
        
    params["calibration_inertia_multipliers"] = multipliers
    return params


def main():
    parser = argparse.ArgumentParser(
        description="Parse an EnergyPlus IDF (Text mode) into archetype_params.json"
    )
    parser.add_argument("idf_path", help="Path to the .idf file")
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="Output JSON path (default: data/results/archetype_params.json)",
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[2]
    output_path = Path(args.output) if args.output else (
        project_root / "data" / "results" / "archetype_params.json"
    )

    print(f"[parse_archetype] Reading IDF as text: {args.idf_path}")
    objects = parse_idf_text(args.idf_path)
    print(f"[parse_archetype] Found {sum(len(v) for v in objects.values())} total objects across {len(objects)} classes.")
    
    # Extract
    params = {"source_idf": Path(args.idf_path).name}
    params.update(extract_zones(objects))
    params.update(extract_materials(objects))
    params.update(extract_constructions(objects))
    params.update(extract_calibration_multipliers(objects))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(params, f, indent=2)

    print(f"[parse_archetype] Successfully built parameter library")
    print(f"[parse_archetype] Zones found:         {params.get('zone_count', 0)}")
    print(f"[parse_archetype] Materials found:     {params.get('material_count', 0)}")
    print(f"[parse_archetype] Constructions found: {params.get('construction_count', 0)}")
    print(f"✅ Saved to: {output_path}")


if __name__ == "__main__":
    main()
