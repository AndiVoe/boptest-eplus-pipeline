#!/usr/bin/env python3
"""
Master Validation Benchmarking Suite
====================================
Iterates through all 4 key validation cases and runs the full 
orchestrator (MPC vs RBC) for each.
"""

import subprocess
import os
from pathlib import Path

CASES = [
    {
        "name": "bestest_air",
        "model": "bestest_air",
        "scenario": "typical_heat_day",
        "idf": "data/results/bestest_naive.idf"
    },
    {
        "name": "seasonal_study_winter",
        "model": "multizone_office_simple_air",
        "scenario": "peak_heat_day",
        "idf": "data/results/multizone_office_naive.idf"
    },
    {
        "name": "multizone_office_dynamic",
        "model": "multizone_office_simple_air",
        "scenario": "typical_cool_day",
        "idf": "data/results/multizone_office_naive.idf"
    },
    {
        "name": "south_tyrol_bfh",
        "model": "multizone_office_simple_air",  # Proxied to multizone for control logic test
        "scenario": "typical_heat_day",
        "idf": "data/results/south_tyrol_baseline.idf"
    }
]

def run_orchestrator(case):
    print(f"\n\n{'#'*80}")
    print(f"### RUNNING MASTER BENCHMARK: {case['name']}")
    print(f"{'#'*80}\n")
    
    cmd = [
        "python", "phd_pipeline_orchestrator.py",
        "--idf", case['idf'],
        "--model", case['model'],
        "--scenario", case['scenario'],
        "--preflight"
    ]
    
    # Run the orchestrator
    result = subprocess.run(cmd, capture_output=False)
    return result.returncode == 0

def main():
    print("🚀 Starting Master Benchmarking Suite...")
    success_count = 0
    
    for case in CASES:
        if run_orchestrator(case):
            success_count += 1
            print(f"✅ Case {case['name']} completed.")
        else:
            print(f"❌ Case {case['name']} failed.")
            
    print(f"\nCompleted {success_count}/{len(CASES)} cases.")

if __name__ == "__main__":
    main()
