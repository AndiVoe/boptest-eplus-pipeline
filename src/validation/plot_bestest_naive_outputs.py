"""
Regenerate BESTEST naive baseline plots from EnergyPlus output CSV.

Creates:
  - plots/bestest_naive_48h.png
  - plots/bestest_naive_full.png
"""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
INPUT_CSV = PROJECT_ROOT / "data" / "results" / "bestest_out" / "eplusout.csv"
PLOTS_DIR = PROJECT_ROOT / "plots"

TEMP_COL = "BESTEST_ZONE:Zone Mean Air Temperature [C](TimeStep)"
HEAT_COL = "BESTEST_IDEALLOADS:Zone Ideal Loads Zone Total Heating Energy [J](TimeStep)"


def _parse_eplus_datetime(date_time: pd.Series) -> pd.Series:
    """Parse EnergyPlus Date/Time strings and handle 24:00 rollover."""
    s = date_time.astype(str).str.strip()
    is_24 = s.str.contains("24:00:00", regex=False)
    s = s.str.replace("24:00:00", "00:00:00", regex=False)
    dt = pd.to_datetime("2024/" + s, format="%Y/%m/%d  %H:%M:%S", errors="coerce")
    dt.loc[is_24] = dt.loc[is_24] + pd.Timedelta(days=1)
    return dt


def _rolling(series: pd.Series, frac: float) -> pd.Series:
    window = max(5, min(96, int(len(series) * frac)))
    return series.rolling(window=window, center=True, min_periods=1).mean()


def _dynamic_ylim(series: pd.Series, min_pad: float = 0.2) -> tuple[float, float]:
    lo = float(series.min())
    hi = float(series.max())
    pad = max(min_pad, 0.1 * max(hi - lo, 0.5))
    return lo - pad, hi + pad


def main() -> None:
    if not INPUT_CSV.exists():
        raise FileNotFoundError(f"Missing input CSV: {INPUT_CSV}")

    PLOTS_DIR.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(INPUT_CSV)
    df.columns = df.columns.str.strip()
    required = ["Date/Time", TEMP_COL, HEAT_COL]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    ts = _parse_eplus_datetime(df["Date/Time"])
    temp_c = pd.to_numeric(df[TEMP_COL], errors="coerce")
    heat_kw = pd.to_numeric(df[HEAT_COL], errors="coerce") / 900.0 / 1000.0

    out = pd.DataFrame({"t": ts, "temp_c": temp_c, "heat_kw": heat_kw}).dropna()

    if out.empty:
        raise RuntimeError("No valid rows after parsing BESTEST output")

    # 48h view
    first_t = out["t"].min()
    t48 = first_t + pd.Timedelta(hours=48)
    out48 = out.loc[out["t"] < t48].copy()
    out48["temp_smooth"] = _rolling(out48["temp_c"], frac=0.08)
    out48["heat_smooth"] = _rolling(out48["heat_kw"], frac=0.08)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 7), sharex=True)
    ax1.plot(out48["t"], out48["temp_c"], color="#2563EB", alpha=0.35, linewidth=1.0, label="Zone Temp (raw)")
    ax1.plot(out48["t"], out48["temp_smooth"], color="#1D4ED8", linewidth=2.0, label="Zone Temp (smoothed)")
    ax1.set_ylabel("Temperature (C)")
    ax1.set_title("BESTEST Naive Baseline - First 48 Hours")
    ax1.set_ylim(*_dynamic_ylim(out48["temp_c"], min_pad=0.3))
    ax1.grid(True, alpha=0.3)
    ax1.legend()

    ax2.plot(out48["t"], out48["heat_kw"], color="#DC2626", alpha=0.35, linewidth=1.0, label="Heating Power (raw)")
    ax2.plot(out48["t"], out48["heat_smooth"], color="#B91C1C", linewidth=2.0, label="Heating Power (smoothed)")
    ax2.set_ylabel("Heating (kW)")
    ax2.set_xlabel("Time")
    ax2.set_ylim(*_dynamic_ylim(out48["heat_kw"], min_pad=0.05))
    ax2.grid(True, alpha=0.3)
    ax2.legend()

    fig.suptitle(
        f"n={len(out48)} | Temp range={out48['temp_c'].min():.2f}..{out48['temp_c'].max():.2f} C | "
        f"Heat range={out48['heat_kw'].min():.2f}..{out48['heat_kw'].max():.2f} kW",
        fontsize=9,
        y=0.995,
    )
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "bestest_naive_48h.png", dpi=150)
    plt.close(fig)

    # Full horizon view
    out["temp_smooth"] = _rolling(out["temp_c"], frac=0.02)
    out["heat_smooth"] = _rolling(out["heat_kw"], frac=0.02)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8), sharex=True)
    ax1.plot(out["t"], out["temp_c"], color="#2563EB", alpha=0.25, linewidth=0.8, label="Zone Temp (raw)")
    ax1.plot(out["t"], out["temp_smooth"], color="#1D4ED8", linewidth=1.8, label="Zone Temp (smoothed)")
    ax1.set_ylabel("Temperature (C)")
    ax1.set_title("BESTEST Naive Baseline - Full Simulation")
    ax1.set_ylim(*_dynamic_ylim(out["temp_c"], min_pad=0.3))
    ax1.grid(True, alpha=0.25)
    ax1.legend()

    ax2.plot(out["t"], out["heat_kw"], color="#DC2626", alpha=0.25, linewidth=0.8, label="Heating Power (raw)")
    ax2.plot(out["t"], out["heat_smooth"], color="#B91C1C", linewidth=1.8, label="Heating Power (smoothed)")
    ax2.set_ylabel("Heating (kW)")
    ax2.set_xlabel("Time")
    ax2.set_ylim(*_dynamic_ylim(out["heat_kw"], min_pad=0.05))
    ax2.grid(True, alpha=0.25)
    ax2.legend()

    fig.suptitle(
        f"n={len(out)} | Temp range={out['temp_c'].min():.2f}..{out['temp_c'].max():.2f} C | "
        f"Heat range={out['heat_kw'].min():.2f}..{out['heat_kw'].max():.2f} kW",
        fontsize=9,
        y=0.995,
    )
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "bestest_naive_full.png", dpi=150)
    plt.close(fig)

    print(f"Saved {PLOTS_DIR / 'bestest_naive_48h.png'}")
    print(f"Saved {PLOTS_DIR / 'bestest_naive_full.png'}")


if __name__ == "__main__":
    main()
