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
        try:
            from boptest.lib.testcase import TestCase
        except ImportError:
            try:
                from testcase import TestCase
            except ImportError:
                # Add project1-boptest to path if not already there
                import sys
                import os
                boptest_root = "C:\\Users\\AVoelser\\<username>\\...\\project1-boptest" # Placeholder logic
                # We'll rely on PYTHONPATH being set correctly in the runner or dynamic detection
                from testcase import TestCase
        
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
    parser.add_argument("--model", type=str, default="bestest_air", help="BopTest model name")
    parser.add_argument("--alpha", type=float, default=1e-4, help="Energy weight")
    parser.add_argument("--beta", type=float, default=100.0, help="Comfort weight")
    args = parser.parse_args()

    print(f"Starting run_closed_loop for model: {args.model}")

    # 1. Load Calibrated Model Parameters (Model Specific)
    if args.model == "bestest_air":
        calibrated_params = {
            'R_env': 0.1922,
            'R_int': 0.0505,
            'R_vent': 0.0961,
            'C_air': 1116937.0
        }
        fmu_name = "bestest_air.fmu"
        # IO Mappings (Control)
        control_points = {
            'hea': 'con_oveTSetHea_u',
            'cool': 'con_oveTSetCoo_u'
        }
    elif args.model == "multizone_office_simple_air":
        # Approximate parameters for 5-zone office (Chicago)
        # Total area 1662 m2 -> ~330 m2 per zone
        zone_params = {
            'R_env': 0.05,
            'R_vent': 0.02,
            'C_air': 5000000.0 # 5 MJ/K
        }
        calibrated_params = [zone_params] * 5 # 5 zones
        fmu_name = "multizone_office_simple_air.fmu"
    else:
        raise ValueError(f"Unknown model: {args.model}")
    
    # 2. Setup Driver (API or Direct)
    if args.direct:
        print(f"Setup: DIRECT mode for {args.model}...")
        fmu_path = f"/worker/jobs/models/{fmu_name}"
        forecast_path = "/worker/jobs/forecast/forecast_uncertainty_params.json"
        client = BoptestTestCase(fmu_path, forecast_path)
    else:
        client = BopTestClient("http://127.0.0.1:8000")
        if args.testid:
            client.testid = args.testid
        else:
            client.select_test_case(args.model, async_select=True)
            client.wait_for_status("Running", timeout=600)
    
    start_sec = 210 * 24 * 3600 # Start in Summer (July) for multi-zone
    duration_sec = 2 * 24 * 3600 
    dt = 3600.0 # config.json says 3600.0 for multizone
    horizon_sec = 6 * 3600  
    
    if args.scenario:
        print(f"Setting scenario: {args.scenario}...")
        res = client.set_scenario(args.scenario)
        if isinstance(res, dict):
            start_sec = res.get('time', start_sec)
        print(f"Scenario start time: {start_sec}")
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

    # Flexible key mapping based on model
    T_OUT_KEYS = ['TDryBul', 'zon_weaSta_reaWeaTDryBul_y', 'weaSta_reaWeaTDryBul_y', 'TDryBul_y']
    SOL_KEYS = ['HGloHor', 'zon_weaSta_reaWeaHGloHor_y', 'weaSta_reaWeaHGloHor_y', 'HGloHor_y']

    if args.model == "multizone_office_simple_air":
        zones = ['Nor', 'Sou', 'Eas', 'Wes', 'Cor']
        T_z_k = [res.get(f'hvac_reaZon{z}_TZon_y', 293.15) for z in zones]
    else:
        T_Z_KEYS = ['zon_reaTRooAir_y', 'TRooAir_y', 'reaTZon_y', 'y']
        T_z_k = [get_val(res, T_Z_KEYS) or 293.15]

    current_time = start_sec
    final_time = start_sec + duration_sec
    
    results = []

    print(f"Simulation loop starting: {current_time} to {final_time}")
    while current_time < final_time:
        T_z_celsius = [t - 273.15 for t in T_z_k]
        
        point_names = ['TDryBul', 'HGloHor']
        forecast_df = client.get_forecast(point_names, horizon_sec, dt)
        
        if forecast_df is None or forecast_df.empty:
            print(f"Warning: Empty forecast at time {current_time}. Exiting.")
            break
            
        T_out_f = forecast_df[forecast_df.columns[forecast_df.columns.str.contains('TDryBul')][0]].values - 273.15
        Q_sol_f_base = forecast_df[forecast_df.columns[forecast_df.columns.str.contains('HGloHor')][0]].values 
        
        # Multizone Gain Mapping
        L_ij_matrix = None
        if args.model == "multizone_office_simple_air":
            # Scale solar gains by orientation (placeholders)
            Q_sol_f_list = [
                Q_sol_f_base * 0.5,  # Nor
                Q_sol_f_base * 1.5,  # Sou
                Q_sol_f_base * 1.0,  # Eas
                Q_sol_f_base * 1.0,  # Wes
                Q_sol_f_base * 0.1   # Cor
            ]
            Q_int_f_list = [np.ones_like(T_out_f) * 500.0] * 5
            
            # Identified Parameters (Phase 8 System ID)
            params_to_use = [
                {'R_env': 0.0195, 'C_air': 1.0e7},
                {'R_env': 0.0218, 'C_air': 1.0e7},
                {'R_env': 0.0224, 'C_air': 1.0e7},
                {'R_env': 0.0216, 'C_air': 1.0e7},
                {'R_env': 0.0196, 'C_air': 1.0e7}
            ]
            T_init_to_use = T_z_celsius
            
            # Identified Laplacian Coupling Matrix
            L_ij_matrix = np.array([
                [ 1.8478, -0.0004, -0.2124, -0.0000, -1.6349],
                [-0.0004,  0.8858, -0.3862, -0.4990, -0.0002],
                [-0.2124, -0.3862,  0.6250, -0.0005, -0.0258],
                [-0.0000, -0.4990, -0.0005,  0.4996, -0.0001],
                [-1.6349, -0.0002, -0.0258, -0.0001,  1.6611]
            ])
        else:
            Q_sol_f_list = [Q_sol_f_base]
            Q_int_f_list = [np.ones_like(T_out_f) * 82.56]
            params_to_use = [calibrated_params]
            T_init_to_use = [T_z_celsius[0]]

        q_hvac_opt, t_z_opt = optimize_trajectory(
            T_init_list=T_init_to_use,
            T_out_f=T_out_f,
            Q_sol_f_list=Q_sol_f_list,
            Q_int_f_list=Q_int_f_list,
            params_list=params_to_use,
            L_ij_matrix=L_ij_matrix,
            dt=dt,
            epochs=100,
            alpha_energy=args.alpha,
            beta_comfort=args.beta
        )
        
        control_action = {}
        if args.model == "bestest_air":
            t_next = float(t_z_opt[0, 1]) if t_z_opt.ndim > 1 else float(t_z_opt[1])
            q_next = float(q_hvac_opt[0, 0]) if q_hvac_opt.ndim > 1 else float(q_hvac_opt[0])
            target_T_hea = 15.0; target_T_coo = 30.0
            if q_next > 10.0: target_T_hea = t_next
            elif q_next < -10.0: target_T_coo = t_next
            control_action = {
                "con_oveTSetHea_u": target_T_hea + 273.15, "con_oveTSetHea_activate": 1,
                "con_oveTSetCoo_u": target_T_coo + 273.15, "con_oveTSetCoo_activate": 1
            }
        elif args.model == "singlezone_commercial_hydronic":
            t_next = float(t_z_opt[0, 1]) if t_z_opt.ndim > 1 else float(t_z_opt[1])
            control_action = {"oveTZonSet_u": t_next + 273.15, "oveTZonSet_activate": 1}
        elif args.model == "multizone_office_simple_air":
            zones = ['Nor', 'Sou', 'Eas', 'Wes', 'Cor']
            for idx, z in enumerate(zones):
                t_n = float(t_z_opt[idx, 1])
                q_n = float(q_hvac_opt[idx, 0])
                t_h = 15.0; t_c = 30.0
                if q_n > 10.0: t_h = t_n
                elif q_n < -10.0: t_c = t_n
                control_action[f"hvac_oveZonSup{z}_TZonHeaSet_u"] = t_h + 273.15
                control_action[f"hvac_oveZonSup{z}_TZonHeaSet_activate"] = 1
                control_action[f"hvac_oveZonSup{z}_TZonCooSet_u"] = t_c + 273.15
                control_action[f"hvac_oveZonSup{z}_TZonCooSet_activate"] = 1

        res = client.advance(control_action)
        if args.model == "multizone_office_simple_air":
            T_z_k = [res.get(f'hvac_reaZon{z}_TZon_y', 293.15) for z in zones]
        else:
            T_z_k = [get_val(res, T_Z_KEYS) or 293.15]
            
        current_time += dt
        if int(current_time) % 3600 == 0:
            hour = (current_time - start_sec) / 3600
            t_avg = np.mean([t-273.15 for t in T_z_k])
            p_tot = np.sum(q_hvac_opt[:, 0]) if q_hvac_opt.ndim > 1 else q_hvac_opt[0]
            print(f"[{hour:02.0f}h] T_avg: {t_avg:.2f}C, Total Power: {p_tot:.0f}W")
            
        results.append({'time': current_time, 'temp_avg': np.mean(T_z_k), 'p_total': np.sum(q_hvac_opt[:, 0]) if q_hvac_opt.ndim > 1 else q_hvac_opt[0]})

    print("\nMPC Loop Finished. Evaluating KPIs...")
    kpis = client.get_kpis()
    print("="*60)
    print(f" Scenario: {args.scenario or 'Default'}")
    print(f" Model: {args.model}")
    print(kpis)
    print("="*60)
    
    pd.DataFrame(results).to_csv(f"mpc_results_{args.model}.csv", index=False)

if __name__ == "__main__":
    try:
        run_closed_loop()
    except Exception as e:
        import traceback
        print("CRITICAL ERROR IN MPC LOOP:")
        traceback.print_exc()
        exit(1)
