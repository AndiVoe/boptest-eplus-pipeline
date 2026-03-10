#!/usr/bin/env python3
"""
Automated Semantic Mapping for Phase 2.
Reads the mock BAS point list (CSV) and generates a Brick Schema graph (Turtle format).
"""
import pandas as pd
from pathlib import Path
from rdflib import Namespace, URIRef, Literal
import brickschema
from brickschema.namespaces import BRICK, A

# Define a custom namespace for our specific building
BLDG = Namespace("urn:phd_building/")

def generate_brick_graph(csv_path: Path, output_ttl: Path):
    print(f"Loading BAS point list from: {csv_path}")
    df = pd.read_csv(csv_path)

    # Initialize Brick Graph (automatically includes Brick imports)
    g = brickschema.Graph()
    g.bind("bldg", BLDG)

    # Dictionary to keep track of created equipment to avoid duplicates
    equipment_created = set()

    # Define the Building and a synthetic HVAC Zone for the mock data
    site = BLDG["Site_1"]
    bldg = BLDG["Building_1"]
    g.add((site, A, BRICK.Site))
    g.add((bldg, A, BRICK.Building))
    g.add((site, BRICK.hasPart, bldg))

    print("Mapping points to Brick ontology...")
    for idx, row in df.iterrows():
        point_name = str(row["Point_Name"])
        equip_id = str(row["Equipment_ID"])
        desc = str(row["Description"])
        bacnet_type = str(row["BACnet_Type"])

        # 1. Map Equipment
        equip_uri = BLDG[equip_id]
        if equip_id not in equipment_created:
            if "AHU" in equip_id:
                g.add((equip_uri, A, BRICK.AHU))
                g.add((bldg, BRICK.hasEquipment, equip_uri))
            elif "VAV" in equip_id:
                g.add((equip_uri, A, BRICK.VAV))
                # Create a zone for each VAV
                zone_uri = BLDG[f"Zone_{equip_id}"]
                g.add((zone_uri, A, BRICK.HVAC_Zone))
                g.add((equip_uri, BRICK.feeds, zone_uri))
                g.add((bldg, BRICK.hasPart, zone_uri))
            elif "Chiller" in equip_id:
                g.add((equip_uri, A, BRICK.Chiller))
            elif "Boiler" in equip_id:
                g.add((equip_uri, A, BRICK.Boiler))
            elif "CHW_Plant" in equip_id:
                g.add((equip_uri, A, BRICK.Chilled_Water_System))
            elif "HW_Plant" in equip_id:
                g.add((equip_uri, A, BRICK.Hot_Water_System))
            elif equip_id == "Building":
                equip_uri = bldg # Attach point directly to building
            else:
                g.add((equip_uri, A, BRICK.Equipment))
            
            equipment_created.add(equip_id)

        # 2. Map Points based on text heuristics
        point_uri = BLDG[point_name.replace(".", "_")]
        brick_class = BRICK.Point # Default fallback

        # Temperature
        if "Zone Temperature Setpoint" in desc:
            brick_class = BRICK.Zone_Air_Temperature_Setpoint
        elif "Zone Temperature" in desc:
            brick_class = BRICK.Zone_Air_Temperature_Sensor
        elif "Discharge Air Temperature" in desc:
            brick_class = BRICK.Discharge_Air_Temperature_Sensor
        elif "Return Air Temperature" in desc:
            brick_class = BRICK.Return_Air_Temperature_Sensor
        elif "Outside Air Temperature" in desc:
            brick_class = BRICK.Outside_Air_Temperature_Sensor
        elif "Chilled Water Supply Temp" in desc:
            brick_class = BRICK.Chilled_Water_Supply_Temperature_Sensor
        elif "Chilled Water Return Temp" in desc:
            brick_class = BRICK.Chilled_Water_Return_Temperature_Sensor
        elif "Hot Water Supply Temp" in desc:
            brick_class = BRICK.Hot_Water_Supply_Temperature_Sensor
        elif "Hot Water Return Temp" in desc:
            brick_class = BRICK.Hot_Water_Return_Temperature_Sensor
            
        # Commands & Status
        elif "Damper Position" in desc and "Outside" not in desc:
            brick_class = BRICK.Damper_Position_Command
        elif "Outside Air Damper Position" in desc:
            brick_class = BRICK.Outside_Air_Damper_Position_Command
        elif "Valve Position" in desc and "Heating" in desc:
            brick_class = BRICK.Heating_Valve_Command
        elif "Valve Position" in desc and "Cooling" in desc:
            brick_class = BRICK.Cooling_Valve_Command
        elif "Reheat Valve" in desc:
            brick_class = BRICK.Heating_Valve_Command
        elif "Fan Speed" in desc:
            brick_class = BRICK.Fan_Speed_Command
        elif "Fan Status" in desc:
            brick_class = BRICK.Fan_Status
        elif "Chiller Status" in desc:
            brick_class = BRICK.On_Off_Status
        elif "Boiler Status" in desc:
            brick_class = BRICK.On_Off_Status
        elif "Pump Status" in desc:
            brick_class = BRICK.Pump_On_Off_Status
            
        # Airflow
        elif "Discharge Airflow" in desc:
            brick_class = BRICK.Discharge_Air_Flow_Sensor
        elif "Airflow Setpoint" in desc:
            brick_class = BRICK.Discharge_Air_Flow_Setpoint
            
        # Power
        elif "Electric Power" in desc:
            brick_class = BRICK.Electrical_Power_Sensor

        # 3. Add Point Triples
        g.add((point_uri, A, brick_class))
        if equip_uri != bldg:
            g.add((equip_uri, BRICK.hasPoint, point_uri))
        else:
            g.add((bldg, BRICK.hasPoint, point_uri))
            
        # Add metadata as RDFS labels or Brick properties where applicable
        g.add((point_uri, BRICK.hasUnit, Literal(row["Unit"])))
        g.add((point_uri, brickschema.namespaces.RDFS.label, Literal(desc)))
        
    # Serialize to Turtle format
    output_ttl.parent.mkdir(parents=True, exist_ok=True)
    g.serialize(destination=str(output_ttl), format="turtle")
    
    print(f"Successfully mapped {len(df)} points.")
    print(f"Generated Brick Schema Graph with {len(g)} triples.")
    print(f"Saved to: {output_ttl}")

    # Basic graph validation
    valid, _, report = g.validate()
    print(f"Is valid against Brick ontology rules: {valid}")
    if not valid:
        print("Validation report:", report)


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parents[2]
    csv_file = project_root / "data" / "bas" / "mock_point_list.csv"
    ttl_file = project_root / "data" / "bas" / "building_topology.ttl"
    
    generate_brick_graph(csv_file, ttl_file)
