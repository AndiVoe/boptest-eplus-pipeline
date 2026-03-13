import time
import json
import pandas as pd
from src.boptest.client import BopTestClient

def check_idf_instrumentation(idf_path):
    """
    Scans the IDF for required ExternalInterface objects.
    """
    print(f"🔍 Auditing IDF Instrumentation: {idf_path}")
    
    with open(idf_path, 'r', errors='ignore') as f:
        content = f.read()
        
    interface = "ExternalInterface," in content or "ExternalInterface;" in content
    variables = "ExternalInterface:Variable," in content
    actuators = "ExternalInterface:Actuator," in content
    
    print(f"  - ExternalInterface: {'✅ Found' if interface else '❌ Missing'}")
    print(f"  - ExternalInterface:Variable: {'✅ Found' if variables else '❌ Missing'}")
    print(f"  - ExternalInterface:Actuator: {'✅ Found' if actuators else '❌ Missing'}")
    
    if not (interface and variables and actuators):
        print("\n⚠️ WARNING: IDF is not fully instrumented for external control.")
        print("BopTest requires all three ExternalInterface types to 'grab the steering wheel'.")
        return False
    
    print("\n✨ IDF Instrumentation Audit: PASSED.")
    return True

def run_preflight_check(test_case="bestest_air", mapping_path="data/archetypes/mapping_template.json", idf_path=None):
    """
    Runs a short diagnostic test to ensure actuators are responsive.
    """
    if idf_path and not check_idf_instrumentation(idf_path):
        return
        
    print(f"🚀 Starting Pre-Flight Sanity Check for {test_case}...")
    
    with open(mapping_path, 'r') as f:
        mapping = json.load(f)
        
    client = BopTestClient("http://localhost:8000")
    
    print(f"Selecting test case...")
    client.select_test_case(test_case, async_select=True)
    client.wait_for_status("Running", timeout=600)
    
    # Initialize for 24 hours
    print("Initializing for 24h diagnostic run...")
    res = client.initialize(start_time=0, warmup_period=0)
    client.set_step(3600)
    
    initial_temps = {k: v for k, v in res.items() if 'TZon' in k or 'TRooAir' in k}
    
    print(f"Applying step commands to {len(mapping['actuators'])} actuators...")
    
    # 1. Apply Max Heating / Minimum Cooling
    control = {}
    for act in mapping['actuators']:
        name = act['boptest_name']
        val = act['max']
        control[name] = val
        # Handle different BopTest activation styles
        if 'activate' not in name:
            control[name + "_activate"] = 1

    print("Advancing 1 step (1 hour)...")
    res_next = client.advance(control)
    
    next_temps = {k: v for k, v in res_next.items() if 'TZon' in k or 'TRooAir' in k}
    
    print("\n--- Diagnostic Results ---")
    responsive_zones = 0
    for k in initial_temps:
        diff = abs(next_temps.get(k, 0) - initial_temps[k])
        status = "✅ OK" if diff > 0.01 else "❌ STALLED"
        print(f"Zone {k}: {initial_temps[k]:.2f}C -> {next_temps.get(k, 0):.2f}C (Δ={diff:.3f}) [{status}]")
        if diff > 0.01:
            responsive_zones += 1

    if responsive_zones == 0:
        print("\n⚠️ WARNING: No zones responded to control signals. Check your IDF routing!")
    else:
        print(f"\n✨ Pre-Flight Complete: {responsive_zones}/{len(initial_temps)} zones are responsive.")

if __name__ == "__main__":
    # For demo, use bestest_air
    import sys
    case = sys.argv[1] if len(sys.argv) > 1 else "bestest_air"
    idf = sys.argv[2] if len(sys.argv) > 2 else None
    run_preflight_check(case, idf_path=idf)
