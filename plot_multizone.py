import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Load data
df = pd.read_csv('data/results/mpc_results_multizone_office_simple_air.csv')
# Convert time to hours relative to start
df['hour'] = (df['time'] - df['time'].iloc[0]) / 3600
df['temp_c'] = df['temp_avg'] - 273.15

# Plotting configuration
fig, ax1 = plt.subplots(figsize=(12, 6))

# Comfort Zone and Temperature
ax1.fill_between(df['hour'], 21, 24, color='green', alpha=0.1, label='Comfort Zone (21-24°C)')
ax1.plot(df['hour'], df['temp_c'], label='Avg Zone Temp', color='black', linewidth=2)
ax1.axhline(24, color='red', linestyle='--', alpha=0.5, label='Cooling Limit (24°C)')
ax1.axhline(21, color='blue', linestyle='--', alpha=0.5, label='Heating Limit (21°C)')

ax1.set_xlabel('Hours')
ax1.set_ylabel('Temperature (°C)', color='black')
ax1.set_title('Multi-zone Office MPC Benchmark (Chicago - 48h)')
ax1.set_ylim(20, 26)
ax1.legend(loc='upper left')
ax1.grid(True, alpha=0.3)

# Power on secondary axis
ax2 = ax1.twinx()
# Heating power is positive, Cooling power is negative
ax2.fill_between(df['hour'], df['p_total'], 0, where=(df['p_total'] >= 0), color='salmon', alpha=0.3, label='Heating Power')
ax2.fill_between(df['hour'], df['p_total'], 0, where=(df['p_total'] < 0), color='lightblue', alpha=0.3, label='Cooling Power')
ax2.plot(df['hour'], df['p_total'], color='gray', linewidth=1, alpha=0.5)

ax2.set_ylabel('Total HVAC Power (W)', color='gray')
ax2.tick_params(axis='y', labelcolor='gray')

# Align zero for power if needed, or just let it float
ax2.axhline(0, color='black', linewidth=0.5, alpha=0.5)

fig.tight_layout()
plt.savefig('plots/multizone_office_bench_48h.png', dpi=300)
print("Optimized plot saved as multizone_office_bench_48h.png")
