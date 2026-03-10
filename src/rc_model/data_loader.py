#!/usr/bin/env python3
"""
MS3.1: Historical Data Preparation
Loads the BopTest reference CSV, extracts the boundary conditions (inputs) 
and the target variable (Zone Temperature), and resamples to a fixed timestep 
for use in the RC Model differential equation solver.
"""
import pandas as pd
from pathlib import Path

def load_calibration_data(csv_path: Path, resample_freq="15min"):
    """
    Parses the BopTest output into a structured DataFrame for RC model training.
    
    Inputs needed for RC 3R1C:
    - T_out : Outside Air Temperature (degC)
    - Q_hvac : Total sensible heating/cooling power from HVAC (Watts)
    - Q_sol : Solar irradiance (Watts) - approximated if not directly available
    - Q_int : Internal gains (Watts)
    
    Target needed for RC 3R1C:
    - T_z : Zone Air Temperature (degC)
    """
    if not csv_path.exists():
        raise FileNotFoundError(f"Missing historical data: {csv_path}")

    # Load raw BopTest output
    df = pd.read_csv(csv_path)
    
    # Identify relevant BopTest columns dynamically
    tz_col = "zon_reaTRooAir_y"
    tout_col = "zon_weaSta_reaWeaTDryBul_y"
    heat_col = "fcu_reaPHea_y"
    solar_col = "zon_weaSta_reaWeaHGloHor_y"
    light_col = "zon_reaPLig_y"
    plug_col = "zon_reaPPlu_y"
    # In bestest_air, solar impacts the building but may not be individually logged.
    # We will assume Q_sol = 0 and Q_int = 0 for the nocturnal 6-hour baseline
    
    # Process time and conversions
    df["datetime"] = pd.to_datetime(df["time"], unit="s", origin="2024-01-01")
    df = df.set_index("datetime")
    
    # Extract states and inputs
    data = pd.DataFrame(index=df.index)
    data["T_z"] = df[tz_col] - 273.15      # Convert Kelvin to Celsius
    data["T_out"] = df[tout_col] - 273.15  # Convert Kelvin to Celsius
    data["Q_hvac"] = df[heat_col]          # Power in Watts (Heating)
    
    # Calculate sensible solar and internal gains
    data["Q_sol"] = df[solar_col]          # W/m2 (or Watts depending on BopTest spec, will calibrate R/C accordingly)
    data["Q_int"] = df[light_col] + df[plug_col] # Internal equipment/light power in Watts
    
    # Calculate time delta in seconds from the start for ODE integration
    data["seconds_from_start"] = (data.index - data.index[0]).total_seconds()
    
    # Drop NAs if any exist from alignment
    data = data.dropna()
    
    return data

if __name__ == "__main__":
    project_root = Path(__file__).resolve().parents[2]
    csv_file = project_root / "data" / "results" / "boptest_baseline_bestest_air.csv"
    
    try:
        training_data = load_calibration_data(csv_file)
        print(f"Successfully loaded {len(training_data)} timesteps for calibration (MS3.1).")
        print("\nFirst 3 rows of prepared inputs & targets:")
        print(training_data.head(3).to_string())
    except Exception as e:
        print(f"Error loading data: {e}")
