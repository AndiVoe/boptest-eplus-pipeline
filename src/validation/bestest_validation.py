#!/usr/bin/env python3
"""Run the full validation: BESTEST E+ model vs 6-hour BopTest time-series."""
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


def load_boptest_timeseries(csv_path):
    """Load BopTest time-series CSV from extract_baseline_kpis."""
    bt = pd.read_csv(csv_path)
    tz_col = [c for c in bt.columns if "reaTRooAir" in c][0]
    bt["zone_temp_C"] = bt[tz_col] - 273.15
    bt["datetime"] = pd.to_datetime(bt["time"], unit="s", origin="2024-01-01")
    bt = bt.set_index("datetime")
    return bt


def load_eplus_bestest(csv_path):
    """Load E+ BESTEST output CSV."""
    ep = pd.read_csv(csv_path)
    ep.columns = ep.columns.str.strip()
    time_str = ep["Date/Time"].str.strip()
    is_24 = time_str.str.contains("24:00:00")
    time_str = time_str.str.replace("24:00:00", "00:00:00")
    dt = pd.to_datetime("2024/" + time_str, format="%Y/%m/%d  %H:%M:%S", errors="coerce")
    dt[is_24] += pd.Timedelta(days=1)
    ep["datetime"] = dt
    ep = ep.set_index("datetime")
    return ep


