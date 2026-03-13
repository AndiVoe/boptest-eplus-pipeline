"""
BopTest Hello World — Micro-Step 1 Deliverable
================================================
Proves end-to-end connectivity with the BopTest REST API:
  1. Connects to BopTest running in Docker
  2. Initializes the 'bestest_air' test case
  3. Runs a 24-hour simulation with a constant heating setpoint of 293.15 K
  4. Retrieves zone temperature results
  5. Plots the zone temperature over time and saves the figure

Prerequisites:
  - Docker running with BopTest: `docker compose up -d`
  - Python deps installed: `pip install -r requirements.txt`

Usage:
  python src/boptest/boptest_hello.py
  python src/boptest/boptest_hello.py --url http://localhost:5050
  python src/boptest/boptest_hello.py --hours 48
"""

import argparse
import sys
import os
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

# Add project root to path so we can import sibling modules
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.boptest.client import BopTestClient


# ======================================================================
# Configuration
# ======================================================================
DEFAULT_URL = "http://localhost:5000"
TEST_CASE = "bestest_air"

# Constant heating setpoint (Kelvin).  20 °C = 293.15 K
HEATING_SETPOINT_K = 293.15

# Simulation step size in seconds (15 min = 900 s)
STEP_SIZE = 900

# Output paths (relative to project root)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = PROJECT_ROOT / "data" / "results"
PLOTS_DIR = PROJECT_ROOT / "plots"


def run_simulation(client: BopTestClient, n_hours: int = 24) -> pd.DataFrame:
    """
    Run a constant-setpoint simulation for *n_hours* hours.

    Returns a DataFrame with columns: time (s), zone_temp (K).
    """
    # Initialize from t=0 with no warm-up
    client.initialize(start_time=0, warmup_period=0)
    client.set_step(STEP_SIZE)

    n_steps = int(n_hours * 3600 / STEP_SIZE)
    records = []

    print(f"[boptest_hello] Simulating {n_hours} h  ({n_steps} steps × {STEP_SIZE} s) ...")

    for i in range(n_steps):
        # Advance with constant setpoint
        y = client.advance({
            "con_oveTSetHea_u": HEATING_SETPOINT_K,
            "con_oveTSetHea_activate": 1,
        })
        records.append({
            "time_s": y.get("time", i * STEP_SIZE),
            "zone_temp_K": y.get("zon_reaTRooAir_y", float("nan")),
        })

        # Progress indicator every 25 %
        if (i + 1) % max(1, n_steps // 4) == 0:
            pct = 100 * (i + 1) / n_steps
            print(f"  ... {pct:.0f}% done")

    df = pd.DataFrame(records)
    df["time_h"] = df["time_s"] / 3600
    df["zone_temp_C"] = df["zone_temp_K"] - 273.15
    return df


def save_results(df: pd.DataFrame, tag: str = "hello") -> Path:
    """Save raw results to CSV and return the file path."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out = RESULTS_DIR / f"boptest_{tag}.csv"
    df.to_csv(out, index=False)
    print(f"[boptest_hello] Results saved → {out}")
    return out


def plot_zone_temperature(df: pd.DataFrame, tag: str = "hello") -> Path:
    """Create a zone temperature plot and save as PNG."""
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    out = PLOTS_DIR / f"boptest_{tag}_zone_temp.png"

    fig, ax = plt.subplots(figsize=(10, 4))
    # Raw + smoothed overlay for better readability while preserving fidelity.
    window = max(3, min(8, len(df) // 10))
    smooth = df["zone_temp_C"].rolling(window=window, center=True, min_periods=1).mean()
    ax.plot(df["time_h"], df["zone_temp_C"], linewidth=1.0, alpha=0.35, color="#2563EB", label="Zone Temp (raw)")
    ax.plot(df["time_h"], smooth, linewidth=2.0, color="#1D4ED8", label="Zone Temp (smoothed)")
    ax.axhline(
        y=HEATING_SETPOINT_K - 273.15,
        color="#DC2626",
        linestyle="--",
        linewidth=0.8,
        label=f"Setpoint ({HEATING_SETPOINT_K - 273.15:.1f} °C)",
    )
    ax.set_xlabel("Time (h)")
    ax.set_ylabel("Zone Temperature (°C)")
    ax.set_title(f"BopTest '{TEST_CASE}' — Constant Setpoint Simulation")
    t_lo = float(df["zone_temp_C"].min())
    t_hi = float(df["zone_temp_C"].max())
    pad = max(0.2, 0.1 * max(t_hi - t_lo, 0.5))
    ax.set_ylim(t_lo - pad, t_hi + pad)
    fig.suptitle(f"n={len(df)} | Temp range={t_lo:.2f}..{t_hi:.2f} C", fontsize=9, y=0.995)
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)

    print(f"[boptest_hello] Plot saved  → {out}")
    return out


# ======================================================================
# Main
# ======================================================================
def main():
    parser = argparse.ArgumentParser(
        description="BopTest Hello World — 24 h constant-setpoint simulation"
    )
    parser.add_argument(
        "--url",
        default=DEFAULT_URL,
        help=f"BopTest API base URL (default: {DEFAULT_URL})",
    )
    parser.add_argument(
        "--hours",
        type=int,
        default=24,
        help="Number of hours to simulate (default: 24)",
    )
    parser.add_argument(
        "--startup-timeout-s",
        type=int,
        default=900,
        help="Max seconds to wait for BOPTEST testcase startup (default: 900)",
    )
    args = parser.parse_args()

    # 1. Connect
    print(f"[boptest_hello] Connecting to BopTest at {args.url} ...")
    client = BopTestClient(url=args.url)
    client.select_test_case(TEST_CASE, async_select=True)
    client.wait_for_status("Running", timeout=args.startup_timeout_s)

    # 2. Check available inputs / measurements
    inputs = client.get_inputs()
    measurements = client.get_measurements()
    print(f"[boptest_hello] Inputs:       {list(inputs.keys())}")
    print(f"[boptest_hello] Measurements: {list(measurements.keys())}")

    # 3. Run simulation
    df = run_simulation(client, n_hours=args.hours)

    # 4. Save outputs
    save_results(df)
    plot_zone_temperature(df)

    # 5. Retrieve KPIs
    kpis = client.get_kpis()
    print("\n[boptest_hello] KPIs:")
    print(kpis.to_string(index=False))

    print("\n✅ boptest_hello.py completed successfully!")


if __name__ == "__main__":
    main()
