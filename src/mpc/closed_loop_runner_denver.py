#!/usr/bin/env python3
"""
MS4.3: Closed-Loop Executer (closed_loop_runner.py)
Orchestrates the Phase 4 live testing.
Initializes the BopTest container, reads the current states and forecasts, compiles inputs,
triggers the PyTorch MPC, and sends the optimal heating setpoint to BopTest every 15 minutes.
"""
import time
import json
import numpy as np
import pandas as pd
from pathlib import Path
from src.boptest.client import BopTestClient
from src.mpc.controller import optimize_trajectory

import argparse

class BoptestTestCase:
    """Wrapper to make internal TestCase look like BopTestClient for the runner."""
    def __init__(self, fmu_path, forecast_path):
        from boptest.lib.testcase import TestCase
        # Provide explicit paths to bypass directory resolution errors
        self.tc = TestCase(fmupath=fmu_path, forecast_uncertainty_params_path=forecast_path)
        self.testid = "direct_sim"
        
    def initialize(self, start_time, warmup_period):
        status, msg, payload = self.tc.initialize(start_time, warmup_period)
        return {"payload": payload}
        
    def set_scenario(self, scenario):
        # BopTest set_scenario expects a dict with all keys
        config = {
            'time_period': scenario,
            'electricity_price': 'constant',
            'temperature_uncertainty': None,
            'solar_uncertainty': None,
            'seed': None
        }
        status, msg, payload = self.tc.set_scenario(config)
        return payload
        
    def set_step(self, step):
        return self.tc.set_step(step)
        
    def get_forecast(self, point_names, horizon, interval):
        # Internal Boptest TestCase.get_forecast takes (point_names, horizon, interval)
        status, msg, payload = self.tc.get_forecast(point_names, horizon, interval)
        print(f"DEBUG: get_forecast payload type: {type(payload)}")
        if payload:
            print(f"DEBUG: get_forecast payload summary: {list(payload.keys()) if isinstance(payload, dict) else len(payload)}")
        df = pd.DataFrame(payload)
        print(f"DEBUG: get_forecast df columns: {df.columns.tolist() if not df.empty else 'EMPTY'}")
        return df
        
    def advance(self, u):
        status, msg, payload = self.tc.advance(u)
        return payload
        
    def get_kpis(self):
        status, msg, payload = self.tc.get_kpis()
        return pd.DataFrame([payload])