def main():
    PLOTS.mkdir(parents=True, exist_ok=True)

    # --- Load BopTest 6h reference ---
    bt = load_boptest_timeseries(RESULTS / "boptest_baseline_bestest_air.csv")
    print(f"BopTest: {len(bt)} rows, {bt.index.min()} -> {bt.index.max()}")
    bt_mean = bt["zone_temp_C"].mean()
    bt_min = bt["zone_temp_C"].min()
    bt_max = bt["zone_temp_C"].max()
    print(f"  Temp: mean={bt_mean:.2f}, min={bt_min:.2f}, max={bt_max:.2f}")

    # --- Load E+ BESTEST output ---
    ep = load_eplus_bestest(RESULTS / "bestest_out" / "eplusout.csv")
    temp_col = [c for c in ep.columns if "Zone Mean Air Temperature" in c][0]
    ep_temp = ep[temp_col].astype(float)
    print(f"E+: {len(ep)} rows, {ep.index.min()} -> {ep.index.max()}")
    print(f"  Temp: mean={ep_temp.mean():.2f}, min={ep_temp.min():.2f}, max={ep_temp.max():.2f}")

    # --- Resample to hourly and align ---
    ep_hourly = ep_temp.resample("1h").mean().dropna()
    bt_hourly = bt["zone_temp_C"].resample("1h").mean().dropna()

    combined = pd.DataFrame({"sim_ep": ep_hourly, "ref_bt": bt_hourly}).dropna()
    print(f"\nOverlap: {len(combined)} hourly points")
    print(combined.to_string())

    # --- ASHRAE Guideline 14 ---
    summary = validation_summary(combined["ref_bt"].values, combined["sim_ep"].values)
    cvrmse_status = "PASS" if summary["cvrmse_pass"] else "FAIL"
    nmbe_status = "PASS" if summary["nmbe_pass"] else "FAIL"
    overall = "PASS" if summary["overall_pass"] else "FAIL"

    print(f"\n{'='*50}")
    print(f"  ASHRAE Guideline 14 Results")
    print(f"{'='*50}")
    print(f"  CVRMSE: {summary['cvrmse_pct']:.2f}% (threshold: {summary['cvrmse_threshold']}%) {cvrmse_status}")
    print(f"  NMBE:   {summary['nmbe_pct']:.2f}% (threshold: +/-{summary['nmbe_threshold']}%) {nmbe_status}")
    print(f"  Overall: {overall}")
    print(f"{'='*50}")

    # --- Plot ---
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8), gridspec_kw={"height_ratios": [3, 1]})

    # Full overlap period: E+ sub-hourly + BT scatter
    overlap_end = combined.index.max() + pd.Timedelta(hours=1)
    ep_window = ep_temp[:overlap_end]
    bt_window = bt["zone_temp_C"][:overlap_end]

    ax1.plot(ep_window.index, ep_window, linewidth=1, color="#DC2626", label="E+ BESTEST Naive")
    ax1.scatter(bt_window.index, bt_window, color="#2563EB", s=40, zorder=5, label="BopTest Reference")
    ax1.axhline(y=21, color="green", linestyle="--", alpha=0.4, label="Heat SP (occ)")
    ax1.axhline(y=15, color="gray", linestyle="--", alpha=0.4, label="Heat SP (unocc)")
    ax1.set_ylabel("Zone Air Temperature (C)")
    cvrmse_str = f"{summary['cvrmse_pct']:.1f}%"
    nmbe_str = f"{summary['nmbe_pct']:.1f}%"
    ax1.set_title(f"BESTEST Validation: CVRMSE={cvrmse_str}  |  NMBE={nmbe_str}  |  {overall}  ({len(combined)} hourly points)")
    # Dynamic y-axis to avoid flattened traces.
    y_all = pd.concat([ep_window.astype(float), bt_window.astype(float)], axis=0).dropna()
    if len(y_all) > 0:
        y_lo, y_hi = float(y_all.min()), float(y_all.max())
        y_pad = max(0.2, 0.1 * max(y_hi - y_lo, 0.5))
        ax1.set_ylim(y_lo - y_pad, y_hi + y_pad)
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # Residual
    residuals = combined["sim_ep"] - combined["ref_bt"]
    colors = ["#DC2626" if r < 0 else "#2563EB" for r in residuals]
    ax2.bar(combined.index, residuals, width=0.03, color=colors, alpha=0.7)
    ax2.axhline(y=0, color="black", linewidth=0.5)
    ax2.set_ylabel("Residual (C)")
    ax2.set_xlabel("Time")
    ax2.grid(True, alpha=0.3)
    if len(residuals) > 0:
        r_lo, r_hi = float(residuals.min()), float(residuals.max())
        r_pad = max(0.1, 0.1 * max(r_hi - r_lo, 0.5))
        ax2.set_ylim(r_lo - r_pad, r_hi + r_pad)

    fig.suptitle(
        f"Temp range={y_all.min():.2f}..{y_all.max():.2f} C | Residual range={residuals.min():.2f}..{residuals.max():.2f} C",
        fontsize=9,
        y=0.995,
    )

    fig.tight_layout()
    fig.savefig(PLOTS / "bestest_validation_6h.png", dpi=150)
    plt.close(fig)
    print(f"\nPlot saved -> plots/bestest_validation_6h.png")

    # --- Report ---
    ep_min = ep_temp.min()
    ep_max = ep_temp.max()
    report_lines = [
        "# BESTEST Validation Report (6-Hour BopTest Reference)",
        "",
        "## Data Summary",
        "",
        "| Dataset | Points | Period | Temp Range |",
        "|---------|--------|--------|------------|",
        f"| E+ BESTEST | {len(ep)} | Jan-Mar 2024 | {ep_min:.1f} - {ep_max:.1f} C |",
        f"| BopTest | {len(bt)} | {bt.index.min().strftime('%H:%M')}-{bt.index.max().strftime('%H:%M')} Jan 1 | {bt_min:.1f} - {bt_max:.1f} C |",
        f"| Overlap | {len(combined)} hourly pts | - | - |",
        "",
        "## ASHRAE Guideline 14 Metrics",
        "",
        "| Metric | Value | Threshold | Status |",
        "|--------|-------|-----------|--------|",
        f"| CVRMSE | {summary['cvrmse_pct']:.1f}% | <=30% | {cvrmse_status} |",
        f"| NMBE | {summary['nmbe_pct']:.1f}% | +/-10% | {nmbe_status} |",
        "",
        f"## Overall: {overall}",
    ]
    report = "\n".join(report_lines) + "\n"
    report_path = RESULTS / "bestest_validation_report.md"
    report_path.write_text(report, encoding="utf-8")
    print(f"Report saved -> {report_path}")


if __name__ == "__main__":
    main()
