"""
Model Validation — Micro-Step 5 Deliverable
=============================================
Compares EnergyPlus simulation output against reference data (e.g., BAS
measurements or BopTest baseline) using ASHRAE Guideline 14 metrics.

Workflow:
  1. Load simulation CSV (eplusout.csv or custom output)
  2. Load reference CSV (BAS measurements or BopTest results)
  3. Align timestamps and resample to hourly
  4. Compute CVRMSE and NMBE per variable
  5. Generate overlay plots and validation report

Usage:
  python src/validation/validate_model.py \\
      --sim-csv data/results/eplusout.csv \\
      --ref-csv data/results/boptest_hello.csv \\
      --sim-col "Room_206 IDEAL LOADS AIR SYSTEM:Zone Ideal Loads Zone Total Heating Energy [J](TimeStep)" \\
      --ref-col "zone_temp_C"
"""

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.validation.metrics import cvrmse, nmbe, validation_summary


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = PROJECT_ROOT / "data" / "results"
PLOTS_DIR = PROJECT_ROOT / "plots"


def load_and_resample(
    csv_path: str,
    value_col: str,
    time_col: str = None,
    resample_freq: str = "1h",
) -> pd.Series:
    """
    Load a CSV, identify the time column, and resample to hourly.

    Handles both EnergyPlus output format (Date/Time column) and
    generic CSV with numeric time columns.
    """
    df = pd.read_csv(csv_path)
    # Strip whitespace from column names (EnergyPlus adds trailing spaces)
    df.columns = df.columns.str.strip()
    value_col = value_col.strip()

    # Try to find a time column
    if time_col and time_col in df.columns:
        df["_time"] = pd.to_datetime(df[time_col])
    elif "Date/Time" in df.columns:
        # EnergyPlus format: " 01/02  01:00:00" or " 01/02  24:00:00"
        time_str = df["Date/Time"].str.strip()
        is_24 = time_str.str.contains("24:00:00")
        time_str = time_str.str.replace("24:00:00", "00:00:00")
        
        # Add year 2024 since EnergyPlus format from our template has no year by default
        dt = pd.to_datetime("2024/" + time_str, format="%Y/%m/%d  %H:%M:%S", errors="coerce")
        # Add 1 day where we replaced 24:00:00
        dt[is_24] += pd.Timedelta(days=1)
        df["_time"] = dt
    elif "time_h" in df.columns:
        # Our boptest output format
        df["_time"] = pd.to_timedelta(df["time_h"], unit="h") + pd.Timestamp("2024-01-01")
    elif "time_s" in df.columns:
        df["_time"] = pd.to_timedelta(df["time_s"], unit="s") + pd.Timestamp("2024-01-01")
    else:
        raise ValueError(
            f"Cannot identify time column in {csv_path}. "
            f"Columns: {list(df.columns)}"
        )

    df = df.set_index("_time")

    if value_col not in df.columns:
        # Try fuzzy match
        matches = [c for c in df.columns if value_col.lower() in c.lower()]
        if matches:
            value_col = matches[0]
            print(f"  [validate] Fuzzy-matched column: '{value_col}'")
        else:
            raise ValueError(
                f"Column '{value_col}' not found in {csv_path}. "
                f"Available: {list(df.columns)}"
            )

    series = df[value_col].astype(float)
    resampled = series.resample(resample_freq).mean().dropna()
    return resampled


