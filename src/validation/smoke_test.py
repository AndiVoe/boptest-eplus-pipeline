#!/usr/bin/env python3
"""Pipeline smoke test: validate E+ naive model against BopTest baseline."""
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend for headless machines
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.validation.metrics import validation_summary

RESULTS_DIR = Path(__file__).resolve().parents[2] / "data" / "results"
PLOTS_DIR = Path(__file__).resolve().parents[2] / "plots"


def load_eplus(csv_path: Path) -> pd.Series:
    """Load EnergyPlus CSV and return hourly zone temperature."""
    df = pd.read_csv(csv_path)
    df.columns = df.columns.str.strip()
    time_str = df["Date/Time"].str.strip()
    is_24 = time_str.str.contains("24:00:00")
    time_str = time_str.str.replace("24:00:00", "00:00:00")
    dt = pd.to_datetime("2024/" + time_str, format="%Y/%m/%d  %H:%M:%S", errors="coerce")
    dt[is_24] += pd.Timedelta(days=1)
    df["_time"] = dt
    df = df.set_index("_time")
    
    # Find first temperature column
    temp_cols = [c for c in df.columns if "Zone Mean Air Temperature" in c]
    if not temp_cols:
        raise ValueError(f"No temperature column found. Columns: {list(df.columns)}")
    col = temp_cols[0]
    print(f"  [E+]  Using column: {col}")
    return df[col].astype(float).resample("1h").mean().dropna()


def load_boptest(csv_path: Path) -> pd.Series:
    """Load BopTest CSV and return hourly zone temperature."""
    df = pd.read_csv(csv_path)
    if "time_h" in df.columns:
        df["_time"] = pd.to_timedelta(df["time_h"], unit="h") + pd.Timestamp("2024-01-01")
    elif "time_s" in df.columns:
        df["_time"] = pd.to_timedelta(df["time_s"], unit="s") + pd.Timestamp("2024-01-01")
    else:
        raise ValueError(f"No time column found. Columns: {list(df.columns)}")
    df = df.set_index("_time")
    
    if "zone_temp_C" in df.columns:
        col = "zone_temp_C"
    else:
        temp_cols = [c for c in df.columns if "temp" in c.lower()]
        if temp_cols:
            col = temp_cols[0]
        else:
            raise ValueError(f"No temperature column found. Columns: {list(df.columns)}")
    print(f"  [BT]  Using column: {col}")
    return df[col].astype(float).resample("1h").mean().dropna()


