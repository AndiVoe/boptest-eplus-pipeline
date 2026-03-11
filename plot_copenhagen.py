import pandas as pd
import matplotlib.pyplot as plt

# Load results
df = pd.read_csv('mpc_results_singlezone_commercial_hydronic.csv')
df['time_hours'] = df['time'] / 3600
df['temp_c'] = df['temp'] - 273.15

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)

# Temperature Plot
ax1.plot(df['time_hours'], df['temp_c'], label='Zone Temp', color='blue', linewidth=2)
ax1.axhline(24, color='red', linestyle='--', alpha=0.5, label='Heat SP')
ax1.axhline(21, color='green', linestyle='--', alpha=0.5, label='Cool SP')
ax1.set_ylabel('Temperature (°C)')
ax1.set_title('Copenhagen (singlezone_commercial_hydronic) - MPC Benchmark')
ax1.legend()
ax1.grid(True, alpha=0.3)

# Power Plot
ax2.fill_between(df['time_hours'], df['p_opt'], color='orange', alpha=0.3, label='MPC Power Demand')
ax2.plot(df['time_hours'], df['p_opt'], color='orange', linewidth=1.5)
ax2.set_ylabel('Optimized Power (W)')
ax2.set_xlabel('Time (Hours)')
ax2.legend()
ax2.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('copenhagen_bench_48h.png')
print("Plot saved as copenhagen_bench_48h.png")
