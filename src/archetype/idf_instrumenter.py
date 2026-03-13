import sys
import os
import re

def instrument_idf(idf_path):
    """
    Automates the 'Wires Must Be Cut' step by injecting ExternalInterface
    and thermostat overrides into a raw IDF.
    """
    if not os.path.exists(idf_path):
        print(f"Error: File {idf_path} not found.")
        return

    print(f"🛠️  Instrumenting IDF: {idf_path}")
    with open(idf_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    # 1. Inject the Main ExternalInterface Object
    if "ExternalInterface," not in content:
        header = "ExternalInterface,\n    FunctionalMockupUnitExport;  !- Name\n\n"
        content = header + content

    # 2. Find Thermostat Setpoints (Dual Setpoint)
    dual_sp_pattern = re.compile(r"ThermostatSetpoint:DualSetpoint,\s*([^,]+),\s*([^,]+),\s*([^;]+);", re.IGNORECASE)
    matches_sp = dual_sp_pattern.findall(content)
    
    instr_count = 0
    for name, heat_sch, cool_sch in matches_sp:
        name = name.strip()
        heat_sch = heat_sch.strip()
        cool_sch = cool_sch.strip()
        print(f"  📍 Found Thermostat: {name}")
        content += f"\nExternalInterface:Schedule,\n    {heat_sch}_Ext,\n    AnyNumber,\n    {heat_sch};  !- Initial Value\n"
        content += f"\nExternalInterface:Schedule,\n    {cool_sch}_Ext,\n    AnyNumber,\n    {cool_sch};  !- Initial Value\n"
        instr_count += 2

    # 3. Find Zones and Inject Sensors
    zone_pattern = re.compile(r"Zone,\s*([^,;]+)", re.IGNORECASE)
    zones = zone_pattern.findall(content)
    
    for zone in zones:
        zone = zone.strip()
        print(f"  🌡️  Adding Sensor Hook for Zone: {zone}")
        # Inject the Output:Variable if not present
        content += f"\nOutput:Variable, {zone}, Zone Air Temperature, Hourly;\n"
        # Inject the ExternalInterface:Variable
        content += f"\nExternalInterface:Variable, {zone}_Temp, {zone}, Zone Air Temperature;\n"
        instr_count += 1

    output_path = idf_path.replace(".idf", "_instrumented.idf")
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)
        
    print(f"✅ Instrumented IDF saved to: {output_path}")
    print(f"   Injected {instr_count} thermostat hooks.")
    return output_path

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python idf_instrumenter.py <path_to_idf>")
    else:
        instrument_idf(sys.argv[1])
