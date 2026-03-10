#!/usr/bin/env python3
"""
MS3.4: Dual-Engine Benchmark & Validation
Master script to execute both SciPy (Engine A) and PyTorch (Engine B) calibration routines.
Benchmarks training time, final MSE, and calculates ASHRAE Guideline 14 CVRMSE and NMBE.
"""
import numpy as np
import pandas as pd
from pathlib import Path
from src.rc_model.data_loader import load_calibration_data
from src.rc_model.simulator_scipy import calibrate_scipy, RCModel3R1C
from src.rc_model.simulator_torch import calibrate_torch

def calculate_ashrae_metrics(T_sim: np.ndarray, T_obs: np.ndarray):
    """Calculates ASHRAE CVRMSE and NMBE."""
    n = len(T_obs)
    mean_obs = np.mean(T_obs)
    
    # Needs to handle mean_obs == 0, but T is in Celsius (approx 20C)
    mse = np.mean((T_sim - T_obs) ** 2)
    rmse = np.sqrt(mse)
    cvrmse = (rmse / mean_obs) * 100.0
    
    nmbe = (np.sum(T_sim - T_obs) / (n * mean_obs)) * 100.0
    
    return cvrmse, nmbe

def main():
    print("="*60)
    print(" PHASE 3: HYBRID VIRTUAL IN-SITU CALIBRATION BENCHMARK")
    print("="*60)
    
    project_root = Path(__file__).resolve().parents[2]
    csv_file = project_root / "data" / "results" / "boptest_baseline_bestest_air.csv"
    template_file = project_root / "data" / "models" / "rc_3r1c_template.json"
    
    if not csv_file.exists():
        print("Missing BopTest ground-truth data. Run MS1 first.")
        return
        
    df = load_calibration_data(csv_file)
    print(f"Loaded {len(df)} timesteps of 15-minute BopTest data.")
    print(f"Target variable: Zone Temperature (T_z)\n")
    
    # Extract arrays for final metrics calculation
    dt = df['seconds_from_start'].diff().mode()[0]
    inputs = df[['T_out', 'Q_hvac', 'Q_sol', 'Q_int']].values
    T_obs = df['T_z'].values
    T_init = T_obs[0]
    
    # --- ENGINE A (SciPy) ---
    print(">>> Starting Engine A (SciPy L-BFGS-B)...")
    scipy_params, scipy_mse, scipy_time = calibrate_scipy(df, template_file)
    
    # Simulate forward pass with calibrated SciPy params to get T_sim
    model_scipy = RCModel3R1C(dt)
    T_sim_scipy = model_scipy.simulate(T_init, inputs, scipy_params)
    scipy_cvrmse, scipy_nmbe = calculate_ashrae_metrics(T_sim_scipy, T_obs)
    
    # --- ENGINE B (PyTorch) ---
    print("\n>>> Starting Engine B (PyTorch Adam)...")
    torch_params, torch_mse, torch_time = calibrate_torch(df, template_file)
    
    # Simulate forward pass with calibrated Torch params to get T_sim
    # We can use the SciPy simulator for identical validation since the physics are the same
    T_sim_torch = model_scipy.simulate(T_init, inputs, torch_params)
    torch_cvrmse, torch_nmbe = calculate_ashrae_metrics(T_sim_torch, T_obs)
    
    # --- REPORT ---
    print("\n" + "="*60)
    print(" DUAL-ENGINE BENCHMARK RESULTS")
    print("="*60)
    
    report = pd.DataFrame({
        "Engine": ["SciPy L-BFGS-B", "PyTorch Adam"],
        "Time (s)": [f"{scipy_time:.3f}", f"{torch_time:.3f}"],
        "Final MSE": [f"{scipy_mse:.4f}", f"{torch_mse:.4f}"],
        "CVRMSE (%)": [f"{scipy_cvrmse:.2f}", f"{torch_cvrmse:.2f}"],
        "NMBE (%)": [f"{scipy_nmbe:.2f}", f"{torch_nmbe:.2f}"],
        "R_env (K/W)": [f"{scipy_params[0]:.4f}", f"{torch_params[0]:.4f}"],
        "C_air (J/K)": [f"{scipy_params[3]:.0f}", f"{torch_params[3]:.0f}"]
    })
    
    # ASHRAE GUIDELINE 14 CRITERIA
    print(report.to_string(index=False))
    print("-" * 60)
    print("ASHRAE Thresholds: CVRMSE <= 30%, NMBE <= +-10%")
    print("="*60)

if __name__ == "__main__":
    main()
