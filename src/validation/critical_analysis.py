#!/usr/bin/env python3
"""Critical analysis of simulation output quality."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from pathlib import Path

RESULTS = Path(__file__).resolve().parents[2] / "data" / "results"
PLOTS = Path(__file__).resolve().parents[2] / "plots"


def analyze_eplus():
    """Deep analysis of the EnergyPlus naive model output."""
    print("=" * 70)
    print("  CRITICAL ANALYSIS: EnergyPlus Naive Model Output")
    print("=" * 70)
    
    df = pd.read_csv(RESULTS / "eplusout.csv")
    df.columns = df.columns.str.strip()
    
    print(f"\nTotal rows: {len(df)}")
    print(f"Columns: {list(df.columns)}")
    
    # Parse time
    time_str = df["Date/Time"].str.strip()
    is_24 = time_str.str.contains("24:00:00")
    time_str = time_str.str.replace("24:00:00", "00:00:00")
    dt = pd.to_datetime("2024/" + time_str, format="%Y/%m/%d  %H:%M:%S", errors="coerce")
    dt[is_24] += pd.Timedelta(days=1)
    df["time"] = dt
    df = df.set_index("time")
    
    # Analyze each column
    for col in df.columns:
        if col == "Date/Time":
            continue
        series = df[col].astype(float)
        print(f"\n--- {col} ---")
        print(f"  count: {series.count()}")
        print(f"  mean:  {series.mean():.4f}")
        print(f"  std:   {series.std():.4f}")
        print(f"  min:   {series.min():.4f}")
        print(f"  max:   {series.max():.4f}")
        
        # Check for constant values
        unique_vals = series.nunique()
        print(f"  unique values: {unique_vals}")
        if unique_vals < 10:
            print(f"  VALUE DISTRIBUTION: {series.value_counts().head(10).to_dict()}")
        
        # Check daily variation
        daily = series.resample("1D").agg(["mean", "min", "max", "std"])
        print(f"\n  Daily variation (first 7 days):")
        for idx, row in daily.head(7).iterrows():
            day_str = idx.strftime("%Y-%m-%d")
            print(f"    {day_str}: mean={row['mean']:.2f}, min={row['min']:.2f}, max={row['max']:.2f}, std={row['std']:.4f}")
    
    # Plot full time series
    temp_col = [c for c in df.columns if "Temperature" in c][0]
    heat_col = [c for c in df.columns if "Heating" in c][0]
    cool_col = [c for c in df.columns if "Cooling" in c][0]
    
    fig, axes = plt.subplots(3, 1, figsize=(14, 10), sharex=True)
    
    axes[0].plot(df.index, df[temp_col], linewidth=0.5, color="#DC2626")
    axes[0].set_ylabel("Zone Temp (C)")
    axes[0].set_title("EnergyPlus Naive Model: Full Simulation Period (Jan-Mar 2024)")
    axes[0].grid(True, alpha=0.3)
    
    axes[1].plot(df.index, df[heat_col].astype(float) / 1e6, linewidth=0.5, color="#F59E0B")
    axes[1].set_ylabel("Heating Energy (MJ)")
    axes[1].grid(True, alpha=0.3)
    
    axes[2].plot(df.index, df[cool_col].astype(float) / 1e6, linewidth=0.5, color="#2563EB")
    axes[2].set_ylabel("Cooling Energy (MJ)")
    axes[2].set_xlabel("Time")
    axes[2].grid(True, alpha=0.3)
    
    fig.tight_layout()
    PLOTS.mkdir(parents=True, exist_ok=True)
    fig.savefig(PLOTS / "eplus_full_timeseries.png", dpi=150)
    plt.close(fig)
    print(f"\n  Full time-series plot saved -> plots/eplus_full_timeseries.png")


def analyze_boptest():
    """Analyze the BopTest reference data."""
    print("\n" + "=" * 70)
    print("  CRITICAL ANALYSIS: BopTest Reference Data (boptest_hello.csv)")
    print("=" * 70)
    
    df = pd.read_csv(RESULTS / "boptest_hello.csv")
    print(f"\nTotal rows: {len(df)}")
    print(f"Columns: {list(df.columns)}")
    print(f"\nFull data:")
    print(df.to_string())
    
    print(f"\n  PROBLEM: Only {len(df)} data points!")
    print(f"  Time span: {df['time_h'].iloc[0]}h to {df['time_h'].iloc[-1]}h ({df['time_h'].iloc[-1] - df['time_h'].iloc[0]:.2f}h total)")
    print(f"  Step size: {df['time_h'].diff().dropna().iloc[0]*3600:.0f} seconds")


def analyze_validation_math():
    """Verify the CVRMSE/NMBE calculation makes sense."""
    print("\n" + "=" * 70)
    print("  CRITICAL ANALYSIS: Validation Math Check")
    print("=" * 70)
    
    # Manually compute with the actual data points
    ref_vals = np.array([20.01, 19.98])  # approximate BopTest values at hour 0 and 1
    sim_vals = np.array([18.0, 18.0])    # E+ values (constant 18.0)
    
    ref_mean = np.mean(ref_vals)
    residuals = sim_vals - ref_vals
    
    print(f"\n  Reference values:  {ref_vals}")
    print(f"  Simulation values: {sim_vals}")
    print(f"  Residuals:         {residuals}")
    print(f"  Reference mean:    {ref_mean:.4f}")
    
    # NMBE
    nmbe = 100 * np.sum(residuals) / (len(residuals) * ref_mean)
    print(f"\n  NMBE = 100 * sum(residuals) / (n * ref_mean)")
    print(f"       = 100 * {np.sum(residuals):.4f} / ({len(residuals)} * {ref_mean:.4f})")
    print(f"       = {nmbe:.2f}%")
    
    # CVRMSE
    rmse = np.sqrt(np.mean(residuals**2))
    cvrmse = 100 * rmse / ref_mean
    print(f"\n  RMSE = sqrt(mean(residuals^2))")
    print(f"       = sqrt({np.mean(residuals**2):.4f})")
    print(f"       = {rmse:.4f}")
    print(f"  CVRMSE = 100 * RMSE / ref_mean")
    print(f"         = 100 * {rmse:.4f} / {ref_mean:.4f}")
    print(f"         = {cvrmse:.2f}%")
    
    print(f"\n  CONCLUSION: CVRMSE ~= NMBE because the E+ model output is CONSTANT (18.0C)!")
    print(f"  When sim is a flat line, RMSE = |mean(sim) - mean(ref)| = bias")
    print(f"  So CVRMSE = NMBE (mathematical tautology with constant sim values)")
    print(f"\n  THIS IS NOT A VALID COMPARISON - the naive model lacks dynamics!")


def diagnose_problems():
    """Summarize all the problems found."""
    print("\n" + "=" * 70)
    print("  DIAGNOSIS SUMMARY")
    print("=" * 70)
    print("""
  PROBLEM 1: E+ model temperature is CONSTANT at 18.0C
    - This is the heating setback temperature
    - The model runs Jan 1 (midnight) which is weekend/off-hours
    - With setback at 18C and IdealLoads, it just holds 18C perfectly
    - NO dynamic behavior (no solar gains, no occupancy variation visible)
    
  PROBLEM 2: Only 2 overlapping data points
    - BopTest hello run was only 4 timesteps (1 hour)  
    - After hourly resampling, only 2 usable points remain
    - ASHRAE Guideline 14 requires minimum 12 months for monthly CVRMSE
      or large samples for hourly CVRMSE
    
  PROBLEM 3: Comparing different buildings
    - BopTest 'bestest_air' = simple BESTEST test case (single-zone box)
    - Naive E+ model = 28-zone office building from archetype
    - These are fundamentally different buildings!
    - Validation should compare same geometry/parameters
    
  PROBLEM 4: CVRMSE = NMBE (suspicious equality)
    - When simulation is a flat line (constant), RMSE = |bias|
    - So CVRMSE = |NMBE| always (mathematical artifact)
    - This means the metrics carry no additional information
    
  ROOT CAUSE: The pipeline works mechanically, but the comparison 
  is scientifically invalid because we're comparing different buildings 
  with insufficient data overlap.
""")


if __name__ == "__main__":
    analyze_eplus()
    analyze_boptest()
    analyze_validation_math()
    diagnose_problems()
    print("\nCritical analysis complete.")
