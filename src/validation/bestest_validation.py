#!/usr/bin/env python3
"""
Full validation: BESTEST-equivalent E+ model vs BopTest bestest_air.

This script:
1. Loads the BESTEST-equivalent E+ output (bestest_out/eplusout.csv)
2. Loads the BopTest reference (boptest_hello.csv)
3. Analyzes E+ output quality (is it dynamic?)
4. Computes ASHRAE Guideline 14 metrics on the overlap
5. Generates comparison plots and a markdown report
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.validation.metrics import validation_summary

RESULTS = Path(__file__).resolve().parents[2] / "data" / "results"
PLOTS = Path(__file__).resolve().parents[2] / "plots"


def load_eplus_bestest(csv_path: Path) -> pd.DataFrame:
    """Load BESTEST E+ CSV and return full DataFrame with parsed time index."""
    df = pd.read_csv(csv_path)
    df.columns = df.columns.str.strip()
    time_str = df["Date/Time"].str.strip()
    is_24 = time_str.str.contains("24:00:00")
    time_str = time_str.str.replace("24:00:00", "00:00:00")
    dt = pd.to_datetime("2024/" + time_str, format="%Y/%m/%d  %H:%M:%S", errors="coerce")
    dt[is_24] += pd.Timedelta(days=1)
    df["time"] = dt
    df = df.set_index("time")
    return df


def load_boptest_hello(csv_path: Path) -> pd.DataFrame:
    """Load BopTest hello CSV."""
    df = pd.read_csv(csv_path)
    df["time"] = pd.to_timedelta(df["time_h"], unit="h") + pd.Timestamp("2024-01-01")
    df = df.set_index("time")
    return df


def main():
    print("=" * 70)
    print("  BESTEST-EQUIVALENT VALIDATION ANALYSIS")
    print("=" * 70)
    
    # --- Load E+ BESTEST output ---
    ep_csv = RESULTS / "bestest_out" / "eplusout.csv"
    ep = load_eplus_bestest(ep_csv)
    
    temp_col = [c for c in ep.columns if "Zone Mean Air Temperature" in c][0]
    heat_col = [c for c in ep.columns if "Heating" in c][0]
    cool_col = [c for c in ep.columns if "Cooling" in c][0]
    
    temps = ep[temp_col].astype(float)
    heats = ep[heat_col].astype(float)
    cools = ep[cool_col].astype(float)
    
    print(f"\n--- EnergyPlus BESTEST Naive Model ---")
    print(f"  Rows: {len(ep)}")
    print(f"  Time: {temps.index.min()} -> {temps.index.max()}")
    print(f"  Temp: mean={temps.mean():.2f}C, std={temps.std():.2f}C, min={temps.min():.2f}C, max={temps.max():.2f}C")
    print(f"  Unique values: {temps.nunique()}")
    print(f"  Heating total: {heats.sum()/1e9:.3f} GJ")
    print(f"  Cooling total: {cools.sum()/1e9:.3f} GJ")
    
    # Daily stats
    daily = temps.resample("1D").agg(["mean", "min", "max", "std"])
    print(f"\n  Daily temperature variation (first 7 days):")
    for idx, row in daily.head(7).iterrows():
        day = idx.strftime("%a %m/%d")
        print(f"    {day}: mean={row['mean']:.1f}C, min={row['min']:.1f}C, max={row['max']:.1f}C, std={row['std']:.2f}")
    
    # --- Load BopTest output ---
    bt_csv = RESULTS / "boptest_hello.csv"
    bt = load_boptest_hello(bt_csv)
    
    print(f"\n--- BopTest Reference (boptest_hello.csv) ---")
    print(f"  Rows: {len(bt)}")
    print(f"  Time: {bt.index.min()} -> {bt.index.max()}")
    print(f"  Zone temp: mean={bt['zone_temp_C'].mean():.2f}C, std={bt['zone_temp_C'].std():.2f}C")
    
    # --- Hourly comparison ---
    ep_hourly = temps.resample("1h").mean().dropna()
    bt_hourly = bt["zone_temp_C"].resample("1h").mean().dropna()
    
    combined = pd.DataFrame({"sim_ep": ep_hourly, "ref_bt": bt_hourly}).dropna()
    print(f"\n--- Overlap Analysis ---")
    print(f"  E+ hourly points: {len(ep_hourly)}")
    print(f"  BT hourly points: {len(bt_hourly)}")
    print(f"  Overlapping: {len(combined)} points")
    
    if len(combined) > 0:
        print(f"\n  Overlapping data:")
        print(combined.to_string())
        
        summary = validation_summary(combined["ref_bt"].values, combined["sim_ep"].values)
        cvrmse_pass = "PASS" if summary["cvrmse_pass"] else "FAIL"
        nmbe_pass = "PASS" if summary["nmbe_pass"] else "FAIL"
        overall_pass = "PASS" if summary["overall_pass"] else "FAIL"
        
        print(f"\n--- ASHRAE Guideline 14 Results ---")
        print(f"  CVRMSE: {summary['cvrmse_pct']:.2f}%  (threshold: {summary['cvrmse_threshold']}%) {cvrmse_pass}")
        print(f"  NMBE:   {summary['nmbe_pct']:.2f}%  (threshold: +/-{summary['nmbe_threshold']}%) {nmbe_pass}")
        print(f"  Overall: {overall_pass}")
    else:
        print("  No overlapping data points!")
    
    # --- Plot 1: Full E+ time-series ---
    PLOTS.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(3, 1, figsize=(14, 10), sharex=True)
    
    axes[0].plot(temps.index, temps, linewidth=0.3, color="#DC2626")
    axes[0].set_ylabel("Zone Temp (C)")
    axes[0].set_title("BESTEST-Equivalent Naive E+ Model: Full Simulation (Jan-Mar 2024)")
    axes[0].axhline(y=21, color="green", linestyle="--", alpha=0.4, label="Heating SP (occ)")
    axes[0].axhline(y=15, color="blue", linestyle="--", alpha=0.4, label="Heating SP (unocc)")
    axes[0].axhline(y=24, color="orange", linestyle="--", alpha=0.4, label="Cooling SP (occ)")
    axes[0].legend(fontsize=8)
    axes[0].grid(True, alpha=0.3)
    
    axes[1].plot(heats.index, heats / 1e6, linewidth=0.3, color="#F59E0B")
    axes[1].set_ylabel("Heating (MJ)")
    axes[1].grid(True, alpha=0.3)
    
    axes[2].plot(cools.index, cools / 1e6, linewidth=0.3, color="#2563EB")
    axes[2].set_ylabel("Cooling (MJ)")
    axes[2].set_xlabel("Time")
    axes[2].grid(True, alpha=0.3)
    
    fig.tight_layout()
    fig.savefig(PLOTS / "bestest_naive_full.png", dpi=150)
    plt.close(fig)
    print(f"\n  Full plot saved -> plots/bestest_naive_full.png")
    
    # --- Plot 2: First 48 hours detail ---
    first_48h = temps[:pd.Timestamp("2024-01-03")]
    fig2, ax = plt.subplots(figsize=(14, 5))
    ax.plot(first_48h.index, first_48h, linewidth=1, color="#DC2626", label="E+ BESTEST Naive")
    
    # Overlay BopTest if available
    if len(combined) > 0:
        bt_plot = bt["zone_temp_C"][:pd.Timestamp("2024-01-03")]
        if len(bt_plot) > 0:
            ax.scatter(bt_plot.index, bt_plot, color="#2563EB", s=50, zorder=5, label="BopTest Reference")
    
    ax.axhline(y=21, color="green", linestyle="--", alpha=0.4, label="Heat SP (occ)")
    ax.axhline(y=15, color="blue", linestyle="--", alpha=0.4, label="Heat SP (unocc)")
    ax.set_ylabel("Zone Air Temperature (C)")
    ax.set_xlabel("Time")
    ax.set_title("BESTEST Naive Model: First 48 Hours Detail")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig2.tight_layout()
    fig2.savefig(PLOTS / "bestest_naive_48h.png", dpi=150)
    plt.close(fig2)
    print(f"  48h detail plot saved -> plots/bestest_naive_48h.png")
    
    # --- Report ---
    report = f"""# BESTEST-Equivalent Model Validation Report

