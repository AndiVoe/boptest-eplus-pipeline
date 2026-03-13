#!/usr/bin/env python3
"""
TABULA Archetype Bridge
=======================
Demonstrates how to ingest a regional building archetype from the 
TABULA/EPISCOPE database and convert it into the project's 
standardized archetype_params.json format.
"""

import json
import argparse
from pathlib import Path

def convert_tabula_to_archetype(tabula_json_path, output_path=None):
    """
    Maps TABULA fields to our internal archetype structure.
    """
    with open(tabula_json_path, 'r') as f:
        data = json.load(f)
    
    print(f"🌉 Importing TABULA Archetype: {data['code']} ({data['country']})")
    
    # 1. Geometry Projection
    # We assume a standard square footprint for the naive model if only area is given
    area = data["geometry"]["floor_area_m2"]
    
    # 2. Physics Mapping (U-values to typical constructions)
    # In a real tool, this would pick specific material layers to match U-values.
    # For now, we store them as target U-values.
    
    archetype = {
        "building_name": f"TABULA_{data['code']}",
        "source": "TABULA_EPISCOPE",
        "description": f"{data['type']} ({data['year_range']})",
        "total_area_m2": area,
        "zones": [
            {
                "name": "LiveArea",
                "floor_area_m2": area,
                "ceiling_height_m": 2.7,
                "volume_m3": area * 2.7
            }
        ],
        "envelope": {
            "u_wall": data["envelope_u_values"]["wall"],
            "u_roof": data["envelope_u_values"]["roof"],
            "u_floor": data["envelope_u_values"]["floor"],
            "u_window": data["envelope_u_values"]["window"]
        },
        "hvac_type": "IdealLoadsAirSystem" if data["hvac"]["cooling_system"] == "None" else "VAV"
    }
    
    if output_path:
        with open(output_path, 'w') as f:
            json.dump(archetype, f, indent=4)
        print(f"✅ Successfully converted to {output_path}")
        
    return archetype

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", default="data/archetypes/tabula_sample_IT_SFH_07.json")
    parser.add_argument("--out", default="data/results/tabula_archetype_params.json")
    args = parser.parse_args()
    
    convert_tabula_to_archetype(args.json, args.out)
