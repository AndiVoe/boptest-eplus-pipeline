#!/usr/bin/env python3
import numpy as np
import pandas as pd
import argparse
from src.boptest.client import BopTestClient

def generate_data():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str, default="multizone_office_simple_air")
    parser.add_argument("--days", type=int, default=14)
    args = parser.parse_args()

    client = BopTestClient("http://127.0.0.1:8000")
    client.select_test_case(args.model)
    
    # 14 days of data collection
    start_time = 210 * 24 * 3600 # Summer
    duration = args.days * 24 * 3600
    dt = 3600.0
    
    print(f"Initializing {args.model} for {args.days} days excitation...")
    res = client.initialize(start_time=start_time, warmup_period=7*24*3600)
    client.set_step(dt)
    
    zones = ['Nor', 'Sou', 'Eas', 'Wes', 'Cor']
    history = []
    
    print("Collecting data...")
    for t in range(int(duration / dt)):
        # Apply random excitation setpoints to "shake" the building thermal mass
        control_action = {}
        for z in zones:
            # Random setpoints between 18C and 28C
            t_hea = np.random.uniform(18, 22)
            t_coo = np.random.uniform(24, 28)
            control_action[f"hvac_oveZonSup{z}_TZonHeaSet_u"] = t_hea + 273.15
            control_action[f"hvac_oveZonSup{z}_TZonHeaSet_activate"] = 1
            control_action[f"hvac_oveZonSup{z}_TZonCooSet_u"] = t_coo + 273.15
            control_action[f"hvac_oveZonSup{z}_TZonCooSet_activate"] = 1
        
        # Advance simulation
        res = client.advance(control_action)
        
        # Log measurements
        entry = {'time': start_time + t * dt}
        # Temperatures
        for z in zones:
            entry[f'T_{z}'] = res.get(f'hvac_reaZon{z}_TZon_y', 293.15)
        # Disturbances
        entry['T_out'] = res.get('weaSta_reaWeaTDryBul_y', 293.15)
        entry['Q_sol'] = res.get('weaSta_reaWeaHGloHor_y', 0.0)
        
        history.append(entry)
        
        if t % 24 == 0:
            print(f"Progress: {t/24:.0f}/{args.days} days")

    df = pd.DataFrame(history)
    df.to_csv("multizone_id_data.csv", index=False)
    print("Data saved to multizone_id_data.csv")

if __name__ == "__main__":
    generate_data()