## EnergyPlus Naive Model Quality

| Metric | Value |
|--------|-------|
| Simulation period | Jan 1 - Mar 1, 2024 |
| Total timesteps | {len(ep)} |
| Temperature range | {temps.min():.1f}C - {temps.max():.1f}C |
| Temperature std dev | {temps.std():.2f}C |
| Unique temp values | {temps.nunique()} |
| Total heating | {heats.sum()/1e9:.3f} GJ |
| Total cooling | {cools.sum()/1e9:.3f} GJ |

**Assessment**: The model shows {'REALISTIC' if temps.nunique() > 100 else 'SUSPICIOUS'} dynamic behavior with {temps.nunique()} unique temperature values.

## BopTest Reference Data

| Metric | Value |
|--------|-------|
| Data points | {len(bt)} |
| Time span | {bt.index.min()} - {bt.index.max()} |
| Temperature mean | {bt['zone_temp_C'].mean():.2f}C |
"""
    
    if len(combined) > 0:
        report += f"""
## ASHRAE Guideline 14 Metrics

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| CVRMSE | {summary['cvrmse_pct']:.1f}% | <=30% | {cvrmse_pass} |
| NMBE | {summary['nmbe_pct']:.1f}% | +/-10% | {nmbe_pass} |
| Overlap points | {len(combined)} | - | {'OK' if len(combined) >= 10 else 'INSUFFICIENT'} |

## Overall: {overall_pass}
"""
    else:
        report += "\n## No overlapping data for validation.\n"
    
    report_path = RESULTS / "bestest_validation_report.md"
    report_path.write_text(report, encoding="utf-8")
    print(f"  Report saved -> {report_path}")
    
    print("\n" + "=" * 70)
    print("  ANALYSIS COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
