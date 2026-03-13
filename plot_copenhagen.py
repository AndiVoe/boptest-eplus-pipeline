import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Load results
df = pd.read_csv('data/results/mpc_results_singlezone_commercial_hydronic.csv')
df['time_hours'] = df['time'] / 3600
df['temp_c'] = df['temp'] - 273.15
df['p_opt_kw'] = df['p_opt'] / 1000.0

# Smoothed overlays while preserving raw traces.
window = max(3, min(8, len(df) // 20))
df['temp_c_smooth'] = df['temp_c'].rolling(window=window, center=True, min_periods=1).mean()
df['p_opt_kw_smooth'] = df['p_opt_kw'].rolling(window=window, center=True, min_periods=1).mean()


def _pad_limits(series, frac=0.1, min_pad=0.05):
	lo = float(series.min())
	hi = float(series.max())
	span = max(hi - lo, min_pad)
	pad = max(span * frac, min_pad)
	return lo - pad, hi + pad

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)

# Temperature Plot
ax1.plot(df['time_hours'], df['temp_c'], label='Zone Temp (raw)', color='blue', linewidth=1.0, alpha=0.35)
ax1.plot(df['time_hours'], df['temp_c_smooth'], label='Zone Temp (smoothed)', color='blue', linewidth=2.0)
ax1.axhline(24, color='red', linestyle='--', alpha=0.5, label='Cooling Limit (24°C)')
ax1.axhline(21, color='blue', linestyle='--', alpha=0.5, label='Heating Limit (21°C)')
ax1.set_ylabel('Temperature (°C)')
ax1.set_title('Copenhagen (singlezone_commercial_hydronic) - MPC Benchmark')
ax1.legend()
ax1.grid(True, alpha=0.3)
ax1.set_ylim(*_pad_limits(df['temp_c']))

# Power Plot
ax2.fill_between(df['time_hours'], df['p_opt_kw'], color='orange', alpha=0.2, label='MPC Power (raw)')
ax2.plot(df['time_hours'], df['p_opt_kw'], color='orange', linewidth=1.0, alpha=0.35)
ax2.plot(df['time_hours'], df['p_opt_kw_smooth'], color='darkorange', linewidth=2.0, label='MPC Power (smoothed)')
ax2.set_ylabel('Optimized Power (kW)')
ax2.set_xlabel('Time (Hours)')
ax2.legend()
ax2.grid(True, alpha=0.3)
ax2.set_ylim(*_pad_limits(df['p_opt_kw']))

stats = (
	f"n={len(df)} | Temp range={df['temp_c'].min():.2f}..{df['temp_c'].max():.2f} °C | "
	f"Power range={df['p_opt_kw'].min():.3f}..{df['p_opt_kw'].max():.3f} kW"
)
fig.suptitle(stats, fontsize=9, y=0.995)

plt.tight_layout()
plt.savefig('plots/copenhagen_bench_48h.png')
print("Plot saved as copenhagen_bench_48h.png")
