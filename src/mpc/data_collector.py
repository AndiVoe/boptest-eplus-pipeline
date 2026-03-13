#!/usr/bin/env python3
"""
SysID Data Collector (data_collector.py)
=======================================
Orchestrates Phase 20 data acquisition. Runs a 14-day simulation 
on Boptest using a PRBS (Pseudo-Random Binary Sequence) signal 
to excite building dynamics for multi-zone System Identification.
"""

import os
import sys
import json
import random
import pandas as pd
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.boptest.client import BopTestClient

def generate_prbs(length, levels=(293.15, 298.15)):
    """Generates a random sequence of two values."""
    return [random.choice(levels) for _ in range(length)]

def run_collection(model="multizone_office_simple_air", duration_days=14):
    print(f"🚀 Starting SysID Data Collection for {model} ({duration_days} days)")
    
    client = BopTestClient("http://localhost:8000")
    client.select_test_case(model, async_select=True)
    client.wait_for_status("Running", timeout=600)
    
    # Initialize with 7 day warmup
    # Start at week 1 (Monday)
    start_time = 0 
    client.initialize(start_time=start_time, warmup_period=7*24*3600)
    
    dt = 3600  # 1 hour steps for SysID
    client.set_step(dt)
    
    zones = ['Nor', 'Sou', 'Eas', 'Wes', 'Cor']
    steps = int(duration_days * 24)
    
    # Generate PRBS for each zone's heating setpoint
    # We toggle between 20C and 25C to ensure thermal response
    prbs_signals = {z: generate_prbs(steps, levels=(273.15 + 20, 273.15 + 25)) for z in zones}
    
    history = []
    
    print(f"Exerting PRBS signals for {steps} hours...")
    for k in range(steps):
        # Prepare inputs
        u = {}
        for z in zones:
            # Multi-zone office simple air naming convention:
            # hvac_oveZonSup{Zone}_TZonHeaSet_u
            u[f"hvac_oveZonSup{z}_TZonHeaSet_u"] = prbs_signals[z][k]
            u[f"hvac_oveZonSup{z}_TZonHeaSet_activate"] = 1
            # Keep cooling high to avoid interference
            u[f"hvac_oveZonSup{z}_TZonCooSet_u"] = 273.15 + 30
            u[f"hvac_oveZonSup{z}_TZonCooSet_activate"] = 1
            
        res = client.advance(u)
        
        # Collect measurements
        record = {
            "time": k * dt,
            "T_out": res.get("weaSta_reaWeaTDryBul_y", 293.15),
            "Q_sol": res.get("weaSta_reaWeaHGloHor_y", 0.0)
        }
        for z in zones:
            record[f"T_{z}"] = res.get(f"hvac_reaZon{z}_TZon_y", 293.15)
            record[f"Q_hea_{z}"] = prbs_signals[z][k]
            # Extract actual heating power if available
            record[f"P_hea_{z}"] = res.get(f"hvac_reaZonAct{z}_yReaHea_y", 0.0)
            
        history.append(record)
        
        if k % 24 == 0:
            print(f"  Day {k//24 + 1}/{duration_days} complete...")
            
    df = pd.DataFrame(history)
    output_path = Path("data/results/sysid_multizone_dataset.csv")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    
    print(f"✅ Data collection complete. Results saved to {output_path}")

if __name__ == "__main__":
    run_collection()