def run_closed_loop():
    parser = argparse.ArgumentParser()
    parser.add_argument("--direct", action="store_true", help="Run directly against FMU (no Web API)")
    parser.add_argument("--testid", type=str, default=None)
    parser.add_argument("--scenario", type=str, default=None, help="BopTest scenario (e.g., typical_heat_day)")
    args = parser.parse_args()

    print("Starting run_closed_loop script logic...")
    # 1. Load Calibrated Model Parameters
    calibrated_params = {
        'R_env': 0.1922,
        'R_int': 0.0505,
        'R_vent': 0.0961,
        'C_air': 1116937.0
    }
    
    # 2. Setup Driver (API or Direct)
    if args.direct:
        print("Setup: DIRECT mode (bypassing Web API)...")
        fmu_path = "/worker/jobs/models/bestest_air.fmu"
        forecast_path = "/worker/jobs/forecast/forecast_uncertainty_params.json"
        client = BoptestTestCase(fmu_path, forecast_path)
    else:
        client = BopTestClient("http://127.0.0.1:8000")
        if args.testid:
            client.testid = args.testid
        else:
            client.select_test_case("bestest_air", async_select=True)
            client.wait_for_status("Running", timeout=600)
    
    start_sec = 10 * 24 * 3600 # Default
    duration_sec = 2 * 24 * 3600 
    dt = 900.0  
    horizon_sec = 6 * 3600  
    
    if args.scenario:
        print(f"Setting scenario: {args.scenario}...")
        res = client.set_scenario(args.scenario)
        # For typical_heat_day, typical_cool_day, mix_day, etc.
        # BopTest set_scenario returns the first measurement payload
        start_sec = res.get('time', 0) if isinstance(res, dict) else 0
    else:
        print(f"Initializing BopTest (Start: {start_sec}s, Warmup: 7 days)...")
        res = client.initialize(start_time=start_sec, warmup_period=7*24*3600)

    print("Setting simulation step...")
    client.set_step(dt)
    
    def get_val(data, keys):
        if not data: return None
        # Handle BopTest nesting levels: payload or time_period
        search_dicts = [data]
        if isinstance(data, dict):
            if 'payload' in data: search_dicts.append(data['payload'])
            if 'time_period' in data: search_dicts.append(data['time_period'])
            
        for d in search_dicts:
            if not isinstance(d, dict): continue
            for k in keys:
                if k in d: return d[k]
        return None

    T_Z_KEYS = ['zon_reaTRooAir_y', 'TRooAir_y', 'y']
    T_OUT_KEYS = ['TDryBul', 'zon_weaSta_reaWeaTDryBul_y', 'weaSta_reaWeaTDryBul_y', 'TDryBul_y']
    SOL_KEYS = ['HGloHor', 'zon_weaSta_reaWeaHGloHor_y', 'weaSta_reaWeaHGloHor_y', 'HGloHor_y']

    T_z_k = get_val(res, T_Z_KEYS)
    if T_z_k is None:
        print(f"Error: Could not find Zone Temp in {res}")
        return

    current_time = start_sec
    final_time = start_sec + duration_sec
    
    while current_time < final_time:
        T_z_celsius = T_z_k - 273.15
        
        point_names = ['TDryBul', 'HGloHor']
        forecast_df = client.get_forecast(point_names, horizon_sec, dt)
        
        if forecast_df is None or forecast_df.empty:
            print(f"Warning: Empty forecast at time {current_time}. Exiting.")
            break
            
        T_out_forecast_celsius = forecast_df[T_OUT_KEYS[0]].values - 273.15
        Q_sol_forecast_watts = forecast_df[SOL_KEYS[0]].values 
        Q_int_forecast_watts = np.ones_like(T_out_forecast_celsius) * 82.56
        
        q_hvac_opt, t_z_opt = optimize_trajectory(
            T_init_celsius=T_z_celsius,
            T_out_forecast_celsius=T_out_forecast_celsius,
            Q_sol_forecast_watts=Q_sol_forecast_watts,
            Q_int_forecast_watts=Q_int_forecast_watts,
            calibrated_params=calibrated_params,
            dt_seconds=dt,
            epochs=100
        )
        
        # Bi-directional setpoint mapping
        target_T_hea = 15.0
        target_T_coo = 30.0
        
        if q_hvac_opt[0] > 10.0:
            target_T_hea = float(t_z_opt[1])
        elif q_hvac_opt[0] < -10.0:
            target_T_coo = float(t_z_opt[1])
            
        control_action = {
            "con_oveTSetHea_u": target_T_hea + 273.15,
            "con_oveTSetHea_activate": 1,
            "con_oveTSetCoo_u": target_T_coo + 273.15,
            "con_oveTSetCoo_activate": 1
        }
        
        res = client.advance(control_action)
        T_z_k = get_val(res, T_Z_KEYS)
        current_time += dt
        
        if int(current_time) % 3600 == 0:
            hour = (current_time - start_sec) / 3600
            mode = "HEAT" if q_hvac_opt[0] > 10 else ("COOL" if q_hvac_opt[0] < -10 else "OFF")
            print(f"[{hour:02.0f}h] T_zone: {T_z_k-273.15:.2f}C, Mode: {mode}, Power: {q_hvac_opt[0]:.0f}W")

    print("\nMPC Loop Finished. Evaluating KPIs...")
    kpis = client.get_kpis()
    energy = kpis['ener_tot'].iloc[0] if 'ener_tot' in kpis.columns else 0
    comfort = kpis['tdis_tot'].iloc[0] if 'tdis_tot' in kpis.columns else 0
    
    print("="*60)
    print(f" Scenario: {args.scenario or 'Default'}")
    print(f" Total Energy: {energy:.2f}")
    print(f" Comfort Violations (Kh): {comfort:.2f}")
    print("="*60)

if __name__ == "__main__":
    try:
        run_closed_loop()
    except Exception as e:
        import traceback
        print("CRITICAL ERROR IN MPC LOOP:")
        traceback.print_exc()
        exit(1)
