import pandas as pd
import numpy as np
import os

def calculate_kpis(csv_path, name):
    if not os.path.exists(csv_path):
        return None
    
    df = pd.read_csv(csv_path)
    
    # Identify dt
    if len(df) > 1:
        dt = df['time'].iloc[1] - df['time'].iloc[0]
    else:
        dt = 3600 # Default
    
    # Energy: p_total or p_opt in W
    # Total energy in kWh = sum(W * dt / 3600) / 1000
    p_col = 'p_total' if 'p_total' in df.columns else 'p_opt'
    energy_kwh = (df[p_col] * dt / 3600.0).sum() / 1000.0
    
    # Discomfort: Kelvin-hours outside [21, 24] C
    temp_col = 'temp_avg' if 'temp_avg' in df.columns else 'temp'
    temp_c = df[temp_col] - 273.15
    
    lower_bound = 21.0
    upper_bound = 24.0
    
    # Discomfort in Kelvin-hours (Kh)
    # dev = deviation in K * hours_per_step
    dev = np.maximum(0, lower_bound - temp_c) + np.maximum(0, temp_c - upper_bound)
    discomfort_kh = (dev * dt / 3600.0).sum()
    
    return {
        "Scenario": name,
        "Rows": len(df),
        "dt [s]": dt,
        "Energy [kWh]": round(float(energy_kwh), 2),
        "Discomfort [Kh]": round(float(discomfort_kh), 2),
        "Avg Temp [C]": round(float(temp_c.mean()), 2),
        "Min Temp [C]": round(float(temp_c.min()), 2),
        "Max Temp [C]": round(float(temp_c.max()), 2)
    }

files = [
    ("mpc_results_winter_5zone.csv", "5-Zone Winter"),
    ("mpc_results_shoulder_5zone.csv", "5-Zone Shoulder"),
    ("mpc_results_multizone_office_simple_air.csv", "5-Zone Summer"),
    ("mpc_results_singlezone_commercial_hydronic.csv", "Copenhagen (Hydronic)")
]

results = []
for f, n in files:
    res = calculate_kpis(f, n)
    if res:
        results.append(res)

print(pd.DataFrame(results).to_string(index=False))
