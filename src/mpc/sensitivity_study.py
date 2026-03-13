import subprocess
import os
import pandas as pd
import numpy as np
import time
from pathlib import Path

import argparse

def run_sensitivity():
    parser = argparse.ArgumentParser()
    parser.add_argument("--testid", type=str, default=None, help="Existing BopTest testid")
    args_in = parser.parse_args()
    
    # Weights for alpha (Energy) vs beta (Comfort) sweep
    # We'll fix alpha=1e-4 and sweep beta from 1 to 1000
    betas = [1.0, 10.0, 100.0, 500.0, 1000.0]
    alpha = 1e-4
    model = "bestest_air"
    scenario = "typical_heat_day"
    
    testid = args_in.testid
    
    results = []
    
    print(f"🚀 Starting Sensitivity Study for {model}")
    if testid:
        print(f"Using existing testid: {testid}")
    print(f"Sweep range: beta = {betas}")
    
    for beta in betas:
        print(f"\n--- Testing Weight: alpha={alpha}, beta={beta} ---")
        
        # Run MPC Runner
        cmd = [
            "python", "-m", "src.mpc.closed_loop_runner",
            "--model", model,
            "--scenario", scenario,
            "--alpha", str(alpha),
            "--beta", str(beta)
        ]
        if testid:
            cmd += ["--testid", testid]
        
        env = os.environ.copy()
        env["PYTHONPATH"] = str(Path.cwd())
        
        start_time = time.time()
        subprocess.run(cmd, env=env, check=True)
        end_time = time.time()
        
        # Extract results from mpc_results_bestest_air.csv
        # Actually, the runner prints KPIs but doesn't return them.
        # Let's read the mpc_results_bestest_air.csv for trajectory-based manual KPI calc
        csv_file = f"mpc_results_{model}.csv"
        if os.path.exists(csv_file):
            df = pd.read_csv(csv_file)
            # Simple KPI calc: Total Power Sum * dt / 3.6e6
            energy = (df['p_total'].sum() * 3600) / 3.6e6
            # Discomfort calc (simplified)
            temps = df['temp_avg'] - 273.15
            discomfort = (temps[temps < 21].apply(lambda x: 21 - x).sum() + 
                          temps[temps > 24].apply(lambda x: x - 24).sum())
            
            results.append({
                'alpha': alpha,
                'beta': beta,
                'energy_kWh': energy,
                'discomfort_Kh': discomfort,
                'runtime_sec': end_time - start_time
            })
            print(f"Result: Energy={energy:.2f} kWh, Discomfort={discomfort:.2f} Kh")
        else:
            print(f"Warning: No result CSV found for beta={beta}")

    # Save summary
    res_df = pd.DataFrame(results)
    res_df.to_csv("data/results/sensitivity_results.csv", index=False)
    print("\n✨ Sensitivity Study Complete! Results saved to 'data/results/sensitivity_results.csv'")

if __name__ == "__main__":
    run_sensitivity()
