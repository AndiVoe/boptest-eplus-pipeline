#!/usr/bin/env python3
"""
MS3.2: SciPy RC Calibration Engine (Engine A)
Implements an explicit Euler forward-pass simulator for a 3R1C RC thermal network.
Uses scipy.optimize.minimize (L-BFGS-B) to calibrate parameters against BopTest data.
"""
import json
import numpy as np
import pandas as pd
from pathlib import Path
from scipy.optimize import minimize
from src.rc_model.data_loader import load_calibration_data

class RCModel3R1C:
    def __init__(self, dt_seconds: float):
        self.dt = dt_seconds

    def simulate(self, T_init: float, inputs: np.ndarray, params: list) -> np.ndarray:
        """
        Forward Euler simulation of the 3R1C zone temperature.
        Inputs array (Nx4): [T_out, Q_hvac, Q_sol, Q_int]
        Params list (4): [R_env, R_int, R_vent, C_air]
        """
        R_env, R_int, R_vent, C_air = params
        N = len(inputs)
        T_z = np.zeros(N)
        T_z[0] = T_init

        # Precompute the equivalent resistance for heat loss
        # 1/R_eq = 1/R_env + 1/R_vent
        # Q_loss = (T_out - T_z) * (1/R_eq)
        inv_R_eq = (1.0 / R_env) + (1.0 / R_vent)
        
        for t in range(0, N - 1):
            T_out_t = inputs[t, 0]
            Q_hvac_t = inputs[t, 1]
            Q_sol_t = inputs[t, 2]
            Q_int_t = inputs[t, 3]

            # Physics ODE: C * dT/dt = (T_out - T_z) / R_eq + Q_tot
            Q_tot = Q_hvac_t + Q_sol_t + Q_int_t
            dT_dt = ((T_out_t - T_z[t]) * inv_R_eq + Q_tot) / C_air
            
            # Explicit Euler step
            T_z[t + 1] = T_z[t] + dT_dt * self.dt
            
        return T_z

def objective_function(params, model: RCModel3R1C, T_init: float, inputs: np.ndarray, targets: np.ndarray):
    """
    Computes the Mean Squared Error (MSE) between simulated T_z and BopTest T_z.
    """
    T_sim = model.simulate(T_init, inputs, params)
    mse = np.mean((T_sim - targets) ** 2)
    return mse

def calibrate_scipy(data: pd.DataFrame, template_path: Path):
    """Runs the L-BFGS-B optimizer to find the best physical parameters."""
    print("--- Engine A: SciPy L-BFGS-B Calibration ---")
    
    # Load constraints from our auto-generated semantic template
    with open(template_path, 'r') as f:
        template = json.load(f)
    
    # We calibrate the first zone found for this test
    zone_id = list(template['zones'].keys())[0]
    zone_params = template['zones'][zone_id]['parameters']
    
    initial_guess = [
        zone_params['R_env']['value'],
        zone_params['R_int']['value'],
        zone_params['R_vent']['value'],
        zone_params['C_air']['value']
    ]
    
    bounds = (
        tuple(zone_params['R_env']['bounds']),
        tuple(zone_params['R_int']['bounds']),
        tuple(zone_params['R_vent']['bounds']),
        tuple(zone_params['C_air']['bounds'])
    )
    
    # Prepare NumPy arrays for fast 
    dt = data['seconds_from_start'].diff().mode()[0]  # Timestep in seconds
    inputs = data[['T_out', 'Q_hvac', 'Q_sol', 'Q_int']].values
    targets = data['T_z'].values
    T_init = targets[0]
    
    model = RCModel3R1C(dt_seconds=dt)
    
    # Initial Baseline Error
    initial_T = model.simulate(T_init, inputs, initial_guess)
    initial_mse = np.mean((initial_T - targets) ** 2)
    print(f"Initial MSE (Seed Params): {initial_mse:.4f}")
    
    # Run Optimizer
    import time
    start_time = time.time()
    
    result = minimize(
        fun=objective_function,
        x0=initial_guess,
        args=(model, T_init, inputs, targets),
        method='L-BFGS-B',
        bounds=bounds,
        options={'maxiter': 1000, 'ftol': 1e-9}
    )
    
    train_time = time.time() - start_time
    
    print(f"Calibration finished in {train_time:.3f} seconds.")
    print(f"Final MSE: {result.fun:.4f}")
    print(f"Success: {result.success} ({result.message})")
    print(f"Calibrated R_env:  {result.x[0]:.4f} K/W (Bounds: {bounds[0]})")
    print(f"Calibrated R_int:  {result.x[1]:.4f} K/W (Bounds: {bounds[1]})")
    print(f"Calibrated R_vent: {result.x[2]:.4f} K/W (Bounds: {bounds[2]})")
    print(f"Calibrated C_air:  {result.x[3]:.0f} J/K (Bounds: {bounds[3]})")
    
    return result.x, result.fun, train_time

if __name__ == "__main__":
    project_root = Path(__file__).resolve().parents[2]
    csv_file = project_root / "data" / "results" / "boptest_baseline_bestest_air.csv"
    template_file = project_root / "data" / "models" / "rc_3r1c_template.json"
    
    df = load_calibration_data(csv_file)
    calibrate_scipy(df, template_file)
