#!/usr/bin/env python3
"""
BopTest to IDF Parameter Bridge
===============================
Automatically discovers building topology (zones) from a BopTest test case's
measurements/inputs and generates a 'naive' parameter JSON compatible with 
generate_model.py.

This bridges the gap for Category B (Modelica-based) test cases.
"""

import argparse
import json
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.boptest.client import BopTestClient

def discover_building(client, model_name):
    """
    Queries Boptest API to find zones and basic building info.
    """
    print(f"🔍 Discovering building topology for: {model_name}")
    
    # 1. Get Measurements (API Attempt)
    measurements = {}
    try:
        measurements = client.get_measurements()
    except Exception as e:
        print(f"  ⚠️  API Error: {e}")

    # 2. Extract Zone Names
    zone_ids = set()
    if measurements:
        for key in measurements.keys():
            m1 = re.search(r'reaZon([A-Za-z0-9]+)_', key)
            if m1:
                zone_ids.add(m1.group(1))
                continue
            m2 = re.search(r'^([A-Za-z0-9]+)_reaTRooAir', key)
            if m2:
                zone_ids.add(m2.group(1))
                continue

    # 2b. Filesystem Fallback (kpis.json)
    phd_root = Path(__file__).resolve().parents[2]
    boptest_root = phd_root.parent / "project1-boptest"
    models_dir = boptest_root / "testcases" / model_name / "models"
    kpis_path = models_dir / "kpis.json"
    
    if not zone_ids and kpis_path.exists():
        print(f"  📂 Falling back to filesystem: {kpis_path}")
        with open(kpis_path, 'r') as f:
            kpis = json.load(f)
            for k in kpis.keys():
                m = re.search(r'\[([A-Za-z0-9]+)\]', k)
                if m:
                    zone_ids.add(m.group(1).capitalize())

    # Fallback for single-zone
    if not zone_ids:
        zone_ids.add("Zone1")

    print(f"  📍 Found {len(zone_ids)} zones: {sorted(list(zone_ids))}")

    # 3. Find Building Area
    config_path = models_dir / "config.json"
    
    total_area = 100.0 # Default fallback
    if config_path.exists():
        with open(config_path, 'r') as f:
            config = json.load(f)
            total_area = config.get("area", 100.0)
            print(f"  🏢 Found config.json. Total Area: {total_area} m2")
    else:
        print(f"  ⚠️  config.json not found at {config_path}. Using default area {total_area} m2.")

    # 4. Synthesize Parameters
    area_per_zone = total_area / max(1, len(zone_ids))
    
    zones_list = []
    for i, zid in enumerate(sorted(list(zone_ids))):
        zones_list.append({
            "name": zid,
            "ceiling_height_m": 3.0,
            "volume_m3": area_per_zone * 3.0
        })

    params = {
        "building_name": model_name,
        "source_boptest": model_name,
        "zone_count": len(zones_list),
        "zones": zones_list,
        "total_area_m2_estimate": total_area
    }
    
    return params

def main():
    parser = argparse.ArgumentParser(description="Extract Boptest building info into archetype_params.json")
    parser.add_argument("model", help="BopTest model name (e.g. bestest_air)")
    parser.add_argument("--url", default="http://localhost:8000", help="BopTest API URL")
    parser.add_argument("-o", "--output", default="data/results/archetype_params.json", help="Output JSON path")
    parser.add_argument("--offline", action="store_true", help="Skip API and use filesystem discovery only")
    args = parser.parse_args()

    client = BopTestClient(url=args.url)
    try:
        if not args.offline:
            # Check if already running or select
            print(f"Connecting to Boptest for model '{args.model}'...")
            client.select_test_case(args.model)
        else:
            print(f"🚀 Offline mode enabled. Skipping API connection.")
        
        params = discover_building(client, args.model)
        if params:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                json.dump(params, f, indent=2)
            print(f"✅ Saved archetype parameters to: {output_path}")
            print(f"🚀 Now run: python src/archetype/generate_model.py --params {output_path}")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
