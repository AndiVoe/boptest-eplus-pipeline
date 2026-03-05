"""
Baseline KPI Extraction — Micro-Step 2 Deliverable
====================================================
Runs the BopTest built-in baseline controller for a full simulation period
on one or more test cases, extracts KPIs, and saves comparison outputs.

Usage:
  python src/boptest/extract_baseline_kpis.py
  python src/boptest/extract_baseline_kpis.py --url http://localhost:5050
  python src/boptest/extract_baseline_kpis.py --hours 8760
"""

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.boptest.client import BopTestClient


# ======================================================================
# Configuration
# ======================================================================
DEFAULT_URL = "http://localhost:5000"

# Test cases to benchmark
TEST_CASES = [
    "bestest_air",
    "bestest_hydronic_heat_pump",
]

# Step size (seconds) — using 900 s (15 min) for practical speed
STEP_SIZE = 900

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = PROJECT_ROOT / "data" / "results"
PLOTS_DIR = PROJECT_ROOT / "plots"


def run_baseline(
    client: BopTestClient,
    n_hours: int = 24 * 7,
) -> tuple:
    """
    Run baseline controller (empty control inputs = built-in PID) for
    *n_hours* hours and return (kpi_row, timeseries_df).
    """
    client.initialize(start_time=0, warmup_period=0)
    client.set_step(STEP_SIZE)

    n_steps = int(n_hours * 3600 / STEP_SIZE)
    print(f"  Running baseline for {n_hours} h ({n_steps} steps) ...")

    ts_records = []
    for i in range(n_steps):
        # Empty dict → BopTest uses its own baseline controller
        payload = client.advance({})
        ts_records.append(payload)

        if (i + 1) % max(1, n_steps // 10) == 0:
            pct = 100 * (i + 1) / n_steps
            print(f"    ... {pct:.0f}%")

    # Build time-series DataFrame from advance() payloads
    ts_df = pd.DataFrame(ts_records)

    return client.get_kpis(), ts_df


def run_all_test_cases(
    url: str,
    test_cases: list[str],
    n_hours: int,
) -> pd.DataFrame:
    """Run baseline on each test case and return a combined KPI DataFrame."""
    all_kpis = []
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    for tc in test_cases:
        print(f"\n{'='*60}")
        print(f"  Test case: {tc}")
        print(f"{'='*60}")
        client = BopTestClient(url=url)
        client.select_test_case(tc, async_select=True)
        print(f"[extract_baseline_kpis] Waiting for test case to compile/initialize (up to 1 hour)...")
        client.wait_for_status("Running", timeout=3600)
        kpi_row, ts_df = run_baseline(client, n_hours=n_hours)

        # Save time-series for downstream validation
        ts_path = RESULTS_DIR / f"boptest_baseline_{tc}.csv"
        ts_df.to_csv(ts_path, index=False)
        print(f"  [extract_baseline_kpis] Time-series saved -> {ts_path} ({len(ts_df)} rows)")

        kpi_row.insert(0, "test_case", tc)
        all_kpis.append(kpi_row)

    return pd.concat(all_kpis, ignore_index=True)


def save_and_plot(df: pd.DataFrame):
    """Save KPI table to CSV and create a grouped bar chart."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)

    csv_path = RESULTS_DIR / "baseline_kpis.csv"
    df.to_csv(csv_path, index=False)
    print(f"\n[extract_baseline_kpis] CSV saved → {csv_path}")

    # --- Grouped bar chart ---
    kpi_cols = [c for c in df.columns if c != "test_case"]
    # Drop columns that are all NaN
    kpi_cols = [c for c in kpi_cols if df[c].notna().any()]

    if not kpi_cols:
        print("[extract_baseline_kpis] No valid KPIs to plot.")
        return

    x = np.arange(len(kpi_cols))
    width = 0.8 / len(df)

    fig, ax = plt.subplots(figsize=(12, 5))
    for i, (_, row) in enumerate(df.iterrows()):
        vals = [row[c] if pd.notna(row[c]) else 0 for c in kpi_cols]
        offset = (i - len(df) / 2 + 0.5) * width
        ax.bar(x + offset, vals, width, label=row["test_case"])

    ax.set_xticks(x)
    ax.set_xticklabels(kpi_cols, rotation=30, ha="right")
    ax.set_ylabel("KPI Value")
    ax.set_title("BopTest Baseline KPI Comparison")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()

    plot_path = PLOTS_DIR / "baseline_comparison.png"
    fig.savefig(plot_path, dpi=150)
    plt.close(fig)
    print(f"[extract_baseline_kpis] Plot saved → {plot_path}")


# ======================================================================
# Main
# ======================================================================
def main():
    parser = argparse.ArgumentParser(
        description="Extract baseline KPIs from BopTest test cases"
    )
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument(
        "--hours",
        type=int,
        default=24 * 7,
        help="Simulation hours per test case (default: 168 = 1 week)",
    )
    args = parser.parse_args()

    df = run_all_test_cases(args.url, TEST_CASES, args.hours)

    print("\n[extract_baseline_kpis] Combined KPIs:")
    print(df.to_string(index=False))

    save_and_plot(df)
    print("\n✅ extract_baseline_kpis.py completed successfully!")


if __name__ == "__main__":
    main()