def compare_and_plot(
    sim_series: pd.Series,
    ref_series: pd.Series,
    label: str = "variable",
    output_dir: Path = PLOTS_DIR,
) -> dict:
    """
    Align two time series, compute metrics, and create overlay plot.

    Returns validation summary dict.
    """
    # Align on shared time index
    combined = pd.DataFrame({"sim": sim_series, "ref": ref_series}).dropna()

    if len(combined) == 0:
        print(f"  [validate] WARNING: No overlapping timestamps for '{label}'")
        return {"error": "no_overlap"}

    print(f"  [validate] {len(combined)} overlapping hourly points")

    # Compute metrics
    summary = validation_summary(
        combined["ref"].values, combined["sim"].values
    )

    # Print results
    status = "✅ PASS" if summary["overall_pass"] else "❌ FAIL"
    print(f"\n  {status}  CVRMSE = {summary['cvrmse_pct']:.1f}% "
          f"(threshold: {summary['cvrmse_threshold']}%)")
    print(f"         NMBE   = {summary['nmbe_pct']:.1f}% "
          f"(threshold: ±{summary['nmbe_threshold']}%)")

    # --- Overlay plot ---
    output_dir.mkdir(parents=True, exist_ok=True)
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 7), height_ratios=[3, 1])

    ax1.plot(combined.index, combined["ref"], label="Reference",
             linewidth=1, color="#2563EB", alpha=0.8)
    ax1.plot(combined.index, combined["sim"], label="Simulation",
             linewidth=1, color="#DC2626", alpha=0.8)
    ax1.set_ylabel(label)
    ax1.set_title(
        f"Model Validation: {label}\n"
        f"CVRMSE={summary['cvrmse_pct']:.1f}%  |  "
        f"NMBE={summary['nmbe_pct']:.1f}%  |  {status}"
    )
    y_all = pd.concat([combined["ref"], combined["sim"]], axis=0)
    y_pad = max(0.2, 0.1 * max(float(y_all.max() - y_all.min()), 0.5))
    ax1.set_ylim(float(y_all.min()) - y_pad, float(y_all.max()) + y_pad)
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # Residuals
    residuals = combined["sim"] - combined["ref"]
    ax2.bar(combined.index, residuals, color="#6B7280", alpha=0.6, width=0.03)
    ax2.axhline(y=0, color="black", linewidth=0.5)
    ax2.set_ylabel("Residual")
    ax2.set_xlabel("Time")
    ax2.grid(True, alpha=0.3)
    r_pad = max(0.1, 0.1 * max(float(residuals.max() - residuals.min()), 0.5))
    ax2.set_ylim(float(residuals.min()) - r_pad, float(residuals.max()) + r_pad)

    fig.suptitle(
        f"n={len(combined)} | Value range={y_all.min():.2f}..{y_all.max():.2f} | Residual range={residuals.min():.2f}..{residuals.max():.2f}",
        fontsize=9,
        y=0.995,
    )

    fig.tight_layout()
    safe_label = label.replace(" ", "_").replace("/", "_")[:30]
    plot_path = output_dir / f"validation_{safe_label}.png"
    fig.savefig(plot_path, dpi=150)
    plt.close(fig)
    print(f"  [validate] Plot saved → {plot_path}")

    summary["plot_path"] = str(plot_path)
    return summary


def generate_report(results: list[dict], output_path: Path):
    """Write a markdown validation report."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines = ["# Model Validation Report\n"]
    lines.append(f"Generated by `validate_model.py`\n")
    lines.append("## ASHRAE Guideline 14 Metrics\n")
    lines.append("| Variable | CVRMSE (%) | NMBE (%) | Pass? |")
    lines.append("|----------|-----------|---------|-------|")

    all_pass = True
    for r in results:
        if "error" in r:
            lines.append(f"| {r.get('label', '?')} | — | — | ⚠️ {r['error']} |")
            all_pass = False
        else:
            status = "✅" if r["overall_pass"] else "❌"
            if not r["overall_pass"]:
                all_pass = False
            lines.append(
                f"| {r.get('label', '?')} | {r['cvrmse_pct']:.1f} | "
                f"{r['nmbe_pct']:.1f} | {status} |"
            )

    lines.append(f"\n## Overall Verdict: {'✅ PASS' if all_pass else '❌ FAIL'}\n")
    lines.append(f"- CVRMSE threshold: {results[0].get('cvrmse_threshold', 30)}%")
    lines.append(f"- NMBE threshold: ±{results[0].get('nmbe_threshold', 10)}%")

    report = "\n".join(lines)
    output_path.write_text(report, encoding="utf-8")
    print(f"\n[validate_model] Report saved → {output_path}")


# ======================================================================
# Main
# ======================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Validate EnergyPlus model against reference data"
    )
    parser.add_argument("--sim-csv", required=True, help="Simulation output CSV")
    parser.add_argument("--ref-csv", required=True, help="Reference data CSV")
    parser.add_argument("--sim-col", required=True, help="Column name in sim CSV")
    parser.add_argument("--ref-col", required=True, help="Column name in ref CSV")
    parser.add_argument("--sim-time-col", default=None, help="Time column in sim CSV")
    parser.add_argument("--ref-time-col", default=None, help="Time column in ref CSV")
    parser.add_argument("--label", default="Temperature", help="Variable label for report")
    args = parser.parse_args()

    print(f"[validate_model] Simulation: {args.sim_csv}")
    print(f"[validate_model] Reference:  {args.ref_csv}")

    sim = load_and_resample(args.sim_csv, args.sim_col, args.sim_time_col)
    ref = load_and_resample(args.ref_csv, args.ref_col, args.ref_time_col)

    result = compare_and_plot(sim, ref, label=args.label)
    result["label"] = args.label

    generate_report([result], RESULTS_DIR / "validation_report.md")
    print("\n✅ validate_model.py completed successfully!")


if __name__ == "__main__":
    main()