def main():
    print("=" * 60)
    print("  PIPELINE SMOKE TEST")
    print("=" * 60)
    
    ep_csv = RESULTS_DIR / "eplusout.csv"
    bt_csv = RESULTS_DIR / "boptest_hello.csv"
    
    if not ep_csv.exists():
        print(f"ERROR: {ep_csv} not found. Run EnergyPlus simulation first.")
        sys.exit(1)
    if not bt_csv.exists():
        print(f"ERROR: {bt_csv} not found. Run BopTest hello first.")
        sys.exit(1)
    
    print("\n--- Loading data ---")
    sim = load_eplus(ep_csv)
    ref = load_boptest(bt_csv)
    
    print(f"\n--- Data Summary ---")
    print(f"  EnergyPlus:  {len(sim)} hourly points")
    print(f"    Range: {sim.index.min()} -> {sim.index.max()}")
    print(f"    Mean={sim.mean():.2f}C  Min={sim.min():.2f}C  Max={sim.max():.2f}C")
    print(f"  BopTest:     {len(ref)} hourly points")
    print(f"    Range: {ref.index.min()} -> {ref.index.max()}")
    print(f"    Mean={ref.mean():.2f}C  Min={ref.min():.2f}C  Max={ref.max():.2f}C")
    
    combined = pd.DataFrame({"sim": sim, "ref": ref}).dropna()
    print(f"\n  Overlap: {len(combined)} hourly points")
    
    if len(combined) == 0:
        print("\n  WARNING: No overlapping data points available.")
        print("  The BopTest and EnergyPlus simulations cover different time ranges.")
        sys.exit(0)
    
    # --- Compute ASHRAE Guideline 14 metrics ---
    summary = validation_summary(combined["ref"].values, combined["sim"].values)
    
    cvrmse_status = "PASS" if summary["cvrmse_pass"] else "FAIL"
    nmbe_status = "PASS" if summary["nmbe_pass"] else "FAIL"
    overall_status = "PASS" if summary["overall_pass"] else "FAIL"
    
    print(f"\n--- ASHRAE Guideline 14 Results ---")
    print(f"  CVRMSE:   {summary['cvrmse_pct']:.2f}%  (threshold: {summary['cvrmse_threshold']}%)  {cvrmse_status}")
    print(f"  NMBE:     {summary['nmbe_pct']:.2f}%   (threshold: +/-{summary['nmbe_threshold']}%) {nmbe_status}")
    print(f"  Overall:  {overall_status}")
    
    if len(combined) < 10:
        print(f"\n  NOTE: Only {len(combined)} overlap points. Need more data for meaningful validation.")
    
    # --- Generate validation plot ---
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 7), gridspec_kw={"height_ratios": [3, 1]})
    
    ax1.plot(combined.index, combined["ref"], label="Reference (BopTest)", linewidth=1, color="#2563EB", alpha=0.8)
    ax1.plot(combined.index, combined["sim"], label="Simulation (Naive E+)", linewidth=1, color="#DC2626", alpha=0.8)
    ax1.set_ylabel("Zone Air Temperature (C)")
    ax1.set_title(
        f"Model Validation: Zone Air Temperature\n"
        f"CVRMSE={summary['cvrmse_pct']:.1f}%  |  NMBE={summary['nmbe_pct']:.1f}%  |  {overall_status}"
    )
    y_all = pd.concat([combined["ref"], combined["sim"]], axis=0)
    y_pad = max(0.2, 0.1 * max(float(y_all.max() - y_all.min()), 0.5))
    ax1.set_ylim(float(y_all.min()) - y_pad, float(y_all.max()) + y_pad)
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    residuals = combined["sim"] - combined["ref"]
    ax2.bar(combined.index, residuals, color="#6B7280", alpha=0.6, width=0.03)
    ax2.axhline(y=0, color="black", linewidth=0.5)
    ax2.set_ylabel("Residual (C)")
    ax2.set_xlabel("Time")
    ax2.grid(True, alpha=0.3)
    r_pad = max(0.1, 0.1 * max(float(residuals.max() - residuals.min()), 0.5))
    ax2.set_ylim(float(residuals.min()) - r_pad, float(residuals.max()) + r_pad)

    fig.suptitle(
        f"n={len(combined)} | Temp range={y_all.min():.2f}..{y_all.max():.2f} C | Residual range={residuals.min():.2f}..{residuals.max():.2f} C",
        fontsize=9,
        y=0.995,
    )
    
    fig.tight_layout()
    plot_path = PLOTS_DIR / "validation_zone_temp.png"
    fig.savefig(plot_path, dpi=150)
    plt.close(fig)
    print(f"\n  Plot saved -> {plot_path}")
    
    # --- Generate markdown report ---
    report = "\n".join([
        "# Model Validation Report",
        "",
        "Generated by `smoke_test.py`",
        "",
        "## ASHRAE Guideline 14 Metrics",
        "",
        "| Variable | CVRMSE (%) | NMBE (%) | Pass? |",
        "|----------|-----------|---------|-------|",
        f"| Zone Air Temperature | {summary['cvrmse_pct']:.1f} | {summary['nmbe_pct']:.1f} | {overall_status} |",
        "",
        f"## Overall Verdict: {overall_status}",
        "",
        f"- CVRMSE threshold: {summary['cvrmse_threshold']}%",
        f"- NMBE threshold: +/-{summary['nmbe_threshold']}%",
        f"- Overlapping data points: {len(combined)}",
        "",
    ])
    
    report_path = RESULTS_DIR / "validation_report.md"
    report_path.write_text(report, encoding="utf-8")
    print(f"  Report saved -> {report_path}")
    
    print("\n" + "=" * 60)
    print("  PIPELINE SMOKE TEST COMPLETED SUCCESSFULLY")
    print("=" * 60)


if __name__ == "__main__":
    main()
