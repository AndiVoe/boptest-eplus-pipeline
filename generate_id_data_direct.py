#!/usr/bin/env python3
import numpy as np
import pandas as pd
import argparse
from pathlib import Path

class BoptestTestCase:
    def __init__(self, fmu_path, forecast_path):
        from boptest.lib.testcase import TestCase
        self.tc = TestCase(fmupath=fmu_path, forecast_uncertainty_params_path=forecast_path)
        
    def initialize(self, start_time, warmup_period):
        status, msg, payload = self.tc.initialize(start_time, warmup_period)
        return payload
        
    def set_step(self, step):
        return self.tc.set_step(step)
        
    def advance(self, u):
        status, msg, payload = self.tc.advance(u)
        return payload

def generate_data():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str, default="multizone_office_simple_air")
    parser.add_argument("--days", type=int, default=14)
    args = parser.parse_args()

    fmu_path = f"/worker/jobs/models/{args.model}.fmu"
    forecast_path = "/worker/jobs/forecast/forecast_uncertainty_params.json"
    client = BoptestTestCase(fmu_path, forecast_path)
    
    start_time = 210 * 24 * 3600 # Summer
    duration = args.days * 24 * 3600
    dt = 3600.0
    
    print(f"Initializing {args.model} for {args.days} days excitation (DIRECT)...")
    res = client.initialize(start_time=start_time, warmup_period=7*24*3600)
    client.set_step(dt)
    
    zones = ['Nor', 'Sou', 'Eas', 'Wes', 'Cor']
    history = []
    
    print("Collecting data...")
    for t in range(int(duration / dt)):
        control_action = {}
        for z in zones:
            t_hea = np.random.uniform(288.15, 292.15) # 15-19C
            t_coo = np.random.uniform(300.15, 304.15) # 27-31C
            control_action[f"hvac_oveZonSup{z}_TZonHeaSet_u"] = t_hea
            control_action[f"hvac_oveZonSup{z}_TZonHeaSet_activate"] = 1
            control_action[f"hvac_oveZonSup{z}_TZonCooSet_u"] = t_coo
            control_action[f"hvac_oveZonSup{z}_TZonCooSet_activate"] = 1
        
        res = client.advance(control_action)
        
        entry = {'time': start_time + t * dt}
        for z in zones:
            entry[f'T_{z}'] = res.get(f'hvac_reaZon{z}_TZon_y', 293.15)
        
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
