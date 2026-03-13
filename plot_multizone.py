import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Load data
df = pd.read_csv('data/results/mpc_results_multizone_office_simple_air.csv')
# Convert time to hours relative to start
df['hour'] = (df['time'] - df['time'].iloc[0]) / 3600
df['temp_c'] = df['temp_avg'] - 273.15
df['p_total_kw'] = df['p_total'] / 1000.0

# Smoothed overlays while preserving raw traces.
window = max(3, min(8, len(df) // 10))
df['temp_c_smooth'] = df['temp_c'].rolling(window=window, center=True, min_periods=1).mean()
df['p_total_kw_smooth'] = df['p_total_kw'].rolling(window=window, center=True, min_periods=1).mean()


def _pad_limits(series, frac=0.1, min_pad=0.05):
	lo = float(series.min())
	hi = float(series.max())
	span = max(hi - lo, min_pad)
	pad = max(span * frac, min_pad)
	return lo - pad, hi + pad

# Plotting configuration
fig, ax1 = plt.subplots(figsize=(12, 6))

# Comfort Zone and Temperature
ax1.fill_between(df['hour'], 21, 24, color='green', alpha=0.1, label='Comfort Zone (21-24°C)')
ax1.plot(df['hour'], df['temp_c'], label='Avg Zone Temp (raw)', color='black', linewidth=1.0, alpha=0.35)
ax1.plot(df['hour'], df['temp_c_smooth'], label='Avg Zone Temp (smoothed)', color='black', linewidth=2)
ax1.axhline(24, color='red', linestyle='--', alpha=0.5, label='Cooling Limit (24°C)')
ax1.axhline(21, color='blue', linestyle='--', alpha=0.5, label='Heating Limit (21°C)')

ax1.set_xlabel('Hours')
ax1.set_ylabel('Temperature (°C)', color='black')
ax1.set_title('Multi-zone Office MPC Benchmark (Chicago - 48h)')
ax1.set_ylim(*_pad_limits(df['temp_c']))
ax1.legend(loc='upper left')
ax1.grid(True, alpha=0.3)

# Power on secondary axis
ax2 = ax1.twinx()
# Heating power is positive, Cooling power is negative
ax2.fill_between(df['hour'], df['p_total_kw'], 0, where=(df['p_total_kw'] >= 0), color='salmon', alpha=0.25, label='Heating Power (raw)')
ax2.fill_between(df['hour'], df['p_total_kw'], 0, where=(df['p_total_kw'] < 0), color='lightblue', alpha=0.25, label='Cooling Power (raw)')
ax2.plot(df['hour'], df['p_total_kw'], color='gray', linewidth=1, alpha=0.35)
ax2.plot(df['hour'], df['p_total_kw_smooth'], color='dimgray', linewidth=2.0, label='Total HVAC Power (smoothed)')

ax2.set_ylabel('Total HVAC Power (kW)', color='gray')
ax2.tick_params(axis='y', labelcolor='gray')
ax2.set_ylim(*_pad_limits(df['p_total_kw']))

# Align zero for power if needed, or just let it float
ax2.axhline(0, color='black', linewidth=0.5, alpha=0.5)

stats = (
	f"n={len(df)} | Temp range={df['temp_c'].min():.2f}..{df['temp_c'].max():.2f} °C | "
	f"Power range={df['p_total_kw'].min():.3f}..{df['p_total_kw'].max():.3f} kW"
)
fig.suptitle(stats, fontsize=9, y=0.995)

fig.tight_layout()
plt.savefig('plots/multizone_office_bench_48h.png', dpi=300)
print("Optimized plot saved as multizone_office_bench_48h.png")
