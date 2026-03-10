#!/usr/bin/env python3
"""
MS2.3: Low-Order RC Model Templating
Parses the Brick Schema topology graph and generates a 3R1C (3 Resistance, 1 Capacitance) 
model configuration for each HVAC Zone identified in the building.
This structure is modular and can be upgraded to 5R1C or others in the future.
"""
import json
from pathlib import Path
from rdflib import Graph, Namespace
from brickschema.namespaces import BRICK, A

BLDG = Namespace("urn:phd_building/")

def generate_rc_template(ttl_path: Path, output_json: Path):
    print(f"Loading Building Topology from: {ttl_path}")
    g = Graph()
    g.parse(ttl_path, format="turtle")

    # The blueprint for our RC Model Topology
    rc_topology = {
        "metadata": {
            "model_type": "3R1C",
            "description": "3-Resistance, 1-Capacitance thermal network per zone.",
            "components": {
                "R_env": "Thermal resistance of the building envelope (walls/windows)",
                "R_int": "Thermal resistance between internal air and internal mass",
                "R_vent": "Thermal resistance of ventilation/infiltration air exchange",
                "C_air": "Thermal capacitance of the zone air volume",
            }
        },
        "zones": {}
    }

    # Query the graph to find all HVAC Zones
    # ?zone a brick:HVAC_Zone
    q_zones = """
        SELECT ?zone
        WHERE {
            ?zone a brick:HVAC_Zone .
        }
    """
    
    zones = list(g.query(q_zones))
    print(f"Discovered {len(zones)} HVAC Zones in the graph.")

    for row in zones:
        zone_uri = row.zone
        # Extract the local name, e.g., "urn:phd_building/Zone_VAV-101" -> "Zone_VAV-101"
        zone_id = zone_uri.split("/")[-1]
        
        # Query for equipment feeding this zone (e.g., VAVs)
        # ?equip brick:feeds ?zone .
        q_equip = f"""
            SELECT ?equip
            WHERE {{
                ?equip brick:feeds <{zone_uri}> .
            }}
        """
        equip_results = list(g.query(q_equip))
        feeding_equip = [str(r.equip).split("/")[-1] for r in equip_results]

        # Template the RC parameters for this zone.
        # Initial values are uncalibrated placeholders (e.g., 1.0 or 1000.0)
        # Phase 3 (Calibration) will estimate these parameters using training data.
        rc_topology["zones"][zone_id] = {
            "fed_by": feeding_equip,
            "states": {
                "T_z": {"description": "Zone Air Temperature", "initial_value": 20.0},
            },
            "parameters": {
                "R_env": {"value": 0.05, "bounds": [0.01, 0.2], "unit": "K/W"},
                "R_int": {"value": 0.01, "bounds": [0.001, 0.1], "unit": "K/W"},
                "R_vent": {"value": 0.02, "bounds": [0.005, 0.1], "unit": "K/W"},
                "C_air": {"value": 500000.0, "bounds": [1e5, 5e6], "unit": "J/K"},
            },
            "inputs": {
                "T_out": "Outside Air Temperature (Weather)",
                "Q_hvac": f"Heating/Cooling thermal power from {feeding_equip}",
                "Q_int": "Internal thermal gains (occupants, equipment)",
                "Q_sol": "Solar irradiance gains"
            }
        }

    # Save the RC topology to JSON
    output_json.parent.mkdir(parents=True, exist_ok=True)
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(rc_topology, f, indent=4)
    
    print(f"\nGenerated RC Template mapped to {len(zones)} zones.")
    print(f"Saved to: {output_json}")

if __name__ == "__main__":
    project_root = Path(__file__).resolve().parents[2]
    ttl_file = project_root / "data" / "bas" / "building_topology.ttl"
    rc_out_file = project_root / "data" / "models" / "rc_3r1c_template.json"
    
    generate_rc_template(ttl_file, rc_out_file)
