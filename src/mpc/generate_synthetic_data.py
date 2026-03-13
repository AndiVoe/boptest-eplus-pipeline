#!/usr/bin/env python3
"""
Synthetic SysID Data Generator
==============================
Generates a known dataset for a 5-zone building to verify that 
system_id_multizone.py can correctly identify R and C parameters 
and inter-zonal coupling.
"""

import pandas as pd
import numpy as np
from pathlib import Path

def generate_synthetic_data(output_path="multizone_synthetic_data.csv", days=7):
    np.random.seed(42)
    dt = 3600
    steps = days * 24
    zones = ['Nor', 'Sou', 'Eas', 'Wes', 'Cor']
    n_zones = len(zones)
    
    # Ground Truth Parameters
    R_env_true = np.array([0.15, 0.18, 0.20, 0.12, 0.25])
    C_air_true = np.array([5e6, 6e6, 7e6, 4e6, 8e6])
    
    # Coupling Matrix (Admittance G_ij)
    # Simple star topology for testing: Core (Cor) connects to all others
    G_ij_true = np.zeros((n_zones, n_zones))
    G_ij_true[4, 0] = G_ij_true[0, 4] = 0.5
    G_ij_true[4, 1] = G_ij_true[1, 4] = 0.4
    G_ij_true[4, 2] = G_ij_true[2, 4] = 0.6
    G_ij_true[4, 3] = G_ij_true[3, 4] = 0.7
    
    # Boundary Conditions
    T_out = 273.15 + 5 + 10 * np.sin(np.linspace(0, 2*np.pi*days, steps))
    Q_sol = 500 * np.maximum(0, np.sin(np.linspace(0, 2*np.pi*days, steps)))
    
    # Control Input (PRBS Heating)
    Q_hea = np.random.choice([0, 5000], size=(steps, n_zones))
    
    # Simulation
    T_history = []
    T_curr = np.full(n_zones, 293.15)
    
    for k in range(steps):
        # Physics: C dT/dt = (T_out - T)/R_env + Q_hea + Q_sol + sum(G_ij*(Tj - Ti))
        Q_ext = (T_out[k] - T_curr) / R_env_true
        Q_couple = []
        for i in range(n_zones):
            qc = sum(G_ij_true[i, j] * (T_curr[j] - T_curr[i]) for j in range(n_zones))
            Q_couple.append(qc)
        
        dT_dt = (Q_ext + Q_hea[k] + Q_sol[k]*2.0 + np.array(Q_couple)) / C_air_true
        T_next = T_curr + dT_dt * dt
        
        # Add a tiny bit of measurement noise
        T_obs = T_next + np.random.normal(0, 0.05, n_zones)
        
        record = {
            "time": k * dt,
            "T_out": T_out[k],
            "Q_sol": Q_sol[k],
        }
        for i, z in enumerate(zones):
            record[f"T_{z}"] = T_obs[i]
            record[f"Q_hea_{z}"] = Q_hea[k, i]
            
        T_history.append(record)
        T_curr = T_next
        
    df = pd.DataFrame(T_history)
    df.to_csv(output_path, index=False)
    print(f"✅ Synthetic dataset generated at {output_path}")
    print(f"Ground Truth R_env: {R_env_true}")

if __name__ == "__main__":
    generate_synthetic_data()
