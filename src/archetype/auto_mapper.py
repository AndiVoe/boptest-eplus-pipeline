import sys
import os
import json
import re
from pathlib import Path

def auto_map_idf(idf_path):
    """
    Scans an IDF file for ExternalInterface objects and generates a BopTest mapping template.
    """
    if not os.path.exists(idf_path):
        print(f"Error: IDF file not found at {idf_path}")
        return

    print(f"🔍 Scanning IDF: {idf_path}")
    with open(idf_path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()

    sensors = []
    actuators = []
    
    # Standardize content: remove comments and join lines until semicolon
    content = ""
    for line in lines:
        line = line.split('!')[0].strip() # Remove comments
        if not line: continue
        content += line + " "

    # Split into objects
    objects = content.split(';')
    
    for obj in objects:
        obj = obj.strip()
        if not obj: continue
        
        # Split fields by comma
        fields = [f.strip() for f in obj.split(',')]
        if not fields: continue
        
        obj_type = fields[0].lower()
        
        if obj_type == "externalinterface:variable":
            # [Name, Key Value, Variable Name]
            if len(fields) >= 2:
                name = fields[1]
                sensors.append({
                    "boptest_name": f"rea{name}",
                    "idf_name": name,
                    "description": f"Sensor for {name}"
                })
        
        elif obj_type == "externalinterface:actuator":
            # [Name, Actuated Component Unique Name, Actuated Component Type, Actuated Component Control Type]
            if len(fields) >= 2:
                name = fields[1]
                actuators.append({
                    "boptest_name": f"ove{name}",
                    "idf_name": name,
                    "description": f"Actuator for {name}",
                    "min": 288.15,
                    "max": 303.15,
                    "unit": "K" # Defaulting to Kelvin for thermal actuators
                })

    mapping = {
        "sensors": sensors,
        "actuators": actuators,
        "metadata": {
            "source_idf": os.path.basename(idf_path),
            "generated_by": "Antigravity Auto-Mapper"
        }
    }

    output_path = "data/archetypes/mapping_template.json"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(mapping, f, indent=4)
        
    print(f"✅ Auto-Mapping complete!")
    print(f"Found {len(sensors)} sensors and {len(actuators)} actuators.")
    print(f"Saved to: {output_path}")
    return output_path

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python auto_mapper.py <path_to_idf>")
    else:
        auto_map_idf(sys.argv[1])
