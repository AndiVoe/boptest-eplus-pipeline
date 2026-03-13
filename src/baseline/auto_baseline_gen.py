import json
import os
import sys

def generate_auto_baseline(mapping_path):
    """
    Generates a Python RBC script using the point names found in the mapping file.
    """
    if not os.path.exists(mapping_path):
        print(f"Error: Mapping file {mapping_path} not found.")
        return

    with open(mapping_path, 'r') as f:
        mapping = json.load(f)

    sensors = mapping.get("sensors", [])
    actuators = mapping.get("actuators", [])

    # Find key points (simplified heuristic)
    t_zon_points = [s['boptest_name'] for s in sensors if 'TZon' in s['boptest_name']]
    h_set_points = [a['boptest_name'] for a in actuators if 'TSetHea' in a['boptest_name']]
    c_set_points = [a['boptest_name'] for a in actuators if 'TSetCoo' in a['boptest_name']]

    if not t_zon_points or not h_set_points:
        print("⚠️  Warning: Could not identify standard ZoneTemp/SetPoint points. Baseline might be incomplete.")

    script_content = f"""
import requests
import json
import time

def run_baseline(testid, url="http://localhost:8000"):
    print(f"🚀 Running Auto-Generated Baseline for TestID: {{testid}}")
    
    # Zone Temperature Point: {t_zon_points[0] if t_zon_points else 'Unknown'}
    # Heating Setpoint Point: {h_set_points[0] if h_set_points else 'Unknown'}
    # Cooling Setpoint Point: {c_set_points[0] if c_set_points else 'Unknown'}

    def rbc_logic(t_zone):
        if t_zone < 293.15: # 20C
            return 294.15 # 21C Heating SP
        elif t_zone > 297.15: # 24C
            return 295.15 # 22C Cooling SP
        return 293.15 # Default/Deadband

    # Simulation loop would go here...
    print("Baseline script boilerplate generated. Ready for loop integration.")

if __name__ == "__main__":
    # Example usage: python baseline_at_runtime.py <testid>
    if len(sys.argv) > 1:
        run_baseline(sys.argv[1])
"""

    output_path = "src/baseline/baseline_at_runtime.py"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(script_content)
        
    print(f"✅ Auto-Baseline script generated: {output_path}")

if __name__ == "__main__":
    mapping_file = "data/archetypes/mapping_template.json"
    generate_auto_baseline(mapping_file)
